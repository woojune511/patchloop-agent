"""Pure call-budget forecasts for completion and mutation failure paths.

Inputs are a snapshot of public workflow/resource state. These functions perform
no I/O and neither select tools nor admit provider cost; the runner owns those
execution decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CompletionState:
    check_count: int
    remaining_check_count: int
    unused_check_count: int
    unrun_recoverable_check: bool
    requires_mutation: bool
    anchor_available: bool
    remaining_mutations: int
    mutation_retry_available: bool
    repair_read_credit: bool = False


@dataclass(frozen=True)
class CompletionBudget:
    minimum: int
    protected: int
    future_check_failures: int
    mutation_retry_reserve: int
    check_recovery_reserve: int
    current_read_reserve: int


def completion_budget(state: CompletionState) -> CompletionBudget:
    """Count a completion path and its bounded failures without assuming check order.

    A protected failed check may occur last, require one inspection and one repair,
    and invalidate every earlier PASS. Its worst-case incremental cost is N + 2.
    IDs remain eligibility evidence; no cheap declaration-order subset is selected.
    """

    if state.requires_mutation:
        minimum = int(not state.anchor_available) + 1 + state.check_count + 1
        future_failures = min(
            max(0, state.remaining_mutations - 1), state.unused_check_count
        )
    else:
        minimum = state.remaining_check_count + 1
        future_failures = (
            min(state.remaining_mutations, state.unused_check_count)
            if state.unrun_recoverable_check
            else 0
        )
    current_read = int(
        state.requires_mutation and state.anchor_available and state.repair_read_credit
    )
    mutation_retry = 2 * int(
        state.mutation_retry_available
        and (state.requires_mutation or future_failures > 0)
    )
    check_recovery = future_failures * (state.check_count + 2)
    return CompletionBudget(
        minimum=minimum,
        protected=minimum + current_read + mutation_retry + check_recovery,
        future_check_failures=future_failures,
        mutation_retry_reserve=mutation_retry,
        check_recovery_reserve=check_recovery,
        current_read_reserve=current_read,
    )


def mutation_attempt_budget(state: CompletionState) -> CompletionBudget:
    """Protect the offered attempt, including its first rejection, not just success.

    Evidence admission remains separate. Selecting the immediate edit for this
    forecast excludes an optional read before it, but retains the retry allowance.
    """
    return completion_budget(replace(
        state, requires_mutation=True, anchor_available=True, repair_read_credit=False,
    ))
