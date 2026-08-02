from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
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
from patchloop.evals import report as report_module
from patchloop.evals import runner as eval_runner
from patchloop.evals.budget import calculate_budget_pressure
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package

SUITE_PATH = Path(
    "experiments/pyfakefs-workflow-completion-probe-v2v5-20260803-r1.yaml"
)


def _suite_payload() -> dict[str, Any]:
    return yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))


def _exact_manifest() -> RunManifest:
    package = load_task_package(
        Path(eval_runner.WORKFLOW_COMPLETION_PROBE_TASK).parent
    )
    return build_manifest(
        package,
        run_id="run_workflow_completion_contract",
        provider="openai",
        model_id=eval_runner.GPT54_MINI_PILOT_MODEL_ID,
        sandbox_backend="docker",
        budget=eval_runner.GPT54_MINI_WORKFLOW_COMPLETION_PROBE_BUDGET,
        transport_max_retries=0,
        max_output_tokens=25_000,
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        output_price_per_million_usd=4.5,
        experiment_context=ExperimentRunContext(
            experiment_id=eval_runner.WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID,
            purpose=ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
            suite_hash="sha256:" + "a" * 64,
            execution_hash="sha256:" + "b" * 64,
            dataset_manifest_hash="sha256:" + "c" * 64,
            dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + "d" * 64,
            repetition=1,
        ),
    )


def test_workflow_completion_probe_suite_loads_exact_contract() -> None:
    suite = eval_runner.load_suite(SUITE_PATH)
    pricing = eval_runner._pricing_contract(suite, schedule_size=1)

    assert suite.experiment_id == (
        eval_runner.WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID
    )
    assert suite.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
    assert suite.tasks == [eval_runner.WORKFLOW_COMPLETION_PROBE_TASK]
    assert [condition.value for condition in suite.conditions] == ["no_memory"]
    assert suite.repetitions == 1
    assert suite.model == "openai"
    assert suite.model_id == eval_runner.GPT54_MINI_PILOT_MODEL_ID
    assert suite.transport_max_retries == 0
    assert suite.max_output_tokens == 25_000
    assert suite.budget == (
        eval_runner.GPT54_MINI_WORKFLOW_COMPLETION_PROBE_BUDGET
    )
    assert suite.budget.model_dump(mode="json") == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 7_200,
    }
    assert suite.estimated_cost_usd == pytest.approx(13.6125)
    assert suite.cost_limit_usd == 14
    assert suite.live_cost_approved is False
    assert suite.approved_execution_hash is None
    assert suite.pilot_run_id is None
    assert pricing["per_run_cost_reserve_usd"] == pytest.approx(13.6125)
    assert pricing["budget_upper_bound_usd"] == pytest.approx(13.6125)


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_purpose",
        "wrong_id",
        "only_model_limit_disabled",
        "only_tool_limit_disabled",
        "huge_count_sentinel",
        "foreign_purpose_with_null_limits",
    ],
)
def test_workflow_completion_probe_suite_rejects_call_limit_escape_hatches(
    mutation: str,
) -> None:
    payload = _suite_payload()
    budget = payload["budget"]
    if mutation == "wrong_purpose":
        payload["purpose"] = "generic-baseline-readiness"
    elif mutation == "wrong_id":
        payload["experiment_id"] = "pyfakefs-workflow-completion-probe-wrong"
    elif mutation == "only_model_limit_disabled":
        budget["max_tool_calls"] = 100
    elif mutation == "only_tool_limit_disabled":
        budget["max_model_calls"] = 100
    elif mutation == "huge_count_sentinel":
        budget["max_model_calls"] = 2_147_483_647
        budget["max_tool_calls"] = 2_147_483_647
    elif mutation == "foreign_purpose_with_null_limits":
        payload["experiment_id"] = "foreign-null-call-limit-suite"
        payload["purpose"] = "offline-smoke"
        payload["model"] = "mock"
        payload["model_id"] = "mock-v1"
        payload["transport_max_retries"] = None
    else:  # pragma: no cover - parametrization is exhaustive
        raise AssertionError(mutation)

    with pytest.raises(ValidationError):
        eval_runner.ExperimentSuite.model_validate(payload)


