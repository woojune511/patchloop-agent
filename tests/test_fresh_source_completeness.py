from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

import patchloop.evals.fresh_source_completeness as completeness_module
from patchloop.errors import ContractError
from patchloop.evals.fresh_candidate_registry import (
    FileBinding,
    FreshPublicSourceSnapshot,
    PublicCandidateRow,
    build_fresh_candidate_registry,
    build_qualified_fresh_candidate_registry,
    load_qualified_fresh_candidate_registry,
    materialize_qualified_fresh_candidate_registry,
    public_row_hash,
    qualified_registry_bytes,
    source_snapshot_bytes,
)
from patchloop.evals.fresh_source_completeness import (
    FreshSourceCompletenessError,
    FreshSourceCompletenessQualification,
    NormalizationTranscript,
    NormalizationTranscriptRow,
    SourceCaptureReceipt,
    SourceFormatAdapterQualification,
    adapter_source_qualification_bytes,
    load_fresh_source_completeness_qualification,
    normalization_transcript_bytes,
    qualification_bytes,
    source_capture_receipt_bytes,
)
from patchloop.util import sha256_bytes, sha256_json

REPOSITORY = Path(__file__).resolve().parents[1]


def _row() -> PublicCandidateRow:
    body = {
        "source_ordinal": 1,
        "canonical_public_instance_id": "qualified-public-instance",
        "upstream_repository": "future/repository",
        "issue_or_pull_request_url": "https://github.com/future/repository/issues/1",
        "upstream_base_commit": "1" * 40,
        "resolution_commit": "2" * 40,
        "issue_created_at": "2026-04-01T00:00:00Z",
        "resolution_merged_at": "2026-04-02T00:00:00Z",
        "license_spdx": "MIT",
        "license_compatibility": "pass",
        "public_difficulty_tier": "hard",
        "environment_image": "registry.example/future@sha256:" + "3" * 64,
    }
    return PublicCandidateRow(**body, public_row_hash=public_row_hash(body))


def _snapshot() -> FreshPublicSourceSnapshot:
    row = _row()
    body = {
        "schema_version": "lean-fresh-public-source-snapshot-v1",
        "snapshot_id": "qualified-synthetic-2026-08",
        "candidate_source_family": "SWE-rebench-leaderboard",
        "source_url": "https://example.invalid/immutable-source",
        "source_revision": "4" * 40,
        "source_published_at": "2026-08-17T00:00:00Z",
        "source_window_start_exclusive": "2026-03-17T23:59:59Z",
        "source_window_end_inclusive": "2026-08-16T23:59:59Z",
        "immutable_revision_asserted": True,
        "earliest_qualifying_revision_asserted": True,
        "complete_frozen_window_asserted": True,
        "raw_source_file_bytes": 12_345,
        "raw_source_file_sha256": "sha256:" + "5" * 64,
        "normalization_rule": (
            "public-identity-provenance-difficulty-license-and-image-fields-only-v1"
        ),
        "query_universe": "every-row-in-bound-immutable-source-snapshot",
        "solution_or_test_patch_fields_included": False,
        "oracle_fields_included": False,
        "private_fields_included": False,
        "external_completeness_assertions_qualified": False,
        "raw_source_row_count": 1,
        "declared_source_row_count": 1,
        "rows": (row,),
    }
    hashed = {
        key: [row.model_dump(mode="json")] if key == "rows" else value
        for key, value in body.items()
    }
    return FreshPublicSourceSnapshot(**body, content_hash=sha256_json(hashed))


def _write_snapshot(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source_snapshot_bytes(_snapshot()))
    return path.relative_to(REPOSITORY).as_posix()


def _adapter_qualification() -> SourceFormatAdapterQualification:
    body = {
        "schema_version": "lean-fresh-source-format-adapter-source-qualification-v1",
        "qualification_id": ("lean-fresh-source-format-adapter-synthetic-source-qualification-v1"),
        "status": "SOURCE_FORMAT_ADAPTER_QUALIFIED_NO_RAW_SOURCE_AUTHORITY",
        "adapter_id": "synthetic-public-source-adapter-v1",
        "adapter_source_hash": "sha256:" + "6" * 64,
        "adapter_validation_hash": "sha256:" + "7" * 64,
        "public_projection_schema": "lean-fresh-public-source-snapshot-v1",
        "required_qualification_method": (
            "isolated-source-specific-adapter-with-complete-row-transcript-v1"
        ),
        "authority": {
            "source_files_read": 1,
            "validation_files_read": 1,
            "raw_source_files_read": 0,
            "task_package_files_read": 0,
            "private_task_files_read": 0,
            "network_calls": 0,
            "docker_calls": 0,
            "provider_calls": 0,
            "evaluator_calls": 0,
            "agent_runs": 0,
            "added_model_cost_usd": 0,
            "adapter_source_qualified": True,
            "raw_source_qualification_executed": False,
            "public_registry_projection_authorized": False,
            "task_admission_authorized": False,
            "execution_authorized": False,
        },
    }
    return SourceFormatAdapterQualification(**body, content_hash=sha256_json(body))


