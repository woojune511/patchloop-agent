"""Small offline tests for diagnosis admission and paired-test physical budgets."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_finish_reproduction_budget import snapshot

from patchloop.dev import runner
from patchloop.dev.completion_budget import (
    CompletionState,
    completion_budget,
    minimum_successor_calls,
)
from patchloop.dev.contracts import DevLimits, RequestedTool
from patchloop.dev.cost import COMPLETION_MINIMUM_POLICY
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import sha256_json


def path_state(gateway, *, status="needs_path_diagnosis", preparation=True):
    state = snapshot(gateway, status="refuted", pending_count=0)
    state.completion_verification.update({
        "early_replay_reusable": True, "baseline_failure_case_ids": ["original"],
        "repair_path": {
            "policy": "repair-call-path-v1", "status": status, "blocked": status != "diagnosed",
            "preparation_available": preparation, "candidate_diff_hash": "candidate",
            "replay_action_id": "original", "case_id": "case", "call_id": "call-1",
            "rejected_requests": 0, "execution_attempted": status == "verification_incomplete",
        },
    })
    return state


@pytest.mark.parametrize("short", [None, "model", "tool", "money"])
def test_diagnosis_preserves_edit_original_recheck_check_and_finish(short):
    gateway = Gateway(initial=False)
    state = path_state(gateway)
    policy = runner._tool_policy(
        gateway, counters(model=3 if short == "model" else 4,
                          tools=4 if short == "tool" else 5), DevLimits(), snapshot=state,
        cost_ledger=ledger_for_slots(3 if short == "money" else 4),
        completion_cost_policy=COMPLETION_MINIMUM_POLICY, _preview_inspection=False,
    )
    assert policy.minimum_completion_calls == 4  # diagnostic, edit, check, finish
    assert policy.minimum_completion_tool_actions == 5  # same original replay after the edit
    if short:
        assert policy.allowed_tools == {"stop_task"}
        assert policy.workflow_gate == "verification_incomplete"
    else:
        assert policy.allowed_tools == {"run_probe", "stop_task"}
        assert policy.workflow_gate == "needs_path_diagnosis"
        guidance = runner._completion_guidance(state, policy)
        assert guidance["next_action"] == {
            "tool": "run_probe", "replay_action_id": "original", "call_path": {"call_id": "call-1"},
        }
        public = compact_model_state({
            "action_horizon": runner._repair_inspection_payload(policy)}, [])
        assert public["action_horizon"]["repair_path_diagnosis"] == policy.repair_path_diagnosis


def test_single_preparation_leaves_actual_diagnostic_available_and_has_no_edit_bypass():
    gateway = Gateway(initial=False)
    state = path_state(gateway)
    policy = runner._tool_policy(gateway, counters(model=5, tools=6), DevLimits(), snapshot=state)
    assert policy.allowed_tools == {"read_file", "search_files", "run_probe", "stop_task"}
    assert policy.max_parallel_reads == 1
    assert set(policy.tools_closing_after_this_turn) == {"read_file", "search_files"}
    state.completion_verification["repair_path"]["preparation_available"] = False
    after = runner._tool_policy(gateway, counters(model=4, tools=5), DevLimits(), snapshot=state)
    assert after.allowed_tools == {"run_probe", "stop_task"}


@pytest.mark.parametrize("status", ["diagnosed", "verification_incomplete"])
def test_complete_path_releases_repair_but_unknown_observation_cannot(status):
    gateway = Gateway(initial=False)
    state = path_state(gateway, status=status)
    policy = runner._tool_policy(gateway, counters(model=30, tools=70), DevLimits(), snapshot=state)
    if status == "diagnosed":
        assert policy.workflow_gate == "needs_mutation" and "replace_text" in policy.allowed_tools
    else:
        assert policy.workflow_gate == "verification_incomplete"
        assert policy.allowed_tools == {"stop_task"}
        assert "modified branch" in runner._completion_guidance(state, policy)["message"]


def test_diagnosis_budget_separates_execution_preparation_and_rejected_request_correction():
    state = CompletionState(
        check_count=1, remaining_check_count=1, unused_check_count=0,
        unrun_recoverable_check=False, requires_mutation=True, anchor_available=True,
        remaining_mutations=1, mutation_retry_available=False, reproduction_case_count=1,
    )
    before = completion_budget(state)
    pending = replace(state, path_diagnosis_pending=True, path_preparation_available=True,
                      path_request_correction_available=True)
    after = completion_budget(pending)
    assert after.minimum == before.minimum + 1
    assert after.minimum_tool_actions == before.minimum_tool_actions + 1
    assert after.protected == before.protected + 3
    assert after.protected_tool_actions == before.protected_tool_actions + 3
    assert minimum_successor_calls(pending, "run_probe") == before.minimum
    assert minimum_successor_calls(pending, "read_file") == after.minimum


def _comparison_call():
    return RequestedTool(name="run_tests", action_id="pair", arguments={
        "suite_id": "suite", "targets": ["tests/test_bug.py::test_bug"],
        "comparison": {"baseline": "original_base", "mutation_action_id": None},
    })


def _child(phase):
    return {"event_type": "test_comparison_child_started", "payload": {
        "action_id": "pair-" + phase, "identity": {"action_id": "pair", "phase": phase},
    }}


def test_comparison_admits_two_children_before_dispatch_with_completion_reserve():
    call = _comparison_call()
    policy = SimpleNamespace(completion_budget_tool_actions=4)
    assert runner._batch_fits_tool_budget([call], counters(tools=6), DevLimits(), policy)
    assert not runner._batch_fits_tool_budget([call], counters(tools=5), DevLimits(), policy)
    single = call.model_copy(update={"arguments": {**call.arguments, "comparison": None}})
    assert runner._batch_fits_tool_budget([single], counters(tools=1), DevLimits(), policy)


@pytest.mark.parametrize("tool_slots,comparison_enabled", [(2, False), (3, True)])
def test_schema_preserves_single_test_at_boundary_without_offering_unfunded_comparison(
    tool_slots, comparison_enabled,
):
    gateway = Gateway(("PASS",), initial=False)
    counts = counters(model=20, tools=tool_slots)
    limits = DevLimits()
    policy = runner._tool_policy(gateway, counts, limits)
    assert "run_tests" in policy.allowed_tools
    enabled = runner._test_comparison_enabled(policy, counts, limits)
    assert enabled is comparison_enabled
    schemas = dev_tool_schemas(
        finish_enabled=False, test_suite_ids=["suite"], allowed_tools=["run_tests"],
        test_comparison_enabled=enabled,
    )
    assert [item["name"] for item in schemas] == ["run_tests"]
    field = schemas[0]["parameters"]["properties"]["comparison"]
    assert ("anyOf" in field) is comparison_enabled
    if not enabled:
        assert field["type"] == "null"
    assert runner._batch_fits_tool_budget([_comparison_call()], counts, limits, policy) is enabled


def test_default_selected_test_schema_and_description_keep_pre_restriction_bytes():
    options = dict(finish_enabled=False, test_suite_ids=["suite"], allowed_tools=["run_tests"])
    default = dev_tool_schemas(**options)
    assert sha256_json(default) == (
        "sha256:de37564bb51728110c58d10b68af4badc04cd0a68eb6119439e0c754a09175dc"
    )
    assert default == dev_tool_schemas(**options, test_comparison_enabled=True)
    restricted = dev_tool_schemas(**options, test_comparison_enabled=False)
    restricted[0]["parameters"]["properties"]["comparison"] = (
        default[0]["parameters"]["properties"]["comparison"]
    )
    assert sha256_json(restricted) == sha256_json(default)


@pytest.mark.parametrize("raises", [False, True])
def test_child_starts_charge_live_and_restore_once_even_without_a_returned_result(raises):
    call = _comparison_call()
    events = [{"event_type": "tool_batch_started", "payload": {
        "tool_calls": [call.model_dump(mode="json")],
    }}]
    journal = SimpleNamespace(events=lambda: list(events))
    counts = runner._RunCounters(tool_actions=1)

    def execute(calls):
        assert calls == [call]
        if not any(e["event_type"] == "test_comparison_child_started" for e in events):
            events.extend([_child("baseline"), _child("candidate")])
        if raises:
            raise RuntimeError("lost result after dispatch")
        return []

    gateway = SimpleNamespace(execute_batch=execute)
    for _ in range(2):
        if raises:
            with pytest.raises(RuntimeError, match="lost result"):
                runner._execute_completion_batch(calls=[call], journal=journal, gateway=gateway,
                                                 counters=counts, active_elapsed_ms=lambda: 0)
        else:
            runner._execute_completion_batch(calls=[call], journal=journal, gateway=gateway,
                                             counters=counts, active_elapsed_ms=lambda: 0)
        assert counts.tool_actions == runner._restore_counters(journal).tool_actions == 2
