from __future__ import annotations

import copy
import json
from types import SimpleNamespace

from test_dev_context_v12 import note_call, source_note
from test_dev_note_temporal_v18 import _update, _with_update
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore


def _completed_batch(gateway, calls, turn_id):
    gateway.journal.append("turn_started", {"turn_id": turn_id})
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [call.model_dump(mode="json") for call in calls],
    })
    update = gateway.record_working_notes_update(calls, turn_id=turn_id)
    results = gateway.execute_batch(calls)
    assert all(result.status == "succeeded" for result in results)
    gateway.journal.append("tool_batch_finished", {
        "turn_id": turn_id, "action_ids": [call.action_id for call in calls],
    })
    return update, results


def _context(gateway, results):
    return runner._build_context(
        package=SimpleNamespace(public=SimpleNamespace(
            model_dump=lambda **kwargs: {"task_id": "public-note-feedback"},
        )),
        gateway=gateway, journal=gateway.journal, correction=None,
        latest_tool_results=results, counters=runner._RunCounters(),
        elapsed_seconds=0, limits=gateway.limits,
    )


def _input(gateway, results, tmp_path, *, context=None):
    return runner._build_model_input(
        journal=gateway.journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
        context=_context(gateway, results) if context is None else context,
        latest_tool_results=results,
    )


def _outputs(items):
    return {
        item["call_id"]: json.loads(item["output"])
        for item in items if item.get("type") == "function_call_output"
    }


def _expiring_mutation(gateway):
    _read(gateway)
    call = _with_update(_mutation(
        "expire-note", "stable = 'observed mechanism'", "stable = 'changed mechanism'",
    ), _update())
    payload, results = _completed_batch(gateway, [call], "turn-expire")
    return call, payload, results


def test_native_mutation_feedback_separates_update_receipt_from_current_ids(tmp_path):
    gateway = _gateway(tmp_path)
    before_hash = gateway.current_diff_hash
    call, payload, results = _expiring_mutation(gateway)
    original_receipt = copy.deepcopy(payload["receipt"])
    items = _input(gateway, results, tmp_path)
    output = _outputs(items)[call.action_id]
    assert output["memory_update_result"] == original_receipt
    assert original_receipt["scope"] == "before_tool_batch"
    assert original_receipt["diff_hash_at_update"] == before_hash
    assert original_receipt["note_ids_after_update"] == ["n1"]
    assert output["working_notes_after_batch"] == {
        "scope": "after_completed_tool_batch", "turn_id": "turn-expire",
        "diff_hash": gateway.current_diff_hash, "available_note_ids": [],
        "expired_notes": [{"note_id": "n1", "reason": "source_changed"}],
    }
    context = json.loads(items[-1]["content"])
    assert context["current_diff"]["patch_hash"] != before_hash
    assert context["working_notes"]["available_note_ids"] == []
    assert context["working_notes"]["last_update_result"] == {
        "turn_id": "turn-expire", "action_id": call.action_id,
        "delivery": "preceding_function_call_output",
    }
    assert "last_update_diagnostics" not in context["working_notes"]
    assert payload["receipt"] == original_receipt
    assert sum("memory_update_result" in result for result in _outputs(items).values()) == 1


def test_parallel_first_owner_alone_gets_pre_and_post_batch_note_feedback(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    calls = [
        note_call("without-update", None),
        note_call("owner", source_note("The observed declaration is stable.", 3, 3)),
        note_call("ignored", source_note("An additional annotation must be ignored.", 3, 3)),
    ]
    original_calls = [call.model_dump(mode="json") for call in calls]
    payload, results = _completed_batch(gateway, calls, "parallel")
    items = _input(gateway, results, tmp_path)
    outputs = _outputs(items)
    assert outputs["owner"]["memory_update_result"] == payload["receipt"]
    assert outputs["owner"]["working_notes_after_batch"] == {
        "scope": "after_completed_tool_batch", "turn_id": "parallel",
        "diff_hash": gateway.current_diff_hash, "available_note_ids": ["n1"],
        "expired_notes": [],
    }
    for action_id in ("without-update", "ignored"):
        assert "memory_update_result" not in outputs[action_id]
        assert "working_notes_after_batch" not in outputs[action_id]
    assert "ignored_additional_memory_updates" in {
        diagnostic["code"] for diagnostic in payload["receipt"]["diagnostics"]
    }
    context = json.loads(items[-1]["content"])
    assert context["working_notes"]["available_note_ids"] == ["n1"]
    echoed = {
        item["call_id"]: json.loads(item["arguments"])["turn_decision"]
        for item in items if item.get("type") == "function_call"
    }
    assert echoed == {
        call.action_id: call.turn_decision.model_dump(mode="json") for call in calls
    }
    assert [call.model_dump(mode="json") for call in calls] == original_calls


def test_old_expiry_is_not_reported_as_an_unrelated_batch_lifecycle_event(tmp_path):
    gateway = _gateway(tmp_path)
    _expiring_mutation(gateway)
    prior_lifecycle = gateway.working_notes()["last_source_lifecycle"]
    assert prior_lifecycle["expired_notes"]
    call = note_call("later-read", {
        "findings": [], "remove_note_ids": [], "open_question": "Which branch remains?",
    })
    payload, results = _completed_batch(gateway, [call], "later")
    items = _input(gateway, results, tmp_path)
    output = _outputs(items)[call.action_id]
    assert output["memory_update_result"] == payload["receipt"]
    assert output["working_notes_after_batch"]["expired_notes"] == []
    assert output["working_notes_after_batch"]["available_note_ids"] == []
    assert output["working_notes_after_batch"]["turn_id"] == "later"
    context = json.loads(items[-1]["content"])
    assert context["working_notes"]["last_source_lifecycle"] == prior_lifecycle

    no_update = note_call("later-without-update", None)
    payload, results = _completed_batch(gateway, [no_update], "without-update")
    assert payload == {"status": "not_requested"}
    output = _outputs(_input(gateway, results, tmp_path))[no_update.action_id]
    assert "memory_update_result" not in output
    assert "working_notes_after_batch" not in output


def test_restart_rebuilds_identical_feedback_without_execution_or_new_journal_events(tmp_path):
    gateway = _gateway(tmp_path)
    call, payload, results = _expiring_mutation(gateway)
    stored_context = _context(gateway, results)
    items = _input(gateway, results, tmp_path, context=stored_context)
    before = gateway.journal.path.read_bytes()
    counts = {
        event_type: sum(event["event_type"] == event_type for event in gateway.journal.events())
        for event_type in ("turn_started", "provider_call_started", "action_finished")
    }
    assert counts == {"turn_started": 1, "provider_call_started": 0, "action_finished": 2}
    restarted = _restart(gateway)
    assert restarted.record_working_notes_update([call], turn_id="turn-expire") == payload
    restored_items = _input(restarted, results, tmp_path)
    original_context = json.loads(items[-1]["content"])
    restored_context = json.loads(restored_items[-1]["content"])
    for key, value in original_context.items():
        assert restored_context[key] == value, key
    assert restored_items[:-1] == items[:-1]
    # The persisted context preserves its original JSON key order. Hydrating
    # gateway state may reorder nested dictionaries, but not the public values.
    assert _input(restarted, results, tmp_path, context=stored_context) == items
    assert restarted.accepted_mutations == 1
    assert restarted.working_notes()["available_note_ids"] == []
    assert gateway.journal.path.read_bytes() == before
