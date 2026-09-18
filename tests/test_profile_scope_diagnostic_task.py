"""The assisted diagnostic changes one public check and preserves evaluation separation."""
from __future__ import annotations

import pytest

from diagnostics.profile_scope_check import registered_check
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

PARENT = repository_root() / "tasks/dev-train/pydantic-ai-synthetic-tool-reasoning"
TASK = PARENT.with_name("pydantic-ai-profile-scope-diagnostic")


def test_only_public_identity_and_additional_contrast_change():
    parent = load_task_package(PARENT)
    diagnostic = load_task_package(TASK)
    public = diagnostic.public.model_dump(mode="json")
    assert public.pop("task_id") == TASK.name
    assert public["visible_checks"].pop() == registered_check().model_dump(mode="json")
    expected = parent.public.model_dump(mode="json")
    expected.pop("task_id")
    assert public == expected
    assert diagnostic.environment == parent.environment
    assert diagnostic.task_content_hash != parent.task_content_hash


def test_private_support_is_an_opaque_copy_with_only_identity_changed():
    parent_private = (PARENT / "private.yaml").read_bytes()
    expected = parent_private.replace(
        f"task_id: {PARENT.name}".encode(), f"task_id: {TASK.name}".encode(),
    )
    assert (TASK / "private.yaml").read_bytes() == expected
    for path in PARENT.rglob("*"):
        if path.is_file() and path.name not in {"public.yaml", "private.yaml", "audit.md"}:
            assert (TASK / path.relative_to(PARENT)).read_bytes() == path.read_bytes()


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_added_contrast_is_public_but_private_artifacts_remain_excluded(policy):
    task = load_task_package(TASK)
    state = {"public_task": task.public.model_dump(mode="json"),
             "current_diff": {"patch": ""}, "visible_check_status": {}}
    projected = assemble_model_input(system_prompt="Public task only.", state=state,
                                     history=[], context_policy=policy)
    recovered = reconstruct_state(projected, context_policy=policy)
    assert recovered == state
    assert recovered["public_task"]["visible_checks"][-1] == registered_check().model_dump(
        mode="json",
    )
    serialized = canonical_json(projected)
    assert task.private_spec_hash not in serialized
    assert task.private.reference_patch.path not in serialized
    for artifact in task.private.hidden_artifacts:
        assert artifact.path not in serialized
        assert artifact.sha256 not in serialized
