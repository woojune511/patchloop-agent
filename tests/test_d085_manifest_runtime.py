from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from patchloop.agent import runner as agent_runner_module
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
    Artifact,
    Budget,
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
    TaskPackage,
)
from patchloop.errors import RecoveryError
from patchloop.evals import qualification as trace_qualification
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json

PILOT_TASK = Path(
    "tasks/dev-validation/"
    "babel-strict-grouped-decimal-trailing-zeroes/public.yaml"
)
SMOKE_TASK = Path("tasks/smoke/csv-quoted-newline")
PILOT_TASK_ID = "babel-strict-grouped-decimal-trailing-zeroes"
FROZEN_BUDGET = Budget(
    max_model_calls=None,
    max_tool_calls=None,
    max_total_tokens=1_600_000,
    wall_clock_timeout_seconds=1_800,
)


def _experiment_context(
    *,
    experiment_id: str = CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
) -> ExperimentRunContext:
    return ExperimentRunContext(
        experiment_id=experiment_id,
        purpose=ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT,
        suite_hash="sha256:" + ("a" * 64),
        execution_hash="sha256:" + ("b" * 64),
        dataset_manifest_hash="sha256:" + ("c" * 64),
        dataset_role=DatasetRole.DEVELOPMENT_VALIDATION,
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id="sha256:" + ("d" * 64),
        repetition=1,
    )


def _pilot_manifest(
    *,
    package: TaskPackage | None = None,
    run_id: str = "run_d085_pilot",
) -> RunManifest:
    selected_package = package or load_task_package(PILOT_TASK.parent)
    return build_manifest(
        selected_package,
        run_id=run_id,
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        memory_condition=MemoryCondition.NO_MEMORY,
        sandbox_backend="local",
        budget=FROZEN_BUDGET,
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        experiment_context=_experiment_context(),
    )


def _smoke_backed_pilot_package() -> TaskPackage:
    """Use the local smoke snapshot while retaining the exact pilot identity."""

    package = load_task_package(SMOKE_TASK)
    public = package.public.model_copy(
        update={
            "task_id": PILOT_TASK_ID,
            "split": "dev-validation",
        }
    )
    private = package.private.model_copy(update={"task_id": PILOT_TASK_ID})
    return package.model_copy(update={"public": public, "private": private})


def test_d085_exports_one_exact_pilot_identity() -> None:
    assert CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID == (
        "dev-validation-condition-neutral-v2v5-pilot-20260803-r1"
    )


def test_d085_exact_pilot_manifest_accepts_nullable_call_limits() -> None:
    manifest = _pilot_manifest()

    assert manifest.experiment is not None
    assert manifest.experiment.experiment_id == (
        CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
    )
    assert (
        manifest.experiment.purpose
        == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
    )
    assert manifest.task_id == PILOT_TASK_ID
    assert manifest.memory.condition == MemoryCondition.NO_MEMORY
    assert manifest.budget == FROZEN_BUDGET
    assert AgentRunner._is_frozen_comparison_runtime_manifest(manifest)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("experiment", "experiment_id"), "arbitrary-live-pilot"),
        (("task_id",), "moto-query-scanned-count"),
        (("experiment", "dataset_role"), DatasetRole.MEMORY_DEVELOPMENT.value),
        (("experiment", "schedule_order"), 2),
        (("experiment", "repetition"), 2),
        (("model", "transport_max_retries"), None),
        (("budget", "max_tool_calls"), 100),
        (("budget", "max_total_tokens"), 1_599_999),
        (("memory", "condition"), MemoryCondition.RAW_TRACE.value),
    ],
)
def test_d085_nullable_pilot_rejects_identity_and_tuple_drift(
    path: tuple[str, ...],
    replacement: object,
) -> None:
    payload = _pilot_manifest().model_dump(mode="json")
    target = payload
    for key in path[:-1]:
        child = target[key]
        assert isinstance(child, dict)
        target = child
    target[path[-1]] = replacement

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)


