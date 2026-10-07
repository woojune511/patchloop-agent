"""Policy parity for real gateway checks, citations and repair recheck accounting."""

from __future__ import annotations

import pytest
from test_dev_notes_lifecycle_v15 import _gateway
from test_dev_probe_cases import ExecutingProbe
from test_dev_probes import context as probe_context
from test_dev_repair_recheck import CheckSandbox
from test_dev_verification_concerns_v17 import concern
from test_selected_tests import TARGET, RecordingSandbox, enable
from test_thin_policy_gateway import call, mutation, restart

from patchloop.contracts import RegisteredCheck
from patchloop.dev import runner
from patchloop.dev.probe_observation import probe_observation
from patchloop.dev.test_selection import recent_tests


def source_call(policy, action_id="read", *, end_line=60, update=None):
    return call(policy, action_id=action_id, arguments={
        "path": "src.py", "start_line": 1, "end_line": end_line,
    }, update=update)


def source_edit(policy, action_id, old="editable = 0", new="editable = 1"):
    return call(policy, "replace_text", action_id, {
        "path": "src.py", "old_text": old, "new_text": new, "occurrence": 1,
        "hypothesis": "Change the observed editable value.",
        "expected_behavior": "The observed declaration uses the requested value.",
        "causal_revision": None,
    })


def completed_batch(gateway, requested):
    """A scripted model action with the same durable counting boundaries as the runner."""
    serialized = requested.model_dump(mode="json")
    payload = {"turn_id": f"turn-{requested.action_id}", "tool_calls": [serialized]}
    gateway.journal.append("model_call_finished", payload)
    gateway.journal.append("turn_decision_recorded", payload)
    gateway.journal.append("tool_batch_started", payload)
    result, = gateway.execute_batch([requested])
    assert result.status == "succeeded", result.message
    gateway.journal.append("tool_batch_finished", {
        "turn_id": payload["turn_id"], "action_ids": [requested.action_id],
    })
    return result


@pytest.mark.parametrize("policy", ["current", "thin"])
@pytest.mark.parametrize("exit_code,expected", [(0, "PASS"), (1, "FAIL"), (2, "ERROR")])
def test_selected_tests_never_grant_required_check_credit(
    gateway_factory, policy, exit_code, expected,
):
    sandbox = RecordingSandbox(exit_code=exit_code, **({
        "stdout": "", "stderr": "ERROR: selected fixture dependency unavailable",
    } if exit_code == 2 else {}))
    gateway = enable(restart(gateway_factory(sandbox=sandbox)[0], policy))
    selected = call(policy, "run_tests", "selected", {
        "suite_id": "public-pytest", "targets": [TARGET],
    })
    result, = gateway.execute_batch([selected])
    assert result.status == "succeeded"
    assert result.output["test_status"] == expected
    assert result.output["passed"] == (exit_code == 0)
    if exit_code == 2:
        assert "dependency unavailable" in result.output["stderr"]
    assert result.output["counts_toward_completion"] is False
    assert gateway.remaining_visible_check_ids() == ["existing-unit-tests"]
    assert not gateway.visible_checks_pass()
    assert not gateway.ready_to_submit()
    assert sandbox.calls[0][1].command[-2:] == ["--", TARGET]
    assert recent_tests(gateway.journal.events(), gateway.current_diff_hash)[0][
        "evidence_currency"
    ] == "current"
    restarted = restart(gateway, policy)
    assert restarted.execute(selected).replayed
    assert len(sandbox.calls) == 1
    restarted.execute_batch([call(policy)])
    assert restarted.execute(mutation(policy)).status == "succeeded"
    assert recent_tests(restarted.journal.events(), restarted.current_diff_hash)[0][
        "evidence_currency"
    ] == "historical"
    assert not restarted.visible_checks_pass()
    assert not restarted.ready_to_submit()
    observations = restarted.verification_concerns()["observations"]["items"]
    assert len(observations) == int(exit_code != 0)
    if observations:
        assert observations[0]["origin"] == "selected_public_tests"
        assert observations[0]["currency"] == "historical"


