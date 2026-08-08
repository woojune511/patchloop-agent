"""Append-only successor validation for the sealed D-112 diagnostic.

D-114 does not edit or replay D-112.  It validates the exact historical
receipt and completion gate under the D-113 trust anchor, then independently
replays the nine recorded score rows from checked-in public evidence.  The
portable path never rehydrates the local embedding snapshot or installed
embedding dependency versions and never loads or encodes a model.

The optional current-input mode is deliberately separate.  It first completes
the sealed-historical validation and only then asks an explicit loader to
rebuild D-112's current input state.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
import struct
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-114"
APPROVAL_RECEIPT_SCHEMA_VERSION = "validator-correction-approval-receipt-d114-v1"
COMPLETION_GATE_SCHEMA_VERSION = "validator-correction-completion-gate-d114-v1"

# This is when the exact user approval was observed locally.  It is a
# self-attested record, not an authenticated platform timestamp or signature.
APPROVAL_RECORDED_AT = "2026-08-07T03:04:28.745556Z"
APPROVAL_ACTION_ID = "d114-exact-d113-append-only-validator-correction-1"
APPROVAL_REFERENCE = "user-message:d113-exact-d114-validator-correction-approval"
APPROVAL_STATEMENT_CODE = "EXPLICITLY_APPROVE_D113_EXACT_D114_VALIDATOR_CORRECTION_ONCE"

EXPECTED_D113_CANDIDATE_ID = (
    "d113validatorcandidate_"
    "373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732"
)
EXPECTED_D113_CANDIDATE_BODY_SHA = (
    "sha256:373257ce1e2c904482a2aeb4649495baf737a11b3c958ef8420b66640a7f3732"
)
EXPECTED_D113_CANDIDATE_BYTES = 5_963
EXPECTED_D113_CANDIDATE_FILE_SHA = (
    "sha256:4b576b6b7edbb7ebf9813e8c4ac35fae7af88992dc4dac3a28a181f79aa6e8a9"
)
EXPECTED_D113_ACTION_HASH = (
    "sha256:b086f8066aff043b27a816e1cd77d4ca176a8adc0f75895c362f93efb9641e5d"
)
EXPECTED_D113_SOURCE_GATE_ID = (
    "d113_0cbf14cc933ba33374f7a5b5db2800e62d6e6d1456f2b6eb48facfa35ace568c"
)
EXPECTED_D113_SOURCE_GATE_BODY_SHA = (
    "sha256:0cbf14cc933ba33374f7a5b5db2800e62d6e6d1456f2b6eb48facfa35ace568c"
)
EXPECTED_D113_SOURCE_GATE_BYTES = 3_133
EXPECTED_D113_SOURCE_GATE_FILE_SHA = (
    "sha256:a69677ddfe7875322e4a27d9f7c3b6086e4fa7350ac9f3f68381fe460dc28d54"
)
EXPECTED_D113_PREFLIGHT_BYTES = 8_270
EXPECTED_D113_PREFLIGHT_FILE_SHA = (
    "sha256:f2053137c80a9429251651201f61df942d9e448d0ddf2dab0faf2366bcfbf505"
)

EXPECTED_D112_RECEIPT_ID = (
    "d112probereceipt_"
    "ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257"
)
EXPECTED_D112_RECEIPT_BODY_SHA = (
    "sha256:ad73368b4b0f47174f53762c917f9f39f17e22ac3bd077d795b0b9e1ac8c9257"
)
EXPECTED_D112_RECEIPT_BYTES = 13_835
EXPECTED_D112_RECEIPT_FILE_SHA = (
    "sha256:74fcd761cac65a9cab26529076b7cde60eaa14a1faf40475e680f526e00ba1d1"
)
EXPECTED_D112_GATE_ID = (
    "d112_3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6"
)
EXPECTED_D112_GATE_BODY_SHA = (
    "sha256:3242bed73c9a322ff1d346eba61cfec2f9eae3b57e4cc7e4d7b0e9a5456367b6"
)
EXPECTED_D112_GATE_BYTES = 77_591
EXPECTED_D112_GATE_FILE_SHA = (
    "sha256:a7e691ae43c60405cbb10cd27caf3055eabaa96bb7fa6f2a02142d97aa903951"
)
EXPECTED_D112_INPUT_FINGERPRINT = (
    "sha256:d54454b2693e231c0ef50c94b20d75d58f00a885dfae98d3b6b190665f9d2e17"
)
EXPECTED_D112_APPROVAL_AT = "2026-08-06T16:41:32.316176Z"
EXPECTED_D112_EXECUTION_AT = "2026-08-06T17:16:20.878831Z"
EXPECTED_D112_COMPLETION_AT = "2026-08-06T17:18:33.876453Z"

INDEX_ID = "idxgrp_563976c4443a725e287225cef1e718daf134fbb96574921cb9e020049ea52064"
EXPECTED_MEMORY_IDS = (
    "memgrp_649483b80292fea26e4009ebdb72df31",
    "memgrp_b421547d481faabf9be3511217258de5",
    "memgrp_5a23f463cba43bf3ba395f67cf976047",
)
VECTOR_DIMENSION = 384
VECTOR_DTYPE = "float32"
SELECTIVE_THRESHOLD = 0.72
SCORE_WEIGHTS = {
    "semantic": 0.35,
    "failure_class": 0.25,
    "phase": 0.15,
    "language": 0.15,
    "validation": 0.10,
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")

DEFAULT_D113_PREFLIGHT_PATH = Path(
    "reports/memory-development/d113-d112-validator-correction-preflight.json"
)
DEFAULT_D113_CANDIDATE_PATH = Path(
    "reports/memory-development/d113-validator-correction-authorization-candidate.json"
)
DEFAULT_D113_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d113-validator-correction-source-gate.json"
)
DEFAULT_D112_RECEIPT_PATH = Path(
    "reports/memory-development/d112-retrieval-readiness-probe-receipt.json"
)
DEFAULT_D112_GATE_PATH = Path(
    "reports/memory-development/d112-retrieval-readiness-completion-gate.json"
)
DEFAULT_D110_INDEX_PATH = Path(
    f"reports/memory-development/artifacts/d110/{INDEX_ID}/index.json"
)
DEFAULT_D110_MARKER_PATH = Path(
    f"reports/memory-development/artifacts/d110/{INDEX_ID}/FROZEN"
)
DEFAULT_D106_INDEX_PATH = Path(
    f"reports/memory-development/artifacts/d106/{INDEX_ID}.json"
)
DEFAULT_APPROVAL_RECEIPT_PATH = Path(
    "reports/memory-development/d114-d112-validator-correction-receipt.json"
)
DEFAULT_COMPLETION_GATE_PATH = Path(
    "reports/memory-development/d114-d112-validator-correction-gate.json"
)

D114_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d114_d112_validator_correction.py"),
    Path("scripts/build_d114_d112_validator_correction.py"),
    Path("tests/test_d114_d112_validator_correction.py"),
)

D112_IMPLEMENTATION_SPECS = (
    {
        "path": "patchloop/memory/d112_retrieval_readiness_probe.py",
        "file_bytes": 54_182,
        "file_sha256": "sha256:3df099f518b8c0707a6f6a81921c8735037fb97f1357a45b238148ac67c70d2b",
    },
    {
        "path": "scripts/run_d112_retrieval_readiness_probe.py",
        "file_bytes": 2_000,
        "file_sha256": "sha256:308ed1e6499da73edf064a8ecd211c526c4ef4c0fc0123623f1723135b78cd9e",
    },
    {
        "path": "tests/test_d112_retrieval_readiness_probe.py",
        "file_bytes": 11_297,
        "file_sha256": "sha256:3629de37190cd8337fb3a5c2da07eb6795ca65f8e6599f4ac275fd135e393bb6",
    },
)

PROTECTED_FILE_SPECS = (
    {
        "path": DEFAULT_D112_RECEIPT_PATH.as_posix(),
        "file_bytes": EXPECTED_D112_RECEIPT_BYTES,
        "file_sha256": EXPECTED_D112_RECEIPT_FILE_SHA,
    },
    {
        "path": DEFAULT_D112_GATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D112_GATE_BYTES,
        "file_sha256": EXPECTED_D112_GATE_FILE_SHA,
    },
    *D112_IMPLEMENTATION_SPECS,
    {
        "path": DEFAULT_D110_INDEX_PATH.as_posix(),
        "file_bytes": 55_687,
        "file_sha256": "sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0",
    },
    {
        "path": DEFAULT_D110_MARKER_PATH.as_posix(),
        "file_bytes": 72,
        "file_sha256": "sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561",
    },
    {
        "path": DEFAULT_D106_INDEX_PATH.as_posix(),
        "file_bytes": 55_644,
        "file_sha256": "sha256:c9b292f67fcb3c4bf524065801681e76c5df22142bbbb8b2db36d3c932df358a",
    },
    {
        "path": DEFAULT_D113_PREFLIGHT_PATH.as_posix(),
        "file_bytes": EXPECTED_D113_PREFLIGHT_BYTES,
        "file_sha256": EXPECTED_D113_PREFLIGHT_FILE_SHA,
    },
    {
        "path": DEFAULT_D113_CANDIDATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D113_CANDIDATE_BYTES,
        "file_sha256": EXPECTED_D113_CANDIDATE_FILE_SHA,
    },
    {
        "path": DEFAULT_D113_SOURCE_GATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D113_SOURCE_GATE_BYTES,
        "file_sha256": EXPECTED_D113_SOURCE_GATE_FILE_SHA,
    },
    {
        "path": "tasks/dev-validation/moto-query-scanned-count/public.yaml",
        "file_bytes": 2_839,
        "file_sha256": "sha256:4005b070d9e46c72a68554fbe998e9d81e920321a31e8bf633d3fd32277857f7",
    },
    {
        "path": "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml",
        "file_bytes": 2_023,
        "file_sha256": "sha256:d65e09fe70bb0449c85e663d0eeb695fe52bc7fb34619debbbe81a0b16ab2aca",
    },
)

PUBLIC_TASK_SPECS = {
    "moto-query-scanned-count": {
        "path": "tasks/dev-validation/moto-query-scanned-count/public.yaml",
        "file_bytes": 2_839,
        "file_sha256": "sha256:4005b070d9e46c72a68554fbe998e9d81e920321a31e8bf633d3fd32277857f7",
    },
    "babel-strict-grouped-decimal-trailing-zeroes": {
        "path": "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml",
        "file_bytes": 2_023,
        "file_sha256": "sha256:d65e09fe70bb0449c85e663d0eeb695fe52bc7fb34619debbbe81a0b16ab2aca",
    },
}

RECEIPT_ROOT_KEYS = (
    "schema_version",
    "receipt_id",
    "semantic_body_hash",
    "semantic_body",
)
RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "approval_recorded_at",
    "execution_claimed_at",
    "approval_action_id",
    "approval_reference",
    "approval_reference_mode",
    "approval_statement_code",
    "d111_source_gate",
    "d111_candidate",
    "authorized_action_hash",
    "authorized_scope",
    "probe_ids_in_order",
    "pre_execution_input",
    "claim_semantics",
    "self_attested",
    "approver_kind",
    "approver_label",
    "reviewer_identity_authenticated",
    "cryptographic_signature_verified",
    "execution_result_present",
)
RECEIPT_CLAIM_KEYS = (
    "exclusive_create_and_fsync_required",
    "claim_created_before_model_load",
    "receipt_is_one_use_consumption_marker",
    "failure_or_hard_kill_remains_consumed",
    "automatic_retry_or_rollback_allowed",
    "completion_gate_required_for_success",
    "sidecar_does_not_modify_frozen_authority",
)
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "probe_receipt",
    "input_integrity",
    "embedding_execution",
    "query_vectors",
    "diagnostic_scoring",
    "implementation_files",
    "qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)
GATE_QUALIFICATION_KEYS = (
    "exact_candidate_and_user_approval_bound",
    "one_use_receipt_consumed_before_model_load",
    "local_embedding_model_load_count_exact",
    "local_batch_encode_call_count_exact",
    "ordered_three_public_queries_encoded",
    "query_vector_shape_dtype_finite_normalized",
    "all_nine_component_and_final_score_rows_recorded",
    "rank_and_threshold_recomputed_portably",
    "identical_moto_query_vectors_equal",
    "moto_phase_control_delta_valid",
    "probe_hypotheses_used_as_acceptance_criteria",
    "runtime_selection_executed",
    "memory_text_returned_or_injected",
    "pre_and_post_input_fingerprints_equal",
)
GATE_EVIDENCE_BOUNDARY_KEYS = (
    "public_spec_only",
    "private_hidden_reference_or_known_bad_read",
    "raw_trace_read",
    "legacy_retrieve_memory_calls",
    "runtime_memory_injection_count",
    "agent_context_render_calls",
    "agent_runs",
    "provider_calls_made",
    "evaluator_calls_made",
    "added_model_cost_usd",
    "network_access_authorized",
    "library_offline_and_local_files_only_enforced",
    "os_level_network_block_verified",
    "frozen_index_or_marker_mutated",
    "d106_unfrozen_index_mutated",
    "score_policy_or_threshold_mutated",
)
GATE_AUTHORITY_KEYS = (
    "exact_candidate_user_approval_received",
    "local_scoring_diagnostic_authorized",
    "local_scoring_diagnostic_executed",
    "retrieval_probe_authorized",
    "retrieval_probe_executed",
    "retrieval_ready",
    "retrieval_experiment_authorized",
    "runtime_memory_injection_count",
    "raw_trace_ready",
    "four_condition_retrieval_ready",
    "score_policy_correction_authorized",
    "core_campaign_unlocked",
    "analysis_ready",
    "memory_effect_established",
    "negative_transfer_established",
    "provider_calls_made",
    "evaluator_calls_made",
    "added_model_cost_usd",
)
PROBE_RESULT_KEYS = (
    "probe_id",
    "task_id",
    "phase",
    "query_bytes",
    "query_sha256",
    "query_phase_sha256",
    "hypothesis_kind",
    "hypothesized_group_id",
    "hypothesis_is_acceptance_criterion",
    "observed_top_memory_id",
    "observed_top_group_id",
    "hypothesis_agrees_with_top_group",
    "candidates",
    "diagnostic_threshold_passing_memory_ids",
    "diagnostic_no_match",
    "runtime_selection_executed",
    "memory_text_returned",
)
CANDIDATE_SCORE_KEYS = (
    "memory_id",
    "semantic_group_id",
    "failure_class",
    "entry_phase",
    "semantic_raw_dot",
    "components",
    "weighted_components",
    "final_score",
    "threshold",
    "threshold_comparator",
    "diagnostic_threshold_pass",
    "rank",
)
COMPONENT_KEYS = ("semantic", "failure_class", "phase", "language", "validation")

D114_RECEIPT_ROOT_KEYS = RECEIPT_ROOT_KEYS
D114_RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "approval_recorded_at",
    "correction_claimed_at",
    "approval_action_id",
    "approval_reference",
    "approval_reference_mode",
    "approval_statement_code",
    "d113_source_gate",
    "d113_candidate",
    "authorized_action_hash",
    "authorized_scope",
    "protected_pre_state",
    "implementation_pre_state",
    "claim_semantics",
    "self_attested",
    "approver_kind",
    "approver_label",
    "reviewer_identity_authenticated",
    "cryptographic_signature_verified",
    "execution_result_present",
)
D114_RECEIPT_CLAIM_KEYS = (
    "exclusive_create_and_fsync_required",
    "repository_local_one_use_consumption_marker",
    "global_one_use_or_cross_clone_exclusion_proved",
    "arbitrary_writer_delete_recreate_exclusion_proved",
    "failure_or_hard_kill_remains_consumed",
    "automatic_retry_or_rollback_allowed",
    "completion_gate_required_for_success",
    "d112_or_frozen_authority_modified",
)
D114_GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_receipt",
    "d113_authorization",
    "validation_contract",
    "sealed_historical_validation",
    "current_input_validation",
    "protected_input_integrity",
    "implementation_integrity",
    "qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)


class ValidationMode(StrEnum):
    """The two intentionally distinct D-114 validation modes."""

    SEALED_HISTORICAL = "sealed-historical"
    CURRENT_INPUT = "current-input"


class D114CorrectionError(ContractError):
    """Raised when D-114 scope, historical evidence, or successor evidence drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D114CorrectionError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    try:
        return selected.resolve()
    except OSError as exc:
        raise D114CorrectionError("D-114 repository root cannot be resolved") from exc


