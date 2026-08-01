"""Versioned public contracts for tasks, runs, tools, memory, and evaluation."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.util import safe_relative_path, sha256_json


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
    MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT = (
        "memory-development-no-memory-budget-pilot"
    )
    MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT = (
        "memory-development-no-memory-corrective-pilot"
    )
    MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT = (
        "memory-development-no-memory-saturation-pilot"
    )
    MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT = (
        "memory-development-no-memory-review-evidence-pilot"
    )
    MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT = (
        "memory-development-no-memory-coverage-review-pilot"
    )
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
    MODEL_GENERATION_BLOCKED = "ModelGenerationBlocked"
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
    TOOL_ADMISSION_BLOCKED = "ToolAdmissionBlocked"
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


class RegisteredProbeProfile(StrictModel):
    """Public opt-in for one bounded, non-authoritative diagnostic runtime."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]+$")
    runtime: Literal["ephemeral-python-v1"] = "ephemeral-python-v1"
    timeout_seconds: int = Field(default=30, ge=1, le=60)
    output_limit_bytes: int = Field(default=64_000, ge=1, le=64_000)
    source_limit_bytes: int = Field(default=12_000, ge=1, le=12_000)


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
    schema_version: Literal["task-public-v1", "task-public-v2"] = "task-public-v1"
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(default=1, ge=1)
    split: Literal[
        "smoke", "dev-train", "dev-validation", "same-repo-heldout", "cross-repo-heldout"
    ]
    repository: RepositorySpec
    issue: IssueSpec
    constraints: TaskConstraints = Field(default_factory=TaskConstraints)
    visible_checks: list[RegisteredCheck] = Field(default_factory=list)
    probe_profiles: list[RegisteredProbeProfile] = Field(
        default_factory=list,
        exclude_if=lambda value: not value,
    )
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def bind_probe_profiles_to_v2(self) -> PublicTask:
        if (
            self.schema_version == "task-public-v1"
            and "probe_profiles" in self.model_fields_set
        ):
            raise ValueError("probe_profiles requires task-public-v2")
        if self.schema_version == "task-public-v2" and not self.probe_profiles:
            raise ValueError("task-public-v2 requires at least one probe profile")
        ids = [profile.id for profile in self.probe_profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("probe profile IDs must be unique")
        return self


class PublicReviewCoverageTarget(StrictModel):
    """One public, requirement-bound code or validation coverage target."""

    coverage_target_id: str = Field(pattern=r"^cov-[0-9a-f]{12}$")
    description: str = Field(min_length=1, max_length=1_000)
    evidence_kind: Literal[
        "current_diff_inspection",
        "passing_validation",
    ]
    path: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    anchor: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        exclude_if=lambda value: value is None,
    )
    check_ids: list[str] = Field(
        default_factory=list,
        max_length=20,
        exclude_if=lambda value: not value,
    )

    @field_validator("description")
    @classmethod
    def validate_normalized_description(cls, value: str) -> str:
        if re.sub(r"\s+", " ", value).strip() != value:
            raise ValueError(
                "public review coverage target description must use normalized whitespace"
            )
        return value

    @field_validator("path")
    @classmethod
    def validate_public_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return safe_relative_path(value, field_name="public review coverage target path")

    @field_validator("anchor")
    @classmethod
    def validate_exact_anchor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value != value.strip() or "\n" in value or "\r" in value:
            raise ValueError(
                "public review coverage target anchor must be one exact, trimmed line"
            )
        return value

    @field_validator("check_ids")
    @classmethod
    def validate_check_ids(cls, values: list[str]) -> list[str]:
        if any(re.fullmatch(r"[a-z][a-z0-9_-]+", value) is None for value in values):
            raise ValueError("public review coverage target check IDs are invalid")
        if values != sorted(set(values)):
            raise ValueError(
                "public review coverage target check IDs must be unique and sorted"
            )
        return values

    @model_validator(mode="after")
    def validate_evidence_shape(self) -> PublicReviewCoverageTarget:
        if self.evidence_kind == "current_diff_inspection":
            if self.path is None or self.anchor is None:
                raise ValueError(
                    "current-diff inspection coverage targets require path and anchor"
                )
            if "check_ids" in self.model_fields_set:
                raise ValueError(
                    "current-diff inspection coverage targets cannot declare check_ids"
                )
        else:
            if not self.check_ids:
                raise ValueError(
                    "passing-validation coverage targets require nonempty check_ids"
                )
            if "path" in self.model_fields_set or "anchor" in self.model_fields_set:
                raise ValueError(
                    "passing-validation coverage targets cannot declare path or anchor"
                )
        return self


