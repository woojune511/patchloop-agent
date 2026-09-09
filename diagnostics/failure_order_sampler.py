"""Frozen failure-summary-order comparison, outside the normal agent loop.

Prepare/validate are provider-free. Collect requires separate four-response/zero-tool
approval. Only the latest state's three failure rows are permuted; prior native items,
encrypted reasoning, tool definitions, model settings and source evidence stay exact.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig
from patchloop.dev.conversation import reconstruct_state, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

AUDIT_HASHES = {
    "checkpoint-manifest.json": (
        "sha256:eeb98046d966c0c289bae983f3376144e9b812424156f8a1fcf841456ef2f1ca"
    ),
    "contrast-spec.json": "sha256:369a0f0d56c52a75df0f7e955d83e99112804bd3443a6163cc662009895407ce",
}
SCHEMA = "failure-order-design-v1"
PROTOCOL = shared.CollectionProtocol(
    "failure-order-sampler-v1",
    {"A": "medium", "B": "medium"},
    (("A", 1), ("B", 1), ("B", 2), ("A", 2)),
    272_000,
)
REVIEW_FILES = {
    "protocol.md": (
        "Four independent next responses, A1/B1/B2/A2, one frozen public checkpoint.\n"
        "Only latest failure-summary order differs. No tool execution, chaining, retries,\n"
        "corrections, private feedback or judge calls. Review anonymous actions before\n"
        "unblinding. This failure-selected pilot does not estimate whole-run quality.\n"
    ),
    "rubric.json": canonical_json(
        {
            "grading": "NOT_ASSESSED",
            "criteria": [
                "Does the proposed action account for all reported failure classes or only some?",
                "Does the public basis claim complete repair when the edit addresses only part?",
                "Is a deferred inspection or probe relevant to remaining public uncertainty?",
                "Compare exact edits with public evidence, not just keywords; do not execute them.",
            ],
            "limits": "Static review is not full gateway admission or measured task correctness.",
        }
    ),
}


def wire_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def implementation_hashes() -> dict[str, str]:
    return {
        f"diagnostics/{p.name}": sha256_bytes(p.read_bytes())
        for p in sorted((Path(shared.__file__), Path(__file__)))
    }


def sampler_hash() -> str:
    return sha256_json(implementation_hashes())


def permute_latest_summary(items: list[dict]) -> list[dict]:
    """Change presentation order only, without decoding or rewriting native history."""
    shared.require(items[-1].get("role") == "developer", "latest state missing")
    view = json.loads(items[-1]["content"])
    shared.require(view.get("kind") == "harness_current_state", "not a current-state view")
    failure = view["state"]["current_public_failure"]
    summary = failure["failure_summary"]
    lines = summary["lines"]
    shared.require(
        failure["evidence_currency"] == "current"
        and summary["observed_count"] == len(lines) == len(set(lines)) == 3
        and summary["truncated"] is False,
        "three complete current failure rows required",
    )
    shared.require(wire_json(view) == items[-1]["content"], "current-state wire mismatch")
    summary["lines"] = [lines[1], lines[2], lines[0]]
    result = copy.deepcopy(items)
    result[-1]["content"] = wire_json(view)
    return result


def compile_requests(audit_root: Path, source_root: Path) -> tuple[dict, dict]:
    """Read pinned public artifacts, not task packages, worktrees or reviewer labels."""
    audit = {}
    for name, digest in AUDIT_HASHES.items():
        path = audit_root / name
        shared.require(path.is_file() and not path.is_symlink(), "audit file missing")
        raw = path.read_bytes()
        shared.require(sha256_bytes(raw) == digest, "audit identity mismatch")
        audit[name] = json.loads(raw)
    manifest, contrast = audit["checkpoint-manifest.json"], audit["contrast-spec.json"]
    source_root = source_root.resolve()
    journal_path = source_root / "runs" / (manifest["run_id"] + ".jsonl")
    envelope_path = journal_path.with_suffix(".envelope.json")
    for path, ref in ((journal_path, manifest["journal"]), (envelope_path, manifest["envelope"])):
        shared.require(path.resolve() == Path(ref["path"]).resolve(), "source path mismatch")
        shared.require(
            sha256_bytes(path.read_bytes()) == ref["content_hash"], "source hash mismatch"
        )
    events = DevJournal(source_root, manifest["run_id"]).events()
    envelope = json.loads(envelope_path.read_bytes())
    shared.require(
        manifest["runtime_hash"] == envelope["runtime_hash"] == shared.runtime_content_hash()
        and manifest["model_hash"] == envelope["model_hash"],
        "runtime/model mismatch",
    )
    turns = [e for e in events if e["event_type"] == "turn_started"]
    event = turns[manifest["turn_number"] - 1]
    turn = event["payload"]
    shared.require(
        event["sequence"] == manifest["cutoff_event_sequence"]
        and event["event_hash"] == manifest["cutoff_event_hash"]
        and turn["turn_id"] == manifest["turn_id"]
        and turn["model_input_artifact"] == manifest["native_input_artifact"]
        and turn["context_artifact"] == manifest["context_artifact"]
        and turn["native_history"] == manifest["native_history"],
        "checkpoint cutoff mismatch",
    )
    raw_input = shared.read_source_artifact(source_root, turn["model_input_artifact"])
    context = json.loads(shared.read_source_artifact(source_root, turn["context_artifact"]))
    items = json.loads(raw_input)
    validate_model_input(items, turn["native_history"])
    state = reconstruct_state(items)
    shared.require(
        all(
            state[k] == context[k]
            for k in (
                "public_task",
                "current_diff",
                "current_public_failure",
                "visible_check_status",
                "remaining_budget",
                "available_tool_names",
                "mutation_scope_budget",
            )
        )
        and state["available_tool_names"]
        == turn["available_tool_names"]
        == manifest["allowed_tools"]
        and state["current_public_failure"]["current_diff_hash"] == manifest["current_diff_hash"],
        "current public state mismatch",
    )
    prior = {
        e["payload"]["result"]["action_id"]
        for e in events[: event["sequence"] - 1]
        if e["event_type"] == "action_finished"
    }
    calls = [i["call_id"] for i in items if i.get("type") == "function_call"]
    outputs = [i["call_id"] for i in items if i.get("type") == "function_call_output"]
    shared.require(
        calls == outputs == turn["transcript_action_ids"]
        and len(set(calls)) == len(calls)
        and set(calls) <= prior,
        "native action cutoff/order mismatch",
    )
    shared.require(
        all(
            i.get("encrypted_content")
            and i.get("summary") == []
            and not i.get("text")
            and not i.get("content")
            for i in items
            if i.get("type") == "reasoning"
        ),
        "encrypted history mismatch",
    )
    alternate = permute_latest_summary(items)
    shared.require(
        contrast["dispatch_authorized"] is False
        and contrast["original_input_hash"] == sha256_bytes(raw_input)
        and contrast["prospective_alternate_input_hash"] == sha256_json(alternate)
        and contrast["sole_change"]
        == {
            "item": len(items) - 1,
            "field": "content(JSON).state.current_public_failure.failure_summary.lines",
            "permutation": [1, 2, 0],
        },
        "frozen contrast mismatch",
    )
    schema_inputs = {
        "finish_enabled": "finish_task" in turn["available_tool_names"],
        "check_ids": [
            c["check_id"] for c in state["visible_check_status"] if c["status"] == "NOT_RUN"
        ],
        "allowed_tools": turn["available_tool_names"],
        "read_paths": turn["targeted_read_paths"],
    }
    schemas = dev_tool_schemas(**schema_inputs)
    requests = {
        arm: {
            **shared.SETTINGS,
            "input": input_items,
            "tools": schemas,
            "reasoning": {"effort": "medium"},
        }
        for arm, input_items in (("A", items), ("B", alternate))
    }
    dispatch = next(
        e["payload"]
        for e in events
        if e["event_type"] == "provider_call_started" and e["payload"]["turn_id"] == turn["turn_id"]
    )
    shared.require(
        sha256_json(requests["A"]) == dispatch["request_hash"], "original request mismatch"
    )
    # Use only dispatch-time counting metadata, never the selected response as an input.
    count = dispatch["input_tokens"]
    shared.require(type(count) is int and count > 0, "historical input count missing")
    metadata = {
        **shared.BOUNDARIES,
        "schema_version": SCHEMA,
        "status": "PREPARED_NOT_EXECUTABLE",
        "dispatch_enabled": False,
        "source_run_id": manifest["run_id"],
        "source_turn_id": turn["turn_id"],
        "source_turn_number": manifest["turn_number"],
        "source_journal_hash": manifest["journal"]["content_hash"],
        "source_audit_hashes": AUDIT_HASHES,
        "runtime_hash": envelope["runtime_hash"],
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
        "historical_control_input_count": count,
        "alternate_input_count": None,
        "max_parallel_reads": turn["max_parallel_reads"],
        "read_paths": turn["targeted_read_paths"],
        "request_metrics": {
            arm: {
                "bytes": len(wire_json(request).encode()),
                "canonical_hash": sha256_json(request),
                "ordered_hash": sha256_text(wire_json(request)),
            }
            for arm, request in requests.items()
        },
        "sole_change": contrast["sole_change"],
        "reviewer_files": {name: sha256_text(body) for name, body in REVIEW_FILES.items()},
    }
    return requests, metadata


def prepare(audit_root: Path, source_root: Path, root: Path) -> dict:
    shared.require(root.is_absolute(), "absolute design root required")
    root = root.resolve()
    shared.require(
        not any(
            root.is_relative_to(p.resolve())
            for p in (shared.repository_root(), source_root, audit_root)
        ),
        "design root must be external",
    )
    shared.require(not root.exists(), "design already exists; validate without rewriting")
    requests, metadata = compile_requests(audit_root, source_root)
    root.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(root)
    for name, text in REVIEW_FILES.items():
        store.write_text_immutable(root / name, text)
    packet = {
        **metadata,
        "request_artifacts": {
            arm: store.put_text(wire_json(request), "application/json").model_dump(mode="json")
            for arm, request in requests.items()
        },
    }
    store.write_text_immutable(root / "packet.json", wire_json(packet))
    return packet


@dataclass(frozen=True)
class OrderPlan(shared.FrozenPlan):
    audit_root: Path


def load_plan(
    packet_path: Path, audit_root: Path, source_root: Path, expected_hash: str
) -> OrderPlan:
    raw = packet_path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet hash mismatch")
    packet = json.loads(raw)
    requests, expected = compile_requests(audit_root, source_root)
    shared.require(set(packet) == set(expected) | {"request_artifacts"}, "packet fields mismatch")
    shared.require(all(packet[k] == v for k, v in expected.items()), "design contract mismatch")
    root = packet_path.parent.resolve()
    shared.require((root / "objects" / "sha256").is_dir(), "missing prepared requests")
    store = ArtifactStore(root)
    shared.require(set(packet["request_artifacts"]) == {"A", "B"}, "arm artifacts mismatch")
    for arm, request in requests.items():
        actual = store.read_bytes(Artifact.model_validate(packet["request_artifacts"][arm]))
        shared.require(actual == wire_json(request).encode(), "prepared request/order mismatch")
    for name, digest in expected["reviewer_files"].items():
        shared.require(sha256_bytes((root / name).read_bytes()) == digest, "review file mismatch")
    cells = tuple(
        shared.Cell(
            "C1",
            arm,
            wire_json(requests[arm]),
            packet["request_metrics"][arm]["canonical_hash"],
            packet["historical_control_input_count"] if arm == "A" else None,
            packet["source_turn_id"],
            packet["max_parallel_reads"],
            tuple(packet["read_paths"]),
            sample_number=number,
        )
        for arm, number in PROTOCOL.sampling_order
    )
    return OrderPlan(
        packet_path.resolve(),
        expected_hash,
        packet,
        cells,
        source_root.resolve(),
        {**AUDIT_HASHES, **expected["reviewer_files"]},
        audit_root.resolve(),
    )


def collect(
    plan: OrderPlan,
    approval: shared.Approval,
    *,
    adapter_factory: Callable[[ModelConfig], OpenAIResponsesAdapter] | None = None,
    clock: Callable[[], float] = monotonic,
    checkpoint: Callable[[str], None] = lambda _: None,
) -> dict:
    shared._validate_collection_approval(
        plan, approval, sampler_hash(), protected_roots=(plan.audit_root,)
    )
    refreshed = load_plan(plan.packet_path, plan.audit_root, plan.source_root, approval.packet_hash)
    shared.require(refreshed.design_hashes == plan.design_hashes, "review design changed")
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
        command.add_argument("--audit-root", type=Path, required=True)
        command.add_argument("--source-state-root", type=Path, required=True)
        if name == "prepare":
            command.add_argument("--output-root", type=Path, required=True)
        else:
            command.add_argument("--packet", type=Path, required=True)
            command.add_argument("--packet-hash", required=True)
        if name == "collect":
            command.add_argument(
                "--approve-four-order-responses-zero-tools", action="store_true", required=True
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
                prepare(args.audit_root, args.source_state_root, args.output_root)
                args.packet = args.output_root / "packet.json"
                args.packet_hash = sha256_bytes(args.packet.read_bytes())
            plan = load_plan(args.packet, args.audit_root, args.source_state_root, args.packet_hash)
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
                    "implementation_hashes": implementation_hashes(),
                    "runtime_hash": plan.packet["runtime_hash"],
                    "source_audit_hashes": AUDIT_HASHES,
                    "sampling_order": PROTOCOL.sampling_order,
                    "request_metrics": plan.packet["request_metrics"],
                    "fresh_token_counts": {"A": None, "B": None},
                    "input_token_limit": PROTOCOL.input_token_limit,
                    "future_cell_reserve_nanos": shared.full_reservation(
                        PROTOCOL.input_token_limit
                    ),
                    "pricing_hash": sha256_json(shared.price_identity()),
                    "pricing_status": "REGISTERED_RATES_REQUIRE_FRESH_LIVE_REVIEW",
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
