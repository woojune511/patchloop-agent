from __future__ import annotations

import json
import subprocess

import pytest
from test_dev_resume_v12 import SimulatedCrash, _mutation, _read, _request, _restart

import patchloop.dev.runner as runner
import patchloop.git_execution as git_execution
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.evaluation_completion import EvaluationCompletion
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.git_execution import GitExecutionUncertain, run_git
from patchloop.repository import WorkspaceManager


def test_git_capture_preserves_bytes_and_has_no_reader_pipe(tmp_path, monkeypatch):
    launches = []
    waits = []

    class Process:
        returncode = 0

        def wait(self, *, timeout):
            waits.append(timeout)

    def spawn(command, **kwargs):
        launches.append(command)
        assert "shell" not in kwargs
        assert kwargs["stdin"].read() == b"input\r\n"
        assert kwargs["stdout"] != subprocess.PIPE
        assert kwargs["stderr"] != subprocess.PIPE
        kwargs["stdout"].write(b"raw\r\n" + b"x" * 100_000)
        kwargs["stderr"].write(b"error\r\n")
        return Process()

    monkeypatch.setattr(git_execution.subprocess, "Popen", spawn)
    deadline = ExecutionDeadline.from_remaining(8, clock=lambda: 0)
    result = run_git(tmp_path, "show", text=False, input=b"input\r\n", deadline=deadline)
    assert result.stdout == b"raw\r\n" + b"x" * 100_000
    assert result.stderr == b"error\r\n"
    assert launches == [["git", "show"]]
    assert waits == [pytest.approx(7.2)]


