from __future__ import annotations

import copy
import hashlib
import json

import pytest
from test_dev_context_v12 import note_call, source_note
from test_dev_feedback_integration_v18 import _context, _input, _outputs
from test_dev_notes_lifecycle_v15 import _gateway, _read, _restart

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.dev.contracts import (
    DEV_RUN_SCHEMA,
    DevLimits,
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ProviderContinuationArtifact,
    PublicTurnDecision,
    dev_tool_surface_hash,
)
from patchloop.dev.inspection_projection import (
    project_inspection_context,
    project_inspection_result,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.tools import ALL_DEV_TOOLS, dev_tool_schemas

BASIS = "The previous read did not show the function body."
GOAL = "Locate the body before choosing an edit."


def _result(action_id="read-a", tool="read_file"):
    return {
        "action_id": action_id, "tool": tool, "status": "succeeded",
        "input_hash": "input-identity", "workspace_diff_hash": "diff-identity",
        "output": {
            "inspection_intent": {"mode": "inspect", "basis": BASIS, "evidence_goal": GOAL},
            "spans": [{"path": "src.py", "start_line": 1, "end_line": 2,
                       "file_hash": "raw-byte-identity", "content": "def f():\n    return 1"}],
            "evidence_gain": {"new_covered_line_count": 0}, "evidence_cache_hit": True,
        },
    }


def _payload():
    result = _result()
    return {
        "latest_tool_results": [result],
        "evidence_ledger": {
            "latest_inspection_intent": {
                "action_id": "read-a", "basis": BASIS, "evidence_goal": GOAL,
                "evidence_span_ids": ["span-a"], "marginal_evidence_gain": False,
            },
            "recent_inspection_outcomes": [{
                "action_id": "read-a", "tool": "read_file", "path": "src.py",
                "start_line": 1, "end_line": 2, "evidence_goal": GOAL,
                "outcome": "covered_only", "new_covered_line_count": 0,
            }],
        },
        "recent_attempt_result_next_question": [{
            "attempt": "inspect", "result": {"actions": [{
                "action_id": "read-a", "tool": "read_file",
                "input": {"path": "src.py", "start_line": 1, "end_line": 2},
                "turn_decision": {**result["output"]["inspection_intent"], "memory_update": None},
                "status": "succeeded", "span_count": 1,
            }]},
        }],
        "working_notes": {"findings": [], "open_question": "An explicit retained question."},
        "source_spans": copy.deepcopy(result["output"]["spans"]),
        "current_diff": {"patch": "unchanged public diff"},
        "current_public_failure": {"exception_type": "AssertionError"},
        "recent_checks": [{"check_id": "visible", "passed": False, "stderr": "public failure"}],
        "action_horizon": {"exploration_state": "open"},
    }


def test_context_only_delivery_keeps_latest_intent_once_and_observations_exact():
    payload = _payload()
    before = copy.deepcopy(payload)
    projected = project_inspection_context(payload)
    assert json.dumps(projected).count(BASIS) == 1
    assert json.dumps(projected).count(GOAL) == 1
    assert projected["latest_tool_results"] == payload["latest_tool_results"]
    ledger = projected["evidence_ledger"]
    assert ledger["latest_inspection_intent"]["decision_ref"] == {
        "action_id": "read-a", "delivery": "latest_tool_result.inspection_intent",
        "kind": "model_authored_pre_observation_intent",
    }
    assert ledger["latest_inspection_intent"]["evidence_span_ids"] == ["span-a"]
    assert ledger["recent_inspection_outcomes"][0]["outcome"] == "covered_only"
    for key in ("working_notes", "source_spans", "current_diff", "current_public_failure",
                "recent_checks", "action_horizon"):
        assert projected[key] == payload[key]
    assert project_inspection_context(projected) == projected
    assert payload == before


@pytest.mark.parametrize("tool", ["read_file", "search_files"])
def test_native_projection_removes_only_echoed_intent_not_tool_evidence(tool):
    result = _result(tool=tool)
    before = copy.deepcopy(result)
    projected = project_inspection_result(result, native_action_ids=["read-a"])
    reference = projected["output"].pop("inspection_intent_ref")
    assert reference["delivery"] == "preceding_function_call_arguments"
    expected = copy.deepcopy(result)
    expected["output"].pop("inspection_intent")
    assert projected == expected
    assert result == before


def test_native_and_historical_references_do_not_repeat_prior_premises():
    payload = _payload()
    native = project_inspection_context(payload, native_action_ids=["read-a"])
    assert BASIS not in json.dumps(native)
    assert GOAL not in json.dumps(native)
    assert project_inspection_context(native, native_action_ids=["read-a"]) == native
    assert native["evidence_ledger"]["latest_inspection_intent"]["decision_ref"][
        "delivery"
    ] == "preceding_function_call_arguments"
    historical = project_inspection_context({**native, "latest_tool_results": []})
    assert historical["evidence_ledger"]["latest_inspection_intent"]["decision_ref"][
        "delivery"
    ] == "journal_only"
    assert historical["recent_attempt_result_next_question"][0]["result"]["actions"][0][
        "input"
    ] == {"path": "src.py", "start_line": 1, "end_line": 2}


def test_repeated_text_in_source_notes_questions_and_checks_is_never_redacted():
    payload = _payload()
    payload["source_spans"][0]["content"] = BASIS
    payload["working_notes"] = {"findings": [{"statement": BASIS}], "open_question": GOAL}
    payload["recent_checks"][0]["stdout"] = BASIS
    projected = project_inspection_context(payload, native_action_ids=["read-a"])
    for key in ("source_spans", "working_notes", "recent_checks"):
        assert projected[key] == payload[key]
    assert json.dumps(projected).count(BASIS) == 3
    assert json.dumps(projected).count(GOAL) == 1


@pytest.mark.parametrize("tool", [
    "replace_text", "run_check", "run_probe", "finish_task", "stop_task",
])
def test_noninspection_results_are_not_rewritten(tool):
    result = _result(tool=tool)
    assert project_inspection_result(result, native_action_ids=["read-a"]) == result


def test_failed_read_without_intent_and_empty_initial_context_remain_exact():
    result = _result()
    result.update(status="failed", error_code="PUBLIC_READ_ERROR", output={"diagnostic": "eof"})
    assert project_inspection_result(result, native_action_ids=["read-a"]) == result
    assert project_inspection_context({}) == {}


def _complete(gateway, calls, turn_id, store):
    continuation = ProviderContinuationArtifact(output_order=[
        EncryptedReasoningContinuationItem(
            id=f"rs-{turn_id}", encrypted_content="opaque-test-state",
        ),
        *(FunctionCallContinuationRef(action_id=call.action_id) for call in calls),
    ])
    ref = runner._store_provider_continuation(store, continuation)
    gateway.journal.append("turn_started", {"turn_id": turn_id})
    gateway.journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [call.model_dump(mode="json") for call in calls],
        "continuation_ref": ref.model_dump(mode="json"),
    })
    update = gateway.record_working_notes_update(calls, turn_id=turn_id)
    results = gateway.execute_batch(calls)
    runner._record_tool_batch(
        journal=gateway.journal, gateway=gateway, turn_id=turn_id, calls=calls,
        results=results, active_elapsed_ms=0,
    )
    return update, results, ref


