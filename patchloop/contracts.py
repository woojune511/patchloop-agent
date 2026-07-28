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


class ExperimentPurpose(StrEnum):
    OFFLINE_SMOKE = "offline-smoke"
    DEVELOPMENT_VALIDATION_LIVE_PILOT = "development-validation-live-pilot"
    DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT = (
        "development-validation-model-candidate-pilot"
    )
    MEMORY_DEVELOPMENT_NO_MEMORY = "memory-development-no-memory"
    CORE = "core"


class RunOutcomeKind(StrEnum):
    RESOLVED = "resolved"
    TASK_FAILURE = "task_failure"
    AGENT_FAILURE = "agent_failure"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


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
    TOOL_REPLAYED = "ToolReplayed"
    PATCH_PREPARED = "PatchPrepared"
    TOOL_SUCCEEDED = "ToolSucceeded"
    TOOL_FAILED = "ToolFailed"
    PATCH_APPLIED = "PatchApplied"
    CHECK_STARTED = "CheckStarted"
    CHECK_FINISHED = "CheckFinished"
    REVIEW_RECORDED = "ReviewRecorded"
    SUBMISSION_ATTEMPTED = "SubmissionAttempted"
    SUBMISSION_REJECTED = "SubmissionRejected"
    SUBMISSION_ACCEPTED = "SubmissionAccepted"
    LOOP_DETECTED = "LoopDetected"
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


