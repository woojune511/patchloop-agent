"""Primary action outcomes stay distinct from optional annotation receipts."""

from __future__ import annotations

import copy
import json

import pytest
from test_dev_context_v12 import note_call, source_note
from test_dev_feedback_integration_v18 import _context
from test_dev_notes_lifecycle_v15 import _gateway, _restart

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, segments, working_plan
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.conversation import (
    APPEND_POLICY,
    WINDOW_POLICY,
    history_metadata,
    reconstruct_state,
)
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.util import canonical_json

POLICIES = (APPEND_POLICY, WINDOW_POLICY, segments.POLICY)
ANNOTATIONS = {"memory_update_result", "plan_update_result", "working_notes_after_batch"}


def _build(gateway, store, policy, results, *, handoff=False, planning="none"):
    context = json.loads(_context(gateway, results))
    if planning != "none":
        context["working_plan"] = working_plan.project(
            gateway.journal.events(), diff_hash=gateway.current_diff_hash,
            gate=context["workflow_gate"], policy=planning,
        )
    return runner._build_model_input(
        journal=gateway.journal, artifact_store=store, context=canonical_json(context),
        latest_tool_results=results, context_policy=policy, planning_policy=planning,
        force_segment_reason="request_bytes" if handoff else None,
    )


def _begin(gateway, store, policy, items, call):
    artifact = store.put_json(items)
    payload = {
        "turn_id": f"turn-{call.action_id}",
        "model_input_artifact": artifact.model_dump(mode="json"),
        "model_input_hash": artifact.content_hash,
        "native_history": history_metadata(items, context_policy=policy),
    }
    if policy == WINDOW_POLICY:
        payload["context_window"] = runner._window_binding(gateway.journal, store, items)
    if policy == segments.POLICY:
        segments.commit(gateway.journal, store)
        payload["context_segment"] = runner._segment_input_binding(gateway.journal, store)
    gateway.journal.append("turn_started", payload)
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": payload["turn_id"], "tool_calls": [call.model_dump(mode="json")],
    })
    return payload["turn_id"]


def _batch(gateway, call, turn):
    receipt = gateway.record_working_notes_update([call], turn_id=turn)
    result = gateway.execute(call)
    gateway.journal.append("tool_batch_finished", {
        "turn_id": turn, "action_ids": [call.action_id],
    })
    return receipt, result


def _outputs(items, policy):
    archive = PUBLIC_EVIDENCE_KIND if policy != APPEND_POLICY else None
    return {item["call_id"]: json.loads(item["output"])
            for item in public_exchanges(items, archive_kind=archive)
            if item.get("type") == "function_call_output"}


