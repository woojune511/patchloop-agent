from __future__ import annotations

import copy
import json
import socket
import subprocess
import sys

import pytest

from diagnostics import completion_signal_view as prototype
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.util import sha256_bytes


def frozen_request(statuses=("NOT_RUN", "NOT_RUN")):
    current = "sha256:current"
    pending = [name for name, status in zip(("contract", "regression"), statuses, strict=True)
               if status == "NOT_RUN"]
    tools = ["search_files", "read_file", "run_check", "stop_task", "run_probe"]
    if not pending:
        tools.append("finish_task")
    state = {
        "workflow_gate": "needs_visible_checks" if pending else "ready_to_submit",
        "completion_guidance": {
            "diff_hash": current, "submission_ready": not pending,
            "next_action": ({"tool": "run_check", "check_id": pending[0]}
                            if pending else {"tool": "finish_task"}),
            "message": "Existing current-candidate guidance remains exact.",
        },
        "visible_check_status": [
            {"check_id": name, "diff_hash": current, "status": status}
            for name, status in zip(("contract", "regression"), statuses, strict=True)
        ],
        "remaining_visible_check_ids": pending,
        "remaining_budget": {"model_calls": 18, "tool_actions": 78, "accepted_mutations": 0},
        "action_horizon": {
            "completion_possible": True, "protected_completion_possible": True,
            "mutation_completion_horizon": {
                "minimum_calls": 4, "minimum_possible": False, "protected_calls": 6,
                "protected_possible": False, "recovery_warning": None,
            },
            "minimum_completion_calls": len(pending) + 1,
            "tools_closing_after_this_turn": [], "exploration_state": "open",
        },
        "current_diff": {"patch_hash": current, "patch": "PUBLIC_DIFF_현재"},
        "current_public_failure": None,
        "pending_recheck": {"previous_failure": {"diff_hash": "old", "status": "FAIL"}},
        "current_sources": [{"path": "src.py", "file_hash": "raw", "content_delivery": {
            "read": {"output.spans[0]": [[1, 2]]},
        }}],
        "working_notes": {"findings": [], "available_note_ids": []},
        "protocol_correction": None, "available_tool_names": tools,
        "public_task": {"description": "PUBLIC_TASK"},
    }
    initial = assemble_model_input(system_prompt="UNCHANGED_SYSTEM", state={
        "public_task": state["public_task"], "current_diff": {"patch_hash": "old"},
    }, history=[])
    history = [
        {"type": "reasoning", "id": "r1", "encrypted_content": "OPAQUE_ONE", "summary": []},
        {"type": "function_call", "call_id": "check", "name": "run_check",
         "arguments": '{"check_id":"regression"}'},
        {"type": "function_call_output", "call_id": "check", "output": json.dumps({
            "action_id": "check", "tool": "run_check", "status": "succeeded",
            "output": {"diff_hash": "old", "passed": False, "stdout": "OLD_PUBLIC_FAILURE"},
        })},
        {"type": "reasoning", "id": "r2", "encrypted_content": "OPAQUE_TWO", "summary": []},
        {"type": "function_call", "call_id": "edit", "name": "replace_text",
         "arguments": '{"old_text":"old","new_text":"new"}'},
        {"type": "function_call_output", "call_id": "edit", "output": json.dumps({
            "action_id": "edit", "tool": "replace_text", "status": "succeeded",
            "output": {"worktree_diff_hash": current},
        })},
    ]
    return {
        "model": "frozen-model", "reasoning": {"effort": "medium"}, "store": False,
        "max_output_tokens": 25000, "include": ["reasoning.encrypted_content"],
        "input": assemble_model_input(system_prompt="unused", state=state,
                                      history=history, previous_input=initial),
        "tools": [{"name": name, "parameters": {"z": 1, "a": 2}} for name in tools],
    }


def replace_state(request, record):
    request["input"][-1]["content"] = prototype.wire(record).decode()


@pytest.mark.parametrize("statuses", [
    ("NOT_RUN", "NOT_RUN"), ("PASS", "NOT_RUN"), ("NOT_RUN", "PASS"), ("PASS", "PASS"),
])
def test_exact_one_field_changes_without_touching_history_or_runtime_truth(statuses):
    request = frozen_request(statuses)
    original = prototype.wire(request)
    changed, metrics = prototype.without_further_edit_horizon(request)
    expected_record = json.loads(request["input"][-1]["content"])
    removed = expected_record["state"]["action_horizon"].pop("mutation_completion_horizon")
    expected = copy.deepcopy(request)
    expected["input"][-1]["content"] = prototype.wire(expected_record).decode()
    assert prototype.wire(changed) == prototype.wire(expected)
    assert prototype.wire(request) == original
    assert prototype.wire(changed["input"][:-1]) == prototype.wire(request["input"][:-1])
    assert prototype.wire(changed["tools"]) == prototype.wire(request["tools"])
    current = reconstruct_state(changed["input"])
    assert current["remaining_budget"]["accepted_mutations"] == 0
    assert current["action_horizon"]["completion_possible"]
    assert current["completion_guidance"] == reconstruct_state(request["input"])[
        "completion_guidance"
    ]
    assert removed["minimum_possible"] is False and metrics["reasoning_item_count"] == 2
    assert metrics["original_request_bytes"] == len(original)
    assert metrics["prototype_request_bytes"] == len(prototype.wire(changed)) < len(original)
    assert metrics["provider_calls"] == metrics["input_count_calls"] == 0
    for forbidden in ("PRIVATE_SPEC_SENTINEL", "HIDDEN_PATH_SENTINEL",
                      "REFERENCE_PATCH_SENTINEL", "PLAINTEXT_REASONING_SENTINEL"):
        assert forbidden not in prototype.wire(changed).decode()


