"""Prepare one operator-assisted public-counterexample revision, not a fresh solve."""
from __future__ import annotations

import argparse
import copy
import json
import time
from contextlib import contextmanager
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from diagnostics import counterexample_packet as packet_api
from diagnostics import first_reproduction_comparison as original
from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics import post_reproduction_repair as post
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.checkpoint_envelope import read_checkpoint_envelope
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ProbeDependencyIdentity
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.prepared_probe_dependencies import load_dependencies
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "public-counterexample-repair-v1"
FIELD = "operator_public_counterexamples"
RESERVED_ACTIONS = 1
RESERVED_SECONDS = 35
INSTRUCTION = (
    "An operator supplied additional public counterexamples on the saved candidate. "
    "Revise the candidate to satisfy these public examples while preserving the original "
    "caller behavior and existing public checks. Use the available source and test tools. "
    "The observations apply only to measured_diff; after an edit they are historical, "
    "not verification of the new diff. The attached public program can be rerun. "
    "One separate final public replay is reserved. No implementation is prescribed."
)


def inject(state, packet):
    result = copy.deepcopy(state)
    current = result["current_diff"]["patch_hash"]
    result[FIELD] = {**packet_api.model_visible(packet, current), "request": INSTRUCTION}
    return result


@contextmanager
def public_feedback(packet):
    """Visible context only; no tool, gate, original obligation or check is altered."""
    build_context, build_input = runner._build_context, runner._build_model_input

    def context(**kwargs):
        return canonical_json(inject(json.loads(build_context(**kwargs)), packet))

    def model_input(**kwargs):
        items = copy.deepcopy(build_input(**kwargs))
        current = json.loads(items[-1]["content"])
        require("state" in current, "current public model state missing")
        current["state"] = inject(current["state"], packet)
        items[-1]["content"] = canonical_json(current)
        return items

    with patch.object(runner, "_build_context", context), \
            patch.object(runner, "_build_model_input", model_input):
        yield


def restore(source, cut, output, cap, env_file, *, funded=False):
    return exposure._fork(source, cut, output, "B", new_cap_usd=cap,
        mode="funded-observation" if funded else "offline-scripted-only",
        env_file=env_file, preserve_parent_configuration=True,
        reserved_tool_actions=RESERVED_ACTIONS, reserved_wall_seconds=RESERVED_SECONDS)


def feedback_audit(branch, request, packet):
    state = json.loads(request["input"][-1]["content"])["state"]
    require(request["input"] == original.public_input(request["input"]),
            "historical opaque reasoning remains")
    require(state["current_diff"]["patch_hash"] == packet["candidate_diff_hash"],
            "restored candidate differs from measured counterexamples")
    expected = inject({"current_diff": state["current_diff"]}, packet)[FIELD]
    require(state.get(FIELD) == expected, "public counterexample delivery changed")
    completion = state["reproduction_review"]["completion"]
    require(completion["status"] == "cases_verified" and completion["cases"],
            "original public verification missing")
    require(all(case["current"]["comparison"] == "matched"
                and case["comparability"]["status"] == "same" for case in completion["cases"]),
            "original call comparability or successful observation changed")
    require(all(check["status"] == "PASS" for check in state["visible_check_status"]),
            "prior public checks are not represented accurately")
    tools = {tool["name"] for tool in request["tools"]}
    require({"replace_text", "read_file", "search_files", "stop_task"} <= tools,
            "revision or exploration is unavailable")
    callers = post.caller_scope_audit(request, branch.request.caller_source_roots)
    return {"status": "PASS", "packet_hash": sha256_json(packet),
            "candidate_diff_hash": packet["candidate_diff_hash"],
            "regressions": packet["regressions"], "original_status": completion["status"],
            "baseline_failure_case_ids": completion["baseline_failure_case_ids"],
            "workflow_gate": state["workflow_gate"], "available_tools": sorted(tools),
            "caller_sources": callers, "context_field": FIELD,
            "original_checks_or_gate_overridden": False,
            "provider_calls": 0, "target_executions": 0}


def run_branch(branch, packet, group, journal, store, first_hash, *, client=None):
    with public_feedback(packet):
        return post.run_branch(branch, group, journal, store, first_hash, client=client)


