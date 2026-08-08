"""Build the D-109 exact index-freeze authorization candidate offline.

D-109 observes the current unfrozen runtime copy, binds it to the portable
D-106 index and the completed D-108 provider token-budget gate, and produces
an exact candidate that a user may later approve.  This module never mutates
the runtime index, creates a ``FROZEN`` marker, invokes retrieval, calls a
provider/evaluator, or starts a core experiment.
"""

from __future__ import annotations

import json
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.memory import d105_renderer_authorization as d105
from patchloop.memory import d106_locked_group_index as d106
from patchloop.memory import d107_portable_index_freeze_readiness as d107
from patchloop.memory import d108_provider_token_count_execution as d108
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-109"
RUNTIME_PREFLIGHT_SCHEMA_VERSION = "runtime-index-freeze-preflight-d109-v1"
CANDIDATE_SCHEMA_VERSION = "memory-index-freeze-authorization-candidate-d109-v1"
FREEZE_ACTION_SCHEMA_VERSION = "exact-group-index-freeze-action-d109-v1"
SOURCE_GATE_SCHEMA_VERSION = "index-freeze-authorization-source-gate-d109-v1"

PREFLIGHT_RECORDED_AT = "2026-08-06T12:00:00Z"
CANDIDATE_RECORDED_AT = "2026-08-06T12:05:00Z"
GATE_RECORDED_AT = "2026-08-06T12:10:00Z"

EXPECTED_D108_GATE_ID = (
    "d108_c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86"
)
EXPECTED_D108_BODY_SHA = (
    "sha256:c663c745d43fc31bdee5309825059827899872c13368d7e3709e8730ee0a0f86"
)
EXPECTED_D108_GATE_BYTES = 4_794
EXPECTED_D108_GATE_FILE_SHA = (
    "sha256:5f57e29caa3a3c940c280a69fbed3abe3d8daba4b4542e039355443df931d7bc"
)
EXPECTED_D107_PORTABLE_VALIDATION_ID = (
    "d107portable_8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785"
)
EXPECTED_D107_PORTABLE_VALIDATION_BODY_SHA = (
    "sha256:8fb06997dfd9aa7e07c116db8095b5397382356bcd1cfd71ab3ce6c8b4ad1785"
)
EXPECTED_D107_PORTABLE_VALIDATION_BYTES = 3_146
EXPECTED_D107_PORTABLE_VALIDATION_FILE_SHA = (
    "sha256:a6e71de1eea4a311d790e14a25dc9e507e1a2107176a7d0967ac074f9e50f259"
)
EXPECTED_INDEX_ID = d107.EXPECTED_D106_INDEX_ID
EXPECTED_INDEX_BYTES = d107.EXPECTED_D106_INDEX_BYTES
EXPECTED_INDEX_FILE_SHA = d107.EXPECTED_D106_INDEX_FILE_SHA
EXPECTED_INDEX_CONTENT_HASH = d107.EXPECTED_D106_INDEX_CONTENT_HASH
EXPECTED_EMBEDDING_REVISION = d106.MODEL_REVISION
EXPECTED_MEMORY_IDS = d107.EXPECTED_MEMORY_IDS
EXPECTED_GROUP_IDS = d107.EXPECTED_GROUP_IDS
EXPECTED_HELD_GROUP_IDS = tuple(d106.HELD_GROUP_IDS)

DEFAULT_RUNTIME_PREFLIGHT_PATH = Path(
    "reports/memory-development/d109-runtime-index-freeze-preflight.json"
)
DEFAULT_CANDIDATE_PATH = Path(
    "reports/memory-development/d109-index-freeze-authorization-candidate.json"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d109-index-freeze-authorization-source-gate.json"
)
DEFAULT_PORTABLE_INDEX_PATH = d107.DEFAULT_D106_INDEX_PATH
DEFAULT_RUNTIME_INDEX_PATH = (
    Path(".patchloop/memory/indexes") / EXPECTED_INDEX_ID / "index.json"
)

D109_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d109_index_freeze_authorization.py"),
    Path("scripts/build_d109_index_freeze_authorization_candidate.py"),
    Path("tests/test_d109_index_freeze_authorization.py"),
)

