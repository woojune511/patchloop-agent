"""Prepare the D-118 external public-development source evidence pack.

D-118 binds the user's exact D-117 candidate approval to two official,
revision-pinned benchmark snapshots.  The snapshots are handled as opaque
bytes: this module hashes files but never parses Parquet metadata, schemas,
columns, rows, issue prose, labels, patches, tests, or oracle fields.

The resulting pack is intentionally blocked.  Exact content and an
exhaustive split rule are available, but no trusted pre-D-116 timestamp binds
both the snapshot and membership rule, and the future isolation profile has
not been executed.  D-118 therefore does not acquire or freeze a pool and does
not authorize a matcher, classifier, calibration, retrieval, agent, provider,
evaluator, or core campaign.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-118"
RECEIPT_SCHEMA_VERSION = "external-source-evidence-approval-receipt-d118-v1"
PREFLIGHT_SCHEMA_VERSION = "external-source-evidence-preflight-d118-v1"
EVIDENCE_PACK_SCHEMA_VERSION = "external-source-evidence-pack-d118-v1"
SOURCE_GATE_SCHEMA_VERSION = "external-source-evidence-source-gate-d118-v1"

# These are artifact-recording timestamps, not authenticated user-message or
# external-publication timestamps.  The user authorization preceded the
# approved metadata/download actions, but the app message timestamp is not an
# authenticated cutoff anchor and is not used as one.
APPROVAL_RECORDED_AT = "2026-08-07T10:17:00Z"
PREFLIGHT_RECORDED_AT = "2026-08-07T10:17:01Z"
EVIDENCE_PACK_RECORDED_AT = "2026-08-07T10:17:02Z"
SOURCE_GATE_RECORDED_AT = "2026-08-07T10:17:03Z"

DEFAULT_RECEIPT_PATH = Path(
    "reports/memory-development/d118-external-source-evidence-approval-receipt.json"
)
DEFAULT_PREFLIGHT_PATH = Path(
    "reports/memory-development/d118-external-source-evidence-preflight.json"
)
DEFAULT_EVIDENCE_PACK_PATH = Path(
    "reports/memory-development/d118-external-source-evidence-pack.json"
)
DEFAULT_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d118-external-source-evidence-source-gate.json"
)

D118_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d118_external_source_evidence.py"),
    Path("scripts/prepare_d118_external_source_evidence.py"),
    Path("tests/test_d118_external_source_evidence.py"),
)

D117_RECEIPT_PATH = Path(
    "reports/memory-development/d117-blind-control-acquisition-protocol-approval-receipt.json"
)
D117_PREFLIGHT_PATH = Path(
    "reports/memory-development/d117-blind-control-acquisition-protocol-preflight.json"
)
D117_CANDIDATE_PATH = Path(
    "reports/memory-development/"
    "d117-blind-control-acquisition-protocol-authorization-candidate.json"
)
D117_SOURCE_GATE_PATH = Path(
    "reports/memory-development/d117-blind-control-acquisition-protocol-source-gate.json"
)

EXPECTED_D117_CANDIDATE_ID = (
    "d117blindprotocolcandidate_27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae"
)
EXPECTED_D117_CANDIDATE_BODY_SHA = (
    "sha256:27622afdd9d46e43cb9e23675a334b5a4e91fc768298374cae61ab440c850dae"
)
EXPECTED_D117_CANDIDATE_BYTES = 7_999
EXPECTED_D117_CANDIDATE_FILE_SHA = (
    "sha256:d10bbe5b3b65050868a1202cd1af9f130c89bbe43ceccf9359af145cac96cda7"
)
EXPECTED_D117_GATE_ID = "d117_750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589"
EXPECTED_D117_GATE_BODY_SHA = (
    "sha256:750cd5a0a8946984aafe75b0939417bf026120cdb3dbc54d09180fd795202589"
)
EXPECTED_D117_GATE_BYTES = 16_813
EXPECTED_D117_GATE_FILE_SHA = (
    "sha256:a439fc936b5b594c043b4ea90cd57bb676e79004cf4de8794b83f3af15fb13e3"
)
EXPECTED_D117_PROPOSED_ACTION_HASH = (
    "sha256:362cf3f74c9d57ecc4238f4b7c024b470c8ad65038ee6a599581a1df82fc6c06"
)
EXPECTED_D116_CUTOFF = "2026-08-07T06:22:51.021003Z"

PROTECTED_FILE_SPECS = (
    {
        "path": D117_RECEIPT_PATH.as_posix(),
        "file_bytes": 10_096,
        "file_sha256": ("sha256:40ea64548634353a12b48f8bcabce941df47e16f9b27d892722d55fcda1e5e13"),
    },
    {
        "path": D117_PREFLIGHT_PATH.as_posix(),
        "file_bytes": 29_919,
        "file_sha256": ("sha256:6682f4f2870cdb34e6ee766333c95ac58a406a7d4e4086d6086752650869c305"),
    },
    {
        "path": D117_CANDIDATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D117_CANDIDATE_BYTES,
        "file_sha256": EXPECTED_D117_CANDIDATE_FILE_SHA,
    },
    {
        "path": D117_SOURCE_GATE_PATH.as_posix(),
        "file_bytes": EXPECTED_D117_GATE_BYTES,
        "file_sha256": EXPECTED_D117_GATE_FILE_SHA,
    },
    {
        "path": "patchloop/memory/d117_blind_control_acquisition_protocol.py",
        "file_bytes": 77_586,
        "file_sha256": ("sha256:56b2b428924e55fb9e6ba708b91552ee52472d4cadb53bfb2ac9bfb3be7f9a79"),
    },
    {
        "path": "scripts/build_d117_blind_control_acquisition_protocol_candidate.py",
        "file_bytes": 4_981,
        "file_sha256": ("sha256:70c1a57485e005f8bcc52255aca0aed52d475c78f3d8c60e06163b63addfc857"),
    },
    {
        "path": "tests/test_d117_blind_control_acquisition_protocol.py",
        "file_bytes": 30_733,
        "file_sha256": ("sha256:145d8252feac285af727ba9eb60e8e5923e773600d6632910f10715b751170aa"),
    },
)

# Only these local ignored files may be opened by D-118, and only as binary
# streams for size/SHA verification.  README and .gitattributes are bound as
# source-level metadata bytes but are not decoded or parsed by this module.
SOURCE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "source_id": "swe-bench-dev-f5351",
        "priority": 1,
        "benchmark_family": "SWE-bench",
        "publisher": "princeton-nlp",
        "repository_id": "princeton-nlp/SWE-bench",
        "repository_type": "dataset",
        "development_role": "dev",
        "revision": "f5351ee8c6663736817027db3ad03fe662cb5bb8",
        "official_commit_url": (
            "https://huggingface.co/datasets/princeton-nlp/SWE-bench/commit/"
            "f5351ee8c6663736817027db3ad03fe662cb5bb8"
        ),
        "download_host": "huggingface.co",
        "local_root": ".patchloop/external-evidence/d118/swe-bench-f5351",
        "requested_paths": (
            {
                "path": ".gitattributes",
                "file_bytes": 2_307,
                "file_sha256": (
                    "sha256:f4e703ea6e44bbebe53aceed2a89c11e40b88b7ae130c480c89860ab805ffc8f"
                ),
                "media_kind": "source-level-git-metadata",
            },
            {
                "path": "README.md",
                "file_bytes": 3_880,
                "file_sha256": (
                    "sha256:807eeb9e3a95b1b06958d7b7d93bc796c9b454fffdfa22f646ccfff2e17af45c"
                ),
                "media_kind": "source-level-dataset-card",
            },
            {
                "path": "data/dev-00000-of-00001.parquet",
                "file_bytes": 1_382_594,
                "file_sha256": (
                    "sha256:d758d54540aa4140d0274ed0cc93b8288aa6f323c3c603e2557e7666a47fc41b"
                ),
                "media_kind": "opaque-record-container",
            },
        ),
        "membership_rule": "all rows in the sole data/dev-* shard at the exact revision",
        "membership_glob": "data/dev-*",
        "provider_declared_member_count": 225,
        "provider_reports_gpg_verified_commit": True,
        "provider_reported_commit_date": "2024-06-27",
        "dataset_license_claim_scope": "official dataset/code repository metadata only",
        "upstream_issue_content_relicensed": False,
    },
    {
        "source_id": "swe-gym-train-26a6",
        "priority": 2,
        "benchmark_family": "SWE-Gym",
        "publisher": "SWE-Gym",
        "repository_id": "SWE-Gym/SWE-Gym",
        "repository_type": "dataset",
        "development_role": "train",
        "revision": "26a6eae79ae9cb6d4307c3cc99c126fbf23cb3f0",
        "official_commit_url": (
            "https://huggingface.co/datasets/SWE-Gym/SWE-Gym/commit/"
            "26a6eae79ae9cb6d4307c3cc99c126fbf23cb3f0"
        ),
        "download_host": "huggingface.co",
        "local_root": ".patchloop/external-evidence/d118/swe-gym-26a6",
        "requested_paths": (
            {
                "path": ".gitattributes",
                "file_bytes": 2_461,
                "file_sha256": (
                    "sha256:e7a120ab07b1bc5b486be249e9fc6c83d59448d0093e1dfebe95d1566d9cafc0"
                ),
                "media_kind": "source-level-git-metadata",
            },
            {
                "path": "README.md",
                "file_bytes": 680,
                "file_sha256": (
                    "sha256:e6aadc383f198bb7592af3c077d8dd71d350a86bea76e1218fd1042fe4b99a04"
                ),
                "media_kind": "source-level-dataset-card",
            },
            {
                "path": "data/train-00000-of-00001.parquet",
                "file_bytes": 43_644_473,
                "file_sha256": (
                    "sha256:60569cea74bb281f7a5579467436a2bc1932c6e0c5f2f7fa0d084392abd9ad97"
                ),
                "media_kind": "opaque-record-container",
            },
        ),
        "membership_rule": "all rows in the sole data/train-* shard at the exact revision",
        "membership_glob": "data/train-*",
        "provider_declared_member_count": 2_438,
        "provider_reports_gpg_verified_commit": True,
        "provider_reported_commit_date": "2024-12-09",
        "dataset_license_claim_scope": "official dataset repository metadata only",
        "upstream_issue_content_relicensed": False,
    },
)

REJECTED_SOURCE_SPECS = (
    {
        "source_id": "terminal-bench-2-1",
        "benchmark_family": "Terminal-Bench 2.1",
        "status": "excluded-before-snapshot-download",
        "reason_codes": [
            "EVALUATION_ONLY_NO_PUBLIC_DEVELOPMENT_SPLIT",
            "OFFICIAL_TRAINING_CORPUS_CANARY_CONFLICT",
            "NO_EXACT_PRE_D116_MEMBERSHIP_EVIDENCE_IDENTIFIED",
        ],
        "snapshot_downloaded": False,
        "task_or_issue_record_read_count": 0,
    },
)

AUTHORIZED_SCOPE = {
    "action_kind": "prepare-external-public-development-source-evidence",
    "milestone": MILESTONE,
    "exact_d117_candidate_triple_required": True,
    "official_public_development_benchmark_metadata_research_allowed": True,
    "revision_pinned_opaque_snapshot_download_allowed": True,
    "source_level_manifest_checksum_license_and_version_lookup_allowed": True,
    "membership_cutoff_and_isolation_hash_preflight_allowed": True,
    "issue_or_task_record_parsing_or_reading_allowed": False,
    "issue_labeling_or_blind_review_allowed": False,
    "pool_selection_acquisition_or_freeze_allowed": False,
    "matcher_classifier_or_calibration_execution_allowed": False,
    "score_policy_or_index_mutation_allowed": False,
    "retrieval_or_runtime_memory_injection_allowed": False,
    "agent_provider_evaluator_or_core_campaign_allowed": False,
}
AUTHORIZED_ACTION_HASH = sha256_text(canonical_json(AUTHORIZED_SCOPE))

RECEIPT_ROOT_KEYS = ("schema_version", "receipt_id", "semantic_body_hash", "semantic_body")
PREFLIGHT_ROOT_KEYS = (
    "schema_version",
    "preflight_id",
    "semantic_body_hash",
    "semantic_body",
)
EVIDENCE_PACK_ROOT_KEYS = (
    "schema_version",
    "evidence_pack_id",
    "semantic_body_hash",
    "semantic_body",
)
GATE_ROOT_KEYS = ("schema_version", "gate_id", "semantic_body_hash", "semantic_body")

RECEIPT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_reference",
    "approval_reference_mode",
    "approval_statement_code",
    "d117_candidate",
    "d117_source_gate",
    "authorized_scope",
    "authorized_action_hash",
    "materialization_scope",
    "claim_semantics",
    "self_attested",
    "approver_kind",
    "approver_label",
    "reviewer_identity_authenticated",
    "cryptographic_signature_verified",
)
PREFLIGHT_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_receipt",
    "d117_candidate",
    "d117_source_gate",
    "source_request_plan",
    "opaque_handling_contract",
    "membership_preflight_contract",
    "cutoff_preflight_contract",
    "isolation_profile",
    "isolation_profile_hash",
    "protected_pre_state",
    "evidence_boundary",
    "authority",
)
EVIDENCE_PACK_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_receipt",
    "preflight",
    "research_summary",
    "source_candidates",
    "rejected_sources",
    "download_observation",
    "aggregate_disposition",
    "unresolved_prerequisites",
    "protected_pre_state",
    "protected_post_state",
    "protected_fingerprints_equal",
    "external_object_pre_state",
    "external_object_post_state",
    "external_object_fingerprints_equal",
    "evidence_boundary",
    "authority",
)
GATE_BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "approval_receipt",
    "d117_candidate",
    "d117_source_gate",
    "preflight",
    "evidence_pack",
    "implementation_files",
    "protected_input_integrity",
    "qualification",
    "evidence_boundary",
    "authority",
    "next_gate",
)


class D118ExternalEvidenceError(ContractError):
    """Raised when D-118 evidence violates its sealed boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D118ExternalEvidenceError(message)


