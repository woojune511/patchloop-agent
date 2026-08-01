from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from patchloop.agent.runner import AgentRunner
from patchloop.artifacts import ArtifactStore
from patchloop.cli import app
from patchloop.contracts import (
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    FaultSpec,
    MemoryCondition,
    PublicReviewContract,
)
from patchloop.dataset import load_dataset_manifest
from patchloop.errors import ContractError
from patchloop.evals import qualification as trace_qualification
from patchloop.evals import runner as eval_runner
from patchloop.evals.runner import ExperimentSuite
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

PRIMARY_PILOT_SUITE = (
    "experiments/dev-validation-gpt54mini-campaign-pilot-r2.yaml"
)
FUTURE_PILOT_SUITE = (
    "experiments/dev-validation-gpt54mini-token-tail-v5-pilot-r1.yaml"
)
COMPLETION_PILOT_SUITE = (
    "experiments/dev-validation-gpt54mini-completion-v6-pilot-r1.yaml"
)
BUDGET_PILOT_SUITE = (
    "experiments/dev-no-memory-budget-pilot-20260731-r1.yaml"
)
CORRECTIVE_PILOT_SUITE = (
    "experiments/dev-no-memory-corrective-pilot-20260731-r1.yaml"
)
SATURATION_PILOT_SUITE = (
    "experiments/dev-no-memory-saturation-v8-pilot-20260801-r1.yaml"
)
REVIEW_EVIDENCE_PILOT_SUITE = (
    "experiments/dev-no-memory-review-evidence-v9-pilot-20260801-r1.yaml"
)
COVERAGE_REVIEW_PILOT_SUITE = (
    "experiments/dev-no-memory-coverage-review-v10-pilot-20260802-r1.yaml"
)
HISTORICAL_PRIMARY_PILOT_SUITE = (
    "experiments/dev-validation-gpt54mini-campaign-pilot-r1.yaml"
)


def _core_suite_payload(dataset_manifest_hash: str) -> dict:
    return {
        "schema_version": "experiment-v1",
        "experiment_id": "core-role-test",
        "core": True,
        "tasks": [f"task-{index}" for index in range(12)],
        "conditions": [
            "no_memory",
            "raw_trace",
            "structured",
            "selective_structured",
        ],
        "repetitions": 2,
        "model": "mock",
        "embedding_revision": "test-revision",
        "dataset_manifest_hash": dataset_manifest_hash,
    }


def _ready_live_environment(monkeypatch, tmp_path: Path) -> None:
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
        lambda: datetime(2026, 7, 30, 23, tzinfo=UTC),
    )
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")


