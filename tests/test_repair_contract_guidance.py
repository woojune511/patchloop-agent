"""Public repair guidance survives actual policy and compact-stage delivery."""

import copy

import pytest
from test_dev_probes import FakeProbe, context, probe_call
from test_dev_tools import read_calls

from patchloop.artifacts import ArtifactStore
from patchloop.dev import completion_context, repair_context, runner, thin_policy, working_plan
from patchloop.dev.contracts import (
    FileEditIntent,
    PublicTurnDecision,
    RequestedTool,
    TextReplacementIntent,
)
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.probe_observation import project_probe_result
from patchloop.dev.repair_guidance import (
    EXPECTED_BEHAVIOR_DESCRIPTION,
    HYPOTHESIS_DESCRIPTION,
    INSTRUCTIONS,
)
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.util import canonical_json, sha256_bytes


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
    for guidance in (
        "compare inputs/setup/assertions with current-diff results",
        "new cases, incomplete observations or post-edit rechecks in basis if offered",
        "no host judgment, not an unfinished case",
    ):
        assert guidance in request[0]["content"]
    actual = reconstruct_state(request, context_policy=context_policy)
    for key in ("workflow_gate", "available_tool_names", "remaining_budget"):
        assert actual[key] == state[key]
    assert actual["completion_guidance"]["verification_policy"] == verification_policy
    assert actual["public_task"] == state["public_task"]


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("agent_policy", ["current", "thin"])
def test_initial_repair_delivers_correspondence_with_distinct_helper_and_control_evidence(
    gateway_factory, smoke_package, context_policy, agent_policy,
):
    """Test real request transport with canned observations, not CSV/model correctness."""
    helper_source = (
        "from mini_data_utils.csvlite import parse_rows\n"
        "parse_rows(['\"left', 'right\",tail'])\n"
    )
    control_source = (
        "from mini_data_utils.csvlite import parse_rows\n"
        "assert parse_rows('plain,tail') == [['plain', 'tail']]\n"
    )
    observations = {
        helper_source: ("failed", "", "TypeError: expected text, got list\n"),
        control_source: ("passed", "ordinary text control passed\n", ""),
    }

    class RecordedProbe(FakeProbe):
        def run_probe(self, workspace, question, python_source, **kwargs):
            self.status, stdout, stderr = observations[python_source]
            result = super().run_probe(workspace, question, python_source, **kwargs)
            return {**result, "stdout": stdout, "stderr": stderr}

    gateway, journal, _ = gateway_factory()
    backend = gateway.probe_sandbox = RecordedProbe()
    gateway.execute_batch(read_calls())
    results = {}
    for action_id, source, question in (
        ("substituted-helper", helper_source, "Does a list of physical lines parse?"),
        ("ordinary-control", control_source, "Does ordinary text retain one CSV record?"),
    ):
        call = probe_call(action_id)
        call.arguments.update(question=question, python_source=source)
        results[action_id] = gateway.execute(call)
        assert results[action_id].status == "succeeded"
    state = context(gateway, smoke_package)
    assert state["workflow_gate"] == "needs_mutation"
    assert repair_context.pending(state)
    assert not state.get("working_plan")
    assert gateway.accepted_mutations == 0 and not gateway.current_diff.patch
    before = copy.deepcopy(state)
    with journal.execution_lock():
        request = runner._build_model_input(
            journal=journal, artifact_store=ArtifactStore(journal.root / "artifacts"),
            context=canonical_json(state), latest_tool_results=[],
            context_policy=context_policy, agent_policy=agent_policy, planning_policy="none",
        )

    prompt = request[0]["content"]
    assert prompt.startswith(repair_context.system_prompt(state))
    assert prompt.count("Preserve the input representation;") == 1
    assert prompt.count(INSTRUCTIONS) == 1
    actual = reconstruct_state(request, context_policy=context_policy)
    assert actual["public_task"] == state["public_task"]
    assert "parse_rows(text)" in actual["public_task"]["issue"]["description"]
    assert actual["current_diff"] == state["current_diff"]
    expected_sources = sorted(
        (span["path"], span["file_hash"], span["start_line"], span["end_line"], span["content"])
        for span in state["source_spans"]
    )
    delivered_sources = sorted(
        (group["path"], group["file_hash"], span["start_line"], span["end_line"], span["content"])
        for group in actual["current_sources"] for span in group.get("inline_spans", [])
    )
    assert delivered_sources == expected_sources and delivered_sources
    for key in ("available_tool_names", "workflow_gate", "visible_check_status"):
        assert actual[key] == state[key]
    assert not actual.get("working_plan")
    assert "behavior_change" not in canonical_json(actual)
    retained = {row["action_id"]: row for row in actual["recent_probes"]}
    assert set(retained) == set(results)
    for action_id, result in results.items():
        row = retained[action_id]
        source = helper_source if action_id == "substituted-helper" else control_source
        assert row["program"] == {
            "python_source": source, "source_hash": sha256_bytes(source.encode()),
        }
        assert row["diff_hash"] == result.workspace_diff_hash == gateway.current_diff_hash
        assert row["stdout"] == result.output["stdout"]
        assert row["stderr"] == result.output["stderr"]
        assert row["exit_code"] == result.output["exit_code"]
        assert row["observation"]["behavior_verdict"] == "not_assessed"
        assert row["observation"]["execution_status"] == (
            "failed" if action_id == "substituted-helper" else "completed")
    # The passing ordinary control neither supplies the multiline original case
    # nor grants visible-check credit. No probe body is executed by this fixture.
    assert gateway.checks_by_diff == {} and backend.calls == 2
    assert gateway.accepted_mutations == 0 and not gateway.current_diff.patch
    assert state == before


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("changed_diff", [False, True])
@pytest.mark.parametrize("outcome", ["passed", "timeout"])
def test_verification_reuse_guidance_and_observations_reach_fresh_completion_request(
    tmp_path, context_policy, changed_diff, outcome,
):
    """Deliver correction evidence without certifying semantics or ordering a rerun."""
    checked_diff = "sha256:" + "a" * 64
    current_diff = "sha256:" + "b" * 64 if changed_diff else checked_diff
    previous_stdout = "valid.value='ok'; invalid raised MissingItem\n"
    previous_stderr = "ValueError: exception formatting failed\n"
    current_stdout = (
        "valid.value='ok'; invalid.exception='MissingItem'; assertions_passed\n"
        if outcome == "passed" else "valid.value='ok'; invalid call has not returned\n"
    )
    latest = project_probe_result({
        "tool": "run_probe", "action_id": "corrected-probe", "status": "succeeded",
        "workspace_diff_hash": checked_diff,
        "output": {
            "status": outcome, "diff_hash": checked_diff,
            "question": "Does valid lookup succeed and invalid lookup raise MissingItem?",
            "stdout": current_stdout, "stderr": "",
            "exit_code": 0 if outcome == "passed" else None,
            "timed_out": outcome == "timeout", "truncated": False,
        },
    })
    authority = {
        "workflow_gate": "ready_to_submit",
        "available_tool_names": ["run_probe", "run_tests", "finish_task", "stop_task"],
        "remaining_budget": {"model_calls": 3, "tool_actions": 5, "accepted_mutations": 1},
    }
    state = {
        **authority,
        "public_task": {"task_id": "public-fixture", "issue": "Repair public lookup."},
        "completion_guidance": {"verification_policy": "public-checks-v1"},
        "current_diff": {"patch_hash": current_diff, "patch": "+return lookup(key)\n",
                         "changed_files": ["public_source.py"]},
        "working_notes": {"findings": [], "verification": {"items": []}},
        "current_public_failure": None,
        "recent_probes": [{
            "action_id": "logging-error-probe", "diff_hash": checked_diff,
            "historical": False, "exit_code": 1,
            "stdout": previous_stdout, "stderr": previous_stderr,
            "observation": {"execution_status": "failed", "behavior_verdict": "not_assessed"},
        }],
        "latest_tool_results": [latest],
    }
    journal = DevJournal(tmp_path, "run_dev_verificationreuse")
    with journal.execution_lock():
        request = runner._build_model_input(
            journal=journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
            context=canonical_json(state), latest_tool_results=[],
            context_policy=context_policy, planning_policy="none",
        )
    assert request[0]["content"].count(INSTRUCTIONS) == 1
    actual = reconstruct_state(request, context_policy=context_policy)
    for key, value in authority.items():
        assert actual[key] == value
    assert actual["current_public_failure"] is None
    if changed_diff:
        # An old success or partial result cannot be reused on the edited candidate.
        assert current_stdout not in canonical_json(actual)
        assert previous_stdout not in canonical_json(actual)
        assert "observation" not in actual["latest_tool_results"][0]
    else:
        # The model receives both the probe error and its correction; the host does
        # not silently clear a failure or claim that exit zero answers the question.
        previous = actual["recent_probes"][0]
        assert previous["stdout"] == previous_stdout
        assert previous["stderr"] == previous_stderr
        assert previous["observation"]["execution_status"] == "failed"
        retained = actual["latest_tool_results"][0]
        assert retained["output"]["stdout"] == current_stdout
        assert retained["output"]["exit_code"] == (0 if outcome == "passed" else None)
        assert retained["observation"]["behavior_verdict"] == "not_assessed"
        assert retained["observation"]["execution_status"] == (
            "completed" if outcome == "passed" else "timeout")


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
    intents = {"replace_text": TextReplacementIntent, "edit_files": FileEditIntent}
    descriptions = {
        "hypothesis": HYPOTHESIS_DESCRIPTION,
        "expected_behavior": EXPECTED_BEHAVIOR_DESCRIPTION,
    }
    for name, fields in expected_fields.items():
        parameters = by_name[name]["parameters"]
        assert set(parameters["properties"]) == fields
        assert set(parameters["required"]) == fields
        assert parameters["additionalProperties"] is False
        for field in ("hypothesis", "expected_behavior"):
            assert parameters["properties"][field]["minLength"] == 1
            assert parameters["properties"][field]["maxLength"] == 1_500
            assert descriptions[field].strip()
            assert parameters["properties"][field]["description"] == descriptions[field]
            assert intents[name].model_json_schema()["properties"][field]["description"] == (
                descriptions[field])


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
