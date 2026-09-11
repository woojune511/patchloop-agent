"""Opt-in repair/check feedback: real gateway actions, no fabricated native calls."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from native_history_support import input_context
from test_dev_completion_v27 import _batch, _check
from test_dev_feedback_integration_v18 import _input
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart
from test_dev_resume_v12 import SimulatedCrash, _request

import patchloop.dev.runner as runner
from patchloop.contracts import RegisteredCheck
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.repair_recheck import select_repair_recheck
from patchloop.dev.state import DevJournal
from patchloop.errors import ResumeContractMismatch
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import SandboxResult


class CheckSandbox:
    backend = "local"
    supports_execution_deadline = True

    def __init__(self, *, fail_after_repair=False, cleanup_failed=False, expired=False):
        self.calls = []
        self.fail_after_repair = fail_after_repair
        self.cleanup_failed = cleanup_failed
        self.expired = expired

    def run_check(self, workspace, check, **kwargs):
        self.calls.append((check.id, kwargs))
        first = len(self.calls) == 1
        failed = first or self.fail_after_repair
        return SandboxResult(
            command=check.command, exit_code=int(failed), stdout="PUBLIC_CHECK_RESULT",
            stderr=("TypeError: public bytes mismatch\n" if first else
                    "AssertionError: public mode mismatch\n" if failed else ""),
            duration_ms=1, timed_out=False, truncated=False, original_output_bytes=70,
            cleanup_failed=self.cleanup_failed and not first,
            deadline_exhausted=self.expired and not first,
        )

    @property
    def public_calls(self):
        return [row for row in self.calls if not row[1].get("execution_identity", {}).get(
            "action_id", "",
        ).startswith("evaluator:")]


def _repaired(tmp_path, **kwargs):
    gateway = _gateway(tmp_path)
    gateway.sandbox = CheckSandbox(**kwargs)
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=["python", "-c", "pass"])
        for name in ("contract", "regression")
    ]
    _read(gateway)
    _batch(gateway, _mutation("first"), tmp_path)
    _batch(gateway, _check("contract", "failed-check"), tmp_path)
    repair = _batch(gateway, _mutation("repair", "editable = 1", "editable = 2"), tmp_path)
    return gateway, [repair]


def _drain(gateway, results, counters=None):
    counters = counters or runner._restore_counters(gateway.journal)
    return runner._run_repair_recheck(
        journal=gateway.journal, gateway=gateway, latest_results=results,
        counters=counters, active_elapsed_ms=lambda: 50,
    )


@pytest.mark.parametrize("fail_after_repair", [False, True])
def test_current_feedback_native_identity_and_restart(tmp_path, fail_after_repair):
    gateway, results = _repaired(tmp_path, fail_after_repair=fail_after_repair)
    counters = runner._restore_counters(gateway.journal)
    before = counters.model_calls
    assert _drain(gateway, results, counters) == (None, None)
    assert [name for name, _ in gateway.sandbox.calls] == ["contract", "contract"]
    assert counters.model_calls == before
    assert counters.tool_actions == 1
    assert runner._restore_counters(gateway.journal) == counters
    assert gateway.visible_check_status()[0]["status"] == (
        "FAIL" if fail_after_repair else "PASS"
    )
    assert gateway.visible_check_status()[1]["status"] == "NOT_RUN"

    def context(gw):
        return runner._build_context(
            package=SimpleNamespace(public=SimpleNamespace(
                model_dump=lambda **kw: {"task_id": "public-note-feedback"},
            )), gateway=gw, journal=gw.journal, correction=None,
            latest_tool_results=results, counters=counters, elapsed_seconds=0,
            limits=gw.limits, repair_recheck=True,
        )

    raw = context(gateway)
    items = _input(gateway, results, tmp_path, context=raw)
    view = input_context(items)
    receipt = view["repair_recheck"]["last_result"]
    assert receipt["origin"] == "harness"
    assert receipt["parent_action_id"] == "repair"
    assert receipt["previous_check_action_id"] == "failed-check"
    assert receipt["evidence_currency"] == "current"
    assert receipt["candidate_diff_hash"] == gateway.current_diff_hash
    current = next(row for row in view["recent_checks"] if row["action_id"] == receipt["action_id"])
    assert current["passed"] is not fail_after_repair
    assert "delivery" not in current  # Body is in public state, not a nonexistent native output.
    if fail_after_repair:
        assert "mode mismatch" in current["stderr"]
        assert view["current_public_failure"]["diff_hash"] == gateway.current_diff_hash
    else:
        assert view["current_public_failure"] is None
    assert all(item.get("call_id") != receipt["action_id"] for item in items)
    assert [r.action_id for r in gateway.journal.latest_tool_batch_results()] == ["repair"]
    for sentinel in ("private_spec", "hidden_test", "reference_patch", "reasoning_summary"):
        assert sentinel not in raw
    restarted = _restart(gateway)
    assert json.loads(context(restarted)) == json.loads(raw)
    before_bytes = gateway.journal.path.read_bytes()
    restarted.deadline = ExecutionDeadline(0, clock=lambda: 1)
    assert _drain(restarted, results, runner._restore_counters(gateway.journal)) == (None, None)
    assert gateway.journal.path.read_bytes() == before_bytes
    assert len(gateway.sandbox.calls) == 2


def test_selection_ignores_historical_pass_rejection_and_initial_edit(tmp_path):
    gateway, results = _repaired(tmp_path)
    select = lambda rs: select_repair_recheck(  # noqa: E731
        gateway.journal, rs, registered_checks={"contract", "regression"},
    )
    assert select(results).previous_check_action_id == "failed-check"
    # A further edit has only the earlier diff's error, not a current failure.
    next_edit = _batch(gateway, _mutation("next", "editable = 2", "editable = 3"), tmp_path)
    assert select([next_edit]) is None
    assert select([results[0].model_copy(update={"status": "failed"})]) is None
    assert select([]) is None
    initial = next(event["payload"]["result"] for event in gateway.journal.events()
                   if event["event_type"] == "action_finished"
                   and event["payload"]["result"]["action_id"] == "first")
    assert select([runner.DevToolResult.model_validate(initial)]) is None
    # A newer PASS on the same baseline replaces that check's earlier failure.
    _batch(gateway, _check("contract", "pass-now"), tmp_path)
    final = _batch(gateway, _mutation("last", "editable = 3", "editable = 4"), tmp_path)
    assert select([final]) is None


def test_budget_deadline_and_workspace_identity(tmp_path):
    gateway, results = _repaired(tmp_path)
    counters = runner._restore_counters(gateway.journal)
    counters.tool_actions = gateway.limits.max_tool_actions
    assert _drain(gateway, results, counters)[0] == runner.DevTerminal.LIMIT_REACHED
    assert len(gateway.sandbox.calls) == 1
    counters.tool_actions -= 1
    clock = [0.0]
    gateway.deadline = ExecutionDeadline(1, clock=lambda: clock[0])
    clock[0] = 2.0
    with pytest.raises(ExecutionDeadlineExceeded):
        _drain(gateway, results, counters)
    assert len(gateway.sandbox.calls) == 1
    gateway.deadline = None
    WorkspaceManager.atomic_replace_source(gateway.workspace, "src.py", b"external drift\n")
    with pytest.raises(ResumeContractMismatch):
        _drain(gateway, results, counters)
    assert len(gateway.sandbox.calls) == 1


def test_latest_still_failed_check_not_declaration_order(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.sandbox = CheckSandbox(fail_after_repair=True)
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=["python", "-c", "pass"])
        for name in ("first-declared", "last-declared")
    ]
    _read(gateway)
    _batch(gateway, _mutation("first"), tmp_path)
    _batch(gateway, _check("last-declared", "older-failure"), tmp_path)
    _batch(gateway, _check("first-declared", "latest-failure"), tmp_path)
    repair = _batch(gateway, _mutation("repair", "editable = 1", "editable = 2"), tmp_path)
    assert _drain(gateway, [repair]) == (None, None)
    assert gateway.sandbox.calls[-1][0] == "first-declared"
    receipt = next(e["payload"] for e in gateway.journal.events()
                   if e["event_type"] == "repair_recheck_finished")
    assert receipt["previous_check_action_id"] == "latest-failure"


def _script(monkeypatch, *, fail_after_repair=False, cleanup_failed=False, expired=False):
    contexts = []
    sandbox = CheckSandbox(
        fail_after_repair=fail_after_repair, cleanup_failed=cleanup_failed, expired=expired,
    )

    class Adapter(MockDevAdapter):
        def next_turn(self, context, tools):
            state = json.loads(context)
            contexts.append(state)
            failure = state.get("current_public_failure")
            if failure and failure["evidence_currency"] == "current":
                if "# repair-recheck" in state["current_diff"]["patch"]:
                    turn = DevModelTurn(tool_calls=[RequestedTool(
                        name="stop_task", action_id="stop", arguments={
                            "reason_code": "no_safe_scoped_mutation", "summary": "Mock limit.",
                        }, turn_decision=PublicTurnDecision(mode="stop", basis="Mock boundary."),
                    )])
                else:
                    turn = DevModelTurn(tool_calls=[RequestedTool(
                        name="replace_text", action_id="repair", arguments={
                            "path": self.mutation.path, "old_text": "import csv",
                            "new_text": "import csv  # repair-recheck", "occurrence": 1,
                            "hypothesis": "Synthetic repair for feedback ordering.",
                            "expected_behavior": "Observe the mocked check on the new diff.",
                        }, turn_decision=PublicTurnDecision(mode="mutate", basis="Mock repair."),
                    )])
            else:
                turn = super().next_turn(context, tools)
            for index, call in enumerate(turn.tool_calls):
                call.action_id = f"model-{len(contexts)}-{index}"
            return turn

    monkeypatch.setattr(runner, "MockDevAdapter", Adapter)
    monkeypatch.setattr(runner, "LocalSandbox", lambda: sandbox)
    return contexts, sandbox


@pytest.mark.parametrize("enabled", [False, True])
def test_opt_in_end_to_end_default_unchanged(tmp_path, monkeypatch, enabled):
    contexts, sandbox = _script(monkeypatch)
    request = _request(tmp_path).model_copy(update={"repair_recheck": enabled})
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["accepted_mutations"] == 2
    assert result["call_counts"] == {"model": 5 if enabled else 6, "tool": 7, "input_count": 0}
    assert len(sandbox.public_calls) == 2
    journal = DevJournal(tmp_path, result["run_id"])
    assert journal.load_envelope().repair_recheck is enabled
    assert any(e["event_type"] == "repair_recheck_finished" for e in journal.events()) is enabled
    if enabled:
        assert contexts[-1]["repair_recheck"]["last_result"]["passed"] is True
        assert contexts[-1]["remaining_budget"]["tool_actions"] == 94
    else:
        assert all("repair_recheck" not in row for row in contexts)
    before = journal.path.read_bytes()
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"]}))
    assert resumed["runs"][0] == result
    assert journal.path.read_bytes() == before
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={
            "resume_run_id": result["run_id"], "repair_recheck": not enabled,
        }))
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("boundary", [
    "mutation_applied", "batch_finished", "child_started", "child_admitted",
    "child_result", "child_finished",
])
def test_crash_resume_preserves_order_and_counts(tmp_path, monkeypatch, boundary):
    contexts, sandbox = _script(monkeypatch)
    request = _request(tmp_path).model_copy(update={"repair_recheck": True})
    original_append = DevJournal.append
    original_replace = WorkspaceManager.atomic_replace_source
    crashed = False

    def crash():
        nonlocal crashed
        if not crashed:
            crashed = True
            raise SimulatedCrash()

    def append(self, kind, payload=None):
        event = original_append(self, kind, payload)
        child = str((payload or {}).get("action_id", "")).startswith("harness_recheck_")
        if (boundary == "batch_finished" and kind == "tool_batch_finished"
                and payload["action_ids"] == ["model-4-0"]):
            crash()
        if boundary == "child_started" and kind == "repair_recheck_started":
            crash()
        if boundary == "child_admitted" and kind == "action_started" and child:
            crash()
        if (boundary == "child_result" and kind == "action_finished"
                and payload["result"]["action_id"].startswith("harness_recheck_")):
            crash()
        if boundary == "child_finished" and kind == "repair_recheck_finished":
            crash()
        return event

    def replace(workspace, path, content):
        original_replace(workspace, path, content)
        if boundary == "mutation_applied" and b"# repair-recheck" in content:
            crash()

    monkeypatch.setattr(DevJournal, "append", append)
    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(replace))
    with pytest.raises(SimulatedCrash):
        runner.run_dev(request)
    assert len(contexts) == 4
    run_id = next((tmp_path / "runs").glob("*.jsonl")).stem
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["call_counts"] == {"model": 5, "input_count": 0, "tool": 7}
    assert result["accepted_mutations"] == 2
    assert len(contexts) == 5 and len(sandbox.public_calls) == 2
    events = DevJournal(tmp_path, run_id).events()
    assert sum(e["event_type"] == "repair_recheck_started" for e in events) == 1
    assert sum(e["event_type"] == "repair_recheck_finished" for e in events) == 1
    assert sum(e["event_type"] == "action_started" and e["payload"]["tool"] == "replace_text"
               for e in events) == 2


@pytest.mark.parametrize("kind,terminal", [
    ("fail_after_repair", "AGENT_STOPPED"), ("cleanup_failed", "TASK_FAILED"),
    ("expired", "LIMIT_REACHED"),
])
def test_failure_feedback_or_uncertainty_stops_before_another_decision(
    tmp_path, monkeypatch, kind, terminal,
):
    contexts, sandbox = _script(monkeypatch, **{kind: True})
    result = runner.run_dev(_request(tmp_path).model_copy(update={"repair_recheck": True}))
    assert result["runs"][0]["terminal"] == terminal
    assert len(sandbox.public_calls) == 2
    assert len(contexts) == (5 if kind == "fail_after_repair" else 4)
    if kind == "fail_after_repair":
        assert "mode mismatch" in contexts[-1]["recent_checks"][-1]["stderr"]


def test_last_mutation_is_rechecked_before_horizon_stop(tmp_path, monkeypatch):
    contexts, sandbox = _script(monkeypatch, fail_after_repair=True)
    request = _request(tmp_path)
    request.repair_recheck = True
    request.limits.max_accepted_mutations = 2
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED"
    assert len(contexts) == 4 and len(sandbox.public_calls) == 2
    assert result["call_counts"] == {"model": 4, "input_count": 0, "tool": 6}
    assert result["completion_horizon"]["blocking_resources"] == ["accepted_mutations"]
    events = DevJournal(tmp_path, result["run_id"]).events()
    assert any(e["event_type"] == "repair_recheck_finished" for e in events)


def test_unknown_provider_dispatch_precedes_pending_recheck(tmp_path, monkeypatch):
    contexts, sandbox = _script(monkeypatch)
    original = DevJournal.append

    def crash(self, kind, payload=None):
        if kind == "repair_recheck_started":
            raise SimulatedCrash()
        return original(self, kind, payload)

    monkeypatch.setattr(DevJournal, "append", crash)
    request = _request(tmp_path).model_copy(update={"repair_recheck": True})
    with pytest.raises(SimulatedCrash):
        runner.run_dev(request)
    run_id = next((tmp_path / "runs").glob("*.jsonl")).stem
    journal = DevJournal(tmp_path, run_id)
    journal.append("provider_call_started", {"call_id": "uncertain", "turn_id": "uncertain"})
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert len(contexts) == 4 and len(sandbox.public_calls) == 1
    assert not any(e["event_type"] == "repair_recheck_started" for e in journal.events())
