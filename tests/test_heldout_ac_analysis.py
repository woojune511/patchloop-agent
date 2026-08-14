from __future__ import annotations

import ast
import inspect
from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from patchloop.evals import heldout_ac_analysis as analysis


def _evaluator_outcome(*, success: bool) -> dict[str, Any]:
    return {
        "kind": "evaluator_completed",
        "terminal_outcome": True,
        "trace_qualified": True,
        "cost_settled": True,
        "durable_usage_reconciled": True,
        "matrix_inconclusive_triggers": [],
        "evaluator_v2_runtime_authenticated": True,
        "evaluator_v2_completion_eligible": True,
        "hidden_verdict": "PASS" if success else "FAIL",
        "regression_verdict": "PASS",
        "scope_verdict": "PASS",
        "safety_verdict": "PASS",
    }


def _agent_terminal_outcome() -> dict[str, Any]:
    return {
        "kind": "typed_pre_evaluator_agent_terminal",
        "terminal_outcome": True,
        "trace_qualified": True,
        "cost_settled": True,
        "durable_usage_reconciled": True,
        "matrix_inconclusive_triggers": [],
        "evaluator_not_run": True,
        "terminal_type": "token-budget-exhaustion",
    }


def _usage(condition: str) -> dict[str, int]:
    if condition == "no_memory":
        return {
            "input_tokens": 100,
            "output_tokens": 20,
            "reasoning_tokens": 5,
            "total_tokens": 120,
            "model_cost_nanos": 1_000_000_000,
            "model_calls": 3,
            "tool_calls": 4,
            "wall_time_milliseconds": 1_000,
        }
    return {
        "input_tokens": 90,
        "output_tokens": 10,
        "reasoning_tokens": 3,
        "total_tokens": 100,
        "model_cost_nanos": 2_000_000_000,
        "model_calls": 2,
        "tool_calls": 3,
        "wall_time_milliseconds": 800,
    }


def _projection(
    *,
    successes: set[tuple[str, int, str]] | None = None,
    agent_terminals: set[tuple[str, int, str]] | None = None,
) -> dict[str, Any]:
    success_cells = successes
    terminal_cells = agent_terminals or set()
    rows: list[dict[str, Any]] = []
    for order, (task_id, role, condition, repetition) in enumerate(
        analysis.EXPECTED_SCHEDULE,
        start=1,
    ):
        cell = (task_id, repetition, condition)
        rows.append(
            {
                "order": order,
                "task_id": task_id,
                "role": role,
                "condition": condition,
                "repetition": repetition,
                "outcome": (
                    _agent_terminal_outcome()
                    if cell in terminal_cells
                    else _evaluator_outcome(
                        success=True if success_cells is None else cell in success_cells
                    )
                ),
                "usage": _usage(condition),
            }
        )
    return {
        "schema_version": analysis.SCHEMA_VERSION,
        "preregistration_id": analysis.PREREGISTRATION_ID,
        "preregistration_content_hash": analysis.PREREGISTRATION_CONTENT_HASH,
        "rows": rows,
    }


def _rational(value: analysis.ReducedRational) -> tuple[int, int]:
    return value.numerator, value.denominator


def test_exact_complete_panel_computes_zero_point_mass_deterministically() -> None:
    result = analysis.analyze_heldout_ac(_projection())
    repeated = analysis.analyze_heldout_ac(_projection())

    assert result == repeated
    assert result.complete_panel is True
    assert result.scheduled_rows == result.eligible_rows == 48
    assert _rational(result.primary_estimate) == (0, 1)
    assert _rational(result.stability_interval.lower) == (0, 1)
    assert _rational(result.stability_interval.upper) == (0, 1)
    assert result.stability_interval.samples == 100_000
    assert result.stability_interval.confidence_interval_claim_authorized is False
    assert result.sign_flip_sensitivity.extreme_or_equal_sign_vectors == 4_096
    assert _rational(result.sign_flip_sensitivity.p_value) == (1, 1)
    assert result.directional_flips.benefit_count == 0
    assert result.directional_flips.negative_transfer_count == 0
    assert {row.role: _rational(row.estimate) for row in result.role_strata} == {
        "core-same-repo": (0, 1),
        "core-cross-repo": (0, 1),
    }
    for distribution in result.verdict_distributions:
        assert distribution.pass_rows == 48
        assert distribution.fail_rows == 0
        assert distribution.not_run_typed_agent_terminal_rows == 0

    by_condition = {row.condition: row for row in result.conditions}
    assert by_condition["no_memory"].successes == 24
    assert _rational(by_condition["no_memory"].total_model_cost_usd) == (24, 1)
    assert _rational(by_condition["no_memory"].cost_per_success_usd) == (1, 1)
    assert by_condition["structured"].successes == 24
    assert _rational(by_condition["structured"].total_model_cost_usd) == (48, 1)
    assert _rational(by_condition["structured"].cost_per_success_usd) == (2, 1)


