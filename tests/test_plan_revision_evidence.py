"""Unexplained plan deletion, evidence overclaim and submission remain separate."""
from __future__ import annotations

import copy
import json

import httpx
import pytest
from test_dev_planning import call, put, request, view

from patchloop.dev import runner
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
def test_unexplained_deletion_needs_no_extra_call_and_finish_binds_plan_assessment(
    tmp_path, monkeypatch, context_policy,
):
    def forbidden(*args, **kwargs):
        pytest.fail("local plan evidence tests must not dispatch a provider request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    original = MockDevAdapter.next_turn
    seen = []

    def decide(self, context, tools):
        turn = original(self, context, tools)
        state = json.loads(context)
        seen.append(state)
        decision = turn.tool_calls[0].turn_decision
        decision.plan_update_reason = None
        decision.plan_update = OPEN if state["working_plan"]["plan"] is None else DONE
        if turn.tool_calls[0].name == "finish_task":
            decision.plan_update = None
            turn.tool_calls[0].arguments["assessment"] = (
                "The registered CSV assertions passed. The optional broader variation remains "
                "untested and is outside the public requirement; ready on that limited evidence."
            )
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", decide)
    req = request(tmp_path).model_copy(update={"context_policy": context_policy})
    run = runner.run_dev(req)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    assert run["cost_nanos"] == 0
    assert all(s["working_plan"]["plan"]["text"] == OPEN for s in seen[1:])
    events = DevJournal(tmp_path, run["run_id"]).events()
    assert not any(e["event_type"] == "protocol_correction" for e in events)
    finish = next(e["payload"]["result"] for e in events
                  if e["event_type"] == "action_finished"
                  and e["payload"]["result"]["tool"] == "finish_task")
    assert finish["status"] == "succeeded"
    review = finish["output"]["plan_review"]
    assert review["plan"]["text"] == OPEN
    assert review["assessment_ref"] == "assessment"
    assert review["verification_status"] == "not_inferred_from_submission"
    assert "untested" in finish["output"][review["assessment_ref"]]
    before = DevJournal(tmp_path, run["run_id"]).path.read_bytes()
    assert runner.run_dev(req.model_copy(update={"resume_run_id": run["run_id"]}))["runs"][0] == run
    assert DevJournal(tmp_path, run["run_id"]).path.read_bytes() == before
