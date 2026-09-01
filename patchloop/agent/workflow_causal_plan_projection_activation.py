"""Runtime activation for the qualified server-owned causal-plan projection.

This module is append-only with respect to Lean V17.  It reuses the exact
public ``cspan`` projection qualified by
``workflow_causal_plan_projection_successor`` while keeping the V17 baseline
restore, family-distinctness, correction-limit, and one-retry contracts.

The model supplies only public semantic text and request-enumerated IDs.  The
gateway owns workflow state, evidence binding, causal roles and locations,
check order, and durable plan identity.  A pre-restore failed check remains a
bounded observation after reset; only current-baseline source reads authorize
the next mutation.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
    causal_reset_gate_id,
)
from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    CAUSAL_PLAN_PROJECTION_POLICY,
    CausalPlanModelInputV2,
    CausalPlanRequestProjection,
    EligibleCausalSourceSpan,
    PublicCausalMechanismV2,
    RecordedCausalPlanV2,
    _normalize_mechanism,
    normalize_causal_plan_request,
    project_causal_plan_request,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    PublicSemanticProgressState,
    WorkflowDecisionV3,
    project_workflow_tool_surface_v3,
    workflow_instruction_v3,
)
from patchloop.agent.workflow_successor_v2 import (
    ActiveWorkState,
    CandidateFileEvidence,
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalog,
    EligiblePlanEvidenceCatalogV2,
    PlanTrigger,
    RecordedWorkPlanV2,
    WorkflowToolSurfaceV2,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json

CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY = "gateway-owned-causal-plan-projection-v1"
ACTIVATED_CAUSAL_PLAN_REQUEST_SCHEMA = "activated-causal-plan-request-v1"
CAUSAL_PLAN_BINDING_SCHEMA_V2 = "causal-work-plan-binding-v2"
CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA_V5 = "lean-workflow-instruction-v5"

_SERVER_OWNED_FIELDS = (
    "observation_status",
    "observation_evidence_id",
    "foundation_evidence_ids",
    "candidate_files",
    "planned_check_ids",
    "causal_path_roles",
    "causal_path_ordinals",
    "causal_path_locations",
    "final_relationship_to_next",
    "run_id",
    "task_id",
    "task_version",
    "public_task_hash",
    "worktree_diff_hash",
)


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _reject(reason_code: str, message: str) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


class ActivatedCausalPlanRequest(BaseModel):
    """Exact dynamic plan schema and its immutable source-qualified projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["activated-causal-plan-request-v1"]
    policy_version: Literal["gateway-owned-causal-plan-projection-v1"]
    source_projection_policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    source_projection: CausalPlanRequestProjection
    source_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cross_reset_failure_trigger_hash: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    parameters: dict[str, Any]
    parameter_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    stale_check_observation_only: bool
    current_source_read_authorizes_mutation: Literal[True]
    runtime_surface_activated: Literal[True]
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_activation(self) -> Self:
        if (
            self.source_projection.policy_version != self.source_projection_policy_version
            or self.source_projection_hash != self.source_projection.content_hash
            or self.parameters != self.source_projection.parameters
            or self.parameter_schema_hash != self.source_projection.parameter_schema_hash
            or self.stale_check_observation_only
            is not (self.cross_reset_failure_trigger_hash is not None)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("activated causal-plan request differs")
        return self


class CausalMechanismHistoryEntryV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    revision_index: int = Field(ge=0, le=3)
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parent_plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: PlanTrigger
    mechanism: PublicCausalMechanismV2
    projected_plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_entry(self) -> Self:
        if self.revision_index == 0:
            if self.parent_plan_hash is not None or self.trigger != "initial":
                raise ValueError("initial causal v2 history entry differs")
        elif self.parent_plan_hash is None or self.trigger == "initial":
            raise ValueError("causal v2 history revision binding differs")
        return self


class CausalWorkPlanBindingV2(BaseModel):
    """Companion binding between the ordinary active plan and projected plan."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["causal-work-plan-binding-v2"]
    policy_version: Literal["gateway-owned-causal-plan-projection-v1"]
    source_projection_policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    run_id: str = Field(min_length=1)
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_event_sequence: int = Field(ge=1)
    revision_index: int = Field(ge=0, le=3)
    parent_plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: PlanTrigger
    projected_plan: RecordedCausalPlanV2
    projected_plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mechanism: PublicCausalMechanismV2
    request_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cross_reset_failure_trigger_hash: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    stale_check_observation_only: bool
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        plan = self.projected_plan
        if self.revision_index == 0:
            initial_valid = self.parent_plan_hash is None and self.trigger == "initial"
        else:
            initial_valid = self.parent_plan_hash is not None and self.trigger != "initial"
        if (
            not initial_valid
            or plan.run_id != self.run_id
            or plan.revision_index != self.revision_index
            or plan.parent_plan_hash != self.parent_plan_hash
            or plan.trigger != self.trigger
            or self.projected_plan_hash != plan.content_hash
            or self.mechanism != plan.causal_mechanism
            or self.stale_check_observation_only
            is not (self.cross_reset_failure_trigger_hash is not None)
            or (
                self.stale_check_observation_only
                and (
                    plan.trigger != "check_failure"
                    or plan.observation_evidence is not None
                    or plan.prior_hypothesis_disposition != "rejected"
                )
            )
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("causal work-plan v2 binding differs")
        return self


def _cross_reset_source_projection(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
) -> CausalPlanRequestProjection:
    """Reuse the qualified source projection without inventing stale evidence."""

    initial = project_causal_plan_request(task=task, catalog=catalog, trigger="initial")
    body = {
        **initial.model_dump(mode="python", exclude={"content_hash"}),
        "trigger": "check_failure",
        "observation_status": "visible_check_failed",
        "observation_evidence_id": None,
    }
    return _hashed(CausalPlanRequestProjection, body)


def project_activated_causal_plan_request(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    trigger: PlanTrigger,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> ActivatedCausalPlanRequest:
    """Activate the exact qualified parameters for one request-bound plan gate."""

    if cross_reset_trigger is None:
        source = project_causal_plan_request(
            task=task,
            catalog=catalog,
            trigger=trigger,
            trigger_check_id=trigger_check_id,
            trigger_event_sequence=trigger_event_sequence,
        )
    else:
        if (
            trigger != "check_failure"
            or trigger_check_id != cross_reset_trigger.check_id
            or trigger_event_sequence != cross_reset_trigger.failure_event_sequences[-1]
            or catalog.run_id != cross_reset_trigger.run_id
            or catalog.worktree_diff_hash != cross_reset_trigger.restored_baseline_diff_hash
            or (
                isinstance(catalog, EligiblePlanEvidenceCatalogV2)
                and catalog.required_trigger_status != "not_required"
            )
        ):
            raise RecoveryError("cross-reset causal-plan request binding differs")
        source = _cross_reset_source_projection(task=task, catalog=catalog)
    body = {
        "schema_version": ACTIVATED_CAUSAL_PLAN_REQUEST_SCHEMA,
        "policy_version": CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY,
        "source_projection_policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "source_projection": source.model_dump(mode="python"),
        "source_projection_hash": source.content_hash,
        "cross_reset_failure_trigger_hash": (
            cross_reset_trigger.content_hash if cross_reset_trigger is not None else None
        ),
        "parameters": copy.deepcopy(source.parameters),
        "parameter_schema_hash": source.parameter_schema_hash,
        "stale_check_observation_only": cross_reset_trigger is not None,
        "current_source_read_authorizes_mutation": True,
        "runtime_surface_activated": True,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(ActivatedCausalPlanRequest, body)


def _normalize_cross_reset_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    projection: ActivatedCausalPlanRequest,
    revision_index: int,
    parent_plan_hash: str,
    trigger: CrossResetFailureTrigger,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> RecordedCausalPlanV2:
    try:
        submitted = CausalPlanModelInputV2.model_validate(raw_arguments)
    except ValueError as exc:
        _reject("causal_plan_input_shape_invalid", "causal plan model input differs")
        raise AssertionError from exc
    if (
        revision_index < 1
        or revision_index > 3
        or submitted.prior_hypothesis_disposition != "rejected"
    ):
        _reject("causal_plan_revision_binding_invalid", "cross-reset causal revision differs")
    source_projection = projection.source_projection
    mechanism = _normalize_mechanism(
        projection=source_projection,
        submitted=submitted.causal_mechanism,
    )
    span_by_id = {item.source_span_id: item for item in source_projection.source_span_catalog.spans}
    candidate_spans: list[EligibleCausalSourceSpan] = []
    for span_id in dict.fromkeys(submitted.candidate_source_span_ids):
        span = span_by_id.get(span_id)
        if span is None:
            _reject(
                "causal_candidate_span_ineligible",
                "causal plan candidate is outside the current source-span catalog",
            )
        candidate_spans.append(span)
    mechanism_ids = {step.source_span.source_span_id for step in mechanism.causal_path}
    if any(item.source_span_id not in mechanism_ids for item in candidate_spans):
        _reject(
            "causal_candidate_not_in_mechanism",
            "causal plan candidate is not one of its evidence-bound mechanism spans",
        )
    mutation_span_id = mechanism.causal_path[-1].source_span.source_span_id
    if mutation_span_id not in {item.source_span_id for item in candidate_spans}:
        _reject(
            "causal_mutation_site_candidate_mismatch",
            "causal mutation site is not one of the selected candidate spans",
        )
    exhausted_boundaries = {
        item.mechanism.causal_path[0].source_span.coverage_key for item in history
    }
    boundary_key = mechanism.causal_path[0].source_span.coverage_key
    if boundary_key in exhausted_boundaries:
        _reject(
            "causal_boundary_already_exhausted",
            "causal alternative reuses an exhausted public boundary",
        )
    if mechanism.mechanism_family_key in {item.mechanism.mechanism_family_key for item in history}:
        _reject(
            "causal_mechanism_family_unchanged",
            "causal alternative remains in an exhausted mechanism family",
        )
    catalog_by_id = {item.evidence_id: item for item in catalog.items}
    support: list[EligiblePlanEvidence] = []
    for evidence_id in dict.fromkeys(submitted.supporting_evidence_ids):
        evidence = catalog_by_id.get(evidence_id)
        if evidence is None or evidence.role != "support":
            _reject(
                "causal_support_evidence_ineligible",
                "causal plan support evidence differs from the current request",
            )
        support.append(evidence)
    foundation_ids = set(mechanism.source_evidence_ids)
    foundation_ids.update(item.read_evidence_id for item in candidate_spans)
    foundation = tuple(
        item
        for item in catalog.items
        if item.evidence_id in foundation_ids and item.role == "foundation"
    )
    if not foundation:
        _reject("causal_source_evidence_unavailable", "cross-reset causal source is absent")
    candidates_by_path: dict[str, EligibleCausalSourceSpan] = {}
    for span in candidate_spans:
        previous = candidates_by_path.get(span.path)
        if previous is None or span.canonical_event_sequence > previous.canonical_event_sequence:
            candidates_by_path[span.path] = span
    candidates = tuple(
        CandidateFileEvidence(path=path, read_evidence_id=span.read_evidence_id)
        for path, span in sorted(candidates_by_path.items())
    )
    body = {
        "schema_version": "recorded-causal-plan-v2",
        "policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "run_id": catalog.run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": catalog.public_task_hash,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "trigger": "check_failure",
        "revision_index": revision_index,
        "parent_plan_hash": parent_plan_hash,
        "trigger_check_id": trigger.check_id,
        "trigger_event_sequence": trigger.failure_event_sequences[-1],
        "observation_status": "visible_check_failed",
        "observation_evidence": None,
        "hypothesis": submitted.hypothesis,
        "foundation_evidence": tuple(item.model_dump(mode="python") for item in foundation),
        "supporting_evidence": tuple(item.model_dump(mode="python") for item in support),
        "candidate_source_spans": tuple(item.model_dump(mode="python") for item in candidate_spans),
        "candidate_files": tuple(item.model_dump(mode="python") for item in candidates),
        "intended_change": submitted.intended_change,
        "expected_behavior": submitted.expected_behavior,
        "unknowns": tuple(submitted.unknowns),
        "prior_hypothesis_disposition": "rejected",
        "planned_check_ids": tuple(check.id for check in task.visible_checks),
        "causal_mechanism": mechanism.model_dump(mode="python"),
        "source_span_catalog_hash": source_projection.source_span_catalog.content_hash,
        "server_owned_fields": _SERVER_OWNED_FIELDS,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(RecordedCausalPlanV2, body)


def normalize_activated_causal_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    request_projection: ActivatedCausalPlanRequest,
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> RecordedCausalPlanV2:
    """Recompute the exact request, then normalize only model-owned semantics."""

    exact = project_activated_causal_plan_request(
        task=task,
        catalog=catalog,
        trigger=trigger,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
        cross_reset_trigger=cross_reset_trigger,
    )
    if request_projection != exact:
        raise RecoveryError("causal-plan request projection differs")
    if cross_reset_trigger is None:
        return normalize_causal_plan_request(
            task=task,
            catalog=catalog,
            trigger=trigger,
            revision_index=revision_index,
            parent_plan_hash=parent_plan_hash,
            trigger_check_id=trigger_check_id,
            trigger_event_sequence=trigger_event_sequence,
            raw_arguments=raw_arguments,
        )
    if parent_plan_hash is None or not history or history[-1].plan_hash != parent_plan_hash:
        raise RecoveryError("cross-reset causal-plan parent differs")
    return _normalize_cross_reset_plan(
        task=task,
        catalog=catalog,
        projection=request_projection,
        revision_index=revision_index,
        parent_plan_hash=parent_plan_hash,
        trigger=cross_reset_trigger,
        history=history,
        raw_arguments=raw_arguments,
    )


def standard_plan_from_projected_causal_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    projected: RecordedCausalPlanV2,
) -> RecordedWorkPlanV2:
    if (
        projected.run_id != catalog.run_id
        or projected.task_id != task.task_id
        or projected.task_version != task.task_version
        or projected.public_task_hash != catalog.public_task_hash
        or projected.worktree_diff_hash != catalog.worktree_diff_hash
    ):
        raise ContractError("projected causal standard-plan binding differs")
    body = {
        "schema_version": "recorded-work-plan-v2",
        "run_id": projected.run_id,
        "task_id": projected.task_id,
        "task_version": projected.task_version,
        "public_task_hash": projected.public_task_hash,
        "worktree_diff_hash": projected.worktree_diff_hash,
        "observation_status": projected.observation_status,
        "hypothesis": projected.hypothesis,
        "foundation_evidence": tuple(
            item.model_dump(mode="python") for item in projected.foundation_evidence
        ),
        "supporting_evidence": tuple(
            item.model_dump(mode="python") for item in projected.supporting_evidence
        ),
        "candidate_files": tuple(
            item.model_dump(mode="python") for item in projected.candidate_files
        ),
        "intended_change": projected.intended_change,
        "expected_behavior": projected.expected_behavior,
        "unknowns": projected.unknowns,
        "planned_check_ids": projected.planned_check_ids,
        "evidence_catalog_hash": catalog.content_hash,
        "revision_index": projected.revision_index,
        "parent_plan_hash": projected.parent_plan_hash,
        "trigger": projected.trigger,
        "trigger_check_id": projected.trigger_check_id,
        "trigger_event_sequence": projected.trigger_event_sequence,
        "prior_hypothesis_disposition": projected.prior_hypothesis_disposition,
        "public_evidence_only": True,
        "hidden_evidence_used": False,
        "private_evidence_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(RecordedWorkPlanV2, body)


def build_causal_work_plan_binding_v2(
    *,
    plan: RecordedWorkPlanV2,
    plan_event_sequence: int,
    projected: RecordedCausalPlanV2,
    request_projection: ActivatedCausalPlanRequest,
    cross_reset_trigger_hash: str | None,
) -> CausalWorkPlanBindingV2:
    if (
        projected.run_id != plan.run_id
        or projected.worktree_diff_hash != plan.worktree_diff_hash
        or projected.revision_index != plan.revision_index
        or projected.parent_plan_hash != plan.parent_plan_hash
        or projected.trigger != plan.trigger
        or not set(projected.causal_mechanism.source_evidence_ids).issubset(
            {item.evidence_id for item in plan.foundation_evidence}
        )
    ):
        raise ContractError("projected causal mechanism does not bind the work plan")
    body = {
        "schema_version": CAUSAL_PLAN_BINDING_SCHEMA_V2,
        "policy_version": CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY,
        "source_projection_policy_version": CAUSAL_PLAN_PROJECTION_POLICY,
        "run_id": plan.run_id,
        "plan_hash": plan.content_hash,
        "plan_event_sequence": plan_event_sequence,
        "revision_index": plan.revision_index,
        "parent_plan_hash": plan.parent_plan_hash,
        "trigger": plan.trigger,
        "projected_plan": projected.model_dump(mode="python"),
        "projected_plan_hash": projected.content_hash,
        "mechanism": projected.causal_mechanism.model_dump(mode="python"),
        "request_projection_hash": request_projection.content_hash,
        "cross_reset_failure_trigger_hash": cross_reset_trigger_hash,
        "stale_check_observation_only": cross_reset_trigger_hash is not None,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(CausalWorkPlanBindingV2, body)


def project_causal_mechanism_history_v2(
    *,
    run_id: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> tuple[CausalMechanismHistoryEntryV2, ...]:
    event_tuple = tuple(events)
    plan_events = {
        event.sequence: event for event in event_tuple if event.type == EventType.PLAN_RECORDED
    }
    bindings: list[CausalWorkPlanBindingV2] = []
    for event in event_tuple:
        if event.type != EventType.CAUSAL_MECHANISM_RECORDED:
            continue
        try:
            binding = CausalWorkPlanBindingV2.model_validate_json(
                canonical_json(event.payload.get("binding"))
            )
        except ValueError as exc:
            raise RecoveryError("causal work-plan v2 binding event is invalid") from exc
        plan_event = plan_events.get(binding.plan_event_sequence)
        if (
            event.run_id != run_id
            or binding.run_id != run_id
            or event.payload.get("schema_version") != "causal-mechanism-recorded-v2"
            or event.payload.get("binding_hash") != binding.content_hash
            or plan_event is None
            or plan_event.payload.get("plan_hash") != binding.plan_hash
            or plan_event.payload.get("revision_index") != binding.revision_index
            or plan_event.payload.get("parent_plan_hash") != binding.parent_plan_hash
            or plan_event.payload.get("trigger") != binding.trigger
        ):
            raise RecoveryError("causal work-plan v2 event binding differs")
        bindings.append(binding)
    if len(bindings) > 4:
        raise RecoveryError("causal mechanism v2 history exceeds the correction envelope")
    for prior, current in zip(bindings, bindings[1:], strict=False):
        if (
            current.revision_index != prior.revision_index + 1
            or current.parent_plan_hash != prior.plan_hash
        ):
            raise RecoveryError("causal mechanism v2 history chain differs")
    return tuple(
        CausalMechanismHistoryEntryV2(
            revision_index=item.revision_index,
            plan_hash=item.plan_hash,
            parent_plan_hash=item.parent_plan_hash,
            trigger=item.trigger,
            mechanism=item.mechanism,
            projected_plan_hash=item.projected_plan_hash,
        )
        for item in bindings
    )


def causal_plan_binding_for_hash_v2(
    *,
    run_id: str,
    plan_hash: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> CausalWorkPlanBindingV2 | None:
    matches: list[CausalWorkPlanBindingV2] = []
    for event in events:
        if event.type != EventType.CAUSAL_MECHANISM_RECORDED:
            continue
        try:
            binding = CausalWorkPlanBindingV2.model_validate_json(
                canonical_json(event.payload.get("binding"))
            )
        except ValueError as exc:
            raise RecoveryError("causal work-plan v2 binding event is invalid") from exc
        if binding.run_id == run_id and binding.plan_hash == plan_hash:
            matches.append(binding)
    if len(matches) > 1:
        raise RecoveryError("causal work-plan v2 binding repeats")
    return matches[0] if matches else None


def _decision(
    base: WorkflowDecisionV3,
    state: PublicSemanticProgressState,
    **updates: Any,
) -> WorkflowDecisionV3:
    body = {
        **base.model_dump(mode="python", exclude={"content_hash"}),
        "semantic_progress_state_hash": state.content_hash,
        "semantic_reset_required": True,
        "required_prior_hypothesis_disposition": "rejected",
        **updates,
    }
    return _hashed(WorkflowDecisionV3, body)


def project_causal_reset_decision_v2(
    *,
    base_decision: WorkflowDecisionV3,
    semantic_progress_state: PublicSemanticProgressState,
    trigger: CrossResetFailureTrigger,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    events: tuple[RunEvent, ...] | list[RunEvent],
    accepted_plan_hash: str | None,
) -> WorkflowDecisionV3:
    """V17-equivalent limits over V2 causal bindings."""

    if (
        not history
        or trigger.source_semantic_progress_state_hash != semantic_progress_state.content_hash
    ):
        raise RecoveryError("cross-reset causal v2 decision history differs")
    event_tuple = tuple(events)
    gate_id = causal_reset_gate_id(trigger, history[-1].plan_hash)
    blocked = [
        event
        for event in event_tuple
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == CAUSAL_ALTERNATIVE_POLICY
        and event.payload.get("plan_gate_id") == gate_id
    ]
    if len(blocked) >= 2:
        raise ContractError(
            "causal projected-plan admission failed twice",
            details={"reason_codes": ["causal_alternative_admission_repeated"]},
        )
    if accepted_plan_hash is not None:
        return _decision(
            base_decision,
            semantic_progress_state,
            target="corrective-mutation",
            allowed_tool_names=("apply_structured_edit",),
            active_plan_hash=accepted_plan_hash,
            plan_gate_id=gate_id,
            plan_admission_recovery_used=bool(blocked),
            plan_admission_recovery_remaining=0 if blocked else 1,
            required_trigger_evidence_id=f"pev:{trigger.failure_event_sequences[-1]}",
            revision_trigger="check_failure",
            terminal_reason=None,
            effective_max_output_tokens=min(base_decision.configured_max_output_tokens, 12_288),
            reasoning_effort="medium",
        )
    episode = [
        event
        for event in event_tuple
        if event.sequence > trigger.restored_event_sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") in {"search_files", "read_file"}
        and event.payload.get("worktree_diff_hash") == trigger.restored_baseline_diff_hash
    ]
    has_search = any(event.payload.get("tool") == "search_files" for event in episode)
    has_read = any(event.payload.get("tool") == "read_file" for event in episode)
    if has_search and has_read:
        target = "revise-work-plan"
        allowed = ("revise_work_plan",)
        ceiling = 8_192
        effort = "medium"
    elif len(episode) >= 3:
        raise ContractError(
            "causal projected-plan evidence acquisition was exhausted",
            details={"reason_codes": ["causal_alternative_evidence_exhausted"]},
        )
    else:
        target = "correction-investigation"
        allowed = (
            ("search_files", "read_file")
            if not has_search and not has_read
            else ("search_files",)
            if not has_search
            else ("read_file",)
        )
        ceiling = 4_096
        effort = "low"
    return _decision(
        base_decision,
        semantic_progress_state,
        target=target,
        allowed_tool_names=allowed,
        information_actions_in_episode=min(len(episode), 3),
        fresh_current_read=has_read,
        active_plan_hash=history[-1].plan_hash,
        plan_gate_id=gate_id,
        plan_admission_recovery_used=bool(blocked),
        plan_admission_recovery_remaining=0 if blocked else 1,
        required_trigger_evidence_id=f"pev:{trigger.failure_event_sequences[-1]}",
        revision_trigger="check_failure",
        terminal_reason=None,
        effective_max_output_tokens=min(base_decision.configured_max_output_tokens, ceiling),
        reasoning_effort=effort,
    )


def _trigger_binding(
    *,
    plan_tool_name: str,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[PlanTrigger, str | None, int | None]:
    if plan_tool_name == "record_work_plan":
        return "initial", None, None
    if plan_tool_name != "revise_work_plan" or decision.revision_trigger is None:
        raise RecoveryError("causal plan surface lacks a plan trigger")
    if cross_reset_trigger is not None:
        return (
            "check_failure",
            cross_reset_trigger.check_id,
            cross_reset_trigger.failure_event_sequences[-1],
        )
    evidence_id = decision.required_trigger_evidence_id
    evidence = next((item for item in catalog.items if item.evidence_id == evidence_id), None)
    if evidence is None:
        raise RecoveryError("causal plan surface trigger is not request-visible")
    return (
        decision.revision_trigger,
        evidence.check.check_id
        if decision.revision_trigger == "check_failure" and evidence.check is not None
        else None,
        evidence.canonical_event_sequence,
    )


def project_causal_plan_workflow_tool_surface_v2(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[WorkflowToolSurfaceV2, ActivatedCausalPlanRequest | None]:
    surface = project_workflow_tool_surface_v3(
        decision=decision,
        catalog=catalog,
        source_tool_schemas=source_tool_schemas,
    )
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    plan_schemas = [
        item for item in selected if item.get("name") in {"record_work_plan", "revise_work_plan"}
    ]
    if not plan_schemas:
        return surface, None
    if len(plan_schemas) != 1:
        raise RecoveryError("causal plan dynamic surface repeats")
    trigger, check_id, event_sequence = _trigger_binding(
        plan_tool_name=str(plan_schemas[0]["name"]),
        decision=decision,
        catalog=catalog,
        cross_reset_trigger=cross_reset_trigger,
    )
    projection = project_activated_causal_plan_request(
        task=task,
        catalog=catalog,
        trigger=trigger,
        trigger_check_id=check_id,
        trigger_event_sequence=event_sequence,
        cross_reset_trigger=cross_reset_trigger,
    )
    for schema in selected:
        if schema.get("name") in {"record_work_plan", "revise_work_plan"}:
            schema["parameters"] = copy.deepcopy(projection.parameters)
            schema["description"] = (
                "Record one public causal work plan using only request-enumerated cspan IDs. "
                "Workflow status, evidence bindings, roles, locations, and check order are "
                "server-owned."
            )
    body = {
        **surface.model_dump(mode="python", exclude={"content_hash", "selected_tool_schema_hash"}),
        "selected_tool_schemas": tuple(selected),
        "selected_tool_schema_hash": sha256_json(selected),
    }
    return _hashed(WorkflowToolSurfaceV2, body), projection


def workflow_instruction_v5(
    decision: WorkflowDecisionV3,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV2,
    active_work_state: ActiveWorkState | None,
    semantic_progress_state: PublicSemanticProgressState | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    request_projection: ActivatedCausalPlanRequest | None,
) -> dict[str, Any]:
    base = workflow_instruction_v3(
        decision,
        public_task_spec=public_task_spec,
        catalog=catalog,
        active_work_state=active_work_state,
        semantic_progress_state=semantic_progress_state,
    )
    history_body = [item.model_dump(mode="json") for item in history]
    body = {
        **{key: value for key, value in base.items() if key != "content_hash"},
        "schema_version": CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA_V5,
        "cross_reset_failure_trigger": (
            cross_reset_trigger.model_dump(mode="json") if cross_reset_trigger is not None else None
        ),
        "causal_mechanism_history": history_body,
        "causal_mechanism_history_hash": sha256_json(history_body),
        "causal_plan_request_projection": (
            request_projection.model_dump(mode="json") if request_projection is not None else None
        ),
        "causal_plan_request_projection_hash": (
            request_projection.content_hash if request_projection is not None else sha256_json(None)
        ),
    }
    if request_projection is not None:
        body["instruction"] = (
            "Use only the exact cspan and support IDs in causal_plan_request_projection. "
            "Describe the causal boundary, optional intermediate steps, and mutation site; "
            "the server supplies roles, locations, evidence, workflow status, and check order."
        )
    return {**body, "content_hash": sha256_json(body)}


__all__ = [
    "ACTIVATED_CAUSAL_PLAN_REQUEST_SCHEMA",
    "CAUSAL_PLAN_BINDING_SCHEMA_V2",
    "CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY",
    "CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA_V5",
    "ActivatedCausalPlanRequest",
    "CausalMechanismHistoryEntryV2",
    "CausalWorkPlanBindingV2",
    "build_causal_work_plan_binding_v2",
    "causal_plan_binding_for_hash_v2",
    "normalize_activated_causal_plan",
    "project_activated_causal_plan_request",
    "project_causal_mechanism_history_v2",
    "project_causal_plan_workflow_tool_surface_v2",
    "project_causal_reset_decision_v2",
    "standard_plan_from_projected_causal_plan",
    "workflow_instruction_v5",
]
