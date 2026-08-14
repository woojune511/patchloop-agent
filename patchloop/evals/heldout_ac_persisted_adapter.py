"""Source for authenticating future held-out A/C persisted row evidence.

This module grants no execution or task access by itself.  Its runtime entrypoint
requires an already-qualified task/evaluator binding, invokes the existing
evaluator-v2 receipt validator and read-only trace recomputation, then binds the
exact persisted result, qualification and usage-evidence bytes.  No campaign is
materialized in the current repository.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from pydantic import Field, PrivateAttr, ValidationError, model_validator

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Budget,
    EvaluatorV2EvaluationReceipt,
    EventType,
    RunEvent,
    RunResult,
    TaskPackage,
)
from patchloop.errors import ContractError
from patchloop.evals.heldout_ac_completion import (
    HeldoutACDurableUsage,
    heldout_ac_schedule_row_id,
)
from patchloop.evals.heldout_ac_contracts import (
    HELDOUT_AC_SUITE_ID,
    HeldoutACFrozenModel,
    HeldoutACSuite,
)
from patchloop.evals.heldout_ac_task_evaluator import HeldoutACTaskEvaluatorBinding
from patchloop.state import StateStore
from patchloop.util import canonical_json, safe_relative_path, sha256_bytes, sha256_json
from patchloop.verifier.receipt import (
    EvaluatorV2QualificationAuthority,
    EvaluatorV2ReceiptValidation,
    validate_persisted_evaluator_v2_evaluation_receipt,
)

USAGE_SCHEMA_VERSION = "heldout-ac-durable-usage-evidence-v1"
ROW_SCHEMA_VERSION = "heldout-ac-authenticated-persisted-row-v1"
QUALIFICATION_PROJECTION_SCHEMA_VERSION = (
    "heldout-ac-authenticated-trace-qualification-projection-v2"
)
PERSISTED_EVIDENCE_SCHEMA_VERSION = "heldout-ac-authenticated-persisted-evidence-v4"
AGENT_TERMINAL_EVENT_PROJECTION_SCHEMA_VERSION = "heldout-ac-agent-terminal-event-projection-v1"
EVALUATOR_CONFOUND_SCHEMA_VERSION = "heldout-ac-authenticated-evaluator-confound-v1"
HELDOUT_AC_PRICE_NANOS_PER_TOKEN: Mapping[str, int] = MappingProxyType(
    {
        "uncached_input": 750,
        "cached_input": 75,
        "cache_write_input": 750,
        "output": 4_500,
    }
)
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"

EvaluatorFailureCode = Literal[
    "EVALUATOR_CONTROL_CONTRACT_COLLISION",
    "UNTRUSTED_PRIVATE_MARKER_HIT",
]
AgentTerminalType = Literal[
    "token-budget-exhaustion",
    "model-call-limit",
    "tool-call-limit",
    "wall-clock-timeout",
    "submission-failure",
]
AgentTerminalReasonCode = Literal[
    "exact_request_budget_exceeded",
    "model_call_budget_exhausted",
    "tool_call_budget_exhausted",
    "wall_clock_budget_exhausted",
]

_AGENT_TERMINAL_REASON_TYPES: dict[str, AgentTerminalType] = {
    "exact_request_budget_exceeded": "token-budget-exhaustion",
    "model_call_budget_exhausted": "model-call-limit",
    "tool_call_budget_exhausted": "tool-call-limit",
    "wall_clock_budget_exhausted": "wall-clock-timeout",
}

_QUALIFICATION_KEYS = {
    "schema_version",
    "run_id",
    "qualified",
    "trace_integrity_passed",
    "leakage_scan_passed",
    "evaluation_reached",
    "outcome_kind",
    "purpose",
    "experiment_id",
    "dataset_role",
    "dataset_manifest_hash",
    "suite_hash",
    "execution_hash",
    "schedule_row_id",
    "model_provider",
    "memory_condition",
    "fault_type",
    "memory_candidate_eligible",
    "failure_record_id",
    "failure_record_hash",
    "source_evidence_hash",
    "checks",
    "evaluator_version",
    "evaluator_v2_receipt_hash",
    "evaluator_v2_receipt_file_hash",
    "evaluator_v2_source_hash",
    "evaluator_v2_source_qualification_hash",
    "evaluator_v2_runtime_authenticated",
    "evaluator_v2_completion_eligible",
    "task_id",
    "model_id",
    "reasoning_effort",
    "reasoning_mode",
    "service_tier",
    "max_output_tokens",
    "budget",
    "harness_git_commit",
    "tool_schema_version",
    "context_policy_version",
    "runtime_contract_content_hash",
    "transport_max_retries",
    "qualification_hash",
}

_BASE_HELDOUT_CHECK_IDS = (
    "task_identity",
    "heldout_ac_runtime_contract",
    "bounded_call_guard_contract",
    "contiguous_events",
    "worker_claim_provenance",
    "single_terminal_event",
    "required_trace_evidence",
    "submission_lifecycle",
    "fixed_memory_delivery_integrity",
    "live_openai_provider",
    "frozen_model_contract",
    "fault_free",
    "frozen_campaign_provenance",
    "approved_execution_plan",
    "heldout_ac_full_schedule_cost_contract",
    "sandbox_provenance",
    "agent_visible_artifacts",
    "rejected_patch_retry_context",
    "public_private_boundary",
    "investigation_evidence",
    "investigation_lifecycle",
    "prompt_token_integrity",
    "usage_reconciliation",
    "persisted_result",
    "pilot_tool_loop",
    "terminal_result_integrity",
    "failure_record_linkage",
)


class HeldoutACPersistedUsageEvidence(HeldoutACFrozenModel):
    schema_version: Literal[USAGE_SCHEMA_VERSION] = USAGE_SCHEMA_VERSION
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    pricing_binding_hash: str = Field(pattern=_SHA256_PATTERN)
    price_nanos_per_token: dict[
        Literal["uncached_input", "cached_input", "cache_write_input", "output"], int
    ]
    usage: HeldoutACDurableUsage
    token_derived_cost_nanos: int = Field(ge=0)
    qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_file_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_file_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_usage_evidence(self) -> HeldoutACPersistedUsageEvidence:
        expected_keys = {
            "uncached_input",
            "cached_input",
            "cache_write_input",
            "output",
        }
        if set(self.price_nanos_per_token) != expected_keys or any(
            type(value) is not int or value < 0 for value in self.price_nanos_per_token.values()
        ):
            raise ValueError("held-out price table must contain exact nonnegative integers")
        usage = self.usage
        uncached = usage.input_tokens - usage.cached_input_tokens - usage.cache_write_input_tokens
        prices = self.price_nanos_per_token
        expected_cost = (
            uncached * prices["uncached_input"]
            + usage.cached_input_tokens * prices["cached_input"]
            + usage.cache_write_input_tokens * prices["cache_write_input"]
            + usage.output_tokens * prices["output"]
        )
        if self.token_derived_cost_nanos != expected_cost:
            raise ValueError("held-out usage evidence cost does not match its counters")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("held-out usage evidence content hash mismatch")
        return self


class HeldoutACAuthenticatedQualificationProjection(HeldoutACFrozenModel):
    """Reduced, typed projection of a fully recomputed trace-qualification-v2.

    The projection deliberately has its own schema identity.  It records the
    source schema and hashes the complete check list without pretending to be
    the producer's considerably larger source payload.
    """

    schema_version: Literal[QUALIFICATION_PROJECTION_SCHEMA_VERSION] = (
        QUALIFICATION_PROJECTION_SCHEMA_VERSION
    )
    source_schema_version: Literal["trace-qualification-v2"] = "trace-qualification-v2"
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    qualified: Literal[True] = True
    trace_integrity_passed: Literal[True] = True
    leakage_scan_passed: Literal[True] = True
    evaluation_reached: bool
    outcome_kind: Literal["resolved", "task_failure", "agent_failure", "infrastructure_error"]
    purpose: Literal["core"] = "core"
    experiment_id: Literal[HELDOUT_AC_SUITE_ID] = HELDOUT_AC_SUITE_ID
    dataset_role: Literal["core-same-repo", "core-cross-repo"]
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    suite_hash: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    memory_condition: Literal["no_memory", "structured"]
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    source_qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    check_count: int = Field(ge=27, le=28)
    checks_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_version: Literal["v2"] = "v2"
    evaluator_v2_source_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    evaluator_v2_source_qualification_hash: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    evaluator_v2_receipt_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_file_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    evaluator_v2_runtime_authenticated: bool
    evaluator_v2_completion_eligible: bool
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_projection(self) -> HeldoutACAuthenticatedQualificationProjection:
        if (
            type(self.evaluation_reached) is not bool
            or type(self.evaluator_v2_runtime_authenticated) is not bool
            or type(self.evaluator_v2_completion_eligible) is not bool
        ):
            raise ValueError("qualification projection flags must be exact booleans")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("authenticated qualification projection content hash mismatch")
        return self


class HeldoutACAuthenticatedPersistedRow(HeldoutACFrozenModel):
    schema_version: Literal[ROW_SCHEMA_VERSION] = ROW_SCHEMA_VERSION
    persisted_evidence_authenticated: Literal[True] = True
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    task_evaluator_binding_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_file_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_semantic_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_file_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    usage_evidence_file_hash: str = Field(pattern=_SHA256_PATTERN)
    usage_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    evaluator_v2_receipt_file_hash: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    result: RunResult
    usage_evidence: HeldoutACPersistedUsageEvidence
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_row(self) -> HeldoutACAuthenticatedPersistedRow:
        if self.result.run_id != self.run_id:
            raise ValueError("authenticated row result identity differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("authenticated persisted row content hash mismatch")
        return self


class HeldoutACAgentTerminalEventProjection(HeldoutACFrozenModel):
    """Safe typed projection authenticating one agent-terminal classification."""

    schema_version: Literal[AGENT_TERMINAL_EVENT_PROJECTION_SCHEMA_VERSION] = (
        AGENT_TERMINAL_EVENT_PROJECTION_SCHEMA_VERSION
    )
    event_id: str = Field(min_length=1)
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    sequence: int = Field(ge=1)
    type: Literal["ModelGenerationBlocked", "RunFailed"]
    timestamp: str
    actor: Literal["budget-guard", "runner"]
    reason_code: AgentTerminalReasonCode | None
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_projection(self) -> HeldoutACAgentTerminalEventProjection:
        try:
            parsed_timestamp = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("agent terminal event timestamp is invalid") from exc
        if self.type == "ModelGenerationBlocked":
            valid_shape = self.actor == "budget-guard" and self.reason_code is not None
        else:
            valid_shape = self.actor == "runner" and self.reason_code is None
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if not (
            self.timestamp.endswith("Z")
            and parsed_timestamp.tzinfo is not None
            and parsed_timestamp.utcoffset() == UTC.utcoffset(parsed_timestamp)
            and valid_shape
            and self.content_hash == expected
        ):
            raise ValueError("agent terminal event projection differs")
        return self

    def terminal_type(self) -> AgentTerminalType:
        if self.type == "RunFailed":
            return "submission-failure"
        assert self.reason_code is not None
        return _AGENT_TERMINAL_REASON_TYPES[self.reason_code]


class HeldoutACAuthenticatedPersistedEvidence(HeldoutACFrozenModel):
    """Serializable evidence DTO that is never authority by itself.

    The runtime authenticator attaches an owner-bound, non-serialized capability
    to the exact returned instance.  Dumping, reparsing, copying or directly
    constructing this DTO therefore cannot authorize official completion.
    """

    schema_version: Literal[PERSISTED_EVIDENCE_SCHEMA_VERSION] = PERSISTED_EVIDENCE_SCHEMA_VERSION
    persisted_evidence_authenticated: Literal[True] = True
    official: Literal[False] = False
    analysis_eligible: Literal[False] = False
    row: HeldoutACAuthenticatedPersistedRow
    qualification: HeldoutACAuthenticatedQualificationProjection
    terminal_type: AgentTerminalType | None
    terminal_event: HeldoutACAgentTerminalEventProjection | None
    content_hash: str = Field(pattern=_SHA256_PATTERN)
    _runtime_authentication_capability: object | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def validate_evidence(self) -> HeldoutACAuthenticatedPersistedEvidence:
        if (
            self.row.qualification_hash != self.qualification.source_qualification_hash
            or self.row.source_evidence_hash != self.qualification.source_evidence_hash
            or self.row.run_id != self.qualification.run_id
            or self.row.schedule_row_id != self.qualification.schedule_row_id
        ):
            raise ValueError("authenticated persisted evidence projection differs")
        evaluator_completed = self.row.result.evaluation_status == "completed"
        if not (
            evaluator_completed == (self.terminal_type is None) == (self.terminal_event is None)
        ):
            raise ValueError("authenticated persisted evidence terminal type differs")
        if self.terminal_event is not None and not (
            self.terminal_event.run_id == self.row.run_id
            and self.terminal_event.terminal_type() == self.terminal_type
        ):
            raise ValueError("authenticated persisted evidence terminal event differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("authenticated persisted evidence content hash mismatch")
        return self


class _RuntimeAuthenticationCapability:
    """Owner-bound runtime marker; deliberately absent from serialized evidence."""

    __slots__ = ("content_hash", "owner")

    def __init__(self, owner: HeldoutACAuthenticatedPersistedEvidence) -> None:
        self.owner = owner
        self.content_hash = owner.content_hash

    def __copy__(self) -> _RuntimeAuthenticationCapability:
        return self

    def __deepcopy__(self, _memo: dict[int, object]) -> _RuntimeAuthenticationCapability:
        return self


def _issue_runtime_authentication_capability(
    evidence: HeldoutACAuthenticatedPersistedEvidence,
) -> HeldoutACAuthenticatedPersistedEvidence:
    capability = _RuntimeAuthenticationCapability(evidence)
    evidence._runtime_authentication_capability = capability
    return evidence


def has_heldout_ac_runtime_authentication_capability(
    evidence: object,
) -> bool:
    """Return whether ``evidence`` is the exact runtime-authenticated instance."""

    if type(evidence) is not HeldoutACAuthenticatedPersistedEvidence:
        return False
    capability = evidence._runtime_authentication_capability
    return (
        type(capability) is _RuntimeAuthenticationCapability
        and capability.owner is evidence
        and capability.content_hash == evidence.content_hash
    )


class HeldoutACEvaluatorConfoundEvidence(HeldoutACFrozenModel):
    """Authenticated post-submission evaluator confound, never an analysis row."""

    schema_version: Literal[EVALUATOR_CONFOUND_SCHEMA_VERSION] = EVALUATOR_CONFOUND_SCHEMA_VERSION
    persisted_evidence_authenticated: Literal[True] = True
    analysis_eligible: Literal[False] = False
    order: int = Field(ge=1, le=48)
    wave: int = Field(ge=1, le=4)
    task_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    role: Literal["core-same-repo", "core-cross-repo"]
    condition: Literal["no_memory", "structured"]
    repetition: Literal[1, 2]
    run_id: str = Field(pattern=r"^run_[A-Za-z0-9_-]+$")
    schedule_row_id: str = Field(pattern=_SHA256_PATTERN)
    execution_hash: str = Field(pattern=_SHA256_PATTERN)
    task_evaluator_binding_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_file_hash: str = Field(pattern=_SHA256_PATTERN)
    persisted_result_semantic_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_file_hash: str = Field(pattern=_SHA256_PATTERN)
    qualification_hash: str = Field(pattern=_SHA256_PATTERN)
    source_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    usage_evidence_file_hash: str = Field(pattern=_SHA256_PATTERN)
    usage_evidence_hash: str = Field(pattern=_SHA256_PATTERN)
    evaluator_failure_code: EvaluatorFailureCode
    evaluator_failure_event_hash: str = Field(pattern=_SHA256_PATTERN)
    result: RunResult
    usage_evidence: HeldoutACPersistedUsageEvidence
    qualification: HeldoutACAuthenticatedQualificationProjection
    content_hash: str = Field(pattern=_SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_confound(self) -> HeldoutACEvaluatorConfoundEvidence:
        if not (
            self.result.run_id == self.run_id == self.qualification.run_id
            and self.result.schema_version == "run-result-v2"
            and self.result.agent_submission_status == "completed"
            and self.result.evaluation_status == "not_run"
            and self.result.outcome_kind is not None
            and self.result.outcome_kind.value == "infrastructure_error"
            and self.result.terminal_error
            == {"code": "EVALUATOR_INFRASTRUCTURE_ERROR", "phase": "evaluator"}
            and self.qualification.outcome_kind == "infrastructure_error"
            and self.qualification.evaluation_reached is False
            and self.qualification.evaluator_v2_runtime_authenticated is False
            and self.qualification.evaluator_v2_completion_eligible is False
            and self.qualification.evaluator_v2_receipt_hash is None
            and self.qualification.evaluator_v2_receipt_file_hash is None
        ):
            raise ValueError("post-submission evaluator confound shape differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("authenticated evaluator confound content hash mismatch")
        return self


def _qualification_hash(payload: Mapping[str, Any]) -> str:
    recorded = payload.get("qualification_hash")
    if not isinstance(recorded, str):
        raise ContractError("held-out trace qualification has no content hash")
    expected = sha256_json(
        {key: value for key, value in payload.items() if key != "qualification_hash"}
    )
    if recorded != expected:
        raise ContractError("held-out trace qualification content hash mismatch")
    return recorded


def _usage_from_result(result: RunResult) -> dict[str, Any]:
    raw = result.usage.model_dump(mode="json")
    return {
        key: raw[key]
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


def validate_heldout_ac_persisted_usage_cross_binding(
    *,
    result: RunResult,
    usage_evidence: HeldoutACPersistedUsageEvidence,
    expected_run_id: str,
    expected_schedule_row_id: str,
    expected_pricing_binding_hash: str,
    expected_qualification_hash: str,
    expected_source_evidence_hash: str,
    expected_result_file_hash: str,
    expected_result_semantic_hash: str,
    expected_receipt_file_hash: str | None,
) -> None:
    """Recompute the frozen usage/result bindings used by producer and replay."""

    expected_usage = HeldoutACDurableUsage(**_usage_from_result(result))
    expected_cost_nanos = expected_usage.token_derived_cost_nanos()
    completed = result.evaluation_status == "completed"
    if not (
        result.run_id == expected_run_id == usage_evidence.run_id
        and usage_evidence.schedule_row_id == expected_schedule_row_id
        and usage_evidence.pricing_binding_hash == expected_pricing_binding_hash
        and usage_evidence.price_nanos_per_token == HELDOUT_AC_PRICE_NANOS_PER_TOKEN
        and usage_evidence.usage == expected_usage
        and usage_evidence.token_derived_cost_nanos == expected_cost_nanos
        and Decimal(str(result.usage.model_cost_usd))
        == Decimal(expected_cost_nanos) / Decimal(1_000_000_000)
        and usage_evidence.qualification_hash == expected_qualification_hash
        and usage_evidence.source_evidence_hash == expected_source_evidence_hash
        and usage_evidence.persisted_result_file_hash == expected_result_file_hash
        and sha256_json(result.model_dump(mode="json")) == expected_result_semantic_hash
        and usage_evidence.evaluator_v2_receipt_file_hash == expected_receipt_file_hash
        and completed == (expected_receipt_file_hash is not None)
    ):
        raise ContractError("held-out persisted usage/result cross-binding differs")


def _project_agent_terminal_event(
    event: RunEvent,
    *,
    terminal_type: AgentTerminalType,
) -> HeldoutACAgentTerminalEventProjection:
    reason_code = (
        event.payload.get("reason_code")
        if event.type == EventType.MODEL_GENERATION_BLOCKED
        else None
    )
    expected_terminal_type = (
        _AGENT_TERMINAL_REASON_TYPES.get(reason_code)
        if isinstance(reason_code, str)
        else "submission-failure"
        if event.type == EventType.RUN_FAILED
        else None
    )
    if not (
        expected_terminal_type == terminal_type
        and event.type in {EventType.MODEL_GENERATION_BLOCKED, EventType.RUN_FAILED}
        and (
            (event.type == EventType.MODEL_GENERATION_BLOCKED and event.actor == "budget-guard")
            or (event.type == EventType.RUN_FAILED and event.actor == "runner")
        )
    ):
        raise ContractError("held-out agent terminal event is not trusted")
    body = {
        "schema_version": AGENT_TERMINAL_EVENT_PROJECTION_SCHEMA_VERSION,
        "event_id": event.event_id,
        "run_id": event.run_id,
        "sequence": event.sequence,
        "type": event.type.value,
        "timestamp": event.model_dump(mode="json")["timestamp"],
        "actor": event.actor,
        "reason_code": reason_code,
    }
    return HeldoutACAgentTerminalEventProjection(
        schema_version=AGENT_TERMINAL_EVENT_PROJECTION_SCHEMA_VERSION,
        event_id=event.event_id,
        run_id=event.run_id,
        sequence=event.sequence,
        type=event.type.value,
        timestamp=body["timestamp"],
        actor=event.actor,
        reason_code=reason_code,
        content_hash=sha256_json(body),
    )


def _canonical_qualification_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _canonical_usage_evidence_bytes(payload: HeldoutACPersistedUsageEvidence) -> bytes:
    return json.dumps(
        payload.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
    ).encode("utf-8")


def _require_sha256(value: Any, *, field_name: str, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or re.fullmatch(_SHA256_PATTERN, value) is None:
        raise ContractError(f"held-out trace qualification {field_name} is invalid")


def _heldout_check_ids(*, evaluator_completed: bool) -> tuple[str, ...]:
    if not evaluator_completed:
        return _BASE_HELDOUT_CHECK_IDS
    insertion = _BASE_HELDOUT_CHECK_IDS.index("public_private_boundary")
    return (
        *_BASE_HELDOUT_CHECK_IDS[:insertion],
        "verifier_evidence_artifacts",
        *_BASE_HELDOUT_CHECK_IDS[insertion:],
    )


def _project_authenticated_qualification(
    *,
    qualification: Mapping[str, Any],
    suite: HeldoutACSuite,
    execution_hash: str,
    order: int,
    result: RunResult,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    receipt_validation: EvaluatorV2ReceiptValidation | None,
) -> HeldoutACAuthenticatedQualificationProjection:
    """Validate the complete producer payload, then emit a distinct reduced DTO."""

    if set(qualification) != _QUALIFICATION_KEYS:
        raise ContractError("held-out trace qualification fields are incomplete or unknown")
    qualification_hash = _qualification_hash(qualification)
    scheduled = suite.schedule[order - 1]
    expected_row_id = heldout_ac_schedule_row_id(
        suite=suite,
        execution_hash=execution_hash,
        order=order,
    )
    checks = qualification.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ContractError("held-out trace qualification has no full check list")
    check_ids: list[str] = []
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"check_id", "passed", "details"}:
            raise ContractError("held-out trace qualification check shape is invalid")
        check_id = check["check_id"]
        if not isinstance(check_id, str) or not check_id:
            raise ContractError("held-out trace qualification check identity is invalid")
        if check["passed"] is not True or not isinstance(check["details"], dict):
            raise ContractError("held-out trace qualification contains a failed or invalid check")
        check_ids.append(check_id)
    expected_check_ids = _heldout_check_ids(
        evaluator_completed=result.evaluation_status == "completed"
    )
    if tuple(check_ids) != expected_check_ids or len(check_ids) != len(set(check_ids)):
        raise ContractError("held-out trace qualification check set or order differs")

    for field_name in (
        "dataset_manifest_hash",
        "suite_hash",
        "execution_hash",
        "schedule_row_id",
        "source_evidence_hash",
        "runtime_contract_content_hash",
    ):
        _require_sha256(qualification.get(field_name), field_name=field_name)
    for field_name in (
        "failure_record_hash",
        "evaluator_v2_receipt_hash",
        "evaluator_v2_receipt_file_hash",
        "evaluator_v2_source_hash",
        "evaluator_v2_source_qualification_hash",
    ):
        _require_sha256(qualification.get(field_name), field_name=field_name, nullable=True)
    failure_record_id = qualification.get("failure_record_id")
    failure_record_hash = qualification.get("failure_record_hash")
    if (failure_record_id is None) != (failure_record_hash is None) or (
        failure_record_id is not None
        and (
            not isinstance(failure_record_id, str)
            or re.fullmatch(r"^fail_[A-Za-z0-9_-]+$", failure_record_id) is None
        )
    ):
        raise ContractError("held-out trace qualification failure record binding is invalid")
    try:
        budget = Budget.model_validate(qualification.get("budget"))
    except ValidationError as exc:
        raise ContractError("held-out trace qualification budget is invalid") from exc

    runtime = suite.runtime
    expected_budget = {
        "max_model_calls": runtime.max_model_calls,
        "max_tool_calls": runtime.max_tool_calls,
        "max_total_tokens": runtime.max_total_tokens,
        "wall_clock_timeout_seconds": runtime.wall_clock_timeout_seconds,
        "token_budget_schema_version": runtime.token_budget_schema_version,
        "max_cumulative_input_tokens": runtime.max_cumulative_input_tokens,
        "max_cumulative_output_tokens": runtime.max_cumulative_output_tokens,
    }
    exact_flags = all(
        type(qualification.get(field_name)) is bool
        for field_name in (
            "qualified",
            "trace_integrity_passed",
            "leakage_scan_passed",
            "evaluation_reached",
            "memory_candidate_eligible",
            "evaluator_v2_runtime_authenticated",
            "evaluator_v2_completion_eligible",
        )
    )
    common_identity = (
        exact_flags
        and qualification.get("schema_version") == "trace-qualification-v2"
        and qualification.get("qualified") is True
        and qualification.get("trace_integrity_passed") is True
        and qualification.get("leakage_scan_passed") is True
        and qualification.get("purpose") == "core"
        and qualification.get("experiment_id") == HELDOUT_AC_SUITE_ID
        and qualification.get("run_id") == result.run_id
        and qualification.get("task_id") == scheduled.task_id
        and qualification.get("dataset_role") == scheduled.role
        and qualification.get("memory_condition") == scheduled.condition
        and qualification.get("suite_hash") == suite.content_hash
        and qualification.get("execution_hash") == execution_hash
        and qualification.get("schedule_row_id") == expected_row_id
        and qualification.get("outcome_kind")
        == (result.outcome_kind.value if result.outcome_kind is not None else None)
        and qualification.get("memory_candidate_eligible") is False
        and qualification.get("evaluator_version") == "v2"
        and qualification.get("model_provider") == runtime.model
        and qualification.get("model_id") == runtime.model_id
        and qualification.get("reasoning_effort") == runtime.reasoning_effort
        and qualification.get("reasoning_mode") == runtime.reasoning_mode
        and qualification.get("service_tier") == runtime.service_tier
        and type(qualification.get("max_output_tokens")) is int
        and qualification.get("max_output_tokens") == runtime.max_output_tokens
        and type(qualification.get("transport_max_retries")) is int
        and qualification.get("transport_max_retries") == runtime.transport_max_retries
        and qualification.get("tool_schema_version") == runtime.tool_schema_version
        and qualification.get("context_policy_version") == runtime.context_policy_version
        and qualification.get("fault_type") == "none"
        and isinstance(qualification.get("harness_git_commit"), str)
        and re.fullmatch(r"[0-9a-f]{40}", qualification["harness_git_commit"]) is not None
        and budget.model_dump(mode="json") == expected_budget
        and result.evaluator_contract is not None
        and result.evaluator_contract == task_evaluator_binding.evaluator_contract
    )
    if not common_identity:
        raise ContractError("held-out trace qualification runtime identity differs")

    completed = result.evaluation_status == "completed"
    if completed:
        if receipt_validation is None:
            raise ContractError("evaluator-completed qualification lacks receipt validation")
        receipt = receipt_validation.receipt
        status_valid = (
            result.agent_submission_status == "completed"
            and qualification.get("evaluation_reached") is True
            and qualification.get("evaluator_v2_runtime_authenticated") is True
            and qualification.get("evaluator_v2_completion_eligible") is True
            and qualification.get("evaluator_v2_receipt_hash") == receipt.content_hash
            and qualification.get("evaluator_v2_source_hash")
            == task_evaluator_binding.evaluator_source_hash
            and qualification.get("evaluator_v2_source_qualification_hash")
            == receipt.source_qualification_hash
            and isinstance(qualification.get("evaluator_v2_receipt_file_hash"), str)
        )
    else:
        status_valid = (
            result.evaluation_status == "not_run"
            and qualification.get("evaluation_reached") is False
            and qualification.get("evaluator_v2_runtime_authenticated") is False
            and qualification.get("evaluator_v2_completion_eligible") is False
            and qualification.get("evaluator_v2_receipt_hash") is None
            and qualification.get("evaluator_v2_receipt_file_hash") is None
            and qualification.get("evaluator_v2_source_hash") is None
            and qualification.get("evaluator_v2_source_qualification_hash") is None
        )
    if not status_valid:
        raise ContractError("held-out trace qualification completion eligibility differs")

    body = {
        "schema_version": QUALIFICATION_PROJECTION_SCHEMA_VERSION,
        "source_schema_version": "trace-qualification-v2",
        "run_id": result.run_id,
        "qualified": True,
        "trace_integrity_passed": True,
        "leakage_scan_passed": True,
        "evaluation_reached": qualification["evaluation_reached"],
        "outcome_kind": qualification["outcome_kind"],
        "purpose": "core",
        "experiment_id": HELDOUT_AC_SUITE_ID,
        "dataset_role": scheduled.role,
        "task_id": scheduled.task_id,
        "suite_hash": suite.content_hash,
        "execution_hash": execution_hash,
        "schedule_row_id": expected_row_id,
        "memory_condition": scheduled.condition,
        "source_evidence_hash": qualification["source_evidence_hash"],
        "source_qualification_hash": qualification_hash,
        "check_count": len(checks),
        "checks_hash": sha256_json(checks),
        "evaluator_version": "v2",
        "evaluator_v2_source_hash": qualification["evaluator_v2_source_hash"],
        "evaluator_v2_source_qualification_hash": qualification[
            "evaluator_v2_source_qualification_hash"
        ],
        "evaluator_v2_receipt_hash": qualification["evaluator_v2_receipt_hash"],
        "evaluator_v2_receipt_file_hash": qualification["evaluator_v2_receipt_file_hash"],
        "evaluator_v2_runtime_authenticated": qualification["evaluator_v2_runtime_authenticated"],
        "evaluator_v2_completion_eligible": qualification["evaluator_v2_completion_eligible"],
    }
    return HeldoutACAuthenticatedQualificationProjection(
        **body,
        content_hash=sha256_json(body),
    )


def project_authenticated_heldout_ac_persisted_row(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    expected_pricing_binding_hash: str,
    order: int,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    persisted_result_bytes: bytes,
    qualification_bytes: bytes,
    recomputed_qualification: Mapping[str, Any],
    usage_evidence_bytes: bytes,
    receipt_validation: EvaluatorV2ReceiptValidation | None,
    receipt_bytes: bytes | None,
) -> HeldoutACAuthenticatedPersistedRow:
    """Cross-bind exact bytes after trusted receipt and trace recomputation."""

    if type(order) is not int or not 1 <= order <= len(suite.schedule):
        raise ContractError("held-out persisted row order is invalid")
    scheduled = suite.schedule[order - 1]
    expected_row_id = heldout_ac_schedule_row_id(
        suite=suite,
        execution_hash=execution_hash,
        order=order,
    )
    try:
        result = RunResult.model_validate_json(persisted_result_bytes)
        qualification = json.loads(qualification_bytes)
        usage_evidence = HeldoutACPersistedUsageEvidence.model_validate_json(usage_evidence_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ContractError("held-out persisted row files are invalid") from exc
    if not isinstance(qualification, dict):
        raise ContractError("held-out trace qualification is not an object")
    if persisted_result_bytes != result.model_dump_json(indent=2).encode("utf-8"):
        raise ContractError("held-out persisted result bytes are not canonical")
    if qualification_bytes != _canonical_qualification_bytes(qualification):
        raise ContractError("held-out trace qualification bytes are not canonical")
    if usage_evidence_bytes != _canonical_usage_evidence_bytes(usage_evidence):
        raise ContractError("held-out usage evidence bytes are not canonical")
    if canonical_json(qualification) != canonical_json(dict(recomputed_qualification)):
        raise ContractError("held-out trace qualification differs from read-only recomputation")
    qualification_hash = _qualification_hash(qualification)
    qualification_projection = _project_authenticated_qualification(
        qualification=qualification,
        suite=suite,
        execution_hash=execution_hash,
        order=order,
        result=result,
        task_evaluator_binding=task_evaluator_binding,
        receipt_validation=receipt_validation,
    )
    experiment = receipt_validation.manifest.experiment if receipt_validation else None
    binding = result.evaluator_contract
    expected_task = task_evaluator_binding.task
    expected_usage = HeldoutACDurableUsage(**_usage_from_result(result))
    validate_heldout_ac_persisted_usage_cross_binding(
        result=result,
        usage_evidence=usage_evidence,
        expected_run_id=result.run_id,
        expected_schedule_row_id=expected_row_id,
        expected_pricing_binding_hash=expected_pricing_binding_hash,
        expected_qualification_hash=qualification_hash,
        expected_source_evidence_hash=str(qualification.get("source_evidence_hash")),
        expected_result_file_hash=sha256_bytes(persisted_result_bytes),
        expected_result_semantic_hash=sha256_json(result.model_dump(mode="json")),
        expected_receipt_file_hash=(
            sha256_bytes(receipt_bytes) if receipt_bytes is not None else None
        ),
    )
    common_valid = (
        expected_task.task_id == scheduled.task_id
        and result.run_id == usage_evidence.run_id
        and usage_evidence.schedule_row_id == expected_row_id
        and usage_evidence.qualification_hash == qualification_hash
        and usage_evidence.source_evidence_hash == qualification.get("source_evidence_hash")
        and usage_evidence.persisted_result_file_hash == sha256_bytes(persisted_result_bytes)
        and usage_evidence.pricing_binding_hash == expected_pricing_binding_hash
        and usage_evidence.usage == expected_usage
        and Decimal(str(result.usage.model_cost_usd))
        == Decimal(usage_evidence.token_derived_cost_nanos) / Decimal(1_000_000_000)
        and binding is not None
        and binding == task_evaluator_binding.evaluator_contract
        and qualification_projection.run_id == result.run_id
        and qualification_projection.source_qualification_hash == qualification_hash
    )
    receipt_hash: str | None = None
    receipt_file_hash: str | None = None
    if result.evaluation_status == "completed":
        if receipt_validation is None or receipt_bytes is None:
            raise ContractError("evaluator-completed held-out row lacks receipt validation")
        receipt = receipt_validation.receipt
        try:
            persisted_receipt = EvaluatorV2EvaluationReceipt.model_validate_json(receipt_bytes)
        except ValidationError as exc:
            raise ContractError("held-out evaluator receipt bytes are invalid") from exc
        receipt_hash = receipt.content_hash
        receipt_file_hash = sha256_bytes(receipt_bytes)
        common_valid = common_valid and (
            persisted_receipt == receipt
            and receipt_validation.result == result
            and receipt.run_id == result.run_id
            and receipt.suite_hash == suite.content_hash
            and receipt.result_file_hash == sha256_bytes(persisted_result_bytes)
            and receipt_file_hash == usage_evidence.evaluator_v2_receipt_file_hash
            and experiment is not None
            and experiment.experiment_id == suite.suite_id
            and experiment.suite_hash == suite.content_hash
            and experiment.execution_hash == execution_hash
            and experiment.schedule_order == order
            and experiment.schedule_row_id == expected_row_id
        )
    elif not (
        receipt_validation is None
        and receipt_bytes is None
        and usage_evidence.evaluator_v2_receipt_file_hash is None
        and result.evaluation_status == "not_run"
        and result.agent_submission_status == "failed"
        and result.outcome_kind.value == "agent_failure"
        and result.terminal_error == {"code": "AGENT_SUBMISSION_FAILED", "phase": "agent"}
    ):
        raise ContractError("held-out agent-terminal persisted evidence is invalid")
    if not common_valid:
        raise ContractError("held-out persisted row cross-binding differs")
    body = {
        "schema_version": ROW_SCHEMA_VERSION,
        "persisted_evidence_authenticated": True,
        "order": order,
        "wave": scheduled.wave,
        "task_id": scheduled.task_id,
        "role": scheduled.role,
        "condition": scheduled.condition,
        "repetition": scheduled.repetition,
        "run_id": result.run_id,
        "schedule_row_id": expected_row_id,
        "execution_hash": execution_hash,
        "task_evaluator_binding_hash": task_evaluator_binding.content_hash,
        "persisted_result_file_hash": sha256_bytes(persisted_result_bytes),
        "persisted_result_semantic_hash": sha256_json(result.model_dump(mode="json")),
        "qualification_file_hash": sha256_bytes(qualification_bytes),
        "qualification_hash": qualification_hash,
        "source_evidence_hash": qualification["source_evidence_hash"],
        "usage_evidence_file_hash": sha256_bytes(usage_evidence_bytes),
        "usage_evidence_hash": usage_evidence.content_hash,
        "evaluator_v2_receipt_hash": receipt_hash,
        "evaluator_v2_receipt_file_hash": receipt_file_hash,
        "result": result.model_dump(mode="json"),
        "usage_evidence": usage_evidence.model_dump(mode="json"),
    }
    return HeldoutACAuthenticatedPersistedRow(**body, content_hash=sha256_json(body))


def project_authenticated_heldout_ac_persisted_evidence(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    expected_pricing_binding_hash: str,
    order: int,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    persisted_result_bytes: bytes,
    qualification_bytes: bytes,
    recomputed_qualification: Mapping[str, Any],
    usage_evidence_bytes: bytes,
    receipt_validation: EvaluatorV2ReceiptValidation | None,
    receipt_bytes: bytes | None,
    evaluator_failure_event: RunEvent | None = None,
    agent_terminal_type: AgentTerminalType | None = None,
    agent_terminal_event: RunEvent | None = None,
) -> HeldoutACAuthenticatedPersistedEvidence | HeldoutACEvaluatorConfoundEvidence:
    """Project eligible evidence or a typed, authenticated evaluator confound.

    Stable failure codes are accepted only from a persisted ``RunFailed`` event.
    The raw event payload and exception message are deliberately not projected.
    """

    try:
        result = RunResult.model_validate_json(persisted_result_bytes)
        qualification = json.loads(qualification_bytes)
        usage_evidence = HeldoutACPersistedUsageEvidence.model_validate_json(usage_evidence_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ContractError("held-out persisted evidence files are invalid") from exc
    if not isinstance(qualification, dict):
        raise ContractError("held-out trace qualification is not an object")

    is_evaluator_confound = (
        result.schema_version == "run-result-v2"
        and result.agent_submission_status == "completed"
        and result.evaluation_status == "not_run"
        and result.outcome_kind is not None
        and result.outcome_kind.value == "infrastructure_error"
    )
    if not is_evaluator_confound:
        if evaluator_failure_event is not None:
            raise ContractError("eligible held-out row cannot carry evaluator confound evidence")
        if not (
            (result.evaluation_status == "completed")
            == (agent_terminal_type is None)
            == (agent_terminal_event is None)
        ):
            raise ContractError("eligible held-out row terminal classification differs")
        terminal_event_projection = (
            _project_agent_terminal_event(
                agent_terminal_event,
                terminal_type=agent_terminal_type,
            )
            if agent_terminal_event is not None and agent_terminal_type is not None
            else None
        )
        row = project_authenticated_heldout_ac_persisted_row(
            suite=suite,
            execution_hash=execution_hash,
            expected_pricing_binding_hash=expected_pricing_binding_hash,
            order=order,
            task_evaluator_binding=task_evaluator_binding,
            persisted_result_bytes=persisted_result_bytes,
            qualification_bytes=qualification_bytes,
            recomputed_qualification=recomputed_qualification,
            usage_evidence_bytes=usage_evidence_bytes,
            receipt_validation=receipt_validation,
            receipt_bytes=receipt_bytes,
        )
        projection = _project_authenticated_qualification(
            qualification=qualification,
            suite=suite,
            execution_hash=execution_hash,
            order=order,
            result=result,
            task_evaluator_binding=task_evaluator_binding,
            receipt_validation=receipt_validation,
        )
        body = {
            "schema_version": PERSISTED_EVIDENCE_SCHEMA_VERSION,
            "persisted_evidence_authenticated": True,
            "official": False,
            "analysis_eligible": False,
            "row": row.model_dump(mode="json"),
            "qualification": projection.model_dump(mode="json"),
            "terminal_type": agent_terminal_type,
            "terminal_event": (
                terminal_event_projection.model_dump(mode="json")
                if terminal_event_projection is not None
                else None
            ),
        }
        return HeldoutACAuthenticatedPersistedEvidence(
            **{
                **body,
                "terminal_event": terminal_event_projection,
            },
            content_hash=sha256_json(body),
        )

    if receipt_validation is not None or receipt_bytes is not None:
        raise ContractError("evaluator confound cannot carry completion receipt evidence")
    if agent_terminal_type is not None:
        raise ContractError("evaluator confound cannot carry an agent terminal classification")
    if agent_terminal_event is not None:
        raise ContractError("evaluator confound cannot carry an agent terminal event")
    if persisted_result_bytes != result.model_dump_json(indent=2).encode("utf-8"):
        raise ContractError("held-out persisted result bytes are not canonical")
    if qualification_bytes != _canonical_qualification_bytes(qualification):
        raise ContractError("held-out trace qualification bytes are not canonical")
    if usage_evidence_bytes != _canonical_usage_evidence_bytes(usage_evidence):
        raise ContractError("held-out usage evidence bytes are not canonical")
    if canonical_json(qualification) != canonical_json(dict(recomputed_qualification)):
        raise ContractError("held-out trace qualification differs from read-only recomputation")
    projection = _project_authenticated_qualification(
        qualification=qualification,
        suite=suite,
        execution_hash=execution_hash,
        order=order,
        result=result,
        task_evaluator_binding=task_evaluator_binding,
        receipt_validation=None,
    )
    if evaluator_failure_event is None:
        raise ContractError("post-submission evaluator confound lacks a persisted typed event")
    failure_code = evaluator_failure_event.payload.get("error_code")
    if not (
        evaluator_failure_event.run_id == result.run_id
        and evaluator_failure_event.type == EventType.RUN_FAILED
        and evaluator_failure_event.actor == "runner"
        and failure_code
        in {
            "EVALUATOR_CONTROL_CONTRACT_COLLISION",
            "UNTRUSTED_PRIVATE_MARKER_HIT",
        }
    ):
        raise ContractError("post-submission evaluator confound event is not trusted")

    scheduled = suite.schedule[order - 1]
    expected_row_id = heldout_ac_schedule_row_id(
        suite=suite,
        execution_hash=execution_hash,
        order=order,
    )
    binding = result.evaluator_contract
    expected_usage = HeldoutACDurableUsage(**_usage_from_result(result))
    validate_heldout_ac_persisted_usage_cross_binding(
        result=result,
        usage_evidence=usage_evidence,
        expected_run_id=result.run_id,
        expected_schedule_row_id=expected_row_id,
        expected_pricing_binding_hash=expected_pricing_binding_hash,
        expected_qualification_hash=projection.source_qualification_hash,
        expected_source_evidence_hash=projection.source_evidence_hash,
        expected_result_file_hash=sha256_bytes(persisted_result_bytes),
        expected_result_semantic_hash=sha256_json(result.model_dump(mode="json")),
        expected_receipt_file_hash=None,
    )
    common_valid = (
        task_evaluator_binding.task.task_id == scheduled.task_id
        and binding is not None
        and binding == task_evaluator_binding.evaluator_contract
        and usage_evidence.run_id == result.run_id
        and usage_evidence.schedule_row_id == expected_row_id
        and usage_evidence.qualification_hash == projection.source_qualification_hash
        and usage_evidence.source_evidence_hash == projection.source_evidence_hash
        and usage_evidence.persisted_result_file_hash == sha256_bytes(persisted_result_bytes)
        and usage_evidence.pricing_binding_hash == expected_pricing_binding_hash
        and usage_evidence.usage == expected_usage
        and usage_evidence.evaluator_v2_receipt_file_hash is None
        and Decimal(str(result.usage.model_cost_usd))
        == Decimal(usage_evidence.token_derived_cost_nanos) / Decimal(1_000_000_000)
    )
    if not common_valid:
        raise ContractError("held-out evaluator confound cross-binding differs")
    body = {
        "schema_version": EVALUATOR_CONFOUND_SCHEMA_VERSION,
        "persisted_evidence_authenticated": True,
        "analysis_eligible": False,
        "order": order,
        "wave": scheduled.wave,
        "task_id": scheduled.task_id,
        "role": scheduled.role,
        "condition": scheduled.condition,
        "repetition": scheduled.repetition,
        "run_id": result.run_id,
        "schedule_row_id": expected_row_id,
        "execution_hash": execution_hash,
        "task_evaluator_binding_hash": task_evaluator_binding.content_hash,
        "persisted_result_file_hash": sha256_bytes(persisted_result_bytes),
        "persisted_result_semantic_hash": sha256_json(result.model_dump(mode="json")),
        "qualification_file_hash": sha256_bytes(qualification_bytes),
        "qualification_hash": projection.source_qualification_hash,
        "source_evidence_hash": projection.source_evidence_hash,
        "usage_evidence_file_hash": sha256_bytes(usage_evidence_bytes),
        "usage_evidence_hash": usage_evidence.content_hash,
        "evaluator_failure_code": failure_code,
        "evaluator_failure_event_hash": sha256_json(
            {
                "event_id": evaluator_failure_event.event_id,
                "run_id": evaluator_failure_event.run_id,
                "sequence": evaluator_failure_event.sequence,
                "type": evaluator_failure_event.type.value,
                "timestamp": evaluator_failure_event.model_dump(mode="json")["timestamp"],
                "actor": evaluator_failure_event.actor,
                "error_code": failure_code,
            }
        ),
        "result": result.model_dump(mode="json"),
        "usage_evidence": usage_evidence.model_dump(mode="json"),
        "qualification": projection.model_dump(mode="json"),
    }
    return HeldoutACEvaluatorConfoundEvidence(**body, content_hash=sha256_json(body))


def authenticate_heldout_ac_persisted_row(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    expected_pricing_binding_hash: str,
    order: int,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    run_root: str | Path,
    task_dir: str | Path,
    dataset_manifest_path: str | Path,
    evaluator_authority: EvaluatorV2QualificationAuthority,
    usage_evidence_relative_path: str,
) -> HeldoutACAuthenticatedPersistedRow:
    """Invoke durable receipt/trace validators, then project one authenticated row.

    Calling this function is a future evaluator-side operation and is not
    authorized by importing or source-qualifying this module.
    """

    from patchloop.evals.qualification import load_trace_qualification, qualify_run
    from patchloop.task_loader import load_task_package

    root = Path(run_root).resolve()
    relative = safe_relative_path(
        usage_evidence_relative_path, field_name="held-out usage evidence path"
    )
    usage_path = (root / relative).resolve()
    if not usage_path.is_relative_to(root) or usage_path.is_symlink():
        raise ContractError("held-out usage evidence path escapes the runtime root")
    package: TaskPackage = load_task_package(task_dir)
    state = StateStore(root / "state.sqlite3")
    artifacts = ArtifactStore(root / "artifacts")
    scheduled = suite.schedule[order - 1]
    usage_bytes = usage_path.read_bytes()
    try:
        persisted_usage = HeldoutACPersistedUsageEvidence.model_validate_json(usage_bytes)
    except ValidationError as exc:
        raise ContractError("held-out usage evidence is invalid") from exc
    run_id = persisted_usage.run_id
    qualification = load_trace_qualification(run_id, root=root)
    recomputed = qualify_run(
        run_id,
        task_dir=task_dir,
        dataset_manifest_path=dataset_manifest_path,
        root=root,
        persist=False,
        evaluator_v2_authority=evaluator_authority,
    )
    run_dir = artifacts.root / "runs" / run_id
    persisted_result_bytes = (run_dir / "result.json").read_bytes()
    qualification_bytes = (root / "qualifications" / f"{run_id}.json").read_bytes()
    result = RunResult.model_validate_json(persisted_result_bytes)
    receipt_validation: EvaluatorV2ReceiptValidation | None = None
    receipt_bytes: bytes | None = None
    if result.evaluation_status == "completed":
        receipt_validation = validate_persisted_evaluator_v2_evaluation_receipt(
            state_store=state,
            artifact_store=artifacts,
            run_id=run_id,
            package=package,
            authority=evaluator_authority,
            expected_result=result,
        )
        receipt_bytes = (run_dir / "evaluation-receipt.json").read_bytes()
    if qualification != recomputed or scheduled.task_id != package.public.task_id:
        raise ContractError("held-out persisted validation task or qualification differs")
    return project_authenticated_heldout_ac_persisted_row(
        suite=suite,
        execution_hash=execution_hash,
        expected_pricing_binding_hash=expected_pricing_binding_hash,
        order=order,
        task_evaluator_binding=task_evaluator_binding,
        persisted_result_bytes=persisted_result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=recomputed,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=receipt_validation,
        receipt_bytes=receipt_bytes,
    )


def _load_and_project_heldout_ac_persisted_evidence(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    expected_pricing_binding_hash: str,
    order: int,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    run_root: str | Path,
    task_dir: str | Path,
    dataset_manifest_path: str | Path,
    evaluator_authority: EvaluatorV2QualificationAuthority,
    usage_evidence_relative_path: str,
) -> HeldoutACAuthenticatedPersistedEvidence | HeldoutACEvaluatorConfoundEvidence:
    """Load, recompute and project runtime evidence without issuing authority."""

    from patchloop.evals.qualification import load_trace_qualification, qualify_run
    from patchloop.task_loader import load_task_package

    root = Path(run_root).resolve()
    relative = safe_relative_path(
        usage_evidence_relative_path, field_name="held-out usage evidence path"
    )
    usage_path = (root / relative).resolve()
    if not usage_path.is_relative_to(root) or usage_path.is_symlink():
        raise ContractError("held-out usage evidence path escapes the runtime root")
    package: TaskPackage = load_task_package(task_dir)
    state = StateStore(root / "state.sqlite3")
    artifacts = ArtifactStore(root / "artifacts")
    scheduled = suite.schedule[order - 1]
    usage_bytes = usage_path.read_bytes()
    try:
        persisted_usage = HeldoutACPersistedUsageEvidence.model_validate_json(usage_bytes)
    except ValidationError as exc:
        raise ContractError("held-out usage evidence is invalid") from exc
    run_id = persisted_usage.run_id
    qualification = load_trace_qualification(run_id, root=root)
    recomputed = qualify_run(
        run_id,
        task_dir=task_dir,
        dataset_manifest_path=dataset_manifest_path,
        root=root,
        persist=False,
        evaluator_v2_authority=evaluator_authority,
    )
    run_dir = artifacts.root / "runs" / run_id
    persisted_result_bytes = (run_dir / "result.json").read_bytes()
    qualification_bytes = (root / "qualifications" / f"{run_id}.json").read_bytes()
    result = RunResult.model_validate_json(persisted_result_bytes)
    receipt_validation: EvaluatorV2ReceiptValidation | None = None
    receipt_bytes: bytes | None = None
    if result.evaluation_status == "completed":
        receipt_validation = validate_persisted_evaluator_v2_evaluation_receipt(
            state_store=state,
            artifact_store=artifacts,
            run_id=run_id,
            package=package,
            authority=evaluator_authority,
            expected_result=result,
        )
        receipt_bytes = (run_dir / "evaluation-receipt.json").read_bytes()
    run_events = state.list_events(run_id)
    failure_events = [event for event in run_events if event.type == EventType.RUN_FAILED]
    failure_event = (
        failure_events[0]
        if len(failure_events) == 1
        and result.agent_submission_status == "completed"
        and result.evaluation_status == "not_run"
        else None
    )
    terminal_mapping: dict[Any, AgentTerminalType] = {
        "exact_request_budget_exceeded": "token-budget-exhaustion",
        "model_call_budget_exhausted": "model-call-limit",
        "tool_call_budget_exhausted": "tool-call-limit",
        "wall_clock_budget_exhausted": "wall-clock-timeout",
    }
    terminal_type: AgentTerminalType | None = None
    terminal_event: RunEvent | None = None
    if result.agent_submission_status == "failed":
        terminal_type = "submission-failure"
        for event in reversed(run_events):
            if event.type == EventType.MODEL_GENERATION_BLOCKED:
                observed = terminal_mapping.get(event.payload.get("reason_code"))
                if observed is not None:
                    terminal_type = observed
                    terminal_event = event
                    break
        if terminal_event is None:
            if len(failure_events) != 1:
                raise ContractError("held-out agent terminal RunFailed event is not unique")
            terminal_event = failure_events[0]
    if qualification != recomputed or scheduled.task_id != package.public.task_id:
        raise ContractError("held-out persisted validation task or qualification differs")
    return project_authenticated_heldout_ac_persisted_evidence(
        suite=suite,
        execution_hash=execution_hash,
        expected_pricing_binding_hash=expected_pricing_binding_hash,
        order=order,
        task_evaluator_binding=task_evaluator_binding,
        persisted_result_bytes=persisted_result_bytes,
        qualification_bytes=qualification_bytes,
        recomputed_qualification=recomputed,
        usage_evidence_bytes=usage_bytes,
        receipt_validation=receipt_validation,
        receipt_bytes=receipt_bytes,
        evaluator_failure_event=failure_event,
        agent_terminal_type=terminal_type,
        agent_terminal_event=terminal_event,
    )


def authenticate_heldout_ac_persisted_evidence(
    *,
    suite: HeldoutACSuite,
    execution_hash: str,
    expected_pricing_binding_hash: str,
    order: int,
    task_evaluator_binding: HeldoutACTaskEvaluatorBinding,
    run_root: str | Path,
    task_dir: str | Path,
    dataset_manifest_path: str | Path,
    evaluator_authority: EvaluatorV2QualificationAuthority,
    usage_evidence_relative_path: str,
) -> HeldoutACAuthenticatedPersistedEvidence | HeldoutACEvaluatorConfoundEvidence:
    """Authenticate persisted evidence and issue capability only to eligible rows.

    The serializable DTO remains unofficial.  Only the exact in-memory eligible
    instance returned by this function can cross the official completion gate.
    Typed evaluator confounds remain durable non-analysis evidence.
    """

    projected = _load_and_project_heldout_ac_persisted_evidence(
        suite=suite,
        execution_hash=execution_hash,
        expected_pricing_binding_hash=expected_pricing_binding_hash,
        order=order,
        task_evaluator_binding=task_evaluator_binding,
        run_root=run_root,
        task_dir=task_dir,
        dataset_manifest_path=dataset_manifest_path,
        evaluator_authority=evaluator_authority,
        usage_evidence_relative_path=usage_evidence_relative_path,
    )
    if type(projected) is HeldoutACAuthenticatedPersistedEvidence:
        return _issue_runtime_authentication_capability(projected)
    return projected


__all__ = [
    "AGENT_TERMINAL_EVENT_PROJECTION_SCHEMA_VERSION",
    "EVALUATOR_CONFOUND_SCHEMA_VERSION",
    "HELDOUT_AC_PRICE_NANOS_PER_TOKEN",
    "PERSISTED_EVIDENCE_SCHEMA_VERSION",
    "QUALIFICATION_PROJECTION_SCHEMA_VERSION",
    "ROW_SCHEMA_VERSION",
    "USAGE_SCHEMA_VERSION",
    "EvaluatorFailureCode",
    "AgentTerminalType",
    "HeldoutACAgentTerminalEventProjection",
    "HeldoutACAuthenticatedPersistedEvidence",
    "HeldoutACAuthenticatedPersistedRow",
    "HeldoutACAuthenticatedQualificationProjection",
    "HeldoutACEvaluatorConfoundEvidence",
    "HeldoutACPersistedUsageEvidence",
    "authenticate_heldout_ac_persisted_evidence",
    "authenticate_heldout_ac_persisted_row",
    "has_heldout_ac_runtime_authentication_capability",
    "project_authenticated_heldout_ac_persisted_evidence",
    "project_authenticated_heldout_ac_persisted_row",
    "validate_heldout_ac_persisted_usage_cross_binding",
]
