"""Prepare the offline D-125 A/C runtime-finalization qualification gate.

D-125 binds the exact historical D-124 seal and the reviewed source paths for
repository-local paid-boundary consumption and final campaign sealing.  It
does not authorize or execute a live experiment.  The reviewed runtime
identities are exact post-hardening source identities supplied by the audits.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from patchloop.errors import ContractError
from patchloop.evals import d122_ac_fixed_bundle_qualification as d122
from patchloop.evals import d124_ac_settlement_reconciliation_correction as d124
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-125"
SCHEMA_VERSION = "ac-runtime-finalization-offline-source-gate-d125-v1"
STATUS = "D125_AC_RUNTIME_FINALIZATION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED"
SEALED_HISTORICAL_GATE_ID = "d125_ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539"
SEALED_HISTORICAL_BODY_SHA256 = (
    "sha256:ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539"
)
SEALED_HISTORICAL_FILE_SHA256 = (
    "sha256:9bc5f6e618f31312dc5026a807eabf478e47c05893cca72c71328378b593856e"
)
SEALED_HISTORICAL_FILE_BYTES = 13_820

D124_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d124-ac-cost-settlement-reconciliation-correction-source-gate.json"
)
D124_GATE_ID = "d124_4d9b60873850fbd6b871d4ca45e2a9043bc19f53c8b960307bff0143dd5c1855"
D124_BODY_SHA256 = "sha256:4d9b60873850fbd6b871d4ca45e2a9043bc19f53c8b960307bff0143dd5c1855"
D124_FILE_SHA256 = "sha256:c5677bd6bdfcf1dc97edb624d00471afefc04e7dfd9826fcab68def7385f2396"
D124_FILE_BYTES = 23_279
D124_STATUS = "D124_AC_SETTLEMENT_RECONCILIATION_CORRECTED_EXECUTION_CANDIDATE_BLOCKED"
D124_RECORDED_AT = "2026-08-08T10:17:56.670095Z"
D124_CORRECTION_CONTRACT_SHA256 = (
    "sha256:cea8d119696f6f7f7c41aa3e3ff6fdd8cef754a8a0a928010f0aa49e871e0bf0"
)
D124_INHERITED_AC_CONTRACT_SHA256 = (
    "sha256:2c2e5868430acd0052b550ae9cf9c405df201a631d6d0135b8b50fad43442ce4"
)
D124_SUITE_HASH = "sha256:4564e57268619174c26ff85f243d2cb95cbb3f7cd7008cdf7391148913c2e9ce"
D124_SCHEDULE_HASH = "sha256:df8c06972308783f6d02364f4e785b4f2ddb2602be0f56b4f487387cf2ea4bcc"
D124_COST_CONTROL_HASH = "sha256:bd0093aeba056185c23991c2b5f5841c81f09fa4513462b40b2a1138871d7dcc"
D124_COMPLETION_CONTRACT_HASH = (
    "sha256:94a1868965b01265db5aa13180f64d15f0091d4c4f3c858f7ed9a884209e9730"
)
EXPERIMENT_ID = "dev-validation-ac-fixed-bundle-readiness-20260808-r2"

OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/d125-ac-runtime-finalization-offline-source-gate.json"
)

REVIEWED_AGENT_RUNNER_FILE_BYTES: int | None = 239_930
REVIEWED_AGENT_RUNNER_FILE_SHA256: str | None = (
    "sha256:dfddea4c185a9edbc433c93ff6dac17dee4edfad3d61422e2c1b0520acfcbbff"
)
REVIEWED_STATE_STORE_FILE_BYTES: int | None = 44_023
REVIEWED_STATE_STORE_FILE_SHA256: str | None = (
    "sha256:3d54a347028abffc1b1f997c740513239fa542ec64b78beb63a7d5a74b6f4284"
)
REVIEWED_EVAL_RUNNER_FILE_BYTES: int | None = 409_780
REVIEWED_EVAL_RUNNER_FILE_SHA256: str | None = (
    "sha256:57f1c11f0db97d72f582b090a51ab4c3f7c2d998bb52d98db2cfb753e55d2461"
)
REVIEWED_ROW_CLAIM_TEST_FILE_BYTES: int | None = 20_767
REVIEWED_ROW_CLAIM_TEST_FILE_SHA256: str | None = (
    "sha256:54a900ece5455dc1b247164bb4faf4b5e8817fd905ccc698a0539fac3fad924e"
)
REVIEWED_FINALIZATION_TEST_FILE_BYTES: int | None = 18_283
REVIEWED_FINALIZATION_TEST_FILE_SHA256: str | None = (
    "sha256:5f61870a1f91d124a331626686f6932587516cf997c4cceea5ec528356e9c12e"
)
REVIEWED_EXPERIMENTS_TEST_FILE_BYTES: int | None = 183_098
REVIEWED_EXPERIMENTS_TEST_FILE_SHA256: str | None = (
    "sha256:d2c8356b6eae0f27b7c8efac606db127cc531ccaa722ef5c30f0c60b18cd74a9"
)

REVIEWED_RUNTIME_PATHS = (
    Path("patchloop/agent/runner.py"),
    Path("patchloop/state/store.py"),
    Path("patchloop/evals/runner.py"),
    Path("tests/test_ac_row_start_consumption.py"),
    Path("tests/test_ac_campaign_finalization.py"),
    Path("tests/test_experiments.py"),
)
IMPLEMENTATION_PATHS = REVIEWED_RUNTIME_PATHS + (
    Path("patchloop/evals/d124_ac_settlement_reconciliation_correction.py"),
    Path("patchloop/evals/d125_ac_runtime_finalization_qualification.py"),
    Path("scripts/build_d124_ac_settlement_reconciliation_correction.py"),
    Path("scripts/build_d125_ac_runtime_finalization_qualification.py"),
    Path("tests/test_d124_ac_settlement_reconciliation_correction.py"),
    Path("tests/test_d125_ac_runtime_finalization_qualification.py"),
)

ROOT_KEYS = (
    "schema_version",
    "gate_id",
    "semantic_body_hash",
    "semantic_body",
)
BODY_KEYS = (
    "milestone",
    "evidence_kind",
    "recorded_at",
    "status",
    "predecessor_binding",
    "inherited_contract_binding",
    "runtime_finalization_contract",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)
BLOCKED_PREREQUISITES = (
    "clean-committed-source-identity-not-sealed",
    "fresh-official-pricing-within-72-hours-not-verified",
    "separately-authorized-no-call-docker-sdk-and-credential-presence-preflight-not-completed",
    "exact-runner-execution-hash-not-created",
    "one-use-execution-authorization-candidate-not-created",
    "separate-candidate-triple-execution-hash-and-55-dollar-cap-approval-missing",
)


class D125QualificationError(ContractError):
    """Raised when D-125 source qualification is unavailable or drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D125QualificationError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D125QualificationError("D-125 repository root is unavailable") from exc
    _require(root.is_dir(), "D-125 repository root is not a directory")
    return root


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d122._stable_read(root, relative)
    except ContractError as exc:
        raise D125QualificationError(f"D-125 cannot stably read {relative.as_posix()}") from exc


