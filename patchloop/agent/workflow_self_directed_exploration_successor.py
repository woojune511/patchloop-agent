"""Lean V23 bounded self-directed public exploration.

This opt-in successor preserves the V22 runtime and evidence.  It replaces the
mechanical two-range readiness switch with a one-read safety floor and an
explicit model choice: record/revise a public plan, gather one more bounded
piece of public evidence, or stop when the information-action envelope is
exhausted.  The gateway validates provenance and structure only; it never
claims that model-authored prose is semantically correct.
"""

from __future__ import annotations

import copy
from fnmatch import fnmatchcase
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    ActivatedCausalPlanRequest,
    CausalMechanismHistoryEntryV2,
    normalize_activated_causal_plan,
    project_causal_plan_workflow_tool_surface_v2,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    EligibleCausalSourceSpan,
    RecordedCausalPlanV2,
    project_eligible_causal_source_spans,
)
from patchloop.agent.workflow_exploration_gate_activation import (
    project_activated_exploration_plan_request,
)
from patchloop.agent.workflow_exploration_gate_successor import (
    ExplorationGatedCausalPlanRequest,
    ExplorationStateInput,
)
from patchloop.agent.workflow_plan_gate_liveness_successor import (
    EligiblePlanEvidenceCatalogV3,
    workflow_instruction_v7,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    PublicSemanticProgressState,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import (
    ActiveWorkState,
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalog,
    EligiblePlanEvidenceCatalogV2,
    PlanTrigger,
    WorkflowToolSurfaceV2,
    _path_allowed,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, safe_relative_path, sha256_json

SELF_DIRECTED_EXPLORATION_POLICY = "bounded-self-directed-exploration-v1"
SELF_DIRECTED_DECISION_SCHEMA = "lean-workflow-decision-v4"
SELF_DIRECTED_STATE_SCHEMA = "self-directed-exploration-state-v1"
SELF_DIRECTED_INTENT_SCHEMA = "self-directed-investigation-intent-v1"
SELF_DIRECTED_TARGET_SCHEMA = "self-directed-investigation-target-v1"
SELF_DIRECTED_CARD_SCHEMA = "self-directed-investigation-card-v1"
SELF_DIRECTED_PLAN_REQUEST_SCHEMA = "self-directed-exploration-plan-request-v1"
SELF_DIRECTED_READINESS_SCHEMA = "self-directed-readiness-assessment-v1"
SELF_DIRECTED_RECEIPT_SCHEMA = "self-directed-exploration-closure-receipt-v1"
SELF_DIRECTED_BINDING_SCHEMA = "self-directed-exploration-work-plan-binding-v1"
SELF_DIRECTED_SNAPSHOT_SCHEMA = "self-directed-plan-gate-snapshot-v1"
SELF_DIRECTED_PIN_SCHEMA = "recovered-self-directed-plan-gate-pin-v1"
SELF_DIRECTED_CATALOG_SCHEMA = "eligible-plan-evidence-catalog-v4"
SELF_DIRECTED_STOP_SCHEMA = "self-directed-exploration-stop-v1"
SELF_DIRECTED_WORKFLOW_INSTRUCTION_SCHEMA = "lean-workflow-instruction-v8"
SELF_DIRECTED_TERMINAL_REASON = "self_directed_exploration_exhausted"

_PLAN_TOOLS = frozenset({"record_work_plan", "revise_work_plan"})
_INFO_TOOLS = frozenset({"search_files", "read_file"})
_TARGET_ROLES = (
    "ownership_boundary",
    "execution_path",
    "mutation_site",
    "preservation_obligation",
    "falsification",
)
_MAX_PINNED_SOURCE_SPANS = 8
_MAX_PINNED_SOURCE_EVIDENCE = 8


def _hashed(model: type[BaseModel], body: dict[str, Any]) -> Any:
    return model.model_validate({**body, "content_hash": sha256_json(body)})


def _reject(reason_code: str, message: str) -> None:
    raise ContractError(message, details={"reason_codes": [reason_code]})


def _public_text(value: str, *, field_name: str) -> str:
    if not value or value != value.strip() or "\x00" in value:
        raise ValueError(f"{field_name} must be trimmed public text")
    return value


class InvestigationIntentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: Literal["need_more_evidence"]
    blocking_question: str = Field(min_length=1, max_length=1_000)
    basis_source_span_ids: list[str] = Field(min_length=1, max_length=8)
    target_role: Literal[
        "ownership_boundary",
        "execution_path",
        "mutation_site",
        "preservation_obligation",
        "falsification",
    ]
    expected_information_gain: str = Field(min_length=1, max_length=1_500)

    @field_validator("blocking_question", "expected_information_gain")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _public_text(value, field_name="investigation intent")

    @model_validator(mode="after")
    def validate_basis(self) -> Self:
        if self.basis_source_span_ids != list(dict.fromkeys(self.basis_source_span_ids)):
            raise ValueError("investigation intent source spans repeat")
        return self


class InvestigationTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-investigation-target-v1"]
    tool: Literal["search_files", "read_file"]
    query: str | None = Field(default=None, min_length=1, max_length=500)
    path_glob: str | None = Field(default=None, min_length=1, max_length=500)
    path: str | None = Field(default=None, min_length=1)
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    target_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        body = self.model_dump(mode="json", exclude={"target_hash"})
        read_shape = (
            self.query is None
            and self.path_glob is None
            and self.path is not None
            and self.start_line is not None
            and self.end_line is not None
            and self.end_line >= self.start_line
        )
        search_shape = (
            self.query is not None
            and self.path_glob is not None
            and self.path is None
            and self.start_line is None
            and self.end_line is None
        )
        if (
            (self.tool == "read_file" and not read_shape)
            or (self.tool == "search_files" and not search_shape)
            or self.target_hash != sha256_json(body)
        ):
            raise ValueError("self-directed investigation target differs")
        return self


class InvestigationCard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-investigation-card-v1"]
    event_sequence: int = Field(ge=1)
    action_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    intent: InvestigationIntentInput
    intent_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target: InvestigationTarget
    target_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    result_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    novelty_classification: str | None = Field(default=None, max_length=100)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_card(self) -> Self:
        if (
            self.intent_hash != sha256_json(self.intent.model_dump(mode="json"))
            or self.target_hash != self.target.target_hash
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("self-directed investigation card differs")
        return self


class SelfDirectedExplorationState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-exploration-state-v1"]
    policy_version: Literal["bounded-self-directed-exploration-v1"]
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_gate_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: Literal["initial", "check_failure", "review_correction"]
    information_actions_used: int = Field(ge=0, le=10)
    information_action_limit: Literal[3, 10]
    source_spans: tuple[EligibleCausalSourceSpan, ...] = Field(max_length=8)
    distinct_source_coverage_keys: tuple[str, ...] = Field(max_length=8)
    recent_investigations: tuple[InvestigationCard, ...] = Field(max_length=3)
    omitted_investigation_count: int = Field(ge=0)
    investigation_chain_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    available_choices: tuple[Literal["ready_to_plan", "need_more_evidence", "stop_not_ready"], ...]
    active_plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    latest_prior_hypothesis_disposition: Literal["retained", "refined", "rejected"] | None
    public_current_diff_source_only: Literal[True]
    raw_source_body_retained: Literal[False]
    raw_reasoning_retained: Literal[False]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        coverage = tuple(dict.fromkeys(item.coverage_key for item in self.source_spans))
        if (
            coverage != self.distinct_source_coverage_keys
            or self.information_actions_used > self.information_action_limit
            or len(set(self.available_choices)) != len(self.available_choices)
            or (not self.source_spans and "ready_to_plan" in self.available_choices)
            or (
                self.information_actions_used < self.information_action_limit
                and "stop_not_ready" in self.available_choices
            )
            or (
                self.information_actions_used >= self.information_action_limit
                and "need_more_evidence" in self.available_choices
            )
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("self-directed exploration state differs")
        return self


class WorkflowDecisionV4(WorkflowDecisionV3):
    schema_version: Literal["lean-workflow-decision-v4"]
    runtime_policy_version: Literal["lean-harness-v23"]
    policy_version: Literal["bounded-self-directed-exploration-v1"]
    terminal_reason: (
        Literal[
            "correction_attempt_limit",
            "pre_mutation_evidence_exhausted",
            "work_plan_admission_repeated",
            "required_workflow_evidence_unavailable",
            "semantic_no_progress_evidence_exhausted",
            "semantic_no_progress_revision_invalid",
            "self_directed_exploration_exhausted",
        ]
        | None
    )
    self_directed_exploration_state_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    investigation_intent_required: bool
    readiness_choice_available: bool
    stop_choice_available: bool
    minimum_source_read_satisfied: bool

    @model_validator(mode="after")
    def validate_self_directed_decision(self) -> Self:
        if self.minimum_source_read_satisfied is not self.readiness_choice_available:
            raise ValueError("self-directed readiness choice differs")
        if self.stop_choice_available is not (
            "declare_exploration_exhausted" in self.allowed_tool_names
        ):
            raise ValueError("self-directed stop choice differs")
        if self.investigation_intent_required is not bool(
            self.minimum_source_read_satisfied
            and set(self.allowed_tool_names).intersection(_INFO_TOOLS)
        ):
            raise ValueError("self-directed intent requirement differs")
        return self


class ReadinessAssessmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    readiness_status: Literal["ready_to_plan"]
    sufficiency_mode: Literal["multi_range", "co_located_boundary"]
    basis_source_span_ids: list[str] = Field(min_length=1, max_length=8)
    sufficiency_rationale: str = Field(min_length=1, max_length=2_000)
    remaining_unknowns_non_blocking: Literal[True]

    @field_validator("sufficiency_rationale")
    @classmethod
    def normalize_rationale(cls, value: str) -> str:
        return _public_text(value, field_name="readiness rationale")

    @model_validator(mode="after")
    def validate_basis(self) -> Self:
        if self.basis_source_span_ids != list(dict.fromkeys(self.basis_source_span_ids)):
            raise ValueError("readiness source spans repeat")
        return self


class SelfDirectedPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-exploration-plan-request-v1"]
    policy_version: Literal["bounded-self-directed-exploration-v1"]
    source_request: ExplorationGatedCausalPlanRequest
    source_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_activation_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parameters: dict[str, Any]
    parameter_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    minimum_current_source_reads: Literal[1]
    readiness_modes: tuple[Literal["multi_range", "co_located_boundary"], ...]
    unknowns_canonical_source: Literal["exploration_state.unknown_dispositions"]
    duplicated_unknown_text_allowed: Literal[False]
    semantic_truth_verified: Literal[False]
    runtime_surface_activated: Literal[True]
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        properties = self.parameters.get("properties")
        required = self.parameters.get("required")
        if (
            not hasattr(self.source_request, "base_request")
            or self.source_request_hash != self.source_request.content_hash
            or self.base_request_hash != self.source_request.base_request.content_hash
            or not isinstance(properties, dict)
            or not isinstance(required, list)
            or "unknowns" in properties
            or "unknowns" in required
            or "readiness_assessment" not in properties
            or "readiness_assessment" not in required
            or self.parameter_schema_hash != sha256_json(self.parameters)
            or self.readiness_modes != ("multi_range", "co_located_boundary")
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("self-directed plan request differs")
        return self


class SelfDirectedExplorationClosureReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-exploration-closure-receipt-v1"]
    policy_version: Literal["bounded-self-directed-exploration-v1"]
    run_id: str = Field(min_length=1)
    worktree_diff_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    projected_plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_span_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exploration_state: ExplorationStateInput
    readiness_assessment: ReadinessAssessmentInput
    selected_source_spans: tuple[EligibleCausalSourceSpan, ...] = Field(
        min_length=1,
        max_length=8,
    )
    selected_source_coverage_keys: tuple[str, ...] = Field(min_length=1, max_length=8)
    public_current_diff_source_only: Literal[True]
    declared_unknowns_closed: Literal[True]
    semantic_truth_verified: Literal[False]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        coverage = tuple(dict.fromkeys(item.coverage_key for item in self.selected_source_spans))
        if (
            coverage != self.selected_source_coverage_keys
            or any(
                item.run_id != self.run_id or item.worktree_diff_hash != self.worktree_diff_hash
                for item in self.selected_source_spans
            )
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("self-directed exploration receipt differs")
        return self


class SelfDirectedWorkPlanBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-exploration-work-plan-binding-v1"]
    policy_version: Literal["bounded-self-directed-exploration-v1"]
    run_id: str = Field(min_length=1)
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_event_sequence: int = Field(ge=1)
    revision_index: int = Field(ge=0, le=3)
    parent_plan_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: PlanTrigger
    receipt: SelfDirectedExplorationClosureReceipt
    receipt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_evidence_only: Literal[True]
    private_evidence_used: Literal[False]
    hidden_evaluator_used: Literal[False]
    reference_patch_used: Literal[False]
    reasoning_text_used: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

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
            raise ValueError("self-directed work-plan binding differs")
        return self


class SelfDirectedPlanGateSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["self-directed-plan-gate-snapshot-v1"]
    policy_version: Literal["bounded-self-directed-exploration-v1"]
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
        min_length=1,
        max_length=_MAX_PINNED_SOURCE_SPANS,
    )
    distinct_source_coverage_keys: tuple[str, ...] = Field(min_length=1, max_length=8)
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
            or self.content_hash
            != sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        ):
            raise ValueError("self-directed plan-gate snapshot differs")
        return self


class RecoveredSelfDirectedPlanGatePin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["recovered-self-directed-plan-gate-pin-v1"]
    policy_version: Literal["bounded-self-directed-exploration-v1"]
    snapshot: SelfDirectedPlanGateSnapshot
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
            raise ValueError("recovered self-directed plan-gate pin differs")
        return self


class EligiblePlanEvidenceCatalogV4(EligiblePlanEvidenceCatalogV3):
    schema_version: Literal["eligible-plan-evidence-catalog-v4"]
    plan_gate_liveness_policy_version: Literal["bounded-self-directed-exploration-v1"]


def _normalized_search_glob(path_glob: str) -> str:
    normalized = safe_relative_path(path_glob, field_name="path_glob")
    return normalized + "/*" if normalized == "**" or normalized.endswith("/**") else normalized


def _static_glob_prefix(path_glob: str) -> str:
    parts: list[str] = []
    for part in path_glob.split("/"):
        if any(marker in part for marker in ("*", "?", "[")):
            break
        parts.append(part)
    return "/".join(parts)


def _search_glob_allowed(task: PublicTask, path_glob: str) -> bool:
    normalized = _normalized_search_glob(path_glob)
    prefix = _static_glob_prefix(normalized)
    if not prefix:
        return bool(
            any(item in {"**", "**/*"} for item in task.constraints.allowed_paths)
            and not task.constraints.forbidden_paths
        )
    probe = prefix.rstrip("/") + "/__patchloop_probe__.py"
    allowed = any(
        fnmatchcase(probe, pattern)
        or probe.startswith(_static_glob_prefix(pattern).rstrip("/") + "/")
        for pattern in task.constraints.allowed_paths
    )
    forbidden = any(
        fnmatchcase(probe, pattern)
        or prefix.startswith(_static_glob_prefix(pattern).rstrip("/") + "/")
        for pattern in task.constraints.forbidden_paths
        if _static_glob_prefix(pattern)
    )
    return allowed and not forbidden


def project_investigation_target(
    *, tool: Literal["search_files", "read_file"], arguments: dict[str, Any]
) -> InvestigationTarget:
    if tool == "read_file":
        body = {
            "schema_version": SELF_DIRECTED_TARGET_SCHEMA,
            "tool": tool,
            "query": None,
            "path_glob": None,
            "path": safe_relative_path(str(arguments.get("path")), field_name="read path"),
            "start_line": arguments.get("start_line"),
            "end_line": arguments.get("end_line"),
        }
    else:
        body = {
            "schema_version": SELF_DIRECTED_TARGET_SCHEMA,
            "tool": tool,
            "query": arguments.get("query"),
            "path_glob": _normalized_search_glob(str(arguments.get("path_glob", "**/*"))),
            "path": None,
            "start_line": None,
            "end_line": None,
        }
    return InvestigationTarget.model_validate({**body, "target_hash": sha256_json(body)})


def validate_investigation_action(
    *,
    task: PublicTask,
    state: SelfDirectedExplorationState,
    tool: Literal["search_files", "read_file"],
    arguments: dict[str, Any],
    prior_target_hashes: tuple[str, ...] = (),
) -> tuple[InvestigationIntentInput, InvestigationTarget]:
    expected = (
        {"path", "start_line", "end_line", "investigation_intent"}
        if tool == "read_file"
        else {"query", "path_glob", "investigation_intent"}
    )
    if set(arguments) != expected:
        _reject(
            "self_directed_investigation_shape_invalid",
            "self-directed inspection requires its exact operation and investigation intent",
        )
    try:
        intent = InvestigationIntentInput.model_validate(arguments.get("investigation_intent"))
    except ValueError as exc:
        _reject("self_directed_investigation_intent_invalid", "investigation intent differs")
        raise AssertionError from exc
    span_ids = {item.source_span_id for item in state.source_spans}
    if any(item not in span_ids for item in intent.basis_source_span_ids):
        _reject(
            "self_directed_investigation_basis_ineligible",
            "investigation intent cites a source span outside the current request",
        )
    target = project_investigation_target(tool=tool, arguments=arguments)
    if tool == "read_file":
        if not _path_allowed(task, str(target.path)):
            _reject(
                "self_directed_investigation_target_outside_scope",
                "read target is outside the public allowed path scope",
            )
    elif not _search_glob_allowed(task, str(target.path_glob)):
        _reject(
            "self_directed_investigation_target_outside_scope",
            "search target is outside the public allowed path scope",
        )
    if any(not isinstance(item, str) for item in prior_target_hashes):
        raise RecoveryError("self-directed target inventory differs")
    prior = {
        *(item.target_hash for item in state.recent_investigations),
        *prior_target_hashes,
    }
    if target.target_hash in prior:
        _reject(
            "self_directed_investigation_target_repeated",
            "the normalized investigation target already succeeded in this episode",
        )
    return intent, target


def _investigation_cards(
    *, events: tuple[RunEvent, ...], worktree_diff_hash: str, after_sequence: int
) -> tuple[InvestigationCard, ...]:
    cards: list[InvestigationCard] = []
    for event in events:
        if (
            event.sequence <= after_sequence
            or event.type != EventType.TOOL_SUCCEEDED
            or event.payload.get("tool") not in _INFO_TOOLS
            or event.payload.get("worktree_diff_hash") != worktree_diff_hash
            or event.payload.get("self_directed_exploration_policy_version")
            != SELF_DIRECTED_EXPLORATION_POLICY
        ):
            continue
        descriptor = event.payload.get("result_artifact")
        if not isinstance(descriptor, dict) or not isinstance(descriptor.get("content_hash"), str):
            raise RecoveryError("self-directed investigation lacks a result artifact")
        try:
            intent = InvestigationIntentInput.model_validate(
                event.payload.get("investigation_intent")
            )
            target = InvestigationTarget.model_validate(event.payload.get("investigation_target"))
        except ValueError as exc:
            raise RecoveryError("self-directed investigation event is invalid") from exc
        body = {
            "schema_version": SELF_DIRECTED_CARD_SCHEMA,
            "event_sequence": event.sequence,
            "action_id": event.correlation_id,
            "worktree_diff_hash": worktree_diff_hash,
            "intent": intent.model_dump(mode="python"),
            "intent_hash": sha256_json(intent.model_dump(mode="json")),
            "target": target.model_dump(mode="python"),
            "target_hash": target.target_hash,
            "result_artifact_hash": descriptor["content_hash"],
            "novelty_classification": (
                event.payload.get("novelty", {}).get("classification")
                if isinstance(event.payload.get("novelty"), dict)
                else None
            ),
        }
        if not isinstance(body["action_id"], str):
            raise RecoveryError("self-directed investigation lacks an action identity")
        cards.append(_hashed(InvestigationCard, body))
    return tuple(cards)


def project_episode_investigation_target_hashes(
    *,
    events: tuple[RunEvent, ...] | list[RunEvent],
    decision: WorkflowDecisionV3,
    worktree_diff_hash: str,
) -> tuple[str, ...]:
    """Return the exact succeeded target inventory for the current episode."""

    event_tuple = tuple(events)
    cards = _investigation_cards(
        events=event_tuple,
        worktree_diff_hash=worktree_diff_hash,
        after_sequence=_trigger_sequence(decision),
    )
    return tuple(item.target_hash for item in cards)


def _trigger_sequence(decision: WorkflowDecisionV3) -> int:
    evidence_id = decision.required_trigger_evidence_id
    if evidence_id is None:
        return 0
    try:
        return int(evidence_id.split(":", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RecoveryError("self-directed trigger evidence ID differs") from exc


def project_self_directed_exploration_state(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV3,
    catalog: EligiblePlanEvidenceCatalogV2,
    events: tuple[RunEvent, ...] | list[RunEvent],
    active_work_state: ActiveWorkState | None,
) -> SelfDirectedExplorationState | None:
    if decision.plan_gate_id is None:
        return None
    trigger: Literal["initial", "check_failure", "review_correction"] = (
        decision.revision_trigger or "initial"
    )
    limit: Literal[3, 10] = 10 if trigger == "initial" else 3
    used = (
        decision.pre_mutation_actions_used
        if trigger == "initial"
        else decision.information_actions_in_episode
    )
    try:
        source_catalog = project_eligible_causal_source_spans(task=task, catalog=catalog)
        spans = source_catalog.spans[:8]
    except ContractError:
        spans = ()
    event_tuple = tuple(events)
    if any(event.run_id != catalog.run_id for event in event_tuple):
        raise RecoveryError("self-directed exploration contains a foreign run")
    cards = _investigation_cards(
        events=event_tuple,
        worktree_diff_hash=catalog.worktree_diff_hash,
        after_sequence=_trigger_sequence(decision),
    )
    choices: tuple[Literal["ready_to_plan", "need_more_evidence", "stop_not_ready"], ...]
    if used >= limit:
        choices = ("ready_to_plan", "stop_not_ready") if spans else ()
    else:
        choices = ("ready_to_plan", "need_more_evidence") if spans else ("need_more_evidence",)
    body = {
        "schema_version": SELF_DIRECTED_STATE_SCHEMA,
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "run_id": catalog.run_id,
        "task_id": catalog.task_id,
        "worktree_diff_hash": catalog.worktree_diff_hash,
        "plan_gate_id": decision.plan_gate_id,
        "trigger": trigger,
        "information_actions_used": min(used, limit),
        "information_action_limit": limit,
        "source_spans": tuple(item.model_dump(mode="python") for item in spans),
        "distinct_source_coverage_keys": tuple(dict.fromkeys(item.coverage_key for item in spans)),
        "recent_investigations": tuple(item.model_dump(mode="python") for item in cards[-3:]),
        "omitted_investigation_count": max(0, len(cards) - 3),
        "investigation_chain_hash": sha256_json([item.model_dump(mode="json") for item in cards]),
        "available_choices": choices,
        "active_plan_hash": (
            active_work_state.latest_plan.content_hash if active_work_state is not None else None
        ),
        "latest_prior_hypothesis_disposition": (
            active_work_state.latest_plan.prior_hypothesis_disposition
            if active_work_state is not None
            else None
        ),
        "public_current_diff_source_only": True,
        "raw_source_body_retained": False,
        "raw_reasoning_retained": False,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
    }
    return _hashed(SelfDirectedExplorationState, body)


def _decision_v4(
    base: WorkflowDecisionV3,
    state: SelfDirectedExplorationState | None,
    **updates: Any,
) -> WorkflowDecisionV4:
    body = {
        **base.model_dump(
            mode="python",
            exclude={"schema_version", "runtime_policy_version", "policy_version", "content_hash"},
        ),
        "schema_version": SELF_DIRECTED_DECISION_SCHEMA,
        "runtime_policy_version": "lean-harness-v23",
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "self_directed_exploration_state_hash": (state.content_hash if state is not None else None),
        "investigation_intent_required": False,
        "readiness_choice_available": bool(state and state.source_spans),
        "stop_choice_available": False,
        "minimum_source_read_satisfied": bool(state and state.source_spans),
        **updates,
    }
    allowed = tuple(body["allowed_tool_names"])
    body["investigation_intent_required"] = bool(
        body["minimum_source_read_satisfied"] and set(allowed).intersection(_INFO_TOOLS)
    )
    body["stop_choice_available"] = "declare_exploration_exhausted" in allowed
    return _hashed(WorkflowDecisionV4, body)


def _stop_event_exists(
    *, events: tuple[RunEvent, ...], gate_id: str, worktree_diff_hash: str
) -> bool:
    matches = [
        event
        for event in events
        if event.type == EventType.EXPLORATION_STOP_RECORDED
        and event.payload.get("schema_version") == SELF_DIRECTED_STOP_SCHEMA
        and event.payload.get("policy_version") == SELF_DIRECTED_EXPLORATION_POLICY
        and event.payload.get("plan_gate_id") == gate_id
        and event.payload.get("worktree_diff_hash") == worktree_diff_hash
    ]
    if len(matches) > 1:
        raise RecoveryError("self-directed exploration stop repeats")
    return bool(matches)


def project_self_directed_workflow_decision(
    *,
    base_decision: WorkflowDecisionV3,
    state: SelfDirectedExplorationState | None,
    source_tool_schemas: tuple[dict[str, Any], ...],
    events: tuple[RunEvent, ...] | list[RunEvent],
) -> WorkflowDecisionV4:
    event_tuple = tuple(events)
    if base_decision.active_plan_hash is not None:
        pending = [
            event
            for event in event_tuple
            if event.type == EventType.PLAN_RECORDED
            and event.payload.get("plan_hash") == base_decision.active_plan_hash
            and event.payload.get("trigger") in {"initial", "check_failure", "review_correction"}
            and event.payload.get("worktree_diff_hash") == base_decision.current_diff_hash
        ]
        if len(pending) > 1:
            raise RecoveryError("self-directed pending plan repeats")
        if pending:
            binding = self_directed_binding_for_hash(
                run_id=pending[0].run_id,
                plan_hash=base_decision.active_plan_hash,
                events=event_tuple,
            )
            if binding is None:
                raise RecoveryError("self-directed pending plan lacks its closure")
            later = [event for event in event_tuple if event.sequence > pending[0].sequence]
            if not any(event.type == EventType.PATCH_APPLIED for event in later):
                rejection = next(
                    (
                        event
                        for event in reversed(later)
                        if event.type == EventType.TOOL_FAILED
                        and event.payload.get("tool") in {"apply_patch", "apply_structured_edit"}
                    ),
                    None,
                )
                fresh_after_rejection = bool(
                    rejection
                    and any(
                        event.sequence > rejection.sequence
                        and event.type == EventType.TOOL_SUCCEEDED
                        and event.payload.get("tool") == "read_file"
                        and event.payload.get("worktree_diff_hash")
                        == base_decision.current_diff_hash
                        for event in later
                    )
                )
                require_read = rejection is not None and not fresh_after_rejection
                return _decision_v4(
                    base_decision,
                    None,
                    target=("correction-investigation" if require_read else "corrective-mutation"),
                    allowed_tool_names=(
                        ("read_file",) if require_read else ("apply_structured_edit",)
                    ),
                    expected_check_id=None,
                    terminal_reason=None,
                    effective_max_output_tokens=(4_096 if require_read else 12_288),
                    reasoning_effort="medium",
                )
    if state is None:
        return _decision_v4(base_decision, None)
    if _stop_event_exists(
        events=event_tuple,
        gate_id=state.plan_gate_id,
        worktree_diff_hash=state.worktree_diff_hash,
    ):
        return _decision_v4(
            base_decision,
            state,
            target="terminal",
            allowed_tool_names=(),
            expected_check_id=None,
            terminal_reason=SELF_DIRECTED_TERMINAL_REASON,
            effective_max_output_tokens=1,
            reasoning_effort="low",
        )
    hard_terminal = base_decision.terminal_reason in {
        "correction_attempt_limit",
        "work_plan_admission_repeated",
        "required_workflow_evidence_unavailable",
        "semantic_no_progress_revision_invalid",
    }
    if base_decision.target == "terminal" and hard_terminal:
        return _decision_v4(base_decision, state)

    available = {str(item.get("name")) for item in source_tool_schemas}
    plan_tool = "record_work_plan" if state.trigger == "initial" else "revise_work_plan"
    if plan_tool not in available:
        raise RecoveryError("self-directed exploration lacks its plan tool")
    if not state.source_spans and state.information_actions_used >= state.information_action_limit:
        return _decision_v4(
            base_decision,
            state,
            target="terminal",
            allowed_tool_names=(),
            expected_check_id=None,
            terminal_reason=SELF_DIRECTED_TERMINAL_REASON,
            effective_max_output_tokens=1,
            reasoning_effort="low",
        )

    allowed: list[str] = []
    if state.trigger == "review_correction" and "finish_task" in available:
        allowed.append("finish_task")
    if state.information_actions_used < state.information_action_limit:
        allowed.extend(name for name in ("search_files", "read_file") if name in available)
        if state.trigger == "initial" and "run_check" in base_decision.allowed_tool_names:
            allowed.append("run_check")
    if state.source_spans:
        allowed.append(plan_tool)
        if state.information_actions_used >= state.information_action_limit:
            if "declare_exploration_exhausted" not in available:
                raise RecoveryError("self-directed exploration lacks its explicit stop tool")
            allowed.append("declare_exploration_exhausted")
    if not allowed:
        raise RecoveryError("self-directed exploration leaves no bounded action")
    target = (
        "pre-mutation-exploration"
        if state.trigger == "initial"
        else "review-decision"
        if state.trigger == "review_correction"
        else "correction-investigation"
    )
    return _decision_v4(
        base_decision,
        state,
        target=target,
        allowed_tool_names=tuple(dict.fromkeys(allowed)),
        expected_check_id=(base_decision.expected_check_id if "run_check" in allowed else None),
        terminal_reason=None,
        effective_max_output_tokens=min(base_decision.configured_max_output_tokens, 8_192),
        reasoning_effort="medium",
    )


def _readiness_schema(span_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "readiness_status": {"type": "string", "enum": ["ready_to_plan"]},
            "sufficiency_mode": {
                "type": "string",
                "enum": ["multi_range", "co_located_boundary"],
            },
            "basis_source_span_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {"type": "string", "enum": span_ids},
            },
            "sufficiency_rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2_000,
            },
            "remaining_unknowns_non_blocking": {"type": "boolean", "enum": [True]},
        },
        "required": [
            "readiness_status",
            "sufficiency_mode",
            "basis_source_span_ids",
            "sufficiency_rationale",
            "remaining_unknowns_non_blocking",
        ],
        "additionalProperties": False,
    }


def project_self_directed_plan_request(
    base_request: ActivatedCausalPlanRequest,
) -> SelfDirectedPlanRequest:
    source_activation = project_activated_exploration_plan_request(base_request)
    parameters = copy.deepcopy(source_activation.parameters)
    properties = parameters.get("properties")
    required = parameters.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise RecoveryError("self-directed plan parameter schema differs")
    if "unknowns" not in properties or "unknowns" not in required:
        raise RecoveryError("self-directed plan lacks its predecessor unknown field")
    properties.pop("unknowns")
    required.remove("unknowns")
    spans = base_request.source_projection.source_span_catalog.spans
    span_ids = [item.source_span_id for item in spans]
    if not span_ids:
        raise RecoveryError("self-directed plan lacks current source spans")
    properties["readiness_assessment"] = _readiness_schema(span_ids)
    required.append("readiness_assessment")
    body = {
        "schema_version": SELF_DIRECTED_PLAN_REQUEST_SCHEMA,
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "source_request": source_activation.source_request.model_dump(mode="python"),
        "source_request_hash": source_activation.source_request_hash,
        "source_activation_request_hash": source_activation.content_hash,
        "base_request_hash": base_request.content_hash,
        "parameters": parameters,
        "parameter_schema_hash": sha256_json(parameters),
        "minimum_current_source_reads": 1,
        "readiness_modes": ("multi_range", "co_located_boundary"),
        "unknowns_canonical_source": "exploration_state.unknown_dispositions",
        "duplicated_unknown_text_allowed": False,
        "semantic_truth_verified": False,
        "runtime_surface_activated": True,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return _hashed(SelfDirectedPlanRequest, body)


def _intent_parameter_schema(span_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["need_more_evidence"]},
            "blocking_question": {"type": "string", "minLength": 1, "maxLength": 1_000},
            "basis_source_span_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {"type": "string", "enum": span_ids},
            },
            "target_role": {"type": "string", "enum": list(_TARGET_ROLES)},
            "expected_information_gain": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1_500,
            },
        },
        "required": [
            "status",
            "blocking_question",
            "basis_source_span_ids",
            "target_role",
            "expected_information_gain",
        ],
        "additionalProperties": False,
    }


