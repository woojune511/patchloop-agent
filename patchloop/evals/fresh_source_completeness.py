"""Consumer contract for future raw-source completeness qualification.

The actual source-specific adapter cannot be frozen until a qualifying immutable
snapshot exists.  This module freezes what that adapter must prove and validates
the resulting append-only artifact before the public selector may consume it.
It never fetches or parses remote/task/private/oracle material itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Self, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_candidate_registry import (
    WINDOW_END,
    WINDOW_START,
    FileBinding,
    FreshCandidateRegistryError,
    FreshPublicSourceSnapshot,
    load_public_source_snapshot,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-fresh-raw-source-completeness-qualification-v1"
STATUS = "RAW_SOURCE_COMPLETE_FOR_PUBLIC_REGISTRY_PROJECTION_ONLY"
QUALIFICATION_METHOD = "isolated-source-specific-adapter-with-complete-row-transcript-v1"


class FreshSourceCompletenessError(ContractError):
    """A raw-source completeness qualification is invalid or inconsistent."""


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


class RawSourceIdentity(FrozenModel):
    candidate_source_family: Literal["SWE-rebench-leaderboard"]
    source_url: str = Field(pattern=r"^https://")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_published_at: str
    source_window_start_exclusive: Literal[WINDOW_START]
    source_window_end_inclusive: Literal[WINDOW_END]
    raw_source_file_bytes: int = Field(ge=1)
    raw_source_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    raw_source_row_count: int = Field(ge=1)
    provider_declared_row_count: int = Field(ge=1)

    @model_validator(mode="before")
    @classmethod
    def require_exact_integers(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in (
            "raw_source_file_bytes",
            "raw_source_row_count",
            "provider_declared_row_count",
        ):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.raw_source_row_count != self.provider_declared_row_count:
            raise ValueError("provider and raw-source row counts differ")
        return self


class CompletenessChecks(FrozenModel):
    immutable_revision_verified: Literal[True]
    earliest_qualifying_revision_verified: Literal[True]
    complete_frozen_window_verified: Literal[True]
    source_listing_or_pagination_exhausted: Literal[True]
    raw_file_bytes_and_hash_verified: Literal[True]
    provider_and_raw_row_counts_equal: Literal[True]
    normalized_rows_account_for_every_raw_row_exactly_once: Literal[True]
    normalized_ordinals_contiguous: Literal[True]
    public_identity_unique: Literal[True]
    public_row_hashes_recomputed: Literal[True]
    forbidden_solution_test_oracle_private_fields_excluded: Literal[True]
    raw_parser_isolated_from_selector: Literal[True]
    raw_source_bytes_persisted_in_qualification: Literal[False]


class SourceFormatAdapterAuthority(FrozenModel):
    source_files_read: int = Field(ge=1)
    validation_files_read: int = Field(ge=1)
    raw_source_files_read: Literal[0]
    task_package_files_read: Literal[0]
    private_task_files_read: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    adapter_source_qualified: Literal[True]
    raw_source_qualification_executed: Literal[False]
    public_registry_projection_authorized: Literal[False]
    task_admission_authorized: Literal[False]
    execution_authorized: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def require_exact_counts(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in ("source_files_read", "validation_files_read"):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value


class SourceFormatAdapterQualification(FrozenModel):
    schema_version: Literal["lean-fresh-source-format-adapter-source-qualification-v1"]
    qualification_id: str = Field(
        pattern=r"^lean-fresh-source-format-adapter-[a-z0-9-]+-source-qualification-v1$"
    )
    status: Literal["SOURCE_FORMAT_ADAPTER_QUALIFIED_NO_RAW_SOURCE_AUTHORITY"]
    adapter_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+-v[0-9]+$")
    adapter_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    adapter_validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_projection_schema: Literal["lean-fresh-public-source-snapshot-v1"]
    required_qualification_method: Literal[QUALIFICATION_METHOD]
    authority: SourceFormatAdapterAuthority
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("source-format adapter qualification content hash differs")
        return self


class SourceCaptureReceipt(FrozenModel):
    schema_version: Literal["lean-fresh-raw-source-capture-receipt-v1"]
    candidate_source_family: Literal["SWE-rebench-leaderboard"]
    source_url: str = Field(pattern=r"^https://")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_published_at: str
    immutable_revision_resolved: Literal[True]
    earliest_qualifying_revision_verified: Literal[True]
    complete_frozen_window_verified: Literal[True]
    source_listing_or_pagination_exhausted: Literal[True]
    raw_source_file_bytes: int = Field(ge=1)
    raw_source_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    raw_source_row_count: int = Field(ge=1)
    provider_declared_row_count: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="before")
    @classmethod
    def require_exact_counts(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in (
            "raw_source_file_bytes",
            "raw_source_row_count",
            "provider_declared_row_count",
        ):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        if self.raw_source_row_count != self.provider_declared_row_count:
            raise ValueError("source capture row counts differ")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("source capture receipt content hash differs")
        return self


class NormalizationTranscriptRow(FrozenModel):
    source_ordinal: int = Field(ge=1)
    raw_public_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_public_row_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("source_ordinal", mode="before")
    @classmethod
    def require_exact_ordinal(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("source transcript ordinal must be a JSON integer")
        return value


class NormalizationTranscript(FrozenModel):
    schema_version: Literal["lean-fresh-public-normalization-transcript-v1"]
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    raw_source_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    row_count: int = Field(ge=1)
    rows: tuple[NormalizationTranscriptRow, ...]
    solution_test_oracle_private_fields_persisted: Literal[0]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("row_count", mode="before")
    @classmethod
    def require_exact_row_count(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("normalization transcript row count must be a JSON integer")
        return value

    @field_validator("rows", mode="before")
    @classmethod
    def freeze_rows(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def validate_transcript(self) -> Self:
        if self.row_count != len(self.rows):
            raise ValueError("normalization transcript row count differs")
        if [row.source_ordinal for row in self.rows] != list(range(1, self.row_count + 1)):
            raise ValueError("normalization transcript ordinals differ")
        normalized = [row.normalized_public_row_hash for row in self.rows]
        raw = [row.raw_public_projection_hash for row in self.rows]
        if len(normalized) != len(set(normalized)) or len(raw) != len(set(raw)):
            raise ValueError("normalization transcript repeats a row")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("normalization transcript content hash differs")
        return self


class QualificationEvidence(FrozenModel):
    qualification_method: Literal[QUALIFICATION_METHOD]
    source_format_adapter: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]+-v[0-9]+$")
    source_format_adapter_qualification_binding: FileBinding
    qualifier_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    qualifier_validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_capture_receipt_binding: FileBinding
    normalization_transcript_binding: FileBinding
    source_capture_receipt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalization_transcript_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalization_transcript_rows: int = Field(ge=1)

    @model_validator(mode="before")
    @classmethod
    def require_exact_transcript_count(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "normalization_transcript_rows" in value
            and type(value["normalization_transcript_rows"]) is not int
        ):
            raise ValueError("normalization transcript rows must be a JSON integer")
        return value


class QualificationAuthority(FrozenModel):
    raw_source_files_read_by_isolated_qualifier: Literal[1]
    normalized_snapshot_files_read: Literal[1]
    selector_raw_source_files_read: Literal[0]
    task_package_files_read: Literal[0]
    private_task_files_read: Literal[0]
    solution_test_patch_or_oracle_fields_persisted: Literal[0]
    network_calls_during_offline_replay: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    raw_source_completeness_qualified: Literal[True]
    public_registry_projection_authorized: Literal[True]
    task_admission_authorized: Literal[False]
    fresh_panel_materialized: Literal[False]
    full_experiment_preregistered: Literal[False]
    candidate_created: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class FreshSourceCompletenessQualification(FrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    qualification_id: str = Field(pattern=r"^lean-fresh-source-completeness-[a-z0-9-]+-v1$")
    status: Literal[STATUS]
    source_snapshot_binding: FileBinding
    raw_source_identity: RawSourceIdentity
    completeness_checks: CompletenessChecks
    evidence: QualificationEvidence
    authority: QualificationAuthority
    next_gate: Literal[
        "run-the-frozen-public-selector-and-audit-the-complete-transcript-before-task-admission"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_envelope(self) -> Self:
        if self.source_snapshot_binding.role != "normalized-public-source-snapshot":
            raise ValueError("source qualification snapshot role differs")
        if (
            self.evidence.normalization_transcript_rows
            != self.raw_source_identity.raw_source_row_count
        ):
            raise ValueError("normalization transcript row count differs")
        if (
            self.evidence.source_format_adapter_qualification_binding.role
            != "raw-source-format-adapter-qualification"
        ):
            raise ValueError("source-format adapter qualification role differs")
        if self.evidence.source_capture_receipt_binding.role != "raw-source-capture-receipt":
            raise ValueError("source capture receipt role differs")
        if self.evidence.normalization_transcript_binding.role != "public-normalization-transcript":
            raise ValueError("normalization transcript role differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("source completeness content hash differs")
        return self


def _relative_artifact_path(value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute() or "\\" in value:
        raise FreshSourceCompletenessError("qualification path must be repository-relative POSIX")
    normalized = candidate.as_posix()
    if normalized in {"", "."} or normalized.startswith("../") or "/../" in normalized:
        raise FreshSourceCompletenessError("qualification path escapes the repository")
    if normalized != value or normalized.startswith(("tasks/", ".patchloop/")):
        raise FreshSourceCompletenessError("qualification path is not an allowed artifact path")
    return value


def _resolved_artifact(root: Path, path: str) -> Path:
    relative = _relative_artifact_path(path)
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        is_junction = getattr(cursor, "is_junction", lambda: False)
        if cursor.exists() and (cursor.is_symlink() or is_junction()):
            raise FreshSourceCompletenessError("qualification path contains a link")
    return ensure_within(root, relative)


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshSourceCompletenessError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshSourceCompletenessError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise FreshSourceCompletenessError(f"{label} must be an object")
    return value


def qualification_bytes(value: FreshSourceCompletenessQualification) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def adapter_source_qualification_bytes(value: SourceFormatAdapterQualification) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def source_capture_receipt_bytes(value: SourceCaptureReceipt) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def normalization_transcript_bytes(value: NormalizationTranscript) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _load_adapter_source_qualification(
    root: Path,
    binding: FileBinding,
) -> SourceFormatAdapterQualification:
    if binding.role != "raw-source-format-adapter-qualification":
        raise FreshSourceCompletenessError("source-format adapter qualification role differs")
    selected = _resolved_artifact(root, binding.path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceCompletenessError(
            "source-format adapter qualification is unavailable"
        ) from exc
    _json_object(raw, label="source-format adapter qualification")
    try:
        value = SourceFormatAdapterQualification.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceCompletenessError(
            "source-format adapter qualification contract is invalid"
        ) from exc
    if not (
        adapter_source_qualification_bytes(value) == raw
        and binding.file_bytes == len(raw)
        and binding.file_sha256 == sha256_bytes(raw)
        and binding.content_hash == value.content_hash
    ):
        raise FreshSourceCompletenessError("source-format adapter qualification binding differs")
    return value


def _load_source_capture_receipt(root: Path, binding: FileBinding) -> SourceCaptureReceipt:
    if binding.role != "raw-source-capture-receipt":
        raise FreshSourceCompletenessError("source capture receipt role differs")
    selected = _resolved_artifact(root, binding.path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceCompletenessError("source capture receipt is unavailable") from exc
    _json_object(raw, label="source capture receipt")
    try:
        value = SourceCaptureReceipt.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceCompletenessError("source capture receipt contract is invalid") from exc
    if not (
        source_capture_receipt_bytes(value) == raw
        and binding.file_bytes == len(raw)
        and binding.file_sha256 == sha256_bytes(raw)
        and binding.content_hash == value.content_hash
    ):
        raise FreshSourceCompletenessError("source capture receipt binding differs")
    return value


def _load_normalization_transcript(
    root: Path,
    binding: FileBinding,
) -> NormalizationTranscript:
    if binding.role != "public-normalization-transcript":
        raise FreshSourceCompletenessError("normalization transcript role differs")
    selected = _resolved_artifact(root, binding.path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceCompletenessError("normalization transcript is unavailable") from exc
    _json_object(raw, label="normalization transcript")
    try:
        value = NormalizationTranscript.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceCompletenessError("normalization transcript contract is invalid") from exc
    if not (
        normalization_transcript_bytes(value) == raw
        and binding.file_bytes == len(raw)
        and binding.file_sha256 == sha256_bytes(raw)
        and binding.content_hash == value.content_hash
    ):
        raise FreshSourceCompletenessError("normalization transcript binding differs")
    return value


def _validate_snapshot_binding(
    qualification: FreshSourceCompletenessQualification,
    snapshot: FreshPublicSourceSnapshot,
    snapshot_raw: bytes,
) -> None:
    binding = qualification.source_snapshot_binding
    if not (
        binding.file_bytes == len(snapshot_raw)
        and binding.file_sha256 == sha256_bytes(snapshot_raw)
        and binding.content_hash == snapshot.content_hash
        and qualification.raw_source_identity.candidate_source_family
        == snapshot.candidate_source_family
        and qualification.raw_source_identity.source_url == snapshot.source_url
        and qualification.raw_source_identity.source_revision == snapshot.source_revision
        and qualification.raw_source_identity.source_published_at == snapshot.source_published_at
        and qualification.raw_source_identity.source_window_start_exclusive
        == snapshot.source_window_start_exclusive
        and qualification.raw_source_identity.source_window_end_inclusive
        == snapshot.source_window_end_inclusive
        and qualification.raw_source_identity.raw_source_file_bytes
        == snapshot.raw_source_file_bytes
        and qualification.raw_source_identity.raw_source_file_sha256
        == snapshot.raw_source_file_sha256
        and qualification.raw_source_identity.raw_source_row_count == snapshot.raw_source_row_count
        and qualification.raw_source_identity.provider_declared_row_count
        == snapshot.declared_source_row_count
        and qualification.evidence.normalization_transcript_rows == len(snapshot.rows)
    ):
        raise FreshSourceCompletenessError("source qualification snapshot binding differs")


def load_fresh_source_completeness_qualification(
    repository: str | Path,
    path: str,
) -> tuple[FreshSourceCompletenessQualification, bytes]:
    root = Path(repository).resolve()
    selected = _resolved_artifact(root, path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceCompletenessError(
            "source completeness qualification is unavailable"
        ) from exc
    _json_object(raw, label="source completeness qualification")
    try:
        value = FreshSourceCompletenessQualification.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceCompletenessError(
            "source completeness qualification contract is invalid"
        ) from exc
    if qualification_bytes(value) != raw:
        raise FreshSourceCompletenessError(
            "source completeness qualification bytes are not canonical"
        )
    adapter = _load_adapter_source_qualification(
        root, value.evidence.source_format_adapter_qualification_binding
    )
    if not (
        adapter.adapter_id == value.evidence.source_format_adapter
        and adapter.adapter_source_hash == value.evidence.qualifier_source_hash
        and adapter.adapter_validation_hash == value.evidence.qualifier_validation_hash
        and adapter.required_qualification_method == value.evidence.qualification_method
    ):
        raise FreshSourceCompletenessError("source-format adapter qualification identity differs")
    receipt = _load_source_capture_receipt(root, value.evidence.source_capture_receipt_binding)
    transcript = _load_normalization_transcript(
        root, value.evidence.normalization_transcript_binding
    )
    if not (
        receipt.content_hash == value.evidence.source_capture_receipt_hash
        and transcript.content_hash == value.evidence.normalization_transcript_hash
        and receipt.candidate_source_family == value.raw_source_identity.candidate_source_family
        and receipt.source_url == value.raw_source_identity.source_url
        and receipt.source_revision == value.raw_source_identity.source_revision
        and receipt.source_published_at == value.raw_source_identity.source_published_at
        and receipt.raw_source_file_bytes == value.raw_source_identity.raw_source_file_bytes
        and receipt.raw_source_file_sha256 == value.raw_source_identity.raw_source_file_sha256
        and receipt.raw_source_row_count == value.raw_source_identity.raw_source_row_count
        and receipt.provider_declared_row_count
        == value.raw_source_identity.provider_declared_row_count
        and transcript.source_revision == value.raw_source_identity.source_revision
        and transcript.raw_source_file_sha256 == value.raw_source_identity.raw_source_file_sha256
        and transcript.row_count == value.evidence.normalization_transcript_rows
    ):
        raise FreshSourceCompletenessError("source qualification evidence differs")
    try:
        snapshot, snapshot_raw = load_public_source_snapshot(
            root, value.source_snapshot_binding.path
        )
    except FreshCandidateRegistryError as exc:
        raise FreshSourceCompletenessError("source qualification snapshot binding differs") from exc
    _validate_snapshot_binding(value, snapshot, snapshot_raw)
    if tuple(row.normalized_public_row_hash for row in transcript.rows) != tuple(
        row.public_row_hash for row in snapshot.rows
    ):
        raise FreshSourceCompletenessError(
            "normalization transcript does not map every snapshot row"
        )
    return value, raw