def test_maximal_benefit_includes_typed_agent_terminals_as_zero() -> None:
    structured = {
        (task_id, repetition, "structured")
        for task_id in analysis.TASK_ORDER
        for repetition in (1, 2)
    }
    no_memory = {
        (task_id, repetition, "no_memory")
        for task_id in analysis.TASK_ORDER
        for repetition in (1, 2)
    }

    result = analysis.analyze_heldout_ac(
        _projection(successes=structured, agent_terminals=no_memory)
    )

    assert _rational(result.primary_estimate) == (1, 1)
    assert [_rational(row.effect) for row in result.task_effects] == [(1, 1)] * 12
    assert _rational(result.stability_interval.lower) == (1, 1)
    assert _rational(result.stability_interval.upper) == (1, 1)
    assert result.sign_flip_sensitivity.observed_abs_integer_statistic == 24
    assert result.sign_flip_sensitivity.extreme_or_equal_sign_vectors == 2
    assert _rational(result.sign_flip_sensitivity.p_value) == (1, 2_048)
    assert result.directional_flips.benefit_count == 24
    assert _rational(result.directional_flips.benefit_rate) == (1, 1)
    assert result.directional_flips.negative_transfer_count == 0
    assert [_rational(row.estimate) for row in result.role_strata] == [(1, 1), (1, 1)]
    for distribution in result.verdict_distributions:
        assert distribution.pass_rows == 24
        assert distribution.fail_rows == 0
        assert distribution.not_run_typed_agent_terminal_rows == 24

    assert _rational(result.resource_deltas.input_tokens) == (-10, 1)
    assert _rational(result.resource_deltas.output_tokens) == (-10, 1)
    assert _rational(result.resource_deltas.reasoning_tokens) == (-2, 1)
    assert _rational(result.resource_deltas.total_tokens) == (-20, 1)
    assert _rational(result.resource_deltas.model_cost_usd) == (1, 1)
    assert _rational(result.resource_deltas.model_calls) == (-1, 1)
    assert _rational(result.resource_deltas.tool_calls) == (-1, 1)
    assert _rational(result.resource_deltas.wall_time_seconds) == (-1, 5)

    by_condition = {row.condition: row for row in result.conditions}
    assert by_condition["no_memory"].successes == 0
    assert by_condition["no_memory"].cost_per_success_usd is None
    assert by_condition["no_memory"].cost_per_success_status == "undefined-zero-success-denominator"
    assert _rational(by_condition["structured"].cost_per_success_usd) == (2, 1)


def test_evaluator_fail_is_an_eligible_zero_and_directional_negative_transfer() -> None:
    successes = {
        (task_id, repetition, condition)
        for task_id in analysis.TASK_ORDER
        for repetition in (1, 2)
        for condition in ("no_memory", "structured")
    }
    target = (analysis.TASK_ORDER[0], 1, "structured")
    successes.remove(target)

    result = analysis.analyze_heldout_ac(_projection(successes=successes))

    assert _rational(result.primary_estimate) == (-1, 24)
    assert result.directional_flips.benefit_count == 0
    assert result.directional_flips.negative_transfer_count == 1
    assert _rational(result.directional_flips.negative_transfer_rate) == (1, 24)
    by_role = {row.role: row for row in result.role_strata}
    assert _rational(by_role["core-same-repo"].estimate) == (0, 1)
    assert _rational(by_role["core-cross-repo"].estimate) == (-1, 12)
    hidden = next(row for row in result.verdict_distributions if row.verdict == "hidden")
    assert (hidden.pass_rows, hidden.fail_rows, hidden.not_run_typed_agent_terminal_rows) == (
        47,
        1,
        0,
    )


def test_nontrivial_sha256_percentile_endpoints_are_exact_reduced_rationals() -> None:
    integerized_effects = (-2, -1, 0, 1, 2, -2, -1, 0, 1, 2, -1, 1)
    successes: set[tuple[str, int, str]] = set()
    for task_id, effect in zip(analysis.TASK_ORDER, integerized_effects, strict=True):
        for repetition in (1, 2):
            if effect == -2 or (effect == -1 and repetition == 1):
                successes.add((task_id, repetition, "no_memory"))
            elif effect == 2 or (effect == 1 and repetition == 1):
                successes.add((task_id, repetition, "structured"))
            else:
                successes.add((task_id, repetition, "no_memory"))
                successes.add((task_id, repetition, "structured"))

    result = analysis.analyze_heldout_ac(_projection(successes=successes))

    assert [row.integerized_effect for row in result.task_effects] == list(integerized_effects)
    assert _rational(result.primary_estimate) == (0, 1)
    assert _rational(result.stability_interval.lower) == (-3, 8)
    assert _rational(result.stability_interval.upper) == (3, 8)


