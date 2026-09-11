"""Blind public-action assessment followed by a separate read-only unblinding report.

Only exact sampled replacements and registered public checks/inspections may execute,
in fresh copies. No model, probe, finish, private evaluator or source-run write path.
"""

from __future__ import annotations

import argparse
import copy
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

from diagnostics import decision_sampler as shared
from diagnostics import model_state_sampler as design
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.runner import _live_sandbox_preflight, _requested_tool_from_openai
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, validate_tool_batch
from patchloop.repository import WorkspaceManager, run_git
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

BOUNDARIES = {
    "official": False,
    "claim_eligible": False,
    "task_acceptance": "NOT_RUN",
    "safety_state": "NOT_RUN",
    "hidden_evaluator": "NOT_RUN",
    "provider_calls": 0,
    "original_agent_check_credit": False,
    "resume_allowed": False,
}


def read_json(store: ArtifactStore, ref: dict) -> dict:
    return json.loads(store.read_bytes(Artifact.model_validate(ref)))


def collection(plan: shared.FrozenPlan, root: Path):
    """Bind anonymous artifacts back to the exact completed collection, read-only."""
    envelope = json.loads((root / "envelope.json").read_bytes())
    shared.require(
        envelope["kind"] == design.PROTOCOL.kind
        and envelope["packet_hash"] == plan.packet_hash
        and envelope["sampler_hash"] == design.sampler_hash(),
        "collection mismatch",
    )
    store = design.readonly_store(root)
    journal = DevJournal(root, envelope["run_id"])
    events = journal.events()
    shared.require(
        read_json(store, events[0]["payload"]["envelope_artifact"]) == envelope,
        "collection envelope mismatch",
    )
    result = json.loads((root / "result.json").read_bytes())
    shared.require(
        journal.terminal() is not None and journal.terminal()["payload"] == result,
        "durable collection terminal required",
    )
    review = read_json(store, result["review_artifact"])
    records = [e["payload"] for e in events if e["event_type"] == "sample_recorded"]
    shared.require(
        len(records) == result["sample_count"] == len(review["samples"])
        and len(records) <= len(plan.cells),
        "sample inventory mismatch",
    )
    mapping = {}
    for record, cell in zip(records, plan.cells, strict=False):
        shared.require(
            (record["case_id"], record["arm"], record["sample_number"])
            == (cell.case_id, cell.arm, cell.sample_number)
            and record["request_hash"] == cell.request_hash,
            "sample schedule mismatch",
        )
        mapping[record["sample_id"]] = record
    shared.require(
        len(mapping) == len(records)
        and set(mapping) == {s["anonymous_sample_id"] for s in review["samples"]},
        "duplicate/missing anonymous sample",
    )
    for sample in review["samples"]:
        shared.require(
            sample["public_artifact"] == mapping[sample["anonymous_sample_id"]]["public_artifact"],
            "anonymous artifact changed",
        )
    return store, result, review["samples"], events


def import_evidence(value, source: ArtifactStore, target: ArtifactStore):
    if isinstance(value, list):
        return [import_evidence(v, source, target) for v in value]
    if not isinstance(value, dict):
        return value
    if {
        "artifact_id",
        "content_hash",
        "path",
        "size_bytes",
        "media_type",
        "created_at",
    } <= value.keys():
        ref = Artifact.model_validate(value)
        copied = target.put_bytes(source.read_bytes(ref), ref.media_type)
        return ref.model_copy(update={"path": copied.path}).model_dump(mode="json")
    return {k: import_evidence(v, source, target) for k, v in value.items()}


def clone_checkpoint(plan, state, directory, store, deadline):
    source_repo = plan.source_root / "workspaces" / plan.packet["source_run_id"] / "repo"
    shared.require(
        source_repo.is_dir() and not source_repo.is_symlink(), "source repository absent"
    )
    directory.parent.mkdir(parents=True, exist_ok=True)
    run_git(
        directory.parent,
        "clone",
        "--quiet",
        "--no-hardlinks",
        "--no-checkout",
        str(source_repo),
        str(directory),
        deadline=deadline,
    )
    run_git(directory, "config", "core.longpaths", "true", deadline=deadline)
    run_git(
        directory,
        "checkout",
        "--quiet",
        "--detach",
        state["public_task"]["repository"]["base_commit"],
        deadline=deadline,
    )
    patch = store.put_text(state["current_diff"]["patch"], "text/x-diff")
    if state["current_diff"]["patch"]:
        WorkspaceManager.apply_patch(directory, Path(patch.path), deadline=deadline)
    for group in state["source_bodies"]:
        path = ensure_within(directory, group["path"])
        shared.require(path.is_file() and not path.is_symlink(), "source file missing")
        raw = path.read_bytes()
        if sha256_bytes(raw) != group["file_hash"]:
            # Git's host autocrlf setting can change checkout bytes. Only restore a
            # newline variant that proves the *entire* original raw-byte identity.
            # This never imports the final source worktree or unobserved source text.
            lf = raw.replace(b"\r\n", b"\n")
            matches = {
                v for v in (lf, lf.replace(b"\n", b"\r\n")) if sha256_bytes(v) == group["file_hash"]
            }
            shared.require(len(matches) == 1, "source bytes mismatch")
            path.write_bytes(matches.pop())
    summary = WorkspaceManager.diff_summary(directory, deadline=deadline)
    shared.require(
        summary.patch_hash == state["current_diff"]["patch_hash"] and not summary.untracked_files,
        "checkpoint diff mismatch",
    )


