"""Exact, recoverable file batches under the gateway's existing execution lock.

The caller persists the CAS packet in action admission before applying it. A process
crash may expose a mixture of before/after files; reconciliation accepts only those
two known images and finishes the admitted batch. It never absorbs external drift.
"""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path, PureWindowsPath

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.errors import ContractError, RecoveryError
from patchloop.git_execution import GitExecutionUncertain, run_git
from patchloop.repository import DiffSummary, WorkspaceManager, _parse_numstat
from patchloop.util import safe_relative_path, sha256_bytes


@dataclass(frozen=True)
class FileChange:
    path: str
    before: bytes | None
    after: bytes | None
    mode: int | None = None


class FileTransactionUncertain(RecoveryError):
    code = "FILE_TRANSACTION_UNCERTAIN"


def checked_target(workspace: Path, path: str) -> tuple[str, Path]:
    """Resolve a literal source path without following links or Git metadata aliases."""
    normalized = safe_relative_path(path)
    parts = Path(normalized).parts
    if (normalized == "." or PureWindowsPath(normalized).drive
            or any(":" in part or part.rstrip(" .").casefold() == ".git" for part in parts)):
        raise ContractError("file transaction path is not a public source path")
    root = Path(workspace)
    cursor = root
    for index, part in enumerate((None, *parts)):
        if part is not None:
            cursor = cursor / part
        if cursor.is_symlink() or bool(getattr(cursor, "is_junction", lambda: False)()):
            raise ContractError("file transaction path contains a symlink or junction")
        if cursor.exists() and index < len(parts) and not cursor.is_dir():
            raise ContractError("file transaction parent is not a directory")
    target = cursor.resolve()
    resolved_root = root.resolve()
    if (not target.is_relative_to(resolved_root)
            or any(part.casefold() == ".git" for part in target.relative_to(resolved_root).parts)):
        raise ContractError("file transaction path escapes public source")
    if target.exists() and not target.is_file():
        raise ContractError("file transaction target is not a regular source file")
    return normalized, target


def _normalized(workspace: Path, changes: list[FileChange]) -> list[FileChange]:
    if not changes:
        raise ContractError("file transaction requires at least one change")
    result, targets = [], []
    for change in changes:
        path, target = checked_target(workspace, change.path)
        if (change.before is not None and not isinstance(change.before, bytes)
                or change.after is not None and not isinstance(change.after, bytes)
                or change.before == change.after):
            raise ContractError("file transaction requires distinct byte images")
        if any(target == old or target.is_relative_to(old) or old.is_relative_to(target)
               for old in targets):
            raise ContractError("file transaction paths overlap")
        mode = change.mode
        if mode is None:
            mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        if type(mode) is not int or not 0 <= mode <= 0o777:
            raise ContractError("file transaction has an invalid source mode")
        result.append(replace(change, path=path, mode=mode))
        targets.append(target)
    return result


def _current(workspace: Path, change: FileChange) -> bytes | None:
    _, target = checked_target(workspace, change.path)
    return target.read_bytes() if target.exists() else None


def _entries(workspace: Path, *, deadline: ExecutionDeadline | None = None) -> dict[str, str]:
    raw = run_git(workspace, "ls-files", "--stage", "-z", text=False, deadline=deadline).stdout
    result = {}
    for entry in raw.decode("utf-8").split("\0"):
        if not entry:
            continue
        metadata, path = entry.split("\t", 1)
        mode, _, stage = metadata.split(" ")
        if stage != "0" or path in result:
            raise ContractError("file transaction requires an unambiguous Git index")
        result[path] = mode
    return result


