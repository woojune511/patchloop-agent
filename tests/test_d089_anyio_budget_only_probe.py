from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from patchloop.contracts import (
    CONDITION_NEUTRAL_BUDGET_READINESS_PROBE_EXPERIMENT_ID,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
)
from patchloop.evals import qualification as qualification_module
from patchloop.evals import runner as eval_runner
from patchloop.evals.budget import calculate_budget_pressure
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes
from tests.test_workflow_completion_probe_qualification import (
    _minimal_probe_trace,
)

SUITE_PATH = Path(
    "experiments/"
    "anyio-workflow-completion-budget-only-v2v5-20260804-r1.yaml"
)
D087_IMMUTABLE_FILES = {
    Path("experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml"):
        "sha256:44de6899656c96830d3a0aa3326777848c5d632ef903eccc166839fa1caeaf79",
    Path(
        "reports/live-pilot/"
        "dev-no-memory-condition-neutral-accrued-cap-20260804-r1.json"
    ): "sha256:2e24bfb0d98c2a7b2b0d8b5bf80c238ae048d782ce43c1cf08a2c10a6c6b5269",
    Path(
        "reports/live-pilot/artifacts/"
        "d087-condition-neutral-comparison-accrued-spend-cap-source-gate.json"
    ): "sha256:5f038999b65930a0f155d5eb00a530ac06b6e359de0bdac12fff22398aaa7efe",
}


def _payload() -> dict[str, Any]:
    return yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))


def _ready_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-rendered")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": "a" * 40, "clean": True},
    )
    monkeypatch.setattr(
        eval_runner,
        "_docker_image_state",
        lambda images: {
            "available": True,
            "images": [
                {
                    "image": image,
                    "identity": image.rsplit("@", 1)[-1],
                    "ready": True,
                }
                for image in sorted(set(images))
            ],
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_openai_sdk_state",
        lambda: {"installed": True, "version": "2.47.0"},
    )
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 4, 6, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")


def _exact_manifest() -> RunManifest:
    package = load_task_package(
        Path(eval_runner.ANYIO_BUDGET_READINESS_PROBE_TASK).parent
    )
    return build_manifest(
        package,
        run_id="run_d089_contract",
        provider="openai",
        model_id=eval_runner.GPT54_MINI_PILOT_MODEL_ID,
        memory_condition=MemoryCondition.NO_MEMORY,
        sandbox_backend="docker",
        budget=eval_runner.GPT54_MINI_ANYIO_BUDGET_READINESS_PROBE_BUDGET,
        transport_max_retries=0,
        max_output_tokens=25_000,
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        output_price_per_million_usd=4.5,
        experiment_context=ExperimentRunContext(
            experiment_id=(
                CONDITION_NEUTRAL_BUDGET_READINESS_PROBE_EXPERIMENT_ID
            ),
            purpose=ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash="sha256:" + ("b" * 64),
            dataset_manifest_hash="sha256:" + ("c" * 64),
            dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("d" * 64),
            repetition=1,
        ),
    )


def _passing_row(preflight: dict[str, Any]) -> dict[str, Any]:
    schedule = preflight["schedule"][0]
    run_id = "run_d089_gate"
    return {
        **{
            key: schedule[key]
            for key in (
                "order",
                "schedule_row_id",
                "task_id",
                "split",
                "dataset_role",
                "condition",
                "repetition",
            )
        },
        "attempt_status": "terminal",
        "run_id": run_id,
        "result": {
            "run_id": run_id,
            "official": True,
            "evaluation_status": "completed",
            "outcome_kind": "task_failure",
            "scope_compliant_success": False,
            "terminal_error": None,
        },
        "qualification": {
            "run_id": run_id,
            "qualified": True,
            "evaluation_reached": True,
            "task_id": schedule["task_id"],
            "schedule_row_id": schedule["schedule_row_id"],
            "execution_hash": preflight["execution_hash"],
            "gate_checks": {
                "disabled_call_guard_contract": {
                    "schema_version": "qualification-gate-check-projection-v1",
                    "check_id": "disabled_call_guard_contract",
                    "check_count": 1,
                    "passed": True,
                }
            },
        },
        "infrastructure_error": None,
        "qualification_error": None,
        "diagnostic_error": None,
    }


def test_d089_source_is_exactly_one_anyio_budget_only_probe() -> None:
    suite = eval_runner.load_suite(SUITE_PATH)
    pricing = eval_runner._pricing_contract(suite, schedule_size=1)

    assert suite.experiment_id == (
        CONDITION_NEUTRAL_BUDGET_READINESS_PROBE_EXPERIMENT_ID
    )
    assert suite.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
    assert suite.tasks == [eval_runner.ANYIO_BUDGET_READINESS_PROBE_TASK]
    assert suite.conditions == [MemoryCondition.NO_MEMORY]
    assert suite.repetitions == 1
    assert suite.model_id == "gpt-5.4-mini-2026-03-17"
    assert suite.reasoning_effort == "medium"
    assert suite.reasoning_mode == "standard"
    assert suite.service_tier == "default"
    assert suite.transport_max_retries == 0
    assert suite.max_output_tokens == 25_000
    assert suite.budget.model_dump(mode="json") == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 2_000_000,
        "wall_clock_timeout_seconds": 1_800,
    }
    assert suite.estimated_cost_usd == 9.1125
    assert suite.cost_limit_usd == 10
    assert suite.live_cost_approved is False
    assert suite.approved_execution_hash is None
    assert suite.pilot_run_id is None
    assert pricing["per_run_cost_reserve_usd"] == 9.1125
    assert pricing["budget_upper_bound_usd"] == 9.1125


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment_id",), "anyio-budget-probe-wrong"),
        (("purpose",), "memory-development-no-memory"),
        (("tasks",), [eval_runner.WORKFLOW_COMPLETION_PROBE_TASK]),
        (("conditions",), ["raw_trace"]),
        (("repetitions",), 2),
        (("transport_max_retries",), None),
        (("max_output_tokens",), 24_999),
        (("memory_token_budget",), 1_999),
        (("budget", "max_model_calls"), 100),
        (("budget", "max_tool_calls"), 100),
        (("budget", "max_total_tokens"), 1_600_000),
        (("budget", "wall_clock_timeout_seconds"), 1_801),
        (("estimated_cost_usd",), 9.0),
        (("cost_limit_usd",), 11),
        (("live_cost_approved",), True),
        (("approved_execution_hash",), "sha256:" + ("1" * 64)),
        (("pilot_run_id",), "run_forbidden"),
    ],
)
def test_d089_source_drift_fails_closed(
    path: tuple[str, ...],
    replacement: Any,
) -> None:
    payload = _payload()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValidationError):
        eval_runner.ExperimentSuite.model_validate(payload)


