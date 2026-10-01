"""Three-arm scripted review -> native repair rehearsal. No live collector."""

from __future__ import annotations

import copy
import json
import math
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diagnostics import checkpoint_continuation as continuation
from diagnostics import review_context_offline as offline
from diagnostics.decision_sampler import require
from patchloop.agent.model import EncryptedReasoningContinuationItem, OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, ModelConfig
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.contracts import DevRunRequest, RequestedTool
from patchloop.dev.conversation import history_metadata
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, validate_tool_batch
from patchloop.errors import ContractError
from patchloop.prepared_probe_dependencies import load_dependencies
from patchloop.sandbox import LocalSandbox
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.util import canonical_json, sha256_json


class RepairLedger(DevCostLedger):
    """Inherited usage and new reviewer usage remain separate in the journal."""

    def __init__(self, cap, pricing, review_cost):
        super().__init__(cap, pricing)
        self.review_cost = review_cost

    def restore_settled_usage(self, rows, *, base_spent_nanos=0):
        super().restore_settled_usage(rows, base_spent_nanos=base_spent_nanos)
        self.spent_nanos += self.review_cost


def admitted_probe(loaded, deadline):
    """Verify existing public dependencies/image only; never acquire an image."""
    env = loaded.envelope
    require(env.probe_image_digest is not None, "source probes were not enabled")
    dependencies = (
        load_dependencies(Path(env.prepared_probe_dependencies_path), loaded.package.public,
                          env.probe_dependencies)
        if env.prepared_probe_dependencies_path else None
    )
    sandbox = DockerProbeSandbox(dependencies=dependencies)
    require(sandbox.preflight(deadline=deadline) == {
        "image_digest": env.probe_image_digest, "profile_hash": env.probe_profile_hash,
    }, "review probe identity changed")
    return sandbox


def scripted_review(loaded, arm, root, workspace, client, budget, panel, *,
                    execute_probes=False):
    require(type(client) is continuation.ScriptedClient, "scripted reviewer required")
    return _review(loaded, arm, root, workspace, client, budget, panel,
                   execute_probes=execute_probes, simulated=True)


