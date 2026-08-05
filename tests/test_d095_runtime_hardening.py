from __future__ import annotations

from pathlib import Path

import pytest

from patchloop.contracts import GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from tests.test_d094_high_headroom_readiness import SUITE_PATH, _ready_environment


def test_d095_hard_consumes_d094_without_local_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _ready_environment(monkeypatch, tmp_path)

    assert GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID in (
        eval_runner.CONSUMED_GENERIC_BASELINE_READINESS_EXPERIMENT_IDS
    )
    assert GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID in (
        eval_runner.HISTORICAL_IMMUTABLE_LIVE_EXPERIMENT_IDS
    )
    assert GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID not in (
        eval_runner.SINGLE_TASK_LIVE_EXPERIMENT_IDS
    )

    preflight = eval_runner.preflight_suite(SUITE_PATH)
    blocker_codes = {row["code"] for row in preflight["blockers"]}
    assert blocker_codes == {
        "HISTORICAL_SUITE_IMMUTABLE",
        "LIVE_COST_NOT_APPROVED",
        "APPROVAL_HASH_MISMATCH",
    }

    class ForbiddenRunner:
        def __init__(self) -> None:
            pytest.fail("hard-consumed D-094 must stop before runner construction")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    with pytest.raises(ContractError, match="preflight failed"):
        eval_runner.evaluate_suite(
            SUITE_PATH,
            approve_live_cost=True,
            approved_execution_hash=preflight["execution_hash"],
        )

    runtime = tmp_path / "runtime"
    result_path = runtime / "experiments" / f"{GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID}.json"
    journal_path = (
        runtime
        / "experiments"
        / "journals"
        / f"{GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID}.jsonl"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("{}", encoding="utf-8")
    journal_path.write_text("{}\n", encoding="utf-8")

    with_local_artifacts = eval_runner.preflight_suite(SUITE_PATH)
    artifact_codes = {row["code"] for row in with_local_artifacts["blockers"]}
    assert "HISTORICAL_SUITE_IMMUTABLE" in artifact_codes
    assert "EXPERIMENT_RESULT_EXISTS" in artifact_codes
    assert "EXPERIMENT_JOURNAL_EXISTS" in artifact_codes
