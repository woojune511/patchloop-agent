"""Pure role funding checks; no provider, sandbox or target execution."""

from decimal import Decimal

import pytest

from patchloop.dev import cost


def ledger():
    return cost.DevCostLedger(Decimal("1.20"), cost.pricing_for_model("gpt-5.4-mini"))


def test_preparation_repair_checks_and_finish_share_existing_call_slots():
    ceilings = cost.recovery_successor_output_ceilings(
        calls=5, preparation_calls=1, repair_calls=1, max_output_tokens=40_000,
    )
    assert ceilings == (8_192, 40_000, 8_192, 8_192, 8_192)
    book = ledger()
    reservation = sum(book.future_call_reservation_nanos(output_ceiling=value)
                      for value in ceilings)
    assert reservation == 5 * 45_000_000 + sum(ceilings) * 4_500
    assert reservation > 5 * book.future_call_reservation_nanos()
    assert book.spent_nanos == 0


@pytest.mark.parametrize("normal", [128, 256, 8_192, 25_000, 40_000])
def test_role_allowances_never_increase_configured_output_ceiling(normal):
    ceilings = cost.recovery_successor_output_ceilings(
        calls=3, preparation_calls=1, repair_calls=1, max_output_tokens=normal,
    )
    assert ceilings == (min(8_192, normal), normal, min(8_192, normal))


def test_successful_path_and_finished_path_keep_only_needed_roles():
    assert cost.recovery_successor_output_ceilings(calls=0, max_output_tokens=40_000) == ()
    assert cost.recovery_successor_output_ceilings(calls=1, max_output_tokens=40_000) == (8_192,)
    assert cost.recovery_successor_output_ceilings(
        calls=3, max_output_tokens=40_000,
    ) == (8_192, 8_192, 8_192)


@pytest.mark.parametrize("changes", [
    {"calls": -1}, {"calls": True}, {"repair_calls": -1}, {"preparation_calls": 1.5},
    {"max_output_tokens": 127}, {"max_output_tokens": 128_001},
    {"calls": 0, "repair_calls": 1}, {"calls": 2, "repair_calls": 1, "preparation_calls": 1},
])
def test_invalid_or_overlapping_role_slots_do_not_silently_lose_reserves(changes):
    with pytest.raises(ValueError):
        cost.recovery_successor_output_ceilings(**{
            "calls": 3, "max_output_tokens": 40_000, **changes,
        })


def test_current_spend_cannot_consume_funded_repair_and_finish():
    book = ledger()
    ceilings = cost.recovery_successor_output_ceilings(
        calls=3, preparation_calls=1, repair_calls=1, max_output_tokens=40_000,
    )
    reserve = sum(book.future_call_reservation_nanos(output_ceiling=value) for value in ceilings)
    correction = book.future_call_reservation_nanos(output_ceiling=25_000)
    current = book.future_call_reservation_nanos(output_ceiling=40_000)
    book.cap_nanos = current + reserve + correction
    admission = book.admit(60_000, desired_output_ceiling=40_000,
                          future_cost_reserve_nanos=reserve + correction)
    assert admission is not None and admission.output_ceiling == 40_000
    book.settle(input_tokens=60_000, cached_input_tokens=0, output_tokens=40_000)
    assert book.remaining_nanos == reserve + correction
    for ceiling in ceilings:
        reserve -= book.future_call_reservation_nanos(output_ceiling=ceiling)
        admission = book.admit(60_000, desired_output_ceiling=ceiling,
                              minimum_output_ceiling=ceiling,
                              future_cost_reserve_nanos=reserve + correction)
        assert admission is not None and admission.output_ceiling == ceiling
        book.settle(input_tokens=60_000, cached_input_tokens=0, output_tokens=ceiling)
    assert book.remaining_nanos == correction


def test_recovery_contract_binds_roles_without_changing_other_policies():
    contract = cost.completion_cost_contract(cost.COMPLETION_RECOVERY_POLICY,
                                             max_correction_output_tokens=25_000)
    assert contract["reservation"] == "role-successors-plus-correction-v3"
    assert contract["future_output_tokens"] == 8_192
    assert contract["preparation_output_tokens"] == contract["finalization_output_tokens"] == 8_192
    assert contract["repair_output_tokens"] == "invocation-max-output-tokens"
    assert contract["correction_output_tokens"] == 25_000
    assert contract["correction_credits_per_run"] == 1
    for policy in (cost.COMPLETION_MINIMUM_POLICY, cost.COMPLETION_RESERVE_POLICY):
        baseline = cost.completion_cost_contract(policy)
        assert baseline["future_output_tokens"] == 128
        assert baseline["pricing"] == "uncached-input-and-minimum-output"
        assert "repair_output_tokens" not in baseline
