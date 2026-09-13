"""Provider-free lifecycle/advice comparison; mock execution is not case repair."""
from __future__ import annotations

import copy
import json
import socket
from dataclasses import fields

import pytest
from test_counterexample_review_rollout import Adapter, Checks, action
from test_dev_probes import FakeProbe, probe_call
from test_dev_tools import mutation_call
from test_failure_given_repair_rollout import (
    CaseProbe,
    dispatch,
    mock_plan,
    prepare,
    reopen,
)
from test_failure_given_repair_rollout import factory as feedback_factory  # noqa: F401

from diagnostics import report_verification_review as rollout
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.conversation import reconstruct_state
from patchloop.util import canonical_json, sha256_bytes, utc_now


def as_review_branch(branch):
    return rollout.Branch(**{f.name: getattr(branch, f.name) for f in fields(branch)})


@pytest.fixture
def factory(request):
    make = request.getfixturevalue("feedback_factory")
    return lambda label="B1", **kwargs: as_review_branch(make(label, **kwargs))


def current(branch):
    request = prepare(branch)[1]
    return reconstruct_state(request["input"]), request


def test_only_two_unsent_fields_change_no_fake_notes_tools_or_new_evidence(factory):
    branch = factory("A1", checked=True)
    before, request = current(branch)
    raw = copy.deepcopy(request)
    changed = rollout.add_review(request)
    after = reconstruct_state(changed["input"])
    issue = after["working_notes"].pop(rollout.FIELD)
    assert after["working_notes"] == before["working_notes"]
    assert issue["model_authored"] is False and issue["report_ref"] == rollout.design.FIELD
    assert issue["current_diff_behavior_verdict"] == "NOT_ASSESSED"
    assert issue["state"] == "reported_failure_on_current_candidate"
    assert after["completion_guidance"]["next_action"] == {"tool": "run_probe"}
    after["completion_guidance"] = before["completion_guidance"]
    assert after == before and request == raw
    assert {**changed, "input": request["input"]} == request
    assert changed["input"][:-1] == request["input"][:-1]
    assert branch.new_provider_calls == branch.new_tools == branch.gateway.probe_sandbox.calls == 0


def test_context_artifact_and_native_view_match_through_mutation_check_and_optional_finish(factory):
    branch = factory()
    first = dispatch(branch, [mutation_call(branch.gateway)])
    state, request = current(branch)
    issue = state["working_notes"][rollout.FIELD]
    assert issue["state"] == "modified_unverified"
    assert state[rollout.design.FIELD]["currency"] == "historical_candidate"
    assert state["completion_guidance"]["next_action"]["tool"] == "run_check"
    assert request["input"][:len(first["input"])] == first["input"]
    dispatch(branch, [action("run_check", "check", check_id="existing-unit-tests")])
    state, request = current(branch)
    assert state["working_notes"][rollout.FIELD] == issue  # Generic PASS never resolves the case.
    assert state["completion_guidance"]["submission_ready"]
    assert state["completion_guidance"]["next_action"] == {"tool": "run_probe"}
    assert "finish_task" in state["available_tool_names"]
    ref = branch._new_events("turn_started")[-1]["context_artifact"]
    context = json.loads(branch.store.read_bytes(Artifact.model_validate(ref)))
    # Native projection omits the raw notes' static interpretation prose. Only the
    # new report entry must be identical; do not undo that existing deduplication.
    assert context["working_notes"][rollout.FIELD] == state["working_notes"][rollout.FIELD]
    assert context["completion_guidance"] == state["completion_guidance"]
    event = branch._new_events("report_verification_review_projected")[-1]
    assert event["review_state"] == "modified_unverified" and event["arm"] == "B"
    assert event["request_hash"] == sha256_bytes(rollout.design.wire(request))
    dispatch(branch, [action("finish_task", "finish")])
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert branch.gateway.probe_sandbox.calls == 0
    assert branch.terminal["task_acceptance"] == "NOT_RUN" and not branch.terminal["official"]
    before = branch.journal.path.read_bytes()
    assert prepare(as_review_branch(reopen(branch))) is None
    assert branch.journal.path.read_bytes() == before