def _review(loaded, arm, root, workspace, client, budget, panel, *,
            execute_probes, simulated):
    request = offline.reviewer_request(loaded, arm)
    allowed_tools = offline.REVIEW_TOOLS if execute_probes else (
        offline.REVIEW_TOOLS - {"run_probe"})
    request["tools"] = [tool for tool in request["tools"] if tool["name"] in allowed_tools]
    adapter = OpenAIResponsesAdapter(ModelConfig(
        provider="openai", model_id=loaded.envelope.model,
        reasoning_effort=loaded.envelope.reasoning_effort,
        reasoning_continuation="encrypted-v1", transport_max_retries=0,
        max_output_tokens=loaded.envelope.max_output_tokens,
    ), api_key="offline-no-credential", client=client)
    fields = ["suspected_behavior", "evidence", "observation", "candidate_hash", "limitations"]
    request["tools"].append(
        {
            "type": "function",
            "name": "finish_review",
            "strict": True,
            "description": "Call alone. Return untrusted review advice; candidate_hash must "
                           "equal current_diff.patch_hash. No turn_decision field.",
            "parameters": {
                "type": "object",
                "properties": {k: {"type": "string", "maxLength": 4000} for k in fields},
                "required": fields,
                "additionalProperties": False,
            },
        }
    )
    journal = DevJournal(root, "run_dev_review" + sha256_json(str(root.resolve()))[7:23])
    deadline = ExecutionDeadline(budget.started + 180, budget.clock)
    gateway = DevToolGateway(
        workspace=workspace,
        public_task=loaded.package.public,
        sandbox=LocalSandbox(),
        journal=journal,
        limits=loaded.envelope.limits,
        deadline=deadline,
        probe_policy=loaded.envelope.probe_policy,
    )
    billing_known, settled_cost_nanos = True, 0
    try:
        if execute_probes:
            gateway.probe_sandbox = admitted_probe(loaded, deadline)
            journal.append("review_probe_admitted", gateway.probe_sandbox.identity)
        while True:
            budget.require_call_available()
            remaining_calls = 4 - budget.review_calls
            report_required = remaining_calls == 1 or budget.review_actions >= 12
            request["input"].append({"role": "user", "content": canonical_json({
                "review_budget": {
                    "remaining_model_calls_including_this": remaining_calls,
                    "remaining_tool_actions": 12 - budget.review_actions,
                    "remaining_seconds": max(0, 180 - (budget.clock() - budget.started)),
                    "remaining_shared_cost_nanos": budget.ledger.cap_nanos
                    - budget.ledger.spent_nanos,
                    "report_required_this_call": report_required,
                    "instruction": "Reserve the final call for finish_review. Report limitations "
                    "if no defect is established; no extra call is available.",
                }})})
            if report_required:
                request["tool_choice"] = {"type": "function", "name": "finish_review"}
            request_hash = sha256_json(request)
            journal.append("review_count_started", {"request_hash": request_hash,
                                                     "simulated": simulated})
            billing_known = False
            count = adapter.count_input_tokens_v2(
                request, timeout_seconds=deadline.check())
            journal.append("review_count_finished", {"request_hash": request_hash,
                                                      "input_tokens": count})
            billing_known = True
            admission = budget.admit(count)
            request["max_output_tokens"] = admission.output_ceiling
            dispatch_event = "review_simulated_dispatch" if simulated else "review_dispatch_started"
            journal.append(dispatch_event, {
                "request_hash": sha256_json(request), "call": budget.calls,
                "reserved_cost_nanos": admission.reserved_cost_nanos,
                "artifact": ArtifactStore(root / "artifacts").put_json(request).model_dump(
                    mode="json"),
            })
            billing_known = False
            turn = adapter.execute_request(request, requested_input_tokens=count,
                                           timeout_seconds=deadline.check())
            journal.append("review_response_received", {
                "response_id": turn.response_id, "status": turn.response_status,
                "usage_evidence": turn.usage_evidence,
                "error_code": turn.error.code if turn.error else None,
            })
            require(turn.usage_evidence is not None
                    and turn.usage_evidence["failure_kind"] is None,
                    "unknown or mismatched reviewer usage")
            cost = budget.settle(
                turn.input_tokens, turn.cached_input_tokens, turn.output_tokens
            )
            journal.append("review_usage_settled", {
                "call": budget.calls, "cost_nanos": cost,
                "input_tokens": turn.input_tokens,
                "cached_input_tokens": turn.cached_input_tokens,
                "output_tokens": turn.output_tokens,
                "total_new_cost_nanos": budget.ledger.spent_nanos, "simulated": simulated,
            })
            settled_cost_nanos += cost
            billing_known = True
            budget._ready()
            require(turn.error is None, turn.error.code if turn.error else "invalid response")
            require(turn.response_model == loaded.envelope.model, "review response model changed")
            require(set(turn.output_item_types) <= {"reasoning", "function_call"},
                    "unsupported reviewer output item")
            calls = [SimpleNamespace(name=c.name, call_id=c.action_id,
                                     arguments=canonical_json(c.arguments))
                     for c in turn.tool_calls]
            require(bool(calls), "review response has no calls")
            require(not report_required or
                    (len(calls) == 1 and calls[0].name == "finish_review"),
                    "final review call must finish_review")
            require(len({c.call_id for c in calls}) == len(calls), "duplicate review call IDs")
            require(bool(turn.provider_continuation), "review continuation missing")
            native = []
            by_id = {c.call_id: c for c in calls}
            for item in turn.provider_continuation:
                if isinstance(item, EncryptedReasoningContinuationItem):
                    native.append({"type": "reasoning", "id": item.id,
                                   "encrypted_content": item.encrypted_content, "summary": [],
                                   **({"status": item.status} if item.status else {})})
                else:
                    call = by_id[item.action_id]
                    native.append({"type": "function_call", "name": call.name,
                                   "call_id": call.call_id, "arguments": call.arguments})
            journal.append("review_continuation_saved", {
                "artifact": ArtifactStore(root / "artifacts").put_json(native).model_dump(
                    mode="json"), "item_count": len(native),
            })
            if any(c.name == "finish_review" for c in calls):
                require(len(calls) == 1, "report cannot accompany tools")
                report = offline.handoff_report(
                    json.loads(calls[0].arguments), loaded.diff["patch_hash"]
                )
                journal.append("review_reported", {"report": report, "simulated": simulated})
                return report
            requested = []
            for call in calls:
                args = json.loads(call.arguments)
                requested.append(RequestedTool(name=call.name, action_id=call.call_id,
                    arguments={k: v for k, v in args.items() if k != "turn_decision"},
                    turn_decision=args.get("turn_decision")))
            validate_tool_batch(requested, allowed_tools=allowed_tools)
            require(all(call.turn_decision.memory_update is None
                        and call.turn_decision.plan_update is None for call in requested),
                    "reviewer does not manage notes or plans")
            request["input"].extend(native)
            for call in requested:
                budget.action(call.name)
                result = gateway.execute(call)
                abort, reason = runner._batch_execution_abort([result])
                require(abort is None, reason or "review execution uncertain")
                budget._ready()
                request["input"].extend(
                    [
                        {
                            "type": "function_call_output",
                            "call_id": call.action_id,
                            "output": canonical_json(result.model_dump(mode="json")),
                        },
                    ]
                )
    except Exception as exc:
        budget.fail()
        reason = str(exc) if isinstance(exc, ContractError) else type(exc).__name__
        receipt = {"phase": "review", "reason": reason,
                   "settled_cost_nanos": settled_cost_nanos, "billing_known": billing_known}
        journal.append("review_stopped", receipt)
        panel.append("panel_stopped", receipt)
        raise offline.ReviewStopped(reason, settled_cost_nanos, billing_known) from exc


