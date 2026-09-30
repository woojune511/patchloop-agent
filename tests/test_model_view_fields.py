"""The compact view admits known public fields without reordering current inputs."""

import copy
import hashlib
import json

import pytest

from patchloop.dev.model_state import compact_model_state


def public_state():
    # Independent inventory of current base, optional and delivery fields.
    return {
        "workflow_gate": "needs_mutation",
        "completion_guidance": {"message": "repair then check"},
        "visible_check_status": [],
        "remaining_visible_check_ids": ["public"],
        "remaining_budget": {"model_calls": 4},
        "action_horizon": {"completion_possible": True, "inspection_turns_at_current_diff": 2},
        "current_public_failure": None,
        "mutation_readiness": {"state": "ready", "current_anchor_evidence_paths": ["a.py"]},
        "mutation_scope_budget": {"max_diff_lines": 50},
        "observed_source_index": {"entries": [], "omitted_count": 2},
        "evidence_ledger": {"search_summary": {"total_search_count": 1}},
        "working_notes": {"findings": [], "open_question": "경계?", "interpretation": "audit"},
        "context_projection": {"retained_content_chars": 0, "delivered_source_hash": "audit"},
        "commitment_signal": {"state": "open"},
        "available_tool_names": ["read_file", "replace_text"],
        "last_failed_mutation": None,
        "last_successful_mutation": None,
        "current_diff": {"patch_hash": "current", "patch": ""},
        "recent_checks": [],
        "public_execution_summary": {"checks": []},
        "latest_tool_results": [],
        "source_spans": [],
        "recent_attempt_result_next_question": [],
        "public_task": {"task_id": "public-example"},
        "working_plan": {"steps": [], "last_update_result": None},
        "probe_cases": {"cases": []},
        "repair_recheck": {"last_result": None},
        "recent_probes": [],
        "latest_tool_results_delivery": {"action_ids": ["read-1"]},
        "segment_handoff": {"segment_id": "segment-1", "review_requested": True},
        "protocol_correction": {"message": "Use an available action"},
    }


@pytest.mark.parametrize("reverse,expected_hash", [
    (False, "410b7f0901b8b7cd6dbfcce7b67616b81ad674fbfb1d1df8d30b4049d47396bc"),
    (True, "1a5fae24aaa568dda32a37cf9eac03964c4ff74159950c34172ac4bf42d955a7"),
])
def test_current_public_fields_keep_ordered_wire_and_independent_values(reverse, expected_hash):
    state = public_state()
    if reverse:
        state = dict(reversed(list(state.items())))
    before = copy.deepcopy(state)
    view = compact_model_state(state, [])
    wire = json.dumps(view, ensure_ascii=False, separators=(",", ":")).encode()
    assert hashlib.sha256(wire).hexdigest() == expected_hash
    assert state == before
    view["remaining_budget"]["model_calls"] = 0
    view["working_plan"]["steps"].append("changed")
    assert state == before


def test_new_top_level_audit_fields_do_not_enter_model_view_or_get_copied():
    class AuditOnly:
        def __deepcopy__(self, memo):
            pytest.fail("unselected audit fields must not be copied")

    state = public_state()
    expected = compact_model_state(state, [])
    audit = AuditOnly()
    state["future_audit_field"] = audit
    state["current_sources"] = [{"path": "unobserved.py"}]
    state["pending_recheck"] = {"check_id": "unobserved"}
    assert compact_model_state(state, []) == expected
    assert state["future_audit_field"] is audit


def test_projection_keeps_absent_fields_absent_and_explicit_nulls():
    assert compact_model_state({}, []) == {}
    state = {"protocol_correction": None, "current_public_failure": None}
    assert compact_model_state(state, []) == state


@pytest.mark.parametrize("field", [
    "candidate_reconsideration", "operator_public_feedback", "independent_candidate",
    "change_review_request", "paired_observation", "followup_state_contract",
    "operator_caller_observation", "verification_scope_cue", "expectation_review",
    "operator_current_candidate_feedback", "supplied_public_case", "public_case_status",
])
def test_existing_public_diagnostic_overlay_keeps_wire_without_enabling_other_fields(field):
    state = {"protocol_correction": None, field: {"origin": "public diagnostic", "value": []}}
    expected = json.dumps(state)
    state["future_diagnostic_field"] = "not automatically model-visible"
    view = compact_model_state(state, [])
    assert json.dumps(view) == expected
    view[field]["value"].append("changed")
    assert state[field]["value"] == []


@pytest.mark.parametrize("optional", [False, True])
def test_runner_fields_have_an_explicit_model_projection(gateway_factory, smoke_package, optional):
    from patchloop.dev.runner import _build_context, _RunCounters

    gateway, journal, _ = gateway_factory()
    if optional:
        gateway.probe_policy = "cases-v1"
        gateway.probe_sandbox = object()  # Context construction only; no tool execution.
    raw = json.loads(_build_context(
        package=smoke_package, gateway=gateway, journal=journal, correction=None,
        latest_tool_results=[], counters=_RunCounters(), elapsed_seconds=0,
        limits=gateway.limits, planning_policy="brief-v1" if optional else "none",
        repair_recheck=optional,
    ))
    assert set(raw) <= set(public_state())
    before = copy.deepcopy(raw)
    view = compact_model_state(raw, [])
    assert list(view) == [
        key for key in raw if key not in {"source_spans", "observed_source_index"}
    ] + ["current_sources", "source_index_omitted_count"]
    assert raw == before
