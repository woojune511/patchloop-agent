from __future__ import annotations

import copy
import json
import socket
import subprocess
import sys
from types import SimpleNamespace

import pytest
from test_probe_first_view import frozen_request

from diagnostics import counterexample_review as design
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.util import sha256_bytes, sha256_json


def request_at_submission():
    request = frozen_request()
    request["model"] = design.MODEL
    record = json.loads(request["input"][-1]["content"])
    state = record["state"]
    state["workflow_gate"] = "ready_to_submit"
    state["current_public_failure"] = None
    state["remaining_budget"]["accepted_mutations"] = 2
    state["available_tool_names"].append("finish_task")
    request["tools"].append({"type": "function", "name": "finish_task", "parameters": {}})
    state["action_horizon"]["mutation_completion_horizon"] = {
        "minimum_calls": 4, "minimum_possible": True,
    }
    for check in state["visible_check_status"]:
        check["status"] = "PASS"
    request["input"][-1]["content"] = design.wire(record).decode()
    return request


def test_only_system_suffix_changes_preserving_state_memory_cipher_and_tool_order():
    request = request_at_submission()
    original = design.wire(request)
    alternate, metrics = design.add_review(request)
    expected = copy.deepcopy(request)
    expected["input"][0]["content"] += design.PROMPT_SUFFIX
    assert alternate == expected and design.wire(request) == original
    assert alternate["input"][1:] == request["input"][1:]
    assert reconstruct_state(alternate["input"]) == reconstruct_state(request["input"])
    assert metrics["control_request_bytes"] == len(original)
    assert metrics["treatment_request_bytes"] == len(design.wire(alternate))
    assert metrics["probe_plus_minimum_repair_calls"] == 5
    assert metrics["native_action_pair_count"] == metrics["reasoning_item_count"] == 1
    assert metrics["unchanged_tools_hash"] == sha256_bytes(design.wire(request["tools"]))
    # A generic workflow intervention, not this task's answers or the operator's case panel.
    for token in ("pyfakefs", "makedirs", "..", "symlink", "umask", "errno", "0o", "mode",
                  "a/../b", "file/../leaf", "private.yaml", "reference.patch"):
        assert token not in design.PROMPT_SUFFIX


@pytest.mark.parametrize("fault", [
    "different_model", "forced_tool", "zero_mutations", "old_pass", "failed_check", "empty_diff",
    "no_probe", "no_finish", "too_few_turns", "plain_reasoning", "missing_cipher", "unpaired",
    "duplicate_guidance", "summary",
])
def test_ineligible_or_invalid_request_is_rejected_without_mutating_it(fault):
    request = request_at_submission()
    record = json.loads(request["input"][-1]["content"])
    state = record["state"]
    if fault == "different_model":
        request["model"] = "another-model"
    elif fault == "forced_tool":
        request["tool_choice"] = {"type": "function", "name": "run_probe"}
    elif fault == "zero_mutations":
        state["remaining_budget"]["accepted_mutations"] = 0
    elif fault == "old_pass":
        state["visible_check_status"][0]["diff_hash"] = "old"
    elif fault == "failed_check":
        state["visible_check_status"][0]["status"] = "FAIL"
    elif fault == "empty_diff":
        state["current_diff"]["patch"] = ""
    elif fault in {"no_probe", "no_finish"}:
        name = "run_probe" if fault == "no_probe" else "finish_task"
        request["tools"] = [t for t in request["tools"] if t["name"] != name]
        state["available_tool_names"].remove(name)
    elif fault == "too_few_turns":
        state["remaining_budget"]["model_calls"] = 4
    elif fault == "plain_reasoning":
        request["input"][3]["text"] = "PLAINTEXT_REASONING_SENTINEL"
    elif fault == "summary":
        request["input"][3]["summary"] = ["PLAINTEXT_SUMMARY_SENTINEL"]
    elif fault == "missing_cipher":
        request["input"][3]["encrypted_content"] = ""
    elif fault == "unpaired":
        request["input"][4]["call_id"] = "unmatched"
    elif fault == "duplicate_guidance":
        request["input"][0]["content"] += design.PROMPT_SUFFIX
    request["input"][-1]["content"] = design.wire(record).decode()
    before = design.wire(request)
    with pytest.raises(ValueError):
        design.add_review(request)
    assert design.wire(request) == before


