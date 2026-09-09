from __future__ import annotations

import copy
import json
import socket
import subprocess
import sys

import pytest

from diagnostics import probe_first_view as design
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.util import sha256_bytes


def frozen_request():
    current = "sha256:public-current"
    names = ["search_files", "read_file", "replace_text", "stop_task", "run_probe"]
    state = {
        "public_task": {"description": "PUBLIC_TASK_ONLY"},
        "current_diff": {"patch_hash": current, "patch": "PUBLIC_DIFF_현재"},
        "current_public_failure": {"check_id": "regression", "diff_hash": current},
        "visible_check_status": [
            {"check_id": "contract", "diff_hash": current, "status": "PASS"},
            {"check_id": "regression", "diff_hash": current, "status": "FAIL"},
        ],
        "remaining_budget": {"model_calls": 20, "tool_actions": 80,
                             "accepted_mutations": 1, "active_wall_time_seconds": 1601},
        "action_horizon": {"completion_possible": True, "minimum_completion_calls": 4},
        "available_tool_names": names, "current_sources": [{"inline_spans": ["PUBLIC_SOURCE"]}],
        "working_notes": {"findings": [{"text": "MODEL_PUBLIC_NOTE"}]},
    }
    initial = assemble_model_input(system_prompt="UNCHANGED_SYSTEM", state=state, history=[])
    history = [
        {"type": "reasoning", "id": "r1", "encrypted_content": "OPAQUE_ONE", "summary": []},
        {"type": "function_call", "call_id": "check", "name": "run_check",
         "arguments": '{"check_id":"regression"}'},
        {"type": "function_call_output", "call_id": "check", "output": json.dumps({
            "tool": "run_check", "action_id": "check", "status": "succeeded",
            "output": {"diff_hash": current, "passed": False, "stdout": "PUBLIC_ERROR"},
        })},
    ]
    state["progress"] = "FAILED_CURRENT_CHECK"
    return {
        "model": "frozen-model", "tool_choice": "required", "parallel_tool_calls": True,
        "store": False, "include": ["reasoning.encrypted_content"], "max_output_tokens": 25000,
        "reasoning": {"effort": "medium"},
        "input": assemble_model_input(system_prompt="unused", state=state, history=history,
                                      previous_input=initial),
        "tools": [{"type": "function", "name": name, "parameters": {"z": 1, "a": 2}}
                  for name in names],
    }


def test_only_tool_choice_changes_no_hint_memory_budget_schema_or_cipher_changes():
    request = frozen_request()
    original = design.wire(request)
    alternate, metrics = design.force_probe(request)
    expected = copy.deepcopy(request)
    expected["tool_choice"] = {"type": "function", "name": "run_probe"}
    assert design.wire(alternate) == design.wire(expected)
    assert design.wire(request) == original
    assert design.wire(alternate["input"]) == design.wire(request["input"])
    assert design.wire(alternate["tools"]) == design.wire(request["tools"])
    assert reconstruct_state(alternate["input"]) == reconstruct_state(request["input"])
    assert metrics["reasoning_item_count"] == 1
    assert metrics["original_request_bytes"] == len(original)
    assert metrics["prototype_request_bytes"] == len(design.wire(alternate))
    assert metrics["unchanged_input_hash"] == sha256_bytes(design.wire(request["input"]))
    assert metrics["tool_names_in_order"] == [t["name"] for t in request["tools"]]


@pytest.mark.parametrize("fault", [
    "auto", "already_forced", "store", "no_include", "plain_reasoning", "no_cipher",
    "missing_model", "missing_probe", "missing_mutation", "duplicate_tool", "mismatched_tools",
    "wrong_probe_type", "no_failure", "old_failure", "old_check", "not_failed",
    "unknown_check", "empty_diff", "zero_mutations", "bool_budget", "no_budget",
    "zero_slack", "tool_zero_slack", "impossible", "bool_minimum", "short_bound", "no_latest",
])
def test_bad_or_ineligible_inputs_fail_without_mutating_request(fault):
    request = frozen_request()
    record = json.loads(request["input"][-1]["content"])
    state = record["state"]
    if fault == "auto":
        request["tool_choice"] = "auto"
    elif fault == "already_forced":
        request["tool_choice"] = dict(design.FORCED_PROBE)
    elif fault == "store":
        request["store"] = True
    elif fault == "no_include":
        request["include"] = []
    elif fault == "missing_model":
        request["model"] = None
    elif fault == "plain_reasoning":
        request["input"][3]["text"] = "PLAINTEXT_REASONING_SENTINEL"
    elif fault == "no_cipher":
        request["input"][3]["encrypted_content"] = ""
    elif fault in {"missing_probe", "missing_mutation"}:
        name = "run_probe" if fault == "missing_probe" else "replace_text"
        request["tools"] = [t for t in request["tools"] if t["name"] != name]
        state["available_tool_names"].remove(name)
    elif fault == "duplicate_tool":
        request["tools"].append(request["tools"][-1])
    elif fault == "mismatched_tools":
        request["tools"].pop()
    elif fault == "wrong_probe_type":
        request["tools"][-1]["type"] = "custom"
    elif fault == "no_failure":
        state["current_public_failure"] = None
    elif fault == "old_failure":
        state["current_public_failure"]["diff_hash"] = "old"
    elif fault == "old_check":
        state["visible_check_status"][1]["diff_hash"] = "old"
    elif fault in {"not_failed", "unknown_check"}:
        state["visible_check_status"][1]["status"] = "PASS" if fault == "not_failed" else "UNKNOWN"
    elif fault == "empty_diff":
        state["current_diff"]["patch"] = ""
    elif fault in {"zero_mutations", "bool_budget", "no_budget"}:
        state["remaining_budget"]["accepted_mutations"] = {
            "zero_mutations": 0, "bool_budget": True, "no_budget": None,
        }[fault]
    elif fault == "zero_slack":
        state["remaining_budget"]["model_calls"] = 4
    elif fault == "tool_zero_slack":
        state["remaining_budget"]["tool_actions"] = 4
    elif fault == "impossible":
        state["action_horizon"]["completion_possible"] = False
    elif fault == "bool_minimum":
        state["action_horizon"]["minimum_completion_calls"] = True
    elif fault == "short_bound":
        state["action_horizon"]["minimum_completion_calls"] = 8
    request["input"][-1]["content"] = design.wire(record).decode()
    if fault == "no_latest":
        request["input"].pop()
    before = design.wire(request)
    with pytest.raises(ValueError):
        design.force_probe(request)
    assert design.wire(request) == before


