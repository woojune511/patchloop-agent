"""Public-only reliability seams selected from immutable Rapid R21 traces.

This module is opt-in.  It does not execute a provider, check, evaluator, or
container.  It keeps generation recovery separate from action admission,
projects compact plan feedback, binds reads to exact public search matches, and
adds a task-generic lifecycle state-transition description to work plans.
"""

from __future__ import annotations

import copy
import fnmatch
import json
from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.context_event_compaction import CompactedEventContext
from patchloop.agent.investigation import InspectionRecord
from patchloop.agent.workflow_causal_alternative_activation import CrossResetFailureTrigger
from patchloop.agent.workflow_causal_plan_projection_activation import (
    CausalMechanismHistoryEntryV2,
    RecordedCausalPlanV2,
)
from patchloop.agent.workflow_plan_admission_feedback_successor import (
    project_compatible_bounded_plan_admission_feedback,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    TriggerBoundSelfDirectedPlanRequest,
    normalize_trigger_bound_self_directed_plan,
    project_trigger_bound_self_directed_tool_surface,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    EligiblePlanEvidenceCatalogV4,
    SelfDirectedExplorationClosureReceipt,
    SelfDirectedExplorationState,
    WorkflowDecisionV4,
    workflow_instruction_v8,
)
from patchloop.agent.workflow_successor_v2 import WorkflowToolSurfaceV2
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, safe_relative_path, sha256_json, sha256_text

GENERATION_INCOMPLETE_RECOVERY_POLICY = "dedicated-generation-incomplete-recovery-v1"
PLAN_ADMISSION_FEEDBACK_POLICY_V2 = "bounded-plan-admission-feedback-v2"
ANCHORED_READ_POLICY = "anchored-source-read-v1"
LIFECYCLE_PLAN_POLICY = "public-lifecycle-state-transition-plan-v1"
LIFECYCLE_PLAN_REQUEST_SCHEMA = "lifecycle-bound-self-directed-plan-request-v1"
LIFECYCLE_PLAN_RECORD_SCHEMA = "public-lifecycle-state-transition-v1"
COMPACT_FEEDBACK_SCHEMA = "compact-plan-admission-feedback-v2"
COMPACT_FEEDBACK_EVIDENCE_SCHEMA = "compact-plan-admission-feedback-evidence-v2"
MAX_PLAN_FEEDBACK_BYTES = 12_000


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _public_text(value: str, *, field: str) -> str:
    if not value or value != value.strip() or "\x00" in value:
        raise ValueError(f"{field} must be bounded trimmed public text")
    return value