def test_expired_git_does_not_launch(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("expired Git must not launch")

    monkeypatch.setattr(git_execution.subprocess, "Popen", forbidden)
    with pytest.raises(ExecutionDeadlineExceeded):
        run_git(tmp_path, "status", deadline=ExecutionDeadline.from_remaining(0))


@pytest.mark.parametrize("cause", ["timeout", "os_error", "interrupt"])
@pytest.mark.parametrize("cleanup_fails", [False, True])
@pytest.mark.parametrize("remaining", [30, 300])
def test_git_interruption_is_bounded_uncertainty(
    tmp_path, monkeypatch, cause, cleanup_fails, remaining,
):
    launches = []
    waits = []
    kills = []

    class Process:
        returncode = 0

        def wait(self, *, timeout):
            waits.append(timeout)
            if len(waits) == 1:
                if cause == "timeout":
                    raise subprocess.TimeoutExpired("git", timeout)
                if cause == "os_error":
                    raise OSError("synthetic wait failure")
                raise KeyboardInterrupt()
            if cleanup_fails:
                raise subprocess.TimeoutExpired("git", timeout)

        def kill(self):
            kills.append(True)

    def spawn(*args, **kwargs):
        launches.append(args)
        return Process()

    monkeypatch.setattr(git_execution.subprocess, "Popen", spawn)
    with pytest.raises(GitExecutionUncertain) as captured:
        run_git(tmp_path, "show", deadline=ExecutionDeadline.from_remaining(
            remaining, clock=lambda: 0,
        ))
    assert len(launches) == len(kills) == 1
    assert waits == [min(120, remaining - 1), 1]
    assert captured.value.details["direct_process_reaped"] is not cleanup_fails
    assert captured.value.details["descendant_cleanup"] == "unknown"
    assert captured.value.details["deadline_exhausted"] is (cause == "timeout" and remaining < 120)


def test_workspace_creation_spends_active_row_time(tmp_path, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(runner, "monotonic", lambda: clock[0])
    original = WorkspaceManager.create

    def create(self, *args, **kwargs):
        assert kwargs["deadline"] is not None
        result = original(self, *args, **kwargs)
        clock[0] = 1_800
        return result

    monkeypatch.setattr(WorkspaceManager, "create", create)
    result = runner.run_dev(_request(tmp_path))["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED"
    assert result["call_counts"]["model"] == 0
    terminal = DevJournal(tmp_path, result["run_id"]).terminal()["payload"]
    assert terminal["active_elapsed_ms"] == 1_800_000


@pytest.mark.parametrize("uncertain", [False, True])
def test_context_preparation_ends_durably_without_dispatch(tmp_path, monkeypatch, uncertain):
    def projection(*args, **kwargs):
        if uncertain:
            raise GitExecutionUncertain("synthetic Git uncertainty")
        raise ExecutionDeadlineExceeded("synthetic context deadline")

    monkeypatch.setattr(DevToolGateway, "prepare_context_projection", projection)
    results = runner.run_dev(_request(tmp_path).model_copy(update={"repeat": 2}))["runs"]
    assert len(results) == (1 if uncertain else 2)
    assert all(r["call_counts"]["model"] == 0 for r in results)
    assert all(r["terminal"] == ("TASK_FAILED" if uncertain else "LIMIT_REACHED") for r in results)


@pytest.mark.parametrize("deadline_limited", [False, True])
def test_evaluator_git_uncertainty_keeps_compatible_completion_and_provenance(
    tmp_path, monkeypatch, deadline_limited,
):
    original = WorkspaceManager.create

    def create(self, run_id, *args, **kwargs):
        if run_id.startswith("eval_"):
            raise GitExecutionUncertain("synthetic evaluator Git uncertainty", details={
                "deadline_exhausted": deadline_limited,
                "direct_process_reaped": True, "descendant_cleanup": "unknown",
            })
        return original(self, run_id, *args, **kwargs)

    monkeypatch.setattr(WorkspaceManager, "create", create)
    request = _request(tmp_path).model_copy(update={"repeat": 2})
    results = runner.run_dev(request)["runs"]
    assert len(results) == 1
    result = results[0]
    assert result["terminal"] == ("LIMIT_REACHED" if deadline_limited else "EVALUATOR_ERROR")
    assert result["evaluator"]["failure_class"] == (
        "ACTIVE_DEADLINE_EXHAUSTED" if deadline_limited else "EVALUATOR_INFRA_FAILURE"
    )
    journal = DevJournal(tmp_path, result["run_id"])
    completion = EvaluationCompletion.model_validate(next(
        e["payload"] for e in journal.events() if e["event_type"] == "evaluator_finished"
    ))
    assert completion.stop_remaining is True
    root = tmp_path / "artifacts/runs" / result["run_id"]
    assert (root / "manifest.json").is_file()
    assert (root / "terminal-provenance.json").is_file()
    provenance = json.loads((root / "provenance.json").read_text())
    assert provenance["failure_class"] == "GitExecutionUncertain"
    assert provenance["deadline_exhausted"] is deadline_limited
    assert provenance["completed_check_results"] == []
    before = journal.path.read_bytes()
    resumed = request.model_copy(update={"repeat": 1, "resume_run_id": result["run_id"]})
    # Repeat belongs to the invocation, not the per-row exact resume contract.
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("scope_failure", [False, True])
def test_expired_pending_mutation_reconciles_without_reapplying(
    gateway_factory, monkeypatch, scope_failure,
):
    # Keep the active row expired below; this tests reconciliation/rollback, not
    # whether concurrent Windows Git metadata reads finish within five seconds.
    monkeypatch.setattr(DevToolGateway, "_recovery_read_deadline", staticmethod(
        lambda: ExecutionDeadline.from_remaining(60)))
    gateway, journal, workspace = gateway_factory()
    if scope_failure:
        gateway.public_task = gateway.public_task.model_copy(update={
            "constraints": gateway.public_task.constraints.model_copy(update={"max_diff_lines": 1}),
        })
    _read(gateway, "mini_data_utils/csvlite.py")
    baseline = (workspace / "mini_data_utils/csvlite.py").read_bytes()
    original = WorkspaceManager.atomic_replace_source
    writes = []

    def crash_once(*args):
        original(*args)
        writes.append(True)
        if len(writes) == 1:
            raise SimulatedCrash()

    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(crash_once))
    with pytest.raises(SimulatedCrash):
        gateway.execute(_mutation())
    resumed = _restart(gateway, journal)
    resumed.deadline = ExecutionDeadline.from_remaining(0)
    result = resumed.execute(_mutation())
    assert result.status == ("failed" if scope_failure else "succeeded")
    assert len(writes) == (2 if scope_failure else 1)
    if scope_failure:
        assert (workspace / "mini_data_utils/csvlite.py").read_bytes() == baseline
        assert result.output["mutation_failure"]["rolled_back"] is True