@pytest.mark.parametrize("field", ["A.json", "B.json", "protocol.json", "manifest.json",
                                   "source", "implementation", "runtime"])
def test_prepare_validate_only_reads_public_seed_no_execution_and_detects_tampering(
    tmp_path, monkeypatch, field,
):
    def forbidden(*args, **kwargs):
        pytest.fail("no network, provider, counting or subprocess execution")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    source = tmp_path / "input.json"
    raw = design.wire(frozen_request())
    source.write_bytes(raw)
    # None of these sibling private/operator/credential files should be read or copied.
    secrets = "PRIVATE_SPEC HIDDEN_TEST REFERENCE_PATCH OPERATOR_SOLUTION SECRET_API_KEY"
    (tmp_path / ".env").write_text(secrets)
    (tmp_path / "operator-report.txt").write_text(secrets)
    root = tmp_path / "packet"
    result = design.prepare(source, sha256_bytes(raw), root)
    assert design.validate(root) == result
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    assert (root / "A.json").read_bytes() == raw == source.read_bytes()
    assert design.validate(root) == result
    assert {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()} == before
    assert not any(token in b"".join(before.values()).decode() for token in secrets.split())
    assert result["provider_calls"] == result["input_count_calls"] == result["tool_executions"] == 0
    with pytest.raises(ValueError, match="fresh external"):
        design.prepare(source, sha256_bytes(raw), root)
    with pytest.raises(ValueError, match="input hash"):
        design.prepare(source, "sha256:wrong", tmp_path / "never-created")
    assert not (tmp_path / "never-created").exists()
    if field == "source":
        source.write_bytes(raw + b" ")
    elif field in {"implementation", "runtime"}:
        result[field + "_hash"] = "wrong"
        (root / "manifest.json").write_bytes(design.wire(result))
    else:
        (root / field).write_bytes(b"{}")
    with pytest.raises((ValueError, KeyError)):
        design.validate(root)


def test_contract_does_not_change_budget_or_credit_probe_as_correct_repair():
    _, metrics = design.force_probe(frozen_request())
    contract = design.design_contract(metrics)
    assert contract["inherited_remaining_budget_each"] == metrics["remaining_budget"]
    assert contract["new_response_limit_each"] == 8
    assert contract["shared_invocation_cap_usd"] == "1.20"
    assert len(contract["branches"]) == 4
    assert set(contract["review_axes"]) == {
        "question", "interpretation", "implementation", "completion",
    }
    assert not contract["collector_implemented"]
    assert contract["status"] == "PREPARED_NOT_EXECUTABLE"
    assert not contract["collection_boundaries"]["normal_runtime_change"]
    assert not contract["collection_boundaries"]["paid_retry_or_resume"]


def test_probe_feedback_remains_native_and_followup_request_is_normal():
    seed = frozen_request()
    initial_b, _ = design.force_probe(seed)
    state = reconstruct_state(seed["input"])
    state["remaining_budget"]["model_calls"] -= 1
    state["remaining_budget"]["tool_actions"] -= 1
    probe_history = [
        {"type": "reasoning", "id": "r-probe", "encrypted_content": "OPAQUE_PROBE", "summary": []},
        {"type": "function_call", "call_id": "probe", "name": "run_probe",
         "arguments": '{"question":"public question","python_source":"print(1)"}'},
        {"type": "function_call_output", "call_id": "probe", "output": json.dumps({
            "action_id": "probe", "tool": "run_probe", "status": "succeeded",
            "output": {"stdout": "PUBLIC_OBSERVATION", "diff_hash": "sha256:public-current"},
        })},
    ]
    following = copy.deepcopy(seed)  # Normal request builder, not the forced wire request.
    following["input"] = assemble_model_input(system_prompt="unused", state=state,
                                             history=probe_history,
                                             previous_input=initial_b["input"])
    assert following["tool_choice"] == "required"
    assert following["input"][:len(seed["input"])] == seed["input"]
    assert sum(i.get("encrypted_content") == "OPAQUE_PROBE" for i in following["input"]) == 1
    assert following["input"][len(seed["input"]):][-2] == probe_history[-1]
    assert reconstruct_state(following["input"])["remaining_budget"]["model_calls"] == 19


def test_cli_cannot_collect_or_load_credentials(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["probe_first_view", "--help"])
    with pytest.raises(SystemExit) as result:
        design.main()
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "{prepare,validate}" in output
    assert "collect" not in output and "credential" not in output