@pytest.mark.parametrize("status", ["passed", "failed"])
def test_any_probe_is_not_same_case_proof_and_expires_after_edit(factory, status):
    branch = factory(checked=True)
    branch.gateway.probe_sandbox.status = status
    dispatch(branch, [probe_call()])  # Question/source do not reproduce the report.
    state, request = current(branch)
    issue = state["working_notes"][rollout.FIELD]
    assert issue["state"] == "probe_evidence_available_for_review"
    assert issue["current_diff_behavior_verdict"] == "NOT_ASSESSED"
    assert issue["probe_evidence_refs"] == [{
        "action_id": "probe-1", "delivery": "native_function_call_and_output",
        "execution_status": "completed" if status == "passed" else "failed"}]
    assert "PUBLIC_PROBE_OUTPUT" not in canonical_json(issue)  # Reference, not duplicate body.
    assert "PUBLIC_PROBE_OUTPUT" in canonical_json(request)
    assert "unrelated" in state["completion_guidance"]["message"]
    assert state["completion_guidance"]["next_action"] == {"tool": "finish_task"}
    # Reconstruct from durable public receipts; no extra analysis-model call or lifecycle store.
    restored = as_review_branch(reopen(branch))
    assert current(restored)[0]["working_notes"][rollout.FIELD] == issue
    edit = mutation_call(branch.gateway, action_id="second-edit")
    old = edit.arguments["new_text"]
    edit = edit.model_copy(update={"arguments": {
        **edit.arguments, "old_text": old, "new_text": old + "  # second"}})
    dispatch(restored, [edit])
    next_issue = current(restored)[0]["working_notes"][rollout.FIELD]
    assert next_issue["state"] == "modified_unverified" and not next_issue["probe_evidence_refs"]


def test_rejected_mutation_does_not_invalidate_same_diff_probe_or_force_read(factory):
    branch = factory(checked=True)
    dispatch(branch, [probe_call()])
    issue = current(branch)[0]["working_notes"][rollout.FIELD]
    edit = mutation_call(branch.gateway, action_id="oversized-edit")
    edit = edit.model_copy(update={"arguments": {
        **edit.arguments, "old_text": edit.arguments["new_text"],
        "new_text": "# too big\n" * 100}})
    dispatch(branch, [edit])
    state, _ = current(branch)
    assert state["last_failed_mutation"] is not None
    assert state["working_notes"][rollout.FIELD] == issue
    assert "finish_task" in state["available_tool_names"]


def test_guidance_uses_actual_action_space_and_never_treats_note_resolution_as_proof(factory):
    state, _ = current(factory("A1", checked=True))
    state["available_tool_names"] = ["finish_task", "stop_task"]
    state["working_notes"]["verification"] = {
        "items": [{"status": "resolved", "model_authored": True}], "unresolved_ids": []}
    issue = rollout.review(state)
    guidance = rollout.completion_guidance(state, issue)
    assert "run_probe" not in canonical_json(guidance)
    assert guidance["next_action"] == {"tool": "finish_task"}
    assert issue["state"] == "reported_failure_on_current_candidate"
    assert issue["current_diff_behavior_verdict"] == "NOT_ASSESSED"
    assert state["working_notes"]["verification"]["items"][0]["status"] == "resolved"


@pytest.mark.parametrize("fault,code", [
    ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("decision_recorded", None), ("actions_finished", None), ("batch_finished", None),
])
def test_branch_replay_preserves_projection_without_duplicate_mutation_or_provider(factory, fault,
                                                                                  code):
    branch = factory()
    adapter = Adapter([mutation_call(branch.gateway)])

    def crash(point):
        if point == fault:
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError, match="crash"):
        dispatch(branch, adapter=adapter, checkpoint=crash)
    restored = as_review_branch(reopen(branch))
    if code:
        with pytest.raises(rollout.native.engine.AbortExperiment) as error:
            current(restored)
        assert error.value.code == code
        assert restored.gateway.accepted_mutations == 0
    else:
        state, _ = current(restored)
        assert state["working_notes"][rollout.FIELD]["state"] == "modified_unverified"
        assert restored.gateway.accepted_mutations == 1 and restored.new_provider_calls == 1
        path = restored.gateway.workspace / mutation_call(restored.gateway).arguments["path"]
        before = path.read_bytes()
        current(as_review_branch(reopen(restored)))
        assert path.read_bytes() == before