def test_parallel_native_receipt_cache_and_restart_preserve_originals(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    calls = [note_call("owner", source_note("The observed declaration is stable.", 3, 3)),
             note_call("second", None)]
    for call in calls:
        call.turn_decision = PublicTurnDecision(
            mode="inspect", basis=f"{BASIS} {call.action_id}",
            evidence_goal=f"{GOAL} {call.action_id}",
            memory_update=call.turn_decision.memory_update,
        )
    original_calls = [call.model_dump(mode="json") for call in calls]
    store = ArtifactStore(tmp_path / "artifacts")
    update, results, ref = _complete(gateway, calls, "parallel", store)
    before = gateway.journal.path.read_bytes()
    original_results = [result.model_dump(mode="json") for result in results]
    saved_context = _context(gateway, results)
    items = _input(gateway, results, tmp_path, context=saved_context)
    outputs = _outputs(items)
    native_calls = [item for item in items if item.get("type") == "function_call"]
    assert [item["call_id"] for item in native_calls] == [call.action_id for call in calls]
    for call, native in zip(calls, native_calls, strict=True):
        assert json.loads(native["arguments"]) == runner._provider_tool_arguments(call)
        assert json.dumps(items).count(call.turn_decision.basis) == 1
        assert json.dumps(items).count(call.turn_decision.evidence_goal) == 1
    assert outputs["owner"]["memory_update_result"] == update["receipt"]
    assert "memory_update_result" not in outputs["second"]
    for result in results:
        assert outputs[result.action_id]["output"]["spans"] == result.output["spans"]
        assert outputs[result.action_id]["output"]["evidence_gain"] == (
            result.output["evidence_gain"]
        )
    assert items[1]["encrypted_content"] == "opaque-test-state"
    assert items[1]["summary"] == []
    assert runner._load_provider_continuation(store, ref).output_order[0].encrypted_content == (
        "opaque-test-state"
    )
    restored = _restart(gateway)
    assert _input(restored, results, tmp_path, context=saved_context) == items
    rebuilt = _input(restored, results, tmp_path)
    assert rebuilt[:-1] == items[:-1]
    assert json.loads(rebuilt[-1]["content"]) == json.loads(items[-1]["content"])
    assert gateway.journal.path.read_bytes() == before
    assert [call.model_dump(mode="json") for call in calls] == original_calls
    assert [result.model_dump(mode="json") for result in results] == original_results
    # Cached reinspection receives its own decision identity; no stale premise is reused.
    call = note_call("cached-next", None)
    call.turn_decision.basis = "A different pre-observation interpretation."
    _, cached, _ = _complete(restored, [call], "cached", store)
    assert cached[0].evidence_cache_hit is True
    next_items = _input(restored, cached, tmp_path)
    assert json.dumps(next_items).count(call.turn_decision.basis) == 1
    assert BASIS not in json.dumps(next_items)


def test_surface_identity_changes_without_tool_inputs_prompt_or_limits_changing():
    schemas = dev_tool_schemas(finish_enabled=True, allowed_tools=ALL_DEV_TOOLS)

    def structure(value):
        if isinstance(value, dict):
            return {key: structure(item) for key, item in value.items() if key != "description"}
        if isinstance(value, list):
            return [structure(item) for item in value]
        return value

    encoded = json.dumps(structure(schemas), separators=(",", ":"), ensure_ascii=False).encode()
    assert hashlib.sha256(encoded).hexdigest() == (
        "2be7c053908b397aaefac42085a7af992e60dcac39ad45c0bbc3cb88d92278aa"
    )
    assert dev_tool_surface_hash() != (
        "sha256:90dc9a92b61cfd61f61572af504a66424f3e703ab8e29f114de29c22cf97a684"
    )
    assert len(DEV_SYSTEM_PROMPT) == 7880
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions, limits.max_accepted_mutations,
            limits.wall_time_seconds) == (40, 100, 4, 1800)
