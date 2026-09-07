"""Current permission and note feedback without new admission or memory rules."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from native_history_support import input_context, start_turn
from test_dev_context_v12 import note_call
from test_dev_conversation_v23 import _output, _span
from test_dev_feedback_integration_v18 import _context, _input, _outputs
from test_dev_note_temporal_v18 import _update
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import DEV_RUN_SCHEMA, dev_tool_surface_hash
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.native_sources import reference_native_sources
from patchloop.dev.tools import DevToolGateway
from patchloop.util import canonical_json


@pytest.mark.parametrize("native", [False, True])
@pytest.mark.parametrize("path,allowed,forbidden,permission", [
    ("src.py", ["src.py"], [], "allowed"),
    ("helper.py", ["src.py"], [], "read_only"),
    ("src/deep/code.py", ["src/*.py"], [], "allowed"),
    ("src/code.py", ["src/**"], ["src/code.py"], "read_only"),
    ("src/test_code.py", ["src/**"], ["**/test_*.py"], "read_only"),
    ("Src.py", ["src.py"], [], "read_only"),
    ("src.py", [], [], "read_only"),
])
def test_source_permission_is_the_existing_gateway_rule(
    native, path, allowed, forbidden, permission,
):
    span = {**_span("PUBLIC_SOURCE"), "path": path, "unused_metadata": "DO_NOT_PROJECT"}
    state = {
        "public_task": {"constraints": {"allowed_paths": allowed, "forbidden_paths": forbidden}},
        "source_spans": [span],
        "observed_source_index": {"entries": [{
            "path": path, "file_hash": span["file_hash"], "start_line": 1,
            "kind": "def", "name": "public_function",
        }]},
        "available_tool_names": ["read_file", "search_files", "stop_task"],
    }
    history = [_output("read", [span])] if native else []
    before = copy.deepcopy((state, history))
    projected = compact_model_state(reference_native_sources(state, history), history)
    group, = projected["current_sources"]
    constraints = SimpleNamespace(allowed_paths=allowed, forbidden_paths=forbidden)
    gateway = SimpleNamespace(public_task=SimpleNamespace(constraints=constraints))
    assert DevToolGateway._path_allowed(gateway, path) == (permission == "allowed")
    assert group["edit_permission"] == permission
    assert group["path"] == path and group["file_hash"] == span["file_hash"]
    assert bool(group["content_delivery"]) is native
    assert projected["available_tool_names"] == state["available_tool_names"]
    assert "DO_NOT_PROJECT" not in canonical_json(projected)
    assert (state, history) == before


def test_header_only_source_has_permission_without_inventing_a_body():
    state = {"public_task": {"constraints": {"allowed_paths": ["src.py"], "forbidden_paths": []}},
             "observed_source_index": {"entries": [{"path": "src.py", "file_hash": "hash",
                 "start_line": 10, "kind": "def", "name": "partial_header"}]}}
    group, = compact_model_state(state, [])["current_sources"]
    assert group["edit_permission"] == "allowed"
    assert group["content_delivery"] == {} and "inline_spans" not in group
    del state["public_task"]
    assert "edit_permission" not in compact_model_state(state, [])["current_sources"][0]


@pytest.mark.parametrize("mismatch", [None, "missing", "call_id", "turn_id", "diff_hash", "status"])
def test_old_receipt_is_referenced_only_after_exact_native_delivery(mismatch):
    receipt = {"turn_id": "old-turn", "action_id": "old-action", "status": "applied",
               "scope": "before_tool_batch", "diff_hash_at_update": "old-diff",
               "note_ids_after_update": ["n1"], "findings": [{"message": "RECEIPT_BODY"}]}
    state = {"working_notes": {"findings": [], "available_note_ids": [],
              "last_update_result": receipt, "last_update_diagnostics": [],
              "last_source_lifecycle": {"trigger_action_id": "edit", "expired_notes": [
                  {"note_id": "n1", "reason": "source_changed"}]}}}
    delivered = copy.deepcopy(receipt)
    if mismatch in {"turn_id", "status"}:
        delivered[mismatch] = "different"
    if mismatch == "diff_hash":
        delivered["diff_hash_at_update"] = "different"
    history = [{"type": "function_call_output", "call_id": "old-action", "output": canonical_json({
        "action_id": "wrong" if mismatch == "call_id" else "old-action",
        "tool": "read_file", "status": "succeeded", "output": {},
        "memory_update_result": delivered,
    })}, _output("later-read", [])]
    if mismatch == "missing":
        history = history[1:]
    before = copy.deepcopy((state, history))
    notes = compact_model_state(state, history)["working_notes"]
    if mismatch is None:
        assert notes["last_update_result"] == {
            "turn_id": "old-turn", "action_id": "old-action",
            "delivery": "preceding_function_call_output",
        }
        assert "RECEIPT_BODY" not in canonical_json(notes)
        assert "last_update_diagnostics" not in notes
    else:
        assert notes == state["working_notes"]  # No dangling or wrong-result reference.
    assert notes["available_note_ids"] == []
    assert notes["last_source_lifecycle"] == state["working_notes"]["last_source_lifecycle"]
    assert (state, history) == before


def _batch(gateway, call, tmp_path, *, finish=True):
    latest = gateway.journal.latest_tool_batch_results()
    turn_id = f"turn-{call.action_id}"
    start_turn(gateway.journal, ArtifactStore(tmp_path / "artifacts"), turn_id,
               context=_context(gateway, latest), results=latest)
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [call.model_dump(mode="json")],
    })
    update = gateway.record_working_notes_update([call], turn_id=turn_id)
    result = gateway.execute(call)
    if finish:
        gateway.journal.append("tool_batch_finished", {
            "turn_id": turn_id, "action_ids": [call.action_id],
        })
    return update, result


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("crash_before_batch", [False, True])
def test_unannotated_mutation_delivers_expiry_once_and_preserves_prior_receipt(
    tmp_path, newline, crash_before_batch,
):
    gateway = _gateway(tmp_path, newline=newline)
    _read(gateway)
    update, observed = _batch(gateway, note_call("create-note", _update()), tmp_path)
    assert update["receipt"]["note_ids_after_update"] == ["n1"]
    previous = _input(gateway, [observed], tmp_path)
    edit = _mutation("expire", "stable = 'observed mechanism'", "stable = 'changed mechanism'")
    payload, result = _batch(gateway, edit, tmp_path, finish=not crash_before_batch)
    assert payload == {"status": "not_requested"} and result.status == "succeeded"
    if crash_before_batch:
        gateway = _restart(gateway)
        before = gateway.journal.path.read_bytes()
        assert gateway.execute(edit).replayed and gateway.accepted_mutations == 1
        assert gateway.journal.path.read_bytes() == before
        gateway.journal.append("tool_batch_finished", {
            "turn_id": "turn-expire", "action_ids": [edit.action_id],
        })
    canonical = _context(gateway, [result])
    raw_notes = json.loads(canonical)["working_notes"]
    assert raw_notes["last_update_result"] == update["receipt"]
    items = _input(gateway, [result], tmp_path, context=canonical)
    assert items[:len(previous)] == previous
    native = _outputs(items)[edit.action_id]
    assert "memory_update_result" not in native
    assert native["working_notes_after_batch"] == {
        "scope": "after_completed_tool_batch", "turn_id": "turn-expire",
        "diff_hash": gateway.current_diff_hash, "available_note_ids": [],
        "expired_notes": [{"note_id": "n1", "reason": "source_changed"}],
    }
    assert "working_notes_after_batch" not in result.model_dump()
    receipt_ref = input_context(items)["working_notes"]["last_update_result"]
    assert receipt_ref == {"turn_id": "turn-create-note", "action_id": "create-note",
                           "delivery": "preceding_function_call_output"}
    assert _outputs(items)["create-note"]["memory_update_result"] == update["receipt"]
    saved = gateway.journal.path.read_bytes(), (gateway.workspace / "src.py").read_bytes()
    gateway = _restart(gateway)
    assert _input(gateway, [result], tmp_path, context=canonical) == items
    assert (gateway.journal.path.read_bytes(), (gateway.workspace / "src.py").read_bytes()) == saved
    assert not any(e["event_type"] == "provider_call_started" for e in gateway.journal.events())

    # A useful later action cannot re-emit an old expiry or recreate the old ID.
    payload, later = _batch(gateway, note_call("later", None), tmp_path)
    final = _input(gateway, [later], tmp_path)
    assert final[:len(items)] == items
    assert "working_notes_after_batch" not in _outputs(final)["later"]
    assert input_context(final)["working_notes"]["last_update_result"] == receipt_ref
    assert input_context(final)["working_notes"]["available_note_ids"] == []


@pytest.mark.parametrize("rejected", [False, True])
def test_unannotated_nonexpiring_or_rolled_back_edit_does_not_invent_expiry(tmp_path, rejected):
    gateway = _gateway(tmp_path)
    _read(gateway)
    _batch(gateway, note_call("create-note", _update()), tmp_path)
    if rejected:
        gateway.public_task.constraints.max_diff_lines = 1
        edit = _mutation("edit", "stable = 'observed mechanism'", "stable = 'changed mechanism'")
    else:
        edit = _mutation("edit")
    _, result = _batch(gateway, edit, tmp_path)
    assert result.status == ("failed" if rejected else "succeeded")
    items = _input(gateway, [result], tmp_path)
    assert "working_notes_after_batch" not in _outputs(items)[edit.action_id]
    assert input_context(items)["working_notes"]["available_note_ids"] == ["n1"]


def test_presentation_contract_changes_identity_without_migrating_the_run_schema():
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    assert dev_tool_surface_hash() != (
        "sha256:85aa6d76fe3026f1c9a240f34521a55d7dd294affa577516cdf332cfbb66a2b5"
    )
