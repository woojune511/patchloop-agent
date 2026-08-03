from __future__ import annotations

from pathlib import Path

import pytest

from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from tests.test_d087_cost_runner import SUITE_PATH, _ready_environment


def test_d088_consumed_d087_is_hard_immutable_without_local_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS",
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
        | eval_runner.CONSUMED_CONDITION_NEUTRAL_ACCRUED_CAP_EXPERIMENT_IDS,
    )

    experiment_id = (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID
    )
    assert {experiment_id} == (
        eval_runner.CONSUMED_CONDITION_NEUTRAL_ACCRUED_CAP_EXPERIMENT_IDS
    )
    assert experiment_id in eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
    assert experiment_id not in eval_runner.CONSUMED_CURRENT_LIVE_EXPERIMENT_IDS
    assert experiment_id not in eval_runner.SINGLE_TASK_LIVE_EXPERIMENT_IDS

    unapproved = eval_runner.preflight_suite(SUITE_PATH)
    blocker_codes = {row["code"] for row in unapproved["blockers"]}
    assert "HISTORICAL_SUITE_IMMUTABLE" in blocker_codes
    assert "LIVE_COST_NOT_APPROVED" in blocker_codes
    assert "APPROVAL_HASH_MISMATCH" in blocker_codes
    assert "EXPERIMENT_RESULT_EXISTS" not in blocker_codes
    assert "EXPERIMENT_JOURNAL_EXISTS" not in blocker_codes

    class ForbiddenRunner:
        def __init__(self) -> None:
            pytest.fail("hard-consumed D-087 must stop before runner construction")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="preflight failed"):
        eval_runner.evaluate_suite(
            SUITE_PATH,
            approve_live_cost=True,
            approved_execution_hash=unapproved["execution_hash"],
        )

    runtime = tmp_path / "runtime"
    result_path = runtime / "experiments" / f"{experiment_id}.json"
    journal_path = (
        runtime / "experiments" / "journals" / f"{experiment_id}.jsonl"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("{}", encoding="utf-8")
    journal_path.write_text("{}\n", encoding="utf-8")

    with_artifacts = eval_runner.preflight_suite(SUITE_PATH)
    artifact_codes = {row["code"] for row in with_artifacts["blockers"]}
    assert "HISTORICAL_SUITE_IMMUTABLE" in artifact_codes
    assert "EXPERIMENT_RESULT_EXISTS" in artifact_codes
    assert "EXPERIMENT_JOURNAL_EXISTS" in artifact_codes
