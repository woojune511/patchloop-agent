from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest
from test_dev_conversation_v23 import _output, _span

from diagnostics import current_source_view as prototype
from patchloop.dev.conversation import assemble_model_input
from patchloop.util import sha256_bytes


def frozen_request():
    state = {
        "public_task": {"description": "PUBLIC_TASK"},
        "current_sources": [], "current_diff": {"patch": "PUBLIC_DIFF"},
        "working_notes": {"findings": [], "available_note_ids": []},
    }
    initial = assemble_model_input(system_prompt="UNCHANGED_SYSTEM", state=state, history=[])
    history = [
        {"type": "reasoning", "id": "r1", "encrypted_content": "OPAQUE_ONE", "summary": []},
        {"type": "function_call", "call_id": "read", "name": "read_file",
         "arguments": '{"path":"src.py","start_line":1,"end_line":4}'},
        _output("read", [_span("selected one\nomitted two\nomitted three\nselected four")]),
    ]
    current = {**state, "current_sources": [{
        "path": "src.py", "file_hash": "raw-hash", "edit_permission": "read_only",
        "content_delivery": {"read": {"output.spans[0]": [[1, 1], [4, 4]]}},
        "headers": [{"kind": "def", "name": "header", "start_line": 1}],
        "inline_spans": [{"start_line": 8, "end_line": 9, "content": "inline\r\nbody",
                          "diagnostic_metadata": "preserved"}],
    }], "remaining_budget": {"model_calls": 12}, "protocol_correction": None}
    return {
        "model": "frozen-model", "reasoning": {"effort": "medium"}, "store": False,
        "max_output_tokens": 25000, "include": ["reasoning.encrypted_content"],
        "input": assemble_model_input(system_prompt="unused", state=current,
                                      history=history, previous_input=initial),
        "tools": [{"name": "second-tool", "parameters": {"z": 1, "a": 2}},
                  {"name": "first-tool", "parameters": {"b": 2, "a": 1}}],
    }


def latest(request):
    return json.loads(request["input"][-1]["content"])


def replace_latest(request, record):
    request["input"][-1]["content"] = prototype.wire(record).decode()


def test_only_selected_current_delivery_changes_and_native_prefix_stays_exact():
    original = frozen_request()
    before = prototype.wire(original)
    changed, metrics = prototype.inline_current_sources(original)
    old_record, new_record = latest(original), latest(changed)
    old_group = old_record["state"]["current_sources"][0]
    new_group = new_record["state"]["current_sources"][0]
    assert new_group["inline_spans"] == [*old_group["inline_spans"],
        {"start_line": 1, "end_line": 1, "content": "selected one"},
        {"start_line": 4, "end_line": 4, "content": "selected four"}]
    assert new_group["content_delivery"] == {}
    assert "omitted" not in prototype.wire(new_record).decode()
    assert prototype.wire(changed["input"][:-1]) == prototype.wire(original["input"][:-1])
    assert prototype.wire(changed["tools"]) == prototype.wire(original["tools"])
    new_record["state"]["current_sources"] = old_record["state"]["current_sources"]
    assert prototype.wire(new_record) == prototype.wire(old_record)
    reverted = copy.deepcopy(changed)
    reverted["input"][-1] = original["input"][-1]
    assert prototype.wire(reverted) == before == prototype.wire(original)
    assert metrics["selected_line_count"] == 4
    assert metrics["removed_current_reference_ranges"] == 2
    assert metrics["selected_ranges_equal"] is True
    assert metrics["prototype_request_bytes"] == len(prototype.wire(changed))
    assert metrics["provider_calls"] == metrics["input_count_calls"] == 0
    assert prototype.inline_current_sources(changed)[0] == changed


def test_exact_backward_alias_resolves_only_selected_postimage_range():
    request = frozen_request()
    alias = {
        "path": "src.py", "file_hash": "new-hash", "start_line": 10, "end_line": 13,
        "origin": "revalidated_after_mutation",
        "content_hash": sha256_bytes(b"selected one\nomitted two\nomitted three\nselected four"),
        "content_delivery": [{"action_id": "read", "field": "output.spans[0]",
                              "file_hash": "raw-hash", "start_line": 1, "end_line": 4,
                              "target_start_line": 10}],
    }
    request["input"][-1:-1] = [
        {"type": "reasoning", "id": "r2", "encrypted_content": "OPAQUE_TWO", "summary": []},
        _output("mutation", [alias], tool="replace_text", field="revalidated_spans"),
    ]
    record = latest(request)
    record["state"]["current_sources"] = [{
        "path": "src.py", "file_hash": "new-hash", "edit_permission": "allowed",
        "content_delivery": {"mutation": {"output.revalidated_spans[0]": [[13, 13]]}},
    }]
    replace_latest(request, record)
    changed, metrics = prototype.inline_current_sources(request)
    assert latest(changed)["state"]["current_sources"][0]["inline_spans"] == [{
        "start_line": 13, "end_line": 13, "content": "selected four",
    }]
    assert changed["input"][:-1] == request["input"][:-1]
    assert metrics["reasoning_item_count"] == 2 and metrics["selected_line_count"] == 1


