"""Pure monetary/time envelopes for already eligible ordinary-runner actions."""

from __future__ import annotations

from dataclasses import dataclass, replace

from patchloop.dev.completion_budget import CompletionRoute, CompletionState, CompletionStep
from patchloop.dev.cost import FINALIZATION_OUTPUT_FLOOR, recovery_successor_output_ceilings

FOLLOWUP_SECONDS = 30
CHECK_OVERHEAD_SECONDS = 5


@dataclass(frozen=True)
class RecoveryResources:
    output_ceilings: tuple[int, ...]
    seconds: float
    failure_recovery: bool
    routes: tuple[CompletionRoute, ...] = ()
    adapter_reason: str | None = None
    physical_model_floor: int | None = None
    physical_tool_floor: int | None = None
    additional_output_options: tuple[tuple[int, ...], ...] = ()

    @property
    def model_calls(self) -> int | None:
        values = [route.model_calls for route in self.routes]
        if self.physical_model_floor is not None:
            values.append(self.physical_model_floor)
        return max(values, default=None)

    @property
    def tool_actions(self) -> int | None:
        values = [route.tool_actions for route in self.routes]
        if self.physical_tool_floor is not None:
            values.append(self.physical_tool_floor)
        return max(values, default=None)

    @property
    def output_options(self) -> tuple[tuple[int, ...], ...]:
        """Retain every funding alternative, including adapters without step routes."""
        return tuple(dict.fromkeys((self.output_ceilings, *self.additional_output_options,
                                    *(route.output_ceilings for route in self.routes))))


def requested_revision_resources(
    state: CompletionState, tool: str, *, max_output_tokens: int,
    check_seconds: tuple[float, ...], probe_seconds: float,
    optional_check_seconds: float = 0, test_comparison: bool = False,
) -> RecoveryResources:
    """Reserve one requested revision after exploration, without creating an obligation.

    The runner supplies the current-diff request and excludes special gates. An
    optional caller/test read cannot promise an edit anchor; all original replays
    and checks invalidated by the future edit still belong to its completion path.
    """
    if tool not in {"read_file", "search_files", "search_history", "run_probe", "run_tests"}:
        raise ValueError(f"not a requested-revision exploration tool: {tool}")
    route, = ordinary_completion_routes(
        replace(state, requires_mutation=True), tool, max_output_tokens=max_output_tokens,
        check_seconds=check_seconds, remaining_check_seconds=check_seconds,
        probe_seconds=probe_seconds, preserve_read_anchor=True,
    )
    if tool == "run_tests":
        executions = 2 if test_comparison else 1
        route = replace(route, current=replace(
            route.current, role="selected_test", tool_actions=executions,
            execution_seconds=optional_check_seconds * executions,
        ))
    route = replace(route, name="requested_revision")
    return RecoveryResources(route.output_ceilings, route.seconds(FOLLOWUP_SECONDS), False,
                             (route,))


def merge_resources(
    existing: RecoveryResources, requested: RecoveryResources, *,
    model_floor: int = 0, tool_floor: int = 0,
) -> RecoveryResources:
    """Preserve independent lower bounds using maxima, never concatenate their work."""
    options = tuple(dict.fromkeys((*existing.output_options, *requested.output_options)))
    primary = max(options, key=lambda ceilings: (len(ceilings), sum(ceilings)))
    routes = tuple(dict.fromkeys((*existing.routes, *requested.routes)))
    return RecoveryResources(
        output_ceilings=primary, seconds=max(existing.seconds, requested.seconds),
        failure_recovery=existing.failure_recovery or requested.failure_recovery,
        routes=routes, adapter_reason=existing.adapter_reason or requested.adapter_reason,
        physical_model_floor=max(
            model_floor, existing.model_calls or 0, requested.model_calls or 0),
        physical_tool_floor=max(
            tool_floor, existing.tool_actions or 0, requested.tool_actions or 0),
        additional_output_options=tuple(option for option in options if option != primary),
    )


