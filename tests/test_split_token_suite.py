from pathlib import Path

import pytest
from pydantic import ValidationError

from patchloop.contracts import Budget
from patchloop.evals.runner import (  # noqa: PLC2701
    AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY,
    GPT54_MINI_AC_SPLIT_TOKEN_BUDGET,
    _campaign_cost_control,
    _is_ac_fixed_bundle_readiness_profile,
    _pricing_contract,
    _suite_hash,
    load_suite,
)
from patchloop.verifier.runtime_evidence import evaluator_v2_runtime_tuple_hash

REPOSITORY = Path(__file__).resolve().parents[1]
R3_SUITE = REPOSITORY / "experiments/dev-validation-ac-fixed-bundle-readiness-20260813-r3.yaml"
R4_SUITE = REPOSITORY / "experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r4.yaml"


def test_legacy_budget_serialization_and_r3_hash_are_unchanged() -> None:
    assert Budget().model_dump(mode="json") == {
        "max_model_calls": 20,
        "max_tool_calls": 50,
        "max_total_tokens": 80_000,
        "wall_clock_timeout_seconds": 900,
    }
    r3 = load_suite(R3_SUITE)
    assert r3.budget.model_dump(mode="json") == {
        "max_model_calls": None,
        "max_tool_calls": None,
        "max_total_tokens": 3_000_000,
        "wall_clock_timeout_seconds": 3_600,
    }
    assert _suite_hash(r3) == (
        "sha256:72b31401ece7a1edd14ac36285041744fa4f1f86fff7f1fb03f5240bd407a57a"
    )
    assert evaluator_v2_runtime_tuple_hash(
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        reasoning_effort="medium",
        reasoning_mode="standard",
        service_tier="default",
        transport_max_retries=0,
        max_output_tokens=25_000,
        max_total_tokens=3_000_000,
        wall_clock_timeout_seconds=3_600,
        tool_schema_version="v2",
        context_policy_version="phase-evidence-v5",
        memory_policy_version="fixed-d110-bundle-v1",
        sandbox_backend="docker",
    ) == "sha256:d2195cdce2ab55a23e4dd186d57cb5fb3222ecc40bd190458d2b64c6df438265"


@pytest.mark.parametrize(
    "payload",
    [
        {"max_cumulative_input_tokens": 3_000_000},
        {
            "token_budget_schema_version": "cumulative-split-v1",
            "max_cumulative_input_tokens": 3_000_000,
        },
        {
            "token_budget_schema_version": "cumulative-split-v1",
            "max_total_tokens": 3_500_001,
            "max_cumulative_input_tokens": 3_000_000,
            "max_cumulative_output_tokens": 500_000,
        },
    ],
)
def test_split_budget_rejects_partial_or_incoherent_contracts(payload: dict) -> None:
    with pytest.raises(ValidationError):
        Budget.model_validate(payload)


def test_r4_uses_one_exact_split_budget_for_all_ac_rows() -> None:
    suite = load_suite(R4_SUITE)
    assert suite.budget == GPT54_MINI_AC_SPLIT_TOKEN_BUDGET
    assert suite.budget.model_dump(mode="json") == {
        "max_model_calls": 180,
        "max_tool_calls": 300,
        "max_total_tokens": 3_350_000,
        "wall_clock_timeout_seconds": 3_600,
        "token_budget_schema_version": "cumulative-split-v1",
        "max_cumulative_input_tokens": 3_000_000,
        "max_cumulative_output_tokens": 350_000,
    }
    assert suite.max_output_tokens == 25_000
    assert len(suite.schedule or []) == 4
    assert _is_ac_fixed_bundle_readiness_profile(suite)
    assert _suite_hash(suite) != _suite_hash(load_suite(R3_SUITE))


def test_r4_price_aware_reserve_matches_split_ceilings() -> None:
    suite = load_suite(R4_SUITE)
    pricing = _pricing_contract(suite, schedule_size=4)
    assert pricing["per_run_cost_reserve_usd"] == 3.825
    assert pricing["budget_upper_bound_usd"] == 15.3

    schedule_hash = "sha256:" + "1" * 64
    row_ids = [f"sha256:{index:064x}" for index in range(1, 5)]
    control = _campaign_cost_control(
        suite,
        pricing,
        schedule_size=4,
        schedule_hash=schedule_hash,
        schedule_row_ids=row_ids,
    )
    assert control is not None
    descriptor = control["descriptor"]
    assert descriptor["policy"] == AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY
    assert descriptor["per_run_reserve_nanos"] == 3_825_000_000
    assert descriptor["full_schedule_reserve_nanos"] == 15_300_000_000
    assert descriptor["hard_cap_nanos"] == 18_000_000_000
    assert descriptor["full_schedule_reserve_usd"] == 15.3


def test_split_runtime_tuple_binds_each_resource_dimension() -> None:
    suite = load_suite(R4_SUITE)
    budget = suite.budget

    def runtime_hash(**changes: int | str | None) -> str:
        values = {
            "token_budget_schema_version": budget.token_budget_schema_version,
            "max_model_calls": budget.max_model_calls,
            "max_tool_calls": budget.max_tool_calls,
            "max_cumulative_input_tokens": budget.max_cumulative_input_tokens,
            "max_cumulative_output_tokens": budget.max_cumulative_output_tokens,
        }
        values.update(changes)
        return evaluator_v2_runtime_tuple_hash(
            provider="openai",
            model_id=suite.model_id,
            reasoning_effort=suite.reasoning_effort,
            reasoning_mode=suite.reasoning_mode,
            service_tier=suite.service_tier,
            transport_max_retries=suite.transport_max_retries,
            max_output_tokens=suite.max_output_tokens,
            max_total_tokens=budget.max_total_tokens,
            wall_clock_timeout_seconds=budget.wall_clock_timeout_seconds,
            tool_schema_version="v2",
            context_policy_version="phase-evidence-v5",
            memory_policy_version="fixed-d110-bundle-v1",
            sandbox_backend="docker",
            **values,
        )

    baseline = runtime_hash()
    assert runtime_hash(max_model_calls=181) != baseline
    assert runtime_hash(max_tool_calls=301) != baseline
    assert runtime_hash(max_cumulative_input_tokens=3_000_001) != baseline
    assert runtime_hash(max_cumulative_output_tokens=350_001) != baseline