def gateway_at(plan, case, payload, prefix, root, workspace, public_task, sandbox, deadline):
    store = ArtifactStore(root / "artifacts")
    clone_checkpoint(plan, payload, workspace, store, deadline)
    journal = DevJournal(root, f"run_dev_assess_{uuid.uuid4().hex[:16]}")
    source = design.readonly_store(plan.source_root / "artifacts")
    journal.append(
        "diagnostic_checkpoint",
        {
            **BOUNDARIES,
            "case_id": case,
            "source_cutoff": plan.packet["cases"][case]["cutoff_event_hash"],
        },
    )
    for event in prefix:
        if event["event_type"] in {"action_started", "action_finished", "working_notes_updated"}:
            inherited = import_evidence(event["payload"], source, store)
            journal.append(
                event["event_type"],
                {
                    **inherited,
                    "diagnostic_inherited": True,
                    "source_event_hash": event["event_hash"],
                },
            )
    return DevToolGateway(
        workspace=workspace,
        public_task=public_task,
        sandbox=sandbox,
        journal=journal,
        limits=DevLimits(),
        deadline=deadline,
    )


def assess_sample(
    public: dict,
    payload: dict,
    gateway,
    store,
    cache,
    case: str,
    *,
    max_parallel_reads: int = 4,
    read_paths: tuple[str, ...] = (),
) -> dict:
    """No condition/model argument; freeze observable facts, never grade persuasive prose."""
    observation = {
        **BOUNDARIES,
        "anonymous_sample_id": public["anonymous_sample_id"],
        "case_id": case,
        "action_kinds": [c.get("name") for c in public["tool_calls"]],
        "batch_valid": False,
        "mutation_admission": "NOT_RUN",
        "mutation_quality": "NOT_ASSESSED",
        "checks": [],
        "new_regressions": [],
        "regression_assessment": "NOT_ASSESSED",
        "diagnostic_tool_executions": 0,
        "error_code": public.get("error_code"),
    }
    if public.get("error_code"):
        return observation
    try:
        calls = [_requested_tool_from_openai(SimpleNamespace(**c)) for c in public["tool_calls"]]
        validate_tool_batch(
            calls,
            allowed_tools=set(payload["available_tool_names"]),
            max_parallel_reads=max_parallel_reads,
            allowed_read_paths=read_paths,
        )
    except (ValueError, TypeError, shared.ContractError) as exc:
        observation["contract_error_type"] = type(exc).__name__
        return observation
    observation["batch_valid"] = True
    if all(c.name in {"read_file", "search_files"} for c in calls):
        # Validity/relevance are separate: execute bounded inspection without another model turn.
        results = [
            gateway.execute(c.model_copy(update={"action_id": f"diag_inspect_{uuid.uuid4().hex}"}))
            for c in calls
        ]
        observation.update(
            inspection_valid=all(r.status == "succeeded" for r in results),
            inspection_results=[
                store.put_json(r.model_dump(mode="json")).model_dump(mode="json") for r in results
            ],
            diagnostic_tool_executions=len(results),
            inspection_relevance="HUMAN_PUBLIC_CODE_REVIEW; not inferred from validity",
        )
        return observation
    if calls[0].name != "replace_text":
        observation["action_execution"] = "NOT_RUN; not a mutation or inspection"
        return observation
    proposal = calls[0].model_copy(update={"action_id": f"diag_mutation_{uuid.uuid4().hex}"})
    result = gateway.execute(proposal)
    observation["diagnostic_tool_executions"] = 1
    observation["mutation_admission"] = "PASS" if result.status == "succeeded" else "FAIL"
    observation["mutation_result"] = store.put_json(result.model_dump(mode="json")).model_dump(
        mode="json"
    )
    if result.status != "succeeded":
        return observation
    candidate = gateway.current_diff
    observation.update(
        candidate_hash=candidate.patch_hash,
        changed_files=candidate.changed_files,
        diff_lines=candidate.diff_lines,
        candidate_artifact=store.put_text(candidate.patch, "text/x-diff").model_dump(mode="json"),
    )
    key = (case, candidate.patch_hash)
    if key in cache:
        observation["checks"] = copy.deepcopy(cache[key])
        observation["check_cache_hit"] = True
    else:
        observation["check_cache_hit"] = False
        for check in gateway.public_task.visible_checks:
            call = RequestedTool(
                name="run_check",
                action_id=f"diag_check_{uuid.uuid4().hex}",
                arguments={"check_id": check.id},
                turn_decision=PublicTurnDecision(
                    mode="verify",
                    basis="Independent public diagnostic check; not an agent decision.",
                ),
            )
            gateway.journal.append(
                "diagnostic_check_started", {**BOUNDARIES, "action_id": call.action_id}
            )
            checked = gateway.execute(call)
            output = checked.output
            infrastructure = (
                checked.status != "succeeded"
                or output.get("deadline_exhausted")
                or output.get("cleanup_failed")
            )
            status = "ERROR" if infrastructure else "PASS" if output.get("passed") else "FAIL"
            observation["checks"].append(
                {
                    "check_id": check.id,
                    "status": status,
                    "diff_hash": candidate.patch_hash,
                    "evidence": store.put_json(checked.model_dump(mode="json")).model_dump(
                        mode="json"
                    ),
                }
            )
            observation["diagnostic_tool_executions"] += 1
            if infrastructure:
                observation["infrastructure_error"] = True
                return observation
        cache[key] = copy.deepcopy(observation["checks"])
    historical = {c["check_id"]: c["status"] for c in payload["visible_check_status"]}
    observation["new_regressions"] = [
        c["check_id"]
        for c in observation["checks"]
        if c["status"] == "FAIL" and historical.get(c["check_id"]) == "PASS"
    ]
    observation["regression_assessment"] = "DECLARED_PREVIOUSLY_PASS_CHECKS_ONLY"
    observation["mutation_quality"] = (
        "PUBLIC_CHECKS_PASS"
        if all(c["status"] == "PASS" for c in observation["checks"])
        else "PUBLIC_CHECKS_FAIL"
    )
    return observation


