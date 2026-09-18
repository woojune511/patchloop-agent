"""Bounded fixed-candidate discovery: simulated provider, public tools and read-only audit."""
from __future__ import annotations

import copy
import json
import socket
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_counterexample_discovery import inputs as source_inputs

from diagnostics import counterexample_discovery as design
from diagnostics import counterexample_discovery_rollout as rollout
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ModelTurn,
    ModelTurnError,
    RequestedTool,
)
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.probes import probe_execution_policy, probe_profile
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SECRET = "SECRET_PROVIDER_BODY_REASONING_KEY_SENTINEL"
inputs = source_inputs


def action(name, action_id, **arguments):
    if name in rollout.TOOL_NAMES:
        arguments["turn_decision"] = {
            "mode": "verify" if name == "run_probe" else "inspect", "basis": "Public review.",
            "evidence_goal": None if name == "run_probe" else "Read current public code.",
            "memory_update": None, "plan_update": None,
        }
    return RequestedTool(name=name, action_id=action_id, arguments=arguments)


def read_call(action_id="read"):
    return action("read_file", action_id, path="toy.py", start_line=1, end_line=10)


def probe_call(action_id="probe"):
    return action("run_probe", action_id, question="Does the public behavior hold?",
                  python_source="import toy\nprint(toy.value())\n")


def report_call(outcome="counterexample_reported", **changes):
    data = {"outcome": outcome, "requirement_excerpt": "value() returns zero.",
            "justification": "Compare the recorded observation with the public requirement.",
            "probe_action_id": "probe", "expected": "0", "observed": "1",
            "limitations": "Mock execution cannot establish real task behavior."}
    data.update(changes)
    return action("report_discovery", "report", **data)


class MockProbe:
    def __init__(self, dependencies):
        self.profile = probe_profile(dependencies.identity)
        self.calls = 0
        self.change = {}

    def preflight(self, **kwargs):
        return {"image_digest": self.profile["image_digest"],
                "profile_hash": sha256_json(self.profile)}

    def run_probe(self, workspace, question, python_source, **kwargs):
        self.calls += 1
        assert "return 1" in (workspace / "toy.py").read_text()
        policy = probe_execution_policy(effective_timeout_seconds=30, row_deadline_limited=False,
                                         cleanup_status="confirmed", profile=self.profile)
        return {"status": "passed", "source_hash": sha256_bytes(python_source.encode()),
                "snapshot_hash": sha256_json({"mock": True}), **self.preflight(),
                "exit_code": 0, "stdout": "MOCK_OBSERVATION: value=1\n", "stderr": "",
                "timed_out": False, "truncated": False, "cleanup_failed": False,
                "deadline_exhausted": False, "execution_policy": policy,
                "execution_policy_hash": sha256_json(policy), **self.change}


class Adapter:
    def __init__(self, config, batches, *, count=1000, fault=None):
        self.config, self.batches, self.count, self.fault = config, batches, count, fault
        self.requests, self.counts = [], []
        self.client = SimpleNamespace(max_retries=0, close=self.close)
        self.closed = 0

    def close(self, **kwargs):
        self.closed += 1
        if self.fault == "client_cleanup":
            raise OSError(SECRET)

    def count_input_tokens_v2(self, request, **kwargs):
        self.counts.append(copy.deepcopy(request))
        if self.fault == "count":
            raise TimeoutError(SECRET)
        return self.count

    def execute_request(self, request, *, requested_input_tokens, **kwargs):
        self.requests.append(copy.deepcopy(request))
        if self.fault == "provider":
            raise TimeoutError(SECRET)
        calls = self.batches[len(self.requests) - 1]
        suffix = str(len(self.requests))
        raw = ModelTurn(
            tool_calls=calls, requested_input_tokens=requested_input_tokens,
            input_tokens=requested_input_tokens, cached_input_tokens=100,
            output_tokens=150, reasoning_output_tokens=100,
            response_id="response-" + suffix, response_model=design.MODEL,
            response_status="completed", output_item_count=1 + len(calls),
            output_item_types=("reasoning", *("function_call" for _ in calls)),
            provider_continuation=(EncryptedReasoningContinuationItem("reason-" + suffix,
                                                                        "cipher-" + suffix),
                                   *(FunctionCallContinuationRef(c.action_id) for c in calls)),
        )
        if self.fault == "billing":
            raw = replace(raw, input_tokens=requested_input_tokens + 1)
        elif self.fault == "model":
            raw = replace(raw, response_model="wrong-model")
        elif self.fault == "continuation":
            raw = replace(raw, provider_continuation=())
        elif self.fault == "incomplete":
            raw = replace(raw, tool_calls=[], response_status="incomplete",
                          response_incomplete_reason="max_output_tokens",
                          error=ModelTurnError("incomplete_response", "max_output_tokens"),
                          provider_continuation=raw.provider_continuation[:1])
        return raw


