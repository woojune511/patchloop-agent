"""A run-added test can move without undoing the repaired implementation."""

import pytest
from test_additive_test_policy import BASE, source
from test_file_edits import (
    SOURCE,
    TEST,
    Crash,
    batch,
    edit,
    expanded_gateway,
    restart,
    source_read,
)

from patchloop.contracts import TaskConstraints
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import file_edits, file_transaction
from patchloop.dev.contracts import RequestedTool
from patchloop.errors import ActionConflict, ContractError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.test_additions import UnsupportedTestChange
from patchloop.verifier.policy import validate_test_addition

NEW_TEST = "tests/test_moved.py"
ADDITION = "\n\ndef test_run_added():\n    assert 2 == 2\n"


@pytest.fixture
def added_gateway(gateway_factory):
    gateway, journal, workspace = expanded_gateway(gateway_factory)
    gateway.public_task.constraints.allowed_paths = ["mini_data_utils/**", "tests/**"]
    gateway.public_task.constraints.forbidden_paths = []
    gateway.public_task.constraints.additive_test_roots = ["tests"]
    original = (workspace / TEST).read_bytes()
    assert gateway.execute(source_read()).status == "succeeded"
    assert gateway.execute(source_read(TEST, "read-original-test")).status == "succeeded"
    initial = batch("add-test", [
        edit(SOURCE, "physical_line", "record_line", "all"),
        edit(TEST, original.decode(), original.decode() + ADDITION),
    ])
    result = gateway.execute(initial)
    assert result.status == "succeeded", result.message
    assert gateway.execute(source_read(TEST, "read-added-test")).status == "succeeded"
    return gateway, journal, workspace, original


def move():
    return batch("move-test", [edit(TEST, ADDITION, ""), edit(NEW_TEST, None, ADDITION)])


@pytest.mark.parametrize("tool", ["replace_text", "edit_files"])
def test_exact_restore_preserves_source_and_replays_once(added_gateway, tool):
    gateway, journal, workspace, original = added_gateway
    source_bytes = (workspace / SOURCE).read_bytes()
    call = batch("restore-test", [edit(TEST, ADDITION, "")])
    if tool == "replace_text":
        call = RequestedTool(name=tool, action_id="restore-test", arguments={
            **edit(TEST, ADDITION, ""), "hypothesis": "Restore the original test file.",
            "expected_behavior": "Keep the source repair and every original test.",
        })
    result = gateway.execute(call)
    assert result.status == "succeeded", result.message
    assert (workspace / TEST).read_bytes() == original
    assert (workspace / SOURCE).read_bytes() == source_bytes
    assert gateway.current_diff.changed_files == [SOURCE]
    assert gateway.accepted_mutations == 2
    before_replay = journal.path.read_bytes()
    resumed = restart(gateway)
    replay = resumed.execute(call)
    assert replay.replayed and replay.output == result.output
    assert resumed.accepted_mutations == 2 and journal.path.read_bytes() == before_replay
    conflicting = call.model_copy(update={
        "arguments": {**call.arguments, "hypothesis": "Changed request with the same action ID."},
    })
    with pytest.raises(ActionConflict):
        resumed.execute(conflicting)
    assert journal.path.read_bytes() == before_replay
    assert (workspace / TEST).read_bytes() == original


def test_move_restores_original_and_creates_selectable_test_atomically(added_gateway):
    gateway, journal, workspace, original = added_gateway
    source_bytes = (workspace / SOURCE).read_bytes()
    result = gateway.execute(move())
    assert result.status == "succeeded", result.message
    assert (workspace / TEST).read_bytes() == original
    assert (workspace / NEW_TEST).read_text(encoding="utf-8") == ADDITION
    assert (workspace / SOURCE).read_bytes() == source_bytes
    assert set(gateway.current_diff.changed_files) == {SOURCE, NEW_TEST}
    assert gateway.current_diff.untracked_files == []
    assert gateway._tracked_path(NEW_TEST)[0] == NEW_TEST
    before_replay = journal.path.read_bytes()
    assert restart(gateway).execute(move()).replayed
    assert journal.path.read_bytes() == before_replay and gateway.accepted_mutations == 2


def test_failed_move_rolls_back_restored_original_and_new_file(added_gateway, monkeypatch):
    gateway, _, workspace, _ = added_gateway
    before = (workspace / TEST).read_bytes()
    old_diff = gateway.current_diff_hash
    write = file_transaction._write_one

    def fail_new_file(folder, change, content):
        if change.path == NEW_TEST and content is not None:
            raise OSError("new test file write failed")
        return write(folder, change, content)

    monkeypatch.setattr(file_transaction, "_write_one", fail_new_file)
    result = gateway.execute(move())
    assert result.status == "failed"
    assert (workspace / TEST).read_bytes() == before
    assert not (workspace / NEW_TEST).exists()
    assert gateway.current_diff_hash == old_diff and gateway.accepted_mutations == 1
    assert WorkspaceManager.untracked_files(workspace) == []


