"""Seal the append-only D-124 correction to D-123 settlement evidence.

D-124 preserves the immutable D-123 gate, binds the corrected final-state
reconciliation rule, and keeps every live execution authority closed.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from patchloop.errors import ContractError
from patchloop.evals import d122_ac_fixed_bundle_qualification as d122
from patchloop.evals import d123_ac_cost_completion_qualification as d123
from patchloop.evals.runner import _terminal_cost_settlement_reconciliation_passed
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MILESTONE = "D-124"
SCHEMA_VERSION = "ac-cost-settlement-reconciliation-correction-source-gate-d124-v1"
STATUS = "D124_AC_SETTLEMENT_RECONCILIATION_CORRECTED_EXECUTION_CANDIDATE_BLOCKED"
SEALED_HISTORICAL_GATE_ID = "d124_4d9b60873850fbd6b871d4ca45e2a9043bc19f53c8b960307bff0143dd5c1855"
SEALED_HISTORICAL_BODY_SHA256 = (
    "sha256:4d9b60873850fbd6b871d4ca45e2a9043bc19f53c8b960307bff0143dd5c1855"
)
SEALED_HISTORICAL_FILE_SHA256 = (
    "sha256:c5677bd6bdfcf1dc97edb624d00471afefc04e7dfd9826fcab68def7385f2396"
)
SEALED_HISTORICAL_FILE_BYTES = 23_279

D123_PATH = Path("reports/live-pilot/artifacts/d123-ac-cost-completion-offline-source-gate.json")
D123_GATE_ID = "d123_13fe44a6cc188de29dc38876fb60d114c8a777f8d05ad8b9db833b3d33cf4112"
D123_BODY_SHA256 = "sha256:13fe44a6cc188de29dc38876fb60d114c8a777f8d05ad8b9db833b3d33cf4112"
D123_FILE_SHA256 = "sha256:fab1543644ffefb9e4cda24d73207d3d9f66c07a5a1e006dec27a22699778e17"
D123_FILE_BYTES = 20_953
D123_STATUS = "D123_AC_COST_COMPLETION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED"
D123_RUNNER_FILE_BYTES = 382_006
D123_RUNNER_FILE_SHA256 = "sha256:210d983168c01bf5bf569f440a7259d3d4b093a32da165f75adc3da519bf8936"
D123_COST_TEST_FILE_BYTES = 47_589
D123_COST_TEST_FILE_SHA256 = (
    "sha256:6efa519243dabe98c2c4572e29b3be9fef2f85a3d77fa6779691863009ae9c2c"
)
CORRECTED_RUNNER_FILE_BYTES = 383_282
CORRECTED_RUNNER_FILE_SHA256 = (
    "sha256:07c479c865f3f0d7f421c18b1a86bb687ebb2aeb93e7eade1df81dc3615d5c80"
)
CORRECTED_COST_TEST_FILE_BYTES = 55_561
CORRECTED_COST_TEST_FILE_SHA256 = (
    "sha256:5d7e35e59c767f6e979bedd1bc330870c5097f47ee72c949919a17f4613c226b"
)

OUTPUT_PATH = Path(
    "reports/live-pilot/artifacts/"
    "d124-ac-cost-settlement-reconciliation-correction-source-gate.json"
)
IMPLEMENTATION_PATHS = (
    Path("patchloop/agent/runner.py"),
    Path("patchloop/evals/qualification.py"),
    Path("patchloop/evals/runner.py"),
    Path("patchloop/evals/d123_ac_cost_completion_qualification.py"),
    Path("patchloop/evals/d124_ac_settlement_reconciliation_correction.py"),
    Path("patchloop/runtime.py"),
    Path("scripts/build_d123_ac_cost_completion_qualification.py"),
    Path("scripts/build_d124_ac_settlement_reconciliation_correction.py"),
    Path("tests/test_ac_fixed_bundle_cost_completion.py"),
    Path("tests/test_d123_ac_cost_completion_qualification.py"),
    Path("tests/test_d124_ac_settlement_reconciliation_correction.py"),
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
    "finding",
    "correction_contract",
    "inherited_ac_contract",
    "implementation_integrity",
    "offline_qualification",
    "blocked_prerequisites",
    "evidence_boundary",
    "authority",
    "next_gate",
)
BLOCKED_PREREQUISITES = (
    "atomic-row-start-one-use-consumption-not-yet-qualified",
    "final-result-and-campaign-completed-crash-collision-recovery-not-yet-qualified",
    "clean-committed-source-identity-not-sealed",
    "fresh-official-pricing-within-72-hours-not-verified",
    "separately-authorized-no-call-docker-sdk-and-credential-presence-preflight-not-completed",
    "exact-runner-execution-hash-not-created",
    "one-use-execution-authorization-candidate-not-created",
    "separate-candidate-triple-execution-hash-and-55-dollar-cap-approval-missing",
)


class D124CorrectionError(ContractError):
    """Raised when the D-124 correction seal or source closure drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D124CorrectionError(message)


