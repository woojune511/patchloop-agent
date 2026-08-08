"""D-102 exact maintainer-assisted decisions and candidate evidence.

This module seals the narrow state created after the maintainer confirmed the
system recommendation for all five D-101 review items.  It validates the live
append-only decision journal and the still-unapproved D-101 candidate.  It does
not create an approval receipt, an admission seal, a MemoryEntry, an index, or
any experiment authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import D100GroupDecisionRecord
from patchloop.errors import ContractError
from patchloop.memory import d100_group_admission as d100
from patchloop.memory import d101_group_admission as d101
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

GATE_SCHEMA_VERSION = "maintainer-assisted-decision-candidate-gate-d102-v1"
GATE_RECORDED_AT = "2026-08-06T02:22:00Z"

DEFAULT_JOURNAL_PATH = Path(
    "reports/memory-development/d102-maintainer-assisted-group-decisions.jsonl"
)
EXPECTED_JOURNAL_BYTES = 7_829
EXPECTED_JOURNAL_FILE_SHA = (
    "sha256:5c46e6b6a49e436794c1b118f96a9d05caa48a4cd4199e9791ec2ec4499327e3"
)
EXPECTED_JOURNAL_HEAD = "sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469"
EXPECTED_JOURNAL_RECORD_COUNT = 5

DEFAULT_CANDIDATE_PATH = Path(
    "reports/memory-development/d102-maintainer-assisted-admission-candidate.json"
)
EXPECTED_CANDIDATE_BYTES = 31_148
EXPECTED_CANDIDATE_FILE_SHA = (
    "sha256:9620e99961010bc4c942728f1948cb50b3f067025b8d5a02ba579dd3a1b4e457"
)
EXPECTED_CANDIDATE_ID = (
    "d101candidate_97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d"
)
EXPECTED_CANDIDATE_BODY_SHA = (
    "sha256:97c0d2499e2ffab97df6050b84af7c1d455e4af631a3e0fb58d50a084a62ac9d"
)

DEFAULT_GATE_PATH = Path(
    "reports/memory-development/d102-maintainer-assisted-decision-candidate-gate.json"
)
SOURCE_IMPLEMENTATION_PATHS = (
    Path("patchloop/memory/d102_maintainer_assisted_decisions.py"),
    Path("scripts/build_d102_maintainer_assisted_decision_gate.py"),
    Path("tests/test_d102_maintainer_assisted_decisions.py"),
)

EXPECTED_REVIEWER_KIND = "maintainer_assisted"
EXPECTED_REVIEWER = "maintainer-confirmed-system-recommendation"
EXPECTED_DECISIONS = (
    {
        "order": 1,
        "semantic_group_id": "platform-emulation-matrix-gap",
        "decision": "approve",
        "action_id": "d102-user-confirmed-recommendation-1",
        "rationale_sha256": (
            "sha256:2e24aac1e3be67c043411909041fa64e6a3368fa817a5306efa5a133408b9919"
        ),
        "decision_hash": (
            "sha256:9933f0f079ca2d40ebdbc1e2257e794b36ca05045d186c02785c1c00df92bfa3"
        ),
    },
    {
        "order": 2,
        "semantic_group_id": "request-context-propagation-gap",
        "decision": "approve",
        "action_id": "d102-user-confirmed-recommendation-2",
        "rationale_sha256": (
            "sha256:9bcca42d665c6dc60ea131242ecb756a1eb1fa67bca8d7e50d1928693a6abb07"
        ),
        "decision_hash": (
            "sha256:5943da335c469334e9fee94da46d26ffe7cea6a732c19c3dc97e3f4da718127d"
        ),
    },
    {
        "order": 3,
        "semantic_group_id": "interrupt-lifecycle-unresolved",
        "decision": "continue_hold",
        "action_id": "d102-user-confirmed-recommendation-3",
        "rationale_sha256": (
            "sha256:5b53369adbe4ee8812502f74db9a2699ce1294daecf96e908d2b8de7bc32167d"
        ),
        "decision_hash": (
            "sha256:bf5ea8618dc2b1868c89713bc4fdb8730264cc6be9612d5919f42e1f9382ae38"
        ),
    },
    {
        "order": 4,
        "semantic_group_id": "diagnostic-contract-unresolved",
        "decision": "continue_hold",
        "action_id": "d102-user-confirmed-recommendation-4",
        "rationale_sha256": (
            "sha256:4285439f8c0975b96ca8de0c6d556bead9c5158e8b4b5651832bcfc50f7e1008"
        ),
        "decision_hash": (
            "sha256:567bc94630404712732ee7437cfafdc6fba5d77cc70ff7f0c7e00343320800ae"
        ),
    },
    {
        "order": 5,
        "semantic_group_id": "exception-origin-state-conflation",
        "decision": "approve",
        "action_id": "d102-user-confirmed-recommendation-5",
        "rationale_sha256": (
            "sha256:d65c6aa1f9bc45770144042441ed09bdd5dcb3298ed6f925274930f223d87d65"
        ),
        "decision_hash": (
            "sha256:4192b503768093e2134b7651da4922fcd9d5c2a064e0150a7f523adc952ac469"
        ),
    },
)


class D102DecisionGateError(ContractError):
    """Stable fail-closed error for the D-102 evidence boundary."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D102DecisionGateError(message)


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
        raise D102DecisionGateError(f"D-102 {label} is unavailable") from exc
    _require(len(content) == expected_bytes, f"D-102 {label} byte count drifted")
    _require(
        sha256_bytes(content) == expected_sha256,
        f"D-102 {label} file hash drifted",
    )
    return selected, content


