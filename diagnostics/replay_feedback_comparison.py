"""Bounded replay-feedback and completion-guidance checkpoint comparisons.

The replay is collected once on the exact candidate. Its real action and elapsed
time are charged to each receiving arm. The guidance comparison gives both arms
the same receipt. No operator diagnosis or private evaluation reaches either model.
"""
from __future__ import annotations

import copy
import json
from contextlib import ExitStack
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from diagnostics import completion_guidance as guidance
from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics import replay_feedback_checkpoint as checkpoint
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.checkpoint_envelope import read_checkpoint_envelope
from diagnostics.decision_sampler import require
from diagnostics.declaration_checkpoint import Source, disjoint
from diagnostics.post_reproduction_repair import (
    PUBLIC_EVIDENCE_KIND,
    normalized_request,
    public_exchanges,
    stop_client,
)
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.cost import DevCostLedger, pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import git_commit, repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SCHEMA = "replay-feedback-comparison-v1"
GUIDANCE_SCHEMA = "completion-guidance-comparison-v1"


def restore(source, cut, output, cap, env_file, *, funded=False, packet=None,
            completion_guidance="baseline"):
    branch = exposure._fork(
        source, cut, output, "B", new_cap_usd=cap,
        mode="funded-observation" if funded else "offline-scripted-only",
        env_file=env_file, preserve_parent_configuration=True,
    )
    if completion_guidance != "baseline":
        guidance.install(branch, completion_guidance)
    else:
        branch.completion_guidance = "baseline"
    if packet is not None:
        checkpoint.attach(branch, packet)
        branch.feedback_packet = packet
    return branch


def feedback_audit(branch, request, packet=None):
    """Check the actual next request, including its unabridged raw replay output."""
    state = json.loads(request["input"][-1]["content"])["state"]
    budget = state["remaining_budget"]
    counters = runner._restore_counters(branch.journal)
    require(budget["model_calls"] == branch.request.limits.max_model_calls -
            counters.model_calls, "model allowance changed in next request")
    require(budget["tool_actions"] == branch.request.limits.max_tool_actions -
            counters.tool_actions, "tool allowance changed in next request")
    edits = sum(event["event_type"] == "action_finished"
                and event["payload"]["result"]["tool"] == "replace_text"
                and event["payload"]["result"]["status"] == "succeeded"
                and event["payload"]["result"].get("error_code") is None
                for event in branch.journal.events())
    require(budget["accepted_mutations"] == branch.request.limits.max_accepted_mutations - edits,
            "edit allowance changed in next request")
    require(budget["cost"]["settled_usage"] == branch.initial_spent_nanos
            and budget["cost"]["remaining"] ==
            usd_to_nanos(branch.request.max_cost_usd) - branch.initial_spent_nanos,
            "inherited/new cost allowance changed in next request")
    require(branch.request.verification_policy == "public-checks-v1",
            "submission policy changed")
    require(branch.request.probe_policy == "none", "probe policy changed")
    require(all(item.get("type") != "reasoning" for item in request["input"]),
            "unexpected reasoning in the completion-stage checkpoint")
    replay_delivered = False
    if packet is not None:
        result = checkpoint.packet_result(packet)
        delivered = {item["action_id"]: item for item in state["latest_tool_results"]}
        for exchange in public_exchanges(request["input"], archive_kind=PUBLIC_EVIDENCE_KIND):
            if exchange.get("type") == "function_call_output":
                item = json.loads(exchange["output"])
                if isinstance(item, dict) and "action_id" in item:
                    delivered.setdefault(item["action_id"], item)
        actual = delivered.get(result["action_id"])
        require(actual is not None, "replay action missing from next request")
        for key in ("tool", "input_hash", "status", "workspace_diff_hash", "error_code"):
            require(actual.get(key) == result.get(key), f"replay {key} changed in next request")
        for key in ("stdout", "stderr", "exit_code", "source_hash", "snapshot_hash",
                    "timed_out", "truncated", "cleanup_failed", "deadline_exhausted",
                    "question"):
            require(actual["output"].get(key) == result["output"].get(key),
                    f"replay output {key} changed in next request")
        projected = runner.project_probe_result({key: value for key, value in result.items()
                                                if key != "replayed"})
        require(actual.get("observation") == projected["observation"],
                "canonical helper observation changed in next request")
        require("status" not in actual["output"],
                "sandbox PASS must not replace the canonical helper observation")
        replay_delivered = True
    elapsed = branch.active_elapsed_ms + (packet["elapsed_ms"] if packet else 0)
    max_solver_seconds = (branch.request.limits.wall_time_seconds -
                          branch.request.evaluation_reserve_seconds - elapsed / 1000)
    require(0 < budget["active_wall_time_seconds"] <= max_solver_seconds,
            "replay active time was refunded or solver time exhausted")
    require(any(tool["name"] == "run_probe" for tool in request["tools"]),
            "optional replay opportunity was removed")
    return {"policy": branch.request.verification_policy,
            "probe_policy": branch.request.probe_policy,
            "remaining_model_calls": budget["model_calls"],
            "remaining_tool_actions": budget["tool_actions"],
            "remaining_accepted_mutations": budget["accepted_mutations"],
            "raw_replay_delivered": replay_delivered,
            "first_request_hash": sha256_json(normalized_request(request))}


