"""Pure contracts for the opt-in mechanical-friction successor.

This module separates visible-check execution from behavior, and projects one
bounded recovery for reasoning-only incomplete responses.  It performs no
workspace, provider, Docker, evaluator, or state mutation.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.contracts import Budget, EventType, RunEvent, Usage
from patchloop.errors import ContractError
from patchloop.util import sha256_json, sha256_text

CHECK_OUTCOME_SCHEMA = "registered-check-outcome-v2"
CHECK_OUTCOME_POLICY = "invocation-vs-behavior-v1"
INCOMPLETE_RECOVERY_SCHEMA = "reasoning-incomplete-recovery-v1"
INCOMPLETE_RECOVERY_POLICY = "reasoning-only-single-retry-split-reserved-v1"
INCOMPLETE_RECOVERY_OUTPUT_RESERVE = 2_048
INCOMPLETE_RECOVERY_MIN_PRIMARY_AND_RETRY = 4_096
COMPLETION_RESPONSE_RECOVERY_SCHEMA = "completion-response-recovery-v1"
COMPLETION_RESPONSE_RECOVERY_POLICY = "completion-response-single-shared-retry-v1"
COMPLETION_RESPONSE_RECOVERY_OUTPUT_RESERVE = 2_048
COMPLETION_RESPONSE_RECOVERY_MIN_PRIMARY_AND_RETRY = 4_096
_FAILURE_SUMMARY_LIMIT = 2_000


class RegisteredCheckOutcomeV2(BaseModel):
    """Typed public check result: invocation success is not behavior success."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["registered-check-outcome-v2"]
    policy_version: Literal["invocation-vs-behavior-v1"]
    check_id: str = Field(min_length=1)
    invocation_status: Literal["completed"]
    behavior_status: Literal["passed", "failed"]
    passed: bool
    correction_required: bool
    exit_code: int
    timed_out: bool
    truncated: bool
    failure_summary: str | None
    stdout_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    stderr_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_visible_only: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        expected_status = "passed" if self.passed else "failed"
        if self.behavior_status != expected_status:
            raise ValueError("registered check behavior status differs")
        if self.correction_required is self.passed:
            raise ValueError("registered check correction decision differs")
        if self.passed and self.failure_summary is not None:
            raise ValueError("passing registered check has failure summary")
        if not self.passed and not self.failure_summary:
            raise ValueError("failed registered check lacks failure summary")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("registered check outcome hash differs")
        return self


def project_registered_check_outcome(
    *,
    check_id: str,
    exit_code: int,
    passed: bool,
    timed_out: bool,
    truncated: bool,
    stdout: str,
    stderr: str,
    worktree_diff_hash: str,
) -> RegisteredCheckOutcomeV2:
    """Build a concise, public-only check outcome from an executed check."""

    if any(type(value) is not str for value in (check_id, stdout, stderr)):
        raise TypeError("registered check text fields must be exact strings")
    if type(exit_code) is not int or any(
        type(value) is not bool for value in (passed, timed_out, truncated)
    ):
        raise TypeError("registered check scalar fields are invalid")
    summary = None
    if not passed:
        candidate = stderr.strip() or stdout.strip()
        if not candidate:
            candidate = "timed out" if timed_out else f"exit code {exit_code}"
        summary = candidate[:_FAILURE_SUMMARY_LIMIT]
    body = {
        "schema_version": CHECK_OUTCOME_SCHEMA,
        "policy_version": CHECK_OUTCOME_POLICY,
        "check_id": check_id,
        "invocation_status": "completed",
        "behavior_status": "passed" if passed else "failed",
        "passed": passed,
        "correction_required": not passed,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "truncated": truncated,
        "failure_summary": summary,
        "stdout_hash": sha256_text(stdout),
        "stderr_hash": sha256_text(stderr),
        "worktree_diff_hash": worktree_diff_hash,
        "public_visible_only": True,
    }
    return RegisteredCheckOutcomeV2.model_validate({**body, "content_hash": sha256_json(body)})


