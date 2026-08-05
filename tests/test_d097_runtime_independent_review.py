from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import Usage
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

EXPERIMENT_ID = eval_runner.CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID
EXECUTION_HASH = "sha256:" + "e" * 64
EXECUTION_PLAN_HASH = "sha256:" + "d" * 64


def _hash(index: int) -> str:
    return f"sha256:{index:064x}"


def _schedule() -> list[dict[str, Any]]:
    return [
        {
            "order": index,
            "schedule_row_id": _hash(index),
            "task_id": task_id,
            "split": "dev-train",
            "dataset_role": "memory-development",
            "condition": "no_memory",
            "repetition": repetition,
        }
        for index, (task_id, repetition) in enumerate(
            eval_runner.CONDITION_NEUTRAL_NO_MEMORY_ROW_ORDER,
            start=1,
        )
    ]


def _cost_control(schedule: list[dict[str, Any]]) -> dict[str, Any]:
    descriptor = {
        "schema_version": (
            eval_runner.CONDITION_NEUTRAL_FULL_SCHEDULE_COST_POLICY_SCHEMA
        ),
        "experiment_id": EXPERIMENT_ID,
        "policy": deepcopy(eval_runner.CONDITION_NEUTRAL_FULL_SCHEDULE_COST_POLICY),
        "schedule_size": 12,
        "schedule_hash": sha256_text(canonical_json(schedule)),
        "schedule_row_ids": [row["schedule_row_id"] for row in schedule],
        "campaign_local_source_cap": True,
        "full_schedule_reservation_required": True,
        "row_bound_reservations": True,
        "deterministic_settlement_required": True,
        "row_cost_censoring_allowed": False,
        "full_schedule_worst_rate_reserve_usd": 163.35,
        "full_schedule_reserve_nanos": 163_350_000_000,
        "per_run_reserve_nanos": 13_612_500_000,
        "hard_cap_nanos": 164_000_000_000,
        "completion_guaranteed": False,
        "invoice_or_free_tier_claim": False,
    }
    return {
        "schema_version": (
            eval_runner.CONDITION_NEUTRAL_FULL_SCHEDULE_COST_CONTROL_SCHEMA
        ),
        "descriptor": descriptor,
        "content_hash": sha256_text(canonical_json(descriptor)),
    }


def _readiness_checks() -> dict[str, dict[str, Any]]:
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
    return {
        check_id: {
            "schema_version": eval_runner.QUALIFICATION_GATE_CHECK_PROJECTION_SCHEMA,
            "check_id": check_id,
            "check_count": 1,
            "passed": True,
        }
        for check_id in check_ids
    }


def _official_rows(schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, expected in enumerate(schedule, start=1):
        run_id = f"run_d097_independent_{index}"
        outcome = "resolved" if index == 1 else "task_failure"
        qualification_hash = _hash(100 + index)
        qualification = {
            "run_id": run_id,
            "task_id": expected["task_id"],
            "schedule_row_id": expected["schedule_row_id"],
            "execution_hash": EXECUTION_HASH,
            "experiment_id": EXPERIMENT_ID,
            "purpose": "memory-development-no-memory",
            "dataset_role": "memory-development",
            "qualified": True,
            "trace_integrity_passed": True,
            "leakage_scan_passed": True,
            "source_evidence_hash": _hash(200 + index),
            "evaluation_reached": True,
            "outcome_kind": outcome,
            "memory_candidate_eligible": outcome == "task_failure",
            "qualification_hash": qualification_hash,
            "readiness_checks": _readiness_checks(),
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
        result = {
            "run_id": run_id,
            "agent_submission_status": "completed",
            "evaluation_status": "completed",
            "official": True,
            "outcome_kind": outcome,
            "terminal_error": None,
            "scope_compliant_success": outcome == "resolved",
        }
        rows.append(
            {
                **expected,
                "attempt_status": "terminal",
                "run_id": run_id,
                "result": result,
                "qualification": qualification,
                "infrastructure_error": None,
                "qualification_error": None,
                "diagnostic_error": None,
            }
        )
    return rows


def _make_budget_terminal(
    row: dict[str, Any],
    *,
    reason_code: str,
    schema_version: str,
) -> None:
    row["result"].update(
        {
            "agent_submission_status": "failed",
            "evaluation_status": "not_run",
            "official": False,
            "outcome_kind": "agent_failure",
            "terminal_error": {
                "type": "ModelGenerationBudgetError",
                "code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                "details": {
                    "schema_version": schema_version,
                    "reason_code": reason_code,
                    "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                    "generation_started": False,
                },
            },
            "scope_compliant_success": False,
        }
    )
    row["qualification"].update(
        {
            "evaluation_reached": False,
            "outcome_kind": "agent_failure",
            "memory_candidate_eligible": False,
        }
    )


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
        "accrued_cost_nanos": 0,
        "full_schedule_reserve_nanos": 163_350_000_000,
        "hard_cap_nanos": 164_000_000_000,
        "cost_censoring_events": 0,
        "live_resume_supported": False,
    }


