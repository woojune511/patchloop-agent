"""Pure offline projection for a future split-aware generation allowance.

This module does not mutate a model request or activate a runtime policy.  It
provides a closed arithmetic contract that can be qualified on public
development evidence before a successor context policy is wired into the
runner.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SPLIT_AWARE_REQUEST_ALLOWANCE_SCHEMA = "split-aware-request-allowance-v1"

TokenDimension = Literal["input_tokens", "output_tokens", "total_tokens"]
AllowanceDecision = Literal["admit_full", "admit_reduced", "block"]
_DIMENSION_ORDER: tuple[TokenDimension, ...] = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
)


class SplitAwareRequestAllowance(BaseModel):
    """Self-validating projection of one exact request against split limits."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["split-aware-request-allowance-v1"]
    decision: AllowanceDecision
    binding_dimension: TokenDimension | None
    constrained_dimensions: tuple[TokenDimension, ...]
    blocking_dimensions: tuple[TokenDimension, ...]
    finalization_required: bool
    investigation_allowed: bool
    requested_input_tokens: int = Field(ge=0)
    configured_max_output_tokens: int = Field(ge=1)
    effective_max_output_tokens: int = Field(ge=0)
    input_tokens_used: int = Field(ge=0)
    output_tokens_used: int = Field(ge=0)
    total_tokens_used: int = Field(ge=0)
    max_cumulative_input_tokens: int = Field(ge=1)
    max_cumulative_output_tokens: int = Field(ge=1)
    max_total_tokens: int = Field(ge=1)
    remaining_input_tokens: int = Field(ge=0)
    remaining_output_tokens: int = Field(ge=0)
    remaining_total_tokens: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.total_tokens_used != self.input_tokens_used + self.output_tokens_used:
            raise ValueError("total_tokens_used must equal split token usage")
        if self.input_tokens_used > self.max_cumulative_input_tokens:
            raise ValueError("input token usage exceeds its cumulative limit")
        if self.output_tokens_used > self.max_cumulative_output_tokens:
            raise ValueError("output token usage exceeds its cumulative limit")
        if self.total_tokens_used > self.max_total_tokens:
            raise ValueError("total token usage exceeds its cumulative limit")

        remaining_input = self.max_cumulative_input_tokens - self.input_tokens_used
        remaining_output = self.max_cumulative_output_tokens - self.output_tokens_used
        remaining_total = self.max_total_tokens - self.total_tokens_used
        if (
            self.remaining_input_tokens,
            self.remaining_output_tokens,
            self.remaining_total_tokens,
        ) != (remaining_input, remaining_output, remaining_total):
            raise ValueError("remaining token evidence does not match usage and limits")

        constrained = {
            "input_tokens": self.requested_input_tokens > remaining_input,
            "output_tokens": self.configured_max_output_tokens > remaining_output,
            "total_tokens": (
                self.requested_input_tokens + self.configured_max_output_tokens > remaining_total
            ),
        }
        expected_constrained = tuple(
            dimension for dimension in _DIMENSION_ORDER if constrained[dimension]
        )
        blocking = {
            "input_tokens": self.requested_input_tokens > remaining_input,
            "output_tokens": remaining_output == 0,
            "total_tokens": self.requested_input_tokens >= remaining_total,
        }
        expected_blocking = tuple(
            dimension for dimension in _DIMENSION_ORDER if blocking[dimension]
        )
        available_output = min(
            self.configured_max_output_tokens,
            remaining_output,
            max(0, remaining_total - self.requested_input_tokens),
        )
        expected_output = 0 if expected_blocking else available_output
        expected_decision: AllowanceDecision
        if expected_output == 0:
            expected_decision = "block"
        elif expected_output == self.configured_max_output_tokens:
            expected_decision = "admit_full"
        else:
            expected_decision = "admit_reduced"
        expected_binding = expected_constrained[0] if expected_constrained else None

        if self.constrained_dimensions != expected_constrained:
            raise ValueError("constrained token dimensions are inconsistent")
        if self.blocking_dimensions != expected_blocking:
            raise ValueError("blocking token dimensions are inconsistent")
        if self.binding_dimension != expected_binding:
            raise ValueError("binding token dimension is inconsistent")
        if self.effective_max_output_tokens != expected_output:
            raise ValueError("effective output allowance is inconsistent")
        if self.decision != expected_decision:
            raise ValueError("request allowance decision is inconsistent")
        if self.finalization_required is not (expected_decision == "admit_reduced"):
            raise ValueError("finalization requirement is inconsistent")
        if self.investigation_allowed is not (expected_decision == "admit_full"):
            raise ValueError("investigation allowance is inconsistent")
        return self


