"""Opt-in runtime activation for the public exploration-closure gate.

This successor wraps the immutable, source-qualified exploration request from
``workflow_exploration_gate_successor``.  It changes only the new V19 request
surface: V18 remains on its original causal-plan schema and event path.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    ActivatedCausalPlanRequest,
    CausalMechanismHistoryEntryV2,
    project_causal_plan_workflow_tool_surface_v2,
    workflow_instruction_v5,
)
from patchloop.agent.workflow_causal_plan_projection_successor import RecordedCausalPlanV2
from patchloop.agent.workflow_exploration_gate_successor import (
    EXPLORATION_GATE_POLICY,
    ExplorationGatedCausalPlanRequest,
    ExplorationWorkPlanBinding,
    PublicExplorationClosureReceipt,
    normalize_exploration_gated_causal_plan,
    project_exploration_gated_causal_plan_request,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    PublicSemanticProgressState,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import (
    ActiveWorkState,
    EligiblePlanEvidenceCatalog,
    EligiblePlanEvidenceCatalogV2,
    PlanTrigger,
    WorkflowToolSurfaceV2,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json, sha256_json

EXPLORATION_GATE_ACTIVATION_POLICY = "gateway-owned-public-exploration-closure-v1"
EXPLORATION_ACTIVATED_REQUEST_SCHEMA = "activated-exploration-gated-causal-plan-request-v1"
EXPLORATION_CLOSURE_RECORDED_EVENT_SCHEMA = "exploration-closure-recorded-v1"
EXPLORATION_WORKFLOW_INSTRUCTION_SCHEMA = "lean-workflow-instruction-v6"


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


class ActivatedExplorationPlanRequest(BaseModel):
    """Exact V19 dynamic schema derived from one request-bound V18 schema."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["activated-exploration-gated-causal-plan-request-v1"]
    policy_version: Literal["gateway-owned-public-exploration-closure-v1"]
    source_policy_version: Literal["public-boundary-and-unknown-closure-v1"]
    source_request: ExplorationGatedCausalPlanRequest
    source_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parameters: dict[str, Any]
    parameter_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
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
            self.source_request.policy_version != self.source_policy_version
            or self.source_request.runtime_surface_activated
            or self.source_request_hash != self.source_request.content_hash
            or self.base_request_hash != self.source_request.base_request.content_hash
            or self.parameters != self.source_request.parameters
            or self.parameter_schema_hash != self.source_request.parameter_schema_hash
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("activated exploration request differs")
        return self


