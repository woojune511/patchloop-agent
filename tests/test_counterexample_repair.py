"""Public feedback changes context only and final check failures remain failures."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_counterexample_packet import receipt, rows, saved  # noqa: F401

from diagnostics import counterexample_repair as diagnostic
from patchloop.artifacts import ArtifactStore
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def test_read_delivery_audit_requires_success_without_correction_and_exact_output():
    result = {"action_id": "public_counterexample_delivery_read", "tool": "read_file",
              "status": "succeeded", "input_hash": "bound", "workspace_diff_hash": "current",
              "output": {"spans": [{"path": "public.py", "file_hash": "source-hash",
                                     "start_line": 1, "end_line": 1, "content": "public source"}]}}
    event = {"event_type": "action_finished", "payload": {
        "action_id": result["action_id"], "result": result}}
    request = {"input": [{"role": "user", "content": canonical_json(
        {"state": {"latest_tool_results": [result]}})}]}
    assert diagnostic.read_delivery_audit([event], request)["protocol_corrections"] == 0
    with pytest.raises(ContractError, match="protocol correction"):
        diagnostic.read_delivery_audit([{"event_type": "protocol_correction"}, event], request)
    with pytest.raises(ContractError, match="did not succeed"):
        diagnostic.read_delivery_audit([], request)
    changed = copy.deepcopy(event)
    changed["payload"]["result"]["input_hash"] = "different"
    with pytest.raises(ContractError, match="missing from following request"):
        diagnostic.read_delivery_audit([changed], request)
    changed["payload"]["result"]["input_hash"] = "bound"
    changed["payload"]["result"]["output"]["spans"][0]["content"] = "different body"
    with pytest.raises(ContractError, match="missing from following request"):
        diagnostic.read_delivery_audit([changed], request)


def test_context_and_actual_input_receive_same_packet_without_changing_gate(monkeypatch):
    state = {"current_diff": {"patch_hash": "measured"}, "workflow_gate": "ready_to_submit",
             "visible_check_status": [{"status": "PASS"}],
             "reproduction_review": {"completion": {"status": "cases_verified"}}}
    before = copy.deepcopy(state)
    monkeypatch.setattr(diagnostic.packet_api, "model_visible", lambda packet, current: {
        "measured_diff": packet["diff"], "current_diff": current,
        "measurement_is_current": current == packet["diff"]})
    context = lambda **kwargs: canonical_json(state)  # noqa: E731
    model_input = lambda **kwargs: [{"role": "user", "content": canonical_json(  # noqa: E731
        {"state": state})}]
    monkeypatch.setattr(diagnostic.runner, "_build_context", context)
    monkeypatch.setattr(diagnostic.runner, "_build_model_input", model_input)
    with diagnostic.public_feedback({"diff": "measured"}):
        canonical = json.loads(diagnostic.runner._build_context())
        actual = json.loads(diagnostic.runner._build_model_input()[-1]["content"])["state"]
        assert canonical == actual
        assert actual.pop(diagnostic.FIELD)["measurement_is_current"] is True
        assert actual == before
        state["current_diff"]["patch_hash"] = "edited"
        later = json.loads(diagnostic.runner._build_model_input()[-1]["content"])["state"]
        assert later[diagnostic.FIELD]["measurement_is_current"] is False
        assert later["workflow_gate"] == "ready_to_submit"
    assert diagnostic.runner._build_context is context
    assert diagnostic.runner._build_model_input is model_input
    assert diagnostic.FIELD not in state


@pytest.mark.parametrize("result", [
    {"billing_known": True, "result": {}},
    {"billing_known": False, "result": {"artifact_hashes": {"submitted_patch": "x"}}},
    {"billing_known": True, "stop_remaining": True,
     "result": {"artifact_hashes": {"submitted_patch": "x"}}},
])
def test_no_final_execution_after_uncertainty_or_missing_submission(result):
    outcome = diagnostic.final_public_check(None, None, None, None, None, result)
    assert outcome["status"] == "NOT_RUN"


def test_final_check_rejects_drift_and_exhausted_host_slot(tmp_path, monkeypatch):
    branch = SimpleNamespace(workspace=tmp_path, journal=DevJournal(tmp_path, "run_dev_test"))
    result = {"billing_known": True,
              "result": {"artifact_hashes": {"submitted_patch": "submitted"}}}
    monkeypatch.setattr(diagnostic.runner, "_restore_counters",
                        lambda journal: SimpleNamespace(tool_actions=26))
    monkeypatch.setattr(diagnostic.DevJournal, "latest_active_elapsed_ms", lambda journal: 621651)
    plan = {"combined_limits": {"max_tool_actions": 40, "wall_time_seconds": 2400}}
    monkeypatch.setattr(diagnostic.WorkspaceManager, "diff_summary",
                        lambda workspace, **kwargs: SimpleNamespace(patch_hash="different"))
    with pytest.raises(ContractError, match="differs from submitted"):
        diagnostic.final_public_check(branch, {}, plan, None, None, result)
    monkeypatch.setattr(diagnostic.WorkspaceManager, "diff_summary",
                        lambda workspace, **kwargs: SimpleNamespace(patch_hash="submitted"))
    monkeypatch.setattr(diagnostic.runner, "_restore_counters",
                        lambda journal: SimpleNamespace(tool_actions=40))
    with pytest.raises(ContractError, match="host tool slot"):
        diagnostic.final_public_check(branch, {}, {"combined_limits": {"max_tool_actions": 40}},
                                      None, None, result)


@pytest.mark.parametrize("repaired", [False, True])
def test_final_assessment_is_independent_and_cannot_dispatch_twice(
    saved, tmp_path, monkeypatch, repaired,  # noqa: F811
):
    packet = diagnostic.packet_api.build_packet(saved["root"])
    branch = SimpleNamespace(workspace=tmp_path,
        journal=DevJournal(tmp_path/"branch", "run_dev_branch"),
        envelope=SimpleNamespace(prepared_probe_dependencies_path="unused",
            probe_dependencies={"manifest_hash": "sha256:"+"1"*64,
                "content_hash": "sha256:"+"2"*64, "python": "3.9",
                "platform": "linux/amd64", "runtime_profile": "python39-v1",
                "source_roots": ["astroid"]}), package=SimpleNamespace(public=None))
    result = {"billing_known": True,
              "result": {"artifact_hashes": {"submitted_patch": "submitted"}}}
    plan = {"packet_hash": "packet", "combined_limits": {
        "max_tool_actions": 40, "wall_time_seconds": 2400},
        "executing_probe_identity": {"image_digest": "image", "profile_hash": "profile"}}
    monkeypatch.setattr(diagnostic.runner, "_restore_counters",
                        lambda journal: SimpleNamespace(tool_actions=39))
    monkeypatch.setattr(diagnostic.DevJournal, "latest_active_elapsed_ms", lambda journal: 621651)
    deadlines, dispatches = [], []

    def diff(workspace, *, deadline):
        deadlines.append(deadline.expires_at)
        deadline.check()
        return SimpleNamespace(patch_hash="submitted")

    class Probe:
        def __init__(self, **kwargs):
            pass

        def preflight(self, *, deadline):
            deadlines.append(deadline.expires_at)
            return plan["executing_probe_identity"]

        def run_probe(self, workspace, question, source, *, deadline, execution_identity):
            assert source == packet["program_text"]
            deadlines.append(deadline.expires_at)
            dispatches.append(execution_identity)
            return receipt(rows(not repaired), saved["program_hash"])

    monkeypatch.setattr(diagnostic.WorkspaceManager, "diff_summary", diff)
    monkeypatch.setattr(diagnostic, "load_dependencies", lambda *args: None)
    monkeypatch.setattr(diagnostic, "DockerProbeSandbox", Probe)
    journal = DevJournal(tmp_path/"collector", "run_dev_collector")
    store = ArtifactStore(tmp_path/"objects")
    outcome = diagnostic.final_public_check(branch, packet, plan, journal, store, result)
    assert outcome["status"] == ("PASS" if repaired else "FAIL")
    assert outcome["preexisting"]["status"] == "FAIL"
    assert outcome["preexisting"]["mandatory"] is False
    assert outcome["combined_tool_actions"] == 40 and outcome["feedback_to_model"] is False
    assert len(set(deadlines)) == 1 and len(dispatches) == 1
    with pytest.raises(ContractError, match="already attempted"):
        diagnostic.final_public_check(branch, packet, plan, journal, store, result)
    assert len(dispatches) == 1