def _bad_note_call(primary):
    # The source has not been observed yet. A simultaneous read cannot authorize this note.
    update = source_note("The first declaration has been observed.")
    update["open_question"] = None
    if primary == "read_file":
        return note_call("primary", update)
    return RequestedTool(name="run_probe", action_id="primary", arguments={
        "question": "Does the original caller return the requested value?",
        "python_source": "record_observation(call_target())",
        "replay_action_id": None,
        "purpose": {
            "kind": "original_requirement", "requirement_quote": "Invented public quotation.",
            "entrypoint": "src.public_call", "input_conditions": "No arguments.",
            "environment_conditions": "Current working tree.", "expected_json": "1",
        },
    }, turn_decision={
        "mode": "verify", "basis": "Exercise the reported caller.", "memory_update": update,
    })


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("primary", ["read_file", "run_probe"])
def test_optional_note_rejection_does_not_replace_primary_result(
    tmp_path, monkeypatch, policy, primary,
):
    gateway = _gateway(tmp_path)
    store = ArtifactStore(tmp_path / "artifacts")

    def forbidden(*args, **kwargs):
        pytest.fail("the invalid requirement quote must be rejected before probe execution")

    monkeypatch.setattr(gateway, "_run_probe", forbidden)
    call = _bad_note_call(primary)
    with gateway.journal.execution_lock():
        seed = _build(gateway, store, policy, [])
        turn = _begin(gateway, store, policy, seed, call)
        update, result = _batch(gateway, call, turn)
        assert update["receipt"]["status"] == "rejected"
        assert update["receipt"]["findings"][0]["status"] == "rejected"
        assert update["receipt"]["findings"][0]["code"] == "unobserved_source_range"
        assert update["receipt"]["note_ids_after_update"] == []
        delivered = _build(gateway, store, policy, [result])

        outcome = _outputs(delivered, policy)[call.action_id]
        assert not ANNOTATIONS.intersection(outcome)
        assert outcome["status"] == result.status
        assert outcome["error_code"] == result.error_code
        assert outcome["message"] == result.message
        if primary == "run_probe":
            assert outcome["status"] == "failed" and outcome["error_code"] == "CONTRACT_ERROR"
            assert outcome["message"] == (
                "reproduction requirement_quote must occur in the public issue")
            assert outcome["output"] == result.output
        else:
            assert outcome["status"] == "succeeded" and outcome["error_code"] is None
            assert "header = 0" in canonical_json(outcome["output"])
        state = reconstruct_state(delivered, context_policy=policy)
        notes = state["working_notes"]
        assert notes["last_update_result"] == update["receipt"]
        assert notes["available_note_ids"] == []
        assert "last_update_diagnostics" not in notes
        assert notes["last_update_result"]["scope"] == "before_tool_batch"
        assert notes["last_update_result"]["action_id"] == call.action_id

        # Rebuilding after restart neither repeats an action nor rewrites durable input/results.
        saved = gateway.journal.path.read_bytes()
        before = copy.deepcopy(delivered)
        gateway = _restart(gateway)
        assert _build(gateway, store, policy, [result]) == delivered
        assert gateway.journal.path.read_bytes() == saved and delivered == before

        if policy == segments.POLICY:
            handed_off = _build(gateway, store, policy, [result], handoff=True)
            assert not any(item.get("type") == "function_call_output" for item in handed_off)
            # A fresh handoff quotes the canonical result, not its native read projection.
            quoted = _outputs(handed_off, policy)[call.action_id]
            recorded = result.model_dump(mode="json", exclude={"replayed"})
            assert {key: quoted[key] for key in recorded} == recorded
            assert not ANNOTATIONS.intersection(quoted)
            handoff_notes = reconstruct_state(handed_off, context_policy=policy)["working_notes"]
            assert handoff_notes["last_update_result"] == update["receipt"]
            assert handoff_notes["available_note_ids"] == []
            assert "last_update_diagnostics" not in handoff_notes
            saved = gateway.journal.path.read_bytes()
            assert _build(_restart(gateway), store, policy, [result]) == handed_off
            assert gateway.journal.path.read_bytes() == saved

    decision = next(event["payload"] for event in gateway.journal.events()
                    if event["event_type"] == "turn_decision_recorded")
    assert decision["tool_calls"] == [call.model_dump(mode="json")]
    finished = [event["payload"]["result"] for event in gateway.journal.events()
                if event["event_type"] == "action_finished"]
    assert finished == [result.model_dump(mode="json")]
    assert not any(event["event_type"] == "provider_call_started"
                   for event in gateway.journal.events())


@pytest.mark.parametrize("policy", POLICIES)
def test_optional_plan_rejection_stays_in_current_plan_state(tmp_path, policy):
    gateway = _gateway(tmp_path)
    store = ArtifactStore(tmp_path / "artifacts")
    call = note_call("read-with-bad-plan", None)
    call.turn_decision.plan_update = {"invalid": "not a plan string"}
    with gateway.journal.execution_lock():
        seed = _build(gateway, store, policy, [], planning=working_plan.POLICY)
        turn = _begin(gateway, store, policy, seed, call)
        update = working_plan.record(
            gateway.journal, [call], turn_id=turn, diff_hash=gateway.current_diff_hash,
            gate="needs_mutation", policy=working_plan.POLICY,
        )
        _, result = _batch(gateway, call, turn)
        delivered = _build(gateway, store, policy, [result], planning=working_plan.POLICY)
        outcome = _outputs(delivered, policy)[call.action_id]
        assert outcome["status"] == "succeeded" and not ANNOTATIONS.intersection(outcome)
        plan = reconstruct_state(delivered, context_policy=policy)["working_plan"]
        assert plan["last_update_result"] == update
        assert plan["last_update_result"]["status"] == "rejected"
        assert plan["plan"] is None
        if policy == segments.POLICY:
            handed_off = _build(gateway, store, policy, [result], handoff=True,
                                planning=working_plan.POLICY)
            current = reconstruct_state(handed_off, context_policy=policy)["working_plan"]
            assert current["last_update_result"] == update
            assert current["plan"] is None
            assert _outputs(handed_off, policy)[call.action_id] == result.model_dump(
                mode="json", exclude={"replayed"})