@pytest.mark.parametrize("damage", [
    "missing_action", "wrong_field", "wrong_hash", "wrong_path", "out_of_range", "bool_range",
    "reversed_range", "empty_ranges", "invalid_inline", "inline_conflict", "history_conflict",
    "duplicate_group", "failed_result", "malformed_result", "malformed_group", "malformed_ref",
    "plaintext_reasoning", "missing_ciphertext", "old_state_only",
])
def test_invalid_or_missing_delivery_fails_closed_without_mutating_input(damage):
    request = frozen_request()
    record = latest(request)
    group = record["state"]["current_sources"][0]
    if damage == "missing_action":
        group["content_delivery"] = {"absent": {"output.spans[0]": [[1, 1]]}}
    elif damage == "wrong_field":
        group["content_delivery"] = {"read": {"output.spans[1]": [[1, 1]]}}
    elif damage in {"wrong_hash", "wrong_path"}:
        group["file_hash" if damage == "wrong_hash" else "path"] = "wrong"
    elif damage in {"out_of_range", "bool_range", "reversed_range", "empty_ranges"}:
        group["content_delivery"]["read"]["output.spans[0]"] = {
            "out_of_range": [[1, 5]], "bool_range": [[True, 1]],
            "reversed_range": [[4, 1]], "empty_ranges": [],
        }[damage]
    elif damage == "invalid_inline":
        group["inline_spans"][0]["end_line"] = 20
    elif damage == "inline_conflict":
        group["inline_spans"].append({"start_line": 1, "end_line": 1, "content": "conflict"})
    elif damage == "history_conflict":
        request["input"][-1:-1] = [_output("another", [_span("conflict")])]
    elif damage == "duplicate_group":
        record["state"]["current_sources"].append(copy.deepcopy(group))
    elif damage in {"failed_result", "malformed_result"}:
        output = json.loads(request["input"][5]["output"])
        output["status"] = "failed"
        request["input"][5]["output"] = (
            "bad JSON" if damage == "malformed_result" else prototype.wire(output).decode()
        )
    elif damage == "malformed_group":
        record["state"]["current_sources"] = [None]
    elif damage == "malformed_ref":
        group["content_delivery"] = {"read": []}
    elif damage == "plaintext_reasoning":
        request["input"][3]["text"] = "PLAINTEXT_REASONING_SENTINEL"
    elif damage == "missing_ciphertext":
        del request["input"][3]["encrypted_content"]
    replace_latest(request, record)
    if damage == "old_state_only":
        request["input"].pop()
    before = prototype.wire(request)
    with pytest.raises(ValueError):
        prototype.inline_current_sources(request)
    assert prototype.wire(request) == before


def test_adjacent_selected_ranges_merge_but_not_unselected_native_lines():
    request = frozen_request()
    record = latest(request)
    group = record["state"]["current_sources"][0]
    group["content_delivery"]["read"]["output.spans[0]"] = [[1, 1], [2, 2], [4, 4]]
    replace_latest(request, record)
    changed, metrics = prototype.inline_current_sources(request)
    spans = latest(changed)["state"]["current_sources"][0]["inline_spans"]
    assert spans[1:] == [
        {"start_line": 1, "end_line": 2, "content": "selected one\nomitted two"},
        {"start_line": 4, "end_line": 4, "content": "selected four"},
    ]
    assert metrics["selected_line_count"] == 5


def test_prepare_validate_are_provider_free_read_only_and_hash_bound(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("prototype must not start a process, provider, or task")

    monkeypatch.setattr(subprocess, "run", forbidden)
    source = tmp_path / "original.json"
    body = prototype.wire(frozen_request())
    source.write_bytes(body)
    root = tmp_path / "prepared"
    manifest = prototype.prepare(source, sha256_bytes(body), root)
    prepared = {p.name: p.read_bytes() for p in root.iterdir()}
    metrics = prototype.validate(root)
    assert metrics["selected_ranges_equal"] is True
    assert source.read_bytes() == body
    assert {p.name: p.read_bytes() for p in root.iterdir()} == prepared
    assert sha256_bytes(prepared["request.json"]) == manifest["prototype_hash"]
    with pytest.raises(ValueError, match="fresh external"):
        prototype.prepare(source, sha256_bytes(body), root)
    with pytest.raises(ValueError, match="input hash"):
        prototype.prepare(source, "sha256:wrong", tmp_path / "uncreated")
    assert not (tmp_path / "uncreated").exists()
    (root / "request.json").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="prototype request changed"):
        prototype.validate(root)


@pytest.mark.parametrize("change", ["input", "manifest"])
def test_validation_rejects_changed_source_or_metrics(tmp_path, change):
    source = tmp_path / "original.json"
    body = prototype.wire(frozen_request())
    source.write_bytes(body)
    root = tmp_path / "prepared"
    prototype.prepare(source, sha256_bytes(body), root)
    if change == "input":
        source.write_bytes(body + b" ")
    else:
        manifest = json.loads((root / "manifest.json").read_bytes())
        manifest["selected_line_count"] += 1
        (root / "manifest.json").write_bytes(prototype.wire(manifest))
    with pytest.raises(ValueError, match="changed"):
        prototype.validate(root)


def test_cli_exposes_only_prepare_validate(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["current_source_view", "--help"])
    with pytest.raises(SystemExit) as result:
        prototype.main()
    assert result.value.code == 0
    help_text = capsys.readouterr().out
    assert "{prepare,validate}" in help_text
    assert "collect" not in help_text and "credential" not in help_text