@contextmanager
def repair_inputs(branch, report):
    original = native_compaction.prepared_input
    first = []

    def prepare(journal, store, turn, request, transition):
        boundary, bundle = original(journal, store, turn, request, transition)
        if first:
            return boundary, bundle
        first.append(True)
        baseline = bundle["request"]
        # New resource limits can rebuild current state, but cannot rewrite native history.
        require(
            baseline["input"][:-1] == branch.source_request["input"][:-1],
            "repair trajectory changed before handoff",
        )
        if report is None:
            return boundary, bundle
        selected = copy.deepcopy(bundle)
        view = json.loads(selected["request"]["input"][-1]["content"])
        view["state"]["review_handoff"] = report
        selected["request"]["input"][-1]["content"] = canonical_json(view)
        prepared = selected["turn"]
        canonical = json.loads(
            store.read_bytes(Artifact.model_validate(prepared["context_artifact"]))
        )
        canonical["review_handoff"] = report
        prepared["context_artifact"] = native_compaction.put_json(store, canonical)
        prepared["context_hash"] = prepared["context_artifact"]["content_hash"]
        prepared["model_input_artifact"] = native_compaction.put_json(
            store, selected["request"]["input"]
        )
        prepared["model_input_hash"] = prepared["model_input_artifact"]["content_hash"]
        prepared["native_history"] = history_metadata(
            selected["request"]["input"], context_policy="segmented-v1"
        )
        prepared["context_request_sizes"] = segments.request_sizes(selected["request"])
        require(not segments.size_reasons(prepared["context_request_sizes"]), "handoff too large")
        replacement = {
            **boundary,
            "artifact": native_compaction.put_json(store, selected),
            "request_hash": sha256_json(selected["request"]),
        }
        journal.append("model_input_prepared", replacement)
        return replacement, selected

    with patch.object(native_compaction, "prepared_input", prepare):
        yield first


