from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest
from test_dev_context_v12 import note_call, observe, source_note
from test_dev_context_v12 import source_gateway as source_gateway

from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway
from patchloop.util import sha256_bytes


class SimulatedCrash(BaseException):
    pass


def _gateway(tmp_path, *, newline="\n"):
    workspace = tmp_path / "work"
    workspace.mkdir()
    lines = ["header = 0", "other = 0", "stable = 'observed mechanism'"]
    lines.extend(f"padding_{number} = 0" for number in range(4, 50))
    lines.append("editable = 0")
    (workspace / "src.py").write_bytes((newline.join(lines) + newline).encode())
    for args in [
        ["init", "--quiet"],
        ["config", "core.autocrlf", "false"],
        ["add", "src.py"],
        ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"],
    ]:
        subprocess.run(["git", *args], cwd=workspace, check=True, capture_output=True)
    public = SimpleNamespace(
        constraints=SimpleNamespace(
            allowed_paths=["src.py"], forbidden_paths=[], max_diff_lines=50, max_changed_files=1,
        ),
        visible_checks=[],
    )
    return DevToolGateway(
        workspace=workspace, public_task=public, sandbox=None,
        journal=DevJournal(tmp_path / "state", "run_dev_notes"), limits=DevLimits(),
    )


def _restart(gateway):
    return DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task,
        sandbox=gateway.sandbox, journal=gateway.journal, limits=gateway.limits,
    )


def _read(gateway, action_id="read", start=1, end=60):
    call = RequestedTool(
        name="read_file", action_id=action_id,
        arguments={"path": "src.py", "start_line": start, "end_line": end},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Observe current public source.",
            evidence_goal="Find the exact current public implementation.",
        ),
    )
    assert gateway.execute(call).status == "succeeded"
    return call


def _note(gateway):
    call = RequestedTool(
        name="read_file", action_id="notes-next-read",
        arguments={"path": "src.py", "start_line": 1, "end_line": 3},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Retain the public mechanism.", evidence_goal="Check usage.",
            memory_update={
                "findings": [{
                    "note_id": None, "statement": "The stable declaration records the mechanism.",
                    "evidence": [{
                        "kind": "source", "path": "src.py", "start_line": 3, "end_line": 3,
                    }],
                }],
                "remove_note_ids": [], "open_question": None,
            },
        ),
    )
    payload = gateway.record_working_notes_update([call], turn_id="turn-note")
    assert payload["allocated_note_ids"] == ["n1"]