def _write_future_primary_suite(
    tmp_path: Path,
    experiment_id: str,
) -> Path:
    payload = yaml.safe_load(
        Path(COMPLETION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    payload["experiment_id"] = experiment_id
    suite_path = tmp_path / f"{experiment_id}.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    return suite_path


def _retry_qualification(
    *,
    retry_episode_count: int,
    verified_retry_count: int,
    failed_source_failure_sequences: list[int],
    check_count: int = 1,
    check_passed: bool = True,
) -> dict:
    return {
        "run_id": "run_diagnostic",
        "qualified": True,
        "trace_integrity_passed": True,
        "evaluation_reached": True,
        "qualification_hash": "sha256:" + ("d" * 64),
        "trace_features": {
            "rejected_patch_retry_context": {
                "check_count": check_count,
                "check_passed": check_passed,
                "rejected_candidate_count": retry_episode_count,
                "retry_episode_count": retry_episode_count,
                "verified_retry_count": verified_retry_count,
                "failed_source_failure_sequences": (
                    failed_source_failure_sequences
                ),
            }
        },
    }


def test_expected_runtime_contract_hash_uses_phase_evidence_v5() -> None:
    encoded = json.dumps(
        {
            "system_prompt": eval_runner.SYSTEM_PROMPT_V3,
            "tools": eval_runner.TOOL_SCHEMAS_V2,
            "tool_schema_version": "v2",
            "context_policy_version": "phase-evidence-v5",
        },
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")

    assert eval_runner._expected_runtime_contract_hash() == sha256_bytes(encoded)


def test_live_campaign_approval_is_an_invocation_preflight_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = _write_future_primary_suite(
        tmp_path,
        "future-primary-approval-gate",
    )
    suite = eval_runner.load_suite(suite_path)
    assert suite.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT

    unapproved = eval_runner.preflight_suite(suite_path)
    blocker_codes = {row["code"] for row in unapproved["blockers"]}
    assert blocker_codes == {"LIVE_COST_NOT_APPROVED", "APPROVAL_HASH_MISMATCH"}
    assert "test-secret-never-rendered" not in json.dumps(unapproved)

    approved = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )
    assert approved["ready"] is True
    assert approved["execution_hash"] == unapproved["execution_hash"]
    assert approved["suite"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert approved["suite"]["max_output_tokens"] == 25_000
    assert approved["expected_runs"] == 2
    assert {
        row["task_id"] for row in approved["tasks"]
    } == {
        "babel-strict-grouped-decimal-trailing-zeroes",
        "moto-query-scanned-count",
    }
    assert approved["suite"]["budget"]["max_model_calls"] == 40
    assert approved["suite"]["budget"]["max_tool_calls"] == 100
    assert approved["suite"]["budget"]["max_total_tokens"] == 600_000
    assert approved["suite"]["budget"]["wall_clock_timeout_seconds"] == 1_800
    assert approved["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        2.8125
    )
    assert approved["pricing"]["budget_upper_bound_usd"] == pytest.approx(
        5.625
    )


def test_historical_terra_pilot_suite_is_loadable_but_never_runnable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-validation-pilot.template.yaml"

    suite = eval_runner.load_suite(suite_path)
    preflight = eval_runner.preflight_suite(suite_path)

    assert suite.experiment_id == "dev-validation-live-pilot-20260728-r3"
    assert suite.model_id == "gpt-5.6-terra"
    assert suite.max_output_tokens == 4096
    assert suite.budget.max_total_tokens == 80_000
    assert "HISTORICAL_SUITE_IMMUTABLE" in {
        row["code"] for row in preflight["blockers"]
    }


@pytest.mark.parametrize(
    "experiment_id",
    [
        "dev-validation-live-pilot-20260728",
        "dev-validation-live-pilot-20260728-r2",
        "dev-validation-live-pilot-20260728-r3",
    ],
)
def test_all_consumed_terra_pilot_ids_are_immutable(
    experiment_id: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path(
            "experiments/dev-validation-pilot.template.yaml"
        ).read_text(encoding="utf-8")
    )
    payload["experiment_id"] = experiment_id
    suite_path = tmp_path / f"{experiment_id}.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    unapproved = eval_runner.preflight_suite(suite_path)
    approved = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is False
    assert "HISTORICAL_SUITE_IMMUTABLE" in {
        row["code"] for row in approved["blockers"]
    }


def test_historical_primary_r1_is_loadable_but_never_runnable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    suite = eval_runner.load_suite(HISTORICAL_PRIMARY_PILOT_SUITE)
    preflight = eval_runner.preflight_suite(HISTORICAL_PRIMARY_PILOT_SUITE)

    assert suite.experiment_id == (
        "dev-validation-gpt54mini-campaign-20260730-r1"
    )
    assert suite.budget.max_model_calls == 20
    assert "HISTORICAL_SUITE_IMMUTABLE" in {
        row["code"] for row in preflight["blockers"]
    }


def test_consumed_primary_r2_keeps_current_budget_and_is_never_runnable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    suite = eval_runner.load_suite(PRIMARY_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(PRIMARY_PILOT_SUITE)
    approved = eval_runner.preflight_suite(
        PRIMARY_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert suite.experiment_id == (
        "dev-validation-gpt54mini-campaign-20260730-r2"
    )
    assert suite.budget.max_model_calls == 21
    assert suite.budget.max_total_tokens == 200_000
    assert approved["ready"] is False
    assert "HISTORICAL_SUITE_IMMUTABLE" in {
        row["code"] for row in approved["blockers"]
    }


def test_unexecuted_250k_v5_pilot_is_superseded_and_never_runnable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    suite = eval_runner.load_suite(FUTURE_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(FUTURE_PILOT_SUITE)
    approved = eval_runner.preflight_suite(
        FUTURE_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert suite.budget.max_total_tokens == 250_000
    assert approved["ready"] is False
    assert "SUPERSEDED_SUITE" in {
        row["code"] for row in approved["blockers"]
    }


def test_consumed_completion_panel_is_loadable_but_never_runnable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    suite = eval_runner.load_suite(COMPLETION_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(COMPLETION_PILOT_SUITE)
    approved = eval_runner.preflight_suite(
        COMPLETION_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert suite.tasks == [
        (
            "tasks/dev-validation/"
            "babel-strict-grouped-decimal-trailing-zeroes/public.yaml"
        ),
        "tasks/dev-validation/moto-query-scanned-count/public.yaml",
    ]
    assert suite.budget == eval_runner.GPT54_MINI_COMPLETION_BUDGET
    assert approved["ready"] is False
    assert {
        row["code"] for row in approved["blockers"]
    } == {"HISTORICAL_SUITE_IMMUTABLE"}


def test_consumed_no_memory_campaign_is_never_runnable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-no-memory.template.yaml"

    unapproved = eval_runner.preflight_suite(suite_path)
    approved = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is False
    assert "HISTORICAL_SUITE_IMMUTABLE" in {
        row["code"] for row in approved["blockers"]
    }


@pytest.mark.parametrize(
    "suite_path",
    [
        "experiments/dev-validation-gpt54mini-investigation-v4-pilot-r1.yaml",
        "experiments/dev-no-memory-v4.template.yaml",
    ],
)
def test_consumed_v4_200k_suites_are_loadable_but_never_runnable(
    suite_path: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    suite = eval_runner.load_suite(suite_path)
    preflight = eval_runner.preflight_suite(suite_path)

    assert suite.budget.max_model_calls == 21
    assert suite.budget.max_total_tokens == 200_000
    assert preflight["ready"] is False
    assert "HISTORICAL_SUITE_IMMUTABLE" in {
        row["code"] for row in preflight["blockers"]
    }


@pytest.mark.parametrize(
    "suite_path",
    [
        "experiments/dev-validation-gpt54mini-pilot.yaml",
        "experiments/dev-validation-gpt54mini-pilot-r2.yaml",
        "experiments/dev-validation-gpt54mini-d037-r3.yaml",
        "experiments/dev-validation-gpt54mini-d037-r4.yaml",
        "experiments/dev-validation-gpt54mini-d037-r5.yaml",
        "experiments/dev-validation-gpt54mini-d037-r6.yaml",
    ],
)
def test_consumed_mini_diagnostic_suites_are_immutable_even_with_approval(
    suite_path: str,
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    unapproved = eval_runner.preflight_suite(suite_path)
    approved = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is False
    assert "HISTORICAL_SUITE_IMMUTABLE" in {
        row["code"] for row in approved["blockers"]
    }


def test_completion_panel_contract_rejects_legacy_20_call_limit() -> None:
    payload = yaml.safe_load(
        Path(COMPLETION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    payload["budget"]["max_model_calls"] = 20

    with pytest.raises(ValidationError, match="max_model_calls=40"):
        ExperimentSuite.model_validate(payload)


def test_completion_panel_contract_rejects_250k_budget() -> None:
    payload = yaml.safe_load(
        Path(COMPLETION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    payload["budget"]["max_total_tokens"] = 250_000

    with pytest.raises(ValidationError, match="max_total_tokens=600000"):
        ExperimentSuite.model_validate(payload)


def test_completion_panel_contract_rejects_one_task_subset() -> None:
    payload = yaml.safe_load(
        Path(COMPLETION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    payload["tasks"] = payload["tasks"][:1]

    with pytest.raises(ValidationError, match="exact frozen task set"):
        ExperimentSuite.model_validate(payload)


def test_model_candidate_history_id_cannot_bypass_completion_defaults() -> None:
    payload = yaml.safe_load(
        Path(COMPLETION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    payload["experiment_id"] = "dev-validation-gpt54mini-d037-20260730-r5"
    payload["tasks"] = payload["tasks"][:1]
    payload["budget"]["max_total_tokens"] = 200_000
    payload["cost_limit_usd"] = 2

    with pytest.raises(ValidationError, match="exact frozen task set"):
        ExperimentSuite.model_validate(payload)


def test_completion_gate_rejects_budget_terminal_even_when_trace_qualified() -> None:
    suite = eval_runner.load_suite(COMPLETION_PILOT_SUITE)
    rows = []
    for index in range(2):
        rows.append(
            {
                "attempt_status": "terminal",
                "run_id": f"run_completion_{index}",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "model_calls": 2,
                    "tool_calls": 1,
                    "wall_clock_ms": 1_000,
                },
                "result": {
                    "official": True,
                    "evaluation_status": "completed",
                    "scope_compliant_success": index == 0,
                    "terminal_error": (
                        {
                            "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                            "details": {
                                "reason_code": "exact_request_budget_exceeded"
                            },
                        }
                        if index == 1
                        else None
                    ),
                },
                "qualification": {
                    "qualified": True,
                    "evaluation_reached": True,
                },
                "infrastructure_error": None,
                "qualification_error": None,
            }
        )

    gate = eval_runner._completion_gate(suite, rows)

    assert gate is not None
    assert gate["passed"] is False
    assert gate["budget_terminal_runs"] == 1
    assert gate["budget_terminal_run_ids"] == ["run_completion_1"]
    assert gate["task_successes"] == 1


@pytest.mark.parametrize(
    "usage_overrides",
    [
        {"input_tokens": 480_001, "output_tokens": 0},
        {"model_calls": 33},
        {"tool_calls": 81},
        {"wall_clock_ms": 1_440_001},
    ],
    ids=[
        "total-tokens-480001",
        "model-calls-33",
        "tool-calls-81",
        "wall-clock-ms-1440001",
    ],
)
def test_completion_gate_can_pass_while_panel_headroom_fails(
    usage_overrides: dict[str, int],
) -> None:
    suite = eval_runner.load_suite(COMPLETION_PILOT_SUITE)
    rows = []
    for index in range(2):
        usage = {
            "input_tokens": 100,
            "output_tokens": 20,
            "model_calls": 2,
            "tool_calls": 1,
            "wall_clock_ms": 1_000,
        }
        if index == 1:
            usage.update(usage_overrides)
        rows.append(
            {
                "attempt_status": "terminal",
                "run_id": f"run_completion_{index}",
                "usage": usage,
                "result": {
                    "official": True,
                    "evaluation_status": "completed",
                    "scope_compliant_success": False,
                    "terminal_error": None,
                },
                "qualification": {
                    "qualified": True,
                    "evaluation_reached": True,
                },
                "infrastructure_error": None,
                "qualification_error": None,
                "diagnostic_error": None,
            }
        )

    gate = eval_runner._completion_gate(suite, rows)

    assert gate is not None
    assert gate["passed"] is True
    assert gate["panel_headroom"]["passed"] is False
    assert gate["panel_headroom"]["failed_run_ids"] == [
        "run_completion_1"
    ]


def test_memory_development_budget_pilot_has_exact_preflight_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 1, 12, tzinfo=UTC),
    )

    suite = eval_runner.load_suite(BUDGET_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(BUDGET_PILOT_SUITE)

    assert suite.purpose == (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_BUDGET_PILOT
    )
    assert set(suite.tasks) == {
        "tasks/dev-train/hf-hub-xet-endpoint-propagation/public.yaml",
        "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml",
        "tasks/dev-train/pyfakefs-makedirs-parent-traversal/public.yaml",
    }
    assert suite.conditions == [eval_runner.MemoryCondition.NO_MEMORY]
    assert suite.repetitions == 1
    assert suite.budget == (
        eval_runner.GPT54_MINI_MEMORY_DEVELOPMENT_BUDGET_PILOT
    )
    assert {row["code"] for row in unapproved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert unapproved["expected_runs"] == 3
    assert {row["dataset_role"] for row in unapproved["tasks"]} == {
        DatasetRole.MEMORY_DEVELOPMENT.value
    }
    assert {row["condition"] for row in unapproved["schedule"]} == {
        "no_memory"
    }
    assert {row["repetition"] for row in unapproved["schedule"]} == {1}
    assert unapproved["pilot_qualification"] == {
        "run_id": None,
        "qualified": None,
    }
    assert unapproved["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        2.2725
    )
    assert unapproved["pricing"]["budget_upper_bound_usd"] == pytest.approx(
        6.8175
    )
    assert "test-secret-never-rendered" not in json.dumps(unapproved)

    approved = eval_runner.preflight_suite(
        BUDGET_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is False
    assert approved["execution_hash"] == unapproved["execution_hash"]
    assert approved["suite"]["cost_limit_usd"] == 7
    assert approved["suite"]["budget"] == {
        "max_model_calls": 40,
        "max_tool_calls": 100,
        "max_total_tokens": 480_000,
        "wall_clock_timeout_seconds": 1_800,
    }
    assert {row["code"] for row in approved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE"
    }


def test_corrective_pilot_binds_review_contracts_and_larger_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 1, 12, tzinfo=UTC),
    )

    suite = eval_runner.load_suite(CORRECTIVE_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(CORRECTIVE_PILOT_SUITE)

    assert suite.purpose == (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
    )
    assert suite.budget == (
        eval_runner.GPT54_MINI_MEMORY_DEVELOPMENT_CORRECTIVE_PILOT
    )
    assert suite.budget.max_total_tokens == 900_000
    assert unapproved["expected_runs"] == 3
    assert {row["code"] for row in unapproved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert all(
        row["public_review_contract"]["content_hash"].startswith(
            "sha256:"
        )
        and row["public_review_contract_path"].startswith(
            "experiments/review-contracts/"
        )
        for row in unapproved["tasks"]
    )
    assert unapproved["pricing"][
        "per_run_cost_reserve_usd"
    ] == pytest.approx(4.1625)
    assert unapproved["pricing"][
        "budget_upper_bound_usd"
    ] == pytest.approx(12.4875)

    approved = eval_runner.preflight_suite(
        CORRECTIVE_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is False
    assert approved["suite"]["cost_limit_usd"] == 13
    assert approved["execution_hash"] == unapproved["execution_hash"]
    assert {row["code"] for row in approved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE"
    }


def test_saturation_pilot_has_exact_no_call_preflight_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 1, 12, tzinfo=UTC),
    )

    suite = eval_runner.load_suite(SATURATION_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(SATURATION_PILOT_SUITE)

    assert suite.purpose == (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
    )
    assert suite.tasks == [eval_runner.SATURATION_PILOT_TASK]
    assert suite.conditions == [eval_runner.MemoryCondition.NO_MEMORY]
    assert suite.repetitions == 1
    assert suite.budget == (
        eval_runner.GPT54_MINI_MEMORY_DEVELOPMENT_SATURATION_PILOT
    )
    assert suite.diagnostic is not None
    assert suite.diagnostic.profile == "v8-saturation-context-v1"
    assert {row["code"] for row in unapproved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert unapproved["expected_runs"] == 1
    assert [row["task_id"] for row in unapproved["tasks"]] == [
        eval_runner.SATURATION_PILOT_TASK_ID
    ]
    assert unapproved["tasks"][0]["public_review_contract"][
        "content_hash"
    ].startswith("sha256:")
    assert unapproved["runtime_contract"] == {
        "schema_version": "corrective-runtime-contract-v2",
        "tool_schema_version": "v4",
        "context_policy_version": "phase-evidence-v8",
        "system_prompt_hash": sha256_text(eval_runner.SYSTEM_PROMPT_V5),
        "tool_schema_hash": sha256_text(
            canonical_json(eval_runner.TOOL_SCHEMAS_V4)
        ),
        "harness_git_commit": "a" * 40,
    }
    assert unapproved["pricing"][
        "per_run_cost_reserve_usd"
    ] == pytest.approx(4.1625)
    assert unapproved["pricing"][
        "budget_upper_bound_usd"
    ] == pytest.approx(4.1625)

    approved = eval_runner.preflight_suite(
        SATURATION_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is False
    assert approved["execution_hash"] == unapproved["execution_hash"]
    assert approved["suite"]["cost_limit_usd"] == 5
    assert {row["code"] for row in approved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE"
    }


def test_review_evidence_pilot_has_exact_no_call_preflight_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 1, 12, tzinfo=UTC),
    )

    suite = eval_runner.load_suite(REVIEW_EVIDENCE_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(REVIEW_EVIDENCE_PILOT_SUITE)

    assert suite.purpose == (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
    )
    assert suite.tasks == [eval_runner.REVIEW_EVIDENCE_PILOT_TASK]
    assert suite.conditions == [eval_runner.MemoryCondition.NO_MEMORY]
    assert suite.repetitions == 1
    assert suite.budget == (
        eval_runner.GPT54_MINI_MEMORY_DEVELOPMENT_REVIEW_EVIDENCE_PILOT
    )
    assert suite.max_output_tokens == 25_000
    assert suite.diagnostic is None
    assert {row["code"] for row in unapproved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert unapproved["expected_runs"] == 1
    assert [row["task_id"] for row in unapproved["tasks"]] == [
        eval_runner.REVIEW_EVIDENCE_PILOT_TASK_ID
    ]
    assert unapproved["tasks"][0]["public_review_contract"][
        "content_hash"
    ].startswith("sha256:")
    assert unapproved["runtime_contract"] == {
        "schema_version": "corrective-runtime-contract-v3",
        "tool_schema_version": "v4",
        "context_policy_version": "phase-evidence-v9",
        "system_prompt_hash": sha256_text(eval_runner.SYSTEM_PROMPT_V6),
        "tool_schema_hash": sha256_text(
            canonical_json(eval_runner.TOOL_SCHEMAS_V4)
        ),
        "harness_git_commit": "a" * 40,
    }
    assert unapproved["pricing"][
        "per_run_cost_reserve_usd"
    ] == pytest.approx(5.5125)
    assert unapproved["pricing"][
        "budget_upper_bound_usd"
    ] == pytest.approx(5.5125)

    approved = eval_runner.preflight_suite(
        REVIEW_EVIDENCE_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is False
    assert approved["execution_hash"] == unapproved["execution_hash"]
    assert approved["suite"]["cost_limit_usd"] == 6
    assert {row["code"] for row in approved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE"
    }


def test_coverage_review_pilot_has_exact_no_call_preflight_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS",
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
        - eval_runner.CONSUMED_COVERAGE_REVIEW_PILOT_EXPERIMENT_IDS,
    )
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 2, 0, tzinfo=UTC),
    )

    suite = eval_runner.load_suite(COVERAGE_REVIEW_PILOT_SUITE)
    unapproved = eval_runner.preflight_suite(COVERAGE_REVIEW_PILOT_SUITE)

    assert suite.purpose == (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
    )
    assert suite.tasks == [eval_runner.COVERAGE_REVIEW_PILOT_TASK]
    assert suite.conditions == [eval_runner.MemoryCondition.NO_MEMORY]
    assert suite.repetitions == 1
    assert suite.budget == (
        eval_runner.GPT54_MINI_MEMORY_DEVELOPMENT_COVERAGE_REVIEW_PILOT
    )
    assert suite.max_output_tokens == 25_000
    assert suite.diagnostic is None
    assert {row["code"] for row in unapproved["blockers"]} == {
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert unapproved["expected_runs"] == 1
    assert [row["task_id"] for row in unapproved["tasks"]] == [
        eval_runner.COVERAGE_REVIEW_PILOT_TASK_ID
    ]
    task = unapproved["tasks"][0]
    assert task["public_review_contract_path"] == (
        "experiments/review-contracts-v2/"
        "hf-hub-xet-endpoint-propagation.yaml"
    )
    assert task["public_review_contract"]["schema_version"] == (
        "public-review-contract-v2"
    )
    assert task["public_review_contract"]["content_hash"] == (
        "sha256:51c6c4ace6bb46a5919cc7cfe13088e456088a0f5ed9d87b67eb75b5a7221cce"
    )
    assert unapproved["runtime_contract"] == {
        "schema_version": "corrective-runtime-contract-v4",
        "tool_schema_version": "v5",
        "context_policy_version": "phase-evidence-v10",
        "system_prompt_hash": sha256_text(eval_runner.SYSTEM_PROMPT_V7),
        "tool_schema_hash": sha256_text(
            canonical_json(eval_runner.TOOL_SCHEMAS_V5)
        ),
        "harness_git_commit": "a" * 40,
    }
    assert unapproved["pricing"][
        "per_run_cost_reserve_usd"
    ] == pytest.approx(5.5125)
    assert unapproved["pricing"][
        "budget_upper_bound_usd"
    ] == pytest.approx(5.5125)

    approved = eval_runner.preflight_suite(
        COVERAGE_REVIEW_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )

    assert approved["ready"] is True
    assert approved["execution_hash"] == unapproved["execution_hash"]
    assert approved["suite"]["cost_limit_usd"] == 6
    assert approved["blockers"] == []


def test_consumed_coverage_review_pilot_is_hard_immutable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 2, 0, tzinfo=UTC),
    )
    unsigned = eval_runner.preflight_suite(COVERAGE_REVIEW_PILOT_SUITE)
    approved = eval_runner.preflight_suite(
        COVERAGE_REVIEW_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unsigned["execution_hash"],
    )

    assert approved["ready"] is False
    assert {row["code"] for row in approved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE"
    }


def test_coverage_review_approved_plan_binds_v10_runtime_and_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS",
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
        - eval_runner.CONSUMED_COVERAGE_REVIEW_PILOT_EXPERIMENT_IDS,
    )
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 2, 0, tzinfo=UTC),
    )
    monkeypatch.setattr("patchloop.runtime.git_commit", lambda: "a" * 40)
    monkeypatch.setattr("patchloop.runtime.version", lambda _package: "2.47.0")

    suite = eval_runner.load_suite(COVERAGE_REVIEW_PILOT_SUITE)
    unsigned = eval_runner.preflight_suite(COVERAGE_REVIEW_PILOT_SUITE)
    approved = eval_runner.preflight_suite(
        COVERAGE_REVIEW_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unsigned["execution_hash"],
    )
    plan = eval_runner._persist_preflight_plan(approved)
    item = approved["schedule"][0]
    task_row = approved["tasks"][0]
    task_path = Path(item["task"])
    package = load_task_package(task_path.parent)
    experiment = ExperimentRunContext(
        experiment_id=suite.experiment_id,
        purpose=suite.purpose,
        suite_hash=approved["suite_hash"],
        execution_hash=approved["execution_hash"],
        dataset_manifest_hash=approved["dataset"]["manifest_hash"],
        dataset_role=DatasetRole(item["dataset_role"]),
        schedule_seed=suite.seed,
        schedule_order=item["order"],
        schedule_row_id=item["schedule_row_id"],
        repetition=item["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id="run_coverage_review_paid_boundary",
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(item["condition"]),
        sandbox_backend="docker",
        budget=suite.budget,
        agent_image_digest=item["evaluator_image_digest"],
        evaluator_image_digest=item["evaluator_image_digest"],
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
        max_output_tokens=suite.max_output_tokens,
        experiment_context=experiment,
        coverage_review_live_pilot=True,
        public_review_contract=PublicReviewContract.model_validate(
            task_row["public_review_contract"]
        ),
    )

    eval_runner._assert_manifest_matches_preflight(
        manifest,
        suite=suite,
        preflight=approved,
        item={**task_row, **item},
    )
    authorization = SimpleNamespace(plan_path=plan["path"])
    assert AgentRunner._live_plan_matches_manifest(manifest, authorization) is True
    plan_payload = json.loads(Path(plan["path"]).read_text(encoding="utf-8"))
    assert trace_qualification._execution_plan_matches(
        plan=plan_payload,
        manifest=manifest,
    ) is True

    tampered = json.loads(json.dumps(plan_payload))
    tampered["runtime_contract"]["tool_schema_version"] = "v4"
    assert trace_qualification._execution_plan_matches(
        plan=tampered,
        manifest=manifest,
    ) is False
    tampered = json.loads(json.dumps(plan_payload))
    tampered["tasks"][0]["public_review_contract"]["content_hash"] = (
        "sha256:" + ("0" * 64)
    )
    assert trace_qualification._execution_plan_matches(
        plan=tampered,
        manifest=manifest,
    ) is False


def test_saturation_approved_plan_binds_paid_boundary_and_qualification_inputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    boundary_at = datetime(2026, 8, 1, 12, tzinfo=UTC)
    monkeypatch.setattr(eval_runner, "utc_now", lambda: boundary_at)
    monkeypatch.setattr(
        "patchloop.runtime.git_commit",
        lambda: "a" * 40,
    )
    monkeypatch.setattr(
        "patchloop.runtime.version",
        lambda _package: "2.47.0",
    )
    monkeypatch.setattr(
        eval_runner,
        "HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS",
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
        - eval_runner.CONSUMED_SATURATION_PILOT_EXPERIMENT_IDS,
    )

    suite = eval_runner.load_suite(SATURATION_PILOT_SUITE)
    unsigned = eval_runner.preflight_suite(SATURATION_PILOT_SUITE)
    approved = eval_runner.preflight_suite(
        SATURATION_PILOT_SUITE,
        approve_live_cost=True,
        approved_execution_hash=unsigned["execution_hash"],
    )
    assert approved["ready"] is True
    plan = eval_runner._persist_preflight_plan(approved)
    item = approved["schedule"][0]
    task_path = Path(item["task"])
    package = load_task_package(task_path.parent)
    task_row = approved["tasks"][0]
    experiment = ExperimentRunContext(
        experiment_id=suite.experiment_id,
        purpose=suite.purpose,
        suite_hash=approved["suite_hash"],
        execution_hash=approved["execution_hash"],
        dataset_manifest_hash=approved["dataset"]["manifest_hash"],
        dataset_role=DatasetRole(item["dataset_role"]),
        schedule_seed=suite.seed,
        schedule_order=item["order"],
        schedule_row_id=item["schedule_row_id"],
        repetition=item["repetition"],
    )
    manifest = build_manifest(
        package,
        run_id="run_saturation_paid_boundary",
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(item["condition"]),
        sandbox_backend="docker",
        budget=suite.budget,
        agent_image_digest=item["evaluator_image_digest"],
        evaluator_image_digest=item["evaluator_image_digest"],
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
        max_output_tokens=suite.max_output_tokens,
        fault=eval_runner._diagnostic_fault(suite),
        experiment_context=experiment,
        saturation_live_pilot=True,
        public_review_contract=PublicReviewContract.model_validate(
            task_row["public_review_contract"]
        ),
    )
    eval_runner._assert_manifest_matches_preflight(
        manifest,
        suite=suite,
        preflight=approved,
        item={**task_row, **item},
    )
    authorization = SimpleNamespace(plan_path=plan["path"])
    assert AgentRunner._live_plan_matches_manifest(
        manifest,
        authorization,
    ) is True

    plan_payload = json.loads(
        Path(plan["path"]).read_text(encoding="utf-8")
    )
    assert trace_qualification._execution_plan_matches(
        plan=plan_payload,
        manifest=manifest,
    ) is True
    freshness = eval_runner._pricing_freshness_evidence(
        suite,
        boundary_at=boundary_at,
    )
    assert eval_runner._pricing_freshness_passed(freshness) is True

    run_root = tmp_path / "runtime"
    state = StateStore(run_root / "state.sqlite3")
    state.create_run(manifest)
    artifacts = ArtifactStore(run_root / "artifacts")
    system_prompt, tools = AgentRunner._runtime_contract(manifest)
    runtime_artifact = artifacts.put_json(
        {
            "schema_version": "corrective-runtime-contract-v2",
            "system_prompt": system_prompt,
            "tools": tools,
            "tool_schema_version": "v4",
            "context_policy_version": "phase-evidence-v8",
        }
    )
    monkeypatch.setattr(
        "patchloop.state.store.utc_now",
        lambda: boundary_at,
    )
    state.append_event(
        manifest.run_id,
        EventType.RUN_STARTED,
        actor="runner",
        payload={
            "task_id": manifest.task_id,
            "artifact_id": runtime_artifact.artifact_id,
            "artifact_path": runtime_artifact.path,
            "artifact_role": "runtime-contract",
            "runtime_contract_artifact": runtime_artifact.model_dump(
                mode="json"
            ),
        },
    )
    qualification = trace_qualification.qualify_run(
        manifest.run_id,
        task_dir=task_path.parent,
        root=run_root,
        persist=False,
    )
    checks = {
        check["check_id"]: check for check in qualification["checks"]
    }
    assert checks["public_review_contract"]["passed"] is True
    assert checks["corrective_runtime_contract"]["passed"] is True
    assert checks["approved_execution_plan"]["passed"] is True
    assert checks["pricing_start_freshness"]["passed"] is True
    assert checks["saturation_context_contract"]["passed"] is False
    assert qualification["qualified"] is False

    tampered = manifest.model_copy(deep=True)
    tampered.budget = tampered.budget.model_copy(
        update={"max_total_tokens": 899_999}
    )
    assert AgentRunner._live_plan_matches_manifest(
        tampered,
        authorization,
    ) is False

    tampered = manifest.model_copy(deep=True)
    tampered.experiment.schedule_row_id = "sha256:" + "f" * 64
    assert AgentRunner._live_plan_matches_manifest(
        tampered,
        authorization,
    ) is False


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("task", "exactly the frozen HF Hub task"),
        ("repetition", "exactly the frozen HF Hub task"),
        ("condition", "exactly the frozen HF Hub task"),
        ("budget", "max_total_tokens=900000"),
        ("output", "max_total_tokens=900000"),
        ("cap", "requires cost_limit_usd=5"),
        ("estimate", "requires estimated_cost_usd=4.1625"),
        ("diagnostic", "exact v8 saturation diagnostic"),
    ],
)
def test_saturation_pilot_rejects_contract_drift(
    mutation: str,
    match: str,
) -> None:
    payload = yaml.safe_load(
        Path(SATURATION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    if mutation == "task":
        payload["tasks"] = [
            "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml"
        ]
    elif mutation == "repetition":
        payload["repetitions"] = 2
    elif mutation == "condition":
        payload["conditions"] = ["structured"]
    elif mutation == "budget":
        payload["budget"]["max_total_tokens"] = 899_999
    elif mutation == "output":
        payload["max_output_tokens"] = 24_999
    elif mutation == "cap":
        payload["cost_limit_usd"] = 6
    elif mutation == "estimate":
        payload["estimated_cost_usd"] = 4
    else:
        payload["diagnostic"] = None

    with pytest.raises(ValidationError, match=match):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("task", "exactly the frozen HF Hub task"),
        ("repetition", "exactly the frozen HF Hub task"),
        ("condition", "exactly the frozen HF Hub task"),
        ("model_calls", "max_model_calls=60"),
        ("tokens", "max_model_calls=60"),
        ("output", "max_model_calls=60"),
        ("cap", "requires cost_limit_usd=6"),
        ("estimate", "requires estimated_cost_usd=5.5125"),
    ],
)
def test_review_evidence_pilot_rejects_contract_drift(
    mutation: str,
    match: str,
) -> None:
    payload = yaml.safe_load(
        Path(REVIEW_EVIDENCE_PILOT_SUITE).read_text(encoding="utf-8")
    )
    if mutation == "task":
        payload["tasks"] = [
            "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml"
        ]
    elif mutation == "repetition":
        payload["repetitions"] = 2
    elif mutation == "condition":
        payload["conditions"] = ["structured"]
    elif mutation == "model_calls":
        payload["budget"]["max_model_calls"] = 59
    elif mutation == "tokens":
        payload["budget"]["max_total_tokens"] = 1_199_999
    elif mutation == "output":
        payload["max_output_tokens"] = 24_999
    elif mutation == "cap":
        payload["cost_limit_usd"] = 7
    else:
        payload["estimated_cost_usd"] = 5.5

    with pytest.raises(ValidationError, match=match):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("id", "exact D-070 id"),
        ("purpose", "D-070 experiment id"),
        ("task", "exact D-070 id"),
        ("repetition", "exact D-070 id"),
        ("condition", "exact D-070 id"),
        ("model_calls", "max_model_calls=60"),
        ("tool_calls", "max_tool_calls=100"),
        ("tokens", "max_total_tokens=1200000"),
        ("wall", "wall_clock_timeout_seconds=1800"),
        ("output", "max_model_calls=60"),
        ("cap", "requires cost_limit_usd=6"),
        ("estimate", "requires estimated_cost_usd=5.5125"),
    ],
)
def test_coverage_review_pilot_rejects_contract_drift(
    mutation: str,
    match: str,
) -> None:
    payload = yaml.safe_load(
        Path(COVERAGE_REVIEW_PILOT_SUITE).read_text(encoding="utf-8")
    )
    if mutation == "id":
        payload["experiment_id"] = "alternate-coverage-review-pilot"
    elif mutation == "purpose":
        payload["purpose"] = "memory-development-no-memory-review-evidence-pilot"
    elif mutation == "task":
        payload["tasks"] = [
            "tasks/dev-train/pdm-ignore-active-venv-resolution/public.yaml"
        ]
    elif mutation == "repetition":
        payload["repetitions"] = 2
    elif mutation == "condition":
        payload["conditions"] = ["structured"]
    elif mutation == "model_calls":
        payload["budget"]["max_model_calls"] = 59
    elif mutation == "tool_calls":
        payload["budget"]["max_tool_calls"] = 99
    elif mutation == "tokens":
        payload["budget"]["max_total_tokens"] = 1_199_999
    elif mutation == "wall":
        payload["budget"]["wall_clock_timeout_seconds"] = 1_799
    elif mutation == "output":
        payload["max_output_tokens"] = 24_999
    elif mutation == "cap":
        payload["cost_limit_usd"] = 7
    else:
        payload["estimated_cost_usd"] = 5.5

    with pytest.raises(ValidationError, match=match):
        ExperimentSuite.model_validate(payload)


def test_saturation_diagnostic_separates_pass_inconclusive_and_failure() -> None:
    base = {
        "qualified": True,
        "evaluation_reached": True,
        "qualification_hash": "sha256:" + "a" * 64,
        "trace_features": {
            "saturation_context": {
                "check_count": 1,
                "check_passed": True,
                "saturated_context_count": 1,
                "read_search_removed_saturated_context_sequences": [20],
                "post_saturation_patch_count": 1,
                "reset_opportunity_count": 1,
                "reset_context_count": 1,
                "reset_context_sequences": [30],
                "failed_reset_context_sequences": [],
            }
        },
    }

    passed = eval_runner._saturation_diagnostic_result(base)
    assert passed["status"] == "passed"
    assert passed["reason_code"] is None
    assert passed["required_trace_features"] == ["saturation_context"]
    assert passed["qualification_hash"] == base["qualification_hash"]
    assert passed["features"]["saturation_context"][
        "reset_context_sequences"
    ] == [30]

    before_evaluator = json.loads(json.dumps(base))
    before_evaluator["evaluation_reached"] = False
    assert eval_runner._saturation_diagnostic_result(before_evaluator)[
        "status"
    ] == "passed"

    no_saturation = json.loads(json.dumps(base))
    feature = no_saturation["trace_features"]["saturation_context"]
    feature["saturated_context_count"] = 0
    feature["read_search_removed_saturated_context_sequences"] = []
    assert eval_runner._saturation_diagnostic_result(no_saturation)[
        "reason_code"
    ] == "saturation_not_observed"

    failed_reset = json.loads(json.dumps(base))
    feature = failed_reset["trace_features"]["saturation_context"]
    feature["reset_context_count"] = 0
    feature["reset_context_sequences"] = []
    feature["failed_reset_context_sequences"] = [30]
    failed = eval_runner._saturation_diagnostic_result(failed_reset)
    assert failed["status"] == "failed"
    assert failed["reason_code"] == "post_saturation_reset_not_verified"


def test_saturation_completion_gate_requires_exercise_not_task_success() -> None:
    suite = eval_runner.load_suite(SATURATION_PILOT_SUITE)
    row = {
        "attempt_status": "terminal",
        "run_id": "run_saturation",
        "result": {
            "official": True,
            "evaluation_status": "completed",
            "scope_compliant_success": False,
            "terminal_error": None,
        },
        "qualification": {
            "qualified": True,
            "evaluation_reached": True,
        },
        "diagnostic": {"status": "passed"},
        "infrastructure_error": None,
        "qualification_error": None,
        "diagnostic_error": None,
    }

    gate = eval_runner._completion_gate(suite, [row])

    assert gate is not None
    assert gate["schema_version"] == "v8-saturation-live-pilot-gate-v1"
    assert gate["passed"] is True
    assert gate["task_successes"] == 0
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False

    row["diagnostic"] = {"status": "inconclusive"}
    row["diagnostic_error"] = {"type": "TraceExerciseInconclusive"}
    assert eval_runner._completion_gate(suite, [row])["passed"] is False

    row["diagnostic"] = {"status": "passed"}
    row["diagnostic_error"] = None
    row["qualification"]["evaluation_reached"] = False
    assert eval_runner._completion_gate(suite, [row])["passed"] is False
    row["qualification"]["evaluation_reached"] = True
    row["result"]["terminal_error"] = {
        "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "details": {"reason_code": "model_call_budget_exhausted"},
    }
    assert eval_runner._completion_gate(suite, [row])["passed"] is False


def test_review_evidence_completion_gate_requires_evaluator_not_task_success() -> None:
    suite = eval_runner.load_suite(REVIEW_EVIDENCE_PILOT_SUITE)
    row = {
        "attempt_status": "terminal",
        "run_id": "run_review_evidence",
        "result": {
            "official": True,
            "evaluation_status": "completed",
            "scope_compliant_success": False,
            "terminal_error": None,
        },
        "qualification": {
            "qualified": True,
            "evaluation_reached": True,
        },
        "diagnostic": None,
        "infrastructure_error": None,
        "qualification_error": None,
        "diagnostic_error": None,
    }

    gate = eval_runner._completion_gate(suite, [row])

    assert gate is not None
    assert gate["schema_version"] == "v9-review-evidence-live-pilot-gate-v1"
    assert gate["passed"] is True
    assert gate["task_successes"] == 0
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False

    row["qualification"]["evaluation_reached"] = False
    assert eval_runner._completion_gate(suite, [row])["passed"] is False
    row["qualification"]["evaluation_reached"] = True
    row["result"]["terminal_error"] = {
        "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "details": {"reason_code": "model_call_budget_exhausted"},
    }
    assert eval_runner._completion_gate(suite, [row])["passed"] is False


def test_coverage_review_completion_gate_requires_nonvacuous_v10_lifecycle() -> None:
    suite = eval_runner.load_suite(COVERAGE_REVIEW_PILOT_SUITE)
    row = {
        "attempt_status": "terminal",
        "run_id": "run_coverage_review",
        "result": {
            "official": True,
            "evaluation_status": "completed",
            "scope_compliant_success": False,
            "terminal_error": None,
        },
        "qualification": {
            "qualified": True,
            "evaluation_reached": True,
            "trace_features": {
                "public_coverage_review": {"observed": True}
            },
        },
        "diagnostic": None,
        "infrastructure_error": None,
        "qualification_error": None,
        "diagnostic_error": None,
    }

    gate = eval_runner._completion_gate(suite, [row])

    assert gate is not None
    assert gate["schema_version"] == "v10-coverage-review-live-pilot-gate-v1"
    assert gate["passed"] is True
    assert gate["coverage_lifecycle_observed_runs"] == 1
    assert gate["task_successes"] == 0
    assert gate["task_success_required"] is False
    assert gate["comparison_denominator_eligible"] is False
    assert gate["memory_admission_unlocked"] is False

    row["qualification"]["trace_features"] = {}
    assert eval_runner._completion_gate(suite, [row])["passed"] is False
    row["qualification"]["trace_features"] = {
        "public_coverage_review": {"observed": True}
    }
    row["result"]["terminal_error"] = {
        "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "details": {"reason_code": "model_call_budget_exhausted"},
    }
    assert eval_runner._completion_gate(suite, [row])["passed"] is False


def test_terminal_qualification_sanitizes_nonvacuous_v10_coverage_feature(
    monkeypatch,
) -> None:
    checks = [
        {
            "check_id": "public_coverage_contract",
            "passed": True,
            "details": {"coverage_target_count": 8},
        },
        {
            "check_id": "coverage_decision_integrity",
            "passed": True,
            "details": {"coverage_complete_review_count": 1},
        },
        {
            "check_id": "coverage_submission_lifecycle",
            "passed": True,
            "details": {
                "accepted_submission_count": 1,
                "evaluation_completed": True,
            },
        },
        {
            "check_id": "coverage_recovery_contract",
            "passed": True,
            "details": {
                "nonvacuous": True,
                "accepted_finish_count": 1,
            },
        },
        {
            "check_id": "coverage_terminal_contract",
            "passed": True,
            "details": {
                "coverage_complete_review_sequences": [41],
                "accepted_submission_count": 1,
                "evaluation_completed": True,
            },
        },
    ]
    payload = {
        "qualified": True,
        "checks": checks,
    }
    monkeypatch.setattr(
        trace_qualification,
        "qualify_run",
        lambda *_args, **_kwargs: payload,
    )

    summary = eval_runner._qualify_terminal_run(
        "run_coverage_feature",
        eval_runner.COVERAGE_REVIEW_PILOT_TASK,
    )
    feature = summary["trace_features"]["public_coverage_review"]
    assert feature["observed"] is True
    assert feature["coverage_target_count"] == 8
    assert feature["check_counts"] == {
        "public_coverage_contract": 1,
        "coverage_decision_integrity": 1,
        "coverage_submission_lifecycle": 1,
        "coverage_recovery_contract": 1,
        "coverage_terminal_contract": 1,
    }

    payload["checks"] = [*checks, checks[0]]
    duplicated = eval_runner._qualify_terminal_run(
        "run_coverage_feature_duplicate",
        eval_runner.COVERAGE_REVIEW_PILOT_TASK,
    )
    assert duplicated["trace_features"]["public_coverage_review"][
        "observed"
    ] is False


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("task", "exact three frozen resource-max tasks"),
        ("repetition", "exact three frozen resource-max tasks"),
        ("budget", "max_total_tokens=480000"),
    ],
)
def test_memory_development_budget_pilot_rejects_contract_drift(
    mutation: str,
    match: str,
) -> None:
    payload = yaml.safe_load(
        Path(BUDGET_PILOT_SUITE).read_text(encoding="utf-8")
    )
    if mutation == "task":
        payload["tasks"] = payload["tasks"][:-1]
    elif mutation == "repetition":
        payload["repetitions"] = 2
    else:
        payload["budget"]["max_total_tokens"] = 600_000

    with pytest.raises(ValidationError, match=match):
        ExperimentSuite.model_validate(payload)


def _budget_pilot_completion_rows() -> list[dict]:
    return [
        {
            "attempt_status": "terminal",
            "run_id": f"run_budget_pilot_{index}",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "model_calls": 2,
                "tool_calls": 1,
                "wall_clock_ms": 1_000,
            },
            "result": {
                "official": True,
                "evaluation_status": "completed",
                "scope_compliant_success": False,
                "terminal_error": None,
            },
            "qualification": {
                "qualified": True,
                "evaluation_reached": True,
            },
            "infrastructure_error": None,
            "qualification_error": None,
            "diagnostic_error": None,
        }
        for index in range(3)
    ]


def test_memory_development_budget_pilot_completion_gate_passes_without_task_success(
) -> None:
    suite = eval_runner.load_suite(BUDGET_PILOT_SUITE)

    gate = eval_runner._completion_gate(
        suite,
        _budget_pilot_completion_rows(),
    )

    assert gate == {
        "schema_version": "no-memory-budget-pilot-gate-v1",
        "passed": True,
        "expected_runs": 3,
        "terminal_runs": 3,
        "qualified_runs": 3,
        "evaluator_reached_runs": 3,
        "official_evaluator_runs": 3,
        "infrastructure_errors": 0,
        "qualification_errors": 0,
        "diagnostic_errors": 0,
        "budget_terminal_runs": 0,
        "budget_terminal_run_ids": [],
        "task_successes": 0,
        "task_success_required": False,
        "comparison_denominator_eligible": False,
        "memory_admission_unlocked": False,
    }


def test_memory_development_budget_pilot_completion_gate_rejects_run_errors(
) -> None:
    suite = eval_runner.load_suite(BUDGET_PILOT_SUITE)
    rows = _budget_pilot_completion_rows()
    rows[0]["result"]["terminal_error"] = {
        "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
        "details": {"reason_code": "exact_request_budget_exceeded"},
    }
    rows[0]["infrastructure_error"] = {"type": "InfrastructureError"}
    rows[1]["qualification_error"] = {"type": "QualificationError"}
    rows[2]["diagnostic_error"] = {"type": "DiagnosticError"}

    gate = eval_runner._completion_gate(suite, rows)

    assert gate is not None
    assert gate["passed"] is False
    assert gate["budget_terminal_runs"] == 1
    assert gate["budget_terminal_run_ids"] == ["run_budget_pilot_0"]
    assert gate["infrastructure_errors"] == 1
    assert gate["qualification_errors"] == 1
    assert gate["diagnostic_errors"] == 1
    assert gate["terminal_runs"] == 3
    assert gate["qualified_runs"] == 3
    assert gate["evaluator_reached_runs"] == 3
    assert gate["official_evaluator_runs"] == 3


def test_future_comparison_templates_remain_at_250k_pending_calibration() -> None:
    for path in (
        "experiments/dev-no-memory-v5.template.yaml",
        "experiments/core.template.yaml",
    ):
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        assert payload["budget"]["max_model_calls"] == 21
        assert payload["budget"]["max_total_tokens"] == 250_000


def test_gpt54mini_pilot_has_exact_model_budget_and_pricing_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-validation-gpt54mini-pilot-r2.yaml"

    unapproved = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in unapproved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert unapproved["purpose"] == (
        "development-validation-model-candidate-pilot"
    )
    assert unapproved["suite"]["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert unapproved["suite"]["budget"]["max_total_tokens"] == 90_000
    assert unapproved["suite"]["max_output_tokens"] == 4096
    assert unapproved["pricing"]["input_price_per_million_usd"] == 0.75
    assert unapproved["pricing"]["cached_input_price_per_million_usd"] == 0.075
    assert unapproved["pricing"]["cache_write_input_price_per_million_usd"] is None
    assert unapproved["pricing"]["output_price_per_million_usd"] == 4.5
    assert unapproved["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        (90_000 + 4096) * 4.5 / 1_000_000
    )

    approved = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=unapproved["execution_hash"],
    )
    assert approved["ready"] is False
    assert {row["code"] for row in approved["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE"
    }


def test_d037_r3_pilot_binds_exact_diagnostic_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    r1 = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-pilot.yaml"
    )
    r2 = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-pilot-r2.yaml"
    )
    suite_path = "experiments/dev-validation-gpt54mini-d037-r3.yaml"
    r3 = eval_runner.load_suite(suite_path)

    assert r1.diagnostic is None
    assert r2.diagnostic is None
    assert r3.diagnostic is not None
    assert r3.diagnostic.profile == "d037-rejected-patch-retry-v1"
    assert r3.diagnostic.required_trace_features == [
        "rejected_patch_retry_context"
    ]
    historical_payload = r2.model_dump(mode="json")
    historical_payload.pop("diagnostic")
    assert eval_runner._suite_hash(r2) == sha256_text(
        canonical_json(historical_payload)
    )
    r2_yaml = yaml.safe_load(
        Path(
            "experiments/dev-validation-gpt54mini-pilot-r2.yaml"
        ).read_text(encoding="utf-8")
    )
    r3_yaml = yaml.safe_load(
        Path(suite_path).read_text(encoding="utf-8")
    )
    r3_yaml.pop("diagnostic")
    r3_yaml["experiment_id"] = r2_yaml["experiment_id"]
    assert r3_yaml == r2_yaml

    preflight = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in preflight["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["suite"]["diagnostic"] == {
        "schema_version": "experiment-diagnostic-v1",
        "profile": "d037-rejected-patch-retry-v1",
        "required_trace_features": [
            "rejected_patch_retry_context"
        ],
    }


def test_d037_r4_binds_corrective_output_allowance_and_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-validation-gpt54mini-d037-r4.yaml"

    suite = eval_runner.load_suite(suite_path)

    assert suite.diagnostic is not None
    assert suite.diagnostic.profile == "d037-rejected-patch-retry-v2"
    assert suite.max_output_tokens == 25_000
    assert suite.budget.max_total_tokens == 120_000
    assert suite.estimated_cost_usd == pytest.approx(0.66)

    preflight = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in preflight["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["suite"]["diagnostic"]["profile"] == (
        "d037-rejected-patch-retry-v2"
    )
    assert preflight["suite"]["max_output_tokens"] == 25_000
    assert preflight["suite"]["budget"]["max_total_tokens"] == 120_000
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        (120_000 + 25_000) * 4.5 / 1_000_000
    )
    assert preflight["pricing"]["budget_upper_bound_usd"] == pytest.approx(
        0.6525
    )


def test_d037_r5_binds_tail_reserve_budget_without_changing_output_allowance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-validation-gpt54mini-d037-r5.yaml"

    suite = eval_runner.load_suite(suite_path)

    assert suite.diagnostic is not None
    assert suite.diagnostic.profile == "d037-rejected-patch-retry-v3"
    assert suite.max_output_tokens == 25_000
    assert suite.budget.max_total_tokens == 200_000
    assert suite.estimated_cost_usd == pytest.approx(1.02)
    assert suite.live_cost_approved is False
    assert suite.approved_execution_hash is None

    preflight = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in preflight["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["suite"]["diagnostic"]["profile"] == (
        "d037-rejected-patch-retry-v3"
    )
    assert preflight["suite"]["max_output_tokens"] == 25_000
    assert preflight["suite"]["budget"]["max_total_tokens"] == 200_000
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        (200_000 + 25_000) * 4.5 / 1_000_000
    )
    assert preflight["pricing"]["budget_upper_bound_usd"] == pytest.approx(
        1.0125
    )


def test_d037_r6_binds_one_shot_controlled_rejection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-validation-gpt54mini-d037-r6.yaml"

    suite = eval_runner.load_suite(suite_path)

    assert suite.diagnostic is not None
    assert suite.diagnostic.profile == "d037-rejected-patch-retry-v4"
    assert suite.max_output_tokens == 25_000
    assert suite.budget.max_total_tokens == 200_000
    assert eval_runner._diagnostic_fault(suite) == FaultSpec(
        type="controlled-reject-first-prepared-patch",
        trigger_after=1,
    )

    preflight = eval_runner.preflight_suite(suite_path)

    assert {row["code"] for row in preflight["blockers"]} == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert preflight["suite"]["diagnostic"]["profile"] == (
        "d037-rejected-patch-retry-v4"
    )
    assert preflight["pricing"]["budget_upper_bound_usd"] == pytest.approx(
        1.0125
    )


def test_d037_r6_profile_change_removes_controlled_fault_and_changes_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path(
            "experiments/dev-validation-gpt54mini-d037-r6.yaml"
        ).read_text(encoding="utf-8")
    )
    controlled_path = tmp_path / "controlled.yaml"
    controlled_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    controlled = eval_runner.preflight_suite(controlled_path)

    payload["diagnostic"]["profile"] = (
        "d037-rejected-patch-retry-v3"
    )
    natural_path = tmp_path / "natural.yaml"
    natural_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    natural_suite = eval_runner.load_suite(natural_path)
    natural = eval_runner.preflight_suite(natural_path)

    assert eval_runner._diagnostic_fault(natural_suite) == FaultSpec()
    assert natural["execution_hash"] != controlled["execution_hash"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_output_tokens", 4096),
        ("budget", {"max_total_tokens": 120_000}),
        (
            "diagnostic",
            {
                "schema_version": "experiment-diagnostic-v1",
                "profile": "d037-rejected-patch-retry-v2",
                "required_trace_features": [
                    "rejected_patch_retry_context"
                ],
            },
        ),
    ],
)
def test_d037_r5_rejects_partial_tail_reserve_contract(
    field: str,
    value: object,
) -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r5.yaml").read_text(
            encoding="utf-8"
        )
    )
    if field == "budget":
        payload["budget"].update(value)
    else:
        payload[field] = value

    with pytest.raises(ValidationError):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_output_tokens", 4096),
        ("budget", {"max_total_tokens": 90_000}),
        (
            "diagnostic",
            {
                "schema_version": "experiment-diagnostic-v1",
                "profile": "d037-rejected-patch-retry-v1",
                "required_trace_features": [
                    "rejected_patch_retry_context"
                ],
            },
        ),
    ],
)
def test_d037_r4_rejects_partial_corrective_contract(
    field: str,
    value: object,
) -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r4.yaml").read_text(
            encoding="utf-8"
        )
    )
    if field == "budget":
        payload["budget"].update(value)
    else:
        payload[field] = value

    with pytest.raises(ValidationError):
        ExperimentSuite.model_validate(payload)


