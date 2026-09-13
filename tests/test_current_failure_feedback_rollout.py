"""Current-candidate feedback integration; fake providers and public sandboxes only."""
from __future__ import annotations

import copy
import json
import socket
import subprocess
from dataclasses import fields, replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_counterexample_review_rollout import Adapter, Checks, action
from test_dev_probes import FakeProbe, probe_call
from test_dev_tools import mutation_call
from test_failure_given_repair_rollout import CaseProbe, dispatch, mock_plan, prepare, reopen
from test_failure_given_repair_rollout import factory as feedback_factory  # noqa: F401

from diagnostics import current_failure_feedback_rollout as rollout
from patchloop.agent.model import ModelTurnError
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.conversation import reconstruct_state
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, utc_now


def as_branch(branch):
    return rollout.Branch(**{f.name: getattr(branch, f.name) for f in fields(branch)})


@pytest.fixture
def factory(request):
    make = request.getfixturevalue("feedback_factory")

    def create(label="B1", **kwargs):
        branch = as_branch(make(label, **kwargs))
        old = branch.report()
        report = {
            "origin": "operator_executed_public_diagnostic", "model_authored": False,
            "observed_on_diff_hash": old["observed_on_diff_hash"],
            "case_definition_ref": rollout.design.prior.FIELD,
            "expected": old["expected"], "actual": {"error": None,
                "entries": [[p, "dir", "0o755"] for p in ("a", "a/b", "c")]},
            "matches_expected": False,
        }
        branch.bind_candidate_report(report if label.startswith("B") else None)
        return branch
    return create


def current(branch):
    request = prepare(branch)[1]
    return reconstruct_state(request["input"]), request


def test_two_reports_bound_once_and_only_latest_field_changes_without_fake_credit(factory):
    branch = factory(checked=True)
    budget = (branch.counters.model_calls, branch.counters.tool_actions,
              branch.gateway.accepted_mutations)
    state, request = current(branch)
    new = state[rollout.design.FIELD]
    assert new["currency"] == "current_candidate" and new["matches_expected"] is False
    assert state["workflow_gate"] == "ready_to_submit"
    assert "finish_task" in state["available_tool_names"]
    assert all(c["status"] == "PASS" for c in state["visible_check_status"])
    assert state["current_public_failure"] is None
    assert budget == (branch.counters.model_calls, branch.counters.tool_actions,
                      branch.gateway.accepted_mutations)
    assert branch.new_tools == branch.new_provider_calls == branch.new_cost_nanos == 0
    assert len(branch._new_events("operator_feedback_bound")) == 1
    assert len(branch._new_events("current_candidate_feedback_bound")) == 1
    branch.bind_candidate_report(branch.candidate_report())
    assert len(branch._new_events("current_candidate_feedback_bound")) == 1
    event = branch._new_events("turn_started")[-1]
    ref = Artifact.model_validate(event["context_artifact"])
    context = json.loads(branch.store.read_bytes(ref))
    assert context[rollout.design.FIELD] == new
    assert context[rollout.design.prior.FIELD] == state[rollout.design.prior.FIELD]
    control = copy.deepcopy(request)
    view = json.loads(control["input"][-1]["content"])
    del view["state"][rollout.design.FIELD]
    control["input"][-1]["content"] = rollout.design.wire(view).decode()
    assert rollout.design.add_feedback(control, branch.candidate_report()) == request
    projected = branch._new_events("current_candidate_feedback_projected")[-1]
    assert projected["arm"] == "B" and projected["request_hash"] == sha256_bytes(
        rollout.design.wire(request))
    assert projected["candidate_report_hash"] == sha256_bytes(
        rollout.design.wire(branch.candidate_report()))


@pytest.mark.parametrize("label", ["A1", "B1"])
def test_repair_probe_check_finish_and_terminal_reopen_keep_history(factory, label):
    branch = factory(label)
    first = dispatch(branch, [mutation_call(branch.gateway)])
    state, after = current(branch)
    assert after["input"][:len(first["input"])] == first["input"]
    if label.startswith("B"):
        assert state[rollout.design.FIELD]["currency"] == "historical_candidate"
    else:
        assert rollout.design.FIELD not in state
    dispatch(branch, [probe_call()])
    dispatch(branch, [action("run_check", "check", check_id="existing-unit-tests")])
    final = dispatch(branch, [action("finish_task", "finish")])
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert branch.terminal["accepted_mutations_since_checkpoint"] == 1
    assert branch.terminal["submitted_artifact"]["content_hash"] == branch.gateway.current_diff_hash
    assert branch.new_provider_calls == branch.new_tools == 4
    assert branch.gateway.probe_sandbox.calls == 1
    items = final["input"]
    assert [i["call_id"] for i in items if i.get("type") == "function_call"] == [
        i["call_id"] for i in items if i.get("type") == "function_call_output"]
    assert sum(i.get("encrypted_content") == "cipher-probe-1" for i in items) == 1
    assert rollout.design.FIELD not in canonical_json(reconstruct_state(items)["working_notes"])
    assert branch.terminal["task_acceptance"] == "NOT_RUN" and not branch.terminal["official"]
    before = branch.journal.path.read_bytes()
    assert prepare(as_branch(reopen(branch))) is None
    assert branch.journal.path.read_bytes() == before


