from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from patchloop.agent.budget_adequacy import (
    BudgetAdequacyReport,
    BudgetAdequacyRowObservation,
    BudgetEnvelope,
    build_budget_adequacy_row,
    build_budget_envelope,
    project_budget_adequacy,
    r8_public_budget_adequacy_contract,
)
from patchloop.util import sha256_json


def _envelope() -> BudgetEnvelope:
    return build_budget_envelope(
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
        max_total_tokens=1_100_000,
    )


def _row(
    order: int,
    condition: str,
    *,
    outcome_kind: str = "resolved",
    terminal_dimension: str = "none",
    evaluator_reached: bool | None = None,
    milestones: bool | None = None,
    patch_attempts: int = 2,
    patch_rejections: int = 1,
    input_tokens: int = 100_000,
    output_tokens: int = 10_000,
    cost_nanos: int = 120_000_000,
) -> BudgetAdequacyRowObservation:
    success = outcome_kind == "resolved"
    reached = success if evaluator_reached is None else evaluator_reached
    complete = success if milestones is None else milestones
    return build_budget_adequacy_row(
        order=order,
        task_id=f"public-task-{(order + 1) // 2}",
        condition=condition,
        outcome_kind=outcome_kind,
        success=success,
        evaluator_reached=reached,
        token_terminal_dimension=terminal_dimension,
        patch_milestone=complete,
        check_milestone=complete,
        diff_milestone=complete,
        submission_milestone=complete,
        no_new_evidence_turns=order - 1,
        patch_attempts=patch_attempts,
        patch_rejections=patch_rejections,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        model_cost_nanos=cost_nanos,
    )


def _rows() -> tuple[BudgetAdequacyRowObservation, ...]:
    return (
        _row(1, "no_memory"),
        _row(2, "structured"),
        _row(3, "structured"),
        _row(4, "no_memory"),
    )


def _report(
    rows: tuple[BudgetAdequacyRowObservation, ...] | None = None,
) -> BudgetAdequacyReport:
    return project_budget_adequacy(
        measurement_id="public-budget-adequacy-test",
        expected_rows=4,
        realized_schedule_hash="sha256:" + "a" * 64,
        envelope=_envelope(),
        full_schedule_reserve_nanos=600_000_000,
        hard_cap_nanos=700_000_000,
        rows=_rows() if rows is None else rows,
    )


def _rehashed(model, **changes):
    body = model.model_dump(mode="python")
    body.update(changes)
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    return type(model).model_validate(body)


def test_public_contract_freezes_zero_terminal_interpretation_without_authority() -> None:
    contract = r8_public_budget_adequacy_contract()

    assert contract.public_rows == 4
    assert contract.public_token_terminal_rows == 0
    assert contract.maximum_overall_token_terminal_rows == 0
    assert contract.maximum_per_condition_token_terminal_rows == 0
    assert contract.threshold_selection_uses_r16 is False
    assert contract.threshold_optimality_established is False
    assert contract.population_terminal_rate_bound_established is False
    assert contract.pure_projection_is_official_analysis is False
    assert contract.official_analysis_requires_authenticated_persisted_evidence is True
    assert contract.provider_calls_authorized is False
    assert contract.runner_activation_authorized is False
    assert contract.fresh_panel_authorized is False


def test_complete_zero_terminal_matrix_passes_adequacy_gate() -> None:
    report = _report()

    assert report.complete_matrix is True
    assert report.fixed_budget_primary_status == "estimable-complete-matrix"
    assert report.budget_adequacy_gate_passed is True
    assert report.administrative_truncation_status == "none-observed-at-frozen-envelope"
    assert report.higher_budget_capability_status == "not-identified-no-terminal-observation-only"
    assert report.overall_summary.successes == 4
    assert report.overall_summary.token_terminal_rate.model_dump() == {
        "numerator": 0,
        "denominator": 1,
    }
    assert report.structured_minus_no_memory_success_rate.model_dump() == {
        "numerator": 0,
        "denominator": 1,
    }
    assert report.unrestricted_capability_claim_authorized is False
    assert report.measurement_projection_only is True
    assert report.official_analysis_authorized is False
    assert report.settled_model_cost_nanos == 480_000_000
    assert report.dollar_cap_boundary_reached is False
    assert report.dollar_cap_truncation_observed is False
    assert report.paid_execution_authorized is False