def _repo_root(repository: str | Path | None) -> Path:
    selected = Path(repository) if repository is not None else repository_root()
    try:
        root = selected.resolve(strict=True)
    except OSError as exc:
        raise D124CorrectionError("D-124 repository root is unavailable") from exc
    _require(root.is_dir(), "D-124 repository root is not a directory")
    return root


def _stable_read(root: Path, relative: Path) -> bytes:
    try:
        return d122._stable_read(root, relative)
    except ContractError as exc:
        raise D124CorrectionError(f"D-124 cannot stably read {relative.as_posix()}") from exc


def _file_binding(root: Path, relative: Path) -> dict[str, Any]:
    content = _stable_read(root, relative)
    return {
        "path": relative.as_posix(),
        "file_bytes": len(content),
        "file_sha256": sha256_bytes(content),
    }


def _implementation_state(root: Path) -> dict[str, Any]:
    files = [_file_binding(root, path) for path in IMPLEMENTATION_PATHS]
    by_path = {item["path"]: item for item in files}
    _require(
        by_path.get("patchloop/evals/runner.py")
        == {
            "path": "patchloop/evals/runner.py",
            "file_bytes": CORRECTED_RUNNER_FILE_BYTES,
            "file_sha256": CORRECTED_RUNNER_FILE_SHA256,
        }
        and by_path.get("tests/test_ac_fixed_bundle_cost_completion.py")
        == {
            "path": "tests/test_ac_fixed_bundle_cost_completion.py",
            "file_bytes": CORRECTED_COST_TEST_FILE_BYTES,
            "file_sha256": CORRECTED_COST_TEST_FILE_SHA256,
        },
        "D-124 reviewed correction source identities differ",
    )
    return {
        "files": files,
        "file_count": len(files),
        "fingerprint": sha256_text(canonical_json(files)),
    }


