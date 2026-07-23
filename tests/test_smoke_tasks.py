from __future__ import annotations

from pathlib import Path

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.repository import WorkspaceManager
from patchloop.runtime import build_manifest
from patchloop.sandbox import LocalSandbox
from patchloop.task_loader import load_task_package
from patchloop.verifier import EvaluationEngine

TASK_CASES = {
    "config-falsy-override": [
        "bad/noop.patch",
        "bad/near-miss.patch",
        "bad/regression.patch",
        "bad/forbidden-path.patch",
    ],
    "path-prefix-boundary": [
        "bad/noop.patch",
        "bad/near-miss.patch",
        "bad/regression.patch",
        "bad/forbidden-path.patch",
    ],
}


def _evaluate(tmp_path: Path, task_id: str, patch_name: str):
    task_dir = Path("tasks/smoke") / task_id
    package = load_task_package(task_dir)
    engine = EvaluationEngine(
        WorkspaceManager("fixtures/repositories", tmp_path / "workspaces"),
        LocalSandbox(),
        ArtifactStore(tmp_path / "artifacts"),
    )
    manifest = build_manifest(package, sandbox_backend="local")
    return engine.evaluate(task_dir, task_dir / patch_name, manifest)


@pytest.mark.parametrize("task_id", TASK_CASES)
def test_added_smoke_reference_patch_passes(tmp_path, task_id: str) -> None:
    result = _evaluate(tmp_path, task_id, "reference.patch")
    assert result.scope_compliant_success is True
    assert result.official is False


@pytest.mark.parametrize(
    ("task_id", "patch_name"),
    [
        (task_id, patch_name)
        for task_id, patch_names in TASK_CASES.items()
        for patch_name in patch_names
    ],
)
def test_added_smoke_bad_patch_is_rejected(
    tmp_path, task_id: str, patch_name: str
) -> None:
    assert _evaluate(tmp_path, task_id, patch_name).scope_compliant_success is False