def _source_binding(path: Path, *, repository: Path) -> dict[str, Any]:
    selected = _resolved(path, repository=repository)
    try:
        content = selected.read_bytes()
    except OSError as exc:
        raise D102DecisionGateError("D-102 source implementation is unavailable") from exc
    return {
        "path": selected.relative_to(repository).as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _journal_records(content: bytes) -> list[D100GroupDecisionRecord]:
    try:
        return [
            D100GroupDecisionRecord.model_validate_json(line)
            for line in content.decode("utf-8").splitlines()
        ]
    except (UnicodeDecodeError, ValidationError) as exc:
        raise D102DecisionGateError("D-102 journal record parsing failed") from exc


def validate_d102_decision_candidate(
    *,
    repository: str | Path | None = None,
    journal_path: str | Path = DEFAULT_JOURNAL_PATH,
    candidate_path: str | Path = DEFAULT_CANDIDATE_PATH,
) -> dict[str, Any]:
    """Validate the exact five decisions and the still-unapproved candidate."""

    repo = _repo_root(repository)
    journal, journal_content = _read_exact(
        journal_path,
        repository=repo,
        expected_bytes=EXPECTED_JOURNAL_BYTES,
        expected_sha256=EXPECTED_JOURNAL_FILE_SHA,
        label="decision journal",
    )
    journal_result = d100.validate_d100_decision_journal(
        d100.DEFAULT_PROPOSAL_PATH,
        journal,
        repository=repo,
        expected_head=EXPECTED_JOURNAL_HEAD,
        expected_record_count=EXPECTED_JOURNAL_RECORD_COUNT,
    )
    _require(journal_result["complete_group_decisions"] is True, "D-102 decisions are incomplete")
    _require(journal_result["correction_count"] == 0, "D-102 decision corrections are unexpected")

    records = _journal_records(journal_content)
    _require(len(records) == len(EXPECTED_DECISIONS), "D-102 decision count drifted")
    decision_evidence: list[dict[str, Any]] = []
    for record, expected in zip(records, EXPECTED_DECISIONS, strict=True):
        _require(record.sequence == expected["order"], "D-102 decision order drifted")
        _require(
            record.semantic_group_id == expected["semantic_group_id"]
            and record.decision == expected["decision"]
            and record.action_id == expected["action_id"]
            and record.decision_hash == expected["decision_hash"],
            "D-102 exact decision identity drifted",
        )
        _require(
            record.reviewer_kind == EXPECTED_REVIEWER_KIND and record.reviewer == EXPECTED_REVIEWER,
            "D-102 maintainer-assisted provenance drifted",
        )
        rationale_sha = sha256_text(record.rationale)
        _require(
            rationale_sha == expected["rationale_sha256"],
            "D-102 system rationale binding drifted",
        )
        decision_evidence.append(
            {
                **expected,
                "reviewer_kind": record.reviewer_kind,
                "reviewer": record.reviewer,
            }
        )

    candidate, candidate_content = _read_exact(
        candidate_path,
        repository=repo,
        expected_bytes=EXPECTED_CANDIDATE_BYTES,
        expected_sha256=EXPECTED_CANDIDATE_FILE_SHA,
        label="admission candidate",
    )
    candidate_result = d101.validate_d101_admission_candidate(
        candidate,
        repository=repo,
        live_journal_path=journal,
        expected_candidate_file_sha256=EXPECTED_CANDIDATE_FILE_SHA,
    )
    _require(
        candidate_result["candidate_id"] == EXPECTED_CANDIDATE_ID
        and candidate_result["semantic_body_hash"] == EXPECTED_CANDIDATE_BODY_SHA,
        "D-102 candidate identity drifted",
    )
    _require(
        candidate_result["approved_group_count"] == 3
        and candidate_result["rejected_group_count"] == 0
        and candidate_result["continued_hold_group_count"] == 2,
        "D-102 candidate decision totals drifted",
    )
    _require(
        candidate_result["approval_receipt_present"] is False
        and candidate_result["memory_admission_unlocked"] is False
        and candidate_result["memory_index_build_authorized"] is False
        and candidate_result["core_campaign_unlocked"] is False,
        "D-102 candidate authority widened",
    )
    try:
        candidate_payload = json.loads(candidate_content)
    except json.JSONDecodeError as exc:
        raise D102DecisionGateError("D-102 candidate JSON is invalid") from exc
    body = candidate_payload["semantic_body"]
    preview = body["preview"]["semantic_body"]
    _require(len(preview["entries"]) == 3, "D-102 preview entry count drifted")
    _require(
        preview["authority"]["admitted_memory_rule_count"] == 0, "D-102 preview admitted rules"
    )
    _require(
        body["authority"]["explicit_candidate_approval_pending"] is True,
        "D-102 approval is not pending",
    )
    _require(body["authority"]["admission_seal_created"] is False, "D-102 seal already exists")

    return {
        "journal": {
            "path": journal.relative_to(repo).as_posix(),
            "file_bytes": len(journal_content),
            "file_sha256": sha256_bytes(journal_content),
            "record_count": len(records),
            "head_decision_hash": records[-1].decision_hash,
        },
        "decisions": decision_evidence,
        "candidate": {
            "path": candidate.relative_to(repo).as_posix(),
            "candidate_id": candidate_result["candidate_id"],
            "semantic_body_hash": candidate_result["semantic_body_hash"],
            "file_bytes": len(candidate_content),
            "file_sha256": sha256_bytes(candidate_content),
        },
        "approved_group_count": 3,
        "rejected_group_count": 0,
        "continued_hold_group_count": 2,
        "preview_entry_count": 3,
    }


def build_d102_decision_candidate_gate(
    *,
    repository: str | Path | None = None,
    journal_path: str | Path = DEFAULT_JOURNAL_PATH,
    candidate_path: str | Path = DEFAULT_CANDIDATE_PATH,
) -> dict[str, Any]:
    """Build deterministic portable evidence without widening authority."""

    repo = _repo_root(repository)
    evidence = validate_d102_decision_candidate(
        repository=repo,
        journal_path=journal_path,
        candidate_path=candidate_path,
    )
    body = {
        "milestone": "D-102",
        "evidence_kind": "maintainer-assisted-five-decision-candidate-gate",
        "recorded_at": GATE_RECORDED_AT,
        **evidence,
        "source_files": [
            _source_binding(path, repository=repo) for path in SOURCE_IMPLEMENTATION_PATHS
        ],
        "authority": {
            "maintainer_assisted_decision_count": 5,
            "human_independent_technical_review_claimed": False,
            "full_five_group_review_finalized": False,
            "admission_candidate_created": True,
            "explicit_candidate_approval_pending": True,
            "approval_receipt_present": False,
            "admission_seal_created": False,
            "admitted_memory_rule_count": 0,
            "memory_admission_unlocked": False,
            "memory_index_source_authoring_unlocked": False,
            "memory_index_build_authorized": False,
            "memory_index_built": False,
            "memory_index_frozen": False,
            "core_campaign_unlocked": False,
            "analysis_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": "explicit-exact-candidate-approval",
    }
    body_hash = sha256_text(canonical_json(body))
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "gate_id": f"d102_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }


def encode_d102_gate(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_d102_decision_candidate_gate(
    gate_path: str | Path = DEFAULT_GATE_PATH,
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Rebuild and exact-compare the checked-in D-102 gate."""

    repo = _repo_root(repository)
    selected = _resolved(gate_path, repository=repo)
    try:
        content = selected.read_bytes()
        parsed = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise D102DecisionGateError("D-102 gate is invalid") from exc
    expected = build_d102_decision_candidate_gate(repository=repo)
    expected_content = encode_d102_gate(expected)
    _require(content == expected_content, "D-102 gate exact bytes drifted")
    _require(parsed == expected, "D-102 gate semantic content drifted")
    body = expected["semantic_body"]
    return {
        "ok": True,
        "schema_version": expected["schema_version"],
        "gate_id": expected["gate_id"],
        "semantic_body_hash": expected["semantic_body_hash"],
        "gate_file_bytes": len(content),
        "gate_file_sha256": sha256_bytes(content),
        "decision_count": body["authority"]["maintainer_assisted_decision_count"],
        "approved_group_count": body["approved_group_count"],
        "continued_hold_group_count": body["continued_hold_group_count"],
        "candidate_id": body["candidate"]["candidate_id"],
        "approval_receipt_present": body["authority"]["approval_receipt_present"],
        "admission_seal_created": body["authority"]["admission_seal_created"],
        "admitted_memory_rule_count": body["authority"]["admitted_memory_rule_count"],
        "memory_index_build_authorized": body["authority"]["memory_index_build_authorized"],
        "core_campaign_unlocked": body["authority"]["core_campaign_unlocked"],
        "gate_validation": "pass",
    }
