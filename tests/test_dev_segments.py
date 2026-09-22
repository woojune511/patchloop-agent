from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from test_dev_conversation_v22 import (
    ModelTurn,
    ProviderCall,
    ProviderCallRef,
    ProviderReasoning,
    _provider_smoke,
)
from test_dev_planning import request as mock_request
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash

from patchloop.agent.model import ModelTurnError
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import (
    assemble_model_input,
    history_metadata,
    reconstruct_state,
    validate_model_input,
)
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, _SourceIndex, public_exchanges
from patchloop.dev.public_history import source_groups
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("segmented verification must not dispatch real network requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def configured(monkeypatch, tmp_path, *, planning="none", incomplete_at=(), oversized_at=(),
               with_notes=False, boundary_policy=segments.DEFAULT_BOUNDARY_POLICY, script=None):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)
    request = request.model_copy(update={"context_policy": segments.POLICY,
                                         "planning_policy": planning,
                                         "segment_boundary_policy": boundary_policy})
    implementation = runner.OpenAIResponsesAdapter
    script = script or MockDevAdapter("csv-quoted-newline")
    delivered = []

    def execute(self, payload, *, requested_input_tokens, timeout_seconds):
        number = len(inputs)
        inputs.append(copy.deepcopy(payload["input"]))
        state = reconstruct_state(payload["input"], context_policy=segments.POLICY)
        delivered.append(copy.deepcopy(state))
        cipher = ("x" * 1_717_452 if number in oversized_at else f"cipher-{number}")
        if number in incomplete_at:
            return ModelTurn(
                tool_calls=[], input_tokens=requested_input_tokens, output_tokens=25_000,
                error=ModelTurnError("incomplete_response", "max_output_tokens"),
                response_incomplete_reason="max_output_tokens",
                output_item_types=("reasoning",),
                provider_continuation=(ProviderReasoning(f"r-{number}", cipher),),
            )
        # Deterministic fixture reads only source actually delivered in this input.
        index = _SourceIndex(payload["input"], archive_kind=PUBLIC_EVIDENCE_KIND)
        groups = source_groups({(*key, line): value[0] for key, rows in index.observed.items()
                                for line, value in rows.items()})
        state["source_spans"] = [{"path": g["path"], "file_hash": g["file_hash"], **s}
                                 for g in groups for s in g["inline_spans"]]
        turn = script.next_turn(canonical_json(state), payload["tools"])
        if with_notes and number == 1:
            turn.tool_calls[0].turn_decision.memory_update = {
                "findings": [{"note_id": None, "statement": statement, "evidence": [{
                    "kind": "source", "path": script.mutation.path,
                    "start_line": line, "end_line": line,
                }]} for line, statement in [(1, "The module imports csv."),
                                            (8, "The loop splits physical lines.")]],
                "open_question": "Does the new parser preserve quoted newlines?",
            }
        calls = [ProviderCall(c.name, c.action_id, runner._provider_tool_arguments(c))
                 for c in turn.tool_calls]
        return ModelTurn(
            tool_calls=calls, input_tokens=requested_input_tokens, output_tokens=100,
            output_item_types=("reasoning", "function_call"),
            provider_continuation=(ProviderReasoning(f"r-{number}", cipher),
                                   *(ProviderCallRef(c.action_id) for c in turn.tool_calls)),
        )
    monkeypatch.setattr(implementation, "execute_request", execute)
    return request, inputs, counted, delivered


def records(request):
    journal = DevJournal(request.state_root, _enveloped_run_id(request.state_root))
    return journal, ArtifactStore(request.state_root / "artifacts")


def assert_submitted(result):
    # Fake-live fixture binds a synthetic Docker identity to a local-only smoke task.
    # Real evaluation correctly refuses that mismatch; it must not be weakened here.
    assert result["terminal"] == "EVALUATOR_ERROR", result
    assert result["artifact_hashes"]["submitted_patch"]
    assert result["evaluator"]["task_acceptance"] == "ERROR"


