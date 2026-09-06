from __future__ import annotations

import copy

import pytest
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _note, _read, _restart

from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.working_notes import memory_update_schema


def _update(*, note_id=None, end_line=3):
    return {
        "findings": [{
            "note_id": note_id,
            "statement": "The observed stable declaration records the mechanism.",
            "evidence": [{
                "kind": "source", "path": "src.py", "start_line": 3,
                "end_line": end_line,
            }],
        }],
        "remove_note_ids": [], "open_question": None,
    }


def _with_update(call, update):
    return call.model_copy(update={
        "turn_decision": call.turn_decision.model_copy(update={"memory_update": update}),
    })


def test_mutation_receipt_is_before_batch_not_post_mutation_availability(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    before_hash = gateway.current_diff_hash
    call = _with_update(_mutation(
        "edit", "stable = 'observed mechanism'", "stable = 'changed mechanism'",
    ), _update())
    payload = gateway.record_working_notes_update([call], turn_id="turn-edit")
    receipt = copy.deepcopy(payload["receipt"])
    assert receipt["scope"] == "before_tool_batch"
    assert receipt["diff_hash_at_update"] == before_hash
    assert receipt["note_ids_after_update"] == ["n1"]
    assert "available_note_ids" not in receipt
    assert "before this tool batch" in receipt["findings"][0]["message"]
    assert "working_notes.available_note_ids" in receipt["findings"][0]["message"]

    assert gateway.execute(call).status == "succeeded"
    assert gateway.current_diff_hash != before_hash
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == []
    assert notes["last_update_result"] == receipt
    assert notes["last_source_lifecycle"]["expired_notes"] == [
        {"note_id": "n1", "reason": "source_changed"},
    ]
    before = gateway.journal.path.read_bytes()
    restored = _restart(gateway)
    assert restored.working_notes() == notes
    assert restored.record_working_notes_update([call], turn_id="turn-edit") == payload
    assert restored.execute(call).status == "succeeded"
    assert restored.accepted_mutations == 1
    assert gateway.journal.path.read_bytes() == before


def test_rolled_back_mutation_preserves_current_ids_and_historical_receipt(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    before_hash = gateway.current_diff_hash
    before_source = (gateway.workspace / "src.py").read_bytes()
    oversized = "\n".join(f"new_line_{number} = 1" for number in range(60))
    call = _with_update(_mutation("rejected-edit", "stable = 'observed mechanism'", oversized),
                        _update())
    receipt = gateway.record_working_notes_update([call], turn_id="turn-rejected")["receipt"]
    result = gateway.execute(call)
    assert result.status == "failed"
    assert result.output["mutation_failure"]["rolled_back"] is True
    assert gateway.current_diff_hash == before_hash
    assert (gateway.workspace / "src.py").read_bytes() == before_source
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == ["n1"]
    assert notes["last_update_result"] == receipt
    assert receipt["diff_hash_at_update"] == before_hash
    assert receipt["note_ids_after_update"] == ["n1"]
    assert _restart(gateway).working_notes() == notes
    assert gateway.accepted_mutations == 0


def test_no_update_creates_no_receipt_and_does_not_freeze_current_note_ids(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    _note(gateway)
    earlier_receipt = gateway.working_notes()["last_update_result"]
    call = _mutation("without-update", "stable = 'observed mechanism'", "stable = 'changed'")
    journal_before = gateway.journal.path.read_bytes()
    assert gateway.record_working_notes_update([call], turn_id="no-update") == {
        "status": "not_requested",
    }
    assert gateway.journal.path.read_bytes() == journal_before
    assert gateway.execute(call).status == "succeeded"
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == []
    assert notes["last_update_result"] == earlier_receipt
    assert earlier_receipt["note_ids_after_update"] == ["n1"]
    assert _restart(gateway).working_notes() == notes


@pytest.mark.parametrize("invalid", ["unknown_id", "unobserved_range", "shape"])
def test_rejected_annotation_has_temporal_receipt_without_rejecting_action(tmp_path, invalid):
    gateway = _gateway(tmp_path)
    _read(gateway)
    _note(gateway)
    update = _update(note_id="n999") if invalid == "unknown_id" else _update(end_line=999)
    if invalid == "shape":
        update = {"findings": "private-sentinel-not-to-echo"}
    call = RequestedTool(
        name="read_file", action_id="read-after-rejected-note",
        arguments={"path": "src.py", "start_line": 1, "end_line": 3},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Check the public declaration.",
            evidence_goal="Observe the source without requiring valid annotation.",
            memory_update=update,
        ),
    )
    receipt = gateway.record_working_notes_update([call], turn_id="invalid-note")["receipt"]
    assert receipt["status"] == "rejected"
    assert receipt["scope"] == "before_tool_batch"
    assert receipt["diff_hash_at_update"] == gateway.current_diff_hash
    assert receipt["note_ids_after_update"] == ["n1"]
    assert "private-sentinel-not-to-echo" not in str(receipt)
    assert gateway.execute(call).status == "succeeded"
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == ["n1"]
    assert notes["last_update_result"] == receipt
    assert _restart(gateway).working_notes() == notes


def test_wire_description_distinguishes_historical_receipt_and_current_note_ids():
    description = memory_update_schema()["description"]
    assert "before-tool-batch" in description
    assert "note_ids_after_update is historical" in description
    assert "working_notes.available_note_ids" in description
    assert "for later updates" not in description
