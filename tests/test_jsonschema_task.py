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
V2 = TASK.with_name(TASK.name + "-v2")


def test_v2_requires_hidden_evidence_without_changing_public_cases():
    original = load_task_package(TASK)
    package = load_task_package(V2)
    assert package.public.task_version == package.private.task_version == 2
    assert package.public.issue == original.public.issue
    assert package.public.visible_checks == original.public.visible_checks
    assert package.public.repository == original.public.repository
    assert package.private.schema_version == "task-private-v2"
    assert len(package.private.hidden_checks) == len(package.private.hidden_artifacts) == 1
    assert package.private.hidden_checks[0].infrastructure_exit_codes == [2]
    assert package.task_content_hash != original.task_content_hash


@pytest.mark.parametrize("missing", [False, True])
def test_v2_hidden_artifact_integrity(tmp_path, missing):
    root = tmp_path / "task"
    shutil.copytree(V2, root)
    artifact = root / "hidden/test_regex_semantics.py"
    if missing:
        artifact.unlink()
    else:
        artifact.write_bytes(artifact.read_bytes() + b"\n")
    with pytest.raises(ContractError, match="hidden artifact"):
        load_task_package(root)


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_v2_hides_evaluator_from_agent(policy):
    package = load_task_package(V2)
    projected = assemble_model_input(
        system_prompt="Public task only.",
        state={"public_task": package.public.model_dump(mode="json"),
               "current_diff": {"patch": ""}, "visible_check_status": {}},
        history=[], context_policy=policy,
    )
    serialized = canonical_json(projected)
    for marker in ("test_regex_semantics", "private-regex-semantics",
                   package.private.hidden_artifacts[0].sha256, package.private_spec_hash):
        assert marker not in serialized


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
