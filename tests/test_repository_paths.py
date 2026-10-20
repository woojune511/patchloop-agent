"""Git path framing must preserve the files authorized by the public tool layer."""
from __future__ import annotations

import pytest

from patchloop.contracts import PublicTask
from patchloop.dev.contracts import DevLimits, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager


@pytest.mark.parametrize("path,other_path", [
    ("src/café.py", None),
    ("src/한글 이름.py", None),
    ("src/space b/name.py", None),
    ("src/mod[x].py", "src/modx.py"),
])
@pytest.mark.parametrize("quote_path", ["true", "false"])
def test_allowed_path_survives_mutation_submission_and_patch_parsing(
    tmp_path, path, other_path, quote_path,
):
    workspace = tmp_path / "repo"
    target = workspace / path
    target.parent.mkdir(parents=True)
    target.write_bytes(b"value = 1\n")
    if other_path is not None:
        (workspace / other_path).write_bytes(b"value = 99\n")
    for args in [
        ("init", "-q"), ("config", "core.quotepath", quote_path),
        ("config", "core.autocrlf", "false"), ("add", "."),
        ("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"),
    ]:
        run_git(workspace, *args)
    public = PublicTask.model_validate({
        "task_id": "quoted-path", "split": "smoke",
        "repository": {"url": "snapshot://quoted-path", "base_commit": "sha256:" + "0" * 64},
        "issue": {"title": "Update value", "description": "Change the value to 2."},
        "constraints": {"allowed_paths": ["src/**" if other_path else path]},
    })
    gateway = DevToolGateway(
        workspace=workspace, public_task=public, sandbox=None, limits=DevLimits(),
        journal=DevJournal(tmp_path / "state", "run_dev_quotedpath"),
    )
    read = gateway.execute(RequestedTool(
        name="read_file", action_id="read",
        arguments={"path": path, "start_line": 1, "end_line": 5},
    ))
    assert read.status == "succeeded", read.message
    mutation = RequestedTool(name="replace_text", action_id="edit", arguments={
        "path": path, "old_text": "value = 1", "new_text": "value = 2", "occurrence": 1,
        "hypothesis": "The value is incorrect.", "expected_behavior": "The value is 2.",
        "causal_revision": None,
    })
    edited = gateway.execute(mutation)
    assert edited.status == "succeeded", edited.message
    assert target.read_bytes() == b"value = 2\n"
    summary = WorkspaceManager.diff_summary(workspace)
    assert summary.changed_files == [path]
    assert (summary.added_lines, summary.deleted_lines) == (1, 1)
    assert summary.patch_hash == edited.workspace_diff_hash
    raw_patch = run_git(workspace, "diff", "HEAD", "--no-ext-diff", "--binary", text=False).stdout
    assert summary.patch.encode("utf-8") == raw_patch
    assert WorkspaceManager.patch_changed_files(raw_patch) == [path]
    restored = DevToolGateway(
        workspace=workspace, public_task=public, sandbox=None, limits=DevLimits(),
        journal=gateway.journal,
    )
    assert restored.execute(mutation).replayed
    finished = restored.execute(RequestedTool(name="finish_task", action_id="finish", arguments={
        "assessment": "Reviewed the public patch and remaining uncertainty.",
    }))
    assert finished.status == "succeeded", finished.message
    assert target.read_bytes() == b"value = 2\n"
    if other_path is not None:
        assert (workspace / other_path).read_bytes() == b"value = 99\n"


def test_untracked_filename_matching_a_tracked_path_is_not_readable(gateway_factory):
    gateway, _, workspace = gateway_factory()
    path = "mini_data_utils/[c]svlite.py"
    assert (workspace / "mini_data_utils/csvlite.py").is_file()
    (workspace / path).write_bytes(b"untracked = True\n")
    read = gateway.execute(RequestedTool(
        name="read_file", action_id="untracked-pattern",
        arguments={"path": path, "start_line": 1, "end_line": 5},
    ))
    assert read.status == "failed"
    assert "tracked public file" in read.message


@pytest.mark.parametrize("header,expected", [
    ('diff --git "a/src/caf\\303\\251.py" "b/src/caf\\303\\251.py"', "src/café.py"),
    ('diff --git "a/src/tab\\tname.py" "b/src/tab\\tname.py"', "src/tab\tname.py"),
    ('diff --git "a/src/quote\\\"name.py" "b/src/quote\\\"name.py"', 'src/quote"name.py'),
    ("diff --git a/src/space b/name.py b/src/space b/name.py", "src/space b/name.py"),
])
def test_patch_paths_decode_git_quoted_bytes(header, expected):
    assert WorkspaceManager.patch_changed_files((header + "\n").encode()) == [expected]


@pytest.mark.parametrize("header", [
    "diff --git a/old.py b/new.py",
    'diff --git "a/caf\\303\\251.py" b/new.py',
    'diff --git a/old.py "b/caf\\303\\251.py"',
    'diff --git "a/old\\tname.py" "b/new\\tname.py"',
])
def test_patch_paths_still_reject_renames(header):
    with pytest.raises(ContractError, match="renames are unsupported"):
        WorkspaceManager.patch_changed_files((header + "\n").encode())


def test_patch_paths_do_not_hide_a_rename_behind_ambiguous_spaces():
    patch = b"diff --git a/x b/x b/x b/x\nrename from x\nrename to x b/x b/x\n"
    with pytest.raises(ContractError, match="renames are unsupported"):
        WorkspaceManager.patch_changed_files(patch)


def test_patch_paths_do_not_skip_an_invalid_second_header():
    patch = b'diff --git a/valid.py b/valid.py\ndiff --git "a/bad\\q.py" "b/bad\\q.py"\n'
    with pytest.raises(ContractError):
        WorkspaceManager.patch_changed_files(patch)


def test_numstat_preserves_control_characters_binary_counts_and_rename_paths():
    from patchloop.repository import _parse_numstat

    output = "1\t2\tsrc/café\tname\n.py\0-\t-\timage.png\0" "0\t0\t\0old.py\0new.py\0"
    assert _parse_numstat(output) == (
        ["src/café\tname\n.py", "image.png", "old.py", "new.py"], 1, 2,
    )