def evaluate(
    plan,
    collection_root: Path,
    output_root: Path,
    scratch_root: Path,
    task_root: Path,
    *,
    sandbox=None,
    deadline=None,
    checkpoint=lambda _: None,
) -> dict:
    plan = design.load_plan(plan.packet_path, plan.source_root, plan.packet_hash)
    source_store, receipt, samples, _ = collection(plan, collection_root)
    output_root = design.fresh_root(
        output_root, plan.source_root, plan.packet_path.parent, collection_root
    )
    scratch_root = design.fresh_root(
        scratch_root, plan.source_root, plan.packet_path.parent, collection_root, output_root
    )
    package = load_task_package(
        task_root
    )  # Host-only identity validation; never load a hidden evaluator.
    shared.require(
        package.task_content_hash == plan.packet["task_content_hash"]
        and package.public.task_id == plan.packet["task_id"]
        and package.public.task_version == plan.packet["task_version"],
        "task package mismatch",
    )
    deadline = deadline or ExecutionDeadline.from_remaining(1800)
    sandbox = sandbox or _live_sandbox_preflight(package, deadline=deadline)
    events, envelope = design.source_events(plan.source_root)
    cases = {}
    for case, number in design.CASE_TURNS.items():
        original, event, _ = design.cutoff_request(events, envelope, plan.source_root, number)
        payload = json.loads(design.factorial_requests(original)[0]["B"]["input"][1]["content"])
        shared.require(
            payload["public_task"] == package.public.model_dump(mode="json"), "public task mismatch"
        )
        cases[case] = (payload, events[: event["sequence"] - 1])
    output_root.mkdir(exist_ok=False)
    scratch_root.mkdir(exist_ok=False)
    store = ArtifactStore(output_root)
    journal = DevJournal(output_root, f"run_dev_blind_{uuid.uuid4().hex[:16]}")
    binding = {
        **BOUNDARIES,
        "kind": "model-state-public-assessment-v1",
        "packet_hash": plan.packet_hash,
        "sampler_hash": design.sampler_hash(),
        "collection_result_hash": sha256_json(receipt),
        "task_content_hash": package.task_content_hash,
        "backend": sandbox.backend,
        "source_state_root": str(plan.source_root),
        "scratch_root": str(scratch_root),
    }
    store.write_text_immutable(output_root / "envelope.json", canonical_json(binding))
    observations, cache = [], {}
    terminal = "BLIND_OBSERVATIONS_FROZEN"
    error_type = None
    try:
        for index, sample in enumerate(samples):
            deadline.check()
            public = read_json(source_store, sample["public_artifact"])
            case = sample["case_id"]
            shared.require(
                public["case_id"] == case
                and public["anonymous_sample_id"] == sample["anonymous_sample_id"],
                "sample content mismatch",
            )
            payload, prefix = cases[case]
            gateway = gateway_at(
                plan,
                case,
                payload,
                prefix,
                output_root / f"sample_{index}",
                scratch_root / f"s{index}" / "repo",
                package.public,
                sandbox,
                deadline,
            )
            limits = plan.packet["cases"][case]
            row = assess_sample(
                public,
                payload,
                gateway,
                store,
                cache,
                case,
                max_parallel_reads=limits["max_parallel_reads"],
                read_paths=tuple(limits["read_paths"]),
            )
            ref = store.put_json(row)
            journal.append(
                "anonymous_observation_recorded", {"observation": ref.model_dump(mode="json")}
            )
            observations.append(ref.model_dump(mode="json"))
            checkpoint("observation_recorded")
            if row.get("infrastructure_error"):
                terminal = "ASSESSMENT_ERROR"
                break
    except (Exception, KeyboardInterrupt) as exc:
        terminal, error_type = "ASSESSMENT_ERROR", type(exc).__name__
    result = {
        **binding,
        "terminal": terminal,
        "error_type": error_type,
        "observations": observations,
        "unassessed_samples": len(samples) - len(observations),
        "blind_to": ["condition", "model", "tokens", "cost"],
        "journal_run_id": journal.run_id,
    }
    journal.append("terminal", result)
    store.write_text_immutable(output_root / "result.json", canonical_json(result))
    return result


