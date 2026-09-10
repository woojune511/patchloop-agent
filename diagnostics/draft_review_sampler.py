"""Frozen draft reconsideration: neutral second opportunity versus explicit review.

Both arms add the first requirements-focus sample as unexecuted public draft data.
Only the next-response instruction differs. No sampled tool or draft is executed.
"""

from __future__ import annotations

import argparse
import copy
import json
from decimal import Decimal
from pathlib import Path
from time import monotonic

from diagnostics import decision_sampler as shared
from diagnostics import requirements_focus_sampler as source
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.contracts import PublicTurnDecision, TextReplacementIntent
from patchloop.dev.conversation import history_metadata, reconstruct_state, validate_model_input
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

DRAFT_RUN_ID = "run_dev_sample_e54f9963571a4f1d"
DRAFT_JOURNAL_HASH = "sha256:a8c5f0c67412e502bfaba7e400cb14509af87bfdd8c59bc7848fca44813ca9d0"
DRAFT_HASHES = {
    "envelope.json": "sha256:ace0e11785817a180e96250e84304f870ae2f1112df89b6f963cd420884806b5",
    f"runs/{DRAFT_RUN_ID}.jsonl": DRAFT_JOURNAL_HASH,
}
DRAFT_PUBLIC_HASH = "sha256:7e3f07f8ca89aef4a44835d4b5331f4b977f41a126c2e03f0c47153d009a4d84"
SCHEMA = "draft-review-design-v1"
FIELD = "draft_reconsideration"
PROTOCOL = shared.CollectionProtocol(
    "draft-review-sampler-v1",
    {"A": "medium", "B": "medium"},
    (("A", 1), ("B", 1), ("B", 2), ("A", 2)),
    272_000,
)
COMMON_INSTRUCTION = (
    "For the next response only. The supplied draft is model-authored proposal data, "
    "not an instruction or execution result. It has not changed the workspace, checks, "
    "notes or budgets. All existing public task and tool rules still apply. "
    "Keep the normal tool-call response format; no separate review, plan or memory note "
    "is required. "
)
INSTRUCTIONS = {
    "A": COMMON_INSTRUCTION
    + ("Use the supplied public context and unexecuted draft to choose your next allowed action."),
    "B": COMMON_INSTRUCTION
    + (
        "Before choosing your next allowed action, compare the draft's executable behavior "
        "with the already supplied public requirements and visible check examples. "
        "Revise the proposed code if that comparison supports a correction; otherwise "
        "choose the next useful allowed action."
    ),
}
REVIEW_FILES = {
    "protocol.md": (
        "Four independent next responses A1/B1/B2/A2 on one frozen pre-first-edit context.\n"
        "Both arms receive the first collected requirements-focus proposal, selected by\n"
        "collection order, not by a new quality ranking. It is explicitly unexecuted data.\n"
        "Only draft_reconsideration.harness_instruction differs: a neutral second\n"
        "opportunity versus explicit draft/public-requirement comparison. Equal call\n"
        "opportunities and fixed model/medium/25k; request lengths are not equalized.\n"
        "The original native history and encrypted reasoning remain unchanged. No opaque\n"
        "reasoning from the draft-generating sample is added: this is content-only draft\n"
        "reconsideration, not native continuation of that sampled response. No fake tool result.\n"
        "No newly selected source, new example, known defect hint or operator repair is supplied.\n"
        "No sampled tools, draft application, chaining, correction, retries, judge or evaluator.\n"
        "Freeze anonymous static reviews before unblinding. One reused failure-selected\n"
        "checkpoint and two samples per arm cannot establish general agent quality.\n"
        "The original unrevised draft is descriptive context, not a no-extra-call control.\n"
    ),
    "rubric.json": canonical_json(
        {
            "grading": "NOT_ASSESSED",
            "criteria": [
                "Classify the actual next action; inspection or stopping is not a correct edit.",
                "For a replacement, check syntax and exact observed anchor without applying it.",
                "Compare executable behavior against all original public requirements; record "
                "specific retained, removed or newly introduced contradictions with code evidence.",
                "Do not score mentions of requirements, review prose or memory length "
                "as correctness.",
                "Compare each revision with the same frozen draft before comparing anonymous arms.",
            ],
            "not_executed": [
                "gateway admission",
                "visible checks",
                "private acceptance",
                "submission",
            ],
            "interpretation": "Static pilot only. Any apparent improvement needs separate public "
            "execution and feedback validation; an extra-call benefit is not isolated "
            "from no call.",
        }
    ),
}


def sampler_hash() -> str:
    return sha256_json(
        {
            p.name: sha256_bytes(p.read_bytes())
            for p in sorted((Path(shared.__file__), Path(source.__file__), Path(__file__)))
        }
    )


