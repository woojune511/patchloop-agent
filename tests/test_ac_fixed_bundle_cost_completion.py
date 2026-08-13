from __future__ import annotations

import copy
import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from patchloop import runtime as runtime_module
from patchloop.agent.runner import LiveExecutionAuthorization, _load_live_execution_plan
from patchloop.contracts import (
    AC_FIXED_BUNDLE_CAPABILITY_CORRECTED_EXPERIMENT_ID,
    AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID,
    AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
    AC_FIXED_BUNDLE_READINESS_EXPERIMENT_ID,
    DatasetRole,
    ExperimentRunContext,
    Usage,
)
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

R1_SUITE = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r1.yaml")
R2_SUITE = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260813-fast-r1.yaml")
R3_SUITE = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260813-r3.yaml")
R5_SUITE = Path("experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r5.yaml")
SOURCE_COMMIT = "a" * 40
R2_BASE_SUITE_HASH = eval_runner._suite_hash(eval_runner.load_suite(R2_SUITE))
EVALUATOR_V2_SOURCE_QUALIFICATION = {
    "source_qualification_hash": "sha256:" + "a" * 64,
    "evaluator_source_hash": "sha256:" + "b" * 64,
    "successor_suite_hash": "sha256:" + "c" * 64,
    "base_suite_hash": R2_BASE_SUITE_HASH,
    "base_suite_matches": True,
}


def _forbidden(label: str):
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError(f"{label} is forbidden in offline D-123 tests")

    return fail


@pytest.fixture
def ac_preflights(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], dict[str, Any]]:
    monkeypatch.setenv("OPENAI_API_KEY", "offline-placeholder-not-used")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path / "runtime")
    monkeypatch.setattr(
        eval_runner,
        "utc_now",
        lambda: datetime(2026, 8, 13, 12, 5, 27, tzinfo=UTC),
    )
    monkeypatch.setattr(
        eval_runner,
        "_git_state",
        lambda: {"available": True, "commit": SOURCE_COMMIT, "clean": True},
    )
    monkeypatch.setattr(
        eval_runner,
        "_docker_image_state",
        lambda images: {
            "available": True,
            "images": [
                {"image": image, "identity": image.rsplit("@", 1)[-1], "ready": True}
                for image in sorted(set(images))
            ],
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_openai_sdk_state",
        lambda: {"installed": True, "version": "offline-test-sdk"},
    )
    monkeypatch.setattr(runtime_module, "git_commit", lambda: SOURCE_COMMIT)
    monkeypatch.setattr(runtime_module, "version", lambda _package: "offline-test-sdk")
    monkeypatch.setattr(
        eval_runner,
        "_validated_ac_evaluator_v2_source_qualification",
        lambda suite: (
            dict(EVALUATOR_V2_SOURCE_QUALIFICATION)
            if suite.experiment_id == AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID
            else None
        ),
    )
    monkeypatch.setattr(socket, "socket", _forbidden("network socket"))
    monkeypatch.setattr(socket, "create_connection", _forbidden("network connection"))

    class ForbiddenRunner:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("AgentRunner construction is forbidden")

    monkeypatch.setattr(eval_runner, "AgentRunner", ForbiddenRunner)
    return eval_runner.preflight_suite(R1_SUITE), eval_runner.preflight_suite(R2_SUITE)


def _row_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "order",
            "schedule_row_id",
            "task_id",
            "split",
            "dataset_role",
            "condition",
            "repetition",
        )
    }


def _usage() -> Usage:
    return Usage(
        input_tokens=1_000,
        cached_input_tokens=100,
        cache_write_input_tokens=0,
        output_tokens=50,
        reasoning_output_tokens=20,
        model_cost_usd=999.0,
    )


def _full_schedule_journal(
    root: Path,
    preflight: dict[str, Any],
) -> tuple[Path, dict[str, dict[str, Any]], dict[str, Any]]:
    journal = root / "experiments" / "journals" / f"{preflight['experiment_id']}.jsonl"
    control = preflight["campaign_cost_control"]
    control_hash = control["content_hash"]
    plan_hash = "sha256:" + "b" * 64
    execution_hash = preflight["execution_hash"]
    sequence = 1
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=sequence,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": preflight["experiment_id"],
            "purpose": preflight["purpose"],
            "execution_hash": execution_hash,
            "schedule_hash": preflight["schedule_hash"],
            "execution_plan_hash": plan_hash,
            "campaign_cost_control_hash": control_hash,
        },
    )
    sequence += 1
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=sequence,
        previous_event_hash=previous,
        event_type="FullScheduleCostReserved",
        payload={
            "experiment_id": preflight["experiment_id"],
            "execution_hash": execution_hash,
            "execution_plan_hash": plan_hash,
            "campaign_cost_control_hash": control_hash,
            "schedule_hash": preflight["schedule_hash"],
            "schedule_row_ids": [row["schedule_row_id"] for row in preflight["schedule"]],
            "per_run_reserve_nanos": 13_612_500_000,
            "full_schedule_reserve_nanos": 54_450_000_000,
            "hard_cap_nanos": 55_000_000_000,
            "row_reserve_count": 4,
            "cost_censoring_allowed": False,
        },
    )
    accrued = 0
    evidence_by_run: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(preflight["schedule"], start=1):
        run_id = f"run_ac_d123_{index}"
        identity = _row_identity(row)
        usage_evidence = eval_runner._full_schedule_usage_evidence(
            _usage(),
            experiment_id=AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
            run_id=run_id,
            schedule_row_id=row["schedule_row_id"],
            qualification_hash="sha256:" + f"{index:x}" * 64,
            source_evidence_hash="sha256:" + f"{index + 4:x}" * 64,
            persisted_result_hash="sha256:" + f"{index + 8:x}" * 64,
        )
        evidence_by_run[run_id] = usage_evidence
        run_cost = eval_runner._validate_full_schedule_usage_evidence(
            usage_evidence,
            experiment_id=AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
            run_id=run_id,
            schedule_row_id=row["schedule_row_id"],
        )
        sequence += 1
        previous = eval_runner._append_campaign_event(
            journal,
            sequence=sequence,
            previous_event_hash=previous,
            event_type="RunStarted",
            payload={
                **identity,
                "run_id": run_id,
                "execution_hash": execution_hash,
                "execution_plan_hash": plan_hash,
                "campaign_cost_control_hash": control_hash,
            },
        )
        sequence += 1
        previous = eval_runner._append_campaign_event(
            journal,
            sequence=sequence,
            previous_event_hash=previous,
            event_type="RunTerminal",
            payload={
                **identity,
                "run_id": run_id,
                "execution_hash": execution_hash,
                "execution_plan_hash": plan_hash,
                "campaign_cost_control_hash": control_hash,
                "usage_evidence": usage_evidence,
                "usage_evidence_hash": usage_evidence["content_hash"],
                "usage_reconciliation_passed": True,
                "outcome_kind": "task_failure",
                "model_cost_usd": 0.0009075,
                "infrastructure_error_type": None,
                "qualification_hash": usage_evidence["descriptor"]["qualification_hash"],
                "qualification_error_type": None,
                "diagnostic_status": None,
                "diagnostic_error_type": None,
            },
        )
        sequence += 1
        previous = eval_runner._append_campaign_event(
            journal,
            sequence=sequence,
            previous_event_hash=previous,
            event_type="RunCostSettled",
            payload={
                **identity,
                "run_id": run_id,
                "execution_hash": execution_hash,
                "execution_plan_hash": plan_hash,
                "campaign_cost_control_hash": control_hash,
                "accrued_cost_nanos_before": accrued,
                "actual_run_cost_nanos": run_cost,
                "usage_evidence_hash": usage_evidence["content_hash"],
                "usage_reconciliation_passed": True,
                "accrued_cost_nanos_after": accrued + run_cost,
                "remaining_reserved_rows_after": 4 - index,
            },
        )
        accrued += run_cost
    qualification = eval_runner._full_schedule_cost_journal_evidence(
        journal,
        control,
        run_root=root,
        expected_execution_hash=execution_hash,
        expected_execution_plan_hash=plan_hash,
        expected_schedule=preflight["schedule"],
        durable_usage_resolver=lambda run_id, _row_id, _root: evidence_by_run[run_id],
    )
    return journal, evidence_by_run, qualification


