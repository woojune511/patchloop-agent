from __future__ import annotations

import copy
import hashlib
import json

import pytest
from native_history_support import input_context
from test_dev_check_identity_v19 import _result
from test_dev_context_v12 import note_call, source_note
from test_dev_feedback_integration_v18 import _completed_batch, _context, _input
from test_dev_notes_lifecycle_v15 import SimulatedCrash, _gateway, _mutation, _read, _restart

from patchloop.dev.contracts import DEV_RUN_SCHEMA, DevLimits, dev_tool_surface_hash
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.tools import ALL_DEV_TOOLS, dev_tool_schemas
from patchloop.dev.working_notes import check_note_result, memory_update_schema


def _check(action_id, diff, *, passed=False, exception="AttributeError", check_id="traversal"):
    result = _result(action_id, check_id, diff, passed=passed)
    if not passed:
        result.output["public_check_failure"] = {"exception_type": exception}
    return result


def _annotation(*action_ids, statement="The visible failure has moved to an assertion."):
    update = source_note(statement)
    update["findings"][0]["evidence"] = [
        {"kind": "tool_result", "action_id": action_id} for action_id in action_ids
    ]
    return update


def _append(gateway, result):
    gateway.journal.append("action_finished", {"result": result.model_dump(mode="json")})
    gateway._remember_check(result.output)


def _assert_replayed_input(gateway, results, tmp_path, original):
    restarted = _restart(gateway)
    restored = _input(restarted, results, tmp_path)
    assert [restored[0], *restored[2:]] == [original[0], *original[2:]]
    assert input_context(restored) == input_context(original)
    # Hydration may reorder nested dictionaries; the saved context replays byte-exactly.
    assert _input(restarted, results, tmp_path, context=_context(gateway, results)) == original


@pytest.mark.parametrize("passed,exception", [
    (True, None), (False, "AttributeError"), (False, None),
])
def test_check_citation_binds_actual_result_without_judging_note_prose(tmp_path, passed, exception):
    gateway = _gateway(tmp_path)
    check = _check("actual-check", gateway.current_diff_hash, passed=passed, exception=exception)
    _append(gateway, check)
    call = note_call("annotated-read", _annotation(check.action_id))
    payload, results = _completed_batch(gateway, [call], "note-turn")
    assert payload["receipt"]["status"] == "applied"
    assert results[0].status == "succeeded"
    stored = payload["findings"][0]["evidence"][0]["check_result"]
    assert stored == {"check_id": "traversal", "passed": passed, "exception_type": exception}
    projected = gateway.working_notes()["findings"][0]
    assert projected["statement"] == call.turn_decision.memory_update["findings"][0]["statement"]
    assert projected["interpretation_status"] == "model_authored_unverified"
    assert projected["evidence"][0]["check_result"] == {**stored, "currency": "current"}
    before = gateway.journal.path.read_bytes()
    assert _restart(gateway).working_notes() == gateway.working_notes()
    assert gateway.journal.path.read_bytes() == before


def test_row27_cross_diff_false_summary_keeps_each_cited_failure_beside_the_note(tmp_path):
    gateway = _gateway(tmp_path)
    old = _check("older-assertion", "previous-diff", exception="AssertionError")
    new = _check("current-attribute", gateway.current_diff_hash)
    _append(gateway, old)
    _append(gateway, new)
    # Reproduce the public annotation mistake without correcting or rejecting its prose.
    calls = [
        note_call("owner", _annotation(old.action_id, new.action_id)),
        note_call("ignored", _annotation(new.action_id, statement="Ignore this extra update.")),
    ]
    payload, results = _completed_batch(gateway, calls, "parallel-notes")
    assert payload["receipt"]["status"] == "partially_applied"
    items = _input(gateway, results, tmp_path)
    public = input_context(items)
    finding = public["working_notes"]["findings"][0]
    assert finding["statement"] == "The visible failure has moved to an assertion."
    assert [ref["check_result"] for ref in finding["evidence"]] == [
        {"check_id": "traversal", "passed": False, "exception_type": "AssertionError",
         "currency": "historical"},
        {"check_id": "traversal", "passed": False, "exception_type": "AttributeError",
         "currency": "current"},
    ]
    outputs = [json.loads(item["output"]) for item in items
               if item.get("type") == "function_call_output"]
    assert sum("memory_update_result" in result for result in outputs) == 1
    assert "stdout" not in json.dumps(finding)
    assert "stderr" not in json.dumps(finding)
    before = gateway.journal.path.read_bytes()
    _assert_replayed_input(gateway, results, tmp_path, items)
    assert gateway.journal.path.read_bytes() == before


