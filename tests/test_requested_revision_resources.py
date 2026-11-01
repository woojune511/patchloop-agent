"""Pure requested-revision paths and independent resource lower bounds."""

from dataclasses import replace

import pytest

from patchloop.dev.completion_budget import CompletionRoute, CompletionState, CompletionStep
from patchloop.dev.cost import FINALIZATION_OUTPUT_FLOOR
from patchloop.dev.recovery_resources import (
    RecoveryResources,
    merge_resources,
    requested_revision_resources,
    successor_resources,
)


def state(**changes):
    return replace(CompletionState(
        check_count=1, remaining_check_count=0, unused_check_count=0,
        unrun_recoverable_check=False, requires_mutation=False, anchor_available=True,
        remaining_mutations=2, mutation_retry_available=True,
        reproduction_case_count=1, early_reproduction_count=1, early_replay_reusable=True,
    ), **changes)


def resources(tool="run_probe", *, current=None, **changes):
    return requested_revision_resources(
        current or state(), tool, max_output_tokens=40_000,
        check_seconds=(15,), probe_seconds=35, **changes,
    )


@pytest.mark.parametrize("tool,seconds", [
    ("read_file", 140), ("search_files", 140), ("search_history", 140), ("run_probe", 175),
])
def test_exploration_retains_edit_replay_check_finish_in_all_dimensions(tool, seconds):
    original = state()
    reserved = resources(tool, current=original)
    route, = reserved.routes
    assert route.name == "requested_revision"
    assert [step.role for step in route.successors] == [
        "repair", "original_replay", "public_check", "finish"]
    assert reserved.model_calls == 4 and reserved.tool_actions == 5
    assert reserved.seconds == seconds
    assert reserved.output_ceilings == (
        40_000, FINALIZATION_OUTPUT_FLOOR, FINALIZATION_OUTPUT_FLOOR)
    assert reserved.output_options == (reserved.output_ceilings,)
    assert not reserved.failure_recovery and not original.requires_mutation


@pytest.mark.parametrize("tool", ["read_file", "search_files", "search_history", "run_probe"])
def test_optional_read_or_helper_cannot_claim_to_supply_a_missing_mutation_anchor(tool):
    reserved = resources(tool, current=state(anchor_available=False))
    assert reserved.routes[0].successors[0].role == "source_anchor"
    assert reserved.model_calls == 5 and reserved.tool_actions == 6
    assert reserved.seconds == resources(tool).seconds + 30


@pytest.mark.parametrize("comparison,actions,seconds", [(False, 5, 160), (True, 6, 180)])
def test_selected_test_preserves_one_response_and_actual_sandbox_executions(
    comparison, actions, seconds,
):
    reserved = resources("run_tests", optional_check_seconds=20, test_comparison=comparison)
    assert reserved.model_calls == 4 and reserved.tool_actions == actions
    assert reserved.seconds == seconds
    current = reserved.routes[0].current
    assert current.role == "selected_test" and current.model_call
    assert current.tool_actions == (2 if comparison else 1)
    assert current.execution_seconds == (40 if comparison else 20)


def test_all_original_replays_and_fresh_checks_survive_existing_same_diff_passes():
    reserved = requested_revision_resources(
        state(check_count=2, reproduction_case_count=2, early_reproduction_count=2),
        "run_probe", max_output_tokens=40_000, check_seconds=(15, 25), probe_seconds=35,
    )
    steps = reserved.routes[0].successors
    assert sum(step.role == "original_replay" for step in steps) == 2
    assert sum(step.role == "public_check" for step in steps) == 2
    assert reserved.model_calls == 5 and reserved.tool_actions == 7
    assert reserved.seconds == 265


def test_merge_keeps_more_expensive_short_adapter_and_larger_physical_time_floors():
    existing = RecoveryResources((100_000,), 900, True, adapter_reason="special_obligations")
    requested = resources()
    merged = merge_resources(existing, requested, model_floor=8, tool_floor=12)
    assert merged.model_calls == 8 and merged.tool_actions == 12
    assert merged.seconds == 900 and merged.failure_recovery
    assert merged.adapter_reason == "special_obligations"
    assert merged.output_ceilings == requested.output_ceilings
    # Funding must use every alternative, not only the longest primary tuple.
    assert merged.output_options == (requested.output_ceilings, existing.output_ceilings)
    assert max(sum(option) for option in merged.output_options) == 100_000
    assert existing.model_calls is None and existing.tool_actions is None
    assert merge_resources(merged, requested) == merged


def test_merge_keeps_all_old_alternatives_and_uses_maxima_not_sums():
    old_route = CompletionRoute(
        "legacy_route", CompletionStep("read"), (CompletionStep("finish", output_tokens=7_000),))
    old_alternative = CompletionRoute(
        "other_route", CompletionStep("read"), (CompletionStep("repair", output_tokens=80_000),))
    existing = RecoveryResources((5_000,), 10, False, (old_route, old_alternative))
    requested = resources()
    merged = merge_resources(existing, requested)
    assert merged.model_calls == 4 and merged.tool_actions == 5 and merged.seconds == 175
    assert set(merged.output_options) == {
        (5_000,), (7_000,), (80_000,),
        (40_000, FINALIZATION_OUTPUT_FLOOR, FINALIZATION_OUTPUT_FLOOR),
    }
    assert len(merged.routes) == 3


def test_existing_adapter_acquisition_lower_bound_is_not_replaced_by_requested_revision():
    existing = successor_resources(
        state(), "run_probe", calls=6, max_output_tokens=40_000,
        check_seconds=(15,), remaining_check_seconds=(), probe_seconds=35,
        acquisition_pending=True,
    )
    merged = merge_resources(existing, resources(), model_floor=7, tool_floor=9)
    assert merged.model_calls == 7 and merged.tool_actions == 9
    assert merged.seconds == max(existing.seconds, 175)
    assert existing.output_ceilings in merged.output_options
    assert resources().output_ceilings in merged.output_options


def test_requested_revision_is_not_a_finish_or_mutation_override():
    with pytest.raises(ValueError, match="exploration tool"):
        resources("finish_task")
