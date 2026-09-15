"""Exact pre-dispatch cost admission for development calls."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from patchloop.errors import ContractError

NANOS_PER_USD = Decimal("1000000000")
TOKENS_PER_MILLION = Decimal("1000000")
# Responses counts reasoning tokens against this ceiling. Medium-reasoning coding
# turns have repeatedly exhausted 4,096 tokens before emitting a required tool call,
# while this project has prior live completion evidence at 25,000.
# The invocation-wide cost ledger still lowers this value before every dispatch.
DEFAULT_OUTPUT_CEILING = 25_000
MINIMUM_OUTPUT_CEILING = 128
PRICING_SOURCE = "https://developers.openai.com/api/docs/pricing"
PRICING_VERIFIED_ON = "2026-09-15"


@dataclass(frozen=True)
class ModelPricing:
    input_per_million_usd: Decimal
    cached_input_per_million_usd: Decimal
    output_per_million_usd: Decimal


# Standard, short-context rates verified against PRICING_SOURCE on
# PRICING_VERIFIED_ON. The client pins service_tier=default and the global API
# endpoint; regional and non-default tier uplifts are therefore out of scope.
# Unknown model IDs fail closed before token counting or generation.
OPENAI_MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-5.4-mini": ModelPricing(Decimal("0.75"), Decimal("0.075"), Decimal("4.5")),
    "gpt-5.4-mini-2026-03-17": ModelPricing(Decimal("0.75"), Decimal("0.075"), Decimal("4.5")),
    # DevRunRequest restricts this snapshot to segmented-v1's counted 60K bound,
    # below the >272K input threshold where the official rates increase.
    "gpt-5.4-2026-03-05": ModelPricing(Decimal("2.5"), Decimal("0.25"), Decimal("15")),
}


def pricing_for_model(model_id: str) -> ModelPricing:
    try:
        return OPENAI_MODEL_PRICING[model_id]
    except KeyError as exc:
        raise ContractError(
            f"no dev-head price is registered for model {model_id!r}; add a reviewed price first"
        ) from exc


def usd_to_nanos(value: Decimal) -> int:
    if not value.is_finite() or value <= 0:
        raise ContractError("max cost must be a finite positive decimal")
    return int((value * NANOS_PER_USD).to_integral_value(rounding=ROUND_FLOOR))


def _token_cost_nanos(tokens: int, rate_per_million: Decimal, *, round_up: bool) -> int:
    if tokens < 0:
        raise ValueError("token counts cannot be negative")
    rounding = ROUND_CEILING if round_up else ROUND_FLOOR
    value = Decimal(tokens) * rate_per_million * NANOS_PER_USD / TOKENS_PER_MILLION
    return int(value.to_integral_value(rounding=rounding))


@dataclass(frozen=True)
class CostAdmission:
    input_tokens: int
    output_ceiling: int
    reserved_cost_nanos: int


class DevCostLedger:
    def __init__(self, cap_usd: Decimal, pricing: ModelPricing) -> None:
        self.cap_nanos = usd_to_nanos(cap_usd)
        self.pricing = pricing
        self.spent_nanos = 0

    @property
    def remaining_nanos(self) -> int:
        return max(0, self.cap_nanos - self.spent_nanos)

    def admit(
        self,
        input_tokens: int,
        *,
        desired_output_ceiling: int = DEFAULT_OUTPUT_CEILING,
        minimum_output_ceiling: int = MINIMUM_OUTPUT_CEILING,
    ) -> CostAdmission | None:
        input_cost = _token_cost_nanos(
            input_tokens,
            self.pricing.input_per_million_usd,
            round_up=True,
        )
        output_nanos_per_token = (
            self.pricing.output_per_million_usd * NANOS_PER_USD / TOKENS_PER_MILLION
        )
        available_for_output = self.remaining_nanos - input_cost
        if available_for_output <= 0 or output_nanos_per_token <= 0:
            return None
        affordable = int(
            (Decimal(available_for_output) / output_nanos_per_token).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        ceiling = min(desired_output_ceiling, affordable)
        if ceiling < minimum_output_ceiling:
            return None
        reservation = input_cost + _token_cost_nanos(
            ceiling,
            self.pricing.output_per_million_usd,
            round_up=True,
        )
        if reservation > self.remaining_nanos:
            return None
        return CostAdmission(input_tokens, ceiling, reservation)

    def settle(
        self,
        *,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int,
    ) -> int:
        cached = min(max(0, cached_input_tokens), max(0, input_tokens))
        uncached = max(0, input_tokens - cached)
        cost = (
            _token_cost_nanos(
                uncached,
                self.pricing.input_per_million_usd,
                round_up=True,
            )
            + _token_cost_nanos(
                cached,
                self.pricing.cached_input_per_million_usd,
                round_up=True,
            )
            + _token_cost_nanos(
                max(0, output_tokens),
                self.pricing.output_per_million_usd,
                round_up=True,
            )
        )
        self.spent_nanos += cost
        return cost

    def restore_settled_usage(
        self,
        usage_rows: list[dict[str, object]],
        *,
        base_spent_nanos: int = 0,
    ) -> None:
        if type(base_spent_nanos) is not int or not 0 <= base_spent_nanos <= self.cap_nanos:
            raise ContractError("durable base cost is invalid")
        self.spent_nanos = base_spent_nanos
        for row in usage_rows:
            cost = row.get("cost_nanos")
            if type(cost) is not int or cost < 0:
                raise ContractError("durable provider usage is invalid")
            self.spent_nanos += cost