def test_instruction_survives_native_followup_once_without_rewriting_state():
    seed, _ = design.add_review(request_at_submission())
    state = reconstruct_state(seed["input"])
    state["remaining_budget"]["model_calls"] -= 1
    state["remaining_budget"]["tool_actions"] -= 1
    exchange = [
        {"type": "reasoning", "id": "r-next", "encrypted_content": "OPAQUE_NEXT", "summary": []},
        {"type": "function_call", "call_id": "probe", "name": "run_probe", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "probe", "output": "PUBLIC_PROBE_RESULT"},
    ]
    following = assemble_model_input(system_prompt="not reapplied", state=state,
                                      history=exchange, previous_input=seed["input"])
    assert following[:len(seed["input"])] == seed["input"]
    assert following[len(seed["input"]):][-2] == exchange[-1]
    assert sum(design.PROMPT_SUFFIX in i.get("content", "") for i in following) == 1
    assert reconstruct_state(following) == state


@pytest.mark.parametrize("fault", [None, "request_hash", "replay", "runtime", "current_diff"])
def test_restore_checks_prefix_and_wire_without_importing_future_output(
    tmp_path, monkeypatch, fault,
):
    request = request_at_submission()
    state = reconstruct_state(request["input"])
    raw_context = copy.deepcopy(state)
    raw_context["working_notes"] = {"larger_storage_only_representation": True}
    if fault == "current_diff":
        raw_context["current_diff"]["patch_hash"] = "different"
    store = ArtifactStore(tmp_path / "artifacts")
    turn = {
        "turn_id": "checkpoint",
        "context_artifact": store.put_json(raw_context).model_dump(mode="json"),
        "model_input_artifact": store.put_json(request["input"]).model_dump(mode="json"),
        "native_history": design.history_metadata(request["input"]),
        "available_tool_names": state["available_tool_names"], "targeted_read_paths": [],
    }
    config = ModelConfig(provider="openai", model_id=design.MODEL, reasoning_effort="medium",
                         reasoning_continuation="encrypted-v1", max_output_tokens=25000)
    wire_request = design.OpenAIResponsesAdapter.request_payload(
        SimpleNamespace(config=config), request["input"], request["tools"], system_prompt="unused",
    )
    envelope = SimpleNamespace(
        model=design.MODEL, reasoning_effort="medium", context_policy="append-v1",
        runtime_hash="runtime" if fault != "runtime" else "changed", compaction_contract=None,
        model_hash="model", task_content_hash="task", base_commit="base",
    )
    events = [{"event_type": "turn_started", "payload": turn, "sequence": 1, "event_hash": "cut"}]
    for kind in ("input_count_started", "provider_call_started"):
        events.append({"event_type": kind, "payload": {
            "turn_id": "checkpoint",
            "request_hash": sha256_json(wire_request) if fault != "request_hash" else "changed",
        }})
    events.append({"event_type": "evaluator_finished", "payload": {
        "not_public": "FUTURE_PRIVATE_SENTINEL", "model_response": "FUTURE_RESPONSE_SENTINEL",
    }})
    (tmp_path / "runs").mkdir()
    journal_path, envelope_path = tmp_path / "runs/source.jsonl", tmp_path / "runs/envelope.json"
    journal_path.write_text("immutable source", encoding="utf-8")
    envelope_path.write_text("immutable envelope", encoding="utf-8")
    journal = SimpleNamespace(
        events=lambda: events, load_envelope=lambda: envelope,
        path=journal_path, envelope_path=envelope_path,
    )

    def fake_journal(*args):
        return journal

    fake_journal.latest_tool_batch_results = lambda prefix: []

    def replay(**kwargs):
        # Not even the selected turn's dispatch is replayed.
        assert kwargs["journal"].events() == []
        return request["input"] if fault != "replay" else []

    monkeypatch.setattr(design, "DevJournal", fake_journal)
    monkeypatch.setattr(design, "TURN_NUMBER", 1)
    monkeypatch.setattr(design, "runtime_content_hash", lambda: "runtime")
    monkeypatch.setattr(design.runner, "_build_model_input", replay)
    monkeypatch.setattr(design, "dev_tool_schemas", lambda **kwargs: request["tools"])
    if fault:
        with pytest.raises(ValueError):
            design.restore(tmp_path)
    else:
        restored, checkpoint = design.restore(tmp_path)
        assert restored == wire_request
        assert checkpoint["prefix_event_count"] == 0
        assert b"FUTURE_" not in design.wire(restored)
        assert b"FUTURE_" not in design.wire(checkpoint)
        assert len(checkpoint["verified_source_files"]) == 4


