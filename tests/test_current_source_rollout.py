from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_dev_tools import mutation_call, read_calls
from test_fresh_state_rollout import Adapter, start

from diagnostics import current_source_rollout as rollout
from diagnostics import current_source_view as view
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner as loop
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError
from patchloop.util import canonical_json, utc_now


class FullAdapter(Adapter):
    def request_payload(self, items, schemas, **_):
        return {**rollout.shared.SETTINGS, "input": items, "tools": schemas,
                "reasoning": {"effort": "medium"}}


@pytest.fixture
def branch(gateway_factory):
    gateway, journal, _ = gateway_factory()
    active = rollout.common.ActiveClock()
    gateway.deadline = ExecutionDeadline.from_remaining(1601, clock=active)
    result = rollout.Branch("A1", journal, ArtifactStore(journal.root / "artifacts"),
                            gateway, loop._RunCounters(), active, 0)
    start(result, "read-first", read_calls())
    return result


def prepare(branch, adapter=None):
    return branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task),
                                  adapter or FullAdapter([]))


def ledger():
    return DevCostLedger(Decimal("1.20"), pricing_for_model(rollout.shared.MODEL))


def test_a_b_change_only_latest_selected_source_delivery(branch):
    a = prepare(branch)[1]
    branch.label = "B1"
    b = prepare(branch)[1]
    # The same state computation may differ only in its measured active time.
    # Unit clocks are frozen, so the entire A/B request can be compared exactly.
    expected, metrics = view.inline_current_sources(a)
    assert b == expected
    assert b["input"][:-1] == a["input"][:-1]
    assert b["tools"] == a["tools"]
    assert metrics["selected_ranges_equal"]
    # Tiny fixtures may already be inline; the frozen case below exercises 15 refs.
    assert metrics["removed_current_reference_ranges"] >= 0
    assert "followup_state_contract" not in b["input"][-1]["content"]


@pytest.mark.parametrize("label", ["A1", "B1"])
def test_new_exchange_preserves_prefix_and_ciphertext_once(branch, label):
    branch.label = label
    adapter = FullAdapter([mutation_call(branch.gateway)])
    prepared = prepare(branch, adapter)
    prefix = copy.deepcopy(prepared[1]["input"])
    rollout.common.dispatch(branch, adapter, ledger(), prepared)
    after = prepare(branch)[1]["input"]
    assert after[:len(prefix)] == prefix
    assert view.wire(after[:len(prefix)]) == view.wire(prefix)
    assert sum(i.get("encrypted_content") == "cipher-new" for i in after) == 1
    assert [i["call_id"] for i in after if i.get("type") == "function_call"] == [
        i["call_id"] for i in after if i.get("type") == "function_call_output"]
    state = rollout.reconstruct_state(after)
    assert state["current_diff"]["patch_hash"] == branch.gateway.current_diff_hash
    if label == "B1":
        assert all(not g.get("content_delivery") for g in state["current_sources"])


def test_frozen_first_request_is_exact_a_or_inline_b(branch):
    a = prepare(branch)[1]
    branch.initial_request, branch.initial_context = copy.deepcopy(a), "{}"
    assert prepare(branch)[1] == a
    branch.initial_request, branch.label = copy.deepcopy(a), "B1"
    assert prepare(branch)[1] == view.inline_current_sources(a)[0]


def test_frozen_policy_mismatch_fails_before_count(branch):
    branch.initial_request = prepare(branch)[1]
    branch.initial_request["tools"] = []
    adapter = FullAdapter([])
    with pytest.raises(ContractError, match="current policy differs"):
        prepare(branch, adapter)
    assert adapter.sequence == []


def test_eight_response_bound_stops_before_count(branch):
    branch.new_provider_calls = 8
    adapter = FullAdapter([])
    assert prepare(branch, adapter) is None
    assert branch.terminal["terminal"] == "LIMIT_REACHED"
    assert branch.terminal["censored"]
    assert adapter.sequence == []


@pytest.mark.parametrize("fault", ["dispatch_recorded", "provider_returned", "usage_recorded",
                                   "decision_recorded", "actions_finished", "batch_finished"])
