from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import (
    CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
    ExperimentPurpose,
    RunManifest,
)
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.evals.budget import calculate_budget_pressure
from tests.test_d085_condition_neutral_pilot_preflight import (
    SUITE_PATH,
    _ready_environment,
)
from tests.test_d085_manifest_runtime import _pilot_manifest


def _replace(payload: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    target = payload
    for key in path[:-1]:
        child = target[key]
        assert isinstance(child, dict)
        target = child
    target[path[-1]] = value


def test_d086_exact_d085_profile_produces_budget_pressure() -> None:
    manifest = _pilot_manifest(run_id="run_d086_budget_pressure")
    diagnostic = calculate_budget_pressure(
        manifest,
        [],
        {
            "run_id": manifest.run_id,
            "usage": {
                "input_tokens": 69_701,
                "output_tokens": 3_500,
                "model_calls": 8,
                "tool_calls": 9,
                "wall_clock_ms": 50_769,
            },
        },
    )

    assert diagnostic["schema_version"] == "budget-pressure-v1"
    assert diagnostic["configured_limits"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 1_600_000,
        "wall_clock_ms": 1_800_000,
    }
    assert diagnostic["observed_usage"] == {
        "input_tokens": 69_701,
        "output_tokens": 3_500,
        "total_tokens": 73_201,
        "model_calls": 8,
        "tool_calls": 9,
        "wall_clock_ms": 50_769,
    }
    assert diagnostic["headroom"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 1_526_799,
        "wall_clock_ms": 1_749_231,
    }
    assert diagnostic["binding_dimension"] == "none"
    assert diagnostic["binding_reason"] is None


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment", "experiment_id"), "d085-near-match"),
        (("task_id",), "moto-query-scanned-count"),
        (("experiment", "dataset_role"), "memory-development"),
        (("experiment", "schedule_seed"), 20260724),
        (("experiment", "schedule_order"), 2),
        (("experiment", "repetition"), 2),
        (("model", "max_output_tokens"), 24_999),
        (("memory", "max_context_tokens"), 1_999),
        (("tool_schema_version",), "v1"),
        (("context_policy_version",), "phase-evidence-v4"),
        (("budget", "max_model_calls"), 1),
        (("budget", "max_tool_calls"), 1),
        (("budget", "max_total_tokens"), 1_599_999),
    ],
)
def test_d086_budget_pressure_rejects_d085_near_matches(
    path: tuple[str, ...],
    replacement: Any,
) -> None:
    payload = _pilot_manifest().model_dump(mode="json")
    _replace(payload, path, replacement)

    with pytest.raises(ValueError):
        calculate_budget_pressure(payload, [])


def test_d086_d085_id_cannot_escape_through_future_comparison_purpose() -> None:
    payload = _pilot_manifest().model_dump(mode="json")
    payload["experiment"]["purpose"] = (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY.value
    )
    # This is otherwise a structurally valid future-comparison manifest. The
    # consumed D-085 ID must still retain its exact pilot semantics.
    near_match = RunManifest.model_validate(payload)

    with pytest.raises(ValueError, match="D-085 condition-neutral"):
        calculate_budget_pressure(near_match, [])


def test_d086_consumed_d085_is_hard_immutable_with_or_without_local_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)

    unapproved = eval_runner.preflight_suite(SUITE_PATH)
    blocker_codes = {row["code"] for row in unapproved["blockers"]}

    assert {
        CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
    } == eval_runner.CONSUMED_CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_IDS
    assert (
        CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
        in eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
    )
    assert blocker_codes == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }
    assert "EXPERIMENT_RESULT_EXISTS" not in blocker_codes
    assert "EXPERIMENT_JOURNAL_EXISTS" not in blocker_codes

    class ForbiddenRunner:
        def __init__(self) -> None:
            pytest.fail("consumed D-085 must be blocked before runner construction")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="preflight failed"):
        eval_runner.evaluate_suite(
            SUITE_PATH,
            approve_live_cost=True,
            approved_execution_hash=unapproved["execution_hash"],
        )

    output = (
        tmp_path
        / "runtime"
        / "experiments"
        / f"{CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID}.json"
    )
    journal = (
        tmp_path
        / "runtime"
        / "experiments"
        / "journals"
        / f"{CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID}.jsonl"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    journal.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("{}", encoding="utf-8")
    journal.write_text("{}\n", encoding="utf-8")

    with_artifacts = eval_runner.preflight_suite(SUITE_PATH)
    with_artifact_codes = {
        row["code"] for row in with_artifacts["blockers"]
    }
    assert "HISTORICAL_SUITE_IMMUTABLE" in with_artifact_codes
    assert "EXPERIMENT_RESULT_EXISTS" in with_artifact_codes
    assert "EXPERIMENT_JOURNAL_EXISTS" in with_artifact_codes