def test_d085_finite_historical_live_pilot_manifest_is_unchanged() -> None:
    payload = _pilot_manifest().model_dump(mode="json")
    payload["experiment"]["experiment_id"] = "historical-finite-pilot"
    payload["model"]["transport_max_retries"] = None
    payload["budget"] = {
        "max_model_calls": 40,
        "max_tool_calls": 100,
        "max_total_tokens": 600_000,
        "wall_clock_timeout_seconds": 1_800,
    }

    historical = RunManifest.model_validate(payload)

    assert historical.budget.max_model_calls == 40
    assert historical.budget.max_tool_calls == 100
    assert not AgentRunner._is_frozen_comparison_runtime_manifest(historical)


def test_d085_pilot_uses_d084_runtime_evidence_document() -> None:
    manifest = _pilot_manifest()
    system_prompt, tools = AgentRunner._runtime_contract(manifest)

    document = AgentRunner._generic_baseline_runtime_evidence_document(
        manifest=manifest,
        system_prompt=system_prompt,
        tool_schemas=tools,
    )

    assert document is not None
    assert document["schema_version"] == (
        "condition-neutral-comparison-runtime-evidence-v1"
    )
    assert document["purpose"] == (
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value
    )
    assert document["memory_condition"] == MemoryCondition.NO_MEMORY.value
    assert document["budget"] == FROZEN_BUDGET.model_dump(mode="json")
    assert document["call_guard_policy"] == (
        "model-tool-observability-only-v1"
    )
    assert document["comparison_budget_policy"]["content_hash"] == (
        "sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88"
    )


def test_d085_paid_boundary_routes_only_exact_pilot_through_plan_matcher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _pilot_manifest(run_id="run_d085_paid_boundary")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        canonical_json(
            {
                "runtime_contract": {
                    "schema_version": (
                        "condition-neutral-comparison-runtime-contract-v1"
                    )
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def plan_matches(*, plan, manifest):
        assert plan["runtime_contract"]["schema_version"] == (
            "condition-neutral-comparison-runtime-contract-v1"
        )
        calls.append(manifest.run_id)
        return True

    monkeypatch.setattr(
        trace_qualification,
        "_execution_plan_matches",
        plan_matches,
    )
    authorization = SimpleNamespace(plan_path=str(plan_path))

    assert AgentRunner._live_plan_matches_manifest(manifest, authorization)
    assert calls == [manifest.run_id]

    arbitrary_experiment = manifest.experiment.model_copy(
        update={"experiment_id": "arbitrary-live-pilot"}
    )
    arbitrary = manifest.model_copy(update={"experiment": arbitrary_experiment})
    assert not AgentRunner._live_plan_matches_manifest(arbitrary, authorization)
    assert calls == [manifest.run_id]


def test_d085_fresh_start_persists_and_resume_revalidates_runtime_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _smoke_backed_pilot_package()
    manifest = _pilot_manifest(
        package=package,
        run_id="run_d085_start_resume",
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        agent_runner_module,
        "load_task_package",
        lambda _path: package,
    )
    monkeypatch.setattr(
        AgentRunner,
        "_require_live_authorization",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner,
        "_transition",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SystemExit("stop after RunStarted")
        ),
    )

    with pytest.raises(SystemExit, match="stop after RunStarted"):
        runner.start(SMOKE_TASK, model="openai", manifest=manifest)

    started = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.RUN_STARTED
    ]
    assert len(started) == 1
    artifact = Artifact.model_validate(
        started[0].payload["runtime_contract_artifact"]
    )
    evidence = json.loads(
        runner.artifacts.read_bytes(artifact).decode("utf-8")
    )
    assert evidence["schema_version"] == (
        "condition-neutral-comparison-runtime-evidence-v1"
    )
    assert evidence["purpose"] == (
        ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value
    )

    monkeypatch.setattr(runner.artifacts, "read_bytes", lambda _artifact: b"{}")
    with pytest.raises(RecoveryError, match="runtime contract artifact"):
        runner.resume(manifest.run_id)