def _preview_transaction(
    workspace: Path, changes: list[FileChange], *, baseline_diff_hash: str,
    deadline: ExecutionDeadline | None, recovering: bool, include_incremental: bool,
) -> tuple[DiffSummary, str]:
    """Construct the complete candidate without writing source or the real Git index."""
    changes = _normalized(workspace, changes)
    entries = _entries(workspace, deadline=deadline)
    for change in changes:
        current = _current(workspace, change)
        if current not in ((change.before, change.after) if recovering else (change.before,)):
            raise RecoveryError("workspace changed before file transaction admission")
        if (not recovering and change.before is not None
                and entries.get(change.path) not in {"100644", "100755"}):
            raise ContractError("file transaction target is not a tracked regular file")
        if change.path in entries and entries[change.path] not in {"100644", "100755"}:
            raise ContractError("file transaction target is not a regular Git entry")
    untracked = WorkspaceManager.untracked_files(workspace, deadline=deadline)
    if recovering:
        admitted_creates = {change.path for change in changes if change.before is None}
        untracked = [path for path in untracked if path not in admitted_creates]
        if untracked:
            raise RecoveryError("file transaction has unrelated untracked files")
    with tempfile.TemporaryDirectory(
        prefix="file-transaction-index-", dir=workspace.parent, ignore_cleanup_errors=True,
    ) as temporary:
        index = Path(temporary) / "index"
        real_index = Path(run_git(workspace, "rev-parse", "--git-path", "index",
                                  deadline=deadline).stdout.strip())
        if not real_index.is_absolute():
            real_index = workspace / real_index
        # Git uses the index timestamp to detect racy-clean worktree entries.
        # A newer copy timestamp can make a same-size edit look unchanged to
        # add -u, producing a false baseline mismatch (or a stale candidate).
        shutil.copy2(real_index, index)
        environment = {**os.environ, "GIT_INDEX_FILE": str(index)}

        def git(*arguments: str, content: bytes | None = None) -> str:
            completed = run_git(workspace, *arguments, input=content, text=False,
                                env=environment, deadline=deadline)
            return completed.stdout.decode("utf-8")

        # A copied index retains earlier explicit creates (intent-to-add), while
        # -u includes their current bytes and excludes unrelated untracked files.
        git("add", "-u", "--", ".")
        head_modes = {}
        for row in git("ls-tree", "-r", "HEAD", "-z").split("\0"):
            if row:
                metadata, path = row.split("\t", 1)
                head_modes[path] = metadata.split(" ", 1)[0]
        if recovering and any(change.path in head_modes and change.path not in entries
                              for change in changes):
            raise RecoveryError("file transaction has unknown Git index drift")

        def install(change: FileChange, content: bytes | None) -> None:
            if content is None:
                git("update-index", "--force-remove", "--", change.path)
                return
            mode = entries.get(change.path, head_modes.get(change.path, "100644"))
            if mode not in {"100644", "100755"}:
                raise ContractError("file transaction target is not a regular Git entry")
            blob = git("hash-object", "-w", "--stdin", f"--path={change.path}",
                       content=content).strip()
            git("update-index", "--add", "--cacheinfo", mode, blob, change.path)

        if recovering:
            for change in changes:
                install(change, change.before)
        baseline = git("diff", "--cached", "HEAD", "--no-ext-diff", "--binary")
        if sha256_bytes(baseline.encode("utf-8")) != baseline_diff_hash:
            raise RecoveryError("workspace changed before file transaction admission")
        before_tree = git("write-tree").strip() if include_incremental else None
        for change in changes:
            install(change, change.after)
        patch = git("diff", "--cached", "HEAD", "--no-ext-diff", "--binary")
        changed, added, deleted = _parse_numstat(git(
            "diff", "--cached", "HEAD", "--numstat", "-z"))
        incremental = ""
        if include_incremental:
            after_tree = git("write-tree").strip()
            incremental = git("diff", before_tree, after_tree, "--no-ext-diff", "--binary")
    return DiffSummary(changed, added, deleted, patch, untracked), incremental


def preview_transaction(
    workspace: Path, changes: list[FileChange], *, baseline_diff_hash: str,
    deadline: ExecutionDeadline | None = None,
) -> tuple[DiffSummary, str]:
    return _preview_transaction(workspace, changes, baseline_diff_hash=baseline_diff_hash,
                                deadline=deadline, recovering=False, include_incremental=True)


def preview_changes(
    workspace: Path, changes: list[FileChange], *, baseline_diff_hash: str,
    deadline: ExecutionDeadline | None = None,
) -> DiffSummary:
    return _preview_transaction(workspace, changes, baseline_diff_hash=baseline_diff_hash,
                                deadline=deadline, recovering=False, include_incremental=False)[0]


def validate_recovery(
    workspace: Path, changes: list[FileChange], *, baseline_diff_hash: str,
    candidate_diff_hash: str, deadline: ExecutionDeadline | None = None,
) -> None:
    """Validate an admitted partial write without changing source or the real index."""
    candidate, _ = _preview_transaction(
        workspace, changes, baseline_diff_hash=baseline_diff_hash,
        deadline=deadline, recovering=True, include_incremental=False,
    )
    if candidate.patch_hash != candidate_diff_hash:
        raise RecoveryError("file transaction candidate differs from admission")