@pytest.mark.parametrize("policy", ["current", "thin"])
@pytest.mark.parametrize("source,expected_status,diagnostic", [
    ("print('PUBLIC_PROBE_PASS')", "passed", ""),
    ("assert False, 'PUBLIC_ASSERTION'", "failed", "AssertionError: PUBLIC_ASSERTION"),
    ("import patchloop_missing_public_probe_dependency_xyz", "failed", "ModuleNotFoundError:"),
], ids=["pass", "assertion", "setup-import"])
def test_probe_receipt_preserves_outcome_currency_and_no_completion_credit(
    gateway_factory, smoke_package, policy, source, expected_status, diagnostic,
):
    gateway = restart(gateway_factory()[0], policy)
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    requested = call(policy, "run_probe", "probe", {
        "question": "What does this trusted public diagnostic execute?",
        "python_source": source, "replay_action_id": None,
    })
    result, = gateway.execute_batch([requested])
    assert result.status == "succeeded", result.message
    assert result.output["status"] == expected_status
    assert result.output["exit_code"] == int(expected_status != "passed")
    assert result.workspace_diff_hash == result.output["diff_hash"] == gateway.current_diff_hash
    assert backend.sources == [source]
    if diagnostic:
        assert diagnostic in result.output["stderr"]
    else:
        assert result.output["stdout"].strip() == "PUBLIC_PROBE_PASS"
    observation = probe_observation(result.model_dump(mode="json"))
    assert observation["behavior_verdict"] == "not_assessed"
    assert observation["execution_status"] == (
        "completed" if expected_status == "passed" else "failed"
    )
    if diagnostic.startswith("ModuleNotFoundError"):
        assert observation["environment_guidance"]["basis"] == "reported_import_error"
    else:
        assert "environment_guidance" not in observation
    assert gateway.checks_by_diff == {}
    assert gateway.remaining_visible_check_ids() == ["existing-unit-tests"]
    assert not gateway.ready_to_submit()
    current = probe_context(gateway, smoke_package)["recent_probes"][0]
    assert current["historical"] is False and current["diagnostic_only"] is True
    assert current["stdout"] == result.output["stdout"]
    assert current["stderr"] == result.output["stderr"]
    before = gateway.verification_concerns()["observations"]["items"]
    assert len(before) == int(expected_status != "passed")
    if before:
        assert before[0]["currency"] == "current"
    restarted = restart(gateway, policy)
    restarted.probe_sandbox = backend
    assert restarted.execute(requested).replayed
    assert backend.calls == 1
    restarted.execute_batch([call(policy)])
    assert restarted.execute(mutation(policy)).status == "succeeded"
    historical = probe_context(restarted, smoke_package)["recent_probes"][0]
    assert historical["historical"] is True and historical["diagnostic_only"] is True
    assert historical["diff_hash"] == result.workspace_diff_hash
    assert historical["stdout"] == current["stdout"]
    assert historical["stderr"] == current["stderr"]
    after = restarted.verification_concerns()["observations"]["items"]
    if after:
        assert after[0]["currency"] == "historical"
    assert not restarted.visible_checks_pass()
    assert not restarted.ready_to_submit()


