"""Deterministic zero-call qualification for Rapid row-local isolation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals.rapid_row_continuation import (
    RAPID_ROW_CONTINUATION_POLICY_VERSION,
    RapidRowSettlementChecks,
    RapidRowSettlementEvidence,
    build_rapid_row_settlement_evidence,
    classify_rapid_row_continuation,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-row-local-infrastructure-isolation-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/rapid-row-local-infrastructure-continuation-public-qualification-20260827-v1.json"
)

R16_RESULT_PATH = (
    "reports/rapid-development/"
    "rapid-public-dev-anyio-v5-epoch-parity-ab-20260827-r16-df2cc46ce6d3.jsonl"
)
R16_DIAGNOSIS_PATH = (
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-epoch-parity-ab-20260827-r16-"
    "workflow-diagnosis-v1.json"
)
IMMUTABLE_PREDECESSORS = {
    R16_RESULT_PATH: {
        "bytes": 6_759,
        "file_sha256": ("sha256:83277c403c7cff7f762c9a6b6a4b2d472bcbf4902d06a1fed48ac02dfbc0cde9"),
        "final_event_hash": (
            "sha256:7c8e558a43e130c1007513ef02690ba8e4073674ed2c558d4ec5c922386958c9"
        ),
    },
    R16_DIAGNOSIS_PATH: {
        "bytes": 6_228,
        "file_sha256": ("sha256:95af2d73ad1aee910035d139525973f5971638b52000658160af7f1b9c442306"),
        "content_hash": ("sha256:6fa041393163c328452b80fdfd00ae2801755dc41a3fe5b93b7a6766d3806966"),
    },
}

SOURCE_FILES = (
    "patchloop/evals/rapid_row_continuation.py",
    "patchloop/evals/rapid_row_continuation_qualification.py",
    "patchloop/agent/runner.py",
    "patchloop/state/store.py",
    "scripts/build_rapid_row_continuation_qualification.py",
    "tests/test_rapid_row_continuation.py",
    "tests/test_rapid_row_continuation_qualification.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid row-isolation source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _jsonl_identity(root: Path, relative: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    identity = _source_identity(root, relative)
    try:
        events = [
            json.loads(line) for line in ensure_within(root, relative).read_bytes().splitlines()
        ]
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid R16 result is not valid JSONL") from exc
    previous: str | None = None
    for event in events:
        if not isinstance(event, dict):
            raise ContractError("Rapid R16 result event is not an object")
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if event.get("previous_event_hash") != previous or event.get("content_hash") != sha256_json(
            body
        ):
            raise ContractError("Rapid R16 result hash chain differs")
        previous = event["content_hash"]
    if not events or events[-1].get("event") != "batch-completed":
        raise ContractError("Rapid R16 result lacks batch completion")
    identity["final_event_hash"] = previous
    return identity, events


def _json_identity(
    root: Path,
    relative: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    identity = _source_identity(root, relative)
    try:
        value = json.loads(ensure_within(root, relative).read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid R16 diagnosis is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ContractError("Rapid R16 diagnosis is not an object")
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid R16 diagnosis content hash differs")
    identity["content_hash"] = value["content_hash"]
    return identity, value


def _all_checks(**changes: bool) -> RapidRowSettlementChecks:
    body = {name: True for name in RapidRowSettlementChecks.model_fields}
    body.update(changes)
    return RapidRowSettlementChecks.model_validate(body)


def _base_evidence(
    *,
    checks: RapidRowSettlementChecks | None = None,
    **changes: Any,
) -> RapidRowSettlementEvidence:
    current_manifest_hash = sha256_json("qualified-manifest-01")
    result_hash = sha256_json("qualified-result-01")
    body: dict[str, Any] = {
        "authority_kind": "live",
        "execution_hash": sha256_json("qualified-execution"),
        "plan_hash": sha256_json("qualified-plan"),
        "schedule_hash": sha256_json("qualified-schedule"),
        "cost_control_hash": sha256_json("qualified-cost-control"),
        "current_schedule_order": 1,
        "next_schedule_order": 2,
        "current_schedule_row_id": "qualified-row-01",
        "next_schedule_row_id": "qualified-row-02",
        "current_run_id": "run_qualified_row_01",
        "next_run_id": "run_qualified_row_02",
        "current_manifest_hash": current_manifest_hash,
        "next_manifest_hash": sha256_json("qualified-manifest-02"),
        "batch_receipt_hash": sha256_json("qualified-batch-receipt"),
        "row_receipt_hash": sha256_json("qualified-row-receipt"),
        "outcome_kind": "infrastructure_error",
        "evaluation_status": "not_run",
        "agent_submission_status": "failed",
        "terminal_error_code": "RECOVERY_ERROR",
        "terminal_event_sequence": 7,
        "terminal_event_hash": sha256_json("qualified-terminal-event"),
        "state_manifest_hash": current_manifest_hash,
        "state_result_hash": result_hash,
        "returned_result_hash": result_hash,
        "manifest_file_sha256": sha256_json("qualified-manifest-file"),
        "result_file_sha256": sha256_json("qualified-result-file"),
        "provenance_file_sha256": sha256_json("qualified-provenance-file"),
        "model_cost_nanos": 100_000_000,
        "row_reserve_nanos": 1_200_000_000,
        "accrued_cost_nanos_before": 200_000_000,
        "accrued_cost_nanos_after": 300_000_000,
        "hard_cap_nanos": 7_500_000_000,
        "checks": checks or _all_checks(),
    }
    body.update(changes)
    return build_rapid_row_settlement_evidence(**body)


def _tamper_message(evidence: RapidRowSettlementEvidence) -> str:
    value = evidence.model_dump(mode="json")
    value["terminal_error_code"] = "TAMPERED"
    try:
        classify_rapid_row_continuation(value)
    except ContractError as exc:
        return str(exc)
    raise ContractError("Rapid row-isolation qualification expected tamper rejection")


def _scenarios() -> dict[str, Any]:
    eligible = _base_evidence()
    eligible_decision = classify_rapid_row_continuation(eligible)
    missing_checks = {}
    for field_name in RapidRowSettlementChecks.model_fields:
        decision = classify_rapid_row_continuation(
            _base_evidence(checks=_all_checks(**{field_name: False}))
        )
        missing_checks[field_name] = {
            "decision": decision.decision,
            "reason_codes": list(decision.reason_codes),
            "decision_hash": decision.content_hash,
        }
    missing_identities = {}
    for field_name in (
        "plan_hash",
        "schedule_hash",
        "cost_control_hash",
        "batch_receipt_hash",
        "row_receipt_hash",
        "terminal_event_sequence",
        "terminal_event_hash",
        "state_manifest_hash",
        "state_result_hash",
        "returned_result_hash",
        "manifest_file_sha256",
        "result_file_sha256",
        "provenance_file_sha256",
    ):
        decision = classify_rapid_row_continuation(_base_evidence(**{field_name: None}))
        missing_identities[field_name] = {
            "decision": decision.decision,
            "reason_codes": list(decision.reason_codes),
            "decision_hash": decision.content_hash,
        }
    semantic_conflicts = {}
    for name, changes in {
        "non_live_authority": {"authority_kind": "rehearsal"},
        "skipped_order": {"next_schedule_order": 3},
        "wrong_terminal_code": {"terminal_error_code": "OTHER"},
        "cost_mismatch": {"accrued_cost_nanos_after": 299_999_999},
        "row_reserve_exceeded": {
            "model_cost_nanos": 1_300_000_000,
            "accrued_cost_nanos_after": 1_500_000_000,
        },
        "hard_cap_exceeded": {
            "model_cost_nanos": 7_400_000_000,
            "accrued_cost_nanos_before": 200_000_000,
            "accrued_cost_nanos_after": 7_600_000_000,
        },
    }.items():
        decision = classify_rapid_row_continuation(_base_evidence(**changes))
        semantic_conflicts[name] = {
            "decision": decision.decision,
            "reason_codes": list(decision.reason_codes),
            "decision_hash": decision.content_hash,
        }
    return {
        "eligible_exact_settlement": {
            "evidence_hash": eligible.content_hash,
            "decision": eligible_decision.decision,
            "reason_codes": list(eligible_decision.reason_codes),
            "decision_hash": eligible_decision.content_hash,
            "next_row_capability_issued": eligible_decision.next_row_capability_issued,
        },
        "each_missing_check_halts": missing_checks,
        "each_missing_identity_halts": missing_identities,
        "semantic_conflicts_halt": semantic_conflicts,
        "tampered_evidence": {
            "rejected": True,
            "public_error": _tamper_message(eligible),
        },
    }


def _r16_observation(
    events: list[dict[str, Any]],
    diagnosis: dict[str, Any],
) -> dict[str, Any]:
    terminal_rows = [event for event in events if event.get("event") == "row-terminal"]
    if len(terminal_rows) != 1:
        raise ContractError("Rapid R16 result terminal-row count differs")
    row = terminal_rows[0]
    receipt_fields = {
        "batch_receipt_hash",
        "row_receipt_hash",
        "worker_lock_released",
        "workspace_isolated",
        "batch_next_order_ready",
    }
    diagnosis_rows = diagnosis.get("rows")
    diagnosis_row = (
        diagnosis_rows[0] if isinstance(diagnosis_rows, list) and len(diagnosis_rows) == 1 else None
    )
    terminal_attribution = (
        diagnosis_row.get("terminal_attribution") if isinstance(diagnosis_row, dict) else None
    )
    if not (
        row.get("order") == 1
        and row.get("outcome_kind") == "infrastructure_error"
        and row.get("error_code") is None
        and row.get("evaluator_reached") is False
        and isinstance(terminal_attribution, dict)
        and terminal_attribution.get("error_code") == "RECOVERY_ERROR"
    ):
        raise ContractError("Rapid R16 bounded terminal projection differs")
    return {
        "consumed_execution_hash": (
            "sha256:df2cc46ce6d313918499a6382ca5b1beface18aa5a7811aaf1deb9132d2ee024"
        ),
        "started_rows": 1,
        "terminal_order": 1,
        "terminal_outcome_kind": row["outcome_kind"],
        "bundle_terminal_error_code": row["error_code"],
        "diagnosis_terminal_error_code": terminal_attribution["error_code"],
        "evaluator_reached": row["evaluator_reached"],
        "bounded_settlement_receipt_fields_present": bool(receipt_fields.intersection(row)),
        "retroactive_continuation_eligible": False,
        "retroactive_reason": "EPHEMERAL_CAPABILITY_AND_CLEANUP_RECEIPT_NOT_PERSISTED",
        "retry_allowed": False,
        "historical_result_reclassified": False,
    }


def build_rapid_row_continuation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    r16_identity, r16_events = _jsonl_identity(root, R16_RESULT_PATH)
    diagnosis_identity, diagnosis = _json_identity(root, R16_DIAGNOSIS_PATH)
    if r16_identity != {"path": R16_RESULT_PATH, **IMMUTABLE_PREDECESSORS[R16_RESULT_PATH]}:
        raise ContractError("immutable Rapid R16 result identity differs")
    if diagnosis_identity != {
        "path": R16_DIAGNOSIS_PATH,
        **IMMUTABLE_PREDECESSORS[R16_DIAGNOSIS_PATH],
    }:
        raise ContractError("immutable Rapid R16 diagnosis identity differs")
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "rapid-row-local-infrastructure-isolation",
        "policy_version": RAPID_ROW_CONTINUATION_POLICY_VERSION,
        "scenarios": _scenarios(),
        "r16_observation": _r16_observation(r16_events, diagnosis),
        "source_files": [_source_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_predecessors": [r16_identity, diagnosis_identity],
        "evidence_boundary": {
            "public_r16_result_and_diagnosis_read": True,
            "exception_messages_projected": False,
            "raw_reasoning_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "workspace_mutations": 0,
            "added_cost_usd": "0",
        },
        "consumed_r16_modified": False,
        "consumed_r16_retry_allowed": False,
        "typed_capability_gateway_integrated": True,
        "rapid_batch_driver_integrated": False,
        "runtime_surface_integrated": False,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid row-isolation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_row_continuation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_row_continuation_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_rapid_row_continuation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid row-isolation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("Rapid row-isolation qualification bytes differ")
    if value != build_rapid_row_continuation_qualification(root):
        raise ContractError("Rapid row-isolation qualification source binding differs")
    return value
