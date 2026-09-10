"""First-decision requirements proximity pilot; no sampled tool is executed.

A is the exact historical request. B repeats verbatim public issue/check declarations
in the latest state, without new diagnoses, instructions, notes or tool restrictions.
Preparation/validation are provider-free; collection needs a frozen four-sample grant.
"""

from __future__ import annotations

import argparse
import copy
import json
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.conversation import history_metadata, reconstruct_state, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SOURCE_ID = "run_dev_9b91e06c13ff4bd3"
TURN_NUMBER = 14
SOURCE_HASHES = {
    ".jsonl": "sha256:a7aaeb82cc1df35ca92ed23fcd5319c616af6104bf3c034ec299aea7f5b8f48d",
    ".envelope.json": "sha256:9771e89d06d341f41f0cf1b24491786adcd4fe6d1d1ed2896b244e51c69c4b86",
}
SCHEMA = "requirements-focus-design-v1"
FIELD = "public_requirements_at_decision"
PROTOCOL = shared.CollectionProtocol(
    "requirements-focus-sampler-v1",
    {"A": "medium", "B": "medium"},
    (("A", 1), ("B", 1), ("B", 2), ("A", 2)),
    272_000,
)
REVIEW_FILES = {
    "protocol.md": (
        "Four independent next responses A1/B1/B2/A2 at the same pre-first-edit checkpoint.\n"
        "Only B repeats the already supplied public issue and every visible check declaration\n"
        "in the latest state. No source selection, paraphrase, proposed solution, new behavior\n"
        "example, mandatory memory, changed action space or encrypted-history reset.\n"
        "No sampled tool execution, chaining, correction, retry/resume or private evaluation.\n"
        "Review anonymized public actions before unblinding. Two samples per arm, one reused\n"
        "failure-selected checkpoint: no causal proof, whole-run or generalization claim.\n"
        "This tests proximity plus repetition/extra bytes, not pure memory use or attention.\n"
    ),
    "rubric.json": canonical_json(
        {
            "grading": "NOT_ASSESSED",
            "criteria": [
                "Classify next action; an inspection/probe is not automatically better "
                "than mutation.",
                "For an edit, compare executable behavior with all original public requirements.",
                "Distinguish a supported preservation rule from merely mentioning a requirement.",
                "Record assumptions/notes and whether a chosen inspection could answer "
                "an uncertainty.",
                "Non-mutation leaves first-edit quality unobserved; "
                "do not score it as a correct edit.",
            ],
            "limits": "Static proposed-action review, not gateway admission, "
            "checks or task acceptance.",
            "deferred_metrics": ["first accepted mutation", "counterexample repair", "submission"],
        }
    ),
}


