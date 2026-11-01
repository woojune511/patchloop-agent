"""Required public feedback uses normal gates and never adds a final target run."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_counterexample_packet import saved  # noqa: F401

from diagnostics import counterexample_repair as diagnostic
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


def test_context_and_actual_input_receive_same_packet_without_changing_gate(
    saved, monkeypatch,  # noqa: F811
):
    state = {"current_diff": {"patch_hash": "measured"}, "workflow_gate": "ready_to_submit",
             "visible_check_status": [{"status": "PASS"}],
             "reproduction_review": {"completion": {"status": "cases_verified"}}}
    before = copy.deepcopy(state)
    packet = diagnostic.packet_api.build_packet(saved["root"])
    packet["diff"] = "measured"
    monkeypatch.setattr(diagnostic.packet_api, "model_visible", lambda packet, current: {
        "measured_diff": packet["diff"], "current_diff": current,
        "measurement_is_current": current == packet["diff"]})
    context = lambda **kwargs: canonical_json(state)  # noqa: E731
    model_input = lambda **kwargs: [{"role": "user", "content": canonical_json(  # noqa: E731
        {"state": state})}]
    monkeypatch.setattr(diagnostic.runner, "_build_context", context)
    monkeypatch.setattr(diagnostic.runner, "_build_model_input", model_input)
    with diagnostic.public_feedback(packet):
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
    {"billing_known": False}, {"billing_known": True, "stop_remaining": True},
])
def test_no_summary_claim_after_uncertainty(result):
    outcome = diagnostic.final_public_check(None, None, None, None, None, result)
    assert outcome["status"] == "INCOMPLETE"
    assert outcome["additional_final_executions"] == 0


def test_restore_no_longer_removes_final_only_resources(monkeypatch):
    captured = {}
    monkeypatch.setattr(diagnostic.exposure, "_fork", lambda *a, **kw: captured.update(kw))
    diagnostic.restore(None, 212, None, 1, None)
    assert "reserved_tool_actions" not in captured
    assert "reserved_wall_seconds" not in captured
    assert captured["preserve_parent_configuration"] is True


def test_v1_approval_cannot_execute_v2(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(canonical_json({"schema": "public-counterexample-repair-v1", "repeat": 1}))
    with pytest.raises(ContractError, match="unsupported manifest"):
        diagnostic.validate(path, diagnostic.sha256_bytes(path.read_bytes()))


def test_final_summary_uses_imported_current_receipt_without_target_execution(
    saved, tmp_path, monkeypatch,  # noqa: F811
):
    packet = diagnostic.packet_api.build_packet(saved["root"])
    entry = diagnostic.check_api.required_check(packet)
    journal = DevJournal(tmp_path / "branch", "run_dev_branch")
    journal.append("public_check_imported", {"observation_id": entry.observation_id,
        "output": {**entry.observation, "binding_hash": entry.binding_hash}})
    branch = SimpleNamespace(workspace=tmp_path, journal=journal)
    current = packet["candidate_diff_hash"]
    monkeypatch.setattr(diagnostic.WorkspaceManager, "diff_summary",
                        lambda workspace: SimpleNamespace(patch_hash=current))
    result = {"billing_known": True, "result": {"artifact_hashes": {}}}
    report = diagnostic.final_public_check(branch, packet, {}, None, None, result)
    assert report["status"] == "FAIL"
    assert report["source"] == "imported_observation" and not report["new_execution"]
    assert report["additional_final_executions"] == 0
    current = "sha256:" + "2" * 64
    later = diagnostic.final_public_check(branch, packet, {}, None, None, result)
    assert later["status"] == "NOT_RUN"


def test_gateway_factory_adds_registered_check_without_mutating_task(
    saved, tmp_path, monkeypatch,  # noqa: F811
):
    packet = diagnostic.packet_api.build_packet(saved["root"])
    task, delegate, probe = object(), object(), object()
    journal = DevJournal(tmp_path, "run_dev_factory")
    class Gateway:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
    monkeypatch.setattr(diagnostic.runner, "DevToolGateway", Gateway)
    with diagnostic.public_feedback(packet):
        gateway = diagnostic.runner.DevToolGateway(
            public_task=task, sandbox=delegate, probe_sandbox=probe, journal=journal)
    assert gateway.kwargs["public_task"] is task
    assert len(gateway.kwargs["supplemental_checks"]) == 1
    assert gateway.kwargs["supplemental_checks"][0].check.id == diagnostic.check_api.CHECK_ID
    assert gateway.kwargs["sandbox"].delegate is delegate
    assert gateway.kwargs["sandbox"].probe is probe
    assert diagnostic.runner.DevToolGateway is Gateway


@pytest.mark.parametrize("first_response", [True, False])
@pytest.mark.parametrize("exploration_offered", [True, False])
def test_feedback_audit_accepts_current_required_failure_and_rejects_finish(
    saved, first_response, exploration_offered,  # noqa: F811
):
    packet = diagnostic.packet_api.build_packet(saved["root"])
    entry = diagnostic.check_api.required_check(packet)
    state = {
        "current_diff": {"patch_hash": packet["candidate_diff_hash"]},
        "workflow_gate": "needs_visible_checks",
        "mutation_readiness": {"state": "ready_to_attempt",
                               "current_anchor_evidence_paths": ["astroid/modutils.py"]},
        "current_sources": [{"path": "astroid/modutils.py", "file_hash": "current-source",
                             "edit_permission": "allowed", "inline_spans": [{
                                 "start_line": 1, "end_line": 1, "content": "editable = 1\n"}]}],
        "visible_check_status": [{"check_id": "base-regression", "status": "PASS"},
                                 {"check_id": entry.check.id, "status": "FAIL"}],
        "supplemental_required_checks": [{"check": entry.check.model_dump(mode="json"),
                                         "binding_hash": entry.binding_hash}],
        "reproduction_review": {"completion": {
            "status": "cases_verified", "baseline_failure_case_ids": ["original-case"],
            "cases": [{"current": {"comparison": "matched"},
                       "comparability": {"status": "same"}}],
        }},
    }
    state = diagnostic.inject(state, packet)
    assert state[diagnostic.FIELD]["required_check_status"] == "FAIL"
    assert state[diagnostic.FIELD]["new_verification_required"] is True
    assert "program_text" not in state[diagnostic.FIELD]
    names = ["replace_text", "stop_task"]
    if exploration_offered:
        names += ["read_file", "search_files"]
    request = {"input": [{"role": "user", "content": canonical_json({"state": state})}],
               "tools": [{"name": name, "parameters": {"properties": {}}}
                         for name in names]}
    branch = SimpleNamespace(request=SimpleNamespace(caller_source_roots={}))
    audit = diagnostic.feedback_audit(branch, request, packet, first_response=first_response)
    assert audit["confirmed_failure_blocks_finish"] is True
    assert audit["available_tools"] == sorted(names)
    assert audit["caller_sources"]["status"] == ("PASS" if exploration_offered else "NOT_OFFERED")
    if first_response:
        assert audit["initial_source_projection"]["spans"][0]["content_chars"] > 0
    request["tools"].append({"name": "finish_task"})
    with pytest.raises(ContractError, match="permits successful finish"):
        diagnostic.feedback_audit(branch, request, packet, first_response=first_response)


def test_unoffered_read_rehearsal_never_restores_or_dispatches(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("unavailable read must not create or dispatch a rehearsal")
    monkeypatch.setattr(diagnostic, "restore", forbidden)
    monkeypatch.setattr(diagnostic.exposure, "rehearse", forbidden)
    request = {"tools": [{"name": "replace_text"}, {"name": "stop_task"}]}
    audit, receipt = diagnostic.rehearse_later_read(None, 212, None, None, None, None, request)
    assert audit["later_read_delivery"]["status"] == receipt["status"] == "NOT_EXERCISED"
    assert not audit["later_response_delivery_checked"]
    caller = diagnostic._caller_scope_audit(request, {"pylint": "pylint"})
    assert caller["offered_source_tools"] == [] and caller["status"] == "NOT_OFFERED"


def test_initial_source_audit_rejects_headers_without_delivered_body():
    state = {"mutation_readiness": {"state": "ready_to_attempt",
                                   "current_anchor_evidence_paths": ["public.py"]},
             "current_sources": [{"path": "public.py", "file_hash": "current",
                                  "edit_permission": "allowed", "headers": [{"start_line": 1}]}]}
    with pytest.raises(ContractError, match="lacks current delivered editable source"):
        diagnostic._initial_source_audit(state)
