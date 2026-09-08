from __future__ import annotations

import json

from test_dev_context_v12 import note_call, source_note
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.tools import dev_tool_schemas
from patchloop.dev.working_notes import memory_update_schema


def test_current_citation_does_not_claim_semantic_revalidation_after_edit(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    # Deliberately cite an unchanged header for an interpretation of another line.
    # Admission validates the citation, not whether this interpretation follows.
    update = source_note("The current editable value is zero.", 1, 1)
    update["open_question"] = "Which public observation will test the proposed change?"
    gateway.record_working_notes_update([note_call("note", update)], turn_id="note")
    first = gateway.working_notes()["findings"][0]
    assert first["status"] == "current"
    assert first["interpretation_status"] == "model_authored_unverified"

    changed = gateway.execute(_mutation("edit"))
    assert changed.status == "succeeded"
    notes = gateway.working_notes()
    finding = notes["findings"][0]
    assert finding["statement"] == "The current editable value is zero."
    assert finding["status"] == "current"
    assert finding["interpretation_status"] == "model_authored_unverified"
    assert "not that the statement was revalidated" in notes["interpretation"]
    assert notes["last_source_lifecycle"]["rebound_note_ids"] == ["n1"]

    before = gateway.journal.path.read_bytes()
    assert _restart(gateway).working_notes() == notes
    assert gateway.journal.path.read_bytes() == before
    assert "source_bodies_by_note_id" not in json.dumps(notes)

    # A later useful turn can revise the interpretation from observed post-image
    # evidence and close its question. No extra source read or hard plan is needed.
    revised = source_note("The edited source now sets editable to one.", 50, 50)
    revised["findings"][0]["note_id"] = "n1"
    revised["open_question"] = None
    receipt = gateway.record_working_notes_update(
        [note_call("revise", revised)], turn_id="revise",
    )["receipt"]
    assert receipt["findings"][0]["status"] == "updated"
    refreshed = gateway.working_notes()
    assert refreshed["open_question"] is None
    assert refreshed["findings"][0]["evidence"][0]["start_line"] == 50
    assert refreshed["findings"][0]["interpretation_status"] == "model_authored_unverified"
    assert _restart(gateway).working_notes() == refreshed


def test_guidance_preserves_exact_edit_and_optional_note_wire_contracts():
    schemas = dev_tool_schemas(finish_enabled=True)
    edit = next(schema for schema in schemas if schema["name"] == "replace_text")
    old_text = edit["parameters"]["properties"]["old_text"]
    assert "smallest sufficient unique anchor" in old_text["description"]
    assert "line breaks" in old_text["description"]
    assert old_text["maxLength"] == 20_000
    assert set(edit["parameters"]["required"]) == {
        "path", "old_text", "new_text", "occurrence", "hypothesis",
        "expected_behavior", "causal_revision", "turn_decision",
    }
    notes = memory_update_schema()
    assert notes["type"] == ["object", "null"]
    assert set(notes["required"]) == {
        "findings", "remove_note_ids", "open_question", "verification_updates",
    }
    statement = notes["properties"]["findings"]["items"]["properties"]["statement"]
    assert "behavior-bearing" in statement["description"]
    assert statement["maxLength"] == 400
    assert "Resolve an answered question" in notes["properties"]["open_question"]["description"]
    for instruction in (
        "smallest sufficient unique exact anchor", "status=current only means",
        "interpretation remains unverified", "post-image", "public input",
        "No update or three-part plan is required each turn",
        "Use concern_id=null for a distinct concern",
    ):
        assert instruction in DEV_SYSTEM_PROMPT
    assert dev_tool_surface_hash() != (
        "sha256:6671634f44eb187dd5631bfbcd4788df848b9933906436c0388ee68e80d59ab7"
    )
