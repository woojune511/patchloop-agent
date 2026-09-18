"""Small active contracts for the mutable ``dev-head`` lane.

Historical experiment, candidate, qualification, activation, and evaluator-v2
contracts intentionally live only in Git history and archived artifacts.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.util import safe_relative_path, sha256_json


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class RepositorySpec(StrictModel):
    url: str
    base_commit: str = Field(min_length=1)
    language: Literal["python"] = "python"

    @model_validator(mode="after")
    def snapshot_is_content_addressed(self) -> RepositorySpec:
        if self.url.startswith("snapshot://") and re.fullmatch(
            r"sha256:[0-9a-f]{64}", self.base_commit
        ) is None:
            raise ValueError("snapshot repositories require a sha256 content revision")
        if self.url.startswith("https://github.com/") and re.fullmatch(
            r"[0-9a-f]{40}", self.base_commit
        ) is None:
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
    """Parser compatibility for audited task-public-v2 packages.

    Active ``dev-head`` probes use a runtime-owned opt-in profile, not these
    legacy task-package profile settings.
    """

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
        "smoke",
        "dev-train",
        "dev-validation",
        "same-repo-heldout",
        "cross-repo-heldout",
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
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def matching_identity(self) -> TaskPackage:
        if (self.public.task_id, self.public.task_version) != (
            self.private.task_id,
            self.private.task_version,
        ):
            raise ValueError("public/private task identity mismatch")
        public_hash, private_hash = task_package_spec_hashes(self.public, self.private)
        if self.public_spec_hash != public_hash or self.private_spec_hash != private_hash:
            raise ValueError("task package specification hash mismatch")
        return self


def task_package_spec_hashes(public: PublicTask, private: PrivateTask) -> tuple[str, str]:
    """Preserve the audited v1/v2 task identity algorithm."""

    private_identity = private.model_dump(mode="json")
    if private.schema_version == "task-private-v1":
        private_identity.pop("hidden_artifacts", None)
    return (
        sha256_json(public.model_dump(mode="json")),
        sha256_json(private_identity),
    )


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

DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V2 = {
    **DOCKER_REGISTERED_CHECK_REQUEST_POLICY_V1,
    "schema_version": "docker-registered-check-request-policy-v2",
    "owned_container_cleanup": True,
    "cleanup_reserve_seconds": 5,
}


class ModelConfig(StrictModel):
    provider: Literal["mock", "openai"]
    model_id: str = Field(min_length=1)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] = "medium"
    reasoning_mode: Literal["standard", "pro"] = "standard"
    reasoning_continuation: Literal["none", "encrypted-v1"] = "none"
    service_tier: Literal["default", "flex", "priority"] = "default"
    transport_max_retries: Literal[0] | None = None
    max_output_tokens: int = Field(default=4096, ge=1)
    input_price_per_million_usd: float | None = Field(default=None, ge=0)
    cached_input_price_per_million_usd: float | None = Field(default=None, ge=0)
    output_price_per_million_usd: float | None = Field(default=None, ge=0)


class ProbeDependencyIdentity(StrictModel):
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    python: Literal["3.12"] = "3.12"
    platform: Literal["linux/amd64"] = "linux/amd64"
    source_roots: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("source_roots")
    @classmethod
    def public_import_roots(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("probe source roots must be unique")
        for value in values:
            safe_relative_path(value, field_name="probe source root")
            if any(part.casefold().startswith(".env")
                   or part.casefold() in {".git", ".patchloop-hidden"}
                   for part in value.split("/")):
                raise ValueError("probe source root is not public")
        return values


class RunManifest(StrictModel):
    schema_version: Literal["dev-manifest-v1"] = "dev-manifest-v1"
    official: Literal[False] = False
    runtime_id: Literal["dev-head"] = "dev-head"
    planning_policy: Literal[
        "none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1",
    ] = "none"
    probe_policy: Literal["none", "cases-v1"] = "none"
    run_id: str = Field(pattern=r"^run_[a-zA-Z0-9_-]+$")
    task_id: str
    task_version: int = Field(ge=1)
    base_commit: str
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    tool_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sandbox_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    submitted_patch_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    visible_check_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    submitted_changed_files: list[str] = Field(min_length=1)
    harness_git_commit: str = "uncommitted"
    model: ModelConfig
    max_model_calls: int = Field(default=40, ge=1)
    max_tool_actions: int = Field(default=100, ge=1)
    max_accepted_mutations: int = Field(default=4, ge=1)
    wall_time_seconds: int = Field(default=1800, ge=1)
    protocol_recovery_limit: int = Field(default=1, ge=0)
    memory_enabled: Literal[False] = False
    sandbox_backend: Literal["local", "docker"] = "local"
    evaluator_image_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    probe_image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    probe_profile_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    probe_dependencies: ProbeDependencyIdentity | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    probe_execution_count: int = Field(default=0, ge=0, le=100)
    probe_evidence: list[Artifact] = Field(default_factory=list, max_length=100)
    created_at: datetime

    @field_validator("submitted_changed_files")
    @classmethod
    def validate_submitted_paths(cls, values: list[str]) -> list[str]:
        normalized = [safe_relative_path(value, field_name="submitted path") for value in values]
        if normalized != sorted(set(normalized)):
            raise ValueError("submitted changed files must be unique and sorted")
        return normalized

    @model_validator(mode="after")
    def sandbox_identity_is_complete(self) -> RunManifest:
        if self.submitted_patch_content_hash != self.visible_check_diff_hash:
            raise ValueError("submitted patch must equal the visibly checked diff")
        if self.sandbox_backend == "docker" and self.evaluator_image_digest is None:
            raise ValueError("Docker manifests require an evaluator image digest")
        if self.sandbox_backend == "local" and self.evaluator_image_digest is not None:
            raise ValueError("local manifests cannot claim an evaluator image digest")
        if (self.probe_image_digest is None) != (self.probe_profile_hash is None):
            raise ValueError("probe manifests require both image and profile identities")
        if self.probe_dependencies is not None and self.probe_profile_hash is None:
            raise ValueError("probe dependencies require enabled probe identities")
        return self


class VerdictState(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    NOT_RUN = "not_run"


class SafetyControl(StrEnum):
    RUNTIME_CONTRACT = "runtime_contract"
    CONSTRAINED_TOOL_SURFACE = "constrained_tool_surface"
    MANAGED_WORKSPACE = "managed_workspace"
    REQUESTED_SANDBOX_POLICY = "requested_sandbox_policy"


class SafetyEvidence(StrictModel):
    schema_version: Literal["dev-safety-evidence-v1"] = "dev-safety-evidence-v1"
    control: SafetyControl
    state: VerdictState
    evidence_artifact_ids: list[str] = Field(default_factory=list)
    evidence_hashes: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence_hashes")
    @classmethod
    def validate_evidence_hashes(cls, values: list[str]) -> list[str]:
        if any(re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None for value in values):
            raise ValueError("safety evidence hashes must be SHA-256 identities")
        return values


class Artifact(StrictModel):
    artifact_id: str = Field(pattern=r"^art_[0-9a-f]{32}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_type: str
    size_bytes: int = Field(ge=0)
    path: str
    created_at: datetime


class VerifierResult(StrictModel):
    schema_version: Literal["dev-verifier-result-v1"] = "dev-verifier-result-v1"
    verifier_result_id: str = Field(pattern=r"^vr_[0-9a-f]{32}$")
    run_id: str
    check_type: Literal["hidden", "regression", "policy"]
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
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_output_tokens: int = Field(default=0, ge=0)
    model_cost_nanos: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    input_token_count_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    wall_clock_ms: int = Field(default=0, ge=0)


class RunResult(StrictModel):
    schema_version: Literal["dev-evaluator-result-v1"] = "dev-evaluator-result-v1"
    run_id: str
    agent_submission_status: str
    evaluation_status: str
    scope_compliant_success: bool
    official: Literal[False] = False
    verdicts: Verdicts
    usage: Usage = Field(default_factory=Usage)
    submitted_patch_artifact_id: str | None = None
    verifier_results: list[VerifierResult] = Field(default_factory=list)
    safety_evidence: list[SafetyEvidence] = Field(default_factory=list)
