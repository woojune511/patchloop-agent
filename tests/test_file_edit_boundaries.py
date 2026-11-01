"""Expired admission is not execution authority; uncertain file state stops repetitions."""

import pytest
from test_file_edits import (
    CREATED,
    SOURCE,
    Crash,
    batch,
    edit,
    expanded_gateway,
    restart,
    source_read,
)

from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import file_edits, file_transaction, runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root


def test_expired_transaction_does_not_write_after_preview(gateway_factory, monkeypatch):
    _, _, workspace = gateway_factory()
    before = (workspace / SOURCE).read_bytes()
    changes = [file_transaction.FileChange(SOURCE, before, before + b"\n# change\n")]

    def forbidden(*args):
        pytest.fail("an expired transaction must not write any source")

    monkeypatch.setattr(file_transaction, "_write_one", forbidden)
    with pytest.raises(ExecutionDeadlineExceeded):
        file_transaction.apply_changes(
            workspace, changes, deadline=ExecutionDeadline.from_remaining(0))
    assert (workspace / SOURCE).read_bytes() == before


@pytest.mark.parametrize("boundary", ["admission", "mixed"])
def test_expired_admission_cannot_start_but_partial_execution_can_reconcile(
    gateway_factory, monkeypatch, boundary,
):
    # Exercise active-deadline authority rather than concurrent Windows metadata latency.
    monkeypatch.setattr(DevToolGateway, "_recovery_read_deadline", staticmethod(
        lambda: ExecutionDeadline.from_remaining(60)))
    gateway, journal, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    assert gateway.execute(source_read()).status == "succeeded"
    call = batch("deadline-file-batch")
    append, write = DevJournal.append, file_transaction._write_one
    writes = []

    def crash_admission(self, event_type, payload=None):
        value = append(self, event_type, payload)
        if event_type == "action_started" and payload.get("action_id") == call.action_id:
            raise Crash
        return value

    def crash_after_first(folder, change, content):
        write(folder, change, content)
        writes.append(change.path)
        if len(writes) == 1:
            raise Crash

    with monkeypatch.context() as scoped:
        if boundary == "admission":
            scoped.setattr(DevJournal, "append", crash_admission)
        else:
            scoped.setattr(file_transaction, "_write_one", crash_after_first)
        with pytest.raises(Crash):
            gateway.execute(call)
    resumed = restart(gateway)
    resumed.deadline = ExecutionDeadline.from_remaining(0)
    if boundary == "admission":
        with pytest.raises(ExecutionDeadlineExceeded):
            resumed.execute(call)
        assert (workspace / SOURCE).read_bytes() == before
        assert not (workspace / CREATED).exists()
        assert WorkspaceManager.diff_summary(workspace).patch == ""
        assert resumed.accepted_mutations == 0
        assert not any(e["event_type"] == "action_finished"
                       and e["payload"].get("action_id") == call.action_id
                       for e in journal.events())
    else:
        result = resumed.execute(call)
        assert result.status == "succeeded", result.message
        assert result.output["recovered_after_crash"] is True
        assert (workspace / SOURCE).read_bytes() == before.replace(b"physical_line", b"record_line")
        assert (workspace / CREATED).read_bytes() == b"VALUE = 1\n"
        assert resumed.accepted_mutations == 1
        assert writes == [CREATED]
        assert WorkspaceManager.diff_summary(workspace).untracked_files == []


def test_uncertain_file_transaction_stops_repetitions_with_admission_pending(tmp_path, monkeypatch):
    calls = []

    class FileMock(MockDevAdapter):
        def _next_action(self, context, tools):
            turn = super()._next_action(context, tools)
            for index, call in enumerate(turn.tool_calls):
                if call.name == "replace_text":
                    turn.tool_calls[index] = batch("uncertain-file-batch", [edit(
                        SOURCE, self.mutation.old_text, self.mutation.new_text)])
            return turn

    def uncertain(gateway, arguments, start, **kwargs):
        assert start["mutation_admitted"] and start["file_transaction"]
        calls.append(start["action_id"])
        raise file_transaction.FileTransactionUncertain(
            "synthetic unconfirmed file rollback", details={"file_transaction_uncertain": True})

    monkeypatch.setattr(runner, "MockDevAdapter", FileMock)
    monkeypatch.setattr(file_edits, "apply", uncertain)
    result = runner.run_dev(DevRunRequest(
        provider="mock", model="mock-dev", repeat=2, state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
    ))
    assert calls == ["uncertain-file-batch"]
    assert result["stop_remaining"] is True
    assert len(result["runs"]) == 1
    run = result["runs"][0]
    assert run["terminal"] == "TASK_FAILED" and run["accepted_mutations"] == 0
    events = DevJournal(tmp_path, run["run_id"]).events()
    assert any(e["event_type"] == "action_started"
               and e["payload"].get("action_id") == calls[0] for e in events)
    assert not any(e["event_type"] == "action_finished"
                   and e["payload"].get("action_id") == calls[0] for e in events)


def test_result_failure_restores_batch_with_bounded_rollback(gateway_factory, monkeypatch):
    gateway, _, workspace = expanded_gateway(gateway_factory)
    before = (workspace / SOURCE).read_bytes()
    assert gateway.execute(source_read()).status == "succeeded"
    reconcile = file_transaction.reconcile_changes
    rollback_deadlines = []

    def fail_result(*args, **kwargs):
        assert (workspace / CREATED).read_bytes() == b"VALUE = 1\n"
        assert (workspace / SOURCE).read_bytes() != before
        raise OSError("post-write evidence unavailable")

    def capture_rollback(folder, changes, **kwargs):
        if any(change.path == CREATED and change.after is None for change in changes):
            rollback_deadlines.append(kwargs.get("deadline"))
        return reconcile(folder, changes, **kwargs)

    monkeypatch.setattr(file_edits, "result", fail_result)
    monkeypatch.setattr(file_transaction, "reconcile_changes", capture_rollback)
    result = gateway.execute(batch("failed-result"))
    assert result.status == "failed"
    assert gateway.accepted_mutations == 0
    assert (workspace / SOURCE).read_bytes() == before
    assert not (workspace / CREATED).exists()
    assert WorkspaceManager.diff_summary(workspace).patch == ""
    assert WorkspaceManager.untracked_files(workspace) == []
    assert len(rollback_deadlines) == 1
    assert isinstance(rollback_deadlines[0], ExecutionDeadline)
    assert 0 < rollback_deadlines[0].remaining_seconds() <= 5
