"""Append-only public-source availability checkpoint for fresh-panel acquisition.

This module records a bounded public-metadata observation made after the fresh
acquisition design was preregistered.  It does not download task rows, inspect
task packages or oracle material, qualify source code, or authorize execution.
The materializer is offline: a future public snapshot requires a new successor
checkpoint rather than mutation of this observation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Self, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_acquisition_preregistration import (
    FreshAcquisitionPreregistration,
    preregistration_bytes,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-harness-fresh-source-availability-v3"
CHECKPOINT_ID = "lean-harness-fresh-source-availability-20260818-v3"
STATUS = "NO_QUALIFYING_SNAPSHOT_OBSERVED_AT_CHECKPOINT"
OBSERVED_AT = "2026-08-17T18:37:43.6220149Z"
OUTPUT_PATH = "experiments/lean-harness-fresh-source-availability-20260818-v3.json"

PREDECESSOR_PATH = "experiments/lean-harness-fresh-source-availability-20260818-v2.json"
PREDECESSOR_BYTES = 5_139
PREDECESSOR_FILE_SHA256 = "sha256:65a726d657b2f8119c224eca0dcfddee3eda81b1d18971c0420cf905e2b9f8c0"
PREDECESSOR_CONTENT_HASH = "sha256:6c841590acf00d88605fd3e4095cf8b6626918bf95bc6e0a494ccba39d61efb3"

PREREGISTRATION_PATH = "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json"
PREREGISTRATION_BYTES = 7_255
PREREGISTRATION_FILE_SHA256 = (
    "sha256:086b9fc56ab5eca3ae23cd367243d9b71c3805d7f3edd3613afdb73a34bbf359"
)
PREREGISTRATION_CONTENT_HASH = (
    "sha256:adec1153d8eab532d118fe24d0f60247385d154dbcc840db8dc24167c0c1cb94"
)

HF_DATA_TREE_URL = "https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard/tree/main/data"
HF_COMMIT_HISTORY_URL = (
    "https://huggingface.co/datasets/nebius/SWE-rebench-leaderboard/commits/main/data"
)
HARBOR_MAIN_DATASET_URL = (
    "https://hub.harborframework.com/datasets/swe-rebench/swe-rebench-leaderboard/latest"
)
HARBOR_AUGUST_DATASET_URL = (
    "https://hub.harborframework.com/datasets/ibragim-badertdinov/swe-rebench-08-2026/latest"
)


class FreshSourceAvailabilityError(ContractError):
    """The fresh-source availability checkpoint is invalid or has drifted."""


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


class PreregistrationBinding(FrozenModel):
    path: Literal[PREREGISTRATION_PATH]
    file_bytes: Literal[PREREGISTRATION_BYTES]
    file_sha256: Literal[PREREGISTRATION_FILE_SHA256]
    content_hash: Literal[PREREGISTRATION_CONTENT_HASH]
    role: Literal["outcome-blind-fresh-acquisition-preregistration"]


class PredecessorBinding(FrozenModel):
    path: Literal[PREDECESSOR_PATH]
    file_bytes: Literal[PREDECESSOR_BYTES]
    file_sha256: Literal[PREDECESSOR_FILE_SHA256]
    content_hash: Literal[PREDECESSOR_CONTENT_HASH]
    role: Literal["immutable-no-qualifying-snapshot-predecessor"]


class RequiredSnapshot(FrozenModel):
    candidate_source_family: Literal["SWE-rebench-leaderboard"]
    snapshot_selection: Literal[
        "earliest-published-immutable-revision-after-2026-08-16-containing-the-complete-frozen-window"
    ]
    source_window_start_exclusive: Literal["2026-03-17T23:59:59Z"]
    source_window_end_inclusive: Literal["2026-08-16T23:59:59Z"]
    completeness_evidence_required: Literal[
        "immutable-source-snapshot-plus-complete-query-transcript-and-append-only-rejection-log"
    ]


class HuggingFaceObservation(FrozenModel):
    data_tree_url: Literal[HF_DATA_TREE_URL]
    commit_history_url: Literal[HF_COMMIT_HISTORY_URL]
    data_tree_head_short_commit: Literal["ab4805d"]
    latest_monthly_split_observed: Literal["2026_03"]
    latest_monthly_split_commit_short: Literal["a1191b8"]
    complete_frozen_window_observed: Literal[False]


class HarborObservation(FrozenModel):
    main_dataset_url: Literal[HARBOR_MAIN_DATASET_URL]
    august_snapshot_url: Literal[HARBOR_AUGUST_DATASET_URL]
    direct_fetch_attempts: Literal[2]
    successful_direct_fetches: Literal[0]
    main_dataset_fetch_outcome: Literal["timeout"]
    august_snapshot_fetch_outcome: Literal["safe-open-rejected"]
    public_search_queries: Literal[2]
    public_search_results_observed: Literal[0]
    current_http_status_observed: Literal[False]
    august_2026_monthly_snapshot_observed: Literal[False]
    complete_frozen_window_observed: Literal[False]


class AvailabilityDecision(FrozenModel):
    successful_authoritative_pages_read: Literal[2]
    inconclusive_harbor_direct_fetches: Literal[2]
    public_search_queries: Literal[3]
    public_search_results_observed: Literal[0]
    qualifying_snapshot_observed: Literal[False]
    qualifying_snapshot_absence_proven: Literal[False]
    candidate_registry_materialized: Literal[False]
    task_package_materialization_allowed: Literal[False]
    acquisition_rules_relaxed: Literal[False]
    disposition: Literal["blocked-without-relaxation"]
    reason: Literal[
        "hugging-face-remained-at-2026-03-while-harbor-direct-recheck-was-inconclusive-and-public-search-returned-no-successor-result-so-no-qualifying-snapshot-was-observed"
    ]


class EvidenceLimitations(FrozenModel):
    observation_method: Literal["interactive-public-metadata-browser-review"]
    direct_public_metadata_fetch_attempts: Literal[4]
    successful_authoritative_page_reads: Literal[2]
    inconclusive_harbor_fetches: Literal[2]
    search_queries_with_zero_results: Literal[3]
    raw_http_response_bytes_persisted: Literal[False]
    remote_page_file_hashes_recorded: Literal[False]
    absence_claim_scope: Literal[
        "only-no-qualifying-snapshot-observed-on-two-successful-pages-and-three-zero-result-searches-at-observed-at"
    ]
    harbor_current_status_established: Literal[False]
    future_snapshot_availability_ruled_out: Literal[False]
    task_validity_established: Literal[False]
    registry_completeness_established: Literal[False]


class Authority(FrozenModel):
    public_metadata_browser_lookup_performed: Literal[True]
    public_metadata_fetches_attempted: Literal[4]
    public_metadata_pages_read: Literal[2]
    public_search_queries: Literal[3]
    offline_builder_network_calls: Literal[0]
    task_rows_downloaded: Literal[0]
    task_package_files_read: Literal[0]
    private_task_files_read: Literal[0]
    oracle_solution_pages_opened: Literal[0]
    r16_row_outcomes_or_traces_read: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    candidate_registry_materialized: Literal[False]
    fresh_task_panel_materialized: Literal[False]
    task_admission_authorized: Literal[False]
    full_experiment_preregistered: Literal[False]
    runtime_source_qualified_for_fresh_panel: Literal[False]
    candidate_created: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class FreshSourceAvailabilityCheckpoint(FrozenModel):
    schema_version: Literal[SCHEMA_VERSION]
    checkpoint_id: Literal[CHECKPOINT_ID]
    status: Literal[STATUS]
    observed_at: Literal[OBSERVED_AT]
    predecessor_binding: PredecessorBinding
    preregistration_binding: PreregistrationBinding
    required_snapshot: RequiredSnapshot
    hugging_face_observation: HuggingFaceObservation
    harbor_observation: HarborObservation
    decision: AvailabilityDecision
    evidence_limitations: EvidenceLimitations
    authority: Authority
    next_gate: Literal[
        "wait-for-and-record-a-successor-observation-of-the-earliest-qualifying-immutable-snapshot-before-materializing-a-candidate-registry"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_content_hash(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("fresh-source availability content hash differs")
        return self


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshSourceAvailabilityError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshSourceAvailabilityError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise FreshSourceAvailabilityError(f"{label} must be an object")
    return value


def _binding() -> PreregistrationBinding:
    return PreregistrationBinding(
        path=PREREGISTRATION_PATH,
        file_bytes=PREREGISTRATION_BYTES,
        file_sha256=PREREGISTRATION_FILE_SHA256,
        content_hash=PREREGISTRATION_CONTENT_HASH,
        role="outcome-blind-fresh-acquisition-preregistration",
    )


def _predecessor_binding() -> PredecessorBinding:
    return PredecessorBinding(
        path=PREDECESSOR_PATH,
        file_bytes=PREDECESSOR_BYTES,
        file_sha256=PREDECESSOR_FILE_SHA256,
        content_hash=PREDECESSOR_CONTENT_HASH,
        role="immutable-no-qualifying-snapshot-predecessor",
    )


def _read_predecessor(root: Path) -> bytes:
    binding = _predecessor_binding()
    selected = ensure_within(root, binding.path)
    if selected.is_symlink():
        raise FreshSourceAvailabilityError("fresh-source predecessor is a symlink")
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceAvailabilityError("fresh-source predecessor is unavailable") from exc
    if len(raw) != binding.file_bytes or sha256_bytes(raw) != binding.file_sha256:
        raise FreshSourceAvailabilityError("fresh-source predecessor differs")
    parsed = _json_object(raw, label="fresh-source predecessor")
    if not (
        parsed.get("schema_version") == "lean-harness-fresh-source-availability-v2"
        and parsed.get("checkpoint_id") == "lean-harness-fresh-source-availability-20260818-v2"
        and parsed.get("content_hash") == binding.content_hash
        and (parsed.get("decision") or {}).get("qualifying_snapshot_observed") is False
        and (parsed.get("decision") or {}).get("candidate_registry_materialized") is False
        and (parsed.get("authority") or {}).get("execution_authorized") is False
    ):
        raise FreshSourceAvailabilityError("fresh-source predecessor authority differs")
    return raw


def _read_preregistration(root: Path) -> FreshAcquisitionPreregistration:
    binding = _binding()
    selected = ensure_within(root, binding.path)
    if selected.is_symlink():
        raise FreshSourceAvailabilityError("fresh acquisition preregistration is a symlink")
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceAvailabilityError(
            "fresh acquisition preregistration is unavailable"
        ) from exc
    if len(raw) != binding.file_bytes or sha256_bytes(raw) != binding.file_sha256:
        raise FreshSourceAvailabilityError("fresh acquisition preregistration differs")
    _json_object(raw, label="fresh acquisition preregistration")
    try:
        value = FreshAcquisitionPreregistration.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceAvailabilityError(
            "fresh acquisition preregistration contract is invalid"
        ) from exc
    if preregistration_bytes(value) != raw or value.content_hash != binding.content_hash:
        raise FreshSourceAvailabilityError("fresh acquisition preregistration identity differs")
    if not (
        value.acquisition_design.candidate_source_family == "SWE-rebench-leaderboard"
        and value.acquisition_design.source_window_start_exclusive == "2026-03-17T23:59:59Z"
        and value.acquisition_design.source_window_end_inclusive == "2026-08-16T23:59:59Z"
        and value.current_pool_audit.eligible_fresh_task_count == 0
        and value.authority.candidate_registry_materialized is False
        and value.authority.execution_authorized is False
    ):
        raise FreshSourceAvailabilityError("fresh acquisition authority or source rule differs")
    return value


def _required_snapshot() -> RequiredSnapshot:
    return RequiredSnapshot(
        candidate_source_family="SWE-rebench-leaderboard",
        snapshot_selection=(
            "earliest-published-immutable-revision-after-2026-08-16-containing-the-complete-"
            "frozen-window"
        ),
        source_window_start_exclusive="2026-03-17T23:59:59Z",
        source_window_end_inclusive="2026-08-16T23:59:59Z",
        completeness_evidence_required=(
            "immutable-source-snapshot-plus-complete-query-transcript-and-append-only-rejection-log"
        ),
    )


def _hugging_face_observation() -> HuggingFaceObservation:
    return HuggingFaceObservation(
        data_tree_url=HF_DATA_TREE_URL,
        commit_history_url=HF_COMMIT_HISTORY_URL,
        data_tree_head_short_commit="ab4805d",
        latest_monthly_split_observed="2026_03",
        latest_monthly_split_commit_short="a1191b8",
        complete_frozen_window_observed=False,
    )


def _harbor_observation() -> HarborObservation:
    return HarborObservation(
        main_dataset_url=HARBOR_MAIN_DATASET_URL,
        august_snapshot_url=HARBOR_AUGUST_DATASET_URL,
        direct_fetch_attempts=2,
        successful_direct_fetches=0,
        main_dataset_fetch_outcome="timeout",
        august_snapshot_fetch_outcome="safe-open-rejected",
        public_search_queries=2,
        public_search_results_observed=0,
        current_http_status_observed=False,
        august_2026_monthly_snapshot_observed=False,
        complete_frozen_window_observed=False,
    )


def _decision() -> AvailabilityDecision:
    return AvailabilityDecision(
        successful_authoritative_pages_read=2,
        inconclusive_harbor_direct_fetches=2,
        public_search_queries=3,
        public_search_results_observed=0,
        qualifying_snapshot_observed=False,
        qualifying_snapshot_absence_proven=False,
        candidate_registry_materialized=False,
        task_package_materialization_allowed=False,
        acquisition_rules_relaxed=False,
        disposition="blocked-without-relaxation",
        reason=(
            "hugging-face-remained-at-2026-03-while-harbor-direct-recheck-was-inconclusive-"
            "and-public-search-returned-no-successor-result-so-no-qualifying-snapshot-was-"
            "observed"
        ),
    )


def _limitations() -> EvidenceLimitations:
    return EvidenceLimitations(
        observation_method="interactive-public-metadata-browser-review",
        direct_public_metadata_fetch_attempts=4,
        successful_authoritative_page_reads=2,
        inconclusive_harbor_fetches=2,
        search_queries_with_zero_results=3,
        raw_http_response_bytes_persisted=False,
        remote_page_file_hashes_recorded=False,
        absence_claim_scope=(
            "only-no-qualifying-snapshot-observed-on-two-successful-pages-and-three-zero-"
            "result-searches-at-observed-at"
        ),
        harbor_current_status_established=False,
        future_snapshot_availability_ruled_out=False,
        task_validity_established=False,
        registry_completeness_established=False,
    )


def _authority() -> Authority:
    return Authority(
        public_metadata_browser_lookup_performed=True,
        public_metadata_fetches_attempted=4,
        public_metadata_pages_read=2,
        public_search_queries=3,
        offline_builder_network_calls=0,
        task_rows_downloaded=0,
        task_package_files_read=0,
        private_task_files_read=0,
        oracle_solution_pages_opened=0,
        r16_row_outcomes_or_traces_read=0,
        docker_calls=0,
        provider_calls=0,
        evaluator_calls=0,
        agent_runs=0,
        added_model_cost_usd=0,
        candidate_registry_materialized=False,
        fresh_task_panel_materialized=False,
        task_admission_authorized=False,
        full_experiment_preregistered=False,
        runtime_source_qualified_for_fresh_panel=False,
        candidate_created=False,
        approval_granted=False,
        execution_authorized=False,
        official_analysis_authorized=False,
        memory_effect_claim_authorized=False,
    )


def build_fresh_source_availability_checkpoint(
    repository: str | Path = ".",
) -> FreshSourceAvailabilityCheckpoint:
    root = Path(repository).resolve()
    _read_predecessor(root)
    _read_preregistration(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "checkpoint_id": CHECKPOINT_ID,
        "status": STATUS,
        "observed_at": OBSERVED_AT,
        "predecessor_binding": _predecessor_binding(),
        "preregistration_binding": _binding(),
        "required_snapshot": _required_snapshot(),
        "hugging_face_observation": _hugging_face_observation(),
        "harbor_observation": _harbor_observation(),
        "decision": _decision(),
        "evidence_limitations": _limitations(),
        "authority": _authority(),
        "next_gate": (
            "wait-for-and-record-a-successor-observation-of-the-earliest-qualifying-immutable-"
            "snapshot-before-materializing-a-candidate-registry"
        ),
    }
    hashed_body = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return FreshSourceAvailabilityCheckpoint(
        **body,
        content_hash=sha256_json(hashed_body),
    )


def checkpoint_bytes(checkpoint: FreshSourceAvailabilityCheckpoint) -> bytes:
    return (
        json.dumps(
            checkpoint.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_frozen_contract(value: FreshSourceAvailabilityCheckpoint) -> None:
    if not (
        value.predecessor_binding == _predecessor_binding()
        and value.preregistration_binding == _binding()
        and value.required_snapshot == _required_snapshot()
        and value.hugging_face_observation == _hugging_face_observation()
        and value.harbor_observation == _harbor_observation()
        and value.decision == _decision()
        and value.evidence_limitations == _limitations()
        and value.authority == _authority()
    ):
        raise FreshSourceAvailabilityError("fresh-source availability facts differ")


def load_fresh_source_availability_checkpoint(
    repository: str | Path = ".", path: str = OUTPUT_PATH
) -> FreshSourceAvailabilityCheckpoint:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    try:
        raw = selected.read_bytes()
    except OSError as exc:
        raise FreshSourceAvailabilityError(
            "fresh-source availability checkpoint is unavailable"
        ) from exc
    _json_object(raw, label="fresh-source availability checkpoint")
    try:
        value = FreshSourceAvailabilityCheckpoint.model_validate_json(raw)
    except ValueError as exc:
        raise FreshSourceAvailabilityError(
            "fresh-source availability checkpoint contract is invalid"
        ) from exc
    if checkpoint_bytes(value) != raw:
        raise FreshSourceAvailabilityError(
            "fresh-source availability checkpoint bytes are not canonical"
        )
    _read_predecessor(root)
    _read_preregistration(root)
    _validate_frozen_contract(value)
    return value


def materialize_fresh_source_availability_checkpoint(
    repository: str | Path = ".", path: str = OUTPUT_PATH
) -> FreshSourceAvailabilityCheckpoint:
    root = Path(repository).resolve()
    selected = ensure_within(root, path)
    if selected.exists():
        return load_fresh_source_availability_checkpoint(root, path)
    value = build_fresh_source_availability_checkpoint(root)
    raw = checkpoint_bytes(value)
    selected.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(selected, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise
    return load_fresh_source_availability_checkpoint(root, path)
