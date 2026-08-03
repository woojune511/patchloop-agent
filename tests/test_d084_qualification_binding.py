from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from patchloop.agent.model import SYSTEM_PROMPT_V3
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V2
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
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
from patchloop.evals.budget import calculate_budget_pressure
from patchloop.evals.qualification import qualify_run
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from tests import test_trace_qualification as trace_fixtures
from tests.test_experiments import _ready_live_environment

FROZEN_BUDGET = Budget(
    max_model_calls=None,
    max_tool_calls=None,
    max_total_tokens=1_600_000,
    wall_clock_timeout_seconds=1_800,
)
POLICY_BINDING = {
    "schema_version": "condition-neutral-comparison-budget-freeze-v1",
    "profile_id": "gpt54mini-v2v5-condition-neutral-1600k-v1",
    "path": (
        "reports/live-pilot/artifacts/"
        "d083-condition-neutral-comparison-budget-freeze.json"
    ),
    "content_hash": (
        "sha256:e01c5f0107592e1c29c1ec8264f32bf05c979a718c353c37acb0d87fafd2cb88"
    ),
}
TASK_PATH = Path("tasks/dev-train/loguru-invalid-format-feedback")


def _comparison_terminal_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[str, Any, str]:
    """Reuse the terminal fixture while selecting the new comparison lane.

    The historical fixture treats generic-readiness rows as the complete V2/V5
    trace shape.  This proxy redirects only that fixture-local branch to the
    exact D-084 memory-development purpose; production enums are unchanged.
    """

    suite = eval_runner.load_suite(
        "experiments/dev-no-memory-v5.template.yaml"
    )
    suite = suite.model_copy(
        update={"pricing_verified_at": datetime.now(UTC)}
    )
    purpose_members = dict(ExperimentPurpose.__members__)
    purpose_members["GENERIC_BASELINE_READINESS"] = (
        ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
    )
    fixture_purpose = type("D084FixturePurpose", (), purpose_members)
    monkeypatch.setattr(
        trace_fixtures,
        "ExperimentPurpose",
        fixture_purpose,
    )
    monkeypatch.setattr(
        trace_fixtures.eval_runner,
        "load_suite",
        lambda _path: suite,
    )
    # D-083 deliberately keeps the source template blocked by its old $20
    # authorization cap. Isolate trace qualification from that separate live
    # authority decision; the production pricing-freshness check remains real.
    monkeypatch.setattr(
        trace_fixtures.eval_runner,
        "_pricing_contract_matches",
        lambda *_args, **_kwargs: True,
    )
    return trace_fixtures._terminal_trace(
        tmp_path,
        task_dir=TASK_PATH,
        purpose=ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
        role=DatasetRole.MEMORY_DEVELOPMENT,
        resolved=False,
        prompt_telemetry=True,
        budget=FROZEN_BUDGET,
        max_output_tokens=25_000,
        experiment_id=suite.experiment_id,
    )


