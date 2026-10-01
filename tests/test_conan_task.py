"""Original benchmark package admission and agent/evaluator separation."""

import json
import shutil

import pytest

from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.runner import _live_task_is_admitted
from patchloop.errors import ContractError
from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES, WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

TASK = repository_root() / "tasks/dev-train/original-conan-19735"


def test_original_conan_package_binds_oracle_and_source():
    package = load_task_package(TASK)
    _live_task_is_admitted(TASK, package)
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    assert package.public.repository.base_commit == "4a65d65f53d2ab37f4ce0e52dc3f25cd832b2934"
    assert package.environment.evaluator_image.endswith("@" + package.environment.image_digest)
    oracle = json.loads((TASK / "hidden/oracle.json").read_text(encoding="utf-8"))
    assert len(oracle["FAIL_TO_PASS"]) == 1
    assert len(oracle["PASS_TO_PASS"]) == 21
    assert not set(oracle["FAIL_TO_PASS"]) & set(oracle["PASS_TO_PASS"])
    assert package.private.hidden_checks[0].infrastructure_exit_codes == [2]
    paths = WorkspaceManager.patch_changed_files((TASK / "reference.patch").read_bytes())
    assert paths and all(path.startswith("conan/") and "/test/" not in path for path in paths)
    assert (TASK / "hidden/run_oracle.py").read_bytes() == (
        repository_root() / "diagnostics/original_task_oracle.py"
    ).read_bytes()


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_original_conan_private_data_is_not_projected(policy):
    package = load_task_package(TASK)
    state = {"public_task": package.public.model_dump(mode="json"),
             "current_diff": {"patch": ""}, "visible_check_status": {}}
    serialized = canonical_json(assemble_model_input(
        system_prompt="Public task only.", state=state, history=[], context_policy=policy,
    ))
    for marker in ("oracle.json", "original-oracle", "FAIL_TO_PASS", "reference.patch",
                   package.private_spec_hash,
                   *[a.sha256 for a in package.private.hidden_artifacts]):
        assert marker not in serialized
    assert "base-regression" in serialized


@pytest.mark.parametrize("relative", [
    "hidden/oracle.json", "hidden/scoring.py", "hidden/run_oracle.py", "reference.patch",
])
def test_original_conan_rejects_modified_private_inputs(tmp_path, relative):
    root = tmp_path / "task"
    shutil.copytree(TASK, root)
    path = root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ContractError, match="hash mismatch"):
        load_task_package(root)
