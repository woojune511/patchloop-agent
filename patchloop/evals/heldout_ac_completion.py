"""Offline completion-contract rehearsal for the preregistered held-out A/C panel.

This module is deliberately I/O-free.  It accepts a fully materialized,
internally hash-bound fixture, verifies the exact 48-row suite and cost
envelope, and exercises ``heldout_ac_analysis``.  It is not the authoritative
persisted-evidence adapter: all outputs remain explicitly unofficial and
analysis-ineligible until a separately qualified adapter binds real files,
receipts, candidate authority, and the dedicated held-out qualifier.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from patchloop.contracts import RunResult
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_analysis import (
    EvaluatorCompletedOutcome,
    HeldoutACAnalysis,
    HeldoutACOutcomeProjection,
    HeldoutACOutcomeRow,
    HeldoutACUsage,
    TypedAgentTerminalOutcome,
    analyze_heldout_ac,
)
from patchloop.evals.heldout_ac_contracts import HELDOUT_AC_SUITE_ID, HeldoutACSuite
from patchloop.util import sha256_json

SCHEMA_VERSION = "heldout-ac-completion-contract-fixture-v1"
COMPLETION_SCHEMA_VERSION = "heldout-ac-completion-contract-projection-v1"
PREREGISTRATION_ID = "core-ac-fixed-bundle-heldout-20260814-v1"
PREREGISTRATION_CONTENT_HASH = (
    "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
)

_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
_RUN_ID_PATTERN = r"^run_[A-Za-z0-9_-]+$"

Condition = Literal["no_memory", "structured"]
Role = Literal["core-same-repo", "core-cross-repo"]
AgentTerminalType = Literal[
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


class HeldoutACTerminalClassification(_StrictFrozenModel):
    """Projection derived from a validated terminal event and failure record."""

    schema_version: Literal["heldout-ac-agent-terminal-classification-v1"]
    terminal_type: AgentTerminalType
    terminal_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    failure_record_id: str = Field(pattern=r"^fail_[A-Za-z0-9_-]+$")
    failure_record_hash: str = Field(pattern=_SHA256_PATTERN)
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACTerminalClassification:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("agent terminal classification content hash mismatch")
        return self


class HeldoutACQualificationProjection(_StrictFrozenModel):
    """Fixture for the future dedicated held-out qualifier contract."""

    schema_version: Literal["heldout-ac-trace-qualification-contract-fixture-v1"]
    source_schema_version: Literal["heldout-ac-trace-qualification-v1"]
    run_id: str = Field(pattern=_RUN_ID_PATTERN)
    qualified: Literal[True]
    trace_integrity_passed: Literal[True]
    leakage_scan_passed: Literal[True]
    evaluation_reached: bool
    outcome_kind: Literal["resolved", "task_failure", "agent_failure"]
    purpose: Literal["core-ac-heldout"]
    experiment_id: Literal[HELDOUT_AC_SUITE_ID]
    dataset_role: Role
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    suite_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    memory_condition: Condition
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_version: Literal["v2"]
    evaluator_v2_source_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_source_qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_hash: str | None = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_file_hash: str | None = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_runtime_authenticated: bool
    evaluator_v2_completion_eligible: bool
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACQualificationProjection:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("trace qualification projection content hash mismatch")
        return self


class HeldoutACDurableUsage(_StrictFrozenModel):
    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    cache_write_input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_output_tokens: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    input_token_count_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    wall_clock_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_usage(self) -> HeldoutACDurableUsage:
        if self.cached_input_tokens + self.cache_write_input_tokens > self.input_tokens:
            raise ValueError("cached and cache-write input exceed total input")
        if self.reasoning_output_tokens > self.output_tokens:
            raise ValueError("reasoning output exceeds total output")
        if self.input_tokens > 4_000_000:
            raise ValueError("held-out cumulative input ceiling exceeded")
        if self.output_tokens > 500_000:
            raise ValueError("held-out cumulative output ceiling exceeded")
        if self.input_tokens + self.output_tokens > 4_500_000:
            raise ValueError("held-out aggregate token ceiling exceeded")
        if self.model_calls > 240 or self.tool_calls > 400:
            raise ValueError("held-out model or tool call ceiling exceeded")
        if self.wall_clock_ms > 3_600_000:
            raise ValueError("held-out wall-clock ceiling exceeded")
        return self

    def token_derived_cost_nanos(self) -> int:
        uncached = self.input_tokens - self.cached_input_tokens - self.cache_write_input_tokens
        return (
            uncached * 750
            + self.cached_input_tokens * 75
            + self.cache_write_input_tokens * 750
            + self.output_tokens * 4_500
        )


class HeldoutACRowSettlementEvidence(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-row-settlement-v1"]
    settled: Literal[True]
    usage: HeldoutACDurableUsage
    token_derived_cost_nanos: int = Field(ge=0)
    persisted_result_file_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_semantic_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_file_hash: str = Field(pattern=_SHA256_PATTERN)
    usage_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_projection_hash: str = Field(pattern=_SHA256_PATTERN)
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_file_hash: str | None = Field(pattern=_SHA256_PATTERN)
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACRowSettlementEvidence:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("row settlement content hash mismatch")
        return self


class HeldoutACCompletionRow(_StrictFrozenModel):
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Role
    condition: Condition
    repetition: Literal[1, 2]
    attempt_status: Literal["terminal"]
    run_id: str = Field(pattern=_RUN_ID_PATTERN)
    retry_performed: Literal[False]
    replacement_performed: Literal[False]
    resume_performed: Literal[False]
    infrastructure_error: None
    qualification_error: None
    diagnostic_error: None
    result: dict[str, Any]
    terminal_classification: HeldoutACTerminalClassification | None
    qualification: HeldoutACQualificationProjection
    settlement: HeldoutACRowSettlementEvidence


class HeldoutACFullScheduleCostQualification(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-full-schedule-cost-qualification-v1"]
    passed: Literal[True]
    fully_settled: Literal[True]
    full_schedule_reserved: Literal[True]
    reserved_runs: Literal[48]
    settled_runs: Literal[48]
    not_started_runs: Literal[0]
    unsettled_runs: Literal[0]
    cost_censoring_events: Literal[0]
    accrued_cost_nanos: int = Field(ge=0, le=252_000_000_000)
    full_schedule_reserve_nanos: Literal[252_000_000_000]
    hard_cap_nanos: Literal[275_000_000_000]
    schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    campaign_cost_control_hash: str = Field(pattern=_SHA256_PATTERN)
    live_resume_supported: Literal[False]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACFullScheduleCostQualification:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("full-schedule cost qualification content hash mismatch")
        return self


class HeldoutACCompletionInput(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-completion-contract-fixture-v1"]
    evidence_status: Literal["offline-untrusted-contract-fixture"]
    persisted_evidence_authenticated: Literal[False]
    source_qualification_present: Literal[False]
    execution_candidate_present: Literal[False]
    paid_approval_present: Literal[False]
    provider_execution_authorized: Literal[False]
    analysis_claim_authorized: Literal[False]
    preregistration_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    preregistration_content_hash: Literal[
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    ]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_candidate_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    runtime_tuple_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    completion_adapter_source_hash: str = Field(pattern=_SHA256_PATTERN)
    analysis_source_hash: str = Field(pattern=_SHA256_PATTERN)
    rows: list[HeldoutACCompletionRow] = Field(min_length=48, max_length=48)
    campaign_cost_qualification: HeldoutACFullScheduleCostQualification
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACCompletionInput:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out completion input content hash mismatch")
        return self


class HeldoutACCompletionProjection(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-completion-contract-projection-v1"]
    evidence_status: Literal["offline-untrusted-contract-fixture"]
    persisted_evidence_authenticated: Literal[False]
    source_qualification_present: Literal[False]
    execution_candidate_present: Literal[False]
    paid_approval_present: Literal[False]
    provider_execution_authorized: Literal[False]
    official: Literal[False]
    preregistration_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    preregistration_content_hash: Literal[
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    ]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_candidate_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    runtime_tuple_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    completion_adapter_source_hash: str = Field(pattern=_SHA256_PATTERN)
    analysis_source_hash: str = Field(pattern=_SHA256_PATTERN)
    expected_runs: Literal[48]
    terminal_runs: Literal[48]
    qualified_runs: Literal[48]
    cost_settled_runs: Literal[48]
    evaluator_completed_runs: int = Field(ge=0, le=48)
    typed_agent_terminal_runs: int = Field(ge=0, le=48)
    task_successes: int = Field(ge=0, le=48)
    task_failures: int = Field(ge=0, le=48)
    contract_checks_passed: Literal[True]
    analysis_ready: Literal[False]
    disposition: Literal["offline-complete-matrix-contract-fixture"]
    outcome_projection: HeldoutACOutcomeProjection
    memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_counts_and_hash(self) -> HeldoutACCompletionProjection:
        rows = self.outcome_projection.rows
        evaluator_completed = sum(row.outcome.kind == "evaluator_completed" for row in rows)
        typed_agent_terminals = sum(
            row.outcome.kind == "typed_pre_evaluator_agent_terminal" for row in rows
        )
        successes = sum(
            row.outcome.kind == "evaluator_completed"
            and all(
                verdict == "PASS"
                for verdict in (
                    row.outcome.hidden_verdict,
                    row.outcome.regression_verdict,
                    row.outcome.scope_verdict,
                    row.outcome.safety_verdict,
                )
            )
            for row in rows
        )
        if self.evaluator_completed_runs + self.typed_agent_terminal_runs != 48:
            raise ValueError("completion outcome counts do not sum to 48")
        if self.task_successes + self.task_failures != 48:
            raise ValueError("completion success counts do not sum to 48")
        if (
            self.evaluator_completed_runs != evaluator_completed
            or self.typed_agent_terminal_runs != typed_agent_terminals
            or self.task_successes != successes
            or self.task_failures != 48 - successes
        ):
            raise ValueError("completion counts differ from the nested outcome projection")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out completion projection content hash mismatch")
        return self


class HeldoutACAnalysisEnvelope(_StrictFrozenModel):
    """Unofficial deterministic preview over an offline contract fixture."""

    schema_version: Literal["heldout-ac-analysis-preview-v1"]
    evidence_status: Literal["offline-untrusted-contract-fixture"]
    official: Literal[False]
    persisted_evidence_authenticated: Literal[False]
    source_qualification_present: Literal[False]
    execution_candidate_present: Literal[False]
    paid_approval_present: Literal[False]
    provider_execution_authorized: Literal[False]
    preregistration_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    preregistration_content_hash: Literal[
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    ]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_candidate_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    runtime_tuple_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    completion_adapter_source_hash: str = Field(pattern=_SHA256_PATTERN)
    analysis_source_hash: str = Field(pattern=_SHA256_PATTERN)
    completion_projection_hash: str = Field(pattern=_SHA256_PATTERN)
    analysis: HeldoutACAnalysis
    complete_panel: Literal[True]
    analysis_ready: Literal[False]
    contract_preview_ready: Literal[True]
    analysis_claim_authorized: Literal[False]
    causal_general_memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACAnalysisEnvelope:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out analysis envelope content hash mismatch")
        return self


class HeldoutACObservedTerminalBinding(_StrictFrozenModel):
    order: int = Field(ge=1, le=47)
    wave: int = Field(ge=1, le=4)
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Role
    condition: Condition
    repetition: Literal[1, 2]
    attempt_status: Literal["terminal"]
    run_id: str = Field(pattern=_RUN_ID_PATTERN)
    cost_settled: Literal[True]
    token_derived_cost_nanos: int = Field(ge=0)
    persisted_result_file_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_file_hash: str = Field(pattern=_SHA256_PATTERN)
    settlement_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    retry_performed: Literal[False]
    replacement_performed: Literal[False]
    resume_performed: Literal[False]


class HeldoutACConfoundedRow(_StrictFrozenModel):
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Role
    condition: Condition
    repetition: Literal[1, 2]
    attempt_status: Literal["terminal", "not_started"]
    run_id: str | None = Field(default=None, pattern=_RUN_ID_PATTERN)
    trigger: MatrixConfound
    confound_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    cost_settled: bool
    token_derived_cost_nanos: int | None = Field(default=None, ge=0)
    retry_performed: Literal[False]
    replacement_performed: Literal[False]
    resume_performed: Literal[False]

    @model_validator(mode="after")
    def validate_attempt_shape(self) -> HeldoutACConfoundedRow:
        if self.attempt_status == "terminal" and self.run_id is None:
            raise ValueError("terminal confound requires a run identity")
        if self.attempt_status == "not_started" and (
            self.run_id is not None
            or self.cost_settled
            or self.token_derived_cost_nanos is not None
        ):
            raise ValueError("not-started confound cannot carry a run or settlement")
        if self.cost_settled is (self.token_derived_cost_nanos is None):
            raise ValueError("confound settlement and token-derived cost must appear together")
        return self


class HeldoutACNotStartedRow(_StrictFrozenModel):
    order: int = Field(ge=2, le=48)
    wave: int = Field(ge=1, le=4)
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Role
    condition: Condition
    repetition: Literal[1, 2]
    attempt_status: Literal["not_started"]
    run_id: None
    reason: Literal["campaign-halted-after-prespecified-confound"]
    trigger: MatrixConfound
    retry_performed: Literal[False]
    replacement_performed: Literal[False]
    resume_performed: Literal[False]


class HeldoutACInconclusiveInput(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-inconclusive-input-v1"]
    evidence_status: Literal["offline-untrusted-contract-fixture"]
    persisted_evidence_authenticated: Literal[False]
    source_qualification_present: Literal[False]
    execution_candidate_present: Literal[False]
    paid_approval_present: Literal[False]
    provider_execution_authorized: Literal[False]
    preregistration_id: Literal["core-ac-fixed-bundle-heldout-20260814-v1"]
    preregistration_content_hash: Literal[
        "sha256:3b75f049649850b7561f310229e1e5429f72ea24024e835ccf4910fb2c901f74"
    ]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_candidate_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    runtime_tuple_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_source_qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    completion_adapter_source_hash: str = Field(pattern=_SHA256_PATTERN)
    analysis_source_hash: str = Field(pattern=_SHA256_PATTERN)
    prior_eligible_terminals: list[HeldoutACObservedTerminalBinding] = Field(max_length=47)
    first_confounded_row: HeldoutACConfoundedRow
    remaining_not_started_rows: list[HeldoutACNotStartedRow] = Field(max_length=47)
    cost_boundary_phase: Literal["not-applicable", "pre-reservation", "post-reservation"]
    full_schedule_reserved: bool
    reserved_runs: int = Field(ge=0, le=48)
    settled_runs: int = Field(ge=0, le=48)
    not_started_runs: int = Field(ge=0, le=48)
    unsettled_runs: int = Field(ge=0, le=1)
    accrued_cost_nanos: int = Field(ge=0, le=252_000_000_000)
    schedule_hash: str = Field(pattern=_SHA256_PATTERN)
    campaign_cost_control_hash: str | None = Field(pattern=_SHA256_PATTERN)
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACInconclusiveInput:
        reservation_trigger = (
            self.first_confounded_row.trigger
            == "full-schedule-reservation-or-hard-cap-boundary-failure"
        )
        if self.cost_boundary_phase == "pre-reservation":
            if not reservation_trigger or self.full_schedule_reserved or self.reserved_runs != 0:
                raise ValueError("pre-reservation failure requires zero reserved runs")
            if self.campaign_cost_control_hash is not None:
                raise ValueError("pre-reservation failure cannot carry a cost-control receipt hash")
        else:
            if not self.full_schedule_reserved or self.reserved_runs != 48:
                raise ValueError("post-reservation evidence requires all 48 runs reserved")
            if self.campaign_cost_control_hash is None:
                raise ValueError("reserved schedule requires a cost-control receipt hash")
            if reservation_trigger is (self.cost_boundary_phase != "post-reservation"):
                raise ValueError("cost boundary phase does not match the confound trigger")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out inconclusive input content hash mismatch")
        return self


class HeldoutACCompleteMatrixReport(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-completion-contract-report-v1"]
    disposition: Literal["offline_complete_matrix_contract_fixture"]
    evidence_status: Literal["offline-untrusted-contract-fixture"]
    official: Literal[False]
    analysis_ready: Literal[False]
    completion: HeldoutACCompletionProjection
    primary_outcome_projection_present: Literal[True]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACCompleteMatrixReport:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("complete held-out report content hash mismatch")
        return self


class HeldoutACInconclusiveMatrixReport(_StrictFrozenModel):
    schema_version: Literal["heldout-ac-completion-contract-report-v1"]
    disposition: Literal["offline_inconclusive_matrix_contract_fixture"]
    evidence_status: Literal["offline-untrusted-contract-fixture"]
    official: Literal[False]
    analysis_ready: Literal[False]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    cost_boundary_phase: Literal["not-applicable", "pre-reservation", "post-reservation"]
    full_schedule_reserved: bool
    reserved_runs: int = Field(ge=0, le=48)
    first_confound_order: int = Field(ge=1, le=48)
    trigger: MatrixConfound
    eligible_terminal_rows: int = Field(ge=0, le=47)
    cost_settled_rows: int = Field(ge=0, le=48)
    not_started_rows: int = Field(ge=0, le=48)
    unsettled_rows: int = Field(ge=0, le=1)
    inconclusive_input_hash: str = Field(pattern=_SHA256_PATTERN)
    primary_outcome_projection: None
    partial_rows_disposition: Literal["diagnostic-only-not-headline"]
    memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_content_hash(self) -> HeldoutACInconclusiveMatrixReport:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("inconclusive held-out report content hash mismatch")
        return self


class HeldoutACCompletionError(ContractError):
    """Raised when the held-out completion projection is incomplete or inconsistent."""


def _parse_suite(value: HeldoutACSuite | Mapping[str, Any]) -> HeldoutACSuite:
    try:
        suite = (
            HeldoutACSuite.model_validate(value.model_dump(mode="python"))
            if isinstance(value, HeldoutACSuite)
            else HeldoutACSuite.model_validate(value)
        )
    except ValidationError as exc:
        raise HeldoutACCompletionError("held-out suite contract is invalid") from exc
    expected_hash = sha256_json(suite.model_dump(mode="json", exclude={"content_hash"}))
    if suite.content_hash != expected_hash:
        raise HeldoutACCompletionError("held-out suite content hash mismatch")
    return suite


def _parse_completion(
    value: HeldoutACCompletionInput | Mapping[str, Any],
) -> HeldoutACCompletionInput:
    try:
        return (
            HeldoutACCompletionInput.model_validate(value.model_dump(mode="python"))
            if isinstance(value, HeldoutACCompletionInput)
            else HeldoutACCompletionInput.model_validate(value)
        )
    except ValidationError as exc:
        raise HeldoutACCompletionError("held-out completion input contract is invalid") from exc


def _exact_typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_typed_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            _exact_typed_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return bool(actual == expected)


def _parse_run_result(raw: dict[str, Any]) -> RunResult:
    try:
        parsed = RunResult.model_validate(raw)
    except ValidationError as exc:
        raise HeldoutACCompletionError("persisted run-result-v2 contract is invalid") from exc
    canonical = parsed.model_dump(mode="json")
    if not _exact_typed_equal(raw, canonical):
        raise HeldoutACCompletionError("persisted run result uses a coercive or reduced shape")
    if parsed.schema_version != "run-result-v2" or parsed.evaluator_contract is None:
        raise HeldoutACCompletionError("held-out completion requires a full run-result-v2")
    return parsed


def heldout_ac_schedule_row_id(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    order: int,
) -> str:
    """Derive the dedicated runtime row identity from sealed suite metadata."""

    expected = next((row for row in suite.schedule if row.order == order), None)
    if expected is None:
        raise HeldoutACCompletionError("held-out schedule order is outside the sealed suite")
    return sha256_json(
        {
            "schema_version": "heldout-ac-schedule-row-v1",
            "suite_id": suite.suite_id,
            "suite_content_hash": suite.content_hash,
            "execution_hash": execution_hash,
            **expected.model_dump(mode="json"),
        }
    )


def heldout_ac_campaign_cost_control_hash(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    schedule_hash: str,
) -> str:
    """Recompute the only acceptable full-schedule cost-control identity."""

    return sha256_json(
        {
            "schema_version": "heldout-ac-full-schedule-cost-control-v1",
            "suite_id": suite.suite_id,
            "suite_content_hash": suite.content_hash,
            "execution_hash": execution_hash,
            "schedule_hash": schedule_hash,
            "scheduled_run_count": 48,
            "per_run_reserve_nanos": 5_250_000_000,
            "full_schedule_reserve_nanos": 252_000_000_000,
            "hard_cap_nanos": 275_000_000_000,
            "cost_censoring_allowed": False,
            "live_resume_supported": False,
        }
    )


def _runtime_schedule_projection(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "order": row.order,
            "wave": row.wave,
            "schedule_row_id": row.schedule_row_id,
            "task_id": row.task_id,
            "role": row.role,
            "condition": row.condition,
            "repetition": row.repetition,
        }
        for row in rows
    ]


def _analysis_usage(usage: HeldoutACDurableUsage, cost_nanos: int) -> HeldoutACUsage:
    return HeldoutACUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        reasoning_tokens=usage.reasoning_output_tokens,
        total_tokens=usage.input_tokens + usage.output_tokens,
        model_cost_nanos=cost_nanos,
        model_calls=usage.model_calls,
        tool_calls=usage.tool_calls,
        wall_time_milliseconds=usage.wall_clock_ms,
    )


def _analysis_row(row: HeldoutACCompletionRow, result: RunResult) -> HeldoutACOutcomeRow:
    if result.evaluation_status == "completed":
        outcome = EvaluatorCompletedOutcome(
            kind="evaluator_completed",
            terminal_outcome=True,
            trace_qualified=True,
            cost_settled=True,
            durable_usage_reconciled=True,
            matrix_inconclusive_triggers=[],
            evaluator_v2_runtime_authenticated=True,
            evaluator_v2_completion_eligible=True,
            hidden_verdict=result.verdicts.hidden_tests.value.upper(),
            regression_verdict=result.verdicts.regression_tests.value.upper(),
            scope_verdict=result.verdicts.scope_policy.value.upper(),
            safety_verdict=result.verdicts.safety_policy.value.upper(),
        )
    else:
        terminal = row.terminal_classification
        if terminal is None:
            raise HeldoutACCompletionError("typed agent terminal has no classification")
        outcome = TypedAgentTerminalOutcome(
            kind="typed_pre_evaluator_agent_terminal",
            terminal_outcome=True,
            trace_qualified=True,
            cost_settled=True,
            durable_usage_reconciled=True,
            matrix_inconclusive_triggers=[],
            evaluator_not_run=True,
            terminal_type=terminal.terminal_type,
        )
    return HeldoutACOutcomeRow(
        order=row.order,
        task_id=row.task_id,
        role=row.role,
        condition=row.condition,
        repetition=row.repetition,
        outcome=outcome,
        usage=_analysis_usage(row.settlement.usage, row.settlement.token_derived_cost_nanos),
    )


def project_heldout_ac_completion_contract_fixture(
    *,
    suite: HeldoutACSuite | Mapping[str, Any],
    completion: HeldoutACCompletionInput | Mapping[str, Any],
) -> HeldoutACCompletionProjection:
    """Rehearse the complete-matrix contract without authenticating runtime evidence."""

    parsed_suite = _parse_suite(suite)
    parsed = _parse_completion(completion)
    if parsed.suite_content_hash != parsed_suite.content_hash:
        raise HeldoutACCompletionError("completion input uses another held-out suite")
    if parsed.execution_candidate_hash != parsed.execution_hash:
        raise HeldoutACCompletionError("execution candidate and execution hash differ")

    rows = sorted(parsed.rows, key=lambda item: item.order)
    if tuple(row.order for row in rows) != tuple(range(1, 49)):
        raise HeldoutACCompletionError("completion rows are not exactly orders 1 through 48")
    if len({row.schedule_row_id for row in rows}) != 48:
        raise HeldoutACCompletionError("completion schedule row identities are not unique")
    if len({row.run_id for row in rows}) != 48:
        raise HeldoutACCompletionError("completion run identities are not unique")

    parsed_results: list[RunResult] = []
    for row, expected in zip(rows, parsed_suite.schedule, strict=True):
        observed_identity = (
            row.order,
            row.wave,
            row.task_id,
            row.role,
            row.condition,
            row.repetition,
        )
        expected_identity = (
            expected.order,
            expected.wave,
            expected.task_id,
            expected.role,
            expected.condition,
            expected.repetition,
        )
        if observed_identity != expected_identity:
            raise HeldoutACCompletionError(f"completion identity differs at order {row.order}")
        qualification = row.qualification
        result = _parse_run_result(row.result)
        parsed_results.append(result)
        settlement = row.settlement
        evaluator_contract = result.evaluator_contract
        assert evaluator_contract is not None
        expected_schedule_row_id = heldout_ac_schedule_row_id(
            suite=parsed_suite,
            execution_hash=parsed.execution_hash,
            order=row.order,
        )
        result_usage = result.usage.model_dump(mode="json")
        expected_usage = {
            key: result_usage[key]
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "cache_write_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
                "model_calls",
                "input_token_count_calls",
                "tool_calls",
                "wall_clock_ms",
            )
        }
        settlement_usage = settlement.usage.model_dump(mode="json")
        recomputed_cost_nanos = settlement.usage.token_derived_cost_nanos()
        if (
            row.schedule_row_id != expected_schedule_row_id
            or result.run_id != row.run_id
            or evaluator_contract.task_id != row.task_id
            or evaluator_contract.evaluator_source_hash != parsed.evaluator_source_hash
            or qualification.run_id != row.run_id
            or qualification.task_id != row.task_id
            or qualification.dataset_role != row.role
            or qualification.memory_condition != row.condition
            or qualification.schedule_row_id != row.schedule_row_id
            or qualification.execution_hash != parsed.execution_hash
            or qualification.suite_hash != parsed_suite.content_hash
            or qualification.outcome_kind != result.outcome_kind.value
            or qualification.evaluator_v2_source_hash != parsed.evaluator_source_hash
            or qualification.evaluator_v2_source_qualification_hash
            != parsed.evaluator_source_qualification_hash
            or settlement.qualification_projection_hash != qualification.content_hash
            or settlement.source_evidence_hash != qualification.source_evidence_hash
            or settlement.persisted_result_semantic_hash != sha256_json(row.result)
            or not _exact_typed_equal(settlement_usage, expected_usage)
            or settlement.token_derived_cost_nanos != recomputed_cost_nanos
            or Decimal(str(result.usage.model_cost_usd))
            != Decimal(recomputed_cost_nanos) / Decimal(1_000_000_000)
        ):
            raise HeldoutACCompletionError(
                f"completion evidence cross-binding differs at order {row.order}"
            )
        verdict_values = tuple(value.value for value in result.verdicts.model_dump().values())
        if result.evaluation_status == "completed":
            if not (
                result.agent_submission_status == "completed"
                and result.outcome_kind.value in {"resolved", "task_failure"}
                and result.terminal_error is None
                and result.official is False
                and all(value in {"pass", "fail"} for value in verdict_values)
                and row.terminal_classification is None
                and qualification.evaluation_reached is True
                and qualification.evaluator_v2_runtime_authenticated is True
                and qualification.evaluator_v2_completion_eligible is True
                and qualification.evaluator_v2_receipt_hash is not None
                and qualification.evaluator_v2_receipt_file_hash is not None
                and settlement.evaluator_v2_receipt_file_hash
                == qualification.evaluator_v2_receipt_file_hash
            ):
                raise HeldoutACCompletionError(
                    f"evaluator-v2 completion evidence differs at order {row.order}"
                )
        elif not (
            result.agent_submission_status == "failed"
            and result.evaluation_status == "not_run"
            and result.outcome_kind.value == "agent_failure"
            and result.terminal_error == {"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"}
            and result.official is False
            and row.terminal_classification is not None
            and qualification.evaluation_reached is False
            and qualification.evaluator_v2_runtime_authenticated is False
            and qualification.evaluator_v2_completion_eligible is False
            and qualification.evaluator_v2_receipt_hash is None
            and qualification.evaluator_v2_receipt_file_hash is None
            and settlement.evaluator_v2_receipt_file_hash is None
        ):
            raise HeldoutACCompletionError(
                f"typed agent-terminal evidence differs at order {row.order}"
            )

    schedule_hash = sha256_json(_runtime_schedule_projection(rows))
    cost = parsed.campaign_cost_qualification
    if cost.schedule_hash != schedule_hash:
        raise HeldoutACCompletionError("cost qualification uses another runtime schedule")
    expected_cost_control_hash = heldout_ac_campaign_cost_control_hash(
        suite=parsed_suite,
        execution_hash=parsed.execution_hash,
        schedule_hash=schedule_hash,
    )
    if cost.campaign_cost_control_hash != expected_cost_control_hash:
        raise HeldoutACCompletionError("campaign cost-control identity differs")
    if cost.accrued_cost_nanos != sum(row.settlement.token_derived_cost_nanos for row in rows):
        raise HeldoutACCompletionError("campaign cost differs from settled row costs")

    analysis_projection = HeldoutACOutcomeProjection(
        schema_version="heldout-ac-outcome-projection-v1",
        preregistration_id=PREREGISTRATION_ID,
        preregistration_content_hash=PREREGISTRATION_CONTENT_HASH,
        rows=[_analysis_row(row, result) for row, result in zip(rows, parsed_results, strict=True)],
    )
    evaluator_completed = sum(result.evaluation_status == "completed" for result in parsed_results)
    successes = sum(
        result.evaluation_status == "completed" and result.outcome_kind.value == "resolved"
        for result in parsed_results
    )
    body = {
        "schema_version": COMPLETION_SCHEMA_VERSION,
        "evidence_status": "offline-untrusted-contract-fixture",
        "persisted_evidence_authenticated": False,
        "source_qualification_present": False,
        "execution_candidate_present": False,
        "paid_approval_present": False,
        "provider_execution_authorized": False,
        "official": False,
        "preregistration_id": PREREGISTRATION_ID,
        "preregistration_content_hash": PREREGISTRATION_CONTENT_HASH,
        "suite_id": HELDOUT_AC_SUITE_ID,
        "suite_content_hash": parsed_suite.content_hash,
        "execution_candidate_hash": parsed.execution_candidate_hash,
        "execution_hash": parsed.execution_hash,
        "runtime_tuple_hash": parsed.runtime_tuple_hash,
        "evaluator_source_hash": parsed.evaluator_source_hash,
        "evaluator_source_qualification_hash": parsed.evaluator_source_qualification_hash,
        "completion_adapter_source_hash": parsed.completion_adapter_source_hash,
        "analysis_source_hash": parsed.analysis_source_hash,
        "expected_runs": 48,
        "terminal_runs": 48,
        "qualified_runs": 48,
        "cost_settled_runs": 48,
        "evaluator_completed_runs": evaluator_completed,
        "typed_agent_terminal_runs": 48 - evaluator_completed,
        "task_successes": successes,
        "task_failures": 48 - successes,
        "contract_checks_passed": True,
        "analysis_ready": False,
        "disposition": "offline-complete-matrix-contract-fixture",
        "outcome_projection": analysis_projection.model_dump(mode="json"),
        "memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
    }
    return HeldoutACCompletionProjection(**body, content_hash=sha256_json(body))


def build_heldout_ac_completion_contract_report(
    completion: HeldoutACCompletionProjection,
) -> HeldoutACCompleteMatrixReport:
    """Wrap an offline fixture projection without granting analysis authority."""

    if not isinstance(completion, HeldoutACCompletionProjection):
        raise HeldoutACCompletionError("complete report requires a typed completion projection")
    body = {
        "schema_version": "heldout-ac-completion-contract-report-v1",
        "disposition": "offline_complete_matrix_contract_fixture",
        "evidence_status": "offline-untrusted-contract-fixture",
        "official": False,
        "analysis_ready": False,
        "completion": completion.model_dump(mode="json"),
        "primary_outcome_projection_present": True,
    }
    return HeldoutACCompleteMatrixReport(**body, content_hash=sha256_json(body))


def project_heldout_ac_inconclusive_contract_fixture(
    *,
    suite: HeldoutACSuite | Mapping[str, Any],
    value: HeldoutACInconclusiveInput | Mapping[str, Any],
) -> HeldoutACInconclusiveMatrixReport:
    """Rehearse the preregistered stop path without sealing runtime evidence."""

    parsed_suite = _parse_suite(suite)
    try:
        parsed = (
            HeldoutACInconclusiveInput.model_validate(value.model_dump(mode="python"))
            if isinstance(value, HeldoutACInconclusiveInput)
            else HeldoutACInconclusiveInput.model_validate(value)
        )
    except ValidationError as exc:
        raise HeldoutACCompletionError("held-out inconclusive input is invalid") from exc
    if parsed.suite_content_hash != parsed_suite.content_hash:
        raise HeldoutACCompletionError("inconclusive input uses another held-out suite")
    if parsed.execution_candidate_hash != parsed.execution_hash:
        raise HeldoutACCompletionError("inconclusive candidate and execution hash differ")

    all_rows: list[Any] = [
        *parsed.prior_eligible_terminals,
        parsed.first_confounded_row,
        *parsed.remaining_not_started_rows,
    ]
    if [row.order for row in all_rows] != list(range(1, 49)):
        raise HeldoutACCompletionError("inconclusive rows are not the exact scheduled order")
    confound_order = parsed.first_confounded_row.order
    if confound_order != len(parsed.prior_eligible_terminals) + 1:
        raise HeldoutACCompletionError("first confound does not follow the observed prefix")
    if any(
        row.trigger != parsed.first_confounded_row.trigger
        for row in parsed.remaining_not_started_rows
    ):
        raise HeldoutACCompletionError("not-started rows use another confound trigger")
    run_ids = [row.run_id for row in parsed.prior_eligible_terminals]
    if parsed.first_confounded_row.run_id is not None:
        run_ids.append(parsed.first_confounded_row.run_id)
    if len(run_ids) != len(set(run_ids)):
        raise HeldoutACCompletionError("inconclusive report contains duplicate run identities")

    for row, expected in zip(all_rows, parsed_suite.schedule, strict=True):
        identity = (
            row.order,
            row.wave,
            row.task_id,
            row.role,
            row.condition,
            row.repetition,
        )
        expected_identity = (
            expected.order,
            expected.wave,
            expected.task_id,
            expected.role,
            expected.condition,
            expected.repetition,
        )
        expected_row_id = heldout_ac_schedule_row_id(
            suite=parsed_suite,
            execution_hash=parsed.execution_hash,
            order=row.order,
        )
        if identity != expected_identity or row.schedule_row_id != expected_row_id:
            raise HeldoutACCompletionError(
                f"inconclusive schedule binding differs at order {row.order}"
            )

    schedule_hash = sha256_json(_runtime_schedule_projection(all_rows))
    expected_control_hash = (
        heldout_ac_campaign_cost_control_hash(
            suite=parsed_suite,
            execution_hash=parsed.execution_hash,
            schedule_hash=schedule_hash,
        )
        if parsed.full_schedule_reserved
        else None
    )
    confound = parsed.first_confounded_row
    expected_settled = len(parsed.prior_eligible_terminals) + int(confound.cost_settled)
    expected_not_started = len(parsed.remaining_not_started_rows) + int(
        confound.attempt_status == "not_started"
    )
    expected_unsettled = int(confound.attempt_status == "terminal" and not confound.cost_settled)
    expected_accrued = sum(
        row.token_derived_cost_nanos for row in parsed.prior_eligible_terminals
    ) + (confound.token_derived_cost_nanos or 0)
    if (
        parsed.schedule_hash != schedule_hash
        or parsed.campaign_cost_control_hash != expected_control_hash
        or parsed.settled_runs != expected_settled
        or parsed.not_started_runs != expected_not_started
        or parsed.unsettled_runs != expected_unsettled
        or parsed.accrued_cost_nanos != expected_accrued
        or expected_settled + expected_not_started + expected_unsettled != 48
    ):
        raise HeldoutACCompletionError("inconclusive campaign counts or cost binding differ")
    if parsed.cost_boundary_phase == "pre-reservation" and (
        parsed.prior_eligible_terminals
        or confound.order != 1
        or confound.attempt_status != "not_started"
        or parsed.settled_runs != 0
        or parsed.not_started_runs != 48
        or parsed.unsettled_runs != 0
        or parsed.accrued_cost_nanos != 0
    ):
        raise HeldoutACCompletionError(
            "pre-reservation failure must precede every run and cost settlement"
        )

    body = {
        "schema_version": "heldout-ac-completion-contract-report-v1",
        "disposition": "offline_inconclusive_matrix_contract_fixture",
        "evidence_status": "offline-untrusted-contract-fixture",
        "official": False,
        "analysis_ready": False,
        "suite_id": HELDOUT_AC_SUITE_ID,
        "suite_content_hash": parsed_suite.content_hash,
        "execution_hash": parsed.execution_hash,
        "cost_boundary_phase": parsed.cost_boundary_phase,
        "full_schedule_reserved": parsed.full_schedule_reserved,
        "reserved_runs": parsed.reserved_runs,
        "first_confound_order": confound.order,
        "trigger": confound.trigger,
        "eligible_terminal_rows": len(parsed.prior_eligible_terminals),
        "cost_settled_rows": parsed.settled_runs,
        "not_started_rows": parsed.not_started_runs,
        "unsettled_rows": parsed.unsettled_runs,
        "inconclusive_input_hash": parsed.content_hash,
        "primary_outcome_projection": None,
        "partial_rows_disposition": "diagnostic-only-not-headline",
        "memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
    }
    return HeldoutACInconclusiveMatrixReport(**body, content_hash=sha256_json(body))


def preview_heldout_ac_completion_analysis(
    completion: HeldoutACCompletionProjection,
) -> HeldoutACAnalysisEnvelope:
    """Compute an unofficial deterministic preview from a contract fixture."""

    if not isinstance(completion, HeldoutACCompletionProjection):
        raise HeldoutACCompletionError(
            "held-out analysis preview requires a typed contract projection"
        )
    expected_completion_hash = sha256_json(
        completion.model_dump(mode="json", exclude={"content_hash"})
    )
    if completion.content_hash != expected_completion_hash:
        raise HeldoutACCompletionError("completion projection content hash mismatch")
    analysis = analyze_heldout_ac(completion.outcome_projection)
    body = {
        "schema_version": "heldout-ac-analysis-preview-v1",
        "evidence_status": "offline-untrusted-contract-fixture",
        "official": False,
        "persisted_evidence_authenticated": False,
        "source_qualification_present": False,
        "execution_candidate_present": False,
        "paid_approval_present": False,
        "provider_execution_authorized": False,
        "preregistration_id": PREREGISTRATION_ID,
        "preregistration_content_hash": PREREGISTRATION_CONTENT_HASH,
        "suite_id": HELDOUT_AC_SUITE_ID,
        "suite_content_hash": completion.suite_content_hash,
        "execution_candidate_hash": completion.execution_candidate_hash,
        "execution_hash": completion.execution_hash,
        "runtime_tuple_hash": completion.runtime_tuple_hash,
        "evaluator_source_hash": completion.evaluator_source_hash,
        "evaluator_source_qualification_hash": (completion.evaluator_source_qualification_hash),
        "completion_adapter_source_hash": completion.completion_adapter_source_hash,
        "analysis_source_hash": completion.analysis_source_hash,
        "completion_projection_hash": completion.content_hash,
        "analysis": analysis.model_dump(mode="json"),
        "complete_panel": True,
        "analysis_ready": False,
        "contract_preview_ready": True,
        "analysis_claim_authorized": False,
        "causal_general_memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
    }
    return HeldoutACAnalysisEnvelope(**body, content_hash=sha256_json(body))


__all__ = [
    "COMPLETION_SCHEMA_VERSION",
    "PREREGISTRATION_CONTENT_HASH",
    "PREREGISTRATION_ID",
    "SCHEMA_VERSION",
    "HeldoutACAnalysisEnvelope",
    "HeldoutACCompleteMatrixReport",
    "HeldoutACCompletionError",
    "HeldoutACCompletionInput",
    "HeldoutACCompletionProjection",
    "HeldoutACCompletionRow",
    "HeldoutACDurableUsage",
    "HeldoutACFullScheduleCostQualification",
    "HeldoutACInconclusiveInput",
    "HeldoutACInconclusiveMatrixReport",
    "HeldoutACNotStartedRow",
    "HeldoutACObservedTerminalBinding",
    "HeldoutACQualificationProjection",
    "HeldoutACRowSettlementEvidence",
    "HeldoutACTerminalClassification",
    "build_heldout_ac_completion_contract_report",
    "heldout_ac_campaign_cost_control_hash",
    "heldout_ac_schedule_row_id",
    "preview_heldout_ac_completion_analysis",
    "project_heldout_ac_completion_contract_fixture",
    "project_heldout_ac_inconclusive_contract_fixture",
]
