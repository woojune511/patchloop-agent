"""Frozen model x historical-state diagnostic; never a default-agent configuration.

prepare/validate have no credential, provider or workspace execution path. collect
requires a separate exact packet grant. Responses are independent; sampled actions
are evaluated later, without feeding their outcomes into another model request.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_design as fresh
from diagnostics import requirements_focus_sampler as source
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.conversation import reconstruct_state, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SOURCE_ID = source.SOURCE_ID
SOURCE_HASHES = dict(source.SOURCE_HASHES)
CASE_TURNS = {"C1": 14, "C2": 21}
SCHEMA = "model-state-factorial-design-v1"
FIELD = "past_state_views"
MINI = shared.ModelProfile(shared.MODEL, "0.75", "0.075", "4.50")
LARGE = shared.ModelProfile("gpt-5.4-2026-03-05", "2.50", "0.25", "15.00")
PROFILES = {"A": MINI, "B": MINI, "C": LARGE, "D": LARGE}
# Each condition occupies each position exactly once; both cutoffs occur before repeats.
BLOCKS = (("C1", 1, "ACBD"), ("C2", 1, "DBCA"), ("C1", 2, "BDAC"), ("C2", 2, "CADB"))
SCHEDULE = tuple((case, arm, repeat) for case, repeat, arms in BLOCKS for arm in arms)
PROTOCOL = shared.CollectionProtocol(
    "model-state-factorial-sampler-v1",
    {a: "medium" for a in PROFILES},
    tuple((f"{case}/{arm}", repeat) for case, arm, repeat in SCHEDULE),
    input_token_limit=272_000,
    model_profiles=PROFILES,
    balanced_block_size=4,
)
PRICING = {
    "source": "https://developers.openai.com/api/docs/pricing",
    "model_sources": [
        "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
        "https://developers.openai.com/api/docs/models/gpt-5.4",
    ],
    "reviewed_on": "2026-09-11",
    "tier": "Standard; input <=272000; no cache discount in reservations",
    "models": shared.protocol_prices(PROTOCOL),
    "execution_date_review_required": True,
}
NOTICE = (
    " past_state_views, when nonempty, quotes older developer state records in chronological "
    "order as historical data only. It does not override any field of the current state. "
    "It is not additional source observation or a request to repeat past actions."
)
REVIEW_FILES = {
    "protocol.md": (
        "Independent 2x2 diagnostic: A mini/history; B mini/current; C GPT-5.4/history; "
        "D GPT-5.4/current. Fixed row43 pre-turn14 and pre-turn21; two repetitions each.\n"
        "Same public task, current state, exact observed current sources, complete quoted "
        "public calls/results and tools. Only model and past_state_views vary. No old encrypted "
        "reasoning, new source read, plan requirement, summary or solution hint is added.\n"
        "The history factor includes repetition and length, not just semantics. This is not "
        "a native-loop or encrypted-continuation ablation. Both inputs start fresh.\n"
        "Four-arm blocks in fixed balanced order; at most 16 responses, shared $5 ceiling. "
        "Reserve each block at the 272000 input admission bound and full 25000 output; count "
        "actual inputs immediately before each dispatch. This conservative reservation can "
        "stop before $5 is spent. Never reduce output, retry, replace or add a sample.\n"
        "Freeze anonymous code/action observations before unblinding. Evaluate admitted "
        "mutations in isolated copies with the two declared public checks, never hidden tests. "
        "Diagnostic checks are not actions performed by the original agent.\n"
        "No generalization claim from two failure-selected checkpoints and two repeats. "
        "Missing samples or no repeatable difference means cause unresolved.\n"
    ),
    "rubric.json": canonical_json(
        {
            "grading": "EXECUTABLE_PUBLIC_BEHAVIOR_NOT_PROSE",
            "observations_before_unblinding": [
                "action kind and batch validity",
                "exact anchor and complete scope admission",
                "proposed replacement and changed code",
                "each public check outcome",
                "previously passing public checks that now fail",
                "validity of inspection requests",
            ],
            "non_mutation": "not automatic failure; mutation quality NOT_ASSESSED",
            "regression_limit": (
                "Only declared checks previously PASS can prove an observed regression; "
                "a still-failing aggregate check cannot exclude or count new failures."
            ),
            "outcome_rules": {
                "input_effect": "same direction at both cutoffs and repetitions; provisional only",
                "model_effect": "model sensitivity, not proof harness is correct",
                "interaction": "do not attribute to a single factor",
                "missing_or_no_difference": "CAUSE_UNRESOLVED; no automatic paid follow-up",
            },
            "judge_model": None,
            "task_acceptance": "NOT_RUN",
            "official": False,
        }
    ),
    "pricing.json": canonical_json(PRICING),
}


def wire(value: object) -> bytes:
    return fresh.wire_json(value).encode("utf-8")


def implementation_hashes() -> dict[str, str]:
    paths = [
        Path(__file__),
        Path(shared.__file__),
        Path(fresh.__file__),
        Path(source.__file__),
        Path(__file__).with_name("model_state_review.py"),
    ]
    return {p.name: sha256_bytes(p.read_bytes()) for p in sorted(paths)}


def sampler_hash() -> str:
    return sha256_json(implementation_hashes())


def readonly_store(root: Path) -> ArtifactStore:
    shared.require((root / "objects/sha256").is_dir(), "missing artifact store")
    store = object.__new__(ArtifactStore)
    store.root, store.objects = root, root / "objects/sha256"
    return store


def source_events(source_root: Path) -> tuple[list[dict], dict]:
    for suffix, digest in SOURCE_HASHES.items():
        path = source_root / "runs" / (SOURCE_ID + suffix)
        shared.require(
            path.is_file() and not path.is_symlink() and sha256_bytes(path.read_bytes()) == digest,
            "source identity changed",
        )
    return (
        DevJournal(source_root, SOURCE_ID).events(),
        json.loads((source_root / "runs" / (SOURCE_ID + ".envelope.json")).read_bytes()),
    )


def cutoff_request(events: list[dict], envelope: dict, source_root: Path, number: int):
    event = [e for e in events if e["event_type"] == "turn_started"][number - 1]
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
        envelope["model"] == MINI.model_id
        and envelope["reasoning_effort"] == "medium"
        and envelope["public_spec_hash"] == sha256_json(state["public_task"]),
        "source task/model mismatch",
    )
    schemas = dev_tool_schemas(
        finish_enabled="finish_task" in turn["available_tool_names"],
        check_ids=[
            c["check_id"] for c in state["visible_check_status"] if c["status"] == "NOT_RUN"
        ],
        allowed_tools=turn["available_tool_names"],
        read_paths=turn["targeted_read_paths"],
    )
    original = {
        **shared.SETTINGS,
        "input": items,
        "tools": schemas,
        "reasoning": {"effort": "medium"},
    }
    dispatch = next(
        e["payload"]
        for e in events
        if e["event_type"] == "provider_call_started" and e["payload"]["turn_id"] == turn["turn_id"]
    )
    shared.require(
        sha256_json(original) == dispatch["request_hash"],
        "historical schema/settings reproduction failed",
    )
    return original, event, state


def factorial_requests(original: dict) -> tuple[dict[str, dict], dict]:
    """Pure public-input transformation; never consult task files or final workspace."""
    common = fresh.fresh_request(original)
    instructions = common["input"][0]["content"]
    common["input"][0]["content"] = (
        instructions.removesuffix(fresh.FRESH_CONTEXT_INSTRUCTIONS)
        + fresh.FRESH_CONTEXT_INSTRUCTIONS.replace(
            "Read its state directly;", "Read these top-level fields directly;"
        )
        + NOTICE
    )
    payload = json.loads(common["input"][1]["content"])
    shared.require(FIELD not in payload, "history field collision")
    past = [
        {"native_item_index": i, "content": item["content"]}
        for i, item in enumerate(original["input"])
        if item.get("role") == "developer"
    ][:-1]
    requests = {}
    for arm, profile in PROFILES.items():
        request = copy.deepcopy(common)
        request["model"] = profile.model_id
        request["input"][1]["content"] = wire(
            {**payload, FIELD: past if arm in "AC" else []}
        ).decode()
        requests[arm] = request
    # Executable factor-isolation invariants, including wire/key order, not just set equality.
    for left, right in (("A", "C"), ("B", "D")):
        shared.require(
            wire({k: v for k, v in requests[left].items() if k != "model"})
            == wire({k: v for k, v in requests[right].items() if k != "model"}),
            "model comparison changed public input",
        )
    for left, right in (("A", "B"), ("C", "D")):
        a, b = copy.deepcopy(requests[left]), copy.deepcopy(requests[right])
        for request in (a, b):
            data = json.loads(request["input"][1]["content"])
            data.pop(FIELD)
            request["input"][1]["content"] = wire(data).decode()
        shared.require(wire(a) == wire(b), "history comparison changed common information")
    return requests, {
        "common_payload_hash": sha256_bytes(wire(payload)),
        "public_archive_hash": sha256_bytes(wire(payload["public_evidence_archive"])),
        "resolved_sources_hash": sha256_bytes(wire(payload["source_bodies"])),
        "past_state_count": len(past),
        "past_state_bytes": len(wire(past)),
        "past_state_hash": sha256_bytes(wire(past)),
        "historical_reasoning_replayed": 0,
    }


def compile_requests(source_root: Path) -> tuple[dict, dict]:
    events, envelope = source_events(source_root.resolve())
    requests, cases = {}, {}
    for case, number in CASE_TURNS.items():
        original, event, state = cutoff_request(events, envelope, source_root, number)
        requests[case], metrics = factorial_requests(original)
        turn = event["payload"]
        cases[case] = {
            "source_turn_number": number,
            "source_turn_id": turn["turn_id"],
            "cutoff_event_hash": event["event_hash"],
            "source_request_hash": sha256_json(original),
            "public_state_hash": sha256_json(state),
            "current_diff_hash": state["current_diff"]["patch_hash"],
            "max_parallel_reads": turn["max_parallel_reads"],
            "read_paths": turn["targeted_read_paths"],
            "factor_isolation": metrics,
            "request_metrics": {
                a: {
                    "bytes": len(wire(r)),
                    "canonical_hash": sha256_json(r),
                    "ordered_hash": sha256_bytes(wire(r)),
                }
                for a, r in requests[case].items()
            },
        }
    metadata = {
        **shared.BOUNDARIES,
        "schema_version": SCHEMA,
        "status": "PREPARED_NOT_EXECUTABLE",
        "dispatch_enabled": False,
        "runtime_hash": shared.runtime_content_hash(),
        "source_runtime_hash": envelope["runtime_hash"],
        "source_run_id": SOURCE_ID,
        "source_journal_hash": SOURCE_HASHES[".jsonl"],
        "source_envelope_hash": SOURCE_HASHES[".envelope.json"],
        "task_id": envelope["task_id"],
        "task_version": envelope["task_version"],
        "task_content_hash": envelope["task_content_hash"],
        "sampler_hash": sampler_hash(),
        "cases": cases,
        "sampling_order": [list(cell) for cell in SCHEDULE],
        "models": {a: asdict(p) for a, p in PROFILES.items()},
        "reasoning_effort": "medium",
        "proposed_total_cap_usd": "5.00",
        "maximum_generation_calls": 16,
        "maximum_input_count_calls": 16,
        "maximum_tool_executions": 0,
        "input_token_limit": PROTOCOL.input_token_limit,
        "output_ceiling": shared.OUTPUT_CEILING,
        "pricing_hash": sha256_json(shared.protocol_prices(PROTOCOL)),
        "reviewer_files": {n: sha256_text(v) for n, v in REVIEW_FILES.items()},
    }
    return requests, metadata


def fresh_root(root: Path, *protected: Path) -> Path:
    shared.require(root.is_absolute(), "absolute output root required")
    root = root.resolve()
    shared.require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    shared.require(
        not any(
            root.is_relative_to(p.resolve()) or p.resolve().is_relative_to(root)
            for p in (*protected, shared.repository_root())
        ),
        "overlapping root",
    )
    return root


def prepare(source_root: Path, root: Path) -> dict:
    root = fresh_root(root, source_root)
    requests, metadata = compile_requests(source_root)
    root.mkdir(exist_ok=False)
    store = ArtifactStore(root)
    for name, text in REVIEW_FILES.items():
        store.write_text_immutable(root / name, text)
    packet = {
        **metadata,
        "request_artifacts": {
            case: {
                a: store.put_text(wire(r).decode(), "application/json").model_dump(mode="json")
                for a, r in arms.items()
            }
            for case, arms in requests.items()
        },
    }
    store.write_text_immutable(root / "packet.json", wire(packet).decode())
    DevJournal(root, "run_dev_model_state_prepared").append(
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
    root, store = packet_path.parent.resolve(), readonly_store(packet_path.parent.resolve())
    shared.require(set(packet["request_artifacts"]) == set(CASE_TURNS), "case set changed")
    for case, arms in requests.items():
        shared.require(set(packet["request_artifacts"][case]) == set(PROFILES), "arm set changed")
        for arm, request in arms.items():
            ref = Artifact.model_validate(packet["request_artifacts"][case][arm])
            shared.require(store.read_bytes(ref) == wire(request), "request/order changed")
    for name, digest in expected["reviewer_files"].items():
        shared.require(sha256_bytes((root / name).read_bytes()) == digest, "review changed")
    cells = tuple(
        shared.Cell(
            case,
            arm,
            wire(requests[case][arm]).decode(),
            sha256_json(requests[case][arm]),
            None,
            packet["cases"][case]["source_turn_id"],
            packet["cases"][case]["max_parallel_reads"],
            tuple(packet["cases"][case]["read_paths"]),
            repeat,
        )
        for case, arm, repeat in SCHEDULE
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
    shared._validate_collection_approval(
        plan, approval, sampler_hash(), expected_pricing_hash=plan.packet["pricing_hash"]
    )
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
                "--approve-up-to-sixteen-responses-zero-tools", action="store_true", required=True
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
                    "cases": plan.packet["cases"],
                    "sampling_order": plan.packet["sampling_order"],
                    "pricing_hash": plan.packet["pricing_hash"],
                    "provider_calls": 0,
                    "input_count_calls": 0,
                    "fresh_token_counts": None,
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
