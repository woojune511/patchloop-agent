"""Unexplained plan deletion, evidence overclaim and submission remain separate."""
from __future__ import annotations

import copy
import json

import httpx
import pytest
from test_dev_planning import call, put, request, view

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import validate_tool_batch

OPEN = (
    "Check the public multiline CSV example on this patch; regression PASS alone is insufficient."
)
DONE = "The scoped repair is ready to submit."


@pytest.mark.parametrize("reason", [None, "", " \n", 1, True, {}, [], "x" * 801])
def test_regression_only_rewrite_without_reason_preserves_plan_and_action(tmp_path, reason):
    journal = DevJournal(tmp_path, "run_dev_revision")
    put(journal, OPEN)
    original = copy.deepcopy(view(journal)["plan"])
    journal.append("action_finished", {"result": {
        "tool": "run_check", "status": "succeeded", "action_id": "regression",
        "output": {"passed": True, "diff_hash": "d1"},
    }})
    selected = call(DONE, reason=reason, tool="run_check")
    assert validate_tool_batch([selected]) == "single_action"
    receipt = put(journal, turn="review", gate="ready_to_submit", calls=[selected])
    assert receipt["status"] == "rejected"
    assert "previous_plan_preserved" in receipt["diagnostics"][0]
    assert view(journal)["plan"] == original


def test_reason_and_predecessor_survive_handoff_null_updates_and_exact_replay(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_revision")
    put(journal, OPEN)
    reason = (
        "The additional delimiter-variation check is outside the public multiline requirement; "
        "source review is an inference, and no execution of that variation is claimed."
    )
    selected = call(DONE, reason=reason)
    receipt = put(journal, turn="review", calls=[selected])
    before = journal.path.read_bytes()
    assert put(journal, turn="review", calls=[call("different", reason="different")]) == receipt
    assert journal.path.read_bytes() == before
    journal.append("context_segment_started", {"segment_id": "new"})
    put(journal, turn="unchanged")
    state = {"working_plan": view(DevJournal(tmp_path, journal.run_id), diff="edited")}
    delivered = compact_model_state(state, [])  # No old native exchanges are available.
    plan = delivered["working_plan"]["plan"]
    assert plan["text"] == DONE and plan["diff_currency"] == "historical"
    assert plan["last_change"]["reason"] == reason
    assert plan["last_change"]["previous_plan"]["text"] == OPEN
    assert plan["last_change"]["interpretation_status"] == "model_authored_unverified"
    # No assertion about the reason's truth or the omitted behavior is manufactured.
    assert "verified" not in plan["last_change"]


def test_revision_chain_is_bounded_in_context_but_all_reasons_remain_in_journal(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_revision")
    put(journal, OPEN)
    for number in range(6):
        put(journal, turn=f"t{number + 2}", calls=[call(
            f"Remaining public work {number}", reason=f"Evidence interpretation {number}",
        )])
    latest = view(journal)["plan"]["last_change"]
    assert "last_change" not in latest["previous_plan"]
    assert latest["reason"] == "Evidence interpretation 5"
    revisions = [e["payload"]["plan"]["last_change"] for e in journal.events()[1:]]
    assert revisions[0]["previous_plan"]["text"] == OPEN
    assert [r["reason"] for r in revisions] == [f"Evidence interpretation {n}" for n in range(6)]


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("close_by_inference", [False, True])
def test_original_purpose_reaches_finish_without_forcing_another_check(
    tmp_path, monkeypatch, context_policy, close_by_inference,
):
    def forbidden(*args, **kwargs):
        pytest.fail("local plan evidence tests must not dispatch a provider request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    original = MockDevAdapter.next_turn
    seen = []
    reason = (
        "Original purpose: preserve a newline inside one quoted field. The current diff uses "
        "one csv.reader over io.StringIO instead of iterating physical lines. This is source "
        "inference, not an executed multiline reproduction; removing the per-line parser "
        "reset makes that separate reproduction nonblocking."
    )
    assessment = (
        "The current diff replaces per-line parsing with one reader over io.StringIO, so "
        "parser state spans embedded newlines. This is source inference for the original "
        "multiline purpose, not an executed reproduction. That reproduction remains "
        "unperformed but nonblocking for this scoped parser-lifetime repair. Required "
        "checks passed on this diff; that PASS does not establish multiline behavior."
    )

    def decide(self, context, tools):
        turn = original(self, context, tools)
        state = json.loads(context)
        seen.append(state)
        decision = turn.tool_calls[0].turn_decision
        decision.plan_update_reason = None
        decision.plan_update = OPEN if state["working_plan"]["plan"] is None else None
        if turn.tool_calls[0].name == "run_check":
            decision.plan_update = DONE
            decision.plan_update_reason = reason if close_by_inference else None
        if turn.tool_calls[0].name == "finish_task":
            turn.tool_calls[0].arguments["assessment"] = assessment
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", decide)
    req = request(tmp_path).model_copy(update={"context_policy": context_policy})
    run = runner.run_dev(req)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    assert run["cost_nanos"] == 0
    assert all(s["working_plan"]["plan"]["text"] == OPEN for s in seen[1:-1])
    events = DevJournal(tmp_path, run["run_id"]).events()
    final_turn = next(e["payload"] for e in reversed(events) if e["event_type"] == "turn_started")
    items = runner._load_active_model_input(
        final_turn, ArtifactStore(tmp_path / "artifacts"), context_policy=context_policy,
    )
    delivered = reconstruct_state(items, context_policy=context_policy)
    plan = delivered["working_plan"]["plan"]
    assert plan == seen[-1]["working_plan"]["plan"]
    assert plan["text"] == (DONE if close_by_inference else OPEN)
    if close_by_inference:
        assert plan["last_change"]["previous_plan"]["text"] == OPEN
        assert plan["last_change"]["reason"] == reason
        assert plan["last_change"]["interpretation_status"] == "model_authored_unverified"
    # Assert delivery at the actual finish boundary, not just the prompt constant.
    system = " ".join(items[0]["content"].split())
    assert "Suite PASS or another path's success cannot replace that purpose" in system
    assert "make verification conditional on a suite failure" in system
    assert "the original purpose despite plan changes: cite current-diff results" in system
    assert "Label source inference and tie it to specific current source" in system
    assert "leaving unexecuted behavior unverified" in system
    assert "No additional check is mandatory" in system
    assert delivered["current_diff"]["patch"] and "finish_task" in delivered["available_tool_names"]
    assert not any(e["event_type"] == "protocol_correction" for e in events)
    actions = [e["payload"]["result"]["tool"] for e in events
               if e["event_type"] == "action_finished"]
    assert set(actions[:2]) == {"search_files", "read_file"}
    assert actions[2:] == ["replace_text", "run_check", "finish_task"]
    finish = next(e["payload"]["result"] for e in events
                  if e["event_type"] == "action_finished"
                  and e["payload"]["result"]["tool"] == "finish_task")
    assert finish["status"] == "succeeded"
    review = finish["output"]["plan_review"]
    assert review["plan"] == plan
    assert review["assessment_ref"] == "assessment"
    assert review["verification_status"] == "not_inferred_from_submission"
    assert finish["output"][review["assessment_ref"]] == assessment
    before = DevJournal(tmp_path, run["run_id"]).path.read_bytes()
    assert runner.run_dev(req.model_copy(update={"resume_run_id": run["run_id"]}))["runs"][0] == run
    assert DevJournal(tmp_path, run["run_id"]).path.read_bytes() == before
