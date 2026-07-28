from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from patchloop.agent.context import build_context
from patchloop.agent.tools import TOOL_SCHEMAS, ToolGateway
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import EventType
from patchloop.errors import ActionConflict, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_text


def _smoke_gateway(tmp_path, run_id):
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id=run_id)
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )
    return manager, workspace, gateway


def _r2_style_recount_patch() -> str:
    return (
        "diff --git a/mini_data_utils/csvlite.py "
        "b/mini_data_utils/csvlite.py\n"
        "--- a/mini_data_utils/csvlite.py\n"
        "+++ b/mini_data_utils/csvlite.py\n"
        "@@ -1,7 +1,7 @@\n"
        '-"""A deliberately small CSV reader with one audited defect."""\n'
        '+"""A deliberately small CSV reader with one verified defect."""\n'
        " \n"
        " import csv\n"
        " \n"
        " \n"
        " def parse_rows(text: str) -> list[list[str]]:\n"
    )


def test_mutating_tool_rolls_back_forbidden_path(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_policy")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )
    patch = Path("tasks/smoke/csv-quoted-newline/bad/forbidden-path.patch").read_text(
        encoding="utf-8"
    )
    result = gateway.execute("apply_patch", "forbidden-mutation", {"patch": patch})
    assert result.status == "rejected"
    assert "outside allowed_paths" in (result.error_message or "")
    assert manager.diff_summary(workspace).changed_files == []


def test_apply_patch_recounts_incorrect_hunk_line_totals(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount",
    )
    patch = _r2_style_recount_patch()

    result = gateway.execute(
        "apply_patch",
        "recount-valid-text-patch",
        {"patch": patch},
    )

    assert result.status == "succeeded"
    assert result.output["patch_hash"] == sha256_text(patch)
    assert manager.diff_summary(workspace).changed_files == [
        "mini_data_utils/csvlite.py"
    ]
    assert "one verified defect" in (
        workspace / "mini_data_utils" / "csvlite.py"
    ).read_text(encoding="utf-8")


def test_recounted_patch_replay_is_idempotent(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount_replay",
    )
    patch = _r2_style_recount_patch()

    first = gateway.execute(
        "apply_patch",
        "recount-replay",
        {"patch": patch},
    )
    first_diff_hash = manager.diff_summary(workspace).patch_hash
    second = gateway.execute(
        "apply_patch",
        "recount-replay",
        {"patch": patch},
    )

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert second.output["replayed"] is True
    assert manager.diff_summary(workspace).patch_hash == first_diff_hash
    events = gateway.state.list_events(gateway.run_id)
    assert sum(event.type.value == "ToolCalled" for event in events) == 1
    assert sum(event.type.value == "PatchApplied" for event in events) == 1
    conflicting_patch = patch.replace("verified defect", "reviewed defect", 1)
    with pytest.raises(ActionConflict):
        gateway.execute(
            "apply_patch",
            "recount-replay",
            {"patch": conflicting_patch},
        )
    assert manager.diff_summary(workspace).patch_hash == first_diff_hash


def test_recounted_policy_violation_is_rolled_back_with_same_patch(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount_rollback",
    )
    accepted_patch = _r2_style_recount_patch()
    accepted = gateway.execute(
        "apply_patch",
        "recount-before-forbidden",
        {"patch": accepted_patch},
    )
    assert accepted.status == "succeeded"
    pre_rejection_diff_hash = manager.diff_summary(workspace).patch_hash

    patch = Path(
        "tasks/smoke/csv-quoted-newline/bad/forbidden-path.patch"
    ).read_text(encoding="utf-8")
    patch = patch.replace("@@ -1,4 +1,6 @@", "@@ -1,40 +1,60 @@")

    result = gateway.execute(
        "apply_patch",
        "recount-forbidden-text-patch",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert "outside allowed_paths" in (result.error_message or "")
    summary = manager.diff_summary(workspace)
    assert summary.patch_hash == pre_rejection_diff_hash
    assert summary.changed_files == ["mini_data_utils/csvlite.py"]
    assert "intentionally outside the task scope" not in (
        workspace / "README.md"
    ).read_text(encoding="utf-8")


def test_search_glob_cannot_escape_workspace(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_search")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )
    result = gateway.execute(
        "search_files", "escape-search", {"query": "secret", "path_glob": "../**/*"}
    )
    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"


def test_rejected_patch_format_is_durable_and_visible_to_next_turn(tmp_path) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_patch_format")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )

    result = gateway.execute(
        "apply_patch",
        "invalid-patch-envelope",
        {
            "patch": (
                "*** Begin Patch\n"
                "*** Update File: mini_data_utils/csvlite.py\n"
                "*** End Patch"
            )
        },
    )

    assert result.status == "rejected"
    assert "raw Git unified diff" in (result.error_message or "")
    assert result.output["error_details"]["stage"] == "format"
    assert result.output["error_details"]["reason"] == "invalid_envelope"
    patch_schema = next(schema for schema in TOOL_SCHEMAS if schema["name"] == "apply_patch")
    assert "diff --git" in patch_schema["description"]
    assert "*** Begin Patch" in patch_schema["description"]
    error_artifact = Path(result.output["artifact_path"])
    assert error_artifact.is_file()
    events = state.list_events(manifest.run_id)
    failed = events[-1]
    assert failed.payload["error_message"] == result.error_message
    context, _ = build_context(package.public, events, None)
    assert "raw Git unified diff" in context
    assert "diff --git" in context


def test_check_and_diff_results_are_bound_to_current_worktree(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_diff_binding",
    )
    patch = Path(
        "tasks/smoke/csv-quoted-newline/reference.patch"
    ).read_text(encoding="utf-8")

    applied = gateway.execute(
        "apply_patch",
        "diff-binding-patch",
        {"patch": patch},
    )
    checked = gateway.execute(
        "run_check",
        "diff-binding-check",
        {"check_id": "existing-unit-tests"},
    )
    reviewed = gateway.execute("get_diff", "diff-binding-review", {})

    diff_hash = manager.diff_summary(workspace).patch_hash
    assert applied.output["worktree_diff_hash"] == diff_hash
    assert checked.output["worktree_diff_hash"] == diff_hash
    assert reviewed.output["worktree_diff_hash"] == diff_hash
    bound_events = [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") in {"run_check", "get_diff"}
    ]
    assert {event.payload["worktree_diff_hash"] for event in bound_events} == {
        diff_hash
    }


def test_repeated_call_is_advisory_and_visible(tmp_path) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_repeat_signal",
    )
    arguments = {"query": "parse_rows", "path_glob": "**/*.py"}

    first = gateway.execute("search_files", "search-first", arguments)
    second = gateway.execute("search_files", "search-second", arguments)

    assert first.status == second.status == "succeeded"
    loop_events = [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.LOOP_DETECTED
    ]
    assert len(loop_events) == 1
    assert loop_events[0].payload["tool"] == "search_files"
    assert loop_events[0].payload["enforcement"] == "advisory"


def test_nonconsecutive_repeated_call_is_not_marked_as_loop(tmp_path) -> None:
    _, _, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_nonconsecutive_repeat",
    )
    repeated = {"query": "parse_rows", "path_glob": "**/*.py"}

    gateway.execute("search_files", "search-first", repeated)
    gateway.execute(
        "read_file",
        "read-between-searches",
        {
            "path": "mini_data_utils/csvlite.py",
            "start_line": 1,
            "end_line": 2,
        },
    )
    gateway.execute("search_files", "search-after-read", repeated)

    assert not [
        event
        for event in gateway.state.list_events(gateway.run_id)
        if event.type == EventType.LOOP_DETECTED
    ]


@pytest.mark.parametrize(
    ("patch", "expected_error"),
    [
        (
            "diff --git a/mini_data_utils/csvlite.py b/mini_data_utils/csvlite.py\n"
            "old mode 100644\n"
            "new mode 100755\n",
            "metadata-only",
        ),
        (
            "diff --git a/mini_data_utils/blob.bin b/mini_data_utils/blob.bin\n"
            "new file mode 100644\n"
            "index 0000000..1234567\n"
            "GIT binary patch\n"
            "literal 1\n"
            "AcmZQz\n",
            "binary patches",
        ),
    ],
)
def test_apply_patch_rejects_binary_and_metadata_only_changes(
    tmp_path,
    patch,
    expected_error,
) -> None:
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(package, run_id="run_gateway_patch_policy")
    state = StateStore(tmp_path / "state.sqlite3")
    state.create_run(manifest)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create(
        manifest.run_id,
        package.public.repository.url,
        package.public.repository.base_commit,
    )
    gateway = ToolGateway(
        run_id=manifest.run_id,
        workspace=workspace,
        task=package.public,
        state=state,
        artifacts=ArtifactStore(tmp_path / "artifacts"),
        sandbox=LocalSandbox(),
    )

    result = gateway.execute(
        "apply_patch",
        f"reject-{expected_error}",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert expected_error in (result.error_message or "")
    assert manager.diff_summary(workspace).changed_files == []


@pytest.mark.parametrize(
    "patch",
    [
        (
            "diff --git a/mini_data_utils/new_module.py "
            "b/mini_data_utils/new_module.py\n"
            "new file mode 100644\n"
            "index 0000000..f11d8a9\n"
            "--- /dev/null\n"
            "+++ b/mini_data_utils/new_module.py\n"
            "@@ -0,0 +1 @@\n"
            "+VALUE = 1\n"
        ),
        (
            "diff --git a/mini_data_utils/csvlite.py "
            "b/mini_data_utils/renamed.py\n"
            "--- a/mini_data_utils/csvlite.py\n"
            "+++ b/mini_data_utils/renamed.py\n"
            "@@ -1 +1 @@\n"
            "-import csv\n"
            "+import csv\n"
        ),
    ],
)
def test_apply_patch_rejects_untracked_or_path_changing_outputs(
    tmp_path,
    patch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_reject_untracked",
    )

    result = gateway.execute(
        "apply_patch",
        "reject-untracked-output",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert result.error_code == "CONTRACT_ERROR"
    assert not (workspace / "mini_data_utils" / "new_module.py").exists()
    assert not (workspace / "mini_data_utils" / "renamed.py").exists()
    assert manager.diff_summary(workspace).changed_files == []


def test_post_apply_untracked_file_is_rolled_back(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_post_apply_untracked",
    )
    patch = (
        "diff --git a/mini_data_utils/new_module.py "
        "b/mini_data_utils/new_module.py\n"
        "new file mode 100644\n"
        "index 0000000..f11d8a9\n"
        "--- /dev/null\n"
        "+++ b/mini_data_utils/new_module.py\n"
        "@@ -0,0 +1 @@\n"
        "+VALUE = 1\n"
    )
    monkeypatch.setattr(
        "patchloop.agent.tools._validate_raw_git_patch",
        lambda _patch: None,
    )

    result = gateway.execute(
        "apply_patch",
        "rollback-post-apply-untracked",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert "produced untracked files" in (result.error_message or "")
    assert not (workspace / "mini_data_utils" / "new_module.py").exists()
    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == []


def test_apply_patch_rejects_preexisting_untracked_target(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_preexisting_untracked",
    )
    target = workspace / "scratch.txt"
    target.write_text("before\n", encoding="utf-8")
    patch = (
        "diff --git a/scratch.txt b/scratch.txt\n"
        "--- a/scratch.txt\n"
        "+++ b/scratch.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )

    result = gateway.execute(
        "apply_patch",
        "reject-preexisting-untracked",
        {"patch": patch},
    )

    assert result.status == "failed"
    assert result.error_code == RecoveryError.code
    assert result.output["fatal"] is True
    assert target.read_text(encoding="utf-8") == "before\n"
    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == ["scratch.txt"]


def test_recount_does_not_relax_hunk_context(tmp_path) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_recount_context",
    )
    patch = _r2_style_recount_patch()
    patch = patch.replace("import csv", "import missing_csv")

    result = gateway.execute(
        "apply_patch",
        "reject-invalid-context",
        {"patch": patch},
    )

    assert result.status == "rejected"
    assert "patch application failed" in (result.error_message or "")
    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == []


def test_post_apply_verifier_error_rolls_back_before_propagating(
    tmp_path,
    monkeypatch,
) -> None:
    manager, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_verifier_error",
    )
    patch = _r2_style_recount_patch()

    def fail_verifier(*_args, **_kwargs):
        raise RuntimeError("synthetic verifier failure")

    monkeypatch.setattr("patchloop.agent.tools.verify_scope", fail_verifier)

    with pytest.raises(RuntimeError, match="synthetic verifier failure"):
        gateway.execute(
            "apply_patch",
            "rollback-verifier-error",
            {"patch": patch},
        )

    assert manager.diff_summary(workspace).changed_files == []
    assert manager.untracked_files(workspace) == []


def test_apply_patch_fails_closed_when_policy_rollback_fails(
    tmp_path,
    monkeypatch,
) -> None:
    _, workspace, gateway = _smoke_gateway(
        tmp_path,
        "run_gateway_failed_rollback",
    )
    patch = Path(
        "tasks/smoke/csv-quoted-newline/bad/forbidden-path.patch"
    ).read_text(encoding="utf-8")
    real_run = subprocess.run

    def fail_reverse(args, *positional, **keywords):
        if args[:2] == ["git", "apply"] and "--reverse" in args:
            return subprocess.CompletedProcess(
                args,
                1,
                stdout=b"",
                stderr=b"forced rollback failure",
            )
        return real_run(args, *positional, **keywords)

    monkeypatch.setattr(subprocess, "run", fail_reverse)

    result = gateway.execute(
        "apply_patch",
        "force-failed-rollback",
        {"patch": patch},
    )

    assert result.status == "failed"
    assert result.error_code == RecoveryError.code
    assert "policy rollback failed" in (result.error_message or "")
    assert result.output["fatal"] is True
    assert "intentionally outside the task scope" in (
        workspace / "README.md"
    ).read_text(encoding="utf-8")
