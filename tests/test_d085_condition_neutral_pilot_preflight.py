from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from patchloop.contracts import (
    CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
    ExperimentPurpose,
    MemoryCondition,
)
from patchloop.evals import runner as eval_runner
from patchloop.evals.runner import ExperimentSuite

SUITE_PATH = Path(
    "experiments/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.yaml"
)


def _payload() -> dict:
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
        lambda: datetime(2026, 8, 3, 7, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")


def _passing_row(preflight: dict) -> dict:
    schedule = preflight["schedule"][0]
    run_id = "run_d085_gate"
    return {
        "attempt_status": "terminal",
        "run_id": run_id,
        "task_id": schedule["task_id"],
        "schedule_row_id": schedule["schedule_row_id"],
        "order": schedule["order"],
        "split": schedule["split"],
        "dataset_role": schedule["dataset_role"],
        "condition": schedule["condition"],
        "repetition": schedule["repetition"],
        "result": {
            "run_id": run_id,
            "official": True,
            "evaluation_status": "completed",
            # Hidden/task success is deliberately not part of readiness.
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


def test_d085_source_is_the_exact_one_row_condition_neutral_profile() -> None:
    suite = eval_runner.load_suite(SUITE_PATH)

    assert suite.experiment_id == (
        CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
    )
    assert suite.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
    assert suite.tasks == [eval_runner.PILOT_TASK]
    assert suite.conditions == [MemoryCondition.NO_MEMORY]
    assert suite.repetitions == 1
    assert suite.transport_max_retries == 0
    assert suite.budget == eval_runner.GPT54_MINI_FROZEN_COMPARISON_BUDGET
    assert suite.max_output_tokens == 25_000
    assert suite.memory_token_budget == 2_000
    assert suite.estimated_cost_usd == 7.3125
    assert suite.cost_limit_usd == 8
    assert suite.live_cost_approved is False
    assert suite.approved_execution_hash is None
    assert suite.pilot_run_id is None
    assert eval_runner._is_frozen_comparison_runtime_profile(suite)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("experiment_id", "dev-validation-condition-neutral-arbitrary"),
        ("purpose", "memory-development-no-memory"),
        ("tasks", ["tasks/dev-validation/moto-query-scanned-count/public.yaml"]),
        ("repetitions", 2),
        ("transport_max_retries", None),
        ("estimated_cost_usd", 7.3),
        ("cost_limit_usd", 9),
        ("live_cost_approved", True),
        ("approved_execution_hash", "sha256:" + ("1" * 64)),
        ("pilot_run_id", "run_forbidden"),
    ],
)
def test_d085_source_identity_drift_is_rejected(field: str, value: object) -> None:
    payload = _payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize(
    ("budget_field", "value"),
    [
        ("max_model_calls", 1),
        ("max_tool_calls", 1),
        ("max_total_tokens", 1_599_999),
        ("wall_clock_timeout_seconds", 1_799),
    ],
)
def test_d085_budget_drift_is_rejected(
    budget_field: str,
    value: int,
) -> None:
    payload = _payload()
    payload["budget"][budget_field] = value

    with pytest.raises(ValidationError):
        ExperimentSuite.model_validate(payload)


def test_d085_no_call_preflight_emits_only_invocation_approval_blockers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)

    preflight = eval_runner.preflight_suite(SUITE_PATH)
    suite = eval_runner.load_suite(SUITE_PATH)

    assert preflight["ready"] is False
    assert {blocker["code"] for blocker in preflight["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["expected_runs"] == 1
    assert preflight["schedule"][0]["task_id"] == eval_runner.PILOT_TASK_ID
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == 7.3125
    assert preflight["pricing"]["budget_upper_bound_usd"] == 7.3125
    assert preflight["pricing"]["start_time_verification"][
        "within_maximum_age"
    ] is True
    assert preflight["runtime_contract"] == (
        eval_runner._experiment_runtime_contract(
            suite,
            harness_git_commit="a" * 40,
        )
    )
    assert preflight["runtime_contract"]["schema_version"] == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_RUNTIME_CONTRACT_SCHEMA
    )
    assert preflight["runtime_contract"]["purpose"] == (
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value
    )
    assert "test-secret-never-rendered" not in str(preflight)


def test_d085_approved_no_call_preflight_keeps_the_same_execution_hash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    unapproved = eval_runner.preflight_suite(SUITE_PATH)

    approved = eval_runner.preflight_suite(
        SUITE_PATH,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is True
    assert approved["blockers"] == []
    assert approved["execution_hash"] == unapproved["execution_hash"]
    assert approved["approval"] == {
        "suite_live_cost_approved_deprecated": False,
        "suite_approved_execution_hash_deprecated": None,
        "invocation_approve_live_cost": True,
        "invocation_approved_execution_hash": unapproved["execution_hash"],
        "matches_execution_hash": True,
    }


def test_d085_selector_does_not_reinterpret_historical_pilots() -> None:
    historical = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml"
    )
    superseded = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml"
    )

    assert not eval_runner._is_frozen_comparison_runtime_profile(historical)
    assert not eval_runner._is_frozen_comparison_runtime_profile(superseded)
    assert superseded.experiment_id in (
        eval_runner.SUPERSEDED_UNEXECUTED_LIVE_EXPERIMENT_IDS
    )