@pytest.fixture
def frozen(inputs, tmp_path, monkeypatch):  # noqa: F811 - shared pytest fixture
    monkeypatch.setattr(design, "EXPECTED_HASHES", {
        name: sha256_bytes(path.read_bytes()) for name, path in inputs.paths().items()
    })

    def forbidden(*args, **kwargs):
        pytest.fail("network, credential or real Docker access during mock verification")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(rollout, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout, "DockerProbeSandbox", forbidden)
    parent = tmp_path / "design"
    design.prepare(inputs, parent)
    plan_root, result_root = tmp_path / "executable", tmp_path / "result"
    plan = rollout.prepare(parent, plan_root, result_root, utc_now().date().isoformat())
    return SimpleNamespace(inputs=inputs, design=parent, root=plan_root, plan=plan,
                           result=result_root, plan_hash=sha256_bytes(
                               (plan_root / "plan.json").read_bytes()))


def run_mock(frozen, batches, *, fault=None, count=1000, probe_change=None,
             checkpoint=lambda _: None):
    adapter = Adapter(rollout.configuration(), batches, fault=fault, count=count)
    probes = []

    def probe_factory(dependencies):
        probe = MockProbe(dependencies)
        probe.change = probe_change or {}
        probes.append(probe)
        return probe

    result = rollout.run(frozen.root, plan_hash=frozen.plan_hash, adapter_factory=lambda _: adapter,
                         probe_factory=probe_factory, checkpoint=checkpoint)
    return result, adapter, probes


def test_real_request_and_public_native_feedback_reach_report_without_a_verdict(frozen):
    result, adapter, probes = run_mock(frozen, [[read_call()], [probe_call()], [report_call()]])
    assert result["terminal"] == "REPORT_RECORDED"
    assert result["review_status"] == "PUBLIC_REVIEW_REQUIRED"
    assert result["discovery_outcome"] is None
    assert result["live_provider_calls"] == 0 and result["accounting_basis"] == "mock_simulation"
    assert result["model_calls"] == result["input_count_calls"] == result["tool_actions"] == 3
    assert adapter.closed == 1 and probes[0].calls == 1
    assert adapter.requests == adapter.counts
    initial = json.loads((frozen.design / "request.json").read_bytes())
    assert adapter.requests[0] == initial
    for before, after in zip(adapter.requests[:-1], adapter.requests[1:], strict=True):
        assert after["input"][:len(before["input"])] == before["input"]
        assert {k: v for k, v in after.items() if k != "input"} == {
            k: v for k, v in initial.items() if k != "input"}
    assert "return 1" in canonical_json(adapter.requests[1])
    assert "MOCK_OBSERVATION: value=1" in canonical_json(adapter.requests[2])
    reasoning = [x for x in adapter.requests[2]["input"] if x.get("type") == "reasoning"]
    assert [x["encrypted_content"] for x in reasoning] == ["cipher-1", "cipher-2"]
    assert all(x["summary"] == [] for x in reasoning)
    evidence = result["report"]["evidence"]
    assert evidence["probe_identity_bound"] and evidence["complete_probe_receipt"]
    assert evidence["semantic_verdict"] is None
    assert "import toy" in evidence["program"]
    assert rollout.inspect(frozen.result) == result
    with pytest.raises(ContractError, match="fresh external"):
        run_mock(frozen, [[report_call()]])