class HiddenArtifact(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = safe_relative_path(value)
        if not path.startswith("hidden/"):
            raise ValueError("hidden artifact path must be below hidden/")
        return path


class AuditSpec(StrictModel):
    expected_files: list[str] = Field(default_factory=list)
    prohibited_behaviors: list[str] = Field(default_factory=list)


class PrivateTask(StrictModel):
    schema_version: Literal["task-private-v1", "task-private-v2"] = "task-private-v1"
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(default=1, ge=1)
    hidden_checks: list[RegisteredCheck] = Field(default_factory=list)
    hidden_artifacts: list[HiddenArtifact] = Field(default_factory=list)
    reference_patch: ReferencePatch
    audit: AuditSpec = Field(default_factory=AuditSpec)

    @model_validator(mode="after")
    def bind_v2_hidden_artifacts(self) -> PrivateTask:
        if self.schema_version == "task-private-v2" and not self.hidden_artifacts:
            raise ValueError("task-private-v2 requires at least one hidden artifact")
        if self.schema_version == "task-private-v1" and self.hidden_artifacts:
            raise ValueError("hidden_artifacts requires task-private-v2")
        paths = [artifact.path for artifact in self.hidden_artifacts]
        if len(paths) != len(set(paths)):
            raise ValueError("hidden artifact paths must be unique")
        return self


class TaskEnvironment(StrictModel):
    schema_version: Literal["task-environment-v1"] = "task-environment-v1"
    evaluator_image: str = Field(min_length=1)
    image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_image_tag: str | None = None

    @model_validator(mode="after")
    def require_digest_pinned_image(self) -> TaskEnvironment:
        if not self.evaluator_image.endswith(f"@{self.image_digest}"):
            raise ValueError("evaluator_image must end with the declared immutable image digest")
        return self


class TaskPackage(StrictModel):
    public: PublicTask
    private: PrivateTask
    environment: TaskEnvironment | None = None
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


class DatasetRole(StrEnum):
    CALIBRATION = "calibration"
    MEMORY_DEVELOPMENT = "memory-development"
    DEVELOPMENT_VALIDATION = "development-validation"
    CORE_SAME_REPO = "core-same-repo"
    CORE_CROSS_REPO = "core-cross-repo"
    EXTERNAL_ACCEPTANCE = "external-acceptance"


class ExperimentRunContext(StrictModel):
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    purpose: ExperimentPurpose
    suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dataset_manifest_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    dataset_role: DatasetRole | None = None
    schedule_seed: int
    schedule_order: int = Field(ge=1)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repetition: int = Field(ge=1)


class DatasetAdmissionState(StrEnum):
    FIXTURE = "fixture"
    ADMITTED = "admitted"


class DatasetSourceKind(StrEnum):
    SYNTHETIC_CONTROL = "synthetic-control"
    BENCHMARK_INSTANCE = "benchmark-instance"
    UPSTREAM_INCIDENT = "upstream-incident"
    BENCHMARK_INSPIRED = "benchmark-inspired"


class WorkflowType(StrEnum):
    ISSUE_FIX = "issue-fix"
    FEATURE_IMPLEMENTATION = "feature-implementation"
    CI_REPAIR = "ci-repair"
    REVIEW_REMEDIATION = "review-remediation"
    MIGRATION = "migration"
    SECURITY_FIX = "security-fix"


class DifficultyTier(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class DifficultyAudit(StrictModel):
    localization: int = Field(ge=0, le=2)
    reasoning_depth: int = Field(ge=0, le=2)
    implementation_breadth: int = Field(ge=0, le=2)
    verification_breadth: int = Field(ge=0, le=2)
    total: int = Field(ge=0, le=8)
    tier: DifficultyTier
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_total_and_tier(self) -> DifficultyAudit:
        expected_total = (
            self.localization
            + self.reasoning_depth
            + self.implementation_breadth
            + self.verification_breadth
        )
        if self.total != expected_total:
            raise ValueError(
                f"difficulty total must equal dimension sum: {expected_total}, got {self.total}"
            )
        expected_tier = (
            DifficultyTier.EASY
            if self.total <= 2
            else DifficultyTier.MEDIUM
            if self.total <= 5
            else DifficultyTier.HARD
        )
        if self.tier != expected_tier:
            raise ValueError(
                f"difficulty tier for total {self.total} must be {expected_tier.value}"
            )
        return self


class SourceProvenance(StrictModel):
    kind: DatasetSourceKind
    benchmark_family: str | None = None
    benchmark_revision: str | None = None
    benchmark_instance_id: str | None = None
    upstream_repository: str | None = None
    issue_url: str | None = None
    pull_request_url: str | None = None
    upstream_base_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    resolution_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    license_spdx: str | None = None
    retrieved_at: datetime | None = None
    contamination_risk: Literal["none", "low", "medium", "high", "unknown"] = "unknown"
    workflow_type: WorkflowType
    environment_image: str | None = None

    @model_validator(mode="after")
    def validate_source_identity(self) -> SourceProvenance:
        if self.kind == DatasetSourceKind.SYNTHETIC_CONTROL:
            if self.contamination_risk != "none":
                raise ValueError("synthetic controls must use contamination_risk=none")
            return self

        required = {
            "upstream_repository": self.upstream_repository,
            "upstream_base_commit": self.upstream_base_commit,
            "license_spdx": self.license_spdx,
            "retrieved_at": self.retrieved_at,
        }
        missing = [
            name
            for name, value in required.items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise ValueError(
                "non-synthetic dataset source is missing provenance: " + ", ".join(missing)
            )
        if self.kind in {
            DatasetSourceKind.BENCHMARK_INSTANCE,
            DatasetSourceKind.BENCHMARK_INSPIRED,
        }:
            benchmark_required = {
                "benchmark_family": self.benchmark_family,
                "benchmark_revision": self.benchmark_revision,
                "benchmark_instance_id": self.benchmark_instance_id,
            }
            benchmark_missing = [
                name
                for name, value in benchmark_required.items()
                if value is None or (isinstance(value, str) and not value.strip())
            ]
            if benchmark_missing:
                raise ValueError(
                    "benchmark source is missing identity: " + ", ".join(benchmark_missing)
                )
        return self


class AdmissionEvidence(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    official: bool
    base_visible_pass: bool
    base_hidden_fail: bool
    reference_pass: bool
    reference_pass_runs: int = Field(ge=3)
    rejected_bad_patches: int = Field(ge=3)

    @field_validator("path")
    @classmethod
    def validate_evidence_path(cls, value: str) -> str:
        return safe_relative_path(value)


class DatasetTaskEntry(StrictModel):
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(ge=1)
    path: str
    role: DatasetRole
    admission_state: DatasetAdmissionState
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source: SourceProvenance
    difficulty: DifficultyAudit
    failure_pattern_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    solution_lineage_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    admission_evidence: AdmissionEvidence | None = None

    @field_validator("path")
    @classmethod
    def validate_task_path(cls, value: str) -> str:
        return safe_relative_path(value)

    @model_validator(mode="after")
    def validate_role_eligibility(self) -> DatasetTaskEntry:
        if self.role == DatasetRole.CALIBRATION:
            if self.admission_state != DatasetAdmissionState.FIXTURE:
                raise ValueError("calibration entries must use admission_state=fixture")
            if self.source.kind != DatasetSourceKind.SYNTHETIC_CONTROL:
                raise ValueError("calibration entries must be synthetic-control sources")
            return self

        if self.admission_state != DatasetAdmissionState.ADMITTED:
            raise ValueError("research dataset entries must be admitted")
        if self.source.kind not in {
            DatasetSourceKind.BENCHMARK_INSTANCE,
            DatasetSourceKind.UPSTREAM_INCIDENT,
        }:
            raise ValueError(
                "research dataset entries require benchmark-instance or upstream-incident sources"
            )
        if self.difficulty.tier == DifficultyTier.EASY:
            raise ValueError("easy tasks are not eligible for the research dataset")
        if self.source.contamination_risk == "unknown":
            raise ValueError("research dataset entries require a contamination-risk audit")
        if not (
            self.source.issue_url is not None and self.source.issue_url.strip()
        ) and not (
            self.source.pull_request_url is not None
            and self.source.pull_request_url.strip()
        ):
            raise ValueError(
                "research dataset entries require an upstream issue or pull request URL"
            )
        if self.admission_evidence is None:
            raise ValueError("research dataset entries require admission evidence")
        evidence = self.admission_evidence
        if (
            not evidence.official
            or not evidence.base_visible_pass
            or not evidence.base_hidden_fail
            or not evidence.reference_pass
        ):
            raise ValueError(
                "research admission evidence must prove the base failure "
                "and official reference pass"
            )
        return self


class DatasetPolicy(StrictModel):
    minimum_repositories: int = Field(default=2, ge=2)
    same_repo_must_overlap_development: bool = True
    same_repo_requires_one_to_one_development_coverage: bool = True
    cross_repo_must_be_disjoint: bool = True
    research_minimum_tier: Literal["medium"] = "medium"


class StressScheduleCase(StrictModel):
    fault: Literal["context-reset", "worker-kill-after-patch", "test-timeout"]
    trigger: Literal[
        "after-model-call-10",
        "after-first-durable-patch-checkpoint",
        "first-registered-visible-check",
    ]
    persistent_state_modes: list[Literal["on", "off"]] = Field(min_length=1)
    repetitions: Literal[2] = 2
    arm_once: Literal[True] = True

    @model_validator(mode="after")
    def canonical_fault_case(self) -> StressScheduleCase:
        expected = {
            "context-reset": ("after-model-call-10", {"on", "off"}),
            "worker-kill-after-patch": (
                "after-first-durable-patch-checkpoint",
                {"on", "off"},
            ),
            "test-timeout": ("first-registered-visible-check", {"on"}),
        }
        expected_trigger, expected_modes = expected[self.fault]
        if self.trigger != expected_trigger:
            raise ValueError(
                f"{self.fault} requires trigger={expected_trigger}, got {self.trigger}"
            )
        if len(self.persistent_state_modes) != len(set(self.persistent_state_modes)):
            raise ValueError("stress persistent_state_modes must be unique")
        if set(self.persistent_state_modes) != expected_modes:
            modes = ", ".join(sorted(expected_modes))
            raise ValueError(f"{self.fault} requires persistent state modes: {modes}")
        return self


class StressSchedule(StrictModel):
    schema_version: Literal["stress-schedule-v1"] = "stress-schedule-v1"
    schedule_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    seed: Literal[20260723] = 20260723
    memory_condition: Literal["no_memory"] = "no_memory"
    task_scope: Literal["all-sentinels"] = "all-sentinels"
    baseline_source: Literal["core-no-memory"] = "core-no-memory"
    expected_derived_runs: int = Field(default=30, ge=1)
    cases: list[StressScheduleCase] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def complete_fault_matrix(self) -> StressSchedule:
        faults = [case.fault for case in self.cases]
        expected = {
            "context-reset",
            "worker-kill-after-patch",
            "test-timeout",
        }
        if len(faults) != len(set(faults)):
            raise ValueError("stress schedule faults must be unique")
        if set(faults) != expected:
            missing = ", ".join(sorted(expected - set(faults)))
            extra = ", ".join(sorted(set(faults) - expected))
            raise ValueError(
                f"stress schedule must contain the canonical fault set; "
                f"missing={missing or 'none'}, extra={extra or 'none'}"
            )
        return self


class StressLane(StrictModel):
    lane_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    benchmark_inspiration: Literal["terminal-bench-2.1"]
    sentinel_count: int = Field(default=3, ge=1)
    task_ids: list[str] = Field(default_factory=list)
    scenarios: list[Literal["context-reset", "worker-kill-after-patch", "test-timeout"]] = Field(
        min_length=1
    )
    selection_policy: Literal["public-contract-structure-v1"] | None = None
    selection_rationale: dict[str, str] = Field(default_factory=dict)
    schedule: StressSchedule | None = None
    include_in_core_metrics: Literal[False] = False

    @model_validator(mode="after")
    def validate_lane(self) -> StressLane:
        if len(self.task_ids) != len(set(self.task_ids)):
            raise ValueError("stress lane task_ids must be unique")
        if len(self.scenarios) != len(set(self.scenarios)):
            raise ValueError("stress lane scenarios must be unique")
        if self.selection_rationale and set(self.selection_rationale) != set(self.task_ids):
            raise ValueError(
                "stress selection_rationale keys must match the selected task_ids"
            )
        if any(not rationale.strip() for rationale in self.selection_rationale.values()):
            raise ValueError("stress selection rationale must not be blank")
        if self.schedule is not None:
            scheduled_faults = {case.fault for case in self.schedule.cases}
            if scheduled_faults != set(self.scenarios):
                raise ValueError("stress lane scenarios must match the schedule fault set")
            if len(self.task_ids) == self.sentinel_count:
                derived_runs = len(self.task_ids) * sum(
                    len(case.persistent_state_modes) * case.repetitions
                    for case in self.schedule.cases
                )
                if self.schedule.expected_derived_runs != derived_runs:
                    raise ValueError(
                        "stress schedule expected_derived_runs mismatch: "
                        f"{self.schedule.expected_derived_runs} != {derived_runs}"
                    )
        return self


RESEARCH_DATASET_ROLES = {
    DatasetRole.MEMORY_DEVELOPMENT,
    DatasetRole.DEVELOPMENT_VALIDATION,
    DatasetRole.CORE_SAME_REPO,
    DatasetRole.CORE_CROSS_REPO,
}


class DatasetManifest(StrictModel):
    schema_version: Literal["dataset-manifest-v1"] = "dataset-manifest-v1"
    dataset_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    status: Literal["draft", "frozen"] = "draft"
    calibration_target: int = Field(default=5, ge=1)
    targets: dict[DatasetRole, int]
    policy: DatasetPolicy = Field(default_factory=DatasetPolicy)
    tasks: list[DatasetTaskEntry] = Field(default_factory=list)
    stress_lanes: list[StressLane] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_registry(self) -> DatasetManifest:
        if set(self.targets) != RESEARCH_DATASET_ROLES:
            expected = ", ".join(sorted(role.value for role in RESEARCH_DATASET_ROLES))
            raise ValueError(f"dataset targets must contain exactly: {expected}")
        if any(value < 1 for value in self.targets.values()):
            raise ValueError("dataset target counts must be positive")

        identities = [(entry.task_id, entry.task_version) for entry in self.tasks]
        if len(identities) != len(set(identities)):
            raise ValueError("dataset task identities must be unique")
        paths = [entry.path for entry in self.tasks]
        if len(paths) != len(set(paths)):
            raise ValueError("dataset task paths must be unique")

        research = [entry for entry in self.tasks if entry.role in RESEARCH_DATASET_ROLES]
        source_ids = [
            (entry.source.benchmark_family, entry.source.benchmark_instance_id)
            for entry in research
            if entry.source.benchmark_instance_id is not None
        ]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("benchmark instances must not be reused across dataset roles")
        lineages = [entry.solution_lineage_id for entry in research]
        if len(lineages) != len(set(lineages)):
            raise ValueError("research solution_lineage_id values must be unique")

        counts = {
            role: sum(entry.role == role for entry in research) for role in RESEARCH_DATASET_ROLES
        }
        exceeded = [role.value for role, count in counts.items() if count > self.targets[role]]
        if exceeded:
            raise ValueError("dataset role count exceeds target: " + ", ".join(sorted(exceeded)))
        if self.status == "frozen":
            incomplete = [
                f"{role.value}={counts[role]}/{target}"
                for role, target in self.targets.items()
                if counts[role] != target
            ]
            if incomplete:
                raise ValueError("frozen dataset has incomplete roles: " + ", ".join(incomplete))
            if len(self.stress_lanes) != 1:
                raise ValueError("frozen dataset requires exactly one stress lane")
            lane = self.stress_lanes[0]
            if lane.sentinel_count != 3 or len(lane.task_ids) != 3:
                raise ValueError("frozen stress lane requires exactly three sentinels")
            expected_scenarios = {
                "context-reset",
                "worker-kill-after-patch",
                "test-timeout",
            }
            if set(lane.scenarios) != expected_scenarios:
                raise ValueError("frozen stress lane requires the canonical three scenarios")
            if lane.selection_policy is None or lane.schedule is None:
                raise ValueError(
                    "frozen stress lane requires a selection policy and fault schedule"
                )
            if set(lane.selection_rationale) != set(lane.task_ids):
                raise ValueError(
                    "frozen stress lane requires rationale for every selected task"
                )
            eligible_sentinels = {
                entry.task_id
                for entry in self.tasks
                if entry.admission_state == DatasetAdmissionState.ADMITTED
                and entry.role
                in {
                    DatasetRole.CORE_SAME_REPO,
                    DatasetRole.CORE_CROSS_REPO,
                }
            }
            ineligible = sorted(set(lane.task_ids) - eligible_sentinels)
            if ineligible:
                raise ValueError(
                    "frozen stress lane requires admitted held-out tasks: "
                    + ", ".join(ineligible)
                )
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
    replay_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "medium"
    reasoning_mode: Literal["standard", "pro"] = "standard"
    service_tier: Literal["default", "flex", "priority"] = "default"
    temperature: float = 0
    max_output_tokens: int = Field(default=4096, ge=1)
    input_price_per_million_usd: float | None = Field(default=None, ge=0)
    cached_input_price_per_million_usd: float | None = Field(default=None, ge=0)
    cache_write_input_price_per_million_usd: float | None = Field(default=None, ge=0)
    output_price_per_million_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_replay_identity(self) -> ModelConfig:
        if self.provider == "replay":
            if not self.model_id.startswith("replay:") or self.replay_hash is None:
                raise ValueError("replay provider requires a replay model ID and content hash")
        elif self.replay_hash is not None:
            raise ValueError("replay_hash is only valid for the replay provider")
        return self


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
    experiment: ExperimentRunContext | None = None
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
    tool_schema_version: Literal["v1", "v2"] = "v1"
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
    model_config = ConfigDict(extra="forbid", frozen=False, validate_assignment=True)

    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cache_write_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_output_tokens: int = Field(default=0, ge=0)
    model_cost_usd: float = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    input_token_count_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    wall_clock_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_input_token_breakdown(self) -> Usage:
        accounted_input = self.cached_input_tokens + self.cache_write_input_tokens
        if accounted_input > self.input_tokens:
            raise ValueError(
                "cached_input_tokens + cache_write_input_tokens "
                "must not exceed input_tokens"
            )
        if self.reasoning_output_tokens > self.output_tokens:
            raise ValueError("reasoning_output_tokens must not exceed output_tokens")
        return self


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
    outcome_kind: RunOutcomeKind | None = None
    terminal_error: dict[str, str] | None = None

    @model_validator(mode="after")
    def derive_outcome_kind(self) -> RunResult:
        if self.outcome_kind is None:
            if self.scope_compliant_success:
                self.outcome_kind = RunOutcomeKind.RESOLVED
            elif self.evaluation_status == "completed":
                self.outcome_kind = RunOutcomeKind.TASK_FAILURE
            else:
                self.outcome_kind = RunOutcomeKind.AGENT_FAILURE
        return self


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