def _predecessor_binding(root: Path) -> tuple[dict[str, Any], str]:
    _require(
        d123.OUTPUT_PATH == D123_PATH
        and d123.SEALED_HISTORICAL_GATE_ID == D123_GATE_ID
        and d123.SEALED_HISTORICAL_BODY_SHA256 == D123_BODY_SHA256
        and d123.SEALED_HISTORICAL_FILE_SHA256 == D123_FILE_SHA256
        and d123.SEALED_HISTORICAL_FILE_BYTES == D123_FILE_BYTES
        and d123.STATUS == D123_STATUS,
        "D-124 D-123 constants differ from the independently pinned predecessor",
    )
    result = d123.validate_d123_source_gate(repository=root, mode="sealed-historical")
    _require(
        result
        == {
            "status": D123_STATUS,
            "gate_id": D123_GATE_ID,
            "semantic_body_hash": D123_BODY_SHA256,
            "file_bytes": D123_FILE_BYTES,
            "file_sha256": D123_FILE_SHA256,
            "execution_authorization_candidate_ready": False,
            "provider_calls_made": 0,
            "evaluator_calls_made": 0,
            "docker_calls_made": 0,
        },
        "D-124 D-123 sealed validation differs",
    )
    raw = _stable_read(root, D123_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D124CorrectionError("D-124 cannot parse the D-123 seal") from exc
    body = payload.get("semantic_body") if isinstance(payload, dict) else None
    _require(isinstance(body, dict), "D-124 D-123 semantic body is missing")
    cost = body.get("cost_reservation_and_settlement_contract")
    journal = cost.get("journal_contract") if isinstance(cost, dict) else None
    authority = body.get("authority")
    implementation = body.get("implementation_integrity")
    files = implementation.get("files") if isinstance(implementation, dict) else None
    historical_files = (
        {item.get("path"): item for item in files if isinstance(item, dict)}
        if isinstance(files, list)
        else {}
    )
    _require(
        isinstance(journal, dict)
        and journal.get("settlement_unavailable_is_sealed_as_inconclusive") is True
        and isinstance(authority, dict)
        and authority.get("execution_authorization_candidate_ready") is False
        and authority.get("provider_execution_authorized") is False
        and authority.get("evaluator_execution_authorized") is False
        and authority.get("reservation_executed") is False,
        "D-124 D-123 finding or closed authority differs",
    )
    _require(
        historical_files.get("patchloop/evals/runner.py")
        == {
            "path": "patchloop/evals/runner.py",
            "file_bytes": D123_RUNNER_FILE_BYTES,
            "file_sha256": D123_RUNNER_FILE_SHA256,
        }
        and historical_files.get("tests/test_ac_fixed_bundle_cost_completion.py")
        == {
            "path": "tests/test_ac_fixed_bundle_cost_completion.py",
            "file_bytes": D123_COST_TEST_FILE_BYTES,
            "file_sha256": D123_COST_TEST_FILE_SHA256,
        },
        "D-124 historical D-123 implementation binding differs",
    )
    recorded_at = body.get("recorded_at")
    _require(isinstance(recorded_at, str), "D-124 D-123 chronology is missing")
    return (
        {
            "milestone": "D-123",
            "path": D123_PATH.as_posix(),
            "gate_id": D123_GATE_ID,
            "semantic_body_hash": D123_BODY_SHA256,
            "file_bytes": D123_FILE_BYTES,
            "file_sha256": D123_FILE_SHA256,
            "status": D123_STATUS,
            "validation_mode": "sealed-historical",
            "artifact_mutated": False,
            "execution_or_result_existed": False,
            "historical_implementation": {
                "runner": historical_files["patchloop/evals/runner.py"],
                "cost_test": historical_files["tests/test_ac_fixed_bundle_cost_completion.py"],
            },
        },
        recorded_at,
    )


def _truth_table_probe() -> dict[str, Any]:
    evidence_hash = "sha256:" + "1" * 64
    evidence = {"content_hash": evidence_hash}
    cases = {
        "exact-final-durable-state": {
            "usage_reconciliation_passed": True,
            "persisted_result_passed": True,
            "settled_run_cost_nanos": 1,
            "durable_usage_evidence": evidence,
            "usage_evidence_hash": evidence_hash,
        },
        "usage-projection-failed": {
            "usage_reconciliation_passed": False,
            "persisted_result_passed": True,
            "settled_run_cost_nanos": 1,
            "durable_usage_evidence": evidence,
            "usage_evidence_hash": evidence_hash,
        },
        "persisted-result-projection-failed": {
            "usage_reconciliation_passed": True,
            "persisted_result_passed": False,
            "settled_run_cost_nanos": 1,
            "durable_usage_evidence": evidence,
            "usage_evidence_hash": evidence_hash,
        },
        "durable-evidence-missing": {
            "usage_reconciliation_passed": True,
            "persisted_result_passed": True,
            "settled_run_cost_nanos": 1,
            "durable_usage_evidence": None,
            "usage_evidence_hash": evidence_hash,
        },
        "durable-hash-missing": {
            "usage_reconciliation_passed": True,
            "persisted_result_passed": True,
            "settled_run_cost_nanos": 1,
            "durable_usage_evidence": evidence,
            "usage_evidence_hash": None,
        },
        "durable-hash-mismatch": {
            "usage_reconciliation_passed": True,
            "persisted_result_passed": True,
            "settled_run_cost_nanos": 1,
            "durable_usage_evidence": evidence,
            "usage_evidence_hash": "sha256:" + "2" * 64,
        },
        "settlement-unavailable": {
            "usage_reconciliation_passed": True,
            "persisted_result_passed": True,
            "settled_run_cost_nanos": None,
            "durable_usage_evidence": None,
            "usage_evidence_hash": None,
        },
    }
    observed = {
        name: _terminal_cost_settlement_reconciliation_passed(**values)
        for name, values in cases.items()
    }
    expected = {
        "exact-final-durable-state": True,
        "usage-projection-failed": False,
        "persisted-result-projection-failed": False,
        "durable-evidence-missing": False,
        "durable-hash-missing": False,
        "durable-hash-mismatch": False,
        "settlement-unavailable": False,
    }
    _require(observed == expected, "D-124 final-state truth-table probe differs")
    return {
        "schema_version": "ac-final-settlement-truth-table-probe-d124-v1",
        "observed": observed,
        "passed": True,
    }


def _correction_contract() -> dict[str, Any]:
    return {
        "schema_version": "ac-settlement-reconciliation-correction-d124-v1",
        "corrected_helper": "_terminal_cost_settlement_reconciliation_passed",
        "final_state_inputs": [
            "usage_reconciliation_projection_passed",
            "persisted_result_projection_passed",
            "settled_run_cost_nanos_present",
            "durable_usage_evidence_present",
            "durable_usage_content_hash_exact",
        ],
        "all_final_state_inputs_required": True,
        "durable_load_hash_or_reprice_failure_forces_false": True,
        "run_terminal_records_final_settlement_reconciliation": True,
        "unavailable_settlement_event_records_no_usage_hash": True,
        "unavailable_settlement_cost_qualification_passed": False,
        "unavailable_settlement_completion_disposition": "inconclusive",
        "d123_artifact_rewritten": False,
        "runtime_failure_path_live_executed": False,
        "focused_regressions": [
            "final-durable-state-truth-table",
            "mocked-evaluate-suite-durable-loader-failure-persists-inconclusive-result",
        ],
        "focused_regressions_use_mock_runtime_only": True,
        "builder_truth_table_probe": _truth_table_probe(),
    }


def _source_state(root: Path) -> dict[str, Any]:
    predecessor, predecessor_time = _predecessor_binding(root)
    inherited = d123._source_state(root)
    _require(
        inherited["suite_binding"]["experiment_id"]
        == "dev-validation-ac-fixed-bundle-readiness-20260808-r2"
        and inherited["schedule_binding"]["expected_run_count"] == 4
        and inherited["cost_reservation_and_settlement_contract"]["reservation_executed"] is False
        and inherited["completion_gate_contract"]["completion_result_present"] is False,
        "D-124 inherited A/C source contract differs",
    )
    return {
        "predecessor_binding": predecessor,
        "predecessor_recorded_at": predecessor_time,
        "inherited_ac_contract": inherited,
        "correction_contract": _correction_contract(),
    }


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str), f"D-124 {label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D124CorrectionError(f"D-124 {label} is invalid") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        f"D-124 {label} is timezone-naive",
    )
    return parsed