def project_activated_exploration_plan_request(
    base_request: ActivatedCausalPlanRequest,
) -> ActivatedExplorationPlanRequest:
    """Activate the already-qualified exploration schema without changing V18."""

    source = project_exploration_gated_causal_plan_request(base_request)
    body = {
        "schema_version": EXPLORATION_ACTIVATED_REQUEST_SCHEMA,
        "policy_version": EXPLORATION_GATE_ACTIVATION_POLICY,
        "source_policy_version": EXPLORATION_GATE_POLICY,
        "source_request": source.model_dump(mode="python"),
        "source_request_hash": source.content_hash,
        "base_request_hash": base_request.content_hash,
        "parameters": copy.deepcopy(source.parameters),
        "parameter_schema_hash": source.parameter_schema_hash,
        "runtime_surface_activated": True,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(ActivatedExplorationPlanRequest, body)


def project_exploration_workflow_tool_surface(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[WorkflowToolSurfaceV2, ActivatedExplorationPlanRequest | None]:
    """Replace only V19's selected plan tool with the exploration schema."""

    surface, base_request = project_causal_plan_workflow_tool_surface_v2(
        task=task,
        decision=decision,
        catalog=catalog,
        source_tool_schemas=source_tool_schemas,
        cross_reset_trigger=cross_reset_trigger,
    )
    if base_request is None:
        return surface, None
    request = project_activated_exploration_plan_request(base_request)
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    plan_schemas = [
        item for item in selected if item.get("name") in {"record_work_plan", "revise_work_plan"}
    ]
    if len(plan_schemas) != 1:
        raise RecoveryError("exploration plan dynamic surface differs")
    plan_schemas[0]["parameters"] = copy.deepcopy(request.parameters)
    plan_schemas[0]["description"] = (
        "Record one public causal plan and close its ownership, execution, mutation, "
        "preservation, and declared-unknown evidence before semantic mutation."
    )
    body = {
        **surface.model_dump(mode="python", exclude={"content_hash", "selected_tool_schema_hash"}),
        "selected_tool_schemas": tuple(selected),
        "selected_tool_schema_hash": sha256_json(selected),
    }
    return _hashed(WorkflowToolSurfaceV2, body), request


def project_exploration_readiness_decision(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> WorkflowDecisionV3:
    """Keep V19 in bounded public exploration until its plan is constructible."""

    plan_tool_names = {
        name
        for name in decision.allowed_tool_names
        if name in {"record_work_plan", "revise_work_plan"}
    }
    if not plan_tool_names:
        return decision
    _, base_request = project_causal_plan_workflow_tool_surface_v2(
        task=task,
        decision=decision,
        catalog=catalog,
        source_tool_schemas=source_tool_schemas,
        cross_reset_trigger=cross_reset_trigger,
    )
    if base_request is None:
        raise RecoveryError("exploration readiness lacks a causal request")
    coverage_keys = {
        item.coverage_key for item in base_request.source_projection.source_span_catalog.spans
    }
    if len(coverage_keys) >= 2:
        return decision
    revision = "revise_work_plan" in plan_tool_names
    exhausted = (
        decision.information_actions_in_episode >= 3
        if revision
        else decision.pre_mutation_actions_used >= 10
    )
    body = decision.model_dump(mode="python", exclude={"content_hash"})
    if exhausted:
        body.update(
            {
                "target": "terminal",
                "allowed_tool_names": (),
                "expected_check_id": None,
                "terminal_reason": (
                    "semantic_no_progress_evidence_exhausted"
                    if revision
                    else "pre_mutation_evidence_exhausted"
                ),
            }
        )
        return _hashed(WorkflowDecisionV3, body)
    available = {
        str(item.get("name"))
        for item in source_tool_schemas
        if item.get("name") in {"search_files", "read_file"}
    }
    selected = tuple(name for name in ("search_files", "read_file") if name in available)
    if not selected:
        raise RecoveryError("exploration readiness lacks public inspection tools")
    body.update(
        {
            "target": "correction-investigation" if revision else "pre-mutation-exploration",
            "allowed_tool_names": selected,
            "expected_check_id": None,
            "terminal_reason": None,
            "reasoning_effort": "low",
            "effective_max_output_tokens": min(decision.effective_max_output_tokens, 4_096),
        }
    )
    return _hashed(WorkflowDecisionV3, body)


def normalize_activated_exploration_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    request_projection: ActivatedExplorationPlanRequest,
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> tuple[RecordedCausalPlanV2, PublicExplorationClosureReceipt]:
    """Recompute the exact V19 request before admitting model-owned fields."""

    exact = project_activated_exploration_plan_request(
        request_projection.source_request.base_request
    )
    if request_projection != exact:
        raise RecoveryError("activated exploration request projection differs")
    return normalize_exploration_gated_causal_plan(
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
        raw_arguments=raw_arguments,
    )


def exploration_closure_event_payload(
    *,
    binding: ExplorationWorkPlanBinding,
    request_projection: ActivatedExplorationPlanRequest,
) -> dict[str, Any]:
    """Build the durable event body used by restart/recovery validation."""

    if binding.receipt.request_projection_hash != request_projection.source_request_hash:
        raise RecoveryError("exploration binding request projection differs")
    return {
        "schema_version": EXPLORATION_CLOSURE_RECORDED_EVENT_SCHEMA,
        "policy_version": EXPLORATION_GATE_ACTIVATION_POLICY,
        "plan_hash": binding.plan_hash,
        "binding": binding.model_dump(mode="python"),
        "binding_hash": binding.content_hash,
        "activated_request_hash": request_projection.content_hash,
        "source_request_hash": request_projection.source_request_hash,
    }


def exploration_binding_for_hash(
    *,
    run_id: str,
    plan_hash: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> ExplorationWorkPlanBinding | None:
    """Recover exactly one closure binding and verify its PlanRecorded link."""

    event_tuple = tuple(events)
    plan_events = {
        event.sequence: event for event in event_tuple if event.type == EventType.PLAN_RECORDED
    }
    matches: list[ExplorationWorkPlanBinding] = []
    for event in event_tuple:
        if event.type != EventType.EXPLORATION_CLOSURE_RECORDED:
            continue
        try:
            binding = ExplorationWorkPlanBinding.model_validate_json(
                canonical_json(event.payload.get("binding"))
            )
        except ValueError as exc:
            raise RecoveryError("exploration closure binding event is invalid") from exc
        plan_event = plan_events.get(binding.plan_event_sequence)
        if (
            event.run_id != run_id
            or binding.run_id != run_id
            or event.payload.get("schema_version") != EXPLORATION_CLOSURE_RECORDED_EVENT_SCHEMA
            or event.payload.get("policy_version") != EXPLORATION_GATE_ACTIVATION_POLICY
            or event.payload.get("binding_hash") != binding.content_hash
            or event.payload.get("plan_hash") != binding.plan_hash
            or event.payload.get("source_request_hash") != binding.receipt.request_projection_hash
            or plan_event is None
            or plan_event.payload.get("plan_hash") != binding.plan_hash
            or plan_event.payload.get("revision_index") != binding.revision_index
            or plan_event.payload.get("parent_plan_hash") != binding.parent_plan_hash
            or plan_event.payload.get("trigger") != binding.trigger
            or plan_event.payload.get("exploration_closure_receipt_hash") != binding.receipt_hash
            or plan_event.payload.get("activated_exploration_request_hash")
            != event.payload.get("activated_request_hash")
        ):
            raise RecoveryError("exploration closure event binding differs")
        if binding.plan_hash == plan_hash:
            matches.append(binding)
    if len(matches) > 1:
        raise RecoveryError("exploration closure binding repeats")
    return matches[0] if matches else None


def workflow_instruction_v6(
    decision: WorkflowDecisionV3,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV2,
    active_work_state: ActiveWorkState | None,
    semantic_progress_state: PublicSemanticProgressState | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    request_projection: ActivatedExplorationPlanRequest | None,
) -> dict[str, Any]:
    """Pin the exact V19 exploration request beside bounded active work state."""

    base = workflow_instruction_v5(
        decision,
        public_task_spec=public_task_spec,
        catalog=catalog,
        active_work_state=active_work_state,
        semantic_progress_state=semantic_progress_state,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        request_projection=(
            request_projection.source_request.base_request
            if request_projection is not None
            else None
        ),
    )
    body = {
        **{key: value for key, value in base.items() if key != "content_hash"},
        "schema_version": EXPLORATION_WORKFLOW_INSTRUCTION_SCHEMA,
        "activated_exploration_plan_request": (
            request_projection.model_dump(mode="json") if request_projection is not None else None
        ),
        "activated_exploration_plan_request_hash": (
            request_projection.content_hash if request_projection is not None else sha256_json(None)
        ),
    }
    if request_projection is not None:
        body["instruction"] = (
            "Use only request-enumerated cspan IDs. Describe a causal path and explicitly "
            "close ownership, execution, mutation, preservation, and every declared unknown; "
            "leave open_blocking_unknowns empty only when public evidence supports mutation."
        )
    elif decision.target in {"pre-mutation-exploration", "correction-investigation"}:
        body["instruction"] = (
            "Gather a second distinct current-source range that clarifies an ownership, "
            "execution, or mutation boundary. Do not repeat the same covered range."
        )
    return {**body, "content_hash": sha256_json(body)}


__all__ = [
    "EXPLORATION_ACTIVATED_REQUEST_SCHEMA",
    "EXPLORATION_CLOSURE_RECORDED_EVENT_SCHEMA",
    "EXPLORATION_GATE_ACTIVATION_POLICY",
    "EXPLORATION_WORKFLOW_INSTRUCTION_SCHEMA",
    "ActivatedExplorationPlanRequest",
    "exploration_binding_for_hash",
    "exploration_closure_event_payload",
    "normalize_activated_exploration_plan",
    "project_activated_exploration_plan_request",
    "project_exploration_readiness_decision",
    "project_exploration_workflow_tool_surface",
    "workflow_instruction_v6",
]
