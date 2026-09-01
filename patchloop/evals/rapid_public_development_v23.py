"""Candidate-v28 Rapid V22/V24 comparison under the qualified driver.

R20 keeps AnyIO-v5, model, budget, evaluator, schedule shape and the
append-only row-settlement driver fixed.  It compares the last exercised
workflow predecessor (Lean V22) with the offline-qualified Lean V24 package.
Candidate construction and rehearsal stop before every external seam.
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

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.runner import (
    AgentRunner,
    BatchExecutionAuthorization,
    LiveExecutionAuthorization,
    issue_batch_execution_authorization,
    issue_live_execution_authorization,
    issue_row_execution_authorization,
    row_execution_authorization_receipt,
)
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
)
from patchloop.errors import ContractError, HarnessAdmissionError, RecoveryError
from patchloop.evals.live_verifier_registry import live_verifier_registry
from patchloop.evals.rapid_batch_driver import (
    RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
    RAPID_BATCH_DRIVER_EVENT_SCHEMA,
    RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
    build_rapid_batch_driver_terminal_parity_contract,
    run_append_only_rapid_batch_driver,
)
from patchloop.evals.rapid_public_development import (
    MODEL_ID,
    RUNTIME_BUDGET,
    _UniqueKeyLoader,
    _within,
)
from patchloop.evals.rapid_public_development_v2 import _write_once
from patchloop.evals.rapid_public_development_v4 import (
    _rapid_v4_row_projection,
    _runtime_build_binding,
)
from patchloop.evals.rapid_public_development_v19 import (
    FULL_SCHEDULE_RESERVE_NANOS,
    HARD_CAP_NANOS,
    PER_RUN_RESERVE_NANOS,
    TASK_ID,
    TASK_PATH,
    TASK_VERSION,
    RapidAnyioCostPolicy,
    _file_binding,
    _task_binding,
)
from patchloop.evals.rapid_public_development_v22 import (
    V22_ACTIVATION_REVIEW_BYTES,
    V22_ACTIVATION_REVIEW_CONTENT_HASH,
    V22_ACTIVATION_REVIEW_FILE_SHA256,
    V22_ACTIVATION_REVIEW_PATH,
    V22_QUALIFICATION_BYTES,
    V22_QUALIFICATION_CONTENT_HASH,
    V22_QUALIFICATION_FILE_SHA256,
    V22_QUALIFICATION_PATH,
    _stable_json,
)
from patchloop.evals.rapid_public_development_v22 import (
    VARIANT_CONTRACTS as PREDECESSOR_VARIANT_CONTRACTS,
)
from patchloop.evals.rapid_terminal_state_parity_qualification import (
    QUALIFICATION_PATH as DRIVER_QUALIFICATION_PATH,
)
from patchloop.memory.fixed_bundle import FIXED_BUNDLE_POLICY_VERSION
from patchloop.runtime import build_manifest
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "rapid-public-development-anyio-v5-self-directed-bounded-ab-v1"
EXPERIMENT_ID = "rapid-public-dev-anyio-v5-self-directed-bounded-ab-20260830-r20"
SCHEDULE_SEED = 20260830
CONFIG_PATH = Path(
    "experiments/rapid-public-development-anyio-v5-self-directed-bounded-ab-20260830-r20.yaml"
)
CANDIDATE_SCHEMA = "rapid-public-development-candidate-v28"
CANDIDATE_REVISION = 28
CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-self-directed-bounded-ab-20260830-r20-"
    "candidate-v28.json"
)
REHEARSAL_SCHEMA = "rapid-public-development-rehearsal-v25"
REHEARSAL_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-self-directed-bounded-ab-20260830-r20-"
    "candidate-v28-rehearsal-v25.json"
)
PLAN_SCHEMA = "experiment-execution-plan-v28"
PLAN_KIND = "rapid-public-development-batch-v1"
RUNTIME_BUILD_SCHEMA = "rapid-runtime-build-v1"
VERIFIER_ID = "rapid-r20-candidate-v28-plan-v28"
RUN_ID_PREFIX = "run_rapid_v28"
MANIFEST_CREATED_AT = datetime(2026, 8, 30, tzinfo=UTC)

PREDECESSOR_CANDIDATE_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-v5-plan-feedback-ab-20260828-r19-candidate-v27.json"
)
PREDECESSOR_CANDIDATE_BYTES = 17_175
PREDECESSOR_CANDIDATE_FILE_SHA256 = (
    "sha256:7a90060d43cb401c2b8750a767883c4433b505c8af8428990b7d8254b65b61e0"
)
PREDECESSOR_CANDIDATE_CONTENT_HASH = (
    "sha256:05195747ca32ca63bf1fede1fa73438b8dfcd217e5cee6f651d4a68985e3774e"
)
PREDECESSOR_EXECUTION_HASH = (
    "sha256:ed5c319756ed2b093bd4deba23c10fa0dfed2f30b1bdc6451ce58ccee5d066cd"
)
PREDECESSOR_RESULT_PATH = Path(
    "reports/rapid-development/"
    "rapid-public-dev-anyio-v5-plan-feedback-ab-20260828-r19-ed5c319756ed.jsonl"
)
PREDECESSOR_RESULT_BYTES = 44_890
PREDECESSOR_RESULT_FILE_SHA256 = (
    "sha256:8647dfdfcc44ba479bcf36304b543778bf3fd2c8c818c1c705fa6a553e7a939c"
)
PREDECESSOR_RESULT_FINAL_HASH = (
    "sha256:5ace0dddfa211e711c40584311f5e1a13fb0ac0283dbe41679c5938c1871446d"
)

DRIVER_QUALIFICATION_BYTES = 3_920
DRIVER_QUALIFICATION_FILE_SHA256 = (
    "sha256:d992159b613c9de86c1c1319eceaac29b54a5ad2adee0d94562e8df6f21de0d6"
)
DRIVER_QUALIFICATION_CONTENT_HASH = (
    "sha256:c316e23c0a295f6c4e5b913104e1db6e6c2f15055b4348b60822527399bc53bd"
)

V24_QUALIFICATION_PATH = Path(
    "experiments/lean-harness-bounded-request-context-public-qualification-20260829-v1.json"
)
V24_QUALIFICATION_BYTES = 5_482
V24_QUALIFICATION_FILE_SHA256 = (
    "sha256:818d9ce5842a4bad5ad318b87d65aca6018dfc97dc84dc0d61eb9a9c57acf2e6"
)
V24_QUALIFICATION_CONTENT_HASH = (
    "sha256:581b7485abab5941cbf71d8def52d5ee9a1e504b539df16b838b9f2a180b99bd"
)
V24_ACTIVATION_REVIEW_PATH = Path(
    "experiments/lean-harness-bounded-request-context-activation-review-20260829-v1.json"
)
V24_ACTIVATION_REVIEW_BYTES = 6_110
V24_ACTIVATION_REVIEW_FILE_SHA256 = (
    "sha256:18d4d769f486f053e1a71681111de20d2186b092245e8f7001bd51b055b1cf59"
)
V24_ACTIVATION_REVIEW_CONTENT_HASH = (
    "sha256:8959a06ecf95fcd4b0701c77e93aa67d62648e02e09761e129effb5539498423"
)

V24_RUNTIME_IDENTITY = {
    "context_policy_version": "phase-evidence-v34",
    "request_evidence_schema": "lean-harness-request-evidence-v24",
    "runtime_policy_version": "lean-harness-v24",
    "tool_schema_version": "v26",
}

VARIANTS = ("lean-harness-v22", "lean-harness-v24")
VARIANT_CONTRACTS = {
    "lean-harness-v22": PREDECESSOR_VARIANT_CONTRACTS["lean-harness-v22"],
    "lean-harness-v24": {
        **PREDECESSOR_VARIANT_CONTRACTS["lean-harness-v22"],
        "tool_schema_version": "v26",
        "context_policy_version": "phase-evidence-v34",
        "runtime_policy_version": "lean-harness-v24",
        "request_evidence_schema": "lean-harness-request-evidence-v24",
        "self_directed_exploration_policy_version": ("bounded-self-directed-exploration-v1"),
        "exact_pre_plan_surface_policy_version": ("exact-self-directed-pre-plan-surface-v1"),
        "bounded_request_context_policy_version": (
            "bounded-public-investigation-request-context-v1"
        ),
    },
}
EXPECTED_SCHEDULE = (
    (1, "lean-harness-v22", 1),
    (2, "lean-harness-v24", 1),
    (3, "lean-harness-v24", 2),
    (4, "lean-harness-v22", 2),
    (5, "lean-harness-v22", 3),
    (6, "lean-harness-v24", 3),
)

_REHEARSAL_STAGE_SEQUENCE = (
    "candidate-current-binding",
    "registered-plan-schema",
    "all-row-manifests",
    "batch-capability",
    "terminal-parity-driver-binding",
    "first-row-capability",
    "first-provider-dispatch-boundary",
    "settled-ordinary-terminal-projection",
    "persisted-ordinary-continue-decision-projection",
    "second-row-capability",
    "second-provider-dispatch-boundary",
)


class RapidAnyioScheduleRowV23(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: int = Field(ge=1, le=6)
    task: Literal[TASK_PATH]
    variant: Literal["lean-harness-v22", "lean-harness-v24"]
    repetition: int = Field(ge=1, le=3)

    @field_validator("order", "repetition", mode="before")
    @classmethod
    def exact_int(cls, value: Any) -> Any:
        if type(value) is not int:
            raise ValueError("Rapid R20 schedule counters must be exact integers")
        return value


class RapidAnyioV22V24ABConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["rapid-public-development-anyio-v5-self-directed-bounded-ab-v1"]
    experiment_id: Literal["rapid-public-dev-anyio-v5-self-directed-bounded-ab-20260830-r20"]
    status: Literal["development-only"]
    official: Literal[False]
    selection_policy_version: Literal[
        "qualified-public-v22-v24-anyio-v5-self-directed-bounded-ab-v1"
    ]
    public_development_history_only: Literal[True]
    heldout_outcomes_used: Literal[False]
    private_evidence_used: Literal[False]
    frozen_dataset_modified: Literal[False]
    task_successor_opt_in: Literal[True]
    tasks: tuple[str, ...]
    variants: tuple[Literal["lean-harness-v22"], Literal["lean-harness-v24"]]
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
    schedule: tuple[RapidAnyioScheduleRowV23, ...] = Field(min_length=6, max_length=6)
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
                raise ValueError(f"Rapid R20 {field} must be a YAML sequence")
            frozen[field] = tuple(sequence)
        return frozen

    @model_validator(mode="after")
    def validate_design(self) -> Self:
        if self.tasks != (TASK_PATH,) or self.variants != VARIANTS:
            raise ValueError("Rapid R20 task or variant panel differs")
        if self.budget != RUNTIME_BUDGET:
            raise ValueError("Rapid R20 runtime budget differs")
        if self.metrics != (
            "evaluator_reached",
            "token_terminal",
            "submission_completed",
            "success_at_budget",
            "model_calls",
            "tool_calls",
            "model_cost_nanos",
        ):
            raise ValueError("Rapid R20 metric set differs")
        actual = tuple((row.order, row.variant, row.repetition) for row in self.schedule)
        if actual != EXPECTED_SCHEDULE:
            raise ValueError("Rapid R20 schedule is not the fixed balanced matrix")
        return self


@dataclass(frozen=True)
class PreparedRapidV23Batch:
    plan: dict[str, Any]
    plan_hash: str
    manifests: tuple[RunManifest, ...]
    authorization: BatchExecutionAuthorization
    verifier_id: str


def _verifier_entry_hash() -> str:
    return live_verifier_registry().descriptor_hash_for(
        experiment_id=EXPERIMENT_ID,
        plan_schema=PLAN_SCHEMA,
        plan_kind=PLAN_KIND,
    )


def _read_config(
    path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> tuple[RapidAnyioV22V24ABConfig, bytes, Path]:
    root = Path(repository).resolve()
    selected = _within(root, path)
    if selected.relative_to(root).as_posix() != CONFIG_PATH.as_posix():
        raise ContractError("Rapid R20 requires its canonical config path")
    if selected.is_symlink() or not selected.is_file():
        raise ContractError("Rapid R20 config must be a regular repository file")
    raw = selected.read_bytes()
    try:
        payload = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
        config = RapidAnyioV22V24ABConfig.model_validate(payload)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        raise ContractError("Rapid R20 config is invalid") from exc
    return config, raw, selected


def _result_identity(root: Path) -> dict[str, Any]:
    selected = ensure_within(root, PREDECESSOR_RESULT_PATH.as_posix())
    raw = selected.read_bytes()
    if len(raw) != PREDECESSOR_RESULT_BYTES or sha256_bytes(raw) != (
        PREDECESSOR_RESULT_FILE_SHA256
    ):
        raise RecoveryError("Consumed Rapid R19 result identity differs")
    try:
        events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("Consumed Rapid R19 result is invalid") from exc
    previous: str | None = None
    for event in events:
        if type(event) is not dict:
            raise RecoveryError("Consumed Rapid R19 result event differs")
        body = {key: value for key, value in event.items() if key != "content_hash"}
        if event.get("previous_event_hash") != previous or event.get("content_hash") != sha256_json(
            body
        ):
            raise RecoveryError("Consumed Rapid R19 result chain differs")
        previous = event["content_hash"]
    final = events[-1] if events else None
    if not (
        isinstance(final, dict)
        and final.get("content_hash") == PREDECESSOR_RESULT_FINAL_HASH
        and final.get("execution_hash") == PREDECESSOR_EXECUTION_HASH
        and final.get("official") is False
        and final.get("event") == "batch-completed"
        and final.get("driver_policy_version") == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
        and final.get("reason_codes") == ["SCHEDULE_EXHAUSTED_AFTER_SETTLED_TERMINAL"]
        and final.get("terminal_row_count") == 6
        and final.get("not_started_row_count") == 0
        and final.get("accrued_cost_nanos") == 3_068_239_500
        and final.get("cost_fully_settled") is True
    ):
        raise RecoveryError("Consumed Rapid R19 terminal differs")
    return {
        "path": PREDECESSOR_RESULT_PATH.as_posix(),
        "file_bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "final_event_content_hash": final["content_hash"],
        "execution_hash": final["execution_hash"],
        "event": final["event"],
        "reason_codes": final["reason_codes"],
        "terminal_row_count": final["terminal_row_count"],
        "not_started_row_count": final["not_started_row_count"],
        "accrued_cost_nanos": final["accrued_cost_nanos"],
    }


def _validated_v22_evidence(root: Path) -> dict[str, Any]:
    qualification, qualification_raw = _stable_json(
        root, V22_QUALIFICATION_PATH, "Lean V22 qualification"
    )
    review, review_raw = _stable_json(
        root, V22_ACTIVATION_REVIEW_PATH, "Lean V22 activation review"
    )
    if not (
        len(qualification_raw) == V22_QUALIFICATION_BYTES
        and sha256_bytes(qualification_raw) == V22_QUALIFICATION_FILE_SHA256
        and qualification.get("content_hash") == V22_QUALIFICATION_CONTENT_HASH
        and qualification.get("status") == "offline-qualified"
        and qualification.get("paid_execution_authorized") is False
        and len(review_raw) == V22_ACTIVATION_REVIEW_BYTES
        and sha256_bytes(review_raw) == V22_ACTIVATION_REVIEW_FILE_SHA256
        and review.get("content_hash") == V22_ACTIVATION_REVIEW_CONTENT_HASH
        and review.get("status") == "candidate-preparation-ready"
        and review.get("decision", {}).get("candidate_preparation_ready") is True
        and review.get("paid_execution_authorized") is False
    ):
        raise RecoveryError("Lean V22 evidence binding differs")
    return {
        "qualification": {
            "path": V22_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(qualification_raw),
            "file_sha256": sha256_bytes(qualification_raw),
            "content_hash": qualification["content_hash"],
        },
        "activation_review": {
            "path": V22_ACTIVATION_REVIEW_PATH.as_posix(),
            "file_bytes": len(review_raw),
            "file_sha256": sha256_bytes(review_raw),
            "content_hash": review["content_hash"],
            "candidate_preparation_ready": True,
        },
    }


def _validated_v24_evidence(root: Path) -> dict[str, Any]:
    qualification, qualification_raw = _stable_json(
        root, V24_QUALIFICATION_PATH, "Lean V24 qualification"
    )
    review, review_raw = _stable_json(
        root, V24_ACTIVATION_REVIEW_PATH, "Lean V24 activation review"
    )
    if not (
        len(qualification_raw) == V24_QUALIFICATION_BYTES
        and sha256_bytes(qualification_raw) == V24_QUALIFICATION_FILE_SHA256
        and qualification.get("content_hash") == V24_QUALIFICATION_CONTENT_HASH
        and qualification.get("schema_version")
        == "lean-bounded-request-context-successor-qualification-v1"
        and qualification.get("status") == "offline-qualified"
        and qualification.get("candidate_created") is False
        and qualification.get("external_calls") == 0
        and qualification.get("scenarios", {}).get("runtime_identity")
        == {
            **V24_RUNTIME_IDENTITY,
            "bounded_context_policy_version": ("bounded-public-investigation-request-context-v1"),
            "exact_surface_policy_version": "exact-self-directed-pre-plan-surface-v1",
            "opt_in_successor": True,
        }
        and len(review_raw) == V24_ACTIVATION_REVIEW_BYTES
        and sha256_bytes(review_raw) == V24_ACTIVATION_REVIEW_FILE_SHA256
        and review.get("content_hash") == V24_ACTIVATION_REVIEW_CONTENT_HASH
        and review.get("status") == "activation-reviewed-candidate-decision-ready"
        and review.get("runtime_identity") == V24_RUNTIME_IDENTITY
        and review.get("decision", {}).get("candidate_preparation_ready") is True
        and review.get("decision", {}).get("candidate_created") is False
        and review.get("decision", {}).get("rehearsal_executed") is False
        and review.get("external_calls") == 0
        and review.get("paid_execution_authorized") is False
    ):
        raise RecoveryError("Lean V24 evidence binding differs")
    return {
        "qualification": {
            "path": V24_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(qualification_raw),
            "file_sha256": sha256_bytes(qualification_raw),
            "content_hash": qualification["content_hash"],
            "runtime_identity": V24_RUNTIME_IDENTITY,
        },
        "activation_review": {
            "path": V24_ACTIVATION_REVIEW_PATH.as_posix(),
            "file_bytes": len(review_raw),
            "file_sha256": sha256_bytes(review_raw),
            "content_hash": review["content_hash"],
            "candidate_preparation_ready": True,
        },
    }


def _selection_evidence(root: Path) -> dict[str, Any]:
    predecessor, predecessor_raw = _stable_json(
        root, PREDECESSOR_CANDIDATE_PATH, "Consumed Rapid R19 candidate"
    )
    if not (
        len(predecessor_raw) == PREDECESSOR_CANDIDATE_BYTES
        and sha256_bytes(predecessor_raw) == PREDECESSOR_CANDIDATE_FILE_SHA256
        and predecessor.get("content_hash") == PREDECESSOR_CANDIDATE_CONTENT_HASH
        and predecessor.get("execution_hash") == PREDECESSOR_EXECUTION_HASH
        and predecessor.get("variant_contracts") == PREDECESSOR_VARIANT_CONTRACTS
    ):
        raise RecoveryError("Consumed Rapid R19 candidate identity differs")
    driver, driver_raw = _stable_json(
        root, DRIVER_QUALIFICATION_PATH, "Rapid terminal-state parity qualification"
    )
    if not (
        len(driver_raw) == DRIVER_QUALIFICATION_BYTES
        and sha256_bytes(driver_raw) == DRIVER_QUALIFICATION_FILE_SHA256
        and driver.get("content_hash") == DRIVER_QUALIFICATION_CONTENT_HASH
        and driver.get("status") == "offline-qualified"
        and driver.get("successor_policy_version")
        == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
        and driver.get("paid_execution_authorized") is False
    ):
        raise RecoveryError("Rapid terminal-state parity qualification differs")
    return {
        "schema_version": "rapid-anyio-v5-v22-v24-selection-evidence-v1",
        "policy_version": ("qualified-public-v22-v24-anyio-v5-self-directed-bounded-ab-v1"),
        "official": False,
        "public_development_history_only": True,
        "heldout_outcomes_used": False,
        "private_evidence_used": False,
        "hidden_failure_cause_used": False,
        "reference_patch_used": False,
        "consumed_r19": {
            "candidate": {
                "path": PREDECESSOR_CANDIDATE_PATH.as_posix(),
                "file_bytes": len(predecessor_raw),
                "file_sha256": sha256_bytes(predecessor_raw),
                "content_hash": predecessor["content_hash"],
                "execution_hash": predecessor["execution_hash"],
            },
            "result": _result_identity(root),
            "retry_allowed": False,
            "historical_result_reclassified": False,
        },
        "terminal_state_parity_qualification": {
            "path": DRIVER_QUALIFICATION_PATH.as_posix(),
            "file_bytes": len(driver_raw),
            "file_sha256": sha256_bytes(driver_raw),
            "content_hash": driver["content_hash"],
            "policy_version": driver["successor_policy_version"],
        },
        "control_lean_v22": _validated_v22_evidence(root),
        "treatment_lean_v24": _validated_v24_evidence(root),
        "changed_experiment_variable": (
            "v22-to-v24-self-directed-exploration-plus-bounded-request-context"
        ),
        "single_policy_effect_attribution_allowed": False,
        "product_package_comparison_only": True,
        "quality_improvement_established": False,
        "generalization_established": False,
    }


def _schedule_projection(
    config: RapidAnyioV22V24ABConfig,
    binding: Any,
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
    selection = _selection_evidence(root)
    binding = _task_binding(config, root, selection)
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
    driver_contract = {
        "contract_schema": RAPID_BATCH_DRIVER_CONTRACT_SCHEMA,
        "event_schema": RAPID_BATCH_DRIVER_EVENT_SCHEMA,
        "policy_version": RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
        "qualification_path": DRIVER_QUALIFICATION_PATH.as_posix(),
        "qualification_file_sha256": DRIVER_QUALIFICATION_FILE_SHA256,
        "qualification_content_hash": DRIVER_QUALIFICATION_CONTENT_HASH,
        "row_advance_owner": "append-only-driver",
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
        "selection_evidence": selection,
        "selection_evidence_hash": sha256_json(selection),
        "runtime_build_schema": RUNTIME_BUILD_SCHEMA,
        "runtime_build_hash": runtime_build_hash,
        "model_contract": model_contract,
        "predecessor_candidate": _file_binding(root, PREDECESSOR_CANDIDATE_PATH).model_dump(
            mode="json"
        ),
        "predecessor_result": _file_binding(root, PREDECESSOR_RESULT_PATH).model_dump(mode="json"),
        "variant_contracts": VARIANT_CONTRACTS,
        "driver_contract": driver_contract,
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
    "driver_contract",
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
        raise RecoveryError("Rapid candidate-v28 execution body is incomplete") from exc


def build_rapid_public_development_v23_candidate(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build a deterministic candidate while every external seam is blocked."""

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
        raise RecoveryError("Rapid candidate-v28 generation attempted an external call")

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
    candidate = {
        **body,
        "execution_hash": sha256_json(body),
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
    content = {key: value for key, value in candidate.items() if key != "content_hash"}
    schedule = candidate.get("schedule")
    selection = candidate.get("selection_evidence")
    cost = candidate.get("cost_control")
    driver = candidate.get("driver_contract")
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
        and isinstance(selection, dict)
        and candidate.get("selection_evidence_hash") == sha256_json(selection)
        and isinstance(schedule, list)
        and len(schedule) == 6
        and tuple((row.get("order"), row.get("variant"), row.get("repetition")) for row in schedule)
        == EXPECTED_SCHEDULE
        and candidate.get("schedule_hash") == sha256_json(schedule)
        and isinstance(cost, dict)
        and candidate.get("cost_control_hash") == sha256_json(cost)
        and isinstance(driver, dict)
        and driver.get("policy_version") == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
        and driver.get("row_advance_owner") == "append-only-driver"
        and candidate.get("execution_hash") == sha256_json(_execution_body(candidate))
        and candidate.get("content_hash") == sha256_json(content)
    ):
        raise RecoveryError("Rapid candidate-v28 identity differs")