def _repo_root(repository: str | Path | None) -> Path:
    root = Path(repository) if repository is not None else Path(__file__).resolve().parents[2]
    return root.resolve(strict=True)


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attrs & reparse)


def _resolved(
    relative: str | Path,
    *,
    repository: Path,
    label: str,
    must_exist: bool = True,
) -> Path:
    raw = Path(relative)
    _require(not raw.is_absolute(), f"D-118 {label} path must be repository-relative")
    _require(".." not in raw.parts, f"D-118 {label} path traversal rejected")
    _require(
        all(":" not in part and not part.endswith((" ", ".")) for part in raw.parts),
        f"D-118 {label} path alias rejected",
    )
    selected = repository.joinpath(raw)
    parent = selected.parent
    current = repository
    for part in parent.relative_to(repository).parts:
        current = current / part
        if current.exists():
            _require(not _is_linklike(current), f"D-118 {label} linked ancestor rejected")
    _require(
        not _is_linklike(selected),
        f"D-118 {label} linked final component rejected",
    )
    resolved = selected.resolve(strict=must_exist)
    try:
        resolved.relative_to(repository)
    except ValueError as exc:
        raise D118ExternalEvidenceError(f"D-118 {label} escaped repository") from exc
    if must_exist:
        _require(resolved.is_file(), f"D-118 {label} must be a regular file")
    return resolved


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _stable_file_binding(
    relative: str | Path,
    *,
    repository: Path,
    label: str,
) -> dict[str, Any]:
    selected = _resolved(relative, repository=repository, label=label)
    before = selected.stat()
    digest = hashlib.sha256()
    total = 0
    with selected.open("rb") as handle:
        opened_before = os.fstat(handle.fileno())
        _require(
            _stat_identity(before) == _stat_identity(opened_before),
            f"D-118 {label} changed before open",
        )
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            total += len(chunk)
        opened_after = os.fstat(handle.fileno())
    after = selected.stat()
    _require(
        _stat_identity(before)
        == _stat_identity(opened_before)
        == _stat_identity(opened_after)
        == _stat_identity(after),
        f"D-118 {label} changed during stable hash",
    )
    _require(total == before.st_size, f"D-118 {label} size changed while hashing")
    return {
        "path": Path(relative).as_posix(),
        "file_bytes": total,
        "file_sha256": f"sha256:{digest.hexdigest()}",
    }


