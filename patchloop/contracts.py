"""Versioned public contracts for tasks, runs, tools, memory, and evaluation."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.util import safe_relative_path


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class Phase(StrEnum):
    INTAKE = "INTAKE"
    REPRODUCE = "REPRODUCE"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    VERIFY = "VERIFY"
    REVIEW = "REVIEW"
    DONE = "DONE"


class MemoryCondition(StrEnum):
    NO_MEMORY = "no_memory"
    RAW_TRACE = "raw_trace"
    STRUCTURED = "structured"
    SELECTIVE_STRUCTURED = "selective_structured"


class VerdictState(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    NOT_RUN = "not_run"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(StrEnum):
    RUN_STARTED = "RunStarted"
    PHASE_CHANGED = "PhaseChanged"
    CONTEXT_BUILT = "ContextBuilt"
    MEMORY_RETRIEVED = "MemoryRetrieved"
    MODEL_CALLED = "ModelCalled"
    TOOL_CALLED = "ToolCalled"
    TOOL_SUCCEEDED = "ToolSucceeded"
    TOOL_FAILED = "ToolFailed"
    PATCH_APPLIED = "PatchApplied"
    CHECK_STARTED = "CheckStarted"
    CHECK_FINISHED = "CheckFinished"
    CHECKPOINT_SAVED = "CheckpointSaved"
    FAILURE_TAGGED = "FailureTagged"
    FAULT_INJECTED = "FaultInjected"
    RUN_COMPLETED = "RunCompleted"
    RUN_FAILED = "RunFailed"


class RepositorySpec(StrictModel):
    url: str
    base_commit: str = Field(min_length=1)
    language: Literal["python"] = "python"

    @model_validator(mode="after")
    def snapshot_is_content_addressed(self) -> RepositorySpec:
        if self.url.startswith("snapshot://") and not re.fullmatch(
            r"sha256:[0-9a-f]{64}", self.base_commit
        ):
            raise ValueError("snapshot repositories require a sha256 content revision")
        if self.url.startswith("https://github.com/") and not re.fullmatch(
            r"[0-9a-f]{40}", self.base_commit
        ):
            raise ValueError("GitHub repositories require a full 40-character commit revision")
        return self


class IssueSpec(StrictModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class RegisteredCheck(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]+$")
    command: list[str] = Field(min_length=1)
    timeout_seconds: int = Field(default=60, ge=1, le=1800)
    working_directory: str = "."
    environment: dict[str, str] = Field(default_factory=dict)
    expected_exit_codes: list[int] = Field(default_factory=lambda: [0])
    output_limit_bytes: int = Field(default=200_000, ge=1, le=10_000_000)

    @field_validator("working_directory")
    @classmethod
    def validate_workdir(cls, value: str) -> str:
        if value == ".":
            return value
        return safe_relative_path(value, field_name="working_directory")


class TaskConstraints(StrictModel):
    allowed_paths: list[str] = Field(default_factory=lambda: ["**"])
    forbidden_paths: list[str] = Field(default_factory=list)
    max_changed_files: int = Field(default=4, ge=1, le=100)
    max_diff_lines: int = Field(default=120, ge=1, le=10_000)
    dependency_changes_allowed: bool = False
    public_api_changes_allowed: bool = False

    @field_validator("allowed_paths", "forbidden_paths")
    @classmethod
    def validate_patterns(cls, values: list[str]) -> list[str]:
        for value in values:
            safe_relative_path(value, field_name="path pattern")
        return values


class PublicTask(StrictModel):
    schema_version: Literal["task-public-v1"] = "task-public-v1"
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(default=1, ge=1)
    split: Literal[
        "smoke", "dev-train", "dev-validation", "same-repo-heldout", "cross-repo-heldout"
    ]
    repository: RepositorySpec
    issue: IssueSpec
    constraints: TaskConstraints = Field(default_factory=TaskConstraints)
    visible_checks: list[RegisteredCheck] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ReferencePatch(StrictModel):
    path: str
    sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value)


class AuditSpec(StrictModel):
    expected_files: list[str] = Field(default_factory=list)
    prohibited_behaviors: list[str] = Field(default_factory=list)


class PrivateTask(StrictModel):
    schema_version: Literal["task-private-v1"] = "task-private-v1"
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(default=1, ge=1)
    hidden_checks: list[RegisteredCheck] = Field(default_factory=list)
    reference_patch: ReferencePatch
    audit: AuditSpec = Field(default_factory=AuditSpec)


class TaskPackage(StrictModel):
    public: PublicTask
    private: PrivateTask
    root: str
    public_spec_hash: str
    private_spec_hash: str

    @model_validator(mode="after")
    def matching_identity(self) -> TaskPackage:
        if (self.public.task_id, self.public.task_version) != (
            self.private.task_id,
            self.private.task_version,
        ):
            raise ValueError("public/private task identity mismatch")
        return self


class Budget(StrictModel):
    max_model_calls: int = Field(default=20, ge=1)
    max_tool_calls: int = Field(default=50, ge=1)
    max_total_tokens: int = Field(default=80_000, ge=1)
    wall_clock_timeout_seconds: int = Field(default=900, ge=1)


class ModelConfig(StrictModel):
    provider: str
    model_id: str
    provider_sdk_version: str | None = None
    reasoning_effort: str = "medium"
    temperature: float = 0
    max_output_tokens: int = 4096
    input_price_per_million_usd: float | None = Field(default=None, ge=0)
    output_price_per_million_usd: float | None = Field(default=None, ge=0)


class FaultSpec(StrictModel):
    type: Literal["none", "context-reset", "worker-kill-after-patch", "test-timeout"] = "none"
    trigger_after: int | None = None


class MemoryConfig(StrictModel):
    condition: MemoryCondition = MemoryCondition.NO_MEMORY
    index_version: str | None = None
    index_hash: str | None = None
    max_context_tokens: int = 2000


class RunManifest(StrictModel):
    schema_version: Literal["run-manifest-v1"] = "run-manifest-v1"
    run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    task_id: str
    task_version: int
    base_commit: str
    public_spec_hash: str
    private_spec_hash: str | None = None
    harness_git_commit: str = "uncommitted"
    tool_schema_version: str = "v1"
    context_policy_version: str = "v1"
    memory_policy_version: str = "v1"
    model: ModelConfig
    budget: Budget = Field(default_factory=Budget)
    sandbox_backend: Literal["local", "docker"] = "local"
    agent_image_digest: str | None = None
    evaluator_image_digest: str | None = None
    fault: FaultSpec = Field(default_factory=FaultSpec)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    created_at: datetime


class RunEvent(StrictModel):
    schema_version: Literal["run-event-v1"] = "run-event-v1"
    event_id: str
    run_id: str
    sequence: int = Field(ge=1)
    type: EventType
    timestamp: datetime
    actor: str
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class Artifact(StrictModel):
    artifact_id: str
    content_hash: str
    media_type: str
    size_bytes: int
    path: str
    created_at: datetime


class Checkpoint(StrictModel):
    schema_version: Literal["checkpoint-v1"] = "checkpoint-v1"
    checkpoint_id: str
    run_id: str
    through_sequence: int = Field(ge=0)
    phase: Phase
    task_summary: str = ""
    reproduction_status: Literal["unknown", "confirmed", "not_reproduced", "static_evidence"] = (
        "unknown"
    )
    current_plan: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    completed_action_ids: list[str] = Field(default_factory=list)
    completed_checks: list[str] = Field(default_factory=list)
    pending_checks: list[str] = Field(default_factory=list)
    important_decisions: list[dict[str, Any]] = Field(default_factory=list)
    repository_head: str
    worktree_diff_hash: str
    last_patch_hash: str | None = None
    remaining_budget: dict[str, int] = Field(default_factory=dict)
    created_at: datetime


class ToolCall(StrictModel):
    tool: str
    tool_schema_version: Literal["v1"] = "v1"
    action_id: str
    run_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    input_hash: str


class ToolResult(StrictModel):
    action_id: str
    status: Literal["succeeded", "failed", "rejected"]
    started_at: datetime
    finished_at: datetime
    output: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class VerifierResult(StrictModel):
    schema_version: Literal["verifier-result-v1"] = "verifier-result-v1"
    verifier_result_id: str
    run_id: str
    check_type: str
    check_id: str
    state: VerdictState
    duration_ms: int = Field(ge=0)
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class Verdicts(StrictModel):
    hidden_tests: VerdictState = VerdictState.NOT_RUN
    regression_tests: VerdictState = VerdictState.NOT_RUN
    scope_policy: VerdictState = VerdictState.NOT_RUN
    safety_policy: VerdictState = VerdictState.NOT_RUN


class Usage(StrictModel):
    input_tokens: int = 0
    output_tokens: int = 0
    model_cost_usd: float = 0
    model_calls: int = 0
    tool_calls: int = 0
    wall_clock_ms: int = 0


class RunResult(StrictModel):
    schema_version: Literal["run-result-v1"] = "run-result-v1"
    run_id: str
    agent_submission_status: str
    evaluation_status: str
    scope_compliant_success: bool
    official: bool = False
    verdicts: Verdicts
    usage: Usage = Field(default_factory=Usage)
    submitted_patch_artifact_id: str | None = None
    verifier_results: list[VerifierResult] = Field(default_factory=list)


class FailureRecord(StrictModel):
    schema_version: Literal["failure-v1"] = "failure-v1"
    failure_id: str
    run_id: str
    primary_cause: str
    observed_symptoms: list[str] = Field(default_factory=list)
    phase: Phase
    recoverability: Literal["recoverable", "terminal", "unknown"] = "unknown"
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    classification_method: str
    review_status: Literal["unreviewed", "reviewed", "rejected"] = "unreviewed"


class FailurePattern(StrictModel):
    failure_class: str
    phase: Phase
    description: str


class MemoryEntry(StrictModel):
    schema_version: Literal["memory-entry-v1"] = "memory-entry-v1"
    memory_id: str
    index_version: str
    failure_pattern: FailurePattern
    preconditions: list[str] = Field(min_length=1)
    diagnostic_evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(min_length=1)
    do_not_apply_when: list[str] = Field(min_length=1)
    applicable_languages: list[Literal["python"]] = Field(default_factory=lambda: ["python"])
    source_run_ids: list[str] = Field(min_length=1)
    validation_count: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0, le=1)


class RetrievalCandidate(StrictModel):
    memory_id: str
    score: float
    selected: bool
    rendered_tokens: int


class RetrievalDecision(StrictModel):
    schema_version: Literal["memory-retrieval-v1"] = "memory-retrieval-v1"
    run_id: str
    index_version: str
    query_hash: str
    threshold: float
    token_budget: int
    candidates: list[RetrievalCandidate] = Field(default_factory=list)
    selected_memory_ids: list[str] = Field(default_factory=list)
    no_match: bool