@pytest.mark.parametrize("outcome", ["no_counterexample_found", "blocked"])
def test_no_probe_or_positive_claim_required_for_reporting(frozen, outcome):
    result, adapter, probes = run_mock(frozen, [[report_call(
        outcome, probe_action_id=None, requirement_excerpt=None, expected=None, observed=None)]])
    assert result["terminal"] == "REPORT_RECORDED"
    assert not result["report"]["evidence"]["probe_identity_bound"]
    assert result["report"]["evidence"]["semantic_verdict"] is None
    assert probes[0].calls == 0 and len(adapter.requests) == 1


@pytest.mark.parametrize("fault,expected,counts,calls", [
    ("count", "COUNT_TIMEOUT_OR_UNKNOWN", 1, 0),
    ("provider", "PROVIDER_TIMEOUT_OR_UNKNOWN", 1, 1),
    ("billing", "PROVIDER_TIMEOUT_OR_UNKNOWN", 1, 1),
    ("model", "PROVIDER_TIMEOUT_OR_UNKNOWN", 1, 1),
    ("continuation", "PROVIDER_CONTINUATION_ERROR", 1, 1),
    ("incomplete", "INCOMPLETE_RESPONSE", 1, 1),
    ("client_cleanup", "CLIENT_CLEANUP_UNCONFIRMED", 1, 1),
])
def test_uncertainty_incomplete_and_cleanup_stop_without_another_request(
    frozen, fault, expected, counts, calls,
):
    result, adapter, probes = run_mock(frozen, [[report_call()]], fault=fault)
    assert result["terminal"] == expected
    assert result["input_count_calls"] == counts and result["model_calls"] == calls
    assert len(adapter.requests) == calls and adapter.closed == 1 and probes[0].calls == 0
    assert rollout.inspect(frozen.result) == result
    for path in frozen.result.rglob("*.json*"):
        assert SECRET.encode() not in path.read_bytes()


@pytest.mark.parametrize("count,expected", [(0, "COUNT_TIMEOUT_OR_UNKNOWN"),
                                            (True, "COUNT_TIMEOUT_OR_UNKNOWN"),
                                            (60001, "INPUT_LIMIT_EXCEEDED")])
def test_count_limits_prevent_dispatch(frozen, count, expected):
    result, adapter, _ = run_mock(frozen, [[report_call()]], count=count)
    assert result["terminal"] == expected and not adapter.requests


def test_full_25000_output_reservation_never_shrinks():
    ledger = rollout.DiscoveryLedger(Decimal("0.37"), rollout.pricing_for_model(design.MODEL))
    assert ledger.admit(1, desired_output_ceiling=25000, minimum_output_ceiling=25000) is None
    ledger = rollout.DiscoveryLedger(Decimal("1.20"), rollout.pricing_for_model(design.MODEL))
    assert ledger.admit(60000, desired_output_ceiling=25000,
                        minimum_output_ceiling=25000).output_ceiling == 25000


@pytest.mark.parametrize("batch", [
    [action("replace_text", "mutation", path="toy.py")],
    [read_call(), probe_call()], [report_call(), read_call()],
    [read_call(), read_call()], [report_call(outcome="invented")], [],
])
def test_invalid_or_mutating_batch_never_executes(frozen, batch):
    result, adapter, probes = run_mock(frozen, [batch])
    assert result["terminal"] == "PROTOCOL_VIOLATION"
    assert result["tool_actions"] == 0 and len(adapter.requests) == 1 and probes[0].calls == 0


@pytest.mark.parametrize("change,expected", [
    ({"cleanup_failed": True}, "SANDBOX_CLEANUP_UNCONFIRMED"),
    ({"deadline_exhausted": True}, "LIMIT_REACHED"),
    ({"source_hash": "sha256:" + "0" * 64}, "TOOL_EXECUTION_UNCERTAIN"),
    ({"profile_hash": "sha256:" + "0" * 64}, "TOOL_EXECUTION_UNCERTAIN"),
])
def test_probe_uncertainty_stops_before_next_model_turn(frozen, change, expected):
    result, adapter, probes = run_mock(frozen, [[probe_call()], [report_call()]],
                                       probe_change=change)
    assert result["terminal"] == expected and len(adapter.requests) == probes[0].calls == 1