@pytest.mark.parametrize("policy", ["current", "thin"])
@pytest.mark.parametrize("fail_after_repair", [False, True])
def test_automatic_required_recheck_consumes_one_action_and_no_model_call(
    tmp_path, policy, fail_after_repair,
):
    gateway = restart(_gateway(tmp_path), policy)
    gateway.sandbox = CheckSandbox(fail_after_repair=fail_after_repair)
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=["python", "-c", "pass"])
        for name in ("contract", "regression")
    ]
    completed_batch(gateway, source_call(policy))
    completed_batch(gateway, source_edit(policy, "first"))
    failed = completed_batch(gateway, call(policy, "run_check", "failed", {
        "check_id": "contract",
    }))
    assert failed.output["passed"] is False
    repaired = completed_batch(gateway, source_edit(
        policy, "repair", "editable = 1", "editable = 2",
    ))
    counters = runner._restore_counters(gateway.journal)
    before_calls, before_actions = counters.model_calls, counters.tool_actions
    assert (before_calls, before_actions) == (4, 4)
    assert runner._run_repair_recheck(
        journal=gateway.journal, gateway=gateway, latest_results=[repaired],
        counters=counters, active_elapsed_ms=lambda: 50,
    ) == (None, None)
    assert counters.model_calls == before_calls
    assert counters.tool_actions == before_actions + 1
    assert runner._restore_counters(gateway.journal) == counters
    assert [name for name, _ in gateway.sandbox.calls] == ["contract", "contract"]
    assert [row["status"] for row in gateway.visible_check_status()] == [
        "FAIL" if fail_after_repair else "PASS", "NOT_RUN",
    ]
    assert not gateway.ready_to_submit()
    child = next(event["payload"] for event in gateway.journal.events()
                 if event["event_type"] == "repair_recheck_finished")
    native_actions = {item["action_id"] for event in gateway.journal.events()
                      if event["event_type"] == "turn_decision_recorded"
                      for item in event["payload"]["tool_calls"]}
    assert child["action_id"] not in native_actions
    assert child["parent_action_id"] == "repair"
    assert child["previous_check_action_id"] == "failed"
    before_journal = gateway.journal.path.read_bytes()
    restarted = restart(gateway, policy)
    assert runner._run_repair_recheck(
        journal=restarted.journal, gateway=restarted, latest_results=[repaired],
        counters=runner._restore_counters(restarted.journal), active_elapsed_ms=lambda: 60,
    ) == (None, None)
    assert gateway.journal.path.read_bytes() == before_journal
    assert len(gateway.sandbox.calls) == 2


@pytest.mark.parametrize("policy", ["current", "thin"])
def test_source_citations_and_failure_concerns_keep_currency_across_edit(tmp_path, policy):
    gateway = restart(_gateway(tmp_path), policy)
    gateway.sandbox = CheckSandbox()
    gateway.public_task.visible_checks = [
        RegisteredCheck(id="contract", command=["python", "-c", "pass"]),
    ]
    gateway.execute_batch([source_call(policy, end_line=49)])
    note = {
        "findings": [{"note_id": None, "statement": "The editable value is zero.",
                      "evidence": [{"kind": "source", "path": "src.py",
                                    "start_line": 50, "end_line": 50}]}],
        "remove_note_ids": [], "open_question": None, "verification_updates": [],
    }
    premature = source_call(policy, "not-yet-observed", update=note)
    rejected = gateway.record_working_notes_update([premature], turn_id="before-evidence")
    assert rejected["receipt"]["findings"][0]["status"] == "rejected"
    assert gateway.working_notes()["findings"] == []
    assert gateway.execute_batch([premature])[0].status == "succeeded"
    failed = gateway.execute(call(policy, "run_check", "failed", {"check_id": "contract"}))
    assert failed.output["passed"] is False
    note["verification_updates"] = [concern(
        statement="Investigate the observed public check failure.", evidence="failed",
    )]
    annotated = source_call(policy, "retain-evidence", update=note)
    receipt = gateway.record_working_notes_update([annotated], turn_id="observed-evidence")
    assert receipt["allocated_note_ids"] == ["n1"]
    assert gateway.execute_batch([annotated])[0].status == "succeeded"
    before = gateway.working_notes()
    assert before["findings"][0]["status"] == "current"
    assert before["verification"]["unresolved_ids"] == ["v1"]
    assert before["verification"]["items"][0]["observation"]["currency"] == "current"
    assert gateway.execute(source_edit(policy, "change-cited-source")).status == "succeeded"
    after = gateway.working_notes()
    assert after["findings"] == []
    assert after["verification"]["unresolved_ids"] == ["v1"]
    assert after["verification"]["items"][0]["observation"]["currency"] == "historical"
    passed = gateway.execute(call(policy, "run_check", "passed", {"check_id": "contract"}))
    assert passed.output["passed"] is True
    assert gateway.verification_concerns()["unresolved_ids"] == ["v1"]
    assert gateway.ready_to_submit()
    restarted = restart(gateway, policy)
    assert restarted.working_notes() == gateway.working_notes()
    finish = call(policy, "finish_task", "finish")
    finish.arguments = {}
    assert restarted.execute_batch([finish])[0].status == "succeeded"