def test_d085_terminal_summary_projects_exactly_one_call_guard_check() -> None:
    payload = {
        "purpose": ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value,
        "experiment_id": CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
        "memory_condition": MemoryCondition.NO_MEMORY.value,
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "budget": eval_runner.GPT54_MINI_FROZEN_COMPARISON_BUDGET.model_dump(
            mode="json"
        ),
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "checks": [
            {
                "check_id": "disabled_call_guard_contract",
                "passed": True,
                "details": {"not_exported": "private diagnostic detail"},
            }
        ],
    }

    summary = eval_runner._terminal_qualification_summary(payload)

    assert summary["gate_checks"] == {
        "disabled_call_guard_contract": {
            "schema_version": "qualification-gate-check-projection-v1",
            "check_id": "disabled_call_guard_contract",
            "check_count": 1,
            "passed": True,
        }
    }
    assert "not_exported" not in str(summary)


def test_d085_process_gate_passes_without_hidden_task_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(SUITE_PATH)
    suite = eval_runner.load_suite(SUITE_PATH)
    row = _passing_row(preflight)

    gate = eval_runner._completion_gate(
        suite,
        [row],
        expected_execution_hash=preflight["execution_hash"],
        expected_schedule=preflight["schedule"],
    )

    assert gate is not None
    assert gate["schema_version"] == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_GATE_SCHEMA
    )
    assert gate["gate_id"] == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_GATE_ID
    )
    assert gate["passed"] is True
    assert gate["expected_runs"] == 1
    assert gate["terminal_runs"] == 1
    assert gate["qualified_runs"] == 1
    assert gate["evaluator_reached_runs"] == 1
    assert gate["official_evaluator_runs"] == 1
    assert gate["infrastructure_errors"] == 0
    assert gate["qualification_errors"] == 0
    assert gate["diagnostic_errors"] == 0
    assert gate["budget_terminal_runs"] == 0
    assert gate["task_successes"] == 0
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False
    assert gate["task_identity_passed"] is True
    assert gate["row_binding_passed"] is True
    assert gate["call_guard_contract_passed"] is True
    assert gate["terminal_loop_failure_runs"] == 0
    assert gate["terminal_loop_failure_run_ids"] == []

    successful_row = copy.deepcopy(row)
    successful_row["result"]["scope_compliant_success"] = True
    successful_gate = eval_runner._completion_gate(
        suite,
        [successful_row],
        expected_execution_hash=preflight["execution_hash"],
        expected_schedule=preflight["schedule"],
    )
    assert successful_gate is not None
    assert successful_gate["passed"] is True
    assert successful_gate["task_successes"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "nonterminal",
        "unqualified",
        "evaluator_not_reached",
        "unofficial",
        "infrastructure_error",
        "qualification_error",
        "diagnostic_error",
        "budget_terminal",
        "terminal_loop_failure",
        "call_guard_projection_missing",
        "execution_hash_mismatch",
    ],
)
def test_d085_process_gate_fails_closed_on_process_confound(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(SUITE_PATH)
    suite = eval_runner.load_suite(SUITE_PATH)
    row = _passing_row(preflight)

    if mutation == "nonterminal":
        row["attempt_status"] = "not_started"
    elif mutation == "unqualified":
        row["qualification"]["qualified"] = False
    elif mutation == "evaluator_not_reached":
        row["qualification"]["evaluation_reached"] = False
    elif mutation == "unofficial":
        row["result"]["official"] = False
    elif mutation == "infrastructure_error":
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
    elif mutation == "terminal_loop_failure":
        row["result"]["terminal_error"] = {
            "type": "AgentLoopError",
            "code": "TERMINAL_LOOP_DETECTED",
            "details": {"reason_code": "terminal_loop_failure"},
        }
    elif mutation == "call_guard_projection_missing":
        row["qualification"]["gate_checks"] = {}
    else:
        row["qualification"]["execution_hash"] = "sha256:" + ("f" * 64)

    gate = eval_runner._completion_gate(
        suite,
        [row],
        expected_execution_hash=preflight["execution_hash"],
        expected_schedule=preflight["schedule"],
    )

    assert gate is not None
    assert gate["schema_version"] == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_GATE_SCHEMA
    )
    assert gate["passed"] is False
