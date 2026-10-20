"""I4 continuation: remove ready finish advice, preserving I3 delivery and execution.

The single-row loop keeps I1's budget, terminal assessment and offline isolation
helpers. Public A/D/first-action and U/C/R seals precede assessments. CLI is provider-free.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from time import monotonic
from unittest.mock import patch

from diagnostics import isort_finish_checkpoint as checkpoint
from diagnostics import isort_finish_review as review
from diagnostics import isort_uptake_execution as baseline
from diagnostics import observation_exposure as exposure
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.decision_sampler import require
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import native_compaction, runner, segments
from patchloop.dev.state import DevJournal
from patchloop.repository import WorkspaceManager
from patchloop.runtime import git_commit, repository_root
from patchloop.util import canonical_json, sha256_json

BoundStop = baseline.BoundStop
Invocation = baseline.Invocation
RowBudget = baseline.RowBudget
retain_observation = checkpoint.retain_observation
remove_finish_advice = checkpoint.remove_finish_advice
seal_review = review.seal_review
submitted_assessment = review.submitted_assessment
file_reviewer = baseline.file_reviewer
inert_reviewer = baseline.inert_reviewer
offline_environment = baseline.offline_environment


def verify_first_input(branch, request):
    baseline.verify_first_input(branch, request)
    checkpoint.verify_feedback(branch.feedback, branch)
    branch.first_input_parity = checkpoint.compare_first_request(
        request, branch.expected_first_request
    )
    branch.first_request = copy.deepcopy(request)


def record_assembly(branch, ordinary, delivered):
    expected = json.loads(branch.expected_first_request["input"][-1]["content"])["state"]
    require(branch.feedback == expected[checkpoint.FIELD], "frozen operator data changed")
    require(branch.observed_candidate_diff == expected["current_diff"], "frozen patch changed")
    retained = checkpoint.retain_observation(
        ordinary, branch.feedback, branch.observed_candidate_diff
    )
    require(
        delivered == checkpoint.remove_finish_advice(retained), "non-treatment assembly changed"
    )
    state = json.loads(retained[-1]["content"])["state"]
    field = checkpoint.FIELD if checkpoint.FIELD in state else checkpoint.HISTORICAL_FIELD
    restored = copy.deepcopy(retained)
    view = json.loads(restored[-1]["content"])
    del view["state"][field]
    restored[-1]["content"] = canonical_json(view)
    require(restored == ordinary, "non-treatment recovery changed")
    # Invert only the two allowed fields, not the whole guidance object.
    recovered = copy.deepcopy(delivered)
    view = json.loads(recovered[-1]["content"])
    for key in ("message", "next_action"):
        view["state"]["completion_guidance"][key] = state["completion_guidance"][key]
    recovered[-1]["content"] = canonical_json(view)
    require(recovered == retained, "advice removal changed another field")
    record = {
        "ordinary_input": branch.store.put_json(ordinary).model_dump(mode="json"),
        "retained_input": branch.store.put_json(retained).model_dump(mode="json"),
        "delivered_input": branch.store.put_json(delivered).model_dump(mode="json"),
        "input_hash": sha256_json(delivered),
        "advice_stage": state["completion_guidance"]["stage"],
        "advice_removed": state["completion_guidance"]["stage"] == "ready_to_submit",
        "advice_parity": "PASS",
        "packet_hash": sha256_json(branch.feedback),
        "observed_diff_hash": branch.observed_candidate_diff["patch_hash"],
        "current_diff_hash": state["current_diff"]["patch_hash"],
        "placement": field,
        "segment_id": state["segment_handoff"]["segment_id"],
        "segment_review_requested": state["segment_handoff"]["review_requested"],
        "public_active_seconds": state["remaining_budget"]["active_wall_time_seconds"],
        "non_treatment_parity": "PASS",
    }
    branch.delivery_assemblies[record["input_hash"]] = record


def verify_delivery(branch, request):
    record = branch.delivery_assemblies.get(sha256_json(request["input"]))
    require(record is not None, "counted/dispatched input lacks ordinary assembly")
    ordinary = json.loads(checkpoint.read_bound(record["ordinary_input"]))
    retained = json.loads(checkpoint.read_bound(record["retained_input"]))
    delivered = json.loads(checkpoint.read_bound(record["delivered_input"]))
    require(request["input"] == delivered, "delivered input changed after assembly")
    require(
        retained
        == checkpoint.retain_observation(ordinary, branch.feedback, branch.observed_candidate_diff),
        "delivery data or currency changed",
    )
    require(delivered == checkpoint.remove_finish_advice(retained), "advice or input changed")
    require(
        WorkspaceManager.diff_summary(branch.workspace, deadline=branch.solver_deadline).patch_hash
        == record["current_diff_hash"],
        "delivery candidate changed after assembly",
    )
    return record


def run_row(branch, group, oracle_source, *, reviewer, client=None):
    require(
        branch.provider_free == isinstance(client, ScriptedClient),
        "finite offline transport required",
    )
    require(
        not any(
            e["event_type"] == "isort_finish_execution_started" for e in branch.journal.events()
        ),
        "row cannot be retried or resumed",
    )
    require(branch.envelope.runtime_hash == runner._runtime_hash(), "executing runtime changed")
    branch.journal.append(
        "isort_finish_execution_started",
        {
            "row": "I4",
            "synthetic": branch.provider_free,
            "harness_git_commit": git_commit(),
        },
    )
    budget = RowBudget(branch, group)
    build, count, active, boundary = (
        runner._build_model_input,
        native_compaction.count_prepared,
        runner._run_one_active,
        segments.boundary_reason,
    )
    requests, dispatched = [], []

    def assemble(**kwargs):
        items = build(**kwargs)
        retained = retain_observation(items, branch.feedback, branch.observed_candidate_diff)
        result = remove_finish_advice(retained)
        record_assembly(branch, items, result)
        return result

    def bounded_count(*args, **kwargs):
        budget.before_count()
        value = count(*args, **kwargs)
        if value[1] > 60000:
            raise BoundStop("continuation exceeds input-token bound")
        return value

    def bounded_active(**kwargs):
        kwargs["deadline"] = ExecutionDeadline(
            min(
                kwargs["deadline"].expires_at,
                branch.solver_deadline.expires_at,
                group.deadline.expires_at,
            ),
            group.clock,
        )
        kwargs["harness_git_commit"] = git_commit()
        return active(**kwargs)

    class Adapter(OpenAIResponsesAdapter):
        def __init__(self, config, **kwargs):
            super().__init__(config, **kwargs, **({"client": client} if client else {}))

        def count_input_tokens_v2(self, request, **kwargs):
            require(
                all(
                    request[k] == branch.selected[k]
                    for k in ("model", "reasoning", "service_tier", "max_output_tokens")
                ),
                "fixed continuation configuration changed",
            )
            if not budget.generations:
                verify_first_input(branch, request)
            verify_delivery(branch, request)
            requests.append(copy.deepcopy(request))
            method = super().count_input_tokens_v2
            tokens = budget.counted(request, lambda: method(request, **kwargs))
            branch.journal.append(
                "isort_finish_input_counted",
                {
                    "request_hash": sha256_json(request),
                    "input_tokens": tokens,
                    "synthetic": branch.provider_free,
                },
            )
            return tokens

        def execute_request(self, request, **kwargs):
            delivery = verify_delivery(branch, request)
            budget.dispatch(request, kwargs["requested_input_tokens"])
            branch.journal.append(
                "isort_finish_input_dispatched",
                {
                    **delivery,
                    "request_hash": sha256_json(request),
                    "generation": budget.generations,
                    "synthetic": branch.provider_free,
                    "elapsed_solver_seconds": group.clock() - group.started,
                },
            )
            if not dispatched:
                verify_first_input(branch, request)
                branch.journal.append(
                    "isort_finish_first_dispatch_input",
                    {
                        "request_hash": sha256_json(request),
                        "synthetic": branch.provider_free,
                        "feedback_hash": sha256_json(branch.feedback),
                        "model_authored": False,
                        "parity": branch.first_input_parity,
                    },
                )
            dispatched.append(sha256_json(request))
            return super().execute_request(request, **kwargs)

    result, reason, uncertain = None, None, False
    try:
        group.check()
        with (
            inherited_reads(branch),
            exposure.current_probe_receipts(branch),
            patch.object(runner, "_build_model_input", assemble),
            patch.object(native_compaction, "count_prepared", bounded_count),
            patch.object(
                segments,
                "boundary_reason",
                lambda *a, **k: boundary(*a, **k) if budget.generations else None,
            ),
            patch.object(runner, "_run_one_active", bounded_active),
            patch.object(runner, "OpenAIResponsesAdapter", Adapter),
            submitted_assessment(branch, group, oracle_source, reviewer),
            branch.journal.execution_lock(),
        ):
            result = runner._run_one_locked(
                request=branch.request,
                task_dir=branch.task_dir,
                package=branch.package,
                state_root=branch.root,
                pricing=branch.pricing,
                cost_ledger=budget,
                runtime_hash=branch.envelope.runtime_hash,
                model_hash=branch.envelope.model_hash,
                run_id=branch.journal.run_id,
                journal=branch.journal,
                envelope=branch.envelope,
                resuming=True,
            )
    except BoundStop as exc:
        reason, uncertain = exc.reason, exc.all_rows
    except Exception as exc:
        reason, uncertain = f"connector uncertainty: {type(exc).__name__}: {exc}", True
    known = (
        runner._provider_usage_failure(branch.journal) is None
        and branch.journal.unresolved_input_count() is None
    )
    uncertain |= not known or group.deadline.remaining_seconds() <= 0
    if result:
        uncertain |= result.stop_remaining or result.public["terminal"] in {
            "PREFLIGHT_FAILED",
            "PROVIDER_CONTINUATION_ERROR",
            "EVALUATOR_ERROR",
            "TASK_FAILED",
        }
    if not uncertain and not hasattr(branch, "public_review"):
        try:
            seal_review(branch, group, reviewer)
        except (Exception, BoundStop) as exc:
            reason, uncertain = f"public review stopped: {type(exc).__name__}: {exc}", True
    group.stopped |= uncertain
    events = branch.journal.events()[branch.inherited_events :]
    receipt = {
        "row": "I4",
        "synthetic": branch.provider_free,
        "result": result.public if result else None,
        "stop_reason": reason,
        "new_counts": budget.counts,
        "new_generations": budget.generations,
        "new_tool_actions": runner._restore_counters(branch.journal).tool_actions
        - branch.parent_actions,
        "accepted_new_edits": checkpoint.accepted_edits(events),
        "billing_known": known,
        "stop_remaining": uncertain,
        "provisional_cost_nanos": budget.spent_nanos - branch.initial_spent_nanos
        if known
        else None,
        "provider_calls": 0 if branch.provider_free else budget.counts + budget.generations,
        "billed_cost_nanos": 0 if branch.provider_free else None,
        "first_input_verified": bool(dispatched),
        "D": "NOT_RUN"
        if branch.provider_free
        else ("PASS" if dispatched and known else "UNKNOWN" if dispatched else "UNEXPOSED"),
        "first_request_hash": dispatched[0] if dispatched else None,
        "first_input_parity": getattr(branch, "first_input_parity", None),
        "U": branch.u_grade["U"] if hasattr(branch, "u_grade") else "NOT_RUN",
        "A": branch.u_grade["A"] if hasattr(branch, "u_grade") else "NOT_RUN",
        "first_response": branch.u_grade["first_response"]
        if hasattr(branch, "u_grade")
        else {"category": "NOT_OBSERVABLE"},
        "advice_removal_effect": "NOT_RUN" if branch.provider_free else "SEE_PUBLIC_AD_GRADE",
        "model_uptake": "NOT_RUN" if branch.provider_free else "SEE_PUBLIC_U_GRADE",
        "C": branch.u_grade["C"] if hasattr(branch, "u_grade") else "NOT_RUN",
        "R": branch.u_grade["R"] if hasattr(branch, "u_grade") else "NOT_RUN",
        "continuity_and_recheck_effect": "NOT_RUN"
        if branch.provider_free
        else "SEE_PUBLIC_CR_GRADE",
        "public_repair": getattr(branch, "public_repair", "NOT_RUN"),
        "public_review": branch.public_review.model_dump(mode="json")
        if hasattr(branch, "public_review")
        else None,
    }
    branch.journal.append("isort_finish_row_finished", receipt)
    group.journal.append("isort_finish_row_finished", receipt)
    return receipt


def rehearse(output):
    started = monotonic()
    plan, source, feedback = checkpoint.load_design()
    output = output.resolve()
    exposure.disjoint(output, (repository_root(), source.root, checkpoint.DESIGN.parent))
    output.mkdir()
    journal, store = DevJournal(output, "run_dev_isortfinishbridge"), ArtifactStore(output)
    group = Invocation(journal, started=started)
    journal.append(
        "isort_finish_mock_started",
        {
            "design_hash": checkpoint.DESIGN_HASH,
            "diagnostic_implementation_hash": exposure.implementation_hash(),
            "runtime_hash": runner._runtime_hash(),
            "harness_git_commit": git_commit(),
        },
    )
    branch = checkpoint.restore_branch(
        source,
        plan["inheritance"]["prepared_cut_sequence"],
        feedback,
        output / "I4",
        started=started,
        deadline=group.deadline,
    )
    client = ScriptedClient(
        [
            [
                {
                    "name": "read_file",
                    "action_id": "synthetic_read",
                    "arguments": {
                        "path": "isort/parse.py",
                        "start_line": 1,
                        "end_line": 60,
                        "turn_decision": {
                            "mode": "inspect",
                            "basis": "Synthetic connector verification.",
                            "evidence_goal": "Read restored public source.",
                            "memory_update": None,
                            "plan_update": None,
                        },
                    },
                }
            ],
            [
                {
                    "name": "stop_task",
                    "action_id": "synthetic_stop",
                    "arguments": {
                        "reason_code": "insufficient_public_evidence",
                        "summary": "Provider-free connector rehearsal only.",
                        "turn_decision": {
                            "mode": "stop",
                            "basis": "Synthetic connector verification complete.",
                            "evidence_goal": None,
                            "memory_update": None,
                            "plan_update": None,
                        },
                    },
                }
            ],
        ]
    )
    with offline_environment(branch, client):
        row = run_row(
            branch,
            group,
            checkpoint.read_bound(plan["terminal_public_oracle"]).decode(),
            reviewer=inert_reviewer,
            client=client,
        )
    checkpoint.load_design()
    require(
        row["result"]
        and row["result"]["terminal"] == "AGENT_STOPPED"
        and row["first_input_verified"]
        and not row["stop_remaining"]
        and row["C"] == "PASS"
        and row["R"] == "NOT_OBSERVABLE",
        "fixed I4 rehearsal did not complete",
    )
    first_ref = store.put_json(branch.first_request)
    result = {
        "official": False,
        "provider_free": True,
        "paid_authorized": False,
        "design_hash": checkpoint.DESIGN_HASH,
        "first_request": first_ref.model_dump(mode="json"),
        "row": row,
        "provider_calls": 0,
        "credential_reads": 0,
        "metadata_calls": 0,
        "billed_cost_nanos": 0,
        "actual_isort_probes": 0,
        "actual_isort_checks": 0,
        "actual_isort_acceptance": "NOT_RUN",
        "model_uptake": "NOT_RUN",
        "continuity_and_recheck_effect": "NOT_RUN",
        "advice_removal_effect": "NOT_RUN",
    }
    ref = store.put_json(result)
    journal.append("isort_finish_mock_finished", {"result": ref.model_dump(mode="json")})
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(result) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    print(canonical_json(rehearse(parser.parse_args().output)))


if __name__ == "__main__":
    main()
