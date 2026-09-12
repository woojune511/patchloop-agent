"""Freeze/verify two historical count bodies, without a client or live entry point.

This is a new diagnostic design, not a resume of the source run. The protocol
reducer is pure; it does not dispatch requests. Count-only billing and exact
packet approval must be resolved separately before implementing live collection.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

from diagnostics import decision_sampler as shared
from patchloop.agent.count_diagnostics import input_count_request_metadata
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.dev.conversation import reconstruct_state, validate_model_input
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.runtime import repository_root, runtime_content_hash
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SOURCE_ID = "run_dev_03b4fcac720b4760"
SOURCE_HASHES = {
    ".jsonl": "sha256:3f27e07f11efc1e041ebe8addf03b594ba2571cb04997eeed3ec7d2a801f631f",
    ".envelope.json": "sha256:1be2ab4dd030d2446da0e46432cba57990e0e9b7381e04d86faca1d974195fe8",
}
TURNS = (20, 21)
CONTROL_COUNT = 97_810
COUNT_HASHES = (
    "sha256:45a7fa37ef5655f222304f71930c63543d2e3bdd3e857713b758a0660766367a",
    "sha256:2a8cbf3632f1f4332741c907e3931efd2094c68126c9e3307ad54987d6703251",
)
CASE_IDS = ("successful_count_control", "failed_count_case")
PROTOCOL = {
    "endpoint": "https://api.openai.com/v1/responses/input_tokens",
    "method": "POST", "order": list(CASE_IDS), "max_count_requests": 2,
    "max_attempts_per_case": 1, "sdk_retries": 0,
    "proposed_count_timeout_seconds": 30, "proposed_total_timeout_seconds": 65,
    "proposed_cleanup_reserve_seconds": 5,
    "control_must_match_historical_count": True,
    "error_or_interruption": "STOP_ALL", "automatic_retry_or_resume": False,
    "response_generation_requests": 0, "tool_executions": 0,
    "docker_operations": 0, "hidden_evaluations": 0,
    "continuation_reset": False,
}
BILLING = {
    "count_endpoint_pricing": "UNCONFIRMED", "count_cost_usd": None,
    "live_execution_enabled": False,
    "blockers": ["COUNT_BILLING_UNCONFIRMED", "EXACT_PACKET_APPROVAL_REQUIRED"],
    "prior_grant_reusable": False,
    "reviewed_on": "2026-09-12",
    "sources": [
        "https://developers.openai.com/api/docs/guides/token-counting",
        "https://developers.openai.com/api/docs/pricing",
    ],
    "finding": (
        "The guide documents input counting; neither reviewed page explicitly establishes "
        "this endpoint's billing. Generation prices do not prove count-only pricing."
    ),
}
INTERPRETATION = {
    "control_failure_or_count_change": "BASELINE_NOT_REPRODUCED; stop before second case",
    "both_counts_succeed": "NOT_REPRODUCED; not proof the original error was transient",
    "case_http_failure": "NEW_REJECTION_OBSERVED; not a recovered historical error",
    "size_difference": "CANONICAL_ONLY; not wire capture or proof of a server size limit",
    "transport_or_missing_outcome": "UNKNOWN; stop without retry",
}


def source_events(source_root: Path) -> tuple[list[dict], dict]:
    """Verify old bytes and their hash chain; never construct a writable source store."""
    for suffix, digest in SOURCE_HASHES.items():
        path = source_root / "runs" / (SOURCE_ID + suffix)
        shared.require(
            path.is_file() and not path.is_symlink() and sha256_bytes(path.read_bytes()) == digest,
            "frozen source identity mismatch",
        )
    journal = object.__new__(DevJournal)
    journal.path = source_root / "runs" / (SOURCE_ID + ".jsonl")
    journal.run_id = SOURCE_ID
    events = journal.events()
    envelope = json.loads((source_root / "runs" / (SOURCE_ID + ".envelope.json")).read_bytes())
    shared.require(
        events[-1]["event_type"] == "terminal"
        and events[-1]["payload"]["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN",
        "source terminal mismatch",
    )
    return events, envelope


def cutoff_request(events: list[dict], envelope: dict, source_root: Path, number: int):
    event = [e for e in events if e["event_type"] == "turn_started"][number - 1]
    turn = event["payload"]
    items = json.loads(shared.read_source_artifact(source_root, turn["model_input_artifact"]))
    context_raw = shared.read_source_artifact(source_root, turn["context_artifact"])
    context = json.loads(context_raw)
    validate_model_input(items, turn["native_history"])
    shared.require(sha256_json(items) == turn["model_input_hash"], "model input mismatch")
    shared.require(sha256_bytes(context_raw) == turn["context_hash"], "context mismatch")
    state = reconstruct_state(items)
    for key in ("public_task", "current_diff", "remaining_budget", "available_tool_names"):
        shared.require(state[key] == context[key], "current public state mismatch")
    shared.require(state["available_tool_names"] == turn["available_tool_names"], "tool mismatch")
    shared.require(
        envelope["run_id"] == SOURCE_ID and envelope["provider"] == "openai"
        and envelope["model"] == shared.MODEL and envelope["reasoning_effort"] == "medium"
        and envelope["split"] == "dev-train"
        and envelope["public_spec_hash"] == sha256_json(state["public_task"]),
        "source task/model mismatch",
    )
    calls = [i["call_id"] for i in items if i.get("type") == "function_call"]
    outputs = [i["call_id"] for i in items if i.get("type") == "function_call_output"]
    shared.require(
        calls == outputs == turn["transcript_action_ids"] and len(calls) == len(set(calls)),
        "native call/output order mismatch",
    )
    # Harness checks are real evidence but are not synthetic native tool calls.
    prior_actions = {
        e["payload"]["result"]["action_id"] for e in events[:event["sequence"] - 1]
        if e["event_type"] == "action_finished"
    }
    shared.require(set(calls) <= prior_actions, "native output is not a prior completed action")
    for item in items:
        if item.get("type") == "reasoning":
            shared.require(
                set(item) <= {"type", "id", "encrypted_content", "status", "summary"}
                and item.get("summary", []) == []
                and isinstance(item.get("encrypted_content"), str) and item["encrypted_content"],
                "reasoning must contain encrypted state only",
            )
    schemas = dev_tool_schemas(
        finish_enabled="finish_task" in turn["available_tool_names"],
        check_ids=[c["check_id"] for c in state["visible_check_status"]
                   if c["status"] == "NOT_RUN"],
        allowed_tools=turn["available_tool_names"], read_paths=turn["targeted_read_paths"],
    )
    request = OpenAIResponsesAdapter.request_payload(
        SimpleNamespace(config=shared.model_config("medium")), items, schemas,
        system_prompt=DEV_SYSTEM_PROMPT,
    )
    admissions = [e for e in events if e["event_type"] == "input_count_started"
                  and e["payload"]["turn_id"] == turn["turn_id"]]
    shared.require(len(admissions) == 1, "source count admission mismatch")
    admission = admissions[0]
    request_hash = sha256_json(request)
    shared.require(
        request_hash == admission["payload"]["request_hash"], "original request mismatch",
    )
    outcomes = [e for e in events if e["event_type"] == "input_count_finished"
                and e["payload"]["count_id"] == admission["payload"]["count_id"]]
    shared.require(len(outcomes) <= 1, "duplicate source count outcome")
    metadata = {
        "turn": number, "turn_id": turn["turn_id"],
        "source_prefix_event_hash": event["event_hash"],
        "source_count_event_hash": admission["event_hash"],
        "original_generation_request_hash": request_hash,
        "model_input_hash": turn["model_input_hash"], "context_hash": turn["context_hash"],
        "native_history": turn["native_history"], "native_call_output_pairs": len(calls),
        "historical_count": outcomes[0]["payload"]["input_tokens"] if outcomes else None,
        "request_metadata": input_count_request_metadata(request),
    }
    return OpenAIResponsesAdapter._count_payload(request), metadata


def reconstruct_cases(source_root: Path) -> tuple[list[tuple[dict, dict]], dict]:
    events, envelope = source_events(source_root)
    cases = [cutoff_request(events, envelope, source_root, number) for number in TURNS]
    for index, (payload, metadata) in enumerate(cases):
        shared.require(sha256_json(payload) == COUNT_HASHES[index], "frozen count payload mismatch")
        shared.require(
            metadata["historical_count"] == (CONTROL_COUNT if index == 0 else None),
            "historical count mismatch",
        )
        metadata["case_id"] = CASE_IDS[index]
    return cases, envelope


def packet_header(source_root: Path, envelope: dict) -> dict:
    return {
        "schema_version": "count-only-diagnostic-design-v1",
        "source_root": str(source_root.resolve()), "source_run_id": SOURCE_ID,
        "source_hashes": SOURCE_HASHES,
        "source_contract": {key: envelope[key] for key in (
            "task_id", "task_version", "task_content_hash", "public_spec_hash", "runtime_hash",
            "model_hash", "model", "reasoning_effort", "credential_file_path_hash",
        )},
        "preparation_identity": {
            "runtime_hash": runtime_content_hash(), "tool_surface_hash": dev_tool_surface_hash(),
            "diagnostic_hash": sha256_bytes(Path(__file__).read_bytes()),
            "shared_reader_hash": sha256_bytes(Path(shared.__file__).read_bytes()),
        },
        "protocol": PROTOCOL, "billing": BILLING, "interpretation": INTERPRETATION,
        "official": False, "claim_eligible": False,
        "task_acceptance": "NOT_RUN", "safety_state": "NOT_RUN",
    }


def prepare(source_root: Path, output: Path) -> dict:
    source_root, output = source_root.resolve(), output.resolve()
    for protected in (repository_root().resolve(), source_root):
        shared.require(
            not output.is_relative_to(protected) and not protected.is_relative_to(output),
            "packet must be outside source state and repository",
        )
    shared.require(not output.exists(), "packet destination must be new")
    cases, envelope = reconstruct_cases(source_root)
    packet = packet_header(source_root, envelope)
    output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(output / "artifacts")
    packet["cases"] = []
    for payload, metadata in cases:
        artifact = store.put_text(canonical_json(payload), media_type="application/json")
        packet["cases"].append({
            **metadata, "count_payload_artifact": artifact.model_dump(mode="json"),
        })
    packet_hash = sha256_json(packet)
    document_store = ArtifactStore(output)
    document_store.write_text_immutable(output / "packet.json", canonical_json(packet))
    document_store.write_text_immutable(output / "packet.sha256", packet_hash + "\n")
    journal = DevJournal(output, "run_dev_countdesign_" + uuid.uuid4().hex[:16])
    journal.append("count_design_prepared", {
        "packet_hash": packet_hash, "case_count": len(cases), "api_requests": 0,
        "live_execution_enabled": False,
    })
    # Source identity is rechecked after writing; no source root file is ever written.
    return verify(output, packet_hash)


def verify(output: Path, packet_hash: str) -> dict:
    """Read-only and deterministic, including two independently repeated rehearsals."""
    output = output.resolve()
    packet = json.loads((output / "packet.json").read_bytes())
    shared.require(sha256_json(packet) == packet_hash, "packet hash mismatch")
    source_root = Path(packet["source_root"])
    cases, envelope = reconstruct_cases(source_root)
    shared.require(
        {key: value for key, value in packet.items() if key != "cases"}
        == packet_header(source_root, envelope), "packet contract mismatch",
    )
    shared.require(len(packet["cases"]) == len(cases), "packet case count mismatch")
    for saved, (payload, metadata) in zip(packet["cases"], cases, strict=True):
        shared.require(
            {key: value for key, value in saved.items() if key != "count_payload_artifact"}
            == metadata, "case metadata mismatch",
        )
        raw = shared.read_source_artifact(output, saved["count_payload_artifact"])
        shared.require(raw == canonical_json(payload).encode("utf-8"), "count body mismatch")
    return {
        "packet_hash": packet_hash, "status": "VERIFIED_NO_CALL",
        "count_payload_hashes": list(COUNT_HASHES),
        "canonical_utf8_bytes": [c[1]["request_metadata"]["count_payload_canonical_utf8_bytes"]
                                 for c in cases],
        "input_item_counts": [c[1]["request_metadata"]["input_item_count"] for c in cases],
        "native_call_output_pairs": [c[1]["native_call_output_pairs"] for c in cases],
        "api_requests": 0, "task_executions": 0, "official": False,
        "billing_status": "UNCONFIRMED", "live_execution_enabled": False,
    }


def protocol_state(receipts: list[dict]) -> dict:
    """Pure proposed scheduling rule. No network, persistence, credentials or retry."""
    shared.require(len(receipts) <= 2, "too many count receipts")
    for index, receipt in enumerate(receipts):
        shared.require(receipt.get("case_id") == CASE_IDS[index], "count receipt order mismatch")
        status = receipt.get("status")
        shared.require(status in {"started", "failed", "succeeded"}, "invalid count receipt")
        if status != "succeeded":
            shared.require(index == len(receipts) - 1, "dispatch after uncertainty")
            return {"next_case": None, "result": "UNKNOWN" if status == "started" else "STOP_ERROR"}
        count = receipt.get("input_tokens")
        shared.require(type(count) is int and count >= 0, "invalid input token count")
        if index == 0 and count != CONTROL_COUNT:
            shared.require(len(receipts) == 1, "dispatch after control count changed")
            return {"next_case": None, "result": "BASELINE_NOT_REPRODUCED"}
    return {
        "next_case": CASE_IDS[len(receipts)] if len(receipts) < 2 else None,
        "result": "PENDING" if len(receipts) < 2 else "NOT_REPRODUCED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare", help="new external packet; no API/client")
    build.add_argument("--source-root", type=Path, default=Path("C:/patchloop-state"))
    build.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("verify", help="read-only source and packet verification")
    check.add_argument("--packet-root", type=Path, required=True)
    check.add_argument("--packet-hash", required=True)
    args = parser.parse_args()
    result = (prepare(args.source_root, args.output) if args.command == "prepare"
              else verify(args.packet_root, args.packet_hash))
    print(canonical_json(result))


if __name__ == "__main__":
    main()
