"""Changed-source diagnostics follow Git paths and the declared Python entrypoint."""

from __future__ import annotations

import pytest

from patchloop.contracts import RegisteredCheck
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.execution_feedback import changed_lines, make_request
from patchloop.sandbox.runner import LocalSandbox
from patchloop.util import sha256_bytes


@pytest.mark.parametrize("path", ["src/café.py", "src/한글 이름.py", "src/space name.py"])
@pytest.mark.parametrize("quote_path", ["true", "false"])
def test_changed_lines_use_exact_paths_from_real_git_diff(tmp_path, path, quote_path):
    workspace = tmp_path / "repo"
    target = workspace / path
    target.parent.mkdir(parents=True)
    target.write_bytes(b"print(1)\n")
    for args in [
        ("init", "-q"), ("config", "core.quotepath", quote_path),
        ("config", "core.autocrlf", "false"), ("add", "."),
        ("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"),
    ]:
        run_git(workspace, *args)
    target.write_bytes(b"print(2)\n")
    summary = WorkspaceManager.diff_summary(workspace)
    assert summary.changed_files == [path]
    assert changed_lines(summary.patch) == {path: {1}}


@pytest.mark.parametrize("separator", ["\x85", "\u2028", "\u2029"])
def test_changed_lines_split_only_git_lf_framing(separator):
    path = f"src/line{separator}name.py"
    patch = (
        f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
        "@@ -1 +1,2 @@\n-old\n"
        f'+value = "first{separator}+still_string_content"\n'
        "+done = True\n"
    )
    assert changed_lines(patch) == {path: {1, 2}}


@pytest.mark.parametrize("spelling", ["relative", "dot-relative", "absolute"])
@pytest.mark.parametrize("change_directory", [False, True])
def test_changed_entrypoint_lines_are_observed_without_changing_script_arguments(
    tmp_path, spelling, change_directory,
):
    path = "scripts/main.py"
    target = tmp_path / path
    target.parent.mkdir()
    source = (
        "import os, sys\n"
        "print(sys.argv[0])\n"
        "print(sys.argv[1])\n"
        + ("os.chdir('scripts')\n" if change_directory else "pass\n")
        + "print('CURRENT_LINE')\n"
    ).encode()
    target.write_bytes(source)
    entrypoint = {"relative": path, "dot-relative": "./" + path, "absolute": str(target)}[
        spelling
    ]
    targets = make_request(
        sha256_bytes(b"entrypoint-diff"), [{
            "path": path, "file_hash": sha256_bytes(source), "changed_lines": [1, 2, 3, 4, 5],
        }], execution_identity={"run_id": "entrypoint", "action_id": "check"},
        omitted_file_count=0, deleted_line_count=1,
    )
    check = RegisteredCheck(id="script", command=["python", entrypoint, "public-argument"])
    result = LocalSandbox().run_check(tmp_path, check, execution_targets=targets)
    assert result.passed and not result.stderr
    assert result.command == check.command
    assert result.stdout.splitlines() == [entrypoint, "public-argument", "CURRENT_LINE"]
    row = result.public_execution["files"][0]
    assert row["status"] == "collected"
    assert row["executed_changed_ranges"] == [[1, 5]]
    assert row["not_observed_changed_ranges"] == []