def _rehearse_locked(
    source, sequence, output, arm, repair_client, *, reviewer_client=None, panel_root=None,
    execute_reviewer_probes=False,
    current_runtime_fork=False,
    real_sandboxes=False,
    live=False, env_file=None,
):
    require(arm in {"A", "B", "C"}, "unknown arm")
    if not live:
        require(type(repair_client) is continuation.ScriptedClient, "scripted repair required")
        require(reviewer_client is None or type(reviewer_client) is continuation.ScriptedClient,
                "scripted reviewer required")
    else:
        require(real_sandboxes and current_runtime_fork and env_file is not None,
                "live execution requires a bound current fork")
    require(not real_sandboxes or current_runtime_fork, "real execution requires a current fork")
    require((arm == "C") == (reviewer_client is None), "reviewer/arm mismatch")
    panel = DevJournal(panel_root or output.parent / "panel", "run_dev_reviewpanel")
    events = panel.events()
    started = {e["payload"]["output"] for e in events if e["event_type"] == "episode_started"}
    finished = {e["payload"]["output"] for e in events if e["event_type"] == "episode_finished"}
    require(started <= finished, "panel stopped: unfinished episode")
    require(len(started) < 12, "panel episode cap exhausted")
    require(
        not any(
            e["event_type"] in {"panel_stopped", "episode_started"}
            and (
                e["event_type"] == "panel_stopped"
                or e["payload"]["output"] == str(output.resolve())
            )
            for e in panel.events()
        ),
        "panel stopped or episode already claimed",
    )
    loaded = offline.load(source, sequence, conan_materialization=current_runtime_fork)
    materialized = offline.restore(source, sequence, output,
                                   conan_materialization=current_runtime_fork,
                                   defer_envelope=current_runtime_fork)
    journal = DevJournal(output, source.run_id)
    panel.append("episode_started", {"arm": arm, "output": str(output.resolve())})
    budget = offline.SharedBudget()
    report = None
    if reviewer_client is not None:
        report = _review(
            loaded,
            arm,
            output / "review",
            Path(materialized["workspace"]),
            reviewer_client,
            budget,
            panel,
            execute_probes=execute_reviewer_probes,
            simulated=not live,
        )
    budget.repair()
    env = loaded.envelope
    historical = DevCostLedger(Decimal(env.max_cost_nanos) / 10**9, budget.ledger.pricing)
    historical.restore_settled_usage(
        journal.provider_usage(), base_spent_nanos=env.cost_start_nanos
    )
    ledger = RepairLedger(
        Decimal(historical.spent_nanos + budget.ledger.cap_nanos) / 10**9,
        budget.ledger.pricing,
        budget.ledger.spent_nanos,
    )
    ledger.restore_settled_usage(journal.provider_usage(), base_spent_nanos=env.cost_start_nanos)
    counters = runner._restore_counters(journal)
    limits = env.limits.model_copy(
        update={
            "max_model_calls": counters.model_calls + 16 - budget.calls,
            "max_tool_actions": counters.tool_actions + 48 - budget.actions,
            "max_accepted_mutations": materialized["accepted_edits"] + 2,
            "wall_time_seconds": math.ceil(journal.latest_active_elapsed_ms() / 1000)
            + max(1, math.floor(900 - (budget.clock() - budget.started))),
        }
    )
    request = DevRunRequest(
        provider="openai",
        task=source.public_path,
        model=env.model,
        reasoning_effort=env.reasoning_effort,
        max_output_tokens=env.max_output_tokens,
        env_file=env_file if live else output / "NO_CREDENTIAL_FILE",
        state_root=output,
        resume_run_id=source.run_id,
        max_cost_usd=Decimal(ledger.cap_nanos) / 10**9,
        limits=limits,
        prepared_source=Path(env.prepared_source_path) if env.prepared_source_path else None,
        prepared_probe_dependencies=(
            Path(env.prepared_probe_dependencies_path)
            if env.prepared_probe_dependencies_path
            else None
        ),
        enable_probes=env.probe_image_digest is not None,
        **{
            k: getattr(env, k)
            for k in (
                "repair_recheck",
                "repair_inspection_policy",
                "planning_policy",
                "probe_policy",
                "context_policy",
                "segment_boundary_policy",
                "completion_cost_policy",
            )
        },
    )
    events = journal.events()
    if current_runtime_fork:
        envelope_request = request.model_copy(update={"provider": env.provider})
        target = runner._run_envelope(
            request=envelope_request, task_dir=source.public_path.parent, package=loaded.package,
            run_id=source.run_id, runtime_hash=runner._runtime_hash(),
            model_hash=runner._model_hash(request, ledger.pricing), cost_ledger=ledger,
            cost_start_nanos=env.cost_start_nanos, prepared_source_hash=env.prepared_source_hash,
            probe_dependencies=env.probe_dependencies,
        )
        journal.write_envelope(target)
        journal.append("review_current_runtime_fork", {
            "mode": "funded-review" if live else "offline-scripted-only", "parent": source.record(),
            "parent_runtime_hash": env.runtime_hash, "target_runtime_hash": target.runtime_hash,
            "parent_prefix_hash": loaded.prefix[-1]["event_hash"],
            "historical_cost_nanos": historical.spent_nanos,
            "historical_funds_reopened": False,
            "new_cap_nanos": budget.ledger.cap_nanos,
            "inherited_events_are_not_new_execution": True,
        })
        env = target
    branch = SimpleNamespace(
        root=output,
        store=ArtifactStore(output / "artifacts"),
        journal=journal,
        references=next(e["payload"]["artifact_references"] for e in reversed(events)
                        if e["event_type"] == "diagnostic_checkpoint_fork"),
        envelope=env,
        request=request,
        package=loaded.package,
        task_dir=source.public_path.parent,
        ledger=ledger,
        pricing=ledger.pricing,
        packet={},
        source_request=loaded.bundle["request"],
        inherited_events=len(loaded.prefix),
        initial_spent_nanos=historical.spent_nanos,
        parent_journal_hash=source.journal_hash,
    )
    journal.append(
        "review_repair_allowance",
        {
            "historical_cost": historical.spent_nanos,
            "review_cost_nanos" if live else "simulated_review_cost": budget.ledger.spent_nanos,
            "review_calls": budget.calls,
            "review_actions": budget.actions,
            "limits": limits.model_dump(mode="json"),
            "new_cap_nanos": budget.ledger.cap_nanos,
            "report_is_not_check_credit": True,
        },
    )
    try:
        if real_sandboxes:
            from diagnostics.review_integrated_execution import repair
            result = repair(branch, repair_client, report, live=live)
        else:
            with patch.object(continuation, "first_input", lambda b: repair_inputs(b, report)):
                result = continuation.rehearse(branch, repair_client)
        if result["stop_remaining"] or not result.get("billing_known",
                                                       result.get("simulated_billing_known")):
            panel.append("panel_stopped", {"phase": "repair", "output": str(output.resolve())})
        panel.append(
            "episode_finished", {"arm": arm, "output": str(output.resolve()), "receipt": result}
        )
        result["workspace"] = materialized["workspace"]
        return result
    except Exception as exc:
        panel.append("panel_stopped", {"phase": "repair", "reason": type(exc).__name__})
        raise


def rehearse(
    source, sequence, output, arm, repair_client, *, reviewer_client=None, panel_root=None,
    execute_reviewer_probes=False,
    current_runtime_fork=False,
    real_sandboxes=False,
):
    panel_root = panel_root or output.parent / "panel"
    panel = DevJournal(panel_root, "run_dev_reviewpanel")
    with panel.execution_lock():
        return _rehearse_locked(
            source,
            sequence,
            output,
            arm,
            repair_client,
            reviewer_client=reviewer_client,
            panel_root=panel_root,
            execute_reviewer_probes=execute_reviewer_probes,
            current_runtime_fork=current_runtime_fork,
            real_sandboxes=real_sandboxes,
        )
