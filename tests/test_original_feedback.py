"""Short local controls for original-case feedback; no live repair-quality claim."""
from __future__ import annotations

import json
import sys

import pytest
from test_dev_probes import FakeProbe
from test_finish_reproduction import (
    finish,
    original_with_control,
    prepare,
    request,
    results_for,
)
from test_probe_invocation import inject_api

from patchloop.contracts import RegisteredCheck
from patchloop.dev import probe_invocation, reproduction, runner
from patchloop.dev.contracts import DevModelTurn, DevToolResult, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.sandbox import LocalSandbox


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("original feedback controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


class LaunchProbe(FakeProbe):
    """Execute real observers with host arguments that change after the baseline."""

    def __init__(self):
        super().__init__(status="passed")
        self.sources = []

    def run_probe(self, workspace, question, python_source, *, deadline, execution_identity):
        receipt = super().run_probe(workspace, question, python_source, deadline=deadline,
                                    execution_identity=execution_identity)
        self.sources.append(python_source)
        argv = ["30"] + (["host-line-tracing-request"] if self.calls > 1 else [])
        result = LocalSandbox().run_check(workspace, RegisteredCheck(
            id="local-launch-control",
            command=[sys.executable, "-c", inject_api(python_source), *argv],
            timeout_seconds=10, environment={"PYTHONPATH": str(workspace)},
        ), deadline=deadline, execution_identity=execution_identity)
        return {**receipt, "status": "passed" if result.passed else "failed",
                "exit_code": result.exit_code, "stdout": result.stdout, "stderr": result.stderr}


@pytest.mark.parametrize("stable_identity,early_feedback", [
    (False, False), (True, False), (False, True), (True, True),
])
def test_identity_and_early_feedback_four_conditions(
    tmp_path, monkeypatch, smoke_package, stable_identity, early_feedback,
):
    backend, seen = LaunchProbe(), []
    if not stable_identity:
        select = reproduction.selection

        def legacy_selection(*args, **kwargs):
            purpose, channel = select(*args, **kwargs)
            return purpose, probe_invocation.CAPTURE_CHANNEL if channel else channel

        monkeypatch.setattr(reproduction, "selection", legacy_selection)
    if not early_feedback:
        monkeypatch.setattr(runner, "_run_original_recheck", lambda **kwargs: (None, None))

    class OriginalThenWrong(MockDevAdapter):
        def next_turn(self, context, tools):
            state = json.loads(context)
            if not state["reproduction_review"]["items"]:
                return DevModelTurn(tool_calls=[original_with_control(smoke_package.public)])
            if state["current_diff"].get("patch"):
                seen.append(state)
                return DevModelTurn(tool_calls=[RequestedTool(
                    name="stop_task", action_id="observed-next-input",
                    arguments={"reason_code": "no_safe_scoped_mutation",
                               "summary": "Local mechanism control ends after feedback."},
                    turn_decision={"mode": "stop", "basis": "Record the next model input."},
                )])
            turn = super().next_turn(context, tools)
            for call in turn.tool_calls:
                if call.name == "replace_text":
                    call.arguments["new_text"] = call.arguments["old_text"] + "\n# no repair\n"
            return turn

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", OriginalThenWrong)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert len(seen) == 1, result
    completion = seen[0]["reproduction_review"]["completion"]
    case = completion["cases"][0]
    assert case["baseline_acquisition"]["status"] == "qualified"
    assert backend.calls == 1 + int(early_feedback)
    if early_feedback:
        assert backend.sources[0] == backend.sources[1]
        assert case["current"]["comparison"] == "mismatched"
        assert json.loads(case["current"]["observed_json"]) == json.loads(
            case["purpose"]["reported_failure_json"])
        assert case["comparability"]["status"] == ("same" if stable_identity else "changed")
        assert completion["status"] == ("refuted" if stable_identity else "unverified")
        if not stable_identity:
            assert {d["path"] for d in case["comparability"]["differences"]} == {
                "/calls/0/argv/2", "/calls/1/argv/2",
            }
    else:
        assert case["current"] is None and completion["status"] == "pending"
    journal = DevJournal(tmp_path, result["run_id"])
    events = journal.events()
    assert not results_for(journal, "finish_task")
    if early_feedback:
        replay = next(e for e in events if e["event_type"] == "completion_reproduction_finished")
        following = [e for e in events if e["event_type"] == "model_call_finished"
                     and e["sequence"] > replay["sequence"]]
        assert len(following) == 1
        assert following[0]["payload"]["tool_calls"][0]["name"] == "stop_task"
    # Native tool outputs continue to match only model-requested calls.
    assert all(not action.startswith("completion-reproduction-")
               for e in events if e["event_type"] == "tool_batch_finished"
               for action in e["payload"]["action_ids"])


def test_early_replay_uses_reserved_completion_work_and_finish_reuses_it(gateway_factory, tmp_path):
    gateway, journal, _, backend, _ = prepare(gateway_factory)
    mutation = DevToolResult.model_validate(results_for(journal, "replace_text")[-1])
    # Only the final model slot remains; an optional run_probe is unaffordable.
    counters = runner._RunCounters(model_calls=gateway.limits.max_model_calls - 1)
    req = request(tmp_path).model_copy(update={"limits": gateway.limits})
    policy = runner._tool_policy(gateway, counters, gateway.limits)
    assert policy.completion_possible and "run_probe" not in policy.allowed_tools
    assert runner._run_original_recheck(
        journal=journal, gateway=gateway, latest_results=[mutation], counters=counters,
        active_elapsed_ms=lambda: 20, request=req,
    ) == (None, None)
    assert backend.calls == 2
    result, _ = finish(gateway, counters=counters)
    assert result.output["submission_verification"]["status"] == "cases_verified"
    assert backend.calls == 2


def test_unfunded_early_replay_stays_pending_without_execution(gateway_factory, tmp_path):
    gateway, journal, _, backend, _ = prepare(gateway_factory)
    mutation = DevToolResult.model_validate(results_for(journal, "replace_text")[-1])
    counters = runner._RunCounters(model_calls=gateway.limits.max_model_calls)
    runner._run_original_recheck(
        journal=journal, gateway=gateway, latest_results=[mutation], counters=counters,
        active_elapsed_ms=lambda: 20, request=request(tmp_path).model_copy(
            update={"limits": gateway.limits}),
    )
    assert backend.calls == 1
    verification = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert verification["status"] == "pending"
    assert not any(e["event_type"].startswith("completion_reproduction_") for e in journal.events())