def _write_adapter_qualification(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(adapter_source_qualification_bytes(_adapter_qualification()))
    return path.relative_to(REPOSITORY).as_posix()


def _source_capture_receipt(snapshot: FreshPublicSourceSnapshot) -> SourceCaptureReceipt:
    body = {
        "schema_version": "lean-fresh-raw-source-capture-receipt-v1",
        "candidate_source_family": snapshot.candidate_source_family,
        "source_url": snapshot.source_url,
        "source_revision": snapshot.source_revision,
        "source_published_at": snapshot.source_published_at,
        "immutable_revision_resolved": True,
        "earliest_qualifying_revision_verified": True,
        "complete_frozen_window_verified": True,
        "source_listing_or_pagination_exhausted": True,
        "raw_source_file_bytes": snapshot.raw_source_file_bytes,
        "raw_source_file_sha256": snapshot.raw_source_file_sha256,
        "raw_source_row_count": snapshot.raw_source_row_count,
        "provider_declared_row_count": snapshot.declared_source_row_count,
    }
    return SourceCaptureReceipt(**body, content_hash=sha256_json(body))


def _normalization_transcript(snapshot: FreshPublicSourceSnapshot) -> NormalizationTranscript:
    rows = tuple(
        NormalizationTranscriptRow(
            source_ordinal=row.source_ordinal,
            raw_public_projection_hash="sha256:" + f"{row.source_ordinal:064x}",
            normalized_public_row_hash=row.public_row_hash,
        )
        for row in snapshot.rows
    )
    body = {
        "schema_version": "lean-fresh-public-normalization-transcript-v1",
        "source_revision": snapshot.source_revision,
        "raw_source_file_sha256": snapshot.raw_source_file_sha256,
        "row_count": len(rows),
        "rows": [row.model_dump(mode="json") for row in rows],
        "solution_test_oracle_private_fields_persisted": 0,
    }
    return NormalizationTranscript(**body, content_hash=sha256_json(body))


def _write_source_evidence(
    directory: Path,
    snapshot_path: str,
) -> tuple[str, str]:
    snapshot = FreshPublicSourceSnapshot.model_validate_json(
        (REPOSITORY / snapshot_path).read_bytes()
    )
    receipt_path = directory / "source-capture-receipt.json"
    transcript_path = directory / "normalization-transcript.json"
    receipt_path.write_bytes(source_capture_receipt_bytes(_source_capture_receipt(snapshot)))
    transcript_path.write_bytes(normalization_transcript_bytes(_normalization_transcript(snapshot)))
    return (
        receipt_path.relative_to(REPOSITORY).as_posix(),
        transcript_path.relative_to(REPOSITORY).as_posix(),
    )


def _qualification(
    snapshot_path: str,
    adapter_qualification_path: str,
    receipt_path: str,
    transcript_path: str,
) -> FreshSourceCompletenessQualification:
    snapshot_path_obj = REPOSITORY / snapshot_path
    snapshot_raw = snapshot_path_obj.read_bytes()
    snapshot = FreshPublicSourceSnapshot.model_validate_json(snapshot_raw)
    adapter_path_obj = REPOSITORY / adapter_qualification_path
    adapter_raw = adapter_path_obj.read_bytes()
    adapter = SourceFormatAdapterQualification.model_validate_json(adapter_raw)
    receipt_raw = (REPOSITORY / receipt_path).read_bytes()
    receipt = SourceCaptureReceipt.model_validate_json(receipt_raw)
    transcript_raw = (REPOSITORY / transcript_path).read_bytes()
    transcript = NormalizationTranscript.model_validate_json(transcript_raw)
    body = {
        "schema_version": "lean-fresh-raw-source-completeness-qualification-v1",
        "qualification_id": "lean-fresh-source-completeness-qualified-synthetic-2026-08-v1",
        "status": "RAW_SOURCE_COMPLETE_FOR_PUBLIC_REGISTRY_PROJECTION_ONLY",
        "source_snapshot_binding": FileBinding(
            path=snapshot_path,
            file_bytes=len(snapshot_raw),
            file_sha256=sha256_bytes(snapshot_raw),
            content_hash=snapshot.content_hash,
            role="normalized-public-source-snapshot",
        ),
        "raw_source_identity": {
            "candidate_source_family": snapshot.candidate_source_family,
            "source_url": snapshot.source_url,
            "source_revision": snapshot.source_revision,
            "source_published_at": snapshot.source_published_at,
            "source_window_start_exclusive": snapshot.source_window_start_exclusive,
            "source_window_end_inclusive": snapshot.source_window_end_inclusive,
            "raw_source_file_bytes": snapshot.raw_source_file_bytes,
            "raw_source_file_sha256": snapshot.raw_source_file_sha256,
            "raw_source_row_count": snapshot.raw_source_row_count,
            "provider_declared_row_count": snapshot.declared_source_row_count,
        },
        "completeness_checks": {
            "immutable_revision_verified": True,
            "earliest_qualifying_revision_verified": True,
            "complete_frozen_window_verified": True,
            "source_listing_or_pagination_exhausted": True,
            "raw_file_bytes_and_hash_verified": True,
            "provider_and_raw_row_counts_equal": True,
            "normalized_rows_account_for_every_raw_row_exactly_once": True,
            "normalized_ordinals_contiguous": True,
            "public_identity_unique": True,
            "public_row_hashes_recomputed": True,
            "forbidden_solution_test_oracle_private_fields_excluded": True,
            "raw_parser_isolated_from_selector": True,
            "raw_source_bytes_persisted_in_qualification": False,
        },
        "evidence": {
            "qualification_method": (
                "isolated-source-specific-adapter-with-complete-row-transcript-v1"
            ),
            "source_format_adapter": "synthetic-public-source-adapter-v1",
            "source_format_adapter_qualification_binding": FileBinding(
                path=adapter_qualification_path,
                file_bytes=len(adapter_raw),
                file_sha256=sha256_bytes(adapter_raw),
                content_hash=adapter.content_hash,
                role="raw-source-format-adapter-qualification",
            ).model_dump(mode="json"),
            "qualifier_source_hash": "sha256:" + "6" * 64,
            "qualifier_validation_hash": "sha256:" + "7" * 64,
            "source_capture_receipt_binding": FileBinding(
                path=receipt_path,
                file_bytes=len(receipt_raw),
                file_sha256=sha256_bytes(receipt_raw),
                content_hash=receipt.content_hash,
                role="raw-source-capture-receipt",
            ).model_dump(mode="json"),
            "normalization_transcript_binding": FileBinding(
                path=transcript_path,
                file_bytes=len(transcript_raw),
                file_sha256=sha256_bytes(transcript_raw),
                content_hash=transcript.content_hash,
                role="public-normalization-transcript",
            ).model_dump(mode="json"),
            "source_capture_receipt_hash": receipt.content_hash,
            "normalization_transcript_hash": transcript.content_hash,
            "normalization_transcript_rows": 1,
        },
        "authority": {
            "raw_source_files_read_by_isolated_qualifier": 1,
            "normalized_snapshot_files_read": 1,
            "selector_raw_source_files_read": 0,
            "task_package_files_read": 0,
            "private_task_files_read": 0,
            "solution_test_patch_or_oracle_fields_persisted": 0,
            "network_calls_during_offline_replay": 0,
            "docker_calls": 0,
            "provider_calls": 0,
            "evaluator_calls": 0,
            "agent_runs": 0,
            "added_model_cost_usd": 0,
            "raw_source_completeness_qualified": True,
            "public_registry_projection_authorized": True,
            "task_admission_authorized": False,
            "fresh_panel_materialized": False,
            "full_experiment_preregistered": False,
            "candidate_created": False,
            "approval_granted": False,
            "execution_authorized": False,
            "official_analysis_authorized": False,
            "memory_effect_claim_authorized": False,
        },
        "next_gate": (
            "run-the-frozen-public-selector-and-audit-the-complete-transcript-before-task-admission"
        ),
    }
    dumped = {
        key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        for key, value in body.items()
    }
    return FreshSourceCompletenessQualification(**body, content_hash=sha256_json(dumped))


def _write_qualification(
    path: Path,
    snapshot_path: str,
    adapter_qualification_path: str,
    receipt_path: str,
    transcript_path: str,
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        qualification_bytes(
            _qualification(
                snapshot_path,
                adapter_qualification_path,
                receipt_path,
                transcript_path,
            )
        )
    )
    return path.relative_to(REPOSITORY).as_posix()


def _fixture(tmp_path: Path) -> tuple[str, str, str, str, str]:
    snapshot_path = _write_snapshot(tmp_path / "source.json")
    adapter_path = _write_adapter_qualification(tmp_path / "adapter-source-qualification.json")
    receipt_path, transcript_path = _write_source_evidence(tmp_path, snapshot_path)
    qualification_path = _write_qualification(
        tmp_path / "qualification.json",
        snapshot_path,
        adapter_path,
        receipt_path,
        transcript_path,
    )
    return snapshot_path, adapter_path, receipt_path, transcript_path, qualification_path


def test_qualification_binds_snapshot_and_raw_completeness_claims(tmp_path: Path) -> None:
    snapshot_path, _, _, _, qualification_path = _fixture(tmp_path)
    value, raw = load_fresh_source_completeness_qualification(REPOSITORY, qualification_path)

    assert value.source_snapshot_binding.path == snapshot_path
    assert value.raw_source_identity.raw_source_row_count == 1
    assert value.evidence.normalization_transcript_rows == 1
    assert value.completeness_checks.raw_parser_isolated_from_selector is True
    assert value.authority.public_registry_projection_authorized is True
    assert value.authority.task_admission_authorized is False
    assert raw == qualification_bytes(value)


def test_unqualified_projection_stays_unqualified_and_wrapper_holds_authority(
    tmp_path: Path,
) -> None:
    snapshot_path, _, _, _, qualification_path = _fixture(tmp_path)
    projection = build_fresh_candidate_registry(REPOSITORY, snapshot_path)
    qualified = build_qualified_fresh_candidate_registry(REPOSITORY, qualification_path)

    assert projection.authority.source_snapshot_externally_qualified is False
    assert projection.authority.candidate_registry_qualified is False
    assert qualified.projection == projection
    assert qualified.authority.source_snapshot_externally_qualified is True
    assert qualified.authority.candidate_registry_qualified is True
    assert qualified.authority.task_admission_authorized is False
    assert qualified.status == "QUALIFIED_PUBLIC_REGISTRY_INSUFFICIENT_POOL"


def test_qualified_materialization_is_append_only_and_idempotent(tmp_path: Path) -> None:
    _, _, _, _, qualification_path = _fixture(tmp_path / "input")
    output = tmp_path / "qualified-registry.json"
    output_path = output.relative_to(REPOSITORY).as_posix()

    first = materialize_qualified_fresh_candidate_registry(
        REPOSITORY,
        source_qualification_path=qualification_path,
        output_path=output_path,
    )
    before = output.stat().st_mtime_ns
    second = materialize_qualified_fresh_candidate_registry(
        REPOSITORY,
        source_qualification_path=qualification_path,
        output_path=output_path,
    )

    assert first == second
    assert output.stat().st_mtime_ns == before
    assert output.read_bytes() == qualified_registry_bytes(first)
    assert load_qualified_fresh_candidate_registry(REPOSITORY, output_path) == first


def test_missing_qualification_cannot_open_selector() -> None:
    with pytest.raises(FreshSourceCompletenessError, match="unavailable"):
        build_qualified_fresh_candidate_registry(REPOSITORY, "reports/missing-qualification.json")


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    [
        ("raw_source_identity", "raw_source_file_sha256", "sha256:" + "0" * 64),
        ("evidence", "normalization_transcript_rows", 2),
        ("authority", "task_admission_authorized", True),
        ("completeness_checks", "source_listing_or_pagination_exhausted", False),
    ],
)
def test_rehashed_qualification_drift_fails_closed(
    tmp_path: Path,
    section: str,
    field: str,
    replacement: object,
) -> None:
    _, _, _, _, qualification_path = _fixture(tmp_path)
    selected = REPOSITORY / qualification_path
    body = json.loads(selected.read_text(encoding="utf-8"))
    body[section][field] = replacement
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    selected.write_bytes((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    with pytest.raises((FreshSourceCompletenessError, ValidationError)):
        load_fresh_source_completeness_qualification(REPOSITORY, qualification_path)


def test_snapshot_drift_after_qualification_fails_closed(tmp_path: Path) -> None:
    snapshot_path, _, _, _, qualification_path = _fixture(tmp_path)
    selected = REPOSITORY / snapshot_path
    selected.write_bytes(selected.read_bytes() + b" ")

    with pytest.raises(FreshSourceCompletenessError, match="snapshot binding differs"):
        load_fresh_source_completeness_qualification(REPOSITORY, qualification_path)


def _rebind_evidence_file(
    qualification_path: str,
    *,
    binding_field: str,
    evidence_path: str,
    evidence_content_hash: str,
    hash_field: str | None = None,
) -> None:
    selected = REPOSITORY / qualification_path
    body = json.loads(selected.read_text(encoding="utf-8"))
    evidence_raw = (REPOSITORY / evidence_path).read_bytes()
    binding = body["evidence"][binding_field]
    binding["file_bytes"] = len(evidence_raw)
    binding["file_sha256"] = sha256_bytes(evidence_raw)
    binding["content_hash"] = evidence_content_hash
    if hash_field is not None:
        body["evidence"][hash_field] = evidence_content_hash
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    selected.write_bytes((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def test_fully_rehashed_transcript_mapping_drift_fails_closed(tmp_path: Path) -> None:
    snapshot_path, _, _, transcript_path, qualification_path = _fixture(tmp_path)
    selected = REPOSITORY / transcript_path
    body = json.loads(selected.read_text(encoding="utf-8"))
    body["rows"][0]["normalized_public_row_hash"] = "sha256:" + "0" * 64
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    selected.write_bytes((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    _rebind_evidence_file(
        qualification_path,
        binding_field="normalization_transcript_binding",
        evidence_path=transcript_path,
        evidence_content_hash=body["content_hash"],
        hash_field="normalization_transcript_hash",
    )

    with pytest.raises(FreshSourceCompletenessError, match="does not map every snapshot row"):
        load_fresh_source_completeness_qualification(REPOSITORY, qualification_path)
    assert (REPOSITORY / snapshot_path).is_file()


def test_rehashed_adapter_source_identity_drift_fails_closed(tmp_path: Path) -> None:
    _, adapter_path, _, _, qualification_path = _fixture(tmp_path)
    selected = REPOSITORY / adapter_path
    body = json.loads(selected.read_text(encoding="utf-8"))
    body["adapter_source_hash"] = "sha256:" + "0" * 64
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    selected.write_bytes((json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    _rebind_evidence_file(
        qualification_path,
        binding_field="source_format_adapter_qualification_binding",
        evidence_path=adapter_path,
        evidence_content_hash=body["content_hash"],
    )

    with pytest.raises(FreshSourceCompletenessError, match="adapter qualification identity"):
        load_fresh_source_completeness_qualification(REPOSITORY, qualification_path)


def test_qualified_selector_reads_only_public_contract_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot_path, adapter_path, receipt_path, transcript_path, qualification_path = _fixture(
        tmp_path
    )
    reads: list[Path] = []
    original = Path.read_bytes

    def tracked(path: Path) -> bytes:
        reads.append(path.resolve(strict=False))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    build_qualified_fresh_candidate_registry(REPOSITORY, qualification_path)

    relative = {path.relative_to(REPOSITORY).as_posix() for path in reads}
    assert relative == {
        "data/dataset-manifest.yaml",
        "experiments/lean-harness-fresh-acquisition-preregistration-20260817-v1.json",
        adapter_path,
        receipt_path,
        snapshot_path,
        transcript_path,
        qualification_path,
    }
    assert all("tasks/" not in path and ".patchloop/" not in path for path in relative)


def test_qualified_selector_performs_no_external_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _, _, qualification_path = _fixture(tmp_path)

    def bomb(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("qualified selector attempted external execution")

    monkeypatch.setattr(socket, "create_connection", bomb)
    monkeypatch.setattr(socket.socket, "connect", bomb)
    monkeypatch.setattr(subprocess, "Popen", bomb)
    build_qualified_fresh_candidate_registry(REPOSITORY, qualification_path)


def test_consumer_module_has_no_raw_parser_or_external_execution_imports() -> None:
    source = Path(completeness_module.__file__).read_text(encoding="utf-8").lower()
    for forbidden in (
        "pyarrow",
        "pandas",
        "polars",
        "from patchloop.agent",
        "from patchloop.task_loader",
        "import subprocess",
        "import socket",
        "import openai",
        "import docker",
        "import requests",
        "import httpx",
        "import urllib",
    ):
        assert forbidden not in source


def test_generic_experiment_loader_rejects_qualification_and_registry(tmp_path: Path) -> None:
    from patchloop.evals.runner import load_suite

    _, _, _, _, qualification_path = _fixture(tmp_path / "input")
    qualification = REPOSITORY / qualification_path
    registry = tmp_path / "registry.json"
    registry.write_bytes(
        qualified_registry_bytes(
            build_qualified_fresh_candidate_registry(REPOSITORY, qualification_path)
        )
    )

    for path in (qualification, registry):
        with pytest.raises(ContractError, match="experiment contract validation failed"):
            load_suite(path)
