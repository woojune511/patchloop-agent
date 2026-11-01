from __future__ import annotations

import json

import httpx
import pytest
from test_dev_probes import FakeProbe, probe_call
from test_dev_segments import assert_submitted, configured, records

from diagnostics.segmented_input_audit import verify_turn
from patchloop.dev import repair_context, runner, working_plan
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.util import canonical_json

FINDING = "The first public probe supports only the small parser case."
QUESTION = "Does the complete public input preserve the quoted newline?"
PLAN = "Keep the complete-input question open; inspect the caller before editing."


class ContinuityScript(MockDevAdapter):
    number = 0

    def next_turn(self, context, tools):
        planning = "working_plan" in json.loads(context)
        number = self.number
        self.number += 1
        if number in (1, 3, 4, 5):
            call = probe_call(f"probe-{number}")
            call.arguments.update(
                question=f"Public parser observation {number}",
                python_source=f"print('case-{number}')",
            )
            turn = DevModelTurn(tool_calls=[call])
        elif number in (2, 6):
            turn = DevModelTurn(tool_calls=[RequestedTool(
                name="read_file", action_id=f"continuity-read-{number}",
                arguments={"path": self.mutation.path, "start_line": 1, "end_line": 40},
                turn_decision={"mode": "inspect", "basis": "Inspect the public caller.",
                               "evidence_goal": QUESTION},
            )])
        else:
            turn = super().next_turn(context, tools)
        # Null updates must preserve the last useful plan without extra actions.
        for call in turn.tool_calls:
            if call.turn_decision is not None:
                call.turn_decision.memory_update = None
                if planning:
                    call.turn_decision.plan_update = None
                    call.turn_decision.plan_update_reason = None
        if number == 2:
            decision = turn.tool_calls[0].turn_decision
            decision.memory_update = {
                "findings": [{"note_id": None, "statement": FINDING, "evidence": [
                    {"kind": "tool_result", "action_id": "probe-1"}]}],
                "remove_note_ids": [], "open_question": QUESTION,
            }
            if planning:
                decision.plan_update = PLAN
                decision.plan_update_reason = "The first probe leaves the complete input untested."
        return turn


@pytest.mark.parametrize("planning", ["none", "brief-v1"])
def test_actual_repair_input_retains_findings_questions_and_plan_after_probe_eviction(
    tmp_path, monkeypatch, planning,
):
    def forbidden(*args, **kwargs):
        pytest.fail("continuity verification must not call a real provider")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    backend = FakeProbe(status="passed")
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, planning=planning,
        script=ContinuityScript("csv-quoted-newline"),
    )
    request = request.model_copy(update={"enable_probes": True, "repair_recheck": True})
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert backend.calls == 4
    assert len(inputs) == len(counted) == 10
    assert inputs == counted
    assert result["call_counts"] == {"model": 10, "input_count": 10, "tool": 11}
    assert result["accepted_mutations"] == 1

    # The follow-up read completed a real result boundary. The old probe's body
    # left the recent tail, but its model-authored conclusion and question did not.
    state = views[7]
    assert repair_context.pending(state)
    assert state["segment_handoff"]["reason"] == "major_result_followup_completed"
    assert {p["action_id"] for p in state["recent_probes"]} == {
        "probe-3", "probe-4", "probe-5",
    }
    assert "case-1" not in canonical_json(inputs[7])
    for state in views[3:8]:
        notes = state["working_notes"]
        assert notes["available_note_ids"] == ["n1"]
        assert notes["open_question"] == QUESTION
        assert notes["findings"][0]["model_interpretation"] == FINDING
        assert notes["findings"][0]["evidence"][0]["action_id"] == "probe-1"
        assert notes["interpretation_status"] == "model_authored_unverified"
        assert notes["last_update_result"]["findings"][0]["status"] == "created"
        if planning == "none":
            assert "working_plan" not in state
            assert not state["segment_handoff"]["review_requested"]
        else:
            assert state["working_plan"]["plan"]["text"] == PLAN
            assert state["working_plan"]["plan"]["revision"] == 1
    if planning != "none":
        review = views[7]["working_plan"]["review_request"]
        assert review["requested"] and "context_handoff" in review["reasons"]
        assert views[7]["segment_handoff"]["review_requested"]
        assert working_plan.instructions(planning) in inputs[7][0]["content"]
    else:
        assert working_plan.INSTRUCTIONS not in inputs[7][0]["content"]

    journal, store = records(request)
    events = journal.events()
    assert len([e for e in events if e["event_type"] == "working_notes_updated"]) == 1
    turns = [e for e in events if e["event_type"] == "turn_started"]
    for event, actual in zip(turns, inputs, strict=True):
        assert verify_turn(event, events, store, actual_input=actual)["verified"]
    # Recovery reuses the completed run; it does not repeat probes or annotation writes.
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before and len(inputs) == 10 and backend.calls == 4