def test_four_arm_mock_reuses_bounded_executor_optional_finish_no_keys_or_docker(factory,
                                                                              tmp_path,
                                                                              monkeypatch):
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "plan.json").write_bytes(b"{}")
    branches = {label: factory(label, checked=True) for label in rollout.ORDER}
    plan = mock_plan(branches["A1"])
    monkeypatch.setattr(rollout, "validate", lambda _: (plan, {}))
    monkeypatch.setattr(rollout, "initialize_branch", lambda p, label, *a: branches[label])

    def forbidden(*args, **kwargs):
        pytest.fail("live preflight or credentials used by a mock")

    monkeypatch.setattr(rollout.feedback, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_source_preflight", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_sandbox_preflight", forbidden)
    args = dict(approval_packet_hash=sha256_bytes(b"{}"), credential_file=repository_env(),
                cap=rollout.TOTAL_CAP, pricing_verified_on=utc_now().date().isoformat(),
                sandbox=Checks(), probe=CaseProbe(plan.report), adapter_factory=lambda _: Adapter([
                    action("finish_task", "finish")]))
    result = rollout.run(packet, tmp_path / "result", **args)
    assert result["terminal"] == "ROLLOUTS_COMPLETED" and result["provider_free"]
    assert [b["branch"] for b in result["branches"]] == list(rollout.ORDER)
    assert result["new_provider_calls"] == result["new_tool_actions"] == 4
    assert all(b.gateway.probe_sandbox.calls == 0 for b in branches.values())
    assert args["probe"].calls == 1 and len(result["operator_case_audits"]) == 4
    assert all(not row["agent_credit"] for row in result["operator_case_audits"])
    assert not result["official"] and result["task_acceptance"] == "NOT_RUN"


def repository_env():
    return rollout.repository_root() / ".env"


def test_real_checkpoint_packet_and_two_exact_inputs_no_candidate_execution(tmp_path, monkeypatch):
    if not rollout.feedback.DESIGN.exists():
        pytest.skip("external evidence unavailable")

    def forbidden(*args, **kwargs):
        pytest.fail("network/credential access during no-call preparation")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(rollout.feedback, "load_exact_openai_api_key", forbidden)
    packet = tmp_path / "packet"
    envelope = rollout.prepare(packet)
    plan, again = rollout.validate(packet)
    assert envelope == again and not envelope["paid_execution_authorized"]
    assert envelope["branch_order"] == list(rollout.ORDER)
    assert (packet / "A.json").read_bytes() == (
        rollout.feedback.DESIGN / "feedback-request.json").read_bytes()
    assert plan.arms["B"] == rollout.add_review(plan.arms["A"])
    assert plan.arms["A"]["input"][:-1] == plan.arms["B"]["input"][:-1]
    assert plan.arms["A"]["tools"] == plan.arms["B"]["tools"]
    assert len([i for i in plan.arms["B"]["input"] if i.get("type") == "reasoning"]) == 21
    sandbox, probe = Checks(), FakeProbe()
    branch = rollout.initialize_branch(plan, "B1", tmp_path / "branches", sandbox, probe,
                                       ExecutionDeadline.from_remaining(90))
    state, request = current(branch)
    assert request == plan.arms["B"]
    assert state["working_notes"][rollout.FIELD]["state"] == "reported_failure_on_current_candidate"
    assert branch.counters.model_calls == 21 and branch.counters.tool_actions == 22
    assert branch.gateway.accepted_mutations == branch.inherited_accepted_mutations == 2
    assert sandbox.calls == [] and probe.calls == branch.new_provider_calls == branch.new_tools == 0
    # No future F1/F2 outcome, source repair hint or extra public case enters the treatment.
    delta = canonical_json({k: state[k] for k in ("working_notes", "completion_guidance")})
    assert all(word not in delta for word in (
        "reference_patch", "hidden_test", "private_spec", "F1", "F2", "a/b", "component stack"))
    assert all(p.name not in {"private.yaml", "hidden_evaluator.py"}
               for p in packet.iterdir())
