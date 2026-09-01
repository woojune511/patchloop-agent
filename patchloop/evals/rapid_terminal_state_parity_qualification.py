"""Deterministic zero-call qualification for Rapid terminal-state parity V2."""

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
    RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
)
from patchloop.evals.rapid_batch_driver_qualification import (
    QUALIFICATION_PATH as PREDECESSOR_QUALIFICATION_PATH,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-terminal-state-parity-public-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/rapid-terminal-state-parity-public-qualification-20260827-v1.json"
)
R17_RESULT_PATH = Path(
    "reports/rapid-development/"
    "rapid-public-dev-anyio-v5-row-isolation-ab-20260827-r17-b38b8c17c761.jsonl"
)
PREDECESSOR_QUALIFICATION_IDENTITY = {
    "path": PREDECESSOR_QUALIFICATION_PATH.as_posix(),
    "bytes": 4_510,
    "file_sha256": "sha256:72b355114b3a92eaf2a281bec6d5778c93c55751927e9cd530ee174c03b1cc5c",
    "content_hash": "sha256:e2825a3c5e839764e3e5fc7fd99418575d6971119188e2e36a5dc9ee7012cb6a",
}
R17_RESULT_IDENTITY = {
    "path": R17_RESULT_PATH.as_posix(),
    "bytes": 8_377,
    "file_sha256": "sha256:21660ac7e862487329bc0f83fc71bbbb16eb1f28a5a402a486d7ddf1e1cde3a7",
    "execution_hash": "sha256:b38b8c17c76127d380d7e91905ca87329075a0d497605c177bcd0b2df57acee8",
    "final_event_content_hash": (
        "sha256:7a73f545c37cf693830e7ddef47a0260de628c1dd815597efe26a5795b7fe61f"
    ),
}
SOURCE_FILES = (
    "patchloop/evals/rapid_batch_driver.py",
    "patchloop/evals/rapid_terminal_state_parity_qualification.py",
    "patchloop/agent/runner.py",
    "patchloop/state/store.py",
    "scripts/build_rapid_terminal_state_parity_qualification.py",
    "tests/test_rapid_batch_driver.py",
    "tests/test_rapid_terminal_state_parity_qualification.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid terminal-parity source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _predecessor_identity(root: Path) -> dict[str, Any]:
    selected = ensure_within(root, PREDECESSOR_QUALIFICATION_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid driver predecessor qualification is unavailable") from exc
    observed = {
        "path": PREDECESSOR_QUALIFICATION_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "content_hash": value.get("content_hash"),
    }
    if observed != PREDECESSOR_QUALIFICATION_IDENTITY:
        raise ContractError("Rapid driver predecessor qualification identity differs")
    return observed


def _r17_result_identity(root: Path) -> dict[str, Any]:
    selected = ensure_within(root, R17_RESULT_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Consumed Rapid R17 result is unavailable") from exc
    previous: str | None = None
    for event in events:
        if not isinstance(event, dict):
            raise ContractError("Consumed Rapid R17 event is invalid")
        content_hash = event.get("content_hash")
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if event.get("previous_event_hash") != previous or content_hash != sha256_json(body):
            raise ContractError("Consumed Rapid R17 result chain differs")
        previous = content_hash
    final = events[-1] if events else {}
    observed = {
        "path": R17_RESULT_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_hash": final.get("execution_hash"),
        "final_event_content_hash": final.get("content_hash"),
    }
    if observed != R17_RESULT_IDENTITY:
        raise ContractError("Consumed Rapid R17 result identity differs")
    row_terminals = [event for event in events if event.get("event") == "row-terminal"]
    if not (
        final.get("event") == "batch-halted"
        and final.get("reason_codes") == ["TERMINAL_STATE_NOT_ATOMIC"]
        and final.get("terminal_row_count") == 1
        and final.get("not_started_row_count") == 5
        and len(row_terminals) == 1
        and row_terminals[0].get("terminal_state_atomic") is False
        and row_terminals[0].get("projection_matches_result") is True
        and row_terminals[0].get("cost_settlement_complete") is True
    ):
        raise ContractError("Consumed Rapid R17 terminal attribution differs")
    return observed


def build_rapid_terminal_state_parity_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "rapid-production-terminal-state-parity",
        "driver_contract_schema": RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
        "driver_event_schema": RAPID_BATCH_DRIVER_EVENT_SCHEMA,
        "predecessor_policy_version": RAPID_BATCH_DRIVER_POLICY_VERSION,
        "successor_policy_version": RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
        "successor_opt_in_required": True,
        "terminal_contract": {
            "completed": {
                "event_type": "RunCompleted",
                "status": "completed",
                "result_outcomes": ["resolved", "task_failure"],
                "payload_result_bindings": ["scope_compliant_success", "official"],
                "payload_outcome_kind_required": False,
            },
            "failed": {
                "event_type": "RunFailed",
                "status": "failed",
                "result_outcomes": ["agent_failure", "infrastructure_error"],
                "payload_result_bindings": ["outcome_kind"],
                "payload_outcome_kind_required": True,
            },
            "manifest_result_status_event_atomic": True,
            "exactly_one_terminal_event": True,
            "terminal_event_must_be_last": True,
            "payload_mismatch_halts_before_next_row": True,
        },
        "production_shaped_mock_gate": {
            "task_failure_completed_without_payload_outcome_kind": True,
            "resolved_completed_without_payload_outcome_kind": True,
            "failed_terminal_retains_payload_outcome_kind": True,
            "completed_payload_result_mismatch_halts": True,
            "fault_recovery_restart_duplicate_and_tamper_regression": True,
        },
        "source_files": [_source_identity(root, relative) for relative in SOURCE_FILES],
        "predecessor_qualification": _predecessor_identity(root),
        "consumed_r17_result": _r17_result_identity(root),
        "evidence_boundary": {
            "public_driver_and_result_only": True,
            "raw_reasoning_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "agent_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
        },
        "consumed_r17_modified": False,
        "consumed_r17_retry_allowed": False,
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
        raise ContractError("Rapid terminal-parity qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_terminal_state_parity_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_terminal_state_parity_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_rapid_terminal_state_parity_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("Rapid terminal-parity qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("Rapid terminal-parity qualification bytes differ")
    if value != build_rapid_terminal_state_parity_qualification(root):
        raise ContractError("Rapid terminal-parity qualification source binding differs")
    return value


__all__ = [
    "PREDECESSOR_QUALIFICATION_IDENTITY",
    "QUALIFICATION_PATH",
    "R17_RESULT_IDENTITY",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_rapid_terminal_state_parity_qualification",
    "load_rapid_terminal_state_parity_qualification",
    "materialize_rapid_terminal_state_parity_qualification",
    "qualification_bytes",
]