def project_self_directed_tool_surface(
    *,
    task: PublicTask,
    decision: WorkflowDecisionV4,
    catalog: EligiblePlanEvidenceCatalogV4,
    state: SelfDirectedExplorationState | None,
    source_tool_schemas: tuple[dict[str, Any], ...],
    cross_reset_trigger: CrossResetFailureTrigger | None,
) -> tuple[WorkflowToolSurfaceV2, SelfDirectedPlanRequest | None]:
    surface, base_request = project_causal_plan_workflow_tool_surface_v2(
        task=task,
        decision=decision,
        catalog=catalog,
        source_tool_schemas=source_tool_schemas,
        cross_reset_trigger=cross_reset_trigger,
    )
    request = project_self_directed_plan_request(base_request) if base_request else None
    selected = [copy.deepcopy(item) for item in surface.selected_tool_schemas]
    span_ids = [item.source_span_id for item in state.source_spans] if state else []
    for schema in selected:
        name = schema.get("name")
        if name in _PLAN_TOOLS:
            if request is None:
                raise RecoveryError("self-directed plan surface lacks its dynamic request")
            schema["parameters"] = copy.deepcopy(request.parameters)
            schema["description"] = (
                "Record the bounded public causal plan and explicitly declare why the "
                "currently visible source evidence is sufficient for mutation."
            )
        elif name in _INFO_TOOLS and decision.investigation_intent_required:
            parameters = schema.get("parameters")
            if not isinstance(parameters, dict):
                raise RecoveryError("self-directed inspection schema differs")
            properties = parameters.get("properties")
            required = parameters.get("required")
            if not isinstance(properties, dict) or not isinstance(required, list):
                raise RecoveryError("self-directed inspection parameters differ")
            properties["investigation_intent"] = _intent_parameter_schema(span_ids)
            required.append("investigation_intent")
            schema["description"] = (
                str(schema.get("description", ""))
                + " State the blocking public question and expected information gain."
            )
        elif name == "declare_exploration_exhausted":
            parameters = schema["parameters"]
            parameters["properties"]["basis_source_span_ids"]["items"]["enum"] = span_ids
            schema["description"] = (
                "Stop without mutation or submission because the bounded public exploration "
                "budget is exhausted and the agent is not ready to plan."
            )
    body = {
        **surface.model_dump(mode="python", exclude={"content_hash", "selected_tool_schema_hash"}),
        "selected_tool_schemas": tuple(selected),
        "selected_tool_schema_hash": sha256_json(selected),
    }
    return _hashed(WorkflowToolSurfaceV2, body), request


