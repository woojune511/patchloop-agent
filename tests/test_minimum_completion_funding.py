"""Successful completion funding is distinct from speculative recovery money."""

from dataclasses import replace
from decimal import Decimal

import pytest

from patchloop.dev import cost
from patchloop.dev.completion_budget import (
    CompletionState,
    completion_budget,
    minimum_successor_calls,
)


def state(**changes):
    baseline = CompletionState(
        check_count=2, remaining_check_count=2, unused_check_count=2,
        unrun_recoverable_check=True, requires_mutation=True, anchor_available=False,
        remaining_mutations=4, mutation_retry_available=True,
    )
    return replace(baseline, **changes)


def test_legacy_contract_is_unchanged_and_minimum_contract_is_explicit():
    legacy = {
        "policy": "completion-reserve-v1",
        "future_input_tokens": 60_000,
        "future_output_tokens": 128,
        "pricing": "uncached-input-and-minimum-output",
        "horizon": "intersect-funded-calls-with-existing-completion-paths-v1",
        "reservation": "largest-offered-action-successor-protected-or-minimum-v1",
        "release": "exact-count-for-ready-finish-with-no-successor",
        "limit": "Minimum admission only; useful output and task success are not guaranteed.",
    }
    assert cost.completion_cost_contract() == legacy
    assert cost.completion_cost_contract(cost.COMPLETION_RESERVE_POLICY) == legacy
    minimum = cost.completion_cost_contract(cost.COMPLETION_MINIMUM_POLICY)
    assert minimum["policy"] == "completion-minimum-v1"
    assert minimum["future_input_tokens"] == legacy["future_input_tokens"]
    assert minimum["future_output_tokens"] == legacy["future_output_tokens"]
    assert minimum["reservation"] == "largest-offered-action-minimum-successor-v1"
    assert "failure recovery and task success are not guaranteed" in minimum["limit"]
    assert cost.DEFAULT_COMPLETION_COST_POLICY == "per-call-v1"


@pytest.mark.parametrize("policy", ["per-call-v1", "unknown"])
def test_non_reserving_or_unknown_policy_has_no_reservation_contract(policy):
    with pytest.raises(ValueError, match="no reservation contract"):
        cost.completion_cost_contract(policy)


@pytest.mark.parametrize("tool", ["read_file", "search_files"])
@pytest.mark.parametrize("anchor", [False, True])
def test_source_inspection_only_credits_the_missing_anchor(tool, anchor):
    successor = ["edit", "check-0", "check-1", "finish"]
    initial = state(anchor_available=anchor)
    assert minimum_successor_calls(initial, tool) == len(successor)
    assert completion_budget(initial).minimum == len(successor) + int(not anchor)


@pytest.mark.parametrize("tool", ["search_history", "run_probe", "run_tests"])
def test_optional_observation_cannot_replace_the_current_source_anchor(tool):
    successor = ["read-anchor", "edit", "check-0", "check-1", "finish"]
    assert minimum_successor_calls(state(), tool) == len(successor)


def test_optional_edit_invalidates_every_existing_pass():
    ready = state(requires_mutation=False, anchor_available=True, remaining_check_count=0)
    assert minimum_successor_calls(ready, "finish_task") == 0
    assert minimum_successor_calls(ready, "read_file") == 1
    assert minimum_successor_calls(ready, "replace_text") == len([
        "check-0-again", "check-1-again", "finish",
    ])


@pytest.mark.parametrize("remaining", [1, 2, 3])
def test_required_check_pass_removes_one_check_and_keeps_finish(remaining):
    candidate = state(check_count=3, remaining_check_count=remaining,
                      requires_mutation=False, anchor_available=True)
    successor = [f"remaining-check-{index}" for index in range(remaining - 1)] + ["finish"]
    assert minimum_successor_calls(candidate, "run_check") == len(successor)


@pytest.mark.parametrize("automatic,eligible", [(False, False), (False, True),
                                                (True, False), (True, True)])