def prepare(source, cut, packet_root, env_file, output, result_root, cap):
    require(cap.is_finite() and cap > 0, "positive new cap required")
    packet = packet_api.build_packet(packet_root)
    disjoint(output, (repository_root(), source.root, packet_root, result_root))
    disjoint(result_root, (repository_root(), source.root, packet_root, output))
    output.mkdir()
    journal = DevJournal(output, "run_dev_counterexamplepreparation")
    branch = restore(source, cut, output/"preview", cap, env_file)
    old = read_checkpoint_envelope(source)
    require(packet["environment"]["image_digest"] == old.probe_image_digest
            and packet["environment"]["profile_hash"] == old.probe_profile_hash
            and packet["environment"]["dependencies"]
                == old.probe_dependencies.model_dump(mode="json"),
            "public comparison differs from the restored environment")
    require(branch.initial_spent_nanos + usd_to_nanos(cap) == old.max_cost_nanos,
            "retain the original cumulative cap; proposed fresh cap must equal unused capacity")
    client = post.stop_client()
    with public_feedback(packet), post.public_checkpoint():
        preview = exposure.rehearse(branch, client)
    require(len(client.created) == len(client.counted) == 1
            and client.created[0]["tools"] == client.counted[0]["tools"]
            and not preview["synthetic_probe_calls"], "offline preview not isolated")
    request = post.normalized_request(client.created[0])
    audit = feedback_audit(branch, request, packet)
    replay = restore(source, cut, output/"dispatch-rehearsal", cap, env_file)
    check = run_branch(replay, packet, DevCostLedger(cap, replay.pricing), journal,
                       ArtifactStore(output/"artifacts"), sha256_json(request),
                       client=post.stop_client())
    require(check["input_counts"] == check["dispatches"] == 1
            and check["result"]["terminal"] == "AGENT_STOPPED",
            "offline dispatch differs from preparation")
    audit["fresh_offline_dispatch_match"] = True
    later = restore(source, cut, output/"later-response", cap, env_file)
    later_client = ScriptedClient([[{
        "name": "read_file", "action_id": "public_counterexample_delivery_read",
        "arguments": {"path": "astroid/modutils.py", "start_line": 1, "end_line": 12,
                      "source_scope": "repository"},
    }], post.stop_client().steps[0]])
    with public_feedback(packet), post.public_checkpoint():
        later_receipt = exposure.rehearse(later, later_client)
    require(len(later_client.created) == len(later_client.counted) == 2
            and later_receipt["result"]["terminal"] == "AGENT_STOPPED"
            and not later_receipt["synthetic_probe_calls"], "later offline delivery not verified")
    for delivered in later_client.created:
        feedback_audit(later, post.normalized_request(delivered), packet)
    audit["later_response_delivery_checked"] = True
    plan = {"schema": SCHEMA, "official": False, "paid_execution_authorized": False,
        "source": source.record(), "cut_sequence": cut, "include_cut": False,
        "task": str(source.public_path), "split": "dev-train", "repeat": 1,
        "model": old.model, "reasoning_effort": old.reasoning_effort,
        "env_file": str(env_file.resolve()), "new_cap_nanos": usd_to_nanos(cap),
        "historical_spent_nanos": branch.initial_spent_nanos, "historical_funds_reopened": False,
        "active_elapsed_ms": branch.active_elapsed_ms, "remaining_budget": branch.remaining_budget,
        "combined_limits": old.limits.model_dump(mode="json"),
        "limits": branch.request.limits.model_dump(mode="json"),
        "reserved_final_public_check": {"tool_actions": RESERVED_ACTIONS,
                                         "wall_time_seconds": RESERVED_SECONDS, "max_runs": 1},
        "max_output_tokens": old.max_output_tokens,
        "max_correction_output_tokens": old.max_correction_output_tokens,
        "max_context_tokens": 60000, "evaluation_reserve_seconds": old.evaluation_reserve_seconds,
        "caller_source_roots": branch.request.caller_source_roots,
        "packet_root": str(packet_root.resolve()), "packet_hash": sha256_json(packet),
        "baseline_failure_case_ids": audit["baseline_failure_case_ids"],
        "first_request_hash": sha256_json(request),
        "runtime_hash": runner._runtime_hash(),
        "implementation_hash": exposure.implementation_hash(),
        "preparation_commit": git_commit(), "preparation_root": str(output.resolve()),
        "result_root": str(result_root.resolve()),
        "executing_probe_identity": {"image_digest": old.probe_image_digest,
                                     "profile_hash": old.probe_profile_hash},
        "pricing": {key: str(value) for key, value in asdict(branch.pricing).items()},
        "sdk_retries": 0, "automatic_resume": False,
        "intervention": "Operator-authored public counterexample feedback before normal finish",
        "stop_conditions": ["count uncertainty", "transport or billing uncertainty",
                            "execution or cleanup uncertainty", "normal runner terminal"],
        "scope": "Assisted checkpoint revision; no clean-start or causal repair-gain claim"}
    store = ArtifactStore(output)
    for name, value in (("packet.json", packet), ("first-request.json", request),
                        ("feedback-audit.json", audit), ("manifest.json", plan)):
        store.write_text_immutable(output/name, canonical_json(value)+"\n")
    digest = sha256_bytes((output/"manifest.json").read_bytes())
    journal.append("counterexample_repair_prepared", {"manifest_hash": digest,
        "audit": audit, "preview": preview, "offline_dispatch": check,
        "later_response_rehearsal": later_receipt,
        "provider_calls": 0, "target_executions": 0})
    return {"manifest_hash": digest, "audit": audit, "new_cap_nanos": plan["new_cap_nanos"]}


