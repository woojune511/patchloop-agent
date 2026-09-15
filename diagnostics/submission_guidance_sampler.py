"""Latest submission recommendation versus eligibility facts; zero sampled tools.

Two public segmented checkpoints, two independent responses per arm/checkpoint.
This is a diagnostic view, not a new default prompt, workflow or continuation policy.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from diagnostics import decision_sampler as shared
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import segments
from patchloop.dev.conversation import reconstruct_state, validate_model_input
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SCHEMA = "submission-guidance-design-v1"
SOURCE_PACKET_HASH = "sha256:be99533f6a65ba7a84abd2a6df18e9e72e9ab8725e54ac14f40356c3cca839f9"
CHECKPOINTS = (("C1", "A1", 17), ("C2", "A3", 15))
BLOCKS = (("C1", 1, "AB"), ("C2", 1, "BA"), ("C1", 2, "BA"), ("C2", 2, "AB"))
SCHEDULE = tuple((case, arm, repeat) for case, repeat, arms in BLOCKS for arm in arms)
PROTOCOL = shared.CollectionProtocol(
    "submission-guidance-sampler-v1",
    {"A": "medium", "B": "medium"},
    tuple((f"{case}/{arm}", repeat) for case, arm, repeat in SCHEDULE),
    input_token_limit=60_000,
    balanced_block_size=2,
)
FACTS = (
    "All required visible checks pass on the current diff; submission is eligible, "
    "not proof of untested behavior."
)
RECOMMENDATION = FACTS + (
    " Use run_probe if a concrete remaining public uncertainty could change the edit; "
    "otherwise use finish_task to submit. No extra experiment is required."
)
REVIEW_FILES = {
    "protocol.md": (
        "Two failure-selected public checkpoints from the closed probe comparison: "
        "A1 turn17 (C1), A3 turn15 (C2). Two fresh responses per arm/checkpoint, eight max.\n"
        "A reconstructs the original request. B changes only the latest completion_guidance: "
        "next_action becomes null and message retains eligibility facts without an action "
        "recommendation. Diff binding and submission_ready remain exact.\n"
        "Keep full public task, diff, checks, sources, notes, concerns, plan, history, "
        "budgets, tools/schema order, model/medium/25k and store=false unchanged. "
        "Both selected native segments already contain zero reasoning items; no reset is added. "
        "Other instructions, old public records and model-authored submission plans remain. "
        "This does not remove every submission cue or test the whole native loop.\n"
        "Use root .env, a fresh result root, shared $1.20 cap. Reserve both arms in each "
        "pair at <=60000 input/full25000 output, count actual input immediately before "
        "dispatch, never reduce output. Stop on uncertainty; no retry/resume, correction, "
        "chaining, selected tool execution, paid judge, private evaluation or extra sample.\n"
        "Record anonymous public decisions before unblinding. A probe/read choice is not "
        "successful verification; a finish choice alone is not semantic failure. "
        "No automatic runtime adoption or live follow-up from eight responses.\n"
    ),
    "rubric.json": canonical_json(
        {
            "grading": "PUBLIC_ACTION_SELECTION_ONLY",
            "criteria": [
                "Offered tool selected and batch validity: finish, probe, inspect, edit, stop.",
                "Does the response identify a concrete unresolved public behavior?",
                "Does a proposed experiment exercise current code and discriminate an assumption?",
                "Does the response equate visible eligibility with all required behavior verified?",
                "Do plan changes preserve or omit already public unresolved concerns?",
            ],
            "success_claim": "NOT_ASSESSED; tools and candidates are never executed",
            "decision_rule": (
                "A repeated difference at both checkpoints supports further testing only; "
                "same choices, mixed outcomes or censored pairs leave the cause unresolved."
            ),
            "blinding": "Hide arm/order/cost/effort; prose may indirectly reveal the condition.",
            "task_acceptance": "NOT_RUN",
            "official": False,
        }
    ),
}


def wire(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def implementation_hashes() -> dict[str, str]:
    return {
        f"diagnostics/{p.name}": sha256_bytes(p.read_bytes())
        for p in sorted((Path(__file__), Path(shared.__file__)))
    }


def sampler_hash() -> str:
    return sha256_json(implementation_hashes())


def facts_only(request: dict) -> tuple[dict, dict]:
    """Pure, latest-field-only diagnostic transformation, with no source read."""
    items = request["input"]
    shared.require(items[-1].get("role") == "developer", "latest state required")
    record = json.loads(items[-1]["content"])
    shared.require(record.get("kind") == "harness_current_state", "current state required")
    state = record["state"]
    current = state["current_diff"]
    checks = state["visible_check_status"]
    shared.require(
        current.get("patch")
        and checks
        and all(c["status"] == "PASS" and c["diff_hash"] == current["patch_hash"] for c in checks)
        and state["workflow_gate"] == "ready_to_submit"
        and state.get("current_public_failure") is None,
        "current checked submission required",
    )
    tools = {s["name"] for s in request["tools"]}
    shared.require(
        tools == set(state["available_tool_names"])
        and {"finish_task", "run_probe", "replace_text"} <= tools,
        "affordable verification and repair required",
    )
    shared.require(
        state["remaining_budget"]["accepted_mutations"] > 0
        and state["action_horizon"]["completion_possible"],
        "completion slack required",
    )
    guidance = state["completion_guidance"]
    shared.require(
        guidance
        == {
            "diff_hash": current["patch_hash"],
            "submission_ready": True,
            "next_action": {"tool": "finish_task"},
            "message": RECOMMENDATION,
        },
        "unexpected recommendation",
    )
    changed = copy.deepcopy(request)
    guidance["next_action"] = None
    guidance["message"] = FACTS
    changed["input"][-1]["content"] = wire(record).decode()
    restored = json.loads(changed["input"][-1]["content"])
    restored["state"]["completion_guidance"] = json.loads(items[-1]["content"])["state"][
        "completion_guidance"
    ]
    shared.require(wire(restored).decode() == items[-1]["content"], "noncanonical source state")
    return changed, {
        "changed_fields": [
            "state.completion_guidance.message",
            "state.completion_guidance.next_action",
        ],
        "current_diff_hash": current["patch_hash"],
        "unchanged_prefix_hash": sha256_bytes(wire(items[:-1])),
        "original_request_bytes": len(wire(request)),
        "facts_request_bytes": len(wire(changed)),
    }


def _request(
    source_root: Path, slot: dict, turn_number: int, public_task: dict
) -> tuple[dict, dict]:
    root = Path(slot["request"]["state_root"])
    shared.require(
        root.resolve() == (source_root / "state" / slot["label"]).resolve(), "source root mismatch"
    )
    paths = list((root / "runs").glob("run_dev_*.jsonl"))
    shared.require(len(paths) == 1, "one source journal required")
    # Validation reads the existing chain; it never acquires an execution lock or appends.
    events = DevJournal(root, paths[0].stem).events()
    starts = [e for e in events if e["event_type"] == "turn_started"]
    shared.require(0 < turn_number <= len(starts), "source turn absent")
    event = starts[turn_number - 1]
    start = event["payload"]
    boundary = start["prepared_input"]
    bundle = json.loads(shared.read_source_artifact(root, boundary["artifact"]))
    items = json.loads(shared.read_source_artifact(root, start["model_input_artifact"]))
    validate_model_input(items, start["native_history"], context_policy=segments.POLICY)
    state = reconstruct_state(items, context_policy=segments.POLICY)
    dispatch = next(
        e
        for e in events
        if e["event_type"] == "provider_call_started"
        and e["payload"]["turn_id"] == start["turn_id"]
    )
    count = next(
        e
        for e in events
        if e["event_type"] == "input_count_finished"
        and e["payload"].get("count_id") == start["selected_count_id"]
    )
    shared.require(
        count["sequence"] < event["sequence"] < dispatch["sequence"]
        and bundle["turn"]["turn_id"] == boundary["boundary_id"] == start["turn_id"]
        and bundle["request"]["input"] == items
        and state["public_task"] == public_task,
        "source cutoff/task mismatch",
    )
    shared.require(
        not any(
            i.get("type") in {"reasoning", "function_call", "function_call_output"} for i in items
        ),
        "fresh recorded segment required; never reset history",
    )
    options = slot["request"]
    shared.require(
        (
            options["model"],
            options["reasoning_effort"],
            options["planning_policy"],
            options["context_policy"],
            options["probe_policy"],
            options["enable_probes"],
        )
        == (shared.MODEL, "medium", "brief-evidence-v1", segments.POLICY, "none", True),
        "source configuration mismatch",
    )
    schemas = dev_tool_schemas(
        finish_enabled=True,
        allowed_tools=start["available_tool_names"],
        check_ids=[],
        read_paths=start["targeted_read_paths"],
        planning_policy=options["planning_policy"],
        probe_policy=options["probe_policy"],
    )
    # CAS canonicalizes object keys. Recover property order with the identical frozen runtime
    # builder, rather than send sorted schemas or claim that a canonical hash is raw HTTP capture.
    request = OpenAIResponsesAdapter.request_payload(
        SimpleNamespace(config=shared.model_config("medium")),
        items,
        schemas,
        system_prompt=DEV_SYSTEM_PROMPT,
    )
    digest = sha256_json(request)
    shared.require(
        request == bundle["request"]
        and digest
        == boundary["request_hash"]
        == start["counted_request_hash"]
        == count["payload"]["request_hash"]
        == dispatch["payload"]["request_hash"]
        and count["payload"]["input_tokens"] == dispatch["payload"]["input_tokens"]
        and dispatch["payload"]["output_ceiling"] == 25000,
        "count/dispatch/request identity mismatch",
    )
    return request, {
        "checkpoint": slot["label"],
        "source_turn_number": turn_number,
        "source_turn_id": start["turn_id"],
        "run_id": paths[0].stem,
        "source_journal_hash": sha256_bytes(paths[0].read_bytes()),
        "turn_start_event_hash": event["event_hash"],
        "dispatch_event_hash": dispatch["event_hash"],
        "count_event_hash": count["event_hash"],
        "historical_input_tokens": count["payload"]["input_tokens"],
        "max_parallel_reads": start["max_parallel_reads"],
        "read_paths": start["targeted_read_paths"],
        "source_canonical_request_hash": digest,
        "original_native_reasoning_items": 0,
        "request_identity_scope": "canonical identity and builder order; not raw HTTP capture",
    }


def compile_requests(source_root: Path) -> tuple[dict, dict]:
    source = json.loads((source_root / "packet.json").read_bytes())
    shared.require(sha256_json(source) == SOURCE_PACKET_HASH, "source packet mismatch")
    frozen = source["frozen"]
    shared.require(frozen["runtime_hash"] == shared.runtime_content_hash(), "runtime changed")
    shared.require(
        (frozen["task_id"], frozen["task_version"], frozen["public_task"]["split"])
        == ("pyfakefs-makedirs-parent-traversal", 2, "dev-train"),
        "source task mismatch",
    )
    requests, checkpoints, metrics = {}, [], {}
    for case, label, turn in CHECKPOINTS:
        slot = next(s for s in source["slots"] if s["label"] == label)
        control, checkpoint = _request(source_root, slot, turn, frozen["public_task"])
        alternate, contrast = facts_only(control)
        checkpoints.append({"case_id": case, **checkpoint, **contrast})
        for arm, request in (("A", control), ("B", alternate)):
            key = f"{case}/{arm}"
            requests[key] = wire(request)
            metrics[key] = {
                "canonical_hash": sha256_json(request),
                "ordered_hash": sha256_bytes(requests[key]),
                "bytes": len(requests[key]),
            }
    return requests, {
        **shared.BOUNDARIES,
        "schema_version": SCHEMA,
        "status": "PREPARED_NOT_EXECUTABLE",
        "source_packet_hash": SOURCE_PACKET_HASH,
        "source_run_id": None,
        "source_journal_hash": None,
        "source_checkpoints": checkpoints,
        "runtime_hash": frozen["runtime_hash"],
        "preparer_hash": sampler_hash(),
        "implementation_hashes": implementation_hashes(),
        "task_id": frozen["task_id"],
        "task_version": 2,
        "task_content_hash": frozen["task_content_hash"],
        "model": shared.MODEL,
        "reasoning_effort": "medium",
        "fixed_request_settings": shared.SETTINGS,
        "proposed_total_cap_usd": "1.20",
        "collection_protocol": asdict(PROTOCOL),
        "sampling_order": [list(s) for s in SCHEDULE],
        "maximum_generation_calls": 8,
        "maximum_input_count_calls": 8,
        "request_metrics": metrics,
        "reviewer_files": {name: sha256_text(body) for name, body in REVIEW_FILES.items()},
    }


def prepare(source_root: Path, root: Path) -> dict:
    shared.require(source_root.is_absolute() and root.is_absolute(), "absolute paths required")
    shared.require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    shared.require(
        not any(
            root.resolve().is_relative_to(p.resolve()) or p.resolve().is_relative_to(root.resolve())
            for p in (shared.repository_root(), source_root)
        ),
        "output overlaps source",
    )
    requests, packet = compile_requests(source_root)
    root.mkdir()
    store = ArtifactStore(root)
    packet["request_artifacts"] = {
        k: store.put_text(v.decode(), "application/json").model_dump(mode="json")
        for k, v in requests.items()
    }
    for name, body in REVIEW_FILES.items():
        store.write_text_immutable(root / name, body)
    store.write_text_immutable(root / "packet.json", canonical_json(packet))
    return {
        **shared.BOUNDARIES,
        "status": "PREPARED_NOT_EXECUTABLE",
        "packet_hash": sha256_bytes((root / "packet.json").read_bytes()),
        "sampler_hash": sampler_hash(),
        "pricing_hash": sha256_json(shared.price_identity()),
    }


def load_plan(packet_path: Path, source_root: Path, expected_hash: str) -> shared.FrozenPlan:
    raw = packet_path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet hash mismatch")
    packet = json.loads(raw)
    requests, expected = compile_requests(source_root)
    shared.require(
        set(packet) == set(expected) | {"request_artifacts"}
        and all(packet[k] == json.loads(canonical_json(v)) for k, v in expected.items()),
        "design contract mismatch",
    )
    shared.require(set(packet["request_artifacts"]) == set(requests), "request set mismatch")
    store = ArtifactStore(packet_path.parent)
    for key, body in requests.items():
        shared.require(
            store.read_bytes(Artifact.model_validate(packet["request_artifacts"][key])) == body,
            "request artifact changed",
        )
    for name, digest in packet["reviewer_files"].items():
        shared.require(
            sha256_bytes((packet_path.parent / name).read_bytes()) == digest,
            "review contract changed",
        )
    checkpoints = {c["case_id"]: c for c in packet["source_checkpoints"]}
    cells = tuple(
        shared.Cell(
            case,
            arm,
            requests[f"{case}/{arm}"].decode(),
            packet["request_metrics"][f"{case}/{arm}"]["canonical_hash"],
            checkpoints[case]["historical_input_tokens"],
            checkpoints[case]["source_turn_id"],
            checkpoints[case]["max_parallel_reads"],
            tuple(checkpoints[case]["read_paths"]),
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
        {**packet["implementation_hashes"], **packet["reviewer_files"]},
    )


def collect(plan, approval, *, adapter_factory=None, clock=monotonic, checkpoint=lambda _: None):
    shared._validate_collection_approval(plan, approval, sampler_hash())
    refreshed = load_plan(plan.packet_path, plan.source_root, approval.packet_hash)
    shared.require(refreshed.design_hashes == plan.design_hashes, "design changed")
    return shared._collect_validated(
        refreshed,
        approval,
        protocol=PROTOCOL,
        adapter_factory=adapter_factory,
        clock=clock,
        checkpoint=checkpoint,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="read only; never resume/recollect")
    inspect.add_argument("--result-root", type=Path, required=True)
    for name in ("prepare", "validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--source-root", type=Path, required=True)
        if name == "prepare":
            command.add_argument("--output-root", type=Path, required=True)
        else:
            command.add_argument("--packet", type=Path, required=True)
            command.add_argument("--packet-hash", required=True)
        if name == "collect":
            command.add_argument(
                "--approve-eight-responses-zero-tools", action="store_true", required=True
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
        elif args.command == "prepare":
            result = prepare(args.source_root, args.output_root)
        else:
            plan = load_plan(args.packet, args.source_root, args.packet_hash)
            if args.command == "validate":
                result = {
                    **shared.BOUNDARIES,
                    "status": "VALIDATED_NOT_EXECUTED",
                    "packet_hash": plan.packet_hash,
                    "sampler_hash": sampler_hash(),
                    "pricing_hash": sha256_json(shared.price_identity()),
                    "source_checkpoints": plan.packet["source_checkpoints"],
                }
            else:
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