def save_changes(
    store: ArtifactStore, changes: list[FileChange], *, workspace: Path,
) -> dict:
    """Store exact pre/post images outside the worktree for admitted recovery and undo."""
    if store.root.resolve().is_relative_to(workspace.resolve()):
        raise ContractError("file transaction artifacts must be outside the workspace")
    return {"schema": "file-transaction-v1", "changes": [{
        "path": change.path, "mode": change.mode,
        "before": (store.put_bytes(change.before).model_dump(mode="json")
                   if change.before is not None else None),
        "after": (store.put_bytes(change.after).model_dump(mode="json")
                  if change.after is not None else None),
    } for change in _normalized(workspace, changes)]}


def load_changes(store: ArtifactStore, packet: dict) -> list[FileChange]:
    if (not isinstance(packet, dict) or packet.get("schema") != "file-transaction-v1"
            or not isinstance(packet.get("changes"), list) or not packet["changes"]):
        raise RecoveryError("file transaction recovery packet is invalid")
    try:
        return [FileChange(
            path=row["path"], mode=row["mode"],
            before=(store.read_bytes(Artifact.model_validate(row["before"]))
                    if row["before"] is not None else None),
            after=(store.read_bytes(Artifact.model_validate(row["after"]))
                   if row["after"] is not None else None),
        ) for row in packet["changes"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise RecoveryError("file transaction recovery packet is invalid") from exc


def reverse_changes(changes: list[FileChange]) -> list[FileChange]:
    return [replace(change, before=change.after, after=change.before) for change in changes]


def _write_one(workspace: Path, change: FileChange, content: bytes | None) -> None:
    _, target = checked_target(workspace, change.path)
    if content is None:
        target.unlink(missing_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    checked_target(workspace, change.path)
    descriptor, name = tempfile.mkstemp(prefix="file-transaction-source-", dir=workspace.parent)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, change.mode)
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)


def _register_presence(
    workspace: Path, change: FileChange, content: bytes | None,
    *, deadline: ExecutionDeadline | None,
) -> None:
    if change.before is not None and change.after is not None:
        return  # Replacing bytes cannot change the existing index membership.
    base = run_git(workspace, "--literal-pathspecs", "ls-tree", "HEAD", "-z", "--", change.path,
                   deadline=deadline).stdout
    if not base:
        if content is None:
            run_git(workspace, "update-index", "--force-remove", "--", change.path,
                    deadline=deadline)
        else:
            # Only the explicitly admitted path joins the index. Content stays
            # unstaged and unrelated untracked files remain visible to scope checks.
            run_git(workspace, "--literal-pathspecs", "add", "-N", "-f", "--", change.path,
                    deadline=deadline)


def _complete(
    workspace: Path, changes: list[FileChange], *, after: bool,
    deadline: ExecutionDeadline | None,
) -> None:
    # Validate the whole batch before completing any partial write.
    for change in changes:
        if _current(workspace, change) not in (change.before, change.after):
            raise RecoveryError("file transaction has unknown source drift")
    for change in changes:
        if deadline is not None:
            deadline.check()
        wanted = change.after if after else change.before
        if _current(workspace, change) != wanted:
            _write_one(workspace, change, wanted)
        _register_presence(workspace, change, wanted, deadline=deadline)


def apply_changes(
    workspace: Path, changes: list[FileChange], *, deadline: ExecutionDeadline | None = None,
) -> None:
    """Apply one admitted batch; ordinary failures restore its exact preimages."""
    changes = _normalized(workspace, changes)
    if any(_current(workspace, change) != change.before for change in changes):
        raise RecoveryError("workspace changed before file transaction execution")
    reconcile_changes(workspace, changes, deadline=deadline)


def reconcile_changes(
    workspace: Path, changes: list[FileChange], *, deadline: ExecutionDeadline | None = None,
) -> None:
    """Finish known partial writes; ordinary errors restore the whole admitted preimage."""
    changes = _normalized(workspace, changes)
    if any(_current(workspace, change) not in (change.before, change.after) for change in changes):
        raise RecoveryError("file transaction has unknown source drift")
    try:
        _complete(workspace, changes, after=True, deadline=deadline)
    except GitExecutionUncertain:
        # A still-running Git descendant may own the index. Preserve uncertainty.
        raise
    except Exception:
        try:
            _complete(workspace, changes, after=False,
                      deadline=ExecutionDeadline.from_remaining(5))
        except Exception as exc:
            raise FileTransactionUncertain(
                "file transaction rollback could not be confirmed",
                details={"file_transaction_uncertain": True},
            ) from exc
        raise
