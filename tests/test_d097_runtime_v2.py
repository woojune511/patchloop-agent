from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.agent.runner import AgentRunner
from patchloop.contracts import (
    Budget,
    DatasetRole,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    RunManifest,
    Usage,
)
from patchloop.errors import ContractError
from patchloop.evals import budget as budget_diagnostics
from patchloop.evals import qualification
from patchloop.evals import runner as eval_runner
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_text

SUITE_PATH = Path("experiments/dev-no-memory-condition-neutral-3000k-20260805-r1.yaml")
EXECUTION_HASH = "sha256:" + "a" * 64
PLAN_HASH = "sha256:" + "b" * 64
QUALIFICATION_HASH = "sha256:" + "c" * 64
SOURCE_HASH = "sha256:" + "d" * 64
RESULT_HASH = "sha256:" + "e" * 64


def _schedule() -> list[dict[str, Any]]:
    rows = []
    for order, (task_id, repetition) in enumerate(
        eval_runner.CONDITION_NEUTRAL_NO_MEMORY_ROW_ORDER,
        start=1,
    ):
        row = {
            "order": order,
            "task_id": task_id,
            "split": "dev-train",
            "dataset_role": "memory-development",
            "condition": "no_memory",
            "repetition": repetition,
        }
        row["schedule_row_id"] = sha256_text(canonical_json(row))
        rows.append(row)
    return rows


def _cost_control(schedule: list[dict[str, Any]]) -> dict[str, Any]:
    suite = eval_runner.load_suite(SUITE_PATH)
    result = eval_runner._campaign_cost_control(
        suite,
        {
            "per_run_cost_reserve_usd": 13.6125,
            "budget_upper_bound_usd": 163.35,
        },
        schedule_size=12,
        schedule_hash=sha256_text(canonical_json(schedule)),
        schedule_row_ids=[row["schedule_row_id"] for row in schedule],
    )
    assert result is not None
    return result


def _projection(check_id: str) -> dict[str, Any]:
    return {
        "schema_version": "qualification-gate-check-projection-v1",
        "check_id": check_id,
        "check_count": 1,
        "passed": True,
    }


def _gate_row(
    schedule_row: dict[str, Any],
    *,
    budget_terminal: bool = False,
) -> dict[str, Any]:
    run_id = f"run_d097_{schedule_row['order']:02d}"
    outcome = "agent_failure" if budget_terminal else "task_failure"
    result = {
        "run_id": run_id,
        "agent_submission_status": "failed" if budget_terminal else "completed",
        "evaluation_status": "not_run" if budget_terminal else "completed",
        "scope_compliant_success": False,
        "official": not budget_terminal,
        "outcome_kind": outcome,
        "terminal_error": (
            {
                "type": "ModelGenerationBudgetError",
                "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                "details": {
                    "schema_version": "model-generation-block-v1",
                    "reason_code": "exact_request_budget_exceeded",
                    "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                    "generation_started": False,
                },
            }
            if budget_terminal
            else None
        ),
    }
    check_ids = {
        "submission_lifecycle",
        "prompt_token_integrity",
        "usage_reconciliation",
        "persisted_result",
        "disabled_call_guard_contract",
        "approved_execution_plan",
        "comparison_runtime_contract",
        "pricing_start_freshness",
        "campaign_full_schedule_cost_contract",
    }
    row = {
        **schedule_row,
        "attempt_status": "terminal",
        "run_id": run_id,
        "usage": {},
        "result": result,
        "infrastructure_error": None,
        "qualification_error": None,
        "diagnostic_error": None,
        "qualification": {
            "run_id": run_id,
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "evaluation_reached": not budget_terminal,
            "outcome_kind": outcome,
            "purpose": "memory-development-no-memory",
            "experiment_id": (eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID),
            "dataset_role": "memory-development",
            "task_id": schedule_row["task_id"],
            "execution_hash": EXECUTION_HASH,
            "schedule_row_id": schedule_row["schedule_row_id"],
            "memory_candidate_eligible": not budget_terminal,
            "source_evidence_hash": SOURCE_HASH,
            "qualification_hash": QUALIFICATION_HASH,
            "readiness_checks": {check_id: _projection(check_id) for check_id in check_ids},
            "model_or_tool_call_budget_blocks": {
                "schema_version": "call-budget-block-projection-v1",
                "source_check_count": 1,
                "source_check_passed": True,
                "event_sequences": [],
            },
            "read_only_recomputation": {
                "schema_version": "qualification-read-only-recomputation-v1",
                "matched": True,
                "qualification_hash": QUALIFICATION_HASH,
                "recomputed_qualification_hash": QUALIFICATION_HASH,
            },
        },
    }
    return row


