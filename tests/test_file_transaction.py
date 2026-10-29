"""New files and multi-file repairs share exact diff, rollback and recovery identities."""

import os
from pathlib import Path

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.dev import file_transaction as transaction
from patchloop.dev.file_transaction import FileChange
from patchloop.errors import ContractError, RecoveryError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    for path, content in {"a.py": b"a = 1\r\n", "b.py": b"b = 1\n",
                          "unrelated.py": b"untouched = True\n"}.items():
        (root / "src" / path).write_bytes(content)
    for args in (("init", "-q"), ("config", "core.autocrlf", "false"), ("add", "."),
                 ("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                  "commit", "-qm", "base")):
        run_git(root, *args)
    return root


def changes():
    return [FileChange("src/a.py", b"a = 1\r\n", b"a = 2\r\n"),
            FileChange("src/새 파일[x].py", None, b"new_value = 3\n"),
            FileChange("src/b.py", b"b = 1\n", b"b = 2\n")]


def summary(workspace):
    return WorkspaceManager.diff_summary(workspace)


def test_preview_apply_and_exact_undo_preserve_canonical_full_patch(workspace, tmp_path):
    batch = changes()
    baseline = summary(workspace)
    store = ArtifactStore(tmp_path / "artifacts")
    packet = transaction.save_changes(store, batch, workspace=workspace)
    restored = transaction.load_changes(store, packet)
    index_before = (workspace / ".git/index").read_bytes()
    candidate, incremental = transaction.preview_transaction(
        workspace, restored, baseline_diff_hash=baseline.patch_hash)
    assert summary(workspace).patch_hash == baseline.patch_hash
    assert (workspace / ".git/index").read_bytes() == index_before
    assert not (workspace / batch[1].path).exists()
    assert candidate.patch == incremental
    assert set(candidate.changed_files) == {change.path for change in batch}

    transaction.apply_changes(workspace, restored)
    assert summary(workspace) == candidate
    assert all((workspace / change.path).read_bytes() == change.after for change in batch)
    assert run_git(workspace, "--literal-pathspecs", "ls-files", "--error-unmatch", "--",
                   batch[1].path).returncode == 0

    # The existing one-file tool must also preview a previously created file.
    revised = WorkspaceManager.preview_text_replacement(
        workspace, batch[1].path, b"new_value = 4\n", baseline_diff_hash=candidate.patch_hash)
    assert b"new_value = 4" in revised.patch.encode()
    assert summary(workspace) == candidate
    transaction.apply_changes(workspace, transaction.reverse_changes(restored))
    assert summary(workspace) == baseline
    assert not (workspace / batch[1].path).exists()
    assert batch[1].path not in run_git(workspace, "ls-files", "-z").stdout.split("\0")


def test_incremental_patch_excludes_prior_changes_and_reapplies_new_files(workspace, tmp_path):
    (workspace / "src/unrelated.py").write_bytes(b"untouched = False\n")
    baseline = summary(workspace)
    candidate, incremental = transaction.preview_transaction(
        workspace, changes(), baseline_diff_hash=baseline.patch_hash)
    assert "src/unrelated.py" in candidate.patch and "src/unrelated.py" not in incremental
    transaction.apply_changes(workspace, changes())
    target = tmp_path / "evaluation"
    run_git(tmp_path, "clone", "-q", "--no-hardlinks", "-c", "core.autocrlf=false",
            str(workspace), str(target))
    patch = tmp_path / "candidate.patch"
    patch.write_bytes(candidate.patch.encode("utf-8"))
    assert WorkspaceManager.apply_patch(target, patch) == candidate.patch_hash
    assert summary(target) == candidate
    assert (target / changes()[1].path).read_bytes() == changes()[1].after


def test_empty_package_file_is_included_in_candidate_and_undo(workspace):
    batch = [FileChange("src/new_package/__init__.py", None, b"")]
    baseline = summary(workspace)
    candidate = transaction.preview_changes(
        workspace, batch, baseline_diff_hash=baseline.patch_hash)
    assert candidate.changed_files == [batch[0].path]
    assert candidate.patch and candidate.diff_lines == 0
    transaction.apply_changes(workspace, batch)
    assert summary(workspace) == candidate
    transaction.apply_changes(workspace, transaction.reverse_changes(batch))
    assert summary(workspace) == baseline


def test_failure_in_second_write_restores_first_write_and_created_membership(
    workspace, monkeypatch,
):
    batch = [changes()[1], changes()[0]]
    baseline = summary(workspace)
    write = transaction._write_one
    count = 0

    def fail_once(*args):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("simulated write failure")
        return write(*args)

    monkeypatch.setattr(transaction, "_write_one", fail_once)
    with pytest.raises(OSError, match="simulated"):
        transaction.apply_changes(workspace, batch)
    assert summary(workspace) == baseline
    assert not (workspace / batch[0].path).exists()
    assert batch[0].path not in run_git(workspace, "ls-files", "-z").stdout.split("\0")


def test_crash_before_new_file_registration_is_validated_without_writes_and_reconciled(
    workspace, tmp_path, monkeypatch,
):
    batch = [changes()[1], changes()[0]]
    baseline = summary(workspace)
    store = ArtifactStore(tmp_path / "artifacts")
    packet = transaction.save_changes(store, batch, workspace=workspace)
    batch = transaction.load_changes(store, packet)
    candidate = transaction.preview_changes(
        workspace, batch, baseline_diff_hash=baseline.patch_hash)
    register = transaction._register_presence

    class Crash(BaseException):
        pass

    def crash(*args, **kwargs):
        raise Crash

    monkeypatch.setattr(transaction, "_register_presence", crash)
    with pytest.raises(Crash):
        transaction.apply_changes(workspace, batch)
    assert WorkspaceManager.untracked_files(workspace) == [batch[0].path]
    index_before = (workspace / ".git/index").read_bytes()
    files_before = [(workspace / c.path).read_bytes() for c in batch]
    transaction.validate_recovery(workspace, batch, baseline_diff_hash=baseline.patch_hash,
                                  candidate_diff_hash=candidate.patch_hash)
    assert (workspace / ".git/index").read_bytes() == index_before
    assert [(workspace / c.path).read_bytes() for c in batch] == files_before
    monkeypatch.setattr(transaction, "_register_presence", register)
    transaction.reconcile_changes(workspace, transaction.load_changes(store, packet))
    assert summary(workspace) == candidate
    transaction.reconcile_changes(workspace, batch)
    assert summary(workspace) == candidate


@pytest.mark.parametrize("drift", ["member", "other_tracked", "untracked", "candidate_hash"])
def test_recovery_rejects_unknown_drift_before_finishing_partial_batch(workspace, drift):
    batch = changes()
    baseline = summary(workspace)
    candidate = transaction.preview_changes(
        workspace, batch, baseline_diff_hash=baseline.patch_hash)
    (workspace / batch[0].path).write_bytes(batch[0].after)
    candidate_hash = candidate.patch_hash
    if drift == "member":
        (workspace / batch[2].path).write_bytes(b"unknown\n")
    elif drift == "other_tracked":
        (workspace / "src/unrelated.py").write_bytes(b"unknown\n")
    elif drift == "untracked":
        (workspace / "unrelated.py").write_bytes(b"unknown\n")
    else:
        candidate_hash = "sha256:" + "0" * 64
    with pytest.raises(RecoveryError):
        transaction.validate_recovery(workspace, batch, baseline_diff_hash=baseline.patch_hash,
                                      candidate_diff_hash=candidate_hash)
    assert not (workspace / batch[1].path).exists()
    assert (workspace / batch[0].path).read_bytes() == batch[0].after


def test_undo_requires_the_exact_current_postimages(workspace):
    batch = changes()
    transaction.apply_changes(workspace, batch)
    (workspace / batch[2].path).write_bytes(b"newer edit\n")
    with pytest.raises(RecoveryError, match="workspace changed"):
        transaction.apply_changes(workspace, transaction.reverse_changes(batch))
    assert (workspace / batch[0].path).read_bytes() == batch[0].after
    assert (workspace / batch[1].path).read_bytes() == batch[1].after


def test_reconcile_write_failure_restores_the_original_whole_batch(workspace, monkeypatch):
    batch = changes()
    baseline = summary(workspace)
    (workspace / batch[0].path).write_bytes(batch[0].after)
    write = transaction._write_one

    def fail_new_file(root, change, content):
        if change.path == batch[1].path and content is not None:
            raise OSError("new file unavailable")
        return write(root, change, content)

    monkeypatch.setattr(transaction, "_write_one", fail_new_file)
    with pytest.raises(OSError, match="new file unavailable"):
        transaction.reconcile_changes(workspace, batch)
    assert summary(workspace) == baseline
    assert not (workspace / batch[1].path).exists()


def test_unconfirmed_rollback_preserves_uncertainty_for_the_gateway(workspace, monkeypatch):
    batch = changes()
    write = transaction._write_one
    count = 0

    def fail_after_first(*args):
        nonlocal count
        count += 1
        if count > 1:
            raise OSError("storage unavailable")
        return write(*args)

    monkeypatch.setattr(transaction, "_write_one", fail_after_first)
    with pytest.raises(transaction.FileTransactionUncertain) as error:
        transaction.apply_changes(workspace, batch)
    assert error.value.code == "FILE_TRANSACTION_UNCERTAIN"
    assert error.value.details["file_transaction_uncertain"] is True
    assert (workspace / batch[0].path).read_bytes() == batch[0].after


@pytest.mark.parametrize("path", ["../escape.py", ".git/config", ".GIT/config", ".git./config",
                                  "src/file.py:stream", "C:/escape.py", "."])
def test_create_rejects_non_public_paths_before_writing(workspace, path):
    with pytest.raises(ContractError):
        transaction.apply_changes(workspace, [FileChange(path, None, b"content")])


def test_duplicate_and_parent_child_members_are_rejected(workspace):
    for batch in ([changes()[0], changes()[0]],
                  [FileChange("new", None, b"file"), FileChange("new/child", None, b"file")]):
        with pytest.raises(ContractError, match="overlap"):
            transaction.apply_changes(workspace, batch)
    assert (workspace / "src/a.py").read_bytes() == changes()[0].before


def test_unregistered_existing_file_cannot_be_edited(workspace):
    (workspace / "unregistered.py").write_bytes(b"old\n")
    with pytest.raises(ContractError, match="tracked regular"):
        transaction.preview_changes(workspace, [FileChange("unregistered.py", b"old\n", b"new\n")],
                                    baseline_diff_hash=summary(workspace).patch_hash)


def test_linked_parent_is_rejected_before_external_write(workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (workspace / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        # Directory junctions need no symlink privilege on Windows and exercise
        # the same real reparse-point boundary used by managed workspaces.
        import _winapi

        _winapi.CreateJunction(str(outside), str(workspace / "linked"))
    with pytest.raises(ContractError, match="symlink or junction"):
        transaction.apply_changes(workspace, [FileChange("linked/out.py", None, b"content")])
    assert list(outside.iterdir()) == []


def test_cas_packet_is_external_and_integrity_checked(workspace, tmp_path):
    store = ArtifactStore(tmp_path / "artifacts")
    packet = transaction.save_changes(store, changes(), workspace=workspace)
    Path(packet["changes"][0]["before"]["path"]).write_bytes(b"changed artifact")
    with pytest.raises(RecoveryError, match="integrity"):
        transaction.load_changes(store, packet)
    with pytest.raises(ContractError, match="outside"):
        transaction.save_changes(ArtifactStore(workspace / "bad-state"), changes(),
                                 workspace=workspace)