class PublicReviewRequirement(StrictModel):
    """One stable, public issue clause required by structured review."""

    requirement_id: str = Field(pattern=r"^req-[0-9a-f]{12}$")
    source: Literal["issue.description"] = "issue.description"
    source_excerpt: str = Field(min_length=1, max_length=1_000)
    coverage_targets: list[PublicReviewCoverageTarget] = Field(
        default_factory=list,
        max_length=20,
        exclude_if=lambda value: not value,
    )


class PublicReviewContract(StrictModel):
    """Hash-bound public checklist without evaluator or reference data."""

    schema_version: Literal[
        "public-review-contract-v1",
        "public-review-contract-v2",
    ] = (
        "public-review-contract-v1"
    )
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(ge=1)
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requirements: list[PublicReviewRequirement] = Field(
        min_length=1,
        max_length=20,
    )
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identity_and_hash(self) -> PublicReviewContract:
        requirement_ids = [
            requirement.requirement_id
            for requirement in self.requirements
        ]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("public review requirement IDs must be unique")
        source_excerpts = [
            requirement.source_excerpt
            for requirement in self.requirements
        ]
        if len(source_excerpts) != len(set(source_excerpts)):
            raise ValueError(
                "public review source excerpts must be unique"
            )
        coverage_targets = [
            target
            for requirement in self.requirements
            for target in requirement.coverage_targets
        ]
        if self.schema_version == "public-review-contract-v1":
            if any(
                "coverage_targets" in requirement.model_fields_set
                for requirement in self.requirements
            ):
                raise ValueError(
                    "public-review-contract-v1 cannot declare coverage targets"
                )
        else:
            if any(not requirement.coverage_targets for requirement in self.requirements):
                raise ValueError(
                    "public-review-contract-v2 requires coverage targets for every requirement"
                )
            if len(coverage_targets) > 20:
                raise ValueError(
                    "public-review-contract-v2 supports at most 20 coverage targets"
                )
            target_ids = [
                target.coverage_target_id for target in coverage_targets
            ]
            if len(target_ids) != len(set(target_ids)):
                raise ValueError("public review coverage target IDs must be unique")
        expected_hash = sha256_json(
            self.model_dump(mode="json", exclude={"content_hash"})
        )
        if self.content_hash != expected_hash:
            raise ValueError("public review contract content hash mismatch")
        return self


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
    type: Literal[
        "none",
        "context-reset",
        "worker-kill-after-patch",
        "test-timeout",
        "controlled-reject-first-prepared-patch",
    ] = "none"
    trigger_after: int | None = None

    @model_validator(mode="after")
    def validate_controlled_rejection_trigger(self) -> FaultSpec:
        if (
            self.type == "controlled-reject-first-prepared-patch"
            and self.trigger_after != 1
        ):
            raise ValueError(
                "controlled rejection requires trigger_after=1"
            )
        return self


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
    probe_image_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    public_review_contract: PublicReviewContract | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    fault: FaultSpec = Field(default_factory=FaultSpec)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    experiment: ExperimentRunContext | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_corrective_runtime_contract(self) -> RunManifest:
        corrective_pair_v7 = (
            self.tool_schema_version == "v4"
            and self.context_policy_version == "phase-evidence-v7"
        )
        saturation_pair_v8 = (
            self.tool_schema_version == "v4"
            and self.context_policy_version == "phase-evidence-v8"
        )
        review_evidence_pair_v9 = (
            self.tool_schema_version == "v4"
            and self.context_policy_version == "phase-evidence-v9"
        )
        coverage_review_pair_v10 = (
            self.tool_schema_version == "v5"
            and self.context_policy_version == "phase-evidence-v10"
        )
        corrective_pair = (
            corrective_pair_v7
            or saturation_pair_v8
            or review_evidence_pair_v9
            or coverage_review_pair_v10
        )
        corrective_declared = bool(
            self.tool_schema_version in {"v4", "v5"}
            or self.context_policy_version
            in {
                "phase-evidence-v7",
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
            }
            or self.public_review_contract is not None
        )
        if corrective_declared and (
            not corrective_pair or self.public_review_contract is None
        ):
            raise ValueError(
                "corrective runtime requires an exact v4/v7-v9 or v5/v10 pair, "
                "and a public review contract"
            )
        if (
            self.public_review_contract is not None
            and (
                (
                    coverage_review_pair_v10
                    and self.public_review_contract.schema_version
                    != "public-review-contract-v2"
                )
                or (
                    not coverage_review_pair_v10
                    and self.public_review_contract.schema_version
                    != "public-review-contract-v1"
                )
            )
        ):
            raise ValueError(
                "public review contract version conflicts with the runtime pair"
            )
        if (
            self.experiment is not None
            and self.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
            and not corrective_pair_v7
        ):
            raise ValueError(
                "corrective pilot purpose requires the v4/v7 runtime contract"
            )
        saturation_live_pilot = bool(
            self.experiment is not None
            and self.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
        )
        if (
            saturation_pair_v8
            and self.experiment is not None
            and not saturation_live_pilot
        ):
            raise ValueError(
                "phase-evidence-v8 saturation context is offline-only and "
                "cannot declare an experiment context outside the exact "
                "saturation pilot purpose"
            )
        if (
            saturation_pair_v8
            and self.model.provider != "mock"
            and not (
                saturation_live_pilot
                and self.model.provider == "openai"
            )
        ):
            raise ValueError(
                "phase-evidence-v8 saturation context is offline-only and "
                "requires the mock provider outside the exact saturation "
                "pilot purpose"
            )
        if saturation_live_pilot and not saturation_pair_v8:
            raise ValueError(
                "saturation pilot purpose requires the v4/v8 runtime contract"
            )
        if saturation_live_pilot and self.model.provider != "openai":
            raise ValueError(
                "saturation pilot purpose requires the OpenAI provider"
            )
        review_evidence_live_pilot = bool(
            self.experiment is not None
            and self.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
        )
        if (
            review_evidence_pair_v9
            and self.experiment is not None
            and not review_evidence_live_pilot
        ):
            raise ValueError(
                "phase-evidence-v9 review evidence is offline-only and cannot "
                "declare an experiment context outside the exact review-evidence "
                "pilot purpose"
            )
        if (
            review_evidence_pair_v9
            and self.model.provider != "mock"
            and not (
                review_evidence_live_pilot
                and self.model.provider == "openai"
            )
        ):
            raise ValueError(
                "phase-evidence-v9 review evidence is offline-only and requires "
                "the mock provider outside the exact review-evidence pilot purpose"
            )
        if review_evidence_live_pilot and not review_evidence_pair_v9:
            raise ValueError(
                "review-evidence pilot purpose requires the v4/v9 runtime contract"
            )
        if review_evidence_live_pilot and self.model.provider != "openai":
            raise ValueError(
                "review-evidence pilot purpose requires the OpenAI provider"
            )
        coverage_review_live_pilot = bool(
            self.experiment is not None
            and self.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        )
        if (
            coverage_review_pair_v10
            and self.experiment is not None
            and not coverage_review_live_pilot
        ):
            raise ValueError(
                "phase-evidence-v10 coverage review is offline-only and cannot "
                "declare an experiment context outside the exact coverage-review "
                "pilot purpose"
            )
        if (
            coverage_review_pair_v10
            and self.model.provider != "mock"
            and not (
                coverage_review_live_pilot
                and self.model.provider == "openai"
            )
        ):
            raise ValueError(
                "phase-evidence-v10 coverage review is offline-only and requires "
                "the mock provider outside the exact coverage-review pilot purpose"
            )
        if coverage_review_live_pilot and not coverage_review_pair_v10:
            raise ValueError(
                "coverage-review pilot purpose requires the v5/v10 runtime contract"
            )
        if coverage_review_live_pilot and self.model.provider != "openai":
            raise ValueError(
                "coverage-review pilot purpose requires the OpenAI provider"
            )
        return self


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
    tool_schema_version: Literal["v1", "v2", "v3", "v4", "v5"] = "v1"
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
    terminal_error: dict[str, Any] | None = None

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