def test_d037_diagnostic_is_rejected_outside_model_candidate_pilot() -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["purpose"] = "development-validation-live-pilot"

    with pytest.raises(
        ValidationError,
        match="diagnostic profiles are allowed only",
    ):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize(
    "required_features",
    [
        [
            "rejected_patch_retry_context",
            "rejected_patch_retry_context",
        ],
        ["unknown_feature"],
    ],
)
def test_d037_diagnostic_rejects_invalid_feature_contract(
    required_features: list[str],
) -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["diagnostic"]["required_trace_features"] = required_features

    with pytest.raises(ValidationError):
        ExperimentSuite.model_validate(payload)


def test_d037_diagnostic_removal_invalidates_approved_execution_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["experiment_id"] = "d037-hash-binding"
    suite_path = tmp_path / "d037-hash-binding.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    diagnostic_preflight = eval_runner.preflight_suite(suite_path)
    payload.pop("diagnostic")
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    modified_preflight = eval_runner.preflight_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=diagnostic_preflight["execution_hash"],
    )

    assert (
        modified_preflight["execution_hash"]
        != diagnostic_preflight["execution_hash"]
    )
    assert "APPROVAL_HASH_MISMATCH" in {
        row["code"] for row in modified_preflight["blockers"]
    }

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail(
                "changed diagnostic contract must stop before runner creation"
            )

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="approved execution hash"):
        eval_runner.evaluate_suite(
            suite_path,
            approve_live_cost=True,
            approved_execution_hash=diagnostic_preflight[
                "execution_hash"
            ],
        )
    assert not (
        tmp_path
        / "runtime"
        / "experiments"
        / "journals"
        / "d037-hash-binding.jsonl"
    ).exists()


