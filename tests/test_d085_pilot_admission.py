from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from patchloop.contracts import (
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
)
from patchloop.evals import qualification as qualification_module
from patchloop.evals import runner as eval_runner
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_text
from tests.test_d085_qualification import _terminal_pilot_trace
from tests.test_experiments import _ready_live_environment

CAMPAIGN_SUITE = Path("experiments/dev-no-memory-v5.template.yaml")
CAMPAIGN_COMMIT = "b" * 40


def _manifest_for_plan(plan: dict[str, Any], *, run_id: str):
    suite = eval_runner.ExperimentSuite.model_validate(plan["suite"])
    row = plan["schedule"][0]
    task = next(
        item for item in plan["tasks"] if item["task_id"] == row["task_id"]
    )
    package = load_task_package(Path(task["task"]).parent)
    manifest = build_manifest(
        package,
        run_id=run_id,
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(row["condition"]),
        sandbox_backend="docker",
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
            dataset_manifest_hash=plan["dataset"]["manifest_hash"],
            dataset_role=DatasetRole(row["dataset_role"]),
            schedule_seed=suite.seed,
            schedule_order=row["order"],
            schedule_row_id=row["schedule_row_id"],
            repetition=row["repetition"],
        ),
    )
    manifest.harness_git_commit = plan["environment"]["git"]["commit"]
    return manifest


@pytest.fixture
def admission_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    original_load_suite = eval_runner.load_suite
    run_id, result, _ = _terminal_pilot_trace(
        tmp_path,
        monkeypatch,
        pricing_verified_at=datetime.now(UTC),
    )
    monkeypatch.setattr(eval_runner, "load_suite", original_load_suite)
    qualification = qualification_module.qualify_run(
        run_id,
        task_dir=Path(eval_runner.PILOT_TASK).parent,
        root=tmp_path,
        persist=True,
    )
    assert result.outcome_kind.value == "task_failure"
    assert qualification["qualified"] is True
    state = StateStore(tmp_path / "state.sqlite3")
    pilot_manifest = state.get_manifest(run_id)
    assert pilot_manifest.experiment is not None
    source_plan_path = qualification_module._execution_plan_path(
        tmp_path,
        pilot_manifest.experiment.execution_hash,
    )

    campaign_payload = yaml.safe_load(
        CAMPAIGN_SUITE.read_text(encoding="utf-8")
    )
    campaign_payload["pilot_run_id"] = pilot_manifest.run_id
    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text(
        yaml.safe_dump(campaign_payload, sort_keys=False),
        encoding="utf-8",
    )
    _ready_live_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path)
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {
            "available": True,
            "commit": CAMPAIGN_COMMIT,
            "clean": True,
        },
    )
    return {
        "campaign_path": campaign_path,
        "qualification": qualification,
        "qualification_path": qualification_module.qualification_path(
            run_id,
            root=tmp_path,
        ),
        "source_plan_path": source_plan_path,
        "pilot_manifest": pilot_manifest,
        "state": state,
        "runtime_root": tmp_path,
    }


