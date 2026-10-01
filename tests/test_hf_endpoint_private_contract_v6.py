"""Versioned behavior evaluation must remain private and byte-bound."""

import shutil

import pytest

from patchloop.dev.conversation import assemble_model_input
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

TASK = repository_root() / "tasks/dev-train/hf-hub-xet-endpoint-propagation-v6"


def test_v6_preserves_public_behavior_and_binds_hidden_inventory():
    old = load_task_package(TASK.with_name(TASK.name[:-1] + "5"))
    new = load_task_package(TASK)
    assert new.public.task_version == new.private.task_version == 6
    assert new.public.issue == old.public.issue
    assert new.public.repository == old.public.repository
    assert new.public.constraints == old.public.constraints
    assert new.public.visible_checks == old.public.visible_checks
    assert new.environment == old.environment
    assert new.private.schema_version == "task-private-v2"
    assert {a.path for a in new.private.hidden_artifacts} == {
        "hidden/http_fixture.py", "hidden/test_endpoint_behavior.py",
    }
    assert new.private.hidden_checks[0].infrastructure_exit_codes == [2]
    assert new.task_content_hash != old.task_content_hash


@pytest.mark.parametrize("name", ["http_fixture.py", "test_endpoint_behavior.py"])
@pytest.mark.parametrize("missing", [False, True])
def test_evaluator_bytes_cannot_be_missing_or_changed(tmp_path, name, missing):
    target = tmp_path / "task"
    shutil.copytree(TASK, target)
    path = target / "hidden" / name
    if missing:
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"\n# changed\n")
    with pytest.raises(ContractError, match="hidden artifact"):
        load_task_package(target)


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_hidden_behavior_contract_is_not_projected(policy):
    package = load_task_package(TASK)
    result = assemble_model_input(
        system_prompt="Public task only.",
        state={"public_task": package.public.model_dump(mode="json"),
               "current_diff": {"patch": ""}, "visible_check_status": {}},
        history=[], context_policy=policy,
    )
    raw = canonical_json(result)
    for marker in ("test_endpoint_behavior", "http_fixture", "isolated-mirror",
                   package.private_spec_hash, package.private.reference_patch.sha256):
        assert marker not in raw