ALLOWED_EXISTING_JSON_MUTATIONS = (
    "/frozen: false -> true",
    "/frozen_at: absent -> approval-bound execution UTC timestamp",
    "/authority/index_freeze_authorized: false -> true",
    "/authority/memory_index_frozen: false -> true",
    "/content_hash: recompute after the four allowed semantic changes",
)


class D109AuthorizationError(ContractError):
    """Raised when the D-109 authorization candidate fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D109AuthorizationError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        return selected.resolve()
    except OSError as exc:
        raise D109AuthorizationError("D-109 repository root cannot be resolved") from exc


def _is_linklike(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse)


def _resolved(
    path: str | Path,
    *,
    repository: Path,
    label: str,
    must_exist: bool = True,
) -> Path:
    selected = Path(path)
    if not selected.is_absolute():
        selected = repository / selected
    try:
        resolved = selected.resolve(strict=must_exist)
        resolved.relative_to(repository)
    except (OSError, ValueError) as exc:
        raise D109AuthorizationError(f"D-109 {label} escapes the repository") from exc
    _require(not _is_linklike(selected), f"D-109 {label} cannot be a link or junction")
    return resolved


def _read_stable(path: Path, *, label: str) -> bytes:
    _require(not _is_linklike(path), f"D-109 {label} cannot be a link or junction")
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise D109AuthorizationError(f"D-109 {label} is unavailable") from exc
    _require(first == second, f"D-109 {label} changed while being read")
    return first


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D109AuthorizationError(f"D-109 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-109 {label} JSON root is invalid")
    return payload


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _file_binding(path: Path, *, repository: Path, label: str) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable(selected, label=label)
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _root_identity(
    payload: Mapping[str, Any],
    *,
    schema_version: str,
    id_field: str,
    id_prefix: str,
    label: str,
) -> None:
    _require(payload.get("schema_version") == schema_version, f"D-109 {label} schema drifted")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), f"D-109 {label} body is invalid")
    body_hash = sha256_text(canonical_json(body))
    _require(
        payload.get("semantic_body_hash") == body_hash
        and payload.get(id_field) == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-109 {label} identity drifted",
    )


def _load_exact_portable_inputs(repository: Path) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    d108_result = d108.validate_d108_completion_gate(repository=repository)
    _require(
        d108_result["gate_id"] == EXPECTED_D108_GATE_ID
        and d108_result["semantic_body_hash"] == EXPECTED_D108_BODY_SHA
        and d108_result["file_bytes"] == EXPECTED_D108_GATE_BYTES
        and d108_result["file_sha256"] == EXPECTED_D108_GATE_FILE_SHA
        and d108_result["provider_exact_budget_validated"] is True
        and d108_result["index_freeze_authorization_candidate_ready"] is True
        and d108_result["index_freeze_authorized"] is False,
        "D-109 exact D-108 completion gate drifted",
    )
    report_path = _resolved(
        d107.DEFAULT_PORTABLE_REPORT_PATH,
        repository=repository,
        label="D-107 portable validation report",
    )
    report_content = _read_stable(report_path, label="D-107 portable validation report")
    report = _parse_json(report_content, label="D-107 portable validation report")
    _require(
        len(report_content) == EXPECTED_D107_PORTABLE_VALIDATION_BYTES
        and sha256_bytes(report_content) == EXPECTED_D107_PORTABLE_VALIDATION_FILE_SHA
        and report.get("validation_id") == EXPECTED_D107_PORTABLE_VALIDATION_ID
        and report.get("semantic_body_hash") == EXPECTED_D107_PORTABLE_VALIDATION_BODY_SHA,
        "D-109 exact D-107 portable validation report drifted",
    )
    portable_path = _resolved(
        DEFAULT_PORTABLE_INDEX_PATH,
        repository=repository,
        label="portable unfrozen index",
    )
    portable_content = _read_stable(portable_path, label="portable unfrozen index")
    _require(
        len(portable_content) == EXPECTED_INDEX_BYTES
        and sha256_bytes(portable_content) == EXPECTED_INDEX_FILE_SHA,
        "D-109 portable index file identity drifted",
    )
    portable = _parse_json(portable_content, label="portable unfrozen index")
    _require(portable_content == _pretty_json(portable), "D-109 portable index is not canonical")
    validation = d106.validate_d106_group_index_payload(portable, repository=repository)
    _require(
        validation["index_id"] == EXPECTED_INDEX_ID
        and validation["content_hash"] == EXPECTED_INDEX_CONTENT_HASH
        and validation["entries"] == 3
        and validation["embeddings"] == 3
        and validation["frozen"] is False,
        "D-109 portable index semantic identity drifted",
    )
    return portable, portable_content, report


def _inspect_runtime_target_bytes(
    runtime_index_path: Path,
    expected_content: bytes,
    *,
    repository: Path,
) -> dict[str, Any]:
    selected = _resolved(
        runtime_index_path,
        repository=repository,
        label="runtime index target",
    )
    directory = selected.parent
    _require(not _is_linklike(directory), "D-109 runtime index directory is linked")
    try:
        names = sorted(item.name for item in directory.iterdir())
    except OSError as exc:
        raise D109AuthorizationError("D-109 runtime index directory is unavailable") from exc
    _require(
        names == ["index.json"],
        "D-109 runtime index directory must contain only index.json before freeze",
    )
    _require(not (directory / "FROZEN").exists(), "D-109 runtime index is already frozen")
    content = _read_stable(selected, label="runtime index target")
    _require(content == expected_content, "D-109 runtime index differs from the portable index")
    payload = _parse_json(content, label="runtime index target")
    authority = payload.get("authority")
    _require(isinstance(authority, dict), "D-109 runtime index authority is invalid")
    _require(
        payload.get("index_version") == EXPECTED_INDEX_ID
        and payload.get("content_hash") == EXPECTED_INDEX_CONTENT_HASH
        and payload.get("frozen") is False
        and authority.get("index_freeze_authorized") is False
        and authority.get("memory_index_frozen") is False
        and authority.get("retrieval_ready") is False
        and authority.get("retrieval_experiment_authorized") is False
        and authority.get("runtime_memory_injection_count") == 0
        and authority.get("core_campaign_unlocked") is False
        and authority.get("analysis_ready") is False,
        "D-109 runtime index authority or state drifted",
    )
    return {
        "target_path": selected.relative_to(repository).as_posix(),
        "directory_path": directory.relative_to(repository).as_posix(),
        "directory_file_names": names,
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
        "content_hash": payload["content_hash"],
        "index_id": payload["index_version"],
        "frozen": False,
        "frozen_marker_present": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "byte_identical_to_portable_index": True,
    }


def observe_d109_runtime_preflight(
    *,
    repository: str | Path | None = None,
    runtime_index_path: str | Path = DEFAULT_RUNTIME_INDEX_PATH,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    portable, portable_content, _ = _load_exact_portable_inputs(repo)
    runtime = _inspect_runtime_target_bytes(
        Path(runtime_index_path),
        portable_content,
        repository=repo,
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "runtime-index-unfrozen-precondition-observation",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "portable_index": {
            "path": DEFAULT_PORTABLE_INDEX_PATH.as_posix(),
            "index_id": EXPECTED_INDEX_ID,
            "file_bytes": len(portable_content),
            "file_sha256": sha256_bytes(portable_content),
            "content_hash": portable["content_hash"],
        },
        "runtime_target": runtime,
        "semantic_contents": {
            "entry_count": len(portable["entries"]),
            "embedding_count": len(portable["embeddings"]),
            "memory_ids": [row["memory_id"] for row in portable["entries"]],
            "semantic_group_ids": [
                row["semantic_group_id"] for row in portable["group_provenance"]
            ],
            "held_group_ids": portable["held_group_ids"],
            "embedding_model": portable["embedding"]["model"],
            "embedding_revision": portable["embedding"]["revision"],
            "vector_set_hash": portable["embedding"]["vector_set_hash"],
        },
        "evidence_boundary": {
            "runtime_index_read": True,
            "runtime_index_written": False,
            "frozen_marker_created": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "retrieval_called": False,
            "freeze_called": False,
        },
    }
    _require(
        body["semantic_contents"]["memory_ids"] == list(EXPECTED_MEMORY_IDS)
        and body["semantic_contents"]["semantic_group_ids"] == list(EXPECTED_GROUP_IDS)
        and body["semantic_contents"]["held_group_ids"] == list(EXPECTED_HELD_GROUP_IDS)
        and body["semantic_contents"]["embedding_revision"] == EXPECTED_EMBEDDING_REVISION,
        "D-109 runtime target contents drifted",
    )
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": RUNTIME_PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": f"d109preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d109_runtime_preflight_payload(
    payload: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    verify_live_runtime: bool = False,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    _root_identity(
        payload,
        schema_version=RUNTIME_PREFLIGHT_SCHEMA_VERSION,
        id_field="preflight_id",
        id_prefix="d109preflight_",
        label="runtime preflight",
    )
    body = payload["semantic_body"]
    portable, portable_content, _ = _load_exact_portable_inputs(repo)
    expected_runtime = {
        "target_path": DEFAULT_RUNTIME_INDEX_PATH.as_posix(),
        "directory_path": DEFAULT_RUNTIME_INDEX_PATH.parent.as_posix(),
        "directory_file_names": ["index.json"],
        "file_bytes": len(portable_content),
        "file_sha256": sha256_bytes(portable_content),
        "content_hash": portable["content_hash"],
        "index_id": portable["index_version"],
        "frozen": False,
        "frozen_marker_present": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "runtime_memory_injection_count": 0,
        "byte_identical_to_portable_index": True,
    }
    _require(
        body.get("runtime_target") == expected_runtime,
        "D-109 runtime preflight target drifted",
    )
    _require(
        body.get("portable_index")
        == {
            "path": DEFAULT_PORTABLE_INDEX_PATH.as_posix(),
            "index_id": EXPECTED_INDEX_ID,
            "file_bytes": len(portable_content),
            "file_sha256": sha256_bytes(portable_content),
            "content_hash": portable["content_hash"],
        },
        "D-109 runtime preflight portable binding drifted",
    )
    boundary = body.get("evidence_boundary", {})
    _require(
        boundary.get("runtime_index_read") is True
        and boundary.get("runtime_index_written") is False
        and boundary.get("frozen_marker_created") is False
        and boundary.get("provider_calls_made") == 0
        and boundary.get("evaluator_calls_made") == 0
        and boundary.get("retrieval_called") is False
        and boundary.get("freeze_called") is False,
        "D-109 runtime preflight boundary widened",
    )
    if verify_live_runtime:
        observed = observe_d109_runtime_preflight(repository=repo)
        _require(observed == payload, "D-109 live runtime precondition drifted")
    return {
        "preflight_id": payload["preflight_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "runtime_target": expected_runtime,
        "live_runtime_verified": verify_live_runtime,
        "memory_index_frozen": False,
    }


def build_d109_freeze_authorization_candidate(
    runtime_preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    validated_preflight = validate_d109_runtime_preflight_payload(
        runtime_preflight,
        repository=repo,
        verify_live_runtime=False,
    )
    d108_result = d108.validate_d108_completion_gate(repository=repo)
    portable, portable_content, report = _load_exact_portable_inputs(repo)
    preflight_content = _pretty_json(runtime_preflight)
    body = {
        "milestone": MILESTONE,
        "candidate_kind": "exact-unfrozen-group-index-freeze-authorization",
        "recorded_at": CANDIDATE_RECORDED_AT,
        "d108_completion_gate": {
            "path": d108.DEFAULT_COMPLETION_GATE_PATH.as_posix(),
            "gate_id": d108_result["gate_id"],
            "semantic_body_hash": d108_result["semantic_body_hash"],
            "file_bytes": d108_result["file_bytes"],
            "file_sha256": d108_result["file_sha256"],
            "provider_exact_budget_validated": True,
            "memory_delta_tokens": d108_result["memory_delta_tokens"],
            "maximum_memory_delta_tokens": d108_result["maximum_memory_delta_tokens"],
        },
        "d107_portable_validation": {
            "path": d107.DEFAULT_PORTABLE_REPORT_PATH.as_posix(),
            "validation_id": report["validation_id"],
            "semantic_body_hash": report["semantic_body_hash"],
            "file_bytes": EXPECTED_D107_PORTABLE_VALIDATION_BYTES,
            "file_sha256": EXPECTED_D107_PORTABLE_VALIDATION_FILE_SHA,
        },
        "runtime_preflight": {
            "path": DEFAULT_RUNTIME_PREFLIGHT_PATH.as_posix(),
            "schema_version": runtime_preflight["schema_version"],
            "preflight_id": validated_preflight["preflight_id"],
            "semantic_body_hash": validated_preflight["semantic_body_hash"],
            "file_bytes": len(preflight_content),
            "file_sha256": sha256_bytes(preflight_content),
        },
        "freeze_target": {
            "index_id": portable["index_version"],
            "runtime_index_path": DEFAULT_RUNTIME_INDEX_PATH.as_posix(),
            "portable_index_path": DEFAULT_PORTABLE_INDEX_PATH.as_posix(),
            "pre_freeze_file_bytes": len(portable_content),
            "pre_freeze_file_sha256": sha256_bytes(portable_content),
            "pre_freeze_content_hash": portable["content_hash"],
            "entry_count": len(portable["entries"]),
            "embedding_count": len(portable["embeddings"]),
            "memory_ids": [row["memory_id"] for row in portable["entries"]],
            "semantic_group_ids": [
                row["semantic_group_id"] for row in portable["group_provenance"]
            ],
            "held_group_ids": portable["held_group_ids"],
            "embedding_model": portable["embedding"]["model"],
            "embedding_revision": portable["embedding"]["revision"],
            "vector_set_hash": portable["embedding"]["vector_set_hash"],
        },
        "authorized_action_template": {
            "schema_version": FREEZE_ACTION_SCHEMA_VERSION,
            "action": "freeze-exact-group-index-once",
            "approval_receipt_required": True,
            "approval_must_repeat_candidate_id_body_sha_and_file_sha": True,
            "one_use_execution_required": True,
            "automatic_retry_allowed": False,
            "allowed_existing_json_mutations": list(ALLOWED_EXISTING_JSON_MUTATIONS),
            "all_other_existing_json_fields_byte_semantically_unchanged": True,
            "frozen_at_source": "approval-bound-freeze-execution-start-utc",
            "post_freeze_content_hash_rule": (
                "sha256(canonical_json(index_without_content_hash))"
            ),
            "marker_path": (
                DEFAULT_RUNTIME_INDEX_PATH.parent / "FROZEN"
            ).as_posix(),
            "marker_content_rule": "post_freeze_content_hash + LF",
            "marker_written_after_index": True,
            "partial_or_ambiguous_state_must_fail_closed": True,
            "provider_calls_authorized": 0,
            "evaluator_calls_authorized": 0,
            "retrieval_authorized": False,
            "runtime_memory_injection_authorized": False,
            "core_campaign_authorized": False,
            "analysis_authorized": False,
        },
        "expected_post_freeze_authority": {
            "index_freeze_authorized": True,
            "memory_index_frozen": True,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
        },
        "current_authority": {
            "freeze_authorization_candidate_ready": True,
            "explicit_user_approval_received": False,
            "index_freeze_authorized": False,
            "memory_index_frozen": False,
            "frozen_marker_present": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "provider_calls_made_by_d109": 0,
            "evaluator_calls_made_by_d109": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": "exact-d109-candidate-id-body-sha-file-sha-user-approval",
    }
    _require(
        body["d108_completion_gate"]["memory_delta_tokens"] == 702
        and body["freeze_target"]["memory_ids"] == list(EXPECTED_MEMORY_IDS)
        and body["freeze_target"]["semantic_group_ids"] == list(EXPECTED_GROUP_IDS)
        and body["freeze_target"]["held_group_ids"] == list(EXPECTED_HELD_GROUP_IDS)
        and body["freeze_target"]["embedding_revision"] == EXPECTED_EMBEDDING_REVISION,
        "D-109 candidate target drifted",
    )
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"d109freezecandidate_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def validate_d109_candidate_payload(
    payload: Mapping[str, Any],
    runtime_preflight: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    _root_identity(
        payload,
        schema_version=CANDIDATE_SCHEMA_VERSION,
        id_field="candidate_id",
        id_prefix="d109freezecandidate_",
        label="freeze authorization candidate",
    )
    expected = build_d109_freeze_authorization_candidate(runtime_preflight, repository=repo)
    _require(payload == expected, "D-109 freeze authorization candidate semantic content drifted")
    authority = payload["semantic_body"]["current_authority"]
    _require(
        authority["freeze_authorization_candidate_ready"] is True
        and authority["explicit_user_approval_received"] is False
        and authority["index_freeze_authorized"] is False
        and authority["memory_index_frozen"] is False
        and authority["retrieval_ready"] is False
        and authority["core_campaign_unlocked"] is False,
        "D-109 candidate authority widened",
    )
    return {
        "candidate_id": payload["candidate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "index_id": payload["semantic_body"]["freeze_target"]["index_id"],
        "explicit_user_approval_received": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
    }


def build_d109_source_gate(
    runtime_preflight: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    preflight_validation = validate_d109_runtime_preflight_payload(
        runtime_preflight,
        repository=repo,
        verify_live_runtime=False,
    )
    candidate_validation = validate_d109_candidate_payload(
        candidate,
        runtime_preflight,
        repository=repo,
    )
    preflight_content = _pretty_json(runtime_preflight)
    candidate_content = _pretty_json(candidate)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-index-freeze-authorization-candidate-source-gate",
        "recorded_at": GATE_RECORDED_AT,
        "d108_completion_gate": {
            "gate_id": EXPECTED_D108_GATE_ID,
            "semantic_body_hash": EXPECTED_D108_BODY_SHA,
            "file_bytes": EXPECTED_D108_GATE_BYTES,
            "file_sha256": EXPECTED_D108_GATE_FILE_SHA,
        },
        "runtime_preflight": {
            "path": DEFAULT_RUNTIME_PREFLIGHT_PATH.as_posix(),
            "preflight_id": preflight_validation["preflight_id"],
            "semantic_body_hash": preflight_validation["semantic_body_hash"],
            "file_bytes": len(preflight_content),
            "file_sha256": sha256_bytes(preflight_content),
        },
        "authorization_candidate": {
            "path": DEFAULT_CANDIDATE_PATH.as_posix(),
            "candidate_id": candidate_validation["candidate_id"],
            "semantic_body_hash": candidate_validation["semantic_body_hash"],
            "file_bytes": len(candidate_content),
            "file_sha256": sha256_bytes(candidate_content),
        },
        "implementation_files": [
            _file_binding(path, repository=repo, label="D-109 implementation")
            for path in D109_IMPLEMENTATION_PATHS
        ],
        "evidence_boundary": {
            "portable_index_read": True,
            "runtime_index_read_for_preflight": True,
            "runtime_index_written": False,
            "frozen_marker_created": False,
            "freeze_function_called": False,
            "retrieval_called": False,
            "runtime_memory_injected": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "core_campaign_started": False,
        },
        "authority": {
            "freeze_authorization_candidate_ready": True,
            "exact_candidate_user_approval_received": False,
            "freeze_execution_authorized": False,
            "index_freeze_authorized": False,
            "memory_index_frozen": False,
            "retrieval_ready": False,
            "retrieval_experiment_authorized": False,
            "runtime_memory_injection_count": 0,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "memory_effect_established": False,
            "negative_transfer_established": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": "exact-d109-candidate-id-body-sha-file-sha-user-approval",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": f"d109_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _preflight_output(path: Path, content: bytes, *, repository: Path) -> None:
    d105.preflight_d105_exact_output(path, content, repository=repository)


def _write_exact(path: Path, content: bytes, *, repository: Path) -> dict[str, Any]:
    return d105.write_d105_new_exact(path, content, repository=repository)


def run_d109_offline_source_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Observe and materialize D-109 without mutating the runtime index."""

    repo = _repo_root(repository)
    before = observe_d109_runtime_preflight(repository=repo)
    candidate = build_d109_freeze_authorization_candidate(before, repository=repo)
    gate = build_d109_source_gate(before, candidate, repository=repo)
    outputs = {
        DEFAULT_RUNTIME_PREFLIGHT_PATH: _pretty_json(before),
        DEFAULT_CANDIDATE_PATH: _pretty_json(candidate),
        DEFAULT_SOURCE_GATE_PATH: _pretty_json(gate),
    }
    for path, content in outputs.items():
        _preflight_output(path, content, repository=repo)
    after = observe_d109_runtime_preflight(repository=repo)
    _require(before == after, "D-109 runtime target changed during offline preflight")
    writes = {
        path.as_posix(): _write_exact(path, content, repository=repo)
        for path, content in outputs.items()
    }
    return {
        "runtime_preflight_id": before["preflight_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_sha256": sha256_bytes(outputs[DEFAULT_CANDIDATE_PATH]),
        "gate_id": gate["gate_id"],
        "gate_semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_sha256": sha256_bytes(outputs[DEFAULT_SOURCE_GATE_PATH]),
        "writes": writes,
        "runtime_index_written": False,
        "frozen_marker_created": False,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
    }


def validate_d109_source_gate(
    source_gate_path: str | Path = DEFAULT_SOURCE_GATE_PATH,
    *,
    repository: str | Path | None = None,
    verify_live_runtime: bool = False,
) -> dict[str, Any]:
    """Rebuild the checked-in D-109 gate; live runtime verification is opt-in."""

    repo = _repo_root(repository)
    preflight_path = _resolved(
        DEFAULT_RUNTIME_PREFLIGHT_PATH,
        repository=repo,
        label="D-109 runtime preflight",
    )
    preflight_content = _read_stable(preflight_path, label="D-109 runtime preflight")
    preflight = _parse_json(preflight_content, label="D-109 runtime preflight")
    validate_d109_runtime_preflight_payload(
        preflight,
        repository=repo,
        verify_live_runtime=verify_live_runtime,
    )
    _require(
        preflight_content == _pretty_json(preflight),
        "D-109 runtime preflight is not canonical",
    )

    candidate_path = _resolved(
        DEFAULT_CANDIDATE_PATH,
        repository=repo,
        label="D-109 authorization candidate",
    )
    candidate_content = _read_stable(candidate_path, label="D-109 authorization candidate")
    candidate = _parse_json(candidate_content, label="D-109 authorization candidate")
    validate_d109_candidate_payload(candidate, preflight, repository=repo)
    _require(candidate_content == _pretty_json(candidate), "D-109 candidate is not canonical")

    gate_path = _resolved(source_gate_path, repository=repo, label="D-109 source gate")
    gate_content = _read_stable(gate_path, label="D-109 source gate")
    gate = _parse_json(gate_content, label="D-109 source gate")
    _root_identity(
        gate,
        schema_version=SOURCE_GATE_SCHEMA_VERSION,
        id_field="gate_id",
        id_prefix="d109_",
        label="source gate",
    )
    expected = build_d109_source_gate(preflight, candidate, repository=repo)
    _require(gate == expected, "D-109 source gate semantic content drifted")
    _require(gate_content == _pretty_json(expected), "D-109 source gate exact bytes drifted")
    authority = gate["semantic_body"]["authority"]
    _require(
        authority["freeze_authorization_candidate_ready"] is True
        and authority["exact_candidate_user_approval_received"] is False
        and authority["freeze_execution_authorized"] is False
        and authority["index_freeze_authorized"] is False
        and authority["memory_index_frozen"] is False
        and authority["retrieval_ready"] is False
        and authority["core_campaign_unlocked"] is False,
        "D-109 source gate authority widened",
    )
    return {
        "ok": True,
        "gate_id": gate["gate_id"],
        "semantic_body_hash": gate["semantic_body_hash"],
        "file_bytes": len(gate_content),
        "file_sha256": sha256_bytes(gate_content),
        "runtime_preflight_id": preflight["preflight_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_semantic_body_hash": candidate["semantic_body_hash"],
        "candidate_file_bytes": len(candidate_content),
        "candidate_file_sha256": sha256_bytes(candidate_content),
        "live_runtime_verified": verify_live_runtime,
        "index_freeze_authorized": False,
        "memory_index_frozen": False,
        "retrieval_ready": False,
        "core_campaign_unlocked": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
    }


__all__ = [
    "ALLOWED_EXISTING_JSON_MUTATIONS",
    "CANDIDATE_SCHEMA_VERSION",
    "DEFAULT_CANDIDATE_PATH",
    "DEFAULT_RUNTIME_INDEX_PATH",
    "DEFAULT_RUNTIME_PREFLIGHT_PATH",
    "DEFAULT_SOURCE_GATE_PATH",
    "D109AuthorizationError",
    "SOURCE_GATE_SCHEMA_VERSION",
    "build_d109_freeze_authorization_candidate",
    "build_d109_source_gate",
    "observe_d109_runtime_preflight",
    "run_d109_offline_source_gate",
    "validate_d109_candidate_payload",
    "validate_d109_runtime_preflight_payload",
    "validate_d109_source_gate",
]
