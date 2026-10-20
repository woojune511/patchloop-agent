"""Public advice exposure, first action and unchanged U/C/R, sealed before assessments."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from diagnostics import isort_finish_checkpoint as checkpoint
from diagnostics import isort_retention_review as retention
from diagnostics import isort_uptake_execution as baseline
from diagnostics.decision_sampler import require
from patchloop.repository import WorkspaceManager


def review_evidence(branch, events):
    # The immutable C/R algorithm consumes the same delivery semantics.
    adapted = [
        {**event, "event_type": "isort_retention_input_dispatched"}
        if event["event_type"] == "isort_finish_input_dispatched"
        else event
        for event in events
    ]
    return retention.review_evidence(branch, adapted)


grade_cr = retention.grade_cr


def first_response(branch, events):
    new = [e for e in events if e["sequence"] > branch.inherited_events]
    decisions = [e for e in new if e["event_type"] == "turn_decision_recorded"]
    result = {"category": "NOT_OBSERVABLE", "decision_sequence": None, "action_sequences": []}
    if not decisions:
        return result
    decision = decisions[0]
    data = decision["payload"]
    result["decision_sequence"] = decision["sequence"]
    calls = data.get("tool_calls", [])
    if not calls or any(
        data.get(k) for k in ("error_code", "incomplete_reason", "tool_contract_failure")
    ):
        return result
    actions = [
        e
        for e in new
        if e["sequence"] > decision["sequence"]
        and e["event_type"] == "action_finished"
        and e["payload"]["result"]["action_id"] in {c["action_id"] for c in calls}
    ]
    result["action_sequences"] = [e["sequence"] for e in actions]
    result["tools"] = [c["name"] for c in calls]
    if len(actions) != len(calls) or any(
        e["payload"]["result"]["status"] != "succeeded" for e in actions
    ):
        return result
    tools = result["tools"]
    if tools == ["finish_task"]:
        patch = actions[0]["payload"]["result"]["output"].get("patch_hash")
        submissions = [
            e
            for e in new
            if e["event_type"] == "submission_recorded"
            and e["payload"]["patch_hash"] == patch == branch.observed_candidate_diff["patch_hash"]
            and e["sequence"] > actions[0]["sequence"]
        ]
        if submissions:
            result.update(
                category="IMMEDIATE_UNCHANGED_SUBMISSION",
                submission_sequence=submissions[0]["sequence"],
            )
    elif tools == ["stop_task"]:
        result["category"] = "STOP_WITHOUT_SUBMISSION"
    elif set(tools) <= {
        "read_file",
        "search_files",
        "run_probe",
        "replace_text",
        "run_check",
        "run_tests",
    }:
        result["category"] = "CONTINUES_WITH_PUBLIC_ACTION"
    return result


def advice_evidence(branch, events):
    new = [e for e in events if e["sequence"] > branch.inherited_events]
    deliveries = [e for e in new if e["event_type"] == "isort_finish_input_dispatched"]
    starts = [e for e in new if e["event_type"] == "provider_call_started"]
    counts = [e for e in new if e["event_type"] == "isort_finish_input_counted"]
    bound = bool(deliveries) and [e["payload"]["request_hash"] for e in starts] == [
        e["payload"]["request_hash"] for e in deliveries
    ]
    used_counts = set()
    for delivery in deliveries:
        matches = [
            e
            for e in counts
            if e["sequence"] < delivery["sequence"]
            and e["sequence"] not in used_counts
            and e["payload"]["request_hash"] == delivery["payload"]["request_hash"]
        ]
        bound &= bool(matches)
        if matches:
            used_counts.add(matches[-1]["sequence"])
        data = delivery["payload"]
        bound &= data["advice_parity"] == data["non_treatment_parity"] == "PASS"
        bound &= data["advice_removed"] == (data["advice_stage"] == "ready_to_submit")
    bound &= bool(deliveries) and deliveries[0]["payload"]["advice_removed"]
    return {
        "A": "PASS" if bound else "NOT_ASSESSABLE",
        "D": "PASS" if bound else "NOT_ASSESSABLE",
        "delivery_sequences": [e["sequence"] for e in deliveries],
        "count_sequences": sorted(used_counts),
        "provider_count_dispatch_binding": bool(bound),
        "first_response": first_response(branch, events),
        "synthetic_transport": branch.provider_free,
    }


@contextmanager
def submitted_assessment(branch, group, oracle_source, reviewer):
    # Preserve the original oracle/evaluation sequence and deadlines. Only the
    # public review includes the additional predeclared C/R axes.
    with (
        patch.object(baseline, "seal_review", seal_review),
        baseline.submitted_assessment(branch, group, oracle_source, reviewer),
    ):
        yield


def seal_review(branch, group, reviewer):
    """The callback performs semantic public-trace grading, never patch-only inference."""
    require(not hasattr(branch, "public_review"), "public review cannot be repeated")
    group.check()
    summary = WorkspaceManager.diff_summary(branch.workspace, deadline=group.deadline)
    public_types = {
        "action_started",
        "action_finished",
        "turn_decision_recorded",
        "working_notes_updated",
        "working_plan_updated",
        "isort_finish_input_dispatched",
        "isort_finish_input_counted",
        "provider_call_started",
        "submission_recorded",
    }
    events = [
        {
            "sequence": e["sequence"],
            "event_type": e["event_type"],
            "payload": {k: v for k, v in e["payload"].items() if k != "continuation_ref"},
        }
        for e in branch.journal.events()
        if e["event_type"] in public_types
    ]
    cr = review_evidence(branch, events)
    advice = advice_evidence(branch, events)
    require(
        not advice["delivery_sequences"] or advice["A"] == "PASS",
        "advice count/dispatch exposure is not assessable",
    )
    review = {
        "public_task": branch.package.public.model_dump(mode="json"),
        "operator_observation": branch.feedback,
        "observed_candidate_diff": branch.observed_candidate_diff,
        "continuity_and_recheck": cr,
        "advice_and_first_response": advice,
        "public_events": events,
        "new_events_after": branch.inherited_events,
        "final_patch": summary.patch,
        "patch_hash": summary.patch_hash,
        "submitted": any(e["event_type"] == "submission_recorded" for e in branch.journal.events()),
        "terminal_assessments_present": False,
        "synthetic_transport": branch.provider_free,
    }
    ref = branch.store.put_json(review)
    branch.journal.append("isort_uptake_public_review", {"artifact": ref.model_dump(mode="json")})
    grade = reviewer(ref, review, group.deadline)
    group.check()
    require(grade["review_hash"] == ref.content_hash, "U review binding changed")
    require(
        grade["U"] in {"PASS", "FAIL", "NOT_OBSERVABLE"} and grade["reason"],
        "semantic public U grade required",
    )
    by_sequence = {e["sequence"]: e for e in events}
    citations = grade["public_event_sequences"]
    require(set(citations) <= by_sequence.keys(), "U citation is not a public event")
    if grade["U"] == "PASS":
        require(
            grade["observation_case_ids"]
            and set(grade["observation_case_ids"])
            <= {c["case_id"] for c in branch.feedback["cases"]},
            "U PASS needs specific public observation citations",
        )
        edits = [
            by_sequence[s]
            for s in citations
            if s > branch.inherited_events
            and by_sequence[s]["event_type"] == "action_finished"
            and checkpoint.accepted_edits([by_sequence[s]])
            and s in cr["new_nonnoop_source_edit_sequences"]
        ]
        explanations = [
            by_sequence[s]
            for s in citations
            if by_sequence[s]["event_type"]
            in {
                "action_started",
                "turn_decision_recorded",
                "working_notes_updated",
                "working_plan_updated",
            }
        ]
        require(
            edits
            and explanations
            and min(e["sequence"] for e in explanations) <= max(e["sequence"] for e in edits),
            "U PASS lacks explanation/accepted-edit linkage",
        )
    elif grade["U"] == "FAIL":
        require(citations, "U FAIL requires public evidence, not a resource cutoff")
    grade = {
        **grade,
        **grade_cr(cr, grade.get("probe_reviews", []), branch.feedback),
        "A": advice["A"],
        "D": advice["D"],
        "first_response": advice["first_response"],
        "advice_evidence": advice,
    }
    branch.public_review, branch.u_grade = ref, grade
    branch.journal.append("isort_finish_AD_sealed", grade)
    branch.journal.append("isort_uptake_U_sealed", grade)
    branch.journal.append("isort_finish_CR_sealed", grade)
    return grade