def test_only_current_eligible_automatic_recheck_saves_one_model_call(automatic, eligible):
    repair = state(check_count=3, remaining_check_count=3, anchor_available=True,
                   automatic_recheck=automatic, current_recheck_eligible=eligible)
    successor = ["check-0", "check-1", "check-2", "finish"]
    if automatic and eligible:
        successor.remove("check-0")  # Host still spends this tool action after the edit.
    assert minimum_successor_calls(repair, "replace_text") == len(successor)
    assert completion_budget(repair).minimum_tool_actions == 5


def test_diagnostic_pass_does_not_reuse_its_old_failed_check_auto_recheck_credit():
    baseline = state(anchor_available=True, automatic_recheck=True,
                     current_recheck_eligible=True)
    assert completion_budget(baseline).minimum == 3  # edit, other check, finish
    # The diagnostic PASS can retire the current failed check. A later edit must
    # then request both registered checks; it cannot reuse the old auto credit.
    successor = ["edit", "check-0", "check-1", "finish"]
    assert minimum_successor_calls(baseline, "run_check") == len(successor)


@pytest.mark.parametrize("cases", [0, 1, 8])
def test_finish_case_replays_consume_tool_slots_without_successor_model_calls(cases):
    ready = state(requires_mutation=False, anchor_available=True, remaining_check_count=0,
                  reproduction_case_count=cases, pending_reproduction_count=cases)
    assert minimum_successor_calls(ready, "finish_task") == 0
    assert completion_budget(ready).minimum == 1
    assert completion_budget(ready).minimum_tool_actions == 1 + cases


def test_acquiring_an_original_case_preserves_the_successful_repair_path():
    before = state(anchor_available=True)
    after = replace(before, reproduction_case_count=1, pending_reproduction_count=1)
    successful_path = ["edit", "check-0", "check-1", "finish"]
    assert minimum_successor_calls(before, "run_probe") == len(successful_path)
    assert minimum_successor_calls(after, "run_probe") == len(successful_path)
    assert completion_budget(after).minimum_tool_actions == len(successful_path) + 1
    assert completion_budget(after).protected > len(successful_path)


def test_worst_case_current_spend_leaves_each_successful_check_and_finish_funded():
    ledger = cost.DevCostLedger(Decimal("1"), cost.pricing_for_model("gpt-5.4-mini-2026-03-17"))
    unit = ledger.future_call_reservation_nanos()
    ledger.cap_nanos = 10 * unit
    path = [
        (state(), "read_file", 4),
        (state(anchor_available=True), "replace_text", 3),
        (state(requires_mutation=False, anchor_available=True), "run_check", 2),
        (state(requires_mutation=False, anchor_available=True, remaining_check_count=1),
         "run_check", 1),
        (state(requires_mutation=False, anchor_available=True, remaining_check_count=0),
         "finish_task", 0),
    ]
    for current, tool, expected in path:
        successor = minimum_successor_calls(current, tool)
        assert successor == expected
        reserve = successor * unit
        admission = ledger.admit(60_000, future_cost_reserve_nanos=reserve)
        assert admission is not None
        ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                      output_tokens=admission.output_ceiling)
        assert ledger.remaining_nanos >= reserve


def test_success_path_does_not_promise_funding_after_a_check_failure():
    candidate = state(requires_mutation=False, anchor_available=True, remaining_check_count=1)
    funded_successor = minimum_successor_calls(candidate, "run_check")
    failed = replace(candidate, requires_mutation=True)
    assert funded_successor == 1  # Only the successful next finish was funded.
    assert completion_budget(failed).minimum == 4  # Repair invalidates both checks.
    assert completion_budget(failed).minimum > funded_successor


def test_unknown_action_does_not_receive_a_zero_cost_successor():
    with pytest.raises(ValueError, match="unknown completion successor tool"):
        minimum_successor_calls(state(), "unregistered")
