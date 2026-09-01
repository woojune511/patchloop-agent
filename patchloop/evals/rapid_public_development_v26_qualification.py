"""Zero-call qualification for candidate-v32's Lean V25/V26 package comparison."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from patchloop.errors import ContractError
from patchloop.evals.batch_image_qualification import run_batch_image_mock
from patchloop.evals.rapid_batch_driver import (
    RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
)
from patchloop.evals.rapid_public_development_v2 import _write_once
from patchloop.evals.rapid_public_development_v26 import (
    CANDIDATE_PATH,
    EXPERIMENT_ID,
    PLAN_KIND,
    PLAN_SCHEMA,
    REHEARSAL_PATH,
    VARIANT_CONTRACTS,
    VERIFIER_ID,
    _build_rehearsal_for,
    _stable_json,
    _verifier_entry_hash,
    candidate_bytes,
    load_rapid_public_development_v26_candidate,
    load_rapid_public_development_v26_rehearsal,
    rehearsal_bytes,
)
from patchloop.evals.rapid_terminal_state_parity_qualification import (
    QUALIFICATION_PATH as DRIVER_QUALIFICATION_PATH,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-candidate-v32-v25-v26-batch-image-ab-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/rapid-candidate-v32-v25-v26-batch-image-ab-public-qualification-20260831-v1.json"
)

SOURCE_FILES = (
    "patchloop/agent/batch_image_authority.py",
    "patchloop/agent/runner.py",
    "patchloop/evals/batch_image_qualification.py",
    "patchloop/evals/rapid_public_development_v26.py",
    "patchloop/evals/rapid_public_development_v26_qualification.py",
    "patchloop/evals/rapid_v26_batch_image_binding.py",
    "patchloop/evals/rapid_batch_driver.py",
    "patchloop/evals/rapid_terminal_state_parity_qualification.py",
    "patchloop/evals/rapid_row_continuation.py",
    "patchloop/evals/live_verifier_registry.py",
    "patchloop/contracts.py",
    "scripts/build_rapid_public_development_v32_candidate.py",
    "scripts/run_rapid_public_development_v32.py",
    "scripts/build_rapid_public_development_v26_qualification.py",
    "tests/test_batch_image_authority.py",
    "tests/test_rapid_public_development_v26.py",
    "tests/test_rapid_public_development_v26_qualification.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid candidate-v32 source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def build_rapid_public_development_v26_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    candidate = load_rapid_public_development_v26_candidate(root)
    rehearsal = load_rapid_public_development_v26_rehearsal(candidate, repository=root)
    first = _build_rehearsal_for(candidate, repository=root)
    second = _build_rehearsal_for(candidate, repository=root)
    if rehearsal_bytes(first) != rehearsal_bytes(second) or first != rehearsal:
        raise ContractError("Rapid candidate-v32 rehearsals are not byte-identical")
    candidate_raw = ensure_within(root, CANDIDATE_PATH.as_posix()).read_bytes()
    rehearsal_raw = ensure_within(root, REHEARSAL_PATH.as_posix()).read_bytes()
    if candidate_raw != candidate_bytes(candidate) or rehearsal_raw != rehearsal_bytes(rehearsal):
        raise ContractError("Rapid candidate-v32 artifact bytes differ")
    driver, driver_raw = _stable_json(
        root, DRIVER_QUALIFICATION_PATH, "Rapid terminal-state parity qualification"
    )
    if not (
        candidate["driver_contract"]["policy_version"]
        == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
        and candidate["driver_contract"]["qualification_path"]
        == DRIVER_QUALIFICATION_PATH.as_posix()
        and candidate["driver_contract"]["qualification_file_sha256"] == sha256_bytes(driver_raw)
        and candidate["driver_contract"]["qualification_content_hash"] == driver["content_hash"]
        and driver["successor_policy_version"] == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
    ):
        raise ContractError("Rapid candidate-v32 terminal-parity binding differs")
    criteria = candidate["promotion_criteria"]
    with TemporaryDirectory(prefix=".tmp-wi78-image-qualification-", dir=root) as temp:
        first_mock = run_batch_image_mock(
            candidate, repository=root, state_root=Path(temp) / "first"
        )
        second_mock = run_batch_image_mock(
            candidate, repository=root, state_root=Path(temp) / "second"
        )
    if first_mock != second_mock:
        raise ContractError("Rapid candidate-v32 production-shaped image mock is not deterministic")
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 31, tzinfo=UTC).isoformat(),
        "status": "offline-qualified-awaiting-exact-paid-approval",
        "scope": "rapid-r23-candidate-v32-v25-v26-batch-image-ab",
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
            "generation_count": 2,
            "byte_identical": True,
        },
        "registered_admission": {
            "plan_schema": PLAN_SCHEMA,
            "plan_kind": PLAN_KIND,
            "verifier_id": VERIFIER_ID,
            "verifier_entry_hash": _verifier_entry_hash(),
            "all_manifest_count": 6,
            "requires_row_capability": True,
        },
        "activation_design": {
            "kind": "balanced-interleaved-product-package-ab",
            "control": VARIANT_CONTRACTS["lean-harness-v25"],
            "treatment": VARIANT_CONTRACTS["lean-harness-v26"],
            "rows": 6,
            "control_rows": 3,
            "treatment_rows": 3,
            "same_anyio_v5_task_model_image_memory_budget_evaluator_driver_as_r21": True,
            "package_is_single_comparison_variable": True,
            "single_mechanism_attribution_allowed": False,
            "runner_continuity_check_included": False,
            "task_successor_created": False,
            "quality_claim_allowed": False,
            "generalization_claim_allowed": False,
        },
        "image_admission_contract": candidate["image_admission_contract"],
        "production_shaped_image_start_mock": first_mock,
        "real_docker_identity_observed": False,
        "real_agent_performance_measured": False,
        "reviewed_package_binding": candidate["selection_evidence"]["treatment_lean_v26"],
        "promotion_criteria": criteria,
        "result_contract": {
            "canonical_bundle_schema": driver["driver_event_schema"],
            "row_projection_nested_and_hashed": True,
            "terminal_before_decision": True,
            "decision_before_next_capability": True,
            "completed_terminal_uses_durable_result": True,
            "payload_result_mismatch_halts": True,
            "batch_close_reports_unstarted_rows": True,
            "candidate_wrapper_has_no_manual_row_loop": True,
        },
        "recovery_contract": {
            "escaped_exception_halts": True,
            "incomplete_settlement_halts": True,
            "restart_without_ephemeral_receipts_halts": True,
            "duplicate_capability_grant_halts": True,
            "consumed_r21_retry_allowed": False,
            "stopped_r22_retry_allowed": False,
            "image_receipt_missing_or_tampered_reinspection_allowed": False,
            "image_inspection_attempt_durable_before_dispatch": True,
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
            "private_task_schema_parsed_by_trusted_loader": True,
            "sealed_task_bytes_hashed_for_identity_only": True,
            "hidden_or_reference_content_exposed_to_model_or_selection": False,
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
        raise ContractError("Rapid candidate-v32 qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_public_development_v26_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_public_development_v26_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    raw = qualification_bytes(value)
    if target.exists():
        if target.read_bytes() != raw:
            raise ContractError("Rapid candidate-v32 qualification already differs")
        return value
    _write_once(target, raw)
    return value


def load_rapid_public_development_v26_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("Rapid candidate-v32 qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("Rapid candidate-v32 qualification bytes differ")
    if value != build_rapid_public_development_v26_qualification(root):
        raise ContractError("Rapid candidate-v32 qualification source binding differs")
    return value


__all__ = [
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_rapid_public_development_v26_qualification",
    "load_rapid_public_development_v26_qualification",
    "materialize_rapid_public_development_v26_qualification",
    "qualification_bytes",
]
