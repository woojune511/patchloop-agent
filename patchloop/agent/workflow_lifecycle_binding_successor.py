"""Offline opt-in lifecycle component binding and exact relation feedback.

The V1 lifecycle request repeated free-form component labels across owners,
states, and transitions.  This successor defines each component once and uses
integer references from transitions.  It validates only public provenance and
structural relations; visible checks still decide semantic correctness.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.context_event_compaction import (
    CompactedEventContext,
    validate_lean_context_event_compaction,
)
from patchloop.agent.workflow_causal_alternative_activation import CrossResetFailureTrigger
from patchloop.agent.workflow_causal_plan_projection_activation import (
    CausalMechanismHistoryEntryV2,
    RecordedCausalPlanV2,
)
from patchloop.agent.workflow_plan_admission_feedback_successor import (
    _validate_source_details,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    TriggerBoundSelfDirectedPlanRequest,
    normalize_trigger_bound_self_directed_plan,
    project_trigger_bound_self_directed_tool_surface,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SELF_DIRECTED_EXPLORATION_POLICY,
    EligiblePlanEvidenceCatalogV4,
    SelfDirectedExplorationClosureReceipt,
    SelfDirectedExplorationState,
    WorkflowDecisionV4,
    workflow_instruction_v8,
)
from patchloop.agent.workflow_successor_v2 import WorkflowToolSurfaceV2
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json, sha256_text

LIFECYCLE_COMPONENT_BINDING_POLICY = "public-lifecycle-component-binding-plan-v2"
LIFECYCLE_COMPONENT_REQUEST_SCHEMA = "lifecycle-component-bound-self-directed-plan-request-v2"
LIFECYCLE_COMPONENT_RECORD_SCHEMA = "public-lifecycle-component-binding-v2"
LIFECYCLE_RELATION_MISMATCH_SCHEMA = "public-lifecycle-relation-mismatch-v1"
PLAN_ADMISSION_FEEDBACK_POLICY_V3 = "bounded-plan-admission-feedback-v3"
COMPACT_FEEDBACK_SCHEMA_V3 = "compact-plan-admission-feedback-v3"
COMPACT_FEEDBACK_EVIDENCE_SCHEMA_V3 = "compact-plan-admission-feedback-evidence-v3"
MAX_PLAN_FEEDBACK_BYTES_V3 = 14_000


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _public_text(value: str, *, field: str) -> str:
    if not value or value != value.strip() or "\x00" in value:
        raise ValueError(f"{field} must be bounded trimmed public text")
    return value


class LifecycleComponentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1, max_length=200)
    owner_source_span_id: str = Field(pattern=r"^cspan:[1-9][0-9]*:[0-9]+$")
    responsibility: str = Field(min_length=1, max_length=1_000)
    before: str = Field(min_length=1, max_length=500)
    after: str = Field(min_length=1, max_length=500)

    @field_validator("name", "responsibility", "before", "after")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _public_text(value, field="lifecycle component")


class LifecycleTransitionReferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    trigger: str = Field(min_length=1, max_length=500)
    affected_component_indices: tuple[int, ...] = Field(min_length=1, max_length=8)
    evidence_source_span_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    atomic: Literal[True]

    @field_validator("trigger")
    @classmethod
    def normalize_trigger(cls, value: str) -> str:
        return _public_text(value, field="lifecycle transition")


class LifecycleAtomicPostconditionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    condition: str = Field(min_length=1, max_length=1_000)
    evidence_source_span_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    falsification_observation: str = Field(min_length=1, max_length=1_000)

    @field_validator("condition", "falsification_observation")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _public_text(value, field="lifecycle postcondition")


class LifecycleComponentBindingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    components: tuple[LifecycleComponentInput, ...] = Field(min_length=1, max_length=8)
    transitions: tuple[LifecycleTransitionReferenceInput, ...] = Field(min_length=1, max_length=8)
    atomic_postconditions: tuple[LifecycleAtomicPostconditionInput, ...] = Field(
        min_length=1, max_length=8
    )


class LifecycleComponentBoundPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lifecycle-component-bound-self-directed-plan-request-v2"]
    policy_version: Literal["public-lifecycle-component-binding-plan-v2"]
    source_request: TriggerBoundSelfDirectedPlanRequest
    source_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parameters: dict[str, Any]
    parameter_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_evidence_only: Literal[True]
    semantic_truth_verified: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        if (
            self.source_request_hash != self.source_request.content_hash
            or self.parameter_schema_hash != sha256_json(self.parameters)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("lifecycle component request binding differs")
        return self


class ComponentNameCollision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1, max_length=200)
    component_indices: tuple[int, ...] = Field(min_length=2, max_length=8)


class TransitionReferenceViolation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    transition_index: int = Field(ge=0, le=7)
    duplicate_component_indices: tuple[int, ...] = Field(max_length=8)
    out_of_range_component_indices: tuple[int, ...] = Field(max_length=8)

    @model_validator(mode="after")
    def validate_violation(self) -> Self:
        if not self.duplicate_component_indices and not self.out_of_range_component_indices:
            raise ValueError("empty transition relation violation")
        return self


class LifecycleRelationMismatch(BaseModel):
    """Exact public structural mismatch returned after admission rejection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-lifecycle-relation-mismatch-v1"]
    policy_version: Literal["public-lifecycle-component-binding-plan-v2"]
    component_count: int = Field(ge=1, le=8)
    component_name_collisions: tuple[ComponentNameCollision, ...]
    unchanged_state_component_indices: tuple[int, ...] = Field(max_length=8)
    transition_reference_violations: tuple[TransitionReferenceViolation, ...]
    unknown_evidence_source_span_ids: tuple[str, ...] = Field(max_length=24)
    owner_source_span_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    mutation_site_span_id: str | None = Field(default=None, pattern=r"^cspan:[1-9][0-9]*:[0-9]+$")
    mutation_owner_missing: bool
    public_current_diff_source_only: Literal[True]
    semantic_truth_verified: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_mismatch(self) -> Self:
        structural = bool(
            self.component_name_collisions
            or self.unchanged_state_component_indices
            or self.transition_reference_violations
            or self.unknown_evidence_source_span_ids
        )
        if self.mutation_owner_missing is not (self.mutation_site_span_id is not None):
            raise ValueError("lifecycle mutation mismatch binding differs")
        if not structural and not self.mutation_owner_missing:
            raise ValueError("lifecycle relation mismatch is empty")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("lifecycle relation mismatch hash differs")
        return self


class RecordedLifecycleComponentBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-lifecycle-component-binding-v2"]
    policy_version: Literal["public-lifecycle-component-binding-plan-v2"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    lifecycle: LifecycleComponentBindingInput
    cited_source_span_ids: tuple[str, ...] = Field(min_length=1)
    mutation_site_span_id: str = Field(pattern=r"^cspan:[1-9][0-9]*:[0-9]+$")
    mutation_owner_component_index: int = Field(ge=0, le=7)
    public_current_diff_source_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.mutation_owner_component_index >= len(self.lifecycle.components):
            raise ValueError("lifecycle mutation owner index differs")
        if self.lifecycle.components[
            self.mutation_owner_component_index
        ].owner_source_span_id != self.mutation_site_span_id or self.content_hash != sha256_json(
            self.model_dump(mode="json", exclude={"content_hash"})
        ):
            raise ValueError("lifecycle component record binding differs")
        return self


def _lifecycle_component_schema(span_ids: list[str]) -> dict[str, Any]:
    span = {"type": "string", "enum": span_ids}
    return {
        "type": "object",
        "properties": {
            "components": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1, "maxLength": 200},
                        "owner_source_span_id": span,
                        "responsibility": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 1000,
                        },
                        "before": {"type": "string", "minLength": 1, "maxLength": 500},
                        "after": {"type": "string", "minLength": 1, "maxLength": 500},
                    },
                    "required": [
                        "name",
                        "owner_source_span_id",
                        "responsibility",
                        "before",
                        "after",
                    ],
                    "additionalProperties": False,
                },
            },
            "transitions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "trigger": {"type": "string", "minLength": 1, "maxLength": 500},
                        "affected_component_indices": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": {"type": "integer", "minimum": 0, "maximum": 7},
                        },
                        "evidence_source_span_ids": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": span,
                        },
                        "atomic": {"type": "boolean", "enum": [True]},
                    },
                    "required": [
                        "trigger",
                        "affected_component_indices",
                        "evidence_source_span_ids",
                        "atomic",
                    ],
                    "additionalProperties": False,
                },
            },
            "atomic_postconditions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "condition": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 1000,
                        },
                        "evidence_source_span_ids": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": span,
                        },
                        "falsification_observation": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 1000,
                        },
                    },
                    "required": [
                        "condition",
                        "evidence_source_span_ids",
                        "falsification_observation",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["components", "transitions", "atomic_postconditions"],
        "additionalProperties": False,
    }


