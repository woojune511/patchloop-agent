"""Current completion guidance survives the actual public native-input boundary."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from native_history_support import input_context, start_turn
from test_dev_feedback_integration_v18 import _context, _input
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import (
    DEV_READ_TOOLS,
    DEV_SINGLE_ACTION_TOOLS,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import sha256_json


class CheckSandbox:
    def __init__(self):
        self.calls = []

    def run_check(self, workspace, check, **kwargs):
        del workspace, kwargs
        self.calls.append(check.id)
        failed = self.calls == ["contract", "regression"]
        return SandboxResult(
            command=check.command, exit_code=int(failed), stdout="PUBLIC_CHECK_RESULT",
            stderr="", duration_ms=1, timed_out=False, truncated=False, original_output_bytes=19,
        )


def _check(check_id, action_id):
    return RequestedTool(
        name="run_check", action_id=action_id, arguments={"check_id": check_id},
        turn_decision=PublicTurnDecision(mode="verify", basis="Check this public candidate."),
    )


def _batch(gateway, call, tmp_path):
    latest = gateway.journal.latest_tool_batch_results()
    turn_id = f"turn-{call.action_id}"
    start_turn(
        gateway.journal, ArtifactStore(tmp_path / "artifacts"), turn_id,
        context=_context(gateway, latest), results=latest,
    )
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [call.model_dump(mode="json")],
    })
    result = gateway.execute(call)
    assert result.status == "succeeded", result.message
    gateway.journal.append("attempt_card", runner._attempt_card(result, gateway))
    gateway.journal.append("tool_batch_finished", {
        "turn_id": turn_id, "action_ids": [call.action_id],
    })
    return result


def _repaired_candidate(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.sandbox = CheckSandbox()
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=["python", "-c", "pass"])
        for name in ("contract", "regression")
    ]
    _read(gateway)
    _batch(gateway, _mutation("first-edit"), tmp_path)
    _batch(gateway, _check("contract", "old-contract"), tmp_path)
    _batch(gateway, _check("regression", "old-regression"), tmp_path)
    _batch(gateway, _mutation("repair", "editable = 1", "editable = 2"), tmp_path)
    latest = _batch(gateway, _check("regression", "new-regression"), tmp_path)
    return gateway, latest


def test_recheck_guidance_reaches_native_input_and_survives_restart(tmp_path):
    gateway, latest = _repaired_candidate(tmp_path)
    canonical = _context(gateway, [latest])
    items = _input(gateway, [latest], tmp_path, context=canonical)
    view = input_context(items)
    assert view["completion_guidance"] == json.loads(canonical)["completion_guidance"]
    guidance = view["completion_guidance"]
    assert not guidance["submission_ready"]
    assert guidance["next_action"] == {"tool": "run_check", "check_id": "contract"}
    assert guidance["diff_hash"] == gateway.current_diff_hash
    assert "Run one remaining visible check for the current diff: contract" in guidance["message"]
    assert guidance["message"] in items[-1]["content"]
    assert [row["status"] for row in view["visible_check_status"]] == ["NOT_RUN", "PASS"]
    assert list(json.loads(items[-1]["content"])["state"])[:4] == [
        "workflow_gate", "completion_guidance", "visible_check_status",
        "remaining_visible_check_ids",
    ]
    old_pass = next(row for row in view["recent_checks"] if row["action_id"] == "old-contract")
    assert old_pass["passed"] is True
    assert old_pass["evidence_currency"] == "historical"
    assert old_pass["counts_toward_completion"] is False
    current_pass = next(
        row for row in view["recent_checks"] if row["action_id"] == latest.action_id
    )
    assert current_pass["evidence_currency"] == "current"
    assert current_pass["counts_toward_completion"] is True
    native = {item["call_id"]: json.loads(item["output"]) for item in items
              if item.get("type") == "function_call_output"}
    assert native["old-contract"]["output"]["passed"] is True
    assert "evidence_currency" not in native["old-contract"]["output"]
    review = view["recent_attempt_result_next_question"]
    assert len(review) == 1
    assert review[0]["action_id"] == latest.action_id
    assert review[0]["mutation_expectation"]["diff_hash"] == gateway.current_diff_hash

    journal_bytes = gateway.journal.path.read_bytes()
    source_bytes = (gateway.workspace / "src.py").read_bytes()
    calls = list(gateway.sandbox.calls)
    restarted = _restart(gateway)
    assert _input(restarted, [latest], tmp_path, context=canonical) == items
    restored = input_context(_input(restarted, [latest], tmp_path))
    assert restored["completion_guidance"] == guidance
    assert restored["recent_checks"] == view["recent_checks"]
    assert restored["recent_attempt_result_next_question"] == review
    assert gateway.journal.path.read_bytes() == journal_bytes
    assert (gateway.workspace / "src.py").read_bytes() == source_bytes
    assert gateway.sandbox.calls == calls


def test_guidance_tracks_recheck_then_submission_without_rewriting_history(tmp_path):
    gateway, latest = _repaired_candidate(tmp_path)
    before = _input(gateway, [latest], tmp_path)
    result = _batch(gateway, _check("contract", "rechecked-contract"), tmp_path)
    after = _input(gateway, [result], tmp_path)
    assert after[:len(before)] == before
    view = input_context(after)
    assert view["completion_guidance"]["submission_ready"]
    assert view["completion_guidance"]["next_action"] == {"tool": "finish_task"}
    assert view["remaining_visible_check_ids"] == []
    assert all(row["status"] == "PASS" for row in view["visible_check_status"])
    finish = _batch(gateway, RequestedTool(
        name="finish_task", action_id="submitted", arguments={},
        turn_decision=PublicTurnDecision(mode="finish", basis="Submit the checked public diff."),
    ), tmp_path)
    assert finish.output["patch_hash"] == result.output["diff_hash"]
    assert gateway.sandbox.calls == ["contract", "regression", "regression", "contract"]


@pytest.mark.parametrize("gate,statuses,allowed,next_action", [
    ("needs_mutation", ["NOT_RUN"], {"read_file", "stop_task"}, {"tool": "read_file"}),
    ("needs_mutation", ["NOT_RUN"], {"search_files", "stop_task"}, {"tool": "search_files"}),
    ("needs_mutation", ["NOT_RUN"], {"replace_text", "stop_task"}, {"tool": "replace_text"}),
    ("needs_visible_checks", ["FAIL"], {"replace_text", "read_file", "stop_task"},
     {"tool": "replace_text"}),
    ("needs_visible_checks", ["FAIL"], {"read_file", "stop_task"}, {"tool": "read_file"}),
    ("needs_visible_checks", ["NOT_RUN"], {"run_check", "stop_task"},
     {"tool": "run_check", "check_id": "contract"}),
    ("ready_to_submit", ["PASS"], {"finish_task", "stop_task"}, {"tool": "finish_task"}),
    ("needs_visible_checks", ["NOT_RUN"], {"stop_task"}, None),
])
def test_guidance_is_advisory_and_recommends_only_an_offered_action(
    gate, statuses, allowed, next_action,
):
    snapshot = SimpleNamespace(
        diff=SimpleNamespace(patch_hash="current"), ready_to_submit=gate == "ready_to_submit",
        visible_check_status=tuple({"check_id": "contract", "status": s} for s in statuses),
    )
    policy = SimpleNamespace(
        workflow_gate=gate, allowed_tools=frozenset(allowed), check_ids=("contract",),
    )
    before = copy.deepcopy((snapshot, policy))
    result = runner._completion_guidance(snapshot, policy)
    assert (snapshot, policy) == before
    assert result["next_action"] == next_action
    assert len(json.dumps(result)) < 650
    if next_action:
        assert next_action["tool"] in allowed
    described_unavailable = {
        tool for tool in {
        "read_file", "search_files", "replace_text", "run_check", "finish_task",
        } - allowed if tool in result["message"]
    }
    if described_unavailable:
        assert described_unavailable == {"replace_text"}
        assert result["stage"] == "needs_source_evidence"
        assert "temporarily unavailable" in result["message"]


def test_success_prose_does_not_create_a_new_stop_rejection_or_a_submission():
    gateway = SimpleNamespace(spans={}, current_diff_hash="current")
    result = DevToolGateway._stop_task(gateway, {
        "reason_code": "no_safe_scoped_mutation", "summary": "Everything is complete.",
    })
    assert result["reason_code"] == "no_safe_scoped_mutation"
    assert "patch" not in result


def test_completion_descriptions_preserve_tool_order_and_current_input_shapes():
    schemas = dev_tool_schemas(
        finish_enabled=True, allowed_tools=DEV_READ_TOOLS | DEV_SINGLE_ACTION_TOOLS,
        check_ids=["first", "second"],
    )

    def without_descriptions(value):
        if isinstance(value, dict):
            return {key: without_descriptions(item) for key, item in value.items()
                    if key != "description"}
        if isinstance(value, list):
            return [without_descriptions(item) for item in value]
        return value

    assert sha256_json(without_descriptions(schemas)) == (
        "sha256:b9a718dbdbcd9aabd230b2ee90b8ae680decdb0d4069986e9209c3e1fd03adbe"
    )
    assert [schema["name"] for schema in schemas] == [
        "search_files", "read_file", "run_check", "replace_text", "stop_task", "finish_task",
        "run_probe",
    ]
    descriptions = {schema["name"]: schema["description"] for schema in schemas}
    assert "without submission or evaluation" in descriptions["stop_task"]
    assert "not successful completion" in descriptions["stop_task"]
    assert "same diff" in descriptions["finish_task"]
    assert "latest completion_guidance and visible_check_status" in DEV_SYSTEM_PROMPT
    assert "historical PASS does not" in DEV_SYSTEM_PROMPT
    assert "not merely when no edit is needed" in DEV_SYSTEM_PROMPT
    assert len(DEV_SYSTEM_PROMPT) <= 8007