def test_rollback_keeps_current_failure_but_does_not_force_another_mutation(factory):
    branch = factory(checked=True)
    baseline = branch.gateway.current_diff_hash
    edit = mutation_call(branch.gateway, action_id="too-big")
    rejected = edit.model_copy(update={"arguments": {
        **edit.arguments, "old_text": edit.arguments["new_text"],
        "new_text": "# oversized\n" * 100}})
    dispatch(branch, [rejected])
    state, _ = current(as_branch(reopen(branch)))
    assert branch.gateway.current_diff_hash == baseline
    assert state[rollout.design.FIELD]["currency"] == "current_candidate"
    assert state["last_failed_mutation"] is not None
    assert "finish_task" in state["available_tool_names"]
    dispatch(branch, [action("finish_task", "finish")])
    assert branch.terminal["accepted_mutations_since_checkpoint"] == 0
    assert branch.gateway.probe_sandbox.calls == 0  # No new mandatory probe/check gate.


@pytest.mark.parametrize("fault,code", [
    ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("usage_recorded", "PROVIDER_CONTINUATION_ERROR"),
    ("decision_recorded", None), ("actions_finished", None), ("batch_finished", None),
])
def test_recovery_keeps_feedback_and_never_duplicates_provider_or_mutation(factory, fault, code):
    branch = factory()
    adapter = Adapter([mutation_call(branch.gateway)])

    def crash(point):
        if point == fault:
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError, match="crash"):
        dispatch(branch, adapter=adapter, checkpoint=crash)
    restored = as_branch(reopen(branch))
    calls_before = list(adapter.sequence)
    if code:
        with pytest.raises(rollout.native.engine.AbortExperiment) as error:
            current(restored)
        assert error.value.code == code and restored.gateway.accepted_mutations == 0
    else:
        state, _ = current(restored)
        assert state[rollout.design.FIELD]["currency"] == "historical_candidate"
        assert restored.new_provider_calls == restored.new_tools == 1
        assert restored.gateway.accepted_mutations == 1
        before = restored.gateway.current_diff_hash
        current(as_branch(reopen(restored)))
        assert restored.gateway.current_diff_hash == before
    assert adapter.sequence == calls_before


@pytest.mark.parametrize("fault", ["decision_recorded", "dispatch_recorded"])
def test_corrupt_feedback_blocks_pending_action_but_unknown_dispatch_has_priority(factory, fault):
    branch = factory()

    def crash(point):
        if point == fault:
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        dispatch(branch, [mutation_call(branch.gateway)], checkpoint=crash)
    ref = Artifact.model_validate(branch._new_events("current_candidate_feedback_bound")[0][
        "report_artifact"])
    # Each parametrized case owns a separate temporary store; corrupting one must
    # not poison the next case's content-addressed report with identical bytes.
    Path(ref.path).write_bytes(b"tampered")
    with pytest.raises(rollout.native.engine.AbortExperiment) as error:
        current(as_branch(reopen(branch)))
    assert error.value.code == ("CURRENT_CANDIDATE_FEEDBACK_ERROR"
                                if fault == "decision_recorded"
                                else "PROVIDER_TIMEOUT_OR_UNKNOWN")
    assert branch.gateway.accepted_mutations == 0


def test_incomplete_correction_preserves_current_observation_and_cipher_without_plaintext(factory):
    class Incomplete(Adapter):
        def execute_request(self, *args, **kwargs):
            return replace(super().execute_request(*args, **kwargs),
                           output_item_types=("reasoning",), response_status="incomplete",
                           response_incomplete_reason="max_output_tokens",
                           error=ModelTurnError("incomplete_response", "RAW_REASONING_SENTINEL"))

    branch = factory()
    dispatch(branch, adapter=Incomplete([]))
    prepare(branch)
    restored = as_branch(reopen(branch))
    state, request = current(restored)
    assert "max_output_tokens" in request["input"][-1]["content"]
    assert state[rollout.design.FIELD]["currency"] == "current_candidate"
    assert sum(i.get("encrypted_content") == "cipher-incomplete" for i in request["input"]) == 1
    assert "RAW_REASONING_SENTINEL" not in canonical_json(request) + branch.journal.path.read_text()
    dispatch(restored, [probe_call()])
    assert all(c["attempt"] != "protocol" for c in current(restored)[0][
        "recent_attempt_result_next_question"])


