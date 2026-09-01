"""Sanitize and qualify retained Harbor task-admission evidence without execution.

The trusted sanitizer may read public package archives and evaluator-private
Harbor verifier reports only after the 12-task public panel is frozen.  It
persists report byte identities and aggregate verdict/count fields, never test
identifiers, output text, solution patches, or package contents.  The source
qualification grants only this offline projection.  Missing raw receipts keep
task conversion, runtime qualification, candidate creation, Docker, provider,
and spend authority closed.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.errors import ContractError
from patchloop.evals.fresh_all_cross_successor import (
    CANDIDATE_IDS,
    PLAN_PATH,
    PREREG_PATH,
    REGISTRY_PATH,
    SUITE_PATH,
    CandidateObservation,
    SearchObservation,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SOURCE_QUALIFICATION_SCHEMA = "lean-fresh-harbor-admission-source-qualification-v1"
SOURCE_QUALIFICATION_ID = "lean-fresh-harbor-admission-sanitizer-20260818-r1"
SOURCE_QUALIFICATION_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-admission-source-qualification-r1.json"
)
INVENTORY_SCHEMA = "lean-fresh-harbor-admission-evidence-inventory-v1"
INVENTORY_ID = "lean-fresh-harbor-admission-evidence-availability-20260818-r1"
INVENTORY_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-admission-evidence-inventory-r1.json"
)
OBSERVATION_PATH = "reports/fresh-panel/artifacts/fresh-all-cross-search-observation-v1.json"

PREREG_BYTES = 8_815
PREREG_SHA256 = "sha256:a6d2918b486e36dc2ba6e4d8f586ee4b46a8c2b60a4abb3854b98c4715c99748"
PREREG_CONTENT_HASH = "sha256:12bb5ca18034f7592c4d630ff91c9789a81ff7af22803da3269e68343f234955"
REGISTRY_BYTES = 19_240
REGISTRY_SHA256 = "sha256:2e5565faa2bb2c2b63cb52a4fcde8b920488be1c59acc5538f567a99c26917a6"
REGISTRY_CONTENT_HASH = "sha256:bf4e3711c4b116bd3027781a9f39b3ae0fcf94b38563c83a408061c15e34f135"
SUITE_BYTES = 22_629
SUITE_SHA256 = "sha256:3d81476977071be5e578697e0e4da53e9bdbbdf9e84504af465f8159e40c3a19"
SUITE_CONTENT_HASH = "sha256:f57eded985460f982e908b768d1b512cc6bf6daeaf26e59f86a688343d9f951f"
PLAN_BYTES = 3_726
PLAN_SHA256 = "sha256:d7408a99fc498032f736b8741edb28848e6eb0a963eabfc18546a5a572036939"
PLAN_CONTENT_HASH = "sha256:1f13d5a84fb41ecb83ccc45c16f8fff8551114475cc55041be9ebbe49e75c755"
OBSERVATION_BYTES = 15_689
OBSERVATION_SHA256 = "sha256:fb947e2e6ba227f1993fe41a625ab5fac028d38b4e9ec42a7e859101c85e6e1a"

SOURCE_PATHS = (
    "patchloop/evals/fresh_harbor_admission.py",
    "scripts/build_lean_fresh_harbor_admission_source_qualification.py",
    "scripts/capture_lean_fresh_harbor_admission_inventory.py",
)
VALIDATION_PATHS = ("tests/test_fresh_harbor_admission.py",)

_REPORT_KEYS = frozenset(
    {
        "fail_to_pass",
        "fail_to_pass_ok",
        "log_parser",
        "parsed_counts",
        "pass_to_pass",
        "pass_to_pass_ok",
        "resolved",
    }
)
_COUNT_KEYS = frozenset({"PASSED", "FAILED", "SKIPPED", "ERROR"})
_PARTIAL_DIRECTORY = re.compile(r"^(?:omit|only)-hunk-[0-9]+$")


class FreshHarborAdmissionError(ContractError):
    """A sanitizer source binding or raw admission projection differs."""


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FileBinding(FrozenModel):
    path: str
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    role: str = Field(min_length=1)

    @field_validator("file_bytes", mode="before")
    @classmethod
    def exact_file_bytes(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("file_bytes must be a JSON integer")
        return value


class ExternalRawBinding(FrozenModel):
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("file_bytes", mode="before")
    @classmethod
    def exact_file_bytes(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("external file_bytes must be a JSON integer")
        return value


class ParsedCounts(FrozenModel):
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    error: int = Field(ge=0)

    @model_validator(mode="before")
    @classmethod
    def exact_counts(cls, value: Any) -> Any:
        if isinstance(value, dict) and any(type(item) is not int for item in value.values()):
            raise ValueError("parsed counts must be JSON integers")
        return value


class SanitizedVerifierReport(FrozenModel):
    role: Literal["base", "reference", "partial"]
    ordinal: int = Field(ge=1)
    raw_report: ExternalRawBinding
    resolved: bool
    pass_to_pass_ok: bool
    fail_to_pass_ok: bool
    pass_to_pass_case_count: int = Field(ge=0)
    fail_to_pass_case_count: int = Field(ge=0)
    parsed_counts: ParsedCounts
    log_parser_present: Literal[True]
    raw_test_identifiers_persisted: Literal[0]
    raw_test_outputs_persisted: Literal[0]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="before")
    @classmethod
    def exact_scalars(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in ("ordinal", "pass_to_pass_case_count", "fail_to_pass_case_count"):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        for name in ("resolved", "pass_to_pass_ok", "fail_to_pass_ok"):
            if name in value and type(value[name]) is not bool:
                raise ValueError(f"{name} must be a JSON boolean")
        return value

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("sanitized verifier report content hash differs")
        return self


class CandidateEvidenceInventory(FrozenModel):
    task_id: str
    repository: str
    package_archive: ExternalRawBinding
    base_report: SanitizedVerifierReport
    reference_reports: tuple[SanitizedVerifierReport, ...]
    expected_partial_receipts: int = Field(ge=8)
    expected_rejected_partial_receipts: int = Field(ge=8)
    partial_reports: tuple[SanitizedVerifierReport, ...]
    available_partial_receipts: int = Field(ge=0)
    available_rejected_partial_receipts: int = Field(ge=0)
    missing_partial_receipts: int = Field(ge=0)
    base_contract_verified: Literal[True]
    reference_triplicate_verified: Literal[True]
    available_partial_receipts_sanitized: Literal[True]
    raw_receipt_set_complete: bool
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("reference_reports", "partial_reports", mode="before")
    @classmethod
    def freeze_reports(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="before")
    @classmethod
    def exact_counts(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in (
            "expected_partial_receipts",
            "expected_rejected_partial_receipts",
            "available_partial_receipts",
            "available_rejected_partial_receipts",
            "missing_partial_receipts",
        ):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        if len(self.reference_reports) != 3 or tuple(
            report.ordinal for report in self.reference_reports
        ) != (1, 2, 3):
            raise ValueError("reference report triplicate differs")
        if any(report.role != "reference" for report in self.reference_reports):
            raise ValueError("reference report role differs")
        if self.base_report.role != "base" or self.base_report.ordinal != 1:
            raise ValueError("base report role differs")
        if any(report.role != "partial" for report in self.partial_reports):
            raise ValueError("partial report role differs")
        if tuple(report.ordinal for report in self.partial_reports) != tuple(
            range(1, len(self.partial_reports) + 1)
        ):
            raise ValueError("partial report order differs")
        rejected = sum(not report.resolved for report in self.partial_reports)
        if not (
            self.available_partial_receipts == len(self.partial_reports)
            and self.available_rejected_partial_receipts == rejected
            and self.missing_partial_receipts
            == self.expected_partial_receipts - self.available_partial_receipts
            and self.available_partial_receipts <= self.expected_partial_receipts
            and self.available_rejected_partial_receipts <= self.expected_rejected_partial_receipts
        ):
            raise ValueError("partial receipt counts differ")
        complete = self.missing_partial_receipts == 0
        if complete and rejected != self.expected_rejected_partial_receipts:
            raise ValueError("complete partial receipt rejection count differs")
        if self.raw_receipt_set_complete != complete:
            raise ValueError("raw receipt completeness differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("candidate evidence inventory content hash differs")
        return self


class SourceQualificationAuthority(FrozenModel):
    source_files_read: Literal[3]
    validation_files_read: Literal[1]
    raw_package_archives_read: Literal[0]
    private_verifier_reports_read: Literal[0]
    private_test_identifiers_persisted: Literal[0]
    raw_test_outputs_persisted: Literal[0]
    solution_or_reference_patch_files_read: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    sanitizer_source_qualified: Literal[True]
    raw_admission_replay_complete: Literal[False]
    task_package_conversion_authorized: Literal[False]
    candidate_creation_authorized: Literal[False]
    execution_authorized: Literal[False]


class AdmissionSanitizerSourceQualification(FrozenModel):
    schema_version: Literal[SOURCE_QUALIFICATION_SCHEMA]
    qualification_id: Literal[SOURCE_QUALIFICATION_ID]
    status: Literal["ADMISSION_SANITIZER_SOURCE_QUALIFIED_NO_RAW_REPLAY_AUTHORITY"]
    predecessor_bindings: tuple[FileBinding, ...]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checks: dict[str, bool]
    authority: SourceQualificationAuthority
    next_gate: Literal[
        "capture-sanitized-raw-admission-availability-without-docker-or-task-conversion"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("predecessor_bindings", "source_files", "validation_files", mode="before")
    @classmethod
    def freeze_bindings(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        expected_checks = {
            "duplicate-json-keys-rejected": True,
            "raw-report-top-level-schema-closed": True,
            "report-byte-size-and-sha-bound": True,
            "test-identifiers-counted-not-persisted": True,
            "raw-output-text-not-persisted": True,
            "package-archive-bytes-not-extracted": True,
            "selected-archive-hash-bound-to-frozen-observation": True,
            "base-and-reference-semantics-fail-closed": True,
            "partial-receipt-absence-remains-blocking": True,
            "source-root-links-and-escape-rejected": True,
            "append-only-output": True,
        }
        if self.checks != expected_checks:
            raise ValueError("admission sanitizer checks differ")
        if self.source_inventory_hash != sha256_json(
            [binding.model_dump(mode="json") for binding in self.source_files]
        ) or self.validation_inventory_hash != sha256_json(
            [binding.model_dump(mode="json") for binding in self.validation_files]
        ):
            raise ValueError("admission sanitizer inventory hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("admission sanitizer source qualification hash differs")
        return self


class InventoryAuthority(FrozenModel):
    package_archive_files_read: int = Field(ge=0)
    private_verifier_report_files_read_by_trusted_sanitizer: int = Field(ge=0)
    private_test_identifiers_persisted: Literal[0]
    raw_test_outputs_persisted: Literal[0]
    package_archive_contents_read: Literal[0]
    solution_or_reference_patch_files_read: Literal[0]
    task_packages_materialized: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    provider_calls: Literal[0]
    evaluator_calls: Literal[0]
    agent_runs: Literal[0]
    added_model_cost_usd: Literal[0]
    sanitized_inventory_created: Literal[True]
    raw_admission_replay_complete: bool
    task_admission_authorized: Literal[False]
    task_package_conversion_authorized: Literal[False]
    runtime_source_qualification_authorized: Literal[False]
    candidate_creation_authorized: Literal[False]
    preflight_authorized: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def exact_counts(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in (
            "package_archive_files_read",
            "private_verifier_report_files_read_by_trusted_sanitizer",
        ):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value


class AdmissionEvidenceInventory(FrozenModel):
    schema_version: Literal[INVENTORY_SCHEMA]
    inventory_id: Literal[INVENTORY_ID]
    status: Literal[
        "SANITIZED_RAW_ADMISSION_INVENTORY_INCOMPLETE_ACTIVATION_BLOCKED",
        "SANITIZED_RAW_ADMISSION_INVENTORY_COMPLETE_TASK_CONVERSION_PENDING",
    ]
    predecessor_bindings: tuple[FileBinding, ...]
    source_qualification_binding: FileBinding
    rows: tuple[CandidateEvidenceInventory, ...]
    candidate_count: Literal[12]
    archive_receipts_available: Literal[12]
    base_receipts_available: Literal[12]
    reference_receipts_expected: Literal[36]
    reference_receipts_available: Literal[36]
    partial_receipts_expected: Literal[133]
    partial_rejections_expected: Literal[105]
    partial_receipts_available: int = Field(ge=0, le=133)
    partial_rejections_available: int = Field(ge=0, le=105)
    partial_receipts_missing: int = Field(ge=0, le=133)
    tasks_with_complete_raw_receipt_set: int = Field(ge=0, le=12)
    all_raw_receipts_available: bool
    row_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: InventoryAuthority
    next_gate: str
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("predecessor_bindings", "rows", mode="before")
    @classmethod
    def freeze_sequences(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="before")
    @classmethod
    def exact_counts(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in (
            "partial_receipts_available",
            "partial_rejections_available",
            "partial_receipts_missing",
            "tasks_with_complete_raw_receipt_set",
        ):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_inventory(self) -> Self:
        if tuple(row.task_id for row in self.rows) != CANDIDATE_IDS:
            raise ValueError("admission inventory candidate order differs")
        if len(self.rows) != self.candidate_count:
            raise ValueError("admission inventory candidate count differs")
        available = sum(row.available_partial_receipts for row in self.rows)
        rejected = sum(row.available_rejected_partial_receipts for row in self.rows)
        missing = sum(row.missing_partial_receipts for row in self.rows)
        complete_tasks = sum(row.raw_receipt_set_complete for row in self.rows)
        all_complete = complete_tasks == 12 and missing == 0
        if not (
            self.partial_receipts_available == available
            and self.partial_rejections_available == rejected
            and self.partial_receipts_missing == missing
            and self.partial_receipts_expected == available + missing
            and self.tasks_with_complete_raw_receipt_set == complete_tasks
            and self.all_raw_receipts_available == all_complete
            and self.authority.raw_admission_replay_complete == all_complete
        ):
            raise ValueError("admission inventory aggregate differs")
        expected_status = (
            "SANITIZED_RAW_ADMISSION_INVENTORY_COMPLETE_TASK_CONVERSION_PENDING"
            if all_complete
            else "SANITIZED_RAW_ADMISSION_INVENTORY_INCOMPLETE_ACTIVATION_BLOCKED"
        )
        expected_gate = (
            "source-qualify-public-private-task-package-conversion-before-runtime-qualification"
            if all_complete
            else (
                "produce-and-persist-the-missing-partial-verifier-receipts-under-"
                "a-new-approved-admission-run"
            )
        )
        if self.status != expected_status or self.next_gate != expected_gate:
            raise ValueError("admission inventory status or next gate differs")
        if self.row_inventory_hash != sha256_json(
            [row.model_dump(mode="json") for row in self.rows]
        ):
            raise ValueError("admission row inventory hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("admission evidence inventory hash differs")
        return self


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def artifact_bytes(value: BaseModel) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FreshHarborAdmissionError(f"duplicate JSON key in {label}")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshHarborAdmissionError(f"invalid JSON in {label}") from exc
    if not isinstance(value, dict):
        raise FreshHarborAdmissionError(f"{label} must be a JSON object")
    return value


def _safe_repository_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or "\\" in relative or ".." in candidate.parts:
        raise FreshHarborAdmissionError("repository binding path is not canonical")
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        is_junction = getattr(cursor, "is_junction", lambda: False)
        if cursor.exists() and (cursor.is_symlink() or is_junction()):
            raise FreshHarborAdmissionError("repository binding path contains a link")
    return ensure_within(root, relative)


def _safe_external_file(source_root: Path, candidate: Path) -> Path:
    lexical_root = source_root.absolute()
    lexical = candidate.absolute()
    try:
        relative = lexical.relative_to(lexical_root)
    except ValueError as exc:
        raise FreshHarborAdmissionError("raw admission path escapes source root") from exc
    cursor = lexical_root
    is_junction = getattr(cursor, "is_junction", lambda: False)
    if cursor.is_symlink() or is_junction():
        raise FreshHarborAdmissionError("raw admission source root is a link")
    for part in relative.parts:
        cursor = cursor / part
        is_junction = getattr(cursor, "is_junction", lambda: False)
        if cursor.exists() and (cursor.is_symlink() or is_junction()):
            raise FreshHarborAdmissionError("raw admission path contains a link")
    resolved_root = lexical_root.resolve()
    resolved = lexical.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise FreshHarborAdmissionError("raw admission path resolves outside source root") from exc
    if not resolved.is_file():
        raise FreshHarborAdmissionError("raw admission file is unavailable")
    return resolved


def _binding(
    root: Path,
    path: str,
    *,
    role: str,
    content_hash: str | None = None,
) -> FileBinding:
    selected = _safe_repository_file(root, path)
    raw = selected.read_bytes()
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
        role=role,
    )


def _assert_exact_binding(
    root: Path,
    *,
    path: str,
    file_bytes: int,
    file_sha256: str,
    content_hash: str | None,
    role: str,
) -> FileBinding:
    binding = _binding(root, path, role=role, content_hash=content_hash)
    if binding.file_bytes != file_bytes or binding.file_sha256 != file_sha256:
        raise FreshHarborAdmissionError(f"predecessor bytes differ: {path}")
    return binding


def _predecessor_bindings(root: Path) -> tuple[FileBinding, ...]:
    return (
        _assert_exact_binding(
            root,
            path=PREREG_PATH,
            file_bytes=PREREG_BYTES,
            file_sha256=PREREG_SHA256,
            content_hash=PREREG_CONTENT_HASH,
            role="all-cross-successor-preregistration",
        ),
        _assert_exact_binding(
            root,
            path=REGISTRY_PATH,
            file_bytes=REGISTRY_BYTES,
            file_sha256=REGISTRY_SHA256,
            content_hash=REGISTRY_CONTENT_HASH,
            role="all-cross-public-registry-qualification",
        ),
        _assert_exact_binding(
            root,
            path=SUITE_PATH,
            file_bytes=SUITE_BYTES,
            file_sha256=SUITE_SHA256,
            content_hash=SUITE_CONTENT_HASH,
            role="all-cross-metadata-suite",
        ),
        _assert_exact_binding(
            root,
            path=PLAN_PATH,
            file_bytes=PLAN_BYTES,
            file_sha256=PLAN_SHA256,
            content_hash=PLAN_CONTENT_HASH,
            role="all-cross-activation-plan",
        ),
        _assert_exact_binding(
            root,
            path=OBSERVATION_PATH,
            file_bytes=OBSERVATION_BYTES,
            file_sha256=OBSERVATION_SHA256,
            content_hash=None,
            role="frozen-public-admission-observation",
        ),
    )


def _current_bindings(root: Path, paths: tuple[str, ...], role: str) -> tuple[FileBinding, ...]:
    return tuple(_binding(root, path, role=role) for path in paths)


def build_source_qualification(root: Path) -> AdmissionSanitizerSourceQualification:
    root = root.resolve()
    source_files = _current_bindings(root, SOURCE_PATHS, "admission-sanitizer-source")
    validation_files = _current_bindings(root, VALIDATION_PATHS, "admission-sanitizer-validation")
    body: dict[str, Any] = {
        "schema_version": SOURCE_QUALIFICATION_SCHEMA,
        "qualification_id": SOURCE_QUALIFICATION_ID,
        "status": "ADMISSION_SANITIZER_SOURCE_QUALIFIED_NO_RAW_REPLAY_AUTHORITY",
        "predecessor_bindings": _predecessor_bindings(root),
        "source_files": source_files,
        "validation_files": validation_files,
        "source_inventory_hash": sha256_json(
            [binding.model_dump(mode="json") for binding in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [binding.model_dump(mode="json") for binding in validation_files]
        ),
        "checks": {
            "duplicate-json-keys-rejected": True,
            "raw-report-top-level-schema-closed": True,
            "report-byte-size-and-sha-bound": True,
            "test-identifiers-counted-not-persisted": True,
            "raw-output-text-not-persisted": True,
            "package-archive-bytes-not-extracted": True,
            "selected-archive-hash-bound-to-frozen-observation": True,
            "base-and-reference-semantics-fail-closed": True,
            "partial-receipt-absence-remains-blocking": True,
            "source-root-links-and-escape-rejected": True,
            "append-only-output": True,
        },
        "authority": SourceQualificationAuthority(
            source_files_read=3,
            validation_files_read=1,
            raw_package_archives_read=0,
            private_verifier_reports_read=0,
            private_test_identifiers_persisted=0,
            raw_test_outputs_persisted=0,
            solution_or_reference_patch_files_read=0,
            network_calls=0,
            docker_calls=0,
            provider_calls=0,
            evaluator_calls=0,
            agent_runs=0,
            added_model_cost_usd=0,
            sanitizer_source_qualified=True,
            raw_admission_replay_complete=False,
            task_package_conversion_authorized=False,
            candidate_creation_authorized=False,
            execution_authorized=False,
        ),
        "next_gate": (
            "capture-sanitized-raw-admission-availability-without-docker-or-task-conversion"
        ),
    }
    return AdmissionSanitizerSourceQualification(
        **body,
        content_hash=sha256_json(_jsonable(body)),
    )


def _verify_current_bindings(root: Path, value: AdmissionSanitizerSourceQualification) -> None:
    if value.predecessor_bindings != _predecessor_bindings(root):
        raise FreshHarborAdmissionError("source qualification predecessor binding differs")
    source_files = _current_bindings(root, SOURCE_PATHS, "admission-sanitizer-source")
    validation_files = _current_bindings(root, VALIDATION_PATHS, "admission-sanitizer-validation")
    if value.source_files != source_files or value.validation_files != validation_files:
        raise FreshHarborAdmissionError("admission sanitizer source or validation drifted")


def load_source_qualification(root: Path) -> tuple[AdmissionSanitizerSourceQualification, bytes]:
    root = root.resolve()
    selected = _safe_repository_file(root, SOURCE_QUALIFICATION_PATH)
    try:
        raw = selected.read_bytes()
        value = AdmissionSanitizerSourceQualification.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise FreshHarborAdmissionError("admission sanitizer qualification is unavailable") from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborAdmissionError("admission sanitizer qualification bytes are noncanonical")
    _verify_current_bindings(root, value)
    return value, raw


def _write_once(root: Path, path: str, value: BaseModel) -> FileBinding:
    selected = _safe_repository_file(root, path)
    raw = artifact_bytes(value)
    if selected.exists():
        if selected.read_bytes() != raw:
            raise FreshHarborAdmissionError(f"append-only admission artifact differs: {path}")
    else:
        selected.parent.mkdir(parents=True, exist_ok=True)
        try:
            with selected.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if selected.read_bytes() != raw:
                raise FreshHarborAdmissionError(
                    f"admission artifact appeared with different bytes: {path}"
                ) from None
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=str(value.model_dump(mode="json")["content_hash"]),
        role="admission-sanitizer-source-qualification"
        if path == SOURCE_QUALIFICATION_PATH
        else "sanitized-admission-evidence-inventory",
    )


def materialize_source_qualification(root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(root, SOURCE_QUALIFICATION_PATH, build_source_qualification(root))


def _project_report(
    path: Path, *, source_root: Path, role: str, ordinal: int
) -> SanitizedVerifierReport:
    selected = _safe_external_file(source_root, path)
    raw = selected.read_bytes()
    value = _json_object(raw, label="Harbor verifier report")
    if frozenset(value) != _REPORT_KEYS:
        raise FreshHarborAdmissionError("Harbor verifier report fields differ")
    for name in ("resolved", "pass_to_pass_ok", "fail_to_pass_ok"):
        if type(value[name]) is not bool:
            raise FreshHarborAdmissionError("Harbor verifier verdict has non-boolean type")
    if not isinstance(value["log_parser"], str) or not value["log_parser"]:
        raise FreshHarborAdmissionError("Harbor verifier log parser identity is missing")
    for name in ("pass_to_pass", "fail_to_pass"):
        cases = value[name]
        if not isinstance(cases, dict) or any(
            not isinstance(key, str) or not isinstance(item, str) for key, item in cases.items()
        ):
            raise FreshHarborAdmissionError("Harbor verifier case result mapping differs")
    parsed = value["parsed_counts"]
    if (
        not isinstance(parsed, dict)
        or frozenset(parsed) != _COUNT_KEYS
        or any(type(item) is not int or item < 0 for item in parsed.values())
    ):
        raise FreshHarborAdmissionError("Harbor verifier parsed counts differ")
    body: dict[str, Any] = {
        "role": role,
        "ordinal": ordinal,
        "raw_report": ExternalRawBinding(
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
        ),
        "resolved": value["resolved"],
        "pass_to_pass_ok": value["pass_to_pass_ok"],
        "fail_to_pass_ok": value["fail_to_pass_ok"],
        "pass_to_pass_case_count": len(value["pass_to_pass"]),
        "fail_to_pass_case_count": len(value["fail_to_pass"]),
        "parsed_counts": ParsedCounts(
            passed=parsed["PASSED"],
            failed=parsed["FAILED"],
            skipped=parsed["SKIPPED"],
            error=parsed["ERROR"],
        ),
        "log_parser_present": True,
        "raw_test_identifiers_persisted": 0,
        "raw_test_outputs_persisted": 0,
    }
    return SanitizedVerifierReport(**body, content_hash=sha256_json(_jsonable(body)))


def _candidate_root_by_archive(
    source_root: Path,
    candidates: tuple[CandidateObservation, ...],
) -> dict[str, Path]:
    expected = {candidate.archive.sha256: candidate.instance for candidate in candidates}
    matches: dict[str, list[Path]] = {candidate.instance: [] for candidate in candidates}
    for archive in source_root.glob("fresh-admission-*/dist.tar.gz"):
        selected = _safe_external_file(source_root, archive)
        digest = sha256_bytes(selected.read_bytes())
        task_id = expected.get(digest)
        if task_id is not None:
            matches[task_id].append(selected.parent)
    result: dict[str, Path] = {}
    for candidate in candidates:
        roots = matches[candidate.instance]
        if len(roots) != 1:
            raise FreshHarborAdmissionError(
                f"expected one raw admission root for frozen task {candidate.instance}"
            )
        result[candidate.instance] = roots[0]
    return result


def _capture_candidate(
    source_root: Path,
    candidate_root: Path,
    candidate: CandidateObservation,
) -> tuple[CandidateEvidenceInventory, int]:
    archive_path = _safe_external_file(source_root, candidate_root / "dist.tar.gz")
    archive_raw = archive_path.read_bytes()
    if not (
        len(archive_raw) == candidate.archive.bytes
        and sha256_bytes(archive_raw) == candidate.archive.sha256
    ):
        raise FreshHarborAdmissionError("Harbor package archive binding differs")

    base_reports: list[SanitizedVerifierReport] = []
    report_reads = 0
    for path in sorted(candidate_root.glob("base-nosync-*/logs/verifier/report.json")):
        report_reads += 1
        report = _project_report(
            path,
            source_root=source_root,
            role="base",
            ordinal=1,
        )
        expected_counts = candidate.base_counts
        if (
            report.resolved is False
            and report.pass_to_pass_ok is True
            and report.fail_to_pass_ok is False
            and report.parsed_counts.passed == expected_counts["pass_to_pass_passed"]
            and report.parsed_counts.failed == expected_counts["fail_to_pass_failed"]
            and report.parsed_counts.skipped == expected_counts.get("skipped", 0)
            and report.parsed_counts.error == 0
        ):
            base_reports.append(report)
    if len(base_reports) != 1:
        raise FreshHarborAdmissionError("Harbor base visible/hidden contract receipt differs")

    reference_paths = sorted(candidate_root.glob("reference-nosync-*/logs/verifier/report.json"))
    if len(reference_paths) != 3:
        raise FreshHarborAdmissionError("Harbor reference receipt triplicate is unavailable")
    reference_reports = tuple(
        _project_report(path, source_root=source_root, role="reference", ordinal=index)
        for index, path in enumerate(reference_paths, start=1)
    )
    report_reads += len(reference_reports)
    if any(
        not (
            report.raw_report.file_sha256 == candidate.reference_report_sha256
            and report.resolved is True
            and report.pass_to_pass_ok is True
            and report.fail_to_pass_ok is True
        )
        for report in reference_reports
    ):
        raise FreshHarborAdmissionError("Harbor reference receipt semantics differ")

    partial_paths: list[Path] = []
    for directory in sorted(candidate_root.iterdir(), key=lambda item: item.name):
        if directory.is_dir() and _PARTIAL_DIRECTORY.fullmatch(directory.name):
            report_path = directory / "logs" / "verifier" / "report.json"
            if report_path.is_file():
                partial_paths.append(report_path)
    if len(partial_paths) > candidate.partial_variants.tested:
        raise FreshHarborAdmissionError("available partial receipts exceed frozen tested count")
    partial_reports = tuple(
        _project_report(path, source_root=source_root, role="partial", ordinal=index)
        for index, path in enumerate(partial_paths, start=1)
    )
    report_reads += len(partial_reports)
    rejected = sum(not report.resolved for report in partial_reports)
    if rejected > candidate.partial_variants.rejected:
        raise FreshHarborAdmissionError("available partial rejections exceed frozen count")
    complete = len(partial_reports) == candidate.partial_variants.tested
    if complete and rejected != candidate.partial_variants.rejected:
        raise FreshHarborAdmissionError("complete partial receipt rejection count differs")

    body: dict[str, Any] = {
        "task_id": candidate.instance,
        "repository": candidate.repository,
        "package_archive": ExternalRawBinding(
            file_bytes=len(archive_raw), file_sha256=sha256_bytes(archive_raw)
        ),
        "base_report": base_reports[0],
        "reference_reports": reference_reports,
        "expected_partial_receipts": candidate.partial_variants.tested,
        "expected_rejected_partial_receipts": candidate.partial_variants.rejected,
        "partial_reports": partial_reports,
        "available_partial_receipts": len(partial_reports),
        "available_rejected_partial_receipts": rejected,
        "missing_partial_receipts": candidate.partial_variants.tested - len(partial_reports),
        "base_contract_verified": True,
        "reference_triplicate_verified": True,
        "available_partial_receipts_sanitized": True,
        "raw_receipt_set_complete": complete,
    }
    return (
        CandidateEvidenceInventory(**body, content_hash=sha256_json(_jsonable(body))),
        report_reads,
    )


def _load_observation(root: Path) -> SearchObservation:
    selected = _safe_repository_file(root, OBSERVATION_PATH)
    raw = selected.read_bytes()
    if len(raw) != OBSERVATION_BYTES or sha256_bytes(raw) != OBSERVATION_SHA256:
        raise FreshHarborAdmissionError("frozen public admission observation differs")
    try:
        return SearchObservation.model_validate_json(raw)
    except ValueError as exc:
        raise FreshHarborAdmissionError("frozen public admission observation is invalid") from exc


def build_evidence_inventory(root: Path, source_root: Path) -> AdmissionEvidenceInventory:
    root = root.resolve()
    lexical_source_root = source_root.absolute()
    if not lexical_source_root.is_dir():
        raise FreshHarborAdmissionError("raw admission source root is unavailable")
    qualification, qualification_raw = load_source_qualification(root)
    observation = _load_observation(root)
    candidate_roots = _candidate_root_by_archive(lexical_source_root, observation.candidates)
    rows: list[CandidateEvidenceInventory] = []
    verifier_reads = 0
    for candidate in observation.candidates:
        row, report_reads = _capture_candidate(
            lexical_source_root,
            candidate_roots[candidate.instance],
            candidate,
        )
        rows.append(row)
        verifier_reads += report_reads
    frozen_rows = tuple(rows)
    available = sum(row.available_partial_receipts for row in frozen_rows)
    rejected = sum(row.available_rejected_partial_receipts for row in frozen_rows)
    missing = sum(row.missing_partial_receipts for row in frozen_rows)
    complete_tasks = sum(row.raw_receipt_set_complete for row in frozen_rows)
    all_complete = complete_tasks == 12 and missing == 0
    body: dict[str, Any] = {
        "schema_version": INVENTORY_SCHEMA,
        "inventory_id": INVENTORY_ID,
        "status": (
            "SANITIZED_RAW_ADMISSION_INVENTORY_COMPLETE_TASK_CONVERSION_PENDING"
            if all_complete
            else "SANITIZED_RAW_ADMISSION_INVENTORY_INCOMPLETE_ACTIVATION_BLOCKED"
        ),
        "predecessor_bindings": _predecessor_bindings(root),
        "source_qualification_binding": FileBinding(
            path=SOURCE_QUALIFICATION_PATH,
            file_bytes=len(qualification_raw),
            file_sha256=sha256_bytes(qualification_raw),
            content_hash=qualification.content_hash,
            role="admission-sanitizer-source-qualification",
        ),
        "rows": frozen_rows,
        "candidate_count": 12,
        "archive_receipts_available": 12,
        "base_receipts_available": 12,
        "reference_receipts_expected": 36,
        "reference_receipts_available": 36,
        "partial_receipts_expected": 133,
        "partial_rejections_expected": 105,
        "partial_receipts_available": available,
        "partial_rejections_available": rejected,
        "partial_receipts_missing": missing,
        "tasks_with_complete_raw_receipt_set": complete_tasks,
        "all_raw_receipts_available": all_complete,
        "row_inventory_hash": sha256_json([row.model_dump(mode="json") for row in frozen_rows]),
        "authority": InventoryAuthority(
            package_archive_files_read=12,
            private_verifier_report_files_read_by_trusted_sanitizer=verifier_reads,
            private_test_identifiers_persisted=0,
            raw_test_outputs_persisted=0,
            package_archive_contents_read=0,
            solution_or_reference_patch_files_read=0,
            task_packages_materialized=0,
            network_calls=0,
            docker_calls=0,
            provider_calls=0,
            evaluator_calls=0,
            agent_runs=0,
            added_model_cost_usd=0,
            sanitized_inventory_created=True,
            raw_admission_replay_complete=all_complete,
            task_admission_authorized=False,
            task_package_conversion_authorized=False,
            runtime_source_qualification_authorized=False,
            candidate_creation_authorized=False,
            preflight_authorized=False,
            approval_granted=False,
            execution_authorized=False,
            official_analysis_authorized=False,
            memory_effect_claim_authorized=False,
        ),
        "next_gate": (
            "source-qualify-public-private-task-package-conversion-before-runtime-qualification"
            if all_complete
            else (
                "produce-and-persist-the-missing-partial-verifier-receipts-under-"
                "a-new-approved-admission-run"
            )
        ),
    }
    return AdmissionEvidenceInventory(**body, content_hash=sha256_json(_jsonable(body)))


def materialize_evidence_inventory(root: Path, source_root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(root, INVENTORY_PATH, build_evidence_inventory(root, source_root))


def load_evidence_inventory(root: Path) -> tuple[AdmissionEvidenceInventory, bytes]:
    root = root.resolve()
    qualification, qualification_raw = load_source_qualification(root)
    selected = _safe_repository_file(root, INVENTORY_PATH)
    try:
        raw = selected.read_bytes()
        value = AdmissionEvidenceInventory.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise FreshHarborAdmissionError("admission evidence inventory is unavailable") from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborAdmissionError("admission evidence inventory bytes are noncanonical")
    if value.predecessor_bindings != _predecessor_bindings(root):
        raise FreshHarborAdmissionError("admission evidence predecessor binding differs")
    expected_qualification = FileBinding(
        path=SOURCE_QUALIFICATION_PATH,
        file_bytes=len(qualification_raw),
        file_sha256=sha256_bytes(qualification_raw),
        content_hash=qualification.content_hash,
        role="admission-sanitizer-source-qualification",
    )
    if value.source_qualification_binding != expected_qualification:
        raise FreshHarborAdmissionError("admission sanitizer qualification binding differs")
    return value, raw
