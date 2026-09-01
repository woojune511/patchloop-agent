"""Freeze a new deterministic evaluator-private partial-patch admission panel.

The retained exploratory Harbor observation recorded aggregate partial-patch
counts, but most raw variant identities and receipts no longer exist.  Those
counts therefore cannot identify a replay set.  This module leaves the
retained inventory immutable and defines a new, pre-outcome campaign instead:
for each of the 12 already-frozen tasks, rank eligible single-line ablations of
the evaluator-private reference diff and freeze exactly 12 hash-only variants.

Reference and generated patch bodies stay inside the trusted builder.  The
artifact stores byte identities, structural coordinates, and aggregate design
metadata only.  It authorizes no Docker, evaluator, provider, agent, task
conversion, candidate, approval, analysis, or spend operation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
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
)
from patchloop.evals.fresh_harbor_admission import (
    INVENTORY_PATH,
    _candidate_root_by_archive,
    _load_observation,
    load_evidence_inventory,
)
from patchloop.evals.fresh_harbor_admission import (
    SOURCE_QUALIFICATION_PATH as RETAINED_SOURCE_QUALIFICATION_PATH,
)
from patchloop.util import ensure_within, sha256_bytes, sha256_json

SOURCE_QUALIFICATION_SCHEMA = "lean-fresh-harbor-partial-admission-source-qualification-v1"
SOURCE_QUALIFICATION_ID = "lean-fresh-harbor-partial-admission-generator-20260818-r1"
SOURCE_QUALIFICATION_PATH = (
    "reports/fresh-panel/artifacts/lean-fresh-harbor-partial-admission-source-qualification-r1.json"
)
PREREGISTRATION_SCHEMA = "lean-fresh-harbor-partial-admission-preregistration-v1"
PREREGISTRATION_ID = "lean-harness-fresh-harbor-partial-admission-20260818-v1"
PREREGISTRATION_PATH = "experiments/lean-harness-fresh-harbor-partial-admission-20260818-v1.json"

SELECTION_SEED = "lean-fresh-harbor-partial-admission-20260818-v1"
VARIANTS_PER_TASK = 12
TASK_COUNT = 12
EXPECTED_ROWS = TASK_COUNT * VARIANTS_PER_TASK
MINIMUM_APPLIED_REJECTIONS_PER_TASK = 8

RETAINED_SOURCE_QUALIFICATION_BYTES = 4_797
RETAINED_SOURCE_QUALIFICATION_SHA256 = (
    "sha256:7f930251777d2c512b8769c13fb838dff6d9b30f1db0a2dbe6d750a2c5f2f10d"
)
RETAINED_SOURCE_QUALIFICATION_CONTENT_HASH = (
    "sha256:cbe435ae2f6a203e6c468afb1e5cd9c61d9802d1bad7331de642142daf6c6056"
)
RETAINED_INVENTORY_BYTES = 62_887
RETAINED_INVENTORY_SHA256 = (
    "sha256:53dc7ade442915da780dd1506dccbc6824fcd5292ff3b0f6ea889d10f87cb0a9"
)
RETAINED_INVENTORY_CONTENT_HASH = (
    "sha256:b55d89d45cb2b601994d7bca19aada66be7cfcc32152cbc6e0c592b8b5472917"
)
ALL_CROSS_PREREG_BYTES = 8_815
ALL_CROSS_PREREG_SHA256 = "sha256:a6d2918b486e36dc2ba6e4d8f586ee4b46a8c2b60a4abb3854b98c4715c99748"
ALL_CROSS_PREREG_CONTENT_HASH = (
    "sha256:12bb5ca18034f7592c4d630ff91c9789a81ff7af22803da3269e68343f234955"
)
REGISTRY_BYTES = 19_240
REGISTRY_SHA256 = "sha256:2e5565faa2bb2c2b63cb52a4fcde8b920488be1c59acc5538f567a99c26917a6"
REGISTRY_CONTENT_HASH = "sha256:bf4e3711c4b116bd3027781a9f39b3ae0fcf94b38563c83a408061c15e34f135"
SUITE_BYTES = 22_629
SUITE_SHA256 = "sha256:3d81476977071be5e578697e0e4da53e9bdbbdf9e84504af465f8159e40c3a19"
SUITE_CONTENT_HASH = "sha256:f57eded985460f982e908b768d1b512cc6bf6daeaf26e59f86a688343d9f951f"
PLAN_BYTES = 3_726
PLAN_SHA256 = "sha256:d7408a99fc498032f736b8741edb28848e6eb0a963eabfc18546a5a572036939"
PLAN_CONTENT_HASH = "sha256:1f13d5a84fb41ecb83ccc45c16f8fff8551114475cc55041be9ebbe49e75c755"

SOURCE_PATHS = (
    "patchloop/evals/fresh_harbor_partial_admission.py",
    "scripts/build_lean_fresh_harbor_partial_admission_source_qualification.py",
    "scripts/build_lean_fresh_harbor_partial_admission_preregistration.py",
)
VALIDATION_PATHS = ("tests/test_fresh_harbor_partial_admission.py",)

_HUNK_HEADER = re.compile(rb"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


class FreshHarborPartialAdmissionError(ContractError):
    """A deterministic partial-admission source or design binding differs."""


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
    def exact_bytes(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("file_bytes must be a JSON integer")
        return value


class RawBinding(FrozenModel):
    file_bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("file_bytes", mode="before")
    @classmethod
    def exact_bytes(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("raw file_bytes must be a JSON integer")
        return value


class VariantDescriptor(FrozenModel):
    ordinal: int = Field(ge=1, le=VARIANTS_PER_TASK)
    rank_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    operation: Literal["remove-added-line", "retain-deleted-line"]
    file_ordinal: int = Field(ge=1)
    hunk_ordinal: int = Field(ge=1)
    hunk_body_ordinal: int = Field(ge=1)
    target_path_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    atomic_unit_fingerprint_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    generated_patch: RawBinding
    patch_body_persisted: Literal[0]
    reference_line_content_persisted: Literal[0]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="before")
    @classmethod
    def exact_integers(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        for name in (
            "ordinal",
            "file_ordinal",
            "hunk_ordinal",
            "hunk_body_ordinal",
        ):
            if name in value and type(value[name]) is not int:
                raise ValueError(f"{name} must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("partial variant descriptor content hash differs")
        return self


class TaskVariantPlan(FrozenModel):
    task_id: str
    repository: str
    reference_patch: RawBinding
    eligible_atomic_unit_count: int = Field(ge=VARIANTS_PER_TASK)
    unique_generated_variant_count: int = Field(ge=VARIANTS_PER_TASK)
    variants: tuple[VariantDescriptor, ...]
    variant_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reference_patch_body_persisted: Literal[0]
    generated_patch_bodies_persisted: Literal[0]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("variants", mode="before")
    @classmethod
    def freeze_variants(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("eligible_atomic_unit_count", "unique_generated_variant_count", mode="before")
    @classmethod
    def exact_count(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("partial variant capacity must be a JSON integer")
        return value

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if len(self.variants) != VARIANTS_PER_TASK:
            raise ValueError("partial variant count differs")
        if tuple(item.ordinal for item in self.variants) != tuple(range(1, VARIANTS_PER_TASK + 1)):
            raise ValueError("partial variant ordinals differ")
        ranks = tuple(item.rank_sha256 for item in self.variants)
        if ranks != tuple(sorted(ranks)) or len(set(ranks)) != VARIANTS_PER_TASK:
            raise ValueError("partial variant ranking differs")
        patch_hashes = tuple(item.generated_patch.file_sha256 for item in self.variants)
        if len(set(patch_hashes)) != VARIANTS_PER_TASK:
            raise ValueError("partial variant patch identities are not unique")
        if self.variant_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.variants]
        ):
            raise ValueError("partial variant inventory hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("partial task plan content hash differs")
        return self


class SourceAuthority(FrozenModel):
    source_files_read: Literal[3]
    validation_files_read: Literal[1]
    public_package_archives_read: Literal[0]
    evaluator_private_reference_patches_read: Literal[0]
    private_patch_bodies_persisted: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    provider_calls: Literal[0]
    agent_runs: Literal[0]
    added_cost_usd: Literal[0]
    source_qualified: Literal[True]
    partial_campaign_authorized: Literal[False]
    task_conversion_authorized: Literal[False]
    candidate_creation_authorized: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]


class PreregistrationAuthority(FrozenModel):
    public_package_archives_read: Literal[12]
    evaluator_private_reference_patches_read_by_trusted_builder: Literal[12]
    solution_files_read: Literal[0]
    private_patch_bodies_persisted: Literal[0]
    private_test_identifiers_read: Literal[0]
    private_test_identifiers_persisted: Literal[0]
    network_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    provider_calls: Literal[0]
    agent_runs: Literal[0]
    added_cost_usd: Literal[0]
    deterministic_variant_plan_frozen: Literal[True]
    retained_missing_receipts_replayed: Literal[False]
    task_admission_authorized: Literal[False]
    task_conversion_authorized: Literal[False]
    runtime_qualification_authorized: Literal[False]
    candidate_creation_authorized: Literal[False]
    preflight_authorized: Literal[False]
    approval_granted: Literal[False]
    execution_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    memory_effect_claim_authorized: Literal[False]


class PartialAdmissionSourceQualification(FrozenModel):
    schema_version: Literal[SOURCE_QUALIFICATION_SCHEMA]
    qualification_id: Literal[SOURCE_QUALIFICATION_ID]
    status: Literal["DETERMINISTIC_PARTIAL_GENERATOR_SOURCE_QUALIFIED_EXECUTION_CLOSED"]
    predecessor_bindings: tuple[FileBinding, ...]
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checks: dict[str, bool]
    authority: SourceAuthority
    next_gate: Literal["materialize-hash-only-deterministic-partial-admission-preregistration"]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("predecessor_bindings", "source_files", "validation_files", mode="before")
    @classmethod
    def freeze_bindings(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.checks != _source_checks():
            raise ValueError("partial generator source checks differ")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("partial generator source inventory hash differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("partial generator validation inventory hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("partial generator source content hash differs")
        return self


class PartialAdmissionPreregistration(FrozenModel):
    schema_version: Literal[PREREGISTRATION_SCHEMA]
    preregistration_id: Literal[PREREGISTRATION_ID]
    status: Literal["DETERMINISTIC_PRIVATE_PARTIAL_ADMISSION_PREREGISTERED_EXECUTION_CLOSED"]
    predecessor_bindings: tuple[FileBinding, ...]
    source_qualification_binding: FileBinding
    retained_evidence_disposition: dict[str, Any]
    design: dict[str, Any]
    task_plans: tuple[TaskVariantPlan, ...]
    task_plan_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_count: Literal[TASK_COUNT]
    variants_per_task: Literal[VARIANTS_PER_TASK]
    expected_rows: Literal[EXPECTED_ROWS]
    authority: PreregistrationAuthority
    next_gate: Literal[
        "source-qualify-a-no-call-docker-evaluator-runner-for-the-exact-144-row-admission-plan"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("predecessor_bindings", "task_plans", mode="before")
    @classmethod
    def freeze_tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_preregistration(self) -> Self:
        if self.retained_evidence_disposition != _retained_evidence_disposition():
            raise ValueError("retained partial evidence disposition differs")
        if self.design != _design_contract():
            raise ValueError("partial admission design differs")
        if tuple(item.task_id for item in self.task_plans) != CANDIDATE_IDS:
            raise ValueError("partial admission task order differs")
        if self.task_plan_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.task_plans]
        ):
            raise ValueError("partial task-plan inventory hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("partial admission preregistration content hash differs")
        return self


@dataclass(frozen=True)
class _Hunk:
    file_ordinal: int
    hunk_ordinal: int
    header_index: int
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    suffix: bytes
    eol: bytes
    body_start: int
    body_end: int
    target_path_sha256: str


@dataclass(frozen=True)
class _AtomicUnit:
    file_ordinal: int
    hunk_ordinal: int
    hunk_body_ordinal: int
    absolute_line_index: int
    operation: Literal["remove-added-line", "retain-deleted-line"]
    target_path_sha256: str
    fingerprint_sha256: str
    rank_sha256: str


def _strip_eol(line: bytes) -> tuple[bytes, bytes]:
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith(b"\n"):
        return line[:-1], b"\n"
    return line, b""


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


def _safe_repository_file(root: Path, path: str) -> Path:
    selected = ensure_within(root, path)
    lexical = root / Path(path)
    if lexical.is_symlink() or selected.is_symlink():
        raise FreshHarborPartialAdmissionError(f"repository binding is a link: {path}")
    return selected


def _safe_external_file(source_root: Path, path: Path) -> Path:
    lexical_root = source_root.absolute()
    lexical = path.absolute()
    try:
        lexical.relative_to(lexical_root)
    except ValueError as exc:
        raise FreshHarborPartialAdmissionError("private source path escapes its root") from exc
    cursor = lexical
    while True:
        if cursor.is_symlink():
            raise FreshHarborPartialAdmissionError("private source path contains a link")
        if cursor == lexical_root:
            break
        if cursor.parent == cursor:
            raise FreshHarborPartialAdmissionError("private source root is not an ancestor")
        cursor = cursor.parent
    if not lexical.is_file():
        raise FreshHarborPartialAdmissionError("required private source file is unavailable")
    resolved_root = lexical_root.resolve()
    resolved = lexical.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise FreshHarborPartialAdmissionError("private source file resolves outside root") from exc
    return resolved


def _binding(root: Path, path: str, role: str) -> FileBinding:
    selected = _safe_repository_file(root, path)
    raw = selected.read_bytes()
    content_hash: str | None = None
    if path.endswith(".json"):
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict) and isinstance(parsed.get("content_hash"), str):
            content_hash = parsed["content_hash"]
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
        role=role,
    )


def _exact_binding(
    root: Path,
    *,
    path: str,
    file_bytes: int,
    file_sha256: str,
    content_hash: str,
    role: str,
) -> FileBinding:
    value = _binding(root, path, role)
    expected = FileBinding(
        path=path,
        file_bytes=file_bytes,
        file_sha256=file_sha256,
        content_hash=content_hash,
        role=role,
    )
    if value != expected:
        raise FreshHarborPartialAdmissionError(f"partial admission predecessor differs: {path}")
    return value


def _predecessor_bindings(root: Path) -> tuple[FileBinding, ...]:
    return (
        _exact_binding(
            root,
            path=RETAINED_SOURCE_QUALIFICATION_PATH,
            file_bytes=RETAINED_SOURCE_QUALIFICATION_BYTES,
            file_sha256=RETAINED_SOURCE_QUALIFICATION_SHA256,
            content_hash=RETAINED_SOURCE_QUALIFICATION_CONTENT_HASH,
            role="retained-admission-sanitizer-source-qualification",
        ),
        _exact_binding(
            root,
            path=INVENTORY_PATH,
            file_bytes=RETAINED_INVENTORY_BYTES,
            file_sha256=RETAINED_INVENTORY_SHA256,
            content_hash=RETAINED_INVENTORY_CONTENT_HASH,
            role="retained-incomplete-admission-evidence-inventory",
        ),
        _exact_binding(
            root,
            path=PREREG_PATH,
            file_bytes=ALL_CROSS_PREREG_BYTES,
            file_sha256=ALL_CROSS_PREREG_SHA256,
            content_hash=ALL_CROSS_PREREG_CONTENT_HASH,
            role="all-cross-panel-preregistration",
        ),
        _exact_binding(
            root,
            path=REGISTRY_PATH,
            file_bytes=REGISTRY_BYTES,
            file_sha256=REGISTRY_SHA256,
            content_hash=REGISTRY_CONTENT_HASH,
            role="all-cross-public-registry",
        ),
        _exact_binding(
            root,
            path=SUITE_PATH,
            file_bytes=SUITE_BYTES,
            file_sha256=SUITE_SHA256,
            content_hash=SUITE_CONTENT_HASH,
            role="all-cross-metadata-suite",
        ),
        _exact_binding(
            root,
            path=PLAN_PATH,
            file_bytes=PLAN_BYTES,
            file_sha256=PLAN_SHA256,
            content_hash=PLAN_CONTENT_HASH,
            role="all-cross-activation-plan",
        ),
    )


def _source_checks() -> dict[str, bool]:
    return {
        "retained-counts-not-treated-as-replay-identities": True,
        "reference-diff-parser-has-closed-hunk-grammar": True,
        "eligible-unit-requires-another-change-in-the-same-hunk": True,
        "no-newline-marker-adjacent-units-excluded": True,
        "single-line-ablation-rewrites-hunk-counts": True,
        "later-new-side-hunk-starts-shifted": True,
        "generated-diffs-structurally-reparsed": True,
        "selection-ranked-before-evaluator-outcomes": True,
        "reference-and-generated-patch-bodies-not-persisted": True,
        "append-only-output": True,
        "docker-provider-agent-and-evaluator-authority-zero": True,
    }


def _source_authority() -> SourceAuthority:
    return SourceAuthority(
        source_files_read=3,
        validation_files_read=1,
        public_package_archives_read=0,
        evaluator_private_reference_patches_read=0,
        private_patch_bodies_persisted=0,
        network_calls=0,
        docker_calls=0,
        evaluator_calls=0,
        provider_calls=0,
        agent_runs=0,
        added_cost_usd=0,
        source_qualified=True,
        partial_campaign_authorized=False,
        task_conversion_authorized=False,
        candidate_creation_authorized=False,
        approval_granted=False,
        execution_authorized=False,
    )


def _preregistration_authority() -> PreregistrationAuthority:
    return PreregistrationAuthority(
        public_package_archives_read=12,
        evaluator_private_reference_patches_read_by_trusted_builder=12,
        solution_files_read=0,
        private_patch_bodies_persisted=0,
        private_test_identifiers_read=0,
        private_test_identifiers_persisted=0,
        network_calls=0,
        docker_calls=0,
        evaluator_calls=0,
        provider_calls=0,
        agent_runs=0,
        added_cost_usd=0,
        deterministic_variant_plan_frozen=True,
        retained_missing_receipts_replayed=False,
        task_admission_authorized=False,
        task_conversion_authorized=False,
        runtime_qualification_authorized=False,
        candidate_creation_authorized=False,
        preflight_authorized=False,
        approval_granted=False,
        execution_authorized=False,
        official_analysis_authorized=False,
        memory_effect_claim_authorized=False,
    )


def _retained_evidence_disposition() -> dict[str, Any]:
    return {
        "retained_inventory_status": (
            "SANITIZED_RAW_ADMISSION_INVENTORY_INCOMPLETE_ACTIVATION_BLOCKED"
        ),
        "retained_partial_receipts_expected": 133,
        "retained_partial_receipts_available": 14,
        "retained_partial_receipts_missing": 119,
        "missing_variant_identities_reconstructible_from_counts": False,
        "missing_receipts_replayed_or_backfilled_by_this_design": False,
        "retained_artifacts_modified": False,
        "successor_campaign_relation": (
            "new-deterministic-private-admission-campaign-not-a-replay-or-repair"
        ),
    }


def _design_contract() -> dict[str, Any]:
    return {
        "task_count": TASK_COUNT,
        "variants_per_task": VARIANTS_PER_TASK,
        "expected_rows": EXPECTED_ROWS,
        "variant_family": "single-atomic-reference-diff-line-ablation-v1",
        "selection_seed": SELECTION_SEED,
        "selection_timing": "after-task-freeze-before-new-partial-evaluator-outcomes",
        "atomic_unit": {
            "eligible_prefixes": ["+", "-"],
            "file-header-lines-excluded": True,
            "adjacent-no-newline-marker-excluded": True,
            "target-hunk-must-retain-at-least-one-other-change": True,
            "added_line_operation": "remove-the-added-line",
            "deleted_line_operation": "convert-the-deleted-line-to-context",
            "target_hunk_new_count_adjustment": "minus-one-for-added-plus-one-for-deleted",
            "later_same-file_new-start_adjustment": "same-signed-unit-delta",
            "canonical_hunk_header_counts_always_explicit": True,
        },
        "ranking": {
            "algorithm": "ascending-sha256-utf8",
            "preimage": (
                "lean-fresh-harbor-partial-admission-20260818-v1|task={task_id}|"
                "reference={reference_patch_sha256}|file={file_ordinal}|"
                "hunk={hunk_ordinal}|body={hunk_body_ordinal}|operation={operation}|"
                "unit={atomic_unit_fingerprint_sha256}"
            ),
            "generated_patch_deduplication": (
                "keep-lowest-ranked-unit-per-generated-patch-sha256-before-prefix-selection"
            ),
            "selected_prefix_length": VARIANTS_PER_TASK,
            "runtime_rng_used": False,
        },
        "evaluator_campaign": {
            "exact_rows": EXPECTED_ROWS,
            "one_fresh_workspace_per_variant": True,
            "reference_patch_or_generated_patch_agent_visible": False,
            "all_rows_require-terminal-durable-evidence": True,
            "patch-application-failure_counts_as_rejection": False,
            "resolved-false-after-successful-application_counts_as_rejection": True,
            "minimum_applied_rejections_per_task": MINIMUM_APPLIED_REJECTIONS_PER_TASK,
            "all-12-task-decisions-required": True,
            "infrastructure-or-contract-confound_stops_campaign": True,
            "partial-results-are-diagnostic-only": True,
        },
        "adaptation": {
            "outcome-based-variant-selection": False,
            "replacement-after-application-failure": False,
            "automatic-retry": False,
            "resume": False,
            "threshold-relaxation": False,
            "reuse-of-retained-unidentified-variants": False,
        },
        "claim_boundary": {
            "task-admission-result-exists": False,
            "task-package-conversion-authorized": False,
            "fresh-ac-provider-comparison-authorized": False,
            "memory-benefit-claim-authorized": False,
        },
    }


def _parse_patch(
    raw: bytes, *, task_id: str, reference_sha256: str
) -> tuple[tuple[bytes, ...], tuple[_Hunk, ...], tuple[_AtomicUnit, ...]]:
    if not raw or b"\x00" in raw:
        raise FreshHarborPartialAdmissionError("reference patch is empty or binary")
    lines = tuple(raw.splitlines(keepends=True))
    if b"".join(lines) != raw:
        raise FreshHarborPartialAdmissionError("reference patch line framing differs")

    file_ordinal = 0
    hunk_ordinal = 0
    target_path_sha256: str | None = None
    hunks: list[_Hunk] = []
    units: list[_AtomicUnit] = []
    index = 0
    while index < len(lines):
        line_no_eol, _eol = _strip_eol(lines[index])
        if line_no_eol.startswith(b"diff --git "):
            file_ordinal += 1
            hunk_ordinal = 0
            target_path_sha256 = None
            index += 1
            continue
        if line_no_eol.startswith(b"+++ "):
            if file_ordinal == 0:
                raise FreshHarborPartialAdmissionError("target path appears before diff header")
            target_path_sha256 = sha256_bytes(line_no_eol)
            index += 1
            continue
        if not line_no_eol.startswith(b"@@ "):
            index += 1
            continue
        if file_ordinal == 0 or target_path_sha256 is None:
            raise FreshHarborPartialAdmissionError("hunk lacks a bound target path")
        match = _HUNK_HEADER.fullmatch(line_no_eol)
        if match is None:
            raise FreshHarborPartialAdmissionError("reference patch hunk header differs")
        old_start = int(match.group(1))
        old_count = int(match.group(2) or b"1")
        new_start = int(match.group(3))
        new_count = int(match.group(4) or b"1")
        hunk_ordinal += 1
        body_start = index + 1
        cursor = body_start
        old_consumed = 0
        new_consumed = 0
        while cursor < len(lines):
            prefix = lines[cursor][:1]
            if prefix == b" ":
                old_consumed += 1
                new_consumed += 1
            elif prefix == b"-":
                old_consumed += 1
            elif prefix == b"+":
                new_consumed += 1
            elif prefix == b"\\":
                cursor += 1
                continue
            else:
                break
            if old_consumed > old_count or new_consumed > new_count:
                raise FreshHarborPartialAdmissionError("reference hunk body exceeds header counts")
            cursor += 1
            if old_consumed == old_count and new_consumed == new_count:
                while cursor < len(lines) and lines[cursor].startswith(b"\\"):
                    cursor += 1
                break
        if old_consumed != old_count or new_consumed != new_count:
            raise FreshHarborPartialAdmissionError("reference hunk body count differs")
        body_end = cursor
        hunk = _Hunk(
            file_ordinal=file_ordinal,
            hunk_ordinal=hunk_ordinal,
            header_index=index,
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
            suffix=match.group(5),
            eol=_eol,
            body_start=body_start,
            body_end=body_end,
            target_path_sha256=target_path_sha256,
        )
        hunks.append(hunk)
        change_indexes = [
            body_index
            for body_index in range(body_start, body_end)
            if lines[body_index][:1] in (b"+", b"-")
        ]
        for body_index in change_indexes:
            if len(change_indexes) <= 1:
                continue
            if body_index + 1 < body_end and lines[body_index + 1].startswith(b"\\"):
                continue
            prefix = lines[body_index][:1]
            operation: Literal["remove-added-line", "retain-deleted-line"] = (
                "remove-added-line" if prefix == b"+" else "retain-deleted-line"
            )
            body_ordinal = body_index - body_start + 1
            fingerprint = sha256_bytes(
                b"|".join(
                    (
                        SELECTION_SEED.encode("ascii"),
                        task_id.encode("utf-8"),
                        reference_sha256.encode("ascii"),
                        str(file_ordinal).encode("ascii"),
                        str(hunk_ordinal).encode("ascii"),
                        str(body_ordinal).encode("ascii"),
                        operation.encode("ascii"),
                        lines[body_index],
                    )
                )
            )
            rank_preimage = (
                f"{SELECTION_SEED}|task={task_id}|reference={reference_sha256}|"
                f"file={file_ordinal}|hunk={hunk_ordinal}|body={body_ordinal}|"
                f"operation={operation}|unit={fingerprint}"
            ).encode()
            units.append(
                _AtomicUnit(
                    file_ordinal=file_ordinal,
                    hunk_ordinal=hunk_ordinal,
                    hunk_body_ordinal=body_ordinal,
                    absolute_line_index=body_index,
                    operation=operation,
                    target_path_sha256=target_path_sha256,
                    fingerprint_sha256=fingerprint,
                    rank_sha256=sha256_bytes(rank_preimage),
                )
            )
        index = body_end
    if not hunks or not units:
        raise FreshHarborPartialAdmissionError("reference patch has no eligible textual changes")
    ranks = [unit.rank_sha256 for unit in units]
    if len(ranks) != len(set(ranks)):
        raise FreshHarborPartialAdmissionError("partial unit rank collision")
    return lines, tuple(hunks), tuple(units)


def _render_variant(lines: tuple[bytes, ...], hunks: tuple[_Hunk, ...], unit: _AtomicUnit) -> bytes:
    rendered = list(lines)
    target_hunk = next(
        (
            hunk
            for hunk in hunks
            if hunk.file_ordinal == unit.file_ordinal and hunk.hunk_ordinal == unit.hunk_ordinal
        ),
        None,
    )
    if target_hunk is None:
        raise FreshHarborPartialAdmissionError("selected partial unit hunk is unavailable")
    delta = -1 if unit.operation == "remove-added-line" else 1
    for hunk in hunks:
        if hunk.file_ordinal != unit.file_ordinal:
            continue
        adjusted_start = hunk.new_start
        adjusted_count = hunk.new_count
        if hunk.hunk_ordinal == unit.hunk_ordinal:
            adjusted_count += delta
        elif hunk.hunk_ordinal > unit.hunk_ordinal:
            adjusted_start += delta
        if adjusted_start < 0 or adjusted_count < 0:
            raise FreshHarborPartialAdmissionError("generated partial hunk count is invalid")
        header = (
            f"@@ -{hunk.old_start},{hunk.old_count} +{adjusted_start},{adjusted_count} @@"
        ).encode("ascii")
        rendered[hunk.header_index] = header + hunk.suffix + hunk.eol
    if unit.operation == "remove-added-line":
        rendered[unit.absolute_line_index] = b""
    else:
        selected = rendered[unit.absolute_line_index]
        if not selected.startswith(b"-"):
            raise FreshHarborPartialAdmissionError("selected deletion line differs")
        rendered[unit.absolute_line_index] = b" " + selected[1:]
    return b"".join(rendered)


def _task_plan(task_id: str, repository: str, reference_raw: bytes) -> TaskVariantPlan:
    reference_sha256 = sha256_bytes(reference_raw)
    lines, hunks, units = _parse_patch(
        reference_raw,
        task_id=task_id,
        reference_sha256=reference_sha256,
    )
    ranked = tuple(sorted(units, key=lambda item: item.rank_sha256))
    if len(ranked) < VARIANTS_PER_TASK:
        raise FreshHarborPartialAdmissionError(
            f"task has fewer than {VARIANTS_PER_TASK} eligible partial units"
        )
    candidates: list[tuple[_AtomicUnit, bytes, str]] = []
    seen_patch_hashes: set[str] = set()
    for unit in ranked:
        variant_raw = _render_variant(lines, hunks, unit)
        if variant_raw == reference_raw:
            raise FreshHarborPartialAdmissionError("generated partial patch equals reference patch")
        parsed_lines, parsed_hunks, _parsed_units = _parse_patch(
            variant_raw,
            task_id=task_id,
            reference_sha256=reference_sha256,
        )
        if b"".join(parsed_lines) != variant_raw or len(parsed_hunks) != len(hunks):
            raise FreshHarborPartialAdmissionError("generated partial patch structure differs")
        patch_hash = sha256_bytes(variant_raw)
        if patch_hash in seen_patch_hashes:
            continue
        seen_patch_hashes.add(patch_hash)
        candidates.append((unit, variant_raw, patch_hash))
    if len(candidates) < VARIANTS_PER_TASK:
        raise FreshHarborPartialAdmissionError(
            f"task has fewer than {VARIANTS_PER_TASK} unique generated partial patches"
        )
    descriptors: list[VariantDescriptor] = []
    for ordinal, (unit, variant_raw, patch_hash) in enumerate(
        candidates[:VARIANTS_PER_TASK], start=1
    ):
        body: dict[str, Any] = {
            "ordinal": ordinal,
            "rank_sha256": unit.rank_sha256,
            "operation": unit.operation,
            "file_ordinal": unit.file_ordinal,
            "hunk_ordinal": unit.hunk_ordinal,
            "hunk_body_ordinal": unit.hunk_body_ordinal,
            "target_path_sha256": unit.target_path_sha256,
            "atomic_unit_fingerprint_sha256": unit.fingerprint_sha256,
            "generated_patch": RawBinding(
                file_bytes=len(variant_raw),
                file_sha256=patch_hash,
            ),
            "patch_body_persisted": 0,
            "reference_line_content_persisted": 0,
        }
        descriptors.append(VariantDescriptor(**body, content_hash=sha256_json(_jsonable(body))))
    variants = tuple(descriptors)
    body = {
        "task_id": task_id,
        "repository": repository,
        "reference_patch": RawBinding(
            file_bytes=len(reference_raw),
            file_sha256=reference_sha256,
        ),
        "eligible_atomic_unit_count": len(units),
        "unique_generated_variant_count": len(candidates),
        "variants": variants,
        "variant_inventory_hash": sha256_json([item.model_dump(mode="json") for item in variants]),
        "reference_patch_body_persisted": 0,
        "generated_patch_bodies_persisted": 0,
    }
    return TaskVariantPlan(**body, content_hash=sha256_json(_jsonable(body)))


def build_source_qualification(root: Path) -> PartialAdmissionSourceQualification:
    root = root.resolve()
    predecessors = _predecessor_bindings(root)
    source_files = tuple(_binding(root, path, "partial-generator-source") for path in SOURCE_PATHS)
    validation_files = tuple(
        _binding(root, path, "partial-generator-validation") for path in VALIDATION_PATHS
    )
    body: dict[str, Any] = {
        "schema_version": SOURCE_QUALIFICATION_SCHEMA,
        "qualification_id": SOURCE_QUALIFICATION_ID,
        "status": "DETERMINISTIC_PARTIAL_GENERATOR_SOURCE_QUALIFIED_EXECUTION_CLOSED",
        "predecessor_bindings": predecessors,
        "source_files": source_files,
        "validation_files": validation_files,
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "checks": _source_checks(),
        "authority": _source_authority(),
        "next_gate": "materialize-hash-only-deterministic-partial-admission-preregistration",
    }
    return PartialAdmissionSourceQualification(
        **body,
        content_hash=sha256_json(_jsonable(body)),
    )


def _source_qualification_binding(
    root: Path,
) -> tuple[FileBinding, PartialAdmissionSourceQualification, bytes]:
    selected = _safe_repository_file(root, SOURCE_QUALIFICATION_PATH)
    try:
        raw = selected.read_bytes()
        value = PartialAdmissionSourceQualification.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise FreshHarborPartialAdmissionError(
            "partial generator source qualification is unavailable"
        ) from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborPartialAdmissionError(
            "partial generator source qualification bytes are noncanonical"
        )
    expected = build_source_qualification(root)
    if value != expected:
        raise FreshHarborPartialAdmissionError("partial generator source qualification drifted")
    return (
        FileBinding(
            path=SOURCE_QUALIFICATION_PATH,
            file_bytes=len(raw),
            file_sha256=sha256_bytes(raw),
            content_hash=value.content_hash,
            role="partial-generator-source-qualification",
        ),
        value,
        raw,
    )


def load_source_qualification(
    root: Path,
) -> tuple[PartialAdmissionSourceQualification, bytes]:
    _binding_value, value, raw = _source_qualification_binding(root.resolve())
    return value, raw


def build_preregistration(root: Path, source_root: Path) -> PartialAdmissionPreregistration:
    root = root.resolve()
    lexical_source_root = source_root.absolute()
    if not lexical_source_root.is_dir():
        raise FreshHarborPartialAdmissionError("private admission source root is unavailable")
    source_binding, _qualification, _qualification_raw = _source_qualification_binding(root)
    inventory, inventory_raw = load_evidence_inventory(root)
    if not (
        len(inventory_raw) == RETAINED_INVENTORY_BYTES
        and sha256_bytes(inventory_raw) == RETAINED_INVENTORY_SHA256
        and inventory.content_hash == RETAINED_INVENTORY_CONTENT_HASH
        and inventory.partial_receipts_missing == 119
        and inventory.all_raw_receipts_available is False
    ):
        raise FreshHarborPartialAdmissionError("retained admission inventory boundary differs")
    observation = _load_observation(root)
    candidate_roots = _candidate_root_by_archive(lexical_source_root, observation.candidates)
    plans: list[TaskVariantPlan] = []
    for candidate in observation.candidates:
        reference_path = _safe_external_file(
            lexical_source_root,
            candidate_roots[candidate.instance] / "reference-patch" / "reference.patch",
        )
        plans.append(
            _task_plan(
                candidate.instance,
                candidate.repository,
                reference_path.read_bytes(),
            )
        )
    task_plans = tuple(plans)
    body: dict[str, Any] = {
        "schema_version": PREREGISTRATION_SCHEMA,
        "preregistration_id": PREREGISTRATION_ID,
        "status": "DETERMINISTIC_PRIVATE_PARTIAL_ADMISSION_PREREGISTERED_EXECUTION_CLOSED",
        "predecessor_bindings": _predecessor_bindings(root),
        "source_qualification_binding": source_binding,
        "retained_evidence_disposition": _retained_evidence_disposition(),
        "design": _design_contract(),
        "task_plans": task_plans,
        "task_plan_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in task_plans]
        ),
        "task_count": TASK_COUNT,
        "variants_per_task": VARIANTS_PER_TASK,
        "expected_rows": EXPECTED_ROWS,
        "authority": _preregistration_authority(),
        "next_gate": (
            "source-qualify-a-no-call-docker-evaluator-runner-for-the-exact-144-row-admission-plan"
        ),
    }
    return PartialAdmissionPreregistration(
        **body,
        content_hash=sha256_json(_jsonable(body)),
    )


def _write_once(root: Path, path: str, value: BaseModel, role: str) -> FileBinding:
    selected = _safe_repository_file(root, path)
    raw = artifact_bytes(value)
    if selected.exists():
        if selected.read_bytes() != raw:
            raise FreshHarborPartialAdmissionError(f"append-only artifact differs: {path}")
    else:
        selected.parent.mkdir(parents=True, exist_ok=True)
        try:
            with selected.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if selected.read_bytes() != raw:
                raise FreshHarborPartialAdmissionError(
                    f"artifact appeared with different bytes: {path}"
                ) from None
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=str(value.model_dump(mode="json")["content_hash"]),
        role=role,
    )


def materialize_source_qualification(root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(
        root,
        SOURCE_QUALIFICATION_PATH,
        build_source_qualification(root),
        "partial-generator-source-qualification",
    )


def materialize_preregistration(root: Path, source_root: Path) -> FileBinding:
    root = root.resolve()
    return _write_once(
        root,
        PREREGISTRATION_PATH,
        build_preregistration(root, source_root),
        "deterministic-private-partial-admission-preregistration",
    )


def load_preregistration(root: Path) -> tuple[PartialAdmissionPreregistration, bytes]:
    root = root.resolve()
    source_binding, _qualification, _qualification_raw = _source_qualification_binding(root)
    selected = _safe_repository_file(root, PREREGISTRATION_PATH)
    try:
        raw = selected.read_bytes()
        value = PartialAdmissionPreregistration.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise FreshHarborPartialAdmissionError(
            "partial admission preregistration is unavailable"
        ) from exc
    if artifact_bytes(value) != raw:
        raise FreshHarborPartialAdmissionError(
            "partial admission preregistration bytes are noncanonical"
        )
    if value.predecessor_bindings != _predecessor_bindings(root):
        raise FreshHarborPartialAdmissionError(
            "partial admission preregistration predecessor drifted"
        )
    if value.source_qualification_binding != source_binding:
        raise FreshHarborPartialAdmissionError(
            "partial admission preregistration source qualification drifted"
        )
    return value, raw


def sha256_standard_library(raw: bytes) -> str:
    """Expose an independent hash oracle for focused source tests."""

    return "sha256:" + hashlib.sha256(raw).hexdigest()
