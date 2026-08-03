from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from patchloop.errors import ContractError
from patchloop.evals import runner as eval_runner
from patchloop.util import canonical_json, sha256_bytes, sha256_text

SUITE_PATH = Path(
    "experiments/dev-no-memory-condition-neutral-accrued-cap-20260804-r1.yaml"
)
HISTORICAL_SOURCE_PATH = Path("experiments/dev-no-memory-v5.template.yaml")
HISTORICAL_SOURCE_SHA = (
    "sha256:ef7f901a65764832f294e6e5d5706beb9f953523d669b292234d78bd7aa6a1a3"
)


def _payload() -> dict:
    payload = yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_d087_exact_successor_source_loads_with_twelve_rows() -> None:
    suite = eval_runner.load_suite(SUITE_PATH)

    assert suite.experiment_id == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID
    )
    assert suite.purpose.value == "memory-development-no-memory"
    assert len(suite.tasks) * len(suite.conditions) * suite.repetitions == 12
    assert suite.pilot_run_id == "run_c355405d826641b9"
    assert suite.live_cost_approved is False
    assert suite.approved_execution_hash is None
    assert suite.budget == eval_runner.GPT54_MINI_FROZEN_COMPARISON_BUDGET
    assert suite.max_output_tokens == 25_000
    assert suite.estimated_cost_usd == pytest.approx(5.38278975)
    assert suite.cost_limit_usd == 25.0
    assert suite.campaign_cost_policy is not None
    assert suite.campaign_cost_policy.model_dump(mode="json") == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_POLICY
    )
    assert eval_runner._is_frozen_comparison_runtime_profile(suite)
    assert eval_runner._is_accrued_spend_cap_suite(suite)


def test_d087_does_not_mutate_the_historical_d083_source() -> None:
    source_bytes = HISTORICAL_SOURCE_PATH.read_bytes()

    assert sha256_bytes(source_bytes) == HISTORICAL_SOURCE_SHA
    historical = eval_runner.load_suite(HISTORICAL_SOURCE_PATH)
    assert historical.experiment_id == (
        eval_runner.CONDITION_NEUTRAL_COMPARISON_CAMPAIGN_EXPERIMENT_ID
    )
    assert historical.estimated_cost_usd == 87.75
    assert historical.cost_limit_usd == 20
    assert historical.campaign_cost_policy is None
    assert historical.experiment_id in (
        eval_runner.SUPERSEDED_UNEXECUTED_LIVE_EXPERIMENT_IDS
    )


def test_historical_plan_without_pricing_or_cost_control_stays_valid() -> None:
    historical = eval_runner.load_suite(HISTORICAL_SOURCE_PATH)

    assert eval_runner._campaign_cost_control_matches(
        historical,
        None,
        None,
        schedule_size=12,
    )
    assert not eval_runner._campaign_cost_control_matches(
        historical,
        {"content_hash": "sha256:" + "0" * 64},
        None,
        schedule_size=12,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("expected_cost_usd", 5.38278976),
        ("empirical_envelope_usd", 14.36725),
        ("per_run_reserve_usd", 7.312500001),
        ("cap_basis_usd", 21.67975),
        ("cap_usd", 25.000000001),
        ("schedule_worst_rate_upper_bound_usd", 87.750000001),
    ],
)
def test_d087_exact_cost_policy_drift_is_rejected(
    field: str,
    value: float,
) -> None:
    payload = _payload()
    payload["campaign_cost_policy"][field] = value

    with pytest.raises(
        ValidationError,
        match="requires its exact campaign cost policy",
    ):
        eval_runner.ExperimentSuite.model_validate(payload)


def test_d087_cost_policy_is_reserved_for_the_exact_successor_id() -> None:
    payload = _payload()
    payload["experiment_id"] = "dev-no-memory-unbound-accrued-cap"

    with pytest.raises(
        ValidationError,
        match="campaign_cost_policy is reserved for the exact D-087 successor",
    ):
        eval_runner.ExperimentSuite.model_validate(payload)


def test_d087_pricing_separates_expected_spend_cap_and_schedule_upper_bound() -> None:
    suite = eval_runner.load_suite(SUITE_PATH)
    pricing = eval_runner._pricing_contract(suite, schedule_size=12)
    control = eval_runner._campaign_cost_control(
        suite,
        pricing,
        schedule_size=12,
    )

    assert pricing["per_run_cost_reserve_usd"] == 7.3125
    assert pricing["budget_upper_bound_usd"] == 87.75
    assert pricing["cost_admission"] == {
        "schema_version": "campaign-list-price-accrual-cap-v1",
        "mode": "accrued-plus-full-next-run-reserve",
        "hard_cap_usd": 25.0,
        "full_schedule_reserved": False,
        "schedule_completion_guaranteed": False,
    }
    assert suite.estimated_cost_usd == 5.38278975
    assert suite.cost_limit_usd == 25.0

    assert control is not None
    descriptor = control["descriptor"]
    assert descriptor["hard_cap_nanos"] == 25_000_000_000
    assert descriptor["per_run_reserve_nanos"] == 7_312_500_000
    assert descriptor["schedule_upper_bound_nanos"] == 87_750_000_000
    assert descriptor["full_schedule_reserved"] is False
    assert descriptor["schedule_completion_guaranteed"] is False
    assert descriptor["invoice_or_free_tier_claim"] is False
    assert control["content_hash"] == sha256_text(canonical_json(descriptor))
    assert eval_runner._campaign_cost_control_matches(
        suite,
        json.loads(json.dumps(control)),
        pricing,
        schedule_size=12,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        ("0.0000000001", 1),
        ("0.000000001", 1),
        (7.3125, 7_312_500_000),
        (25, 25_000_000_000),
        ("25.0000000001", 25_000_000_001),
    ],
)
def test_usd_to_nanos_uses_conservative_ceiling(
    value: object,
    expected: int,
) -> None:
    assert eval_runner._usd_to_nanos(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(True, id="boolean"),
        pytest.param(-1, id="negative"),
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="infinity"),
        pytest.param("not-a-number", id="invalid-decimal"),
    ],
)
def test_usd_to_nanos_rejects_non_finite_or_invalid_amounts(value: object) -> None:
    with pytest.raises(ContractError):
        eval_runner._usd_to_nanos(value)