@pytest.mark.parametrize(
    ("qualification", "expected_status", "expected_reason"),
    [
        (
            _retry_qualification(
                retry_episode_count=1,
                verified_retry_count=1,
                failed_source_failure_sequences=[],
            ),
            "passed",
            None,
        ),
        (
            _retry_qualification(
                retry_episode_count=0,
                verified_retry_count=0,
                failed_source_failure_sequences=[],
            ),
            "inconclusive",
            "retry_episode_not_observed",
        ),
        (
            _retry_qualification(
                retry_episode_count=2,
                verified_retry_count=1,
                failed_source_failure_sequences=[42],
            ),
            "failed",
            "retry_episode_not_fully_verified",
        ),
        (
            {
                **_retry_qualification(
                    retry_episode_count=1,
                    verified_retry_count=1,
                    failed_source_failure_sequences=[],
                ),
                "evaluation_reached": False,
            },
            "failed",
            "evaluation_not_reached",
        ),
    ],
)
def test_d037_diagnostic_truth_table(
    qualification: dict,
    expected_status: str,
    expected_reason: str | None,
) -> None:
    suite = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-d037-r3.yaml"
    )

    diagnostic = eval_runner._diagnostic_result(suite, qualification)

    assert diagnostic is not None
    assert diagnostic["status"] == expected_status
    assert diagnostic["reason_code"] == expected_reason