def test_total_token_limit_may_be_stricter_than_split_sum() -> None:
    envelope = build_budget_envelope(
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
        max_total_tokens=900_000,
    )
    assert envelope.max_total_tokens == 900_000

    with pytest.raises(ValidationError, match="reachable split usage"):
        build_budget_envelope(
            max_cumulative_input_tokens=1_000_000,
            max_cumulative_output_tokens=100_000,
            max_total_tokens=1_100_001,
        )


@pytest.mark.parametrize("dimension", ["input_tokens", "output_tokens", "total_tokens"])
def test_each_token_terminal_dimension_fails_only_the_adequacy_interpretation(
    dimension: str,
) -> None:
    rows = list(_rows())
    rows[0] = _row(
        1,
        "no_memory",
        outcome_kind="agent_failure",
        terminal_dimension=dimension,
        evaluator_reached=False,
        milestones=False,
    )

    report = _report(tuple(rows))

    assert report.fixed_budget_primary_status == "estimable-complete-matrix"
    assert report.token_terminals_retained_as_observed_zero is True
    assert report.overall_summary.successes == 3
    assert report.overall_summary.any_token_terminal_rows == 1
    dimension_counts = {
        "input_tokens": report.overall_summary.input_token_terminal_rows,
        "output_tokens": report.overall_summary.output_token_terminal_rows,
        "total_tokens": report.overall_summary.total_token_terminal_rows,
    }
    assert dimension_counts[dimension] == 1
    assert report.budget_adequacy_gate_passed is False
    assert report.administrative_truncation_status == "exceeds-zero-terminal-criterion"
    assert report.higher_budget_capability_status == "inconclusive-administrative-truncation"


def test_condition_terminal_imbalance_is_reported_without_resource_relief() -> None:
    rows = list(_rows())
    rows[1] = _row(
        2,
        "structured",
        outcome_kind="agent_failure",
        terminal_dimension="output_tokens",
        evaluator_reached=False,
        milestones=False,
    )

    report = _report(tuple(rows))

    assert report.structured_minus_no_memory_token_terminal_rows == 1
    assert report.absolute_condition_token_terminal_difference_rows == 1
    assert report.condition_specific_budget_relief_performed is False
    assert report.budget_adequacy_gate_passed is False


def test_zero_success_cost_per_success_is_explicitly_undefined() -> None:
    rows = (
        _row(1, "no_memory"),
        _row(
            2,
            "structured",
            outcome_kind="task_failure",
            evaluator_reached=True,
            milestones=True,
        ),
        _row(
            3,
            "structured",
            outcome_kind="task_failure",
            evaluator_reached=True,
            milestones=True,
        ),
        _row(4, "no_memory"),
    )

    report = _report(rows)

    structured = report.condition_summaries[1]
    assert structured.successes == 0
    assert structured.cost_per_success_nanos.status == "undefined-zero-denominator"
    assert structured.cost_per_success_nanos.value is None
    assert report.budget_adequacy_gate_passed is True


def test_zero_patch_attempt_denominator_is_explicitly_undefined() -> None:
    rows = tuple(
        _row(
            index,
            condition,
            outcome_kind="agent_failure",
            evaluator_reached=False,
            milestones=False,
            patch_attempts=0,
            patch_rejections=0,
        )
        for index, condition in enumerate(
            ("no_memory", "structured", "structured", "no_memory"), start=1
        )
    )

    report = _report(rows)

    assert report.overall_summary.patch_rejection_rate.status == ("undefined-zero-denominator")
    assert report.overall_summary.patch_rejection_rate.value is None


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"success": False}, "success differs"),
        ({"patch_rejections": 3}, "rejections exceed"),
        ({"total_tokens": 1}, "total tokens differ"),
        ({"submission_milestone": False}, "requires submission"),
        ({"token_terminal_dimension": "input_tokens"}, "pre-evaluator agent failure"),
    ],
)
def test_row_contract_rejects_semantic_drift(changes: dict, match: str) -> None:
    row = _rows()[0]
    body = row.model_dump(mode="python")
    body.update(changes)
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError, match=match):
        BudgetAdequacyRowObservation.model_validate(body)