def project_split_aware_request_allowance(
    *,
    requested_input_tokens: int,
    configured_max_output_tokens: int,
    input_tokens_used: int,
    output_tokens_used: int,
    max_cumulative_input_tokens: int,
    max_cumulative_output_tokens: int,
    max_total_tokens: int,
) -> SplitAwareRequestAllowance:
    """Return a condition-neutral exact allowance without changing a request."""

    values = {
        "requested_input_tokens": requested_input_tokens,
        "configured_max_output_tokens": configured_max_output_tokens,
        "input_tokens_used": input_tokens_used,
        "output_tokens_used": output_tokens_used,
        "max_cumulative_input_tokens": max_cumulative_input_tokens,
        "max_cumulative_output_tokens": max_cumulative_output_tokens,
        "max_total_tokens": max_total_tokens,
    }
    for name, value in values.items():
        if type(value) is not int:
            raise TypeError(f"{name} must be an exact integer")
    if requested_input_tokens < 0 or input_tokens_used < 0 or output_tokens_used < 0:
        raise ValueError("request and usage tokens must be nonnegative")
    if (
        configured_max_output_tokens <= 0
        or max_cumulative_input_tokens <= 0
        or max_cumulative_output_tokens <= 0
        or max_total_tokens <= 0
    ):
        raise ValueError("configured output and cumulative limits must be positive")

    total_used = input_tokens_used + output_tokens_used
    if input_tokens_used > max_cumulative_input_tokens:
        raise ValueError("input token usage exceeds its cumulative limit")
    if output_tokens_used > max_cumulative_output_tokens:
        raise ValueError("output token usage exceeds its cumulative limit")
    if total_used > max_total_tokens:
        raise ValueError("total token usage exceeds its cumulative limit")

    remaining_input = max_cumulative_input_tokens - input_tokens_used
    remaining_output = max_cumulative_output_tokens - output_tokens_used
    remaining_total = max_total_tokens - total_used
    constrained = {
        "input_tokens": requested_input_tokens > remaining_input,
        "output_tokens": configured_max_output_tokens > remaining_output,
        "total_tokens": requested_input_tokens + configured_max_output_tokens > remaining_total,
    }
    constrained_dimensions = tuple(
        dimension for dimension in _DIMENSION_ORDER if constrained[dimension]
    )
    blocking = {
        "input_tokens": requested_input_tokens > remaining_input,
        "output_tokens": remaining_output == 0,
        "total_tokens": requested_input_tokens >= remaining_total,
    }
    blocking_dimensions = tuple(dimension for dimension in _DIMENSION_ORDER if blocking[dimension])
    available_output = min(
        configured_max_output_tokens,
        remaining_output,
        max(0, remaining_total - requested_input_tokens),
    )
    effective_output = 0 if blocking_dimensions else available_output
    if effective_output == 0:
        decision: AllowanceDecision = "block"
    elif effective_output == configured_max_output_tokens:
        decision = "admit_full"
    else:
        decision = "admit_reduced"

    return SplitAwareRequestAllowance(
        schema_version=SPLIT_AWARE_REQUEST_ALLOWANCE_SCHEMA,
        decision=decision,
        binding_dimension=(constrained_dimensions[0] if constrained_dimensions else None),
        constrained_dimensions=constrained_dimensions,
        blocking_dimensions=blocking_dimensions,
        finalization_required=decision == "admit_reduced",
        investigation_allowed=decision == "admit_full",
        requested_input_tokens=requested_input_tokens,
        configured_max_output_tokens=configured_max_output_tokens,
        effective_max_output_tokens=effective_output,
        input_tokens_used=input_tokens_used,
        output_tokens_used=output_tokens_used,
        total_tokens_used=total_used,
        max_cumulative_input_tokens=max_cumulative_input_tokens,
        max_cumulative_output_tokens=max_cumulative_output_tokens,
        max_total_tokens=max_total_tokens,
        remaining_input_tokens=remaining_input,
        remaining_output_tokens=remaining_output,
        remaining_total_tokens=remaining_total,
    )