@pytest.mark.parametrize(
    (
        "controlled_count",
        "verified_controlled_count",
        "controlled_failures",
        "controlled_applied",
        "expected_status",
        "expected_reason",
    ),
    [
        (1, 1, [], [], "passed", None),
        (
            0,
            0,
            [],
            [],
            "failed",
            "controlled_rejection_not_verified",
        ),
        (
            2,
            1,
            [41],
            [],
            "failed",
            "controlled_rejection_not_verified",
        ),
        (
            1,
            1,
            [],
            [42],
            "failed",
            "controlled_rejection_not_verified",
        ),
    ],
)
def test_d037_controlled_diagnostic_truth_table(
    controlled_count: int,
    verified_controlled_count: int,
    controlled_failures: list[int],
    controlled_applied: list[int],
    expected_status: str,
    expected_reason: str | None,
) -> None:
    suite = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-d037-r6.yaml"
    )
    qualification = _retry_qualification(
        retry_episode_count=1,
        verified_retry_count=1,
        failed_source_failure_sequences=[],
    )
    qualification["trace_features"][
        "rejected_patch_retry_context"
    ].update(
        {
            "controlled_rejection_count": controlled_count,
            "verified_controlled_rejection_count": (
                verified_controlled_count
            ),
            "failed_controlled_source_failure_sequences": (
                controlled_failures
            ),
            "controlled_patch_applied_sequences": (
                controlled_applied
            ),
        }
    )

    diagnostic = eval_runner._diagnostic_result(
        suite,
        qualification,
    )

    assert diagnostic is not None
    assert diagnostic["status"] == expected_status
    assert diagnostic["reason_code"] == expected_reason