@pytest.mark.parametrize("change", [
    {"status": "failed", "exit_code": 1, "stderr": "ImportError: mock fixture"},
    {"status": "output_limit", "truncated": True},
    {"status": "timeout", "timed_out": True},
])
def test_probe_failure_or_unbound_output_cannot_create_a_semantic_success(frozen, change):
    result, adapter, _ = run_mock(frozen, [[probe_call()], [report_call()]], probe_change=change)
    assert result["terminal"] == "REPORT_RECORDED" and len(adapter.requests) == 2
    evidence = result["report"]["evidence"]
    assert evidence["semantic_verdict"] is None and result["discovery_outcome"] is None
    if "stderr" not in change:
        assert not evidence["complete_probe_receipt"]


@pytest.mark.parametrize("stage", ["dispatch_recorded", "provider_returned", "decision_recorded",
                                   "actions_finished", "batch_finished", "report_recorded"])
def test_fault_evidence_is_inspected_without_retry_or_resume(frozen, stage):
    def interrupted(name):
        if name == stage:
            raise KeyboardInterrupt()

    result, adapter, probes = run_mock(frozen, [[probe_call()], [report_call()]],
                                       checkpoint=interrupted)
    before = {str(p): sha256_bytes(p.read_bytes()) for p in frozen.result.rglob("*") if p.is_file()}
    assert rollout.inspect(frozen.result) == rollout.inspect(frozen.result) == result
    after = {str(p): sha256_bytes(p.read_bytes()) for p in frozen.result.rglob("*") if p.is_file()}
    assert before == after and adapter.closed == 1
    assert probes[0].calls <= 1
    if stage == "dispatch_recorded":
        assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN" and len(adapter.requests) == 0


def test_frozen_request_tamper_rejected_before_result_creation(frozen):
    with (frozen.root / "request.json").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ContractError, match="request bytes changed"):
        run_mock(frozen, [[report_call()]])
    assert not frozen.result.exists()


def test_missing_source_fails_before_count_with_no_fallback(frozen, monkeypatch):
    def missing(*args, **kwargs):
        raise ContractError("source unavailable")

    monkeypatch.setattr(design, "load_source", missing)
    with pytest.raises(ContractError, match="unavailable"):
        run_mock(frozen, [[report_call()]])
    assert not frozen.result.exists()


def test_inspect_detects_tampered_model_input_artifact(frozen):
    run_mock(frozen, [[report_call()]])
    journal = DevJournal(frozen.result, rollout.RUN_ID)
    turn = next(e["payload"] for e in journal.events() if e["event_type"] == "turn_started")
    Path(turn["model_input_artifact"]["path"]).write_bytes(b"changed")
    with pytest.raises(RecoveryError, match="integrity"):
        rollout.inspect(frozen.result)


def test_gateway_replay_does_not_repeat_probe_after_completed_action(frozen):
    _, _, probes = run_mock(frozen, [[probe_call()], [report_call()]])
    journal = DevJournal(frozen.result, rollout.RUN_ID)
    original = next(e["payload"]["result"] for e in journal.events()
                    if e["event_type"] == "action_finished")
    workspace = frozen.result / "workspaces/candidate/repo"
    gateway = DevToolGateway(
        workspace=workspace, public_task=design.load_public_task(frozen.design / "public.yaml"),
        sandbox=None, probe_sandbox=probes[0], journal=journal, limits=DevLimits(),
        deadline=ExecutionDeadline.from_remaining(5))
    replay = gateway.execute(rollout.loop._requested_tool_from_openai(probe_call()))
    assert replay.replayed and probes[0].calls == 1
    assert replay.model_dump(exclude={"replayed"}) == {
        k: v for k, v in original.items() if k != "replayed"}
    assert WorkspaceManager.diff_summary(workspace).patch_hash == design.EXPECTED_HASHES[
        "candidate_patch"]