class MemoryReviewCampaign(StrictModel):
    report_path: str
    report_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    experiment_id: str = Field(min_length=1)
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dataset_manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("report_path")
    @classmethod
    def validate_report_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="campaign.report_path")


class MemoryReviewEvidenceBoundary(StrictModel):
    policy: Literal["agent-visible-public-evidence-v1"]
    allowed_sources: list[str] = Field(min_length=1)
    prohibited_sources_not_read: list[str] = Field(min_length=1)
    generic_outcome_only: bool

    @field_validator("allowed_sources", "prohibited_sources_not_read")
    @classmethod
    def validate_sources(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(not item.strip() for item in value):
            raise ValueError("evidence source lists must contain unique non-blank values")
        return value


class MemoryReviewSource(StrictModel):
    failure_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    submitted_patch_path: str
    submitted_patch_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_group_id: str = Field(min_length=1)
    evidence_event_sequences: list[int] = Field(min_length=1)
    assessment: str = Field(min_length=1)
    causal_confidence: float = Field(ge=0, le=1)
    disposition: Literal["candidate", "hold"]

    @field_validator("submitted_patch_path")
    @classmethod
    def validate_submitted_patch_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="source.submitted_patch_path")

    @field_validator("evidence_event_sequences")
    @classmethod
    def validate_evidence_sequences(cls, value: list[int]) -> list[int]:
        if any(sequence < 1 for sequence in value):
            raise ValueError("evidence event sequences must be positive")
        if value != sorted(set(value)):
            raise ValueError("evidence event sequences must be sorted and unique")
        return value