def _cost_qualification(
    schedule: list[dict[str, Any]],
    cost_control: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "campaign-full-schedule-cost-qualification-v1",
        "passed": True,
        "fully_settled": True,
        "campaign_cost_control_hash": cost_control["content_hash"],
        "schedule_hash": sha256_text(canonical_json(schedule)),
        "full_schedule_reserved": True,
        "reserved_runs": 12,
        "settled_runs": 12,
        "not_started_runs": 0,
        "accrued_cost_nanos": 9_000,
        "full_schedule_reserve_nanos": 163_350_000_000,
        "hard_cap_nanos": 164_000_000_000,
        "cost_censoring_events": 0,
        "live_resume_supported": False,
    }


def _completion_gate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    suite = eval_runner.load_suite(SUITE_PATH)
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    gate = eval_runner._completion_gate(
        suite,
        rows,
        expected_execution_hash=EXECUTION_HASH,
        expected_schedule=schedule,
        expected_campaign_cost_control_hash=cost_control["content_hash"],
        campaign_cost_qualification=_cost_qualification(schedule, cost_control),
    )
    assert gate is not None
    return gate


def _manifest() -> RunManifest:
    package = load_task_package(Path("tasks/dev-train/pyfakefs-makedirs-parent-traversal"))
    context = ExperimentRunContext(
        experiment_id=eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
        purpose=ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
        suite_hash="sha256:" + "1" * 64,
        execution_hash=EXECUTION_HASH,
        campaign_cost_control_hash="sha256:" + "2" * 64,
        dataset_manifest_hash="sha256:" + "3" * 64,
        dataset_role=DatasetRole.MEMORY_DEVELOPMENT,
        schedule_seed=20260723,
        schedule_order=1,
        schedule_row_id="sha256:" + "4" * 64,
        repetition=1,
    )
    return build_manifest(
        package,
        run_id="run_d097_manifest",
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        memory_condition=MemoryCondition.NO_MEMORY,
        sandbox_backend="docker",
        budget=Budget(
            max_model_calls=None,
            max_tool_calls=None,
            max_total_tokens=3_000_000,
            wall_clock_timeout_seconds=3_600,
        ),
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        experiment_context=context,
    )


def _append(
    path: Path,
    state: dict[str, Any],
    event_type: str,
    payload: dict[str, Any],
) -> None:
    state["sequence"] += 1
    state["event_hash"] = eval_runner._append_campaign_event(
        path,
        sequence=state["sequence"],
        previous_event_hash=state["event_hash"],
        event_type=event_type,
        payload=payload,
    )


def _journal_fixture(
    tmp_path: Path,
) -> tuple[
    Path,
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, dict[str, Any]],
]:
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    journal = tmp_path / "campaign.jsonl"
    state: dict[str, Any] = {"sequence": 0, "event_hash": None}
    descriptor = cost_control["descriptor"]
    _append(
        journal,
        state,
        "CampaignStarted",
        {
            "experiment_id": eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
            "purpose": "memory-development-no-memory",
            "execution_hash": EXECUTION_HASH,
            "schedule_hash": descriptor["schedule_hash"],
            "execution_plan_hash": PLAN_HASH,
            "campaign_cost_control_hash": cost_control["content_hash"],
        },
    )
    _append(
        journal,
        state,
        "FullScheduleCostReserved",
        {
            "experiment_id": eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
            "execution_hash": EXECUTION_HASH,
            "execution_plan_hash": PLAN_HASH,
            "campaign_cost_control_hash": cost_control["content_hash"],
            "schedule_hash": descriptor["schedule_hash"],
            "schedule_row_ids": descriptor["schedule_row_ids"],
            "per_run_reserve_nanos": 13_612_500_000,
            "full_schedule_reserve_nanos": 163_350_000_000,
            "hard_cap_nanos": 164_000_000_000,
            "row_reserve_count": 12,
            "cost_censoring_allowed": False,
        },
    )
    durable: dict[str, dict[str, Any]] = {}
    accrued = 0
    for index, row in enumerate(schedule):
        run_id = f"run_d097_journal_{index + 1:02d}"
        usage = Usage(
            model_calls=1,
            tool_calls=1,
            input_tokens=1,
            output_tokens=0,
            wall_clock_ms=1,
        )
        evidence = eval_runner._d097_usage_evidence(
            usage,
            run_id=run_id,
            schedule_row_id=row["schedule_row_id"],
            qualification_hash=QUALIFICATION_HASH,
            source_evidence_hash=SOURCE_HASH,
            persisted_result_hash=RESULT_HASH,
        )
        durable[run_id] = evidence
        common = {
            **row,
            "run_id": run_id,
            "execution_hash": EXECUTION_HASH,
            "execution_plan_hash": PLAN_HASH,
            "campaign_cost_control_hash": cost_control["content_hash"],
        }
        _append(journal, state, "RunStarted", common)
        _append(
            journal,
            state,
            "RunTerminal",
            {
                **common,
                "outcome_kind": "task_failure",
                "infrastructure_error_type": None,
                "usage_evidence": evidence,
                "usage_evidence_hash": evidence["content_hash"],
                "usage_reconciliation_passed": True,
            },
        )
        run_cost = 750
        _append(
            journal,
            state,
            "RunCostSettled",
            {
                **common,
                "accrued_cost_nanos_before": accrued,
                "actual_run_cost_nanos": run_cost,
                "usage_evidence_hash": evidence["content_hash"],
                "usage_reconciliation_passed": True,
                "accrued_cost_nanos_after": accrued + run_cost,
                "remaining_reserved_rows_after": 11 - index,
            },
        )
        accrued += run_cost
    return journal, schedule, cost_control, state, durable


