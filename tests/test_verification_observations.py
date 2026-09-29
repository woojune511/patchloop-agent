from __future__ import annotations

from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart
from test_dev_verification_flow_v17 import _apply_update, _completed_check, _operation, _update

from patchloop.dev.verification_concerns import (
    empty_verification_state,
    project_verification_concerns,
    update_verification_concerns,
)
from patchloop.dev.verification_observations import project_verification_observations


def failed(action="failed", tool="run_probe"):
    return {"action_id": action, "input_hash": "hash", "tool": tool,
            "status": "succeeded", "workspace_diff_hash": "before",
            "output": {"status": "failed", "exit_code": 1,
                       "stderr": "SyntaxError UNRETAINED", "question": "Does it work?"}}


def test_execution_failure_is_not_a_bug_verdict_and_catalog_is_bounded():
    results = [failed(str(i)) for i in range(8)]
    results.append(results[-1])
    view = project_verification_observations(results, [], diff_hash="after")
    assert view["omitted_count"] == 2
    assert len(view["items"]) == 6
    assert all(x["behavior_verdict"] == "not_assessed" for x in view["items"])
    assert all(x["currency"] == "historical" for x in view["items"])
    assert "UNRETAINED" not in str(view)
    assert view["items"][-1]["origin"] == "agent_probe"


def test_registered_success_codes_are_owned_by_check_verdict():
    result = failed(tool="run_check")
    result["output"] = {"passed": True, "exit_code": 1}
    assert project_verification_observations([result], [], diff_hash="before")["items"] == []


def test_link_requires_completed_observation_and_retains_origin_on_edit():
    operation = _operation(statement="Investigate experiment failure", evidence="failed")
    state, receipt = update_verification_concerns(
        empty_verification_state(), [operation], diff_hash="before", prior_results={}, turn_id="t1")
    assert receipt["updates"][0]["code"] == "unobserved_verification_observation"
    state, receipt = update_verification_concerns(
        state, [operation], diff_hash="before", prior_results={"failed": failed()}, turn_id="t2")
    assert receipt["status"] == "applied"
    view = project_verification_concerns(state, diff_hash="after")
    assert view["items"][0]["observation"]["currency"] == "historical"
    assert view["unresolved_ids"] == ["v1"]
    # An existing concern cannot silently replace the originating observation.
    operation.update(concern_id="v1", evidence_action_id="other")
    unchanged, receipt = update_verification_concerns(
        state, [operation], diff_hash="before", prior_results={"other": failed("other")},
        turn_id="t3")
    assert unchanged == state
    assert receipt["updates"][0]["code"] == "observation_already_bound"


def test_gateway_failure_survives_pass_focus_edit_and_restart_without_finish_gate(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    failure = _completed_check(gateway, "failed", passed=False)
    before = gateway.verification_concerns()["observations"]["items"]
    assert before[0]["action_id"] == failure.action_id
    assert gateway.verification_concerns()["items"] == []
    _apply_update(gateway, "link", _update([
        _operation(statement="Check the observed mismatch", evidence="failed")]))
    _apply_update(gateway, "focus", _update(question="Different focus"))
    _completed_check(gateway, "passed")
    assert gateway.verification_concerns()["unresolved_ids"] == ["v1"]
    assert gateway.verification_concerns()["observations"]["items"][0]["concern_ids"] == ["v1"]
    gateway.execute(_mutation("edit"))
    _completed_check(gateway, "after-edit")
    view = gateway.verification_concerns()
    assert view["observations"]["items"][0]["currency"] == "historical"
    assert _restart(gateway).verification_concerns() == view