def _write_forged_qualification(
    admission_case: dict[str, Any],
    payload: dict[str, Any],
    *,
    rehash: bool = True,
) -> None:
    forged = deepcopy(payload)
    if rehash:
        forged.pop("qualification_hash", None)
        forged["qualification_hash"] = sha256_text(canonical_json(forged))
    admission_case["qualification_path"].write_text(
        json.dumps(forged, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def test_d085_task_failure_is_admitted_and_binds_separate_commits(
    admission_case: dict[str, Any],
) -> None:
    preflight = eval_runner.preflight_suite(admission_case["campaign_path"])
    admission = preflight["pilot_admission"]
    descriptor = admission["descriptor"]

    assert admission["admitted"] is True
    assert admission["pilot_admission_hash"] == sha256_text(
        canonical_json(descriptor)
    )
    assert descriptor["pilot"]["outcome_kind"] == "task_failure"
    assert descriptor["pilot"]["process_qualification"]["evaluation_reached"]
    assert descriptor["campaign"]["expected_runs"] == 12
    assert descriptor["runtime_binding"]["pilot_harness_git_commit"] == (
        admission_case["pilot_manifest"].harness_git_commit
    )
    assert descriptor["runtime_binding"]["campaign_harness_git_commit"] == (
        CAMPAIGN_COMMIT
    )
    assert (
        admission_case["pilot_manifest"].harness_git_commit
        != CAMPAIGN_COMMIT
    )


def test_d085_admission_requires_full_pilot_and_campaign_git_commits(
    admission_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": "short", "clean": True},
    )
    invalid_campaign_commit = eval_runner.preflight_suite(
        admission_case["campaign_path"]
    )
    assert invalid_campaign_commit["pilot_qualification"]["qualified"] is False

    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {
            "available": True,
            "commit": CAMPAIGN_COMMIT,
            "clean": True,
        },
    )
    admitted = eval_runner.preflight_suite(admission_case["campaign_path"])[
        "pilot_admission"
    ]
    malformed = deepcopy(admitted)
    malformed["descriptor"]["runtime_binding"][
        "pilot_harness_git_commit"
    ] = "short"
    malformed["descriptor"]["runtime_binding"]["pilot_runtime_contract"][
        "harness_git_commit"
    ] = "short"
    malformed["pilot_admission_hash"] = sha256_text(
        canonical_json(malformed["descriptor"])
    )
    suite = eval_runner.load_suite(admission_case["campaign_path"])
    assert not eval_runner._pilot_admission_plan_binding_matches(
        malformed,
        suite,
        campaign_harness_commit=CAMPAIGN_COMMIT,
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("experiment_id", "wrong-pilot"),
        ("purpose", ExperimentPurpose.DEVELOPMENT_VALIDATION_MODEL_CANDIDATE_PILOT.value),
        ("task_id", "moto-query-scanned-count"),
        ("dataset_role", DatasetRole.MEMORY_DEVELOPMENT.value),
        ("memory_condition", MemoryCondition.RAW_TRACE.value),
        ("schedule_row_id", "sha256:" + ("d" * 64)),
        ("model_id", "gpt-5.4-mini-drift"),
        ("max_output_tokens", 24_999),
        ("tool_schema_version", "v3"),
        ("context_policy_version", "phase-evidence-v4"),
    ],
)
def test_d085_admission_rejects_qualification_identity_and_runtime_drift(
    admission_case: dict[str, Any],
    field: str,
    replacement: Any,
) -> None:
    forged = deepcopy(admission_case["qualification"])
    forged[field] = replacement
    _write_forged_qualification(admission_case, forged)

    preflight = eval_runner.preflight_suite(admission_case["campaign_path"])

    assert "pilot_admission" not in preflight
    assert preflight["pilot_qualification"]["qualified"] is False
    assert "QUALIFIED_PILOT_REQUIRED" in {
        blocker["code"] for blocker in preflight["blockers"]
    }


@pytest.mark.parametrize(
    "check_id",
    eval_runner.CONDITION_NEUTRAL_COMPARISON_PILOT_REQUIRED_CHECKS,
)
def test_d085_admission_requires_each_process_gate(
    admission_case: dict[str, Any],
    check_id: str,
) -> None:
    check = next(
        row
        for row in admission_case["qualification"]["checks"]
        if row["check_id"] == check_id
    )
    check["passed"] = False
    _write_forged_qualification(
        admission_case,
        admission_case["qualification"],
    )

    preflight = eval_runner.preflight_suite(admission_case["campaign_path"])

    assert preflight["pilot_qualification"]["qualified"] is False


def test_d085_admission_rejects_legacy_runtime_content_hash(
    admission_case: dict[str, Any],
) -> None:
    admission_case["qualification"]["runtime_contract_content_hash"] = (
        eval_runner._expected_runtime_contract_hash()
    )
    _write_forged_qualification(
        admission_case,
        admission_case["qualification"],
    )

    preflight = eval_runner.preflight_suite(admission_case["campaign_path"])

    assert preflight["pilot_qualification"]["qualified"] is False


def test_d085_admission_rejects_qualification_cas_and_commit_mismatch(
    admission_case: dict[str, Any],
) -> None:
    forged = deepcopy(admission_case["qualification"])
    forged["task_id"] = "self-hashed-forgery"
    _write_forged_qualification(
        admission_case,
        forged,
        rehash=False,
    )
    qualification_tamper = eval_runner.preflight_suite(
        admission_case["campaign_path"]
    )
    assert qualification_tamper["pilot_qualification"]["qualified"] is False

    forged = deepcopy(admission_case["qualification"])
    forged["harness_git_commit"] = "f" * 40
    _write_forged_qualification(admission_case, forged)
    commit_tamper = eval_runner.preflight_suite(admission_case["campaign_path"])
    assert commit_tamper["pilot_qualification"]["qualified"] is False


