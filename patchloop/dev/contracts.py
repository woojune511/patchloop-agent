"""Small contracts for the mutable ``dev-head`` runtime."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEV_RUN_SCHEMA = "dev-run-v1"
DEV_RUNTIME_ID = "dev-head"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DevState(StrEnum):
    WORK = "WORK"
    VERIFY = "VERIFY"
    REVIEW = "REVIEW"
    SUBMITTED = "SUBMITTED"


class DevTerminal(StrEnum):
    EVALUATOR_PASS = "EVALUATOR_PASS"
    EVALUATOR_FAIL = "EVALUATOR_FAIL"
    EVALUATOR_ERROR = "EVALUATOR_ERROR"
    COST_CAP_REACHED = "COST_CAP_REACHED"
    PROTOCOL_VIOLATION = "PROTOCOL_VIOLATION"
    INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE"
    PROVIDER_TIMEOUT_OR_UNKNOWN = "PROVIDER_TIMEOUT_OR_UNKNOWN"
    COUNT_TIMEOUT_OR_UNKNOWN = "COUNT_TIMEOUT_OR_UNKNOWN"
    LIMIT_REACHED = "LIMIT_REACHED"
    TASK_FAILED = "TASK_FAILED"
    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"


class DevLimits(StrictModel):
    max_model_calls: int = Field(default=40, ge=1)
    max_tool_actions: int = Field(default=100, ge=1)
    max_accepted_mutations: int = Field(default=4, ge=1)
    wall_time_seconds: int = Field(default=1_800, ge=1)
    max_protocol_recoveries: int = Field(default=1, ge=0, le=1)
    max_parallel_reads: int = Field(default=4, ge=1, le=4)


class EditAnchor(StrictModel):
    path: str = Field(min_length=1, max_length=1_000)
    old_text: str = Field(min_length=1, max_length=20_000)
    occurrence: int = Field(default=1, ge=1, le=100)


class MutationIntent(StrictModel):
    hypothesis: str = Field(min_length=1, max_length=1_500)
    expected_behavior: str = Field(min_length=1, max_length=1_500)
    evidence_span_ids: list[str] = Field(min_length=1, max_length=8)
    edit_anchor: EditAnchor
    falsified_prior_hypothesis: str | None = Field(default=None, min_length=1, max_length=1_500)
    alternative_mechanism: str | None = Field(default=None, min_length=1, max_length=1_500)

    @model_validator(mode="after")
    def alternative_fields_are_paired(self) -> MutationIntent:
        if (self.falsified_prior_hypothesis is None) != (self.alternative_mechanism is None):
            raise ValueError(
                "falsified_prior_hypothesis and alternative_mechanism must be supplied together"
            )
        return self


class RequestedTool(StrictModel):
    name: str
    action_id: str = Field(min_length=1, max_length=500)
    arguments: dict[str, Any] = Field(default_factory=dict)


class DevModelTurn(StrictModel):
    tool_calls: list[RequestedTool] = Field(default_factory=list)
    requested_input_tokens: int | None = None
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    response_id: str | None = None
    response_model: str | None = None
    response_status: str | None = None
    incomplete_reason: str | None = None
    error_code: str | None = None


class DevToolResult(StrictModel):
    action_id: str
    input_hash: str
    tool: str
    status: Literal["succeeded", "failed"]
    output: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None
    replayed: bool = False
    evidence_cache_hit: bool = False
    workspace_diff_hash: str | None = None


class DevRunRequest(StrictModel):
    provider: Literal["mock", "openai"]
    task: Path
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] = "medium"
    env_file: Path | None = None
    max_cost_usd: Decimal | None = None
    repeat: int = Field(default=1, ge=1, le=6)
    state_root: Path | None = None
    limits: DevLimits = Field(default_factory=DevLimits)

    @model_validator(mode="after")
    def provider_options_match(self) -> DevRunRequest:
        if self.provider == "openai":
            if self.env_file is None:
                raise ValueError("--provider openai requires --env-file")
            if self.max_cost_usd is None or self.max_cost_usd <= 0:
                raise ValueError("--provider openai requires a positive --max-cost-usd")
        elif self.env_file is not None or self.max_cost_usd is not None:
            raise ValueError("--provider mock forbids --env-file and --max-cost-usd")
        return self
