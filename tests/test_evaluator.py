from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import TaskConstraints
from patchloop.errors import ContractError
from patchloop.repository import DiffSummary, WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.verifier import EvaluationEngine
from patchloop.verifier.policy import verify_public_api, verify_test_tampering

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


def test_remote_repository_revision_must_be_lowercase_hex(tmp_path) -> None:
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")
    with pytest.raises(ContractError, match="full 40-character commit"):
        manager.create(
            "remote-invalid-revision",
            "https://github.com/youssofal/MTPLX.git",
            "g" * 40,
        )


def test_remote_repository_shallow_fetches_the_exact_revision(tmp_path, monkeypatch) -> None:
    expected_revision = "c06cc13286e86d9ff3d2e3b991eba327549c534b"
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[1] == "init":
            Path(command[-1]).mkdir(parents=True)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if command[1:3] == ["rev-parse", "HEAD"]:
            return SimpleNamespace(
                returncode=0,
                stdout=f"{expected_revision}\n",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("patchloop.repository.subprocess.run", fake_run)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")

    workspace = manager.create(
        "remote-exact-fetch",
        "https://github.com/youssofal/MTPLX.git",
        expected_revision,
    )

    assert workspace.is_dir()
    assert [
        "git",
        "fetch",
        "--quiet",
        "--no-tags",
        "--depth",
        "1",
        "origin",
        expected_revision,
    ] in commands
    assert ["git", "config", "core.longpaths", "true"] in commands
    assert ["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"] in commands
    assert all(command[1] != "clone" for command in commands)


def test_remote_repository_reports_exact_revision_fetch_failure(
    tmp_path, monkeypatch
) -> None:
    expected_revision = "c06cc13286e86d9ff3d2e3b991eba327549c534b"

    def fake_run(command, **kwargs):
        if command[1] == "init":
            Path(command[-1]).mkdir(parents=True)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if command[1] == "fetch":
            return SimpleNamespace(
                returncode=128,
                stdout="",
                stderr="fatal: remote error",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("patchloop.repository.subprocess.run", fake_run)
    manager = WorkspaceManager("fixtures/repositories", tmp_path / "workspaces")

    with pytest.raises(ContractError, match="exact-SHA fetch failed"):
        manager.create(
            "remote-exact-fetch-failure",
            "https://github.com/youssofal/MTPLX.git",
            expected_revision,
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


def test_public_api_base_source_is_explicitly_decoded_as_utf8(
    tmp_path, monkeypatch
) -> None:
    source = '"""Locale separator → canonical form."""\n\ndef stable(value):\n    return value\n'
    (tmp_path / "module.py").write_text(source, encoding="utf-8")

    def fake_run(*args, **kwargs):
        assert kwargs["encoding"] == "utf-8"
        return SimpleNamespace(returncode=0, stdout=source, stderr="")

    monkeypatch.setattr("patchloop.verifier.policy.subprocess.run", fake_run)
    outcome = verify_public_api(
        DiffSummary(["module.py"], 0, 0, ""),
        TaskConstraints(allowed_paths=["module.py"]),
        tmp_path,
    )

    assert outcome.passed is True
    assert outcome.details["changed_symbols"] == []


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_parser.py",
        "python_modules/dagster/dagster_tests/asset_defs_tests/test_partitioned_assets.py",
        "package/component_tests/cases.py",
        "package/test_component.py",
        "package/component_test.py",
        ".patchloop-hidden/oracle.py",
    ],
)
def test_test_tampering_recognizes_common_test_paths(path: str) -> None:
    outcome = verify_test_tampering(DiffSummary([path], 1, 0, ""))

    assert outcome.passed is False
    assert outcome.details["test_files"] == [path]


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
