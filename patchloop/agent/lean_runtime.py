"""Versioned Lean Harness request assembly and offline manifest factory.

This module preserves the consumed ``v7`` / ``phase-evidence-v12`` seam and
adds opt-in ``v8`` / ``phase-evidence-v13`` and ``v9`` /
``phase-evidence-v14`` successors.
It composes the already-qualified context compaction, phase evidence,
saturation recovery, finalization reserve, and split-token allowance into the
exact request that may be persisted by :class:`AgentRunner`.  It does not
provide provider authority and it cannot be reached by legacy runtime pairs.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.completion_loop_successor import (
    COMPLETION_LOOP_POLICY,
    CORRECTION_CONTEXT_POLICY,
    PROVIDER_TERMINAL_ATTRIBUTION_POLICY,
    CompletionLoopDecision,
    CompletionToolSurface,
    CurrentEditCorrectionContextEvidence,
    completion_instruction,
    project_completion_loop_successor,
    project_completion_tool_surface,
    project_current_edit_correction_context,
)
from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_compaction import (
    LeanContextEventCompactionEvidence,
    LeanContextEventCompactionEvidenceV2,
    project_lean_context_event_descriptors,
    project_lean_context_event_descriptors_v2,
)
from patchloop.agent.finalization import (
    FinalizationRequestMode,
    FinalizationReserveContract,
    PhaseToolSurfaceProjection,
    load_r8_public_development_finalization_reserve,
    project_finalization_request_mode,
    project_phase_tool_surface,
)
from patchloop.agent.lean_runtime_preregistration import (
    LeanRuntimeContract,
    LeanRuntimeIntegrationPreregistration,
    load_lean_runtime_integration_preregistration,
)
from patchloop.agent.mechanical_friction import (
    COMPLETION_RESPONSE_RECOVERY_POLICY,
    INCOMPLETE_RECOVERY_POLICY,
    CompletionResponseRecovery,
    ReasoningIncompleteRecovery,
    project_completion_response_recovery,
    project_reasoning_incomplete_recovery,
)
from patchloop.agent.phases import EvidenceState
from patchloop.agent.provider_schema_admission import validate_provider_tool_schemas
from patchloop.agent.request_allowance import (
    SplitAwareRequestAllowance,
    project_split_aware_request_allowance,
)
from patchloop.agent.saturation_recovery_qualification import (
    QUALIFICATION_PATH as SATURATION_QUALIFICATION_PATH,
)
from patchloop.agent.saturation_recovery_qualification import (
    SaturationRecoveryPublicQualification,
)
from patchloop.agent.saturation_recovery_qualification import (
    qualification_bytes as saturation_qualification_bytes,
)
from patchloop.agent.saturation_recovery_shadow import (
    SaturationRecoveryAdmissionShadow,
    SaturationRecoveryAdmissionShadowV2,
    SaturationRecoveryAdmissionShadowV3,
    project_saturation_recovery_admission_shadow,
)
from patchloop.agent.structured_edit import (
    STRUCTURED_EDIT_TOOL_NAME,
    STRUCTURED_EDIT_TOOL_SCHEMA_V1,
    STRUCTURED_EDIT_TOOL_SCHEMA_V2,
)
from patchloop.agent.workflow_bounded_request_context_successor import (
    BOUNDED_REQUEST_CONTEXT_POLICY,
    EXACT_PRE_PLAN_SURFACE_POLICY,
    BoundedInvestigationRequestContext,
    BoundedInvestigationRequestContextEvidence,
    ExactPrePlanSurfaceProjection,
    ExactPrePlanSurfaceProjectionEvidence,
    bind_bounded_request_instruction,
    project_bounded_investigation_request_context,
    project_exact_pre_plan_surface,
)
from patchloop.agent.workflow_candidate_binding_successor import (
    CANDIDATE_BINDING_POLICY_V16,
)
from patchloop.agent.workflow_causal_alternative_activation import (
    CAUSAL_ACTIVATION_POLICY,
    CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA,
    CrossResetFailureTrigger,
    cross_reset_epoch_events,
    project_active_cross_reset_trigger,
    project_causal_mechanism_history,
    project_causal_reset_decision,
    project_causal_workflow_tool_surface,
    project_cross_reset_semantic_progress_state,
    workflow_instruction_v4,
)
from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
    CausalMechanismHistoryEntry,
    MutationBaselineProjection,
    MutationBaselineRestoreReceipt,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY,
    CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA_V5,
    ActivatedCausalPlanRequest,
    CausalMechanismHistoryEntryV2,
    project_causal_mechanism_history_v2,
    project_causal_plan_workflow_tool_surface_v2,
    project_causal_reset_decision_v2,
    workflow_instruction_v5,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    CAUSAL_PLAN_PROJECTION_POLICY,
)
from patchloop.agent.workflow_exploration_gate_activation import (
    EXPLORATION_GATE_ACTIVATION_POLICY,
    EXPLORATION_WORKFLOW_INSTRUCTION_SCHEMA,
    ActivatedExplorationPlanRequest,
    project_exploration_readiness_decision,
    project_exploration_workflow_tool_surface,
    workflow_instruction_v6,
)
from patchloop.agent.workflow_exploration_gate_successor import EXPLORATION_GATE_POLICY
from patchloop.agent.workflow_lifecycle_binding_successor import (
    LIFECYCLE_COMPONENT_BINDING_POLICY,
    PLAN_ADMISSION_FEEDBACK_POLICY_V3,
    LifecycleComponentBoundPlanRequest,
    LifecyclePlanFeedbackEvidenceV3,
    lifecycle_component_workflow_instruction,
    project_lifecycle_component_bound_tool_surface,
    project_lifecycle_plan_admission_feedback_v3,
)
from patchloop.agent.workflow_plan_admission_feedback_successor import (
    PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY,
    PROJECTED_FEEDBACK_SCHEMA,
    BoundedWorkPlanAdmissionFeedback,
    CompatibleBoundedWorkPlanAdmissionFeedback,
    PlanAdmissionFeedbackProjectionEvidence,
    project_bounded_plan_admission_feedback,
    project_compatible_bounded_plan_admission_feedback,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY,
    TriggerBoundSelfDirectedPlanRequest,
    project_trigger_bound_self_directed_tool_surface,
    project_trigger_bound_self_directed_workflow_decision,
)
from patchloop.agent.workflow_plan_gate_liveness_successor import (
    PLAN_GATE_LIVENESS_POLICY,
    EligiblePlanEvidenceCatalogV3,
    PinnedExplorationPlanRequest,
    PlanGateReadinessSnapshot,
    RecoveredPlanGateReadinessPin,
    bind_recovered_plan_gate_pin,
    project_pinned_evidence_catalog,
    project_pinned_plan_gate_decision,
    project_pinned_plan_gate_tool_surface,
    project_plan_gate_readiness_snapshot,
    workflow_instruction_v7,
)
from patchloop.agent.workflow_r21_reliability_successor import (
    ANCHORED_READ_POLICY,
    GENERATION_INCOMPLETE_RECOVERY_POLICY,
    LIFECYCLE_PLAN_POLICY,
    PLAN_ADMISSION_FEEDBACK_POLICY_V2,
    CompactPlanFeedbackEvidence,
    GenerationIncompleteRecoveryState,
    LifecycleBoundPlanRequest,
    lifecycle_workflow_instruction,
    project_compact_plan_admission_feedback_v2,
    project_generation_incomplete_recovery,
    project_lifecycle_bound_tool_surface,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SELF_DIRECTED_EXPLORATION_POLICY,
    EligiblePlanEvidenceCatalogV4,
    RecoveredSelfDirectedPlanGatePin,
    SelfDirectedExplorationState,
    SelfDirectedPlanGateSnapshot,
    SelfDirectedPlanRequest,
    WorkflowDecisionV4,
    bind_recovered_self_directed_pin,
    project_self_directed_evidence_catalog,
    project_self_directed_exploration_state,
    project_self_directed_plan_gate_snapshot,
    project_self_directed_tool_surface,
    project_self_directed_workflow_decision,
    workflow_instruction_v8,
)
from patchloop.agent.workflow_semantic_progress_epoch_parity import (
    SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY,
    SemanticProgressEventDomain,
    project_semantic_progress_event_domain,
    select_semantic_progress_epoch_events,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    WORKFLOW_INSTRUCTION_SCHEMA_V3,
    WORKFLOW_POLICY_V15,
    PublicSemanticProgressState,
    WorkflowDecisionV3,
    current_public_failure_event_sequence,
    project_public_semantic_progress_state,
    project_workflow_semantic_progress_successor,
    project_workflow_tool_surface_v3,
    workflow_instruction_v3,
)
from patchloop.agent.workflow_successor import (
    WORKFLOW_POLICY_V9,
    WORKFLOW_POLICY_V10,
    PublicTaskSpec,
    WorkflowDecision,
    WorkflowToolSurface,
    project_public_task_spec,
    project_workflow_successor,
    project_workflow_tool_surface,
    workflow_instruction,
)
from patchloop.agent.workflow_successor_v2 import (
    WORKFLOW_POLICY_V11,
    WORKFLOW_POLICY_V12,
    WORKFLOW_POLICY_V14,
    ActiveWorkState,
    EligiblePlanEvidenceCatalog,
    EligiblePlanEvidenceCatalogV2,
    RecordedWorkPlanV2,
    WorkflowDecisionV2,
    WorkflowToolSurfaceV2,
    project_active_work_state,
    project_eligible_plan_evidence_catalog,
    project_eligible_plan_evidence_catalog_v2,
    project_workflow_successor_v2,
    project_workflow_tool_surface_v2,
    required_failed_check_trigger_sequence,
    workflow_instruction_v2,
)
from patchloop.contracts import (
    Budget,
    EventType,
    MemoryCondition,
    PublicTask,
    RunEvent,
    RunManifest,
    TaskPackage,
    Usage,
)
from patchloop.errors import (
    ContractError,
    CorrectionAttemptLimitError,
    PreMutationEvidenceExhaustedError,
    RecoveryError,
    RequiredWorkflowEvidenceUnavailableError,
    SelfDirectedExplorationExhaustedError,
    SemanticNoProgressEvidenceExhaustedError,
    SemanticNoProgressRevisionInvalidError,
    SemanticProgressEvidenceUnavailableError,
    WorkPlanAdmissionRepeatedError,
)
from patchloop.memory.fixed_bundle import (
    D110_INDEX_CONTENT_HASH,
    D110_INDEX_VERSION,
    FIXED_BUNDLE_POLICY_VERSION,
)
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json, sha256_text

LEAN_RUNTIME_POLICY_VERSION = "lean-harness-v1"
LEAN_TOOL_SCHEMA_VERSION = "v7"
LEAN_CONTEXT_POLICY_VERSION = "phase-evidence-v12"
LEAN_REQUEST_EVIDENCE_SCHEMA = "lean-harness-request-evidence-v1"
LEAN_RUNTIME_POLICY_VERSION_V2 = "lean-harness-v2"
LEAN_TOOL_SCHEMA_VERSION_V2 = "v8"
LEAN_CONTEXT_POLICY_VERSION_V2 = "phase-evidence-v13"
LEAN_REQUEST_EVIDENCE_SCHEMA_V2 = "lean-harness-request-evidence-v2"
LEAN_COMPLETION_POLICY_VERSION_V2 = "completion-driven-current-diff-v1"
LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2 = "safe-raw-diff-normalization-v1"
LEAN_RUNTIME_POLICY_VERSION_V3 = "lean-harness-v3"
LEAN_TOOL_SCHEMA_VERSION_V3 = "v9"
LEAN_CONTEXT_POLICY_VERSION_V3 = "phase-evidence-v13"
LEAN_REQUEST_EVIDENCE_SCHEMA_V3 = "lean-harness-request-evidence-v3"
LEAN_SEARCH_GLOB_POLICY_VERSION_V3 = "recursive-file-glob-normalization-v1"
LEAN_RUNTIME_POLICY_VERSION_V4 = "lean-harness-v4"
LEAN_TOOL_SCHEMA_VERSION_V4 = "v9"
LEAN_CONTEXT_POLICY_VERSION_V4 = "phase-evidence-v14"
LEAN_REQUEST_EVIDENCE_SCHEMA_V4 = "lean-harness-request-evidence-v4"
LEAN_COMPLETION_POLICY_VERSION_V4 = "completion-driven-current-diff-v2"
LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4 = "configured-ceiling-split-bounded-v1"
LEAN_RUNTIME_POLICY_VERSION_V5 = "lean-harness-v5"
LEAN_TOOL_SCHEMA_VERSION_V5 = "v10"
LEAN_CONTEXT_POLICY_VERSION_V5 = "phase-evidence-v15"
LEAN_REQUEST_EVIDENCE_SCHEMA_V5 = "lean-harness-request-evidence-v5"
LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5 = "gateway-fresh-preimage-unique-text-v1"
LEAN_CHECK_OUTCOME_POLICY_VERSION_V5 = "invocation-vs-behavior-v1"
LEAN_INCOMPLETE_RECOVERY_POLICY_VERSION_V5 = INCOMPLETE_RECOVERY_POLICY
LEAN_RUNTIME_POLICY_VERSION_V6 = "lean-harness-v6"
LEAN_TOOL_SCHEMA_VERSION_V6 = "v10"
LEAN_CONTEXT_POLICY_VERSION_V6 = "phase-evidence-v16"
LEAN_REQUEST_EVIDENCE_SCHEMA_V6 = "lean-harness-request-evidence-v6"
LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6 = "typed-distinct-input-role-v1"
LEAN_RUNTIME_POLICY_VERSION_V7 = "lean-harness-v7"
LEAN_TOOL_SCHEMA_VERSION_V7 = "v11"
LEAN_CONTEXT_POLICY_VERSION_V7 = "phase-evidence-v17"
LEAN_REQUEST_EVIDENCE_SCHEMA_V7 = "lean-harness-request-evidence-v7"
LEAN_COMPLETION_POLICY_VERSION_V7 = "state-driven-current-diff-v3"
LEAN_RESPONSE_RECOVERY_POLICY_VERSION_V7 = COMPLETION_RESPONSE_RECOVERY_POLICY
LEAN_EDIT_CORRECTION_POLICY_VERSION_V7 = "bounded-public-current-source-v1"
LEAN_RUNTIME_POLICY_VERSION_V8 = "lean-harness-v8"
LEAN_TOOL_SCHEMA_VERSION_V8 = "v12"
LEAN_CONTEXT_POLICY_VERSION_V8 = "phase-evidence-v18"
LEAN_REQUEST_EVIDENCE_SCHEMA_V8 = "lean-harness-request-evidence-v8"
LEAN_COMPLETION_POLICY_VERSION_V8 = COMPLETION_LOOP_POLICY
LEAN_CORRECTION_CONTEXT_POLICY_VERSION_V8 = CORRECTION_CONTEXT_POLICY
LEAN_PROVIDER_TERMINAL_POLICY_VERSION_V8 = PROVIDER_TERMINAL_ATTRIBUTION_POLICY
LEAN_RUNTIME_POLICY_VERSION_V9 = "lean-harness-v9"
LEAN_TOOL_SCHEMA_VERSION_V9 = "v13"
LEAN_CONTEXT_POLICY_VERSION_V9 = "phase-evidence-v19"
LEAN_REQUEST_EVIDENCE_SCHEMA_V9 = "lean-harness-request-evidence-v9"
LEAN_WORKFLOW_POLICY_VERSION_V9 = WORKFLOW_POLICY_V9
LEAN_RUNTIME_POLICY_VERSION_V10 = "lean-harness-v10"
LEAN_TOOL_SCHEMA_VERSION_V10 = "v14"
LEAN_CONTEXT_POLICY_VERSION_V10 = "phase-evidence-v20"
LEAN_REQUEST_EVIDENCE_SCHEMA_V10 = "lean-harness-request-evidence-v10"
LEAN_WORKFLOW_POLICY_VERSION_V10 = WORKFLOW_POLICY_V10
LEAN_RUNTIME_POLICY_VERSION_V11 = "lean-harness-v11"
LEAN_TOOL_SCHEMA_VERSION_V11 = "v15"
LEAN_CONTEXT_POLICY_VERSION_V11 = "phase-evidence-v21"
LEAN_REQUEST_EVIDENCE_SCHEMA_V11 = "lean-harness-request-evidence-v11"
LEAN_WORKFLOW_POLICY_VERSION_V11 = WORKFLOW_POLICY_V11
LEAN_RUNTIME_POLICY_VERSION_V12 = "lean-harness-v12"
LEAN_TOOL_SCHEMA_VERSION_V12 = "v16"
LEAN_CONTEXT_POLICY_VERSION_V12 = "phase-evidence-v22"
LEAN_REQUEST_EVIDENCE_SCHEMA_V12 = "lean-harness-request-evidence-v12"
LEAN_WORKFLOW_POLICY_VERSION_V12 = WORKFLOW_POLICY_V12
LEAN_RUNTIME_POLICY_VERSION_V13 = "lean-harness-v13"
LEAN_TOOL_SCHEMA_VERSION_V13 = "v17"
LEAN_CONTEXT_POLICY_VERSION_V13 = "phase-evidence-v23"
LEAN_REQUEST_EVIDENCE_SCHEMA_V13 = "lean-harness-request-evidence-v13"
LEAN_WORKFLOW_POLICY_VERSION_V13 = WORKFLOW_POLICY_V12
LEAN_FINALIZATION_WORKFLOW_SURFACE_POLICY_VERSION_V13 = (
    "workflow-surface-retained-through-reserve-v1"
)
LEAN_RUNTIME_POLICY_VERSION_V14 = "lean-harness-v14"
LEAN_TOOL_SCHEMA_VERSION_V14 = "v18"
LEAN_CONTEXT_POLICY_VERSION_V14 = "phase-evidence-v24"
LEAN_REQUEST_EVIDENCE_SCHEMA_V14 = "lean-harness-request-evidence-v14"
LEAN_WORKFLOW_POLICY_VERSION_V14 = WORKFLOW_POLICY_V14
LEAN_REQUIRED_TRIGGER_PIN_POLICY_VERSION_V14 = "required-failed-check-trigger-pinned-v1"
LEAN_RUNTIME_POLICY_VERSION_V15 = "lean-harness-v15"
LEAN_TOOL_SCHEMA_VERSION_V15 = "v19"
LEAN_CONTEXT_POLICY_VERSION_V15 = "phase-evidence-v25"
LEAN_REQUEST_EVIDENCE_SCHEMA_V15 = "lean-harness-request-evidence-v15"
LEAN_WORKFLOW_POLICY_VERSION_V15 = WORKFLOW_POLICY_V15
LEAN_SEMANTIC_PROGRESS_POLICY_VERSION_V15 = WORKFLOW_POLICY_V15
LEAN_RUNTIME_POLICY_VERSION_V16 = "lean-harness-v16"
LEAN_TOOL_SCHEMA_VERSION_V16 = "v20"
LEAN_CONTEXT_POLICY_VERSION_V16 = "phase-evidence-v26"
LEAN_REQUEST_EVIDENCE_SCHEMA_V16 = "lean-harness-request-evidence-v16"
LEAN_CANDIDATE_BINDING_POLICY_VERSION_V16 = CANDIDATE_BINDING_POLICY_V16
LEAN_RUNTIME_POLICY_VERSION_V17 = "lean-harness-v17"
LEAN_TOOL_SCHEMA_VERSION_V17 = "v21"
LEAN_CONTEXT_POLICY_VERSION_V17 = "phase-evidence-v27"
LEAN_REQUEST_EVIDENCE_SCHEMA_V17 = "lean-harness-request-evidence-v17"
LEAN_CAUSAL_ACTIVATION_POLICY_VERSION_V17 = CAUSAL_ACTIVATION_POLICY
LEAN_RUNTIME_POLICY_VERSION_V18 = "lean-harness-v18"
LEAN_TOOL_SCHEMA_VERSION_V18 = "v22"
LEAN_CONTEXT_POLICY_VERSION_V18 = "phase-evidence-v28"
LEAN_REQUEST_EVIDENCE_SCHEMA_V18 = "lean-harness-request-evidence-v18"
LEAN_CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY_VERSION_V18 = CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY
LEAN_RUNTIME_POLICY_VERSION_V19 = "lean-harness-v19"
LEAN_TOOL_SCHEMA_VERSION_V19 = "v23"
LEAN_CONTEXT_POLICY_VERSION_V19 = "phase-evidence-v29"
LEAN_REQUEST_EVIDENCE_SCHEMA_V19 = "lean-harness-request-evidence-v19"
LEAN_EXPLORATION_GATE_ACTIVATION_POLICY_VERSION_V19 = EXPLORATION_GATE_ACTIVATION_POLICY
LEAN_RUNTIME_POLICY_VERSION_V20 = "lean-harness-v20"
LEAN_TOOL_SCHEMA_VERSION_V20 = "v24"
LEAN_CONTEXT_POLICY_VERSION_V20 = "phase-evidence-v30"
LEAN_REQUEST_EVIDENCE_SCHEMA_V20 = "lean-harness-request-evidence-v20"
LEAN_SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY_VERSION_V20 = SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY
LEAN_RUNTIME_POLICY_VERSION_V21 = "lean-harness-v21"
LEAN_TOOL_SCHEMA_VERSION_V21 = "v25"
LEAN_CONTEXT_POLICY_VERSION_V21 = "phase-evidence-v31"
LEAN_REQUEST_EVIDENCE_SCHEMA_V21 = "lean-harness-request-evidence-v21"
LEAN_PLAN_GATE_LIVENESS_POLICY_VERSION_V21 = PLAN_GATE_LIVENESS_POLICY
LEAN_RUNTIME_POLICY_VERSION_V22 = "lean-harness-v22"
LEAN_TOOL_SCHEMA_VERSION_V22 = "v25"
LEAN_CONTEXT_POLICY_VERSION_V22 = "phase-evidence-v32"
LEAN_REQUEST_EVIDENCE_SCHEMA_V22 = "lean-harness-request-evidence-v22"
LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22 = PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY
LEAN_RUNTIME_POLICY_VERSION_V23 = "lean-harness-v23"
LEAN_TOOL_SCHEMA_VERSION_V23 = "v26"
LEAN_CONTEXT_POLICY_VERSION_V23 = "phase-evidence-v33"
LEAN_REQUEST_EVIDENCE_SCHEMA_V23 = "lean-harness-request-evidence-v23"
LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23 = SELF_DIRECTED_EXPLORATION_POLICY
LEAN_RUNTIME_POLICY_VERSION_V24 = "lean-harness-v24"
LEAN_TOOL_SCHEMA_VERSION_V24 = "v26"
LEAN_CONTEXT_POLICY_VERSION_V24 = "phase-evidence-v34"
LEAN_REQUEST_EVIDENCE_SCHEMA_V24 = "lean-harness-request-evidence-v24"
LEAN_EXACT_PRE_PLAN_SURFACE_POLICY_VERSION_V24 = EXACT_PRE_PLAN_SURFACE_POLICY
LEAN_BOUNDED_REQUEST_CONTEXT_POLICY_VERSION_V24 = BOUNDED_REQUEST_CONTEXT_POLICY
LEAN_RUNTIME_POLICY_VERSION_V25 = "lean-harness-v25"
LEAN_TOOL_SCHEMA_VERSION_V25 = "v26"
LEAN_CONTEXT_POLICY_VERSION_V25 = "phase-evidence-v35"
LEAN_REQUEST_EVIDENCE_SCHEMA_V25 = "lean-harness-request-evidence-v25"
LEAN_PLAN_CONTRACT_COMPATIBILITY_POLICY_VERSION_V25 = TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY
LEAN_RUNTIME_POLICY_VERSION_V26 = "lean-harness-v26"
LEAN_TOOL_SCHEMA_VERSION_V26 = "v27"
LEAN_CONTEXT_POLICY_VERSION_V26 = "phase-evidence-v36"
LEAN_REQUEST_EVIDENCE_SCHEMA_V26 = "lean-harness-request-evidence-v26"
LEAN_GENERATION_INCOMPLETE_RECOVERY_POLICY_VERSION_V26 = GENERATION_INCOMPLETE_RECOVERY_POLICY
LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V26 = PLAN_ADMISSION_FEEDBACK_POLICY_V2
LEAN_ANCHORED_READ_POLICY_VERSION_V26 = ANCHORED_READ_POLICY
LEAN_LIFECYCLE_PLAN_POLICY_VERSION_V26 = LIFECYCLE_PLAN_POLICY

LEAN_RUNTIME_POLICY_VERSION_V27 = "lean-harness-v27"
LEAN_TOOL_SCHEMA_VERSION_V27 = "v28"
LEAN_CONTEXT_POLICY_VERSION_V27 = "phase-evidence-v37"
LEAN_REQUEST_EVIDENCE_SCHEMA_V27 = "lean-harness-request-evidence-v27"
LEAN_RUNTIME_POLICY_VERSION_V28 = "lean-harness-v28"
LEAN_TOOL_SCHEMA_VERSION_V28 = "v29"
LEAN_CONTEXT_POLICY_VERSION_V28 = "phase-evidence-v38"
LEAN_REQUEST_EVIDENCE_SCHEMA_V28 = "lean-harness-request-evidence-v28"
LEAN_LIFECYCLE_PLAN_POLICY_VERSION_V28 = LIFECYCLE_COMPONENT_BINDING_POLICY
LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V28 = PLAN_ADMISSION_FEEDBACK_POLICY_V3
LEAN_PHASE_TOOL_SURFACE_SCHEMA = "lean-harness-phase-tool-surface-v1"
LEAN_PHASE_TOOL_SURFACE_SCHEMA_V2 = "lean-harness-phase-tool-surface-v2"
LEAN_PHASE_TOOL_SURFACE_SCHEMA_V3 = "lean-harness-phase-tool-surface-v3"
LEAN_PHASE_TOOL_SURFACE_SCHEMA_V4 = "lean-harness-phase-tool-surface-v4"
LEAN_MOCK_MODEL_ID = "patchloop-public-calibration-mock-v1"
LEAN_MOCK_COUNT_METHOD = "canonical-json-utf8-bytes-v1"
LEAN_LIVE_COUNT_METHOD = "openai-input-token-count-v1"
LEAN_LIVE_COUNT_METHOD_V2 = "openai-input-token-count-v2-parallel-bound"
_SATURATION_QUALIFICATION_FILE_BYTES = 10_993
_SATURATION_QUALIFICATION_FILE_SHA256 = (
    "sha256:99b30c828989b1a2cae28bd1412d27a9d4e9514768b22cea8047780792f13d0e"
)
_SATURATION_QUALIFICATION_CONTENT_HASH = (
    "sha256:f07374bca99d1046c66f7ade6d96caf2bd06cbafe307dcabcad681f473485db6"
)

_FINALIZATION_CAPABILITIES = {
    "read_file": "read_file",
    "apply_patch": "apply_patch",
    STRUCTURED_EDIT_TOOL_NAME: "apply_patch",
    "run_check": "run_check",
    "get_diff": "get_diff",
    "finish_task": "finish_task",
}


def _tool_names(schemas: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    names: list[str] = []
    for schema in schemas:
        if type(schema) is not dict or schema.get("type") != "function":
            raise ContractError("Lean Harness tool schema must be an exact function mapping")
        name = schema.get("name")
        if type(name) is not str or not name:
            raise ContractError("Lean Harness tool schema name is invalid")
        names.append(name)
    if len(names) != len(set(names)):
        raise ContractError("Lean Harness tool schema names repeat")
    return tuple(names)


class LeanPhaseToolSurface(BaseModel):
    """Final phase/recovery/reserve-filtered tool surface for one request."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-phase-tool-surface-v1"]
    mode: Literal["exploration", "finalization"]
    source_phase_tool_surface: PhaseToolSurfaceProjection
    source_phase_tool_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    saturation_recovery_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    saturation_selected_tool_schemas: tuple[dict[str, Any], ...] = Field(min_length=1)
    saturation_selected_tool_names: tuple[str, ...] = Field(min_length=1)
    finalization_capability_projection: dict[str, str]
    selected_tool_schemas: tuple[dict[str, Any], ...] = Field(min_length=1)
    selected_tool_names: tuple[str, ...] = Field(min_length=1)
    removed_for_finalization: tuple[str, ...]
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    structured_edit_maps_to_mutation_capability: Literal[True]
    condition_neutral: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_surface(self) -> Self:
        if self.source_phase_tool_surface_hash != self.source_phase_tool_surface.content_hash:
            raise ValueError("Lean phase source surface hash differs")
        saturation_names = _tool_names(self.saturation_selected_tool_schemas)
        if self.saturation_selected_tool_names != saturation_names:
            raise ValueError("Lean saturation tool names differ")
        expected_projection = {
            name: _FINALIZATION_CAPABILITIES[name]
            for name in saturation_names
            if name in _FINALIZATION_CAPABILITIES
        }
        if self.finalization_capability_projection != expected_projection:
            raise ValueError("Lean finalization capability projection differs")
        if self.schema_version == LEAN_PHASE_TOOL_SURFACE_SCHEMA:
            allowed = (
                set(self.source_phase_tool_surface.finalization_tool_names)
                if self.mode == "finalization"
                else None
            )
        else:
            completion_target = getattr(self, "completion_target", None)
            completion_successor = self.schema_version in {
                LEAN_PHASE_TOOL_SURFACE_SCHEMA_V3,
                LEAN_PHASE_TOOL_SURFACE_SCHEMA_V4,
            }
            state_driven_after_mutation = self.schema_version == LEAN_PHASE_TOOL_SURFACE_SCHEMA_V4
            expected_target, allowed = _completion_surface_target(
                self.source_phase_tool_surface,
                self.mode,
                prefer_registered_check=completion_successor,
                state_driven_after_mutation=state_driven_after_mutation,
            )
            if completion_target != expected_target:
                raise ValueError("Lean completion target differs")
            if completion_successor:
                if getattr(self, "registered_check_preferred", None) is not True:
                    raise ValueError("Lean registered-check preference differs")
                recheck_required = getattr(self, "recheck_after_mutation_required", None)
                if recheck_required is not (expected_target in {"mutation", "corrective-mutation"}):
                    raise ValueError("Lean post-mutation recheck binding differs")
            if state_driven_after_mutation:
                expected_lane = bool(
                    self.mode == "finalization"
                    or self.source_phase_tool_surface.phase_evidence.get("mutation_present") is True
                )
                if getattr(self, "state_driven_after_mutation", None) is not True:
                    raise ValueError("Lean state-driven completion binding differs")
                if getattr(self, "completion_lane_active", None) is not expected_lane:
                    raise ValueError("Lean completion-lane activation differs")
        expected_schemas = tuple(
            schema
            for schema, name in zip(
                self.saturation_selected_tool_schemas,
                saturation_names,
                strict=True,
            )
            if allowed is None or expected_projection.get(name) in allowed
        )
        if not expected_schemas:
            raise ValueError("Lean final tool surface is empty")
        expected_names = _tool_names(expected_schemas)
        if self.selected_tool_schemas != expected_schemas:
            raise ValueError("Lean selected tool schemas differ")
        if self.selected_tool_names != expected_names:
            raise ValueError("Lean selected tool names differ")
        expected_removed = tuple(name for name in saturation_names if name not in expected_names)
        if self.removed_for_finalization != expected_removed:
            raise ValueError("Lean finalization removal inventory differs")
        if self.selected_tool_schema_hash != sha256_json(list(expected_schemas)):
            raise ValueError("Lean selected tool schema hash differs")
        if STRUCTURED_EDIT_TOOL_NAME in saturation_names and (
            expected_projection.get(STRUCTURED_EDIT_TOOL_NAME) != "apply_patch"
        ):
            raise ValueError("Lean structured edit lacks mutation capability")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("Lean phase tool surface content hash differs")
        return self


