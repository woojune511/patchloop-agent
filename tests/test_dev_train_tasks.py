from __future__ import annotations

from pathlib import Path

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import VerdictState
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.verifier import EvaluationEngine

TASK = Path("tasks/dev-train/duration-minute-boundary")


def _evaluate(tmp_path: Path, patch_name: str):
    package = load_task_package(TASK)
    engine = EvaluationEngine(
        WorkspaceManager("fixtures/repositories", tmp_path / "workspaces"),
        LocalSandbox(),
        ArtifactStore(tmp_path / "artifacts"),
    )
    manifest = build_manifest(package, sandbox_backend="local")
    return engine.evaluate(TASK, TASK / patch_name, manifest)


def test_duration_reference_patch_passes(tmp_path) -> None:
    result = _evaluate(tmp_path, "reference.patch")
    assert result.scope_compliant_success is True
    assert result.official is False
    assert result.verdicts.hidden_tests == VerdictState.PASS
    assert result.verdicts.regression_tests == VerdictState.PASS
    assert result.verdicts.scope_policy == VerdictState.PASS


@pytest.mark.parametrize("patch_name", ["bad/noop.patch", "bad/near-miss.patch"])
def test_duration_incomplete_fixes_fail_hidden_acceptance(
    tmp_path, patch_name: str
) -> None:
    result = _evaluate(tmp_path, patch_name)
    assert result.scope_compliant_success is False
    assert result.verdicts.hidden_tests == VerdictState.FAIL
    assert result.verdicts.regression_tests == VerdictState.PASS
    assert result.verdicts.scope_policy == VerdictState.PASS


def test_duration_regression_patch_fails_visible_checks(tmp_path) -> None:
    result = _evaluate(tmp_path, "bad/regression.patch")
    assert result.scope_compliant_success is False
    assert result.verdicts.hidden_tests == VerdictState.PASS
    assert result.verdicts.regression_tests == VerdictState.FAIL
    assert result.verdicts.scope_policy == VerdictState.PASS


def test_duration_forbidden_patch_fails_scope(tmp_path) -> None:
    result = _evaluate(tmp_path, "bad/forbidden-path.patch")
    assert result.scope_compliant_success is False
    assert result.verdicts.hidden_tests == VerdictState.FAIL
    assert result.verdicts.regression_tests == VerdictState.PASS
    assert result.verdicts.scope_policy == VerdictState.FAIL
