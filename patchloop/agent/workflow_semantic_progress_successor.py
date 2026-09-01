"""Lean V15 public failure-signature and semantic no-progress policy.

This successor is deliberately generic.  It records only a bounded signature
already exposed by a registered public check, detects the same signature across
distinct diffs, and forces a bounded hypothesis reset before another edit.  It
does not inspect task fixtures, evaluator data, reference patches, or reasoning.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.phases import EvidenceState
from patchloop.agent.workflow_successor_v2 import (
    ActiveWorkState,
    EligiblePlanEvidenceCatalogV2,
    WorkflowDecisionV2,
    WorkflowToolSurfaceV2,
    project_workflow_successor_v2,
    project_workflow_tool_surface_v2,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError
from patchloop.util import sha256_json, sha256_text

SEMANTIC_PROGRESS_SCHEMA = "public-semantic-progress-state-v1"
WORKFLOW_DECISION_SCHEMA_V3 = "lean-workflow-decision-v3"
WORKFLOW_INSTRUCTION_SCHEMA_V3 = "lean-workflow-instruction-v3"
WORKFLOW_POLICY_V15 = "public-failure-signature-no-progress-reset-v1"
RUNTIME_POLICY_V15 = "lean-harness-v15"
_INFO_TOOLS = frozenset({"search_files", "read_file"})


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


class PublicSemanticProgressState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-semantic-progress-state-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    check_id: str = Field(min_length=1)
    current_failure_event_sequence: int = Field(ge=1)
    failure_signature: str = Field(min_length=1, max_length=1_000)
    failure_signature_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    same_signature_failed_diff_count: int = Field(ge=1, le=4)
    failure_event_sequences: tuple[int, ...] = Field(min_length=1, max_length=4)
    failed_diff_hashes: tuple[str, ...] = Field(min_length=1, max_length=4)
    semantic_reset_required: bool
    public_check_output_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_progress(self) -> Self:
        if self.failure_signature_hash != sha256_text(self.failure_signature):
            raise ValueError("semantic progress signature hash differs")
        if (
            self.current_failure_event_sequence != self.failure_event_sequences[-1]
            or len(self.failure_event_sequences) != self.same_signature_failed_diff_count
            or len(self.failed_diff_hashes) != self.same_signature_failed_diff_count
            or len(set(self.failure_event_sequences)) != len(self.failure_event_sequences)
            or len(set(self.failed_diff_hashes)) != len(self.failed_diff_hashes)
            or tuple(sorted(self.failure_event_sequences)) != self.failure_event_sequences
        ):
            raise ValueError("semantic progress streak differs")
        if self.semantic_reset_required is not (self.same_signature_failed_diff_count >= 2):
            raise ValueError("semantic progress reset decision differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("semantic progress state hash differs")
        return self


class WorkflowDecisionV3(WorkflowDecisionV2):
    schema_version: Literal["lean-workflow-decision-v3"]
    runtime_policy_version: Literal["lean-harness-v15"]
    policy_version: Literal["public-failure-signature-no-progress-reset-v1"]
    terminal_reason: (
        Literal[
            "correction_attempt_limit",
            "pre_mutation_evidence_exhausted",
            "work_plan_admission_repeated",
            "required_workflow_evidence_unavailable",
            "semantic_no_progress_evidence_exhausted",
            "semantic_no_progress_revision_invalid",
        ]
        | None
    )
    semantic_progress_state_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_reset_required: bool
    required_prior_hypothesis_disposition: Literal["rejected"] | None

    @model_validator(mode="after")
    def validate_semantic_decision(self) -> Self:
        if self.semantic_progress_state_hash is None:
            if (
                self.semantic_reset_required
                or self.required_prior_hypothesis_disposition is not None
            ):
                raise ValueError("semantic progress absent decision differs")
        elif self.semantic_reset_required is not (
            self.required_prior_hypothesis_disposition == "rejected"
        ):
            raise ValueError("semantic progress disposition requirement differs")
        return self


def _failure_signature(event: RunEvent) -> str:
    summary = event.payload.get("failure_summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ContractError("public failed check lacks a bounded failure summary")
    lines = [line.strip() for line in summary.replace("\r\n", "\n").split("\n") if line.strip()]
    if not lines:
        raise ContractError("public failed check failure summary is empty")
    return lines[-1][-1_000:]


def current_public_failure_event_sequence(
    *,
    run_id: str,
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> int | None:
    """Return the current-diff failed visible-check event, even after revision.

    V14's trigger helper deliberately returns ``None`` once a matching plan
    revision exists.  Semantic progress is different: the same failed outcome
    remains the current public observation until a successful mutation
    invalidates it.  This projector therefore binds only to the latest
    completed outcome for the next visible check after the current mutation.
    """

    event_tuple = tuple(events)
    if any(type(event) is not RunEvent or event.run_id != run_id for event in event_tuple):
        raise ContractError("semantic progress event run binding differs")
    if not evidence.mutation_present:
        return None
    expected_check = next(
        (check.id for check in task.visible_checks if check.id not in evidence.completed_checks),
        None,
    )
    if expected_check is None:
        return None
    mutation_sequence = evidence.mutation_event_sequence or 0
    outcomes = [
        event
        for event in event_tuple
        if event.sequence > mutation_sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("check_id") == expected_check
        and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
        and event.payload.get("status") == "succeeded"
        and event.payload.get("invocation_status") == "completed"
        and event.payload.get("behavior_status") in {"passed", "failed"}
    ]
    if not outcomes:
        return None
    current = outcomes[-1]
    if current.payload.get("behavior_status") == "passed":
        return None
    if not (
        current.payload.get("passed") is False
        and current.payload.get("timed_out") is False
        and isinstance(current.payload.get("result_artifact"), dict)
    ):
        raise ContractError("semantic progress current failure binding differs")
    return current.sequence


def project_public_semantic_progress_state(
    *,
    run_id: str,
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...] | list[RunEvent],
    current_failure_event_sequence: int | None,
) -> PublicSemanticProgressState | None:
    """Project the consecutive same-signature streak for the current public check."""

    if current_failure_event_sequence is None:
        return None
    event_tuple = tuple(events)
    if any(type(event) is not RunEvent or event.run_id != run_id for event in event_tuple):
        raise ContractError("semantic progress event run binding differs")
    current = next(
        (event for event in event_tuple if event.sequence == current_failure_event_sequence),
        None,
    )
    check_order = tuple(check.id for check in task.visible_checks)
    if not (
        current is not None
        and current.type == EventType.TOOL_SUCCEEDED
        and current.payload.get("tool") == "run_check"
        and current.payload.get("status") == "succeeded"
        and current.payload.get("invocation_status") == "completed"
        and current.payload.get("behavior_status") == "failed"
        and current.payload.get("passed") is False
        and current.payload.get("timed_out") is False
        and current.payload.get("check_id") in check_order
        and current.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
        and isinstance(current.payload.get("result_artifact"), dict)
    ):
        raise ContractError("semantic progress current failure binding differs")
    signature = _failure_signature(current)
    signature_hash = sha256_text(signature)
    check_id = str(current.payload["check_id"])
    matching_reversed: list[RunEvent] = []
    seen_diffs: set[str] = set()
    for event in reversed(event_tuple):
        if event.sequence > current.sequence:
            continue
        if (
            event.type != EventType.TOOL_SUCCEEDED
            or event.payload.get("tool") != "run_check"
            or event.payload.get("check_id") != check_id
            or event.payload.get("invocation_status") != "completed"
        ):
            continue
        if event.payload.get("behavior_status") != "failed":
            break
        if sha256_text(_failure_signature(event)) != signature_hash:
            break
        diff_hash = event.payload.get("worktree_diff_hash")
        if not isinstance(diff_hash, str):
            raise ContractError("semantic progress failed check lacks a diff hash")
        if diff_hash in seen_diffs:
            continue
        seen_diffs.add(diff_hash)
        matching_reversed.append(event)
    matching = tuple(reversed(matching_reversed))
    if not matching or matching[-1].sequence != current.sequence:
        raise ContractError("semantic progress streak does not end at the current failure")
    if len(matching) > 4:
        raise ContractError("semantic progress streak exceeds the correction envelope")
    body = {
        "schema_version": SEMANTIC_PROGRESS_SCHEMA,
        "run_id": run_id,
        "worktree_diff_hash": evidence.worktree_diff_hash,
        "check_id": check_id,
        "current_failure_event_sequence": current.sequence,
        "failure_signature": signature,
        "failure_signature_hash": signature_hash,
        "same_signature_failed_diff_count": len(matching),
        "failure_event_sequences": tuple(event.sequence for event in matching),
        "failed_diff_hashes": tuple(str(event.payload["worktree_diff_hash"]) for event in matching),
        "semantic_reset_required": len(matching) >= 2,
        "public_check_output_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(PublicSemanticProgressState, body)


def _decision_v3(
    base: WorkflowDecisionV2,
    state: PublicSemanticProgressState | None,
    **updates: Any,
) -> WorkflowDecisionV3:
    body = {
        **base.model_dump(
            mode="python",
            exclude={"schema_version", "runtime_policy_version", "policy_version", "content_hash"},
        ),
        "schema_version": WORKFLOW_DECISION_SCHEMA_V3,
        "runtime_policy_version": RUNTIME_POLICY_V15,
        "policy_version": WORKFLOW_POLICY_V15,
        "semantic_progress_state_hash": state.content_hash if state is not None else None,
        "semantic_reset_required": bool(state and state.semantic_reset_required),
        "required_prior_hypothesis_disposition": (
            "rejected" if state is not None and state.semantic_reset_required else None
        ),
        **updates,
    }
    return _hashed(WorkflowDecisionV3, body)


def apply_semantic_no_progress_policy(
    *,
    base_decision: WorkflowDecisionV2,
    semantic_progress_state: PublicSemanticProgressState | None,
    events: tuple[RunEvent, ...] | list[RunEvent],
    current_revision_disposition: Literal["retained", "refined", "rejected"] | None,
) -> WorkflowDecisionV3:
    """Apply the V15 reset lane to an otherwise exact V14 decision."""

    state = semantic_progress_state
    if base_decision.target == "terminal" or state is None or not state.semantic_reset_required:
        return _decision_v3(base_decision, state)
    if current_revision_disposition is not None:
        if current_revision_disposition != "rejected":
            return _decision_v3(
                base_decision,
                state,
                target="terminal",
                allowed_tool_names=(),
                terminal_reason="semantic_no_progress_revision_invalid",
                effective_max_output_tokens=1,
                reasoning_effort="low",
            )
        return _decision_v3(base_decision, state)

    episode = [
        event
        for event in events
        if event.sequence > state.current_failure_event_sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") in _INFO_TOOLS
        and event.payload.get("worktree_diff_hash") == state.worktree_diff_hash
    ]
    info_count = len(episode)
    has_search = any(event.payload.get("tool") == "search_files" for event in episode)
    has_read = any(event.payload.get("tool") == "read_file" for event in episode)
    if has_search and has_read:
        return _decision_v3(
            base_decision,
            state,
            target="revise-work-plan",
            allowed_tool_names=("revise_work_plan",),
            information_actions_in_episode=min(info_count, 3),
            fresh_current_read=True,
            terminal_reason=None,
            effective_max_output_tokens=min(base_decision.configured_max_output_tokens, 8_192),
            reasoning_effort="medium",
        )
    if info_count >= 3:
        return _decision_v3(
            base_decision,
            state,
            target="terminal",
            allowed_tool_names=(),
            information_actions_in_episode=3,
            fresh_current_read=has_read,
            terminal_reason="semantic_no_progress_evidence_exhausted",
            effective_max_output_tokens=1,
            reasoning_effort="low",
        )
    allowed = (
        ("search_files", "read_file")
        if not has_search and not has_read
        else ("search_files",)
        if not has_search
        else ("read_file",)
    )
    return _decision_v3(
        base_decision,
        state,
        target="correction-investigation",
        allowed_tool_names=allowed,
        information_actions_in_episode=info_count,
        fresh_current_read=has_read,
        terminal_reason=None,
        effective_max_output_tokens=min(base_decision.configured_max_output_tokens, 4_096),
        reasoning_effort="low",
    )


def project_workflow_semantic_progress_successor(
    *,
    run_id: str,
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...] | list[RunEvent],
    work_plan_events: tuple[RunEvent, ...] | list[RunEvent] | None = None,
    catalog: EligiblePlanEvidenceCatalogV2,
    semantic_progress_state: PublicSemanticProgressState | None,
    active_work_state: ActiveWorkState | None,
    available_tool_names: tuple[str, ...],
    configured_max_output_tokens: int,
) -> WorkflowDecisionV3:
    base = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v14",
        run_id=run_id,
        task=task,
        evidence=evidence,
        events=(events if work_plan_events is None else work_plan_events),
        catalog=catalog,
        available_tool_names=available_tool_names,
        configured_max_output_tokens=configured_max_output_tokens,
    )
    disposition = None
    if (
        semantic_progress_state is not None
        and active_work_state is not None
        and active_work_state.latest_plan.trigger == "check_failure"
        and active_work_state.latest_plan.trigger_event_sequence
        == semantic_progress_state.current_failure_event_sequence
        and active_work_state.latest_plan.worktree_diff_hash == evidence.worktree_diff_hash
    ):
        disposition = active_work_state.latest_plan.prior_hypothesis_disposition
    return apply_semantic_no_progress_policy(
        base_decision=base,
        semantic_progress_state=semantic_progress_state,
        events=events,
        current_revision_disposition=disposition,
    )


def project_workflow_tool_surface_v3(
    *,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
    source_tool_schemas: tuple[dict[str, Any], ...],
) -> WorkflowToolSurfaceV2:
    surface = project_workflow_tool_surface_v2(
        decision=decision,
        catalog=catalog,
        source_tool_schemas=source_tool_schemas,
    )
    selected = tuple(copy.deepcopy(item) for item in surface.selected_tool_schemas)
    if decision.semantic_reset_required and "revise_work_plan" in decision.allowed_tool_names:
        schema = next(item for item in selected if item.get("name") == "revise_work_plan")
        disposition = schema["parameters"]["properties"]["prior_hypothesis_disposition"]
        disposition["enum"] = ["rejected"]
        disposition["description"] = (
            "The same public failure signature repeated on distinct diffs; reject the prior "
            "hypothesis before another mutation."
        )
    body = {
        **surface.model_dump(mode="python", exclude={"content_hash", "selected_tool_schema_hash"}),
        "selected_tool_schemas": selected,
        "selected_tool_schema_hash": sha256_json(list(selected)),
    }
    return _hashed(WorkflowToolSurfaceV2, body)


def workflow_instruction_v3(
    decision: WorkflowDecisionV3,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV2,
    active_work_state: ActiveWorkState | None,
    semantic_progress_state: PublicSemanticProgressState | None,
) -> dict[str, Any]:
    instructions = {
        "phase-policy": "Use one phase-filtered public tool action.",
        "visible-check": "Run exactly the bound public check.",
        "correction-investigation": (
            "Investigate the current public failure. A semantic reset requires both one search "
            "and one fresh source read before revision."
        ),
        "corrective-mutation": (
            "Apply one smallest edit under the active rejected hypothesis reset."
        ),
        "diff-review": "Obtain and review the complete current diff.",
        "review-decision": "Submit the checked diff or record the one review revision.",
        "pre-mutation-exploration": "Use exact public evidence IDs, then record one bounded plan.",
        "record-work-plan": "Record the initial plan using only exact catalog IDs.",
        "revise-work-plan": (
            "The same public failure repeated across diffs. Reject the prior hypothesis and "
            "record a new bounded revision using exact catalog IDs."
            if decision.semantic_reset_required
            else "Record the required semantic revision using exact catalog IDs."
        ),
        "plan-implementation": "Follow the pinned active plan and make one smallest mutation.",
        "terminal": "No provider request is authorized for this terminal state.",
    }
    body = {
        "schema_version": WORKFLOW_INSTRUCTION_SCHEMA_V3,
        "policy_version": decision.policy_version,
        "decision_hash": decision.content_hash,
        "target": decision.target,
        "expected_check_id": decision.expected_check_id,
        "available_tool_names": list(decision.allowed_tool_names),
        "plan_gate_id": decision.plan_gate_id,
        "plan_admission_recovery_used": decision.plan_admission_recovery_used,
        "required_trigger_evidence_id": decision.required_trigger_evidence_id,
        "required_prior_hypothesis_disposition": (decision.required_prior_hypothesis_disposition),
        "instruction": instructions[decision.target],
        "public_task_spec": copy.deepcopy(public_task_spec),
        "eligible_plan_evidence_catalog": catalog.model_dump(mode="json"),
        "active_work_plan": (
            active_work_state.latest_plan.model_dump(mode="json")
            if active_work_state is not None
            else None
        ),
        "active_work_state": (
            active_work_state.model_dump(mode="json") if active_work_state is not None else None
        ),
        "semantic_progress_state": (
            semantic_progress_state.model_dump(mode="json")
            if semantic_progress_state is not None
            else None
        ),
        "provider_calls_authorized": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def validate_semantic_progress_revision(
    *,
    semantic_progress_state: PublicSemanticProgressState | None,
    prior_hypothesis_disposition: str | None,
    trigger_event_sequence: int | None,
) -> None:
    if semantic_progress_state is None or not semantic_progress_state.semantic_reset_required:
        return
    if trigger_event_sequence != semantic_progress_state.current_failure_event_sequence:
        raise ContractError(
            "semantic no-progress revision trigger differs",
            details={"reason_codes": ["semantic_no_progress_trigger_mismatch"]},
        )
    if prior_hypothesis_disposition != "rejected":
        raise ContractError(
            "semantic no-progress revision must reject the prior hypothesis",
            details={"reason_codes": ["semantic_no_progress_requires_rejected_hypothesis"]},
        )


__all__ = [
    "PublicSemanticProgressState",
    "RUNTIME_POLICY_V15",
    "SEMANTIC_PROGRESS_SCHEMA",
    "WORKFLOW_DECISION_SCHEMA_V3",
    "WORKFLOW_INSTRUCTION_SCHEMA_V3",
    "WORKFLOW_POLICY_V15",
    "WorkflowDecisionV3",
    "apply_semantic_no_progress_policy",
    "current_public_failure_event_sequence",
    "project_public_semantic_progress_state",
    "project_workflow_semantic_progress_successor",
    "project_workflow_tool_surface_v3",
    "validate_semantic_progress_revision",
    "workflow_instruction_v3",
]