def test_d089_manifest_and_budget_diagnostic_bind_the_2m_profile() -> None:
    manifest = _exact_manifest()
    diagnostic = calculate_budget_pressure(manifest, [])

    assert manifest.task_id == eval_runner.ANYIO_BUDGET_READINESS_PROBE_TASK_ID
    assert manifest.tool_schema_version == "v2"
    assert manifest.context_policy_version == "phase-evidence-v5"
    assert manifest.budget == (
        eval_runner.GPT54_MINI_ANYIO_BUDGET_READINESS_PROBE_BUDGET
    )
    assert diagnostic["configured_limits"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 2_000_000,
        "wall_clock_ms": 1_800_000,
    }
    assert diagnostic["binding_dimension"] == "none"


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment", "purpose"), "memory-development-no-memory"),
        (("experiment", "experiment_id"), "d089-wrong"),
        (("task_id",), "different-task"),
        (("model", "model_id"), "different-model"),
        (("model", "transport_max_retries"), None),
        (("budget", "max_model_calls"), 1),
        (("budget", "max_tool_calls"), 1),
        (("budget", "max_total_tokens"), 1_999_999),
        (("budget", "wall_clock_timeout_seconds"), 1_799),
        (("memory", "max_context_tokens"), 1_999),
        (("memory", "condition"), "raw_trace"),
        (("fault", "type"), "context-reset"),
    ],
)
def test_d089_manifest_drift_fails_closed(
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


def test_d089_claim_cannot_fall_through_to_the_1_6m_comparison_profile() -> None:
    payload = _exact_manifest().model_dump(mode="json")
    payload["experiment"]["purpose"] = "memory-development-no-memory"
    payload["budget"]["max_total_tokens"] = 1_600_000

    with pytest.raises(ValueError, match="D-089 budget-only readiness"):
        RunManifest.model_validate(payload)
    with pytest.raises(ValueError):
        calculate_budget_pressure(payload, [])


def test_d089_diagnostic_rejects_finite_call_limit_near_match() -> None:
    payload = _exact_manifest().model_dump(mode="json")
    payload["budget"]["max_model_calls"] = 1
    payload["budget"]["max_tool_calls"] = 1

    with pytest.raises(ValueError, match="D-089 budget-only readiness"):
        calculate_budget_pressure(payload, [])


def test_d089_no_call_preflight_needs_only_invocation_approval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)

    preflight = eval_runner.preflight_suite(SUITE_PATH)

    assert preflight["ready"] is False
    assert {blocker["code"] for blocker in preflight["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["expected_runs"] == 1
    assert preflight["schedule"][0]["task_id"] == (
        eval_runner.ANYIO_BUDGET_READINESS_PROBE_TASK_ID
    )
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == 9.1125
    assert preflight["pricing"]["budget_upper_bound_usd"] == 9.1125
    assert preflight["runtime_contract"]["schema_version"] == (
        eval_runner.WORKFLOW_COMPLETION_RUNTIME_CONTRACT_SCHEMA
    )
    assert "test-secret-never-rendered" not in str(preflight)

    approved = eval_runner.preflight_suite(
        SUITE_PATH,
        approve_live_cost=True,
        approved_execution_hash=preflight["execution_hash"],
    )
    assert approved["ready"] is True
    assert approved["blockers"] == []
    assert approved["execution_hash"] == preflight["execution_hash"]

    plan = {**approved, "schema_version": "experiment-execution-plan-v1"}
    suite = eval_runner.ExperimentSuite.model_validate(plan["suite"])
    schedule_row = plan["schedule"][0]
    task_row = next(
        row
        for row in plan["tasks"]
        if row["task_id"] == schedule_row["task_id"]
    )
    package = load_task_package(Path(task_row["task"]).parent)
    manifest = build_manifest(
        package,
        run_id="run_d089_plan_qualification",
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(schedule_row["condition"]),
        sandbox_backend="docker",
        budget=suite.budget,
        agent_image_digest=task_row["evaluator_image_digest"],
        evaluator_image_digest=task_row["evaluator_image_digest"],
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
        experiment_context=ExperimentRunContext(
            experiment_id=suite.experiment_id,
            purpose=suite.purpose,
            suite_hash=plan["suite_hash"],
            execution_hash=plan["execution_hash"],
            campaign_cost_control_hash=(
                plan["campaign_cost_control"]["content_hash"]
                if isinstance(plan.get("campaign_cost_control"), dict)
                else None
            ),
            dataset_manifest_hash=plan["dataset"]["manifest_hash"],
            dataset_role=DatasetRole(schedule_row["dataset_role"]),
            schedule_seed=suite.seed,
            schedule_order=schedule_row["order"],
            schedule_row_id=schedule_row["schedule_row_id"],
            repetition=schedule_row["repetition"],
        ),
    )
    manifest.harness_git_commit = "a" * 40
    manifest.model.provider_sdk_version = plan["environment"]["openai_sdk"][
        "version"
    ]
    eval_runner._assert_manifest_matches_preflight(
        manifest,
        suite=suite,
        preflight=plan,
        item={**task_row, **schedule_row},
    )
    assert qualification_module._execution_plan_matches(
        plan=plan,
        manifest=manifest,
    )

    persisted = eval_runner._persist_preflight_plan(approved)
    assert Path(persisted["path"]).is_file()
    runtime_root = tmp_path / "runtime"
    _minimal_probe_trace(
        runtime_root,
        run_id=manifest.run_id,
        manifest=manifest,
    )
    qualification = qualification_module.qualify_run(
        manifest.run_id,
        task_dir=Path(eval_runner.ANYIO_BUDGET_READINESS_PROBE_TASK).parent,
        root=runtime_root,
        persist=False,
    )
    checks = {check["check_id"]: check for check in qualification["checks"]}
    assert qualification["experiment_id"] == suite.experiment_id
    assert qualification["task_id"] == (
        eval_runner.ANYIO_BUDGET_READINESS_PROBE_TASK_ID
    )
    for check_id in (
        "approved_execution_plan",
        "generic_runtime_contract",
        "disabled_call_guard_contract",
        "frozen_model_contract",
    ):
        assert checks[check_id]["passed"] is True, checks[check_id]


def test_d089_process_gate_does_not_require_hidden_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(SUITE_PATH)
    row = _passing_row(preflight)

    gate = eval_runner._completion_gate(
        eval_runner.load_suite(SUITE_PATH),
        [row],
        expected_execution_hash=preflight["execution_hash"],
        expected_schedule=preflight["schedule"],
    )

    assert gate is not None
    assert gate["schema_version"] == "workflow-completion-probe-gate-v1"
    assert gate["gate_id"] == eval_runner.ANYIO_BUDGET_READINESS_PROBE_GATE_ID
    assert gate["budget_only_probe"] is True
    assert gate["calibration_only"] is True
    assert gate["passed"] is True
    assert gate["terminal_runs"] == 1
    assert gate["qualified_runs"] == 1
    assert gate["official_evaluator_runs"] == 1
    assert gate["budget_terminal_runs"] == 0
    assert gate["task_successes"] == 0
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "nonterminal",
        "unqualified",
        "evaluator_not_reached",
        "unofficial",
        "infrastructure",
        "qualification_error",
        "diagnostic_error",
        "budget_terminal",
        "terminal_loop",
        "missing_call_guard",
        "execution_hash",
        "schedule_row",
    ],
)
def test_d089_process_gate_rejects_process_confounds(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(SUITE_PATH)
    row = _passing_row(preflight)
    if mutation == "nonterminal":
        row["attempt_status"] = "not_started"
    elif mutation == "unqualified":
        row["qualification"]["qualified"] = False
    elif mutation == "evaluator_not_reached":
        row["qualification"]["evaluation_reached"] = False
    elif mutation == "unofficial":
        row["result"]["official"] = False
    elif mutation == "infrastructure":
        row["infrastructure_error"] = {"type": "InfrastructureError"}
    elif mutation == "qualification_error":
        row["qualification_error"] = {"type": "QualificationError"}
    elif mutation == "diagnostic_error":
        row["diagnostic_error"] = {"type": "DiagnosticError"}
    elif mutation == "budget_terminal":
        row["result"]["terminal_error"] = {
            "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
            "details": {"reason_code": "exact_request_budget_exceeded"},
        }
    elif mutation == "terminal_loop":
        row["result"]["terminal_error"] = {
            "code": "TERMINAL_LOOP_DETECTED",
            "details": {"reason_code": "terminal_loop_failure"},
        }
    elif mutation == "missing_call_guard":
        row["qualification"]["gate_checks"] = {}
    elif mutation == "execution_hash":
        row["qualification"]["execution_hash"] = "sha256:" + ("f" * 64)
    else:
        row["schedule_row_id"] = "sha256:" + ("e" * 64)

    gate = eval_runner._completion_gate(
        eval_runner.load_suite(SUITE_PATH),
        [row],
        expected_execution_hash=preflight["execution_hash"],
        expected_schedule=preflight["schedule"],
    )
    assert gate is not None
    assert gate["passed"] is False


def test_d089_does_not_rewrite_or_reopen_d087_or_d079() -> None:
    for path, expected_hash in D087_IMMUTABLE_FILES.items():
        assert sha256_bytes(path.read_bytes()) == expected_hash
    assert eval_runner.WORKFLOW_COMPLETION_PROBE_EXPERIMENT_ID in (
        eval_runner.CONSUMED_WORKFLOW_COMPLETION_PROBE_EXPERIMENT_IDS
    )
    assert eval_runner.ANYIO_BUDGET_READINESS_PROBE_EXPERIMENT_ID not in (
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
    )
    assert eval_runner.GPT54_MINI_FROZEN_COMPARISON_BUDGET.max_total_tokens == (
        1_600_000
    )