def _mutation(action_id, old="editable = 0", new="editable = 1"):
    return RequestedTool(
        name="replace_text", action_id=action_id,
        arguments={
            "path": "src.py", "old_text": old, "new_text": new, "occurrence": 1,
            "hypothesis": "Revise the public editable value.",
            "expected_behavior": "The editable value has the requested value.",
            "causal_revision": None,
        },
        turn_decision=PublicTurnDecision(mode="mutate", basis="Use the observed exact anchor."),
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_note_body_survives_two_real_mutations_and_restart(tmp_path, newline):
    gateway = _gateway(tmp_path, newline=newline)
    _read(gateway)
    _note(gateway)
    assert gateway.execute(_mutation("first")).status == "succeeded"
    assert all(span["start_line"] > 3 for span in gateway.spans.values())
    first_notes = gateway.working_notes()
    assert first_notes["findings"][0]["evidence"][0]["start_line"] == 3
    second = gateway.execute(_mutation("second", "editable = 1", "editable = 2"))
    assert second.status == "succeeded"
    notes = gateway.working_notes()
    assert [note["note_id"] for note in notes["findings"]] == ["n1"]
    assert notes["available_note_ids"] == ["n1"]
    assert notes["last_source_lifecycle"] == {
        "trigger_action_id": "second", "rebound_note_ids": ["n1"], "expired_notes": [],
    }
    assert notes["findings"][0]["evidence"][0]["file_hash"] == sha256_bytes(
        (gateway.workspace / "src.py").read_bytes()
    )
    before = gateway.journal.path.read_bytes()
    restored = _restart(gateway)
    assert restored.working_notes() == notes
    assert restored.accepted_mutations == 2
    assert gateway.journal.path.read_bytes() == before
    finished = [
        event["payload"] for event in gateway.journal.events()
        if event["event_type"] == "action_finished"
        and event["payload"]["result"]["tool"] == "replace_text"
    ]
    assert finished[-1]["working_notes_state"]["source_bodies_by_note_id"] == {
        "n1": ["stable = 'observed mechanism'"],
    }
    assert "source_bodies_by_note_id" not in json.dumps(notes)
    assert "working_notes_state" not in json.dumps(finished[-1]["result"])
    assert (gateway.workspace / "src.py").read_bytes().endswith(newline.encode())


@pytest.mark.parametrize("cause", ["source_changed", "source_ambiguous"])
def test_expired_note_cannot_resurrect_when_later_mutation_restores_source(tmp_path, cause):
    gateway = _gateway(tmp_path)
    _read(gateway)
    _note(gateway)
    old = "stable = 'observed mechanism'"
    new = "stable = 'new mechanism'" if cause == "source_changed" else f"{old}\n{old}"
    assert gateway.execute(_mutation("expire", old, new)).status == "succeeded"
    expired = gateway.working_notes()
    assert expired["findings"] == []
    assert expired["available_note_ids"] == []
    assert expired["last_update_result"]["note_ids_after_update"] == ["n1"]
    assert expired["last_update_result"]["scope"] == "before_tool_batch"
    assert expired["last_source_lifecycle"]["expired_notes"] == [
        {"note_id": "n1", "reason": cause},
    ]
    assert gateway.execute(_mutation("restore-source", new, old)).status == "succeeded"
    before = gateway.journal.path.read_bytes()
    assert gateway.working_notes()["findings"] == []
    assert _restart(gateway).working_notes() == gateway.working_notes()
    assert gateway.journal.path.read_bytes() == before


@pytest.mark.parametrize("boundary", ["before_finished", "after_finished"])
@pytest.mark.parametrize("changes_note", [False, True])
def test_mutation_lifecycle_is_atomic_with_durable_finished(
    tmp_path, monkeypatch, boundary, changes_note,
):
    gateway = _gateway(tmp_path)
    _read(gateway)
    _note(gateway)
    call = (
        _mutation("mutation", "stable = 'observed mechanism'", "stable = 'changed'")
        if changes_note else _mutation("mutation")
    )
    append = gateway.journal.append

    def crash(event_type, payload):
        selected = event_type == "action_finished" and payload["result"]["tool"] == "replace_text"
        if selected and boundary == "before_finished":
            raise SimulatedCrash()
        result = append(event_type, payload)
        if selected:
            raise SimulatedCrash()
        return result

    monkeypatch.setattr(gateway.journal, "append", crash)
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    current_bytes = (gateway.workspace / "src.py").read_bytes()
    monkeypatch.setattr(gateway.journal, "append", append)
    restored = _restart(gateway)
    before = gateway.journal.path.read_bytes()
    assert restored.execute(call).status == "succeeded"
    assert (gateway.workspace / "src.py").read_bytes() == current_bytes
    assert restored.accepted_mutations == 1
    assert bool(restored.working_notes()["findings"]) is not changes_note
    assert restored.working_notes()["last_source_lifecycle"]["trigger_action_id"] == "mutation"
    if boundary == "after_finished":
        assert gateway.journal.path.read_bytes() == before
    assert _restart(restored).working_notes() == restored.working_notes()
    finished = [
        event for event in gateway.journal.events()
        if event["event_type"] == "action_finished"
        and event["payload"]["result"]["tool"] == "replace_text"
    ]
    assert len(finished) == 1


def test_source_body_capture_preserves_blank_lines_union_and_bound():
    evidence = [{
        "kind": "source", "path": "src.py", "start_line": 1, "end_line": 3,
        "file_hash": "hash",
    }]
    spans = [
        {"path": "src.py", "file_hash": "hash", "start_line": 1, "content": "first\r\n"},
        {"path": "src.py", "file_hash": "hash", "start_line": 3, "content": "third"},
    ]
    capture = DevToolGateway._capture_working_note_source_bodies
    assert capture(evidence, spans) == ["first\n\nthird"]
    assert capture(evidence, spans[:1]) is None
    evidence[0]["end_line"] = 1
    spans[0]["content"] = "x" * 24_000
    assert capture(evidence, spans[:1]) == ["x" * 24_000]
    spans[0]["content"] += "x"
    assert capture(evidence, spans[:1]) is None


def test_overlapping_unchanged_multiline_matches_are_ambiguous(source_gateway):
    gateway, sources, _ = source_gateway
    sources["src.py"] = b"repeat\nrepeat\nend\n"
    observe(gateway, "src.py", 1, 3)
    gateway.record_working_notes_update(
        [note_call("note", source_note("The repeated public declaration is observed.", 1, 2))],
        turn_id="note",
    )
    sources["src.py"] = b"repeat\nrepeat\nrepeat\nend\n"
    notes = gateway.working_notes()
    assert notes["findings"] == []
    assert notes["last_source_lifecycle"]["expired_notes"] == [
        {"note_id": "n1", "reason": "source_ambiguous"},
    ]
