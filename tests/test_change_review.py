from __future__ import annotations

import copy

import pytest

from diagnostics import change_review as review


@pytest.fixture(params=[review.POLICY, review.VALUE_ORIGIN_POLICY])
def request_review(request):
    def project(state, events):
        return review.review_request(state, events, policy=request.param)
    return project


def event(kind, **payload):
    return {"event_type": kind, "payload": payload}


def seed():
    return event("diagnostic_candidate_seeded", seed_hash="seed")


def state(diff="seed"):
    return {"current_diff": {"patch_hash": diff}}


def mutation(diff="changed", status="succeeded", action_id="edit"):
    return event("action_finished", result={
        "tool": "replace_text", "status": status, "action_id": action_id,
        "output": {"worktree_diff_hash": diff},
    })


def test_seed_request_is_pure_and_not_a_synthetic_tool_mutation(request_review):
    events = [seed()]
    original = copy.deepcopy(events)
    a = request_review(state(), events)
    assert a == request_review(state(), events)
    assert events == original
    assert a["subject"] == {"origin": "imported_model_candidate", "action_id": None,
                            "diff_hash": "seed"}
    assert request_review(state("different"), events) is None
    assert request_review(state(), []) is None


def test_response_consumes_request_without_claiming_review_completed(request_review):
    events = [seed(), event("turn_decision_recorded"), event("segment_started")]
    assert request_review(state(), events) is None
    assert request_review(state(), copy.deepcopy(events)) is None


def test_real_mutation_rearms_after_its_preceding_decision(request_review):
    events = [seed(), event("turn_decision_recorded"), mutation()]
    result = request_review(state("changed"), events)
    assert result["subject"]["action_id"] == "edit"
    assert result["subject"]["origin"] == "successful_agent_mutation"
    events.append(event("segment_started"))
    assert request_review(state("changed"), events) == result
    events.append(event("turn_decision_recorded"))
    assert request_review(state("changed"), events) is None


def test_rejected_and_noop_edits_do_not_rearm(request_review):
    prefix = [seed(), event("turn_decision_recorded")]
    assert request_review(state(), prefix + [mutation(status="rejected")]) is None
    assert request_review(state(), prefix + [mutation("seed")]) is None


def test_reverting_candidate_is_a_distinct_successful_mutation(request_review):
    events = [seed(), event("turn_decision_recorded"), mutation(),
              event("turn_decision_recorded"), mutation("seed", action_id="revert")]
    assert request_review(state(), events)["subject"]["action_id"] == "revert"


def test_policy_changes_only_the_review_question_and_its_identity():
    events = [seed(), event("turn_decision_recorded"), mutation()]
    a = review.review_request(state("changed"), events)
    assert a == review.review_request(state("changed"), events, policy=review.POLICY)
    b = review.review_request(state("changed"), events, policy=review.VALUE_ORIGIN_POLICY)
    assert b["policy"] == review.VALUE_ORIGIN_POLICY
    assert b["instruction"] != a["instruction"]
    assert {k: v for k, v in a.items() if k not in {"policy", "instruction"}} == {
        k: v for k, v in b.items() if k not in {"policy", "instruction"}}
