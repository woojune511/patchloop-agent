"""Prepare a public post-reproduction continuation; collect only after new approval.

The ordinary runner owns repair, replay, public checks, finish and evaluation.
This driver only restores a settled checkpoint and binds new funding/provenance.
"""
from __future__ import annotations

import argparse
import json
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from diagnostics import first_reproduction_comparison as original
from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, usd_to_nanos
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.dev.state import DevJournal
from patchloop.runtime import git_commit, repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "post-reproduction-repair-v1"


@contextmanager
def public_checkpoint():
    """Use the normal evidence handoff once; subsequent turns use normal segments."""
    build, first = runner._build_model_input, True

    def model_input(**kwargs):
        nonlocal first
        if first:
            kwargs = {**kwargs, "force_segment_reason": "post_reproduction_public_checkpoint"}
        result = build(**kwargs)
        if first:
            require(result == original.public_input(result), "historical opaque reasoning remains")
            first = False
        return result

    with patch.object(runner, "_build_model_input", model_input):
        yield


def restore(source, cut, root, cap, env_file, *, funded=False):
    return exposure._fork(
        source, cut, root, "B", new_cap_usd=cap,
        mode="funded-observation" if funded else "offline-scripted-only",
        env_file=env_file, preserve_parent_configuration=True, after_tool_batch=True,
    )


def feedback_audit(branch, request):
    """Check actual prepared input, not merely the restored gateway state."""
    value = json.loads(request["input"][-1]["content"])["state"]
    serialized = canonical_json(request["input"])
    latest = [item.model_dump(mode="json") for item in branch.latest_results]
    obligation = branch.original_obligation
    cases = obligation["baseline_failure_case_ids"]
    require(obligation["stage"] == "acquired" and obligation["status"] == "refuted"
            and cases, "original baseline not acquired/refuted")
    require(all(case in serialized for case in cases), "baseline case missing from next input")
    require(all(item["action_id"] in serialized for item in latest),
            "latest action result missing from next input")
    require("refuted" in serialized, "desired-observation failure missing from next input")
    delivered = {item["action_id"]: item for item in value["latest_tool_results"]}
    for exchange in public_exchanges(request["input"], archive_kind=PUBLIC_EVIDENCE_KIND):
        if exchange.get("type") == "function_call_output":
            result = json.loads(exchange["output"])
            if isinstance(result, dict) and "action_id" in result:
                delivered.setdefault(result["action_id"], result)
    for item in latest:
        actual = delivered.get(item["action_id"])
        require(actual is not None and actual["input_hash"] == item["input_hash"]
                and actual["output"].get("reproduction") == item["output"].get("reproduction"),
                "latest reproduction binding, comparison or call captures changed")
    require(request["input"] == original.public_input(request["input"]), "opaque history present")
    require(value["workflow_gate"] != "needs_original_reproduction", "acquisition was reset")
    # The registered case/program stays in the journal; the current public view is
    # intentionally bounded and need not repeat the entire authored program.
    return {
        "status": "PASS", "baseline_failure_case_ids": cases,
        "latest_action_ids": [item["action_id"] for item in latest],
        "latest_results_hash": sha256_json(latest),
        "workflow_gate": value["workflow_gate"], "original_failure_delivered": True,
        "historical_opaque_items": 0, "new_target_executions": 0,
        "interpretation": "Input delivery only; model adoption and repair are NOT_RUN.",
    }


def run_branch(branch, group, journal, store, first_hash, *, client=None):
    """Reuse dispatch guards, current receipt lineage and executing commit handling."""
    with ExitStack() as stack:
        stack.enter_context(public_checkpoint())
        stack.enter_context(patch.object(live, "normalized", normalized_request))
        if client is not None:
            require(type(client) is ScriptedClient, "finite offline client required")

            class OfflineAdapter(OpenAIResponsesAdapter):
                def __init__(self, config, **_):
                    super().__init__(config, api_key="offline-unused", client=client)

            stack.enter_context(patch("socket.socket.connect", original.forbidden))
            stack.enter_context(patch.object(live, "OpenAIResponsesAdapter", OfflineAdapter))
            stack.enter_context(patch.object(runner, "load_exact_openai_api_key",
                                            lambda _: "offline-unused"))
            stack.enter_context(patch.object(runner, "_live_source_preflight",
                                            lambda *a, **k: None))
            stack.enter_context(patch.object(runner, "_live_sandbox_preflight",
                                            lambda *a, **k: LocalSandbox()))
            stack.enter_context(patch.object(runner, "DockerProbeSandbox",
                                            lambda **kw: exposure.SyntheticProbe(
                                                branch.envelope, {}, **kw)))
        return live.run_branch(branch, group, journal, store, "repair", first_hash)


