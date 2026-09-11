from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_current_source_rollout import FullAdapter
from test_dev_probes import FakeProbe, probe_call
from test_dev_tools import mutation_call, read_calls
from test_fresh_state_rollout import start

from diagnostics import probe_first_rollout as rollout
from patchloop.agent.model import ModelTurnError
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError, ResumeContractMismatch
from patchloop.util import canonical_json, sha256_json, utc_now


@pytest.fixture
def branch(gateway_factory):
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status="passed")
    active = rollout.common.ActiveClock()
    gateway.deadline = ExecutionDeadline.from_remaining(1601, clock=active)
    branch = rollout.Branch("B1", journal, rollout.source.ArtifactStore(journal.root / "artifacts"),
                            gateway, rollout.loop._RunCounters(), active, 0)
    start(branch, "seed-read", read_calls())
    journal.append("model_call_finished", {"turn_id": "seed-read", "tool_calls": []})
    return branch


def prepare(branch, adapter=None):
    return branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task),
                                  adapter or FullAdapter([]))


def ledger():
    return DevCostLedger(Decimal("1.20"), pricing_for_model(rollout.shared.MODEL))


def dispatch(branch, calls, *, cost=None, adapter=None, checkpoint=lambda _: None):
    adapter = adapter or FullAdapter(calls)
    prepared = prepare(branch, adapter)
    rollout.common.dispatch(branch, adapter, cost or ledger(), prepared, checkpoint=checkpoint)
    return prepared[1]


def test_only_first_b_choice_changes_no_source_inlining_or_notice(branch):
    branch.label = "A1"
    a = prepare(branch)[1]
    branch.label = "B1"
    b = prepare(branch)[1]
    expected = copy.deepcopy(a)
    expected["tool_choice"] = dict(rollout.view.FORCED_PROBE)
    assert rollout.view.wire(b) == rollout.view.wire(expected)
    assert b["input"] == a["input"] and b["tools"] == a["tools"]
    assert "followup_state_contract" not in b["input"][-1]["content"]
    assert not branch._new_events("source_presentation_recorded")


@pytest.mark.parametrize("status", ["passed", "failed"])
def test_probe_feedback_releases_once_preserves_native_history_and_spend(branch, status):
    branch.gateway.probe_sandbox.status = status
    before = branch.gateway.current_diff_hash
    request = dispatch(branch, [probe_call()])
    after = prepare(branch)[1]
    assert after["tool_choice"] == "required"
    assert after["input"][:len(request["input"])] == request["input"]
    assert sum(i.get("encrypted_content") == "cipher-new" for i in after["input"]) == 1
    assert "PUBLIC_PROBE_OUTPUT" in canonical_json(after["input"])
    assert [i["call_id"] for i in after["input"] if i.get("type") == "function_call"] == [
        i["call_id"] for i in after["input"] if i.get("type") == "function_call_output"]
    assert branch.gateway.current_diff_hash == before
    assert branch.new_provider_calls == 1 and branch.counters.model_calls == 2
    assert branch.counters.tool_actions == 3 and branch.gateway.probe_sandbox.calls == 1
    prepare(branch)
    assert len(branch._new_events("probe_phase_released")) == 1
    assert len(branch._new_events("working_notes_updated")) <= 2


def test_a_can_mutate_without_probe_b_invalid_choice_gets_probe_only_correction(branch):
    dispatch(branch, [mutation_call(branch.gateway)])
    assert branch.gateway.accepted_mutations == 0
    correction = branch._new_events("protocol_correction")[-1]
    assert correction["available_tool_names"] == ["run_probe"]
    b = prepare(branch)[1]
    assert b["tool_choice"] == rollout.view.FORCED_PROBE
    branch.label = "A1"
    dispatch(branch, [mutation_call(branch.gateway)])
    assert branch.gateway.accepted_mutations == 1
    assert branch.gateway.probe_sandbox.calls == 0


