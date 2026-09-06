from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_dev_context_v12 import note_call
from test_dev_notes_lifecycle_v15 import _gateway, _read, _restart

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import DevToolResult, PublicTurnDecision, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.verification_concerns import (
    empty_verification_state,
    project_verification_concerns,
    update_verification_concerns,
    verification_updates_schema,
)
from patchloop.util import sha256_json


def _result(action_id, check_id="traversal", diff="current", *, passed=True, status="succeeded"):
    return DevToolResult(
        action_id=action_id, input_hash=sha256_json(action_id), tool="run_check", status=status,
        output={
            "check_id": check_id, "diff_hash": diff, "passed": passed,
            "failure_signature": None if passed else "public-failure",
            "stdout": f"output:{action_id}", "stderr": "", "exit_code": 0 if passed else 1,
            "timed_out": False,
        },
        workspace_diff_hash=diff,
    )


def _append(gateway, result):
    gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    if result.status == "succeeded":
        value = result.output
        gateway.checks_by_diff.setdefault(value["diff_hash"], {})[value["check_id"]] = value


def _summaries_gateway(tmp_path):
    return SimpleNamespace(
        journal=DevJournal(tmp_path, "run_dev_check_identity"), checks_by_diff={},
    )


def _native_input(gateway, latest, tmp_path):
    call = RequestedTool(
        name="run_check", action_id=latest.action_id,
        arguments={"check_id": latest.output["check_id"]},
        turn_decision=PublicTurnDecision(mode="verify", basis="Check the current public behavior."),
    )
    turn_id = f"turn-{latest.action_id}"
    from native_history_support import start_turn

    start_turn(gateway.journal, ArtifactStore(tmp_path / "artifacts"), turn_id)
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [call.model_dump(mode="json")],
    })
    gateway.journal.append("tool_batch_finished", {
        "turn_id": turn_id, "action_ids": [latest.action_id],
    })
    return runner._build_model_input(
        journal=gateway.journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
        context=json.dumps({
            "recent_checks": runner._recent_checks(gateway), "working_notes": {},
            "current_diff": {"patch_hash": latest.output["diff_hash"]},
        }),
        latest_tool_results=[latest],
    )


def test_retained_summaries_keep_identity_and_existing_diff_check_order(tmp_path):
    gateway = _summaries_gateway(tmp_path)
    _append(gateway, _result("first", "traversal", "baseline", passed=False))
    _append(gateway, _result("second", "regression", "baseline"))
    _append(gateway, _result("third", "regression", "current"))
    _append(gateway, _result("fourth", "traversal", "current"))
    # Repeated actions replace one stored row; they must not displace other checks.
    for number in range(4):
        _append(gateway, _result(f"repeated-{number}", "regression", "baseline"))
    rows = runner._recent_checks(gateway)
    assert [(row["action_id"], row["check_id"], row["diff_hash"]) for row in rows] == [
        ("repeated-3", "regression", "baseline"),
        ("third", "regression", "current"),
        ("fourth", "traversal", "current"),
    ]
    assert rows[0]["stdout"] == "output:repeated-3"


def test_failed_check_keeps_identity_but_failed_action_does_not_replace_it(tmp_path):
    gateway = _summaries_gateway(tmp_path)
    _append(gateway, _result("check-failed", passed=False))
    _append(gateway, _result("action-failed", passed=False, status="failed"))
    rows = runner._recent_checks(gateway)
    assert len(rows) == 1
    assert rows[0]["action_id"] == "check-failed"
    assert rows[0]["passed"] is False


def test_native_delivery_preserves_older_check_identity_without_copying_latest_body(tmp_path):
    gateway = _summaries_gateway(tmp_path)
    regression = _result("regression-action", "regression")
    traversal = _result("traversal-action", "traversal")
    _append(gateway, regression)
    _append(gateway, traversal)
    original = copy.deepcopy(runner._recent_checks(gateway))
    items = _native_input(gateway, traversal, tmp_path)
    payload = json.loads(items[1]["content"])
    retained, native_reference = payload["recent_checks"]
    assert retained["action_id"] == regression.action_id
    assert retained["check_id"] == "regression"
    assert retained["diff_hash"] == "current"
    assert retained["stdout"] == regression.output["stdout"]
    assert "delivery" not in retained
    assert native_reference["action_id"] == traversal.action_id
    assert native_reference["check_id"] == "traversal"
    assert native_reference["diff_hash"] == "current"
    assert native_reference["delivery"] == "preceding_function_call_output"
    assert "stdout" not in native_reference
    native = [json.loads(item["output"]) for item in items
              if item.get("type") == "function_call_output"]
    assert len(native) == 1
    assert native[0]["action_id"] == traversal.action_id
    assert native[0]["output"]["check_id"] == "traversal"
    assert runner._recent_checks(gateway) == original


