"""Pure resource forecasts for the opt-in original-call repair cycle.

Provider admission and execution remain owned by the caller. Future output
reserves fund bounded opportunities; they do not promise a useful model response
or change the ordinary/correction response ceilings.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CycleLimits:
    model_tools: int = 24
    helper_probes: int = 2
    original_requests: int = 1
    accepted_edits: int = 3
    future_diagnostic_output: int = 8_192
    future_edit_output: int = 8_192
    final_response_output: int = 128
    original_recheck_seconds: int = 60
    final_public_seconds: int = 390
    acceptance_seconds: int = 390
    final_public_actions: int = 11

    @property
    def host_original_actions(self) -> int:
        # Fresh baseline, optional seed observation, and each accepted edit.
        return self.accepted_edits + self.original_requests + 1


DEFAULT_LIMITS = CycleLimits()


def regression_opportunity(*, original_feedback, regression_feedback, initial,
                           allow_inspection=True, **options):
    """Reopen the bounded revision only after an observed public failure."""
    failed = (original_feedback is not None and original_feedback.get("status") == "failed"
              or regression_feedback is not None and regression_feedback.get("status") == "failed")
    if not initial and not failed:
        options["edits_remaining"] = 0
    return cycle_opportunity(allow_inspection=allow_inspection and failed, **options)


@dataclass(frozen=True)
class CycleOpportunity:
    allowed: frozenset[str]
    max_parallel_reads: int
    successor_output_ceilings: tuple[int, ...]
    continuation_reserved: bool = False

    @property
    def successor_calls(self) -> int:
        return len(self.successor_output_ceilings)

    def public(self) -> dict[str, object]:
        return {
            "allowed_tools": sorted(self.allowed),
            "max_parallel_reads": self.max_parallel_reads,
            "reserved_successor_calls": self.successor_calls,
            "reserved_successor_output_tokens": list(self.successor_output_ceilings),
            "repair_continuation_reserved": self.continuation_reserved,
            "reservation_scope": "Minimum future funding, not response ceilings or repair credit.",
        }


def cycle_opportunity(
    *, normal_remaining: int, tool_remaining: int, probes_remaining: int,
    edits_remaining: int, original_remaining: int = 1,
    correction: bool = False, allow_inspection: bool = True,
    allow_probe: bool = True, allow_continuation: bool = True,
    limits: CycleLimits = DEFAULT_LIMITS,
) -> CycleOpportunity:
    """Keep a response/action after every offered edit to consume its recheck.

An inspection/probe also leaves an edit and a final response. When another edit
could follow the currently offered edit, reserve one diagnostic response, one
repair response and one final response. Cost admission can release that optional
continuation reserve, then inspection/probe, but never an edit's final response.
Protocol correction adds only the already-counted correction response; callers
retain the original global response/action/probe/edit counters.
"""
    responses = normal_remaining + int(correction)
    if responses < 1 or tool_remaining < 1:
        return CycleOpportunity(frozenset(), 0, ())
    allowed = {"stop_task"}
    reads = 0
    successors: tuple[int, ...] = ()
    if edits_remaining <= 0:
        return CycleOpportunity(frozenset(allowed), reads, successors)
    if responses >= 2 and tool_remaining >= 2:
        allowed.add("replace_text")
        successors = (limits.final_response_output,)
    if responses >= 3 and tool_remaining >= 3:
        if allow_inspection:
            reads = min(4, tool_remaining - 2)
            allowed.update({"read_file", "search_files"})
        if allow_probe and probes_remaining > 0:
            allowed.add("run_probe")
        if allow_probe and original_remaining > 0:
            allowed.add("recheck_original")
        if reads or allowed.intersection({"run_probe", "recheck_original"}):
            successors = (limits.future_edit_output, limits.final_response_output)
    continuation = (allow_continuation and edits_remaining > 1
                    and responses >= 4 and tool_remaining >= 4)
    if continuation:
        successors = (limits.future_diagnostic_output, limits.future_edit_output,
                      limits.final_response_output)
    return CycleOpportunity(frozenset(allowed), reads, successors, continuation)