@pytest.mark.parametrize("damage", [
    "mutations_remain", "bool_budget", "unknown_budget", "completion_impossible",
    "edit_possible", "forecast_missing", "empty_diff", "check_failed", "check_unknown",
    "check_old_diff", "no_checks", "current_failure", "mutation_tool", "tool_mismatch",
    "no_next_action", "guidance_old_diff", "wrong_gate", "wrong_check_id",
    "plaintext_reasoning", "missing_ciphertext", "old_state_only",
])
def test_ineligible_input_is_rejected_without_mutation_or_dispatch(damage):
    request = frozen_request()
    record = json.loads(request["input"][-1]["content"])
    state = record["state"]
    if damage in {"mutations_remain", "bool_budget", "unknown_budget"}:
        state["remaining_budget"]["accepted_mutations"] = {
            "mutations_remain": 1, "bool_budget": False, "unknown_budget": None,
        }[damage]
    elif damage == "completion_impossible":
        state["action_horizon"]["completion_possible"] = False
    elif damage == "edit_possible":
        state["action_horizon"]["mutation_completion_horizon"]["minimum_possible"] = True
    elif damage == "forecast_missing":
        del state["action_horizon"]["mutation_completion_horizon"]
    elif damage == "empty_diff":
        state["current_diff"]["patch"] = ""
    elif damage in {"check_failed", "check_unknown"}:
        state["visible_check_status"][0]["status"] = (
            "FAIL" if damage == "check_failed" else "UNKNOWN"
        )
    elif damage == "check_old_diff":
        state["visible_check_status"][0]["diff_hash"] = "old"
    elif damage == "no_checks":
        state["visible_check_status"] = []
    elif damage == "current_failure":
        state["current_public_failure"] = {"diff_hash": "current", "status": "FAIL"}
    elif damage == "mutation_tool":
        state["available_tool_names"].append("replace_text")
        request["tools"].append({"name": "replace_text"})
    elif damage == "tool_mismatch":
        request["tools"].pop()
    elif damage == "no_next_action":
        state["completion_guidance"]["next_action"] = {}
    elif damage == "guidance_old_diff":
        state["completion_guidance"]["diff_hash"] = "old"
    elif damage == "wrong_gate":
        state["workflow_gate"] = "needs_mutation"
    elif damage == "wrong_check_id":
        state["completion_guidance"]["next_action"]["check_id"] = "absent"
    elif damage == "plaintext_reasoning":
        request["input"][3]["text"] = "PLAINTEXT_REASONING_SENTINEL"
    elif damage == "missing_ciphertext":
        del request["input"][3]["encrypted_content"]
    replace_state(request, record)
    if damage == "old_state_only":
        request["input"].pop()
    before = prototype.wire(request)
    with pytest.raises(ValueError):
        prototype.without_further_edit_horizon(request)
    assert prototype.wire(request) == before


@pytest.mark.parametrize("damage", ["A", "B", "source", "manifest", "implementation"])
def test_frozen_packet_roundtrip_and_tamper_detection(tmp_path, monkeypatch, damage):
    def forbidden(*args, **kwargs):
        pytest.fail("no provider, count, network, subprocess or task execution")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    source = tmp_path / "source.json"
    body = prototype.wire(frozen_request())
    source.write_bytes(body)
    root = tmp_path / "packet"
    manifest = prototype.prepare(source, sha256_bytes(body), root)
    assert prototype.validate(root) == manifest
    assert source.read_bytes() == (root / "A.json").read_bytes() == body
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    assert prototype.validate(root) == manifest
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before
    with pytest.raises(ValueError, match="fresh external"):
        prototype.prepare(source, sha256_bytes(body), root)
    with pytest.raises(ValueError, match="input hash"):
        prototype.prepare(source, "sha256:wrong", tmp_path / "uncreated")
    assert not (tmp_path / "uncreated").exists()
    if damage in {"A", "B"}:
        (root / f"{damage}.json").write_bytes(b"tampered")
    elif damage == "source":
        source.write_bytes(body + b" ")
    else:
        key = "implementation_hash" if damage == "implementation" else "prototype_request_bytes"
        manifest[key] = "tampered"
        (root / "manifest.json").write_bytes(prototype.wire(manifest))
    with pytest.raises(ValueError, match="changed"):
        prototype.validate(root)


def test_cli_has_no_execution_or_credential_path(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["completion_signal_view", "--help"])
    with pytest.raises(SystemExit) as result:
        prototype.main()
    assert result.value.code == 0
    help_text = capsys.readouterr().out
    assert "{prepare,validate}" in help_text
    assert "collect" not in help_text and "credential" not in help_text
