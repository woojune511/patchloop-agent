"""D-103 exact candidate approval and narrow admission evidence.

This module validates the exact D-102 decision candidate, the maintainer's
self-attested approval receipt, and the live-journal-bound admission seal.  The
seal admits three reviewed rule templates for source materialization only.  It
does not authorize index build/freeze, a core campaign, or comparative
analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.memory import d101_group_admission as d101
from patchloop.memory import d102_maintainer_assisted_decisions as d102
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

GATE_SCHEMA_VERSION = "exact-candidate-admission-gate-d103-v1"
GATE_RECORDED_AT = "2026-08-06T03:00:00Z"

DEFAULT_D102_GATE_PATH = Path(
    "reports/memory-development/d102-maintainer-assisted-decision-candidate-gate.json"
)
EXPECTED_D102_GATE_BYTES = 5_453
EXPECTED_D102_GATE_FILE_SHA = (
    "sha256:e8ff1cdecdb7b107593f43f0b68b564abab34668558a0bb367296e16fbcca373"
)
EXPECTED_D102_GATE_BODY_SHA = (
    "sha256:27e6b50c156e2c590e4225302534c5fedca67596eae2c831d03d3a4810c11732"
)

DEFAULT_RECEIPT_PATH = Path("reports/memory-development/d103-exact-candidate-approval-receipt.json")
EXPECTED_RECEIPT_BYTES = 6_245
EXPECTED_RECEIPT_FILE_SHA = (
    "sha256:dad12cf181fee8e113d9da703795eb8ccb4a16be6014218ea923a919d0695031"
)
EXPECTED_RECEIPT_ID = "d101receipt_23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a"
EXPECTED_RECEIPT_BODY_SHA = (
    "sha256:23c8ff9b5f8b91820d03a25242abaa02f1ec2af0357bd9b26c227882cf8f5f7a"
)
EXPECTED_APPROVAL_ACTION_ID = "d103-exact-candidate-approval-1"
EXPECTED_APPROVER_KIND = "human"
EXPECTED_APPROVER_LABEL = "chat-maintainer-self-attested"
EXPECTED_APPROVAL_REFERENCE = "user-message:d103-exact-candidate-approval"
EXPECTED_RATIONALE_SHA = "sha256:45bb5e03fb1592baa68381646b9549eeb46c030a9a6e28e8006a03386dae016d"
EXPECTED_APPROVAL_STATEMENT = (
    "EXPLICITLY_APPROVE_EXACT_D101_CANDIDATE "
    "d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d "
    "sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d "
    "sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457"
)

DEFAULT_SEAL_PATH = Path("reports/memory-development/d103-maintainer-assisted-admission-seal.json")
EXPECTED_SEAL_BYTES = 19_357
EXPECTED_SEAL_FILE_SHA = "sha256:af1e6ea8811445f26d542f34500d1a7b3919392bef00c98b71f4c26ded236e8e"
EXPECTED_SEAL_ID = "d101seal_3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e"
EXPECTED_SEAL_BODY_SHA = "sha256:3dc67e77a0c8c2d9a94f6bea9138d179eb6d6ac1cda0d8b490a1eab3bfbe705e"

DEFAULT_GATE_PATH = Path("reports/memory-development/d103-exact-candidate-admission-gate.json")
SOURCE_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d103_exact_candidate_admission.py"),
    Path("scripts/build_d103_exact_candidate_admission_gate.py"),
    Path("tests/test_d103_exact_candidate_admission.py"),
)

EXPECTED_ADMITTED_GROUPS = (
    {
        "semantic_group_id": "platform-emulation-matrix-gap",
        "proposed_memory_id": "memgrp_649483b80292fea26e4009ebdb72df31",
        "template_hash": (
            "sha256:844290fa8eab2ff0d2c0541f224c17cb61ced74c27f7861b04ee4bdfae081060"
        ),
    },
    {
        "semantic_group_id": "request-context-propagation-gap",
        "proposed_memory_id": "memgrp_b421547d481faabf9be3511217258de5",
        "template_hash": (
            "sha256:91e444444d313e92b857fdbf871802da9fdc57fc50a71ec0ba5c462626432593"
        ),
    },
    {
        "semantic_group_id": "exception-origin-state-conflation",
        "proposed_memory_id": "memgrp_5a23f463cba43bf3ba395f67cf976047",
        "template_hash": (
            "sha256:5a8e661e092e50e72bf8aa6456e9a5996fcd94503dcf4275a0be60579762ce8a"
        ),
    },
)
EXPECTED_HELD_GROUPS = (
    "interrupt-lifecycle-unresolved",
    "diagnostic-contract-unresolved",
)
EXPECTED_SEAL_AUTHORITY = {
    "admission_snapshot_sealed": True,
    "decision_coverage_complete": True,
    "explicit_approval_receipt_validated": True,
    "reviewer_identity_authenticated": False,
    "cryptographic_signature_verified": False,
    "open_hold_group_count": 2,
    "group_review_finalized": False,
    "admitted_memory_rule_count": 3,
    "memory_admission_unlocked": True,
    "memory_index_source_authoring_unlocked": True,
    "memory_index_build_authorized": False,
    "memory_index_built": False,
    "memory_index_frozen": False,
    "core_campaign_unlocked": False,
    "analysis_ready": False,
    "provider_calls_made": 0,
    "evaluator_calls_made": 0,
    "added_model_cost_usd": 0,
}


class D103ExactAdmissionError(ContractError):
    """Stable fail-closed error for the D-103 admission boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D103ExactAdmissionError(message)