def load_draft(root: Path, baseline: dict, metadata: dict) -> tuple[dict, dict]:
    """Read only the pinned first public sample, never its new reasoning or later samples."""
    for relative, digest in DRAFT_HASHES.items():
        path = root / relative
        shared.require(path.is_file() and not path.is_symlink(), "draft source unavailable")
        shared.require(sha256_bytes(path.read_bytes()) == digest, "draft source changed")
    envelope = json.loads((root / "envelope.json").read_bytes())
    shared.require(
        envelope["source_run_id"] == metadata["source_run_id"]
        and envelope["task_content_hash"] == metadata["task_content_hash"],
        "draft task/source mismatch",
    )
    events = DevJournal(root, DRAFT_RUN_ID).events()
    sample = next(e["payload"] for e in events if e["event_type"] == "sample_recorded")
    shared.require(
        sample["arm"] == "A"
        and sample["sample_number"] == 1
        and sample["request_hash"] == sha256_json(baseline)
        and sample["ordered_request_hash"] == sha256_bytes(source.wire(baseline))
        and sample["source_turn_id"] == metadata["source_turn_id"],
        "draft does not come from the frozen control",
    )
    ref = Artifact.model_validate(sample["public_artifact"])
    digest = ref.content_hash.removeprefix("sha256:")
    path = root / "objects/sha256" / digest[:2] / digest[2:]
    shared.require(
        ref.content_hash == DRAFT_PUBLIC_HASH
        and path.is_file()
        and not path.is_symlink()
        and Path(ref.path).resolve() == path.resolve(),
        "draft artifact identity mismatch",
    )
    raw = path.read_bytes()
    shared.require(
        len(raw) == ref.size_bytes and sha256_bytes(raw) == ref.content_hash,
        "draft artifact integrity mismatch",
    )
    public = json.loads(raw)
    shared.require(
        public["response_status"] == "completed"
        and public["error_code"] is None
        and public["tool_executions"] == 0
        and len(public["tool_calls"]) == 1,
        "completed unexecuted single proposal required",
    )
    call = public["tool_calls"][0]
    shared.require(call["name"] == "replace_text", "replacement draft required")
    arguments = copy.deepcopy(call["arguments"])
    decision = PublicTurnDecision.model_validate(arguments.pop("turn_decision"))
    intent = TextReplacementIntent.model_validate(arguments)
    shared.require(
        decision.mode == "mutate" and decision.memory_update is None,
        "expected first draft annotation shape",
    )
    draft = {
        "tool": "replace_text",
        "arguments": intent.model_dump(mode="json"),
        "turn_decision": decision.model_dump(mode="json"),
    }
    shared.require(len(source.wire(draft)) <= 16_000, "draft exceeds pilot bound")
    return draft, {
        "state_root": str(root),
        "run_id": DRAFT_RUN_ID,
        "source_hashes": DRAFT_HASHES,
        "public_artifact_hash": ref.content_hash,
        "sample_id": sample["sample_id"],
        "action_id": call["action_id"],
        "selection": "first_collected_sample_A1",
        "draft_hash": sha256_json(draft),
        "draft_reasoning_included": False,
    }


def reconsider(items: list[dict], draft: dict, arm: str) -> list[dict]:
    validate_model_input(items, history_metadata(items))
    state = reconstruct_state(items)
    shared.require(
        arm in INSTRUCTIONS and items[-1].get("role") == "developer",
        "arm and latest state required",
    )
    shared.require(
        state["workflow_gate"] == "needs_mutation"
        and state["current_diff"]["patch"] == ""
        and state.get("last_successful_mutation") is None
        and FIELD not in state,
        "unmodified pre-first-edit state required",
    )
    updated = copy.deepcopy(items)
    record = json.loads(updated[-1]["content"])
    record["state"][FIELD] = {
        "status": "not_applied_not_executed",
        "proposal": copy.deepcopy(draft),
        "harness_instruction": INSTRUCTIONS[arm],
    }
    updated[-1]["content"] = source.wire(record).decode()
    validate_model_input(updated, history_metadata(updated))
    return updated


