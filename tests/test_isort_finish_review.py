"""Predeclared C/R semantics from public records, without a model or target run."""

from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from diagnostics import isort_finish_checkpoint as checkpoint
from diagnostics import isort_finish_review as review
from patchloop.errors import ContractError


def evidence(*, edited=True, probe=True, diff="seed"):
    return {
        "C": "PASS",
        "observed_seed_diff_hash": "seed",
        "pre_edit_probe_actions": [{"sequence": 4, "receipt_diff_hash": diff}] if probe else [],
        "new_nonnoop_source_edit_sequences": [5] if edited else [],
        "first_edit_sequence": 5 if edited else None,
        "qualifying_dispatch_sequences": [2],
    }


FEEDBACK = {"cases": [{"case_id": "type_item"}, {"case_id": "type_opening"}]}


def classification(flag=True, strict=False):
    return {
        "sequence": 4,
        "same_case_ownership_recheck": flag,
        "strict_identical_replay": strict,
        "case_ids": ["type_item"] if flag else [],
        "configuration_coverage": "Different line length, same input and ownership question.",
        "reason": "Public program and result are cited; no hidden outcome.",
    }


@pytest.mark.parametrize(
    "flag,strict,expected",
    [
        (True, False, "FAIL"),
        (True, True, "FAIL"),
        (False, False, "PASS"),
        (None, None, "NOT_OBSERVABLE"),
    ],
)
def test_changed_configuration_is_not_an_exception(flag, strict, expected):
    grade = review.grade_cr(evidence(), [classification(flag, strict)], FEEDBACK)
    assert grade["R"] == expected
    assert grade["strict_identical_replay_count"] == (None if strict is None else int(strict))


@pytest.mark.parametrize("edited", [True, False])
def test_zero_checks_needs_an_edit(edited):
    grade = review.grade_cr(evidence(edited=edited, probe=False), [], FEEDBACK)
    assert grade["R"] == ("PASS" if edited else "NOT_OBSERVABLE")


@pytest.mark.parametrize(
    "invalid",
    [
        "missing",
        "duplicate",
        "invented",
        "integer",
        "case",
        "strict_only",
        "reason",
        "candidate",
        "unknown_identity",
    ],
)
def test_classification_cannot_silently_skip_or_relabel_a_probe(invalid):
    data, rows = evidence(), [classification()]
    if invalid == "missing":
        rows = []
    elif invalid == "duplicate":
        rows *= 2
    elif invalid == "invented":
        rows[0]["sequence"] = 8
    elif invalid == "integer":
        rows[0]["same_case_ownership_recheck"] = 1
    elif invalid == "case":
        rows[0]["case_ids"] = ["private-case"]
    elif invalid == "strict_only":
        rows[0].update(same_case_ownership_recheck=False, strict_identical_replay=True)
    elif invalid == "reason":
        rows[0]["reason"] = ""
    else:
        data["pre_edit_probe_actions"][0]["receipt_diff_hash"] = (
            None if invalid == "unknown_identity" else "new-diff"
        )
    with pytest.raises(ContractError):
        review.grade_cr(data, rows, FEEDBACK)


def public_event(sequence, kind, payload):
    return {"sequence": sequence, "event_type": kind, "payload": payload}


def delivery(sequence, segment="later", diff="seed"):
    return public_event(
        sequence,
        "isort_finish_input_dispatched",
        {
            "request_hash": f"request-{sequence}",
            "segment_id": segment,
            "current_diff_hash": diff,
            "placement": checkpoint.FIELD,
            "non_treatment_parity": "PASS",
        },
    )


def action(sequence, tool, output, status="succeeded"):
    return public_event(
        sequence,
        "action_finished",
        {
            "result": {
                "tool": tool,
                "status": status,
                "action_id": f"a{sequence}",
                "error_code": None,
                "output": output,
            }
        },
    )


