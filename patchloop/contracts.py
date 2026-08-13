"""Versioned public contracts for tasks, runs, tools, memory, and evaluation."""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.util import safe_relative_path, sha256_bytes, sha256_json


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class FrozenStrictModel(BaseModel):
    """Immutable base for content-addressed evaluator-v2 values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


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
    GENERIC_BASELINE_READINESS = "generic-baseline-readiness"
    WORKFLOW_COMPLETION_PROBE = "workflow-completion-probe"
    DEVELOPMENT_VALIDATION_LIVE_PILOT = "development-validation-live-pilot"
    DEVELOPMENT_VALIDATION_AC_READINESS = "development-validation-ac-readiness"
    DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT = "development-validation-model-candidate-pilot"
    MEMORY_DEVELOPMENT_NO_MEMORY = "memory-development-no-memory"
    MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT = "memory-development-no-memory-budget-pilot"
    MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT = "memory-development-no-memory-corrective-pilot"
    MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT = "memory-development-no-memory-saturation-pilot"
    MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT = (
        "memory-development-no-memory-review-evidence-pilot"
    )
    MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT = (
        "memory-development-no-memory-coverage-review-pilot"
    )
    MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT = (
        "memory-development-no-memory-coverage-rejection-pilot"
    )
    CORE = "core"


CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID = (
    "dev-validation-condition-neutral-v2v5-pilot-20260803-r1"
)
CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID = (
    "dev-no-memory-condition-neutral-accrued-cap-20260804-r1"
)
CONDITION_NEUTRAL_BUDGET_READINESS_PROBE_EXPERIMENT_ID = (
    "anyio-workflow-completion-budget-only-v2v5-20260804-r1"
)
GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID = "generic-high-headroom-readiness-v2v5-20260804-r1"
CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID = "dev-no-memory-condition-neutral-3000k-20260805-r1"
AC_FIXED_BUNDLE_READINESS_EXPERIMENT_ID = "dev-validation-ac-fixed-bundle-readiness-20260808-r1"
AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID = (
    "dev-validation-ac-fixed-bundle-readiness-20260808-r2"
)
AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID = "dev-validation-ac-fixed-bundle-readiness-20260813-r3"
AC_FIXED_BUNDLE_EXPERIMENT_IDS = frozenset(
    {
        AC_FIXED_BUNDLE_READINESS_EXPERIMENT_ID,
        AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID,
    }
)
AC_FIXED_BUNDLE_COST_EXPERIMENT_IDS = frozenset(
    {
        AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID,
    }
)
AC_FIXED_BUNDLE_POLICY_VERSION = "fixed-d110-bundle-v1"
AC_FIXED_BUNDLE_D110_INDEX_VERSION = (
    "idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064"
)
AC_FIXED_BUNDLE_D110_INDEX_CONTENT_HASH = (
    "sha256:3a99e6c190672d1676bc4d13604de989899de9ddac85d282cc90c4d56f426c56"
)


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


class SafetyControlKind(StrEnum):
    COMMAND = "command"
    NETWORK = "network"
    SECRET = "secret"
    SANDBOX = "sandbox"


class SafetyEvidenceProducer(StrEnum):
    RUNTIME_TRACE = "runtime_trace"
    SANDBOX_POLICY_TRACE = "sandbox_policy_trace"
    ARTIFACT_SCAN = "artifact_scan"


class SafetyPolicyProfile(StrEnum):
    REGISTERED_GATEWAY_DISPATCH_V1 = "registered_gateway_dispatch_v1"
    DOCKER_REGISTERED_CHECK_REQUESTED_NETWORK_NONE_V1 = (
        "docker_registered_check_requested_network_none_v1"
    )
    ENUMERATED_CHAIN_EXACT_MARKER_SCAN_V1 = "enumerated_chain_exact_marker_scan_v1"
    DOCKER_REGISTERED_CHECK_REQUESTED_CONFINEMENT_V1 = (
        "docker_registered_check_requested_confinement_v1"
    )


class SafetyEvidenceReason(StrEnum):
    POLICY_VIOLATION = "policy_violation"
    CHECKER_ERROR = "checker_error"
    INTEGRITY_ERROR = "integrity_error"
    REQUIRED_EVIDENCE_MISSING = "required_evidence_missing"
    NOT_EXECUTED = "not_executed"


DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1 = {
    "schema_version": "docker-registered-check-request-policy-v1",
    "requested_network": "none",
    "read_only_root": True,
    "read_only_workspace": True,
    "cpus": "2",
    "memory": "2g",
    "pids_limit": 128,
    "tmpfs": "/tmp:rw,noexec,nosuid,size=256m",
}


def docker_registered_check_policy_input_hash(
    profile: SafetyPolicyProfile,
    check_ids: tuple[str, ...],
) -> str:
    """Commit one sandbox-policy requirement to exact registered checks and flags."""

    payload: dict[str, Any] = {
        "schema_version": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["schema_version"],
        "registered_check_ids": list(check_ids),
        "requested_network": DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1["requested_network"],
    }
    if profile == SafetyPolicyProfile.DOCKER_REGISTERED_CHECK_REQUESTED_CONFINEMENT_V1:
        payload.update(DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1)
        payload["registered_check_ids"] = list(check_ids)
    elif profile != SafetyPolicyProfile.DOCKER_REGISTERED_CHECK_REQUESTED_NETWORK_NONE_V1:
        raise ValueError("unsupported Docker registered-check safety profile")
    return sha256_json(payload)


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
        if self.schema_version == "task-public-v1" and "probe_profiles" in self.model_fields_set:
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
            raise ValueError("public review coverage target anchor must be one exact, trimmed line")
        return value

    @field_validator("check_ids")
    @classmethod
    def validate_check_ids(cls, values: list[str]) -> list[str]:
        if any(re.fullmatch(r"[a-z][a-z0-9_-]+", value) is None for value in values):
            raise ValueError("public review coverage target check IDs are invalid")
        if values != sorted(set(values)):
            raise ValueError("public review coverage target check IDs must be unique and sorted")
        return values

    @model_validator(mode="after")
    def validate_evidence_shape(self) -> PublicReviewCoverageTarget:
        if self.evidence_kind == "current_diff_inspection":
            if self.path is None or self.anchor is None:
                raise ValueError("current-diff inspection coverage targets require path and anchor")
            if "check_ids" in self.model_fields_set:
                raise ValueError(
                    "current-diff inspection coverage targets cannot declare check_ids"
                )
        else:
            if not self.check_ids:
                raise ValueError("passing-validation coverage targets require nonempty check_ids")
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
    ] = "public-review-contract-v1"
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
        requirement_ids = [requirement.requirement_id for requirement in self.requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("public review requirement IDs must be unique")
        source_excerpts = [requirement.source_excerpt for requirement in self.requirements]
        if len(source_excerpts) != len(set(source_excerpts)):
            raise ValueError("public review source excerpts must be unique")
        coverage_targets = [
            target for requirement in self.requirements for target in requirement.coverage_targets
        ]
        if self.schema_version == "public-review-contract-v1":
            if any(
                "coverage_targets" in requirement.model_fields_set
                for requirement in self.requirements
            ):
                raise ValueError("public-review-contract-v1 cannot declare coverage targets")
        else:
            if any(not requirement.coverage_targets for requirement in self.requirements):
                raise ValueError(
                    "public-review-contract-v2 requires coverage targets for every requirement"
                )
            if len(coverage_targets) > 20:
                raise ValueError("public-review-contract-v2 supports at most 20 coverage targets")
            target_ids = [target.coverage_target_id for target in coverage_targets]
            if len(target_ids) != len(set(target_ids)):
                raise ValueError("public review coverage target IDs must be unique")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
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


class SafetyRequirement(FrozenStrictModel):
    """One evaluator-private safety control and its evidence producer."""

    schema_version: Literal["safety-requirement-v2"] = "safety-requirement-v2"
    requirement_id: str = Field(pattern=r"^[a-z][a-z0-9_-]+$")
    control: SafetyControlKind
    evidence_producer: SafetyEvidenceProducer
    policy_profile: SafetyPolicyProfile
    policy_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_input_count: int = Field(ge=1)
    required_evidence_roles: tuple[str, ...] = Field(min_length=1)
    check_ids: tuple[str, ...] = Field(default_factory=tuple)
    required: Literal[True] = True

    @model_validator(mode="after")
    def validate_check_binding(self) -> SafetyRequirement:
        if tuple(sorted(set(self.required_evidence_roles))) != self.required_evidence_roles or any(
            re.fullmatch(r"[a-z][a-z0-9_]{0,63}", role) is None
            for role in self.required_evidence_roles
        ):
            raise ValueError("required safety evidence roles must be valid, unique, and sorted")
        if tuple(sorted(set(self.check_ids))) != self.check_ids:
            raise ValueError("safety requirement check IDs must be unique and sorted")
        if self.evidence_producer == SafetyEvidenceProducer.SANDBOX_POLICY_TRACE:
            if not self.check_ids:
                raise ValueError("sandbox-audit safety evidence requires registered check IDs")
            if any(
                re.fullmatch(r"(?:hidden|regression):[a-z][a-z0-9_-]+", check_id) is None
                for check_id in self.check_ids
            ):
                raise ValueError("sandbox-audit check IDs must be role-prefixed registered IDs")
            if self.policy_input_count != len(self.check_ids):
                raise ValueError("sandbox-audit policy input count must match registered checks")
            if self.policy_input_hash != docker_registered_check_policy_input_hash(
                self.policy_profile,
                self.check_ids,
            ):
                raise ValueError("sandbox-audit policy hash must bind exact requested flags")
        elif self.check_ids:
            raise ValueError("registered check IDs are only valid for sandbox-audit evidence")
        return self


def safety_requirement_hash(requirement: SafetyRequirement) -> str:
    """Return the opaque public identity of one private safety requirement."""

    return sha256_json(requirement.model_dump(mode="json"))


_SAFETY_CONTROL_ORDER = (
    SafetyControlKind.COMMAND,
    SafetyControlKind.NETWORK,
    SafetyControlKind.SECRET,
    SafetyControlKind.SANDBOX,
)
_SAFETY_POLICY_BY_CONTROL = {
    SafetyControlKind.COMMAND: (
        SafetyEvidenceProducer.RUNTIME_TRACE,
        SafetyPolicyProfile.REGISTERED_GATEWAY_DISPATCH_V1,
    ),
    SafetyControlKind.NETWORK: (
        SafetyEvidenceProducer.SANDBOX_POLICY_TRACE,
        SafetyPolicyProfile.DOCKER_REGISTERED_CHECK_REQUESTED_NETWORK_NONE_V1,
    ),
    SafetyControlKind.SECRET: (
        SafetyEvidenceProducer.ARTIFACT_SCAN,
        SafetyPolicyProfile.ENUMERATED_CHAIN_EXACT_MARKER_SCAN_V1,
    ),
    SafetyControlKind.SANDBOX: (
        SafetyEvidenceProducer.SANDBOX_POLICY_TRACE,
        SafetyPolicyProfile.DOCKER_REGISTERED_CHECK_REQUESTED_CONFINEMENT_V1,
    ),
}
_SAFETY_EVIDENCE_ROLES_BY_PROFILE = {
    SafetyPolicyProfile.REGISTERED_GATEWAY_DISPATCH_V1: ("registered_gateway_trace",),
    SafetyPolicyProfile.DOCKER_REGISTERED_CHECK_REQUESTED_NETWORK_NONE_V1: (
        "docker_network_policy_trace",
    ),
    SafetyPolicyProfile.ENUMERATED_CHAIN_EXACT_MARKER_SCAN_V1: (
        "run_bound_marker_projection",
        "scanned_artifact_inventory",
        "scanned_event_prefix",
        "scanned_patch",
    ),
    SafetyPolicyProfile.DOCKER_REGISTERED_CHECK_REQUESTED_CONFINEMENT_V1: (
        "docker_confinement_policy_trace",
    ),
}
_SAFETY_AGGREGATION_PRECEDENCE = (
    VerdictState.ERROR,
    VerdictState.FAIL,
    VerdictState.NOT_RUN,
    VerdictState.PASS,
)
_SCOPE_POLICY_CHECK_IDS = ("dependency", "public_api", "scope", "test_tampering")


def _check_id_set_hash(check_ids: tuple[str, ...] | list[str]) -> str:
    return sha256_json(sorted(check_ids))


class EvaluatorSafetyContract(FrozenStrictModel):
    """Private, task-bound safety inputs for evaluator-v2."""

    schema_version: Literal["evaluator-safety-contract-v2"] = "evaluator-safety-contract-v2"
    contract_id: str = Field(pattern=r"^[a-z][a-z0-9_-]+$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(ge=1)
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requirements: tuple[SafetyRequirement, ...] = Field(min_length=4, max_length=4)
    aggregation_precedence: tuple[VerdictState, ...] = _SAFETY_AGGREGATION_PRECEDENCE
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> EvaluatorSafetyContract:
        requirement_ids = tuple(item.requirement_id for item in self.requirements)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("safety requirement IDs must be unique")
        controls = tuple(item.control for item in self.requirements)
        if controls != _SAFETY_CONTROL_ORDER:
            raise ValueError(
                "evaluator-v2 requires one canonically ordered requirement per control"
            )
        actual_policy = tuple(
            (item.evidence_producer, item.policy_profile) for item in self.requirements
        )
        expected_policy = tuple(_SAFETY_POLICY_BY_CONTROL[control] for control in controls)
        if actual_policy != expected_policy:
            raise ValueError(
                "evaluator-v2 control, producer, and policy profile mapping is invalid"
            )
        if any(
            item.required_evidence_roles != _SAFETY_EVIDENCE_ROLES_BY_PROFILE[item.policy_profile]
            for item in self.requirements
        ):
            raise ValueError("evaluator-v2 policy profile has an invalid evidence-role inventory")
        if self.aggregation_precedence != _SAFETY_AGGREGATION_PRECEDENCE:
            raise ValueError("evaluator-v2 aggregation precedence must be fail-closed")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("evaluator safety contract content hash mismatch")
        return self


class EvaluatorContractBinding(FrozenStrictModel):
    """Agent-visible hashes; private requirement and check IDs stay evaluator-only."""

    schema_version: Literal["evaluator-contract-binding-v2"] = "evaluator-contract-binding-v2"
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(ge=1)
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contract_id: str = Field(pattern=r"^[a-z][a-z0-9_-]+$")
    contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    safety_requirement_count: Literal[4]
    required_safety_requirement_hashes: tuple[str, ...] = Field(min_length=4, max_length=4)
    requirement_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    hidden_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    regression_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scope_check_ids_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    registered_check_specs_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("required_safety_requirement_hashes")
    @classmethod
    def validate_requirement_hashes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None for value in values):
            raise ValueError("required safety requirement hashes must be SHA-256 identities")
        if len(values) != len(set(values)):
            raise ValueError("required safety requirement hashes must be unique")
        return values

    @model_validator(mode="after")
    def validate_projection_hashes(self) -> EvaluatorContractBinding:
        if self.safety_requirement_count != len(self.required_safety_requirement_hashes):
            raise ValueError("safety requirement count disagrees with the hash projection")
        if self.requirement_set_hash != _check_id_set_hash(
            list(self.required_safety_requirement_hashes)
        ):
            raise ValueError("safety requirement set hash mismatch")
        if self.scope_check_ids_hash != _check_id_set_hash(list(_SCOPE_POLICY_CHECK_IDS)):
            raise ValueError("scope policy check-set hash mismatch")
        return self


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
        public_spec_hash, private_spec_hash = task_package_spec_hashes(
            self.public,
            self.private,
        )
        if self.public_spec_hash != public_spec_hash:
            raise ValueError("task package public spec hash mismatch")
        if self.private_spec_hash != private_spec_hash:
            raise ValueError("task package private spec hash mismatch")
        return self


def task_package_spec_hashes(
    public: PublicTask,
    private: PrivateTask,
) -> tuple[str, str]:
    """Compute the frozen public/private task identities used by the loader."""

    private_identity = private.model_dump(mode="json")
    if private.schema_version == "task-private-v1":
        # Preserve the frozen v1 identity algorithm after adding the v2-only field.
        private_identity.pop("hidden_artifacts", None)
    return (
        sha256_json(public.model_dump(mode="json")),
        sha256_json(private_identity),
    )


def _registered_check_projection(
    package: TaskPackage,
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    hidden_ids = [check.id for check in package.private.hidden_checks]
    regression_ids = [check.id for check in package.public.visible_checks]
    if len(hidden_ids) != len(set(hidden_ids)):
        raise ValueError("private hidden check IDs must be unique for evaluator-v2")
    if len(regression_ids) != len(set(regression_ids)):
        raise ValueError("public regression check IDs must be unique for evaluator-v2")
    specs = [
        {"role": "hidden", "check": check.model_dump(mode="json")}
        for check in package.private.hidden_checks
    ] + [
        {"role": "regression", "check": check.model_dump(mode="json")}
        for check in package.public.visible_checks
    ]
    specs.sort(key=lambda item: (item["role"], item["check"]["id"]))
    return sorted(hidden_ids), sorted(regression_ids), specs


def registered_check_result_hash(
    role: Literal["hidden", "regression"], check: RegisteredCheck
) -> str:
    """Opaque v2 result identity that commits to a registered check specification."""

    return sha256_json({"role": role, "check": check.model_dump(mode="json")})


def build_evaluator_contract_binding(
    contract: EvaluatorSafetyContract,
    package: TaskPackage,
    *,
    evaluator_source_hash: str,
) -> EvaluatorContractBinding:
    """Bind a private evaluator-v2 contract to one exact task package."""

    contract = EvaluatorSafetyContract.model_validate(contract.model_dump(mode="json"))
    package = TaskPackage.model_validate(package.model_dump(mode="json"))
    if re.fullmatch(r"sha256:[0-9a-f]{64}", evaluator_source_hash) is None:
        raise ValueError("evaluator source hash must be a SHA-256 identity")
    expected_identity = (
        package.public.task_id,
        package.public.task_version,
        package.public_spec_hash,
        package.private_spec_hash,
    )
    contract_identity = (
        contract.task_id,
        contract.task_version,
        contract.public_spec_hash,
        contract.private_spec_hash,
    )
    if contract_identity != expected_identity:
        raise ValueError("evaluator safety contract belongs to a different task package")
    hidden_ids, regression_ids, registered_specs = _registered_check_projection(package)
    registered_ids = tuple(
        sorted(
            [f"hidden:{check_id}" for check_id in hidden_ids]
            + [f"regression:{check_id}" for check_id in regression_ids]
        )
    )
    sandbox_requirements = tuple(
        requirement
        for requirement in contract.requirements
        if requirement.evidence_producer == SafetyEvidenceProducer.SANDBOX_POLICY_TRACE
    )
    if not sandbox_requirements or any(
        requirement.check_ids != registered_ids for requirement in sandbox_requirements
    ):
        raise ValueError("sandbox-audit requirements must bind the exact registered check set")
    requirement_hashes = tuple(safety_requirement_hash(item) for item in contract.requirements)
    return EvaluatorContractBinding(
        task_id=contract.task_id,
        task_version=contract.task_version,
        public_spec_hash=contract.public_spec_hash,
        private_spec_hash=contract.private_spec_hash,
        contract_id=contract.contract_id,
        contract_hash=contract.content_hash,
        evaluator_source_hash=evaluator_source_hash,
        safety_requirement_count=len(requirement_hashes),
        required_safety_requirement_hashes=requirement_hashes,
        requirement_set_hash=_check_id_set_hash(list(requirement_hashes)),
        hidden_check_ids_hash=_check_id_set_hash(
            [
                registered_check_result_hash("hidden", check)
                for check in package.private.hidden_checks
            ]
        ),
        regression_check_ids_hash=_check_id_set_hash(
            [
                registered_check_result_hash("regression", check)
                for check in package.public.visible_checks
            ]
        ),
        scope_check_ids_hash=_check_id_set_hash(list(_SCOPE_POLICY_CHECK_IDS)),
        registered_check_specs_hash=sha256_json(registered_specs),
    )


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
    campaign_cost_control_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    dataset_manifest_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    dataset_role: DatasetRole | None = None
    schedule_seed: int
    schedule_order: int = Field(ge=1)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repetition: int = Field(ge=1)

    @model_validator(mode="after")
    def bind_campaign_cost_context(self) -> ExperimentRunContext:
        if self.experiment_id in {
            CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
            *AC_FIXED_BUNDLE_COST_EXPERIMENT_IDS,
        }:
            if self.campaign_cost_control_hash is None:
                raise ValueError(
                    "the exact full-schedule campaign requires campaign_cost_control_hash"
                )
            return self
        requires_cost_control = (
            self.experiment_id == CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID
        )
        if requires_cost_control != (self.campaign_cost_control_hash is not None):
            raise ValueError("the D-087 campaign alone requires campaign_cost_control_hash")
        return self


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
        if not (self.source.issue_url is not None and self.source.issue_url.strip()) and not (
            self.source.pull_request_url is not None and self.source.pull_request_url.strip()
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
            raise ValueError("stress selection_rationale keys must match the selected task_ids")
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
                raise ValueError("frozen stress lane requires rationale for every selected task")
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
                    "frozen stress lane requires admitted held-out tasks: " + ", ".join(ineligible)
                )
        return self


class Budget(StrictModel):
    max_model_calls: int | None = Field(default=20, ge=1)
    max_tool_calls: int | None = Field(default=50, ge=1)
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
    transport_max_retries: Literal[0] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    temperature: float = 0
    max_output_tokens: int = Field(default=4096, ge=1)
    input_price_per_million_usd: float | None = Field(default=None, ge=0)
    cached_input_price_per_million_usd: float | None = Field(default=None, ge=0)
    cache_write_input_price_per_million_usd: float | None = Field(default=None, ge=0)
    output_price_per_million_usd: float | None = Field(default=None, ge=0)

    @field_validator("transport_max_retries", mode="before")
    @classmethod
    def validate_transport_max_retries_type(cls, value: Any) -> Any:
        if value is not None and type(value) is not int:
            raise ValueError("transport_max_retries must be the JSON integer 0")
        return value

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
        if self.type == "controlled-reject-first-prepared-patch" and self.trigger_after != 1:
            raise ValueError("controlled rejection requires trigger_after=1")
        return self


class MemoryConfig(StrictModel):
    condition: MemoryCondition = MemoryCondition.NO_MEMORY
    index_version: str | None = None
    index_hash: str | None = None
    max_context_tokens: int = 2000


class RunManifest(StrictModel):
    schema_version: Literal["run-manifest-v1", "run-manifest-v2"] = "run-manifest-v1"
    run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    task_id: str
    task_version: int
    base_commit: str
    public_spec_hash: str
    private_spec_hash: str | None = None
    evaluator_contract: EvaluatorContractBinding | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
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
    def validate_evaluator_contract_binding(self) -> RunManifest:
        if self.schema_version == "run-manifest-v2":
            if self.evaluator_contract is None:
                raise ValueError("run-manifest-v2 requires an evaluator contract binding")
            if self.private_spec_hash is None or any(
                re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None
                for value in (self.public_spec_hash, self.private_spec_hash)
            ):
                raise ValueError("run-manifest-v2 requires public and private SHA-256 spec hashes")
            manifest_identity = (
                self.task_id,
                self.task_version,
                self.public_spec_hash,
                self.private_spec_hash,
            )
            binding_identity = (
                self.evaluator_contract.task_id,
                self.evaluator_contract.task_version,
                self.evaluator_contract.public_spec_hash,
                self.evaluator_contract.private_spec_hash,
            )
            if manifest_identity != binding_identity:
                raise ValueError("run-manifest-v2 evaluator binding belongs to a different task")
        elif self.evaluator_contract is not None:
            raise ValueError("evaluator contract binding requires run-manifest-v2")
        return self

    @model_validator(mode="after")
    def validate_corrective_runtime_contract(self) -> RunManifest:
        corrective_pair_v7 = (
            self.tool_schema_version == "v4" and self.context_policy_version == "phase-evidence-v7"
        )
        saturation_pair_v8 = (
            self.tool_schema_version == "v4" and self.context_policy_version == "phase-evidence-v8"
        )
        review_evidence_pair_v9 = (
            self.tool_schema_version == "v4" and self.context_policy_version == "phase-evidence-v9"
        )
        coverage_review_pair_v10 = (
            self.tool_schema_version == "v5" and self.context_policy_version == "phase-evidence-v10"
        )
        coverage_rejection_pair_v11 = (
            self.tool_schema_version == "v6" and self.context_policy_version == "phase-evidence-v11"
        )
        corrective_pair = (
            corrective_pair_v7
            or saturation_pair_v8
            or review_evidence_pair_v9
            or coverage_review_pair_v10
            or coverage_rejection_pair_v11
        )
        corrective_declared = bool(
            self.tool_schema_version in {"v4", "v5", "v6"}
            or self.context_policy_version
            in {
                "phase-evidence-v7",
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
                "phase-evidence-v11",
            }
            or self.public_review_contract is not None
        )
        if corrective_declared and (not corrective_pair or self.public_review_contract is None):
            raise ValueError(
                "corrective runtime requires an exact v4/v7-v9, v5/v10, or "
                "v6/v11 pair, and a public review contract"
            )
        if self.public_review_contract is not None and (
            (
                (coverage_review_pair_v10 or coverage_rejection_pair_v11)
                and self.public_review_contract.schema_version != "public-review-contract-v2"
            )
            or (
                not (coverage_review_pair_v10 or coverage_rejection_pair_v11)
                and self.public_review_contract.schema_version != "public-review-contract-v1"
            )
        ):
            raise ValueError("public review contract version conflicts with the runtime pair")
        if (
            self.experiment is not None
            and self.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
            and not corrective_pair_v7
        ):
            raise ValueError("corrective pilot purpose requires the v4/v7 runtime contract")
        saturation_live_pilot = bool(
            self.experiment is not None
            and self.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
        )
        if saturation_pair_v8 and self.experiment is not None and not saturation_live_pilot:
            raise ValueError(
                "phase-evidence-v8 saturation context is offline-only and "
                "cannot declare an experiment context outside the exact "
                "saturation pilot purpose"
            )
        if (
            saturation_pair_v8
            and self.model.provider != "mock"
            and not (saturation_live_pilot and self.model.provider == "openai")
        ):
            raise ValueError(
                "phase-evidence-v8 saturation context is offline-only and "
                "requires the mock provider outside the exact saturation "
                "pilot purpose"
            )
        if saturation_live_pilot and not saturation_pair_v8:
            raise ValueError("saturation pilot purpose requires the v4/v8 runtime contract")
        if saturation_live_pilot and self.model.provider != "openai":
            raise ValueError("saturation pilot purpose requires the OpenAI provider")
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
            and not (review_evidence_live_pilot and self.model.provider == "openai")
        ):
            raise ValueError(
                "phase-evidence-v9 review evidence is offline-only and requires "
                "the mock provider outside the exact review-evidence pilot purpose"
            )
        if review_evidence_live_pilot and not review_evidence_pair_v9:
            raise ValueError("review-evidence pilot purpose requires the v4/v9 runtime contract")
        if review_evidence_live_pilot and self.model.provider != "openai":
            raise ValueError("review-evidence pilot purpose requires the OpenAI provider")
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
            and not (coverage_review_live_pilot and self.model.provider == "openai")
        ):
            raise ValueError(
                "phase-evidence-v10 coverage review is offline-only and requires "
                "the mock provider outside the exact coverage-review pilot purpose"
            )
        if coverage_review_live_pilot and not coverage_review_pair_v10:
            raise ValueError("coverage-review pilot purpose requires the v5/v10 runtime contract")
        if coverage_review_live_pilot and self.model.provider != "openai":
            raise ValueError("coverage-review pilot purpose requires the OpenAI provider")
        coverage_rejection_live_pilot = bool(
            self.experiment is not None
            and self.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        )
        if (
            coverage_rejection_pair_v11
            and self.experiment is not None
            and not coverage_rejection_live_pilot
        ):
            raise ValueError(
                "phase-evidence-v11 coverage rejection recovery is offline-only "
                "and cannot declare an experiment context outside the exact "
                "coverage-rejection pilot purpose"
            )
        if (
            coverage_rejection_pair_v11
            and self.model.provider != "mock"
            and not (coverage_rejection_live_pilot and self.model.provider == "openai")
        ):
            raise ValueError(
                "phase-evidence-v11 coverage rejection recovery is offline-only "
                "and requires the mock provider outside the exact "
                "coverage-rejection pilot purpose"
            )
        if coverage_rejection_live_pilot and not coverage_rejection_pair_v11:
            raise ValueError(
                "coverage-rejection pilot purpose requires the v6/v11 runtime contract"
            )
        if coverage_rejection_live_pilot and self.model.provider != "openai":
            raise ValueError("coverage-rejection pilot purpose requires the OpenAI provider")
        generic_baseline_readiness = bool(
            self.experiment is not None
            and self.experiment.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS
        )
        workflow_completion_probe = bool(
            self.experiment is not None
            and self.experiment.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        )
        condition_neutral_budget_readiness_probe = bool(
            workflow_completion_probe
            and self.experiment is not None
            and self.experiment.experiment_id
            == CONDITION_NEUTRAL_BUDGET_READINESS_PROBE_EXPERIMENT_ID
            and self.task_id == "anyio-interrupt-runner-cleanup"
            and self.experiment.dataset_role == DatasetRole.MEMORY_DEVELOPMENT
            and self.experiment.schedule_seed == 20260723
            and self.experiment.schedule_order == 1
            and self.experiment.repetition == 1
        )
        claims_condition_neutral_budget_readiness_probe = bool(
            self.experiment is not None
            and self.experiment.experiment_id
            == CONDITION_NEUTRAL_BUDGET_READINESS_PROBE_EXPERIMENT_ID
        )
        if (
            claims_condition_neutral_budget_readiness_probe
            and not condition_neutral_budget_readiness_probe
        ):
            raise ValueError(
                "the D-089 budget-only readiness identity requires the exact "
                "workflow-completion AnyIO row"
            )
        condition_neutral_comparison_pilot = bool(
            self.experiment is not None
            and self.experiment.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
            and self.experiment.experiment_id == CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
            and self.task_id == "babel-strict-grouped-decimal-trailing-zeroes"
            and self.experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
            and self.experiment.schedule_seed == 20260723
            and self.experiment.schedule_order == 1
            and self.experiment.repetition == 1
        )
        future_comparison_purpose = (
            self.experiment.purpose
            if self.experiment is not None
            and self.experiment.purpose
            in {
                ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
                ExperimentPurpose.CORE,
            }
            else None
        )
        v2v5_live_contract = (
            self.tool_schema_version == "v2"
            and self.context_policy_version == "phase-evidence-v5"
            and self.model.provider == "openai"
            and self.model.reasoning_effort == "medium"
            and self.model.reasoning_mode == "standard"
            and self.model.service_tier == "default"
            and self.model.transport_max_retries == 0
            and self.memory.condition == MemoryCondition.NO_MEMORY
            and self.fault.type == "none"
            and self.public_review_contract is None
        )
        future_comparison_profile = bool(
            (future_comparison_purpose is not None or condition_neutral_comparison_pilot)
            and self.tool_schema_version == "v2"
            and self.context_policy_version == "phase-evidence-v5"
            and self.model.provider == "openai"
            and self.model.model_id == "gpt-5.4-mini-2026-03-17"
            and self.model.reasoning_effort == "medium"
            and self.model.reasoning_mode == "standard"
            and self.model.service_tier == "default"
            and self.model.transport_max_retries == 0
            and self.model.max_output_tokens == 25_000
            and self.budget.max_model_calls is None
            and self.budget.max_tool_calls is None
            and self.budget.max_total_tokens == 1_600_000
            and self.budget.wall_clock_timeout_seconds == 1_800
            and self.memory.max_context_tokens == 2_000
            and self.fault.type == "none"
            and self.public_review_contract is None
            and (
                future_comparison_purpose == ExperimentPurpose.CORE
                or self.memory.condition == MemoryCondition.NO_MEMORY
            )
        )
        prospective_no_memory_v2_order = {
            ("pyfakefs-makedirs-parent-traversal", 1): 1,
            ("pyfakefs-makedirs-parent-traversal", 2): 2,
            ("anyio-interrupt-runner-cleanup", 1): 3,
            ("hf-hub-xet-endpoint-propagation", 1): 4,
            ("pdm-ignore-active-venv-resolution", 1): 5,
            ("hf-hub-xet-endpoint-propagation", 2): 6,
            ("anyio-interrupt-runner-cleanup", 2): 7,
            ("loguru-invalid-format-feedback", 1): 8,
            ("loguru-invalid-format-feedback", 2): 9,
            ("tox-cross-section-empty-substitution", 2): 10,
            ("tox-cross-section-empty-substitution", 1): 11,
            ("pdm-ignore-active-venv-resolution", 2): 12,
        }
        prospective_no_memory_v2 = bool(
            self.experiment is not None
            and self.experiment.experiment_id == CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID
            and self.experiment.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
            and self.experiment.dataset_role == DatasetRole.MEMORY_DEVELOPMENT
            and self.experiment.schedule_seed == 20260723
            and self.experiment.repetition in {1, 2}
            and self.experiment.schedule_order
            == prospective_no_memory_v2_order.get((self.task_id, self.experiment.repetition))
            and self.tool_schema_version == "v2"
            and self.context_policy_version == "phase-evidence-v5"
            and self.model.provider == "openai"
            and self.model.model_id == "gpt-5.4-mini-2026-03-17"
            and self.model.reasoning_effort == "medium"
            and self.model.reasoning_mode == "standard"
            and self.model.service_tier == "default"
            and self.model.transport_max_retries == 0
            and self.model.max_output_tokens == 25_000
            and self.budget.max_model_calls is None
            and self.budget.max_tool_calls is None
            and self.budget.max_total_tokens == 3_000_000
            and self.budget.wall_clock_timeout_seconds == 3_600
            and self.memory.condition == MemoryCondition.NO_MEMORY
            and self.memory.max_context_tokens == 2_000
            and self.fault.type == "none"
            and self.public_review_contract is None
        )
        claims_prospective_no_memory_v2 = bool(
            self.experiment is not None
            and self.experiment.experiment_id == CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID
        )
        if claims_prospective_no_memory_v2 and not prospective_no_memory_v2:
            raise ValueError(
                "the D-097 no-memory identity requires its exact frozen row and "
                "condition-neutral 3M/3600 runtime tuple"
            )
        if generic_baseline_readiness and not v2v5_live_contract:
            raise ValueError(
                "generic baseline readiness requires OpenAI, the exact v2/v5 "
                "runtime, transport_max_retries=0, no_memory, no fault, and no "
                "public review sidecar"
            )
        if workflow_completion_probe and not v2v5_live_contract:
            raise ValueError(
                "workflow completion probe requires OpenAI, the exact v2/v5 "
                "runtime, transport_max_retries=0, no_memory, no fault, and no "
                "public review sidecar"
            )
        count_limits_disabled = bool(
            self.budget.max_model_calls is None or self.budget.max_tool_calls is None
        )
        generic_count_observability = bool(
            generic_baseline_readiness
            and self.experiment is not None
            and self.experiment.experiment_id
            in {
                "generic-baseline-readiness-v2v5-20260803-r3",
                GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID,
            }
        )
        historical_workflow_completion_probe = bool(
            workflow_completion_probe
            and self.experiment is not None
            and self.experiment.experiment_id
            == "pyfakefs-workflow-completion-probe-v2v5-20260803-r1"
            and self.task_id == "pyfakefs-makedirs-parent-traversal"
            and self.budget.max_total_tokens == 3_000_000
            and self.budget.wall_clock_timeout_seconds == 7_200
        )
        exact_workflow_completion_probe = bool(
            self.budget.max_model_calls is None
            and self.budget.max_tool_calls is None
            and self.model.model_id == "gpt-5.4-mini-2026-03-17"
            and self.model.max_output_tokens == 25_000
            and (
                historical_workflow_completion_probe
                or (
                    condition_neutral_budget_readiness_probe
                    and self.budget.max_total_tokens == 2_000_000
                    and self.budget.wall_clock_timeout_seconds == 1_800
                    and self.memory.max_context_tokens == 2_000
                )
            )
        )
        if workflow_completion_probe and not exact_workflow_completion_probe:
            raise ValueError(
                "workflow completion probe requires an exact registered task, "
                "dated mini model, disabled call limits, and its registered "
                "token and wall ceilings"
            )
        generic_observability_profiles = {
            "generic-baseline-readiness-v2v5-20260803-r3": {
                "task_ids": {
                    "babel-strict-grouped-decimal-trailing-zeroes",
                    "moto-query-scanned-count",
                    "pyfakefs-makedirs-parent-traversal",
                    "hf-hub-xet-endpoint-propagation",
                },
                "max_total_tokens": 2_400_000,
                "wall_clock_timeout_seconds": 1_800,
            },
            GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID: {
                "task_ids": {
                    "anyio-interrupt-runner-cleanup",
                    "pyfakefs-makedirs-parent-traversal",
                    "hf-hub-xet-endpoint-propagation",
                },
                "max_total_tokens": 3_000_000,
                "wall_clock_timeout_seconds": 3_600,
            },
        }
        generic_observability_profile = (
            generic_observability_profiles.get(self.experiment.experiment_id)
            if self.experiment is not None
            else None
        )
        generic_high_headroom_row_identity = bool(
            self.experiment is not None
            and self.experiment.experiment_id == GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID
            and self.experiment.dataset_role == DatasetRole.MEMORY_DEVELOPMENT
            and self.experiment.schedule_seed == 20260723
            and self.experiment.repetition == 1
            and self.experiment.schedule_order
            == {
                "anyio-interrupt-runner-cleanup": 1,
                "pyfakefs-makedirs-parent-traversal": 2,
                "hf-hub-xet-endpoint-propagation": 3,
            }.get(self.task_id)
            and self.memory.max_context_tokens == 2_000
        )
        ac_fixed_bundle_readiness = bool(
            self.experiment is not None
            and self.experiment.experiment_id in AC_FIXED_BUNDLE_EXPERIMENT_IDS
            and self.experiment.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_AC_READINESS
            and self.experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
            and self.experiment.schedule_seed == 20260723
            and self.experiment.repetition == 1
            and self.experiment.schedule_order
            == {
                ("moto-query-scanned-count", MemoryCondition.NO_MEMORY): 1,
                ("moto-query-scanned-count", MemoryCondition.STRUCTURED): 2,
                (
                    "babel-strict-grouped-decimal-trailing-zeroes",
                    MemoryCondition.STRUCTURED,
                ): 3,
                (
                    "babel-strict-grouped-decimal-trailing-zeroes",
                    MemoryCondition.NO_MEMORY,
                ): 4,
            }.get((self.task_id, self.memory.condition))
            and self.memory_policy_version == AC_FIXED_BUNDLE_POLICY_VERSION
            and self.model.provider == "openai"
            and self.model.model_id == "gpt-5.4-mini-2026-03-17"
            and self.model.reasoning_effort == "medium"
            and self.model.reasoning_mode == "standard"
            and self.model.service_tier == "default"
            and self.model.transport_max_retries == 0
            and self.model.max_output_tokens == 25_000
            and self.tool_schema_version == "v2"
            and self.context_policy_version == "phase-evidence-v5"
            and self.budget.max_model_calls is None
            and self.budget.max_tool_calls is None
            and self.budget.max_total_tokens == 3_000_000
            and self.budget.wall_clock_timeout_seconds == 3_600
            and self.memory.max_context_tokens == 2_000
            and (
                (
                    self.memory.condition == MemoryCondition.NO_MEMORY
                    and self.memory.index_version is None
                    and self.memory.index_hash is None
                )
                or (
                    self.memory.condition == MemoryCondition.STRUCTURED
                    and self.memory.index_version == AC_FIXED_BUNDLE_D110_INDEX_VERSION
                    and self.memory.index_hash == AC_FIXED_BUNDLE_D110_INDEX_CONTENT_HASH
                )
            )
            and self.fault.type == "none"
            and self.public_review_contract is None
        )
        if (
            self.experiment is not None
            and self.experiment.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_AC_READINESS
            and not ac_fixed_bundle_readiness
        ):
            raise ValueError(
                "A/C readiness manifest requires the exact four-row fixed-bundle runtime"
            )
        if generic_count_observability and not (
            generic_observability_profile is not None
            and self.budget.max_model_calls is None
            and self.budget.max_tool_calls is None
            and self.budget.max_total_tokens == generic_observability_profile["max_total_tokens"]
            and self.budget.wall_clock_timeout_seconds
            == generic_observability_profile["wall_clock_timeout_seconds"]
            and self.task_id in generic_observability_profile["task_ids"]
            and self.model.model_id == "gpt-5.4-mini-2026-03-17"
            and self.model.max_output_tokens == 25_000
            and (
                self.experiment.experiment_id != GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID
                or generic_high_headroom_row_identity
            )
        ):
            raise ValueError(
                "generic count-observability readiness requires its exact task "
                "identity, dated mini model, disabled call limits, and registered "
                "token and wall ceilings"
            )
        if count_limits_disabled and not (
            workflow_completion_probe
            or generic_count_observability
            or future_comparison_profile
            or prospective_no_memory_v2
            or ac_fixed_bundle_readiness
        ):
            raise ValueError(
                "disabled model/tool call limits are reserved for an exact "
                "registered observability profile"
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
    tool_schema_version: Literal["v1", "v2", "v3", "v4", "v5", "v6"] = "v1"
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


class EvidenceArtifactRef(FrozenStrictModel):
    """Path-free content identity for evaluator-v2 evidence."""

    schema_version: Literal["evidence-artifact-ref-v2"] = "evidence-artifact-ref-v2"
    artifact_id: str = Field(pattern=r"^art_[0-9a-f]{32}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: Literal[
        "application/json; charset=utf-8",
        "text/plain; charset=utf-8",
        "text/x-diff; charset=utf-8",
    ]
    role: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        if value != value.strip() or "\r" in value or "\n" in value or "/" not in value:
            raise ValueError("evidence media type must be one normalized MIME type")
        return value


def build_evidence_artifact_ref(artifact: Artifact, *, role: str) -> EvidenceArtifactRef:
    return EvidenceArtifactRef(
        artifact_id=artifact.artifact_id,
        content_hash=artifact.content_hash,
        size_bytes=artifact.size_bytes,
        media_type=artifact.media_type,
        role=role,
    )


class SafetyEvidenceRecord(FrozenStrictModel):
    schema_version: Literal["safety-evidence-record-v2"] = "safety-evidence-record-v2"
    requirement_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    control: SafetyControlKind
    evidence_producer: SafetyEvidenceProducer
    policy_profile: SafetyPolicyProfile
    state: VerdictState
    evidence_artifacts: tuple[EvidenceArtifactRef, ...] = Field(default_factory=tuple)
    reason_code: SafetyEvidenceReason | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_evidence_state(self) -> SafetyEvidenceRecord:
        if (self.evidence_producer, self.policy_profile) != _SAFETY_POLICY_BY_CONTROL[self.control]:
            raise ValueError("safety evidence control, producer, and policy profile mismatch")
        artifact_ids = tuple(item.artifact_id for item in self.evidence_artifacts)
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("safety evidence artifact IDs must be unique")
        artifact_order = tuple((item.role, item.artifact_id) for item in self.evidence_artifacts)
        if artifact_order != tuple(sorted(artifact_order)):
            raise ValueError("safety evidence artifacts must use canonical role and ID order")
        roles = tuple(item.role for item in self.evidence_artifacts)
        if len(roles) != len(set(roles)):
            raise ValueError("safety evidence roles must be unique")
        if self.state == VerdictState.PASS:
            if not self.evidence_artifacts or self.reason_code is not None:
                raise ValueError("PASS safety evidence requires artifacts and no reason code")
        elif self.state == VerdictState.FAIL:
            if (
                not self.evidence_artifacts
                or self.reason_code != SafetyEvidenceReason.POLICY_VIOLATION
            ):
                raise ValueError("FAIL safety evidence requires artifacts and policy_violation")
        elif self.state == VerdictState.ERROR:
            if self.evidence_artifacts:
                raise ValueError("ERROR safety evidence cannot claim completed evidence roles")
            if self.reason_code not in {
                SafetyEvidenceReason.CHECKER_ERROR,
                SafetyEvidenceReason.INTEGRITY_ERROR,
            }:
                raise ValueError("ERROR safety evidence requires a checker or integrity reason")
        else:
            if self.evidence_artifacts:
                raise ValueError("NOT_RUN safety evidence cannot claim completed evidence roles")
            if self.reason_code not in {
                SafetyEvidenceReason.REQUIRED_EVIDENCE_MISSING,
                SafetyEvidenceReason.NOT_EXECUTED,
            }:
                raise ValueError(
                    "NOT_RUN safety evidence requires a missing or not-executed reason"
                )
        return self


class SafetyEvidenceBundle(FrozenStrictModel):
    """Evaluator-private structural projection; CAS bytes are verified at ingestion."""

    schema_version: Literal["safety-evidence-bundle-v2"] = "safety-evidence-bundle-v2"
    run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    task_version: int = Field(ge=1)
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    safety_contract: EvaluatorSafetyContract
    evaluator_contract: EvaluatorContractBinding
    through_sequence: int = Field(ge=0)
    event_prefix_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    records: tuple[SafetyEvidenceRecord, ...] = Field(min_length=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_bundle(self) -> SafetyEvidenceBundle:
        bundle_identity = (
            self.task_id,
            self.task_version,
            self.public_spec_hash,
            self.private_spec_hash,
        )
        contract_identity = (
            self.safety_contract.task_id,
            self.safety_contract.task_version,
            self.safety_contract.public_spec_hash,
            self.safety_contract.private_spec_hash,
        )
        binding_identity = (
            self.evaluator_contract.task_id,
            self.evaluator_contract.task_version,
            self.evaluator_contract.public_spec_hash,
            self.evaluator_contract.private_spec_hash,
        )
        if bundle_identity != contract_identity or bundle_identity != binding_identity:
            raise ValueError("safety evidence bundle task identity mismatch")
        if (
            self.evaluator_contract.contract_id != self.safety_contract.contract_id
            or self.evaluator_contract.contract_hash != self.safety_contract.content_hash
        ):
            raise ValueError("safety evidence bundle contract binding mismatch")
        expected_requirement_hashes = tuple(
            safety_requirement_hash(requirement)
            for requirement in self.safety_contract.requirements
        )
        if (
            self.evaluator_contract.required_safety_requirement_hashes
            != expected_requirement_hashes
        ):
            raise ValueError("safety evidence bundle requirement projection mismatch")
        expected_records = tuple(
            (
                requirement_hash,
                requirement.control,
                requirement.evidence_producer,
                requirement.policy_profile,
            )
            for requirement_hash, requirement in zip(
                expected_requirement_hashes,
                self.safety_contract.requirements,
                strict=True,
            )
        )
        actual_records = tuple(
            (
                record.requirement_hash,
                record.control,
                record.evidence_producer,
                record.policy_profile,
            )
            for record in self.records
        )
        if actual_records != expected_records:
            raise ValueError("safety evidence records must exactly project the private contract")
        for record, requirement in zip(
            self.records, self.safety_contract.requirements, strict=True
        ):
            if record.state in {VerdictState.PASS, VerdictState.FAIL}:
                actual_roles = tuple(item.role for item in record.evidence_artifacts)
                if actual_roles != requirement.required_evidence_roles:
                    raise ValueError(
                        "completed safety evidence must cover the exact required roles"
                    )
        artifact_ids = [
            artifact.artifact_id
            for record in self.records
            for artifact in record.evidence_artifacts
        ]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("safety evidence artifact IDs cannot be reused across controls")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("safety evidence bundle content hash mismatch")
        return self


class EvaluatorV2EvaluationReceipt(FrozenStrictModel):
    """Public, direct-ID-free proof that one persisted v2 chain was revalidated.

    The receipt does not turn the raw ``RunResult`` into an official result.  A
    trace qualifier must still compare the source/suite qualification hashes
    with separately trusted successor authority before completion can count it.
    """

    schema_version: Literal["evaluator-v2-evaluation-receipt-v1"] = (
        "evaluator-v2-evaluation-receipt-v1"
    )
    run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    evaluator_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_file_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    result_file_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provenance_file_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    safety_bundle_file_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    safety_bundle_semantic_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    safety_bundle_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    submitted_patch_artifact_id: str = Field(pattern=r"^art_[0-9a-f]{32}$")
    submitted_patch_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_prefix_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    through_sequence: int = Field(ge=1)
    preterminal_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    preterminal_through_sequence: int = Field(ge=1)
    evidence_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_artifact_count: int = Field(ge=1)
    evaluator_duration_ms: int = Field(ge=0)
    runtime_authenticated: Literal[True] = True
    qualification_eligible: Literal[True] = True
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> EvaluatorV2EvaluationReceipt:
        if self.preterminal_through_sequence < self.through_sequence:
            raise ValueError("evaluator-v2 preterminal boundary cannot precede accepted submission")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("evaluator-v2 evaluation receipt content hash mismatch")
        return self


def safety_evidence_bundle_artifact_bytes(bundle: SafetyEvidenceBundle) -> bytes:
    """Render bytes exactly as ArtifactStore.put_json persists them."""

    bundle = SafetyEvidenceBundle.model_validate(bundle.model_dump(mode="json"))
    return json.dumps(
        bundle.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")


def build_safety_evidence_bundle_ref(
    bundle: SafetyEvidenceBundle,
    *,
    artifact_id: str,
) -> EvidenceArtifactRef:
    content = safety_evidence_bundle_artifact_bytes(bundle)
    return EvidenceArtifactRef(
        artifact_id=artifact_id,
        content_hash=sha256_bytes(content),
        size_bytes=len(content),
        media_type="application/json; charset=utf-8",
        role="safety_evidence_bundle",
    )


class VerifierResult(StrictModel):
    schema_version: Literal["verifier-result-v1", "verifier-result-v2"] = "verifier-result-v1"
    verifier_result_id: str
    run_id: str
    check_type: str
    check_id: str
    state: VerdictState
    duration_ms: int = Field(ge=0)
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    evaluator_contract_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    safety_evidence_bundle_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    safety_requirement_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    safety_control: SafetyControlKind | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    evidence_producer: SafetyEvidenceProducer | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    safety_policy_profile: SafetyPolicyProfile | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    reason_code: SafetyEvidenceReason | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    evidence_artifacts: tuple[EvidenceArtifactRef, ...] = Field(
        default_factory=tuple,
        exclude_if=lambda value: not value,
    )

    @model_validator(mode="after")
    def validate_versioned_evidence(self) -> VerifierResult:
        v2_fields_present = any(
            value is not None
            for value in (
                self.evaluator_contract_hash,
                self.safety_evidence_bundle_hash,
                self.safety_requirement_hash,
                self.safety_control,
                self.evidence_producer,
                self.safety_policy_profile,
                self.reason_code,
            )
        ) or bool(self.evidence_artifacts)
        if self.schema_version == "verifier-result-v1":
            if v2_fields_present:
                raise ValueError("versioned evaluator evidence requires verifier-result-v2")
            return self
        if self.check_type not in {"hidden", "regression", "policy", "safety"}:
            raise ValueError("verifier-result-v2 has an unknown check type")
        if (
            self.check_type in {"hidden", "regression"}
            and re.fullmatch(r"sha256:[0-9a-f]{64}", self.check_id) is None
        ):
            raise ValueError("v2 registered check results require opaque specification hashes")
        if re.fullmatch(r"vr_[0-9a-f]{32}", self.verifier_result_id) is None:
            raise ValueError("verifier-result-v2 has an invalid result ID")
        if self.evaluator_contract_hash is None:
            raise ValueError("verifier-result-v2 requires an evaluator contract hash")
        if self.details:
            raise ValueError("verifier-result-v2 details must use typed evidence artifacts")
        artifact_ids = [item.artifact_id for item in self.evidence_artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("verifier evidence artifact IDs must be unique")
        if self.evidence_artifact_ids != artifact_ids:
            raise ValueError("verifier artifact IDs disagree with typed evidence references")
        if self.state in {VerdictState.PASS, VerdictState.FAIL} and not self.evidence_artifacts:
            raise ValueError("PASS/FAIL verifier-result-v2 requires typed evidence")
        if (
            self.check_type == "safety"
            and self.state
            in {
                VerdictState.ERROR,
                VerdictState.NOT_RUN,
            }
            and self.evidence_artifacts
        ):
            raise ValueError("incomplete safety verifier results cannot claim completed evidence")
        safety_fields = (
            self.safety_evidence_bundle_hash,
            self.safety_requirement_hash,
            self.safety_control,
            self.evidence_producer,
            self.safety_policy_profile,
        )
        if self.check_type == "safety":
            if any(value is None for value in safety_fields):
                raise ValueError("safety verifier result requires complete typed bundle evidence")
            if self.check_id != self.safety_requirement_hash:
                raise ValueError("safety verifier check ID must be the opaque requirement hash")
            if (self.evidence_producer, self.safety_policy_profile) != (
                _SAFETY_POLICY_BY_CONTROL[self.safety_control]
            ):
                raise ValueError("safety verifier control, producer, and policy profile mismatch")
            if self.state == VerdictState.PASS and self.reason_code is not None:
                raise ValueError("PASS safety verifier result cannot have a reason code")
            if self.state == VerdictState.FAIL and (
                self.reason_code != SafetyEvidenceReason.POLICY_VIOLATION
            ):
                raise ValueError("FAIL safety verifier result requires policy_violation")
            if self.state == VerdictState.ERROR and self.reason_code not in {
                SafetyEvidenceReason.CHECKER_ERROR,
                SafetyEvidenceReason.INTEGRITY_ERROR,
            }:
                raise ValueError("ERROR safety verifier result requires a typed error reason")
            if self.state == VerdictState.NOT_RUN and self.reason_code not in {
                SafetyEvidenceReason.REQUIRED_EVIDENCE_MISSING,
                SafetyEvidenceReason.NOT_EXECUTED,
            }:
                raise ValueError("NOT_RUN safety verifier result requires a typed reason")
        elif any(value is not None for value in safety_fields) or self.reason_code is not None:
            raise ValueError("typed safety fields are only valid for safety verifier results")
        return self


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
                "cached_input_tokens + cache_write_input_tokens must not exceed input_tokens"
            )
        if self.reasoning_output_tokens > self.output_tokens:
            raise ValueError("reasoning_output_tokens must not exceed output_tokens")
        return self


def aggregate_v2_verdict_states(states: list[VerdictState]) -> VerdictState:
    """Fail closed without collapsing NOT_RUN into FAIL."""

    if not states:
        return VerdictState.NOT_RUN
    for state in _SAFETY_AGGREGATION_PRECEDENCE[:-1]:
        if state in states:
            return state
    return VerdictState.PASS


class RunResult(StrictModel):
    schema_version: Literal["run-result-v1", "run-result-v2"] = "run-result-v1"
    run_id: str
    agent_submission_status: str
    evaluation_status: str
    scope_compliant_success: bool
    official: bool = False
    verdicts: Verdicts
    usage: Usage = Field(default_factory=Usage)
    submitted_patch_artifact_id: str | None = None
    submitted_patch_artifact: EvidenceArtifactRef | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    verifier_results: list[VerifierResult] = Field(default_factory=list)
    outcome_kind: RunOutcomeKind | None = None
    terminal_error: dict[str, Any] | None = None
    evaluator_contract: EvaluatorContractBinding | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    safety_evidence_bundle: EvidenceArtifactRef | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    safety_evidence_bundle_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    safety_evidence: tuple[SafetyEvidenceRecord, ...] = Field(
        default_factory=tuple,
        exclude_if=lambda value: not value,
    )

    @model_validator(mode="after")
    def derive_and_validate_outcome_kind(self) -> RunResult:
        if self.schema_version == "run-result-v1":
            if (
                self.evaluator_contract is not None
                or self.submitted_patch_artifact is not None
                or self.safety_evidence_bundle is not None
                or self.safety_evidence_bundle_hash is not None
                or self.safety_evidence
            ):
                raise ValueError("versioned evaluator evidence requires run-result-v2")
            if self.outcome_kind is None:
                if self.scope_compliant_success:
                    self.outcome_kind = RunOutcomeKind.RESOLVED
                elif self.evaluation_status == "completed":
                    self.outcome_kind = RunOutcomeKind.TASK_FAILURE
                else:
                    self.outcome_kind = RunOutcomeKind.AGENT_FAILURE
            return self

        if self.evaluator_contract is None:
            raise ValueError("run-result-v2 requires an evaluator contract binding")
        if self.official:
            raise ValueError("run-result-v2 remains unofficial until qualification integration")
        if re.fullmatch(r"run_[a-zA-Z0-9_-]+", self.run_id) is None:
            raise ValueError("run-result-v2 has an invalid run ID")
        if (
            self.submitted_patch_artifact_id is not None
            and re.fullmatch(r"art_[0-9a-f]{32}", self.submitted_patch_artifact_id) is None
        ):
            raise ValueError("run-result-v2 has an invalid submitted patch artifact ID")
        if self.submitted_patch_artifact is not None and (
            self.submitted_patch_artifact_id != self.submitted_patch_artifact.artifact_id
            or self.submitted_patch_artifact.role != "submitted_patch"
            or self.submitted_patch_artifact.media_type != "text/x-diff; charset=utf-8"
        ):
            raise ValueError("run-result-v2 submitted patch descriptor mismatch")
        if (self.submitted_patch_artifact_id is None) != (self.submitted_patch_artifact is None):
            raise ValueError("run-result-v2 patch ID and typed descriptor must appear together")
        if self.terminal_error is not None:
            if set(self.terminal_error) != {"code", "phase"} or not all(
                isinstance(value, str) for value in self.terminal_error.values()
            ):
                raise ValueError("run-result-v2 terminal errors must use the sanitized typed shape")
            if self.terminal_error["code"] not in {
                "AGENT_SUBMISSION_FAILED",
                "EVALUATOR_NOT_REACHED",
                "EVALUATOR_INFRASTRUCTURE_ERROR",
                "REQUIRED_EVIDENCE_MISSING",
            } or self.terminal_error["phase"] not in {"agent", "evaluator", "infrastructure"}:
                raise ValueError("run-result-v2 terminal error code or phase is invalid")
        if self.agent_submission_status not in {"completed", "failed"}:
            raise ValueError("run-result-v2 has an unknown agent submission status")
        if self.evaluation_status not in {"completed", "not_run"}:
            raise ValueError("run-result-v2 has an unknown evaluation status")

        if self.evaluation_status == "not_run":
            if (
                self.safety_evidence_bundle is not None
                or self.safety_evidence_bundle_hash is not None
                or self.safety_evidence
                or self.verifier_results
            ):
                raise ValueError("an evaluation that was not run cannot invent evaluator evidence")
            if self.verdicts != Verdicts() or self.scope_compliant_success or self.official:
                raise ValueError(
                    "an evaluation that was not run must remain non-successful and unofficial"
                )
            if not self.terminal_error:
                raise ValueError("an evaluation that was not run requires a terminal error")
            if self.agent_submission_status == "completed":
                if self.submitted_patch_artifact is None:
                    raise ValueError(
                        "a completed submission requires its accepted patch descriptor"
                    )
                if (
                    self.terminal_error["code"],
                    self.terminal_error["phase"],
                ) not in {
                    ("EVALUATOR_NOT_REACHED", "evaluator"),
                    ("EVALUATOR_INFRASTRUCTURE_ERROR", "evaluator"),
                    ("EVALUATOR_INFRASTRUCTURE_ERROR", "infrastructure"),
                    ("REQUIRED_EVIDENCE_MISSING", "evaluator"),
                }:
                    raise ValueError("completed submission has an invalid evaluator terminal")
                expected_outcomes = {RunOutcomeKind.INFRASTRUCTURE_ERROR}
                default_outcome = RunOutcomeKind.INFRASTRUCTURE_ERROR
            else:
                if self.submitted_patch_artifact is not None:
                    raise ValueError("a failed submission cannot carry an accepted patch")
                if (
                    self.terminal_error["code"],
                    self.terminal_error["phase"],
                ) != ("AGENT_SUBMISSION_FAILED", "agent"):
                    raise ValueError("failed submission has an invalid agent terminal")
                expected_outcomes = {RunOutcomeKind.AGENT_FAILURE}
                default_outcome = RunOutcomeKind.AGENT_FAILURE
            if self.outcome_kind is None:
                self.outcome_kind = default_outcome
            elif self.outcome_kind not in expected_outcomes:
                raise ValueError("evaluation-not-run has an invalid terminal outcome")
            return self

        if self.agent_submission_status != "completed":
            raise ValueError("a completed evaluation requires a completed agent submission")
        if self.terminal_error is not None:
            raise ValueError("a completed evaluation cannot also carry a terminal error")
        if self.submitted_patch_artifact_id is None:
            raise ValueError("a completed evaluation requires a submitted patch artifact")
        if self.submitted_patch_artifact is None:
            raise ValueError("a completed evaluation requires a typed submitted patch descriptor")
        if (
            self.safety_evidence_bundle is None
            or self.safety_evidence_bundle_hash is None
            or not self.safety_evidence
        ):
            raise ValueError("completed run-result-v2 requires typed safety bundle evidence")
        if (
            self.safety_evidence_bundle.role != "safety_evidence_bundle"
            or self.safety_evidence_bundle.media_type != "application/json; charset=utf-8"
        ):
            raise ValueError(
                "run-result-v2 has an invalid safety bundle artifact role or media type"
            )
        if any(item.schema_version != "verifier-result-v2" for item in self.verifier_results):
            raise ValueError("run-result-v2 cannot mix verifier result versions")
        if any(item.run_id != self.run_id for item in self.verifier_results):
            raise ValueError("verifier result belongs to a different run")
        result_ids = [item.verifier_result_id for item in self.verifier_results]
        if len(result_ids) != len(set(result_ids)):
            raise ValueError("verifier result IDs must be unique")
        result_keys = [(item.check_type, item.check_id) for item in self.verifier_results]
        if len(result_keys) != len(set(result_keys)):
            raise ValueError("verifier result check identities must be unique")
        if any(
            item.evaluator_contract_hash != self.evaluator_contract.contract_hash
            for item in self.verifier_results
        ):
            raise ValueError("verifier result evaluator contract hash mismatch")

        def results_for(check_type: str) -> list[VerifierResult]:
            return [item for item in self.verifier_results if item.check_type == check_type]

        hidden_results = results_for("hidden")
        regression_results = results_for("regression")
        policy_results = results_for("policy")
        safety_results = results_for("safety")
        if _check_id_set_hash([item.check_id for item in hidden_results]) != (
            self.evaluator_contract.hidden_check_ids_hash
        ):
            raise ValueError("run-result-v2 hidden check set disagrees with the task binding")
        if _check_id_set_hash([item.check_id for item in regression_results]) != (
            self.evaluator_contract.regression_check_ids_hash
        ):
            raise ValueError("run-result-v2 regression check set disagrees with the task binding")
        if _check_id_set_hash([item.check_id for item in policy_results]) != (
            self.evaluator_contract.scope_check_ids_hash
        ):
            raise ValueError("run-result-v2 scope policy check set is incomplete")
        required_safety_hashes = self.evaluator_contract.required_safety_requirement_hashes
        actual_safety_hashes = tuple(item.check_id for item in safety_results)
        if actual_safety_hashes != required_safety_hashes:
            raise ValueError("run-result-v2 requires the ordered exact safety result set")
        record_hashes = tuple(item.requirement_hash for item in self.safety_evidence)
        if record_hashes != required_safety_hashes:
            raise ValueError("run-result-v2 requires the ordered exact safety evidence set")
        if any(
            item.safety_evidence_bundle_hash != self.safety_evidence_bundle_hash
            for item in safety_results
        ):
            raise ValueError("safety verifier result bundle hash mismatch")
        result_projection = tuple(
            (
                item.safety_requirement_hash,
                item.safety_control,
                item.evidence_producer,
                item.safety_policy_profile,
                item.state,
                item.evidence_artifacts,
                item.reason_code,
            )
            for item in safety_results
        )
        record_projection = tuple(
            (
                item.requirement_hash,
                item.control,
                item.evidence_producer,
                item.policy_profile,
                item.state,
                item.evidence_artifacts,
                item.reason_code,
            )
            for item in self.safety_evidence
        )
        if result_projection != record_projection:
            raise ValueError("safety verifier results disagree with the safety evidence records")

        expected_verdicts = Verdicts(
            hidden_tests=aggregate_v2_verdict_states([item.state for item in hidden_results]),
            regression_tests=aggregate_v2_verdict_states(
                [item.state for item in regression_results]
            ),
            scope_policy=aggregate_v2_verdict_states([item.state for item in policy_results]),
            safety_policy=aggregate_v2_verdict_states([item.state for item in safety_results]),
        )
        if self.verdicts != expected_verdicts:
            raise ValueError("run-result-v2 verdicts disagree with verifier results")
        expected_success = all(
            value == VerdictState.PASS for value in expected_verdicts.model_dump().values()
        )
        if self.scope_compliant_success is not expected_success:
            raise ValueError("run-result-v2 success disagrees with the four-verdict conjunction")
        if expected_success:
            expected_outcome = RunOutcomeKind.RESOLVED
        elif any(
            value in {VerdictState.ERROR, VerdictState.NOT_RUN}
            for value in expected_verdicts.model_dump().values()
        ):
            expected_outcome = RunOutcomeKind.INFRASTRUCTURE_ERROR
        else:
            expected_outcome = RunOutcomeKind.TASK_FAILURE
        if self.outcome_kind is None:
            self.outcome_kind = expected_outcome
        elif self.outcome_kind != expected_outcome:
            raise ValueError("run-result-v2 outcome disagrees with verifier states")
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
        expected_relation = "single" if len(self.member_run_ids) == 1 else "semantic-duplicate"
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
            raise ValueError("model self-review requires model_id and response_artifact_hash")
        if self.kind == "maintainer-assisted" and (
            self.model_id is not None or self.response_artifact_hash is not None
        ):
            raise ValueError("maintainer-assisted review must not claim model response provenance")
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


class D099ArtifactDescriptor(StrictModel):
    path: str
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return safe_relative_path(value, field_name="artifact.path")


class D099SourceSeal(D099ArtifactDescriptor):
    schema_version: Literal["condition-neutral-no-memory-baseline-d098-evidence-v1"]
    report_id: str = Field(pattern=r"^d098_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class D099CampaignBinding(StrictModel):
    experiment_id: Literal["dev-no-memory-condition-neutral-3000k-20260805-r1"]
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    suite_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dataset_manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class D099EvidenceBoundary(StrictModel):
    policy: Literal["agent-visible-public-evidence-v2"]
    allowed_sources: list[str] = Field(min_length=1)
    prohibited_semantic_sources: list[str] = Field(min_length=1)
    opaque_integrity_bindings: list[str] = Field(min_length=1)
    generic_outcome_only: Literal[True]
    private_task_body_interpreted: Literal[False]
    hidden_test_body_interpreted: Literal[False]
    reference_patch_body_interpreted: Literal[False]
    evaluator_payload_body_interpreted: Literal[False]
    provider_request_or_response_body_interpreted: Literal[False]

    @field_validator(
        "allowed_sources",
        "prohibited_semantic_sources",
        "opaque_integrity_bindings",
    )
    @classmethod
    def validate_source_lists(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(not item.strip() for item in value):
            raise ValueError("D-099 evidence lists must contain unique non-blank values")
        return value


class D099EvidenceRef(StrictModel):
    evidence_ref_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    role: Literal[
        "public_inspection",
        "mutation",
        "visible_check",
        "diff",
        "review",
        "submission",
        "generic_outcome",
    ]
    sequence: int = Field(ge=1)
    event_id: str = Field(pattern=r"^evt_[0-9a-f]+$")
    event_type: Literal[
        "ToolSucceeded",
        "PatchApplied",
        "ReviewRecorded",
        "SubmissionAccepted",
        "FailureTagged",
    ]
    event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    artifact_bytes: int | None = Field(default=None, ge=0)
    check_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_role_shape(self) -> D099EvidenceRef:
        expected_types = {
            "public_inspection": "ToolSucceeded",
            "mutation": "PatchApplied",
            "visible_check": "ToolSucceeded",
            "diff": "ToolSucceeded",
            "review": "ReviewRecorded",
            "submission": "SubmissionAccepted",
            "generic_outcome": "FailureTagged",
        }
        if self.event_type != expected_types[self.role]:
            raise ValueError("D-099 evidence role and event type do not match")
        artifact_present = self.artifact_hash is not None and self.artifact_bytes is not None
        if (self.role == "generic_outcome") == artifact_present:
            raise ValueError("only generic outcome evidence may omit an artifact binding")
        if (self.role == "visible_check") != (self.check_id is not None):
            raise ValueError("only visible-check evidence may carry check_id")
        return self


class D099ReviewSource(StrictModel):
    run_id: str = Field(min_length=1)
    failure_record_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    repetition: int = Field(ge=1)
    public_spec: D099ArtifactDescriptor
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    failure_record_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    qualification_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    submitted_patch: D099ArtifactDescriptor
    semantic_group_id: str = Field(min_length=1)
    assessment: str = Field(min_length=1)
    causal_confidence: float = Field(ge=0, le=1)
    evidence_refs: list[D099EvidenceRef] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence_refs(self) -> D099ReviewSource:
        ref_ids = [ref.evidence_ref_id for ref in self.evidence_refs]
        sequences = [ref.sequence for ref in self.evidence_refs]
        if len(ref_ids) != len(set(ref_ids)):
            raise ValueError("D-099 source evidence reference IDs must be unique")
        if sequences != sorted(set(sequences)):
            raise ValueError("D-099 source evidence sequences must be sorted and unique")
        required = {
            "public_inspection",
            "mutation",
            "visible_check",
            "diff",
            "review",
            "submission",
            "generic_outcome",
        }
        if {ref.role for ref in self.evidence_refs} != required:
            raise ValueError("D-099 source must contain every public evidence role")
        return self


class D099GroupMember(StrictModel):
    run_id: str = Field(min_length=1)
    failure_record_id: str = Field(min_length=1)


class D099ProposedRule(StrictModel):
    failure_class: str = Field(min_length=1)
    phase: Phase
    description: str = Field(min_length=1)
    preconditions: list[str] = Field(min_length=1)
    diagnostic_evidence: list[str] = Field(min_length=1)
    recommended_actions: list[str] = Field(min_length=1)
    do_not_apply_when: list[str] = Field(min_length=1)
    applicable_languages: list[Literal["python"]] = Field(default_factory=lambda: ["python"])
    confidence: float = Field(ge=0, le=1)
    admission_decision: Literal["not_made"]


class D099SemanticGroup(StrictModel):
    semantic_group_id: str = Field(min_length=1)
    representative_run_id: str = Field(min_length=1)
    members: list[D099GroupMember] = Field(min_length=1)
    relation: Literal["single", "semantic-cluster", "exact-duplicate"]
    merge_rationale: str = Field(min_length=1)
    dedup_confidence: float = Field(ge=0, le=1)
    disposition: Literal["candidate", "hold"]
    evidence_ref_ids: list[str] = Field(min_length=1)
    semantic_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    proposed_rule: D099ProposedRule | None = None
    unresolved_reason: str | None = Field(default=None, min_length=1)
    next_review_actions: list[str] = Field(default_factory=list)
    admission_decision: Literal["not_made"]

    @model_validator(mode="after")
    def validate_group_shape(self) -> D099SemanticGroup:
        member_pairs = [(member.run_id, member.failure_record_id) for member in self.members]
        if len(member_pairs) != len(set(member_pairs)):
            raise ValueError("D-099 semantic group members must be unique")
        if self.representative_run_id not in {member.run_id for member in self.members}:
            raise ValueError("D-099 representative run must be a group member")
        if len(self.evidence_ref_ids) != len(set(self.evidence_ref_ids)):
            raise ValueError("D-099 group evidence reference IDs must be unique")
        if self.disposition == "candidate":
            if self.proposed_rule is None or self.unresolved_reason is not None:
                raise ValueError("candidate groups require only a proposed rule")
            if self.next_review_actions:
                raise ValueError("candidate groups must not carry hold review actions")
        elif (
            self.proposed_rule is not None
            or self.unresolved_reason is None
            or not self.next_review_actions
        ):
            raise ValueError("hold groups require only an unresolved reason and review actions")
        expected_relation = "single" if len(self.members) == 1 else self.relation
        if len(self.members) == 1 and expected_relation != self.relation:
            raise ValueError("single-member D-099 groups must use relation=single")
        if len(self.members) > 1 and self.relation == "single":
            raise ValueError("multi-member D-099 groups cannot use relation=single")
        return self


class D099ExcludedRun(StrictModel):
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    repetition: int = Field(ge=1)
    outcome_kind: Literal["resolved", "agent_failure"]
    reason: Literal["resolved", "canonical_pre_provider_budget"]


class D099PopulationPartition(StrictModel):
    source_row_count: Literal[12]
    review_source_count: Literal[9]
    semantic_group_count: Literal[5]
    candidate_group_count: int = Field(ge=0)
    candidate_source_count: int = Field(ge=0)
    hold_group_count: int = Field(ge=0)
    hold_source_count: int = Field(ge=0)
    excluded_resolved: list[D099ExcludedRun]
    excluded_budget: list[D099ExcludedRun]
    candidate_order_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    group_partition_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class D099BuildValidation(StrictModel):
    source_seal_verified: Literal[True]
    dataset_manifest_and_public_specs_verified: Literal[True]
    selected_public_event_refs_verified: int = Field(ge=1)
    portable_submitted_patches_verified: Literal[9]
    proposal_text_leak_scan_passed: Literal[True]
    submitted_patch_leak_scan_passed: Literal[True]
    original_runtime_state_unchanged: Literal[True]
    raw_source_audit_performed: Literal[True]


class D099Authority(StrictModel):
    proposal_only: Literal[True]
    human_admission_status: Literal["pending"]
    group_approval_completed: Literal[False]
    admitted_memory_rule_count: Literal[0]
    d099_review_history_written: Literal[False]
    memory_admission_unlocked: Literal[False]
    memory_index_build_authorized: Literal[False]
    d099_memory_index_built: Literal[False]
    d099_memory_index_frozen: Literal[False]
    historical_memory_artifacts_modified: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]
    automatic_agent_self_review_observed: Literal[False]
    exact_hidden_failure_cause_established: Literal[False]
    agent_architecture_defect_established: Literal[False]
    harness_defect_established: Literal[False]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    added_model_cost_usd: Literal[0]


class D099ReviewBody(StrictModel):
    milestone: Literal["D-099"]
    evidence_kind: Literal["formal-non-admitting-public-review-dedup"]
    recorded_at: str = Field(min_length=1)
    producer: MemoryReviewProducer
    source_seal: D099SourceSeal
    campaign: D099CampaignBinding
    evidence_boundary: D099EvidenceBoundary
    sources: list[D099ReviewSource] = Field(min_length=1)
    groups: list[D099SemanticGroup] = Field(min_length=1)
    population_partition: D099PopulationPartition
    build_validation: D099BuildValidation
    authority: D099Authority
    next_gate: str = Field(min_length=1)


class D099ReviewProposal(StrictModel):
    schema_version: Literal["memory-public-review-proposal-d099-v1"]
    proposal_id: str = Field(pattern=r"^d099_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D099ReviewBody


class D100ProposalBinding(StrictModel):
    schema_version: Literal["memory-public-review-proposal-d099-v1"]
    proposal_id: str = Field(pattern=r"^d099_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class D100GroupDecisionRecord(StrictModel):
    schema_version: Literal["memory-group-review-decision-d100-v1"]
    decision_id: str = Field(pattern=r"^d100dec_[0-9a-f]{64}$")
    sequence: int = Field(ge=1)
    event_kind: Literal["DecisionRecorded", "DecisionCorrected"]
    action_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    action_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    proposal: D100ProposalBinding
    semantic_group_id: str = Field(min_length=1)
    semantic_group_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    group_disposition: Literal["candidate", "hold"]
    decision: Literal["approve", "reject", "continue_hold"]
    reviewer_kind: Literal["human", "maintainer_assisted", "synthetic"]
    reviewer: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=2_000)
    proposed_rule_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    previous_decision_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    supersedes_decision_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    recorded_at: str = Field(min_length=1)
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_decision_shape(self) -> D100GroupDecisionRecord:
        if self.decision == "approve":
            if self.group_disposition != "candidate" or self.proposed_rule_hash is None:
                raise ValueError("only candidate groups with a bound rule may be approved")
        elif self.proposed_rule_hash is not None:
            raise ValueError("non-approval decisions must not bind a proposed rule")
        if self.event_kind == "DecisionRecorded" and self.supersedes_decision_hash is not None:
            raise ValueError("an initial group decision cannot supersede another decision")
        if self.event_kind == "DecisionCorrected" and self.supersedes_decision_hash is None:
            raise ValueError("a corrected group decision must bind the prior decision")
        return self


class D100DecisionJournalDescriptor(StrictModel):
    schema_version: Literal["memory-group-review-journal-d100-v1"]
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    record_count: int = Field(ge=1)
    correction_count: int = Field(ge=0)
    decided_group_count: int = Field(ge=1)
    head_decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class D100MemoryEntryTemplate(StrictModel):
    target_schema: Literal["memory-entry-v1"]
    proposed_memory_id: str = Field(pattern=r"^memgrp_[0-9a-f]{32}$")
    failure_pattern: FailurePattern
    preconditions: list[str] = Field(min_length=1)
    diagnostic_evidence: list[str] = Field(min_length=1)
    recommended_actions: list[str] = Field(min_length=1)
    do_not_apply_when: list[str] = Field(min_length=1)
    applicable_languages: list[Literal["python"]] = Field(min_length=1)
    source_run_ids: list[str] = Field(min_length=1)
    validation_count: Literal[0]
    confidence: float = Field(ge=0, le=1)


class D100PreviewProvenance(StrictModel):
    semantic_group_id: str = Field(min_length=1)
    semantic_group_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_failure_ids: list[str] = Field(min_length=1)
    evidence_ref_ids: list[str] = Field(min_length=1)
    dedup_confidence: float = Field(ge=0, le=1)


class D100ProjectedEntry(StrictModel):
    template: D100MemoryEntryTemplate
    provenance: D100PreviewProvenance
    template_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class D100PreviewAuthority(StrictModel):
    projection_only: Literal[True]
    complete_group_decisions_validated: Literal[True]
    external_head_anchor_validated: bool
    admission_seal_created: Literal[False]
    admitted_memory_rule_count: Literal[0]
    memory_admission_unlocked: Literal[False]
    memory_index_build_authorized: Literal[False]
    memory_index_built: Literal[False]
    memory_index_frozen: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    added_model_cost_usd: Literal[0]


class D100EntryPreviewBody(StrictModel):
    milestone: Literal["D-100"]
    evidence_kind: Literal["group-aware-memory-entry-preview"]
    proposal: D100ProposalBinding
    journal: D100DecisionJournalDescriptor
    final_decision_hashes: dict[str, str] = Field(min_length=5, max_length=5)
    approved_group_ids: list[str]
    rejected_group_ids: list[str]
    continued_hold_group_ids: list[str]
    entries: list[D100ProjectedEntry]
    leak_scan_passed: Literal[True]
    authority: D100PreviewAuthority


class D100EntryPreview(StrictModel):
    schema_version: Literal["memory-entry-preview-d100-v1"]
    preview_id: str = Field(pattern=r"^d100preview_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D100EntryPreviewBody


class D100SourceGroupBinding(StrictModel):
    semantic_group_id: str = Field(min_length=1)
    semantic_group_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    disposition: Literal["candidate", "hold"]
    proposed_rule_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @model_validator(mode="after")
    def validate_rule_binding(self) -> D100SourceGroupBinding:
        if self.disposition == "candidate" and self.proposed_rule_hash is None:
            raise ValueError("candidate source groups require an exact proposed rule hash")
        if self.disposition == "hold" and self.proposed_rule_hash is not None:
            raise ValueError("hold source groups must not bind a proposed rule")
        return self


class D100SourceMechanism(StrictModel):
    decision_schema: Literal["memory-group-review-decision-d100-v1"]
    journal_schema: Literal["memory-group-review-journal-d100-v1"]
    preview_schema: Literal["memory-entry-preview-d100-v1"]
    target_entry_schema: Literal["memory-entry-v1"]
    semantic_group_count: Literal[5]
    tail_cas_required: Literal[True]
    action_idempotency_required: Literal[True]
    correction_binds_effective_group_head: Literal[True]
    append_flush_and_fsync: Literal[True]
    canonical_rows_required: Literal[True]
    snapshot_consistency_required: Literal[True]
    malformed_or_hash_inconsistent_chain_fails_closed: Literal[True]
    external_head_anchor_supported: Literal[True]
    external_head_anchor_required_for_suffix_rewrite_detection: Literal[True]
    reviewer_provenance_self_attested: Literal[True]
    one_approved_group_per_template: Literal[True]
    preview_has_no_index_version_or_embedding: Literal[True]
    legacy_failure_builder_connected: Literal[False]


class D100SourceAuthority(StrictModel):
    mechanism_source_gate_only: Literal[True]
    production_human_decision_records: Literal[0]
    group_review_completed: Literal[False]
    admission_seal_created: Literal[False]
    admitted_memory_rule_count: Literal[0]
    preview_entry_count: Literal[0]
    memory_admission_unlocked: Literal[False]
    memory_index_build_authorized: Literal[False]
    memory_index_built: Literal[False]
    memory_index_frozen: Literal[False]
    historical_memory_artifacts_modified: Literal[False]
    core_campaign_unlocked: Literal[False]
    analysis_ready: Literal[False]
    provider_calls_made: Literal[0]
    evaluator_calls_made: Literal[0]
    added_model_cost_usd: Literal[0]


class D100SourceGateBody(StrictModel):
    milestone: Literal["D-100"]
    evidence_kind: Literal["group-review-projector-offline-source-gate"]
    recorded_at: str = Field(min_length=1)
    proposal: D100ProposalBinding
    group_bindings: list[D100SourceGroupBinding] = Field(min_length=5, max_length=5)
    implementation_files: list[D099ArtifactDescriptor] = Field(min_length=1)
    commands: list[str] = Field(min_length=4)
    mechanism: D100SourceMechanism
    authority: D100SourceAuthority
    next_gate: Literal["explicit-human-group-decisions-and-portable-admission-seal"]


class D100SourceGate(StrictModel):
    schema_version: Literal["memory-group-review-projector-source-gate-d100-v1"]
    gate_id: str = Field(pattern=r"^d100_[0-9a-f]{64}$")
    semantic_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_body: D100SourceGateBody


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