def run_branch(branch, group, journal, store, label, first_hash, *, client=None):
    """The funded collector and the finite offline audit use the same dispatch guard."""
    with ExitStack() as stack:
        stack.enter_context(guidance.activate(branch))
        stack.enter_context(patch.object(live, "normalized", normalized_request))
        if client is not None:
            require(type(client) is ScriptedClient, "finite offline client required")
            class OfflineAdapter(OpenAIResponsesAdapter):
                def __init__(self, config, **_):
                    super().__init__(config, api_key="offline-unused", client=client)

            def no_network(*_, **__):
                raise ContractError("network forbidden in dispatch rehearsal")

            stack.enter_context(patch("socket.socket.connect", no_network))
            stack.enter_context(patch.object(live, "OpenAIResponsesAdapter", OfflineAdapter))
            stack.enter_context(patch.object(runner, "load_exact_openai_api_key",
                                            lambda _: "offline-unused"))
            stack.enter_context(patch.object(runner, "_live_source_preflight",
                                            lambda *a, **k: None))
            stack.enter_context(patch.object(runner, "_live_sandbox_preflight",
                                            lambda *a, **k: LocalSandbox()))
            stack.enter_context(patch.object(runner, "DockerProbeSandbox",
                lambda **kw: exposure.SyntheticProbe(branch.envelope, {}, **kw)))
        if hasattr(branch, "feedback_packet"):
            stack.enter_context(checkpoint.host_handoff(branch, branch.feedback_packet))
        return live.run_branch(branch, group, journal, store, label, first_hash)