def validate(path, digest, cap=None):
    require(sha256_bytes(path.read_bytes()) == digest, "manifest hash differs")
    plan = json.loads(path.read_bytes())
    require(plan["schema"] == SCHEMA and plan["repeat"] == 1, "unsupported manifest")
    require(plan["runtime_hash"] == runner._runtime_hash()
            and plan["implementation_hash"] == exposure.implementation_hash(), "runtime drift")
    if cap is not None:
        require(usd_to_nanos(cap) == plan["new_cap_nanos"], "approved cap differs")
    source = Source.from_record(plan["source"])
    require(original.source_record(source.root, source.run_id, source.public_path) == source,
            "source checkpoint changed")
    packet = packet_api.build_packet(Path(plan["packet_root"]))
    prepared = Path(plan["preparation_root"])
    require(sha256_json(packet) == plan["packet_hash"]
            and json.loads((prepared/"packet.json").read_bytes()) == packet, "packet changed")
    request = json.loads((prepared/"first-request.json").read_bytes())
    require(sha256_json(request) == plan["first_request_hash"], "first request changed")
    require(not Path(plan["result_root"]).exists(), "single-use allocation already used")
    return plan, packet


def final_public_check(branch, packet, plan, journal, store, result):
    """One final observation; it is not injected as private evaluation feedback."""
    submitted = result.get("result", {}).get("artifact_hashes", {}).get("submitted_patch")
    if not submitted or result.get("stop_remaining") or not result.get("billing_known"):
        return {"status": "NOT_RUN", "reason": "no settled submitted candidate"}
    started = time.monotonic()
    deadline = ExecutionDeadline(started + RESERVED_SECONDS)
    events = branch.journal.events()
    used = runner._restore_counters(branch.journal).tool_actions
    require(used + 1 <= plan["combined_limits"]["max_tool_actions"], "host tool slot missing")
    active_ms = DevJournal.latest_active_elapsed_ms(branch.journal)
    seconds = min(RESERVED_SECONDS,
                  plan["combined_limits"]["wall_time_seconds"] - active_ms / 1000)
    require(seconds > 0, "no final public-check time remains")
    deadline = ExecutionDeadline(min(deadline.expires_at, started + seconds))
    deadline.check()
    current = WorkspaceManager.diff_summary(branch.workspace, deadline=deadline)
    require(current.patch_hash == submitted, "final workspace differs from submitted patch")
    require(not any(e["event_type"] == "counterexample_final_started"
                    for e in journal.events()), "final public execution already attempted")
    identity = {"run_id": journal.run_id, "action_id": "final-public-counterexamples",
                "input_hash": sha256_json({"packet": plan["packet_hash"], "diff": submitted})}
    journal.append("counterexample_final_started", {"execution_identity": identity,
        "submitted_patch": submitted, "max_seconds": seconds, "ordinary_tool_actions": used})
    dependencies = load_dependencies(Path(branch.envelope.prepared_probe_dependencies_path),
        branch.package.public,
        ProbeDependencyIdentity.model_validate(branch.envelope.probe_dependencies))
    probe = DockerProbeSandbox(dependencies=dependencies)
    require(probe.preflight(deadline=deadline) == plan["executing_probe_identity"],
            "final public probe identity changed")
    receipt = probe.run_probe(branch.workspace, "Do the public path-contract cases hold?",
        packet["program_text"], deadline=deadline, execution_identity=identity)
    reference = store.put_json(receipt).model_dump(mode="json")
    journal.append("counterexample_final_finished", {"receipt": reference})
    require(all(receipt.get(key) == value for key, value
                in plan["executing_probe_identity"].items())
            and receipt.get("execution_policy", {}).get("dependencies")
                == packet["environment"]["dependencies"], "final public environment changed")
    rows = packet_api.parse_receipt(receipt, packet["program_hash"])["rows"]
    assessment = packet_api.assess_rows(packet, rows)
    require(WorkspaceManager.diff_summary(branch.workspace, deadline=deadline) == current,
            "diagnostic changed source")
    elapsed = time.monotonic() - started
    require(elapsed <= seconds and active_ms + elapsed * 1000
            <= plan["combined_limits"]["wall_time_seconds"] * 1000, "combined time limit exceeded")
    return {**assessment, "receipt": reference, "candidate_diff_hash": submitted,
            "ordinary_tool_actions": used, "combined_tool_actions": used + 1,
            "additional_seconds": elapsed, "ordinary_active_elapsed_ms": active_ms,
            "source_event_count": len(events), "feedback_to_model": False}