def test_d037_diagnostic_rejects_missing_or_duplicate_qualification_check() -> None:
    suite = eval_runner.load_suite(
        "experiments/dev-validation-gpt54mini-d037-r3.yaml"
    )

    missing = _retry_qualification(
        retry_episode_count=1,
        verified_retry_count=1,
        failed_source_failure_sequences=[],
        check_count=0,
    )
    duplicate = _retry_qualification(
        retry_episode_count=1,
        verified_retry_count=1,
        failed_source_failure_sequences=[],
        check_count=2,
    )
    unqualified = _retry_qualification(
        retry_episode_count=1,
        verified_retry_count=1,
        failed_source_failure_sequences=[],
    )
    unqualified["qualified"] = False

    assert eval_runner._diagnostic_result(
        suite,
        missing,
    )["reason_code"] == "qualification_check_cardinality"
    assert eval_runner._diagnostic_result(
        suite,
        duplicate,
    )["reason_code"] == "qualification_check_cardinality"
    assert eval_runner._diagnostic_result(
        suite,
        unqualified,
    )["reason_code"] == "qualification_not_passed"


def test_d037_qualification_summary_does_not_copy_malformed_bodies(
    monkeypatch,
) -> None:
    secret_body = "PRIVATE_PATCH_OR_ERROR_BODY"
    monkeypatch.setattr(
        trace_qualification,
        "qualify_run",
        lambda *_args, **_kwargs: {
            "qualified": True,
            "checks": [
                {
                    "check_id": "rejected_patch_retry_context",
                    "passed": secret_body,
                    "details": {
                        "rejected_candidate_count": secret_body,
                        "retry_episode_count": secret_body,
                        "verified_retry_count": secret_body,
                        "failed_source_failure_sequences": [
                            secret_body
                        ],
                    },
                }
            ],
        },
    )

    summary = eval_runner._qualify_terminal_run(
        "run_sanitized",
        "tasks/dev-validation/"
        "babel-strict-grouped-decimal-trailing-zeroes/public.yaml",
    )
    feature = summary["trace_features"][
        "rejected_patch_retry_context"
    ]

    assert feature["check_count"] == 1
    assert feature["check_passed"] is None
    assert feature["rejected_candidate_count"] is None
    assert feature["retry_episode_count"] is None
    assert feature["verified_retry_count"] is None
    assert feature["failed_source_failure_sequences"] is None
    assert secret_body not in json.dumps(summary)


def test_gpt54mini_corrective_retry_preserves_terminal_r1_contract() -> None:
    terminal = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot.yaml").read_text(
            encoding="utf-8"
        )
    )
    retry = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot-r2.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert terminal["experiment_id"] == (
        "dev-validation-gpt54mini-pilot-20260729-r1"
    )
    assert retry["experiment_id"] == (
        "dev-validation-gpt54mini-pilot-20260729-r2"
    )
    assert retry["live_cost_approved"] is False
    assert retry["approved_execution_hash"] is None
    ignored = {"experiment_id", "pricing_verified_at"}
    assert {
        key: value for key, value in terminal.items() if key not in ignored
    } == {
        key: value for key, value in retry.items() if key not in ignored
    }


def test_gpt54mini_pilot_rejects_non_frozen_token_budget() -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot-r2.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["budget"]["max_total_tokens"] = 80_000

    with pytest.raises(ValidationError, match="max_total_tokens=90000"):
        ExperimentSuite.model_validate(payload)


def test_gpt54mini_pilot_preflight_rejects_wrong_price(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-pilot-r2.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["experiment_id"] = "gpt54mini-wrong-price"
    payload["input_price_per_million_usd"] = 2.5
    suite_path = tmp_path / "gpt54mini-wrong-price.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    preflight = eval_runner.preflight_suite(suite_path)

    assert "PRICING_RATE_MISMATCH" in {
        row["code"] for row in preflight["blockers"]
    }


def test_v2_development_campaign_has_exact_twelve_run_matrix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    preflight = eval_runner.preflight_suite("experiments/dev-no-memory.template.yaml")

    assert preflight["purpose"] == "memory-development-no-memory"
    assert preflight["expected_runs"] == 12
    assert len({row["schedule_row_id"] for row in preflight["schedule"]}) == 12
    assert {row["dataset_role"] for row in preflight["tasks"]} == {
        "memory-development"
    }
    assert {row["condition"] for row in preflight["schedule"]} == {"no_memory"}
    assert {row["repetition"] for row in preflight["schedule"]} == {1, 2}
    assert preflight["suite"]["budget"]["max_model_calls"] == 21
    assert {
        row["code"] for row in preflight["blockers"]
    } == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
        "QUALIFIED_PILOT_REQUIRED",
    }


def test_v5_development_campaign_reserves_250k_for_all_twelve_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = "experiments/dev-no-memory-v5.template.yaml"

    suite = eval_runner.load_suite(suite_path)
    preflight = eval_runner.preflight_suite(suite_path)

    assert suite.budget.max_total_tokens == 250_000
    assert suite.estimated_cost_usd == pytest.approx(14.85)
    assert preflight["expected_runs"] == 12
    assert preflight["pricing"]["per_run_cost_reserve_usd"] == pytest.approx(
        1.2375
    )
    assert preflight["pricing"]["budget_upper_bound_usd"] == pytest.approx(
        14.85
    )


def test_development_campaign_rejects_stale_pilot_source_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-no-memory-v5.template.yaml").read_text(encoding="utf-8")
    )
    suite_payload["experiment_id"] = "dev-stale-pilot-source"
    suite_payload["pilot_run_id"] = "run_qualified_pilot"
    suite_path = tmp_path / "dev-stale-pilot-source.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    stored_source_hash = "sha256:" + ("a" * 64)
    monkeypatch.setattr(
        trace_qualification,
        "load_trace_qualification",
        lambda *_args, **_kwargs: {
            "run_id": "run_qualified_pilot",
            "purpose": "development-validation-live-pilot",
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("c" * 64),
            "source_evidence_hash": stored_source_hash,
            "outcome_kind": "resolved",
        },
    )
    monkeypatch.setattr(
        trace_qualification,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: "sha256:" + ("b" * 64),
    )

    preflight = eval_runner.preflight_suite(suite_path)

    assert "QUALIFIED_PILOT_REQUIRED" in {
        row["code"] for row in preflight["blockers"]
    }
    assert preflight["pilot_qualification"]["qualified"] is False
    assert preflight["pilot_qualification"]["reason"] == (
        "pilot source evidence hash mismatch"
    )


def test_model_candidate_pilot_cannot_unlock_primary_development_campaign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-no-memory-v5.template.yaml").read_text(encoding="utf-8")
    )
    suite_payload["experiment_id"] = "dev-reject-model-candidate-pilot"
    suite_payload["pilot_run_id"] = "run_model_candidate_pilot"
    suite_path = tmp_path / "dev-reject-model-candidate-pilot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    source_hash = "sha256:" + ("a" * 64)
    monkeypatch.setattr(
        trace_qualification,
        "load_trace_qualification",
        lambda *_args, **_kwargs: {
            "run_id": "run_model_candidate_pilot",
            "purpose": "development-validation-model-candidate-pilot",
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("c" * 64),
            "source_evidence_hash": source_hash,
            "outcome_kind": "resolved",
        },
    )
    monkeypatch.setattr(
        trace_qualification,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: source_hash,
    )

    preflight = eval_runner.preflight_suite(suite_path)

    assert preflight["pilot_qualification"]["qualified"] is False
    assert "QUALIFIED_PILOT_REQUIRED" in {
        row["code"] for row in preflight["blockers"]
    }


