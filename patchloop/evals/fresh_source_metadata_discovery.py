"""Offline metadata discovery gate for a future fresh source snapshot.

This gate can identify an immutable post-window *metadata candidate*.  It never
promotes metadata to a qualifying snapshot: raw bytes, adapter qualification,
complete row accounting and normalization remain mandatory downstream.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_source_registry_observation import (
    OUTPUT_PATH as OBSERVATION_PATH,
)
from patchloop.evals.fresh_source_registry_observation import (
    FreshSourceRegistryObservation,
    load_fresh_source_registry_observation,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-fresh-source-metadata-discovery-v1"
DISCOVERY_ID = "lean-fresh-source-metadata-discovery-20260818-v1"
STATUS = "BLOCKED_NO_POST_WINDOW_METADATA_CANDIDATE"
OUTPUT_PATH = "experiments/lean-harness-fresh-source-metadata-discovery-20260818-v1.json"

OBSERVATION_BYTES = 7_161
OBSERVATION_FILE_SHA256 = "sha256:708dba66061c412117b75f86ce6de5a67b9561a12ffa8796808023a6d978389d"
OBSERVATION_CONTENT_HASH = "sha256:cc2e0d8678f4aeb404c586efe87af62cdbf01e6be01a9d64292e6fb447329377"
WINDOW_END = "2026-08-16T23:59:59Z"
LEADERBOARD_PACKAGE = "swe-rebench/swe-rebench-leaderboard"
MONTHLY_PACKAGE_PATTERN = re.compile(
    r"^ibragim-badertdinov/swe-rebench-(?:0[1-9]|1[0-2])-20[0-9]{2}$"
)


class FreshSourceMetadataDiscoveryError(ContractError):
    """The fresh-source metadata discovery gate is invalid or drifted."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ObservationBinding(FrozenModel):
    path: Literal[OBSERVATION_PATH]
    file_bytes: Literal[OBSERVATION_BYTES]
    file_sha256: Literal[OBSERVATION_FILE_SHA256]
    content_hash: Literal[OBSERVATION_CONTENT_HASH]
    role: Literal["official-public-registry-metadata-observation"]