# Retain the original normalizer before temporarily overriding the collector's
# binding. Otherwise normalizing would recurse through that patched binding.
_base_normalized = live.normalized


def normalized_request(request):
    """Ignore elapsed time and the derived segment ID, never evidence or budgets."""
    value = _base_normalized(request)
    content = json.loads(value["input"][-1]["content"])
    content["state"]["segment_handoff"]["segment_id"] = "RUN_LOCAL_SEGMENT"
    forecast = content["state"]["remaining_budget"].get("cost", {}).get("completion_cost", {})
    if "remaining_seconds" in forecast:
        forecast["remaining_seconds"] = 0
    value["input"][-1]["content"] = canonical_json(content)
    return value


def stop_client():
    return ScriptedClient([[{
        "name": "stop_task", "action_id": "prepare_only_stop", "arguments": {
            "reason_code": "insufficient_public_evidence", "summary": "Offline input preparation.",
            "turn_decision": {"mode": "stop", "basis": "Preparation only.",
                              "evidence_goal": None, "memory_update": None, "plan_update": None},
        },
    }]])


def preview(branch):
    client = stop_client()
    # A first preview uses the regular rehearsal, with the same public handoff.
    with public_checkpoint():
        receipt = exposure.rehearse(branch, client)
    require(len(client.counted) == len(client.created) == 1
            and receipt["result"]["terminal"] == "AGENT_STOPPED"
            and not receipt["synthetic_probe_calls"], "offline preview did not stop cleanly")
    request = normalized_request(client.created[0])
    return request, feedback_audit(branch, request), receipt


def prepare(source, cut, env_file, result_root, output, cap):
    require(cap.is_finite() and usd_to_nanos(cap) > 0, "positive finite new cap required")
    disjoint(output, (repository_root(), source.root, source.public_path.parent, result_root))
    disjoint(result_root, (repository_root(), source.root, source.public_path.parent, output))
    output.mkdir()
    branch = restore(source, cut, output / "preview", cap, env_file)
    request, audit, receipt = preview(branch)
    journal = DevJournal(output, "run_dev_postreproductionpreparation")
    replay = restore(source, cut, output / "dispatch-rehearsal", cap, env_file)
    replay_receipt = run_branch(
        replay, DevCostLedger(cap, replay.pricing), journal, ArtifactStore(output / "artifacts"),
        sha256_json(request), client=stop_client(),
    )
    require(replay_receipt["result"]["terminal"] == "AGENT_STOPPED"
            and replay_receipt["input_counts"] == replay_receipt["dispatches"] == 1,
            "prepared first request differs from fresh offline dispatch")
    audit["fresh_offline_dispatch_match"] = True
    (output / "first-request.json").write_text(canonical_json(request), encoding="utf-8")
    old = DevJournal(source.root, source.run_id).load_envelope()
    plan = {
        "schema": SCHEMA, "official": False, "paid_execution_authorized": False,
        "source": source.record(), "cut_sequence": cut, "include_cut": True,
        "task": str(source.public_path), "split": "dev-train", "repeat": 1,
        "model": old.model, "reasoning_effort": old.reasoning_effort,
        "env_file": str(env_file.resolve()), "new_cap_nanos": usd_to_nanos(cap),
        "historical_spent_nanos": branch.initial_spent_nanos,
        "historical_funds_reopened": False, "active_elapsed_ms": branch.active_elapsed_ms,
        "remaining_budget": branch.remaining_budget,
        "limits": old.limits.model_dump(mode="json"),
        "max_output_tokens": old.max_output_tokens,
        "max_correction_output_tokens": old.max_correction_output_tokens,
        "max_context_tokens": 60000, "evaluation_reserve_seconds": old.evaluation_reserve_seconds,
        "baseline_failure_case_ids": branch.original_obligation["baseline_failure_case_ids"],
        "latest_results_hash": audit["latest_results_hash"],
        "runtime_hash": runner._runtime_hash(),
        "implementation_hash": exposure.implementation_hash(),
        "preparation_commit": git_commit(),
        "first_request_hash": sha256_json(request),
        "preparation_root": str(output.resolve()), "result_root": str(result_root.resolve()),
        "executing_probe_identity": {
            "image_digest": runner.probe_profile(old.probe_dependencies)["image_digest"],
            "profile_hash": runner.probe_profile_hash(old.probe_dependencies),
        },
        "pricing": {key: str(value) for key, value in asdict(branch.pricing).items()},
        "sdk_retries": 0, "automatic_resume": False,
        "intervention": "public post-reproduction handoff; ordinary full repair continuation",
        "stop_conditions": ["count uncertainty", "transport or billing uncertainty",
                            "execution or cleanup uncertainty", "normal runner terminal"],
        "scope": "Checkpoint repair only; no clean-start or generalization claim.",
    }
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    journal.append("post_reproduction_prepared", {
        "manifest_hash": sha256_bytes(raw), "feedback_audit": audit,
        "offline_receipt": receipt, "offline_dispatch_receipt": replay_receipt,
        "provider_calls": 0, "target_executions": 0,
    })
    (output / "feedback-audit.json").write_text(canonical_json(audit), encoding="utf-8")
    return {"manifest": str(output / "manifest.json"), "manifest_hash": sha256_bytes(raw),
            "feedback_audit": audit, "new_cap_nanos": plan["new_cap_nanos"],
            "paid_execution_authorized": False, "provider_calls": 0}


