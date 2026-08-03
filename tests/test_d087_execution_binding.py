from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import (
    AgentRunner,
    CampaignCostReservationAuthorization,
    LiveExecutionAuthorization,
    _campaign_reservation_consumption_path,
    issue_campaign_cost_reservation_authorization,
    issue_live_execution_authorization,
)
from patchloop.contracts import (
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
)
from patchloop.errors import ContractError
from patchloop.evals import qualification as qualification_module
from patchloop.evals import runner as eval_runner
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text
from tests import test_trace_qualification as trace_fixtures

SUITE_PATH = Path(
    "experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml"
)
CAMPAIGN_COMMIT = "a" * 40
PILOT_COMMIT = "b" * 40


def _synthetic_pilot_admission(
    run_id: str | None,
    suite: eval_runner.ExperimentSuite,
    *,
    campaign_harness_commit: str,
) -> dict[str, Any]:
    """Build a strict D-085 admission descriptor without replaying a live trace.

    D-085 admission is exercised exhaustively by its own tests.  This fixture
    keeps that contract structurally valid so this module can isolate D-087's
    new cost-control binding without provider, Docker, or historical-state I/O.
    """

    assert run_id == "run_c355405d826641b9"
    campaign_contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit=campaign_harness_commit,
    )
    assert campaign_contract is not None
    pilot_contract = {
        **campaign_contract,
        "purpose": ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value,
        "harness_git_commit": PILOT_COMMIT,
    }
    pilot_semantics = eval_runner._comparison_runtime_semantics(
        pilot_contract
    )
    descriptor = {
        "schema_version": (
            eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_ADMISSION_SCHEMA
        ),
        "pilot": {
            "run_id": run_id,
            "experiment_id": (
                eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
            ),
            "purpose": (
                ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT.value
            ),
            "task_path": eval_runner.PILOT_TASK,
            "task_id": eval_runner.PILOT_TASK_ID,
            "dataset_role": DatasetRole.DEVELOPMENT_VALIDATION.value,
            "memory_condition": MemoryCondition.NO_MEMORY.value,
            "schedule_seed": 20260723,
            "schedule_order": 1,
            "schedule_row_id": "sha256:" + ("1" * 64),
            "repetition": 1,
            "suite_hash": "sha256:" + ("2" * 64),
            "execution_hash": "sha256:" + ("3" * 64),
            "qualification_hash": "sha256:" + ("4" * 64),
            "source_evidence_hash": "sha256:" + ("5" * 64),
            "execution_plan_hash": "sha256:" + ("6" * 64),
            "runtime_contract_content_hash": "sha256:" + ("7" * 64),
            "outcome_kind": "resolved",
            "process_qualification": {
                "qualified": True,
                "trace_integrity_passed": True,
                "leakage_scan_passed": True,
                "evaluation_reached": True,
                "required_checks": list(
                    eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_REQUIRED_CHECKS
                ),
            },
        },
        "campaign": {
            "experiment_id": suite.experiment_id,
            "purpose": suite.purpose.value,
            "expected_runs": (
                len(suite.tasks) * len(suite.conditions) * suite.repetitions
            ),
            "conditions": [
                condition.value for condition in suite.conditions
            ],
            "repetitions": suite.repetitions,
        },
        "runtime_binding": {
            "pilot_harness_git_commit": PILOT_COMMIT,
            "campaign_harness_git_commit": campaign_harness_commit,
            "pilot_runtime_contract": pilot_contract,
            "pilot_runtime_contract_hash": sha256_text(
                canonical_json(pilot_contract)
            ),
            "campaign_runtime_contract_hash": sha256_text(
                canonical_json(campaign_contract)
            ),
            "semantic_runtime_contract_hash": sha256_text(
                canonical_json(pilot_semantics)
            ),
            "excluded_comparison_fields": list(
                eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_RUNTIME_EXCLUSIONS
            ),
        },
    }
    return {
        "schema_version": (
            eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_ADMISSION_SCHEMA
        ),
        "run_id": run_id,
        "admitted": True,
        "descriptor": descriptor,
        "pilot_admission_hash": sha256_text(canonical_json(descriptor)),
        "qualification_hash": descriptor["pilot"]["qualification_hash"],
        "source_evidence_hash": descriptor["pilot"][
            "source_evidence_hash"
        ],
        "reason": None,
    }


