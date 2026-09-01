"""Zero-call qualification for candidate-v33's Lean V25/V27 package comparison."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from patchloop.agent.provider_request_gate import validate_request_schemas
from patchloop.agent.runner import AgentRunner
from patchloop.errors import ContractError
from patchloop.evals.provider_request_batch_qualification import run_provider_request_batch_mock
from patchloop.evals.rapid_batch_driver import (
    RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
)
from patchloop.evals.rapid_public_development_v2 import _write_once
from patchloop.evals.rapid_public_development_v27 import (
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
    build_rapid_v27_run_manifest,
    candidate_bytes,
    load_rapid_public_development_v27_candidate,
    load_rapid_public_development_v27_rehearsal,
    rehearsal_bytes,
)
from patchloop.evals.rapid_terminal_state_parity_qualification import (
    QUALIFICATION_PATH as DRIVER_QUALIFICATION_PATH,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-candidate-v33-v25-v27-provider-schema-ab-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/rapid-candidate-v33-v25-v27-provider-schema-ab-public-qualification-20260901-v1.json"
)

SOURCE_FILES = (
    "patchloop/agent/provider_request_gate.py",
    "patchloop/agent/provider_schema_admission.py",
    "patchloop/agent/provider_schema_adapter.py",
    "patchloop/agent/provider_count_accounting.py",
    "patchloop/agent/batch_image_authority.py",
    "patchloop/agent/runner.py",
    "patchloop/evals/provider_request_batch_qualification.py",
    "patchloop/evals/rapid_public_development_v27.py",
    "patchloop/evals/rapid_public_development_v27_qualification.py",
    "patchloop/evals/rapid_v27_package_binding.py",
    "patchloop/evals/rapid_batch_driver.py",
    "patchloop/evals/rapid_terminal_state_parity_qualification.py",
    "patchloop/evals/rapid_row_continuation.py",
    "patchloop/evals/live_verifier_registry.py",
    "patchloop/contracts.py",
    "scripts/build_rapid_public_development_v33_candidate.py",
    "scripts/run_rapid_public_development_v33.py",
    "scripts/build_rapid_public_development_v27_qualification.py",
    "tests/test_rapid_public_development_v27.py",
    "tests/test_provider_request_gate_runner.py",
    "tests/test_rapid_public_development_v27_qualification.py",
)


def _source_identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"Rapid candidate-v33 source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def build_rapid_public_development_v27_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    candidate = load_rapid_public_development_v27_candidate(root)
    rehearsal = load_rapid_public_development_v27_rehearsal(candidate, repository=root)
    candidate_raw = ensure_within(root, CANDIDATE_PATH.as_posix()).read_bytes()
    rehearsal_raw = ensure_within(root, REHEARSAL_PATH.as_posix()).read_bytes()
    if candidate_raw != candidate_bytes(candidate) or rehearsal_raw != rehearsal_bytes(rehearsal):
        raise ContractError("Rapid candidate-v33 artifact bytes differ")
    return _qualification_for(candidate, rehearsal, repository=root, materialized=True)


def _qualification_for(
    candidate: dict[str, Any],
    rehearsal: dict[str, Any],
    *,
    repository: str | Path,
    materialized: bool = False,
) -> dict[str, Any]:
    """Exercise the entire qualification before freezing any output artifact."""
    root = Path(repository).resolve()
    first = _build_rehearsal_for(candidate, repository=root)
    second = _build_rehearsal_for(candidate, repository=root)
    if rehearsal_bytes(first) != rehearsal_bytes(second) or first != rehearsal:
        raise ContractError("Rapid candidate-v33 rehearsals are not byte-identical")
    candidate_raw = candidate_bytes(candidate)
    rehearsal_raw = rehearsal_bytes(rehearsal)
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
        raise ContractError("Rapid candidate-v33 terminal-parity binding differs")
    criteria = candidate["promotion_criteria"]
    empty_argument_schemas = {}
    for order, variant in ((1, "lean-harness-v25"), (2, "lean-harness-v27")):
        manifest = build_rapid_v27_run_manifest(candidate, order, repository=root)
        _, tools = AgentRunner._runtime_contract(manifest)
        request = {"tools": [tool for tool in tools if tool["name"] in {"get_diff", "finish_task"}]}
        before = canonical_json(request)
        receipt = validate_request_schemas(request)
        if canonical_json(request) != before:
            raise ContractError("R24 schema admission modified immutable wire bytes")
        empty_argument_schemas[variant] = receipt
    with TemporaryDirectory(prefix=".q82-", dir=root) as temp:
        first_mock = run_provider_request_batch_mock(
            candidate, repository=root, state_root=Path(temp) / "first"
        )
        second_mock = run_provider_request_batch_mock(
            candidate, repository=root, state_root=Path(temp) / "second"
        )
    if first_mock != second_mock:
        raise ContractError("Rapid candidate-v33 production-shaped image mock is not deterministic")
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 9, 1, tzinfo=UTC).isoformat(),
        "status": "offline-qualified-awaiting-exact-paid-approval"
        if materialized
        else "offline-dry-validation",
        "scope": "rapid-r24-candidate-v33-v25-v27-provider-schema-ab",
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
            "treatment": VARIANT_CONTRACTS["lean-harness-v27"],
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
        "provider_request_contract": candidate["provider_request_contract"],
        "empty_argument_schema_compatibility": empty_argument_schemas,
        "pre_count_boundary": {
            "row_request_count": len(rehearsal["all_pre_count_boundaries"]),
            "actual_public_task_and_model": True,
            "synthetic_pre_action_prefix": True,
            "initial_surface_only": True,
            "stop": rehearsal["stopped_before"],
            "future_execution_request_bytes_observed": False,
            "provider_input_tokens_observed": False,
            "post_count_budget_decisions_exercised": False,
            "provider_acceptance_observed": False,
            "later_live_trajectories_observed": False,
            "separate_dynamic_mock_regression": "tests/test_provider_request_gate_runner.py",
            "dynamic_mock_is_not_anyio_performance": True,
        },
        "image_admission_contract": candidate["image_admission_contract"],
        "production_shaped_image_request_start_mock": first_mock,
        "real_docker_identity_observed": False,
        "real_agent_performance_measured": False,
        "reviewed_package_binding": candidate["selection_evidence"]["treatment_lean_v27"],
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
            "consumed_r23_retry_allowed": False,
            "input_count_rehearsal_cannot_grant_live_authority": True,
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
        "candidate_created": materialized,
        "rehearsal_created": materialized,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("Rapid candidate-v33 qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_rapid_public_development_v27_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_rapid_public_development_v27_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    raw = qualification_bytes(value)
    if target.exists():
        if target.read_bytes() != raw:
            raise ContractError("Rapid candidate-v33 qualification already differs")
        return value
    _write_once(target, raw)
    return value


def load_rapid_public_development_v27_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("Rapid candidate-v33 qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("Rapid candidate-v33 qualification bytes differ")
    if value != build_rapid_public_development_v27_qualification(root):
        raise ContractError("Rapid candidate-v33 qualification source binding differs")
    return value


def validate_stored_qualification(
    candidate: dict[str, Any], *, repository: str | Path = "."
) -> dict[str, Any]:
    """Read-only live preflight: never re-execute the isolated qualification mocks."""
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    if target.is_symlink() or not target.is_file():
        raise ContractError("R24 requires its frozen offline qualification")
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
        candidate_identity = value["candidate"]
        rehearsal_identity = value["rehearsal"]
        boundary = value["pre_count_boundary"]
        mock = value["production_shaped_image_request_start_mock"]
        source = [_source_identity(root, path) for path in SOURCE_FILES]
        valid = (
            qualification_bytes(value) == raw
            and value["schema_version"] == SCHEMA_VERSION
            and value["status"] == "offline-qualified-awaiting-exact-paid-approval"
            and value["experiment_id"] == EXPERIMENT_ID
            and value["paid_execution_authorized"] is False
            and value["candidate_created"] is True
            and value["rehearsal_created"] is True
            and value["source_files"] == source
            and candidate_identity["execution_hash"] == candidate["execution_hash"]
            and candidate_identity["content_hash"] == candidate["content_hash"]
            and candidate_identity["runtime_build_hash"] == candidate["runtime_build_hash"]
            and candidate_identity["file_sha256"] == sha256_bytes(candidate_bytes(candidate))
            and candidate_identity["bytes"] == len(candidate_bytes(candidate))
            and candidate_identity["path"] == CANDIDATE_PATH.as_posix()
            and sha256_json(value["provider_request_contract"])
            == sha256_json(candidate["provider_request_contract"])
            and boundary["row_request_count"] == 6
            and boundary["actual_public_task_and_model"] is True
            and boundary["provider_acceptance_observed"] is False
            and rehearsal_identity["generation_count"] == 2
            and rehearsal_identity["byte_identical"] is True
            and rehearsal_identity["path"] == REHEARSAL_PATH.as_posix()
            and rehearsal_identity["file_sha256"]
            == _source_identity(root, REHEARSAL_PATH.as_posix())["file_sha256"]
            and mock["real_agent_start_count"] == 6
            and mock["pre_count_gate_count"] == 6
            and mock["provider_gate_count"] == 6
            and mock["mocked_docker_image_inspect_commands"] == 1
            and mock["actual_docker_calls"] == 0
            and all(
                type(value["evidence_boundary"][name]) is int
                and value["evidence_boundary"][name] == 0
                for name in (
                    "provider_calls",
                    "docker_calls",
                    "task_calls",
                    "evaluator_calls",
                    "visible_check_calls",
                    "network_calls",
                )
            )
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ContractError("R24 frozen qualification is invalid") from exc
    if not valid:
        raise ContractError("R24 frozen qualification no longer binds the candidate")
    return value


__all__ = [
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_rapid_public_development_v27_qualification",
    "load_rapid_public_development_v27_qualification",
    "materialize_rapid_public_development_v27_qualification",
    "qualification_bytes",
    "validate_stored_qualification",
]
