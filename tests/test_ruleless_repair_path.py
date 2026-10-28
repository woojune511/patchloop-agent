"""Ruleless failure diagnosis stays bounded and grants no verification credit."""

import copy

import pytest
from test_dev_probe_action_replay import restore
from test_dev_probes import context
from test_dev_tools import mutation_call, read_calls
from test_judgment_integration import diagnostic_probe
from test_probe_purpose import probe
from test_repair_path_diagnosis import PATH, TracedProbe, state
from test_repair_path_reuse import SOURCE, TEST, receipts, result_for, start_for

from patchloop.dev import completion_reproduction, repair_path
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.model_state import compact_model_state
from patchloop.errors import ContractError


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("ruleless diagnosis controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def ruleless_receipts(*, diagnosed=False, test_edit=False):
    events, completion = receipts(test_edit=test_edit)
    for event in events:
        if event["event_type"] == "action_finished":
            observation = event["payload"]["result"].get("output", {}).get("reproduction")
            if observation:
                observation["binding"]["definition"]["diagnostic_rules"] = None
                observation["judgment"] = None
    if not diagnosed:
        events = [event for event in events if event["payload"].get(
            "action_id", event["payload"].get("result", {}).get("action_id")) != "diagnosis"]
    return events, completion


def request(call_id="call-1"):
    return {"replay_action_id": "baseline", "call_path": {
        "call_id": call_id, "watches": [
            {"origin": "workspace", "path": "sample.py", "lines": [12]}]}}


def test_paired_failure_opens_choice_without_promoting_authored_judgment():
    events, completion = ruleless_receipts()
    before = copy.deepcopy(events)
    current = repair_path.review(events, SOURCE, completion)
    assert current["status"] == "needs_path_diagnosis" and current["call_id"] is None
    assert current["call_selection_required"]
    assert current["call_mapping"] == "model_selected_unverified"
    assert [row["call_id"] for row in current["call_choices"]] == ["call-1", "call-2"]
    assert set(current["call_choices"][0]) == {
        "call_id", "argv", "arguments", "outcome", "exit_code"}
    selected = repair_path.validate(current, "run_probe", request("call-2"))
    assert selected == {**repair_path.link(current), "call_id": "call-2"}
    with pytest.raises(ContractError):
        repair_path.validate(current, "run_probe", request("call-3"))
    assert completion["cases"][0]["evidence"]["status"] == "REFUTED"
    assert events == before


@pytest.mark.parametrize("change", [
    "capture", "incomplete", "conditions", "binding", "declared", "cleanup", "executed",
    "canonical_unknown",
])
def test_diagnosis_does_not_weaken_failure_or_coverage_requirements(change):
    events, completion = ruleless_receipts()
    result = result_for(events, "failure-source")
    observation = result["output"]["reproduction"]
    if change == "capture":
        observation["call_observation"]["calls"][0]["capture"]["stdout"] = "changed error"
    elif change == "incomplete":
        observation["call_observation"]["calls"][0]["capture"]["status"] = "incomplete"
    elif change == "conditions":
        observation["call_observation"]["calls"][0]["arguments"]["args"] = ["another"]
    elif change == "binding":
        observation["binding"]["program_hash"] = "another-program"
    elif change == "declared":
        observation["declared_failure_comparison"] = "mismatched"
    elif change == "cleanup":
        result["output"]["execution_policy"]["cleanup_status"] = "unknown"
    elif change == "executed":
        result["output"]["public_execution"]["files"][0]["not_observed_changed_ranges"] = []
    else:
        observation["binding"]["definition"]["diagnostic_rules"] = [
            {"field": "bug", "call_id": "call-1", "contains": "F0010"}]
    assert repair_path.review(events, SOURCE, completion)["status"] == "not_needed"


def test_selection_and_changed_call_attempt_cannot_refill_allowances():
    events, completion = ruleless_receipts()
    initial = repair_path.review(events, SOURCE, completion)
    for action_id, tool, call_id in (
        ("read", "read_file", None), ("bad-first", "run_probe", None),
    ):
        events.append({"event_type": "action_started", "payload": {
            "action_id": action_id, "tool": tool,
            "repair_path_link": {**repair_path.link(initial), "call_id": call_id},
            "probe_request": {"status": "rejected"}}})
    current = repair_path.review(events, SOURCE, completion)
    assert current["rejected_requests"] == 1 and not current["preparation_available"]
    selected = repair_path.validate(current, "run_probe", request("call-2"))
    events.append({"event_type": "action_started", "payload": {
        "action_id": "admitted", "tool": "run_probe", "repair_path_link": selected,
        "diagnosis_request": {"call_path": request("call-2")["call_path"]}}})
    fixed = repair_path.review(events, SOURCE, completion)
    assert fixed["call_id"] == "call-2" and not fixed["call_selection_required"]
    assert fixed["rejected_requests"] == 1 and not fixed["preparation_available"]
    with pytest.raises(ContractError):
        repair_path.validate(fixed, "run_probe", request("call-1"))
    events.append({"event_type": "action_started", "payload": {
        "action_id": "bad-second", "tool": "run_probe",
        "repair_path_link": {**selected, "call_id": "call-1"},
        "probe_request": {"status": "rejected"},
        "diagnosis_request": {"call_path": request("call-1")["call_path"]}}})
    exhausted = repair_path.review(events, SOURCE, completion)
    assert exhausted["status"] == "verification_incomplete"
    assert exhausted["call_id"] == "call-2" and exhausted["rejected_requests"] == 2
    assert not exhausted["execution_attempted"]


@pytest.mark.parametrize("test_edit", [False, True])
def test_completed_ruleless_diagnosis_survives_recovery_and_test_only_edits(test_edit):
    events, completion = ruleless_receipts(diagnosed=True, test_edit=test_edit)
    current = repair_path.review(events, TEST if test_edit else SOURCE, completion)
    assert current["status"] == "diagnosed" and current["call_id"] == "call-1"
    assert not current["call_selection_required"] and current["execution_attempted"]
    assert current["diagnosis_evidence"]["relation"] == (
        "historical_test_only" if test_edit else "current_candidate")
    assert current["original_effect_status"] == "original_effect_refuted"
    assert result_for(events, "diagnosis")["output"]["reproduction"]["judgment"] is None
    assert repair_path.review(copy.deepcopy(events), TEST if test_edit else SOURCE,
                              completion) == current


def test_pending_execution_cannot_switch_calls_to_retry():
    events, completion = ruleless_receipts(diagnosed=True)
    events = [event for event in events if not (
        event["event_type"] == "action_finished"
        and event["payload"]["result"]["action_id"] == "diagnosis")]
    current = repair_path.review(events, SOURCE, completion)
    assert current["status"] == "verification_incomplete" and current["execution_attempted"]
    assert current["call_id"] == "call-1"
    with pytest.raises(ContractError):
        repair_path.validate(current, "run_probe", request("call-2"))


def test_ruleless_gateway_diagnosis_recovery_keeps_original_refuted(gateway_factory, smoke_package):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = TracedProbe(status="passed")
    assert gateway.execute(read_calls()[1]).status == "succeeded"
    original = diagnostic_probe(gateway.public_task, "original", corrected=True, legacy=True)
    original.arguments["purpose"]["diagnostic_rules"] = None
    assert gateway.execute(original).status == "succeeded"
    edit = mutation_call(gateway, action_id="wrong-repair")
    edit.arguments["new_text"] = edit.arguments["old_text"].replace(
        "    rows: list[list[str]] = []", "    if text == '__unreached__':\n"
        "        return []\n    rows: list[list[str]] = []")
    assert gateway.execute(edit).status == "succeeded"
    failed = gateway.execute(probe(gateway.public_task, "failed-current", replay="original"))
    assert failed.output["reproduction"].get("judgment") is None
    assert state(gateway)["status"] == "needs_path_diagnosis"
    call = RequestedTool(name="run_probe", action_id="diagnosis",
        preserve_annotation_presence=True, arguments={"call_id": "call-1", "focus": {
            "origin": "workspace", "path": PATH, "function": "parse_rows"}})
    append = journal.append

    def crash(kind, payload):
        if kind == "action_finished" and payload["action_id"] == call.action_id:
            raise KeyboardInterrupt("completed execution before parent receipt")
        return append(kind, payload)

    journal.append = crash
    with pytest.raises(KeyboardInterrupt):
        gateway.execute(call)
    journal.append = append
    assert backend.calls == 3
    recovered = restore(gateway, journal, workspace, gateway.public_task, backend)
    assert recovered.execute(call).status == "succeeded"
    assert recovered.execute(call).replayed and backend.calls == 3
    completed = recovered.completion_verification(diff_hash=recovered.current_diff_hash)
    assert completed["status"] == "refuted"
    assert completed["repair_path"]["status"] == "diagnosed"
    assert completed["repair_path"]["call_id"] == "call-1"
    assert start_for(journal.events(), "diagnosis")["repair_path_link"]["call_id"] == "call-1"
    fixed = mutation_call(recovered, action_id="repair-from-diagnosis", alternative=True)
    fixed.arguments["old_text"] = edit.arguments["new_text"]
    fixed.arguments.pop("causal_revision")
    fixed.arguments["repair_prediction"] = {
        "kind": "source", "target": -1, "event": "original_failure_absent"}
    repaired = recovered.execute(fixed)
    assert repaired.status == "succeeded", repaired
    linked = repaired.output["mutation"]["repair_path_link"]
    assert linked["diagnosis_action_id"] == "diagnosis" and linked["call_id"] == "call-1"
    assert state(recovered)["status"] == "not_needed"
    recheck = completion_reproduction.replay_call(
        journal.run_id, completed["repair_path"]["case_id"], "original",
        recovered.current_diff_hash)
    checked = recovered.execute(recheck)
    assert checked.output["reproduction"]["comparison"] == "matched"
    assert checked.output["reproduction"].get("judgment") is None and backend.calls == 4
    assessment = checked.output["repair_prediction"]
    assert assessment["status"] == "matched" and assessment["original_effect"] == "supported"
    assert assessment["semantic_correctness"] == "unverified"
    assert not assessment["counts_toward_required_checks"]
    assert assessment["mutation_action_id"] == fixed.action_id
    assert assessment["diagnosis_action_id"] == call.action_id
    assert recovered.state_snapshot().completion_verification["status"] == "cases_verified"
    model_view = compact_model_state(context(recovered, smoke_package, [checked]), [])
    assert model_view["latest_tool_results"][0]["output"]["repair_prediction"] == assessment