@pytest.fixture
def exact_plan_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any]:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-never-rendered")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {
            "available": True,
            "commit": CAMPAIGN_COMMIT,
            "clean": True,
        },
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
        lambda: datetime(2026, 8, 4, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        eval_runner,
        "runtime_root",
        lambda: tmp_path / "preflight-runtime",
    )
    monkeypatch.setattr(
        eval_runner,
        "_condition_neutral_comparison_pilot_admission",
        _synthetic_pilot_admission,
    )

    candidate = eval_runner.preflight_suite(SUITE_PATH)
    preflight = eval_runner.preflight_suite(
        SUITE_PATH,
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
    )
    assert preflight["ready"] is True, preflight["blockers"]
    assert preflight["campaign_cost_control"]["content_hash"].startswith(
        "sha256:"
    )
    plan = {**preflight, "schema_version": "experiment-execution-plan-v1"}

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
        run_id="run_d087_execution_binding",
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
            campaign_cost_control_hash=plan["campaign_cost_control"][
                "content_hash"
            ],
            dataset_manifest_hash=plan["dataset"]["manifest_hash"],
            dataset_role=DatasetRole(schedule_row["dataset_role"]),
            schedule_seed=suite.seed,
            schedule_order=schedule_row["order"],
            schedule_row_id=schedule_row["schedule_row_id"],
            repetition=schedule_row["repetition"],
        ),
    )
    manifest.harness_git_commit = CAMPAIGN_COMMIT
    manifest.model.provider_sdk_version = plan["environment"]["openai_sdk"][
        "version"
    ]
    return plan, suite, {**task_row, **schedule_row}, manifest


def _persist_plan_and_reserve(
    plan: dict[str, Any],
    manifest: Any,
) -> tuple[
    LiveExecutionAuthorization,
    CampaignCostReservationAuthorization,
    Path,
]:
    plan_path = (
        Path(plan["journal_path"]).parents[1]
        / "plans"
        / f"{plan['execution_hash'].removeprefix('sha256:')}.json"
    )
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    runtime = plan_path.parents[2]
    live_authorization = issue_live_execution_authorization(
        plan["execution_hash"],
        root=runtime,
    )
    journal_path = Path(plan["journal_path"])
    cost_control = plan["campaign_cost_control"]
    descriptor = cost_control["descriptor"]
    event_hash = eval_runner._append_campaign_event(
        journal_path,
        sequence=1,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": plan["experiment_id"],
            "execution_hash": plan["execution_hash"],
            "campaign_cost_control_hash": cost_control["content_hash"],
        },
    )
    reservation_event_hash = eval_runner._append_campaign_event(
        journal_path,
        sequence=2,
        previous_event_hash=event_hash,
        event_type="RunCostReserved",
        payload={
            "schedule_row_id": manifest.experiment.schedule_row_id,
            "run_id": manifest.run_id,
            "campaign_cost_control_hash": cost_control["content_hash"],
            "accrued_cost_nanos_before": 0,
            "held_reserve_nanos_after": descriptor[
                "per_run_reserve_nanos"
            ],
            "reserve_nanos": descriptor["per_run_reserve_nanos"],
            "cap_nanos": descriptor["hard_cap_nanos"],
        },
    )
    eval_runner._append_campaign_event(
        journal_path,
        sequence=3,
        previous_event_hash=reservation_event_hash,
        event_type="RunStarted",
        payload={
            "schedule_row_id": manifest.experiment.schedule_row_id,
            "run_id": manifest.run_id,
        },
    )
    reservation = issue_campaign_cost_reservation_authorization(
        manifest,
        live_authorization,
        journal_path=journal_path,
        reservation_event_hash=reservation_event_hash,
    )
    return live_authorization, reservation, journal_path


def test_d087_exact_plan_and_manifest_are_bound_at_both_consumers(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
) -> None:
    plan, suite, item, manifest = exact_plan_manifest

    eval_runner._assert_manifest_matches_preflight(
        manifest,
        suite=suite,
        preflight=plan,
        item=item,
    )
    assert qualification_module._execution_plan_matches(
        plan=plan,
        manifest=manifest,
    )


