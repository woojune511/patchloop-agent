"""Small controls for observation identity, currency and optional replay guidance."""

import copy
from types import SimpleNamespace

import pytest

from patchloop.dev import probe_followup
from patchloop.dev.runner import _reproduction_review_resources
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import sha256_bytes, sha256_json

SOURCE = "print('observed value')"
QUESTION = "Does the public example match its expected result?"


def probe(events, action="before", diff="base", *, source=SOURCE, question=QUESTION,
          status="succeeded", partial=False, pending=False, **output):
    args = {"question": question, "python_source": source, "purpose": {"kind": "helper"},
            "replay_action_id": None}
    input_hash = sha256_json({"tool": "run_probe", "arguments": args})
    events.append({"event_type": "action_started", "payload": {
        "action_id": action, "tool": "run_probe", "arguments": args,
        "input_hash": input_hash, "baseline_diff_hash": diff}})
    if not pending:
        events.append({"event_type": "action_finished", "payload": {"action_id": action, "result": {
            "action_id": action, "tool": "run_probe", "status": status,
            "input_hash": input_hash, "workspace_diff_hash": diff, "output": {
                "question": question, "source_hash": sha256_bytes(source.encode()),
                "diff_hash": diff, "status": "output_limit" if partial else "passed",
                "exit_code": 0, "truncated": partial, "stdout": "observed value\n",
                "stderr": "", "profile_hash": "public-profile",
                "execution_policy": {"cleanup_status": "confirmed"}, **output}}}})


def mutation(events, action="edit", before="base", after="candidate"):
    events.append({"event_type": "action_finished", "payload": {"result": {
        "action_id": action, "tool": "replace_text", "status": "succeeded",
        "workspace_diff_hash": after,
        "output": {"baseline_diff_hash": before, "worktree_diff_hash": after}}}})


def baseline():
    events = []
    probe(events)
    mutation(events)
    return events


def test_pre_edit_observation_survives_edit_and_unrelated_check_without_success_credit():
    events = baseline()
    before = copy.deepcopy(events)
    card = probe_followup.review(events, "candidate")
    assert card["baseline"]["diff_hash"] == "base"
    assert card["baseline"]["observation"]["stdout"] == "observed value\n"
    assert card["candidate"] == {"status": "not_run", "observation": None}
    assert card["replay"]["reference_valid"] is True
    assert card["behavior_verdict"] == card["requirement_coverage"] == "not_assessed"
    assert events == before
    events.append({"event_type": "action_finished", "payload": {"result": {
        "tool": "run_check", "action_id": "check", "status": "succeeded",
        "workspace_diff_hash": "candidate", "output": {"passed": True}}}})
    assert probe_followup.review(events, "candidate") == card


def test_current_same_program_observation_then_another_edit_renews_currency_only():
    events = baseline()
    probe(events, "after", "candidate", exit_code=1)
    card = probe_followup.review(events, "candidate")
    assert card["candidate"]["status"] == "observed"
    assert card["candidate"]["observation"]["action_id"] == "after"
    assert card["candidate"]["observation"]["observation"]["exit_code"] == 1
    assert card["behavior_verdict"] == "not_assessed"
    mutation(events, "second-edit", "candidate", "second")
    card = probe_followup.review(events, "second")
    assert card["baseline"]["action_id"] == "after"
    assert card["candidate"]["status"] == "not_run"


@pytest.mark.parametrize("variation", [
    {"source": "print('a different question')"}, {"question": "Different question"},
    {"status": "failed"},
])
def test_unrelated_or_rejected_actions_do_not_answer_the_retained_question(variation):
    events = baseline()
    probe(events, "different", "candidate", **variation)
    assert probe_followup.review(events, "candidate")["candidate"]["status"] == "not_run"


def test_partial_and_pending_execution_remain_distinct_from_observed():
    events = baseline()
    probe(events, "partial", "candidate", partial=True, stdout="X" * 3_000)
    card = probe_followup.review(events, "candidate")
    assert card["candidate"]["status"] == "partial"
    observed = card["candidate"]["observation"]["observation"]
    assert observed["truncated"] is True
    assert len(observed["stdout"]) == 1_000 and observed["stdout_omitted_chars"] == 2_000
    probe(events, "pending", "candidate", pending=True)
    card = probe_followup.with_guidance(probe_followup.review(events, "candidate"),
        offered=True, restricted=False, probe_policy="none")
    assert card["candidate"]["status"] == "unresolved"
    assert card["replay"]["arguments"] is None
    assert card["replay"]["reason"] == "execution_unresolved"


