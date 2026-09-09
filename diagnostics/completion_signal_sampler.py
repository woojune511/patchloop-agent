"""Eight independent next responses on four frozen pairs; never execute selected tools."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import completion_signal_view as view
from diagnostics import decision_sampler as shared
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig
from patchloop.dev.conversation import reconstruct_state, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SOURCE_VIEW_HASH = "sha256:068d7b62f6eaa23e9f263021a000655edc0fd1205641056e0f6e9771dc17654a"
TASK_ID = "pyfakefs-makedirs-parent-traversal"
TASK_HASH = "sha256:276b791c4c0cb1c18fa8659f6518a172f0d05b239526c0f21a7d0d2c378def87"
SCHEMA = "completion-signal-design-v1"
CHECKPOINTS = ("A1", "B1", "B2", "A2")
PROTOCOL = shared.CollectionProtocol(
    "completion-signal-sampler-v1",
    {"A": "medium", "B": "medium"},
    (
        ("C1", "A"),
        ("C1", "B"),
        ("C2", "B"),
        ("C2", "A"),
        ("C3", "A"),
        ("C3", "B"),
        ("C4", "B"),
        ("C4", "A"),
    ),
    272_000,
    reserve_future_calls=False,
)
REVIEW_FILES = {
    "protocol.md": (
        "Four matched public checkpoints; one fresh response per arm, eight maximum.\n"
        "Only the latest mutation_completion_horizon field is omitted in B.\n"
        "Keep zero mutations, current check status, tool schemas/order, native history,\n"
        "encrypted reasoning and all model settings unchanged. No output chaining,\n"
        "sampled tools, corrections, judge calls, retry/resume or private evaluation.\n"
        "One shared $1.20 cap; count immediately before each dispatch and reserve its\n"
        "full 25k output. There is no future-trajectory reserve. Missing cells are\n"
        "censored, not agent failures. Earlier forecast copies remain historical.\n"
        "Review anonymous decisions before unblinding. This is not normal row 44.\n"
    ),
    "rubric.json": canonical_json(
        {
            "grading": "NOT_ASSESSED",
            "criteria": [
                "Which offered action is selected: current-diff check, stop, or other?",
                "Does the public basis recognize current checks are NOT_RUN?",
                "Does it present a prior diff's failure or PASS as a current observed verdict?",
                "Does it equate zero further edits with no useful available action?",
            ],
            "limits": "A selected check is not an executed check, task success or causal proof.",
        }
    ),
}


def implementation_hashes() -> dict[str, str]:
    return {
        f"diagnostics/{p.name}": sha256_bytes(p.read_bytes())
        for p in sorted((Path(__file__), Path(view.__file__), Path(shared.__file__)))
    }


def sampler_hash() -> str:
    return sha256_json(implementation_hashes())


def compile_requests(view_root: Path, source_root: Path) -> tuple[dict, dict]:
    """Read the frozen public request and its journal identity, never task/worktree bytes."""
    raw = (view_root / "result.json").read_bytes()
    shared.require(sha256_bytes(raw) == SOURCE_VIEW_HASH, "prepared view receipt changed")
    receipt = json.loads(raw)
    shared.require(receipt["runtime_hash"] == shared.runtime_content_hash(), "runtime changed")
    pairs = receipt["independent_pairs"]
    shared.require(tuple(p["checkpoint"] for p in pairs) == CHECKPOINTS, "checkpoint order changed")
    envelope_raw = (source_root / "envelope.json").read_bytes()
    envelope = json.loads(envelope_raw)
    shared.require(
        (envelope["task_id"], envelope["task_version"], envelope["task_content_hash"])
        == (TASK_ID, 2, TASK_HASH)
        and envelope["model"] == shared.MODEL,
        "source task or model mismatch",
    )
    requests, checkpoints, identities, metrics = {}, [], {}, {}
    for index, pair in enumerate(pairs, 1):
        label, case = pair["checkpoint"], f"C{index}"
        packet_root = view_root / label
        shared.require(
            view.validate(packet_root)
            == {
                k: v
                for k, v in pair.items()
                if k
                not in {
                    "checkpoint",
                    "turn_id",
                    "turn_start_event_hash",
                    "count_event_hash",
                }
            },
            "view receipt mismatch",
        )
        paths = list((source_root / label / "runs").glob("*.jsonl"))
        shared.require(len(paths) == 1, "one source journal per checkpoint required")
        journal = DevJournal(source_root / label, paths[0].stem)
        events = journal.events()
        start = next(e for e in events if e["event_hash"] == pair["turn_start_event_hash"])
        count = next(e for e in events if e["event_hash"] == pair["count_event_hash"])
        shared.require(
            start["event_type"] == "turn_started"
            and count["event_type"] == "input_count_started"
            and start["sequence"] < count["sequence"]
            and start["payload"]["turn_id"] == pair["turn_id"] == count["payload"]["turn_id"],
            "source cutoff mismatch",
        )
        original = shared.read_source_artifact(
            source_root / label, count["payload"]["request_artifact"]
        )
        shared.require(
            sha256_bytes(original)
            == pair["input_hash"]
            == count["payload"]["ordered_request_hash"],
            "source request mismatch",
        )
        items = json.loads(
            shared.read_source_artifact(
                source_root / label, start["payload"]["model_input_artifact"]
            )
        )
        validate_model_input(items, start["payload"]["native_history"])
        control = json.loads(original)
        state = reconstruct_state(items)
        shared.require(
            control["input"] == items
            and (state["public_task"]["task_id"], state["public_task"]["task_version"])
            == (TASK_ID, 2),
            "source task mismatch",
        )
        shared.require(
            set(control) == set(shared.SETTINGS) | {"reasoning", "input", "tools"}
            and all(control[k] == v for k, v in shared.SETTINGS.items())
            and control["reasoning"] == {"effort": "medium"},
            "request settings changed",
        )
        read_paths = start["payload"].get("targeted_read_paths", [])
        schemas = dev_tool_schemas(
            finish_enabled="finish_task" in state["available_tool_names"],
            check_ids=[
                c["check_id"] for c in state["visible_check_status"] if c["status"] == "NOT_RUN"
            ],
            allowed_tools=state["available_tool_names"],
            read_paths=read_paths,
        )
        shared.require(control["tools"] == schemas, "tool schema or order changed")
        alternate, _ = view.without_further_edit_horizon(control)
        for arm, request in (("A", control), ("B", alternate)):
            key = f"{case}/{arm}"
            body = view.wire(request)
            shared.require(
                (packet_root / f"{arm}.json").read_bytes() == body, "prepared request bytes changed"
            )
            requests[key] = body
            metrics[key] = {
                "ordered_hash": sha256_bytes(body),
                "canonical_hash": sha256_json(request),
                "request_bytes": len(body),
            }
        checkpoints.append(
            {
                "case_id": case,
                "checkpoint": label,
                "run_id": journal.run_id,
                "source_turn_id": pair["turn_id"],
                "source_journal_hash": sha256_bytes(paths[0].read_bytes()),
                "turn_start_event_hash": start["event_hash"],
                "count_event_hash": count["event_hash"],
                "current_diff_hash": pair["current_diff_hash"],
                "max_parallel_reads": start["payload"]["max_parallel_reads"],
                "read_paths": read_paths,
            }
        )
        identities[f"{label}/manifest.json"] = sha256_bytes(
            (packet_root / "manifest.json").read_bytes()
        )
    return requests, {
        **shared.BOUNDARIES,
        "schema_version": SCHEMA,
        "status": "PREPARED_NOT_EXECUTABLE",
        "source_packet_hash": SOURCE_VIEW_HASH,
        "source_run_id": None,
        "source_journal_hash": None,
        "source_envelope_hash": sha256_bytes(envelope_raw),
        "source_checkpoints": checkpoints,
        "runtime_hash": receipt["runtime_hash"],
        "preparer_hash": sampler_hash(),
        "implementation_hashes": implementation_hashes(),
        "source_view_hashes": identities,
        "task_id": TASK_ID,
        "task_version": 2,
        "task_content_hash": TASK_HASH,
        "model": shared.MODEL,
        "reasoning_effort": "medium",
        "fixed_request_settings": shared.SETTINGS,
        "proposed_total_cap_usd": "1.20",
        "sampling_order": list(map(list, PROTOCOL.sampling_order)),
        "reserve_future_calls": False,
        "input_token_limit": PROTOCOL.input_token_limit,
        "maximum_generation_calls": 8,
        "maximum_input_count_calls": 8,
        "request_metrics": metrics,
        "reviewer_files": {
            name: sha256_bytes(body.encode()) for name, body in REVIEW_FILES.items()
        },
    }


def prepare(view_root: Path, source_root: Path, root: Path) -> dict:
    shared.require(
        all(p.is_absolute() for p in (view_root, source_root, root)), "absolute paths required"
    )
    shared.require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    shared.require(
        not any(
            root.resolve().is_relative_to(p.resolve())
            for p in (shared.repository_root(), source_root, view_root)
        ),
        "output overlaps protected root",
    )
    requests, packet = compile_requests(view_root, source_root)
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
        "provider_calls": 0,
        "input_count_calls": 0,
    }


@dataclass(frozen=True)
class SignalPlan(shared.FrozenPlan):
    view_root: Path


def load_plan(
    packet_path: Path, view_root: Path, source_root: Path, expected_hash: str
) -> SignalPlan:
    raw = packet_path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet hash mismatch")
    packet = json.loads(raw)
    requests, expected = compile_requests(view_root, source_root)
    shared.require(
        set(packet) == set(expected) | {"request_artifacts"}
        and all(packet[k] == v for k, v in expected.items()),
        "design contract mismatch",
    )
    shared.require(
        set(packet["request_artifacts"]) == set(requests), "request artifact set mismatch"
    )
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
            None,
            checkpoints[case]["source_turn_id"],
            checkpoints[case]["max_parallel_reads"],
            tuple(checkpoints[case]["read_paths"]),
            sample_number=1,
        )
        for case, arm in PROTOCOL.sampling_order
    )
    return SignalPlan(
        packet_path.resolve(),
        expected_hash,
        packet,
        cells,
        source_root.resolve(),
        {**packet["source_view_hashes"], **packet["reviewer_files"]},
        view_root.resolve(),
    )


def collect(
    plan: SignalPlan,
    approval: shared.Approval,
    *,
    adapter_factory: Callable[[ModelConfig], OpenAIResponsesAdapter] | None = None,
    clock: Callable[[], float] = monotonic,
    checkpoint: Callable[[str], None] = lambda _: None,
) -> dict:
    shared._validate_collection_approval(
        plan, approval, sampler_hash(), protected_roots=(plan.view_root,)
    )
    refreshed = load_plan(plan.packet_path, plan.view_root, plan.source_root, approval.packet_hash)
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
    inspect = commands.add_parser("inspect", help="read only; never resume")
    inspect.add_argument("--result-root", type=Path, required=True)
    for name in ("prepare", "validate", "collect"):
        command = commands.add_parser(name)
        command.add_argument("--view-root", type=Path, required=True)
        command.add_argument("--source-live-root", type=Path, required=True)
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
            result = prepare(args.view_root, args.source_live_root, args.output_root)
        else:
            plan = load_plan(args.packet, args.view_root, args.source_live_root, args.packet_hash)
            if args.command == "validate":
                result = {
                    **shared.BOUNDARIES,
                    "status": "VALIDATED_NOT_EXECUTED",
                    "packet_hash": plan.packet_hash,
                    "sampler_hash": sampler_hash(),
                    "pricing_hash": sha256_json(shared.price_identity()),
                    "sampling_order": PROTOCOL.sampling_order,
                    "provider_calls": 0,
                    "input_count_calls": 0,
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