def test_d087_execution_plan_rejects_tampered_and_self_rehashed_cost_control(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
) -> None:
    plan, suite, item, manifest = exact_plan_manifest
    tampered = deepcopy(plan)
    descriptor = tampered["campaign_cost_control"]["descriptor"]
    descriptor["hard_cap_nanos"] -= 1

    assert not qualification_module._execution_plan_matches(
        plan=tampered,
        manifest=manifest,
    )

    rehashed = deepcopy(tampered)
    rehashed["campaign_cost_control"]["content_hash"] = sha256_text(
        canonical_json(rehashed["campaign_cost_control"]["descriptor"])
    )
    assert not qualification_module._execution_plan_matches(
        plan=rehashed,
        manifest=manifest,
    )
    with pytest.raises(ContractError, match="approved execution plan"):
        eval_runner._assert_manifest_matches_preflight(
            manifest,
            suite=suite,
            preflight=rehashed,
            item=item,
        )


@pytest.mark.parametrize("replacement", ["sha256:" + ("f" * 64), None])
def test_d087_rejects_wrong_or_missing_manifest_cost_control_hash(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    replacement: str | None,
) -> None:
    plan, suite, item, manifest = exact_plan_manifest
    assert manifest.experiment is not None
    invalid_context = manifest.experiment.model_copy(
        update={"campaign_cost_control_hash": replacement}
    )
    invalid_manifest = manifest.model_copy(
        update={"experiment": invalid_context}
    )

    assert not qualification_module._execution_plan_matches(
        plan=plan,
        manifest=invalid_manifest,
    )
    with pytest.raises(ContractError, match="approved execution plan"):
        eval_runner._assert_manifest_matches_preflight(
            invalid_manifest,
            suite=suite,
            preflight=plan,
            item=item,
        )

    if replacement is None:
        context_payload = manifest.experiment.model_dump(mode="json")
        context_payload.pop("campaign_cost_control_hash")
        with pytest.raises(
            ValidationError,
            match="requires campaign_cost_control_hash",
        ):
            ExperimentRunContext.model_validate(context_payload)


