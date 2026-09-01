"""Offline public-candidate registry projection for a future fresh panel.

The registry stage is intentionally earlier than task admission.  It consumes a
normalized *public-only* source snapshot, applies the preregistered source-window,
identity, repository, difficulty and license filters, and emits deterministic
same/cross admission queues plus a complete decision transcript.  Reference
passes, bad-patch rejection, private evaluator construction and task spec hashes
remain a later admission gate.

This module performs no network, Docker, provider, evaluator or agent call.  A
projection is explicitly unqualified until a separate source qualifier verifies
the raw immutable source bytes and completeness assertions.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Self, get_args, get_origin

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_acquisition_preregistration import (
    DATASET_MANIFEST_BYTES,
    DATASET_MANIFEST_PATH,
    DATASET_MANIFEST_SHA256,
    SAME_REPOSITORY_TARGETS,
    FreshAcquisitionPreregistration,
    preregistration_bytes,
)
from patchloop.util import ensure_within, load_unique_yaml, sha256_bytes, sha256_json

SNAPSHOT_SCHEMA_VERSION = "lean-fresh-public-source-snapshot-v1"
REGISTRY_SCHEMA_VERSION = "lean-fresh-public-candidate-registry-v1"
QUALIFIED_REGISTRY_SCHEMA_VERSION = "lean-fresh-qualified-public-candidate-registry-v1"
PREREGISTRATION_PATH = "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json"
PREREGISTRATION_BYTES = 7_255
PREREGISTRATION_FILE_SHA256 = (
    "sha256:086b9fc56ab5eca3ae23cd367243d9b71c3805d7f3edd3613afdb73a34bbf359"
)
PREREGISTRATION_CONTENT_HASH = (
    "sha256:adec1153d8eab532d118fe24d0f60247385d154dbcc840db8dc24167c0c1cb94"
)

WINDOW_START = "2026-03-17T23:59:59Z"
WINDOW_END = "2026-08-16T23:59:59Z"
RANKING_PREFIX = "lean-fresh-acquisition-20260817-v1"
RANKING_PREIMAGE_TEMPLATE = (
    "lean-fresh-acquisition-20260817-v1|stratum={stratum}|repo={lowercase_repo}|"
    "instance={canonical_public_instance_id}"
)
PENDING_IDENTITY_DIMENSIONS = (
    "task-id-and-version",
    "solution-lineage-id",
    "public-or-private-spec-hash",
)
CHECKED_IDENTITY_DIMENSIONS = (
    "benchmark-instance-id",
    "issue-or-pull-request-url",
    "upstream-base-or-resolution-commit",
)
SCREENING_PRECEDENCE = (
    "outside-frozen-source-window",
    "current-manifest-source-identity-overlap",
    "below-medium-difficulty",
    "license-incompatible",
    "existing-nontarget-repository",
    "ranked-admission-queue",
)


class FreshCandidateRegistryError(ContractError):
    """A public source snapshot or fresh registry projection is invalid."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @model_validator(mode="before")
    @classmethod
    def reject_literal_scalar_type_drift(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name, field in cls.model_fields.items():
            annotation = field.annotation
            if get_origin(annotation) is not Literal:
                continue
            expected_values = get_args(annotation)
            if len(expected_values) != 1 or name not in value:
                continue
            expected = expected_values[0]
            if isinstance(expected, (bool, int, float, str)) and type(value[name]) is not type(
                expected
            ):
                raise ValueError(f"{name} has a non-exact scalar type")
        return value


class FileBinding(FrozenModel):
    path: str
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    role: Literal[
        "fresh-acquisition-preregistration",
        "frozen-current-dataset-manifest",
        "normalized-public-source-snapshot",
        "raw-source-format-adapter-qualification",
        "raw-source-capture-receipt",
        "public-normalization-transcript",
        "raw-source-completeness-qualification",
    ]

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _relative_artifact_path(value)


class PublicCandidateRow(FrozenModel):
    source_ordinal: int = Field(ge=1)
    canonical_public_instance_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+$")
    upstream_repository: str = Field(pattern=r"^[a-z0-9_.-]+/[a-z0-9_.-]+$")
    issue_or_pull_request_url: str = Field(
        pattern=r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/[0-9]+$"
    )
    upstream_base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    resolution_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issue_created_at: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z$")
    resolution_merged_at: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z$")
    license_spdx: str = Field(min_length=1)
    license_compatibility: Literal["pass", "fail"]
    public_difficulty_tier: Literal["easy", "medium", "hard"]
    environment_image: str = Field(pattern=r"^[A-Za-z0-9._/-]+@sha256:[0-9a-f]{64}$")
    public_row_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("source_ordinal", mode="before")
    @classmethod
    def require_exact_ordinal(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("source_ordinal must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_canonical_public_row(self) -> Self:
        if self.upstream_repository != self.upstream_repository.lower():
            raise ValueError("upstream_repository must be lowercase canonical text")
        created = _parse_utc(self.issue_created_at, label="issue_created_at")
        merged = _parse_utc(self.resolution_merged_at, label="resolution_merged_at")
        if created > merged:
            raise ValueError("issue creation must not follow resolution merge")
        expected = sha256_json(self.model_dump(mode="json", exclude={"public_row_hash"}))
        if self.public_row_hash != expected:
            raise ValueError("public candidate row hash differs")
        return self


class FreshPublicSourceSnapshot(FrozenModel):
    schema_version: Literal[SNAPSHOT_SCHEMA_VERSION]
    snapshot_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    candidate_source_family: Literal["SWE-rebench-leaderboard"]
    source_url: str = Field(pattern=r"^https://")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_published_at: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z$")
    source_window_start_exclusive: Literal[WINDOW_START]
    source_window_end_inclusive: Literal[WINDOW_END]
    immutable_revision_asserted: Literal[True]
    earliest_qualifying_revision_asserted: Literal[True]
    complete_frozen_window_asserted: Literal[True]
    raw_source_file_bytes: int = Field(ge=1)
    raw_source_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalization_rule: Literal[
        "public-identity-provenance-difficulty-license-and-image-fields-only-v1"
    ]
    query_universe: Literal["every-row-in-bound-immutable-source-snapshot"]
    solution_or_test_patch_fields_included: Literal[False]
    oracle_fields_included: Literal[False]
    private_fields_included: Literal[False]
    external_completeness_assertions_qualified: Literal[False]
    raw_source_row_count: int = Field(ge=1)
    declared_source_row_count: int = Field(ge=1)
    rows: tuple[PublicCandidateRow, ...]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator(
        "raw_source_file_bytes",
        "raw_source_row_count",
        "declared_source_row_count",
        mode="before",
    )
    @classmethod
    def require_exact_integers(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("source snapshot counts must be JSON integers")
        return value

    @field_validator("rows", mode="before")
    @classmethod
    def freeze_rows(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        published = _parse_utc(self.source_published_at, label="source_published_at")
        if published <= _parse_utc(WINDOW_END, label="source window end"):
            raise ValueError("source snapshot must be published after the frozen window")
        if self.declared_source_row_count != len(self.rows):
            raise ValueError("source snapshot declared row count differs")
        if self.raw_source_row_count != self.declared_source_row_count:
            raise ValueError("normalized source snapshot does not account for every raw row")
        ordinals = [row.source_ordinal for row in self.rows]
        if ordinals != list(range(1, len(self.rows) + 1)):
            raise ValueError("source snapshot ordinals must be contiguous and ordered")
        instance_ids = [row.canonical_public_instance_id for row in self.rows]
        urls = [row.issue_or_pull_request_url.lower() for row in self.rows]
        if len(instance_ids) != len(set(instance_ids)) or len(urls) != len(set(urls)):
            raise ValueError("source snapshot contains duplicate public identity")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("public source snapshot content hash differs")
        return self


class QueryTranscriptRow(FrozenModel):
    source_ordinal: int = Field(ge=1)
    public_row_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_public_instance_id: str
    upstream_repository: str
    decision: Literal["ranked-admission-queue", "rejected"]
    stratum: Literal["same", "cross"] | None
    ranking_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    rejection_code: (
        Literal[
            "outside-frozen-source-window",
            "current-manifest-source-identity-overlap",
            "below-medium-difficulty",
            "license-incompatible",
            "existing-nontarget-repository",
        ]
        | None
    )

    @model_validator(mode="after")
    def validate_decision_envelope(self) -> Self:
        queued = self.decision == "ranked-admission-queue"
        if queued != (
            self.stratum is not None
            and self.ranking_hash is not None
            and self.rejection_code is None
        ):
            raise ValueError("query transcript queued envelope differs")
        if not queued and not (
            self.stratum is None and self.ranking_hash is None and self.rejection_code is not None
        ):
            raise ValueError("query transcript rejection envelope differs")
        return self


class RankedCandidate(FrozenModel):
    canonical_public_instance_id: str
    upstream_repository: str
    stratum: Literal["same", "cross"]
    ranking_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_row_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class RegistryAuthority(FrozenModel):
    preregistration_files_read: Literal[1]
    current_manifest_files_read: Literal[1]
    normalized_public_snapshot_files_read: Literal[1]
    raw_remote_source_files_read: Literal[0]
    task_package_files_read: Literal[0]
    private_task_files_read: Literal[0]
    oracle_or_reference_patch_fields_read: Literal[0]
    r16_row_outcomes_or_traces_read: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    offline_registry_projection_created: Literal[True]
    source_snapshot_externally_qualified: Literal[False]
    candidate_registry_qualified: Literal[False]
    task_admission_authorized: Literal[False]
    fresh_task_panel_materialized: Literal[False]
    full_experiment_preregistered: Literal[False]
    candidate_created: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class AdmissionQueuePolicy(FrozenModel):
    same_repository_rule: Literal[
        "for-each-frozen-target-scan-ascending-rank-and-accept-the-first-fully-admitted-task"
    ]
    cross_repository_rule: Literal[
        "scan-the-global-ascending-rank-queue-and-accept-fully-admitted-tasks-only-when-the-repository-is-not-yet-accepted"
    ]
    cross_repository_target_count: Literal[6]
    replacement_rule: Literal["continue-the-same-frozen-queue-after-a-typed-admission-rejection"]
    stop_rule: Literal[
        "stop-without-relaxation-if-any-same-target-or-six-distinct-cross-repositories-cannot-be-fully-admitted"
    ]
    full_admission_requires: tuple[
        Literal[
            "medium-or-hard-difficulty-audit",
            "three-official-reference-passes",
            "eight-rejected-bad-patches",
            "base-visible-pass-and-hidden-fail",
            "visible-hidden-scope-safety-reference-pass",
            "environment-image-and-public-private-spec-hashes",
            "remaining-identity-dimensions-disjoint",
            "license-compatible",
        ],
        ...,
    ]

    @field_validator("full_admission_requires", mode="before")
    @classmethod
    def freeze_admission_requirements(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def validate_full_admission_requirements(self) -> Self:
        if len(self.full_admission_requires) != 8 or len(set(self.full_admission_requires)) != 8:
            raise ValueError("full task admission requirements differ")
        return self


class FreshCandidateRegistry(FrozenModel):
    schema_version: Literal[REGISTRY_SCHEMA_VERSION]
    registry_id: str = Field(pattern=r"^lean-fresh-candidate-registry-[a-z0-9-]+-v1$")
    status: Literal[
        "OFFLINE_PUBLIC_REGISTRY_PROJECTION_ADMISSION_PENDING",
        "OFFLINE_PUBLIC_REGISTRY_PROJECTION_INSUFFICIENT_POOL",
    ]
    preregistration_binding: FileBinding
    current_manifest_binding: FileBinding
    source_snapshot_binding: FileBinding
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_window_start_exclusive: Literal[WINDOW_START]
    source_window_end_inclusive: Literal[WINDOW_END]
    screening_precedence: tuple[str, ...]
    checked_identity_dimensions: tuple[str, ...]
    pending_admission_identity_dimensions: tuple[str, ...]
    query_transcript_scope: Literal[
        "public-source-screening-only-task-admission-rejections-not-yet-observed"
    ]
    admission_queue_policy: AdmissionQueuePolicy
    query_transcript: tuple[QueryTranscriptRow, ...]
    ranked_candidates: tuple[RankedCandidate, ...]
    same_repository_queues: dict[str, tuple[str, ...]]
    cross_repository_queue: tuple[str, ...]
    source_row_count: int = Field(ge=1)
    queued_candidate_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)
    distinct_cross_repository_count: int = Field(ge=0)
    public_pool_sufficient_for_admission: bool
    task_admission_state: Literal[
        "pending-task-package-private-evaluator-and-identity-audit",
        "stopped-insufficient-public-pool-without-relaxation",
    ]
    authority: RegistryAuthority
    next_gate: Literal[
        "externally-qualify-the-immutable-source-and-complete-public-transcript-before-any-task-package-admission"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator(
        "source_row_count",
        "queued_candidate_count",
        "rejected_row_count",
        "distinct_cross_repository_count",
        mode="before",
    )
    @classmethod
    def require_exact_counts(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("registry counts must be JSON integers")
        return value

    @field_validator(
        "screening_precedence",
        "checked_identity_dimensions",
        "pending_admission_identity_dimensions",
        "query_transcript",
        "ranked_candidates",
        "cross_repository_queue",
        mode="before",
    )
    @classmethod
    def freeze_tuple_fields(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("same_repository_queues", mode="before")
    @classmethod
    def freeze_same_repository_queues(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            key: tuple(items) if isinstance(items, list) else items for key, items in value.items()
        }

    @model_validator(mode="after")
    def validate_registry_envelope(self) -> Self:
        if self.screening_precedence != SCREENING_PRECEDENCE:
            raise ValueError("registry screening precedence differs")
        if self.checked_identity_dimensions != CHECKED_IDENTITY_DIMENSIONS:
            raise ValueError("registry checked identity dimensions differ")
        if self.pending_admission_identity_dimensions != PENDING_IDENTITY_DIMENSIONS:
            raise ValueError("registry pending identity dimensions differ")
        if self.admission_queue_policy != _admission_queue_policy():
            raise ValueError("registry admission queue policy differs")
        if set(self.same_repository_queues) != set(SAME_REPOSITORY_TARGETS):
            raise ValueError("registry same-repository queue keys differ")
        if self.source_row_count != len(self.query_transcript):
            raise ValueError("registry transcript is incomplete")
        if self.queued_candidate_count != len(self.ranked_candidates):
            raise ValueError("registry queued candidate count differs")
        if self.rejected_row_count != sum(
            row.decision == "rejected" for row in self.query_transcript
        ):
            raise ValueError("registry rejection count differs")
        if self.source_row_count != self.queued_candidate_count + self.rejected_row_count:
            raise ValueError("registry row accounting differs")
        expected_status = (
            "OFFLINE_PUBLIC_REGISTRY_PROJECTION_ADMISSION_PENDING"
            if self.public_pool_sufficient_for_admission
            else "OFFLINE_PUBLIC_REGISTRY_PROJECTION_INSUFFICIENT_POOL"
        )
        expected_admission = (
            "pending-task-package-private-evaluator-and-identity-audit"
            if self.public_pool_sufficient_for_admission
            else "stopped-insufficient-public-pool-without-relaxation"
        )
        if self.status != expected_status or self.task_admission_state != expected_admission:
            raise ValueError("registry pool disposition differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("fresh candidate registry content hash differs")
        return self


class QualifiedRegistryAuthority(FrozenModel):
    raw_source_completeness_qualification_files_read: Literal[1]
    selector_raw_source_files_read: Literal[0]
    task_package_files_read: Literal[0]
    private_task_files_read: Literal[0]
    oracle_or_reference_patch_fields_read: Literal[0]
    r16_row_outcomes_or_traces_read: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    source_snapshot_externally_qualified: Literal[True]
    candidate_registry_qualified: Literal[True]
    task_admission_authorized: Literal[False]
    fresh_task_panel_materialized: Literal[False]
    full_experiment_preregistered: Literal[False]
    candidate_created: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class QualifiedFreshCandidateRegistry(FrozenModel):
    schema_version: Literal[QUALIFIED_REGISTRY_SCHEMA_VERSION]
    registry_id: str = Field(pattern=r"^lean-fresh-qualified-candidate-registry-[a-z0-9-]+-v1$")
    status: Literal[
        "QUALIFIED_PUBLIC_REGISTRY_TASK_ADMISSION_PENDING",
        "QUALIFIED_PUBLIC_REGISTRY_INSUFFICIENT_POOL",
    ]
    source_completeness_qualification_binding: FileBinding
    projection: FreshCandidateRegistry
    authority: QualifiedRegistryAuthority
    next_gate: Literal[
        "audit-the-qualified-public-transcript-before-any-task-package-private-evaluator-or-runtime-activation"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualified_registry(self) -> Self:
        if (
            self.source_completeness_qualification_binding.role
            != "raw-source-completeness-qualification"
        ):
            raise ValueError("qualified registry qualification role differs")
        expected_status = (
            "QUALIFIED_PUBLIC_REGISTRY_TASK_ADMISSION_PENDING"
            if self.projection.public_pool_sufficient_for_admission
            else "QUALIFIED_PUBLIC_REGISTRY_INSUFFICIENT_POOL"
        )
        if self.status != expected_status:
            raise ValueError("qualified registry status differs")
        if not (
            self.projection.authority.source_snapshot_externally_qualified is False
            and self.projection.authority.candidate_registry_qualified is False
            and self.authority.source_snapshot_externally_qualified is True
            and self.authority.candidate_registry_qualified is True
            and self.authority.task_admission_authorized is False
        ):
            raise ValueError("qualified registry authority differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("qualified registry content hash differs")
        return self


def _parse_utc(value: str, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is not RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include UTC authority")
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{label} must use UTC")
    return parsed


def _relative_artifact_path(value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute() or "\\" in value:
        raise ValueError("artifact paths must be repository-relative POSIX paths")
    normalized = candidate.as_posix()
    if normalized in {"", "."} or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("artifact path escapes the repository")
    if normalized != value:
        raise ValueError("artifact path is not canonical")
    return value


def _resolved_artifact(root: Path, path: str, *, forbid_runtime_state: bool = True) -> Path:
    try:
        relative = _relative_artifact_path(path)
    except ValueError as exc:
        raise FreshCandidateRegistryError("artifact path is not repository-relative") from exc
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        is_junction = getattr(cursor, "is_junction", lambda: False)
        if cursor.exists() and (cursor.is_symlink() or is_junction()):
            raise FreshCandidateRegistryError(f"artifact path contains a link: {relative}")
    selected = ensure_within(root, relative)
    if forbid_runtime_state and relative.startswith(("tasks/", ".patchloop/")):
        raise FreshCandidateRegistryError("artifact path is inside task or runtime state")
    return selected


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshCandidateRegistryError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshCandidateRegistryError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise FreshCandidateRegistryError(f"{label} must be an object")
    return value


def public_row_hash(body: dict[str, Any]) -> str:
    if "public_row_hash" in body:
        raise FreshCandidateRegistryError("public row hash input must exclude public_row_hash")
    return sha256_json(body)


def source_snapshot_bytes(snapshot: FreshPublicSourceSnapshot) -> bytes:
    return (
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def registry_bytes(registry: FreshCandidateRegistry) -> bytes:
    return (
        json.dumps(registry.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def qualified_registry_bytes(registry: QualifiedFreshCandidateRegistry) -> bytes:
    return (
        json.dumps(registry.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def load_public_source_snapshot(
    repository: str | Path, path: str
) -> tuple[FreshPublicSourceSnapshot, bytes]:
    root = Path(repository).resolve()
    selected = _resolved_artifact(root, path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshCandidateRegistryError("public source snapshot is unavailable") from exc
    _json_object(raw, label="public source snapshot")
    try:
        value = FreshPublicSourceSnapshot.model_validate_json(raw)
    except ValueError as exc:
        raise FreshCandidateRegistryError("public source snapshot contract is invalid") from exc
    if source_snapshot_bytes(value) != raw:
        raise FreshCandidateRegistryError("public source snapshot bytes are not canonical")
    return value, raw


def _read_preregistration(root: Path) -> FreshAcquisitionPreregistration:
    selected = _resolved_artifact(root, PREREGISTRATION_PATH)
    raw = selected.read_bytes()
    if len(raw) != PREREGISTRATION_BYTES or sha256_bytes(raw) != PREREGISTRATION_FILE_SHA256:
        raise FreshCandidateRegistryError("fresh acquisition preregistration differs")
    _json_object(raw, label="fresh acquisition preregistration")
    try:
        value = FreshAcquisitionPreregistration.model_validate_json(raw)
    except ValueError as exc:
        raise FreshCandidateRegistryError("fresh acquisition preregistration is invalid") from exc
    if preregistration_bytes(value) != raw or value.content_hash != PREREGISTRATION_CONTENT_HASH:
        raise FreshCandidateRegistryError("fresh acquisition preregistration identity differs")
    if not (
        value.acquisition_design.ranking_preimage == RANKING_PREIMAGE_TEMPLATE
        and value.acquisition_design.minimum_difficulty_tier == "medium"
        and value.acquisition_design.insufficient_pool_rule
        == "stop-without-relaxation-and-require-a-successor-preregistration-before-new-screening"
        and value.authority.candidate_registry_materialized is False
        and value.authority.execution_authorized is False
    ):
        raise FreshCandidateRegistryError("fresh acquisition screening authority differs")
    return value


def _read_current_manifest(root: Path) -> tuple[dict[str, Any], bytes]:
    selected = _resolved_artifact(root, DATASET_MANIFEST_PATH)
    raw = selected.read_bytes()
    if len(raw) != DATASET_MANIFEST_BYTES or sha256_bytes(raw) != DATASET_MANIFEST_SHA256:
        raise FreshCandidateRegistryError("current dataset manifest differs")
    try:
        parsed = load_unique_yaml(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        raise FreshCandidateRegistryError("current dataset manifest is invalid") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("tasks"), list):
        raise FreshCandidateRegistryError("current dataset manifest task registry is invalid")
    return parsed, raw


def _manifest_exclusions(manifest: dict[str, Any]) -> dict[str, set[str]]:
    repositories: set[str] = set()
    instance_ids: set[str] = set()
    urls: set[str] = set()
    commits: set[str] = set()
    for task in manifest["tasks"]:
        if not isinstance(task, dict):
            raise FreshCandidateRegistryError("current manifest task is invalid")
        source = task.get("source")
        if not isinstance(source, dict):
            continue
        repository = source.get("upstream_repository")
        if isinstance(repository, str) and repository.strip():
            repositories.add(repository.lower())
        instance_id = source.get("benchmark_instance_id")
        if isinstance(instance_id, str) and instance_id.strip():
            instance_ids.add(instance_id.lower())
        for key in ("issue_url", "pull_request_url"):
            url = source.get(key)
            if isinstance(url, str) and url.strip():
                urls.add(url.lower())
        for key in ("upstream_base_commit", "resolution_commit"):
            commit = source.get(key)
            if isinstance(commit, str) and commit.strip():
                commits.add(commit.lower())
    return {
        "repositories": repositories,
        "instance_ids": instance_ids,
        "urls": urls,
        "commits": commits,
    }


def _binding(path: str, raw: bytes, *, role: str, content_hash: str | None = None) -> FileBinding:
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
        role=role,
    )


def _rank(*, stratum: str, repository: str, instance_id: str) -> str:
    preimage = (
        f"{RANKING_PREFIX}|stratum={stratum}|repo={repository.lower()}|instance={instance_id}"
    )
    return sha256_bytes(preimage.encode("utf-8"))


def _outside_window(row: PublicCandidateRow) -> bool:
    start = _parse_utc(WINDOW_START, label="source window start")
    end = _parse_utc(WINDOW_END, label="source window end")
    created = _parse_utc(row.issue_created_at, label="issue_created_at")
    merged = _parse_utc(row.resolution_merged_at, label="resolution_merged_at")
    return not (start < created <= merged <= end)


def _current_identity_overlap(row: PublicCandidateRow, exclusions: dict[str, set[str]]) -> bool:
    return bool(
        row.canonical_public_instance_id.lower() in exclusions["instance_ids"]
        or row.issue_or_pull_request_url.lower() in exclusions["urls"]
        or row.upstream_base_commit.lower() in exclusions["commits"]
        or row.resolution_commit.lower() in exclusions["commits"]
    )


def _screen_row(
    row: PublicCandidateRow,
    exclusions: dict[str, set[str]],
) -> QueryTranscriptRow:
    rejection: str | None = None
    stratum: str | None = None
    if _outside_window(row):
        rejection = "outside-frozen-source-window"
    elif _current_identity_overlap(row, exclusions):
        rejection = "current-manifest-source-identity-overlap"
    elif row.public_difficulty_tier == "easy":
        rejection = "below-medium-difficulty"
    elif row.license_compatibility == "fail":
        rejection = "license-incompatible"
    elif row.upstream_repository in SAME_REPOSITORY_TARGETS:
        stratum = "same"
    elif row.upstream_repository in exclusions["repositories"]:
        rejection = "existing-nontarget-repository"
    else:
        stratum = "cross"

    if rejection is not None:
        return QueryTranscriptRow(
            source_ordinal=row.source_ordinal,
            public_row_hash=row.public_row_hash,
            canonical_public_instance_id=row.canonical_public_instance_id,
            upstream_repository=row.upstream_repository,
            decision="rejected",
            stratum=None,
            ranking_hash=None,
            rejection_code=rejection,
        )
    assert stratum is not None
    return QueryTranscriptRow(
        source_ordinal=row.source_ordinal,
        public_row_hash=row.public_row_hash,
        canonical_public_instance_id=row.canonical_public_instance_id,
        upstream_repository=row.upstream_repository,
        decision="ranked-admission-queue",
        stratum=stratum,
        ranking_hash=_rank(
            stratum=stratum,
            repository=row.upstream_repository,
            instance_id=row.canonical_public_instance_id,
        ),
        rejection_code=None,
    )


def _authority() -> RegistryAuthority:
    return RegistryAuthority(
        preregistration_files_read=1,
        current_manifest_files_read=1,
        normalized_public_snapshot_files_read=1,
        raw_remote_source_files_read=0,
        task_package_files_read=0,
        private_task_files_read=0,
        oracle_or_reference_patch_fields_read=0,
        r16_row_outcomes_or_traces_read=0,
        network_calls=0,
        docker_calls=0,
        provider_calls=0,
        evaluator_calls=0,
        agent_runs=0,
        added_model_cost_usd=0,
        offline_registry_projection_created=True,
        source_snapshot_externally_qualified=False,
        candidate_registry_qualified=False,
        task_admission_authorized=False,
        fresh_task_panel_materialized=False,
        full_experiment_preregistered=False,
        candidate_created=False,
        approval_granted=False,
        execution_authorized=False,
        official_analysis_authorized=False,
        memory_effect_claim_authorized=False,
    )


def _admission_queue_policy() -> AdmissionQueuePolicy:
    return AdmissionQueuePolicy(
        same_repository_rule=(
            "for-each-frozen-target-scan-ascending-rank-and-accept-the-first-fully-admitted-task"
        ),
        cross_repository_rule=(
            "scan-the-global-ascending-rank-queue-and-accept-fully-admitted-tasks-only-when-"
            "the-repository-is-not-yet-accepted"
        ),
        cross_repository_target_count=6,
        replacement_rule="continue-the-same-frozen-queue-after-a-typed-admission-rejection",
        stop_rule=(
            "stop-without-relaxation-if-any-same-target-or-six-distinct-cross-repositories-"
            "cannot-be-fully-admitted"
        ),
        full_admission_requires=(
            "medium-or-hard-difficulty-audit",
            "three-official-reference-passes",
            "eight-rejected-bad-patches",
            "base-visible-pass-and-hidden-fail",
            "visible-hidden-scope-safety-reference-pass",
            "environment-image-and-public-private-spec-hashes",
            "remaining-identity-dimensions-disjoint",
            "license-compatible",
        ),
    )


def build_fresh_candidate_registry(
    repository: str | Path, source_snapshot_path: str
) -> FreshCandidateRegistry:
    root = Path(repository).resolve()
    preregistration = _read_preregistration(root)
    manifest, manifest_raw = _read_current_manifest(root)
    snapshot, snapshot_raw = load_public_source_snapshot(root, source_snapshot_path)
    if not (
        snapshot.source_window_start_exclusive
        == preregistration.acquisition_design.source_window_start_exclusive
        and snapshot.source_window_end_inclusive
        == preregistration.acquisition_design.source_window_end_inclusive
    ):
        raise FreshCandidateRegistryError("public source snapshot window differs")

    exclusions = _manifest_exclusions(manifest)
    transcript = tuple(_screen_row(row, exclusions) for row in snapshot.rows)
    queued = [row for row in transcript if row.decision == "ranked-admission-queue"]
    ranked_candidates = tuple(
        RankedCandidate(
            canonical_public_instance_id=row.canonical_public_instance_id,
            upstream_repository=row.upstream_repository,
            stratum=row.stratum,
            ranking_hash=row.ranking_hash,
            public_row_hash=row.public_row_hash,
        )
        for row in sorted(
            queued,
            key=lambda item: (
                item.stratum or "",
                item.ranking_hash or "",
                item.canonical_public_instance_id,
            ),
        )
    )
    by_instance = {row.canonical_public_instance_id: row for row in ranked_candidates}
    same_queues = {
        repository: tuple(
            row.canonical_public_instance_id
            for row in sorted(
                (
                    candidate
                    for candidate in ranked_candidates
                    if candidate.stratum == "same" and candidate.upstream_repository == repository
                ),
                key=lambda candidate: (
                    candidate.ranking_hash,
                    candidate.canonical_public_instance_id,
                ),
            )
        )
        for repository in SAME_REPOSITORY_TARGETS
    }
    cross_queue = tuple(
        row.canonical_public_instance_id
        for row in sorted(
            (candidate for candidate in ranked_candidates if candidate.stratum == "cross"),
            key=lambda candidate: (
                candidate.ranking_hash,
                candidate.canonical_public_instance_id,
            ),
        )
    )
    distinct_cross_repositories = {
        by_instance[instance_id].upstream_repository for instance_id in cross_queue
    }
    sufficient = bool(
        all(same_queues[repository] for repository in SAME_REPOSITORY_TARGETS)
        and len(distinct_cross_repositories) >= 6
    )
    status = (
        "OFFLINE_PUBLIC_REGISTRY_PROJECTION_ADMISSION_PENDING"
        if sufficient
        else "OFFLINE_PUBLIC_REGISTRY_PROJECTION_INSUFFICIENT_POOL"
    )
    task_admission_state = (
        "pending-task-package-private-evaluator-and-identity-audit"
        if sufficient
        else "stopped-insufficient-public-pool-without-relaxation"
    )
    body: dict[str, Any] = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "registry_id": f"lean-fresh-candidate-registry-{snapshot.snapshot_id}-v1",
        "status": status,
        "preregistration_binding": FileBinding(
            path=PREREGISTRATION_PATH,
            file_bytes=PREREGISTRATION_BYTES,
            file_sha256=PREREGISTRATION_FILE_SHA256,
            content_hash=PREREGISTRATION_CONTENT_HASH,
            role="fresh-acquisition-preregistration",
        ),
        "current_manifest_binding": _binding(
            DATASET_MANIFEST_PATH,
            manifest_raw,
            role="frozen-current-dataset-manifest",
        ),
        "source_snapshot_binding": _binding(
            source_snapshot_path,
            snapshot_raw,
            role="normalized-public-source-snapshot",
            content_hash=snapshot.content_hash,
        ),
        "source_revision": snapshot.source_revision,
        "source_window_start_exclusive": WINDOW_START,
        "source_window_end_inclusive": WINDOW_END,
        "screening_precedence": SCREENING_PRECEDENCE,
        "checked_identity_dimensions": CHECKED_IDENTITY_DIMENSIONS,
        "pending_admission_identity_dimensions": PENDING_IDENTITY_DIMENSIONS,
        "query_transcript_scope": (
            "public-source-screening-only-task-admission-rejections-not-yet-observed"
        ),
        "admission_queue_policy": _admission_queue_policy(),
        "query_transcript": transcript,
        "ranked_candidates": ranked_candidates,
        "same_repository_queues": same_queues,
        "cross_repository_queue": cross_queue,
        "source_row_count": len(snapshot.rows),
        "queued_candidate_count": len(ranked_candidates),
        "rejected_row_count": len(snapshot.rows) - len(ranked_candidates),
        "distinct_cross_repository_count": len(distinct_cross_repositories),
        "public_pool_sufficient_for_admission": sufficient,
        "task_admission_state": task_admission_state,
        "authority": _authority(),
        "next_gate": (
            "externally-qualify-the-immutable-source-and-complete-public-transcript-before-any-"
            "task-package-admission"
        ),
    }
    hashed_body = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    for key in (
        "query_transcript",
        "ranked_candidates",
    ):
        hashed_body[key] = [item.model_dump(mode="json") for item in body[key]]
    return FreshCandidateRegistry(**body, content_hash=sha256_json(hashed_body))


def load_fresh_candidate_registry(repository: str | Path, path: str) -> FreshCandidateRegistry:
    root = Path(repository).resolve()
    selected = _resolved_artifact(root, path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshCandidateRegistryError("fresh candidate registry is unavailable") from exc
    _json_object(raw, label="fresh candidate registry")
    try:
        value = FreshCandidateRegistry.model_validate_json(raw)
    except ValueError as exc:
        raise FreshCandidateRegistryError("fresh candidate registry contract is invalid") from exc
    if registry_bytes(value) != raw:
        raise FreshCandidateRegistryError("fresh candidate registry bytes are not canonical")
    expected = build_fresh_candidate_registry(root, value.source_snapshot_binding.path)
    if value != expected:
        raise FreshCandidateRegistryError("fresh candidate registry projection differs")
    return value


def materialize_fresh_candidate_registry(
    repository: str | Path,
    *,
    source_snapshot_path: str,
    output_path: str,
) -> FreshCandidateRegistry:
    root = Path(repository).resolve()
    selected = _resolved_artifact(root, output_path)
    source = _resolved_artifact(root, source_snapshot_path)
    if not output_path.startswith(".tmp/"):
        raise FreshCandidateRegistryError(
            "unqualified registry projection may only be materialized under .tmp"
        )
    if selected == source:
        raise FreshCandidateRegistryError("registry output must differ from source snapshot")
    if selected.exists():
        value = load_fresh_candidate_registry(root, output_path)
        if value.source_snapshot_binding.path != source_snapshot_path:
            raise FreshCandidateRegistryError("existing registry belongs to another snapshot")
        return value
    value = build_fresh_candidate_registry(root, source_snapshot_path)
    raw = registry_bytes(value)
    selected.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(selected, flags, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return load_fresh_candidate_registry(root, output_path)


def _qualified_authority() -> QualifiedRegistryAuthority:
    return QualifiedRegistryAuthority(
        raw_source_completeness_qualification_files_read=1,
        selector_raw_source_files_read=0,
        task_package_files_read=0,
        private_task_files_read=0,
        oracle_or_reference_patch_fields_read=0,
        r16_row_outcomes_or_traces_read=0,
        network_calls=0,
        docker_calls=0,
        provider_calls=0,
        evaluator_calls=0,
        agent_runs=0,
        added_model_cost_usd=0,
        source_snapshot_externally_qualified=True,
        candidate_registry_qualified=True,
        task_admission_authorized=False,
        fresh_task_panel_materialized=False,
        full_experiment_preregistered=False,
        candidate_created=False,
        approval_granted=False,
        execution_authorized=False,
        official_analysis_authorized=False,
        memory_effect_claim_authorized=False,
    )


def build_qualified_fresh_candidate_registry(
    repository: str | Path,
    source_qualification_path: str,
) -> QualifiedFreshCandidateRegistry:
    from patchloop.evals.fresh_source_completeness import (
        load_fresh_source_completeness_qualification,
    )

    root = Path(repository).resolve()
    qualification, qualification_raw = load_fresh_source_completeness_qualification(
        root, source_qualification_path
    )
    projection = build_fresh_candidate_registry(root, qualification.source_snapshot_binding.path)
    if projection.source_snapshot_binding != qualification.source_snapshot_binding:
        raise FreshCandidateRegistryError("qualified registry snapshot binding differs")
    status = (
        "QUALIFIED_PUBLIC_REGISTRY_TASK_ADMISSION_PENDING"
        if projection.public_pool_sufficient_for_admission
        else "QUALIFIED_PUBLIC_REGISTRY_INSUFFICIENT_POOL"
    )
    body: dict[str, Any] = {
        "schema_version": QUALIFIED_REGISTRY_SCHEMA_VERSION,
        "registry_id": projection.registry_id.replace(
            "lean-fresh-candidate-registry-",
            "lean-fresh-qualified-candidate-registry-",
            1,
        ),
        "status": status,
        "source_completeness_qualification_binding": _binding(
            source_qualification_path,
            qualification_raw,
            role="raw-source-completeness-qualification",
            content_hash=qualification.content_hash,
        ),
        "projection": projection,
        "authority": _qualified_authority(),
        "next_gate": (
            "audit-the-qualified-public-transcript-before-any-task-package-private-evaluator-"
            "or-runtime-activation"
        ),
    }
    hashed = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return QualifiedFreshCandidateRegistry(**body, content_hash=sha256_json(hashed))


def load_qualified_fresh_candidate_registry(
    repository: str | Path,
    path: str,
) -> QualifiedFreshCandidateRegistry:
    root = Path(repository).resolve()
    selected = _resolved_artifact(root, path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshCandidateRegistryError(
            "qualified fresh candidate registry is unavailable"
        ) from exc
    _json_object(raw, label="qualified fresh candidate registry")
    try:
        value = QualifiedFreshCandidateRegistry.model_validate_json(raw)
    except ValueError as exc:
        raise FreshCandidateRegistryError(
            "qualified fresh candidate registry contract is invalid"
        ) from exc
    if qualified_registry_bytes(value) != raw:
        raise FreshCandidateRegistryError(
            "qualified fresh candidate registry bytes are not canonical"
        )
    expected = build_qualified_fresh_candidate_registry(
        root, value.source_completeness_qualification_binding.path
    )
    if value != expected:
        raise FreshCandidateRegistryError("qualified fresh candidate registry differs")
    return value


def materialize_qualified_fresh_candidate_registry(
    repository: str | Path,
    *,
    source_qualification_path: str,
    output_path: str,
) -> QualifiedFreshCandidateRegistry:
    root = Path(repository).resolve()
    selected = _resolved_artifact(root, output_path)
    qualification = _resolved_artifact(root, source_qualification_path)
    if selected == qualification:
        raise FreshCandidateRegistryError("registry output must differ from qualification")
    if selected.exists():
        value = load_qualified_fresh_candidate_registry(root, output_path)
        if value.source_completeness_qualification_binding.path != source_qualification_path:
            raise FreshCandidateRegistryError("existing registry belongs to another qualification")
        return value
    value = build_qualified_fresh_candidate_registry(root, source_qualification_path)
    raw = qualified_registry_bytes(value)
    selected.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(selected, flags, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return load_qualified_fresh_candidate_registry(root, output_path)
