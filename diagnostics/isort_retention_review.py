"""Public U/C/R review, sealed before either terminal assessment."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from diagnostics import isort_retention_checkpoint as checkpoint
from diagnostics import isort_uptake_execution as baseline
from diagnostics.decision_sampler import require
from patchloop.repository import WorkspaceManager


def review_evidence(branch, events):
    new = [e for e in events if e["sequence"] > branch.inherited_events]
    seed = branch.observed_candidate_diff["patch_hash"]
    edits = []
    for event in new:
        if checkpoint.accepted_edits([event]):
            output = event["payload"]["result"]["output"]
            if output.get("worktree_diff_hash") not in {
                None,
                seed,
                output.get("baseline_diff_hash"),
            }:
                edits.append(event)
    cutoff = edits[0]["sequence"] if edits else float("inf")
    deliveries = [e for e in new if e["event_type"] == "isort_retention_input_dispatched"]
    starts = [e for e in new if e["event_type"] == "provider_call_started"]
    dispatch_binding = [e["payload"]["request_hash"] for e in starts] == [
        e["payload"]["request_hash"] for e in deliveries
    ]
    initial = deliveries[0]["payload"]["segment_id"] if deliveries else None
    qualifying = [
        e["sequence"]
        for e in deliveries[1:]
        if e["sequence"] < cutoff
        and e["payload"]["segment_id"] != initial
        and e["payload"]["current_diff_hash"] == seed
        and e["payload"]["placement"] == checkpoint.FIELD
        and e["payload"]["non_treatment_parity"] == "PASS"
    ]
    probes = []
    for event in new:
        if event["event_type"] != "action_finished" or event["sequence"] >= cutoff:
            continue
        result = event["payload"]["result"]
        # A rejected/non-executed call is not an executed probe. Missing receipt
        # identity on an executed result is retained for an unobservable grade.
        if result["tool"] == "run_probe" and result["status"] == "succeeded":
            probes.append(
                {
                    "sequence": event["sequence"],
                    "action_id": result["action_id"],
                    "receipt_diff_hash": result["output"].get("diff_hash"),
                }
            )
    return {
        "C": "NOT_ASSESSABLE"
        if not dispatch_binding
        else "PASS"
        if qualifying
        else "NOT_EXERCISED",
        "qualifying_dispatch_sequences": qualifying,
        "delivery_sequences": [e["sequence"] for e in deliveries],
        "provider_dispatch_binding": dispatch_binding,
        "new_nonnoop_source_edit_sequences": [e["sequence"] for e in edits],
        "first_edit_sequence": None if not edits else edits[0]["sequence"],
        "pre_edit_probe_actions": probes,
        "observed_seed_diff_hash": seed,
        "review_instruction": (
            "Classify every listed executed pre-edit probe from its public arguments/results. "
            "For each provide sequence, same_case_ownership_recheck (true/false/null), "
            "case_ids, strict_identical_replay (true/false/null), configuration_coverage "
            "and reason. Changed settings do not exempt same-case ownership rechecks. "
            "Use null when evidence is insufficient. No target execution or private result."
        ),
    }


def grade_cr(evidence, reviews, feedback):
    require(isinstance(reviews, list), "public probe classifications required")
    expected = {p["sequence"]: p for p in evidence["pre_edit_probe_actions"]}
    require(
        len(reviews) == len(expected) and {r["sequence"] for r in reviews} == expected.keys(),
        "every executed pre-edit probe needs exactly one public classification",
    )
    known, strict, unknown, strict_unknown = 0, 0, 0, 0
    for item in reviews:
        flag, exact = item["same_case_ownership_recheck"], item["strict_identical_replay"]
        require(type(flag) is bool or flag is None, "invalid recheck classification")
        require(type(exact) is bool or exact is None, "invalid strict replay classification")
        require(
            item["reason"] and item["configuration_coverage"], "public probe rationale required"
        )
        require(
            set(item["case_ids"]) <= {c["case_id"] for c in feedback["cases"]},
            "probe case citation changed",
        )
        receipt_diff = expected[item["sequence"]]["receipt_diff_hash"]
        if receipt_diff is None:
            require(flag is None and exact is None, "missing candidate identity is unobservable")
        elif receipt_diff != evidence["observed_seed_diff_hash"]:
            require(flag is False and exact is False, "different-candidate probe is outside metric")
        if flag:
            require(item["case_ids"], "counted probe needs a known case input")
        if exact:
            require(flag is True, "strict replay must also be a same-case recheck")
        known += flag is True
        strict += exact is True
        unknown += flag is None
        strict_unknown += exact is None
    grade = (
        "FAIL"
        if known
        else "NOT_OBSERVABLE"
        if unknown or not evidence["new_nonnoop_source_edit_sequences"]
        else "PASS"
    )
    return {
        "C": evidence["C"],
        "R": grade,
        "same_case_recheck_count": known if not unknown else None,
        "known_same_case_recheck_count": known,
        "strict_identical_replay_count": strict if not strict_unknown else None,
        "unclassified_probe_count": unknown,
        "qualifying_dispatch_sequences": evidence["qualifying_dispatch_sequences"],
        "first_edit_sequence": evidence["first_edit_sequence"],
        "probe_reviews": reviews,
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
        "isort_retention_input_dispatched",
        "provider_call_started",
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
    review = {
        "public_task": branch.package.public.model_dump(mode="json"),
        "operator_observation": branch.feedback,
        "observed_candidate_diff": branch.observed_candidate_diff,
        "continuity_and_recheck": cr,
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
        ]
        explanations = [
            by_sequence[s]
            for s in citations
            if by_sequence[s]["event_type"]
            in {"action_started", "turn_decision_recorded", "working_notes_updated"}
        ]
        require(
            edits
            and explanations
            and min(e["sequence"] for e in explanations) <= max(e["sequence"] for e in edits),
            "U PASS lacks explanation/accepted-edit linkage",
        )
    elif grade["U"] == "FAIL":
        require(citations, "U FAIL requires public evidence, not a resource cutoff")
    grade = {**grade, **grade_cr(cr, grade.get("probe_reviews", []), branch.feedback)}
    branch.public_review, branch.u_grade = ref, grade
    branch.journal.append("isort_uptake_U_sealed", grade)
    branch.journal.append("isort_retention_CR_sealed", grade)
    return grade
