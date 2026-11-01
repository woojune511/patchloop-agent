"""Pending helper/task comparison keeps its instructions at actual finish inputs."""
from __future__ import annotations

import json

import httpx
import pytest
from test_dev_planning import request as smoke_request
from test_dev_probes import FakeProbe, probe_call

from patchloop.artifacts import ArtifactStore
from patchloop.dev import completion_context, runner, scope_review, working_plan
from patchloop.dev.contracts import DevModelTurn
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.util import sha256_bytes, sha256_json


def actual_probe_evidence(items, record):
    """Resolve both inline and explicitly referenced native delivery in this input."""
    action_id = record["action_id"]
    program = record["program"]
    if "python_source" in program:
        source = program["python_source"]
    else:
        assert program["delivery"] == "preceding_function_call_arguments"
        call = next(item for item in items if item.get("type") == "function_call"
                    and item["call_id"] == action_id)
        assert call["name"] == "run_probe"
        source = json.loads(call["arguments"])["python_source"]
    assert sha256_bytes(source.encode()) == program["source_hash"]
    if "stdout" in record and "stderr" in record:
        output = record
    else:
        assert record["delivery"] == "preceding_function_call_output"
        returned = next(item for item in items if item.get("type") == "function_call_output"
                        and item["call_id"] == action_id)
        result = json.loads(returned["output"])
        assert result["tool"] == "run_probe" and result["action_id"] == action_id
        output = result["output"]
        assert output["source_hash"] == program["source_hash"]
        assert output["diff_hash"] == record["diff_hash"]
    return source, output["stdout"], output["stderr"]


@pytest.mark.parametrize("state", [{}, {"working_plan": None}])
def test_completion_with_planning_off_keeps_existing_prompt(state):
    assert completion_context.system_prompt(state) == completion_context.SYSTEM_PROMPT


def test_completion_guidance_is_stable_before_during_and_after_review():
    states = [{"working_plan": {"policy": "brief-v1", "review_request": review}}
              for review in ({}, {"requirement_comparison": {"status": "review_needed"}},
                             {"requirement_comparison": {"status": "review_recorded"}})]
    assert len({completion_context.system_prompt(state) for state in states}) == 1


