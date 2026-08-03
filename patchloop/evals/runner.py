"""Frozen, randomized experiment campaign runner and live-execution preflight."""

from __future__ import annotations

import hmac
import json
import os
import random
import subprocess
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from patchloop.agent.model import (
    SYSTEM_PROMPT_V3,
    SYSTEM_PROMPT_V5,
    SYSTEM_PROMPT_V6,
    SYSTEM_PROMPT_V7,
    SYSTEM_PROMPT_V8,
)
from patchloop.agent.review import load_public_review_contract
from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.agent.tools import (
    TOOL_SCHEMAS_V2,
    TOOL_SCHEMAS_V4,
    TOOL_SCHEMAS_V5,
    TOOL_SCHEMAS_V6,
)
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    FaultSpec,
    MemoryCondition,
    PublicReviewContract,
    RunManifest,
    TaskPackage,
)
from patchloop.dataset import require_dataset_role, require_frozen_dataset
from patchloop.errors import ContractError
from patchloop.evals.budget import calculate_budget_pressure
from patchloop.memory.store import latest_frozen_index
from patchloop.runtime import build_manifest, repository_root, runtime_root
from patchloop.sandbox import DockerSandbox
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_text, utc_now

OFFICIAL_PRICING_URL = "https://developers.openai.com/api/docs/pricing"
PRICING_MAX_AGE = timedelta(hours=72)
LEGACY_TERRA_MODEL_ID = "gpt-5.6-terra"
GPT54_MINI_PILOT_MODEL_ID = "gpt-5.4-mini-2026-03-17"
CAMPAIGN_MODEL_ID = GPT54_MINI_PILOT_MODEL_ID
HISTORICAL_TERRA_PILOT_EXPERIMENT_IDS = frozenset(
    {
        "dev-validation-live-pilot-20260728",
        "dev-validation-live-pilot-20260728-r2",
        "dev-validation-live-pilot-20260728-r3",
    }
)
HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS = frozenset(
    {"dev-validation-gpt54mini-campaign-20260730-r1"}
)
HISTORICAL_MINI_DIAGNOSTIC_EXPERIMENT_IDS = frozenset(
    {
        "dev-validation-gpt54mini-pilot-20260729-r1",
        "dev-validation-gpt54mini-pilot-20260729-r2",
        "dev-validation-gpt54mini-d037-20260729-r3",
        "dev-validation-gpt54mini-d037-20260729-r4",
        "dev-validation-gpt54mini-d037-20260730-r5",
        "dev-validation-gpt54mini-d037-20260730-r6",
    }
)
CONSUMED_CURRENT_LIVE_EXPERIMENT_IDS = frozenset(
    {
        "dev-validation-gpt54mini-campaign-20260730-r2",
        "dev-no-memory-20260728",
        "dev-validation-gpt54mini-investigation-v4-20260730-r1",
        "dev-no-memory-v4-20260730-r1",
    }
)
SUPERSEDED_UNEXECUTED_LIVE_EXPERIMENT_IDS = frozenset(
    {"dev-validation-gpt54mini-token-tail-v5-20260730-r1"}
)
CONSUMED_COMPLETION_PANEL_EXPERIMENT_IDS = frozenset(
    {"dev-validation-gpt54mini-completion-v6-20260731-r1"}
)
CONSUMED_BUDGET_PILOT_EXPERIMENT_IDS = frozenset(
    {"dev-no-memory-budget-pilot-20260731-r1"}
)
CONSUMED_CORRECTIVE_PANEL_EXPERIMENT_IDS = frozenset(
    {"dev-no-memory-corrective-pilot-20260731-r1"}
)
CONSUMED_SATURATION_PILOT_EXPERIMENT_IDS = frozenset(
    {"dev-no-memory-saturation-v8-pilot-20260801-r1"}
)
CONSUMED_REVIEW_EVIDENCE_PILOT_EXPERIMENT_IDS = frozenset(
    {"dev-no-memory-review-evidence-v9-pilot-20260801-r1"}
)
CONSUMED_COVERAGE_REVIEW_PILOT_EXPERIMENT_IDS = frozenset(
    {"dev-no-memory-coverage-review-v10-pilot-20260802-r1"}
)
CONSUMED_COVERAGE_REJECTION_PILOT_EXPERIMENT_IDS = frozenset(
    {"dev-no-memory-coverage-rejection-v11-pilot-20260802-r1"}
)
CONSUMED_GENERIC_BASELINE_READINESS_EXPERIMENT_IDS = frozenset(
    {
        "generic-baseline-readiness-v2v5-20260802-r1",
        "generic-baseline-readiness-v2v5-20260802-r2",
        "generic-baseline-readiness-v2v5-20260803-r3",
    }
)
CONSUMED_WORKFLOW_COMPLETION_PROBE_EXPERIMENT_IDS = frozenset(
    {"pyfakefs-workflow-completion-probe-v2v5-20260803-r1"}
)
HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS = (
    HISTORICAL_TERRA_PILOT_EXPERIMENT_IDS
    | HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS
    | HISTORICAL_MINI_DIAGNOSTIC_EXPERIMENT_IDS
    | CONSUMED_CURRENT_LIVE_EXPERIMENT_IDS
    | CONSUMED_COMPLETION_PANEL_EXPERIMENT_IDS
    | CONSUMED_BUDGET_PILOT_EXPERIMENT_IDS
    | CONSUMED_CORRECTIVE_PANEL_EXPERIMENT_IDS
    | CONSUMED_SATURATION_PILOT_EXPERIMENT_IDS
    | CONSUMED_REVIEW_EVIDENCE_PILOT_EXPERIMENT_IDS
    | CONSUMED_COVERAGE_REVIEW_PILOT_EXPERIMENT_IDS
    | CONSUMED_COVERAGE_REJECTION_PILOT_EXPERIMENT_IDS
    | CONSUMED_GENERIC_BASELINE_READINESS_EXPERIMENT_IDS
    | CONSUMED_WORKFLOW_COMPLETION_PROBE_EXPERIMENT_IDS
)
SINGLE_TASK_LIVE_EXPERIMENT_IDS = (
    HISTORICAL_TERRA_PILOT_EXPERIMENT_IDS
    | HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS
    | CONSUMED_CURRENT_LIVE_EXPERIMENT_IDS
    | SUPERSEDED_UNEXECUTED_LIVE_EXPERIMENT_IDS
)
PRICE_FIELDS = (
    "input_price_per_million_usd",
    "cached_input_price_per_million_usd",
    "cache_write_input_price_per_million_usd",
    "output_price_per_million_usd",
)
OFFICIAL_PRICES_BY_MODEL = {
    LEGACY_TERRA_MODEL_ID: {
        "input_price_per_million_usd": 2.5,
        "cached_input_price_per_million_usd": 0.25,
        "cache_write_input_price_per_million_usd": 3.125,
        "output_price_per_million_usd": 15.0,
    },
    GPT54_MINI_PILOT_MODEL_ID: {
        "input_price_per_million_usd": 0.75,
        "cached_input_price_per_million_usd": 0.075,
        "cache_write_input_price_per_million_usd": None,
        "output_price_per_million_usd": 4.5,
    },
}
GPT54_MINI_PILOT_BUDGET = Budget(max_total_tokens=90_000)
GPT54_MINI_D037_CORRECTIVE_BUDGET = Budget(max_total_tokens=120_000)
GPT54_MINI_D037_TAIL_RESERVE_BUDGET = Budget(max_total_tokens=200_000)
GPT54_MINI_HISTORICAL_200K_CAMPAIGN_BUDGET = Budget(
    max_model_calls=21,
    max_total_tokens=200_000,
)
GPT54_MINI_CAMPAIGN_BUDGET = Budget(
    max_model_calls=21,
    max_total_tokens=250_000,
)
GPT54_MINI_COMPLETION_BUDGET = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=600_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_MEMORY_DEVELOPMENT_BUDGET_PILOT = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=480_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_MEMORY_DEVELOPMENT_CORRECTIVE_PILOT = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=900_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_MEMORY_DEVELOPMENT_SATURATION_PILOT = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=900_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_MEMORY_DEVELOPMENT_REVIEW_EVIDENCE_PILOT = Budget(
    max_model_calls=60,
    max_tool_calls=100,
    max_total_tokens=1_200_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REVIEW_PILOT = Budget(
    max_model_calls=60,
    max_tool_calls=100,
    max_total_tokens=1_200_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REJECTION_PILOT = Budget(
    max_model_calls=60,
    max_tool_calls=100,
    max_total_tokens=1_200_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_GENERIC_BASELINE_READINESS_BUDGET = Budget(
    max_model_calls=40,
    max_tool_calls=100,
    max_total_tokens=850_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_GENERIC_BASELINE_READINESS_D077_BUDGET = Budget(
    max_model_calls=50,
    max_tool_calls=100,
    max_total_tokens=1_200_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_GENERIC_BASELINE_READINESS_D081_BUDGET = Budget(
    max_model_calls=None,
    max_tool_calls=None,
    max_total_tokens=2_400_000,
    wall_clock_timeout_seconds=1_800,
)
GPT54_MINI_WORKFLOW_COMPLETION_PROBE_BUDGET = Budget(
    max_model_calls=None,
    max_tool_calls=None,
    max_total_tokens=3_000_000,
    wall_clock_timeout_seconds=7_200,
)
GPT54_MINI_D037_CORRECTIVE_MAX_OUTPUT_TOKENS = 25_000
CAMPAIGN_BUDGET = GPT54_MINI_CAMPAIGN_BUDGET
CAMPAIGN_MAX_OUTPUT_TOKENS = GPT54_MINI_D037_CORRECTIVE_MAX_OUTPUT_TOKENS

PILOT_TASK = (
    "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes/public.yaml"
)
PILOT_TASK_ID = "babel-strict-grouped-decimal-trailing-zeroes"
COMPLETION_PANEL_TASKS = {
    PILOT_TASK,
    "tasks/dev-validation/moto-query-scanned-count/public.yaml",
}
COMPLETION_PANEL_TASK_IDS = {
    Path(path).parent.name for path in COMPLETION_PANEL_TASKS
}
GENERIC_BASELINE_READINESS_EXPERIMENT_ID = (
    "generic-baseline-readiness-v2v5-20260802-r1"
)
GENERIC_BASELINE_READINESS_D077_EXPERIMENT_ID = (
    "generic-baseline-readiness-v2v5-20260802-r2"
)
GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID = (
    "generic-baseline-readiness-v2v5-20260803-r3"
)
GENERIC_BASELINE_READINESS_BUDGET_BY_EXPERIMENT_ID = {
    GENERIC_BASELINE_READINESS_EXPERIMENT_ID: (
        GPT54_MINI_GENERIC_BASELINE_READINESS_BUDGET
    ),
    GENERIC_BASELINE_READINESS_D077_EXPERIMENT_ID: (
        GPT54_MINI_GENERIC_BASELINE_READINESS_D077_BUDGET
    ),
    GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID: (
        GPT54_MINI_GENERIC_BASELINE_READINESS_D081_BUDGET
    ),
}
GENERIC_BASELINE_READINESS_COST_BY_EXPERIMENT_ID = {
    GENERIC_BASELINE_READINESS_EXPERIMENT_ID: (15.75, 16.0),
    GENERIC_BASELINE_READINESS_D077_EXPERIMENT_ID: (22.05, 23.0),
    GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID: (43.65, 44.0),
}
GENERIC_BASELINE_READINESS_TASKS = [
    PILOT_TASK,
    "tasks/dev-validation/moto-query-scanned-count/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
]
GENERIC_BASELINE_READINESS_TASK_IDS = {
    Path(path).parent.name for path in GENERIC_BASELINE_READINESS_TASKS
}
WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID = (
    "pyfakefs-workflow-completion-probe-v2v5-20260803-r1"
)
WORKFLOW_COMPLETION_PROBE_TASK = (
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml"
)
WORKFLOW_COMPLETION_PROBE_TASK_ID = Path(
    WORKFLOW_COMPLETION_PROBE_TASK
).parent.name
WORKFLOW_COMPLETION_PROBE_ESTIMATED_COST_USD = 13.6125
WORKFLOW_COMPLETION_PROBE_COST_LIMIT_USD = 14.0
MEMORY_DEVELOPMENT_TASKS = {
    "tasks/dev-train/loguru-invalid-format-feedback/public.yaml",
    "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
    "tasks/dev-train/tox-cross-section-empty-substitution/public.yaml",
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
    "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
}
MEMORY_DEVELOPMENT_TASK_IDS = {
    Path(path).parent.name for path in MEMORY_DEVELOPMENT_TASKS
}
MEMORY_DEVELOPMENT_BUDGET_PILOT_TASKS = {
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
    "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
}
MEMORY_DEVELOPMENT_BUDGET_PILOT_TASK_IDS = {
    Path(path).parent.name
    for path in MEMORY_DEVELOPMENT_BUDGET_PILOT_TASKS
}
SATURATION_PILOT_TASK = (
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml"
)
SATURATION_PILOT_TASK_ID = Path(SATURATION_PILOT_TASK).parent.name
REVIEW_EVIDENCE_PILOT_TASK = SATURATION_PILOT_TASK
REVIEW_EVIDENCE_PILOT_TASK_ID = SATURATION_PILOT_TASK_ID
COVERAGE_REVIEW_PILOT_TASK = SATURATION_PILOT_TASK
COVERAGE_REVIEW_PILOT_TASK_ID = SATURATION_PILOT_TASK_ID
COVERAGE_REVIEW_PILOT_EXPERIMENT_ID = (
    "dev-no-memory-coverage-review-v10-pilot-20260802-r1"
)
COVERAGE_REJECTION_PILOT_TASK = COVERAGE_REVIEW_PILOT_TASK
COVERAGE_REJECTION_PILOT_TASK_ID = COVERAGE_REVIEW_PILOT_TASK_ID
COVERAGE_REJECTION_PILOT_EXPERIMENT_ID = (
    "dev-no-memory-coverage-rejection-v11-pilot-20260802-r1"
)
PUBLIC_REVIEW_CONTRACT_ROOT = Path("experiments/review-contracts")
PUBLIC_REVIEW_CONTRACT_V2_ROOT = Path("experiments/review-contracts-v2")
CORRECTIVE_TOOL_SCHEMA_VERSION = "v4"
CORRECTIVE_CONTEXT_POLICY_VERSION = "phase-evidence-v7"
CORRECTIVE_RUNTIME_CONTRACT_SCHEMA = "corrective-runtime-contract-v1"
SATURATION_CONTEXT_POLICY_VERSION = "phase-evidence-v8"
SATURATION_RUNTIME_CONTRACT_SCHEMA = "corrective-runtime-contract-v2"
REVIEW_EVIDENCE_CONTEXT_POLICY_VERSION = "phase-evidence-v9"
REVIEW_EVIDENCE_RUNTIME_CONTRACT_SCHEMA = "corrective-runtime-contract-v3"
COVERAGE_REVIEW_TOOL_SCHEMA_VERSION = "v5"
COVERAGE_REVIEW_CONTEXT_POLICY_VERSION = "phase-evidence-v10"
COVERAGE_REVIEW_RUNTIME_CONTRACT_SCHEMA = "corrective-runtime-contract-v4"
COVERAGE_REJECTION_TOOL_SCHEMA_VERSION = "v6"
COVERAGE_REJECTION_CONTEXT_POLICY_VERSION = "phase-evidence-v11"
COVERAGE_REJECTION_RUNTIME_CONTRACT_SCHEMA = "corrective-runtime-contract-v5"
GENERIC_BASELINE_RUNTIME_CONTRACT_SCHEMA = "generic-baseline-runtime-contract-v1"
GENERIC_BASELINE_OBSERVABILITY_RUNTIME_CONTRACT_SCHEMA = (
    "generic-baseline-runtime-contract-v2"
)
WORKFLOW_COMPLETION_RUNTIME_CONTRACT_SCHEMA = (
    "workflow-completion-runtime-contract-v1"
)
WORKFLOW_COMPLETION_CALL_GUARD_POLICY = "model-tool-observability-only-v1"
GENERIC_BASELINE_OBSERVABILITY_CALL_GUARD_POLICY = (
    WORKFLOW_COMPLETION_CALL_GUARD_POLICY
)
QUALIFICATION_GATE_CHECK_PROJECTION_SCHEMA = (
    "qualification-gate-check-projection-v1"
)
PRICING_START_VERIFICATION_SCHEMA = "pricing-start-verification-v1"

HASH_BOUND_CORRECTIVE_PURPOSES = {
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT,
}
HASH_BOUND_RUNTIME_PURPOSES = HASH_BOUND_CORRECTIVE_PURPOSES | {
    ExperimentPurpose.GENERIC_BASELINE_READINESS,
    ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
}


def _normalized_task_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def _corrective_runtime_contract(
    suite: ExperimentSuite,
    *,
    harness_git_commit: Any,
) -> dict[str, Any] | None:
    """Return the corrective-only runtime identity approved by the execution hash."""

    if suite.purpose not in HASH_BOUND_CORRECTIVE_PURPOSES:
        return None
    saturation_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
    )
    review_evidence_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
    )
    coverage_review_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
    )
    coverage_rejection_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
    )
    return {
        "schema_version": (
            COVERAGE_REJECTION_RUNTIME_CONTRACT_SCHEMA
            if coverage_rejection_pilot
            else COVERAGE_REVIEW_RUNTIME_CONTRACT_SCHEMA
            if coverage_review_pilot
            else REVIEW_EVIDENCE_RUNTIME_CONTRACT_SCHEMA
            if review_evidence_pilot
            else SATURATION_RUNTIME_CONTRACT_SCHEMA
            if saturation_pilot
            else CORRECTIVE_RUNTIME_CONTRACT_SCHEMA
        ),
        "tool_schema_version": (
            COVERAGE_REJECTION_TOOL_SCHEMA_VERSION
            if coverage_rejection_pilot
            else COVERAGE_REVIEW_TOOL_SCHEMA_VERSION
            if coverage_review_pilot
            else CORRECTIVE_TOOL_SCHEMA_VERSION
        ),
        "context_policy_version": (
            COVERAGE_REJECTION_CONTEXT_POLICY_VERSION
            if coverage_rejection_pilot
            else COVERAGE_REVIEW_CONTEXT_POLICY_VERSION
            if coverage_review_pilot
            else REVIEW_EVIDENCE_CONTEXT_POLICY_VERSION
            if review_evidence_pilot
            else SATURATION_CONTEXT_POLICY_VERSION
            if saturation_pilot
            else CORRECTIVE_CONTEXT_POLICY_VERSION
        ),
        "system_prompt_hash": sha256_text(
            SYSTEM_PROMPT_V8
            if coverage_rejection_pilot
            else SYSTEM_PROMPT_V7
            if coverage_review_pilot
            else SYSTEM_PROMPT_V6
            if review_evidence_pilot
            else SYSTEM_PROMPT_V5
        ),
        "tool_schema_hash": sha256_text(
            canonical_json(
                TOOL_SCHEMAS_V5
                if coverage_review_pilot
                else TOOL_SCHEMAS_V6
                if coverage_rejection_pilot
                else TOOL_SCHEMAS_V4
            )
        ),
        "harness_git_commit": harness_git_commit,
    }


def _experiment_runtime_contract(
    suite: ExperimentSuite,
    *,
    harness_git_commit: Any,
) -> dict[str, Any] | None:
    """Return the execution-hash-bound runtime identity for an exact live suite."""

    if suite.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS:
        count_observability = bool(
            suite.experiment_id
            == GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID
        )
        return {
            "schema_version": (
                GENERIC_BASELINE_OBSERVABILITY_RUNTIME_CONTRACT_SCHEMA
                if count_observability
                else GENERIC_BASELINE_RUNTIME_CONTRACT_SCHEMA
            ),
            "tool_schema_version": "v2",
            "context_policy_version": "phase-evidence-v5",
            "system_prompt_hash": sha256_text(SYSTEM_PROMPT_V3),
            "tool_schema_hash": sha256_text(canonical_json(TOOL_SCHEMAS_V2)),
            "transport_max_retries": suite.transport_max_retries,
            **(
                {
                    "call_guard_policy": (
                        GENERIC_BASELINE_OBSERVABILITY_CALL_GUARD_POLICY
                    )
                }
                if count_observability
                else {}
            ),
            "harness_git_commit": harness_git_commit,
        }
    if suite.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE:
        return {
            "schema_version": WORKFLOW_COMPLETION_RUNTIME_CONTRACT_SCHEMA,
            "tool_schema_version": "v2",
            "context_policy_version": "phase-evidence-v5",
            "system_prompt_hash": sha256_text(SYSTEM_PROMPT_V3),
            "tool_schema_hash": sha256_text(canonical_json(TOOL_SCHEMAS_V2)),
            "transport_max_retries": suite.transport_max_retries,
            "call_guard_policy": WORKFLOW_COMPLETION_CALL_GUARD_POLICY,
            "harness_git_commit": harness_git_commit,
        }
    return _corrective_runtime_contract(
        suite,
        harness_git_commit=harness_git_commit,
    )


def _pricing_contract(
    suite: ExperimentSuite,
    *,
    schedule_size: int,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    """Derive the persisted price inputs, reserves, and optional start-time proof."""

    expected_prices = OFFICIAL_PRICES_BY_MODEL.get(suite.model_id)
    configured_prices = [
        getattr(suite, field)
        for field in PRICE_FIELDS
        if getattr(suite, field) is not None
    ]
    per_run_cost_reserve = (
        (suite.budget.max_total_tokens + suite.max_output_tokens)
        * max(configured_prices)
        / 1_000_000
        if configured_prices
        else 0.0
    )
    budget_upper_bound = schedule_size * per_run_cost_reserve
    if suite.purpose in HASH_BOUND_RUNTIME_PURPOSES:
        # Keep the approval-facing currency values stable instead of exposing
        # binary floating-point tails such as 12.487499999999999.
        per_run_cost_reserve = round(per_run_cost_reserve, 12)
        budget_upper_bound = round(
            schedule_size * per_run_cost_reserve,
            12,
        )
    payload: dict[str, Any] = {
        "model_id": suite.model_id,
        "verified_at": (
            suite.pricing_verified_at.isoformat()
            if suite.pricing_verified_at
            else None
        ),
        "source_url": suite.pricing_source_url,
        **{field: getattr(suite, field) for field in PRICE_FIELDS},
        "maximum_age_hours": int(
            PRICING_MAX_AGE.total_seconds() / 3600
        ),
        "per_run_cost_reserve_usd": per_run_cost_reserve,
        "budget_upper_bound_usd": budget_upper_bound,
    }
    if suite.purpose in HASH_BOUND_RUNTIME_PURPOSES:
        payload["start_time_verification"] = _pricing_freshness_evidence(
            suite,
            boundary_at=checked_at,
            expected_prices=expected_prices,
        )
    return payload


def _pricing_freshness_evidence(
    suite: ExperimentSuite,
    *,
    boundary_at: datetime | None,
    expected_prices: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    """Evaluate freshness at an immutable authorization or run boundary."""

    official_prices = (
        OFFICIAL_PRICES_BY_MODEL.get(suite.model_id)
        if expected_prices is None
        else expected_prices
    )
    age_seconds: float | None = None
    timezone_valid = bool(
        suite.pricing_verified_at is not None
        and suite.pricing_verified_at.tzinfo is not None
        and boundary_at is not None
        and boundary_at.tzinfo is not None
    )
    if timezone_valid:
        assert suite.pricing_verified_at is not None
        assert boundary_at is not None
        age_seconds = (
            boundary_at.astimezone(UTC)
            - suite.pricing_verified_at.astimezone(UTC)
        ).total_seconds()
    return {
        "schema_version": PRICING_START_VERIFICATION_SCHEMA,
        "checked_at": boundary_at.isoformat() if boundary_at else None,
        "age_seconds": age_seconds,
        "timezone_valid": timezone_valid,
        "date_not_future": bool(
            age_seconds is not None and age_seconds >= 0
        ),
        "within_maximum_age": bool(
            age_seconds is not None
            and 0 <= age_seconds <= PRICING_MAX_AGE.total_seconds()
        ),
        "official_source_matches": (
            suite.pricing_source_url == OFFICIAL_PRICING_URL
        ),
        "official_rates_match": bool(
            official_prices is not None
            and all(
                getattr(suite, field) == official_prices.get(field)
                for field in PRICE_FIELDS
            )
        ),
    }


def _pricing_freshness_passed(evidence: Any) -> bool:
    return bool(
        isinstance(evidence, dict)
        and evidence.get("schema_version")
        == PRICING_START_VERIFICATION_SCHEMA
        and evidence.get("timezone_valid") is True
        and evidence.get("date_not_future") is True
        and evidence.get("within_maximum_age") is True
        and evidence.get("official_source_matches") is True
        and evidence.get("official_rates_match") is True
    )


def _pricing_contract_matches(
    suite: ExperimentSuite,
    pricing: Any,
    *,
    schedule_size: int,
) -> bool:
    """Recompute a corrective plan's price evidence without using current time."""

    if not isinstance(pricing, dict):
        return False
    verification = pricing.get("start_time_verification")
    if not isinstance(verification, dict):
        return False
    raw_checked_at = verification.get("checked_at")
    if not isinstance(raw_checked_at, str):
        return False
    try:
        checked_at = datetime.fromisoformat(raw_checked_at)
    except ValueError:
        return False
    expected = _pricing_contract(
        suite,
        schedule_size=schedule_size,
        checked_at=checked_at,
    )
    return bool(
        canonical_json(pricing) == canonical_json(expected)
        and _pricing_freshness_passed(verification)
        and suite.estimated_cost_usd > 0
        and suite.estimated_cost_usd <= suite.cost_limit_usd
        and expected["budget_upper_bound_usd"] <= suite.cost_limit_usd
    )


class ExperimentDiagnostic(BaseModel):
    """One execution-hash-bound trace exercise required by a diagnostic suite."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["experiment-diagnostic-v1"] = (
        "experiment-diagnostic-v1"
    )
    profile: Literal[
        "d037-rejected-patch-retry-v1",
        "d037-rejected-patch-retry-v2",
        "d037-rejected-patch-retry-v3",
        "d037-rejected-patch-retry-v4",
        "v8-saturation-context-v1",
    ]
    required_trace_features: list[
        Literal["rejected_patch_retry_context", "saturation_context"]
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_profile(self) -> ExperimentDiagnostic:
        if len(set(self.required_trace_features)) != len(
            self.required_trace_features
        ):
            raise ValueError("diagnostic trace features must be unique")
        expected_features = (
            ["saturation_context"]
            if self.profile == "v8-saturation-context-v1"
            else ["rejected_patch_retry_context"]
        )
        if self.required_trace_features != expected_features:
            raise ValueError(
                f"{self.profile} diagnostic requires exactly "
                f"{expected_features[0]}"
            )
        return self


class ExperimentSuite(BaseModel):
    """Human-authored, immutable campaign configuration.

    Version 2 gives every suite an explicit purpose. Version 1 remains loadable
    for historical offline/core artifacts only.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["experiment-v1", "experiment-v2"] = "experiment-v2"
    experiment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    purpose: ExperimentPurpose | None = None
    core: bool | None = None
    tasks: list[str] = Field(min_length=1)
    conditions: list[MemoryCondition] = Field(min_length=1)
    repetitions: int = Field(default=2, ge=1, le=20)
    model: Literal["mock", "openai"] = "mock"
    model_id: str = CAMPAIGN_MODEL_ID
    reasoning_effort: Literal["medium"] = "medium"
    reasoning_mode: Literal["standard"] = "standard"
    service_tier: Literal["default"] = "default"
    transport_max_retries: Literal[0] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    max_output_tokens: int = Field(default=4096, ge=1)
    budget: Budget = Field(default_factory=Budget)
    seed: int = 20260723
    live_cost_approved: bool = False
    approved_execution_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    pilot_run_id: str | None = Field(
        default=None,
        pattern=r"^run_[a-zA-Z0-9_-]+$",
    )
    diagnostic: ExperimentDiagnostic | None = None
    estimated_cost_usd: float = Field(default=0, ge=0)
    cost_limit_usd: float = Field(default=150, ge=0)
    pricing_verified_at: datetime | None = None
    pricing_source_url: str | None = None
    input_price_per_million_usd: float | None = Field(default=None, gt=0)
    cached_input_price_per_million_usd: float | None = Field(default=None, gt=0)
    cache_write_input_price_per_million_usd: float | None = Field(default=None, gt=0)
    output_price_per_million_usd: float | None = Field(default=None, gt=0)
    retrieval_threshold: float = 0.72
    memory_token_budget: int = 2000
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_revision: str = "PIN_AT_FREEZE"
    dataset_manifest_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )

    @field_validator("transport_max_retries", mode="before")
    @classmethod
    def validate_transport_max_retries_type(cls, value: Any) -> Any:
        if value is not None and type(value) is not int:
            raise ValueError("transport_max_retries must be the JSON integer 0")
        return value

    @model_validator(mode="before")
    @classmethod
    def infer_v1_purpose(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        raw = dict(value)
        if raw.get("schema_version") == "experiment-v1" or (
            "schema_version" not in raw and "core" in raw
        ):
            raw.setdefault("schema_version", "experiment-v1")
            raw.setdefault(
                "purpose",
                (
                    ExperimentPurpose.CORE.value
                    if raw.get("core", False)
                    else ExperimentPurpose.OFFLINE_SMOKE.value
                ),
            )
        return raw

    @model_validator(mode="after")
    def validate_campaign(self) -> ExperimentSuite:
        if len(set(self.tasks)) != len(self.tasks):
            raise ValueError("experiment tasks must be unique")
        if len(set(self.conditions)) != len(self.conditions):
            raise ValueError("experiment conditions must be unique")
        if self.purpose is None:
            raise ValueError("experiment-v2 requires an explicit purpose")
        if self.schema_version == "experiment-v2" and self.core is not None:
            raise ValueError("experiment-v2 uses purpose instead of the legacy core flag")
        if self.schema_version == "experiment-v1":
            legacy_purpose = (
                ExperimentPurpose.CORE if self.core else ExperimentPurpose.OFFLINE_SMOKE
            )
            if self.purpose != legacy_purpose:
                raise ValueError("experiment-v1 purpose conflicts with the legacy core flag")
        diagnostic_allowed = bool(
            self.schema_version == "experiment-v2"
            and (
                (
                    self.purpose
                    == ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
                    and self.diagnostic is not None
                    and self.diagnostic.profile.startswith("d037-")
                )
                or (
                    self.purpose
                    == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
                    and self.diagnostic is not None
                    and self.diagnostic.profile == "v8-saturation-context-v1"
                )
            )
        )
        if self.diagnostic is not None and not diagnostic_allowed:
            raise ValueError(
                "diagnostic profiles are allowed only when the profile matches "
                "its experiment-v2 purpose"
            )
        if (
            self.experiment_id
            in GENERIC_BASELINE_READINESS_BUDGET_BY_EXPERIMENT_ID
            and self.purpose != ExperimentPurpose.GENERIC_BASELINE_READINESS
        ):
            raise ValueError(
                "generic baseline readiness experiment ids require the generic "
                "baseline readiness purpose"
            )
        if (
            self.experiment_id == WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID
            and self.purpose != ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        ):
            raise ValueError(
                "workflow completion probe experiment id requires the exact "
                "workflow completion probe purpose"
            )
        if (
            self.purpose
            not in {
                ExperimentPurpose.GENERIC_BASELINE_READINESS,
                ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
            }
            and self.transport_max_retries is not None
        ):
            raise ValueError(
                "transport_max_retries is frozen only for exact generic v2/v5 "
                "live profiles"
            )
        count_limits_disabled = bool(
            self.budget.max_model_calls is None
            or self.budget.max_tool_calls is None
        )
        generic_count_observability = bool(
            self.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS
            and self.experiment_id
            == GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID
        )
        if (
            self.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
            and not (
                self.budget.max_model_calls is None
                and self.budget.max_tool_calls is None
            )
        ):
            raise ValueError(
                "workflow completion probe requires both model and tool call "
                "limits to be disabled"
            )
        if generic_count_observability and not (
            self.budget.max_model_calls is None
            and self.budget.max_tool_calls is None
        ):
            raise ValueError(
                "D-081 generic readiness requires both model and tool call "
                "limits to be disabled"
            )
        if (
            count_limits_disabled
            and not (
                self.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
                or generic_count_observability
            )
        ):
            raise ValueError(
                "disabled model/tool call limits are reserved for an exact "
                "registered observability profile"
            )

        if self.purpose == ExperimentPurpose.OFFLINE_SMOKE:
            if self.schema_version == "experiment-v2" and self.model != "mock":
                raise ValueError("offline-smoke purpose requires model=mock")
            return self

        if self.seed != 20260723:
            raise ValueError("research campaigns require seed 20260723")
        if (
            self.experiment_id == COVERAGE_REVIEW_PILOT_EXPERIMENT_ID
            and self.purpose
            != ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        ):
            raise ValueError(
                "the D-070 experiment id requires the coverage-review pilot purpose"
            )
        if (
            self.experiment_id == COVERAGE_REJECTION_PILOT_EXPERIMENT_ID
            and self.purpose
            != ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        ):
            raise ValueError(
                "the D-072 experiment id requires the coverage-rejection pilot purpose"
            )

        if self.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS:
            expected_budget = (
                GENERIC_BASELINE_READINESS_BUDGET_BY_EXPERIMENT_ID.get(
                    self.experiment_id
                )
            )
            expected_cost = GENERIC_BASELINE_READINESS_COST_BY_EXPERIMENT_ID.get(
                self.experiment_id
            )
            if (
                expected_budget is None
                or expected_cost is None
                or [_normalized_task_path(task) for task in self.tasks]
                != GENERIC_BASELINE_READINESS_TASKS
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
                or self.transport_max_retries != 0
                or self.live_cost_approved is not False
                or self.approved_execution_hash is not None
                or self.pilot_run_id is not None
            ):
                raise ValueError(
                    "generic baseline readiness requires an exact registered id, "
                    "ordered four-task panel, no_memory, one repetition, "
                    "transport_max_retries=0, and no embedded approval or pilot"
                )
            assert expected_budget is not None
            assert expected_cost is not None
            estimated_cost, cost_limit = expected_cost
            self._require_live_defaults(
                cost_limit=cost_limit,
                budget=expected_budget,
            )
            if self.estimated_cost_usd != estimated_cost:
                raise ValueError(
                    "generic baseline readiness requires "
                    f"estimated_cost_usd={estimated_cost:g} for its exact id"
                )
        elif self.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE:
            if (
                self.experiment_id != WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID
                or [_normalized_task_path(task) for task in self.tasks]
                != [WORKFLOW_COMPLETION_PROBE_TASK]
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
                or self.transport_max_retries != 0
                or self.live_cost_approved is not False
                or self.approved_execution_hash is not None
                or self.pilot_run_id is not None
            ):
                raise ValueError(
                    "workflow completion probe requires its exact registered id, "
                    "single pyfakefs task, no_memory, one repetition, "
                    "transport_max_retries=0, and no embedded approval or pilot"
                )
            self._require_live_defaults(
                cost_limit=WORKFLOW_COMPLETION_PROBE_COST_LIMIT_USD,
                budget=GPT54_MINI_WORKFLOW_COMPLETION_PROBE_BUDGET,
            )
            if (
                self.estimated_cost_usd
                != WORKFLOW_COMPLETION_PROBE_ESTIMATED_COST_USD
            ):
                raise ValueError(
                    "workflow completion probe requires "
                    "estimated_cost_usd=13.6125"
                )
        elif self.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT:
            normalized_tasks = {
                _normalized_task_path(task) for task in self.tasks
            }
            completion_panel = (
                self.experiment_id
                not in SINGLE_TASK_LIVE_EXPERIMENT_IDS
            )
            expected_tasks = (
                COMPLETION_PANEL_TASKS if completion_panel else {PILOT_TASK}
            )
            if (
                normalized_tasks != expected_tasks
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "development-validation live pilot requires its exact frozen "
                    "task set, no_memory, and one repetition"
                )
            if self.experiment_id in HISTORICAL_TERRA_PILOT_EXPERIMENT_IDS:
                self._require_live_defaults(
                    cost_limit=2,
                    model_id=LEGACY_TERRA_MODEL_ID,
                    budget=Budget(),
                    max_output_tokens=4096,
                )
            elif (
                self.experiment_id
                in HISTORICAL_MINI_CAMPAIGN_EXPERIMENT_IDS
            ):
                self._require_live_defaults(
                    cost_limit=2,
                    model_id=GPT54_MINI_PILOT_MODEL_ID,
                    budget=GPT54_MINI_D037_TAIL_RESERVE_BUDGET,
                    max_output_tokens=(
                        GPT54_MINI_D037_CORRECTIVE_MAX_OUTPUT_TOKENS
                    ),
                )
            elif self.experiment_id in CONSUMED_CURRENT_LIVE_EXPERIMENT_IDS:
                self._require_live_defaults(
                    cost_limit=2,
                    model_id=GPT54_MINI_PILOT_MODEL_ID,
                    budget=GPT54_MINI_HISTORICAL_200K_CAMPAIGN_BUDGET,
                    max_output_tokens=(
                        GPT54_MINI_D037_CORRECTIVE_MAX_OUTPUT_TOKENS
                    ),
                )
            elif (
                self.experiment_id
                in SUPERSEDED_UNEXECUTED_LIVE_EXPERIMENT_IDS
            ):
                self._require_live_defaults(
                    cost_limit=2,
                    model_id=GPT54_MINI_PILOT_MODEL_ID,
                    budget=GPT54_MINI_CAMPAIGN_BUDGET,
                    max_output_tokens=(
                        GPT54_MINI_D037_CORRECTIVE_MAX_OUTPUT_TOKENS
                    ),
                )
            elif completion_panel:
                self._require_live_defaults(
                    cost_limit=6,
                    model_id=GPT54_MINI_PILOT_MODEL_ID,
                    budget=GPT54_MINI_COMPLETION_BUDGET,
                    max_output_tokens=(
                        GPT54_MINI_D037_CORRECTIVE_MAX_OUTPUT_TOKENS
                    ),
                )
        elif (
            self.purpose
            == ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT
        ):
            if (
                [_normalized_task_path(task) for task in self.tasks] != [PILOT_TASK]
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "development-validation model-candidate pilot requires exactly "
                    "the frozen Babel task, no_memory, and one repetition"
                )
            diagnostic_profile = (
                self.diagnostic.profile
                if self.diagnostic is not None
                else None
            )
            if diagnostic_profile in {
                "d037-rejected-patch-retry-v2",
                "d037-rejected-patch-retry-v3",
                "d037-rejected-patch-retry-v4",
            }:
                corrective_budget = (
                    GPT54_MINI_D037_TAIL_RESERVE_BUDGET
                    if diagnostic_profile
                    in {
                        "d037-rejected-patch-retry-v3",
                        "d037-rejected-patch-retry-v4",
                    }
                    else GPT54_MINI_D037_CORRECTIVE_BUDGET
                )
                self._require_live_defaults(
                    cost_limit=2,
                    model_id=GPT54_MINI_PILOT_MODEL_ID,
                    budget=corrective_budget,
                    max_output_tokens=(
                        GPT54_MINI_D037_CORRECTIVE_MAX_OUTPUT_TOKENS
                    ),
                )
            else:
                self._require_live_defaults(
                    cost_limit=2,
                    model_id=GPT54_MINI_PILOT_MODEL_ID,
                    budget=GPT54_MINI_PILOT_BUDGET,
                    max_output_tokens=4096,
                )
        elif self.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY:
            if (
                {_normalized_task_path(task) for task in self.tasks}
                != MEMORY_DEVELOPMENT_TASKS
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 2
            ):
                raise ValueError(
                    "memory-development no-memory campaign requires the six frozen "
                    "development tasks, no_memory, and two repetitions"
                )
            self._require_live_defaults(
                cost_limit=20,
                budget=(
                    GPT54_MINI_HISTORICAL_200K_CAMPAIGN_BUDGET
                    if self.experiment_id in CONSUMED_CURRENT_LIVE_EXPERIMENT_IDS
                    else GPT54_MINI_CAMPAIGN_BUDGET
                ),
            )
        elif (
            self.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT
        ):
            if (
                {_normalized_task_path(task) for task in self.tasks}
                != MEMORY_DEVELOPMENT_BUDGET_PILOT_TASKS
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "memory-development no-memory budget pilot requires the exact "
                    "three frozen resource-max tasks, no_memory, and one repetition"
                )
            self._require_live_defaults(
                cost_limit=7,
                budget=GPT54_MINI_MEMORY_DEVELOPMENT_BUDGET_PILOT,
            )
        elif (
            self.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
        ):
            if (
                {_normalized_task_path(task) for task in self.tasks}
                != MEMORY_DEVELOPMENT_BUDGET_PILOT_TASKS
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "memory-development no-memory corrective pilot requires the "
                    "exact three frozen resource-max tasks, no_memory, and one "
                    "repetition"
                )
            self._require_live_defaults(
                cost_limit=13,
                budget=GPT54_MINI_MEMORY_DEVELOPMENT_CORRECTIVE_PILOT,
            )
        elif (
            self.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
        ):
            if (
                [_normalized_task_path(task) for task in self.tasks]
                != [SATURATION_PILOT_TASK]
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "memory-development no-memory saturation pilot requires "
                    "exactly the frozen HF Hub task, no_memory, and one repetition"
                )
            if (
                self.diagnostic is None
                or self.diagnostic.profile != "v8-saturation-context-v1"
                or self.diagnostic.required_trace_features
                != ["saturation_context"]
            ):
                raise ValueError(
                    "saturation pilot requires the exact v8 saturation diagnostic"
                )
            self._require_live_defaults(
                cost_limit=5,
                budget=GPT54_MINI_MEMORY_DEVELOPMENT_SATURATION_PILOT,
            )
            if self.estimated_cost_usd != 4.1625:
                raise ValueError(
                    "saturation pilot requires estimated_cost_usd=4.1625"
                )
        elif (
            self.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
        ):
            if (
                [_normalized_task_path(task) for task in self.tasks]
                != [REVIEW_EVIDENCE_PILOT_TASK]
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "memory-development no-memory review-evidence pilot requires "
                    "exactly the frozen HF Hub task, no_memory, and one repetition"
                )
            self._require_live_defaults(
                cost_limit=6,
                budget=GPT54_MINI_MEMORY_DEVELOPMENT_REVIEW_EVIDENCE_PILOT,
            )
            if self.estimated_cost_usd != 5.5125:
                raise ValueError(
                    "review-evidence pilot requires estimated_cost_usd=5.5125"
                )
        elif (
            self.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        ):
            if (
                self.experiment_id != COVERAGE_REVIEW_PILOT_EXPERIMENT_ID
                or [_normalized_task_path(task) for task in self.tasks]
                != [COVERAGE_REVIEW_PILOT_TASK]
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "memory-development no-memory coverage-review pilot requires "
                    "the exact D-070 id and frozen HF Hub task, no_memory, and "
                    "one repetition"
                )
            self._require_live_defaults(
                cost_limit=6,
                budget=GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REVIEW_PILOT,
            )
            if self.estimated_cost_usd != 5.5125:
                raise ValueError(
                    "coverage-review pilot requires estimated_cost_usd=5.5125"
                )
        elif (
            self.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        ):
            if (
                self.experiment_id != COVERAGE_REJECTION_PILOT_EXPERIMENT_ID
                or [_normalized_task_path(task) for task in self.tasks]
                != [COVERAGE_REJECTION_PILOT_TASK]
                or self.conditions != [MemoryCondition.NO_MEMORY]
                or self.repetitions != 1
            ):
                raise ValueError(
                    "memory-development no-memory coverage-rejection pilot requires "
                    "the exact D-072 id and frozen HF Hub task, no_memory, and "
                    "one repetition"
                )
            self._require_live_defaults(
                cost_limit=6,
                budget=GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REJECTION_PILOT,
            )
            if self.estimated_cost_usd != 5.5125:
                raise ValueError(
                    "coverage-rejection pilot requires estimated_cost_usd=5.5125"
                )
        elif self.purpose == ExperimentPurpose.CORE:
            if len(set(self.tasks)) != 12:
                raise ValueError("core experiment requires exactly 12 unique held-out tasks")
            if set(self.conditions) != set(MemoryCondition):
                raise ValueError("core experiment requires all four memory conditions")
            if self.repetitions != 2:
                raise ValueError("core experiment requires two repetitions")
            if self.embedding_revision == "PIN_AT_FREEZE":
                raise ValueError("core experiment requires a pinned embedding revision")
            if self.schema_version == "experiment-v2":
                self._require_live_defaults(cost_limit=150)
        if self.dataset_manifest_hash is None:
            raise ValueError("research campaign requires a frozen dataset manifest hash")
        return self

    def _require_live_defaults(
        self,
        *,
        cost_limit: float,
        model_id: str = CAMPAIGN_MODEL_ID,
        budget: Budget | None = None,
        max_output_tokens: int = CAMPAIGN_MAX_OUTPUT_TOKENS,
    ) -> None:
        if (
            self.model != "openai"
            or self.reasoning_effort != "medium"
            or self.reasoning_mode != "standard"
            or self.service_tier != "default"
        ):
            raise ValueError(
                "live research purpose requires OpenAI, medium reasoning, "
                "standard mode, and default service tier"
            )
        expected_budget = budget or CAMPAIGN_BUDGET
        if (
            self.model_id != model_id
            or self.budget != expected_budget
            or self.max_output_tokens != max_output_tokens
        ):
            raise ValueError(
                "live research purpose requires the frozen "
                f"{model_id} model/run-budget contract "
                f"(max_model_calls={expected_budget.max_model_calls}, "
                f"max_tool_calls={expected_budget.max_tool_calls}, "
                f"max_total_tokens={expected_budget.max_total_tokens}, "
                "wall_clock_timeout_seconds="
                f"{expected_budget.wall_clock_timeout_seconds}, "
                f"max_output_tokens={max_output_tokens})"
            )
        if self.cost_limit_usd != cost_limit:
            raise ValueError(
                f"{self.purpose.value} requires cost_limit_usd={cost_limit:g}"
            )


def load_suite(path: str | Path) -> ExperimentSuite:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    try:
        return ExperimentSuite.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"experiment contract validation failed: {exc}") from exc


def _validate_memory_index(index_payload: dict, suite: ExperimentSuite) -> None:
    if (
        not index_payload.get("entries")
        or index_payload["embedding"].get("implementation") != "sentence-transformers"
    ):
        raise ContractError("memory campaign requires a non-empty vectorized frozen index")
    if index_payload["embedding"].get("revision") != suite.embedding_revision:
        raise ContractError("experiment embedding revision does not match the frozen memory index")
    if (
        suite.purpose == ExperimentPurpose.CORE
        and index_payload.get("dataset_manifest_hash") != suite.dataset_manifest_hash
    ):
        raise ContractError(
            "frozen memory index dataset manifest hash does not match the core experiment"
        )


def _block(blockers: list[dict[str, str]], code: str, message: str) -> None:
    blockers.append({"code": code, "message": message})


def _campaign_journal_path(experiment_id: str) -> Path:
    return runtime_root() / "experiments" / "journals" / f"{experiment_id}.jsonl"


def _append_campaign_event(
    path: Path,
    *,
    sequence: int,
    previous_event_hash: str | None,
    event_type: str,
    payload: dict[str, Any],
) -> str:
    event = {
        "schema_version": "experiment-journal-event-v1",
        "sequence": sequence,
        "event_type": event_type,
        "recorded_at": utc_now().isoformat(),
        "previous_event_hash": previous_event_hash,
        "payload": payload,
    }
    event["event_hash"] = sha256_text(canonical_json(event))
    path.parent.mkdir(parents=True, exist_ok=True)
    exclusive_start = sequence == 1 and previous_event_hash is None
    try:
        with path.open(
            "x" if exclusive_start else "a",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            stream.write(canonical_json(event) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ContractError(
            "campaign journal already exists; refusing duplicate schedule ownership"
        ) from exc
    return str(event["event_hash"])


def _safe_error_message(error: Exception) -> str:
    message = str(error)
    for name in ("OPENAI_API_KEY",):
        secret = os.environ.get(name)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message[:2_000]


def _git_state() -> dict[str, Any]:
    commit_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "available": commit_result.returncode == 0 and status_result.returncode == 0,
        "commit": (
            commit_result.stdout.strip() if commit_result.returncode == 0 else "uncommitted"
        ),
        "clean": status_result.returncode == 0 and not status_result.stdout.strip(),
    }


def _docker_image_state(images: list[str]) -> dict[str, Any]:
    available = DockerSandbox.available()
    rows = []
    for image in sorted(set(images)):
        identity = DockerSandbox(image).image_identity() if available else None
        rows.append(
            {
                "image": image,
                "identity": identity,
                "ready": identity is not None,
            }
        )
    return {"available": available, "images": rows}


def _openai_sdk_state() -> dict[str, Any]:
    try:
        installed_version = version("openai")
    except PackageNotFoundError:
        installed_version = None
    return {"installed": installed_version is not None, "version": installed_version}


def _expected_runtime_contract_hash() -> str:
    content = json.dumps(
        {
            "system_prompt": SYSTEM_PROMPT_V3,
            "tools": TOOL_SCHEMAS_V2,
            "tool_schema_version": "v2",
            "context_policy_version": "phase-evidence-v5",
        },
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    return sha256_bytes(content.encode("utf-8"))


def _pilot_qualification(
    run_id: str | None,
    suite: ExperimentSuite,
    *,
    expected_harness_commit: str,
) -> dict[str, Any]:
    if run_id is None:
        return {"run_id": None, "qualified": False, "reason": "missing pilot_run_id"}
    try:
        from patchloop.evals.qualification import (
            calculate_source_evidence_hash,
            load_trace_qualification,
        )

        payload = load_trace_qualification(run_id, root=runtime_root())
        current_source_hash = calculate_source_evidence_hash(
            run_id,
            root=runtime_root(),
        )
    except (ContractError, FileNotFoundError) as exc:
        return {"run_id": run_id, "qualified": False, "reason": str(exc)}
    recorded_source_hash = payload["source_evidence_hash"]
    if not hmac.compare_digest(recorded_source_hash, current_source_hash):
        return {
            "run_id": run_id,
            "qualified": False,
            "qualification_hash": payload.get("qualification_hash"),
            "reason": "pilot source evidence hash mismatch",
        }
    expected_runtime_hash = _expected_runtime_contract_hash()
    contract_mismatches = [
        field
        for field, actual, expected in (
            ("schema_version", payload.get("schema_version"), "trace-qualification-v2"),
            ("model_provider", payload.get("model_provider"), "openai"),
            ("model_id", payload.get("model_id"), suite.model_id),
            (
                "reasoning_effort",
                payload.get("reasoning_effort"),
                suite.reasoning_effort,
            ),
            (
                "reasoning_mode",
                payload.get("reasoning_mode"),
                suite.reasoning_mode,
            ),
            ("service_tier", payload.get("service_tier"), suite.service_tier),
            (
                "max_output_tokens",
                payload.get("max_output_tokens"),
                suite.max_output_tokens,
            ),
            (
                "budget",
                payload.get("budget"),
                suite.budget.model_dump(mode="json"),
            ),
            (
                "harness_git_commit",
                payload.get("harness_git_commit"),
                expected_harness_commit,
            ),
            ("tool_schema_version", payload.get("tool_schema_version"), "v2"),
            (
                "context_policy_version",
                payload.get("context_policy_version"),
                "phase-evidence-v5",
            ),
            (
                "runtime_contract_content_hash",
                payload.get("runtime_contract_content_hash"),
                expected_runtime_hash,
            ),
            (
                "memory_condition",
                payload.get("memory_condition"),
                MemoryCondition.NO_MEMORY.value,
            ),
            ("fault_type", payload.get("fault_type"), "none"),
        )
        if actual != expected
    ]
    evidence_required = (
        payload.get("purpose")
        == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value
        and payload.get("qualified") is True
        and payload.get("trace_integrity_passed") is True
        and payload.get("leakage_scan_passed") is True
        and payload.get("evaluation_reached") is True
    )
    required = evidence_required and not contract_mismatches
    return {
        "run_id": run_id,
        "qualified": required,
        "qualification_hash": payload.get("qualification_hash"),
        "source_evidence_hash": recorded_source_hash,
        "purpose": payload.get("purpose"),
        "outcome_kind": payload.get("outcome_kind"),
        "runtime_contract_content_hash": payload.get(
            "runtime_contract_content_hash"
        ),
        "expected_runtime_contract_content_hash": expected_runtime_hash,
        "contract_mismatches": contract_mismatches,
        "reason": (
            None
            if required
            else (
                "pilot runtime/model contract mismatch: "
                + ", ".join(contract_mismatches)
                if contract_mismatches
                else "pilot evidence requirements are not satisfied"
            )
        ),
    }


def _suite_hash(suite: ExperimentSuite) -> str:
    return sha256_text(canonical_json(_suite_payload(suite)))


def _diagnostic_fault(suite: ExperimentSuite) -> FaultSpec:
    if (
        suite.diagnostic is not None
        and suite.diagnostic.profile
        == "d037-rejected-patch-retry-v4"
    ):
        return FaultSpec(
            type="controlled-reject-first-prepared-patch",
            trigger_after=1,
        )
    return FaultSpec()


def _suite_payload(suite: ExperimentSuite) -> dict[str, Any]:
    """Preserve historical suite identities when the new field is absent."""

    payload = suite.model_dump(mode="json")
    if payload.get("diagnostic") is None:
        payload.pop("diagnostic", None)
    if payload.get("transport_max_retries") is None:
        payload.pop("transport_max_retries", None)
    return payload


def _execution_hash(
    suite: ExperimentSuite,
    *,
    dataset: dict[str, Any] | None,
    task_rows: list[dict[str, Any]],
    schedule_hash: str,
    git_state: dict[str, Any],
    docker_state: dict[str, Any],
    openai_sdk: dict[str, Any],
    pilot_qualification: dict[str, Any],
    runtime_contract: dict[str, Any] | None = None,
) -> str:
    payload = _suite_payload(suite)
    payload.pop("live_cost_approved", None)
    payload.pop("approved_execution_hash", None)
    execution_payload: dict[str, Any] = {
        "schema_version": "experiment-execution-v1",
        "suite": payload,
        "dataset": dataset,
        "tasks": task_rows,
        "schedule_hash": schedule_hash,
        "git_commit": git_state.get("commit"),
        "docker_images": docker_state.get("images", []),
        "openai_sdk": openai_sdk,
        "pilot_qualification_hash": pilot_qualification.get(
            "qualification_hash"
        ),
    }
    if runtime_contract is not None:
        execution_payload["runtime_contract"] = runtime_contract
    return sha256_text(
        canonical_json(execution_payload)
    )


def _make_schedule(
    suite: ExperimentSuite,
    task_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    schedule = [
        {
            "task": row["task"],
            "task_id": row["task_id"],
            "task_version": row["task_version"],
            "split": row["split"],
            "dataset_role": row["dataset_role"],
            "evaluator_image_digest": row["evaluator_image_digest"],
            "condition": condition.value,
            "repetition": repetition,
        }
        for row in task_rows
        for condition in suite.conditions
        for repetition in range(1, suite.repetitions + 1)
    ]
    random.Random(suite.seed).shuffle(schedule)
    for order, row in enumerate(schedule, 1):
        row["order"] = order
        row["schedule_row_id"] = sha256_text(
            canonical_json(
                {
                    "experiment_id": suite.experiment_id,
                    "purpose": suite.purpose.value if suite.purpose else None,
                    **row,
                }
            )
        )
    return schedule, sha256_text(canonical_json(schedule))


def _expected_role_and_split(
    purpose: ExperimentPurpose,
    split: str,
) -> tuple[set[DatasetRole], DatasetRole | None]:
    if purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS:
        expected = {
            "dev-validation": DatasetRole.DEVELOPMENT_VALIDATION,
            "dev-train": DatasetRole.MEMORY_DEVELOPMENT,
        }.get(split)
        return {
            DatasetRole.DEVELOPMENT_VALIDATION,
            DatasetRole.MEMORY_DEVELOPMENT,
        }, expected
    if purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE:
        return {DatasetRole.MEMORY_DEVELOPMENT}, DatasetRole.MEMORY_DEVELOPMENT
    if purpose in {
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
    }:
        return {DatasetRole.DEVELOPMENT_VALIDATION}, DatasetRole.DEVELOPMENT_VALIDATION
    if purpose in {
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT,
    }:
        return {DatasetRole.MEMORY_DEVELOPMENT}, DatasetRole.MEMORY_DEVELOPMENT
    if purpose == ExperimentPurpose.CORE:
        expected = {
            "same-repo-heldout": DatasetRole.CORE_SAME_REPO,
            "cross-repo-heldout": DatasetRole.CORE_CROSS_REPO,
        }.get(split)
        return {DatasetRole.CORE_SAME_REPO, DatasetRole.CORE_CROSS_REPO}, expected
    return set(), None


def preflight_suite(
    path: str | Path,
    *,
    approve_live_cost: bool = False,
    approved_execution_hash: str | None = None,
) -> dict[str, Any]:
    """Inspect an experiment without constructing an agent or making API calls."""

    suite = load_suite(path)
    preflight_checked_at = utc_now()
    suite_hash = _suite_hash(suite)
    blockers: list[dict[str, str]] = []
    dataset_identity: dict[str, Any] | None = None
    dataset_manifest_path: Path | None = None
    task_rows: list[dict[str, Any]] = []

    requires_dataset = suite.purpose != ExperimentPurpose.OFFLINE_SMOKE
    if requires_dataset:
        try:
            dataset, actual_dataset_hash, dataset_manifest_path = require_frozen_dataset()
            dataset_identity = {
                "dataset_id": dataset.dataset_id,
                "manifest_hash": actual_dataset_hash,
            }
            if suite.dataset_manifest_hash != actual_dataset_hash:
                _block(
                    blockers,
                    "DATASET_HASH_MISMATCH",
                    "experiment dataset manifest hash does not match the current registry",
                )
        except ContractError as exc:
            _block(blockers, "DATASET_NOT_FROZEN", str(exc))

    if not requires_dataset or dataset_manifest_path is not None:
        for task in suite.tasks:
            try:
                task_path = Path(task)
                package = load_task_package(
                    task_path.parent if task_path.is_file() else task_path
                )
                role: DatasetRole | None = None
                if requires_dataset:
                    allowed_roles, expected_role = _expected_role_and_split(
                        suite.purpose, package.public.split
                    )
                    entry = require_dataset_role(
                        task_id=package.public.task_id,
                        task_version=package.public.task_version,
                        public_spec_hash=package.public_spec_hash,
                        allowed_roles=allowed_roles,
                        manifest_path=dataset_manifest_path,
                    )
                    canonical_task_root = ensure_within(
                        repository_root(), entry.path
                    ).resolve()
                    if Path(package.root).resolve() != canonical_task_root:
                        raise ContractError(
                            "suite task path does not match the frozen dataset package: "
                            f"{package.public.task_id}"
                        )
                    if package.private_spec_hash != entry.private_spec_hash:
                        raise ContractError(
                            "suite private evaluator does not match the frozen dataset entry: "
                            f"{package.public.task_id}"
                        )
                    if package.environment is None:
                        raise ContractError(
                            "research task requires a digest-pinned evaluator environment: "
                            f"{package.public.task_id}"
                        )
                    role = entry.role
                    if expected_role is None:
                        raise ContractError(
                            f"{suite.purpose.value} task has an ineligible split: "
                            f"{package.public.task_id}@{package.public.split}"
                        )
                    if role != expected_role:
                        raise ContractError(
                            f"task role/split mismatch for {package.public.task_id}: "
                            f"{role.value} != {expected_role.value}"
                        )
                review_contract: PublicReviewContract | None = None
                review_contract_path: str | None = None
                if (
                    suite.purpose in HASH_BOUND_CORRECTIVE_PURPOSES
                ):
                    review_contract_root = (
                        PUBLIC_REVIEW_CONTRACT_V2_ROOT
                        if suite.purpose
                        in {
                            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
                            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT,
                        }
                        else PUBLIC_REVIEW_CONTRACT_ROOT
                    )
                    candidate = ensure_within(
                        repository_root(),
                        (
                            review_contract_root
                            / f"{package.public.task_id}.yaml"
                        ).as_posix(),
                    )
                    review_contract = load_public_review_contract(
                        candidate,
                        task=package.public,
                        public_spec_hash=package.public_spec_hash,
                    )
                    review_contract_path = candidate.relative_to(
                        repository_root()
                    ).as_posix()
                task_row = {
                        "task": task,
                        "task_id": package.public.task_id,
                        "task_version": package.public.task_version,
                        "split": package.public.split,
                        "dataset_role": role.value if role else None,
                        "canonical_task_path": entry.path if requires_dataset else None,
                        "public_spec_hash": package.public_spec_hash,
                        "private_spec_hash": package.private_spec_hash,
                        "base_commit": package.public.repository.base_commit,
                        "evaluator_image": (
                            package.environment.evaluator_image
                            if package.environment is not None
                            else None
                        ),
                        "evaluator_image_digest": (
                            package.environment.image_digest
                            if package.environment is not None
                            else None
                        ),
                    }
                if review_contract is not None:
                    task_row.update(
                        {
                            "public_review_contract_path": review_contract_path,
                            "public_review_contract": review_contract.model_dump(
                                mode="json"
                            ),
                        }
                    )
                task_rows.append(task_row)
            except (ContractError, OSError) as exc:
                _block(blockers, "TASK_NOT_ELIGIBLE", str(exc))

    loaded_ids = {row["task_id"] for row in task_rows}
    if len(loaded_ids) != len(task_rows):
        _block(
            blockers,
            "DUPLICATE_TASK_IDENTITY",
            "experiment task paths must resolve to unique task identities",
        )
    if (
        suite.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS
        and loaded_ids != GENERIC_BASELINE_READINESS_TASK_IDS
    ):
        _block(
            blockers,
            "GENERIC_BASELINE_READINESS_TASK_SET_MISMATCH",
            "generic baseline readiness must use exactly the frozen four-task panel",
        )
    if (
        suite.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        and loaded_ids != {WORKFLOW_COMPLETION_PROBE_TASK_ID}
    ):
        _block(
            blockers,
            "WORKFLOW_COMPLETION_PROBE_TASK_MISMATCH",
            "workflow completion probe must use exactly the frozen pyfakefs task",
        )
    expected_live_pilot_ids = (
        COMPLETION_PANEL_TASK_IDS
        if (
            suite.purpose
            == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
            and {
                _normalized_task_path(task) for task in suite.tasks
            }
            == COMPLETION_PANEL_TASKS
        )
        else {PILOT_TASK_ID}
    )
    if (
        suite.purpose
        in {
            ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
            ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        }
        and loaded_ids != expected_live_pilot_ids
    ):
        _block(
            blockers,
            "PILOT_TASK_MISMATCH",
            "live pilot must use its exact frozen development-validation task set",
        )
    if (
        suite.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        and loaded_ids != MEMORY_DEVELOPMENT_TASK_IDS
    ):
        _block(
            blockers,
            "DEVELOPMENT_TASK_SET_MISMATCH",
            "development campaign must use all six frozen memory-development tasks",
        )
    if (
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT
        and loaded_ids != MEMORY_DEVELOPMENT_BUDGET_PILOT_TASK_IDS
    ):
        _block(
            blockers,
            "BUDGET_PILOT_TASK_SET_MISMATCH",
            "budget pilot must use its exact three frozen resource-max tasks",
        )
    if (
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
        and loaded_ids != MEMORY_DEVELOPMENT_BUDGET_PILOT_TASK_IDS
    ):
        _block(
            blockers,
            "CORRECTIVE_PILOT_TASK_SET_MISMATCH",
            "corrective pilot must use its exact three frozen resource-max tasks",
        )
    if (
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
        and loaded_ids != {SATURATION_PILOT_TASK_ID}
    ):
        _block(
            blockers,
            "SATURATION_PILOT_TASK_SET_MISMATCH",
            "saturation pilot must use exactly the frozen HF Hub task",
        )
    if (
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
        and loaded_ids != {REVIEW_EVIDENCE_PILOT_TASK_ID}
    ):
        _block(
            blockers,
            "REVIEW_EVIDENCE_PILOT_TASK_SET_MISMATCH",
            "review-evidence pilot must use exactly the frozen HF Hub task",
        )
    if (
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        and loaded_ids != {COVERAGE_REVIEW_PILOT_TASK_ID}
    ):
        _block(
            blockers,
            "COVERAGE_REVIEW_PILOT_TASK_SET_MISMATCH",
            "coverage-review pilot must use exactly the frozen HF Hub task",
        )
    if (
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        and loaded_ids != {COVERAGE_REJECTION_PILOT_TASK_ID}
    ):
        _block(
            blockers,
            "COVERAGE_REJECTION_PILOT_TASK_SET_MISMATCH",
            "coverage-rejection pilot must use exactly the frozen HF Hub task",
        )

    schedule, schedule_hash = _make_schedule(suite, task_rows)
    git_state = _git_state()
    docker_images = [
        row["evaluator_image"] for row in task_rows if row["evaluator_image"] is not None
    ]
    docker_state = (
        _docker_image_state(docker_images)
        if suite.model == "openai"
        else {"available": None, "images": []}
    )
    openai_sdk = (
        _openai_sdk_state()
        if suite.model == "openai"
        else {"installed": None, "version": None}
    )
    credential = {
        "name": "OPENAI_API_KEY",
        "present": bool(os.environ.get("OPENAI_API_KEY")),
        "custom_base_url_present": bool(
            os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
        ),
    }
    pilot_qualification = (
        _pilot_qualification(
            suite.pilot_run_id,
            suite,
            expected_harness_commit=str(git_state.get("commit")),
        )
        if suite.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        else {"run_id": None, "qualified": None}
    )
    runtime_contract = _experiment_runtime_contract(
        suite,
        harness_git_commit=git_state.get("commit"),
    )
    execution_hash = _execution_hash(
        suite,
        dataset=dataset_identity,
        task_rows=task_rows,
        schedule_hash=schedule_hash,
        git_state=git_state,
        docker_state=docker_state,
        openai_sdk=openai_sdk,
        pilot_qualification=pilot_qualification,
        runtime_contract=runtime_contract,
    )

    expected_prices = OFFICIAL_PRICES_BY_MODEL.get(suite.model_id)
    pricing = _pricing_contract(
        suite,
        schedule_size=len(schedule),
        checked_at=preflight_checked_at,
    )
    theoretical_cost_upper_bound = pricing["budget_upper_bound_usd"]

    if suite.model == "openai":
        if (
            suite.experiment_id
            in SUPERSEDED_UNEXECUTED_LIVE_EXPERIMENT_IDS
        ):
            _block(
                blockers,
                "SUPERSEDED_SUITE",
                "this unexecuted 250k pilot was superseded by the high-budget "
                "completion calibration and must not be run",
            )
        if (
            suite.experiment_id
            in HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
        ):
            _block(
                blockers,
                "HISTORICAL_SUITE_IMMUTABLE",
                "this terminal historical suite is inspectable but must never be rerun",
            )
        if suite.schema_version != "experiment-v2":
            _block(
                blockers,
                "LIVE_SUITE_VERSION_UNSUPPORTED",
                "paid execution requires an experiment-v2 suite",
            )
        if not credential["present"]:
            _block(blockers, "OPENAI_API_KEY_MISSING", "OPENAI_API_KEY is not present")
        if credential["custom_base_url_present"]:
            _block(
                blockers,
                "CUSTOM_OPENAI_BASE_URL_FORBIDDEN",
                "OPENAI_BASE_URL and OPENAI_API_BASE must be unset for official pricing",
            )
        if not openai_sdk["installed"]:
            _block(
                blockers,
                "OPENAI_SDK_MISSING",
                "the official OpenAI Python SDK is not installed",
            )
        if not git_state["available"] or git_state["commit"] == "uncommitted":
            _block(blockers, "GIT_COMMIT_UNAVAILABLE", "Git commit identity is unavailable")
        elif not git_state["clean"]:
            _block(blockers, "GIT_WORKTREE_DIRTY", "live campaign requires a clean worktree")
        if not docker_state["available"]:
            _block(blockers, "DOCKER_UNAVAILABLE", "Docker server is unavailable")
        for image in docker_state["images"]:
            if not image["ready"]:
                _block(
                    blockers,
                    "DOCKER_IMAGE_UNAVAILABLE",
                    f"required evaluator image is unavailable: {image['image']}",
                )
            elif image["identity"] != image["image"].rsplit("@", 1)[-1]:
                _block(
                    blockers,
                    "DOCKER_IMAGE_DIGEST_MISMATCH",
                    f"required evaluator image has the wrong identity: {image['image']}",
                )

        if suite.pricing_source_url != OFFICIAL_PRICING_URL:
            _block(
                blockers,
                "PRICING_SOURCE_INVALID",
                f"pricing source must be {OFFICIAL_PRICING_URL}",
            )
        if suite.pricing_verified_at is None:
            _block(blockers, "PRICING_DATE_MISSING", "pricing verification date is missing")
        else:
            verified_at = suite.pricing_verified_at
            if verified_at.tzinfo is None:
                _block(
                    blockers,
                    "PRICING_TIMEZONE_MISSING",
                    "pricing verification date must include an explicit timezone",
                )
            else:
                age = preflight_checked_at.astimezone(
                    UTC
                ) - verified_at.astimezone(UTC)
                if age < timedelta(0):
                    _block(
                        blockers,
                        "PRICING_DATE_FUTURE",
                        "pricing verification date is in the future",
                    )
                elif age > PRICING_MAX_AGE:
                    _block(
                        blockers,
                        "PRICING_STALE",
                        "pricing verification is older than 72 hours",
                    )
        if expected_prices is None:
            _block(
                blockers,
                "MODEL_PRICING_UNSUPPORTED",
                f"no verified pricing contract exists for {suite.model_id}",
            )
        for field in PRICE_FIELDS:
            expected = expected_prices.get(field) if expected_prices is not None else None
            if getattr(suite, field) != expected:
                _block(
                    blockers,
                    "PRICING_RATE_MISMATCH",
                    f"{field} must equal the verified {suite.model_id} rate "
                    f"{expected if expected is not None else 'null'}",
                )
        if suite.estimated_cost_usd <= 0:
            _block(
                blockers,
                "COST_ESTIMATE_MISSING",
                "live campaign requires a positive estimated_cost_usd",
            )
        if suite.estimated_cost_usd > suite.cost_limit_usd:
            _block(
                blockers,
                "COST_ESTIMATE_EXCEEDS_LIMIT",
                "estimated campaign cost exceeds cost_limit_usd",
            )
        if theoretical_cost_upper_bound > suite.cost_limit_usd:
            _block(
                blockers,
                "TOKEN_BUDGET_EXCEEDS_COST_LIMIT",
                "the frozen token budget can exceed the campaign cost limit",
            )
        if not approve_live_cost:
            _block(
                blockers,
                "LIVE_COST_NOT_APPROVED",
                "paid execution requires the explicit --approve-live-cost invocation flag",
            )
        if approved_execution_hash != execution_hash:
            _block(
                blockers,
                "APPROVAL_HASH_MISMATCH",
                "the invocation's approved execution hash does not match this exact execution",
            )

    if (
        suite.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        and not pilot_qualification["qualified"]
    ):
        _block(
            blockers,
            "QUALIFIED_PILOT_REQUIRED",
            "memory-development campaign requires a qualified live pilot_run_id",
        )

    if any(condition != MemoryCondition.NO_MEMORY for condition in suite.conditions):
        frozen_index = latest_frozen_index()
        if frozen_index is None:
            _block(
                blockers,
                "FROZEN_MEMORY_INDEX_MISSING",
                "memory conditions require one frozen dev-train index",
            )
        else:
            try:
                index_payload = json.loads(frozen_index.read_text(encoding="utf-8"))
                _validate_memory_index(index_payload, suite)
            except (ContractError, OSError, json.JSONDecodeError) as exc:
                _block(blockers, "FROZEN_MEMORY_INDEX_INVALID", str(exc))

    output = runtime_root() / "experiments" / f"{suite.experiment_id}.json"
    journal = _campaign_journal_path(suite.experiment_id)
    if output.exists():
        _block(
            blockers,
            "EXPERIMENT_RESULT_EXISTS",
            f"immutable experiment result already exists: {output}",
        )
    if journal.exists():
        _block(
            blockers,
            "EXPERIMENT_JOURNAL_EXISTS",
            "an append-only campaign journal already exists; inspect or recover it "
            "instead of starting the schedule again",
        )

    output_payload = {
        "schema_version": "experiment-preflight-v1",
        "experiment_id": suite.experiment_id,
        "purpose": suite.purpose.value,
        "suite": _suite_payload(suite),
        "suite_hash": suite_hash,
        "execution_hash": execution_hash,
        "schedule_hash": schedule_hash,
        "expected_runs": len(schedule),
        "dataset": dataset_identity,
        "tasks": task_rows,
        "schedule": schedule,
        "environment": {
            "git": git_state,
            "docker": docker_state,
            "openai_sdk": openai_sdk,
            "credential": credential,
        },
        "pricing": pricing,
        "approval": {
            "suite_live_cost_approved_deprecated": suite.live_cost_approved,
            "suite_approved_execution_hash_deprecated": suite.approved_execution_hash,
            "invocation_approve_live_cost": approve_live_cost,
            "invocation_approved_execution_hash": approved_execution_hash,
            "matches_execution_hash": approved_execution_hash == execution_hash,
        },
        "pilot_qualification": pilot_qualification,
        "journal_path": str(journal),
        "blockers": blockers,
        "ready": not blockers,
    }
    if runtime_contract is not None:
        output_payload["runtime_contract"] = runtime_contract
    return output_payload


def _persisted_attempt_result(runner: AgentRunner, run_id: str) -> dict | None:
    for row in runner.state.list_runs():
        if row["run_id"] == run_id:
            return row.get("result")
    return None


def _assert_task_package_matches_preflight(
    package: TaskPackage,
    task_row: dict[str, Any],
) -> None:
    environment = package.environment
    actual = {
        "task_id": package.public.task_id,
        "task_version": package.public.task_version,
        "split": package.public.split,
        "public_spec_hash": package.public_spec_hash,
        "private_spec_hash": package.private_spec_hash,
        "base_commit": package.public.repository.base_commit,
        "evaluator_image": (
            environment.evaluator_image if environment is not None else None
        ),
        "evaluator_image_digest": (
            environment.image_digest if environment is not None else None
        ),
    }
    expected = {key: task_row[key] for key in actual}
    canonical_task_path = task_row.get("canonical_task_path")
    canonical_path_matches = (
        canonical_task_path is None
        or Path(package.root).resolve()
        == ensure_within(repository_root(), canonical_task_path).resolve()
    )
    if actual != expected or not canonical_path_matches:
        raise ContractError(
            "task package changed since the approved preflight: "
            f"{task_row['task_id']}"
        )
    review_path = task_row.get("public_review_contract_path")
    expected_review = task_row.get("public_review_contract")
    if review_path is not None or expected_review is not None:
        if not isinstance(review_path, str) or not isinstance(
            expected_review, dict
        ):
            raise ContractError("invalid approved public review contract binding")
        observed_review = load_public_review_contract(
            ensure_within(repository_root(), review_path),
            task=package.public,
            public_spec_hash=package.public_spec_hash,
        )
        if observed_review.model_dump(mode="json") != expected_review:
            raise ContractError(
                "public review contract changed since the approved preflight: "
                f"{task_row['task_id']}"
            )


def _assert_manifest_matches_preflight(
    manifest: RunManifest,
    *,
    suite: ExperimentSuite,
    preflight: dict[str, Any],
    item: dict[str, Any],
) -> None:
    expected_runtime_contract = preflight.get("runtime_contract")
    actual_runtime_contract: dict[str, Any] | None = None
    if (
        isinstance(expected_runtime_contract, dict)
        and expected_runtime_contract.get("schema_version")
        in {
            GENERIC_BASELINE_RUNTIME_CONTRACT_SCHEMA,
            GENERIC_BASELINE_OBSERVABILITY_RUNTIME_CONTRACT_SCHEMA,
        }
    ):
        count_observability = bool(
            expected_runtime_contract.get("schema_version")
            == GENERIC_BASELINE_OBSERVABILITY_RUNTIME_CONTRACT_SCHEMA
        )
        actual_runtime_contract = {
            "schema_version": expected_runtime_contract.get("schema_version"),
            "tool_schema_version": manifest.tool_schema_version,
            "context_policy_version": manifest.context_policy_version,
            "system_prompt_hash": sha256_text(SYSTEM_PROMPT_V3),
            "tool_schema_hash": sha256_text(canonical_json(TOOL_SCHEMAS_V2)),
            "transport_max_retries": manifest.model.transport_max_retries,
            **(
                {
                    "call_guard_policy": (
                        GENERIC_BASELINE_OBSERVABILITY_CALL_GUARD_POLICY
                    )
                }
                if count_observability
                else {}
            ),
            "harness_git_commit": manifest.harness_git_commit,
        }
    elif (
        isinstance(expected_runtime_contract, dict)
        and expected_runtime_contract.get("schema_version")
        == WORKFLOW_COMPLETION_RUNTIME_CONTRACT_SCHEMA
    ):
        actual_runtime_contract = {
            "schema_version": WORKFLOW_COMPLETION_RUNTIME_CONTRACT_SCHEMA,
            "tool_schema_version": manifest.tool_schema_version,
            "context_policy_version": manifest.context_policy_version,
            "system_prompt_hash": sha256_text(SYSTEM_PROMPT_V3),
            "tool_schema_hash": sha256_text(canonical_json(TOOL_SCHEMAS_V2)),
            "transport_max_retries": manifest.model.transport_max_retries,
            "call_guard_policy": WORKFLOW_COMPLETION_CALL_GUARD_POLICY,
            "harness_git_commit": manifest.harness_git_commit,
        }
    elif (
        expected_runtime_contract is not None
        or manifest.tool_schema_version
        in {
            CORRECTIVE_TOOL_SCHEMA_VERSION,
            COVERAGE_REVIEW_TOOL_SCHEMA_VERSION,
            COVERAGE_REJECTION_TOOL_SCHEMA_VERSION,
        }
        or manifest.context_policy_version
        in {
            CORRECTIVE_CONTEXT_POLICY_VERSION,
            SATURATION_CONTEXT_POLICY_VERSION,
            REVIEW_EVIDENCE_CONTEXT_POLICY_VERSION,
            COVERAGE_REVIEW_CONTEXT_POLICY_VERSION,
            COVERAGE_REJECTION_CONTEXT_POLICY_VERSION,
        }
        or manifest.public_review_contract is not None
    ):
        actual_runtime_contract = {
            "schema_version": (
                COVERAGE_REJECTION_RUNTIME_CONTRACT_SCHEMA
                if manifest.context_policy_version
                == COVERAGE_REJECTION_CONTEXT_POLICY_VERSION
                else COVERAGE_REVIEW_RUNTIME_CONTRACT_SCHEMA
                if manifest.context_policy_version
                == COVERAGE_REVIEW_CONTEXT_POLICY_VERSION
                else REVIEW_EVIDENCE_RUNTIME_CONTRACT_SCHEMA
                if manifest.context_policy_version
                == REVIEW_EVIDENCE_CONTEXT_POLICY_VERSION
                else SATURATION_RUNTIME_CONTRACT_SCHEMA
                if manifest.context_policy_version == SATURATION_CONTEXT_POLICY_VERSION
                else CORRECTIVE_RUNTIME_CONTRACT_SCHEMA
            ),
            "tool_schema_version": manifest.tool_schema_version,
            "context_policy_version": manifest.context_policy_version,
            "system_prompt_hash": sha256_text(
                SYSTEM_PROMPT_V8
                if manifest.context_policy_version
                == COVERAGE_REJECTION_CONTEXT_POLICY_VERSION
                else SYSTEM_PROMPT_V7
                if manifest.context_policy_version
                == COVERAGE_REVIEW_CONTEXT_POLICY_VERSION
                else SYSTEM_PROMPT_V6
                if manifest.context_policy_version
                == REVIEW_EVIDENCE_CONTEXT_POLICY_VERSION
                else SYSTEM_PROMPT_V5
            ),
            "tool_schema_hash": sha256_text(
                canonical_json(
                    TOOL_SCHEMAS_V6
                    if manifest.context_policy_version
                    == COVERAGE_REJECTION_CONTEXT_POLICY_VERSION
                    else TOOL_SCHEMAS_V5
                    if manifest.context_policy_version
                    == COVERAGE_REVIEW_CONTEXT_POLICY_VERSION
                    else TOOL_SCHEMAS_V4
                )
            ),
            "harness_git_commit": manifest.harness_git_commit,
        }
    expected = {
        "task": {
            "task_id": item["task_id"],
            "task_version": item["task_version"],
            "base_commit": item["base_commit"],
            "public_spec_hash": item["public_spec_hash"],
            "private_spec_hash": item["private_spec_hash"],
        },
        "model": {
            "provider": suite.model,
            "model_id": suite.model_id,
            "provider_sdk_version": (
                preflight["environment"]["openai_sdk"]["version"]
                if suite.model == "openai"
                else None
            ),
            "reasoning_effort": suite.reasoning_effort,
            "reasoning_mode": suite.reasoning_mode,
            "service_tier": suite.service_tier,
            "transport_max_retries": suite.transport_max_retries,
            "max_output_tokens": suite.max_output_tokens,
            "input_price_per_million_usd": suite.input_price_per_million_usd,
            "cached_input_price_per_million_usd": (
                suite.cached_input_price_per_million_usd
            ),
            "cache_write_input_price_per_million_usd": (
                suite.cache_write_input_price_per_million_usd
            ),
            "output_price_per_million_usd": suite.output_price_per_million_usd,
        },
        "budget": suite.budget.model_dump(mode="json"),
        "sandbox": {
            "backend": "docker" if item["evaluator_image_digest"] is not None else "local",
            "agent_image_digest": item["evaluator_image_digest"],
            "evaluator_image_digest": item["evaluator_image_digest"],
        },
        "memory": {
            "condition": item["condition"],
            "max_context_tokens": suite.memory_token_budget,
        },
        "fault": _diagnostic_fault(suite).model_dump(mode="json"),
        "public_review_contract": item.get("public_review_contract"),
        "runtime_contract": expected_runtime_contract,
        "experiment": {
            "experiment_id": suite.experiment_id,
            "purpose": suite.purpose.value,
            "suite_hash": preflight["suite_hash"],
            "execution_hash": preflight["execution_hash"],
            "dataset_manifest_hash": (
                preflight["dataset"]["manifest_hash"]
                if preflight["dataset"] is not None
                else None
            ),
            "dataset_role": item["dataset_role"],
            "schedule_seed": suite.seed,
            "schedule_order": item["order"],
            "schedule_row_id": item["schedule_row_id"],
            "repetition": item["repetition"],
        },
    }
    actual = {
        "task": {
            "task_id": manifest.task_id,
            "task_version": manifest.task_version,
            "base_commit": manifest.base_commit,
            "public_spec_hash": manifest.public_spec_hash,
            "private_spec_hash": manifest.private_spec_hash,
        },
        "model": {
            key: getattr(manifest.model, key)
            for key in expected["model"]
        },
        "budget": manifest.budget.model_dump(mode="json"),
        "sandbox": {
            "backend": manifest.sandbox_backend,
            "agent_image_digest": manifest.agent_image_digest,
            "evaluator_image_digest": manifest.evaluator_image_digest,
        },
        "memory": {
            "condition": manifest.memory.condition.value,
            "max_context_tokens": manifest.memory.max_context_tokens,
        },
        "fault": manifest.fault.model_dump(mode="json"),
        "public_review_contract": (
            manifest.public_review_contract.model_dump(mode="json")
            if manifest.public_review_contract is not None
            else None
        ),
        "runtime_contract": actual_runtime_contract,
        "experiment": (
            manifest.experiment.model_dump(mode="json")
            if manifest.experiment is not None
            else None
        ),
    }
    if actual != expected:
        raise ContractError("run manifest does not match the approved execution plan")


def _qualification_gate_check_projection(
    raw_checks: Any,
    check_id: str,
) -> dict[str, Any]:
    """Project one qualifier check without copying its potentially sensitive details."""

    checks = raw_checks if isinstance(raw_checks, list) else []
    matches = [
        check
        for check in checks
        if isinstance(check, dict) and check.get("check_id") == check_id
    ]
    passed = matches[0].get("passed") if len(matches) == 1 else None
    return {
        "schema_version": QUALIFICATION_GATE_CHECK_PROJECTION_SCHEMA,
        "check_id": check_id,
        "check_count": len(matches),
        "passed": passed if type(passed) is bool else None,
    }


def _terminal_qualification_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = {
        key: payload.get(key)
        for key in (
            "schema_version",
            "run_id",
            "qualified",
            "trace_integrity_passed",
            "leakage_scan_passed",
            "evaluation_reached",
            "outcome_kind",
            "purpose",
            "experiment_id",
            "dataset_role",
            "task_id",
            "execution_hash",
            "schedule_row_id",
            "memory_candidate_eligible",
            "failure_record_id",
            "qualification_hash",
        )
    }
    raw_checks = payload.get("checks")
    if not isinstance(raw_checks, list):
        raw_checks = []
    call_guard_check_id = "disabled_call_guard_contract"
    if (
        payload.get("purpose")
        == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE.value
        or (
            payload.get("purpose")
            == ExperimentPurpose.GENERIC_BASELINE_READINESS.value
            and payload.get("experiment_id")
            == GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID
        )
    ):
        check_id = call_guard_check_id
        summary["gate_checks"] = {
            check_id: _qualification_gate_check_projection(
                raw_checks,
                check_id,
            )
        }
    retry_checks = [
        check
        for check in raw_checks
        if (
            isinstance(check, dict)
            and check.get("check_id")
            == "rejected_patch_retry_context"
        )
    ]
    retry_feature: dict[str, Any] = {
        "check_count": len(retry_checks),
        "check_passed": None,
        "rejected_candidate_count": None,
        "retry_episode_count": None,
        "verified_retry_count": None,
        "failed_source_failure_sequences": None,
    }
    controlled_profile = (
        payload.get("fault_type")
        == "controlled-reject-first-prepared-patch"
    )
    if controlled_profile:
        retry_feature.update(
            {
                "controlled_rejection_count": None,
                "verified_controlled_rejection_count": None,
                "failed_controlled_source_failure_sequences": None,
                "controlled_patch_applied_sequences": None,
            }
        )
    if len(retry_checks) == 1:
        check = retry_checks[0]
        details = check.get("details")
        if not isinstance(details, dict):
            details = {}
        failed_sequences = details.get(
            "failed_source_failure_sequences"
        )
        check_passed = check.get("passed")
        rejected_count = details.get("rejected_candidate_count")
        episode_count = details.get("retry_episode_count")
        verified_count = details.get("verified_retry_count")
        controlled_count = details.get(
            "controlled_rejection_count"
        )
        verified_controlled_count = details.get(
            "verified_controlled_rejection_count"
        )
        failed_controlled_sequences = details.get(
            "failed_controlled_source_failure_sequences"
        )
        controlled_patch_applied_sequences = details.get(
            "controlled_patch_applied_sequences"
        )
        safe_failed_sequences = (
            list(failed_sequences)
            if (
                isinstance(failed_sequences, list)
                and all(
                    type(sequence) is int and sequence >= 1
                    for sequence in failed_sequences
                )
            )
            else None
        )
        retry_feature.update(
            {
                "check_passed": (
                    check_passed
                    if type(check_passed) is bool
                    else None
                ),
                "rejected_candidate_count": (
                    rejected_count
                    if type(rejected_count) is int
                    and rejected_count >= 0
                    else None
                ),
                "retry_episode_count": (
                    episode_count
                    if type(episode_count) is int
                    and episode_count >= 0
                    else None
                ),
                "verified_retry_count": (
                    verified_count
                    if type(verified_count) is int
                    and verified_count >= 0
                    else None
                ),
                "failed_source_failure_sequences": safe_failed_sequences,
            }
        )
        if controlled_profile:
            retry_feature.update(
                {
                    "controlled_rejection_count": (
                        controlled_count
                        if type(controlled_count) is int
                        and controlled_count >= 0
                        else None
                    ),
                    "verified_controlled_rejection_count": (
                        verified_controlled_count
                        if type(verified_controlled_count) is int
                        and verified_controlled_count >= 0
                        else None
                    ),
                    "failed_controlled_source_failure_sequences": (
                        list(failed_controlled_sequences)
                        if (
                            isinstance(
                                failed_controlled_sequences,
                                list,
                            )
                            and all(
                                type(sequence) is int
                                and sequence >= 1
                                for sequence in (
                                    failed_controlled_sequences
                                )
                            )
                        )
                        else None
                    ),
                    "controlled_patch_applied_sequences": (
                        list(controlled_patch_applied_sequences)
                        if (
                            isinstance(
                                controlled_patch_applied_sequences,
                                list,
                            )
                            and all(
                                type(sequence) is int
                                and sequence >= 1
                                for sequence in (
                                    controlled_patch_applied_sequences
                                )
                            )
                        )
                        else None
                    ),
                }
            )
    saturation_checks = [
        check
        for check in raw_checks
        if (
            isinstance(check, dict)
            and check.get("check_id") == "saturation_context_contract"
        )
    ]
    saturation_feature: dict[str, Any] = {
        "check_count": len(saturation_checks),
        "check_passed": None,
        "saturated_context_count": None,
        "read_search_removed_saturated_context_sequences": None,
        "post_saturation_patch_count": None,
        "reset_opportunity_count": None,
        "reset_context_count": None,
        "reset_context_sequences": None,
        "failed_reset_context_sequences": None,
    }
    if len(saturation_checks) == 1:
        check = saturation_checks[0]
        details = check.get("details")
        if not isinstance(details, dict):
            details = {}

        def safe_count(name: str) -> int | None:
            value = details.get(name)
            return value if type(value) is int and value >= 0 else None

        def safe_sequences(name: str) -> list[int] | None:
            value = details.get(name)
            if isinstance(value, list) and all(
                type(sequence) is int and sequence >= 1
                for sequence in value
            ):
                return list(value)
            return None

        saturation_feature.update(
            {
                "check_passed": (
                    check.get("passed")
                    if type(check.get("passed")) is bool
                    else None
                ),
                "saturated_context_count": safe_count(
                    "saturated_context_count"
                ),
                "read_search_removed_saturated_context_sequences": (
                    safe_sequences(
                        "read_search_removed_saturated_context_sequences"
                    )
                ),
                "post_saturation_patch_count": safe_count(
                    "post_saturation_patch_count"
                ),
                "reset_opportunity_count": safe_count(
                    "reset_opportunity_count"
                ),
                "reset_context_count": safe_count(
                    "reset_context_count"
                ),
                "reset_context_sequences": safe_sequences(
                    "reset_context_sequences"
                ),
                "failed_reset_context_sequences": safe_sequences(
                    "failed_reset_context_sequences"
                ),
            }
        )
    coverage_check_ids = (
        "public_coverage_contract",
        "coverage_decision_integrity",
        "coverage_submission_lifecycle",
        "coverage_recovery_contract",
        "coverage_terminal_contract",
    )
    coverage_checks = {
        check_id: [
            check
            for check in raw_checks
            if isinstance(check, dict) and check.get("check_id") == check_id
        ]
        for check_id in coverage_check_ids
    }

    def safe_coverage_count(check_id: str, name: str) -> int | None:
        rows = coverage_checks[check_id]
        details = rows[0].get("details") if len(rows) == 1 else None
        value = details.get(name) if isinstance(details, dict) else None
        return value if type(value) is int and value >= 0 else None

    def safe_coverage_bool(check_id: str, name: str) -> bool | None:
        rows = coverage_checks[check_id]
        details = rows[0].get("details") if len(rows) == 1 else None
        value = details.get(name) if isinstance(details, dict) else None
        return value if type(value) is bool else None

    def safe_coverage_sequences(check_id: str, name: str) -> list[int] | None:
        rows = coverage_checks[check_id]
        details = rows[0].get("details") if len(rows) == 1 else None
        value = details.get(name) if isinstance(details, dict) else None
        if isinstance(value, list) and all(
            type(sequence) is int and sequence >= 1 for sequence in value
        ):
            return list(value)
        return None

    coverage_target_count = safe_coverage_count(
        "public_coverage_contract",
        "coverage_target_count",
    )
    complete_review_count = safe_coverage_count(
        "coverage_decision_integrity",
        "coverage_complete_review_count",
    )
    accepted_submission_count = safe_coverage_count(
        "coverage_submission_lifecycle",
        "accepted_submission_count",
    )
    submission_evaluation_completed = safe_coverage_bool(
        "coverage_submission_lifecycle",
        "evaluation_completed",
    )
    recovery_nonvacuous = safe_coverage_bool(
        "coverage_recovery_contract",
        "nonvacuous",
    )
    accepted_finish_count = safe_coverage_count(
        "coverage_recovery_contract",
        "accepted_finish_count",
    )
    terminal_complete_sequences = safe_coverage_sequences(
        "coverage_terminal_contract",
        "coverage_complete_review_sequences",
    )
    terminal_accepted_count = safe_coverage_count(
        "coverage_terminal_contract",
        "accepted_submission_count",
    )
    terminal_evaluation_completed = safe_coverage_bool(
        "coverage_terminal_contract",
        "evaluation_completed",
    )
    coverage_check_counts = {
        check_id: len(rows) for check_id, rows in coverage_checks.items()
    }
    coverage_checks_passed = bool(
        all(count == 1 for count in coverage_check_counts.values())
        and all(
            rows[0].get("passed") is True
            for rows in coverage_checks.values()
        )
    )
    coverage_feature = {
        "check_counts": coverage_check_counts,
        "all_checks_passed": coverage_checks_passed,
        "coverage_target_count": coverage_target_count,
        "coverage_complete_review_count": complete_review_count,
        "accepted_submission_count": accepted_submission_count,
        "submission_evaluation_completed": submission_evaluation_completed,
        "recovery_nonvacuous": recovery_nonvacuous,
        "accepted_finish_count": accepted_finish_count,
        "terminal_complete_review_sequences": terminal_complete_sequences,
        "terminal_accepted_submission_count": terminal_accepted_count,
        "terminal_evaluation_completed": terminal_evaluation_completed,
        "observed": bool(
            coverage_checks_passed
            and type(coverage_target_count) is int
            and coverage_target_count > 0
            and type(complete_review_count) is int
            and complete_review_count >= 1
            and accepted_submission_count == 1
            and submission_evaluation_completed is True
            and recovery_nonvacuous is True
            and accepted_finish_count == 1
            and isinstance(terminal_complete_sequences, list)
            and bool(terminal_complete_sequences)
            and terminal_accepted_count == 1
            and terminal_evaluation_completed is True
        ),
    }
    coverage_rejection_checks = [
        check
        for check in raw_checks
        if (
            isinstance(check, dict)
            and check.get("check_id")
            == "coverage_rejection_recovery_contract"
        )
    ]
    coverage_rejection_feature: dict[str, Any] = {
        "check_count": len(coverage_rejection_checks),
        "check_passed": None,
        "exercise_status": "failed",
        "rejection_count": None,
        "verified_rejection_sequences": None,
        "restart_observed": None,
        "failed_rejection_sequences": None,
    }
    if len(coverage_rejection_checks) == 1:
        check = coverage_rejection_checks[0]
        details = check.get("details")
        if not isinstance(details, dict):
            details = {}
        exercise_status = details.get("exercise_status")
        rejection_count = details.get("rejection_count")
        verified_sequences = details.get("verified_rejection_sequences")
        failed_sequences = details.get("failed_rejection_sequences")
        coverage_rejection_feature.update(
            {
                "check_passed": (
                    check.get("passed")
                    if type(check.get("passed")) is bool
                    else None
                ),
                "exercise_status": (
                    exercise_status
                    if exercise_status in {"passed", "inconclusive", "failed"}
                    else "failed"
                ),
                "rejection_count": (
                    rejection_count
                    if type(rejection_count) is int and rejection_count >= 0
                    else None
                ),
                "verified_rejection_sequences": (
                    list(verified_sequences)
                    if isinstance(verified_sequences, list)
                    and all(
                        type(sequence) is int and sequence >= 1
                        for sequence in verified_sequences
                    )
                    else None
                ),
                "restart_observed": (
                    details.get("restart_observed")
                    if type(details.get("restart_observed")) is bool
                    else None
                ),
                "failed_rejection_sequences": (
                    list(failed_sequences)
                    if isinstance(failed_sequences, list)
                    and all(
                        type(sequence) is int and sequence >= 1
                        for sequence in failed_sequences
                    )
                    else None
                ),
            }
        )
    summary["trace_features"] = {
        "rejected_patch_retry_context": retry_feature,
        "saturation_context": saturation_feature,
        "public_coverage_review": coverage_feature,
        "coverage_rejection_recovery": coverage_rejection_feature,
    }
    return summary


def _qualify_terminal_run(run_id: str, task: str) -> dict[str, Any]:
    from patchloop.evals.qualification import qualify_run

    task_path = Path(task)
    payload = qualify_run(
        run_id,
        task_dir=task_path.parent if task_path.is_file() else task_path,
    )
    return _terminal_qualification_summary(payload)


def _saturation_diagnostic_result(
    qualification: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify natural V8 branch exercise without redefining trace validity."""

    status = "failed"
    reason_code: str | None = "qualification_unavailable"
    trace_features = (
        qualification.get("trace_features")
        if isinstance(qualification, dict)
        else None
    )
    feature = (
        trace_features.get("saturation_context")
        if isinstance(trace_features, dict)
        else None
    )
    evidence = {
        "check_count": None,
        "check_passed": None,
        "saturated_context_count": None,
        "read_search_removed_saturated_context_sequences": None,
        "post_saturation_patch_count": None,
        "reset_opportunity_count": None,
        "reset_context_count": None,
        "reset_context_sequences": None,
        "failed_reset_context_sequences": None,
    }
    if isinstance(feature, dict):
        evidence.update(
            {key: feature.get(key) for key in evidence}
        )
    counts_valid = all(
        type(evidence[name]) is int and evidence[name] >= 0
        for name in (
            "check_count",
            "saturated_context_count",
            "post_saturation_patch_count",
            "reset_opportunity_count",
            "reset_context_count",
        )
    )
    sequences_valid = all(
        isinstance(evidence[name], list)
        and all(
            type(sequence) is int and sequence >= 1
            for sequence in evidence[name]
        )
        for name in (
            "read_search_removed_saturated_context_sequences",
            "reset_context_sequences",
            "failed_reset_context_sequences",
        )
    )
    evidence_consistent = bool(
        counts_valid
        and sequences_valid
        and evidence["saturated_context_count"]
        == len(
            evidence[
                "read_search_removed_saturated_context_sequences"
            ]
        )
        and evidence["reset_context_count"]
        == len(evidence["reset_context_sequences"])
        and evidence["reset_context_count"]
        <= evidence["reset_opportunity_count"]
        <= evidence["post_saturation_patch_count"]
    )
    if isinstance(qualification, dict):
        if qualification.get("qualified") is not True:
            reason_code = "qualification_not_passed"
        elif evidence["check_count"] != 1:
            reason_code = "qualification_check_cardinality"
        elif evidence["check_passed"] is not True:
            reason_code = "qualification_check_failed"
        elif not evidence_consistent:
            reason_code = "qualification_evidence_malformed"
        elif evidence["saturated_context_count"] == 0:
            status = "inconclusive"
            reason_code = "saturation_not_observed"
        elif evidence["post_saturation_patch_count"] == 0:
            status = "inconclusive"
            reason_code = "post_saturation_patch_not_observed"
        elif evidence["reset_opportunity_count"] == 0:
            status = "inconclusive"
            reason_code = "post_saturation_reset_not_observed"
        elif (
            evidence["reset_context_count"] >= 1
            and not evidence["failed_reset_context_sequences"]
        ):
            status = "passed"
            reason_code = None
        else:
            reason_code = "post_saturation_reset_not_verified"
    return {
        "schema_version": "experiment-diagnostic-result-v1",
        "profile": "v8-saturation-context-v1",
        "required_trace_features": ["saturation_context"],
        "status": status,
        "reason_code": reason_code,
        "qualification_hash": (
            qualification.get("qualification_hash")
            if isinstance(qualification, dict)
            else None
        ),
        "features": {"saturation_context": evidence},
    }


def _diagnostic_result(
    suite: ExperimentSuite,
    qualification: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Evaluate the suite-specific exercise without changing qualification."""

    if suite.diagnostic is None:
        return None
    if suite.diagnostic.profile == "v8-saturation-context-v1":
        return _saturation_diagnostic_result(qualification)
    controlled_profile = (
        suite.diagnostic.profile
        == "d037-rejected-patch-retry-v4"
    )
    feature_name = suite.diagnostic.required_trace_features[0]
    trace_features = (
        qualification.get("trace_features")
        if isinstance(qualification, dict)
        else None
    )
    feature = (
        trace_features.get(feature_name)
        if isinstance(trace_features, dict)
        else None
    )
    status = "failed"
    reason_code = "qualification_unavailable"
    if isinstance(qualification, dict):
        if qualification.get("qualified") is not True:
            reason_code = "qualification_not_passed"
        elif qualification.get("evaluation_reached") is not True:
            reason_code = "evaluation_not_reached"
        else:
            reason_code = "qualification_feature_unavailable"
    sanitized_feature = {
        "check_count": None,
        "check_passed": None,
        "rejected_candidate_count": None,
        "retry_episode_count": None,
        "verified_retry_count": None,
        "failed_source_failure_sequences": None,
    }
    if controlled_profile:
        sanitized_feature.update(
            {
                "controlled_rejection_count": None,
                "verified_controlled_rejection_count": None,
                "failed_controlled_source_failure_sequences": None,
                "controlled_patch_applied_sequences": None,
            }
        )
    if isinstance(feature, dict):
        check_count = feature.get("check_count")
        check_passed = feature.get("check_passed")
        rejected_count = feature.get("rejected_candidate_count")
        episode_count = feature.get("retry_episode_count")
        verified_count = feature.get("verified_retry_count")
        failed_sequences = feature.get(
            "failed_source_failure_sequences"
        )
        controlled_count = feature.get(
            "controlled_rejection_count"
        )
        verified_controlled_count = feature.get(
            "verified_controlled_rejection_count"
        )
        failed_controlled_sequences = feature.get(
            "failed_controlled_source_failure_sequences"
        )
        controlled_patch_applied_sequences = feature.get(
            "controlled_patch_applied_sequences"
        )
        controlled_evidence_valid = bool(
            not controlled_profile
            or (
                type(controlled_count) is int
                and controlled_count >= 0
                and type(verified_controlled_count) is int
                and verified_controlled_count >= 0
                and isinstance(failed_controlled_sequences, list)
                and all(
                    type(sequence) is int and sequence >= 1
                    for sequence in failed_controlled_sequences
                )
                and isinstance(
                    controlled_patch_applied_sequences,
                    list,
                )
                and all(
                    type(sequence) is int and sequence >= 1
                    for sequence in controlled_patch_applied_sequences
                )
            )
        )
        evidence_types_valid = bool(
            type(check_count) is int
            and check_count >= 0
            and type(rejected_count) is int
            and rejected_count >= 0
            and type(episode_count) is int
            and episode_count >= 0
            and type(verified_count) is int
            and verified_count >= 0
            and isinstance(failed_sequences, list)
            and all(
                type(sequence) is int and sequence >= 1
                for sequence in failed_sequences
            )
            and controlled_evidence_valid
        )
        if evidence_types_valid:
            sanitized_feature = {
                "check_count": check_count,
                "check_passed": check_passed,
                "rejected_candidate_count": rejected_count,
                "retry_episode_count": episode_count,
                "verified_retry_count": verified_count,
                "failed_source_failure_sequences": list(
                    failed_sequences
                ),
            }
            if controlled_profile:
                sanitized_feature.update(
                    {
                        "controlled_rejection_count": (
                            controlled_count
                        ),
                        "verified_controlled_rejection_count": (
                            verified_controlled_count
                        ),
                        "failed_controlled_source_failure_sequences": list(
                            failed_controlled_sequences
                        ),
                        "controlled_patch_applied_sequences": list(
                            controlled_patch_applied_sequences
                        ),
                    }
                )
        else:
            sanitized_feature["check_count"] = (
                check_count
                if type(check_count) is int and check_count >= 0
                else None
            )
            sanitized_feature["check_passed"] = (
                check_passed
                if type(check_passed) is bool
                else None
            )
        if qualification.get("qualified") is not True:
            reason_code = "qualification_not_passed"
        elif qualification.get("evaluation_reached") is not True:
            reason_code = "evaluation_not_reached"
        elif check_count != 1:
            reason_code = "qualification_check_cardinality"
        elif check_passed is not True:
            reason_code = "qualification_check_failed"
        elif not evidence_types_valid:
            reason_code = "qualification_evidence_malformed"
        elif controlled_profile and not (
            controlled_count == 1
            and verified_controlled_count == 1
            and rejected_count >= 1
            and not failed_controlled_sequences
            and not controlled_patch_applied_sequences
        ):
            reason_code = "controlled_rejection_not_verified"
        elif episode_count == 0:
            if controlled_profile:
                reason_code = "controlled_retry_episode_not_observed"
            else:
                status = "inconclusive"
                reason_code = "retry_episode_not_observed"
        elif (
            verified_count == episode_count
            and not failed_sequences
        ):
            status = "passed"
            reason_code = None
        else:
            reason_code = "retry_episode_not_fully_verified"
    return {
        "schema_version": "experiment-diagnostic-result-v1",
        "profile": suite.diagnostic.profile,
        "required_trace_features": list(
            suite.diagnostic.required_trace_features
        ),
        "status": status,
        "reason_code": reason_code,
        "qualification_hash": (
            qualification.get("qualification_hash")
            if isinstance(qualification, dict)
            else None
        ),
        "features": {feature_name: sanitized_feature},
    }


def _diagnostic_error(
    diagnostic: dict[str, Any] | None,
) -> dict[str, str] | None:
    if diagnostic is None or diagnostic.get("status") == "passed":
        return None
    status = diagnostic.get("status")
    error_type = (
        "TraceExerciseInconclusive"
        if status == "inconclusive"
        else "TraceExerciseFailed"
    )
    return {
        "type": error_type,
        "message": (
            "required trace exercise was not observed"
            if status == "inconclusive"
            else "required trace exercise did not satisfy its contract"
        ),
        "profile": str(diagnostic.get("profile")),
        "reason_code": str(diagnostic.get("reason_code")),
    }


def _completion_gate(
    suite: ExperimentSuite,
    rows: list[dict[str, Any]],
    *,
    expected_execution_hash: str | None = None,
    expected_schedule: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Separate runtime completion from task success for the high-budget panel."""

    completion_panel = bool(
        suite.purpose
        == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
        and suite.budget == GPT54_MINI_COMPLETION_BUDGET
        and {
            _normalized_task_path(task) for task in suite.tasks
        }
        == COMPLETION_PANEL_TASKS
    )
    generic_baseline_readiness = bool(
        suite.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS
        and suite.experiment_id
        in GENERIC_BASELINE_READINESS_BUDGET_BY_EXPERIMENT_ID
        and suite.budget
        == GENERIC_BASELINE_READINESS_BUDGET_BY_EXPERIMENT_ID.get(
            suite.experiment_id
        )
        and [_normalized_task_path(task) for task in suite.tasks]
        == GENERIC_BASELINE_READINESS_TASKS
        and suite.transport_max_retries == 0
    )
    generic_count_observability = bool(
        generic_baseline_readiness
        and suite.experiment_id
        == GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID
    )
    workflow_completion_probe = bool(
        suite.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        and suite.experiment_id == WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID
        and suite.budget == GPT54_MINI_WORKFLOW_COMPLETION_PROBE_BUDGET
        and [_normalized_task_path(task) for task in suite.tasks]
        == [WORKFLOW_COMPLETION_PROBE_TASK]
        and suite.transport_max_retries == 0
    )
    budget_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT
        and suite.budget
        == GPT54_MINI_MEMORY_DEVELOPMENT_BUDGET_PILOT
        and {
            _normalized_task_path(task) for task in suite.tasks
        }
        == MEMORY_DEVELOPMENT_BUDGET_PILOT_TASKS
    )
    corrective_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
        and suite.budget
        == GPT54_MINI_MEMORY_DEVELOPMENT_CORRECTIVE_PILOT
        and {
            _normalized_task_path(task) for task in suite.tasks
        }
        == MEMORY_DEVELOPMENT_BUDGET_PILOT_TASKS
    )
    saturation_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
        and suite.budget
        == GPT54_MINI_MEMORY_DEVELOPMENT_SATURATION_PILOT
        and [_normalized_task_path(task) for task in suite.tasks]
        == [SATURATION_PILOT_TASK]
    )
    review_evidence_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
        and suite.budget
        == GPT54_MINI_MEMORY_DEVELOPMENT_REVIEW_EVIDENCE_PILOT
        and [_normalized_task_path(task) for task in suite.tasks]
        == [REVIEW_EVIDENCE_PILOT_TASK]
    )
    coverage_review_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        and suite.budget
        == GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REVIEW_PILOT
        and [_normalized_task_path(task) for task in suite.tasks]
        == [COVERAGE_REVIEW_PILOT_TASK]
    )
    coverage_rejection_pilot = bool(
        suite.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        and suite.budget
        == GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REJECTION_PILOT
        and [_normalized_task_path(task) for task in suite.tasks]
        == [COVERAGE_REJECTION_PILOT_TASK]
    )
    if not any(
        (
            generic_baseline_readiness,
            workflow_completion_probe,
            completion_panel,
            budget_pilot,
            corrective_pilot,
            saturation_pilot,
            review_evidence_pilot,
            coverage_review_pilot,
            coverage_rejection_pilot,
        )
    ):
        return None

    budget_terminal_run_ids: list[str] = []
    for row in rows:
        result = row.get("result") or {}
        terminal_error = result.get("terminal_error") or {}
        details = terminal_error.get("details") or {}
        reason_code = details.get("reason_code")
        error_code = terminal_error.get("code")
        run_id = row.get("run_id")
        if (
            (
                isinstance(reason_code, str)
                and "budget" in reason_code
                or isinstance(error_code, str)
                and "BUDGET" in error_code
            )
            and isinstance(run_id, str)
        ):
            budget_terminal_run_ids.append(run_id)

    expected_runs = (
        4
        if generic_baseline_readiness
        else 1
        if (
            workflow_completion_probe
            or saturation_pilot
            or review_evidence_pilot
            or coverage_review_pilot
            or coverage_rejection_pilot
        )
        else 3
        if budget_pilot or corrective_pilot
        else 2
    )
    readiness_task_identity_passed = bool(
        not (generic_baseline_readiness or workflow_completion_probe)
        or (
            len(rows) == expected_runs
            and {row.get("task_id") for row in rows}
            == (
                GENERIC_BASELINE_READINESS_TASK_IDS
                if generic_baseline_readiness
                else {WORKFLOW_COMPLETION_PROBE_TASK_ID}
            )
        )
    )
    readiness_run_ids = [row.get("run_id") for row in rows]
    readiness_schedule_row_ids = [row.get("schedule_row_id") for row in rows]
    expected_schedule_rows = expected_schedule if isinstance(expected_schedule, list) else []
    expected_schedule_row_ids = [
        row.get("schedule_row_id") for row in expected_schedule_rows if isinstance(row, dict)
    ]
    expected_schedule_by_id = {
        row["schedule_row_id"]: row
        for row in expected_schedule_rows
        if isinstance(row, dict) and isinstance(row.get("schedule_row_id"), str)
    }

    def valid_sha256_identity(value: Any) -> bool:
        return bool(
            isinstance(value, str)
            and value.startswith("sha256:")
            and len(value) == 71
            and all(character in "0123456789abcdef" for character in value[7:])
        )

    readiness_run_binding_passed = bool(
        not (generic_baseline_readiness or workflow_completion_probe)
        or (
            len(rows) == expected_runs
            and all(isinstance(run_id, str) and run_id for run_id in readiness_run_ids)
            and len(set(readiness_run_ids)) == expected_runs
            and all(
                isinstance(row.get("result"), dict)
                and row["result"].get("run_id") == row.get("run_id")
                and isinstance(row.get("qualification"), dict)
                and row["qualification"].get("run_id") == row.get("run_id")
                for row in rows
            )
        )
    )
    readiness_schedule_binding_passed = bool(
        not (generic_baseline_readiness or workflow_completion_probe)
        or (
            len(expected_schedule_rows) == expected_runs
            and len(expected_schedule_by_id) == expected_runs
            and all(valid_sha256_identity(row_id) for row_id in expected_schedule_row_ids)
            and len(rows) == expected_runs
            and all(valid_sha256_identity(row_id) for row_id in readiness_schedule_row_ids)
            and set(readiness_schedule_row_ids) == set(expected_schedule_row_ids)
            and all(
                (expected_row := expected_schedule_by_id.get(row.get("schedule_row_id")))
                is not None
                and all(
                    row.get(field) == expected_row.get(field)
                    for field in (
                        "order",
                        "schedule_row_id",
                        "task_id",
                        "split",
                        "dataset_role",
                        "condition",
                        "repetition",
                    )
                )
                and isinstance(row.get("qualification"), dict)
                and row["qualification"].get("task_id") == expected_row.get("task_id")
                and row["qualification"].get("schedule_row_id")
                == expected_row.get("schedule_row_id")
                for row in rows
            )
        )
    )
    readiness_execution_binding_passed = bool(
        not (generic_baseline_readiness or workflow_completion_probe)
        or (
            valid_sha256_identity(expected_execution_hash)
            and len(rows) == expected_runs
            and all(
                isinstance(row.get("qualification"), dict)
                and row["qualification"].get("execution_hash") == expected_execution_hash
                for row in rows
            )
        )
    )
    readiness_row_binding_passed = bool(
        not (generic_baseline_readiness or workflow_completion_probe)
        or (
            readiness_run_binding_passed
            and readiness_schedule_binding_passed
            and readiness_execution_binding_passed
        )
    )
    terminal_runs = sum(row.get("attempt_status") == "terminal" for row in rows)
    qualified_runs = sum(
        (row.get("qualification") or {}).get("qualified") is True
        for row in rows
    )
    evaluator_reached_runs = sum(
        (row.get("qualification") or {}).get("evaluation_reached") is True
        for row in rows
    )
    official_evaluator_runs = sum(
        bool(
            (row.get("result") or {}).get("official") is True
            and (row.get("result") or {}).get("evaluation_status")
            == "completed"
        )
        for row in rows
    )
    infrastructure_errors = sum(
        row.get("infrastructure_error") is not None for row in rows
    )
    qualification_errors = sum(
        row.get("qualification_error") is not None for row in rows
    )
    diagnostic_errors = sum(
        row.get("diagnostic_error") is not None for row in rows
    )
    diagnostic_passed_runs = sum(
        (row.get("diagnostic") or {}).get("status") == "passed"
        for row in rows
    )
    task_successes = sum(
        (row.get("result") or {}).get("scope_compliant_success") is True
        for row in rows
    )

    def qualification_check_passed(
        row: dict[str, Any],
        check_id: str,
    ) -> bool:
        qualification = row.get("qualification") or {}
        gate_checks = qualification.get("gate_checks")
        projection = (
            gate_checks.get(check_id)
            if isinstance(gate_checks, dict)
            else None
        )
        return bool(
            isinstance(projection, dict)
            and set(gate_checks) == {check_id}
            and set(projection)
            == {"schema_version", "check_id", "check_count", "passed"}
            and projection.get("schema_version")
            == QUALIFICATION_GATE_CHECK_PROJECTION_SCHEMA
            and projection.get("check_id") == check_id
            and type(projection.get("check_count")) is int
            and projection.get("check_count") == 1
            and projection.get("passed") is True
        )

    call_guard_contract_required = bool(
        workflow_completion_probe or generic_count_observability
    )
    call_guard_contract_passed = bool(
        not call_guard_contract_required
        or (
            len(rows) == expected_runs
            and all(
                qualification_check_passed(
                    row,
                    "disabled_call_guard_contract",
                )
                for row in rows
            )
        )
    )
    terminal_loop_failure_run_ids = [
        row["run_id"]
        for row in rows
        if isinstance(row.get("run_id"), str)
        and any(
            "loop" in str(value).lower()
            for value in (
                ((row.get("result") or {}).get("terminal_error") or {}).get(
                    "type"
                ),
                ((row.get("result") or {}).get("terminal_error") or {}).get(
                    "code"
                ),
                (
                    ((row.get("result") or {}).get("terminal_error") or {}).get(
                        "details"
                    )
                    or {}
                ).get("reason_code"),
            )
            if value is not None
        )
    ]
    coverage_lifecycle_observed_runs = sum(
        (
            (((row.get("qualification") or {}).get("trace_features") or {}).get(
                "public_coverage_review"
            ) or {}).get("observed")
            is True
        )
        for row in rows
    )
    coverage_rejection_exercise_statuses = [
        (((row.get("qualification") or {}).get("trace_features") or {}).get(
            "coverage_rejection_recovery"
        ) or {}).get("exercise_status")
        for row in rows
    ]
    coverage_rejection_exercise_counts = {
        status: coverage_rejection_exercise_statuses.count(status)
        for status in ("passed", "inconclusive", "failed")
    }
    completion_passed = bool(
        len(rows) == expected_runs
        and readiness_task_identity_passed
        and readiness_row_binding_passed
        and call_guard_contract_passed
        and terminal_runs == expected_runs
        and qualified_runs == expected_runs
        and evaluator_reached_runs == expected_runs
        and official_evaluator_runs == expected_runs
        and infrastructure_errors == 0
        and qualification_errors == 0
        and diagnostic_errors == 0
        and (
            not saturation_pilot
            or diagnostic_passed_runs == expected_runs
        )
        and (
            not (coverage_review_pilot or coverage_rejection_pilot)
            or coverage_lifecycle_observed_runs == expected_runs
        )
        and (
            not coverage_rejection_pilot
            or (
                len(coverage_rejection_exercise_statuses) == expected_runs
                and coverage_rejection_exercise_counts["failed"] == 0
                and coverage_rejection_exercise_counts["passed"]
                + coverage_rejection_exercise_counts["inconclusive"]
                == expected_runs
            )
        )
        and not budget_terminal_run_ids
        and (
            not call_guard_contract_required
            or not terminal_loop_failure_run_ids
        )
    )
    if (
        generic_baseline_readiness
        or workflow_completion_probe
        or budget_pilot
        or corrective_pilot
        or saturation_pilot
        or review_evidence_pilot
        or coverage_review_pilot
        or coverage_rejection_pilot
    ):
        return {
            "schema_version": (
                "generic-baseline-readiness-gate-v2"
                if generic_count_observability
                else "generic-baseline-readiness-gate-v1"
                if generic_baseline_readiness
                else "workflow-completion-probe-gate-v1"
                if workflow_completion_probe
                else "v11-coverage-rejection-live-pilot-gate-v1"
                if coverage_rejection_pilot
                else "v10-coverage-review-live-pilot-gate-v1"
                if coverage_review_pilot
                else "v9-review-evidence-live-pilot-gate-v1"
                if review_evidence_pilot
                else "v8-saturation-live-pilot-gate-v1"
                if saturation_pilot
                else "no-memory-corrective-pilot-gate-v1"
                if corrective_pilot
                else "no-memory-budget-pilot-gate-v1"
            ),
            "passed": completion_passed,
            "expected_runs": expected_runs,
            "terminal_runs": terminal_runs,
            "qualified_runs": qualified_runs,
            "evaluator_reached_runs": evaluator_reached_runs,
            "official_evaluator_runs": official_evaluator_runs,
            "infrastructure_errors": infrastructure_errors,
            "qualification_errors": qualification_errors,
            "diagnostic_errors": diagnostic_errors,
            **(
                {
                    "task_identity_passed": readiness_task_identity_passed,
                    "row_binding_passed": readiness_row_binding_passed,
                    "run_binding_passed": readiness_run_binding_passed,
                    "schedule_binding_passed": (readiness_schedule_binding_passed),
                    "execution_binding_passed": (readiness_execution_binding_passed),
                }
                if generic_baseline_readiness or workflow_completion_probe
                else {}
            ),
            **(
                {
                    "call_guard_policy": (
                        WORKFLOW_COMPLETION_CALL_GUARD_POLICY
                    ),
                    "call_guard_contract_passed": (
                        call_guard_contract_passed
                    ),
                    "terminal_loop_failure_runs": len(
                        terminal_loop_failure_run_ids
                    ),
                    "terminal_loop_failure_run_ids": (
                        terminal_loop_failure_run_ids
                    ),
                }
                if call_guard_contract_required
                else {}
            ),
            **(
                {"diagnostic_passed_runs": diagnostic_passed_runs}
                if saturation_pilot
                else {}
            ),
            **(
                {
                    "coverage_lifecycle_observed_runs": (
                        coverage_lifecycle_observed_runs
                    )
                }
                if coverage_review_pilot or coverage_rejection_pilot
                else {}
            ),
            **(
                {
                    "coverage_rejection_exercise": {
                        "status": (
                            coverage_rejection_exercise_statuses[0]
                            if len(coverage_rejection_exercise_statuses) == 1
                            and coverage_rejection_exercise_statuses[0]
                            in {"passed", "inconclusive", "failed"}
                            else "failed"
                        ),
                        "statuses": coverage_rejection_exercise_statuses,
                        "passed_runs": coverage_rejection_exercise_counts["passed"],
                        "inconclusive_runs": coverage_rejection_exercise_counts[
                            "inconclusive"
                        ],
                        "failed_runs": coverage_rejection_exercise_counts["failed"],
                    }
                }
                if coverage_rejection_pilot
                else {}
            ),
            "budget_terminal_runs": len(budget_terminal_run_ids),
            "budget_terminal_run_ids": budget_terminal_run_ids,
            "task_successes": task_successes,
            "task_success_required": False,
            "comparison_denominator_eligible": False,
            "memory_admission_unlocked": False,
        }

    headroom_failures: list[str] = []
    for row in rows:
        usage = row.get("usage") or {}
        within_headroom = bool(
            int(usage.get("input_tokens", 0))
            + int(usage.get("output_tokens", 0))
            <= 480_000
            and int(usage.get("model_calls", 0)) <= 32
            and int(usage.get("tool_calls", 0)) <= 80
            and int(usage.get("wall_clock_ms", 0)) <= 1_440_000
        )
        if not within_headroom and isinstance(row.get("run_id"), str):
            headroom_failures.append(row["run_id"])

    return {
        "schema_version": "no-memory-completion-gate-v1",
        "passed": completion_passed,
        "expected_runs": expected_runs,
        "terminal_runs": terminal_runs,
        "qualified_runs": qualified_runs,
        "evaluator_reached_runs": evaluator_reached_runs,
        "official_evaluator_runs": official_evaluator_runs,
        "infrastructure_errors": infrastructure_errors,
        "qualification_errors": qualification_errors,
        "diagnostic_errors": diagnostic_errors,
        "budget_terminal_runs": len(budget_terminal_run_ids),
        "budget_terminal_run_ids": budget_terminal_run_ids,
        "task_successes": task_successes,
        "task_success_required": False,
        "panel_headroom": {
            "max_total_tokens": 480_000,
            "max_model_calls": 32,
            "max_tool_calls": 80,
            "max_wall_clock_ms": 1_440_000,
            "passed": completion_passed and not headroom_failures,
            "failed_run_ids": headroom_failures,
            "sufficient_to_freeze_comparison_budget": False,
        },
    }


def _persist_preflight_plan(preflight: dict[str, Any]) -> dict[str, str]:
    execution_hash = preflight["execution_hash"]
    digest = execution_hash.removeprefix("sha256:")
    output = runtime_root() / "experiments" / "plans" / f"{digest}.json"
    payload = {
        **preflight,
        "schema_version": "experiment-execution-plan-v1",
    }
    serialized = canonical_json(payload)
    plan_hash = sha256_text(serialized)
    if output.exists():
        try:
            existing = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"invalid existing preflight plan: {output}") from exc
        if canonical_json(existing) != serialized:
            raise ContractError(
                "existing preflight plan conflicts with the approved execution hash"
            )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return {"path": str(output), "artifact_hash": plan_hash}


def _assert_live_environment_unchanged(preflight: dict[str, Any]) -> None:
    expected = preflight["environment"]
    current_git = _git_state()
    current_sdk = _openai_sdk_state()
    current_docker = _docker_image_state(
        [
            row["evaluator_image"]
            for row in preflight["tasks"]
            if row["evaluator_image"] is not None
        ]
    )
    current_credential = {
        "name": "OPENAI_API_KEY",
        "present": bool(os.environ.get("OPENAI_API_KEY")),
        "custom_base_url_present": bool(
            os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
        ),
    }
    if (
        current_git != expected["git"]
        or current_sdk != expected["openai_sdk"]
        or current_docker != expected["docker"]
        or current_credential != expected["credential"]
    ):
        raise ContractError(
            "live execution environment changed after the approved preflight plan"
        )


def evaluate_suite(
    path: str | Path,
    *,
    approve_live_cost: bool = False,
    approved_execution_hash: str | None = None,
) -> dict:
    """Execute only after the deterministic, secret-free preflight is ready."""

    preflight = preflight_suite(
        path,
        approve_live_cost=approve_live_cost,
        approved_execution_hash=approved_execution_hash,
    )
    if not preflight["ready"]:
        messages = "; ".join(blocker["message"] for blocker in preflight["blockers"])
        raise ContractError(
            f"experiment preflight failed: {messages}",
            details={
                "execution_hash": preflight["execution_hash"],
                "blockers": preflight["blockers"],
            },
        )

    suite = ExperimentSuite.model_validate(preflight["suite"])
    if not hmac.compare_digest(_suite_hash(suite), preflight["suite_hash"]):
        raise ContractError("approved preflight suite hash mismatch")
    plan = _persist_preflight_plan(preflight)
    if suite.model == "openai":
        _assert_live_environment_unchanged(preflight)
    journal_path = Path(preflight["journal_path"])
    journal_sequence = 1
    journal_hash = _append_campaign_event(
        journal_path,
        sequence=journal_sequence,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": suite.experiment_id,
            "purpose": suite.purpose.value,
            "execution_hash": preflight["execution_hash"],
            "schedule_hash": preflight["schedule_hash"],
            "execution_plan_hash": plan["artifact_hash"],
        },
    )
    live_authorization = (
        issue_live_execution_authorization(
            preflight["execution_hash"],
            root=runtime_root(),
        )
        if suite.model == "openai"
        else None
    )
    runner = AgentRunner()
    results = []
    actual_model_cost_usd = 0.0
    task_packages: dict[str, Any] = {}
    per_run_cost_reserve_usd = float(
        preflight["pricing"]["per_run_cost_reserve_usd"]
    )
    qualification_required = suite.purpose in {
        ExperimentPurpose.GENERIC_BASELINE_READINESS,
        ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT,
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT,
    }
    halt_reason: dict[str, str] | None = None

    for item in preflight["schedule"]:
        row_identity = {
            "order": item["order"],
            "schedule_row_id": item["schedule_row_id"],
            "task_id": item["task_id"],
            "split": item["split"],
            "dataset_role": item["dataset_role"],
            "condition": item["condition"],
            "repetition": item["repetition"],
        }
        if halt_reason is not None:
            row = {
                **row_identity,
                "attempt_status": "not_started",
                "run_id": None,
                "usage": None,
                "result": None,
                "infrastructure_error": None,
                "qualification": None,
                "qualification_error": None,
                "diagnostic": None,
                "diagnostic_error": None,
                "not_started_reason": halt_reason,
            }
            results.append(row)
            journal_sequence += 1
            journal_hash = _append_campaign_event(
                journal_path,
                sequence=journal_sequence,
                previous_event_hash=journal_hash,
                event_type="RunNotStarted",
                payload={
                    **row_identity,
                    "reason_type": halt_reason["type"],
                },
            )
            continue
        if (
            suite.model == "openai"
            and actual_model_cost_usd + per_run_cost_reserve_usd
            > suite.cost_limit_usd
        ):
            halt_reason = {
                "type": "CostReserveUnavailable",
                "message": "remaining cost limit cannot reserve one full frozen run budget",
            }
            row = {
                **row_identity,
                "attempt_status": "not_started",
                "run_id": None,
                "usage": None,
                "result": None,
                "infrastructure_error": None,
                "qualification": None,
                "qualification_error": None,
                "diagnostic": None,
                "diagnostic_error": None,
                "not_started_reason": halt_reason,
            }
            results.append(row)
            journal_sequence += 1
            journal_hash = _append_campaign_event(
                journal_path,
                sequence=journal_sequence,
                previous_event_hash=journal_hash,
                event_type="RunNotStarted",
                payload={
                    **row_identity,
                    "reason_type": halt_reason["type"],
                },
            )
            continue

        if suite.model == "openai":
            _assert_live_environment_unchanged(preflight)
        task = item["task"]
        if task not in task_packages:
            task_path = Path(task)
            task_packages[task] = load_task_package(
                task_path.parent if task_path.is_file() else task_path
            )
        package = task_packages[task]
        task_row = next(
            row for row in preflight["tasks"] if row["task_id"] == item["task_id"]
        )
        _assert_task_package_matches_preflight(package, task_row)
        evaluator_digest = item["evaluator_image_digest"]
        sandbox_backend = "docker" if evaluator_digest is not None else "local"
        experiment_context = ExperimentRunContext(
            experiment_id=suite.experiment_id,
            purpose=suite.purpose,
            suite_hash=preflight["suite_hash"],
            execution_hash=preflight["execution_hash"],
            dataset_manifest_hash=(
                preflight["dataset"]["manifest_hash"]
                if preflight["dataset"] is not None
                else None
            ),
            dataset_role=(
                DatasetRole(item["dataset_role"])
                if item["dataset_role"] is not None
                else None
            ),
            schedule_seed=suite.seed,
            schedule_order=item["order"],
            schedule_row_id=item["schedule_row_id"],
            repetition=item["repetition"],
        )
        manifest = build_manifest(
            package,
            provider=suite.model,
            model_id=suite.model_id,
            memory_condition=MemoryCondition(item["condition"]),
            sandbox_backend=sandbox_backend,
            budget=suite.budget,
            agent_image_digest=evaluator_digest,
            evaluator_image_digest=evaluator_digest,
            input_price_per_million_usd=suite.input_price_per_million_usd,
            cached_input_price_per_million_usd=(
                suite.cached_input_price_per_million_usd
            ),
            cache_write_input_price_per_million_usd=(
                suite.cache_write_input_price_per_million_usd
            ),
            output_price_per_million_usd=suite.output_price_per_million_usd,
            reasoning_effort=suite.reasoning_effort,
            reasoning_mode=suite.reasoning_mode,
            service_tier=suite.service_tier,
            transport_max_retries=suite.transport_max_retries,
            max_output_tokens=suite.max_output_tokens,
            fault=_diagnostic_fault(suite),
            experiment_context=experiment_context,
            corrective_validation=(
                suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
            ),
            saturation_live_pilot=(
                suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
            ),
            review_evidence_live_pilot=(
                suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
            ),
            coverage_review_live_pilot=(
                suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
            ),
            coverage_rejection_live_pilot=(
                suite.purpose
                == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
            ),
            public_review_contract=(
                PublicReviewContract.model_validate(
                    task_row["public_review_contract"]
                )
                if "public_review_contract" in task_row
                else None
            ),
        )
        _assert_manifest_matches_preflight(
            manifest,
            suite=suite,
            preflight=preflight,
            item={**task_row, **item},
        )
        journal_sequence += 1
        journal_hash = _append_campaign_event(
            journal_path,
            sequence=journal_sequence,
            previous_event_hash=journal_hash,
            event_type="RunStarted",
            payload={
                **row_identity,
                "run_id": manifest.run_id,
            },
        )

        try:
            result = runner.start(
                task,
                model=suite.model,
                memory_condition=MemoryCondition(item["condition"]),
                manifest=manifest,
                live_authorization=live_authorization,
            )
            infrastructure_error = None
        except Exception as exc:
            result = _persisted_attempt_result(runner, manifest.run_id)
            infrastructure_error = {
                "type": type(exc).__name__,
                "message": _safe_error_message(exc),
            }
        if (
            result is not None
            and result.get("outcome_kind") == "infrastructure_error"
        ):
            terminal_error = result.get("terminal_error") or {}
            infrastructure_error = {
                "type": terminal_error.get(
                    "type", "InfrastructureErrorOutcome"
                ),
                "message": terminal_error.get(
                    "message", "run ended with an infrastructure error"
                ),
            }
        usage = result.get("usage") if result is not None else None
        if usage is not None:
            actual_model_cost_usd += float(usage.get("model_cost_usd", 0))
        qualification = None
        qualification_error = None
        diagnostic = _diagnostic_result(suite, qualification)
        diagnostic_error = _diagnostic_error(diagnostic)
        if result is not None and qualification_required:
            try:
                qualification = _qualify_terminal_run(manifest.run_id, task)
                diagnostic = _diagnostic_result(suite, qualification)
                diagnostic_error = _diagnostic_error(diagnostic)
                if qualification.get("qualified") is not True:
                    qualification_error = {
                        "type": "TraceQualificationFailed",
                        "message": (
                            "terminal trace did not satisfy deterministic qualification"
                        ),
                    }
            except Exception as exc:
                qualification_error = {
                    "type": type(exc).__name__,
                    "message": _safe_error_message(exc),
                }
        budget_pressure = None
        runner_state = getattr(runner, "state", None)
        if runner_state is not None:
            try:
                budget_pressure = calculate_budget_pressure(
                    manifest,
                    runner_state.list_events(manifest.run_id),
                    result,
                )
            except (TypeError, ValueError) as exc:
                budget_pressure = {
                    "schema_version": "budget-pressure-error-v1",
                    "run_id": manifest.run_id,
                    "error": _safe_error_message(exc),
                }

        result_row = {
            **row_identity,
            "attempt_status": "terminal",
            "run_id": manifest.run_id,
            "usage": usage,
            "result": result,
            "infrastructure_error": infrastructure_error,
            "qualification": qualification,
            "qualification_error": qualification_error,
            "diagnostic": diagnostic,
            "diagnostic_error": diagnostic_error,
            "not_started_reason": None,
        }
        if budget_pressure is not None:
            result_row["budget_pressure"] = budget_pressure
        results.append(result_row)
        journal_sequence += 1
        journal_hash = _append_campaign_event(
            journal_path,
            sequence=journal_sequence,
            previous_event_hash=journal_hash,
            event_type="RunTerminal",
            payload={
                **row_identity,
                "run_id": manifest.run_id,
                "outcome_kind": (
                    result.get("outcome_kind") if result is not None else None
                ),
                "model_cost_usd": (
                    float(usage.get("model_cost_usd", 0)) if usage is not None else 0
                ),
                "infrastructure_error_type": (
                    infrastructure_error["type"]
                    if infrastructure_error is not None
                    else None
                ),
                "qualification_hash": (
                    qualification.get("qualification_hash")
                    if qualification is not None
                    else None
                ),
                "qualification_error_type": (
                    qualification_error["type"]
                    if qualification_error is not None
                    else None
                ),
                "diagnostic_status": (
                    diagnostic.get("status")
                    if diagnostic is not None
                    else None
                ),
                "diagnostic_error_type": (
                    diagnostic_error["type"]
                    if diagnostic_error is not None
                    else None
                ),
            },
        )
        if infrastructure_error is not None:
            halt_reason = {
                "type": "InfrastructureFailureHalt",
                "message": (
                    "campaign halted after the first infrastructure error: "
                    f"{infrastructure_error['type']}"
                ),
            }
        elif qualification_error is not None:
            halt_reason = {
                "type": "QualificationFailureHalt",
                "message": (
                    "campaign halted after trace qualification failed: "
                    f"{qualification_error['type']}"
                ),
            }
        elif diagnostic_error is not None:
            halt_reason = {
                "type": "TraceExerciseHalt",
                "message": (
                    "campaign halted after required trace exercise failed: "
                    f"{diagnostic_error['type']}"
                ),
            }

    diagnostic_rows = [
        row["diagnostic"]
        for row in results
        if row.get("diagnostic") is not None
    ]
    record = {
        "schema_version": "experiment-result-v2",
        "experiment_id": suite.experiment_id,
        "purpose": suite.purpose.value,
        "suite_hash": preflight["suite_hash"],
        "execution_hash": preflight["execution_hash"],
        "schedule_hash": preflight["schedule_hash"],
        "created_at": utc_now().isoformat(),
        "schedule_seed": suite.seed,
        "expected_runs": len(preflight["schedule"]),
        "completed_runs": sum(
            row["result"] is not None and row["infrastructure_error"] is None
            for row in results
        ),
        "infrastructure_errors": sum(
            row["infrastructure_error"] is not None for row in results
        ),
        "qualification_errors": sum(
            row["qualification_error"] is not None for row in results
        ),
        "diagnostic_errors": sum(
            row.get("diagnostic_error") is not None for row in results
        ),
        "diagnostic_gate": (
            {
                "profile": suite.diagnostic.profile,
                "required_trace_features": list(
                    suite.diagnostic.required_trace_features
                ),
                "passed": bool(
                    len(diagnostic_rows) == len(preflight["schedule"])
                    and diagnostic_rows
                    and all(
                        item.get("status") == "passed"
                        for item in diagnostic_rows
                    )
                ),
                "passed_runs": sum(
                    item.get("status") == "passed"
                    for item in diagnostic_rows
                ),
                "inconclusive_runs": sum(
                    item.get("status") == "inconclusive"
                    for item in diagnostic_rows
                ),
                "failed_runs": sum(
                    item.get("status") == "failed"
                    for item in diagnostic_rows
                ),
            }
            if suite.diagnostic is not None
            else None
        ),
        "completion_gate": _completion_gate(
            suite,
            results,
            expected_execution_hash=preflight["execution_hash"],
            expected_schedule=preflight["schedule"],
        ),
        "not_started_runs": sum(
            row["attempt_status"] == "not_started" for row in results
        ),
        "halt_reason": halt_reason,
        "actual_model_cost_usd": actual_model_cost_usd,
        "dataset": preflight["dataset"],
        "execution_plan": plan,
        "campaign_journal": {
            "path": str(journal_path),
            "last_event_hash_before_completion": journal_hash,
        },
        "suite": _suite_payload(suite),
        "preflight": {
            key: preflight[key]
            for key in (
                "suite_hash",
                "execution_hash",
                "schedule_hash",
                "expected_runs",
            )
        },
        "runs": results,
    }
    output = runtime_root() / "experiments" / f"{suite.experiment_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded_record = json.dumps(record, indent=2, ensure_ascii=False)
    result_hash = sha256_bytes(encoded_record.encode("utf-8"))
    journal_sequence += 1
    _append_campaign_event(
        journal_path,
        sequence=journal_sequence,
        previous_event_hash=journal_hash,
        event_type="CampaignCompleted",
        payload={
            "experiment_id": suite.experiment_id,
            "result_hash": result_hash,
            "completed_runs": record["completed_runs"],
            "infrastructure_errors": record["infrastructure_errors"],
            "not_started_runs": record["not_started_runs"],
        },
    )
    temporary = output.with_suffix(".json.tmp")
    temporary.write_bytes(encoded_record.encode("utf-8"))
    os.replace(temporary, output)
    return {"experiment_id": suite.experiment_id, "path": str(output), **record}