def _projection(check_id: str) -> dict[str, Any]:
    return {
        "schema_version": "qualification-gate-check-projection-v1",
        "check_id": check_id,
        "check_count": 1,
        "passed": True,
    }


def _completion_rows(
    preflight: dict[str, Any],
    *,
    all_failures: bool = False,
) -> list[dict[str, Any]]:
    checks = {
        check_id: _projection(check_id)
        for check_id in {
            "submission_lifecycle",
            "prompt_token_integrity",
            "usage_reconciliation",
            "persisted_result",
            "disabled_call_guard_contract",
            "approved_execution_plan",
            "ac_fixed_runtime_contract",
            "fixed_memory_delivery_integrity",
            "pricing_start_freshness",
            "campaign_full_schedule_cost_contract",
        }
    }
    rows = []
    for index, expected in enumerate(preflight["schedule"], start=1):
        run_id = f"run_ac_d123_{index}"
        outcome = "task_failure" if all_failures or index % 2 == 0 else "resolved"
        resolved = outcome == "resolved"
        verdicts = {
            "hidden_tests": "pass" if resolved else "fail",
            "regression_tests": "pass",
            "scope_policy": "pass",
            "safety_policy": "pass",
        }
        qualification_hash = "sha256:" + f"{index:x}" * 64
        qualification = {
            "schema_version": "trace-qualification-v1",
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "outcome_kind": outcome,
            "purpose": "development-validation-ac-readiness",
            "experiment_id": AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
            "dataset_role": "development-validation",
            "task_id": expected["task_id"],
            "execution_hash": preflight["execution_hash"],
            "schedule_row_id": expected["schedule_row_id"],
            "memory_condition": expected["condition"],
            "memory_candidate_eligible": False,
            "failure_record_id": None,
            "qualification_hash": qualification_hash,
            "source_evidence_hash": "sha256:" + f"{index + 4:x}" * 64,
            "readiness_checks": copy.deepcopy(checks),
            "model_or_tool_call_budget_blocks": {
                "schema_version": "call-budget-block-projection-v1",
                "source_check_count": 1,
                "source_check_passed": True,
                "event_sequences": [],
            },
            "read_only_recomputation": {
                "schema_version": "qualification-read-only-recomputation-v1",
                "matched": True,
                "qualification_hash": qualification_hash,
                "recomputed_qualification_hash": qualification_hash,
            },
        }
        rows.append(
            {
                **_row_identity(expected),
                "run_id": run_id,
                "attempt_status": "terminal",
                "result": {
                    "run_id": run_id,
                    "agent_submission_status": "completed",
                    "evaluation_status": "completed",
                    "official": True,
                    "outcome_kind": outcome,
                    "scope_compliant_success": resolved,
                    "verdicts": verdicts,
                    "terminal_error": None,
                },
                "qualification": qualification,
                "infrastructure_error": None,
                "qualification_error": None,
                "diagnostic_error": None,
            }
        )
    return rows