class MemoryReviewRule(StrictModel):
    failure_pattern: FailurePattern
    preconditions: list[str] = Field(min_length=1)
    diagnostic_evidence: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(min_length=1)
    do_not_apply_when: list[str] = Field(min_length=1)
    applicable_languages: list[Literal["python"]] = Field(default_factory=lambda: ["python"])
    confidence: float = Field(ge=0, le=1)


class MemoryReviewGroup(StrictModel):
    semantic_group_id: str = Field(min_length=1)
    representative_run_id: str = Field(min_length=1)
    member_failure_ids: list[str] = Field(min_length=1)
    member_run_ids: list[str] = Field(min_length=1)
    relation: Literal["single", "semantic-duplicate"]
    merge_rationale: str = Field(min_length=1)
    dedup_confidence: float = Field(ge=0, le=1)
    disposition: Literal["candidate", "hold"]
    rule: MemoryReviewRule

    @model_validator(mode="after")
    def validate_members(self) -> MemoryReviewGroup:
        if len(self.member_failure_ids) != len(set(self.member_failure_ids)):
            raise ValueError("group member_failure_ids must be unique")
        if len(self.member_run_ids) != len(set(self.member_run_ids)):
            raise ValueError("group member_run_ids must be unique")
        if len(self.member_failure_ids) != len(self.member_run_ids):
            raise ValueError("group failure and run member counts must match")
        expected_relation = (
            "single" if len(self.member_run_ids) == 1 else "semantic-duplicate"
        )
        if self.relation != expected_relation:
            raise ValueError("group relation does not match its member count")
        if self.representative_run_id not in self.member_run_ids:
            raise ValueError("group representative_run_id must be a member")
        return self


class MemoryReviewExcludedRun(StrictModel):
    run_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class MemoryReviewProducer(StrictModel):
    kind: Literal["maintainer-assisted", "model-self-review"]
    method: str = Field(min_length=1)
    model_id: str | None = Field(default=None, min_length=1)
    response_artifact_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def validate_model_provenance(self) -> MemoryReviewProducer:
        model_fields_present = self.model_id is not None and self.response_artifact_hash is not None
        if self.kind == "model-self-review" and not model_fields_present:
            raise ValueError(
                "model self-review requires model_id and response_artifact_hash"
            )
        if self.kind == "maintainer-assisted" and (
            self.model_id is not None or self.response_artifact_hash is not None
        ):
            raise ValueError(
                "maintainer-assisted review must not claim model response provenance"
            )
        return self


class MemoryReviewProposal(StrictModel):
    schema_version: Literal["memory-review-proposal-v1"] = "memory-review-proposal-v1"
    proposal_id: str = Field(min_length=1)
    producer: MemoryReviewProducer
    campaign: MemoryReviewCampaign
    evidence_boundary: MemoryReviewEvidenceBoundary
    sources: list[MemoryReviewSource] = Field(min_length=1)
    groups: list[MemoryReviewGroup] = Field(min_length=1)
    excluded_runs: list[MemoryReviewExcludedRun] = Field(default_factory=list)
    human_review_status: Literal["pending"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_unique_identities(self) -> MemoryReviewProposal:
        identity_lists = {
            "source failure IDs": [source.failure_id for source in self.sources],
            "source run IDs": [source.run_id for source in self.sources],
            "semantic group IDs": [group.semantic_group_id for group in self.groups],
            "excluded run IDs": [item.run_id for item in self.excluded_runs],
        }
        for label, values in identity_lists.items():
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        source_runs = {source.run_id for source in self.sources}
        excluded_runs = {item.run_id for item in self.excluded_runs}
        if source_runs & excluded_runs:
            raise ValueError("source and excluded run IDs must be disjoint")
        return self


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