def _file_binding(root: Path, relative: Path) -> dict[str, Any]:
    content = _stable_read(root, relative)
    return {
        "path": relative.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _reviewed_source_expectations() -> dict[str, dict[str, Any] | None]:
    raw = {
        "patchloop/agent/runner.py": (
            REVIEWED_AGENT_RUNNER_FILE_BYTES,
            REVIEWED_AGENT_RUNNER_FILE_SHA256,
        ),
        "patchloop/state/store.py": (
            REVIEWED_STATE_STORE_FILE_BYTES,
            REVIEWED_STATE_STORE_FILE_SHA256,
        ),
        "patchloop/evals/runner.py": (
            REVIEWED_EVAL_RUNNER_FILE_BYTES,
            REVIEWED_EVAL_RUNNER_FILE_SHA256,
        ),
        "tests/test_ac_row_start_consumption.py": (
            REVIEWED_ROW_CLAIM_TEST_FILE_BYTES,
            REVIEWED_ROW_CLAIM_TEST_FILE_SHA256,
        ),
        "tests/test_ac_campaign_finalization.py": (
            REVIEWED_FINALIZATION_TEST_FILE_BYTES,
            REVIEWED_FINALIZATION_TEST_FILE_SHA256,
        ),
        "tests/test_experiments.py": (
            REVIEWED_EXPERIMENTS_TEST_FILE_BYTES,
            REVIEWED_EXPERIMENTS_TEST_FILE_SHA256,
        ),
    }
    expectations: dict[str, dict[str, Any] | None] = {}
    for path, (file_bytes, file_sha256) in raw.items():
        if file_bytes is None or file_sha256 is None:
            expectations[path] = None
        else:
            expectations[path] = {
                "path": path,
                "file_bytes": file_bytes,
                "file_sha256": file_sha256,
            }
    return expectations


def _implementation_state(root: Path) -> dict[str, Any]:
    files = [_file_binding(root, path) for path in IMPLEMENTATION_PATHS]
    by_path = {item["path"]: item for item in files}
    reviewed = _reviewed_source_expectations()
    _require(
        all(expected is not None for expected in reviewed.values()),
        "D-125 reviewed runtime source identities are pending",
    )
    _require(
        all(by_path.get(path) == expected for path, expected in reviewed.items()),
        "D-125 reviewed runtime source identities differ",
    )
    return {
        "files": files,
        "file_count": len(files),
        "fingerprint": sha256_text(canonical_json(files)),
        "reviewed_runtime_files": [by_path[path.as_posix()] for path in REVIEWED_RUNTIME_PATHS],
        "reviewed_runtime_file_count": len(REVIEWED_RUNTIME_PATHS),
    }


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), f"D-125 {label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D125QualificationError(f"D-125 {label} is invalid") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        f"D-125 {label} is timezone-naive",
    )
    return parsed


