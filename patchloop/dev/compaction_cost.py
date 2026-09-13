"""Model-rate accounting and an explicitly conditional compaction reservation.

The compact endpoint has no caller-controlled output ceiling. The model's published
limits are a planning assumption, not an endpoint-enforced dollar cap. A collector
must require acknowledgement of that distinction, plus a separate exact live grant.
"""
from __future__ import annotations

from decimal import Decimal

from patchloop.agent.compaction import require, usage_fields
from patchloop.dev.cost import DevCostLedger, ModelPricing, usd_to_nanos
from patchloop.errors import ContractError

MODEL = "gpt-5.4-mini-2026-03-17"
INPUT_RESERVE = 400_000  # Full context window, even larger than the 272k max input.
OUTPUT_RESERVE = 128_000
RATES = ModelPricing(Decimal("0.75"), Decimal("0.075"), Decimal("4.50"))
CONTRACT = {
    "kind": "compaction-model-limit-reservation-v1", "model": MODEL,
    "service_tier": "default", "endpoint": "https://api.openai.com/v1/responses/compact",
    "input_per_million_usd": "0.75", "cached_input_per_million_usd": "0.075",
    "output_per_million_usd": "4.50", "reserved_input_tokens": INPUT_RESERVE,
    "reserved_output_tokens": OUTPUT_RESERVE, "reserved_cost_nanos": 876_000_000,
    "reservation_basis": "published model limits; no cache discount assumed",
    "endpoint_enforced_output_limit": None, "endpoint_enforced_dollar_cap": False,
    "limits_apply_to_compaction": "EXPLICIT_PLANNING_ASSUMPTION_NOT_ENDPOINT_GUARANTEE",
    "model_max_input_tokens": 272_000, "model_context_window_tokens": 400_000,
    "reasoning_tokens": "already included in output_tokens; never add twice",
    "historical_native_count": "not reused as an exact count for a different endpoint",
    "count_requests": 0, "generation_requests": 0, "maximum_compaction_requests": 1,
    "reviewed_on": "2026-09-12",
    "sources": [
        "https://developers.openai.com/api/docs/pricing",
        "https://developers.openai.com/api/docs/models/gpt-5.4-mini",
        "https://developers.openai.com/api/reference/python/resources/responses/methods/compact",
    ],
}


def reserve(cap_usd: Decimal) -> dict:
    ledger = DevCostLedger(cap_usd, RATES)
    # This is arithmetic, not a max_output_tokens parameter sent to compact.
    admission = ledger.admit(INPUT_RESERVE, desired_output_ceiling=OUTPUT_RESERVE,
                             minimum_output_ceiling=OUTPUT_RESERVE)
    require(admission is not None, "cap cannot cover the full model-limit reservation")
    require(admission.reserved_cost_nanos == CONTRACT["reserved_cost_nanos"],
            "reservation contract mismatch")
    return {"cap_nanos": ledger.cap_nanos, "reserved_cost_nanos": admission.reserved_cost_nanos,
            "basis": CONTRACT["reservation_basis"], "endpoint_enforced_dollar_cap": False}


def account(usage: dict | None, cap_usd: Decimal) -> dict:
    """Keep provider usage, tariff estimate and invoice verification distinct."""
    cap = usd_to_nanos(cap_usd)
    try:
        validated = usage_fields({"usage": usage})
    except (ContractError, TypeError, ValueError):
        return {"status": "BILLING_UNKNOWN", "model_rate_cost_nanos": None,
                "invoice_cost_usd": None}
    input_tokens = validated["input_tokens"]
    output_tokens = validated["output_tokens"]
    details = validated["input_tokens_details"]
    # The model table has no separate cache-write tariff; do not invent one.
    if details.get("cache_write_tokens", 0) != 0:
        return {"status": "BILLING_UNKNOWN", "model_rate_cost_nanos": None,
                "invoice_cost_usd": None}
    cost = DevCostLedger(cap_usd, RATES).settle(
        input_tokens=input_tokens, output_tokens=output_tokens,
        cached_input_tokens=details["cached_tokens"],
    )
    within = (input_tokens <= INPUT_RESERVE and output_tokens <= OUTPUT_RESERVE
              and cost <= min(cap, CONTRACT["reserved_cost_nanos"]))
    return {"status": "ACCOUNTED_AT_MODEL_RATES" if within else "RESERVATION_EXCEEDED",
            "model_rate_cost_nanos": cost, "invoice_cost_usd": None,
            "within_model_limit_reservation": within}


def reserve_from_ledger(ledger: DevCostLedger) -> dict:
    """Quote the full conditional allowance against the invocation's remaining cap.

    Does not hold or settle money. The run lock serializes admission and the caller
    later restores known usage by unique durable dispatch ID, never by replay count.
    """
    require(ledger.pricing == RATES, "compaction pricing contract mismatch")
    admission = ledger.admit(INPUT_RESERVE, desired_output_ceiling=OUTPUT_RESERVE,
                             minimum_output_ceiling=OUTPUT_RESERVE)
    require(admission is not None, "cap cannot cover the full model-limit reservation")
    require(admission.reserved_cost_nanos == CONTRACT["reserved_cost_nanos"],
            "reservation contract mismatch")
    return {
        "cap_nanos": ledger.cap_nanos,
        "prior_spent_nanos": ledger.spent_nanos,
        "available_nanos": ledger.remaining_nanos,
        "reserved_cost_nanos": admission.reserved_cost_nanos,
        "endpoint_enforced_dollar_cap": False,
    }
