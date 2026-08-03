from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from patchloop.contracts import Usage
from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.util import canonical_json, sha256_text

D087_CAP_NANOS = 25_000_000_000
D087_RESERVE_NANOS = 7_312_500_000
HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)
HASH_C = "sha256:" + ("c" * 64)


def _cost_control(
    *,
    cap_nanos: int = D087_CAP_NANOS,
    reserve_nanos: int = D087_RESERVE_NANOS,
) -> dict[str, Any]:
    descriptor = {
        "schema_version": (
            eval_runner.CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_POLICY_SCHEMA
        ),
        "hard_cap_nanos": cap_nanos,
        "per_run_reserve_nanos": reserve_nanos,
        "schedule_upper_bound_nanos": reserve_nanos * 12,
        "full_schedule_reserved": False,
        "schedule_completion_guaranteed": False,
        "invoice_or_free_tier_claim": False,
    }
    return {
        "schema_version": (
            eval_runner.CONDITION_NEUTRAL_COMPARISON_COST_CONTROL_SCHEMA
        ),
        "descriptor": descriptor,
        "content_hash": sha256_text(canonical_json(descriptor)),
    }


def _row(row_id: str, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schedule_row_id": row_id,
        "campaign_cost_control_hash": state["policy_hash"],
        "cap_nanos": state["cap_nanos"],
        "reserve_nanos": state["reserve_nanos"],
    }


def _append(
    path: Path,
    state: dict[str, Any],
    event_type: str,
    payload: dict[str, Any],
) -> None:
    sequence = state["sequence"] + 1
    event_hash = eval_runner._append_campaign_event(
        path,
        sequence=sequence,
        previous_event_hash=state["event_hash"],
        event_type=event_type,
        payload=payload,
    )
    state.update(sequence=sequence, event_hash=event_hash)


def _usage_for_cost(run_cost_nanos: int) -> Usage:
    # Every D-087 price is an integer multiple of 75 nano-USD. Cached input
    # tokens make arbitrary multiples of that pricing quantum easy to express.
    assert run_cost_nanos % 75 == 0
    tokens = run_cost_nanos // 75
    return Usage(
        model_calls=1,
        tool_calls=0,
        input_tokens=tokens,
        cached_input_tokens=tokens,
        cache_write_input_tokens=0,
        output_tokens=0,
        wall_clock_ms=1,
        model_cost_usd=0,
    )


def _usage_evidence(row_id: str, run_cost_nanos: int) -> dict[str, Any]:
    return eval_runner._d087_usage_evidence(
        _usage_for_cost(run_cost_nanos),
        run_id=f"run-{row_id}",
        schedule_row_id=row_id,
        qualification_hash=HASH_A,
        source_evidence_hash=HASH_B,
        persisted_result_hash=HASH_C,
    )


def _seed_state(path: Path, cost_control: dict[str, Any]) -> dict[str, Any]:
    descriptor = cost_control["descriptor"]
    state: dict[str, Any] = {
        "sequence": 0,
        "event_hash": None,
        "policy_hash": cost_control["content_hash"],
        "cap_nanos": descriptor["hard_cap_nanos"],
        "reserve_nanos": descriptor["per_run_reserve_nanos"],
        "durable": {},
    }
    _append(
        path,
        state,
        "CampaignStarted",
        {"campaign_cost_control_hash": state["policy_hash"]},
    )
    return state


def _resolver(
    state: dict[str, Any],
) -> Callable[[str, str, Path], dict[str, Any]]:
    def resolve(run_id: str, row_id: str, _root: Path) -> dict[str, Any]:
        evidence = state["durable"].get(run_id)
        if evidence is None:
            raise ContractError("fixture durable evidence is missing")
        assert evidence["descriptor"]["schedule_row_id"] == row_id
        return copy.deepcopy(evidence)

    return resolve


def _reconcile(
    path: Path,
    cost_control: dict[str, Any],
    state: dict[str, Any],
    run_root: Path,
) -> dict[str, Any]:
    return eval_runner._campaign_cost_journal_evidence(
        path,
        cost_control,
        run_root=run_root,
        durable_usage_resolver=_resolver(state),
    )