def _reconcile(
    journal: Path,
    schedule: list[dict[str, Any]],
    cost_control: dict[str, Any],
    tmp_path: Path,
    durable: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return eval_runner._full_schedule_cost_journal_evidence(
        journal,
        cost_control,
        run_root=tmp_path,
        expected_execution_hash=EXECUTION_HASH,
        expected_execution_plan_hash=PLAN_HASH,
        expected_schedule=schedule,
        durable_usage_resolver=lambda run_id, _row_id, _root: copy.deepcopy(durable[run_id]),
    )


def test_d097_exact_suite_runtime_and_d096_binding_are_live_source_ready() -> None:
    suite = eval_runner.load_suite(SUITE_PATH)
    contract = eval_runner._experiment_runtime_contract(
        suite,
        harness_git_commit="f" * 40,
    )

    assert eval_runner._is_condition_neutral_runtime_v2_profile(suite)
    assert contract is not None
    assert contract["schema_version"] == "condition-neutral-comparison-runtime-contract-v2"
    assert contract["budget"] == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
    }
    assert contract["baseline_admission"]["admission_id"] == (
        "memory-development-no-memory-12-row-v1"
    )
    assert qualification._condition_neutral_resource_policy_v2_artifact_valid()


def test_d097_exact_manifest_is_selected_by_all_runtime_consumers() -> None:
    manifest = _manifest()

    assert AgentRunner._is_condition_neutral_runtime_v2_manifest(manifest)
    assert qualification._condition_neutral_runtime_v2_manifest_matches(manifest)
    diagnostic = budget_diagnostics.calculate_budget_pressure(manifest, [])
    assert diagnostic["configured_limits"] == {
        "model_calls": None,
        "tool_calls": None,
        "total_tokens": 3_000_000,
        "wall_clock_ms": 3_600_000,
    }


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("experiment", "schedule_order"), 2),
        (("experiment", "campaign_cost_control_hash"), "sha256:bad"),
        (("budget", "max_total_tokens"), 2_999_999),
        (("budget", "wall_clock_timeout_seconds"), 3_599),
    ],
)
def test_d097_manifest_identity_rejects_near_match(
    path: tuple[str, ...],
    value: Any,
) -> None:
    payload = _manifest().model_dump(mode="json")
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValidationError):
        RunManifest.model_validate(payload)
    with pytest.raises(ValueError, match="D-097"):
        budget_diagnostics.calculate_budget_pressure(payload, [])


