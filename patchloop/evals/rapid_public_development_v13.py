"""AnyIO Lean V8/V12 workflow comparison for Rapid development.

The candidate preserves the consumed V8 control and compares it with the
public-only offline-qualified V12 workflow. Candidate materialization and
rehearsal are no-call operations; live execution remains closed behind a fresh
exact execution hash and cost cap.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.completion_loop_successor_qualification import (
    QUALIFICATION_PATH as COMPLETION_QUALIFICATION_PATH,
)
from patchloop.agent.completion_loop_successor_qualification import (
    load_ordered_correction_qualification,
)
from patchloop.agent.event_descriptor_role_qualification import (
    QUALIFICATION_PATH as EVENT_ROLE_QUALIFICATION_PATH,
)
from patchloop.agent.event_descriptor_role_qualification import (
    load_event_descriptor_role_qualification,
)
from patchloop.agent.finalization_successor_qualification import (
    QUALIFICATION_PATH as FINALIZATION_QUALIFICATION_PATH,
)
from patchloop.agent.finalization_successor_qualification import (
    load_finalization_successor_qualification,
)
from patchloop.agent.mechanical_friction_qualification import (
    QUALIFICATION_PATH as MECHANICAL_QUALIFICATION_PATH,
)
from patchloop.agent.mechanical_friction_qualification import (
    load_mechanical_friction_qualification,
)
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.runner import (
    AgentRunner,
    BatchExecutionAuthorization,
    LiveExecutionAuthorization,
    issue_batch_execution_authorization,
    issue_live_execution_authorization,
    issue_row_execution_authorization,
)
from patchloop.agent.workflow_successor_v2_qualification import (
    QUALIFICATION_PATH as WORKFLOW_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_successor_v2_qualification import (
    SOURCE_FILES as WORKFLOW_SOURCE_FILES,
)
from patchloop.agent.workflow_successor_v2_qualification import (
    load_workflow_successor_v2_qualification,
)
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
    RunOutcomeKind,
    Usage,
)
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_public_development import (
    MODEL_ID,
    RUNTIME_BUDGET,
    _append_bundle_event,
    _persisted_result,
    _UniqueKeyLoader,
    _within,
)
from patchloop.evals.rapid_public_development_v2 import FileBinding, _write_once
from patchloop.evals.rapid_public_development_v4 import (
    _rapid_v4_row_projection,
    _runtime_build_binding,
    _seal_event,
)
from patchloop.memory.fixed_bundle import FIXED_BUNDLE_POLICY_VERSION
from patchloop.runtime import build_manifest
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-public-development-anyio-workflow-revision-ab-v1"
EXPERIMENT_ID = "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11"
SCHEDULE_SEED = 20260825
CONFIG_PATH = Path(
    "experiments/rapid-public-development-anyio-workflow-revision-ab-20260825-r11.yaml"
)
CANDIDATE_SCHEMA = "rapid-public-development-candidate-v17"
CANDIDATE_REVISION = 17
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-candidate-v17.json"
)
REHEARSAL_SCHEMA = "rapid-public-development-rehearsal-v14"
REHEARSAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-"
    "candidate-v17-rehearsal-v14.json"
)
RESULT_SCHEMA = "rapid-public-development-bundle-event-v17"
PLAN_SCHEMA = "experiment-execution-plan-v17"
PLAN_KIND = "rapid-public-development-batch-v1"
RUNTIME_BUILD_SCHEMA = "rapid-runtime-build-v1"
VERIFIER_ID = "rapid-r11-candidate-v17-plan-v17"
RUN_ID_PREFIX = "run_rapid_v17"
HARNESS_ADMISSION_FAILURE = "harness_admission_failure"
MANIFEST_CREATED_AT = datetime(2026, 8, 25, tzinfo=UTC)
TASK_PATH = "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml"
TASK_ID = "anyio-interrupt-runner-cleanup"
TASK_VERSION = 4
VARIANTS = ("lean-harness-v8", "lean-harness-v12")
VARIANT_CONTRACTS = {
    "lean-harness-v8": {
        "tool_schema_version": "v12",
        "context_policy_version": "phase-evidence-v18",
        "runtime_policy_version": "lean-harness-v8",
        "completion_policy_version": "ordered-check-refresh-structured-correction-v1",
        "patch_normalization_policy_version": "safe-raw-diff-normalization-v1",
        "search_glob_policy_version": "recursive-file-glob-normalization-v1",
        "finalization_allowance_policy_version": "configured-ceiling-split-bounded-v1",
        "structured_edit_policy_version": "gateway-fresh-preimage-unique-text-v1",
        "check_outcome_policy_version": "invocation-vs-behavior-v1",
        "event_descriptor_role_policy_version": "typed-distinct-input-role-v1",
        "edit_correction_policy_version": "bounded-public-current-source-v1",
        "correction_context_policy_version": "latest-public-edit-correction-once-v1",
        "provider_terminal_policy_version": "explicit-terminal-before-accounting-v1",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
    },
    "lean-harness-v12": {
        "tool_schema_version": "v16",
        "context_policy_version": "phase-evidence-v22",
        "runtime_policy_version": "lean-harness-v12",
        "completion_policy_version": "bounded-correction-review-repair-v1",
        "pre_mutation_plan_policy_version": "eligible-public-evidence-plan-gate-v2",
        "iterative_plan_revision_policy_version": "epoch-work-plan-revision-v1",
        "plan_admission_recovery_policy_version": "work-plan-admission-recovery-v1",
        "evidence_catalog_schema_version": "eligible-plan-evidence-catalog-v1",
        "recorded_work_plan_schema_version": "recorded-work-plan-v2",
        "active_work_state_schema_version": "active-work-state-v1",
        "protocol_recovery_policy_version": "shared-model-action-contract-recovery-v1",
        "patch_normalization_policy_version": "safe-raw-diff-normalization-v1",
        "search_glob_policy_version": "recursive-file-glob-normalization-v1",
        "finalization_allowance_policy_version": "configured-ceiling-split-bounded-v1",
        "structured_edit_policy_version": "gateway-fresh-preimage-unique-text-v1",
        "check_outcome_policy_version": "invocation-vs-behavior-v1",
        "event_descriptor_role_policy_version": "typed-distinct-input-role-v1",
        "edit_correction_policy_version": "bounded-public-current-source-v2",
        "correction_context_policy_version": "bounded-investigation-current-read-v1",
        "provider_terminal_policy_version": "explicit-terminal-before-accounting-v1",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
    },
}
EXPECTED_CHECK_IDS = (
    "public-interrupt-runner-lifecycle",
    "upstream-pytest-plugin-regression",
)
EXPECTED_SCHEDULE = (
    (1, "lean-harness-v8", 1),
    (2, "lean-harness-v12", 1),
    (3, "lean-harness-v12", 2),
    (4, "lean-harness-v8", 2),
    (5, "lean-harness-v8", 3),
    (6, "lean-harness-v12", 3),
)

PER_RUN_RESERVE_NANOS = 1_200_000_000
FULL_SCHEDULE_RESERVE_NANOS = 7_200_000_000
HARD_CAP_NANOS = 7_500_000_000
PRICES_NANOS = {
    "uncached_input": 750,
    "cached_input": 75,
    "cache_write_input": 750,
    "output": 4_500,
}

PREDECESSOR_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-workflow-ab-20260824-r10-candidate-v16.json"
)
PREDECESSOR_RESULT_PATH = Path(
    "reports/rapid-development/rapid-public-dev-anyio-workflow-ab-20260824-r10-cbe3f560b03b.jsonl"
)
WORKFLOW_QUALIFICATION_FILE_BYTES = 10_604
WORKFLOW_QUALIFICATION_FILE_SHA256 = (
    "sha256:68c66708a2615fb93bfa8eb86fb829692721e5ee90b49bff060c74c8ff45aed0"
)
WORKFLOW_QUALIFICATION_CONTENT_HASH = (
    "sha256:25f65f814818e96e38f258c66d79d7a7d045b6111473f53fb0e1ff4bb891f4f5"
)
WORKFLOW_QUALIFICATION_SCENARIO_SET_HASH = (
    "sha256:9cbe72b111732901ecbc24952b9b7efd45faef94049593dbd7a00a4bc0134ff9"
)
QUALIFICATION_V5_PATH = Path(
    "reports/rapid-development/artifacts/"
    "pdm-anyio-public-behavior-check-qualification-result-v5.json"
)
QUALIFICATION_V7_PATH = Path(
    "reports/rapid-development/artifacts/pdm-public-behavior-check-qualification-result-v7.json"
)
QUALIFICATION_V5_EXECUTION_HASH = (
    "sha256:f7b0159d622ee6329db6560ab253d117187e6a05a5e7bb630ba325588eb211b3"
)
QUALIFICATION_V7_EXECUTION_HASH = (
    "sha256:bb0a182325cfeb66fe030251b244d4528ca84777758ba0a6c41a2de431a28f20"
)
FINALIZATION_QUALIFICATION_FILE_BYTES = 10_944
FINALIZATION_QUALIFICATION_FILE_SHA256 = (
    "sha256:3dc973ec737058b6dd964de1c652f174c6274e060eabc8ace29c3b77694604f1"
)
FINALIZATION_QUALIFICATION_CONTENT_HASH = (
    "sha256:a3146592d6482405eac27f7bbb003ae57982983eabe814a5d86f0aba2e2a3aeb"
)
MECHANICAL_QUALIFICATION_FILE_BYTES = 7_282
MECHANICAL_QUALIFICATION_FILE_SHA256 = (
    "sha256:7d622124874b561f8f8447cdfbb180433cb56d0ff484fae3299bcaf2fe9b0b68"
)
MECHANICAL_QUALIFICATION_CONTENT_HASH = (
    "sha256:0053adbd4ae2d0b4aed0aac3f7885af13e2021c00a75eed892ab72f0f79c5e32"
)
EVENT_ROLE_QUALIFICATION_FILE_BYTES = 3_917
EVENT_ROLE_QUALIFICATION_FILE_SHA256 = (
    "sha256:5b12e5f14428fc6be83ed7da581c0c9b345af0eeae3cdb43a98f6e263e8a9d35"
)
EVENT_ROLE_QUALIFICATION_CONTENT_HASH = (
    "sha256:b946531d9b19597f059370a40b0204d44e404de8e1ece78caa9fc1b51e31e5f2"
)
COMPLETION_QUALIFICATION_FILE_BYTES = 7_367
COMPLETION_QUALIFICATION_FILE_SHA256 = (
    "sha256:a77cd1ab7462d2a6a11bf61e30e15d946d665cae468494730560b5c4b15bf86a"
)
COMPLETION_QUALIFICATION_CONTENT_HASH = (
    "sha256:e329aef73b98a879eb20de70e46c6ed17dda82ac3e92f826f345fa88a6010370"
)
COMPLETION_QUALIFICATION_SCENARIO_SET_HASH = (
    "sha256:8258e9bf5c9208f00f200caa133a96a23ca58d5fa50e37169e37ab1b10e635e2"
)

_REHEARSAL_STAGE_SEQUENCE = (
    "candidate-current-binding",
    "registered-plan-schema",
    "all-row-manifests",
    "batch-capability",
    "batch-start-prefix",
    "first-row-capability",
    "first-provider-dispatch-boundary",
    "realistic-resolved-row-terminal",
    "second-row-prefix",
    "second-row-capability",
    "second-provider-dispatch-boundary",
)


def _verifier_entry_hash() -> str:
    return live_verifier_registry().descriptor_hash_for(
        experiment_id=EXPERIMENT_ID,
        plan_schema=PLAN_SCHEMA,
        plan_kind=PLAN_KIND,
    )


class RapidAnyioCostPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    per_run_reserve_nanos: Literal[1_200_000_000]
    full_schedule_reserve_nanos: Literal[7_200_000_000]
    hard_cap_nanos: Literal[7_500_000_000]
    pricing_nanos_per_token: dict[str, int]

    @model_validator(mode="after")
    def validate_cost(self) -> Self:
        if self.pricing_nanos_per_token != PRICES_NANOS:
            raise ValueError("Rapid AnyIO pricing differs")
        if self.full_schedule_reserve_nanos != 6 * self.per_run_reserve_nanos:
            raise ValueError("Rapid AnyIO full-schedule reserve differs")
        if self.full_schedule_reserve_nanos > self.hard_cap_nanos:
            raise ValueError("Rapid AnyIO reserve exceeds hard cap")
        return self


class RapidAnyioScheduleRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=6)
    task: Literal[TASK_PATH]
    variant: Literal["lean-harness-v8", "lean-harness-v12"]
    repetition: int = Field(ge=1, le=3)

    @field_validator("order", "repetition", mode="before")
    @classmethod
    def exact_int(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("Rapid AnyIO schedule counters must be exact integers")
        return value


class RapidAnyioWorkflowABConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-public-development-anyio-workflow-revision-ab-v1"]
    experiment_id: Literal["rapid-public-dev-anyio-workflow-revision-ab-20260825-r11"]
    status: Literal["development-only"]
    official: Literal[False]
    selection_policy_version: Literal["qualified-public-v8-v12-workflow-revision-ab-v1"]
    public_development_history_only: Literal[True]
    heldout_outcomes_used: Literal[False]
    private_evidence_used: Literal[False]
    frozen_dataset_modified: Literal[False]
    task_successor_opt_in: Literal[True]
    tasks: tuple[str, ...]
    variants: tuple[Literal["lean-harness-v8"], Literal["lean-harness-v12"]]
    repetitions: Literal[3]
    memory_condition: Literal["no_memory"]
    model_provider: Literal["openai"]
    model_id: Literal["gpt-5.4-mini-2026-03-17"]
    reasoning_effort: Literal["medium"]
    reasoning_mode: Literal["standard"]
    service_tier: Literal["default"]
    transport_max_retries: Literal[0]
    max_output_tokens: Literal[25_000]
    budget: Budget
    schedule: tuple[RapidAnyioScheduleRow, ...] = Field(min_length=6, max_length=6)
    metrics: tuple[str, ...]
    cost_policy: RapidAnyioCostPolicy
    provider_execution_authorized: Literal[False]
    approved_execution_hash: None

    @model_validator(mode="before")
    @classmethod
    def freeze_yaml_sequences(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        frozen = dict(value)
        for field in ("tasks", "variants", "schedule", "metrics"):
            sequence = frozen.get(field)
            if type(sequence) is not list:
                raise ValueError(f"Rapid AnyIO {field} must be a YAML sequence")
            frozen[field] = tuple(sequence)
        return frozen

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if self.tasks != (TASK_PATH,) or self.variants != VARIANTS:
            raise ValueError("Rapid AnyIO task or variant panel differs")
        if self.budget != RUNTIME_BUDGET:
            raise ValueError("Rapid AnyIO runtime budget differs")
        if self.metrics != (
            "evaluator_reached",
            "token_terminal",
            "submission_completed",
            "success_at_budget",
            "model_calls",
            "tool_calls",
            "model_cost_nanos",
        ):
            raise ValueError("Rapid AnyIO metric set differs")
        actual = tuple((row.order, row.variant, row.repetition) for row in self.schedule)
        if actual != EXPECTED_SCHEDULE:
            raise ValueError("Rapid AnyIO schedule is not the exact balanced matrix")
        return self


class RapidAnyioTaskBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_path: Literal[TASK_PATH]
    task_id: Literal["anyio-interrupt-runner-cleanup"]
    task_version: Literal[4]
    base_commit: str
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_image: str
    evaluator_image_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    package_file_count: int = Field(gt=0)
    package_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    visible_check_ids: tuple[str, ...] = Field(min_length=2, max_length=2)
    visible_check_command_hashes: tuple[str, ...] = Field(min_length=2, max_length=2)
    task_successor_opt_in: Literal[True]
    frozen_dataset_member: Literal[False]
    qualification_binding_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_task(self) -> Self:
        if self.visible_check_ids != EXPECTED_CHECK_IDS:
            raise ValueError("Rapid AnyIO visible check identity differs")
        return self


@dataclass(frozen=True)
class PreparedRapidV13Batch:
    plan: dict[str, Any]
    plan_hash: str
    manifests: tuple[RunManifest, ...]
    authorization: BatchExecutionAuthorization
    verifier_id: str


def _file_binding(root: Path, relative: str | Path) -> FileBinding:
    selected = ensure_within(root, Path(relative).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError(f"Rapid AnyIO source is unavailable: {relative}")
    raw = selected.read_bytes()
    return FileBinding(
        path=selected.relative_to(root).as_posix(),
        file_bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _stable_json(root: Path, relative: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    selected = ensure_within(root, relative.as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError(f"{label} is unavailable")
    first = selected.read_bytes()
    second = selected.read_bytes()
    if first != second:
        raise RecoveryError(f"{label} changed during validation")
    try:
        payload = json.loads(first.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"{label} is invalid") from exc
    if type(payload) is not dict:
        raise RecoveryError(f"{label} must be an object")
    body = {key: value for key, value in payload.items() if key != "content_hash"}
    if payload.get("content_hash") != sha256_json(body):
        raise RecoveryError(f"{label} content hash differs")
    return payload, first


def _workflow_source_transition(root: Path, qualification: Any) -> dict[str, Any]:
    qualified = {item.path: item for item in qualification.source_files}
    if tuple(qualified) != WORKFLOW_SOURCE_FILES:
        raise RecoveryError("Rapid AnyIO workflow source inventory differs")
    rows: list[dict[str, Any]] = []
    changed_paths: list[str] = []
    for relative in WORKFLOW_SOURCE_FILES:
        prior = qualified[relative]
        current = _file_binding(root, relative)
        unchanged = bool(
            prior.bytes == current.file_bytes and prior.file_sha256 == current.file_sha256
        )
        if not unchanged:
            changed_paths.append(relative)
        rows.append(
            {
                "path": relative,
                "qualified_file_bytes": prior.bytes,
                "qualified_file_sha256": prior.file_sha256,
                "current_file_bytes": current.file_bytes,
                "current_file_sha256": current.file_sha256,
                "unchanged": unchanged,
            }
        )
    if changed_paths:
        raise RecoveryError("Rapid AnyIO activation must preserve every qualified workflow source")
    return {
        "schema_version": "workflow-successor-qualification-to-live-activation-v1",
        "qualified_snapshot_preserved": True,
        "unchanged_workflow_source_count": len(rows) - len(changed_paths),
        "permitted_changed_paths": changed_paths,
        "activation_change_role": "r11-candidate-and-verifier-registration-only",
        "source_rows": rows,
    }


def _qualification_evidence(root: Path) -> dict[str, Any]:
    v5, v5_raw = _stable_json(root, QUALIFICATION_V5_PATH, label="qualification v5")
    v7, v7_raw = _stable_json(root, QUALIFICATION_V7_PATH, label="qualification v7")
    finalization = load_finalization_successor_qualification(root)
    finalization_raw = ensure_within(root, FINALIZATION_QUALIFICATION_PATH.as_posix()).read_bytes()
    mechanical = load_mechanical_friction_qualification(root)
    mechanical_raw = ensure_within(root, MECHANICAL_QUALIFICATION_PATH.as_posix()).read_bytes()
    event_role = load_event_descriptor_role_qualification(root)
    event_role_raw = ensure_within(root, EVENT_ROLE_QUALIFICATION_PATH.as_posix()).read_bytes()
    completion = load_ordered_correction_qualification(root)
    completion_raw = ensure_within(root, COMPLETION_QUALIFICATION_PATH.as_posix()).read_bytes()
    workflow = load_workflow_successor_v2_qualification(root)
    workflow_raw = ensure_within(root, WORKFLOW_QUALIFICATION_PATH.as_posix()).read_bytes()
    source_transition = _workflow_source_transition(root, workflow)
    retained = v7.get("retained_anyio_qualification")
    rows = [
        row
        for row in v5.get("row_observations", [])
        if isinstance(row, dict) and row.get("task_id") == TASK_ID
    ]
    if len(rows) != 2:
        raise RecoveryError("Rapid AnyIO qualification row count differs")
    base = next((row for row in rows if row.get("source_state") == "base"), None)
    reference = next((row for row in rows if row.get("source_state") == "reference"), None)
    if not (
        v5.get("execution_hash") == QUALIFICATION_V5_EXECUTION_HASH
        and v5.get("official") is False
        and v5.get("provider_calls") == 0
        and v5.get("network_calls") == 0
        and v7.get("execution_hash") == QUALIFICATION_V7_EXECUTION_HASH
        and v7.get("official") is False
        and v7.get("next_gate") == "preserve-result-and-retire-pdm-targeted-check"
        and isinstance(retained, dict)
        and retained.get("status") == "QUALIFIED_FROM_CONSUMED_V5_ROWS"
        and retained.get("task_id") == TASK_ID
        and retained.get("task_version") == TASK_VERSION
        and isinstance(base, dict)
        and base.get("task_version") == TASK_VERSION
        and base.get("expected_observation_matched") is True
        and base.get("observation") == "public-assertion-failure"
        and base.get("public_assertion_marker_observed") is True
        and base.get("raw_output_persisted") is False
        and isinstance(reference, dict)
        and reference.get("task_version") == TASK_VERSION
        and reference.get("expected_observation_matched") is True
        and reference.get("observation") == "pass"
        and reference.get("raw_output_persisted") is False
        and retained.get("base_row_hash") == sha256_json(base)
        and retained.get("reference_row_hash") == sha256_json(reference)
        and len(finalization_raw) == FINALIZATION_QUALIFICATION_FILE_BYTES
        and sha256_bytes(finalization_raw) == FINALIZATION_QUALIFICATION_FILE_SHA256
        and finalization.content_hash == FINALIZATION_QUALIFICATION_CONTENT_HASH
        and finalization.runtime_policy_version == "lean-harness-v4"
        and finalization.tool_schema_version == "v9"
        and finalization.context_policy_version == "phase-evidence-v14"
        and finalization.policy_arithmetic_qualified is True
        and finalization.runtime_activation_authorized is False
        and finalization.provider_calls_authorized is False
        and finalization.paid_execution_authorized is False
        and len(mechanical_raw) == MECHANICAL_QUALIFICATION_FILE_BYTES
        and sha256_bytes(mechanical_raw) == MECHANICAL_QUALIFICATION_FILE_SHA256
        and mechanical.content_hash == MECHANICAL_QUALIFICATION_CONTENT_HASH
        and mechanical.runtime_policy_version == "lean-harness-v5"
        and mechanical.tool_schema_version == "v10"
        and mechanical.context_policy_version == "phase-evidence-v15"
        and mechanical.mechanical_paths_offline_qualified is True
        and mechanical.historical_runtime_bytes_mutated is False
        and mechanical.task_or_evaluator_contract_changed is False
        and mechanical.hidden_or_private_data_read is False
        and mechanical.provider_calls == 0
        and mechanical.docker_calls == 0
        and mechanical.evaluator_calls == 0
        and mechanical.added_cost_usd == "0"
        and mechanical.runtime_activation_authorized is False
        and mechanical.paid_execution_authorized is False
        and len(event_role_raw) == EVENT_ROLE_QUALIFICATION_FILE_BYTES
        and sha256_bytes(event_role_raw) == EVENT_ROLE_QUALIFICATION_FILE_SHA256
        and event_role.content_hash == EVENT_ROLE_QUALIFICATION_CONTENT_HASH
        and event_role.runtime_policy_version == "lean-harness-v6"
        and event_role.tool_schema_version == "v10"
        and event_role.context_policy_version == "phase-evidence-v16"
        and event_role.production_composition_offline_qualified is True
        and event_role.historical_runtime_bytes_mutated is False
        and event_role.hidden_or_private_data_read is False
        and event_role.provider_calls == 0
        and event_role.docker_calls == 0
        and event_role.evaluator_calls == 0
        and event_role.added_cost_usd == "0"
        and event_role.runtime_activation_authorized is False
        and event_role.paid_execution_authorized is False
        and event_role.r6_retry_authorized is False
        and event_role.quality_improvement_established is False
        and len(completion_raw) == COMPLETION_QUALIFICATION_FILE_BYTES
        and sha256_bytes(completion_raw) == COMPLETION_QUALIFICATION_FILE_SHA256
        and completion.content_hash == COMPLETION_QUALIFICATION_CONTENT_HASH
        and completion.scenario_set_hash == COMPLETION_QUALIFICATION_SCENARIO_SET_HASH
        and completion.runtime_policy_version == "lean-harness-v8"
        and completion.tool_schema_version == "v12"
        and completion.context_policy_version == "phase-evidence-v18"
        and completion.completion_policy_version == "ordered-check-refresh-structured-correction-v1"
        and completion.correction_context_policy_version == "latest-public-edit-correction-once-v1"
        and completion.provider_terminal_attribution_policy_version
        == "explicit-terminal-before-accounting-v1"
        and completion.runtime_contract_offline_qualified is True
        and completion.v7_consumed_artifact_preserved is True
        and completion.task_or_evaluator_contract_changed is False
        and completion.hidden_or_private_data_read is False
        and completion.provider_calls == 0
        and completion.docker_calls == 0
        and completion.evaluator_calls == 0
        and completion.added_cost_usd == "0"
        and completion.runtime_activation_authorized is False
        and completion.paid_execution_authorized is False
        and completion.quality_improvement_established is False
        and len(workflow_raw) == WORKFLOW_QUALIFICATION_FILE_BYTES
        and sha256_bytes(workflow_raw) == WORKFLOW_QUALIFICATION_FILE_SHA256
        and workflow.content_hash == WORKFLOW_QUALIFICATION_CONTENT_HASH
        and workflow.scenario_set_hash == WORKFLOW_QUALIFICATION_SCENARIO_SET_HASH
        and workflow.runtime_versions == ("lean-harness-v11", "lean-harness-v12")
        and workflow.tool_schema_versions == ("v15", "v16")
        and workflow.context_policy_versions == ("phase-evidence-v21", "phase-evidence-v22")
        and workflow.runtime_contract_offline_qualified is True
        and workflow.predecessor_files_modified is False
        and workflow.task_or_evaluator_contract_changed is False
        and workflow.hidden_or_private_data_read is False
        and workflow.reference_patch_read is False
        and workflow.reasoning_text_read is False
        and workflow.provider_calls == 0
        and workflow.docker_calls == 0
        and workflow.evaluator_calls == 0
        and workflow.visible_check_calls == 0
        and workflow.added_cost_usd == "0"
        and workflow.runtime_activation_authorized is False
        and workflow.paid_execution_authorized is False
        and workflow.quality_improvement_established is False
    ):
        raise RecoveryError("Rapid AnyIO qualification binding differs")
    return {
        "schema_version": "rapid-anyio-workflow-revision-ab-selection-evidence-v1",
        "policy_version": "qualified-public-v8-v12-workflow-revision-ab-v1",
        "official": False,
        "heldout_outcomes_used": False,
        "private_evidence_used": False,
        "pdm_task_included": False,
        "reference_result_role": "check-admission-only-not-task-semantic-authority",
        "public_contract_source": "public-task-description-and-upstream-public-behavior",
        "qualification_v5": {
            "path": QUALIFICATION_V5_PATH.as_posix(),
            "file_bytes": len(v5_raw),
            "file_sha256": sha256_bytes(v5_raw),
            "content_hash": v5["content_hash"],
            "execution_hash": v5["execution_hash"],
        },
        "retention_v7": {
            "path": QUALIFICATION_V7_PATH.as_posix(),
            "file_bytes": len(v7_raw),
            "file_sha256": sha256_bytes(v7_raw),
            "content_hash": v7["content_hash"],
            "execution_hash": v7["execution_hash"],
        },
        "retained_anyio": retained,
        "finalization_successor": {
            "path": FINALIZATION_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(finalization_raw),
            "file_sha256": sha256_bytes(finalization_raw),
            "content_hash": finalization.content_hash,
            "qualification_id": finalization.qualification_id,
            "runtime_policy_version": finalization.runtime_policy_version,
            "tool_schema_version": finalization.tool_schema_version,
            "context_policy_version": finalization.context_policy_version,
            "completion_policy_version": finalization.completion_policy_version,
            "finalization_allowance_policy_version": (
                finalization.finalization_allowance_policy_version
            ),
            "runtime_activation_authorized": False,
        },
        "mechanical_successor": {
            "path": MECHANICAL_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(mechanical_raw),
            "file_sha256": sha256_bytes(mechanical_raw),
            "content_hash": mechanical.content_hash,
            "qualification_id": mechanical.qualification_id,
            "scenario_set_hash": mechanical.scenario_set_hash,
            "runtime_policy_version": mechanical.runtime_policy_version,
            "tool_schema_version": mechanical.tool_schema_version,
            "context_policy_version": mechanical.context_policy_version,
            "structured_edit_policy_version": mechanical.structured_edit_policy_version,
            "check_outcome_policy_version": mechanical.check_outcome_policy_version,
            "incomplete_recovery_policy_version": (mechanical.incomplete_recovery_policy_version),
            "runtime_activation_authorized": False,
        },
        "event_role_successor": {
            "path": EVENT_ROLE_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(event_role_raw),
            "file_sha256": sha256_bytes(event_role_raw),
            "content_hash": event_role.content_hash,
            "qualification_id": event_role.qualification_id,
            "scenario_set_hash": event_role.scenario_set_hash,
            "source_execution_hash": event_role.source_execution_hash,
            "runtime_policy_version": event_role.runtime_policy_version,
            "tool_schema_version": event_role.tool_schema_version,
            "context_policy_version": event_role.context_policy_version,
            "compaction_schema_version": event_role.compaction_schema_version,
            "event_descriptor_role_policy_version": (
                event_role.event_descriptor_role_policy_version
            ),
            "runtime_activation_authorized": False,
            "r6_retry_authorized": False,
            "quality_improvement_established": False,
        },
        "ordered_correction_successor": {
            "path": COMPLETION_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(completion_raw),
            "file_sha256": sha256_bytes(completion_raw),
            "content_hash": completion.content_hash,
            "qualification_id": completion.qualification_id,
            "scenario_set_hash": completion.scenario_set_hash,
            "runtime_policy_version": completion.runtime_policy_version,
            "tool_schema_version": completion.tool_schema_version,
            "context_policy_version": completion.context_policy_version,
            "completion_policy_version": completion.completion_policy_version,
            "correction_context_policy_version": (completion.correction_context_policy_version),
            "provider_terminal_attribution_policy_version": (
                completion.provider_terminal_attribution_policy_version
            ),
            "runtime_activation_authorized": False,
            "quality_improvement_established": False,
        },
        "workflow_successor": {
            "path": WORKFLOW_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(workflow_raw),
            "file_sha256": sha256_bytes(workflow_raw),
            "content_hash": workflow.content_hash,
            "qualification_id": workflow.qualification_id,
            "scenario_set_hash": workflow.scenario_set_hash,
            "runtime_versions": list(workflow.runtime_versions),
            "tool_schema_versions": list(workflow.tool_schema_versions),
            "context_policy_versions": list(workflow.context_policy_versions),
            "runtime_activation_authorized": False,
            "quality_improvement_established": False,
        },
        "source_transition": source_transition,
    }


def _read_config(
    path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> tuple[RapidAnyioWorkflowABConfig, bytes, Path]:
    root = Path(repository).resolve()
    selected = _within(root, path)
    if selected.relative_to(root).as_posix() != CONFIG_PATH.as_posix():
        raise ContractError("Rapid AnyIO requires its canonical config path")
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("Rapid AnyIO config must be a regular repository file")
    raw = selected.read_bytes()
    try:
        payload = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
        config = RapidAnyioWorkflowABConfig.model_validate(payload)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        raise ContractError("Rapid AnyIO config is invalid") from exc
    return config, raw, selected


def _package_inventory(task_dir: Path) -> tuple[int, str]:
    required = {"public.yaml", "private.yaml", "environment.yaml", "reference.patch"}
    if not required.issubset({item.name for item in task_dir.iterdir()}):
        raise RecoveryError("Rapid AnyIO task package is incomplete")
    rows: list[dict[str, Any]] = []
    for path in sorted(task_dir.rglob("*")):
        if path.is_symlink():
            raise RecoveryError("Rapid AnyIO task package contains a link")
        if path.is_dir():
            continue
        resolved = path.resolve()
        if task_dir not in resolved.parents:
            raise RecoveryError("Rapid AnyIO task package escapes its root")
        raw = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(task_dir).as_posix(),
                "file_bytes": len(raw),
                "file_sha256": sha256_bytes(raw),
            }
        )
    return len(rows), sha256_json(rows)


def _task_binding(
    config: RapidAnyioWorkflowABConfig,
    root: Path,
    qualification: dict[str, Any],
) -> RapidAnyioTaskBinding:
    task_path = config.tasks[0]
    task_dir = _within(root, task_path).parent
    package = load_task_package(task_dir)
    check_ids = tuple(item.id for item in package.public.visible_checks)
    if not (
        task_path == TASK_PATH
        and package.public.task_id == TASK_ID
        and package.public.task_version == TASK_VERSION
        and package.public.split == "dev-validation"
        and package.environment is not None
        and check_ids == EXPECTED_CHECK_IDS
    ):
        raise ContractError("Rapid AnyIO task lacks its qualified public successor")
    count, inventory_hash = _package_inventory(task_dir)
    return RapidAnyioTaskBinding(
        task_path=TASK_PATH,
        task_id=TASK_ID,
        task_version=TASK_VERSION,
        base_commit=package.public.repository.base_commit,
        public_spec_hash=package.public_spec_hash,
        private_spec_hash=package.private_spec_hash,
        evaluator_image=package.environment.evaluator_image,
        evaluator_image_digest=package.environment.image_digest,
        package_file_count=count,
        package_inventory_hash=inventory_hash,
        visible_check_ids=check_ids,
        visible_check_command_hashes=tuple(
            sha256_json(list(item.command)) for item in package.public.visible_checks
        ),
        task_successor_opt_in=True,
        frozen_dataset_member=False,
        qualification_binding_hash=sha256_json(qualification),
    )


def _schedule_projection(
    config: RapidAnyioWorkflowABConfig,
    binding: RapidAnyioTaskBinding,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for row in config.schedule:
        variant = VARIANT_CONTRACTS[row.variant]
        body = {
            "order": row.order,
            "task": row.task,
            "task_id": binding.task_id,
            "task_version": binding.task_version,
            "variant": row.variant,
            "tool_schema_version": variant["tool_schema_version"],
            "context_policy_version": variant["context_policy_version"],
            "repetition": row.repetition,
            "memory_condition": MemoryCondition.NO_MEMORY.value,
        }
        rows.append({**body, "schedule_row_id": sha256_json(body)})
    return tuple(rows)


def _candidate_body(repository: str | Path = ".") -> dict[str, Any]:
    root = Path(repository).resolve()
    config, raw, selected = _read_config(repository=root)
    qualification = _qualification_evidence(root)
    binding = _task_binding(config, root, qualification)
    schedule = _schedule_projection(config, binding)
    runtime_build_hash, dependencies = _runtime_build_binding(root)
    cost_control = {
        **config.cost_policy.model_dump(mode="json"),
        "scheduled_run_count": len(schedule),
        "cost_censoring_allowed": False,
        "official": False,
    }
    model_contract = {
        "provider": "openai",
        "model_id": MODEL_ID,
        "provider_sdk_version": dependencies["openai_sdk_version"],
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "temperature": 0.0,
        "max_output_tokens": 25_000,
    }
    return {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_revision": CANDIDATE_REVISION,
        "experiment_id": EXPERIMENT_ID,
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "config_path": selected.relative_to(root).as_posix(),
        "config_file_sha256": sha256_bytes(raw),
        "config_semantic_hash": sha256_json(config.model_dump(mode="json")),
        "selection_evidence": qualification,
        "selection_evidence_hash": sha256_json(qualification),
        "runtime_build_schema": RUNTIME_BUILD_SCHEMA,
        "runtime_build_hash": runtime_build_hash,
        "model_contract": model_contract,
        "predecessor_candidate": _file_binding(root, PREDECESSOR_CANDIDATE_PATH).model_dump(
            mode="json"
        ),
        "predecessor_result": _file_binding(root, PREDECESSOR_RESULT_PATH).model_dump(mode="json"),
        "variant_contracts": VARIANT_CONTRACTS,
        "task_bindings": [binding.model_dump(mode="json")],
        "schedule": list(schedule),
        "schedule_hash": sha256_json(list(schedule)),
        "cost_control": cost_control,
        "cost_control_hash": sha256_json(cost_control),
    }


_EXECUTION_KEYS = (
    "schema_version",
    "candidate_revision",
    "experiment_id",
    "purpose",
    "official",
    "config_path",
    "config_file_sha256",
    "config_semantic_hash",
    "selection_evidence",
    "selection_evidence_hash",
    "runtime_build_schema",
    "runtime_build_hash",
    "model_contract",
    "predecessor_candidate",
    "predecessor_result",
    "variant_contracts",
    "task_bindings",
    "schedule",
    "schedule_hash",
    "cost_control",
    "cost_control_hash",
)


def _execution_body(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        return {key: candidate[key] for key in _EXECUTION_KEYS}
    except KeyError as exc:
        raise RecoveryError("Rapid candidate-v17 execution body is incomplete") from exc


def build_rapid_public_development_v13_candidate(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build the deterministic candidate under explicit external-call guards."""

    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    original_available = DockerSandbox.available
    original_next_turn = OpenAIResponsesAdapter.next_turn
    original_execute_request = OpenAIResponsesAdapter.execute_request
    original_start = AgentRunner.start
    original_create_connection = socket.create_connection
    original_socket_connect = socket.socket.connect
    original_popen = subprocess.Popen

    def blocked_external(*_args: Any, **_kwargs: Any) -> Any:
        raise RecoveryError("Rapid candidate-v17 generation attempted an external call")

    DockerSandbox.available = staticmethod(blocked_external)
    OpenAIResponsesAdapter.next_turn = blocked_external
    OpenAIResponsesAdapter.execute_request = blocked_external
    AgentRunner.start = blocked_external
    socket.create_connection = blocked_external
    socket.socket.connect = blocked_external
    subprocess.Popen = blocked_external
    try:
        body = _candidate_body(root)
    finally:
        DockerSandbox.available = staticmethod(original_available)
        OpenAIResponsesAdapter.next_turn = original_next_turn
        OpenAIResponsesAdapter.execute_request = original_execute_request
        AgentRunner.start = original_start
        socket.create_connection = original_create_connection
        socket.socket.connect = original_socket_connect
        subprocess.Popen = original_popen
    execution_hash = sha256_json(body)
    candidate = {
        **body,
        "execution_hash": execution_hash,
        "source_qualified": True,
        "execution_authorized": False,
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "approval_required": True,
        "rehearsal_required": True,
    }
    return {**candidate, "content_hash": sha256_json(candidate)}


