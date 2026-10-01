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
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.contracts import DevRunRequest, RequestedTool
from patchloop.dev.conversation import history_metadata
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_json


class RepairLedger(DevCostLedger):
    """Inherited usage and new reviewer usage remain separate in the journal."""

    def __init__(self, cap, pricing, review_cost):
        super().__init__(cap, pricing)
        self.review_cost = review_cost

    def restore_settled_usage(self, rows, *, base_spent_nanos=0):
        super().restore_settled_usage(rows, base_spent_nanos=base_spent_nanos)
        self.spent_nanos += self.review_cost


def scripted_review(loaded, arm, root, workspace, client, budget, panel):
    require(type(client) is continuation.ScriptedClient, "scripted reviewer required")
    request = offline.reviewer_request(loaded, arm)
    fields = ["suspected_behavior", "evidence", "observation", "candidate_hash", "limitations"]
    request["tools"].append(
        {
            "type": "function",
            "name": "finish_review",
            "strict": True,
            "description": "Return untrusted candidate-bound review advice.",
            "parameters": {
                "type": "object",
                "properties": {k: {"type": "string", "maxLength": 4000} for k in fields},
                "required": fields,
                "additionalProperties": False,
            },
        }
    )
    journal = DevJournal(root, "run_dev_scriptedreview")
    gateway = DevToolGateway(
        workspace=workspace,
        public_task=loaded.package.public,
        sandbox=LocalSandbox(),
        journal=journal,
        limits=loaded.envelope.limits,
    )
    try:
        while True:
            budget._ready()
            count = client.responses.input_tokens.count(**request).input_tokens
            admission = budget.admit(count)
            request["max_output_tokens"] = admission.output_ceiling
            journal.append("review_simulated_dispatch", {"request_hash": sha256_json(request)})
            response = client.responses.create(**request)
            usage = response.usage
            require(usage is not None, "unknown reviewer usage")
            budget.settle(
                usage.input_tokens, usage.input_tokens_details.cached_tokens, usage.output_tokens
            )
            calls = [c for c in response.output if c.type == "function_call"]
            require(bool(calls), "review response has no calls")
            if any(c.name == "finish_review" for c in calls):
                require(len(calls) == 1, "report cannot accompany tools")
                report = offline.handoff_report(
                    json.loads(calls[0].arguments), loaded.diff["patch_hash"]
                )
                journal.append("review_reported", {"report": report, "simulated": True})
                return report
            require(
                len(calls) <= 4
                and (
                    len(calls) == 1 or all(c.name in {"read_file", "search_files"} for c in calls)
                ),
                "invalid review batch",
            )
            for call in calls:
                budget.action(call.name)
                # Probe execution needs a real admitted probe sandbox; do not silently fake it.
                require(call.name != "run_probe", "offline reviewer probe NOT_RUN")
                args = json.loads(call.arguments)
                decision = args.pop("turn_decision")
                result = gateway.execute(
                    RequestedTool(
                        name=call.name,
                        action_id=call.call_id,
                        arguments=args,
                        turn_decision=decision,
                    )
                )
                request["input"].extend(
                    [
                        {
                            "type": "function_call",
                            "name": call.name,
                            "call_id": call.call_id,
                            "arguments": call.arguments,
                        },
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": canonical_json(result.model_dump(mode="json")),
                        },
                    ]
                )
    except Exception as exc:
        budget.fail()
        panel.append("panel_stopped", {"phase": "review", "reason": type(exc).__name__})
        raise


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
    source, sequence, output, arm, repair_client, *, reviewer_client=None, panel_root=None
):
    require(arm in {"A", "B", "C"}, "unknown arm")
    require(type(repair_client) is continuation.ScriptedClient, "scripted repair required")
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
    loaded = offline.load(source, sequence)  # Reject incompatible native runtime, including Conan.
    materialized = offline.restore(source, sequence, output)
    journal = DevJournal(output, source.run_id)
    panel.append("episode_started", {"arm": arm, "output": str(output.resolve())})
    budget = offline.SharedBudget()
    report = None
    if reviewer_client is not None:
        report = scripted_review(
            loaded,
            arm,
            output / "review",
            Path(materialized["workspace"]),
            reviewer_client,
            budget,
            panel,
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
        env_file=output / "NO_CREDENTIAL_FILE",
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
    branch = SimpleNamespace(
        root=output,
        store=ArtifactStore(output / "artifacts"),
        journal=journal,
        references=events[-2]["payload"]["artifact_references"],
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
    )
    journal.append(
        "review_repair_allowance",
        {
            "historical_cost": historical.spent_nanos,
            "simulated_review_cost": budget.ledger.spent_nanos,
            "review_calls": budget.calls,
            "review_actions": budget.actions,
            "limits": limits.model_dump(mode="json"),
            "new_cap_nanos": budget.ledger.cap_nanos,
            "report_is_not_check_credit": True,
        },
    )
    try:
        with patch.object(continuation, "first_input", lambda b: repair_inputs(b, report)):
            result = continuation.rehearse(branch, repair_client)
        if result["stop_remaining"] or not result["simulated_billing_known"]:
            panel.append("panel_stopped", {"phase": "repair", "output": str(output.resolve())})
        panel.append(
            "episode_finished", {"arm": arm, "output": str(output.resolve()), "receipt": result}
        )
        return result
    except Exception as exc:
        panel.append("panel_stopped", {"phase": "repair", "reason": type(exc).__name__})
        raise


def rehearse(
    source, sequence, output, arm, repair_client, *, reviewer_client=None, panel_root=None
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
        )
