from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    Artifact,
    Budget,
    DatasetRole,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.evals import qualification as trace_qualification
from patchloop.evals import runner as eval_runner
from patchloop.evals.runner import ExperimentSuite
from patchloop.runtime import build_manifest, git_commit
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

DEV_TEMPLATE = Path("experiments/dev-no-memory-v5.template.yaml")
CORE_TEMPLATE = Path("experiments/core.template.yaml")
HISTORICAL_TEMPLATE = Path("experiments/dev-no-memory.template.yaml")
SMOKE_TASK = Path("tasks/smoke/csv-quoted-newline")


def _suite(path: Path) -> ExperimentSuite:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if path == CORE_TEMPLATE:
        payload["experiment_id"] = "core-d084-runtime-binding"
        payload["embedding_revision"] = "d084-test-revision"
    return ExperimentSuite.model_validate(payload)


def _comparison_manifest(*, run_id: str = "run_d084_runtime"):
    package = load_task_package(SMOKE_TASK)
    suite = _suite(DEV_TEMPLATE)
    dataset_hash = suite.dataset_manifest_hash
    assert dataset_hash is not None
    return build_manifest(
        package,
        run_id=run_id,
        provider="openai",
        model_id=suite.model_id,
        memory_condition=MemoryCondition.NO_MEMORY,
        sandbox_backend="local",
        budget=suite.budget,
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
            purpose=ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
            suite_hash="sha256:" + ("a" * 64),
            execution_hash="sha256:" + ("b" * 64),
            dataset_manifest_hash=dataset_hash,
            dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
            schedule_seed=suite.seed,
            schedule_order=1,
            schedule_row_id="sha256:" + ("c" * 64),
            repetition=1,
        ),
    )


@pytest.mark.parametrize("path", [DEV_TEMPLATE, CORE_TEMPLATE])
def test_d084_exact_future_profile_is_hash_bound(path: Path) -> None:
    suite = _suite(path)

    assert eval_runner._is_frozen_comparison_runtime_profile(suite)
    contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit="d" * 40,
    )

    assert contract is not None
    assert contract["schema_version"] == (
        "condition-neutral-comparison-runtime-contract-v1"
    )
    assert contract["comparison_budget_policy"] == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_BUDGET_POLICY
    )
    assert contract["purpose"] == suite.purpose.value
    assert contract["model_provider"] == "openai"
    assert contract["model_id"] == "gpt-5.4-mini-2026-03-17"
    assert contract["reasoning_effort"] == "medium"
    assert contract["reasoning_mode"] == "standard"
    assert contract["service_tier"] == "default"
    assert contract["transport_max_retries"] == 0
    assert contract["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 1_600_000,
        "wall_clock_timeout_seconds": 1_800,
    }
    assert contract["max_output_tokens"] == 25_000
    assert contract["memory_max_context_tokens"] == 2_000
    assert contract["memory_conditions"] == [
        condition.value for condition in suite.conditions
    ]
    assert contract["tool_schema_version"] == "v2"
    assert contract["context_policy_version"] == "phase-evidence-v5"
    assert contract["call_guard_policy"] == (
        "model-tool-observability-only-v1"
    )
    assert contract["harness_git_commit"] == "d" * 40


def test_d084_runtime_contract_changes_the_execution_hash() -> None:
    suite = _suite(DEV_TEMPLATE)
    runtime_contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit="d" * 40,
    )
    common = {
        "dataset": {"manifest_hash": suite.dataset_manifest_hash},
        "task_rows": [],
        "schedule_hash": "sha256:" + ("1" * 64),
        "git_state": {"commit": "d" * 40},
        "docker_state": {"images": []},
        "openai_sdk": {"installed": True, "version": "test"},
        "pilot_qualification": {"qualification_hash": None},
    }

    bound = eval_runner._execution_hash(
        suite,
        runtime_contract=runtime_contract,
        **common,
    )
    unbound = eval_runner._execution_hash(
        suite,
        runtime_contract=None,
        **common,
    )
    tampered = json.loads(json.dumps(runtime_contract))
    tampered["budget"]["max_total_tokens"] = 1_599_999
    tampered_hash = eval_runner._execution_hash(
        suite,
        runtime_contract=tampered,
        **common,
    )

    assert len({bound, unbound, tampered_hash}) == 3