def _validate_candidate(candidate: dict[str, Any]) -> None:
    content_body = {key: value for key, value in candidate.items() if key != "content_hash"}
    schedule = candidate.get("schedule")
    task_bindings = candidate.get("task_bindings")
    cost_control = candidate.get("cost_control")
    selection_evidence = candidate.get("selection_evidence")
    if not (
        type(candidate) is dict
        and candidate.get("schema_version") == CANDIDATE_SCHEMA
        and candidate.get("candidate_revision") == CANDIDATE_REVISION
        and candidate.get("experiment_id") == EXPERIMENT_ID
        and candidate.get("official") is False
        and candidate.get("runtime_build_schema") == RUNTIME_BUILD_SCHEMA
        and candidate.get("source_qualified") is True
        and candidate.get("execution_authorized") is False
        and candidate.get("provider_calls_made") == 0
        and candidate.get("docker_calls_made") == 0
        and candidate.get("added_model_cost_usd") == 0.0
        and candidate.get("approval_required") is True
        and candidate.get("rehearsal_required") is True
        and candidate.get("config_path") == CONFIG_PATH.as_posix()
        and candidate.get("variant_contracts") == VARIANT_CONTRACTS
        and isinstance(task_bindings, list)
        and len(task_bindings) == 1
        and isinstance(task_bindings[0], dict)
        and task_bindings[0].get("task_path") == TASK_PATH
        and isinstance(schedule, list)
        and len(schedule) == 6
        and all(isinstance(row, dict) for row in schedule)
        and tuple((row.get("order"), row.get("variant"), row.get("repetition")) for row in schedule)
        == EXPECTED_SCHEDULE
        and candidate.get("schedule_hash") == sha256_json(schedule)
        and isinstance(cost_control, dict)
        and candidate.get("cost_control_hash") == sha256_json(cost_control)
        and isinstance(selection_evidence, dict)
        and candidate.get("selection_evidence_hash") == sha256_json(selection_evidence)
        and candidate.get("execution_hash") == sha256_json(_execution_body(candidate))
        and candidate.get("content_hash") == sha256_json(content_body)
    ):
        raise RecoveryError("Rapid candidate-v17 identity differs")


