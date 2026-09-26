"""Small contracts for the mutable ``dev-head`` runtime."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from patchloop.contracts import Artifact, ProbeDependencyIdentity
from patchloop.dev import check_review, cost, probe_cases, segments
from patchloop.util import sha256_json

DEV_RUN_SCHEMA = "dev-run-v1"
DEV_RUNTIME_ID = "dev-head"
DEV_READ_TOOLS = frozenset({"search_files", "read_file"})
DEV_SINGLE_ACTION_TOOLS = frozenset({
    "replace_text", "run_check", "run_probe", "finish_task", "stop_task",
})


def dev_tool_surface_hash(*, planning_policy: str = "none", probe_policy: str = "none") -> str:
    base = sha256_json(
        {
            "schema_version": "dev-tool-surface-v45",
            "segmented_context": segments.contract(),
            "native_context_policy": "opt-in-full-compaction-seed-public-reentry-prepared-count-v2",
            "repair_recheck": "opt-in-current-failure-child-check-before-inference-v1",
            "sandbox_exception_cleanup": "typed-uncertainty-preserved-through-gateway-v1",
            "registered_check_capture": "bounded-prefix-drain-verdict-preserving-v1",
            "git_execution": "exact-file-capture-active-deadline-uncertainty-stop-v1",
            "active_execution_start": "before-workspace-preflight-bounded-recovery-tail-v1",
            "evaluation_completion": "durable-receipt-leaf-cas-metadata-only-resume-v1",
            "public_check_focus": "current-failure-or-pending-recheck-native-receipt-v1",
            "repair_followup": "recheck-before-reusing-older-failure-advisory-v1",
            "public_check_output": "complete-line-prefix-and-tail-accurate-truncation-v1",
            "public_check_output_character_limits": [12_000, 4_000],
            "public_check_diagnostics": "captured-public-terminal-format-or-null-v1",
            "public_check_diagnostic_bounds": [8, 4_000],
            "mutation_result_identity": "completed-worktree-and-explicit-baseline-v1",
            "native_mutation_output": "admitted-position-prior-body-references-v1",
            "mutation_rebind_reference_limit": 16,
            "mutation_projection": "no-obsolete-alternative-requirement-v1",
            "stop_wire": "reason-and-summary-no-model-source-ids-v1",
            "public_execution_feedback": "current-diff-changed-python-launch-thread-lines-v1",
            "public_execution_feedback_bounds": [8, 256, 12_000],
            "public_execution_report_limit_bytes": 16_000,
            "native_conversation": "single-user-append-only-current-state-v3",
            "native_state_view": "complete-mutable-view-immutable-public-task-v1",
            "model_state_projection": "current-completion-first-native-body-references-v2",
            "current_source_catalog": "file-hash-delivery-groups-with-mutation-path-permission-v2",
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
            "requirement_reference": "legacy-admission-and-replay-only-v3",
            "requirement_excerpt_limit": 600,
            "behavior_cases": "legacy-admission-and-replay-only-v2",
            "behavior_case_text_limits": [5, 300],
            "mutation_evidence_binding": "observed-current-source-union-v2",
            "mutation_source_rebinding": "exact-position-unchanged-complete-line-fragments-v1",
            "inspection_gain": "non-overlapping-public-coverage-v2",
            "inspection_intent_projection": "single-native-intent-with-observation-refs-v1",
            "observation_to_action_guidance": "answer-implication-next-action-advisory-v1",
            "source_search": "rooted-component-glob-double-star-zero-depth-v1",
            "search_feedback": "eligible-decoded-file-count-v1",
            "mutation_failure": "typed-scope-preview-explicit-path-allowance-v3",
            "completion_horizon": "pre-dispatch-best-path-v2",
            "optional_mutation_admission": "minimum-attempt-initial-rejection-protection-v2",
            "mutation_anchor_guidance": "smallest-sufficient-exact-observed-text-v1",
            "public_check_failure_focus": "public-location-with-unknown-execution-boundary-v2",
            "public_failure_guidance": "diff-currency-and-actual-action-space-v1",
            "completion_guidance": "current-diff-tool-prerequisites-v6",
            "public_failure_recurrence": "semantic-site-with-raw-fallback-v1",
            "causal_revision_guidance": "advisory-hypothesis-review-v2",
            "failed_check_repair_action_space": "budget-only-public-inspection-v2",
            "evidence_plateau_transition": "advisory-only-v2",
            "check_recovery_reserve": "order-independent-distinct-failure-bound-v2",
            "context_projection": "observed-priority-merged-24000-chars-v1",
            "observed_source_index": "delivered-lexical-headers-16-entries-4000-chars-v1",
            "tool_closure_warning": "actual-single-inspection-successor-conditional-v1",
            "working_notes": "stable-note-id-independent-body-durable-lifecycle-v3",
            "source_note_normalization": "shared-observation-lf-not-mutation-format-v1",
            "working_note_feedback": "action-bound-expiry-independent-of-annotation-v3",
            "working_note_receipt_projection": "exact-prior-native-receipt-reference-v1",
            "working_note_range_feedback": "bounded-never-observed-versus-stale-current-range-v1",
            "working_note_interpretation": "evidence-currency-not-semantic-validation-v1",
            "working_note_check_result": "durable-verdict-exception-with-projected-currency-v1",
            "working_note_guidance": "compact-reusable-facts-and-lifecycle-guidance-v2",
            "verification_concerns": "original-question-progress-note-exact-noop-v2",
            "check_evidence_identity": "retained-action-check-diff-explicit-completion-currency-v2",
            "check_definition_review": "registered-literal-targets-current-source-navigation-v1",
            "check_definition_review_bounds": [
                check_review.MAX_TARGETS, check_review.MAX_RANGES,
                check_review.MAX_TARGET_CHARS, check_review.MAX_REVIEW_CHARS,
            ],
            "behavior_verification": "current-diff-intent-and-public-results-v3",
            "verification_concern_limit": 3,
            "submission_guidance": "current-check-finish-versus-unsuccessful-voluntary-stop-v2",
            "working_note_source_body_chars": 24_000,
            "public_probe": "optional-clean-python-diagnostic-protected-budget-v1",
            "public_probe_dependencies": "opt-in-public-locked-wheels-offline-snapshot-v1",
            "public_probe_discovery": "explicit-source-root-and-stdlib-reduction-limits-v2",
            "public_probe_process_guidance": "same-process-threads-no-child-process-v1",
            "public_probe_import_guidance": "failed-stderr-import-report-model-view-v1",
            "public_probe_observation": "execution-not-behavior-model-view-v1",
            "public_probe_observation_bounds": [4, 3],
            "public_probe_design_guidance": "public-input-variation-expected-observation-v1",
            "public_probe_usage_guidance": "injected-helper-direct-call-progressive-output-v1",
            "mutation_recovery": "atomic-complete-candidate-diff-v2",
            "correction_recovery": "journal-derived-unconsumed-v2",
            "execution_deadline": "shared-active-deadline-owned-cleanup-v1",
            "provider_tool_validation": "schema-exact-null-bounded-diagnostic-v1",
        }
    )
    if planning_policy != "none":
        from patchloop.dev.working_plan import contract

        base = sha256_json({"base_tool_surface_hash": base, "planning": contract(planning_policy)})
    if probe_policy == "none":
        return base
    if probe_policy != probe_cases.POLICY:
        raise ValueError("unknown probe policy")
    return sha256_json({"base_tool_surface_hash": base, "probe_cases": probe_cases.contract()})


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
    # Retained for old action/intent hashes and journal recovery. These annotations
    # are not advertised by the current provider schema; legacy parsing is nonblocking.
    requirement_ref: Any = None
    behavior_cases: Any = None

    @model_serializer(mode="wrap")
    def preserve_optional_reference_wire(self, handler: Any) -> dict[str, Any]:
        result = handler(self)
        for field in ("requirement_ref", "behavior_cases"):
            if field not in self.model_fields_set:
                result.pop(field, None)
        return result

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


class PublicTurnDecision(StrictModel):
    """One bounded public action decision for one requested tool call."""

    mode: Literal["inspect", "mutate", "verify", "finish", "stop"]
    basis: str = Field(min_length=1, max_length=800)
    evidence_goal: str | None = Field(default=None, min_length=1, max_length=500)
    # Notes are parsed independently: an invalid annotation must not reject an action.
    memory_update: Any = None
    # Independent annotation parsing must not turn a bad plan into a tool failure.
    plan_update: Any = None

    @model_serializer(mode="wrap")
    def preserve_optional_plan_wire(self, handler: Any) -> dict[str, Any]:
        result = handler(self)
        if "plan_update" not in self.model_fields_set:
            result.pop("plan_update", None)
        return result

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
    usage_evidence: dict[str, Any] | None = None
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
    # Snapshot at action completion, not the current workspace at later replay.
    # Successful mutation output.baseline_diff_hash separately names its pre-state.
    workspace_diff_hash: str | None = None


class DevRunRequest(StrictModel):
    provider: Literal["mock", "openai"]
    task: Path
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] = "medium"
    max_output_tokens: int = Field(
        default=cost.DEFAULT_OUTPUT_CEILING,
        ge=cost.MINIMUM_OUTPUT_CEILING, le=cost.MAX_OUTPUT_CEILING, strict=True,
        exclude_if=lambda value: value == cost.DEFAULT_OUTPUT_CEILING,
    )
    env_file: Path | None = None
    max_cost_usd: Decimal | None = None
    repeat: int = Field(default=1, ge=1, le=6)
    resume_run_id: str | None = Field(
        default=None,
        pattern=r"^run_dev_[a-zA-Z0-9_-]+$",
    )
    state_root: Path | None = None
    prepared_source: Path | None = None
    prepared_probe_dependencies: Path | None = None
    enable_probes: bool = False
    probe_policy: Literal["none", "cases-v1"] = "none"
    repair_recheck: bool = False
    repair_inspection_policy: Literal["protected-v1", "current-failure-v1"] = "protected-v1"
    planning_policy: Literal[
        "none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1",
        "brief-after-source-v1",
    ] = "none"
    context_policy: Literal["append-v1", "native-window-v1", "segmented-v1"] = "append-v1"
    segment_boundary_policy: segments.BoundaryPolicy = segments.DEFAULT_BOUNDARY_POLICY
    completion_cost_policy: cost.CompletionCostPolicy = cost.DEFAULT_COMPLETION_COST_POLICY
    compact_at_input_tokens: int | None = Field(default=None, gt=0, lt=272_000)
    accept_compaction_model_limit_reservation: bool = False
    limits: DevLimits = Field(default_factory=DevLimits)

    @model_validator(mode="after")
    def provider_options_match(self) -> DevRunRequest:
        if (self.completion_cost_policy != cost.DEFAULT_COMPLETION_COST_POLICY
                and self.context_policy != segments.POLICY):
            raise ValueError("--completion-cost-policy completion-reserve-v1 requires segmented-v1")
        if (self.segment_boundary_policy != segments.DEFAULT_BOUNDARY_POLICY
                and self.context_policy != segments.POLICY):
            raise ValueError("--segment-boundary-policy size-only-v1 requires segmented-v1")
        if self.prepared_probe_dependencies is not None and not self.enable_probes:
            raise ValueError("--prepared-probe-dependencies requires --enable-probes")
        if self.probe_policy != "none" and not self.enable_probes:
            raise ValueError("--probe-policy cases-v1 requires --enable-probes")
        if self.planning_policy != "none" and self.context_policy not in {
            "append-v1", "segmented-v1",
        }:
            raise ValueError(f"{self.planning_policy} planning requires append-v1 or segmented-v1")
        if self.provider == "openai":
            if self.env_file is None:
                raise ValueError("--provider openai requires --env-file")
            if self.max_cost_usd is None or self.max_cost_usd <= 0:
                raise ValueError("--provider openai requires a positive --max-cost-usd")
            if self.model == "gpt-5.4-2026-03-05" and (
                self.context_policy != segments.POLICY or segments.MAX_INPUT_TOKENS >= 272_000
            ):
                raise ValueError(
                    "reviewed GPT-5.4 pricing requires segmented-v1 with counted input below 272K"
                )
        elif self.env_file is not None or self.max_cost_usd is not None:
            raise ValueError("--provider mock forbids --env-file and --max-cost-usd")
        if self.resume_run_id is not None and self.repeat != 1:
            raise ValueError("--resume-run-id requires --repeat 1")
        if self.compact_at_input_tokens is not None:
            if (self.context_policy != "native-window-v1" or self.provider != "openai"
                    or self.model != "gpt-5.4-mini-2026-03-17"
                    or not self.accept_compaction_model_limit_reservation):
                raise ValueError("compaction requires native-window-v1, OpenAI mini snapshot, "
                                 "and explicit conditional model-limit reservation acknowledgement")
        elif self.accept_compaction_model_limit_reservation:
            raise ValueError("compaction acknowledgement requires --compact-at-input-tokens")
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
    prepared_source_path: str | None = None
    prepared_source_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    prepared_probe_dependencies_path: str | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    probe_dependencies: ProbeDependencyIdentity | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    public_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    private_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    runtime_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sandbox_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repair_recheck: bool = False
    repair_inspection_policy: Literal["protected-v1", "current-failure-v1"] = Field(
        default="protected-v1", exclude_if=lambda value: value == "protected-v1",
    )
    planning_policy: Literal[
        "none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1",
        "brief-after-source-v1",
    ] = "none"
    context_policy: Literal["append-v1", "native-window-v1", "segmented-v1"] = "append-v1"
    segment_boundary_policy: segments.BoundaryPolicy = Field(
        default=segments.DEFAULT_BOUNDARY_POLICY,
        exclude_if=lambda value: value == segments.DEFAULT_BOUNDARY_POLICY,
    )
    segment_contract: dict[str, Any] | None = None
    completion_cost_policy: cost.CompletionCostPolicy = Field(
        default=cost.DEFAULT_COMPLETION_COST_POLICY,
        exclude_if=lambda value: value == cost.DEFAULT_COMPLETION_COST_POLICY,
    )
    completion_cost_contract: dict[str, Any] | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    probe_policy: Literal["none", "cases-v1"] = "none"
    compaction_contract: dict[str, Any] | None = None
    probe_image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    probe_profile_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    model: str
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"]
    max_output_tokens: int = Field(
        default=cost.DEFAULT_OUTPUT_CEILING,
        ge=cost.MINIMUM_OUTPUT_CEILING, le=cost.MAX_OUTPUT_CEILING, strict=True,
        exclude_if=lambda value: value == cost.DEFAULT_OUTPUT_CEILING,
    )
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
        if self.completion_cost_policy == cost.COMPLETION_RESERVE_POLICY:
            if (self.context_policy != segments.POLICY
                    or self.completion_cost_contract != cost.completion_cost_contract()):
                raise ValueError("completion reserve requires segmented-v1 and its exact contract")
        elif self.completion_cost_contract is not None:
            raise ValueError("per-call cost policy has no completion reserve contract")
        if (self.segment_boundary_policy != segments.DEFAULT_BOUNDARY_POLICY
                and self.context_policy != segments.POLICY):
            raise ValueError("size-only-v1 boundary requires segmented-v1")
        if self.probe_policy != "none" and self.probe_image_digest is None:
            raise ValueError("probe cases require enabled probe identities")
        if self.planning_policy != "none" and self.context_policy not in {
            "append-v1", "segmented-v1",
        }:
            raise ValueError(f"{self.planning_policy} planning requires append-v1 or segmented-v1")
        if (self.context_policy == segments.POLICY) != (self.segment_contract is not None):
            raise ValueError("segmented context requires its exact contract")
        if (self.segment_contract is not None and self.segment_contract.get("boundary")
                != segments.contract(self.segment_boundary_policy)["boundary"]):
            raise ValueError("segment boundary policy and contract differ")
        if self.context_policy == segments.POLICY and self.compaction_contract is not None:
            raise ValueError("segmented context forbids compaction")
        if (self.probe_image_digest is None) != (self.probe_profile_hash is None):
            raise ValueError("probe image and profile identities must be paired")
        if self.prepared_probe_dependencies_path is not None and self.probe_profile_hash is None:
            raise ValueError("prepared dependencies require enabled probes")
        if self.probe_dependencies is not None and self.prepared_probe_dependencies_path is None:
            raise ValueError("prepared dependency identity requires its source descriptor")
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