def _body(
    *,
    recorded_at: str,
    source: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    _require(
        _parse_time(recorded_at, label="recorded_at")
        >= _parse_time(source["predecessor_recorded_at"], label="D-123 recorded_at"),
        "D-124 chronology precedes D-123",
    )
    finding = {
        "finding_code": "stale-terminal-reconciliation-after-durable-settlement-failure",
        "disposition": "CONFIRMED_SOURCE_DEFECT_NO_LIVE_RESULT",
        "discovered_after_d123_materialization": True,
        "affected_claim": (
            "cost_reservation_and_settlement_contract.journal_contract."
            "settlement_unavailable_is_sealed_as_inconclusive"
        ),
        "mechanism": (
            "the runtime emitter could retain qualification-only true after persisted-result "
            "or durable usage settlement became unavailable, while the validator correctly "
            "required false for unavailable evidence"
        ),
        "live_execution_or_cost_result_observed": False,
        "proof_grade": "source-and-offline-test",
    }
    body = {
        "milestone": MILESTONE,
        "evidence_kind": "append-only-post-d123-settlement-reconciliation-correction",
        "recorded_at": recorded_at,
        "status": STATUS,
        "predecessor_binding": source["predecessor_binding"],
        "finding": finding,
        "correction_contract": source["correction_contract"],
        "inherited_ac_contract": source["inherited_ac_contract"],
        "implementation_integrity": implementation,
        "offline_qualification": {
            "d123_sealed_historical_bytes_validated": True,
            "d123_artifact_preserved": True,
            "final_state_reconciliation_source_corrected": True,
            "d123_validator_accepts_correctly_formed_unavailable_evidence": True,
            "runtime_emitter_integration_corrected_prospectively": True,
            "official_scrr_and_verdict_conjunction_preserved": True,
            "focused_test_execution_external_to_builder": True,
            "focused_regression_binding": next(
                item
                for item in implementation["files"]
                if item["path"] == "tests/test_ac_fixed_bundle_cost_completion.py"
            ),
            "live_failure_path_executed": False,
            "execution_authorization_candidate_ready": False,
        },
        "blocked_prerequisites": list(BLOCKED_PREREQUISITES),
        "evidence_boundary": {
            "development_validation_only": True,
            "live_reservation_or_row_claim_executed": False,
            "completion_result_present": False,
            "fresh_official_pricing_verified": False,
            "clean_committed_source_verified": False,
            "docker_or_sdk_preflight_verified": False,
            "provider_or_evaluator_result_present": False,
            "memory_effect_or_negative_transfer_result_present": False,
            "cooperative_single_writer_materialization_assumed": True,
            "global_or_cross_clone_exclusion_claimed": False,
        },
        "authority": {
            "exact_d123_predecessor_bound": True,
            "d124_offline_correction_gate_materialized": True,
            "settlement_reconciliation_source_corrected": True,
            "reservation_executed": False,
            "completion_result_present": False,
            "atomic_row_start_one_use_consumption_verified": False,
            "final_result_and_campaign_completed_recovery_verified": False,
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
            "action": (
                "separately-authorize-resolve-all-runtime-finalization-and-clean-no-call-preflight"
            ),
            "requires_atomic_row_start_one_use_qualification": True,
            "requires_final_result_and_campaign_completed_crash_collision_recovery": True,
            "requires_clean_committed_source": True,
            "requires_fresh_official_pricing_within_72_hours": True,
            "requires_separately_authorized_no_call_docker_sdk_preflight": True,
            "then_prepare_exact_execution_authorization_candidate": True,
            "later_candidate_approval_must_repeat_candidate_triple_execution_hash_and_cap": True,
            "hard_cap_usd": 55.0,
            "does_not_authorize_execution": True,
        },
    }
    _require(tuple(body) == BODY_KEYS, "D-124 semantic body fields differ")
    return body


def _envelope(body: dict[str, Any]) -> dict[str, Any]:
    body_hash = sha256_text(canonical_json(body))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "gate_id": f"d124_{body_hash.removeprefix('sha256:')}",
        "semantic_body_hash": body_hash,
        "semantic_body": body,
    }
    _require(tuple(payload) == ROOT_KEYS, "D-124 gate fields differ")
    return payload


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (canonical_json(payload) + "\n").encode("utf-8")