@pytest.mark.parametrize("planning", [
    "none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1",
])
def test_real_mock_smoke_reaches_isolated_acceptance(tmp_path, planning):
    request = mock_request(tmp_path, planning).model_copy(update={
        "context_policy": segments.POLICY,
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    assert result["context_management"]["segment_count"] == 2


def test_request_bytes_are_final_utf8_not_character_or_token_estimates():
    payload = {"model": "mock", "tools": [{"description": '\\"도구'}],
               "input": [{"role": "developer", "content": canonical_json({"한": '\\"'})},
                         {"type": "reasoning", "encrypted_content": "한" * 20}]}
    sizes = segments.request_sizes(payload)
    assert sizes["request_bytes"] == len(httpx.Request("POST", "https://example.test", json=payload)
                                         .content)
    assert sizes["largest_encrypted_item_bytes"] == 60
    assert sizes["request_bytes"] > len(canonical_json(payload))
    assert segments.size_reasons({"request_bytes": 1_048_576,
                                 "largest_encrypted_item_bytes": 262_144}) == []
    assert segments.size_reasons({"request_bytes": 1_048_577,
                                 "largest_encrypted_item_bytes": 262_145}) == [
        "request_bytes", "encrypted_item_bytes"]


@pytest.mark.parametrize("planning", [
    "none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1",
])
def test_options_default_identity_and_compaction_exclusion(tmp_path, planning):
    base = mock_request(tmp_path, planning)
    new = DevRunRequest.model_validate({**base.model_dump(), "context_policy": segments.POLICY})
    assert base.context_policy == "append-v1"
    assert runner._model_hash(base, None) != runner._model_hash(new, None)
    with pytest.raises(ValueError, match="compaction"):
        DevRunRequest.model_validate({**new.model_dump(), "compact_at_input_tokens": 60_000,
                                     "accept_compaction_model_limit_reservation": True})


def test_current_snapshot_replaces_notes_plan_and_checks_without_native_rewriting():
    initial = {"public_task": {"goal": "PUBLIC_GOAL"}, "working_notes": {"findings": []},
               "working_plan": {"plan": "SUPERSEDED_PLAN"}, "current_diff": {"patch": "exact"},
               "visible_check_status": [{"status": "PASS", "diff_hash": "old"}]}
    before = assemble_model_input(system_prompt="Fixed", state=initial, history=[],
                                  context_policy=segments.POLICY)
    native = [{"type": "reasoning", "id": "r1", "encrypted_content": "opaque", "summary": []},
              {"type": "function_call", "call_id": "a1", "name": "read_file", "arguments": "{}"},
              {"type": "function_call_output", "call_id": "a1", "output": "{}"}]
    current = {**initial, "working_plan": {"plan": "CURRENT_PLAN"},
               "visible_check_status": [{"status": "NOT_RUN", "diff_hash": "new"}]}
    after = assemble_model_input(system_prompt="unused", state=current, history=native,
                                 previous_input=before, context_policy=segments.POLICY)
    assert [i for i in after if "type" in i] == native
    assert reconstruct_state(after, context_policy=segments.POLICY) == current
    assert "SUPERSEDED_PLAN" not in canonical_json(after)
    metadata = history_metadata(after, context_policy=segments.POLICY)
    assert metadata["state_update_count"] == 1
    assert validate_model_input(after, metadata, context_policy=segments.POLICY) == after


@pytest.mark.parametrize("planning", [
    "none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1",
])
def test_real_gateway_mock_provider_reaches_handoff_and_submission(
    tmp_path, monkeypatch, planning,
):
    request, inputs, counted, views = configured(monkeypatch, tmp_path, planning=planning)
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 1
    assert len(inputs) == len(counted) == 4
    assert inputs == counted
    assert result["context_management"]["transition_reasons"] == [
        "initial", "major_result_reviewed"]
    # Last input starts a fresh segment: current check result is quoted, not a pending call.
    assert not any(i.get("type") in {"reasoning", "function_call", "function_call_output"}
                   for i in inputs[-1])
    quoted = list(public_exchanges(inputs[-1], archive_kind=PUBLIC_EVIDENCE_KIND))
    assert len([i for i in quoted if i["type"] == "function_call_output"]) == 1
    for view in views:
        assert view["public_task"]["task_id"] == "csv-quoted-newline"
        assert "current_diff" in view and "remaining_budget" in view
        assert view["working_notes"]["findings"] == []
        assert "recent_inspection_outcomes" in view["evidence_ledger"]
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"
    assert bool(views[-1].get("working_plan")) == (planning != "none")
    if planning != "none":
        assert all(v["working_plan"]["policy"] == planning for v in views)
        assert views[-1]["working_plan"]["plan"]["revision"] >= 2
        assert "context_handoff" in views[-1]["working_plan"]["review_request"]["reasons"]
    journal, store = records(request)
    for event in journal.events():
        if event["event_type"] == "turn_started":
            runner._load_active_model_input(event["payload"], store, context_policy=segments.POLICY)
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before
    assert len(inputs) == 4


@pytest.mark.parametrize("boundary", [
    "provider_call_finished", "turn_decision_recorded", "working_plan_updated",
    "action_finished", "tool_batch_finished", "context_segment_started",
    "model_input_prepared", "input_count_finished",
])
def test_crash_recovery_never_repeats_provider_mutation_or_handoff(tmp_path, monkeypatch, boundary):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path, planning="brief-v1")
    def predicate(p):
        if boundary in {"provider_call_finished", "turn_decision_recorded"}:
            return any(c["name"] == "replace_text" for c in p["tool_calls"])
        if boundary == "action_finished":
            return p["result"]["tool"] == "replace_text"
        if boundary == "tool_batch_finished":
            return p["action_ids"] == ["mock-apply-mutation"]
        return boundary != "context_segment_started" or p["reason"] != "initial"
    # Before mutation's action_finished, the atomic candidate is already on disk;
    # resume must reconcile it, not apply it again or ask the provider to retry.
    _crash_journal_once(monkeypatch, event_type=boundary, predicate=predicate,
                        when="before" if boundary == "action_finished" else "after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    request = request.model_copy(update={"resume_run_id": _enveloped_run_id(request.state_root)})
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 1
    assert len(inputs) == len(counted) == 4
    journal, _ = records(request)
    plans = [e["payload"]["turn_id"] for e in journal.events()
             if e["event_type"] == "working_plan_updated"]
    assert len(plans) == len(set(plans)) == 4
    assert len([e for e in journal.events() if e["event_type"] == segments.EVENT]) == 2


def test_giant_incomplete_is_not_counted_and_original_correction_survives(tmp_path, monkeypatch):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, incomplete_at=(1,), oversized_at=(1,),
    )
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert len(inputs) == len(counted) == 5
    assert all(segments.request_sizes({"input": i})["largest_encrypted_item_bytes"]
               <= segments.MAX_ENCRYPTED_ITEM_BYTES for i in counted)
    assert "max_output_tokens" in canonical_json(views[2]["recent_attempt_result_next_question"])
    assert not any(c["attempt"] == "protocol"
                   for c in views[3]["recent_attempt_result_next_question"])
    assert views[2]["remaining_budget"]["consecutive_protocol_corrections"] == 0
    assert views[2]["current_diff"] == views[1]["current_diff"]
    assert views[2]["remaining_budget"]["model_calls"] < views[1]["remaining_budget"]["model_calls"]


def test_repeated_incomplete_cannot_reset_protocol_budget(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(
        monkeypatch, tmp_path, incomplete_at=(0, 1), oversized_at=(0, 1),
    )
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "INCOMPLETE_RESPONSE"
    assert len(inputs) == len(counted) == 2
    assert result["call_counts"]["tool"] == 0


def test_token_trigger_recounts_new_input_but_not_a_new_model_turn(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

    def tokens(self, payload, **kw):
        normal = count(self, payload, **kw)
        return 60_001 if len(counted) == 2 else normal
    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", tokens)
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert len(inputs) == 4 and len(counted) == 5
    assert "input_tokens" in result["context_management"]["transition_reasons"]
    assert result["call_counts"]["model"] == 4


@pytest.mark.parametrize("resource", ["bytes", "tokens"])
def test_fresh_required_state_over_limit_stops_without_dispatch(tmp_path, monkeypatch, resource):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    if resource == "bytes":
        monkeypatch.setattr(segments, "MAX_REQUEST_BYTES", 10)
    else:
        monkeypatch.setattr(segments, "MAX_INPUT_TOKENS", 1)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED", result
    assert not inputs and len(counted) == (resource == "tokens")
    assert result["context_management"]["limit"]["reason"] == (
        "fresh_public_state_exceeds_segment_limit")


def test_full_model_long_input_is_counted_but_never_dispatched(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    request = DevRunRequest.model_validate({
        **request.model_dump(), "model": "gpt-5.4-2026-03-05",
    })
    count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

    def long_input(self, payload, **kw):
        count(self, payload, **kw)
        return 272_001

    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", long_input)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED", result
    assert not inputs and len(counted) == 1
    assert result["call_counts"]["model"] == 0
    assert result["context_management"]["limit"]["reason"] == (
        "fresh_public_state_exceeds_segment_limit")


def test_no_reset_after_unknown_provider_dispatch(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    _crash_journal_once(monkeypatch, event_type="provider_call_started", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    result = runner.run_dev(request.model_copy(update={
        "resume_run_id": _enveloped_run_id(request.state_root),
    }))["runs"][0]
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert not inputs and len(counted) == 1


def test_corrupt_handoff_fails_before_provider_or_pending_tools(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    _crash_journal_once(monkeypatch, event_type=segments.EVENT, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, store = records(request)
    binding, _ = segments.active(journal, store)
    artifact = Artifact.model_validate(binding["handoff_artifact"])
    Path(artifact.path).write_bytes(b"corrupt")
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert not inputs and not counted


@pytest.mark.parametrize("tool", ["replace_text", "run_check", "run_probe"])
@pytest.mark.parametrize("status", ["succeeded", "failed"])
def test_major_result_waits_for_next_normal_decision_and_completed_batch(tool, status):
    events = []

    def add(kind, **payload):
        events.append({"event_type": kind, "sequence": len(events) + 1,
                       "event_hash": str(len(events) + 1), "payload": payload})
    journal = SimpleNamespace(events=lambda: events)
    binding = {"cursor": "old", "reviewed_through_sequence": 0}
    add("turn_started", turn_id="t1")
    add("turn_decision_recorded", turn_id="t1")
    add("action_finished", result={"tool": tool, "status": status})
    add("tool_batch_finished", turn_id="t1")
    assert segments.boundary_reason(journal, binding) is None
    add("turn_started", turn_id="t2")
    add("turn_decision_recorded", turn_id="t2", error_code="incomplete_response")
    assert segments.boundary_reason(journal, binding) is None
    add("turn_started", turn_id="t3")
    add("turn_decision_recorded", turn_id="t3")
    assert segments.boundary_reason(journal, binding) is None
    add("tool_batch_finished", turn_id="t3")
    assert segments.boundary_reason(journal, binding) == "major_result_reviewed"
    # This decision's own major result remains pending, not falsely reviewed.
    binding.update(cursor=segments.cursor(events), reviewed_through_sequence=7)
    assert segments.boundary_reason(journal, binding) is None


def test_notes_are_rebound_or_expired_not_resurrected_in_new_segment(tmp_path, monkeypatch):
    request, _, _, views = configured(monkeypatch, tmp_path, with_notes=True)
    assert_submitted(runner.run_dev(request)["runs"][0])
    notes = views[-1]["working_notes"]
    assert [n["statement"] for n in notes["findings"]] == ["The module imports csv."]
    assert notes["interpretation_status"] == "model_authored_unverified"
    assert notes["findings"][0]["status"] == "current"
    assert "quoted newlines" in str(notes["open_question"])


def test_size_handoff_preserves_parallel_results_and_exact_observed_sources(tmp_path, monkeypatch):
    request, inputs, counted, views = configured(monkeypatch, tmp_path, oversized_at=(0,))
    assert_submitted(runner.run_dev(request)["runs"][0])
    assert len(inputs) == len(counted) == 4
    assert not any(i.get("type") in {"reasoning", "function_call", "function_call_output"}
                   for i in inputs[1])
    quoted = list(public_exchanges(inputs[1], archive_kind=PUBLIC_EVIDENCE_KIND))
    assert [i["call_id"] for i in quoted if i["type"] == "function_call_output"] == [
        "mock-search-source", "mock-read-source"]
    index = _SourceIndex(inputs[1], archive_kind=PUBLIC_EVIDENCE_KIND)
    assert any("import csv" in value[0] for rows in index.observed.values()
               for value in rows.values())
    assert views[1]["remaining_budget"]["cost"]["settled_usage"] > 0
    assert views[1]["remaining_budget"]["cost"]["remaining"] < 1_200_000_000
    assert views[1]["remaining_budget"]["tool_actions"] == 98


@pytest.mark.parametrize("boundary", ["protocol_correction", "context_segment_started"])
def test_oversized_incomplete_and_cas_before_event_resume_once(tmp_path, monkeypatch, boundary):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, incomplete_at=(1,), oversized_at=(1,),
    )
    _crash_journal_once(monkeypatch, event_type=boundary,
                        when="before" if boundary == segments.EVENT else "after",
                        predicate=lambda p: boundary != segments.EVENT or p["reason"] != "initial")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    assert_submitted(runner.run_dev(request.model_copy(update={
        "resume_run_id": journal.run_id,
    }))["runs"][0])
    assert len(inputs) == len(counted) == 5
    assert "max_output_tokens" in canonical_json(views[2])
    assert views[2]["remaining_budget"]["consecutive_protocol_corrections"] == 0


def test_old_continuation_corruption_cannot_be_bypassed_by_size_reset(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path, oversized_at=(0,))
    _crash_journal_once(monkeypatch, event_type="turn_decision_recorded", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    event = next(e for e in journal.events() if e["event_type"] == "turn_decision_recorded")
    Path(event["payload"]["continuation_ref"]["artifact"]["path"]).write_bytes(b"corrupt")
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert result["call_counts"]["tool"] == 0
    assert len(inputs) == len(counted) == 1


def test_unknown_count_does_not_reseed_or_redispatch(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    _crash_journal_once(monkeypatch, event_type="input_count_started", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert result["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"
    assert result["context_management"]["segment_count"] == 1
    assert not inputs and not counted