class ReasoningIncompleteRecovery(BaseModel):
    """One exact request-mode projection inside the existing cumulative cap."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["reasoning-incomplete-recovery-v1"]
    policy_version: Literal["reasoning-only-single-retry-split-reserved-v1"]
    mode: Literal[
        "not-applicable",
        "primary-reserved",
        "primary-direct-low",
        "retry",
    ]
    phase_mode: Literal["exploration", "finalization"]
    source_event_sequence: int | None = Field(default=None, ge=1)
    source_event_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    configured_max_output_tokens: int = Field(ge=1)
    effective_max_output_tokens: int = Field(ge=1)
    reserved_retry_output_tokens: int = Field(ge=0)
    reasoning_effort: Literal["medium", "low"]
    retry_available_after_response: bool
    retry_already_consumed: bool
    requested_input_tokens: int = Field(ge=1)
    input_tokens_used: int = Field(ge=0)
    output_tokens_used: int = Field(ge=0)
    remaining_input_tokens: int = Field(ge=0)
    remaining_output_tokens: int = Field(ge=0)
    remaining_total_tokens: int = Field(ge=0)
    same_cumulative_budget: Literal[True]
    at_most_one_retry: Literal[True]
    previous_response_id_used: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.effective_max_output_tokens > self.configured_max_output_tokens:
            raise ValueError("incomplete recovery exceeds configured output ceiling")
        if self.effective_max_output_tokens > self.remaining_output_tokens:
            raise ValueError("incomplete recovery exceeds remaining output split")
        if (
            self.requested_input_tokens + self.effective_max_output_tokens
            > self.remaining_total_tokens
        ):
            raise ValueError("incomplete recovery exceeds remaining total split")
        if self.requested_input_tokens > self.remaining_input_tokens:
            raise ValueError("incomplete recovery exceeds remaining input split")
        if self.mode == "not-applicable":
            if self.phase_mode != "exploration" or self.reasoning_effort != "medium":
                raise ValueError("non-final recovery mode differs")
        elif self.mode == "primary-reserved":
            if (
                self.phase_mode != "finalization"
                or self.reserved_retry_output_tokens <= 0
                or self.reasoning_effort != "medium"
                or not self.retry_available_after_response
                or self.retry_already_consumed
            ):
                raise ValueError("primary reserved recovery mode differs")
        elif self.mode == "primary-direct-low":
            if (
                self.phase_mode != "finalization"
                or self.reserved_retry_output_tokens != 0
                or self.reasoning_effort != "low"
                or self.retry_available_after_response
            ):
                raise ValueError("direct-low recovery mode differs")
        elif (
            self.mode != "retry"
            or self.phase_mode != "finalization"
            or self.source_event_sequence is None
            or self.source_event_hash is None
            or self.reserved_retry_output_tokens != 0
            or self.reasoning_effort != "low"
            or self.retry_available_after_response
            or self.retry_already_consumed
        ):
            raise ValueError("reasoning retry mode differs")
        if self.mode != "retry" and (
            self.source_event_sequence is not None or self.source_event_hash is not None
        ):
            raise ValueError("primary recovery unexpectedly binds a source event")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("incomplete recovery projection hash differs")
        return self


def _primary_incomplete(event: RunEvent) -> bool:
    payload = event.payload
    return bool(
        event.type == EventType.MODEL_CALLED
        and payload.get("response_error_code") == "incomplete_response"
        and payload.get("response_incomplete_reason") == "max_output_tokens"
        and payload.get("lean_incomplete_recovery_mode") == "primary-reserved"
    )


def _reasoning_only_primary_incomplete(event: RunEvent) -> bool:
    payload = event.payload
    output_tokens = payload.get("output_tokens")
    return bool(
        _primary_incomplete(event)
        and type(output_tokens) is int
        and output_tokens > 0
        and payload.get("reasoning_output_tokens") == output_tokens
        and type(payload.get("lean_reserved_retry_output_tokens")) is int
        and payload["lean_reserved_retry_output_tokens"] > 0
        and payload.get("response_text_present") is False
        and payload.get("response_tool_call_count") == 0
    )


def project_reasoning_incomplete_recovery(
    *,
    phase_mode: Literal["exploration", "finalization"],
    events: tuple[RunEvent, ...] | list[RunEvent],
    usage: Usage,
    budget: Budget,
    requested_input_tokens: int,
    configured_max_output_tokens: int,
) -> ReasoningIncompleteRecovery:
    """Reserve or consume one retry without increasing any cumulative limit."""

    if type(usage) is not Usage or type(budget) is not Budget:
        raise TypeError("incomplete recovery requires exact usage and budget")
    if type(events) not in {tuple, list} or any(type(item) is not RunEvent for item in events):
        raise TypeError("incomplete recovery events must be exact RunEvent values")
    if budget.token_budget_schema_version != "cumulative-split-v1":
        raise ContractError("incomplete recovery requires cumulative-split-v1")
    if budget.max_cumulative_input_tokens is None or budget.max_cumulative_output_tokens is None:
        raise ContractError("incomplete recovery split limits are incomplete")
    remaining_input = budget.max_cumulative_input_tokens - usage.input_tokens
    remaining_output = budget.max_cumulative_output_tokens - usage.output_tokens
    remaining_total = budget.max_total_tokens - usage.input_tokens - usage.output_tokens
    if min(remaining_input, remaining_output, remaining_total) < 0:
        raise ContractError("incomplete recovery usage already exceeds its budget")
    if requested_input_tokens > remaining_input:
        raise ContractError("incomplete recovery cannot fund the exact input")
    fundable_output = min(
        configured_max_output_tokens,
        remaining_output,
        remaining_total - requested_input_tokens,
    )
    if fundable_output <= 0:
        raise ContractError("incomplete recovery cannot fund a positive response")

    retry_already_consumed = any(
        event.type == EventType.MODEL_CALLED
        and event.payload.get("lean_incomplete_recovery_mode") == "retry"
        for event in events
    )
    last_event = events[-1] if events else None
    if last_event is not None and _primary_incomplete(last_event):
        if not _reasoning_only_primary_incomplete(last_event):
            raise ContractError(
                "incomplete response contains output that is not eligible for recovery"
            )
        if retry_already_consumed:
            raise ContractError("reasoning-only incomplete retry was already consumed")
        source_reserve = int(last_event.payload["lean_reserved_retry_output_tokens"])
        mode = "retry"
        effective = min(source_reserve, fundable_output)
        reserve = 0
        effort = "low"
        retry_available = False
        source_sequence = last_event.sequence
        source_hash = sha256_json(last_event.model_dump(mode="json"))
    elif phase_mode == "exploration":
        mode = "not-applicable"
        effective = fundable_output
        reserve = 0
        effort = "medium"
        retry_available = False
        source_sequence = None
        source_hash = None
    else:
        available_output = min(
            remaining_output,
            remaining_total - requested_input_tokens,
        )
        call_capacity = (
            budget.max_model_calls is None or usage.model_calls + 1 < budget.max_model_calls
        )
        if (
            not retry_already_consumed
            and call_capacity
            and available_output >= INCOMPLETE_RECOVERY_MIN_PRIMARY_AND_RETRY
        ):
            mode = "primary-reserved"
            reserve = INCOMPLETE_RECOVERY_OUTPUT_RESERVE
            effective = min(
                configured_max_output_tokens,
                available_output - reserve,
            )
            effort = "medium"
            retry_available = True
        else:
            mode = "primary-direct-low"
            reserve = 0
            effective = fundable_output
            effort = "low"
            retry_available = False
        source_sequence = None
        source_hash = None

    body = {
        "schema_version": INCOMPLETE_RECOVERY_SCHEMA,
        "policy_version": INCOMPLETE_RECOVERY_POLICY,
        "mode": mode,
        "phase_mode": phase_mode,
        "source_event_sequence": source_sequence,
        "source_event_hash": source_hash,
        "configured_max_output_tokens": configured_max_output_tokens,
        "effective_max_output_tokens": effective,
        "reserved_retry_output_tokens": reserve,
        "reasoning_effort": effort,
        "retry_available_after_response": retry_available,
        "retry_already_consumed": retry_already_consumed,
        "requested_input_tokens": requested_input_tokens,
        "input_tokens_used": usage.input_tokens,
        "output_tokens_used": usage.output_tokens,
        "remaining_input_tokens": remaining_input,
        "remaining_output_tokens": remaining_output,
        "remaining_total_tokens": remaining_total,
        "same_cumulative_budget": True,
        "at_most_one_retry": True,
        "previous_response_id_used": False,
        "provider_calls_authorized": False,
    }
    return ReasoningIncompleteRecovery.model_validate({**body, "content_hash": sha256_json(body)})


class CompletionResponseRecovery(BaseModel):
    """One shared actionless/incomplete retry inside the original run caps."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["completion-response-recovery-v1"]
    policy_version: Literal["completion-response-single-shared-retry-v1"]
    mode: Literal[
        "not-applicable",
        "primary-reserved",
        "primary-direct-low",
        "retry-actionless",
        "retry-reasoning-incomplete",
    ]
    phase_mode: Literal["exploration", "finalization"]
    completion_lane_active: bool
    source_response_kind: Literal["actionless", "reasoning-only-incomplete"] | None
    source_event_sequence: int | None = Field(default=None, ge=1)
    source_event_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    configured_max_output_tokens: int = Field(ge=1)
    effective_max_output_tokens: int = Field(ge=1)
    reserved_retry_output_tokens: int = Field(ge=0)
    reasoning_effort: Literal["medium", "low"]
    action_only_required: bool
    retry_available_after_response: bool
    retry_already_consumed: bool
    requested_input_tokens: int = Field(ge=1)
    input_tokens_used: int = Field(ge=0)
    output_tokens_used: int = Field(ge=0)
    model_calls_used: int = Field(ge=0)
    remaining_input_tokens: int = Field(ge=0)
    remaining_output_tokens: int = Field(ge=0)
    remaining_total_tokens: int = Field(ge=0)
    remaining_model_calls: int | None = Field(default=None, ge=1)
    same_cumulative_budget: Literal[True]
    at_most_one_shared_retry: Literal[True]
    previous_response_id_used: Literal[False]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.effective_max_output_tokens > self.configured_max_output_tokens:
            raise ValueError("completion recovery exceeds configured output ceiling")
        if self.effective_max_output_tokens > self.remaining_output_tokens:
            raise ValueError("completion recovery exceeds remaining output split")
        if self.requested_input_tokens > self.remaining_input_tokens:
            raise ValueError("completion recovery exceeds remaining input split")
        if (
            self.requested_input_tokens + self.effective_max_output_tokens
            > self.remaining_total_tokens
        ):
            raise ValueError("completion recovery exceeds remaining total split")
        retry_mode = self.mode in {
            "retry-actionless",
            "retry-reasoning-incomplete",
        }
        if self.mode == "not-applicable":
            if (
                self.completion_lane_active
                or self.phase_mode != "exploration"
                or self.reasoning_effort != "medium"
                or self.action_only_required
                or self.reserved_retry_output_tokens != 0
                or self.retry_available_after_response
            ):
                raise ValueError("non-completion recovery mode differs")
        elif self.mode == "primary-reserved":
            if (
                not self.completion_lane_active
                or self.reserved_retry_output_tokens <= 0
                or self.reasoning_effort != "medium"
                or not self.action_only_required
                or not self.retry_available_after_response
                or self.retry_already_consumed
            ):
                raise ValueError("completion primary reserved mode differs")
            if (
                self.remaining_input_tokens < self.requested_input_tokens * 2
                or self.remaining_total_tokens
                < (
                    self.requested_input_tokens * 2
                    + self.effective_max_output_tokens
                    + self.reserved_retry_output_tokens
                )
            ):
                raise ValueError("completion primary lacks retry input headroom")
        elif self.mode == "primary-direct-low":
            if (
                not self.completion_lane_active
                or self.reserved_retry_output_tokens != 0
                or self.reasoning_effort != "low"
                or not self.action_only_required
                or self.retry_available_after_response
            ):
                raise ValueError("completion direct-low mode differs")
        elif not retry_mode or (
            not self.completion_lane_active
            or self.source_event_sequence is None
            or self.source_event_hash is None
            or self.source_response_kind is None
            or self.reserved_retry_output_tokens != 0
            or self.reasoning_effort != "low"
            or not self.action_only_required
            or self.retry_available_after_response
            or self.retry_already_consumed
        ):
            raise ValueError("completion retry mode differs")
        expected_source_kind = {
            "retry-actionless": "actionless",
            "retry-reasoning-incomplete": "reasoning-only-incomplete",
        }.get(self.mode)
        if retry_mode and self.source_response_kind != expected_source_kind:
            raise ValueError("completion retry source kind differs")
        if not retry_mode and (
            self.source_response_kind is not None
            or self.source_event_sequence is not None
            or self.source_event_hash is not None
        ):
            raise ValueError("completion primary unexpectedly binds a source response")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("completion recovery projection hash differs")
        return self


