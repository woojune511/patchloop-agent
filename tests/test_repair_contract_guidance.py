"""Public repair guidance survives actual policy and compact-stage delivery."""

import pytest

from patchloop.artifacts import ArtifactStore
from patchloop.dev import completion_context, repair_context, runner, thin_policy, working_plan
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.repair_guidance import INSTRUCTIONS
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
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


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_post_edit_contract_survives_pass_and_setup_only_probe_until_completion(
    tmp_path, context_policy,
):
    """Authored cases stay unverified; transport cannot infer a checked property."""
    diff = "sha256:" + "c" * 64
    journal = DevJournal(tmp_path, "run_dev_contractreview")
    store = ArtifactStore(tmp_path / "artifacts")

    def decision(text, action, *, finish=False):
        return RequestedTool(
            name="finish_task" if finish else "read_file", action_id=action, arguments={},
            turn_decision=PublicTurnDecision(
                mode="finish" if finish else "inspect", basis="Public fixture contract.",
                evidence_goal=None if finish else "Distinguish a wrong success result.",
                plan_update=text,
                plan_update_reason="Retain the untested input and observable outcome.",
            ),
        )

    working_plan.record(
        journal, [decision("Inspect the public return contract.", "initial-plan")],
        turn_id="initial", diff_hash="original", gate="needs_mutation",
    )
    journal.append("action_finished", {"result": {
        "tool": "edit_files", "status": "succeeded", "action_id": "edit",
        "workspace_diff_hash": diff, "output": {},
    }})
    authority = {
        "available_tool_names": ["read_file", "run_check", "run_probe", "finish_task", "stop_task"],
        "remaining_budget": {"model_calls": 3, "tool_actions": 5, "accepted_mutations": 1},
    }
    state = {
        **authority,
        "public_task": {"task_id": "public-fixture", "issue": "Preserve the public contract."},
        "workflow_gate": "needs_visible_checks",
        "completion_guidance": {"verification_policy": "public-checks-v1"},
        "current_diff": {"patch_hash": diff, "patch": "-return old\n+return new\n",
                         "changed_files": ["public_source.py"]},
        "working_notes": {"findings": [], "verification": {"items": []}},
        "latest_tool_results": [],
        "working_plan": working_plan.project(
            journal.events(), diff_hash=diff, gate="needs_visible_checks",
        ),
    }
    assert state["working_plan"]["review_request"]["reasons"] == ["mutation_result"]
    with journal.execution_lock():
        post_edit = runner._build_model_input(
            journal=journal, artifact_store=store, context=canonical_json(state),
            latest_tool_results=[], context_policy=context_policy,
            planning_policy=working_plan.POLICY,
        )
    # The selected brief-v1 plan guidance reaches the actual next useful response.
    assert post_edit[0]["content"].count(working_plan.instructions()) == 1

    plan_text = (
        "Required public contract: a failed match retains the input. "
        "Repair-introduced assumption: the new early success obeys the documented minimum. "
        "Refuting setup: one item below that minimum, with a valid control. "
        "Observe success=false and unchanged returned input separately. "
        "Next choice: test this important assumption before relying on the early return. "
        "UNTESTED: setup existence does not establish either behavior."
    )
    working_plan.record(
        journal, [decision(plan_text, "contract-plan")], turn_id="post-edit",
        diff_hash=diff, gate="needs_visible_checks",
    )
    for tool, action, output in (
        ("run_check", "suite-pass", {"passed": True, "exit_code": 0}),
        ("run_probe", "setup-probe", {"exit_code": 0, "stdout": "setup_exists=True"}),
    ):
        journal.append("action_finished", {"result": {
            "tool": tool, "status": "succeeded", "action_id": action,
            "workspace_diff_hash": diff, "output": output,
        }})
    state["workflow_gate"] = "ready_to_submit"
    state["working_plan"] = working_plan.project(
        journal.events(), diff_hash=diff, gate="ready_to_submit",
    )
    state["recent_probes"] = [{
        "action_id": "setup-probe", "diff_hash": diff, "exit_code": 0,
        "question": "Does failure preserve the input?", "stdout": "setup_exists=True",
        "observation": {"behavior_verdict": "not_assessed"},
    }]
    with journal.execution_lock():
        completion = runner._build_model_input(
            journal=journal, artifact_store=store, context=canonical_json(state),
            latest_tool_results=[], context_policy=context_policy,
            planning_policy=working_plan.POLICY,
        )
    actual = reconstruct_state(completion, context_policy=context_policy)
    assert actual["working_plan"]["plan"]["text"] == plan_text
    assert actual["working_plan"]["interpretation_status"] == "model_authored_unverified"
    assert set(actual["working_plan"]["review_request"]["reasons"]) >= {
        "check_result", "probe_result", "first_ready_to_submit",
    }
    assert actual["recent_probes"][0]["stdout"] == "setup_exists=True"
    assert actual["recent_probes"][0]["observation"]["behavior_verdict"] == "not_assessed"
    assert completion[0]["content"].count(INSTRUCTIONS) == 1
    for key, value in authority.items():
        assert actual[key] == value

    # Guidance cannot become a required schema, probe quota or submission gate.
    finish = decision(None, "finish", finish=True)
    assert validate_tool_batch([finish]) == "single_action"
    receipt = working_plan.record(
        journal, [finish], turn_id="finish", diff_hash=diff, gate="ready_to_submit",
    )
    assert receipt["status"] == "not_requested"
    submission = working_plan.submission_review(journal.events(), diff)
    assert submission["plan"]["text"] == plan_text
    assert submission["verification_status"] == "not_inferred_from_submission"


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_narrowed_plan_keeps_required_contract_and_revision_reason_unverified(
    tmp_path, context_policy,
):
    """Transport an authored narrowing decision without certifying its judgment."""
    journal = DevJournal(tmp_path, "run_dev_narrowingreview")
    broad_diff, narrow_diff = "sha256:" + "b" * 64, "sha256:" + "d" * 64
    original_plan = (
        "Required contract: reject a malformed item without losing its input. "
        "Repair-introduced assumption: accepting empty items is also necessary. "
        "Untested: compare empty-item acceptance and retained input with a normal control."
    )
    narrow_plan = (
        "Required contract remains: reject a malformed item without losing its input. "
        "Remove the optional empty-item acceptance change and retain its existing path. "
        "Untested on the narrowed diff: malformed-item rejection and complete input retention. "
        "Next action: run the required check; observe both outcomes before claiming them."
    )
    reason = (
        "The public contract does not require accepting empty items. Remove that extension "
        "instead of carrying its new acceptance assumption; the malformed-item obligation "
        "is unchanged and remains untested on the narrowed diff."
    )

    def record_plan(text, action, diff, revision_reason=None):
        return working_plan.record(
            journal, [RequestedTool(
                name="run_check", action_id=action,
                arguments={"check_id": "public-check"},
                turn_decision=PublicTurnDecision(
                    mode="verify", basis="Check the remaining public contract.",
                    plan_update=text, plan_update_reason=revision_reason,
                ),
            )], turn_id=action, diff_hash=diff, gate="needs_visible_checks",
        )

    record_plan(original_plan, "broad-plan", broad_diff)
    journal.append("action_finished", {"result": {
        "tool": "run_check", "status": "succeeded", "action_id": "old-check",
        "workspace_diff_hash": broad_diff, "output": {"passed": True, "exit_code": 0},
    }})
    journal.append("action_finished", {"result": {
        "tool": "edit_files", "status": "succeeded", "action_id": "narrow-edit",
        "workspace_diff_hash": narrow_diff, "output": {},
    }})
    assert record_plan(narrow_plan, "narrow-plan", narrow_diff, reason)["status"] == "updated"
    authority = {
        "available_tool_names": ["edit_files", "read_file", "run_check", "stop_task"],
        "remaining_budget": {"model_calls": 3, "tool_actions": 5, "accepted_mutations": 1},
        "workflow_gate": "needs_visible_checks",
        "visible_check_status": [{
            "check_id": "public-check", "diff_hash": narrow_diff, "status": "NOT_RUN",
        }],
    }
    state = {
        **authority,
        "public_task": {"task_id": "public-fixture", "issue": "Reject without input loss."},
        "completion_guidance": {"verification_policy": "public-checks-v1"},
        "current_diff": {"patch_hash": narrow_diff, "patch": "-drop(item)\n+reject(item)\n",
                         "changed_files": ["public_source.py"]},
        "working_notes": {"findings": [], "verification": {"items": []}},
        "latest_tool_results": [],
        "working_plan": working_plan.project(
            journal.events(), diff_hash=narrow_diff, gate="needs_visible_checks",
        ),
    }
    with journal.execution_lock():
        request = runner._build_model_input(
            journal=journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
            context=canonical_json(state), latest_tool_results=[], context_policy=context_policy,
            planning_policy=working_plan.POLICY,
        )
    actual = reconstruct_state(request, context_policy=context_policy)
    plan = actual["working_plan"]["plan"]
    assert plan["text"] == narrow_plan and plan["diff_hash"] == narrow_diff
    assert plan["last_change"]["previous_plan"]["text"] == original_plan
    assert plan["last_change"]["previous_plan"]["diff_hash"] == broad_diff
    assert plan["last_change"]["reason"] == reason
    assert plan["last_change"]["interpretation_status"] == "model_authored_unverified"
    assert request[0]["content"].count(INSTRUCTIONS) == 1
    assert request[0]["content"].count(working_plan.instructions()) == 1
    for key, value in authority.items():
        assert actual[key] == value
    assert working_plan.submission_review(journal.events(), narrow_diff)[
        "verification_status"
    ] == "not_inferred_from_submission"