@pytest.mark.parametrize("damage", ["cleanup", "identity"])
def test_unusable_reference_is_retained_but_not_suggested(damage):
    events = baseline()
    result = events[1]["payload"]["result"]
    if damage == "cleanup":
        result["output"]["execution_policy"]["cleanup_status"] = "failed"
    else:
        result["input_hash"] = "wrong-identity"
    card = probe_followup.with_guidance(probe_followup.review(events, "candidate"),
        offered=True, restricted=False, probe_policy="none")
    assert not card["replay"]["reference_valid"]
    assert card["replay"]["reason"] == "reference_unavailable"
    assert card["replay"]["arguments"] is None


@pytest.mark.parametrize("damage", ["input_hash", "output_diff"])
def test_current_result_needs_the_same_start_finish_identity_checks(damage):
    events = baseline()
    probe(events, "after", "candidate")
    result = events[-1]["payload"]["result"]
    if damage == "input_hash":
        result["input_hash"] = "wrong-identity"
    else:
        result["output"]["diff_hash"] = "other-diff"
    card = probe_followup.with_guidance(probe_followup.review(events, "candidate"),
        offered=True, restricted=False, probe_policy="none")
    assert card["candidate"]["status"] == "unresolved"
    assert card["replay"]["arguments"] is None
    assert card["behavior_verdict"] == "not_assessed"


@pytest.mark.parametrize("probe_policy", ["none", "cases-v1", "reference-cases-v1"])
@pytest.mark.parametrize("agent_policy", ["current", "thin"])
def test_replay_arguments_fit_the_offered_schema_and_existing_resolver(probe_policy, agent_policy):
    events = baseline()
    policy = SimpleNamespace(workflow_gate="ready_to_submit", allowed_tools={"run_probe"},
                             verification_policy="public-checks-v1")
    card = _reproduction_review_resources({"probe_followup": probe_followup.review(
        events, "candidate")}, policy, probe_policy=probe_policy)["probe_followup"]
    schema, = dev_tool_schemas(finish_enabled=False, allowed_tools={"run_probe"},
                              probe_policy=probe_policy, agent_policy=agent_policy)
    args = card["replay"]["arguments"]
    assert set(args) == set(schema["parameters"]["required"]) - {"turn_decision", "memory_update"}
    from patchloop.dev.probe_replay import prepare

    assert prepare(args, events)["python_source"] == SOURCE
    assert ("save_program" in args) == (probe_policy == "cases-v1")


@pytest.mark.parametrize("gate,offered,correction", [
    ("needs_path_diagnosis", True, None), ("needs_original_reproduction", True, None),
    ("needs_original_argument_correction", True, None),
    ("needs_helper_correction", True, {"blocked": True}),
    ("ready_to_submit", True, {"blocked": True}), ("ready_to_submit", False, None),
])
def test_restricted_stages_never_advertise_general_replay(gate, offered, correction):
    policy = SimpleNamespace(workflow_gate=gate, allowed_tools={"run_probe"} if offered else set(),
        verification_policy="reproduction-gated-v1", helper_correction=correction,
        observation_correction=None)
    original = {"probe_followup": probe_followup.review(baseline(), "candidate")}
    card = _reproduction_review_resources(original, policy)["probe_followup"]
    assert not card["replay"]["available"] and card["replay"]["arguments"] is None
    assert original["probe_followup"]["replay"]["reason"] == "tool_policy_not_projected"


def test_absent_helper_or_unmatched_current_mutation_adds_no_card():
    assert probe_followup.review([], "candidate") is None
    events = []
    probe(events)
    assert probe_followup.review(events, "base") is None
    assert probe_followup.review(baseline(), "untracked-change") is None


@pytest.mark.parametrize("agent_policy,old_hash", [
    ("current", "61a5d78e47a16753c29733960df9d3be2a8409d47952af27869dbdfeeb2807c5"),
    ("thin", "768208cc2c663c07f212cb78db69a88d3bedaa3e79092aab0657b40b83ea9c3b"),
])
def test_general_probe_guidance_changes_no_argument_schema_or_other_tool(agent_policy, old_hash):
    schemas = dev_tool_schemas(finish_enabled=False, allowed_tools={"run_probe", "stop_task"},
                               agent_policy=agent_policy)
    tool = next(row for row in schemas if row["name"] == "run_probe")
    before = tool["description"]
    tool["description"] = before.replace(
        "After an edit, replay a relevant prior public example to test the repair's "
        "effect; for a new question, choose an input that could falsify an assumption. "
        "Keep caller, input representation and setup comparable. A changed-input "
        "failure is a separate diagnosis even when the error text matches. "
        "For helper probes, state the expected ",
        "Choose a public input variation that could falsify an implementation assumption, "
        "not just repeat a registered example. For helper probes, state the expected ",
    )
    assert before != tool["description"]
    assert sha256_json(schemas) == "sha256:" + old_hash