def _repo_root(repository: str | Path | None) -> Path:
    return Path(repository).resolve() if repository is not None else repository_root().resolve()


def _resolved(path: str | Path, *, repository: Path) -> Path:
    selected = Path(path)
    return selected.resolve() if selected.is_absolute() else (repository / selected).resolve()


def _read_exact(
    path: str | Path,
    *,
    repository: Path,
    expected_bytes: int,
    expected_sha256: str,
    label: str,
) -> tuple[Path, bytes]:
    selected = _resolved(path, repository=repository)
    try:
        content = selected.read_bytes()
    except OSError as exc:
        raise D103ExactAdmissionError(f"D-103 {label} is unavailable") from exc
    _require(len(content) == expected_bytes, f"D-103 {label} byte count drifted")
    _require(sha256_bytes(content) == expected_sha256, f"D-103 {label} file hash drifted")
    return selected, content


def _parse_json(content: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D103ExactAdmissionError(f"D-103 {label} JSON is invalid") from exc
    _require(isinstance(payload, dict), f"D-103 {label} JSON root is invalid")
    return payload


def _source_binding(path: Path, *, repository: Path) -> dict[str, Any]:
    selected = _resolved(path, repository=repository)
    try:
        content = selected.read_bytes()
    except OSError as exc:
        raise D103ExactAdmissionError("D-103 source implementation is unavailable") from exc
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def validate_d103_exact_admission(
    *,
    repository: str | Path | None = None,
    d102_gate_path: str | Path = DEFAULT_D102_GATE_PATH,
    receipt_path: str | Path = DEFAULT_RECEIPT_PATH,
    seal_path: str | Path = DEFAULT_SEAL_PATH,
) -> dict[str, Any]:
    """Validate the exact approval receipt and its narrow admission seal."""

    repo = _repo_root(repository)
    d102_gate, d102_content = _read_exact(
        d102_gate_path,
        repository=repo,
        expected_bytes=EXPECTED_D102_GATE_BYTES,
        expected_sha256=EXPECTED_D102_GATE_FILE_SHA,
        label="D-102 source gate",
    )
    d102_result = d102.validate_d102_decision_candidate_gate(
        d102_gate,
        repository=repo,
    )
    _require(
        d102_result["semantic_body_hash"] == EXPECTED_D102_GATE_BODY_SHA,
        "D-103 D-102 source gate body identity drifted",
    )
    _require(
        d102_result["candidate_id"] == d102.EXPECTED_CANDIDATE_ID,
        "D-103 candidate identity drifted",
    )

    receipt, receipt_content = _read_exact(
        receipt_path,
        repository=repo,
        expected_bytes=EXPECTED_RECEIPT_BYTES,
        expected_sha256=EXPECTED_RECEIPT_FILE_SHA,
        label="approval receipt",
    )
    receipt_result = d101.validate_d101_approval_receipt(
        receipt,
        d102.DEFAULT_CANDIDATE_PATH,
        repository=repo,
        expected_receipt_file_sha256=EXPECTED_RECEIPT_FILE_SHA,
    )
    _require(
        receipt_result["receipt_id"] == EXPECTED_RECEIPT_ID
        and receipt_result["semantic_body_hash"] == EXPECTED_RECEIPT_BODY_SHA,
        "D-103 approval receipt identity drifted",
    )
    receipt_payload = _parse_json(receipt_content, label="approval receipt")
    receipt_body = receipt_payload["semantic_body"]
    _require(
        receipt_body["approval_action_id"] == EXPECTED_APPROVAL_ACTION_ID
        and receipt_body["approver_kind"] == EXPECTED_APPROVER_KIND
        and receipt_body["approver_label"] == EXPECTED_APPROVER_LABEL
        and receipt_body["approval_reference"] == EXPECTED_APPROVAL_REFERENCE,
        "D-103 explicit approval provenance drifted",
    )
    _require(
        sha256_text(receipt_body["rationale"]) == EXPECTED_RATIONALE_SHA,
        "D-103 approval rationale drifted",
    )
    _require(
        receipt_body["approval_statement"] == EXPECTED_APPROVAL_STATEMENT,
        "D-103 explicit approval statement drifted",
    )
    _require(
        receipt_body["explicit_approval_receipt_recorded"] is True
        and receipt_body["reviewer_identity_authenticated"] is False
        and receipt_body["cryptographic_signature_verified"] is False,
        "D-103 receipt attestation boundary drifted",
    )

    seal, seal_content = _read_exact(
        seal_path,
        repository=repo,
        expected_bytes=EXPECTED_SEAL_BYTES,
        expected_sha256=EXPECTED_SEAL_FILE_SHA,
        label="admission seal",
    )
    seal_result = d101.validate_d101_admission_seal(
        seal,
        d102.DEFAULT_CANDIDATE_PATH,
        receipt,
        d102.DEFAULT_JOURNAL_PATH,
        repository=repo,
        expected_seal_file_sha256=EXPECTED_SEAL_FILE_SHA,
    )
    _require(
        seal_result["seal_id"] == EXPECTED_SEAL_ID
        and seal_result["semantic_body_hash"] == EXPECTED_SEAL_BODY_SHA,
        "D-103 admission seal identity drifted",
    )
    seal_payload = _parse_json(seal_content, label="admission seal")
    seal_body = seal_payload["semantic_body"]
    _require(
        seal_body["authority"] == EXPECTED_SEAL_AUTHORITY,
        "D-103 seal authority widened or drifted",
    )
    _require(
        seal_body["next_gate"] == "group-aware-memory-source-materialization-and-render-policy",
        "D-103 seal next gate drifted",
    )
    admitted_groups = [
        {
            "semantic_group_id": entry["provenance"]["semantic_group_id"],
            "proposed_memory_id": entry["template"]["proposed_memory_id"],
            "template_hash": entry["template_hash"],
        }
        for entry in seal_body["admitted_entries"]
    ]
    _require(
        admitted_groups == list(EXPECTED_ADMITTED_GROUPS),
        "D-103 admitted rule template identities drifted",
    )
    held_groups = [
        decision["semantic_group_id"]
        for decision in seal_body["effective_decisions"]
        if decision["decision"] == "continue_hold"
    ]
    _require(held_groups == list(EXPECTED_HELD_GROUPS), "D-103 held groups drifted")

    return {
        "d102_gate": {
            "path": d102_gate.relative_to(repo).as_posix(),
            "semantic_body_hash": d102_result["semantic_body_hash"],
            "file_bytes": len(d102_content),
            "file_sha256": sha256_bytes(d102_content),
        },
        "candidate": {
            "candidate_id": d102_result["candidate_id"],
            "semantic_body_hash": d102.EXPECTED_CANDIDATE_BODY_SHA,
            "file_bytes": d102.EXPECTED_CANDIDATE_BYTES,
            "file_sha256": d102.EXPECTED_CANDIDATE_FILE_SHA,
        },
        "approval_receipt": {
            "path": receipt.relative_to(repo).as_posix(),
            "receipt_id": receipt_result["receipt_id"],
            "semantic_body_hash": receipt_result["semantic_body_hash"],
            "file_bytes": len(receipt_content),
            "file_sha256": sha256_bytes(receipt_content),
            "approval_action_id": receipt_body["approval_action_id"],
            "approver_kind": receipt_body["approver_kind"],
            "approver_label": receipt_body["approver_label"],
            "approval_reference": receipt_body["approval_reference"],
            "rationale_sha256": sha256_text(receipt_body["rationale"]),
            "approval_statement": receipt_body["approval_statement"],
            "self_attested": True,
            "reviewer_identity_authenticated": False,
            "cryptographic_signature_verified": False,
        },
        "admission_seal": {
            "path": seal.relative_to(repo).as_posix(),
            "seal_id": seal_result["seal_id"],
            "semantic_body_hash": seal_result["semantic_body_hash"],
            "file_bytes": len(seal_content),
            "file_sha256": sha256_bytes(seal_content),
        },
        "admitted_groups": admitted_groups,
        "held_groups": held_groups,
    }


def build_d103_exact_admission_gate(
    *,
    repository: str | Path | None = None,
    d102_gate_path: str | Path = DEFAULT_D102_GATE_PATH,
    receipt_path: str | Path = DEFAULT_RECEIPT_PATH,
    seal_path: str | Path = DEFAULT_SEAL_PATH,
) -> dict[str, Any]:
    """Build deterministic portable D-103 evidence without index authority."""

    repo = _repo_root(repository)
    evidence = validate_d103_exact_admission(
        repository=repo,
        d102_gate_path=d102_gate_path,
        receipt_path=receipt_path,
        seal_path=seal_path,
    )
    body = {
        "milestone": "D-103",
        "evidence_kind": "exact-candidate-approval-and-admission-seal-gate",
        "recorded_at": GATE_RECORDED_AT,
        **evidence,
        "source_files": [
            _source_binding(path, repository=repo) for path in SOURCE_IMPLEMENTATION_PATHS
        ],
        "authority": {
            "exact_candidate_approved": True,
            "approval_receipt_present": True,
            "approval_receipt_self_attested": True,
            "reviewer_identity_authenticated": False,
            "cryptographic_signature_verified": False,
            "admission_seal_created": True,
            "admission_snapshot_sealed": True,
            "decision_coverage_complete": True,
            "open_hold_group_count": 2,
            "full_five_group_review_finalized": False,
            "admitted_memory_rule_count": 3,
            "memory_entry_source_materialized_count": 0,
            "memory_admission_unlocked": True,
            "memory_index_source_authoring_unlocked": True,
            "memory_index_build_authorized": False,
            "memory_index_built": False,
            "memory_index_frozen": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": "exact-three-rule-source-materialization-leak-scan-and-validation",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "gate_id": f"d103_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def encode_d103_gate(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_d103_exact_admission_gate(
    gate_path: str | Path = DEFAULT_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Rebuild and exact-compare the checked-in D-103 admission gate."""

    repo = _repo_root(repository)
    selected = _resolved(gate_path, repository=repo)
    try:
        content = selected.read_bytes()
        parsed = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise D103ExactAdmissionError("D-103 gate is invalid") from exc
    expected = build_d103_exact_admission_gate(repository=repo)
    expected_content = encode_d103_gate(expected)
    _require(content == expected_content, "D-103 gate exact bytes drifted")
    _require(parsed == expected, "D-103 gate semantic content drifted")
    body = expected["semantic_body"]
    authority = body["authority"]
    return {
        "ok": True,
        "schema_version": expected["schema_version"],
        "gate_id": expected["gate_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "gate_file_bytes": len(content),
        "gate_file_sha256": sha256_bytes(content),
        "candidate_id": body["candidate"]["candidate_id"],
        "receipt_id": body["approval_receipt"]["receipt_id"],
        "seal_id": body["admission_seal"]["seal_id"],
        "admitted_memory_rule_count": authority["admitted_memory_rule_count"],
        "open_hold_group_count": authority["open_hold_group_count"],
        "memory_index_source_authoring_unlocked": authority[
            "memory_index_source_authoring_unlocked"
        ],
        "memory_index_build_authorized": authority["memory_index_build_authorized"],
        "core_campaign_unlocked": authority["core_campaign_unlocked"],
        "gate_validation": "pass",
    }
