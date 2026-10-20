"""Submission requires a public assessment and checks on the submitted candidate."""

from __future__ import annotations

import sys

import pytest
from test_dev_notes_lifecycle_v15 import _gateway

from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.errors import ActionConflict
from patchloop.sandbox import LocalSandbox


def _call(gateway, name, action_id, arguments):
    values = {"name": name, "action_id": action_id, "arguments": arguments}
    if gateway.agent_policy == "thin":
        values["memory_update"] = None
    else:
        mode = {
            "read_file": "inspect", "replace_text": "mutate", "run_check": "verify",
            "finish_task": "finish",
        }[name]
        values["turn_decision"] = PublicTurnDecision(
            mode=mode, basis="Use the current public source and observed check results.",
            evidence_goal="Observe the editable implementation." if mode == "inspect" else None,
        )
    return RequestedTool(**values)


def _execute(gateway, name, action_id, arguments):
    return gateway.execute_batch([_call(gateway, name, action_id, arguments)])[0]


def _edit(gateway, action_id, old, new):
    result = _execute(gateway, "replace_text", action_id, {
        "path": "src.py", "old_text": f"editable = {old}", "new_text": f"editable = {new}",
        "occurrence": 1, "hypothesis": "The public editable value should be positive.",
        "expected_behavior": "Keep the header unchanged and expose the positive editable value.",
    })
    assert result.status == "succeeded", result.message


def _check(gateway, check_id, action_id):
    result = _execute(gateway, "run_check", action_id, {"check_id": check_id})
    assert result.status == "succeeded", result.message
    return result


@pytest.fixture(params=["current", "thin"])
def checked_candidate(tmp_path, request):
    gateway = _gateway(tmp_path)
    gateway.agent_policy = request.param
    gateway.sandbox = LocalSandbox()
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=[sys.executable, "-c", (
            "import runpy; source = runpy.run_path('src.py'); " + predicate
        )])
        for name, predicate in (
            ("behavior", "assert source['editable'] > 0"),
            ("regression", "assert source['header'] == 0"),
        )
    ]
    observed = _execute(gateway, "read_file", "source", {
        "path": "src.py", "start_line": 1, "end_line": 60,
    })
    assert observed.status == "succeeded"
    _edit(gateway, "first-edit", 0, 1)
    for check_id in ("behavior", "regression"):
        assert _check(gateway, check_id, "first-" + check_id).output["passed"] is True
    assert gateway.visible_checks_pass()
    return gateway


def test_finish_schema_requires_the_same_bounded_assessment_for_both_policies():
    schemas = []
    for policy, annotation in (("current", "turn_decision"), ("thin", "memory_update")):
        schema = dev_tool_schemas(
            finish_enabled=True, allowed_tools={"finish_task"}, agent_policy=policy,
        )[0]
        parameters = schema["parameters"]
        assert parameters["additionalProperties"] is False
        assert set(parameters["required"]) == {"assessment", annotation}
        field = parameters["properties"]["assessment"]
        assert field["type"] == "string"
        assert field["minLength"] == 1
        assert field["maxLength"] == 1_500
        parameters["properties"].pop(annotation)
        parameters["required"].remove(annotation)
        schemas.append(schema)
    assert schemas[0] == schemas[1]


def test_passing_checks_cannot_replace_a_valid_assessment(checked_candidate):
    gateway = checked_candidate
    original_diff = gateway.current_diff_hash
    for number, arguments in enumerate((
        {}, {"assessment": ""}, {"assessment": " \t\n "},
        {"assessment": "x" * 1_501}, {"assessment": None}, {"assessment": 1},
        {"assessment": True}, {"assessment": []},
    )):
        result = _execute(gateway, "finish_task", f"invalid-finish-{number}", arguments)
        assert result.status == "failed", arguments
        assert result.error_code == "TOOL_CONTRACT_ERROR"
        assert "assessment" in result.message
    assert gateway.current_diff_hash == original_diff
    assert gateway.visible_checks_pass()


def test_assessment_is_bound_to_durable_submission_and_exact_replay(checked_candidate):
    gateway = checked_candidate
    assessment = (
        "  The positive editable value satisfies the public behavior check and the header "
        "regression passes on this patch. No other task behavior is asserted; ready to submit.  "
    )
    call = _call(gateway, "finish_task", "submit", {"assessment": assessment})
    result = gateway.execute_batch([call])[0]
    assert result.status == "succeeded", result.message
    assert result.output["assessment"] == assessment
    assert result.output["patch_hash"] == gateway.current_diff_hash
    events = gateway.journal.events()
    started = next(event["payload"] for event in events
                   if event["event_type"] == "action_started"
                   and event["payload"]["action_id"] == "submit")
    assert started["arguments"] == {"assessment": assessment}
    assert started["input_hash"] == result.input_hash
    expected_replay = result.model_copy(update={"replayed": True})
    assert gateway.journal.action_result("submit", result.input_hash) == expected_replay

    original_bytes = gateway.journal.path.read_bytes()
    restored = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task,
        sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits,
        agent_policy=gateway.agent_policy,
    )
    assert restored.execute_batch([call])[0] == expected_replay
    assert gateway.journal.path.read_bytes() == original_bytes
    changed = _call(restored, "finish_task", "submit", {"assessment": "Different judgment."})
    with pytest.raises(ActionConflict, match="reused with different input"):
        restored.execute_batch([changed])
    assert gateway.journal.path.read_bytes() == original_bytes


def test_further_edit_requires_all_checks_again_before_assessed_finish(checked_candidate):
    gateway = checked_candidate
    old_hash = gateway.current_diff_hash
    _edit(gateway, "review-edit", 1, 2)
    current_hash = gateway.current_diff_hash
    assert current_hash != old_hash
    assert not gateway.visible_checks_pass()
    assessment = {"assessment": "The reviewed positive value and preserved header are ready."}
    stale = _execute(gateway, "finish_task", "stale-checks", assessment)
    assert stale.status == "failed"
    assert "all visible checks must pass against the current diff" in stale.message

    assert _check(gateway, "behavior", "review-behavior").output["passed"] is True
    partial = _execute(gateway, "finish_task", "partial-checks", assessment)
    assert partial.status == "failed"
    assert "all visible checks must pass against the current diff" in partial.message

    assert _check(gateway, "regression", "review-regression").output["passed"] is True
    finished = _execute(gateway, "finish_task", "review-submit", assessment)
    assert finished.status == "succeeded", finished.message
    assert finished.output["assessment"] == assessment["assessment"]
    assert finished.output["patch_hash"] == current_hash


def test_agent_assessment_cannot_override_a_failed_current_check(checked_candidate):
    gateway = checked_candidate
    _edit(gateway, "bad-edit", 1, -1)
    assert _check(gateway, "behavior", "failed-behavior").output["passed"] is False
    failed = _execute(gateway, "finish_task", "unsupported-submit", {
        "assessment": "The agent considers this patch ready despite the failed check.",
    })
    assert failed.status == "failed"
    assert "all visible checks must pass against the current diff" in failed.message