def _predecessor_state(root: Path) -> dict[str, Any]:
    _require(
        d124.OUTPUT_PATH == D124_PATH
        and d124.SEALED_HISTORICAL_GATE_ID == D124_GATE_ID
        and d124.SEALED_HISTORICAL_BODY_SHA256 == D124_BODY_SHA256
        and d124.SEALED_HISTORICAL_FILE_SHA256 == D124_FILE_SHA256
        and d124.SEALED_HISTORICAL_FILE_BYTES == D124_FILE_BYTES
        and d124.STATUS == D124_STATUS,
        "D-125 D-124 constants differ from the independently pinned predecessor",
    )
    result = d124.validate_d124_correction_gate(
        repository=root,
        mode="sealed-historical",
    )
    _require(
        result
        == {
            "status": D124_STATUS,
            "gate_id": D124_GATE_ID,
            "semantic_body_hash": D124_BODY_SHA256,
            "file_bytes": D124_FILE_BYTES,
            "file_sha256": D124_FILE_SHA256,
            "execution_authorization_candidate_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "docker_calls_made": 0,
        },
        "D-125 D-124 sealed validation differs",
    )
    raw = _stable_read(root, D124_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D125QualificationError("D-125 cannot parse the D-124 seal") from exc
    body = payload.get("semantic_body") if isinstance(payload, dict) else None
    _require(isinstance(body, dict), "D-125 D-124 semantic body is missing")
    correction = body.get("correction_contract")
    inherited = body.get("inherited_ac_contract")
    authority = body.get("authority")
    _require(
        sha256_text(canonical_json(correction)) == D124_CORRECTION_CONTRACT_SHA256
        and sha256_text(canonical_json(inherited)) == D124_INHERITED_AC_CONTRACT_SHA256,
        "D-125 D-124 inherited contract hashes differ",
    )
    _require(isinstance(inherited, dict), "D-125 D-124 inherited A/C contract is missing")
    suite = inherited.get("suite_binding")
    schedule = inherited.get("schedule_binding")
    cost = inherited.get("cost_reservation_and_settlement_contract")
    completion = inherited.get("completion_gate_contract")
    control = cost.get("control") if isinstance(cost, dict) else None
    _require(
        isinstance(suite, dict)
        and suite.get("experiment_id") == EXPERIMENT_ID
        and suite.get("suite_hash") == D124_SUITE_HASH
        and isinstance(schedule, dict)
        and schedule.get("schedule_hash") == D124_SCHEDULE_HASH
        and isinstance(control, dict)
        and control.get("content_hash") == D124_COST_CONTROL_HASH
        and isinstance(completion, dict)
        and completion.get("contract_hash") == D124_COMPLETION_CONTRACT_HASH,
        "D-125 exact inherited A/C binding differs",
    )
    _require(
        body.get("recorded_at") == D124_RECORDED_AT
        and isinstance(authority, dict)
        and authority.get("execution_authorization_candidate_ready") is False
        and authority.get("exact_execution_hash_created") is False
        and authority.get("reservation_executed") is False
        and authority.get("completion_result_present") is False
        and authority.get("provider_calls_made") == 0
        and authority.get("evaluator_calls_made") == 0
        and authority.get("docker_calls_made") == 0
        and authority.get("agent_runs_made") == 0
        and authority.get("retrieval_calls_made") == 0
        and authority.get("added_model_cost_usd") == 0,
        "D-125 D-124 chronology or closed authority differs",
    )
    return {
        "predecessor_binding": {
            "milestone": "D-124",
            "path": D124_PATH.as_posix(),
            "gate_id": D124_GATE_ID,
            "semantic_body_hash": D124_BODY_SHA256,
            "file_bytes": D124_FILE_BYTES,
            "file_sha256": D124_FILE_SHA256,
            "status": D124_STATUS,
            "recorded_at": D124_RECORDED_AT,
            "validation_mode": "sealed-historical",
            "artifact_mutated": False,
            "execution_or_result_existed": False,
        },
        "inherited_contract_binding": {
            "experiment_id": EXPERIMENT_ID,
            "correction_contract_hash": D124_CORRECTION_CONTRACT_SHA256,
            "inherited_ac_contract_hash": D124_INHERITED_AC_CONTRACT_SHA256,
            "suite_hash": D124_SUITE_HASH,
            "schedule_hash": D124_SCHEDULE_HASH,
            "cost_control_hash": D124_COST_CONTROL_HASH,
            "completion_contract_hash": D124_COMPLETION_CONTRACT_HASH,
        },
        "predecessor_recorded_at": D124_RECORDED_AT,
    }


def _runtime_finalization_contract() -> dict[str, Any]:
    contract = {
        "schema_version": "ac-runtime-finalization-source-contract-d125-v1",
        "experiment_id": EXPERIMENT_ID,
        "qualification_grade": "offline-source-and-mocked-fault-boundary-tests",
        "row_start_consumption": {
            "schema_version": "ac-row-start-paid-boundary-consumption-contract-d125-v1",
            "state_schema": "ac-fixed-bundle-row-start-consumption-v1",
            "marker_schema": "ac-fixed-bundle-row-start-consumption-marker-v1",
            "identity_fields": ["execution_hash", "schedule_row_id", "run_id"],
            "run_started_event_and_journal_prefix_hash_bound": True,
            "sqlite_unique_consumption_precedes_paid_execute": True,
            "durable_marker_precedes_paid_execute": True,
            "marker_failure_preserves_sqlite_consumption_and_blocks_execute": True,
            "journal_revalidated_before_consumption": True,
            "replacement_run_and_journal_reset_rejected": True,
            "repository_local_at_most_once_paid_boundary_verified": True,
            "cross_store_atomicity_claimed": False,
            "run_started_to_sqlite_crash_gap_policy": "fail-closed-no-resume",
            "crash_gap_liveness_or_recovery_verified": False,
            "whole_root_rollback_protection_verified": False,
            "whole_root_rollback_excluded_from_qualified_scope": True,
            "global_or_cross_clone_exclusion_claimed": False,
            "d087_or_d097_behavior_changed": False,
        },
        "campaign_finalization_recovery": {
            "schema_version": "ac-final-result-campaign-completed-recovery-contract-d125-v1",
            "unique_same_directory_temp_written_fsynced_and_stable_verified": True,
            "deterministic_prepared_path_published_by_hard_link_no_replace": True,
            "final_output_published_from_prepared_by_hard_link_no_replace": True,
            "result_published_before_campaign_completed": True,
            "recovery_requires_exact_prepared_result": True,
            "recovery_revalidates_plan_journal_result_and_aggregates": True,
            "recovery_reruns_row_agent_provider_or_evaluator": False,
            "recoverable_fault_boundaries": [
                "after_prepared_result_fsync",
                "after_result_publish",
                "after_campaign_completed_append",
            ],
            "exactly_one_campaign_completed_event_required": True,
            "repeated_exact_recovery_is_idempotent": True,
            "foreign_exact_copy_partial_directory_symlink_and_racing_collisions_fail_closed": True,
            "unprepared_rows_are_not_resumed": True,
            "mocked_process_fault_boundary_finalization_recovery_verified": True,
            "actual_process_kill_executed": False,
            "torn_write_or_power_loss_durability_verified": False,
            "noncooperative_path_swap_protection_verified": False,
            "noncooperative_path_swap_excluded_from_qualified_scope": True,
        },
        "automatic_retry_replacement_or_live_resume_allowed": False,
        "production_execution_or_recovery_observed": False,
    }
    return {
        "contract": contract,
        "contract_hash": sha256_text(canonical_json(contract)),
    }


def _external_test_attestation() -> dict[str, Any]:
    return {
        "attestation_kind": "self-attested-external-to-builder",
        "builder_executed_tests": False,
        "row_start_consumption": {
            "selections_are_node_disjoint": True,
            "distinct_collected_tests_passed": 147,
            "focused_reruns_counted_as_additional_evidence": False,
            "selections": [
                {
                    "label": "row-claim-focused",
                    "pytest_selection": ["tests/test_ac_row_start_consumption.py"],
                    "passed": 12,
                    "collected": 12,
                },
                {
                    "label": "d087-legacy",
                    "pytest_selection": [
                        "tests/test_d087_execution_binding.py",
                        "tests/test_d087_cost_runner.py",
                        "tests/test_d087_cost_journal.py",
                        "tests/test_d087_campaign_cost_policy.py",
                    ],
                    "passed": 51,
                    "collected": 51,
                },
                {
                    "label": "d097-and-state-store-legacy",
                    "pytest_selection": [
                        "tests/test_d097_runtime_v2.py",
                        "tests/test_d097_runtime_independent_review.py",
                        "tests/test_state_store.py",
                    ],
                    "passed": 44,
                    "collected": 44,
                },
                {
                    "label": "ac-cost-completion",
                    "pytest_selection": ["tests/test_ac_fixed_bundle_cost_completion.py"],
                    "passed": 40,
                    "collected": 40,
                },
            ],
        },
        "campaign_finalization": {
            "component_selections_are_node_disjoint": True,
            "distinct_collected_tests_passed": 136,
            "combined_union_is_overlapping_corroboration": True,
            "selections": [
                {
                    "label": "focused-finalization",
                    "command": (
                        "uv run --offline pytest -q -p no:cacheprovider "
                        "--basetemp tmp-d125-finalization-hardening-focused-2 "
                        "tests/test_ac_campaign_finalization.py"
                    ),
                    "passed": 14,
                    "collected": 14,
                    "counted_in_distinct_total": True,
                },
                {
                    "label": "ac-and-stale-generic",
                    "command": (
                        "uv run --offline pytest -q -p no:cacheprovider "
                        "--basetemp tmp-d125-finalization-hardening-ac "
                        "tests/test_ac_fixed_bundle_cost_completion.py "
                        "tests/test_experiments.py::"
                        "test_approved_pilot_persists_plan_manifest_and_qualification"
                    ),
                    "passed": 41,
                    "collected": 41,
                    "counted_in_distinct_total": True,
                },
                {
                    "label": "d087-d097-legacy",
                    "command": (
                        "uv run --offline pytest -q -p no:cacheprovider "
                        "--basetemp tmp-d125-finalization-hardening-legacy "
                        "tests/test_d087_cost_runner.py "
                        "tests/test_d087_cost_journal.py "
                        "tests/test_d087_execution_binding.py "
                        "tests/test_d087_campaign_cost_policy.py "
                        "tests/test_d097_runtime_v2.py "
                        "tests/test_d097_runtime_independent_review.py"
                    ),
                    "passed": 81,
                    "collected": 81,
                    "counted_in_distinct_total": True,
                },
                {
                    "label": "combined-union-rerun",
                    "command": (
                        "uv run --offline pytest -q -p no:cacheprovider "
                        "--basetemp tmp-d125-finalization-hardening-combined "
                        "tests/test_ac_campaign_finalization.py "
                        "tests/test_ac_fixed_bundle_cost_completion.py "
                        "tests/test_experiments.py::"
                        "test_approved_pilot_persists_plan_manifest_and_qualification "
                        "tests/test_d087_cost_runner.py "
                        "tests/test_d087_cost_journal.py "
                        "tests/test_d087_execution_binding.py "
                        "tests/test_d087_campaign_cost_policy.py "
                        "tests/test_d097_runtime_v2.py "
                        "tests/test_d097_runtime_independent_review.py"
                    ),
                    "passed": 136,
                    "collected": 136,
                    "counted_in_distinct_total": False,
                },
            ],
        },
        "row_and_finalization_totals_are_non_additive_due_to_overlap": True,
        "unique_total_across_both_attestations_claimed": False,
    }


def _body(
    *,
    recorded_at: str,
    source: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label="recorded_at")
        >= _parse_time(source["predecessor_recorded_at"], label="D-124 recorded_at"),
        "D-125 chronology precedes D-124",
    )
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "offline-ac-runtime-finalization-source-qualification",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_binding": source["predecessor_binding"],
        "inherited_contract_binding": source["inherited_contract_binding"],
        "runtime_finalization_contract": _runtime_finalization_contract(),
        "implementation_integrity": implementation,
        "offline_qualification": {
            "d124_sealed_historical_bytes_validated": True,
            "d124_artifact_preserved": True,
            "reviewed_runtime_source_identities_bound": True,
            "repository_local_at_most_once_paid_boundary_source_qualified": True,
            "mocked_process_fault_boundary_finalization_recovery_source_qualified": True,
            "focused_test_execution_external_to_builder": True,
            "external_test_attestation": _external_test_attestation(),
            "actual_process_kill_executed": False,
            "live_reservation_or_recovery_executed": False,
            "execution_authorization_candidate_ready": False,
        },
        "blocked_prerequisites": list(BLOCKED_PREREQUISITES),
        "evidence_boundary": {
            "development_validation_ac_only": True,
            "qualification_grade": "offline-source-and-mocked-fault-boundary-tests",
            "live_reservation_or_row_claim_executed": False,
            "production_completion_result_present": False,
            "live_finalization_recovery_executed": False,
            "cross_store_atomicity_claimed": False,
            "crash_gap_liveness_verified": False,
            "actual_process_kill_executed": False,
            "torn_write_or_power_loss_durability_verified": False,
            "whole_root_rollback_protection_verified": False,
            "whole_root_rollback_excluded_from_qualified_scope": True,
            "noncooperative_path_swap_protection_verified": False,
            "noncooperative_path_swap_excluded_from_qualified_scope": True,
            "global_or_cross_clone_exclusion_claimed": False,
            "fresh_official_pricing_verified": False,
            "clean_committed_source_verified": False,
            "docker_or_sdk_preflight_verified": False,
            "provider_or_evaluator_result_present": False,
            "memory_effect_or_negative_transfer_result_present": False,
        },
        "authority": {
            "exact_d124_predecessor_bound": True,
            "d125_offline_source_gate_materialized": True,
            "repository_local_at_most_once_paid_boundary_consumption_verified": True,
            "cross_store_atomic_row_start_consumption_verified": False,
            "mocked_process_fault_boundary_finalization_recovery_verified": True,
            "actual_process_kill_recovery_verified": False,
            "torn_write_or_power_loss_recovery_verified": False,
            "reservation_executed": False,
            "completion_result_present": False,
            "fresh_pricing_lookup_authorized": False,
            "docker_or_sdk_preflight_authorized": False,
            "exact_execution_hash_created": False,
            "approved_execution_hash": None,
            "execution_candidate_prepared": False,
            "execution_authorization_candidate_ready": False,
            "provider_execution_authorized": False,
            "evaluator_execution_authorized": False,
            "runtime_memory_injection_authorized": False,
            "retrieval_authorized": False,
            "agent_execution_authorized": False,
            "analysis_or_memory_benefit_claim_authorized": False,
            "core_or_heldout_campaign_authorized": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "docker_calls_made": 0,
            "agent_runs_made": 0,
            "retrieval_calls_made": 0,
            "added_model_cost_usd": 0,
        },
        "next_gate": {
            "action": "separately-authorize-clean-source-pricing-and-no-call-preflight",
            "requires_exact_d125_gate_id_body_and_file_sha": True,
            "clean_committed_source_sealing_authorized": False,
            "fresh_official_pricing_lookup_authorized": False,
            "no_call_docker_sdk_credential_and_endpoint_preflight_authorized": False,
            "exact_execution_hash_or_candidate_creation_authorized": False,
            "provider_evaluator_agent_or_runtime_memory_execution_authorized": False,
            "later_candidate_approval_must_repeat_candidate_triple_execution_hash_and_cap": True,
            "hard_cap_usd": 55.0,
            "does_not_authorize_execution": True,
        },
    }
    _require(tuple(body) == BODY_KEYS, "D-125 semantic body fields differ")
    return body