class LeanPhaseToolSurfaceV2(LeanPhaseToolSurface):
    """Completion-driven successor surface, including reserve finalization."""

    schema_version: Literal["lean-harness-phase-tool-surface-v2"]
    completion_target: Literal[
        "phase-policy",
        "mutation",
        "visible-check",
        "diff-review",
        "submission",
    ]


class LeanPhaseToolSurfaceV3(LeanPhaseToolSurfaceV2):
    """Completion successor that distinguishes correction from first mutation."""

    schema_version: Literal["lean-harness-phase-tool-surface-v3"]
    completion_target: Literal[
        "phase-policy",
        "mutation",
        "corrective-mutation",
        "visible-check",
        "diff-review",
        "submission",
    ]
    registered_check_preferred: Literal[True]
    recheck_after_mutation_required: bool


class LeanPhaseToolSurfaceV4(LeanPhaseToolSurfaceV3):
    """Successor that enters completion immediately after current-diff mutation."""

    schema_version: Literal["lean-harness-phase-tool-surface-v4"]
    state_driven_after_mutation: Literal[True]
    completion_lane_active: bool


class LeanHarnessRequestEvidence(BaseModel):
    """Persist-before-dispatch evidence for one exact Lean Harness request."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-request-evidence-v1"]
    runtime_policy_version: Literal["lean-harness-v1"]
    tool_schema_version: Literal["v7"]
    context_policy_version: Literal["phase-evidence-v12"]
    input_count_method: Literal[
        "canonical-json-utf8-bytes-v1",
        "openai-input-token-count-v1",
        "openai-input-token-count-v2-parallel-bound",
    ]
    pipeline_stages: tuple[str, ...]
    runtime_contract_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    context_build_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    context_compaction_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    phase_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    saturation_recovery_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    finalization_request_mode_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    phase_tool_surface_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_tool_schema_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requested_input_tokens: int = Field(ge=1)
    effective_max_output_tokens: int = Field(ge=1)
    split_allowance_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    memory_delivery_evidence_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_no_memory_request_body_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    context_build: dict[str, Any]
    context_compaction: LeanContextEventCompactionEvidence
    phase_evidence: dict[str, Any]
    saturation_recovery: SaturationRecoveryAdmissionShadow
    finalization_request_mode: FinalizationRequestMode
    phase_tool_surface: LeanPhaseToolSurface
    split_allowance: SplitAwareRequestAllowance
    request_body: dict[str, Any]
    request_evidence_persisted_before_dispatch: Literal[True]
    dispatch_requires_exact_persisted_request: Literal[True]
    legacy_runtime_fallback_allowed: Literal[False]
    provider_authority_granted: Literal[False]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if self.context_build_hash != sha256_json(self.context_build):
            raise ValueError("Lean context-build hash differs")
        if self.context_compaction_evidence_hash != self.context_compaction.content_hash:
            raise ValueError("Lean context-compaction hash differs")
        if self.phase_evidence_hash != sha256_json(self.phase_evidence):
            raise ValueError("Lean phase-evidence hash differs")
        if self.saturation_recovery_evidence_hash != self.saturation_recovery.content_hash:
            raise ValueError("Lean saturation evidence hash differs")
        if self.finalization_request_mode_hash != self.finalization_request_mode.content_hash:
            raise ValueError("Lean finalization-mode hash differs")
        if self.phase_tool_surface_hash != self.phase_tool_surface.content_hash:
            raise ValueError("Lean phase tool-surface hash differs")
        if self.selected_tool_schema_hash != self.phase_tool_surface.selected_tool_schema_hash:
            raise ValueError("Lean selected schema binding differs")
        if self.split_allowance_hash != sha256_json(self.split_allowance.model_dump(mode="json")):
            raise ValueError("Lean split allowance hash differs")
        expected_body_keys = (
            (
                "model",
                "system_prompt",
                "context",
                "tools",
                "max_output_tokens",
                *(
                    ("parallel_tool_calls",)
                    if self.schema_version
                    in {
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V8,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V9,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V10,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V11,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V12,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V13,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V14,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V15,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V16,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V17,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V18,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V19,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V20,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V27,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
                    }
                    else ()
                ),
            )
            if self.input_count_method == LEAN_MOCK_COUNT_METHOD
            else (
                "model",
                "input",
                "tools",
                "store",
                "reasoning",
                "service_tier",
                "max_output_tokens",
                "truncation",
                *(
                    ("parallel_tool_calls",)
                    if self.schema_version
                    in {
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V8,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V9,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V10,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V11,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V12,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V13,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V14,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V15,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V16,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V17,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V18,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V19,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V20,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V27,
                        LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
                    }
                    else ()
                ),
            )
        )
        if len(self.request_body) != len(expected_body_keys) or set(self.request_body) != set(
            expected_body_keys
        ):
            raise ValueError("Lean request body shape differs")
        if self.request_body.get("tools") != list(self.phase_tool_surface.selected_tool_schemas):
            raise ValueError("Lean request tool surface differs")
        if self.request_body.get("max_output_tokens") != self.effective_max_output_tokens:
            raise ValueError("Lean request output allowance differs")
        if self.input_count_method == LEAN_MOCK_COUNT_METHOD and self.requested_input_tokens != len(
            canonical_json(self.request_body).encode("utf-8")
        ):
            raise ValueError("Lean exact mock input count differs")
        if self.split_allowance.requested_input_tokens != self.requested_input_tokens:
            raise ValueError("Lean allowance input count differs")
        if self.split_allowance.effective_max_output_tokens != self.effective_max_output_tokens:
            raise ValueError("Lean allowance output count differs")
        if self.split_allowance.decision == "block":
            raise ValueError("blocked Lean request cannot be dispatch evidence")
        if self.request_body_hash != sha256_text(canonical_json(self.request_body)):
            raise ValueError("Lean request body hash differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("Lean request evidence content hash differs")
        return self


class LeanHarnessRequestEvidenceV2(LeanHarnessRequestEvidence):
    """Successor evidence binding completion and patch-normalization policy."""

    schema_version: Literal["lean-harness-request-evidence-v2"]
    runtime_policy_version: Literal["lean-harness-v2"]
    tool_schema_version: Literal["v8"]
    context_policy_version: Literal["phase-evidence-v13"]
    completion_policy_version: Literal["completion-driven-current-diff-v1"]
    patch_normalization_policy_version: Literal["safe-raw-diff-normalization-v1"]
    saturation_recovery: SaturationRecoveryAdmissionShadowV2
    phase_tool_surface: LeanPhaseToolSurfaceV2


class LeanHarnessRequestEvidenceV3(LeanHarnessRequestEvidenceV2):
    """Opt-in successor binding recursive-file glob normalization policy."""

    schema_version: Literal["lean-harness-request-evidence-v3"]
    runtime_policy_version: Literal["lean-harness-v3"]
    tool_schema_version: Literal["v9"]
    context_policy_version: Literal["phase-evidence-v13"]
    search_glob_policy_version: Literal["recursive-file-glob-normalization-v1"]


class LeanHarnessRequestEvidenceV4(LeanHarnessRequestEvidenceV3):
    """Offline successor binding recheck and split-bounded finalization."""

    schema_version: Literal["lean-harness-request-evidence-v4"]
    runtime_policy_version: Literal["lean-harness-v4"]
    context_policy_version: Literal["phase-evidence-v14"]
    completion_policy_version: Literal["completion-driven-current-diff-v2"]
    finalization_allowance_policy_version: Literal["configured-ceiling-split-bounded-v1"]
    phase_tool_surface: LeanPhaseToolSurfaceV3


class LeanHarnessRequestEvidenceV5(LeanHarnessRequestEvidenceV4):
    """Mechanical-friction successor with fresh edits and bounded recovery."""

    schema_version: Literal["lean-harness-request-evidence-v5"]
    runtime_policy_version: Literal["lean-harness-v5"]
    tool_schema_version: Literal["v10"]
    context_policy_version: Literal["phase-evidence-v15"]
    structured_edit_policy_version: Literal["gateway-fresh-preimage-unique-text-v1"]
    check_outcome_policy_version: Literal["invocation-vs-behavior-v1"]
    incomplete_recovery_policy_version: Literal["reasoning-only-single-retry-split-reserved-v1"]
    saturation_recovery: SaturationRecoveryAdmissionShadowV3
    incomplete_recovery: ReasoningIncompleteRecovery
    incomplete_recovery_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    recovery_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_mechanical_successor(self) -> Self:
        if self.incomplete_recovery_hash != self.incomplete_recovery.content_hash:
            raise ValueError("Lean incomplete recovery hash differs")
        if self.effective_max_output_tokens != self.incomplete_recovery.effective_max_output_tokens:
            raise ValueError("Lean incomplete recovery output allowance differs")
        if self.input_count_method == LEAN_MOCK_COUNT_METHOD:
            context = self.request_body.get("context")
        else:
            request_input = self.request_body.get("input")
            context = (
                request_input[1].get("content")
                if isinstance(request_input, list)
                and len(request_input) == 2
                and isinstance(request_input[1], dict)
                else None
            )
            reasoning = self.request_body.get("reasoning")
            if (
                not isinstance(reasoning, dict)
                or reasoning.get("effort") != self.incomplete_recovery.reasoning_effort
            ):
                raise ValueError("Lean incomplete recovery reasoning effort differs")
        if not isinstance(context, str) or self.recovery_context_hash != sha256_text(context):
            raise ValueError("Lean recovery context hash differs")
        return self


class LeanHarnessRequestEvidenceV6(LeanHarnessRequestEvidenceV5):
    """Opt-in successor binding role-aware recent-event descriptor compaction."""

    schema_version: Literal["lean-harness-request-evidence-v6"]
    runtime_policy_version: Literal["lean-harness-v6"]
    context_policy_version: Literal["phase-evidence-v16"]
    event_descriptor_role_policy_version: Literal["typed-distinct-input-role-v1"]
    context_compaction: LeanContextEventCompactionEvidenceV2


class LeanHarnessRequestEvidenceV7(LeanHarnessRequestEvidenceV4):
    """State-driven completion with one shared response retry and edit evidence."""

    schema_version: Literal["lean-harness-request-evidence-v7"]
    runtime_policy_version: Literal["lean-harness-v7"]
    tool_schema_version: Literal["v11"]
    context_policy_version: Literal["phase-evidence-v17"]
    completion_policy_version: Literal["state-driven-current-diff-v3"]
    structured_edit_policy_version: Literal["gateway-fresh-preimage-unique-text-v1"]
    check_outcome_policy_version: Literal["invocation-vs-behavior-v1"]
    event_descriptor_role_policy_version: Literal["typed-distinct-input-role-v1"]
    response_recovery_policy_version: Literal["completion-response-single-shared-retry-v1"]
    edit_correction_policy_version: Literal["bounded-public-current-source-v1"]
    saturation_recovery: SaturationRecoveryAdmissionShadowV3
    phase_tool_surface: LeanPhaseToolSurfaceV4
    context_compaction: LeanContextEventCompactionEvidenceV2
    completion_response_recovery: CompletionResponseRecovery
    completion_response_recovery_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    recovery_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_completion_successor(self) -> Self:
        recovery = self.completion_response_recovery
        if self.completion_response_recovery_hash != recovery.content_hash:
            raise ValueError("Lean completion response recovery hash differs")
        if self.effective_max_output_tokens != recovery.effective_max_output_tokens:
            raise ValueError("Lean completion recovery output allowance differs")
        if recovery.completion_lane_active is not self.phase_tool_surface.completion_lane_active:
            raise ValueError("Lean completion recovery lane differs from its tool surface")
        if self.input_count_method == LEAN_MOCK_COUNT_METHOD:
            context = self.request_body.get("context")
        else:
            request_input = self.request_body.get("input")
            context = (
                request_input[1].get("content")
                if isinstance(request_input, list)
                and len(request_input) == 2
                and isinstance(request_input[1], dict)
                else None
            )
            reasoning = self.request_body.get("reasoning")
            if (
                not isinstance(reasoning, dict)
                or reasoning.get("effort") != recovery.reasoning_effort
            ):
                raise ValueError("Lean completion recovery reasoning effort differs")
        if not isinstance(context, str) or self.recovery_context_hash != sha256_text(context):
            raise ValueError("Lean completion recovery context hash differs")
        return self


class LeanHarnessRequestEvidenceV8(LeanHarnessRequestEvidenceV4):
    """Ordered-check successor with request-bound task and correction evidence."""

    schema_version: Literal["lean-harness-request-evidence-v8"]
    runtime_policy_version: Literal["lean-harness-v8"]
    tool_schema_version: Literal["v12"]
    context_policy_version: Literal["phase-evidence-v18"]
    completion_policy_version: Literal["ordered-check-refresh-structured-correction-v1"]
    structured_edit_policy_version: Literal["gateway-fresh-preimage-unique-text-v1"]
    check_outcome_policy_version: Literal["invocation-vs-behavior-v1"]
    event_descriptor_role_policy_version: Literal["typed-distinct-input-role-v1"]
    edit_correction_policy_version: Literal["bounded-public-current-source-v1"]
    correction_context_policy_version: Literal["latest-public-edit-correction-once-v1"]
    provider_terminal_policy_version: Literal["explicit-terminal-before-accounting-v1"]
    saturation_recovery: SaturationRecoveryAdmissionShadowV3
    context_compaction: LeanContextEventCompactionEvidenceV2
    phase_tool_surface: CompletionToolSurface
    public_task_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_check_order: tuple[str, ...] = Field(min_length=1)
    completion_loop_decision: CompletionLoopDecision
    completion_loop_decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    correction_context: CurrentEditCorrectionContextEvidence
    correction_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_correction_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    completion_instruction: dict[str, Any]
    completion_instruction_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    completion_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]

    @model_validator(mode="after")
    def validate_ordered_completion_successor(self) -> Self:
        decision = self.completion_loop_decision
        if self.completion_loop_decision_hash != decision.content_hash:
            raise ValueError("Lean ordered completion decision hash differs")
        if self.phase_tool_surface.decision_hash != decision.content_hash:
            raise ValueError("Lean ordered completion surface decision differs")
        if self.correction_context_hash != self.correction_context.content_hash:
            raise ValueError("Lean ordered correction context hash differs")
        if (
            self.correction_context.source_context_hash
            != self.context_compaction.projected_context_hash
        ):
            raise ValueError("Lean ordered correction source context differs")
        if self.completion_instruction_hash != self.completion_instruction.get("content_hash"):
            raise ValueError("Lean ordered completion instruction hash differs")
        instruction_body = {
            key: value
            for key, value in self.completion_instruction.items()
            if key != "content_hash"
        }
        if self.completion_instruction_hash != sha256_json(instruction_body):
            raise ValueError("Lean ordered completion instruction content differs")
        if self.public_check_order != tuple(
            [*decision.completed_check_ids]
            + (
                [decision.expected_check_id]
                if decision.expected_check_id is not None
                and decision.expected_check_id not in decision.completed_check_ids
                else []
            )
            + [
                check_id
                for check_id in self.public_check_order
                if check_id not in decision.completed_check_ids
                and check_id != decision.expected_check_id
            ]
        ):
            raise ValueError("Lean ordered public check identity repeats or reorders")
        if len(set(self.public_check_order)) != len(self.public_check_order):
            raise ValueError("Lean ordered public check identity repeats")
        if self.effective_max_output_tokens > decision.effective_max_output_tokens:
            raise ValueError("Lean ordered request exceeds its target ceiling")
        if self.request_body.get("parallel_tool_calls") is not False:
            raise ValueError("Lean ordered request permits parallel tool calls")
        if self.input_count_method == LEAN_MOCK_COUNT_METHOD:
            context = self.request_body.get("context")
        else:
            request_input = self.request_body.get("input")
            context = (
                request_input[1].get("content")
                if isinstance(request_input, list)
                and len(request_input) == 2
                and isinstance(request_input[1], dict)
                else None
            )
            reasoning = self.request_body.get("reasoning")
            if (
                not isinstance(reasoning, dict)
                or reasoning.get("effort") != decision.reasoning_effort
            ):
                raise ValueError("Lean ordered completion reasoning effort differs")
        if not isinstance(context, str) or self.completion_context_hash != sha256_text(context):
            raise ValueError("Lean ordered completion context hash differs")
        try:
            payload = json.loads(context)
        except json.JSONDecodeError as exc:
            raise ValueError("Lean ordered completion context is not JSON") from exc
        if payload.get("completion_loop") != self.completion_instruction:
            raise ValueError("Lean ordered completion instruction was not delivered")
        return self


class LeanHarnessRequestEvidenceV9(LeanHarnessRequestEvidenceV4):
    """Bounded correction/review successor with shared protocol recovery."""

    schema_version: Literal["lean-harness-request-evidence-v9"]
    runtime_policy_version: Literal["lean-harness-v9"]
    tool_schema_version: Literal["v13"]
    context_policy_version: Literal["phase-evidence-v19"]
    completion_policy_version: Literal["bounded-correction-review-repair-v1"]
    structured_edit_policy_version: Literal["gateway-fresh-preimage-unique-text-v1"]
    check_outcome_policy_version: Literal["invocation-vs-behavior-v1"]
    event_descriptor_role_policy_version: Literal["typed-distinct-input-role-v1"]
    edit_correction_policy_version: Literal["bounded-public-current-source-v1"]
    correction_context_policy_version: Literal["latest-public-edit-correction-once-v1"]
    provider_terminal_policy_version: Literal["explicit-terminal-before-accounting-v1"]
    protocol_recovery_policy_version: Literal["shared-model-action-contract-recovery-v1"]
    saturation_recovery: SaturationRecoveryAdmissionShadowV3
    context_compaction: LeanContextEventCompactionEvidenceV2
    phase_tool_surface: WorkflowToolSurface
    public_task_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    public_check_order: tuple[str, ...] = Field(min_length=1)
    workflow_decision: WorkflowDecision
    workflow_decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    correction_context: CurrentEditCorrectionContextEvidence
    correction_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_correction_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    workflow_instruction: dict[str, Any]
    workflow_instruction_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    workflow_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parallel_tool_calls: Literal[False]
    one_tool_call_per_response: Literal[True]

    @model_validator(mode="after")
    def validate_workflow_successor(self) -> Self:
        decision = self.workflow_decision
        if self.workflow_decision_hash != decision.content_hash:
            raise ValueError("Lean workflow decision hash differs")
        if self.phase_tool_surface.decision_hash != decision.content_hash:
            raise ValueError("Lean workflow surface decision differs")
        if self.correction_context_hash != self.correction_context.content_hash:
            raise ValueError("Lean workflow correction context hash differs")
        plan_feedback = getattr(self, "plan_admission_feedback_projection", None)
        expected_correction_source = (
            plan_feedback.projected_context_hash
            if isinstance(
                plan_feedback,
                (
                    PlanAdmissionFeedbackProjectionEvidence,
                    CompactPlanFeedbackEvidence,
                    LifecyclePlanFeedbackEvidenceV3,
                ),
            )
            else self.context_compaction.projected_context_hash
        )
        if self.correction_context.source_context_hash != expected_correction_source:
            raise ValueError("Lean workflow correction source context differs")
        if self.workflow_instruction_hash != self.workflow_instruction.get("content_hash"):
            raise ValueError("Lean workflow instruction hash differs")
        instruction_body = {
            key: value for key, value in self.workflow_instruction.items() if key != "content_hash"
        }
        if self.workflow_instruction_hash != sha256_json(instruction_body):
            raise ValueError("Lean workflow instruction content differs")
        if len(set(self.public_check_order)) != len(self.public_check_order):
            raise ValueError("Lean workflow public checks repeat")
        if self.effective_max_output_tokens > decision.effective_max_output_tokens:
            raise ValueError("Lean workflow request exceeds target ceiling")
        if self.request_body.get("parallel_tool_calls") is not False:
            raise ValueError("Lean workflow request permits parallel tools")
        if self.input_count_method == LEAN_MOCK_COUNT_METHOD:
            context = self.request_body.get("context")
        else:
            request_input = self.request_body.get("input")
            context = (
                request_input[1].get("content")
                if isinstance(request_input, list)
                and len(request_input) == 2
                and isinstance(request_input[1], dict)
                else None
            )
            reasoning = self.request_body.get("reasoning")
            if (
                not isinstance(reasoning, dict)
                or reasoning.get("effort") != decision.reasoning_effort
            ):
                raise ValueError("Lean workflow reasoning effort differs")
        if not isinstance(context, str) or self.workflow_context_hash != sha256_text(context):
            raise ValueError("Lean workflow context hash differs")
        try:
            payload = json.loads(context)
        except json.JSONDecodeError as exc:
            raise ValueError("Lean workflow context is not JSON") from exc
        if payload.get("workflow") != self.workflow_instruction:
            raise ValueError("Lean workflow instruction was not delivered")
        return self


class LeanHarnessRequestEvidenceV10(LeanHarnessRequestEvidenceV9):
    """Pre-mutation public evidence and durable plan-gated successor."""

    schema_version: Literal["lean-harness-request-evidence-v10"]
    runtime_policy_version: Literal["lean-harness-v10"]
    tool_schema_version: Literal["v14"]
    context_policy_version: Literal["phase-evidence-v20"]
    completion_policy_version: Literal["public-evidence-plan-gate-v1"]
    record_work_plan_policy_version: Literal["public-evidence-plan-gate-v1"]
    public_task_spec: PublicTaskSpec
    public_task_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_plan_gate(self) -> Self:
        if self.public_task_spec_hash != self.public_task_spec.content_hash:
            raise ValueError("Lean V10 public TaskSpec hash differs")
        if self.public_task_spec.public_task_hash != self.public_task_hash:
            raise ValueError("Lean V10 public TaskSpec task binding differs")
        if self.public_task_spec.visible_check_ids != self.public_check_order:
            raise ValueError("Lean V10 public TaskSpec check order differs")
        if self.workflow_instruction.get("public_task_spec") != self.public_task_spec.model_dump(
            mode="json"
        ):
            raise ValueError("Lean V10 public TaskSpec was not delivered")
        return self


class LeanHarnessRequestEvidenceV11(LeanHarnessRequestEvidenceV9):
    """Model-visible evidence catalog and bounded plan-admission successor."""

    schema_version: Literal["lean-harness-request-evidence-v11"]
    runtime_policy_version: Literal["lean-harness-v11"]
    tool_schema_version: Literal["v15"]
    context_policy_version: Literal["phase-evidence-v21"]
    completion_policy_version: Literal["eligible-public-evidence-plan-gate-v2"]
    record_work_plan_policy_version: Literal["eligible-public-evidence-plan-gate-v2"]
    public_task_spec: PublicTaskSpec
    public_task_spec_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    eligible_plan_evidence_catalog: EligiblePlanEvidenceCatalog
    eligible_plan_evidence_catalog_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    active_work_plan: RecordedWorkPlanV2 | None
    active_work_state: ActiveWorkState | None
    active_work_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    phase_tool_surface: WorkflowToolSurfaceV2
    workflow_decision: WorkflowDecisionV2

    @model_validator(mode="after")
    def validate_visible_plan_gate(self) -> Self:
        if self.public_task_spec_hash != self.public_task_spec.content_hash:
            raise ValueError("Lean V11 public TaskSpec hash differs")
        if self.public_task_spec.public_task_hash != self.public_task_hash:
            raise ValueError("Lean V11 public TaskSpec task binding differs")
        if self.public_task_spec.visible_check_ids != self.public_check_order:
            raise ValueError("Lean V11 public TaskSpec check order differs")
        if (
            self.eligible_plan_evidence_catalog_hash
            != self.eligible_plan_evidence_catalog.content_hash
        ):
            raise ValueError("Lean V11 eligible evidence catalog hash differs")
        expected_state_hash = (
            self.active_work_state.content_hash
            if self.active_work_state is not None
            else sha256_json(None)
        )
        if self.active_work_state_hash != expected_state_hash:
            raise ValueError("Lean V11 active work state hash differs")
        if self.active_work_plan != (
            self.active_work_state.latest_plan if self.active_work_state is not None else None
        ):
            raise ValueError("Lean V11 active work plan differs")
        instruction = self.workflow_instruction
        if instruction.get("public_task_spec") != self.public_task_spec.model_dump(mode="json"):
            raise ValueError("Lean V11 public TaskSpec was not delivered")
        if instruction.get("eligible_plan_evidence_catalog") != (
            self.eligible_plan_evidence_catalog.model_dump(mode="json")
        ):
            raise ValueError("Lean V11 evidence catalog was not delivered")
        if instruction.get("active_work_plan") != (
            self.active_work_plan.model_dump(mode="json")
            if self.active_work_plan is not None
            else None
        ):
            raise ValueError("Lean V11 active plan was not delivered")
        return self


class LeanHarnessRequestEvidenceV12(LeanHarnessRequestEvidenceV11):
    """Mutation-epoch plan revision and bounded active-work-state successor."""

    schema_version: Literal["lean-harness-request-evidence-v12"]
    runtime_policy_version: Literal["lean-harness-v12"]
    tool_schema_version: Literal["v16"]
    context_policy_version: Literal["phase-evidence-v22"]
    completion_policy_version: Literal["epoch-work-plan-revision-v1"]
    record_work_plan_policy_version: Literal["epoch-work-plan-revision-v1"]

    @model_validator(mode="after")
    def validate_revision_state(self) -> Self:
        expected = (
            self.active_work_state.model_dump(mode="json")
            if self.active_work_state is not None
            else None
        )
        if self.workflow_instruction.get("active_work_state") != expected:
            raise ValueError("Lean V12 active work state was not delivered")
        return self


class LeanHarnessRequestEvidenceV13(LeanHarnessRequestEvidenceV12):
    """V12 workflow state with reserve-safe workflow-surface projection."""

    schema_version: Literal["lean-harness-request-evidence-v13"]
    runtime_policy_version: Literal["lean-harness-v13"]
    tool_schema_version: Literal["v17"]
    context_policy_version: Literal["phase-evidence-v23"]
    finalization_workflow_surface_policy_version: Literal[
        "workflow-surface-retained-through-reserve-v1"
    ]

    @model_validator(mode="after")
    def validate_finalization_workflow_surface(self) -> Self:
        if self.finalization_request_mode.mode == "finalization" and (
            self.phase_tool_surface.decision_hash != self.workflow_decision.content_hash
            or self.request_body.get("tools") != list(self.phase_tool_surface.selected_tool_schemas)
            or self.effective_max_output_tokens
            != self.workflow_decision.effective_max_output_tokens
        ):
            raise ValueError("Lean V13 finalization workflow surface differs")
        return self


class LeanHarnessRequestEvidenceV14(LeanHarnessRequestEvidenceV13):
    """V13 reserve safety plus a durable failed-check trigger projection."""

    schema_version: Literal["lean-harness-request-evidence-v14"]
    runtime_policy_version: Literal["lean-harness-v14"]
    tool_schema_version: Literal["v18"]
    context_policy_version: Literal["phase-evidence-v24"]
    completion_policy_version: Literal["required-failed-check-trigger-pinned-v1"]
    record_work_plan_policy_version: Literal["required-failed-check-trigger-pinned-v1"]
    required_trigger_pin_policy_version: Literal["required-failed-check-trigger-pinned-v1"]
    eligible_plan_evidence_catalog: EligiblePlanEvidenceCatalogV2

    @model_validator(mode="after")
    def validate_required_trigger_pin(self) -> Self:
        catalog = self.eligible_plan_evidence_catalog
        if self.workflow_decision.terminal_reason == ("required_workflow_evidence_unavailable"):
            if catalog.required_trigger_status != "unavailable":
                raise ValueError("Lean V14 unavailable trigger terminal differs")
        elif self.workflow_decision.revision_trigger == "check_failure" and (
            catalog.required_trigger_status != "pinned"
            or self.workflow_decision.required_trigger_evidence_id
            != catalog.required_trigger_evidence_id
        ):
            raise ValueError("Lean V14 required trigger pin differs")
        return self


class LeanHarnessRequestEvidenceV15(LeanHarnessRequestEvidenceV14):
    """V14 trigger safety plus bounded public semantic no-progress state."""

    schema_version: Literal["lean-harness-request-evidence-v15"]
    runtime_policy_version: Literal["lean-harness-v15"]
    tool_schema_version: Literal["v19"]
    context_policy_version: Literal["phase-evidence-v25"]
    completion_policy_version: Literal["public-failure-signature-no-progress-reset-v1"]
    record_work_plan_policy_version: Literal["public-failure-signature-no-progress-reset-v1"]
    semantic_progress_policy_version: Literal["public-failure-signature-no-progress-reset-v1"]
    workflow_decision: WorkflowDecisionV3
    semantic_progress_state: PublicSemanticProgressState | None
    semantic_progress_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_semantic_progress(self) -> Self:
        expected_hash = (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else sha256_json(None)
        )
        if self.semantic_progress_state_hash != expected_hash:
            raise ValueError("Lean V15 semantic progress state hash differs")
        instruction = self.workflow_instruction
        if instruction.get("schema_version") != WORKFLOW_INSTRUCTION_SCHEMA_V3:
            raise ValueError("Lean V15 workflow instruction schema differs")
        if instruction.get("semantic_progress_state") != (
            self.semantic_progress_state.model_dump(mode="json")
            if self.semantic_progress_state is not None
            else None
        ):
            raise ValueError("Lean V15 semantic progress state was not delivered")
        decision_state_hash = (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else None
        )
        if (
            self.workflow_decision.semantic_progress_state_hash != decision_state_hash
            or self.workflow_decision.semantic_reset_required
            is not bool(
                self.semantic_progress_state
                and self.semantic_progress_state.semantic_reset_required
            )
        ):
            raise ValueError("Lean V15 semantic decision binding differs")
        if self.workflow_decision.semantic_reset_required and (
            self.workflow_decision.required_prior_hypothesis_disposition != "rejected"
        ):
            raise ValueError("Lean V15 semantic reset disposition differs")
        if (
            self.workflow_decision.semantic_reset_required
            and self.workflow_decision.target == "corrective-mutation"
            and (
                self.active_work_state is None
                or self.active_work_state.latest_plan.trigger != "check_failure"
                or self.active_work_state.latest_plan.trigger_event_sequence
                != self.semantic_progress_state.current_failure_event_sequence
                or self.active_work_state.latest_plan.prior_hypothesis_disposition != "rejected"
            )
        ):
            raise ValueError("Lean V15 corrective mutation lacks a rejected reset plan")
        return self


class LeanHarnessRequestEvidenceV16(LeanHarnessRequestEvidenceV15):
    """V15 semantic progress with same-path public-read binding normalization."""

    schema_version: Literal["lean-harness-request-evidence-v16"]
    runtime_policy_version: Literal["lean-harness-v16"]
    tool_schema_version: Literal["v20"]
    context_policy_version: Literal["phase-evidence-v26"]
    candidate_binding_policy_version: Literal["same-path-public-read-binding-normalization-v1"]


class LeanHarnessRequestEvidenceV17(LeanHarnessRequestEvidenceV13):
    """Causal-plan admission plus gateway-owned exact baseline restore."""

    schema_version: Literal["lean-harness-request-evidence-v17"]
    runtime_policy_version: Literal["lean-harness-v17"]
    tool_schema_version: Literal["v21"]
    context_policy_version: Literal["phase-evidence-v27"]
    completion_policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    record_work_plan_policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    required_trigger_pin_policy_version: Literal["required-failed-check-trigger-pinned-v1"]
    semantic_progress_policy_version: Literal["public-failure-signature-no-progress-reset-v1"]
    candidate_binding_policy_version: Literal["same-path-public-read-binding-normalization-v1"]
    causal_activation_policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    causal_alternative_policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    eligible_plan_evidence_catalog: EligiblePlanEvidenceCatalogV2
    workflow_decision: WorkflowDecisionV3
    semantic_progress_state: PublicSemanticProgressState | None
    semantic_progress_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cross_reset_failure_trigger: CrossResetFailureTrigger | None
    cross_reset_failure_trigger_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mutation_baseline_projection: MutationBaselineProjection | None
    mutation_baseline_restore_receipt: MutationBaselineRestoreReceipt | None
    causal_mechanism_history: tuple[CausalMechanismHistoryEntry, ...]
    causal_mechanism_history_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_causal_activation(self) -> Self:
        state_hash = (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else sha256_json(None)
        )
        trigger_hash = (
            self.cross_reset_failure_trigger.content_hash
            if self.cross_reset_failure_trigger is not None
            else sha256_json(None)
        )
        history_body = [item.model_dump(mode="json") for item in self.causal_mechanism_history]
        if (
            self.semantic_progress_state_hash != state_hash
            or self.cross_reset_failure_trigger_hash != trigger_hash
            or self.causal_mechanism_history_hash != sha256_json(history_body)
            or self.workflow_instruction.get("schema_version") != CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA
            or self.workflow_instruction.get("cross_reset_failure_trigger")
            != (
                self.cross_reset_failure_trigger.model_dump(mode="json")
                if self.cross_reset_failure_trigger is not None
                else None
            )
            or self.workflow_instruction.get("causal_mechanism_history") != history_body
        ):
            raise ValueError("Lean V17 causal request projection differs")
        if self.workflow_decision.semantic_progress_state_hash != (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else None
        ):
            raise ValueError("Lean V17 semantic decision binding differs")
        trigger = self.cross_reset_failure_trigger
        if trigger is None:
            if (
                self.mutation_baseline_projection is not None
                or self.mutation_baseline_restore_receipt is not None
            ):
                raise ValueError("Lean V17 inactive restore evidence differs")
            if self.workflow_decision.revision_trigger == "check_failure" and (
                self.eligible_plan_evidence_catalog.required_trigger_status != "pinned"
                or self.workflow_decision.required_trigger_evidence_id
                != self.eligible_plan_evidence_catalog.required_trigger_evidence_id
            ):
                raise ValueError("Lean V17 current-diff trigger pin differs")
        else:
            baseline = self.mutation_baseline_projection
            receipt = self.mutation_baseline_restore_receipt
            if (
                baseline is None
                or receipt is None
                or self.semantic_progress_state is None
                or self.eligible_plan_evidence_catalog.required_trigger_status != "not_required"
                or trigger.source_semantic_progress_state_hash
                != self.semantic_progress_state.content_hash
                or trigger.mutation_baseline_projection_hash != baseline.content_hash
                or trigger.mutation_baseline_restore_receipt_hash != receipt.content_hash
                or trigger.restored_baseline_diff_hash
                != self.eligible_plan_evidence_catalog.worktree_diff_hash
                or not self.causal_mechanism_history
                or self.workflow_decision.required_trigger_evidence_id
                != f"pev:{trigger.failure_event_sequences[-1]}"
            ):
                raise ValueError("Lean V17 cross-reset binding differs")
        if self.workflow_decision.target == "corrective-mutation" and (
            not self.causal_mechanism_history
            or self.workflow_decision.active_plan_hash
            != self.causal_mechanism_history[-1].plan_hash
        ):
            raise ValueError("Lean V17 mutation lacks an active causal plan")
        return self


class LeanHarnessRequestEvidenceV18(LeanHarnessRequestEvidenceV13):
    """V17 rollback limits with the server-owned causal-plan request surface."""

    schema_version: Literal["lean-harness-request-evidence-v18"]
    runtime_policy_version: Literal["lean-harness-v18"]
    tool_schema_version: Literal["v22"]
    context_policy_version: Literal["phase-evidence-v28"]
    completion_policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    record_work_plan_policy_version: Literal["gateway-owned-causal-plan-projection-v1"]
    required_trigger_pin_policy_version: Literal["required-failed-check-trigger-pinned-v1"]
    semantic_progress_policy_version: Literal["public-failure-signature-no-progress-reset-v1"]
    candidate_binding_policy_version: Literal["same-path-public-read-binding-normalization-v1"]
    causal_activation_policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    causal_alternative_policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    causal_plan_projection_policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    causal_plan_projection_activation_policy_version: Literal[
        "gateway-owned-causal-plan-projection-v1"
    ]
    eligible_plan_evidence_catalog: EligiblePlanEvidenceCatalogV2
    workflow_decision: WorkflowDecisionV3
    semantic_progress_state: PublicSemanticProgressState | None
    semantic_progress_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cross_reset_failure_trigger: CrossResetFailureTrigger | None
    cross_reset_failure_trigger_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mutation_baseline_projection: MutationBaselineProjection | None
    mutation_baseline_restore_receipt: MutationBaselineRestoreReceipt | None
    causal_mechanism_history: tuple[CausalMechanismHistoryEntryV2, ...]
    causal_mechanism_history_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    causal_plan_request_projection: ActivatedCausalPlanRequest | None
    causal_plan_request_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_causal_projection_activation(self) -> Self:
        state_hash = (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else sha256_json(None)
        )
        trigger_hash = (
            self.cross_reset_failure_trigger.content_hash
            if self.cross_reset_failure_trigger is not None
            else sha256_json(None)
        )
        projection_hash = (
            self.causal_plan_request_projection.content_hash
            if self.causal_plan_request_projection is not None
            else sha256_json(None)
        )
        history_body = [item.model_dump(mode="json") for item in self.causal_mechanism_history]
        instruction = self.workflow_instruction
        if (
            self.semantic_progress_state_hash != state_hash
            or self.cross_reset_failure_trigger_hash != trigger_hash
            or self.causal_mechanism_history_hash != sha256_json(history_body)
            or self.causal_plan_request_projection_hash != projection_hash
            or instruction.get("schema_version") != CAUSAL_WORKFLOW_INSTRUCTION_SCHEMA_V5
            or instruction.get("cross_reset_failure_trigger")
            != (
                self.cross_reset_failure_trigger.model_dump(mode="json")
                if self.cross_reset_failure_trigger is not None
                else None
            )
            or instruction.get("causal_mechanism_history") != history_body
            or instruction.get("causal_plan_request_projection")
            != (
                self.causal_plan_request_projection.model_dump(mode="json")
                if self.causal_plan_request_projection is not None
                else None
            )
        ):
            raise ValueError("Lean V18 causal projection request differs")
        plan_schemas = [
            item
            for item in self.phase_tool_surface.selected_tool_schemas
            if item.get("name") in {"record_work_plan", "revise_work_plan"}
        ]
        if bool(plan_schemas) is not (self.causal_plan_request_projection is not None):
            raise ValueError("Lean V18 causal projection surface differs")
        if self.causal_plan_request_projection is not None and (
            len(plan_schemas) != 1
            or plan_schemas[0].get("parameters") != self.causal_plan_request_projection.parameters
        ):
            raise ValueError("Lean V18 dynamic causal schema differs")
        if self.workflow_decision.semantic_progress_state_hash != (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else None
        ):
            raise ValueError("Lean V18 semantic decision binding differs")
        trigger = self.cross_reset_failure_trigger
        if trigger is None:
            if (
                self.mutation_baseline_projection is not None
                or self.mutation_baseline_restore_receipt is not None
            ):
                raise ValueError("Lean V18 inactive restore evidence differs")
            if self.workflow_decision.revision_trigger == "check_failure" and (
                self.eligible_plan_evidence_catalog.required_trigger_status != "pinned"
                or self.workflow_decision.required_trigger_evidence_id
                != self.eligible_plan_evidence_catalog.required_trigger_evidence_id
            ):
                raise ValueError("Lean V18 current-diff trigger pin differs")
        else:
            baseline = self.mutation_baseline_projection
            receipt = self.mutation_baseline_restore_receipt
            if (
                baseline is None
                or receipt is None
                or self.semantic_progress_state is None
                or self.eligible_plan_evidence_catalog.required_trigger_status != "not_required"
                or trigger.source_semantic_progress_state_hash
                != self.semantic_progress_state.content_hash
                or trigger.mutation_baseline_projection_hash != baseline.content_hash
                or trigger.mutation_baseline_restore_receipt_hash != receipt.content_hash
                or trigger.restored_baseline_diff_hash
                != self.eligible_plan_evidence_catalog.worktree_diff_hash
                or not self.causal_mechanism_history
                or self.workflow_decision.required_trigger_evidence_id
                != f"pev:{trigger.failure_event_sequences[-1]}"
            ):
                raise ValueError("Lean V18 cross-reset binding differs")
        if self.workflow_decision.target == "corrective-mutation" and (
            not self.causal_mechanism_history
            or self.workflow_decision.active_plan_hash
            != self.causal_mechanism_history[-1].plan_hash
        ):
            raise ValueError("Lean V18 mutation lacks an active projected causal plan")
        return self


class LeanHarnessRequestEvidenceV19(LeanHarnessRequestEvidenceV13):
    """V18 causal projection plus request-bound public exploration closure."""

    schema_version: Literal["lean-harness-request-evidence-v19"]
    runtime_policy_version: Literal["lean-harness-v19"]
    tool_schema_version: Literal["v23"]
    context_policy_version: Literal["phase-evidence-v29"]
    completion_policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    record_work_plan_policy_version: Literal["gateway-owned-public-exploration-closure-v1"]
    required_trigger_pin_policy_version: Literal["required-failed-check-trigger-pinned-v1"]
    semantic_progress_policy_version: Literal["public-failure-signature-no-progress-reset-v1"]
    candidate_binding_policy_version: Literal["same-path-public-read-binding-normalization-v1"]
    causal_activation_policy_version: Literal["gateway-owned-causal-baseline-reset-v1"]
    causal_alternative_policy_version: Literal["bounded-public-causal-alternative-gate-v1"]
    causal_plan_projection_policy_version: Literal["server-owned-public-causal-plan-projection-v1"]
    causal_plan_projection_activation_policy_version: Literal[
        "gateway-owned-causal-plan-projection-v1"
    ]
    exploration_gate_policy_version: Literal["public-boundary-and-unknown-closure-v1"]
    exploration_gate_activation_policy_version: Literal[
        "gateway-owned-public-exploration-closure-v1"
    ]
    eligible_plan_evidence_catalog: EligiblePlanEvidenceCatalogV2
    workflow_decision: WorkflowDecisionV3
    semantic_progress_state: PublicSemanticProgressState | None
    semantic_progress_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cross_reset_failure_trigger: CrossResetFailureTrigger | None
    cross_reset_failure_trigger_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mutation_baseline_projection: MutationBaselineProjection | None
    mutation_baseline_restore_receipt: MutationBaselineRestoreReceipt | None
    causal_mechanism_history: tuple[CausalMechanismHistoryEntryV2, ...]
    causal_mechanism_history_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    causal_plan_request_projection: ActivatedCausalPlanRequest | None
    causal_plan_request_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    activated_exploration_plan_request: ActivatedExplorationPlanRequest | None
    activated_exploration_plan_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_exploration_activation(self) -> Self:
        state_hash = (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else sha256_json(None)
        )
        trigger_hash = (
            self.cross_reset_failure_trigger.content_hash
            if self.cross_reset_failure_trigger is not None
            else sha256_json(None)
        )
        request = self.activated_exploration_plan_request
        base_request = (
            request.source_request.source_request.base_request
            if isinstance(
                request,
                (LifecycleBoundPlanRequest, LifecycleComponentBoundPlanRequest),
            )
            else request.source_request.base_request
            if request is not None
            else None
        )
        history_body = [item.model_dump(mode="json") for item in self.causal_mechanism_history]
        instruction = self.workflow_instruction
        if (
            self.semantic_progress_state_hash != state_hash
            or self.cross_reset_failure_trigger_hash != trigger_hash
            or self.causal_mechanism_history_hash != sha256_json(history_body)
            or self.causal_plan_request_projection != base_request
            or self.causal_plan_request_projection_hash
            != (base_request.content_hash if base_request is not None else sha256_json(None))
            or self.activated_exploration_plan_request_hash
            != (request.content_hash if request is not None else sha256_json(None))
            or instruction.get("schema_version") != EXPLORATION_WORKFLOW_INSTRUCTION_SCHEMA
            or instruction.get("cross_reset_failure_trigger")
            != (
                self.cross_reset_failure_trigger.model_dump(mode="json")
                if self.cross_reset_failure_trigger is not None
                else None
            )
            or instruction.get("causal_mechanism_history") != history_body
            or instruction.get("causal_plan_request_projection")
            != (base_request.model_dump(mode="json") if base_request is not None else None)
            or instruction.get("activated_exploration_plan_request")
            != (request.model_dump(mode="json") if request is not None else None)
        ):
            raise ValueError("Lean V19 exploration request projection differs")
        plan_schemas = [
            item
            for item in self.phase_tool_surface.selected_tool_schemas
            if item.get("name") in {"record_work_plan", "revise_work_plan"}
        ]
        if bool(plan_schemas) is not (request is not None):
            raise ValueError(
                "Lean V19 exploration projection surface differs: "
                f"plan_schemas={len(plan_schemas)}, request_present={request is not None}, "
                f"target={self.workflow_decision.target}, "
                f"allowed={self.workflow_decision.allowed_tool_names}, "
                f"tools={self.phase_tool_surface.selected_tool_names}"
            )
        if request is not None and (
            len(plan_schemas) != 1 or plan_schemas[0].get("parameters") != request.parameters
        ):
            raise ValueError("Lean V19 dynamic exploration schema differs")
        if self.workflow_decision.semantic_progress_state_hash != (
            self.semantic_progress_state.content_hash
            if self.semantic_progress_state is not None
            else None
        ):
            raise ValueError("Lean V19 semantic decision binding differs")
        trigger = self.cross_reset_failure_trigger
        if trigger is None:
            if (
                self.mutation_baseline_projection is not None
                or self.mutation_baseline_restore_receipt is not None
            ):
                raise ValueError("Lean V19 inactive restore evidence differs")
            if self.workflow_decision.revision_trigger == "check_failure" and (
                self.eligible_plan_evidence_catalog.required_trigger_status != "pinned"
                or self.workflow_decision.required_trigger_evidence_id
                != self.eligible_plan_evidence_catalog.required_trigger_evidence_id
            ):
                raise ValueError("Lean V19 current-diff trigger pin differs")
        else:
            baseline = self.mutation_baseline_projection
            receipt = self.mutation_baseline_restore_receipt
            if (
                baseline is None
                or receipt is None
                or self.semantic_progress_state is None
                or self.eligible_plan_evidence_catalog.required_trigger_status != "not_required"
                or trigger.source_semantic_progress_state_hash
                != self.semantic_progress_state.content_hash
                or trigger.mutation_baseline_projection_hash != baseline.content_hash
                or trigger.mutation_baseline_restore_receipt_hash != receipt.content_hash
                or trigger.restored_baseline_diff_hash
                != self.eligible_plan_evidence_catalog.worktree_diff_hash
                or not self.causal_mechanism_history
                or self.workflow_decision.required_trigger_evidence_id
                != f"pev:{trigger.failure_event_sequences[-1]}"
            ):
                raise ValueError("Lean V19 cross-reset binding differs")
        if self.workflow_decision.target == "corrective-mutation" and (
            not self.causal_mechanism_history
            or self.workflow_decision.active_plan_hash
            != self.causal_mechanism_history[-1].plan_hash
        ):
            raise ValueError("Lean V19 mutation lacks an active exploration-gated plan")
        return self


class LeanHarnessRequestEvidenceV20(LeanHarnessRequestEvidenceV19):
    """V19 exploration closure with one request/dispatch semantic epoch."""

    schema_version: Literal["lean-harness-request-evidence-v20"]
    runtime_policy_version: Literal["lean-harness-v20"]
    tool_schema_version: Literal["v24"]
    context_policy_version: Literal["phase-evidence-v30"]
    semantic_progress_event_domain_policy_version: Literal[
        "post-restore-semantic-progress-epoch-parity-v1"
    ]
    semantic_progress_event_domain: SemanticProgressEventDomain
    semantic_progress_event_domain_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_semantic_progress_epoch(self) -> Self:
        domain = self.semantic_progress_event_domain
        if (
            domain.run_id != self.eligible_plan_evidence_catalog.run_id
            or self.semantic_progress_event_domain_hash != domain.content_hash
            or (
                self.cross_reset_failure_trigger is None
                and self.semantic_progress_state is not None
                and not set(self.semantic_progress_state.failure_event_sequences).issubset(
                    domain.epoch_event_sequences
                )
            )
        ):
            raise ValueError("Lean V20 semantic event-domain binding differs")
        return self


class LeanHarnessRequestEvidenceV21(LeanHarnessRequestEvidenceV20):
    """V20 epoch parity plus a durable, request-proven initial-plan pin."""

    schema_version: Literal["lean-harness-request-evidence-v21"]
    runtime_policy_version: Literal["lean-harness-v21"]
    tool_schema_version: Literal["v25"]
    context_policy_version: Literal["phase-evidence-v31"]
    plan_gate_liveness_policy_version: Literal["pinned-plan-gate-liveness-v1"]
    eligible_plan_evidence_catalog: EligiblePlanEvidenceCatalogV3
    activated_exploration_plan_request: PinnedExplorationPlanRequest | None
    plan_gate_readiness_source: Literal["not_ready", "current_request", "recovered_pin"]
    plan_gate_readiness_snapshot: PlanGateReadinessSnapshot | None
    plan_gate_readiness_snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    recovered_plan_gate_pin: RecoveredPlanGateReadinessPin | None
    recovered_plan_gate_pin_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_plan_gate_liveness(self) -> Self:
        snapshot_hash = (
            self.plan_gate_readiness_snapshot.content_hash
            if self.plan_gate_readiness_snapshot is not None
            else sha256_json(None)
        )
        pin_hash = (
            self.recovered_plan_gate_pin.content_hash
            if self.recovered_plan_gate_pin is not None
            else sha256_json(None)
        )
        expected_source = (
            "recovered_pin"
            if self.recovered_plan_gate_pin is not None
            else "current_request"
            if self.plan_gate_readiness_snapshot is not None
            else "not_ready"
        )
        instruction = self.workflow_instruction
        if (
            self.plan_gate_readiness_source != expected_source
            or self.plan_gate_readiness_snapshot_hash != snapshot_hash
            or self.recovered_plan_gate_pin_hash != pin_hash
            or (
                self.recovered_plan_gate_pin is not None
                and (
                    self.plan_gate_readiness_snapshot != self.recovered_plan_gate_pin.snapshot
                    or self.eligible_plan_evidence_catalog.plan_gate_readiness_status != "pinned"
                    or self.eligible_plan_evidence_catalog.plan_gate_readiness_pin_hash
                    != self.recovered_plan_gate_pin.content_hash
                )
            )
            or (
                self.recovered_plan_gate_pin is None
                and self.eligible_plan_evidence_catalog.plan_gate_readiness_status != "not_pinned"
            )
            or (
                self.workflow_decision.allowed_tool_names == ("record_work_plan",)
                and (
                    self.plan_gate_readiness_snapshot is None
                    or self.activated_exploration_plan_request is None
                )
            )
            or instruction.get("plan_gate_liveness_policy_version") != PLAN_GATE_LIVENESS_POLICY
            or instruction.get("plan_gate_readiness_snapshot")
            != (
                self.plan_gate_readiness_snapshot.model_dump(mode="json")
                if self.plan_gate_readiness_snapshot is not None
                else None
            )
            or instruction.get("recovered_plan_gate_pin")
            != (
                self.recovered_plan_gate_pin.model_dump(mode="json")
                if self.recovered_plan_gate_pin is not None
                else None
            )
        ):
            raise ValueError("Lean V21 plan-gate liveness binding differs")
        return self


class LeanHarnessRequestEvidenceV22(LeanHarnessRequestEvidenceV21):
    """V21 liveness with bounded model-facing admission feedback."""

    schema_version: Literal["lean-harness-request-evidence-v22"]
    runtime_policy_version: Literal["lean-harness-v22"]
    tool_schema_version: Literal["v25"]
    context_policy_version: Literal["phase-evidence-v32"]
    plan_admission_feedback_projection_policy_version: Literal["bounded-plan-admission-feedback-v1"]
    plan_admission_feedback_projection: PlanAdmissionFeedbackProjectionEvidence
    plan_admission_feedback_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_bounded_plan_feedback(self) -> Self:
        projection = self.plan_admission_feedback_projection
        if (
            self.plan_admission_feedback_projection_hash != projection.content_hash
            or projection.source_compaction_evidence_hash != self.context_compaction.content_hash
            or projection.source_context_hash != self.context_compaction.projected_context_hash
            or projection.source_recent_events_hash
            != self.context_compaction.projected_recent_events_hash
            or projection.source_context_bytes != self.context_compaction.projected_context_bytes
            or self.correction_context.source_context_hash != projection.projected_context_hash
            or self.correction_context.source_context_bytes != projection.projected_context_bytes
        ):
            raise ValueError("Lean V22 plan-admission feedback binding differs")
        context = (
            self.request_body.get("context")
            if self.input_count_method == LEAN_MOCK_COUNT_METHOD
            else (
                self.request_body.get("input", [{}, {}])[1].get("content")
                if isinstance(self.request_body.get("input"), list)
                and len(self.request_body["input"]) == 2
                and isinstance(self.request_body["input"][1], dict)
                else None
            )
        )
        try:
            request_context = json.loads(context) if isinstance(context, str) else None
        except json.JSONDecodeError as exc:
            raise ValueError("Lean V22 request context is not JSON") from exc
        recent_events = (
            request_context.get("recent_events") if isinstance(request_context, dict) else None
        )
        if not isinstance(recent_events, list):
            raise ValueError("Lean V22 request recent events differ")
        projected_indices: list[int] = []
        for item in projection.event_projections:
            if item.event_index >= len(recent_events):
                raise ValueError("Lean V22 projected event index differs")
            event = recent_events[item.event_index]
            if not isinstance(event, dict):
                raise ValueError("Lean V22 projected event shape differs")
            details = (
                event.get("payload", {}).get("error_details")
                if isinstance(event.get("payload"), dict)
                else None
            )
            try:
                feedback_model = (
                    CompatibleBoundedWorkPlanAdmissionFeedback
                    if self.runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V25
                    else BoundedWorkPlanAdmissionFeedback
                )
                delivered_feedback = feedback_model.model_validate_json(canonical_json(details))
            except ValueError as exc:
                raise ValueError("Lean V22 projected feedback contract differs") from exc
            if (
                event.get("sequence") != item.event_sequence
                or sha256_json(event) != item.projected_event_hash
                or not isinstance(details, dict)
                or details.get("schema_version") != PROJECTED_FEEDBACK_SCHEMA
                or details.get("projection_policy_version")
                != PLAN_ADMISSION_FEEDBACK_PROJECTION_POLICY
                or details.get("source_event_hash") != item.source_event_hash
                or details.get("source_error_details_hash") != item.source_error_details_hash
                or sha256_json(details) != item.projected_error_details_hash
                or details.get("omitted_details")
                != [entry.model_dump(mode="json") for entry in item.omitted_details]
                or delivered_feedback.model_dump(mode="json") != details
            ):
                raise ValueError("Lean V22 projected event binding differs")
            projected_indices.append(item.event_index)
        delivered_indices = [
            index
            for index, event in enumerate(recent_events)
            if isinstance(event, dict)
            and isinstance(event.get("payload"), dict)
            and isinstance(event["payload"].get("error_details"), dict)
            and event["payload"]["error_details"].get("schema_version") == PROJECTED_FEEDBACK_SCHEMA
        ]
        if projected_indices != delivered_indices:
            raise ValueError("Lean V22 projected event inventory differs")
        return self


class LeanHarnessRequestEvidenceV23(LeanHarnessRequestEvidenceV22):
    """V22 feedback plus bounded, explicitly self-directed source exploration."""

    schema_version: Literal["lean-harness-request-evidence-v23"]
    runtime_policy_version: Literal["lean-harness-v23"]
    tool_schema_version: Literal["v26"]
    context_policy_version: Literal["phase-evidence-v33"]
    record_work_plan_policy_version: Literal["bounded-self-directed-exploration-v1"]
    exploration_gate_activation_policy_version: Literal["bounded-self-directed-exploration-v1"]
    plan_gate_liveness_policy_version: Literal["bounded-self-directed-exploration-v1"]
    self_directed_exploration_policy_version: Literal["bounded-self-directed-exploration-v1"]
    eligible_plan_evidence_catalog: EligiblePlanEvidenceCatalogV4
    workflow_decision: WorkflowDecisionV4
    activated_exploration_plan_request: SelfDirectedPlanRequest | None
    plan_gate_readiness_snapshot: SelfDirectedPlanGateSnapshot | None
    recovered_plan_gate_pin: RecoveredSelfDirectedPlanGatePin | None
    self_directed_exploration_state: SelfDirectedExplorationState | None
    self_directed_exploration_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_self_directed_exploration(self) -> Self:
        state_hash = (
            self.self_directed_exploration_state.content_hash
            if self.self_directed_exploration_state is not None
            else sha256_json(None)
        )
        instruction = self.workflow_instruction
        plan_schemas = [
            item
            for item in self.phase_tool_surface.selected_tool_schemas
            if item.get("name") in {"record_work_plan", "revise_work_plan"}
        ]
        if (
            self.self_directed_exploration_state_hash != state_hash
            or self.workflow_decision.self_directed_exploration_state_hash
            != (
                self.self_directed_exploration_state.content_hash
                if self.self_directed_exploration_state is not None
                else None
            )
            or instruction.get("self_directed_exploration_policy_version")
            != SELF_DIRECTED_EXPLORATION_POLICY
            or instruction.get("self_directed_exploration_state")
            != (
                self.self_directed_exploration_state.model_dump(mode="json")
                if self.self_directed_exploration_state is not None
                else None
            )
            or bool(plan_schemas) is not (self.activated_exploration_plan_request is not None)
            or (
                self.activated_exploration_plan_request is not None
                and (
                    len(plan_schemas) != 1
                    or plan_schemas[0].get("parameters")
                    != self.activated_exploration_plan_request.parameters
                )
            )
        ):
            raise ValueError("Lean V23 self-directed exploration binding differs")
        return self


class LeanHarnessRequestEvidenceV24(LeanHarnessRequestEvidenceV23):
    """V23 semantics with exact pre-plan tools and bounded request context."""

    schema_version: Literal["lean-harness-request-evidence-v24"]
    runtime_policy_version: Literal["lean-harness-v24"]
    tool_schema_version: Literal["v26"]
    context_policy_version: Literal["phase-evidence-v34"]
    exact_pre_plan_surface_policy_version: Literal["exact-self-directed-pre-plan-surface-v1"]
    exact_pre_plan_surface_projection: ExactPrePlanSurfaceProjectionEvidence
    exact_pre_plan_surface_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bounded_request_context_policy_version: Literal[
        "bounded-public-investigation-request-context-v1"
    ]
    bounded_investigation_request_context: BoundedInvestigationRequestContextEvidence
    bounded_investigation_request_context_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    normalized_bounded_investigation_request_context_hash: str = Field(
        pattern=r"^sha256:[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def validate_bounded_request_successor(self) -> Self:
        surface = self.exact_pre_plan_surface_projection
        projection = self.bounded_investigation_request_context
        if (
            self.exact_pre_plan_surface_projection_hash != surface.content_hash
            or surface.projected_decision_hash != self.workflow_decision.content_hash
            or surface.self_directed_state_hash != self.self_directed_exploration_state_hash
            or self.bounded_investigation_request_context_hash != projection.content_hash
            or projection.source_correction_context_evidence_hash
            != self.correction_context.content_hash
            or projection.source_context_hash != self.correction_context.projected_context_hash
        ):
            raise ValueError("Lean V24 request-only projection binding differs")
        context = (
            self.request_body.get("context")
            if self.input_count_method == LEAN_MOCK_COUNT_METHOD
            else (
                self.request_body.get("input", [{}, {}])[1].get("content")
                if isinstance(self.request_body.get("input"), list)
                and len(self.request_body["input"]) == 2
                and isinstance(self.request_body["input"][1], dict)
                else None
            )
        )
        try:
            request_context = json.loads(context) if isinstance(context, str) else None
        except json.JSONDecodeError as exc:
            raise ValueError("Lean V24 request context is not JSON") from exc
        if not isinstance(request_context, dict):
            raise ValueError("Lean V24 request context shape differs")
        workflow = request_context.pop("workflow", None)
        ledger = request_context.get("investigation_ledger")
        recent = request_context.get("recent_events")
        tool_names = tuple(
            item.get("name")
            for item in self.request_body.get("tools", [])
            if isinstance(item, dict)
        )
        if (
            not isinstance(workflow, dict)
            or not isinstance(ledger, dict)
            or not isinstance(recent, list)
            or sha256_text(canonical_json(request_context)) != projection.projected_context_hash
            or ledger.get("content_hash") != projection.projected_investigation_ledger_hash
            or sha256_json(recent) != projection.projected_recent_events_hash
            or tool_names != self.workflow_decision.allowed_tool_names
            or workflow.get("exact_pre_plan_surface_policy_version")
            != EXACT_PRE_PLAN_SURFACE_POLICY
            or workflow.get("exact_pre_plan_surface_projection_hash") != surface.content_hash
            or workflow.get("bounded_investigation_context_policy_version")
            != BOUNDED_REQUEST_CONTEXT_POLICY
            or workflow.get("bounded_investigation_context_projection_hash")
            != projection.content_hash
            or (
                self.self_directed_exploration_state is not None
                and self.self_directed_exploration_state.active_plan_hash is None
                and "run_check" in tool_names
            )
        ):
            raise ValueError("Lean V24 delivered request projection differs")
        return self


class LeanHarnessRequestEvidenceV25(LeanHarnessRequestEvidenceV24):
    """V24 request bounds with trigger-exact plan and feedback contracts."""

    schema_version: Literal["lean-harness-request-evidence-v25"]
    runtime_policy_version: Literal["lean-harness-v25"]
    tool_schema_version: Literal["v26"]
    context_policy_version: Literal["phase-evidence-v35"]
    plan_contract_compatibility_policy_version: Literal[
        "trigger-bound-plan-contract-compatibility-v1"
    ]
    activated_exploration_plan_request: TriggerBoundSelfDirectedPlanRequest | None

    @model_validator(mode="after")
    def validate_plan_contract_compatibility(self) -> Self:
        request = self.activated_exploration_plan_request
        if request is None:
            return self
        compatibility_request = (
            request.source_request
            if isinstance(
                request,
                (LifecycleBoundPlanRequest, LifecycleComponentBoundPlanRequest),
            )
            else request
        )
        properties = request.parameters.get("properties")
        trigger = compatibility_request.source_request.base_request.source_projection.trigger
        expected = (
            {"type": "null", "enum": [None]}
            if trigger == "initial"
            else {
                "type": "string",
                "enum": ["retained", "refined", "rejected"],
            }
        )
        if (
            compatibility_request.compatibility_policy_version
            != self.plan_contract_compatibility_policy_version
            or not isinstance(properties, dict)
            or properties.get("prior_hypothesis_disposition") != expected
        ):
            raise ValueError("Lean V25 plan compatibility binding differs")
        return self


class LeanHarnessRequestEvidenceV26(LeanHarnessRequestEvidenceV25):
    """V25 semantics with R21 reliability seams and no predecessor mutation."""

    schema_version: Literal["lean-harness-request-evidence-v26"]
    runtime_policy_version: Literal["lean-harness-v26"]
    tool_schema_version: Literal["v27"]
    context_policy_version: Literal["phase-evidence-v36"]
    plan_admission_feedback_projection_policy_version: Literal["bounded-plan-admission-feedback-v2"]
    plan_admission_feedback_projection: CompactPlanFeedbackEvidence
    generation_incomplete_recovery_policy_version: Literal[
        "dedicated-generation-incomplete-recovery-v1"
    ]
    generation_incomplete_recovery_state: GenerationIncompleteRecoveryState
    anchored_read_policy_version: Literal["anchored-source-read-v1"]
    lifecycle_plan_policy_version: Literal["public-lifecycle-state-transition-plan-v1"]
    activated_exploration_plan_request: LifecycleBoundPlanRequest | None

    @model_validator(mode="after")
    def validate_bounded_plan_feedback(self) -> Self:
        projection = self.plan_admission_feedback_projection
        if (
            self.plan_admission_feedback_projection_hash != projection.content_hash
            or projection.source_context_hash != self.context_compaction.projected_context_hash
            or self.correction_context.source_context_hash != projection.projected_context_hash
            or self.correction_context.source_context_bytes != projection.projected_context_bytes
        ):
            raise ValueError("Lean V26 compact plan-feedback binding differs")
        return self

    @model_validator(mode="after")
    def validate_plan_contract_compatibility(self) -> Self:
        request = self.activated_exploration_plan_request
        if request is None:
            return self
        source = request.source_request
        properties = request.parameters.get("properties")
        trigger = source.source_request.base_request.source_projection.trigger
        expected = (
            {"type": "null", "enum": [None]}
            if trigger == "initial"
            else {"type": "string", "enum": ["retained", "refined", "rejected"]}
        )
        if (
            source.compatibility_policy_version != self.plan_contract_compatibility_policy_version
            or request.policy_version != self.lifecycle_plan_policy_version
            or self.workflow_instruction.get("lifecycle_plan_policy_version")
            != self.lifecycle_plan_policy_version
            or not isinstance(properties, dict)
            or properties.get("prior_hypothesis_disposition") != expected
            or (
                request.policy_version == LIFECYCLE_PLAN_POLICY
                and "lifecycle_state_transition" not in properties
            )
            or (
                request.policy_version == LIFECYCLE_COMPONENT_BINDING_POLICY
                and "lifecycle_component_binding" not in properties
            )
            or self.generation_incomplete_recovery_state.policy_version
            != self.generation_incomplete_recovery_policy_version
        ):
            raise ValueError("Lean V26 reliability binding differs")
        return self


class LeanHarnessRequestEvidenceV27(LeanHarnessRequestEvidenceV26):
    """V26 workflow with strict request admission before any provider transport."""

    schema_version: Literal["lean-harness-request-evidence-v27"]
    runtime_policy_version: Literal["lean-harness-v27"]
    tool_schema_version: Literal["v28"]
    context_policy_version: Literal["phase-evidence-v37"]
    provider_tool_schema_admission: dict[str, Any]

    @model_validator(mode="after")
    def validate_provider_schema_admission(self) -> Self:
        expected = validate_provider_tool_schemas(self.request_body)
        if self.provider_tool_schema_admission != expected:
            raise ValueError("Lean V27 provider tool schema admission differs")
        return self


class LeanHarnessRequestEvidenceV28(LeanHarnessRequestEvidenceV27):
    """V27 transport admission with one lifecycle component registry."""

    schema_version: Literal["lean-harness-request-evidence-v28"]
    runtime_policy_version: Literal["lean-harness-v28"]
    tool_schema_version: Literal["v29"]
    context_policy_version: Literal["phase-evidence-v38"]
    plan_admission_feedback_projection_policy_version: Literal["bounded-plan-admission-feedback-v3"]
    plan_admission_feedback_projection: LifecyclePlanFeedbackEvidenceV3
    lifecycle_plan_policy_version: Literal["public-lifecycle-component-binding-plan-v2"]
    activated_exploration_plan_request: LifecycleComponentBoundPlanRequest | None


def recover_plan_gate_readiness_pins(
    *,
    run_id: str,
    events: tuple[RunEvent, ...] | list[RunEvent],
    request_artifact_loader: Callable[[str, str], dict[str, Any]],
) -> tuple[RecoveredPlanGateReadinessPin | RecoveredSelfDirectedPlanGatePin, ...]:
    """Recover the first actually delivered readiness request for each gate."""

    event_tuple = tuple(events)
    if any(event.run_id != run_id for event in event_tuple):
        raise ContractError("plan-gate recovery contains a foreign run")
    recovered: dict[str, RecoveredPlanGateReadinessPin | RecoveredSelfDirectedPlanGatePin] = {}
    for event in event_tuple:
        if event.type != EventType.MODEL_CALLED:
            continue
        path = event.payload.get("request_artifact_path")
        artifact_hash = event.payload.get("request_artifact_hash")
        request_body_hash = event.payload.get("request_body_hash")
        if not all(isinstance(value, str) for value in (path, artifact_hash, request_body_hash)):
            raise RecoveryError("model call lacks its request artifact binding")
        payload = request_artifact_loader(path, artifact_hash)
        raw = payload.get("lean_harness_request") if isinstance(payload, dict) else None
        if not isinstance(raw, dict) or raw.get("schema_version") not in {
            LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
            LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
            LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
            LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
            LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
            LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
            LEAN_REQUEST_EVIDENCE_SCHEMA_V27,
            LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
        }:
            continue
        evidence = validate_persisted_lean_harness_request(payload)
        if not isinstance(evidence, LeanHarnessRequestEvidenceV21):
            raise RecoveryError("plan-gate request artifact selected another evidence schema")
        if evidence.request_body_hash != request_body_hash:
            raise RecoveryError("model call request body binding differs")
        snapshot = evidence.plan_gate_readiness_snapshot
        if snapshot is None:
            continue
        pin = (
            bind_recovered_self_directed_pin(
                snapshot=snapshot,
                source_model_event_sequence=event.sequence,
                source_request_artifact_hash=artifact_hash,
                source_request_body_hash=request_body_hash,
            )
            if isinstance(evidence, LeanHarnessRequestEvidenceV23)
            else bind_recovered_plan_gate_pin(
                snapshot=snapshot,
                source_model_event_sequence=event.sequence,
                source_request_artifact_hash=artifact_hash,
                source_request_body_hash=request_body_hash,
            )
        )
        prior = recovered.get(snapshot.plan_gate_id)
        if prior is None:
            recovered[snapshot.plan_gate_id] = pin
            continue
        if evidence.recovered_plan_gate_pin != prior:
            raise RecoveryError("recovered plan-gate pin chain differs")
    return tuple(recovered[key] for key in sorted(recovered))


LeanHarnessRequestEvidenceAny = (
    LeanHarnessRequestEvidence
    | LeanHarnessRequestEvidenceV2
    | LeanHarnessRequestEvidenceV3
    | LeanHarnessRequestEvidenceV4
    | LeanHarnessRequestEvidenceV5
    | LeanHarnessRequestEvidenceV6
    | LeanHarnessRequestEvidenceV7
    | LeanHarnessRequestEvidenceV8
    | LeanHarnessRequestEvidenceV9
    | LeanHarnessRequestEvidenceV10
    | LeanHarnessRequestEvidenceV11
    | LeanHarnessRequestEvidenceV12
    | LeanHarnessRequestEvidenceV13
    | LeanHarnessRequestEvidenceV14
    | LeanHarnessRequestEvidenceV15
    | LeanHarnessRequestEvidenceV16
    | LeanHarnessRequestEvidenceV17
    | LeanHarnessRequestEvidenceV18
    | LeanHarnessRequestEvidenceV19
    | LeanHarnessRequestEvidenceV20
    | LeanHarnessRequestEvidenceV21
    | LeanHarnessRequestEvidenceV22
    | LeanHarnessRequestEvidenceV23
    | LeanHarnessRequestEvidenceV24
    | LeanHarnessRequestEvidenceV25
    | LeanHarnessRequestEvidenceV26
    | LeanHarnessRequestEvidenceV27
    | LeanHarnessRequestEvidenceV28
)


@dataclass(frozen=True)
class LeanHarnessDependencies:
    preregistration: LeanRuntimeIntegrationPreregistration
    reserve: FinalizationReserveContract
    thresholds: SaturationRecoveryPublicQualification


@dataclass(frozen=True)
class LeanHarnessAssembledRequest:
    context: str
    context_hash: str
    tool_schemas: tuple[dict[str, Any], ...]
    request_body: dict[str, Any]
    requested_input_tokens: int
    evidence: LeanHarnessRequestEvidenceAny


def load_lean_harness_dependencies(repository: str | Path = ".") -> LeanHarnessDependencies:
    """Load only the three exact, offline-qualified predecessor contracts."""

    preregistration = load_lean_runtime_integration_preregistration(repository)
    reserve = load_r8_public_development_finalization_reserve(repository)
    root = Path(repository).resolve()
    threshold_raw = ensure_within(root, SATURATION_QUALIFICATION_PATH).read_bytes()
    if (
        len(threshold_raw) != _SATURATION_QUALIFICATION_FILE_BYTES
        or sha256_bytes(threshold_raw) != _SATURATION_QUALIFICATION_FILE_SHA256
    ):
        raise ContractError("Lean preregistered saturation qualification file differs")
    try:
        thresholds = SaturationRecoveryPublicQualification.model_validate_json(threshold_raw)
    except ValueError as exc:
        raise ContractError("Lean preregistered saturation qualification is invalid") from exc
    if (
        saturation_qualification_bytes(thresholds) != threshold_raw
        or thresholds.content_hash != _SATURATION_QUALIFICATION_CONTENT_HASH
    ):
        raise ContractError("Lean preregistered saturation qualification differs")
    if preregistration.runtime_contract_hash != preregistration.runtime_contract.content_hash:
        raise ContractError("Lean preregistration runtime binding differs")
    return LeanHarnessDependencies(
        preregistration=preregistration,
        reserve=reserve,
        thresholds=thresholds,
    )


def _completion_surface_target(
    phase_surface: PhaseToolSurfaceProjection,
    mode: Literal["exploration", "finalization"],
    *,
    prefer_registered_check: bool = False,
    state_driven_after_mutation: bool = False,
) -> tuple[str, set[str] | None]:
    mutation_present = phase_surface.phase_evidence.get("mutation_present") is True
    if mode == "exploration" and not (state_driven_after_mutation and mutation_present):
        return "phase-policy", None
    evidence = phase_surface.phase_evidence
    if evidence.get("mutation_present") is not True:
        return "mutation", {"apply_patch"}
    pending = evidence.get("pending_checks")
    if isinstance(pending, (list, tuple)) and pending:
        allowed_actions = set(phase_surface.phase_allowed_actions)
        if tuple(phase_surface.phase_allowed_actions) == ("run_check",) or (
            prefer_registered_check and "run_check" in allowed_actions
        ):
            return "visible-check", {"run_check"}
        if prefer_registered_check and "apply_patch" in allowed_actions:
            return "corrective-mutation", {"apply_patch"}
        return "mutation", {"apply_patch"}
    if (
        evidence.get("review_event_sequence") is None
        or evidence.get("review_presented_to_model") is not True
    ):
        return "diff-review", {"get_diff"}
    return "submission", {"finish_task"}


def _lean_surface(
    *,
    phase_surface: PhaseToolSurfaceProjection,
    saturation: (
        SaturationRecoveryAdmissionShadow
        | SaturationRecoveryAdmissionShadowV2
        | SaturationRecoveryAdmissionShadowV3
    ),
    mode: Literal["exploration", "finalization"],
    completion_driven: bool = False,
    completion_successor: bool = False,
    state_driven_after_mutation: bool = False,
) -> (
    LeanPhaseToolSurface | LeanPhaseToolSurfaceV2 | LeanPhaseToolSurfaceV3 | LeanPhaseToolSurfaceV4
):
    saturation_schemas = tuple(copy.deepcopy(item) for item in saturation.selected_tool_schemas)
    saturation_names = _tool_names(saturation_schemas)
    projection = {
        name: _FINALIZATION_CAPABILITIES[name]
        for name in saturation_names
        if name in _FINALIZATION_CAPABILITIES
    }
    completion_target = None
    if completion_driven:
        completion_target, allowed = _completion_surface_target(
            phase_surface,
            mode,
            prefer_registered_check=completion_successor,
            state_driven_after_mutation=state_driven_after_mutation,
        )
    else:
        allowed = set(phase_surface.finalization_tool_names) if mode == "finalization" else None
    selected = tuple(
        schema
        for schema, name in zip(saturation_schemas, saturation_names, strict=True)
        if allowed is None or projection.get(name) in allowed
    )
    if not selected:
        raise ContractError("Lean phase/finalization filter leaves no callable tool")
    selected_names = _tool_names(selected)
    body: dict[str, Any] = {
        "schema_version": (
            LEAN_PHASE_TOOL_SURFACE_SCHEMA_V4
            if state_driven_after_mutation
            else LEAN_PHASE_TOOL_SURFACE_SCHEMA_V3
            if completion_successor
            else LEAN_PHASE_TOOL_SURFACE_SCHEMA_V2
            if completion_driven
            else LEAN_PHASE_TOOL_SURFACE_SCHEMA
        ),
        **({"completion_target": completion_target} if completion_driven else {}),
        **(
            {
                "registered_check_preferred": True,
                "recheck_after_mutation_required": completion_target
                in {"mutation", "corrective-mutation"},
            }
            if completion_successor
            else {}
        ),
        **(
            {
                "state_driven_after_mutation": True,
                "completion_lane_active": bool(
                    mode == "finalization"
                    or phase_surface.phase_evidence.get("mutation_present") is True
                ),
            }
            if state_driven_after_mutation
            else {}
        ),
        "mode": mode,
        "source_phase_tool_surface": phase_surface.model_dump(mode="python"),
        "source_phase_tool_surface_hash": phase_surface.content_hash,
        "saturation_recovery_evidence_hash": saturation.content_hash,
        "saturation_selected_tool_schemas": saturation_schemas,
        "saturation_selected_tool_names": saturation_names,
        "finalization_capability_projection": projection,
        "selected_tool_schemas": selected,
        "selected_tool_names": selected_names,
        "removed_for_finalization": tuple(
            name for name in saturation_names if name not in selected_names
        ),
        "selected_tool_schema_hash": sha256_json(list(selected)),
        "structured_edit_maps_to_mutation_capability": True,
        "condition_neutral": True,
    }
    model_type = (
        LeanPhaseToolSurfaceV4
        if state_driven_after_mutation
        else LeanPhaseToolSurfaceV3
        if completion_successor
        else LeanPhaseToolSurfaceV2
        if completion_driven
        else LeanPhaseToolSurface
    )
    return model_type.model_validate({**body, "content_hash": sha256_json(body)})


def _request_body(
    *,
    model_id: str,
    system_prompt: str,
    context: str,
    tools: tuple[dict[str, Any], ...],
    max_output_tokens: int,
) -> dict[str, Any]:
    return {
        "model": model_id,
        "system_prompt": system_prompt,
        "context": context,
        "tools": [copy.deepcopy(item) for item in tools],
        "max_output_tokens": max_output_tokens,
    }


def assemble_lean_harness_request(
    *,
    dependencies: LeanHarnessDependencies,
    built_context: BuiltContext,
    normalized_no_memory_context: BuiltContext,
    base_tool_schemas: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    phase_evidence: EvidenceState,
    events: list[RunEvent] | tuple[RunEvent, ...],
    usage: Usage,
    budget: Budget,
    model_id: str,
    system_prompt: str,
    configured_max_output_tokens: int,
    memory_delivery_evidence_sha256: str,
    runtime_policy_version: str = LEAN_RUNTIME_POLICY_VERSION,
    task: PublicTask | None = None,
    provider_request_builder: (
        Callable[[str, tuple[dict[str, Any], ...], int], dict[str, Any]] | None
    ) = None,
    provider_input_token_counter: Callable[[dict[str, Any]], int] | None = None,
    live_input_count_method: Literal[
        "openai-input-token-count-v1",
        "openai-input-token-count-v2-parallel-bound",
    ] = LEAN_LIVE_COUNT_METHOD,
    recovered_plan_gate_pins: tuple[
        RecoveredPlanGateReadinessPin | RecoveredSelfDirectedPlanGatePin, ...
    ] = (),
) -> LeanHarnessAssembledRequest:
    """Build, recount, and bind an exact versioned request before persistence."""

    if type(dependencies) is not LeanHarnessDependencies:
        raise TypeError("Lean request requires exact loaded dependencies")
    if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION
        evidence_model: type[
            LeanHarnessRequestEvidence
            | LeanHarnessRequestEvidenceV2
            | LeanHarnessRequestEvidenceV3
            | LeanHarnessRequestEvidenceV4
            | LeanHarnessRequestEvidenceV5
            | LeanHarnessRequestEvidenceV6
            | LeanHarnessRequestEvidenceV7
            | LeanHarnessRequestEvidenceV8
            | LeanHarnessRequestEvidenceV9
            | LeanHarnessRequestEvidenceV10
            | LeanHarnessRequestEvidenceV11
            | LeanHarnessRequestEvidenceV12
            | LeanHarnessRequestEvidenceV13
            | LeanHarnessRequestEvidenceV14
            | LeanHarnessRequestEvidenceV15
            | LeanHarnessRequestEvidenceV16
            | LeanHarnessRequestEvidenceV17
            | LeanHarnessRequestEvidenceV18
            | LeanHarnessRequestEvidenceV19
            | LeanHarnessRequestEvidenceV20
            | LeanHarnessRequestEvidenceV21
            | LeanHarnessRequestEvidenceV22
            | LeanHarnessRequestEvidenceV23
            | LeanHarnessRequestEvidenceV24
            | LeanHarnessRequestEvidenceV25
            | LeanHarnessRequestEvidenceV26
            | LeanHarnessRequestEvidenceV27
            | LeanHarnessRequestEvidenceV28
        ] = LeanHarnessRequestEvidence
        successor_bindings: dict[str, Any] = {}
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V2:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V2
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V2
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V2
        evidence_model = LeanHarnessRequestEvidenceV2
        successor_bindings = {
            "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V2,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V3:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V3
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V3
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V3
        evidence_model = LeanHarnessRequestEvidenceV3
        successor_bindings = {
            "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V2,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V4:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V4
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V4
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V4
        evidence_model = LeanHarnessRequestEvidenceV4
        successor_bindings = {
            "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V4,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V5:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V5
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V5
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V5
        evidence_model = LeanHarnessRequestEvidenceV5
        successor_bindings = {
            "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V4,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
            "structured_edit_policy_version": (LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5),
            "check_outcome_policy_version": LEAN_CHECK_OUTCOME_POLICY_VERSION_V5,
            "incomplete_recovery_policy_version": (LEAN_INCOMPLETE_RECOVERY_POLICY_VERSION_V5),
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V6:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V6
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V6
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V6
        evidence_model = LeanHarnessRequestEvidenceV6
        successor_bindings = {
            "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V4,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
            "structured_edit_policy_version": (LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5),
            "check_outcome_policy_version": LEAN_CHECK_OUTCOME_POLICY_VERSION_V5,
            "incomplete_recovery_policy_version": (LEAN_INCOMPLETE_RECOVERY_POLICY_VERSION_V5),
            "event_descriptor_role_policy_version": (LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6),
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V7:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V7
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V7
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V7
        evidence_model = LeanHarnessRequestEvidenceV7
        successor_bindings = {
            "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V7,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
            "structured_edit_policy_version": (LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5),
            "check_outcome_policy_version": LEAN_CHECK_OUTCOME_POLICY_VERSION_V5,
            "event_descriptor_role_policy_version": (LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6),
            "response_recovery_policy_version": (LEAN_RESPONSE_RECOVERY_POLICY_VERSION_V7),
            "edit_correction_policy_version": LEAN_EDIT_CORRECTION_POLICY_VERSION_V7,
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V8:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V8
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V8
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V8
        evidence_model = LeanHarnessRequestEvidenceV8
        successor_bindings = {
            "completion_policy_version": LEAN_COMPLETION_POLICY_VERSION_V8,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
            "structured_edit_policy_version": (LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5),
            "check_outcome_policy_version": LEAN_CHECK_OUTCOME_POLICY_VERSION_V5,
            "event_descriptor_role_policy_version": (LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6),
            "edit_correction_policy_version": LEAN_EDIT_CORRECTION_POLICY_VERSION_V7,
            "correction_context_policy_version": (LEAN_CORRECTION_CONTEXT_POLICY_VERSION_V8),
            "provider_terminal_policy_version": (LEAN_PROVIDER_TERMINAL_POLICY_VERSION_V8),
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V9:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V9
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V9
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V9
        evidence_model = LeanHarnessRequestEvidenceV9
        successor_bindings = {
            "completion_policy_version": LEAN_WORKFLOW_POLICY_VERSION_V9,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
            "structured_edit_policy_version": (LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5),
            "check_outcome_policy_version": LEAN_CHECK_OUTCOME_POLICY_VERSION_V5,
            "event_descriptor_role_policy_version": (LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6),
            "edit_correction_policy_version": LEAN_EDIT_CORRECTION_POLICY_VERSION_V7,
            "correction_context_policy_version": (LEAN_CORRECTION_CONTEXT_POLICY_VERSION_V8),
            "provider_terminal_policy_version": (LEAN_PROVIDER_TERMINAL_POLICY_VERSION_V8),
            "protocol_recovery_policy_version": ("shared-model-action-contract-recovery-v1"),
        }
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V10:
        request_evidence_schema = LEAN_REQUEST_EVIDENCE_SCHEMA_V10
        tool_schema_version = LEAN_TOOL_SCHEMA_VERSION_V10
        context_policy_version = LEAN_CONTEXT_POLICY_VERSION_V10
        evidence_model = LeanHarnessRequestEvidenceV10
        successor_bindings = {
            "completion_policy_version": LEAN_WORKFLOW_POLICY_VERSION_V10,
            "patch_normalization_policy_version": (LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2),
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
            "structured_edit_policy_version": (LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5),
            "check_outcome_policy_version": LEAN_CHECK_OUTCOME_POLICY_VERSION_V5,
            "event_descriptor_role_policy_version": (LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6),
            "edit_correction_policy_version": LEAN_EDIT_CORRECTION_POLICY_VERSION_V7,
            "correction_context_policy_version": (LEAN_CORRECTION_CONTEXT_POLICY_VERSION_V8),
            "provider_terminal_policy_version": (LEAN_PROVIDER_TERMINAL_POLICY_VERSION_V8),
            "protocol_recovery_policy_version": ("shared-model-action-contract-recovery-v1"),
            "record_work_plan_policy_version": LEAN_WORKFLOW_POLICY_VERSION_V10,
        }
    elif runtime_policy_version in {
        LEAN_RUNTIME_POLICY_VERSION_V11,
        LEAN_RUNTIME_POLICY_VERSION_V12,
        LEAN_RUNTIME_POLICY_VERSION_V13,
        LEAN_RUNTIME_POLICY_VERSION_V14,
        LEAN_RUNTIME_POLICY_VERSION_V15,
        LEAN_RUNTIME_POLICY_VERSION_V16,
        LEAN_RUNTIME_POLICY_VERSION_V17,
        LEAN_RUNTIME_POLICY_VERSION_V18,
        LEAN_RUNTIME_POLICY_VERSION_V19,
        LEAN_RUNTIME_POLICY_VERSION_V20,
        LEAN_RUNTIME_POLICY_VERSION_V21,
        LEAN_RUNTIME_POLICY_VERSION_V22,
        LEAN_RUNTIME_POLICY_VERSION_V23,
        LEAN_RUNTIME_POLICY_VERSION_V24,
        LEAN_RUNTIME_POLICY_VERSION_V25,
        LEAN_RUNTIME_POLICY_VERSION_V26,
        LEAN_RUNTIME_POLICY_VERSION_V27,
        LEAN_RUNTIME_POLICY_VERSION_V28,
    }:
        request_evidence_schema = {
            LEAN_RUNTIME_POLICY_VERSION_V11: LEAN_REQUEST_EVIDENCE_SCHEMA_V11,
            LEAN_RUNTIME_POLICY_VERSION_V12: LEAN_REQUEST_EVIDENCE_SCHEMA_V12,
            LEAN_RUNTIME_POLICY_VERSION_V13: LEAN_REQUEST_EVIDENCE_SCHEMA_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14: LEAN_REQUEST_EVIDENCE_SCHEMA_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15: LEAN_REQUEST_EVIDENCE_SCHEMA_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16: LEAN_REQUEST_EVIDENCE_SCHEMA_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17: LEAN_REQUEST_EVIDENCE_SCHEMA_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18: LEAN_REQUEST_EVIDENCE_SCHEMA_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19: LEAN_REQUEST_EVIDENCE_SCHEMA_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20: LEAN_REQUEST_EVIDENCE_SCHEMA_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21: LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22: LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23: LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24: LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25: LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26: LEAN_REQUEST_EVIDENCE_SCHEMA_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27: LEAN_REQUEST_EVIDENCE_SCHEMA_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28: LEAN_REQUEST_EVIDENCE_SCHEMA_V28,
        }[runtime_policy_version]
        tool_schema_version = {
            LEAN_RUNTIME_POLICY_VERSION_V11: LEAN_TOOL_SCHEMA_VERSION_V11,
            LEAN_RUNTIME_POLICY_VERSION_V12: LEAN_TOOL_SCHEMA_VERSION_V12,
            LEAN_RUNTIME_POLICY_VERSION_V13: LEAN_TOOL_SCHEMA_VERSION_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14: LEAN_TOOL_SCHEMA_VERSION_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15: LEAN_TOOL_SCHEMA_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16: LEAN_TOOL_SCHEMA_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17: LEAN_TOOL_SCHEMA_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18: LEAN_TOOL_SCHEMA_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19: LEAN_TOOL_SCHEMA_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20: LEAN_TOOL_SCHEMA_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21: LEAN_TOOL_SCHEMA_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22: LEAN_TOOL_SCHEMA_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23: LEAN_TOOL_SCHEMA_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24: LEAN_TOOL_SCHEMA_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25: LEAN_TOOL_SCHEMA_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26: LEAN_TOOL_SCHEMA_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27: LEAN_TOOL_SCHEMA_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28: LEAN_TOOL_SCHEMA_VERSION_V28,
        }[runtime_policy_version]
        context_policy_version = {
            LEAN_RUNTIME_POLICY_VERSION_V11: LEAN_CONTEXT_POLICY_VERSION_V11,
            LEAN_RUNTIME_POLICY_VERSION_V12: LEAN_CONTEXT_POLICY_VERSION_V12,
            LEAN_RUNTIME_POLICY_VERSION_V13: LEAN_CONTEXT_POLICY_VERSION_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14: LEAN_CONTEXT_POLICY_VERSION_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15: LEAN_CONTEXT_POLICY_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16: LEAN_CONTEXT_POLICY_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17: LEAN_CONTEXT_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18: LEAN_CONTEXT_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19: LEAN_CONTEXT_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20: LEAN_CONTEXT_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21: LEAN_CONTEXT_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22: LEAN_CONTEXT_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23: LEAN_CONTEXT_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24: LEAN_CONTEXT_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25: LEAN_CONTEXT_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26: LEAN_CONTEXT_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27: LEAN_CONTEXT_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28: LEAN_CONTEXT_POLICY_VERSION_V28,
        }[runtime_policy_version]
        evidence_model = {
            LEAN_RUNTIME_POLICY_VERSION_V11: LeanHarnessRequestEvidenceV11,
            LEAN_RUNTIME_POLICY_VERSION_V12: LeanHarnessRequestEvidenceV12,
            LEAN_RUNTIME_POLICY_VERSION_V13: LeanHarnessRequestEvidenceV13,
            LEAN_RUNTIME_POLICY_VERSION_V14: LeanHarnessRequestEvidenceV14,
            LEAN_RUNTIME_POLICY_VERSION_V15: LeanHarnessRequestEvidenceV15,
            LEAN_RUNTIME_POLICY_VERSION_V16: LeanHarnessRequestEvidenceV16,
            LEAN_RUNTIME_POLICY_VERSION_V17: LeanHarnessRequestEvidenceV17,
            LEAN_RUNTIME_POLICY_VERSION_V18: LeanHarnessRequestEvidenceV18,
            LEAN_RUNTIME_POLICY_VERSION_V19: LeanHarnessRequestEvidenceV19,
            LEAN_RUNTIME_POLICY_VERSION_V20: LeanHarnessRequestEvidenceV20,
            LEAN_RUNTIME_POLICY_VERSION_V21: LeanHarnessRequestEvidenceV21,
            LEAN_RUNTIME_POLICY_VERSION_V22: LeanHarnessRequestEvidenceV22,
            LEAN_RUNTIME_POLICY_VERSION_V23: LeanHarnessRequestEvidenceV23,
            LEAN_RUNTIME_POLICY_VERSION_V24: LeanHarnessRequestEvidenceV24,
            LEAN_RUNTIME_POLICY_VERSION_V25: LeanHarnessRequestEvidenceV25,
            LEAN_RUNTIME_POLICY_VERSION_V26: LeanHarnessRequestEvidenceV26,
            LEAN_RUNTIME_POLICY_VERSION_V27: LeanHarnessRequestEvidenceV27,
            LEAN_RUNTIME_POLICY_VERSION_V28: LeanHarnessRequestEvidenceV28,
        }[runtime_policy_version]
        workflow_policy = (
            LEAN_CAUSAL_ACTIVATION_POLICY_VERSION_V17
            if runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
            else LEAN_WORKFLOW_POLICY_VERSION_V11
            if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V11
            else LEAN_WORKFLOW_POLICY_VERSION_V15
            if runtime_policy_version
            in {LEAN_RUNTIME_POLICY_VERSION_V15, LEAN_RUNTIME_POLICY_VERSION_V16}
            else LEAN_WORKFLOW_POLICY_VERSION_V14
            if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V14
            else LEAN_WORKFLOW_POLICY_VERSION_V12
        )
        successor_bindings = {
            "completion_policy_version": workflow_policy,
            "patch_normalization_policy_version": LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2,
            "search_glob_policy_version": LEAN_SEARCH_GLOB_POLICY_VERSION_V3,
            "finalization_allowance_policy_version": (
                LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4
            ),
            "structured_edit_policy_version": LEAN_STRUCTURED_EDIT_POLICY_VERSION_V5,
            "check_outcome_policy_version": LEAN_CHECK_OUTCOME_POLICY_VERSION_V5,
            "event_descriptor_role_policy_version": LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6,
            "edit_correction_policy_version": LEAN_EDIT_CORRECTION_POLICY_VERSION_V7,
            "correction_context_policy_version": LEAN_CORRECTION_CONTEXT_POLICY_VERSION_V8,
            "provider_terminal_policy_version": LEAN_PROVIDER_TERMINAL_POLICY_VERSION_V8,
            "protocol_recovery_policy_version": "shared-model-action-contract-recovery-v1",
            "record_work_plan_policy_version": workflow_policy,
            **(
                {
                    "finalization_workflow_surface_policy_version": (
                        LEAN_FINALIZATION_WORKFLOW_SURFACE_POLICY_VERSION_V13
                    )
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V13,
                    LEAN_RUNTIME_POLICY_VERSION_V14,
                    LEAN_RUNTIME_POLICY_VERSION_V15,
                    LEAN_RUNTIME_POLICY_VERSION_V16,
                    LEAN_RUNTIME_POLICY_VERSION_V17,
                    LEAN_RUNTIME_POLICY_VERSION_V18,
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "required_trigger_pin_policy_version": (
                        LEAN_REQUIRED_TRIGGER_PIN_POLICY_VERSION_V14
                    )
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V14,
                    LEAN_RUNTIME_POLICY_VERSION_V15,
                    LEAN_RUNTIME_POLICY_VERSION_V16,
                    LEAN_RUNTIME_POLICY_VERSION_V17,
                    LEAN_RUNTIME_POLICY_VERSION_V18,
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {"semantic_progress_policy_version": (LEAN_SEMANTIC_PROGRESS_POLICY_VERSION_V15)}
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V15,
                    LEAN_RUNTIME_POLICY_VERSION_V16,
                    LEAN_RUNTIME_POLICY_VERSION_V17,
                    LEAN_RUNTIME_POLICY_VERSION_V18,
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {"candidate_binding_policy_version": (LEAN_CANDIDATE_BINDING_POLICY_VERSION_V16)}
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V16,
                    LEAN_RUNTIME_POLICY_VERSION_V17,
                    LEAN_RUNTIME_POLICY_VERSION_V18,
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "causal_activation_policy_version": (LEAN_CAUSAL_ACTIVATION_POLICY_VERSION_V17),
                    "causal_alternative_policy_version": CAUSAL_ALTERNATIVE_POLICY,
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V17,
                    LEAN_RUNTIME_POLICY_VERSION_V18,
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "record_work_plan_policy_version": (
                        LEAN_CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY_VERSION_V18
                    ),
                    "causal_plan_projection_policy_version": (CAUSAL_PLAN_PROJECTION_POLICY),
                    "causal_plan_projection_activation_policy_version": (
                        LEAN_CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY_VERSION_V18
                    ),
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V18,
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "record_work_plan_policy_version": (
                        LEAN_EXPLORATION_GATE_ACTIVATION_POLICY_VERSION_V19
                    ),
                    "exploration_gate_policy_version": EXPLORATION_GATE_POLICY,
                    "exploration_gate_activation_policy_version": (
                        LEAN_EXPLORATION_GATE_ACTIVATION_POLICY_VERSION_V19
                    ),
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "semantic_progress_event_domain_policy_version": (
                        LEAN_SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY_VERSION_V20
                    )
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {"plan_gate_liveness_policy_version": (LEAN_PLAN_GATE_LIVENESS_POLICY_VERSION_V21)}
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V21, LEAN_RUNTIME_POLICY_VERSION_V22}
                else {}
            ),
            **(
                {
                    "plan_admission_feedback_projection_policy_version": (
                        LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22
                    )
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "record_work_plan_policy_version": (
                        LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23
                    ),
                    "exploration_gate_activation_policy_version": (
                        LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23
                    ),
                    "plan_gate_liveness_policy_version": (
                        LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23
                    ),
                    "self_directed_exploration_policy_version": (
                        LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23
                    ),
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "exact_pre_plan_surface_policy_version": (
                        LEAN_EXACT_PRE_PLAN_SURFACE_POLICY_VERSION_V24
                    ),
                    "bounded_request_context_policy_version": (
                        LEAN_BOUNDED_REQUEST_CONTEXT_POLICY_VERSION_V24
                    ),
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "plan_contract_compatibility_policy_version": (
                        LEAN_PLAN_CONTRACT_COMPATIBILITY_POLICY_VERSION_V25
                    )
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
            **(
                {
                    "generation_incomplete_recovery_policy_version": (
                        LEAN_GENERATION_INCOMPLETE_RECOVERY_POLICY_VERSION_V26
                    ),
                    "plan_admission_feedback_projection_policy_version": (
                        LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V28
                        if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V28
                        else LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V26
                    ),
                    "anchored_read_policy_version": LEAN_ANCHORED_READ_POLICY_VERSION_V26,
                    "lifecycle_plan_policy_version": (
                        LEAN_LIFECYCLE_PLAN_POLICY_VERSION_V28
                        if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V28
                        else LEAN_LIFECYCLE_PLAN_POLICY_VERSION_V26
                    ),
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {}
            ),
        }
    else:
        raise ContractError("unsupported Lean Harness runtime policy version")
    if recovered_plan_gate_pins and runtime_policy_version not in {
        LEAN_RUNTIME_POLICY_VERSION_V21,
        LEAN_RUNTIME_POLICY_VERSION_V22,
        LEAN_RUNTIME_POLICY_VERSION_V23,
        LEAN_RUNTIME_POLICY_VERSION_V24,
        LEAN_RUNTIME_POLICY_VERSION_V25,
        LEAN_RUNTIME_POLICY_VERSION_V26,
        LEAN_RUNTIME_POLICY_VERSION_V27,
        LEAN_RUNTIME_POLICY_VERSION_V28,
    }:
        raise ContractError("plan-gate recovery pins require Lean V21+")
    if len({pin.content_hash for pin in recovered_plan_gate_pins}) != len(recovered_plan_gate_pins):
        raise RecoveryError("plan-gate recovery pins repeat")
    runtime = dependencies.preregistration.runtime_contract
    if type(runtime) is not LeanRuntimeContract:
        raise TypeError("Lean request runtime contract differs")
    live_provider_request = provider_request_builder is not None
    if live_provider_request != (provider_input_token_counter is not None):
        raise ContractError("Lean provider request builder and counter must appear together")
    if not live_provider_request and live_input_count_method != LEAN_LIVE_COUNT_METHOD:
        raise ContractError("Lean mock request cannot select a live input-count method")
    if (
        not (
            model_id == runtime.model_id
            or (live_provider_request and model_id == "gpt-5.4-mini-2026-03-17")
        )
        or configured_max_output_tokens != runtime.configured_max_output_tokens
        or budget.token_budget_schema_version != "cumulative-split-v1"
        or budget.max_cumulative_input_tokens != runtime.max_cumulative_input_tokens
        or budget.max_cumulative_output_tokens != runtime.max_cumulative_output_tokens
        or budget.max_total_tokens != runtime.max_total_tokens
        or budget.max_model_calls != runtime.max_model_calls
        or budget.max_tool_calls != runtime.max_tool_calls
        or budget.wall_clock_timeout_seconds != runtime.wall_clock_timeout_seconds
    ):
        raise ContractError("Lean request runtime/budget tuple differs")
    if type(phase_evidence) is not EvidenceState:
        raise TypeError("Lean request requires exact phase evidence")
    if type(usage) is not Usage:
        raise TypeError("Lean request requires exact usage")
    if not isinstance(memory_delivery_evidence_sha256, str):
        raise TypeError("Lean request memory evidence hash differs")
    if (
        runtime_policy_version
        in {
            LEAN_RUNTIME_POLICY_VERSION_V8,
            LEAN_RUNTIME_POLICY_VERSION_V9,
            LEAN_RUNTIME_POLICY_VERSION_V10,
            LEAN_RUNTIME_POLICY_VERSION_V11,
            LEAN_RUNTIME_POLICY_VERSION_V12,
            LEAN_RUNTIME_POLICY_VERSION_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }
        and type(task) is not PublicTask
    ):
        raise TypeError("Lean V8+ request requires the exact public task")

    request_reasoning_effort: Literal["medium", "low"] = "medium"

    def build_request_body(
        context: str,
        tools: tuple[dict[str, Any], ...],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        if provider_request_builder is None:
            body = _request_body(
                model_id=model_id,
                system_prompt=system_prompt,
                context=context,
                tools=tools,
                max_output_tokens=max_output_tokens,
            )
        else:
            body = provider_request_builder(context, tools, max_output_tokens)
            if type(body) is not dict:
                raise ContractError("Lean provider request builder returned an invalid body")
            if runtime_policy_version in {
                LEAN_RUNTIME_POLICY_VERSION_V5,
                LEAN_RUNTIME_POLICY_VERSION_V6,
                LEAN_RUNTIME_POLICY_VERSION_V7,
                LEAN_RUNTIME_POLICY_VERSION_V8,
                LEAN_RUNTIME_POLICY_VERSION_V9,
                LEAN_RUNTIME_POLICY_VERSION_V10,
                LEAN_RUNTIME_POLICY_VERSION_V11,
                LEAN_RUNTIME_POLICY_VERSION_V12,
                LEAN_RUNTIME_POLICY_VERSION_V13,
                LEAN_RUNTIME_POLICY_VERSION_V14,
                LEAN_RUNTIME_POLICY_VERSION_V15,
                LEAN_RUNTIME_POLICY_VERSION_V16,
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }:
                reasoning = body.get("reasoning")
                if not isinstance(reasoning, dict):
                    raise ContractError("Lean V5+ provider request lacks reasoning controls")
                body["reasoning"] = {
                    **reasoning,
                    "effort": request_reasoning_effort,
                }
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V8,
            LEAN_RUNTIME_POLICY_VERSION_V9,
            LEAN_RUNTIME_POLICY_VERSION_V10,
            LEAN_RUNTIME_POLICY_VERSION_V11,
            LEAN_RUNTIME_POLICY_VERSION_V12,
            LEAN_RUNTIME_POLICY_VERSION_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            body["parallel_tool_calls"] = False
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            validate_provider_tool_schemas(body)
        return copy.deepcopy(body)

    def count_request_body(body: dict[str, Any]) -> int:
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            validate_provider_tool_schemas(body)
        if provider_input_token_counter is None:
            return len(canonical_json(body).encode("utf-8"))
        counted = provider_input_token_counter(copy.deepcopy(body))
        if type(counted) is not int or counted <= 0:
            raise ContractError("Lean provider input-token count is invalid")
        return counted

    compaction_projector = (
        project_lean_context_event_descriptors_v2
        if runtime_policy_version
        in {
            LEAN_RUNTIME_POLICY_VERSION_V6,
            LEAN_RUNTIME_POLICY_VERSION_V7,
            LEAN_RUNTIME_POLICY_VERSION_V8,
            LEAN_RUNTIME_POLICY_VERSION_V9,
            LEAN_RUNTIME_POLICY_VERSION_V10,
            LEAN_RUNTIME_POLICY_VERSION_V11,
            LEAN_RUNTIME_POLICY_VERSION_V12,
            LEAN_RUNTIME_POLICY_VERSION_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }
        else project_lean_context_event_descriptors
    )
    compacted = compaction_projector(built_context)
    normalized_compacted = compaction_projector(normalized_no_memory_context)
    feedback_projector = (
        project_lifecycle_plan_admission_feedback_v3
        if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V28
        else project_compact_plan_admission_feedback_v2
        if runtime_policy_version
        in {LEAN_RUNTIME_POLICY_VERSION_V26, LEAN_RUNTIME_POLICY_VERSION_V27}
        else project_compatible_bounded_plan_admission_feedback
        if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V25
        else project_bounded_plan_admission_feedback
    )
    plan_admission_feedback_projection = (
        feedback_projector(compacted)
        if runtime_policy_version
        in {
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }
        else None
    )
    normalized_plan_admission_feedback_projection = (
        feedback_projector(normalized_compacted)
        if runtime_policy_version
        in {
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }
        else None
    )
    generation_incomplete_recovery_state = (
        project_generation_incomplete_recovery(events)
        if runtime_policy_version
        in {
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }
        else None
    )
    phase_surface = project_phase_tool_surface(
        reserve=dependencies.reserve,
        tool_schemas=base_tool_schemas,
        phase_evidence=phase_evidence,
        mode="exploration",
    )
    saturation = project_saturation_recovery_admission_shadow(
        thresholds=dependencies.thresholds,
        events=events,
        phase_tool_surface=phase_surface,
        allow_non_mutation_surface=(
            runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V2,
                LEAN_RUNTIME_POLICY_VERSION_V3,
                LEAN_RUNTIME_POLICY_VERSION_V4,
                LEAN_RUNTIME_POLICY_VERSION_V5,
                LEAN_RUNTIME_POLICY_VERSION_V6,
                LEAN_RUNTIME_POLICY_VERSION_V7,
                LEAN_RUNTIME_POLICY_VERSION_V8,
                LEAN_RUNTIME_POLICY_VERSION_V9,
                LEAN_RUNTIME_POLICY_VERSION_V10,
                LEAN_RUNTIME_POLICY_VERSION_V11,
                LEAN_RUNTIME_POLICY_VERSION_V12,
                LEAN_RUNTIME_POLICY_VERSION_V13,
                LEAN_RUNTIME_POLICY_VERSION_V14,
                LEAN_RUNTIME_POLICY_VERSION_V15,
                LEAN_RUNTIME_POLICY_VERSION_V16,
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
        ),
        structured_edit_tool_schema=(
            STRUCTURED_EDIT_TOOL_SCHEMA_V2
            if runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V5,
                LEAN_RUNTIME_POLICY_VERSION_V6,
                LEAN_RUNTIME_POLICY_VERSION_V7,
                LEAN_RUNTIME_POLICY_VERSION_V8,
                LEAN_RUNTIME_POLICY_VERSION_V9,
                LEAN_RUNTIME_POLICY_VERSION_V10,
                LEAN_RUNTIME_POLICY_VERSION_V11,
                LEAN_RUNTIME_POLICY_VERSION_V12,
                LEAN_RUNTIME_POLICY_VERSION_V13,
                LEAN_RUNTIME_POLICY_VERSION_V14,
                LEAN_RUNTIME_POLICY_VERSION_V15,
                LEAN_RUNTIME_POLICY_VERSION_V16,
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
            else STRUCTURED_EDIT_TOOL_SCHEMA_V1
        ),
    )
    completion_loop_decision: CompletionLoopDecision | None = None
    workflow_decision: (
        WorkflowDecision | WorkflowDecisionV2 | WorkflowDecisionV3 | WorkflowDecisionV4 | None
    ) = None
    workflow_task_spec: PublicTaskSpec | None = None
    workflow_catalog: (
        EligiblePlanEvidenceCatalog
        | EligiblePlanEvidenceCatalogV2
        | EligiblePlanEvidenceCatalogV3
        | EligiblePlanEvidenceCatalogV4
        | None
    ) = None
    normalized_workflow_catalog: (
        EligiblePlanEvidenceCatalog
        | EligiblePlanEvidenceCatalogV2
        | EligiblePlanEvidenceCatalogV3
        | EligiblePlanEvidenceCatalogV4
        | None
    ) = None
    active_work_state: ActiveWorkState | None = None
    semantic_progress_state: PublicSemanticProgressState | None = None
    cross_reset_trigger: CrossResetFailureTrigger | None = None
    mutation_baseline_projection: MutationBaselineProjection | None = None
    mutation_baseline_restore_receipt: MutationBaselineRestoreReceipt | None = None
    causal_mechanism_history: (
        tuple[CausalMechanismHistoryEntry, ...] | tuple[CausalMechanismHistoryEntryV2, ...]
    ) = ()
    causal_plan_request_projection: ActivatedCausalPlanRequest | None = None
    normalized_causal_plan_request_projection: ActivatedCausalPlanRequest | None = None
    activated_exploration_plan_request: (
        ActivatedExplorationPlanRequest
        | PinnedExplorationPlanRequest
        | SelfDirectedPlanRequest
        | TriggerBoundSelfDirectedPlanRequest
        | LifecycleBoundPlanRequest
        | LifecycleComponentBoundPlanRequest
        | None
    ) = None
    normalized_activated_exploration_plan_request: (
        ActivatedExplorationPlanRequest
        | PinnedExplorationPlanRequest
        | SelfDirectedPlanRequest
        | TriggerBoundSelfDirectedPlanRequest
        | LifecycleBoundPlanRequest
        | LifecycleComponentBoundPlanRequest
        | None
    ) = None
    semantic_progress_event_domain: SemanticProgressEventDomain | None = None
    plan_gate_readiness_snapshot: (
        PlanGateReadinessSnapshot | SelfDirectedPlanGateSnapshot | None
    ) = None
    normalized_plan_gate_readiness_snapshot: (
        PlanGateReadinessSnapshot | SelfDirectedPlanGateSnapshot | None
    ) = None
    recovered_plan_gate_pin: (
        RecoveredPlanGateReadinessPin | RecoveredSelfDirectedPlanGatePin | None
    ) = None
    self_directed_exploration_state: SelfDirectedExplorationState | None = None
    normalized_self_directed_exploration_state: SelfDirectedExplorationState | None = None
    exact_pre_plan_surface_projection: ExactPrePlanSurfaceProjection | None = None
    normalized_exact_pre_plan_surface_projection: ExactPrePlanSurfaceProjection | None = None
    bounded_investigation_request_context: BoundedInvestigationRequestContext | None = None
    normalized_bounded_investigation_request_context: BoundedInvestigationRequestContext | None = (
        None
    )
    workflow_instruction_document: dict[str, Any] | None = None
    correction_context = None
    normalized_correction_context = None
    completion_loop_instruction: dict[str, Any] | None = None
    if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V8:
        assert task is not None
        successor_source_schemas = tuple(saturation.selected_tool_schemas)
        if STRUCTURED_EDIT_TOOL_NAME not in _tool_names(successor_source_schemas):
            successor_source_schemas = (
                *successor_source_schemas,
                copy.deepcopy(STRUCTURED_EDIT_TOOL_SCHEMA_V2),
            )
        completion_loop_decision = project_completion_loop_successor(
            task=task,
            evidence=phase_evidence,
            events=events,
            available_tool_names=_tool_names(successor_source_schemas),
            configured_max_output_tokens=configured_max_output_tokens,
        )
        exploration_surface = project_completion_tool_surface(
            decision=completion_loop_decision,
            source_tool_schemas=successor_source_schemas,
        )
        correction_context = project_current_edit_correction_context(compacted.rendered)
        normalized_correction_context = project_current_edit_correction_context(
            normalized_compacted.rendered
        )
        completion_loop_instruction = completion_instruction(completion_loop_decision)

        def ordered_context(source: str) -> str:
            try:
                payload = json.loads(source)
            except json.JSONDecodeError as exc:
                raise ContractError("Lean V8 completion context must be JSON") from exc
            if type(payload) is not dict:
                raise ContractError("Lean V8 completion context must be an object")
            payload["completion_loop"] = copy.deepcopy(completion_loop_instruction)
            return canonical_json(payload)

        request_context = ordered_context(correction_context.rendered)
        normalized_request_context = ordered_context(normalized_correction_context.rendered)
        request_reasoning_effort = completion_loop_decision.reasoning_effort
        exploratory_ceiling = completion_loop_decision.effective_max_output_tokens
    elif runtime_policy_version in {
        LEAN_RUNTIME_POLICY_VERSION_V9,
        LEAN_RUNTIME_POLICY_VERSION_V10,
    }:
        assert task is not None
        successor_source_schemas = tuple(copy.deepcopy(item) for item in base_tool_schemas)
        if STRUCTURED_EDIT_TOOL_NAME not in _tool_names(successor_source_schemas):
            successor_source_schemas = (
                *successor_source_schemas,
                copy.deepcopy(STRUCTURED_EDIT_TOOL_SCHEMA_V2),
            )
        workflow_decision = project_workflow_successor(
            runtime_policy_version=runtime_policy_version,
            task=task,
            evidence=phase_evidence,
            events=events,
            available_tool_names=_tool_names(successor_source_schemas),
            configured_max_output_tokens=configured_max_output_tokens,
        )
        if workflow_decision.target == "terminal":
            if workflow_decision.terminal_reason == "correction_attempt_limit":
                raise CorrectionAttemptLimitError(
                    "corrective mutation limit reached for the bound public check"
                )
            raise PreMutationEvidenceExhaustedError(
                "pre-mutation public evidence action limit was exhausted"
            )
        exploration_surface = project_workflow_tool_surface(
            decision=workflow_decision,
            source_tool_schemas=successor_source_schemas,
        )
        correction_context = project_current_edit_correction_context(compacted.rendered)
        normalized_correction_context = project_current_edit_correction_context(
            normalized_compacted.rendered
        )
        workflow_task_spec = (
            project_public_task_spec(task)
            if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V10
            else None
        )
        workflow_instruction_document = workflow_instruction(
            workflow_decision,
            task_spec=workflow_task_spec,
        )

        def workflow_context(source: str) -> str:
            try:
                payload = json.loads(source)
            except json.JSONDecodeError as exc:
                raise ContractError("Lean workflow context must be JSON") from exc
            if type(payload) is not dict:
                raise ContractError("Lean workflow context must be an object")
            payload["workflow"] = copy.deepcopy(workflow_instruction_document)
            return canonical_json(payload)

        request_context = workflow_context(correction_context.rendered)
        normalized_request_context = workflow_context(normalized_correction_context.rendered)
        request_reasoning_effort = workflow_decision.reasoning_effort
        exploratory_ceiling = workflow_decision.effective_max_output_tokens
    elif runtime_policy_version in {
        LEAN_RUNTIME_POLICY_VERSION_V11,
        LEAN_RUNTIME_POLICY_VERSION_V12,
        LEAN_RUNTIME_POLICY_VERSION_V13,
        LEAN_RUNTIME_POLICY_VERSION_V14,
        LEAN_RUNTIME_POLICY_VERSION_V15,
        LEAN_RUNTIME_POLICY_VERSION_V16,
        LEAN_RUNTIME_POLICY_VERSION_V17,
        LEAN_RUNTIME_POLICY_VERSION_V18,
        LEAN_RUNTIME_POLICY_VERSION_V19,
        LEAN_RUNTIME_POLICY_VERSION_V20,
        LEAN_RUNTIME_POLICY_VERSION_V21,
        LEAN_RUNTIME_POLICY_VERSION_V22,
        LEAN_RUNTIME_POLICY_VERSION_V23,
        LEAN_RUNTIME_POLICY_VERSION_V24,
        LEAN_RUNTIME_POLICY_VERSION_V25,
        LEAN_RUNTIME_POLICY_VERSION_V26,
        LEAN_RUNTIME_POLICY_VERSION_V27,
        LEAN_RUNTIME_POLICY_VERSION_V28,
    }:
        assert task is not None
        event_run_ids = {event.run_id for event in events}
        if len(event_run_ids) != 1:
            raise ContractError("Lean V11+ request requires one durable run identity")
        event_run_id = next(iter(event_run_ids))
        successor_source_schemas = tuple(copy.deepcopy(item) for item in base_tool_schemas)
        if STRUCTURED_EDIT_TOOL_NAME not in _tool_names(successor_source_schemas):
            successor_source_schemas = (
                *successor_source_schemas,
                copy.deepcopy(STRUCTURED_EDIT_TOOL_SCHEMA_V2),
            )
        correction_context = project_current_edit_correction_context(
            plan_admission_feedback_projection.rendered
            if plan_admission_feedback_projection is not None
            else compacted.rendered
        )
        normalized_correction_context = project_current_edit_correction_context(
            normalized_plan_admission_feedback_projection.rendered
            if normalized_plan_admission_feedback_projection is not None
            else normalized_compacted.rendered
        )
        workflow_source_context = correction_context.rendered
        normalized_workflow_source_context = normalized_correction_context.rendered
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            bounded_investigation_request_context = project_bounded_investigation_request_context(
                correction_context
            )
            normalized_bounded_investigation_request_context = (
                project_bounded_investigation_request_context(normalized_correction_context)
            )
            workflow_source_context = bounded_investigation_request_context.rendered
            normalized_workflow_source_context = (
                normalized_bounded_investigation_request_context.rendered
            )
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            cross_reset_trigger = project_active_cross_reset_trigger(
                run_id=event_run_id,
                current_diff_hash=phase_evidence.worktree_diff_hash,
                events=events,
            )
            causal_mechanism_history = (
                project_causal_mechanism_history_v2(
                    run_id=event_run_id,
                    events=events,
                )
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V18,
                    LEAN_RUNTIME_POLICY_VERSION_V19,
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else project_causal_mechanism_history(
                    run_id=event_run_id,
                    events=events,
                )
            )
        required_trigger_sequence = (
            required_failed_check_trigger_sequence(
                run_id=event_run_id,
                task=task,
                evidence=phase_evidence,
                events=events,
            )
            if runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V14,
                LEAN_RUNTIME_POLICY_VERSION_V15,
                LEAN_RUNTIME_POLICY_VERSION_V16,
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
            and cross_reset_trigger is None
            else None
        )
        catalog_projector = (
            project_eligible_plan_evidence_catalog_v2
            if runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V14,
                LEAN_RUNTIME_POLICY_VERSION_V15,
                LEAN_RUNTIME_POLICY_VERSION_V16,
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
            else project_eligible_plan_evidence_catalog
        )
        catalog_kwargs = (
            {"required_trigger_event_sequence": required_trigger_sequence}
            if runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V14,
                LEAN_RUNTIME_POLICY_VERSION_V15,
                LEAN_RUNTIME_POLICY_VERSION_V16,
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
            else {}
        )
        workflow_catalog = catalog_projector(
            run_id=event_run_id,
            task=task,
            worktree_diff_hash=phase_evidence.worktree_diff_hash,
            model_visible_context=workflow_source_context,
            events=events,
            **catalog_kwargs,
        )
        normalized_workflow_catalog = catalog_projector(
            run_id=event_run_id,
            task=task,
            worktree_diff_hash=phase_evidence.worktree_diff_hash,
            model_visible_context=normalized_workflow_source_context,
            events=events,
            **catalog_kwargs,
        )
        if (
            workflow_catalog.items != normalized_workflow_catalog.items
            or workflow_catalog.model_visible_recent_event_sequences
            != normalized_workflow_catalog.model_visible_recent_event_sequences
        ):
            raise ContractError("Lean V11+ normalized evidence projection differs")
        if isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2) and (
            not isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV2)
            or workflow_catalog.required_trigger_status
            != normalized_workflow_catalog.required_trigger_status
            or workflow_catalog.required_trigger_event_sequence
            != normalized_workflow_catalog.required_trigger_event_sequence
            or workflow_catalog.model_visible_pinned_event_sequences
            != normalized_workflow_catalog.model_visible_pinned_event_sequences
        ):
            raise ContractError("Lean V14+ normalized trigger projection differs")
        active_work_state = project_active_work_state(
            run_id=event_run_id,
            task=task,
            current_diff_hash=phase_evidence.worktree_diff_hash,
            events=events,
        )
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            try:
                if runtime_policy_version in {
                    LEAN_RUNTIME_POLICY_VERSION_V20,
                    LEAN_RUNTIME_POLICY_VERSION_V21,
                    LEAN_RUNTIME_POLICY_VERSION_V22,
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }:
                    semantic_progress_event_domain = project_semantic_progress_event_domain(
                        run_id=event_run_id,
                        events=events,
                    )
                    semantic_events = select_semantic_progress_epoch_events(
                        domain=semantic_progress_event_domain,
                        events=events,
                    )
                else:
                    semantic_events = (
                        cross_reset_epoch_events(events)
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V17,
                            LEAN_RUNTIME_POLICY_VERSION_V18,
                            LEAN_RUNTIME_POLICY_VERSION_V19,
                        }
                        else tuple(events)
                    )
                if cross_reset_trigger is not None:
                    semantic_progress_state = project_cross_reset_semantic_progress_state(
                        run_id=event_run_id,
                        trigger=cross_reset_trigger,
                        events=events,
                    )
                    restored_event = next(
                        event
                        for event in events
                        if event.sequence == cross_reset_trigger.restored_event_sequence
                    )
                    mutation_baseline_projection = MutationBaselineProjection.model_validate_json(
                        canonical_json(restored_event.payload.get("baseline_projection"))
                    )
                    mutation_baseline_restore_receipt = (
                        MutationBaselineRestoreReceipt.model_validate_json(
                            canonical_json(restored_event.payload.get("restore_receipt"))
                        )
                    )
                else:
                    current_failure_sequence = current_public_failure_event_sequence(
                        run_id=event_run_id,
                        task=task,
                        evidence=phase_evidence,
                        events=semantic_events,
                    )
                    semantic_progress_state = project_public_semantic_progress_state(
                        run_id=event_run_id,
                        task=task,
                        evidence=phase_evidence,
                        events=semantic_events,
                        current_failure_event_sequence=current_failure_sequence,
                    )
            except (ContractError, ValueError) as exc:
                raise SemanticProgressEvidenceUnavailableError(
                    "current public failure signature could not be reconstructed"
                ) from exc
            if not isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2):
                raise ContractError("Lean V15 requires the pinned evidence catalog")
            workflow_decision = project_workflow_semantic_progress_successor(
                run_id=event_run_id,
                task=task,
                evidence=phase_evidence,
                events=(events if cross_reset_trigger is not None else semantic_events),
                work_plan_events=(
                    events
                    if runtime_policy_version
                    in {
                        LEAN_RUNTIME_POLICY_VERSION_V17,
                        LEAN_RUNTIME_POLICY_VERSION_V18,
                        LEAN_RUNTIME_POLICY_VERSION_V19,
                        LEAN_RUNTIME_POLICY_VERSION_V20,
                        LEAN_RUNTIME_POLICY_VERSION_V21,
                        LEAN_RUNTIME_POLICY_VERSION_V22,
                        LEAN_RUNTIME_POLICY_VERSION_V23,
                        LEAN_RUNTIME_POLICY_VERSION_V24,
                        LEAN_RUNTIME_POLICY_VERSION_V25,
                        LEAN_RUNTIME_POLICY_VERSION_V26,
                        LEAN_RUNTIME_POLICY_VERSION_V27,
                        LEAN_RUNTIME_POLICY_VERSION_V28,
                    }
                    else None
                ),
                catalog=workflow_catalog,
                semantic_progress_state=(
                    None if cross_reset_trigger is not None else semantic_progress_state
                ),
                active_work_state=active_work_state,
                available_tool_names=_tool_names(successor_source_schemas),
                configured_max_output_tokens=configured_max_output_tokens,
            )
            if cross_reset_trigger is not None:
                accepted = [
                    event.payload.get("plan_hash")
                    for event in events
                    if event.sequence > cross_reset_trigger.restored_event_sequence
                    and event.type == EventType.CAUSAL_MECHANISM_RECORDED
                    and isinstance(event.payload.get("binding"), dict)
                    and event.payload["binding"].get("cross_reset_failure_trigger_hash")
                    == cross_reset_trigger.content_hash
                    and isinstance(event.payload.get("plan_hash"), str)
                ]
                if len(set(accepted)) > 1:
                    raise ContractError("cross-reset accepted causal plan repeats")
                try:
                    workflow_decision = (
                        project_causal_reset_decision_v2(
                            base_decision=workflow_decision,
                            semantic_progress_state=semantic_progress_state,
                            trigger=cross_reset_trigger,
                            history=causal_mechanism_history,
                            events=events,
                            accepted_plan_hash=accepted[-1] if accepted else None,
                        )
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V18,
                            LEAN_RUNTIME_POLICY_VERSION_V19,
                            LEAN_RUNTIME_POLICY_VERSION_V20,
                            LEAN_RUNTIME_POLICY_VERSION_V21,
                            LEAN_RUNTIME_POLICY_VERSION_V22,
                            LEAN_RUNTIME_POLICY_VERSION_V23,
                            LEAN_RUNTIME_POLICY_VERSION_V24,
                            LEAN_RUNTIME_POLICY_VERSION_V25,
                            LEAN_RUNTIME_POLICY_VERSION_V26,
                            LEAN_RUNTIME_POLICY_VERSION_V27,
                            LEAN_RUNTIME_POLICY_VERSION_V28,
                        }
                        else project_causal_reset_decision(
                            base_decision=workflow_decision,
                            semantic_progress_state=semantic_progress_state,
                            trigger=cross_reset_trigger,
                            history=causal_mechanism_history,
                            events=events,
                            accepted_plan_hash=accepted[-1] if accepted else None,
                        )
                    )
                except ContractError as exc:
                    reason_codes = exc.details.get("reason_codes", [])
                    if "causal_alternative_admission_repeated" in reason_codes:
                        raise WorkPlanAdmissionRepeatedError(
                            "causal alternative admission failed twice for the same gate"
                        ) from exc
                    if "causal_alternative_evidence_exhausted" in reason_codes:
                        raise SemanticNoProgressEvidenceExhaustedError(
                            "causal alternative evidence acquisition was exhausted"
                        ) from exc
                    raise
        else:
            workflow_decision = project_workflow_successor_v2(
                runtime_policy_version=runtime_policy_version,
                run_id=event_run_id,
                task=task,
                evidence=phase_evidence,
                events=events,
                catalog=workflow_catalog,
                available_tool_names=_tool_names(successor_source_schemas),
                configured_max_output_tokens=configured_max_output_tokens,
            )
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
        }:
            if not (
                isinstance(workflow_decision, WorkflowDecisionV3)
                and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2)
                and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV2)
            ):
                raise ContractError("Lean V19 exploration readiness state differs")
            base_exploration_decision = workflow_decision
            workflow_decision = project_exploration_readiness_decision(
                task=task,
                decision=base_exploration_decision,
                catalog=workflow_catalog,
                source_tool_schemas=successor_source_schemas,
                cross_reset_trigger=cross_reset_trigger,
            )
            normalized_exploration_decision = project_exploration_readiness_decision(
                task=task,
                decision=base_exploration_decision,
                catalog=normalized_workflow_catalog,
                source_tool_schemas=successor_source_schemas,
                cross_reset_trigger=cross_reset_trigger,
            )
            if workflow_decision != normalized_exploration_decision:
                raise ContractError("Lean V19 normalized exploration readiness differs")
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
        }:
            if not (
                isinstance(workflow_decision, WorkflowDecisionV3)
                and isinstance(normalized_exploration_decision, WorkflowDecisionV3)
                and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2)
                and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV2)
            ):
                raise ContractError("Lean V21 plan-gate base state differs")
            matching_pins = tuple(
                pin
                for pin in recovered_plan_gate_pins
                if pin.snapshot.run_id == event_run_id
                and pin.snapshot.worktree_diff_hash == phase_evidence.worktree_diff_hash
                and pin.snapshot.plan_gate_id == workflow_decision.plan_gate_id
            )
            if len(matching_pins) > 1:
                raise RecoveryError("Lean V21 plan-gate pin repeats")
            recovered_plan_gate_pin = matching_pins[0] if matching_pins else None
            workflow_catalog = project_pinned_evidence_catalog(
                base=workflow_catalog,
                pin=recovered_plan_gate_pin,
            )
            normalized_workflow_catalog = project_pinned_evidence_catalog(
                base=normalized_workflow_catalog,
                pin=recovered_plan_gate_pin,
            )
            plan_gate_readiness_snapshot = (
                recovered_plan_gate_pin.snapshot
                if recovered_plan_gate_pin is not None
                else project_plan_gate_readiness_snapshot(
                    task=task,
                    decision=workflow_decision,
                    catalog=workflow_catalog,
                )
            )
            normalized_plan_gate_readiness_snapshot = (
                recovered_plan_gate_pin.snapshot
                if recovered_plan_gate_pin is not None
                else project_plan_gate_readiness_snapshot(
                    task=task,
                    decision=normalized_exploration_decision,
                    catalog=normalized_workflow_catalog,
                )
            )
            workflow_decision = project_pinned_plan_gate_decision(
                decision=workflow_decision,
                readiness=plan_gate_readiness_snapshot,
                pin=recovered_plan_gate_pin,
            )
            normalized_exploration_decision = project_pinned_plan_gate_decision(
                decision=normalized_exploration_decision,
                readiness=normalized_plan_gate_readiness_snapshot,
                pin=recovered_plan_gate_pin,
            )
            if workflow_decision != normalized_exploration_decision:
                raise ContractError("Lean V21 normalized plan-gate decision differs")
        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            if not (
                isinstance(workflow_decision, WorkflowDecisionV3)
                and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2)
                and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV2)
            ):
                raise ContractError("Lean V23 self-directed base state differs")
            base_self_directed_decision = workflow_decision
            matching_pins = tuple(
                pin
                for pin in recovered_plan_gate_pins
                if isinstance(pin, RecoveredSelfDirectedPlanGatePin)
                and pin.snapshot.run_id == event_run_id
                and pin.snapshot.worktree_diff_hash == phase_evidence.worktree_diff_hash
                and pin.snapshot.plan_gate_id == workflow_decision.plan_gate_id
            )
            if len(matching_pins) > 1:
                raise RecoveryError("Lean V23 plan-gate pin repeats")
            recovered_plan_gate_pin = matching_pins[0] if matching_pins else None
            workflow_catalog = project_self_directed_evidence_catalog(
                base=workflow_catalog,
                pin=recovered_plan_gate_pin,
            )
            normalized_workflow_catalog = project_self_directed_evidence_catalog(
                base=normalized_workflow_catalog,
                pin=recovered_plan_gate_pin,
            )
            self_directed_exploration_state = project_self_directed_exploration_state(
                task=task,
                decision=base_self_directed_decision,
                catalog=workflow_catalog,
                events=events,
                active_work_state=active_work_state,
            )
            normalized_self_directed_exploration_state = project_self_directed_exploration_state(
                task=task,
                decision=base_self_directed_decision,
                catalog=normalized_workflow_catalog,
                events=events,
                active_work_state=active_work_state,
            )
            self_directed_decision_projector = (
                project_trigger_bound_self_directed_workflow_decision
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else project_self_directed_workflow_decision
            )
            workflow_decision = self_directed_decision_projector(
                base_decision=base_self_directed_decision,
                state=self_directed_exploration_state,
                source_tool_schemas=successor_source_schemas,
                events=events,
            )
            normalized_exploration_decision = self_directed_decision_projector(
                base_decision=base_self_directed_decision,
                state=normalized_self_directed_exploration_state,
                source_tool_schemas=successor_source_schemas,
                events=events,
            )
            if (
                workflow_decision != normalized_exploration_decision
                or self_directed_exploration_state != normalized_self_directed_exploration_state
            ):
                raise ContractError("Lean V23 normalized self-directed state differs")
            if runtime_policy_version in {
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }:
                exact_pre_plan_surface_projection = project_exact_pre_plan_surface(
                    source_decision=workflow_decision,
                    state=self_directed_exploration_state,
                )
                normalized_exact_pre_plan_surface_projection = project_exact_pre_plan_surface(
                    source_decision=normalized_exploration_decision,
                    state=normalized_self_directed_exploration_state,
                )
                if (
                    exact_pre_plan_surface_projection.evidence
                    != normalized_exact_pre_plan_surface_projection.evidence
                ):
                    raise ContractError("Lean V24 normalized pre-plan surface differs")
                workflow_decision = exact_pre_plan_surface_projection.decision
                normalized_exploration_decision = (
                    normalized_exact_pre_plan_surface_projection.decision
                )
            if workflow_decision.self_directed_exploration_state_hash is None:
                self_directed_exploration_state = None
                normalized_self_directed_exploration_state = None
            plan_gate_readiness_snapshot = (
                recovered_plan_gate_pin.snapshot
                if recovered_plan_gate_pin is not None
                else project_self_directed_plan_gate_snapshot(
                    task=task,
                    decision=workflow_decision,
                    catalog=workflow_catalog,
                )
            )
            normalized_plan_gate_readiness_snapshot = (
                recovered_plan_gate_pin.snapshot
                if recovered_plan_gate_pin is not None
                else project_self_directed_plan_gate_snapshot(
                    task=task,
                    decision=normalized_exploration_decision,
                    catalog=normalized_workflow_catalog,
                )
            )
            if plan_gate_readiness_snapshot != normalized_plan_gate_readiness_snapshot:
                raise ContractError("Lean V23 normalized plan-gate snapshot differs")
        if workflow_decision.target == "terminal":
            if workflow_decision.terminal_reason == "correction_attempt_limit":
                raise CorrectionAttemptLimitError(
                    "corrective mutation limit reached for the bound public check"
                )
            if workflow_decision.terminal_reason == "work_plan_admission_repeated":
                raise WorkPlanAdmissionRepeatedError(
                    "work-plan admission failed twice for the same durable gate"
                )
            if workflow_decision.terminal_reason == ("required_workflow_evidence_unavailable"):
                raise RequiredWorkflowEvidenceUnavailableError(
                    "required public failed-check evidence could not be reconstructed"
                )
            if workflow_decision.terminal_reason == "semantic_no_progress_evidence_exhausted":
                raise SemanticNoProgressEvidenceExhaustedError(
                    "semantic reset exhausted its required public search/read evidence"
                )
            if workflow_decision.terminal_reason == "semantic_no_progress_revision_invalid":
                raise SemanticNoProgressRevisionInvalidError(
                    "semantic reset revision did not reject the prior hypothesis"
                )
            if workflow_decision.terminal_reason == "self_directed_exploration_exhausted":
                raise SelfDirectedExplorationExhaustedError(
                    "bounded public exploration ended without a safe plan"
                )
            raise PreMutationEvidenceExhaustedError(
                "pre-mutation public evidence action limit was exhausted"
            )
        if (
            runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
            and isinstance(workflow_decision, WorkflowDecisionV4)
            and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV4)
            and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV4)
        ):
            self_directed_surface_projector = (
                project_lifecycle_component_bound_tool_surface
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V28
                else project_lifecycle_bound_tool_surface
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V26, LEAN_RUNTIME_POLICY_VERSION_V27}
                else project_trigger_bound_self_directed_tool_surface
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V25
                else project_self_directed_tool_surface
            )
            exploration_surface, activated_exploration_plan_request = (
                self_directed_surface_projector(
                    task=task,
                    decision=workflow_decision,
                    catalog=workflow_catalog,
                    state=self_directed_exploration_state,
                    source_tool_schemas=successor_source_schemas,
                    cross_reset_trigger=cross_reset_trigger,
                )
            )
            _, normalized_activated_exploration_plan_request = self_directed_surface_projector(
                task=task,
                decision=normalized_exploration_decision,
                catalog=normalized_workflow_catalog,
                state=normalized_self_directed_exploration_state,
                source_tool_schemas=successor_source_schemas,
                cross_reset_trigger=cross_reset_trigger,
            )
            causal_plan_request_projection = (
                activated_exploration_plan_request.source_request.source_request.base_request
                if isinstance(
                    activated_exploration_plan_request,
                    (LifecycleBoundPlanRequest, LifecycleComponentBoundPlanRequest),
                )
                else activated_exploration_plan_request.source_request.base_request
                if activated_exploration_plan_request is not None
                else None
            )
            normalized_causal_plan_request_projection = (
                normalized_activated_exploration_plan_request.source_request.source_request.base_request
                if isinstance(
                    normalized_activated_exploration_plan_request,
                    (LifecycleBoundPlanRequest, LifecycleComponentBoundPlanRequest),
                )
                else normalized_activated_exploration_plan_request.source_request.base_request
                if normalized_activated_exploration_plan_request is not None
                else None
            )
        elif (
            runtime_policy_version
            in {LEAN_RUNTIME_POLICY_VERSION_V21, LEAN_RUNTIME_POLICY_VERSION_V22}
            and isinstance(workflow_decision, WorkflowDecisionV3)
            and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV3)
            and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV3)
        ):
            exploration_surface, activated_exploration_plan_request = (
                project_pinned_plan_gate_tool_surface(
                    task=task,
                    decision=workflow_decision,
                    catalog=workflow_catalog,
                    source_tool_schemas=successor_source_schemas,
                    cross_reset_trigger=cross_reset_trigger,
                )
            )
            _, normalized_activated_exploration_plan_request = (
                project_pinned_plan_gate_tool_surface(
                    task=task,
                    decision=workflow_decision,
                    catalog=normalized_workflow_catalog,
                    source_tool_schemas=successor_source_schemas,
                    cross_reset_trigger=cross_reset_trigger,
                )
            )
            causal_plan_request_projection = (
                activated_exploration_plan_request.source_request.base_request
                if activated_exploration_plan_request is not None
                else None
            )
            normalized_causal_plan_request_projection = (
                normalized_activated_exploration_plan_request.source_request.base_request
                if normalized_activated_exploration_plan_request is not None
                else None
            )
        elif (
            runtime_policy_version
            in {LEAN_RUNTIME_POLICY_VERSION_V19, LEAN_RUNTIME_POLICY_VERSION_V20}
            and isinstance(workflow_decision, WorkflowDecisionV3)
            and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2)
            and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV2)
        ):
            exploration_surface, activated_exploration_plan_request = (
                project_exploration_workflow_tool_surface(
                    task=task,
                    decision=workflow_decision,
                    catalog=workflow_catalog,
                    source_tool_schemas=successor_source_schemas,
                    cross_reset_trigger=cross_reset_trigger,
                )
            )
            _, normalized_activated_exploration_plan_request = (
                project_exploration_workflow_tool_surface(
                    task=task,
                    decision=workflow_decision,
                    catalog=normalized_workflow_catalog,
                    source_tool_schemas=successor_source_schemas,
                    cross_reset_trigger=cross_reset_trigger,
                )
            )
            causal_plan_request_projection = (
                activated_exploration_plan_request.source_request.base_request
                if activated_exploration_plan_request is not None
                else None
            )
            normalized_causal_plan_request_projection = (
                normalized_activated_exploration_plan_request.source_request.base_request
                if normalized_activated_exploration_plan_request is not None
                else None
            )
        elif (
            runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V18
            and isinstance(workflow_decision, WorkflowDecisionV3)
            and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2)
            and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV2)
        ):
            exploration_surface, causal_plan_request_projection = (
                project_causal_plan_workflow_tool_surface_v2(
                    task=task,
                    decision=workflow_decision,
                    catalog=workflow_catalog,
                    source_tool_schemas=successor_source_schemas,
                    cross_reset_trigger=cross_reset_trigger,
                )
            )
            _, normalized_causal_plan_request_projection = (
                project_causal_plan_workflow_tool_surface_v2(
                    task=task,
                    decision=workflow_decision,
                    catalog=normalized_workflow_catalog,
                    source_tool_schemas=successor_source_schemas,
                    cross_reset_trigger=cross_reset_trigger,
                )
            )
        elif (
            runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V17
            and isinstance(workflow_decision, WorkflowDecisionV3)
            and isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2)
        ):
            exploration_surface = project_causal_workflow_tool_surface(
                decision=workflow_decision,
                catalog=workflow_catalog,
                source_tool_schemas=successor_source_schemas,
                trigger=cross_reset_trigger,
                history=causal_mechanism_history,
            )
        elif isinstance(workflow_decision, WorkflowDecisionV3) and isinstance(
            workflow_catalog, EligiblePlanEvidenceCatalogV2
        ):
            exploration_surface = project_workflow_tool_surface_v3(
                decision=workflow_decision,
                catalog=workflow_catalog,
                source_tool_schemas=successor_source_schemas,
            )
        else:
            exploration_surface = project_workflow_tool_surface_v2(
                decision=workflow_decision,
                catalog=workflow_catalog,
                source_tool_schemas=successor_source_schemas,
            )
        workflow_task_spec = project_public_task_spec(task)
        if isinstance(workflow_decision, WorkflowDecisionV3):
            if not (
                isinstance(workflow_catalog, EligiblePlanEvidenceCatalogV2)
                and isinstance(normalized_workflow_catalog, EligiblePlanEvidenceCatalogV2)
            ):
                raise ContractError("Lean V15 instruction requires pinned evidence catalogs")
            instruction_projector = (
                lifecycle_component_workflow_instruction
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V28
                else lifecycle_workflow_instruction
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V26, LEAN_RUNTIME_POLICY_VERSION_V27}
                else workflow_instruction_v8
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else workflow_instruction_v7
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V21, LEAN_RUNTIME_POLICY_VERSION_V22}
                else workflow_instruction_v6
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V19, LEAN_RUNTIME_POLICY_VERSION_V20}
                else workflow_instruction_v5
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V18
                else workflow_instruction_v4
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V17
                else workflow_instruction_v3
            )
            instruction_kwargs = (
                {
                    "cross_reset_trigger": cross_reset_trigger,
                    "history": causal_mechanism_history,
                    "request_projection": activated_exploration_plan_request,
                    "readiness": plan_gate_readiness_snapshot,
                    "recovered_pin": recovered_plan_gate_pin,
                    "self_directed_state": self_directed_exploration_state,
                }
                if runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V23,
                    LEAN_RUNTIME_POLICY_VERSION_V24,
                    LEAN_RUNTIME_POLICY_VERSION_V25,
                    LEAN_RUNTIME_POLICY_VERSION_V26,
                    LEAN_RUNTIME_POLICY_VERSION_V27,
                    LEAN_RUNTIME_POLICY_VERSION_V28,
                }
                else {
                    "cross_reset_trigger": cross_reset_trigger,
                    "history": causal_mechanism_history,
                    "request_projection": activated_exploration_plan_request,
                    "readiness": plan_gate_readiness_snapshot,
                    "recovered_pin": recovered_plan_gate_pin,
                }
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V21, LEAN_RUNTIME_POLICY_VERSION_V22}
                else {
                    "cross_reset_trigger": cross_reset_trigger,
                    "history": causal_mechanism_history,
                    "request_projection": activated_exploration_plan_request,
                }
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V19, LEAN_RUNTIME_POLICY_VERSION_V20}
                else {
                    "cross_reset_trigger": cross_reset_trigger,
                    "history": causal_mechanism_history,
                    "request_projection": causal_plan_request_projection,
                }
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V18
                else {
                    "trigger": cross_reset_trigger,
                    "history": causal_mechanism_history,
                }
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V17
                else {}
            )
            workflow_instruction_document = instruction_projector(
                workflow_decision,
                public_task_spec=workflow_task_spec.model_dump(mode="json"),
                catalog=workflow_catalog,
                active_work_state=active_work_state,
                semantic_progress_state=semantic_progress_state,
                **instruction_kwargs,
            )
            normalized_instruction_document = instruction_projector(
                workflow_decision,
                public_task_spec=workflow_task_spec.model_dump(mode="json"),
                catalog=normalized_workflow_catalog,
                active_work_state=active_work_state,
                semantic_progress_state=semantic_progress_state,
                **(
                    {
                        **instruction_kwargs,
                        "request_projection": normalized_activated_exploration_plan_request,
                        "readiness": normalized_plan_gate_readiness_snapshot,
                        "self_directed_state": (normalized_self_directed_exploration_state),
                    }
                    if runtime_policy_version
                    in {
                        LEAN_RUNTIME_POLICY_VERSION_V23,
                        LEAN_RUNTIME_POLICY_VERSION_V24,
                        LEAN_RUNTIME_POLICY_VERSION_V25,
                        LEAN_RUNTIME_POLICY_VERSION_V26,
                        LEAN_RUNTIME_POLICY_VERSION_V27,
                        LEAN_RUNTIME_POLICY_VERSION_V28,
                    }
                    else {
                        **instruction_kwargs,
                        "request_projection": normalized_activated_exploration_plan_request,
                        "readiness": normalized_plan_gate_readiness_snapshot,
                    }
                    if runtime_policy_version
                    in {LEAN_RUNTIME_POLICY_VERSION_V21, LEAN_RUNTIME_POLICY_VERSION_V22}
                    else {
                        **instruction_kwargs,
                        "request_projection": normalized_activated_exploration_plan_request,
                    }
                    if runtime_policy_version
                    in {LEAN_RUNTIME_POLICY_VERSION_V19, LEAN_RUNTIME_POLICY_VERSION_V20}
                    else {
                        **instruction_kwargs,
                        "request_projection": normalized_causal_plan_request_projection,
                    }
                    if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V18
                    else instruction_kwargs
                ),
            )
            if runtime_policy_version in {
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }:
                if not (
                    exact_pre_plan_surface_projection is not None
                    and normalized_exact_pre_plan_surface_projection is not None
                    and bounded_investigation_request_context is not None
                    and normalized_bounded_investigation_request_context is not None
                ):
                    raise ContractError("Lean V24+ request projections are incomplete")
                workflow_instruction_document = bind_bounded_request_instruction(
                    workflow_instruction_document,
                    surface=exact_pre_plan_surface_projection.evidence,
                    context=bounded_investigation_request_context.evidence,
                )
                normalized_instruction_document = bind_bounded_request_instruction(
                    normalized_instruction_document,
                    surface=normalized_exact_pre_plan_surface_projection.evidence,
                    context=normalized_bounded_investigation_request_context.evidence,
                )
                successor_bindings.update(
                    {
                        "exact_pre_plan_surface_projection": (
                            exact_pre_plan_surface_projection.evidence.model_dump(mode="python")
                        ),
                        "exact_pre_plan_surface_projection_hash": (
                            exact_pre_plan_surface_projection.evidence.content_hash
                        ),
                        "bounded_investigation_request_context": (
                            bounded_investigation_request_context.evidence.model_dump(mode="python")
                        ),
                        "bounded_investigation_request_context_hash": (
                            bounded_investigation_request_context.evidence.content_hash
                        ),
                        "normalized_bounded_investigation_request_context_hash": (
                            normalized_bounded_investigation_request_context.evidence.content_hash
                        ),
                    }
                )
            successor_bindings.update(
                {
                    "semantic_progress_state": (
                        semantic_progress_state.model_dump(mode="python")
                        if semantic_progress_state is not None
                        else None
                    ),
                    "semantic_progress_state_hash": (
                        semantic_progress_state.content_hash
                        if semantic_progress_state is not None
                        else sha256_json(None)
                    ),
                    **(
                        {
                            "cross_reset_failure_trigger": (
                                cross_reset_trigger.model_dump(mode="python")
                                if cross_reset_trigger is not None
                                else None
                            ),
                            "cross_reset_failure_trigger_hash": (
                                cross_reset_trigger.content_hash
                                if cross_reset_trigger is not None
                                else sha256_json(None)
                            ),
                            "mutation_baseline_projection": (
                                mutation_baseline_projection.model_dump(mode="python")
                                if mutation_baseline_projection is not None
                                else None
                            ),
                            "mutation_baseline_restore_receipt": (
                                mutation_baseline_restore_receipt.model_dump(mode="python")
                                if mutation_baseline_restore_receipt is not None
                                else None
                            ),
                            "causal_mechanism_history": tuple(
                                item.model_dump(mode="python") for item in causal_mechanism_history
                            ),
                            "causal_mechanism_history_hash": sha256_json(
                                [item.model_dump(mode="json") for item in causal_mechanism_history]
                            ),
                        }
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V17,
                            LEAN_RUNTIME_POLICY_VERSION_V18,
                            LEAN_RUNTIME_POLICY_VERSION_V19,
                            LEAN_RUNTIME_POLICY_VERSION_V20,
                            LEAN_RUNTIME_POLICY_VERSION_V21,
                            LEAN_RUNTIME_POLICY_VERSION_V22,
                            LEAN_RUNTIME_POLICY_VERSION_V23,
                            LEAN_RUNTIME_POLICY_VERSION_V24,
                            LEAN_RUNTIME_POLICY_VERSION_V25,
                            LEAN_RUNTIME_POLICY_VERSION_V26,
                            LEAN_RUNTIME_POLICY_VERSION_V27,
                            LEAN_RUNTIME_POLICY_VERSION_V28,
                        }
                        else {}
                    ),
                    **(
                        {
                            "causal_plan_request_projection": (
                                causal_plan_request_projection.model_dump(mode="python")
                                if causal_plan_request_projection is not None
                                else None
                            ),
                            "causal_plan_request_projection_hash": (
                                causal_plan_request_projection.content_hash
                                if causal_plan_request_projection is not None
                                else sha256_json(None)
                            ),
                        }
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V18,
                            LEAN_RUNTIME_POLICY_VERSION_V19,
                            LEAN_RUNTIME_POLICY_VERSION_V20,
                            LEAN_RUNTIME_POLICY_VERSION_V21,
                            LEAN_RUNTIME_POLICY_VERSION_V22,
                            LEAN_RUNTIME_POLICY_VERSION_V23,
                            LEAN_RUNTIME_POLICY_VERSION_V24,
                            LEAN_RUNTIME_POLICY_VERSION_V25,
                            LEAN_RUNTIME_POLICY_VERSION_V26,
                            LEAN_RUNTIME_POLICY_VERSION_V27,
                            LEAN_RUNTIME_POLICY_VERSION_V28,
                        }
                        else {}
                    ),
                    **(
                        {
                            "activated_exploration_plan_request": (
                                activated_exploration_plan_request.model_dump(mode="python")
                                if activated_exploration_plan_request is not None
                                else None
                            ),
                            "activated_exploration_plan_request_hash": (
                                activated_exploration_plan_request.content_hash
                                if activated_exploration_plan_request is not None
                                else sha256_json(None)
                            ),
                        }
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V19,
                            LEAN_RUNTIME_POLICY_VERSION_V20,
                            LEAN_RUNTIME_POLICY_VERSION_V21,
                            LEAN_RUNTIME_POLICY_VERSION_V22,
                            LEAN_RUNTIME_POLICY_VERSION_V23,
                            LEAN_RUNTIME_POLICY_VERSION_V24,
                            LEAN_RUNTIME_POLICY_VERSION_V25,
                            LEAN_RUNTIME_POLICY_VERSION_V26,
                            LEAN_RUNTIME_POLICY_VERSION_V27,
                            LEAN_RUNTIME_POLICY_VERSION_V28,
                        }
                        else {}
                    ),
                    **(
                        {
                            "semantic_progress_event_domain": (
                                semantic_progress_event_domain.model_dump(mode="python")
                            ),
                            "semantic_progress_event_domain_hash": (
                                semantic_progress_event_domain.content_hash
                            ),
                        }
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V20,
                            LEAN_RUNTIME_POLICY_VERSION_V21,
                            LEAN_RUNTIME_POLICY_VERSION_V22,
                            LEAN_RUNTIME_POLICY_VERSION_V23,
                            LEAN_RUNTIME_POLICY_VERSION_V24,
                            LEAN_RUNTIME_POLICY_VERSION_V25,
                            LEAN_RUNTIME_POLICY_VERSION_V26,
                            LEAN_RUNTIME_POLICY_VERSION_V27,
                            LEAN_RUNTIME_POLICY_VERSION_V28,
                        }
                        and semantic_progress_event_domain is not None
                        else {}
                    ),
                    **(
                        {
                            "plan_gate_readiness_source": (
                                "recovered_pin"
                                if recovered_plan_gate_pin is not None
                                else "current_request"
                                if plan_gate_readiness_snapshot is not None
                                else "not_ready"
                            ),
                            "plan_gate_readiness_snapshot": (
                                plan_gate_readiness_snapshot.model_dump(mode="python")
                                if plan_gate_readiness_snapshot is not None
                                else None
                            ),
                            "plan_gate_readiness_snapshot_hash": (
                                plan_gate_readiness_snapshot.content_hash
                                if plan_gate_readiness_snapshot is not None
                                else sha256_json(None)
                            ),
                            "recovered_plan_gate_pin": (
                                recovered_plan_gate_pin.model_dump(mode="python")
                                if recovered_plan_gate_pin is not None
                                else None
                            ),
                            "recovered_plan_gate_pin_hash": (
                                recovered_plan_gate_pin.content_hash
                                if recovered_plan_gate_pin is not None
                                else sha256_json(None)
                            ),
                        }
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V21,
                            LEAN_RUNTIME_POLICY_VERSION_V22,
                            LEAN_RUNTIME_POLICY_VERSION_V23,
                            LEAN_RUNTIME_POLICY_VERSION_V24,
                            LEAN_RUNTIME_POLICY_VERSION_V25,
                            LEAN_RUNTIME_POLICY_VERSION_V26,
                            LEAN_RUNTIME_POLICY_VERSION_V27,
                            LEAN_RUNTIME_POLICY_VERSION_V28,
                        }
                        else {}
                    ),
                    **(
                        {
                            "self_directed_exploration_state": (
                                self_directed_exploration_state.model_dump(mode="python")
                                if self_directed_exploration_state is not None
                                else None
                            ),
                            "self_directed_exploration_state_hash": (
                                self_directed_exploration_state.content_hash
                                if self_directed_exploration_state is not None
                                else sha256_json(None)
                            ),
                        }
                        if runtime_policy_version
                        in {
                            LEAN_RUNTIME_POLICY_VERSION_V23,
                            LEAN_RUNTIME_POLICY_VERSION_V24,
                            LEAN_RUNTIME_POLICY_VERSION_V25,
                            LEAN_RUNTIME_POLICY_VERSION_V26,
                            LEAN_RUNTIME_POLICY_VERSION_V27,
                            LEAN_RUNTIME_POLICY_VERSION_V28,
                        }
                        else {}
                    ),
                }
            )
        else:
            workflow_instruction_document = workflow_instruction_v2(
                workflow_decision,
                public_task_spec=workflow_task_spec.model_dump(mode="json"),
                catalog=workflow_catalog,
                active_work_state=active_work_state,
            )
            normalized_instruction_document = workflow_instruction_v2(
                workflow_decision,
                public_task_spec=workflow_task_spec.model_dump(mode="json"),
                catalog=normalized_workflow_catalog,
                active_work_state=active_work_state,
            )

        if runtime_policy_version in {
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }:
            if generation_incomplete_recovery_state is None:
                raise ContractError("Lean V26 generation recovery state is missing")

            def bind_generation_recovery(instruction: dict[str, Any]) -> dict[str, Any]:
                body = {
                    **{
                        key: copy.deepcopy(value)
                        for key, value in instruction.items()
                        if key != "content_hash"
                    },
                    "generation_incomplete_recovery": {
                        **generation_incomplete_recovery_state.model_dump(mode="python"),
                        "instruction": (
                            "The prior response exhausted its turn on reasoning. Emit "
                            "exactly one available tool call now, using the pinned public "
                            "work state."
                            if generation_incomplete_recovery_state.used
                            else "One dedicated reasoning-only incomplete retry remains."
                        ),
                    },
                }
                return {**body, "content_hash": sha256_json(body)}

            workflow_instruction_document = bind_generation_recovery(workflow_instruction_document)
            normalized_instruction_document = bind_generation_recovery(
                normalized_instruction_document
            )

        def workflow_context_v2(source: str, instruction: dict[str, Any]) -> str:
            try:
                payload = json.loads(source)
            except json.JSONDecodeError as exc:
                raise ContractError("Lean V11+ workflow context must be JSON") from exc
            if type(payload) is not dict:
                raise ContractError("Lean V11+ workflow context must be an object")
            payload["workflow"] = copy.deepcopy(instruction)
            return canonical_json(payload)

        request_context = workflow_context_v2(
            workflow_source_context,
            workflow_instruction_document,
        )
        normalized_request_context = workflow_context_v2(
            normalized_workflow_source_context,
            normalized_instruction_document,
        )
        request_reasoning_effort = workflow_decision.reasoning_effort
        exploratory_ceiling = workflow_decision.effective_max_output_tokens
    else:
        exploration_surface = _lean_surface(
            phase_surface=phase_surface,
            saturation=saturation,
            mode="exploration",
            completion_driven=(
                runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V2,
                    LEAN_RUNTIME_POLICY_VERSION_V3,
                    LEAN_RUNTIME_POLICY_VERSION_V4,
                    LEAN_RUNTIME_POLICY_VERSION_V5,
                    LEAN_RUNTIME_POLICY_VERSION_V6,
                    LEAN_RUNTIME_POLICY_VERSION_V7,
                }
            ),
            completion_successor=(
                runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V4,
                    LEAN_RUNTIME_POLICY_VERSION_V5,
                    LEAN_RUNTIME_POLICY_VERSION_V6,
                    LEAN_RUNTIME_POLICY_VERSION_V7,
                }
            ),
            state_driven_after_mutation=(runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V7),
        )
        request_context = compacted.rendered
        normalized_request_context = normalized_compacted.rendered
        exploratory_ceiling = configured_max_output_tokens
    exploratory_body = build_request_body(
        request_context,
        exploration_surface.selected_tool_schemas,
        exploratory_ceiling,
    )
    exploratory_input = count_request_body(exploratory_body)
    mode = project_finalization_request_mode(
        reserve=dependencies.reserve,
        requested_input_tokens=exploratory_input,
        configured_max_output_tokens=exploratory_ceiling,
        input_tokens_used=usage.input_tokens,
        output_tokens_used=usage.output_tokens,
        max_cumulative_input_tokens=runtime.max_cumulative_input_tokens,
        max_cumulative_output_tokens=runtime.max_cumulative_output_tokens,
        max_total_tokens=runtime.max_total_tokens,
    )
    if mode.mode == "block":
        raise ContractError("Lean finalization reserve is exhausted")
    surface = (
        exploration_surface
        if mode.mode == "exploration"
        or runtime_policy_version
        in {
            LEAN_RUNTIME_POLICY_VERSION_V8,
            LEAN_RUNTIME_POLICY_VERSION_V9,
            LEAN_RUNTIME_POLICY_VERSION_V10,
            LEAN_RUNTIME_POLICY_VERSION_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }
        else _lean_surface(
            phase_surface=phase_surface,
            saturation=saturation,
            mode="finalization",
            completion_driven=(
                runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V2,
                    LEAN_RUNTIME_POLICY_VERSION_V3,
                    LEAN_RUNTIME_POLICY_VERSION_V4,
                    LEAN_RUNTIME_POLICY_VERSION_V5,
                    LEAN_RUNTIME_POLICY_VERSION_V6,
                    LEAN_RUNTIME_POLICY_VERSION_V7,
                }
            ),
            completion_successor=(
                runtime_policy_version
                in {
                    LEAN_RUNTIME_POLICY_VERSION_V4,
                    LEAN_RUNTIME_POLICY_VERSION_V5,
                    LEAN_RUNTIME_POLICY_VERSION_V6,
                    LEAN_RUNTIME_POLICY_VERSION_V7,
                }
            ),
            state_driven_after_mutation=(runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V7),
        )
    )
    configured_output = (
        exploratory_ceiling
        if mode.mode == "exploration"
        or runtime_policy_version
        in {
            LEAN_RUNTIME_POLICY_VERSION_V4,
            LEAN_RUNTIME_POLICY_VERSION_V5,
            LEAN_RUNTIME_POLICY_VERSION_V6,
            LEAN_RUNTIME_POLICY_VERSION_V7,
            LEAN_RUNTIME_POLICY_VERSION_V8,
            LEAN_RUNTIME_POLICY_VERSION_V9,
            LEAN_RUNTIME_POLICY_VERSION_V10,
            LEAN_RUNTIME_POLICY_VERSION_V13,
            LEAN_RUNTIME_POLICY_VERSION_V14,
            LEAN_RUNTIME_POLICY_VERSION_V15,
            LEAN_RUNTIME_POLICY_VERSION_V16,
            LEAN_RUNTIME_POLICY_VERSION_V17,
            LEAN_RUNTIME_POLICY_VERSION_V18,
            LEAN_RUNTIME_POLICY_VERSION_V19,
            LEAN_RUNTIME_POLICY_VERSION_V20,
            LEAN_RUNTIME_POLICY_VERSION_V21,
            LEAN_RUNTIME_POLICY_VERSION_V22,
            LEAN_RUNTIME_POLICY_VERSION_V23,
            LEAN_RUNTIME_POLICY_VERSION_V24,
            LEAN_RUNTIME_POLICY_VERSION_V25,
            LEAN_RUNTIME_POLICY_VERSION_V26,
            LEAN_RUNTIME_POLICY_VERSION_V27,
            LEAN_RUNTIME_POLICY_VERSION_V28,
        }
        else runtime.finalization_max_output_tokens
    )
    incomplete_recovery: ReasoningIncompleteRecovery | None = None
    completion_response_recovery: CompletionResponseRecovery | None = None

    def recovery_context(
        source: str,
        recovery: ReasoningIncompleteRecovery,
    ) -> str:
        try:
            payload = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ContractError("Lean V5 recovery context must be JSON") from exc
        if not isinstance(payload, dict):
            raise ContractError("Lean V5 recovery context must be an object")
        instruction = (
            "The previous response spent its output allowance entirely on "
            "reasoning and produced no action. Emit exactly one available tool "
            "call now; do not explore."
            if recovery.mode == "retry"
            else (
                "No retry capacity remains. Complete exactly one available action "
                "before the response ceiling; do not explore."
                if recovery.mode == "primary-direct-low"
                else (
                    "Complete the single allowed action before the response ceiling; "
                    "one bounded retry is reserved only for a reasoning-only "
                    "incomplete response."
                    if recovery.mode == "primary-reserved"
                    else "Use the phase-filtered tool surface."
                )
            )
        )
        payload["response_recovery"] = {
            "schema_version": recovery.schema_version,
            "policy_version": recovery.policy_version,
            "mode": recovery.mode,
            "reasoning_effort": recovery.reasoning_effort,
            "reserved_retry_output_tokens": (recovery.reserved_retry_output_tokens),
            "source_event_sequence": recovery.source_event_sequence,
            "instruction": instruction,
        }
        return canonical_json(payload)

    def completion_recovery_context(
        source: str,
        recovery: CompletionResponseRecovery,
    ) -> str:
        try:
            payload = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ContractError("Lean V7 completion recovery context must be JSON") from exc
        if not isinstance(payload, dict):
            raise ContractError("Lean V7 completion recovery context must be an object")
        selected_names = list(surface.selected_tool_names)
        if recovery.mode == "retry-actionless":
            instruction = (
                "The previous successful response emitted no action. Emit exactly one "
                "available tool call now, with no narration and no exploration."
            )
        elif recovery.mode == "retry-reasoning-incomplete":
            instruction = (
                "The previous response spent its allowance entirely on reasoning. Emit "
                "exactly one available tool call now, with no narration and no exploration."
            )
        elif recovery.mode == "primary-direct-low":
            instruction = (
                "No recovery slot remains. Complete exactly one available tool action "
                "before the response ceiling, with no exploration."
            )
        elif recovery.mode == "primary-reserved":
            instruction = (
                "Complete exactly one available tool action before the response ceiling. "
                "One shared bounded retry is reserved only for an actionless success or "
                "reasoning-only incomplete response."
            )
        else:
            instruction = "Use the phase-filtered tool surface."
        payload["response_recovery"] = {
            "schema_version": recovery.schema_version,
            "policy_version": recovery.policy_version,
            "mode": recovery.mode,
            "completion_lane_active": recovery.completion_lane_active,
            "completion_target": surface.completion_target,
            "available_tool_names": selected_names,
            "reasoning_effort": recovery.reasoning_effort,
            "reserved_retry_output_tokens": recovery.reserved_retry_output_tokens,
            "source_response_kind": recovery.source_response_kind,
            "source_event_sequence": recovery.source_event_sequence,
            "instruction": instruction,
            "edit_correction_instruction": (
                "For a structured edit, use the smallest unique current expected_text "
                "span. Follow edit_correction excerpts after rejection; never replay "
                "stale source or replace a whole function for a small change."
            ),
        }
        return canonical_json(payload)

    if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V7:
        if not isinstance(surface, LeanPhaseToolSurfaceV4):
            raise ContractError("Lean V7 requires its state-driven completion surface")
        candidate_input = count_request_body(
            build_request_body(
                request_context,
                surface.selected_tool_schemas,
                configured_output,
            )
        )
        for _ in range(4):
            completion_response_recovery = project_completion_response_recovery(
                phase_mode=mode.mode,
                completion_lane_active=surface.completion_lane_active,
                events=events,
                usage=usage,
                budget=budget,
                requested_input_tokens=candidate_input,
                configured_max_output_tokens=configured_max_output_tokens,
            )
            request_reasoning_effort = completion_response_recovery.reasoning_effort
            request_context = completion_recovery_context(
                compacted.rendered,
                completion_response_recovery,
            )
            normalized_request_context = completion_recovery_context(
                normalized_compacted.rendered,
                completion_response_recovery,
            )
            configured_output = completion_response_recovery.effective_max_output_tokens
            provisional = build_request_body(
                request_context,
                surface.selected_tool_schemas,
                configured_output,
            )
            recounted = count_request_body(provisional)
            if recounted == candidate_input:
                break
            candidate_input = recounted
        else:
            raise ContractError("Lean V7 completion request count did not converge")
        requested_input = candidate_input
    elif runtime_policy_version in {
        LEAN_RUNTIME_POLICY_VERSION_V5,
        LEAN_RUNTIME_POLICY_VERSION_V6,
    }:
        candidate_input = count_request_body(
            build_request_body(
                request_context,
                surface.selected_tool_schemas,
                configured_output,
            )
        )
        for _ in range(4):
            incomplete_recovery = project_reasoning_incomplete_recovery(
                phase_mode=mode.mode,
                events=events,
                usage=usage,
                budget=budget,
                requested_input_tokens=candidate_input,
                configured_max_output_tokens=configured_max_output_tokens,
            )
            request_reasoning_effort = incomplete_recovery.reasoning_effort
            request_context = recovery_context(
                compacted.rendered,
                incomplete_recovery,
            )
            normalized_request_context = recovery_context(
                normalized_compacted.rendered,
                incomplete_recovery,
            )
            configured_output = incomplete_recovery.effective_max_output_tokens
            provisional = build_request_body(
                request_context,
                surface.selected_tool_schemas,
                configured_output,
            )
            recounted = count_request_body(provisional)
            if recounted == candidate_input:
                break
            candidate_input = recounted
        else:
            raise ContractError("Lean V5 recovery request count did not converge")
        requested_input = candidate_input
    else:
        provisional = build_request_body(
            request_context,
            surface.selected_tool_schemas,
            configured_output,
        )
        requested_input = (
            exploratory_input
            if provisional == exploratory_body
            else count_request_body(provisional)
        )
    allowance = project_split_aware_request_allowance(
        requested_input_tokens=requested_input,
        configured_max_output_tokens=configured_output,
        input_tokens_used=usage.input_tokens,
        output_tokens_used=usage.output_tokens,
        max_cumulative_input_tokens=runtime.max_cumulative_input_tokens,
        max_cumulative_output_tokens=runtime.max_cumulative_output_tokens,
        max_total_tokens=runtime.max_total_tokens,
    )
    if allowance.decision == "block" or allowance.effective_max_output_tokens <= 0:
        raise ContractError("Lean split budget blocks the exact request")
    request_body = build_request_body(
        request_context,
        surface.selected_tool_schemas,
        allowance.effective_max_output_tokens,
    )
    final_input = requested_input if live_provider_request else count_request_body(request_body)
    if final_input != requested_input:
        allowance = project_split_aware_request_allowance(
            requested_input_tokens=final_input,
            configured_max_output_tokens=configured_output,
            input_tokens_used=usage.input_tokens,
            output_tokens_used=usage.output_tokens,
            max_cumulative_input_tokens=runtime.max_cumulative_input_tokens,
            max_cumulative_output_tokens=runtime.max_cumulative_output_tokens,
            max_total_tokens=runtime.max_total_tokens,
        )
        if allowance.decision == "block" or allowance.effective_max_output_tokens <= 0:
            raise ContractError("Lean rebuilt split budget blocks the exact request")
        request_body = build_request_body(
            request_context,
            surface.selected_tool_schemas,
            allowance.effective_max_output_tokens,
        )
        final_input = count_request_body(request_body)

    normalized_body = build_request_body(
        normalized_request_context,
        surface.selected_tool_schemas,
        allowance.effective_max_output_tokens,
    )
    phase_body = asdict(phase_evidence)
    if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION:
        runtime_contract_hash = (
            sha256_json(
                {
                    "schema_version": "lean-harness-live-runtime-contract-v1",
                    "base_runtime_contract_hash": runtime.content_hash,
                    "provider": "openai",
                    "model_id": model_id,
                    "input_count_method": live_input_count_method,
                }
            )
            if live_provider_request
            else runtime.content_hash
        )
    else:
        successor_runtime_contract: dict[str, Any] = {
            "schema_version": (
                "lean-harness-successor-runtime-contract-v28"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V28
                else "lean-harness-successor-runtime-contract-v26"
                if runtime_policy_version
                in {LEAN_RUNTIME_POLICY_VERSION_V26, LEAN_RUNTIME_POLICY_VERSION_V27}
                else "lean-harness-successor-runtime-contract-v25"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V25
                else "lean-harness-successor-runtime-contract-v24"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V24
                else "lean-harness-successor-runtime-contract-v23"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V23
                else "lean-harness-successor-runtime-contract-v22"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V22
                else "lean-harness-successor-runtime-contract-v21"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V21
                else "lean-harness-successor-runtime-contract-v20"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V20
                else "lean-harness-successor-runtime-contract-v19"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V19
                else "lean-harness-successor-runtime-contract-v18"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V18
                else "lean-harness-successor-runtime-contract-v17"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V17
                else "lean-harness-successor-runtime-contract-v16"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V16
                else "lean-harness-successor-runtime-contract-v15"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V15
                else "lean-harness-successor-runtime-contract-v14"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V14
                else "lean-harness-successor-runtime-contract-v13"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V13
                else "lean-harness-successor-runtime-contract-v12"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V12
                else "lean-harness-successor-runtime-contract-v11"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V11
                else "lean-harness-successor-runtime-contract-v10"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V10
                else "lean-harness-successor-runtime-contract-v9"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V9
                else "lean-harness-successor-runtime-contract-v8"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V8
                else "lean-harness-successor-runtime-contract-v7"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V7
                else "lean-harness-successor-runtime-contract-v6"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V6
                else "lean-harness-successor-runtime-contract-v5"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V5
                else "lean-harness-successor-runtime-contract-v4"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V4
                else "lean-harness-successor-runtime-contract-v3"
                if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V3
                else "lean-harness-successor-runtime-contract-v2"
            ),
            "base_runtime_contract_hash": runtime.content_hash,
            "runtime_policy_version": runtime_policy_version,
            "tool_schema_version": tool_schema_version,
            "context_policy_version": context_policy_version,
            **successor_bindings,
        }
        if live_provider_request:
            successor_runtime_contract.update(
                {
                    "provider": "openai",
                    "model_id": model_id,
                    "input_count_method": live_input_count_method,
                }
            )
        runtime_contract_hash = sha256_json(successor_runtime_contract)

    body: dict[str, Any] = {
        "schema_version": request_evidence_schema,
        "runtime_policy_version": runtime_policy_version,
        "tool_schema_version": tool_schema_version,
        "context_policy_version": context_policy_version,
        **successor_bindings,
        "input_count_method": (
            live_input_count_method if live_provider_request else LEAN_MOCK_COUNT_METHOD
        ),
        "pipeline_stages": runtime.pipeline_stages,
        "runtime_contract_hash": runtime_contract_hash,
        "context_build_hash": sha256_json(built_context.evidence),
        "context_compaction_evidence_hash": compacted.evidence.content_hash,
        "phase_evidence_hash": sha256_json(phase_body),
        "saturation_recovery_evidence_hash": saturation.content_hash,
        "finalization_request_mode_hash": mode.content_hash,
        "phase_tool_surface_hash": surface.content_hash,
        "selected_tool_schema_hash": surface.selected_tool_schema_hash,
        "requested_input_tokens": final_input,
        "effective_max_output_tokens": allowance.effective_max_output_tokens,
        "split_allowance_hash": sha256_json(allowance.model_dump(mode="json")),
        "request_body_hash": sha256_text(canonical_json(request_body)),
        "memory_delivery_evidence_sha256": memory_delivery_evidence_sha256,
        "normalized_no_memory_request_body_sha256": sha256_text(canonical_json(normalized_body)),
        "context_build": copy.deepcopy(built_context.evidence),
        "context_compaction": compacted.evidence.model_dump(mode="python"),
        "phase_evidence": phase_body,
        "saturation_recovery": saturation.model_dump(mode="python"),
        "finalization_request_mode": mode.model_dump(mode="python"),
        "phase_tool_surface": surface.model_dump(mode="python"),
        "split_allowance": allowance.model_dump(mode="python"),
        **(
            {
                "incomplete_recovery": (incomplete_recovery.model_dump(mode="python")),
                "incomplete_recovery_hash": incomplete_recovery.content_hash,
                "recovery_context_hash": sha256_text(request_context),
            }
            if incomplete_recovery is not None
            else {}
        ),
        **(
            {
                "completion_response_recovery": (
                    completion_response_recovery.model_dump(mode="python")
                ),
                "completion_response_recovery_hash": (completion_response_recovery.content_hash),
                "recovery_context_hash": sha256_text(request_context),
            }
            if completion_response_recovery is not None
            else {}
        ),
        **(
            {
                "public_task_hash": sha256_json(task.model_dump(mode="json")),
                "public_check_order": tuple(check.id for check in task.visible_checks),
                "completion_loop_decision": (completion_loop_decision.model_dump(mode="python")),
                "completion_loop_decision_hash": completion_loop_decision.content_hash,
                "correction_context": correction_context.evidence.model_dump(mode="python"),
                "correction_context_hash": correction_context.evidence.content_hash,
                "normalized_correction_context_hash": (
                    normalized_correction_context.evidence.content_hash
                ),
                "completion_instruction": completion_loop_instruction,
                "completion_instruction_hash": completion_loop_instruction["content_hash"],
                "completion_context_hash": sha256_text(request_context),
                "parallel_tool_calls": False,
                "one_tool_call_per_response": True,
            }
            if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V8
            and task is not None
            and completion_loop_decision is not None
            and correction_context is not None
            and normalized_correction_context is not None
            and completion_loop_instruction is not None
            else {}
        ),
        **(
            {
                "public_task_hash": sha256_json(task.model_dump(mode="json")),
                "public_check_order": tuple(check.id for check in task.visible_checks),
                "workflow_decision": workflow_decision.model_dump(mode="python"),
                "workflow_decision_hash": workflow_decision.content_hash,
                "correction_context": correction_context.evidence.model_dump(mode="python"),
                "correction_context_hash": correction_context.evidence.content_hash,
                "normalized_correction_context_hash": (
                    normalized_correction_context.evidence.content_hash
                ),
                "workflow_instruction": workflow_instruction_document,
                "workflow_instruction_hash": workflow_instruction_document["content_hash"],
                "workflow_context_hash": sha256_text(request_context),
                "parallel_tool_calls": False,
                "one_tool_call_per_response": True,
                **(
                    {
                        "public_task_spec": workflow_task_spec.model_dump(mode="python"),
                        "public_task_spec_hash": workflow_task_spec.content_hash,
                    }
                    if workflow_task_spec is not None
                    else {}
                ),
            }
            if runtime_policy_version
            in {LEAN_RUNTIME_POLICY_VERSION_V9, LEAN_RUNTIME_POLICY_VERSION_V10}
            and task is not None
            and workflow_decision is not None
            and correction_context is not None
            and normalized_correction_context is not None
            and workflow_instruction_document is not None
            else {}
        ),
        **(
            {
                "public_task_hash": sha256_json(task.model_dump(mode="json")),
                "public_check_order": tuple(check.id for check in task.visible_checks),
                "workflow_decision": workflow_decision.model_dump(mode="python"),
                "workflow_decision_hash": workflow_decision.content_hash,
                "correction_context": correction_context.evidence.model_dump(mode="python"),
                "correction_context_hash": correction_context.evidence.content_hash,
                "normalized_correction_context_hash": (
                    normalized_correction_context.evidence.content_hash
                ),
                "workflow_instruction": workflow_instruction_document,
                "workflow_instruction_hash": workflow_instruction_document["content_hash"],
                "workflow_context_hash": sha256_text(request_context),
                "parallel_tool_calls": False,
                "one_tool_call_per_response": True,
                "public_task_spec": workflow_task_spec.model_dump(mode="python"),
                "public_task_spec_hash": workflow_task_spec.content_hash,
                "eligible_plan_evidence_catalog": workflow_catalog.model_dump(mode="python"),
                "eligible_plan_evidence_catalog_hash": workflow_catalog.content_hash,
                "active_work_plan": (
                    active_work_state.latest_plan.model_dump(mode="python")
                    if active_work_state is not None
                    else None
                ),
                "active_work_state": (
                    active_work_state.model_dump(mode="python")
                    if active_work_state is not None
                    else None
                ),
                "active_work_state_hash": (
                    active_work_state.content_hash
                    if active_work_state is not None
                    else sha256_json(None)
                ),
                **(
                    {
                        "plan_admission_feedback_projection": (
                            plan_admission_feedback_projection.evidence.model_dump(mode="python")
                        ),
                        "plan_admission_feedback_projection_hash": (
                            plan_admission_feedback_projection.evidence.content_hash
                        ),
                    }
                    if runtime_policy_version
                    in {
                        LEAN_RUNTIME_POLICY_VERSION_V22,
                        LEAN_RUNTIME_POLICY_VERSION_V23,
                        LEAN_RUNTIME_POLICY_VERSION_V24,
                        LEAN_RUNTIME_POLICY_VERSION_V25,
                        LEAN_RUNTIME_POLICY_VERSION_V26,
                        LEAN_RUNTIME_POLICY_VERSION_V27,
                        LEAN_RUNTIME_POLICY_VERSION_V28,
                    }
                    and plan_admission_feedback_projection is not None
                    and normalized_plan_admission_feedback_projection is not None
                    else {}
                ),
            }
            if runtime_policy_version
            in {
                LEAN_RUNTIME_POLICY_VERSION_V11,
                LEAN_RUNTIME_POLICY_VERSION_V12,
                LEAN_RUNTIME_POLICY_VERSION_V13,
                LEAN_RUNTIME_POLICY_VERSION_V14,
                LEAN_RUNTIME_POLICY_VERSION_V15,
                LEAN_RUNTIME_POLICY_VERSION_V16,
                LEAN_RUNTIME_POLICY_VERSION_V17,
                LEAN_RUNTIME_POLICY_VERSION_V18,
                LEAN_RUNTIME_POLICY_VERSION_V19,
                LEAN_RUNTIME_POLICY_VERSION_V20,
                LEAN_RUNTIME_POLICY_VERSION_V21,
                LEAN_RUNTIME_POLICY_VERSION_V22,
                LEAN_RUNTIME_POLICY_VERSION_V23,
                LEAN_RUNTIME_POLICY_VERSION_V24,
                LEAN_RUNTIME_POLICY_VERSION_V25,
                LEAN_RUNTIME_POLICY_VERSION_V26,
                LEAN_RUNTIME_POLICY_VERSION_V27,
                LEAN_RUNTIME_POLICY_VERSION_V28,
            }
            and task is not None
            and isinstance(workflow_decision, WorkflowDecisionV2)
            and correction_context is not None
            and normalized_correction_context is not None
            and workflow_instruction_document is not None
            and workflow_task_spec is not None
            and workflow_catalog is not None
            else {}
        ),
        "request_body": request_body,
        "request_evidence_persisted_before_dispatch": True,
        "dispatch_requires_exact_persisted_request": True,
        "legacy_runtime_fallback_allowed": False,
        "provider_authority_granted": False,
    }
    if runtime_policy_version in {
        LEAN_RUNTIME_POLICY_VERSION_V26,
        LEAN_RUNTIME_POLICY_VERSION_V27,
        LEAN_RUNTIME_POLICY_VERSION_V28,
    }:
        if generation_incomplete_recovery_state is None:
            raise ContractError("Lean V26 generation recovery state is missing")
        body["generation_incomplete_recovery_state"] = (
            generation_incomplete_recovery_state.model_dump(mode="python")
        )
    if runtime_policy_version in {
        LEAN_RUNTIME_POLICY_VERSION_V27,
        LEAN_RUNTIME_POLICY_VERSION_V28,
    }:
        body["provider_tool_schema_admission"] = validate_provider_tool_schemas(request_body)
    evidence = evidence_model.model_validate_json(
        canonical_json({**body, "content_hash": sha256_json(body)})
    )
    return LeanHarnessAssembledRequest(
        context=request_context,
        context_hash=sha256_text(request_context),
        tool_schemas=surface.selected_tool_schemas,
        request_body=request_body,
        requested_input_tokens=final_input,
        evidence=evidence,
    )


def validate_persisted_lean_harness_request(
    payload: dict[str, Any],
) -> LeanHarnessRequestEvidenceAny:
    """Validate the nested evidence and exact request body before dispatch."""

    if type(payload) is not dict:
        raise ContractError("Lean persisted request artifact must be an exact mapping")
    try:
        persisted_evidence = payload.get("lean_harness_request")
        if not isinstance(persisted_evidence, dict):
            raise ValueError("Lean persisted request evidence must be a mapping")
        schema_version = persisted_evidence.get("schema_version")
        if schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V28:
            evidence_model = LeanHarnessRequestEvidenceV28
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V27:
            evidence_model = LeanHarnessRequestEvidenceV27
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V26:
            evidence_model = LeanHarnessRequestEvidenceV26
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V25:
            evidence_model = LeanHarnessRequestEvidenceV25
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V24:
            evidence_model = LeanHarnessRequestEvidenceV24
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V23:
            evidence_model = LeanHarnessRequestEvidenceV23
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V22:
            evidence_model = LeanHarnessRequestEvidenceV22
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V21:
            evidence_model = LeanHarnessRequestEvidenceV21
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V20:
            evidence_model = LeanHarnessRequestEvidenceV20
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V19:
            evidence_model = LeanHarnessRequestEvidenceV19
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V18:
            evidence_model = LeanHarnessRequestEvidenceV18
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V17:
            evidence_model = LeanHarnessRequestEvidenceV17
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V16:
            evidence_model = LeanHarnessRequestEvidenceV16
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V15:
            evidence_model = LeanHarnessRequestEvidenceV15
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V14:
            evidence_model = LeanHarnessRequestEvidenceV14
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V13:
            evidence_model = LeanHarnessRequestEvidenceV13
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V12:
            evidence_model = LeanHarnessRequestEvidenceV12
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V11:
            evidence_model = LeanHarnessRequestEvidenceV11
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V10:
            evidence_model = LeanHarnessRequestEvidenceV10
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V9:
            evidence_model = LeanHarnessRequestEvidenceV9
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V8:
            evidence_model = LeanHarnessRequestEvidenceV8
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V7:
            evidence_model = LeanHarnessRequestEvidenceV7
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V6:
            evidence_model = LeanHarnessRequestEvidenceV6
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V5:
            evidence_model = LeanHarnessRequestEvidenceV5
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V4:
            evidence_model = LeanHarnessRequestEvidenceV4
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V3:
            evidence_model = LeanHarnessRequestEvidenceV3
        elif schema_version == LEAN_REQUEST_EVIDENCE_SCHEMA_V2:
            evidence_model = LeanHarnessRequestEvidenceV2
        else:
            evidence_model = LeanHarnessRequestEvidence
        evidence = evidence_model.model_validate_json(
            json.dumps(
                persisted_evidence,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        )
    except ValueError as exc:
        raise ContractError("Lean persisted request evidence is invalid") from exc
    if payload.get("request_body") != evidence.request_body:
        raise ContractError("Lean persisted request body differs from its evidence")
    if payload.get("request_body_hash") != evidence.request_body_hash:
        raise ContractError("Lean persisted request hash differs from its evidence")
    return evidence


def build_lean_harness_calibration_manifest(
    package: TaskPackage,
    *,
    run_id: str,
    condition: MemoryCondition,
    sandbox_backend: Literal["local", "docker"] = "local",
    runtime_policy_version: str = LEAN_RUNTIME_POLICY_VERSION,
) -> RunManifest:
    """Build the exact public-calibration manifest without a live experiment."""

    if condition not in {MemoryCondition.NO_MEMORY, MemoryCondition.STRUCTURED}:
        raise ContractError("Lean calibration supports only A/C conditions")
    from patchloop.runtime import build_manifest

    base = build_manifest(
        package,
        run_id=run_id,
        provider="mock",
        model_id=LEAN_MOCK_MODEL_ID,
        memory_condition=condition,
        memory_policy_version=FIXED_BUNDLE_POLICY_VERSION,
        sandbox_backend=sandbox_backend,
        budget=Budget(
            max_model_calls=240,
            max_tool_calls=400,
            max_total_tokens=1_100_000,
            wall_clock_timeout_seconds=3_600,
            token_budget_schema_version="cumulative-split-v1",
            max_cumulative_input_tokens=1_000_000,
            max_cumulative_output_tokens=100_000,
        ),
        max_output_tokens=25_000,
    )
    body = base.model_dump(mode="python")
    if runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V2:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V2
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V2
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V3:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V3
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V3
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V4:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V4
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V4
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V5:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V5
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V5
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V6:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V6
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V6
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V7:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V7
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V7
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V8:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V8
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V8
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V9:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V9
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V9
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V10:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V10
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V10
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V11:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V11
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V11
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V12:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V12
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V12
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V13:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V13
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V13
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V14:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V14
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V14
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V15:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V15
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V15
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V16:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V16
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V16
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V17:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V17
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V17
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V18:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V18
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V18
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V19:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V19
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V19
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V20:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V20
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V20
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V21:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V21
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V21
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V22:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V22
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V22
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V23:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V23
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V23
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V24:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V24
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V24
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V25:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V25
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V25
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V27:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V27
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V27
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V28:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V28
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V28
    elif runtime_policy_version == LEAN_RUNTIME_POLICY_VERSION_V26:
        body["tool_schema_version"] = LEAN_TOOL_SCHEMA_VERSION_V26
        body["context_policy_version"] = LEAN_CONTEXT_POLICY_VERSION_V26
    else:
        raise ContractError("unsupported Lean Harness runtime policy version")
    body["model"]["temperature"] = 0.0
    manifest = RunManifest.model_validate(body)
    if condition == MemoryCondition.NO_MEMORY and (
        manifest.memory.index_version is not None or manifest.memory.index_hash is not None
    ):
        raise ContractError("Lean A manifest contains memory")
    if condition == MemoryCondition.STRUCTURED and (
        manifest.memory.index_version != D110_INDEX_VERSION
        or manifest.memory.index_hash != D110_INDEX_CONTENT_HASH
    ):
        raise ContractError("Lean C manifest lacks exact D-110 memory")
    return manifest


__all__ = [
    "LEAN_CONTEXT_POLICY_VERSION",
    "LEAN_CONTEXT_POLICY_VERSION_V2",
    "LEAN_CONTEXT_POLICY_VERSION_V3",
    "LEAN_CONTEXT_POLICY_VERSION_V4",
    "LEAN_CONTEXT_POLICY_VERSION_V5",
    "LEAN_CONTEXT_POLICY_VERSION_V6",
    "LEAN_CONTEXT_POLICY_VERSION_V7",
    "LEAN_CONTEXT_POLICY_VERSION_V8",
    "LEAN_CONTEXT_POLICY_VERSION_V9",
    "LEAN_CONTEXT_POLICY_VERSION_V10",
    "LEAN_CONTEXT_POLICY_VERSION_V11",
    "LEAN_CONTEXT_POLICY_VERSION_V12",
    "LEAN_CONTEXT_POLICY_VERSION_V13",
    "LEAN_CONTEXT_POLICY_VERSION_V14",
    "LEAN_CONTEXT_POLICY_VERSION_V15",
    "LEAN_CONTEXT_POLICY_VERSION_V16",
    "LEAN_CONTEXT_POLICY_VERSION_V17",
    "LEAN_CONTEXT_POLICY_VERSION_V18",
    "LEAN_CONTEXT_POLICY_VERSION_V19",
    "LEAN_CONTEXT_POLICY_VERSION_V20",
    "LEAN_CONTEXT_POLICY_VERSION_V21",
    "LEAN_CONTEXT_POLICY_VERSION_V22",
    "LEAN_CONTEXT_POLICY_VERSION_V23",
    "LEAN_CONTEXT_POLICY_VERSION_V24",
    "LEAN_CONTEXT_POLICY_VERSION_V25",
    "LEAN_CONTEXT_POLICY_VERSION_V26",
    "LEAN_CONTEXT_POLICY_VERSION_V27",
    "LEAN_CONTEXT_POLICY_VERSION_V28",
    "LEAN_COMPLETION_POLICY_VERSION_V4",
    "LEAN_FINALIZATION_ALLOWANCE_POLICY_VERSION_V4",
    "LEAN_FINALIZATION_WORKFLOW_SURFACE_POLICY_VERSION_V13",
    "LEAN_REQUIRED_TRIGGER_PIN_POLICY_VERSION_V14",
    "LEAN_SEMANTIC_PROGRESS_POLICY_VERSION_V15",
    "LEAN_CANDIDATE_BINDING_POLICY_VERSION_V16",
    "LEAN_CAUSAL_ACTIVATION_POLICY_VERSION_V17",
    "LEAN_CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY_VERSION_V18",
    "LEAN_EXPLORATION_GATE_ACTIVATION_POLICY_VERSION_V19",
    "LEAN_SEMANTIC_PROGRESS_EPOCH_PARITY_POLICY_VERSION_V20",
    "LEAN_PLAN_GATE_LIVENESS_POLICY_VERSION_V21",
    "LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22",
    "LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23",
    "LEAN_EXACT_PRE_PLAN_SURFACE_POLICY_VERSION_V24",
    "LEAN_BOUNDED_REQUEST_CONTEXT_POLICY_VERSION_V24",
    "LEAN_PLAN_CONTRACT_COMPATIBILITY_POLICY_VERSION_V25",
    "LEAN_GENERATION_INCOMPLETE_RECOVERY_POLICY_VERSION_V26",
    "LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V26",
    "LEAN_ANCHORED_READ_POLICY_VERSION_V26",
    "LEAN_LIFECYCLE_PLAN_POLICY_VERSION_V26",
    "LEAN_LIFECYCLE_PLAN_POLICY_VERSION_V28",
    "LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V28",
    "LEAN_EVENT_DESCRIPTOR_ROLE_POLICY_VERSION_V6",
    "LEAN_EDIT_CORRECTION_POLICY_VERSION_V7",
    "LEAN_RESPONSE_RECOVERY_POLICY_VERSION_V7",
    "LEAN_COMPLETION_POLICY_VERSION_V7",
    "LEAN_COMPLETION_POLICY_VERSION_V8",
    "LEAN_CORRECTION_CONTEXT_POLICY_VERSION_V8",
    "LEAN_PROVIDER_TERMINAL_POLICY_VERSION_V8",
    "LEAN_COMPLETION_POLICY_VERSION_V2",
    "LEAN_MOCK_COUNT_METHOD",
    "LEAN_MOCK_MODEL_ID",
    "LEAN_REQUEST_EVIDENCE_SCHEMA",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V2",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V3",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V4",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V5",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V6",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V7",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V8",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V9",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V10",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V11",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V12",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V13",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V14",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V15",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V16",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V17",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V18",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V19",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V20",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V21",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V22",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V23",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V24",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V25",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V26",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V27",
    "LEAN_REQUEST_EVIDENCE_SCHEMA_V28",
    "LEAN_RUNTIME_POLICY_VERSION",
    "LEAN_RUNTIME_POLICY_VERSION_V2",
    "LEAN_RUNTIME_POLICY_VERSION_V3",
    "LEAN_RUNTIME_POLICY_VERSION_V4",
    "LEAN_RUNTIME_POLICY_VERSION_V5",
    "LEAN_RUNTIME_POLICY_VERSION_V6",
    "LEAN_RUNTIME_POLICY_VERSION_V7",
    "LEAN_RUNTIME_POLICY_VERSION_V8",
    "LEAN_RUNTIME_POLICY_VERSION_V9",
    "LEAN_RUNTIME_POLICY_VERSION_V10",
    "LEAN_RUNTIME_POLICY_VERSION_V11",
    "LEAN_RUNTIME_POLICY_VERSION_V12",
    "LEAN_RUNTIME_POLICY_VERSION_V13",
    "LEAN_RUNTIME_POLICY_VERSION_V14",
    "LEAN_RUNTIME_POLICY_VERSION_V15",
    "LEAN_RUNTIME_POLICY_VERSION_V16",
    "LEAN_RUNTIME_POLICY_VERSION_V17",
    "LEAN_RUNTIME_POLICY_VERSION_V18",
    "LEAN_RUNTIME_POLICY_VERSION_V19",
    "LEAN_RUNTIME_POLICY_VERSION_V20",
    "LEAN_RUNTIME_POLICY_VERSION_V21",
    "LEAN_RUNTIME_POLICY_VERSION_V22",
    "LEAN_RUNTIME_POLICY_VERSION_V23",
    "LEAN_RUNTIME_POLICY_VERSION_V24",
    "LEAN_RUNTIME_POLICY_VERSION_V25",
    "LEAN_RUNTIME_POLICY_VERSION_V26",
    "LEAN_RUNTIME_POLICY_VERSION_V27",
    "LEAN_RUNTIME_POLICY_VERSION_V28",
    "LEAN_PATCH_NORMALIZATION_POLICY_VERSION_V2",
    "LEAN_SEARCH_GLOB_POLICY_VERSION_V3",
    "LEAN_TOOL_SCHEMA_VERSION",
    "LEAN_TOOL_SCHEMA_VERSION_V2",
    "LEAN_TOOL_SCHEMA_VERSION_V3",
    "LEAN_TOOL_SCHEMA_VERSION_V4",
    "LEAN_TOOL_SCHEMA_VERSION_V5",
    "LEAN_TOOL_SCHEMA_VERSION_V6",
    "LEAN_TOOL_SCHEMA_VERSION_V7",
    "LEAN_TOOL_SCHEMA_VERSION_V8",
    "LEAN_TOOL_SCHEMA_VERSION_V9",
    "LEAN_TOOL_SCHEMA_VERSION_V10",
    "LEAN_TOOL_SCHEMA_VERSION_V11",
    "LEAN_TOOL_SCHEMA_VERSION_V12",
    "LEAN_TOOL_SCHEMA_VERSION_V13",
    "LEAN_TOOL_SCHEMA_VERSION_V14",
    "LEAN_TOOL_SCHEMA_VERSION_V15",
    "LEAN_TOOL_SCHEMA_VERSION_V16",
    "LEAN_TOOL_SCHEMA_VERSION_V17",
    "LEAN_TOOL_SCHEMA_VERSION_V18",
    "LEAN_TOOL_SCHEMA_VERSION_V19",
    "LEAN_TOOL_SCHEMA_VERSION_V20",
    "LEAN_TOOL_SCHEMA_VERSION_V21",
    "LEAN_TOOL_SCHEMA_VERSION_V22",
    "LEAN_TOOL_SCHEMA_VERSION_V23",
    "LEAN_TOOL_SCHEMA_VERSION_V24",
    "LEAN_TOOL_SCHEMA_VERSION_V25",
    "LEAN_TOOL_SCHEMA_VERSION_V26",
    "LEAN_TOOL_SCHEMA_VERSION_V27",
    "LEAN_TOOL_SCHEMA_VERSION_V28",
    "LeanHarnessAssembledRequest",
    "LeanHarnessDependencies",
    "LeanHarnessRequestEvidence",
    "LeanHarnessRequestEvidenceV2",
    "LeanHarnessRequestEvidenceV3",
    "LeanHarnessRequestEvidenceV4",
    "LeanHarnessRequestEvidenceV5",
    "LeanHarnessRequestEvidenceV6",
    "LeanHarnessRequestEvidenceV7",
    "LeanHarnessRequestEvidenceV8",
    "LeanHarnessRequestEvidenceV9",
    "LeanHarnessRequestEvidenceV10",
    "LeanHarnessRequestEvidenceV11",
    "LeanHarnessRequestEvidenceV12",
    "LeanHarnessRequestEvidenceV13",
    "LeanHarnessRequestEvidenceV14",
    "LeanHarnessRequestEvidenceV15",
    "LeanHarnessRequestEvidenceV16",
    "LeanHarnessRequestEvidenceV17",
    "LeanHarnessRequestEvidenceV18",
    "LeanHarnessRequestEvidenceV19",
    "LeanHarnessRequestEvidenceV20",
    "LeanHarnessRequestEvidenceV21",
    "LeanHarnessRequestEvidenceV22",
    "LeanHarnessRequestEvidenceV23",
    "LeanHarnessRequestEvidenceV24",
    "LeanHarnessRequestEvidenceV25",
    "LeanHarnessRequestEvidenceV26",
    "LeanHarnessRequestEvidenceV27",
    "LeanHarnessRequestEvidenceV28",
    "LeanPhaseToolSurface",
    "LeanPhaseToolSurfaceV2",
    "LeanPhaseToolSurfaceV3",
    "LeanPhaseToolSurfaceV4",
    "assemble_lean_harness_request",
    "build_lean_harness_calibration_manifest",
    "load_lean_harness_dependencies",
    "recover_plan_gate_readiness_pins",
    "validate_persisted_lean_harness_request",
]
