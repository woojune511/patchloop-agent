"""Native diagnostic integration with fake providers/public sandboxes only."""
from __future__ import annotations

import json
from dataclasses import fields, replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_counterexample_review_rollout import Adapter, Checks, action
from test_dev_probes import FakeProbe, probe_call
from test_dev_tools import mutation_call, read_calls
from test_fresh_state_rollout import start

from diagnostics import failure_given_repair_rollout as rollout
from patchloop.agent.model import ModelTurnError
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, utc_now


def synthetic_report(diff_hash):
    return {
        "kind": "operator_public_bug_report_v1", "origin": "operator_executed_public_diagnostic",
        "observed_on_diff_hash": diff_hash, "input": {"path": "a/../b/../c"},
        "environment": {"platform": "Linux", "python": "3.12.13", "umask": "0o022"},
        "expected": {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "b", "c")]},
        "actual": {"error": None, "entries": [[p, "dir", "0o755"] for p in ("a", "c")]},
    }


@pytest.fixture
def factory(gateway_factory, monkeypatch):
    def make(label="F1", *, checked=False):
        gateway, journal, _ = gateway_factory(sandbox=Checks())
        gateway.probe_sandbox = FakeProbe(status="passed")
        active = rollout.native.engine.ActiveClock()
        gateway.deadline = ExecutionDeadline.from_remaining(1600, clock=active)
        branch = rollout.Branch(label, journal, ArtifactStore(journal.root / "artifacts"),
                                gateway, rollout.native.loop._RunCounters(), active, 200)
        append = journal.append
        with monkeypatch.context() as scoped:
            scoped.setattr(journal, "append", lambda kind, value: append(
                kind, {**value, "diagnostic_inherited": True}))
            for label, calls in [("seed-read", read_calls()), *([
                ("seed-mutation", [mutation_call(gateway)]),
                ("seed-check", [action("run_check", "seed-check", check_id="existing-unit-tests")]),
            ] if checked else [])]:
                start(branch, label, calls)
                journal.append("model_call_finished", {"turn_id": label, "tool_calls": []})
        branch.inherited_accepted_mutations = gateway.accepted_mutations
        branch.bind_report(synthetic_report(gateway.current_diff_hash))
        branch._sync_accounting()
        return branch
    return make


def prepare(branch, adapter=None):
    return branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task),
                                  adapter or Adapter([]))


def dispatch(branch, calls=(), *, adapter=None, checkpoint=lambda _: None):
    adapter = adapter or Adapter(list(calls))
    prepared = prepare(branch, adapter)
    ledger = DevCostLedger(rollout.BRANCH_CAP, pricing_for_model(rollout.design.seed.MODEL))
    ledger.spent_nanos = branch.new_cost_nanos
    rollout.native.engine.dispatch(branch, adapter, ledger, prepared, checkpoint=checkpoint,
                                   request_waits=rollout.native.requests.WAITS)
    return prepared[1]


def reopen(branch):
    values = {f.name: getattr(branch, f.name) for f in fields(branch)}
    values.update(initial_request=None, terminal=None, correction=None)
    values["gateway"] = DevToolGateway(
        workspace=branch.gateway.workspace, public_task=branch.gateway.public_task,
        sandbox=branch.gateway.sandbox, probe_sandbox=branch.gateway.probe_sandbox,
        journal=branch.journal, limits=branch.gateway.limits, deadline=branch.gateway.deadline)
    return rollout.Branch(**values)


def test_report_is_durable_single_overlay_in_context_and_input_without_counter_credit(factory):
    branch = factory()
    before = (branch.counters.model_calls, branch.counters.tool_actions,
              branch.gateway.accepted_mutations)
    _, request, _ = prepare(branch)
    event = branch._new_events("turn_started")[-1]
    context_ref = Artifact.model_validate(event["context_artifact"])
    context = json.loads(branch.store.read_bytes(context_ref))
    state = reconstruct_state(request["input"])
    assert context[rollout.design.FIELD] == state[rollout.design.FIELD]
    assert state[rollout.design.FIELD]["currency"] == "current_candidate"
    assert before == (branch.counters.model_calls, branch.counters.tool_actions,
                      branch.gateway.accepted_mutations)
    assert "counterexample_review>" not in canonical_json(request)
    assert not branch._new_events("review_instruction_recorded")
    assert len(branch._new_events("operator_feedback_projected")) == 1
    assert len(branch._new_events("operator_feedback_bound")) == 1
    assert rollout.design.FIELD not in canonical_json([
        r.model_dump(mode="json") for r in branch.latest])
    branch.bind_report(branch.report())
    assert len(branch._new_events("operator_feedback_bound")) == 1