def _completion_gate(
    rows: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
    cost_control: dict[str, Any],
    *,
    cost_qualification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return eval_runner._d097_completion_gate(
        rows,
        expected_execution_hash=EXECUTION_HASH,
        expected_schedule=schedule,
        expected_campaign_cost_control_hash=cost_control["content_hash"],
        campaign_cost_qualification=(
            cost_qualification
            if cost_qualification is not None
            else _cost_qualification(schedule, cost_control)
        ),
    )


def test_d097_completion_gate_accepts_mixed_official_and_budget_terminals() -> None:
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    rows = _official_rows(schedule)
    _make_budget_terminal(
        rows[1],
        reason_code="exact_request_budget_exceeded",
        schema_version="model-generation-block-v1",
    )
    _make_budget_terminal(
        rows[2],
        reason_code="wall_clock_budget_exhausted",
        schema_version="model-generation-block-v3",
    )

    gate = _completion_gate(rows, schedule, cost_control)

    assert gate["passed"] is True
    assert gate["official_evaluator_runs"] == 10
    assert gate["budget_terminal_runs"] == 2
    assert gate["task_successes"] == 1
    assert gate["task_success_required"] is False
    assert gate["terminal_branches_mutually_exclusive_and_exhaustive"] is True
    assert gate["comparison_denominator_eligible"] is True


def test_d097_completion_gate_rejects_reversed_schedule_rows() -> None:
    schedule = _schedule()
    cost_control = _cost_control(schedule)

    gate = _completion_gate(
        list(reversed(_official_rows(schedule))),
        schedule,
        cost_control,
    )

    assert gate["passed"] is False
    assert gate["schedule_binding_passed"] is False


def test_d097_completion_gate_rejects_a_duplicate_run_identity() -> None:
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    rows = _official_rows(schedule)
    rows[1]["run_id"] = rows[0]["run_id"]
    rows[1]["result"]["run_id"] = rows[0]["run_id"]
    rows[1]["qualification"]["run_id"] = rows[0]["run_id"]

    gate = _completion_gate(rows, schedule, cost_control)

    assert gate["passed"] is False
    assert gate["schedule_binding_passed"] is False


def test_d097_completion_gate_rejects_a_foreign_cost_control_hash() -> None:
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    qualification = _cost_qualification(schedule, cost_control)
    qualification["campaign_cost_control_hash"] = _hash(999)

    gate = _completion_gate(
        _official_rows(schedule),
        schedule,
        cost_control,
        cost_qualification=qualification,
    )

    assert gate["passed"] is False
    assert gate["cost_settlement_passed"] is False


def _append_event(
    path: Path,
    *,
    sequence: int,
    previous_hash: str | None,
    event_type: str,
    payload: dict[str, Any],
) -> str:
    return eval_runner._append_campaign_event(
        path,
        sequence=sequence,
        previous_event_hash=previous_hash,
        event_type=event_type,
        payload=payload,
    )


def _build_journal(
    root: Path,
    schedule: list[dict[str, Any]],
    cost_control: dict[str, Any],
    *,
    reserve_execution_hash: str = EXECUTION_HASH,
    duplicate_first_terminal: bool = False,
) -> tuple[
    Path,
    str,
    int,
    Callable[[str, str, Path], dict[str, Any]],
]:
    journal = root / "experiments" / "journals" / f"{EXPERIMENT_ID}.jsonl"
    control_hash = cost_control["content_hash"]
    sequence = 1
    previous_hash = _append_event(
        journal,
        sequence=sequence,
        previous_hash=None,
        event_type="CampaignStarted",
        payload={
            "experiment_id": EXPERIMENT_ID,
            "purpose": "memory-development-no-memory",
            "execution_hash": EXECUTION_HASH,
            "schedule_hash": sha256_text(canonical_json(schedule)),
            "execution_plan_hash": EXECUTION_PLAN_HASH,
            "campaign_cost_control_hash": control_hash,
        },
    )
    sequence += 1
    previous_hash = _append_event(
        journal,
        sequence=sequence,
        previous_hash=previous_hash,
        event_type="FullScheduleCostReserved",
        payload={
            "experiment_id": EXPERIMENT_ID,
            "execution_hash": reserve_execution_hash,
            "execution_plan_hash": EXECUTION_PLAN_HASH,
            "campaign_cost_control_hash": control_hash,
            "schedule_hash": sha256_text(canonical_json(schedule)),
            "schedule_row_ids": [row["schedule_row_id"] for row in schedule],
            "per_run_reserve_nanos": 13_612_500_000,
            "full_schedule_reserve_nanos": 163_350_000_000,
            "hard_cap_nanos": 164_000_000_000,
            "row_reserve_count": 12,
            "cost_censoring_allowed": False,
        },
    )
    evidence_by_run_and_row: dict[tuple[str, str], dict[str, Any]] = {}
    for index, expected in enumerate(schedule, start=1):
        run_id = f"run_d097_journal_{index}"
        identity = {
            key: expected[key]
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
        evidence = eval_runner._d097_usage_evidence(
            Usage(),
            run_id=run_id,
            schedule_row_id=expected["schedule_row_id"],
            qualification_hash=_hash(300 + index),
            source_evidence_hash=_hash(400 + index),
            persisted_result_hash=_hash(500 + index),
        )
        evidence_by_run_and_row[(run_id, expected["schedule_row_id"])] = evidence
        common = {
            **identity,
            "run_id": run_id,
            "execution_hash": EXECUTION_HASH,
            "execution_plan_hash": EXECUTION_PLAN_HASH,
            "campaign_cost_control_hash": control_hash,
        }
        sequence += 1
        previous_hash = _append_event(
            journal,
            sequence=sequence,
            previous_hash=previous_hash,
            event_type="RunStarted",
            payload=common,
        )
        terminal = {
            **common,
            "outcome_kind": "task_failure",
            "model_cost_usd": 0.0,
            "usage_evidence": evidence,
            "usage_evidence_hash": evidence["content_hash"],
            "usage_reconciliation_passed": True,
            "infrastructure_error_type": None,
            "qualification_hash": _hash(300 + index),
            "qualification_error_type": None,
            "diagnostic_status": None,
            "diagnostic_error_type": None,
        }
        sequence += 1
        previous_hash = _append_event(
            journal,
            sequence=sequence,
            previous_hash=previous_hash,
            event_type="RunTerminal",
            payload=terminal,
        )
        if duplicate_first_terminal and index == 1:
            sequence += 1
            previous_hash = _append_event(
                journal,
                sequence=sequence,
                previous_hash=previous_hash,
                event_type="RunTerminal",
                payload=terminal,
            )
        sequence += 1
        previous_hash = _append_event(
            journal,
            sequence=sequence,
            previous_hash=previous_hash,
            event_type="RunCostSettled",
            payload={
                **common,
                "accrued_cost_nanos_before": 0,
                "actual_run_cost_nanos": 0,
                "usage_evidence_hash": evidence["content_hash"],
                "usage_reconciliation_passed": True,
                "accrued_cost_nanos_after": 0,
                "remaining_reserved_rows_after": 12 - index,
            },
        )

    def resolve(run_id: str, row_id: str, _root: Path) -> dict[str, Any]:
        return evidence_by_run_and_row[(run_id, row_id)]

    return journal, previous_hash, sequence, resolve


def _verify_journal(
    journal: Path,
    root: Path,
    schedule: list[dict[str, Any]],
    cost_control: dict[str, Any],
    resolver: Callable[[str, str, Path], dict[str, Any]],
) -> dict[str, Any]:
    return eval_runner._full_schedule_cost_journal_evidence(
        journal,
        cost_control,
        run_root=root,
        expected_execution_hash=EXECUTION_HASH,
        expected_execution_plan_hash=EXECUTION_PLAN_HASH,
        expected_schedule=schedule,
        durable_usage_resolver=resolver,
    )


def test_d097_journal_rejects_a_rehashed_foreign_execution_reserve(
    tmp_path: Path,
) -> None:
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    journal, _, _, resolver = _build_journal(
        tmp_path,
        schedule,
        cost_control,
        reserve_execution_hash=_hash(998),
    )

    with pytest.raises(ContractError, match="full-schedule reserve event"):
        _verify_journal(journal, tmp_path, schedule, cost_control, resolver)


def test_d097_journal_rejects_a_duplicate_terminal_event(tmp_path: Path) -> None:
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    journal, _, _, resolver = _build_journal(
        tmp_path,
        schedule,
        cost_control,
        duplicate_first_terminal=True,
    )

    with pytest.raises(ContractError, match="terminal usage evidence"):
        _verify_journal(journal, tmp_path, schedule, cost_control, resolver)


def test_d097_final_journal_reverification_binds_the_persisted_result(
    tmp_path: Path,
) -> None:
    schedule = _schedule()
    cost_control = _cost_control(schedule)
    journal, previous_hash, sequence, resolver = _build_journal(
        tmp_path,
        schedule,
        cost_control,
    )
    qualification = _verify_journal(
        journal,
        tmp_path,
        schedule,
        cost_control,
        resolver,
    )
    assert qualification["fully_settled"] is True

    result = {
        "schema_version": "experiment-result-v2",
        "experiment_id": EXPERIMENT_ID,
        "execution_hash": EXECUTION_HASH,
        "schedule_hash": sha256_text(canonical_json(schedule)),
        "campaign_cost_control": cost_control,
        "campaign_cost_qualification": qualification,
    }
    result_path = tmp_path / "experiments" / f"{EXPERIMENT_ID}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_bytes = json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8")
    result_path.write_bytes(result_bytes)
    _append_event(
        journal,
        sequence=sequence + 1,
        previous_hash=previous_hash,
        event_type="CampaignCompleted",
        payload={
            "experiment_id": EXPERIMENT_ID,
            "execution_hash": EXECUTION_HASH,
            "execution_plan_hash": EXECUTION_PLAN_HASH,
            "result_hash": sha256_bytes(result_bytes),
            "completed_runs": 12,
            "infrastructure_errors": 0,
            "not_started_runs": 0,
            "campaign_cost_control_hash": cost_control["content_hash"],
            "campaign_cost_qualification": qualification,
        },
    )

    recomputed = _verify_journal(
        journal,
        tmp_path,
        schedule,
        cost_control,
        resolver,
    )

    assert recomputed == qualification
    result["tampered_after_completion"] = True
    result_path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ContractError, match="final campaign seal"):
        _verify_journal(journal, tmp_path, schedule, cost_control, resolver)