@pytest.mark.parametrize("failure,expected", [
    ("count", "COUNT_TIMEOUT_OR_UNKNOWN"), ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
])
def test_uncertainty_stops_all_new_conditions_without_extra_sample(factory, failure, expected):
    branches = [factory(label, checked=True) for label in rollout.ORDER]
    adapters = []

    def make(_):
        adapter = Adapter([action("finish_task", "finish")], failure=failure,
                          mismatch=failure == "billing")
        adapters.append(adapter)
        return adapter

    result = rollout.native.drive(mock_plan(branches[0]), branches, make,
                                  branch_cap=rollout.BRANCH_CAP, total_cap=rollout.TOTAL_CAP)
    assert result["terminal"] == expected and len(adapters) == 1
    assert all(b.gateway.probe_sandbox.calls == 0 for b in branches)
    assert all(b.new_provider_calls == 0 for b in branches[1:])
    assert "RAW" not in canonical_json(result)


def test_four_nontransferable_one_dollar_ledgers_and_full_output_reservation(factory):
    class Costly(Adapter):
        def count_input_tokens_v2(self, request, **kwargs):
            self.count = 200000
            return super().count_input_tokens_v2(request, **kwargs)

        def execute_request(self, *args, **kwargs):
            return replace(super().execute_request(*args, **kwargs), output_tokens=25000)

    branches = [factory(label, checked=True) for label in rollout.ORDER]
    requests = []

    # A1 keeps inspecting; the other branches finish, leaving their unused caps untouched.
    order = iter(["A1", "B1", "B2", "A2", "A1", "A1", "A1"])

    def scheduled(_):
        label = next(order)
        adapter = Costly([probe_call(action_id=f"probe-{len(requests)}")
                          if label == "A1" else action("finish_task", "finish")])
        requests.append(adapter)
        return adapter

    result = rollout.native.drive(mock_plan(branches[0]), branches, scheduled,
                                  branch_cap=rollout.BRANCH_CAP, total_cap=rollout.TOTAL_CAP)
    assert result["terminal"] == "ROLLOUTS_COMPLETED"
    assert branches[0].terminal["terminal"] == "COST_CAP_REACHED"
    assert branches[0].new_provider_calls == 3  # 3 * .2625; fourth full reserve does not fit.
    assert branches[0].new_cost_nanos == 787500000
    assert all(b.new_provider_calls == 1 for b in branches[1:])
    assert result["new_provider_calls"] == 6 and result["new_input_count_calls"] == 7
    assert result["recorded_cost_nanos"] == 1575000000 < 4000000000
    assert all(e["output_ceiling"] == 25000 for b in branches
               for e in b._new_events("provider_call_started"))


def test_one_shot_four_arm_mock_and_operator_audit_are_separate(factory, tmp_path, monkeypatch):
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "plan.json").write_bytes(b"{}")
    branches = {label: factory(label, checked=True) for label in rollout.ORDER}
    plan = mock_plan(branches["A1"])
    monkeypatch.setattr(rollout, "validate", lambda _: (plan, {}))
    monkeypatch.setattr(rollout, "initialize_branch", lambda p, label, *a: branches[label])

    def forbidden(*args, **kwargs):
        pytest.fail("live access during mock")

    monkeypatch.setattr(rollout.feedback, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_source_preflight", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_sandbox_preflight", forbidden)
    repair = mutation_call(branches["B1"].gateway, action_id="repair")
    repair = repair.model_copy(update={"arguments": {
        **repair.arguments, "old_text": repair.arguments["new_text"],
        "new_text": repair.arguments["new_text"] + "  # revised"}})
    calls = iter([
        action("finish_task", "finish"), repair,
        action("finish_task", "finish"), action("finish_task", "finish"),
        action("run_check", "check-repair", check_id="existing-unit-tests"),
        action("finish_task", "finish-repair"),
    ])
    args = dict(approval_packet_hash=sha256_bytes(b"{}"),
                credential_file=rollout.repository_root() / ".env", cap=rollout.TOTAL_CAP,
                pricing_verified_on=utc_now().date().isoformat(), sandbox=Checks(),
                probe=CaseProbe(plan.report), adapter_factory=lambda _: Adapter([next(calls)]))
    destination = tmp_path / "result"
    result = rollout.run(packet, destination, **args)
    assert result["terminal"] == "ROLLOUTS_COMPLETED" and result["provider_free"]
    assert result["new_provider_calls"] == result["new_tool_actions"] == 6
    assert args["probe"].calls == 2 and len(result["operator_case_audits"]) == 4
    assert branches["B1"].terminal["accepted_mutations_since_checkpoint"] == 1
    assert branches["B1"].terminal["submitted_artifact"]["content_hash"] == (
        branches["B1"].gateway.current_diff_hash)
    assert all(r["case_outcome"] == "FAIL" and not r["agent_credit"]
               for r in result["operator_case_audits"])
    assert all(b.gateway.probe_sandbox.calls == 0 for b in branches.values())
    assert result["task_acceptance"] == "NOT_RUN" and not result["official"]
    with pytest.raises(ContractError, match="fresh disjoint"):
        rollout.run(packet, destination, **args)


