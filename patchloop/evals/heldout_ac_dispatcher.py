"""Authoritative append-only dispatcher for the preregistered held-out A/C panel.

Importing this module grants no runtime authority.  A campaign can start only
from a persisted no-call candidate whose exact execution hash has a separate
paid approval.  Every row is consumed once before provider entry, authenticated
from durable evaluator-v2/qualification/usage files, and settled before the next
row.  Any prespecified confound stops the panel and seals the remainder as not
started; no retry, replacement or resume path exists.
"""

from __future__ import annotations

import json
import os
from contextlib import ExitStack
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from patchloop.agent.runner import AgentRunner, issue_live_execution_authorization
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import EvaluatorV2EvaluationReceipt, EventType, RunResult
from patchloop.environment import (
    exact_openai_api_key_environment,
    exact_openai_api_key_present,
)
from patchloop.errors import (
    ContractError,
    EvaluatorControlContractCollision,
    UntrustedPrivateMarkerHit,
)
from patchloop.evals.heldout_ac_analysis import (
    HeldoutACAnalysis,
    HeldoutACOutcomeProjection,
)
from patchloop.evals.heldout_ac_completion import (
    HeldoutACAuthenticatedCompletionProjection,
    HeldoutACDurableUsage,
    HeldoutACOfficialAnalysisEnvelope,
    analyze_authenticated_heldout_ac_completion,
    project_authenticated_heldout_ac_completion,
    validate_persisted_heldout_ac_completion_replay,
)
from patchloop.evals.heldout_ac_contracts import (
    HELDOUT_AC_SUITE_ID,
    HeldoutACFrozenModel,
)
from patchloop.evals.heldout_ac_execution import (
    HeldoutACExecutionCandidate,
    build_heldout_ac_run_manifest,
    heldout_ac_campaign_identity_hash,
    heldout_ac_candidate_token_limits,
    materialize_heldout_ac_runtime_task_authority,
)
from patchloop.evals.heldout_ac_live_contract import (
    JOURNAL_SCHEMA_VERSION_V2,
    PLAN_KIND_V2,
    PLAN_SCHEMA_VERSION_V2,
    _exact_typed_equal,
    _load_journal_events,
    canonical_heldout_ac_runtime_path,
    heldout_ac_candidate_has_bound_source_qualification,
    heldout_ac_candidate_has_current_source_binding,
    heldout_ac_runtime_contract,
    heldout_ac_terminal_cost_settled_payload,
    validate_heldout_ac_dispatch_plan,
)
from patchloop.evals.heldout_ac_persisted_adapter import (
    HELDOUT_AC_PRICE_NANOS_PER_TOKEN,
    EvaluatorFailureCode,
    HeldoutACAgentTerminalEventProjection,
    HeldoutACAuthenticatedPersistedEvidence,
    HeldoutACAuthenticatedPersistedRow,
    HeldoutACEvaluatorConfoundEvidence,
    HeldoutACPersistedUsageEvidence,
    authenticate_heldout_ac_persisted_evidence,
    validate_heldout_ac_persisted_usage_cross_binding,
)
from patchloop.evals.heldout_ac_suite import load_heldout_ac_suite
from patchloop.runtime import make_run_id, repository_root, runtime_root
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, sha256_json, utc_now

CAMPAIGN_RESULT_SCHEMA_VERSION = "heldout-ac-authoritative-campaign-result-v1"
CAMPAIGN_RESULT_SCHEMA_VERSION_V2 = "heldout-ac-authoritative-campaign-result-v2"
PREPARED_RESULT_SCHEMA_VERSION = "heldout-ac-campaign-prepared-result-v1"
PREPARED_RESULT_SCHEMA_VERSION_V2 = "heldout-ac-campaign-prepared-result-v2"
SETTLED_ROW_SCHEMA_VERSION = "heldout-ac-settled-campaign-row-v1"
SETTLED_ROW_SCHEMA_VERSION_V2 = "heldout-ac-settled-campaign-row-v2"
CONFOUND_SCHEMA_VERSION = "heldout-ac-campaign-confound-v1"
CONFOUND_SCHEMA_VERSION_V2 = "heldout-ac-campaign-confound-v2"
CONFOUND_EVIDENCE_SCHEMA_VERSION = "heldout-ac-confounded-durable-evidence-v1"
COST_OBSERVATION_SCHEMA_VERSION = "heldout-ac-dispatched-cost-observation-v1"
NOT_STARTED_SCHEMA_VERSION = "heldout-ac-campaign-not-started-row-v1"

MatrixConfound = Literal[
    "provider-sdk-docker-or-evaluator-infrastructure-error",
    "qualification-or-completion-contract-mismatch",
    "private-marker-or-leakage-hit",
    "schedule-treatment-runtime-source-or-hash-drift",
    "missing-durable-usage-or-cost-settlement",
    "duplicate-retried-replaced-or-resumed-row",
    "full-schedule-reservation-or-hard-cap-boundary-failure",
]
ConfoundPhase = Literal[
    "row-dispatch",
    "cost-observation",
    "qualification",
    "authentication",
    "settlement",
]
ConfoundReasonCode = Literal[
    "EVALUATOR_CONTROL_CONTRACT_COLLISION",
    "UNTRUSTED_PRIVATE_MARKER_HIT",
    "DURABLE_EVIDENCE_AUTHENTICATION_FAILED",
    "QUALIFICATION_FAILED",
    "SETTLEMENT_FAILED",
    "ROW_DISPATCH_FAILED",
    "COST_OBSERVATION_FAILED",
]
AgentTerminalType = Literal[
    "token-budget-exhaustion",
    "model-call-limit",
    "tool-call-limit",
    "wall-clock-timeout",
    "submission-failure",
]

_SUITE_PATH = Path("experiments/heldout-ac-suite-20260814-v1.yaml")
_DATASET_PATH = Path("data/dataset-manifest.yaml")
_PRICES = dict(HELDOUT_AC_PRICE_NANOS_PER_TOKEN)


class HeldoutACDispatcherError(ContractError):
    """The dedicated campaign dispatcher failed closed."""


class HeldoutACSettledCampaignRow(HeldoutACFrozenModel):
    schema_version: Literal[SETTLED_ROW_SCHEMA_VERSION] = SETTLED_ROW_SCHEMA_VERSION
    authenticated_row: HeldoutACAuthenticatedPersistedRow
    terminal_type: AgentTerminalType | None
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_settled_row(self) -> HeldoutACSettledCampaignRow:
        evaluator_completed = self.authenticated_row.result.evaluation_status == "completed"
        if evaluator_completed != (self.terminal_type is None):
            raise ValueError("held-out settled row terminal classification differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out settled row content hash differs")
        return self


class HeldoutACSettledCampaignRowV2(HeldoutACFrozenModel):
    schema_version: Literal[SETTLED_ROW_SCHEMA_VERSION_V2] = SETTLED_ROW_SCHEMA_VERSION_V2
    authenticated_evidence: HeldoutACAuthenticatedPersistedEvidence
    agent_terminal_event_relative_path: str | None
    agent_terminal_event_file_sha256: str | None = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    agent_terminal_event_content_hash: str | None = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @property
    def authenticated_row(self) -> HeldoutACAuthenticatedPersistedRow:
        return self.authenticated_evidence.row

    @property
    def terminal_type(self) -> AgentTerminalType | None:
        return self.authenticated_evidence.terminal_type

    @model_validator(mode="after")
    def validate_settled_row(self) -> HeldoutACSettledCampaignRowV2:
        terminal_fields = (
            self.agent_terminal_event_relative_path,
            self.agent_terminal_event_file_sha256,
            self.agent_terminal_event_content_hash,
        )
        terminal_event = self.authenticated_evidence.terminal_event
        if not (
            all(value is None for value in terminal_fields)
            and terminal_event is None
            or all(value is not None for value in terminal_fields)
            and terminal_event is not None
            and self.agent_terminal_event_content_hash == terminal_event.content_hash
        ):
            raise ValueError("held-out settled row terminal sidecar binding differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out settled row v2 content hash differs")
        return self


class HeldoutACCampaignConfound(HeldoutACFrozenModel):
    schema_version: Literal[CONFOUND_SCHEMA_VERSION] = CONFOUND_SCHEMA_VERSION
    order: int = Field(ge=1, le=48)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    trigger: MatrixConfound
    phase: ConfoundPhase
    exception_type: str = Field(min_length=1)
    run_started_event_written: bool
    secret_or_exception_message_persisted: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_confound(self) -> HeldoutACCampaignConfound:
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign confound content hash differs")
        return self


