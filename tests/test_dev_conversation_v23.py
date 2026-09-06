from __future__ import annotations

import copy
import json

import pytest
from test_dev_context_v12 import source_gateway as source_gateway

from patchloop.dev.conversation import (
    assemble_model_input,
    history_metadata,
    reconstruct_state,
    validate_model_input,
)
from patchloop.dev.native_sources import reference_native_sources
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json


def _span(content="one\ntwo", *, start=1, file_hash="raw-hash", path="src.py"):
    return {"path": path, "file_hash": file_hash, "start_line": start,
            "end_line": start + len(content.replace("\r\n", "\n").split("\n")) - 1,
            "content": content}


def _output(action_id, spans, *, tool="read_file", field="spans", status="succeeded"):
    return {"type": "function_call_output", "call_id": action_id, "output": canonical_json({
        "action_id": action_id, "tool": tool, "status": status,
        "output": {field: spans[0] if field == "mutation_evidence" else spans},
    })}


def _initial(state):
    return assemble_model_input(system_prompt="Fixed instructions", state=state, history=[])


def test_state_changes_append_after_native_exchange_and_reconstruct_exactly():
    initial_state = {
        "workflow_gate": "needs_mutation", "remaining_budget": {"model_calls": 40},
        "public_task": {"description": "STABLE_PUBLIC_TASK"},
        "working_notes": {"findings": [], "open_question": "Question?"},
        "protocol_correction": None, "remove_later": "obsolete",
    }
    initial = _initial(initial_state)
    before = copy.deepcopy(initial)
    exchange = [
        {"type": "reasoning", "id": "rs", "encrypted_content": "opaque", "summary": []},
        {"type": "function_call", "call_id": "a", "name": "read_file", "arguments": "{}"},
        _output("a", [_span()]),
    ]
    changed = {**initial_state, "remaining_budget": {"model_calls": 39},
               "protocol_correction": {"code": "invalid_batch"}}
    del changed["remove_later"]
    next_input = assemble_model_input(system_prompt="Fixed instructions", state=changed,
                                      history=exchange, previous_input=initial)
    assert next_input[:len(initial)] == initial == before
    assert next_input[len(initial):-1] == exchange
    view = json.loads(next_input[-1]["content"])
    assert set(view) == {"kind", "state"}
    assert view["kind"] == "harness_current_state"
    assert view["state"] == {k: v for k, v in changed.items() if k != "public_task"}
    assert reconstruct_state(next_input) == changed
    assert canonical_json(next_input).count("STABLE_PUBLIC_TASK") == 1
    assert sum(item.get("role") == "user" for item in next_input) == 1
    assert validate_model_input(next_input, history_metadata(next_input)) == next_input
    cleared = {**changed, "protocol_correction": None,
               "working_notes": {"findings": [], "open_question": None}}
    final = assemble_model_input(system_prompt="Fixed instructions", state=cleared,
                                 history=[], previous_input=next_input)
    assert final[:len(next_input)] == next_input
    assert reconstruct_state(final) == cleared
    assert history_metadata(final)["current_state_hash"] == sha256_json(cleared)
    assert history_metadata(final)["state_update_count"] == 2
    # No-op construction adds neither another state nor a fake tool/user message.
    assert assemble_model_input(system_prompt="Fixed instructions", state=cleared,
                                history=[], previous_input=final) == final


def test_reasoning_only_correction_keeps_every_previous_item_and_clears_on_next_decision():
    initial = _initial({"protocol_correction": None, "remaining_budget": {"model_calls": 4}})
    reasoning = {"type": "reasoning", "id": "incomplete", "encrypted_content": "opaque",
                 "summary": [], "status": "incomplete"}
    corrected = assemble_model_input(
        system_prompt="Fixed instructions", previous_input=initial, history=[reasoning],
        state={"protocol_correction": {"code": "incomplete_response",
                                      "message": "max_output_tokens"},
               "remaining_budget": {"model_calls": 3}},
    )
    completed = assemble_model_input(
        system_prompt="Fixed instructions", previous_input=corrected, history=[],
        state={"protocol_correction": None, "remaining_budget": {"model_calls": 2}},
    )
    assert completed[:len(corrected)] == corrected
    assert [item for item in completed if item.get("type") == "reasoning"] == [reasoning]
    assert reconstruct_state(completed)["protocol_correction"] is None
    assert sum(item.get("role") == "user" for item in completed) == 1


