from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from patchloop import runtime as runtime_module
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID,
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

SUITE_PATH = Path(
    "experiments/generic-high-headroom-readiness-v2v5-20260804-r1.yaml"
)
EXPECTED_TASKS = [
    "tasks/dev-train/anyio-interrupt-runner-cleanup/public.yaml",
    "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
    "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
]
READINESS_CHECK_IDS = {
    "submission_lifecycle",
    "prompt_token_integrity",
    "usage_reconciliation",
    "persisted_result",
    "disabled_call_guard_contract",
}


def _payload() -> dict[str, Any]:
    return yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))


def _ready_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
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
        lambda: datetime(2026, 8, 4, 15, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")


def _exact_manifest() -> RunManifest:
    package = load_task_package(Path(EXPECTED_TASKS[0]).parent)
    return build_manifest(
        package,
        run_id="run_d094_contract",
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        memory_condition=MemoryCondition.NO_MEMORY,
        sandbox_backend="docker",
        budget=eval_runner.GPT54_MINI_GENERIC_HIGH_HEADROOM_READINESS_BUDGET,
        transport_max_retries=0,
        max_output_tokens=25_000,
        input_price_per_million_usd=0.75,
        cached_input_price_per_million_usd=0.075,
        output_price_per_million_usd=4.5,
        experiment_context=ExperimentRunContext(
            experiment_id=GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID,
            purpose=ExperimentPurpose.GENERIC_BASELINE_READINESS,
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


def _projection(check_id: str) -> dict[str, Any]:
    return {
        "schema_version": "qualification-gate-check-projection-v1",
        "check_id": check_id,
        "check_count": 1,
        "passed": True,
    }


def _passing_rows(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for schedule in preflight["schedule"]:
        run_id = f"run_d094_gate_{schedule['order']}"
        qualification_hash = "sha256:" + (str(schedule["order"]) * 64)
        rows.append(
            {
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
                    "agent_submission_status": "completed",
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
                    "qualification_hash": qualification_hash,
                    "gate_checks": {
                        "disabled_call_guard_contract": _projection(
                            "disabled_call_guard_contract"
                        )
                    },
                    "readiness_checks": {
                        check_id: _projection(check_id)
                        for check_id in READINESS_CHECK_IDS
                    },
                    "read_only_recomputation": {
                        "schema_version": (
                            "qualification-read-only-recomputation-v1"
                        ),
                        "matched": True,
                        "qualification_hash": qualification_hash,
                        "recomputed_qualification_hash": qualification_hash,
                    },
                    "model_or_tool_call_budget_blocks": {
                        "schema_version": "call-budget-block-projection-v1",
                        "source_check_count": 1,
                        "source_check_passed": True,
                        "event_sequences": [],
                    },
                },
                "infrastructure_error": None,
                "qualification_error": None,
                "diagnostic_error": None,
            }
        )
    return rows


def test_d094_source_and_runtime_contract_are_exact() -> None:
    suite = eval_runner.load_suite(SUITE_PATH)
    pricing = eval_runner._pricing_contract(suite, schedule_size=3)
    runtime = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit="a" * 40,
    )

    assert suite.experiment_id == GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID
    assert suite.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS
    assert suite.tasks == EXPECTED_TASKS
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
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
    }
    assert suite.estimated_cost_usd == 40.8375
    assert suite.cost_limit_usd == 41
    assert suite.live_cost_approved is False
    assert suite.approved_execution_hash is None
    assert pricing["per_run_cost_reserve_usd"] == 13.6125
    assert pricing["budget_upper_bound_usd"] == 40.8375
    assert runtime is not None
    assert runtime["schema_version"] == (
        "generic-high-headroom-readiness-runtime-contract-v1"
    )
    assert runtime["call_guard_policy"] == "model-tool-observability-only-v1"


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment_id",), "generic-high-headroom-wrong"),
        (("tasks",), list(reversed(EXPECTED_TASKS))),
        (("conditions",), ["raw_trace"]),
        (("repetitions",), 2),
        (("transport_max_retries",), None),
        (("max_output_tokens",), 24_999),
        (("memory_token_budget",), 1_999),
        (("budget", "max_model_calls"), 100),
        (("budget", "max_tool_calls"), 100),
        (("budget", "max_total_tokens"), 2_999_999),
        (("budget", "wall_clock_timeout_seconds"), 3_599),
        (("estimated_cost_usd",), 40.8),
        (("cost_limit_usd",), 42),
        (("live_cost_approved",), True),
        (("approved_execution_hash",), "sha256:" + ("1" * 64)),
    ],
)
def test_d094_source_drift_fails_closed(
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


def test_d094_manifest_and_runtime_evidence_bind_exact_profile() -> None:
    manifest = _exact_manifest()
    system_prompt, tools = AgentRunner._runtime_contract(manifest)
    evidence = AgentRunner._generic_baseline_runtime_evidence_document(
        manifest=manifest,
        system_prompt=system_prompt,
        tool_schemas=tools,
    )

    assert manifest.task_id == "anyio-interrupt-runner-cleanup"
    assert manifest.tool_schema_version == "v2"
    assert manifest.context_policy_version == "phase-evidence-v5"
    assert manifest.budget == (
        eval_runner.GPT54_MINI_GENERIC_HIGH_HEADROOM_READINESS_BUDGET
    )
    assert evidence is not None
    assert evidence["schema_version"] == (
        "generic-high-headroom-readiness-runtime-evidence-v1"
    )
    assert evidence["call_guard_policy"] == "model-tool-observability-only-v1"
    assert evidence["purpose"] == "generic-baseline-readiness"
    assert evidence["model_provider"] == "openai"
    assert evidence["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert evidence["reasoning_effort"] == "medium"
    assert evidence["reasoning_mode"] == "standard"
    assert evidence["service_tier"] == "default"
    assert evidence["max_output_tokens"] == 25_000
    assert evidence["budget"] == manifest.budget.model_dump(mode="json")
    assert evidence["memory_max_context_tokens"] == 2_000
    assert evidence["memory_condition"] == "no_memory"
    assert qualification_module._generic_baseline_readiness_budget_matches(
        GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID,
        manifest.budget,
    )
    assert calculate_budget_pressure(manifest, [])["configured_limits"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 3_000_000,
        "wall_clock_ms": 3_600_000,
    }


def test_d094_budget_diagnostic_rejects_near_match() -> None:
    payload = _exact_manifest().model_dump(mode="json")
    payload["experiment"]["experiment_id"] = (
        "generic-high-headroom-readiness-v2v5-20260804-near-match"
    )

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)
    with pytest.raises(ValueError, match="D-081 generic readiness"):
        calculate_budget_pressure(payload, [])


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment", "experiment_id"), "generic-high-headroom-wrong"),
        (("task_id",), "different-task"),
        (("model", "model_id"), "different-model"),
        (("model", "transport_max_retries"), None),
        (("budget", "max_model_calls"), 1),
        (("budget", "max_tool_calls"), 1),
        (("budget", "max_total_tokens"), 2_999_999),
        (("budget", "wall_clock_timeout_seconds"), 3_599),
        (("memory", "condition"), "raw_trace"),
        (("memory", "max_context_tokens"), 1_999),
        (("experiment", "dataset_role"), "development-validation"),
        (("experiment", "schedule_seed"), 20260724),
        (("experiment", "schedule_order"), 2),
        (("experiment", "repetition"), 2),
        (("fault", "type"), "context-reset"),
    ],
)
def test_d094_manifest_drift_fails_closed(
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


def test_d094_no_call_preflight_binds_three_run_full_reserve(
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
    assert preflight["expected_runs"] == 3
    assert {row["task_id"] for row in preflight["schedule"]} == {
        Path(task).parent.name for task in EXPECTED_TASKS
    }
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == 13.6125
    assert preflight["pricing"]["budget_upper_bound_usd"] == 40.8375
    assert preflight["runtime_contract"]["schema_version"] == (
        "generic-high-headroom-readiness-runtime-contract-v1"
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


def test_d094_manifest_and_qualification_match_approved_preflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(runtime_module, "git_commit", lambda: "a" * 40)
    unapproved = eval_runner.preflight_suite(SUITE_PATH)
    preflight = eval_runner.preflight_suite(
        SUITE_PATH,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )
    suite = eval_runner.load_suite(SUITE_PATH)
    item = preflight["schedule"][0]
    task_row = next(
        row
        for row in preflight["tasks"]
        if row["task_id"] == item["task_id"]
    )
    package = load_task_package(Path(item["task"]).parent)
    evaluator_digest = item["evaluator_image_digest"]
    manifest = build_manifest(
        package,
        run_id="run_d094_preflight_binding",
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(item["condition"]),
        sandbox_backend="docker",
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
        experiment_context=ExperimentRunContext(
            experiment_id=suite.experiment_id,
            purpose=suite.purpose,
            suite_hash=preflight["suite_hash"],
            execution_hash=preflight["execution_hash"],
            dataset_manifest_hash=preflight["dataset"]["manifest_hash"],
            dataset_role=DatasetRole(item["dataset_role"]),
            schedule_seed=suite.seed,
            schedule_order=item["order"],
            schedule_row_id=item["schedule_row_id"],
            repetition=item["repetition"],
        ),
    )

    eval_runner._assert_manifest_matches_preflight(
        manifest,
        suite=suite,
        preflight=preflight,
        item={**task_row, **item},
    )
    persisted_plan = {
        **preflight,
        "schema_version": "experiment-execution-plan-v1",
    }
    assert qualification_module._execution_plan_matches(
        plan=persisted_plan,
        manifest=manifest,
    )


def test_d094_completion_gate_requires_exact_public_runtime_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(SUITE_PATH)
    suite = eval_runner.load_suite(SUITE_PATH)
    rows = _passing_rows(preflight)

    gate = eval_runner._completion_gate(
        suite,
        rows,
        expected_execution_hash=preflight["execution_hash"],
        expected_schedule=preflight["schedule"],
    )

    assert gate is not None
    assert gate["schema_version"] == "generic-high-headroom-readiness-gate-v1"
    assert gate["gate_id"] == "d094-generic-high-headroom-readiness"
    assert gate["passed"] is True
    assert gate["terminal_runs"] == 3
    assert gate["qualified_runs"] == 3
    assert gate["evaluator_reached_runs"] == 3
    assert gate["official_evaluator_runs"] == 3
    assert gate["accepted_submission_runs"] == 3
    assert gate["prompt_telemetry_complete_runs"] == 3
    assert gate["usage_reconciled_runs"] == 3
    assert gate["persisted_result_verified_runs"] == 3
    assert gate["qualification_recomputed_runs"] == 3
    assert gate["model_or_tool_call_budget_block_runs"] == 0
    assert gate["model_or_tool_call_budget_block_run_ids"] == []
    assert gate["model_or_tool_call_budget_block_sequences"] == []
    assert gate["budget_terminal_runs"] == 0
    assert gate["terminal_loop_failure_runs"] == 0
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False


@pytest.mark.parametrize(
    "tamper",
    [
        "submission_status",
        "submission_projection",
        "prompt_telemetry",
        "usage_reconciliation",
        "persisted_result",
        "qualification_recompute",
        "qualification_hash_format",
        "call_budget_block",
        "budget_terminal",
        "terminal_loop",
    ],
)
def test_d094_completion_gate_rejects_missing_or_forged_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tamper: str,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite(SUITE_PATH)
    suite = eval_runner.load_suite(SUITE_PATH)
    rows = copy.deepcopy(_passing_rows(preflight))
    row = rows[0]

    if tamper == "submission_status":
        row["result"]["agent_submission_status"] = "failed"
    elif tamper == "submission_projection":
        row["qualification"]["readiness_checks"]["submission_lifecycle"][
            "passed"
        ] = False
    elif tamper == "prompt_telemetry":
        row["qualification"]["readiness_checks"]["prompt_token_integrity"][
            "passed"
        ] = False
    elif tamper == "usage_reconciliation":
        row["qualification"]["readiness_checks"]["usage_reconciliation"][
            "passed"
        ] = False
    elif tamper == "persisted_result":
        row["qualification"]["readiness_checks"]["persisted_result"][
            "passed"
        ] = False
    elif tamper == "qualification_recompute":
        row["qualification"]["read_only_recomputation"]["matched"] = False
    elif tamper == "qualification_hash_format":
        row["qualification"]["qualification_hash"] = "not-a-sha"
        row["qualification"]["read_only_recomputation"][
            "qualification_hash"
        ] = "not-a-sha"
        row["qualification"]["read_only_recomputation"][
            "recomputed_qualification_hash"
        ] = "not-a-sha"
    elif tamper == "call_budget_block":
        row["qualification"]["model_or_tool_call_budget_blocks"][
            "event_sequences"
        ] = [17]
    elif tamper == "budget_terminal":
        row["result"]["terminal_error"] = {
            "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
            "details": {"reason_code": "exact_request_budget_exceeded"},
        }
    elif tamper == "terminal_loop":
        row["result"]["terminal_error"] = {
            "type": "TerminalLoopError",
            "code": "TERMINAL_LOOP",
            "details": {"reason_code": "terminal_loop_detected"},
        }

    gate = eval_runner._completion_gate(
        suite,
        rows,
        expected_execution_hash=preflight["execution_hash"],
        expected_schedule=preflight["schedule"],
    )

    assert gate is not None
    assert gate["passed"] is False
    if tamper == "call_budget_block":
        assert gate["model_or_tool_call_budget_block_runs"] == 1
        assert gate["model_or_tool_call_budget_block_run_ids"] == [
            rows[0]["run_id"]
        ]


def test_d094_terminal_qualification_reloads_persisted_before_recompute(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    generated = {
        "experiment_id": GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID,
        "qualification_hash": "sha256:" + ("1" * 64),
        "checks": [],
    }
    persisted = {
        **generated,
        "qualification_hash": "sha256:" + ("2" * 64),
    }
    calls: list[bool] = []

    def fake_qualify_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        persist = kwargs.get("persist", True)
        calls.append(persist)
        return generated if persist else copy.deepcopy(persisted)

    loaded: list[tuple[str, Path]] = []

    def fake_load_trace_qualification(
        run_id: str,
        *,
        root: Path,
    ) -> dict[str, Any]:
        loaded.append((run_id, root))
        return copy.deepcopy(persisted)

    monkeypatch.setattr(
        qualification_module,
        "qualify_run",
        fake_qualify_run,
    )
    monkeypatch.setattr(
        qualification_module,
        "load_trace_qualification",
        fake_load_trace_qualification,
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path)

    summary = eval_runner._qualify_terminal_run(
        "run_d094_persisted_reload",
        EXPECTED_TASKS[0],
    )

    assert calls == [True, False]
    assert loaded == [("run_d094_persisted_reload", tmp_path)]
    assert summary["qualification_hash"] == persisted["qualification_hash"]
    assert summary["read_only_recomputation"] == {
        "schema_version": "qualification-read-only-recomputation-v1",
        "matched": True,
        "qualification_hash": persisted["qualification_hash"],
        "recomputed_qualification_hash": persisted["qualification_hash"],
    }
