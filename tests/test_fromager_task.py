"""Admission and public/private boundaries for the new development task."""

from __future__ import annotations

import shutil

import pytest

from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.errors import ContractError
from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES, WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

TASK = repository_root() / "tasks/dev-train/fromager-recursive-orphan-removal"


def test_new_development_package_has_bound_source_and_private_artifacts():
    package = load_task_package(TASK)
    assert package.public.split == "dev-train"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.repository.base_commit == "f82c1e64a027060c3e25090f6a4a4d7f4e3d985d"
    assert package.private.schema_version == "task-private-v2"
    assert len(package.private.hidden_artifacts) == 1
    assert package.public.constraints.allowed_paths == ["src/fromager/dependency_graph.py"]
    assert package.environment.evaluator_image.endswith("@" + package.environment.image_digest)
    assert WorkspaceManager.patch_changed_files((TASK / "reference.patch").read_bytes()) == [
        "src/fromager/dependency_graph.py"
    ]
    assert [check.id for check in package.public.visible_checks] == [
        "orphan-removal-contract", "upstream-dependency-graph-regression"
    ]


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_new_task_projection_contains_only_public_requirements_and_checks(policy):
    package = load_task_package(TASK)
    state = {"public_task": package.public.model_dump(mode="json"),
             "current_diff": {"patch": ""}, "visible_check_status": {}}
    projected = assemble_model_input(system_prompt="Public task only.", state=state,
                                     history=[], context_policy=policy)
    assert reconstruct_state(projected, context_policy=policy) == state
    serialized = canonical_json(projected)
    for private_marker in (
        "independent-orphan-invariants", "check_orphan_removal.py", "reference.patch",
        package.private_spec_hash, package.private.hidden_artifacts[0].sha256,
    ):
        assert private_marker not in serialized
    assert "orphan-removal-contract" in serialized


@pytest.mark.parametrize("changed", ["hidden", "reference", "missing"])
def test_new_package_rejects_evaluator_or_reference_tampering(tmp_path, changed):
    copy = tmp_path / "task"
    shutil.copytree(TASK, copy)
    relative = "reference.patch" if changed == "reference" else "hidden/check_orphan_removal.py"
    path = copy / relative
    if changed == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n# modified\n")
    with pytest.raises(ContractError, match="hidden artifact|reference patch"):
        load_task_package(copy)