def _read_stable_bytes(path: Path, *, label: str) -> bytes:
    """Read exact bytes while binding the opened descriptor to the path."""

    before = path.stat()
    with path.open("rb") as handle:
        opened_before = os.fstat(handle.fileno())
        _require(
            _stat_identity(before) == _stat_identity(opened_before),
            f"D-118 {label} changed before open",
        )
        content = handle.read()
        opened_after = os.fstat(handle.fileno())
    after = path.stat()
    _require(
        _stat_identity(before)
        == _stat_identity(opened_before)
        == _stat_identity(opened_after)
        == _stat_identity(after),
        f"D-118 {label} changed during stable read",
    )
    _require(len(content) == before.st_size, f"D-118 {label} byte count changed")
    return content


def _pretty_json(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _read_json_exact(
    relative: str | Path,
    *,
    repository: Path,
    label: str,
    expected_bytes: int,
    expected_sha: str,
) -> tuple[dict[str, Any], bytes]:
    selected = _resolved(relative, repository=repository, label=label)
    content = _read_stable_bytes(selected, label=label)
    _require(len(content) == expected_bytes, f"D-118 {label} byte count drifted")
    _require(sha256_bytes(content) == expected_sha, f"D-118 {label} file SHA drifted")
    try:
        parsed = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D118ExternalEvidenceError(f"D-118 {label} is not canonical JSON") from exc
    _require(isinstance(parsed, dict), f"D-118 {label} root must be an object")
    _require(content == _pretty_json(parsed), f"D-118 {label} canonical bytes drifted")
    return parsed, content


def _require_exact_keys(value: Mapping[str, Any], keys: Sequence[str], *, label: str) -> None:
    _require(tuple(value) == tuple(keys), f"D-118 {label} exact key set/order mismatch")


def _validate_envelope(
    payload: Mapping[str, Any],
    *,
    root_keys: Sequence[str],
    body_keys: Sequence[str],
    id_field: str,
    id_prefix: str,
    schema_version: str,
    label: str,
) -> Mapping[str, Any]:
    _require_exact_keys(payload, root_keys, label=f"{label} root")
    _require(payload["schema_version"] == schema_version, f"D-118 {label} schema drifted")
    body = payload["semantic_body"]
    _require(isinstance(body, Mapping), f"D-118 {label} body must be an object")
    _require_exact_keys(body, body_keys, label=f"{label} body")
    body_hash = sha256_text(canonical_json(body))
    _require(payload["semantic_body_hash"] == body_hash, f"D-118 {label} body SHA drifted")
    _require(
        payload[id_field] == f"{id_prefix}{body_hash.removeprefix('sha256:')}",
        f"D-118 {label} content-derived ID drifted",
    )
    return body


def _artifact_binding(
    relative: Path,
    *,
    payload: Mapping[str, Any],
    content: bytes,
    id_field: str,
) -> dict[str, Any]:
    return {
        "path": relative.as_posix(),
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _output_binding(relative: Path, payload: Mapping[str, Any], *, id_field: str) -> dict[str, Any]:
    content = _pretty_json(payload)
    return {
        "path": relative.as_posix(),
        id_field: payload[id_field],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _load_exact_d117_context(repository: Path) -> dict[str, Any]:
    candidate, candidate_content = _read_json_exact(
        D117_CANDIDATE_PATH,
        repository=repository,
        label="D-117 candidate",
        expected_bytes=EXPECTED_D117_CANDIDATE_BYTES,
        expected_sha=EXPECTED_D117_CANDIDATE_FILE_SHA,
    )
    gate, gate_content = _read_json_exact(
        D117_SOURCE_GATE_PATH,
        repository=repository,
        label="D-117 source gate",
        expected_bytes=EXPECTED_D117_GATE_BYTES,
        expected_sha=EXPECTED_D117_GATE_FILE_SHA,
    )
    _require(
        candidate.get("candidate_id") == EXPECTED_D117_CANDIDATE_ID
        and candidate.get("semantic_body_hash") == EXPECTED_D117_CANDIDATE_BODY_SHA,
        "D-118 exact D-117 candidate triple mismatch",
    )
    _require(
        gate.get("gate_id") == EXPECTED_D117_GATE_ID
        and gate.get("semantic_body_hash") == EXPECTED_D117_GATE_BODY_SHA,
        "D-118 exact D-117 source-gate triple mismatch",
    )
    next_hash = candidate["semantic_body"].get("proposed_next_action_hash")
    _require(
        next_hash == EXPECTED_D117_PROPOSED_ACTION_HASH,
        "D-118 D-117 proposed action hash drifted",
    )
    _require(
        gate["semantic_body"].get("next_gate")
        == (
            "exact-d117-candidate-triple-plus-external-source-membership-cutoff-and-"
            "isolation-triples-d118-execution-authorization-candidate-approval"
        ),
        "D-118 D-117 next gate drifted",
    )
    return {
        "candidate": candidate,
        "candidate_content": candidate_content,
        "gate": gate,
        "gate_content": gate_content,
    }


def _protected_state(repository: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for spec in PROTECTED_FILE_SPECS:
        observed = _stable_file_binding(
            spec["path"], repository=repository, label="protected input"
        )
        _require(observed == spec, f"D-118 protected input drifted: {spec['path']}")
        rows.append(observed)
    fingerprint = sha256_text(canonical_json(rows))
    return {"files": rows, "fingerprint": fingerprint}


def _implementation_state(repository: Path) -> dict[str, Any]:
    rows = [
        _stable_file_binding(path, repository=repository, label="implementation file")
        for path in D118_IMPLEMENTATION_PATHS
    ]
    return {"files": rows, "fingerprint": sha256_text(canonical_json(rows))}


def _expected_external_object_state() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for source in SOURCE_SPECS:
        for file_spec in source["requested_paths"]:
            rows.append(
                {
                    "source_id": source["source_id"],
                    "path": f"{source['local_root']}/{file_spec['path']}",
                    "file_bytes": file_spec["file_bytes"],
                    "file_sha256": file_spec["file_sha256"],
                    "media_kind": file_spec["media_kind"],
                }
            )
    return {
        "files": rows,
        "file_count": len(rows),
        "total_bytes": sum(int(row["file_bytes"]) for row in rows),
        "fingerprint": sha256_text(canonical_json(rows)),
        "claim_scope": "six-expected-files-only-not-directory-exclusivity",
    }


def observe_external_objects(*, repository: str | Path | None = None) -> dict[str, Any]:
    """Hash only the six approved source files; never decode or parse them."""

    repo = _repo_root(repository)
    expected = _expected_external_object_state()
    rows: list[dict[str, Any]] = []
    for spec in expected["files"]:
        observed = _stable_file_binding(spec["path"], repository=repo, label="opaque source object")
        row = {"source_id": spec["source_id"], **observed, "media_kind": spec["media_kind"]}
        _require(row == spec, f"D-118 opaque source object drifted: {spec['path']}")
        rows.append(row)
    result = {
        "files": rows,
        "file_count": len(rows),
        "total_bytes": sum(int(row["file_bytes"]) for row in rows),
        "fingerprint": sha256_text(canonical_json(rows)),
        "claim_scope": "six-expected-files-only-not-directory-exclusivity",
    }
    _require(result == expected, "D-118 opaque source object set drifted")
    return result


def _source_request_plan() -> dict[str, Any]:
    rows = []
    for source in SOURCE_SPECS:
        rows.append(
            {
                "source_id": source["source_id"],
                "repository_id": source["repository_id"],
                "repository_type": source["repository_type"],
                "development_role": source["development_role"],
                "revision": source["revision"],
                "revision_is_full_40_hex_commit": True,
                "requested_paths": [dict(row) for row in source["requested_paths"]],
                "allowed_scheme": "https",
                "allowed_host": source["download_host"],
                "mutable_ref_allowed": False,
                "cross_host_redirect_allowed": False,
                "url_credentials_allowed": False,
                "automatic_retry_allowed": False,
                "max_total_bytes": sum(int(row["file_bytes"]) for row in source["requested_paths"]),
                "response_body_logging_allowed": False,
            }
        )
    return {
        "plan_version": "revision-pinned-opaque-source-request-plan-d118-v1",
        "ordered_sources": rows,
        "plan_frozen_before_current_artifact_materialization": True,
        "plan_precommitted_before_network_download": False,
        "network_execution_journal_present": False,
        "retrospective_observation_limit_disclosed": True,
        "download_counts_and_no_record-read_history_are_self_attested": True,
    }


def _opaque_handling_contract() -> dict[str, Any]:
    return {
        "contract_version": "opaque-no-record-read-d118-v1",
        "binary_stream_hash_only": True,
        "parquet_footer_schema_statistics_or_row_parse_allowed": False,
        "archive_extraction_or_decompression_allowed": False,
        "utf8_decode_of_opaque_container_allowed": False,
        "pyarrow_pandas_datasets_duckdb_or_fastparquet_allowed": False,
        "record_field_read_count": 0,
        "issue_prose_label_hint_patch_test_or_oracle_read_count": 0,
        "raw_snapshot_checked_into_git_or_reports": False,
        "local_objects_are_ignored_runtime_evidence": True,
        "clean_clone_can_validate_sealed_pack_without_reverifying_raw_objects": True,
        "clean_clone_raw_object_reverification_proved": False,
    }


def _membership_contract() -> dict[str, Any]:
    rows = []
    for source in SOURCE_SPECS:
        rule = {
            "source_id": source["source_id"],
            "development_role": source["development_role"],
            "rule_kind": "grammar-independent-exhaustive-official-split-rule",
            "rule_text": source["membership_rule"],
            "membership_glob": source["membership_glob"],
            "exact_revision": source["revision"],
            "provider_declared_member_count": source["provider_declared_member_count"],
            "verified_member_count": None,
            "member_id_read_count": 0,
            "record_content_read_count": 0,
            "content_or_label_dependent_selection": False,
            "post_d116_subset_selection_allowed": False,
            "provider_reports_rule_and_shard_content_bound_in_tree": True,
            "provider_tree_binding_verified_from_bound_inputs_by_d118": False,
            "provider_tree_claim_evidence_kind": "source-level-web-research-self-attested",
            "readme_rule_or_count_parsed_by_d118": False,
            "rule_trusted_pre_d116_time_bound": False,
        }
        rows.append({**rule, "rule_hash": sha256_text(canonical_json(rule))})
    return {
        "contract_version": "exhaustive-development-split-membership-preflight-d118-v1",
        "rules": rows,
        "all_rules_provider_reported_content_bound": True,
        "all_rules_content_bound_verified_from_bound_inputs_by_d118": False,
        "all_rules_trusted_pre_d116_time_bound": False,
        "membership_ready_for_independent_calibration": False,
    }


def _cutoff_contract() -> dict[str, Any]:
    rows = []
    for source in SOURCE_SPECS:
        rows.append(
            {
                "source_id": source["source_id"],
                "exact_revision": source["revision"],
                "provider_reported_commit_date": source["provider_reported_commit_date"],
                "provider_reports_gpg_verified_commit": source[
                    "provider_reports_gpg_verified_commit"
                ],
                "provider_badge_observation_evidence_kind": (
                    "source-level-web-research-self-attested-not-portable-proof"
                ),
                "signature_payload_and_key_verified_locally": False,
                "git_timestamp_accepted_as_trusted_time": False,
                "current_download_time_accepted_as_preexistence": False,
                "http_date_or_last_modified_accepted_as_preexistence": False,
                "independent_timestamp_or_immutable_archive_binds_exact_tree": False,
                "trusted_anchor_binds_snapshot_and_membership_rule": False,
                "strictly_before_d116_cutoff_verified": False,
                "reason_codes": [
                    "TRUSTED_CUTOFF_ANCHOR_MISSING",
                    "SIGNED_GIT_TREE_IS_NOT_AN_INDEPENDENT_TIMESTAMP",
                    "MEMBERSHIP_RULE_NOT_TRUSTED_TIME_BOUND",
                ],
            }
        )
    return {
        "contract_version": "strict-external-cutoff-anchor-preflight-d118-v1",
        "d116_cutoff_exclusive": EXPECTED_D116_CUTOFF,
        "accepted_anchor_kinds": [
            "trusted-timestamp-or-transparency-proof-binding-exact-tree-and-membership",
            "independent-immutable-archive-binding-exact-tree-and-membership",
            "trusted-signed-release-with-independent-time-and-exact-content-binding",
        ],
        "insufficient_alone": [
            "current-download-or-current-hash",
            "filesystem-mtime",
            "http-date-or-last-modified",
            "unsigned-or-signed-git-author-or-committer-date",
            "provider-verified-badge-without-independent-time-proof",
            "paper-or-project-publication-date-without-exact-content-binding",
        ],
        "sources": rows,
        "trusted_cutoff_anchor_verified": False,
    }


def _isolation_profile() -> dict[str, Any]:
    return {
        "profile_version": "future-isolated-public-projection-profile-d118-v1",
        "purpose": "future-hash-bound-record-projection-not-executed-in-d118",
        "immutable_image_digest_required": True,
        "immutable_image_digest": None,
        "network_mode": "none",
        "root_filesystem_read_only": True,
        "run_as_non_root": True,
        "capabilities_drop": ["ALL"],
        "no_new_privileges": True,
        "privileged": False,
        "host_pid_ipc_or_docker_socket_allowed": False,
        "read_only_input_mounts": ["one-exact-approved-opaque-object"],
        "writable_outputs": ["one-size-bounded-tmpfs-output"],
        "forbidden_mounts": [
            "repository-root",
            ".git",
            "AGENTS.md",
            "docs",
            "tasks",
            "D105-through-D118-artifacts",
            "matcher-grammar",
            "memory-index",
            "traces",
            "patches",
            "evaluator-or-private-data",
            "credential-or-host-cache-directories",
        ],
        "environment_allowlist": ["LANG", "LC_ALL", "PYTHONHASHSEED"],
        "api_hf_git_ssh_proxy_credentials_allowed": False,
        "stdout_stderr_may_contain_record_values": False,
        "current_process_or_same_checkout_agent_eligible_as_blind_role": False,
        "technical_negative_probe_executed": False,
        "isolation_session_count": 0,
        "profile_is_plan_only_not_execution_evidence": True,
    }


def _authority() -> dict[str, Any]:
    return {
        "exact_d117_candidate_user_approval_received": True,
        "external_source_evidence_preparation_authorized": True,
        "official_public_development_metadata_research_authorized": True,
        "revision_pinned_opaque_snapshot_download_authorized": True,
        "membership_cutoff_and_isolation_hash_preflight_authorized": True,
        "source_candidate_identification_authorized": True,
        "d117_proposed_next_action_authorized": False,
        "d117_proposed_next_action_consumed": False,
        "external_triples_prerequisite_satisfied": False,
        "source_pool_selection_acquisition_or_freeze_authorized": False,
        "source_pool_selected": False,
        "source_pool_acquired": False,
        "source_pool_frozen": False,
        "issue_or_task_record_read_count": 0,
        "issue_labeling_or_review_count": 0,
        "matcher_execution_count": 0,
        "classifier_execution_count": 0,
        "calibration_execution_count": 0,
        "independent_positive_count": 0,
        "trusted_cutoff_anchor_verified": False,
        "independent_generalization_validated": False,
        "true_relevance_established": False,
        "score_policy_correction_authorized": False,
        "score_policy_or_ranking_changed": False,
        "memory_index_changed": False,
        "retrieval_ready": False,
        "retrieval_calls": 0,
        "runtime_memory_injection_count": 0,
        "agent_runs": 0,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "core_campaign_unlocked": False,
        "analysis_campaign_unlocked": False,
        "d118_execution_authorization_candidate_ready": False,
    }


def build_d118_approval_receipt(
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_d117_context(repo)
    candidate = current["candidate"]
    gate = current["gate"]
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "exact-d117-bound-external-source-evidence-approval",
        "recorded_at": APPROVAL_RECORDED_AT,
        "approval_reference": {
            "candidate_id": EXPECTED_D117_CANDIDATE_ID,
            "semantic_body_hash": EXPECTED_D117_CANDIDATE_BODY_SHA,
            "file_sha256": EXPECTED_D117_CANDIDATE_FILE_SHA,
        },
        "approval_reference_mode": "exact-current-user-message-self-attested",
        "approval_statement_code": (
            "d118-public-development-metadata-opaque-snapshot-and-hash-preflight-only-v1"
        ),
        "d117_candidate": _artifact_binding(
            D117_CANDIDATE_PATH,
            payload=candidate,
            content=current["candidate_content"],
            id_field="candidate_id",
        ),
        "d117_source_gate": _artifact_binding(
            D117_SOURCE_GATE_PATH,
            payload=gate,
            content=current["gate_content"],
            id_field="gate_id",
        ),
        "authorized_scope": dict(AUTHORIZED_SCOPE),
        "authorized_action_hash": AUTHORIZED_ACTION_HASH,
        "materialization_scope": {
            "new_module_script_test_and_four_sanitized_json_artifacts_only": True,
            "ignored_local_opaque_snapshots_allowed": True,
            "raw_snapshot_bytes_in_git_reports_or_docs_allowed": False,
            "record_parser_or_projector_implementation_allowed": False,
            "record_or_issue_content_read_allowed": False,
            "execution_authorization_candidate_allowed": False,
            "exact_d117_bound_input_mutation_allowed": False,
        },
        "claim_semantics": {
            "authorization_observed_before_download_actions_self_attested": True,
            "authenticated_user_message_timestamp_available": False,
            "download_http_request_count_instrumented": False,
            "network_execution_journal_present": False,
            "receipt_is_not_trusted_cutoff_evidence": True,
            "receipt_is_not_pool_acquisition_or_blindness_claim": True,
            "d117_later_execution_candidate_action_not_authorized_or_consumed": True,
            "external_triples_prerequisite_not_satisfied": True,
            "global_cross_clone_or_arbitrary_writer_exclusion_proved": False,
        },
        "self_attested": True,
        "approver_kind": "user",
        "approver_label": "repository-maintainer",
        "reviewer_identity_authenticated": False,
        "cryptographic_signature_verified": False,
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"d118approval_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d118_preflight(
    receipt: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
    protected_pre: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_d117_context(repo)
    protected = dict(protected_pre) if protected_pre is not None else _protected_state(repo)
    isolation = _isolation_profile()
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "external-source-metadata-snapshot-and-hash-preflight",
        "recorded_at": PREFLIGHT_RECORDED_AT,
        "approval_receipt": _output_binding(DEFAULT_RECEIPT_PATH, receipt, id_field="receipt_id"),
        "d117_candidate": _artifact_binding(
            D117_CANDIDATE_PATH,
            payload=current["candidate"],
            content=current["candidate_content"],
            id_field="candidate_id",
        ),
        "d117_source_gate": _artifact_binding(
            D117_SOURCE_GATE_PATH,
            payload=current["gate"],
            content=current["gate_content"],
            id_field="gate_id",
        ),
        "source_request_plan": _source_request_plan(),
        "opaque_handling_contract": _opaque_handling_contract(),
        "membership_preflight_contract": _membership_contract(),
        "cutoff_preflight_contract": _cutoff_contract(),
        "isolation_profile": isolation,
        "isolation_profile_hash": sha256_text(canonical_json(isolation)),
        "protected_pre_state": protected,
        "evidence_boundary": {
            "source_family_metadata_researched_count": 3,
            "revision_pinned_source_candidate_count": 2,
            "successful_snapshot_download_command_count": 3,
            "superseded_snapshot_observation_count": 1,
            "exact_http_request_count": None,
            "http_request_count_instrumented": False,
            "opaque_bound_file_count": 6,
            "record_container_parse_count": 0,
            "record_field_issue_label_patch_test_or_oracle_read_count": 0,
            "pool_member_id_read_count": 0,
            "pool_selected_acquired_or_frozen_count": 0,
            "role_or_isolation_session_count": 0,
            "matcher_classifier_calibration_execution_count": 0,
            "retrieval_agent_provider_evaluator_call_count": 0,
            "added_model_cost_usd": 0,
        },
        "authority": _authority(),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "preflight_id": f"d118preflight_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _source_candidate_rows(external_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in external_state["files"]:
        by_source.setdefault(str(row["source_id"]), []).append(dict(row))
    membership_by_source = {row["source_id"]: row for row in _membership_contract()["rules"]}
    cutoff_by_source = {row["source_id"]: row for row in _cutoff_contract()["sources"]}
    rows = []
    for source in SOURCE_SPECS:
        source_id = source["source_id"]
        objects = by_source[source_id]
        rows.append(
            {
                "source_id": source_id,
                "priority": source["priority"],
                "benchmark_family": source["benchmark_family"],
                "publisher": source["publisher"],
                "official_repository_id": source["repository_id"],
                "development_role": source["development_role"],
                "exact_revision": source["revision"],
                "official_commit_url": source["official_commit_url"],
                "downloaded_opaque_objects": objects,
                "object_set_hash": sha256_text(canonical_json(objects)),
                "snapshot_hash_and_size_verified": True,
                "snapshot_body_decoded": False,
                "archive_extracted": False,
                "record_fields_read": [],
                "issue_or_task_record_read_count": 0,
                "membership_evidence": membership_by_source[source_id],
                "cutoff_evidence": cutoff_by_source[source_id],
                "provider_declared_member_count": source["provider_declared_member_count"],
                "verified_member_count": None,
                "provider_reports_gpg_verified_commit": source[
                    "provider_reports_gpg_verified_commit"
                ],
                "provider_revision_membership_and_badge_claim_evidence_kind": (
                    "source-level-web-research-self-attested-not-rebuilt-from-bound-inputs"
                ),
                "provider_tree_or_signature_proof_bound_in_pack": False,
                "signature_payload_and_key_verified_locally": False,
                "license_claim_scope": source["dataset_license_claim_scope"],
                "upstream_issue_content_relicensed": source["upstream_issue_content_relicensed"],
                "lineage_overlap_with_existing_tasks_checked": False,
                "public_only_sanitized_projection_created": False,
                "pool_selected_acquired_or_frozen": False,
                "post_hoc": True,
                "independent": False,
                "eligible_for_independent_calibration": False,
                "disposition": "BLOCKED_INSUFFICIENT_PREEXISTENCE",
                "reason_codes": [
                    "TRUSTED_CUTOFF_ANCHOR_MISSING",
                    "MEMBERSHIP_RULE_NOT_TRUSTED_TIME_BOUND",
                    "SOURCE_SELECTION_NOT_PRECOMMITTED_BEFORE_D116",
                    "ISOLATION_PROFILE_NOT_EXECUTED",
                    "LINEAGE_OVERLAP_NOT_CHECKED",
                ],
            }
        )
    return rows


def build_d118_evidence_pack(
    receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    external_pre: Mapping[str, Any],
    external_post: Mapping[str, Any],
    protected_pre: Mapping[str, Any],
    protected_post: Mapping[str, Any],
) -> dict[str, Any]:
    _require(protected_pre == protected_post, "D-118 protected inputs changed during evidence prep")
    _require(
        external_pre == external_post,
        "D-118 opaque external objects changed during evidence prep",
    )
    _require(
        external_pre == _expected_external_object_state(),
        "D-118 opaque external object state is not the sealed expected set",
    )
    source_candidates = _source_candidate_rows(external_pre)
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "sanitized-external-source-evidence-pack-not-a-pool",
        "recorded_at": EVIDENCE_PACK_RECORDED_AT,
        "approval_receipt": _output_binding(DEFAULT_RECEIPT_PATH, receipt, id_field="receipt_id"),
        "preflight": _output_binding(DEFAULT_PREFLIGHT_PATH, preflight, id_field="preflight_id"),
        "research_summary": {
            "official_source_families_considered": 3,
            "revision_pinned_snapshots_bound": 2,
            "preferred_provisional_source_id": "swe-bench-dev-f5351",
            "preferred_is_not_admitted_or_selected": True,
            "preference_reason": (
                "official-dev-split-smaller-surface-same-exact-shard-as-observed-source"
            ),
            "terminal_bench_excluded_before_download": True,
            "actual_pool_or_independent_control_count": 0,
        },
        "source_candidates": source_candidates,
        "rejected_sources": [dict(row) for row in REJECTED_SOURCE_SPECS],
        "download_observation": {
            "successful_revision_pinned_download_command_count": 3,
            "download_command_count_evidence_kind": "current-process-self-attested",
            "final_bound_snapshot_count": 2,
            "superseded_swe_bench_e48e_snapshot_count": 1,
            "final_bound_file_count": external_pre["file_count"],
            "final_bound_file_bytes": external_pre["total_bytes"],
            "exact_transport_http_request_count": None,
            "transport_http_request_count_instrumented": False,
            "automatic_transport_retry_count": None,
            "execution_time_append_only_network_journal_present": False,
            "historical_no_record_read_claim_evidence_kind": (
                "current-process-source-path-self-attested"
            ),
            "d118_module_record_parser_or_decoder_call_count": 0,
            "local_download_time_used_as_cutoff_proof": False,
            "raw_response_or_record_value_logged": False,
        },
        "aggregate_disposition": {
            "status": "BLOCKED_INSUFFICIENT_PREEXISTENCE",
            "snapshot_hashes_verified_during_d118_materialization": True,
            "exhaustive_development_split_rules_provider_reported_content_bound": True,
            "provider_tree_or_membership_proof_rebuilt_from_bound_inputs": False,
            "trusted_cutoff_anchor_verified": False,
            "technical_isolation_verified": False,
            "post_hoc": True,
            "independent": False,
            "eligible_for_independent_calibration": False,
            "execution_authorization_candidate_ready": False,
        },
        "unresolved_prerequisites": [
            "trusted-pre-d116-anchor-binding-exact-snapshot-and-membership-rule",
            "externally-precommitted-source-selection-or-explicit-post-hoc-fallback",
            "immutable-isolation-image-digest",
            "executed-isolation-negative-probes",
            "leak-safe-lineage-overlap-check-under-separate-authorization",
            "separate-exact-d118-evidence-triple-user-review-before-any-next-candidate",
        ],
        "protected_pre_state": dict(protected_pre),
        "protected_post_state": dict(protected_post),
        "protected_fingerprints_equal": True,
        "external_object_pre_state": dict(external_pre),
        "external_object_post_state": dict(external_post),
        "external_object_fingerprints_equal": True,
        "evidence_boundary": dict(preflight["semantic_body"]["evidence_boundary"]),
        "authority": _authority(),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
        "evidence_pack_id": f"d118evidencepack_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def build_d118_source_gate(
    receipt: Mapping[str, Any],
    preflight: Mapping[str, Any],
    evidence_pack: Mapping[str, Any],
    *,
    repository: str | Path | None = None,
    context: Mapping[str, Any] | None = None,
    implementation_pre: Mapping[str, Any],
    implementation_post: Mapping[str, Any],
) -> dict[str, Any]:
    repo = _repo_root(repository)
    current = dict(context) if context is not None else _load_exact_d117_context(repo)
    _require(
        implementation_pre == implementation_post,
        "D-118 implementation changed during evidence prep",
    )
    authority = evidence_pack["semantic_body"]["authority"]
    _require(authority == _authority(), "D-118 evidence-pack authority expanded")
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "blocked-external-source-evidence-source-gate",
        "recorded_at": SOURCE_GATE_RECORDED_AT,
        "approval_receipt": _output_binding(DEFAULT_RECEIPT_PATH, receipt, id_field="receipt_id"),
        "d117_candidate": _artifact_binding(
            D117_CANDIDATE_PATH,
            payload=current["candidate"],
            content=current["candidate_content"],
            id_field="candidate_id",
        ),
        "d117_source_gate": _artifact_binding(
            D117_SOURCE_GATE_PATH,
            payload=current["gate"],
            content=current["gate_content"],
            id_field="gate_id",
        ),
        "preflight": _output_binding(DEFAULT_PREFLIGHT_PATH, preflight, id_field="preflight_id"),
        "evidence_pack": _output_binding(
            DEFAULT_EVIDENCE_PACK_PATH, evidence_pack, id_field="evidence_pack_id"
        ),
        "implementation_files": implementation_pre["files"],
        "protected_input_integrity": {
            "protected_pre": evidence_pack["semantic_body"]["protected_pre_state"],
            "protected_post": evidence_pack["semantic_body"]["protected_post_state"],
            "protected_fingerprints_equal": True,
            "external_object_pre": evidence_pack["semantic_body"]["external_object_pre_state"],
            "external_object_post": evidence_pack["semantic_body"]["external_object_post_state"],
            "external_object_fingerprints_equal": True,
            "implementation_pre": dict(implementation_pre),
            "implementation_post": dict(implementation_post),
            "implementation_fingerprints_equal": True,
        },
        "qualification": {
            "exact_d117_user_candidate_triple_bound": True,
            "exact_d117_source_gate_and_next_action_hash_validated": True,
            "d117_proposed_next_action_authorized_or_consumed": False,
            "external_triples_prerequisite_satisfied": False,
            "two_expected_revision_pinned_opaque_file_sets_hashed": True,
            "provider_revision_membership_proof_rebuilt_from_bound_inputs": False,
            "d118_module_source_path_has_no_record_parser_or_decoder": True,
            "historical_download_no_record_read_claim_is_self_attested": True,
            "d118_module_record_parser_or_decoder_call_count": 0,
            "provider_reports_public_development_split_rule_content_binding": True,
            "public_development_split_rule_binding_verified_from_bound_inputs": False,
            "provider_gpg_badge_not_promoted_to_trusted_timestamp": True,
            "trusted_pre_d116_anchor_verified": False,
            "technical_isolation_verified": False,
            "pool_selected_acquired_or_frozen": False,
            "independent_positive_count": 0,
            "execution_authorization_candidate_ready": False,
            "matcher_classifier_calibration_retrieval_agent_or_core_executed": False,
            "exact_d117_external_and_d118_implementation_inputs_unchanged": True,
        },
        "evidence_boundary": dict(evidence_pack["semantic_body"]["evidence_boundary"]),
        "authority": dict(authority),
        "next_gate": (
            "obtain-trusted-pre-d116-anchor-and-executed-isolation-proof-before-"
            "any-d118-execution-authorization-candidate"
        ),
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": SOURCE_GATE_SCHEMA_VERSION,
        "gate_id": f"d118_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), f"D-118 {label} timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D118ExternalEvidenceError(f"D-118 {label} timestamp is invalid") from exc
    _require(parsed.tzinfo is not None, f"D-118 {label} timestamp must be timezone-aware")
    return parsed


def _validate_chronology(*payloads: Mapping[str, Any]) -> None:
    times = [
        _parse_time(payload["semantic_body"]["recorded_at"], label=f"artifact {index}")
        for index, payload in enumerate(payloads, start=1)
    ]
    _require(
        all(left < right for left, right in pairwise(times)),
        "D-118 artifact chronology must be strictly increasing",
    )


def _validate_path_sets_disjoint(repository: Path) -> None:
    groups: list[tuple[str, Path]] = []
    groups.extend(("protected", Path(spec["path"])) for spec in PROTECTED_FILE_SPECS)
    groups.extend(("implementation", path) for path in D118_IMPLEMENTATION_PATHS)
    groups.extend(
        ("external", Path(spec["path"])) for spec in _expected_external_object_state()["files"]
    )
    groups.extend(
        ("output", path)
        for path in (
            DEFAULT_RECEIPT_PATH,
            DEFAULT_PREFLIGHT_PATH,
            DEFAULT_EVIDENCE_PACK_PATH,
            DEFAULT_SOURCE_GATE_PATH,
        )
    )
    folded: dict[str, tuple[str, Path]] = {}
    identities: dict[tuple[int, int], tuple[str, Path]] = {}
    for kind, relative in groups:
        key = relative.as_posix().casefold()
        _require(key not in folded, f"D-118 casefold path collision: {relative}")
        folded[key] = (kind, relative)
        selected = _resolved(
            relative,
            repository=repository,
            label=f"{kind} collision check",
            must_exist=False,
        )
        if not selected.exists():
            continue
        identity = (selected.stat().st_dev, selected.stat().st_ino)
        _require(identity not in identities, f"D-118 hardlink/inode collision: {relative}")
        identities[identity] = (kind, relative)


def _write_exact(path: Path, content: bytes, *, repository: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not _is_linklike(path.parent), "D-118 output parent cannot be linked")
    if path.exists():
        existing = _read_stable_bytes(path, label="existing output")
        _require(existing == content, "D-118 existing output differs from deterministic rebuild")
        return
    parent_before = path.parent.stat()
    try:
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise D118ExternalEvidenceError("D-118 output exclusive-create failed") from exc
    parent_after = path.parent.stat()
    _require(
        (parent_before.st_dev, parent_before.st_ino) == (parent_after.st_dev, parent_after.st_ino),
        "D-118 output parent identity changed during create",
    )
    committed = _resolved(
        path.relative_to(repository),
        repository=repository,
        label="committed output",
    )
    _require(
        _read_stable_bytes(committed, label="committed output") == content,
        "D-118 output read-back mismatch",
    )


def _output_paths(repository: Path) -> tuple[Path, ...]:
    return tuple(
        _resolved(path, repository=repository, label="output", must_exist=False)
        for path in (
            DEFAULT_RECEIPT_PATH,
            DEFAULT_PREFLIGHT_PATH,
            DEFAULT_EVIDENCE_PACK_PATH,
            DEFAULT_SOURCE_GATE_PATH,
        )
    )


def _require_all_or_none_outputs(repository: Path) -> bool:
    paths = _output_paths(repository)
    existence = [path.exists() for path in paths]
    _require(
        not any(existence) or all(existence),
        "D-118 partial artifact set exists; no automatic repair or overwrite allowed",
    )
    return all(existence)


def _expected_artifacts(
    *, repository: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    context = _load_exact_d117_context(repository)
    protected = _protected_state(repository)
    implementation = _implementation_state(repository)
    external = _expected_external_object_state()
    receipt = build_d118_approval_receipt(repository=repository, context=context)
    preflight = build_d118_preflight(
        receipt,
        repository=repository,
        context=context,
        protected_pre=protected,
    )
    evidence_pack = build_d118_evidence_pack(
        receipt,
        preflight,
        external_pre=external,
        external_post=external,
        protected_pre=protected,
        protected_post=protected,
    )
    gate = build_d118_source_gate(
        receipt,
        preflight,
        evidence_pack,
        repository=repository,
        context=context,
        implementation_pre=implementation,
        implementation_post=implementation,
    )
    return receipt, preflight, evidence_pack, gate


def _validate_artifact(
    path: Path,
    *,
    repository: Path,
    root_keys: Sequence[str],
    body_keys: Sequence[str],
    id_field: str,
    id_prefix: str,
    schema_version: str,
    label: str,
    expected: Mapping[str, Any],
) -> dict[str, Any]:
    selected = _resolved(path, repository=repository, label=label)
    content = _read_stable_bytes(selected, label=label)
    try:
        parsed = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D118ExternalEvidenceError(f"D-118 {label} is not valid JSON") from exc
    _require(isinstance(parsed, dict), f"D-118 {label} root must be an object")
    _validate_envelope(
        parsed,
        root_keys=root_keys,
        body_keys=body_keys,
        id_field=id_field,
        id_prefix=id_prefix,
        schema_version=schema_version,
        label=label,
    )
    _require(parsed == expected, f"D-118 {label} full expected payload mismatch")
    _require(content == _pretty_json(expected), f"D-118 {label} canonical bytes drifted")
    return parsed


def validate_d118_artifacts(
    *,
    repository: str | Path | None = None,
    mode: str = "sealed-historical",
) -> dict[str, Any]:
    repo = _repo_root(repository)
    _require(
        mode in {"sealed-historical", "current-object"},
        "D-118 validation mode must be sealed-historical or current-object",
    )
    _validate_path_sets_disjoint(repo)
    _require_all_or_none_outputs(repo)
    expected = _expected_artifacts(repository=repo)
    receipt = _validate_artifact(
        DEFAULT_RECEIPT_PATH,
        repository=repo,
        root_keys=RECEIPT_ROOT_KEYS,
        body_keys=RECEIPT_BODY_KEYS,
        id_field="receipt_id",
        id_prefix="d118approval_",
        schema_version=RECEIPT_SCHEMA_VERSION,
        label="approval receipt",
        expected=expected[0],
    )
    preflight = _validate_artifact(
        DEFAULT_PREFLIGHT_PATH,
        repository=repo,
        root_keys=PREFLIGHT_ROOT_KEYS,
        body_keys=PREFLIGHT_BODY_KEYS,
        id_field="preflight_id",
        id_prefix="d118preflight_",
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        label="preflight",
        expected=expected[1],
    )
    evidence_pack = _validate_artifact(
        DEFAULT_EVIDENCE_PACK_PATH,
        repository=repo,
        root_keys=EVIDENCE_PACK_ROOT_KEYS,
        body_keys=EVIDENCE_PACK_BODY_KEYS,
        id_field="evidence_pack_id",
        id_prefix="d118evidencepack_",
        schema_version=EVIDENCE_PACK_SCHEMA_VERSION,
        label="evidence pack",
        expected=expected[2],
    )
    gate = _validate_artifact(
        DEFAULT_SOURCE_GATE_PATH,
        repository=repo,
        root_keys=GATE_ROOT_KEYS,
        body_keys=GATE_BODY_KEYS,
        id_field="gate_id",
        id_prefix="d118_",
        schema_version=SOURCE_GATE_SCHEMA_VERSION,
        label="source gate",
        expected=expected[3],
    )
    _validate_chronology(receipt, preflight, evidence_pack, gate)
    _require(
        gate["semantic_body"]["authority"] == _authority()
        and gate["semantic_body"]["qualification"]["trusted_pre_d116_anchor_verified"] is False
        and gate["semantic_body"]["qualification"]["execution_authorization_candidate_ready"]
        is False,
        "D-118 source gate overclaims readiness",
    )
    current_objects_reverified = mode == "current-object"
    if current_objects_reverified:
        _require(
            observe_external_objects(repository=repo) == _expected_external_object_state(),
            "D-118 local external-object revalidation failed",
        )
    gate_bytes = _pretty_json(gate)
    pack_bytes = _pretty_json(evidence_pack)
    return {
        "receipt_id": receipt["receipt_id"],
        "preflight_id": preflight["preflight_id"],
        "evidence_pack_id": evidence_pack["evidence_pack_id"],
        "evidence_pack_semantic_body_hash": evidence_pack["semantic_body_hash"],
        "evidence_pack_file_bytes": len(pack_bytes),
        "evidence_pack_file_sha256": sha256_bytes(pack_bytes),
        "gate_id": gate["gate_id"],
        "gate_semantic_body_hash": gate["semantic_body_hash"],
        "gate_file_bytes": len(gate_bytes),
        "gate_file_sha256": sha256_bytes(gate_bytes),
        "aggregate_disposition": evidence_pack["semantic_body"]["aggregate_disposition"]["status"],
        "validation_mode": mode,
        "sealed_historical_pack_validated": True,
        "current_external_objects_reverified": current_objects_reverified,
        "trusted_cutoff_anchor_verified": False,
        "execution_authorization_candidate_ready": False,
        "record_read_count": 0,
        "matcher_classifier_calibration_execution_count": 0,
        "retrieval_agent_provider_evaluator_call_count": 0,
    }


def run_d118_external_source_evidence(*, repository: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repository)
    _validate_path_sets_disjoint(repo)
    complete_preexists = _require_all_or_none_outputs(repo)
    context = _load_exact_d117_context(repo)
    protected_pre = _protected_state(repo)
    implementation_pre = _implementation_state(repo)
    external_pre = observe_external_objects(repository=repo)
    receipt = build_d118_approval_receipt(repository=repo, context=context)
    preflight = build_d118_preflight(
        receipt,
        repository=repo,
        context=context,
        protected_pre=protected_pre,
    )
    protected_post = _protected_state(repo)
    external_post = observe_external_objects(repository=repo)
    evidence_pack = build_d118_evidence_pack(
        receipt,
        preflight,
        external_pre=external_pre,
        external_post=external_post,
        protected_pre=protected_pre,
        protected_post=protected_post,
    )
    implementation_post = _implementation_state(repo)
    gate = build_d118_source_gate(
        receipt,
        preflight,
        evidence_pack,
        repository=repo,
        context=context,
        implementation_pre=implementation_pre,
        implementation_post=implementation_post,
    )
    for relative, payload in (
        (DEFAULT_RECEIPT_PATH, receipt),
        (DEFAULT_PREFLIGHT_PATH, preflight),
        (DEFAULT_EVIDENCE_PACK_PATH, evidence_pack),
        (DEFAULT_SOURCE_GATE_PATH, gate),
    ):
        selected = _resolved(relative, repository=repo, label="output", must_exist=False)
        _write_exact(selected, _pretty_json(payload), repository=repo)
    result = validate_d118_artifacts(repository=repo, mode="current-object")
    return {**result, "complete_exact_set_preexisted": complete_preexists}