def test_completion_reuses_only_bound_comparison_guidance_and_hash(monkeypatch):
    state = {"working_plan": {"review_request": {
        "requirement_comparison": {"status": "review_needed"},
    }}}
    assert scope_review.COMPARISON_INSTRUCTIONS in working_plan.INSTRUCTIONS
    prompt = completion_context.system_prompt(state)
    assert prompt == (completion_context.SYSTEM_PROMPT + "\n\n"
                      + scope_review.COMPARISON_INSTRUCTIONS)
    assert "In the first tool response" not in prompt
    before = completion_context.contract()
    assert before["requirement_comparison_guidance"]["instructions_hash"] == sha256_json(
        scope_review.COMPARISON_INSTRUCTIONS)
    monkeypatch.setattr(scope_review, "COMPARISON_INSTRUCTIONS", "Changed public comparison guide.")
    assert completion_context.contract() != before
    assert completion_context.system_prompt(state).endswith("Changed public comparison guide.")


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("correction", [False, True])
def test_actual_completion_and_correction_keep_comparison_guidance_and_evidence(
    tmp_path, monkeypatch, context_policy, correction,
):
    def forbidden(*args, **kwargs):
        pytest.fail("completion comparison validation must not call a real provider")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    backend = FakeProbe(status="passed")
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)

    class ComparisonScript(MockDevAdapter):
        number = 0
        corrected = False

        def _next_action(self, context, tools):
            state = json.loads(context)
            number = self.number
            self.number += 1
            if number == 1:
                return DevModelTurn(tool_calls=[probe_call("base-helper")])
            if number == 3:
                call = probe_call("candidate-helper")
                call.arguments = {"replay_action_id": "base-helper", "question": None,
                                  "python_source": None}
                return DevModelTurn(tool_calls=[call])
            if state["workflow_gate"] == "ready_to_submit" and correction and not self.corrected:
                self.corrected = True
                return DevModelTurn(tool_calls=[])
            return super()._next_action(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", ComparisonScript)
    req = smoke_request(tmp_path).model_copy(update={
        "context_policy": context_policy, "enable_probes": True,
        "verification_policy": "public-checks-v1",
    })
    result = runner.run_dev(req)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["cost_nanos"] == 0 and backend.calls == 2
    assert result["call_counts"] == {"model": 6 + correction, "tool": 7, "input_count": 0}
    journal = DevJournal(tmp_path, result["run_id"])
    store = ArtifactStore(tmp_path / "artifacts")
    events = journal.events()
    completed = [e for e in events if e["event_type"] == "turn_started"
                 and e["payload"]["workflow_gate"] == "ready_to_submit"]
    assert len(completed) == 1 + correction
    for event in completed:
        items = runner._load_active_model_input(
            event["payload"], store, context_policy=context_policy,
        )
        state = reconstruct_state(items, context_policy=context_policy)
        assert scope_review.COMPARISON_INSTRUCTIONS in items[0]["content"]
        if context_policy == "segmented-v1":
            assert working_plan.INSTRUCTIONS not in items[0]["content"]
        comparison = state["working_plan"]["review_request"]["requirement_comparison"]
        assert comparison["status"] == "review_needed"
        assert comparison["requirement_fit"] == "not_certified"
        assert comparison["task_reference"]["issue_hash"] == sha256_json(
            state["public_task"]["issue"])
        assert comparison["observation_action_ids"] == ["base-helper", "candidate-helper"]
        probes = {p["action_id"]: p for p in state["recent_probes"]}
        assert probes["base-helper"]["historical"]
        assert not probes["candidate-helper"]["historical"]
        base_evidence = actual_probe_evidence(items, probes["base-helper"])
        assert base_evidence == actual_probe_evidence(items, probes["candidate-helper"])
        assert base_evidence == ("assert False", "PUBLIC_PROBE_OUTPUT", "")
        assert "finish_task" in state["available_tool_names"]
    if correction and context_policy == "segmented-v1":
        assert "completion_no_action" in result["context_management"]["transition_reasons"]
    before = journal.path.read_bytes()
    resumed = runner.run_dev(req.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert resumed == result
    assert journal.path.read_bytes() == before and backend.calls == 2


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_completion_entered_before_first_helper_already_has_comparison_guidance(
    tmp_path, monkeypatch, context_policy,
):
    def forbidden(*args, **kwargs):
        pytest.fail("late helper validation must not call a real provider")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    backend = FakeProbe(status="passed")
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)

    class LateHelper(MockDevAdapter):
        probed = False

        def _next_action(self, context, tools):
            if json.loads(context)["workflow_gate"] == "ready_to_submit" and not self.probed:
                self.probed = True
                return DevModelTurn(tool_calls=[probe_call("completion-helper")])
            return super()._next_action(context, tools)

    monkeypatch.setattr(runner, "MockDevAdapter", LateHelper)
    req = smoke_request(tmp_path).model_copy(update={
        "context_policy": context_policy, "enable_probes": True,
        "verification_policy": "public-checks-v1",
    })
    result = runner.run_dev(req)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS" and backend.calls == 1
    store = ArtifactStore(tmp_path / "artifacts")
    events = DevJournal(tmp_path, result["run_id"]).events()
    completed = [e for e in events if e["event_type"] == "turn_started"
                 and e["payload"]["workflow_gate"] == "ready_to_submit"]
    assert len(completed) == 2
    inputs = [runner._load_active_model_input(e["payload"], store, context_policy=context_policy)
              for e in completed]
    states = [reconstruct_state(items, context_policy=context_policy) for items in inputs]
    assert "requirement_comparison" not in states[0]["working_plan"]["review_request"]
    assert states[1]["working_plan"]["review_request"]["requirement_comparison"][
        "status"] == "review_needed"
    assert inputs[0][0]["content"] == inputs[1][0]["content"]
    assert scope_review.COMPARISON_INSTRUCTIONS in inputs[1][0]["content"]
