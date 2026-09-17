"""Eligible submission stays available while current case evidence guides the choice."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from native_history_support import input_context
from test_dev_behavior_cases import CONTRAST
from test_dev_completion_v27 import CheckSandbox, _batch, _check
from test_dev_feedback_integration_v18 import _input
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart
from test_dev_requirement_reference import public_task

from patchloop.contracts import RegisteredCheck
from patchloop.dev import runner
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.util import canonical_json, sha256_json


def _guidance(mutation, offered, *, ready=True):
    snapshot = SimpleNamespace(
        diff=SimpleNamespace(patch_hash="current"), ready_to_submit=ready,
        visible_check_status=({"check_id": "public", "status": "PASS" if ready else "NOT_RUN"},),
    )
    policy = SimpleNamespace(
        workflow_gate="ready_to_submit" if ready else "needs_visible_checks",
        allowed_tools=frozenset(offered), check_ids=("public",),
    )
    before = copy.deepcopy((snapshot, policy, mutation))
    result = runner._completion_guidance(snapshot, policy, mutation=mutation)
    assert before == (snapshot, policy, mutation)
    assert len(canonical_json(result)) < 1_700
    return result


def _record(status="recorded", diff="current"):
    return {"diff_hash": diff, "behavior_cases": {
        "status": status, "cases": CONTRAST,
        "interpretation_status": "model_authored_unverified", "coverage_status": "not_assessed",
    }}


@pytest.mark.parametrize("review_tools", [
    {"read_file"}, {"search_files"}, {"run_probe"}, {"read_file", "search_files", "run_probe"},
])
def test_current_cases_offer_only_affordable_review_and_submission(review_tools):
    mutation = _record()
    result = _guidance(mutation, review_tools | {"finish_task", "stop_task"})
    assert result["submission_ready"] and result["next_action"] is None
    choice = result["verification_choice"]
    assert choice["coverage_status"] == "not_assessed"
    assert choice["case_record_hash"] == sha256_json(mutation["behavior_cases"])
    assert {row["tool"] for row in choice["available_actions"]} == review_tools | {"finish_task"}
    assert "no extra action or annotation is required" in result["message"]
    assert "implementation trigger fixed" in result["message"]
    assert ("Project dependencies are unavailable" in canonical_json(choice)) is (
        "run_probe" in review_tools
    )
    assert CONTRAST["scope_basis"] not in canonical_json(result)  # Existing record is referenced.


@pytest.mark.parametrize("mutation", [
    None, {}, {"diff_hash": "current"}, _record("invalid"), _record("omitted"),
    _record("stale"), _record(diff="older"),
])
def test_absent_invalid_stale_or_older_cases_keep_existing_guidance(mutation):
    result = _guidance(mutation, {"read_file", "run_probe", "finish_task", "stop_task"})
    assert result["next_action"] == {"tool": "finish_task"}
    assert "verification_choice" not in result


def test_case_presence_neither_reopens_closed_tools_nor_skips_required_checks():
    closed = _guidance(_record(), {"finish_task", "stop_task"})
    assert closed["next_action"] == {"tool": "finish_task"}
    assert "verification_choice" not in closed
    missing = _guidance(_record(), {"read_file", "run_check", "stop_task"}, ready=False)
    assert missing["next_action"] == {"tool": "run_check", "check_id": "public"}
    assert "verification_choice" not in missing
    unavailable = _guidance(_record(), {"read_file", "stop_task"})
    assert "verification_choice" not in unavailable


def test_case_choice_survives_restart_and_does_not_block_direct_submission(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.public_task = public_task()
    gateway.sandbox = CheckSandbox()
    gateway.public_task.visible_checks = [
        RegisteredCheck(id="contract", command=["python", "-c", "pass"]),
    ]
    _read(gateway)
    mutation = _mutation("with-cases")
    mutation.arguments["behavior_cases"] = CONTRAST
    edited = _batch(gateway, mutation, tmp_path)
    check = _batch(gateway, _check("contract", "checked"), tmp_path)
    original = _input(gateway, [check], tmp_path)
    view = input_context(original)
    guidance = view["completion_guidance"]
    assert view["workflow_gate"] == "ready_to_submit" and guidance["next_action"] is None
    record = view["last_successful_mutation"]
    assert record["delivery"] == "preceding_function_call_output"
    output = next(item for item in original if item.get("type") == "function_call_output"
                  and item.get("call_id") == record["action_id"])
    cases = json.loads(output["output"])["output"]["mutation"]["behavior_cases"]
    assert cases == edited.output["mutation"]["behavior_cases"]
    assert guidance["verification_choice"]["case_record_hash"] == sha256_json(
        cases,
    )
    before = gateway.journal.path.read_bytes(), (gateway.workspace / "src.py").read_bytes()
    restored = _restart(gateway)
    assert input_context(_input(restored, [check], tmp_path))["completion_guidance"] == guidance
    assert before == (
        gateway.journal.path.read_bytes(), (gateway.workspace / "src.py").read_bytes(),
    )
    assert _input(gateway, [check], tmp_path) == original
    finish = _batch(gateway, RequestedTool(
        name="finish_task", action_id="finish-with-cases", arguments={},
        turn_decision=PublicTurnDecision(mode="finish", basis="Submit after the public check."),
    ), tmp_path)
    assert finish.output["patch_hash"] == check.output["diff_hash"]
    assert gateway.sandbox.calls == ["contract"]
