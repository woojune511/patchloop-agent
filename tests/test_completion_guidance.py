"""Local seed and request contracts; no provider or sandbox execution."""
from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from diagnostics import completion_guidance as guidance
from patchloop.artifacts import ArtifactStore
from patchloop.dev import completion_context, runner, segments
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json


def make_branch(root, *, completion=True, pending=True):
    journal, store = DevJournal(root, "run_dev_guidance"), ArtifactStore(root / "artifacts")
    state = {
        "public_task": {"task_id": "public-fixture", "issue": "Repair the public behavior."},
        "workflow_gate": "ready_to_submit" if completion else "needs_edit",
        "remaining_budget": {"model_calls": 6, "tool_actions": 14, "accepted_mutations": 2},
        "latest_tool_results": [], "current_diff": {"patch_hash": "sha256:candidate"},
    }
    base = runner.segment_seed(guidance.BASELINE_PROMPT, state["public_task"],
                               agent_policy="thin", diagnosis=True)
    with journal.execution_lock():
        segments.start(journal, store, base=base, state=state, reason="previous",
                       parent_input_artifact=None, agent_policy="thin")
        if pending:
            segments.start(journal, store, base=base, state=state,
                           reason="completion_stage_entered", parent_input_artifact=None,
                           agent_policy="thin", prepare=True, replace_pending=True,
                           evidence_manifest={"optional_action_ids": [], "question": None})
        inherited = journal.events()
        marker = {"parent_prefix_hash": inherited[-1]["event_hash"]}
        journal.append("observation_exposure_fork", marker)
    return SimpleNamespace(
        journal=journal, store=store, references={}, inherited_events=len(inherited),
        marker_hash=sha256_json(marker), request=SimpleNamespace(
            segment_boundary_policy=segments.DEFAULT_BOUNDARY_POLICY, agent_policy="thin",
        ),
    )


def test_install_preserves_prefix_state_and_native_binding(tmp_path):
    branch = make_branch(tmp_path / "branch")
    before = branch.journal.path.read_bytes()
    old_binding, old_handoff = segments.active(branch.journal, branch.store)
    receipt = guidance.install(branch)
    binding, handoff = segments.active(branch.journal, branch.store)
    assert branch.journal.path.read_bytes().startswith(before)
    assert branch.completion_guidance == "investigate-v1"
    assert binding != old_binding and binding["state_hash"] == old_binding["state_hash"]
    assert segments.load_binding(old_binding, branch.store) == old_handoff
    assert handoff["state"] == old_handoff["state"]
    assert handoff["evidence_manifest"] == old_handoff["evidence_manifest"]
    assert handoff["base"][1:] == old_handoff["base"][1:]
    suffix = old_handoff["base"][0]["content"][len(guidance.BASELINE_PROMPT):]
    assert handoff["base"][0]["content"] == guidance.INVESTIGATE_PROMPT + suffix
    assert receipt["new_provider_calls"] == receipt["new_target_executions"] == 0
    items = runner.assemble_model_input(
        system_prompt=guidance.INVESTIGATE_PROMPT, state=handoff["state"], history=[],
        previous_input=handoff["base"], context_policy=segments.POLICY,
    )
    metadata = {"binding": binding, "previous_input_artifact": None}
    segments.validate_input_binding(items, metadata, branch.store)
    saved = branch.store.put_json(items)
    continuation = runner.assemble_model_input(
        system_prompt=guidance.INVESTIGATE_PROMPT, state=handoff["state"], history=[],
        previous_input=items, context_policy=segments.POLICY,
    )
    segments.validate_input_binding(continuation, {
        "binding": binding, "previous_input_artifact": saved.model_dump(mode="json"),
    }, branch.store)
    changed = copy.deepcopy(items)
    changed[0]["content"] = old_handoff["base"][0]["content"]
    with pytest.raises(RecoveryError, match="seed prefix"):
        segments.validate_input_binding(changed, metadata, branch.store)


def test_baseline_is_noop(tmp_path):
    branch = make_branch(tmp_path / "branch")
    before = branch.journal.path.read_bytes()
    assert guidance.install(branch, "baseline")["changed"] is False
    assert branch.journal.path.read_bytes() == before
    assert branch.completion_guidance == "baseline"


@pytest.mark.parametrize("completion,pending", [(False, True), (True, False)])
def test_rejects_noncompletion_or_committed_seed(tmp_path, completion, pending):
    branch = make_branch(tmp_path / "branch", completion=completion, pending=pending)
    before = branch.journal.path.read_bytes()
    with pytest.raises(ContractError, match="completion seed"):
        guidance.install(branch)
    assert branch.journal.path.read_bytes() == before


@pytest.mark.parametrize("event", ["input_count_started", "provider_call_started",
                                  "checkpoint_helper_replay_attached"])
def test_install_must_precede_feedback_and_provider_work(tmp_path, event):
    branch = make_branch(tmp_path / "branch")
    branch.journal.append(event, {})
    before = branch.journal.path.read_bytes()
    with pytest.raises(ContractError, match="must precede"):
        guidance.install(branch)
    assert branch.journal.path.read_bytes() == before


def test_activation_restores_module_even_on_failure(tmp_path):
    branch = make_branch(tmp_path / "branch")
    guidance.install(branch)
    original = completion_context.SYSTEM_PROMPT
    with pytest.raises(RuntimeError), guidance.activate(branch):
        assert completion_context.SYSTEM_PROMPT == guidance.INVESTIGATE_PROMPT
        raise RuntimeError("test exit")
    assert completion_context.SYSTEM_PROMPT == original == guidance.BASELINE_PROMPT
    with guidance.activate(SimpleNamespace(completion_guidance="baseline")):
        assert original == completion_context.SYSTEM_PROMPT


def pair():
    common = {"tools": [{"name": "run_probe"}, {"name": "finish_task"}],
              "max_output_tokens": 40000,
              "input": [{"role": "system", "content": ""},
                        {"role": "developer", "content": "same public state"}]}
    left, right = copy.deepcopy(common), copy.deepcopy(common)
    for request, variant in ((left, "baseline"), (right, "investigate-v1")):
        request["input"][0]["content"] = guidance.selected_prompt(variant) + "\nexact suffix"
    return left, right


def test_pair_only_removes_exact_prompt_and_keeps_inputs_unchanged():
    left, right = pair()
    before = copy.deepcopy((left, right))
    assert guidance.assert_pair(left, right)["status"] == "PASS"
    assert (left, right) == before


@pytest.mark.parametrize("changed", ["tools", "state", "suffix", "output_limit"])
def test_pair_rejects_other_changes(changed):
    left, right = pair()
    if changed == "tools":
        right["tools"].pop()
    elif changed == "state":
        right["input"][1]["content"] = "other public state"
    elif changed == "suffix":
        right["input"][0]["content"] += " extra instruction"
    else:
        right["max_output_tokens"] -= 1
    with pytest.raises(ContractError, match="beyond the exact"):
        guidance.assert_pair(left, right)
