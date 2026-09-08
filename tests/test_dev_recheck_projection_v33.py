"""Separate a checked failure from an edited-but-unchecked candidate, without gates."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest
from native_history_support import input_context
from test_dev_completion_v27 import CheckSandbox, _batch, _check
from test_dev_feedback_integration_v18 import _completed_batch, _context, _input, _outputs
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import assemble_model_input, reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.runner import _build_context, _RunCounters, _tool_policy
from patchloop.util import canonical_json


def _state(*, currency="historical", failure_hash="before", current="after"):
    failure = {
        "check_id": "public", "diff_hash": failure_hash,
        "exception_type": "TypeError", "failure_signature": "signature",
        "failure_summary": {"lines": ["TypeError: public bytes mismatch"],
                            "observed_count": 1, "truncated": False},
        "comparison_with_previous_failure": {
            "relation": "same_public_failure_site",
            "inference": "The changed diff did not move the mapped public failure site.",
        },
        "recurrence_across_distinct_diffs": 2,
    }
    state = {
        "current_public_failure": {
            **failure, "current_diff_hash": current, "evidence_currency": currency,
            "phase": "repair_current_diff" if currency == "current" else "awaiting_recheck",
            "mutation_pressure": {"same_public_failure_site": True,
                                  "guidance": "Use run_check for the current candidate."},
        },
        "current_diff": {"patch_hash": current, "patch": "PUBLIC_DIFF"},
        "visible_check_status": [{"check_id": "public", "diff_hash": current,
                                  "status": "FAIL" if currency == "current" else "NOT_RUN"}],
        "available_tool_names": ["read_file", "replace_text", "run_check", "stop_task"],
        "completion_guidance": {"next_action": {"tool": "run_check", "check_id": "public"}},
    }
    result = {"action_id": "old-check", "tool": "run_check", "status": "succeeded",
              "output": {"check_id": "public", "diff_hash": failure_hash, "passed": False,
                         "public_check_failure": failure}}
    history = [{"type": "function_call_output", "call_id": "old-check",
                "output": canonical_json(result)}]
    return state, history


def _awaiting_recheck(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.sandbox = CheckSandbox()
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=["python", "-c", "pass"])
        for name in ("contract", "regression")
    ]
    _read(gateway)
    _batch(gateway, _mutation("first-edit"), tmp_path)
    _batch(gateway, _check("contract", "old-contract"), tmp_path)
    _batch(gateway, _check("regression", "old-regression"), tmp_path)
    repair = _batch(gateway, _mutation("repair", "editable = 1", "editable = 2"), tmp_path)
    return gateway, repair


def test_row40_pattern_is_pending_not_an_active_recurrent_failure():
    state, history = _state()
    before = copy.deepcopy((state, history))
    view = compact_model_state(state, history)
    assert view["current_public_failure"] is None
    pending = view["pending_recheck"]
    assert pending["check_id"] == "public" and pending["diff_hash"] == "after"
    assert pending["current_check_status"] == "NOT_RUN"
    assert pending["previous_failure"] == {
        "check_id": "public", "diff_hash": "before", "evidence_currency": "historical",
        "action_id": "old-check", "delivery": "preceding_function_call_output",
        "field": "output.public_check_failure",
    }
    assert "mutation_pressure" not in canonical_json(view)
    assert "same_public_failure_site" not in canonical_json(view)
    assert "TypeError" not in canonical_json(view)
    assert (state, history) == before
    assert view["completion_guidance"] == state["completion_guidance"]
    assert view["available_tool_names"] == state["available_tool_names"]


@pytest.mark.parametrize("mismatch", ["missing", "tool", "status", "passed", "check_id",
                                     "diff_hash", "summary", "call_id"])
def test_no_receipt_reference_without_complete_matching_delivery(mismatch):
    state, history = _state()
    result = json.loads(history[0]["output"])
    if mismatch in {"tool", "status"}:
        result[mismatch] = "different"
    elif mismatch in {"check_id", "diff_hash", "passed"}:
        result["output"][mismatch] = "different"
    elif mismatch == "summary":
        result["output"]["public_check_failure"]["failure_summary"]["lines"] = ["Different"]
    elif mismatch == "call_id":
        history[0]["call_id"] = "unrelated"
    history[0]["output"] = canonical_json(result)
    if mismatch == "missing":
        history = []
    view = compact_model_state(state, history)
    prior = view["pending_recheck"]["previous_failure"]
    assert "delivery" not in prior and "action_id" not in prior
    assert prior["details"]["failure_summary"] == state["current_public_failure"]["failure_summary"]
    assert "mutation_pressure" not in prior["details"]
    assert "current_diff_hash" not in prior["details"]
    assert view["current_public_failure"] is None


def test_unknown_binding_is_not_current_failure_or_current_check_result():
    state, history = _state(currency="unknown", failure_hash=None)
    state["visible_check_status"] = []
    view = compact_model_state(state, history)
    assert view["current_public_failure"] is None
    assert view["pending_recheck"]["current_check_status"] == "UNKNOWN"
    assert view["pending_recheck"]["previous_failure"]["evidence_currency"] == "unknown"


def test_real_current_failure_keeps_exact_diagnostics_and_repair_advice():
    state, history = _state(currency="current", failure_hash="after")
    state["current_public_failure"]["mutation_pressure"]["guidance"] = "Use replace_text."
    view = compact_model_state(state, history)
    assert view["current_public_failure"] == state["current_public_failure"]
    assert "pending_recheck" not in view


@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_already_observed_current_check_does_not_get_a_pending_recheck_card(status):
    state, history = _state()
    state["visible_check_status"][0]["status"] = status
    view = compact_model_state(state, history)
    assert view["current_public_failure"] is None
    assert "pending_recheck" not in view
    assert view["visible_check_status"] == state["visible_check_status"]


def test_latest_complete_view_clears_pending_without_rewriting_old_exchange():
    raw, history = _state()
    pending = compact_model_state(raw, history)
    previous = assemble_model_input(system_prompt="fixed", state=pending, history=history)
    original = copy.deepcopy(previous)
    passed = copy.deepcopy(raw)
    passed["current_public_failure"] = None
    passed["visible_check_status"][0]["status"] = "PASS"
    current = compact_model_state(passed, history)
    items = assemble_model_input(system_prompt="fixed", state=current, history=[],
                                 previous_input=previous)
    assert items[:len(previous)] == original
    assert "pending_recheck" not in reconstruct_state(items)
    assert previous == original


@pytest.mark.parametrize("result_after_repair", ["PASS", "FAIL"])
def test_actual_native_repair_read_restart_and_recheck(tmp_path, result_after_repair):
    gateway, repair = _awaiting_recheck(tmp_path)
    results = [repair]
    before_policy = _tool_policy(gateway, _RunCounters(), gateway.limits)
    canonical = json.loads(_context(gateway, results))
    items = _input(gateway, results, tmp_path)
    view = input_context(items)
    assert canonical["current_public_failure"]["evidence_currency"] == "historical"
    assert view["current_public_failure"] is None
    assert view["pending_recheck"]["current_check_status"] == "NOT_RUN"
    assert view["pending_recheck"]["previous_failure"]["delivery"] == (
        "preceding_function_call_output"
    )
    assert before_policy == _tool_policy(gateway, _RunCounters(), gateway.limits)
    assert {"replace_text", "run_check", "read_file"} <= before_policy.allowed_tools
    original_journal = gateway.journal.path.read_bytes()
    restored = _restart(gateway)
    replay = restored.execute(_mutation("repair", "editable = 1", "editable = 2"))
    assert replay.replayed and restored.accepted_mutations == 2
    assert _input(restored, results, tmp_path) == items
    assert gateway.journal.path.read_bytes() == original_journal
    assert _outputs(items)[repair.action_id]["output"]["worktree_diff_hash"] == (
        gateway.current_diff_hash
    )
    # Unrelated public inspection does not reactivate the historical error.
    read = _batch(restored, RequestedTool(
        name="read_file", action_id="after-repair-read",
        arguments={"path": "src.py", "start_line": 1, "end_line": 2},
        turn_decision=PublicTurnDecision(mode="inspect", basis="Inspect an independent question.",
                                        evidence_goal="Observe the public dependency."),
    ), tmp_path)
    after_read = _input(restored, [read], tmp_path)
    assert input_context(after_read)["pending_recheck"] == view["pending_recheck"]
    if result_after_repair == "FAIL":
        # The registered fake returns FAIL for exactly this call history.
        restored.sandbox.calls = ["contract"]
    checked = _batch(restored, _check("regression", "recheck-current"), tmp_path)
    after_check = _input(restored, [checked], tmp_path)
    assert "pending_recheck" not in input_context(after_check)
    if result_after_repair == "PASS":
        assert input_context(after_check)["current_public_failure"] is None
    else:
        focus = input_context(after_check)["current_public_failure"]
        assert focus["evidence_currency"] == "current"
        assert focus["diff_hash"] == gateway.current_diff_hash
    assert after_check[:len(after_read)] == after_read


def test_rejected_followup_edit_keeps_pending_baseline_and_does_not_force_repair(tmp_path):
    gateway, repair = _awaiting_recheck(tmp_path)
    pending = input_context(_input(gateway, [repair], tmp_path))["pending_recheck"]
    before = gateway.current_diff_hash
    rejected = gateway.execute(_mutation("bad-optional", "NOT_AN_ANCHOR", "changed"))
    assert rejected.status == "failed" and gateway.current_diff_hash == before
    raw = json.loads(_context(gateway, [rejected]))
    history = _input(gateway, [repair], tmp_path)
    assert compact_model_state(raw, history)["pending_recheck"] == pending
    policy = _tool_policy(gateway, _RunCounters(), gateway.limits)
    assert "run_check" in policy.allowed_tools and policy.completion_possible


def test_parallel_reads_keep_pending_and_independent_followup_mutation_is_allowed(tmp_path):
    gateway, repair = _awaiting_recheck(tmp_path)
    pending = input_context(_input(gateway, [repair], tmp_path))["pending_recheck"]
    calls = [RequestedTool(
        name="read_file", action_id=f"parallel-{line}",
        arguments={"path": "src.py", "start_line": line, "end_line": line},
        turn_decision=PublicTurnDecision(mode="inspect", basis="Independent public observation.",
                                        evidence_goal="Inspect a dependency."),
    ) for line in (1, 2)]
    _, results = _completed_batch(gateway, calls, "parallel-inspection")
    items = _input(gateway, results, tmp_path)
    assert input_context(items)["pending_recheck"] == pending
    assert set(_outputs(items)) >= {call.action_id for call in calls}
    # A real source-supported edit remains possible without a mandatory check.
    edited = _batch(gateway, _mutation("independent", "other = 0", "other = 1"), tmp_path)
    view = input_context(_input(gateway, [edited], tmp_path))
    assert view["pending_recheck"]["diff_hash"] == gateway.current_diff_hash
    assert view["pending_recheck"]["diff_hash"] != pending["diff_hash"]
    assert view["pending_recheck"]["previous_failure"] == pending["previous_failure"]


def test_pending_projection_does_not_load_private_or_reasoning_fields(tmp_path):
    gateway, repair = _awaiting_recheck(tmp_path)
    package = SimpleNamespace(
        public=SimpleNamespace(model_dump=lambda **kwargs: {"task_id": "public-note-feedback"}),
        private="PRIVATE_SPEC_SENTINEL", hidden="HIDDEN_PATH_SENTINEL",
        reference_patch="REFERENCE_PATCH_SENTINEL", reasoning="RAW_REASONING_SENTINEL",
    )
    context = _build_context(
        package=package, gateway=gateway, journal=gateway.journal, correction=None,
        latest_tool_results=[repair], counters=_RunCounters(), elapsed_seconds=0,
        limits=gateway.limits,
    )
    items = _input(gateway, [repair], tmp_path, context=context)
    assert input_context(items)["pending_recheck"]
    combined = context + canonical_json(items) + canonical_json(gateway.journal.events())
    for secret in (package.private, package.hidden, package.reference_patch, package.reasoning):
        assert secret not in combined
