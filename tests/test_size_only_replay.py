from __future__ import annotations

import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from diagnostics import size_only_replay as replay
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import SEGMENT_RULES, reconstruct_state
from patchloop.dev.cost import ModelPricing
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("offline replay attempted network I/O")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture(scope="module")
def saved(tmp_path_factory):
    root = tmp_path_factory.mktemp("sizeonly")
    result = runner.run_dev(DevRunRequest(
        provider="mock", model="mock", state_root=root,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy="segmented-v1", planning_policy="brief-v1", repair_recheck=True))
    assert result["runs"][0]["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(root, result["runs"][0]["run_id"])
    events, store = journal.events(), ArtifactStore(root / "artifacts")
    turns = []
    for event in events:
        if event["event_type"] != "turn_started":
            continue
        turn = event["payload"]
        prefix = events[:event["sequence"] - 1]
        reader = SimpleNamespace(events=lambda prefix=prefix: prefix)
        state = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
        items = runner._load_active_model_input(turn, store, context_policy=segments.POLICY)
        latest = DevJournal.latest_tool_batch_results(reader)
        exchange = runner._build_latest_exchange(
            journal=reader, artifact_store=store, context=canonical_json(state),
            latest_tool_results=latest)[1:-1]
        turns.append(replay.SavedTurn(
            "mock", event["sequence"], prefix, turn, state,
            {"input": items, "tools": [], "model": "mock", "max_output_tokens": 25_000},
            {"input_tokens": 500, "output_tokens": 100, "cached_input_tokens": 0},
            latest, exchange,
            segments.load_binding(turn["context_segment"]["binding"], store)["base"],
            reconstruct_state(items, context_policy=segments.POLICY)["segment_handoff"]))
    return turns


class FixedEstimator:
    def __init__(self, overflow_native=False):
        self.overflow_native = overflow_native

    def estimate(self, turn, items):
        tokens = 500
        if self.overflow_native and any(i.get("type") == "function_call" for i in items):
            tokens = 60_001
        return {"lower": tokens, "central": tokens, "upper": tokens,
                "saved_exact_input": items == turn.wire["input"]}


def test_reconstructs_real_mock_boundaries_and_rejects_corrupt_projection(saved):
    replay.verify_baseline(saved)
    changed = copy.deepcopy(saved)
    changed[-1].state["current_diff"]["patch"] += "changed"
    with pytest.raises(ContractError, match="baseline input mismatch"):
        replay.verify_baseline(changed)


def test_no_result_rollover_preserves_prior_raw_results_and_current_authority(saved):
    inputs = []
    rows = replay.replay(saved, FixedEstimator(), "central",
                         save_input=lambda items: inputs.append(items))
    assert sum(r["fresh"] for r in rows) == 1
    assert sum(r["baseline_fresh"] for r in rows) > 1
    for turn, items in zip(saved, inputs, strict=True):
        state = reconstruct_state(items, context_policy=segments.POLICY)
        assert state["current_diff"] == turn.state["current_diff"]
        assert state["remaining_budget"] == turn.state["remaining_budget"]
        assert state["visible_check_status"] == turn.state["visible_check_status"]
    _, previous_outputs, _ = replay.inventory(inputs[-2])
    _, outputs, _ = replay.inventory(inputs[-1])
    assert set(previous_outputs) <= set(outputs)
    assert any(r["retention"]["added_tool_result_ids"] for r in rows)
    # The old handoff must not survive as a fresh plan-review signal.
    for items in inputs[1:]:
        state = reconstruct_state(items, context_policy=segments.POLICY)
        assert "context_handoff" not in state["working_plan"]["review_request"]["reasons"]


def test_size_rollover_still_keeps_latest_batch_and_two_reference_limit(saved):
    inputs = []
    rows = replay.replay(saved, FixedEstimator(overflow_native=True), "upper",
                         save_input=lambda items: inputs.append(items))
    assert all(r["status"] == "RECONSTRUCTED" for r in rows)
    assert any(r["attempts"] for r in rows)
    for turn, row, items in zip(saved, rows, inputs, strict=True):
        _, outputs, _ = replay.inventory(items)
        assert {r.action_id for r in turn.latest} <= set(outputs)
        assert row["limits"]["question_references"] <= 2
        assert row["limits"]["retained_source_chars"] <= 24_000
        assert not segments.size_reasons(row["sizes"])


def test_token_estimate_never_tokenizes_opaque_reasoning_or_claims_exactness():
    opaque = {"type": "reasoning", "encrypted_content": "opaque-secret"}
    first = {"role": "developer", "content": "public"}
    base = SimpleNamespace(row="A", sequence=1, wire={"input": [first], "tools": []},
                           usage={"input_tokens": 100})

    def encode(text):
        assert "opaque-secret" not in text
        return list(text)

    estimator = replay.TokenEstimator(encode, {sha256_bytes(b"opaque-secret"): 333}, [base])
    estimate = estimator.estimate(base, [first, opaque])
    assert estimate == {"lower": 305, "central": 433, "upper": 561,
                        "saved_exact_input": False}
    assert estimator.estimate(base, [first])["lower"] == 100
    with pytest.raises(ContractError, match="no saved usage attribution"):
        estimator.measure([{**opaque, "encrypted_content": "unattributed"}])


def test_cost_admission_stops_before_unaffordable_saved_output_without_spending():
    row = {"request_sequence": 1, "baseline_tokens": 1000,
           "selected_token_scenario": 1000, "baseline_cached_tokens": 0,
           "output_tokens_held_fixed": 3000, "status": "RECONSTRUCTED"}
    pricing = ModelPricing(Decimal("0.75"), Decimal("0.075"), Decimal("4.5"))
    result = replay.cost_projection([row, {**row, "request_sequence": 2}], pricing=pricing,
                                    row_cap=10_000_000, historical_debit=0, cache_mode="uncached")
    assert result["admitted_saved_outputs"] == 0
    assert result["conditional_prefix_cost_nanos"] == 0
    assert result["stopped_before_saved_output"]["reason"] == (
        "SAVED_OUTPUT_EXCEEDS_AFFORDABLE_CEILING")
    assert result["full_trace_estimate_nanos_ignoring_early_stop"] == 28_500_000


def test_cache_assumption_does_not_discount_admission():
    row = {"request_sequence": 1, "baseline_tokens": 20_000,
           "selected_token_scenario": 20_000, "baseline_cached_tokens": 20_000,
           "output_tokens_held_fixed": 128, "status": "RECONSTRUCTED"}
    pricing = ModelPricing(Decimal("0.75"), Decimal("0.075"), Decimal("4.5"))
    result = replay.cost_projection([row], pricing=pricing, row_cap=10_000_000,
                                    historical_debit=0, cache_mode="saved-cache-count")
    assert result["stopped_before_saved_output"]["reason"] == "COST_CAP"
    assert result["conditional_prefix_cost_nanos"] == 0


def test_raw_probe_delivery_requires_identity_program_and_entire_stdout():
    calls = [{"type": "function_call", "call_id": "p", "name": "run_probe",
              "arguments": canonical_json({"python_source": "print('x')"})},
             {"type": "function_call_output", "call_id": "p",
              "output": canonical_json({"output": {"stdout": "x\n"}})}]
    # Inventory needs no runnable prompt for this isolated public-archive test.
    items = [{}, {"content": "{}"}, {}, SEGMENT_RULES.archive(exchanges=calls)]
    probe = {"sequence": 1, "action_id": "p", "python_source": "print('x')", "stdout": "x\n"}
    assert replay.probe_delivery(items, [probe], 1) == []  # No future evidence.
    assert replay.probe_delivery(items, [probe], 2) == [
        {"action_id": "p", "program": True, "stdout": True}]
    assert replay.probe_delivery(items, [{**probe, "stdout": "x\ntrace"}], 2)[0]["stdout"] is False
    assert replay.probe_delivery(items, [{**probe, "action_id": "other"}], 2) == [
        {"action_id": "other", "program": False, "stdout": False}]


def test_catalog_includes_old_probe_reintroduced_by_question_reference():
    events = [{"event_type": "turn_decision_recorded", "payload": {"tool_calls": [
        {"action_id": "p", "arguments": {"python_source": "print('x')"}}]}},
        {"event_type": "action_finished", "sequence": 10, "payload": {"result": {
            "action_id": "p", "tool": "run_probe", "output": {
                "stdout": "x\n", "diff_hash": "old", "question": "original question"}}}}]
    probes = replay.probe_catalog([SimpleNamespace(prefix=events)], after_sequence=20)
    assert len(probes) == 1 and probes[0]["before_checkpoint"]
