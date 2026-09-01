from __future__ import annotations

import pytest
from pydantic import ValidationError

from patchloop.agent.request_allowance import (
    SplitAwareRequestAllowance,
    project_split_aware_request_allowance,
)


def _project(**updates: int) -> SplitAwareRequestAllowance:
    values = {
        "requested_input_tokens": 100,
        "configured_max_output_tokens": 250,
        "input_tokens_used": 400,
        "output_tokens_used": 300,
        "max_cumulative_input_tokens": 1_000,
        "max_cumulative_output_tokens": 1_000,
        "max_total_tokens": 2_000,
    }
    values.update(updates)
    return project_split_aware_request_allowance(**values)


def test_full_request_preserves_configured_allowance() -> None:
    projection = _project()

    assert projection.decision == "admit_full"
    assert projection.effective_max_output_tokens == 250
    assert projection.constrained_dimensions == ()
    assert projection.blocking_dimensions == ()
    assert projection.finalization_required is False
    assert projection.investigation_allowed is True


def test_output_only_boundary_admits_a_residual_finalization_turn() -> None:
    projection = _project(output_tokens_used=800)

    assert projection.decision == "admit_reduced"
    assert projection.effective_max_output_tokens == 200
    assert projection.binding_dimension == "output_tokens"
    assert projection.constrained_dimensions == ("output_tokens",)
    assert projection.blocking_dimensions == ()
    assert projection.finalization_required is True
    assert projection.investigation_allowed is False


def test_total_boundary_admits_only_the_exact_remaining_allowance() -> None:
    projection = _project(
        input_tokens_used=900,
        output_tokens_used=700,
        max_cumulative_input_tokens=2_000,
        max_cumulative_output_tokens=2_000,
        max_total_tokens=1_850,
    )

    assert projection.decision == "admit_reduced"
    assert projection.effective_max_output_tokens == 150
    assert projection.binding_dimension == "total_tokens"
    assert projection.constrained_dimensions == ("total_tokens",)


@pytest.mark.parametrize(
    ("updates", "blocking_dimensions"),
    [
        ({"input_tokens_used": 950}, ("input_tokens",)),
        ({"output_tokens_used": 1_000}, ("output_tokens",)),
        (
            {
                "input_tokens_used": 900,
                "output_tokens_used": 900,
                "max_total_tokens": 1_900,
            },
            ("total_tokens",),
        ),
    ],
)
def test_request_blocks_only_when_no_positive_safe_response_exists(
    updates: dict[str, int],
    blocking_dimensions: tuple[str, ...],
) -> None:
    projection = _project(**updates)

    assert projection.decision == "block"
    assert projection.effective_max_output_tokens == 0
    assert projection.blocking_dimensions == blocking_dimensions
    assert projection.finalization_required is False
    assert projection.investigation_allowed is False


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("requested_input_tokens", True, TypeError),
        ("configured_max_output_tokens", 2.5, TypeError),
        ("input_tokens_used", -1, ValueError),
        ("max_cumulative_output_tokens", 0, ValueError),
    ],
)
def test_projection_rejects_noncanonical_scalar_inputs(
    field: str,
    value: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        _project(**{field: value})  # type: ignore[arg-type]


def test_projection_rejects_usage_already_outside_the_envelope() -> None:
    with pytest.raises(ValueError, match="total token usage exceeds"):
        _project(max_total_tokens=600)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("effective_max_output_tokens", 199),
        ("decision", "admit_full"),
        ("binding_dimension", "total_tokens"),
        ("finalization_required", False),
        ("investigation_allowed", True),
        ("remaining_output_tokens", 201),
    ],
)
def test_closed_projection_rejects_rehashed_semantic_drift(field: str, value: object) -> None:
    body = _project(output_tokens_used=800).model_dump(mode="python")
    body[field] = value

    with pytest.raises(ValidationError):
        SplitAwareRequestAllowance.model_validate(body)


def test_small_grid_never_exceeds_any_admitted_budget_dimension() -> None:
    for input_used in range(0, 11, 2):
        for output_used in range(0, 11, 2):
            for requested_input in range(0, 7, 2):
                projection = project_split_aware_request_allowance(
                    requested_input_tokens=requested_input,
                    configured_max_output_tokens=5,
                    input_tokens_used=input_used,
                    output_tokens_used=output_used,
                    max_cumulative_input_tokens=10,
                    max_cumulative_output_tokens=10,
                    max_total_tokens=20,
                )
                if projection.decision == "block":
                    continue
                assert input_used + requested_input <= 10
                assert output_used + projection.effective_max_output_tokens <= 10
                assert (
                    input_used
                    + output_used
                    + requested_input
                    + projection.effective_max_output_tokens
                    <= 20
                )
