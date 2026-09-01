from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.evals.fresh_all_cross_successor import (
    ArchiveBinding,
    CandidateObservation,
    PartialVariants,
)
from patchloop.evals.fresh_harbor_admission import (
    INVENTORY_PATH,
    SOURCE_QUALIFICATION_PATH,
    AdmissionEvidenceInventory,
    CandidateEvidenceInventory,
    FreshHarborAdmissionError,
    _capture_candidate,
    _json_object,
    _project_report,
    artifact_bytes,
    build_source_qualification,
    load_evidence_inventory,
    load_source_qualification,
)
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _write_report(
    path: Path,
    *,
    resolved: bool,
    pass_to_pass_ok: bool,
    fail_to_pass_ok: bool,
    passed: int,
    failed: int,
    skipped: int = 0,
    error: int = 0,
) -> bytes:
    body = {
        "fail_to_pass": {f"private-case-{index}": "FAILED" for index in range(failed)},
        "fail_to_pass_ok": fail_to_pass_ok,
        "log_parser": "synthetic-parser",
        "parsed_counts": {
            "PASSED": passed,
            "FAILED": failed,
            "SKIPPED": skipped,
            "ERROR": error,
        },
        "pass_to_pass": {f"public-case-{index}": "PASSED" for index in range(passed)},
        "pass_to_pass_ok": pass_to_pass_ok,
        "resolved": resolved,
    }
    raw = json.dumps(body, sort_keys=True).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _candidate(archive_raw: bytes, reference_raw: bytes) -> CandidateObservation:
    return CandidateObservation(
        instance="synthetic__task-1",
        repository="synthetic/task",
        rank_sha256="sha256:" + "1" * 64,
        package_content_sha256="sha256:" + "2" * 64,
        archive=ArchiveBinding(bytes=len(archive_raw), sha256=sha256_bytes(archive_raw)),
        image_sha256="sha256:" + "3" * 64,
        base_commit="4" * 40,
        resolution_commit="5" * 40,
        license="MIT",
        public_issue_created_at="2026-04-01T00:00:00Z",
        resolution_merged_at="2026-04-02T00:00:00Z",
        base_counts={"pass_to_pass_passed": 2, "fail_to_pass_failed": 1},
        reference_report_sha256=sha256_bytes(reference_raw),
        partial_variants=PartialVariants(tested=8, rejected=8),
    )


def _synthetic_candidate_root(tmp_path: Path) -> tuple[Path, CandidateObservation]:
    source_root = tmp_path / "source"
    candidate_root = source_root / "fresh-admission-synthetic"
    archive_raw = b"opaque-public-package-archive"
    candidate_root.mkdir(parents=True)
    (candidate_root / "dist.tar.gz").write_bytes(archive_raw)
    _write_report(
        candidate_root / "base-nosync-1/logs/verifier/report.json",
        resolved=False,
        pass_to_pass_ok=True,
        fail_to_pass_ok=False,
        passed=2,
        failed=1,
    )
    reference_raw = b""
    for ordinal in range(1, 4):
        raw = _write_report(
            candidate_root / f"reference-nosync-{ordinal}/logs/verifier/report.json",
            resolved=True,
            pass_to_pass_ok=True,
            fail_to_pass_ok=True,
            passed=3,
            failed=0,
        )
        reference_raw = raw
    for name in ("omit-hunk-0", "only-hunk-0"):
        _write_report(
            candidate_root / f"{name}/logs/verifier/report.json",
            resolved=False,
            pass_to_pass_ok=True,
            fail_to_pass_ok=False,
            passed=2,
            failed=1,
        )
    return source_root, _candidate(archive_raw, reference_raw)


def test_report_projection_persists_aggregates_not_private_identifiers(tmp_path: Path) -> None:
    source_root, _candidate_value = _synthetic_candidate_root(tmp_path)
    report_path = source_root / "fresh-admission-synthetic/base-nosync-1/logs/verifier/report.json"
    value = _project_report(report_path, source_root=source_root, role="base", ordinal=1)
    raw = artifact_bytes(value)

    assert value.pass_to_pass_case_count == 2
    assert value.fail_to_pass_case_count == 1
    assert value.raw_test_identifiers_persisted == 0
    assert b"private-case" not in raw
    assert b"public-case" not in raw
    assert b"synthetic-parser" not in raw