def test_reasoning_only_correction_survives_started_turn_and_is_consumed_once(branch):
    class Incomplete(FullAdapter):
        def execute_request(self, *args, **kwargs):
            raw = super().execute_request(*args, **kwargs)
            return replace(raw, output_item_types=("reasoning",), response_status="incomplete",
                           response_incomplete_reason="max_output_tokens",
                           error=ModelTurnError("incomplete_response", "UNSAVED_RAW_REASONING"))

    dispatch(branch, [], adapter=Incomplete([]))
    next_request = prepare(branch)[1]
    assert next_request["tool_choice"] == rollout.view.FORCED_PROBE
    assert "max_output_tokens" in canonical_json(next_request["input"])
    assert "UNSAVED_RAW_REASONING" not in branch.journal.path.read_text()
    branch.correction = None  # Crash after turn_started must not consume correction.
    repeated = prepare(branch)[1]
    assert "max_output_tokens" in repeated["input"][-1]["content"]
    dispatch(branch, [probe_call()])
    following = prepare(branch)[1]
    assert following["tool_choice"] == "required"
    assert branch.correction is None


@pytest.mark.parametrize("fault,code", [
    ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("usage_recorded", "PROVIDER_CONTINUATION_ERROR"),
    ("decision_recorded", None), ("actions_finished", None), ("batch_finished", None),
])
def test_fault_boundary_reconciles_without_provider_or_duplicate_probe(branch, fault, code):
    adapter = FullAdapter([probe_call()])

    def crash(point):
        if point == fault:
            raise RuntimeError("injected crash")

    with pytest.raises(RuntimeError, match="injected crash"):
        dispatch(branch, [], adapter=adapter, checkpoint=crash)
    if code:
        with pytest.raises(rollout.common.AbortExperiment) as error:
            prepare(branch, adapter)
        assert error.value.code == code
        assert branch.gateway.probe_sandbox.calls == 0
    else:
        assert prepare(branch, adapter)[1]["tool_choice"] == "required"
        assert branch.gateway.probe_sandbox.calls == 1
        assert len(branch._new_events("probe_phase_released")) == 1
        assert branch.new_provider_calls == 1
        assert branch.counters.tool_actions == 3
        assert len(branch._new_events("turn_decision_recorded")) == 2
    assert adapter.sequence == (["count"] if fault == "dispatch_recorded"
                                else ["count", "create"])


@pytest.mark.parametrize("fault", ["decision_recorded", "actions_finished", "batch_finished"])
def test_recorded_mutation_reconciles_before_horizon_and_never_repeats(branch, fault):
    branch.label = "A1"

    def crash(point):
        if point == fault:
            raise RuntimeError("mutation crash")

    with pytest.raises(RuntimeError, match="mutation crash"):
        dispatch(branch, [mutation_call(branch.gateway)], checkpoint=crash)
    branch.gateway.limits = branch.gateway.limits.model_copy(update={"max_model_calls": 2})
    assert prepare(branch) is None
    assert branch.gateway.accepted_mutations == 1
    assert branch.terminal["terminal"] == "LIMIT_REACHED"
    assert len([e for e in branch._new_events("action_finished")
                if e["result"]["tool"] == "replace_text"]) == 1


def test_double_protocol_failure_ends_without_probe_and_terminal_recovery_is_read_only(branch):
    for n in range(2):
        dispatch(branch, [mutation_call(branch.gateway, action_id=f"wrong-{n}")])
    assert branch.terminal["terminal"] == "PROTOCOL_VIOLATION"
    before = branch.journal.path.read_bytes()
    branch.terminal = None
    assert prepare(branch) is None
    assert branch.journal.path.read_bytes() == before
    assert branch.gateway.probe_sandbox.calls == 0


