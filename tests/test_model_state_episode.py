from __future__ import annotations

import copy
import json
import socket
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_dev_tools import mutation_call, read_calls
from test_fresh_state_rollout import Adapter
from test_model_state_sampler import factorial as _factorial
from test_model_state_sampler import snapshot

from diagnostics import decision_sampler as shared
from diagnostics import fresh_state_rollout as engine
from diagnostics import model_state_episode as episode
from diagnostics import model_state_inspection_audit as audit
from diagnostics import model_state_review as review
from diagnostics import model_state_sampler as design
from patchloop.agent.model import EncryptedReasoningContinuationItem, ModelTurnError
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import runner as loop
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError
from patchloop.sandbox import LocalSandbox, SandboxResult
from patchloop.util import canonical_json, sha256_json

factorial = _factorial


@pytest.fixture
def episodes(gateway_factory, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("network/credential used by provider-free diagnostic")

    monkeypatch.setattr(shared, "create_openai_client", forbidden)
    monkeypatch.setattr(shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    result = []
    for arm in "ACBD":
        gateway, journal, _ = gateway_factory()
        active = engine.ActiveClock(lambda: 0)
        gateway.deadline = ExecutionDeadline.from_remaining(1800, clock=active)
        branch = episode.Episode(
            arm, journal, ArtifactStore(journal.root / "artifacts"), gateway,
            loop._RunCounters(), active, 0, arm=arm,
        )
        package = SimpleNamespace(public=gateway.public_task)
        context = json.loads(loop._build_context(
            package=package, gateway=gateway, journal=journal, correction=None,
            latest_tool_results=[], counters=branch.counters, elapsed_seconds=0,
            limits=gateway.limits,
        ))
        policy = loop._tool_policy(gateway, branch.counters, gateway.limits)
        request = {**shared.SETTINGS, "reasoning": {"effort": "medium"},
                   "input": assemble_model_input(system_prompt=loop.DEV_SYSTEM_PROMPT,
                                                  state=context, history=[]),
                   "tools": dev_tool_schemas(finish_enabled=False, check_ids=policy.check_ids,
                                             allowed_tools=policy.allowed_tools)}
        requests, _ = design.factorial_requests(request)
        branch.seed_request = episode.episode_request(requests[arm])
        result.append(branch)
    return result


class MultiAdapter(Adapter):
    def __init__(self, arm, calls, *, tag="step", failure=None, incomplete=False, cipher=True):
        super().__init__(calls, failure=failure)
        self.model = design.PROFILES[arm].model_id
        self.tag, self.incomplete, self.cipher = tag, incomplete, cipher
        self.requests = []

    def request_payload(self, items, schemas, **kwargs):
        return {**shared.SETTINGS, **super().request_payload(items, schemas, **kwargs),
                "model": self.model}

    def execute_request(self, request, **kwargs):
        self.requests.append(copy.deepcopy(request))
        raw = super().execute_request(request, **kwargs)
        continuation = (
            EncryptedReasoningContinuationItem("r-" + self.tag, "cipher-" + self.tag),
            *raw.provider_continuation[1:],
        ) if self.cipher else ()
        raw = replace(raw, response_model=self.model, provider_continuation=continuation)
        if self.incomplete:
            raw = replace(raw, tool_calls=[], output_item_types=("reasoning",),
                          provider_continuation=continuation[:1], response_status="incomplete",
                          error=ModelTurnError(code="incomplete_response", message="output cap"),
                          response_incomplete_reason="max_output_tokens")
        return raw


def run_step(episodes, ledger, calls, **kwargs):
    adapters = {e.arm: MultiAdapter(e.arm, calls(e), **kwargs) for e in episodes}
    episode.run_round(episodes, SimpleNamespace(public=episodes[0].gateway.public_task),
                      adapters, ledger)
    return adapters


def call(name, label, **args):
    return RequestedTool(name=name, action_id=label, arguments=args,
                         turn_decision=PublicTurnDecision(
                             mode="verify" if name == "run_check" else "finish",
                             basis="Use the actual public result"))


def test_fresh_requests_then_parallel_results_reasoning_mutation_check_finish(episodes):
    ledger = shared.SharedCostLedger(Decimal("5"))
    seeds = {e.arm: copy.deepcopy(e.seed_request) for e in episodes}
    first = run_step(episodes, ledger, lambda _: read_calls(), tag="read")
    for e in episodes:
        assert first[e.arm].requests[0] == seeds[e.arm]
        assert e.new_tools == 2
    second = run_step(episodes, ledger, lambda e: [mutation_call(e.gateway)], tag="mutation")
    for e in episodes:
        request = second[e.arm].requests[0]
        assert request["input"][:3] == seeds[e.arm]["input"]
        assert sum(i.get("encrypted_content") == "cipher-read" for i in request["input"]) == 1
        output_ids = [i["call_id"] for i in request["input"]
                      if i.get("type") == "function_call_output"]
        assert output_ids == ["search-source", "read-source"]
        assert "def parse_rows" in canonical_json(request)
        assert e.gateway.accepted_mutations == 1
    checked = run_step(episodes, ledger, lambda _: [call(
        "run_check", "check", check_id="existing-unit-tests")], tag="check")
    for e in episodes:
        assert e.gateway.visible_check_status()[0]["status"] == "PASS"
        assert checked[e.arm].requests[0]["max_output_tokens"] == 25000
    run_step(episodes, ledger, lambda _: [call("finish_task", "finish")], tag="finish")
    for e in episodes:
        assert e.terminal["terminal"] == "PUBLIC_CHECKS_SUBMITTED"
        assert e.terminal["accepted_mutations_since_checkpoint"] == 1
        assert e.terminal["submitted_artifact"]["content_hash"] == e.gateway.current_diff_hash
        assert e.terminal["task_acceptance"] == e.terminal["hidden_evaluator"] == "NOT_RUN"
        assert e.terminal["censored"] is False
    assert ledger.spent_nanos == 4 * (2 * 1200000 + 2 * 4000000)


def test_observation_bound_is_censoring_not_action_mask_or_failure(episodes):
    ledger = shared.SharedCostLedger(Decimal("5"))
    for e in episodes:
        e.max_responses = 1
    run_step(episodes, ledger, lambda _: read_calls())
    adapters = run_step(episodes, ledger, lambda _: [])
    for e in episodes:
        assert adapters[e.arm].sequence == []
        assert e.terminal["terminal"] == "DIAGNOSTIC_STEP_LIMIT" and e.terminal["censored"]
        assert e.gateway.limits.max_model_calls == 40
        assert e.gateway.limits.max_tool_actions == 100


@pytest.mark.parametrize("failure", ["count", "create"])
def test_one_uncertain_arm_stops_every_other_arm_without_retry(episodes, failure):
    ledger = shared.SharedCostLedger(Decimal("5"))
    adapters = {e.arm: MultiAdapter(e.arm, read_calls(),
                                    failure=failure if e.arm == "C" else None) for e in episodes}
    package = SimpleNamespace(public=episodes[0].gateway.public_task)
    with pytest.raises(engine.AbortExperiment):
        episode.run_round(episodes, package, adapters, ledger)
    assert adapters["B"].sequence == adapters["D"].sequence == []
    assert episodes[0].new_tools == 2 and all(e.new_tools == 0 for e in episodes[1:])
    before = [e.new_provider_calls for e in episodes]
    episode.run_round(episodes, package, adapters, ledger)
    assert [e.new_provider_calls for e in episodes] == before
    assert all(e.terminal["total_cost_known"] is False for e in episodes)


def test_shared_cap_reserves_whole_active_depth_before_any_count(episodes):
    adapters = run_step(episodes, shared.SharedCostLedger(Decimal("2")), lambda _: read_calls())
    assert all(a.sequence == [] for a in adapters.values())
    assert all(e.terminal["terminal"] == "DIAGNOSTIC_COST_LIMIT" for e in episodes)


def test_reasoning_only_incomplete_continues_once_with_correction(episodes):
    ledger = shared.SharedCostLedger(Decimal("5"))
    run_step(episodes, ledger, lambda _: [], tag="incomplete", incomplete=True)
    adapters = run_step(episodes, ledger, lambda _: read_calls(), tag="read")
    for e in episodes:
        request = adapters[e.arm].requests[0]
        assert sum(i.get("encrypted_content") == "cipher-incomplete"
                   for i in request["input"]) == 1
        assert "max_output_tokens" in canonical_json(request)
        assert any(evt["event_type"] == "protocol_correction" for evt in e.journal.events())
        assert e.correction is None


def test_cipher_absent_stops_before_sampled_tools(episodes):
    with pytest.raises(engine.AbortExperiment):
        run_step(episodes, shared.SharedCostLedger(Decimal("5")), lambda _: read_calls(),
                 cipher=False)
    assert all(e.new_tools == 0 for e in episodes)


def test_model_mismatch_is_not_charged_at_the_requested_model_price_or_executed(episodes):
    adapters = {e.arm: MultiAdapter(e.arm, read_calls()) for e in episodes}
    original = adapters["C"].execute_request

    def wrong_model(*args, **kwargs):
        return replace(original(*args, **kwargs), response_model=design.MINI.model_id)

    adapters["C"].execute_request = wrong_model
    ledger = shared.SharedCostLedger(Decimal("5"))
    with pytest.raises(engine.AbortExperiment):
        episode.run_round(episodes, SimpleNamespace(public=episodes[0].gateway.public_task),
                          adapters, ledger)
    assert ledger.spent_nanos == 1200000  # Only A's durable, known usage is settled.
    assert episodes[1].new_tools == 0 and adapters["B"].sequence == []


class FailOnce:
    official = False

    def __init__(self, delegated):
        self.delegated, self.used = delegated, False

    def run_check(self, workspace, check, **kwargs):
        if not self.used:
            self.used = True
            return SandboxResult(command=["mock"], exit_code=1,
                                 stdout="PUBLIC_CHECK_FAILURE_SENTINEL", stderr="", duration_ms=1,
                                 timed_out=False, truncated=False, original_output_bytes=29)
        return self.delegated.run_check(workspace, check, **kwargs)


def test_public_failure_and_rejected_edit_are_feedback_not_forced_next_actions(episodes):
    ledger = shared.SharedCostLedger(Decimal("5"))
    run_step(episodes, ledger, lambda _: read_calls(), tag="read")
    run_step(episodes, ledger, lambda e: [mutation_call(e.gateway)], tag="mutation")
    for e in episodes:
        e.gateway.sandbox = FailOnce(e.gateway.sandbox)
    run_step(episodes, ledger, lambda _: [call("run_check", "first-check",
                                             check_id="existing-unit-tests")], tag="failure")
    reads = run_step(episodes, ledger, lambda _: [c.model_copy(update={
        "action_id": "after-failure-" + c.action_id}) for c in read_calls()], tag="recovery")
    for e in episodes:
        assert "PUBLIC_CHECK_FAILURE_SENTINEL" in canonical_json(reads[e.arm].requests[0])
        assert e.gateway.accepted_mutations == 1
    # Reusing the replaced old anchor is rejected and rolls back; feedback remains visible.
    run_step(episodes, ledger, lambda e: [mutation_call(e.gateway, action_id="rejected")],
             tag="bad")
    reads = run_step(episodes, ledger, lambda _: [c.model_copy(update={
        "action_id": "after-reject-" + c.action_id}) for c in read_calls()], tag="after-bad")
    for e in episodes:
        state = reconstruct_state(reads[e.arm].requests[0]["input"])
        assert state["last_failed_mutation"]
        assert e.gateway.accepted_mutations == 1


def test_prepare_only_reuses_every_frozen_cell_not_selected_responses(factorial, tmp_path):
    plan, _, _ = factorial
    before = snapshot(plan.source_root, plan.packet_path.parent)
    root = tmp_path / "episode-design"
    packet = episode.prepare(plan, root)
    assert packet["dispatch_enabled"] is False and packet["paid_execution_authorized"] is False
    assert packet["shared_cap_usd"] is None and packet["actual_tool_executions"] == 0
    assert len(packet["cells"]) == 16 and packet["max_generation_calls_proposal"] == 128
    assert packet["prior_sample_responses_reused"] == 0
    assert packet["schema_version"] == episode.PREPARATION_SCHEMA
    assert packet["input_contract_hash"] == episode.INPUT_CONTRACT_HASH
    for row, cell in zip(packet["cells"], plan.cells, strict=True):
        expected = episode.episode_request(json.loads(cell.request_json))
        assert row["source_request_hash"] == cell.request_hash
        assert row["request_hash"] == sha256_json(expected) != cell.request_hash
        assert review.read_json(ArtifactStore(root), row["request_artifact"]) == expected
    assert before == snapshot(plan.source_root, plan.packet_path.parent)
    for raw in snapshot(root).values():
        assert b"OLD_OPAQUE" not in raw and b"PRIVATE_SPEC_SENTINEL" not in raw
        assert b"FUTURE_RESULT_SENTINEL" not in raw
    with pytest.raises(ContractError):
        episode.prepare(plan, root)


def test_checkpoint_hydration_restores_counters_without_old_reasoning(factorial, tmp_path):
    plan, _, package = factorial
    cell = plan.cells[0]
    events, _ = design.source_events(plan.source_root)
    cutoff = plan.packet["cases"][cell.case_id]["cutoff_event_hash"]
    prefix = events[:next(i for i, e in enumerate(events) if e["event_hash"] == cutoff)]
    counters = loop._restore_counters(SimpleNamespace(events=lambda: prefix))
    # This shared sampler fixture uses illustrative, not journal-derived budgets.
    # Bind a synthetic episode cell to its actual counters for this hydration test.
    request = json.loads(cell.request_json)
    payload = json.loads(request["input"][1]["content"])
    payload["remaining_budget"].update(model_calls=40 - counters.model_calls,
                                       tool_actions=100 - counters.tool_actions,
                                       accepted_mutations=4, active_wall_time_seconds=1800)
    request["input"][1]["content"] = canonical_json(payload)
    cell = replace(cell, request_json=canonical_json(request), request_hash=sha256_json(request))
    plan = replace(plan, cells=(cell,))
    before = snapshot(plan.source_root)
    e = episode.initialize(plan, cell, tmp_path / "branch", tmp_path / "copy", package,
                           LocalSandbox())
    assert e.counters.model_calls == counters.model_calls
    assert e.counters.tool_actions == counters.tool_actions
    assert e.gateway.accepted_mutations == e.initial_mutations == 0
    _, first, _ = e.prepare_request(package, None)
    assert first == episode.episode_request(json.loads(cell.request_json))
    started = next(evt["payload"] for evt in e.journal.events()
                   if evt["event_type"] == "diagnostic_episode_started")
    assert started["source_request_hash"] == cell.request_hash
    assert started["first_request_hash"] == sha256_json(first) != cell.request_hash
    assert started["input_contract_hash"] == episode.INPUT_CONTRACT_HASH
    assert e.new_provider_calls == e.new_tools == 0
    assert before == snapshot(plan.source_root)
    assert not any(evt["event_type"] == "provider_call_started" for evt in e.journal.events())
    for data in snapshot(tmp_path / "branch").values():
        assert b"OLD_OPAQUE" not in data and b"FUTURE_RESULT_SENTINEL" not in data
    # A fresh diagnostic cannot become implicit resume.
    with pytest.raises(ContractError):
        episode.initialize(plan, cell, tmp_path / "branch", tmp_path / "copy2", package,
                           LocalSandbox())


def test_counter_mismatch_fails_before_creating_a_checkpoint(factorial, tmp_path, monkeypatch):
    plan, _, package = factorial

    def forbidden(*args, **kwargs):
        pytest.fail("checkpoint created before counter verification")

    monkeypatch.setattr(review, "gateway_at", forbidden)
    with pytest.raises(ContractError, match="counter mismatch"):
        episode.initialize(plan, plan.cells[0], tmp_path / "bad-branch", tmp_path / "copy",
                           package, LocalSandbox())
    assert not (tmp_path / "bad-branch").exists()


def test_inspection_audit_compares_exact_delivered_lines_not_query_novelty():
    span = {"path": "public.py", "file_hash": "hash-a", "start_line": 1,
            "end_line": 3, "content": "first\nsecond\nthird"}
    payload = {"source_bodies": [{"path": "public.py", "file_hash": "hash-a",
                                   "spans": [{**span, "end_line": 2,
                                              "content": "first\nsecond"}]}]}
    result = {"tool": "search_files", "status": "succeeded", "output": {"spans": [span]}}
    fact = audit.inspect_result(payload, result)
    assert (fact["already_delivered_lines"], fact["new_to_request_lines"]) == (2, 1)
    result["output"]["spans"] = payload["source_bodies"][0]["spans"]
    assert audit.inspect_result(payload, result)["outcome"] == "covered_only"
    result["output"]["spans"] = []
    assert audit.inspect_result(payload, result)["outcome"] == "zero_match"
    result["output"]["spans"] = [{**span, "content": "first\nchanged\nthird"}]
    with pytest.raises(ContractError, match="different bytes"):
        audit.inspect_result(payload, result)
