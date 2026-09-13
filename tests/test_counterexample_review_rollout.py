"""Voluntary review diagnostic: synthetic tools/provider, never hidden evaluation."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_current_source_rollout import FullAdapter
from test_dev_probes import FakeProbe, probe_call
from test_dev_repair_recheck import CheckSandbox
from test_dev_tools import mutation_call, read_calls
from test_fresh_state_rollout import start

from diagnostics import counterexample_review_rollout as rollout
from patchloop.agent.model import EncryptedReasoningContinuationItem, ModelTurnError
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.errors import ContractError
from patchloop.sandbox.runner import SandboxResult
from patchloop.util import canonical_json, sha256_bytes, utc_now


class Checks:
    backend = "mock"
    supports_execution_deadline = True

    def __init__(self):
        self.calls = []

    def run_check(self, workspace, check, **kwargs):
        self.calls.append((check.id, kwargs))
        return SandboxResult(check.command, 0, "PUBLIC_MOCK_PASS", "", 1, False, False, 16)


class Adapter(FullAdapter):
    def execute_request(self, *args, **kwargs):
        raw = super().execute_request(*args, **kwargs)
        identity = self.calls[0].action_id if self.calls else "incomplete"
        return replace(raw, response_id="response-" + identity, provider_continuation=(
            EncryptedReasoningContinuationItem("reasoning-" + identity, "cipher-" + identity),
            *raw.provider_continuation[1:],
        ))


@pytest.fixture
def branch_factory(gateway_factory, monkeypatch):
    def make(label="B1"):
        gateway, journal, _ = gateway_factory(sandbox=Checks())
        gateway.probe_sandbox = FakeProbe(status="passed")
        active = rollout.engine.ActiveClock()
        gateway.deadline = ExecutionDeadline.from_remaining(1600, clock=active)
        branch = rollout.Branch(label, journal, ArtifactStore(journal.root / "artifacts"),
                                gateway, rollout.loop._RunCounters(), active, 200)
        append = journal.append
        with monkeypatch.context() as scoped:
            scoped.setattr(journal, "append", lambda kind, value: append(
                kind, {**value, "diagnostic_inherited": True}))
            start(branch, "seed-read", read_calls())
            journal.append("model_call_finished", {"turn_id": "seed-read", "tool_calls": []})
        branch._sync_accounting()
        return branch
    return make


@pytest.fixture
def branch(branch_factory):
    return branch_factory()


def prepare(branch, adapter=None):
    return branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task),
                                  adapter or Adapter([]))


def ledger(cap="0.50"):
    return DevCostLedger(Decimal(cap), pricing_for_model(rollout.design.MODEL))


def dispatch(branch, calls, *, adapter=None, cost=None, checkpoint=lambda _: None):
    adapter = adapter or Adapter(calls)
    prepared = prepare(branch, adapter)
    rollout.engine.dispatch(branch, adapter, cost or ledger(), prepared, checkpoint=checkpoint,
                            request_waits=rollout.requests.WAITS)
    return prepared[1]


def action(name, label, **arguments):
    if name == "stop_task":
        arguments.setdefault("reason_code", "insufficient_public_evidence")
    return RequestedTool(name=name, action_id=label, arguments=arguments,
                         turn_decision=PublicTurnDecision(
                             mode={"run_check": "verify", "stop_task": "stop",
                                   "finish_task": "finish"}[name],
                             basis="Respond to the recorded public observations."))


def test_initial_only_suffix_and_b_can_mutate_without_probe(branch):
    branch.label = "A1"
    a = prepare(branch)[1]
    branch.label = "B1"
    b = prepare(branch)[1]
    expected = copy.deepcopy(a)
    expected["input"][0]["content"] += rollout.design.PROMPT_SUFFIX
    assert b == expected and b["tool_choice"] == "required"
    assert "replace_text" in {t["name"] for t in b["tools"]}
    dispatch(branch, [mutation_call(branch.gateway)])
    assert branch.gateway.accepted_mutations == 1
    assert branch.gateway.probe_sandbox.calls == 0
    assert not branch._new_events("protocol_correction")
    assert not branch._new_events("probe_phase_released")


@pytest.mark.parametrize("with_probe", [False, True])
def test_native_feedback_mutation_check_finish_optional_probe(branch, with_probe):
    if with_probe:
        initial = dispatch(branch, [probe_call()])
        after = prepare(branch)[1]
        assert after["input"][:len(initial["input"])] == initial["input"]
        assert "PUBLIC_PROBE_OUTPUT" in canonical_json(after)
    dispatch(branch, [mutation_call(branch.gateway)])
    dispatch(branch, [action("run_check", "check", check_id="existing-unit-tests")])
    final_request = dispatch(branch, [action("finish_task", "finish")])
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert branch.terminal["submitted_artifact"]["content_hash"] == branch.gateway.current_diff_hash
    assert branch.terminal["accepted_mutations_since_checkpoint"] == 1
    assert branch.terminal["tool_actions"] == 3 + with_probe
    assert branch.terminal["provider_calls"] == 3 + with_probe
    assert len(branch.gateway.sandbox.calls) == 1
    assert branch.gateway.probe_sandbox.calls == with_probe
    assert branch.terminal["task_acceptance"] == "NOT_RUN"
    assert branch.terminal["private_evaluation"] == "NOT_RUN"
    assert not branch.terminal["official"]
    assert final_request["input"][0]["content"].count(rollout.design.PROMPT_SUFFIX) == 1
    items = final_request["input"]
    assert [i["call_id"] for i in items if i.get("type") == "function_call"] == [
        i["call_id"] for i in items if i.get("type") == "function_call_output"]
    ciphers = [i["encrypted_content"] for i in items if i.get("type") == "reasoning"]
    assert len(ciphers) == len(set(ciphers)) == 2 + with_probe
    assert "followup_state_contract" not in reconstruct_state(items)
    before = branch.journal.path.read_bytes()
    assert prepare(branch) is None and branch.journal.path.read_bytes() == before


def test_automatic_recheck_is_preserved_counted_and_not_a_native_call(branch):
    branch.gateway.sandbox = CheckSandbox()
    first = mutation_call(branch.gateway)
    dispatch(branch, [first])
    dispatch(branch, [action("run_check", "failed-check", check_id="existing-unit-tests")])
    repair = first.model_copy(update={"action_id": "repair", "arguments": {
        **first.arguments, "old_text": first.arguments["new_text"],
        "new_text": first.arguments["new_text"] + "\n# public repair\n",
    }})
    dispatch(branch, [repair])
    assert len(branch.gateway.sandbox.calls) == 1
    before = branch.new_provider_calls
    prepared = prepare(branch)[1]
    assert branch.new_provider_calls == before == 3
    assert len(branch.gateway.sandbox.calls) == 2
    assert branch.new_tools == 4 and branch.counters.tool_actions == 6
    receipt = reconstruct_state(prepared["input"])["repair_recheck"]["last_result"]
    assert receipt["origin"] == "harness" and receipt["evidence_currency"] == "current"
    assert receipt["parent_action_id"] == "repair"
    assert all(i.get("call_id") != receipt["action_id"] for i in prepared["input"])
    prepare(branch)
    assert len(branch.gateway.sandbox.calls) == 2
    assert len(branch._new_events("repair_recheck_started")) == 1
    dispatch(branch, [action("finish_task", "finish")])
    assert branch.terminal["tool_actions"] == 5
    assert branch.terminal["accepted_mutations_since_checkpoint"] == 2


def test_reasoning_only_correction_survives_unconsumed_turn_and_never_saves_plaintext(branch):
    class Incomplete(Adapter):
        def execute_request(self, *args, **kwargs):
            return replace(super().execute_request(*args, **kwargs),
                           output_item_types=("reasoning",), response_status="incomplete",
                           response_incomplete_reason="max_output_tokens",
                           error=ModelTurnError("incomplete_response", "UNSAVED_RAW_REASONING"))

    dispatch(branch, [], adapter=Incomplete([]))
    assert "max_output_tokens" in canonical_json(prepare(branch)[1])
    branch.correction = None
    repeated = prepare(branch)[1]
    assert "max_output_tokens" in repeated["input"][-1]["content"]
    assert sum(i.get("encrypted_content") == "cipher-incomplete"
               for i in repeated["input"]) == 1
    dispatch(branch, [probe_call()])
    following = reconstruct_state(prepare(branch)[1]["input"])
    assert all(card["attempt"] != "protocol"
               for card in following["recent_attempt_result_next_question"])
    assert branch.correction is None
    persisted = branch.journal.path.read_text() + "".join(
        p.read_text() for p in branch.store.root.rglob("*") if p.is_file())
    assert "UNSAVED_RAW_REASONING" not in persisted


@pytest.mark.parametrize("fault,code", [
    ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("usage_recorded", "PROVIDER_CONTINUATION_ERROR"),
    ("decision_recorded", None), ("actions_finished", None), ("batch_finished", None),
])
def test_faults_reconcile_identical_probe_once_without_provider_retry(branch, fault, code):
    adapter = Adapter([probe_call()])

    def crash(point):
        if point == fault:
            raise RuntimeError("injected crash")

    with pytest.raises(RuntimeError, match="injected crash"):
        dispatch(branch, [], adapter=adapter, checkpoint=crash)
    if code:
        with pytest.raises(rollout.engine.AbortExperiment) as error:
            prepare(branch, adapter)
        assert error.value.code == code and branch.gateway.probe_sandbox.calls == 0
    else:
        prepare(branch, adapter)
        assert branch.gateway.probe_sandbox.calls == 1
        assert branch.new_tools == 1 and branch.new_provider_calls == 1
        assert len(branch._new_events("action_finished")) == 1
    assert adapter.sequence == (["count"] if fault == "dispatch_recorded" else ["count", "create"])


@pytest.mark.parametrize("fault", ["decision_recorded", "actions_finished", "batch_finished"])
def test_pending_mutation_before_horizon_never_reapplied(branch, fault):
    def crash(point):
        if point == fault:
            raise RuntimeError("mutation crash")

    with pytest.raises(RuntimeError, match="mutation crash"):
        dispatch(branch, [mutation_call(branch.gateway)], checkpoint=crash)
    branch.gateway.limits = branch.gateway.limits.model_copy(update={"max_model_calls": 2})
    assert prepare(branch) is None
    assert branch.gateway.accepted_mutations == 1
    assert branch.terminal["terminal"] == "LIMIT_REACHED"
    assert branch.terminal["provider_calls"] == 1
    assert len(branch._new_events("action_finished")) == 1


def test_late_response_preserved_without_tools_and_terminal_needs_no_git(branch):
    now = [0.0]
    branch.clock.clock = lambda: now[0]
    branch.gateway.deadline = ExecutionDeadline(1, clock=lambda: now[0])

    class Late(Adapter):
        def execute_request(self, *args, **kwargs):
            raw = super().execute_request(*args, **kwargs)
            now[0] = 2
            return raw

    with pytest.raises(rollout.engine.AbortExperiment) as error:
        dispatch(branch, [], adapter=Late([probe_call()]))
    assert error.value.code == "LIMIT_REACHED" and branch.gateway.probe_sandbox.calls == 0
    assert len(branch._new_events("diagnostic_response_processed")) == 1
    result = branch.finish(error.value.code, censored=True)
    assert result["recorded_visible_checks"][0]["status"] == "NOT_RUN"
    assert result["provider_calls"] == 1 and result["cost_nanos"] > 0


@pytest.mark.parametrize("failure,expected", [
    ("count", "COUNT_TIMEOUT_OR_UNKNOWN"), ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
])
def test_uncertainty_stops_all_branches_and_never_leaks_sdk_text(branch_factory, failure, expected):
    branches = [branch_factory(label) for label in rollout.ORDER]
    adapters = []

    def factory(config):
        adapter = Adapter([probe_call()], failure=failure, mismatch=failure == "billing")
        adapters.append(adapter)
        return adapter

    result = rollout.drive(SimpleNamespace(package=SimpleNamespace(
        public=branches[0].gateway.public_task)), branches, factory)
    assert result["terminal"] == expected and len(adapters) == 1
    assert all(b.gateway.probe_sandbox.calls == 0 for b in branches)
    assert all(b.terminal["terminal"] == expected for b in branches)
    assert result["provider_cost_known"] is (failure == "count")
    assert all("SECRET_SDK_ERROR_SENTINEL" not in b.journal.path.read_text() for b in branches)


def test_four_branches_are_round_robin_and_caps_do_not_transfer(branch_factory):
    branches = [branch_factory(label) for label in rollout.ORDER]
    requested = []

    class Spend(Adapter):
        def count_input_tokens_v2(self, request, **kwargs):
            self.count = 200000  # Uncached cost reservation = $0.2625; actual = $0.2625.
            assert request["max_output_tokens"] == 25000
            return super().count_input_tokens_v2(request, **kwargs)

        def execute_request(self, *args, **kwargs):
            return replace(super().execute_request(*args, **kwargs), output_tokens=25000)

    def factory(config):
        ordinal = len(requested)
        requested.append(ordinal)
        # A1 is censored on its second request; the other three retain their own cap.
        label = rollout.ORDER[ordinal % 4]
        call = (probe_call(label) if ordinal < 4 else
                action("stop_task", label + "-stop", summary="Public evidence only."))
        return Spend([call]) if label == "A1" else Adapter([call])

    progress = []
    result = rollout.drive(SimpleNamespace(package=SimpleNamespace(
        public=branches[0].gateway.public_task)), branches, factory, progress=progress.append)
    assert [p["branch"] for p in progress] == list(rollout.ORDER) * 2
    assert result["terminal"] == "ROLLOUTS_COMPLETED"
    assert result["branches"][0]["terminal"] == "COST_CAP_REACHED"
    assert all(b["terminal"] == "AGENT_STOPPED" for b in result["branches"][1:])
    assert result["new_provider_calls"] == 7 and result["new_input_count_calls"] == 8
    assert result["recorded_cost_nanos"] <= 2_000_000_000
    assert all(b["cost_nanos"] <= 500_000_000 for b in result["branches"])


def test_eight_new_response_bound_does_not_dispatch_a_ninth(branch):
    adapters = []

    def factory(config):
        adapter = Adapter([probe_call("probe-" + str(len(adapters)))])
        adapters.append(adapter)
        return adapter

    result = rollout.drive(SimpleNamespace(package=SimpleNamespace(
        public=branch.gateway.public_task)), [branch], factory)
    assert result["new_provider_calls"] == result["new_tool_actions"] == 8
    assert result["branches"][0]["terminal"] == "LIMIT_REACHED"
    assert result["branches"][0]["message"] == "eight-response diagnostic bound"
    assert adapters[-1].sequence == [] and branch.gateway.probe_sandbox.calls == 8


def test_cleanup_uncertainty_stops_before_another_branch(branch_factory):
    branches = [branch_factory(label) for label in ("A1", "B1")]

    class Unclean(FakeProbe):
        def run_probe(self, *args, **kwargs):
            return {**super().run_probe(*args, **kwargs), "cleanup_failed": True}

    branches[0].gateway.probe_sandbox = Unclean()
    called = []

    def factory(config):
        called.append(config)
        return Adapter([probe_call()])

    result = rollout.drive(SimpleNamespace(package=SimpleNamespace(
        public=branches[0].gateway.public_task)), branches, factory)
    assert result["terminal"] == "SANDBOX_CLEANUP_FAILED"
    assert len(called) == 1 and branches[1].gateway.probe_sandbox.calls == 0
    assert result["provider_cost_known"] and result["recorded_cost_nanos"] > 0


def test_one_shot_run_wrapper_mock_does_not_touch_credentials_or_live_preflight(
    tmp_path, monkeypatch, branch_factory,
):
    plan_root = tmp_path / "packet"
    plan_root.mkdir()
    ArtifactStore(plan_root).write_text_immutable(plan_root / "plan.json", "{}")
    branches = {label: branch_factory(label) for label in rollout.ORDER}
    plan = SimpleNamespace(package=SimpleNamespace(public=branches["A1"].gateway.public_task),
                           checkpoint={"source_root": str(tmp_path / "immutable-source")})
    monkeypatch.setattr(rollout, "validate", lambda _: (plan, {}))
    monkeypatch.setattr(rollout, "initialize_branch", lambda p, label, *args: branches[label])

    def forbidden(*args, **kwargs):
        pytest.fail("mock admission must not touch a key, live preflight, or client")

    monkeypatch.setattr(rollout, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout.requests, "DiagnosticClient", type("UnusedClient", (), {}))
    monkeypatch.setattr(rollout.loop, "_live_source_preflight", forbidden)
    monkeypatch.setattr(rollout.loop, "_live_sandbox_preflight", forbidden)
    args = dict(approval_packet_hash=sha256_bytes(b"{}"), cap=rollout.TOTAL_CAP,
                credential_file=rollout.repository_root() / ".env",
                pricing_verified_on=utc_now().date().isoformat(), sandbox=Checks(),
                probe=FakeProbe(), adapter_factory=lambda _: Adapter([
                    action("stop_task", "stop", summary="Synthetic public conclusion.")]))
    root = tmp_path / "result"
    result = rollout.run(plan_root, root, **args)
    assert result == rollout.read(root / "result.json")
    assert result["provider_free"] and result["terminal"] == "ROLLOUTS_COMPLETED"
    assert result["new_provider_calls"] == 4 and result["recorded_cost_nanos"] == 4800000
    assert all(b["terminal"] == "AGENT_STOPPED" for b in result["branches"])
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ContractError, match="fresh disjoint external root"):
        rollout.run(plan_root, root, **args)
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize("bad", ["packet", "cap", "credential", "date"])
def test_approval_mismatch_before_adapter_key_or_result_root(tmp_path, monkeypatch, bad):
    plan_root = tmp_path / "plan"
    plan_root.mkdir()
    ArtifactStore(plan_root).write_text_immutable(plan_root / "plan.json", "{}")
    monkeypatch.setattr(rollout, "validate", lambda _: (SimpleNamespace(), {}))
    args = dict(approval_packet_hash=sha256_bytes(b"{}"), cap=rollout.TOTAL_CAP,
                credential_file=rollout.repository_root() / ".env",
                pricing_verified_on=utc_now().date().isoformat())
    key, value = {"packet": ("approval_packet_hash", "bad"), "cap": ("cap", Decimal("5")),
                  "credential": ("credential_file", tmp_path / ".env"),
                  "date": ("pricing_verified_on", "2000-01-01")}[bad]
    args[key] = value
    with pytest.raises(ContractError):
        rollout.run(plan_root, tmp_path / "result", **args,
                    adapter_factory=lambda _: pytest.fail("no provider admission"))
    assert not (tmp_path / "result").exists()


def test_real_frozen_source_restores_exact_requests_counts_notes_and_no_execution(tmp_path):
    if not rollout.DESIGN.exists():
        pytest.skip("external evidence is not installed")
    before = {p: sha256_bytes(p.read_bytes()) for p in rollout.DESIGN.rglob("*") if p.is_file()}
    saved = json.loads((rollout.DESIGN / "packet.json").read_bytes())
    if saved["runtime_hash"] != rollout.design.runtime_content_hash():
        with pytest.raises(ValueError, match="source runtime/config mismatch"):
            rollout.load_plan()
        assert before == {p: sha256_bytes(p.read_bytes()) for p in before}
        return
    plan = rollout.load_plan()
    envelope = rollout.prepare(tmp_path / "plan")
    assert rollout.validate(tmp_path / "plan")[1] == envelope
    sandbox, probe = Checks(), FakeProbe()
    for label in ("A1", "B1"):
        branch = rollout.initialize_branch(plan, label, tmp_path / "branches", sandbox, probe,
                                           ExecutionDeadline.from_remaining(90))
        request = branch.prepare_request(plan.package, Adapter([]))[1]
        assert rollout.design.wire(request) == (rollout.DESIGN / f"{label[0]}.json").read_bytes()
        assert branch.counters.model_calls == 21 and branch.counters.tool_actions == 22
        assert branch.inherited_accepted_mutations == branch.gateway.accepted_mutations == 2
        assert branch.new_tools == branch.new_provider_calls == branch.new_cost_nanos == 0
        state = reconstruct_state(request["input"])
        assert state["working_notes"] == plan.state["working_notes"]
        assert state["visible_check_status"] == plan.state["visible_check_status"]
        assert len([i for i in request["input"] if i.get("type") == "reasoning"]) == 21
        assert "finish_task" in {t["name"] for t in request["tools"]}
        branch.finish("NO_CALL_REHEARSAL")
        assert branch.terminal["accepted_mutations_since_checkpoint"] == 0
    assert sandbox.calls == [] and probe.calls == 0
    assert before == {p: sha256_bytes(p.read_bytes()) for p in before}