def test_probe_mutation_check_finish_does_not_credit_private_evaluation(branch):
    cost = ledger()
    calls = [probe_call(), mutation_call(branch.gateway), RequestedTool(
        name="run_check", action_id="check-new", arguments={"check_id": "existing-unit-tests"},
        turn_decision=PublicTurnDecision(mode="verify", basis="Check public repair")),
        RequestedTool(name="finish_task", action_id="finish-new", arguments={},
                      turn_decision=PublicTurnDecision(mode="finish", basis="Checks pass"))]
    requests = [dispatch(branch, [call], cost=cost) for call in calls]
    assert [r["tool_choice"] for r in requests] == [rollout.view.FORCED_PROBE] + ["required"] * 3
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert branch.terminal["private_evaluation"] == "NOT_RUN"
    assert branch.terminal["submitted_artifact"]["content_hash"] == branch.gateway.current_diff_hash
    assert branch.new_provider_calls == 4 and branch.gateway.probe_sandbox.calls == 1


@pytest.mark.parametrize("failure,code", [("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
                                          ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN")])
def test_uncertainty_is_never_retried_and_sdk_text_is_not_saved(branch, failure, code):
    adapter = FullAdapter([], failure=failure)
    with pytest.raises(rollout.common.AbortExperiment) as first:
        dispatch(branch, [], adapter=adapter)
    with pytest.raises(rollout.common.AbortExperiment) as second:
        prepare(branch, adapter)
    assert first.value.code == second.value.code == code
    assert adapter.sequence.count("count") == 1 and adapter.sequence.count("create") <= 1
    assert "SECRET_SDK_ERROR_SENTINEL" not in branch.journal.path.read_text()


def test_cap_is_shared_and_reserves_full_output_before_create(branch):
    cost = ledger()
    cost.spent_nanos = cost.cap_nanos
    adapter = FullAdapter([])
    with pytest.raises(rollout.common.AbortExperiment) as error:
        dispatch(branch, [], adapter=adapter, cost=cost)
    assert error.value.code == "COST_CAP_REACHED"
    assert adapter.sequence == ["count"] and branch.gateway.probe_sandbox.calls == 0


def test_packet_preflight_mismatch_before_root_key_adapter_or_sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(rollout, "load_plan", lambda: SimpleNamespace())
    monkeypatch.setattr(rollout, "envelope_for", lambda _: {"expected": 1})
    root = tmp_path / "plan"
    root.mkdir()
    (root / "plan.json").write_text('{"expected":2}')
    with pytest.raises(ContractError, match="prepared experiment changed"):
        rollout.run(root, tmp_path / "result",
                    credential_file=rollout.source.repository_root() / ".env",
                    cap=Decimal("1.20"), pricing_verified_on=utc_now().date().isoformat(),
                    adapter_factory=lambda _: pytest.fail("no adapter"))
    assert not (tmp_path / "result").exists()


def test_real_frozen_checkpoint_and_packets_are_unchanged_and_no_execution(tmp_path):
    if not rollout.DESIGN.exists():
        pytest.skip("external frozen evidence is not installed")
    from patchloop.sandbox import LocalSandbox

    before = {p: p.read_bytes() for p in rollout.DESIGN.iterdir() if p.is_file()}
    frozen_runtime = json.loads(before[rollout.DESIGN / "manifest.json"])["runtime_hash"]
    if rollout.view.runtime_content_hash() != frozen_runtime:
        with pytest.raises(ValueError, match="runtime changed"):
            rollout.load_plan()
        assert before == {p: p.read_bytes() for p in before}
        assert not list(tmp_path.iterdir())
        return
    plan = rollout.load_plan()
    envelope = rollout.prepare(tmp_path / "plan")
    assert envelope["collector_implemented"] and envelope["kind"] == rollout.SCHEMA
    assert "source_metrics" not in envelope
    branch = rollout.initialize_branch(plan, "B1", tmp_path / "branches", LocalSandbox(),
                                       FakeProbe(), ExecutionDeadline.from_remaining(90))
    prepared = prepare(branch)[1]
    assert rollout.view.wire(prepared) == (rollout.DESIGN / "B.json").read_bytes()
    assert branch.counters.model_calls == 20 and branch.counters.tool_actions == 20
    assert branch.gateway.accepted_mutations == 3 and branch.gateway.probe_sandbox.calls == 0
    assert not branch._new_events("provider_call_started")
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("failure", [None, "count", "create", "billing"])
def test_four_branch_driver_uses_probe_only_first_then_stops_shared_on_uncertainty(
    gateway_factory, tmp_path, monkeypatch, failure,
):
    branches = []
    for label in rollout.source.ORDER:
        gateway, journal, _ = gateway_factory()
        gateway.probe_sandbox = FakeProbe(status="passed")
        active = rollout.common.ActiveClock()
        gateway.deadline = ExecutionDeadline.from_remaining(1601, clock=active)
        b = rollout.Branch(label, journal, rollout.source.ArtifactStore(journal.root / "artifacts"),
                           gateway, rollout.loop._RunCounters(), active, 0)
        start(b, "seed-read", read_calls())
        journal.append("model_call_finished", {"turn_id": "seed-read", "tool_calls": []})
        branches.append(b)
    plan = SimpleNamespace(package=SimpleNamespace(public=branches[0].gateway.public_task),
                           requests={"A": {}, "B": {}})
    monkeypatch.setattr(rollout, "load_plan", lambda: plan)
    monkeypatch.setattr(rollout, "envelope_for", lambda _: {"test_driver": True})
    monkeypatch.setattr(rollout, "initialize_branch",
                        lambda _, label, *args: branches[rollout.source.ORDER.index(label)])
    prepared = tmp_path / "plan"
    prepared.mkdir()
    (prepared / "plan.json").write_text('{"test_driver":true}')
    for arm in ("A", "B"):
        (prepared / f"{arm}.json").write_text("{}")
    seen = []

    class ChoosingAdapter(FullAdapter):
        def execute_request(self, request, **kwargs):
            seen.append(request["tool_choice"])
            self.calls = ([probe_call()] if request["tool_choice"] == rollout.view.FORCED_PROBE
                          else [RequestedTool(name="stop_task", action_id="stop-new", arguments={
                              "reason_code": "no_safe_scoped_mutation", "summary": "Mock stop",
                          }, turn_decision=PublicTurnDecision(mode="stop", basis="Mock stop"))])
            return super().execute_request(request, **kwargs)

    adapters = []

    def factory(_):
        adapter = ChoosingAdapter([], failure=None if failure == "billing" else failure,
                                  mismatch=failure == "billing")
        adapters.append(adapter)
        return adapter

    result = rollout.run(prepared, tmp_path / "result",
                         credential_file=rollout.source.repository_root() / ".env",
                         cap=Decimal("1.20"), pricing_verified_on=utc_now().date().isoformat(),
                         adapter_factory=factory, sandbox=object(), probe=object())
    if failure is None:
        assert result["terminal"] == "ROLLOUTS_COMPLETED"
        assert seen == ["required", rollout.view.FORCED_PROBE,
                        rollout.view.FORCED_PROBE, "required", "required", "required"]
        assert result["new_provider_calls"] == 6
        assert all(b["terminal"] == "AGENT_STOPPED" for b in result["branches"])
        assert sum(b.gateway.probe_sandbox.calls for b in branches) == 2
    else:
        assert len(adapters) == 1
        assert result["terminal"] == ("COUNT_TIMEOUT_OR_UNKNOWN" if failure == "count"
                                      else "PROVIDER_TIMEOUT_OR_UNKNOWN")
        assert all(b["censored"] for b in result["branches"])
    assert "SECRET_SDK_ERROR_SENTINEL" not in canonical_json(result)


def test_eight_response_limit_never_dispatches(branch):
    # These events are restored before admission, not an in-memory counter override.
    for n in range(8):
        branch.journal.append("provider_call_started", {
            "call_id": f"limit-{n}", "turn_id": "seed-read",
        })
        branch.journal.append("provider_call_finished", {
            "call_id": f"limit-{n}", "turn_id": "seed-read", "billing_known": True,
            "cost_nanos": 0,
        })
    assert prepare(branch) is None
    assert branch.terminal["censored"] and branch.terminal["terminal"] == "LIMIT_REACHED"
    assert branch.gateway.probe_sandbox.calls == 0


@pytest.mark.parametrize("target", ["continuation", "input"])
def test_pending_native_artifact_tamper_stops_before_probe_or_new_dispatch(branch, target):
    def crash(point):
        if point == "decision_recorded":
            raise RuntimeError("before probe")

    with pytest.raises(RuntimeError):
        dispatch(branch, [probe_call()], checkpoint=crash)
    ref = (branch._new_events("turn_decision_recorded")[-1]["continuation_ref"]["artifact"]
           if target == "continuation"
           else branch._new_events("turn_started")[-1]["model_input_artifact"])
    Path(ref["path"]).write_text("TAMPERED_CIPHER")
    with pytest.raises(rollout.common.AbortExperiment) as error:
        prepare(branch)
    assert error.value.code == "PROVIDER_CONTINUATION_ERROR"
    assert branch.gateway.probe_sandbox.calls == 0
    assert branch.new_provider_calls == 1


@pytest.mark.parametrize("drift", [False, True])
def test_atomic_replacement_crash_reconciles_exact_candidate_or_rejects_other_drift(
    branch, monkeypatch, drift,
):
    branch.label = "A1"
    manager = rollout.source.WorkspaceManager
    original = manager.atomic_replace_source
    replacements = []

    def crash(workspace, path, content):
        original(workspace, path, content)
        replacements.append(path)
        raise KeyboardInterrupt()

    monkeypatch.setattr(manager, "atomic_replace_source", crash)
    with pytest.raises(KeyboardInterrupt):
        dispatch(branch, [mutation_call(branch.gateway)])
    monkeypatch.setattr(manager, "atomic_replace_source", original)
    if drift:
        path = branch.gateway.workspace / "README.md"
        path.write_text(path.read_text() + "\nUnrelated drift\n")
        with pytest.raises(ResumeContractMismatch):
            prepare(branch)
    else:
        prepare(branch)
        assert branch.gateway.accepted_mutations == 1
    assert len(replacements) == 1
    assert branch.new_provider_calls == 1


def test_probe_execution_without_durable_result_is_not_retried(branch, monkeypatch):
    original = branch.journal.append

    def crash(kind, payload=None):
        if kind == "action_finished" and payload["result"]["tool"] == "run_probe":
            raise KeyboardInterrupt()
        return original(kind, payload)

    monkeypatch.setattr(branch.journal, "append", crash)
    with pytest.raises(KeyboardInterrupt):
        dispatch(branch, [probe_call()])
    monkeypatch.setattr(branch.journal, "append", original)
    with pytest.raises(rollout.common.AbortExperiment) as error:
        prepare(branch)
    assert error.value.code == "TOOL_EXECUTION_UNKNOWN"
    assert branch.gateway.probe_sandbox.calls == 1


def test_unavailable_first_probe_is_censored_without_provider(branch):
    branch.gateway.probe_sandbox = None
    adapter = FullAdapter([])
    assert prepare(branch, adapter) is None
    assert branch.terminal["censored"] and branch.terminal["terminal"] == "LIMIT_REACHED"
    assert not adapter.sequence


def test_cleanup_uncertainty_aborts_without_releasing_probe_phase(branch):
    class UncertainCleanup(FakeProbe):
        def run_probe(self, *args, **kwargs):
            result = super().run_probe(*args, **kwargs)
            result["cleanup_failed"] = True
            result["execution_policy"]["cleanup_status"] = "unconfirmed"
            result["execution_policy_hash"] = sha256_json(result["execution_policy"])
            return result

    branch.gateway.probe_sandbox = UncertainCleanup()
    with pytest.raises(rollout.common.AbortExperiment) as error:
        dispatch(branch, [probe_call()])
    assert error.value.code == "SANDBOX_CLEANUP_FAILED"
    with pytest.raises(rollout.common.AbortExperiment):
        prepare(branch)
    assert not branch._new_events("probe_phase_released")
    assert branch.gateway.probe_sandbox.calls == 1