def test_candidate_capture_binds_core_receipts_and_keeps_missing_partials_blocking(
    tmp_path: Path,
) -> None:
    source_root, candidate = _synthetic_candidate_root(tmp_path)
    candidate_root = source_root / "fresh-admission-synthetic"
    value, report_reads = _capture_candidate(source_root, candidate_root, candidate)

    assert value.base_contract_verified is True
    assert value.reference_triplicate_verified is True
    assert value.available_partial_receipts == 2
    assert value.available_rejected_partial_receipts == 2
    assert value.missing_partial_receipts == 6
    assert value.raw_receipt_set_complete is False
    assert report_reads == 6


def test_duplicate_keys_closed_schema_and_archive_drift_fail(tmp_path: Path) -> None:
    with pytest.raises(FreshHarborAdmissionError, match="duplicate JSON key"):
        _json_object(b'{"resolved":false,"resolved":true}', label="synthetic")

    source_root, candidate = _synthetic_candidate_root(tmp_path)
    report_path = source_root / "fresh-admission-synthetic/base-nosync-1/logs/verifier/report.json"
    body = json.loads(report_path.read_bytes())
    body["unexpected"] = True
    report_path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(FreshHarborAdmissionError, match="fields differ"):
        _project_report(report_path, source_root=source_root, role="base", ordinal=1)

    source_root, candidate = _synthetic_candidate_root(tmp_path / "second")
    candidate_root = source_root / "fresh-admission-synthetic"
    (candidate_root / "dist.tar.gz").write_bytes(b"drift")
    with pytest.raises(FreshHarborAdmissionError, match="archive binding differs"):
        _capture_candidate(source_root, candidate_root, candidate)


def test_source_qualification_binds_current_source_and_stays_no_call() -> None:
    value = build_source_qualification(REPOSITORY)

    assert value.status == "ADMISSION_SANITIZER_SOURCE_QUALIFIED_NO_RAW_REPLAY_AUTHORITY"
    assert len(value.source_files) == 3
    assert len(value.validation_files) == 1
    assert value.authority.sanitizer_source_qualified is True
    assert value.authority.raw_admission_replay_complete is False
    assert value.authority.docker_calls == value.authority.provider_calls == 0
    assert value.authority.task_package_conversion_authorized is False


def test_checked_in_source_qualification_and_inventory_are_exact() -> None:
    qualification, qualification_raw = load_source_qualification(REPOSITORY)
    inventory, inventory_raw = load_evidence_inventory(REPOSITORY)

    assert artifact_bytes(qualification) == qualification_raw
    assert artifact_bytes(inventory) == inventory_raw
    assert inventory.status == "SANITIZED_RAW_ADMISSION_INVENTORY_INCOMPLETE_ACTIVATION_BLOCKED"
    assert inventory.partial_receipts_expected == 133
    assert inventory.partial_receipts_available == 14
    assert inventory.partial_rejections_available == 14
    assert inventory.partial_receipts_missing == 119
    assert inventory.tasks_with_complete_raw_receipt_set == 1
    assert inventory.all_raw_receipts_available is False
    assert inventory.authority.private_verifier_report_files_read_by_trusted_sanitizer == 62
    assert inventory.authority.docker_calls == inventory.authority.provider_calls == 0
    assert b"::" not in inventory_raw


def test_rehashed_inventory_overclaim_and_extra_fields_are_rejected() -> None:
    value, _raw = load_evidence_inventory(REPOSITORY)
    body = value.model_dump(mode="json")
    body["all_raw_receipts_available"] = True
    body["content_hash"] = sha256_json(
        {key: item for key, item in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError, match="aggregate differs"):
        AdmissionEvidenceInventory.model_validate(body)

    row = value.rows[0].model_dump(mode="json")
    row["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        CandidateEvidenceInventory.model_validate(row)


def test_append_only_artifact_paths_are_not_inside_tasks() -> None:
    assert SOURCE_QUALIFICATION_PATH.startswith("reports/fresh-panel/artifacts/")
    assert INVENTORY_PATH.startswith("reports/fresh-panel/artifacts/")
    assert not SOURCE_QUALIFICATION_PATH.startswith("tasks/")
    assert not INVENTORY_PATH.startswith("tasks/")


def test_source_file_hash_helper_matches_standard_library() -> None:
    raw = (REPOSITORY / "patchloop/evals/fresh_harbor_admission.py").read_bytes()
    assert sha256_bytes(raw) == "sha256:" + hashlib.sha256(raw).hexdigest()
