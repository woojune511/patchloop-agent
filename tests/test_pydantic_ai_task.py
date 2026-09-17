"""Registration identity and public/private boundaries for synthetic tool history."""

from __future__ import annotations

import shutil

import pytest

from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.errors import ContractError
from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES, WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

TASK = repository_root() / "tasks/dev-train/pydantic-ai-synthetic-tool-reasoning"
PREFIX = "pydantic_ai_slim/pydantic_ai/"


def test_development_task_binds_source_image_and_independent_artifacts():
    package = load_task_package(TASK)
    assert package.public.split == "dev-train"
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.repository.base_commit == "5965db82c4e10012a8598c14716ea8a88fb411a9"
    assert package.private.schema_version == "task-private-v2"
    assert len(package.private.hidden_artifacts) == 1
    assert package.environment.evaluator_image.endswith("@" + package.environment.image_digest)
    assert WorkspaceManager.patch_changed_files((TASK / "reference.patch").read_bytes()) == [
        PREFIX + "models/openai.py", PREFIX + "profiles/openai.py", PREFIX + "providers/deepseek.py"
    ]
    assert [check.id for check in package.public.visible_checks] == [
        "synthetic-tool-history-contract", "upstream-reasoning-regression"
    ]
    assert all(check.command[0] == "/pydantic-ai/.venv/bin/python"
               for check in package.public.visible_checks)


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_task_projects_only_public_requirements_and_checks(policy):
    package = load_task_package(TASK)
    state = {"public_task": package.public.model_dump(mode="json"),
             "current_diff": {"patch": ""}, "visible_check_status": {}}
    projected = assemble_model_input(system_prompt="Public task only.", state=state,
                                     history=[], context_policy=policy)
    assert reconstruct_state(projected, context_policy=policy) == state
    serialized = canonical_json(projected)
    for private_marker in (
        "independent-tool-history-wire-contract", "check_tool_history.py", "reference.patch",
        package.private_spec_hash, package.private.hidden_artifacts[0].sha256,
    ):
        assert private_marker not in serialized
    assert "synthetic-tool-history-contract" in serialized


@pytest.mark.parametrize("changed", ["hidden", "reference", "missing"])
def test_registration_rejects_private_artifact_tampering(tmp_path, changed):
    copied = tmp_path / "task"
    shutil.copytree(TASK, copied)
    relative = "reference.patch" if changed == "reference" else "hidden/check_tool_history.py"
    path = copied / relative
    if changed == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n# modified\n")
    with pytest.raises(ContractError, match="hidden artifact|reference patch"):
        load_task_package(copied)