def test_legacy_runtime_pilot_cannot_unlock_v2_development_campaign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path("experiments/dev-no-memory-v5.template.yaml").read_text(
            encoding="utf-8"
        )
    )
    suite_payload["experiment_id"] = "dev-reject-v1-runtime-pilot"
    suite_payload["pilot_run_id"] = "run_v1_runtime_pilot"
    suite_path = tmp_path / "dev-reject-v1-runtime-pilot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    source_hash = "sha256:" + ("a" * 64)
    monkeypatch.setattr(
        trace_qualification,
        "load_trace_qualification",
        lambda *_args, **_kwargs: {
            "schema_version": "trace-qualification-v1",
            "run_id": "run_v1_runtime_pilot",
            "purpose": "development-validation-live-pilot",
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("c" * 64),
            "source_evidence_hash": source_hash,
            "outcome_kind": "resolved",
            "model_provider": "openai",
            "memory_condition": "no_memory",
            "fault_type": "none",
        },
    )
    monkeypatch.setattr(
        trace_qualification,
        "calculate_source_evidence_hash",
        lambda *_args, **_kwargs: source_hash,
    )

    preflight = eval_runner.preflight_suite(suite_path)

    pilot = preflight["pilot_qualification"]
    assert pilot["qualified"] is False
    assert "schema_version" in pilot["contract_mismatches"]
    assert "tool_schema_version" in pilot["contract_mismatches"]
    assert "runtime_contract_content_hash" in pilot["contract_mismatches"]
    assert "QUALIFIED_PILOT_REQUIRED" in {
        row["code"] for row in preflight["blockers"]
    }


def test_v2_development_campaign_rejects_an_incomplete_task_set() -> None:
    payload = yaml.safe_load(
        Path("experiments/dev-no-memory-v5.template.yaml").read_text(encoding="utf-8")
    )
    payload["tasks"] = payload["tasks"][:-1]

    with pytest.raises(ValidationError, match="six frozen development tasks"):
        ExperimentSuite.model_validate(payload)


@pytest.mark.parametrize("mutation", ["path", "private", "environment"])
def test_live_preflight_binds_canonical_private_evaluator_package(
    tmp_path: Path,
    monkeypatch,
    mutation: str,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    original_loader = eval_runner.load_task_package
    package = original_loader(Path(eval_runner.PILOT_TASK).parent)
    if mutation == "path":
        forged = package.model_copy(update={"root": str(tmp_path / "forged-task")})
    elif mutation == "private":
        forged = package.model_copy(
            update={"private_spec_hash": "sha256:" + ("f" * 64)}
        )
    else:
        forged = package.model_copy(update={"environment": None})
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _path: forged)

    preflight = eval_runner.preflight_suite(PRIMARY_PILOT_SUITE)

    blockers = {row["code"] for row in preflight["blockers"]}
    assert "TASK_NOT_ELIGIBLE" in blockers
    assert preflight["tasks"] == []


def test_blocked_preflight_happens_before_agent_construction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("AgentRunner must not be constructed before live approval")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="explicit --approve-live-cost"):
        eval_runner.evaluate_suite(
            PRIMARY_PILOT_SUITE
        )


def test_approved_pilot_persists_plan_manifest_and_qualification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = _write_future_primary_suite(
        tmp_path,
        "future-primary-persistence",
    )
    byte_writes: dict[Path, bytes] = {}
    original_write_bytes = Path.write_bytes

    def record_write_bytes(path: Path, content: bytes) -> int:
        byte_writes[path] = content
        return original_write_bytes(path, content)

    monkeypatch.setattr(Path, "write_bytes", record_write_bytes)
    preflight = eval_runner.preflight_suite(suite_path)
    captured = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            captured.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "official": True,
                "evaluation_status": "completed",
                "scope_compliant_success": False,
                "usage": {
                    "model_cost_usd": 0.5,
                    "model_calls": 2,
                    "tool_calls": 1,
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "wall_clock_ms": 1_000,
                },
            }

    qualification_hash = "sha256:" + ("e" * 64)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": qualification_hash,
        },
    )

    result = eval_runner.evaluate_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=preflight["execution_hash"],
    )

    assert len(captured) == 2
    assert all(
        manifest.experiment.purpose
        == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
        for manifest in captured
    )
    assert all(
        manifest.experiment.execution_hash == result["execution_hash"]
        for manifest in captured
    )
    assert all(
        row["qualification"]["qualification_hash"] == qualification_hash
        for row in result["runs"]
    )
    assert result["completion_gate"] == {
        "schema_version": "no-memory-completion-gate-v1",
        "passed": True,
        "expected_runs": 2,
        "terminal_runs": 2,
        "qualified_runs": 2,
        "evaluator_reached_runs": 2,
        "official_evaluator_runs": 2,
        "infrastructure_errors": 0,
        "qualification_errors": 0,
        "diagnostic_errors": 0,
        "budget_terminal_runs": 0,
        "budget_terminal_run_ids": [],
        "task_successes": 0,
        "task_success_required": False,
        "panel_headroom": {
            "max_total_tokens": 480_000,
            "max_model_calls": 32,
            "max_tool_calls": 80,
            "max_wall_clock_ms": 1_440_000,
            "passed": True,
            "failed_run_ids": [],
            "sufficient_to_freeze_comparison_budget": False,
        },
    }
    plan_path = Path(result["execution_plan"]["path"])
    assert plan_path.is_file()
    assert json.loads(plan_path.read_text(encoding="utf-8"))["schema_version"] == (
        "experiment-execution-plan-v1"
    )
    journal_rows = [
        json.loads(line)
        for line in Path(result["campaign_journal"]["path"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == [
        "CampaignStarted",
        "RunStarted",
        "RunTerminal",
        "RunStarted",
        "RunTerminal",
        "CampaignCompleted",
    ]
    assert journal_rows[1]["payload"]["run_id"] == result["runs"][0]["run_id"]
    temporary_result_path = Path(result["path"]).with_suffix(".json.tmp")
    assert byte_writes[temporary_result_path] == Path(result["path"]).read_bytes()
    assert journal_rows[-1]["payload"]["result_hash"] == sha256_bytes(
        byte_writes[temporary_result_path]
    )
    previous_hash = None
    for sequence, row in enumerate(journal_rows, start=1):
        recorded_hash = row.pop("event_hash")
        assert row["sequence"] == sequence
        assert row["previous_event_hash"] == previous_hash
        assert sha256_text(canonical_json(row)) == recorded_hash
        previous_hash = recorded_hash
    retry = eval_runner.preflight_suite(suite_path)
    assert {
        "EXPERIMENT_RESULT_EXISTS",
        "EXPERIMENT_JOURNAL_EXISTS",
    }.issubset({row["code"] for row in retry["blockers"]})


def test_d037_pilot_keeps_inconclusive_exercise_separate_from_qualification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    payload = yaml.safe_load(
        Path("experiments/dev-validation-gpt54mini-d037-r3.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["experiment_id"] = "d037-inconclusive-integration"
    suite_path = tmp_path / "d037-inconclusive-integration.yaml"
    suite_path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )
    preflight = eval_runner.preflight_suite(suite_path)

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "usage": {
                    "model_cost_usd": 0.0,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "input_tokens": 10,
                    "output_tokens": 5,
                },
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            **_retry_qualification(
                retry_episode_count=0,
                verified_retry_count=0,
                failed_source_failure_sequences=[],
            ),
            "run_id": run_id,
        },
    )

    result = eval_runner.evaluate_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=preflight["execution_hash"],
    )
    run = result["runs"][0]

    assert run["qualification"]["qualified"] is True
    assert run["qualification_error"] is None
    assert run["diagnostic"]["status"] == "inconclusive"
    assert run["diagnostic_error"]["type"] == "TraceExerciseInconclusive"
    assert result["qualification_errors"] == 0
    assert result["diagnostic_errors"] == 1
    assert result["diagnostic_gate"] == {
        "profile": "d037-rejected-patch-retry-v1",
        "required_trace_features": [
            "rejected_patch_retry_context"
        ],
        "passed": False,
        "passed_runs": 0,
        "inconclusive_runs": 1,
        "failed_runs": 0,
    }


def test_paid_execution_uses_the_suite_snapshot_approved_by_preflight(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path(COMPLETION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    suite_payload["experiment_id"] = "pilot-suite-snapshot"
    suite_path = tmp_path / "pilot-suite-snapshot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    approved = eval_runner.preflight_suite(suite_path)
    original_preflight = eval_runner.preflight_suite

    def preflight_then_replace_suite(*args, **kwargs):
        preflight = original_preflight(*args, **kwargs)
        replaced = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
        replaced["experiment_id"] = "pilot-suite-snapshot-replaced"
        suite_path.write_text(
            yaml.safe_dump(replaced, sort_keys=False),
            encoding="utf-8",
        )
        return preflight

    captured = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_kwargs):
            captured.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "task_failure",
                "usage": {"model_cost_usd": 0.0},
            }

    monkeypatch.setattr(eval_runner, "preflight_suite", preflight_then_replace_suite)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda run_id, _task: {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "evaluation_reached": True,
            "qualification_hash": "sha256:" + ("e" * 64),
        },
    )

    result = eval_runner.evaluate_suite(
        suite_path,
        approve_live_cost=True,
        approved_execution_hash=approved["execution_hash"],
    )

    assert result["experiment_id"] == "pilot-suite-snapshot"
    assert len(captured) == 2
    assert all(
        manifest.experiment.experiment_id == "pilot-suite-snapshot"
        for manifest in captured
    )
    assert all(
        manifest.model.model_id == "gpt-5.4-mini-2026-03-17"
        for manifest in captured
    )


