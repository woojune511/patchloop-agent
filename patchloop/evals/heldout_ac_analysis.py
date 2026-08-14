"""Deterministic, I/O-free analysis for the sealed held-out A/C panel.

The caller must supply an explicit typed projection for all 48 scheduled rows.
This module does not load run artifacts, task packages, the preregistration,
credentials, Docker, or provider state.  It accepts only the two preregistered
eligible outcome variants and fails closed before computing a partial or
confounded primary analysis.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from fractions import Fraction
from functools import cache
from math import gcd
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from patchloop.errors import ContractError

SCHEMA_VERSION = "heldout-ac-outcome-projection-v1"
ANALYSIS_SCHEMA_VERSION = "heldout-ac-analysis-v1"
PREREGISTRATION_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
PREREGISTRATION_CONTENT_HASH = (
    "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
)
SAMPLE_COUNT = 100_000
SIGN_VECTOR_COUNT = 4_096

Condition = Literal["no_memory", "structured"]
Role = Literal["core-same-repo", "core-cross-repo"]
Verdict = Literal["PASS", "FAIL"]
AgentTerminal = Literal[
    "token-budget-exhaustion",
    "model-call-limit",
    "tool-call-limit",
    "wall-clock-timeout",
    "submission-failure",
]
MatrixConfound = Literal[
    "provider-sdk-docker-or-evaluator-infrastructure-error",
    "qualification-or-completion-contract-mismatch",
    "private-marker-or-leakage-hit",
    "schedule-treatment-runtime-source-or-hash-drift",
    "missing-durable-usage-or-cost-settlement",
    "duplicate-retried-replaced-or-resumed-row",
    "full-schedule-reservation-or-hard-cap-boundary-failure",
]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ReducedRational(_StrictFrozenModel):
    """Canonical exact rational with a positive, reduced denominator."""

    numerator: int
    denominator: int = Field(gt=0)

    @field_validator("numerator", "denominator", mode="before")
    @classmethod
    def require_exact_integer(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("rational components must be exact integers")
        return value

    @model_validator(mode="after")
    def require_reduced_form(self) -> ReducedRational:
        if self.numerator == 0 and self.denominator != 1:
            raise ValueError("zero rational must use denominator one")
        if gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("rational must be reduced")
        return self

    @classmethod
    def from_fraction(cls, value: Fraction) -> ReducedRational:
        return cls(numerator=value.numerator, denominator=value.denominator)


class HeldoutACUsage(_StrictFrozenModel):
    """Integer projection of the preregistered secondary resource metrics."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    model_cost_nanos: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    wall_time_milliseconds: int = Field(ge=0)

    @field_validator(
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
        "model_cost_nanos",
        "model_calls",
        "tool_calls",
        "wall_time_milliseconds",
        mode="before",
    )
    @classmethod
    def require_exact_integer_counter(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("usage counters must be exact integers")
        return value

    @model_validator(mode="after")
    def reconcile_usage(self) -> HeldoutACUsage:
        if self.reasoning_tokens > self.output_tokens:
            raise ValueError("reasoning_tokens must not exceed output_tokens")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens plus output_tokens")
        return self


class EvaluatorCompletedOutcome(_StrictFrozenModel):
    kind: Literal["evaluator_completed"]
    terminal_outcome: Literal[True]
    trace_qualified: Literal[True]
    cost_settled: Literal[True]
    durable_usage_reconciled: Literal[True]
    matrix_inconclusive_triggers: list[MatrixConfound]
    evaluator_v2_runtime_authenticated: Literal[True]
    evaluator_v2_completion_eligible: Literal[True]
    hidden_verdict: Verdict
    regression_verdict: Verdict
    scope_verdict: Verdict
    safety_verdict: Verdict

    @field_validator(
        "terminal_outcome",
        "trace_qualified",
        "cost_settled",
        "durable_usage_reconciled",
        "evaluator_v2_runtime_authenticated",
        "evaluator_v2_completion_eligible",
        mode="before",
    )
    @classmethod
    def require_exact_boolean(cls, value: Any) -> bool:
        if type(value) is not bool:
            raise ValueError("eligibility flags must be exact booleans")
        return value


class TypedAgentTerminalOutcome(_StrictFrozenModel):
    kind: Literal["typed_pre_evaluator_agent_terminal"]
    terminal_outcome: Literal[True]
    trace_qualified: Literal[True]
    cost_settled: Literal[True]
    durable_usage_reconciled: Literal[True]
    matrix_inconclusive_triggers: list[MatrixConfound]
    evaluator_not_run: Literal[True]
    terminal_type: AgentTerminal

    @field_validator(
        "terminal_outcome",
        "trace_qualified",
        "cost_settled",
        "durable_usage_reconciled",
        "evaluator_not_run",
        mode="before",
    )
    @classmethod
    def require_exact_boolean(cls, value: Any) -> bool:
        if type(value) is not bool:
            raise ValueError("eligibility flags must be exact booleans")
        return value


EligibleOutcome = Annotated[
    EvaluatorCompletedOutcome | TypedAgentTerminalOutcome,
    Field(discriminator="kind"),
]


class HeldoutACOutcomeRow(_StrictFrozenModel):
    order: int = Field(ge=1, le=48)
    task_id: str = Field(min_length=1)
    role: Role
    condition: Condition
    repetition: Literal[1, 2]
    outcome: EligibleOutcome
    usage: HeldoutACUsage

    @field_validator("order", "repetition", mode="before")
    @classmethod
    def require_exact_integer_identity(cls, value: Any) -> int:
        if type(value) is not int:
            raise ValueError("row integer identities must be exact integers")
        return value


class HeldoutACOutcomeProjection(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-outcome-projection-v1"]
    preregistration_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    preregistration_content_hash: Literal[
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    ]
    rows: list[HeldoutACOutcomeRow] = Field(min_length=48, max_length=48)


class TaskEffect(_StrictFrozenModel):
    task_id: str
    integerized_effect: Literal[-2, -1, 0, 1, 2]
    effect: ReducedRational


class StabilityInterval(_StrictFrozenModel):
    status: Literal["descriptive-stability-only"]
    method: Literal["deterministic-task-cluster-percentile-resampling"]
    samples: Literal[100000]
    endpoint_method: Literal["hyndman-fan-type-7-zero-based"]
    lower: ReducedRational
    upper: ReducedRational
    confidence_interval_claim_authorized: Literal[False]


class SignFlipSensitivity(_StrictFrozenModel):
    status: Literal["sensitivity-reference-only"]
    observed_abs_integer_statistic: int = Field(ge=0)
    extreme_or_equal_sign_vectors: int = Field(ge=0, le=4096)
    sign_vectors_enumerated: Literal[4096]
    p_value: ReducedRational
    design_based_randomization_inference_authorized: Literal[False]
    headline_use_authorized: Literal[False]


class DirectionalFlips(_StrictFrozenModel):
    pair_count: Literal[24]
    benefit_count: int = Field(ge=0, le=24)
    benefit_rate: ReducedRational
    negative_transfer_count: int = Field(ge=0, le=24)
    negative_transfer_rate: ReducedRational
    inference: Literal["counts-and-rates-only"]


class RoleStratum(_StrictFrozenModel):
    role: Role
    task_clusters: Literal[6]
    eligible_rows: Literal[24]
    estimate: ReducedRational
    status: Literal["secondary-descriptive"]


class VerdictDistribution(_StrictFrozenModel):
    verdict: Literal["hidden", "regression", "scope", "safety"]
    eligible_rows: Literal[48]
    pass_rows: int = Field(ge=0, le=48)
    fail_rows: int = Field(ge=0, le=48)
    not_run_typed_agent_terminal_rows: int = Field(ge=0, le=48)

    @model_validator(mode="after")
    def require_complete_distribution(self) -> VerdictDistribution:
        if (
            self.pass_rows + self.fail_rows + self.not_run_typed_agent_terminal_rows
            != self.eligible_rows
        ):
            raise ValueError("verdict distribution counts must sum to 48 eligible rows")
        return self


class ResourceDeltas(_StrictFrozenModel):
    """Equal-task-weighted structured-minus-no-memory mean differences."""

    input_tokens: ReducedRational
    output_tokens: ReducedRational
    reasoning_tokens: ReducedRational
    total_tokens: ReducedRational
    model_cost_usd: ReducedRational
    model_calls: ReducedRational
    tool_calls: ReducedRational
    wall_time_seconds: ReducedRational


class ConditionSummary(_StrictFrozenModel):
    condition: Condition
    eligible_rows: Literal[24]
    successes: int = Field(ge=0, le=24)
    success_rate: ReducedRational
    total_model_cost_usd: ReducedRational
    cost_per_success_usd: ReducedRational | None
    cost_per_success_status: Literal["defined", "undefined-zero-success-denominator"]

    @model_validator(mode="after")
    def require_cost_per_success_null_rule(self) -> ConditionSummary:
        if self.successes == 0:
            if self.cost_per_success_usd is not None:
                raise ValueError("zero successes require null cost_per_success_usd")
            if self.cost_per_success_status != "undefined-zero-success-denominator":
                raise ValueError("zero successes require the undefined status")
        else:
            if self.cost_per_success_usd is None:
                raise ValueError("positive successes require cost_per_success_usd")
            if self.cost_per_success_status != "defined":
                raise ValueError("positive successes require the defined status")
        return self


class HeldoutACAnalysis(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-analysis-v1"]
    preregistration_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    preregistration_content_hash: Literal[
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    ]
    scheduled_rows: Literal[48]
    eligible_rows: Literal[48]
    task_clusters: Literal[12]
    complete_panel: Literal[True]
    primary_estimate: ReducedRational
    task_effects: list[TaskEffect] = Field(min_length=12, max_length=12)
    stability_interval: StabilityInterval
    sign_flip_sensitivity: SignFlipSensitivity
    role_strata: list[RoleStratum] = Field(min_length=2, max_length=2)
    directional_flips: DirectionalFlips
    verdict_distributions: list[VerdictDistribution] = Field(min_length=4, max_length=4)
    resource_deltas: ResourceDeltas
    conditions: list[ConditionSummary] = Field(min_length=2, max_length=2)
    causal_general_memory_benefit_claim_authorized: Literal[False]


class HeldoutACAnalysisError(ContractError):
    """Raised when an explicit projection cannot pass the sealed complete-panel gate."""


# Exact schedule copied as metadata from the sealed preregistration.  No task
# package path or private/public task content is opened by this module.
EXPECTED_SCHEDULE: tuple[tuple[str, Role, Condition, int], ...] = (
    ("loguru-post-2038-local-timezone-fallback", "core-same-repo", "structured", 1),
    ("loguru-post-2038-local-timezone-fallback", "core-same-repo", "no_memory", 1),
    ("dagster-subset-partition-definition-selection", "core-cross-repo", "no_memory", 1),
    ("dagster-subset-partition-definition-selection", "core-cross-repo", "structured", 1),
    ("pyfakefs-file-wrapper-io-capabilities", "core-same-repo", "no_memory", 1),
    ("pyfakefs-file-wrapper-io-capabilities", "core-same-repo", "structured", 1),
    ("sqlglot-duckdb-ignore-nulls-modifier-order", "core-cross-repo", "structured", 1),
    ("sqlglot-duckdb-ignore-nulls-modifier-order", "core-cross-repo", "no_memory", 1),
    ("anyio-extensionless-entrypoint-worker-main", "core-same-repo", "structured", 1),
    ("anyio-extensionless-entrypoint-worker-main", "core-same-repo", "no_memory", 1),
    ("fusesoc-retained-parse-error-diagnostics", "core-cross-repo", "no_memory", 1),
    ("fusesoc-retained-parse-error-diagnostics", "core-cross-repo", "structured", 1),
    ("pdm-target-project-options-loading", "core-same-repo", "structured", 1),
    ("pdm-target-project-options-loading", "core-same-repo", "no_memory", 1),
    ("param-shared-rx-fanout-cache", "core-cross-repo", "structured", 1),
    ("param-shared-rx-fanout-cache", "core-cross-repo", "no_memory", 1),
    ("hf-hub-custom-tqdm-class-contract", "core-same-repo", "no_memory", 1),
    ("hf-hub-custom-tqdm-class-contract", "core-same-repo", "structured", 1),
    ("kubeflow-exit-handler-after-dependencies", "core-cross-repo", "no_memory", 1),
    ("kubeflow-exit-handler-after-dependencies", "core-cross-repo", "structured", 1),
    ("tox-dotted-version-factor-base-python", "core-same-repo", "structured", 1),
    ("tox-dotted-version-factor-base-python", "core-same-repo", "no_memory", 1),
    ("mtplx-mixed-content-tool-call-stream", "core-cross-repo", "no_memory", 1),
    ("mtplx-mixed-content-tool-call-stream", "core-cross-repo", "structured", 1),
    ("param-shared-rx-fanout-cache", "core-cross-repo", "no_memory", 2),
    ("param-shared-rx-fanout-cache", "core-cross-repo", "structured", 2),
    ("pyfakefs-file-wrapper-io-capabilities", "core-same-repo", "structured", 2),
    ("pyfakefs-file-wrapper-io-capabilities", "core-same-repo", "no_memory", 2),
    ("dagster-subset-partition-definition-selection", "core-cross-repo", "structured", 2),
    ("dagster-subset-partition-definition-selection", "core-cross-repo", "no_memory", 2),
    ("pdm-target-project-options-loading", "core-same-repo", "no_memory", 2),
    ("pdm-target-project-options-loading", "core-same-repo", "structured", 2),
    ("fusesoc-retained-parse-error-diagnostics", "core-cross-repo", "structured", 2),
    ("fusesoc-retained-parse-error-diagnostics", "core-cross-repo", "no_memory", 2),
    ("loguru-post-2038-local-timezone-fallback", "core-same-repo", "no_memory", 2),
    ("loguru-post-2038-local-timezone-fallback", "core-same-repo", "structured", 2),
    ("kubeflow-exit-handler-after-dependencies", "core-cross-repo", "structured", 2),
    ("kubeflow-exit-handler-after-dependencies", "core-cross-repo", "no_memory", 2),
    ("tox-dotted-version-factor-base-python", "core-same-repo", "no_memory", 2),
    ("tox-dotted-version-factor-base-python", "core-same-repo", "structured", 2),
    ("mtplx-mixed-content-tool-call-stream", "core-cross-repo", "structured", 2),
    ("mtplx-mixed-content-tool-call-stream", "core-cross-repo", "no_memory", 2),
    ("hf-hub-custom-tqdm-class-contract", "core-same-repo", "structured", 2),
    ("hf-hub-custom-tqdm-class-contract", "core-same-repo", "no_memory", 2),
    ("sqlglot-duckdb-ignore-nulls-modifier-order", "core-cross-repo", "no_memory", 2),
    ("sqlglot-duckdb-ignore-nulls-modifier-order", "core-cross-repo", "structured", 2),
    ("anyio-extensionless-entrypoint-worker-main", "core-same-repo", "no_memory", 2),
    ("anyio-extensionless-entrypoint-worker-main", "core-same-repo", "structured", 2),
)

TASK_ORDER: tuple[str, ...] = (
    "sqlglot-duckdb-ignore-nulls-modifier-order",
    "param-shared-rx-fanout-cache",
    "mtplx-mixed-content-tool-call-stream",
    "fusesoc-retained-parse-error-diagnostics",
    "hf-hub-custom-tqdm-class-contract",
    "pdm-target-project-options-loading",
    "anyio-extensionless-entrypoint-worker-main",
    "tox-dotted-version-factor-base-python",
    "loguru-post-2038-local-timezone-fallback",
    "pyfakefs-file-wrapper-io-capabilities",
    "dagster-subset-partition-definition-selection",
    "kubeflow-exit-handler-after-dependencies",
)


def _parse_projection(
    value: HeldoutACOutcomeProjection | Mapping[str, Any],
) -> HeldoutACOutcomeProjection:
    try:
        if isinstance(value, HeldoutACOutcomeProjection):
            return HeldoutACOutcomeProjection.model_validate(value.model_dump(mode="python"))
        if not isinstance(value, Mapping):
            raise HeldoutACAnalysisError("projection must be a typed projection or mapping")
        return HeldoutACOutcomeProjection.model_validate(value)
    except ValidationError as exc:
        raise HeldoutACAnalysisError("held-out outcome projection contract is invalid") from exc


def _complete_panel_rows(
    projection: HeldoutACOutcomeProjection,
) -> tuple[HeldoutACOutcomeRow, ...]:
    by_order: dict[int, HeldoutACOutcomeRow] = {}
    seen_cells: set[tuple[str, int, str]] = set()
    for row in projection.rows:
        cell = (row.task_id, row.repetition, row.condition)
        if row.order in by_order or cell in seen_cells:
            raise HeldoutACAnalysisError("projection contains a duplicate scheduled row")
        by_order[row.order] = row
        seen_cells.add(cell)
    if set(by_order) != set(range(1, 49)):
        raise HeldoutACAnalysisError(
            "projection does not contain every scheduled order exactly once"
        )

    ordered = tuple(by_order[index] for index in range(1, 49))
    for index, (row, expected) in enumerate(zip(ordered, EXPECTED_SCHEDULE, strict=True), start=1):
        identity = (row.task_id, row.role, row.condition, row.repetition)
        if identity != expected:
            raise HeldoutACAnalysisError(f"scheduled identity differs at order {index}")
        if row.outcome.matrix_inconclusive_triggers:
            raise HeldoutACAnalysisError(
                f"scheduled row {index} carries a matrix-inconclusive confound"
            )
    return ordered


def _row_success(row: HeldoutACOutcomeRow) -> int:
    outcome = row.outcome
    if isinstance(outcome, TypedAgentTerminalOutcome):
        return 0
    return int(
        outcome.hidden_verdict == "PASS"
        and outcome.regression_verdict == "PASS"
        and outcome.scope_verdict == "PASS"
        and outcome.safety_verdict == "PASS"
    )


@cache
def _percentile_draw_indices() -> bytes:
    """Return the sealed 1,200,000 deterministic rejection-sampled task indices."""

    threshold = 18_446_744_073_709_551_612
    selected = bytearray()
    prefix = "heldout-ac-percentile-v1|20260814"
    for sample in range(SAMPLE_COUNT):
        for draw in range(12):
            nonce = 0
            while True:
                preimage = f"{prefix}|b={sample}|j={draw}|nonce={nonce}".encode("ascii")
                digest = hashlib.sha256(preimage).digest()
                value = int.from_bytes(digest[:8], "big", signed=False)
                if value < threshold:
                    selected.append(value % 12)
                    break
                nonce += 1
    return bytes(selected)


def _stability_endpoints(integerized_effects: tuple[int, ...]) -> tuple[Fraction, Fraction]:
    draws = _percentile_draw_indices()
    sums: list[int] = []
    offset = 0
    for _sample in range(SAMPLE_COUNT):
        sample_sum = 0
        for task_index in draws[offset : offset + 12]:
            sample_sum += integerized_effects[task_index]
        sums.append(sample_sum)
        offset += 12
    sums.sort()
    lower = Fraction(sums[2_499] + 39 * sums[2_500], 960)
    upper = Fraction(39 * sums[97_499] + sums[97_500], 960)
    return lower, upper


def _sign_flip(integerized_effects: tuple[int, ...]) -> SignFlipSensitivity:
    observed = abs(sum(integerized_effects))
    extreme = 0
    for mask in range(SIGN_VECTOR_COUNT):
        statistic = abs(
            sum(
                effect if mask & (1 << index) else -effect
                for index, effect in enumerate(integerized_effects)
            )
        )
        extreme += statistic >= observed
    return SignFlipSensitivity(
        status="sensitivity-reference-only",
        observed_abs_integer_statistic=observed,
        extreme_or_equal_sign_vectors=extreme,
        sign_vectors_enumerated=SIGN_VECTOR_COUNT,
        p_value=ReducedRational.from_fraction(Fraction(extreme, SIGN_VECTOR_COUNT)),
        design_based_randomization_inference_authorized=False,
        headline_use_authorized=False,
    )


def _resource_delta(
    rows_by_cell: dict[tuple[str, int, str], HeldoutACOutcomeRow],
    field: str,
    *,
    scale: int = 1,
) -> ReducedRational:
    total_difference = 0
    for task_id in TASK_ORDER:
        for repetition in (1, 2):
            structured = rows_by_cell[(task_id, repetition, "structured")]
            no_memory = rows_by_cell[(task_id, repetition, "no_memory")]
            total_difference += getattr(structured.usage, field) - getattr(no_memory.usage, field)
    return ReducedRational.from_fraction(Fraction(total_difference, 24 * scale))


def _condition_summary(
    condition: Condition,
    rows: tuple[HeldoutACOutcomeRow, ...],
) -> ConditionSummary:
    condition_rows = [row for row in rows if row.condition == condition]
    successes = sum(_row_success(row) for row in condition_rows)
    cost_nanos = sum(row.usage.model_cost_nanos for row in condition_rows)
    total_cost = Fraction(cost_nanos, 1_000_000_000)
    return ConditionSummary(
        condition=condition,
        eligible_rows=24,
        successes=successes,
        success_rate=ReducedRational.from_fraction(Fraction(successes, 24)),
        total_model_cost_usd=ReducedRational.from_fraction(total_cost),
        cost_per_success_usd=(
            ReducedRational.from_fraction(total_cost / successes) if successes else None
        ),
        cost_per_success_status=("defined" if successes else "undefined-zero-success-denominator"),
    )


def _role_stratum(
    role: Role,
    rows_by_cell: dict[tuple[str, int, str], HeldoutACOutcomeRow],
) -> RoleStratum:
    task_ids = [
        task_id for task_id in TASK_ORDER if rows_by_cell[(task_id, 1, "no_memory")].role == role
    ]
    if len(task_ids) != 6:
        raise HeldoutACAnalysisError("prespecified role stratum does not contain six tasks")
    total_difference = 0
    for task_id in task_ids:
        for repetition in (1, 2):
            total_difference += _row_success(
                rows_by_cell[(task_id, repetition, "structured")]
            ) - _row_success(rows_by_cell[(task_id, repetition, "no_memory")])
    return RoleStratum(
        role=role,
        task_clusters=6,
        eligible_rows=24,
        estimate=ReducedRational.from_fraction(Fraction(total_difference, 12)),
        status="secondary-descriptive",
    )


def _verdict_distribution(
    verdict: Literal["hidden", "regression", "scope", "safety"],
    rows: tuple[HeldoutACOutcomeRow, ...],
) -> VerdictDistribution:
    attribute = f"{verdict}_verdict"
    evaluator_rows = [
        row.outcome for row in rows if isinstance(row.outcome, EvaluatorCompletedOutcome)
    ]
    pass_rows = sum(getattr(outcome, attribute) == "PASS" for outcome in evaluator_rows)
    fail_rows = sum(getattr(outcome, attribute) == "FAIL" for outcome in evaluator_rows)
    return VerdictDistribution(
        verdict=verdict,
        eligible_rows=48,
        pass_rows=pass_rows,
        fail_rows=fail_rows,
        not_run_typed_agent_terminal_rows=48 - len(evaluator_rows),
    )


def analyze_heldout_ac(
    projection: HeldoutACOutcomeProjection | Mapping[str, Any],
) -> HeldoutACAnalysis:
    """Compute the preregistered analysis only for an exact eligible 48-row panel."""

    parsed = _parse_projection(projection)
    rows = _complete_panel_rows(parsed)
    rows_by_cell = {(row.task_id, row.repetition, row.condition): row for row in rows}

    task_effect_rows: list[TaskEffect] = []
    integerized_effects: list[int] = []
    benefit_count = 0
    negative_transfer_count = 0
    for task_id in TASK_ORDER:
        task_difference = 0
        for repetition in (1, 2):
            no_memory = _row_success(rows_by_cell[(task_id, repetition, "no_memory")])
            structured = _row_success(rows_by_cell[(task_id, repetition, "structured")])
            task_difference += structured - no_memory
            benefit_count += no_memory == 0 and structured == 1
            negative_transfer_count += no_memory == 1 and structured == 0
        integerized_effects.append(task_difference)
        task_effect_rows.append(
            TaskEffect(
                task_id=task_id,
                integerized_effect=task_difference,
                effect=ReducedRational.from_fraction(Fraction(task_difference, 2)),
            )
        )

    integerized = tuple(integerized_effects)
    lower, upper = _stability_endpoints(integerized)
    return HeldoutACAnalysis(
        schema_version=ANALYSIS_SCHEMA_VERSION,
        preregistration_id=PREREGISTRATION_ID,
        preregistration_content_hash=PREREGISTRATION_CONTENT_HASH,
        scheduled_rows=48,
        eligible_rows=48,
        task_clusters=12,
        complete_panel=True,
        primary_estimate=ReducedRational.from_fraction(Fraction(sum(integerized), 24)),
        task_effects=task_effect_rows,
        stability_interval=StabilityInterval(
            status="descriptive-stability-only",
            method="deterministic-task-cluster-percentile-resampling",
            samples=SAMPLE_COUNT,
            endpoint_method="hyndman-fan-type-7-zero-based",
            lower=ReducedRational.from_fraction(lower),
            upper=ReducedRational.from_fraction(upper),
            confidence_interval_claim_authorized=False,
        ),
        sign_flip_sensitivity=_sign_flip(integerized),
        role_strata=[
            _role_stratum("core-same-repo", rows_by_cell),
            _role_stratum("core-cross-repo", rows_by_cell),
        ],
        directional_flips=DirectionalFlips(
            pair_count=24,
            benefit_count=benefit_count,
            benefit_rate=ReducedRational.from_fraction(Fraction(benefit_count, 24)),
            negative_transfer_count=negative_transfer_count,
            negative_transfer_rate=ReducedRational.from_fraction(
                Fraction(negative_transfer_count, 24)
            ),
            inference="counts-and-rates-only",
        ),
        verdict_distributions=[
            _verdict_distribution("hidden", rows),
            _verdict_distribution("regression", rows),
            _verdict_distribution("scope", rows),
            _verdict_distribution("safety", rows),
        ],
        resource_deltas=ResourceDeltas(
            input_tokens=_resource_delta(rows_by_cell, "input_tokens"),
            output_tokens=_resource_delta(rows_by_cell, "output_tokens"),
            reasoning_tokens=_resource_delta(rows_by_cell, "reasoning_tokens"),
            total_tokens=_resource_delta(rows_by_cell, "total_tokens"),
            model_cost_usd=_resource_delta(
                rows_by_cell,
                "model_cost_nanos",
                scale=1_000_000_000,
            ),
            model_calls=_resource_delta(rows_by_cell, "model_calls"),
            tool_calls=_resource_delta(rows_by_cell, "tool_calls"),
            wall_time_seconds=_resource_delta(
                rows_by_cell,
                "wall_time_milliseconds",
                scale=1_000,
            ),
        ),
        conditions=[
            _condition_summary("no_memory", rows),
            _condition_summary("structured", rows),
        ],
        causal_general_memory_benefit_claim_authorized=False,
    )


__all__ = [
    "ANALYSIS_SCHEMA_VERSION",
    "EXPECTED_SCHEDULE",
    "PREREGISTRATION_CONTENT_HASH",
    "PREREGISTRATION_ID",
    "SAMPLE_COUNT",
    "SCHEMA_VERSION",
    "SIGN_VECTOR_COUNT",
    "TASK_ORDER",
    "ConditionSummary",
    "DirectionalFlips",
    "EvaluatorCompletedOutcome",
    "HeldoutACAnalysis",
    "HeldoutACAnalysisError",
    "HeldoutACOutcomeProjection",
    "HeldoutACOutcomeRow",
    "HeldoutACUsage",
    "ReducedRational",
    "RoleStratum",
    "ResourceDeltas",
    "SignFlipSensitivity",
    "StabilityInterval",
    "TaskEffect",
    "TypedAgentTerminalOutcome",
    "VerdictDistribution",
    "analyze_heldout_ac",
]