def collect(path, digest, cap):
    plan, packet = validate(path, digest, cap)
    original.clean_implementation()
    root, env_file = Path(plan["result_root"]), Path(plan["env_file"])
    root.mkdir()
    journal = DevJournal(root, "run_dev_counterexamplerepair")
    store = ArtifactStore(root/"artifacts")
    group = DevCostLedger(cap, runner.pricing_for_model(plan["model"]))
    branch = None
    with journal.execution_lock():
        journal.append("counterexample_repair_authorized", {"manifest_hash": digest, "plan": plan})
        env = live.check_environment(plan, env_file)
        journal.append("environment_checked", env)
        result = {"status": "PREFLIGHT_FAILED", "billing_known": True, "stop_remaining": True}
        if env["status"] == "READY":
            try:
                branch = restore(Source.from_record(plan["source"]), plan["cut_sequence"],
                                 root/"repair", cap, env_file, funded=True)
                require(branch.remaining_budget == plan["remaining_budget"]
                        and branch.request.limits.model_dump(mode="json") == plan["limits"],
                        "budget changed")
                result = run_branch(branch, packet, group, journal, store,
                                    plan["first_request_hash"])
                result["public_counterexamples"] = final_public_check(
                    branch, packet, plan, journal, store, result)
            except Exception as exc:
                result = {**result, "status": "COLLECTOR_FAILED", "error_type": type(exc).__name__,
                    "stop_remaining": True,
                    "billing_known": branch is None
                        or runner._provider_usage_failure(branch.journal) is None,
                    "input_count_uncertain": branch is not None
                        and branch.journal.unresolved_input_count() is not None,
                    "provider_dispatch_uncertain": branch is not None
                        and branch.journal.unresolved_provider_call() is not None}
        result.update(official=False, new_cap_nanos=group.cap_nanos,
            new_cost_nanos=group.spent_nanos if result["billing_known"] else None,
            recorded_new_cost_nanos=group.spent_nanos, repair_efficacy="NOT_ESTABLISHED")
        journal.append("counterexample_repair_finished", result)
        journal.append("allocation_closed", {"recorded_new_cost_nanos": group.spent_nanos,
                       "billing_known": result["billing_known"], "automatic_retry": False})
        ArtifactStore(root).write_text_immutable(root/"result.json", canonical_json(result)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--source", type=Path, required=True)
    prep.add_argument("--run-id", required=True)
    prep.add_argument("--task", type=Path, required=True)
    prep.add_argument("--cut", type=int, required=True)
    prep.add_argument("--packet-root", type=Path, required=True)
    prep.add_argument("--env-file", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--result-root", type=Path, required=True)
    prep.add_argument("--new-cap-usd", type=Decimal, required=True)
    run = sub.add_parser("collect")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--manifest-hash", required=True)
    run.add_argument("--new-cap-usd", type=Decimal, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(original.source_record(args.source, args.run_id, args.task), args.cut,
                         args.packet_root, args.env_file, args.output, args.result_root,
                         args.new_cap_usd)
    else:
        result = collect(args.manifest, args.manifest_hash, args.new_cap_usd)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
