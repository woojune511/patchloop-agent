"""Small contracts for the mutable ``dev-head`` runtime."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.util import sha256_json

DEV_RUN_SCHEMA = "dev-run-v1"
DEV_RUNTIME_ID = "dev-head"
DEV_READ_TOOLS = frozenset({"search_files", "read_file"})
DEV_SINGLE_ACTION_TOOLS = frozenset({"apply_patch", "run_check", "finish_task"})


def dev_tool_surface_hash() -> str:
    return sha256_json(
        {
            "schema_version": "dev-tool-surface-v1",
            "reads": sorted(DEV_READ_TOOLS),
            "single_actions": sorted(DEV_SINGLE_ACTION_TOOLS),
            "max_parallel_reads": 4,
            "mixed_batches": False,
            "unrestricted_shell": False,
            "new_files": False,
        }
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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
    resume_run_id: str | None = Field(
        default=None,
        pattern=r"^run_dev_[a-zA-Z0-9_-]+$",
    )
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
        if self.resume_run_id is not None and self.repeat != 1:
            raise ValueError("--resume-run-id requires --repeat 1")
        return self


class DevRunEnvelope(StrictModel):
    schema_version: Literal["dev-run-envelope-v1"] = "dev-run-envelope-v1"
    official: Literal[False] = False
    runtime_id: Literal["dev-head"] = "dev-head"
    run_id: str = Field(pattern=r"^run_dev_[a-zA-Z0-9_-]+$")
    provider: Literal["mock", "openai"]
    task_path: str
    task_id: str
    task_version: int = Field(ge=1)
    split: Literal[
        "smoke",
        "dev-train",
        "dev-validation",
        "same-repo-heldout",
        "cross-repo-heldout",
    ]
    base_commit: str
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sandbox_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"]
    credential_file_path_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    max_cost_nanos: int = Field(ge=0)
    cost_start_nanos: int = Field(ge=0)
    limits: DevLimits
    sandbox_backend: Literal["local", "docker"]
    evaluator_image_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    created_at: datetime

    @model_validator(mode="after")
    def provider_boundary_is_exact(self) -> DevRunEnvelope:
        if self.cost_start_nanos > self.max_cost_nanos:
            raise ValueError("run envelope cost start exceeds its invocation cap")
        if self.provider == "openai":
            if (
                self.credential_file_path_hash is None
                or self.max_cost_nanos <= 0
                or self.sandbox_backend != "docker"
                or self.evaluator_image_digest is None
            ):
                raise ValueError("live run envelope is missing an exact execution boundary")
        elif (
            self.credential_file_path_hash is not None
            or self.max_cost_nanos != 0
            or self.cost_start_nanos != 0
            or self.sandbox_backend != "local"
            or self.evaluator_image_digest is not None
        ):
            raise ValueError("mock run envelope contains a live execution boundary")
        return self