def test_interrupted_move_reconciles_without_second_restoration(added_gateway, monkeypatch):
    gateway, journal, workspace, original = added_gateway
    write = file_transaction._write_one
    writes = []

    def crash_after_restoration(folder, change, content):
        write(folder, change, content)
        writes.append(change.path)
        if len(writes) == 1:
            raise Crash

    monkeypatch.setattr(file_transaction, "_write_one", crash_after_restoration)
    with pytest.raises(Crash):
        gateway.execute(move())
    assert (workspace / TEST).read_bytes() == original
    assert not (workspace / NEW_TEST).exists()
    resumed = restart(gateway)
    result = resumed.execute(move())
    assert result.status == "succeeded", result.message
    assert writes == [TEST, NEW_TEST] and resumed.accepted_mutations == 2
    assert (workspace / TEST).read_bytes() == original
    assert (workspace / NEW_TEST).read_text(encoding="utf-8") == ADDITION
    before_replay = journal.path.read_bytes()
    assert restart(resumed).execute(move()).replayed
    assert journal.path.read_bytes() == before_replay and writes == [TEST, NEW_TEST]


@pytest.mark.parametrize("candidate", ["pass\n", "", "original-plus-whitespace"])
def test_non_restoration_cannot_replace_original_tests(added_gateway, candidate):
    gateway, _, workspace, original = added_gateway
    before = (workspace / TEST).read_bytes()
    if candidate == "original-plus-whitespace":
        candidate = original.decode() + "\n"
    previous = gateway.current_diff_hash
    result = gateway.execute(batch("invalid-restore", [
        edit(TEST, before.decode(), candidate), edit(NEW_TEST, None, ADDITION),
    ]))
    assert result.status == "failed"
    assert (workspace / TEST).read_bytes() == before
    assert not (workspace / NEW_TEST).exists()
    assert gateway.current_diff_hash == previous and gateway.accepted_mutations == 1


def test_original_test_deletion_remains_forbidden(added_gateway):
    gateway, _, workspace, original = added_gateway
    with pytest.raises(ContractError, match="cannot remove an original test file"):
        file_edits._check_test(gateway, file_transaction.FileChange(TEST, original, None))
    assert (workspace / TEST).read_bytes() != original


@pytest.mark.parametrize("boundary", ["scope", "observation"])
def test_exact_restore_cannot_bypass_edit_admission(added_gateway, boundary):
    gateway, _, workspace, _ = added_gateway
    before = (workspace / TEST).read_bytes()
    if boundary == "scope":
        gateway.public_task.constraints.allowed_paths = ["mini_data_utils/**"]
    else:
        gateway.spans.clear()
    result = gateway.execute(batch("unadmitted-restore", [edit(TEST, ADDITION, "")]))
    assert result.status == "failed"
    assert (workspace / TEST).read_bytes() == before
    assert gateway.accepted_mutations == 1


@pytest.mark.parametrize("path, roots", [
    ("tests/test_api.py", ["elsewhere"]), ("tests/conftest.py", ["tests"]),
])
def test_exact_original_is_safe_even_when_additions_are_disallowed(tmp_path, path, roots):
    source(tmp_path)
    if path.endswith("conftest.py"):
        (tmp_path / path).write_bytes(BASE)
        run_git(tmp_path, "add", path)
        run_git(tmp_path, "commit", "-m", "existing fixture module")
    constraints = TaskConstraints(additive_test_roots=roots)
    validate_test_addition(tmp_path, path, BASE, constraints)
    with pytest.raises(UnsupportedTestChange):
        validate_test_addition(tmp_path, path, BASE + ADDITION.encode(), constraints)


def test_new_empty_file_is_not_an_original_restoration(tmp_path):
    source(tmp_path)
    with pytest.raises(UnsupportedTestChange, match="must add"):
        validate_test_addition(
            tmp_path, "tests/test_empty.py", b"", TaskConstraints(additive_test_roots=["tests"]))


def test_exact_restore_still_obeys_deadline(tmp_path):
    source(tmp_path)
    with pytest.raises(ExecutionDeadlineExceeded):
        validate_test_addition(
            tmp_path, "tests/test_api.py", BASE, TaskConstraints(additive_test_roots=["tests"]),
            deadline=ExecutionDeadline.from_remaining(0))
