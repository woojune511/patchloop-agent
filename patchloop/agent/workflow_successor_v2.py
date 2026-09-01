"""Public-only evidence and iterative work-state successors for Lean V11/V12.

This module is deliberately separate from the consumed V9/V10 workflow
implementation.  It projects only model-visible public tool results, validates
plans against the exact request catalog, and reconstructs bounded plan revision
state from append-only events.  It never executes a tool or reads evaluator,
private, reference-patch, or model-reasoning data.
"""

from __future__ import annotations

import copy
import fnmatch
import json
from collections import Counter
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.phases import EvidenceState
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import safe_relative_path, sha256_json, sha256_text

ELIGIBLE_PLAN_EVIDENCE_SCHEMA = "eligible-plan-evidence-catalog-v1"
ELIGIBLE_PLAN_EVIDENCE_SCHEMA_V2 = "eligible-plan-evidence-catalog-v2"
RECORDED_WORK_PLAN_SCHEMA_V2 = "recorded-work-plan-v2"
PLAN_RECORDED_EVENT_SCHEMA_V2 = "plan-recorded-event-v2"
ACTIVE_WORK_STATE_SCHEMA = "active-work-state-v1"
WORKFLOW_DECISION_SCHEMA_V2 = "lean-workflow-decision-v2"
WORKFLOW_SURFACE_SCHEMA_V2 = "lean-workflow-tool-surface-v2"
WORKFLOW_POLICY_V11 = "eligible-public-evidence-plan-gate-v2"
WORKFLOW_POLICY_V12 = "epoch-work-plan-revision-v1"
WORKFLOW_POLICY_V14 = "required-failed-check-trigger-pinned-v1"
WORK_PLAN_ADMISSION_POLICY = "work-plan-admission-recovery-v1"

_EMPTY_DIFF_HASH = sha256_text("")
_TRUNCATION_MARKER = "\n...[field truncated for model context]"
_MUTATION_TOOLS = frozenset({"apply_patch", "apply_structured_edit"})
_INFO_TOOLS = frozenset({"search_files", "read_file"})

EvidenceKind = Literal[
    "source_read",
    "targeted_check_result",
    "visible_check_result",
    "diff_review_result",
    "search_support",
]
ObservationStatus = Literal[
    "targeted_check_failed",
    "targeted_check_passed",
    "static_source",
    "visible_check_failed",
    "review_diff",
]
PlanTrigger = Literal["initial", "check_failure", "review_correction"]
WorkflowTargetV2 = Literal[
    "phase-policy",
    "visible-check",
    "correction-investigation",
    "corrective-mutation",
    "diff-review",
    "review-decision",
    "pre-mutation-exploration",
    "record-work-plan",
    "revise-work-plan",
    "plan-implementation",
    "terminal",
]


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _path_allowed(task: PublicTask, path: str) -> bool:
    return any(
        fnmatch.fnmatch(path, pattern) for pattern in task.constraints.allowed_paths
    ) and not any(fnmatch.fnmatch(path, pattern) for pattern in task.constraints.forbidden_paths)


class SourceEvidenceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    requested_range: tuple[int, int]
    actual_range: tuple[int, int] | None
    visible_ranges: tuple[tuple[int, int], ...]
    omitted_ranges: tuple[tuple[int, int], ...]
    partial_line: bool
    total_lines: int = Field(ge=0)
    file_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        if self.requested_range[0] < 1 or self.requested_range[1] < self.requested_range[0]:
            raise ValueError("source evidence requested range differs")
        for start, end in (*self.visible_ranges, *self.omitted_ranges):
            if start < 1 or end < start:
                raise ValueError("source evidence visible range differs")
        return self


class CheckEvidenceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    check_id: str = Field(min_length=1)
    check_index: int = Field(ge=0)
    invocation_status: Literal["completed", "timed_out"]
    behavior_status: Literal["passed", "failed", "not_observed"]
    passed: bool
    timed_out: bool

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.invocation_status == "timed_out":
            if not self.timed_out or self.passed or self.behavior_status != "not_observed":
                raise ValueError("timed-out check evidence differs")
        elif self.timed_out or (self.behavior_status == "passed") is not self.passed:
            raise ValueError("completed check evidence differs")
        return self


class DiffEvidenceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    patch_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    changed_files: tuple[str, ...]


class SearchEvidenceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    query_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    path_glob: str
    match_count: int = Field(ge=0)
    truncated: bool


class EligiblePlanEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    evidence_id: str = Field(pattern=r"^pev:[1-9][0-9]*$")
    kind: EvidenceKind
    role: Literal["foundation", "support"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_event_sequence: int = Field(ge=1)
    model_visible_event_sequences: tuple[int, ...] = Field(min_length=1)
    replay_alias_event_sequences: tuple[int, ...]
    artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    visible_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source: SourceEvidenceProjection | None = None
    check: CheckEvidenceProjection | None = None
    diff_review: DiffEvidenceProjection | None = None
    search: SearchEvidenceProjection | None = None

    @model_validator(mode="after")
    def validate_kind(self) -> Self:
        if self.evidence_id != f"pev:{self.canonical_event_sequence}":
            raise ValueError("eligible evidence identity differs")
        if tuple(sorted(set(self.model_visible_event_sequences))) != (
            self.model_visible_event_sequences
        ):
            raise ValueError("eligible evidence visible aliases differ")
        if tuple(sorted(set(self.replay_alias_event_sequences))) != (
            self.replay_alias_event_sequences
        ):
            raise ValueError("eligible evidence replay aliases differ")
        expected = {
            "source_read": (self.source is not None, self.check, self.diff_review, self.search),
            "targeted_check_result": (
                self.check is not None,
                self.source,
                self.diff_review,
                self.search,
            ),
            "visible_check_result": (
                self.check is not None,
                self.source,
                self.diff_review,
                self.search,
            ),
            "diff_review_result": (
                self.diff_review is not None,
                self.source,
                self.check,
                self.search,
            ),
            "search_support": (self.search is not None, self.source, self.check, self.diff_review),
        }[self.kind]
        if expected[0] is not True or any(value is not None for value in expected[1:]):
            raise ValueError("eligible evidence kind payload differs")
        if (self.kind == "search_support") is not (self.role == "support"):
            raise ValueError("eligible evidence role differs")
        return self


class EligiblePlanEvidenceCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["eligible-plan-evidence-catalog-v1"]
    run_id: str = Field(min_length=1)
    task_id: str
    task_version: int = Field(ge=1)
    public_task_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_visible_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_visible_recent_event_sequences: tuple[int, ...]
    items: tuple[EligiblePlanEvidence, ...]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_catalog(self) -> Self:
        ids = tuple(item.evidence_id for item in self.items)
        if ids != tuple(dict.fromkeys(ids)):
            raise ValueError("eligible evidence IDs repeat")
        if tuple(item.canonical_event_sequence for item in self.items) != tuple(
            sorted(item.canonical_event_sequence for item in self.items)
        ):
            raise ValueError("eligible evidence order differs")
        if any(
            item.run_id != self.run_id or item.worktree_diff_hash != self.worktree_diff_hash
            for item in self.items
        ):
            raise ValueError("eligible evidence catalog binding differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("eligible evidence catalog hash differs")
        return self


class EligiblePlanEvidenceCatalogV2(EligiblePlanEvidenceCatalog):
    """V11 catalog plus one explicitly delivered failed-check trigger.

    The pinned item is a bounded typed projection reconstructed from the
    durable public ``ToolSucceeded(run_check)`` event.  It remains visible in
    the request catalog after the event leaves the recent-event window.
    """

    schema_version: Literal["eligible-plan-evidence-catalog-v2"]
    required_trigger_status: Literal["not_required", "pinned", "unavailable"]
    required_trigger_event_sequence: int | None = Field(default=None, ge=1)
    required_trigger_evidence_id: str | None = Field(default=None, pattern=r"^pev:[1-9][0-9]*$")
    model_visible_pinned_event_sequences: tuple[int, ...] = Field(max_length=1)
    unavailable_reason: (
        Literal[
            "event_missing",
            "event_not_successful_check",
            "stale_diff",
            "unregistered_check",
            "outcome_not_completed_failure",
            "artifact_binding_invalid",
        ]
        | None
    )

    @model_validator(mode="after")
    def validate_required_trigger(self) -> Self:
        if self.required_trigger_status == "not_required":
            if (
                self.required_trigger_event_sequence is not None
                or self.required_trigger_evidence_id is not None
                or self.model_visible_pinned_event_sequences
                or self.unavailable_reason is not None
            ):
                raise ValueError("not-required workflow trigger differs")
            return self
        if self.required_trigger_event_sequence is None:
            raise ValueError("required workflow trigger lacks an event sequence")
        if self.required_trigger_status == "unavailable":
            if (
                self.required_trigger_evidence_id is not None
                or self.model_visible_pinned_event_sequences
                or self.unavailable_reason is None
            ):
                raise ValueError("unavailable workflow trigger differs")
            return self
        expected_id = f"pev:{self.required_trigger_event_sequence}"
        if (
            self.required_trigger_evidence_id != expected_id
            or self.model_visible_pinned_event_sequences != (self.required_trigger_event_sequence,)
            or self.unavailable_reason is not None
        ):
            raise ValueError("pinned workflow trigger identity differs")
        item = next(
            (candidate for candidate in self.items if candidate.evidence_id == expected_id),
            None,
        )
        if (
            item is None
            or item.kind not in {"targeted_check_result", "visible_check_result"}
            or item.check is None
            or item.check.invocation_status != "completed"
            or item.check.behavior_status != "failed"
            or item.check.passed
            or item.check.timed_out
        ):
            raise ValueError("pinned workflow trigger evidence differs")
        return self


class CandidateFileEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    read_evidence_id: str = Field(pattern=r"^pev:[1-9][0-9]*$")

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        normalized = safe_relative_path(value, field_name="candidate file")
        if normalized != value:
            raise ValueError("candidate file differs")
        return value


class RecordedWorkPlanV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["recorded-work-plan-v2"]
    run_id: str = Field(min_length=1)
    task_id: str
    task_version: int = Field(ge=1)
    public_task_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    observation_status: ObservationStatus
    hypothesis: str = Field(min_length=1, max_length=2_000)
    foundation_evidence: tuple[EligiblePlanEvidence, ...] = Field(min_length=1)
    supporting_evidence: tuple[EligiblePlanEvidence, ...]
    candidate_files: tuple[CandidateFileEvidence, ...] = Field(min_length=1, max_length=20)
    intended_change: str = Field(min_length=1, max_length=2_000)
    expected_behavior: str = Field(min_length=1, max_length=2_000)
    unknowns: tuple[str, ...] = Field(max_length=20)
    planned_check_ids: tuple[str, ...] = Field(min_length=1)
    evidence_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    revision_index: int = Field(ge=0)
    parent_plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: PlanTrigger
    trigger_check_id: str | None = None
    trigger_event_sequence: int | None = Field(default=None, ge=1)
    prior_hypothesis_disposition: Literal["retained", "refined", "rejected"] | None
    public_evidence_only: Literal[True]
    hidden_evidence_used: Literal[False]
    private_evidence_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("hypothesis", "intended_change", "expected_behavior")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        if value != value.strip() or "\x00" in value:
            raise ValueError("work-plan text must be trimmed public text")
        return value

    @field_validator("unknowns")
    @classmethod
    def normalize_unknowns(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            not value.strip() or value != value.strip() or len(value) > 1_000 for value in values
        ):
            raise ValueError("work-plan unknowns differ")
        return values

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if self.trigger == "initial":
            if (
                self.revision_index != 0
                or self.parent_plan_hash is not None
                or self.trigger_check_id is not None
                or self.trigger_event_sequence is not None
                or self.prior_hypothesis_disposition is not None
            ):
                raise ValueError("initial work-plan revision binding differs")
        elif (
            self.revision_index < 1
            or self.parent_plan_hash is None
            or self.trigger_event_sequence is None
            or self.prior_hypothesis_disposition is None
        ):
            raise ValueError("work-plan revision binding differs")
        if self.trigger == "check_failure" and not self.trigger_check_id:
            raise ValueError("check-failure revision lacks a check")
        if self.trigger == "review_correction" and self.trigger_check_id is not None:
            raise ValueError("review revision unexpectedly names a check")
        foundation_ids = tuple(item.evidence_id for item in self.foundation_evidence)
        support_ids = tuple(item.evidence_id for item in self.supporting_evidence)
        if (
            len(set(foundation_ids)) != len(foundation_ids)
            or len(set(support_ids)) != len(support_ids)
            or set(foundation_ids) & set(support_ids)
            or any(item.role != "foundation" for item in self.foundation_evidence)
            or any(item.role != "support" for item in self.supporting_evidence)
        ):
            raise ValueError("work-plan evidence roles differ")
        if len({item.path for item in self.candidate_files}) != len(self.candidate_files):
            raise ValueError("work-plan candidate files repeat")
        if len(set(self.planned_check_ids)) != len(self.planned_check_ids):
            raise ValueError("work-plan checks repeat")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("work-plan content hash differs")
        return self


class WorkPlanRevisionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    revision_index: int = Field(ge=0)
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: PlanTrigger
    prior_hypothesis_disposition: Literal["retained", "refined", "rejected"] | None
    trigger_check_id: str | None
    hypothesis: str
    candidate_files: tuple[str, ...]


class ActiveWorkState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["active-work-state-v1"]
    run_id: str
    task_id: str
    task_version: int = Field(ge=1)
    current_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    initial_plan: RecordedWorkPlanV2
    latest_plan: RecordedWorkPlanV2
    recent_revisions: tuple[WorkPlanRevisionSummary, ...] = Field(max_length=8)
    omitted_revision_count: int = Field(ge=0)
    chain_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    raw_source_included: Literal[False]
    raw_reasoning_included: Literal[False]
    private_evidence_included: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if self.initial_plan.revision_index != 0:
            raise ValueError("active work state initial plan differs")
        if self.latest_plan.revision_index < self.initial_plan.revision_index:
            raise ValueError("active work state latest plan differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("active work state hash differs")
        return self


class WorkflowDecisionV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-workflow-decision-v2"]
    runtime_policy_version: Literal[
        "lean-harness-v11",
        "lean-harness-v12",
        "lean-harness-v13",
        "lean-harness-v14",
    ]
    policy_version: Literal[
        "eligible-public-evidence-plan-gate-v2",
        "epoch-work-plan-revision-v1",
        "required-failed-check-trigger-pinned-v1",
    ]
    target: WorkflowTargetV2
    current_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_check_id: str | None
    allowed_tool_names: tuple[str, ...]
    information_actions_in_episode: int = Field(ge=0, le=3)
    fresh_current_read: bool
    corrective_mutations_for_check: int = Field(ge=0, le=3)
    review_corrections_used: int = Field(ge=0, le=1)
    pre_mutation_actions_used: int = Field(ge=0, le=10)
    active_plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    plan_gate_id: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    plan_admission_recovery_used: bool
    plan_admission_recovery_remaining: int = Field(ge=0, le=1)
    required_trigger_evidence_id: str | None = Field(default=None, pattern=r"^pev:[1-9][0-9]*$")
    revision_trigger: Literal["check_failure", "review_correction"] | None
    terminal_reason: (
        Literal[
            "correction_attempt_limit",
            "pre_mutation_evidence_exhausted",
            "work_plan_admission_repeated",
            "required_workflow_evidence_unavailable",
        ]
        | None
    )
    configured_max_output_tokens: int = Field(ge=1)
    effective_max_output_tokens: int = Field(ge=1)
    reasoning_effort: Literal["low", "medium"]
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if len(set(self.allowed_tool_names)) != len(self.allowed_tool_names):
            raise ValueError("workflow successor tool names repeat")
        if self.target == "terminal":
            if self.allowed_tool_names or self.terminal_reason is None:
                raise ValueError("workflow successor terminal differs")
        elif self.terminal_reason is not None or not self.allowed_tool_names:
            raise ValueError("workflow successor active decision differs")
        exact = {
            "visible-check": ("run_check",),
            "record-work-plan": ("record_work_plan",),
            "revise-work-plan": ("revise_work_plan",),
            "diff-review": ("get_diff",),
            "corrective-mutation": ("apply_structured_edit",),
        }
        if self.target in exact and self.allowed_tool_names != exact[self.target]:
            raise ValueError("workflow successor exact surface differs")
        if self.target == "visible-check" and self.expected_check_id is None:
            raise ValueError("workflow successor check binding differs")
        if self.target == "revise-work-plan" and (
            self.revision_trigger is None or self.required_trigger_evidence_id is None
        ):
            raise ValueError("workflow successor revision binding differs")
        if self.plan_admission_recovery_remaining != (
            0 if self.plan_admission_recovery_used else 1
        ):
            raise ValueError("workflow successor plan recovery differs")
        if self.effective_max_output_tokens > self.configured_max_output_tokens:
            raise ValueError("workflow successor output ceiling differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("workflow successor decision hash differs")
        return self


class WorkflowToolSurfaceV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-workflow-tool-surface-v2"]
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_names: tuple[str, ...]
    expected_check_id: str | None
    selected_tool_schemas: tuple[dict[str, Any], ...]
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]
    provider_calls_authorized: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_surface(self) -> Self:
        if tuple(item.get("name") for item in self.selected_tool_schemas) != (
            self.selected_tool_names
        ):
            raise ValueError("workflow successor schema names differ")
        if self.selected_tool_schema_hash != sha256_json(list(self.selected_tool_schemas)):
            raise ValueError("workflow successor selected schema hash differs")
        if self.content_hash != sha256_json(self.model_dump(mode="json", exclude={"content_hash"})):
            raise ValueError("workflow successor surface hash differs")
        return self


def _artifact_hash(event: RunEvent, visible_payload: dict[str, Any]) -> str:
    descriptor = event.payload.get("result_artifact")
    if not isinstance(descriptor, dict):
        raise RecoveryError("eligible public result lacks an artifact descriptor")
    artifact_hash = descriptor.get("content_hash")
    if (
        not isinstance(artifact_hash, str)
        or event.payload.get("artifact_id") != descriptor.get("artifact_id")
        or event.payload.get("artifact_path") != descriptor.get("path")
        or visible_payload.get("artifact_id") != descriptor.get("artifact_id")
        or visible_payload.get("artifact_path") != descriptor.get("path")
    ):
        raise RecoveryError("eligible public result artifact binding differs")
    return artifact_hash


def _source_projection(tool_result: dict[str, Any]) -> SourceEvidenceProjection | None:
    path = tool_result.get("path")
    content = tool_result.get("content")
    requested_start = tool_result.get("start_line")
    requested_end = tool_result.get("end_line")
    actual_start = tool_result.get("actual_start_line")
    actual_end = tool_result.get("actual_end_line")
    total_lines = tool_result.get("total_lines")
    file_hash = tool_result.get("file_content_hash")
    if not (
        isinstance(path, str)
        and isinstance(content, str)
        and type(requested_start) is int
        and type(requested_end) is int
        and (actual_start is None or type(actual_start) is int)
        and (actual_end is None or type(actual_end) is int)
        and type(total_lines) is int
        and isinstance(file_hash, str)
    ):
        return None
    visible_ranges: tuple[tuple[int, int], ...] = ()
    omitted_ranges: tuple[tuple[int, int], ...] = ()
    partial = False
    if actual_start is not None and actual_end is not None:
        if _TRUNCATION_MARKER in content:
            prefix = content.split(_TRUNCATION_MARKER, 1)[0]
            partial = bool(prefix and not prefix.endswith("\n"))
            complete_lines = prefix.count("\n")
            if complete_lines:
                visible_ranges = ((actual_start, actual_start + complete_lines - 1),)
            omitted_start = actual_start + complete_lines
            if omitted_start <= actual_end:
                omitted_ranges = ((omitted_start, actual_end),)
        else:
            visible_ranges = ((actual_start, actual_end),)
    return SourceEvidenceProjection(
        path=safe_relative_path(path, field_name="eligible source path"),
        requested_range=(requested_start, requested_end),
        actual_range=(actual_start, actual_end) if actual_start is not None else None,
        visible_ranges=visible_ranges,
        omitted_ranges=omitted_ranges,
        partial_line=partial,
        total_lines=total_lines,
        file_content_hash=file_hash,
    )


def _exact_replay_source(event: RunEvent, events: tuple[RunEvent, ...]) -> RunEvent | None:
    if event.type != EventType.TOOL_REPLAYED or event.payload.get("semantic_replay") is True:
        return None
    replay_input_hash = event.payload.get("input_hash")
    if not isinstance(replay_input_hash, str):
        return None
    candidates = [
        prior
        for prior in events
        if prior.sequence < event.sequence
        and prior.type == EventType.TOOL_SUCCEEDED
        and prior.correlation_id == event.correlation_id
        and prior.payload.get("tool") == event.payload.get("tool")
        and prior.payload.get("worktree_diff_hash") == event.payload.get("worktree_diff_hash")
        and prior.payload.get("result_artifact") == event.payload.get("result_artifact")
        and any(
            call.type == EventType.TOOL_CALLED
            and call.sequence < prior.sequence
            and call.correlation_id == prior.correlation_id
            and call.payload.get("input_hash") == replay_input_hash
            for call in events
        )
    ]
    return candidates[-1] if candidates else None


def project_eligible_plan_evidence_catalog(
    *,
    run_id: str,
    task: PublicTask,
    worktree_diff_hash: str,
    model_visible_context: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> EligiblePlanEvidenceCatalog:
    """Project exact plan IDs from the public results visible in one request."""

    if type(task) is not PublicTask or not isinstance(model_visible_context, str):
        raise TypeError("eligible plan evidence requires exact public inputs")
    event_tuple = tuple(events)
    if any(type(event) is not RunEvent or event.run_id != run_id for event in event_tuple):
        raise ContractError("eligible plan evidence event run binding differs")
    try:
        context = json.loads(model_visible_context)
    except json.JSONDecodeError as exc:
        raise ContractError("eligible plan evidence context is not JSON") from exc
    recent = context.get("recent_events") if isinstance(context, dict) else None
    if not isinstance(recent, list):
        raise ContractError("eligible plan evidence context lacks recent events")
    by_sequence = {event.sequence: event for event in event_tuple}
    check_order = tuple(check.id for check in task.visible_checks)
    projected: dict[int, dict[str, Any]] = {}
    visible_sequences: list[int] = []
    for visible in recent:
        if not isinstance(visible, dict) or type(visible.get("sequence")) is not int:
            raise RecoveryError("model-visible event identity differs")
        sequence = int(visible["sequence"])
        durable = by_sequence.get(sequence)
        payload = visible.get("payload")
        if durable is None or not isinstance(payload, dict):
            raise RecoveryError("model-visible event is not durable")
        if visible.get("type") != durable.type.value or payload.get("tool") != durable.payload.get(
            "tool"
        ):
            raise RecoveryError("model-visible event differs from durable public state")
        visible_sequences.append(sequence)
        if durable.type not in {EventType.TOOL_SUCCEEDED, EventType.TOOL_REPLAYED}:
            continue
        source_event = durable
        alias_sequences: tuple[int, ...] = ()
        if durable.type == EventType.TOOL_REPLAYED:
            source_event = _exact_replay_source(durable, event_tuple)  # type: ignore[assignment]
            if source_event is None:
                # Semantic cache replays remain visible navigation support but
                # cannot create a new foundation identity.
                continue
            alias_sequences = (durable.sequence,)
        if (
            source_event.payload.get("worktree_diff_hash") != worktree_diff_hash
            or source_event.payload.get("status") != "succeeded"
        ):
            continue
        tool_result = payload.get("tool_result")
        if not isinstance(tool_result, dict):
            continue
        canonical = source_event.sequence
        tool = source_event.payload.get("tool")
        if tool not in {"read_file", "run_check", "get_diff", "search_files"}:
            continue
        artifact_hash = _artifact_hash(source_event, payload)
        item: dict[str, Any] | None = None
        if tool == "read_file":
            source = _source_projection(tool_result)
            if source is not None and _path_allowed(task, source.path):
                item = {
                    "kind": "source_read",
                    "role": "foundation",
                    "source": source.model_dump(mode="python"),
                    "check": None,
                    "diff_review": None,
                    "search": None,
                }
        elif tool == "run_check":
            check_id = tool_result.get("check_id")
            invocation = tool_result.get("invocation_status")
            behavior = tool_result.get("behavior_status")
            passed = tool_result.get("passed")
            timed_out = tool_result.get("timed_out")
            if (
                isinstance(check_id, str)
                and check_id in check_order
                and invocation == "completed"
                and behavior in {"passed", "failed"}
                and type(passed) is bool
                and timed_out is False
            ):
                check = CheckEvidenceProjection(
                    check_id=check_id,
                    check_index=check_order.index(check_id),
                    invocation_status=invocation,
                    behavior_status=behavior,
                    passed=passed,
                    timed_out=timed_out,
                )
                item = {
                    "kind": (
                        "targeted_check_result"
                        if check.check_index == 0
                        else "visible_check_result"
                    ),
                    "role": "foundation",
                    "source": None,
                    "check": check.model_dump(mode="python"),
                    "diff_review": None,
                    "search": None,
                }
        elif tool == "get_diff":
            patch_hash = tool_result.get("patch_hash") or tool_result.get("worktree_diff_hash")
            changed = tool_result.get("changed_files", [])
            if (
                isinstance(patch_hash, str)
                and isinstance(changed, list)
                and all(isinstance(path, str) for path in changed)
            ):
                item = {
                    "kind": "diff_review_result",
                    "role": "foundation",
                    "source": None,
                    "check": None,
                    "diff_review": {
                        "patch_hash": patch_hash,
                        "changed_files": tuple(changed),
                    },
                    "search": None,
                }
        elif tool == "search_files":
            query = tool_result.get("query")
            matches = tool_result.get("matches")
            if isinstance(query, str) and isinstance(matches, list):
                item = {
                    "kind": "search_support",
                    "role": "support",
                    "source": None,
                    "check": None,
                    "diff_review": None,
                    "search": {
                        "query_hash": sha256_text(query),
                        "path_glob": str(tool_result.get("path_glob", "**/*")),
                        "match_count": len(matches),
                        "truncated": bool(tool_result.get("truncated")),
                    },
                }
        if item is None:
            continue
        candidate = {
            "evidence_id": f"pev:{canonical}",
            "run_id": run_id,
            "worktree_diff_hash": worktree_diff_hash,
            "canonical_event_sequence": canonical,
            "model_visible_event_sequences": (sequence,),
            "replay_alias_event_sequences": alias_sequences,
            "artifact_hash": artifact_hash,
            "visible_projection_hash": sha256_json(tool_result),
            **item,
        }
        prior = projected.get(canonical)
        if prior is not None:
            if any(
                prior[key] != candidate[key]
                for key in candidate
                if key not in {"model_visible_event_sequences", "replay_alias_event_sequences"}
            ):
                raise RecoveryError("eligible replay projection conflicts with its source")
            candidate["model_visible_event_sequences"] = tuple(
                sorted(
                    set(prior["model_visible_event_sequences"])
                    | set(candidate["model_visible_event_sequences"])
                )
            )
            candidate["replay_alias_event_sequences"] = tuple(
                sorted(
                    set(prior["replay_alias_event_sequences"])
                    | set(candidate["replay_alias_event_sequences"])
                )
            )
        projected[canonical] = candidate
    items = tuple(
        EligiblePlanEvidence.model_validate(projected[sequence]) for sequence in sorted(projected)
    )
    body = {
        "schema_version": ELIGIBLE_PLAN_EVIDENCE_SCHEMA,
        "run_id": run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": worktree_diff_hash,
        "model_visible_context_hash": sha256_text(model_visible_context),
        "model_visible_recent_event_sequences": tuple(visible_sequences),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(EligiblePlanEvidenceCatalog, body)


def _pinned_failed_check_item(
    *,
    run_id: str,
    task: PublicTask,
    worktree_diff_hash: str,
    event: RunEvent | None,
) -> tuple[EligiblePlanEvidence | None, str | None]:
    """Project one durable public failed-check event without hydrating raw output."""

    if event is None:
        return None, "event_missing"
    if (
        event.run_id != run_id
        or event.type != EventType.TOOL_SUCCEEDED
        or event.payload.get("tool") != "run_check"
        or event.payload.get("status") != "succeeded"
    ):
        return None, "event_not_successful_check"
    if event.payload.get("worktree_diff_hash") != worktree_diff_hash:
        return None, "stale_diff"
    check_order = tuple(check.id for check in task.visible_checks)
    check_id = event.payload.get("check_id")
    if not isinstance(check_id, str) or check_id not in check_order:
        return None, "unregistered_check"
    if not (
        event.payload.get("invocation_status") == "completed"
        and event.payload.get("behavior_status") == "failed"
        and event.payload.get("passed") is False
        and event.payload.get("timed_out") is False
    ):
        return None, "outcome_not_completed_failure"
    descriptor = event.payload.get("result_artifact")
    if not (
        isinstance(descriptor, dict)
        and isinstance(descriptor.get("content_hash"), str)
        and event.payload.get("artifact_id") == descriptor.get("artifact_id")
        and event.payload.get("artifact_path") == descriptor.get("path")
    ):
        return None, "artifact_binding_invalid"
    check = CheckEvidenceProjection(
        check_id=check_id,
        check_index=check_order.index(check_id),
        invocation_status="completed",
        behavior_status="failed",
        passed=False,
        timed_out=False,
    )
    typed_projection = {
        "schema_version": "pinned-failed-check-projection-v1",
        "check": check.model_dump(mode="json"),
    }
    try:
        item = EligiblePlanEvidence(
            evidence_id=f"pev:{event.sequence}",
            kind=("targeted_check_result" if check.check_index == 0 else "visible_check_result"),
            role="foundation",
            run_id=run_id,
            worktree_diff_hash=worktree_diff_hash,
            canonical_event_sequence=event.sequence,
            model_visible_event_sequences=(event.sequence,),
            replay_alias_event_sequences=(),
            artifact_hash=str(descriptor["content_hash"]),
            visible_projection_hash=sha256_json(typed_projection),
            source=None,
            check=check,
            diff_review=None,
            search=None,
        )
    except ValueError:
        return None, "artifact_binding_invalid"
    return item, None


def project_eligible_plan_evidence_catalog_v2(
    *,
    run_id: str,
    task: PublicTask,
    worktree_diff_hash: str,
    model_visible_context: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
    required_trigger_event_sequence: int | None,
) -> EligiblePlanEvidenceCatalogV2:
    """Project V14 evidence with one stable, typed failed-check trigger pin."""

    event_tuple = tuple(events)
    base = project_eligible_plan_evidence_catalog(
        run_id=run_id,
        task=task,
        worktree_diff_hash=worktree_diff_hash,
        model_visible_context=model_visible_context,
        events=event_tuple,
    )
    status: Literal["not_required", "pinned", "unavailable"] = "not_required"
    reason: str | None = None
    pinned_sequences: tuple[int, ...] = ()
    evidence_id: str | None = None
    items = list(base.items)
    if required_trigger_event_sequence is not None:
        selected = next(
            (event for event in event_tuple if event.sequence == required_trigger_event_sequence),
            None,
        )
        pinned, reason = _pinned_failed_check_item(
            run_id=run_id,
            task=task,
            worktree_diff_hash=worktree_diff_hash,
            event=selected,
        )
        if pinned is None:
            status = "unavailable"
        else:
            status = "pinned"
            evidence_id = pinned.evidence_id
            pinned_sequences = (required_trigger_event_sequence,)
            items = [
                item
                for item in items
                if item.canonical_event_sequence != required_trigger_event_sequence
            ]
            items.append(pinned)
            items.sort(key=lambda item: item.canonical_event_sequence)
    body = {
        **base.model_dump(mode="python", exclude={"schema_version", "content_hash"}),
        "schema_version": ELIGIBLE_PLAN_EVIDENCE_SCHEMA_V2,
        "items": tuple(item.model_dump(mode="python") for item in items),
        "required_trigger_status": status,
        "required_trigger_event_sequence": required_trigger_event_sequence,
        "required_trigger_evidence_id": evidence_id,
        "model_visible_pinned_event_sequences": pinned_sequences,
        "unavailable_reason": reason,
    }
    return _hashed(EligiblePlanEvidenceCatalogV2, body)


def _plan_events_v2(
    *, run_id: str, task: PublicTask, events: tuple[RunEvent, ...]
) -> list[tuple[RunEvent, RecordedWorkPlanV2]]:
    task_hash = sha256_json(task.model_dump(mode="json"))
    result: list[tuple[RunEvent, RecordedWorkPlanV2]] = []
    for event in events:
        if (
            event.type != EventType.PLAN_RECORDED
            or event.payload.get("schema_version") != PLAN_RECORDED_EVENT_SCHEMA_V2
        ):
            continue
        try:
            plan = RecordedWorkPlanV2.model_validate_json(
                json.dumps(
                    event.payload.get("plan"),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            )
        except ValueError as exc:
            raise RecoveryError("durable work-plan event is invalid") from exc
        if (
            event.run_id != run_id
            or plan.run_id != run_id
            or plan.task_id != task.task_id
            or plan.task_version != task.task_version
            or plan.public_task_hash != task_hash
            or event.payload.get("plan_hash") != plan.content_hash
            or event.payload.get("worktree_diff_hash") != plan.worktree_diff_hash
            or event.payload.get("revision_index") != plan.revision_index
            or event.payload.get("parent_plan_hash") != plan.parent_plan_hash
            or event.payload.get("trigger") != plan.trigger
        ):
            raise RecoveryError("durable work-plan event binding differs")
        result.append((event, plan))
    return result


def project_active_work_state(
    *,
    run_id: str,
    task: PublicTask,
    current_diff_hash: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> ActiveWorkState | None:
    event_tuple = tuple(events)
    plans = _plan_events_v2(run_id=run_id, task=task, events=event_tuple)
    if not plans:
        return None
    if plans[0][1].trigger != "initial" or plans[0][1].revision_index != 0:
        raise RecoveryError("work-plan chain lacks one initial plan")
    for (_, prior), (_, current) in zip(plans, plans[1:], strict=False):
        if (
            current.revision_index != prior.revision_index + 1
            or current.parent_plan_hash != prior.content_hash
            or current.trigger == "initial"
        ):
            raise RecoveryError("work-plan revision chain differs")
    direct = [pair for pair in plans if pair[1].worktree_diff_hash == current_diff_hash]
    active_pair = direct[-1] if direct else None
    if active_pair is None:
        linked_patch = next(
            (
                event
                for event in reversed(event_tuple)
                if event.type == EventType.PATCH_APPLIED
                and event.payload.get("worktree_diff_hash") == current_diff_hash
                and isinstance(event.payload.get("plan_hash"), str)
            ),
            None,
        )
        if linked_patch is not None:
            active_pair = next(
                (
                    pair
                    for pair in reversed(plans)
                    if pair[1].content_hash == linked_patch.payload.get("plan_hash")
                ),
                None,
            )
    if active_pair is None:
        return None
    active_index = plans.index(active_pair)
    chain = plans[: active_index + 1]
    summaries = tuple(
        WorkPlanRevisionSummary(
            revision_index=plan.revision_index,
            plan_hash=plan.content_hash,
            trigger=plan.trigger,
            prior_hypothesis_disposition=plan.prior_hypothesis_disposition,
            trigger_check_id=plan.trigger_check_id,
            hypothesis=plan.hypothesis,
            candidate_files=tuple(item.path for item in plan.candidate_files),
        )
        for _, plan in chain[-8:]
    )
    body = {
        "schema_version": ACTIVE_WORK_STATE_SCHEMA,
        "run_id": run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "current_diff_hash": current_diff_hash,
        "initial_plan": chain[0][1].model_dump(mode="python"),
        "latest_plan": chain[-1][1].model_dump(mode="python"),
        "recent_revisions": tuple(item.model_dump(mode="python") for item in summaries),
        "omitted_revision_count": max(0, len(chain) - len(summaries)),
        "chain_hash": sha256_json([plan.content_hash for _, plan in chain]),
        "raw_source_included": False,
        "raw_reasoning_included": False,
        "private_evidence_included": False,
    }
    return _hashed(ActiveWorkState, body)


def _plan_reject(
    reason_code: str,
    message: str,
) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


def validate_work_plan_v2(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    arguments: dict[str, Any],
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
) -> RecordedWorkPlanV2:
    """Validate one initial plan or semantic revision against its request catalog."""

    revision = trigger != "initial"
    required = {
        "observation_status",
        "hypothesis",
        "foundation_evidence_ids",
        "supporting_evidence_ids",
        "candidate_files",
        "intended_change",
        "expected_behavior",
        "unknowns",
        *({"prior_hypothesis_disposition"} if revision else set()),
    }
    if type(arguments) is not dict or set(arguments) != required:
        _plan_reject("plan_shape_invalid", "work-plan arguments differ")
    by_id = {item.evidence_id: item for item in catalog.items}
    foundation_ids = arguments.get("foundation_evidence_ids")
    supporting_ids = arguments.get("supporting_evidence_ids")
    candidates = arguments.get("candidate_files")
    unknowns = arguments.get("unknowns")
    if not (
        isinstance(foundation_ids, list)
        and foundation_ids
        and isinstance(supporting_ids, list)
        and isinstance(candidates, list)
        and candidates
        and isinstance(unknowns, list)
    ):
        _plan_reject("plan_collection_invalid", "work-plan collections differ")
    if any(type(item) is not str or item not in by_id for item in foundation_ids):
        _plan_reject("foundation_evidence_ineligible", "work-plan foundation evidence differs")
    if any(type(item) is not str or item not in by_id for item in supporting_ids):
        _plan_reject("supporting_evidence_ineligible", "work-plan supporting evidence differs")
    foundation = tuple(by_id[item] for item in dict.fromkeys(foundation_ids))
    supporting = tuple(by_id[item] for item in dict.fromkeys(supporting_ids))
    if any(item.role != "foundation" for item in foundation):
        _plan_reject("foundation_role_invalid", "work-plan foundation role differs")
    if any(item.role != "support" for item in supporting):
        _plan_reject("support_role_invalid", "work-plan support role differs")
    normalized_candidates: list[CandidateFileEvidence] = []
    for raw in candidates:
        try:
            candidate = CandidateFileEvidence.model_validate(raw)
        except ValueError:
            _plan_reject("candidate_shape_invalid", "work-plan candidate file differs")
        evidence = by_id.get(candidate.read_evidence_id)
        if (
            evidence is None
            or evidence.kind != "source_read"
            or evidence.source is None
            or evidence.source.path != candidate.path
            or evidence.evidence_id not in {item.evidence_id for item in foundation}
            or not _path_allowed(task, candidate.path)
        ):
            _plan_reject(
                "candidate_read_binding_invalid",
                "work-plan candidate lacks its cited current source read",
            )
        normalized_candidates.append(candidate)
    status = arguments.get("observation_status")
    if trigger == "initial":
        if status == "targeted_check_failed":
            valid = any(
                item.kind == "targeted_check_result"
                and item.check is not None
                and item.check.invocation_status == "completed"
                and item.check.behavior_status == "failed"
                for item in foundation
            )
        elif status == "targeted_check_passed":
            valid = any(
                item.kind == "targeted_check_result"
                and item.check is not None
                and item.check.invocation_status == "completed"
                and item.check.behavior_status == "passed"
                for item in foundation
            )
        elif status == "static_source":
            valid = any(item.kind == "source_read" for item in foundation)
        else:
            valid = False
    elif trigger == "check_failure":
        valid = bool(
            status == "visible_check_failed"
            and any(
                item.canonical_event_sequence == trigger_event_sequence
                and item.kind in {"targeted_check_result", "visible_check_result"}
                and item.check is not None
                and item.check.check_id == trigger_check_id
                and item.check.invocation_status == "completed"
                and item.check.behavior_status == "failed"
                for item in foundation
            )
        )
    else:
        valid = bool(
            status == "review_diff"
            and any(
                item.canonical_event_sequence == trigger_event_sequence
                and item.kind == "diff_review_result"
                for item in foundation
            )
        )
    if not valid:
        _plan_reject("observation_evidence_invalid", "work-plan observation evidence differs")
    body = {
        "schema_version": RECORDED_WORK_PLAN_SCHEMA_V2,
        "run_id": catalog.run_id,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": catalog.public_task_hash,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "observation_status": status,
        "hypothesis": arguments.get("hypothesis"),
        "foundation_evidence": tuple(
            item.model_dump(mode="python")
            for item in sorted(foundation, key=lambda item: item.canonical_event_sequence)
        ),
        "supporting_evidence": tuple(
            item.model_dump(mode="python")
            for item in sorted(supporting, key=lambda item: item.canonical_event_sequence)
        ),
        "candidate_files": tuple(
            item.model_dump(mode="python")
            for item in sorted(normalized_candidates, key=lambda item: item.path)
        ),
        "intended_change": arguments.get("intended_change"),
        "expected_behavior": arguments.get("expected_behavior"),
        "unknowns": tuple(unknowns),
        "planned_check_ids": tuple(check.id for check in task.visible_checks),
        "evidence_catalog_hash": catalog.content_hash,
        "revision_index": revision_index,
        "parent_plan_hash": parent_plan_hash,
        "trigger": trigger,
        "trigger_check_id": trigger_check_id,
        "trigger_event_sequence": trigger_event_sequence,
        "prior_hypothesis_disposition": arguments.get("prior_hypothesis_disposition"),
        "public_evidence_only": True,
        "hidden_evidence_used": False,
        "private_evidence_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    try:
        return _hashed(RecordedWorkPlanV2, body)
    except ValueError as exc:
        _plan_reject("plan_schema_invalid", "work-plan failed its public schema")
        raise AssertionError from exc


def _current_check_outcomes(
    task: PublicTask, evidence: EvidenceState, events: tuple[RunEvent, ...]
) -> dict[str, RunEvent]:
    check_ids = {check.id for check in task.visible_checks}
    mutation_sequence = evidence.mutation_event_sequence or 0
    outcomes: dict[str, RunEvent] = {}
    for event in events:
        if (
            event.sequence > mutation_sequence
            and event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("check_id") in check_ids
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
            and event.payload.get("invocation_status") == "completed"
            and event.payload.get("behavior_status") in {"passed", "failed"}
        ):
            outcomes[str(event.payload["check_id"])] = event
    return outcomes


def required_failed_check_trigger_sequence(
    *,
    run_id: str,
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> int | None:
    """Return the failed-check event that still requires a semantic revision."""

    event_tuple = tuple(events)
    if not evidence.mutation_present or evidence.worktree_diff_hash == _EMPTY_DIFF_HASH:
        return None
    expected_check = next(
        (check.id for check in task.visible_checks if check.id not in evidence.completed_checks),
        None,
    )
    if expected_check is None:
        return None
    outcome = _current_check_outcomes(task, evidence, event_tuple).get(expected_check)
    if outcome is None:
        return None
    if outcome.payload.get("behavior_status") != "failed":
        raise ContractError("required workflow trigger check outcome differs")
    revision_exists = any(
        plan.worktree_diff_hash == evidence.worktree_diff_hash
        and plan.trigger == "check_failure"
        and plan.trigger_event_sequence == outcome.sequence
        for _, plan in _plan_events_v2(run_id=run_id, task=task, events=event_tuple)
    )
    return None if revision_exists else outcome.sequence


def _correction_mutations_by_check(events: tuple[RunEvent, ...]) -> Counter[str]:
    counts: Counter[str] = Counter()
    latest_failed: str | None = None
    for event in events:
        if (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("behavior_status") == "failed"
            and isinstance(event.payload.get("check_id"), str)
        ):
            latest_failed = str(event.payload["check_id"])
        elif event.type == EventType.PATCH_APPLIED:
            if latest_failed is not None:
                counts[latest_failed] += 1
            latest_failed = None
    return counts


def _review_corrections(events: tuple[RunEvent, ...]) -> int:
    pending = False
    count = 0
    for event in events:
        if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") == "get_diff":
            pending = True
        elif event.type == EventType.PATCH_APPLIED:
            if pending:
                count += 1
            pending = False
    return count


def _gate_id(
    *,
    run_id: str,
    current_diff_hash: str,
    trigger: PlanTrigger,
    trigger_event_sequence: int | None,
    parent_plan_hash: str | None,
) -> str:
    return sha256_json(
        {
            "schema_version": "work-plan-gate-identity-v1",
            "run_id": run_id,
            "current_diff_hash": current_diff_hash,
            "trigger": trigger,
            "trigger_event_sequence": trigger_event_sequence,
            "parent_plan_hash": parent_plan_hash,
        }
    )


def _admission_attempts(events: tuple[RunEvent, ...], gate_id: str) -> int:
    return sum(
        event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.payload.get("policy_version") == WORK_PLAN_ADMISSION_POLICY
        and event.payload.get("plan_gate_id") == gate_id
        for event in events
    )


def _decision(
    *,
    runtime: Literal[
        "lean-harness-v11",
        "lean-harness-v12",
        "lean-harness-v13",
        "lean-harness-v14",
    ],
    target: WorkflowTargetV2,
    evidence: EvidenceState,
    expected_check_id: str | None,
    allowed: tuple[str, ...],
    info_count: int,
    fresh_read: bool,
    corrective_count: int,
    review_count: int,
    pre_mutation_count: int,
    active_plan_hash: str | None,
    plan_gate_id: str | None,
    plan_attempts: int,
    trigger_evidence_id: str | None,
    revision_trigger: Literal["check_failure", "review_correction"] | None,
    terminal_reason: Literal[
        "correction_attempt_limit",
        "pre_mutation_evidence_exhausted",
        "work_plan_admission_repeated",
        "required_workflow_evidence_unavailable",
    ]
    | None,
    configured_max_output_tokens: int,
) -> WorkflowDecisionV2:
    ceilings = {
        "phase-policy": configured_max_output_tokens,
        "visible-check": 4_096,
        "correction-investigation": 4_096,
        "corrective-mutation": 12_288,
        "diff-review": 4_096,
        "review-decision": 8_192,
        "pre-mutation-exploration": 4_096,
        "record-work-plan": 8_192,
        "revise-work-plan": 8_192,
        "plan-implementation": 12_288,
        "terminal": 1,
    }
    reasoning = (
        "medium"
        if target
        in {
            "phase-policy",
            "corrective-mutation",
            "record-work-plan",
            "revise-work-plan",
            "plan-implementation",
            "review-decision",
        }
        else "low"
    )
    body = {
        "schema_version": WORKFLOW_DECISION_SCHEMA_V2,
        "runtime_policy_version": runtime,
        "policy_version": (
            WORKFLOW_POLICY_V14
            if runtime == "lean-harness-v14"
            else WORKFLOW_POLICY_V12
            if runtime in {"lean-harness-v12", "lean-harness-v13"}
            else WORKFLOW_POLICY_V11
        ),
        "target": target,
        "current_diff_hash": evidence.worktree_diff_hash,
        "expected_check_id": expected_check_id,
        "allowed_tool_names": allowed,
        "information_actions_in_episode": min(info_count, 3),
        "fresh_current_read": fresh_read,
        "corrective_mutations_for_check": min(corrective_count, 3),
        "review_corrections_used": min(review_count, 1),
        "pre_mutation_actions_used": min(pre_mutation_count, 10),
        "active_plan_hash": active_plan_hash,
        "plan_gate_id": plan_gate_id,
        "plan_admission_recovery_used": plan_attempts > 0,
        "plan_admission_recovery_remaining": 0 if plan_attempts > 0 else 1,
        "required_trigger_evidence_id": trigger_evidence_id,
        "revision_trigger": revision_trigger,
        "terminal_reason": terminal_reason,
        "configured_max_output_tokens": configured_max_output_tokens,
        "effective_max_output_tokens": min(configured_max_output_tokens, ceilings[target]),
        "reasoning_effort": reasoning,
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
    }
    return _hashed(WorkflowDecisionV2, body)


def _catalog_item_for_sequence(
    catalog: EligiblePlanEvidenceCatalog, sequence: int, kinds: set[str]
) -> EligiblePlanEvidence | None:
    return next(
        (
            item
            for item in catalog.items
            if item.canonical_event_sequence == sequence and item.kind in kinds
        ),
        None,
    )


def _latest_edit_rejection(events: tuple[RunEvent, ...], after_sequence: int) -> RunEvent | None:
    return next(
        (
            event
            for event in reversed(events)
            if event.sequence > after_sequence
            and event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") in _MUTATION_TOOLS
        ),
        None,
    )


def _active_plan_event_sequence(events: tuple[RunEvent, ...], active_plan_hash: str) -> int:
    return max(
        (
            event.sequence
            for event in events
            if event.type == EventType.PLAN_RECORDED
            and event.payload.get("schema_version") == PLAN_RECORDED_EVENT_SCHEMA_V2
            and event.payload.get("plan_hash") == active_plan_hash
        ),
        default=0,
    )


def project_workflow_successor_v2(
    *,
    runtime_policy_version: Literal[
        "lean-harness-v11",
        "lean-harness-v12",
        "lean-harness-v13",
        "lean-harness-v14",
    ],
    run_id: str,
    task: PublicTask,
    evidence: EvidenceState,
    events: tuple[RunEvent, ...] | list[RunEvent],
    catalog: EligiblePlanEvidenceCatalog,
    available_tool_names: tuple[str, ...],
    configured_max_output_tokens: int,
) -> WorkflowDecisionV2:
    """Project V11 admission or V12 iterative plan-revision state."""

    event_tuple = tuple(events)
    if runtime_policy_version not in {
        "lean-harness-v11",
        "lean-harness-v12",
        "lean-harness-v13",
        "lean-harness-v14",
    }:
        raise ContractError("unsupported workflow successor v2 runtime")
    if catalog.run_id != run_id or catalog.worktree_diff_hash != evidence.worktree_diff_hash:
        raise ContractError("workflow successor v2 catalog binding differs")
    if len(set(available_tool_names)) != len(available_tool_names):
        raise ContractError("workflow successor v2 tools repeat")
    check_order = tuple(check.id for check in task.visible_checks)
    active = project_active_work_state(
        run_id=run_id,
        task=task,
        current_diff_hash=evidence.worktree_diff_hash,
        events=event_tuple,
    )
    active_hash = active.latest_plan.content_hash if active is not None else None
    review_count = _review_corrections(event_tuple)
    if review_count > 1:
        raise ContractError("review correction limit was bypassed")
    first_patch_sequence = min(
        (event.sequence for event in event_tuple if event.type == EventType.PATCH_APPLIED),
        default=10**18,
    )
    pre_mutation_count = min(
        10,
        sum(
            event.type == EventType.TOOL_CALLED
            and event.sequence < first_patch_sequence
            and event.payload.get("tool") in {"search_files", "read_file", "run_check"}
            for event in event_tuple
        ),
    )

    if not evidence.mutation_present and active is None:
        gate = _gate_id(
            run_id=run_id,
            current_diff_hash=evidence.worktree_diff_hash,
            trigger="initial",
            trigger_event_sequence=None,
            parent_plan_hash=None,
        )
        attempts = _admission_attempts(event_tuple, gate)
        if attempts >= 2:
            return _decision(
                runtime=runtime_policy_version,
                target="terminal",
                evidence=evidence,
                expected_check_id=None,
                allowed=(),
                info_count=0,
                fresh_read=False,
                corrective_count=0,
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                active_plan_hash=None,
                plan_gate_id=gate,
                plan_attempts=1,
                trigger_evidence_id=None,
                revision_trigger=None,
                terminal_reason="work_plan_admission_repeated",
                configured_max_output_tokens=configured_max_output_tokens,
            )
        targeted = next(
            (
                event
                for event in event_tuple
                if event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_check"
                and event.payload.get("check_id") == check_order[0]
                and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
                and event.payload.get("invocation_status") == "completed"
            ),
            None,
        )
        plan_ready = any(
            item.kind == "source_read" and item.role == "foundation" for item in catalog.items
        )
        if pre_mutation_count >= 10:
            return _decision(
                runtime=runtime_policy_version,
                target="record-work-plan" if plan_ready else "terminal",
                evidence=evidence,
                expected_check_id=None,
                allowed=("record_work_plan",) if plan_ready else (),
                info_count=0,
                fresh_read=False,
                corrective_count=0,
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                active_plan_hash=None,
                plan_gate_id=gate,
                plan_attempts=attempts,
                trigger_evidence_id=None,
                revision_trigger=None,
                terminal_reason=None if plan_ready else "pre_mutation_evidence_exhausted",
                configured_max_output_tokens=configured_max_output_tokens,
            )
        allowed = ["search_files", "read_file"]
        if targeted is None:
            allowed.append("run_check")
        if plan_ready:
            allowed.append("record_work_plan")
        return _decision(
            runtime=runtime_policy_version,
            target="pre-mutation-exploration",
            evidence=evidence,
            expected_check_id=check_order[0] if targeted is None else None,
            allowed=tuple(allowed),
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=None,
            plan_gate_id=gate,
            plan_attempts=attempts,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    if not evidence.mutation_present and active is not None:
        allowed = (
            ("apply_structured_edit",)
            if pre_mutation_count >= 10
            else ("search_files", "read_file", "apply_structured_edit")
        )
        return _decision(
            runtime=runtime_policy_version,
            target="plan-implementation",
            evidence=evidence,
            expected_check_id=None,
            allowed=allowed,
            info_count=0,
            fresh_read=True,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=active_hash,
            plan_gate_id=None,
            plan_attempts=0,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    if not evidence.mutation_present or evidence.worktree_diff_hash == _EMPTY_DIFF_HASH:
        allowed = tuple(
            name for name in available_tool_names if name in evidence.allowed_next_actions
        )
        if not allowed:
            raise ContractError("workflow successor v2 phase policy leaves no tool")
        return _decision(
            runtime=runtime_policy_version,
            target="phase-policy",
            evidence=evidence,
            expected_check_id=None,
            allowed=allowed,
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=active_hash,
            plan_gate_id=None,
            plan_attempts=0,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    outcomes = _current_check_outcomes(task, evidence, event_tuple)
    expected_check = next(
        (check_id for check_id in check_order if check_id not in evidence.completed_checks),
        None,
    )
    if expected_check is not None:
        outcome = outcomes.get(expected_check)
        correction_count = _correction_mutations_by_check(event_tuple)[expected_check]
        if outcome is None:
            return _decision(
                runtime=runtime_policy_version,
                target="visible-check",
                evidence=evidence,
                expected_check_id=expected_check,
                allowed=("run_check",),
                info_count=0,
                fresh_read=False,
                corrective_count=correction_count,
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                active_plan_hash=active_hash,
                plan_gate_id=None,
                plan_attempts=0,
                trigger_evidence_id=None,
                revision_trigger=None,
                terminal_reason=None,
                configured_max_output_tokens=configured_max_output_tokens,
            )
        if outcome.payload.get("behavior_status") != "failed":
            raise ContractError("workflow successor v2 current check outcome differs")
        if correction_count >= 3:
            return _decision(
                runtime=runtime_policy_version,
                target="terminal",
                evidence=evidence,
                expected_check_id=expected_check,
                allowed=(),
                info_count=0,
                fresh_read=False,
                corrective_count=correction_count,
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                active_plan_hash=active_hash,
                plan_gate_id=None,
                plan_attempts=0,
                trigger_evidence_id=None,
                revision_trigger=None,
                terminal_reason="correction_attempt_limit",
                configured_max_output_tokens=configured_max_output_tokens,
            )
        episode = tuple(event for event in event_tuple if event.sequence > outcome.sequence)
        if runtime_policy_version in {
            "lean-harness-v12",
            "lean-harness-v13",
            "lean-harness-v14",
        }:
            revision = next(
                (
                    pair
                    for pair in reversed(
                        _plan_events_v2(run_id=run_id, task=task, events=event_tuple)
                    )
                    if pair[1].worktree_diff_hash == evidence.worktree_diff_hash
                    and pair[1].trigger == "check_failure"
                    and pair[1].trigger_event_sequence == outcome.sequence
                ),
                None,
            )
            if revision is not None:
                rejection = _latest_edit_rejection(event_tuple, revision[0].sequence)
                fresh_after_rejection = bool(
                    rejection
                    and any(
                        event.sequence > rejection.sequence
                        and event.type == EventType.TOOL_SUCCEEDED
                        and event.payload.get("tool") == "read_file"
                        and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
                        for event in event_tuple
                    )
                )
                allowed = (
                    ("read_file",)
                    if rejection is not None and not fresh_after_rejection
                    else ("apply_structured_edit",)
                )
                return _decision(
                    runtime=runtime_policy_version,
                    target=(
                        "correction-investigation"
                        if allowed == ("read_file",)
                        else "corrective-mutation"
                    ),
                    evidence=evidence,
                    expected_check_id=expected_check,
                    allowed=allowed,
                    info_count=0,
                    fresh_read=fresh_after_rejection,
                    corrective_count=correction_count,
                    review_count=review_count,
                    pre_mutation_count=pre_mutation_count,
                    active_plan_hash=revision[1].content_hash,
                    plan_gate_id=None,
                    plan_attempts=0,
                    trigger_evidence_id=None,
                    revision_trigger=None,
                    terminal_reason=None,
                    configured_max_output_tokens=configured_max_output_tokens,
                )
            trigger_item = _catalog_item_for_sequence(
                catalog,
                outcome.sequence,
                {"targeted_check_result", "visible_check_result"},
            )
            gate = _gate_id(
                run_id=run_id,
                current_diff_hash=evidence.worktree_diff_hash,
                trigger="check_failure",
                trigger_event_sequence=outcome.sequence,
                parent_plan_hash=active_hash,
            )
            if runtime_policy_version == "lean-harness-v14" and trigger_item is None:
                return _decision(
                    runtime=runtime_policy_version,
                    target="terminal",
                    evidence=evidence,
                    expected_check_id=expected_check,
                    allowed=(),
                    info_count=0,
                    fresh_read=False,
                    corrective_count=correction_count,
                    review_count=review_count,
                    pre_mutation_count=pre_mutation_count,
                    active_plan_hash=active_hash,
                    plan_gate_id=gate,
                    plan_attempts=0,
                    trigger_evidence_id=None,
                    revision_trigger="check_failure",
                    terminal_reason="required_workflow_evidence_unavailable",
                    configured_max_output_tokens=configured_max_output_tokens,
                )
            attempts = _admission_attempts(event_tuple, gate)
            if attempts >= 2:
                return _decision(
                    runtime=runtime_policy_version,
                    target="terminal",
                    evidence=evidence,
                    expected_check_id=expected_check,
                    allowed=(),
                    info_count=0,
                    fresh_read=False,
                    corrective_count=correction_count,
                    review_count=review_count,
                    pre_mutation_count=pre_mutation_count,
                    active_plan_hash=active_hash,
                    plan_gate_id=gate,
                    plan_attempts=1,
                    trigger_evidence_id=(trigger_item.evidence_id if trigger_item else None),
                    revision_trigger="check_failure",
                    terminal_reason="work_plan_admission_repeated",
                    configured_max_output_tokens=configured_max_output_tokens,
                )
            info_events = [
                event
                for event in episode
                if event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") in _INFO_TOOLS
                and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
            ]
            fresh_read = any(event.payload.get("tool") == "read_file" for event in info_events)
            info_count = len(info_events)
            revision_ready = bool(trigger_item and fresh_read)
            if info_count >= 3:
                allowed = ("revise_work_plan",) if revision_ready else ("read_file",)
            elif info_count == 2 and not fresh_read:
                allowed = ("read_file",)
            else:
                allowed_list = ["search_files", "read_file"]
                if revision_ready:
                    allowed_list.append("revise_work_plan")
                allowed = tuple(allowed_list)
            return _decision(
                runtime=runtime_policy_version,
                target=(
                    "revise-work-plan"
                    if allowed == ("revise_work_plan",)
                    else "correction-investigation"
                ),
                evidence=evidence,
                expected_check_id=expected_check,
                allowed=allowed,
                info_count=info_count,
                fresh_read=fresh_read,
                corrective_count=correction_count,
                review_count=review_count,
                pre_mutation_count=pre_mutation_count,
                active_plan_hash=active_hash,
                plan_gate_id=gate,
                plan_attempts=attempts,
                trigger_evidence_id=trigger_item.evidence_id if trigger_item else None,
                revision_trigger="check_failure",
                terminal_reason=None,
                configured_max_output_tokens=configured_max_output_tokens,
            )

        latest_rejection = _latest_edit_rejection(event_tuple, outcome.sequence)
        current_reads = [
            event
            for event in episode
            if event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "read_file"
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
            and (latest_rejection is None or event.sequence > latest_rejection.sequence)
        ]
        info_events = [
            event
            for event in episode
            if event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") in _INFO_TOOLS
            and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
        ]
        info_count = len(info_events)
        fresh_read = bool(current_reads)
        if latest_rejection is not None and not fresh_read:
            allowed = ("read_file",)
        elif info_count >= 3:
            if not fresh_read:
                raise ContractError("workflow successor v2 third investigation lacks a read")
            allowed = ("apply_structured_edit",)
        elif info_count == 2 and not fresh_read:
            allowed = ("read_file",)
        elif fresh_read:
            allowed = ("search_files", "read_file", "apply_structured_edit")
        else:
            allowed = ("search_files", "read_file")
        return _decision(
            runtime=runtime_policy_version,
            target=(
                "corrective-mutation"
                if allowed == ("apply_structured_edit",)
                else "correction-investigation"
            ),
            evidence=evidence,
            expected_check_id=expected_check,
            allowed=allowed,
            info_count=info_count,
            fresh_read=fresh_read,
            corrective_count=correction_count,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=active_hash,
            plan_gate_id=None,
            plan_attempts=0,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )

    if evidence.review_event_sequence is None or not evidence.review_presented_to_model:
        return _decision(
            runtime=runtime_policy_version,
            target="diff-review",
            evidence=evidence,
            expected_check_id=None,
            allowed=("get_diff",),
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=active_hash,
            plan_gate_id=None,
            plan_attempts=0,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )
    if runtime_policy_version == "lean-harness-v11":
        return _decision(
            runtime=runtime_policy_version,
            target="review-decision",
            evidence=evidence,
            expected_check_id=None,
            allowed=("finish_task", "read_file", "search_files", "apply_structured_edit"),
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=active_hash,
            plan_gate_id=None,
            plan_attempts=0,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )
    if review_count >= 1:
        return _decision(
            runtime=runtime_policy_version,
            target="review-decision",
            evidence=evidence,
            expected_check_id=None,
            allowed=("finish_task",),
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=active_hash,
            plan_gate_id=None,
            plan_attempts=0,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )
    review_sequence = evidence.review_event_sequence
    assert review_sequence is not None
    revision = next(
        (
            pair
            for pair in reversed(_plan_events_v2(run_id=run_id, task=task, events=event_tuple))
            if pair[1].worktree_diff_hash == evidence.worktree_diff_hash
            and pair[1].trigger == "review_correction"
            and pair[1].trigger_event_sequence == review_sequence
        ),
        None,
    )
    if revision is not None:
        rejection = _latest_edit_rejection(event_tuple, revision[0].sequence)
        fresh_after_rejection = bool(
            rejection
            and any(
                event.sequence > rejection.sequence
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "read_file"
                and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
                for event in event_tuple
            )
        )
        allowed = (
            ("read_file",)
            if rejection is not None and not fresh_after_rejection
            else ("apply_structured_edit",)
        )
        return _decision(
            runtime=runtime_policy_version,
            target=(
                "correction-investigation" if allowed == ("read_file",) else "corrective-mutation"
            ),
            evidence=evidence,
            expected_check_id=None,
            allowed=allowed,
            info_count=0,
            fresh_read=fresh_after_rejection,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=revision[1].content_hash,
            plan_gate_id=None,
            plan_attempts=0,
            trigger_evidence_id=None,
            revision_trigger=None,
            terminal_reason=None,
            configured_max_output_tokens=configured_max_output_tokens,
        )
    trigger_item = _catalog_item_for_sequence(catalog, review_sequence, {"diff_review_result"})
    gate = _gate_id(
        run_id=run_id,
        current_diff_hash=evidence.worktree_diff_hash,
        trigger="review_correction",
        trigger_event_sequence=review_sequence,
        parent_plan_hash=active_hash,
    )
    attempts = _admission_attempts(event_tuple, gate)
    if attempts >= 2:
        return _decision(
            runtime=runtime_policy_version,
            target="terminal",
            evidence=evidence,
            expected_check_id=None,
            allowed=(),
            info_count=0,
            fresh_read=False,
            corrective_count=0,
            review_count=review_count,
            pre_mutation_count=pre_mutation_count,
            active_plan_hash=active_hash,
            plan_gate_id=gate,
            plan_attempts=1,
            trigger_evidence_id=trigger_item.evidence_id if trigger_item else None,
            revision_trigger="review_correction",
            terminal_reason="work_plan_admission_repeated",
            configured_max_output_tokens=configured_max_output_tokens,
        )
    review_episode = [
        event
        for event in event_tuple
        if event.sequence > review_sequence
        and event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") in _INFO_TOOLS
        and event.payload.get("worktree_diff_hash") == evidence.worktree_diff_hash
    ]
    fresh_read = any(event.payload.get("tool") == "read_file" for event in review_episode)
    revision_ready = bool(trigger_item and fresh_read)
    allowed_list = ["finish_task", "search_files", "read_file"]
    if revision_ready:
        allowed_list.append("revise_work_plan")
    return _decision(
        runtime=runtime_policy_version,
        target="review-decision",
        evidence=evidence,
        expected_check_id=None,
        allowed=tuple(allowed_list),
        info_count=min(len(review_episode), 3),
        fresh_read=fresh_read,
        corrective_count=0,
        review_count=review_count,
        pre_mutation_count=pre_mutation_count,
        active_plan_hash=active_hash,
        plan_gate_id=gate,
        plan_attempts=attempts,
        trigger_evidence_id=trigger_item.evidence_id if trigger_item else None,
        revision_trigger="review_correction",
        terminal_reason=None,
        configured_max_output_tokens=configured_max_output_tokens,
    )


def _bind_plan_schema(
    schema: dict[str, Any],
    *,
    catalog: EligiblePlanEvidenceCatalog,
    revision: bool,
) -> None:
    parameters = schema["parameters"]
    properties = parameters["properties"]
    foundation_ids = [item.evidence_id for item in catalog.items if item.role == "foundation"]
    support_ids = [item.evidence_id for item in catalog.items if item.role == "support"]
    source_items = [item for item in catalog.items if item.kind == "source_read"]
    if not foundation_ids or not source_items:
        raise ContractError("work-plan request lacks eligible foundation source evidence")
    properties["foundation_evidence_ids"]["items"]["enum"] = foundation_ids
    if support_ids:
        properties["supporting_evidence_ids"]["items"]["enum"] = support_ids
    else:
        properties["supporting_evidence_ids"]["maxItems"] = 0
    candidate = properties["candidate_files"]["items"]["properties"]
    candidate["path"]["enum"] = sorted({item.source.path for item in source_items if item.source})
    candidate["read_evidence_id"]["enum"] = [item.evidence_id for item in source_items]
    properties["observation_status"]["enum"] = (
        ["visible_check_failed", "review_diff"]
        if revision
        else ["targeted_check_failed", "targeted_check_passed", "static_source"]
    )


def project_workflow_tool_surface_v2(
    *,
    decision: WorkflowDecisionV2,
    catalog: EligiblePlanEvidenceCatalog,
    source_tool_schemas: tuple[dict[str, Any], ...],
) -> WorkflowToolSurfaceV2:
    source = {item.get("name"): item for item in source_tool_schemas}
    if len(source) != len(source_tool_schemas):
        raise ContractError("workflow successor v2 source schemas differ")
    missing = [name for name in decision.allowed_tool_names if name not in source]
    if missing:
        raise ContractError("workflow successor v2 tool is unavailable: " + ", ".join(missing))
    selected = tuple(copy.deepcopy(source[name]) for name in decision.allowed_tool_names)
    for schema in selected:
        if schema.get("name") == "run_check" and decision.expected_check_id is not None:
            check = schema["parameters"]["properties"]["check_id"]
            check["enum"] = [decision.expected_check_id]
            check["description"] = "This request is bound to: " + decision.expected_check_id
        elif schema.get("name") == "record_work_plan":
            _bind_plan_schema(schema, catalog=catalog, revision=False)
        elif schema.get("name") == "revise_work_plan":
            _bind_plan_schema(schema, catalog=catalog, revision=True)
            status = schema["parameters"]["properties"]["observation_status"]
            status["enum"] = [
                "visible_check_failed"
                if decision.revision_trigger == "check_failure"
                else "review_diff"
            ]
    body = {
        "schema_version": WORKFLOW_SURFACE_SCHEMA_V2,
        "decision_hash": decision.content_hash,
        "evidence_catalog_hash": catalog.content_hash,
        "source_tool_schema_hash": sha256_json(list(source_tool_schemas)),
        "selected_tool_schema_hash": sha256_json(list(selected)),
        "selected_tool_names": decision.allowed_tool_names,
        "expected_check_id": (
            decision.expected_check_id if "run_check" in decision.allowed_tool_names else None
        ),
        "selected_tool_schemas": selected,
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
    }
    return _hashed(WorkflowToolSurfaceV2, body)


def workflow_instruction_v2(
    decision: WorkflowDecisionV2,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalog,
    active_work_state: ActiveWorkState | None,
) -> dict[str, Any]:
    instructions = {
        "phase-policy": "Use one phase-filtered public tool action.",
        "visible-check": "Run exactly the bound public check.",
        "correction-investigation": (
            "Inspect bounded current-diff evidence. A fresh source read is required before edit."
        ),
        "corrective-mutation": "Apply one smallest edit under the active plan or revision.",
        "diff-review": "Obtain and review the complete current diff.",
        "review-decision": (
            "Submit the checked diff or gather source evidence and record the one review revision."
        ),
        "pre-mutation-exploration": (
            "Use the exact eligible evidence IDs below; then record one bounded initial plan."
        ),
        "record-work-plan": "Record the initial plan using only the exact catalog IDs.",
        "revise-work-plan": "Record the required semantic plan revision using exact catalog IDs.",
        "plan-implementation": "Follow the pinned active plan and make one smallest mutation.",
        "terminal": "No provider request is authorized for this terminal state.",
    }
    body = {
        "schema_version": "lean-workflow-instruction-v2",
        "policy_version": decision.policy_version,
        "decision_hash": decision.content_hash,
        "target": decision.target,
        "expected_check_id": decision.expected_check_id,
        "available_tool_names": list(decision.allowed_tool_names),
        "plan_gate_id": decision.plan_gate_id,
        "plan_admission_recovery_used": decision.plan_admission_recovery_used,
        "required_trigger_evidence_id": decision.required_trigger_evidence_id,
        "instruction": instructions[decision.target],
        "public_task_spec": copy.deepcopy(public_task_spec),
        "eligible_plan_evidence_catalog": catalog.model_dump(mode="json"),
        "active_work_plan": (
            active_work_state.latest_plan.model_dump(mode="json")
            if active_work_state is not None
            else None
        ),
        "active_work_state": (
            active_work_state.model_dump(mode="json")
            if decision.runtime_policy_version
            in {"lean-harness-v12", "lean-harness-v13", "lean-harness-v14"}
            and active_work_state is not None
            else None
        ),
        "provider_calls_authorized": False,
    }
    return {**body, "content_hash": sha256_json(body)}


__all__ = [
    "ACTIVE_WORK_STATE_SCHEMA",
    "ActiveWorkState",
    "ELIGIBLE_PLAN_EVIDENCE_SCHEMA",
    "ELIGIBLE_PLAN_EVIDENCE_SCHEMA_V2",
    "EligiblePlanEvidence",
    "EligiblePlanEvidenceCatalog",
    "EligiblePlanEvidenceCatalogV2",
    "PLAN_RECORDED_EVENT_SCHEMA_V2",
    "RECORDED_WORK_PLAN_SCHEMA_V2",
    "RecordedWorkPlanV2",
    "WORKFLOW_POLICY_V11",
    "WORKFLOW_POLICY_V12",
    "WORKFLOW_POLICY_V14",
    "WORK_PLAN_ADMISSION_POLICY",
    "WorkflowDecisionV2",
    "WorkflowToolSurfaceV2",
    "project_active_work_state",
    "project_eligible_plan_evidence_catalog",
    "project_eligible_plan_evidence_catalog_v2",
    "project_workflow_successor_v2",
    "project_workflow_tool_surface_v2",
    "required_failed_check_trigger_sequence",
    "validate_work_plan_v2",
    "workflow_instruction_v2",
]