@pytest.mark.parametrize("bad", ["packet", "cap", "credential", "date"])
def test_bad_approval_inputs_fail_before_keys_tools_or_creating_result(tmp_path, monkeypatch, bad):
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "plan.json").write_bytes(b"{}")
    monkeypatch.setattr(rollout, "validate", lambda _: (SimpleNamespace(), {}))
    args = dict(approval_packet_hash=sha256_bytes(b"{}"), cap=rollout.TOTAL_CAP,
                credential_file=rollout.repository_root() / ".env",
                pricing_verified_on=utc_now().date().isoformat())
    key, value = {"packet": ("approval_packet_hash", "bad"), "cap": ("cap", Decimal("2")),
                  "credential": ("credential_file", tmp_path / ".env"),
                  "date": ("pricing_verified_on", "2000-01-01")}[bad]
    args[key] = value
    with pytest.raises(ContractError):
        rollout.run(packet, tmp_path / "result", **args,
                    adapter_factory=lambda _: pytest.fail("provider admitted"))
    assert not (tmp_path / "result").exists()


def test_result_cannot_be_created_inside_immutable_source_parent(tmp_path, monkeypatch):
    monkeypatch.setattr(rollout.design, "SOURCE", tmp_path)
    monkeypatch.setattr(rollout.feedback, "execute_packet", lambda *a, **k: pytest.fail("admitted"))
    with pytest.raises(ContractError, match="fresh disjoint"):
        rollout.run(tmp_path / "plan", tmp_path / "source-sibling")
    assert not (tmp_path / "source-sibling").exists()


@pytest.mark.skipif(not rollout.DESIGN.exists(), reason="local immutable design unavailable")
def test_real_nested_prefix_exact_first_requests_budget_and_notes_without_execution(
    tmp_path, monkeypatch,
):
    def forbidden(*args, **kwargs):
        pytest.fail("live access during preparation")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(rollout.feedback, "load_exact_openai_api_key", forbidden)
    # Loading/validating the plan cannot execute processes. Only the later local
    # clone/patch restore below uses Git, never the candidate's code or a sandbox.
    with monkeypatch.context() as scoped:
        scoped.setattr(subprocess, "Popen", forbidden)
        plan = rollout.load_plan()
        envelope = rollout.prepare(tmp_path / "packet")
        assert rollout.validate(tmp_path / "packet")[1] == envelope
    assert envelope["branch_order"] == list(rollout.ORDER)
    assert envelope["cap_usd_each"] == "1.00" and envelope["cap_usd_total"] == "4.00"
    assert not envelope["paid_execution_authorized"]
    for label in ("A1", "B1"):
        checks, probe = Checks(), FakeProbe()
        branch = rollout.initialize_branch(plan, label, tmp_path / "branches", checks, probe,
                                           ExecutionDeadline.from_remaining(90))
        state, request = current(branch)
        assert rollout.design.wire(request) == (rollout.DESIGN / f"{label[0]}.json").read_bytes()
        assert branch.counters.model_calls == 24 and branch.counters.tool_actions == 25
        assert branch.gateway.accepted_mutations == branch.inherited_accepted_mutations == 3
        assert branch.new_provider_calls == branch.new_tools == branch.new_cost_nanos == 0
        assert checks.calls == [] and probe.calls == 0
        assert state["working_notes"] == plan.state["working_notes"]
        assert state["visible_check_status"] == plan.state["visible_check_status"]
        assert state["remaining_budget"]["accepted_mutations"] == 1
        assert len([i for i in request["input"] if i.get("type") == "reasoning"]) == 24
        assert rollout.design.FIELD not in state if label[0] == "A" else (
            state[rollout.design.FIELD]["currency"] == "current_candidate")
        assert not branch._new_events("turn_decision_recorded")
        assert all(e["payload"].get("diagnostic_inherited") for e in branch.journal.events()
                   if e["event_type"] in {"action_finished", "provider_call_finished"})