@pytest.mark.parametrize("tamper", ["A.json", "B.json", "candidate.patch", "checkpoint.json",
                                    "protocol.json", "prompt.txt", "packet.json"])
def test_preparation_and_two_validations_never_execute_or_load_sibling_secrets(
    tmp_path, monkeypatch, tamper,
):
    def forbidden(*args, **kwargs):
        pytest.fail("network/provider/subprocess invoked during no-call preparation")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    source = tmp_path / "source"
    source.mkdir()
    for name in (".env", "private.yaml", "reference.patch", "operator-results.json"):
        (source / name).write_text("SECRET_PRIVATE_OPERATOR_SENTINEL", encoding="utf-8")
    checkpoint = {
        "source_run_id": "synthetic", "turn_number": 22, "turn_id": "selected-turn",
        "cutoff_event_sequence": 245, "cutoff_event_hash": "sha256:synthetic",
    }
    monkeypatch.setattr(design, "restore", lambda _: (request_at_submission(), checkpoint))
    root = tmp_path / "design"
    result = design.prepare(source, root)
    assert design.validate(root) == design.validate(root) == result
    outputs = b"".join(p.read_bytes() for p in root.iterdir() if p.is_file())
    assert b"SECRET_PRIVATE_OPERATOR_SENTINEL" not in outputs
    assert b"PLAINTEXT_REASONING_SENTINEL" not in outputs
    assert result["boundaries"]["provider_calls"] == result["boundaries"]["tool_executions"] == 0
    with pytest.raises(ValueError, match="fresh external"):
        design.prepare(source, root)
    (root / tamper).write_bytes(b"{}")
    with pytest.raises((ValueError, KeyError)):
        design.validate(root)


def test_design_is_voluntary_bounded_not_paid_or_agent_success_evidence():
    _, metrics = design.add_review(request_at_submission())
    protocol = design.protocol(metrics)
    assert protocol["branch_order"] == ["A1", "B1", "B2", "A2"]
    assert protocol["planning_cap_usd_each"] == "0.50"
    assert protocol["planning_cap_usd_total"] == "2.00"
    assert protocol["new_model_calls_each"] == 8 and protocol["maximum_new_model_calls"] == 32
    assert not protocol["paid_execution_authorized"] and not protocol["collector_implemented"]
    assert "no mandatory probe" in protocol["action_policy"]
    assert protocol["inherited_remaining_budget_each"]["accepted_mutations"] == 2
    assert protocol["boundaries"]["task_acceptance"] == "NOT_RUN"
    assert not protocol["boundaries"]["official"]


def test_cli_has_no_paid_or_tool_execution_entry_point(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["counterexample_review", "--help"])
    with pytest.raises(SystemExit) as exc:
        design.main()
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    assert "{prepare,validate}" in help_text
    assert "--credential" not in help_text and "collect" not in help_text