@pytest.mark.parametrize("damage", ["kind", "shape", "task", "content", "metadata"])
def test_invalid_current_state_or_metadata_fails_closed(damage):
    items = assemble_model_input(system_prompt="Fixed instructions", state={"value": 2},
                                 history=[], previous_input=_initial({"value": 1}))
    metadata = history_metadata(items)
    view = json.loads(items[-1]["content"])
    if damage == "kind":
        view["kind"] = "harness_state_delta"
    elif damage == "shape":
        view["state"] = []
    elif damage == "task":
        view["state"]["public_task"] = {}
    elif damage == "content":
        view["state"]["value"] = 3
    else:
        metadata["current_state_hash"] = "wrong"
    items[-1]["content"] = canonical_json(view)
    with pytest.raises(RecoveryError):
        validate_model_input(items, metadata)


def test_complete_state_reconstruction_matches_independent_json_oracle():
    values = [None, False, True, 0, 1, "", "text", [], [1], [1, 2, 3], {},
              {"value": True}, {"value": 1}, {"value": None, "delete": [1, 2]},
              [{"x": 1}, {"y": [False, "text"]}],
              [{"y": []}, {"x": {"z": "new"}}, 3]]
    for before in values:
        initial = _initial({"state": before, "stable": "keep"})
        for after in values:
            expected = {"state": after, "stable": "keep"}
            items = assemble_model_input(system_prompt="Fixed instructions", state=expected,
                                         history=[], previous_input=initial)
            assert items[:len(initial)] == initial
            # JSON identity distinguishes True from 1, including inside containers.
            assert canonical_json(reconstruct_state(items)) == canonical_json(expected)


def test_equivalent_hydrated_nested_objects_emit_identical_views():
    initial = _initial({"workflow_gate": "needs_mutation", "remaining_budget": {"model": 4},
                        "working_notes": {"findings": []}})
    current = {"workflow_gate": "needs_visible_checks", "remaining_budget": {"model": 3},
               "working_notes": {"findings": [{"statement": "Source finding", "note_id": "n1"}]}}
    hydrated = {**current, "working_notes": {"findings": [
        {"note_id": "n1", "statement": "Source finding"},
    ]}}
    assert assemble_model_input(system_prompt="Fixed instructions", state=current, history=[],
                                previous_input=initial) == assemble_model_input(
        system_prompt="Fixed instructions", state=hydrated, history=[], previous_input=initial,
    )


def test_exact_adjacent_union_uses_native_references_and_preserves_originals():
    span = _span("one\ntwo\nthree\n")
    state = {"source_spans": [span], "mutation_readiness": {"state": "ready_to_attempt"},
             "working_notes": {"open_question": "Keep this interpretation"}}
    history = [_output("first", [_span("one\ntwo")]),
               _output("second", [_span("two\r\nthree\r\n", start=2)])]
    originals = copy.deepcopy((state, history))
    result = reference_native_sources(state, history)
    ref_span = result["source_spans"][0]
    assert "content" not in ref_span
    assert ref_span["content_delivery"] == [
        {"action_id": "first", "field": "output.spans[0]", "start_line": 1, "end_line": 2},
        {"action_id": "second", "field": "output.spans[0]", "start_line": 3, "end_line": 4},
    ]
    assert ref_span["file_hash"] == span["file_hash"]
    assert result["mutation_readiness"] == state["mutation_readiness"]
    assert result["working_notes"] == state["working_notes"]
    assert (state, history) == originals
    assert reference_native_sources(result, history) == result


@pytest.mark.parametrize("problem", ["gap", "stale", "path", "text", "conflict",
                                    "truncated", "probe", "failed", "mismatched_action"])
