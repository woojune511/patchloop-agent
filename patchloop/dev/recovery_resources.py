"""Pure monetary/time envelopes for already eligible ordinary-runner actions."""

from __future__ import annotations

from dataclasses import dataclass

from patchloop.dev.completion_budget import CompletionState
from patchloop.dev.cost import recovery_successor_output_ceilings

FOLLOWUP_SECONDS = 30
CHECK_OVERHEAD_SECONDS = 5


@dataclass(frozen=True)
class RecoveryResources:
    output_ceilings: tuple[int, ...]
    seconds: float
    failure_recovery: bool


def successor_resources(
    state: CompletionState, tool: str, *, calls: int, max_output_tokens: int,
    check_seconds: tuple[float, ...], remaining_check_seconds: tuple[float, ...],
    probe_seconds: float, optional_check_seconds: float = 0,
    acquisition_pending: bool = False, test_edit: bool = False,
    protect_failure: bool = False, test_comparison: bool = False,
) -> RecoveryResources:
    """Reserve a successful route and at most one available public-failure revision.

    The caller supplies the existing call forecast and grants recovery only when
    physical model/tool/edit capacity exists. This function grants no tool access,
    mutates no counters, and never treats a reserve as verification evidence.
    """
    if tool == "stop_task":
        return RecoveryResources((), 0, False)
    editing = tool == "replace_text"
    future_repair = state.requires_mutation and not editing or test_edit
    repairs = int(future_repair)
    preparation = int(future_repair and not state.anchor_available
                      and tool not in {"read_file", "search_files"})
    failure = bool(protect_failure and tool != "finish_task")
    if failure:
        # One read, one repair and new checks. A known failed check is replayed
        # by the host when configured; its execution time is still reserved.
        check_failure_only = (state.check_count > 0 and not state.reproduction_case_count
                              and not acquisition_pending)
        calls += 2 + state.check_count - int(state.automatic_recheck and check_failure_only)
        repairs += 1
        preparation += 1
    outputs = recovery_successor_output_ceilings(
        calls=calls, max_output_tokens=max_output_tokens,
        repair_calls=repairs, preparation_calls=preparation,
    )
    all_checks = sum(check_seconds)
    checks = all_checks if future_repair or editing else sum(remaining_check_seconds)
    if tool == "run_check" and state.requires_mutation:
        checks += max(check_seconds, default=0)
    if tool == "run_tests":
        checks += optional_check_seconds * (2 if test_comparison else 1)
    cases = state.reproduction_case_count
    replays = cases if future_repair or editing else state.pending_reproduction_count
    if test_edit:
        # Adding a test is followed by the paired test and a source repair.
        # Each mutation replays originals; the first can also replay its known
        # failing registered check before the comparison request.
        checks += 2 * optional_check_seconds
        checks += max(check_seconds, default=0) if state.current_recheck_eligible else 0
        replays += cases
    if acquisition_pending and tool not in {"finish_task", "stop_task"}:
        # A new original needs a baseline comparison plus candidate execution,
        # and one replay after the future edit; no saved observation is assumed.
        replays += 3
        cases += 1
    elif tool in {"run_probe", "observe_original"}:
        replays += 1
    if failure:
        checks += all_checks
        replays += cases
    return RecoveryResources(outputs, checks + replays * probe_seconds
                             + FOLLOWUP_SECONDS * len(outputs), failure)