def test_d084_policy_descriptor_fails_closed_on_byte_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = eval_runner.CONDITION_NEUTRAL_COMPARISON_BUDGET_POLICY
    source = Path(descriptor["path"]).read_bytes()
    destination = tmp_path / descriptor["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(source)
    monkeypatch.setattr(eval_runner, "repository_root", lambda: tmp_path)

    assert eval_runner._validated_comparison_budget_policy() == descriptor

    destination.write_bytes(source + b"\n")
    with pytest.raises(ContractError, match="policy artifact"):
        eval_runner._validated_comparison_budget_policy()


def test_d084_historical_campaign_does_not_enter_the_new_runtime_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = eval_runner.load_suite(HISTORICAL_TEMPLATE)
    monkeypatch.setattr(
        eval_runner,
        "_validated_comparison_budget_policy",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected D-083 read")),
    )

    assert not eval_runner._is_frozen_comparison_runtime_profile(historical)
    assert (
        eval_runner._experiment_runtime_contract(
            historical,
            harness_git_commit="d" * 40,
        )
        is None
    )
    pricing = eval_runner._pricing_contract(
        historical,
        schedule_size=12,
    )
    assert "start_time_verification" not in pricing


def test_d084_manifest_preflight_reconstructs_the_exact_runtime_contract() -> None:
    suite = _suite(DEV_TEMPLATE)
    manifest = _comparison_manifest()
    package = load_task_package(SMOKE_TASK)
    assert manifest.experiment is not None
    runtime_contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit=manifest.harness_git_commit,
    )
    preflight = {
        "runtime_contract": runtime_contract,
        "environment": {
            "openai_sdk": {"version": manifest.model.provider_sdk_version}
        },
        "suite_hash": manifest.experiment.suite_hash,
        "execution_hash": manifest.experiment.execution_hash,
        "dataset": {
            "manifest_hash": manifest.experiment.dataset_manifest_hash
        },
    }
    item = {
        "task_id": manifest.task_id,
        "task_version": manifest.task_version,
        "base_commit": manifest.base_commit,
        "public_spec_hash": manifest.public_spec_hash,
        "private_spec_hash": manifest.private_spec_hash,
        "evaluator_image_digest": None,
        "condition": MemoryCondition.NO_MEMORY.value,
        "dataset_role": DatasetRole.MEMORY_DEVELOPMENT.value,
        "order": 1,
        "schedule_row_id": manifest.experiment.schedule_row_id,
        "repetition": 1,
    }
    assert package.public.task_id == manifest.task_id

    eval_runner._assert_manifest_matches_preflight(
        manifest,
        suite=suite,
        preflight=preflight,
        item=item,
    )

    tampered_budget = manifest.budget.model_copy(
        update={"max_total_tokens": 1_599_999}
    )
    tampered = manifest.model_copy(update={"budget": tampered_budget})
    with pytest.raises(ContractError, match="approved execution plan"):
        eval_runner._assert_manifest_matches_preflight(
            tampered,
            suite=suite,
            preflight=preflight,
            item=item,
        )


def test_d084_paid_boundary_routes_exact_profile_through_plan_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _comparison_manifest(run_id="run_d084_paid_boundary")
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
    calls = []

    def plan_matches(*, plan, manifest):
        calls.append((plan, manifest.run_id))
        return True

    monkeypatch.setattr(
        trace_qualification,
        "_execution_plan_matches",
        plan_matches,
    )
    authorization = SimpleNamespace(
        plan_path=str(plan_path),
        plan_hash=sha256_bytes(plan_path.read_bytes()),
    )

    assert AgentRunner._live_plan_matches_manifest(manifest, authorization)
    assert calls == [
        (
            json.loads(plan_path.read_text(encoding="utf-8")),
            manifest.run_id,
        )
    ]

    tampered_budget = manifest.budget.model_copy(
        update={"max_total_tokens": 1_599_999}
    )
    tampered = manifest.model_copy(update={"budget": tampered_budget})
    assert not AgentRunner._live_plan_matches_manifest(
        tampered,
        authorization,
    )

    core_payload = manifest.model_dump(mode="json")
    core_payload["experiment"]["purpose"] = ExperimentPurpose.CORE.value
    core_payload["experiment"]["dataset_role"] = (
        DatasetRole.CORE_SAME_REPO.value
    )
    core_manifest = RunManifest.model_validate(core_payload)
    assert not AgentRunner._live_plan_matches_manifest(
        core_manifest,
        authorization,
    )
    assert len(calls) == 1