def _completion_primary(event: RunEvent) -> bool:
    return bool(
        event.type == EventType.MODEL_CALLED
        and event.payload.get("lean_completion_recovery_mode") == "primary-reserved"
        and type(event.payload.get("lean_reserved_completion_retry_output_tokens")) is int
        and event.payload["lean_reserved_completion_retry_output_tokens"] > 0
    )


def _completion_primary_source_kind(
    event: RunEvent,
) -> Literal["actionless", "reasoning-only-incomplete"] | None:
    payload = event.payload
    if not _completion_primary(event):
        return None
    if payload.get("response_error_code") == "incomplete_response":
        output_tokens = payload.get("output_tokens")
        if (
            payload.get("response_incomplete_reason") == "max_output_tokens"
            and type(output_tokens) is int
            and output_tokens > 0
            and payload.get("reasoning_output_tokens") == output_tokens
            and payload.get("response_text_present") is False
            and payload.get("response_tool_call_count") == 0
        ):
            return "reasoning-only-incomplete"
        raise ContractError(
            "incomplete response contains output that is not eligible for completion recovery"
        )
    if (
        payload.get("response_error_code") is None
        and payload.get("lean_response_done") is False
        and payload.get("response_tool_call_count") == 0
    ):
        return "actionless"
    return None


