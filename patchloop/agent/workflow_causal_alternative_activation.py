"""Runtime-neutral activation primitives for the public causal-alternative gate.

The gateway owns worktree restoration.  The model only receives one bounded
cross-reset failure trigger and current-baseline public source evidence.  This
module deliberately contains no provider, sandbox, evaluator, or task-private
access.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
    CausalMechanismHistoryEntry,
    MutationBaselineProjection,
    MutationBaselineRestoreReceipt,
    PublicCausalMechanism,
    RecordedCausalAlternativePlan,
    project_causal_alternative_input_contract,
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
    EligiblePlanEvidenceCatalog,
    EligiblePlanEvidenceCatalogV2,
    RecordedWorkPlanV2,
    WorkflowToolSurfaceV2,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json

CAUSAL_ACTIVATION_POLICY = "gateway-owned-causal-baseline-reset-v1"
CAUSAL_PLAN_BINDING_SCHEMA = "causal-work-plan-binding-v1"
CROSS_RESET_TRIGGER_SCHEMA = "cross-reset-public-failure-trigger-v1"
RESTORE_PREPARED_EVENT_SCHEMA = "mutation-baseline-restore-prepared-v1"
RESTORE_COMPLETED_EVENT_SCHEMA = "mutation-baseline-restored-v1"
CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA = "lean-workflow-instruction-v4"


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


class CrossResetFailureTrigger(BaseModel):
    """Bounded public observation kept across an exact worktree restore."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["cross-reset-public-failure-trigger-v1"]
    policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    run_id: str = Field(min_length=1)
    check_id: str = Field(min_length=1)
    failure_signature: str = Field(min_length=1, max_length=1_000)
    failure_signature_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    failure_event_sequences: tuple[int, ...] = Field(min_length=2, max_length=4)
    failed_diff_hashes: tuple[str, ...] = Field(min_length=2, max_length=4)
    source_semantic_progress_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mutation_baseline_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mutation_baseline_restore_receipt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    restored_baseline_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    restored_event_sequence: int = Field(ge=1)
    public_check_output_only: Literal[True]
    stale_check_authorizes_mutation: Literal[False]
    current_source_read_required: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_trigger(self) -> Self:
        if (
            len(self.failure_event_sequences) != len(self.failed_diff_hashes)
            or tuple(sorted(set(self.failure_event_sequences))) != self.failure_event_sequences
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("cross-reset failure trigger differs")
        return self


class CausalWorkPlanBinding(BaseModel):
    """Companion binding from one ordinary work-plan hash to its causal model."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["causal-work-plan-binding-v1"]
    policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    run_id: str = Field(min_length=1)
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_event_sequence: int = Field(ge=1)
    revision_index: int = Field(ge=0, le=3)
    parent_plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: Literal["initial", "check_failure", "review_correction"]
    mechanism: PublicCausalMechanism
    causal_alternative_plan: RecordedCausalAlternativePlan | None = None
    cross_reset_failure_trigger_hash: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_binding(self) -> Self:
        alternative = self.causal_alternative_plan
        if self.revision_index == 0:
            if self.parent_plan_hash is not None or self.trigger != "initial":
                raise ValueError("initial causal plan binding differs")
        elif self.parent_plan_hash is None or self.trigger == "initial":
            raise ValueError("causal plan revision binding differs")
        if (alternative is None) is not (self.cross_reset_failure_trigger_hash is None):
            raise ValueError("causal alternative trigger binding differs")
        if alternative is not None and (
            alternative.revision_index != self.revision_index
            or alternative.parent_plan_hash != self.parent_plan_hash
            or alternative.alternative_causal_mechanism != self.mechanism
        ):
            raise ValueError("causal alternative companion differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("causal work-plan binding hash differs")
        return self


def build_cross_reset_failure_trigger(
    *,
    state: PublicSemanticProgressState,
    baseline: MutationBaselineProjection,
    receipt: MutationBaselineRestoreReceipt,
    restored_event_sequence: int,
) -> CrossResetFailureTrigger:
    if (
        baseline.semantic_progress_state_hash != state.content_hash
        or receipt.baseline_projection_hash != baseline.content_hash
        or receipt.observed_after_diff_hash != baseline.baseline_diff_hash
        or receipt.preserved_failure_event_sequences != state.failure_event_sequences
    ):
        raise RecoveryError("cross-reset trigger inputs differ")
    body = {
        "schema_version": CROSS_RESET_TRIGGER_SCHEMA,
        "policy_version": CAUSAL_ACTIVATION_POLICY,
        "run_id": state.run_id,
        "check_id": state.check_id,
        "failure_signature": state.failure_signature,
        "failure_signature_hash": state.failure_signature_hash,
        "failure_event_sequences": state.failure_event_sequences,
        "failed_diff_hashes": state.failed_diff_hashes,
        "source_semantic_progress_state_hash": state.content_hash,
        "mutation_baseline_projection_hash": baseline.content_hash,
        "mutation_baseline_restore_receipt_hash": receipt.content_hash,
        "restored_baseline_diff_hash": baseline.baseline_diff_hash,
        "restored_event_sequence": restored_event_sequence,
        "public_check_output_only": True,
        "stale_check_authorizes_mutation": False,
        "current_source_read_required": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(CrossResetFailureTrigger, body)


def cross_reset_epoch_events(events: tuple[RunEvent, ...] | list[RunEvent]) -> tuple[RunEvent, ...]:
    """Return the append-only suffix after the latest completed restore."""

    event_tuple = tuple(events)
    restored = [
        event for event in event_tuple if event.type == EventType.MUTATION_BASELINE_RESTORED
    ]
    if not restored:
        return event_tuple
    latest = restored[-1]
    return tuple(event for event in event_tuple if event.sequence > latest.sequence)


def project_active_cross_reset_trigger(
    *,
    run_id: str,
    current_diff_hash: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> CrossResetFailureTrigger | None:
    event_tuple = tuple(events)
    completed = [
        event for event in event_tuple if event.type == EventType.MUTATION_BASELINE_RESTORED
    ]
    if not completed:
        return None
    event = completed[-1]
    try:
        trigger = CrossResetFailureTrigger.model_validate_json(
            canonical_json(event.payload.get("trigger"))
        )
        baseline = MutationBaselineProjection.model_validate_json(
            canonical_json(event.payload.get("baseline_projection"))
        )
        receipt = MutationBaselineRestoreReceipt.model_validate_json(
            canonical_json(event.payload.get("restore_receipt"))
        )
        semantic_state = PublicSemanticProgressState.model_validate_json(
            canonical_json(event.payload.get("semantic_progress_state"))
        )
    except ValueError as exc:
        raise RecoveryError("completed causal restore evidence is invalid") from exc
    if (
        event.run_id != run_id
        or trigger.run_id != run_id
        or trigger.restored_event_sequence != event.sequence
        or trigger.mutation_baseline_projection_hash != baseline.content_hash
        or trigger.mutation_baseline_restore_receipt_hash != receipt.content_hash
        or trigger.source_semantic_progress_state_hash != semantic_state.content_hash
        or event.payload.get("trigger_hash") != trigger.content_hash
        or event.payload.get("baseline_projection_hash") != baseline.content_hash
        or event.payload.get("restore_receipt_hash") != receipt.content_hash
        or event.payload.get("semantic_progress_state_hash") != semantic_state.content_hash
    ):
        raise RecoveryError("completed causal restore binding differs")
    later_mutation = any(
        candidate.sequence > event.sequence and candidate.type == EventType.PATCH_APPLIED
        for candidate in event_tuple
    )
    if later_mutation:
        return None
    if current_diff_hash != trigger.restored_baseline_diff_hash:
        raise RecoveryError("active cross-reset trigger worktree differs")
    return trigger


def project_cross_reset_semantic_progress_state(
    *,
    run_id: str,
    trigger: CrossResetFailureTrigger,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> PublicSemanticProgressState:
    """Recover the exact pre-restore public failure state pinned by a trigger."""

    event = next(
        (
            item
            for item in events
            if item.sequence == trigger.restored_event_sequence
            and item.type == EventType.MUTATION_BASELINE_RESTORED
        ),
        None,
    )
    if event is None or event.run_id != run_id:
        raise RecoveryError("cross-reset semantic state event is unavailable")
    try:
        state = PublicSemanticProgressState.model_validate_json(
            canonical_json(event.payload.get("semantic_progress_state"))
        )
    except ValueError as exc:
        raise RecoveryError("cross-reset semantic state is invalid") from exc
    if (
        state.run_id != run_id
        or state.content_hash != trigger.source_semantic_progress_state_hash
        or state.check_id != trigger.check_id
        or state.failure_signature_hash != trigger.failure_signature_hash
        or state.failure_event_sequences != trigger.failure_event_sequences
        or state.failed_diff_hashes != trigger.failed_diff_hashes
        or not state.semantic_reset_required
    ):
        raise RecoveryError("cross-reset semantic state binding differs")
    return state


def build_causal_work_plan_binding(
    *,
    plan: RecordedWorkPlanV2,
    plan_event_sequence: int,
    mechanism: PublicCausalMechanism,
    alternative_plan: RecordedCausalAlternativePlan | None = None,
    cross_reset_trigger_hash: str | None = None,
) -> CausalWorkPlanBinding:
    if (
        mechanism.run_id != plan.run_id
        or mechanism.worktree_diff_hash != plan.worktree_diff_hash
        or not set(mechanism.source_evidence_ids).issubset(
            {item.evidence_id for item in plan.foundation_evidence}
        )
    ):
        raise ContractError("causal mechanism does not bind the recorded work plan")
    body = {
        "schema_version": CAUSAL_PLAN_BINDING_SCHEMA,
        "policy_version": CAUSAL_ACTIVATION_POLICY,
        "run_id": plan.run_id,
        "plan_hash": plan.content_hash,
        "plan_event_sequence": plan_event_sequence,
        "revision_index": plan.revision_index,
        "parent_plan_hash": plan.parent_plan_hash,
        "trigger": plan.trigger,
        "mechanism": mechanism.model_dump(mode="python"),
        "causal_alternative_plan": (
            alternative_plan.model_dump(mode="python") if alternative_plan is not None else None
        ),
        "cross_reset_failure_trigger_hash": cross_reset_trigger_hash,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(CausalWorkPlanBinding, body)


def project_causal_mechanism_history(
    *,
    run_id: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> tuple[CausalMechanismHistoryEntry, ...]:
    event_tuple = tuple(events)
    plan_events = {
        event.sequence: event for event in event_tuple if event.type == EventType.PLAN_RECORDED
    }
    bindings: list[CausalWorkPlanBinding] = []
    for event in event_tuple:
        if event.type != EventType.CAUSAL_MECHANISM_RECORDED:
            continue
        try:
            binding = CausalWorkPlanBinding.model_validate_json(
                canonical_json(event.payload.get("binding"))
            )
        except ValueError as exc:
            raise RecoveryError("causal work-plan binding event is invalid") from exc
        plan_event = plan_events.get(binding.plan_event_sequence)
        if (
            event.run_id != run_id
            or binding.run_id != run_id
            or event.payload.get("binding_hash") != binding.content_hash
            or plan_event is None
            or plan_event.payload.get("plan_hash") != binding.plan_hash
            or plan_event.payload.get("revision_index") != binding.revision_index
            or plan_event.payload.get("parent_plan_hash") != binding.parent_plan_hash
            or plan_event.payload.get("trigger") != binding.trigger
        ):
            raise RecoveryError("causal work-plan event binding differs")
        bindings.append(binding)
    if not bindings:
        return ()
    if len(bindings) > 4:
        raise RecoveryError("causal mechanism history exceeds the correction envelope")
    for prior, current in zip(bindings, bindings[1:], strict=False):
        if (
            current.revision_index != prior.revision_index + 1
            or current.parent_plan_hash != prior.plan_hash
        ):
            raise RecoveryError("causal mechanism history chain differs")
    return tuple(
        CausalMechanismHistoryEntry(
            revision_index=item.revision_index,
            plan_hash=item.plan_hash,
            parent_plan_hash=item.parent_plan_hash,
            trigger=item.trigger,
            mechanism=item.mechanism,
        )
        for item in bindings
    )


def standard_plan_from_causal_alternative(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    alternative: RecordedCausalAlternativePlan,
) -> RecordedWorkPlanV2:
    if (
        alternative.run_id != catalog.run_id
        or alternative.task_id != task.task_id
        or alternative.task_version != task.task_version
        or alternative.public_task_hash != catalog.public_task_hash
        or alternative.worktree_diff_hash != catalog.worktree_diff_hash
    ):
        raise ContractError("causal alternative standard-plan binding differs")
    body = {
        "schema_version": "recorded-work-plan-v2",
        "run_id": alternative.run_id,
        "task_id": alternative.task_id,
        "task_version": alternative.task_version,
        "public_task_hash": alternative.public_task_hash,
        "worktree_diff_hash": alternative.worktree_diff_hash,
        "observation_status": alternative.observation_status,
        "hypothesis": alternative.hypothesis,
        "foundation_evidence": tuple(
            item.model_dump(mode="python") for item in alternative.foundation_evidence
        ),
        "supporting_evidence": tuple(
            item.model_dump(mode="python") for item in alternative.supporting_evidence
        ),
        "candidate_files": tuple(
            CandidateFileEvidence(
                path=item.path,
                read_evidence_id=item.read_evidence_id,
            ).model_dump(mode="python")
            for item in alternative.candidate_files
        ),
        "intended_change": alternative.intended_change,
        "expected_behavior": alternative.expected_behavior,
        "unknowns": alternative.unknowns,
        "planned_check_ids": alternative.planned_check_ids,
        "evidence_catalog_hash": alternative.evidence_catalog_hash,
        "revision_index": alternative.revision_index,
        "parent_plan_hash": alternative.parent_plan_hash,
        "trigger": "check_failure",
        "trigger_check_id": alternative.trigger_check_id,
        "trigger_event_sequence": alternative.trigger_failure_event_sequences[-1],
        "prior_hypothesis_disposition": "rejected",
        "public_evidence_only": True,
        "hidden_evidence_used": False,
        "private_evidence_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(RecordedWorkPlanV2, body)


def causal_plan_binding_for_hash(
    *,
    run_id: str,
    plan_hash: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> CausalWorkPlanBinding | None:
    matches = []
    for event in events:
        if event.type != EventType.CAUSAL_MECHANISM_RECORDED:
            continue
        try:
            binding = CausalWorkPlanBinding.model_validate_json(
                canonical_json(event.payload.get("binding"))
            )
        except ValueError as exc:
            raise RecoveryError("causal work-plan binding event is invalid") from exc
        if binding.run_id == run_id and binding.plan_hash == plan_hash:
            matches.append(binding)
    if len(matches) > 1:
        raise RecoveryError("causal work-plan binding repeats")
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


def causal_reset_gate_id(trigger: CrossResetFailureTrigger, parent_plan_hash: str) -> str:
    return sha256_json(
        {
            "schema_version": "cross-reset-causal-plan-gate-v1",
            "trigger_hash": trigger.content_hash,
            "parent_plan_hash": parent_plan_hash,
            "baseline_diff_hash": trigger.restored_baseline_diff_hash,
        }
    )


def project_causal_reset_decision(
    *,
    base_decision: WorkflowDecisionV3,
    semantic_progress_state: PublicSemanticProgressState,
    trigger: CrossResetFailureTrigger,
    history: tuple[CausalMechanismHistoryEntry, ...],
    events: tuple[RunEvent, ...] | list[RunEvent],
    accepted_plan_hash: str | None,
) -> WorkflowDecisionV3:
    if (
        not history
        or trigger.source_semantic_progress_state_hash != semantic_progress_state.content_hash
    ):
        raise RecoveryError("cross-reset decision history differs")
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
            "causal alternative admission failed twice",
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
            "causal alternative evidence acquisition was exhausted",
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


def _causal_mechanism_schema(catalog: EligiblePlanEvidenceCatalog) -> dict[str, Any]:
    source_items = [
        item
        for item in catalog.items
        if item.kind == "source_read" and item.role == "foundation" and item.source is not None
    ]
    if not source_items:
        raise ContractError("causal work-plan schema lacks current public source evidence")
    source_ids = [item.evidence_id for item in source_items]
    paths = sorted({item.source.path for item in source_items if item.source is not None})
    location = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "enum": paths},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
            "read_evidence_id": {"type": "string", "enum": source_ids},
            "symbol": {"type": ["string", "null"], "minLength": 1, "maxLength": 300},
        },
        "required": ["path", "start_line", "end_line", "read_evidence_id", "symbol"],
        "additionalProperties": False,
    }
    step = {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": [
                    "causal_boundary",
                    "intermediate",
                    "mutation_site",
                    "boundary_and_mutation_site",
                ],
            },
            "location": location,
            "observation": {"type": "string", "minLength": 1, "maxLength": 1_000},
            "relationship_to_next": {
                "type": ["string", "null"],
                "minLength": 1,
                "maxLength": 1_000,
            },
        },
        "required": ["role", "location", "observation", "relationship_to_next"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "minLength": 1, "maxLength": 2_000},
            "causal_path": {"type": "array", "minItems": 1, "maxItems": 8, "items": step},
            "mutation_site_rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2_000,
            },
            "expected_observable_effect": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2_000,
            },
            "falsification_condition": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2_000,
            },
        },
        "required": [
            "summary",
            "causal_path",
            "mutation_site_rationale",
            "expected_observable_effect",
            "falsification_condition",
        ],
        "additionalProperties": False,
    }


def project_causal_workflow_tool_surface(
    *,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
    source_tool_schemas: tuple[dict[str, Any], ...],
    trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntry, ...],
) -> WorkflowToolSurfaceV2:
    surface = project_workflow_tool_surface_v3(
        decision=decision,
        catalog=catalog,
        source_tool_schemas=source_tool_schemas,
    )
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    for schema in selected:
        if schema.get("name") not in {"record_work_plan", "revise_work_plan"}:
            continue
        if trigger is not None:
            if not history or schema.get("name") != "revise_work_plan":
                raise ContractError("cross-reset causal plan surface differs")
            contract = project_causal_alternative_input_contract(
                catalog=catalog,
                prior_causal_mechanism_hash=history[-1].mechanism.content_hash,
            )
            schema["parameters"] = copy.deepcopy(contract.parameters)
            schema["description"] = (
                "Record one current-baseline causal alternative. Cite only current public source "
                "evidence and move to a non-exhausted causal boundary; the stale failed check is "
                "a pinned observation, not mutation authority."
            )
        else:
            properties = schema["parameters"]["properties"]
            properties["causal_mechanism"] = _causal_mechanism_schema(catalog)
            schema["parameters"]["required"].append("causal_mechanism")
    body = {
        **surface.model_dump(mode="python", exclude={"content_hash", "selected_tool_schema_hash"}),
        "selected_tool_schemas": tuple(selected),
        "selected_tool_schema_hash": sha256_json(selected),
    }
    return _hashed(WorkflowToolSurfaceV2, body)


def workflow_instruction_v4(
    decision: WorkflowDecisionV3,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV2,
    active_work_state: ActiveWorkState | None,
    semantic_progress_state: PublicSemanticProgressState | None,
    trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntry, ...],
) -> dict[str, Any]:
    base = workflow_instruction_v3(
        decision,
        public_task_spec=public_task_spec,
        catalog=catalog,
        active_work_state=active_work_state,
        semantic_progress_state=semantic_progress_state,
    )
    body = {
        **{key: value for key, value in base.items() if key != "content_hash"},
        "schema_version": CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA,
        "cross_reset_failure_trigger": trigger.model_dump(mode="json") if trigger else None,
        "causal_mechanism_history": [item.model_dump(mode="json") for item in history],
        "causal_mechanism_history_hash": sha256_json(
            [item.model_dump(mode="json") for item in history]
        ),
    }
    if trigger is not None:
        body["instruction"] = (
            "The exact failed mutation family was restored by the gateway. Treat the pinned "
            "failure only as an observation. Inspect current-baseline public source, then record "
            "a falsifiable plan at a non-exhausted causal boundary before editing."
        )
    elif decision.target in {"record-work-plan", "revise-work-plan"}:
        body["instruction"] = (
            "Record the bounded public plan and its generic causal_path. Every causal location "
            "must be fully covered by a cited current-diff source read."
        )
    return {**body, "content_hash": sha256_json(body)}


__all__ = [
    "CAUSAL_ACTIVATION_POLICY",
    "CAUSAL_PLAN_BINDING_SCHEMA",
    "CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA",
    "CROSS_RESET_TRIGGER_SCHEMA",
    "RESTORE_COMPLETED_EVENT_SCHEMA",
    "RESTORE_PREPARED_EVENT_SCHEMA",
    "CausalWorkPlanBinding",
    "CrossResetFailureTrigger",
    "build_causal_work_plan_binding",
    "build_cross_reset_failure_trigger",
    "causal_plan_binding_for_hash",
    "causal_reset_gate_id",
    "cross_reset_epoch_events",
    "project_active_cross_reset_trigger",
    "project_cross_reset_semantic_progress_state",
    "project_causal_mechanism_history",
    "project_causal_reset_decision",
    "project_causal_workflow_tool_surface",
    "standard_plan_from_causal_alternative",
    "workflow_instruction_v4",
]
