"""Public input auditing only; no provider, sandbox, or checkpoint execution."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from diagnostics import replay_feedback_comparison as diagnostic
from patchloop.dev import completion_context
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND
from patchloop.errors import ContractError
from patchloop.util import canonical_json

PACKET = {"elapsed_ms": 1000}


@pytest.fixture
def audit_case(monkeypatch):
    result = {
        "action_id": "checkpoint_helper_replay", "input_hash": "sha256:input",
        "tool": "run_probe", "status": "succeeded", "error_code": None, "message": None,
        "workspace_diff_hash": "sha256:candidate",
        "output": {
            "status": "passed", "exit_code": 0, "timed_out": False, "truncated": False,
            "cleanup_failed": False, "deadline_exhausted": False,
            "stdout": "{'selected': 'missing/__init__.py'}\n", "stderr": "",
            "source_hash": "sha256:source", "snapshot_hash": "sha256:snapshot",
            "question": "Does the public caller still select the missing path?",
        },
    }
    state = completion_context.project({
        "workflow_gate": "ready_to_submit",
        "completion_guidance": {"verification_policy": "public-checks-v1"},
        "available_tool_names": ["run_probe", "finish_task"],
        "remaining_budget": {
            "model_calls": 5, "tool_actions": 8, "accepted_mutations": 2,
            "active_wall_time_seconds": 120, "total_active_wall_time_seconds": 150,
            "cost": {"settled_usage": 200_000_000, "remaining": 800_000_000},
        },
        "current_diff": {"patch_hash": "sha256:candidate"},
        "visible_check_status": [{"check_id": "base-regression", "status": "PASS",
                                  "diff_hash": "sha256:candidate"}],
        "latest_tool_results": [diagnostic.runner.project_probe_result(copy.deepcopy(result))],
        "segment_handoff": {"segment_id": "segment_123"},
    })
    request = {"input": [{"role": "user", "content": canonical_json({"state": state})}],
               "tools": [{"name": "run_probe"}, {"name": "finish_task"}]}
    branch = SimpleNamespace(
        request=SimpleNamespace(
            limits=SimpleNamespace(max_model_calls=20, max_tool_actions=40,
                                   max_accepted_mutations=3, wall_time_seconds=180),
            verification_policy="public-checks-v1", probe_policy="none",
            max_cost_usd=Decimal("1"), evaluation_reserve_seconds=30,
        ),
        journal=SimpleNamespace(events=lambda: [{
            "event_type": "action_finished", "payload": {"result": {
                "tool": "replace_text", "status": "succeeded", "error_code": None,
            }},
        }]),
        initial_spent_nanos=200_000_000, active_elapsed_ms=10000,
    )
    monkeypatch.setattr(diagnostic.runner, "_restore_counters", lambda _: SimpleNamespace(
        model_calls=15, tool_actions=32,
    ))
    monkeypatch.setattr(diagnostic.checkpoint, "packet_result", lambda _: copy.deepcopy(result))
    return branch, request, result


def update_state(request, mutate):
    payload = json.loads(request["input"][-1]["content"])
    mutate(payload["state"])
    request["input"][-1]["content"] = canonical_json(payload)


def test_audit_accepts_current_completion_probe_output(audit_case):
    branch, request, _ = audit_case
    audit = diagnostic.feedback_audit(branch, request, packet=PACKET)
    assert audit["raw_replay_delivered"] is True
    assert audit["remaining_model_calls"] == 5
    assert audit["remaining_tool_actions"] == 8


@pytest.mark.parametrize("field,value", [
    ("input_hash", "sha256:other-input"),
    ("workspace_diff_hash", "sha256:other-candidate"),
    ("status", "failed"),
    ("tool", "run_check"),
])
def test_audit_rejects_changed_result_identity(audit_case, field, value):
    branch, request, _ = audit_case
    update_state(request, lambda state: state["latest_tool_results"][0].update({field: value}))
    with pytest.raises(ContractError):
        diagnostic.feedback_audit(branch, request, packet=PACKET)


@pytest.mark.parametrize("field,value", [("exit_code", 1), ("timed_out", True),
                                       ("truncated", True), ("snapshot_hash", "sha256:other")])
def test_audit_rejects_changed_execution_observation(audit_case, field, value):
    branch, request, _ = audit_case
    update_state(request, lambda state: state["latest_tool_results"][0]["output"].update(
        {field: value},
    ))
    with pytest.raises(ContractError):
        diagnostic.feedback_audit(branch, request, packet=PACKET)


def test_audit_does_not_join_output_from_different_actions(audit_case):
    branch, request, result = audit_case

    def split_output(state):
        state["latest_tool_results"][0]["output"]["stdout"] = "different observation"
        other = copy.deepcopy(result)
        other["action_id"] = "different_helper"
        state["latest_tool_results"].append(other)

    update_state(request, split_output)
    with pytest.raises(ContractError):
        diagnostic.feedback_audit(branch, request, packet=PACKET)


def test_audit_accepts_exact_public_archive_delivery(audit_case):
    branch, request, result = audit_case
    update_state(request, lambda state: state.update({"latest_tool_results": []}))
    request["input"].insert(0, {
        "role": "developer", "content": canonical_json({
            "kind": PUBLIC_EVIDENCE_KIND,
            "referenced_public_exchanges": [{
                "type": "function_call_output", "call_id": result["action_id"],
                "output": canonical_json(diagnostic.runner.project_probe_result(result)),
            }],
        }),
    })
    assert diagnostic.feedback_audit(branch, request, packet=PACKET)["raw_replay_delivered"] is True


@pytest.mark.parametrize("field,value", [
    ("model_calls", 6), ("tool_actions", 9), ("accepted_mutations", 3),
    ("active_wall_time_seconds", 140),
    ("cost", {"settled_usage": 200_000_000, "remaining": 900_000_000}),
])
def test_audit_rejects_refunded_resources(audit_case, field, value):
    branch, request, _ = audit_case
    update_state(request, lambda state: state["remaining_budget"].update({field: value}))
    with pytest.raises(ContractError):
        diagnostic.feedback_audit(branch, request, packet=PACKET)


def test_normalization_ignores_clock_and_segment_identity_only(audit_case):
    _, request, _ = audit_case
    changed = copy.deepcopy(request)

    def advance_clock(state):
        state["remaining_budget"]["active_wall_time_seconds"] -= 1
        state["remaining_budget"]["total_active_wall_time_seconds"] -= 1
        state["segment_handoff"]["segment_id"] = "another_segment"

    update_state(changed, advance_clock)
    assert diagnostic.normalized_request(changed) == diagnostic.normalized_request(request)
    update_state(changed, lambda state: state["latest_tool_results"][0]["output"].update(
        stdout="different observation",
    ))
    assert diagnostic.normalized_request(changed) != diagnostic.normalized_request(request)
