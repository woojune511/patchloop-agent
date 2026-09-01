"""Outcome-blind preregistration for the first versioned Lean Harness runtime.

The artifact built here fixes a public calibration frame and the contract that
future source integration must satisfy.  It does not import the runner, open a
task package, execute a tool, or authorize a provider call.  Source integration
and its offline qualification are deliberately the next, separate gate.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.errors import RecoveryError
from patchloop.util import ensure_within, sha256_bytes, sha256_json

PREREGISTRATION_SCHEMA = "lean-harness-runtime-integration-preregistration-v1"
PREREGISTRATION_ID = "lean-harness-runtime-integration-public-calibration-20260816-v1"
PREREGISTRATION_PATH = (
    "experiments/lean-harness-runtime-integration-preregistration-20260816-v1.json"
)
PREREGISTERED_AT = "2026-08-16T14:12:35.9954542Z"

DATASET_MANIFEST_PATH = "data/dataset-manifest.yaml"
DATASET_MANIFEST_FILE_BYTES = 47_368
DATASET_MANIFEST_FILE_SHA256 = (
    "sha256:e8cf14ca9dabebcc03c3522e400dfcb79606541e9b11e59f49510ea5c40bebed"
)

FINALIZATION_RESERVE_PATH = "experiments/lean-harness-finalization-reserve-20260816-v1.json"
FINALIZATION_RESERVE_FILE_BYTES = 6_036
FINALIZATION_RESERVE_FILE_SHA256 = (
    "sha256:30cf34a19c94025777df612b283376be5d08047069f3c49e19b58e950434bf06"
)
FINALIZATION_RESERVE_CONTENT_HASH = (
    "sha256:9458bb1d59d51aaf94a082504a3883d799bf4d807ce7a83376bdc391ab6348db"
)

COMPACTED_SHADOW_PATH = (
    "experiments/lean-harness-compacted-shadow-public-qualification-20260816-v1.json"
)
COMPACTED_SHADOW_FILE_BYTES = 52_449
COMPACTED_SHADOW_FILE_SHA256 = (
    "sha256:c26a8318d0f3ba5d132c003398a97d83eef317b8192021c9fd81b6266dbcbbe1"
)
COMPACTED_SHADOW_CONTENT_HASH = (
    "sha256:566589fe6ecc246bfa31720c141b321e13b6764de37cc80fa8be0dee1f59e8c5"
)

SATURATION_SHADOW_PATH = (
    "experiments/lean-harness-saturation-recovery-shadow-public-qualification-20260816-v2.json"
)
SATURATION_SHADOW_FILE_BYTES = 365_815
SATURATION_SHADOW_FILE_SHA256 = (
    "sha256:d046025d4c4277786d0d63fc3f946aa50d0c1481fb3237200f51aebf13de2478"
)
SATURATION_SHADOW_CONTENT_HASH = (
    "sha256:172359ac848acf18e38fff43117cefd58c4cad691d9180f77008b6bbc8f57916"
)

BUDGET_ADEQUACY_PATH = (
    "experiments/lean-harness-budget-adequacy-public-qualification-20260816-v1.json"
)
BUDGET_ADEQUACY_FILE_BYTES = 62_544
BUDGET_ADEQUACY_FILE_SHA256 = (
    "sha256:8ac0b1dddd5c9850f25909a1ecbc785d63a73e45c58b53d72dd4b5d0286f4625"
)
BUDGET_ADEQUACY_CONTENT_HASH = (
    "sha256:d628390d8cf3971e81144bde8717c10c75f8450c19ae6f441aa5d6c6fa1251e6"
)

SOURCE_PATHS = (
    "patchloop/agent/lean_runtime_preregistration.py",
    "scripts/build_lean_harness_runtime_preregistration.py",
)
VALIDATION_PATHS = ("tests/test_lean_runtime_preregistration.py",)

CONDITIONS = ("no_memory", "structured")
FINALIZATION_TOOLS = ("read_file", "apply_patch", "run_check", "get_diff", "finish_task")
PIPELINE_STAGES = (
    "build-phase-evidence",
    "compact-event-context-and-verify-restoration",
    "project-saturation-recovery-tool-surface",
    "build-and-count-exploration-request",
    "select-exploration-finalization-or-block-mode",
    "filter-finalization-tool-surface-when-required",
    "rebuild-and-recount-after-tool-filtering",
    "project-split-aware-effective-output-allowance",
    "persist-request-evidence-before-generation",
    "dispatch-only-the-persisted-exact-request",
)
REQUEST_EVIDENCE_FIELDS = (
    "runtime_contract_hash",
    "context_build_hash",
    "context_compaction_evidence_hash",
    "phase_evidence_hash",
    "saturation_recovery_evidence_hash",
    "finalization_request_mode_hash",
    "phase_tool_surface_hash",
    "selected_tool_schema_hash",
    "requested_input_tokens",
    "effective_max_output_tokens",
    "split_allowance_hash",
    "request_body_hash",
    "memory_delivery_evidence_sha256",
    "normalized_no_memory_request_body_sha256",
)
FAIL_CLOSED_REASONS = (
    "predecessor-evidence-drift",
    "event-descriptor-restoration-mismatch",
    "phase-evidence-or-tool-surface-mismatch",
    "saturation-threshold-or-strategy-change-mismatch",
    "structured-edit-threshold-not-satisfied",
    "empty-or-unknown-tool-surface",
    "request-rebuild-or-recount-mismatch",
    "split-budget-or-finalization-reserve-exhausted",
    "request-evidence-persistence-failure",
)
EXPECTED_CALIBRATION_TASKS = {
    "config-falsy-override": {
        "path": "tasks/smoke/config-falsy-override",
        "public_spec_hash": (
            "sha256:581e592642862cf6a5e286e032a923480d6b2006784d2bda1cac96b2ff5bd578"
        ),
        "private_spec_hash": (
            "sha256:a15cc52fbad7ff8483786d4b8884d026d755dd8695275d06a9b2ec8906cfe162"
        ),
    },
    "csv-quoted-newline": {
        "path": "tasks/smoke/csv-quoted-newline",
        "public_spec_hash": (
            "sha256:e396266522131f4aabfaae3fd140e33c60eaab17dfdd7bca18be03be3a93e04d"
        ),
        "private_spec_hash": (
            "sha256:c2174e536111cec56d29ad59bb0d547bd38febfff156bb7ca63cdc42c7ef65be"
        ),
    },
    "path-prefix-boundary": {
        "path": "tasks/smoke/path-prefix-boundary",
        "public_spec_hash": (
            "sha256:57ecb70019f4b68c2605e6b8e4813ac80b9b579085f0d5531f09964bd584421b"
        ),
        "private_spec_hash": (
            "sha256:261f245167b171545e186cd56791bc0055d1fdc143b5c0021818a16031cbba40"
        ),
    },
}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if type(key) is not str or key in mapping:
            raise ValueError("dataset manifest has a duplicate or non-string key")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )


class CalibrationTaskBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_id: Literal[
        "config-falsy-override",
        "csv-quoted-newline",
        "path-prefix-boundary",
    ]
    task_version: Literal[1]
    path: Literal[
        "tasks/smoke/config-falsy-override",
        "tasks/smoke/csv-quoted-newline",
        "tasks/smoke/path-prefix-boundary",
    ]
    role: Literal["calibration"]
    admission_state: Literal["fixture"]
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_kind: Literal["synthetic-control"]
    contamination_risk: Literal["none"]
    workflow_type: Literal["issue-fix"]
    difficulty_total: Literal[2]
    difficulty_tier: Literal["easy"]
    deterministic_mock_transcript_registered: Literal[True]
    entry_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_entry(self) -> Self:
        expected_binding = EXPECTED_CALIBRATION_TASKS[self.task_id]
        if (
            self.path != expected_binding["path"]
            or self.public_spec_hash != expected_binding["public_spec_hash"]
            or self.private_spec_hash != expected_binding["private_spec_hash"]
        ):
            raise ValueError("calibration task binding differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"entry_hash"}))
        if self.entry_hash != expected:
            raise ValueError("calibration task entry hash differs")
        return self


class PreregisteredScheduleRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=12)
    wave: Literal[1, 2]
    task_id: Literal[
        "config-falsy-override",
        "csv-quoted-newline",
        "path-prefix-boundary",
    ]
    task_version: Literal[1]
    task_path: str = Field(min_length=1)
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    orientation: Literal["A-then-C", "C-then-A"]
    row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        identity = self.model_dump(mode="json", exclude={"row_id"})
        identity["preregistration_id"] = PREREGISTRATION_ID
        if self.row_id != sha256_json(identity):
            raise ValueError("preregistered row identity differs")
        return self


class LeanRuntimeContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-runtime-contract-v1"]
    runtime_policy_version: Literal["lean-harness-v1"]
    proposed_tool_schema_version: Literal["v7"]
    proposed_context_policy_version: Literal["phase-evidence-v12"]
    system_prompt_version: Literal["SYSTEM_PROMPT_V3"]
    base_tool_schema_version: Literal["v2"]
    request_evidence_schema: Literal["lean-harness-request-evidence-v1"]
    context_compaction_schema: Literal["lean-harness-context-event-compaction-v1"]
    saturation_recovery_policy: Literal["lean-harness-saturation-recovery-v1"]
    finalization_reserve_schema: Literal["finalization-reserve-contract-v1"]
    split_allowance_schema: Literal["split-aware-request-allowance-v1"]
    structured_edit_arguments_schema: Literal["structured-edit-arguments-v1"]
    conditions: tuple[Literal["no_memory", "structured"], ...]
    no_memory_delivery: Literal["null"]
    structured_memory_policy_version: Literal["fixed-d110-bundle-v1"]
    structured_memory_bundle_bytes: Literal[3528]
    structured_memory_bundle_sha256: Literal[
        "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
    ]
    model_provider: Literal["mock"]
    model_id: Literal["patchloop-public-calibration-mock-v1"]
    max_cumulative_input_tokens: Literal[1000000]
    max_cumulative_output_tokens: Literal[100000]
    max_total_tokens: Literal[1100000]
    configured_max_output_tokens: Literal[25000]
    finalization_max_output_tokens: Literal[5000]
    max_model_calls: Literal[240]
    max_tool_calls: Literal[400]
    wall_clock_timeout_seconds: Literal[3600]
    semantic_replay_threshold: Literal[4]
    no_progress_streak_threshold: Literal[2]
    patch_rejection_threshold: Literal[2]
    finalization_tool_names: tuple[str, ...]
    pipeline_stages: tuple[str, ...]
    request_evidence_required_fields: tuple[str, ...]
    fail_closed_reasons: tuple[str, ...]
    legacy_v2_v5_bytes_unchanged: Literal[True]
    no_fallback_to_legacy_after_opt_in: Literal[True]
    tool_filter_is_condition_neutral: Literal[True]
    budget_policy_is_condition_neutral: Literal[True]
    provider_request_requires_persisted_evidence: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.conditions != CONDITIONS:
            raise ValueError("lean runtime condition order differs")
        if self.finalization_tool_names != FINALIZATION_TOOLS:
            raise ValueError("lean runtime finalization tools differ")
        if self.pipeline_stages != PIPELINE_STAGES:
            raise ValueError("lean runtime pipeline order differs")
        if self.request_evidence_required_fields != REQUEST_EVIDENCE_FIELDS:
            raise ValueError("lean runtime request evidence fields differ")
        if self.fail_closed_reasons != FAIL_CLOSED_REASONS:
            raise ValueError("lean runtime failure inventory differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("lean runtime contract hash differs")
        return self


class DevelopmentValidationContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-public-calibration-validation-v1"]
    frame_kind: Literal["deterministic-public-calibration-integration"]
    selection_rule: Literal[
        "frozen-calibration-fixtures-with-existing-deterministic-mock-transcripts"
    ]
    prior_lean_runtime_outcomes_used_for_selection: Literal[False]
    task_count: Literal[3]
    repetitions: Literal[2]
    expected_rows: Literal[12]
    rows_per_condition: Literal[6]
    tasks: tuple[CalibrationTaskBinding, ...]
    schedule: tuple[PreregisteredScheduleRow, ...]
    realized_schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    every_task_repetition_has_one_a_and_one_c: Literal[True]
    repetition_two_reverses_orientation: Literal[True]
    fresh_meaning: Literal["not-previously-run-under-lean-harness-v1"]
    unseen_task_or_population_claimed: Literal[False]
    required_terminal_rows: Literal[12]
    required_resolved_rows: Literal[12]
    required_typed_token_terminals: Literal[0]
    required_provider_calls: Literal[0]
    required_network_calls: Literal[0]
    required_docker_calls: Literal[0]
    required_request_evidence_coverage: Literal["every-model-turn"]
    required_a_c_parity: Literal[
        "same-task-repetition-terminal-tool-sequence-and-non-memory-request-semantics"
    ]
    required_phase_surfaces: Literal[6]
    required_saturation_boundary_cases: Literal[9]
    required_split_budget_boundary_cases: Literal[3]
    quality_effect_estimate_authorized: Literal[False]
    memory_effect_estimate_authorized: Literal[False]
    runtime_source_qualification_required_after_implementation: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_frame(self) -> Self:
        tasks = tuple(
            CalibrationTaskBinding.model_validate(item.model_dump(mode="python"))
            for item in self.tasks
        )
        rows = tuple(
            PreregisteredScheduleRow.model_validate(item.model_dump(mode="python"))
            for item in self.schedule
        )
        if tasks != self.tasks or rows != self.schedule:
            raise ValueError("public calibration nested evidence differs")
        expected_task_ids = (
            "config-falsy-override",
            "csv-quoted-newline",
            "path-prefix-boundary",
        )
        if tuple(item.task_id for item in tasks) != expected_task_ids:
            raise ValueError("public calibration task order differs")
        if tuple(item.order for item in rows) != tuple(range(1, 13)):
            raise ValueError("public calibration row order differs")
        if len({item.row_id for item in rows}) != 12:
            raise ValueError("public calibration row identity is duplicated")
        task_by_id = {item.task_id: item for item in tasks}
        if (
            sum(item.condition == "no_memory" for item in rows) != 6
            or sum(item.condition == "structured" for item in rows) != 6
        ):
            raise ValueError("public calibration condition denominator differs")
        for row in rows:
            task = task_by_id.get(row.task_id)
            if (
                task is None
                or row.task_version != task.task_version
                or row.task_path != task.path
                or row.wave != row.repetition
            ):
                raise ValueError("public calibration row task binding differs")
        if self.realized_schedule_hash != sha256_json(
            [item.model_dump(mode="json") for item in rows]
        ):
            raise ValueError("public calibration schedule hash differs")
        for task in tasks:
            for repetition in (1, 2):
                block = tuple(
                    row
                    for row in rows
                    if row.task_id == task.task_id and row.repetition == repetition
                )
                if len(block) != 2 or {row.condition for row in block} != set(CONDITIONS):
                    raise ValueError("public calibration A/C block differs")
                if block[0].order + 1 != block[1].order:
                    raise ValueError("public calibration A/C block is not adjacent")
                expected_conditions = (
                    ("no_memory", "structured")
                    if block[0].orientation == "A-then-C"
                    else ("structured", "no_memory")
                )
                if tuple(row.condition for row in block) != expected_conditions or any(
                    row.orientation != block[0].orientation for row in block
                ):
                    raise ValueError("public calibration A/C orientation differs")
            orientations = tuple(
                next(
                    row.orientation
                    for row in rows
                    if row.task_id == task.task_id and row.repetition == repetition
                )
                for repetition in (1, 2)
            )
            if orientations not in {("A-then-C", "C-then-A"), ("C-then-A", "A-then-C")}:
                raise ValueError("public calibration orientation is not reversed")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("public calibration contract hash differs")
        return self


class LeanRuntimeIntegrationPreregistration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-runtime-integration-preregistration-v1"]
    preregistration_id: Literal["lean-harness-runtime-integration-public-calibration-20260816-v1"]
    status: Literal["PREREGISTERED_SOURCE_AND_EXECUTION_CLOSED"]
    preregistered_at: Literal["2026-08-16T14:12:35.9954542Z"]
    purpose: Literal["versioned-runtime-integration-public-calibration-no-effect-estimate"]
    dataset_manifest: FileBinding
    predecessor_artifacts: tuple[FileBinding, ...]
    runtime_contract: LeanRuntimeContract
    runtime_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    development_validation: DevelopmentValidationContract
    development_validation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_files: tuple[FileBinding, ...]
    validation_files: tuple[FileBinding, ...]
    source_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    dataset_manifest_files_read: Literal[1]
    predecessor_artifact_files_read: Literal[4]
    source_validation_files_read: Literal[3]
    public_task_files_read: Literal[0]
    private_task_files_read: Literal[0]
    heldout_artifact_files_read: Literal[0]
    r16_artifact_files_read: Literal[0]
    runtime_state_files_read: Literal[0]
    provider_transport_calls: Literal[0]
    provider_generation_calls: Literal[0]
    runner_calls: Literal[0]
    tool_execution_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_model_cost_usd: Literal[0]
    source_integration_completed: Literal[False]
    source_qualification_completed: Literal[False]
    validation_frame_executed: Literal[False]
    provider_calls_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    tool_policy_activation_authorized: Literal[False]
    request_integration_authorized: Literal[False]
    state_mutation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    fresh_memory_comparison_authorized: Literal[False]
    official_analysis_authorized: Literal[False]
    next_gate: Literal[
        "implement-opt-in-lean-harness-v1-and-offline-source-qualify-against-preregistered-frame"
    ]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_preregistration(self) -> Self:
        expected_dataset = FileBinding(
            path=DATASET_MANIFEST_PATH,
            file_bytes=DATASET_MANIFEST_FILE_BYTES,
            file_sha256=DATASET_MANIFEST_FILE_SHA256,
        )
        if self.dataset_manifest != expected_dataset:
            raise ValueError("dataset manifest binding differs")
        expected_predecessors = _expected_predecessors()
        if self.predecessor_artifacts != expected_predecessors:
            raise ValueError("Lean Harness predecessor binding differs")
        runtime = LeanRuntimeContract.model_validate(
            self.runtime_contract.model_dump(mode="python")
        )
        frame = DevelopmentValidationContract.model_validate(
            self.development_validation.model_dump(mode="python")
        )
        if runtime != self.runtime_contract or frame != self.development_validation:
            raise ValueError("Lean Harness nested contract differs")
        if self.runtime_contract_hash != runtime.content_hash:
            raise ValueError("Lean Harness runtime contract binding differs")
        if self.development_validation_hash != frame.content_hash:
            raise ValueError("Lean Harness development frame binding differs")
        if tuple(item.path for item in self.source_files) != SOURCE_PATHS:
            raise ValueError("Lean Harness source inventory path differs")
        if tuple(item.path for item in self.validation_files) != VALIDATION_PATHS:
            raise ValueError("Lean Harness validation inventory path differs")
        if self.source_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.source_files]
        ):
            raise ValueError("Lean Harness source inventory hash differs")
        if self.validation_inventory_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.validation_files]
        ):
            raise ValueError("Lean Harness validation inventory hash differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("Lean Harness preregistration hash differs")
        return self


def _expected_predecessors() -> tuple[FileBinding, ...]:
    return (
        FileBinding(
            path=FINALIZATION_RESERVE_PATH,
            file_bytes=FINALIZATION_RESERVE_FILE_BYTES,
            file_sha256=FINALIZATION_RESERVE_FILE_SHA256,
            content_hash=FINALIZATION_RESERVE_CONTENT_HASH,
        ),
        FileBinding(
            path=COMPACTED_SHADOW_PATH,
            file_bytes=COMPACTED_SHADOW_FILE_BYTES,
            file_sha256=COMPACTED_SHADOW_FILE_SHA256,
            content_hash=COMPACTED_SHADOW_CONTENT_HASH,
        ),
        FileBinding(
            path=SATURATION_SHADOW_PATH,
            file_bytes=SATURATION_SHADOW_FILE_BYTES,
            file_sha256=SATURATION_SHADOW_FILE_SHA256,
            content_hash=SATURATION_SHADOW_CONTENT_HASH,
        ),
        FileBinding(
            path=BUDGET_ADEQUACY_PATH,
            file_bytes=BUDGET_ADEQUACY_FILE_BYTES,
            file_sha256=BUDGET_ADEQUACY_FILE_SHA256,
            content_hash=BUDGET_ADEQUACY_CONTENT_HASH,
        ),
    )


def _repository_root(repository: str | Path) -> Path:
    root = Path(repository).resolve()
    if not root.is_dir():
        raise RecoveryError("repository root is not a directory")
    return root


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _file_binding(root: Path, path: str, *, content_hash: str | None = None) -> FileBinding:
    target = ensure_within(root, path)
    raw = target.read_bytes()
    return FileBinding(
        path=path,
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
        content_hash=content_hash,
    )


def _validated_predecessors(root: Path) -> tuple[FileBinding, ...]:
    for expected in _expected_predecessors():
        target = ensure_within(root, expected.path)
        raw = target.read_bytes()
        if len(raw) != expected.file_bytes or sha256_bytes(raw) != expected.file_sha256:
            raise RecoveryError(f"Lean Harness predecessor differs: {expected.path}")
        try:
            payload = json.loads(
                raw.decode("utf-8", errors="strict"),
                object_pairs_hook=_reject_duplicate_pairs,
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise RecoveryError(f"Lean Harness predecessor is invalid: {expected.path}") from exc
        if type(payload) is not dict or payload.get("content_hash") != expected.content_hash:
            raise RecoveryError(f"Lean Harness predecessor content differs: {expected.path}")
    return _expected_predecessors()


def _manifest_tasks(root: Path) -> tuple[CalibrationTaskBinding, ...]:
    target = ensure_within(root, DATASET_MANIFEST_PATH)
    raw = target.read_bytes()
    if len(raw) != DATASET_MANIFEST_FILE_BYTES or sha256_bytes(raw) != DATASET_MANIFEST_FILE_SHA256:
        raise RecoveryError("dataset manifest differs")
    try:
        payload = yaml.load(raw.decode("utf-8", errors="strict"), Loader=_UniqueKeyLoader)
    except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        raise RecoveryError("dataset manifest is invalid YAML") from exc
    if (
        type(payload) is not dict
        or payload.get("schema_version") != "dataset-manifest-v1"
        or payload.get("dataset_id") != "patchloop-benchmark-v1"
        or payload.get("status") != "frozen"
        or type(payload.get("tasks")) is not list
    ):
        raise RecoveryError("dataset manifest identity differs")
    by_id = {
        item.get("task_id"): item
        for item in payload["tasks"]
        if type(item) is dict and type(item.get("task_id")) is str
    }
    task_ids = (
        "config-falsy-override",
        "csv-quoted-newline",
        "path-prefix-boundary",
    )
    rows: list[CalibrationTaskBinding] = []
    for task_id in task_ids:
        item = by_id.get(task_id)
        if type(item) is not dict:
            raise RecoveryError(f"calibration task is missing: {task_id}")
        source = item.get("source")
        difficulty = item.get("difficulty")
        if type(source) is not dict or type(difficulty) is not dict:
            raise RecoveryError(f"calibration metadata is incomplete: {task_id}")
        body = {
            "task_id": item.get("task_id"),
            "task_version": item.get("task_version"),
            "path": item.get("path"),
            "role": item.get("role"),
            "admission_state": item.get("admission_state"),
            "public_spec_hash": item.get("public_spec_hash"),
            "private_spec_hash": item.get("private_spec_hash"),
            "source_kind": source.get("kind"),
            "contamination_risk": source.get("contamination_risk"),
            "workflow_type": source.get("workflow_type"),
            "difficulty_total": difficulty.get("total"),
            "difficulty_tier": difficulty.get("tier"),
            "deterministic_mock_transcript_registered": True,
        }
        rows.append(
            CalibrationTaskBinding.model_validate({**body, "entry_hash": sha256_json(body)})
        )
    return tuple(rows)


def _schedule(tasks: tuple[CalibrationTaskBinding, ...]) -> tuple[PreregisteredScheduleRow, ...]:
    first_orientation = {
        "config-falsy-override": "A-then-C",
        "csv-quoted-newline": "C-then-A",
        "path-prefix-boundary": "A-then-C",
    }
    rows: list[PreregisteredScheduleRow] = []
    order = 1
    for repetition in (1, 2):
        for task in tasks:
            initial = first_orientation[task.task_id]
            orientation = (
                initial
                if repetition == 1
                else ("C-then-A" if initial == "A-then-C" else "A-then-C")
            )
            conditions = (
                ("no_memory", "structured")
                if orientation == "A-then-C"
                else ("structured", "no_memory")
            )
            for condition in conditions:
                body = {
                    "order": order,
                    "wave": repetition,
                    "task_id": task.task_id,
                    "task_version": task.task_version,
                    "task_path": task.path,
                    "condition": condition,
                    "repetition": repetition,
                    "orientation": orientation,
                }
                identity = {**body, "preregistration_id": PREREGISTRATION_ID}
                rows.append(
                    PreregisteredScheduleRow.model_validate(
                        {**body, "row_id": sha256_json(identity)}
                    )
                )
                order += 1
    return tuple(rows)


def _runtime_contract() -> LeanRuntimeContract:
    body = {
        "schema_version": "lean-harness-runtime-contract-v1",
        "runtime_policy_version": "lean-harness-v1",
        "proposed_tool_schema_version": "v7",
        "proposed_context_policy_version": "phase-evidence-v12",
        "system_prompt_version": "SYSTEM_PROMPT_V3",
        "base_tool_schema_version": "v2",
        "request_evidence_schema": "lean-harness-request-evidence-v1",
        "context_compaction_schema": "lean-harness-context-event-compaction-v1",
        "saturation_recovery_policy": "lean-harness-saturation-recovery-v1",
        "finalization_reserve_schema": "finalization-reserve-contract-v1",
        "split_allowance_schema": "split-aware-request-allowance-v1",
        "structured_edit_arguments_schema": "structured-edit-arguments-v1",
        "conditions": CONDITIONS,
        "no_memory_delivery": "null",
        "structured_memory_policy_version": "fixed-d110-bundle-v1",
        "structured_memory_bundle_bytes": 3_528,
        "structured_memory_bundle_sha256": (
            "sha256:572667d431aa75e4fe74bfc030a99f64245b77d9afa1c88e5d531129f708accf"
        ),
        "model_provider": "mock",
        "model_id": "patchloop-public-calibration-mock-v1",
        "max_cumulative_input_tokens": 1_000_000,
        "max_cumulative_output_tokens": 100_000,
        "max_total_tokens": 1_100_000,
        "configured_max_output_tokens": 25_000,
        "finalization_max_output_tokens": 5_000,
        "max_model_calls": 240,
        "max_tool_calls": 400,
        "wall_clock_timeout_seconds": 3_600,
        "semantic_replay_threshold": 4,
        "no_progress_streak_threshold": 2,
        "patch_rejection_threshold": 2,
        "finalization_tool_names": FINALIZATION_TOOLS,
        "pipeline_stages": PIPELINE_STAGES,
        "request_evidence_required_fields": REQUEST_EVIDENCE_FIELDS,
        "fail_closed_reasons": FAIL_CLOSED_REASONS,
        "legacy_v2_v5_bytes_unchanged": True,
        "no_fallback_to_legacy_after_opt_in": True,
        "tool_filter_is_condition_neutral": True,
        "budget_policy_is_condition_neutral": True,
        "provider_request_requires_persisted_evidence": True,
    }
    return LeanRuntimeContract.model_validate({**body, "content_hash": sha256_json(body)})


def _development_validation(
    tasks: tuple[CalibrationTaskBinding, ...],
) -> DevelopmentValidationContract:
    schedule = _schedule(tasks)
    body = {
        "schema_version": "lean-harness-public-calibration-validation-v1",
        "frame_kind": "deterministic-public-calibration-integration",
        "selection_rule": (
            "frozen-calibration-fixtures-with-existing-deterministic-mock-transcripts"
        ),
        "prior_lean_runtime_outcomes_used_for_selection": False,
        "task_count": 3,
        "repetitions": 2,
        "expected_rows": 12,
        "rows_per_condition": 6,
        "tasks": tuple(item.model_dump(mode="python") for item in tasks),
        "schedule": tuple(item.model_dump(mode="python") for item in schedule),
        "realized_schedule_hash": sha256_json([item.model_dump(mode="json") for item in schedule]),
        "every_task_repetition_has_one_a_and_one_c": True,
        "repetition_two_reverses_orientation": True,
        "fresh_meaning": "not-previously-run-under-lean-harness-v1",
        "unseen_task_or_population_claimed": False,
        "required_terminal_rows": 12,
        "required_resolved_rows": 12,
        "required_typed_token_terminals": 0,
        "required_provider_calls": 0,
        "required_network_calls": 0,
        "required_docker_calls": 0,
        "required_request_evidence_coverage": "every-model-turn",
        "required_a_c_parity": (
            "same-task-repetition-terminal-tool-sequence-and-non-memory-request-semantics"
        ),
        "required_phase_surfaces": 6,
        "required_saturation_boundary_cases": 9,
        "required_split_budget_boundary_cases": 3,
        "quality_effect_estimate_authorized": False,
        "memory_effect_estimate_authorized": False,
        "runtime_source_qualification_required_after_implementation": True,
    }
    return DevelopmentValidationContract.model_validate({**body, "content_hash": sha256_json(body)})


def build_lean_runtime_integration_preregistration(
    repository: str | Path = ".",
) -> LeanRuntimeIntegrationPreregistration:
    root = _repository_root(repository)
    predecessors = _validated_predecessors(root)
    tasks = _manifest_tasks(root)
    runtime = _runtime_contract()
    frame = _development_validation(tasks)
    source_files = tuple(_file_binding(root, path) for path in SOURCE_PATHS)
    validation_files = tuple(_file_binding(root, path) for path in VALIDATION_PATHS)
    body = {
        "schema_version": PREREGISTRATION_SCHEMA,
        "preregistration_id": PREREGISTRATION_ID,
        "status": "PREREGISTERED_SOURCE_AND_EXECUTION_CLOSED",
        "preregistered_at": PREREGISTERED_AT,
        "purpose": "versioned-runtime-integration-public-calibration-no-effect-estimate",
        "dataset_manifest": FileBinding(
            path=DATASET_MANIFEST_PATH,
            file_bytes=DATASET_MANIFEST_FILE_BYTES,
            file_sha256=DATASET_MANIFEST_FILE_SHA256,
        ).model_dump(mode="python"),
        "predecessor_artifacts": tuple(item.model_dump(mode="python") for item in predecessors),
        "runtime_contract": runtime.model_dump(mode="python"),
        "runtime_contract_hash": runtime.content_hash,
        "development_validation": frame.model_dump(mode="python"),
        "development_validation_hash": frame.content_hash,
        "source_files": tuple(item.model_dump(mode="python") for item in source_files),
        "validation_files": tuple(item.model_dump(mode="python") for item in validation_files),
        "source_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in source_files]
        ),
        "validation_inventory_hash": sha256_json(
            [item.model_dump(mode="json") for item in validation_files]
        ),
        "dataset_manifest_files_read": 1,
        "predecessor_artifact_files_read": 4,
        "source_validation_files_read": 3,
        "public_task_files_read": 0,
        "private_task_files_read": 0,
        "heldout_artifact_files_read": 0,
        "r16_artifact_files_read": 0,
        "runtime_state_files_read": 0,
        "provider_transport_calls": 0,
        "provider_generation_calls": 0,
        "runner_calls": 0,
        "tool_execution_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_model_cost_usd": 0,
        "source_integration_completed": False,
        "source_qualification_completed": False,
        "validation_frame_executed": False,
        "provider_calls_authorized": False,
        "runner_activation_authorized": False,
        "tool_policy_activation_authorized": False,
        "request_integration_authorized": False,
        "state_mutation_authorized": False,
        "paid_execution_authorized": False,
        "fresh_memory_comparison_authorized": False,
        "official_analysis_authorized": False,
        "next_gate": (
            "implement-opt-in-lean-harness-v1-and-offline-source-qualify-against-preregistered-frame"
        ),
    }
    return LeanRuntimeIntegrationPreregistration.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def preregistration_bytes(
    preregistration: LeanRuntimeIntegrationPreregistration,
) -> bytes:
    return (
        json.dumps(
            preregistration.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def materialize_lean_runtime_integration_preregistration(
    repository: str | Path = ".",
    output_path: str | Path = PREREGISTRATION_PATH,
) -> LeanRuntimeIntegrationPreregistration:
    root = _repository_root(repository)
    preregistration = build_lean_runtime_integration_preregistration(root)
    content = preregistration_bytes(preregistration)
    output = ensure_within(root, str(output_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if output.read_bytes() != content:
            raise RecoveryError("existing Lean Harness preregistration differs")
        return preregistration
    with output.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return preregistration


def load_lean_runtime_integration_preregistration(
    repository: str | Path = ".",
    path: str | Path = PREREGISTRATION_PATH,
) -> LeanRuntimeIntegrationPreregistration:
    root = _repository_root(repository)
    raw = ensure_within(root, str(path)).read_bytes()
    try:
        text = raw.decode("utf-8", errors="strict")
        json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
        preregistration = LeanRuntimeIntegrationPreregistration.model_validate_json(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError("Lean Harness preregistration is invalid JSON") from exc
    if preregistration_bytes(preregistration) != raw:
        raise RecoveryError("Lean Harness preregistration bytes are not canonical")
    expected = build_lean_runtime_integration_preregistration(root)
    if preregistration != expected:
        raise RecoveryError("Lean Harness preregistration differs from source")
    return preregistration


__all__ = [
    "DevelopmentValidationContract",
    "LeanRuntimeContract",
    "LeanRuntimeIntegrationPreregistration",
    "PREREGISTRATION_ID",
    "PREREGISTRATION_PATH",
    "PREREGISTRATION_SCHEMA",
    "build_lean_runtime_integration_preregistration",
    "load_lean_runtime_integration_preregistration",
    "materialize_lean_runtime_integration_preregistration",
    "preregistration_bytes",
]
