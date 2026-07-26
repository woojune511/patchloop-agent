from __future__ import annotations

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.verifier import EvaluationEngine

TASK = "tasks/smoke/csv-quoted-newline"


def _evaluate(tmp_path, patch_name: str):
    package = load_task_package(TASK)
    engine = EvaluationEngine(
        WorkspaceManager("fixtures/repositories", tmp_path / "workspaces"),
        LocalSandbox(),
        ArtifactStore(tmp_path / "artifacts"),
    )
    manifest = build_manifest(package, sandbox_backend="local")
    return engine.evaluate(TASK, f"{TASK}/{patch_name}", manifest)


def test_reference_patch_passes_hidden_regression_and_scope(tmp_path) -> None:
    result = _evaluate(tmp_path, "reference.patch")
    assert result.scope_compliant_success is True
    assert result.official is False


def test_snapshot_content_hash_mismatch_is_rejected(tmp_path) -> None:
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    with pytest.raises(ContractError, match="content hash"):
        manager.create("bad-revision", "snapshot://mini-data-utils", "sha256:not-the-tree")


def test_remote_repository_must_be_allowlisted(tmp_path) -> None:
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    with pytest.raises(ContractError, match="not allowlisted"):
        manager.create(
            "remote",
            "https://github.com/example/untrusted",
            "0" * 40,
        )


def test_diff_summary_decodes_utf8_source_content(tmp_path) -> None:
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    workspace = manager.create("utf8-diff", "snapshot://mini-data-utils")
    readme = workspace / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nValid empty — not missing.\n",
        encoding="utf-8",
    )

    summary = manager.diff_summary(workspace)

    assert "Valid empty — not missing." in summary.patch
    assert summary.changed_files == ["README.md"]


@pytest.mark.parametrize(
    "patch_name",
    [
        "bad/noop.patch",
        "bad/regression.patch",
        "bad/forbidden-path.patch",
        "bad/dependency.patch",
        "bad/tampering.patch",
        "bad/public-api.patch",
    ],
)
def test_known_bad_patch_never_passes_full_evaluator(tmp_path, patch_name: str) -> None:
    assert _evaluate(tmp_path, patch_name).scope_compliant_success is False
