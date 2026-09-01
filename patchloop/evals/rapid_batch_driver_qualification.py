"""Deterministic zero-call qualification for the append-only Rapid driver."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals.rapid_batch_driver import (
    RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
    RAPID_BATCH_DRIVER_EVENT_SCHEMA,
    RAPID_BATCH_DRIVER_POLICY_VERSION,
)
from patchloop.evals.rapid_row_continuation_qualification import (
    QUALIFICATION_PATH as ROW_CONTINUATION_QUALIFICATION_PATH,
)
from patchloop.evals.rapid_row_continuation_qualification import (
    load_rapid_row_continuation_qualification,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-append-only-driver-integration-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/rapid-append-only-driver-integration-public-qualification-20260827-v1.json"
)

ROW_CONTINUATION_QUALIFICATION_IDENTITY = {
    "path": ROW_CONTINUATION_QUALIFICATION_PATH.as_posix(),
    "bytes": 9_969,
    "file_sha256": "sha256:61c07553945d18e6d3c71166f95ab6aa4ed575c1685820d44237621ee1511cbd",
    "content_hash": "sha256:0a8096cde6e3938b24f5a3e6dbdf90be8655697b4e9fc87a11fc339b02c47de1",
}

SOURCE_FILES = (
    "patchloop/evals/rapid_batch_driver.py",
    "patchloop/evals/rapid_batch_driver_qualification.py",
    "patchloop/evals/rapid_row_continuation.py",
    "patchloop/agent/runner.py",
    "patchloop/state/store.py",
    "scripts/build_rapid_batch_driver_qualification.py",
    "tests/test_rapid_batch_driver.py",
    "tests/test_rapid_batch_driver_qualification.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid driver source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _predecessor_identity(root: Path) -> dict[str, Any]:
    value = load_rapid_row_continuation_qualification(root)
    path = ensure_within(root, ROW_CONTINUATION_QUALIFICATION_PATH.as_posix())
    raw = path.read_bytes()
    observed = {
        "path": ROW_CONTINUATION_QUALIFICATION_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "content_hash": value["content_hash"],
    }
    if observed != ROW_CONTINUATION_QUALIFICATION_IDENTITY:
        raise ContractError("Rapid row-continuation predecessor identity differs")
    return observed


def _fault_matrix() -> dict[str, Any]:
    return {
        "eligible_returned_row": {
            "runner_returned": True,
            "typed_settlement_required": True,
            "decision": "continue",
            "decision_persisted_before_grant": True,
            "later_independent_row_may_start": True,
        },
        "escaped_exception": {
            "runner_returned": False,
            "decision": "halt",
            "later_independent_row_may_start": False,
        },
        "artifact_fault": {
            "artifact_triad_matches": False,
            "decision": "halt",
            "later_independent_row_may_start": False,
        },
        "accounting_fault": {
            "cost_settlement_complete": False,
            "decision": "halt",
            "later_independent_row_may_start": False,
        },
        "active_worker_lock": {
            "worker_lock_released": False,
            "decision": "halt",
            "later_independent_row_may_start": False,
        },
        "restart_without_ephemeral_receipts": {
            "decision": "halt",
            "reason_code": "EPHEMERAL_CAPABILITY_STATE_UNAVAILABLE_ON_RESTART",
            "capability_reconstructed": False,
        },
        "duplicate_grant": {
            "first_grant_one_use": True,
            "second_grant_rejected_before_schedule_advance": True,
        },
        "rehashed_semantic_tamper": {
            "hash_chain_alone_sufficient": False,
            "semantic_transition_rejected": True,
        },
    }


def build_rapid_batch_driver_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "append-only-rapid-batch-driver-integration",
        "driver_contract_schema": RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
        "driver_event_schema": RAPID_BATCH_DRIVER_EVENT_SCHEMA,
        "driver_policy_version": RAPID_BATCH_DRIVER_POLICY_VERSION,
        "required_event_order": [
            "row-capability-issued",
            "row-terminal",
            "optional-row-settlement-evidence",
            "row-decision",
            "next-row-capability-issued",
        ],
        "schedule_advance_contract": {
            "ordinary_terminal_requires_typed_continue": True,
            "infrastructure_terminal_requires_gateway_continue": True,
            "decision_persisted_before_capability": True,
            "capability_persisted_before_next_row_start": True,
            "halt_or_incomplete_journal_starts_no_later_row": True,
        },
        "fault_matrix": _fault_matrix(),
        "mocked_gate": {
            "test_module": "tests/test_rapid_batch_driver.py",
            "eligible_returned_row": True,
            "ordinary_terminal": True,
            "escaped_exception": True,
            "artifact_fault": True,
            "accounting_fault": True,
            "active_lock": True,
            "restart": True,
            "duplicate_grant": True,
            "journal_tamper": True,
            "provider_or_container_mocked": True,
        },
        "source_files": [_source_identity(root, relative) for relative in SOURCE_FILES],
        "predecessor_qualification": _predecessor_identity(root),
        "evidence_boundary": {
            "public_driver_contract_only": True,
            "driver_added_exception_message": False,
            "candidate_public_projection_retained": True,
            "raw_reasoning_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
        },
        "consumed_r16_modified": False,
        "consumed_r16_retry_allowed": False,
        "typed_capability_gateway_integrated": True,
        "append_only_rapid_driver_integrated": True,
        "candidate_specific_runtime_integrated": False,
        "rapid_candidate_created": False,
        "rehearsal_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid driver qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_batch_driver_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_batch_driver_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_rapid_batch_driver_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid driver qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("Rapid driver qualification bytes differ")
    if value != build_rapid_batch_driver_qualification(root):
        raise ContractError("Rapid driver qualification source binding differs")
    return value


__all__ = [
    "QUALIFICATION_PATH",
    "ROW_CONTINUATION_QUALIFICATION_IDENTITY",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_rapid_batch_driver_qualification",
    "load_rapid_batch_driver_qualification",
    "materialize_rapid_batch_driver_qualification",
    "qualification_bytes",
]