def test_d084_run_started_persists_exact_runtime_evidence_before_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _comparison_manifest(run_id="run_d084_started_evidence")
    runner = AgentRunner(tmp_path / "runtime")
    validation_calls: list[str] = []
    validate_runtime = (
        runner._validate_generic_baseline_runtime_resume_contract
    )

    def validate_and_record(**kwargs):
        validation_calls.append(kwargs["manifest"].run_id)
        return validate_runtime(**kwargs)

    monkeypatch.setattr(
        AgentRunner,
        "_require_live_authorization",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner,
        "_validate_generic_baseline_runtime_resume_contract",
        validate_and_record,
    )
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("paid model boundary reached")
        ),
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

    assert validation_calls == [manifest.run_id]

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
    system_prompt, tools = AgentRunner._runtime_contract(manifest)

    assert evidence == {
        "schema_version": "condition-neutral-comparison-runtime-evidence-v1",
        "comparison_budget_policy": (
            eval_runner.CONDITION_NEUTRAL_COMPARISON_BUDGET_POLICY
        ),
        "purpose": ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY.value,
        "model_provider": "openai",
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "budget": eval_runner.GPT54_MINI_FROZEN_COMPARISON_BUDGET.model_dump(
            mode="json"
        ),
        "memory_max_context_tokens": 2_000,
        "memory_condition": MemoryCondition.NO_MEMORY.value,
        "system_prompt": system_prompt,
        "tools": tools,
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "call_guard_policy": "model-tool-observability-only-v1",
    }
    runner._validate_generic_baseline_runtime_resume_contract(
        manifest=manifest,
        events=runner.state.list_events(manifest.run_id),
        system_prompt=system_prompt,
        tool_schemas=tools,
    )
    with pytest.raises(RecoveryError, match="runtime contract artifact"):
        runner._validate_generic_baseline_runtime_resume_contract(
            manifest=manifest,
            events=runner.state.list_events(manifest.run_id),
            system_prompt=system_prompt + "\ndrift",
            tool_schemas=tools,
        )


def test_d084_fresh_start_fails_before_transition_when_runtime_cas_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _comparison_manifest(run_id="run_d084_fresh_start_tamper")
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        AgentRunner,
        "_require_live_authorization",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        runner.artifacts,
        "read_bytes",
        lambda _artifact: b"{}",
    )
    monkeypatch.setattr(
        runner,
        "_transition",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("transition reached after invalid runtime CAS")
        ),
    )

    with pytest.raises(RecoveryError, match="runtime contract artifact"):
        runner.start(SMOKE_TASK, model="openai", manifest=manifest)


def test_d084_plan_contract_hashes_current_v3_prompt_and_v2_tools() -> None:
    suite = _suite(DEV_TEMPLATE)
    contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit=git_commit(),
    )

    assert contract is not None
    assert contract["system_prompt_hash"] == sha256_text(
        eval_runner.SYSTEM_PROMPT_V3
    )
    assert contract["tool_schema_hash"] == sha256_text(
        canonical_json(eval_runner.TOOL_SCHEMAS_V2)
    )


def test_d084_terminal_summary_projects_exact_no_memory_call_guard() -> None:
    payload = {
        "schema_version": "trace-qualification-v2",
        "run_id": "run_d084_summary",
        "qualified": True,
        "purpose": ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY.value,
        "memory_condition": MemoryCondition.NO_MEMORY.value,
        "model_id": "gpt-5.4-mini-2026-03-17",
        "reasoning_effort": "medium",
        "reasoning_mode": "standard",
        "service_tier": "default",
        "transport_max_retries": 0,
        "max_output_tokens": 25_000,
        "budget": Budget(
            max_model_calls=None,
            max_tool_calls=None,
            max_total_tokens=1_600_000,
            wall_clock_timeout_seconds=1_800,
        ).model_dump(mode="json"),
        "tool_schema_version": "v2",
        "context_policy_version": "phase-evidence-v5",
        "checks": [
            {
                "check_id": "disabled_call_guard_contract",
                "passed": True,
                "details": {},
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

    duplicate = {
        **payload,
        "checks": [*payload["checks"], *payload["checks"]],
    }
    assert eval_runner._terminal_qualification_summary(duplicate)[
        "gate_checks"
    ]["disabled_call_guard_contract"] == {
        "schema_version": "qualification-gate-check-projection-v1",
        "check_id": "disabled_call_guard_contract",
        "check_count": 2,
        "passed": None,
    }
