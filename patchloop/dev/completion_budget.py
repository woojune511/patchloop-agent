"""Pure call-budget forecasts for completion and mutation failure paths.

Inputs are a snapshot of public workflow/resource state. These functions perform
no I/O and neither select tools nor admit provider cost; the runner owns those
execution decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CompletionStep:
    """One response, public tool action, or host execution on a forecast path."""

    role: str
    model_call: bool = True
    tool_actions: int = 1
    output_tokens: int = 0
    execution_seconds: float = 0


@dataclass(frozen=True)
class CompletionRoute:
    """A current action and its successors; all resource dimensions share these steps."""

    name: str
    current: CompletionStep
    successors: tuple[CompletionStep, ...]
    speculative_failure: bool = False
    adapter: str | None = None

    @property
    def model_calls(self) -> int:
        return sum(step.model_call for step in (self.current, *self.successors))

    @property
    def tool_actions(self) -> int:
        return sum(step.tool_actions for step in (self.current, *self.successors))

    @property
    def output_ceilings(self) -> tuple[int, ...]:
        return tuple(step.output_tokens for step in self.successors if step.model_call)

    def seconds(self, followup_seconds: float) -> float:
        # Current generation is admitted separately; current execution still must fit.
        return (sum(step.execution_seconds for step in (self.current, *self.successors))
                + followup_seconds * sum(step.model_call for step in self.successors))


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
    automatic_recheck: bool = False
    current_recheck_eligible: bool = False
    reproduction_case_count: int = 0
    pending_reproduction_count: int = 0
    early_reproduction_count: int = 0
    # The caller confirms healthy current evidence for every acquired original
    # and that post-edit early execution is available. Missing/unknown evidence
    # must retain the conservative finish-fallback forecast.
    early_replay_reusable: bool = False
    # A known observation conflict must be corrected on the unchanged base
    # before source repair. This is one real model request and probe execution,
    # separate from protocol-response recovery.
    observation_correction_pending: bool = False
    path_diagnosis_pending: bool = False
    path_preparation_available: bool = False
    path_request_correction_available: bool = False
    helper_correction_pending: bool = False
    test_comparison_pending: bool = False
    test_comparison_replay_count: int = 0


@dataclass(frozen=True)
class CompletionBudget:
    minimum: int
    protected: int
    future_check_failures: int
    mutation_retry_reserve: int
    check_recovery_reserve: int
    current_read_reserve: int
    minimum_tool_actions: int
    protected_tool_actions: int
    check_recovery_tool_actions: int


def completion_budget(state: CompletionState) -> CompletionBudget:
    """Count a completion path and its bounded failures without assuming check order.

    A protected failed check may occur last, require one inspection and one repair,
    and invalidate every earlier PASS. Its incremental cost is N + 2 tool actions.
    An enabled automatic recheck saves one model call, never its tool action.
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
    minimum_tools = minimum
    minimum -= int(
        state.automatic_recheck and state.current_recheck_eligible and state.requires_mutation
    )
    check_recovery_tools = future_failures * (state.check_count + 2)
    check_recovery = check_recovery_tools - future_failures * int(state.automatic_recheck)
    # Public-case replay runs after an edit or before finish, without another
    # model call. An edit invalidates every case; otherwise only stale cases need work.
    reproduction_actions = (
        state.reproduction_case_count if state.requires_mutation
        else state.pending_reproduction_count
    )
    protected = minimum + current_read + mutation_retry + check_recovery
    protected_tools = (minimum_tools + current_read + mutation_retry + check_recovery_tools
                       + (state.reproduction_case_count if future_failures
                          else reproduction_actions)
                       + future_failures * state.early_reproduction_count)
    # A deferred final replay consumes the finish request too. Healthy acquired
    # originals instead run after the edit; their same-diff result is reused at
    # finish, so that failure cannot consume an extra finish action. Keep the
    # fallback for mixed, pending/deferred or otherwise unverified coverage.
    early_failure = (
        state.early_replay_reusable
        and 0 < state.early_reproduction_count == state.reproduction_case_count
        and state.pending_reproduction_count == 0
    )
    # Protect read, repair, checks and replay recovery when an edit remains.
    # Compare against check failure instead of reserving impossible extra edits.
    spare_edits = state.remaining_mutations - int(state.requires_mutation)
    if spare_edits > 0 and state.reproduction_case_count:
        prior_failures = min(future_failures, spare_edits - 1)
        first_replays = state.reproduction_case_count if prior_failures else reproduction_actions
        if first_replays:
            recovery = state.check_count + 3 - int(early_failure)
            replay_mutation_retry = 2 * int(state.mutation_retry_available)
            protected = max(protected, minimum + current_read + replay_mutation_retry + recovery
                            + prior_failures * (state.check_count + 2
                                                - int(state.automatic_recheck)))
            protected_tools = max(
                protected_tools, minimum_tools + current_read + replay_mutation_retry
                + prior_failures * (state.check_count + 2 + state.early_reproduction_count)
                + first_replays
                + recovery + state.reproduction_case_count,
            )
    diagnosis = (int(state.observation_correction_pending) + int(state.path_diagnosis_pending)
                 + int(state.helper_correction_pending))
    # The same preparation read can acquire the required repair anchor or spend
    # an already protected current repair read. Reserve it only once. Otherwise
    # it remains optional: host-built path diagnostics need no extra source read.
    preparation = int(
        state.path_diagnosis_pending and state.path_preparation_available
        and not (state.requires_mutation and not state.anchor_available)
        and not current_read
    )
    request_correction = int(
        state.path_diagnosis_pending and state.path_request_correction_available
    )
    comparison_calls = int(state.test_comparison_pending)
    comparison_actions = (2 + state.test_comparison_replay_count) * comparison_calls
    return CompletionBudget(
        minimum=minimum + diagnosis + comparison_calls,
        protected=protected + diagnosis + preparation + request_correction + comparison_calls,
        future_check_failures=future_failures,
        mutation_retry_reserve=mutation_retry,
        check_recovery_reserve=check_recovery,
        current_read_reserve=current_read,
        minimum_tool_actions=(minimum_tools + reproduction_actions
                              + diagnosis + comparison_actions),
        protected_tool_actions=(protected_tools + diagnosis + preparation + request_correction
                                + comparison_actions),
        check_recovery_tool_actions=(check_recovery_tools
                                     + future_failures * state.early_reproduction_count),
    )