def candidate_bytes(candidate: dict[str, Any]) -> bytes:
    _validate_candidate(candidate)
    return (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def load_rapid_public_development_v23_candidate(
    repository: str | Path = ".",
    candidate_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    selected = ensure_within(root, Path(candidate_path).as_posix())
    if selected.is_symlink() or not selected.is_file():
        raise RecoveryError("Rapid candidate-v28 is unavailable")
    try:
        candidate = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("Rapid candidate-v28 is invalid") from exc
    if type(candidate) is not dict or candidate_bytes(candidate) != selected.read_bytes():
        raise RecoveryError("Rapid candidate-v28 bytes differ")
    current = build_rapid_public_development_v23_candidate(repository=root)
    if candidate != current:
        raise RecoveryError("Rapid candidate-v28 current binding differs")
    return candidate


def materialize_rapid_public_development_v23_candidate(
    repository: str | Path = ".",
    output_path: str | Path = CANDIDATE_PATH,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    output = ensure_within(root, Path(output_path).as_posix())
    if output.exists():
        return load_rapid_public_development_v23_candidate(root, output_path)
    candidate = build_rapid_public_development_v23_candidate(repository=root)
    _prepare_batch(candidate, authority_kind="rehearsal", repository=root)
    _write_once(output, candidate_bytes(candidate))
    return load_rapid_public_development_v23_candidate(root, output_path)


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
        "driver_contract": candidate["driver_contract"],
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


def build_rapid_v23_run_manifest(
    candidate: dict[str, Any],
    order: int,
    *,
    repository: str | Path = ".",
) -> RunManifest:
    _validate_candidate(candidate)
    return _build_manifest_unchecked(candidate, order, repository=repository)


def _manifest_matches_projection(projection: dict[str, Any], manifest: RunManifest) -> bool:
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
        driver = projection["driver_contract"]
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
            and driver["policy_version"] == RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION
            and driver["row_advance_owner"] == "append-only-driver"
        )
    except (AssertionError, KeyError, StopIteration, TypeError, ValueError):
        return False


def rapid_v23_registered_plan_matches_manifest(
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
) -> PreparedRapidV23Batch:
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
        raise HarnessAdmissionError("Rapid candidate-v28 plan schema is not registered")
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
                "Rapid candidate-v28 manifest is incompatible with its verifier"
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
    return PreparedRapidV23Batch(
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


def rehearsal_bytes(receipt: dict[str, Any]) -> bytes:
    body = {key: value for key, value in receipt.items() if key != "content_hash"}
    if receipt.get("content_hash") != sha256_json(body):
        raise RecoveryError("Rapid candidate-v28 rehearsal content hash differs")
    return (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _build_rehearsal_for(candidate: dict[str, Any], *, repository: str | Path) -> dict[str, Any]:
    prepared = _prepare_batch(candidate, authority_kind="rehearsal", repository=repository)
    first_manifest = prepared.manifests[0]
    first_authorization = issue_row_execution_authorization(
        prepared.authorization, first_manifest, active_schedule_order=1
    )
    first_boundary = AgentRunner.rehearse_provider_dispatch(first_manifest, first_authorization)
    first_receipt = row_execution_authorization_receipt(first_authorization)
    transition_body = {
        "driver_policy_version": RAPID_BATCH_DRIVER_TERMINAL_PARITY_POLICY_VERSION,
        "prior_schedule_order": 1,
        "prior_schedule_row_id": candidate["schedule"][0]["schedule_row_id"],
        "prior_run_id": first_manifest.run_id,
        "prior_terminal_kind": "ordinary-settled",
        "prior_outcome_kind": "resolved",
        "terminal_persisted_before_decision": True,
        "decision": "continue",
        "decision_source": "ordinary-terminal",
        "decision_persisted_before_capability": True,
        "next_schedule_order": 2,
        "next_schedule_row_id": candidate["schedule"][1]["schedule_row_id"],
        "next_run_id": prepared.manifests[1].run_id,
    }
    transition = {**transition_body, "content_hash": sha256_json(transition_body)}
    second_manifest = prepared.manifests[1]
    second_authorization = issue_row_execution_authorization(
        prepared.authorization, second_manifest, active_schedule_order=2
    )
    second_boundary = AgentRunner.rehearse_provider_dispatch(second_manifest, second_authorization)
    second_receipt = row_execution_authorization_receipt(second_authorization)
    body = {
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
        "driver_binding": candidate["driver_contract"],
        "stage_sequence": list(_REHEARSAL_STAGE_SEQUENCE),
        "first_row_capability": first_receipt,
        "first_provider_boundary": first_boundary,
        "inter_row_transition": transition,
        "second_row_capability": second_receipt,
        "second_provider_boundary": second_boundary,
        "stopped_before": "second-provider-dispatch",
        "provider_calls_made": 0,
        "docker_calls_made": 0,
        "task_calls_made": 0,
        "evaluator_calls_made": 0,
        "visible_check_calls_made": 0,
        "added_model_cost_usd": 0.0,
        "harness_admission_failures": 0,
    }
    return {**body, "content_hash": sha256_json(body)}


def build_rapid_public_development_v23_rehearsal(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    candidate = load_rapid_public_development_v23_candidate(root)
    return _build_rehearsal_for(candidate, repository=root)


def load_rapid_public_development_v23_rehearsal(
    candidate: dict[str, Any],
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    path = ensure_within(root, REHEARSAL_PATH.as_posix())
    if path.is_symlink() or not path.is_file():
        raise HarnessAdmissionError(
            "Rapid candidate-v28 requires its exact no-call rehearsal receipt"
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessAdmissionError("Rapid candidate-v28 rehearsal is invalid") from exc
    expected = _build_rehearsal_for(candidate, repository=root)
    if receipt != expected or rehearsal_bytes(receipt) != path.read_bytes():
        raise HarnessAdmissionError("Rapid candidate-v28 rehearsal binding differs")
    return receipt


def rehearse_rapid_public_development_v23(
    config_path: str | Path = CONFIG_PATH,
    *,
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    candidate = load_rapid_public_development_v23_candidate(root)
    receipt = _build_rehearsal_for(candidate, repository=root)
    output = ensure_within(root, REHEARSAL_PATH.as_posix())
    if output.exists():
        existing = load_rapid_public_development_v23_rehearsal(candidate, repository=root)
        if existing != receipt:
            raise RecoveryError("Rapid candidate-v28 rehearsal changed")
        return existing
    _write_once(output, rehearsal_bytes(receipt))
    return load_rapid_public_development_v23_rehearsal(candidate, repository=root)


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
                "Rapid candidate-v28 approved plan path contains different bytes"
            ) from None
    return path


def _run_prepared_driver(
    *,
    candidate: dict[str, Any],
    prepared: PreparedRapidV23Batch,
    live_authorization: LiveExecutionAuthorization,
    runner: AgentRunner,
    repository: str | Path,
) -> dict[str, Any]:
    root = Path(repository).resolve()
    contract = build_rapid_batch_driver_terminal_parity_contract(
        experiment_id=EXPERIMENT_ID,
        manifests=prepared.manifests,
        batch_authorization=prepared.authorization,
        row_reserve_nanos=PER_RUN_RESERVE_NANOS,
        full_schedule_reserve_nanos=FULL_SCHEDULE_RESERVE_NANOS,
        hard_cap_nanos=HARD_CAP_NANOS,
    )

    def execute_row(
        *,
        schedule_row: dict[str, Any],
        manifest: RunManifest,
        row_authorization: Any,
    ) -> dict[str, Any]:
        return runner.start(
            schedule_row["task"],
            model="openai",
            memory_condition=MemoryCondition.NO_MEMORY,
            manifest=manifest,
            live_authorization=live_authorization,
            row_execution_authorization=row_authorization,
        )

    def project_row(
        *,
        schedule_row: dict[str, Any],
        manifest: RunManifest,
        result: Any,
        runner: AgentRunner,
        error: Exception | None,
    ) -> dict[str, Any]:
        return _rapid_v4_row_projection(
            schedule_row=schedule_row,
            manifest=manifest,
            result=result,
            runner=runner,
            error=error,
        )

    return run_append_only_rapid_batch_driver(
        journal_path=_result_bundle_path(candidate, root),
        contract=contract,
        manifests=prepared.manifests,
        schedule_rows=tuple(candidate["schedule"]),
        runner=runner,
        batch_authorization=prepared.authorization,
        execute_row=execute_row,
        project_row=project_row,
    )


def run_rapid_public_development_v23(
    config_path: str | Path = CONFIG_PATH,
    *,
    approve_live_cost: bool,
    approved_execution_hash: str | None,
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Execute R20 only under fresh exact authority and the qualified driver."""

    root = Path(repository).resolve()
    _read_config(config_path, repository=root)
    candidate = load_rapid_public_development_v23_candidate(root)
    bundle_path = _result_bundle_path(candidate, root)
    if bundle_path.exists() or bundle_path.is_symlink():
        raise ContractError("Rapid candidate-v28 result already exists and cannot be retried")
    if not approve_live_cost or approved_execution_hash != candidate["execution_hash"]:
        raise ContractError(
            "Rapid candidate-v28 live execution requires its exact hash and cost-cap approval"
        )
    load_rapid_public_development_v23_rehearsal(candidate, repository=root)
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
        raise ContractError("Rapid candidate-v28 live execution requires OPENAI_API_KEY")
    if not DockerSandbox.available():
        raise ContractError("Rapid candidate-v28 requires the local Docker daemon")
    binding = candidate["task_bindings"][0]
    if (
        DockerSandbox(binding["evaluator_image"]).image_identity()
        != (binding["evaluator_image_digest"])
    ):
        raise ContractError("Rapid candidate-v28 AnyIO image is unavailable")
    runner = AgentRunner(root / ".patchloop")
    return _run_prepared_driver(
        candidate=candidate,
        prepared=prepared,
        live_authorization=live_authorization,
        runner=runner,
        repository=root,
    )


__all__ = [
    "CANDIDATE_PATH",
    "CONFIG_PATH",
    "EXPERIMENT_ID",
    "REHEARSAL_PATH",
    "build_rapid_public_development_v23_candidate",
    "build_rapid_public_development_v23_rehearsal",
    "build_rapid_v23_run_manifest",
    "load_rapid_public_development_v23_candidate",
    "load_rapid_public_development_v23_rehearsal",
    "materialize_rapid_public_development_v23_candidate",
    "rapid_v23_registered_plan_matches_manifest",
    "rehearse_rapid_public_development_v23",
    "run_rapid_public_development_v23",
]