def _validate_payload(
    *,
    root: Path,
    payload: dict[str, Any],
    raw: bytes,
) -> dict[str, Any]:
    _require(set(payload) == set(ROOT_KEYS), "D-124 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-124 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-124 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-124 semantic body fields differ")
    recorded_at = body.get("recorded_at")
    expected = _envelope(
        _body(
            recorded_at=recorded_at,
            source=_source_state(root),
            implementation=_implementation_state(root),
        )
    )
    _require(raw == _canonical_bytes(expected), "D-124 full expected payload differs")
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
    _require(set(payload) == set(ROOT_KEYS), "D-124 gate root fields differ")
    _require(payload.get("schema_version") == SCHEMA_VERSION, "D-124 schema differs")
    body = payload.get("semantic_body")
    _require(isinstance(body, dict), "D-124 semantic body is missing")
    _require(set(body) == set(BODY_KEYS), "D-124 semantic body fields differ")
    _parse_time(body.get("recorded_at"), label="recorded_at")
    _require(body.get("status") == STATUS, "D-124 sealed status differs")
    _require(raw == _canonical_bytes(payload), "D-124 gate bytes are noncanonical")
    body_hash = sha256_text(canonical_json(body))
    _require(body_hash == SEALED_HISTORICAL_BODY_SHA256, "D-124 sealed body differs")
    _require(
        payload.get("semantic_body_hash") == body_hash,
        "D-124 semantic body hash differs",
    )
    _require(
        payload.get("gate_id") == SEALED_HISTORICAL_GATE_ID,
        "D-124 sealed gate ID differs",
    )
    _require(len(raw) == SEALED_HISTORICAL_FILE_BYTES, "D-124 sealed size differs")
    _require(
        sha256_bytes(raw) == SEALED_HISTORICAL_FILE_SHA256,
        "D-124 sealed file hash differs",
    )
    return payload


