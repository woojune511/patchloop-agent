from __future__ import annotations

import copy

import pytest
from test_dev_context_v12 import note_call, observe, source_note
from test_dev_context_v12 import source_gateway as source_gateway

from patchloop.dev.tools import DevToolGateway
from patchloop.dev.working_notes import WorkingNotesUpdate, memory_update_schema


def restore(gateway, tracked):
    restored = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=None,
        journal=gateway.journal, limits=gateway.limits,
    )
    restored._tracked_path = tracked
    return restored


def test_memory_wire_requires_explicit_identity_and_removals():
    schema = memory_update_schema()
    assert set(schema["required"]) == {
        "findings", "remove_note_ids", "open_question", "verification_updates",
    }
    finding = schema["properties"]["findings"]["items"]
    assert set(finding["required"]) == {"note_id", "statement", "evidence"}
    assert finding["properties"]["note_id"]["type"] == ["string", "null"]
    assert schema["properties"]["remove_note_ids"]["maxItems"] == 6
    # Local old synthetic decisions can still be interpreted without changing any
    # saved journal. The strict provider schema above requires both new fields.
    legacy = source_note()
    del legacy["findings"][0]["note_id"]
    del legacy["remove_note_ids"]
    assert WorkingNotesUpdate.model_validate(legacy).findings[0].note_id is None


def test_distinct_notes_share_source_and_explicit_update_can_change_citation(source_gateway):
    gateway, _, tracked = source_gateway
    observe(gateway, "src.py", 1, 4)
    update = source_note("The first line establishes the existing entry behavior.")
    update["findings"].append({
        **copy.deepcopy(update["findings"][0]),
        "statement": "Current approach: preserve the existing entry behavior.",
    })
    payload = gateway.record_working_notes_update([note_call("a", update)], turn_id="a")
    assert payload["allocated_note_ids"] == ["n1", "n2"]
    assert payload["receipt"]["scope"] == "before_tool_batch"
    assert payload["receipt"]["diff_hash_at_update"] == gateway.current_diff_hash
    assert payload["receipt"]["note_ids_after_update"] == ["n1", "n2"]
    assert "available_note_ids" not in payload["receipt"]
    assert gateway.working_notes()["available_note_ids"] == ["n1", "n2"]
    assert [note["note_id"] for note in gateway.working_notes()["findings"]] == ["n1", "n2"]
    revised = source_note("Preserve entry behavior and change the adjacent branch.", 2, 3)
    revised["findings"][0]["note_id"] = "n1"
    revised["remove_note_ids"] = ["n2"]
    revised["open_question"] = None
    merged = gateway.record_working_notes_update([note_call("b", revised)], turn_id="b")
    assert merged["allocated_note_ids"] == []
    assert merged["removed_note_ids"] == ["n2"]
    assert merged["retained_note_ids"] == ["n1"]
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == ["n1"]
    assert notes["open_question"] is None
    assert notes["findings"][0]["evidence"][0]["start_line"] == 2
    assert notes["findings"][0]["model_authored"] is True
    assert restore(gateway, tracked).working_notes() == notes


@pytest.mark.parametrize("failure", ["unknown_id", "unobserved_source", "duplicate_update"])
def test_invalid_merge_never_deletes_source_notes_or_blocks_read(source_gateway, failure):
    gateway, _, _ = source_gateway
    observe(gateway, "src.py", 1, 4)
    gateway.record_working_notes_update([note_call("a", source_note())], turn_id="a")
    update = source_note("A revised public observation.")
    update["findings"][0]["note_id"] = "n1"
    update["remove_note_ids"] = ["n1"]
    if failure == "unknown_id":
        update["findings"][0]["note_id"] = "n999"
    elif failure == "unobserved_source":
        update["findings"][0]["evidence"][0]["end_line"] = 99
    else:
        update["findings"].append(copy.deepcopy(update["findings"][0]))
    call = note_call("read-after-invalid-note", update)
    payload = gateway.record_working_notes_update([call], turn_id="b")
    assert payload["removed_note_ids"] == []
    assert "removals_skipped_after_invalid_finding" in payload["diagnostics"]
    assert gateway.working_notes()["findings"][0]["note_id"] == "n1"
    assert gateway.execute(call).status == "succeeded"


