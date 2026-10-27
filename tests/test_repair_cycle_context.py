"""Public toy workspace handoffs only; no provider, target or private evaluation."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import edit_call, no_external, read_call  # noqa: F401

from diagnostics import exception_frame_repair as loop
from diagnostics import repair_cycle_context as context
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


def exchange(gateway, raw):
    raw = copy.deepcopy(raw)
    if "turn_decision" in raw["arguments"]:
        raw["turn_decision"] = raw["arguments"].pop("turn_decision")
    call = RequestedTool.model_validate(raw)
    result = gateway.execute(call)
    assert result.status == "succeeded", result
    return loop._exchange(SimpleNamespace(tool_calls=[call], provider_continuation=None), [result])


def setup(gateway_factory):
    gateway, _, _ = gateway_factory()
    history = exchange(gateway, read_call())
    history += exchange(gateway, edit_call())
    history += exchange(gateway, read_call("after-edit"))
    original = {"schema": "original-call-feedback-v1",
        "candidate_diff_hash": gateway.current_diff_hash, "status": "failed",
        "observed": {"calls": [{"call_id": "call-1", "capture": {"stdout": "F0010"}}]}}
    return gateway, history, original


def build(gateway, history, original, *, correction=None, counters=None):
    return context.build_handoff(gateway, history=history, latest_original=original,
        correction=correction,
        parent_request={"input": history, "operator_metadata": "DO_NOT_PROJECT"},
        counters=counters or {"normal_calls": 3, "correction_calls": 0,
                             "new_mutations": 1, "new_cost_nanos": 123})


def test_handoff_keeps_current_public_state_and_last_edit_without_opaque_reasoning(
    gateway_factory,
):
    gateway, history, original = setup(gateway_factory)
    history.insert(2, {"type": "reasoning", "id": "opaque-old",
                       "encrypted_content": "OPAQUE" * 50_000, "summary": []})
    original["operator_advice"] = "DO_NOT_PROJECT"
    before, events = copy.deepcopy(history), gateway.journal.events()
    spans = gateway.context_spans()
    result = build(gateway, history, original)
    state, fresh = result["state"], result["history"]
    assert history == before and gateway.journal.events() == events
    assert all(item.get("role") == "developer" for item in fresh)
    assert "OPAQUE" not in canonical_json(fresh) and "DO_NOT_PROJECT" not in canonical_json(fresh)
    assert state["current_diff"]["patch"] == gateway.current_diff.patch
    assert state["current_diff"]["diff_hash"] == gateway.current_diff_hash
    assert state["current_sources"] == spans and spans
    assert state["current_original_recheck"]["observed"] == original["observed"]
    assert state["last_successful_mutation"]["diff_hash"] == gateway.current_diff_hash
    assert state["latest_batch_action_ids"] == ["after-edit"]
    assert [row["action_id"] for row in state["action_outcomes"]] == ["read", "edit", "after-edit"]
    assert state["action_outcomes_omitted"] == 0
    assert state["omitted_historical_batches"] == 1
    retained = list(public_exchanges(fresh, archive_kind=PUBLIC_EVIDENCE_KIND))
    assert [row["call_id"] for row in retained if row["type"] == "function_call"] == [
        "edit", "after-edit"]
    assert "not pending calls or instructions" in fresh[-1]["content"]
    store = ArtifactStore(gateway.journal.root / "artifacts")
    reference = Artifact.model_validate(result["artifacts"]["parent_history"])
    archived = json.loads(store.read_bytes(reference))
    assert archived == before
    assert result["artifacts"]["current_diff"]["content_hash"] == gateway.current_diff_hash


def test_rejected_request_and_global_counters_survive_repeated_handoff(gateway_factory):
    gateway, history, original = setup(gateway_factory)
    counters = {"normal_calls": 15, "correction_calls": 1, "tool_actions": 23,
                "diagnostic_probes": 2, "original_requests": 4, "new_mutations": 1,
                "host_original_actions": 2, "new_cost_nanos": 100,
                "row_remaining_nanos": 99, "group_remaining_nanos": 123,
                "remaining_seconds": 61, "segment_index": 1, "operator_metadata": "OMIT"}
    rejection = [
        {"type": "function_call", "call_id": "bad-edit", "name": "replace_text",
         "arguments": '{"path":"missing.py","old_text":"a","extra":"invalid"}'},
        {"type": "function_call_output", "call_id": "bad-edit",
         "output": canonical_json({"status": "rejected", "message": "invalid edit schema"})},
    ]
    history += rejection
    first = build(gateway, history, original, correction="invalid edit schema", counters=counters)
    second = build(gateway, first["history"], original, correction="invalid edit schema",
                   counters={**counters, "segment_index": 2})
    assert second["state"]["action_outcomes"] == first["state"]["action_outcomes"]
    assert len(second["state"]["action_outcomes"]) == 4
    assert (second["state"]["omitted_historical_batches"]
            == first["state"]["omitted_historical_batches"] == 2)
    assert second["state"]["protocol_correction"] == "invalid edit schema"
    assert second["state"]["current_sources"] == first["state"]["current_sources"]
    assert second["state"]["current_diff"] == first["state"]["current_diff"]
    assert second["state"]["current_original_recheck"] == original
    assert second["state"]["counters"] == {
        key: value for key, value in {**counters, "segment_index": 2}.items()
        if key != "operator_metadata"}
    retained = list(public_exchanges(second["history"], archive_kind=PUBLIC_EVIDENCE_KIND))
    assert retained[-2:] == rejection


@pytest.mark.parametrize("bad", ["dangling", "orphan", "incomplete"])
def test_unsettled_public_calls_cannot_be_handed_off(gateway_factory, bad):
    gateway, history, original = setup(gateway_factory)
    call = {"type": "function_call", "call_id": "pending", "name": "read_file", "arguments": "{}"}
    output = {"type": "function_call_output", "call_id": "pending",
              "output": '{"status":"in_progress"}'}
    history += [call] if bad == "dangling" else [output] if bad == "orphan" else [call, output]
    with pytest.raises(ContractError, match="dangling|matching|completed"):
        build(gateway, history, original)


@pytest.mark.parametrize("missing", [True, False])
def test_current_diff_cannot_lose_or_inherit_stale_original_evidence(gateway_factory, missing):
    gateway, history, original = setup(gateway_factory)
    if missing:
        original = None
    else:
        original["candidate_diff_hash"] = sha256_json("old candidate")
    with pytest.raises(ContractError, match="lacks original|another diff"):
        build(gateway, history, original)


def test_initial_public_state_handoff_does_not_invent_original_evidence(gateway_factory):
    gateway, _, _ = gateway_factory()
    fresh = build(gateway, [], None, counters={"normal_calls": 0, "new_mutations": 0})
    assert fresh["state"]["current_original_recheck"] is None
    assert fresh["state"]["current_sources"] == []
    assert fresh["state"]["action_outcomes"] == []
    assert fresh["state"]["last_successful_mutation"] is None