def test_paid_execution_rejects_task_package_replacement_before_run_start(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_payload = yaml.safe_load(
        Path(COMPLETION_PILOT_SUITE).read_text(encoding="utf-8")
    )
    suite_payload["experiment_id"] = "pilot-task-snapshot"
    suite_path = tmp_path / "pilot-task-snapshot.yaml"
    suite_path.write_text(
        yaml.safe_dump(suite_payload, sort_keys=False),
        encoding="utf-8",
    )
    approved = eval_runner.preflight_suite(suite_path)
    original_loader = eval_runner.load_task_package
    replace_task = False

    def mark_post_preflight(_preflight):
        nonlocal replace_task
        replace_task = True

    def load_replaced_task(path):
        package = original_loader(path)
        if not replace_task:
            return package
        return package.model_copy(
            update={"private_spec_hash": "sha256:" + ("f" * 64)}
        )

    class FakeRunner:
        def start(self, *_args, **_kwargs):
            pytest.fail("replaced task package must not reach the model runner")

    monkeypatch.setattr(
        eval_runner,
        "_assert_live_environment_unchanged",
        mark_post_preflight,
    )
    monkeypatch.setattr(eval_runner, "load_task_package", load_replaced_task)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)

    with pytest.raises(ContractError, match="task package changed"):
        eval_runner.evaluate_suite(
            suite_path,
            approve_live_cost=True,
            approved_execution_hash=approved["execution_hash"],
        )

    journal_path = Path(approved["journal_path"])
    journal_rows = [
        json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == ["CampaignStarted"]


def test_hard_crash_journal_blocks_duplicate_paid_schedule(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = _write_future_primary_suite(
        tmp_path,
        "future-primary-hard-crash",
    )
    preflight = eval_runner.preflight_suite(suite_path)

    class CrashingRunner:
        def start(self, *_args, **_kwargs):
            raise SystemExit("synthetic hard crash after durable row start")

    monkeypatch.setattr(eval_runner, "AgentRunner", CrashingRunner)
    with pytest.raises(SystemExit, match="synthetic hard crash"):
        eval_runner.evaluate_suite(
            suite_path,
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )

    retry = eval_runner.preflight_suite(suite_path)
    assert "EXPERIMENT_JOURNAL_EXISTS" in {
        row["code"] for row in retry["blockers"]
    }
    journal_rows = [
        json.loads(line)
        for line in Path(retry["journal_path"]).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in journal_rows] == [
        "CampaignStarted",
        "RunStarted",
    ]


def test_atomic_journal_claim_blocks_a_racing_paid_invocation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = _write_future_primary_suite(
        tmp_path,
        "future-primary-racing-claim",
    )
    preflight = eval_runner.preflight_suite(suite_path)
    journal_path = Path(preflight["journal_path"])

    def claim_journal_after_preflight(_preflight):
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        journal_path.write_text("claimed-by-racing-invocation\n", encoding="utf-8")

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("a losing journal claimant must not construct AgentRunner")

    monkeypatch.setattr(
        eval_runner,
        "_assert_live_environment_unchanged",
        claim_journal_after_preflight,
    )
    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    monkeypatch.setattr(
        eval_runner,
        "issue_live_execution_authorization",
        lambda *_args, **_kwargs: pytest.fail(
            "a losing journal claimant must not receive live authorization"
        ),
    )

    with pytest.raises(ContractError, match="duplicate schedule ownership"):
        eval_runner.evaluate_suite(
            suite_path,
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )

    assert journal_path.read_text(encoding="utf-8") == (
        "claimed-by-racing-invocation\n"
    )


def test_environment_drift_after_preflight_stops_before_agent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    suite_path = _write_future_primary_suite(
        tmp_path,
        "future-primary-environment-drift",
    )
    commits = iter(["a" * 40, "a" * 40, "b" * 40])
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": next(commits), "clean": True},
    )
    preflight = eval_runner.preflight_suite(suite_path)

    class ForbiddenRunner:
        def __init__(self):
            pytest.fail("environment drift must stop before AgentRunner construction")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="changed after the approved preflight"):
        eval_runner.evaluate_suite(
            suite_path,
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )


@pytest.mark.parametrize("model", ["openai", "gpt-5.6-terra", "unknown-provider"])
def test_direct_openai_run_is_blocked_before_adapter_construction(
    monkeypatch,
    model: str,
) -> None:
    def forbidden_run(*_, **__):
        pytest.fail("direct live run must not reach run_from_cli")

    monkeypatch.setattr("patchloop.agent.runner.run_from_cli", forbidden_run)
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--task",
            "tasks/smoke/csv-quoted-newline/public.yaml",
            "--model",
            model,
        ],
    )

    assert result.exit_code == 1
    assert "direct live runs are disabled" in result.stdout


def test_core_campaign_requires_exact_design() -> None:
    with pytest.raises(ValidationError, match="12 unique"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=["task"],
            conditions=["no_memory"],
            model="mock",
        )


def test_core_campaign_requires_dataset_manifest_hash() -> None:
    with pytest.raises(ValidationError, match="dataset manifest hash"):
        ExperimentSuite(
            experiment_id="core-test",
            core=True,
            tasks=[f"task-{index}" for index in range(12)],
            conditions=[
                "no_memory",
                "raw_trace",
                "structured",
                "selective_structured",
            ],
            repetitions=2,
            model="mock",
            embedding_revision="test-revision",
        )


def test_offline_smoke_remains_a_calibration_suite() -> None:
    suite = eval_runner.load_suite("experiments/smoke.yaml")
    assert suite.core is False
    assert suite.purpose == ExperimentPurpose.OFFLINE_SMOKE
    assert suite.dataset_manifest_hash is None


def test_core_campaign_rejects_calibration_registry_role(tmp_path, monkeypatch) -> None:
    package = load_task_package("tasks/dev-train/duration-minute-boundary")
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(dataset[1]), sort_keys=False),
        encoding="utf-8",
    )
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", lambda _: package)

    with pytest.raises(ContractError, match="dataset role calibration is not eligible"):
        eval_runner.evaluate_suite(suite_path)
    assert preflight_calls == 1


def test_core_campaign_rejects_dataset_manifest_hash_drift(tmp_path, monkeypatch) -> None:
    dataset = load_dataset_manifest()
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("f" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(eval_runner, "require_frozen_dataset", lambda: dataset)

    with pytest.raises(ContractError, match="does not match"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_runs_complete_frozen_dataset_preflight_first(
    tmp_path: Path,
    monkeypatch,
) -> None:
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            _core_suite_payload("sha256:" + ("a" * 64)),
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def reject_incomplete_dataset():
        raise ContractError("core experiment requires a complete frozen dataset")

    def fail_if_task_loading_starts(_):
        pytest.fail("task loading must not start before the frozen-dataset preflight")

    monkeypatch.setattr(
        eval_runner,
        "require_frozen_dataset",
        reject_incomplete_dataset,
    )
    monkeypatch.setattr(eval_runner, "load_task_package", fail_if_task_loading_starts)

    with pytest.raises(ContractError, match="complete frozen dataset"):
        eval_runner.evaluate_suite(suite_path)


def test_core_campaign_schedule_remains_96_runs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest_hash = "sha256:" + ("a" * 64)
    suite_path = tmp_path / "suite.yaml"
    suite_path.write_text(
        yaml.safe_dump(_core_suite_payload(manifest_hash), sort_keys=False),
        encoding="utf-8",
    )
    dataset = SimpleNamespace(dataset_id="core-role-test")
    preflight_calls = 0

    def frozen_preflight():
        nonlocal preflight_calls
        preflight_calls += 1
        return dataset, manifest_hash, tmp_path / "dataset.yaml"

    def fake_load_task_package(path):
        index = int(Path(path).name.removeprefix("task-"))
        split = "same-repo-heldout" if index < 6 else "cross-repo-heldout"
        public = SimpleNamespace(
            task_id=f"task-{index}",
            task_version=1,
            split=split,
            repository=SimpleNamespace(base_commit=f"{index:040x}"),
        )
        image_digest = "sha256:" + f"{index + 200:064x}"
        return SimpleNamespace(
            public=public,
            root=str((eval_runner.repository_root() / f"task-{index}").resolve()),
            public_spec_hash="sha256:" + f"{index:064x}",
            private_spec_hash="sha256:" + f"{index + 100:064x}",
            environment=SimpleNamespace(
                evaluator_image=f"example.invalid/task-{index}@{image_digest}",
                image_digest=image_digest,
            ),
        )

    def fake_require_dataset_role(*, task_id, **_):
        index = int(task_id.removeprefix("task-"))
        role = (
            DatasetRole.CORE_SAME_REPO
            if index < 6
            else DatasetRole.CORE_CROSS_REPO
        )
        return SimpleNamespace(
            role=role,
            path=f"task-{index}",
            private_spec_hash="sha256:" + f"{index + 100:064x}",
        )

    index_path = tmp_path / "memory-index.json"
    index_path.write_text(
        json.dumps(
            {
                "entries": [{"memory_id": "mem_test"}],
                "embedding": {
                    "implementation": "sentence-transformers",
                    "revision": "test-revision",
                },
                "dataset_manifest_hash": manifest_hash,
            }
        ),
        encoding="utf-8",
    )

    starts: list[tuple[str, object]] = []

    class FakeRunner:
        def start(self, task, *, memory_condition, **_):
            starts.append((task, memory_condition))
            return {"usage": {"model_cost_usd": 0.0}}

    monkeypatch.setattr(eval_runner, "require_frozen_dataset", frozen_preflight)
    monkeypatch.setattr(eval_runner, "load_task_package", fake_load_task_package)
    monkeypatch.setattr(eval_runner, "require_dataset_role", fake_require_dataset_role)
    monkeypatch.setattr(eval_runner, "latest_frozen_index", lambda: index_path)
    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda *_: pytest.fail("core runs must not use the development qualifier"),
    )

    result = eval_runner.evaluate_suite(suite_path)

    assert preflight_calls == 1
    assert result["expected_runs"] == 96
    assert result["completed_runs"] == 96
    assert result["infrastructure_errors"] == 0
    assert len(result["runs"]) == 96
    assert len(starts) == 96
    assert result["qualification_errors"] == 0
    assert Path(result["execution_plan"]["path"]).is_file()
    assert {row["task_id"] for row in result["runs"]} == {
        f"task-{index}" for index in range(12)
    }
    assert {
        row["condition"] for row in result["runs"]
    } == {
        "no_memory",
        "raw_trace",
        "structured",
        "selective_structured",
    }
    assert {row["repetition"] for row in result["runs"]} == {1, 2}


def test_core_campaign_rejects_memory_index_from_another_dataset() -> None:
    suite = ExperimentSuite.model_validate(_core_suite_payload("sha256:" + ("a" * 64)))
    index_payload = {
        "entries": [{"memory_id": "mem_test"}],
        "embedding": {
            "implementation": "sentence-transformers",
            "revision": "test-revision",
        },
        "dataset_manifest_hash": "sha256:" + ("b" * 64),
    }

    with pytest.raises(ContractError, match="memory index dataset manifest hash"):
        eval_runner._validate_memory_index(index_payload, suite)


def test_infrastructure_outcome_halts_and_preserves_not_started_ledger(
    tmp_path: Path,
    monkeypatch,
) -> None:
    suite_path = tmp_path / "offline-two-task.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "experiment-v2",
                "experiment_id": "offline-infrastructure-halt",
                "purpose": "offline-smoke",
                "tasks": [
                    "tasks/smoke/csv-quoted-newline/public.yaml",
                    "tasks/smoke/config-falsy-override/public.yaml",
                ],
                "conditions": ["no_memory"],
                "repetitions": 1,
                "model": "mock",
                "model_id": "mock-v1",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    captured_manifests = []

    class FakeRunner:
        def start(self, _task, *, manifest, **_):
            captured_manifests.append(manifest)
            return {
                "run_id": manifest.run_id,
                "outcome_kind": "infrastructure_error",
                "terminal_error": {
                    "type": "ProviderUnavailable",
                    "message": "synthetic provider failure",
                },
                "usage": {
                    "model_cost_usd": 0.125,
                    "model_calls": 1,
                    "tool_calls": 0,
                    "input_tokens": 50,
                    "output_tokens": 0,
                },
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        lambda *_: pytest.fail("offline smoke must not use the development qualifier"),
    )

    result = eval_runner.evaluate_suite(suite_path)

    assert len(captured_manifests) == 1
    assert captured_manifests[0].experiment is not None
    assert captured_manifests[0].experiment.execution_hash == result["execution_hash"]
    assert result["actual_model_cost_usd"] == 0.125
    assert result["infrastructure_errors"] == 1
    assert result["not_started_runs"] == 1
    assert len(result["runs"]) == 2
    assert result["runs"][0]["run_id"] == captured_manifests[0].run_id
    assert result["runs"][0]["usage"]["model_calls"] == 1
    assert result["runs"][1]["attempt_status"] == "not_started"
    assert result["runs"][1]["run_id"] is None
    assert result["runs"][1]["not_started_reason"]["type"] == "InfrastructureFailureHalt"
