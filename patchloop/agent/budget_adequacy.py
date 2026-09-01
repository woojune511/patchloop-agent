"""Pure measurement contract for fixed-budget administrative truncation.

This module does not choose a runtime budget and does not activate the agent.
It freezes how a future complete A/C matrix reports success at its exact
envelope and when token-budget terminals make a higher-budget interpretation
inconclusive.  The zero-terminal criterion is deliberately conservative: the
four resolved R8 public-development rows observed no token terminal, but that
small frame establishes neither an optimal budget nor a population rate.
"""

from __future__ import annotations

import math
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.util import sha256_json

BUDGET_ADEQUACY_CONTRACT_SCHEMA = "lean-harness-budget-adequacy-contract-v1"
BUDGET_ADEQUACY_CONTRACT_ID = "r8-public-development-zero-terminal-criterion-20260816-v1"
BUDGET_ADEQUACY_REPORT_SCHEMA = "lean-harness-budget-adequacy-report-v1"
BUDGET_ENVELOPE_SCHEMA = "lean-harness-budget-envelope-v1"

R8_DEVELOPMENT_EVIDENCE_PATH = (
    "reports/live-pilot/dev-validation-ac-fixed-bundle-readiness-20260814-r8-evidence-r4.json"
)
R8_DEVELOPMENT_EVIDENCE_FILE_BYTES = 19_557
R8_DEVELOPMENT_EVIDENCE_FILE_SHA256 = (
    "sha256:5035421a63d58fededab133b77c72e23ee4ad6d380a37c8d1157ce7480b7c62c"
)
R8_DEVELOPMENT_EVIDENCE_CONTENT_HASH = (
    "sha256:0ef31d2b27a7601800d4352e352f67262e462f19b5c2aef25d1d3f0106aade83"
)

FINALIZATION_RESERVE_PATH = "experiments/lean-harness-finalization-reserve-20260816-v1.json"
FINALIZATION_RESERVE_FILE_BYTES = 6_036
FINALIZATION_RESERVE_FILE_SHA256 = (
    "sha256:30cf34a19c94025777df612b283376be5d08047069f3c49e19b58e950434bf06"
)
FINALIZATION_RESERVE_CONTENT_HASH = (
    "sha256:9458bb1d59d51aaf94a082504a3883d799bf4d807ce7a83376bdc391ab6348db"
)

SATURATION_THRESHOLD_PATH = (
    "experiments/lean-harness-saturation-recovery-public-qualification-20260816-v1.json"
)
SATURATION_THRESHOLD_FILE_BYTES = 10_993
SATURATION_THRESHOLD_FILE_SHA256 = (
    "sha256:99b30c828989b1a2cae28bd1412d27a9d4e9514768b22cea8047780792f13d0e"
)
SATURATION_THRESHOLD_CONTENT_HASH = (
    "sha256:f07374bca99d1046c66f7ade6d96caf2bd06cbafe307dcabcad681f473485db6"
)

ADMISSION_SHADOW_PATH = (
    "experiments/lean-harness-saturation-recovery-shadow-public-qualification-20260816-v2.json"
)
ADMISSION_SHADOW_FILE_BYTES = 365_815
ADMISSION_SHADOW_FILE_SHA256 = (
    "sha256:d046025d4c4277786d0d63fc3f946aa50d0c1481fb3237200f51aebf13de2478"
)
ADMISSION_SHADOW_CONTENT_HASH = (
    "sha256:172359ac848acf18e38fff43117cefd58c4cad691d9180f77008b6bbc8f57916"
)

Condition = Literal["no_memory", "structured"]
OutcomeKind = Literal["resolved", "task_failure", "agent_failure"]
TokenTerminalDimension = Literal["none", "input_tokens", "output_tokens", "total_tokens"]
AggregateLabel = Literal["no_memory", "structured", "overall"]

CONDITIONS: tuple[Condition, ...] = ("no_memory", "structured")
TOKEN_DIMENSIONS = ("input_tokens", "output_tokens", "total_tokens")
REQUIRED_METRICS = (
    "success_at_budget",
    "evaluator_reach",
    "input_output_total_token_terminals",
    "patch_check_diff_submission_milestones",
    "no_new_evidence_turns",
    "patch_rejection_rate",
    "spend",
    "cost_per_success",
)


class EvidenceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    file_bytes: int = Field(gt=0)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ExactRatio(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    numerator: int
    denominator: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_reduced(self) -> Self:
        if math.gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("ratio must be reduced")
        return self


class OptionalRatio(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: Literal["defined", "undefined-zero-denominator"]
    value: ExactRatio | None

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if (self.status == "defined") != (self.value is not None):
            raise ValueError("optional ratio status differs from value")
        return self


class BudgetEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-budget-envelope-v1"]
    max_cumulative_input_tokens: int = Field(gt=0)
    max_cumulative_output_tokens: int = Field(gt=0)
    max_total_tokens: int = Field(gt=0)
    equal_for_all_conditions: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_envelope(self) -> Self:
        if self.max_total_tokens > (
            self.max_cumulative_input_tokens + self.max_cumulative_output_tokens
        ):
            raise ValueError("total token limit exceeds reachable split usage")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("budget envelope hash differs")
        return self


class BudgetAdequacyThresholdContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-budget-adequacy-contract-v1"]
    contract_id: Literal["r8-public-development-zero-terminal-criterion-20260816-v1"]
    status: Literal["PUBLIC_DEVELOPMENT_MEASUREMENT_CONTRACT_RUNTIME_CLOSED"]
    evidence_date: Literal["2026-08-16"]
    evidence_scope: Literal["r8-public-development-only"]
    r8_development_evidence: EvidenceBinding
    finalization_reserve: EvidenceBinding
    saturation_thresholds: EvidenceBinding
    admission_recovery_shadow: EvidenceBinding
    public_task_count: Literal[2]
    public_rows: Literal[4]
    public_rows_per_condition: Literal[2]
    public_realized_schedule_hash: Literal[
        "sha256:26026929c2992473b00ce58af760481d7406509f592b8d7674cb7ac6fa4a9a6d"
    ]
    public_max_cumulative_input_tokens: Literal[3000000]
    public_max_cumulative_output_tokens: Literal[350000]
    public_max_total_tokens: Literal[3350000]
    public_full_schedule_reserve_nanos: Literal[15300000000]
    public_hard_cap_nanos: Literal[18000000000]
    public_settled_model_cost_nanos: Literal[366421500]
    public_resolved_rows: Literal[4]
    public_evaluator_reached_rows: Literal[4]
    public_token_terminal_rows: Literal[0]
    public_patch_milestone_rows: Literal[4]
    public_check_milestone_rows: Literal[4]
    public_diff_milestone_rows: Literal[4]
    public_submission_milestone_rows: Literal[4]
    conditions: tuple[Condition, ...]
    terminal_dimensions: tuple[str, ...]
    required_metrics: tuple[str, ...]
    maximum_overall_token_terminal_rows: Literal[0]
    maximum_per_condition_token_terminal_rows: Literal[0]
    maximum_input_token_terminal_rows: Literal[0]
    maximum_output_token_terminal_rows: Literal[0]
    maximum_total_token_terminal_rows: Literal[0]
    maximum_absolute_condition_terminal_difference_rows: Literal[0]
    terminal_rate_denominator: Literal["all-scheduled-rows"]
    fixed_budget_estimand: Literal["complete-scheduled-row-success-at-exact-envelope"]
    token_terminal_source: Literal["authenticated-typed-terminal-evidence"]
    patch_milestone_definition: Literal["at-least-one-authenticated-successful-mutation"]
    check_milestone_definition: Literal["at-least-one-authenticated-check-completion"]
    diff_milestone_definition: Literal["authenticated-terminal-diff-observed"]
    submission_milestone_definition: Literal["authenticated-submission-observed"]
    no_new_evidence_turn_definition: Literal["typed-loop-detected-event-count"]
    patch_attempt_definition: Literal["successful-mutations-plus-typed-rejected-apply-patch-events"]
    patch_rejection_definition: Literal["typed-rejected-apply-patch-event-count"]
    token_terminals_score_zero: Literal[True]
    complete_case_exclusion_authorized: Literal[False]
    evaluator_reached_subset_as_primary_authorized: Literal[False]
    post_hoc_continuation_authorized: Literal[False]
    condition_specific_budget_relief_authorized: Literal[False]
    threshold_selection_uses_r16: Literal[False]
    threshold_optimality_established: Literal[False]
    population_terminal_rate_bound_established: Literal[False]
    unrestricted_capability_claim_authorized: Literal[False]
    pure_projection_is_official_analysis: Literal[False]
    official_analysis_requires_authenticated_persisted_evidence: Literal[True]
    provider_calls_authorized: Literal[False]
    runner_activation_authorized: Literal[False]
    fresh_panel_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        expected_bindings = (
            EvidenceBinding(
                path=R8_DEVELOPMENT_EVIDENCE_PATH,
                file_bytes=R8_DEVELOPMENT_EVIDENCE_FILE_BYTES,
                file_sha256=R8_DEVELOPMENT_EVIDENCE_FILE_SHA256,
                content_hash=R8_DEVELOPMENT_EVIDENCE_CONTENT_HASH,
            ),
            EvidenceBinding(
                path=FINALIZATION_RESERVE_PATH,
                file_bytes=FINALIZATION_RESERVE_FILE_BYTES,
                file_sha256=FINALIZATION_RESERVE_FILE_SHA256,
                content_hash=FINALIZATION_RESERVE_CONTENT_HASH,
            ),
            EvidenceBinding(
                path=SATURATION_THRESHOLD_PATH,
                file_bytes=SATURATION_THRESHOLD_FILE_BYTES,
                file_sha256=SATURATION_THRESHOLD_FILE_SHA256,
                content_hash=SATURATION_THRESHOLD_CONTENT_HASH,
            ),
            EvidenceBinding(
                path=ADMISSION_SHADOW_PATH,
                file_bytes=ADMISSION_SHADOW_FILE_BYTES,
                file_sha256=ADMISSION_SHADOW_FILE_SHA256,
                content_hash=ADMISSION_SHADOW_CONTENT_HASH,
            ),
        )
        observed_bindings = (
            self.r8_development_evidence,
            self.finalization_reserve,
            self.saturation_thresholds,
            self.admission_recovery_shadow,
        )
        if observed_bindings != expected_bindings:
            raise ValueError("budget adequacy evidence binding differs")
        if self.conditions != CONDITIONS or self.terminal_dimensions != TOKEN_DIMENSIONS:
            raise ValueError("budget adequacy condition or dimension order differs")
        if self.required_metrics != REQUIRED_METRICS:
            raise ValueError("budget adequacy metric inventory differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("budget adequacy contract hash differs")
        return self


class BudgetAdequacyRowObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    observation_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    order: int = Field(ge=1)
    task_id: str = Field(min_length=1)
    condition: Condition
    outcome_kind: OutcomeKind
    success: bool
    evaluator_reached: bool
    token_terminal_dimension: TokenTerminalDimension
    patch_milestone: bool
    check_milestone: bool
    diff_milestone: bool
    submission_milestone: bool
    no_new_evidence_turns: int = Field(ge=0)
    patch_attempts: int = Field(ge=0)
    patch_rejections: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    model_cost_nanos: int = Field(ge=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_row(self) -> Self:
        identity = {
            "order": self.order,
            "task_id": self.task_id,
            "condition": self.condition,
        }
        if self.observation_id != sha256_json(identity):
            raise ValueError("budget adequacy row identity differs")
        if self.success != (self.outcome_kind == "resolved"):
            raise ValueError("budget adequacy success differs from outcome")
        if self.patch_rejections > self.patch_attempts:
            raise ValueError("patch rejections exceed attempts")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("row total tokens differ from split usage")
        if self.evaluator_reached and not self.submission_milestone:
            raise ValueError("evaluator reach requires submission")
        if self.success and not all(
            (
                self.evaluator_reached,
                self.patch_milestone,
                self.check_milestone,
                self.diff_milestone,
                self.submission_milestone,
            )
        ):
            raise ValueError("successful row lacks required milestones")
        if self.token_terminal_dimension != "none" and (
            self.outcome_kind != "agent_failure" or self.success or self.evaluator_reached
        ):
            raise ValueError("token terminal must be a pre-evaluator agent failure")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("budget adequacy row hash differs")
        return self


class BudgetAdequacyAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    label: AggregateLabel
    scheduled_rows: int = Field(gt=0)
    successes: int = Field(ge=0)
    success_rate: ExactRatio
    evaluator_reached_rows: int = Field(ge=0)
    evaluator_reach_rate: ExactRatio
    input_token_terminal_rows: int = Field(ge=0)
    output_token_terminal_rows: int = Field(ge=0)
    total_token_terminal_rows: int = Field(ge=0)
    any_token_terminal_rows: int = Field(ge=0)
    token_terminal_rate: ExactRatio
    patch_milestone_rows: int = Field(ge=0)
    check_milestone_rows: int = Field(ge=0)
    diff_milestone_rows: int = Field(ge=0)
    submission_milestone_rows: int = Field(ge=0)
    no_new_evidence_turns: int = Field(ge=0)
    maximum_no_new_evidence_turns: int = Field(ge=0)
    patch_attempts: int = Field(ge=0)
    patch_rejections: int = Field(ge=0)
    patch_rejection_rate: OptionalRatio
    model_cost_nanos: int = Field(ge=0)
    cost_per_success_nanos: OptionalRatio


class BudgetAdequacyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-budget-adequacy-report-v1"]
    measurement_id: str = Field(min_length=1)
    contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    realized_schedule_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    envelope: BudgetEnvelope
    full_schedule_reserve_nanos: int = Field(gt=0)
    hard_cap_nanos: int = Field(gt=0)
    settled_model_cost_nanos: int = Field(ge=0)
    dollar_cap_boundary_reached: bool
    dollar_cap_truncation_observed: Literal[False]
    expected_rows: int = Field(gt=0)
    rows_per_condition: int = Field(gt=0)
    rows: tuple[BudgetAdequacyRowObservation, ...]
    condition_summaries: tuple[BudgetAdequacyAggregate, ...]
    overall_summary: BudgetAdequacyAggregate
    structured_minus_no_memory_success_rate: ExactRatio
    structured_minus_no_memory_token_terminal_rows: int
    absolute_condition_token_terminal_difference_rows: int = Field(ge=0)
    complete_matrix: Literal[True]
    fixed_budget_primary_status: Literal["estimable-complete-matrix"]
    token_terminals_retained_as_observed_zero: Literal[True]
    budget_adequacy_gate_passed: bool
    administrative_truncation_status: Literal[
        "none-observed-at-frozen-envelope", "exceeds-zero-terminal-criterion"
    ]
    higher_budget_capability_status: Literal[
        "not-identified-no-terminal-observation-only",
        "inconclusive-administrative-truncation",
    ]
    complete_case_exclusion_performed: Literal[False]
    post_hoc_continuation_performed: Literal[False]
    condition_specific_budget_relief_performed: Literal[False]
    threshold_optimality_established: Literal[False]
    population_terminal_rate_bound_established: Literal[False]
    measurement_projection_only: Literal[True]
    official_analysis_authorized: Literal[False]
    unrestricted_capability_claim_authorized: Literal[False]
    runtime_activation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        if self.contract_hash != r8_public_budget_adequacy_contract().content_hash:
            raise ValueError("budget adequacy report contract differs")
        if self.full_schedule_reserve_nanos > self.hard_cap_nanos:
            raise ValueError("full schedule reserve exceeds hard cap")
        try:
            validated_envelope = BudgetEnvelope.model_validate(
                self.envelope.model_dump(mode="python")
            )
            validated_rows = tuple(
                BudgetAdequacyRowObservation.model_validate(row.model_dump(mode="python"))
                for row in self.rows
            )
        except ValueError as exc:
            raise ValueError("budget adequacy nested evidence is invalid") from exc
        if validated_envelope != self.envelope or validated_rows != self.rows:
            raise ValueError("budget adequacy nested evidence differs")
        if self.expected_rows != 2 * self.rows_per_condition:
            raise ValueError("budget adequacy matrix is not equal A/C")
        if len(self.rows) != self.expected_rows:
            raise ValueError("budget adequacy matrix is incomplete")
        if tuple(row.order for row in self.rows) != tuple(range(1, self.expected_rows + 1)):
            raise ValueError("budget adequacy row order differs")
        if len({row.observation_id for row in self.rows}) != len(self.rows):
            raise ValueError("budget adequacy row identity is duplicated")
        for row in self.rows:
            if row.input_tokens > self.envelope.max_cumulative_input_tokens:
                raise ValueError("row input usage exceeds the envelope")
            if row.output_tokens > self.envelope.max_cumulative_output_tokens:
                raise ValueError("row output usage exceeds the envelope")
            if row.total_tokens > self.envelope.max_total_tokens:
                raise ValueError("row total usage exceeds the envelope")
        expected_conditions = tuple(
            _aggregate(condition, tuple(row for row in self.rows if row.condition == condition))
            for condition in CONDITIONS
        )
        if any(item.scheduled_rows != self.rows_per_condition for item in expected_conditions):
            raise ValueError("budget adequacy condition denominator differs")
        if self.condition_summaries != expected_conditions:
            raise ValueError("budget adequacy condition summary differs")
        expected_overall = _aggregate("overall", self.rows)
        if self.overall_summary != expected_overall:
            raise ValueError("budget adequacy overall summary differs")
        if self.settled_model_cost_nanos != expected_overall.model_cost_nanos:
            raise ValueError("budget adequacy settled cost differs")
        if self.settled_model_cost_nanos > self.full_schedule_reserve_nanos:
            raise ValueError("budget adequacy settled cost exceeds full reserve")
        if self.dollar_cap_boundary_reached is not (
            self.settled_model_cost_nanos >= self.hard_cap_nanos
        ):
            raise ValueError("budget adequacy hard-cap boundary differs")
        no_memory, structured = expected_conditions
        expected_success_delta = _ratio(
            structured.successes - no_memory.successes,
            self.rows_per_condition,
        )
        terminal_delta = structured.any_token_terminal_rows - no_memory.any_token_terminal_rows
        if (
            self.structured_minus_no_memory_success_rate != expected_success_delta
            or self.structured_minus_no_memory_token_terminal_rows != terminal_delta
            or self.absolute_condition_token_terminal_difference_rows != abs(terminal_delta)
        ):
            raise ValueError("budget adequacy A/C delta differs")
        expected_gate = expected_overall.any_token_terminal_rows == 0
        if self.budget_adequacy_gate_passed is not expected_gate:
            raise ValueError("budget adequacy gate differs")
        expected_status = (
            "none-observed-at-frozen-envelope"
            if expected_gate
            else "exceeds-zero-terminal-criterion"
        )
        expected_capability = (
            "not-identified-no-terminal-observation-only"
            if expected_gate
            else "inconclusive-administrative-truncation"
        )
        if (
            self.administrative_truncation_status != expected_status
            or self.higher_budget_capability_status != expected_capability
        ):
            raise ValueError("budget adequacy interpretation differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("budget adequacy report hash differs")
        return self


def _ratio(numerator: int, denominator: int) -> ExactRatio:
    divisor = math.gcd(abs(numerator), denominator)
    return ExactRatio(numerator=numerator // divisor, denominator=denominator // divisor)


def _optional_ratio(numerator: int, denominator: int) -> OptionalRatio:
    if denominator == 0:
        return OptionalRatio(status="undefined-zero-denominator", value=None)
    return OptionalRatio(status="defined", value=_ratio(numerator, denominator))


def _aggregate(
    label: AggregateLabel,
    rows: tuple[BudgetAdequacyRowObservation, ...],
) -> BudgetAdequacyAggregate:
    if not rows:
        raise ValueError("budget adequacy aggregate cannot be empty")
    scheduled = len(rows)
    successes = sum(row.success for row in rows)
    evaluator = sum(row.evaluator_reached for row in rows)
    dimensions = {
        dimension: sum(row.token_terminal_dimension == dimension for row in rows)
        for dimension in TOKEN_DIMENSIONS
    }
    any_terminal = sum(dimensions.values())
    patch_attempts = sum(row.patch_attempts for row in rows)
    patch_rejections = sum(row.patch_rejections for row in rows)
    cost_nanos = sum(row.model_cost_nanos for row in rows)
    return BudgetAdequacyAggregate(
        label=label,
        scheduled_rows=scheduled,
        successes=successes,
        success_rate=_ratio(successes, scheduled),
        evaluator_reached_rows=evaluator,
        evaluator_reach_rate=_ratio(evaluator, scheduled),
        input_token_terminal_rows=dimensions["input_tokens"],
        output_token_terminal_rows=dimensions["output_tokens"],
        total_token_terminal_rows=dimensions["total_tokens"],
        any_token_terminal_rows=any_terminal,
        token_terminal_rate=_ratio(any_terminal, scheduled),
        patch_milestone_rows=sum(row.patch_milestone for row in rows),
        check_milestone_rows=sum(row.check_milestone for row in rows),
        diff_milestone_rows=sum(row.diff_milestone for row in rows),
        submission_milestone_rows=sum(row.submission_milestone for row in rows),
        no_new_evidence_turns=sum(row.no_new_evidence_turns for row in rows),
        maximum_no_new_evidence_turns=max(row.no_new_evidence_turns for row in rows),
        patch_attempts=patch_attempts,
        patch_rejections=patch_rejections,
        patch_rejection_rate=_optional_ratio(patch_rejections, patch_attempts),
        model_cost_nanos=cost_nanos,
        cost_per_success_nanos=_optional_ratio(cost_nanos, successes),
    )


def r8_public_budget_adequacy_contract() -> BudgetAdequacyThresholdContract:
    """Return the zero-authority public-development measurement contract."""

    body = {
        "schema_version": BUDGET_ADEQUACY_CONTRACT_SCHEMA,
        "contract_id": BUDGET_ADEQUACY_CONTRACT_ID,
        "status": "PUBLIC_DEVELOPMENT_MEASUREMENT_CONTRACT_RUNTIME_CLOSED",
        "evidence_date": "2026-08-16",
        "evidence_scope": "r8-public-development-only",
        "r8_development_evidence": {
            "path": R8_DEVELOPMENT_EVIDENCE_PATH,
            "file_bytes": R8_DEVELOPMENT_EVIDENCE_FILE_BYTES,
            "file_sha256": R8_DEVELOPMENT_EVIDENCE_FILE_SHA256,
            "content_hash": R8_DEVELOPMENT_EVIDENCE_CONTENT_HASH,
        },
        "finalization_reserve": {
            "path": FINALIZATION_RESERVE_PATH,
            "file_bytes": FINALIZATION_RESERVE_FILE_BYTES,
            "file_sha256": FINALIZATION_RESERVE_FILE_SHA256,
            "content_hash": FINALIZATION_RESERVE_CONTENT_HASH,
        },
        "saturation_thresholds": {
            "path": SATURATION_THRESHOLD_PATH,
            "file_bytes": SATURATION_THRESHOLD_FILE_BYTES,
            "file_sha256": SATURATION_THRESHOLD_FILE_SHA256,
            "content_hash": SATURATION_THRESHOLD_CONTENT_HASH,
        },
        "admission_recovery_shadow": {
            "path": ADMISSION_SHADOW_PATH,
            "file_bytes": ADMISSION_SHADOW_FILE_BYTES,
            "file_sha256": ADMISSION_SHADOW_FILE_SHA256,
            "content_hash": ADMISSION_SHADOW_CONTENT_HASH,
        },
        "public_task_count": 2,
        "public_rows": 4,
        "public_rows_per_condition": 2,
        "public_realized_schedule_hash": (
            "sha256:26026929c2992473b00ce58af760481d7406509f592b8d7674cb7ac6fa4a9a6d"
        ),
        "public_max_cumulative_input_tokens": 3_000_000,
        "public_max_cumulative_output_tokens": 350_000,
        "public_max_total_tokens": 3_350_000,
        "public_full_schedule_reserve_nanos": 15_300_000_000,
        "public_hard_cap_nanos": 18_000_000_000,
        "public_settled_model_cost_nanos": 366_421_500,
        "public_resolved_rows": 4,
        "public_evaluator_reached_rows": 4,
        "public_token_terminal_rows": 0,
        "public_patch_milestone_rows": 4,
        "public_check_milestone_rows": 4,
        "public_diff_milestone_rows": 4,
        "public_submission_milestone_rows": 4,
        "conditions": CONDITIONS,
        "terminal_dimensions": TOKEN_DIMENSIONS,
        "required_metrics": REQUIRED_METRICS,
        "maximum_overall_token_terminal_rows": 0,
        "maximum_per_condition_token_terminal_rows": 0,
        "maximum_input_token_terminal_rows": 0,
        "maximum_output_token_terminal_rows": 0,
        "maximum_total_token_terminal_rows": 0,
        "maximum_absolute_condition_terminal_difference_rows": 0,
        "terminal_rate_denominator": "all-scheduled-rows",
        "fixed_budget_estimand": "complete-scheduled-row-success-at-exact-envelope",
        "token_terminal_source": "authenticated-typed-terminal-evidence",
        "patch_milestone_definition": "at-least-one-authenticated-successful-mutation",
        "check_milestone_definition": "at-least-one-authenticated-check-completion",
        "diff_milestone_definition": "authenticated-terminal-diff-observed",
        "submission_milestone_definition": "authenticated-submission-observed",
        "no_new_evidence_turn_definition": "typed-loop-detected-event-count",
        "patch_attempt_definition": ("successful-mutations-plus-typed-rejected-apply-patch-events"),
        "patch_rejection_definition": "typed-rejected-apply-patch-event-count",
        "token_terminals_score_zero": True,
        "complete_case_exclusion_authorized": False,
        "evaluator_reached_subset_as_primary_authorized": False,
        "post_hoc_continuation_authorized": False,
        "condition_specific_budget_relief_authorized": False,
        "threshold_selection_uses_r16": False,
        "threshold_optimality_established": False,
        "population_terminal_rate_bound_established": False,
        "unrestricted_capability_claim_authorized": False,
        "pure_projection_is_official_analysis": False,
        "official_analysis_requires_authenticated_persisted_evidence": True,
        "provider_calls_authorized": False,
        "runner_activation_authorized": False,
        "fresh_panel_authorized": False,
    }
    return BudgetAdequacyThresholdContract.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def build_budget_envelope(
    *,
    max_cumulative_input_tokens: int,
    max_cumulative_output_tokens: int,
    max_total_tokens: int,
) -> BudgetEnvelope:
    values = (
        max_cumulative_input_tokens,
        max_cumulative_output_tokens,
        max_total_tokens,
    )
    if any(type(value) is not int for value in values):
        raise TypeError("budget envelope values must be exact integers")
    body = {
        "schema_version": BUDGET_ENVELOPE_SCHEMA,
        "max_cumulative_input_tokens": max_cumulative_input_tokens,
        "max_cumulative_output_tokens": max_cumulative_output_tokens,
        "max_total_tokens": max_total_tokens,
        "equal_for_all_conditions": True,
    }
    return BudgetEnvelope.model_validate({**body, "content_hash": sha256_json(body)})


def build_budget_adequacy_row(**values: object) -> BudgetAdequacyRowObservation:
    """Build one strictly hashed row observation."""

    if {"observation_id", "content_hash"} & values.keys():
        raise ValueError("row identity and content hash are derived fields")
    identity = {
        "order": values.get("order"),
        "task_id": values.get("task_id"),
        "condition": values.get("condition"),
    }
    body = {"observation_id": sha256_json(identity), **values}
    return BudgetAdequacyRowObservation.model_validate({**body, "content_hash": sha256_json(body)})


def project_budget_adequacy(
    *,
    measurement_id: str,
    expected_rows: int,
    realized_schedule_hash: str,
    envelope: BudgetEnvelope,
    full_schedule_reserve_nanos: int,
    hard_cap_nanos: int,
    rows: tuple[BudgetAdequacyRowObservation, ...],
) -> BudgetAdequacyReport:
    """Project a complete equal-A/C matrix under the frozen measurement rule."""

    if type(measurement_id) is not str or not measurement_id:
        raise ValueError("measurement_id must be a nonempty exact string")
    if type(expected_rows) is not int or expected_rows <= 0 or expected_rows % 2:
        raise ValueError("expected_rows must be a positive even exact integer")
    if (
        type(realized_schedule_hash) is not str
        or len(realized_schedule_hash) != 71
        or not realized_schedule_hash.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in realized_schedule_hash[7:])
    ):
        raise ValueError("realized_schedule_hash must be an exact SHA-256 value")
    if (
        type(full_schedule_reserve_nanos) is not int
        or type(hard_cap_nanos) is not int
        or full_schedule_reserve_nanos <= 0
        or hard_cap_nanos <= 0
        or full_schedule_reserve_nanos > hard_cap_nanos
    ):
        raise ValueError("campaign cost envelope is invalid")
    if type(envelope) is not BudgetEnvelope:
        raise TypeError("envelope must be an exact BudgetEnvelope")
    if type(rows) is not tuple or not rows:
        raise TypeError("rows must be a nonempty exact tuple")
    if any(type(row) is not BudgetAdequacyRowObservation for row in rows):
        raise TypeError("rows must contain exact BudgetAdequacyRowObservation values")
    envelope = BudgetEnvelope.model_validate(envelope.model_dump(mode="python"))
    rows = tuple(
        BudgetAdequacyRowObservation.model_validate(row.model_dump(mode="python")) for row in rows
    )
    if len(rows) != expected_rows:
        raise ValueError("budget adequacy matrix is incomplete")
    rows_per_condition = expected_rows // 2
    condition_summaries = tuple(
        _aggregate(condition, tuple(row for row in rows if row.condition == condition))
        for condition in CONDITIONS
    )
    if any(item.scheduled_rows != rows_per_condition for item in condition_summaries):
        raise ValueError("budget adequacy matrix must have equal A/C rows")
    overall = _aggregate("overall", rows)
    if overall.model_cost_nanos > full_schedule_reserve_nanos:
        raise ValueError("settled model cost exceeds the full schedule reserve")
    no_memory, structured = condition_summaries
    terminal_delta = structured.any_token_terminal_rows - no_memory.any_token_terminal_rows
    gate = overall.any_token_terminal_rows == 0
    body = {
        "schema_version": BUDGET_ADEQUACY_REPORT_SCHEMA,
        "measurement_id": measurement_id,
        "contract_hash": r8_public_budget_adequacy_contract().content_hash,
        "realized_schedule_hash": realized_schedule_hash,
        "envelope": envelope.model_dump(mode="python"),
        "full_schedule_reserve_nanos": full_schedule_reserve_nanos,
        "hard_cap_nanos": hard_cap_nanos,
        "settled_model_cost_nanos": overall.model_cost_nanos,
        "dollar_cap_boundary_reached": overall.model_cost_nanos >= hard_cap_nanos,
        "dollar_cap_truncation_observed": False,
        "expected_rows": expected_rows,
        "rows_per_condition": rows_per_condition,
        "rows": tuple(row.model_dump(mode="python") for row in rows),
        "condition_summaries": tuple(
            item.model_dump(mode="python") for item in condition_summaries
        ),
        "overall_summary": overall.model_dump(mode="python"),
        "structured_minus_no_memory_success_rate": _ratio(
            structured.successes - no_memory.successes,
            rows_per_condition,
        ).model_dump(mode="python"),
        "structured_minus_no_memory_token_terminal_rows": terminal_delta,
        "absolute_condition_token_terminal_difference_rows": abs(terminal_delta),
        "complete_matrix": True,
        "fixed_budget_primary_status": "estimable-complete-matrix",
        "token_terminals_retained_as_observed_zero": True,
        "budget_adequacy_gate_passed": gate,
        "administrative_truncation_status": (
            "none-observed-at-frozen-envelope" if gate else "exceeds-zero-terminal-criterion"
        ),
        "higher_budget_capability_status": (
            "not-identified-no-terminal-observation-only"
            if gate
            else "inconclusive-administrative-truncation"
        ),
        "complete_case_exclusion_performed": False,
        "post_hoc_continuation_performed": False,
        "condition_specific_budget_relief_performed": False,
        "threshold_optimality_established": False,
        "population_terminal_rate_bound_established": False,
        "measurement_projection_only": True,
        "official_analysis_authorized": False,
        "unrestricted_capability_claim_authorized": False,
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
    }
    return BudgetAdequacyReport.model_validate({**body, "content_hash": sha256_json(body)})


__all__ = [
    "ADMISSION_SHADOW_CONTENT_HASH",
    "ADMISSION_SHADOW_FILE_BYTES",
    "ADMISSION_SHADOW_FILE_SHA256",
    "ADMISSION_SHADOW_PATH",
    "BUDGET_ADEQUACY_CONTRACT_ID",
    "BUDGET_ADEQUACY_CONTRACT_SCHEMA",
    "BUDGET_ADEQUACY_REPORT_SCHEMA",
    "BudgetAdequacyReport",
    "BudgetAdequacyRowObservation",
    "BudgetAdequacyThresholdContract",
    "BudgetEnvelope",
    "EvidenceBinding",
    "ExactRatio",
    "FINALIZATION_RESERVE_CONTENT_HASH",
    "FINALIZATION_RESERVE_FILE_BYTES",
    "FINALIZATION_RESERVE_FILE_SHA256",
    "FINALIZATION_RESERVE_PATH",
    "R8_DEVELOPMENT_EVIDENCE_CONTENT_HASH",
    "R8_DEVELOPMENT_EVIDENCE_FILE_BYTES",
    "R8_DEVELOPMENT_EVIDENCE_FILE_SHA256",
    "R8_DEVELOPMENT_EVIDENCE_PATH",
    "SATURATION_THRESHOLD_CONTENT_HASH",
    "SATURATION_THRESHOLD_FILE_BYTES",
    "SATURATION_THRESHOLD_FILE_SHA256",
    "SATURATION_THRESHOLD_PATH",
    "build_budget_adequacy_row",
    "build_budget_envelope",
    "project_budget_adequacy",
    "r8_public_budget_adequacy_contract",
]