def test_workflow_completion_probe_manifest_accepts_only_exact_identity() -> None:
    manifest = _exact_manifest()

    assert manifest.experiment is not None
    assert manifest.experiment.experiment_id == (
        eval_runner.WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID
    )
    assert manifest.experiment.purpose == (
        ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
    )
    assert manifest.task_id == eval_runner.WORKFLOW_COMPLETION_PROBE_TASK_ID
    assert manifest.tool_schema_version == "v2"
    assert manifest.context_policy_version == "phase-evidence-v5"
    assert manifest.model.transport_max_retries == 0
    assert manifest.budget.max_model_calls is None
    assert manifest.budget.max_tool_calls is None


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment", "purpose"), "generic-baseline-readiness"),
        (("experiment", "experiment_id"), "workflow-probe-wrong"),
        (("task_id",), "different-task"),
        (("model", "provider"), "mock"),
        (("model", "model_id"), "different-model"),
        (("model", "max_output_tokens"), 24_999),
        (("model", "transport_max_retries"), None),
        (("budget", "max_model_calls"), 1_000_000),
        (("budget", "max_tool_calls"), 1_000_000),
        (("budget", "max_total_tokens"), 2_999_999),
        (("budget", "wall_clock_timeout_seconds"), 7_199),
        (("memory", "condition"), "raw_trace"),
        (("fault", "type"), "context-reset"),
    ],
)
def test_workflow_completion_probe_manifest_rejects_identity_drift(
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


def test_budget_diagnostic_accepts_null_limits_only_for_exact_probe() -> None:
    manifest = _exact_manifest()

    diagnostic = calculate_budget_pressure(manifest, [])

    assert diagnostic["configured_limits"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 3_000_000,
        "wall_clock_ms": 7_200_000,
    }
    assert diagnostic["headroom"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 3_000_000,
        "wall_clock_ms": None,
    }
    assert diagnostic["binding_dimension"] == "none"


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment", "purpose"), "generic-baseline-readiness"),
        (("experiment", "experiment_id"), "workflow-probe-wrong"),
        (("task_id",), "different-task"),
        (("budget", "max_model_calls"), 100),
        (("budget", "max_tool_calls"), 100),
        (("model", "provider"), "mock"),
        (("model", "model_id"), "different-model"),
        (("model", "max_output_tokens"), 24_999),
        (("tool_schema_version",), "v1"),
        (("context_policy_version",), "v1"),
    ],
)
def test_budget_diagnostic_rejects_non_exact_null_limit_contract(
    path: tuple[str, ...],
    replacement: Any,
) -> None:
    payload = _exact_manifest().model_dump(mode="json")
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValueError, match="workflow completion probe"):
        calculate_budget_pressure(payload, [])


def test_workflow_completion_runtime_disables_only_call_count_guards() -> None:
    manifest = _exact_manifest()
    within_token_and_wall = Usage(
        model_calls=10_000_000,
        tool_calls=10_000_000,
        input_tokens=2_500_000,
        output_tokens=499_999,
        wall_clock_ms=7_199_999,
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
        update={"output_tokens": 500_000}
    )
    with pytest.raises(ContractError, match="token budget exhausted"):
        AgentRunner._assert_budget(None, manifest, token_exhausted)

    wall_exhausted = within_token_and_wall.model_copy(
        update={"wall_clock_ms": 7_200_000}
    )
    assert AgentRunner._pre_generation_budget_reason(
        manifest,
        wall_exhausted,
    ) == "wall_clock_budget_exhausted"
    with pytest.raises(ContractError, match="wall clock budget exhausted"):
        AgentRunner._assert_budget(None, manifest, wall_exhausted)

    token_exceeded = within_token_and_wall.model_copy(
        update={"output_tokens": 500_001}
    )
    with pytest.raises(ContractError, match="token budget exceeded"):
        AgentRunner._assert_consumed_budget(manifest, token_exceeded)


def test_workflow_completion_probe_report_is_calibration_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "runtime"
    experiment_dir = root / "experiments"
    experiment_dir.mkdir(parents=True)
    raw = {
        "purpose": "workflow-completion-probe",
        "schedule_seed": 20260723,
        "expected_runs": 1,
        "infrastructure_errors": 0,
        "suite": {
            "tasks": ["pyfakefs-makedirs-parent-traversal"],
            "conditions": ["no_memory"],
            "repetitions": 1,
        },
        "runs": [
            {
                "task_id": "pyfakefs-makedirs-parent-traversal",
                "split": "dev-train",
                "condition": "no_memory",
                "repetition": 1,
                "attempt_status": "terminal",
                "run_id": "run_workflow_report",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "model_cost_usd": 0.1,
                },
                "result": {
                    "run_id": "run_workflow_report",
                    "outcome_kind": "task_failure",
                    "scope_compliant_success": False,
                    "verdicts": {
                        "hidden_tests": "fail",
                        "regression_tests": "pass",
                        "scope_policy": "pass",
                    },
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "model_cost_usd": 0.1,
                    },
                },
                "infrastructure_error": None,
                "qualification": {"qualified": True},
                "qualification_error": None,
                "diagnostic": None,
                "diagnostic_error": None,
            }
        ],
    }
    (experiment_dir / "workflow-probe.json").write_text(
        json.dumps(raw),
        encoding="utf-8",
    )
    monkeypatch.setattr(report_module, "runtime_root", lambda: root)

    output = tmp_path / "report-workflow-probe"
    report_module.build_report("workflow-probe", output)
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    with (output / "runs.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert "workflow-completion-probe" in report_module._CALIBRATION_ONLY_PURPOSES
    assert report["analysis_ready"] is False
    assert report["metrics"] == {}
    assert report["diagnostic_metrics"]["no_memory"]["runs"] == 1
    assert report["headline_metrics"] is None
    assert len(rows) == 1
    assert rows[0]["calibration_only"] == "1"
    assert rows[0]["analysis_included"] == "0"
    assert rows[0]["exclusion_reason"] == "calibration_only"
