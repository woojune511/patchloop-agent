"""Ruleless original observation selects captured calls without claiming a repair."""

import copy

import pytest
import test_first_observation as controls
from test_dev_probe_action_replay import restore
from test_dev_tools import read_calls
from test_first_repair_integration import observe
from test_judgment_integration import diagnostic_probe
from test_repair_path_diagnosis import TracedProbe

from patchloop.dev import first_observation as observation
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError


def baseline():
    events, completion = controls.baseline()
    reproduction = events[1]["payload"]["result"]["output"]["reproduction"]
    reproduction["binding"]["definition"]["diagnostic_rules"] = None
    reproduction["judgment"] = None
    return events, completion


def selection(call_id="call-1"):
    return {**controls.selection(), "call_id": call_id}


def test_ruleless_original_offers_only_captured_explicit_choices(tmp_path):
    events, completion = baseline()
    before = copy.deepcopy(events)
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    assert state["available"] and state["call_id"] is None
    assert state["call_selection_required"]
    assert state["call_mapping"] == "model_selected_unverified"
    assert [row["call_id"] for row in state["call_choices"]] == ["call-1", "call-2"]
    tools = dev_tool_schemas(finish_enabled=False, allowed_tools=["observe_original"],
                            first_original_observation=state)
    schema = next(tool for tool in tools if tool["name"] == "observe_original")
    assert schema["parameters"]["properties"]["call_id"] == {
        "type": "string", "enum": ["call-1", "call-2"]}
    assert "call_id" in schema["parameters"]["required"]
    assert "call_id" not in observation.schema()["parameters"]["properties"]
    (tmp_path / "sample.py").write_text(controls.SOURCE, encoding="utf-8")
    for raw in (controls.selection(), selection("call-3")):
        with pytest.raises(ContractError, match="/call_id"):
            observation.prepare(raw, state, tmp_path, controls.preflight)
    admitted = observation.prepare(selection("call-2"), state, tmp_path, controls.preflight)
    assert admitted["call_id"] == admitted["call_path"]["call_id"] == "call-2"
    assert admitted["replay_action_id"] == "baseline"
    assert observation.arguments(selection("call-2"), admitted)["python_source"] is None
    assert events == before


@pytest.mark.parametrize("change", ["capture", "incomplete", "cleanup", "declared",
                                  "same_expected", "authored_mismatch", "duplicate_call"])
def test_ruleless_selection_needs_healthy_acquired_failure(change):
    events, completion = baseline()
    result = events[1]["payload"]["result"]
    reproduction = result["output"]["reproduction"]
    if change == "capture":
        reproduction["call_observation"]["calls"][0]["capture"]["status"] = "incomplete"
    elif change == "incomplete":
        reproduction["call_observation"]["incomplete"] = True
    elif change == "cleanup":
        result["output"]["execution_policy"]["cleanup_status"] = "unknown"
    elif change == "declared":
        reproduction["declared_failure_comparison"] = "mismatched"
    elif change == "same_expected":
        reproduction["binding"]["definition"]["expected_json"] = reproduction["observed_json"]
    elif change == "authored_mismatch":
        reproduction["observed_json"] = '{"bug":1,"control":false}'
    else:
        reproduction["call_observation"]["calls"][1]["call_id"] = "call-1"
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    assert not state["available"] and not state["blocked"]


@pytest.mark.parametrize("change", [None, "capture", "arguments", "binding", "call_id"])
def test_ruleless_trace_requires_same_failure_and_call_identity(tmp_path, monkeypatch, change):
    original_baseline = controls.baseline

    def ruleless():
        events, completion = original_baseline()
        reproduction = events[1]["payload"]["result"]["output"]["reproduction"]
        reproduction["binding"]["definition"]["diagnostic_rules"] = None
        reproduction["judgment"] = None
        return events, completion

    monkeypatch.setattr(controls, "baseline", ruleless)
    events, completion = controls.execute_receipt(tmp_path, selection("call-2"))
    start = events[2]["payload"]
    start["first_observation_link"] = observation.link(start["first_observation"])
    replay = events[-1]["payload"]["result"]["output"]["reproduction"]
    if change == "capture":
        replay["call_observation"]["calls"][0]["capture"]["stdout"] = "another failure"
    elif change == "arguments":
        replay["call_observation"]["calls"][1]["arguments"]["args"] = ["another"]
    elif change == "binding":
        replay["binding"]["program_hash"] = "another-program"
    elif change == "call_id":
        replay["call_observation"]["calls"][0]["call_id"] = "call-3"
    state = observation.review(events, observation.EMPTY_DIFF, completion)
    assert state["status"] == ("observed" if change is None else "incomplete")
    assert state["call_id"] == "call-2" and not state["available"]
    assert state["repair_correctness"] == "unverified"
    assert completion["cases"][0]["evidence"]["status"] == "REFUTED"
    assert replay["judgment"] is None
    assert observation.review(copy.deepcopy(events), observation.EMPTY_DIFF, completion) == state


def test_ruleless_rejections_across_call_choices_share_one_allowance(tmp_path):
    events, completion = baseline()
    initial = observation.review(events, observation.EMPTY_DIFF, completion)
    for index, call_id in enumerate((None, "call-2")):
        events.append({"event_type": "action_started", "payload": {
            "action_id": f"rejected-{index}", "tool": observation.TOOL_NAME,
            "first_observation_link": {**observation.link(initial), "call_id": call_id},
            "probe_request": {"status": "rejected"}}})
        state = observation.review(events, observation.EMPTY_DIFF, completion)
        assert state["rejected_requests"] == index + 1
        assert state["available"] is (index == 0)
        assert state["call_id"] is None and state["call_selection_required"]
        assert not state["execution_attempted"]
    with pytest.raises(ContractError, match="not available"):
        observation.prepare(selection(), state, tmp_path, controls.preflight)


def test_ruleless_gateway_selection_recovery_keeps_failure_obligation(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = TracedProbe(status="passed")
    assert gateway.execute(read_calls()[1]).status == "succeeded"
    original = diagnostic_probe(gateway.public_task, "original", corrected=True, legacy=True)
    original.arguments["purpose"]["diagnostic_rules"] = None
    assert gateway.execute(original).status == "succeeded"
    rejected = gateway.execute(observe("missing-call"))
    assert rejected.status == "failed" and backend.calls == 1
    assert rejected.output["invalid_fields"][0]["path"] == "/call_id"
    call = observe()
    call.arguments["call_id"] = "call-2"
    append = journal.append

    def crash(kind, payload):
        if kind == "action_finished" and payload["action_id"] == call.action_id:
            raise KeyboardInterrupt("completed observation before parent receipt")
        return append(kind, payload)

    journal.append = crash
    with pytest.raises(KeyboardInterrupt):
        gateway.execute(call)
    journal.append = append
    assert backend.calls == 2
    gateway = restore(gateway, journal, workspace, gateway.public_task, backend)
    result = gateway.execute(call)
    assert result.status == "succeeded", result
    completed = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert completed["first_observation"]["status"] == "observed", completed
    assert completed["first_observation"]["call_id"] == "call-2"
    assert completed["first_observation"]["rejected_requests"] == 1
    assert completed["status"] == "refuted"
    assert backend.calls == 2
    assert result.output["reproduction"].get("judgment") is None
    recovered = restore(gateway, journal, workspace, gateway.public_task, backend)
    assert recovered.execute(call).replayed and backend.calls == 2
    repeat = observe("different-call")
    repeat.arguments["call_id"] = "call-1"
    assert recovered.execute(repeat).status == "failed" and backend.calls == 2