def test_repair_probe_check_finish_keep_cipher_native_history_and_expire_report(factory):
    branch = factory()
    initial = dispatch(branch, [mutation_call(branch.gateway)])
    after = prepare(branch)[1]
    assert after["input"][:len(initial["input"])] == initial["input"]
    currency = reconstruct_state(after["input"])[rollout.design.FIELD]["currency"]
    assert currency == "historical_candidate"
    dispatch(branch, [probe_call()])
    assert "PUBLIC_PROBE_OUTPUT" in canonical_json(prepare(branch)[1])
    dispatch(branch, [action("run_check", "check", check_id="existing-unit-tests")])
    last = dispatch(branch, [action("finish_task", "finish")])
    assert branch.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
    assert branch.terminal["accepted_mutations_since_checkpoint"] == 1
    assert branch.terminal["provider_calls"] == branch.terminal["tool_actions"] == 4
    assert branch.terminal["submitted_artifact"]["content_hash"] == branch.gateway.current_diff_hash
    assert branch.terminal["task_acceptance"] == "NOT_RUN" and not branch.terminal["official"]
    ciphers = [i["encrypted_content"] for i in last["input"] if i.get("type") == "reasoning"]
    assert len(ciphers) == len(set(ciphers)) == 3
    items = last["input"]
    assert [i["call_id"] for i in items if i.get("type") == "function_call"] == [
        i["call_id"] for i in items if i.get("type") == "function_call_output"]
    before = branch.journal.path.read_bytes()
    assert prepare(reopen(branch)) is None and branch.journal.path.read_bytes() == before


def test_public_pass_can_finish_without_repair_or_probe_not_new_success(factory):
    branch = factory(checked=True)
    checks = len(branch.gateway.sandbox.calls)
    request = dispatch(branch, [action("finish_task", "finish")])
    assert reconstruct_state(request["input"])["workflow_gate"] == "ready_to_submit"
    assert branch.terminal["accepted_mutations_since_checkpoint"] == 0
    assert branch.gateway.probe_sandbox.calls == 0 and len(branch.gateway.sandbox.calls) == checks
    assert branch.terminal["provider_calls"] == branch.terminal["tool_actions"] == 1


def test_rollback_keeps_report_current_and_no_forced_recovery_read(factory):
    branch = factory()
    edit = mutation_call(branch.gateway)
    oversized = edit.model_copy(update={"arguments": {
        **edit.arguments, "new_text": edit.arguments["new_text"] + "\n# excessive\n" * 100}})
    baseline = branch.gateway.current_diff_hash
    dispatch(branch, [oversized])
    state = reconstruct_state(prepare(branch)[1]["input"])
    assert branch.gateway.current_diff_hash == baseline and branch.gateway.accepted_mutations == 0
    assert state[rollout.design.FIELD]["currency"] == "current_candidate"
    assert "replace_text" in state["available_tool_names"]
    assert state["last_failed_mutation"] is not None


def test_incomplete_correction_and_report_survive_reopen_without_plain_reasoning(factory):
    class Incomplete(Adapter):
        def execute_request(self, *args, **kwargs):
            return replace(super().execute_request(*args, **kwargs),
                           output_item_types=("reasoning",), response_status="incomplete",
                           response_incomplete_reason="max_output_tokens",
                           error=ModelTurnError("incomplete_response", "RAW_REASONING_SENTINEL"))

    branch = factory()
    dispatch(branch, adapter=Incomplete([]))
    prepare(branch)  # A turn_started record alone must not consume correction.
    restored = reopen(branch)
    request = prepare(restored)[1]
    assert "max_output_tokens" in request["input"][-1]["content"]
    assert reconstruct_state(request["input"])[rollout.design.FIELD] is not None
    assert sum(i.get("encrypted_content") == "cipher-incomplete" for i in request["input"]) == 1
    dispatch(restored, [probe_call()])
    state = reconstruct_state(prepare(restored)[1]["input"])
    assert all(c["attempt"] != "protocol" for c in state["recent_attempt_result_next_question"])
    persisted = branch.journal.path.read_bytes() + b"".join(
        p.read_bytes() for p in branch.store.root.rglob("*") if p.is_file())
    assert b"RAW_REASONING_SENTINEL" not in persisted