def _source_state(root: Path) -> dict[str, Any]:
    return _predecessor_state(root)


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d125_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    _require(tuple(payload) == ROOT_KEYS, "D-125 gate fields differ")
    return payload


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _validate_payload(
    *,
    root: Path,
    payload: dict[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    _require(set(payload) == set(ROOT_KEYS), "D-125 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-125 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-125 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-125 semantic body fields differ")
    expected = _envelope(
        _body(
            recorded_at=body.get("recorded_at"),
            source=_source_state(root),
            implementation=_implementation_state(root),
        )
    )
    _require(raw == _canonical_bytes(expected), "D-125 full expected payload differs")
    return expected


def _result(payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    return {
        "status": payload["semantic_body"]["status"],
        "gate_id": payload["gate_id"],
        "semantic_body_hash": payload["semantic_body_hash"],
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "execution_authorization_candidate_ready": False,
        "provider_calls_made": 0,
        "evaluator_calls_made": 0,
        "docker_calls_made": 0,
    }


def _validate_sealed_historical_payload(
    *,
    payload: dict[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    _require(set(payload) == set(ROOT_KEYS), "D-125 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-125 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-125 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-125 semantic body fields differ")
    _parse_time(body.get("recorded_at"), label="recorded_at")
    _require(body.get("status") == STATUS, "D-125 sealed status differs")
    _require(raw == _canonical_bytes(payload), "D-125 gate bytes are noncanonical")
    body_hash = sha256_text(canonical_json(body))
    _require(body_hash == SEALED_HISTORICAL_BODY_SHA256, "D-125 sealed body differs")
    _require(
        payload.get("semantic_body_hash") == body_hash,
        "D-125 semantic body hash differs",
    )
    _require(
        payload.get("gate_id") == SEALED_HISTORICAL_GATE_ID,
        "D-125 sealed gate ID differs",
    )
    _require(len(raw) == SEALED_HISTORICAL_FILE_BYTES, "D-125 sealed size differs")
    _require(
        sha256_bytes(raw) == SEALED_HISTORICAL_FILE_SHA256,
        "D-125 sealed file hash differs",
    )
    return payload


def validate_d125_source_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "sealed-historical"] = "current-source",
) -> dict[str, Any]:
    """Validate D-125 against current sources or its exact historical bytes."""

    root = _repo_root(repository)
    raw = _stable_read(root, OUTPUT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D125QualificationError("D-125 gate is not canonical UTF-8 JSON") from exc
    _require(isinstance(payload, dict), "D-125 gate root is not an object")
    if mode == "current-source":
        validated = _validate_payload(root=root, payload=payload, raw=raw)
    elif mode == "sealed-historical":
        validated = _validate_sealed_historical_payload(payload=payload, raw=raw)
    else:
        raise D125QualificationError("D-125 validation mode is unsupported")
    return _result(validated, raw)


def _fsync_directory_best_effort(path: Path) -> bool:
    if os.name == "nt":
        return False
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return True


def _write_new(root: Path, payload: dict[str, Any]) -> bytes:
    try:
        selected = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D125QualificationError("D-125 output path is unsafe") from exc
    _require(not selected.exists(), "D-125 source gate already exists")
    content = _canonical_bytes(payload)
    temporary = selected.with_name(f".{selected.name}.{uuid.uuid4().hex}.tmp")
    try:
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise D125QualificationError(
                "D-125 temporary source gate cannot be written durably"
            ) from exc
        temporary_relative = temporary.relative_to(root)
        temporary_content = _stable_read(root, temporary_relative)
        _require(
            temporary_content == content,
            "D-125 temporary source gate differs from exact bytes",
        )
        try:
            os.link(temporary, selected)
        except FileExistsError as exc:
            raise D125QualificationError("D-125 source gate publication collision") from exc
        except OSError as exc:
            raise D125QualificationError(
                "D-125 source gate cannot be atomically published"
            ) from exc
        observed = _stable_read(root, OUTPUT_PATH)
        _require(observed == content, "D-125 source gate changed after publication")
        _fsync_directory_best_effort(selected.parent)
        return observed
    finally:
        with suppress(OSError):
            temporary.unlink()


def run_d125_offline_source_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    try:
        output = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D125QualificationError("D-125 output path is unsafe") from exc
    if output.exists():
        return validate_d125_source_gate(repository=root)
    source = _source_state(root)
    implementation = _implementation_state(root)
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = _envelope(
        _body(recorded_at=recorded_at, source=source, implementation=implementation)
    )
    raw = _write_new(root, payload)
    _validate_payload(root=root, payload=payload, raw=raw)
    return _result(payload, raw)


__all__ = [
    "D125QualificationError",
    "OUTPUT_PATH",
    "SEALED_HISTORICAL_BODY_SHA256",
    "SEALED_HISTORICAL_FILE_BYTES",
    "SEALED_HISTORICAL_FILE_SHA256",
    "SEALED_HISTORICAL_GATE_ID",
    "run_d125_offline_source_gate",
    "validate_d125_source_gate",
]
