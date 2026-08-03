from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    RunManifest,
    Usage,
)
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.evals.budget import calculate_budget_pressure
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package


def _exact_manifest() -> RunManifest:
    task = eval_runner.GENERIC_BASELINE_READINESS_TASKS[0]
    package = load_task_package(Path(task).parent)
    return build_manifest(
        package,
        run_id="run_d081_observability_contract",
        provider="openai",
        model_id=eval_runner.GPT54_MINI_PILOT_MODEL_ID,
        sandbox_backend="docker",
        budget=eval_runner.GPT54_MINI_GENERIC_BASELINE_READINESS_D081_BUDGET,
        transport_max_retries=0,
        max_output_tokens=25_000,
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        output_price_per_million_usd=4.5,
        experiment_context=ExperimentRunContext(
            experiment_id=(
                eval_runner.GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID
            ),
            purpose=ExperimentPurpose.GENERIC_BASELINE_READINESS,
            suite_hash="sha256:" + "a" * 64,
            execution_hash="sha256:" + "b" * 64,
            dataset_manifest_hash="sha256:" + "c" * 64,
            dataset_role=DatasetRole.DEVELOPMENT_VALIDATION,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + "d" * 64,
            repetition=1,
        ),
    )


def test_d081_manifest_and_budget_diagnostic_accept_exact_null_limits() -> None:
    manifest = _exact_manifest()

    assert manifest.budget.max_model_calls is None
    assert manifest.budget.max_tool_calls is None
    assert manifest.budget.max_total_tokens == 2_400_000
    assert manifest.budget.wall_clock_timeout_seconds == 1_800
    diagnostic = calculate_budget_pressure(manifest, [])
    assert diagnostic["configured_limits"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 2_400_000,
        "wall_clock_ms": 1_800_000,
    }
    assert diagnostic["binding_dimension"] == "none"


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment", "experiment_id"), "generic-readiness-wrong"),
        (("experiment", "purpose"), "workflow-completion-probe"),
        (("task_id",), "different-task"),
        (("budget", "max_model_calls"), 110),
        (("budget", "max_tool_calls"), 150),
        (("budget", "max_total_tokens"), 2_399_999),
        (("budget", "wall_clock_timeout_seconds"), 1_799),
        (("model", "model_id"), "different-model"),
        (("model", "max_output_tokens"), 24_999),
        (("model", "transport_max_retries"), None),
        (("memory", "condition"), "raw_trace"),
    ],
)
def test_d081_manifest_rejects_identity_or_budget_drift(
    path: tuple[str, ...],
    replacement: Any,
) -> None:
    payload = _exact_manifest().model_dump(mode="json")
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_d081_disables_only_call_count_guards() -> None:
    manifest = _exact_manifest()
    within_token_and_wall = Usage(
        model_calls=10_000_000,
        tool_calls=10_000_000,
        input_tokens=2_000_000,
        output_tokens=399_999,
        wall_clock_ms=1_799_999,
    )

    assert (
        AgentRunner._pre_generation_budget_reason(
            manifest,
            within_token_and_wall,
        )
        is None
    )
    AgentRunner._assert_budget(None, manifest, within_token_and_wall)
    AgentRunner._assert_consumed_budget(manifest, within_token_and_wall)

    token_exhausted = within_token_and_wall.model_copy(
        update={"output_tokens": 400_000}
    )
    with pytest.raises(ContractError, match="token budget exhausted"):
        AgentRunner._assert_budget(None, manifest, token_exhausted)

    wall_exhausted = within_token_and_wall.model_copy(
        update={"wall_clock_ms": 1_800_000}
    )
    assert AgentRunner._pre_generation_budget_reason(
        manifest,
        wall_exhausted,
    ) == (
        "wall_clock_budget_exhausted"
    )


def test_d081_runtime_evidence_and_gate_projection_are_versioned() -> None:
    manifest = _exact_manifest()
    runtime_document = AgentRunner._generic_baseline_runtime_evidence_document(
        manifest=manifest,
        system_prompt=eval_runner.SYSTEM_PROMPT_V3,
        tool_schemas=eval_runner.TOOL_SCHEMAS_V2,
    )

    assert runtime_document == {
        "schema_version": "generic-baseline-runtime-evidence-v2",
        "transport_max_retries": 0,
        "system_prompt": eval_runner.SYSTEM_PROMPT_V3,
        "tools": eval_runner.TOOL_SCHEMAS_V2,
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "call_guard_policy": "model-tool-observability-only-v1",
    }

    summary = eval_runner._terminal_qualification_summary(
        {
            "purpose": ExperimentPurpose.GENERIC_BASELINE_READINESS.value,
            "experiment_id": (
                eval_runner.GENERIC_BASELINE_READINESS_D081_EXPERIMENT_ID
            ),
            "checks": [
                {
                    "check_id": "disabled_call_guard_contract",
                    "passed": True,
                    "details": {"must_not_be_projected": "private"},
                }
            ],
        }
    )
    assert summary["gate_checks"] == {
        "disabled_call_guard_contract": {
            "schema_version": "qualification-gate-check-projection-v1",
            "check_id": "disabled_call_guard_contract",
            "check_count": 1,
            "passed": True,
        }
    }
    assert "checks" not in summary