def test_d085_admission_rejects_self_hashed_forged_qualification(
    admission_case: dict[str, Any],
) -> None:
    forged = deepcopy(admission_case["qualification"])
    forged["task_id"] = "self-hashed-forgery"
    _write_forged_qualification(admission_case, forged)
    checked = qualification_module.load_trace_qualification(
        admission_case["pilot_manifest"].run_id,
        root=admission_case["runtime_root"],
    )
    assert checked["task_id"] == "self-hashed-forgery"

    preflight = eval_runner.preflight_suite(admission_case["campaign_path"])

    assert preflight["pilot_qualification"]["qualified"] is False
    assert "durable recomputation" in preflight["pilot_qualification"]["reason"]


def test_d085_admission_rejects_created_run_without_terminal_result(
    admission_case: dict[str, Any],
    tmp_path: Path,
) -> None:
    created_run_id = "run_d085_created_forgery"
    created_manifest = admission_case["pilot_manifest"].model_copy(
        update={"run_id": created_run_id}
    )
    admission_case["state"].create_run(created_manifest)
    source_hash = qualification_module.calculate_source_evidence_hash(
        created_run_id,
        root=tmp_path,
    )
    forged = deepcopy(admission_case["qualification"])
    forged["run_id"] = created_run_id
    forged["source_evidence_hash"] = source_hash
    forged.pop("qualification_hash", None)
    forged["qualification_hash"] = sha256_text(canonical_json(forged))
    created_qualification_path = qualification_module.qualification_path(
        created_run_id,
        root=tmp_path,
    )
    created_qualification_path.parent.mkdir(parents=True, exist_ok=True)
    created_qualification_path.write_text(
        json.dumps(forged, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    campaign_payload = yaml.safe_load(
        admission_case["campaign_path"].read_text(encoding="utf-8")
    )
    campaign_payload["pilot_run_id"] = created_run_id
    admission_case["campaign_path"].write_text(
        yaml.safe_dump(campaign_payload, sort_keys=False),
        encoding="utf-8",
    )

    preflight = eval_runner.preflight_suite(admission_case["campaign_path"])

    assert preflight["pilot_qualification"]["qualified"] is False
    assert "durable recomputation" in preflight["pilot_qualification"]["reason"]


def test_d085_admission_rejects_source_and_plan_cas_tamper(
    admission_case: dict[str, Any],
) -> None:
    forged = deepcopy(admission_case["qualification"])
    forged["source_evidence_hash"] = "sha256:" + ("e" * 64)
    _write_forged_qualification(
        admission_case,
        forged,
    )
    source_tamper = eval_runner.preflight_suite(admission_case["campaign_path"])
    assert source_tamper["pilot_qualification"]["qualified"] is False

    _write_forged_qualification(
        admission_case,
        admission_case["qualification"],
    )
    plan = json.loads(
        admission_case["source_plan_path"].read_text(encoding="utf-8")
    )
    plan["runtime_contract"]["comparison_budget_policy"]["profile_id"] = (
        "forged-policy"
    )
    admission_case["source_plan_path"].write_text(
        json.dumps(plan, indent=2),
        encoding="utf-8",
    )
    plan_tamper = eval_runner.preflight_suite(admission_case["campaign_path"])
    assert plan_tamper["pilot_qualification"]["qualified"] is False


def test_d085_plan_matcher_rejects_admission_descriptor_tamper(
    admission_case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight = eval_runner.preflight_suite(admission_case["campaign_path"])
    plan = deepcopy(preflight)
    plan["schema_version"] = "experiment-execution-plan-v1"
    plan["ready"] = True
    plan["blockers"] = []
    plan["approval"] = {
        "invocation_approve_live_cost": True,
        "invocation_approved_execution_hash": plan["execution_hash"],
        "matches_execution_hash": True,
    }
    manifest = _manifest_for_plan(plan, run_id="run_d085_campaign_binding")
    monkeypatch.setattr(
        eval_runner,
        "_pricing_contract_matches",
        lambda *_args, **_kwargs: True,
    )

    assert qualification_module._execution_plan_matches(
        plan=plan,
        manifest=manifest,
    )

    tampered = deepcopy(plan)
    tampered["pilot_admission"]["descriptor"]["runtime_binding"][
        "campaign_harness_git_commit"
    ] = "f" * 40
    assert not qualification_module._execution_plan_matches(
        plan=tampered,
        manifest=manifest,
    )

    rehashed = deepcopy(tampered)
    rehashed["pilot_admission"]["pilot_admission_hash"] = sha256_text(
        canonical_json(rehashed["pilot_admission"]["descriptor"])
    )
    assert not qualification_module._execution_plan_matches(
        plan=rehashed,
        manifest=manifest,
    )
