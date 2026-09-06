"""Small contracts for the mutable ``dev-head`` runtime."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.contracts import Artifact
from patchloop.util import sha256_json

DEV_RUN_SCHEMA = "dev-run-v1"
DEV_RUNTIME_ID = "dev-head"
DEV_READ_TOOLS = frozenset({"search_files", "read_file"})
DEV_SINGLE_ACTION_TOOLS = frozenset({
    "replace_text", "run_check", "run_probe", "finish_task", "stop_task",
})


def dev_tool_surface_hash() -> str:
    return sha256_json(
        {
            "schema_version": "dev-tool-surface-v25",
            "native_conversation": "single-user-append-only-current-state-v3",
            "native_state_view": "complete-mutable-view-immutable-public-task-v1",
            "model_state_projection": "audit-ledger-separated-native-body-references-v1",
            "current_source_catalog": "file-hash-action-field-range-groups-inline-fallback-v1",
            "native_source_delivery": "exact-path-hash-line-union-references-v1",
            "native_source_reference_limit": 16,
            "public_read_range": "inclusive-1-to-400-lines-advertised-v1",
            "reasoning_context_evidence": "provider-reported-mode-or-null-v1",
            "reads": sorted(DEV_READ_TOOLS),
            "single_actions": sorted(DEV_SINGLE_ACTION_TOOLS),
            "max_parallel_reads": 4,
            "mixed_batches": False,
            "unrestricted_shell": False,
            "new_files": False,
            "turn_decision": [
                "mode",
                "basis",
                "evidence_goal",
                "memory_update",
            ],
            "parallel_read_decisions": "shared_inspect_mode_with_call_specific_rationale",
            "dynamic_workflow_tools": True,
            "mutation_wire": "gateway-bound-exact-anchor-replacement-v2",
            "mutation_evidence_binding": "observed-current-source-union-v2",
            "mutation_source_rebinding": "exact-position-unchanged-complete-line-fragments-v1",
            "inspection_gain": "non-overlapping-public-coverage-v2",
            "inspection_intent_projection": "single-native-intent-with-observation-refs-v1",
            "source_search": "rooted-component-glob-double-star-zero-depth-v1",
            "search_feedback": "eligible-decoded-file-count-v1",
            "mutation_failure": "typed-scope-preview-explicit-path-allowance-v3",
            "completion_horizon": "pre-dispatch-best-path-v2",
            "optional_mutation_admission": "minimum-successor-with-protected-warning-v1",
            "mutation_anchor_guidance": "smallest-sufficient-exact-observed-text-v1",
            "public_check_failure_focus": "public-location-with-unknown-execution-boundary-v2",
            "public_failure_guidance": "diff-currency-and-actual-action-space-v1",
            "completion_guidance": "current-candidate-checks-separate-from-further-edits-v1",
            "public_failure_recurrence": "semantic-site-with-raw-fallback-v1",
            "causal_revision_guidance": "advisory-hypothesis-review-v2",
            "failed_check_repair_action_space": "budget-only-public-inspection-v2",
            "evidence_plateau_transition": "advisory-only-v2",
            "check_recovery_reserve": "order-independent-distinct-failure-bound-v2",
            "context_projection": "observed-priority-merged-24000-chars-v1",
            "observed_source_index": "delivered-lexical-headers-16-entries-4000-chars-v1",
            "tool_closure_warning": "actual-single-inspection-successor-conditional-v1",
            "working_notes": "stable-note-id-independent-body-durable-lifecycle-v3",
            "working_note_feedback": "pre-batch-receipt-with-current-post-batch-ids-v2",
            "working_note_range_feedback": "bounded-never-observed-versus-stale-current-range-v1",
            "working_note_interpretation": "evidence-currency-not-semantic-validation-v1",
            "working_note_check_result": "durable-verdict-exception-with-projected-currency-v1",
            "working_note_guidance": "reusable-facts-separate-from-current-failure-v1",
            "verification_concerns": "original-question-progress-note-exact-noop-v2",
            "check_evidence_identity": "retained-action-check-diff-and-resolution-label-v1",
            "verification_concern_limit": 3,
            "submission_guidance": "required-checks-pass-with-advisory-concern-review-v1",
            "working_note_source_body_chars": 24_000,
            "public_probe": "optional-clean-python-diagnostic-protected-budget-v1",
            "public_probe_discovery": "current-public-snapshot-import-and-environment-limits-v1",
            "mutation_recovery": "atomic-complete-candidate-diff-v2",
            "correction_recovery": "journal-derived-unconsumed-v2",
            "execution_deadline": "shared-active-deadline-owned-cleanup-v1",
            "provider_tool_validation": "schema-exact-null-bounded-diagnostic-v1",
        }
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DevTerminal(StrEnum):
    EVALUATOR_PASS = "EVALUATOR_PASS"
    EVALUATOR_FAIL = "EVALUATOR_FAIL"
    EVALUATOR_ERROR = "EVALUATOR_ERROR"
    COST_CAP_REACHED = "COST_CAP_REACHED"
    PROTOCOL_VIOLATION = "PROTOCOL_VIOLATION"
    INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE"
    PROVIDER_CONTINUATION_ERROR = "PROVIDER_CONTINUATION_ERROR"
    PROVIDER_TIMEOUT_OR_UNKNOWN = "PROVIDER_TIMEOUT_OR_UNKNOWN"
    COUNT_TIMEOUT_OR_UNKNOWN = "COUNT_TIMEOUT_OR_UNKNOWN"
    LIMIT_REACHED = "LIMIT_REACHED"
    TASK_FAILED = "TASK_FAILED"
    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"
    AGENT_STOPPED = "AGENT_STOPPED"


class DevLimits(StrictModel):
    max_model_calls: int = Field(default=40, ge=1)
    max_tool_actions: int = Field(default=100, ge=1)
    max_accepted_mutations: int = Field(default=4, ge=1)
    wall_time_seconds: int = Field(default=1_800, ge=1)
    max_protocol_recoveries: int = Field(default=1, ge=0, le=1)
    max_parallel_reads: int = Field(default=4, ge=1, le=4)
    max_consecutive_inspection_turns: int = Field(default=24, ge=0)
    max_failed_mutation_repair_turns: int = Field(default=3, ge=0)


class CausalRevision(StrictModel):
    falsified_prior_hypothesis: str = Field(min_length=1, max_length=1_500)
    alternative_mechanism: str = Field(min_length=1, max_length=1_500)


class TextReplacementIntent(StrictModel):
    path: str = Field(min_length=1, max_length=1_000)
    old_text: str = Field(min_length=1, max_length=20_000)
    new_text: str = Field(max_length=20_000)
    occurrence: int = Field(default=1, ge=1, le=100)
    hypothesis: str = Field(min_length=1, max_length=1_500)
    expected_behavior: str = Field(min_length=1, max_length=1_500)
    causal_revision: CausalRevision | None = None

    @model_validator(mode="after")
    def replacement_changes_source(self) -> TextReplacementIntent:
        if self.old_text == self.new_text:
            raise ValueError("old_text and new_text must differ")
        return self


class StopIntent(StrictModel):
    reason_code: Literal[
        "insufficient_public_evidence",
        "no_safe_scoped_mutation",
        "public_task_conflict",
    ]
    summary: str = Field(min_length=1, max_length=1_000)
    evidence_span_ids: list[str] = Field(default_factory=list, max_length=8)


class PublicTurnDecision(StrictModel):
    """One bounded public action decision for one requested tool call."""

    mode: Literal["inspect", "mutate", "verify", "finish", "stop"]
    basis: str = Field(min_length=1, max_length=800)
    evidence_goal: str | None = Field(default=None, min_length=1, max_length=500)
    # Notes are parsed independently: an invalid annotation must not reject an action.
    memory_update: Any = None

    @model_validator(mode="after")
    def evidence_goal_matches_mode(self) -> PublicTurnDecision:
        if self.mode == "inspect" and self.evidence_goal is None:
            raise ValueError("inspect decisions require one evidence_goal")
        if self.mode != "inspect" and self.evidence_goal is not None:
            raise ValueError("only inspect decisions may carry an evidence_goal")
        return self


class RequestedTool(StrictModel):
    name: str
    action_id: str = Field(min_length=1, max_length=500)
    arguments: dict[str, Any] = Field(default_factory=dict)
    turn_decision: PublicTurnDecision | None = None


class EncryptedReasoningContinuationItem(StrictModel):
    type: Literal["reasoning"] = "reasoning"
    id: str = Field(min_length=1, max_length=500)
    encrypted_content: str = Field(min_length=1, repr=False)
    status: Literal["in_progress", "completed", "incomplete"] | None = None


class FunctionCallContinuationRef(StrictModel):
    type: Literal["function_call_ref"] = "function_call_ref"
    action_id: str = Field(min_length=1, max_length=500)


class ProviderContinuationArtifact(StrictModel):
    schema_version: Literal["openai-stateless-reasoning-v1"] = "openai-stateless-reasoning-v1"
    output_order: list[EncryptedReasoningContinuationItem | FunctionCallContinuationRef] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def contains_reasoning(self) -> ProviderContinuationArtifact:
        if not any(
            isinstance(item, EncryptedReasoningContinuationItem) for item in self.output_order
        ):
            raise ValueError("provider continuation must contain encrypted reasoning")
        return self


class ProviderContinuationRef(StrictModel):
    schema_version: Literal["provider-continuation-ref-v1"] = "provider-continuation-ref-v1"
    artifact: Artifact
    item_count: int = Field(ge=1)
    reasoning_item_count: int = Field(ge=1)
    order_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def counts_are_possible(self) -> ProviderContinuationRef:
        if self.reasoning_item_count > self.item_count:
            raise ValueError("reasoning continuation count exceeds total item count")
        return self


class DevToolContractViolation(StrictModel):
    field_path: str = Field(min_length=1, max_length=500)
    validation_code: str = Field(min_length=1, max_length=200)


class DevToolContractFailure(StrictModel):
    tool_name: str = Field(min_length=1, max_length=200)
    arguments_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    violations: list[DevToolContractViolation] = Field(min_length=1, max_length=4)
    violations_truncated: bool = False


class DevModelTurn(StrictModel):
    tool_calls: list[RequestedTool] = Field(default_factory=list)
    requested_input_tokens: int | None = None
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    response_id: str | None = None
    response_model: str | None = None
    response_status: str | None = None
    response_reasoning_context: Literal["current_turn", "all_turns"] | None = None
    incomplete_reason: str | None = None
    error_code: str | None = None
    output_item_count: int = Field(default=0, ge=0)
    non_tool_output_item_count: int = Field(default=0, ge=0)
    output_item_types: list[str] = Field(default_factory=list)
    output_shape_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    tool_contract_failure: DevToolContractFailure | None = None
    provider_continuation: ProviderContinuationArtifact | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    continuation_ref: ProviderContinuationRef | None = None


class DevToolResult(StrictModel):
    action_id: str
    input_hash: str
    tool: str
    status: Literal["succeeded", "failed"]
    output: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None
    replayed: bool = False
    evidence_cache_hit: bool = False
    workspace_diff_hash: str | None = None


class DevRunRequest(StrictModel):
    provider: Literal["mock", "openai"]
    task: Path
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] = "medium"
    env_file: Path | None = None
    max_cost_usd: Decimal | None = None
    repeat: int = Field(default=1, ge=1, le=6)
    resume_run_id: str | None = Field(
        default=None,
        pattern=r"^run_dev_[a-zA-Z0-9_-]+$",
    )
    state_root: Path | None = None
    enable_probes: bool = False
    limits: DevLimits = Field(default_factory=DevLimits)

    @model_validator(mode="after")
    def provider_options_match(self) -> DevRunRequest:
        if self.provider == "openai":
            if self.env_file is None:
                raise ValueError("--provider openai requires --env-file")
            if self.max_cost_usd is None or self.max_cost_usd <= 0:
                raise ValueError("--provider openai requires a positive --max-cost-usd")
        elif self.env_file is not None or self.max_cost_usd is not None:
            raise ValueError("--provider mock forbids --env-file and --max-cost-usd")
        if self.resume_run_id is not None and self.repeat != 1:
            raise ValueError("--resume-run-id requires --repeat 1")
        return self


class DevRunEnvelope(StrictModel):
    schema_version: Literal["dev-run-envelope-v1"] = "dev-run-envelope-v1"
    official: Literal[False] = False
    runtime_id: Literal["dev-head"] = "dev-head"
    run_id: str = Field(pattern=r"^run_dev_[a-zA-Z0-9_-]+$")
    provider: Literal["mock", "openai"]
    task_path: str
    task_id: str
    task_version: int = Field(ge=1)
    split: Literal[
        "smoke",
        "dev-train",
        "dev-validation",
        "same-repo-heldout",
        "cross-repo-heldout",
    ]
    base_commit: str
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sandbox_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    probe_image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    probe_profile_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"]
    credential_file_path_hash: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    max_cost_nanos: int = Field(ge=0)
    cost_start_nanos: int = Field(ge=0)
    limits: DevLimits
    sandbox_backend: Literal["local", "docker"]
    evaluator_image_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    created_at: datetime

    @model_validator(mode="after")
    def provider_boundary_is_exact(self) -> DevRunEnvelope:
        if (self.probe_image_digest is None) != (self.probe_profile_hash is None):
            raise ValueError("probe image and profile identities must be paired")
        if self.cost_start_nanos > self.max_cost_nanos:
            raise ValueError("run envelope cost start exceeds its invocation cap")
        if self.provider == "openai":
            if (
                self.credential_file_path_hash is None
                or self.max_cost_nanos <= 0
                or self.sandbox_backend != "docker"
                or self.evaluator_image_digest is None
            ):
                raise ValueError("live run envelope is missing an exact execution boundary")
        elif (
            self.credential_file_path_hash is not None
            or self.max_cost_nanos != 0
            or self.cost_start_nanos != 0
            or self.sandbox_backend != "local"
            or self.evaluator_image_digest is not None
        ):
            raise ValueError("mock run envelope contains a live execution boundary")
        return self