def validate_d124_correction_gate(
    *,
    repository: str | Path | None = None,
    mode: Literal["current-source", "sealed-historical"] = "current-source",
) -> dict[str, Any]:
    """Validate D-124 against current sources or its exact historical bytes."""

    root = _repo_root(repository)
    raw = _stable_read(root, OUTPUT_PATH)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D124CorrectionError("D-124 gate is not canonical UTF-8 JSON") from exc
    _require(isinstance(payload, dict), "D-124 gate root is not an object")
    if mode == "current-source":
        validated = _validate_payload(root=root, payload=payload, raw=raw)
    elif mode == "sealed-historical":
        validated = _validate_sealed_historical_payload(payload=payload, raw=raw)
    else:
        raise D124CorrectionError("D-124 validation mode is unsupported")
    return _result(validated, raw)


def _write_new(root: Path, payload: dict[str, Any]) -> bytes:
    try:
        selected = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D124CorrectionError("D-124 output path is unsafe") from exc
    _require(not selected.exists(), "D-124 correction gate already exists")
    content = _canonical_bytes(payload)
    try:
        with selected.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise D124CorrectionError("D-124 correction gate cannot be created") from exc
    observed = _stable_read(root, OUTPUT_PATH)
    _require(observed == content, "D-124 correction gate changed after creation")
    return observed


def run_d124_correction_gate(
    *,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    root = _repo_root(repository)
    try:
        output = d122._logical_path(root, OUTPUT_PATH, must_exist=False)
    except ContractError as exc:
        raise D124CorrectionError("D-124 output path is unsafe") from exc
    if output.exists():
        return validate_d124_correction_gate(repository=root)
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
    "D124CorrectionError",
    "OUTPUT_PATH",
    "SEALED_HISTORICAL_BODY_SHA256",
    "SEALED_HISTORICAL_FILE_BYTES",
    "SEALED_HISTORICAL_FILE_SHA256",
    "SEALED_HISTORICAL_GATE_ID",
    "run_d124_correction_gate",
    "validate_d124_correction_gate",
]