def test_row_serialization_order_does_not_replace_scheduled_order_identity() -> None:
    payload = _projection()
    payload["rows"].reverse()

    result = analysis.analyze_heldout_ac(payload)

    assert result.complete_panel is True
    assert _rational(result.primary_estimate) == (0, 1)


def test_partial_panel_fails_closed() -> None:
    payload = _projection()
    payload["rows"].pop()

    with pytest.raises(analysis.HeldoutACAnalysisError, match="contract is invalid"):
        analysis.analyze_heldout_ac(payload)


def test_duplicate_row_fails_closed() -> None:
    payload = _projection()
    payload["rows"][-1] = deepcopy(payload["rows"][0])

    with pytest.raises(analysis.HeldoutACAnalysisError, match="duplicate scheduled row"):
        analysis.analyze_heldout_ac(payload)


def test_schedule_identity_drift_fails_closed() -> None:
    payload = _projection()
    payload["rows"][0]["role"] = "core-cross-repo"

    with pytest.raises(analysis.HeldoutACAnalysisError, match="scheduled identity differs"):
        analysis.analyze_heldout_ac(payload)


def test_matrix_confound_fails_closed_before_analysis() -> None:
    payload = _projection()
    payload["rows"][0]["outcome"]["matrix_inconclusive_triggers"] = [
        "qualification-or-completion-contract-mismatch"
    ]

    with pytest.raises(analysis.HeldoutACAnalysisError, match="matrix-inconclusive confound"):
        analysis.analyze_heldout_ac(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("rows", 0, "order"), True),
        (("rows", 0, "repetition"), 1.0),
        (("rows", 0, "usage", "input_tokens"), "100"),
        (("rows", 0, "outcome", "hidden_verdict"), "pass"),
        (("rows", 0, "outcome", "trace_qualified"), 1),
    ],
)
def test_scalar_type_or_enum_drift_fails_closed(path: tuple[Any, ...], value: Any) -> None:
    payload = _projection()
    cursor: Any = payload
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value

    with pytest.raises(analysis.HeldoutACAnalysisError, match="contract is invalid"):
        analysis.analyze_heldout_ac(payload)


def test_unknown_fields_fail_closed() -> None:
    payload = _projection()
    payload["rows"][0]["usage"]["cached_tokens"] = 1

    with pytest.raises(analysis.HeldoutACAnalysisError, match="contract is invalid"):
        analysis.analyze_heldout_ac(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("total_tokens", 119), ("reasoning_tokens", 21)],
)
def test_usage_reconciliation_fails_closed(field: str, value: int) -> None:
    payload = _projection()
    payload["rows"][0]["usage"][field] = value

    with pytest.raises(analysis.HeldoutACAnalysisError, match="contract is invalid"):
        analysis.analyze_heldout_ac(payload)


def test_unknown_agent_terminal_is_outside_the_eligible_union() -> None:
    payload = _projection()
    payload["rows"][0]["outcome"] = _agent_terminal_outcome()
    payload["rows"][0]["outcome"]["terminal_type"] = "provider-error"

    with pytest.raises(analysis.HeldoutACAnalysisError, match="contract is invalid"):
        analysis.analyze_heldout_ac(payload)


def test_wrong_preregistration_binding_fails_closed() -> None:
    payload = _projection()
    payload["preregistration_content_hash"] = "sha256:" + "0" * 64

    with pytest.raises(analysis.HeldoutACAnalysisError, match="contract is invalid"):
        analysis.analyze_heldout_ac(payload)


def test_reduced_rational_rejects_noncanonical_values() -> None:
    with pytest.raises(ValidationError, match="rational must be reduced"):
        analysis.ReducedRational(numerator=2, denominator=4)
    with pytest.raises(ValidationError, match="zero rational must use denominator one"):
        analysis.ReducedRational(numerator=0, denominator=2)


def test_module_has_no_runtime_artifact_task_or_io_loader_imports() -> None:
    tree = ast.parse(inspect.getsource(analysis))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)

    assert not any(
        name.startswith(
            (
                "openai",
                "requests",
                "subprocess",
                "pathlib",
                "patchloop.runtime",
                "patchloop.task_loader",
                "patchloop.state",
                "patchloop.sandbox",
            )
        )
        for name in imported
    )
