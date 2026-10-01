"""Fixed batch admission preserves private oracle boundaries and failure classes."""
import json
import shutil

import pytest

from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.runner import _live_task_is_admitted
from patchloop.errors import ContractError
from patchloop.repository import ALLOWED_REMOTE_REPOSITORIES
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json


@pytest.fixture(params=["original-opensandbox-816", "original-pyinfra-1679",
                        "original-isort-2491"])
def task(request):
    return repository_root() / "tasks/dev-train" / request.param


def test_batch_admission_and_oracle_membership(task):
    package = load_task_package(task)
    _live_task_is_admitted(task, package)
    assert package.public.repository.url in ALLOWED_REMOTE_REPOSITORIES
    oracle = json.loads((task / "hidden/oracle.json").read_text(encoding="utf-8"))
    counts = {"original-opensandbox-816": (1, 108), "original-pyinfra-1679": (3, 10),
              "original-isort-2491": (1, 73)}
    assert (len(oracle["FAIL_TO_PASS"]), len(oracle["PASS_TO_PASS"])) == counts[task.name]
    assert not set(oracle["FAIL_TO_PASS"]) & set(oracle["PASS_TO_PASS"])
    assert package.private.hidden_checks[0].infrastructure_exit_codes == [2]
    assert package.public.visible_checks[0].infrastructure_exit_codes == [2, 3, 4, 5]


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_batch_context_contains_no_private_inputs(task, policy):
    package = load_task_package(task)
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


@pytest.mark.parametrize("relative", ["hidden/oracle.json", "hidden/scoring.py",
                                      "hidden/run_oracle.py", "reference.patch"])
def test_batch_rejects_modified_private_inputs(task, tmp_path, relative):
    target = tmp_path / "task"
    shutil.copytree(task, target)
    path = target / relative
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ContractError, match="hash mismatch"):
        load_task_package(target)
