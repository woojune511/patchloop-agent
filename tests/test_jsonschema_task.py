"""Admission boundaries for the public jsonschema development task."""

import shutil

import pytest

from patchloop.dev.conversation import assemble_model_input
from patchloop.errors import ContractError
from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES, WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

TASK = repository_root() / "tasks/dev-train/jsonschema-regex-recursion-1538"


def test_package_binds_source_image_and_public_only_evaluation():
    package = load_task_package(TASK)
    assert package.public.split == "dev-train"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.repository.base_commit == "51cd75e399c760e5aa3adce600dcce1385756ab0"
    assert package.environment.evaluator_image.endswith("@" + package.environment.image_digest)
    assert not package.private.hidden_checks
    assert not package.private.hidden_artifacts
    assert "public-only-evaluation" in package.public.tags
    assert package.public.constraints.forbidden_paths == ["jsonschema/tests/**"]
    assert WorkspaceManager.patch_changed_files((TASK / "reference.patch").read_bytes()) == [
        "jsonschema/_format.py"
    ]
    assert all(c.infrastructure_exit_codes == [2] for c in package.public.visible_checks)


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_agent_projection_excludes_calibration_reference(policy):
    package = load_task_package(TASK)
    state = {"public_task": package.public.model_dump(mode="json"),
             "current_diff": {"patch": ""}, "visible_check_status": {}}
    projected = assemble_model_input(system_prompt="Public task only.", state=state,
                                     history=[], context_policy=policy)
    serialized = canonical_json(projected)
    for marker in ("reference.patch", package.private.reference_patch.sha256,
                   package.private_spec_hash, package.environment.evaluator_image):
        assert marker not in serialized
    assert "regex-format-contract" in serialized


@pytest.mark.parametrize("missing", [False, True])
def test_reference_identity_is_checked(tmp_path, missing):
    root = tmp_path / "task"
    shutil.copytree(TASK, root)
    reference = root / "reference.patch"
    if missing:
        reference.unlink()
    else:
        reference.write_bytes(reference.read_bytes() + b"\n")
    with pytest.raises(ContractError, match="reference patch"):
        load_task_package(root)