def test_nonidentical_or_unobserved_source_stays_inline(problem):
    target = _span("one\ntwo\nthree")
    seen = copy.deepcopy(target)
    history = []
    if problem == "gap":
        seen = _span("one")
        history.append(_output("gap-tail", [_span("three", start=3)]))
    elif problem == "stale":
        seen["file_hash"] = "old-hash"
    elif problem == "path":
        seen["path"] = "other.py"
    elif problem == "text":
        seen["content"] = "one\nWRONG\nthree"
    elif problem == "conflict":
        history.append(_output("conflicting", [_span("WRONG", start=2)]))
    elif problem == "truncated":
        seen["content"] = "one"
    item = _output("seen", [seen], tool="run_probe" if problem == "probe" else "read_file",
                   status="failed" if problem == "failed" else "succeeded")
    if problem == "mismatched_action":
        item["call_id"] = "other-action"
    history.append(item)
    state = {"source_spans": [target]}
    assert reference_native_sources(state, history) == state


@pytest.mark.parametrize("field", ["mutation_evidence", "revalidated_spans"])
def test_accepted_post_image_can_supply_current_source_without_promoting_old_hash(field):
    old = _span("same", file_hash="before")
    current = _span("same", file_hash="after")
    history = [_output("read", [old]), _output("edit", [current], tool="replace_text", field=field)]
    result = reference_native_sources({"source_spans": [current]}, history)
    assert result["source_spans"][0]["content_delivery"][0]["action_id"] == "edit"
    assert result["source_spans"][0]["file_hash"] == "after"


def test_reference_list_is_bounded_without_clipping_the_original_body():
    history = [_output(f"r{i}", [_span(str(i), start=i + 1)]) for i in range(17)]
    state = {"source_spans": [_span("\n".join(str(i) for i in range(17)))]}
    assert reference_native_sources(state, history) == state


def test_large_source_is_not_duplicated_in_current_state_and_append_only_wire_is_smaller():
    span = _span("\n".join(f"observed_line_{i} = {'x' * 90}" for i in range(200)))
    base = {"public_task": {"description": "Stable task"}, "remaining_budget": {"model": 40},
            "source_spans": []}
    new = _initial(base)
    old_total = new_total = 0
    history = []
    for i in range(12):
        exchange = [_output(f"read-{i}", [span])]
        history.extend(exchange)
        state = {**base, "remaining_budget": {"model": 39 - i}, "source_spans": [span]}
        compact = reference_native_sources(state, history)
        next_input = assemble_model_input(system_prompt="Fixed instructions", state=compact,
                                          history=exchange, previous_input=new)
        assert next_input[:len(new)] == new
        assert "content" not in reconstruct_state(next_input)["source_spans"][0]
        old_total += len(canonical_json(assemble_model_input(
            system_prompt="Fixed instructions", state=state, history=history,
        )))
        new_total += len(canonical_json(next_input))
        new = next_input
    assert new_total < old_total  # Serialized bytes, not a claim about billed tokens or behavior.
    assert sum(item.get("type") == "function_call_output" for item in new) == 12


def test_read_range_limit_is_explained_without_changing_argument_names_or_tool_order():
    schemas = dev_tool_schemas(finish_enabled=False)
    read = next(tool for tool in schemas if tool["name"] == "read_file")
    assert "inclusive" in read["description"]
    assert "end_line - start_line + 1" in read["description"]
    assert "between 1 and 400" in read["description"]
    assert set(read["parameters"]["properties"]) == {
        "path", "start_line", "end_line", "turn_decision",
    }


def test_advertised_read_limit_matches_existing_gateway_boundary(source_gateway):
    gateway, sources, _ = source_gateway
    sources["src.py"] = ("line\n" * 500).encode()
    assert gateway._read_file("src.py", 1, 400)["spans"][0]["end_line"] == 400
    assert gateway._read_file("src.py", 2, 401)["spans"][0]["end_line"] == 401
    with pytest.raises(ContractError, match="1-400 line inclusive range"):
        gateway._read_file("src.py", 1, 401)