def test_missing_executable_journal_rejected_before_result_creation(frozen):
    (frozen.root / "runs/run_dev_discovery_executable.jsonl").unlink()
    with pytest.raises(ContractError, match="preparation journal missing"):
        run_mock(frozen, [[report_call()]])
    assert not frozen.result.exists()


@pytest.mark.parametrize("change", ["plan", "provider_free"])
def test_inspect_binds_execution_identity_to_sealed_journal(frozen, change):
    run_mock(frozen, [[report_call()]])
    execution_path = frozen.result / "execution.json"
    execution = rollout.read(execution_path)
    if change == "plan":
        execution["plan"]["repeat"] = 2
    else:
        execution["provider_free"] = False
    execution_path.write_bytes(design.wire(execution))
    with pytest.raises(ContractError, match="identity"):
        rollout.inspect(frozen.result)


@pytest.mark.parametrize("limit,expected", [("max_model_calls", "MODEL_CALL_LIMIT"),
                                           ("max_tool_actions", "TOOL_ACTION_LIMIT")])
def test_loop_limits_stop_before_an_extra_count_or_call(frozen, monkeypatch, limit, expected):
    monkeypatch.setattr(rollout, "DevLimits", lambda: DevLimits(**{limit: 1}))
    result, adapter, _ = run_mock(frozen, [[read_call()], [report_call()]])
    assert result["terminal"] == expected
    assert len(adapter.counts) == len(adapter.requests) == result["tool_actions"] == 1


def test_late_response_preserves_usage_without_executing_a_probe(frozen):
    now = [0.0]
    adapter = Adapter(rollout.configuration(), [[probe_call()]])
    execute = adapter.execute_request

    def late(request, **kwargs):
        result = execute(request, **kwargs)
        now[0] = 1801.0
        return result

    adapter.execute_request = late
    probes = []

    def probe_factory(dependencies):
        probes.append(MockProbe(dependencies))
        return probes[-1]

    result = rollout.run(frozen.root, plan_hash=frozen.plan_hash,
                         adapter_factory=lambda _: adapter, probe_factory=probe_factory,
                         clock=lambda: now[0])
    assert result["terminal"] == "LIMIT_REACHED"
    assert result["recorded_cost_nanos"] > 0 and result["provider_cost_known"]
    assert result["tool_actions"] == probes[0].calls == 0 and len(adapter.requests) == 1
    assert rollout.inspect(frozen.result) == result


def test_stale_pricing_and_wrong_plan_hash_fail_before_consuming_the_sample(frozen, monkeypatch):
    with pytest.raises(ContractError, match="exact executable plan hash"):
        rollout.run(frozen.root, plan_hash="sha256:" + "0" * 64)
    tomorrow = utc_now() + timedelta(days=1)
    monkeypatch.setattr(rollout, "utc_now", lambda: tomorrow)
    with pytest.raises(ContractError, match="price review date expired"):
        run_mock(frozen, [[report_call()]])
    assert not frozen.result.exists()


def test_unpublished_interrupted_evidence_is_read_only_and_never_resumed(frozen):
    run_mock(frozen, [[report_call()]])
    journal_path = frozen.result / "runs" / f"{rollout.RUN_ID}.jsonl"
    lines = journal_path.read_bytes().splitlines(keepends=True)
    assert json.loads(lines[-1])["event_type"] == "diagnostic_execution_finished"
    journal_path.write_bytes(b"".join(lines[:-1]))
    (frozen.result / "result.json").unlink()
    before = {str(p): sha256_bytes(p.read_bytes()) for p in frozen.result.rglob("*") if p.is_file()}
    result = rollout.inspect(frozen.result)
    assert result["terminal"] == "INTERRUPTED" and result["report"] is not None
    assert result["resume_allowed"] is False
    assert before == {
        str(p): sha256_bytes(p.read_bytes()) for p in frozen.result.rglob("*") if p.is_file()}