def candidate_bytes(candidate: dict[str, Any]) -> bytes:
    _validate_candidate(candidate)
    return (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_consumed_rapid_public_development_v13_candidate(
    repository: str | Path = ".",
    candidate_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    """Load immutable candidate bytes without claiming current-source identity."""

    root = Path(repository).resolve()
    selected = ensure_within(root, Path(candidate_path).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError("Rapid candidate-v17 is unavailable")
    try:
        candidate = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("Rapid candidate-v17 is invalid") from exc
    if type(candidate) is not dict or candidate_bytes(candidate) != selected.read_bytes():
        raise RecoveryError("Rapid candidate-v17 bytes differ")
    return candidate


def materialize_rapid_public_development_v13_candidate(
    repository: str | Path = ".",
    output_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    output = ensure_within(root, Path(output_path).as_posix())
    if output.exists():
        return load_rapid_public_development_v13_candidate(root, output_path)
    candidate = build_rapid_public_development_v13_candidate(repository=root)
    _prepare_batch(candidate, authority_kind="rehearsal", repository=root)
    _write_once(output, candidate_bytes(candidate))
    return load_rapid_public_development_v13_candidate(root, output_path)


def load_rapid_public_development_v13_candidate(
    repository: str | Path = ".",
    candidate_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    candidate = load_consumed_rapid_public_development_v13_candidate(
        root,
        candidate_path,
    )
    current = build_rapid_public_development_v13_candidate(repository=root)
    if candidate != current:
        raise RecoveryError("Rapid candidate-v17 current binding differs")
    return candidate


def _plan(candidate: dict[str, Any], *, approved: bool) -> dict[str, Any]:
    _validate_candidate(candidate)
    body = {
        "schema_version": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "experiment_id": EXPERIMENT_ID,
        "candidate_revision": CANDIDATE_REVISION,
        "candidate_content_hash": candidate["content_hash"],
        "ready": approved,
        "blockers": [] if approved else ["EXACT_APPROVAL_REQUIRED"],
        "purpose": ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT.value,
        "official": False,
        "execution_hash": candidate["execution_hash"],
        "suite_hash": candidate["config_semantic_hash"],
        "config_file_sha256": candidate["config_file_sha256"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "selection_evidence_hash": candidate["selection_evidence_hash"],
        "model_contract": candidate["model_contract"],
        "variant_contracts": candidate["variant_contracts"],
        "task_bindings": candidate["task_bindings"],
        "schedule_seed": SCHEDULE_SEED,
        "dataset_role": DatasetRole.DEVELOPMENT_VALIDATION.value,
        "schedule": candidate["schedule"],
        "schedule_hash": candidate["schedule_hash"],
        "campaign_cost_control": {
            "content_hash": candidate["cost_control_hash"],
            "descriptor": candidate["cost_control"],
        },
        "approval": {
            "invocation_approve_live_cost": approved,
            "invocation_approved_execution_hash": (
                candidate["execution_hash"] if approved else None
            ),
            "matches_execution_hash": approved,
        },
    }
    return {**body, "content_hash": sha256_json(body)}


def _plan_bytes(plan: dict[str, Any]) -> bytes:
    return (canonical_json(plan) + "\n").encode("utf-8")


def _run_id(candidate: dict[str, Any], order: int) -> str:
    return f"{RUN_ID_PREFIX}_{candidate['execution_hash'][7:19]}_{order:02d}"


def _build_manifest_unchecked(
    candidate: dict[str, Any],
    order: int,
    *,
    repository: str | Path,
) -> RunManifest:
    root = Path(repository).resolve()
    row = next(item for item in candidate["schedule"] if item["order"] == order)
    binding = candidate["task_bindings"][0]
    package = load_task_package(_within(root, row["task"]).parent)
    experiment = ExperimentRunContext(
        experiment_id=EXPERIMENT_ID,
        purpose=ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT,
        suite_hash=candidate["config_semantic_hash"],
        execution_hash=candidate["execution_hash"],
        campaign_cost_control_hash=candidate["cost_control_hash"],
        dataset_manifest_hash=None,
        dataset_role=DatasetRole.DEVELOPMENT_VALIDATION,
        schedule_seed=SCHEDULE_SEED,
        schedule_order=order,
        schedule_row_id=row["schedule_row_id"],
        repetition=row["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id=_run_id(candidate, order),
        provider="openai",
        model_id=MODEL_ID,
        memory_condition=MemoryCondition.NO_MEMORY,
        memory_policy_version=FIXED_BUNDLE_POLICY_VERSION,
        sandbox_backend="docker",
        budget=RUNTIME_BUDGET,
        agent_image_digest=binding["evaluator_image_digest"],
        evaluator_image_digest=binding["evaluator_image_digest"],
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        cache_write_input_price_per_million_usd=0.75,
        output_price_per_million_usd=4.5,
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        experiment_context=experiment,
    )
    payload = manifest.model_dump(mode="python")
    payload["model"]["temperature"] = 0.0
    payload["tool_schema_version"] = row["tool_schema_version"]
    payload["context_policy_version"] = row["context_policy_version"]
    payload["created_at"] = MANIFEST_CREATED_AT
    return RunManifest.model_validate(payload)


def build_rapid_v13_run_manifest(
    candidate: dict[str, Any],
    order: int,
    *,
    repository: str | Path = ".",
) -> RunManifest:
    _validate_candidate(candidate)
    return _build_manifest_unchecked(candidate, order, repository=repository)


def _manifest_matches_projection(
    projection: dict[str, Any],
    manifest: RunManifest,
) -> bool:
    try:
        experiment = manifest.experiment
        assert experiment is not None
        row = next(
            item
            for item in projection["schedule"]
            if item["schedule_row_id"] == experiment.schedule_row_id
        )
        binding = projection["task_bindings"][0]
        model = projection["model_contract"]
        cost = projection["campaign_cost_control"]
        return bool(
            experiment.purpose == ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT
            and experiment.experiment_id == EXPERIMENT_ID
            and experiment.suite_hash == projection["suite_hash"]
            and experiment.execution_hash == projection["execution_hash"]
            and experiment.campaign_cost_control_hash == cost["content_hash"]
            and experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
            and experiment.schedule_seed == SCHEDULE_SEED
            and experiment.schedule_order == row["order"]
            and experiment.repetition == row["repetition"]
            and manifest.run_id == _run_id(projection, row["order"])
            and manifest.task_id == row["task_id"] == binding["task_id"] == TASK_ID
            and manifest.task_version
            == row["task_version"]
            == binding["task_version"]
            == TASK_VERSION
            and manifest.tool_schema_version == row["tool_schema_version"]
            and manifest.context_policy_version == row["context_policy_version"]
            and manifest.memory.condition == MemoryCondition.NO_MEMORY
            and manifest.memory.index_version is None
            and manifest.memory.index_hash is None
            and manifest.budget == RUNTIME_BUDGET
            and manifest.model.provider == model["provider"]
            and manifest.model.model_id == model["model_id"]
            and manifest.model.provider_sdk_version == model["provider_sdk_version"]
            and manifest.model.reasoning_effort == model["reasoning_effort"]
            and manifest.model.reasoning_mode == model["reasoning_mode"]
            and manifest.model.service_tier == model["service_tier"]
            and manifest.model.transport_max_retries == model["transport_max_retries"]
            and manifest.model.temperature == model["temperature"]
            and manifest.model.max_output_tokens == model["max_output_tokens"]
            and manifest.sandbox_backend == "docker"
            and manifest.evaluator_image_digest == binding["evaluator_image_digest"]
            and manifest.agent_image_digest == binding["evaluator_image_digest"]
            and manifest.public_spec_hash == binding["public_spec_hash"]
            and manifest.private_spec_hash == binding["private_spec_hash"]
            and manifest.base_commit == binding["base_commit"]
        )
    except (AssertionError, KeyError, StopIteration, TypeError, ValueError):
        return False


def _candidate_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "suite_hash": candidate["config_semantic_hash"],
        "execution_hash": candidate["execution_hash"],
        "model_contract": candidate["model_contract"],
        "task_bindings": candidate["task_bindings"],
        "schedule": candidate["schedule"],
        "campaign_cost_control": {"content_hash": candidate["cost_control_hash"]},
    }


def _manifest_matches_candidate(candidate: dict[str, Any], manifest: RunManifest) -> bool:
    return _manifest_matches_projection(_candidate_projection(candidate), manifest)


def rapid_v13_registered_plan_matches_manifest(
    *,
    plan: dict[str, Any],
    manifest: RunManifest,
    repository: str | Path = ".",
) -> bool:
    del repository
    return _manifest_matches_projection(plan, manifest)


def _prepare_batch(
    candidate: dict[str, Any],
    *,
    authority_kind: Literal["live", "rehearsal"],
    live_authorization: LiveExecutionAuthorization | None = None,
    repository: str | Path = ".",
) -> PreparedRapidV13Batch:
    _validate_candidate(candidate)
    root = Path(repository).resolve()
    plan = _plan(candidate, approved=True)
    plan_hash = sha256_bytes(_plan_bytes(plan))
    registry = live_verifier_registry()
    plan_decision = registry.validate_authorization_plan(plan)
    if not (
        plan_decision.handled
        and plan_decision.accepted
        and plan_decision.verifier_id == VERIFIER_ID
        and plan_decision.requires_row_capability
    ):
        raise HarnessAdmissionError("Rapid candidate-v17 plan schema is not registered")
    manifests = tuple(
        _build_manifest_unchecked(candidate, order, repository=root)
        for order in range(1, len(candidate["schedule"]) + 1)
    )
    for manifest in manifests:
        decision = registry.verify_manifest(
            plan=plan,
            manifest=manifest,
            authorization_plan_path=(
                live_authorization.plan_path if live_authorization is not None else "<rehearsal>"
            ),
            authorization_plan_hash=plan_hash,
            repository=root,
            runner_root=None,
            batch_validation=True,
        )
        if not decision.accepted or decision.verifier_id != VERIFIER_ID:
            raise HarnessAdmissionError(
                "Rapid candidate-v17 manifest is incompatible with its verifier"
            )
    authorization = issue_batch_execution_authorization(
        authority_kind=authority_kind,
        execution_hash=candidate["execution_hash"],
        plan_hash=plan_hash,
        runtime_build_hash=candidate["runtime_build_hash"],
        schedule_hash=candidate["schedule_hash"],
        cost_control_hash=candidate["cost_control_hash"],
        manifests=manifests,
        live_authorization=live_authorization,
    )
    return PreparedRapidV13Batch(
        plan=plan,
        plan_hash=plan_hash,
        manifests=manifests,
        authorization=authorization,
        verifier_id=VERIFIER_ID,
    )


def _result_bundle_path(candidate: dict[str, Any], root: Path) -> Path:
    return (
        root
        / "reports"
        / "rapid-development"
        / f"{EXPERIMENT_ID}-{candidate['execution_hash'][7:19]}.jsonl"
    )


def _batch_started_event(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA,
        "event": "batch-started",
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "candidate_content_hash": candidate["content_hash"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "schedule_hash": candidate["schedule_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "verifier_entry_hash": _verifier_entry_hash(),
        "full_schedule_reserve_nanos": FULL_SCHEDULE_RESERVE_NANOS,
        "hard_cap_nanos": HARD_CAP_NANOS,
    }


def _rehearsed_resolved_terminal(
    candidate: dict[str, Any],
    previous: str,
) -> dict[str, Any]:
    row = candidate["schedule"][0]
    return _seal_event(
        {
            "schema_version": RESULT_SCHEMA,
            "event": "row-terminal",
            **row,
            "run_id": _run_id(candidate, 1),
            "agent_started": True,
            "harness_admission_failure": False,
            "evaluator_reached": True,
            "token_terminal": False,
            "submission_completed": True,
            "success_at_budget": True,
            "outcome_kind": RunOutcomeKind.RESOLVED.value,
            "usage": Usage().model_dump(mode="json"),
            "model_cost_nanos": 0,
            "runtime_result_official": True,
            "bundle_official": False,
            "error_type": None,
            "error_code": None,
            "error_message": None,
        },
        previous,
    )


def _active_bundle_next_order_from_events(
    candidate: dict[str, Any],
    events: list[dict[str, Any]],
) -> int | None:
    if not events:
        return None
    previous: str | None = None
    for event in events:
        if type(event) is not dict or type(event.get("content_hash")) is not str:
            return None
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if body.get("previous_event_hash") != previous or event["content_hash"] != sha256_json(
            body
        ):
            return None
        previous = event["content_hash"]
    expected_start = {**_batch_started_event(candidate), "previous_event_hash": None}
    first_body = {key: value for key, value in events[0].items() if key != "content_hash"}
    if first_body != expected_start or len(events) > len(candidate["schedule"]):
        return None
    for index, event in enumerate(events[1:]):
        schedule_row = candidate["schedule"][index]
        if (
            event.get("schema_version") != RESULT_SCHEMA
            or event.get("event") != "row-terminal"
            or event.get("bundle_official") is not False
            or type(event.get("runtime_result_official")) is not bool
            or event.get("run_id") != _run_id(candidate, schedule_row["order"])
            or event.get("harness_admission_failure") is not False
            or event.get("outcome_kind")
            not in {
                RunOutcomeKind.RESOLVED.value,
                RunOutcomeKind.TASK_FAILURE.value,
                RunOutcomeKind.AGENT_FAILURE.value,
            }
            or any(event.get(key) != value for key, value in schedule_row.items())
        ):
            return None
    return len(events)


def _active_bundle_next_order(candidate: dict[str, Any], root: Path) -> int | None:
    path = _result_bundle_path(candidate, root)
    if path.is_symlink() or not path.is_file():
        return None
    try:
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, TypeError, ValueError):
        return None
    return _active_bundle_next_order_from_events(candidate, events)


def _write_or_validate_plan(candidate: dict[str, Any], root: Path) -> Path:
    plan = _plan(candidate, approved=True)
    raw = _plan_bytes(plan)
    path = (
        root
        / ".patchloop"
        / "experiments"
        / "plans"
        / f"{candidate['execution_hash'].removeprefix('sha256:')}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ContractError(
                "Rapid candidate-v17 approved plan path contains different bytes"
            ) from None
    return path


def rehearsal_bytes(receipt: dict[str, Any]) -> bytes:
    body = {key: value for key, value in receipt.items() if key != "content_hash"}
    if receipt.get("content_hash") != sha256_json(body):
        raise RecoveryError("Rapid candidate-v17 rehearsal content hash differs")
    return (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _rehearsal_body(
    candidate: dict[str, Any],
    prepared: PreparedRapidV13Batch,
    first_boundary: dict[str, Any],
    transition: dict[str, Any],
    second_boundary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REHEARSAL_SCHEMA,
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "candidate_content_hash": candidate["content_hash"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "config_file_sha256": candidate["config_file_sha256"],
        "schedule_hash": candidate["schedule_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "plan_hash": prepared.plan_hash,
        "plan_schema": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "verifier_id": prepared.verifier_id,
        "verifier_entry_hash": _verifier_entry_hash(),
        "verified_manifest_count": len(prepared.manifests),
        "stage_sequence": list(_REHEARSAL_STAGE_SEQUENCE),
        "first_provider_boundary": first_boundary,
        "inter_row_transition": transition,
        "second_provider_boundary": second_boundary,
        "stopped_before": "second-provider-dispatch-after-resolved-prefix",
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "task_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "harness_admission_failures": 0,
    }


def build_rapid_public_development_v13_rehearsal(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    candidate = load_rapid_public_development_v13_candidate(root)
    prepared = _prepare_batch(candidate, authority_kind="rehearsal", repository=root)
    start = _seal_event(_batch_started_event(candidate), None)
    first_order = _active_bundle_next_order_from_events(candidate, [start])
    if first_order != 1:
        raise HarnessAdmissionError("Rapid candidate-v17 rehearsal prefix is incompatible")
    first = prepared.manifests[0]
    first_authorization = issue_row_execution_authorization(
        prepared.authorization,
        first,
        active_schedule_order=first_order,
    )
    first_boundary = AgentRunner.rehearse_provider_dispatch(first, first_authorization)
    first_terminal = _rehearsed_resolved_terminal(candidate, start["content_hash"])
    second_order = _active_bundle_next_order_from_events(candidate, [start, first_terminal])
    if second_order != 2:
        raise HarnessAdmissionError(
            "Rapid candidate-v17 rehearsal inter-row prefix is incompatible"
        )
    second = prepared.manifests[1]
    second_authorization = issue_row_execution_authorization(
        prepared.authorization,
        second,
        active_schedule_order=second_order,
    )
    second_boundary = AgentRunner.rehearse_provider_dispatch(second, second_authorization)
    transition = {
        "prior_terminal_content_hash": first_terminal["content_hash"],
        "prior_outcome_kind": first_terminal["outcome_kind"],
        "prior_runtime_result_official": first_terminal["runtime_result_official"],
        "prior_bundle_official": first_terminal["bundle_official"],
        "next_schedule_order": second_order,
    }
    body = _rehearsal_body(candidate, prepared, first_boundary, transition, second_boundary)
    return {**body, "content_hash": sha256_json(body)}


def rehearse_rapid_public_development_v13(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    candidate = load_rapid_public_development_v13_candidate(root)
    receipt = build_rapid_public_development_v13_rehearsal(
        config_path=config_path,
        repository=root,
    )
    output = ensure_within(root, REHEARSAL_PATH.as_posix())
    if output.exists():
        existing = load_rapid_public_development_v13_rehearsal(candidate, repository=root)
        if existing != receipt:
            raise RecoveryError("Rapid candidate-v17 rehearsal differs from current contracts")
        return existing
    _write_once(output, rehearsal_bytes(receipt))
    return load_rapid_public_development_v13_rehearsal(candidate, repository=root)


def load_rapid_public_development_v13_rehearsal(
    candidate: dict[str, Any],
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    path = ensure_within(root, REHEARSAL_PATH.as_posix())
    if path.is_symlink() or not path.is_file():
        raise HarnessAdmissionError(
            "Rapid candidate-v17 requires its exact no-call rehearsal receipt"
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessAdmissionError("Rapid candidate-v17 rehearsal is invalid") from exc
    if type(receipt) is not dict:
        raise HarnessAdmissionError("Rapid candidate-v17 rehearsal must be an object")
    plan = _plan(candidate, approved=True)
    first_boundary = receipt.get("first_provider_boundary")
    transition = receipt.get("inter_row_transition")
    second_boundary = receipt.get("second_provider_boundary")
    start = _seal_event(_batch_started_event(candidate), None)
    first_terminal = _rehearsed_resolved_terminal(candidate, start["content_hash"])
    expected_transition = {
        "prior_terminal_content_hash": first_terminal["content_hash"],
        "prior_outcome_kind": RunOutcomeKind.RESOLVED.value,
        "prior_runtime_result_official": True,
        "prior_bundle_official": False,
        "next_schedule_order": 2,
    }
    expected = {
        "schema_version": REHEARSAL_SCHEMA,
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "candidate_content_hash": candidate["content_hash"],
        "runtime_build_hash": candidate["runtime_build_hash"],
        "config_file_sha256": candidate["config_file_sha256"],
        "schedule_hash": candidate["schedule_hash"],
        "cost_control_hash": candidate["cost_control_hash"],
        "plan_hash": sha256_bytes(_plan_bytes(plan)),
        "plan_schema": PLAN_SCHEMA,
        "plan_kind": PLAN_KIND,
        "verifier_id": VERIFIER_ID,
        "verifier_entry_hash": _verifier_entry_hash(),
        "verified_manifest_count": 6,
        "stage_sequence": list(_REHEARSAL_STAGE_SEQUENCE),
        "stopped_before": "second-provider-dispatch-after-resolved-prefix",
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "task_calls_made": 0,
        "evaluator_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "harness_admission_failures": 0,
    }
    body = {key: value for key, value in receipt.items() if key != "content_hash"}
    valid_first = bool(
        isinstance(first_boundary, dict)
        and first_boundary.get("stage") == "provider-dispatch-boundary"
        and first_boundary.get("provider_dispatch_blocked") is True
        and first_boundary.get("execution_hash") == candidate["execution_hash"]
        and first_boundary.get("schedule_order") == 1
        and first_boundary.get("schedule_row_id") == candidate["schedule"][0]["schedule_row_id"]
        and first_boundary.get("run_id") == _run_id(candidate, 1)
    )
    valid_second = bool(
        isinstance(second_boundary, dict)
        and second_boundary.get("stage") == "provider-dispatch-boundary"
        and second_boundary.get("provider_dispatch_blocked") is True
        and second_boundary.get("execution_hash") == candidate["execution_hash"]
        and second_boundary.get("schedule_order") == 2
        and second_boundary.get("schedule_row_id") == candidate["schedule"][1]["schedule_row_id"]
        and second_boundary.get("run_id") == _run_id(candidate, 2)
    )
    comparable = {
        key: value
        for key, value in body.items()
        if key
        not in {
            "first_provider_boundary",
            "inter_row_transition",
            "second_provider_boundary",
        }
    }
    if (
        not valid_first
        or transition != expected_transition
        or not valid_second
        or comparable != expected
        or receipt.get("content_hash") != sha256_json(body)
        or rehearsal_bytes(receipt) != path.read_bytes()
    ):
        raise HarnessAdmissionError("Rapid candidate-v17 rehearsal does not bind current contracts")
    return receipt


def run_rapid_public_development_v13(
    config_path: str | Path = CONFIG_PATH,
    *,
    approve_live_cost: bool,
    approved_execution_hash: str | None,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Run the AnyIO successor only after exact hash-and-cap approval."""

    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    candidate = load_rapid_public_development_v13_candidate(root)
    bundle_path = _result_bundle_path(candidate, root)
    if bundle_path.exists() or bundle_path.is_symlink():
        raise ContractError("Rapid candidate-v17 result already exists and cannot be retried")
    if not approve_live_cost or approved_execution_hash != candidate["execution_hash"]:
        raise ContractError(
            "Rapid candidate-v17 live execution requires its exact hash and cost-cap approval"
        )
    load_rapid_public_development_v13_rehearsal(candidate, repository=root)
    _write_or_validate_plan(candidate, root)
    live_authorization = issue_live_execution_authorization(
        candidate["execution_hash"], root=root / ".patchloop"
    )
    prepared = _prepare_batch(
        candidate,
        authority_kind="live",
        live_authorization=live_authorization,
        repository=root,
    )
    if not os.environ.get("OPENAI_API_KEY"):
        raise ContractError("Rapid candidate-v17 live execution requires OPENAI_API_KEY")
    if not DockerSandbox.available():
        raise ContractError("Rapid candidate-v17 requires the local Docker daemon")
    binding = candidate["task_bindings"][0]
    if (
        DockerSandbox(binding["evaluator_image"]).image_identity()
        != binding["evaluator_image_digest"]
    ):
        raise ContractError("Rapid candidate-v17 AnyIO image is unavailable")

    _append_bundle_event(bundle_path, _batch_started_event(candidate), create=True)
    runner = AgentRunner(root / ".patchloop")
    rows: list[dict[str, Any]] = []
    accrued_nanos = 0
    halted_reason: str | None = None
    for schedule_row, manifest in zip(candidate["schedule"], prepared.manifests, strict=True):
        if halted_reason is not None:
            _append_bundle_event(
                bundle_path,
                {
                    "schema_version": RESULT_SCHEMA,
                    "event": "row-not-started",
                    "official": False,
                    **schedule_row,
                    "reason": halted_reason,
                },
            )
            continue
        result: dict[str, Any] | None = None
        error: Exception | None = None
        try:
            active_order = _active_bundle_next_order(candidate, root)
            if active_order != schedule_row["order"]:
                raise HarnessAdmissionError("Rapid candidate-v17 active bundle row order differs")
            row_authorization = issue_row_execution_authorization(
                prepared.authorization,
                manifest,
                active_schedule_order=active_order,
            )
            result = runner.start(
                schedule_row["task"],
                model="openai",
                memory_condition=MemoryCondition.NO_MEMORY,
                manifest=manifest,
                live_authorization=live_authorization,
                row_execution_authorization=row_authorization,
            )
        except Exception as exc:  # terminal projection preserves the exact failure
            error = exc
            result = _persisted_result(runner, manifest.run_id)
        projected = _rapid_v4_row_projection(
            schedule_row=schedule_row,
            manifest=manifest,
            result=result,
            runner=runner,
            error=error,
        )
        accrued_nanos += projected["model_cost_nanos"]
        if accrued_nanos > HARD_CAP_NANOS:
            raise ContractError("Rapid candidate-v17 observed cost exceeds the approved hard cap")
        _append_bundle_event(
            bundle_path,
            {"schema_version": RESULT_SCHEMA, "event": "row-terminal", **projected},
        )
        rows.append(projected)
        if projected["harness_admission_failure"]:
            halted_reason = "prior-harness-admission-failure"
        elif projected["outcome_kind"] == RunOutcomeKind.INFRASTRUCTURE_ERROR.value:
            halted_reason = "prior-infrastructure-terminal"

    agent_rows_started = sum(bool(row["agent_started"]) for row in rows)
    agent_failures = sum(row["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value for row in rows)
    harness_failures = sum(bool(row["harness_admission_failure"]) for row in rows)
    summary = {
        "schema_version": RESULT_SCHEMA,
        "event": "batch-completed",
        "official": False,
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": candidate["execution_hash"],
        "attempted_rows": len(rows),
        "started_rows": agent_rows_started,
        "agent_rows_started": agent_rows_started,
        "harness_admission_failures": harness_failures,
        "agent_failures": agent_failures,
        "agent_failure_rate": (agent_failures / agent_rows_started if agent_rows_started else None),
        "evaluator_reached": sum(row["evaluator_reached"] for row in rows),
        "token_terminals": sum(row["token_terminal"] for row in rows),
        "submissions_completed": sum(row["submission_completed"] for row in rows),
        "successes_at_budget": sum(row["success_at_budget"] for row in rows),
        "model_calls": sum(row["usage"]["model_calls"] for row in rows),
        "tool_calls": sum(row["usage"]["tool_calls"] for row in rows),
        "model_cost_nanos": accrued_nanos,
        "result_bundle": bundle_path.relative_to(root).as_posix(),
        "external_claim_authorized": False,
        "confirmatory_promotion_automatic": False,
    }
    return _append_bundle_event(bundle_path, summary)


__all__ = [
    "CANDIDATE_PATH",
    "CONFIG_PATH",
    "EXPERIMENT_ID",
    "REHEARSAL_PATH",
    "build_rapid_public_development_v13_candidate",
    "build_rapid_public_development_v13_rehearsal",
    "build_rapid_v13_run_manifest",
    "load_consumed_rapid_public_development_v13_candidate",
    "load_rapid_public_development_v13_candidate",
    "load_rapid_public_development_v13_rehearsal",
    "materialize_rapid_public_development_v13_candidate",
    "rapid_v13_registered_plan_matches_manifest",
    "rehearse_rapid_public_development_v13",
    "run_rapid_public_development_v13",
]
