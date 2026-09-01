"""Lean V25 trigger-bound work-plan contract compatibility.

V24 exposed a nullable ``prior_hypothesis_disposition`` enum for every plan
trigger even though admission requires ``null`` for an initial plan and a
non-null disposition for revisions.  This opt-in successor projects the exact
trigger-specific schema and admits self-directed plan-rejection feedback into
the already-bounded request projection.  It does not change V23/V24 request
objects or their fail-closed validators.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    ActivatedCausalPlanRequest,
    CausalMechanismHistoryEntryV2,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    RecordedCausalPlanV2,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    EligiblePlanEvidenceCatalogV4,
    SelfDirectedExplorationClosureReceipt,
    SelfDirectedExplorationState,
    SelfDirectedPlanRequest,
    WorkflowDecisionV4,
    normalize_self_directed_plan,
    project_self_directed_plan_request,
    project_self_directed_tool_surface,
    project_self_directed_workflow_decision,
)
from patchloop.agent.workflow_successor_v2 import (
    EligiblePlanEvidenceCatalog,
    PlanTrigger,
    WorkflowToolSurfaceV2,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import RecoveryError
from patchloop.util import sha256_json

TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY = "trigger-bound-plan-contract-compatibility-v1"
TRIGGER_BOUND_SELF_DIRECTED_PLAN_REQUEST_SCHEMA = "self-directed-exploration-plan-request-v2"

_PLAN_TOOLS = frozenset({"record_work_plan", "revise_work_plan"})
_REVISION_DISPOSITIONS = ("retained", "refined", "rejected")


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _trigger(request: SelfDirectedPlanRequest) -> PlanTrigger:
    return request.source_request.base_request.source_projection.trigger


def _disposition_schema(trigger: PlanTrigger) -> dict[str, Any]:
    if trigger == "initial":
        return {"type": "null", "enum": [None]}
    return {"type": "string", "enum": list(_REVISION_DISPOSITIONS)}


class TriggerBoundSelfDirectedPlanRequest(SelfDirectedPlanRequest):
    """Self-directed plan request whose disposition schema matches its trigger."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-exploration-plan-request-v2"]
    compatibility_policy_version: Literal["trigger-bound-plan-contract-compatibility-v1"]

    @model_validator(mode="after")
    def validate_trigger_bound_schema(self) -> Self:
        properties = self.parameters.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("trigger-bound plan properties differ")
        if (
            properties.get("prior_hypothesis_disposition") != _disposition_schema(_trigger(self))
            or self.parameter_schema_hash != sha256_json(self.parameters)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("trigger-bound plan request differs")
        return self


def project_trigger_bound_self_directed_plan_request(
    base_request: ActivatedCausalPlanRequest,
) -> TriggerBoundSelfDirectedPlanRequest:
    """Project the exact initial-or-revision disposition contract."""

    source = project_self_directed_plan_request(base_request)
    parameters = copy.deepcopy(source.parameters)
    properties = parameters.get("properties")
    if not isinstance(properties, dict) or "prior_hypothesis_disposition" not in properties:
        raise RecoveryError("trigger-bound plan lacks prior disposition")
    properties["prior_hypothesis_disposition"] = _disposition_schema(_trigger(source))
    body = {
        **source.model_dump(mode="python", exclude={"schema_version", "content_hash"}),
        "schema_version": TRIGGER_BOUND_SELF_DIRECTED_PLAN_REQUEST_SCHEMA,
        "compatibility_policy_version": TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
    }
    return _hashed(TriggerBoundSelfDirectedPlanRequest, body)


def project_trigger_bound_self_directed_tool_surface(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV4,
    catalog: EligiblePlanEvidenceCatalogV4,
    state: SelfDirectedExplorationState | None,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[WorkflowToolSurfaceV2, TriggerBoundSelfDirectedPlanRequest | None]:
    """Replace only the V24 plan schema; retain its exact tool selection."""

    surface, source_request = project_self_directed_tool_surface(
        task=task,
        decision=decision,
        catalog=catalog,
        state=state,
        source_tool_schemas=source_tool_schemas,
        cross_reset_trigger=cross_reset_trigger,
    )
    request = (
        project_trigger_bound_self_directed_plan_request(source_request.source_request.base_request)
        if source_request is not None
        else None
    )
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    for schema in selected:
        if schema.get("name") in _PLAN_TOOLS:
            if request is None:
                raise RecoveryError("trigger-bound plan surface lacks its dynamic request")
            schema["parameters"] = copy.deepcopy(request.parameters)
    body = {
        **surface.model_dump(
            mode="python",
            exclude={"content_hash", "selected_tool_schema_hash"},
        ),
        "selected_tool_schemas": tuple(selected),
        "selected_tool_schema_hash": sha256_json(selected),
    }
    return _hashed(WorkflowToolSurfaceV2, body), request


def project_trigger_bound_self_directed_workflow_decision(
    *,
    base_decision: Any,
    state: SelfDirectedExplorationState | None,
    source_tool_schemas: tuple[dict[str, Any], ...],
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> WorkflowDecisionV4:
    """Count self-directed admission blocks in V25's shared one-retry slot."""

    event_tuple = tuple(events)
    decision = project_self_directed_workflow_decision(
        base_decision=base_decision,
        state=state,
        source_tool_schemas=source_tool_schemas,
        events=event_tuple,
    )
    gate_id = decision.plan_gate_id
    blocked = [
        event
        for event in event_tuple
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == "bounded-self-directed-exploration-v1"
        and event.payload.get("plan_gate_id") == gate_id
    ]
    if not blocked:
        return decision
    body = decision.model_dump(mode="python", exclude={"content_hash"})
    body.update(
        {
            "plan_admission_recovery_used": True,
            "plan_admission_recovery_remaining": 0,
        }
    )
    if len(blocked) >= 2:
        body.update(
            {
                "target": "terminal",
                "allowed_tool_names": (),
                "expected_check_id": None,
                "terminal_reason": "work_plan_admission_repeated",
                "effective_max_output_tokens": 1,
                "reasoning_effort": "low",
                "investigation_intent_required": False,
                "stop_choice_available": False,
            }
        )
    return _hashed(WorkflowDecisionV4, body)


def normalize_trigger_bound_self_directed_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    request_projection: TriggerBoundSelfDirectedPlanRequest,
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> tuple[RecordedCausalPlanV2, SelfDirectedExplorationClosureReceipt]:
    """Reuse V23 semantic admission after checking the exact V25 projection."""

    exact = project_trigger_bound_self_directed_plan_request(
        request_projection.source_request.base_request
    )
    if request_projection != exact or trigger != _trigger(request_projection):
        raise RecoveryError("trigger-bound plan request projection differs")
    source_request = project_self_directed_plan_request(
        request_projection.source_request.base_request
    )
    projected, source_receipt = normalize_self_directed_plan(
        task=task,
        catalog=catalog,
        request_projection=source_request,
        trigger=trigger,
        revision_index=revision_index,
        parent_plan_hash=parent_plan_hash,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        raw_arguments=raw_arguments,
    )
    receipt_body = source_receipt.model_dump(mode="python", exclude={"content_hash"})
    receipt_body["request_projection_hash"] = request_projection.content_hash
    return projected, _hashed(SelfDirectedExplorationClosureReceipt, receipt_body)


__all__ = [
    "TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY",
    "TRIGGER_BOUND_SELF_DIRECTED_PLAN_REQUEST_SCHEMA",
    "TriggerBoundSelfDirectedPlanRequest",
    "normalize_trigger_bound_self_directed_plan",
    "project_trigger_bound_self_directed_plan_request",
    "project_trigger_bound_self_directed_tool_surface",
    "project_trigger_bound_self_directed_workflow_decision",
]
