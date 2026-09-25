from __future__ import annotations

import copy

from diagnostics import change_review as review


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


def test_seed_request_is_pure_and_not_a_synthetic_tool_mutation():
    events = [seed()]
    original = copy.deepcopy(events)
    a = review.review_request(state(), events)
    assert a == review.review_request(state(), events)
    assert events == original
    assert a["subject"] == {"origin": "imported_model_candidate", "action_id": None,
                            "diff_hash": "seed"}
    assert review.review_request(state("different"), events) is None
    assert review.review_request(state(), []) is None


def test_response_consumes_request_without_claiming_review_completed():
    events = [seed(), event("turn_decision_recorded"), event("segment_started")]
    assert review.review_request(state(), events) is None
    assert review.review_request(state(), copy.deepcopy(events)) is None


def test_real_mutation_rearms_after_its_preceding_decision():
    events = [seed(), event("turn_decision_recorded"), mutation()]
    result = review.review_request(state("changed"), events)
    assert result["subject"]["action_id"] == "edit"
    assert result["subject"]["origin"] == "successful_agent_mutation"
    events.append(event("segment_started"))
    assert review.review_request(state("changed"), events) == result
    events.append(event("turn_decision_recorded"))
    assert review.review_request(state("changed"), events) is None


def test_rejected_and_noop_edits_do_not_rearm():
    prefix = [seed(), event("turn_decision_recorded")]
    assert review.review_request(state(), prefix + [mutation(status="rejected")]) is None
    assert review.review_request(state(), prefix + [mutation("seed")]) is None


def test_reverting_candidate_is_a_distinct_successful_mutation():
    events = [seed(), event("turn_decision_recorded"), mutation(),
              event("turn_decision_recorded"), mutation("seed", action_id="revert")]
    assert review.review_request(state(), events)["subject"]["action_id"] == "revert"