class HeldoutACDispatchedCostObservation(HeldoutACFrozenModel):
    schema_version: Literal[COST_OBSERVATION_SCHEMA_VERSION] = COST_OBSERVATION_SCHEMA_VERSION
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    pricing_binding_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    price_nanos_per_token: dict[str, int]
    usage: HeldoutACDurableUsage
    result_relative_path: str
    result_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    result_semantic_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    token_derived_cost_nanos: int = Field(ge=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_observation(self) -> HeldoutACDispatchedCostObservation:
        if self.price_nanos_per_token != _PRICES:
            raise ValueError("held-out cost observation price binding differs")
        if self.token_derived_cost_nanos != self.usage.token_derived_cost_nanos():
            raise ValueError("held-out cost observation counters differ")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out cost observation content hash differs")
        return self


class HeldoutACEvaluatorFailureEventProjection(HeldoutACFrozenModel):
    """Safe locator and hash projection of one persisted evaluator RunFailed event."""

    event_id: str = Field(min_length=1)
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    sequence: int = Field(ge=1)
    type: Literal["RunFailed"]
    timestamp: str
    actor: Literal["runner"]
    error_code: EvaluatorFailureCode
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_projection(self) -> HeldoutACEvaluatorFailureEventProjection:
        try:
            parsed_timestamp = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("evaluator failure event timestamp is invalid") from exc
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if not (
            self.timestamp.endswith("Z")
            and parsed_timestamp.tzinfo is not None
            and parsed_timestamp.utcoffset() == UTC.utcoffset(parsed_timestamp)
            and self.content_hash == expected
        ):
            raise ValueError("evaluator failure event projection hash differs")
        return self


class HeldoutACConfoundedDurableEvidence(HeldoutACFrozenModel):
    schema_version: Literal[CONFOUND_EVIDENCE_SCHEMA_VERSION] = CONFOUND_EVIDENCE_SCHEMA_VERSION
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    result_relative_path: str
    result_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    result_semantic_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cost_observation_relative_path: str
    cost_observation_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cost_observation_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    qualification_relative_path: str | None = None
    qualification_file_sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    qualification_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    usage_relative_path: str | None = None
    usage_file_sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    usage_evidence_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    receipt_relative_path: str | None = None
    receipt_file_sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    receipt_content_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_failure_code: EvaluatorFailureCode | None = None
    evaluator_failure_event_relative_path: str | None = None
    evaluator_failure_event_file_sha256: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    evaluator_failure_event_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_failure_event: HeldoutACEvaluatorFailureEventProjection | None = None
    token_derived_cost_nanos: int = Field(ge=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> HeldoutACConfoundedDurableEvidence:
        qualification_fields = (
            self.qualification_relative_path,
            self.qualification_file_sha256,
            self.qualification_hash,
        )
        usage_fields = (
            self.usage_relative_path,
            self.usage_file_sha256,
            self.usage_evidence_hash,
        )
        if any(value is None for value in qualification_fields) != all(
            value is None for value in qualification_fields
        ):
            raise ValueError("confounded qualification evidence must be complete or absent")
        if any(value is None for value in usage_fields) != all(
            value is None for value in usage_fields
        ):
            raise ValueError("confounded usage evidence must be complete or absent")
        if self.usage_relative_path is not None and self.qualification_relative_path is None:
            raise ValueError("confounded usage evidence requires qualification evidence")
        if (self.receipt_relative_path is None) != (self.receipt_file_sha256 is None) or (
            self.receipt_relative_path is None
        ) != (self.receipt_content_hash is None):
            raise ValueError("confounded receipt evidence must be complete or absent")
        if self.receipt_relative_path is not None and self.usage_relative_path is None:
            raise ValueError("confounded receipt evidence requires usage evidence")
        failure_fields = (
            self.evaluator_failure_code,
            self.evaluator_failure_event_relative_path,
            self.evaluator_failure_event_file_sha256,
            self.evaluator_failure_event_hash,
            self.evaluator_failure_event,
        )
        if any(value is None for value in failure_fields) != all(
            value is None for value in failure_fields
        ):
            raise ValueError("confounded evaluator failure evidence must be complete or absent")
        if self.evaluator_failure_event is not None and self.usage_relative_path is None:
            raise ValueError("confounded evaluator failure event requires usage evidence")
        if self.evaluator_failure_event is not None and not (
            self.evaluator_failure_event.run_id == self.run_id
            and self.evaluator_failure_event.error_code == self.evaluator_failure_code
            and self.evaluator_failure_event.content_hash == self.evaluator_failure_event_hash
        ):
            raise ValueError("confounded evaluator failure event binding differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("confounded durable evidence content hash differs")
        return self


class HeldoutACCampaignConfoundV2(HeldoutACFrozenModel):
    schema_version: Literal[CONFOUND_SCHEMA_VERSION_V2] = CONFOUND_SCHEMA_VERSION_V2
    order: int = Field(ge=1, le=48)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    trigger: MatrixConfound
    phase: ConfoundPhase
    reason_code: ConfoundReasonCode
    exception_type: str = Field(min_length=1)
    run_started_event_written: bool
    durable_evidence: HeldoutACConfoundedDurableEvidence | None
    secret_or_exception_message_persisted: Literal[False] = False
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_confound(self) -> HeldoutACCampaignConfoundV2:
        if self.durable_evidence is not None and (
            not self.run_started_event_written or self.durable_evidence.run_id != self.run_id
        ):
            raise ValueError("confounded durable evidence requires the started run")
        if (
            self.durable_evidence is not None
            and self.durable_evidence.evaluator_failure_code is not None
            and self.reason_code != self.durable_evidence.evaluator_failure_code
        ):
            raise ValueError("confounded reason differs from the persisted evaluator failure")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign confound v2 content hash differs")
        return self


class HeldoutACNotStartedRow(HeldoutACFrozenModel):
    schema_version: Literal[NOT_STARTED_SCHEMA_VERSION] = NOT_STARTED_SCHEMA_VERSION
    order: int = Field(ge=1, le=48)
    schedule_row_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_id: str
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    reason: Literal["campaign-stopped-after-prespecified-confound"]
    trigger: MatrixConfound


class HeldoutACCampaignResult(HeldoutACFrozenModel):
    schema_version: Literal[CAMPAIGN_RESULT_SCHEMA_VERSION] = CAMPAIGN_RESULT_SCHEMA_VERSION
    evidence_status: Literal["authenticated-persisted-campaign"]
    disposition: Literal["complete-matrix", "inconclusive-matrix"]
    suite_id: Literal[HELDOUT_AC_SUITE_ID]
    suite_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_qualification_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evaluator_source_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_plan_path: str
    execution_plan_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    journal_path: str
    journal_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    campaign_completed_event_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prepared_result_path: str
    prepared_result_file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prepared_result_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_runs: Literal[48]
    terminal_settled_runs: int = Field(ge=0, le=48)
    not_started_runs: int = Field(ge=0, le=48)
    settled_model_cost_nanos: int = Field(ge=0, le=275_000_000_000)
    unsettled_dispatched_runs: int = Field(ge=0, le=1)
    cost_accounting_complete: bool
    full_schedule_reserve_nanos: int = Field(gt=0)
    hard_cap_nanos: int = Field(gt=0)
    settled_rows: tuple[HeldoutACSettledCampaignRow, ...]
    confound: HeldoutACCampaignConfound | None
    not_started_rows: tuple[HeldoutACNotStartedRow, ...]
    outcome_projection: HeldoutACOutcomeProjection | None
    analysis: HeldoutACAnalysis | None
    analysis_ready: bool
    official_heldout_analysis: bool
    memory_benefit_claim_authorized: Literal[False]
    broad_generalization_claim_authorized: Literal[False]
    retry_replacement_or_resume_performed: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_result(self) -> HeldoutACCampaignResult:
        if type(self) is not HeldoutACCampaignResult:
            return self
        settled_orders = tuple(row.authenticated_row.order for row in self.settled_rows)
        not_started_orders = tuple(row.order for row in self.not_started_rows)
        if self.terminal_settled_runs != len(self.settled_rows):
            raise ValueError("held-out settled run count differs")
        if self.not_started_runs != len(self.not_started_rows):
            raise ValueError("held-out not-started run count differs")
        if (self.full_schedule_reserve_nanos, self.hard_cap_nanos) not in {
            (252_000_000_000, 275_000_000_000),
            (57_600_000_000, 60_000_000_000),
        }:
            raise ValueError("held-out result cost boundary differs")
        if self.settled_model_cost_nanos != sum(
            row.authenticated_row.usage_evidence.token_derived_cost_nanos
            for row in self.settled_rows
        ):
            raise ValueError("held-out settled model cost differs")
        expected_unsettled = int(
            self.confound is not None and self.confound.run_started_event_written
        )
        if (
            self.unsettled_dispatched_runs != expected_unsettled
            or self.cost_accounting_complete != (expected_unsettled == 0)
        ):
            raise ValueError("held-out unsettled dispatch accounting differs")
        if self.disposition == "complete-matrix":
            complete = (
                settled_orders == tuple(range(1, 49))
                and not not_started_orders
                and self.confound is None
                and self.outcome_projection is not None
                and self.analysis is not None
                and self.analysis_ready is True
                and self.official_heldout_analysis is True
            )
        else:
            confound_order = self.confound.order if self.confound is not None else None
            complete = (
                settled_orders == tuple(range(1, len(settled_orders) + 1))
                and confound_order == len(settled_orders) + 1
                and not_started_orders == tuple(range(confound_order + 1, 49))
                and self.outcome_projection is None
                and self.analysis is None
                and self.analysis_ready is False
                and self.official_heldout_analysis is False
            )
        if not complete:
            raise ValueError("held-out result disposition does not match its rows")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign result content hash differs")
        return self


class HeldoutACCampaignResultV2(HeldoutACCampaignResult):
    schema_version: Literal[CAMPAIGN_RESULT_SCHEMA_VERSION_V2] = CAMPAIGN_RESULT_SCHEMA_VERSION_V2
    observed_unsettled_model_cost_nanos: int = Field(ge=0)
    observed_started_model_cost_nanos: int = Field(ge=0)
    authenticated_completion: HeldoutACAuthenticatedCompletionProjection | None
    official_analysis_envelope: HeldoutACOfficialAnalysisEnvelope | None
    settled_rows: tuple[HeldoutACSettledCampaignRowV2, ...]
    confound: HeldoutACCampaignConfoundV2 | None

    @model_validator(mode="after")
    def validate_result_v2(self) -> HeldoutACCampaignResultV2:
        settled_orders = tuple(row.authenticated_row.order for row in self.settled_rows)
        not_started_orders = tuple(row.order for row in self.not_started_rows)
        settled_cost = sum(
            row.authenticated_row.usage_evidence.token_derived_cost_nanos
            for row in self.settled_rows
        )
        observed_unsettled = (
            self.confound.durable_evidence.token_derived_cost_nanos
            if self.confound is not None and self.confound.durable_evidence is not None
            else 0
        )
        expected_unsettled_runs = int(
            self.confound is not None and self.confound.run_started_event_written
        )
        accounting_complete = bool(
            self.confound is None
            or not self.confound.run_started_event_written
            or self.confound.durable_evidence is not None
        )
        if not (
            self.terminal_settled_runs == len(self.settled_rows)
            and self.not_started_runs == len(self.not_started_rows)
            and self.settled_model_cost_nanos == settled_cost
            and self.observed_unsettled_model_cost_nanos == observed_unsettled
            and self.observed_started_model_cost_nanos == settled_cost + observed_unsettled
            and self.unsettled_dispatched_runs == expected_unsettled_runs
            and self.cost_accounting_complete == accounting_complete
        ):
            raise ValueError("held-out campaign v2 counts or cost accounting differ")
        if self.disposition == "complete-matrix":
            complete = (
                settled_orders == tuple(range(1, 49))
                and not not_started_orders
                and self.confound is None
                and self.outcome_projection is not None
                and self.analysis is not None
                and self.analysis_ready is True
                and self.official_heldout_analysis is True
                and self.authenticated_completion is not None
                and self.official_analysis_envelope is not None
                and self.authenticated_completion.outcome_projection == self.outcome_projection
                and self.official_analysis_envelope.analysis == self.analysis
                and self.authenticated_completion.execution_hash == self.execution_hash
                and self.authenticated_completion.suite_content_hash == self.suite_content_hash
                and self.authenticated_completion.evaluator_source_hash
                == self.evaluator_source_hash
                and self.authenticated_completion.evaluator_source_qualification_hash
                == self.source_qualification_hash
                and self.official_analysis_envelope.completion_projection_hash
                == self.authenticated_completion.content_hash
            )
        else:
            confound_order = self.confound.order if self.confound is not None else None
            complete = (
                settled_orders == tuple(range(1, len(settled_orders) + 1))
                and confound_order == len(settled_orders) + 1
                and not_started_orders == tuple(range(confound_order + 1, 49))
                and self.outcome_projection is None
                and self.analysis is None
                and self.analysis_ready is False
                and self.official_heldout_analysis is False
                and self.authenticated_completion is None
                and self.official_analysis_envelope is None
            )
        if not complete:
            raise ValueError("held-out result v2 disposition does not match its rows")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("held-out campaign result v2 content hash differs")
        return self


def _root(path: str | Path | None) -> Path:
    return Path(path).absolute() if path is not None else runtime_root().absolute()


def _repository(path: str | Path | None) -> Path:
    return Path(path).resolve() if path is not None else repository_root().resolve()


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise HeldoutACDispatcherError("held-out dispatcher timestamp must be UTC")
    return value.isoformat().replace("+00:00", "Z")


def _write_new(path: Path, content: bytes, *, run_root: Path) -> None:
    canonical = canonical_heldout_ac_runtime_path(path, expected_run_root=run_root)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical = canonical_heldout_ac_runtime_path(canonical, expected_run_root=run_root)
    if canonical.exists() or canonical.is_symlink():
        raise HeldoutACDispatcherError(f"append-only held-out path already exists: {path.name}")
    try:
        with canonical.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise HeldoutACDispatcherError(
            f"append-only held-out path already exists: {path.name}"
        ) from exc


def _campaign_ledger_path(run_root: Path, campaign_identity_hash: str) -> Path:
    return (
        run_root
        / "experiments"
        / "heldout-ac"
        / "one-use"
        / f"{campaign_identity_hash.removeprefix('sha256:')}.json"
    )


def heldout_ac_paid_campaign_identity_consumed(
    candidate: HeldoutACExecutionCandidate,
    *,
    root: str | Path | None = None,
) -> bool:
    """Read only whether this source/suite/schedule already received a paid plan."""

    run_root = _root(root)
    identity = heldout_ac_campaign_identity_hash(candidate)
    ledger = canonical_heldout_ac_runtime_path(
        _campaign_ledger_path(run_root, identity),
        expected_run_root=run_root,
    )
    if ledger.exists() or ledger.is_symlink():
        return True
    plans = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "plans",
        expected_run_root=run_root,
    )
    if not plans.is_dir():
        return False
    for path in plans.glob("*.json"):
        try:
            canonical_plan = canonical_heldout_ac_runtime_path(
                path,
                expected_run_root=run_root,
            )
        except ContractError:
            return True
        try:
            payload = json.loads(canonical_plan.read_bytes())
            raw_candidate = payload.get("candidate") if isinstance(payload, dict) else None
            parsed = _candidate_from_mapping(raw_candidate)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ContractError):
            continue
        if heldout_ac_campaign_identity_hash(parsed) == identity:
            return True
    return False


def _claim_paid_campaign_identity(
    candidate: HeldoutACExecutionCandidate,
    *,
    run_root: Path,
    claimed_at: datetime,
) -> tuple[Path, bytes, str]:
    identity = heldout_ac_campaign_identity_hash(candidate)
    if heldout_ac_paid_campaign_identity_consumed(candidate, root=run_root):
        raise HeldoutACDispatcherError(
            "held-out paid campaign identity was already consumed by this source and schedule"
        )
    body = {
        "schema_version": (
            "heldout-ac-paid-campaign-one-use-v1"
            if candidate.schema_version == "heldout-ac-execution-candidate-v1"
            else "heldout-ac-paid-campaign-one-use-v2"
        ),
        "campaign_identity_hash": identity,
        "execution_hash": candidate.execution_hash,
        "suite_content_hash": candidate.suite_content_hash,
        "source_qualification_hash": (candidate.source_qualification.source_qualification_hash),
        "base_schedule_hash": candidate.base_schedule_hash,
        "scheduled_run_count": 48,
        "full_schedule_reserve_nanos": (
            candidate.campaign_cost_control.full_schedule_reserve_nanos
        ),
        "hard_cap_nanos": candidate.campaign_cost_control.hard_cap_nanos,
        "claimed_at": _utc_text(claimed_at),
    }
    payload = {**body, "content_hash": sha256_json(body)}
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path = _campaign_ledger_path(run_root, identity)
    _write_new(path, encoded, run_root=run_root)
    return path, encoded, payload["content_hash"]


def _candidate_from_mapping(
    value: HeldoutACExecutionCandidate | dict[str, Any],
) -> HeldoutACExecutionCandidate:
    try:
        candidate = (
            HeldoutACExecutionCandidate.model_validate(value.model_dump(mode="python"))
            if isinstance(value, HeldoutACExecutionCandidate)
            else HeldoutACExecutionCandidate.model_validate_json(json.dumps(value))
        )
    except ValidationError as exc:
        raise HeldoutACDispatcherError("held-out candidate contract is invalid") from exc
    return candidate


def prepare_heldout_ac_approved_plan(
    *,
    candidate: HeldoutACExecutionCandidate | dict[str, Any],
    approve_live_cost: bool,
    approved_execution_hash: str,
    root: str | Path | None = None,
    repository: str | Path | None = None,
    created_at: datetime | None = None,
) -> Path:
    """Persist one new-only paid plan after exact external approval."""

    if type(approve_live_cost) is not bool or approve_live_cost is not True:
        raise HeldoutACDispatcherError("held-out paid approval must be the exact boolean true")
    parsed = _candidate_from_mapping(candidate)
    if approved_execution_hash != parsed.execution_hash:
        raise HeldoutACDispatcherError("held-out paid approval hash differs from the candidate")
    suite = load_heldout_ac_suite(_SUITE_PATH, repository=_repository(repository))
    if parsed.suite_content_hash != suite.content_hash:
        raise HeldoutACDispatcherError("held-out candidate uses another suite")
    if not heldout_ac_candidate_has_current_source_binding(
        parsed,
        repository=_repository(repository),
    ):
        raise HeldoutACDispatcherError(
            "held-out candidate source qualification differs from the current successor"
        )
    run_root = _root(root)
    digest = parsed.execution_hash.removeprefix("sha256:")
    plan_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "plans" / f"{digest}.json",
        expected_run_root=run_root,
    )
    journal_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "journals" / f"{digest}.jsonl",
        expected_run_root=run_root,
    )
    result_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "heldout-ac" / f"{digest}.json",
        expected_run_root=run_root,
    )
    ledger_path = canonical_heldout_ac_runtime_path(
        _campaign_ledger_path(
            run_root,
            heldout_ac_campaign_identity_hash(parsed),
        ),
        expected_run_root=run_root,
    )
    if any(path.exists() or path.is_symlink() for path in (journal_path, result_path)):
        raise HeldoutACDispatcherError("held-out campaign identity already has runtime state")
    claimed_at = created_at or utc_now()
    ledger_path, ledger_bytes, ledger_content_hash = _claim_paid_campaign_identity(
        parsed,
        run_root=run_root,
        claimed_at=claimed_at,
    )
    body = {
        "schema_version": PLAN_SCHEMA_VERSION_V2,
        "plan_kind": PLAN_KIND_V2,
        "created_at": _utc_text(claimed_at),
        "ready": True,
        "blockers": [],
        "suite": suite.model_dump(mode="json"),
        "candidate": parsed.model_dump(mode="json", exclude_none=True),
        "execution_hash": parsed.execution_hash,
        "schedule_hash": parsed.schedule_hash,
        "runtime_contract": heldout_ac_runtime_contract(parsed),
        "campaign_cost_control": parsed.campaign_cost_control.model_dump(mode="json"),
        "approval": {
            "invocation_approve_live_cost": True,
            "invocation_approved_execution_hash": parsed.execution_hash,
            "matches_execution_hash": True,
            "scheduled_run_count": 48,
            "full_schedule_reserve_nanos": (
                parsed.campaign_cost_control.full_schedule_reserve_nanos
            ),
            "hard_cap_nanos": parsed.campaign_cost_control.hard_cap_nanos,
        },
        "journal_path": str(journal_path),
        "result_path": str(result_path),
        "campaign_identity_hash": heldout_ac_campaign_identity_hash(parsed),
        "campaign_one_use_ledger_path": str(ledger_path),
        "campaign_one_use_ledger_file_sha256": sha256_bytes(ledger_bytes),
        "campaign_one_use_ledger_content_hash": ledger_content_hash,
    }
    encoded = (json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    _write_new(plan_path, encoded, run_root=run_root)
    return plan_path


def _load_approved_plan(execution_hash: str, run_root: Path) -> tuple[dict[str, Any], bytes]:
    expected_plan_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "plans" / f"{execution_hash.removeprefix('sha256:')}.json",
        expected_run_root=run_root,
    )
    authorization = issue_live_execution_authorization(execution_hash, root=run_root)
    try:
        plan_path = canonical_heldout_ac_runtime_path(
            authorization.plan_path,
            expected_run_root=run_root,
        )
        raw = plan_path.read_bytes()
        plan = json.loads(raw)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        raise HeldoutACDispatcherError("held-out approved plan is unavailable") from exc
    if (
        plan_path != expected_plan_path
        or not isinstance(plan, dict)
        or sha256_bytes(raw) != authorization.plan_hash
    ):
        raise HeldoutACDispatcherError("held-out approved plan bytes differ")
    _candidate_from_mapping(plan.get("candidate"))
    return plan, raw


