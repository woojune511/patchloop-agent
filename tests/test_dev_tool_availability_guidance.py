"""Public completion guidance reaches real inputs without changing tool admission."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from test_dev_feedback_integration_v18 import _context
from test_dev_mutation_attempt_budget import _state
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import (
    DevLimits,
    DevModelTurn,
    DevRunRequest,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("tool-availability verification must not dispatch a network request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_actual_inputs_explain_source_edit_check_submit_transitions(
    tmp_path, monkeypatch, context_policy,
):
    captured = []
    unfinished_plan = (
        "Required behavior: keep a quoted newline inside one CSV field. "
        "Optional duplicate verification, still unperformed: rerun the registered check. "
        "Purpose: observe multiline field preservation and existing parser behavior. "
        "Before submission, decide whether the current check already serves that purpose."
    )
    assessment = (
        "The parser uses one reader for the input, and required public checks pass on this "
        "unchanged patch. Repeating the same check would add no evidence for the optional "
        "plan's purpose, so it remains unperformed. Other inputs remain unverified."
    )

    class CapturingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            state = json.loads(context)
            guidance = state["completion_guidance"]
            names = {tool["name"] for tool in tools}
            if guidance["stage"] == "ready_to_submit":
                assert guidance["next_action"] is None
                assert "assessment" in guidance["message"]
            else:
                assert guidance["next_action"]["tool"] in names
            assert set(state["available_tool_names"]) == names
            captured.append(guidance)
            turn = super().next_turn(context, tools)
            for call in turn.tool_calls:
                # Scripted public statements exercise transport, not model judgment quality.
                call.turn_decision.plan_update = (
                    unfinished_plan if call.name == "run_check" else None
                )
                if call.name == "finish_task":
                    call.arguments["assessment"] = assessment
            return turn

    monkeypatch.setattr(runner, "MockDevAdapter", CapturingMock)
    state_root = tmp_path / context_policy
    request = DevRunRequest(
        provider="mock", model="mock-dev", state_root=state_root,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy, planning_policy="brief-v1",
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["accepted_mutations"] == 1
    assert run["evaluator"]["claim_eligible"] is False
    journal = DevJournal(state_root, run["run_id"])
    store = ArtifactStore(state_root / "artifacts")
    turns = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"]
    inputs = [runner._load_active_model_input(t, store, context_policy=context_policy)
              for t in turns]
    states = [reconstruct_state(i, context_policy=context_policy) for i in inputs]
    assert [s["completion_guidance"] for s in states] == captured
    assert [g["stage"] for g in captured] == [
        "needs_source_evidence", "needs_mutation", "needs_visible_checks", "ready_to_submit",
    ]
    assert all(i[0]["content"].startswith(DEV_SYSTEM_PROMPT) for i in inputs)
    initial = states[0]
    assert initial["mutation_readiness"]["state"] == "needs_anchor_evidence"
    assert initial["action_horizon"]["completion_possible"]
    assert not initial["action_horizon"]["mutation_completion_horizon"]["minimum_possible"]
    assert "replace_text" not in initial["available_tool_names"]
    assert "temporarily unavailable" in captured[0]["message"]
    assert "reevaluated with remaining budgets" in captured[0]["message"]
    assert "replace_text" in states[1]["available_tool_names"]
    assert states[1]["mutation_readiness"]["state"] == "ready_to_attempt"
    assert all(s["public_task"] == initial["public_task"] for s in states)
    assert initial["current_diff"]["patch"] == states[1]["current_diff"]["patch"] == ""
    assert states[2]["current_diff"]["patch"] == states[3]["current_diff"]["patch"] != ""
    assert states[2]["visible_check_status"][0]["status"] == "NOT_RUN"
    assert states[3]["visible_check_status"][0]["status"] == "PASS"
    assert "finish_task" not in states[2]["available_tool_names"]
    assert "finish_task" in states[3]["available_tool_names"]
    final = states[-1]
    assert final["working_plan"]["plan"]["text"] == unfinished_plan
    assert final["working_plan"]["plan"]["diff_currency"] == "current"
    assert final["working_plan"]["interpretation_status"] == "model_authored_unverified"
    assert "check_result" in final["working_plan"]["review_request"]["reasons"]
    assert "unfinished verification" in final["completion_guidance"]["message"]
    system = inputs[-1][0]["content"]
    assert "Skipped/rejected verification remains unperformed." in system
    assert "listing a limitation is insufficient" in system
    assert "Keep unfinished verification" in system
    assert "This judgment needs no separate call or mandatory experiment." in system
    results = [e["payload"]["result"] for e in journal.events()
               if e["event_type"] == "action_finished"]
    assert {result["tool"] for result in results[:2]} == {"search_files", "read_file"}
    assert [result["tool"] for result in results[2:]] == [
        "replace_text", "run_check", "finish_task",
    ]
    assert results[-1]["output"]["assessment"] == assessment
    assert results[-2]["workspace_diff_hash"] == results[-1]["output"]["patch_hash"]


def test_edit_stays_rejected_until_current_editable_source_is_observed(tmp_path):
    gateway = _gateway(tmp_path)
    original = (gateway.workspace / "src.py").read_bytes()
    assert json.loads(_context(gateway, []))["completion_guidance"]["stage"] == (
        "needs_source_evidence"
    )
    rejected = gateway.execute(_mutation("unobserved-edit"))
    assert rejected.status == "failed"
    assert gateway.accepted_mutations == 0
    assert (gateway.workspace / "src.py").read_bytes() == original
    assert json.loads(_context(gateway, [rejected]))["completion_guidance"]["stage"] == (
        "needs_source_evidence"
    )
    _read(gateway)
    after_read = json.loads(_context(gateway, []))["completion_guidance"]
    assert after_read["stage"] == "needs_mutation"
    assert after_read["next_action"] == {"tool": "replace_text"}
    before_restart = gateway.journal.path.read_bytes()
    restored = _restart(gateway)
    assert json.loads(_context(restored, []))["completion_guidance"] == after_read
    assert gateway.journal.path.read_bytes() == before_restart
    mutation = _mutation("observed-edit")
    assert restored.execute(mutation).status == "succeeded"
    completed = restored.journal.path.read_bytes()
    assert restored.execute(mutation).status == "succeeded"
    assert restored.journal.path.read_bytes() == completed
    assert restored.accepted_mutations == 1


@pytest.mark.parametrize("limits", [
    {"model": 3}, {"tools": 3}, {"mutations": 0}, {"untracked": True},
])
def test_actual_completion_barriers_do_not_promise_source_unlock(limits):
    gateway, counters = _state(("FAIL", "NOT_RUN"), anchor=False, **limits)
    policy = runner._tool_policy(gateway, counters, DevLimits())
    assert policy.allowed_tools == {"stop_task"}
    snapshot = SimpleNamespace(
        diff=gateway.current_diff, ready_to_submit=gateway.ready_to_submit(),
        visible_check_status=gateway.visible_check_status(),
    )
    guidance = runner._completion_guidance(snapshot, policy)
    assert guidance["stage"] == "blocked"
    assert guidance["next_action"] is None
    assert not guidance["submission_ready"]
    assert "temporarily unavailable" not in guidance["message"]
    assert "without submission or evaluation" in guidance["message"]


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_voluntary_stop_remains_terminal_without_evaluation(
    tmp_path, monkeypatch, context_policy,
):
    class StoppingMock(MockDevAdapter):
        def next_turn(self, context, tools):
            assert json.loads(context)["completion_guidance"]["stage"] == "needs_source_evidence"
            assert "stop_task" in {tool["name"] for tool in tools}
            return DevModelTurn(tool_calls=[RequestedTool(
                name="stop_task", action_id="explicit-stop",
                arguments={"reason_code": "public_task_conflict", "summary": "Fixture conflict."},
                turn_decision=PublicTurnDecision(mode="stop", basis="Record the public conflict."),
            )])

    monkeypatch.setattr(runner, "MockDevAdapter", StoppingMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy,
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "AGENT_STOPPED"
    assert run["call_counts"] == {"model": 1, "input_count": 0, "tool": 1}
    assert run["accepted_mutations"] == 0
    assert run["evaluator"] is None
    journal = DevJournal(tmp_path, run["run_id"])
    assert journal.terminal()["payload"]["milestones"]["submission"] is None