def test_r1_remains_cost_pending_and_r2_binds_exact_full_schedule_control(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    r1, r2 = ac_preflights
    assert r1["experiment_id"] == AC_FIXED_BUNDLE_READINESS_EXPERIMENT_ID
    assert "campaign_cost_control" not in r1
    assert "AC_FULL_SCHEDULE_COST_CONTROL_PENDING" in {
        blocker["code"] for blocker in r1["blockers"]
    }

    assert r2["experiment_id"] == AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID
    control = r2["campaign_cost_control"]
    assert control["schema_version"] == ("ac-fixed-bundle-full-schedule-cost-control-evidence-v1")
    assert control["content_hash"] == sha256_text(canonical_json(control["descriptor"]))
    assert control["descriptor"]["policy"] == eval_runner.AC_FIXED_BUNDLE_COST_POLICY
    assert control["descriptor"]["schedule_row_ids"] == [
        row["schedule_row_id"] for row in r2["schedule"]
    ]
    assert control["descriptor"]["full_schedule_reserve_nanos"] == 54_450_000_000
    assert control["descriptor"]["hard_cap_nanos"] == 55_000_000_000
    assert r2["evaluator_v2_qualification"] == EVALUATOR_V2_SOURCE_QUALIFICATION
    assert r2["suite_hash"] == EVALUATOR_V2_SOURCE_QUALIFICATION["successor_suite_hash"]
    blocker_codes = {blocker["code"] for blocker in r2["blockers"]}
    assert "AC_FULL_SCHEDULE_COST_CONTROL_PENDING" not in blocker_codes
    assert "AC_EXECUTION_AUTHORIZATION_CANDIDATE_PENDING" not in blocker_codes
    assert blocker_codes == {"LIVE_COST_NOT_APPROVED", "APPROVAL_HASH_MISMATCH"}
    assert r2["execution_candidate_ready"] is True
    assert r2["ready"] is False


def test_r2_execution_hash_binds_evaluator_v2_qualification(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _r1, original = ac_preflights
    changed = {
        **EVALUATOR_V2_SOURCE_QUALIFICATION,
        "source_qualification_hash": "sha256:" + "d" * 64,
    }
    monkeypatch.setattr(
        eval_runner,
        "_validated_ac_evaluator_v2_source_qualification",
        lambda _suite: changed,
    )

    observed = eval_runner.preflight_suite(R2_SUITE)

    assert observed["evaluator_v2_qualification"] == changed
    assert observed["suite_hash"] == changed["successor_suite_hash"]
    assert observed["execution_hash"] != original["execution_hash"]


def test_r2_paid_plan_matches_qualified_successor_manifest(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    from patchloop.evals import qualification as qualification_module

    _r1, candidate = ac_preflights
    approved = eval_runner.preflight_suite(
        R2_SUITE,
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
    )
    plan = {**approved, "schema_version": "experiment-execution-plan-v1"}
    v1_manifest = _paid_boundary_manifest(approved, row_index=0)
    manifest = _bind_paid_boundary_manifest_v2(v1_manifest, approved)

    assert approved["ready"] is True
    assert not qualification_module._execution_plan_matches(
        plan=plan,
        manifest=v1_manifest,
    )
    assert qualification_module._execution_plan_matches(
        plan=plan,
        manifest=manifest,
    )

    tampered_payload = manifest.model_dump(mode="json")
    tampered_payload["evaluator_contract"]["evaluator_source_hash"] = "sha256:" + "0" * 64
    assert not qualification_module._execution_plan_matches(
        plan=plan,
        manifest=type(manifest).model_validate(tampered_payload),
    )


def test_r3_paid_plan_uses_a_fresh_identity_and_matches_qualified_manifest(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from patchloop.evals import qualification as qualification_module

    _r1, r2 = ac_preflights
    r3_binding = {
        **EVALUATOR_V2_SOURCE_QUALIFICATION,
        "successor_suite_hash": "sha256:" + "d" * 64,
        "base_suite_hash": eval_runner._suite_hash(eval_runner.load_suite(R3_SUITE)),
    }
    monkeypatch.setattr(
        eval_runner,
        "_validated_ac_evaluator_v2_source_qualification",
        lambda suite: (
            dict(r3_binding)
            if suite.experiment_id == AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID
            else None
        ),
    )
    candidate = eval_runner.preflight_suite(R3_SUITE)
    approved = eval_runner.preflight_suite(
        R3_SUITE,
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
    )
    v1_manifest = _paid_boundary_manifest(approved, row_index=0, suite_path=R3_SUITE)
    manifest = _bind_paid_boundary_manifest_v2(v1_manifest, approved)

    assert approved["ready"] is True
    assert approved["experiment_id"] == AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID
    assert approved["execution_hash"] != r2["execution_hash"]
    assert approved["campaign_cost_control"]["descriptor"]["experiment_id"] == (
        AC_FIXED_BUNDLE_CORRECTED_EXPERIMENT_ID
    )
    assert not qualification_module._execution_plan_matches(
        plan={**approved, "schema_version": "experiment-execution-plan-v1"},
        manifest=v1_manifest,
    )
    assert qualification_module._execution_plan_matches(
        plan={**approved, "schema_version": "experiment-execution-plan-v1"},
        manifest=manifest,
    )


def test_r5_split_budget_paid_plan_round_trips_through_capability_revalidation(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from patchloop.evals import qualification as qualification_module

    _r1, _r2 = ac_preflights
    r5_binding = {
        **EVALUATOR_V2_SOURCE_QUALIFICATION,
        "successor_suite_hash": "sha256:" + "e" * 64,
        "base_suite_hash": eval_runner._suite_hash(eval_runner.load_suite(R5_SUITE)),
    }
    monkeypatch.setattr(
        eval_runner,
        "_validated_ac_evaluator_v2_source_qualification",
        lambda suite: (
            dict(r5_binding)
            if suite.experiment_id == AC_FIXED_BUNDLE_CAPABILITY_CORRECTED_EXPERIMENT_ID
            else None
        ),
    )
    candidate = eval_runner.preflight_suite(R5_SUITE)
    approved = eval_runner.preflight_suite(
        R5_SUITE,
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
    )
    plan = {**approved, "schema_version": "experiment-execution-plan-v1"}
    v1_manifest = _paid_boundary_manifest(approved, row_index=0, suite_path=R5_SUITE)
    manifest = _bind_paid_boundary_manifest_v2(v1_manifest, approved)

    assert approved["ready"] is True
    assert approved["experiment_id"] == AC_FIXED_BUNDLE_CAPABILITY_CORRECTED_EXPERIMENT_ID
    assert approved["runtime_contract"]["budget"] == (
        eval_runner.GPT54_MINI_AC_SPLIT_TOKEN_BUDGET.model_dump(mode="json")
    )
    assert qualification_module._execution_plan_matches(plan=plan, manifest=manifest)

    legacy_budget_plan = copy.deepcopy(plan)
    legacy_budget_plan["runtime_contract"]["budget"] = (
        eval_runner.GPT54_MINI_CONDITION_NEUTRAL_V2_BUDGET.model_dump(mode="json")
    )
    assert not qualification_module._execution_plan_matches(
        plan=legacy_budget_plan,
        manifest=manifest,
    )


def test_paid_boundary_revalidates_the_source_qualified_v2_authority(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
    from patchloop.evals import evaluator_v2_source_qualification as source_q

    _r1, candidate = ac_preflights
    approved = eval_runner.preflight_suite(
        R2_SUITE,
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
    )
    manifest = _bind_paid_boundary_manifest_v2(
        _paid_boundary_manifest(approved, row_index=0),
        approved,
    )
    plan_binding = eval_runner._persist_preflight_plan(approved)
    authorization = issue_live_execution_authorization(
        approved["execution_hash"],
        root=eval_runner.runtime_root(),
    )
    authority = object()
    observed: list[tuple[Any, Any, Any]] = []

    monkeypatch.setattr(
        source_q,
        "validate_evaluator_v2_ac_paid_authority",
        lambda checked_manifest, checked_authority, qualification: observed.append(
            (checked_manifest, checked_authority, qualification)
        ),
    )
    monkeypatch.setattr(
        AgentRunner,
        "_require_full_schedule_reservation",
        staticmethod(lambda *_args, **_kwargs: {}),
    )

    AgentRunner._require_live_authorization(
        manifest,
        authorization,
        evaluator_v2_authority=authority,
    )

    assert authorization.plan_path == plan_binding["path"]
    assert observed == [(manifest, authority, approved["evaluator_v2_qualification"])]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_qualification_hash", "sha256:" + "0" * 64),
        ("evaluator_source_hash", "sha256:" + "0" * 64),
        ("successor_suite_hash", "sha256:" + "0" * 64),
        ("base_suite_hash", "sha256:" + "0" * 64),
        ("base_suite_matches", False),
        ("unexpected", "sha256:" + "0" * 64),
    ],
)
def test_r2_paid_plan_rejects_tampered_successor_binding(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    field: str,
    value: Any,
) -> None:
    from patchloop.evals import qualification as qualification_module

    _r1, candidate = ac_preflights
    approved = eval_runner.preflight_suite(
        R2_SUITE,
        approve_live_cost=True,
        approved_execution_hash=candidate["execution_hash"],
    )
    manifest = _bind_paid_boundary_manifest_v2(
        _paid_boundary_manifest(approved, row_index=0),
        approved,
    )
    tampered = copy.deepcopy({**approved, "schema_version": "experiment-execution-plan-v1"})
    tampered["evaluator_v2_qualification"][field] = value

    assert not qualification_module._execution_plan_matches(
        plan=tampered,
        manifest=manifest,
    )


def test_r2_context_requires_the_exact_cost_control_hash(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    _r1, r2 = ac_preflights
    row = r2["schedule"][0]
    common = {
        "experiment_id": AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        "purpose": "development-validation-ac-readiness",
        "suite_hash": r2["suite_hash"],
        "execution_hash": r2["execution_hash"],
        "dataset_manifest_hash": r2["dataset"]["manifest_hash"],
        "dataset_role": DatasetRole.DEVELOPMENT_VALIDATION,
        "schedule_seed": 20260723,
        "schedule_order": 1,
        "schedule_row_id": row["schedule_row_id"],
        "repetition": 1,
    }
    with pytest.raises(ValueError, match="requires campaign_cost_control_hash"):
        ExperimentRunContext(**common)
    context = ExperimentRunContext(
        **common,
        campaign_cost_control_hash=r2["campaign_cost_control"]["content_hash"],
    )
    assert context.campaign_cost_control_hash == r2["campaign_cost_control"]["content_hash"]


def test_ac_full_schedule_journal_reconciles_all_four_rows(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
) -> None:
    _r1, r2 = ac_preflights
    journal, evidence, qualification = _full_schedule_journal(tmp_path, r2)
    assert journal.read_bytes().endswith(b"\n")
    assert len(evidence) == 4
    assert qualification == {
        "schema_version": "ac-fixed-bundle-full-schedule-cost-qualification-v1",
        "passed": True,
        "fully_settled": True,
        "campaign_cost_control_hash": r2["campaign_cost_control"]["content_hash"],
        "schedule_hash": r2["schedule_hash"],
        "full_schedule_reserved": True,
        "reserved_runs": 4,
        "settled_runs": 4,
        "not_started_runs": 0,
        "unsettled_runs": 0,
        "accrued_cost_nanos": 4 * 907_500,
        "full_schedule_reserve_nanos": 54_450_000_000,
        "hard_cap_nanos": 55_000_000_000,
        "cost_censoring_events": 0,
        "live_resume_supported": False,
    }


def test_ac_unavailable_settlement_seals_an_inconclusive_cost_qualification(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
) -> None:
    _r1, r2 = ac_preflights
    journal = tmp_path / "experiments" / "journals" / f"{r2['experiment_id']}.jsonl"
    control = r2["campaign_cost_control"]
    control_hash = control["content_hash"]
    execution_hash = r2["execution_hash"]
    plan_hash = "sha256:" + "b" * 64
    sequence = 1
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=sequence,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": r2["experiment_id"],
            "purpose": r2["purpose"],
            "execution_hash": execution_hash,
            "schedule_hash": r2["schedule_hash"],
            "execution_plan_hash": plan_hash,
            "campaign_cost_control_hash": control_hash,
        },
    )
    sequence += 1
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=sequence,
        previous_event_hash=previous,
        event_type="FullScheduleCostReserved",
        payload={
            "experiment_id": r2["experiment_id"],
            "execution_hash": execution_hash,
            "execution_plan_hash": plan_hash,
            "campaign_cost_control_hash": control_hash,
            "schedule_hash": r2["schedule_hash"],
            "schedule_row_ids": [row["schedule_row_id"] for row in r2["schedule"]],
            "per_run_reserve_nanos": 13_612_500_000,
            "full_schedule_reserve_nanos": 54_450_000_000,
            "hard_cap_nanos": 55_000_000_000,
            "row_reserve_count": 4,
            "cost_censoring_allowed": False,
        },
    )
    first = r2["schedule"][0]
    run_id = "run_ac_unavailable"
    sequence += 1
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=sequence,
        previous_event_hash=previous,
        event_type="RunStarted",
        payload={
            **_row_identity(first),
            "run_id": run_id,
            "execution_hash": execution_hash,
            "execution_plan_hash": plan_hash,
            "campaign_cost_control_hash": control_hash,
        },
    )
    sequence += 1
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=sequence,
        previous_event_hash=previous,
        event_type="RunTerminal",
        payload={
            **_row_identity(first),
            "run_id": run_id,
            "outcome_kind": None,
            "model_cost_usd": 0.0,
            "execution_hash": execution_hash,
            "execution_plan_hash": plan_hash,
            "campaign_cost_control_hash": control_hash,
            "usage_evidence": None,
            "usage_evidence_hash": None,
            "usage_reconciliation_passed": False,
            "infrastructure_error_type": "CostAccountingUnavailable",
            "qualification_hash": None,
            "qualification_error_type": None,
            "diagnostic_status": None,
            "diagnostic_error_type": None,
        },
    )
    sequence += 1
    previous = eval_runner._append_campaign_event(
        journal,
        sequence=sequence,
        previous_event_hash=previous,
        event_type="RunCostSettlementUnavailable",
        payload={
            **_row_identity(first),
            "run_id": run_id,
            "execution_hash": execution_hash,
            "execution_plan_hash": plan_hash,
            "campaign_cost_control_hash": control_hash,
            "reason_type": "CostAccountingUnavailable",
            "accrued_cost_nanos": 0,
            "usage_evidence_hash": None,
            "full_schedule_reserve_remains_held": True,
        },
    )
    for row in r2["schedule"][1:]:
        sequence += 1
        previous = eval_runner._append_campaign_event(
            journal,
            sequence=sequence,
            previous_event_hash=previous,
            event_type="RunNotStarted",
            payload={
                **_row_identity(row),
                "reason_type": "InfrastructureFailureHalt",
                "execution_hash": execution_hash,
                "execution_plan_hash": plan_hash,
                "campaign_cost_control_hash": control_hash,
            },
        )
    qualification = eval_runner._full_schedule_cost_journal_evidence(
        journal,
        control,
        run_root=tmp_path,
        expected_execution_hash=execution_hash,
        expected_execution_plan_hash=plan_hash,
        expected_schedule=r2["schedule"],
    )
    assert qualification["passed"] is False
    assert qualification["fully_settled"] is False
    assert qualification["unsettled_runs"] == 1
    assert qualification["not_started_runs"] == 3
    assert qualification["settled_runs"] == 0
    assert qualification["accrued_cost_nanos"] == 0


