from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.review import (
    normalize_public_issue_text,
    public_review_contract_content_hash,
    public_review_requirement_id,
)
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    PublicReviewContract,
    RunManifest,
)
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package

MINI_MODEL_ID = "gpt-5.4-mini-2026-03-17"
DEV_TASK = Path(
    "tasks/dev-train/loguru-invalid-format-feedback/public.yaml"
)
CORE_TASK = Path(
    "tasks/same-repo-heldout/"
    "anyio-extensionless-entrypoint-worker-main/public.yaml"
)
FROZEN_COMPARISON_BUDGET = Budget(
    max_model_calls=None,
    max_tool_calls=None,
    max_total_tokens=1_600_000,
    wall_clock_timeout_seconds=1_800,
)


def _experiment_context(
    purpose: ExperimentPurpose,
    *,
    dataset_role: DatasetRole,
) -> ExperimentRunContext:
    return ExperimentRunContext(
        experiment_id=(
            "dev-no-memory-v5-20260730-r1"
            if purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
            else "core-d084-offline-contract"
        ),
        purpose=purpose,
        suite_hash="sha256:" + "a" * 64,
        execution_hash="sha256:" + "b" * 64,
        dataset_manifest_hash="sha256:" + "c" * 64,
        dataset_role=dataset_role,
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id="sha256:" + "d" * 64,
        repetition=1,
    )


def _exact_manifest(
    *,
    purpose: ExperimentPurpose = (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
    ),
    memory_condition: MemoryCondition = MemoryCondition.NO_MEMORY,
) -> RunManifest:
    task_path = (
        DEV_TASK
        if purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        else CORE_TASK
    )
    dataset_role = (
        DatasetRole.MEMORY_DEVELOPMENT
        if purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
        else DatasetRole.CORE_SAME_REPO
    )
    package = load_task_package(task_path.parent)
    manifest = build_manifest(
        package,
        run_id=(
            "run_d084_development_manifest"
            if purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
            else "run_d084_core_manifest"
        ),
        provider="openai",
        model_id=MINI_MODEL_ID,
        memory_condition=MemoryCondition.NO_MEMORY,
        sandbox_backend="docker",
        budget=FROZEN_COMPARISON_BUDGET,
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        experiment_context=_experiment_context(
            purpose,
            dataset_role=dataset_role,
        ),
    )
    if memory_condition == MemoryCondition.NO_MEMORY:
        return manifest
    payload = manifest.model_dump(mode="json")
    payload["memory"]["condition"] = memory_condition.value
    return RunManifest.model_validate(payload)


def _review_contract(manifest: RunManifest) -> PublicReviewContract:
    package = load_task_package(DEV_TASK.parent)
    excerpt = normalize_public_issue_text(package.public.issue.description)
    payload: dict[str, Any] = {
        "schema_version": "public-review-contract-v1",
        "task_id": manifest.task_id,
        "task_version": manifest.task_version,
        "public_spec_hash": manifest.public_spec_hash,
        "requirements": [
            {
                "requirement_id": public_review_requirement_id(excerpt),
                "source": "issue.description",
                "source_excerpt": excerpt,
            }
        ],
    }
    payload["content_hash"] = public_review_contract_content_hash(payload)
    return PublicReviewContract.model_validate(payload)