class VersionMetadata(FrozenModel):
    id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    package: str = Field(pattern=r"^[a-z0-9-]+/[a-z0-9-]+$")
    revision: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    published_at: str
    yanked: bool

    @field_validator("revision", mode="before")
    @classmethod
    def require_exact_revision(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("revision must be a JSON integer")
        return value

    @field_validator("yanked", mode="before")
    @classmethod
    def require_exact_yanked(cls, value: Any) -> bool:
        if type(value) is not bool:
            raise ValueError("yanked must be a JSON boolean")
        return value

    @field_validator("published_at")
    @classmethod
    def require_utc_timestamp(cls, value: str) -> str:
        _parse_timestamp(value)
        return value


class DiscoveryTranscriptRow(FrozenModel):
    version: VersionMetadata
    disposition: Literal[
        "rejected-disallowed-source-package",
        "rejected-yanked-version",
        "rejected-not-after-frozen-window",
        "pending-raw-capture-and-completeness",
    ]
    selector_eligible: Literal[False]
    raw_completeness_qualified: Literal[False]


class MetadataCandidate(FrozenModel):
    version: VersionMetadata
    rank: int = Field(ge=1)
    status: Literal["PENDING_RAW_CAPTURE_AND_COMPLETENESS"]
    qualifying_snapshot_asserted: Literal[False]
    selector_authorized: Literal[False]

    @field_validator("rank", mode="before")
    @classmethod
    def require_exact_rank(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("candidate rank must be a JSON integer")
        return value


class DiscoveryProjection(FrozenModel):
    transcript: tuple[DiscoveryTranscriptRow, ...]
    candidates: tuple[MetadataCandidate, ...]

    @field_validator("transcript", "candidates", mode="before")
    @classmethod
    def freeze_rows(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        pending = [
            row.version
            for row in self.transcript
            if row.disposition == "pending-raw-capture-and-completeness"
        ]
        if [candidate.version for candidate in self.candidates] != pending:
            raise ValueError("metadata candidates differ from discovery transcript")
        if [candidate.rank for candidate in self.candidates] != list(
            range(1, len(self.candidates) + 1)
        ):
            raise ValueError("metadata candidate ranks differ")
        return self


class DiscoveryRule(FrozenModel):
    allowed_source_packages: Literal["leaderboard-exact-or-ibragim-badertdinov-monthly-name-v1"]
    publish_time_rule: Literal["strictly-after-2026-08-16T23:59:59Z"]
    yanked_versions_allowed: Literal[False]
    immutable_sha256_digest_required: Literal[True]
    ranking: Literal["published-at-then-package-revision-content-hash-ascending"]
    mutable_tags_used_for_ranking: Literal[False]
    metadata_can_establish_complete_frozen_window: Literal[False]
    raw_capture_required_after_candidate: Literal[True]
    source_specific_adapter_qualification_required: Literal[True]
    complete_row_transcript_required: Literal[True]


class CurrentDecision(FrozenModel):
    versions_examined: Literal[3]
    versions_rejected_pre_window: Literal[3]
    versions_rejected_yanked: Literal[0]
    post_window_metadata_candidates: Literal[0]
    disallowed_matching_package_names_observed: Literal[2]
    disallowed_package_task_rows_read: Literal[0]
    qualifying_snapshot_observed: Literal[False]
    raw_capture_permitted_now: Literal[False]
    disposition: Literal[STATUS]


class Authority(FrozenModel):
    registry_observation_files_read: Literal[1]
    network_calls: Literal[0]
    dataset_task_membership_requests: Literal[0]
    task_archive_or_file_requests: Literal[0]
    task_rows_read: Literal[0]
    private_or_oracle_rows_read: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    metadata_candidate_materialized: Literal[False]
    raw_source_qualification_executed: Literal[False]
    candidate_registry_materialized: Literal[False]
    task_admission_authorized: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class FreshSourceMetadataDiscovery(FrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    discovery_id: Literal[DISCOVERY_ID]
    status: Literal[STATUS]
    observation_binding: ObservationBinding
    rule: DiscoveryRule
    projection: DiscoveryProjection
    current_decision: CurrentDecision
    authority: Authority
    next_gate: Literal[
        "create-an-append-only-successor-metadata-observation-only-after-a-new-visible-version-then-rerun-discovery-without-relaxation"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_discovery(self) -> Self:
        if self.projection.candidates:
            raise ValueError("current discovery unexpectedly contains a metadata candidate")
        if len(self.projection.transcript) != self.current_decision.versions_examined:
            raise ValueError("current discovery transcript count differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("fresh-source metadata discovery content hash differs")
        return self


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("published_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("published_at must have a timezone")
    return parsed.astimezone(UTC)


def _allowed_source_package(value: str) -> bool:
    return value == LEADERBOARD_PACKAGE or MONTHLY_PACKAGE_PATTERN.fullmatch(value) is not None


def discover_metadata_candidates(
    versions: tuple[VersionMetadata, ...] | list[VersionMetadata],
) -> DiscoveryProjection:
    window_end = _parse_timestamp(WINDOW_END)
    ordered = sorted(
        tuple(versions),
        key=lambda row: (
            _parse_timestamp(row.published_at),
            row.package,
            row.revision,
            row.content_hash,
        ),
    )
    transcript: list[DiscoveryTranscriptRow] = []
    pending: list[VersionMetadata] = []
    for version in ordered:
        if not _allowed_source_package(version.package):
            disposition = "rejected-disallowed-source-package"
        elif version.yanked:
            disposition = "rejected-yanked-version"
        elif _parse_timestamp(version.published_at) <= window_end:
            disposition = "rejected-not-after-frozen-window"
        else:
            disposition = "pending-raw-capture-and-completeness"
            pending.append(version)
        transcript.append(
            DiscoveryTranscriptRow(
                version=version,
                disposition=disposition,
                selector_eligible=False,
                raw_completeness_qualified=False,
            )
        )
    return DiscoveryProjection(
        transcript=tuple(transcript),
        candidates=tuple(
            MetadataCandidate(
                version=version,
                rank=rank,
                status="PENDING_RAW_CAPTURE_AND_COMPLETENESS",
                qualifying_snapshot_asserted=False,
                selector_authorized=False,
            )
            for rank, version in enumerate(pending, start=1)
        ),
    )


def _binding() -> ObservationBinding:
    return ObservationBinding(
        path=OBSERVATION_PATH,
        file_bytes=OBSERVATION_BYTES,
        file_sha256=OBSERVATION_FILE_SHA256,
        content_hash=OBSERVATION_CONTENT_HASH,
        role="official-public-registry-metadata-observation",
    )


def _rule() -> DiscoveryRule:
    return DiscoveryRule(
        allowed_source_packages="leaderboard-exact-or-ibragim-badertdinov-monthly-name-v1",
        publish_time_rule="strictly-after-2026-08-16T23:59:59Z",
        yanked_versions_allowed=False,
        immutable_sha256_digest_required=True,
        ranking="published-at-then-package-revision-content-hash-ascending",
        mutable_tags_used_for_ranking=False,
        metadata_can_establish_complete_frozen_window=False,
        raw_capture_required_after_candidate=True,
        source_specific_adapter_qualification_required=True,
        complete_row_transcript_required=True,
    )


def _current_projection(observation: FreshSourceRegistryObservation) -> DiscoveryProjection:
    return discover_metadata_candidates(
        [
            VersionMetadata(
                id=row.id,
                package=row.package,
                revision=row.revision,
                content_hash=row.content_hash,
                published_at=row.published_at,
                yanked=row.yanked,
            )
            for row in observation.observed_rows.versions
        ]
    )


def _decision() -> CurrentDecision:
    return CurrentDecision(
        versions_examined=3,
        versions_rejected_pre_window=3,
        versions_rejected_yanked=0,
        post_window_metadata_candidates=0,
        disallowed_matching_package_names_observed=2,
        disallowed_package_task_rows_read=0,
        qualifying_snapshot_observed=False,
        raw_capture_permitted_now=False,
        disposition=STATUS,
    )


def _authority() -> Authority:
    return Authority(
        registry_observation_files_read=1,
        network_calls=0,
        dataset_task_membership_requests=0,
        task_archive_or_file_requests=0,
        task_rows_read=0,
        private_or_oracle_rows_read=0,
        docker_calls=0,
        provider_calls=0,
        evaluator_calls=0,
        agent_runs=0,
        added_model_cost_usd=0,
        metadata_candidate_materialized=False,
        raw_source_qualification_executed=False,
        candidate_registry_materialized=False,
        task_admission_authorized=False,
        execution_authorized=False,
        official_analysis_authorized=False,
        memory_effect_claim_authorized=False,
    )


def _read_observation(root: Path) -> FreshSourceRegistryObservation:
    selected = ensure_within(root, OBSERVATION_PATH)
    raw = selected.read_bytes()
    if not (len(raw) == OBSERVATION_BYTES and sha256_bytes(raw) == OBSERVATION_FILE_SHA256):
        raise FreshSourceMetadataDiscoveryError("registry observation bytes differ")
    value = load_fresh_source_registry_observation(root, OBSERVATION_PATH)
    if value.content_hash != OBSERVATION_CONTENT_HASH:
        raise FreshSourceMetadataDiscoveryError("registry observation content differs")
    return value


def build_fresh_source_metadata_discovery(
    repository: str | Path = ".",
) -> FreshSourceMetadataDiscovery:
    root = Path(repository).resolve()
    observation = _read_observation(root)
    projection = _current_projection(observation)
    if projection.candidates or any(
        row.disposition != "rejected-not-after-frozen-window" for row in projection.transcript
    ):
        raise FreshSourceMetadataDiscoveryError("current registry discovery facts differ")
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "discovery_id": DISCOVERY_ID,
        "status": STATUS,
        "observation_binding": _binding(),
        "rule": _rule(),
        "projection": projection,
        "current_decision": _decision(),
        "authority": _authority(),
        "next_gate": (
            "create-an-append-only-successor-metadata-observation-only-after-a-new-visible-"
            "version-then-rerun-discovery-without-relaxation"
        ),
    }
    hashed = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return FreshSourceMetadataDiscovery(**body, content_hash=sha256_json(hashed))


def discovery_bytes(value: FreshSourceMetadataDiscovery) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _reject_duplicate_keys(raw: bytes) -> None:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshSourceMetadataDiscoveryError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshSourceMetadataDiscoveryError("metadata discovery is invalid JSON") from exc
    if not isinstance(value, dict):
        raise FreshSourceMetadataDiscoveryError("metadata discovery must be an object")


def load_fresh_source_metadata_discovery(
    repository: str | Path = ".", path: str = OUTPUT_PATH
) -> FreshSourceMetadataDiscovery:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceMetadataDiscoveryError("metadata discovery is unavailable") from exc
    _reject_duplicate_keys(raw)
    try:
        value = FreshSourceMetadataDiscovery.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceMetadataDiscoveryError("metadata discovery contract is invalid") from exc
    if discovery_bytes(value) != raw:
        raise FreshSourceMetadataDiscoveryError("metadata discovery bytes are not canonical")
    _read_observation(root)
    if not (
        value.observation_binding == _binding()
        and value.rule == _rule()
        and value.projection
        == _current_projection(load_fresh_source_registry_observation(root, OBSERVATION_PATH))
        and value.current_decision == _decision()
        and value.authority == _authority()
    ):
        raise FreshSourceMetadataDiscoveryError("metadata discovery facts differ")
    return value


def materialize_fresh_source_metadata_discovery(
    repository: str | Path = ".", path: str = OUTPUT_PATH
) -> FreshSourceMetadataDiscovery:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    if selected.exists():
        return load_fresh_source_metadata_discovery(root, path)
    value = build_fresh_source_metadata_discovery(root)
    raw = discovery_bytes(value)
    selected.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(selected, flags, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return load_fresh_source_metadata_discovery(root, path)