def test_ac_runtime_persists_inconclusive_result_when_durable_settlement_fails(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _r1, r2 = ac_preflights
    started_run_ids: list[str] = []
    runner_authorities: list[object] = []
    qualifier_authorities: list[object] = []
    evaluator_v2_authority = object()

    class FakeRunner:
        def start(
            self,
            _task: str,
            *,
            manifest,
            evaluator_v2_authority,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            started_run_ids.append(manifest.run_id)
            runner_authorities.append(evaluator_v2_authority)
            return {
                "run_id": manifest.run_id,
                "agent_submission_status": "completed",
                "evaluation_status": "completed",
                "scope_compliant_success": False,
                "official": True,
                "verdicts": {
                    "hidden_tests": "fail",
                    "regression_tests": "pass",
                    "scope_policy": "pass",
                    "safety_policy": "pass",
                },
                "outcome_kind": "task_failure",
                "terminal_error": None,
                "usage": _usage().model_dump(mode="json"),
            }

    monkeypatch.setattr(eval_runner, "AgentRunner", FakeRunner)
    monkeypatch.setattr(
        eval_runner,
        "_load_ac_evaluator_v2_runtime_authorities",
        lambda _suite, _qualification: {
            "moto-query-scanned-count": evaluator_v2_authority,
            "babel-strict-grouped-decimal-trailing-zeroes": evaluator_v2_authority,
        },
    )
    monkeypatch.setattr(
        eval_runner,
        "_bind_evaluator_v2_manifest",
        lambda manifest, _package, authority: (
            manifest if authority is evaluator_v2_authority else None
        ),
    )

    def qualified_terminal(
        run_id: str,
        _task: str,
        *,
        evaluator_v2_authority,
    ) -> dict[str, Any]:
        qualifier_authorities.append(evaluator_v2_authority)
        return {
            "schema_version": "trace-qualification-v1",
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": True,
            "outcome_kind": "task_failure",
            "qualification_hash": "sha256:" + "1" * 64,
            "source_evidence_hash": "sha256:" + "2" * 64,
            "usage_reconciliation": _projection("usage_reconciliation"),
            "persisted_result": _projection("persisted_result"),
        }

    monkeypatch.setattr(
        eval_runner,
        "_qualify_terminal_run",
        qualified_terminal,
    )

    def unavailable_durable_usage(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise ContractError("durable settlement fixture is unavailable")

    monkeypatch.setattr(
        eval_runner,
        "_load_full_schedule_durable_usage_evidence",
        unavailable_durable_usage,
    )
    approved_preflight = copy.deepcopy(r2)
    approved_preflight["approval"] = {
        **approved_preflight["approval"],
        "invocation_approve_live_cost": True,
        "invocation_approved_execution_hash": r2["execution_hash"],
        "matches_execution_hash": True,
    }
    approved_preflight["blockers"] = []
    approved_preflight["ready"] = True
    # Exercise only the post-preflight runtime path with a fake provider boundary.
    monkeypatch.setattr(
        eval_runner,
        "preflight_suite",
        lambda *_args, **_kwargs: copy.deepcopy(approved_preflight),
    )

    result = eval_runner.evaluate_suite(
        R2_SUITE,
        approve_live_cost=True,
        approved_execution_hash=r2["execution_hash"],
    )

    assert len(started_run_ids) == 1
    assert runner_authorities == [evaluator_v2_authority]
    assert qualifier_authorities == [evaluator_v2_authority]
    assert result["halt_reason"]["type"] == "InfrastructureFailureHalt"
    assert result["runs"][0]["infrastructure_error"]["type"] == ("CostAccountingUnavailable")
    assert result["not_started_runs"] == 3
    assert result["campaign_cost_qualification"]["passed"] is False
    assert result["campaign_cost_qualification"]["fully_settled"] is False
    assert result["campaign_cost_qualification"]["settled_runs"] == 0
    assert result["campaign_cost_qualification"]["unsettled_runs"] == 1
    assert result["campaign_cost_qualification"]["not_started_runs"] == 3
    assert result["completion_gate"]["passed"] is False
    assert result["completion_gate"]["analysis_ready"] is False
    assert result["completion_gate"]["disposition"] == "inconclusive"

    output = Path(result["path"])
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["campaign_cost_qualification"] == result["campaign_cost_qualification"]
    assert persisted["completion_gate"] == result["completion_gate"]

    journal_path = Path(result["campaign_journal"]["path"])
    journal = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert [event["event_type"] for event in journal] == [
        "CampaignStarted",
        "FullScheduleCostReserved",
        "RunStarted",
        "RunTerminal",
        "RunCostSettlementUnavailable",
        "RunNotStarted",
        "RunNotStarted",
        "RunNotStarted",
        "CampaignCompleted",
    ]
    terminal = next(event for event in journal if event["event_type"] == "RunTerminal")
    assert terminal["payload"]["usage_evidence"] is None
    assert terminal["payload"]["usage_reconciliation_passed"] is False
    assert (
        eval_runner._full_schedule_cost_journal_evidence(
            journal_path,
            result["campaign_cost_control"],
            run_root=tmp_path / "runtime",
            expected_execution_hash=result["execution_hash"],
            expected_execution_plan_hash=result["execution_plan"]["artifact_hash"],
            expected_schedule=r2["schedule"],
        )
        == result["campaign_cost_qualification"]
    )


def test_displayed_model_cost_is_not_usage_authority() -> None:
    usage = _usage()
    evidence = eval_runner._full_schedule_usage_evidence(
        usage,
        experiment_id=AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        run_id="run_ac_cost_display",
        schedule_row_id="sha256:" + "1" * 64,
        qualification_hash="sha256:" + "2" * 64,
        source_evidence_hash="sha256:" + "3" * 64,
        persisted_result_hash="sha256:" + "4" * 64,
    )
    assert "model_cost_usd" not in evidence["descriptor"]["usage"]
    assert evidence["descriptor"]["token_derived_cost_nanos"] == 907_500


def test_ac_usage_evidence_rejects_fully_rehashed_unknown_descriptor() -> None:
    evidence = eval_runner._full_schedule_usage_evidence(
        _usage(),
        experiment_id=AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        run_id="run_ac_unknown_descriptor",
        schedule_row_id="sha256:" + "1" * 64,
        qualification_hash="sha256:" + "2" * 64,
        source_evidence_hash="sha256:" + "3" * 64,
        persisted_result_hash="sha256:" + "4" * 64,
    )
    evidence["descriptor"]["unknown_authority"] = True
    evidence["content_hash"] = sha256_text(canonical_json(evidence["descriptor"]))
    with pytest.raises(ContractError, match="durable usage evidence descriptor"):
        eval_runner._validate_full_schedule_usage_evidence(
            evidence,
            experiment_id=AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
            run_id="run_ac_unknown_descriptor",
            schedule_row_id="sha256:" + "1" * 64,
        )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("exact", True),
        ("usage-projection-failed", False),
        ("persisted-result-failed", False),
        ("settlement-unavailable", False),
        ("durable-evidence-missing", False),
        ("durable-hash-missing", False),
        ("durable-hash-mismatch", False),
    ],
)
def test_terminal_settlement_reconciliation_uses_final_durable_state(
    mutation: str,
    expected: bool,
) -> None:
    evidence = eval_runner._full_schedule_usage_evidence(
        _usage(),
        experiment_id=AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        run_id="run_ac_final_settlement_state",
        schedule_row_id="sha256:" + "1" * 64,
        qualification_hash="sha256:" + "2" * 64,
        source_evidence_hash="sha256:" + "3" * 64,
        persisted_result_hash="sha256:" + "4" * 64,
    )
    values = {
        "usage_reconciliation_passed": mutation != "usage-projection-failed",
        "persisted_result_passed": mutation != "persisted-result-failed",
        "settled_run_cost_nanos": (None if mutation == "settlement-unavailable" else 907_500),
        "durable_usage_evidence": (None if mutation == "durable-evidence-missing" else evidence),
        "usage_evidence_hash": (
            None
            if mutation == "durable-hash-missing"
            else "sha256:" + "f" * 64
            if mutation == "durable-hash-mismatch"
            else evidence["content_hash"]
        ),
    }
    assert eval_runner._terminal_cost_settlement_reconciliation_passed(**values) is expected


@pytest.mark.parametrize("tamper", ["unknown-payload", "backward-chronology"])
def test_ac_journal_rejects_fully_rehashed_payload_or_chronology_tamper(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    tamper: str,
) -> None:
    _r1, r2 = ac_preflights
    journal, evidence_by_run, _qualification = _full_schedule_journal(tmp_path, r2)
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    if tamper == "unknown-payload":
        events[2]["payload"]["unknown_authority"] = False
    else:
        events[2]["recorded_at"] = "2000-01-01T00:00:00+00:00"
    previous: str | None = None
    for event in events:
        event["previous_event_hash"] = previous
        body = {key: value for key, value in event.items() if key != "event_hash"}
        event["event_hash"] = sha256_text(canonical_json(body))
        previous = event["event_hash"]
    journal.write_text(
        "".join(f"{canonical_json(event)}\n" for event in events),
        encoding="utf-8",
        newline="",
    )
    expected = (
        "event payload fields differ" if tamper == "unknown-payload" else "chronology is invalid"
    )
    with pytest.raises(ContractError, match=expected):
        eval_runner._full_schedule_cost_journal_evidence(
            journal,
            r2["campaign_cost_control"],
            run_root=tmp_path,
            expected_execution_hash=r2["execution_hash"],
            expected_execution_plan_hash="sha256:" + "b" * 64,
            expected_schedule=r2["schedule"],
            durable_usage_resolver=(lambda run_id, _row_id, _root: evidence_by_run[run_id]),
        )


@pytest.mark.parametrize(
    ("mutation", "expected_field"),
    [
        (lambda rows: rows.pop(), "terminal_runs"),
        (lambda rows: rows.reverse(), "schedule_binding_passed"),
        (
            lambda rows: rows[1].__setitem__("run_id", rows[0]["run_id"]),
            "schedule_binding_passed",
        ),
        (
            lambda rows: rows[2]["result"].__setitem__("official", False),
            "official_evaluator_runs",
        ),
        (
            lambda rows: rows[0]["result"].update(
                {
                    "agent_submission_status": "failed",
                    "evaluation_status": "not_run",
                    "official": False,
                    "outcome_kind": "agent_failure",
                    "terminal_error": {"type": "ModelGenerationBudgetError"},
                }
            ),
            "official_evaluator_runs",
        ),
        (
            lambda rows: rows[3]["qualification"]["readiness_checks"].pop(
                "campaign_full_schedule_cost_contract"
            ),
            "official_evaluator_runs",
        ),
        (
            lambda rows: rows[0]["result"].__setitem__("scope_compliant_success", False),
            "official_evaluator_runs",
        ),
        (
            lambda rows: rows[1]["result"].__setitem__(
                "verdicts",
                {
                    "hidden_tests": "pass",
                    "regression_tests": "pass",
                    "scope_policy": "pass",
                    "safety_policy": "pass",
                },
            ),
            "official_evaluator_runs",
        ),
        (
            lambda rows: rows[1]["result"].__setitem__(
                "verdicts",
                {
                    "hidden_tests": "not_run",
                    "regression_tests": "not_run",
                    "scope_policy": "not_run",
                    "safety_policy": "not_run",
                },
            ),
            "official_evaluator_runs",
        ),
    ],
)
def test_ac_completion_gate_fails_closed_on_matrix_tamper(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    mutation,
    expected_field: str,
) -> None:
    _r1, r2 = ac_preflights
    _journal, _evidence, cost = _full_schedule_journal(tmp_path, r2)
    rows = _completion_rows(r2)
    mutation(rows)
    gate = eval_runner._ac_fixed_bundle_completion_gate(
        rows,
        expected_execution_hash=r2["execution_hash"],
        expected_schedule=r2["schedule"],
        expected_campaign_cost_control_hash=r2["campaign_cost_control"]["content_hash"],
        campaign_cost_qualification=cost,
    )
    assert gate["passed"] is False
    assert gate["analysis_ready"] is False
    assert gate["disposition"] == "inconclusive"
    if expected_field.endswith("runs"):
        assert gate[expected_field] != 4
    else:
        assert not gate[expected_field]


def test_ac_completion_gate_accepts_four_official_task_failures(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
) -> None:
    _r1, r2 = ac_preflights
    _journal, _evidence, cost = _full_schedule_journal(tmp_path, r2)
    gate = eval_runner._completion_gate(
        eval_runner.load_suite(R2_SUITE),
        _completion_rows(r2, all_failures=True),
        expected_execution_hash=r2["execution_hash"],
        expected_schedule=r2["schedule"],
        expected_campaign_cost_control_hash=r2["campaign_cost_control"]["content_hash"],
        campaign_cost_qualification=cost,
    )
    assert gate is not None
    assert gate["passed"] is True
    assert gate["analysis_ready"] is True
    assert gate["official_evaluator_runs"] == 4
    assert gate["task_successes"] == 0
    assert gate["task_failures"] == 4
    assert gate["task_success_required"] is False
    assert gate["memory_effect_claim_authorized"] is False


def test_ac_completion_gate_accepts_qualified_v2_receipts_without_mutating_raw_official(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
) -> None:
    _r1, r2 = ac_preflights
    _journal, _evidence, cost = _full_schedule_journal(tmp_path, r2)
    rows = _completion_rows(r2, all_failures=True)
    for index, row in enumerate(rows, start=1):
        source_hash = "sha256:" + f"{index + 8:x}" * 64
        result = row["result"]
        result.update(
            {
                "schema_version": "run-result-v2",
                "official": False,
                "evaluator_contract": {"evaluator_source_hash": source_hash},
                "safety_evidence_bundle_hash": "sha256:" + "a" * 64,
                "safety_evidence": [{"control": control} for control in range(4)],
                "verifier_results": [{"check_type": "safety", "state": "pass"} for _ in range(4)],
            }
        )
        row["qualification"].update(
            {
                "evaluator_version": "v2",
                "evaluator_v2_receipt_hash": "sha256:" + "b" * 64,
                "evaluator_v2_receipt_file_hash": "sha256:" + "c" * 64,
                "evaluator_v2_source_hash": source_hash,
                "evaluator_v2_source_qualification_hash": "sha256:" + "d" * 64,
                "evaluator_v2_runtime_authenticated": True,
                "evaluator_v2_completion_eligible": True,
            }
        )

    gate = eval_runner._ac_fixed_bundle_completion_gate(
        rows,
        expected_execution_hash=r2["execution_hash"],
        expected_schedule=r2["schedule"],
        expected_campaign_cost_control_hash=r2["campaign_cost_control"]["content_hash"],
        campaign_cost_qualification=cost,
    )
    assert gate["passed"] is True
    assert gate["official_evaluator_runs"] == 4
    assert all(row["result"]["official"] is False for row in rows)

    rows[0]["qualification"]["evaluator_v2_completion_eligible"] = False
    failed = eval_runner._ac_fixed_bundle_completion_gate(
        rows,
        expected_execution_hash=r2["execution_hash"],
        expected_schedule=r2["schedule"],
        expected_campaign_cost_control_hash=r2["campaign_cost_control"]["content_hash"],
        campaign_cost_qualification=cost,
    )
    assert failed["passed"] is False
    assert failed["official_evaluator_runs"] == 3


def test_campaign_append_rejects_stale_tail_and_preserves_bytes(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    first = eval_runner._append_campaign_event(
        journal,
        sequence=1,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={"experiment_id": AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID},
    )
    before = journal.read_bytes()
    with pytest.raises(ContractError, match="tail is invalid"):
        eval_runner._append_campaign_event(
            journal,
            sequence=2,
            previous_event_hash="sha256:" + "f" * 64,
            event_type="FullScheduleCostReserved",
            payload={},
        )
    assert journal.read_bytes() == before
    assert first == json.loads(before.decode("utf-8"))["event_hash"]
    assert sha256_bytes(before).startswith("sha256:")


def test_r2_terminal_projection_includes_cost_contract_but_r1_does_not() -> None:
    check_ids = {
        "submission_lifecycle",
        "prompt_token_integrity",
        "usage_reconciliation",
        "persisted_result",
        "disabled_call_guard_contract",
        "approved_execution_plan",
        "ac_fixed_runtime_contract",
        "fixed_memory_delivery_integrity",
        "pricing_start_freshness",
        "campaign_full_schedule_cost_contract",
    }
    payload = {
        "experiment_id": AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        "memory_condition": "structured",
        "checks": [{"check_id": check_id, "passed": True, "details": {}} for check_id in check_ids],
    }
    r2 = eval_runner._terminal_qualification_summary(payload)
    assert r2["memory_condition"] == "structured"
    assert set(r2["readiness_checks"]) == check_ids
    assert r2["readiness_checks"]["campaign_full_schedule_cost_contract"]["passed"] is True

    payload["experiment_id"] = AC_FIXED_BUNDLE_READINESS_EXPERIMENT_ID
    r1 = eval_runner._terminal_qualification_summary(payload)
    assert "campaign_full_schedule_cost_contract" not in r1["readiness_checks"]


def test_r2_terminal_qualification_adds_read_only_recomputation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from patchloop.evals import qualification as qualification_module

    payload = {
        "schema_version": "trace-qualification-v1",
        "run_id": "run_ac_r2_recompute",
        "experiment_id": AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID,
        "qualification_hash": "sha256:" + "1" * 64,
        "checks": [],
    }
    monkeypatch.setattr(eval_runner, "runtime_root", lambda: tmp_path)
    monkeypatch.setattr(
        qualification_module,
        "qualify_run",
        lambda *_args, **_kwargs: copy.deepcopy(payload),
    )
    monkeypatch.setattr(
        qualification_module,
        "load_trace_qualification",
        lambda *_args, **_kwargs: copy.deepcopy(payload),
    )
    summary = eval_runner._qualify_terminal_run(
        "run_ac_r2_recompute",
        "tasks/dev-validation/moto-query-scanned-count/public.yaml",
    )
    assert summary["read_only_recomputation"] == {
        "schema_version": "qualification-read-only-recomputation-v1",
        "matched": True,
        "qualification_hash": payload["qualification_hash"],
        "recomputed_qualification_hash": payload["qualification_hash"],
    }


def test_live_plan_loader_rejects_plan_swap_after_capability_issuance(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    original = b'{"schema_version":"experiment-execution-plan-v1"}'
    plan_path.write_bytes(original)
    authorization = LiveExecutionAuthorization(
        execution_hash="sha256:" + "1" * 64,
        plan_path=str(plan_path),
        plan_hash=sha256_bytes(original),
        _guard=object(),
    )
    assert _load_live_execution_plan(authorization)["schema_version"] == (
        "experiment-execution-plan-v1"
    )
    plan_path.write_bytes(b'{"schema_version":"tampered"}')
    with pytest.raises(ContractError, match="unavailable"):
        _load_live_execution_plan(authorization)


def _paid_boundary_manifest(
    preflight: dict[str, Any],
    *,
    row_index: int,
    suite_path: Path = R2_SUITE,
):
    from patchloop.contracts import MemoryCondition
    from patchloop.runtime import build_manifest
    from patchloop.task_loader import load_task_package

    suite = eval_runner.load_suite(suite_path)
    schedule_row = preflight["schedule"][row_index]
    task_row = next(row for row in preflight["tasks"] if row["task_id"] == schedule_row["task_id"])
    item = {**task_row, **schedule_row}
    task_path = Path(item["task"])
    package = load_task_package(task_path.parent if task_path.is_file() else task_path)
    experiment = ExperimentRunContext(
        experiment_id=suite.experiment_id,
        purpose=suite.purpose,
        suite_hash=preflight["suite_hash"],
        execution_hash=preflight["execution_hash"],
        dataset_manifest_hash=preflight["dataset"]["manifest_hash"],
        dataset_role=DatasetRole(item["dataset_role"]),
        schedule_seed=suite.seed,
        schedule_order=item["order"],
        schedule_row_id=item["schedule_row_id"],
        repetition=item["repetition"],
        campaign_cost_control_hash=preflight["campaign_cost_control"]["content_hash"],
    )
    manifest = build_manifest(
        package,
        run_id=f"run_ac_paid_boundary_{row_index + 1}",
        provider=suite.model,
        model_id=suite.model_id,
        memory_condition=MemoryCondition(item["condition"]),
        memory_policy_version=suite.memory_policy_version or "v1",
        sandbox_backend="docker",
        budget=suite.budget,
        agent_image_digest=item["evaluator_image_digest"],
        evaluator_image_digest=item["evaluator_image_digest"],
        input_price_per_million_usd=suite.input_price_per_million_usd,
        cached_input_price_per_million_usd=suite.cached_input_price_per_million_usd,
        cache_write_input_price_per_million_usd=(suite.cache_write_input_price_per_million_usd),
        output_price_per_million_usd=suite.output_price_per_million_usd,
        reasoning_effort=suite.reasoning_effort,
        reasoning_mode=suite.reasoning_mode,
        service_tier=suite.service_tier,
        transport_max_retries=suite.transport_max_retries,
        max_output_tokens=suite.max_output_tokens,
        experiment_context=experiment,
    )
    return manifest


def _bind_paid_boundary_manifest_v2(manifest, preflight: dict[str, Any]):
    from patchloop.agent.tools import TOOL_SCHEMAS_V2
    from patchloop.task_loader import load_task_package
    from patchloop.verifier.receipt import EvaluatorV2QualificationAuthority
    from patchloop.verifier.runtime_evidence import (
        EvaluatorV2RuntimeAuthority,
        build_evaluator_safety_contract_v2,
        evaluator_v2_manifest_runtime_tuple_hash,
    )

    package = load_task_package(Path("tasks/dev-validation") / manifest.task_id)
    markers = (b"offline-v2-paid-boundary-marker",)
    qualification = preflight["evaluator_v2_qualification"]
    contract = build_evaluator_safety_contract_v2(
        package=package,
        tool_schemas=TOOL_SCHEMAS_V2,
        private_markers=markers,
    )
    authority = EvaluatorV2QualificationAuthority(
        runtime=EvaluatorV2RuntimeAuthority(
            safety_contract=contract,
            evaluator_source_hash=qualification["evaluator_source_hash"],
            tool_schemas=tuple(TOOL_SCHEMAS_V2),
            private_markers=markers,
        ),
        suite_hash=qualification["successor_suite_hash"],
        source_qualification_hash=qualification["source_qualification_hash"],
        runtime_tuple_hash=evaluator_v2_manifest_runtime_tuple_hash(manifest),
    )
    return eval_runner._bind_evaluator_v2_manifest(manifest, package, authority)


def _paid_boundary_case(
    root: Path,
    preflight: dict[str, Any],
    *,
    row_index: int = 0,
    reserve_overrides: dict[str, Any] | None = None,
    prior_settled: bool = True,
    forged_prior_cost_delta: int = 0,
) -> tuple[Any, LiveExecutionAuthorization, dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = _paid_boundary_manifest(preflight, row_index=row_index)
    experiment_id = AC_FIXED_BUNDLE_COST_COMPLETION_EXPERIMENT_ID
    journal_path = root / "experiments" / "journals" / f"{experiment_id}.jsonl"
    plan_path = root / "experiments" / "plans" / "paid-boundary-plan.json"
    plan = {
        "schema_version": "experiment-execution-plan-v1",
        "execution_hash": preflight["execution_hash"],
        "campaign_cost_control": preflight["campaign_cost_control"],
        "schedule": preflight["schedule"],
        "journal_path": str(journal_path.resolve(strict=False)),
    }
    plan_bytes = canonical_json(plan).encode("utf-8")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_bytes(plan_bytes)
    authorization = LiveExecutionAuthorization(
        execution_hash=preflight["execution_hash"],
        plan_path=str(plan_path.resolve(strict=False)),
        plan_hash=sha256_bytes(plan_bytes),
        _guard=object(),
    )
    plan_content_hash = sha256_text(canonical_json(plan))
    control_hash = preflight["campaign_cost_control"]["content_hash"]
    schedule_row_ids = [row["schedule_row_id"] for row in preflight["schedule"]]
    sequence = 1
    previous = eval_runner._append_campaign_event(
        journal_path,
        sequence=sequence,
        previous_event_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": experiment_id,
            "purpose": preflight["purpose"],
            "execution_hash": preflight["execution_hash"],
            "execution_plan_hash": plan_content_hash,
            "schedule_hash": preflight["schedule_hash"],
            "campaign_cost_control_hash": control_hash,
        },
    )
    reserve_payload = {
        "experiment_id": experiment_id,
        "execution_hash": preflight["execution_hash"],
        "execution_plan_hash": plan_content_hash,
        "campaign_cost_control_hash": control_hash,
        "schedule_hash": preflight["schedule_hash"],
        "schedule_row_ids": schedule_row_ids,
        "per_run_reserve_nanos": 13_612_500_000,
        "full_schedule_reserve_nanos": 54_450_000_000,
        "hard_cap_nanos": 55_000_000_000,
        "row_reserve_count": 4,
        "cost_censoring_allowed": False,
    }
    reserve_payload.update(reserve_overrides or {})
    sequence += 1
    previous = eval_runner._append_campaign_event(
        journal_path,
        sequence=sequence,
        previous_event_hash=previous,
        event_type="FullScheduleCostReserved",
        payload=reserve_payload,
    )
    evidence_by_run: dict[str, dict[str, Any]] = {}
    accrued = 0
    for prior_index in range(row_index):
        prior_row = preflight["schedule"][prior_index]
        prior_run_id = f"run_ac_paid_boundary_{prior_index + 1}"
        prior_evidence = eval_runner._full_schedule_usage_evidence(
            _usage(),
            experiment_id=experiment_id,
            run_id=prior_run_id,
            schedule_row_id=prior_row["schedule_row_id"],
            qualification_hash="sha256:" + f"{prior_index + 1:x}" * 64,
            source_evidence_hash="sha256:" + f"{prior_index + 5:x}" * 64,
            persisted_result_hash="sha256:" + f"{prior_index + 9:x}" * 64,
        )
        evidence_by_run[prior_run_id] = prior_evidence
        run_cost = eval_runner._validate_full_schedule_usage_evidence(
            prior_evidence,
            experiment_id=experiment_id,
            run_id=prior_run_id,
            schedule_row_id=prior_row["schedule_row_id"],
        )
        sequence += 1
        previous = eval_runner._append_campaign_event(
            journal_path,
            sequence=sequence,
            previous_event_hash=previous,
            event_type="RunStarted",
            payload={
                **_row_identity(prior_row),
                "run_id": prior_run_id,
                "execution_hash": preflight["execution_hash"],
                "execution_plan_hash": plan_content_hash,
                "campaign_cost_control_hash": control_hash,
            },
        )
        sequence += 1
        previous = eval_runner._append_campaign_event(
            journal_path,
            sequence=sequence,
            previous_event_hash=previous,
            event_type="RunTerminal",
            payload={
                **_row_identity(prior_row),
                "run_id": prior_run_id,
                "execution_hash": preflight["execution_hash"],
                "execution_plan_hash": plan_content_hash,
                "campaign_cost_control_hash": control_hash,
                "usage_evidence": prior_evidence,
                "usage_evidence_hash": prior_evidence["content_hash"],
                "usage_reconciliation_passed": True,
                "outcome_kind": "task_failure",
                "model_cost_usd": 0.0009075,
                "infrastructure_error_type": None,
                "qualification_hash": prior_evidence["descriptor"]["qualification_hash"],
                "qualification_error_type": None,
                "diagnostic_status": None,
                "diagnostic_error_type": None,
            },
        )
        if prior_settled:
            sequence += 1
            recorded_cost = run_cost + forged_prior_cost_delta
            previous = eval_runner._append_campaign_event(
                journal_path,
                sequence=sequence,
                previous_event_hash=previous,
                event_type="RunCostSettled",
                payload={
                    **_row_identity(prior_row),
                    "run_id": prior_run_id,
                    "execution_hash": preflight["execution_hash"],
                    "execution_plan_hash": plan_content_hash,
                    "campaign_cost_control_hash": control_hash,
                    "actual_run_cost_nanos": recorded_cost,
                    "usage_evidence_hash": prior_evidence["content_hash"],
                    "usage_reconciliation_passed": True,
                    "accrued_cost_nanos_before": accrued,
                    "accrued_cost_nanos_after": accrued + recorded_cost,
                    "remaining_reserved_rows_after": 4 - prior_index - 1,
                },
            )
            accrued += recorded_cost
    current_row = preflight["schedule"][row_index]
    sequence += 1
    eval_runner._append_campaign_event(
        journal_path,
        sequence=sequence,
        previous_event_hash=previous,
        event_type="RunStarted",
        payload={
            **_row_identity(current_row),
            "run_id": manifest.run_id,
            "execution_hash": preflight["execution_hash"],
            "execution_plan_hash": plan_content_hash,
            "campaign_cost_control_hash": control_hash,
        },
    )
    return manifest, authorization, plan, evidence_by_run


def test_paid_boundary_accepts_exact_row_one_reservation(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
) -> None:
    from patchloop.agent.runner import AgentRunner

    _r1, r2 = ac_preflights
    root = tmp_path / "paid-boundary-row-one"
    manifest, authorization, plan, _evidence = _paid_boundary_case(root, r2)
    AgentRunner._require_full_schedule_reservation(
        manifest,
        authorization,
        plan=plan,
        runner_root=root,
    )


@pytest.mark.parametrize(
    "reserve_overrides",
    [
        {"per_run_reserve_nanos": 13_612_499_999},
        {"row_reserve_count": 3},
    ],
)
def test_paid_boundary_rejects_wrong_per_run_reserve_or_row_count(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    reserve_overrides: dict[str, Any],
) -> None:
    from patchloop.agent.runner import AgentRunner

    _r1, r2 = ac_preflights
    root = tmp_path / "paid-boundary-wrong-reserve"
    manifest, authorization, plan, _evidence = _paid_boundary_case(
        root,
        r2,
        reserve_overrides=reserve_overrides,
    )
    with pytest.raises(ContractError, match="reserve does not match"):
        AgentRunner._require_full_schedule_reservation(
            manifest,
            authorization,
            plan=plan,
            runner_root=root,
        )


def test_paid_boundary_rejects_runner_root_mismatch(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
) -> None:
    from patchloop.agent.runner import AgentRunner

    _r1, r2 = ac_preflights
    root = tmp_path / "paid-boundary-root"
    manifest, authorization, plan, _evidence = _paid_boundary_case(root, r2)
    with pytest.raises(ContractError, match="runtime root"):
        AgentRunner._require_full_schedule_reservation(
            manifest,
            authorization,
            plan=plan,
            runner_root=tmp_path / "different-runtime-root",
        )


def test_paid_boundary_rejects_unsettled_prior_row(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
) -> None:
    from patchloop.agent.runner import AgentRunner

    _r1, r2 = ac_preflights
    root = tmp_path / "paid-boundary-unsettled"
    manifest, authorization, plan, _evidence = _paid_boundary_case(
        root,
        r2,
        row_index=1,
        prior_settled=False,
    )
    with pytest.raises(ContractError, match="prior row prefix is not fully settled"):
        AgentRunner._require_full_schedule_reservation(
            manifest,
            authorization,
            plan=plan,
            runner_root=root,
        )


@pytest.mark.parametrize("durable_mode", ["forged-cost", "missing-evidence"])
def test_paid_boundary_rejects_forged_or_non_durable_prior_settlement(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    durable_mode: str,
) -> None:
    from patchloop.agent.runner import AgentRunner

    _r1, r2 = ac_preflights
    root = tmp_path / f"paid-boundary-{durable_mode}"
    manifest, authorization, plan, evidence_by_run = _paid_boundary_case(
        root,
        r2,
        row_index=1,
        forged_prior_cost_delta=1 if durable_mode == "forged-cost" else 0,
    )
    if durable_mode == "missing-evidence":

        def missing(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise ContractError("durable evidence is absent")

        monkeypatch.setattr(
            eval_runner,
            "_load_full_schedule_durable_usage_evidence",
            missing,
        )
    else:
        monkeypatch.setattr(
            eval_runner,
            "_load_full_schedule_durable_usage_evidence",
            lambda run_id, _row_id, _root, **_kwargs: evidence_by_run[run_id],
        )
    with pytest.raises(ContractError, match="prior row .*settlement is invalid"):
        AgentRunner._require_full_schedule_reservation(
            manifest,
            authorization,
            plan=plan,
            runner_root=root,
        )


@pytest.mark.parametrize("tamper", ["unknown-payload", "backward-chronology"])
def test_paid_boundary_rejects_rehashed_shape_or_chronology_tamper(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    tamper: str,
) -> None:
    from patchloop.agent.runner import AgentRunner

    _r1, r2 = ac_preflights
    root = tmp_path / f"paid-boundary-{tamper}"
    manifest, authorization, plan, _evidence = _paid_boundary_case(root, r2)
    journal = Path(plan["journal_path"])
    events = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    if tamper == "unknown-payload":
        events[1]["payload"]["unknown_authority"] = False
    else:
        events[1]["recorded_at"] = "2000-01-01T00:00:00+00:00"
    previous: str | None = None
    for event in events:
        event["previous_event_hash"] = previous
        body = {key: value for key, value in event.items() if key != "event_hash"}
        event["event_hash"] = sha256_text(canonical_json(body))
        previous = event["event_hash"]
    journal.write_text(
        "".join(f"{canonical_json(event)}\n" for event in events),
        encoding="utf-8",
        newline="",
    )
    expected = "payload fields differ" if tamper == "unknown-payload" else "chronology"
    with pytest.raises(ContractError, match=expected):
        AgentRunner._require_full_schedule_reservation(
            manifest,
            authorization,
            plan=plan,
            runner_root=root,
        )


def test_agent_start_rejects_invalid_reserve_before_model_adapter(
    ac_preflights: tuple[dict[str, Any], dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from patchloop.agent import runner as agent_runner_module
    from patchloop.agent.runner import AgentRunner

    _r1, r2 = ac_preflights
    root = tmp_path / "paid-boundary-start-order"
    manifest, authorization, plan, _evidence = _paid_boundary_case(
        root,
        r2,
        reserve_overrides={"row_reserve_count": 3},
    )
    authorization = LiveExecutionAuthorization(
        execution_hash=authorization.execution_hash,
        plan_path=authorization.plan_path,
        plan_hash=authorization.plan_hash,
        _guard=agent_runner_module._LIVE_AUTHORIZATION_GUARD,
    )
    monkeypatch.setattr(
        AgentRunner,
        "_live_plan_matches_manifest",
        staticmethod(lambda *_args, **_kwargs: True),
    )
    runner = AgentRunner(root)
    model_adapter_calls = 0

    def forbidden_model_adapter(*_args: Any, **_kwargs: Any) -> Any:
        nonlocal model_adapter_calls
        model_adapter_calls += 1
        raise AssertionError("model adapter must not be constructed before reserve validation")

    monkeypatch.setattr(runner, "_model_adapter", forbidden_model_adapter)
    task = next(row["task"] for row in r2["tasks"] if row["task_id"] == manifest.task_id)
    with pytest.raises(ContractError, match="reserve does not match"):
        runner.start(
            task,
            model="openai",
            manifest=manifest,
            live_authorization=authorization,
        )
    assert model_adapter_calls == 0
    assert plan["journal_path"]
