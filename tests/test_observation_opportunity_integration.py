"""Offline normal-request control for ruleless observation and subsequent repair."""

import json

import pytest
from test_dev_segments import assert_submitted, configured, records
from test_dev_tools import read_calls
from test_first_repair_integration import edit, observe
from test_judgment_integration import diagnostic_probe
from test_repair_path_diagnosis import TracedProbe

from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn
from patchloop.dev.model import MockDevAdapter


def test_normal_request_offers_ruleless_call_choice_before_edit(
    tmp_path, monkeypatch, smoke_package,
):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("offline only"))
    backend = TracedProbe(status="passed")
    original = diagnostic_probe(smoke_package.public, "original", corrected=True, legacy=True)
    original.arguments["purpose"]["diagnostic_rules"] = None
    observation = observe()
    observation.arguments["call_id"] = "call-1"
    steps = iter([read_calls()[1], original, observation, edit()])
    exposed = []

    class Script(MockDevAdapter):
        def next_turn(self, context, tools):
            call = next(steps, None)
            if call is observation:
                schema = next(tool for tool in tools if tool["name"] == "observe_original")
                assert schema["parameters"]["properties"]["call_id"]["enum"] == [
                    "call-1", "call-2"]
                state = json.loads(context)["repair_stage"]["first_observation"]
                assert state["call_selection_required"] and state["call_id"] is None
                exposed.append(state)
            return DevModelTurn(tool_calls=[call]) if call else super().next_turn(context, tools)

    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=Script("csv-quoted-newline"))
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    result = runner.run_dev(request.model_copy(update={"enable_probes": True}))["runs"][0]
    # The fake provider fixture intentionally lacks a real evaluator image identity.
    assert_submitted(result)
    assert len(exposed) == 1 and backend.calls == 3
    assert len(inputs) == len(counted)
    observed = views[3]["repair_stage"]["first_observation"]
    assert observed["status"] == "observed" and observed["call_id"] == "call-1"
    journal, _ = records(request)
    start = next(event["payload"] for event in journal.events()
                 if event["event_type"] == "action_started"
                 and event["payload"]["action_id"] == observation.action_id)
    assert start["first_observation_link"]["call_id"] == "call-1"
    assert start["first_observation"]["replay_action_id"] == original.action_id