def _manifest(
    *,
    purpose: ExperimentPurpose = ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
    condition: MemoryCondition = MemoryCondition.NO_MEMORY,
    run_id: str = "run_d084_qualification_binding",
):
    package = load_task_package(TASK_PATH)
    return build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        memory_condition=condition,
        sandbox_backend="docker",
        transport_max_retries=0,
        max_output_tokens=25_000,
        budget=FROZEN_BUDGET,
        agent_image_digest=package.environment.image_digest,
        evaluator_image_digest=package.environment.image_digest,
        experiment_context=ExperimentRunContext(
            experiment_id=f"d084-{purpose.value}-offline-binding",
            purpose=purpose,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash="sha256:" + ("b" * 64),
            dataset_manifest_hash="sha256:" + ("c" * 64),
            dataset_role=(
                DatasetRole.MEMORY_DEVELOPMENT
                if purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
                else DatasetRole.CORE_SAME_REPO
            ),
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
        event_id="evt_d084_runtime",
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


@pytest.mark.parametrize(
    ("purpose", "condition"),
    [
        (
            ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
            MemoryCondition.NO_MEMORY,
        ),
        *[
            (ExperimentPurpose.CORE, condition)
            for condition in MemoryCondition
        ],
    ],
)
def test_d084_runtime_evidence_binds_exact_profile_for_each_supported_condition(
    tmp_path: Path,
    purpose: ExperimentPurpose,
    condition: MemoryCondition,
) -> None:
    manifest = _manifest(
        purpose=purpose,
        condition=condition,
        run_id=f"run_d084_{purpose.value}_{condition.value}",
    )
    event = _runtime_event(tmp_path, manifest)

    passed, details = (
        qualification_module._generic_baseline_runtime_contract_evidence(
            root=tmp_path,
            manifest=manifest,
            events=[event],
        )
    )

    assert passed is True, details
    assert details["comparison_budget_policy"] == POLICY_BINDING
    assert details["comparison_budget_policy_artifact_valid"] is True
    assert details["purpose"] == purpose.value
    assert details["memory_condition"] == condition.value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "budget",
            {
                "max_model_calls": None,
                "max_tool_calls": None,
                "max_total_tokens": 1_599_999,
                "wall_clock_timeout_seconds": 1_800,
            },
        ),
        ("memory_max_context_tokens", 1_999),
        (
            "comparison_budget_policy",
            {**POLICY_BINDING, "profile_id": "forged-profile"},
        ),
        ("purpose", ExperimentPurpose.CORE.value),
        ("memory_condition", MemoryCondition.RAW_TRACE.value),
    ],
)
def test_d084_runtime_evidence_rejects_semantic_cas_relabeling(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    manifest = _manifest()
    event = _runtime_event(
        tmp_path,
        manifest,
        document_mutation=(field, value),
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


def test_d084_no_memory_terminal_trace_requires_all_comparison_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id, result, _ = _comparison_terminal_trace(tmp_path, monkeypatch)

    qualification = qualify_run(
        run_id,
        task_dir=TASK_PATH,
        root=tmp_path,
        persist=False,
    )
    checks = {
        check["check_id"]: check for check in qualification["checks"]
    }

    assert result.official is True
    assert qualification["qualified"] is True, [
        check for check in qualification["checks"] if not check["passed"]
    ]
    assert checks["comparison_runtime_contract"]["passed"] is True
    assert checks["disabled_call_guard_contract"]["passed"] is True
    assert checks["pricing_start_freshness"]["passed"] is True


def test_d084_no_memory_terminal_trace_rejects_runtime_cas_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id, _, _ = _comparison_terminal_trace(tmp_path, monkeypatch)
    state = StateStore(tmp_path / "state.sqlite3")
    run_started = next(
        event
        for event in state.list_events(run_id)
        if event.type == EventType.RUN_STARTED
    )
    Path(run_started.payload["artifact_path"]).write_bytes(b"{}")

    qualification = qualify_run(
        run_id,
        task_dir=TASK_PATH,
        root=tmp_path,
        persist=False,
    )
    checks = {
        check["check_id"]: check for check in qualification["checks"]
    }

    assert qualification["qualified"] is False
    assert checks["comparison_runtime_contract"]["passed"] is False
    assert checks["comparison_runtime_contract"]["details"][
        "cas_integrity_valid"
    ] is False


def test_d084_budget_diagnostic_treats_counts_as_observations_only() -> None:
    manifest = _manifest()
    diagnostic = calculate_budget_pressure(
        manifest,
        [],
        {
            "run_id": manifest.run_id,
            "usage": {
                "input_tokens": 1_200_000,
                "output_tokens": 100_000,
                "model_calls": 10_000,
                "tool_calls": 20_000,
                "wall_clock_ms": 1_700_000,
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
    assert diagnostic["headroom"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 300_000,
        "wall_clock_ms": 100_000,
    }


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("budget", "max_total_tokens"), 1_599_999),
        (("budget", "max_model_calls"), 100),
        (("model", "transport_max_retries"), 1),
        (("model", "max_output_tokens"), 24_999),
        (("memory", "max_context_tokens"), 1_999),
        (("context_policy_version",), "phase-evidence-v4"),
        (("fault", "type"), "context-reset"),
    ],
)
def test_d084_budget_diagnostic_rejects_near_match_profiles(
    path: tuple[str, ...],
    replacement: Any,
) -> None:
    payload = _manifest().model_dump(mode="json")
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValueError, match="condition-neutral comparison"):
        calculate_budget_pressure(payload, [])


def test_d084_execution_plan_reconstructs_full_schedule_and_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ready_live_environment(monkeypatch, tmp_path)
    plan = eval_runner.preflight_suite(
        "experiments/dev-no-memory-v5.template.yaml"
    )
    plan["ready"] = True
    plan["blockers"] = []
    plan["approval"] = {
        "invocation_approve_live_cost": True,
        "invocation_approved_execution_hash": plan["execution_hash"],
        "matches_execution_hash": True,
    }
    monkeypatch.setattr(
        eval_runner,
        "_pricing_contract_matches",
        lambda *_args, **_kwargs: True,
    )
    persisted = eval_runner._persist_preflight_plan(plan)
    plan = json.loads(Path(persisted["path"]).read_text(encoding="utf-8"))
    row = plan["schedule"][0]
    task = next(
        item for item in plan["tasks"] if item["task_id"] == row["task_id"]
    )
    package = load_task_package(Path(task["task"]).parent)
    suite = eval_runner.ExperimentSuite.model_validate(plan["suite"])
    manifest = build_manifest(
        package,
        run_id="run_d084_plan_binding",
        provider="openai",
        model_id=suite.model_id,
        sandbox_backend="docker",
        transport_max_retries=0,
        max_output_tokens=suite.max_output_tokens,
        budget=suite.budget,
        agent_image_digest=task["evaluator_image_digest"],
        evaluator_image_digest=task["evaluator_image_digest"],
        input_price_per_million_usd=suite.input_price_per_million_usd,
        cached_input_price_per_million_usd=(
            suite.cached_input_price_per_million_usd
        ),
        cache_write_input_price_per_million_usd=(
            suite.cache_write_input_price_per_million_usd
        ),
        output_price_per_million_usd=suite.output_price_per_million_usd,
        experiment_context=ExperimentRunContext(
            experiment_id=suite.experiment_id,
            purpose=suite.purpose,
            suite_hash=plan["suite_hash"],
            execution_hash=plan["execution_hash"],
            dataset_manifest_hash=plan["dataset"]["manifest_hash"],
            dataset_role=DatasetRole(row["dataset_role"]),
            schedule_seed=suite.seed,
            schedule_order=row["order"],
            schedule_row_id=row["schedule_row_id"],
            repetition=row["repetition"],
        ),
    )
    manifest.harness_git_commit = plan["environment"]["git"]["commit"]

    assert qualification_module._execution_plan_matches(
        plan=plan,
        manifest=manifest,
    )

    policy_tamper = deepcopy(plan)
    policy_tamper["runtime_contract"]["comparison_budget_policy"][
        "profile_id"
    ] = "forged-profile"
    assert not qualification_module._execution_plan_matches(
        plan=policy_tamper,
        manifest=manifest,
    )

    schedule_tamper = deepcopy(plan)
    schedule_tamper["schedule"] = schedule_tamper["schedule"][:-1]
    assert not qualification_module._execution_plan_matches(
        plan=schedule_tamper,
        manifest=manifest,
    )