def project_completion_response_recovery(
    *,
    phase_mode: Literal["exploration", "finalization"],
    completion_lane_active: bool,
    events: tuple[RunEvent, ...] | list[RunEvent],
    usage: Usage,
    budget: Budget,
    requested_input_tokens: int,
    configured_max_output_tokens: int,
) -> CompletionResponseRecovery:
    """Project one shared completion retry without increasing any run limit."""

    if type(usage) is not Usage or type(budget) is not Budget:
        raise TypeError("completion recovery requires exact usage and budget")
    if type(completion_lane_active) is not bool:
        raise TypeError("completion recovery lane flag must be an exact bool")
    if type(events) not in {tuple, list} or any(type(item) is not RunEvent for item in events):
        raise TypeError("completion recovery events must be exact RunEvent values")
    if budget.token_budget_schema_version != "cumulative-split-v1":
        raise ContractError("completion recovery requires cumulative-split-v1")
    if budget.max_cumulative_input_tokens is None or budget.max_cumulative_output_tokens is None:
        raise ContractError("completion recovery split limits are incomplete")
    remaining_input = budget.max_cumulative_input_tokens - usage.input_tokens
    remaining_output = budget.max_cumulative_output_tokens - usage.output_tokens
    remaining_total = budget.max_total_tokens - usage.input_tokens - usage.output_tokens
    remaining_model_calls = (
        None if budget.max_model_calls is None else budget.max_model_calls - usage.model_calls
    )
    if min(remaining_input, remaining_output, remaining_total) < 0:
        raise ContractError("completion recovery usage already exceeds its budget")
    if remaining_model_calls is not None and remaining_model_calls <= 0:
        raise ContractError("completion recovery cannot fund another model call")
    if requested_input_tokens > remaining_input:
        raise ContractError("completion recovery cannot fund the exact input")
    fundable_output = min(
        configured_max_output_tokens,
        remaining_output,
        remaining_total - requested_input_tokens,
    )
    if fundable_output <= 0:
        raise ContractError("completion recovery cannot fund a positive response")

    retry_modes = {"retry-actionless", "retry-reasoning-incomplete"}
    retry_already_consumed = any(
        event.type == EventType.MODEL_CALLED
        and event.payload.get("lean_completion_recovery_mode") in retry_modes
        for event in events
    )
    last_event = next(
        (event for event in reversed(events) if event.type == EventType.MODEL_CALLED),
        None,
    )
    source_kind = _completion_primary_source_kind(last_event) if last_event is not None else None
    if source_kind is not None:
        if retry_already_consumed:
            raise ContractError("completion response retry was already consumed")
        source_reserve = int(last_event.payload["lean_reserved_completion_retry_output_tokens"])
        mode = "retry-actionless" if source_kind == "actionless" else "retry-reasoning-incomplete"
        effective = min(source_reserve, fundable_output)
        reserve = 0
        effort = "low"
        action_only = True
        retry_available = False
        source_sequence = last_event.sequence
        source_hash = sha256_json(last_event.model_dump(mode="json"))
        lane_active = True
    elif not completion_lane_active:
        mode = "not-applicable"
        effective = fundable_output
        reserve = 0
        effort = "medium"
        action_only = False
        retry_available = False
        source_kind = None
        source_sequence = None
        source_hash = None
        lane_active = False
    else:
        call_capacity = remaining_model_calls is None or remaining_model_calls >= 2
        reservable_output = min(
            configured_max_output_tokens,
            remaining_output,
            remaining_total - (requested_input_tokens * 2),
        )
        if (
            not retry_already_consumed
            and call_capacity
            and remaining_input >= requested_input_tokens * 2
            and reservable_output >= COMPLETION_RESPONSE_RECOVERY_MIN_PRIMARY_AND_RETRY
        ):
            mode = "primary-reserved"
            reserve = COMPLETION_RESPONSE_RECOVERY_OUTPUT_RESERVE
            effective = min(
                configured_max_output_tokens,
                reservable_output - reserve,
            )
            effort = "medium"
            retry_available = True
        else:
            mode = "primary-direct-low"
            reserve = 0
            effective = fundable_output
            effort = "low"
            retry_available = False
        action_only = True
        source_kind = None
        source_sequence = None
        source_hash = None
        lane_active = True

    body = {
        "schema_version": COMPLETION_RESPONSE_RECOVERY_SCHEMA,
        "policy_version": COMPLETION_RESPONSE_RECOVERY_POLICY,
        "mode": mode,
        "phase_mode": phase_mode,
        "completion_lane_active": lane_active,
        "source_response_kind": source_kind,
        "source_event_sequence": source_sequence,
        "source_event_hash": source_hash,
        "configured_max_output_tokens": configured_max_output_tokens,
        "effective_max_output_tokens": effective,
        "reserved_retry_output_tokens": reserve,
        "reasoning_effort": effort,
        "action_only_required": action_only,
        "retry_available_after_response": retry_available,
        "retry_already_consumed": retry_already_consumed,
        "requested_input_tokens": requested_input_tokens,
        "input_tokens_used": usage.input_tokens,
        "output_tokens_used": usage.output_tokens,
        "model_calls_used": usage.model_calls,
        "remaining_input_tokens": remaining_input,
        "remaining_output_tokens": remaining_output,
        "remaining_total_tokens": remaining_total,
        "remaining_model_calls": remaining_model_calls,
        "same_cumulative_budget": True,
        "at_most_one_shared_retry": True,
        "previous_response_id_used": False,
        "provider_calls_authorized": False,
    }
    return CompletionResponseRecovery.model_validate({**body, "content_hash": sha256_json(body)})
