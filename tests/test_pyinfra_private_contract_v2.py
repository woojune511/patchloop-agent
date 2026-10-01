"""Versioned timeout evaluation preserves public inputs and private integrity."""

import shutil

import pytest

from patchloop.dev.conversation import assemble_model_input
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

TASK = repository_root() / "tasks/dev-train/original-pyinfra-1679-v2"


def test_public_contract_preserved_and_hidden_inventory_bound():
    old = load_task_package(TASK.with_name("original-pyinfra-1679"))
    new = load_task_package(TASK)
    expected = old.public.model_dump(mode="json")
    expected["task_version"] = 2
    assert new.public.model_dump(mode="json") == expected
    assert new.private.task_version == 2
    assert new.environment == old.environment
    assert {a.path for a in new.private.hidden_artifacts} == {
        "hidden/test_timeout_behavior.py",
    }
    assert new.task_content_hash != old.task_content_hash


@pytest.mark.parametrize("missing", [False, True])
def test_hidden_bytes_cannot_be_changed_or_missing(tmp_path, missing):
    target = tmp_path / "task"
    shutil.copytree(TASK, target)
    path = target / "hidden/test_timeout_behavior.py"
    if missing:
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n# changed\n")
    with pytest.raises(ContractError, match="hidden artifact"):
        load_task_package(target)


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_private_behavior_is_not_projected(policy):
    package = load_task_package(TASK)
    result = assemble_model_input(
        system_prompt="Public task only.",
        state={"public_task": package.public.model_dump(mode="json"),
               "current_diff": {"patch": ""}, "visible_check_status": {}},
        history=[], context_policy=policy,
    )
    raw = canonical_json(result)
    for marker in ("test_timeout_behavior", "hop_configuration_is_independent",
                   package.private_spec_hash, package.private.reference_patch.sha256):
        assert marker not in raw