@pytest.mark.parametrize("fault,code", [
    ("dispatch_recorded", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("provider_returned", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("usage_recorded", "PROVIDER_CONTINUATION_ERROR"),
    ("decision_recorded", None), ("actions_finished", None), ("batch_finished", None),
])
def test_crash_reopen_never_retries_provider_or_duplicates_mutation(factory, fault, code):
    branch = factory()
    adapter = Adapter([mutation_call(branch.gateway)])

    def crash(point):
        if point == fault:
            raise RuntimeError("injected crash")

    with pytest.raises(RuntimeError, match="injected crash"):
        dispatch(branch, adapter=adapter, checkpoint=crash)
    restored = reopen(branch)
    if code:
        with pytest.raises(rollout.native.engine.AbortExperiment) as error:
            prepare(restored, adapter)
        assert error.value.code == code and restored.gateway.accepted_mutations == 0
    else:
        after = prepare(restored, adapter)[1]
        assert restored.gateway.accepted_mutations == 1 and restored.new_tools == 1
        assert reconstruct_state(after["input"])[rollout.design.FIELD]["currency"] == (
            "historical_candidate")
        prepare(restored, adapter)
        assert len(restored._new_events("action_finished")) == 1
    assert adapter.sequence == (["count"] if fault == "dispatch_recorded" else ["count", "create"])


def test_corrupt_report_before_pending_action_stops_replay(factory):
    branch = factory()

    def crash(point):
        if point == "decision_recorded":
            raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        dispatch(branch, [mutation_call(branch.gateway)], checkpoint=crash)
    binding = branch._new_events("operator_feedback_bound")[0]
    ref = Artifact.model_validate(binding["report_artifact"])
    Path(ref.path).write_bytes(b"corrupted")
    restored = reopen(branch)
    with pytest.raises(rollout.native.engine.AbortExperiment) as error:
        prepare(restored)
    assert error.value.code == "OPERATOR_FEEDBACK_ERROR"
    assert restored.gateway.accepted_mutations == 0


@pytest.mark.parametrize("failure,code", [
    ("count", "COUNT_TIMEOUT_OR_UNKNOWN"), ("create", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
    ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
])
def test_uncertainty_stops_both_branches(factory, failure, code):
    branches = [factory(label) for label in rollout.ORDER]
    adapters = []

    def adapter(config):
        result = Adapter([probe_call()], failure=failure, mismatch=failure == "billing")
        adapters.append(result)
        return result

    result = rollout.drive(SimpleNamespace(package=SimpleNamespace(
        public=branches[0].gateway.public_task)), branches, adapter)
    assert result["terminal"] == code and len(adapters) == 1
    assert all(b.gateway.probe_sandbox.calls == 0 for b in branches)
    assert "SECRET_SDK_ERROR_SENTINEL" not in canonical_json(result)


def test_unknown_terminal_reopen_is_read_only_even_with_unresolved_provider(factory):
    branch = factory()
    branch.journal.append("provider_call_started", {
        "call_id": "unknown", "turn_id": "unknown", "input_tokens": 1, "output_ceiling": 25000,
    })
    terminal = branch.finish("PROVIDER_TIMEOUT_OR_UNKNOWN")
    before = branch.journal.path.read_bytes()
    restored = reopen(branch)
    assert prepare(restored) is None and restored.terminal == terminal
    assert branch.journal.path.read_bytes() == before


def test_f_caps_round_robin_and_full_output_reserve_do_not_transfer(factory):
    branches = [factory(label) for label in rollout.ORDER]
    order = []

    class Costly(Adapter):
        def count_input_tokens_v2(self, request, **kwargs):
            assert request["max_output_tokens"] == 25000
            self.count = 200000
            return super().count_input_tokens_v2(request, **kwargs)

        def execute_request(self, *args, **kwargs):
            return replace(super().execute_request(*args, **kwargs), output_tokens=25000)

    def adapter(config):
        ordinal = len(order)
        label = rollout.ORDER[ordinal % 2]
        order.append(label)
        call = (probe_call(label) if ordinal < 2 else
                action("stop_task", label + "-stop", summary="Synthetic stop."))
        return Costly([call]) if label == "F1" else Adapter([call])

    result = rollout.drive(SimpleNamespace(package=SimpleNamespace(
        public=branches[0].gateway.public_task)), branches, adapter)
    assert order == ["F1", "F2", "F1", "F2"]
    assert result["branches"][0]["terminal"] == "COST_CAP_REACHED"
    assert result["branches"][1]["terminal"] == "AGENT_STOPPED"
    assert result["new_provider_calls"] == 3 and result["new_input_count_calls"] == 4
    assert result["recorded_cost_nanos"] < 1000000000
    assert all(b["cost_nanos"] <= 500000000 for b in result["branches"])


def test_report_cannot_spend_a_ninth_new_call(factory):
    branch, adapters = factory(), []

    def adapter(config):
        value = Adapter([probe_call("p" + str(len(adapters)))])
        adapters.append(value)
        return value

    result = rollout.drive(SimpleNamespace(package=SimpleNamespace(
        public=branch.gateway.public_task)), [branch], adapter)
    assert result["new_provider_calls"] == result["new_tool_actions"] == 8
    assert result["branches"][0]["terminal"] == "LIMIT_REACHED"
    assert adapters[-1].sequence == []


class CaseProbe(FakeProbe):
    def __init__(self, report, *, outcome="FAIL", failure=None):
        super().__init__(status="passed")
        self.report, self.outcome, self.failure = report, outcome, failure

    def run_probe(self, *args, **kwargs):
        result = super().run_probe(*args, **kwargs)
        data = {**self.report["environment"], "rows": [{
            "id": rollout.design.CASE_ID, "real": self.report["expected"],
            "fake": self.report["expected"] if self.outcome == "PASS" else self.report["actual"],
            "matches": self.outcome == "PASS"}]}
        result["stdout"] = json.dumps(data)
        if self.failure == "cleanup":
            result["cleanup_failed"] = True
        elif self.failure == "malformed":
            result["stdout"] = "NOT_JSON"
        elif self.failure == "deadline":
            result["deadline_exhausted"] = True
        return result


def mock_plan(branch):
    identity = branch.gateway.probe_sandbox.preflight()
    return SimpleNamespace(
        package=SimpleNamespace(public=branch.gateway.public_task), report=branch.report(),
        checkpoint={"source_root": str(branch.journal.root / "unused-source")},
        envelope={"probe_image_digest": identity["image_digest"],
                  "probe_profile_hash": identity["profile_hash"]},
        verification_source="# SAME PUBLIC CASE; MOCK EXECUTION ONLY\n",
    )


@pytest.mark.parametrize("outcome", ["PASS", "FAIL"])
def test_operator_audit_is_separate_cached_and_never_agent_credit(factory, tmp_path, outcome):
    branches = [factory(label, checked=True) for label in rollout.ORDER]
    for branch in branches:
        dispatch(branch, [action("finish_task", "finish")])
    plan = mock_plan(branches[0])
    probe, store = CaseProbe(plan.report, outcome=outcome), ArtifactStore(tmp_path / "audit")
    observer = DevJournal(store.root, "run_dev_mock_audit")
    before = [b.journal.path.read_bytes() for b in branches]
    rows = rollout.operator_audits(plan, branches, probe, observer, store,
                                   ExecutionDeadline.from_remaining(10))
    assert probe.calls == 1 and [r["reused"] for r in rows] == [False, True]
    assert all(r["case_outcome"] == outcome and not r["agent_credit"] for r in rows)
    assert before == [b.journal.path.read_bytes() for b in branches]
    assert all(b.new_provider_calls == b.new_tools == 1 for b in branches)


@pytest.mark.parametrize("failure", ["cleanup", "malformed", "deadline"])
def test_operator_audit_error_keeps_evidence_and_stops(failure, factory, tmp_path):
    branch = factory(checked=True)
    dispatch(branch, [action("finish_task", "finish")])
    plan = mock_plan(branch)
    store = ArtifactStore(tmp_path / "audit")
    observer = DevJournal(store.root, "run_dev_mock_audit")
    probe = CaseProbe(plan.report, failure=failure)
    with pytest.raises((rollout.native.engine.AbortExperiment, ExecutionDeadlineExceeded,
                        ContractError)):
        rollout.operator_audits(plan, [branch, branch], probe, observer, store,
                                ExecutionDeadline.from_remaining(10))
    finished = [e for e in observer.events() if e["event_type"] == "operator_case_finished"]
    assert len(finished) == probe.calls == 1
    assert finished[0]["payload"]["case_outcome"] == "ERROR"
    assert store.read_bytes(Artifact.model_validate(finished[0]["payload"]["result_artifact"]))


def test_one_shot_mock_no_keys_docker_or_resume(factory, tmp_path, monkeypatch):
    root = tmp_path / "packet"
    root.mkdir()
    (root / "plan.json").write_bytes(b"{}")
    branches = {label: factory(label, checked=True) for label in rollout.ORDER}
    plan = mock_plan(branches["F1"])
    monkeypatch.setattr(rollout, "validate", lambda _: (plan, {}))
    monkeypatch.setattr(rollout, "initialize_branch", lambda p, label, *args: branches[label])

    def forbidden(*args, **kwargs):
        pytest.fail("mock run touched credentials or live preflight")

    monkeypatch.setattr(rollout, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_source_preflight", forbidden)
    monkeypatch.setattr(rollout.native.loop, "_live_sandbox_preflight", forbidden)
    args = dict(approval_packet_hash=sha256_bytes(b"{}"), cap=rollout.TOTAL_CAP,
                credential_file=rollout.repository_root() / ".env",
                pricing_verified_on=utc_now().date().isoformat(), sandbox=Checks(),
                probe=CaseProbe(plan.report), adapter_factory=lambda _: Adapter([
                    action("finish_task", "finish")]))
    result_root = tmp_path / "result"
    result = rollout.run(root, result_root, **args)
    assert result["terminal"] == "ROLLOUTS_COMPLETED" and result["provider_free"]
    assert result["new_provider_calls"] == result["new_tool_actions"] == 2
    assert result["recorded_cost_nanos"] == 2400000
    assert len(result["operator_case_audits"]) == 2 and args["probe"].calls == 1
    assert result["task_acceptance"] == "NOT_RUN" and not result["official"]
    assert not rollout.read(result_root / "envelope.json")["paid_execution_authorized"]
    before = {p: p.read_bytes() for p in result_root.rglob("*") if p.is_file()}
    with pytest.raises(ContractError, match="fresh disjoint"):
        rollout.run(root, result_root, **args)
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize("bad", ["packet", "cap", "credential", "date"])
def test_approval_contract_before_key_provider_or_result_root(tmp_path, monkeypatch, bad):
    root = tmp_path / "packet"
    root.mkdir()
    (root / "plan.json").write_bytes(b"{}")
    monkeypatch.setattr(rollout, "validate", lambda _: (SimpleNamespace(), {}))
    args = dict(approval_packet_hash=sha256_bytes(b"{}"), cap=rollout.TOTAL_CAP,
                credential_file=rollout.repository_root() / ".env",
                pricing_verified_on=utc_now().date().isoformat())
    key, value = {"packet": ("approval_packet_hash", "bad"), "cap": ("cap", Decimal("2")),
                  "credential": ("credential_file", tmp_path / ".env"),
                  "date": ("pricing_verified_on", "2000-01-01")}[bad]
    args[key] = value
    with pytest.raises(ContractError):
        rollout.run(root, tmp_path / "result", **args,
                    adapter_factory=lambda _: pytest.fail("provider admission"))
    assert not (tmp_path / "result").exists()


def test_real_packet_and_checkpoint_restore_with_no_provider_or_candidate_execution(tmp_path):
    if not rollout.DESIGN.exists():
        pytest.skip("external evidence unavailable")
    saved = json.loads((rollout.DESIGN / "packet.json").read_bytes())
    if saved["runtime_hash"] != rollout.design.runtime_content_hash():
        with pytest.raises(ValueError, match="source runtime/config mismatch"):
            rollout.load_plan()
        return
    plan = rollout.load_plan()
    envelope = rollout.prepare(tmp_path / "executable")
    assert rollout.validate(tmp_path / "executable")[1] == envelope
    sandbox, probe = Checks(), FakeProbe()
    branch = rollout.initialize_branch(plan, "F1", tmp_path / "branches", sandbox, probe,
                                       ExecutionDeadline.from_remaining(90))
    request = prepare(branch)[1]
    assert rollout.design.wire(request) == (rollout.DESIGN / "feedback-request.json").read_bytes()
    assert branch.counters.model_calls == 21 and branch.counters.tool_actions == 22
    assert branch.gateway.accepted_mutations == branch.inherited_accepted_mutations == 2
    assert branch.new_provider_calls == branch.new_tools == 0
    state = reconstruct_state(request["input"])
    assert state["working_notes"] == plan.state["working_notes"]
    assert state["visible_check_status"] == plan.state["visible_check_status"]
    assert len([i for i in request["input"] if i.get("type") == "reasoning"]) == 21
    assert sandbox.calls == [] and probe.calls == 0