def ordinary_route_supported(
    state: CompletionState, tool: str, *, acquisition_pending=False,
    test_edit=False, test_comparison=False,
) -> bool:
    """Use the same adapter boundary for eligibility and resource construction."""
    return not (
        acquisition_pending or test_edit or test_comparison and tool == "run_tests"
        or tool in {"run_probe", "observe_original"} and not state.path_diagnosis_pending
        or state.observation_correction_pending or state.helper_correction_pending
        or state.test_comparison_pending or tool == "run_tests"
        or (state.reproduction_case_count and not (
            state.early_replay_reusable and state.pending_reproduction_count == 0
            and state.early_reproduction_count == state.reproduction_case_count)))


def ordinary_completion_routes(
    state: CompletionState, tool: str, *, max_output_tokens: int,
    check_seconds: tuple[float, ...], remaining_check_seconds: tuple[float, ...],
    probe_seconds: float, protect_failure: bool = False,
    preserve_read_anchor: bool = False,
) -> tuple[CompletionRoute, ...]:
    """Enumerate ordinary success and one later public-failure revision.

    A host replay/check consumes a tool and execution time, never a response.
    The public-check failure path can reuse one automatic registered recheck;
    the early original-failure path reaches revision before running public checks.
    These alternatives are not concatenated. Original-failure recovery also
    includes the alternative in which the new candidate needs path diagnosis.
    """
    floor = min(FINALIZATION_OUTPUT_FLOOR, max_output_tokens)

    def model(role, seconds=0):
        return CompletionStep(role, output_tokens=(max_output_tokens if role == "repair"
                                                    else floor), execution_seconds=seconds)

    def host(role, seconds):
        return CompletionStep(role, model_call=False, execution_seconds=seconds)

    def replays():
        return [host("original_replay", probe_seconds)
                for _ in range(state.reproduction_case_count)]

    def checks(durations, *, automatic=False):
        durations = sorted(durations, reverse=True)
        return [(host("registered_recheck", seconds) if automatic and index == 0
                 else model("public_check", seconds))
                for index, seconds in enumerate(durations)]

    role = {"replace_text": "repair", "run_check": "public_check",
            "run_probe": "diagnosis", "observe_original": "diagnosis",
            "finish_task": "finish", "stop_task": "stop"}.get(tool, "source_read")
    current = model(role, probe_seconds if tool in {"run_probe", "observe_original"}
                    else max(check_seconds, default=0) if tool == "run_check" else 0)
    if tool == "stop_task":
        return (CompletionRoute("stop", current, ()),)
    future = []
    if state.path_diagnosis_pending and state.path_request_correction_available:
        # A rejected diagnostic request uses a response/action but no target execution.
        if tool == "run_probe":
            current = model("diagnostic_request_rejection")
            future.append(model("diagnostic_request_correction", probe_seconds))
        else:
            future.append(model("diagnostic_request_rejection"))
    if state.path_diagnosis_pending and tool != "run_probe":
        future.append(model("diagnosis", probe_seconds))
    future_repair = state.requires_mutation and tool != "replace_text"
    if future_repair:
        if not state.anchor_available and (tool not in {"read_file", "search_files"}
                                           or preserve_read_anchor):
            future.append(model("source_anchor"))
        future.append(model("repair"))
    mutation = future_repair or tool == "replace_text"
    if mutation:
        future.extend(replays())
        future.extend(checks(check_seconds, automatic=(state.automatic_recheck
                                                       and state.current_recheck_eligible)))
    else:
        durations = sorted(remaining_check_seconds, reverse=True)
        if tool == "run_check" and durations:
            # The selected remaining check is the current action, not a second successor.
            durations = durations[1:]
        future.extend(checks(durations))
        future.extend(host("original_replay", probe_seconds)
                      for _ in range(state.pending_reproduction_count))
    if tool != "finish_task":
        future.append(model("finish"))
    mandatory = CompletionRoute("required_completion", current, tuple(future))
    routes = [mandatory]
    if not protect_failure or tool == "finish_task":
        return tuple(routes)

    all_steps = [current, *future]
    repair_index = next((i for i, step in enumerate(all_steps) if step.role == "repair"), None)
    if state.reproduction_case_count and repair_index is not None:
        end = repair_index + 1
        while end < len(all_steps) and not all_steps[end].model_call:
            end += 1
        # A failed early replay precedes any remaining model-requested checks.
        # A prior known check may already have passed its automatic recheck after
        # this edit. Original failure alone cannot renew that check-failure credit.
        revision = [model("failure_source_read"), model("repair"), *replays(),
                    *checks(check_seconds),
                    model("finish")]
        steps = [*all_steps[:end], *revision]
        routes.append(CompletionRoute("original_failure_revision", steps[0], tuple(steps[1:]),
                                      speculative_failure=True))
        diagnostic_revision = [model("failure_diagnostic_request_rejection"),
                               model("failure_path_diagnosis", probe_seconds), *revision]
        diagnosed = [*all_steps[:end], *diagnostic_revision]
        routes.append(CompletionRoute("original_failure_diagnosis_revision", diagnosed[0],
                                      tuple(diagnosed[1:]), speculative_failure=True))
    if check_seconds:
        # The worst public failure is last. The accepted next edit reruns that
        # known check automatically when enabled; other invalidated checks need calls.
        prefix = [step for step in all_steps if step.role != "finish"]
        revision = [model("failure_source_read"), model("repair"), *replays(),
                    *checks(check_seconds, automatic=state.automatic_recheck), model("finish")]
        steps = [*prefix, *revision]
        routes.append(CompletionRoute("public_failure_revision", steps[0], tuple(steps[1:]),
                                      speculative_failure=True))
    return tuple(routes)


