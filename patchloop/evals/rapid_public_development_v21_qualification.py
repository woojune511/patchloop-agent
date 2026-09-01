"""Zero-call qualification for candidate-v26 terminal-state parity integration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals.rapid_batch_driver import (
    RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
)
from patchloop.evals.rapid_public_development_v21 import (
    CANDIDATE_PATH,
    EXPERIMENT_ID,
    PLAN_KIND,
    PLAN_SCHEMA,
    REHEARSAL_PATH,
    VERIFIER_ID,
    _verifier_entry_hash,
    candidate_bytes,
    load_rapid_public_development_v21_candidate,
    load_rapid_public_development_v21_rehearsal,
    rehearsal_bytes,
)
from patchloop.evals.rapid_terminal_state_parity_qualification import (
    QUALIFICATION_PATH as DRIVER_QUALIFICATION_PATH,
)
from patchloop.evals.rapid_terminal_state_parity_qualification import (
    load_rapid_terminal_state_parity_qualification,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-candidate-v26-terminal-parity-integration-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/rapid-candidate-v26-terminal-parity-integration-"
    "public-qualification-20260827-v1.json"
)

SOURCE_FILES = (
    "patchloop/evals/rapid_public_development_v21.py",
    "patchloop/evals/rapid_public_development_v21_qualification.py",
    "patchloop/evals/rapid_batch_driver.py",
    "patchloop/evals/rapid_terminal_state_parity_qualification.py",
    "patchloop/evals/rapid_row_continuation.py",
    "patchloop/evals/live_verifier_registry.py",
    "patchloop/contracts.py",
    "scripts/build_rapid_public_development_v26_candidate.py",
    "scripts/run_rapid_public_development_v26.py",
    "scripts/build_rapid_public_development_v21_qualification.py",
    "tests/test_rapid_public_development_v21.py",
    "tests/test_rapid_public_development_v21_qualification.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid candidate-v26 source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def build_rapid_public_development_v21_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    candidate = load_rapid_public_development_v21_candidate(root)
    rehearsal = load_rapid_public_development_v21_rehearsal(candidate, repository=root)
    candidate_raw = ensure_within(root, CANDIDATE_PATH.as_posix()).read_bytes()
    rehearsal_raw = ensure_within(root, REHEARSAL_PATH.as_posix()).read_bytes()
    if candidate_raw != candidate_bytes(candidate) or rehearsal_raw != rehearsal_bytes(rehearsal):
        raise ContractError("Rapid candidate-v26 artifact bytes differ")
    driver = load_rapid_terminal_state_parity_qualification(root)
    driver_raw = ensure_within(root, DRIVER_QUALIFICATION_PATH.as_posix()).read_bytes()
    if not (
        candidate["driver_contract"]["policy_version"]
        == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
        and candidate["driver_contract"]["qualification_path"]
        == DRIVER_QUALIFICATION_PATH.as_posix()
        and candidate["driver_contract"]["qualification_file_sha256"] == sha256_bytes(driver_raw)
        and candidate["driver_contract"]["qualification_content_hash"] == driver["content_hash"]
        and driver["successor_policy_version"] == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
    ):
        raise ContractError("Rapid candidate-v26 terminal-parity binding differs")
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "rapid-r18-candidate-v26-terminal-state-parity-integration",
        "experiment_id": EXPERIMENT_ID,
        "candidate": {
            "path": CANDIDATE_PATH.as_posix(),
            "bytes": len(candidate_raw),
            "file_sha256": sha256_bytes(candidate_raw),
            "content_hash": candidate["content_hash"],
            "execution_hash": candidate["execution_hash"],
            "runtime_build_hash": candidate["runtime_build_hash"],
            "schedule_hash": candidate["schedule_hash"],
            "cost_control_hash": candidate["cost_control_hash"],
        },
        "rehearsal": {
            "path": REHEARSAL_PATH.as_posix(),
            "bytes": len(rehearsal_raw),
            "file_sha256": sha256_bytes(rehearsal_raw),
            "content_hash": rehearsal["content_hash"],
            "verified_manifest_count": rehearsal["verified_manifest_count"],
            "stage_sequence": rehearsal["stage_sequence"],
        },
        "registered_admission": {
            "plan_schema": PLAN_SCHEMA,
            "plan_kind": PLAN_KIND,
            "verifier_id": VERIFIER_ID,
            "verifier_entry_hash": _verifier_entry_hash(),
            "all_manifest_count": 6,
            "requires_row_capability": True,
        },
        "driver_qualification": {
            "path": DRIVER_QUALIFICATION_PATH.as_posix(),
            "bytes": len(driver_raw),
            "file_sha256": sha256_bytes(driver_raw),
            "content_hash": driver["content_hash"],
            "predecessor_policy_version": driver["predecessor_policy_version"],
            "successor_policy_version": driver["successor_policy_version"],
        },
        "result_contract": {
            "canonical_bundle_schema": driver["driver_event_schema"],
            "row_projection_nested_and_hashed": True,
            "terminal_before_decision": True,
            "decision_before_next_capability": True,
            "completed_terminal_uses_durable_result": True,
            "completed_payload_outcome_kind_required": False,
            "payload_result_mismatch_halts": True,
            "batch_close_reports_unstarted_rows": True,
            "candidate_wrapper_has_no_manual_row_loop": True,
        },
        "recovery_contract": {
            "escaped_exception_halts": True,
            "incomplete_settlement_halts": True,
            "restart_without_ephemeral_receipts_halts": True,
            "duplicate_capability_grant_halts": True,
            "consumed_r17_retry_allowed": False,
        },
        "source_files": [_source_identity(root, relative) for relative in SOURCE_FILES],
        "evidence_boundary": {
            "provider_calls": 0,
            "docker_calls": 0,
            "task_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "raw_reasoning_read": False,
        },
        "candidate_specific_runtime_integrated": True,
        "candidate_created": True,
        "rehearsal_created": True,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid candidate-v26 qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_public_development_v21_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_public_development_v21_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    raw = qualification_bytes(value)
    if target.exists():
        if target.read_bytes() != raw:
            raise ContractError("Rapid candidate-v26 qualification already differs")
        return value
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return value


def load_rapid_public_development_v21_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("Rapid candidate-v26 qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("Rapid candidate-v26 qualification bytes differ")
    if value != build_rapid_public_development_v21_qualification(root):
        raise ContractError("Rapid candidate-v26 qualification source binding differs")
    return value


__all__ = [
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_rapid_public_development_v21_qualification",
    "load_rapid_public_development_v21_qualification",
    "materialize_rapid_public_development_v21_qualification",
    "qualification_bytes",
]