def test_crash_does_not_retry_provider_or_mutation(branch, fault):
    adapter = FullAdapter([mutation_call(branch.gateway)])
    prepared = prepare(branch, adapter)

    def crash(point):
        if point == fault:
            raise RuntimeError("fault")

    with pytest.raises(RuntimeError, match="fault"):
        rollout.common.dispatch(branch, adapter, ledger(), prepared, checkpoint=crash)
    assert adapter.sequence.count("create") <= 1
    assert branch.gateway.accepted_mutations <= 1
    assert sum(e["event_type"] == "provider_call_started" for e in branch.journal.events()) == 1


@pytest.mark.parametrize("failure,terminal", [("count", "COUNT_TIMEOUT_OR_UNKNOWN"),
                                               ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN")])
def test_uncertainty_is_not_retried(branch, failure, terminal):
    adapter = FullAdapter([], failure=failure)
    with pytest.raises(rollout.common.AbortExperiment) as error:
        rollout.common.dispatch(branch, adapter, ledger(), prepare(branch, adapter))
    assert error.value.code == terminal
    assert adapter.sequence.count("count") == 1
    assert adapter.sequence.count("create") <= 1
    assert "SECRET_SDK_ERROR_SENTINEL" not in branch.journal.path.read_text()


def test_full_shared_cap_censors_before_create(branch):
    cost = ledger()
    cost.spent_nanos = cost.cap_nanos
    adapter = FullAdapter([])
    with pytest.raises(rollout.common.AbortExperiment) as error:
        rollout.common.dispatch(branch, adapter, cost, prepare(branch, adapter))
    assert error.value.code == "COST_CAP_REACHED"
    assert adapter.sequence == ["count"]


def test_mock_mutation_check_finish_with_inline_history(branch):
    branch.label = "B1"
    calls = [mutation_call(branch.gateway), RequestedTool(
        name="run_check", action_id="new-check", arguments={"check_id": "existing-unit-tests"},
        turn_decision=PublicTurnDecision(mode="verify", basis="Check repaired public code"),
    ), RequestedTool(name="finish_task", action_id="new-finish", arguments={},
                     turn_decision=PublicTurnDecision(mode="finish", basis="Public check passed"))]
    cost = ledger()
    for call in calls:
        adapter = FullAdapter([call])
        rollout.common.dispatch(branch, adapter, cost, prepare(branch, adapter))
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert branch.terminal["submitted_artifact"]["content_hash"] == branch.gateway.current_diff_hash
    assert branch.terminal["private_evaluation"] == "NOT_RUN"


def test_frozen_plan_is_read_only_and_has_no_post_cutoff_actions():
    if not rollout.REQUEST.exists():
        pytest.skip("external frozen diagnostic evidence is not installed")
    source = rollout.SOURCE / "runs/run_dev_9b91e06c13ff4bd3.jsonl"
    before = source.read_bytes()
    plan = rollout.load_plan()
    assert source.read_bytes() == before
    assert len(plan.prefix) == 222
    assert plan.requests["A"]["input"][:-1] == plan.requests["B"]["input"][:-1]
    assert plan.metrics["selected_line_count"] == 385
    assert plan.metrics["removed_current_reference_ranges"] == 15
    assert plan.envelope["runtime_hash"] != rollout.EXECUTING_RUNTIME


def test_envelope_mismatch_stops_before_adapter(tmp_path, monkeypatch):
    plan = SimpleNamespace(requests={"A": {"x": 1}, "B": {"x": 2}})
    monkeypatch.setattr(rollout, "load_plan", lambda: plan)
    monkeypatch.setattr(rollout, "envelope_for", lambda _: {"expected": 1})
    root = tmp_path / "plan"
    root.mkdir()
    (root / "plan.json").write_text(canonical_json({"expected": 2}))
    with pytest.raises(ContractError, match="prepared experiment changed"):
        rollout.run(root, tmp_path / "live", credential_file=rollout.repository_root() / ".env",
                    cap=Decimal("1.20"), pricing_verified_on=utc_now().date().isoformat(),
                    adapter_factory=lambda _: pytest.fail("must not instantiate provider"))
    assert not (tmp_path / "live").exists()


@pytest.mark.parametrize("failure", [None, "count", "create", "billing"])
def test_four_branch_driver_stops_on_uncertainty(gateway_factory, tmp_path, monkeypatch, failure):
    branches = []
    for label in rollout.ORDER:
        gateway, journal, _ = gateway_factory()
        active = rollout.common.ActiveClock()
        gateway.deadline = ExecutionDeadline.from_remaining(1601, clock=active)
        branch = rollout.Branch(label, journal, ArtifactStore(journal.root / "artifacts"),
                                gateway, loop._RunCounters(), active, 0)
        start(branch, "seed-read", read_calls())
        branches.append(branch)
    package = SimpleNamespace(public=branches[0].gateway.public_task)
    plan = SimpleNamespace(package=package, requests={"A": {}, "B": {}})
    monkeypatch.setattr(rollout, "load_plan", lambda: plan)
    monkeypatch.setattr(rollout, "envelope_for", lambda _: {"unit_test": True})
    monkeypatch.setattr(rollout, "initialize_branch",
                        lambda _, label, *args: branches[rollout.ORDER.index(label)])
    root = tmp_path / "plan"
    root.mkdir()
    (root / "plan.json").write_text(canonical_json({"unit_test": True}))
    for arm in ("A", "B"):
        (root / f"{arm}.json").write_bytes(b"{}")
    seen = []

    def factory(_):
        call = RequestedTool(name="stop_task", action_id="stop-" + str(len(seen)), arguments={
            "reason_code": "no_safe_scoped_mutation", "summary": "Synthetic diagnostic stop",
        }, turn_decision=PublicTurnDecision(mode="stop", basis="Synthetic test"))
        result = FullAdapter([call], failure=None if failure == "billing" else failure,
                             mismatch=failure == "billing")
        seen.append(result)
        return result

    result = rollout.run(root, tmp_path / "result",
                         credential_file=rollout.repository_root() / ".env",
                         cap=Decimal("1.20"), pricing_verified_on=utc_now().date().isoformat(),
                         adapter_factory=factory, sandbox=object(), probe=object())
    if failure is None:
        assert result["terminal"] == "ROLLOUTS_COMPLETED"
        assert result["new_provider_calls"] == 4
        assert all(b["terminal"] == "AGENT_STOPPED" for b in result["branches"])
    else:
        assert len(seen) == 1
        assert result["terminal"] == ("COUNT_TIMEOUT_OR_UNKNOWN" if failure == "count"
                                      else "PROVIDER_TIMEOUT_OR_UNKNOWN")
        assert all(b["censored"] for b in result["branches"])
    assert "SECRET_SDK_ERROR_SENTINEL" not in canonical_json(result)
    assert result == json.loads((tmp_path / "result/result.json").read_bytes())


def test_real_frozen_checkpoint_initializes_without_execution(tmp_path):
    if not rollout.REQUEST.exists():
        pytest.skip("external frozen diagnostic evidence is not installed")
    from patchloop.sandbox import LocalSandbox
    from patchloop.sandbox.probes import DockerProbeSandbox

    plan = rollout.load_plan()
    branch = rollout.initialize_branch(plan, "B1", tmp_path, LocalSandbox(), DockerProbeSandbox(),
                                        ExecutionDeadline.from_remaining(100))
    assert branch.counters.model_calls == branch.counters.tool_actions == 20
    assert branch.gateway.accepted_mutations == 3
    prepared = prepare(branch)
    assert view.wire(prepared[1]) == view.wire(plan.requests["B"])
    assert branch.gateway.current_diff_hash == plan.manifest["current_diff_hash"]
    rows = branch.journal.events()
    assert not any(e["event_type"] == "provider_call_started"
                   and not e["payload"].get("diagnostic_inherited") for e in rows)
    assert all(e["payload"].get("diagnostic_inherited") for e in rows
               if e["event_type"] == "action_finished")