def test_restart_restores_summary_identity_without_new_events(tmp_path):
    gateway = _gateway(tmp_path)
    _append(gateway, _result("historical-check", "regression", "baseline", passed=False))
    _append(gateway, _result("current-check", "regression", gateway.current_diff_hash))
    before = gateway.journal.path.read_bytes()
    expected = runner._recent_checks(gateway)
    assert runner._recent_checks(_restart(gateway)) == expected
    assert gateway.journal.path.read_bytes() == before


def _operation(operation, *, statement=None, evidence=None, reason=None):
    return {
        "operation": operation, "concern_id": None if operation == "upsert" else "v1",
        "statement": statement, "evidence_action_id": evidence, "reason": reason,
    }


def _annotation(operation):
    return {
        "findings": [], "remove_note_ids": [], "open_question": None,
        "verification_updates": [operation],
    }


def test_wrong_prose_reason_is_nonblocking_but_actual_check_label_is_retained(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    create = note_call("create-concern", _annotation(_operation(
        "upsert", statement="The broader regression behavior remains unverified.",
    )))
    gateway.record_working_notes_update([create], turn_id="create")
    traversal = _result("actual-traversal-action", "traversal", gateway.current_diff_hash)
    _append(gateway, traversal)
    resolve = note_call("resolve-concern", _annotation(_operation(
        "resolve", evidence=traversal.action_id,
        reason="The regression suite passed and addresses this concern.",
    )))
    payload = gateway.record_working_notes_update([resolve], turn_id="resolve")
    assert payload["receipt"]["verification"]["status"] == "applied"
    assert gateway.execute(resolve).status == "succeeded"
    decision = gateway.working_notes()["verification"]["items"][0]["decision"]
    assert decision["evidence"]["action_id"] == traversal.action_id
    assert decision["evidence"]["check_id"] == "traversal"
    assert decision["evidence"]["diff_hash"] == gateway.current_diff_hash
    assert decision["reason"].startswith("The regression suite")
    assert decision["basis"] == "model_interpretation_of_result"
    before = gateway.journal.path.read_bytes()
    assert _restart(gateway).working_notes() == gateway.working_notes()
    assert gateway.journal.path.read_bytes() == before


@pytest.mark.parametrize("next_diff", ["current", "later"])
def test_check_label_survives_projection_and_serialized_historical_decision(next_diff):
    state, _ = update_verification_concerns(
        empty_verification_state(),
        [_operation("upsert", statement="A public branch is untested.")],
        diff_hash="current", prior_results={}, turn_id="create",
    )
    result = _result("verified", "named-public-check")
    state, _ = update_verification_concerns(
        state, [_operation("resolve", evidence="verified", reason="Public observation.")],
        diff_hash="current", prior_results={"verified": result.model_dump(mode="json")},
        turn_id="resolve",
    )
    restored = json.loads(json.dumps(state))
    projected = project_verification_concerns(restored, diff_hash=next_diff)
    evidence = projected["items"][0]["decision"]["evidence"]
    assert evidence["check_id"] == "named-public-check"
    assert evidence["currency"] == ("current" if next_diff == "current" else "historical")
    assert restored == state


def test_probe_keeps_action_identity_without_inventing_a_registered_check_or_probe_id():
    state, _ = update_verification_concerns(
        empty_verification_state(),
        [_operation("upsert", statement="A public branch is untested.")],
        diff_hash="current", prior_results={}, turn_id="create",
    )
    probe = {
        "action_id": "experiment", "input_hash": "sha256:probe", "tool": "run_probe",
        "status": "succeeded", "workspace_diff_hash": "current",
        "output": {"diff_hash": "current", "status": "passed", "exit_code": 0},
    }
    state, receipt = update_verification_concerns(
        state, [_operation("resolve", evidence="experiment", reason="Public observation.")],
        diff_hash="current", prior_results={"experiment": probe}, turn_id="resolve",
    )
    assert receipt["status"] == "applied"
    evidence = state["items"][0]["decision"]["evidence"]
    assert evidence["action_id"] == "experiment"
    assert "check_id" not in evidence
    assert "probe_id" not in evidence


def test_resolution_identity_does_not_add_model_authored_check_id_field():
    schema = verification_updates_schema()["items"]
    assert list(schema["properties"]) == [
        "operation", "concern_id", "statement", "evidence_action_id", "reason",
    ]
    assert schema["required"] == list(schema["properties"])
