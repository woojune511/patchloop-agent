"""Exploration must explain loss of an affordable repair before it happens."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_dev_completion_recovery import funding
from test_dev_completion_resources import Gateway, counters
from test_finish_reproduction_budget import snapshot

from patchloop.dev import runner, thin_policy
from patchloop.dev.completion_budget import CompletionState, action_budget_explanations
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import COMPLETION_RECOVERY_POLICY
from patchloop.dev.model_state import compact_model_state


def test_probe_warns_about_last_edit_opportunity_and_actual_transition_names_call_shortfall():
    gateway = Gateway(statuses=("PASS",), initial=False, mutations=2)
    gateway.verification_policy = "public-checks-v1"
    counts = counters(model=4, tools=12)
    limits = DevLimits(max_accepted_mutations=4)
    ledger = funding(20)

    def select(current):
        return runner._tool_policy(
            gateway, current, limits, cost_ledger=ledger,
            completion_cost_policy=COMPLETION_RECOVERY_POLICY,
        )

    before = select(counts)
    assert {"replace_text", "run_probe", "finish_task"} <= before.allowed_tools
    forecast = before.action_budget
    assert forecast["total_calls_remaining"] == 4
    assert forecast["correction_calls_reserved"] == 1
    assert forecast["ordinary_calls_remaining"] == 3
    assert forecast["edit_route_required"]["model_calls"] == 3
    probe = forecast["after_exploration"]["run_probe"][0]
    assert probe["ordinary_calls_after"] == 2
    assert probe["edit_route_shortfalls"] == ["model_calls"]

    # Same evidence, plenty of money, actions and edits: one response is decisive.
    after = select(replace(counts, model_calls=counts.model_calls + 1,
                           tool_actions=counts.tool_actions + 1))
    assert "replace_text" not in after.allowed_tools
    assert "finish_task" in after.allowed_tools
    assert after.edit_availability["reason"] == "model_calls_insufficient_for_edit_completion"
    history = SimpleNamespace(events=lambda: [
        {"event_type": "turn_started", "payload": {
            "turn_id": "t1", "available_tool_names": sorted(before.allowed_tools),
            "workflow_gate": before.workflow_gate,
        }},
        {"event_type": "turn_decision_recorded", "payload": {"turn_id": "t1"}},
    ])
    transition = runner._tool_policy_transition(history, after)
    assert transition["reason"] == after.edit_availability["reason"]
    assert "replace_text" in transition["removed_tools"]

    # The state the model receives keeps the warning, including in thin mode.
    state = {"action_horizon": {"action_budget": forecast}}
    assert thin_policy.project_state(compact_model_state(state, []), "thin") == state


def test_read_batches_share_one_response_but_comparisons_spend_two_executions():
    state = CompletionState(
        check_count=1, remaining_check_count=0, unused_check_count=0,
        unrun_recoverable_check=False, requires_mutation=False, anchor_available=True,
        remaining_mutations=2, mutation_retry_available=False,
    )
    report = action_budget_explanations(
        state, offered_tools=frozenset({"read_file", "search_files", "run_tests", "run_probe"}),
        total_model_calls=5, correction_model_calls=1, remaining_tool_actions=4,
        max_parallel_reads=4, test_comparison_enabled=True,
    )
    reads = report["after_exploration"]["read_file"]
    assert [row["ordinary_calls_after"] for row in reads] == [3] * 4
    assert [row["tool_actions_after"] for row in reads] == [3, 2, 1, 0]
    assert reads[0]["edit_route_shortfalls"] == []
    assert reads[1]["edit_route_shortfalls"] == ["tool_actions"]
    tests = report["after_exploration"]["run_tests"]
    assert tests[0]["variant"] == "single"
    assert tests[0]["edit_route_shortfalls"] == []
    assert tests[1]["variant"] == "comparison"
    assert tests[1]["edit_route_shortfalls"] == ["tool_actions"]
    assert "do not promise edit availability" in report["assumptions"]
    assert "cost and time require reassessment" in report["assumptions"]


def test_does_not_offer_unavailable_comparison_and_consumed_correction_releases_slot():
    state = CompletionState(
        check_count=1, remaining_check_count=0, unused_check_count=0,
        unrun_recoverable_check=False, requires_mutation=False, anchor_available=True,
        remaining_mutations=1, mutation_retry_available=False,
    )
    report = action_budget_explanations(
        state, offered_tools=frozenset({"run_tests"}), total_model_calls=4,
        correction_model_calls=0, remaining_tool_actions=8, max_parallel_reads=0,
        test_comparison_enabled=False,
    )
    assert report["ordinary_calls_remaining"] == 4
    assert len(report["after_exploration"]["run_tests"]) == 1
    assert report["after_exploration"]["run_tests"][0]["edit_route_shortfalls"] == []


@pytest.mark.parametrize("required,enabled,executions", [
    (False, True, [1, 2]), (True, True, [2]), (True, False, [2]),
])
def test_selected_test_variants_match_required_comparison_override(required, enabled, executions):
    state = CompletionState(
        check_count=1, remaining_check_count=0, unused_check_count=0,
        unrun_recoverable_check=False, requires_mutation=False, anchor_available=True,
        remaining_mutations=1, mutation_retry_available=False,
    )
    report = action_budget_explanations(
        state, offered_tools=frozenset({"run_tests"}), total_model_calls=4,
        correction_model_calls=0, remaining_tool_actions=8, max_parallel_reads=0,
        test_comparison_enabled=enabled, test_comparison_required=required,
    )
    variants = report["after_exploration"]["run_tests"]
    assert [row["tool_actions"] for row in variants] == executions
    if required:
        assert [row["variant"] for row in variants] == ["comparison"]
        assert variants[0]["tool_actions_after"] == 6


def test_pending_comparison_policy_uses_same_required_flag_as_schema_override():
    gateway = Gateway(statuses=("PASS",), initial=False, mutations=2)
    state = snapshot(gateway, status="cases_verified", case_count=0, pending_count=0)
    state.completion_verification.update(
        repair_path={"status": "diagnosed"},
        repair_prediction={"status": "needs_test_comparison"},
    )
    selected = runner._tool_policy(
        gateway, counters(model=20, tools=30), DevLimits(max_accepted_mutations=4),
        snapshot=state,
    )
    assert selected.selected_test_comparison_required
    assert selected.workflow_gate == "needs_test_comparison"
    variants = selected.action_budget["after_exploration"]["run_tests"]
    assert [row["variant"] for row in variants] == ["comparison"]
    assert variants[0]["tool_actions"] == 2


@pytest.mark.parametrize("resource", ["model_calls", "tool_actions", "cost", "time"])
def test_actual_edit_exclusion_identifies_the_limiting_resource(resource):
    gateway = Gateway(statuses=("PASS",), initial=False, mutations=2)
    gateway.verification_policy = "public-checks-v1"
    counts = counters(model=3 if resource == "model_calls" else 20,
                      tools=2 if resource == "tool_actions" else 30)
    ledger = funding(20)
    if resource == "cost":
        ledger.cap_nanos = 1
    selected = runner._tool_policy(
        gateway, counts, DevLimits(max_accepted_mutations=4), cost_ledger=ledger,
        completion_cost_policy=COMPLETION_RECOVERY_POLICY,
        remaining_seconds=1 if resource == "time" else 1000,
    )
    assert "replace_text" not in selected.allowed_tools
    assert selected.edit_availability["reason"] == f"{resource}_insufficient_for_edit_completion"