def test_continuity_requires_dispatch_on_seed_before_edit_and_ignores_late_probes():
    branch = SimpleNamespace(inherited_events=0, observed_candidate_diff={"patch_hash": "seed"})
    edit = action(50, "replace_text", {"worktree_diff_hash": "new", "baseline_diff_hash": "seed"})
    events = [
        delivery(10, "initial"),
        delivery(20),
        action(40, "run_probe", {"diff_hash": "seed"}),
        edit,
        action(80, "run_probe", {"diff_hash": "new"}),
    ]

    def dispatched(trace):
        result = []
        for event in trace:
            if event["event_type"] == "isort_finish_input_dispatched":
                result.append(
                    public_event(
                        event["sequence"] - 1,
                        "provider_call_started",
                        {
                            "request_hash": event["payload"]["request_hash"],
                        },
                    )
                )
            result.append(event)
        return result

    result = review.review_evidence(branch, dispatched(events))
    assert result["C"] == "PASS" and result["qualifying_dispatch_sequences"] == [20]
    assert [e["sequence"] for e in result["pre_edit_probe_actions"]] == [40]
    assert review.review_evidence(branch, events)["C"] == "NOT_ASSESSABLE"
    for altered in (
        [events[0], edit, delivery(60)],
        [events[0], delivery(20, "initial"), edit],
        [events[0], delivery(20, diff="new"), edit],
    ):
        assert review.review_evidence(branch, dispatched(altered))["C"] == "NOT_EXERCISED"
    noop = copy.deepcopy(edit)
    noop["payload"]["result"]["output"]["worktree_diff_hash"] = "seed"
    assert review.review_evidence(branch, [events[0], noop])["first_edit_sequence"] is None


def test_known_recheck_failure_does_not_become_pass_with_unclassified_probe():
    data = evidence()
    data["pre_edit_probe_actions"].append({"sequence": 9, "receipt_diff_hash": None})
    uncertain = {**classification(None, None), "sequence": 9}
    grade = review.grade_cr(data, [classification(), uncertain], FEEDBACK)
    assert grade["R"] == "FAIL" and grade["same_case_recheck_count"] is None
    assert grade["known_same_case_recheck_count"] == grade["unclassified_probe_count"] == 1


@pytest.mark.parametrize(
    "tool,executed,submitted,expected",
    [
        ("finish_task", True, True, "IMMEDIATE_UNCHANGED_SUBMISSION"),
        ("finish_task", True, False, "NOT_OBSERVABLE"),
        ("finish_task", False, False, "NOT_OBSERVABLE"),
        ("stop_task", True, False, "STOP_WITHOUT_SUBMISSION"),
        ("read_file", True, False, "CONTINUES_WITH_PUBLIC_ACTION"),
        ("replace_text", True, False, "CONTINUES_WITH_PUBLIC_ACTION"),
    ],
)
def test_first_response_uses_executed_batch_and_actual_submission(
    tool, executed, submitted, expected
):
    branch = SimpleNamespace(inherited_events=0, observed_candidate_diff={"patch_hash": "seed"})
    events = [
        public_event(
            2,
            "turn_decision_recorded",
            {
                "tool_calls": [{"name": tool, "action_id": "a3"}],
            },
        )
    ]
    if executed:
        events.append(action(3, tool, {"patch_hash": "seed"}))
    if submitted:
        events.append(public_event(4, "submission_recorded", {"patch_hash": "seed"}))
    assert review.first_response(branch, events)["category"] == expected
    events[0]["payload"]["tool_contract_failure"] = "invalid batch"
    assert review.first_response(branch, events)["category"] == "NOT_OBSERVABLE"


@pytest.mark.parametrize("missing", [None, "count", "start", "advice", "parity"])
def test_advice_exposure_requires_matching_count_dispatch_and_subtraction(missing):
    branch = SimpleNamespace(
        inherited_events=0,
        observed_candidate_diff={"patch_hash": "seed"},
        provider_free=True,
    )
    delivered = delivery(4, "initial")
    delivered["payload"].update(
        advice_removed=True, advice_stage="ready_to_submit", advice_parity="PASS"
    )
    events = [
        public_event(1, "isort_finish_input_counted", {"request_hash": "request-4"}),
        public_event(3, "provider_call_started", {"request_hash": "request-4"}),
        delivered,
    ]
    if missing == "count":
        events.pop(0)
    elif missing == "start":
        events.pop(1)
    elif missing == "advice":
        delivered["payload"]["advice_removed"] = False
    elif missing == "parity":
        delivered["payload"]["non_treatment_parity"] = "FAIL"
    grade = review.advice_evidence(branch, events)
    assert grade["A"] == grade["D"] == ("PASS" if missing is None else "NOT_ASSESSABLE")
    assert grade["first_response"]["category"] == "NOT_OBSERVABLE"