def mutation_attempt_budget(state: CompletionState) -> CompletionBudget:
    """Protect the offered attempt, including its first rejection, not just success.

    Evidence admission remains separate. Selecting the immediate edit for this
    forecast excludes an optional read before it, but retains the retry allowance.
    """
    return completion_budget(replace(
        state, requires_mutation=True, anchor_available=True, repair_read_credit=False,
    ))


def test_addition_budget(state: CompletionState) -> CompletionBudget:
    """Count a test edit, paired comparison, and the still-required source repair.

    The test edit consumes a real mutation slot and its automatic original replay.
    Its comparison consumes one model call and two sandbox actions. A diagnostic
    recheck may retire the earlier failure, so the next source edit cannot rely on
    that check's automatic-recheck saving.
    """
    successor = completion_budget(replace(
        state, requires_mutation=True, remaining_mutations=max(0, state.remaining_mutations - 1),
        current_recheck_eligible=False, test_comparison_pending=True,
        test_comparison_replay_count=state.early_reproduction_count,
    ))
    extra_actions = 1 + int(state.automatic_recheck and state.current_recheck_eligible)
    return replace(
        successor, minimum=successor.minimum + 1, protected=successor.protected + 1,
        minimum_tool_actions=successor.minimum_tool_actions + extra_actions,
        protected_tool_actions=successor.protected_tool_actions + extra_actions,
    )


def minimum_successor_calls(state: CompletionState, tool: str) -> int:
    """Bound successful successor model calls for an already eligible action.

    This is separate from physical model/tool admission and its protected recovery
    paths. A required source read must acquire its missing anchor; checks, edits
    and finish replays must succeed. Otherwise the runner reassesses the new state
    without a monetary recovery guarantee. Host replays consume tools, not calls.
    """
    if tool in {"finish_task", "stop_task"}:
        return 0
    if tool == "run_probe" and state.observation_correction_pending:
        return completion_budget(replace(state, observation_correction_pending=False)).minimum
    if tool == "run_probe" and state.path_diagnosis_pending:
        return completion_budget(replace(state, path_diagnosis_pending=False)).minimum
    if tool == "run_probe" and state.helper_correction_pending:
        return completion_budget(replace(state, helper_correction_pending=False)).minimum
    if tool == "run_tests" and state.test_comparison_pending:
        return completion_budget(replace(
            state, test_comparison_pending=False, test_comparison_replay_count=0,
        )).minimum
    if tool in {"read_file", "search_files"}:
        return completion_budget(replace(state, anchor_available=True)).minimum
    if tool in {"search_history", "run_probe", "run_tests", "observe_original"}:
        return completion_budget(state).minimum
    if tool == "replace_text":
        return mutation_attempt_budget(state).minimum - 1
    if tool == "run_check":
        if state.requires_mutation:
            # A diagnostic PASS cannot satisfy checks invalidated by the future
            # edit. It may also retire the failure that qualified for automatic
            # recheck, so do not carry that old credit into its successor.
            return completion_budget(replace(state, current_recheck_eligible=False)).minimum
        return max(0, completion_budget(state).minimum - 1)
    raise ValueError(f"unknown completion successor tool: {tool}")