def test_eviction_and_durable_append_crash_do_not_reuse_note_ids(source_gateway, monkeypatch):
    gateway, _, tracked = source_gateway
    observe(gateway, "src.py", 1, 4)
    for index in range(1, 8):
        payload = gateway.record_working_notes_update(
            [note_call(str(index), source_note(f"Distinct public fact {index}."))],
            turn_id=f"turn{index}",
        )
    assert payload["evicted_note_ids"] == ["n1"]
    assert [note["note_id"] for note in gateway.working_notes()["findings"]] == [
        f"n{index}" for index in range(2, 8)
    ]
    original_append = gateway.journal.append

    def crash_after_append(event_type, payload):
        result = original_append(event_type, payload)
        if event_type == "working_notes_updated":
            raise RuntimeError("injected crash after durable notes before in-memory apply")
        return result

    monkeypatch.setattr(gateway.journal, "append", crash_after_append)
    call = note_call("eight", source_note("Distinct public fact 8."))
    with pytest.raises(RuntimeError, match="injected crash"):
        gateway.record_working_notes_update([call], turn_id="turn8")
    restored = restore(gateway, tracked)
    monkeypatch.setattr(gateway.journal, "append", original_append)
    before = gateway.journal.path.read_bytes()
    replay = restored.record_working_notes_update([call], turn_id="turn8")
    assert replay["allocated_note_ids"] == ["n8"]
    assert gateway.journal.path.read_bytes() == before
    assert [note["note_id"] for note in restored.working_notes()["findings"]] == [
        f"n{index}" for index in range(3, 9)
    ]
    next_payload = restored.record_working_notes_update(
        [note_call("nine", source_note("Distinct public fact 9."))], turn_id="turn9",
    )
    assert next_payload["allocated_note_ids"] == ["n9"]


def test_source_rebinding_preserves_id_and_expiry_is_durable_on_next_update(source_gateway):
    gateway, sources, tracked = source_gateway
    observe(gateway, "src.py", 1, 4)
    gateway.record_working_notes_update(
        [note_call("a", source_note("The branch contains second.", 2, 2))], turn_id="a",
    )
    sources["src.py"] = b"inserted\nfirst\nsecond\nthird\nfourth\n"
    notes = gateway.working_notes()
    assert notes["findings"][0]["note_id"] == "n1"
    assert notes["findings"][0]["evidence"][0]["start_line"] == 3
    assert restore(gateway, tracked).working_notes() == notes
    sources["src.py"] = b"changed\n"
    cleared = gateway.record_working_notes_update(
        [note_call("clear", {"findings": [], "remove_note_ids": [], "open_question": None})],
        turn_id="clear",
    )
    assert cleared["retained_note_ids"] == []
    # Restoring the old source later must not resurrect a note already expired
    # at a durable update boundary.
    sources["src.py"] = b"first\nsecond\nthird\nfourth\n"
    assert restore(gateway, tracked).working_notes()["findings"] == []


def test_legacy_note_journal_is_projected_without_rewriting_it(source_gateway):
    gateway, _, tracked = source_gateway
    read = observe(gateway, "src.py", 1, 4)
    evidence = [{
        "kind": "source", "path": "src.py", "start_line": 1, "end_line": 1,
        "file_hash": read.output["spans"][0]["file_hash"],
    }]
    for index in (1, 2):
        gateway.journal.append("working_notes_updated", {
            "turn_id": f"legacy{index}", "update_valid": True, "diagnostics": [],
            "open_question": None, "findings": [{
                "finding_id": "sha256:legacy-evidence-key", "statement": f"Legacy fact {index}",
                "evidence": evidence, "author": "model_public_observation", "model_authored": True,
            }],
        })
    before = gateway.journal.path.read_bytes()
    findings = restore(gateway, tracked).working_notes()["findings"]
    assert len(findings) == 1
    assert findings[0]["note_id"] == "n1"
    assert findings[0]["statement"] == "Legacy fact 2"
    assert gateway.journal.path.read_bytes() == before