def successor_resources(
    state: CompletionState, tool: str, *, calls: int, max_output_tokens: int,
    check_seconds: tuple[float, ...], remaining_check_seconds: tuple[float, ...],
    probe_seconds: float, optional_check_seconds: float = 0,
    acquisition_pending: bool = False, test_edit: bool = False,
    protect_failure: bool = False, test_comparison: bool = False,
    preserve_pending_diagnosis: bool = False,
    ordinary_routes: bool = False, preserve_read_anchor: bool = False,
) -> RecoveryResources:
    """Reserve a successful route and at most one available public-failure revision.

    The caller supplies the existing call forecast and grants recovery only when
    physical model/tool/edit capacity exists. This function grants no tool access,
    mutates no counters, and never treats a reserve as verification evidence.
    """
    supported = ordinary_route_supported(
        state, tool, acquisition_pending=acquisition_pending,
        test_edit=test_edit, test_comparison=test_comparison)
    if ordinary_routes and supported:
        routes = ordinary_completion_routes(
            state, tool, max_output_tokens=max_output_tokens, check_seconds=check_seconds,
            remaining_check_seconds=remaining_check_seconds, probe_seconds=probe_seconds,
            protect_failure=protect_failure, preserve_read_anchor=preserve_read_anchor,
        )
        # The ordinary failure alternatives have the same repair roles; the longer
        # one dominates output cost. Keep each path so physical/time maxima remain auditable.
        largest = max(routes, key=lambda route: (route.model_calls, sum(route.output_ceilings)))
        return RecoveryResources(largest.output_ceilings,
                                 max(route.seconds(FOLLOWUP_SECONDS) for route in routes),
                                 any(route.speculative_failure for route in routes), routes)
    if tool == "stop_task":
        return RecoveryResources((), 0, False)
    editing = tool == "replace_text"
    future_repair = state.requires_mutation and not editing or test_edit
    repairs = int(future_repair)
    preparation = int(future_repair and not state.anchor_available
                      and (tool not in {"read_file", "search_files"}
                           or preserve_pending_diagnosis))
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
    if preserve_pending_diagnosis:
        # Optional caller/test reads leave both the original diagnostic and a
        # missing current-source anchor ahead. A rejected request executes no probe.
        replays += 1
    if failure:
        checks += all_checks
        replays += cases
    return RecoveryResources(outputs, checks + replays * probe_seconds
                             + FOLLOWUP_SECONDS * len(outputs), failure,
                             adapter_reason="special_obligations" if ordinary_routes
                             else "legacy_forecast")