def _replace(payload: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    target: dict[str, Any] = payload
    for key in path[:-1]:
        child = target[key]
        assert isinstance(child, dict)
        target = child
    target[path[-1]] = value


def test_d084_exact_development_manifest_accepts_frozen_profile() -> None:
    manifest = _exact_manifest()

    assert manifest.experiment is not None
    assert (
        manifest.experiment.purpose
        == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
    )
    assert manifest.memory.condition == MemoryCondition.NO_MEMORY
    assert manifest.budget == FROZEN_COMPARISON_BUDGET
    assert manifest.model.model_id == MINI_MODEL_ID
    assert manifest.model.transport_max_retries == 0
    assert manifest.tool_schema_version == "v2"
    assert manifest.context_policy_version == "phase-evidence-v5"


@pytest.mark.parametrize("condition", list(MemoryCondition))
def test_d084_core_manifest_accepts_every_memory_condition(
    condition: MemoryCondition,
) -> None:
    manifest = _exact_manifest(
        purpose=ExperimentPurpose.CORE,
        memory_condition=condition,
    )

    assert manifest.experiment is not None
    assert manifest.experiment.purpose == ExperimentPurpose.CORE
    assert manifest.memory.condition == condition
    assert manifest.budget == FROZEN_COMPARISON_BUDGET


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("tool_schema_version",), "v1"),
        (("context_policy_version",), "phase-evidence-v4"),
        (("model", "provider"), "mock"),
        (("model", "model_id"), "gpt-5.4-mini"),
        (("model", "reasoning_effort"), "low"),
        (("model", "reasoning_mode"), "pro"),
        (("model", "service_tier"), "flex"),
        (("model", "transport_max_retries"), None),
        (("model", "max_output_tokens"), 24_999),
        (("budget", "max_total_tokens"), 1_599_999),
        (("budget", "wall_clock_timeout_seconds"), 1_799),
        (("memory", "max_context_tokens"), 1_999),
        (("fault", "type"), "context-reset"),
        (("experiment", "purpose"), "offline-smoke"),
    ],
)
def test_d084_disabled_count_manifest_rejects_tuple_drift(
    path: tuple[str, ...],
    replacement: Any,
) -> None:
    payload = _exact_manifest().model_dump(mode="json")
    _replace(payload, path, replacement)

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("model_limit", "tool_limit"),
    [(1, None), (None, 1)],
)
def test_d084_manifest_rejects_partial_null_call_limits(
    model_limit: int | None,
    tool_limit: int | None,
) -> None:
    payload = _exact_manifest().model_dump(mode="json")
    payload["budget"]["max_model_calls"] = model_limit
    payload["budget"]["max_tool_calls"] = tool_limit

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_d084_development_profile_rejects_non_no_memory_condition() -> None:
    payload = _exact_manifest().model_dump(mode="json")
    payload["memory"]["condition"] = MemoryCondition.RAW_TRACE.value

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_d084_profile_requires_an_experiment_contract() -> None:
    payload = _exact_manifest().model_dump(mode="json")
    payload["experiment"] = None

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_d084_profile_rejects_public_review_sidecar() -> None:
    manifest = _exact_manifest()
    payload = manifest.model_dump(mode="json")
    payload["public_review_contract"] = _review_contract(manifest).model_dump(
        mode="json"
    )

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_d084_preserves_finite_count_historical_memory_manifest() -> None:
    payload = _exact_manifest().model_dump(mode="json")
    payload["experiment"]["experiment_id"] = "dev-no-memory-20260728"
    payload["budget"] = {
        "max_model_calls": 21,
        "max_tool_calls": 50,
        "max_total_tokens": 200_000,
        "wall_clock_timeout_seconds": 900,
    }
    payload["model"]["transport_max_retries"] = None

    historical = RunManifest.model_validate(payload)

    assert historical.budget.max_model_calls == 21
    assert historical.budget.max_tool_calls == 50
    assert historical.budget.max_total_tokens == 200_000


@pytest.mark.parametrize(
    ("purpose", "experiment_id", "task_id", "budget"),
    [
        (
            ExperimentPurpose.GENERIC_BASELINE_READINESS.value,
            "generic-baseline-readiness-v2v5-20260803-r3",
            "babel-strict-grouped-decimal-trailing-zeroes",
            {
                "max_model_calls": None,
                "max_tool_calls": None,
                "max_total_tokens": 2_400_000,
                "wall_clock_timeout_seconds": 1_800,
            },
        ),
        (
            ExperimentPurpose.WORKFLOW_COMPLETION_PROBE.value,
            "pyfakefs-workflow-completion-probe-v2v5-20260803-r1",
            "pyfakefs-makedirs-parent-traversal",
            {
                "max_model_calls": None,
                "max_tool_calls": None,
                "max_total_tokens": 3_000_000,
                "wall_clock_timeout_seconds": 7_200,
            },
        ),
    ],
)
def test_d084_preserves_registered_historical_null_limit_profiles(
    purpose: str,
    experiment_id: str,
    task_id: str,
    budget: dict[str, Any],
) -> None:
    payload = deepcopy(_exact_manifest().model_dump(mode="json"))
    payload["experiment"]["purpose"] = purpose
    payload["experiment"]["experiment_id"] = experiment_id
    payload["task_id"] = task_id
    payload["budget"] = budget

    historical = RunManifest.model_validate(payload)

    assert historical.experiment is not None
    assert historical.experiment.experiment_id == experiment_id
    assert historical.budget.max_model_calls is None
    assert historical.budget.max_tool_calls is None