def test_projection_revalidates_copied_nested_rows() -> None:
    rows = list(_rows())
    rows[0] = rows[0].model_copy(update={"success": False})

    with pytest.raises(ValidationError, match="success differs"):
        _report(tuple(rows))


def test_projection_rejects_incomplete_or_imbalanced_matrix() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        _report(_rows()[:2])

    imbalanced = (
        _row(1, "no_memory"),
        _row(2, "no_memory"),
        _row(3, "no_memory"),
        _row(4, "structured"),
    )
    with pytest.raises(ValueError, match="equal A/C rows"):
        _report(imbalanced)


def test_projection_rejects_usage_above_exact_envelope() -> None:
    rows = list(_rows())
    rows[0] = _row(1, "no_memory", input_tokens=1_000_001, output_tokens=0)

    with pytest.raises(ValidationError, match="input usage exceeds"):
        _report(tuple(rows))


def test_projection_rejects_invalid_cost_or_schedule_binding() -> None:
    with pytest.raises(ValueError, match="realized_schedule_hash"):
        project_budget_adequacy(
            measurement_id="bad-schedule",
            expected_rows=4,
            realized_schedule_hash="sha256:bad",
            envelope=_envelope(),
            full_schedule_reserve_nanos=600_000_000,
            hard_cap_nanos=700_000_000,
            rows=_rows(),
        )

    with pytest.raises(ValueError, match="cost envelope"):
        project_budget_adequacy(
            measurement_id="bad-cost",
            expected_rows=4,
            realized_schedule_hash="sha256:" + "a" * 64,
            envelope=_envelope(),
            full_schedule_reserve_nanos=700_000_000,
            hard_cap_nanos=600_000_000,
            rows=_rows(),
        )

    with pytest.raises(ValueError, match="exceeds the full schedule reserve"):
        project_budget_adequacy(
            measurement_id="cost-over-reserve",
            expected_rows=4,
            realized_schedule_hash="sha256:" + "a" * 64,
            envelope=_envelope(),
            full_schedule_reserve_nanos=400_000_000,
            hard_cap_nanos=700_000_000,
            rows=_rows(),
        )


def test_report_rejects_rehashed_summary_or_interpretation_drift() -> None:
    report = _report()
    body = report.model_dump(mode="python")
    body["budget_adequacy_gate_passed"] = False
    body["administrative_truncation_status"] = "exceeds-zero-terminal-criterion"
    body["higher_budget_capability_status"] = "inconclusive-administrative-truncation"
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )

    with pytest.raises(ValidationError, match="gate differs"):
        BudgetAdequacyReport.model_validate(body)


def test_raw_bool_and_float_token_values_are_rejected() -> None:
    row = _rows()[0].model_dump(mode="python")
    row["input_tokens"] = True
    row["content_hash"] = sha256_json(
        {key: value for key, value in row.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        BudgetAdequacyRowObservation.model_validate(row)

    envelope = _envelope().model_dump(mode="python")
    envelope["max_total_tokens"] = 1_100_000.0
    envelope["content_hash"] = sha256_json(
        {key: value for key, value in envelope.items() if key != "content_hash"}
    )
    with pytest.raises(ValidationError):
        BudgetEnvelope.model_validate(envelope)


def test_derived_identity_fields_cannot_be_supplied() -> None:
    values = _rows()[0].model_dump(mode="python")
    values.pop("content_hash")
    with pytest.raises(ValueError, match="derived fields"):
        build_budget_adequacy_row(**values)


def test_extra_fields_are_rejected() -> None:
    body = copy.deepcopy(_report().model_dump(mode="python"))
    body["unregistered_claim"] = True
    with pytest.raises(ValidationError):
        BudgetAdequacyReport.model_validate(body)