class GenerationIncompleteRecoveryState(BaseModel):
    """Durable one-use generation retry, independent of action recovery."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["generation-incomplete-recovery-state-v1"]
    policy_version: Literal["dedicated-generation-incomplete-recovery-v1"]
    used: bool
    remaining: int = Field(ge=0, le=1)
    source_event_sequence: int | None = Field(default=None, ge=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.remaining != (0 if self.used else 1):
            raise ValueError("generation-incomplete retry accounting differs")
        if self.used is not (self.source_event_sequence is not None):
            raise ValueError("generation-incomplete retry source differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("generation-incomplete retry hash differs")
        return self


def project_generation_incomplete_recovery(
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> GenerationIncompleteRecoveryState:
    event_tuple = tuple(events)
    recoveries = [
        event
        for event in event_tuple
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == GENERATION_INCOMPLETE_RECOVERY_POLICY
        and event.payload.get("reason_code") == "reasoning_incomplete"
        and event.payload.get("execution") == "not_dispatched"
    ]
    if len(recoveries) > 1:
        raise RecoveryError("generation-incomplete retry was consumed more than once")
    body = {
        "schema_version": "generation-incomplete-recovery-state-v1",
        "policy_version": GENERATION_INCOMPLETE_RECOVERY_POLICY,
        "used": bool(recoveries),
        "remaining": 0 if recoveries else 1,
        "source_event_sequence": recoveries[0].sequence if recoveries else None,
    }
    return _hashed(GenerationIncompleteRecoveryState, body)


class CompactPlanFeedbackEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["compact-plan-admission-feedback-evidence-v2"]
    policy_version: Literal["bounded-plan-admission-feedback-v2"]
    source_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_context_bytes: int = Field(ge=1)
    projected_context_bytes: int = Field(ge=1, le=2_000_000)
    latest_feedback_bytes: int = Field(ge=0, le=MAX_PLAN_FEEDBACK_BYTES)
    rejection_count: int = Field(ge=0)
    latest_rejection_sequence: int | None = Field(default=None, ge=1)
    durable_event_changed: Literal[False]
    public_projection_only: Literal[True]
    private_or_hidden_material_included: Literal[False]
    raw_reasoning_included: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if bool(self.rejection_count) is not (self.latest_rejection_sequence is not None):
            raise ValueError("compact feedback latest rejection differs")
        if bool(self.rejection_count) is not bool(self.latest_feedback_bytes):
            raise ValueError("compact feedback byte accounting differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("compact feedback evidence hash differs")
        return self


@dataclass(frozen=True)
class CompactPlanFeedbackContext:
    rendered: str
    content_hash: str
    evidence: CompactPlanFeedbackEvidence


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

    def collect_source_spans(value: Any) -> None:
        if isinstance(value, dict):
            raw_spans = value.get("spans")
            if isinstance(raw_spans, list) and all(isinstance(item, dict) for item in raw_spans):
                spans.extend(raw_spans)
            for item in value.values():
                collect_source_spans(item)
        elif isinstance(value, list):
            for item in value:
                collect_source_spans(item)

    collect_source_spans(details.get("activated_exploration_plan_request"))
    span_ids = sorted(
        {
            str(item["source_span_id"])
            for item in spans
            if isinstance(item, dict) and isinstance(item.get("source_span_id"), str)
        }
    )
    return evidence_ids, span_ids


def project_compact_plan_admission_feedback_v2(
    compacted: CompactedEventContext,
) -> CompactPlanFeedbackContext:
    """Validate the durable source with V25, then retain one compact rejection."""

    # This validation and first projection deliberately reuse the immutable
    # predecessor contract.  V2 then reduces that already-bounded view rather
    # than accidentally re-emitting the large durable rejection payload.
    predecessor = project_compatible_bounded_plan_admission_feedback(compacted)
    try:
        source = json.loads(predecessor.rendered)
        durable_source = json.loads(compacted.rendered)
    except json.JSONDecodeError as exc:
        raise ContractError("compact plan feedback context is not JSON") from exc
    if not isinstance(source, dict) or not isinstance(source.get("recent_events"), list):
        raise ContractError("compact plan feedback context shape differs")
    projected = copy.deepcopy(source)
    targets: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(projected["recent_events"]):
        payload = event.get("payload") if isinstance(event, dict) else None
        if (
            isinstance(payload, dict)
            and event.get("type") == "ToolFailed"
            and payload.get("tool") in {"record_work_plan", "revise_work_plan"}
            and payload.get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
            and isinstance(payload.get("error_details"), dict)
            and isinstance(event.get("sequence"), int)
        ):
            targets.append((index, event))
    latest_sequence = targets[-1][1]["sequence"] if targets else None
    latest_feedback_bytes = 0
    for _index, event in targets:
        durable_event = next(
            (
                item
                for item in durable_source.get("recent_events", [])
                if isinstance(item, dict) and item.get("sequence") == event["sequence"]
            ),
            None,
        )
        details = (
            durable_event.get("payload", {}).get("error_details")
            if isinstance(durable_event, dict) and isinstance(durable_event.get("payload"), dict)
            else None
        )
        if not isinstance(details, dict):
            raise ContractError("compact plan feedback lost its durable source details")
        source_hash = sha256_json(details)
        if event["sequence"] != latest_sequence:
            event["payload"]["error_details"] = {
                "schema_version": "superseded-plan-admission-feedback-v2",
                "projection_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V2,
                "source_error_details_hash": source_hash,
                "superseded_by_event_sequence": latest_sequence,
            }
            continue
        evidence_ids, span_ids = _catalog_ids(details)
        compact = {
            "schema_version": COMPACT_FEEDBACK_SCHEMA,
            "projection_policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V2,
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
            "guidance": (
                "Retry once using only IDs listed here. If causal_reset_required is true, "
                "reject the prior hypothesis and select a different causal boundary."
            ),
        }
        compact_bytes = len(canonical_json(compact).encode("utf-8"))
        if compact_bytes > MAX_PLAN_FEEDBACK_BYTES:
            raise ContractError("compact plan feedback exceeds its byte ceiling")
        latest_feedback_bytes = compact_bytes
        event["payload"]["error_details"] = compact
    rendered = json.dumps(projected, indent=2, ensure_ascii=False, default=str)
    projected_bytes = len(rendered.encode("utf-8"))
    body = {
        "schema_version": COMPACT_FEEDBACK_EVIDENCE_SCHEMA,
        "policy_version": PLAN_ADMISSION_FEEDBACK_POLICY_V2,
        "source_context_hash": compacted.content_hash,
        "projected_context_hash": sha256_text(rendered),
        "source_context_bytes": len(compacted.rendered.encode("utf-8")),
        "projected_context_bytes": projected_bytes,
        "latest_feedback_bytes": latest_feedback_bytes,
        "rejection_count": len(targets),
        "latest_rejection_sequence": latest_sequence,
        "durable_event_changed": False,
        "public_projection_only": True,
        "private_or_hidden_material_included": False,
        "raw_reasoning_included": False,
    }
    evidence = _hashed(CompactPlanFeedbackEvidence, body)
    return CompactPlanFeedbackContext(rendered, evidence.projected_context_hash, evidence)


class SearchAnchorInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    search_event_sequence: int = Field(ge=1)
    match_index: int = Field(ge=0, le=99)
    before_lines: int = Field(default=25, ge=0, le=100)
    after_lines: int = Field(default=25, ge=0, le=100)


class AnchoredReadResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["anchored-source-read-resolution-v1"]
    policy_version: Literal["anchored-source-read-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    search_event_sequence: int = Field(ge=1)
    search_result_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    match_index: int = Field(ge=0)
    match_line: int = Field(ge=1)
    path: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
        if not self.start_line <= self.match_line <= self.end_line:
            raise ValueError("anchored read does not cover its selected match")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("anchored read resolution hash differs")
        return self


def _path_allowed(task: PublicTask, path: str) -> bool:
    return any(fnmatch.fnmatch(path, item) for item in task.constraints.allowed_paths) and not any(
        fnmatch.fnmatch(path, item) for item in task.constraints.forbidden_paths
    )


def resolve_anchored_read(
    *,
    run_id: str,
    task: PublicTask,
    worktree_diff_hash: str,
    records: tuple[InspectionRecord, ...] | list[InspectionRecord],
    raw_anchor: dict[str, Any],
) -> AnchoredReadResolution:
    try:
        anchor = SearchAnchorInput.model_validate(raw_anchor)
    except ValueError as exc:
        raise ContractError(
            "anchored read input differs",
            details={"reason_codes": ["anchored_read_input_invalid"]},
        ) from exc
    matching = [
        record
        for record in records
        if record.tool == "search_files"
        and record.outcome_sequence == anchor.search_event_sequence
        and record.worktree_diff_hash == worktree_diff_hash
    ]
    if len(matching) != 1:
        raise ContractError(
            "anchored read search result is stale or unavailable",
            details={"reason_codes": ["anchored_read_search_unavailable"]},
        )
    record = matching[0]
    matches = record.result.get("matches")
    if not isinstance(matches, list) or anchor.match_index >= len(matches):
        raise ContractError(
            "anchored read match index is unavailable",
            details={"reason_codes": ["anchored_read_match_unavailable"]},
        )
    match = matches[anchor.match_index]
    path = safe_relative_path(str(match.get("path")), field_name="anchored read path")
    line = match.get("line")
    if type(line) is not int or line < 1 or not _path_allowed(task, path):
        raise ContractError(
            "anchored read match is outside public scope",
            details={"reason_codes": ["anchored_read_match_out_of_scope"]},
        )
    start = max(1, line - anchor.before_lines)
    end = line + anchor.after_lines
    body = {
        "schema_version": "anchored-source-read-resolution-v1",
        "policy_version": ANCHORED_READ_POLICY,
        "run_id": run_id,
        "worktree_diff_hash": worktree_diff_hash,
        "search_event_sequence": record.outcome_sequence,
        "search_result_hash": record.result_artifact.content_hash,
        "match_index": anchor.match_index,
        "match_line": line,
        "path": path,
        "start_line": start,
        "end_line": end,
    }
    return _hashed(AnchoredReadResolution, body)


class LifecycleOwnerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    component: str = Field(min_length=1, max_length=200)
    owner_source_span_id: str = Field(pattern=r"^cspan:[1-9][0-9]*:[0-9]+$")
    responsibility: str = Field(min_length=1, max_length=1_000)

    @field_validator("component", "responsibility")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _public_text(value, field="lifecycle owner")


class LifecycleStateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    component: str = Field(min_length=1, max_length=200)
    before: str = Field(min_length=1, max_length=500)
    after: str = Field(min_length=1, max_length=500)

    @field_validator("component", "before", "after")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _public_text(value, field="lifecycle state")


class LifecycleTransitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    trigger: str = Field(min_length=1, max_length=500)
    affected_components: tuple[str, ...] = Field(min_length=1, max_length=8)
    evidence_source_span_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    atomic: Literal[True]

    @field_validator("trigger")
    @classmethod
    def normalize_trigger(cls, value: str) -> str:
        return _public_text(value, field="lifecycle transition")


class AtomicPostconditionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    condition: str = Field(min_length=1, max_length=1_000)
    evidence_source_span_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    falsification_observation: str = Field(min_length=1, max_length=1_000)

    @field_validator("condition", "falsification_observation")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _public_text(value, field="lifecycle postcondition")


class LifecycleStateTransitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    owners: tuple[LifecycleOwnerInput, ...] = Field(min_length=1, max_length=8)
    states: tuple[LifecycleStateInput, ...] = Field(min_length=1, max_length=8)
    transitions: tuple[LifecycleTransitionInput, ...] = Field(min_length=1, max_length=8)
    atomic_postconditions: tuple[AtomicPostconditionInput, ...] = Field(min_length=1, max_length=8)


class LifecycleBoundPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lifecycle-bound-self-directed-plan-request-v1"]
    policy_version: Literal["public-lifecycle-state-transition-plan-v1"]
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
            raise ValueError("lifecycle plan request binding differs")
        return self


class RecordedLifecycleStateTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["public-lifecycle-state-transition-v1"]
    policy_version: Literal["public-lifecycle-state-transition-plan-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    lifecycle: LifecycleStateTransitionInput
    cited_source_span_ids: tuple[str, ...] = Field(min_length=1)
    mutation_site_span_id: str = Field(pattern=r"^cspan:[1-9][0-9]*:[0-9]+$")
    public_current_diff_source_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("lifecycle plan record hash differs")
        return self


def _lifecycle_schema(span_ids: list[str]) -> dict[str, Any]:
    span = {"type": "string", "enum": span_ids}
    return {
        "type": "object",
        "properties": {
            "owners": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "component": {"type": "string", "minLength": 1, "maxLength": 200},
                        "owner_source_span_id": span,
                        "responsibility": {"type": "string", "minLength": 1, "maxLength": 1000},
                    },
                    "required": ["component", "owner_source_span_id", "responsibility"],
                    "additionalProperties": False,
                },
            },
            "states": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "component": {"type": "string", "minLength": 1, "maxLength": 200},
                        "before": {"type": "string", "minLength": 1, "maxLength": 500},
                        "after": {"type": "string", "minLength": 1, "maxLength": 500},
                    },
                    "required": ["component", "before", "after"],
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
                        "affected_components": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 8,
                            "items": {"type": "string", "minLength": 1},
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
                        "affected_components",
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
                        "condition": {"type": "string", "minLength": 1, "maxLength": 1000},
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
        "required": ["owners", "states", "transitions", "atomic_postconditions"],
        "additionalProperties": False,
    }


def project_lifecycle_bound_plan_request(
    source: TriggerBoundSelfDirectedPlanRequest,
) -> LifecycleBoundPlanRequest:
    parameters = copy.deepcopy(source.parameters)
    properties = parameters.get("properties")
    required = parameters.get("required")
    spans = source.source_request.base_request.source_projection.source_span_catalog.spans
    if not isinstance(properties, dict) or not isinstance(required, list) or not spans:
        raise RecoveryError("lifecycle plan predecessor request differs")
    span_ids = [item.source_span_id for item in spans]
    properties["lifecycle_state_transition"] = _lifecycle_schema(span_ids)
    required.append("lifecycle_state_transition")
    body = {
        "schema_version": LIFECYCLE_PLAN_REQUEST_SCHEMA,
        "policy_version": LIFECYCLE_PLAN_POLICY,
        "source_request": source.model_dump(mode="python"),
        "source_request_hash": source.content_hash,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
        "public_evidence_only": True,
        "semantic_truth_verified": False,
    }
    return _hashed(LifecycleBoundPlanRequest, body)


def project_lifecycle_bound_tool_surface(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV4,
    catalog: EligiblePlanEvidenceCatalogV4,
    state: SelfDirectedExplorationState | None,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[WorkflowToolSurfaceV2, LifecycleBoundPlanRequest | None]:
    surface, source_request = project_trigger_bound_self_directed_tool_surface(
        task=task,
        decision=decision,
        catalog=catalog,
        state=state,
        source_tool_schemas=source_tool_schemas,
        cross_reset_trigger=cross_reset_trigger,
    )
    request = (
        project_lifecycle_bound_plan_request(source_request) if source_request is not None else None
    )
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    for schema in selected:
        if schema.get("name") in {"record_work_plan", "revise_work_plan"}:
            if request is None:
                raise RecoveryError("lifecycle plan surface lacks its request")
            schema["parameters"] = copy.deepcopy(request.parameters)
            schema["description"] = (
                "Record the public causal plan, readiness, and generic lifecycle owners, "
                "state transitions, and atomic postconditions."
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


def lifecycle_workflow_instruction(
    decision: WorkflowDecisionV4,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV4,
    active_work_state: Any,
    semantic_progress_state: Any,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    request_projection: LifecycleBoundPlanRequest | None,
    readiness: Any,
    recovered_pin: Any,
    self_directed_state: SelfDirectedExplorationState | None,
) -> dict[str, Any]:
    """Bind the generic lifecycle request without changing V8 instruction code."""

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
        "lifecycle_plan_policy_version": LIFECYCLE_PLAN_POLICY,
        "activated_exploration_plan_request": (
            request_projection.model_dump(mode="json") if request_projection is not None else None
        ),
        "activated_exploration_plan_request_hash": (
            request_projection.content_hash if request_projection is not None else sha256_json(None)
        ),
    }
    if request_projection is not None:
        body["instruction"] = (
            "Use only the public request-enumerated evidence. Record causal ownership, "
            "before/after states, the triggering transition, and falsifiable atomic "
            "postconditions before mutation."
        )
    return {**body, "content_hash": sha256_json(body)}


def normalize_lifecycle_bound_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalogV4,
    request_projection: LifecycleBoundPlanRequest,
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
    RecordedLifecycleStateTransition,
]:
    exact = project_lifecycle_bound_plan_request(request_projection.source_request)
    if request_projection != exact or set(raw_arguments) != set(
        request_projection.parameters.get("required", [])
    ):
        raise RecoveryError("lifecycle plan request binding differs")
    try:
        lifecycle = LifecycleStateTransitionInput.model_validate_json(
            canonical_json(raw_arguments.get("lifecycle_state_transition"))
        )
    except ValueError as exc:
        raise ContractError(
            "lifecycle state-transition input differs",
            details={"reason_codes": ["lifecycle_state_transition_invalid"]},
        ) from exc
    source_projection = (
        request_projection.source_request.source_request.base_request.source_projection
    )
    source_spans = source_projection.source_span_catalog.spans
    span_ids = {item.source_span_id for item in source_spans}
    owners = {item.component: item for item in lifecycle.owners}
    states = {item.component: item for item in lifecycle.states}
    cited = {
        *(item.owner_source_span_id for item in lifecycle.owners),
        *(span_id for item in lifecycle.transitions for span_id in item.evidence_source_span_ids),
        *(
            span_id
            for item in lifecycle.atomic_postconditions
            for span_id in item.evidence_source_span_ids
        ),
    }
    if (
        len(owners) != len(lifecycle.owners)
        or len(states) != len(lifecycle.states)
        or set(owners) != set(states)
        or not cited.issubset(span_ids)
        or any(item.before == item.after for item in lifecycle.states)
        or any(
            len(set(item.affected_components)) != len(item.affected_components)
            or not set(item.affected_components).issubset(owners)
            for item in lifecycle.transitions
        )
    ):
        raise ContractError(
            "lifecycle owners, states, transitions, or evidence differ",
            details={"reason_codes": ["lifecycle_state_transition_unbound"]},
        )
    normalized_arguments = {
        key: copy.deepcopy(value)
        for key, value in raw_arguments.items()
        if key != "lifecycle_state_transition"
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
    if mutation_span not in {item.owner_source_span_id for item in lifecycle.owners}:
        raise ContractError(
            "lifecycle ownership does not include the mutation site",
            details={"reason_codes": ["lifecycle_mutation_owner_missing"]},
        )
    body = {
        "schema_version": LIFECYCLE_PLAN_RECORD_SCHEMA,
        "policy_version": LIFECYCLE_PLAN_POLICY,
        "run_id": plan.run_id,
        "worktree_diff_hash": plan.worktree_diff_hash,
        "plan_hash": plan.content_hash,
        "lifecycle": lifecycle.model_dump(mode="python"),
        "cited_source_span_ids": tuple(sorted(cited)),
        "mutation_site_span_id": mutation_span,
        "public_current_diff_source_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return plan, closure, _hashed(RecordedLifecycleStateTransition, body)


__all__ = [
    "ANCHORED_READ_POLICY",
    "AnchoredReadResolution",
    "COMPACT_FEEDBACK_EVIDENCE_SCHEMA",
    "COMPACT_FEEDBACK_SCHEMA",
    "CompactPlanFeedbackContext",
    "CompactPlanFeedbackEvidence",
    "GENERATION_INCOMPLETE_RECOVERY_POLICY",
    "GenerationIncompleteRecoveryState",
    "LIFECYCLE_PLAN_POLICY",
    "LifecycleBoundPlanRequest",
    "PLAN_ADMISSION_FEEDBACK_POLICY_V2",
    "RecordedLifecycleStateTransition",
    "normalize_lifecycle_bound_plan",
    "lifecycle_workflow_instruction",
    "project_compact_plan_admission_feedback_v2",
    "project_generation_incomplete_recovery",
    "project_lifecycle_bound_plan_request",
    "project_lifecycle_bound_tool_surface",
    "resolve_anchored_read",
]
