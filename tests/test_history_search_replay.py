from __future__ import annotations

import copy

from test_size_only_replay import saved as saved

from diagnostics import history_search_replay as replay
from diagnostics.size_only_replay import TokenEstimator
from patchloop.dev import history_search as search
from patchloop.dev.conversation import reconstruct_state


def test_query_uses_only_current_question_else_plan_else_public_issue():
    state = {"working_notes": {"open_question": {"text": "current question"}},
             "working_plan": {"plan": {"text": "current plan"}},
             "public_task": {"issue": {"description": "public report"}},
             "private_grade": "never query this"}
    assert replay.query_for(state) == ("current question", "open_question")
    state["working_notes"]["open_question"] = None
    assert replay.query_for(state) == ("current plan", "working_plan")
    state["working_plan"]["plan"] = None
    assert replay.query_for(state) == ("public report", "public_task")
    state["public_task"] = {}
    assert replay.query_for(state) == (None, "empty")
    state["working_notes"]["open_question"] = "x" * 1000
    assert len(replay.query_for(state)[0]) == 800


def test_public_search_packing_delivers_exact_body_and_keeps_source_and_refs(saved):
    turns = copy.deepcopy(saved)
    for turn in turns:
        turn.usage["input_tokens"] = 20_000
    estimator = TokenEstimator(lambda text: list(text[::4]), {}, turns)
    history = search.PublicHistory()
    for turn in turns[:2]:
        history.ingest(turn.wire["input"], sequence=turn.sequence,
                       turn_id=turn.turn["turn_id"], input_hash=turn.turn["model_input_hash"])
    result = history.search("parse_rows", current_diff_hash="different")
    assert result["records"]
    original = copy.deepcopy(turns[1])
    packed, items = replay.pack_result(turns[1], result, estimator)
    assert packed["fits_known_content"] and packed["mode"] == "same_segment"
    assert not packed["lost_sources"] and not packed["lost_outputs"]
    assert not packed["lost_observations"]
    assert turns[1] == original
    state = reconstruct_state(items, context_policy="segmented-v1")
    assert state["remaining_budget"]["model_calls"] == (
        original.state["remaining_budget"]["model_calls"] - 1)
    assert len((state["working_notes"].get("open_question") or {}).get("evidence", [])) <= 2
    # Tool queries permit 800 chars; the separate public decision goal permits 500.
    long_query = {**result, "query": "x" * 800}
    packed, _ = replay.pack_result(turns[1], long_query, estimator)
    assert packed["fits_known_content"] and long_query["query"] == "x" * 800


def test_search_result_size_uses_existing_handoff_not_larger_cap(saved):
    turns = copy.deepcopy(saved)
    for turn in turns:
        turn.usage["input_tokens"] = 59_990
    estimator = TokenEstimator(lambda text: list(text[::4]), {}, turns)
    history = search.PublicHistory()
    turn = turns[1]
    history.ingest(turn.wire["input"], sequence=turn.sequence,
                   turn_id="t", input_hash="input")
    result = history.search("parse_rows", current_diff_hash="different")
    packed, _ = replay.pack_result(turn, result, estimator)
    assert packed["attempts"][0]["reasons"] == ["input_tokens"]
    assert packed["mode"] != "same_segment"
    # A fresh seed can still be too large; the diagnostic never raises the limit.
    if packed["fits_known_content"]:
        assert packed["attempts"][-1]["counts_before_unknown_search_reasoning"]["central"] <= 60_000


def test_search_completes_major_result_followup_even_with_plenty_of_context_space(saved):
    turns = copy.deepcopy(saved)
    for turn in turns:
        turn.usage["input_tokens"] = 20_000
    estimator = TokenEstimator(lambda text: list(text[::4]), {}, turns)
    turn = turns[2]  # The actual mutation has returned; this decision reviews its result.
    history = search.PublicHistory()
    history.ingest(turn.wire["input"], sequence=turn.sequence, turn_id="t", input_hash="input")
    result = history.search("parse_rows", current_diff_hash="different")
    packed, items = replay.pack_result(turn, result, estimator)
    assert packed["mode"] == "major_result_handoff"
    assert packed["already_due_result_boundary"] == "major_result_followup_completed"
    assert packed["attempts"][0]["reasons"] == ["major_result_followup_completed"]
    state = reconstruct_state(items, context_policy="segmented-v1")
    assert state["segment_handoff"]["review_requested"]
    assert "context_handoff" in state["working_plan"]["review_request"]["reasons"]