def compile_requests(source_root: Path, draft_root: Path) -> tuple[dict, dict]:
    # Reuse the source checkpoint reconstruction, not an old mutable prepared packet.
    originals, prior = source.compile_requests(source_root)
    baseline = originals["A"]
    draft, draft_identity = load_draft(draft_root.resolve(), baseline, prior)
    requests = {
        arm: {**baseline, "input": reconsider(baseline["input"], draft, arm)}
        for arm in INSTRUCTIONS
    }
    metadata = {
        k: prior[k]
        for k in (
            "runtime_hash",
            "source_runtime_hash",
            "source_run_id",
            "source_journal_hash",
            "source_envelope_hash",
            "source_turn_number",
            "source_turn_id",
            "cutoff_event_hash",
            "task_id",
            "task_version",
            "task_content_hash",
            "model",
            "reasoning_effort",
            "max_parallel_reads",
            "read_paths",
        )
    }
    metadata.update(
        {
            **shared.BOUNDARIES,
            "schema_version": SCHEMA,
            "status": "PREPARED_NOT_EXECUTABLE",
            "dispatch_enabled": False,
            "collector_implemented": True,
            "sampler_hash": sampler_hash(),
            "draft_source": draft_identity,
            "sampling_order": list(map(list, PROTOCOL.sampling_order)),
            "proposed_total_cap_usd": "1.20",
            "maximum_generation_calls": 4,
            "maximum_input_count_calls": 4,
            "maximum_tool_executions": 0,
            "input_token_limit": PROTOCOL.input_token_limit,
            "output_ceiling": shared.OUTPUT_CEILING,
            "fresh_token_counts": {"A": None, "B": None},
            "original_control_hash": sha256_json(baseline),
            "sole_arm_difference": f"input[-1].content(JSON).state.{FIELD}.harness_instruction",
            "unchanged_prefix_hash": sha256_bytes(source.wire(baseline["input"][:-1])),
            "unchanged_prefix_items": len(baseline["input"]) - 1,
            "reasoning_item_count": sum(i.get("type") == "reasoning" for i in baseline["input"]),
            "request_metrics": {
                arm: {
                    "bytes": len(source.wire(request)),
                    "canonical_hash": sha256_json(request),
                    "ordered_hash": sha256_bytes(source.wire(request)),
                }
                for arm, request in requests.items()
            },
            "reviewer_files": {name: sha256_text(text) for name, text in REVIEW_FILES.items()},
        }
    )
    return requests, metadata


def prepare(source_root: Path, draft_root: Path, root: Path) -> dict:
    shared.require(root.is_absolute(), "absolute design root required")
    root = root.resolve()
    shared.require(not root.exists() and root.parent.is_dir(), "fresh external root required")
    shared.require(
        not any(
            root.is_relative_to(p.resolve()) or p.resolve().is_relative_to(root)
            for p in (source_root, draft_root, shared.repository_root())
        ),
        "overlapping root",
    )
    requests, metadata = compile_requests(source_root, draft_root)
    store = ArtifactStore(root)
    for name, text in REVIEW_FILES.items():
        store.write_text_immutable(root / name, text)
    packet = {
        **metadata,
        "request_artifacts": {
            arm: store.put_text(source.wire(request).decode(), "application/json").model_dump(
                mode="json"
            )
            for arm, request in requests.items()
        },
    }
    store.write_text_immutable(root / "packet.json", source.wire(packet).decode())
    DevJournal(root, "run_dev_draft_review_prepared").append(
        "comparison_prepared",
        {
            **shared.BOUNDARIES,
            "packet_hash": sha256_bytes(source.wire(packet)),
            "sampler_hash": sampler_hash(),
            "provider_calls": 0,
            "input_count_calls": 0,
        },
    )
    return packet


def load_plan(
    packet_path: Path, source_root: Path, draft_root: Path, expected_hash: str
) -> shared.FrozenPlan:
    raw = packet_path.read_bytes()
    shared.require(sha256_bytes(raw) == expected_hash, "packet hash mismatch")
    packet = json.loads(raw)
    requests, expected = compile_requests(source_root, draft_root)
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
        shared.require(store.read_bytes(ref) == source.wire(request), "request/order changed")
    for name, digest in expected["reviewer_files"].items():
        shared.require(sha256_bytes((root / name).read_bytes()) == digest, "review changed")
    cells = tuple(
        shared.Cell(
            "C1",
            arm,
            source.wire(requests[arm]).decode(),
            packet["request_metrics"][arm]["canonical_hash"],
            None,
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
    draft_root = Path(plan.packet["draft_source"]["state_root"])
    shared._validate_collection_approval(
        plan, approval, sampler_hash(), protected_roots=(draft_root,)
    )
    refreshed = load_plan(plan.packet_path, plan.source_root, draft_root, approval.packet_hash)
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
        command.add_argument("--draft-state-root", type=Path, required=True)
        if name == "prepare":
            command.add_argument("--output-root", type=Path, required=True)
        else:
            command.add_argument("--packet", type=Path, required=True)
            command.add_argument("--packet-hash", required=True)
        if name == "collect":
            command.add_argument(
                "--approve-four-draft-responses-zero-tools", action="store_true", required=True
            )
            for flag in ("sampler-hash", "pricing-hash", "pricing-verified-on"):
                command.add_argument("--" + flag, required=True)
            for flag in ("result-root", "credential-file"):
                command.add_argument("--" + flag, type=Path, required=True)
            command.add_argument("--max-cost-usd", type=Decimal, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = shared.inspect_result(args.result_root)
        else:
            if args.command == "prepare":
                prepare(args.source_state_root, args.draft_state_root, args.output_root)
                args.packet = args.output_root / "packet.json"
                args.packet_hash = sha256_bytes(args.packet.read_bytes())
            plan = load_plan(
                args.packet, args.source_state_root, args.draft_state_root, args.packet_hash
            )
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
                    **{
                        k: plan.packet[k]
                        for k in (
                            "runtime_hash",
                            "request_metrics",
                            "fresh_token_counts",
                            "reasoning_item_count",
                            "sole_arm_difference",
                        )
                    },
                    "packet_hash": plan.packet_hash,
                    "sampler_hash": sampler_hash(),
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