def _reserve(
    path: Path,
    state: dict[str, Any],
    *,
    row_id: str,
    accrued_nanos: int,
) -> None:
    _append(
        path,
        state,
        "RunCostReserved",
        {
            **_row(row_id, state),
            "run_id": f"run-{row_id}",
            "accrued_cost_nanos_before": accrued_nanos,
            "held_reserve_nanos_after": state["reserve_nanos"],
        },
    )


def _start_and_finish(
    path: Path,
    state: dict[str, Any],
    *,
    row_id: str,
    run_cost_nanos: int,
    reconciliation_passed: bool = True,
    terminal_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = f"run-{row_id}"
    durable_evidence = _usage_evidence(row_id, run_cost_nanos)
    state["durable"][run_id] = durable_evidence
    evidence = terminal_evidence or durable_evidence
    _append(
        path,
        state,
        "RunStarted",
        {"schedule_row_id": row_id, "run_id": run_id},
    )
    _append(
        path,
        state,
        "RunTerminal",
        {
            "schedule_row_id": row_id,
            "run_id": run_id,
            "usage_evidence": evidence,
            "usage_evidence_hash": evidence["content_hash"],
            "usage_reconciliation_passed": reconciliation_passed,
        },
    )
    return evidence


def _settle(
    path: Path,
    state: dict[str, Any],
    *,
    row_id: str,
    accrued_nanos: int,
    run_cost_nanos: int,
    usage_evidence_hash: str | None = None,
) -> None:
    run_id = f"run-{row_id}"
    evidence = state["durable"].get(run_id)
    evidence_hash = usage_evidence_hash or (
        evidence["content_hash"] if evidence is not None else HASH_A
    )
    _append(
        path,
        state,
        "RunCostSettled",
        {
            **_row(row_id, state),
            "run_id": run_id,
            "accrued_cost_nanos_before": accrued_nanos,
            "actual_run_cost_nanos": run_cost_nanos,
            "accrued_cost_nanos_after": accrued_nanos + run_cost_nanos,
            "held_reserve_nanos_after": 0,
            "usage_evidence_hash": evidence_hash,
            "usage_reconciliation_passed": True,
        },
    )


def _complete_run(
    path: Path,
    state: dict[str, Any],
    *,
    row_id: str,
    accrued_nanos: int,
    run_cost_nanos: int,
) -> None:
    _reserve(path, state, row_id=row_id, accrued_nanos=accrued_nanos)
    evidence = _start_and_finish(
        path,
        state,
        row_id=row_id,
        run_cost_nanos=run_cost_nanos,
    )
    _settle(
        path,
        state,
        row_id=row_id,
        accrued_nanos=accrued_nanos,
        run_cost_nanos=run_cost_nanos,
        usage_evidence_hash=evidence["content_hash"],
    )


def test_d087_fixed_integer_pricing_covers_all_token_classes() -> None:
    usage = Usage(
        model_calls=1,
        tool_calls=0,
        input_tokens=10,
        cached_input_tokens=2,
        cache_write_input_tokens=3,
        output_tokens=4,
        wall_clock_ms=1,
        model_cost_usd=999,
    )
    assert eval_runner._d087_fixed_cost_nanos(usage) == (
        5 * 750 + 2 * 75 + 3 * 750 + 4 * 4_500
    )


def test_d087_reconciles_valid_hash_chained_reserve_and_settlement(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _complete_run(
        journal,
        state,
        row_id="row-1",
        accrued_nanos=0,
        run_cost_nanos=68_025_750,
    )

    evidence = _reconcile(journal, cost_control, state, tmp_path)

    assert evidence == {
        "schema_version": "campaign-cost-qualification-v1",
        "passed": True,
        "fully_settled": True,
        "campaign_cost_control_hash": cost_control["content_hash"],
        "cap_nanos": D087_CAP_NANOS,
        "accrued_cost_nanos": 68_025_750,
        "held_reserve_nanos": 0,
        "maximum_committed_nanos": D087_RESERVE_NANOS,
        "reserved_runs": 1,
        "settled_runs": 1,
        "reserve_unavailable_events": 0,
        "active_schedule_row_id": None,
        "active_run_id": None,
        "active_usage_reconciliation_passed": None,
        "live_resume_supported": False,
    }


def test_d087_exact_cap_equality_admits_the_full_next_reserve(
    tmp_path: Path,
) -> None:
    # D-087 token prices have a 75-nano quantum. Use the nearest divisible cap
    # so this test exercises equality rather than an impossible token total.
    cap_nanos = 25_000_000_050
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control(cap_nanos=cap_nanos)
    state = _seed_state(journal, cost_control)
    accrued_nanos = 0
    for index, run_cost_nanos in enumerate(
        (D087_RESERVE_NANOS, D087_RESERVE_NANOS, 3_062_500_050),
        start=1,
    ):
        _complete_run(
            journal,
            state,
            row_id=f"row-{index}",
            accrued_nanos=accrued_nanos,
            run_cost_nanos=run_cost_nanos,
        )
        accrued_nanos += run_cost_nanos

    assert accrued_nanos + D087_RESERVE_NANOS == cap_nanos
    _complete_run(
        journal,
        state,
        row_id="row-4",
        accrued_nanos=accrued_nanos,
        run_cost_nanos=D087_RESERVE_NANOS,
    )
    evidence = _reconcile(journal, cost_control, state, tmp_path)
    assert evidence["accrued_cost_nanos"] == cap_nanos
    assert evidence["maximum_committed_nanos"] == cap_nanos
    assert evidence["reserved_runs"] == evidence["settled_runs"] == 4


def test_d087_cap_plus_one_records_unavailable_without_reserving(
    tmp_path: Path,
) -> None:
    cap_nanos = 25_000_000_049
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control(cap_nanos=cap_nanos)
    state = _seed_state(journal, cost_control)
    accrued_nanos = 0
    for index, run_cost_nanos in enumerate(
        (D087_RESERVE_NANOS, D087_RESERVE_NANOS, 3_062_500_050),
        start=1,
    ):
        _complete_run(
            journal,
            state,
            row_id=f"row-{index}",
            accrued_nanos=accrued_nanos,
            run_cost_nanos=run_cost_nanos,
        )
        accrued_nanos += run_cost_nanos
    assert accrued_nanos + D087_RESERVE_NANOS == cap_nanos + 1
    _append(
        journal,
        state,
        "CostReserveUnavailable",
        {
            **_row("row-4", state),
            "accrued_cost_nanos": accrued_nanos,
            "held_reserve_nanos": 0,
        },
    )
    _append(
        journal,
        state,
        "RunNotStarted",
        {"schedule_row_id": "row-4", "reason_type": "CostReserveUnavailable"},
    )
    evidence = _reconcile(journal, cost_control, state, tmp_path)
    assert evidence["accrued_cost_nanos"] == cap_nanos - D087_RESERVE_NANOS + 1
    assert evidence["reserve_unavailable_events"] == 1


def test_d087_rejects_a_tampered_hash_chained_event(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    rows = [json.loads(line) for line in journal.read_text().splitlines()]
    rows[-1]["payload"]["accrued_cost_nanos_before"] = 1
    journal.write_text(
        "\n".join(canonical_json(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ContractError, match="hash chain mismatch"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_rejects_a_duplicate_reservation(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    with pytest.raises(ContractError, match="duplicate campaign cost reservation"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_rejects_a_settlement_without_a_reservation(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _settle(
        journal,
        state,
        row_id="row-1",
        accrued_nanos=0,
        run_cost_nanos=75,
    )
    with pytest.raises(ContractError, match="invalid campaign cost settlement"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_rejects_terminal_before_run_started(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    _append(
        journal,
        state,
        "RunTerminal",
        {
            "schedule_row_id": "row-1",
            "run_id": "run-row-1",
            "usage_evidence": None,
            "usage_evidence_hash": None,
            "usage_reconciliation_passed": False,
        },
    )
    with pytest.raises(ContractError, match="run terminal ordering"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_rejects_settlement_with_a_different_usage_evidence_hash(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    _start_and_finish(journal, state, row_id="row-1", run_cost_nanos=75)
    _settle(
        journal,
        state,
        row_id="row-1",
        accrued_nanos=0,
        run_cost_nanos=75,
        usage_evidence_hash=HASH_C,
    )
    with pytest.raises(ContractError, match="invalid campaign cost settlement"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_unqualified_terminal_keeps_the_reserve_held(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    _append(
        journal,
        state,
        "RunStarted",
        {"schedule_row_id": "row-1", "run_id": "run-row-1"},
    )
    _append(
        journal,
        state,
        "RunTerminal",
        {
            "schedule_row_id": "row-1",
            "run_id": "run-row-1",
            "usage_evidence": None,
            "usage_evidence_hash": None,
            "usage_reconciliation_passed": False,
        },
    )
    evidence = _reconcile(journal, cost_control, state, tmp_path)
    assert evidence["fully_settled"] is False
    assert evidence["accrued_cost_nanos"] == 0
    assert evidence["held_reserve_nanos"] == D087_RESERVE_NANOS
    assert evidence["active_run_id"] == "run-row-1"
    assert evidence["active_usage_reconciliation_passed"] is False


def test_d087_rejects_false_terminal_verdict_rewritten_true_at_settlement(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    _append(
        journal,
        state,
        "RunStarted",
        {"schedule_row_id": "row-1", "run_id": "run-row-1"},
    )
    _append(
        journal,
        state,
        "RunTerminal",
        {
            "schedule_row_id": "row-1",
            "run_id": "run-row-1",
            "usage_evidence": None,
            "usage_evidence_hash": None,
            "usage_reconciliation_passed": False,
        },
    )
    _settle(
        journal,
        state,
        row_id="row-1",
        accrued_nanos=0,
        run_cost_nanos=75,
    )
    with pytest.raises(ContractError, match="invalid campaign cost settlement"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_rejects_terminal_descriptor_that_differs_from_durable_result(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    original = _usage_evidence("row-1", 750)
    tampered = copy.deepcopy(original)
    descriptor = tampered["descriptor"]
    descriptor["usage"]["input_tokens"] += 1
    descriptor["usage"]["cached_input_tokens"] += 1
    descriptor["token_derived_cost_nanos"] += 75
    tampered["content_hash"] = sha256_text(canonical_json(descriptor))
    _start_and_finish(
        journal,
        state,
        row_id="row-1",
        run_cost_nanos=750,
        terminal_evidence=tampered,
    )
    # The settlement is internally consistent with the tampered terminal, but
    # the resolver still returns the original durable result evidence.
    _settle(
        journal,
        state,
        row_id="row-1",
        accrued_nanos=0,
        run_cost_nanos=825,
        usage_evidence_hash=tampered["content_hash"],
    )
    with pytest.raises(ContractError, match="invalid campaign cost settlement"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_rejects_settlement_cost_plus_one_nano(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _reserve(journal, state, row_id="row-1", accrued_nanos=0)
    evidence = _start_and_finish(
        journal,
        state,
        row_id="row-1",
        run_cost_nanos=750,
    )
    _settle(
        journal,
        state,
        row_id="row-1",
        accrued_nanos=0,
        run_cost_nanos=751,
        usage_evidence_hash=evidence["content_hash"],
    )
    with pytest.raises(ContractError, match="invalid campaign cost settlement"):
        _reconcile(journal, cost_control, state, tmp_path)


def test_d087_rejects_missing_durable_usage_evidence(tmp_path: Path) -> None:
    journal = tmp_path / "campaign.jsonl"
    cost_control = _cost_control()
    state = _seed_state(journal, cost_control)
    _complete_run(
        journal,
        state,
        row_id="row-1",
        accrued_nanos=0,
        run_cost_nanos=750,
    )
    state["durable"].clear()
    with pytest.raises(ContractError, match="could not be revalidated"):
        _reconcile(journal, cost_control, state, tmp_path)
