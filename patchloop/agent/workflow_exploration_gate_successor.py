"""Offline public-evidence closure gate for a post-V18 workflow successor.

R14 showed two distinct exploration failures that read-count quotas cannot
detect: one plan admitted a mutation while retaining explicitly unresolved
questions, and another reused one broad source span as every causal boundary.
This module adds a task-generic, request-bound closure statement to the
already-qualified V18 causal-plan projection.

The contract is deliberately not activated by an existing runtime.  It does
not run tools, checks, evaluators, containers, or providers.  A later opt-in
activation may use the exact request and binding types defined here after this
successor passes its offline qualification.
"""

from __future__ import annotations

import copy
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    ActivatedCausalPlanRequest,
    CausalMechanismHistoryEntryV2,
    normalize_activated_causal_plan,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    CausalPlanModelInputV2,
    EligibleCausalSourceSpan,
    RecordedCausalPlanV2,
)
from patchloop.agent.workflow_successor_v2 import (
    EligiblePlanEvidenceCatalog,
    PlanTrigger,
    RecordedWorkPlanV2,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json

EXPLORATION_GATE_POLICY = "public-boundary-and-unknown-closure-v1"
EXPLORATION_REQUEST_SCHEMA = "exploration-gated-causal-plan-request-v1"
EXPLORATION_RECEIPT_SCHEMA = "public-exploration-closure-receipt-v1"
EXPLORATION_BINDING_SCHEMA = "exploration-work-plan-binding-v1"

SourceSpanId = Annotated[str, Field(pattern=r"^cspan:[1-9][0-9]*:[0-9]+$")]
Hash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _reject(reason_code: str, message: str) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


def _normalized_public_text(value: str, *, field_name: str) -> str:
    if not value or value != value.strip() or "\x00" in value:
        raise ValueError(f"{field_name} must be trimmed public text")
    return value


class ExplorationBoundaryCoverageInput(BaseModel):
    """Model-selected current-source coverage for three generic causal roles."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    ownership_boundary_span_ids: list[SourceSpanId] = Field(min_length=1, max_length=4)
    execution_boundary_span_ids: list[SourceSpanId] = Field(min_length=1, max_length=4)
    mutation_boundary_span_ids: list[SourceSpanId] = Field(min_length=1, max_length=4)


class ExplorationInvariantInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    subject: str = Field(min_length=1, max_length=500)
    claim: str = Field(min_length=1, max_length=1_500)
    evidence_source_span_ids: list[SourceSpanId] = Field(min_length=1, max_length=6)

    @field_validator("subject", "claim")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalized_public_text(value, field_name="exploration invariant")


class PreservationObligationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    public_requirement: str = Field(min_length=1, max_length=1_500)
    expected_behavior: str = Field(min_length=1, max_length=1_500)
    evidence_source_span_ids: list[SourceSpanId] = Field(min_length=1, max_length=6)

    @field_validator("public_requirement", "expected_behavior")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalized_public_text(value, field_name="preservation obligation")


class UnknownDispositionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    question: str = Field(min_length=1, max_length=1_000)
    disposition: Literal["resolved", "non_blocking"]
    explanation: str = Field(min_length=1, max_length=1_500)
    evidence_source_span_ids: list[SourceSpanId] = Field(min_length=1, max_length=6)

    @field_validator("question", "explanation")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalized_public_text(value, field_name="unknown disposition")


class ExplorationStateInput(BaseModel):
    """The model-owned closure statement required immediately before mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    boundary_coverage: ExplorationBoundaryCoverageInput
    invariants: list[ExplorationInvariantInput] = Field(min_length=1, max_length=8)
    preservation_obligations: list[PreservationObligationInput] = Field(min_length=1, max_length=8)
    unknown_dispositions: list[UnknownDispositionInput] = Field(max_length=20)
    open_blocking_unknowns: list[str] = Field(max_length=20)

    @field_validator("open_blocking_unknowns")
    @classmethod
    def normalize_blockers(cls, values: list[str]) -> list[str]:
        if any(
            not value or value != value.strip() or "\x00" in value or len(value) > 1_000
            for value in values
        ):
            raise ValueError("open blocking unknowns differ")
        return values


class ExplorationCausalPlanInput(CausalPlanModelInputV2):
    """V18 model-owned plan plus one generic public exploration statement."""

    exploration_state: ExplorationStateInput


class ExplorationGatedCausalPlanRequest(BaseModel):
    """Exact dynamic schema delivered by a future opt-in runtime."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["exploration-gated-causal-plan-request-v1"]
    policy_version: Literal["public-boundary-and-unknown-closure-v1"]
    base_request: ActivatedCausalPlanRequest
    base_request_hash: Hash
    parameters: dict[str, Any]
    parameter_schema_hash: Hash
    minimum_distinct_source_coverage_keys: Literal[2]
    mutation_boundary_must_bind_candidate_and_mechanism: Literal[True]
    declared_unknowns_require_disposition: Literal[True]
    open_blocking_unknowns_allowed: Literal[False]
    runtime_surface_activated: Literal[False]
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        properties = self.parameters.get("properties", {})
        required = self.parameters.get("required", [])
        if (
            self.base_request_hash != self.base_request.content_hash
            or "exploration_state" not in properties
            or "exploration_state" not in required
            or self.parameter_schema_hash != sha256_json(self.parameters)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("exploration-gated request differs")
        return self


class PublicExplorationClosureReceipt(BaseModel):
    """Server-resolved, current-diff closure evidence for one projected plan."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-exploration-closure-receipt-v1"]
    policy_version: Literal["public-boundary-and-unknown-closure-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: Hash
    projected_plan_hash: Hash
    request_projection_hash: Hash
    source_span_catalog_hash: Hash
    exploration_state: ExplorationStateInput
    selected_source_spans: tuple[EligibleCausalSourceSpan, ...] = Field(min_length=2)
    selected_source_coverage_keys: tuple[Hash, ...] = Field(min_length=2)
    public_current_diff_source_only: Literal[True]
    declared_unknowns_closed: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        expected_keys = tuple(
            dict.fromkeys(item.coverage_key for item in self.selected_source_spans)
        )
        if (
            len(expected_keys) < 2
            or self.selected_source_coverage_keys != expected_keys
            or any(
                item.run_id != self.run_id or item.worktree_diff_hash != self.worktree_diff_hash
                for item in self.selected_source_spans
            )
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("public exploration closure receipt differs")
        return self


class ExplorationWorkPlanBinding(BaseModel):
    """Durable companion binding between an active plan and closure receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["exploration-work-plan-binding-v1"]
    policy_version: Literal["public-boundary-and-unknown-closure-v1"]
    run_id: str = Field(min_length=1)
    plan_hash: Hash
    plan_event_sequence: int = Field(ge=1)
    revision_index: int = Field(ge=0, le=3)
    parent_plan_hash: Hash | None
    trigger: PlanTrigger
    receipt: PublicExplorationClosureReceipt
    receipt_hash: Hash
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: Hash

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        initial_valid = (
            self.parent_plan_hash is None and self.trigger == "initial"
            if self.revision_index == 0
            else self.parent_plan_hash is not None and self.trigger != "initial"
        )
        if (
            not initial_valid
            or self.receipt_hash != self.receipt.content_hash
            or self.receipt.run_id != self.run_id
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("exploration work-plan binding differs")
        return self


def _span_array_schema(span_ids: list[str], *, max_items: int = 6) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": max_items,
        "items": {"type": "string", "enum": span_ids},
    }


def _exploration_state_schema(span_ids: list[str]) -> dict[str, Any]:
    invariant = {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "minLength": 1, "maxLength": 500},
            "claim": {"type": "string", "minLength": 1, "maxLength": 1_500},
            "evidence_source_span_ids": _span_array_schema(span_ids),
        },
        "required": ["subject", "claim", "evidence_source_span_ids"],
        "additionalProperties": False,
    }
    preservation = {
        "type": "object",
        "properties": {
            "public_requirement": {"type": "string", "minLength": 1, "maxLength": 1_500},
            "expected_behavior": {"type": "string", "minLength": 1, "maxLength": 1_500},
            "evidence_source_span_ids": _span_array_schema(span_ids),
        },
        "required": [
            "public_requirement",
            "expected_behavior",
            "evidence_source_span_ids",
        ],
        "additionalProperties": False,
    }
    disposition = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "minLength": 1, "maxLength": 1_000},
            "disposition": {"type": "string", "enum": ["resolved", "non_blocking"]},
            "explanation": {"type": "string", "minLength": 1, "maxLength": 1_500},
            "evidence_source_span_ids": _span_array_schema(span_ids),
        },
        "required": [
            "question",
            "disposition",
            "explanation",
            "evidence_source_span_ids",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "boundary_coverage": {
                "type": "object",
                "properties": {
                    "ownership_boundary_span_ids": _span_array_schema(span_ids, max_items=4),
                    "execution_boundary_span_ids": _span_array_schema(span_ids, max_items=4),
                    "mutation_boundary_span_ids": _span_array_schema(span_ids, max_items=4),
                },
                "required": [
                    "ownership_boundary_span_ids",
                    "execution_boundary_span_ids",
                    "mutation_boundary_span_ids",
                ],
                "additionalProperties": False,
            },
            "invariants": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": invariant,
            },
            "preservation_obligations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": preservation,
            },
            "unknown_dispositions": {
                "type": "array",
                "maxItems": 20,
                "items": disposition,
            },
            "open_blocking_unknowns": {
                "type": "array",
                "maxItems": 0,
                "items": {"type": "string", "minLength": 1, "maxLength": 1_000},
                "description": (
                    "Must be empty. Gather another public search/read result before "
                    "recording a plan when a mutation-relevant question remains open."
                ),
            },
        },
        "required": [
            "boundary_coverage",
            "invariants",
            "preservation_obligations",
            "unknown_dispositions",
            "open_blocking_unknowns",
        ],
        "additionalProperties": False,
    }


def project_exploration_gated_causal_plan_request(
    base_request: ActivatedCausalPlanRequest,
) -> ExplorationGatedCausalPlanRequest:
    """Add finite public exploration closure fields to one exact V18 request."""

    parameters = copy.deepcopy(base_request.parameters)
    properties = parameters.get("properties")
    required = parameters.get("required")
    spans = base_request.source_projection.source_span_catalog.spans
    span_ids = [item.source_span_id for item in spans]
    if (
        not isinstance(properties, dict)
        or not isinstance(required, list)
        or "exploration_state" in properties
        or "exploration_state" in required
        or not span_ids
    ):
        raise RecoveryError("base causal-plan request cannot accept exploration closure")
    properties["exploration_state"] = _exploration_state_schema(span_ids)
    required.append("exploration_state")
    body = {
        "schema_version": EXPLORATION_REQUEST_SCHEMA,
        "policy_version": EXPLORATION_GATE_POLICY,
        "base_request": base_request.model_dump(mode="python"),
        "base_request_hash": base_request.content_hash,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
        "minimum_distinct_source_coverage_keys": 2,
        "mutation_boundary_must_bind_candidate_and_mechanism": True,
        "declared_unknowns_require_disposition": True,
        "open_blocking_unknowns_allowed": False,
        "runtime_surface_activated": False,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(ExplorationGatedCausalPlanRequest, body)


def _input_span_ids(state: ExplorationStateInput) -> tuple[str, ...]:
    coverage = state.boundary_coverage
    values: list[str] = [
        *coverage.ownership_boundary_span_ids,
        *coverage.execution_boundary_span_ids,
        *coverage.mutation_boundary_span_ids,
    ]
    for item in state.invariants:
        values.extend(item.evidence_source_span_ids)
    for item in state.preservation_obligations:
        values.extend(item.evidence_source_span_ids)
    for item in state.unknown_dispositions:
        values.extend(item.evidence_source_span_ids)
    return tuple(dict.fromkeys(values))


def normalize_exploration_gated_causal_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    request_projection: ExplorationGatedCausalPlanRequest,
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> tuple[RecordedCausalPlanV2, PublicExplorationClosureReceipt]:
    """Normalize the V18 plan, then fail closed on unresolved exploration."""

    exact = project_exploration_gated_causal_plan_request(request_projection.base_request)
    if request_projection != exact:
        raise RecoveryError("exploration-gated causal-plan request differs")
    try:
        submitted = ExplorationCausalPlanInput.model_validate(raw_arguments)
    except ValueError as exc:
        _reject("exploration_plan_input_shape_invalid", "exploration plan input differs")
        raise AssertionError from exc
    state = submitted.exploration_state
    if state.open_blocking_unknowns:
        _reject(
            "exploration_blocking_unknowns_open",
            "mutation-relevant public questions remain unresolved",
        )
    questions = tuple(item.question for item in state.unknown_dispositions)
    if len(questions) != len(set(questions)) or questions != tuple(submitted.unknowns):
        _reject(
            "exploration_unknown_disposition_mismatch",
            "each declared plan unknown requires one ordered disposition",
        )
    base_arguments = submitted.model_dump(mode="python", exclude={"exploration_state"})
    projected = normalize_activated_causal_plan(
        task=task,
        catalog=catalog,
        request_projection=request_projection.base_request,
        trigger=trigger,
        revision_index=revision_index,
        parent_plan_hash=parent_plan_hash,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        raw_arguments=base_arguments,
    )
    span_by_id = {
        item.source_span_id: item
        for item in request_projection.base_request.source_projection.source_span_catalog.spans
    }
    selected_ids = _input_span_ids(state)
    if any(span_id not in span_by_id for span_id in selected_ids):
        _reject(
            "exploration_source_span_ineligible",
            "exploration statement cites a source span outside the current request",
        )
    selected = tuple(span_by_id[span_id] for span_id in selected_ids)
    mechanism_ids = {
        item.source_span.source_span_id for item in projected.causal_mechanism.causal_path
    }
    boundary = state.boundary_coverage
    boundary_ids = {
        *boundary.ownership_boundary_span_ids,
        *boundary.execution_boundary_span_ids,
        *boundary.mutation_boundary_span_ids,
    }
    boundary_coverage_keys = tuple(
        dict.fromkeys(span_by_id[span_id].coverage_key for span_id in boundary_ids)
    )
    if len(boundary_coverage_keys) < 2:
        _reject(
            "exploration_boundary_coverage_insufficient",
            "ownership, execution, and mutation need two distinct public source ranges",
        )
    if not boundary_ids.issubset(mechanism_ids):
        _reject(
            "exploration_boundary_outside_mechanism",
            "exploration boundaries must be represented by the causal mechanism",
        )
    mutation_ids = set(boundary.mutation_boundary_span_ids)
    candidate_ids = {item.source_span_id for item in projected.candidate_source_spans}
    mechanism_mutation_id = projected.causal_mechanism.causal_path[-1].source_span.source_span_id
    if mechanism_mutation_id not in mutation_ids or not mutation_ids.intersection(candidate_ids):
        _reject(
            "exploration_mutation_boundary_unbound",
            "mutation coverage must bind the selected candidate and mechanism mutation site",
        )
    body = {
        "schema_version": EXPLORATION_RECEIPT_SCHEMA,
        "policy_version": EXPLORATION_GATE_POLICY,
        "run_id": projected.run_id,
        "worktree_diff_hash": projected.worktree_diff_hash,
        "projected_plan_hash": projected.content_hash,
        "request_projection_hash": request_projection.content_hash,
        "source_span_catalog_hash": (
            request_projection.base_request.source_projection.source_span_catalog.content_hash
        ),
        "exploration_state": state.model_dump(mode="python"),
        "selected_source_spans": tuple(item.model_dump(mode="python") for item in selected),
        "selected_source_coverage_keys": tuple(
            dict.fromkeys(item.coverage_key for item in selected)
        ),
        "public_current_diff_source_only": True,
        "declared_unknowns_closed": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return projected, _hashed(PublicExplorationClosureReceipt, body)


def build_exploration_work_plan_binding(
    *,
    plan: RecordedWorkPlanV2,
    plan_event_sequence: int,
    projected: RecordedCausalPlanV2,
    receipt: PublicExplorationClosureReceipt,
) -> ExplorationWorkPlanBinding:
    """Bind one durable active plan to its exact public closure receipt."""

    if (
        receipt.run_id != plan.run_id
        or receipt.worktree_diff_hash != plan.worktree_diff_hash
        or receipt.projected_plan_hash != projected.content_hash
        or receipt.source_span_catalog_hash != projected.source_span_catalog_hash
        or projected.run_id != plan.run_id
        or projected.worktree_diff_hash != plan.worktree_diff_hash
        or projected.revision_index != plan.revision_index
        or projected.parent_plan_hash != plan.parent_plan_hash
        or projected.trigger != plan.trigger
    ):
        raise ContractError("exploration closure does not bind the active plan")
    body = {
        "schema_version": EXPLORATION_BINDING_SCHEMA,
        "policy_version": EXPLORATION_GATE_POLICY,
        "run_id": plan.run_id,
        "plan_hash": plan.content_hash,
        "plan_event_sequence": plan_event_sequence,
        "revision_index": plan.revision_index,
        "parent_plan_hash": plan.parent_plan_hash,
        "trigger": plan.trigger,
        "receipt": receipt.model_dump(mode="python"),
        "receipt_hash": receipt.content_hash,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(ExplorationWorkPlanBinding, body)


__all__ = [
    "EXPLORATION_BINDING_SCHEMA",
    "EXPLORATION_GATE_POLICY",
    "EXPLORATION_RECEIPT_SCHEMA",
    "EXPLORATION_REQUEST_SCHEMA",
    "ExplorationCausalPlanInput",
    "ExplorationGatedCausalPlanRequest",
    "ExplorationStateInput",
    "ExplorationWorkPlanBinding",
    "PublicExplorationClosureReceipt",
    "build_exploration_work_plan_binding",
    "normalize_exploration_gated_causal_plan",
    "project_exploration_gated_causal_plan_request",
]
