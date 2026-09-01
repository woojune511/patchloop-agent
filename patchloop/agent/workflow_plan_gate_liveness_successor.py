"""Pinned initial-plan liveness for a post-V20 opt-in workflow.

V20 could expose a constructible initial plan and later lose the same public
source coverage when recent-event compaction changed.  It could also return to
exploration after the first typed plan rejection.  This successor pins only a
request that was actually delivered to a model (a durable ``ModelCalled``
event exact-binds the request artifact), keeps that pin valid only for the same
run/diff/gate, and forces the one bounded plan retry before exploration can
exhaust.

The model-facing request also removes the duplicated top-level ``unknowns``
field.  ``exploration_state.unknown_dispositions[*].question`` is the sole
canonical representation; the gateway derives the recorded-plan unknown list.
No raw source body, model reasoning, private task material, hidden evaluator
data, or reference patch is retained by the pin.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    CausalMechanismHistoryEntryV2,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    EligibleCausalSourceSpan,
    RecordedCausalPlanV2,
    project_eligible_causal_source_spans,
)
from patchloop.agent.workflow_exploration_gate_activation import (
    normalize_activated_exploration_plan,
    project_activated_exploration_plan_request,
    project_exploration_workflow_tool_surface,
    workflow_instruction_v6,
)
from patchloop.agent.workflow_exploration_gate_successor import (
    ExplorationGatedCausalPlanRequest,
    ExplorationStateInput,
    PublicExplorationClosureReceipt,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    PublicSemanticProgressState,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import (
    ActiveWorkState,
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalogV2,
    PlanTrigger,
    WorkflowToolSurfaceV2,
)
from patchloop.contracts import PublicTask
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json

PLAN_GATE_LIVENESS_POLICY = "pinned-plan-gate-liveness-v1"
PLAN_GATE_READINESS_SNAPSHOT_SCHEMA = "plan-gate-readiness-snapshot-v1"
RECOVERED_PLAN_GATE_PIN_SCHEMA = "recovered-plan-gate-readiness-pin-v1"
PINNED_EVIDENCE_CATALOG_SCHEMA = "eligible-plan-evidence-catalog-v3"
PINNED_EXPLORATION_REQUEST_SCHEMA = "pinned-exploration-plan-request-v1"

_MAX_PINNED_SOURCE_SPANS = 8
_MAX_PINNED_SOURCE_EVIDENCE = 8


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _reject(reason_code: str, message: str) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


class PlanGateReadinessSnapshot(BaseModel):
    """Bounded source readiness from one exact model-visible request."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["plan-gate-readiness-snapshot-v1"]
    policy_version: Literal["pinned-plan-gate-liveness-v1"]
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_version: int = Field(ge=1)
    public_task_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_gate_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: Literal["initial"]
    source_evidence: tuple[EligiblePlanEvidence, ...] = Field(
        min_length=1,
        max_length=_MAX_PINNED_SOURCE_EVIDENCE,
    )
    source_spans: tuple[EligibleCausalSourceSpan, ...] = Field(
        min_length=2,
        max_length=_MAX_PINNED_SOURCE_SPANS,
    )
    distinct_source_coverage_keys: tuple[str, ...] = Field(min_length=2, max_length=8)
    source_evidence_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_span_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_current_diff_source_only: Literal[True]
    raw_source_body_retained: Literal[False]
    raw_reasoning_retained: Literal[False]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        evidence_ids = tuple(item.evidence_id for item in self.source_evidence)
        span_evidence_ids = tuple(
            dict.fromkeys(item.read_evidence_id for item in self.source_spans)
        )
        coverage = tuple(dict.fromkeys(item.coverage_key for item in self.source_spans))
        if (
            evidence_ids != tuple(dict.fromkeys(evidence_ids))
            or span_evidence_ids != evidence_ids
            or coverage != self.distinct_source_coverage_keys
            or any(
                item.kind != "source_read"
                or item.role != "foundation"
                or item.run_id != self.run_id
                or item.worktree_diff_hash != self.worktree_diff_hash
                for item in self.source_evidence
            )
            or any(
                item.run_id != self.run_id or item.worktree_diff_hash != self.worktree_diff_hash
                for item in self.source_spans
            )
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("plan-gate readiness snapshot differs")
        return self


class RecoveredPlanGateReadinessPin(BaseModel):
    """One readiness snapshot proven to have been sent in a completed model turn."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["recovered-plan-gate-readiness-pin-v1"]
    policy_version: Literal["pinned-plan-gate-liveness-v1"]
    snapshot: PlanGateReadinessSnapshot
    snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_model_event_sequence: int = Field(ge=1)
    source_request_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    actual_model_visible_request: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_pin(self) -> Self:
        if self.snapshot_hash != self.snapshot.content_hash or self.content_hash != sha256_json(
            self.model_dump(mode="json", exclude={"content_hash"})
        ):
            raise ValueError("recovered plan-gate pin differs")
        return self


class EligiblePlanEvidenceCatalogV3(EligiblePlanEvidenceCatalogV2):
    """V2 catalog plus bounded source evidence from one model-visible pin."""

    schema_version: Literal["eligible-plan-evidence-catalog-v3"]
    plan_gate_liveness_policy_version: Literal["pinned-plan-gate-liveness-v1"]
    plan_gate_readiness_status: Literal["not_pinned", "pinned"]
    plan_gate_readiness_pin_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    plan_gate_pinned_evidence_ids: tuple[str, ...] = Field(max_length=8)
    source_model_event_sequence: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_plan_gate_pin(self) -> Self:
        pinned = self.plan_gate_readiness_status == "pinned"
        if pinned is not (
            self.plan_gate_readiness_pin_hash is not None
            and bool(self.plan_gate_pinned_evidence_ids)
            and self.source_model_event_sequence is not None
        ):
            raise ValueError("eligible catalog plan-gate pin state differs")
        item_ids = {item.evidence_id for item in self.items}
        if any(item not in item_ids for item in self.plan_gate_pinned_evidence_ids):
            raise ValueError("eligible catalog lacks pinned source evidence")
        return self


class PinnedExplorationPlanRequest(BaseModel):
    """V20 exploration request with one canonical unknown representation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["pinned-exploration-plan-request-v1"]
    policy_version: Literal["pinned-plan-gate-liveness-v1"]
    source_request: ExplorationGatedCausalPlanRequest
    source_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_activation_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parameters: dict[str, Any]
    parameter_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    unknowns_canonical_source: Literal["exploration_state.unknown_dispositions"]
    duplicated_unknown_text_allowed: Literal[False]
    runtime_surface_activated: Literal[True]
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        source_activation = project_activated_exploration_plan_request(
            self.source_request.base_request
        )
        properties = self.parameters.get("properties")
        required = self.parameters.get("required")
        if (
            self.source_request != source_activation.source_request
            or self.source_request_hash != self.source_request.content_hash
            or self.source_activation_request_hash != source_activation.content_hash
            or self.base_request_hash != self.source_request.base_request.content_hash
            or not isinstance(properties, dict)
            or not isinstance(required, list)
            or "unknowns" in properties
            or "unknowns" in required
            or self.parameter_schema_hash != sha256_json(self.parameters)
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("pinned exploration request differs")
        return self


def _bounded_distinct_spans(
    spans: tuple[EligibleCausalSourceSpan, ...],
) -> tuple[EligibleCausalSourceSpan, ...]:
    selected: list[EligibleCausalSourceSpan] = []
    seen: set[str] = set()
    for span in spans:
        if span.coverage_key not in seen:
            selected.append(span)
            seen.add(span.coverage_key)
        if len(seen) >= 2:
            break
    if len(seen) < 2:
        return ()
    for span in spans:
        if span not in selected and len(selected) < _MAX_PINNED_SOURCE_SPANS:
            selected.append(span)
    return tuple(selected)


def project_plan_gate_readiness_snapshot(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
) -> PlanGateReadinessSnapshot | None:
    """Project initial-plan readiness only when two current source ranges exist."""

    if (
        decision.plan_gate_id is None
        or decision.active_plan_hash is not None
        or decision.revision_trigger is not None
        or catalog.run_id == ""
    ):
        return None
    try:
        source_catalog = project_eligible_causal_source_spans(task=task, catalog=catalog)
    except ContractError:
        return None
    spans = _bounded_distinct_spans(source_catalog.spans)
    if not spans:
        return None
    evidence_ids = tuple(dict.fromkeys(item.read_evidence_id for item in spans))
    evidence_by_id = {item.evidence_id: item for item in catalog.items}
    try:
        evidence = tuple(evidence_by_id[evidence_id] for evidence_id in evidence_ids)
    except KeyError as exc:
        raise RecoveryError("plan-gate source span lost its evidence") from exc
    body = {
        "schema_version": PLAN_GATE_READINESS_SNAPSHOT_SCHEMA,
        "policy_version": PLAN_GATE_LIVENESS_POLICY,
        "run_id": catalog.run_id,
        "task_id": catalog.task_id,
        "task_version": catalog.task_version,
        "public_task_hash": catalog.public_task_hash,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "plan_gate_id": decision.plan_gate_id,
        "trigger": "initial",
        "source_evidence": tuple(item.model_dump(mode="python") for item in evidence),
        "source_spans": tuple(item.model_dump(mode="python") for item in spans),
        "distinct_source_coverage_keys": tuple(dict.fromkeys(item.coverage_key for item in spans)),
        "source_evidence_catalog_hash": catalog.content_hash,
        "source_span_catalog_hash": source_catalog.content_hash,
        "public_current_diff_source_only": True,
        "raw_source_body_retained": False,
        "raw_reasoning_retained": False,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
    }
    return _hashed(PlanGateReadinessSnapshot, body)


def bind_recovered_plan_gate_pin(
    *,
    snapshot: PlanGateReadinessSnapshot,
    source_model_event_sequence: int,
    source_request_artifact_hash: str,
    source_request_body_hash: str,
) -> RecoveredPlanGateReadinessPin:
    body = {
        "schema_version": RECOVERED_PLAN_GATE_PIN_SCHEMA,
        "policy_version": PLAN_GATE_LIVENESS_POLICY,
        "snapshot": snapshot.model_dump(mode="python"),
        "snapshot_hash": snapshot.content_hash,
        "source_model_event_sequence": source_model_event_sequence,
        "source_request_artifact_hash": source_request_artifact_hash,
        "source_request_body_hash": source_request_body_hash,
        "actual_model_visible_request": True,
    }
    return _hashed(RecoveredPlanGateReadinessPin, body)


def project_pinned_evidence_catalog(
    *,
    base: EligiblePlanEvidenceCatalogV2,
    pin: RecoveredPlanGateReadinessPin | None,
) -> EligiblePlanEvidenceCatalogV3:
    items = list(base.items)
    pinned_ids: tuple[str, ...] = ()
    if pin is not None:
        snapshot = pin.snapshot
        if (
            snapshot.run_id != base.run_id
            or snapshot.task_id != base.task_id
            or snapshot.task_version != base.task_version
            or snapshot.public_task_hash != base.public_task_hash
            or snapshot.worktree_diff_hash != base.worktree_diff_hash
        ):
            raise RecoveryError("plan-gate pin is stale or foreign")
        by_sequence = {item.canonical_event_sequence: item for item in items}
        for item in snapshot.source_evidence:
            prior = by_sequence.get(item.canonical_event_sequence)
            if prior is not None and prior != item:
                raise RecoveryError("plan-gate pinned evidence conflicts with current evidence")
            by_sequence[item.canonical_event_sequence] = item
        items = [by_sequence[key] for key in sorted(by_sequence)]
        pinned_ids = tuple(item.evidence_id for item in snapshot.source_evidence)
    body = {
        **base.model_dump(mode="python", exclude={"schema_version", "content_hash"}),
        "schema_version": PINNED_EVIDENCE_CATALOG_SCHEMA,
        "items": tuple(item.model_dump(mode="python") for item in items),
        "plan_gate_liveness_policy_version": PLAN_GATE_LIVENESS_POLICY,
        "plan_gate_readiness_status": "pinned" if pin is not None else "not_pinned",
        "plan_gate_readiness_pin_hash": pin.content_hash if pin is not None else None,
        "plan_gate_pinned_evidence_ids": pinned_ids,
        "source_model_event_sequence": (
            pin.source_model_event_sequence if pin is not None else None
        ),
    }
    return _hashed(EligiblePlanEvidenceCatalogV3, body)


def project_pinned_plan_gate_decision(
    *,
    decision: WorkflowDecisionV3,
    readiness: PlanGateReadinessSnapshot | None,
    pin: RecoveredPlanGateReadinessPin | None,
) -> WorkflowDecisionV3:
    """Force the initial plan and its one recovery attempt once ready."""

    selected = pin.snapshot if pin is not None else readiness
    if selected is None:
        return decision
    if (
        decision.plan_gate_id != selected.plan_gate_id
        or decision.current_diff_hash != selected.worktree_diff_hash
    ):
        raise RecoveryError("plan-gate readiness does not bind the current decision")
    if decision.terminal_reason == "work_plan_admission_repeated":
        return decision
    if decision.active_plan_hash is not None or decision.revision_trigger is not None:
        return decision
    body = decision.model_dump(mode="python", exclude={"content_hash"})
    body.update(
        {
            "target": "record-work-plan",
            "allowed_tool_names": ("record_work_plan",),
            "expected_check_id": None,
            "terminal_reason": None,
            "effective_max_output_tokens": min(decision.configured_max_output_tokens, 8_192),
            "reasoning_effort": "medium",
        }
    )
    return _hashed(WorkflowDecisionV3, body)


def project_pinned_exploration_plan_request(
    base_request: Any,
) -> PinnedExplorationPlanRequest:
    source_activation = project_activated_exploration_plan_request(base_request)
    parameters = copy.deepcopy(source_activation.parameters)
    properties = parameters.get("properties")
    required = parameters.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise RecoveryError("exploration plan parameter schema differs")
    if "unknowns" not in properties or "unknowns" not in required:
        raise RecoveryError("exploration plan lacks its duplicated unknown field")
    properties.pop("unknowns")
    required.remove("unknowns")
    disposition = (
        properties.get("exploration_state", {})
        .get("properties", {})
        .get("unknown_dispositions", {})
    )
    if isinstance(disposition, dict):
        disposition["description"] = (
            "Each item declares and resolves one unknown. Its question is the sole "
            "canonical unknown text; do not duplicate it elsewhere."
        )
    body = {
        "schema_version": PINNED_EXPLORATION_REQUEST_SCHEMA,
        "policy_version": PLAN_GATE_LIVENESS_POLICY,
        "source_request": source_activation.source_request.model_dump(mode="python"),
        "source_request_hash": source_activation.source_request_hash,
        "source_activation_request_hash": source_activation.content_hash,
        "base_request_hash": source_activation.base_request_hash,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
        "unknowns_canonical_source": "exploration_state.unknown_dispositions",
        "duplicated_unknown_text_allowed": False,
        "runtime_surface_activated": True,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(PinnedExplorationPlanRequest, body)


def project_pinned_plan_gate_tool_surface(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV3,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[WorkflowToolSurfaceV2, PinnedExplorationPlanRequest | None]:
    surface, source_request = project_exploration_workflow_tool_surface(
        task=task,
        decision=decision,
        catalog=catalog,
        source_tool_schemas=source_tool_schemas,
        cross_reset_trigger=cross_reset_trigger,
    )
    if source_request is None:
        return surface, None
    request = project_pinned_exploration_plan_request(source_request.source_request.base_request)
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    plan = [
        item for item in selected if item.get("name") in {"record_work_plan", "revise_work_plan"}
    ]
    if len(plan) != 1:
        raise RecoveryError("pinned plan-gate tool surface differs")
    plan[0]["parameters"] = copy.deepcopy(request.parameters)
    plan[0]["description"] = (
        "Record the forced public causal plan. Declare each unknown exactly once in "
        "exploration_state.unknown_dispositions."
    )
    body = {
        **surface.model_dump(mode="python", exclude={"content_hash", "selected_tool_schema_hash"}),
        "selected_tool_schemas": tuple(selected),
        "selected_tool_schema_hash": sha256_json(selected),
    }
    return _hashed(WorkflowToolSurfaceV2, body), request


def normalize_pinned_exploration_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalogV3,
    request_projection: PinnedExplorationPlanRequest,
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> tuple[RecordedCausalPlanV2, PublicExplorationClosureReceipt]:
    exact = project_pinned_exploration_plan_request(request_projection.source_request.base_request)
    if request_projection != exact:
        raise RecoveryError("pinned exploration plan request projection differs")
    if "unknowns" in raw_arguments:
        _reject(
            "plan_gate_unknown_text_duplicated",
            "unknown text must be represented only by unknown dispositions",
        )
    state_raw = raw_arguments.get("exploration_state")
    try:
        state = ExplorationStateInput.model_validate(state_raw)
    except ValueError as exc:
        _reject("exploration_plan_input_shape_invalid", "exploration plan input differs")
        raise AssertionError from exc
    questions = [item.question for item in state.unknown_dispositions]
    if len(questions) != len(set(questions)):
        _reject("plan_gate_unknown_question_repeated", "unknown disposition questions repeat")
    normalized = {**raw_arguments, "unknowns": questions}
    source_activation = project_activated_exploration_plan_request(
        request_projection.source_request.base_request
    )
    return normalize_activated_exploration_plan(
        task=task,
        catalog=catalog,
        request_projection=source_activation,
        trigger=trigger,
        revision_index=revision_index,
        parent_plan_hash=parent_plan_hash,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        raw_arguments=normalized,
    )


def workflow_instruction_v7(
    decision: WorkflowDecisionV3,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV3,
    active_work_state: ActiveWorkState | None,
    semantic_progress_state: PublicSemanticProgressState | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    request_projection: PinnedExplorationPlanRequest | None,
    readiness: PlanGateReadinessSnapshot | None,
    recovered_pin: RecoveredPlanGateReadinessPin | None,
) -> dict[str, Any]:
    base = workflow_instruction_v6(
        decision,
        public_task_spec=public_task_spec,
        catalog=catalog,
        active_work_state=active_work_state,
        semantic_progress_state=semantic_progress_state,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        request_projection=request_projection,  # compatible request projection shape
    )
    body = {
        **{key: value for key, value in base.items() if key != "content_hash"},
        "plan_gate_liveness_policy_version": PLAN_GATE_LIVENESS_POLICY,
        "plan_gate_readiness_snapshot": (
            readiness.model_dump(mode="json") if readiness is not None else None
        ),
        "plan_gate_readiness_snapshot_hash": (
            readiness.content_hash if readiness is not None else sha256_json(None)
        ),
        "recovered_plan_gate_pin": (
            recovered_pin.model_dump(mode="json") if recovered_pin is not None else None
        ),
        "recovered_plan_gate_pin_hash": (
            recovered_pin.content_hash if recovered_pin is not None else sha256_json(None)
        ),
    }
    if request_projection is not None:
        body["instruction"] = (
            "The initial plan gate is ready and forced. Use only request-enumerated public "
            "IDs, declare each unknown exactly once in unknown_dispositions, and submit "
            "record_work_plan now."
        )
    return {**body, "content_hash": sha256_json(body)}


__all__ = [
    "EligiblePlanEvidenceCatalogV3",
    "PINNED_EVIDENCE_CATALOG_SCHEMA",
    "PINNED_EXPLORATION_REQUEST_SCHEMA",
    "PLAN_GATE_LIVENESS_POLICY",
    "PlanGateReadinessSnapshot",
    "PinnedExplorationPlanRequest",
    "RecoveredPlanGateReadinessPin",
    "bind_recovered_plan_gate_pin",
    "normalize_pinned_exploration_plan",
    "project_pinned_evidence_catalog",
    "project_pinned_exploration_plan_request",
    "project_pinned_plan_gate_decision",
    "project_pinned_plan_gate_tool_surface",
    "project_plan_gate_readiness_snapshot",
    "workflow_instruction_v7",
]
