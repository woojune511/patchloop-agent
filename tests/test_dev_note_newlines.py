from __future__ import annotations

import pytest
from test_dev_context_v12 import note_call, observe, replacement, source_note
from test_dev_context_v12 import source_gateway as source_gateway

from patchloop.dev.contracts import DevToolResult
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes, sha256_json


def encoded_lines(lines: list[str], style: str) -> bytes:
    separators = {"lf": ("\n",), "crlf": ("\r\n",), "mixed": ("\r\n", "\n")}[style]
    return "".join(
        line + separators[index % len(separators)] for index, line in enumerate(lines)
    ).encode()


def add_note(gateway):
    observation = observe(gateway, "src.py", 1, 4)
    receipt = gateway.record_working_notes_update(
        [note_call("note", source_note("The stable declaration is observed.", 2, 2))],
        turn_id="note",
    )["receipt"]
    assert observation.status == "succeeded"
    assert receipt["findings"][0]["status"] == "created"
    assert receipt["note_ids_after_update"] == ["n1"]
    return receipt


def restart(gateway, tracked):
    restored = DevToolGateway(
        workspace=gateway.workspace, public_task=gateway.public_task, sandbox=None,
        journal=gateway.journal, limits=gateway.limits,
    )
    restored._tracked_path = tracked
    return restored


def bind_synthetic_mutation_lifecycle(gateway, action_id="mutation"):
    """Exercise the durable lifecycle payload without executing a task or mutation."""
    state = gateway._refreshed_working_notes_state(action_id=action_id)
    result = DevToolResult(
        action_id=action_id, input_hash=sha256_json(action_id),
        tool="replace_text", status="succeeded", output={"changed_files": ["src.py"]},
        workspace_diff_hash=gateway.current_diff_hash,
    )
    gateway.journal.append("action_finished", {
        "result": result.model_dump(mode="json"), "working_notes_state": state,
    })
    gateway._restore_working_notes_state(state)
    return state


@pytest.mark.parametrize("style", ["lf", "crlf", "mixed"])
@pytest.mark.parametrize("read_only", [False, True])
def test_unchanged_public_note_survives_projection_and_hydration(
    source_gateway, style, read_only,
):
    gateway, sources, tracked = source_gateway
    raw = encoded_lines(["header = 0", "stable = 1", "other = 2", "tail = 3"], style)
    sources["src.py"] = raw
    if read_only:
        gateway.public_task.constraints.allowed_paths = []
    add_note(gateway)

    gateway.prepare_context_projection()
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == ["n1"]
    assert notes["findings"][0]["status"] == "current"
    assert notes["findings"][0]["evidence"][0]["file_hash"] == sha256_bytes(raw)
    assert notes["last_source_lifecycle"] is None

    before = gateway.journal.path.read_bytes()
    assert restart(gateway, tracked).working_notes() == notes
    assert gateway.journal.path.read_bytes() == before
    assert sources["src.py"] == raw


@pytest.mark.parametrize("style", ["lf", "crlf", "mixed"])
def test_unique_unchanged_note_body_rebinds_across_source_line_endings(source_gateway, style):
    gateway, sources, tracked = source_gateway
    lines = ["header = 0", "stable = 1", "other = 2", "tail = 3"]
    sources["src.py"] = encoded_lines(lines, "lf")
    add_note(gateway)
    sources["src.py"] = encoded_lines(["inserted = 4", *lines], style)

    bind_synthetic_mutation_lifecycle(gateway)
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == ["n1"]
    citation = notes["findings"][0]["evidence"][0]
    assert (citation["start_line"], citation["end_line"]) == (3, 3)
    assert citation["file_hash"] == sha256_bytes(sources["src.py"])
    assert notes["last_source_lifecycle"] == {
        "trigger_action_id": "mutation", "rebound_note_ids": ["n1"], "expired_notes": [],
    }
    before = gateway.journal.path.read_bytes()
    assert restart(gateway, tracked).working_notes() == notes
    assert gateway.journal.path.read_bytes() == before


@pytest.mark.parametrize("style", ["lf", "crlf", "mixed"])
@pytest.mark.parametrize("cause", ["source_changed", "source_ambiguous"])
def test_changed_or_ambiguous_note_expiry_is_durable_without_resurrection(
    source_gateway, style, cause,
):
    gateway, sources, tracked = source_gateway
    lines = ["header = 0", "stable = 1", "other = 2", "tail = 3"]
    original = encoded_lines(lines, "lf")
    sources["src.py"] = original
    add_note(gateway)
    changed = (
        ["header = 0", "stable = 9", "other = 2", "tail = 3"]
        if cause == "source_changed" else [*lines, "stable = 1"]
    )
    sources["src.py"] = encoded_lines(changed, style)

    bind_synthetic_mutation_lifecycle(gateway)
    notes = gateway.working_notes()
    assert notes["available_note_ids"] == []
    assert notes["last_source_lifecycle"] == {
        "trigger_action_id": "mutation", "rebound_note_ids": [],
        "expired_notes": [{"note_id": "n1", "reason": cause}],
    }
    # The durable snapshot, not the final filesystem text, determines prior expiry.
    sources["src.py"] = original
    before = gateway.journal.path.read_bytes()
    assert gateway.working_notes() == notes
    assert restart(gateway, tracked).working_notes() == notes
    assert gateway.journal.path.read_bytes() == before


def test_mixed_source_observation_does_not_relax_mutation_newline_admission(source_gateway):
    gateway, sources, _ = source_gateway
    raw = encoded_lines(["header = 0", "stable = 1", "other = 2", "tail = 3"], "mixed")
    sources["src.py"] = raw
    observe(gateway, "src.py", 1, 4)
    with pytest.raises(ContractError, match="replace_text refuses mixed newline styles"):
        gateway._validate_replacement_intent(replacement("stable = 1", "stable = 9"))
    assert sources["src.py"] == raw
    assert gateway.accepted_mutations == 0