def _journal_event(
    *,
    sequence: int,
    event_type: str,
    payload: dict[str, Any],
    previous_event_hash: str | None,
    recorded_at: datetime | None = None,
    schema_version: str = JOURNAL_SCHEMA_VERSION_V2,
) -> dict[str, Any]:
    body = {
        "schema_version": schema_version,
        "sequence": sequence,
        "event_type": event_type,
        "recorded_at": _utc_text(recorded_at or utc_now()),
        "previous_event_hash": previous_event_hash,
        "payload": payload,
    }
    return {**body, "event_hash": sha256_json(body)}


def _create_journal(
    path: Path,
    candidate: HeldoutACExecutionCandidate,
    plan_hash: str,
    *,
    run_root: Path,
) -> None:
    started = _journal_event(
        sequence=1,
        event_type="CampaignStarted",
        payload={
            "suite_id": candidate.suite_id,
            "suite_content_hash": candidate.suite_content_hash,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": plan_hash,
            "schedule_hash": candidate.schedule_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "expected_runs": 48,
        },
        previous_event_hash=None,
    )
    reserved = _journal_event(
        sequence=2,
        event_type="FullScheduleCostReserved",
        payload={
            "suite_id": candidate.suite_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": plan_hash,
            "schedule_hash": candidate.schedule_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "reserved_runs": 48,
            "per_run_reserve_nanos": candidate.campaign_cost_control.per_run_reserve_nanos,
            "full_schedule_reserve_nanos": (
                candidate.campaign_cost_control.full_schedule_reserve_nanos
            ),
            "hard_cap_nanos": candidate.campaign_cost_control.hard_cap_nanos,
            "cost_censoring_allowed": False,
        },
        previous_event_hash=started["event_hash"],
    )
    encoded = (
        json.dumps(started, sort_keys=True, separators=(",", ":"))
        + "\n"
        + json.dumps(reserved, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    _write_new(path, encoded, run_root=run_root)


def _append_journal(
    path: Path,
    event_type: str,
    payload: dict[str, Any],
    *,
    run_root: Path,
) -> dict[str, Any]:
    canonical = canonical_heldout_ac_runtime_path(path, expected_run_root=run_root)
    try:
        raw = canonical.read_bytes()
        last = json.loads(raw.decode("utf-8").splitlines()[-1])
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, IndexError) as exc:
        raise HeldoutACDispatcherError("held-out journal prefix is unavailable") from exc
    event = _journal_event(
        sequence=int(last["sequence"]) + 1,
        event_type=event_type,
        payload=payload,
        previous_event_hash=last["event_hash"],
        schema_version=str(last["schema_version"]),
    )
    encoded = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    canonical = canonical_heldout_ac_runtime_path(canonical, expected_run_root=run_root)
    with canonical.open("ab") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    return event


def _row_identity(row: Any) -> dict[str, Any]:
    return {
        "order": row.order,
        "wave": row.wave,
        "schedule_row_id": row.schedule_row_id,
        "task_id": row.task_id,
        "role": row.role,
        "condition": row.condition,
        "repetition": row.repetition,
    }


def _append_terminal_cost_settled(
    journal_path: Path,
    *,
    run_root: Path,
    candidate: HeldoutACExecutionCandidate,
    row: Any,
    authenticated: HeldoutACAuthenticatedPersistedRow,
    run_id: str,
    authenticated_row_path: str,
    authenticated_row_bytes: bytes,
    authenticated_row_content_hash: str,
    actual_run_cost_nanos: int,
    accrued_cost_nanos_before: int,
) -> dict[str, Any]:
    return _append_journal(
        journal_path,
        "RunTerminalCostSettled",
        heldout_ac_terminal_cost_settled_payload(
            candidate=candidate,
            row=row,
            authenticated=authenticated,
            run_id=run_id,
            authenticated_row_path=authenticated_row_path,
            authenticated_row_bytes=authenticated_row_bytes,
            authenticated_row_content_hash=authenticated_row_content_hash,
            actual_run_cost_nanos=actual_run_cost_nanos,
            accrued_cost_nanos_before=accrued_cost_nanos_before,
        ),
        run_root=run_root,
    )


def _durable_usage_from_result(result: RunResult) -> HeldoutACDurableUsage:
    usage_raw = result.usage.model_dump(mode="json")
    return HeldoutACDurableUsage(
        **{
            key: usage_raw[key]
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
    )


def _persist_cost_observation(
    *,
    candidate: HeldoutACExecutionCandidate,
    order: int,
    run_id: str,
    run_root: Path,
) -> tuple[HeldoutACDispatchedCostObservation, Path]:
    row = candidate.schedule[order - 1]
    result_relative = Path("artifacts") / "runs" / run_id / "result.json"
    result_bytes = _read_canonical_runtime_file(
        run_root / result_relative,
        run_root=run_root,
    )
    try:
        result = RunResult.model_validate_json(result_bytes)
    except ValidationError as exc:
        raise HeldoutACDispatcherError("held-out dispatched result is invalid") from exc
    usage = _durable_usage_from_result(result)
    cost = usage.token_derived_cost_nanos()
    if not (
        result.run_id == run_id
        and Decimal(str(result.usage.model_cost_usd)) == Decimal(cost) / Decimal(1_000_000_000)
    ):
        raise HeldoutACDispatcherError("held-out dispatched result cost differs")
    body = {
        "schema_version": COST_OBSERVATION_SCHEMA_VERSION,
        "run_id": run_id,
        "schedule_row_id": row.schedule_row_id,
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "price_nanos_per_token": _PRICES,
        "usage": usage.model_dump(mode="json"),
        "result_relative_path": result_relative.as_posix(),
        "result_file_sha256": sha256_bytes(result_bytes),
        "result_semantic_hash": sha256_json(result.model_dump(mode="json")),
        "token_derived_cost_nanos": cost,
    }
    observation = HeldoutACDispatchedCostObservation(
        **body,
        content_hash=sha256_json(body),
    )
    relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / candidate.execution_hash.removeprefix("sha256:")
        / f"{order:02d}-{run_id}-cost-observation.json"
    )
    encoded = (
        json.dumps(
            observation.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")
    _write_new(run_root / relative, encoded, run_root=run_root)
    return observation, relative


def _durable_evidence_from_cost_observation(
    observation: HeldoutACDispatchedCostObservation,
    *,
    run_root: Path,
    observation_relative_path: Path,
) -> HeldoutACConfoundedDurableEvidence:
    observation_bytes = _read_canonical_runtime_file(
        run_root / observation_relative_path,
        run_root=run_root,
    )
    if observation_bytes != (
        json.dumps(
            observation.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8"):
        raise HeldoutACDispatcherError("held-out cost observation bytes differ")
    body = {
        "schema_version": CONFOUND_EVIDENCE_SCHEMA_VERSION,
        "run_id": observation.run_id,
        "result_relative_path": observation.result_relative_path,
        "result_file_sha256": observation.result_file_sha256,
        "result_semantic_hash": observation.result_semantic_hash,
        "cost_observation_relative_path": observation_relative_path.as_posix(),
        "cost_observation_file_sha256": sha256_bytes(observation_bytes),
        "cost_observation_content_hash": observation.content_hash,
        "qualification_relative_path": None,
        "qualification_file_sha256": None,
        "qualification_hash": None,
        "usage_relative_path": None,
        "usage_file_sha256": None,
        "usage_evidence_hash": None,
        "receipt_relative_path": None,
        "receipt_file_sha256": None,
        "receipt_content_hash": None,
        "evaluator_failure_code": None,
        "evaluator_failure_event_relative_path": None,
        "evaluator_failure_event_file_sha256": None,
        "evaluator_failure_event_hash": None,
        "evaluator_failure_event": None,
        "token_derived_cost_nanos": observation.token_derived_cost_nanos,
    }
    return HeldoutACConfoundedDurableEvidence(**body, content_hash=sha256_json(body))


def _usage_evidence_relative_path(
    candidate: HeldoutACExecutionCandidate,
    *,
    order: int,
    run_id: str,
) -> Path:
    return (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / candidate.execution_hash.removeprefix("sha256:")
        / f"{order:02d}-{run_id}-usage.json"
    )


def _extend_durable_evidence_from_files(
    cost_only: HeldoutACConfoundedDurableEvidence,
    *,
    run_root: Path,
    usage_relative_path: Path,
    candidate: HeldoutACExecutionCandidate,
    expected_row: Any,
) -> HeldoutACConfoundedDurableEvidence:
    qualification_relative = Path("qualifications") / f"{cost_only.run_id}.json"
    qualification_bytes = _read_canonical_runtime_file(
        run_root / qualification_relative,
        run_root=run_root,
    )
    usage_bytes = _read_canonical_runtime_file(
        run_root / usage_relative_path,
        run_root=run_root,
    )
    result_bytes = _read_canonical_runtime_file(
        run_root / cost_only.result_relative_path,
        run_root=run_root,
    )
    try:
        qualification = json.loads(qualification_bytes)
        usage = HeldoutACPersistedUsageEvidence.model_validate_json(usage_bytes)
        result = RunResult.model_validate_json(result_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise HeldoutACDispatcherError("held-out durable evidence extension is invalid") from exc
    qualification_hash = (
        qualification.get("qualification_hash") if isinstance(qualification, dict) else None
    )
    source_evidence_hash = (
        qualification.get("source_evidence_hash") if isinstance(qualification, dict) else None
    )
    if not (
        isinstance(qualification_hash, str)
        and isinstance(source_evidence_hash, str)
        and result.run_id == cost_only.run_id == usage.run_id
        and sha256_bytes(result_bytes) == cost_only.result_file_sha256
        and sha256_json(result.model_dump(mode="json")) == cost_only.result_semantic_hash
        and usage.qualification_hash == qualification_hash
        and usage.source_evidence_hash == source_evidence_hash
        and usage.persisted_result_file_hash == cost_only.result_file_sha256
        and usage.token_derived_cost_nanos == cost_only.token_derived_cost_nanos
    ):
        raise HeldoutACDispatcherError("held-out durable evidence extension differs")

    receipt_relative: Path | None = None
    receipt_file_sha256: str | None = None
    receipt_content_hash: str | None = None
    if result.evaluation_status == "completed":
        selected_receipt = Path("artifacts") / "runs" / cost_only.run_id / "evaluation-receipt.json"
        try:
            receipt_bytes = _read_canonical_runtime_file(
                run_root / selected_receipt,
                run_root=run_root,
            )
            receipt = EvaluatorV2EvaluationReceipt.model_validate_json(receipt_bytes)
        except (HeldoutACDispatcherError, ValidationError) as exc:
            raise HeldoutACDispatcherError("held-out completed durable receipt is invalid") from exc
        receipt_file_sha256 = sha256_bytes(receipt_bytes)
        if not (
            usage.evaluator_v2_receipt_file_hash == receipt_file_sha256
            and receipt.run_id == cost_only.run_id
            and receipt.result_file_hash == cost_only.result_file_sha256
            and receipt.suite_hash == candidate.suite_content_hash
            and result.evaluator_contract is not None
            and receipt.evaluator_contract_hash == result.evaluator_contract.contract_hash
            and receipt.evaluator_source_hash
            == candidate.source_qualification.evaluator_source_hash
            and receipt.source_qualification_hash
            == candidate.source_qualification.source_qualification_hash
            and qualification.get("evaluator_v2_receipt_hash") == receipt.content_hash
            and qualification.get("evaluator_v2_receipt_file_hash") == receipt_file_sha256
            and qualification.get("evaluator_v2_source_hash") == receipt.evaluator_source_hash
            and qualification.get("evaluator_v2_source_qualification_hash")
            == receipt.source_qualification_hash
        ):
            raise HeldoutACDispatcherError("held-out completed durable receipt binding differs")
        receipt_relative = selected_receipt
        receipt_content_hash = receipt.content_hash

    try:
        validate_heldout_ac_persisted_usage_cross_binding(
            result=result,
            usage_evidence=usage,
            expected_run_id=cost_only.run_id,
            expected_schedule_row_id=expected_row.schedule_row_id,
            expected_pricing_binding_hash=candidate.pricing_binding_hash,
            expected_qualification_hash=qualification_hash,
            expected_source_evidence_hash=source_evidence_hash,
            expected_result_file_hash=cost_only.result_file_sha256,
            expected_result_semantic_hash=cost_only.result_semantic_hash,
            expected_receipt_file_hash=receipt_file_sha256,
        )
    except ContractError as exc:
        raise HeldoutACDispatcherError(
            "held-out durable usage/result cross-binding differs"
        ) from exc

    body = {
        **cost_only.model_dump(mode="json", exclude={"content_hash"}),
        "qualification_relative_path": qualification_relative.as_posix(),
        "qualification_file_sha256": sha256_bytes(qualification_bytes),
        "qualification_hash": qualification_hash,
        "usage_relative_path": usage_relative_path.as_posix(),
        "usage_file_sha256": sha256_bytes(usage_bytes),
        "usage_evidence_hash": usage.content_hash,
        "receipt_relative_path": receipt_relative.as_posix() if receipt_relative else None,
        "receipt_file_sha256": receipt_file_sha256,
        "receipt_content_hash": receipt_content_hash,
    }
    return HeldoutACConfoundedDurableEvidence(**body, content_hash=sha256_json(body))


def _persist_usage_evidence(
    *,
    candidate: HeldoutACExecutionCandidate,
    order: int,
    run_id: str,
    run_root: Path,
    repository: Path,
    task_dir: Path,
    authority: Any,
) -> Path:
    from patchloop.evals.qualification import qualify_run

    row = candidate.schedule[order - 1]
    artifacts = ArtifactStore(run_root / "artifacts")
    result_file = artifacts.root / "runs" / run_id / "result.json"
    result_bytes = result_file.read_bytes()
    result = RunResult.model_validate_json(result_bytes)
    qualification = qualify_run(
        run_id,
        task_dir=task_dir,
        dataset_manifest_path=repository / _DATASET_PATH,
        root=run_root,
        evaluator_v2_authority=authority.qualification_authority,
    )
    qualification_hash = qualification.get("qualification_hash")
    source_evidence_hash = qualification.get("source_evidence_hash")
    if not isinstance(qualification_hash, str) or not isinstance(source_evidence_hash, str):
        raise HeldoutACDispatcherError("held-out trace qualification has no durable identities")
    durable_usage = _durable_usage_from_result(result)
    receipt_file = artifacts.root / "runs" / run_id / "evaluation-receipt.json"
    receipt_file_hash = (
        sha256_bytes(receipt_file.read_bytes()) if result.evaluation_status == "completed" else None
    )
    usage_body = {
        "schema_version": "heldout-ac-durable-usage-evidence-v1",
        "run_id": run_id,
        "schedule_row_id": row.schedule_row_id,
        "pricing_binding_hash": candidate.pricing_binding_hash,
        "price_nanos_per_token": _PRICES,
        "usage": durable_usage.model_dump(mode="json"),
        "token_derived_cost_nanos": durable_usage.token_derived_cost_nanos(),
        "qualification_hash": qualification_hash,
        "source_evidence_hash": source_evidence_hash,
        "persisted_result_file_hash": sha256_bytes(result_bytes),
        "evaluator_v2_receipt_file_hash": receipt_file_hash,
    }
    usage = HeldoutACPersistedUsageEvidence(
        **usage_body,
        content_hash=sha256_json(usage_body),
    )
    relative = _usage_evidence_relative_path(
        candidate,
        order=order,
        run_id=run_id,
    )
    usage_path = run_root / relative
    usage_bytes = json.dumps(
        usage.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")
    _write_new(usage_path, usage_bytes, run_root=run_root)
    return relative


def _authenticate_persisted_evidence(
    *,
    candidate: HeldoutACExecutionCandidate,
    order: int,
    run_root: Path,
    repository: Path,
    task_dir: Path,
    authority: Any,
    usage_evidence_relative_path: Path,
) -> HeldoutACAuthenticatedPersistedEvidence | HeldoutACEvaluatorConfoundEvidence:
    return authenticate_heldout_ac_persisted_evidence(
        suite=load_heldout_ac_suite(_SUITE_PATH, repository=repository),
        execution_hash=candidate.execution_hash,
        expected_pricing_binding_hash=candidate.pricing_binding_hash,
        order=order,
        task_evaluator_binding=authority.task_binding,
        run_root=run_root,
        task_dir=task_dir,
        dataset_manifest_path=repository / _DATASET_PATH,
        evaluator_authority=authority.qualification_authority,
        usage_evidence_relative_path=usage_evidence_relative_path.as_posix(),
    )


def _read_canonical_runtime_file(path: Path, *, run_root: Path) -> bytes:
    try:
        canonical = canonical_heldout_ac_runtime_path(
            path,
            expected_run_root=run_root,
        )
    except ContractError as exc:
        raise HeldoutACDispatcherError("held-out durable evidence path is not canonical") from exc
    try:
        resolved = canonical.resolve(strict=True)
        raw = canonical.read_bytes()
    except OSError as exc:
        raise HeldoutACDispatcherError("held-out durable evidence file is unavailable") from exc
    if resolved != canonical or not resolved.is_relative_to(run_root) or not canonical.is_file():
        raise HeldoutACDispatcherError("held-out durable evidence path is not canonical")
    return raw


def _evaluator_failure_event_relative_path(
    evidence: HeldoutACEvaluatorConfoundEvidence,
) -> Path:
    return (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / evidence.execution_hash.removeprefix("sha256:")
        / f"{evidence.order:02d}-{evidence.run_id}-evaluator-failure.json"
    )


def _evaluator_failure_event_projection(
    evidence: HeldoutACEvaluatorConfoundEvidence,
    *,
    run_root: Path,
) -> HeldoutACEvaluatorFailureEventProjection:
    state_path = canonical_heldout_ac_runtime_path(
        run_root / "state.sqlite3",
        expected_run_root=run_root,
    )
    if not state_path.is_file():
        raise HeldoutACDispatcherError("held-out evaluator failure state is unavailable")
    failure_events = [
        event
        for event in StateStore(state_path).list_events(evidence.run_id)
        if event.type == EventType.RUN_FAILED
    ]
    if len(failure_events) != 1:
        raise HeldoutACDispatcherError("held-out evaluator failure event is not unique")
    event = failure_events[0]
    error_code = event.payload.get("error_code")
    if not (event.actor == "runner" and error_code == evidence.evaluator_failure_code):
        raise HeldoutACDispatcherError("held-out evaluator failure event differs")
    body = {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "sequence": event.sequence,
        "type": event.type.value,
        "timestamp": event.model_dump(mode="json")["timestamp"],
        "actor": event.actor,
        "error_code": error_code,
    }
    projection_hash = sha256_json(body)
    if projection_hash != evidence.evaluator_failure_event_hash:
        raise HeldoutACDispatcherError("held-out evaluator failure event hash differs")
    return HeldoutACEvaluatorFailureEventProjection(
        event_id=event.event_id,
        run_id=event.run_id,
        sequence=event.sequence,
        type="RunFailed",
        timestamp=body["timestamp"],
        actor="runner",
        error_code=evidence.evaluator_failure_code,
        content_hash=projection_hash,
    )


def _durable_evidence_from_authenticated(
    evidence: HeldoutACAuthenticatedPersistedEvidence | HeldoutACEvaluatorConfoundEvidence,
    *,
    run_root: Path,
    usage_relative_path: Path,
    cost_observation: HeldoutACDispatchedCostObservation,
    cost_observation_relative_path: Path,
) -> HeldoutACConfoundedDurableEvidence:
    authenticated = (
        evidence.row if isinstance(evidence, HeldoutACAuthenticatedPersistedEvidence) else evidence
    )
    run_id = authenticated.run_id
    result_relative = Path("artifacts") / "runs" / run_id / "result.json"
    qualification_relative = Path("qualifications") / f"{run_id}.json"
    result_bytes = _read_canonical_runtime_file(run_root / result_relative, run_root=run_root)
    qualification_bytes = _read_canonical_runtime_file(
        run_root / qualification_relative, run_root=run_root
    )
    usage_bytes = _read_canonical_runtime_file(run_root / usage_relative_path, run_root=run_root)
    if not (
        cost_observation.run_id == run_id
        and cost_observation.result_file_sha256 == authenticated.persisted_result_file_hash
        and cost_observation.result_semantic_hash == authenticated.persisted_result_semantic_hash
        and cost_observation.token_derived_cost_nanos
        == authenticated.usage_evidence.token_derived_cost_nanos
        and sha256_bytes(result_bytes) == authenticated.persisted_result_file_hash
        and sha256_bytes(qualification_bytes) == authenticated.qualification_file_hash
        and sha256_bytes(usage_bytes) == authenticated.usage_evidence_file_hash
        and RunResult.model_validate_json(result_bytes) == authenticated.result
        and HeldoutACPersistedUsageEvidence.model_validate_json(usage_bytes)
        == authenticated.usage_evidence
    ):
        raise HeldoutACDispatcherError("held-out authenticated durable evidence bytes differ")

    receipt_relative: Path | None = None
    receipt_file_sha256: str | None = None
    receipt_content_hash: str | None = None
    if isinstance(evidence, HeldoutACAuthenticatedPersistedEvidence):
        row = evidence.row
        if row.evaluator_v2_receipt_file_hash is not None:
            receipt_relative = Path("artifacts") / "runs" / run_id / "evaluation-receipt.json"
            receipt_bytes = _read_canonical_runtime_file(
                run_root / receipt_relative, run_root=run_root
            )
            if sha256_bytes(receipt_bytes) != row.evaluator_v2_receipt_file_hash:
                raise HeldoutACDispatcherError("held-out evaluator receipt bytes differ")
            receipt_file_sha256 = row.evaluator_v2_receipt_file_hash
            receipt_content_hash = row.evaluator_v2_receipt_hash

    failure_event: HeldoutACEvaluatorFailureEventProjection | None = None
    failure_code: EvaluatorFailureCode | None = None
    failure_event_relative_path: Path | None = None
    failure_event_file_sha256: str | None = None
    failure_event_hash: str | None = None
    if isinstance(evidence, HeldoutACEvaluatorConfoundEvidence):
        failure_event = _evaluator_failure_event_projection(evidence, run_root=run_root)
        failure_code = evidence.evaluator_failure_code
        failure_event_hash = evidence.evaluator_failure_event_hash
        failure_event_relative_path = _evaluator_failure_event_relative_path(evidence)
        failure_event_bytes = (failure_event.model_dump_json(indent=2) + "\n").encode("utf-8")
        _write_new(
            run_root / failure_event_relative_path,
            failure_event_bytes,
            run_root=run_root,
        )
        failure_event_file_sha256 = sha256_bytes(failure_event_bytes)

    cost_only = _durable_evidence_from_cost_observation(
        cost_observation,
        run_root=run_root,
        observation_relative_path=cost_observation_relative_path,
    )
    body = {
        **cost_only.model_dump(mode="json", exclude={"content_hash"}),
        "qualification_relative_path": qualification_relative.as_posix(),
        "qualification_file_sha256": authenticated.qualification_file_hash,
        "qualification_hash": authenticated.qualification_hash,
        "usage_relative_path": usage_relative_path.as_posix(),
        "usage_file_sha256": authenticated.usage_evidence_file_hash,
        "usage_evidence_hash": authenticated.usage_evidence_hash,
        "receipt_relative_path": receipt_relative.as_posix() if receipt_relative else None,
        "receipt_file_sha256": receipt_file_sha256,
        "receipt_content_hash": receipt_content_hash,
        "evaluator_failure_code": failure_code,
        "evaluator_failure_event_relative_path": (
            failure_event_relative_path.as_posix()
            if failure_event_relative_path is not None
            else None
        ),
        "evaluator_failure_event_file_sha256": failure_event_file_sha256,
        "evaluator_failure_event_hash": failure_event_hash,
        "evaluator_failure_event": (
            failure_event.model_dump(mode="json") if failure_event is not None else None
        ),
    }
    return HeldoutACConfoundedDurableEvidence(**body, content_hash=sha256_json(body))


def _verify_confound_durable_evidence(
    durable: HeldoutACConfoundedDurableEvidence,
    *,
    run_root: Path,
    candidate: HeldoutACExecutionCandidate,
    expected_row: Any,
) -> None:
    evidence_root = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / candidate.execution_hash.removeprefix("sha256:")
    )
    expected_result_relative = (
        Path("artifacts") / "runs" / durable.run_id / "result.json"
    ).as_posix()
    expected_observation_relative = (
        evidence_root / f"{expected_row.order:02d}-{durable.run_id}-cost-observation.json"
    ).as_posix()
    expected_qualification_relative = (Path("qualifications") / f"{durable.run_id}.json").as_posix()
    expected_usage_relative = (
        evidence_root / f"{expected_row.order:02d}-{durable.run_id}-usage.json"
    ).as_posix()
    expected_receipt_relative = (
        Path("artifacts") / "runs" / durable.run_id / "evaluation-receipt.json"
    ).as_posix()
    expected_failure_relative = (
        evidence_root / f"{expected_row.order:02d}-{durable.run_id}-evaluator-failure.json"
    ).as_posix()
    if not (
        durable.result_relative_path == expected_result_relative
        and durable.cost_observation_relative_path == expected_observation_relative
        and (
            durable.qualification_relative_path is None
            or durable.qualification_relative_path == expected_qualification_relative
        )
        and (
            durable.usage_relative_path is None
            or durable.usage_relative_path == expected_usage_relative
        )
        and (
            durable.receipt_relative_path is None
            or durable.receipt_relative_path == expected_receipt_relative
        )
        and (
            durable.evaluator_failure_event_relative_path is None
            or durable.evaluator_failure_event_relative_path == expected_failure_relative
        )
    ):
        raise HeldoutACDispatcherError("held-out confounded durable evidence path differs")
    result_bytes = _read_canonical_runtime_file(
        run_root / durable.result_relative_path, run_root=run_root
    )
    observation_bytes = _read_canonical_runtime_file(
        run_root / durable.cost_observation_relative_path,
        run_root=run_root,
    )
    try:
        result = RunResult.model_validate_json(result_bytes)
        observation = HeldoutACDispatchedCostObservation.model_validate_json(observation_bytes)
    except ValidationError as exc:
        raise HeldoutACDispatcherError("held-out confounded durable evidence is invalid") from exc
    expected_usage = _durable_usage_from_result(result)
    expected_cost = expected_usage.token_derived_cost_nanos()
    if not (
        sha256_bytes(result_bytes) == durable.result_file_sha256
        and sha256_json(result.model_dump(mode="json")) == durable.result_semantic_hash
        and result.run_id == durable.run_id
        and sha256_bytes(observation_bytes) == durable.cost_observation_file_sha256
        and observation.content_hash == durable.cost_observation_content_hash
        and observation.result_file_sha256 == durable.result_file_sha256
        and observation.result_semantic_hash == durable.result_semantic_hash
        and observation.result_relative_path == durable.result_relative_path
        and observation.run_id == durable.run_id
        and observation.schedule_row_id == expected_row.schedule_row_id
        and observation.pricing_binding_hash == candidate.pricing_binding_hash
        and observation.usage == expected_usage
        and observation.token_derived_cost_nanos == expected_cost
        and Decimal(str(result.usage.model_cost_usd))
        == Decimal(expected_cost) / Decimal(1_000_000_000)
        and observation.token_derived_cost_nanos == durable.token_derived_cost_nanos
    ):
        raise HeldoutACDispatcherError("held-out confounded durable evidence replay differs")
    if durable.evaluator_failure_event is not None:
        assert durable.evaluator_failure_event_relative_path is not None
        assert durable.evaluator_failure_event_file_sha256 is not None
        assert durable.evaluator_failure_code is not None
        assert durable.evaluator_failure_event_hash is not None
        failure_event_bytes = _read_canonical_runtime_file(
            run_root / durable.evaluator_failure_event_relative_path,
            run_root=run_root,
        )
        expected_event = durable.evaluator_failure_event
        try:
            observed_event = HeldoutACEvaluatorFailureEventProjection.model_validate_json(
                failure_event_bytes
            )
        except ValidationError as exc:
            raise HeldoutACDispatcherError(
                "held-out confounded evaluator failure event is invalid"
            ) from exc
        canonical_event_bytes = (observed_event.model_dump_json(indent=2) + "\n").encode("utf-8")
        if not (
            failure_event_bytes == canonical_event_bytes
            and sha256_bytes(failure_event_bytes) == durable.evaluator_failure_event_file_sha256
            and observed_event == expected_event
            and observed_event.run_id == durable.run_id
            and observed_event.type == "RunFailed"
            and observed_event.actor == "runner"
            and observed_event.error_code == durable.evaluator_failure_code
            and observed_event.content_hash == durable.evaluator_failure_event_hash
        ):
            raise HeldoutACDispatcherError(
                "held-out confounded evaluator failure event replay differs"
            )
    if durable.qualification_relative_path is not None:
        assert durable.qualification_file_sha256 is not None
        assert durable.qualification_hash is not None
        qualification_bytes = _read_canonical_runtime_file(
            run_root / durable.qualification_relative_path,
            run_root=run_root,
        )
        try:
            qualification = json.loads(qualification_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HeldoutACDispatcherError("held-out confounded qualification is invalid") from exc
        if not (
            sha256_bytes(qualification_bytes) == durable.qualification_file_sha256
            and isinstance(qualification, dict)
            and qualification.get("qualification_hash") == durable.qualification_hash
            and isinstance(qualification.get("source_evidence_hash"), str)
        ):
            raise HeldoutACDispatcherError("held-out confounded qualification replay differs")
    if durable.usage_relative_path is not None:
        assert durable.usage_file_sha256 is not None
        assert durable.usage_evidence_hash is not None
        usage_bytes = _read_canonical_runtime_file(
            run_root / durable.usage_relative_path,
            run_root=run_root,
        )
        try:
            usage = HeldoutACPersistedUsageEvidence.model_validate_json(usage_bytes)
        except ValidationError as exc:
            raise HeldoutACDispatcherError("held-out confounded usage is invalid") from exc
        try:
            validate_heldout_ac_persisted_usage_cross_binding(
                result=result,
                usage_evidence=usage,
                expected_run_id=durable.run_id,
                expected_schedule_row_id=expected_row.schedule_row_id,
                expected_pricing_binding_hash=candidate.pricing_binding_hash,
                expected_qualification_hash=durable.qualification_hash,
                expected_source_evidence_hash=str(qualification["source_evidence_hash"]),
                expected_result_file_hash=durable.result_file_sha256,
                expected_result_semantic_hash=durable.result_semantic_hash,
                expected_receipt_file_hash=durable.receipt_file_sha256,
            )
        except ContractError as exc:
            raise HeldoutACDispatcherError(
                "held-out confounded usage/result cross-binding differs"
            ) from exc
        if not (
            sha256_bytes(usage_bytes) == durable.usage_file_sha256
            and usage.content_hash == durable.usage_evidence_hash
            and usage.run_id == durable.run_id
            and usage.schedule_row_id == expected_row.schedule_row_id
            and usage.pricing_binding_hash == candidate.pricing_binding_hash
            and usage.token_derived_cost_nanos == durable.token_derived_cost_nanos
        ):
            raise HeldoutACDispatcherError("held-out confounded usage replay differs")
    if durable.receipt_relative_path is not None:
        receipt_bytes = _read_canonical_runtime_file(
            run_root / durable.receipt_relative_path, run_root=run_root
        )
        try:
            receipt = EvaluatorV2EvaluationReceipt.model_validate_json(receipt_bytes)
        except ValidationError as exc:
            raise HeldoutACDispatcherError("held-out confounded receipt is invalid") from exc
        if not (
            sha256_bytes(receipt_bytes) == durable.receipt_file_sha256
            and receipt.content_hash == durable.receipt_content_hash
            and receipt.run_id == durable.run_id
            and receipt.result_file_hash == durable.result_file_sha256
            and receipt.suite_hash == candidate.suite_content_hash
            and result.evaluator_contract is not None
            and receipt.evaluator_contract_hash == result.evaluator_contract.contract_hash
            and receipt.evaluator_source_hash
            == candidate.source_qualification.evaluator_source_hash
            and receipt.source_qualification_hash
            == candidate.source_qualification.source_qualification_hash
            and qualification.get("evaluator_v2_receipt_hash") == receipt.content_hash
            and qualification.get("evaluator_v2_receipt_file_hash") == durable.receipt_file_sha256
            and qualification.get("evaluator_v2_source_hash") == receipt.evaluator_source_hash
            and qualification.get("evaluator_v2_source_qualification_hash")
            == receipt.source_qualification_hash
        ):
            raise HeldoutACDispatcherError("held-out confounded receipt replay differs")


def _verify_settled_source_files(
    authenticated: HeldoutACAuthenticatedPersistedRow,
    *,
    run_root: Path,
    candidate: HeldoutACExecutionCandidate,
    expected_row: Any,
    authenticated_evidence: HeldoutACAuthenticatedPersistedEvidence | None,
) -> None:
    usage_relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / authenticated.execution_hash.removeprefix("sha256:")
        / f"{authenticated.order:02d}-{authenticated.run_id}-usage.json"
    )
    result_bytes = _read_canonical_runtime_file(
        run_root / "artifacts" / "runs" / authenticated.run_id / "result.json",
        run_root=run_root,
    )
    qualification_bytes = _read_canonical_runtime_file(
        run_root / "qualifications" / f"{authenticated.run_id}.json",
        run_root=run_root,
    )
    usage_bytes = _read_canonical_runtime_file(run_root / usage_relative, run_root=run_root)
    try:
        result = RunResult.model_validate_json(result_bytes)
        qualification = json.loads(qualification_bytes)
        usage = HeldoutACPersistedUsageEvidence.model_validate_json(usage_bytes)
    except (ValidationError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACDispatcherError("held-out settled source evidence is invalid") from exc
    source_evidence_hash = (
        qualification.get("source_evidence_hash") if isinstance(qualification, dict) else None
    )
    try:
        validate_heldout_ac_persisted_usage_cross_binding(
            result=result,
            usage_evidence=usage,
            expected_run_id=authenticated.run_id,
            expected_schedule_row_id=expected_row.schedule_row_id,
            expected_pricing_binding_hash=candidate.pricing_binding_hash,
            expected_qualification_hash=authenticated.qualification_hash,
            expected_source_evidence_hash=authenticated.source_evidence_hash,
            expected_result_file_hash=authenticated.persisted_result_file_hash,
            expected_result_semantic_hash=authenticated.persisted_result_semantic_hash,
            expected_receipt_file_hash=authenticated.evaluator_v2_receipt_file_hash,
        )
    except ContractError as exc:
        raise HeldoutACDispatcherError(
            "held-out settled usage/result cross-binding differs"
        ) from exc
    if not (
        sha256_bytes(result_bytes) == authenticated.persisted_result_file_hash
        and sha256_json(result.model_dump(mode="json"))
        == authenticated.persisted_result_semantic_hash
        and result == authenticated.result
        and sha256_bytes(qualification_bytes) == authenticated.qualification_file_hash
        and isinstance(qualification, dict)
        and qualification.get("qualification_hash") == authenticated.qualification_hash
        and source_evidence_hash == authenticated.source_evidence_hash
        and sha256_bytes(usage_bytes) == authenticated.usage_evidence_file_hash
        and usage == authenticated.usage_evidence
        and authenticated.schedule_row_id == expected_row.schedule_row_id
        and authenticated.execution_hash == candidate.execution_hash
        and result.evaluator_contract is not None
        and result.evaluator_contract.task_id == expected_row.task_id
        and result.evaluator_contract.evaluator_source_hash
        == candidate.source_qualification.evaluator_source_hash
    ):
        raise HeldoutACDispatcherError("held-out settled source evidence replay differs")
    if authenticated.evaluator_v2_receipt_file_hash is not None:
        receipt_bytes = _read_canonical_runtime_file(
            run_root / "artifacts" / "runs" / authenticated.run_id / "evaluation-receipt.json",
            run_root=run_root,
        )
        try:
            receipt = EvaluatorV2EvaluationReceipt.model_validate_json(receipt_bytes)
        except ValidationError as exc:
            raise HeldoutACDispatcherError("held-out settled receipt is invalid") from exc
        if not (
            sha256_bytes(receipt_bytes) == authenticated.evaluator_v2_receipt_file_hash
            and receipt.content_hash == authenticated.evaluator_v2_receipt_hash
            and receipt.run_id == authenticated.run_id
            and receipt.result_file_hash == authenticated.persisted_result_file_hash
            and receipt.suite_hash == candidate.suite_content_hash
            and result.evaluator_contract is not None
            and receipt.evaluator_contract_hash == result.evaluator_contract.contract_hash
            and receipt.evaluator_source_hash
            == candidate.source_qualification.evaluator_source_hash
            and receipt.source_qualification_hash
            == candidate.source_qualification.source_qualification_hash
            and usage.evaluator_v2_receipt_file_hash == authenticated.evaluator_v2_receipt_file_hash
            and (
                authenticated_evidence is None
                or (
                    authenticated_evidence.qualification.evaluator_v2_receipt_hash
                    == receipt.content_hash
                    and authenticated_evidence.qualification.evaluator_v2_receipt_file_hash
                    == authenticated.evaluator_v2_receipt_file_hash
                    and authenticated_evidence.qualification.evaluator_v2_source_hash
                    == receipt.evaluator_source_hash
                    and authenticated_evidence.qualification.evaluator_v2_source_qualification_hash
                    == receipt.source_qualification_hash
                )
            )
        ):
            raise HeldoutACDispatcherError("held-out settled receipt replay differs")


def _verify_settled_agent_terminal_sidecar(
    settled: HeldoutACSettledCampaignRowV2,
    *,
    run_root: Path,
) -> None:
    terminal_event = settled.authenticated_evidence.terminal_event
    if terminal_event is None:
        return
    expected_relative = (
        Path("experiments")
        / "heldout-ac"
        / "rows"
        / settled.authenticated_row.execution_hash.removeprefix("sha256:")
        / (
            f"{settled.authenticated_row.order:02d}-"
            f"{settled.authenticated_row.run_id}-agent-terminal.json"
        )
    )
    if settled.agent_terminal_event_relative_path != expected_relative.as_posix():
        raise HeldoutACDispatcherError("held-out agent terminal sidecar path differs")
    terminal_bytes = _read_canonical_runtime_file(
        run_root / expected_relative,
        run_root=run_root,
    )
    try:
        observed = HeldoutACAgentTerminalEventProjection.model_validate_json(terminal_bytes)
    except ValidationError as exc:
        raise HeldoutACDispatcherError("held-out agent terminal sidecar is invalid") from exc
    canonical = (observed.model_dump_json(indent=2) + "\n").encode("utf-8")
    if not (
        terminal_bytes == canonical
        and sha256_bytes(terminal_bytes) == settled.agent_terminal_event_file_sha256
        and observed == terminal_event
        and observed.content_hash == settled.agent_terminal_event_content_hash
    ):
        raise HeldoutACDispatcherError("held-out agent terminal sidecar replay differs")


def _terminal_type(run_root: Path, row: HeldoutACAuthenticatedPersistedRow) -> AgentTerminalType:
    state = StateStore(run_root / "state.sqlite3")
    reason_codes = [
        event.payload.get("reason_code")
        for event in state.list_events(row.run_id)
        if event.type == EventType.MODEL_GENERATION_BLOCKED
    ]
    mapping: dict[Any, AgentTerminalType] = {
        "exact_request_budget_exceeded": "token-budget-exhaustion",
        "model_call_budget_exhausted": "model-call-limit",
        "tool_call_budget_exhausted": "tool-call-limit",
        "wall_clock_budget_exhausted": "wall-clock-timeout",
    }
    for reason in reversed(reason_codes):
        if reason in mapping:
            return mapping[reason]
    return "submission-failure"


def _settled_row(
    row: HeldoutACAuthenticatedPersistedRow | HeldoutACAuthenticatedPersistedEvidence,
    *,
    run_root: Path,
) -> HeldoutACSettledCampaignRow | HeldoutACSettledCampaignRowV2:
    if isinstance(row, HeldoutACAuthenticatedPersistedEvidence):
        terminal_relative: Path | None = None
        terminal_file_sha256: str | None = None
        terminal_content_hash: str | None = None
        if row.terminal_event is not None:
            terminal_relative = (
                Path("experiments")
                / "heldout-ac"
                / "rows"
                / row.row.execution_hash.removeprefix("sha256:")
                / f"{row.row.order:02d}-{row.row.run_id}-agent-terminal.json"
            )
            terminal_bytes = (row.terminal_event.model_dump_json(indent=2) + "\n").encode("utf-8")
            _write_new(run_root / terminal_relative, terminal_bytes, run_root=run_root)
            terminal_file_sha256 = sha256_bytes(terminal_bytes)
            terminal_content_hash = row.terminal_event.content_hash
        body = {
            "schema_version": SETTLED_ROW_SCHEMA_VERSION_V2,
            "authenticated_evidence": row.model_dump(mode="json"),
            "agent_terminal_event_relative_path": (
                terminal_relative.as_posix() if terminal_relative is not None else None
            ),
            "agent_terminal_event_file_sha256": terminal_file_sha256,
            "agent_terminal_event_content_hash": terminal_content_hash,
        }
        return HeldoutACSettledCampaignRowV2(
            schema_version=SETTLED_ROW_SCHEMA_VERSION_V2,
            authenticated_evidence=row,
            agent_terminal_event_relative_path=body["agent_terminal_event_relative_path"],
            agent_terminal_event_file_sha256=terminal_file_sha256,
            agent_terminal_event_content_hash=terminal_content_hash,
            content_hash=sha256_json(body),
        )
    terminal_type = (
        None if row.result.evaluation_status == "completed" else _terminal_type(run_root, row)
    )
    body = {
        "schema_version": SETTLED_ROW_SCHEMA_VERSION,
        "authenticated_row": row.model_dump(mode="json"),
        "terminal_type": terminal_type,
    }
    return HeldoutACSettledCampaignRow(**body, content_hash=sha256_json(body))


def _validate_settlement_limits(
    row: HeldoutACAuthenticatedPersistedRow,
    *,
    accrued_before: int,
    candidate: HeldoutACExecutionCandidate | None = None,
) -> int:
    usage = row.usage_evidence.usage
    cost = row.usage_evidence.token_derived_cost_nanos
    if candidate is None:
        max_input_tokens, max_output_tokens, max_total_tokens = 4_000_000, 500_000, 4_500_000
        per_run_reserve_nanos = 5_250_000_000
        full_schedule_reserve_nanos = 252_000_000_000
    else:
        max_input_tokens, max_output_tokens, max_total_tokens = heldout_ac_candidate_token_limits(
            candidate
        )
        per_run_reserve_nanos = candidate.campaign_cost_control.per_run_reserve_nanos
        full_schedule_reserve_nanos = candidate.campaign_cost_control.full_schedule_reserve_nanos
    within_runtime = (
        usage.input_tokens <= max_input_tokens
        and usage.output_tokens <= max_output_tokens
        and usage.input_tokens + usage.output_tokens <= max_total_tokens
        and usage.model_calls <= 240
        and usage.tool_calls <= 400
        and cost <= per_run_reserve_nanos
    )
    if not within_runtime:
        raise HeldoutACDispatcherError(
            "held-out authenticated usage exceeds the frozen per-row boundary"
        )
    if accrued_before + cost > full_schedule_reserve_nanos:
        raise HeldoutACDispatcherError("held-out settled cost exceeds the full-schedule reserve")
    return cost


def _confound_reason_code(exc: Exception, phase: ConfoundPhase) -> ConfoundReasonCode:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        code = getattr(current, "code", None)
        if code in {
            "EVALUATOR_CONTROL_CONTRACT_COLLISION",
            "UNTRUSTED_PRIVATE_MARKER_HIT",
        }:
            return code
        current = current.__cause__ or current.__context__
    return {
        "row-dispatch": "ROW_DISPATCH_FAILED",
        "cost-observation": "COST_OBSERVATION_FAILED",
        "qualification": "QUALIFICATION_FAILED",
        "authentication": "DURABLE_EVIDENCE_AUTHENTICATION_FAILED",
        "settlement": "SETTLEMENT_FAILED",
    }[phase]


def _trigger_for_reason(
    reason_code: ConfoundReasonCode,
) -> MatrixConfound:
    if reason_code == "UNTRUSTED_PRIVATE_MARKER_HIT":
        return "private-marker-or-leakage-hit"
    if reason_code in {
        "EVALUATOR_CONTROL_CONTRACT_COLLISION",
        "DURABLE_EVIDENCE_AUTHENTICATION_FAILED",
        "QUALIFICATION_FAILED",
    }:
        return "qualification-or-completion-contract-mismatch"
    if reason_code == "SETTLEMENT_FAILED":
        return "missing-durable-usage-or-cost-settlement"
    if reason_code == "COST_OBSERVATION_FAILED":
        return "missing-durable-usage-or-cost-settlement"
    return "provider-sdk-docker-or-evaluator-infrastructure-error"


def _record_confound(
    *,
    candidate: HeldoutACExecutionCandidate,
    run_root: Path,
    journal_path: Path,
    row: Any,
    run_id: str,
    exc: Exception,
    phase: ConfoundPhase,
    run_started_event_written: bool,
    reason_code: ConfoundReasonCode | None = None,
    durable_evidence: HeldoutACConfoundedDurableEvidence | None = None,
) -> tuple[HeldoutACCampaignConfoundV2, list[HeldoutACNotStartedRow]]:
    reason = reason_code or _confound_reason_code(exc, phase)
    trigger = _trigger_for_reason(reason)
    confound_body = {
        "schema_version": CONFOUND_SCHEMA_VERSION_V2,
        "order": row.order,
        "schedule_row_id": row.schedule_row_id,
        "task_id": row.task_id,
        "run_id": run_id,
        "trigger": trigger,
        "phase": phase,
        "reason_code": reason,
        "exception_type": type(exc).__name__,
        "run_started_event_written": run_started_event_written,
        "durable_evidence": (
            durable_evidence.model_dump(mode="json") if durable_evidence is not None else None
        ),
        "secret_or_exception_message_persisted": False,
    }
    confound = HeldoutACCampaignConfoundV2(
        **confound_body,
        content_hash=sha256_json(confound_body),
    )
    _append_journal(
        journal_path,
        "RunConfounded",
        {
            **_row_identity(row),
            "run_id": run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "trigger": trigger,
            "phase": phase,
            "reason_code": reason,
            "run_started_event_written": run_started_event_written,
            "durable_evidence": (
                durable_evidence.model_dump(mode="json") if durable_evidence is not None else None
            ),
            "confound_content_hash": confound.content_hash,
            "exception_message_persisted": False,
        },
        run_root=run_root,
    )
    not_started: list[HeldoutACNotStartedRow] = []
    for remaining in candidate.schedule[row.order :]:
        not_started_row = HeldoutACNotStartedRow(
            schema_version=NOT_STARTED_SCHEMA_VERSION,
            order=remaining.order,
            schedule_row_id=remaining.schedule_row_id,
            task_id=remaining.task_id,
            role=remaining.role,
            condition=remaining.condition,
            repetition=remaining.repetition,
            reason="campaign-stopped-after-prespecified-confound",
            trigger=trigger,
        )
        not_started.append(not_started_row)
        _append_journal(
            journal_path,
            "RunNotStarted",
            {
                **_row_identity(remaining),
                "execution_hash": candidate.execution_hash,
                "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
                "reason": "campaign-stopped-after-prespecified-confound",
                "trigger": trigger,
            },
            run_root=run_root,
        )
    return confound, not_started


def _prepared_result(
    *,
    candidate: HeldoutACExecutionCandidate,
    plan_path: Path,
    plan_hash: str,
    journal_path: Path,
    settled: list[HeldoutACSettledCampaignRow | HeldoutACSettledCampaignRowV2],
    confound: HeldoutACCampaignConfound | HeldoutACCampaignConfoundV2 | None,
    not_started: list[HeldoutACNotStartedRow],
    persisted_official: tuple[
        HeldoutACAuthenticatedCompletionProjection,
        HeldoutACOfficialAnalysisEnvelope,
    ]
    | None = None,
) -> tuple[dict[str, Any], HeldoutACOutcomeProjection | None, HeldoutACAnalysis | None]:
    for index, settled_row in enumerate(settled, start=1):
        authenticated = settled_row.authenticated_row
        expected = candidate.schedule[index - 1]
        evaluator_contract = authenticated.result.evaluator_contract
        evaluator_completed = authenticated.result.evaluation_status == "completed"
        if not (
            authenticated.order == expected.order
            and authenticated.wave == expected.wave
            and authenticated.task_id == expected.task_id
            and authenticated.role == expected.role
            and authenticated.condition == expected.condition
            and authenticated.repetition == expected.repetition
            and authenticated.schedule_row_id == expected.schedule_row_id
            and authenticated.execution_hash == candidate.execution_hash
            and authenticated.usage_evidence.schedule_row_id == expected.schedule_row_id
            and authenticated.usage_evidence.pricing_binding_hash == candidate.pricing_binding_hash
            and evaluator_contract is not None
            and evaluator_contract.task_id == expected.task_id
            and evaluator_contract.evaluator_source_hash
            == candidate.source_qualification.evaluator_source_hash
            and (
                (
                    evaluator_completed
                    and authenticated.evaluator_v2_receipt_hash is not None
                    and authenticated.evaluator_v2_receipt_file_hash is not None
                    and settled_row.terminal_type is None
                )
                or (
                    not evaluator_completed
                    and authenticated.evaluator_v2_receipt_hash is None
                    and authenticated.evaluator_v2_receipt_file_hash is None
                    and settled_row.terminal_type is not None
                )
            )
        ):
            raise HeldoutACDispatcherError(
                f"authenticated held-out row differs from candidate at order {index}"
            )
    if confound is not None:
        expected_confound = candidate.schedule[confound.order - 1]
        if (
            confound.schedule_row_id != expected_confound.schedule_row_id
            or confound.task_id != expected_confound.task_id
        ):
            raise HeldoutACDispatcherError("held-out confound belongs to another schedule row")
    for item in not_started:
        expected_not_started = candidate.schedule[item.order - 1]
        if (
            item.schedule_row_id,
            item.task_id,
            item.role,
            item.condition,
            item.repetition,
        ) != (
            expected_not_started.schedule_row_id,
            expected_not_started.task_id,
            expected_not_started.role,
            expected_not_started.condition,
            expected_not_started.repetition,
        ):
            raise HeldoutACDispatcherError("held-out not-started row differs from the schedule")
    projection: HeldoutACOutcomeProjection | None = None
    analysis: HeldoutACAnalysis | None = None
    completion: HeldoutACAuthenticatedCompletionProjection | None = None
    official: HeldoutACOfficialAnalysisEnvelope | None = None
    if len(settled) == 48 and confound is None:
        if not all(isinstance(item, HeldoutACSettledCampaignRowV2) for item in settled):
            raise HeldoutACDispatcherError(
                "complete held-out matrix requires authenticated persisted-evidence v2 rows"
            )
        typed_rows = [
            item.authenticated_evidence
            for item in settled
            if isinstance(item, HeldoutACSettledCampaignRowV2)
        ]
        if persisted_official is None:
            completion = project_authenticated_heldout_ac_completion(
                suite=load_heldout_ac_suite(_SUITE_PATH),
                execution_hash=candidate.execution_hash,
                expected_pricing_binding_hash=candidate.pricing_binding_hash,
                evaluator_source_hash=candidate.source_qualification.evaluator_source_hash,
                evaluator_source_qualification_hash=(
                    candidate.source_qualification.source_qualification_hash
                ),
                rows=typed_rows,
                full_schedule_reserve_nanos=(
                    candidate.campaign_cost_control.full_schedule_reserve_nanos
                ),
                hard_cap_nanos=candidate.campaign_cost_control.hard_cap_nanos,
            )
            official = analyze_authenticated_heldout_ac_completion(completion)
            projection = completion.outcome_projection
            analysis = official.analysis
        else:
            completion, official = persisted_official
            validate_persisted_heldout_ac_completion_replay(
                suite=load_heldout_ac_suite(_SUITE_PATH),
                execution_hash=candidate.execution_hash,
                expected_pricing_binding_hash=candidate.pricing_binding_hash,
                evaluator_source_hash=candidate.source_qualification.evaluator_source_hash,
                evaluator_source_qualification_hash=(
                    candidate.source_qualification.source_qualification_hash
                ),
                rows=typed_rows,
                completion=completion,
                official_envelope=official,
                full_schedule_reserve_nanos=(
                    candidate.campaign_cost_control.full_schedule_reserve_nanos
                ),
                hard_cap_nanos=candidate.campaign_cost_control.hard_cap_nanos,
            )
            projection = completion.outcome_projection
            analysis = official.analysis
    elif persisted_official is not None:
        raise HeldoutACDispatcherError(
            "inconclusive held-out replay cannot carry official completion"
        )
    disposition = "complete-matrix" if analysis is not None else "inconclusive-matrix"
    is_v2 = bool(
        any(isinstance(item, HeldoutACSettledCampaignRowV2) for item in settled)
        or isinstance(confound, HeldoutACCampaignConfoundV2)
    )
    settled_cost = sum(
        row.authenticated_row.usage_evidence.token_derived_cost_nanos for row in settled
    )
    observed_unsettled_cost = (
        confound.durable_evidence.token_derived_cost_nanos
        if isinstance(confound, HeldoutACCampaignConfoundV2)
        and confound.durable_evidence is not None
        else 0
    )
    unsettled = int(confound is not None and confound.run_started_event_written)
    accounting_complete = bool(
        not unsettled
        or (
            isinstance(confound, HeldoutACCampaignConfoundV2)
            and confound.durable_evidence is not None
        )
    )
    body = {
        "schema_version": (
            PREPARED_RESULT_SCHEMA_VERSION_V2 if is_v2 else PREPARED_RESULT_SCHEMA_VERSION
        ),
        "evidence_status": "authenticated-persisted-campaign",
        "disposition": disposition,
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "execution_hash": candidate.execution_hash,
        "source_qualification_hash": candidate.source_qualification.source_qualification_hash,
        "evaluator_source_hash": candidate.source_qualification.evaluator_source_hash,
        "execution_plan_path": str(plan_path.resolve(strict=False)),
        "execution_plan_file_sha256": plan_hash,
        "journal_path": str(journal_path.resolve(strict=False)),
        "expected_runs": 48,
        "terminal_settled_runs": len(settled),
        "not_started_runs": len(not_started),
        "settled_model_cost_nanos": settled_cost,
        "unsettled_dispatched_runs": unsettled,
        "cost_accounting_complete": accounting_complete if is_v2 else unsettled == 0,
        "full_schedule_reserve_nanos": (
            candidate.campaign_cost_control.full_schedule_reserve_nanos
        ),
        "hard_cap_nanos": candidate.campaign_cost_control.hard_cap_nanos,
        "settled_rows": [row.model_dump(mode="json") for row in settled],
        "confound": confound.model_dump(mode="json") if confound is not None else None,
        "not_started_rows": [row.model_dump(mode="json") for row in not_started],
        "outcome_projection": projection.model_dump(mode="json")
        if projection is not None
        else None,
        "analysis": analysis.model_dump(mode="json") if analysis is not None else None,
        "analysis_ready": analysis is not None,
        "official_heldout_analysis": analysis is not None,
        "memory_benefit_claim_authorized": False,
        "broad_generalization_claim_authorized": False,
        "retry_replacement_or_resume_performed": False,
    }
    if is_v2:
        body.update(
            {
                "observed_unsettled_model_cost_nanos": observed_unsettled_cost,
                "observed_started_model_cost_nanos": settled_cost + observed_unsettled_cost,
                "authenticated_completion": (
                    completion.model_dump(mode="json") if completion is not None else None
                ),
                "official_analysis_envelope": (
                    official.model_dump(mode="json") if official is not None else None
                ),
            }
        )
    return {**body, "content_hash": sha256_json(body)}, projection, analysis


def _finalize_result(
    *,
    run_root: Path,
    candidate: HeldoutACExecutionCandidate,
    plan_path: Path,
    plan_hash: str,
    journal_path: Path,
    result_path: Path,
    settled: list[HeldoutACSettledCampaignRow | HeldoutACSettledCampaignRowV2],
    confound: HeldoutACCampaignConfound | HeldoutACCampaignConfoundV2 | None,
    not_started: list[HeldoutACNotStartedRow],
) -> HeldoutACCampaignResult | HeldoutACCampaignResultV2:
    prepared, projection, analysis = _prepared_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash=plan_hash,
        journal_path=journal_path,
        settled=settled,
        confound=confound,
        not_started=not_started,
    )
    prepared_path = result_path.with_name(f"{result_path.stem}.prepared.json")
    prepared_bytes = (
        json.dumps(prepared, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    _write_new(prepared_path, prepared_bytes, run_root=run_root)
    completed_payload = {
        "suite_id": candidate.suite_id,
        "execution_hash": candidate.execution_hash,
        "disposition": prepared["disposition"],
        "terminal_settled_runs": len(settled),
        "not_started_runs": len(not_started),
        "settled_model_cost_nanos": prepared["settled_model_cost_nanos"],
        "unsettled_dispatched_runs": prepared["unsettled_dispatched_runs"],
        "cost_accounting_complete": prepared["cost_accounting_complete"],
        "prepared_result_path": str(prepared_path.resolve(strict=False)),
        "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
        "prepared_result_content_hash": prepared["content_hash"],
    }
    if prepared["schema_version"] == PREPARED_RESULT_SCHEMA_VERSION_V2:
        completed_payload.update(
            {
                "observed_unsettled_model_cost_nanos": prepared[
                    "observed_unsettled_model_cost_nanos"
                ],
                "observed_started_model_cost_nanos": prepared["observed_started_model_cost_nanos"],
            }
        )
    completed = _append_journal(
        journal_path,
        "CampaignCompleted",
        completed_payload,
        run_root=run_root,
    )
    journal_hash = sha256_bytes(journal_path.read_bytes())
    body = {
        **{
            key: value
            for key, value in prepared.items()
            if key not in {"schema_version", "content_hash"}
        },
        "schema_version": (
            CAMPAIGN_RESULT_SCHEMA_VERSION_V2
            if prepared["schema_version"] == PREPARED_RESULT_SCHEMA_VERSION_V2
            else CAMPAIGN_RESULT_SCHEMA_VERSION
        ),
        "journal_file_sha256": journal_hash,
        "campaign_completed_event_hash": completed["event_hash"],
        "prepared_result_path": str(prepared_path.resolve(strict=False)),
        "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
        "prepared_result_content_hash": prepared["content_hash"],
    }
    result_payload = {**body, "content_hash": sha256_json(body)}
    result_model = (
        HeldoutACCampaignResultV2
        if body["schema_version"] == CAMPAIGN_RESULT_SCHEMA_VERSION_V2
        else HeldoutACCampaignResult
    )
    result = result_model.model_validate_json(json.dumps(result_payload, sort_keys=True))
    result_bytes = (result.model_dump_json(indent=2) + "\n").encode("utf-8")
    _write_new(result_path, result_bytes, run_root=run_root)
    return result


def validate_heldout_ac_campaign_result(
    *,
    execution_hash: str,
    root: str | Path | None = None,
    repository: str | Path | None = None,
) -> dict[str, Any]:
    """Replay the persisted plan, rows, journal, prepared result, and final result."""

    run_root = _root(root)
    repo = _repository(repository)
    plan, plan_bytes = _load_approved_plan(execution_hash, run_root)
    candidate = _candidate_from_mapping(plan["candidate"])
    if not heldout_ac_candidate_has_bound_source_qualification(candidate, repository=repo):
        raise HeldoutACDispatcherError(
            "held-out result candidate bound source qualification differs"
        )
    result_path = canonical_heldout_ac_runtime_path(
        str(plan["result_path"]),
        expected_run_root=run_root,
    )
    expected_result_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "heldout-ac" / f"{execution_hash[7:]}.json",
        expected_run_root=run_root,
    )
    try:
        result_bytes = result_path.read_bytes()
        result_payload = json.loads(result_bytes)
        result_model = (
            HeldoutACCampaignResultV2
            if isinstance(result_payload, dict)
            and result_payload.get("schema_version") == CAMPAIGN_RESULT_SCHEMA_VERSION_V2
            else HeldoutACCampaignResult
        )
        result = result_model.model_validate_json(result_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise HeldoutACDispatcherError("held-out campaign result is invalid") from exc
    if (
        result_path != expected_result_path
        or result_path.is_symlink()
        or result_bytes != (result.model_dump_json(indent=2) + "\n").encode("utf-8")
    ):
        raise HeldoutACDispatcherError("held-out campaign result bytes differ")
    plan_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "plans" / f"{execution_hash[7:]}.json",
        expected_run_root=run_root,
    )
    journal_path = canonical_heldout_ac_runtime_path(
        result.journal_path,
        expected_run_root=run_root,
    )
    expected_journal_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "journals" / f"{execution_hash[7:]}.jsonl",
        expected_run_root=run_root,
    )
    prepared_path = canonical_heldout_ac_runtime_path(
        result.prepared_result_path,
        expected_run_root=run_root,
    )
    expected_prepared_path = canonical_heldout_ac_runtime_path(
        result_path.with_name(f"{result_path.stem}.prepared.json"),
        expected_run_root=run_root,
    )
    try:
        prepared_bytes = prepared_path.read_bytes()
        prepared = json.loads(prepared_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HeldoutACDispatcherError("held-out prepared result is invalid") from exc
    if not isinstance(prepared, dict):
        raise HeldoutACDispatcherError("held-out prepared result is not an object")
    if not (
        candidate.execution_hash == execution_hash
        and plan.get("journal_path") == str(expected_journal_path)
        and plan.get("result_path") == str(expected_result_path)
        and journal_path == expected_journal_path
        and journal_path.is_symlink() is False
    ):
        raise HeldoutACDispatcherError("held-out historical plan paths or identity differ")
    prepared_body = {key: value for key, value in prepared.items() if key != "content_hash"}
    expected_prepared, _projection, _analysis = _prepared_result(
        candidate=candidate,
        plan_path=plan_path,
        plan_hash=sha256_bytes(plan_bytes),
        journal_path=journal_path,
        settled=list(result.settled_rows),
        confound=result.confound,
        not_started=list(result.not_started_rows),
        persisted_official=(
            (result.authenticated_completion, result.official_analysis_envelope)
            if isinstance(result, HeldoutACCampaignResultV2)
            and result.authenticated_completion is not None
            and result.official_analysis_envelope is not None
            else None
        ),
    )
    canonical_prepared = (
        json.dumps(prepared, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    if not (
        prepared_path == expected_prepared_path
        and prepared_path.is_symlink() is False
        and prepared_bytes == canonical_prepared
        and prepared.get("content_hash") == sha256_json(prepared_body)
        and _exact_typed_equal(prepared, expected_prepared)
        and result.prepared_result_file_sha256 == sha256_bytes(prepared_bytes)
        and result.prepared_result_content_hash == prepared["content_hash"]
    ):
        raise HeldoutACDispatcherError("held-out prepared result replay differs")

    events, journal_bytes = _load_journal_events(journal_path)
    expected_started = {
        "suite_id": candidate.suite_id,
        "suite_content_hash": candidate.suite_content_hash,
        "execution_hash": candidate.execution_hash,
        "execution_plan_file_sha256": sha256_bytes(plan_bytes),
        "schedule_hash": candidate.schedule_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "expected_runs": 48,
    }
    expected_reserved = {
        "suite_id": candidate.suite_id,
        "execution_hash": candidate.execution_hash,
        "execution_plan_file_sha256": sha256_bytes(plan_bytes),
        "schedule_hash": candidate.schedule_hash,
        "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        "reserved_runs": 48,
        "per_run_reserve_nanos": candidate.campaign_cost_control.per_run_reserve_nanos,
        "full_schedule_reserve_nanos": (
            candidate.campaign_cost_control.full_schedule_reserve_nanos
        ),
        "hard_cap_nanos": candidate.campaign_cost_control.hard_cap_nanos,
        "cost_censoring_allowed": False,
    }
    if not (
        len(events) >= 3
        and events[0]["event_type"] == "CampaignStarted"
        and _exact_typed_equal(events[0]["payload"], expected_started)
        and events[1]["event_type"] == "FullScheduleCostReserved"
        and _exact_typed_equal(events[1]["payload"], expected_reserved)
    ):
        raise HeldoutACDispatcherError("held-out campaign opening journal differs")

    cursor = 2
    accrued = 0
    for settled in result.settled_rows:
        authenticated = settled.authenticated_row
        row = candidate.schedule[authenticated.order - 1]
        if isinstance(settled, HeldoutACSettledCampaignRowV2):
            _verify_settled_agent_terminal_sidecar(settled, run_root=run_root)
        _verify_settled_source_files(
            authenticated,
            run_root=run_root,
            candidate=candidate,
            expected_row=row,
            authenticated_evidence=(
                settled.authenticated_evidence
                if isinstance(settled, HeldoutACSettledCampaignRowV2)
                else None
            ),
        )
        v2_atomic_settlement = isinstance(settled, HeldoutACSettledCampaignRowV2)
        required_events = 2 if v2_atomic_settlement else 3
        if len(events) < cursor + required_events:
            raise HeldoutACDispatcherError("held-out settled journal row is absent")
        start_event = events[cursor]
        terminal_event = events[cursor + 1]
        cost_event = None if v2_atomic_settlement else events[cursor + 2]
        terminal_payload = terminal_event["payload"]
        relative = terminal_payload.get("authenticated_row_path")
        if not isinstance(relative, str):
            raise HeldoutACDispatcherError("held-out terminal row path is absent")
        expected_relative = (
            Path("experiments")
            / "heldout-ac"
            / "rows"
            / candidate.execution_hash.removeprefix("sha256:")
            / f"{row.order:02d}-{authenticated.run_id}-authenticated.json"
        ).as_posix()
        if relative != expected_relative:
            raise HeldoutACDispatcherError("held-out terminal row path differs")
        row_path = canonical_heldout_ac_runtime_path(
            run_root / expected_relative,
            expected_run_root=run_root,
        )
        try:
            row_bytes = _read_canonical_runtime_file(row_path, run_root=run_root)
            raw_persisted = json.loads(row_bytes)
            if (
                isinstance(raw_persisted, dict)
                and raw_persisted.get("schema_version")
                == "heldout-ac-authenticated-persisted-evidence-v4"
            ):
                persisted_row: (
                    HeldoutACAuthenticatedPersistedRow | HeldoutACAuthenticatedPersistedEvidence
                ) = HeldoutACAuthenticatedPersistedEvidence.model_validate_json(row_bytes)
            else:
                persisted_row = HeldoutACAuthenticatedPersistedRow.model_validate_json(row_bytes)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
            raise HeldoutACDispatcherError("held-out authenticated row file is invalid") from exc
        persisted_content_hash = persisted_row.content_hash
        expected_persisted = (
            settled.authenticated_evidence
            if isinstance(settled, HeldoutACSettledCampaignRowV2)
            else authenticated
        )
        cost = authenticated.usage_evidence.token_derived_cost_nanos
        expected_start = {
            **_row_identity(row),
            "run_id": authenticated.run_id,
            "execution_hash": candidate.execution_hash,
            "execution_plan_file_sha256": sha256_bytes(plan_bytes),
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
        }
        expected_terminal = {
            **_row_identity(row),
            "run_id": authenticated.run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "authenticated_row_path": relative,
            "authenticated_row_file_sha256": sha256_bytes(row_bytes),
            "authenticated_row_content_hash": persisted_content_hash,
            "result_outcome_kind": authenticated.result.outcome_kind.value,
            "evaluation_status": authenticated.result.evaluation_status,
            "qualification_hash": authenticated.qualification_hash,
            "source_evidence_hash": authenticated.source_evidence_hash,
            "actual_run_cost_nanos": cost,
        }
        expected_cost = {
            "order": row.order,
            "schedule_row_id": row.schedule_row_id,
            "run_id": authenticated.run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "authenticated_row_file_sha256": sha256_bytes(row_bytes),
            "authenticated_row_content_hash": persisted_content_hash,
            "actual_run_cost_nanos": cost,
            "accrued_cost_nanos_before": accrued,
            "accrued_cost_nanos_after": accrued + cost,
            "remaining_reserved_rows_after": 48 - row.order,
        }
        expected_atomic = heldout_ac_terminal_cost_settled_payload(
            candidate=candidate,
            row=row,
            authenticated=authenticated,
            run_id=authenticated.run_id,
            authenticated_row_path=relative,
            authenticated_row_bytes=row_bytes,
            authenticated_row_content_hash=persisted_content_hash,
            actual_run_cost_nanos=cost,
            accrued_cost_nanos_before=accrued,
        )
        terminal_events_match = (
            terminal_event["event_type"] == "RunTerminalCostSettled"
            and _exact_typed_equal(terminal_payload, expected_atomic)
            if v2_atomic_settlement
            else terminal_event["event_type"] == "RunTerminal"
            and _exact_typed_equal(terminal_payload, expected_terminal)
            and cost_event is not None
            and cost_event["event_type"] == "RunCostSettled"
            and _exact_typed_equal(cost_event["payload"], expected_cost)
        )
        if not (
            start_event["event_type"] == "RunStarted"
            and _exact_typed_equal(start_event["payload"], expected_start)
            and terminal_events_match
            and persisted_row == expected_persisted
            and row_bytes == expected_persisted.model_dump_json(indent=2).encode("utf-8")
        ):
            raise HeldoutACDispatcherError("held-out settled journal row differs")
        accrued += cost
        cursor += required_events

    if result.confound is not None:
        confound = result.confound
        row = candidate.schedule[confound.order - 1]
        if confound.run_started_event_written:
            if len(events) <= cursor:
                raise HeldoutACDispatcherError("held-out confounded row start is absent")
            expected_start = {
                **_row_identity(row),
                "run_id": confound.run_id,
                "execution_hash": candidate.execution_hash,
                "execution_plan_file_sha256": sha256_bytes(plan_bytes),
                "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            }
            if not (
                events[cursor]["event_type"] == "RunStarted"
                and _exact_typed_equal(events[cursor]["payload"], expected_start)
            ):
                raise HeldoutACDispatcherError("held-out confounded row start differs")
            cursor += 1
        expected_confound: dict[str, Any] = {
            **_row_identity(row),
            "run_id": confound.run_id,
            "execution_hash": candidate.execution_hash,
            "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
            "trigger": confound.trigger,
            "phase": confound.phase,
            "run_started_event_written": confound.run_started_event_written,
            "confound_content_hash": confound.content_hash,
            "exception_message_persisted": False,
        }
        if isinstance(confound, HeldoutACCampaignConfoundV2):
            expected_confound["reason_code"] = confound.reason_code
            expected_confound["durable_evidence"] = (
                confound.durable_evidence.model_dump(mode="json")
                if confound.durable_evidence is not None
                else None
            )
            if confound.durable_evidence is not None:
                _verify_confound_durable_evidence(
                    confound.durable_evidence,
                    run_root=run_root,
                    candidate=candidate,
                    expected_row=row,
                )
        if len(events) <= cursor:
            raise HeldoutACDispatcherError("held-out confound journal event is absent")
        if not (
            events[cursor]["event_type"] == "RunConfounded"
            and _exact_typed_equal(events[cursor]["payload"], expected_confound)
        ):
            raise HeldoutACDispatcherError("held-out confound journal event differs")
        cursor += 1
        for item in result.not_started_rows:
            row = candidate.schedule[item.order - 1]
            expected_not_started = {
                **_row_identity(row),
                "execution_hash": candidate.execution_hash,
                "campaign_cost_control_hash": candidate.campaign_cost_control.content_hash,
                "reason": item.reason,
                "trigger": item.trigger,
            }
            if len(events) <= cursor:
                raise HeldoutACDispatcherError("held-out not-started journal row is absent")
            if not (
                events[cursor]["event_type"] == "RunNotStarted"
                and _exact_typed_equal(events[cursor]["payload"], expected_not_started)
            ):
                raise HeldoutACDispatcherError("held-out not-started journal row differs")
            cursor += 1

    completed_payload = {
        "suite_id": candidate.suite_id,
        "execution_hash": candidate.execution_hash,
        "disposition": result.disposition,
        "terminal_settled_runs": result.terminal_settled_runs,
        "not_started_runs": result.not_started_runs,
        "settled_model_cost_nanos": result.settled_model_cost_nanos,
        "unsettled_dispatched_runs": result.unsettled_dispatched_runs,
        "cost_accounting_complete": result.cost_accounting_complete,
        "prepared_result_path": str(prepared_path),
        "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
        "prepared_result_content_hash": prepared["content_hash"],
    }
    if isinstance(result, HeldoutACCampaignResultV2):
        completed_payload.update(
            {
                "observed_unsettled_model_cost_nanos": (result.observed_unsettled_model_cost_nanos),
                "observed_started_model_cost_nanos": result.observed_started_model_cost_nanos,
            }
        )
    if not (
        len(events) > cursor
        and cursor == len(events) - 1
        and events[cursor]["event_type"] == "CampaignCompleted"
        and _exact_typed_equal(events[cursor]["payload"], completed_payload)
        and result.campaign_completed_event_hash == events[cursor]["event_hash"]
        and result.journal_file_sha256 == sha256_bytes(journal_bytes)
    ):
        raise HeldoutACDispatcherError("held-out campaign completion journal differs")

    final_body = {
        **{
            key: value
            for key, value in prepared.items()
            if key not in {"schema_version", "content_hash"}
        },
        "schema_version": result.schema_version,
        "journal_file_sha256": sha256_bytes(journal_bytes),
        "campaign_completed_event_hash": events[cursor]["event_hash"],
        "prepared_result_path": str(prepared_path),
        "prepared_result_file_sha256": sha256_bytes(prepared_bytes),
        "prepared_result_content_hash": prepared["content_hash"],
    }
    expected_final = {**final_body, "content_hash": sha256_json(final_body)}
    if not _exact_typed_equal(result.model_dump(mode="json"), expected_final):
        raise HeldoutACDispatcherError("held-out final result projection differs")
    summary = {
        "disposition": result.disposition,
        "execution_hash": result.execution_hash,
        "terminal_settled_runs": result.terminal_settled_runs,
        "not_started_runs": result.not_started_runs,
        "settled_model_cost_nanos": result.settled_model_cost_nanos,
        "cost_accounting_complete": result.cost_accounting_complete,
        "analysis_ready": result.analysis_ready,
        "official_heldout_analysis": result.official_heldout_analysis,
        "result_file_sha256": sha256_bytes(result_bytes),
        "journal_file_sha256": sha256_bytes(journal_bytes),
        "provider_calls_made_by_validation": 0,
    }
    if isinstance(result, HeldoutACCampaignResultV2):
        summary.update(
            {
                "observed_unsettled_model_cost_nanos": (result.observed_unsettled_model_cost_nanos),
                "observed_started_model_cost_nanos": result.observed_started_model_cost_nanos,
                "authenticated_completion_hash": (
                    result.authenticated_completion.content_hash
                    if result.authenticated_completion is not None
                    else None
                ),
                "official_analysis_envelope_hash": (
                    result.official_analysis_envelope.content_hash
                    if result.official_analysis_envelope is not None
                    else None
                ),
            }
        )
    return summary


def run_heldout_ac_campaign(
    *,
    execution_hash: str,
    env_file: str | Path,
    root: str | Path | None = None,
    repository: str | Path | None = None,
) -> HeldoutACCampaignResult | HeldoutACCampaignResultV2:
    """Run the exact approved 48-row schedule once; no retry or resume is exposed."""

    run_root = _root(root)
    repo = _repository(repository)
    plan, plan_bytes = _load_approved_plan(execution_hash, run_root)
    candidate = _candidate_from_mapping(plan["candidate"])
    plan_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "plans" / f"{execution_hash[7:]}.json",
        expected_run_root=run_root,
    )
    plan_hash = sha256_bytes(plan_bytes)
    validated_candidate = validate_heldout_ac_dispatch_plan(
        plan=plan,
        plan_path=plan_path,
        plan_file_sha256=plan_hash,
        expected_run_root=run_root,
        repository=repo,
    )
    if candidate != validated_candidate:
        raise HeldoutACDispatcherError("held-out dispatch candidate validation differs")
    journal_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "journals" / f"{execution_hash[7:]}.jsonl",
        expected_run_root=run_root,
    )
    result_path = canonical_heldout_ac_runtime_path(
        run_root / "experiments" / "heldout-ac" / f"{execution_hash[7:]}.json",
        expected_run_root=run_root,
    )
    if journal_path.exists() or result_path.exists():
        raise HeldoutACDispatcherError("held-out campaign cannot retry or resume existing state")
    settled: list[HeldoutACSettledCampaignRow | HeldoutACSettledCampaignRowV2] = []
    confound: HeldoutACCampaignConfound | HeldoutACCampaignConfoundV2 | None = None
    not_started: list[HeldoutACNotStartedRow] = []
    current_phase: ConfoundPhase = "row-dispatch"
    _create_journal(journal_path, candidate, plan_hash, run_root=run_root)

    def seal_pre_row_failure(exc: Exception) -> HeldoutACCampaignResult:
        first_row = candidate.schedule[0]
        pre_row_confound, remaining = _record_confound(
            candidate=candidate,
            run_root=run_root,
            journal_path=journal_path,
            row=first_row,
            run_id=make_run_id("heldout"),
            exc=exc,
            phase="row-dispatch",
            run_started_event_written=False,
        )
        return _finalize_result(
            run_root=run_root,
            candidate=candidate,
            plan_path=plan_path,
            plan_hash=plan_hash,
            journal_path=journal_path,
            result_path=result_path,
            settled=[],
            confound=pre_row_confound,
            not_started=remaining,
        )

    credential_stack = ExitStack()
    try:
        try:
            installed_sdk = version("openai")
        except PackageNotFoundError as exc:
            raise HeldoutACDispatcherError("held-out OpenAI SDK is unavailable") from exc
        if installed_sdk != candidate.readiness.openai_sdk.version:
            raise HeldoutACDispatcherError("held-out OpenAI SDK version differs from the candidate")
        if os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE"):
            raise HeldoutACDispatcherError("custom OpenAI base URLs are forbidden")
        exact_openai_api_key_present(env_file)
        authorization = issue_live_execution_authorization(execution_hash, root=run_root)
        runner = AgentRunner(root=run_root)
        credential_stack.enter_context(exact_openai_api_key_environment(env_file))
        api_key = os.environ.get("OPENAI_API_KEY")
        if not isinstance(api_key, str) or not api_key:
            raise HeldoutACDispatcherError("held-out runtime credential was not installed")
    except Exception as exc:
        credential_stack.close()
        return seal_pre_row_failure(exc)

    with credential_stack:
        for row in candidate.schedule:
            run_id = make_run_id("heldout")
            task_dir = repo / row.task_path
            run_started_event_written = False
            durable_evidence: HeldoutACConfoundedDurableEvidence | None = None
            current_phase = "row-dispatch"
            try:
                package = load_task_package(task_dir)
                runtime_authority = materialize_heldout_ac_runtime_task_authority(
                    candidate=candidate,
                    task_id=row.task_id,
                    package=package,
                    api_key=api_key,
                    repository=repo,
                )
                manifest = build_heldout_ac_run_manifest(
                    candidate=candidate,
                    row_order=row.order,
                    run_id=run_id,
                    created_at=utc_now(),
                    authority=runtime_authority,
                )
                _append_journal(
                    journal_path,
                    "RunStarted",
                    {
                        **_row_identity(row),
                        "run_id": run_id,
                        "execution_hash": candidate.execution_hash,
                        "execution_plan_file_sha256": plan_hash,
                        "campaign_cost_control_hash": (
                            candidate.campaign_cost_control.content_hash
                        ),
                    },
                    run_root=run_root,
                )
                run_started_event_written = True
                current_phase = "row-dispatch"
                runner.start(
                    task_dir,
                    model="openai",
                    manifest=manifest,
                    live_authorization=authorization,
                    evaluator_v2_authority=runtime_authority.qualification_authority,
                )
                current_phase = "cost-observation"
                cost_observation, cost_observation_relative = _persist_cost_observation(
                    candidate=candidate,
                    order=row.order,
                    run_id=run_id,
                    run_root=run_root,
                )
                durable_evidence = _durable_evidence_from_cost_observation(
                    cost_observation,
                    run_root=run_root,
                    observation_relative_path=cost_observation_relative,
                )
                expected_usage_relative = _usage_evidence_relative_path(
                    candidate,
                    order=row.order,
                    run_id=run_id,
                )
                current_phase = "qualification"
                usage_relative = _persist_usage_evidence(
                    candidate=candidate,
                    order=row.order,
                    run_id=run_id,
                    run_root=run_root,
                    repository=repo,
                    task_dir=task_dir,
                    authority=runtime_authority,
                )
                if usage_relative != expected_usage_relative:
                    raise HeldoutACDispatcherError(
                        "held-out durable usage path differs from the schedule"
                    )
                durable_evidence = _extend_durable_evidence_from_files(
                    durable_evidence,
                    run_root=run_root,
                    usage_relative_path=usage_relative,
                    candidate=candidate,
                    expected_row=row,
                )
                current_phase = "authentication"
                persisted_evidence = _authenticate_persisted_evidence(
                    candidate=candidate,
                    order=row.order,
                    run_root=run_root,
                    repository=repo,
                    task_dir=task_dir,
                    authority=runtime_authority,
                    usage_evidence_relative_path=usage_relative,
                )
                authenticated_durable_evidence = _durable_evidence_from_authenticated(
                    persisted_evidence,
                    run_root=run_root,
                    usage_relative_path=usage_relative,
                    cost_observation=cost_observation,
                    cost_observation_relative_path=cost_observation_relative,
                )
                failure_binding_fields = {
                    "content_hash",
                    "evaluator_failure_code",
                    "evaluator_failure_event_relative_path",
                    "evaluator_failure_event_file_sha256",
                    "evaluator_failure_event_hash",
                    "evaluator_failure_event",
                }
                durable_projection_matches = (
                    _exact_typed_equal(
                        authenticated_durable_evidence.model_dump(
                            mode="json", exclude=failure_binding_fields
                        ),
                        durable_evidence.model_dump(mode="json", exclude=failure_binding_fields),
                    )
                    if isinstance(persisted_evidence, HeldoutACEvaluatorConfoundEvidence)
                    else authenticated_durable_evidence == durable_evidence
                )
                if not durable_projection_matches:
                    raise HeldoutACDispatcherError(
                        "held-out authenticated durable evidence projection differs"
                    )
                if isinstance(persisted_evidence, HeldoutACEvaluatorConfoundEvidence):
                    durable_evidence = authenticated_durable_evidence
                    evaluator_exc: Exception
                    if (
                        persisted_evidence.evaluator_failure_code
                        == "EVALUATOR_CONTROL_CONTRACT_COLLISION"
                    ):
                        evaluator_exc = EvaluatorControlContractCollision(
                            "held-out evaluator control contract collision"
                        )
                    else:
                        evaluator_exc = UntrustedPrivateMarkerHit(
                            "held-out untrusted private marker hit"
                        )
                    confound, not_started = _record_confound(
                        candidate=candidate,
                        run_root=run_root,
                        journal_path=journal_path,
                        row=row,
                        run_id=run_id,
                        exc=evaluator_exc,
                        phase="authentication",
                        run_started_event_written=True,
                        reason_code=persisted_evidence.evaluator_failure_code,
                        durable_evidence=durable_evidence,
                    )
                    break
                authenticated = persisted_evidence.row
                current_phase = "settlement"
                settled_row = _settled_row(persisted_evidence, run_root=run_root)
                accrued_before = sum(
                    item.authenticated_row.usage_evidence.token_derived_cost_nanos
                    for item in settled
                )
                cost = _validate_settlement_limits(
                    authenticated,
                    accrued_before=accrued_before,
                    candidate=candidate,
                )
                row_path = (
                    run_root
                    / "experiments"
                    / "heldout-ac"
                    / "rows"
                    / candidate.execution_hash[7:]
                    / f"{row.order:02d}-{run_id}-authenticated.json"
                )
                row_bytes = persisted_evidence.model_dump_json(indent=2).encode("utf-8")
                _write_new(row_path, row_bytes, run_root=run_root)
                relative = row_path.relative_to(run_root).as_posix()
                persisted_content_hash = persisted_evidence.content_hash
                _append_terminal_cost_settled(
                    journal_path,
                    run_root=run_root,
                    candidate=candidate,
                    row=row,
                    authenticated=authenticated,
                    run_id=run_id,
                    authenticated_row_path=relative,
                    authenticated_row_bytes=row_bytes,
                    authenticated_row_content_hash=persisted_content_hash,
                    actual_run_cost_nanos=cost,
                    accrued_cost_nanos_before=accrued_before,
                )
                settled.append(settled_row)
            except Exception as exc:
                confound, not_started = _record_confound(
                    candidate=candidate,
                    run_root=run_root,
                    journal_path=journal_path,
                    row=row,
                    run_id=run_id,
                    exc=exc,
                    phase=current_phase,
                    run_started_event_written=run_started_event_written,
                    durable_evidence=durable_evidence,
                )
                break

    return _finalize_result(
        run_root=run_root,
        candidate=candidate,
        plan_path=plan_path,
        plan_hash=plan_hash,
        journal_path=journal_path,
        result_path=result_path,
        settled=settled,
        confound=confound,
        not_started=not_started,
    )


__all__ = [
    "CAMPAIGN_RESULT_SCHEMA_VERSION",
    "CAMPAIGN_RESULT_SCHEMA_VERSION_V2",
    "HeldoutACCampaignConfound",
    "HeldoutACCampaignConfoundV2",
    "HeldoutACCampaignResult",
    "HeldoutACCampaignResultV2",
    "HeldoutACConfoundedDurableEvidence",
    "HeldoutACDispatcherError",
    "HeldoutACNotStartedRow",
    "HeldoutACSettledCampaignRow",
    "HeldoutACSettledCampaignRowV2",
    "heldout_ac_paid_campaign_identity_consumed",
    "prepare_heldout_ac_approved_plan",
    "run_heldout_ac_campaign",
    "validate_heldout_ac_campaign_result",
]
