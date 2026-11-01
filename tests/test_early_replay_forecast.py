"""Small independent path controls for early replay and finish-result reuse."""

from dataclasses import replace
from functools import cache

import pytest

from patchloop.dev.completion_budget import CompletionState, completion_budget


def _state(*, checks=1, edits=3, retry=True, automatic=True, current_failure=False):
    return CompletionState(
        check_count=checks, remaining_check_count=checks,
        unused_check_count=checks - int(current_failure),
        unrun_recoverable_check=checks > int(current_failure),
        requires_mutation=True, anchor_available=True, remaining_mutations=edits,
        mutation_retry_available=retry, automatic_recheck=automatic,
        current_recheck_eligible=automatic and current_failure,
        repair_read_credit=current_failure,
        reproduction_case_count=1, early_reproduction_count=1,
        early_replay_reusable=True,
    )


def _longest_paths(*, checks, edits, retry, automatic, early, current_failure=False):
    """Enumerate bounded public outcomes, independently of forecast arithmetic.

    A registered check can fail once; one original replay can fail; one mutation
    can be rejected. Host replay/recheck actions consume no model call. Return
    separate longest model and tool paths, rather than assuming their maxima
    belong to the same sequence.
    """
    all_checks = (1 << checks) - 1

    def add(cost, rest):
        return cost[0] + rest[0], cost[1] + rest[1]

    def longest(paths):
        return max(p[0] for p in paths), max(p[1] for p in paths)

    @cache
    def visit(passed, unused, remaining, edit, read, reject, original, recheck):
        if read:
            return add((1, 1), visit(
                passed, unused, remaining, edit, False, reject, original, recheck,
            ))
        if edit:
            assert remaining > 0
            paths = []
            if reject:
                # A rejected edit preserves capacity and needs a fresh anchor read.
                paths.append(add((1, 1), visit(
                    passed, unused, remaining, True, True, False, original, recheck,
                )))
            # The accepted edit invalidates checks and prior replay evidence.
            initial_passed = (1 << recheck) if automatic and recheck >= 0 else 0
            cost = (1, 1 + int(early) + int(automatic and recheck >= 0))
            paths.append(add(cost, visit(
                initial_passed, unused, remaining - 1, False, False,
                reject, original, -1,
            )))
            if early and original and remaining > 1:
                # Failure is known before inference, so no failed finish occurs.
                # A registered automatic recheck still runs after the replay.
                paths.append(add(cost, visit(
                    initial_passed, unused, remaining - 1, True, True,
                    reject, False, -1,
                )))
            return longest(paths)
        if passed != all_checks:
            paths = []
            for index in range(checks):
                bit = 1 << index
                if passed & bit:
                    continue
                paths.append(add((1, 1), visit(
                    passed | bit, unused, remaining, False, False,
                    reject, original, -1,
                )))
                if unused & bit and remaining:
                    paths.append(add((1, 1), visit(
                        passed, unused & ~bit, remaining, True, True,
                        reject, original, index,
                    )))
            return longest(paths)
        if early:
            return 1, 1  # Finish reuses the successful same-diff early result.
        paths = [(1, 2)]  # One finish call and one host replay action.
        if original and remaining:
            paths.append(add((1, 2), visit(
                passed, unused, remaining, True, True, reject, False, -1,
            )))
        return longest(paths)

    return visit(
        0, all_checks ^ int(current_failure), edits, True, current_failure,
        retry, True, 0 if current_failure else -1,
    )


@pytest.mark.parametrize("early", [False, True])
@pytest.mark.parametrize("checks,edits,retry,automatic,current_failure", [
    (0, 2, False, False, False),
    (0, 2, True, False, False),
    (1, 1, True, True, False),
    (1, 2, False, True, False),
    (1, 3, True, False, False),
    (1, 3, True, True, False),
    (2, 4, True, True, False),
    (2, 3, True, True, True),
])
def test_forecast_covers_bounded_early_and_delayed_paths(
    early, checks, edits, retry, automatic, current_failure,
):
    state = _state(checks=checks, edits=edits, retry=retry, automatic=automatic,
                   current_failure=current_failure)
    if not early:
        state = replace(state, early_reproduction_count=0, early_replay_reusable=False)
    expected_calls, expected_tools = _longest_paths(
        checks=checks, edits=edits, retry=retry, automatic=automatic,
        early=early, current_failure=current_failure,
    )
    budget = completion_budget(state)
    assert budget.protected >= expected_calls
    assert budget.protected_tool_actions >= expected_tools


def test_original_pilot_removes_only_the_unreachable_failed_finish_action():
    state = _state(edits=4)
    early = completion_budget(state)
    delayed = completion_budget(replace(state, early_replay_reusable=False))
    assert (early.minimum, early.minimum_tool_actions) == (3, 4)
    assert (early.protected, early.protected_tool_actions) == (10, 14)
    assert (delayed.protected, delayed.protected_tool_actions) == (11, 15)
    assert _longest_paths(checks=1, edits=4, retry=True, automatic=True, early=True) == (
        early.protected, early.protected_tool_actions,
    )
    assert early.mutation_retry_reserve == delayed.mutation_retry_reserve == 2
    assert early.check_recovery_tool_actions == delayed.check_recovery_tool_actions == 4


@pytest.mark.parametrize("changes", [
    {"pending_reproduction_count": 1},  # Deferred early work still reaches finish.
    {"reproduction_case_count": 2},  # One case is not covered by early execution.
    {"early_reproduction_count": 0},  # Unacquired/legacy cases retain fallback.
    {"early_replay_reusable": False},  # Unknown, unhealthy or changed conditions.
])
def test_pending_mixed_and_unverified_cases_keep_finish_failure_reserve(changes):
    state = replace(_state(edits=4), **changes)
    assert completion_budget(state) == completion_budget(
        replace(state, early_replay_reusable=False),
    )


def test_reused_current_result_without_an_edit_reserves_only_finish():
    state = replace(_state(), requires_mutation=False, remaining_check_count=0,
                    unrun_recoverable_check=False)
    budget = completion_budget(state)
    assert (budget.minimum, budget.protected) == (1, 1)
    assert (budget.minimum_tool_actions, budget.protected_tool_actions) == (1, 1)
