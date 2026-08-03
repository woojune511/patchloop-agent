from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent.model import SYSTEM_PROMPT_V3
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
    Budget,
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunEvent,
)
from patchloop.evals import qualification as qualification_module
from patchloop.evals import runner as eval_runner
from patchloop.evals.qualification import qualify_run
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from tests import test_trace_qualification as trace_fixtures

PILOT_SUITE_PATH = Path(
    "experiments/dev-validation-condition-neutral-v2v5-pilot-20260803-r1.yaml"
)
PILOT_TASK_PATH = Path(
    "tasks/dev-validation/babel-strict-grouped-decimal-trailing-zeroes"
)
PILOT_TASK_ID = "babel-strict-grouped-decimal-trailing-zeroes"
FROZEN_BUDGET = Budget(
    max_model_calls=None,
    max_tool_calls=None,
    max_total_tokens=1_600_000,
    wall_clock_timeout_seconds=1_800,
)


def _pilot_manifest(*, run_id: str = "run_d085_qualification"):
    package = load_task_package(PILOT_TASK_PATH)
    suite = eval_runner.load_suite(PILOT_SUITE_PATH)
    return build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id=suite.model_id,
        memory_condition=MemoryCondition.NO_MEMORY,
        sandbox_backend="docker",
        transport_max_retries=0,
        max_output_tokens=suite.max_output_tokens,
        budget=suite.budget,
        agent_image_digest=package.environment.image_digest,
        evaluator_image_digest=package.environment.image_digest,
        input_price_per_million_usd=suite.input_price_per_million_usd,
        cached_input_price_per_million_usd=(
            suite.cached_input_price_per_million_usd
        ),
        cache_write_input_price_per_million_usd=(
            suite.cache_write_input_price_per_million_usd
        ),
        output_price_per_million_usd=suite.output_price_per_million_usd,
        experiment_context=ExperimentRunContext(
            experiment_id=CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
            purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash="sha256:" + ("b" * 64),
            dataset_manifest_hash="sha256:" + ("c" * 64),
            dataset_role=DatasetRole.DEVELOPMENT_VALIDATION,
            schedule_seed=20260723,
            schedule_order=1,
            schedule_row_id="sha256:" + ("d" * 64),
            repetition=1,
        ),
    )


def _runtime_event(
    tmp_path: Path,
    manifest,
    *,
    document_mutation: tuple[str, Any] | None = None,
) -> RunEvent:
    document = AgentRunner._generic_baseline_runtime_evidence_document(
        manifest=manifest,
        system_prompt=SYSTEM_PROMPT_V3,
        tool_schemas=TOOL_SCHEMAS_V2,
    )
    assert isinstance(document, dict)
    if document_mutation is not None:
        field, value = document_mutation
        document[field] = value
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(document)
    return RunEvent(
        event_id="evt_d085_runtime",
        run_id=manifest.run_id,
        sequence=1,
        type=EventType.RUN_STARTED,
        timestamp=datetime.now(UTC),
        actor="runner",
        payload={
            "task_id": manifest.task_id,
            "artifact_role": "runtime-contract",
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
            "runtime_contract_artifact": artifact.model_dump(mode="json"),
        },
    )


def _terminal_pilot_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    pricing_verified_at: datetime | None = None,
):
    suite = eval_runner.load_suite(PILOT_SUITE_PATH).model_copy(
        update={
            "pricing_verified_at": (
                pricing_verified_at or datetime.now(UTC)
            )
        }
    )
    purpose_members = dict(ExperimentPurpose.__members__)
    purpose_members["GENERIC_BASELINE_READINESS"] = (
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
    )
    fixture_purpose = type("D085FixturePurpose", (), purpose_members)
    monkeypatch.setattr(trace_fixtures, "ExperimentPurpose", fixture_purpose)
    monkeypatch.setattr(
        trace_fixtures.eval_runner,
        "load_suite",
        lambda _path: suite,
    )
    return trace_fixtures._terminal_trace(
        tmp_path,
        task_dir=PILOT_TASK_PATH,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        role=DatasetRole.DEVELOPMENT_VALIDATION,
        resolved=False,
        prompt_telemetry=True,
        budget=FROZEN_BUDGET,
        max_output_tokens=25_000,
        experiment_id=CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
    )