def test_d087_openai_resume_is_blocked_before_task_lookup_or_start(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, manifest = exact_plan_manifest
    runner = AgentRunner(tmp_path / "resume-runtime")
    runner.state.create_run(manifest)
    calls: list[str] = []

    def unexpected(*_args: Any, **_kwargs: Any) -> None:
        calls.append("called")
        raise AssertionError("resume crossed the D-087 no-live-resume boundary")

    monkeypatch.setattr(runner, "_find_task", unexpected)
    monkeypatch.setattr(runner, "start", unexpected)

    with pytest.raises(ContractError, match="D-087 live resume is disabled"):
        runner.resume(manifest.run_id)

    assert calls == []


def test_d087_direct_fresh_run_requires_exact_reservation_before_execute(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, item, manifest = exact_plan_manifest
    live_authorization, reservation, _ = _persist_plan_and_reserve(
        plan,
        manifest,
    )
    runner = AgentRunner(tmp_path / "direct-start-runtime")
    execute_calls: list[str] = []
    monkeypatch.setattr(
        runner,
        "_execute",
        lambda *_args, **_kwargs: execute_calls.append("called"),
    )

    with pytest.raises(ContractError, match="campaign cost reservation"):
        runner.start(
            item["task"],
            model="openai",
            manifest=manifest,
            live_authorization=live_authorization,
        )

    fresh_manifest = manifest.model_copy(
        update={"run_id": "run_d087_unreserved_fresh_clone"}
    )
    with pytest.raises(ContractError, match="campaign cost reservation"):
        runner.start(
            item["task"],
            model="openai",
            manifest=fresh_manifest,
            live_authorization=live_authorization,
            campaign_cost_reservation=reservation,
        )

    assert execute_calls == []


def test_d087_rejects_tampered_journal_and_capability_before_execute(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, item, manifest = exact_plan_manifest
    live_authorization, reservation, journal_path = _persist_plan_and_reserve(
        plan,
        manifest,
    )
    runner = AgentRunner(journal_path.parents[2])
    execute_calls: list[str] = []
    monkeypatch.setattr(
        runner,
        "_execute",
        lambda *_args, **_kwargs: execute_calls.append("called"),
    )

    forged_capability = replace(
        reservation,
        journal_hash="sha256:" + ("f" * 64),
    )
    with pytest.raises(ContractError, match="journal bytes changed"):
        runner.start(
            item["task"],
            model="openai",
            manifest=manifest,
            live_authorization=live_authorization,
            campaign_cost_reservation=forged_capability,
        )

    journal_path.write_bytes(journal_path.read_bytes() + b"tamper")
    with pytest.raises(ContractError, match="reservation journal"):
        runner.start(
            item["task"],
            model="openai",
            manifest=manifest,
            live_authorization=live_authorization,
            campaign_cost_reservation=reservation,
        )

    assert execute_calls == []


def test_d087_rejects_alias_path_and_different_runner_root(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, item, manifest = exact_plan_manifest
    live_authorization, reservation, journal_path = _persist_plan_and_reserve(
        plan,
        manifest,
    )
    execute_calls: list[str] = []
    alias_capability = replace(
        reservation,
        journal_path=str(
            journal_path.parent / "alias" / ".." / journal_path.name
        ),
    )
    exact_runner = AgentRunner(journal_path.parents[2])
    monkeypatch.setattr(
        exact_runner,
        "_execute",
        lambda *_args, **_kwargs: execute_calls.append("called"),
    )

    with pytest.raises(ContractError, match="exact canonical approved path"):
        exact_runner.start(
            item["task"],
            model="openai",
            manifest=manifest,
            live_authorization=live_authorization,
            campaign_cost_reservation=alias_capability,
        )

    other_runner = AgentRunner(tmp_path / "other-runtime")
    monkeypatch.setattr(
        other_runner,
        "_execute",
        lambda *_args, **_kwargs: execute_calls.append("called"),
    )
    with pytest.raises(ContractError, match="runner root"):
        other_runner.start(
            item["task"],
            model="openai",
            manifest=manifest,
            live_authorization=live_authorization,
            campaign_cost_reservation=reservation,
        )

    assert execute_calls == []


def test_d087_reservation_is_durably_consumed_once_before_execute(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, item, manifest = exact_plan_manifest
    live_authorization, reservation, journal_path = _persist_plan_and_reserve(
        plan,
        manifest,
    )
    runner = AgentRunner(journal_path.parents[2])
    workspace = tmp_path / "managed-workspace"
    workspace.mkdir()
    execute_calls: list[str] = []

    class FakeDockerSandbox:
        def image_identity(self) -> str | None:
            return manifest.evaluator_image_digest

        def probe_image_identity(self) -> None:
            return None

    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: True,
    )
    monkeypatch.setattr(
        runner,
        "_docker_sandbox",
        lambda _package: FakeDockerSandbox(),
    )
    monkeypatch.setattr(
        runner.workspaces,
        "create",
        lambda *_args, **_kwargs: workspace,
    )
    monkeypatch.setattr(
        runner.workspaces,
        "validate_managed_workspace",
        lambda _workspace: workspace,
    )
    monkeypatch.setattr(
        runner.workspaces,
        "validate_pristine",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner,
        "_execute",
        lambda *_args, **_kwargs: execute_calls.append(manifest.run_id)
        or {"run_id": manifest.run_id},
    )

    result = runner.start(
        item["task"],
        model="openai",
        manifest=manifest,
        live_authorization=live_authorization,
        campaign_cost_reservation=reservation,
    )

    marker_path = _campaign_reservation_consumption_path(reservation)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert result == {"run_id": manifest.run_id}
    assert execute_calls == [manifest.run_id]
    assert marker["reservation_event_hash"] == reservation.reservation_event_hash
    assert marker["run_id"] == manifest.run_id
    assert marker["state_consumption_content_hash"].startswith("sha256:")

    marker_path.unlink()

    with pytest.raises(ContractError, match="already consumed"):
        runner.start(
            item["task"],
            model="openai",
            manifest=manifest,
            live_authorization=live_authorization,
            campaign_cost_reservation=reservation,
        )

    assert execute_calls == [manifest.run_id]


def test_d087_consumed_row_rejects_three_event_journal_reset(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
) -> None:
    plan, _, _, manifest = exact_plan_manifest
    live_authorization, reservation, journal_path = _persist_plan_and_reserve(
        plan,
        manifest,
    )
    state = StateStore(journal_path.parents[2] / "state.sqlite3")
    state.create_run(manifest)
    state.record_d087_reservation_consumption(
        execution_hash=reservation.execution_hash,
        schedule_row_id=reservation.schedule_row_id,
        run_id=reservation.run_id,
        reservation_event_hash=reservation.reservation_event_hash,
        control_hash=reservation.campaign_cost_control_hash,
    )

    fresh_manifest = manifest.model_copy(
        update={"run_id": "run_d087_reset_clone"}
    )
    journal_path.unlink()
    cost_control = plan["campaign_cost_control"]
    descriptor = cost_control["descriptor"]
    event_hash = eval_runner._append_campaign_event(
        journal_path,
        sequence=1,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": plan["experiment_id"],
            "execution_hash": plan["execution_hash"],
            "campaign_cost_control_hash": cost_control["content_hash"],
        },
    )
    reset_reservation_hash = eval_runner._append_campaign_event(
        journal_path,
        sequence=2,
        previous_event_hash=event_hash,
        event_type="RunCostReserved",
        payload={
            "schedule_row_id": fresh_manifest.experiment.schedule_row_id,
            "run_id": fresh_manifest.run_id,
            "campaign_cost_control_hash": cost_control["content_hash"],
            "accrued_cost_nanos_before": 0,
            "held_reserve_nanos_after": descriptor[
                "per_run_reserve_nanos"
            ],
            "reserve_nanos": descriptor["per_run_reserve_nanos"],
            "cap_nanos": descriptor["hard_cap_nanos"],
        },
    )
    eval_runner._append_campaign_event(
        journal_path,
        sequence=3,
        previous_event_hash=reset_reservation_hash,
        event_type="RunStarted",
        payload={
            "schedule_row_id": fresh_manifest.experiment.schedule_row_id,
            "run_id": fresh_manifest.run_id,
        },
    )

    with pytest.raises(ContractError, match="omits or rewrites"):
        issue_campaign_cost_reservation_authorization(
            fresh_manifest,
            live_authorization,
            journal_path=journal_path,
            reservation_event_hash=reset_reservation_hash,
        )


def test_d087_paid_boundary_recomputes_rehashed_prior_settlement(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, _, manifest = exact_plan_manifest
    live_authorization, _, journal_path = _persist_plan_and_reserve(
        plan,
        manifest,
    )
    journal_path.unlink()
    cost_control = plan["campaign_cost_control"]
    descriptor = cost_control["descriptor"]
    control_hash = cost_control["content_hash"]
    cap_nanos = descriptor["hard_cap_nanos"]
    reserve_nanos = descriptor["per_run_reserve_nanos"]
    prior_row_id = "sha256:" + ("9" * 64)
    prior_manifest = manifest.model_copy(
        update={"run_id": "run_d087_prior_settlement"}
    )
    usage_evidence = eval_runner._d087_usage_evidence(
        eval_runner.Usage(input_tokens=1),
        run_id=prior_manifest.run_id,
        schedule_row_id=prior_row_id,
        qualification_hash="sha256:" + ("a" * 64),
        source_evidence_hash="sha256:" + ("b" * 64),
        persisted_result_hash="sha256:" + ("c" * 64),
    )
    monkeypatch.setattr(
        eval_runner,
        "_load_d087_durable_usage_evidence",
        lambda run_id, row_id, _root: (
            usage_evidence
            if run_id == prior_manifest.run_id and row_id == prior_row_id
            else pytest.fail("unexpected durable usage lookup")
        ),
    )

    sequence = 1
    event_hash = eval_runner._append_campaign_event(
        journal_path,
        sequence=sequence,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": plan["experiment_id"],
            "execution_hash": plan["execution_hash"],
            "campaign_cost_control_hash": control_hash,
        },
    )

    def append(event_type: str, payload: dict[str, Any]) -> str:
        nonlocal sequence, event_hash
        sequence += 1
        event_hash = eval_runner._append_campaign_event(
            journal_path,
            sequence=sequence,
            previous_event_hash=event_hash,
            event_type=event_type,
            payload=payload,
        )
        return event_hash

    prior_reservation_hash = append(
        "RunCostReserved",
        {
            "schedule_row_id": prior_row_id,
            "run_id": prior_manifest.run_id,
            "campaign_cost_control_hash": control_hash,
            "accrued_cost_nanos_before": 0,
            "held_reserve_nanos_after": reserve_nanos,
            "reserve_nanos": reserve_nanos,
            "cap_nanos": cap_nanos,
        },
    )
    append(
        "RunStarted",
        {
            "schedule_row_id": prior_row_id,
            "run_id": prior_manifest.run_id,
        },
    )
    append(
        "RunTerminal",
        {
            "schedule_row_id": prior_row_id,
            "run_id": prior_manifest.run_id,
            "usage_evidence": usage_evidence,
            "usage_evidence_hash": usage_evidence["content_hash"],
            "usage_reconciliation_passed": True,
            "qualification_hash": usage_evidence["descriptor"][
                "qualification_hash"
            ],
        },
    )
    # The hash chain is internally consistent, but the one input token costs
    # 750 nano-USD under D-087's fixed price and is fraudulently settled at 0.
    append(
        "RunCostSettled",
        {
            "schedule_row_id": prior_row_id,
            "run_id": prior_manifest.run_id,
            "campaign_cost_control_hash": control_hash,
            "accrued_cost_nanos_before": 0,
            "actual_run_cost_nanos": 0,
            "usage_evidence_hash": usage_evidence["content_hash"],
            "usage_reconciliation_passed": True,
            "accrued_cost_nanos_after": 0,
            "held_reserve_nanos_after": 0,
            "reserve_nanos": reserve_nanos,
            "cap_nanos": cap_nanos,
        },
    )
    current_reservation_hash = append(
        "RunCostReserved",
        {
            "schedule_row_id": manifest.experiment.schedule_row_id,
            "run_id": manifest.run_id,
            "campaign_cost_control_hash": control_hash,
            "accrued_cost_nanos_before": 0,
            "held_reserve_nanos_after": reserve_nanos,
            "reserve_nanos": reserve_nanos,
            "cap_nanos": cap_nanos,
        },
    )
    append(
        "RunStarted",
        {
            "schedule_row_id": manifest.experiment.schedule_row_id,
            "run_id": manifest.run_id,
        },
    )
    state = StateStore(journal_path.parents[2] / "state.sqlite3")
    state.create_run(prior_manifest)
    state.record_d087_reservation_consumption(
        execution_hash=plan["execution_hash"],
        schedule_row_id=prior_row_id,
        run_id=prior_manifest.run_id,
        reservation_event_hash=prior_reservation_hash,
        control_hash=control_hash,
    )

    with pytest.raises(ContractError, match="invalid D-087 campaign cost settlement"):
        issue_campaign_cost_reservation_authorization(
            manifest,
            live_authorization,
            journal_path=journal_path,
            reservation_event_hash=current_reservation_hash,
        )


def test_d087_qualify_run_requires_exact_campaign_spend_cap_contract(
    exact_plan_manifest: tuple[
        dict[str, Any], eval_runner.ExperimentSuite, dict[str, Any], Any
    ],
    tmp_path: Path,
) -> None:
    plan, suite, item, manifest = exact_plan_manifest
    trace_root = tmp_path / "qualification-runtime"
    run_id, _, _ = trace_fixtures._terminal_trace(
        trace_root,
        task_dir=Path(item["task"]).parent,
        purpose=ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
        role=DatasetRole.MEMORY_DEVELOPMENT,
        max_output_tokens=suite.max_output_tokens,
        write_execution_plan=False,
    )
    exact_manifest = manifest.model_copy(update={"run_id": run_id})
    with sqlite3.connect(trace_root / "state.sqlite3") as connection:
        updated = connection.execute(
            "UPDATE runs SET manifest_json = ? WHERE run_id = ?",
            (
                canonical_json(exact_manifest.model_dump(mode="json")),
                run_id,
            ),
        )
        assert updated.rowcount == 1

    plan_path = (
        trace_root
        / "experiments"
        / "plans"
        / f"{plan['execution_hash'].removeprefix('sha256:')}.json"
    )
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    qualification = qualification_module.qualify_run(
        run_id,
        task_dir=Path(item["task"]).parent,
        root=trace_root,
        persist=False,
    )
    checks = {
        row["check_id"]: row for row in qualification["checks"]
    }
    spend_check = checks["campaign_spend_cap_contract"]

    assert spend_check["passed"] is True, spend_check
    assert spend_check["details"] == {
        "campaign_cost_control_hash": plan["campaign_cost_control"][
            "content_hash"
        ],
        "manifest_cost_control_hash": plan["campaign_cost_control"][
            "content_hash"
        ],
        "hard_cap_nanos": 25_000_000_000,
        "per_run_reserve_nanos": 7_312_500_000,
        "live_resume_supported": False,
    }

    rehashed_tamper = deepcopy(plan)
    descriptor = rehashed_tamper["campaign_cost_control"]["descriptor"]
    descriptor["hard_cap_nanos"] -= 1
    rehashed_tamper["campaign_cost_control"]["content_hash"] = sha256_text(
        canonical_json(descriptor)
    )
    plan_path.write_text(
        json.dumps(rehashed_tamper, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    rejected = qualification_module.qualify_run(
        run_id,
        task_dir=Path(item["task"]).parent,
        root=trace_root,
        persist=False,
    )
    rejected_checks = {
        row["check_id"]: row for row in rejected["checks"]
    }

    assert rejected_checks["approved_execution_plan"]["passed"] is False
    assert rejected_checks["campaign_spend_cap_contract"]["passed"] is False