def project_lifecycle_component_bound_plan_request(
    source: TriggerBoundSelfDirectedPlanRequest,
) -> LifecycleComponentBoundPlanRequest:
    parameters = copy.deepcopy(source.parameters)
    properties = parameters.get("properties")
    required = parameters.get("required")
    spans = source.source_request.base_request.source_projection.source_span_catalog.spans
    if not isinstance(properties, dict) or not isinstance(required, list) or not spans:
        raise RecoveryError("lifecycle component predecessor request differs")
    span_ids = [item.source_span_id for item in spans]
    properties["lifecycle_component_binding"] = _lifecycle_component_schema(span_ids)
    required.append("lifecycle_component_binding")
    body = {
        "schema_version": LIFECYCLE_COMPONENT_REQUEST_SCHEMA,
        "policy_version": LIFECYCLE_COMPONENT_BINDING_POLICY,
        "source_request": source.model_dump(mode="python"),
        "source_request_hash": source.content_hash,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
        "public_evidence_only": True,
        "semantic_truth_verified": False,
    }
    return _hashed(LifecycleComponentBoundPlanRequest, body)


def project_lifecycle_component_bound_tool_surface(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV4,
    catalog: EligiblePlanEvidenceCatalogV4,
    state: SelfDirectedExplorationState | None,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[WorkflowToolSurfaceV2, LifecycleComponentBoundPlanRequest | None]:
    surface, source_request = project_trigger_bound_self_directed_tool_surface(
        task=task,
        decision=decision,
        catalog=catalog,
        state=state,
        source_tool_schemas=source_tool_schemas,
        cross_reset_trigger=cross_reset_trigger,
    )
    request = (
        project_lifecycle_component_bound_plan_request(source_request)
        if source_request is not None
        else None
    )
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    for schema in selected:
        if schema.get("name") in {"record_work_plan", "revise_work_plan"}:
            if request is None:
                raise RecoveryError("lifecycle component surface lacks its request")
            schema["parameters"] = copy.deepcopy(request.parameters)
            schema["description"] = (
                "Define lifecycle components once, reference them by array index, and record "
                "falsifiable atomic postconditions before mutation."
            )
    body = {
        **surface.model_dump(
            mode="python",
            exclude={"content_hash", "selected_tool_schema_hash"},
        ),
        "selected_tool_schemas": tuple(selected),
        "selected_tool_schema_hash": sha256_json(selected),
    }
    return _hashed(WorkflowToolSurfaceV2, body), request


def lifecycle_component_workflow_instruction(
    decision: WorkflowDecisionV4,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV4,
    active_work_state: Any,
    semantic_progress_state: Any,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    request_projection: LifecycleComponentBoundPlanRequest | None,
    readiness: Any,
    recovered_pin: Any,
    self_directed_state: SelfDirectedExplorationState | None,
) -> dict[str, Any]:
    source_request = request_projection.source_request if request_projection is not None else None
    source = workflow_instruction_v8(
        decision,
        public_task_spec=public_task_spec,
        catalog=catalog,
        active_work_state=active_work_state,
        semantic_progress_state=semantic_progress_state,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        request_projection=source_request,
        readiness=readiness,
        recovered_pin=recovered_pin,
        self_directed_state=self_directed_state,
    )
    body = {
        **{key: value for key, value in source.items() if key != "content_hash"},
        "lifecycle_plan_policy_version": LIFECYCLE_COMPONENT_BINDING_POLICY,
        "activated_exploration_plan_request": (
            request_projection.model_dump(mode="json") if request_projection is not None else None
        ),
        "activated_exploration_plan_request_hash": (
            request_projection.content_hash if request_projection is not None else sha256_json(None)
        ),
    }
    if request_projection is not None:
        body["instruction"] = (
            "Define each public lifecycle component once. Use zero-based component indices "
            "for transitions, then state the falsifiable atomic postconditions before mutation."
        )
    return {**body, "content_hash": sha256_json(body)}


def _build_relation_mismatch(
    *,
    lifecycle: LifecycleComponentBindingInput,
    span_ids: set[str],
    mutation_site_span_id: str | None = None,
) -> LifecycleRelationMismatch | None:
    name_indices: dict[str, list[int]] = {}
    for index, component in enumerate(lifecycle.components):
        name_indices.setdefault(component.name, []).append(index)
    collisions = tuple(
        {"name": name, "component_indices": tuple(indices)}
        for name, indices in sorted(name_indices.items())
        if len(indices) > 1
    )
    unchanged = tuple(
        index
        for index, component in enumerate(lifecycle.components)
        if component.before == component.after
    )
    violations = []
    for index, transition in enumerate(lifecycle.transitions):
        counts = {
            value: transition.affected_component_indices.count(value)
            for value in transition.affected_component_indices
        }
        duplicates = tuple(sorted(value for value, count in counts.items() if count > 1))
        outside = tuple(
            sorted(
                {
                    value
                    for value in transition.affected_component_indices
                    if value < 0 or value >= len(lifecycle.components)
                }
            )
        )
        if duplicates or outside:
            violations.append(
                {
                    "transition_index": index,
                    "duplicate_component_indices": duplicates,
                    "out_of_range_component_indices": outside,
                }
            )
    cited = {
        *(component.owner_source_span_id for component in lifecycle.components),
        *(
            span_id
            for transition in lifecycle.transitions
            for span_id in transition.evidence_source_span_ids
        ),
        *(
            span_id
            for postcondition in lifecycle.atomic_postconditions
            for span_id in postcondition.evidence_source_span_ids
        ),
    }
    unknown = tuple(sorted(cited - span_ids))
    owner_spans = tuple(component.owner_source_span_id for component in lifecycle.components)
    mutation_missing = (
        mutation_site_span_id is not None and mutation_site_span_id not in owner_spans
    )
    if not (collisions or unchanged or violations or unknown or mutation_missing):
        return None
    body = {
        "schema_version": LIFECYCLE_RELATION_MISMATCH_SCHEMA,
        "policy_version": LIFECYCLE_COMPONENT_BINDING_POLICY,
        "component_count": len(lifecycle.components),
        "component_name_collisions": collisions,
        "unchanged_state_component_indices": unchanged,
        "transition_reference_violations": tuple(violations),
        "unknown_evidence_source_span_ids": unknown,
        "owner_source_span_ids": owner_spans,
        "mutation_site_span_id": mutation_site_span_id if mutation_missing else None,
        "mutation_owner_missing": mutation_missing,
        "public_current_diff_source_only": True,
        "semantic_truth_verified": False,
    }
    return _hashed(LifecycleRelationMismatch, body)


def _raise_relation_mismatch(mismatch: LifecycleRelationMismatch) -> None:
    raise ContractError(
        "lifecycle component relations differ",
        details={
            "reason_codes": ["lifecycle_component_relation_invalid"],
            "lifecycle_relation_mismatch": mismatch.model_dump(mode="json"),
        },
    )


def normalize_lifecycle_component_bound_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalogV4,
    request_projection: LifecycleComponentBoundPlanRequest,
    trigger: str,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> tuple[
    RecordedCausalPlanV2,
    SelfDirectedExplorationClosureReceipt,
    RecordedLifecycleComponentBinding,
]:
    exact = project_lifecycle_component_bound_plan_request(request_projection.source_request)
    if request_projection != exact or set(raw_arguments) != set(
        request_projection.parameters.get("required", [])
    ):
        raise RecoveryError("lifecycle component request binding differs")
    try:
        lifecycle = LifecycleComponentBindingInput.model_validate_json(
            canonical_json(raw_arguments.get("lifecycle_component_binding"))
        )
    except ValueError as exc:
        raise ContractError(
            "lifecycle component input differs",
            details={"reason_codes": ["lifecycle_component_binding_invalid"]},
        ) from exc
    source_projection = (
        request_projection.source_request.source_request.base_request.source_projection
    )
    source_spans = source_projection.source_span_catalog.spans
    span_ids = {item.source_span_id for item in source_spans}
    mismatch = _build_relation_mismatch(lifecycle=lifecycle, span_ids=span_ids)
    if mismatch is not None:
        _raise_relation_mismatch(mismatch)
    normalized_arguments = {
        key: copy.deepcopy(value)
        for key, value in raw_arguments.items()
        if key != "lifecycle_component_binding"
    }
    plan, closure = normalize_trigger_bound_self_directed_plan(
        task=task,
        catalog=catalog,
        request_projection=request_projection.source_request,
        trigger=trigger,
        revision_index=revision_index,
        parent_plan_hash=parent_plan_hash,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        raw_arguments=normalized_arguments,
    )
    mutation_span = plan.causal_mechanism.causal_path[-1].source_span.source_span_id
    mismatch = _build_relation_mismatch(
        lifecycle=lifecycle,
        span_ids=span_ids,
        mutation_site_span_id=mutation_span,
    )
    if mismatch is not None:
        _raise_relation_mismatch(mismatch)
    owner_index = next(
        index
        for index, component in enumerate(lifecycle.components)
        if component.owner_source_span_id == mutation_span
    )
    cited = {
        *(component.owner_source_span_id for component in lifecycle.components),
        *(
            span_id
            for transition in lifecycle.transitions
            for span_id in transition.evidence_source_span_ids
        ),
        *(
            span_id
            for postcondition in lifecycle.atomic_postconditions
            for span_id in postcondition.evidence_source_span_ids
        ),
    }
    body = {
        "schema_version": LIFECYCLE_COMPONENT_RECORD_SCHEMA,
        "policy_version": LIFECYCLE_COMPONENT_BINDING_POLICY,
        "run_id": plan.run_id,
        "worktree_diff_hash": plan.worktree_diff_hash,
        "plan_hash": plan.content_hash,
        "lifecycle": lifecycle.model_dump(mode="python"),
        "cited_source_span_ids": tuple(sorted(cited)),
        "mutation_site_span_id": mutation_span,
        "mutation_owner_component_index": owner_index,
        "public_current_diff_source_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return plan, closure, _hashed(RecordedLifecycleComponentBinding, body)


class LifecyclePlanFeedbackEvidenceV3(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["compact-plan-admission-feedback-evidence-v3"]
    policy_version: Literal["bounded-plan-admission-feedback-v3"]
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_bytes: int = Field(ge=1)
    projected_context_bytes: int = Field(ge=1, le=2_000_000)
    latest_feedback_bytes: int = Field(ge=0, le=MAX_PLAN_FEEDBACK_BYTES_V3)
    rejection_count: int = Field(ge=0)
    latest_rejection_sequence: int | None = Field(default=None, ge=1)
    latest_relation_mismatch_hash: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    durable_event_changed: Literal[False]
    public_projection_only: Literal[True]
    private_or_hidden_material_included: Literal[False]
    raw_reasoning_included: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if bool(self.rejection_count) is not (self.latest_rejection_sequence is not None):
            raise ValueError("lifecycle feedback latest rejection differs")
        if bool(self.rejection_count) is not bool(self.latest_feedback_bytes):
            raise ValueError("lifecycle feedback byte accounting differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("lifecycle feedback evidence hash differs")
        return self


@dataclass(frozen=True)
class LifecyclePlanFeedbackContextV3:
    rendered: str
    content_hash: str
    evidence: LifecyclePlanFeedbackEvidenceV3


def _catalog_ids(details: dict[str, Any]) -> tuple[list[str], list[str]]:
    catalog = details.get("eligible_plan_evidence_catalog")
    items = catalog.get("items", []) if isinstance(catalog, dict) else []
    evidence_ids = sorted(
        {
            str(item["evidence_id"])
            for item in items
            if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
        }
    )
    spans: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            raw_spans = value.get("spans")
            if isinstance(raw_spans, list) and all(isinstance(item, dict) for item in raw_spans):
                spans.extend(raw_spans)
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(details.get("activated_exploration_plan_request"))
    span_ids = sorted(
        {
            str(item["source_span_id"])
            for item in spans
            if isinstance(item, dict) and isinstance(item.get("source_span_id"), str)
        }
    )
    return evidence_ids, span_ids


def project_lifecycle_plan_admission_feedback_v3(
    compacted: CompactedEventContext,
) -> LifecyclePlanFeedbackContextV3:
    """Keep one exact public relation mismatch in bounded model-facing feedback."""

    if type(compacted) is not CompactedEventContext:
        raise TypeError("lifecycle plan feedback requires an exact compacted context")
    validate_lean_context_event_compaction(compacted)
    try:
        source = json.loads(compacted.rendered)
    except json.JSONDecodeError as exc:
        raise ContractError("lifecycle plan feedback context is not JSON") from exc
    if not isinstance(source, dict) or not isinstance(source.get("recent_events"), list):
        raise ContractError("lifecycle plan feedback context shape differs")
    projected = copy.deepcopy(source)
    targets: list[tuple[int, dict[str, Any], LifecycleRelationMismatch | None]] = []
    for index, event in enumerate(projected["recent_events"]):
        payload = event.get("payload") if isinstance(event, dict) else None
        if not (
            isinstance(payload, dict)
            and event.get("type") == "ToolFailed"
            and payload.get("tool") in {"record_work_plan", "revise_work_plan"}
            and payload.get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
            and isinstance(payload.get("error_details"), dict)
            and isinstance(event.get("sequence"), int)
        ):
            continue
        if (
            event.get("actor") != "tool-gateway"
            or payload.get("status") != "rejected"
            or payload.get("admission_blocked") is not True
        ):
            raise ContractError("lifecycle plan feedback event contract differs")
        details = payload["error_details"]
        relation_raw = details.get("lifecycle_relation_mismatch")
        try:
            relation = (
                LifecycleRelationMismatch.model_validate_json(canonical_json(relation_raw))
                if relation_raw is not None
                else None
            )
        except ValueError as exc:
            raise ContractError("lifecycle relation feedback is invalid") from exc
        reduced = copy.deepcopy(details)
        reduced.pop("lifecycle_relation_mismatch", None)
        _validate_source_details(
            reduced,
            accepted_policy_versions=frozenset({SELF_DIRECTED_EXPLORATION_POLICY}),
        )
        relation_reason = "lifecycle_component_relation_invalid" in details.get("reason_codes", [])
        if relation_reason is not (relation is not None):
            raise ContractError("lifecycle relation feedback reason differs")
        targets.append((index, event, relation))
    latest_sequence = targets[-1][1]["sequence"] if targets else None
    latest_feedback_bytes = 0
    latest_mismatch_hash = None
    for _index, event, relation in targets:
        details = event["payload"]["error_details"]
        source_hash = sha256_json(details)
        if event["sequence"] != latest_sequence:
            event["payload"]["error_details"] = {
                "schema_version": "superseded-plan-admission-feedback-v3",
                "projection_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V3,
                "source_error_details_hash": source_hash,
                "superseded_by_event_sequence": latest_sequence,
            }
            continue
        evidence_ids, span_ids = _catalog_ids(details)
        compact = {
            "schema_version": COMPACT_FEEDBACK_SCHEMA_V3,
            "projection_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V3,
            "source_error_details_hash": source_hash,
            "plan_gate_id": details.get("plan_gate_id"),
            "attempt": details.get("attempt"),
            "reason_codes": details.get("reason_codes"),
            "worktree_diff_hash": details.get("worktree_diff_hash"),
            "required_prior_hypothesis_disposition": details.get(
                "required_prior_hypothesis_disposition"
            ),
            "eligible_evidence_ids": evidence_ids,
            "eligible_source_span_ids": span_ids,
            "causal_reset_required": details.get("cross_reset_failure_trigger") is not None,
            "different_causal_boundary_required": (
                details.get("cross_reset_failure_trigger") is not None
            ),
            "lifecycle_relation_mismatch": (
                relation.model_dump(mode="json") if relation is not None else None
            ),
            "guidance": (
                "Retry once using components[0..component_count-1], the exact transition "
                "indices, and current source spans reported in lifecycle_relation_mismatch."
                if relation is not None
                else "Retry once using only the exact public evidence and source-span IDs."
            ),
        }
        compact_bytes = len(canonical_json(compact).encode("utf-8"))
        if compact_bytes > MAX_PLAN_FEEDBACK_BYTES_V3:
            raise ContractError("lifecycle plan feedback exceeds its byte ceiling")
        latest_feedback_bytes = compact_bytes
        latest_mismatch_hash = relation.content_hash if relation is not None else None
        event["payload"]["error_details"] = compact
    rendered = json.dumps(projected, indent=2, ensure_ascii=False, default=str)
    body = {
        "schema_version": COMPACT_FEEDBACK_EVIDENCE_SCHEMA_V3,
        "policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V3,
        "source_context_hash": compacted.content_hash,
        "projected_context_hash": sha256_text(rendered),
        "source_context_bytes": len(compacted.rendered.encode("utf-8")),
        "projected_context_bytes": len(rendered.encode("utf-8")),
        "latest_feedback_bytes": latest_feedback_bytes,
        "rejection_count": len(targets),
        "latest_rejection_sequence": latest_sequence,
        "latest_relation_mismatch_hash": latest_mismatch_hash,
        "durable_event_changed": False,
        "public_projection_only": True,
        "private_or_hidden_material_included": False,
        "raw_reasoning_included": False,
    }
    evidence = _hashed(LifecyclePlanFeedbackEvidenceV3, body)
    return LifecyclePlanFeedbackContextV3(
        rendered=rendered,
        content_hash=evidence.projected_context_hash,
        evidence=evidence,
    )


__all__ = [
    "COMPACT_FEEDBACK_EVIDENCE_SCHEMA_V3",
    "COMPACT_FEEDBACK_SCHEMA_V3",
    "LIFECYCLE_COMPONENT_BINDING_POLICY",
    "LIFECYCLE_COMPONENT_RECORD_SCHEMA",
    "LIFECYCLE_COMPONENT_REQUEST_SCHEMA",
    "LIFECYCLE_RELATION_MISMATCH_SCHEMA",
    "LifecycleComponentBindingInput",
    "LifecycleComponentBoundPlanRequest",
    "LifecyclePlanFeedbackContextV3",
    "LifecyclePlanFeedbackEvidenceV3",
    "LifecycleRelationMismatch",
    "PLAN_ADMISSION_FEEDBACK_POLICY_V3",
    "RecordedLifecycleComponentBinding",
    "lifecycle_component_workflow_instruction",
    "normalize_lifecycle_component_bound_plan",
    "project_lifecycle_component_bound_plan_request",
    "project_lifecycle_component_bound_tool_surface",
    "project_lifecycle_plan_admission_feedback_v3",
]