def test_d097_completion_gate_accepts_official_and_canonical_budget_partition() -> None:
    schedule = _schedule()
    rows = [_gate_row(row) for row in schedule]
    rows[-1] = _gate_row(schedule[-1], budget_terminal=True)

    gate = _completion_gate(rows)

    assert gate["passed"] is True
    assert gate["official_evaluator_runs"] == 11
    assert gate["budget_terminal_runs"] == 1
    assert gate["terminal_branches_mutually_exclusive_and_exhaustive"] is True
    assert gate["comparison_denominator_eligible"] is True
    assert gate["memory_review_eligible"] is True
    assert gate["memory_admission_unlocked"] is False
    assert gate["task_successes"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        "neither",
        "wrong_reason",
        "generation_started",
        "model_call_block",
        "infrastructure",
        "not_started",
        "duplicate_run_id",
        "wrong_row_order",
    ],
)
def test_d097_completion_gate_fails_closed_on_terminal_or_binding_tamper(
    mutation: str,
) -> None:
    schedule = _schedule()
    rows = [_gate_row(row) for row in schedule]
    rows[-1] = _gate_row(schedule[-1], budget_terminal=True)
    target = rows[-1]
    if mutation == "neither":
        target["result"]["official"] = True
    elif mutation == "wrong_reason":
        target["result"]["terminal_error"]["details"]["reason_code"] = "other"
    elif mutation == "generation_started":
        target["result"]["terminal_error"]["details"]["generation_started"] = True
    elif mutation == "model_call_block":
        target["result"]["terminal_error"]["details"].update(
            {
                "schema_version": "model-generation-block-v3",
                "reason_code": "model_call_budget_exhausted",
            }
        )
    elif mutation == "infrastructure":
        target["infrastructure_error"] = {"type": "DockerError"}
    elif mutation == "not_started":
        target["attempt_status"] = "not_started"
    elif mutation == "duplicate_run_id":
        target["run_id"] = rows[0]["run_id"]
        target["result"]["run_id"] = rows[0]["run_id"]
        target["qualification"]["run_id"] = rows[0]["run_id"]
    else:
        rows[-1], rows[-2] = rows[-2], rows[-1]

    gate = _completion_gate(rows)

    assert gate["passed"] is False
    assert gate["comparison_denominator_eligible"] is False


def test_d097_journal_reconciles_before_and_after_final_campaign_seal(
    tmp_path: Path,
) -> None:
    journal, schedule, cost_control, state, durable = _journal_fixture(tmp_path)
    qualification_payload = _reconcile(
        journal,
        schedule,
        cost_control,
        tmp_path,
        durable,
    )
    assert qualification_payload["fully_settled"] is True
    result = {
        "experiment_id": eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
        "execution_hash": EXECUTION_HASH,
        "schedule_hash": sha256_text(canonical_json(schedule)),
        "campaign_cost_control": cost_control,
        "campaign_cost_qualification": qualification_payload,
    }
    result_path = (
        tmp_path
        / "experiments"
        / f"{eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID}.json"
    )
    result_path.parent.mkdir(parents=True)
    result_bytes = json.dumps(result, indent=2).encode()
    result_path.write_bytes(result_bytes)
    _append(
        journal,
        state,
        "CampaignCompleted",
        {
            "experiment_id": eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
            "execution_hash": EXECUTION_HASH,
            "execution_plan_hash": PLAN_HASH,
            "result_hash": sha256_bytes(result_bytes),
            "completed_runs": 12,
            "infrastructure_errors": 0,
            "not_started_runs": 0,
            "campaign_cost_control_hash": cost_control["content_hash"],
            "campaign_cost_qualification": qualification_payload,
        },
    )

    assert _reconcile(journal, schedule, cost_control, tmp_path, durable) == (qualification_payload)


@pytest.mark.parametrize(
    ("event_index", "field"),
    [
        (0, "execution_hash"),
        (0, "execution_plan_hash"),
        (1, "execution_hash"),
        (1, "execution_plan_hash"),
        (2, "execution_hash"),
        (2, "execution_plan_hash"),
    ],
)
def test_d097_journal_rejects_foreign_execution_or_plan_binding(
    tmp_path: Path,
    event_index: int,
    field: str,
) -> None:
    journal, schedule, cost_control, _state, durable = _journal_fixture(tmp_path)
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    events[event_index]["payload"][field] = "sha256:" + "9" * 64
    previous = None
    for sequence, event in enumerate(events, start=1):
        event["sequence"] = sequence
        event["previous_event_hash"] = previous
        body = {key: value for key, value in event.items() if key != "event_hash"}
        event["event_hash"] = sha256_text(canonical_json(body))
        previous = event["event_hash"]
    journal.write_text("".join(json.dumps(event) + "\n" for event in events))

    with pytest.raises(ContractError):
        _reconcile(journal, schedule, cost_control, tmp_path, durable)


def test_d097_journal_rejects_duplicate_terminal_even_when_rehashed(
    tmp_path: Path,
) -> None:
    journal, schedule, cost_control, _state, durable = _journal_fixture(tmp_path)
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    events.insert(4, copy.deepcopy(events[3]))
    previous = None
    for sequence, event in enumerate(events, start=1):
        event["sequence"] = sequence
        event["previous_event_hash"] = previous
        body = {key: value for key, value in event.items() if key != "event_hash"}
        event["event_hash"] = sha256_text(canonical_json(body))
        previous = event["event_hash"]
    journal.write_text("".join(json.dumps(event) + "\n" for event in events))

    with pytest.raises(ContractError, match="terminal usage evidence"):
        _reconcile(journal, schedule, cost_control, tmp_path, durable)