def preview(branch, packet=None):
    client, counted = stop_client(), []

    class CapturedAdapter(OpenAIResponsesAdapter):
        def count_input_tokens_v2(self, payload, **kwargs):
            counted.append(copy.deepcopy(payload))
            return super().count_input_tokens_v2(payload, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(guidance.activate(branch))
        stack.enter_context(patch.object(exposure, "OpenAIResponsesAdapter", CapturedAdapter))
        if packet is not None:
            stack.enter_context(checkpoint.host_handoff(branch, packet))
        receipt = exposure.rehearse(branch, client)
    require(receipt["result"]["terminal"] == "AGENT_STOPPED"
            and len(counted) == len(client.created) == 1
            and not receipt["synthetic_probe_calls"], "offline preview failed")
    # The stop is synthetic; audit request-time counters instead of its extra action.
    with patch.object(runner, "_restore_counters", lambda _: branch.preview_counters):
        audit = feedback_audit(branch, counted[0], packet)
    return normalized_request(counted[0]), audit, receipt


def continuation_rehearsal(branch, packet, first_hash, journal, store):
    """Exercise the transition from host feedback to a real native tool exchange."""
    edit = next(event["payload"] for event in reversed(branch.journal.events())
                if event["event_type"] == "action_started"
                and event["payload"]["tool"] == "replace_text")
    read = {"name": "read_file", "action_id": "offline_guidance_read",
            "arguments": {"path": edit["arguments"]["path"], "start_line": 1,
                          "end_line": 8, "source_scope": "repository", "memory_update": None}}
    client = ScriptedClient([[read], *stop_client().steps])
    result = run_branch(branch, DevCostLedger(
        Decimal(branch.ledger.remaining_nanos) / 10**9, branch.pricing),
        journal, store, "B-native-continuation", first_hash, client=client)
    require(result["result"]["terminal"] == "AGENT_STOPPED"
            and result["input_counts"] == result["dispatches"] == 2,
            "two-turn native continuation failed")
    with inherited_reads(branch):
        turns = [event["payload"] for event in branch.journal.events()
                 if event["sequence"] > branch.inherited_events
                 and event["event_type"] == "turn_started"]
        require(len(turns) == 2, "native continuation turn count differs")
        for turn in turns:
            items = runner._load_active_model_input(turn, branch.store,
                                                   context_policy="segmented-v1")
            require(items[0]["content"].startswith(
                guidance.selected_prompt("investigate-v1") + "\n"),
                "completion guidance disappeared on a subsequent response")
    require("offline_guidance_read" in canonical_json(client.created[1]["input"]),
            "the second request lost the native read result")
    return {"status": "PASS", "synthetic_responses": 2,
            "provider_calls": 0, "target_executions": 0,
            "native_bindings_verified": 2, "read_result_delivered": True,
            "same_prompt_after_new_model_decision": True, "replay_packet": sha256_json(packet)}


def prepare(source, cut, target_action_id, env_file, result_root, output, cap, *, packet_path=None,
            baseline_plan_path=None):
    """With a baseline plan, hold its replay fixed and vary only completion guidance."""
    guidance_comparison = baseline_plan_path is not None
    require(not guidance_comparison or packet_path is not None,
            "guidance comparison reuses one sealed observation in both arms")
    require(cap.is_finite() and usd_to_nanos(cap) > 0, "positive new allowance required")
    output, result_root = output.resolve(), result_root.resolve()
    disjoint(output, (repository_root(), source.root, source.public_path.parent, result_root))
    disjoint(result_root, (repository_root(), source.root, source.public_path.parent, output))
    live.clean_implementation()
    old = read_checkpoint_envelope(source)
    require(old.runtime_hash == runner._runtime_hash(), "parent runtime differs")
    require(old.model == "gpt-5.4-2026-03-05" and old.reasoning_effort == "xhigh",
            "unexpected parent model")
    row = {"source": source.record(), "executing_probe_identity": {
        "image_digest": old.probe_image_digest, "profile_hash": old.probe_profile_hash}}
    preflight = live.check_environment(row, env_file)
    require(preflight["status"] == "READY", f"environment not ready: {preflight}")
    output.mkdir()
    journal = DevJournal(output, "run_dev_replayfeedbackpreparation")
    seed = restore(source, cut, output / "public-replay", cap, env_file)
    require(usd_to_nanos(cap) == old.max_cost_nanos - seed.initial_spent_nanos,
            "new funding differs from original remaining ceiling")
    if packet_path is None:
        packet = checkpoint.capture(seed, target_action_id)
    else:
        packet = json.loads(packet_path.read_bytes())
        checkpoint.attach(seed, packet)  # Verify the same candidate and immutable capture.
    (output / "public-replay.json").write_text(canonical_json(packet), encoding="utf-8")
    journal.append("public_replay_prepared", {"packet_hash": sha256_json(packet),
                                             "actual_provider_calls": 0})
    parent_events = DevJournal(source.root, source.run_id).events()
    cut_event = next(event for event in parent_events if event["sequence"] == cut)
    read_parent = exposure._parent_reader(source, parent_events[:cut - 1])
    original_request = json.loads(read_parent(Artifact.model_validate(
        cut_event["payload"]["artifact"])))["request"]
    baseline_binding = None
    if guidance_comparison:
        raw_baseline = baseline_plan_path.read_bytes()
        baseline = json.loads(raw_baseline)
        reference_path = baseline_plan_path.parent / "B-first.json"
        reference = json.loads(reference_path.read_bytes())
        require(baseline["schema"] == SCHEMA and baseline["source"] == source.record()
                and baseline["cut_sequence"] == cut
                and baseline["public_replay_hash"] == sha256_json(packet),
                "prior observation comparison differs from this checkpoint")
        require(sha256_json(reference) == next(row["first_request_hash"]
                for row in baseline["rows"] if row["label"] == "B"),
                "prior replay-condition first request changed")
        original_request = reference
        baseline_binding = {"plan_path": str(baseline_plan_path.resolve()),
                            "plan_hash": sha256_bytes(raw_baseline),
                            "request_path": str(reference_path.resolve()),
                            "request_hash": sha256_json(reference)}
    rows, requests = [], {}
    for label in ("A", "B"):
        evidence = packet if guidance_comparison or label == "B" else None
        variant = "investigate-v1" if guidance_comparison and label == "B" else "baseline"
        branch = restore(source, cut, output / f"preview-{label}", cap, env_file,
                         packet=evidence, completion_guidance=variant)
        branch.preview_counters = runner._restore_counters(branch.journal)
        first, audit, receipt = preview(branch, evidence)
        if label == "A":
            require(first == normalized_request(original_request),
                    "baseline first request differs from the reference beyond elapsed time")
            audit["reference_request_preserved" if guidance_comparison
                  else "parent_request_preserved"] = True
        requests[label] = first
        (output / f"{label}-first.json").write_text(canonical_json(first), encoding="utf-8")
        rehearsal = restore(source, cut, output / f"dispatch-{label}", cap, env_file,
                            funded=True, packet=evidence, completion_guidance=variant)
        replay = run_branch(rehearsal, DevCostLedger(cap, rehearsal.pricing), journal,
                            ArtifactStore(output / "artifacts"), label,
                            sha256_json(first), client=stop_client())
        require(replay["result"]["terminal"] == "AGENT_STOPPED"
                and replay["input_counts"] == replay["dispatches"] == 1,
                "fresh offline dispatch did not match prepared input")
        journal.append("row_prepared", {"row": label, "audit": audit,
                       "preview": receipt, "dispatch_rehearsal": replay,
                       "synthetic_accounting_only": True, "actual_provider_calls": 0})
        rows.append({"label": label, "new_cap_nanos": usd_to_nanos(cap),
                     "first_request_hash": sha256_json(first), "audit": audit,
                     **({"completion_guidance": variant} if guidance_comparison else {})})
    if guidance_comparison:
        guidance.assert_pair(requests["A"], requests["B"])
        journal.append("prompt_only_pair_verified", {
            "contract": guidance.contract(),
            "same_public_evidence_tools_state_and_allowances": True,
            "elapsed_time_and_derived_segment_identity_normalized": True,
        })
        continuation = restore(source, cut, output / "native-continuation-B", cap, env_file,
                               funded=True, packet=packet, completion_guidance="investigate-v1")
        journal.append("native_continuation_verified", continuation_rehearsal(
            continuation, packet, sha256_json(requests["B"]), journal,
            ArtifactStore(output / "artifacts")))
    plan = {
        "schema": GUIDANCE_SCHEMA if guidance_comparison else SCHEMA,
        "official": False, "paid_execution_authorized": False,
        "source": source.record(), "cut_sequence": cut, "target_action_id": target_action_id,
        "model": old.model, "reasoning_effort": old.reasoning_effort,
        "task": str(source.public_path), "split": "dev-train", "repeat_per_arm": 1,
        "rows": rows, "env_file": str(env_file.resolve()),
        "new_cap_nanos": 2 * usd_to_nanos(cap), "historical_funds_reopened": False,
        "historical_spent_nanos": seed.initial_spent_nanos,
        "remaining_budget": seed.remaining_budget, "active_elapsed_ms": seed.active_elapsed_ms,
        "limits": old.limits.model_dump(mode="json"),
        "max_output_tokens": old.max_output_tokens,
        "max_correction_output_tokens": old.max_correction_output_tokens,
        "evaluation_reserve_seconds": old.evaluation_reserve_seconds,
        "runtime_hash": runner._runtime_hash(),
        "implementation_hash": exposure.implementation_hash(),
        "preparation_commit": git_commit(), "preparation_root": str(output),
        "result_root": str(result_root), "public_replay_hash": sha256_json(packet),
        "executing_probe_identity": row["executing_probe_identity"],
        "pricing": {key: str(value) for key, value in asdict(seed.pricing).items()},
        "sdk_retries": 0, "automatic_resume": False,
        "intervention": ("Both receive the same sealed helper replay and resource charge; "
                         "A retains completion guidance, B distinguishes submission eligibility "
                         "from whether further diagnosis or repair is warranted"
                         if guidance_comparison else
                         "A optional replay; B receives the exact helper replay collected during "
                         "preparation on this candidate, charged one action and elapsed time"),
        "stop_conditions": ["count uncertainty", "transport or billing uncertainty",
                            "execution or cleanup uncertainty", "normal runner terminal"],
        "scope": "Selected exposed checkpoint; no fresh solve-rate or generalization claim.",
        "material_passport": {"inputs": "public task, parent prefix, model-authored helper",
            "excluded": "operator diagnosis, CLI result, traces, hidden tests and evaluator logs",
            "reuse": ("same current-diff receipt and actual resource cost in both arms"
                      if guidance_comparison else
                      "one current-diff receipt, bytes and actual resource cost sealed for B")},
        **({"completion_guidance_contract": guidance.contract(),
            "baseline_binding": baseline_binding} if guidance_comparison else {}),
    }
    raw = (canonical_json(plan) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    result = {"manifest": str(output / "manifest.json"), "manifest_hash": sha256_bytes(raw),
              "new_cap_nanos": plan["new_cap_nanos"], "preflight": preflight,
              "actual_provider_calls": 0,
              "public_helper_executions": int(packet_path is None),
              "reused_public_helper_executions": int(packet_path is not None),
              "paid_execution_authorized": False, "rows": rows}
    journal.append("preparation_finished", result)
    (output / "preparation.json").write_text(canonical_json(result), encoding="utf-8")
    return result


def validate(path, digest, cap):
    raw = path.read_bytes()
    require(sha256_bytes(raw) == digest, "approved manifest differs")
    plan = json.loads(raw)
    require(plan["schema"] in {SCHEMA, GUIDANCE_SCHEMA} and plan["repeat_per_arm"] == 1
            and [row["label"] for row in plan["rows"]] == ["A", "B"], "unsupported plan")
    require(usd_to_nanos(cap) == plan["new_cap_nanos"] > 0
            and sum(row["new_cap_nanos"] for row in plan["rows"]) == plan["new_cap_nanos"],
            "approved allocation differs")
    require(plan["runtime_hash"] == runner._runtime_hash()
            and plan["implementation_hash"] == exposure.implementation_hash(),
            "implementation drift")
    require(plan["pricing"] == {key: str(value) for key, value in
            asdict(pricing_for_model(plan["model"])).items()}, "pricing changed")
    source = Source.from_record(plan["source"])
    parent = DevJournal(source.root, source.run_id)
    for file, identity in ((parent.path, source.journal_hash),
                           (parent.envelope_path, source.envelope_hash),
                           (source.public_path, source.public_hash)):
        require(sha256_bytes(file.read_bytes()) == identity, "source identity changed")
    prepared = Path(plan["preparation_root"])
    packet = json.loads((prepared / "public-replay.json").read_bytes())
    require(sha256_json(packet) == plan["public_replay_hash"], "public replay changed")
    for row in plan["rows"]:
        require(sha256_json(json.loads((prepared / f'{row["label"]}-first.json').read_bytes()))
                == row["first_request_hash"], "prepared first input changed")
    if plan["schema"] == GUIDANCE_SCHEMA:
        require(plan["completion_guidance_contract"] == guidance.contract()
                and [row["completion_guidance"] for row in plan["rows"]]
                == ["baseline", "investigate-v1"], "guidance intervention changed")
        binding = plan["baseline_binding"]
        require(sha256_bytes(Path(binding["plan_path"]).read_bytes()) == binding["plan_hash"]
                and sha256_json(json.loads(Path(binding["request_path"]).read_bytes()))
                == binding["request_hash"], "historical baseline request changed")
        guidance.assert_pair(json.loads((prepared / "A-first.json").read_bytes()),
                             json.loads((prepared / "B-first.json").read_bytes()))
    require(not Path(plan["result_root"]).exists(), "single-use allocation already used")
    return plan, packet


def collect(path, digest, cap):
    plan, packet = validate(path, digest, cap)
    live.clean_implementation()
    root, env_file = Path(plan["result_root"]), Path(plan["env_file"])
    root.mkdir()
    journal, store = DevJournal(root, "run_dev_replayfeedback"), ArtifactStore(root / "artifacts")
    group = DevCostLedger(cap, pricing_for_model(plan["model"]))
    rows = [{"row": label, "status": "NOT_RUN"} for label in ("A", "B")]
    stop_reason, known = None, True
    with journal.execution_lock():
        journal.append("comparison_authorized", {"manifest_hash": digest, "plan": plan})
        for index, row in enumerate(plan["rows"]):
            branch = None
            try:
                preflight = live.check_environment(plan, env_file)
                journal.append("environment_checked", {"row": row["label"], **preflight})
                require(preflight["status"] == "READY", "environment preflight failed")
                branch = restore(Source.from_record(plan["source"]), plan["cut_sequence"],
                    root / row["label"], Decimal(row["new_cap_nanos"]) / 10**9, env_file,
                    funded=True, packet=packet if plan["schema"] == GUIDANCE_SCHEMA
                    or row["label"] == "B" else None,
                    completion_guidance=row.get("completion_guidance", "baseline"))
                result = run_branch(branch, group, journal, store, row["label"],
                                    row["first_request_hash"])
            except Exception as exc:
                known = branch is None or runner._provider_usage_failure(branch.journal) is None
                result = {"row": row["label"], "status": "COLLECTOR_FAILED",
                          "error_type": type(exc).__name__, "error": str(exc)[:1000],
                          "billing_known": known, "stop_remaining": True}
            rows[index] = result
            known = known and result["billing_known"]
            journal.append("row_finished", result)
            if result["stop_remaining"]:
                stop_reason = result.get("result", {}).get("terminal", result["status"])
                break
        receipt = {"official": False, "rows": rows, "stop_reason": stop_reason,
            "billing_known": known, "new_cost_nanos": group.spent_nanos if known else None,
            "new_cap_nanos": group.cap_nanos, "fresh_solve": False,
            "historical_funds_reopened": False, "efficacy_claim": "NOT_ESTABLISHED"}
        journal.append("comparison_finished", receipt)
        (root / "result.json").write_text(canonical_json(receipt), encoding="utf-8")
    return receipt