def wire(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def implementation_hashes() -> dict[str, str]:
    return {
        p.name: sha256_bytes(p.read_bytes())
        for p in sorted((Path(shared.__file__), Path(__file__)))
    }


def sampler_hash() -> str:
    return sha256_json(implementation_hashes())


def focus_requirements(items: list[dict]) -> tuple[list[dict], dict]:
    """Repeat a whitelist of existing task fields; never load another source."""
    validate_model_input(items, history_metadata(items))
    shared.require(len(items) > 3 and items[-1].get("role") == "developer", "latest state required")
    state = reconstruct_state(items)
    shared.require(
        state.get("workflow_gate") == "needs_mutation"
        and state["current_diff"]["patch"] == ""
        and state.get("last_successful_mutation") is None,
        "pre-first-mutation checkpoint required",
    )
    for item in items:
        if item.get("type") == "reasoning":
            shared.require(
                bool(item.get("encrypted_content"))
                and item.get("summary") == []
                and not item.get("text")
                and not item.get("content"),
                "opaque reasoning required",
            )
    record = json.loads(items[-1]["content"])
    shared.require(wire(record).decode() == items[-1]["content"], "state wire changed")
    shared.require(FIELD not in record["state"], "treatment already present")
    task = state["public_task"]
    issue, checks = task["issue"], task["visible_checks"]
    shared.require(
        isinstance(issue.get("title"), str)
        and isinstance(issue.get("description"), str)
        and bool(checks),
        "public issue and checks required",
    )
    card = {
        "source": "initial public_task; verbatim declarations, not execution evidence",
        "issue": {k: issue[k] for k in ("title", "description")},
        "visible_checks": [{k: c[k] for k in ("id", "command")} for c in checks],
    }
    shared.require(len(wire(card)) <= 16_000, "public requirement card exceeds pilot bound")
    alternate = copy.deepcopy(items)
    record["state"][FIELD] = card
    alternate[-1]["content"] = wire(record).decode()
    return alternate, {
        "card_hash": sha256_bytes(wire(card)),
        "card_bytes": len(wire(card)),
        "copied_field_paths": [
            "public_task.issue.title",
            "public_task.issue.description",
            "public_task.visible_checks[*].id",
            "public_task.visible_checks[*].command",
        ],
        "unchanged_prefix_items": len(items) - 1,
        "unchanged_prefix_hash": sha256_bytes(wire(items[:-1])),
        "reasoning_item_count": sum(i.get("type") == "reasoning" for i in items),
    }


def compile_requests(source_root: Path) -> tuple[dict, dict]:
    """Pin the whole journal but project only the selected dispatch's public prefix."""
    source_root = source_root.resolve()
    for suffix, digest in SOURCE_HASHES.items():
        path = source_root / "runs" / (SOURCE_ID + suffix)
        shared.require(
            path.is_file() and not path.is_symlink() and sha256_bytes(path.read_bytes()) == digest,
            "source identity changed",
        )
    events = DevJournal(source_root, SOURCE_ID).events()
    envelope = json.loads((source_root / "runs" / (SOURCE_ID + ".envelope.json")).read_bytes())
    event = [e for e in events if e["event_type"] == "turn_started"][TURN_NUMBER - 1]
    turn = event["payload"]
    items = json.loads(shared.read_source_artifact(source_root, turn["model_input_artifact"]))
    context = json.loads(shared.read_source_artifact(source_root, turn["context_artifact"]))
    validate_model_input(items, turn["native_history"])
    state = reconstruct_state(items)
    for key in ("public_task", "current_diff", "remaining_budget", "available_tool_names"):
        shared.require(state[key] == context[key], "current state mismatch")
    shared.require(state["available_tool_names"] == turn["available_tool_names"], "tool mismatch")
    prior = [
        e["payload"]["result"]["action_id"]
        for e in events[: event["sequence"] - 1]
        if e["event_type"] == "action_finished"
    ]
    calls = [i["call_id"] for i in items if i.get("type") == "function_call"]
    outputs = [i["call_id"] for i in items if i.get("type") == "function_call_output"]
    shared.require(calls == outputs == prior == turn["transcript_action_ids"], "cutoff mismatch")
    shared.require(
        envelope["model"] == shared.MODEL
        and envelope["reasoning_effort"] == "medium"
        and envelope["public_spec_hash"] == sha256_json(state["public_task"]),
        "public task/model mismatch",
    )
    alternate, metrics = focus_requirements(items)
    schemas = dev_tool_schemas(
        finish_enabled="finish_task" in turn["available_tool_names"],
        check_ids=[
            c["check_id"] for c in state["visible_check_status"] if c["status"] == "NOT_RUN"
        ],
        allowed_tools=turn["available_tool_names"],
        read_paths=turn["targeted_read_paths"],
    )
    requests = {
        arm: {
            **shared.SETTINGS,
            "input": value,
            "tools": schemas,
            "reasoning": {"effort": "medium"},
        }
        for arm, value in (("A", items), ("B", alternate))
    }
    dispatch = next(
        e["payload"]
        for e in events
        if e["event_type"] == "provider_call_started" and e["payload"]["turn_id"] == turn["turn_id"]
    )
    shared.require(
        sha256_json(requests["A"]) == dispatch["request_hash"],
        "current schema/settings cannot reproduce historical control",
    )
    metadata = {
        **shared.BOUNDARIES,
        "schema_version": SCHEMA,
        "status": "PREPARED_NOT_EXECUTABLE",
        "dispatch_enabled": False,
        "collector_implemented": True,
        "runtime_hash": shared.runtime_content_hash(),
        "source_runtime_hash": envelope["runtime_hash"],
        "source_run_id": SOURCE_ID,
        "source_journal_hash": SOURCE_HASHES[".jsonl"],
        "source_envelope_hash": SOURCE_HASHES[".envelope.json"],
        "source_turn_number": TURN_NUMBER,
        "source_turn_id": turn["turn_id"],
        "cutoff_event_hash": event["event_hash"],
        "task_id": envelope["task_id"],
        "task_version": envelope["task_version"],
        "task_content_hash": envelope["task_content_hash"],
        "sampler_hash": sampler_hash(),
        "model": shared.MODEL,
        "reasoning_effort": "medium",
        "sampling_order": [list(p) for p in PROTOCOL.sampling_order],
        "proposed_total_cap_usd": "1.20",
        "maximum_generation_calls": 4,
        "maximum_input_count_calls": 4,
        "maximum_tool_executions": 0,
        "input_token_limit": PROTOCOL.input_token_limit,
        "output_ceiling": shared.OUTPUT_CEILING,
        "historical_control_input_count": dispatch["input_tokens"],
        "alternate_input_count": None,
        "max_parallel_reads": turn["max_parallel_reads"],
        "read_paths": turn["targeted_read_paths"],
        "sole_change": f"input[-1].content(JSON).state.{FIELD}",
        "focus_metrics": metrics,
        "request_metrics": {
            a: {
                "bytes": len(wire(r)),
                "canonical_hash": sha256_json(r),
                "ordered_hash": sha256_bytes(wire(r)),
            }
            for a, r in requests.items()
        },
        "reviewer_files": {n: sha256_text(v) for n, v in REVIEW_FILES.items()},
    }
    return requests, metadata


def prepare(source_root: Path, root: Path) -> dict:
    shared.require(root.is_absolute(), "absolute design root required")
    root = root.resolve()
    shared.require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    shared.require(
        not any(
            root.is_relative_to(p.resolve()) or p.resolve().is_relative_to(root)
            for p in (source_root, shared.repository_root())
        ),
        "overlapping root",
    )
    requests, metadata = compile_requests(source_root)
    store = ArtifactStore(root)
    for name, text in REVIEW_FILES.items():
        store.write_text_immutable(root / name, text)
    packet = {
        **metadata,
        "request_artifacts": {
            a: store.put_text(wire(r).decode(), "application/json").model_dump(mode="json")
            for a, r in requests.items()
        },
    }
    store.write_text_immutable(root / "packet.json", wire(packet).decode())
    journal = DevJournal(root, "run_dev_requirements_focus_prepared")
    journal.append(
        "comparison_prepared",
        {
            **shared.BOUNDARIES,
            "packet_hash": sha256_bytes(wire(packet)),
            "sampler_hash": sampler_hash(),
            "provider_calls": 0,
            "input_count_calls": 0,
        },
    )
    return packet


def load_plan(packet_path: Path, source_root: Path, expected_hash: str) -> shared.FrozenPlan:
    raw = packet_path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet hash mismatch")
    packet = json.loads(raw)
    requests, expected = compile_requests(source_root)
    shared.require(
        set(packet) == set(expected) | {"request_artifacts"}
        and all(packet[k] == v for k, v in expected.items()),
        "design changed",
    )
    root = packet_path.parent.resolve()
    shared.require((root / "objects/sha256").is_dir(), "missing request store")
    store = ArtifactStore(root)
    shared.require(set(packet["request_artifacts"]) == {"A", "B"}, "arm set changed")
    for arm, request in requests.items():
        ref = Artifact.model_validate(packet["request_artifacts"][arm])
        shared.require(store.read_bytes(ref) == wire(request), "request/order changed")
    for name, digest in expected["reviewer_files"].items():
        shared.require(sha256_bytes((root / name).read_bytes()) == digest, "review changed")
    cells = tuple(
        shared.Cell(
            "C1",
            arm,
            wire(requests[arm]).decode(),
            packet["request_metrics"][arm]["canonical_hash"],
            packet["historical_control_input_count"] if arm == "A" else None,
            packet["source_turn_id"],
            packet["max_parallel_reads"],
            tuple(packet["read_paths"]),
            number,
        )
        for arm, number in PROTOCOL.sampling_order
    )
    return shared.FrozenPlan(
        packet_path.resolve(),
        expected_hash,
        packet,
        cells,
        source_root.resolve(),
        expected["reviewer_files"],
    )


def collect(plan, approval, *, adapter_factory=None, clock=monotonic, checkpoint=lambda _: None):
    shared._validate_collection_approval(plan, approval, sampler_hash())
    refreshed = load_plan(plan.packet_path, plan.source_root, approval.packet_hash)
    return shared._collect_validated(
        refreshed,
        approval,
        protocol=PROTOCOL,
        adapter_factory=adapter_factory,
        clock=clock,
        checkpoint=checkpoint,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect").add_argument("--result-root", type=Path, required=True)
    for name in ("prepare", "validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--source-state-root", type=Path, required=True)
        if name == "prepare":
            command.add_argument("--output-root", type=Path, required=True)
        else:
            command.add_argument("--packet", type=Path, required=True)
            command.add_argument("--packet-hash", required=True)
        if name == "collect":
            command.add_argument(
                "--approve-four-focus-responses-zero-tools", action="store_true", required=True
            )
            command.add_argument("--sampler-hash", required=True)
            command.add_argument("--result-root", type=Path, required=True)
            command.add_argument("--credential-file", type=Path, required=True)
            command.add_argument("--max-cost-usd", type=Decimal, required=True)
            command.add_argument("--pricing-hash", required=True)
            command.add_argument("--pricing-verified-on", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = shared.inspect_result(args.result_root)
        else:
            if args.command == "prepare":
                prepare(args.source_state_root, args.output_root)
                args.packet = args.output_root / "packet.json"
                args.packet_hash = sha256_bytes(args.packet.read_bytes())
            plan = load_plan(args.packet, args.source_state_root, args.packet_hash)
            if args.command == "collect":
                result = collect(
                    plan,
                    shared.Approval(
                        args.packet_hash,
                        args.sampler_hash,
                        args.result_root,
                        args.credential_file,
                        args.max_cost_usd,
                        args.pricing_hash,
                        args.pricing_verified_on,
                    ),
                )
            else:
                result = {
                    **shared.BOUNDARIES,
                    "status": "VALIDATED_NOT_EXECUTED",
                    "packet_hash": plan.packet_hash,
                    "sampler_hash": sampler_hash(),
                    "runtime_hash": plan.packet["runtime_hash"],
                    "request_metrics": plan.packet["request_metrics"],
                    "focus_metrics": plan.packet["focus_metrics"],
                    "sampling_order": PROTOCOL.sampling_order,
                    "fresh_token_counts": {"A": None, "B": None},
                    "pricing_status": "REGISTERED_RATES_REQUIRE_FRESH_LIVE_REVIEW",
                    "pricing_hash": sha256_json(shared.price_identity()),
                    "provider_calls": 0,
                    "input_count_calls": 0,
                }
        print(canonical_json(result))
        return 0 if result.get("terminal") in {None, "SAMPLES_COLLECTED"} else 1
    except Exception as exc:
        print(
            canonical_json(
                {
                    **shared.BOUNDARIES,
                    "status": "PREFLIGHT_REJECTED",
                    "error_type": type(exc).__name__,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