def report(plan, collection_root: Path, assessment_root: Path) -> dict:
    """Read-only; refuses to unblind until anonymous observations are durably frozen."""
    _, receipt, _, events = collection(plan, collection_root)
    store = design.readonly_store(assessment_root)
    result = json.loads((assessment_root / "result.json").read_bytes())
    journal = DevJournal(assessment_root, result["journal_run_id"])
    shared.require(
        journal.terminal()["payload"] == result
        and result["packet_hash"] == plan.packet_hash
        and result["collection_result_hash"] == sha256_json(receipt)
        and result["sampler_hash"] == design.sampler_hash(),
        "assessment identity mismatch",
    )
    observations = [read_json(store, ref) for ref in result["observations"]]
    mapping = {
        e["payload"]["sample_id"]: e["payload"]
        for e in events
        if e["event_type"] == "sample_recorded"
    }
    usage = {
        e["payload"]["sample_id"]: e["payload"]
        for e in events
        if e["event_type"] == "provider_call_finished"
    }
    rows = []
    for row in observations:
        sample = row["anonymous_sample_id"]
        metadata, cost = mapping[sample], usage[sample]
        rows.append(
            {
                **row,
                "condition": metadata["arm"],
                "repetition": metadata["sample_number"],
                "model": cost["response_model"],
                **{
                    k: cost[k]
                    for k in (
                        "input_tokens",
                        "cached_input_tokens",
                        "output_tokens",
                        "reasoning_output_tokens",
                        "cost_nanos",
                    )
                },
            }
        )
    return {
        **BOUNDARIES,
        "status": "UNBLINDED_PUBLIC_DIAGNOSTIC",
        "rows": rows,
        "collection_terminal": receipt["terminal"],
        "assessment_terminal": result["terminal"],
        "uncollected_cells": receipt["uncollected_cells"],
        "unassessed_samples": result["unassessed_samples"],
        "interpretation": (
            "Compare repeated directions at both cutoffs; no automatic causal verdict. "
            "Missing/unevaluable cells are censored, not failed mutations. "
            "No paid follow-up authorized."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate", "report"))
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--packet-hash", required=True)
    parser.add_argument("--source-state-root", type=Path, required=True)
    parser.add_argument("--collection-root", type=Path, required=True)
    parser.add_argument("--assessment-root", type=Path, required=True)
    parser.add_argument("--scratch-root", type=Path)
    parser.add_argument("--task", type=Path)
    parser.add_argument("--approve-public-checks", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = design.load_plan(args.packet, args.source_state_root, args.packet_hash)
        if args.command == "evaluate":
            shared.require(
                args.approve_public_checks and args.scratch_root and args.task,
                "exact public-check execution approval required",
            )
            result = evaluate(
                plan, args.collection_root, args.assessment_root, args.scratch_root, args.task
            )
        else:
            result = report(plan, args.collection_root, args.assessment_root)
        print(canonical_json(result))
        return 1 if result.get("terminal") == "ASSESSMENT_ERROR" else 0
    except Exception as exc:
        print(
            canonical_json(
                {**BOUNDARIES, "status": "PREFLIGHT_REJECTED", "error_type": type(exc).__name__}
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