def _checks(qualification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {check["check_id"]: check for check in qualification["checks"]}


def test_d085_exact_suite_and_manifest_select_comparison_qualification() -> None:
    suite = eval_runner.load_suite(PILOT_SUITE_PATH)
    manifest = _pilot_manifest()

    assert qualification_module._condition_neutral_comparison_suite_matches(suite)
    assert qualification_module._condition_neutral_comparison_manifest_matches(
        manifest
    )
    assert suite.experiment_id == CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
    assert manifest.task_id == PILOT_TASK_ID


@pytest.mark.parametrize(
    "mutation",
    [
        "experiment_id",
        "task_id",
        "memory_condition",
        "budget",
    ],
)
def test_d085_manifest_selector_rejects_near_match_and_historical_profiles(
    mutation: str,
) -> None:
    manifest = _pilot_manifest()
    assert manifest.experiment is not None
    if mutation == "experiment_id":
        manifest = manifest.model_copy(
            update={
                "experiment": manifest.experiment.model_copy(
                    update={"experiment_id": "historical-live-pilot"}
                )
            }
        )
    elif mutation == "task_id":
        manifest = manifest.model_copy(update={"task_id": "forged-task"})
    elif mutation == "memory_condition":
        manifest = manifest.model_copy(
            update={
                "memory": manifest.memory.model_copy(
                    update={"condition": MemoryCondition.RAW_TRACE}
                )
            }
        )
    else:
        manifest = manifest.model_copy(
            update={
                "budget": FROZEN_BUDGET.model_copy(
                    update={"max_total_tokens": 1_599_999}
                )
            }
        )

    assert not qualification_module._condition_neutral_comparison_manifest_matches(
        manifest
    )


def test_d085_runtime_cas_binds_exact_pilot_profile(tmp_path: Path) -> None:
    manifest = _pilot_manifest()
    event = _runtime_event(tmp_path, manifest)

    passed, details = (
        qualification_module._generic_baseline_runtime_contract_evidence(
            root=tmp_path,
            manifest=manifest,
            events=[event],
        )
    )

    assert passed is True, details
    assert details["purpose"] == (
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value
    )
    assert details["memory_condition"] == MemoryCondition.NO_MEMORY.value
    assert details["comparison_budget_policy_artifact_valid"] is True


def test_d085_runtime_cas_rejects_semantic_relabeling(tmp_path: Path) -> None:
    manifest = _pilot_manifest()
    event = _runtime_event(
        tmp_path,
        manifest,
        document_mutation=("purpose", ExperimentPurpose.CORE.value),
    )

    passed, details = (
        qualification_module._generic_baseline_runtime_contract_evidence(
            root=tmp_path,
            manifest=manifest,
            events=[event],
        )
    )

    assert passed is False
    assert details["cas_integrity_valid"] is True
    assert details["semantic_contract_valid"] is False


def test_d085_terminal_task_failure_qualifies_process_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id, result, _ = _terminal_pilot_trace(tmp_path, monkeypatch)

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK_PATH,
        root=tmp_path,
        persist=False,
    )
    checks = _checks(qualification)

    assert result.outcome_kind.value == "task_failure"
    assert qualification["qualified"] is True, [
        check for check in qualification["checks"] if not check["passed"]
    ]
    assert qualification["evaluation_reached"] is True
    assert qualification["experiment_id"] == (
        CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
    )
    assert checks["approved_execution_plan"]["passed"] is True
    assert checks["comparison_runtime_contract"]["passed"] is True
    assert checks["disabled_call_guard_contract"]["passed"] is True
    assert checks["pricing_start_freshness"]["passed"] is True


def test_d085_terminal_qualification_rejects_runtime_cas_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id, _, _ = _terminal_pilot_trace(tmp_path, monkeypatch)
    state = StateStore(tmp_path / "state.sqlite3")
    run_started = next(
        event
        for event in state.list_events(run_id)
        if event.type == EventType.RUN_STARTED
    )
    Path(run_started.payload["artifact_path"]).write_bytes(b"{}")

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK_PATH,
        root=tmp_path,
        persist=False,
    )
    checks = _checks(qualification)

    assert qualification["qualified"] is False
    assert checks["comparison_runtime_contract"]["passed"] is False
    assert checks["comparison_runtime_contract"]["details"][
        "cas_integrity_valid"
    ] is False
    assert checks["disabled_call_guard_contract"]["passed"] is False


def test_d085_terminal_qualification_rejects_execution_plan_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id, _, _ = _terminal_pilot_trace(tmp_path, monkeypatch)
    manifest = StateStore(tmp_path / "state.sqlite3").get_manifest(run_id)
    assert manifest.experiment is not None
    plan_path = qualification_module._execution_plan_path(
        tmp_path,
        manifest.experiment.execution_hash,
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["runtime_contract"]["call_guard_policy"] = "forged-policy"
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK_PATH,
        root=tmp_path,
        persist=False,
    )
    checks = _checks(qualification)

    assert qualification["qualified"] is False
    assert checks["approved_execution_plan"]["passed"] is False
    assert checks["comparison_runtime_contract"]["passed"] is True
    assert checks["pricing_start_freshness"]["passed"] is False

def test_d085_terminal_qualification_rejects_stale_start_pricing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id, _, _ = _terminal_pilot_trace(
        tmp_path,
        monkeypatch,
        pricing_verified_at=datetime.now(UTC) - timedelta(days=10),
    )

    qualification = qualify_run(
        run_id,
        task_dir=PILOT_TASK_PATH,
        root=tmp_path,
        persist=False,
    )
    checks = _checks(qualification)

    assert qualification["qualified"] is False
    assert checks["approved_execution_plan"]["passed"] is True
    assert checks["comparison_runtime_contract"]["passed"] is True
    assert checks["disabled_call_guard_contract"]["passed"] is True
    assert checks["pricing_start_freshness"]["passed"] is False