def validate(path, digest, cap=None):
    raw = path.read_bytes()
    require(sha256_bytes(raw) == digest, "manifest hash changed")
    plan = json.loads(raw)
    require(plan["schema"] == SCHEMA and plan["repeat"] == 1, "unsupported plan")
    require(plan["runtime_hash"] == runner._runtime_hash()
            and plan["implementation_hash"] == exposure.implementation_hash(),
            "implementation drift")
    require(plan["new_cap_nanos"] > 0, "new funding cap missing")
    if cap is not None:
        require(usd_to_nanos(cap) == plan["new_cap_nanos"], "approved new cap differs")
    source = Source.from_record(plan["source"])
    saved = original.source_record(source.root, source.run_id, source.public_path)
    require(saved == source, "source bytes changed")
    request = json.loads((Path(plan["preparation_root"]) / "first-request.json").read_bytes())
    require(sha256_json(request) == plan["first_request_hash"], "first request changed")
    require(not Path(plan["result_root"]).exists(), "result allocation already used")
    return plan


def collect(path, digest, cap):
    plan = validate(path, digest, cap)
    original.clean_implementation()
    root, env_file = Path(plan["result_root"]), Path(plan["env_file"])
    root.mkdir()  # One allocation, no automatic resume or retry after uncertainty.
    journal = DevJournal(root, "run_dev_postreproductionrepair")
    store = ArtifactStore(root / "artifacts")
    group = DevCostLedger(cap, runner.pricing_for_model(plan["model"]))
    with journal.execution_lock():
        journal.append("repair_continuation_authorized", {"manifest_hash": digest, "plan": plan})
        preflight = live.check_environment(plan, env_file)
        journal.append("environment_checked", preflight)
        result = {"status": "PREFLIGHT_FAILED", "billing_known": True, "stop_remaining": True}
        branch = None
        if preflight["status"] == "READY":
            try:
                branch = restore(Source.from_record(plan["source"]), plan["cut_sequence"],
                                 root / "repair", cap, env_file, funded=True)
                require(branch.remaining_budget == plan["remaining_budget"],
                        "checkpoint budget changed")
                result = run_branch(branch, group, journal, store, plan["first_request_hash"])
            except Exception as exc:
                result = {
                    "status": "COLLECTOR_FAILED", "error_type": type(exc).__name__,
                    "stop_remaining": True,
                    "billing_known": branch is None
                    or runner._provider_usage_failure(branch.journal) is None,
                    "input_count_uncertain": branch is not None
                    and branch.journal.unresolved_input_count() is not None,
                }
        result.update(
            official=False, new_cap_nanos=group.cap_nanos,
            new_cost_nanos=group.spent_nanos if result["billing_known"] else None,
            recorded_new_cost_nanos=group.spent_nanos,
            repair_efficacy="NOT_ESTABLISHED",
        )
        journal.append("repair_continuation_finished", result)
        journal.append("allocation_closed", {"recorded_new_cost_nanos": group.spent_nanos,
                                             "billing_known": result["billing_known"],
                                             "automatic_retry": False})
        (root / "result.json").write_text(canonical_json(result), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("source-root", "public-task", "env-file", "result-root", "output"):
        prep.add_argument("--" + name, type=Path, required=True)
    prep.add_argument("--run-id", required=True)
    prep.add_argument("--cut-sequence", type=int, required=True)
    prep.add_argument("--new-cap-usd", type=Decimal, required=True)
    for name in ("validate", "collect"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--manifest", type=Path, required=True)
        cmd.add_argument("--manifest-hash", required=True)
        cmd.add_argument("--new-cap-usd", type=Decimal, required=name == "collect")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(original.source_record(args.source_root, args.run_id, args.public_task),
                         args.cut_sequence, args.env_file, args.result_root, args.output,
                         args.new_cap_usd)
    elif args.command == "collect":
        result = collect(args.manifest, args.manifest_hash, args.new_cap_usd)
    else:
        plan = validate(args.manifest, args.manifest_hash, args.new_cap_usd)
        result = {"status": "VALID", "provider_calls": 0,
                  "new_cap_nanos": plan["new_cap_nanos"]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