def _is_linklike(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    junction = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & junction)


def _resolved(
    relative: str | Path,
    *,
    repository: Path,
    label: str,
    must_exist: bool = True,
) -> Path:
    candidate = repository / Path(relative)
    try:
        selected = candidate.resolve(strict=must_exist)
        selected.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D114CorrectionError(f"D-114 {label} escapes or is missing") from exc
    current = candidate
    while current != repository:
        _require(not _is_linklike(current), f"D-114 {label} cannot use a link or junction")
        current = current.parent
    return selected


def _read_stable(path: Path, *, label: str) -> bytes:
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise D114CorrectionError(f"D-114 {label} cannot be read") from exc
    _require(
        (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
        f"D-114 {label} changed while being read",
    )
    return content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D114CorrectionError(f"D-114 {label} is not valid UTF-8 JSON") from exc
    _require(isinstance(value, dict), f"D-114 {label} root must be an object")
    return value


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _parse_utc(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"D-114 {label} is not UTC")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise D114CorrectionError(f"D-114 {label} is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-114 {label} has no timezone")
    return parsed


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _require_exact_keys(value: Any, expected: Sequence[str], *, label: str) -> None:
    _require(isinstance(value, dict), f"D-114 {label} must be an object")
    actual = set(value)
    wanted = set(expected)
    _require(
        actual == wanted,
        f"D-114 {label} key set mismatch: missing={sorted(wanted - actual)}, "
        f"unknown={sorted(actual - wanted)}",
    )


def _validate_envelope(
    payload: Mapping[str, Any],
    *,
    root_keys: Sequence[str],
    body_keys: Sequence[str],
    id_field: str,
    id_prefix: str,
    label: str,
) -> Mapping[str, Any]:
    _require_exact_keys(payload, root_keys, label=f"{label} root")
    body = payload.get("semantic_body")
    _require_exact_keys(body, body_keys, label=f"{label} semantic body")
    body_hash = sha256_text(canonical_json(body))
    _require(payload.get("semantic_body_hash") == body_hash, f"D-114 {label} body hash mismatch")
    _require(payload.get(id_field) == id_prefix + body_hash.removeprefix("sha256:"),
             f"D-114 {label} identifier mismatch")
    return body


def _file_binding(relative: str | Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _load_bound_json(
    relative: str | Path,
    *,
    repository: Path,
    expected_bytes: int,
    expected_sha: str,
    label: str,
) -> tuple[dict[str, Any], bytes]:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    _require(
        len(content) == expected_bytes and sha256_bytes(content) == expected_sha,
        f"D-114 {label} exact file binding mismatch",
    )
    return _parse_json(content, label=label), content


def _load_bound_bytes(
    relative: str | Path,
    *,
    repository: Path,
    expected_bytes: int,
    expected_sha: str,
    label: str,
) -> bytes:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    _require(
        len(content) == expected_bytes and sha256_bytes(content) == expected_sha,
        f"D-114 {label} exact file binding mismatch",
    )
    return content


def _artifact_binding_from_content(
    relative: str | Path,
    *,
    repository: Path,
    content: bytes,
    payload: Mapping[str, Any],
    id_field: str,
    label: str,
) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "schema_version": payload["schema_version"],
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def _validate_d113_authorization(repository: Path) -> dict[str, Any]:
    _load_bound_bytes(
        DEFAULT_D113_PREFLIGHT_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D113_PREFLIGHT_BYTES,
        expected_sha=EXPECTED_D113_PREFLIGHT_FILE_SHA,
        label="D-113 preflight",
    )
    candidate, candidate_content = _load_bound_json(
        DEFAULT_D113_CANDIDATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D113_CANDIDATE_BYTES,
        expected_sha=EXPECTED_D113_CANDIDATE_FILE_SHA,
        label="D-113 authorization candidate",
    )
    candidate_body = _validate_envelope(
        candidate,
        root_keys=("schema_version", "candidate_id", "semantic_body_hash", "semantic_body"),
        body_keys=(
            "milestone",
            "evidence_kind",
            "recorded_at",
            "preflight",
            "candidate_status",
            "proposed_action",
            "proposed_action_hash",
            "protected_d112_paths",
            "approval_contract",
            "authority",
        ),
        id_field="candidate_id",
        id_prefix="d113validatorcandidate_",
        label="D-113 authorization candidate",
    )
    _require(
        candidate["candidate_id"] == EXPECTED_D113_CANDIDATE_ID
        and candidate["semantic_body_hash"] == EXPECTED_D113_CANDIDATE_BODY_SHA,
        "D-114 exact D-113 candidate identity mismatch",
    )
    action = candidate_body["proposed_action"]
    _require(
        candidate_body["proposed_action_hash"] == EXPECTED_D113_ACTION_HASH
        and sha256_text(canonical_json(action)) == EXPECTED_D113_ACTION_HASH,
        "D-114 D-113 authorized action hash mismatch",
    )
    _require(action["future_milestone"] == MILESTONE, "D-114 authorized milestone mismatch")
    _require(action["new_files_only"] is True, "D-114 new-files-only authority is missing")
    _require(
        action["correction_evidence_materializations"] == 1,
        "D-114 materialization count authority mismatch",
    )
    _require(
        action["closed_runtime_boundaries"]
        == {
            "score_weights_or_threshold_change_allowed": False,
            "ranking_policy_change_allowed": False,
            "memory_entry_change_allowed": False,
            "index_or_marker_change_allowed": False,
            "retrieval_execution_allowed": False,
            "runtime_memory_injection_allowed": False,
            "agent_run_allowed": False,
            "model_load_or_encode_allowed": False,
            "provider_call_allowed": False,
            "evaluator_call_allowed": False,
            "network_access_allowed": False,
            "core_campaign_allowed": False,
            "analysis_campaign_allowed": False,
        },
        "D-114 closed runtime boundaries drifted",
    )

    source_gate, source_gate_content = _load_bound_json(
        DEFAULT_D113_SOURCE_GATE_PATH,
        repository=repository,
        expected_bytes=EXPECTED_D113_SOURCE_GATE_BYTES,
        expected_sha=EXPECTED_D113_SOURCE_GATE_FILE_SHA,
        label="D-113 source gate",
    )
    source_body = _validate_envelope(
        source_gate,
        root_keys=GATE_ROOT_KEYS,
        body_keys=(
            "milestone",
            "evidence_kind",
            "recorded_at",
            "preflight",
            "candidate",
            "implementation_files",
            "qualification",
            "authority",
            "next_gate",
        ),
        id_field="gate_id",
        id_prefix="d113_",
        label="D-113 source gate",
    )
    _require(
        source_gate["gate_id"] == EXPECTED_D113_SOURCE_GATE_ID
        and source_gate["semantic_body_hash"] == EXPECTED_D113_SOURCE_GATE_BODY_SHA,
        "D-114 exact D-113 source gate identity mismatch",
    )
    _require(
        source_body["candidate"]
        == {
            "path": DEFAULT_D113_CANDIDATE_PATH.as_posix(),
            "file_bytes": EXPECTED_D113_CANDIDATE_BYTES,
            "file_sha256": EXPECTED_D113_CANDIDATE_FILE_SHA,
            "candidate_id": EXPECTED_D113_CANDIDATE_ID,
            "semantic_body_hash": EXPECTED_D113_CANDIDATE_BODY_SHA,
        },
        "D-114 D-113 source gate candidate binding mismatch",
    )
    return {
        "candidate": candidate,
        "candidate_body": candidate_body,
        "source_gate": source_gate,
        "action": action,
        "candidate_binding": _artifact_binding_from_content(
            DEFAULT_D113_CANDIDATE_PATH,
            repository=repository,
            content=candidate_content,
            payload=candidate,
            id_field="candidate_id",
            label="D-113 authorization candidate",
        ),
        "source_gate_binding": _artifact_binding_from_content(
            DEFAULT_D113_SOURCE_GATE_PATH,
            repository=repository,
            content=source_gate_content,
            payload=source_gate,
            id_field="gate_id",
            label="D-113 source gate",
        ),
    }


def _validate_d112_receipt_structure(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    body = _validate_envelope(
        payload,
        root_keys=RECEIPT_ROOT_KEYS,
        body_keys=RECEIPT_BODY_KEYS,
        id_field="receipt_id",
        id_prefix="d112probereceipt_",
        label="D-112 receipt",
    )
    _require_exact_keys(
        body["claim_semantics"], RECEIPT_CLAIM_KEYS, label="D-112 receipt claim semantics"
    )
    _require_exact_keys(
        body["pre_execution_input"],
        ("schema_version", "fingerprint", "state"),
        label="D-112 receipt pre-execution input",
    )
    return body


def _validate_d112_gate_structure(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    body = _validate_envelope(
        payload,
        root_keys=GATE_ROOT_KEYS,
        body_keys=GATE_BODY_KEYS,
        id_field="gate_id",
        id_prefix="d112_",
        label="D-112 gate",
    )
    _require_exact_keys(
        body["probe_receipt"],
        ("path", "file_bytes", "file_sha256", "schema_version", "receipt_id", "semantic_body_hash"),
        label="D-112 gate receipt binding",
    )
    _require_exact_keys(
        body["input_integrity"],
        ("pre_execution", "post_execution", "fingerprints_equal"),
        label="D-112 gate input integrity",
    )
    for position in ("pre_execution", "post_execution"):
        _require_exact_keys(
            body["input_integrity"][position],
            ("schema_version", "fingerprint", "state"),
            label=f"D-112 gate {position} input",
        )
    _require_exact_keys(
        body["qualification"], GATE_QUALIFICATION_KEYS, label="D-112 gate qualification"
    )
    _require_exact_keys(
        body["evidence_boundary"],
        GATE_EVIDENCE_BOUNDARY_KEYS,
        label="D-112 gate evidence boundary",
    )
    _require_exact_keys(body["authority"], GATE_AUTHORITY_KEYS, label="D-112 gate authority")
    scoring = body["diagnostic_scoring"]
    _require_exact_keys(
        scoring,
        (
            "scoring_contract",
            "probe_results",
            "score_row_count",
            "all_diagnostic_no_match",
            "moto_phase_control_score_deltas",
            "moto_phase_control_expected_delta",
            "runtime_selection_executed",
            "memory_text_returned",
        ),
        label="D-112 diagnostic scoring",
    )
    probes = scoring["probe_results"]
    _require(isinstance(probes, list) and len(probes) == 3, "D-114 D-112 probe count mismatch")
    for probe in probes:
        _require_exact_keys(probe, PROBE_RESULT_KEYS, label="D-112 diagnostic probe")
        candidates = probe["candidates"]
        _require(
            isinstance(candidates, list) and len(candidates) == 3,
            "D-114 D-112 candidate score count mismatch",
        )
        for candidate in candidates:
            _require_exact_keys(candidate, CANDIDATE_SCORE_KEYS, label="D-112 candidate score")
            _require_exact_keys(
                candidate["components"], COMPONENT_KEYS, label="D-112 score components"
            )
            _require_exact_keys(
                candidate["weighted_components"],
                COMPONENT_KEYS,
                label="D-112 weighted score components",
            )
    vectors = body["query_vectors"]
    _require(isinstance(vectors, list) and len(vectors) == 3, "D-114 query vector count mismatch")
    for descriptor in vectors:
        _require_exact_keys(
            descriptor,
            ("probe_id", "shape", "dtype", "l2_norm", "float32_bytes", "float32_sha256", "vector"),
            label="D-112 query vector descriptor",
        )
    return body


def _receipt_binding_for_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    content = _pretty_json(payload)
    return {
        "path": DEFAULT_D112_RECEIPT_PATH.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "schema_version": payload["schema_version"],
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def _validate_d112_chronology(
    receipt_body: Mapping[str, Any], gate_body: Mapping[str, Any]
) -> None:
    approval = _parse_utc(receipt_body["approval_recorded_at"], label="D-112 approval timestamp")
    execution = _parse_utc(receipt_body["execution_claimed_at"], label="D-112 execution timestamp")
    completion = _parse_utc(gate_body["recorded_at"], label="D-112 completion timestamp")
    _require(approval <= execution, "D-114 chronology violation: approval occurs after execution")
    _require(
        execution <= completion,
        "D-114 chronology violation: execution occurs after completion",
    )


def _counter_cosine(left: str, right: str) -> float:
    first = Counter(_TOKEN_PATTERN.findall(left.lower()))
    second = Counter(_TOKEN_PATTERN.findall(right.lower()))
    if not first or not second:
        return 0.0
    numerator = sum(first[token] * second[token] for token in first.keys() & second.keys())
    left_norm = math.sqrt(sum(value * value for value in first.values()))
    right_norm = math.sqrt(sum(value * value for value in second.values()))
    return numerator / (left_norm * right_norm) if numerator else 0.0


def _validate_vector(values: Any, *, label: str) -> tuple[list[float], float]:
    _require(isinstance(values, list), f"D-114 {label} must be a list")
    _require(
        all(type(value) in (int, float) for value in values),
        f"D-114 {label} contains a non-numeric JSON value",
    )
    vector = [float(value) for value in values]
    _require(
        len(vector) == VECTOR_DIMENSION and all(math.isfinite(value) for value in vector),
        f"D-114 {label} shape or finiteness mismatch",
    )
    norm = math.sqrt(sum(value * value for value in vector))
    _require(abs(norm - 1.0) <= 1e-5, f"D-114 {label} is not normalized")
    return vector, norm


def _load_portable_queries(
    *, repository: Path, gate_body: Mapping[str, Any]
) -> list[dict[str, Any]]:
    pre_input = gate_body["input_integrity"]["pre_execution"]
    public_probes = pre_input["state"]["public_probes"]
    _require(
        isinstance(public_probes, list) and len(public_probes) == 3,
        "D-114 sealed public probe metadata is invalid",
    )
    task_cache: dict[str, tuple[Mapping[str, Any], bytes]] = {}
    rows: list[dict[str, Any]] = []
    for probe in public_probes:
        task_id = probe["task_id"]
        _require(task_id in PUBLIC_TASK_SPECS, f"D-114 unknown public task: {task_id}")
        spec = PUBLIC_TASK_SPECS[task_id]
        if task_id not in task_cache:
            content = _load_bound_bytes(
                spec["path"],
                repository=repository,
                expected_bytes=spec["file_bytes"],
                expected_sha=spec["file_sha256"],
                label=f"public task {task_id}",
            )
            try:
                task = yaml.safe_load(content.decode("utf-8"))
            except (UnicodeDecodeError, yaml.YAMLError) as exc:
                raise D114CorrectionError(f"D-114 public task is invalid: {task_id}") from exc
            _require(isinstance(task, dict), f"D-114 public task is not an object: {task_id}")
            task_cache[task_id] = (task, content)
        task, content = task_cache[task_id]
        issue = task.get("issue")
        tags = task.get("tags")
        _require(isinstance(issue, dict) and isinstance(tags, list),
                 f"D-114 public query fields are invalid: {task_id}")
        title = issue.get("title")
        description = issue.get("description")
        _require(isinstance(title, str) and isinstance(description, str),
                 f"D-114 public issue fields are invalid: {task_id}")
        _require(all(isinstance(tag, str) for tag in tags),
                 f"D-114 public tags are invalid: {task_id}")
        query = title + "\n" + description + "\n" + " ".join(tags)
        phase = probe["phase"]
        _require(
            len(content) == probe["public_task_file_bytes"]
            and sha256_bytes(content) == probe["public_task_file_sha256"],
            f"D-114 D-112 public task binding mismatch: {task_id}",
        )
        _require(
            len(query.encode("utf-8")) == probe["query_bytes"]
            and sha256_text(query) == probe["query_sha256"]
            and sha256_text(canonical_json({"query": query, "phase": phase}))
            == probe["query_phase_sha256"],
            f"D-114 D-112 public query identity mismatch: {probe['probe_id']}",
        )
        rows.append(dict(probe) | {"query": query})
    return rows


def _load_gate_query_vectors(gate_body: Mapping[str, Any]) -> list[list[float]]:
    descriptors = gate_body["query_vectors"]
    vectors: list[list[float]] = []
    for descriptor in descriptors:
        vector, norm = _validate_vector(
            descriptor["vector"], label=f"query vector {descriptor['probe_id']}"
        )
        packed = b"".join(struct.pack("<f", value) for value in vector)
        _require(
            descriptor["shape"] == [VECTOR_DIMENSION]
            and descriptor["dtype"] == VECTOR_DTYPE
            and descriptor["float32_bytes"] == len(packed) == VECTOR_DIMENSION * 4
            and descriptor["float32_sha256"] == sha256_bytes(packed)
            and descriptor["l2_norm"] == norm,
            f"D-114 query vector descriptor mismatch: {descriptor['probe_id']}",
        )
        vectors.append(vector)
    _require(
        vectors[0] == vectors[2]
        and descriptors[0]["float32_sha256"] == descriptors[2]["float32_sha256"],
        "D-114 identical Moto query vectors differ",
    )
    return vectors


def _scoring_contract() -> dict[str, Any]:
    return {
        "query_text": "public-title-newline-description-newline-space-joined-tags",
        "semantic_component": "max-zero-normalized-query-vector-dot-frozen-entry-vector",
        "failure_class_tokenizer_regex": "[a-z0-9_]+",
        "failure_class_component": "counter-cosine-public-query-vs-entry-failure-class",
        "phase_component": "float-entry-phase-equals-probe-phase",
        "language_component": "float-python-in-entry-applicable-languages",
        "validation_component": "min-one-entry-validation-count-divided-by-three",
        "score_weights": dict(SCORE_WEIGHTS),
        "selective_threshold": SELECTIVE_THRESHOLD,
        "selective_comparator": "greater-than-or-equal",
        "rank_order": "descending-score-then-ascending-memory-id",
        "scoring_policy_changed": False,
    }


def _replay_diagnostic_scores(
    *,
    queries: Sequence[Mapping[str, Any]],
    query_vectors: Sequence[Sequence[float]],
    index: Mapping[str, Any],
) -> dict[str, Any]:
    entries = index.get("entries")
    embeddings = index.get("embeddings")
    provenance_rows = index.get("group_provenance")
    _require(isinstance(entries, list), "D-114 frozen index entries are invalid")
    _require(isinstance(embeddings, dict), "D-114 frozen index embeddings are invalid")
    _require(isinstance(provenance_rows, list), "D-114 frozen index provenance is invalid")
    memory_ids = [entry.get("memory_id") for entry in entries if isinstance(entry, dict)]
    _require(memory_ids == list(EXPECTED_MEMORY_IDS), "D-114 frozen memory entry order drifted")
    _require(set(embeddings) == set(EXPECTED_MEMORY_IDS), "D-114 embedding key set drifted")
    provenance: dict[str, str] = {}
    for row in provenance_rows:
        _require(isinstance(row, dict), "D-114 provenance row is invalid")
        memory_id = row.get("memory_id")
        group_id = row.get("semantic_group_id")
        _require(
            memory_id in EXPECTED_MEMORY_IDS and isinstance(group_id, str),
            "D-114 provenance identity is invalid",
        )
        _require(memory_id not in provenance, "D-114 duplicate provenance memory ID")
        provenance[memory_id] = group_id
    _require(set(provenance) == set(EXPECTED_MEMORY_IDS), "D-114 provenance coverage drifted")

    entry_vectors = {
        memory_id: _validate_vector(embeddings[memory_id], label=f"entry vector {memory_id}")[0]
        for memory_id in EXPECTED_MEMORY_IDS
    }
    probe_results: list[dict[str, Any]] = []
    for query_vector, query in zip(query_vectors, queries, strict=True):
        candidates: list[dict[str, Any]] = []
        for entry in entries:
            memory_id = entry["memory_id"]
            pattern = entry["failure_pattern"]
            semantic_raw = sum(
                left * right
                for left, right in zip(query_vector, entry_vectors[memory_id], strict=True)
            )
            components = {
                "semantic": max(0.0, semantic_raw),
                "failure_class": _counter_cosine(query["query"], pattern["failure_class"]),
                "phase": float(pattern["phase"] == query["phase"]),
                "language": float("python" in entry["applicable_languages"]),
                "validation": min(1.0, entry["validation_count"] / 3),
            }
            weighted = {
                key: SCORE_WEIGHTS[key] * components[key] for key in SCORE_WEIGHTS
            }
            final_score = sum(weighted[key] for key in SCORE_WEIGHTS)
            candidates.append(
                {
                    "memory_id": memory_id,
                    "semantic_group_id": provenance[memory_id],
                    "failure_class": pattern["failure_class"],
                    "entry_phase": pattern["phase"],
                    "semantic_raw_dot": semantic_raw,
                    "components": components,
                    "weighted_components": weighted,
                    "final_score": final_score,
                    "threshold": SELECTIVE_THRESHOLD,
                    "threshold_comparator": "greater-than-or-equal",
                    "diagnostic_threshold_pass": final_score >= SELECTIVE_THRESHOLD,
                }
            )
        candidates.sort(key=lambda row: (-row["final_score"], row["memory_id"]))
        for rank, candidate in enumerate(candidates, start=1):
            candidate["rank"] = rank
        passing = [row["memory_id"] for row in candidates if row["diagnostic_threshold_pass"]]
        probe_results.append(
            {
                "probe_id": query["probe_id"],
                "task_id": query["task_id"],
                "phase": query["phase"],
                "query_bytes": query["query_bytes"],
                "query_sha256": query["query_sha256"],
                "query_phase_sha256": query["query_phase_sha256"],
                "hypothesis_kind": query["hypothesis_kind"],
                "hypothesized_group_id": query["hypothesized_group_id"],
                "hypothesis_is_acceptance_criterion": False,
                "observed_top_memory_id": candidates[0]["memory_id"],
                "observed_top_group_id": candidates[0]["semantic_group_id"],
                "hypothesis_agrees_with_top_group": (
                    query["hypothesized_group_id"] is not None
                    and query["hypothesized_group_id"] == candidates[0]["semantic_group_id"]
                ),
                "candidates": candidates,
                "diagnostic_threshold_passing_memory_ids": passing,
                "diagnostic_no_match": not passing,
                "runtime_selection_executed": False,
                "memory_text_returned": False,
            }
        )
    implement = {row["memory_id"]: row for row in probe_results[0]["candidates"]}
    reproduce = {row["memory_id"]: row for row in probe_results[2]["candidates"]}
    deltas = {
        memory_id: implement[memory_id]["final_score"] - reproduce[memory_id]["final_score"]
        for memory_id in EXPECTED_MEMORY_IDS
    }
    _require(
        all(math.isclose(value, 0.15, rel_tol=0.0, abs_tol=1e-12) for value in deltas.values()),
        "D-114 Moto phase-control delta mismatch",
    )
    return {
        "scoring_contract": _scoring_contract(),
        "probe_results": probe_results,
        "score_row_count": 9,
        "all_diagnostic_no_match": all(row["diagnostic_no_match"] for row in probe_results),
        "moto_phase_control_score_deltas": deltas,
        "moto_phase_control_expected_delta": 0.15,
        "runtime_selection_executed": False,
        "memory_text_returned": False,
    }


def _portable_score_replay(
    *, repository: Path, gate_body: Mapping[str, Any]
) -> dict[str, Any]:
    index, _ = _load_bound_json(
        DEFAULT_D110_INDEX_PATH,
        repository=repository,
        expected_bytes=55_687,
        expected_sha="sha256:c0d2ec424e6cc10d64cdebd5ae493e0546fdfa08d09eb5f3269557b46025c6d0",
        label="portable D-110 frozen index",
    )
    _load_bound_bytes(
        DEFAULT_D110_MARKER_PATH,
        repository=repository,
        expected_bytes=72,
        expected_sha="sha256:cdfe40b734135a30f66e34ff24469940063a7231a1fe0783420ee2ff816d9561",
        label="portable D-110 frozen marker",
    )
    _require(index.get("frozen") is True, "D-114 portable index is not frozen")
    queries = _load_portable_queries(repository=repository, gate_body=gate_body)
    query_vectors = _load_gate_query_vectors(gate_body)
    _require(
        [row["probe_id"] for row in queries]
        == [row["probe_id"] for row in gate_body["query_vectors"]],
        "D-114 query and vector order mismatch",
    )
    replayed = _replay_diagnostic_scores(
        queries=queries, query_vectors=query_vectors, index=index
    )
    _require(
        replayed == gate_body["diagnostic_scoring"],
        "D-114 portable score replay differs from sealed D-112 scoring",
    )
    return replayed


CurrentInputLoader = Callable[[Path], Mapping[str, Any] | tuple[Any, ...]]


def _default_current_input_loader(repository: Path) -> tuple[Any, ...]:
    # Deliberately lazy: sealed-historical mode never imports D-112 or its
    # snapshot/dependency stack.
    from patchloop.memory import d112_retrieval_readiness_probe as d112

    return d112._input_state(repository)


def validate_d112_history(
    *,
    repository: str | Path | None = None,
    mode: ValidationMode | str = ValidationMode.SEALED_HISTORICAL,
    current_input_loader: CurrentInputLoader | None = None,
    _receipt_payload: Mapping[str, Any] | None = None,
    _gate_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Strictly validate the exact D-112 pair in one explicit mode.

    Payload overrides exist only to exercise fail-closed tamper tests.  The
    expected payload remains the pinned checked-in D-112 pair.
    """

    try:
        selected_mode = ValidationMode(mode)
    except (TypeError, ValueError) as exc:
        raise D114CorrectionError("D-114 validation mode is invalid") from exc
    repo = _repo_root(repository)
    reference_receipt, _ = _load_bound_json(
        DEFAULT_D112_RECEIPT_PATH,
        repository=repo,
        expected_bytes=EXPECTED_D112_RECEIPT_BYTES,
        expected_sha=EXPECTED_D112_RECEIPT_FILE_SHA,
        label="pinned D-112 receipt",
    )
    reference_gate, _ = _load_bound_json(
        DEFAULT_D112_GATE_PATH,
        repository=repo,
        expected_bytes=EXPECTED_D112_GATE_BYTES,
        expected_sha=EXPECTED_D112_GATE_FILE_SHA,
        label="pinned D-112 gate",
    )
    receipt = dict(_receipt_payload) if _receipt_payload is not None else reference_receipt
    gate = dict(_gate_payload) if _gate_payload is not None else reference_gate
    receipt_body = _validate_d112_receipt_structure(receipt)
    gate_body = _validate_d112_gate_structure(gate)
    _validate_d112_chronology(receipt_body, gate_body)
    _require(
        receipt_body["approval_recorded_at"] == EXPECTED_D112_APPROVAL_AT
        and receipt_body["execution_claimed_at"] == EXPECTED_D112_EXECUTION_AT
        and gate_body["recorded_at"] == EXPECTED_D112_COMPLETION_AT,
        "D-114 D-112 exact chronology values mismatch",
    )
    _require(
        receipt == reference_receipt,
        "D-114 D-112 receipt differs from the full expected historical payload",
    )
    _require(
        gate_body["probe_receipt"] == _receipt_binding_for_payload(receipt),
        "D-114 D-112 receipt and gate paired binding mismatch",
    )
    _require(
        gate == reference_gate,
        "D-114 D-112 gate differs from the full expected historical payload",
    )
    _require(
        receipt["receipt_id"] == EXPECTED_D112_RECEIPT_ID
        and receipt["semantic_body_hash"] == EXPECTED_D112_RECEIPT_BODY_SHA
        and gate["gate_id"] == EXPECTED_D112_GATE_ID
        and gate["semantic_body_hash"] == EXPECTED_D112_GATE_BODY_SHA,
        "D-114 pinned D-112 artifact identities mismatch",
    )
    pre_input = receipt_body["pre_execution_input"]
    _require(
        pre_input == gate_body["input_integrity"]["pre_execution"]
        == gate_body["input_integrity"]["post_execution"],
        "D-114 D-112 pre/post input payload mismatch",
    )
    _require(
        pre_input["fingerprint"] == EXPECTED_D112_INPUT_FINGERPRINT
        and pre_input["fingerprint"] == sha256_text(canonical_json(pre_input["state"])),
        "D-114 D-112 input fingerprint mismatch",
    )
    replayed = _portable_score_replay(repository=repo, gate_body=gate_body)

    current_checked = False
    default_current_loader_used = False
    if selected_mode is ValidationMode.CURRENT_INPUT:
        default_current_loader_used = current_input_loader is None
        loader = current_input_loader or _default_current_input_loader
        loaded = loader(repo)
        current = loaded[0] if isinstance(loaded, tuple) else loaded
        _require(isinstance(current, Mapping), "D-114 current-input loader result is invalid")
        _require(
            dict(current) == pre_input,
            "D-114 current D-112 input differs from the sealed historical input",
        )
        current_checked = True

    custom_current_loader_used = current_checked and not default_current_loader_used
    zero_or_unknown = None if custom_current_loader_used else 0
    false_or_unknown = None if custom_current_loader_used else False

    return {
        "validation_mode": selected_mode.value,
        "current_input_loader_kind": (
            "d112-default"
            if default_current_loader_used
            else "injected-not-audited"
            if custom_current_loader_used
            else "not-used"
        ),
        "sealed_historical_validation_passed": True,
        "current_input_validation_executed": current_checked,
        "current_input_validation_passed": current_checked,
        "d112_receipt_expected_payload_full_equality": True,
        "d112_gate_expected_payload_full_equality": True,
        "approval_execution_completion_chronology_valid": True,
        "receipt_gate_pair_binding_valid": True,
        "portable_score_replay_exact": True,
        "score_row_count": replayed["score_row_count"],
        "all_diagnostic_no_match": replayed["all_diagnostic_no_match"],
        "stored_vector_integrity_validated": True,
        "query_embedding_semantic_fidelity_recomputed": false_or_unknown,
        "model_reencoding_performed": false_or_unknown,
        "snapshot_rehydration_performed": (
            True if default_current_loader_used else None if custom_current_loader_used else False
        ),
        "installed_embedding_dependency_check_performed": (
            True if default_current_loader_used else None if custom_current_loader_used else False
        ),
        "retrieval_calls": zero_or_unknown,
        "runtime_memory_injection_count": zero_or_unknown,
        "agent_runs": zero_or_unknown,
        "provider_calls_made": zero_or_unknown,
        "evaluator_calls_made": zero_or_unknown,
        "model_load_count": zero_or_unknown,
        "model_encode_count": zero_or_unknown,
        "network_claim": (
            "custom-loader-not-audited"
            if custom_current_loader_used
            else "source-path-and-self-attestation-only"
        ),
        "os_socket_block_verified": False,
    }


def _protected_state(repository: Path) -> dict[str, Any]:
    bindings: list[dict[str, Any]] = []
    for spec in PROTECTED_FILE_SPECS:
        binding = _file_binding(spec["path"], repository=repository, label="protected input")
        _require(
            binding["file_bytes"] == spec["file_bytes"]
            and binding["file_sha256"] == spec["file_sha256"],
            f"D-114 protected input drifted: {spec['path']}",
        )
        bindings.append(binding)
    return {
        "files": bindings,
        "fingerprint": sha256_text(canonical_json(bindings)),
    }


def _implementation_bindings(repository: Path) -> list[dict[str, Any]]:
    return [
        _file_binding(path, repository=repository, label="D-114 implementation")
        for path in D114_IMPLEMENTATION_PATHS
    ]


def _implementation_state(repository: Path) -> dict[str, Any]:
    files = _implementation_bindings(repository)
    return {
        "files": files,
        "fingerprint": sha256_text(canonical_json(files)),
    }


def build_d114_approval_receipt(
    *,
    correction_claimed_at: str,
    authorization: Mapping[str, Any],
    protected_pre_state: Mapping[str, Any],
    implementation_pre_state: Mapping[str, Any],
) -> dict[str, Any]:
    _parse_utc(correction_claimed_at, label="D-114 correction claim timestamp")
    _require(
        _parse_utc(APPROVAL_RECORDED_AT, label="D-114 approval timestamp")
        <= _parse_utc(correction_claimed_at, label="D-114 correction claim timestamp"),
        "D-114 approval occurs after correction claim",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d113-approval-and-repository-local-one-use-claim",
        "approval_recorded_at": APPROVAL_RECORDED_AT,
        "correction_claimed_at": correction_claimed_at,
        "approval_action_id": APPROVAL_ACTION_ID,
        "approval_reference": APPROVAL_REFERENCE,
        "approval_reference_mode": "self-attested-exact-user-message",
        "approval_statement_code": APPROVAL_STATEMENT_CODE,
        "d113_source_gate": dict(authorization["source_gate_binding"]),
        "d113_candidate": dict(authorization["candidate_binding"]),
        "authorized_action_hash": EXPECTED_D113_ACTION_HASH,
        "authorized_scope": dict(authorization["action"]),
        "protected_pre_state": dict(protected_pre_state),
        "implementation_pre_state": dict(implementation_pre_state),
        "claim_semantics": {
            "exclusive_create_and_fsync_required": True,
            "repository_local_one_use_consumption_marker": True,
            "global_one_use_or_cross_clone_exclusion_proved": False,
            "arbitrary_writer_delete_recreate_exclusion_proved": False,
            "failure_or_hard_kill_remains_consumed": True,
            "automatic_retry_or_rollback_allowed": False,
            "completion_gate_required_for_success": True,
            "d112_or_frozen_authority_modified": False,
        },
        "self_attested": True,
        "approver_kind": "human",
        "approver_label": "project-owner",
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
        "execution_result_present": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": APPROVAL_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d114approval_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _d114_receipt_binding(
    payload: Mapping[str, Any], *, actual_content: bytes | None = None
) -> dict[str, Any]:
    content = actual_content if actual_content is not None else _pretty_json(payload)
    return {
        "path": DEFAULT_APPROVAL_RECEIPT_PATH.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "schema_version": payload["schema_version"],
        "receipt_id": payload["receipt_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
    }


def build_d114_completion_gate(
    *,
    completed_at: str,
    approval_receipt: Mapping[str, Any],
    authorization: Mapping[str, Any],
    sealed_validation: Mapping[str, Any],
    protected_pre_state: Mapping[str, Any],
    protected_post_state: Mapping[str, Any],
    implementation_pre_state: Mapping[str, Any],
    implementation_post_state: Mapping[str, Any],
) -> dict[str, Any]:
    completion = _parse_utc(completed_at, label="D-114 completion timestamp")
    claim = _parse_utc(
        approval_receipt["semantic_body"]["correction_claimed_at"],
        label="D-114 correction claim timestamp",
    )
    _require(claim <= completion, "D-114 correction claim occurs after completion")
    _require(
        protected_pre_state == protected_post_state,
        "D-114 protected D-112 or index input changed during correction",
    )
    _require(
        implementation_pre_state == implementation_post_state,
        "D-114 implementation changed after the repository-local claim",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "append-only-d112-successor-validator-correction-completion-gate",
        "recorded_at": completed_at,
        "approval_receipt": _d114_receipt_binding(approval_receipt),
        "d113_authorization": {
            "source_gate": dict(authorization["source_gate_binding"]),
            "candidate": dict(authorization["candidate_binding"]),
            "authorized_action_hash": EXPECTED_D113_ACTION_HASH,
        },
        "validation_contract": {
            "modes": [
                ValidationMode.SEALED_HISTORICAL.value,
                ValidationMode.CURRENT_INPUT.value,
            ],
            "sealed_historical_uses_pinned_d112_bytes": True,
            "sealed_historical_uses_checked_in_frozen_index": True,
            "sealed_historical_uses_gate_query_vectors": True,
            "sealed_historical_uses_exact_hash_public_specs": True,
            "sealed_historical_rehydrates_snapshot": False,
            "sealed_historical_checks_installed_embedding_versions": False,
            "current_input_is_opt_in_after_sealed_pass": True,
            "d112_original_validator_invoked": False,
        },
        "sealed_historical_validation": dict(sealed_validation),
        "current_input_validation": {
            "implemented": True,
            "executed_for_correction_evidence": False,
            "requires_explicit_mode": ValidationMode.CURRENT_INPUT.value,
            "requires_snapshot_and_installed_embedding_dependencies": True,
        },
        "protected_input_integrity": {
            "pre_execution": dict(protected_pre_state),
            "post_execution": dict(protected_post_state),
            "fingerprints_equal": True,
        },
        "implementation_integrity": {
            "pre_execution": dict(implementation_pre_state),
            "post_execution": dict(implementation_post_state),
            "fingerprints_equal": True,
        },
        "qualification": {
            "exact_d113_candidate_user_approval_bound": True,
            "repository_local_one_use_claim_consumed": True,
            "receipt_and_gate_exact_root_and_body_keys_enforced": True,
            "receipt_claim_keys_enforced": True,
            "receipt_full_expected_payload_equality_enforced": True,
            "rehashed_unknown_and_unchecked_fields_rejected": True,
            "paired_receipt_gate_rehash_rejected": True,
            "approval_execution_completion_chronology_enforced": True,
            "current_and_sealed_modes_separated": True,
            "portable_score_rows_recomputed_exactly": True,
            "score_row_count": 9,
            "d112_and_index_bytes_unchanged": True,
            "negative_tamper_probes_executed_during_materialization": False,
        },
        "evidence_boundary": {
            "public_spec_only": True,
            "private_hidden_reference_or_known_bad_read": False,
            "raw_trace_read": False,
            "snapshot_rehydration_performed": False,
            "installed_embedding_dependency_check_performed": False,
            "query_embedding_semantic_fidelity_recomputed": False,
            "model_load_count": 0,
            "model_encode_count": 0,
            "retrieval_calls": 0,
            "runtime_memory_injection_count": 0,
            "agent_runs": 0,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
            "network_access_authorized": False,
            "network_calls_made_self_attested": 0,
            "os_socket_block_verified": False,
            "global_one_use_or_cross_clone_exclusion_proved": False,
            "arbitrary_writer_delete_recreate_exclusion_proved": False,
            "human_reviewer_identity_authenticated": False,
            "cryptographic_signature_verified": False,
        },
        "authority": {
            "exact_candidate_user_approval_received": True,
            "append_only_successor_validator_implemented": True,
            "correction_evidence_materializations": 1,
            "original_d112_validator_modified": False,
            "original_d112_guarantees_changed": False,
            "d112_execution_replayed": False,
            "d112_one_use_capability_recreated": False,
            "score_policy_correction_authorized": False,
            "score_weights_or_threshold_changed": False,
            "ranking_policy_changed": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "agent_runs": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
        },
        "next_gate": "separate-offline-score-policy-decision-candidate",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": COMPLETION_GATE_SCHEMA_VERSION,
        "gate_id": f"d114_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _write_new_fsynced(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(path.parent), "D-114 output parent cannot be a link or junction")
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise D114CorrectionError(
            "D-114 repository-local one-use claim is already consumed"
        ) from exc
    except OSError as exc:
        raise D114CorrectionError("D-114 append-only evidence write failed") from exc
    committed = _read_stable(path, label="committed D-114 evidence")
    _require(committed == content, "D-114 committed evidence read-back mismatch")


def preflight_d114_correction(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Check exact authority and immutable inputs without consuming D-114."""

    repo = _repo_root(repository)
    authorization = _validate_d113_authorization(repo)
    receipt_path = _resolved(
        DEFAULT_APPROVAL_RECEIPT_PATH,
        repository=repo,
        label="D-114 approval receipt",
        must_exist=False,
    )
    gate_path = _resolved(
        DEFAULT_COMPLETION_GATE_PATH,
        repository=repo,
        label="D-114 completion gate",
        must_exist=False,
    )
    _require(not receipt_path.exists(), "D-114 repository-local one-use claim is already consumed")
    _require(not gate_path.exists(), "D-114 gate exists without a fresh repository-local claim")
    return {
        "authorization": authorization,
        "protected_pre_state": _protected_state(repo),
        "implementation_pre_state": _implementation_state(repo),
        "receipt_path": receipt_path,
        "gate_path": gate_path,
    }


def execute_d114_correction(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Materialize the exact D-113-authorized correction evidence once.

    The receipt is committed first.  Any later failure remains consumed; this
    function performs no retry, rollback, or overwrite.
    """

    repo = _repo_root(repository)
    preflight = preflight_d114_correction(repository=repo)
    authorization = preflight["authorization"]
    protected_pre = preflight["protected_pre_state"]
    implementation_pre = preflight["implementation_pre_state"]
    receipt = build_d114_approval_receipt(
        correction_claimed_at=_utc_now_text(),
        authorization=authorization,
        protected_pre_state=protected_pre,
        implementation_pre_state=implementation_pre,
    )
    receipt_content = _pretty_json(receipt)
    _write_new_fsynced(preflight["receipt_path"], receipt_content)

    sealed = validate_d112_history(
        repository=repo, mode=ValidationMode.SEALED_HISTORICAL
    )
    protected_post = _protected_state(repo)
    implementation_post = _implementation_state(repo)
    gate = build_d114_completion_gate(
        completed_at=_utc_now_text(),
        approval_receipt=receipt,
        authorization=authorization,
        sealed_validation=sealed,
        protected_pre_state=protected_pre,
        protected_post_state=protected_post,
        implementation_pre_state=implementation_pre,
        implementation_post_state=implementation_post,
    )
    _write_new_fsynced(preflight["gate_path"], _pretty_json(gate))
    return gate


def validate_d114_correction_evidence(
    *, repository: str | Path | None = None
) -> dict[str, Any]:
    """Read-only validation of the once-materialized D-114 receipt and gate."""

    repo = _repo_root(repository)
    authorization = _validate_d113_authorization(repo)
    receipt_content = _read_stable(
        _resolved(DEFAULT_APPROVAL_RECEIPT_PATH, repository=repo, label="D-114 receipt"),
        label="D-114 receipt",
    )
    gate_content = _read_stable(
        _resolved(DEFAULT_COMPLETION_GATE_PATH, repository=repo, label="D-114 gate"),
        label="D-114 gate",
    )
    receipt = _parse_json(receipt_content, label="D-114 receipt")
    gate = _parse_json(gate_content, label="D-114 gate")
    _require(
        receipt_content == _pretty_json(receipt),
        "D-114 receipt is not the exact canonical evidence bytes",
    )
    _require(
        gate_content == _pretty_json(gate),
        "D-114 gate is not the exact canonical evidence bytes",
    )
    receipt_body = _validate_envelope(
        receipt,
        root_keys=D114_RECEIPT_ROOT_KEYS,
        body_keys=D114_RECEIPT_BODY_KEYS,
        id_field="receipt_id",
        id_prefix="d114approval_",
        label="D-114 receipt",
    )
    _require_exact_keys(
        receipt_body["claim_semantics"],
        D114_RECEIPT_CLAIM_KEYS,
        label="D-114 receipt claim semantics",
    )
    gate_body = _validate_envelope(
        gate,
        root_keys=GATE_ROOT_KEYS,
        body_keys=D114_GATE_BODY_KEYS,
        id_field="gate_id",
        id_prefix="d114_",
        label="D-114 gate",
    )
    claim_at = _parse_utc(receipt_body["correction_claimed_at"], label="D-114 claim timestamp")
    completion_at = _parse_utc(gate_body["recorded_at"], label="D-114 completion timestamp")
    _require(
        _parse_utc(receipt_body["approval_recorded_at"], label="D-114 approval timestamp")
        <= claim_at
        <= completion_at,
        "D-114 approval, claim, completion chronology is invalid",
    )
    protected = _protected_state(repo)
    implementation = _implementation_state(repo)
    expected_receipt = build_d114_approval_receipt(
        correction_claimed_at=receipt_body["correction_claimed_at"],
        authorization=authorization,
        protected_pre_state=protected,
        implementation_pre_state=implementation,
    )
    _require(receipt == expected_receipt, "D-114 receipt full expected payload mismatch")
    _require(
        gate_body["approval_receipt"]
        == _d114_receipt_binding(receipt, actual_content=receipt_content),
        "D-114 receipt and completion gate binding mismatch",
    )
    sealed = validate_d112_history(
        repository=repo, mode=ValidationMode.SEALED_HISTORICAL
    )
    expected_gate = build_d114_completion_gate(
        completed_at=gate_body["recorded_at"],
        approval_receipt=receipt,
        authorization=authorization,
        sealed_validation=sealed,
        protected_pre_state=protected,
        protected_post_state=protected,
        implementation_pre_state=implementation,
        implementation_post_state=implementation,
    )
    _require(gate == expected_gate, "D-114 gate full expected payload mismatch")
    return {
        "receipt_id": receipt["receipt_id"],
        "receipt_semantic_body_hash": receipt["semantic_body_hash"],
        "receipt_file_bytes": len(receipt_content),
        "receipt_file_sha256": sha256_bytes(receipt_content),
        "gate_id": gate["gate_id"],
        "gate_semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_bytes": len(gate_content),
        "gate_file_sha256": sha256_bytes(gate_content),
        "sealed_historical_validation": sealed,
    }