def test_pass_citation_becomes_historical_after_mutation_without_rewriting_verdict(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    check = _check("passed-regression", gateway.current_diff_hash, passed=True,
                   check_id="regression")
    _append(gateway, check)
    payload, _ = _completed_batch(
        gateway, [note_call("record-pass", _annotation(check.action_id))], "record-pass",
    )
    stored = copy.deepcopy(payload)
    _, results = _completed_batch(gateway, [_mutation("change")], "change")
    items = _input(gateway, results, tmp_path)
    evidence = input_context(items)["working_notes"]["findings"][0]["evidence"][0]
    assert evidence["check_result"] == {
        "check_id": "regression", "passed": True, "exception_type": None,
        "currency": "historical",
    }
    assert evidence["diff_hash"] != gateway.current_diff_hash
    assert payload == stored
    _assert_replayed_input(gateway, results, tmp_path, items)


def test_crash_after_durable_note_restores_label_without_duplicate(tmp_path, monkeypatch):
    gateway = _gateway(tmp_path)
    check = _check("before-crash", gateway.current_diff_hash)
    _append(gateway, check)
    call = note_call("note-before-action", _annotation(check.action_id))
    append = gateway.journal.append

    def crash(event_type, payload):
        result = append(event_type, payload)
        if event_type == "working_notes_updated":
            raise SimulatedCrash()
        return result

    monkeypatch.setattr(gateway.journal, "append", crash)
    with pytest.raises(SimulatedCrash):
        gateway.record_working_notes_update([call], turn_id="crash")
    restored = _restart(gateway)
    before = restored.journal.path.read_bytes()
    payload = restored.record_working_notes_update([call], turn_id="crash")
    label = payload["findings"][0]["evidence"][0]["check_result"]
    assert label["exception_type"] == "AttributeError"
    assert restored.journal.path.read_bytes() == before
    assert len(restored.working_notes()["findings"]) == 1


@pytest.mark.parametrize("change", [
    {"tool": "read_file"}, {"tool": "run_probe"}, {"status": "failed"},
    {"output": {}}, {"output": {"check_id": "public", "passed": "false"}},
])
def test_noncheck_or_unexecuted_action_has_no_invented_check_verdict(change):
    result = _check("result", "current").model_dump(mode="json")
    result.update(change)
    assert check_note_result(result) is None


def test_result_label_does_not_copy_traceback_paths_private_fields_or_reasoning():
    result = _check("result", "current").model_dump(mode="json")
    output = result["output"]
    output.update({
        "stdout": "PRIVATE_SPEC_SENTINEL", "stderr": ".patchloop-hidden/HIDDEN_PATH_SENTINEL",
        "reference_patch": "REFERENCE_PATCH_SENTINEL", "reasoning": "REASONING_SENTINEL",
    })
    output["public_check_failure"].update({
        "message": "PRIVATE_MESSAGE_SENTINEL", "public_location": {"path": "PRIVATE_PATH_SENTINEL"},
    })
    label = check_note_result(result)
    assert label == {"check_id": "traversal", "passed": False, "exception_type": "AttributeError"}
    assert "SENTINEL" not in json.dumps(label)
    output["public_check_failure"]["exception_type"] = "E" * 300
    assert len(check_note_result(result)["exception_type"]) == 200
    output["passed"] = True
    assert check_note_result(result)["exception_type"] is None


def test_missing_diff_is_not_labeled_a_current_check(tmp_path):
    gateway = _gateway(tmp_path)
    check = _check("without-diff", None)
    _append(gateway, check)
    _completed_batch(gateway, [note_call("note", _annotation(check.action_id))], "note")
    evidence = gateway.working_notes()["findings"][0]["evidence"][0]
    assert evidence["check_result"]["currency"] == "unknown"


def test_probe_description_exposes_existing_capability_without_changing_wire_shape():
    schemas = dev_tool_schemas(finish_enabled=True, allowed_tools=ALL_DEV_TOOLS)
    description = next(item["description"] for item in schemas if item["name"] == "run_probe")
    for phrase in ("accepted edits", "importable", "read-only", "/workspace", "/tmp",
                   "base Python", "no network or dependency installation", "diagnostics"):
        assert phrase in description
    assert "run_probe" not in {item["name"] for item in dev_tool_schemas(finish_enabled=True)}

    def structure(value):
        if isinstance(value, dict):
            return {key: structure(item) for key, item in value.items() if key != "description"}
        if isinstance(value, list):
            return [structure(item) for item in value]
        return value

    # V29 removes stop's source IDs; probe properties/limits and tool order stay unchanged.
    encoded = json.dumps(structure(schemas), separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(encoded).hexdigest() == (
        "918f1c2a1aa600f1c2eef71dde64b3542d35ea9a34a08a70c494130776891710"
    )
    assert dev_tool_surface_hash() != (
        "sha256:d69d9d4f71a4ed6517e0ae077d2df1fe934f6498abcacf104eed0b9b0fc717a8"
    )
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (40, 100, 4, 1800)


def test_guidance_prioritizes_reusable_facts_without_growing_the_system_prompt():
    assert len(DEV_SYSTEM_PROMPT) <= 8007  # v19 length; replace guidance, do not stack warnings.
    assert "current_public_failure labels the latest failure's diff currency" in DEV_SYSTEM_PROMPT
    assert "note_id=null creates a distinct fact" in DEV_SYSTEM_PROMPT
    assert "experiment on the current candidate" in DEV_SYSTEM_PROMPT
    assert "not confirmation of the note's prose" in DEV_SYSTEM_PROMPT
    description = memory_update_schema()["description"]
    assert "refine the same fact" in description
    assert "Keep distinct facts in separate notes" in description
