"""Public repair guidance survives actual policy and compact-stage delivery."""

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.dev import completion_context, repair_context, runner, thin_policy
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.repair_guidance import INSTRUCTIONS
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("agent_policy", ["current", "thin"])
@pytest.mark.parametrize("verification_policy", ["public-checks-v1", "reproduction-gated-v1"])
@pytest.mark.parametrize("stage,gate", [
    ("general", "needs_visible_checks"),
    ("repair", "needs_mutation"),
    ("completion", "ready_to_submit"),
])
def test_actual_request_keeps_shared_guidance_and_existing_authority(
    tmp_path, context_policy, agent_policy, verification_policy, stage, gate,
):
    tools = ["replace_text", "edit_files", "run_check", "stop_task"]
    if stage == "completion":
        tools.append("finish_task")
    state = {
        "public_task": {"task_id": "public-fixture", "issue": "Repair the public behavior."},
        "workflow_gate": gate,
        "completion_guidance": {"verification_policy": verification_policy},
        "available_tool_names": tools,
        "remaining_budget": {"model_calls": 3, "tool_actions": 5, "accepted_mutations": 1},
        "current_diff": {"patch_hash": "sha256:" + "a" * 64,
                         "patch": "-return old\n+return new\n",
                         "changed_files": ["public_source.py"]},
        "working_notes": {"findings": [], "verification": {"items": []}},
        "latest_tool_results": [],
    }
    expected = (
        completion_context.SYSTEM_PROMPT if stage == "completion" else
        repair_context.system_prompt(state) if stage == "repair" else
        thin_policy.system_prompt(agent_policy, verification_policy=verification_policy)
    )
    journal = DevJournal(tmp_path, "run_dev_contractguidance")
    with journal.execution_lock():
        request = runner._build_model_input(
            journal=journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
            context=canonical_json(state), latest_tool_results=[],
            context_policy=context_policy, agent_policy=agent_policy,
        )

    # Exercise the real runner selector rather than composing a chosen prompt by hand.
    assert request[0]["role"] == "system"
    assert request[0]["content"].startswith(expected)
    assert request[0]["content"].count(INSTRUCTIONS) == 1
    actual = reconstruct_state(request, context_policy=context_policy)
    for key in ("workflow_gate", "available_tool_names", "remaining_budget"):
        assert actual[key] == state[key]
    assert actual["completion_guidance"]["verification_policy"] == verification_policy
    assert actual["public_task"] == state["public_task"]


@pytest.mark.parametrize("agent_policy", ["current", "thin"])
@pytest.mark.parametrize("verification_policy", ["public-checks-v1", "reproduction-gated-v1"])
def test_guidance_uses_existing_intents_for_both_mutation_tools(
    agent_policy, verification_policy,
):
    schemas = dev_tool_schemas(
        finish_enabled=False, allowed_tools=["replace_text", "edit_files"],
        agent_policy=agent_policy, verification_policy=verification_policy,
    )
    by_name = {schema["name"]: schema for schema in schemas}
    assert set(by_name) == {"replace_text", "edit_files"}
    expected_fields = {
        "replace_text": {"path", "old_text", "new_text", "occurrence",
                         "hypothesis", "expected_behavior"},
        "edit_files": {"edits", "undo_action_id", "hypothesis", "expected_behavior"},
    }
    for name, fields in expected_fields.items():
        parameters = by_name[name]["parameters"]
        assert set(parameters["properties"]) == fields
        assert set(parameters["required"]) == fields
        assert parameters["additionalProperties"] is False
        for field in ("hypothesis", "expected_behavior"):
            assert parameters["properties"][field]["minLength"] == 1
            assert parameters["properties"][field]["maxLength"] == 1_500