def _selected_state_span_ids(state: ExplorationStateInput) -> tuple[str, ...]:
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


def normalize_self_directed_plan(
    *,
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    request_projection: SelfDirectedPlanRequest,
    trigger: PlanTrigger,
    revision_index: int,
    parent_plan_hash: str | None,
    trigger_check_id: str | None,
    trigger_event_sequence: int | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    raw_arguments: dict[str, Any],
) -> tuple[RecordedCausalPlanV2, SelfDirectedExplorationClosureReceipt]:
    exact = project_self_directed_plan_request(request_projection.source_request.base_request)
    if request_projection != exact:
        raise RecoveryError("self-directed plan request projection differs")
    if set(raw_arguments) != set(request_projection.parameters.get("required", [])):
        _reject("self_directed_plan_input_shape_invalid", "self-directed plan input differs")
    try:
        state = ExplorationStateInput.model_validate(raw_arguments.get("exploration_state"))
        readiness = ReadinessAssessmentInput.model_validate(
            raw_arguments.get("readiness_assessment")
        )
    except ValueError as exc:
        _reject("self_directed_plan_input_shape_invalid", "self-directed plan input differs")
        raise AssertionError from exc
    if state.open_blocking_unknowns:
        _reject(
            "self_directed_blocking_unknowns_open",
            "mutation-relevant public questions remain unresolved",
        )
    questions = [item.question for item in state.unknown_dispositions]
    if len(questions) != len(set(questions)):
        _reject("self_directed_unknown_question_repeated", "unknown questions repeat")
    normalized = {
        key: copy.deepcopy(value)
        for key, value in raw_arguments.items()
        if key not in {"exploration_state", "readiness_assessment"}
    }
    normalized["unknowns"] = questions
    projected = normalize_activated_causal_plan(
        task=task,
        catalog=catalog,
        request_projection=request_projection.source_request.base_request,
        trigger=trigger,
        revision_index=revision_index,
        parent_plan_hash=parent_plan_hash,
        trigger_check_id=trigger_check_id,
        trigger_event_sequence=trigger_event_sequence,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        raw_arguments=normalized,
    )
    span_by_id = {
        item.source_span_id: item
        for item in (
            request_projection.source_request.base_request.source_projection.source_span_catalog.spans
        )
    }
    selected_ids = tuple(
        dict.fromkeys((*_selected_state_span_ids(state), *readiness.basis_source_span_ids))
    )
    if any(item not in span_by_id for item in selected_ids):
        _reject(
            "self_directed_source_span_ineligible",
            "self-directed plan cites a source span outside the current request",
        )
    selected = tuple(span_by_id[item] for item in selected_ids)
    boundary = state.boundary_coverage
    boundary_ids = {
        *boundary.ownership_boundary_span_ids,
        *boundary.execution_boundary_span_ids,
        *boundary.mutation_boundary_span_ids,
    }
    mechanism_ids = {
        item.source_span.source_span_id for item in projected.causal_mechanism.causal_path
    }
    if not boundary_ids.issubset(mechanism_ids):
        _reject(
            "self_directed_boundary_outside_mechanism",
            "exploration boundaries must be represented by the causal mechanism",
        )
    mutation_ids = set(boundary.mutation_boundary_span_ids)
    candidate_ids = {item.source_span_id for item in projected.candidate_source_spans}
    mechanism_mutation_id = projected.causal_mechanism.causal_path[-1].source_span.source_span_id
    if mechanism_mutation_id not in mutation_ids or not mutation_ids.intersection(candidate_ids):
        _reject(
            "self_directed_mutation_boundary_unbound",
            "mutation coverage must bind the selected candidate and mechanism mutation site",
        )
    basis = tuple(readiness.basis_source_span_ids)
    basis_keys = tuple(dict.fromkeys(span_by_id[item].coverage_key for item in basis))
    if readiness.sufficiency_mode == "multi_range":
        if len(basis_keys) < 2 or not set(basis).issubset(boundary_ids):
            _reject(
                "self_directed_multi_range_insufficient",
                "multi-range readiness requires two distinct current boundary ranges",
            )
    else:
        role_ids = (
            tuple(dict.fromkeys(boundary.ownership_boundary_span_ids)),
            tuple(dict.fromkeys(boundary.execution_boundary_span_ids)),
            tuple(dict.fromkeys(boundary.mutation_boundary_span_ids)),
        )
        if (
            len(basis) != 1
            or len(basis_keys) != 1
            or any(items != basis for items in role_ids)
            or projected.causal_mechanism.causal_path[0].source_span.source_span_id != basis[0]
            or mechanism_mutation_id != basis[0]
            or basis[0] not in candidate_ids
            or not any(
                basis[0] in item.evidence_source_span_ids for item in state.preservation_obligations
            )
        ):
            _reject(
                "self_directed_colocated_boundary_invalid",
                "one-range readiness must bind ownership, execution, mutation, "
                "candidate, and preservation",
            )
    body = {
        "schema_version": SELF_DIRECTED_RECEIPT_SCHEMA,
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "run_id": projected.run_id,
        "worktree_diff_hash": projected.worktree_diff_hash,
        "projected_plan_hash": projected.content_hash,
        "request_projection_hash": request_projection.content_hash,
        "source_span_catalog_hash": (
            request_projection.source_request.base_request.source_projection.source_span_catalog.content_hash
        ),
        "exploration_state": state.model_dump(mode="python"),
        "readiness_assessment": readiness.model_dump(mode="python"),
        "selected_source_spans": tuple(item.model_dump(mode="python") for item in selected),
        "selected_source_coverage_keys": tuple(
            dict.fromkeys(item.coverage_key for item in selected)
        ),
        "public_current_diff_source_only": True,
        "declared_unknowns_closed": True,
        "semantic_truth_verified": False,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return projected, _hashed(SelfDirectedExplorationClosureReceipt, body)


def build_self_directed_work_plan_binding(
    *,
    plan: Any,
    plan_event_sequence: int,
    projected: RecordedCausalPlanV2,
    receipt: SelfDirectedExplorationClosureReceipt,
) -> SelfDirectedWorkPlanBinding:
    if (
        receipt.run_id != plan.run_id
        or receipt.worktree_diff_hash != plan.worktree_diff_hash
        or receipt.projected_plan_hash != projected.content_hash
        or projected.revision_index != plan.revision_index
        or projected.parent_plan_hash != plan.parent_plan_hash
        or projected.trigger != plan.trigger
    ):
        raise ContractError("self-directed closure does not bind the active plan")
    body = {
        "schema_version": SELF_DIRECTED_BINDING_SCHEMA,
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
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
    return _hashed(SelfDirectedWorkPlanBinding, body)


def self_directed_closure_event_payload(
    *, binding: SelfDirectedWorkPlanBinding, request_projection: SelfDirectedPlanRequest
) -> dict[str, Any]:
    if binding.receipt.request_projection_hash != request_projection.content_hash:
        raise RecoveryError("self-directed closure request projection differs")
    return {
        "schema_version": "self-directed-exploration-closure-recorded-v1",
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "plan_hash": binding.plan_hash,
        "binding": binding.model_dump(mode="python"),
        "binding_hash": binding.content_hash,
        "activated_request_hash": request_projection.content_hash,
        "source_request_hash": request_projection.source_request_hash,
    }


def self_directed_binding_for_hash(
    *, run_id: str, plan_hash: str, events: tuple[RunEvent, ...] | list[RunEvent]
) -> SelfDirectedWorkPlanBinding | None:
    event_tuple = tuple(events)
    plan_events = {
        event.sequence: event for event in event_tuple if event.type == EventType.PLAN_RECORDED
    }
    matches: list[SelfDirectedWorkPlanBinding] = []
    for event in event_tuple:
        if (
            event.type != EventType.EXPLORATION_CLOSURE_RECORDED
            or event.payload.get("policy_version") != SELF_DIRECTED_EXPLORATION_POLICY
        ):
            continue
        try:
            binding = SelfDirectedWorkPlanBinding.model_validate_json(
                canonical_json(event.payload.get("binding"))
            )
        except ValueError as exc:
            raise RecoveryError("self-directed closure binding event is invalid") from exc
        plan_event = plan_events.get(binding.plan_event_sequence)
        if (
            event.run_id != run_id
            or binding.run_id != run_id
            or event.payload.get("binding_hash") != binding.content_hash
            or event.payload.get("plan_hash") != binding.plan_hash
            or plan_event is None
            or plan_event.payload.get("plan_hash") != binding.plan_hash
            or plan_event.payload.get("self_directed_closure_receipt_hash") != binding.receipt_hash
        ):
            raise RecoveryError("self-directed closure event binding differs")
        if binding.plan_hash == plan_hash:
            matches.append(binding)
    if len(matches) > 1:
        raise RecoveryError("self-directed closure binding repeats")
    return matches[0] if matches else None


def project_self_directed_plan_gate_snapshot(
    *, task: PublicTask, decision: WorkflowDecisionV4, catalog: EligiblePlanEvidenceCatalogV2
) -> SelfDirectedPlanGateSnapshot | None:
    if (
        decision.plan_gate_id is None
        or decision.active_plan_hash is not None
        or decision.revision_trigger is not None
    ):
        return None
    try:
        source_catalog = project_eligible_causal_source_spans(task=task, catalog=catalog)
    except ContractError:
        return None
    spans = source_catalog.spans[:_MAX_PINNED_SOURCE_SPANS]
    if not spans:
        return None
    evidence_ids = tuple(dict.fromkeys(item.read_evidence_id for item in spans))
    evidence_by_id = {item.evidence_id: item for item in catalog.items}
    try:
        evidence = tuple(evidence_by_id[item] for item in evidence_ids)
    except KeyError as exc:
        raise RecoveryError("self-directed snapshot lost its source evidence") from exc
    body = {
        "schema_version": SELF_DIRECTED_SNAPSHOT_SCHEMA,
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
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
    return _hashed(SelfDirectedPlanGateSnapshot, body)


def bind_recovered_self_directed_pin(
    *,
    snapshot: SelfDirectedPlanGateSnapshot,
    source_model_event_sequence: int,
    source_request_artifact_hash: str,
    source_request_body_hash: str,
) -> RecoveredSelfDirectedPlanGatePin:
    body = {
        "schema_version": SELF_DIRECTED_PIN_SCHEMA,
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "snapshot": snapshot.model_dump(mode="python"),
        "snapshot_hash": snapshot.content_hash,
        "source_model_event_sequence": source_model_event_sequence,
        "source_request_artifact_hash": source_request_artifact_hash,
        "source_request_body_hash": source_request_body_hash,
        "actual_model_visible_request": True,
    }
    return _hashed(RecoveredSelfDirectedPlanGatePin, body)


def project_self_directed_evidence_catalog(
    *,
    base: EligiblePlanEvidenceCatalogV2,
    pin: RecoveredSelfDirectedPlanGatePin | None,
) -> EligiblePlanEvidenceCatalogV4:
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
            raise RecoveryError("self-directed plan-gate pin is stale or foreign")
        by_sequence = {item.canonical_event_sequence: item for item in items}
        for item in snapshot.source_evidence:
            prior = by_sequence.get(item.canonical_event_sequence)
            if prior is not None and prior != item:
                raise RecoveryError("self-directed pinned evidence conflicts")
            by_sequence[item.canonical_event_sequence] = item
        items = [by_sequence[key] for key in sorted(by_sequence)]
        pinned_ids = tuple(item.evidence_id for item in snapshot.source_evidence)
    body = {
        **base.model_dump(mode="python", exclude={"schema_version", "content_hash"}),
        "schema_version": SELF_DIRECTED_CATALOG_SCHEMA,
        "items": tuple(item.model_dump(mode="python") for item in items),
        "plan_gate_liveness_policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "plan_gate_readiness_status": "pinned" if pin is not None else "not_pinned",
        "plan_gate_readiness_pin_hash": pin.content_hash if pin is not None else None,
        "plan_gate_pinned_evidence_ids": pinned_ids,
        "source_model_event_sequence": (
            pin.source_model_event_sequence if pin is not None else None
        ),
    }
    return _hashed(EligiblePlanEvidenceCatalogV4, body)


def validate_exploration_stop(
    *, state: SelfDirectedExplorationState, arguments: dict[str, Any]
) -> dict[str, Any]:
    expected = {
        "status",
        "blocking_question",
        "basis_source_span_ids",
        "reason",
    }
    if set(arguments) != expected:
        _reject("self_directed_stop_shape_invalid", "exploration stop input differs")
    if (
        arguments.get("status") != "not_ready"
        or arguments.get("reason") != "evidence_budget_exhausted"
        or state.information_actions_used < state.information_action_limit
        or "stop_not_ready" not in state.available_choices
    ):
        _reject("self_directed_stop_not_available", "exploration stop is not available")
    question = arguments.get("blocking_question")
    basis = arguments.get("basis_source_span_ids")
    if not isinstance(question, str):
        _reject("self_directed_stop_question_invalid", "exploration stop question differs")
    try:
        _public_text(question, field_name="exploration stop question")
    except ValueError as exc:
        _reject("self_directed_stop_question_invalid", "exploration stop question differs")
        raise AssertionError from exc
    if (
        not isinstance(basis, list)
        or not basis
        or basis != list(dict.fromkeys(basis))
        or any(item not in {span.source_span_id for span in state.source_spans} for item in basis)
    ):
        _reject("self_directed_stop_basis_ineligible", "exploration stop basis differs")
    return {
        "schema_version": SELF_DIRECTED_STOP_SCHEMA,
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "run_id": state.run_id,
        "worktree_diff_hash": state.worktree_diff_hash,
        "plan_gate_id": state.plan_gate_id,
        "status": "not_ready",
        "blocking_question": question,
        "basis_source_span_ids": basis,
        "reason": "evidence_budget_exhausted",
        "information_actions_used": state.information_actions_used,
        "information_action_limit": state.information_action_limit,
        "investigation_chain_hash": state.investigation_chain_hash,
        "patch_created": False,
        "submission_created": False,
        "public_evidence_only": True,
        "private_evidence_used": False,
        "reasoning_text_used": False,
    }


def workflow_instruction_v8(
    decision: WorkflowDecisionV4,
    *,
    public_task_spec: dict[str, Any],
    catalog: EligiblePlanEvidenceCatalogV4,
    active_work_state: ActiveWorkState | None,
    semantic_progress_state: PublicSemanticProgressState | None,
    cross_reset_trigger: CrossResetFailureTrigger | None,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
    request_projection: SelfDirectedPlanRequest | None,
    readiness: SelfDirectedPlanGateSnapshot | None,
    recovered_pin: RecoveredSelfDirectedPlanGatePin | None,
    self_directed_state: SelfDirectedExplorationState | None,
) -> dict[str, Any]:
    base = workflow_instruction_v7(
        decision,
        public_task_spec=public_task_spec,
        catalog=catalog,
        active_work_state=active_work_state,
        semantic_progress_state=semantic_progress_state,
        cross_reset_trigger=cross_reset_trigger,
        history=history,
        request_projection=request_projection,
        readiness=readiness,
        recovered_pin=recovered_pin,
    )
    body = {
        **{key: value for key, value in base.items() if key != "content_hash"},
        "self_directed_instruction_schema_version": (SELF_DIRECTED_WORKFLOW_INSTRUCTION_SCHEMA),
        "self_directed_exploration_policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "self_directed_exploration_state": (
            self_directed_state.model_dump(mode="json") if self_directed_state is not None else None
        ),
        "self_directed_exploration_state_hash": (
            self_directed_state.content_hash
            if self_directed_state is not None
            else sha256_json(None)
        ),
    }
    if self_directed_state is not None:
        if decision.stop_choice_available:
            body["instruction"] = (
                "The bounded public exploration limit is reached. Record/revise the plan "
                "only if the visible source evidence is sufficient; otherwise explicitly "
                "stop without mutation or submission."
            )
        elif decision.readiness_choice_available:
            body["instruction"] = (
                "Choose exactly one action: record/revise the plan if the current public "
                "source evidence is sufficient, or search/read with a blocking question "
                "and expected information gain."
            )
        else:
            body["instruction"] = (
                "Acquire at least one current-diff public source read before planning."
            )
    return {**body, "content_hash": sha256_json(body)}


__all__ = [
    "EligiblePlanEvidenceCatalogV4",
    "InvestigationIntentInput",
    "InvestigationTarget",
    "ReadinessAssessmentInput",
    "RecoveredSelfDirectedPlanGatePin",
    "SELF_DIRECTED_EXPLORATION_POLICY",
    "SELF_DIRECTED_STOP_SCHEMA",
    "SELF_DIRECTED_TERMINAL_REASON",
    "SelfDirectedExplorationClosureReceipt",
    "SelfDirectedExplorationState",
    "SelfDirectedPlanGateSnapshot",
    "SelfDirectedPlanRequest",
    "SelfDirectedWorkPlanBinding",
    "WorkflowDecisionV4",
    "bind_recovered_self_directed_pin",
    "build_self_directed_work_plan_binding",
    "normalize_self_directed_plan",
    "project_investigation_target",
    "project_episode_investigation_target_hashes",
    "project_self_directed_evidence_catalog",
    "project_self_directed_exploration_state",
    "project_self_directed_plan_gate_snapshot",
    "project_self_directed_plan_request",
    "project_self_directed_tool_surface",
    "project_self_directed_workflow_decision",
    "self_directed_binding_for_hash",
    "self_directed_closure_event_payload",
    "validate_exploration_stop",
    "validate_investigation_action",
    "workflow_instruction_v8",
]
