"""Constrained, evidence-producing tool gateway."""

from __future__ import annotations

import ast
import copy
import difflib
import fnmatch
import json
import os
import re
import stat
import subprocess
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any

from patchloop.agent.investigation import (
    INSPECTION_ADMISSION_PREFLIGHT_SCHEMA,
    INVESTIGATION_LOOP_SCHEMA,
    INVESTIGATION_POLICY_VERSION,
    TOOL_REPLAY_SCHEMA,
    investigation_policy_version,
    load_inspection_records,
    mutation_epoch,
    nominal_tail_reserve,
    prior_search_match_keys,
    read_coverage,
    reconstruct_covered_read,
    search_match_key,
    tail_policy,
    tool_admission_schema,
    validate_inspection_arguments,
)
from patchloop.agent.mechanical_friction import project_registered_check_outcome
from patchloop.agent.phases import EvidenceState, diff_bound_evidence
from patchloop.agent.provider_schema_admission import (
    STRICT_ANCHORED_READ_POLICY,
    normalize_strict_read_arguments,
    strict_anchored_read_schema,
)
from patchloop.agent.structured_edit import (
    STRUCTURED_EDIT_TOOL_NAME,
    STRUCTURED_EDIT_TOOL_SCHEMA_V2,
    AtomicStructuredEditProjection,
    FreshStructuredEditArguments,
    FreshStructuredEditProjection,
    StructuredEditArguments,
    project_atomic_structured_edit,
    project_fresh_atomic_structured_edit,
)
from patchloop.agent.structured_edit_replay import (
    StructuredEditGatewayPatch,
    render_structured_edit_gateway_patch,
)
from patchloop.agent.workflow_candidate_binding_successor import (
    CANDIDATE_BINDING_POLICY_V16,
    CandidateBindingNormalization,
    validate_work_plan_v16,
)
from patchloop.agent.workflow_causal_alternative_activation import (
    CAUSAL_ACTIVATION_POLICY,
    RESTORE_COMPLETED_EVENT_SCHEMA,
    RESTORE_PREPARED_EVENT_SCHEMA,
    CausalWorkPlanBinding,
    CrossResetFailureTrigger,
    build_causal_work_plan_binding,
    build_cross_reset_failure_trigger,
    causal_plan_binding_for_hash,
    causal_reset_gate_id,
    cross_reset_epoch_events,
    project_active_cross_reset_trigger,
    project_causal_mechanism_history,
    project_cross_reset_semantic_progress_state,
    standard_plan_from_causal_alternative,
)
from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
    CausalMechanismHistoryEntry,
    MutationBaselineProjection,
    MutationBaselineRestoreReceipt,
    PublicCausalMechanism,
    RecordedCausalAlternativePlan,
    project_mutation_baseline,
    record_mutation_baseline_restore,
    validate_causal_alternative_plan,
    validate_public_causal_mechanism,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY,
    ActivatedCausalPlanRequest,
    CausalMechanismHistoryEntryV2,
    CausalWorkPlanBindingV2,
    build_causal_work_plan_binding_v2,
    causal_plan_binding_for_hash_v2,
    normalize_activated_causal_plan,
    project_causal_mechanism_history_v2,
    standard_plan_from_projected_causal_plan,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    PublicCausalMechanismV2,
    RecordedCausalPlanV2,
)
from patchloop.agent.workflow_exploration_gate_activation import (
    ActivatedExplorationPlanRequest,
    exploration_binding_for_hash,
    exploration_closure_event_payload,
    normalize_activated_exploration_plan,
)
from patchloop.agent.workflow_exploration_gate_successor import (
    PublicExplorationClosureReceipt,
    build_exploration_work_plan_binding,
)
from patchloop.agent.workflow_lifecycle_binding_successor import (
    LIFECYCLE_COMPONENT_BINDING_POLICY,
    LifecycleComponentBoundPlanRequest,
    RecordedLifecycleComponentBinding,
    normalize_lifecycle_component_bound_plan,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    TriggerBoundSelfDirectedPlanRequest,
    normalize_trigger_bound_self_directed_plan,
)
from patchloop.agent.workflow_plan_gate_liveness_successor import (
    EligiblePlanEvidenceCatalogV3,
    PinnedExplorationPlanRequest,
    normalize_pinned_exploration_plan,
)
from patchloop.agent.workflow_r21_reliability_successor import (
    ANCHORED_READ_POLICY,
    LIFECYCLE_PLAN_POLICY,
    LifecycleBoundPlanRequest,
    RecordedLifecycleStateTransition,
    normalize_lifecycle_bound_plan,
    resolve_anchored_read,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SELF_DIRECTED_EXPLORATION_POLICY,
    EligiblePlanEvidenceCatalogV4,
    SelfDirectedExplorationClosureReceipt,
    SelfDirectedExplorationState,
    SelfDirectedPlanRequest,
    WorkflowDecisionV4,
    build_self_directed_work_plan_binding,
    normalize_self_directed_plan,
    project_episode_investigation_target_hashes,
    project_investigation_target,
    self_directed_binding_for_hash,
    self_directed_closure_event_payload,
    validate_investigation_action,
)
from patchloop.agent.workflow_semantic_progress_epoch_parity import (
    SemanticProgressEventDomain,
    select_semantic_progress_epoch_events,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    PublicSemanticProgressState,
    WorkflowDecisionV3,
    current_public_failure_event_sequence,
    project_public_semantic_progress_state,
    validate_semantic_progress_revision,
)
from patchloop.agent.workflow_successor import (
    PLAN_RECORDED_EVENT_SCHEMA,
    RecordedWorkPlan,
    validate_record_work_plan,
)
from patchloop.agent.workflow_successor_v2 import (
    PLAN_RECORDED_EVENT_SCHEMA_V2,
    WORK_PLAN_ADMISSION_POLICY,
    ActiveWorkState,
    EligiblePlanEvidenceCatalog,
    EligiblePlanEvidenceCatalogV2,
    RecordedWorkPlanV2,
    WorkflowDecisionV2,
    project_active_work_state,
    validate_work_plan_v2,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Checkpoint,
    EventType,
    FaultSpec,
    Phase,
    PublicReviewCoverageTarget,
    PublicTask,
    RegisteredProbeProfile,
    ToolResult,
)
from patchloop.errors import (
    ContractError,
    ControlledDiagnosticRejection,
    CoverageCitationError,
    PolicyViolation,
    RecoveryError,
    WorkPlanAdmissionRejectedError,
)
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import Sandbox, probe_execution_policy
from patchloop.state import StateStore
from patchloop.util import (
    canonical_json,
    ensure_within,
    safe_relative_path,
    sha256_bytes,
    sha256_json,
    sha256_text,
    utc_now,
)
from patchloop.verifier.policy import (
    verify_dependencies,
    verify_public_api,
    verify_scope,
    verify_test_tampering,
)

TOOL_SCHEMAS_V1: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_files",
        "description": "Search repository text files for a literal query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path_glob": {"type": "string", "default": "**/*"},
            },
            "required": ["query", "path_glob"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a bounded range from a repository file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path", "start_line", "end_line"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "apply_patch",
        "description": (
            "Apply a raw Git unified diff to existing tracked text files within "
            "the task's allowed paths. New files, renames, copies, and binary "
            "patches are not supported. "
            "The patch must begin with 'diff --git' and contain ---/+++/@@ lines. "
            "Do not use '*** Begin Patch' or '*** End Patch' markers."
        ),
        "parameters": {
            "type": "object",
            "properties": {"patch": {"type": "string"}},
            "required": ["patch"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "run_check",
        "description": "Run one task-registered public check by ID.",
        "parameters": {
            "type": "object",
            "properties": {"check_id": {"type": "string"}},
            "required": ["check_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_diff",
        "description": "Return the current Git diff and size summary.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
]

TOOL_SCHEMAS_V2: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V1)
next(item for item in TOOL_SCHEMAS_V2 if item["name"] == "run_check")["description"] = (
    "Run one task-registered public check by ID. A passing result is valid only "
    "for the exact current worktree diff; any later patch requires another check."
)
next(item for item in TOOL_SCHEMAS_V2 if item["name"] == "get_diff")["description"] = (
    "Return the current Git diff and size summary. Call this after all registered "
    "checks pass for the current diff so the next turn can perform final review."
)
TOOL_SCHEMAS_V2.append(
    {
        "type": "function",
        "name": "finish_task",
        "description": (
            "Submit the current patch for deterministic evaluation. Call only "
            "after every registered check passes for the current diff and the "
            "complete final get_diff result has been reviewed in this turn."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    }
)
TOOL_SCHEMAS_V3: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V2)
finish_index = next(
    index for index, item in enumerate(TOOL_SCHEMAS_V3) if item["name"] == "finish_task"
)
TOOL_SCHEMAS_V3[finish_index:finish_index] = [
    {
        "type": "function",
        "name": "run_probe",
        "description": (
            "Run an ephemeral Python reproducer in the isolated, network-disabled, "
            "read-only sandbox using one task-registered public probe profile. "
            "The source is stored as trace evidence outside the repository and "
            "is never included in the submitted patch."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "probe_id": {"type": "string", "minLength": 1},
                "source": {"type": "string", "minLength": 1, "maxLength": 12000},
            },
            "required": ["probe_id", "source"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "review_task",
        "description": (
            "Record a structured public-requirement review bound to the current "
            "diff and the complete get_diff result shown in this request. Cite "
            "exact event sequences and disclose residual risks."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "requirements": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "requirement": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 1000,
                            },
                            "status": {
                                "type": "string",
                                "enum": [
                                    "verified",
                                    "partially_verified",
                                    "unverified",
                                ],
                            },
                            "evidence_event_sequences": {
                                "type": "array",
                                "maxItems": 20,
                                "items": {"type": "integer", "minimum": 1},
                            },
                            "notes": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 2000,
                            },
                        },
                        "required": [
                            "requirement",
                            "status",
                            "evidence_event_sequences",
                            "notes",
                        ],
                        "additionalProperties": False,
                    },
                },
                "targeted_validation": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": [
                                    "probe",
                                    "registered_check",
                                    "repository_evidence",
                                ],
                            },
                            "event_sequence": {
                                "type": "integer",
                                "minimum": 1,
                            },
                            "outcome": {
                                "type": "string",
                                "enum": ["passed", "failed", "inconclusive"],
                            },
                            "notes": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 2000,
                            },
                        },
                        "required": [
                            "kind",
                            "event_sequence",
                            "outcome",
                            "notes",
                        ],
                        "additionalProperties": False,
                    },
                },
                "residual_risks": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1000,
                    },
                },
            },
            "required": [
                "requirements",
                "targeted_validation",
                "residual_risks",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
next(item for item in TOOL_SCHEMAS_V3 if item["name"] == "finish_task")["description"] = (
    "Submit the current patch for deterministic evaluation. Call only after "
    "registered checks, complete get_diff review, and a same-diff review_task "
    "artifact have all been presented on the required turns."
)
TOOL_SCHEMAS_V4: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V3)
next(item for item in TOOL_SCHEMAS_V4 if item["name"] == "apply_patch")["description"] = (
    "Apply one raw Git unified diff to existing tracked text files within the "
    "task's allowed paths. This call is a turn barrier: any later tool calls "
    "from the same model response are recorded as not executed. Every hunk "
    "header must use numeric unified-diff ranges such as "
    "'@@ -12,3 +12,4 @@'. New files, renames, copies, binary patches, and "
    "'*** Begin Patch' markers are not supported."
)
review_v4 = next(item for item in TOOL_SCHEMAS_V4 if item["name"] == "review_task")
review_v4["description"] = (
    "Assess every requirement_id in the hash-bound public_review_contract "
    "exactly once against current-diff evidence. Cite exact event sequences "
    "and map every partially_verified or unverified item to a residual risk."
)
review_v4["parameters"]["properties"]["requirements"]["items"] = {
    "type": "object",
    "properties": {
        "requirement_id": {
            "type": "string",
            "pattern": "^req-[0-9a-f]{12}$",
        },
        "status": {
            "type": "string",
            "enum": ["verified", "partially_verified", "unverified"],
        },
        "evidence_event_sequences": {
            "type": "array",
            "maxItems": 20,
            "items": {"type": "integer", "minimum": 1},
        },
        "notes": {
            "type": "string",
            "minLength": 1,
            "maxLength": 2000,
        },
    },
    "required": [
        "requirement_id",
        "status",
        "evidence_event_sequences",
        "notes",
    ],
    "additionalProperties": False,
}
review_v4["parameters"]["properties"]["residual_risks"] = {
    "type": "array",
    "maxItems": 20,
    "items": {
        "type": "object",
        "properties": {
            "requirement_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {
                    "type": "string",
                    "pattern": "^req-[0-9a-f]{12}$",
                },
            },
            "risk": {"type": "string", "minLength": 1, "maxLength": 1000},
            "mitigation": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1000,
            },
        },
        "required": ["requirement_ids", "risk", "mitigation"],
        "additionalProperties": False,
    },
}
TOOL_SCHEMAS_V5: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V4)
review_v5 = next(item for item in TOOL_SCHEMAS_V5 if item["name"] == "review_task")
review_v5["description"] = (
    "Assess every public requirement and every coverage_target_id exactly once. "
    "Use only the target-specific event sequences advertised by review_evidence. "
    "A partial or unverified target is preserved as review evidence but prevents "
    "submission and returns the run to corrective investigation."
)
review_v5["parameters"]["properties"]["coverage_targets"] = {
    "type": "array",
    "minItems": 1,
    "maxItems": 20,
    "items": {
        "type": "object",
        "properties": {
            "coverage_target_id": {
                "type": "string",
                "pattern": "^cov-[0-9a-f]{12}$",
            },
            "status": {
                "type": "string",
                "enum": ["verified", "partially_verified", "unverified"],
            },
            "evidence_event_sequences": {
                "type": "array",
                "maxItems": 20,
                "items": {"type": "integer", "minimum": 1},
            },
            "notes": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2000,
            },
        },
        "required": [
            "coverage_target_id",
            "status",
            "evidence_event_sequences",
            "notes",
        ],
        "additionalProperties": False,
    },
}
review_v5["parameters"]["required"] = [
    "requirements",
    "coverage_targets",
    "targeted_validation",
    "residual_risks",
]
next(item for item in TOOL_SCHEMAS_V5 if item["name"] == "finish_task")["description"] = (
    "Submit the current patch for deterministic evaluation only after every "
    "public coverage target is verified in a same-diff task-review-v3 artifact."
)
TOOL_SCHEMAS_V6: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V5)
next(item for item in TOOL_SCHEMAS_V6 if item["name"] == "review_task")["description"] = (
    "Assess every public requirement and every coverage_target_id exactly once. "
    "Use only the target-specific event sequences advertised by review_evidence. "
    "If a target citation is rejected, follow the target-specific structured "
    "feedback and obtain the required current-diff evidence before retrying. A "
    "partial or unverified target is preserved as review evidence but prevents "
    "submission and returns the run to corrective investigation."
)
TOOL_SCHEMAS_V7: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V2)
TOOL_SCHEMAS_V8: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V7)
next(item for item in TOOL_SCHEMAS_V8 if item["name"] == "apply_patch")["description"] = (
    "Apply one raw Git unified diff to existing tracked text files within the "
    "task's allowed paths. A standalone outer '*** Begin Patch' or "
    "'*** End Patch' wrapper, CRLF transport, and a missing terminal newline "
    "are normalized and recorded before validation. Non-Git wrapper formats, "
    "malformed hunks, stale context, new files, renames, copies, and binary "
    "patches are rejected with a typed correction reason."
)
TOOL_SCHEMAS_V9: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V8)
search_v9 = next(item for item in TOOL_SCHEMAS_V9 if item["name"] == "search_files")
search_v9["description"] = (
    "Search repository text files for a literal query. Use '**/*' for all "
    "recursive files and '**/*.py' for recursive Python files. A path_glob "
    "equal to '**' or ending in '/**' is normalized to include descendant "
    "files, and the raw and executed patterns are recorded in the result."
)
search_v9["parameters"]["properties"]["path_glob"]["description"] = (
    "Safe repository-relative glob. Canonical recursive examples are '**/*' "
    "and '**/*.py'; a terminal '/**' is accepted and normalized to '/**/*'."
)
TOOL_SCHEMAS_V10: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V9)
next(item for item in TOOL_SCHEMAS_V10 if item["name"] == "run_check")["description"] = (
    "Execute one registered public check on the current diff. Tool invocation "
    "success only means the check process completed; inspect behavior_status "
    "and passed. behavior_status='failed' requires one bounded correction using "
    "failure_summary, followed by the same current-diff check again."
)
TOOL_SCHEMAS_V11: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V10)
next(item for item in TOOL_SCHEMAS_V11 if item["name"] == "apply_patch")["description"] = (
    "Apply one raw Git unified diff to existing tracked text files within the "
    "task's allowed paths. Safe outer wrappers and transport newlines are "
    "normalized, but hunks are never invented. On rejection, follow the typed "
    "edit_correction reason and bounded current-source excerpt; regenerate from "
    "that exact preimage instead of replaying stale context."
)
TOOL_SCHEMAS_V12: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V11)
next(item for item in TOOL_SCHEMAS_V12 if item["name"] == "run_check")["description"] = (
    "Execute exactly the one registered public check bound in this request. "
    "Invocation success means only that the process completed; inspect "
    "behavior_status and passed before advancing to the next check."
)
TOOL_SCHEMAS_V13: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V12)
TOOL_SCHEMAS_V13.append(copy.deepcopy(STRUCTURED_EDIT_TOOL_SCHEMA_V2))
next(item for item in TOOL_SCHEMAS_V13 if item["name"] == "apply_structured_edit")[
    "description"
] = (
    "Apply one smallest current-source structured edit. After a failed public "
    "check this tool is exposed only after a fresh current-diff read; a "
    "rejected edit invalidates that read and requires another read."
)
TOOL_SCHEMAS_V14: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V13)
record_plan_index = next(
    index for index, item in enumerate(TOOL_SCHEMAS_V14) if item["name"] == "apply_patch"
)
TOOL_SCHEMAS_V14[record_plan_index:record_plan_index] = [
    {
        "type": "function",
        "name": "record_work_plan",
        "description": (
            "Record one bounded implementation plan using only public current-run, "
            "current-diff read/check evidence. Every candidate file must already "
            "have been read and planned_check_ids must exactly match public order."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reproduction_status": {
                    "type": "string",
                    "enum": [
                        "confirmed_failure",
                        "not_reproduced",
                        "static_evidence",
                    ],
                },
                "hypothesis": {"type": "string", "minLength": 1, "maxLength": 2000},
                "evidence_event_sequences": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "integer", "minimum": 1},
                },
                "candidate_files": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string", "minLength": 1},
                },
                "planned_check_ids": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string", "minLength": 1},
                },
                "unknowns": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {"type": "string", "minLength": 1, "maxLength": 1000},
                },
            },
            "required": [
                "reproduction_status",
                "hypothesis",
                "evidence_event_sequences",
                "candidate_files",
                "planned_check_ids",
                "unknowns",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    }
]
TOOL_SCHEMAS_V15: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V13)
record_plan_v2_index = next(
    index for index, item in enumerate(TOOL_SCHEMAS_V15) if item["name"] == "apply_patch"
)
_WORK_PLAN_V2_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "observation_status": {"type": "string"},
        "hypothesis": {"type": "string", "minLength": 1, "maxLength": 2000},
        "foundation_evidence_ids": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {"type": "string"},
        },
        "supporting_evidence_ids": {
            "type": "array",
            "maxItems": 20,
            "items": {"type": "string"},
        },
        "candidate_files": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "read_evidence_id": {"type": "string"},
                },
                "required": ["path", "read_evidence_id"],
                "additionalProperties": False,
            },
        },
        "intended_change": {"type": "string", "minLength": 1, "maxLength": 2000},
        "expected_behavior": {"type": "string", "minLength": 1, "maxLength": 2000},
        "unknowns": {
            "type": "array",
            "maxItems": 20,
            "items": {"type": "string", "minLength": 1, "maxLength": 1000},
        },
    },
    "required": [
        "observation_status",
        "hypothesis",
        "foundation_evidence_ids",
        "supporting_evidence_ids",
        "candidate_files",
        "intended_change",
        "expected_behavior",
        "unknowns",
    ],
    "additionalProperties": False,
}
TOOL_SCHEMAS_V15[record_plan_v2_index:record_plan_v2_index] = [
    {
        "type": "function",
        "name": "record_work_plan",
        "description": (
            "Record one initial public work plan. Use only the exact eligible evidence IDs "
            "and candidate paths enumerated in this request; check order is server-derived."
        ),
        "parameters": copy.deepcopy(_WORK_PLAN_V2_PARAMETERS),
        "strict": True,
    }
]
TOOL_SCHEMAS_V16: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V15)
revise_parameters = copy.deepcopy(_WORK_PLAN_V2_PARAMETERS)
revise_parameters["properties"]["prior_hypothesis_disposition"] = {
    "type": "string",
    "enum": ["retained", "refined", "rejected"],
}
revise_parameters["required"].append("prior_hypothesis_disposition")
revise_index = next(
    index for index, item in enumerate(TOOL_SCHEMAS_V16) if item["name"] == "apply_patch"
)
TOOL_SCHEMAS_V16[revise_index:revise_index] = [
    {
        "type": "function",
        "name": "revise_work_plan",
        "description": (
            "Record the one required semantic work-plan revision after a visible-check "
            "failure or before a review correction. Trigger identity is server-derived."
        ),
        "parameters": revise_parameters,
        "strict": True,
    }
]
TOOL_SCHEMAS_V17: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V16)
TOOL_SCHEMAS_V18: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V17)
TOOL_SCHEMAS_V19: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V18)
TOOL_SCHEMAS_V20: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V19)
TOOL_SCHEMAS_V21: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V20)
TOOL_SCHEMAS_V22: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V21)
TOOL_SCHEMAS_V23: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V22)
TOOL_SCHEMAS_V24: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V23)
TOOL_SCHEMAS_V25: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V24)
TOOL_SCHEMAS_V26: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V25)
TOOL_SCHEMAS_V26.append(
    {
        "type": "function",
        "name": "declare_exploration_exhausted",
        "description": (
            "Stop without mutation or submission when the bounded public exploration "
            "budget is exhausted and the currently visible source evidence is insufficient."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["not_ready"]},
                "blocking_question": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1_000,
                },
                "basis_source_span_ids": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "items": {"type": "string"},
                },
                "reason": {
                    "type": "string",
                    "enum": ["evidence_budget_exhausted"],
                },
            },
            "required": [
                "status",
                "blocking_question",
                "basis_source_span_ids",
                "reason",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    }
)
TOOL_SCHEMAS_V27: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V26)
read_v27 = next(item for item in TOOL_SCHEMAS_V27 if item["name"] == "read_file")
read_v27["description"] = (
    "Read either one explicit public source range or one server-resolved range centered "
    "on an exact prior search match. Supply exactly path/start_line/end_line or "
    "search_anchor; never guess a range after choosing a search match."
)
read_v27["parameters"]["properties"]["search_anchor"] = {
    "type": "object",
    "properties": {
        "search_event_sequence": {"type": "integer", "minimum": 1},
        "match_index": {"type": "integer", "minimum": 0, "maximum": 99},
        "before_lines": {"type": "integer", "minimum": 0, "maximum": 100},
        "after_lines": {"type": "integer", "minimum": 0, "maximum": 100},
    },
    "required": ["search_event_sequence", "match_index", "before_lines", "after_lines"],
    "additionalProperties": False,
}
read_v27["parameters"]["required"] = []
TOOL_SCHEMAS_V28: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V27)
for tool_v28 in TOOL_SCHEMAS_V28:
    if tool_v28["name"] == "read_file":
        tool_v28.update(strict_anchored_read_schema(tool_v28))
    elif tool_v28["parameters"].get("properties") == {}:
        tool_v28["parameters"]["required"] = []
TOOL_SCHEMAS_V29: list[dict[str, Any]] = copy.deepcopy(TOOL_SCHEMAS_V28)
TOOL_SCHEMAS = TOOL_SCHEMAS_V2

_EVENT_ERROR_MESSAGE_LIMIT = 2_000
_INVESTIGATION_CONTEXT_POLICIES = {
    "phase-evidence-v4",
    "phase-evidence-v5",
    "phase-evidence-v6",
    "phase-evidence-v7",
    "phase-evidence-v8",
    "phase-evidence-v9",
    "phase-evidence-v10",
    "phase-evidence-v11",
    "phase-evidence-v12",
    "phase-evidence-v13",
    "phase-evidence-v14",
    "phase-evidence-v15",
    "phase-evidence-v16",
    "phase-evidence-v17",
    "phase-evidence-v18",
    "phase-evidence-v19",
    "phase-evidence-v20",
    "phase-evidence-v21",
    "phase-evidence-v22",
    "phase-evidence-v23",
    "phase-evidence-v24",
    "phase-evidence-v25",
    "phase-evidence-v26",
    "phase-evidence-v27",
    "phase-evidence-v28",
    "phase-evidence-v29",
    "phase-evidence-v30",
    "phase-evidence-v31",
    "phase-evidence-v32",
    "phase-evidence-v33",
    "phase-evidence-v34",
    "phase-evidence-v35",
    "phase-evidence-v36",
    "phase-evidence-v37",
    "phase-evidence-v38",
}
_TOKEN_TAIL_CONTEXT_POLICIES = {
    "phase-evidence-v5",
    "phase-evidence-v6",
    "phase-evidence-v7",
    "phase-evidence-v8",
    "phase-evidence-v9",
    "phase-evidence-v10",
    "phase-evidence-v11",
    "phase-evidence-v12",
    "phase-evidence-v13",
    "phase-evidence-v14",
    "phase-evidence-v15",
    "phase-evidence-v16",
    "phase-evidence-v17",
    "phase-evidence-v18",
    "phase-evidence-v19",
    "phase-evidence-v20",
    "phase-evidence-v21",
    "phase-evidence-v22",
    "phase-evidence-v23",
    "phase-evidence-v24",
    "phase-evidence-v25",
    "phase-evidence-v26",
    "phase-evidence-v27",
    "phase-evidence-v28",
    "phase-evidence-v29",
    "phase-evidence-v30",
    "phase-evidence-v31",
    "phase-evidence-v32",
    "phase-evidence-v33",
    "phase-evidence-v34",
    "phase-evidence-v35",
    "phase-evidence-v36",
    "phase-evidence-v37",
    "phase-evidence-v38",
}
_STRUCTURED_TOOL_SCHEMAS = {
    "v2",
    "v3",
    "v4",
    "v5",
    "v6",
    "v7",
    "v8",
    "v9",
    "v10",
    "v11",
    "v12",
    "v13",
    "v14",
    "v15",
    "v16",
    "v17",
    "v18",
    "v19",
    "v20",
    "v21",
    "v22",
    "v23",
    "v24",
    "v25",
    "v26",
    "v27",
    "v28",
    "v29",
}
_SELF_VALIDATION_TOOL_SCHEMAS = {"v3", "v4", "v5", "v6"}
_PATCH_RETRY_TOOL_SCHEMAS = {
    "v4",
    "v5",
    "v6",
    "v7",
    "v8",
    "v9",
    "v10",
    "v11",
    "v12",
    "v13",
    "v14",
    "v15",
    "v16",
    "v17",
    "v18",
    "v19",
    "v20",
    "v21",
    "v22",
    "v23",
    "v24",
    "v25",
    "v26",
    "v27",
    "v28",
    "v29",
}
_SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS = {
    "v8",
    "v9",
    "v10",
    "v11",
    "v12",
    "v13",
    "v14",
    "v15",
    "v16",
    "v17",
    "v18",
    "v19",
    "v20",
    "v21",
    "v22",
    "v23",
    "v24",
    "v25",
    "v26",
    "v27",
    "v28",
    "v29",
}
_SEARCH_GLOB_NORMALIZATION_TOOL_SCHEMAS = {
    "v9",
    "v10",
    "v11",
    "v12",
    "v13",
    "v14",
    "v15",
    "v16",
    "v17",
    "v18",
    "v19",
    "v20",
    "v21",
    "v22",
    "v23",
    "v24",
    "v25",
    "v26",
    "v27",
    "v28",
    "v29",
}
_SEARCH_GLOB_NORMALIZATION_POLICY_VERSION = "recursive-file-glob-normalization-v1"
_MUTATION_TOOL_NAMES = {"apply_patch", STRUCTURED_EDIT_TOOL_NAME}
_PROBE_SOURCE_LIMIT_BYTES = 12_000
_PROBE_OUTPUT_LIMIT_BYTES = 64_000
_REVIEW_INPUT_LIMIT_BYTES = 8_000
_PATCH_SOURCE_MAX_ENTRIES = 8
_PATCH_SOURCE_MAX_LINES_PER_ENTRY = 120
_PATCH_SOURCE_MAX_CHARACTERS = 24_000
_EDIT_CORRECTION_MAX_FILES = 4
_EDIT_CORRECTION_MAX_EXCERPTS = 8
_EDIT_CORRECTION_MAX_CHARACTERS = 12_000
_EDIT_CORRECTION_CONTEXT_LINES = 4
_EVIDENCE_SATURATION_THRESHOLD = 6
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")
_PROBE_DENIED_IMPORT_ROOTS = {
    "_posixsubprocess",
    "commands",
    "ctypes",
    "importlib",
    "multiprocessing",
    "os",
    "pty",
    "runpy",
    "subprocess",
}
_PROBE_DENIED_CALL_NAMES = {
    "__import__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
}
_PROBE_DENIED_ATTRIBUTE_NAMES = {
    "CDLL",
    "Popen",
    "PyDLL",
    "__builtins__",
    "__code__",
    "__globals__",
    "__import__",
    "__subclasses__",
    "fork",
    "forkpty",
    "kill",
    "killpg",
    "popen",
    "pythonapi",
    "system",
}
_PROBE_DENIED_ATTRIBUTE_PREFIXES = (
    "exec",
    "posix_spawn",
    "spawn",
)
_UNSUPPORTED_PATCH_METADATA = (
    "new file mode ",
    "old mode ",
    "new mode ",
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
)
_PATCH_WRAPPER_MARKERS = {"*** Begin Patch", "*** End Patch"}
_PATCH_WRAPPER_DIRECTIVES = (
    "*** Add File:",
    "*** Delete File:",
    "*** Move to:",
    "*** Update File:",
)


def _validate_probe_source_policy(source: str) -> None:
    """Reject source-level access to process and dynamic-code capabilities."""

    try:
        tree = ast.parse(source, filename="<patchloop-probe>", mode="exec")
    except SyntaxError as exc:
        raise ContractError(f"run_probe source is not valid Python: {exc.msg}") from exc

    def reject(node: ast.AST, capability: str) -> None:
        raise PolicyViolation(
            "run_probe source requests a forbidden execution capability",
            details={
                "stage": "probe",
                "reason": "probe_source_policy_violation",
                "capability": capability,
                "line": getattr(node, "lineno", None),
                "column": getattr(node, "col_offset", None),
                "guidance": (
                    "Use pure Python assertions and repository imports only. "
                    "Direct process, OS-command, native-loading, and "
                    "dynamic-code constructs are rejected before dispatch; "
                    "the Docker kernel boundary is authoritative."
                ),
            },
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in _PROBE_DENIED_IMPORT_ROOTS:
                    reject(node, f"import:{root}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in _PROBE_DENIED_IMPORT_ROOTS:
                reject(node, f"import:{root}")
        elif isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name) and function.id in _PROBE_DENIED_CALL_NAMES:
                reject(node, f"call:{function.id}")
            if (
                isinstance(function, ast.Name)
                and function.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value
                in {
                    "__import__",
                    "compile",
                    "eval",
                    "exec",
                }
            ):
                reject(
                    node,
                    f"dynamic-lookup:{node.args[1].value}",
                )
            if isinstance(function, ast.Attribute):
                attribute = function.attr
                if attribute in _PROBE_DENIED_ATTRIBUTE_NAMES or attribute.startswith(
                    _PROBE_DENIED_ATTRIBUTE_PREFIXES
                ):
                    reject(node, f"call-attribute:{attribute}")
        elif isinstance(node, ast.Attribute) and node.attr in {
            "__builtins__",
            "__code__",
            "__globals__",
            "__subclasses__",
        }:
            reject(node, f"attribute:{node.attr}")
        elif isinstance(node, ast.Name) and node.id == "__builtins__":
            reject(node, "name:__builtins__")


def _header_path(header: str) -> str:
    path = header[4:].split("\t", 1)[0]
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def _patch_contract_error(
    message: str,
    *,
    reason: str,
    stage: str = "format",
    line: int | None = None,
    guidance: str | None = None,
    extra_details: dict[str, Any] | None = None,
) -> ContractError:
    details: dict[str, Any] = {
        "stage": stage,
        "reason": reason,
        "guidance": guidance
        or (
            "Regenerate a raw Git unified diff against the current file content, "
            "then retry with a new action_id."
        ),
    }
    if line is not None:
        details["line"] = line
    if extra_details:
        details.update(extra_details)
    return ContractError(message, details=details)


def _normalize_raw_git_patch(patch: str) -> tuple[str, dict[str, Any]]:
    """Normalize only transport-level raw-diff defects; never synthesize hunks."""

    if type(patch) is not str:
        raise TypeError("apply_patch patch must be an exact string")
    normalized_line_endings = patch.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized_line_endings.splitlines()
    removed_markers: list[str] = []

    first_content = next(
        (index for index, line in enumerate(lines) if line.strip()),
        None,
    )
    if first_content is not None and lines[first_content].strip() == "*** Begin Patch":
        removed_markers.append("begin")
        del lines[first_content]

    last_content = next(
        (index for index in range(len(lines) - 1, -1, -1) if lines[index].strip()),
        None,
    )
    if last_content is not None and lines[last_content].strip() == "*** End Patch":
        removed_markers.append("end")
        del lines[last_content]

    normalized = "\n".join(lines)
    terminal_newline_added = bool(
        normalized and not normalized_line_endings.endswith("\n") and "end" not in removed_markers
    )
    if normalized:
        normalized += "\n"
    body: dict[str, Any] = {
        "schema_version": "raw-git-patch-normalization-v1",
        "policy_version": "safe-raw-diff-normalization-v1",
        "changed": normalized != patch,
        "line_endings_normalized": normalized_line_endings != patch,
        "removed_outer_markers": tuple(removed_markers),
        "terminal_newline_added": terminal_newline_added,
        "raw_patch_hash": sha256_text(patch),
        "normalized_patch_hash": sha256_text(normalized),
    }
    body["content_hash"] = sha256_text(canonical_json(body))
    return normalized, body


def _validate_raw_git_patch(
    patch: str,
    *,
    diagnose_hunk_headers: bool = False,
    diagnose_wrappers: bool = False,
) -> None:
    if "\x00" in patch or "GIT binary patch" in patch or "Binary files " in patch:
        raise _patch_contract_error(
            "apply_patch accepts text patches only; binary patches are forbidden",
            reason="binary_patch",
        )
    if not patch.lstrip().startswith("diff --git "):
        raise _patch_contract_error(
            "apply_patch requires a raw Git unified diff beginning with "
            "'diff --git'; do not use '*** Begin Patch' markers",
            reason="invalid_envelope",
        )
    if diagnose_wrappers:
        for line_number, line in enumerate(patch.splitlines(), 1):
            candidate = line.rstrip()
            if candidate in _PATCH_WRAPPER_MARKERS or candidate.startswith(
                _PATCH_WRAPPER_DIRECTIVES
            ):
                raise _patch_contract_error(
                    "apply_patch found a non-Git patch wrapper inside the raw diff",
                    reason="invalid_wrapper_position",
                    stage="syntax",
                    line=line_number,
                    guidance=(
                        "Send only the raw 'diff --git' document. The v8 gateway "
                        "can remove standalone outer Begin/End markers, but it "
                        "does not translate Update/Add/Delete wrapper directives."
                    ),
                )

    sections: list[list[str]] = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
        elif line.strip():
            raise _patch_contract_error(
                "apply_patch does not allow content before the first diff header",
                reason="content_before_header",
            )

    for section in sections:
        if any(line.startswith(_UNSUPPORTED_PATCH_METADATA) for line in section):
            raise _patch_contract_error(
                "apply_patch only supports in-place tracked text changes; "
                "new files, mode/symlink changes, renames, and copies "
                "are forbidden",
                reason="unsupported_metadata",
            )
        old_header = next(
            (index for index, line in enumerate(section) if line.startswith("--- ")),
            None,
        )
        new_header = next(
            (index for index, line in enumerate(section) if line.startswith("+++ ")),
            None,
        )
        hunk_candidates = [
            (index, line) for index, line in enumerate(section) if line.startswith("@@")
        ]
        if diagnose_hunk_headers:
            malformed = next(
                (
                    (index, line)
                    for index, line in hunk_candidates
                    if _HUNK_HEADER.fullmatch(line) is None
                ),
                None,
            )
            if malformed is not None:
                index, header = malformed
                raise _patch_contract_error(
                    "apply_patch hunk headers require numeric old and new ranges; "
                    "use a header such as '@@ -12,3 +12,4 @@'",
                    reason="invalid_hunk_header",
                    line=index + 1,
                    guidance=(
                        "Regenerate the hunk against the current source and use "
                        "the exact form '@@ -<old_start>,<old_count> "
                        "+<new_start>,<new_count> @@'."
                    ),
                    extra_details={"header": header[:200]},
                )
        hunk_header = (
            hunk_candidates[0][0]
            if diagnose_hunk_headers and hunk_candidates
            else next(
                (index for index, line in enumerate(section) if line.startswith("@@ ")),
                None,
            )
        )
        if (
            old_header is None
            or new_header is None
            or hunk_header is None
            or not old_header < new_header < hunk_header
        ):
            raise _patch_contract_error(
                "each diff section must contain ordered '---', '+++', and '@@' "
                "headers; binary and metadata-only patches are forbidden",
                reason="missing_ordered_headers",
            )
        old_path = _header_path(section[old_header])
        new_path = _header_path(section[new_header])
        if old_path == "/dev/null":
            raise _patch_contract_error(
                "apply_patch only supports tracked files; new-file patches are forbidden",
                reason="new_file",
            )
        if new_path != "/dev/null" and old_path != new_path:
            raise _patch_contract_error(
                "apply_patch only supports in-place changes; rename and copy patches are forbidden",
                reason="path_change",
            )


def _git_apply_contract_error(message: str, error: str) -> ContractError:
    """Translate Git's unstable prose into stable correction categories."""

    line_match = re.search(
        r"(?:corrupt patch at line|patch at line) (\d+)",
        error,
        flags=re.IGNORECASE,
    )
    lowered = error.lower()
    if line_match or any(
        marker in lowered
        for marker in (
            "corrupt patch",
            "malformed patch",
            "unrecognized input",
            "patch fragment without header",
        )
    ):
        return _patch_contract_error(
            message,
            reason="malformed_unified_diff",
            stage="syntax",
            line=(int(line_match.group(1)) if line_match else None),
            guidance=(
                "Regenerate a complete raw Git unified diff. Ensure every "
                "section has diff/---/+++/@@ headers and every hunk line has "
                "a space, '+', '-', or '\\' prefix."
            ),
            extra_details={"git_error": error[:1000]},
        )
    if any(
        marker in lowered
        for marker in (
            "patch failed:",
            "does not apply",
            "while searching for:",
        )
    ):
        return _patch_contract_error(
            message,
            reason="context_mismatch",
            stage="context",
            guidance=(
                "Re-read the current target lines and regenerate the hunk from "
                "that exact source. Do not reuse context from another file or "
                "an earlier worktree state."
            ),
            extra_details={"git_error": error[:1000]},
        )
    return _patch_contract_error(
        message,
        reason="git_apply_failed",
        stage="context",
        extra_details={"git_error": error[:1000]},
    )


def _patch_paths(patch: str) -> list[str]:
    paths: list[str] = []
    sections: list[list[str]] = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
    for section in sections:
        old_header = next(line for line in section if line.startswith("--- "))
        path = safe_relative_path(
            _header_path(old_header),
            field_name="patch path",
        )
        if path in paths:
            raise _patch_contract_error(
                f"patch contains duplicate file section: {path}",
                reason="duplicate_file_section",
            )
        paths.append(path)
    return paths


def _investigation_compat_version(policy_version: str) -> str:
    """Reuse the frozen v6 investigation policy inside the v7 envelope."""

    return (
        "phase-evidence-v6"
        if policy_version
        in {
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
            "phase-evidence-v19",
            "phase-evidence-v20",
            "phase-evidence-v21",
            "phase-evidence-v22",
            "phase-evidence-v23",
            "phase-evidence-v24",
            "phase-evidence-v25",
            "phase-evidence-v26",
            "phase-evidence-v27",
            "phase-evidence-v28",
            "phase-evidence-v29",
            "phase-evidence-v30",
            "phase-evidence-v31",
            "phase-evidence-v32",
            "phase-evidence-v33",
            "phase-evidence-v34",
            "phase-evidence-v35",
            "phase-evidence-v36",
            "phase-evidence-v37",
            "phase-evidence-v38",
        }
        else policy_version
    )


def _evidence_state_from_json(value: Any) -> EvidenceState:
    if not isinstance(value, dict) or set(value) != set(EvidenceState.__dataclass_fields__):
        raise ValueError("phase evidence fields differ")
    tuple_fields = {
        "completed_checks",
        "pending_checks",
        "current_diff_check_event_sequences",
        "unresolved_coverage_target_ids",
        "missing_evidence",
        "allowed_next_actions",
    }
    normalized = {
        key: tuple(item) if key in tuple_fields and isinstance(item, list) else item
        for key, item in value.items()
    }
    state = EvidenceState(**normalized)
    integer_or_none = (
        state.mutation_event_sequence,
        state.latest_check_sequence,
        state.review_event_sequence,
        state.task_review_event_sequence,
    )
    if (
        not isinstance(state.worktree_diff_hash, str)
        or any(item is not None and type(item) is not int for item in integer_or_none)
        or type(state.mutation_present) is not bool
        or type(state.review_presented_to_model) is not bool
        or type(state.task_review_presented_to_model) is not bool
        or (
            state.task_review_coverage_complete is not None
            and type(state.task_review_coverage_complete) is not bool
        )
        or type(state.submission_ready) is not bool
        or any(type(item) is not str for item in state.completed_checks)
        or any(type(item) is not str for item in state.pending_checks)
        or any(type(item) is not int for item in state.current_diff_check_event_sequences)
        or any(type(item) is not str for item in state.unresolved_coverage_target_ids)
        or any(type(item) is not str for item in state.missing_evidence)
        or any(type(item) is not str for item in state.allowed_next_actions)
        or canonical_json(asdict(state)) != canonical_json(value)
    ):
        raise ValueError("phase evidence value types differ")
    return state


class ToolGateway:
    def __init__(
        self,
        *,
        run_id: str,
        workspace: Path,
        task: PublicTask,
        state: StateStore,
        artifacts: ArtifactStore,
        sandbox: Sandbox,
        tool_schema_version: str = "v2",
        context_policy_version: str = "phase-evidence-v3",
        fault: FaultSpec | None = None,
    ) -> None:
        self.run_id = run_id
        self.workspace = workspace
        self.task = task
        self.state = state
        self.artifacts = artifacts
        self.sandbox = sandbox
        self.tool_schema_version = tool_schema_version
        self.context_policy_version = context_policy_version
        self.fault = fault or FaultSpec()

    def prepare_causal_mutation_baseline_restore(
        self,
        phase_evidence: EvidenceState,
    ) -> CrossResetFailureTrigger | None:
        """Persist, but do not execute, one V17 semantic baseline restore."""

        if (self.tool_schema_version, self.context_policy_version) not in {
            ("v21", "phase-evidence-v27"),
            ("v22", "phase-evidence-v28"),
            ("v23", "phase-evidence-v29"),
            ("v24", "phase-evidence-v30"),
            ("v25", "phase-evidence-v31"),
            ("v25", "phase-evidence-v32"),
            ("v26", "phase-evidence-v33"),
            ("v26", "phase-evidence-v34"),
            ("v26", "phase-evidence-v35"),
            ("v27", "phase-evidence-v36"),
            ("v28", "phase-evidence-v37"),
            ("v29", "phase-evidence-v38"),
        }:
            return None
        if type(phase_evidence) is not EvidenceState:
            raise TypeError("causal baseline restore requires exact phase evidence")
        current_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
        if phase_evidence.worktree_diff_hash != current_diff_hash:
            raise RecoveryError("causal baseline phase evidence is stale")
        events = self.state.list_events(self.run_id)
        active = project_active_cross_reset_trigger(
            run_id=self.run_id,
            current_diff_hash=current_diff_hash,
            events=events,
        )
        if active is not None:
            return active
        completed_sequences = {
            int(event.payload.get("restore_prepared_sequence"))
            for event in events
            if event.type == EventType.MUTATION_BASELINE_RESTORED
            and type(event.payload.get("restore_prepared_sequence")) is int
        }
        pending = [
            event
            for event in events
            if event.type == EventType.MUTATION_BASELINE_RESTORE_PREPARED
            and event.sequence not in completed_sequences
        ]
        if len(pending) > 1:
            raise RecoveryError("multiple causal baseline restores are pending")
        if pending:
            return self.reconcile_causal_mutation_baseline_restore()

        epoch = cross_reset_epoch_events(events)
        try:
            failure_sequence = current_public_failure_event_sequence(
                run_id=self.run_id,
                task=self.task,
                evidence=phase_evidence,
                events=epoch,
            )
            semantic_state = project_public_semantic_progress_state(
                run_id=self.run_id,
                task=self.task,
                evidence=phase_evidence,
                events=epoch,
                current_failure_event_sequence=failure_sequence,
            )
        except ContractError as exc:
            raise RecoveryError("causal baseline failure state is unavailable") from exc
        if semantic_state is None or not semantic_state.semantic_reset_required:
            return None
        history = (
            project_causal_mechanism_history_v2(run_id=self.run_id, events=events)
            if self.tool_schema_version in {"v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29"}
            else project_causal_mechanism_history(run_id=self.run_id, events=events)
        )
        if not history:
            raise RecoveryError("causal baseline restore lacks prior causal plan history")
        baseline = project_mutation_baseline(
            semantic_progress_state=semantic_state,
            events=epoch,
        )
        if (
            baseline.current_failed_diff_hash != current_diff_hash
            or WorkspaceManager.untracked_files(self.workspace)
        ):
            raise RecoveryError("causal baseline restore source worktree differs")
        intent_body = {
            "schema_version": RESTORE_PREPARED_EVENT_SCHEMA,
            "policy_version": CAUSAL_ACTIVATION_POLICY,
            "run_id": self.run_id,
            "semantic_progress_state": semantic_state.model_dump(mode="json"),
            "semantic_progress_state_hash": semantic_state.content_hash,
            "baseline_projection": baseline.model_dump(mode="json"),
            "baseline_projection_hash": baseline.content_hash,
            "prior_plan_hash": history[-1].plan_hash,
            "observed_before_diff_hash": current_diff_hash,
            "provider_calls": 0,
            "visible_check_calls": 0,
        }
        intent_artifact = self.artifacts.put_json(intent_body)
        self.state.append_event(
            self.run_id,
            EventType.MUTATION_BASELINE_RESTORE_PREPARED,
            actor="tool-gateway",
            payload={
                **intent_body,
                "intent_artifact": intent_artifact.model_dump(mode="json"),
                "intent_artifact_hash": intent_artifact.content_hash,
                "execution": "prepared_not_started",
            },
        )
        return None

    def reconcile_causal_mutation_baseline_restore(
        self,
    ) -> CrossResetFailureTrigger | None:
        """Idempotently finish one gateway-owned reverse-preimage restore."""

        if (self.tool_schema_version, self.context_policy_version) not in {
            ("v21", "phase-evidence-v27"),
            ("v22", "phase-evidence-v28"),
            ("v23", "phase-evidence-v29"),
            ("v24", "phase-evidence-v30"),
            ("v25", "phase-evidence-v31"),
            ("v25", "phase-evidence-v32"),
            ("v26", "phase-evidence-v33"),
            ("v26", "phase-evidence-v34"),
            ("v26", "phase-evidence-v35"),
            ("v27", "phase-evidence-v36"),
            ("v28", "phase-evidence-v37"),
            ("v29", "phase-evidence-v38"),
        }:
            return None
        events = self.state.list_events(self.run_id)
        current_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
        active = project_active_cross_reset_trigger(
            run_id=self.run_id,
            current_diff_hash=current_diff_hash,
            events=events,
        )
        if active is not None:
            return active
        completed_sequences = {
            int(event.payload.get("restore_prepared_sequence"))
            for event in events
            if event.type == EventType.MUTATION_BASELINE_RESTORED
            and type(event.payload.get("restore_prepared_sequence")) is int
        }
        pending = [
            event
            for event in events
            if event.type == EventType.MUTATION_BASELINE_RESTORE_PREPARED
            and event.sequence not in completed_sequences
        ]
        if not pending:
            return None
        if len(pending) != 1:
            raise RecoveryError("multiple causal baseline restores are pending")
        prepared_restore = pending[0]
        try:
            semantic_state = PublicSemanticProgressState.model_validate_json(
                canonical_json(prepared_restore.payload.get("semantic_progress_state"))
            )
            baseline = MutationBaselineProjection.model_validate_json(
                canonical_json(prepared_restore.payload.get("baseline_projection"))
            )
            intent_artifact = Artifact.model_validate(
                prepared_restore.payload.get("intent_artifact")
            )
            intent_document = json.loads(
                self.artifacts.read_bytes(intent_artifact).decode("utf-8", errors="strict")
            )
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            raise RecoveryError("causal baseline restore intent is invalid") from exc
        expected_intent = {
            "schema_version": RESTORE_PREPARED_EVENT_SCHEMA,
            "policy_version": CAUSAL_ACTIVATION_POLICY,
            "run_id": self.run_id,
            "semantic_progress_state": semantic_state.model_dump(mode="json"),
            "semantic_progress_state_hash": semantic_state.content_hash,
            "baseline_projection": baseline.model_dump(mode="json"),
            "baseline_projection_hash": baseline.content_hash,
            "prior_plan_hash": prepared_restore.payload.get("prior_plan_hash"),
            "observed_before_diff_hash": baseline.current_failed_diff_hash,
            "provider_calls": 0,
            "visible_check_calls": 0,
        }
        if (
            intent_document != expected_intent
            or prepared_restore.payload.get("intent_artifact_hash") != intent_artifact.content_hash
            or baseline.semantic_progress_state_hash != semantic_state.content_hash
            or semantic_state.run_id != self.run_id
            or baseline.run_id != self.run_id
            or not semantic_state.semantic_reset_required
        ):
            raise RecoveryError("causal baseline restore intent binding differs")
        if WorkspaceManager.untracked_files(self.workspace):
            raise RecoveryError("causal baseline restore found untracked files")

        restored_actions: list[str] = []
        restored_intents: list[str] = []
        for action_id, intent_hash in zip(
            baseline.restore_action_ids,
            baseline.restore_intent_hashes,
            strict=True,
        ):
            calls = [
                event
                for event in events
                if event.type == EventType.TOOL_CALLED
                and event.correlation_id == action_id
                and event.payload.get("tool") in _MUTATION_TOOL_NAMES
            ]
            preparations = [
                event
                for event in events
                if event.type == EventType.PATCH_PREPARED
                and event.correlation_id == action_id
                and event.sequence < prepared_restore.sequence
            ]
            if len(calls) != 1 or len(preparations) != 1:
                raise RecoveryError("causal baseline mutation intent binding differs")
            intent, _ = self._load_patch_intent(calls[0], preparations[0])
            if (
                preparations[0].payload.get("content_hash") != intent_hash
                or intent.get("expected_worktree_diff_hash") not in baseline.forward_diff_chain
                or intent.get("baseline_worktree_diff_hash") not in baseline.forward_diff_chain
            ):
                raise RecoveryError("causal baseline mutation intent hash differs")
            observed = WorkspaceManager.diff_summary(self.workspace).patch_hash
            if observed == intent.get("expected_worktree_diff_hash"):
                if self._classify_patch_state(intent) != "post":
                    raise RecoveryError("causal baseline post-state classification differs")
                self._restore_patch_preimages(intent)
            elif observed == intent.get("baseline_worktree_diff_hash"):
                if self._classify_patch_state(intent) != "pre":
                    raise RecoveryError("causal baseline pre-state classification differs")
            else:
                raise RecoveryError("causal baseline restore encountered an unknown diff")
            restored_actions.append(action_id)
            restored_intents.append(intent_hash)

        observed_after = WorkspaceManager.diff_summary(self.workspace).patch_hash
        receipt = record_mutation_baseline_restore(
            baseline=baseline,
            observed_before_diff_hash=baseline.current_failed_diff_hash,
            observed_after_diff_hash=observed_after,
            restored_action_ids=tuple(restored_actions),
            restored_intent_hashes=tuple(restored_intents),
        )
        predicted_sequence = self.state.last_sequence(self.run_id) + 1
        trigger = build_cross_reset_failure_trigger(
            state=semantic_state,
            baseline=baseline,
            receipt=receipt,
            restored_event_sequence=predicted_sequence,
        )
        completion_body = {
            "schema_version": RESTORE_COMPLETED_EVENT_SCHEMA,
            "policy_version": CAUSAL_ACTIVATION_POLICY,
            "restore_prepared_sequence": prepared_restore.sequence,
            "semantic_progress_state": semantic_state.model_dump(mode="json"),
            "semantic_progress_state_hash": semantic_state.content_hash,
            "baseline_projection": baseline.model_dump(mode="json"),
            "baseline_projection_hash": baseline.content_hash,
            "restore_receipt": receipt.model_dump(mode="json"),
            "restore_receipt_hash": receipt.content_hash,
            "trigger": trigger.model_dump(mode="json"),
            "trigger_hash": trigger.content_hash,
            "provider_calls": 0,
            "visible_check_calls": 0,
        }
        completion_artifact = self.artifacts.put_json(completion_body)
        completed = self.state.append_event(
            self.run_id,
            EventType.MUTATION_BASELINE_RESTORED,
            actor="tool-gateway",
            payload={
                **completion_body,
                "completion_artifact": completion_artifact.model_dump(mode="json"),
                "completion_artifact_hash": completion_artifact.content_hash,
            },
        )
        if completed.sequence != predicted_sequence:
            raise RecoveryError("causal baseline restore sequence raced")
        return project_active_cross_reset_trigger(
            run_id=self.run_id,
            current_diff_hash=observed_after,
            events=self.state.list_events(self.run_id),
        )

    def activate_causal_mutation_baseline_restore(
        self,
        phase_evidence: EvidenceState,
    ) -> CrossResetFailureTrigger | None:
        """Prepare and complete a required V17 restore without model dispatch."""

        prepared = self.prepare_causal_mutation_baseline_restore(phase_evidence)
        return prepared or self.reconcile_causal_mutation_baseline_restore()

    def execute(
        self,
        name: str,
        action_id: str,
        arguments: dict[str, Any],
        *,
        execution_context: dict[str, Any] | None = None,
    ) -> ToolResult:
        input_hash = sha256_text(canonical_json({"tool": name, "input": arguments}))
        prior = self.state.get_action_result(self.run_id, action_id, input_hash)
        self_directed_intent = None
        self_directed_target = None
        anchored_read_resolution = None
        operation_arguments = arguments
        if (
            self.tool_schema_version in {"v26", "v27", "v28", "v29"}
            and name in {"read_file", "search_files"}
            and prior is None
        ):
            if not isinstance(execution_context, dict):
                raise RecoveryError("self-directed inspection lacks its exact request context")
            try:
                decision = WorkflowDecisionV4.model_validate_json(
                    canonical_json(execution_context.get("workflow_decision"))
                )
            except ValueError as exc:
                raise RecoveryError("self-directed inspection request context is invalid") from exc
            inspection_arguments = arguments
            if self.tool_schema_version in {"v28", "v29"} and name == "read_file":
                inspection_arguments = normalize_strict_read_arguments(arguments)
                operation_arguments = inspection_arguments
            if self.tool_schema_version in {"v27", "v28", "v29"} and name == "read_file":
                direct_keys = {"path", "start_line", "end_line"}
                supplied_direct = direct_keys.intersection(inspection_arguments)
                supplied_anchor = "search_anchor" in inspection_arguments
                allowed_keys = direct_keys | {"search_anchor", "investigation_intent"}
                if (
                    not set(inspection_arguments).issubset(allowed_keys)
                    or supplied_anchor is bool(supplied_direct)
                    or (supplied_direct and supplied_direct != direct_keys)
                ):
                    raise ContractError(
                        "V27 read_file requires exactly one direct range or search anchor",
                        details={"reason_codes": ["anchored_read_mode_invalid"]},
                    )
                if supplied_anchor:
                    current_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
                    records = load_inspection_records(
                        self.state.list_events(self.run_id),
                        self.artifacts,
                        worktree_diff_hash=current_diff_hash,
                    )
                    anchored_read_resolution = resolve_anchored_read(
                        run_id=self.run_id,
                        task=self.task,
                        worktree_diff_hash=current_diff_hash,
                        records=records,
                        raw_anchor=inspection_arguments["search_anchor"],
                    )
                    operation_arguments = {
                        "path": anchored_read_resolution.path,
                        "start_line": anchored_read_resolution.start_line,
                        "end_line": anchored_read_resolution.end_line,
                    }
                    inspection_arguments = {
                        **operation_arguments,
                        **(
                            {"investigation_intent": arguments["investigation_intent"]}
                            if "investigation_intent" in arguments
                            else {}
                        ),
                    }
            if decision.investigation_intent_required:
                try:
                    state = SelfDirectedExplorationState.model_validate_json(
                        canonical_json(execution_context.get("self_directed_exploration_state"))
                    )
                except ValueError as exc:
                    raise RecoveryError("self-directed investigation state is invalid") from exc
                events = tuple(self.state.list_events(self.run_id))
                prior_target_hashes = project_episode_investigation_target_hashes(
                    events=events,
                    decision=decision,
                    worktree_diff_hash=state.worktree_diff_hash,
                )
                self_directed_intent, self_directed_target = validate_investigation_action(
                    task=self.task,
                    state=state,
                    tool=name,
                    arguments=inspection_arguments,
                    prior_target_hashes=prior_target_hashes,
                )
                if anchored_read_resolution is None:
                    operation_arguments = {
                        key: copy.deepcopy(value)
                        for key, value in inspection_arguments.items()
                        if key != "investigation_intent"
                    }
            elif "investigation_intent" in arguments:
                raise ContractError(
                    "initial self-directed inspection cannot cite unavailable source spans",
                    details={"reason_codes": ["self_directed_investigation_intent_premature"]},
                )
        if name not in {
            "review_task",
            "record_work_plan",
            "revise_work_plan",
            *(
                {"read_file", "search_files"}
                if self.tool_schema_version in {"v26", "v27", "v28", "v29"}
                else set()
            ),
        } and (execution_context is not None):
            raise ContractError("execution context is reserved for bound workflow tools")
        if prior is not None:
            self.state.append_event(
                self.run_id,
                (
                    EventType.TOOL_REPLAYED
                    if self.tool_schema_version in _STRUCTURED_TOOL_SCHEMAS
                    else (
                        EventType.TOOL_SUCCEEDED
                        if prior.status == "succeeded"
                        else EventType.TOOL_FAILED
                    )
                ),
                actor="idempotency-store",
                correlation_id=action_id,
                payload={
                    "tool": name,
                    "input_hash": input_hash,
                    "status": prior.status,
                    "artifact_id": prior.output.get("artifact_id"),
                    "artifact_path": prior.output.get("artifact_path"),
                    "result_artifact": prior.output.get("result_artifact"),
                    "replayed": True,
                    "error_code": prior.error_code,
                    "error_message": (
                        prior.error_message[:_EVENT_ERROR_MESSAGE_LIMIT]
                        if prior.error_message
                        else None
                    ),
                    "check_id": prior.output.get("check_id"),
                    "passed": prior.output.get("passed"),
                    "timed_out": prior.output.get("timed_out"),
                    "worktree_diff_hash": prior.output.get("worktree_diff_hash"),
                    "duration_ms": 0,
                },
            )
            prior.output = {**prior.output, "replayed": True}
            return prior
        worktree_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
        normalized_call_hash = self._normalized_call_hash(
            name,
            operation_arguments,
            worktree_diff_hash=worktree_diff_hash,
        )
        if (
            self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
            and name in {"read_file", "search_files", "run_probe"}
            and self._inspection_short_circuit_eligible(
                name,
                operation_arguments,
            )
        ):
            blocked = self._inspection_admission_block(
                name=name,
                action_id=action_id,
                arguments=operation_arguments,
                input_hash=input_hash,
                normalized_call_hash=normalized_call_hash,
                worktree_diff_hash=worktree_diff_hash,
            )
            if blocked is not None:
                return blocked
            if name in {"read_file", "search_files"} and self.tool_schema_version not in {
                "v26",
                "v27",
                "v28",
                "v29",
            }:
                semantic_replay = self._semantic_inspection_replay(
                    name=name,
                    action_id=action_id,
                    arguments=operation_arguments,
                    input_hash=input_hash,
                    normalized_call_hash=normalized_call_hash,
                    worktree_diff_hash=worktree_diff_hash,
                )
                if semantic_replay is not None:
                    return semantic_replay
        prior_calls = [
            event
            for event in self.state.list_events(self.run_id)
            if event.type == EventType.TOOL_CALLED
        ]
        repeated_calls = 0
        for prior_call in reversed(prior_calls):
            if prior_call.payload.get("normalized_call_hash") != normalized_call_hash:
                break
            repeated_calls += 1
        if repeated_calls:
            self.state.append_event(
                self.run_id,
                EventType.LOOP_DETECTED,
                actor="tool-gateway",
                correlation_id=action_id,
                payload={
                    "tool": name,
                    "normalized_call_hash": normalized_call_hash,
                    "prior_call_sequence": prior_calls[-1].sequence,
                    "occurrences": repeated_calls + 1,
                    "enforcement": "advisory",
                },
            )
        started = utc_now()
        patch_artifact: Artifact | None = None
        patch_source_artifact: Artifact | None = None
        patch_source_snapshot: dict[str, Any] | None = None
        input_artifact: Artifact | None = None
        probe_source_artifact: Artifact | None = None
        structured_projection_artifact: Artifact | None = None
        structured_refresh_projection_artifact: Artifact | None = None
        structured_gateway_patch_artifact: Artifact | None = None
        normalized_patch_artifact: Artifact | None = None
        patch_normalization_artifact: Artifact | None = None
        patch_normalization: dict[str, Any] | None = None
        mutation_patch: str | None = None
        structured_preflight_error: Exception | None = None
        current_plan_hash: str | None = None
        if (
            self.tool_schema_version
            in {
                "v14",
                "v15",
                "v16",
                "v17",
                "v18",
                "v19",
                "v20",
                "v21",
                "v22",
                "v23",
                "v24",
                "v25",
                "v26",
                "v27",
                "v28",
                "v29",
            }
            and name in _MUTATION_TOOL_NAMES
        ):
            try:
                current_plan = (
                    self._current_work_plan(worktree_diff_hash)
                    if self.tool_schema_version == "v14"
                    else self._current_work_plan_v2(worktree_diff_hash)
                )
                if current_plan is None:
                    raise ContractError(
                        "Lean workflow mutation lacks a current-diff recorded work plan"
                    )
                current_plan_hash = current_plan.content_hash
            except (ContractError, RecoveryError, TypeError, ValueError) as exc:
                structured_preflight_error = exc
        if self.tool_schema_version in _STRUCTURED_TOOL_SCHEMAS and name != "apply_patch":
            input_document: dict[str, Any] = {
                "tool": name,
                "input": arguments,
            }
            if execution_context is not None:
                input_document["execution_context"] = execution_context
            input_artifact = self.artifacts.put_json(input_document)
        if name == STRUCTURED_EDIT_TOOL_NAME:
            if (self.tool_schema_version, self.context_policy_version) not in {
                ("v7", "phase-evidence-v12"),
                ("v8", "phase-evidence-v13"),
                ("v9", "phase-evidence-v13"),
                ("v9", "phase-evidence-v14"),
                ("v10", "phase-evidence-v15"),
                ("v10", "phase-evidence-v16"),
                ("v11", "phase-evidence-v17"),
                ("v12", "phase-evidence-v18"),
                ("v13", "phase-evidence-v19"),
                ("v14", "phase-evidence-v20"),
                ("v15", "phase-evidence-v21"),
                ("v16", "phase-evidence-v22"),
                ("v17", "phase-evidence-v23"),
                ("v18", "phase-evidence-v24"),
                ("v19", "phase-evidence-v25"),
                ("v20", "phase-evidence-v26"),
                ("v21", "phase-evidence-v27"),
                ("v22", "phase-evidence-v28"),
                ("v23", "phase-evidence-v29"),
                ("v24", "phase-evidence-v30"),
                ("v25", "phase-evidence-v31"),
                ("v25", "phase-evidence-v32"),
                ("v26", "phase-evidence-v33"),
                ("v26", "phase-evidence-v34"),
                ("v26", "phase-evidence-v35"),
                ("v27", "phase-evidence-v36"),
                ("v28", "phase-evidence-v37"),
                ("v29", "phase-evidence-v38"),
            }:
                structured_preflight_error = ContractError(
                    "apply_structured_edit requires the exact v7/v12, v8/v13, "
                    "v9/v13, v9/v14, v10/v15, v10/v16, v11/v17, or "
                    "v12/v18, v13/v19, v14/v20, v15/v21, v16/v22, or "
                    "v17/v23, v18/v24, v19/v25, v20/v26, v21/v27, v22/v28, "
                    "v23/v29, v24/v30, v25/v31, v25/v32, v26/v33, or "
                    "v26/v34, v26/v35, or v27/v36 runtime"
                )
            else:
                try:
                    (
                        structured,
                        gateway_patch,
                        fresh_projection,
                    ) = self._structured_edit_gateway_patch(
                        action_id=action_id,
                        arguments=arguments,
                        worktree_diff_hash=worktree_diff_hash,
                    )
                    mutation_patch = gateway_patch.patch
                    structured_projection_artifact = self.artifacts.put_json(
                        structured.model_dump(mode="json")
                    )
                    structured_gateway_patch_artifact = self.artifacts.put_json(
                        gateway_patch.model_dump(mode="json")
                    )
                    if fresh_projection is not None:
                        structured_refresh_projection_artifact = self.artifacts.put_json(
                            fresh_projection.model_dump(mode="json")
                        )
                except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
                    structured_preflight_error = exc
        if (
            self.tool_schema_version in _STRUCTURED_TOOL_SCHEMAS
            and name == "apply_patch"
            and isinstance(arguments.get("patch"), str)
        ):
            mutation_patch = str(arguments["patch"])
        if mutation_patch is not None:
            patch_artifact = self.artifacts.put_text(
                mutation_patch,
                media_type="text/x-diff",
            )
            if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS:
                mutation_patch, patch_normalization = _normalize_raw_git_patch(mutation_patch)
                normalized_patch_artifact = self.artifacts.put_text(
                    mutation_patch,
                    media_type="text/x-diff",
                )
                patch_normalization_artifact = self.artifacts.put_json(patch_normalization)
            if self.tool_schema_version in _PATCH_RETRY_TOOL_SCHEMAS:
                patch_source_snapshot = self._bounded_patch_source_snapshot(
                    mutation_patch,
                    candidate_content_hash=(
                        normalized_patch_artifact.content_hash
                        if normalized_patch_artifact is not None
                        else patch_artifact.content_hash
                    ),
                    input_hash=input_hash,
                    worktree_diff_hash=worktree_diff_hash,
                )
                patch_source_artifact = self.artifacts.put_json(patch_source_snapshot)
        if (
            self.tool_schema_version in _SELF_VALIDATION_TOOL_SCHEMAS
            and name == "run_probe"
            and isinstance(arguments.get("source"), str)
        ):
            probe_source_artifact = self.artifacts.put_text(
                str(arguments["source"]),
                media_type="text/x-python",
            )
        call_payload: dict[str, Any] = {
            "tool": name,
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
        }
        if self.tool_schema_version in {"v28", "v29"} and name == "read_file":
            call_payload["read_argument_policy_version"] = STRICT_ANCHORED_READ_POLICY
        if self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES:
            call_payload["worktree_diff_hash"] = worktree_diff_hash
            call_payload["execution"] = "dispatched"
        if execution_context is not None:
            call_payload.update(
                {
                    "request_artifact_id": execution_context.get("request_artifact_id"),
                    "request_phase": execution_context.get("phase"),
                }
            )
        if self_directed_intent is not None and self_directed_target is not None:
            call_payload.update(
                {
                    "self_directed_exploration_policy_version": (SELF_DIRECTED_EXPLORATION_POLICY),
                    "investigation_intent": self_directed_intent.model_dump(mode="json"),
                    "investigation_intent_hash": sha256_text(
                        canonical_json(self_directed_intent.model_dump(mode="json"))
                    ),
                    "investigation_target": self_directed_target.model_dump(mode="json"),
                    "investigation_target_hash": self_directed_target.target_hash,
                }
            )
        if anchored_read_resolution is not None:
            call_payload.update(
                {
                    "anchored_read_policy_version": ANCHORED_READ_POLICY,
                    "anchored_read_resolution": anchored_read_resolution.model_dump(mode="json"),
                    "anchored_read_resolution_hash": anchored_read_resolution.content_hash,
                }
            )
        if input_artifact is not None:
            call_payload["input_artifact"] = input_artifact.model_dump(mode="json")
        if patch_artifact is not None:
            call_payload["patch_artifact"] = patch_artifact.model_dump(mode="json")
            call_payload["artifact_id"] = patch_artifact.artifact_id
            call_payload["artifact_path"] = patch_artifact.path
        elif input_artifact is not None:
            call_payload["artifact_id"] = input_artifact.artifact_id
            call_payload["artifact_path"] = input_artifact.path
        if probe_source_artifact is not None:
            call_payload["source_artifact"] = probe_source_artifact.model_dump(mode="json")
            call_payload["source_hash"] = probe_source_artifact.content_hash
            call_payload["probe_policy_version"] = "ephemeral-python-probe-v2"
            call_payload["probe_id"] = arguments.get("probe_id")
        if patch_source_artifact is not None:
            call_payload["source_snapshot_artifact"] = patch_source_artifact.model_dump(mode="json")
            call_payload["source_snapshot_schema_version"] = "patch-source-snapshot-v1"
        if normalized_patch_artifact is not None:
            call_payload["normalized_patch_artifact"] = normalized_patch_artifact.model_dump(
                mode="json"
            )
            call_payload["patch_normalization_artifact"] = (
                patch_normalization_artifact.model_dump(mode="json")
                if patch_normalization_artifact is not None
                else None
            )
        if structured_projection_artifact is not None:
            call_payload["structured_edit_projection_artifact"] = (
                structured_projection_artifact.model_dump(mode="json")
            )
            call_payload["structured_edit_gateway_patch_artifact"] = (
                structured_gateway_patch_artifact.model_dump(mode="json")
                if structured_gateway_patch_artifact is not None
                else None
            )
            call_payload["structured_edit_refresh_projection_artifact"] = (
                structured_refresh_projection_artifact.model_dump(mode="json")
                if structured_refresh_projection_artifact is not None
                else None
            )
        if current_plan_hash is not None:
            call_payload["plan_hash"] = current_plan_hash
        self.state.append_event(
            self.run_id,
            EventType.TOOL_CALLED,
            actor="agent",
            correlation_id=action_id,
            payload=call_payload,
        )
        try:
            if structured_preflight_error is not None:
                raise structured_preflight_error
            if (
                self.tool_schema_version in _STRUCTURED_TOOL_SCHEMAS
                and name in _MUTATION_TOOL_NAMES
                and patch_artifact is not None
                and mutation_patch is not None
            ):
                intent = self._prepare_patch_mutation(
                    action_id,
                    input_hash,
                    mutation_patch,
                    normalized_patch_artifact or patch_artifact,
                )
                if self._controlled_rejection_pending():
                    raise self._controlled_rejection(
                        action_id=action_id,
                        input_hash=input_hash,
                        patch_artifact=(normalized_patch_artifact or patch_artifact),
                        intent=intent,
                    )
                output = self._apply_patch(
                    mutation_patch,
                    intent=intent,
                )
                if patch_normalization is not None:
                    output.update(
                        {
                            "patch_normalization": patch_normalization,
                            "normalized_patch_artifact": (
                                normalized_patch_artifact.model_dump(mode="json")
                                if normalized_patch_artifact is not None
                                else None
                            ),
                            "patch_normalization_artifact": (
                                patch_normalization_artifact.model_dump(mode="json")
                                if patch_normalization_artifact is not None
                                else None
                            ),
                        }
                    )
                if structured_projection_artifact is not None:
                    output.update(
                        {
                            "structured_edit_projection_artifact": (
                                structured_projection_artifact.model_dump(mode="json")
                            ),
                            "structured_edit_gateway_patch_artifact": (
                                structured_gateway_patch_artifact.model_dump(mode="json")
                                if structured_gateway_patch_artifact is not None
                                else None
                            ),
                            "structured_edit_refresh_projection_artifact": (
                                structured_refresh_projection_artifact.model_dump(mode="json")
                                if structured_refresh_projection_artifact is not None
                                else None
                            ),
                        }
                    )
                if current_plan_hash is not None:
                    output["plan_hash"] = current_plan_hash
            else:
                if name in {"review_task", "record_work_plan", "revise_work_plan"}:
                    output = self._dispatch(
                        name,
                        arguments,
                        execution_context=execution_context,
                    )
                elif name == "run_probe":
                    output = self._dispatch(
                        name,
                        arguments,
                        probe_source_artifact=probe_source_artifact,
                    )
                else:
                    output = self._dispatch(name, operation_arguments)
            if self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES and name in {
                "read_file",
                "search_files",
            }:
                output = self._annotate_inspection_result(
                    name=name,
                    output=output,
                    worktree_diff_hash=worktree_diff_hash,
                    investigation_intent=(
                        self_directed_intent.model_dump(mode="json")
                        if self_directed_intent is not None
                        else None
                    ),
                    investigation_target=(
                        self_directed_target.model_dump(mode="json")
                        if self_directed_target is not None
                        else None
                    ),
                )
                if self.tool_schema_version in {"v28", "v29"} and name == "read_file":
                    output["read_argument_policy_version"] = STRICT_ANCHORED_READ_POLICY
                if anchored_read_resolution is not None:
                    output.update(
                        {
                            "anchored_read_policy_version": ANCHORED_READ_POLICY,
                            "anchored_read_resolution": (
                                anchored_read_resolution.model_dump(mode="json")
                            ),
                            "anchored_read_resolution_hash": (
                                anchored_read_resolution.content_hash
                            ),
                        }
                    )
            artifact = self.artifacts.put_json(output)
            result_artifact = (
                artifact.model_dump(mode="json")
                if (
                    self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
                    and name in {"read_file", "search_files"}
                )
                or (
                    self.tool_schema_version in _SELF_VALIDATION_TOOL_SCHEMAS
                    and name in {"run_probe", "review_task"}
                )
                or (
                    self.context_policy_version
                    in {
                        "phase-evidence-v9",
                        "phase-evidence-v10",
                        "phase-evidence-v11",
                    }
                    and name in {"run_check", "get_diff"}
                )
                or (
                    self.tool_schema_version
                    in {
                        "v10",
                        "v11",
                        "v12",
                        "v13",
                        "v14",
                        "v15",
                        "v16",
                        "v17",
                        "v18",
                        "v19",
                        "v20",
                        "v21",
                        "v22",
                        "v23",
                        "v24",
                        "v25",
                        "v26",
                        "v27",
                        "v28",
                        "v29",
                    }
                    and name == "run_check"
                )
                or (self.tool_schema_version == "v14" and name == "record_work_plan")
                or (
                    self.tool_schema_version
                    in {
                        "v15",
                        "v16",
                        "v17",
                        "v18",
                        "v19",
                        "v20",
                        "v21",
                        "v22",
                        "v23",
                        "v24",
                        "v25",
                        "v26",
                        "v27",
                        "v28",
                        "v29",
                    }
                    and name in {"record_work_plan", "revise_work_plan", "get_diff"}
                )
                else None
            )
            result = ToolResult(
                action_id=action_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    **({"result_artifact": result_artifact} if result_artifact is not None else {}),
                    **output,
                },
            )
        except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
            result = self._error_result(
                name,
                action_id,
                started,
                exc,
                fatal=False,
                edit_correction=self._edit_correction_evidence(
                    name=name,
                    arguments=arguments,
                    error=exc,
                    pre_call_worktree_diff_hash=worktree_diff_hash,
                    patch_source_snapshot=patch_source_snapshot,
                ),
            )
        except RecoveryError as exc:
            result = self._error_result(
                name,
                action_id,
                started,
                exc,
                fatal=True,
            )
        self._complete_result(name, input_hash, result)
        return result

    def block_same_turn_action(
        self,
        name: str,
        action_id: str,
        arguments: dict[str, Any],
        *,
        source_action_id: str,
        source_result_status: str,
        source_model_event_id: str,
        source_call_index: int,
        blocked_call_index: int,
    ) -> ToolResult:
        """Durably close a call emitted after the v4 apply-patch barrier."""

        if self.tool_schema_version not in _PATCH_RETRY_TOOL_SCHEMAS:
            raise ContractError("same-turn mutation barriers require tool schema v4")
        input_hash = sha256_text(canonical_json({"tool": name, "input": arguments}))
        prior = self.state.get_action_result(
            self.run_id,
            action_id,
            input_hash,
        )
        if prior is not None:
            prior.output = {**prior.output, "replayed": True}
            return prior

        started = utc_now()
        worktree_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
        input_artifact = self.artifacts.put_json({"tool": name, "input": arguments})
        error_message = (
            "tool call was not executed because an earlier apply_patch call "
            "from the same model response is a turn barrier"
        )
        error_details = {
            "schema_version": "tool-admission-blocked-v3",
            "policy_version": "turn-mutation-barrier-v1",
            "reason_codes": ["prior_apply_patch_same_turn"],
            "source_action_id": source_action_id,
            "source_result_status": source_result_status,
            "source_model_event_id": source_model_event_id,
            "source_call_index": source_call_index,
            "blocked_call_index": blocked_call_index,
            "guidance": (
                "Inspect the apply_patch result in the next request before "
                "choosing any follow-up tool."
            ),
        }
        result_payload = {
            "tool": name,
            "status": "rejected",
            "error_code": "TOOL_ADMISSION_BLOCKED",
            "error_message": error_message,
            "error_details": error_details,
            "admission_blocked": True,
            "worktree_diff_hash": worktree_diff_hash,
        }
        result_artifact = self.artifacts.put_json(result_payload)
        result = ToolResult(
            action_id=action_id,
            status="rejected",
            started_at=started,
            finished_at=utc_now(),
            output={
                "artifact_id": result_artifact.artifact_id,
                "artifact_path": result_artifact.path,
                "result_artifact": result_artifact.model_dump(mode="json"),
                **result_payload,
            },
            error_code="TOOL_ADMISSION_BLOCKED",
            error_message=error_message,
        )
        event_payload = {
            **result_payload,
            "schema_version": "tool-admission-blocked-v3",
            "policy_version": "turn-mutation-barrier-v1",
            "reason_codes": ["prior_apply_patch_same_turn"],
            "input_hash": input_hash,
            "normalized_call_hash": self._normalized_call_hash(
                name,
                arguments,
                worktree_diff_hash=worktree_diff_hash,
            ),
            "source_action_id": source_action_id,
            "source_result_status": source_result_status,
            "source_model_event_id": source_model_event_id,
            "source_call_index": source_call_index,
            "blocked_call_index": blocked_call_index,
            "mutation_epoch_sequence": mutation_epoch(self.state.list_events(self.run_id)),
            "input_artifact": input_artifact.model_dump(mode="json"),
            "result_artifact": result_artifact.model_dump(mode="json"),
            "artifact_id": result_artifact.artifact_id,
            "artifact_path": result_artifact.path,
        }
        self.state.complete_nonexecuted_action(
            self.run_id,
            action_id,
            input_hash,
            result,
            event_specs=[
                (
                    EventType.TOOL_ADMISSION_BLOCKED,
                    "tool-admission-policy",
                    event_payload,
                )
            ],
        )
        return result

    def reconcile_same_turn_barriers(self) -> int:
        """Close a v4 model response suffix after a recovered apply result."""

        if self.tool_schema_version not in _PATCH_RETRY_TOOL_SCHEMAS:
            return 0
        created = 0
        object_root = self.artifacts.objects.resolve()
        for model_event in self.state.list_events(self.run_id):
            if model_event.type != EventType.MODEL_CALLED:
                continue
            try:
                artifact_path = Path(str(model_event.payload["artifact_path"])).resolve()
                relative = artifact_path.relative_to(object_root)
                parts = relative.parts
                content = artifact_path.read_bytes()
                if (
                    len(parts) != 2
                    or len(parts[0]) != 2
                    or len(parts[1]) != 62
                    or sha256_bytes(content) != f"sha256:{parts[0]}{parts[1]}"
                ):
                    raise RecoveryError("model response artifact failed content-address validation")
                document = json.loads(content.decode("utf-8", errors="strict"))
                calls = document.get("tool_calls")
            except (
                KeyError,
                OSError,
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as exc:
                raise RecoveryError(
                    "model response artifact is unavailable during barrier recovery"
                ) from exc
            if not isinstance(calls, list):
                raise RecoveryError("model response artifact has invalid tool calls")
            first_apply_index = next(
                (
                    index
                    for index, call in enumerate(calls, 1)
                    if isinstance(call, dict) and call.get("name") in _MUTATION_TOOL_NAMES
                ),
                None,
            )
            if first_apply_index is None or first_apply_index == len(calls):
                continue
            source_call = calls[first_apply_index - 1]
            source_action_id = source_call.get("action_id")
            source_arguments = source_call.get("arguments")
            if not isinstance(source_action_id, str) or not isinstance(
                source_arguments,
                dict,
            ):
                raise RecoveryError("model response apply_patch call is malformed")
            source_name = source_call.get("name")
            if source_name not in _MUTATION_TOOL_NAMES:
                raise RecoveryError("model response mutation tool identity differs")
            source_input_hash = sha256_text(
                canonical_json({"tool": source_name, "input": source_arguments})
            )
            source_result = self.state.get_action_result(
                self.run_id,
                source_action_id,
                source_input_hash,
            )
            if source_result is None:
                continue
            for blocked_index, blocked_call in enumerate(
                calls[first_apply_index:],
                first_apply_index + 1,
            ):
                if not isinstance(blocked_call, dict):
                    raise RecoveryError("model response barrier call is malformed")
                name = blocked_call.get("name")
                action_id = blocked_call.get("action_id")
                arguments = blocked_call.get("arguments")
                if (
                    not isinstance(name, str)
                    or not isinstance(action_id, str)
                    or not isinstance(arguments, dict)
                ):
                    raise RecoveryError("model response barrier call is malformed")
                result = self.block_same_turn_action(
                    name,
                    action_id,
                    arguments,
                    source_action_id=source_action_id,
                    source_result_status=source_result.status,
                    source_model_event_id=model_event.event_id,
                    source_call_index=first_apply_index,
                    blocked_call_index=blocked_index,
                )
                if not result.output.get("replayed"):
                    created += 1
        return created

    def _inspection_short_circuit_eligible(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> bool:
        """Validate inspection shape and paths before a no-dispatch outcome.

        Invalid requests continue through the ordinary ToolCalled/ToolFailed
        path so tail admission cannot hide a contract or path-policy attempt.
        """

        try:
            if name == "run_probe":
                self._validate_probe_arguments(arguments)
                return True
            validate_inspection_arguments(
                self.workspace,
                name,
                arguments,
            )
            return True
        except (ContractError, PolicyViolation):
            return False

    def _inspection_admission_block(
        self,
        *,
        name: str,
        action_id: str,
        arguments: dict[str, Any],
        input_hash: str,
        normalized_call_hash: str,
        worktree_diff_hash: str,
    ) -> ToolResult | None:
        events = self.state.list_events(self.run_id)
        manifest = self.state.get_manifest(self.run_id)
        reserve = nominal_tail_reserve(
            self.task,
            context_policy_version=_investigation_compat_version(self.context_policy_version),
        )
        policy_version = investigation_policy_version(
            _investigation_compat_version(self.context_policy_version)
        )
        admission_schema = tool_admission_schema(
            _investigation_compat_version(self.context_policy_version)
        )
        model_calls_used = sum(event.type == EventType.MODEL_CALLED for event in events)
        tool_calls_used = sum(event.type == EventType.TOOL_CALLED for event in events)
        remaining_model_calls = (
            manifest.budget.max_model_calls - model_calls_used
            if manifest.budget.max_model_calls is not None
            else None
        )
        remaining_tool_calls = (
            manifest.budget.max_tool_calls - tool_calls_used
            if manifest.budget.max_tool_calls is not None
            else None
        )
        calculated_tail_policy = None
        if self.context_policy_version in _TOKEN_TAIL_CONTEXT_POLICIES:
            calculated_tail_policy = tail_policy(
                self.task,
                None,
                context_policy_version=_investigation_compat_version(self.context_policy_version),
                events=events,
                budget=manifest.budget,
                max_output_tokens=manifest.model.max_output_tokens,
                projection_stage="post_generation",
            )
            block_reasons = list(calculated_tail_policy["block_reasons"])
        else:
            block_reasons = []
            if remaining_tool_calls is not None and remaining_tool_calls <= reserve["tool_calls"]:
                block_reasons.append("tool_tail_reserved")
            if (
                remaining_model_calls is not None
                and remaining_model_calls
                <= reserve["model_calls"] + reserve["feedback_model_calls"]
            ):
                block_reasons.append("model_tail_reserved")
        epoch = mutation_epoch(events)
        semantic_replay_count = sum(
            event.type == EventType.TOOL_REPLAYED
            and event.payload.get("semantic_replay") is True
            and (epoch is None or event.sequence > epoch)
            for event in events
        )
        evidence_saturated = (
            self.context_policy_version
            in {
                "phase-evidence-v7",
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
                "phase-evidence-v11",
            }
            and name in {"read_file", "search_files"}
            and semantic_replay_count >= _EVIDENCE_SATURATION_THRESHOLD
        )
        if evidence_saturated:
            block_reasons.append("evidence_saturated")
        if not block_reasons:
            return None

        started = utc_now()
        input_artifact = self.artifacts.put_json({"tool": name, "input": arguments})
        try:
            preflight_artifact = self._inspection_admission_preflight(
                name=name,
                arguments=arguments,
                worktree_diff_hash=worktree_diff_hash,
            )
        except (ContractError, OSError):
            # The target can disappear between eligibility and snapshot.
            # Ordinary dispatch will then record the structured failure.
            return None
        preflight_descriptor = preflight_artifact.model_dump(mode="json")
        error_message = (
            "inspection was not admitted because the active mutation epoch "
            "has exhausted its semantic replay allowance; use the durable "
            "evidence or make a scoped mutation"
            if evidence_saturated
            else (
                "inspection was not admitted because the nominal corrective "
                "lifecycle tail is reserved; use apply_patch or another "
                "phase-advancing action"
            )
        )
        error_details = {
            "schema_version": admission_schema,
            "policy_version": policy_version,
            "reason_codes": block_reasons,
            "nominal_reserve": reserve,
            "remaining_model_calls": remaining_model_calls,
            "remaining_tool_calls": remaining_tool_calls,
            "guidance": (
                "Use the durable investigation ledger and move to a scoped "
                "patch, registered validation, diff review, or submission."
            ),
        }
        if evidence_saturated:
            error_details.update(
                {
                    "evidence_saturation_policy_version": ("evidence-saturation-v1"),
                    "semantic_replay_count": semantic_replay_count,
                    "semantic_replay_threshold": (_EVIDENCE_SATURATION_THRESHOLD),
                    "mutation_epoch_sequence": epoch,
                }
            )
        if calculated_tail_policy is not None:
            error_details["tail_policy"] = calculated_tail_policy
        result_payload = {
            "tool": name,
            "status": "rejected",
            "error_code": "TOOL_ADMISSION_BLOCKED",
            "error_message": error_message,
            "error_details": error_details,
            "admission_blocked": True,
            "worktree_diff_hash": worktree_diff_hash,
            "preflight_artifact": preflight_descriptor,
        }
        result_artifact = self.artifacts.put_json(result_payload)
        result = ToolResult(
            action_id=action_id,
            status="rejected",
            started_at=started,
            finished_at=utc_now(),
            output={
                "artifact_id": result_artifact.artifact_id,
                "artifact_path": result_artifact.path,
                "result_artifact": result_artifact.model_dump(mode="json"),
                **result_payload,
            },
            error_code="TOOL_ADMISSION_BLOCKED",
            error_message=error_message,
        )
        event_payload = {
            "schema_version": admission_schema,
            "policy_version": policy_version,
            "tool": name,
            "status": "rejected",
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
            "worktree_diff_hash": worktree_diff_hash,
            "mutation_epoch_sequence": epoch,
            "reason_codes": block_reasons,
            "nominal_reserve": reserve,
            "model_calls_used": model_calls_used,
            "max_model_calls": manifest.budget.max_model_calls,
            "tool_calls_used": tool_calls_used,
            "max_tool_calls": manifest.budget.max_tool_calls,
            "input_artifact": input_artifact.model_dump(mode="json"),
            "preflight_artifact": preflight_descriptor,
            "result_artifact": result_artifact.model_dump(mode="json"),
            "artifact_id": result_artifact.artifact_id,
            "artifact_path": result_artifact.path,
            "error_code": result.error_code,
            "error_message": error_message,
            "error_details": error_details,
        }
        if evidence_saturated:
            event_payload.update(
                {
                    "evidence_saturation_policy_version": ("evidence-saturation-v1"),
                    "semantic_replay_count": semantic_replay_count,
                    "semantic_replay_threshold": (_EVIDENCE_SATURATION_THRESHOLD),
                }
            )
        if calculated_tail_policy is not None:
            token_projection = calculated_tail_policy["token_projection"]
            event_payload.update(
                {
                    "tail_policy": calculated_tail_policy,
                    "tokens_used": token_projection["total_tokens_used"],
                    "remaining_tokens": token_projection["remaining_tokens"],
                    "max_total_tokens": manifest.budget.max_total_tokens,
                    "max_output_tokens": (manifest.model.max_output_tokens),
                }
            )
        self.state.complete_nonexecuted_action(
            self.run_id,
            action_id,
            input_hash,
            result,
            event_specs=[
                (
                    EventType.TOOL_ADMISSION_BLOCKED,
                    "tool-admission-policy",
                    event_payload,
                )
            ],
        )
        return result

    def _inspection_admission_preflight(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        worktree_diff_hash: str,
    ) -> Artifact:
        """Freeze stateful validation evidence before a no-dispatch result."""

        payload: dict[str, Any] = {
            "schema_version": INSPECTION_ADMISSION_PREFLIGHT_SCHEMA,
            "policy_version": investigation_policy_version(
                _investigation_compat_version(self.context_policy_version)
            ),
            "tool": name,
            "worktree_diff_hash": worktree_diff_hash,
        }
        if name == "run_probe":
            profile = self._validate_probe_arguments(arguments)
            source_artifact = self.artifacts.put_text(
                str(arguments["source"]),
                media_type="text/x-python",
            )
            payload.update(
                {
                    "probe_id": profile.id,
                    "probe_runtime": profile.runtime,
                    "source_artifact": source_artifact.model_dump(mode="json"),
                    "source_hash": source_artifact.content_hash,
                }
            )
            return self.artifacts.put_json(payload)
        if name == "read_file":
            path = str(arguments["path"])
            workspace = self.workspace.resolve()
            target = ensure_within(workspace, path)
            content = target.read_bytes()
            target_artifact = self.artifacts.put_bytes(content)
            payload.update(
                {
                    "requested_path": path,
                    "resolved_relative_path": target.relative_to(workspace).as_posix(),
                    "target_artifact": target_artifact.model_dump(mode="json"),
                }
            )
        else:
            payload.update(
                {
                    "query": arguments["query"],
                    "path_glob": arguments.get("path_glob", "**/*"),
                }
            )
        return self.artifacts.put_json(payload)

    def _investigation_no_progress_streak(
        self,
        events: list,
    ) -> int:
        epoch = mutation_epoch(events)
        streak = 0
        for event in events:
            if epoch is not None and event.sequence <= epoch:
                continue
            if (
                event.type == EventType.LOOP_DETECTED
                and event.payload.get("schema_version") == INVESTIGATION_LOOP_SCHEMA
            ):
                streak += 1
            elif event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") in {
                "read_file",
                "search_files",
            }:
                novelty = event.payload.get("novelty")
                if isinstance(novelty, dict) and novelty.get("classification") == "seen_only":
                    streak += 1
                else:
                    streak = 0
            elif event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool") not in {
                "read_file",
                "search_files",
            }:
                streak = 0
        return streak

    def _semantic_inspection_replay(
        self,
        *,
        name: str,
        action_id: str,
        arguments: dict[str, Any],
        input_hash: str,
        normalized_call_hash: str,
        worktree_diff_hash: str,
        existing_call_payload: dict[str, Any] | None = None,
    ) -> ToolResult | None:
        events = self.state.list_events(self.run_id)
        records = load_inspection_records(
            events,
            self.artifacts,
            worktree_diff_hash=worktree_diff_hash,
        )
        sources = []
        replay_output: dict[str, Any] | None = None
        reason_code: str | None = None
        if name == "search_files":
            exact = [
                record
                for record in records
                if record.tool == name
                and record.normalized_call_hash == normalized_call_hash
                and record.result["truncated"] is False
            ]
            if exact:
                sources = [exact[-1]]
                replay_output = dict(exact[-1].result)
                reason_code = "duplicate_search"
        elif (
            name == "read_file"
            and isinstance(arguments.get("path"), str)
            and type(arguments.get("start_line")) is int
            and type(arguments.get("end_line")) is int
        ):
            reconstructed = reconstruct_covered_read(
                records,
                path=str(arguments["path"]),
                start_line=int(arguments["start_line"]),
                end_line=int(arguments["end_line"]),
                worktree_diff_hash=worktree_diff_hash,
            )
            if reconstructed is not None:
                replay_output, sources = reconstructed
                reason_code = "fully_covered_read"
        if replay_output is None or reason_code is None:
            return None

        started = utc_now()
        input_artifact = (
            Artifact.model_validate(existing_call_payload["input_artifact"])
            if existing_call_payload is not None
            else self.artifacts.put_json({"tool": name, "input": arguments})
        )
        source_call_sequences = [source.call_sequence for source in sources]
        source_outcome_sequences = [source.outcome_sequence for source in sources]
        replay_payload = {
            **replay_output,
            "novelty": {
                "classification": "seen_only",
                "new_evidence_count": 0,
                "reason": reason_code,
            },
            "semantic_replay": True,
            "replay_kind": "semantic-investigation",
            "replay_reason": reason_code,
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
        }
        result_artifact = self.artifacts.put_json(replay_payload)
        result = ToolResult(
            action_id=action_id,
            status="succeeded",
            started_at=started,
            finished_at=utc_now(),
            output={
                "artifact_id": result_artifact.artifact_id,
                "artifact_path": result_artifact.path,
                "result_artifact": result_artifact.model_dump(mode="json"),
                **replay_payload,
            },
        )
        new_streak = self._investigation_no_progress_streak(events) + 1
        epoch = mutation_epoch(events)
        call_payload = (
            dict(existing_call_payload)
            if existing_call_payload is not None
            else {
                "tool": name,
                "input_hash": input_hash,
                "normalized_call_hash": normalized_call_hash,
                "worktree_diff_hash": worktree_diff_hash,
                "execution": "semantic-cache-replay",
                "input_artifact": input_artifact.model_dump(mode="json"),
                "artifact_id": input_artifact.artifact_id,
                "artifact_path": input_artifact.path,
            }
        )
        loop_payload = {
            "schema_version": INVESTIGATION_LOOP_SCHEMA,
            "policy_version": INVESTIGATION_POLICY_VERSION,
            "tool": name,
            "reason_code": reason_code,
            "normalized_call_hash": normalized_call_hash,
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
            "mutation_epoch_sequence": epoch,
            "worktree_diff_hash": worktree_diff_hash,
            "no_progress_streak": new_streak,
            "strategy_change_required": new_streak >= 2,
            "occurrences": new_streak + 1,
            "enforcement": "semantic-cache-replay",
        }
        outcome_payload = {
            "schema_version": TOOL_REPLAY_SCHEMA,
            "tool": name,
            "status": "succeeded",
            "semantic_replay": True,
            "replay_kind": "semantic-investigation",
            "reason_code": reason_code,
            "input_hash": input_hash,
            "normalized_call_hash": normalized_call_hash,
            "source_action_ids": [source.action_id for source in sources],
            "source_call_sequences": source_call_sequences,
            "source_outcome_sequences": source_outcome_sequences,
            "mutation_epoch_sequence": epoch,
            "worktree_diff_hash": worktree_diff_hash,
            "artifact_id": result_artifact.artifact_id,
            "artifact_path": result_artifact.path,
            "result_artifact": result_artifact.model_dump(mode="json"),
            "duration_ms": int((result.finished_at - result.started_at).total_seconds() * 1000),
        }
        self.state.complete_nonexecuted_action(
            self.run_id,
            action_id,
            input_hash,
            result,
            event_specs=[
                (EventType.TOOL_CALLED, "agent", call_payload),
                (EventType.LOOP_DETECTED, "tool-gateway", loop_payload),
                (EventType.TOOL_REPLAYED, "semantic-cache", outcome_payload),
            ],
        )
        return result

    def _annotate_inspection_result(
        self,
        *,
        name: str,
        output: dict[str, Any],
        worktree_diff_hash: str,
        investigation_intent: dict[str, Any] | None = None,
        investigation_target: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        events = self.state.list_events(self.run_id)
        records = load_inspection_records(
            events,
            self.artifacts,
            worktree_diff_hash=worktree_diff_hash,
        )
        annotated = {**output, "worktree_diff_hash": worktree_diff_hash}
        if name == "read_file":
            prior_lines = {
                line
                for start, end in read_coverage(
                    records,
                    str(output["path"]),
                )
                for line in range(start, end + 1)
            }
            actual_start = output["actual_start_line"]
            actual_end = output["actual_end_line"]
            returned_lines = (
                set(range(actual_start, actual_end + 1))
                if actual_start is not None and actual_end is not None
                else set()
            )
            new_lines = returned_lines - prior_lines
            classification = "novel" if new_lines else "novel_negative"
            annotated["novelty"] = {
                "schema_version": "inspection-novelty-v1",
                "classification": classification,
                "new_evidence_count": len(new_lines),
                "reused_evidence_count": len(returned_lines & prior_lines),
            }
        else:
            prior_matches = prior_search_match_keys(records)
            current_matches = {search_match_key(match) for match in output["matches"]}
            new_matches = current_matches - prior_matches
            if output["truncated"]:
                classification = "novel_truncated"
            elif not current_matches:
                classification = "novel_negative"
            elif new_matches:
                classification = "novel"
            else:
                classification = "seen_only"
            annotated["novelty"] = {
                "schema_version": "inspection-novelty-v1",
                "classification": classification,
                "new_evidence_count": len(new_matches),
                "reused_evidence_count": len(current_matches & prior_matches),
            }
        if investigation_intent is not None and investigation_target is not None:
            target = project_investigation_target(
                tool=name,
                arguments={
                    **(
                        {
                            "path": investigation_target["path"],
                            "start_line": investigation_target["start_line"],
                            "end_line": investigation_target["end_line"],
                        }
                        if name == "read_file"
                        else {
                            "query": investigation_target["query"],
                            "path_glob": investigation_target["path_glob"],
                        }
                    )
                },
            )
            annotated.update(
                {
                    "self_directed_exploration_policy_version": (SELF_DIRECTED_EXPLORATION_POLICY),
                    "investigation_intent": copy.deepcopy(investigation_intent),
                    "investigation_intent_hash": sha256_text(canonical_json(investigation_intent)),
                    "investigation_target": target.model_dump(mode="json"),
                    "investigation_target_hash": target.target_hash,
                }
            )
        return annotated

    def _controlled_rejection_pending(self) -> bool:
        if self.fault.type != "controlled-reject-first-prepared-patch":
            return False
        events = self.state.list_events(self.run_id)
        controlled_failures = [
            event
            for event in events
            if (
                event.type == EventType.TOOL_FAILED
                and event.payload.get("error_code") == "CONTROLLED_DIAGNOSTIC_REJECTION"
            )
        ]
        if not controlled_failures:
            return True
        if len(controlled_failures) > 1:
            raise RecoveryError("controlled rejection evidence contains duplicate declarations")

        failure = controlled_failures[0]
        action_id = failure.correlation_id
        calls = [
            event
            for event in events
            if (
                event.type == EventType.TOOL_CALLED
                and event.actor == "agent"
                and event.payload.get("tool") == "apply_patch"
                and event.correlation_id == action_id
                and event.sequence < failure.sequence
            )
        ]
        prepared = [
            event
            for event in events
            if (
                event.type == EventType.PATCH_PREPARED
                and event.actor == "tool-gateway"
                and event.correlation_id == action_id
                and event.sequence < failure.sequence
            )
        ]
        all_prepared = [event for event in events if event.type == EventType.PATCH_PREPARED]
        applied = [
            event
            for event in events
            if (event.type == EventType.PATCH_APPLIED and event.correlation_id == action_id)
        ]
        call = calls[0] if len(calls) == 1 else None
        intent = prepared[0] if len(prepared) == 1 else None
        expected_details = None
        if call is not None and intent is not None:
            patch_artifact = call.payload.get(
                "normalized_patch_artifact"
                if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS
                else "patch_artifact"
            )
            candidate_hash = (
                patch_artifact.get("content_hash") if isinstance(patch_artifact, dict) else None
            )
            expected_details = {
                "schema_version": "controlled-rejection-v1",
                "stage": "diagnostic",
                "reason": "controlled_rejection",
                "guidance": (
                    "Review the rehydrated candidate and rejection evidence, "
                    "then retry with a new action_id."
                ),
                "fault_type": "controlled-reject-first-prepared-patch",
                "trigger": "first-preflight-valid-apply-patch",
                "trigger_after": 1,
                "source_call_sequence": call.sequence,
                "source_prepared_sequence": intent.sequence,
                "candidate_content_hash": candidate_hash,
                "input_hash": call.payload.get("input_hash"),
                "prepared_intent_content_hash": intent.payload.get("content_hash"),
                "baseline_worktree_diff_hash": intent.payload.get("baseline_worktree_diff_hash"),
                "expected_worktree_diff_hash": intent.payload.get("expected_worktree_diff_hash"),
                "observed_worktree_diff_hash": intent.payload.get("baseline_worktree_diff_hash"),
                "worktree_mutated": False,
            }
        details = failure.payload.get("error_details")
        valid = bool(
            failure.actor == "tool-gateway"
            and failure.payload.get("tool") == "apply_patch"
            and failure.payload.get("status") == "rejected"
            and isinstance(action_id, str)
            and action_id
            and call is not None
            and intent is not None
            and call.sequence < intent.sequence < failure.sequence
            and failure.sequence == intent.sequence + 1
            and all_prepared
            and intent.sequence == all_prepared[0].sequence
            and expected_details is not None
            and all(
                isinstance(expected_details.get(field), str) and expected_details[field]
                for field in (
                    "candidate_content_hash",
                    "input_hash",
                    "prepared_intent_content_hash",
                    "baseline_worktree_diff_hash",
                    "expected_worktree_diff_hash",
                    "observed_worktree_diff_hash",
                )
            )
            and details == expected_details
            and not applied
        )
        if not valid:
            raise RecoveryError("controlled rejection evidence is malformed")
        return False

    def _controlled_rejection(
        self,
        *,
        action_id: str,
        input_hash: str,
        patch_artifact: Artifact,
        intent: dict[str, Any],
    ) -> ControlledDiagnosticRejection:
        if self._classify_patch_state(intent) != "pre":
            raise RecoveryError("controlled rejection requires the prepared patch pre-state")
        events = self.state.list_events(self.run_id)
        prepared_events = [
            event
            for event in events
            if (event.type == EventType.PATCH_PREPARED and event.correlation_id == action_id)
        ]
        all_prepared = [event for event in events if event.type == EventType.PATCH_PREPARED]
        call_events = [
            event
            for event in events
            if (
                event.type == EventType.TOOL_CALLED
                and event.correlation_id == action_id
                and event.payload.get("tool") == "apply_patch"
            )
        ]
        if len(call_events) != 1 or len(prepared_events) != 1:
            raise RecoveryError(
                "controlled rejection lacks one correlated call and prepared intent"
            )
        call = call_events[0]
        prepared = prepared_events[0]
        if not all_prepared or prepared.sequence != all_prepared[0].sequence:
            raise RecoveryError("controlled rejection is not bound to the first prepared patch")
        if not events or prepared.sequence != events[-1].sequence:
            raise RecoveryError(
                "controlled rejection prepared intent is not the current latest event"
            )
        baseline_hash = str(intent["baseline_worktree_diff_hash"])
        expected_hash = str(intent["expected_worktree_diff_hash"])
        observed = WorkspaceManager.diff_summary(self.workspace)
        if observed.patch_hash != baseline_hash or WorkspaceManager.untracked_files(self.workspace):
            raise RecoveryError("controlled rejection observed a mutated or untracked worktree")
        return ControlledDiagnosticRejection(
            (
                "diagnostic control rejected the first preflight-valid patch "
                "before worktree mutation"
            ),
            details={
                "schema_version": "controlled-rejection-v1",
                "stage": "diagnostic",
                "reason": "controlled_rejection",
                "guidance": (
                    "Review the rehydrated candidate and rejection evidence, "
                    "then retry with a new action_id."
                ),
                "fault_type": self.fault.type,
                "trigger": "first-preflight-valid-apply-patch",
                "trigger_after": self.fault.trigger_after,
                "source_call_sequence": call.sequence,
                "source_prepared_sequence": prepared.sequence,
                "candidate_content_hash": patch_artifact.content_hash,
                "input_hash": input_hash,
                "prepared_intent_content_hash": prepared.payload.get("content_hash"),
                "baseline_worktree_diff_hash": baseline_hash,
                "expected_worktree_diff_hash": expected_hash,
                "observed_worktree_diff_hash": observed.patch_hash,
                "worktree_mutated": False,
            },
        )

    def _error_result(
        self,
        name: str,
        action_id: str,
        started,
        error: Exception,
        *,
        fatal: bool,
        edit_correction: dict[str, Any] | None = None,
    ) -> ToolResult:
        details = dict(getattr(error, "details", {}))
        if edit_correction is not None:
            details["edit_correction"] = edit_correction
        if fatal:
            details["fatal"] = True
        status = "failed" if fatal else "rejected"
        error_payload = {
            "tool": name,
            "status": status,
            "error_code": getattr(error, "code", "INVALID_TOOL_INPUT"),
            "error_message": str(error),
            "error_details": details,
            **(
                {"admission_blocked": True}
                if isinstance(error, WorkPlanAdmissionRejectedError)
                else {}
            ),
        }
        artifact = self.artifacts.put_json(error_payload)
        output: dict[str, Any] = {
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
            "result_artifact": artifact.model_dump(mode="json"),
            "error_details": details,
            **(
                {"admission_blocked": True}
                if isinstance(error, WorkPlanAdmissionRejectedError)
                else {}
            ),
        }
        if fatal:
            output["fatal"] = True
        return ToolResult(
            action_id=action_id,
            status=status,
            started_at=started,
            finished_at=utc_now(),
            output=output,
            error_code=getattr(error, "code", "INVALID_TOOL_INPUT"),
            error_message=str(error),
        )

    def _result_event_payload(
        self,
        name: str,
        result: ToolResult,
    ) -> dict[str, Any]:
        payload = {
            "tool": name,
            "status": result.status,
            "artifact_id": result.output.get("artifact_id"),
            "artifact_path": result.output.get("artifact_path"),
            "result_artifact": result.output.get("result_artifact"),
            "error_code": result.error_code,
            "error_message": (
                result.error_message[:_EVENT_ERROR_MESSAGE_LIMIT] if result.error_message else None
            ),
            "check_id": result.output.get("check_id"),
            "passed": result.output.get("passed"),
            "invocation_status": result.output.get("invocation_status"),
            "behavior_status": result.output.get("behavior_status"),
            "correction_required": result.output.get("correction_required"),
            "failure_summary": result.output.get("failure_summary"),
            "timed_out": result.output.get("timed_out"),
            "worktree_diff_hash": result.output.get("worktree_diff_hash"),
            "patch_hash": result.output.get("patch_hash"),
            "error_details": result.output.get("error_details"),
            "novelty": result.output.get("novelty"),
            "admission_blocked": result.output.get("admission_blocked"),
            "self_directed_exploration_policy_version": result.output.get(
                "self_directed_exploration_policy_version"
            ),
            "investigation_intent": result.output.get("investigation_intent"),
            "investigation_intent_hash": result.output.get("investigation_intent_hash"),
            "investigation_target": result.output.get("investigation_target"),
            "investigation_target_hash": result.output.get("investigation_target_hash"),
            "anchored_read_policy_version": result.output.get("anchored_read_policy_version"),
            "anchored_read_resolution": result.output.get("anchored_read_resolution"),
            "anchored_read_resolution_hash": result.output.get("anchored_read_resolution_hash"),
            "duration_ms": int((result.finished_at - result.started_at).total_seconds() * 1000),
        }
        if self.tool_schema_version in _SELF_VALIDATION_TOOL_SCHEMAS and name in {
            "run_probe",
            "review_task",
        }:
            payload.update(
                {
                    "truncated": result.output.get("truncated"),
                    "exit_code": result.output.get("exit_code"),
                    "original_output_bytes": result.output.get("original_output_bytes"),
                    "source_hash": result.output.get("source_hash"),
                    "source_artifact": result.output.get("source_artifact"),
                    "probe_policy_version": result.output.get("probe_policy_version"),
                    "probe_id": result.output.get("probe_id"),
                    "probe_runtime": result.output.get("probe_runtime"),
                    "timeout_seconds": result.output.get("timeout_seconds"),
                    "output_limit_bytes": result.output.get("output_limit_bytes"),
                    "source_limit_bytes": result.output.get("source_limit_bytes"),
                    "execution_policy": result.output.get("execution_policy"),
                    "review_schema_version": result.output.get("review_schema_version"),
                    "review_artifact": result.output.get("review_artifact"),
                    "review_content_hash": result.output.get("review_content_hash"),
                    "requirement_count": result.output.get("requirement_count"),
                    "targeted_validation_count": result.output.get("targeted_validation_count"),
                    "residual_risk_count": result.output.get("residual_risk_count"),
                    "request_artifact_id": result.output.get("request_artifact_id"),
                    "mutation_event_sequence": result.output.get("mutation_event_sequence"),
                    "source_get_diff_sequence": result.output.get("source_get_diff_sequence"),
                    "self_attestation": result.output.get("self_attestation"),
                    "deterministic_correctness_claimed": (
                        result.output.get("deterministic_correctness_claimed")
                    ),
                }
            )
        if self.tool_schema_version in {"v5", "v6"} and name == "review_task":
            payload.update(
                {
                    "coverage_target_count": result.output.get("coverage_target_count"),
                    "coverage_complete": result.output.get("coverage_complete"),
                    "verified_coverage_target_ids": result.output.get(
                        "verified_coverage_target_ids"
                    ),
                    "unresolved_coverage_target_ids": result.output.get(
                        "unresolved_coverage_target_ids"
                    ),
                }
            )
        if self.tool_schema_version == "v14" and name == "record_work_plan":
            payload.update(
                {
                    "plan_hash": result.output.get("plan_hash"),
                    "plan_event_sequence": result.output.get("plan_event_sequence"),
                    "reproduction_status": result.output.get("reproduction_status"),
                    "candidate_files": result.output.get("candidate_files"),
                    "planned_check_ids": result.output.get("planned_check_ids"),
                }
            )
        if self.tool_schema_version in {
            "v15",
            "v16",
            "v17",
            "v18",
            "v19",
            "v20",
            "v21",
            "v22",
            "v23",
            "v24",
            "v25",
            "v26",
            "v27",
            "v28",
            "v29",
        } and name in {
            "record_work_plan",
            "revise_work_plan",
        }:
            payload.update(
                {
                    "plan_hash": result.output.get("plan_hash"),
                    "plan_event_sequence": result.output.get("plan_event_sequence"),
                    "observation_status": result.output.get("observation_status"),
                    "candidate_files": result.output.get("candidate_files"),
                    "planned_check_ids": result.output.get("planned_check_ids"),
                    "revision_index": result.output.get("revision_index"),
                    "parent_plan_hash": result.output.get("parent_plan_hash"),
                    "trigger": result.output.get("trigger"),
                    "plan_gate_id": result.output.get("plan_gate_id"),
                    **(
                        {
                            "semantic_progress_state_hash": result.output.get(
                                "semantic_progress_state_hash"
                            ),
                            "semantic_reset_required": result.output.get("semantic_reset_required"),
                        }
                        if self.tool_schema_version
                        in {
                            "v19",
                            "v20",
                            "v21",
                            "v22",
                            "v23",
                            "v24",
                            "v25",
                            "v26",
                            "v27",
                            "v28",
                            "v29",
                        }
                        else {}
                    ),
                    **(
                        {
                            "candidate_binding_policy_version": result.output.get(
                                "candidate_binding_policy_version"
                            ),
                            "candidate_binding_normalization_hash": result.output.get(
                                "candidate_binding_normalization_hash"
                            ),
                        }
                        if self.tool_schema_version
                        in {"v20", "v21", "v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29"}
                        else {}
                    ),
                    **(
                        {
                            "causal_activation_policy_version": result.output.get(
                                "causal_activation_policy_version"
                            ),
                            "causal_mechanism_hash": result.output.get("causal_mechanism_hash"),
                            "causal_plan_binding_hash": result.output.get(
                                "causal_plan_binding_hash"
                            ),
                            "cross_reset_failure_trigger_hash": result.output.get(
                                "cross_reset_failure_trigger_hash"
                            ),
                        }
                        if self.tool_schema_version
                        in {"v21", "v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29"}
                        else {}
                    ),
                }
            )
        return payload

    def _complete_result(
        self,
        name: str,
        input_hash: str,
        result: ToolResult,
    ) -> None:
        patch_payload = None
        if name in _MUTATION_TOOL_NAMES and result.status == "succeeded":
            patch_payload = {
                "patch_hash": result.output["patch_hash"],
                "worktree_diff_hash": result.output["worktree_diff_hash"],
            }
            if self.tool_schema_version in {
                "v14",
                "v15",
                "v16",
                "v17",
                "v18",
                "v19",
                "v20",
                "v21",
                "v22",
                "v23",
                "v24",
                "v25",
                "v26",
                "v27",
                "v28",
                "v29",
            }:
                plan_hash = result.output.get("plan_hash")
                if not isinstance(plan_hash, str):
                    raise RecoveryError("Lean workflow mutation lost its recorded plan binding")
                patch_payload["plan_hash"] = plan_hash
        admission_payload = None
        if (
            result.error_code == "WORK_PLAN_ADMISSION_REJECTED"
            and result.output.get("admission_blocked") is True
        ):
            details = result.output.get("error_details")
            if not isinstance(details, dict):
                raise RecoveryError("work-plan admission rejection lacks typed details")
            admission_payload = {
                "schema_version": "work-plan-admission-blocked-v1",
                "policy_version": details.get("policy_version", WORK_PLAN_ADMISSION_POLICY),
                "tool": name,
                "execution": "not_dispatched",
                "plan_gate_id": details.get("plan_gate_id"),
                "attempt": details.get("attempt"),
                "reason_codes": details.get("reason_codes"),
                "eligible_catalog_hash": details.get("eligible_catalog_hash"),
                "worktree_diff_hash": details.get("worktree_diff_hash"),
            }
        self.state.complete_action(
            self.run_id,
            result.action_id,
            input_hash,
            result,
            outcome_type=(
                EventType.TOOL_SUCCEEDED if result.status == "succeeded" else EventType.TOOL_FAILED
            ),
            outcome_payload=self._result_event_payload(name, result),
            patch_payload=patch_payload,
            admission_payload=admission_payload,
        )

    def reconcile_interrupted_patch(
        self,
        checkpoint: Checkpoint,
    ) -> ToolResult | None:
        """Complete one v2 patch action that crossed a hard process boundary."""

        if self.tool_schema_version not in _STRUCTURED_TOOL_SCHEMAS:
            return None
        events = self.state.list_events(self.run_id)
        controlled_rejection_pending = self._controlled_rejection_pending()
        calls = [
            event
            for event in events
            if event.sequence > checkpoint.through_sequence
            and event.type == EventType.TOOL_CALLED
            and event.payload.get("tool") in _MUTATION_TOOL_NAMES
        ]
        if not calls:
            return None
        if len(calls) != 1:
            raise RecoveryError("recovery found multiple patch calls after the latest checkpoint")
        call = calls[0]
        mutation_tool = call.payload.get("tool")
        if mutation_tool not in _MUTATION_TOOL_NAMES:
            raise RecoveryError("interrupted mutation tool identity differs")
        if call.correlation_id is None:
            raise RecoveryError("interrupted patch call lacks an action identity")
        action_id = call.correlation_id
        input_hash = call.payload.get("input_hash")
        if not isinstance(input_hash, str):
            raise RecoveryError("interrupted patch call lacks its input hash")
        prior = self.state.get_action_result(
            self.run_id,
            action_id,
            input_hash,
        )
        prepared_events = [
            event
            for event in events
            if event.sequence > call.sequence
            and event.type == EventType.PATCH_PREPARED
            and event.correlation_id == action_id
        ]
        if len(prepared_events) > 1:
            raise RecoveryError("interrupted patch has duplicate prepared intents")

        current = WorkspaceManager.diff_summary(self.workspace)
        if WorkspaceManager.untracked_files(self.workspace):
            raise RecoveryError("agent workspace contains untracked files during patch recovery")
        if prior is not None:
            if prior.status == "succeeded":
                if not prepared_events:
                    raise RecoveryError("successful interrupted patch lacks a prepared intent")
                intent, patch = self._load_patch_intent(
                    call,
                    prepared_events[0],
                )
                state = self._classify_patch_state(intent)
                if state != "post":
                    raise RecoveryError(
                        "successful interrupted patch is not in its prepared post-state"
                    )
                if current.patch_hash != prior.output.get("worktree_diff_hash") or sha256_text(
                    patch
                ) != prior.output.get("patch_hash"):
                    raise RecoveryError(
                        "successful interrupted patch conflicts with its durable result"
                    )
            elif current.patch_hash != checkpoint.worktree_diff_hash:
                raise RecoveryError("failed interrupted patch did not restore its checkpoint state")
            self._complete_result(str(mutation_tool), input_hash, prior)
            return prior

        started = call.timestamp
        try:
            patch = self._load_call_patch(call)
            if prepared_events:
                intent, prepared_patch = self._load_patch_intent(
                    call,
                    prepared_events[0],
                )
                if prepared_patch != patch:
                    raise RecoveryError("prepared patch bytes conflict with ToolCalled evidence")
            else:
                if current.patch_hash != checkpoint.worktree_diff_hash:
                    raise RecoveryError(
                        "workspace changed before a durable patch intent was recorded"
                    )
                patch_artifact = Artifact.model_validate(
                    call.payload.get(
                        "normalized_patch_artifact"
                        if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS
                        else "patch_artifact"
                    )
                )
                intent = self._prepare_patch_mutation(
                    action_id,
                    input_hash,
                    patch,
                    patch_artifact,
                )
            if intent.get("baseline_worktree_diff_hash") != checkpoint.worktree_diff_hash:
                raise RecoveryError("prepared patch baseline does not match the durable checkpoint")
            if controlled_rejection_pending:
                patch_artifact = Artifact.model_validate(
                    call.payload.get(
                        "normalized_patch_artifact"
                        if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS
                        else "patch_artifact"
                    )
                )
                result = self._error_result(
                    str(mutation_tool),
                    action_id,
                    started,
                    self._controlled_rejection(
                        action_id=action_id,
                        input_hash=input_hash,
                        patch_artifact=patch_artifact,
                        intent=intent,
                    ),
                    fatal=False,
                )
                self._complete_result(str(mutation_tool), input_hash, result)
                return result
            state = self._classify_patch_state(intent)
            if state == "mixed":
                hypothetical = self._hypothetical_preimage_diff_hash(intent)
                if hypothetical != intent["baseline_worktree_diff_hash"]:
                    raise RecoveryError(
                        "mixed patch state includes changes outside the prepared mutation"
                    )
                self._restore_patch_preimages(intent)
                state = "pre"
            if state == "pre":
                output = self._apply_patch(patch, intent=intent)
            elif state == "post":
                output = self._finalize_applied_patch(
                    patch,
                    str(intent["baseline_worktree_diff_hash"]),
                    expected_diff_hash=str(intent["expected_worktree_diff_hash"]),
                    intent=intent,
                )
            else:
                raise RecoveryError(f"unsupported interrupted patch state: {state}")
            artifact = self.artifacts.put_json(output)
            result = ToolResult(
                action_id=action_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    **output,
                },
            )
        except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
            result = self._error_result(
                str(mutation_tool),
                action_id,
                started,
                exc,
                fatal=False,
            )
        except RecoveryError as exc:
            result = self._error_result(
                str(mutation_tool),
                action_id,
                started,
                exc,
                fatal=True,
            )
        self._complete_result(str(mutation_tool), input_hash, result)
        return result

    def reconcile_interrupted_action(
        self,
        checkpoint: Checkpoint,
    ) -> tuple[str, ToolResult] | None:
        """Complete one non-mutating v2 action without another ToolCalled."""

        if self.tool_schema_version not in _STRUCTURED_TOOL_SCHEMAS:
            return None
        events = self.state.list_events(self.run_id)
        calls = [
            event
            for event in events
            if event.sequence > checkpoint.through_sequence
            and event.type == EventType.TOOL_CALLED
            and event.payload.get("tool") not in {*_MUTATION_TOOL_NAMES, "finish_task"}
        ]
        if not calls:
            return None
        if len(calls) != 1:
            raise RecoveryError(
                "recovery found multiple non-patch calls after the latest checkpoint"
            )
        call = calls[0]
        if call.correlation_id is None:
            raise RecoveryError("interrupted tool call lacks an action identity")
        (
            name,
            arguments,
            input_hash,
            execution_context,
        ) = self._load_call_input(call)
        prior = self.state.get_action_result(
            self.run_id,
            call.correlation_id,
            input_hash,
        )
        if (
            self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
            and name in {"read_file", "search_files"}
            and call.payload.get("execution") == "semantic-cache-replay"
        ):
            normalized_call_hash = call.payload.get("normalized_call_hash")
            worktree_diff_hash = call.payload.get("worktree_diff_hash")
            if not isinstance(normalized_call_hash, str) or not isinstance(worktree_diff_hash, str):
                raise RecoveryError("semantic replay call lacks a valid inspection identity")
            current_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
            expected_normalized_hash = self._normalized_call_hash(
                name,
                arguments,
                worktree_diff_hash=worktree_diff_hash,
            )
            if (
                worktree_diff_hash != current_diff_hash
                or normalized_call_hash != expected_normalized_hash
            ):
                raise RecoveryError(
                    "semantic replay call no longer matches the worktree or canonical input"
                )
            if prior is not None:
                semantic_suffix = [
                    event
                    for event in events
                    if event.sequence > call.sequence
                    and event.correlation_id == call.correlation_id
                    and event.type in {EventType.LOOP_DETECTED, EventType.TOOL_REPLAYED}
                ]
                if [event.type for event in semantic_suffix] != [
                    EventType.LOOP_DETECTED,
                    EventType.TOOL_REPLAYED,
                ] or any(
                    event.actor != expected_actor or event.payload.get("tool") != name
                    for event, expected_actor in zip(
                        semantic_suffix,
                        ("tool-gateway", "semantic-cache"),
                        strict=True,
                    )
                ):
                    raise RecoveryError("semantic replay action has an invalid durable suffix")
                return name, prior
            replay = self._semantic_inspection_replay(
                name=name,
                action_id=call.correlation_id,
                arguments=arguments,
                input_hash=input_hash,
                normalized_call_hash=normalized_call_hash,
                worktree_diff_hash=worktree_diff_hash,
                existing_call_payload=call.payload,
            )
            if replay is None:
                raise RecoveryError("interrupted semantic replay can no longer be derived")
            return name, replay
        outcomes = [
            event
            for event in events
            if event.sequence > call.sequence
            and event.correlation_id == call.correlation_id
            and event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        ]
        if len(outcomes) > 1:
            raise RecoveryError("interrupted tool call has duplicate durable outcomes")
        if outcomes and prior is None:
            raise RecoveryError("tool outcome exists without its atomic action result")
        if prior is not None:
            self._complete_result(name, input_hash, prior)
            return name, prior

        started = call.timestamp
        if name == "run_probe":
            result = self._error_result(
                name,
                call.correlation_id,
                started,
                RecoveryError(
                    "interrupted ephemeral probe cannot be safely "
                    "redispatched after a process boundary"
                ),
                fatal=True,
            )
            self._complete_result(name, input_hash, result)
            return name, result
        try:
            output = (
                self._dispatch(
                    name,
                    arguments,
                    execution_context=execution_context,
                )
                if name == "review_task"
                else self._dispatch(name, arguments)
            )
            if self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES and name in {
                "read_file",
                "search_files",
            }:
                worktree_diff_hash = call.payload.get("worktree_diff_hash")
                if not isinstance(worktree_diff_hash, str):
                    raise RecoveryError("v4 inspection call lacks a worktree diff identity")
                output = self._annotate_inspection_result(
                    name=name,
                    output=output,
                    worktree_diff_hash=worktree_diff_hash,
                )
            artifact = self.artifacts.put_json(output)
            result_artifact = (
                artifact.model_dump(mode="json")
                if (
                    self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES
                    and name in {"read_file", "search_files"}
                )
                or (
                    self.tool_schema_version in _SELF_VALIDATION_TOOL_SCHEMAS
                    and name in {"run_probe", "review_task"}
                )
                or (
                    self.context_policy_version in {"phase-evidence-v10", "phase-evidence-v11"}
                    and name in {"run_check", "get_diff"}
                )
                else None
            )
            result = ToolResult(
                action_id=call.correlation_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    **({"result_artifact": result_artifact} if result_artifact is not None else {}),
                    **output,
                },
            )
        except (ContractError, PolicyViolation, TypeError, ValueError) as exc:
            result = self._error_result(
                name,
                call.correlation_id,
                started,
                exc,
                fatal=False,
            )
        except RecoveryError as exc:
            result = self._error_result(
                name,
                call.correlation_id,
                started,
                exc,
                fatal=True,
            )
        self._complete_result(name, input_hash, result)
        return name, result

    def _load_call_input(
        self,
        call,
    ) -> tuple[
        str,
        dict[str, Any],
        str,
        dict[str, Any] | None,
    ]:
        try:
            artifact = Artifact.model_validate(call.payload["input_artifact"])
            raw = self.artifacts.read_bytes(artifact)
            value = json.loads(raw.decode("utf-8", errors="strict"))
            name = value["tool"]
            arguments = value["input"]
            execution_context = value.get("execution_context")
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError("interrupted tool call lacks valid input evidence") from exc
        if (
            not isinstance(name, str)
            or name != call.payload.get("tool")
            or name in {"apply_patch", "finish_task"}
            or not isinstance(arguments, dict)
            or (execution_context is not None and not isinstance(execution_context, dict))
            or (name != "review_task" and execution_context is not None)
            or (
                name == "review_task"
                and self.tool_schema_version in _SELF_VALIDATION_TOOL_SCHEMAS
                and execution_context is None
            )
            or call.payload.get("artifact_id") != artifact.artifact_id
            or call.payload.get("artifact_path") != artifact.path
        ):
            raise RecoveryError("interrupted tool input conflicts with ToolCalled evidence")
        input_hash = sha256_text(canonical_json({"tool": name, "input": arguments}))
        if input_hash != call.payload.get("input_hash"):
            raise RecoveryError("interrupted tool input does not match its call hash")
        return name, arguments, input_hash, execution_context

    def _load_call_patch(self, call) -> str:
        try:
            artifact = Artifact.model_validate(call.payload["patch_artifact"])
            content = self.artifacts.read_bytes(artifact)
            patch = content.decode("utf-8", errors="strict")
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise RecoveryError("interrupted patch lacks valid raw input evidence") from exc
        tool_name = call.payload.get("tool")
        if tool_name == "apply_patch":
            expected_input_hash = sha256_text(
                canonical_json({"tool": "apply_patch", "input": {"patch": patch}})
            )
        elif tool_name == STRUCTURED_EDIT_TOOL_NAME:
            try:
                input_artifact = Artifact.model_validate(call.payload["input_artifact"])
                input_document = json.loads(
                    self.artifacts.read_bytes(input_artifact).decode("utf-8", errors="strict")
                )
                projection_artifact = Artifact.model_validate(
                    call.payload["structured_edit_projection_artifact"]
                )
                projection = AtomicStructuredEditProjection.model_validate_json(
                    self.artifacts.read_bytes(projection_artifact)
                )
                gateway_artifact = Artifact.model_validate(
                    call.payload["structured_edit_gateway_patch_artifact"]
                )
                gateway_patch = StructuredEditGatewayPatch.model_validate_json(
                    self.artifacts.read_bytes(gateway_artifact)
                )
                refresh_raw = call.payload.get("structured_edit_refresh_projection_artifact")
                refresh_projection = None
                if refresh_raw is not None:
                    refresh_artifact = Artifact.model_validate(refresh_raw)
                    refresh_projection = FreshStructuredEditProjection.model_validate_json(
                        self.artifacts.read_bytes(refresh_artifact)
                    )
            except (
                KeyError,
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as exc:
                raise RecoveryError(
                    "interrupted structured edit lacks valid projection evidence"
                ) from exc
            expected_requested_arguments = (
                refresh_projection.requested_arguments.model_dump(mode="json")
                if refresh_projection is not None
                else projection.arguments.model_dump(mode="json")
            )
            if not (
                type(input_document) is dict
                and input_document.get("tool") == STRUCTURED_EDIT_TOOL_NAME
                and input_document.get("input") == expected_requested_arguments
                and projection.action_id == call.correlation_id
                and gateway_patch.structured_edit_content_hash == projection.content_hash
                and gateway_patch.patch == patch
                and (
                    refresh_projection is None
                    or (
                        refresh_projection.action_id == call.correlation_id
                        and refresh_projection.atomic_projection == projection
                        and refresh_projection.derived_arguments == projection.arguments
                    )
                )
            ):
                raise RecoveryError("interrupted structured edit evidence differs")
            expected_input_hash = sha256_text(canonical_json(input_document))
        else:
            raise RecoveryError("interrupted patch tool identity differs")
        if expected_input_hash != call.payload.get("input_hash"):
            raise RecoveryError("interrupted patch input does not match its ToolCalled hash")
        if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS:
            try:
                normalized_patch, expected_normalization = _normalize_raw_git_patch(patch)
                normalized_artifact = Artifact.model_validate(
                    call.payload["normalized_patch_artifact"]
                )
                normalization_artifact = Artifact.model_validate(
                    call.payload["patch_normalization_artifact"]
                )
                observed_normalization = json.loads(
                    self.artifacts.read_bytes(normalization_artifact).decode(
                        "utf-8", errors="strict"
                    )
                )
            except (
                KeyError,
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as exc:
                raise RecoveryError(
                    "interrupted v8 patch lacks valid normalization evidence"
                ) from exc
            if self.artifacts.read_bytes(normalized_artifact) != normalized_patch.encode(
                "utf-8"
            ) or canonical_json(observed_normalization) != canonical_json(expected_normalization):
                raise RecoveryError("interrupted v8 patch normalization evidence differs")
            return normalized_patch
        return patch

    def _load_patch_intent(
        self,
        call,
        prepared_event,
    ) -> tuple[dict[str, Any], str]:
        try:
            artifact = Artifact.model_validate(prepared_event.payload["intent_artifact"])
            raw = self.artifacts.read_bytes(artifact)
            intent = json.loads(raw.decode("utf-8", errors="strict"))
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError("prepared patch intent artifact is invalid") from exc
        if not isinstance(intent, dict):
            raise RecoveryError("prepared patch intent must be a JSON object")
        if (
            intent.get("schema_version") != "patch-mutation-intent-v1"
            or intent.get("run_id") != self.run_id
            or intent.get("action_id") != call.correlation_id
            or intent.get("input_hash") != call.payload.get("input_hash")
            or prepared_event.payload.get("content_hash") != artifact.content_hash
            or prepared_event.payload.get("baseline_worktree_diff_hash")
            != intent.get("baseline_worktree_diff_hash")
            or prepared_event.payload.get("expected_worktree_diff_hash")
            != intent.get("expected_worktree_diff_hash")
        ):
            raise RecoveryError("prepared patch intent conflicts with its event identity")
        patch = self._load_call_patch(call)
        try:
            intent_patch_artifact = Artifact.model_validate(intent["patch_artifact"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RecoveryError("prepared patch intent lacks its raw patch artifact") from exc
        expected_patch_artifact = call.payload.get(
            "normalized_patch_artifact"
            if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS
            else "patch_artifact"
        )
        if intent_patch_artifact.model_dump(mode="json") != expected_patch_artifact or (
            self.artifacts.read_bytes(intent_patch_artifact) != patch.encode("utf-8")
        ):
            raise RecoveryError("prepared patch artifact conflicts with ToolCalled evidence")
        files = intent.get("files")
        if not isinstance(files, list) or not files:
            raise RecoveryError("prepared patch intent has no file images")
        paths: list[str] = []
        try:
            for entry in files:
                if (
                    not isinstance(entry, dict)
                    or set(entry)
                    != {
                        "path",
                        "mode",
                        "git_mode",
                        "preimage_artifact",
                        "postimage_artifact",
                    }
                    or type(entry["mode"]) is not int
                    or not 0 <= entry["mode"] <= 0o7777
                    or entry["git_mode"] not in {"100644", "100755"}
                ):
                    raise ValueError("invalid file image entry")
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                preimage_artifact = Artifact.model_validate(entry["preimage_artifact"])
                self.artifacts.read_bytes(preimage_artifact)
                postimage_raw = entry["postimage_artifact"]
                if postimage_raw is not None:
                    postimage_artifact = Artifact.model_validate(postimage_raw)
                    self.artifacts.read_bytes(postimage_artifact)
                paths.append(path)
        except (ContractError, KeyError, TypeError, ValueError) as exc:
            raise RecoveryError("prepared patch contains invalid file image evidence") from exc
        try:
            patch_paths = _patch_paths(patch)
        except ContractError as exc:
            raise RecoveryError(
                "prepared patch raw input no longer satisfies its contract"
            ) from exc
        if paths != patch_paths:
            raise RecoveryError("prepared patch file images do not match the raw patch")
        return intent, patch

    def _classify_patch_state(self, intent: dict[str, Any]) -> str:
        states: list[str] = []
        for entry in intent["files"]:
            try:
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                pre_artifact = Artifact.model_validate(entry["preimage_artifact"])
                post_raw = entry.get("postimage_artifact")
                post_artifact = Artifact.model_validate(post_raw) if post_raw is not None else None
                preimage = self.artifacts.read_bytes(pre_artifact)
                postimage = (
                    self.artifacts.read_bytes(post_artifact) if post_artifact is not None else None
                )
                mode = int(entry["mode"])
            except (ContractError, KeyError, TypeError, ValueError) as exc:
                raise RecoveryError("prepared patch contains invalid file image evidence") from exc
            target = self._prepared_workspace_target(path, recovery=True)
            if target.exists():
                target_stat = target.lstat()
                if not stat.S_ISREG(target_stat.st_mode):
                    raise RecoveryError(
                        f"prepared patch target is no longer a regular file: {path}"
                    )
                if stat.S_IMODE(target_stat.st_mode) != mode:
                    raise RecoveryError(f"prepared patch target mode changed: {path}")
                current = target.read_bytes()
                if current == preimage:
                    states.append("pre")
                elif postimage is not None and current == postimage:
                    states.append("post")
                else:
                    raise RecoveryError(f"prepared patch target is in an unknown state: {path}")
            elif postimage is None:
                states.append("post")
            else:
                raise RecoveryError(f"prepared patch target is unexpectedly missing: {path}")

        summary = WorkspaceManager.diff_summary(self.workspace)
        state_set = set(states)
        if state_set == {"pre"}:
            if summary.patch_hash != intent["baseline_worktree_diff_hash"]:
                raise RecoveryError("pre-state files do not match the prepared baseline diff")
            return "pre"
        if state_set == {"post"}:
            if summary.patch_hash != intent["expected_worktree_diff_hash"]:
                raise RecoveryError("post-state files do not match the prepared expected diff")
            return "post"
        if state_set == {"pre", "post"}:
            return "mixed"
        raise RecoveryError("prepared patch has an invalid file-state classification")

    def _restore_patch_preimages(self, intent: dict[str, Any]) -> None:
        recovery_root = self.artifacts.root / "recovery-tmp" / self.run_id
        recovery_root.mkdir(parents=True, exist_ok=True)
        for entry in intent["files"]:
            path = safe_relative_path(
                str(entry["path"]),
                field_name="prepared patch path",
            )
            artifact = Artifact.model_validate(entry["preimage_artifact"])
            preimage = self.artifacts.read_bytes(artifact)
            target = self._prepared_workspace_target(path, recovery=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = recovery_root / f"{uuid.uuid4().hex}.tmp"
            try:
                with temporary.open("xb") as stream:
                    stream.write(preimage)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, int(entry["mode"]))
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        restored = WorkspaceManager.diff_summary(self.workspace)
        if restored.patch_hash != intent[
            "baseline_worktree_diff_hash"
        ] or WorkspaceManager.untracked_files(self.workspace):
            raise RecoveryError("prepared patch preimages did not restore the durable baseline")

    def _prepared_workspace_target(
        self,
        path: str,
        *,
        recovery: bool,
    ) -> Path:
        safe = safe_relative_path(path, field_name="prepared patch path")
        root = self.workspace.resolve()
        parts = PurePosixPath(safe).parts
        target = root.joinpath(*parts)
        cursor = root
        for part in parts:
            cursor = cursor / part
            is_junction = bool(getattr(cursor, "is_junction", lambda: False)())
            if cursor.is_symlink() or is_junction:
                message = f"prepared patch path contains a symlink or junction: {safe}"
                if recovery:
                    raise RecoveryError(message)
                raise _patch_contract_error(
                    message,
                    reason="unsupported_target",
                    stage="policy",
                )
        resolved_target = target.resolve(strict=False)
        if os.path.commonpath([str(root), str(resolved_target)]) != str(root):
            message = f"prepared patch path escapes workspace: {safe}"
            if recovery:
                raise RecoveryError(message)
            raise _patch_contract_error(
                message,
                reason="unsupported_target",
                stage="policy",
            )
        return target

    def _normalized_call_hash(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        worktree_diff_hash: str | None = None,
    ) -> str:
        summary = (
            None
            if worktree_diff_hash is not None
            else WorkspaceManager.diff_summary(self.workspace)
        )
        current_diff_hash = (
            worktree_diff_hash if worktree_diff_hash is not None else summary.patch_hash
        )
        state_marker: int | None = None
        if name == "get_diff":
            current_checks = [
                event.sequence
                for event in self.state.list_events(self.run_id)
                if event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") == "run_check"
                and event.payload.get("worktree_diff_hash") == current_diff_hash
            ]
            state_marker = max(current_checks, default=None)
        return sha256_text(
            canonical_json(
                {
                    "tool": name,
                    "input": arguments,
                    "worktree_diff_hash": current_diff_hash,
                    "state_marker": state_marker,
                }
            )
        )

    def _structured_edit_gateway_patch(
        self,
        *,
        action_id: str,
        arguments: dict[str, Any],
        worktree_diff_hash: str,
    ):
        """Refresh successor preimages, then render the atomic mutation input."""

        fresh_projection: FreshStructuredEditProjection | None = None
        try:
            if self.tool_schema_version in {
                "v10",
                "v11",
                "v12",
                "v13",
                "v14",
                "v15",
                "v16",
                "v17",
                "v18",
                "v19",
                "v20",
                "v21",
                "v22",
                "v23",
                "v24",
                "v25",
                "v26",
                "v27",
                "v28",
                "v29",
            } and self.context_policy_version in {
                "phase-evidence-v15",
                "phase-evidence-v16",
                "phase-evidence-v17",
                "phase-evidence-v18",
                "phase-evidence-v19",
                "phase-evidence-v20",
                "phase-evidence-v21",
                "phase-evidence-v22",
                "phase-evidence-v23",
                "phase-evidence-v24",
                "phase-evidence-v25",
                "phase-evidence-v26",
                "phase-evidence-v27",
                "phase-evidence-v28",
                "phase-evidence-v29",
                "phase-evidence-v30",
                "phase-evidence-v31",
                "phase-evidence-v32",
                "phase-evidence-v33",
                "phase-evidence-v34",
                "phase-evidence-v35",
                "phase-evidence-v36",
                "phase-evidence-v37",
                "phase-evidence-v38",
            }:
                fresh_arguments = FreshStructuredEditArguments.model_validate_json(
                    canonical_json(arguments)
                )
                requested_files = fresh_arguments.files
            else:
                structured_arguments = StructuredEditArguments.model_validate_json(
                    canonical_json(arguments)
                )
                if structured_arguments.source_worktree_diff_hash != worktree_diff_hash:
                    raise ContractError("apply_structured_edit source diff is stale")
                requested_files = structured_arguments.files
        except ValueError as exc:
            raise ContractError("apply_structured_edit arguments are invalid") from exc
        preimages: dict[str, bytes] = {}
        for requested in requested_files:
            target = ensure_within(self.workspace, requested.path)
            if not target.is_file():
                raise ContractError(
                    f"apply_structured_edit target is unavailable: {requested.path}"
                )
            preimages[requested.path] = target.read_bytes()
        if self.tool_schema_version in {
            "v10",
            "v11",
            "v12",
            "v13",
            "v14",
            "v15",
            "v16",
            "v17",
            "v18",
            "v19",
            "v20",
            "v21",
            "v22",
            "v23",
            "v24",
            "v25",
            "v26",
            "v27",
            "v28",
            "v29",
        } and self.context_policy_version in {
            "phase-evidence-v15",
            "phase-evidence-v16",
            "phase-evidence-v17",
            "phase-evidence-v18",
            "phase-evidence-v19",
            "phase-evidence-v20",
            "phase-evidence-v21",
            "phase-evidence-v22",
            "phase-evidence-v23",
            "phase-evidence-v24",
            "phase-evidence-v25",
            "phase-evidence-v26",
            "phase-evidence-v27",
            "phase-evidence-v28",
            "phase-evidence-v29",
            "phase-evidence-v30",
            "phase-evidence-v31",
            "phase-evidence-v32",
            "phase-evidence-v33",
            "phase-evidence-v34",
            "phase-evidence-v35",
            "phase-evidence-v36",
            "phase-evidence-v37",
            "phase-evidence-v38",
        }:
            fresh_projection = project_fresh_atomic_structured_edit(
                action_id=action_id,
                arguments=fresh_arguments,
                source_worktree_diff_hash=worktree_diff_hash,
                preimages=preimages,
                constraints=self.task.constraints,
            )
            structured = fresh_projection.atomic_projection
        else:
            structured = project_atomic_structured_edit(
                action_id=action_id,
                arguments=structured_arguments,
                preimages=preimages,
                constraints=self.task.constraints,
            )
        gateway_patch = render_structured_edit_gateway_patch(structured)
        if gateway_patch.source_worktree_diff_hash != worktree_diff_hash:
            raise ContractError("structured gateway patch source diff differs")
        return structured, gateway_patch, fresh_projection

    def _dispatch(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        execution_context: dict[str, Any] | None = None,
        probe_source_artifact: Artifact | None = None,
    ) -> dict[str, Any]:
        if name == "read_file":
            return self._read_file(**arguments)
        if name == "search_files":
            return self._search_files(**arguments)
        if name == "apply_patch":
            return self._apply_patch(**arguments)
        if name == "run_check":
            return self._run_check(**arguments)
        if name == "get_diff":
            return self._get_diff()
        if self.tool_schema_version == "v14" and name == "record_work_plan":
            return self._record_work_plan(arguments)
        if self.tool_schema_version in {
            "v15",
            "v16",
            "v17",
            "v18",
            "v19",
            "v20",
            "v21",
            "v22",
            "v23",
            "v24",
            "v25",
            "v26",
            "v27",
            "v28",
            "v29",
        } and name in {
            "record_work_plan",
            "revise_work_plan",
        }:
            return self._record_work_plan_v2(
                arguments,
                execution_context=execution_context,
                revision=name == "revise_work_plan",
            )
        if self.tool_schema_version in _SELF_VALIDATION_TOOL_SCHEMAS and name == "run_probe":
            return self._run_probe(
                **arguments,
                source_artifact=probe_source_artifact,
            )
        if self.tool_schema_version in _SELF_VALIDATION_TOOL_SCHEMAS and name == "review_task":
            return self._review_task(
                **arguments,
                execution_context=execution_context,
            )
        raise ContractError(f"unknown tool: {name}")

    def _record_work_plan(self, arguments: dict[str, Any]) -> dict[str, Any]:
        current_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
        events = self.state.list_events(self.run_id)
        read_paths: dict[int, str] = {}
        for event in events:
            if (
                event.type != EventType.TOOL_SUCCEEDED
                or event.payload.get("tool") != "read_file"
                or event.payload.get("worktree_diff_hash") != current_diff_hash
            ):
                continue
            try:
                descriptor = Artifact.model_validate(event.payload.get("result_artifact"))
                document = json.loads(
                    self.artifacts.read_bytes(descriptor).decode("utf-8", errors="strict")
                )
            except (UnicodeDecodeError, ValueError, OSError) as exc:
                raise RecoveryError("record_work_plan read evidence is unavailable") from exc
            path = document.get("path") if isinstance(document, dict) else None
            if not isinstance(path, str):
                raise ContractError("record_work_plan read evidence lacks a public path")
            read_paths[event.sequence] = path
        plan = validate_record_work_plan(
            run_id=self.run_id,
            task=self.task,
            worktree_diff_hash=current_diff_hash,
            events=events,
            read_paths_by_sequence=read_paths,
            arguments=arguments,
        )
        prior = [
            event
            for event in events
            if event.type == EventType.PLAN_RECORDED
            and event.payload.get("plan_hash") == plan.content_hash
            and event.payload.get("worktree_diff_hash") == current_diff_hash
        ]
        if prior:
            plan_event = prior[-1]
        else:
            plan_event = self.state.append_event(
                self.run_id,
                EventType.PLAN_RECORDED,
                actor="workflow-state-machine",
                payload={
                    "schema_version": PLAN_RECORDED_EVENT_SCHEMA,
                    "task_id": plan.task_id,
                    "task_version": plan.task_version,
                    "public_task_hash": plan.public_task_hash,
                    "worktree_diff_hash": plan.worktree_diff_hash,
                    "plan_hash": plan.content_hash,
                    "reproduction_status": plan.reproduction_status,
                    "evidence_event_sequences": list(plan.evidence_event_sequences),
                    "candidate_files": list(plan.candidate_files),
                    "planned_check_ids": list(plan.planned_check_ids),
                    "plan": plan.model_dump(mode="json"),
                    "public_evidence_only": True,
                },
            )
        return {
            "plan_hash": plan.content_hash,
            "plan_event_sequence": plan_event.sequence,
            "reproduction_status": plan.reproduction_status,
            "candidate_files": list(plan.candidate_files),
            "planned_check_ids": list(plan.planned_check_ids),
            "worktree_diff_hash": current_diff_hash,
            "idempotent": bool(prior),
        }

    def _current_work_plan(self, worktree_diff_hash: str) -> RecordedWorkPlan | None:
        expected_task_hash = sha256_text(canonical_json(self.task.model_dump(mode="json")))
        plan_events = [
            event
            for event in self.state.list_events(self.run_id)
            if event.type == EventType.PLAN_RECORDED
            and event.payload.get("schema_version") == PLAN_RECORDED_EVENT_SCHEMA
            and event.payload.get("task_id") == self.task.task_id
            and event.payload.get("task_version") == self.task.task_version
            and event.payload.get("public_task_hash") == expected_task_hash
        ]
        direct = [
            event
            for event in plan_events
            if event.payload.get("worktree_diff_hash") == worktree_diff_hash
        ]
        linked_patch = next(
            (
                event
                for event in reversed(self.state.list_events(self.run_id))
                if event.type == EventType.PATCH_APPLIED
                and event.payload.get("worktree_diff_hash") == worktree_diff_hash
                and isinstance(event.payload.get("plan_hash"), str)
            ),
            None,
        )
        matching = direct
        if not matching and linked_patch is not None:
            matching = [
                event
                for event in plan_events
                if event.payload.get("plan_hash") == linked_patch.payload.get("plan_hash")
            ]
        if not matching:
            return None
        plans: list[RecordedWorkPlan] = []
        for event in matching:
            try:
                plan = RecordedWorkPlan.model_validate_json(
                    canonical_json(event.payload.get("plan"))
                )
            except ValueError as exc:
                raise RecoveryError("current work plan event is invalid") from exc
            if (
                event.payload.get("plan_hash") != plan.content_hash
                or plan.run_id != self.run_id
                or (
                    plan.worktree_diff_hash != worktree_diff_hash
                    and (
                        linked_patch is None
                        or linked_patch.payload.get("plan_hash") != plan.content_hash
                    )
                )
            ):
                raise RecoveryError("current work plan event binding differs")
            plans.append(plan)
        if len({plan.content_hash for plan in plans}) > 1:
            raise RecoveryError("current diff has conflicting recorded work plans")
        return plans[-1]

    def _record_work_plan_v2(
        self,
        arguments: dict[str, Any],
        *,
        execution_context: dict[str, Any] | None,
        revision: bool,
    ) -> dict[str, Any]:
        """Validate and durably record one request-bound V11/V12 plan."""

        if not isinstance(execution_context, dict):
            raise RecoveryError("work-plan tool lacks its exact request context")
        request_artifact_id = execution_context.get("request_artifact_id")
        request_body_hash = execution_context.get("request_body_hash")
        phase_evidence: EvidenceState | None = None
        semantic_progress_state: PublicSemanticProgressState | None = None
        semantic_progress_event_domain: SemanticProgressEventDomain | None = None
        candidate_binding_normalization: CandidateBindingNormalization | None = None
        cross_reset_trigger: CrossResetFailureTrigger | None = None
        cross_reset_baseline: MutationBaselineProjection | None = None
        cross_reset_receipt: MutationBaselineRestoreReceipt | None = None
        causal_history: (
            tuple[CausalMechanismHistoryEntry, ...] | tuple[CausalMechanismHistoryEntryV2, ...]
        ) = ()
        causal_mechanism: PublicCausalMechanism | PublicCausalMechanismV2 | None = None
        causal_alternative: RecordedCausalAlternativePlan | None = None
        projected_causal_plan: RecordedCausalPlanV2 | None = None
        lifecycle_state_transition: RecordedLifecycleStateTransition | None = None
        lifecycle_component_binding: RecordedLifecycleComponentBinding | None = None
        causal_plan_request_projection: ActivatedCausalPlanRequest | None = None
        activated_exploration_request: (
            ActivatedExplorationPlanRequest
            | PinnedExplorationPlanRequest
            | SelfDirectedPlanRequest
            | TriggerBoundSelfDirectedPlanRequest
            | LifecycleBoundPlanRequest
            | LifecycleComponentBoundPlanRequest
            | None
        ) = None
        exploration_closure_receipt: (
            PublicExplorationClosureReceipt | SelfDirectedExplorationClosureReceipt | None
        ) = None
        admission_policy = WORK_PLAN_ADMISSION_POLICY
        try:
            catalog_raw = execution_context.get("eligible_plan_evidence_catalog")
            catalog_model = (
                EligiblePlanEvidenceCatalogV4
                if isinstance(catalog_raw, dict)
                and catalog_raw.get("schema_version") == "eligible-plan-evidence-catalog-v4"
                else EligiblePlanEvidenceCatalogV3
                if isinstance(catalog_raw, dict)
                and catalog_raw.get("schema_version") == "eligible-plan-evidence-catalog-v3"
                else EligiblePlanEvidenceCatalogV2
                if isinstance(catalog_raw, dict)
                and catalog_raw.get("schema_version") == "eligible-plan-evidence-catalog-v2"
                else EligiblePlanEvidenceCatalog
            )
            catalog = catalog_model.model_validate_json(canonical_json(catalog_raw))
            decision_raw = execution_context.get("workflow_decision")
            decision_model = (
                WorkflowDecisionV4
                if isinstance(decision_raw, dict)
                and decision_raw.get("schema_version") == "lean-workflow-decision-v4"
                else WorkflowDecisionV3
                if isinstance(decision_raw, dict)
                and decision_raw.get("schema_version") == "lean-workflow-decision-v3"
                else WorkflowDecisionV2
            )
            decision = decision_model.model_validate_json(canonical_json(decision_raw))
            if isinstance(decision, WorkflowDecisionV3):
                phase_evidence = _evidence_state_from_json(execution_context.get("phase_evidence"))
                semantic_raw = execution_context.get("semantic_progress_state")
                semantic_progress_state = (
                    PublicSemanticProgressState.model_validate_json(canonical_json(semantic_raw))
                    if semantic_raw is not None
                    else None
                )
                if self.tool_schema_version in {"v24", "v25", "v26", "v27", "v28", "v29"}:
                    semantic_progress_event_domain = (
                        SemanticProgressEventDomain.model_validate_json(
                            canonical_json(execution_context.get("semantic_progress_event_domain"))
                        )
                    )
                elif execution_context.get("semantic_progress_event_domain") is not None:
                    raise ValueError("legacy work-plan context includes a semantic event domain")
                if self.tool_schema_version in {
                    "v22",
                    "v23",
                    "v24",
                    "v25",
                    "v26",
                    "v27",
                    "v28",
                    "v29",
                }:
                    if self.tool_schema_version in {"v26", "v27", "v28", "v29"}:
                        request_model = (
                            LifecycleComponentBoundPlanRequest
                            if self.context_policy_version == "phase-evidence-v38"
                            else LifecycleBoundPlanRequest
                            if self.context_policy_version
                            in {"phase-evidence-v36", "phase-evidence-v37"}
                            else TriggerBoundSelfDirectedPlanRequest
                            if self.context_policy_version == "phase-evidence-v35"
                            else SelfDirectedPlanRequest
                        )
                        activated_exploration_request = request_model.model_validate_json(
                            canonical_json(
                                execution_context.get("activated_exploration_plan_request")
                            )
                        )
                        causal_plan_request_projection = (
                            activated_exploration_request.source_request.source_request.base_request
                            if isinstance(
                                activated_exploration_request,
                                (
                                    LifecycleBoundPlanRequest,
                                    LifecycleComponentBoundPlanRequest,
                                ),
                            )
                            else activated_exploration_request.source_request.base_request
                        )
                        admission_policy = SELF_DIRECTED_EXPLORATION_POLICY
                    elif self.tool_schema_version == "v25":
                        activated_exploration_request = (
                            PinnedExplorationPlanRequest.model_validate_json(
                                canonical_json(
                                    execution_context.get("activated_exploration_plan_request")
                                )
                            )
                        )
                        causal_plan_request_projection = (
                            activated_exploration_request.source_request.base_request
                        )
                    elif self.tool_schema_version in {"v23", "v24"}:
                        activated_exploration_request = (
                            ActivatedExplorationPlanRequest.model_validate_json(
                                canonical_json(
                                    execution_context.get("activated_exploration_plan_request")
                                )
                            )
                        )
                        causal_plan_request_projection = (
                            activated_exploration_request.source_request.base_request
                        )
                    else:
                        causal_plan_request_projection = (
                            ActivatedCausalPlanRequest.model_validate_json(
                                canonical_json(
                                    execution_context.get("causal_plan_request_projection")
                                )
                            )
                        )
                    causal_history = tuple(
                        CausalMechanismHistoryEntryV2.model_validate_json(canonical_json(item))
                        for item in execution_context.get("causal_mechanism_history", [])
                    )
                trigger_raw = execution_context.get("cross_reset_failure_trigger")
                if trigger_raw is not None:
                    cross_reset_trigger = CrossResetFailureTrigger.model_validate_json(
                        canonical_json(trigger_raw)
                    )
                    cross_reset_baseline = MutationBaselineProjection.model_validate_json(
                        canonical_json(execution_context.get("mutation_baseline_projection"))
                    )
                    cross_reset_receipt = MutationBaselineRestoreReceipt.model_validate_json(
                        canonical_json(execution_context.get("mutation_baseline_restore_receipt"))
                    )
                    if self.tool_schema_version not in {
                        "v22",
                        "v23",
                        "v24",
                        "v25",
                        "v26",
                        "v27",
                        "v28",
                        "v29",
                    }:
                        causal_history = tuple(
                            CausalMechanismHistoryEntry.model_validate_json(canonical_json(item))
                            for item in execution_context.get("causal_mechanism_history", [])
                        )
                    admission_policy = CAUSAL_ALTERNATIVE_POLICY
            elif (
                execution_context.get("phase_evidence") is not None
                or execution_context.get("semantic_progress_state") is not None
                or execution_context.get("cross_reset_failure_trigger") is not None
            ):
                raise ValueError("legacy work-plan context includes semantic progress state")
        except ValueError as exc:
            raise RecoveryError("work-plan request context is invalid") from exc
        if (
            not isinstance(request_artifact_id, str)
            or not isinstance(request_body_hash, str)
            or catalog.run_id != self.run_id
            or decision.current_diff_hash != catalog.worktree_diff_hash
            or decision.plan_gate_id is None
            or (
                (revision and "revise_work_plan" not in decision.allowed_tool_names)
                or (not revision and "record_work_plan" not in decision.allowed_tool_names)
            )
        ):
            raise RecoveryError("work-plan request binding differs")
        current_diff_hash = WorkspaceManager.diff_summary(self.workspace).patch_hash
        if current_diff_hash != catalog.worktree_diff_hash:
            raise RecoveryError("work-plan request catalog is stale")
        events = tuple(self.state.list_events(self.run_id))
        semantic_events = events
        if self.tool_schema_version in {"v24", "v25", "v26", "v27", "v28", "v29"}:
            if semantic_progress_event_domain is None:
                raise RecoveryError("V24 work-plan request lacks its semantic event domain")
            semantic_events = select_semantic_progress_epoch_events(
                domain=semantic_progress_event_domain,
                events=events,
            )
        if self.tool_schema_version in {
            "v22",
            "v23",
            "v24",
            "v25",
            "v26",
            "v27",
            "v28",
            "v29",
        } and causal_history != (
            project_causal_mechanism_history_v2(run_id=self.run_id, events=events)
        ):
            raise RecoveryError("projected causal history request state differs")
        if isinstance(decision, WorkflowDecisionV3):
            assert phase_evidence is not None
            if phase_evidence.worktree_diff_hash != current_diff_hash:
                raise RecoveryError("semantic progress phase evidence is stale")
            if cross_reset_trigger is not None:
                exact_trigger = project_active_cross_reset_trigger(
                    run_id=self.run_id,
                    current_diff_hash=current_diff_hash,
                    events=events,
                )
                exact_semantic_progress_state = project_cross_reset_semantic_progress_state(
                    run_id=self.run_id,
                    trigger=cross_reset_trigger,
                    events=events,
                )
                exact_history = (
                    project_causal_mechanism_history_v2(
                        run_id=self.run_id,
                        events=events,
                    )
                    if self.tool_schema_version
                    in {"v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29"}
                    else project_causal_mechanism_history(
                        run_id=self.run_id,
                        events=events,
                    )
                )
                completed_restore = next(
                    event
                    for event in events
                    if event.sequence == cross_reset_trigger.restored_event_sequence
                )
                try:
                    exact_baseline = MutationBaselineProjection.model_validate_json(
                        canonical_json(completed_restore.payload.get("baseline_projection"))
                    )
                    exact_receipt = MutationBaselineRestoreReceipt.model_validate_json(
                        canonical_json(completed_restore.payload.get("restore_receipt"))
                    )
                except ValueError as exc:
                    raise RecoveryError("cross-reset restore evidence is invalid") from exc
                if (
                    cross_reset_trigger != exact_trigger
                    or cross_reset_baseline != exact_baseline
                    or cross_reset_receipt != exact_receipt
                    or causal_history != exact_history
                    or not causal_history
                ):
                    raise RecoveryError("cross-reset request state differs")
            else:
                current_failure_sequence = current_public_failure_event_sequence(
                    run_id=self.run_id,
                    task=self.task,
                    evidence=phase_evidence,
                    events=semantic_events,
                )
                exact_semantic_progress_state = project_public_semantic_progress_state(
                    run_id=self.run_id,
                    task=self.task,
                    evidence=phase_evidence,
                    events=semantic_events,
                    current_failure_event_sequence=current_failure_sequence,
                )
            if (
                semantic_progress_state != exact_semantic_progress_state
                or decision.semantic_progress_state_hash
                != (
                    exact_semantic_progress_state.content_hash
                    if exact_semantic_progress_state is not None
                    else None
                )
                or decision.semantic_reset_required
                is not bool(
                    exact_semantic_progress_state
                    and exact_semantic_progress_state.semantic_reset_required
                )
            ):
                raise RecoveryError("semantic progress request state differs")
        active = project_active_work_state(
            run_id=self.run_id,
            task=self.task,
            current_diff_hash=current_diff_hash,
            events=events,
        )
        context_active_raw = execution_context.get("active_work_state")
        try:
            context_active = (
                ActiveWorkState.model_validate_json(canonical_json(context_active_raw))
                if context_active_raw is not None
                else None
            )
        except ValueError as exc:
            raise RecoveryError("work-plan active request state is invalid") from exc
        if context_active != active:
            raise RecoveryError("work-plan active request state differs")
        if revision:
            if decision.revision_trigger is None:
                raise RecoveryError("work-plan revision lacks an active parent")
            if cross_reset_trigger is not None:
                if (
                    not causal_history
                    or decision.revision_trigger != "check_failure"
                    or decision.required_trigger_evidence_id
                    != f"pev:{cross_reset_trigger.failure_event_sequences[-1]}"
                    or decision.plan_gate_id
                    != causal_reset_gate_id(cross_reset_trigger, causal_history[-1].plan_hash)
                ):
                    raise RecoveryError("cross-reset revision trigger differs")
                trigger = "check_failure"
                trigger_event_sequence = cross_reset_trigger.failure_event_sequences[-1]
                trigger_check_id = cross_reset_trigger.check_id
                revision_index = causal_history[-1].revision_index + 1
                parent_plan_hash = causal_history[-1].plan_hash
            else:
                if active is None:
                    raise RecoveryError("work-plan revision lacks an active parent")
                trigger = decision.revision_trigger
                trigger_id = decision.required_trigger_evidence_id
                trigger_evidence = next(
                    (item for item in catalog.items if item.evidence_id == trigger_id),
                    None,
                )
                if trigger_evidence is None:
                    raise RecoveryError("work-plan revision trigger is not request-visible")
                trigger_event_sequence = trigger_evidence.canonical_event_sequence
                trigger_check_id = (
                    trigger_evidence.check.check_id
                    if trigger == "check_failure" and trigger_evidence.check is not None
                    else None
                )
                revision_index = active.latest_plan.revision_index + 1
                parent_plan_hash = active.latest_plan.content_hash
        else:
            if cross_reset_trigger is not None:
                raise RecoveryError("cross-reset plan must be a revision")
            if active is not None:
                raise RecoveryError("initial work-plan request already has an active plan")
            trigger = "initial"
            trigger_event_sequence = None
            trigger_check_id = None
            revision_index = 0
            parent_plan_hash = None
        try:
            if self.tool_schema_version == "v29":
                if not isinstance(
                    activated_exploration_request,
                    LifecycleComponentBoundPlanRequest,
                ) or not isinstance(catalog, EligiblePlanEvidenceCatalogV4):
                    raise RecoveryError("V29 work plan lacks its component projection")
                (
                    projected_causal_plan,
                    exploration_closure_receipt,
                    lifecycle_component_binding,
                ) = normalize_lifecycle_component_bound_plan(
                    task=self.task,
                    catalog=catalog,
                    request_projection=activated_exploration_request,
                    trigger=trigger,
                    revision_index=revision_index,
                    parent_plan_hash=parent_plan_hash,
                    trigger_check_id=trigger_check_id,
                    trigger_event_sequence=trigger_event_sequence,
                    cross_reset_trigger=cross_reset_trigger,
                    history=causal_history,
                    raw_arguments=arguments,
                )
                plan = standard_plan_from_projected_causal_plan(
                    task=self.task,
                    catalog=catalog,
                    projected=projected_causal_plan,
                )
                lifecycle_body = {
                    **lifecycle_component_binding.model_dump(
                        mode="python", exclude={"content_hash", "plan_hash"}
                    ),
                    "plan_hash": plan.content_hash,
                }
                lifecycle_component_binding = RecordedLifecycleComponentBinding.model_validate_json(
                    canonical_json(
                        {
                            **lifecycle_body,
                            "content_hash": sha256_json(lifecycle_body),
                        }
                    )
                )
                causal_mechanism = projected_causal_plan.causal_mechanism
            elif self.tool_schema_version in {"v27", "v28"}:
                if not isinstance(
                    activated_exploration_request, LifecycleBoundPlanRequest
                ) or not isinstance(catalog, EligiblePlanEvidenceCatalogV4):
                    raise RecoveryError("V27 work plan lacks its lifecycle projection")
                (
                    projected_causal_plan,
                    exploration_closure_receipt,
                    lifecycle_state_transition,
                ) = normalize_lifecycle_bound_plan(
                    task=self.task,
                    catalog=catalog,
                    request_projection=activated_exploration_request,
                    trigger=trigger,
                    revision_index=revision_index,
                    parent_plan_hash=parent_plan_hash,
                    trigger_check_id=trigger_check_id,
                    trigger_event_sequence=trigger_event_sequence,
                    cross_reset_trigger=cross_reset_trigger,
                    history=causal_history,
                    raw_arguments=arguments,
                )
                plan = standard_plan_from_projected_causal_plan(
                    task=self.task,
                    catalog=catalog,
                    projected=projected_causal_plan,
                )
                lifecycle_body = {
                    **lifecycle_state_transition.model_dump(
                        mode="python", exclude={"content_hash", "plan_hash"}
                    ),
                    "plan_hash": plan.content_hash,
                }
                lifecycle_state_transition = RecordedLifecycleStateTransition.model_validate_json(
                    canonical_json(
                        {
                            **lifecycle_body,
                            "content_hash": sha256_text(canonical_json(lifecycle_body)),
                        }
                    )
                )
                causal_mechanism = projected_causal_plan.causal_mechanism
            elif self.tool_schema_version == "v26":
                if not isinstance(
                    activated_exploration_request, SelfDirectedPlanRequest
                ) or not isinstance(catalog, EligiblePlanEvidenceCatalogV4):
                    raise RecoveryError("V26 work plan lacks its self-directed projection")
                plan_normalizer = (
                    normalize_trigger_bound_self_directed_plan
                    if self.context_policy_version == "phase-evidence-v35"
                    else normalize_self_directed_plan
                )
                projected_causal_plan, exploration_closure_receipt = plan_normalizer(
                    task=self.task,
                    catalog=catalog,
                    request_projection=activated_exploration_request,
                    trigger=trigger,
                    revision_index=revision_index,
                    parent_plan_hash=parent_plan_hash,
                    trigger_check_id=trigger_check_id,
                    trigger_event_sequence=trigger_event_sequence,
                    cross_reset_trigger=cross_reset_trigger,
                    history=causal_history,
                    raw_arguments=arguments,
                )
                plan = standard_plan_from_projected_causal_plan(
                    task=self.task,
                    catalog=catalog,
                    projected=projected_causal_plan,
                )
                causal_mechanism = projected_causal_plan.causal_mechanism
            elif self.tool_schema_version == "v25":
                if not isinstance(
                    activated_exploration_request, PinnedExplorationPlanRequest
                ) or not isinstance(catalog, EligiblePlanEvidenceCatalogV3):
                    raise RecoveryError("V25 work plan lacks its exact pinned projection")
                projected_causal_plan, exploration_closure_receipt = (
                    normalize_pinned_exploration_plan(
                        task=self.task,
                        catalog=catalog,
                        request_projection=activated_exploration_request,
                        trigger=trigger,
                        revision_index=revision_index,
                        parent_plan_hash=parent_plan_hash,
                        trigger_check_id=trigger_check_id,
                        trigger_event_sequence=trigger_event_sequence,
                        cross_reset_trigger=cross_reset_trigger,
                        history=causal_history,
                        raw_arguments=arguments,
                    )
                )
                plan = standard_plan_from_projected_causal_plan(
                    task=self.task,
                    catalog=catalog,
                    projected=projected_causal_plan,
                )
                causal_mechanism = projected_causal_plan.causal_mechanism
            elif self.tool_schema_version in {"v23", "v24"}:
                if activated_exploration_request is None:
                    raise RecoveryError("V23 work plan lacks its exact exploration projection")
                projected_causal_plan, exploration_closure_receipt = (
                    normalize_activated_exploration_plan(
                        task=self.task,
                        catalog=catalog,
                        request_projection=activated_exploration_request,
                        trigger=trigger,
                        revision_index=revision_index,
                        parent_plan_hash=parent_plan_hash,
                        trigger_check_id=trigger_check_id,
                        trigger_event_sequence=trigger_event_sequence,
                        cross_reset_trigger=cross_reset_trigger,
                        history=causal_history,
                        raw_arguments=arguments,
                    )
                )
                plan = standard_plan_from_projected_causal_plan(
                    task=self.task,
                    catalog=catalog,
                    projected=projected_causal_plan,
                )
                causal_mechanism = projected_causal_plan.causal_mechanism
            elif self.tool_schema_version == "v22":
                if causal_plan_request_projection is None:
                    raise RecoveryError("V22 work plan lacks its exact causal projection")
                projected_causal_plan = normalize_activated_causal_plan(
                    task=self.task,
                    catalog=catalog,
                    request_projection=causal_plan_request_projection,
                    trigger=trigger,
                    revision_index=revision_index,
                    parent_plan_hash=parent_plan_hash,
                    trigger_check_id=trigger_check_id,
                    trigger_event_sequence=trigger_event_sequence,
                    cross_reset_trigger=cross_reset_trigger,
                    history=causal_history,
                    raw_arguments=arguments,
                )
                plan = standard_plan_from_projected_causal_plan(
                    task=self.task,
                    catalog=catalog,
                    projected=projected_causal_plan,
                )
                causal_mechanism = projected_causal_plan.causal_mechanism
            elif cross_reset_trigger is not None:
                assert cross_reset_baseline is not None
                assert cross_reset_receipt is not None
                causal_alternative, candidate_binding_normalization = (
                    validate_causal_alternative_plan(
                        task=self.task,
                        catalog=catalog,
                        semantic_progress_state=semantic_progress_state,
                        baseline=cross_reset_baseline,
                        restore_receipt=cross_reset_receipt,
                        history=causal_history,
                        parent_plan_hash=parent_plan_hash,
                        arguments=arguments,
                    )
                )
                plan = standard_plan_from_causal_alternative(
                    task=self.task,
                    catalog=catalog,
                    alternative=causal_alternative,
                )
                causal_mechanism = causal_alternative.alternative_causal_mechanism
            elif self.tool_schema_version in {"v20", "v21"}:
                normalized_arguments = dict(arguments)
                raw_causal_mechanism = normalized_arguments.pop("causal_mechanism", None)
                plan, candidate_binding_normalization = validate_work_plan_v16(
                    task=self.task,
                    catalog=catalog,
                    arguments=normalized_arguments,
                    trigger=trigger,
                    revision_index=revision_index,
                    parent_plan_hash=parent_plan_hash,
                    trigger_check_id=trigger_check_id,
                    trigger_event_sequence=trigger_event_sequence,
                )
                if self.tool_schema_version == "v21":
                    causal_mechanism = validate_public_causal_mechanism(
                        task=self.task,
                        catalog=catalog,
                        foundation_evidence_ids=[
                            item.evidence_id for item in plan.foundation_evidence
                        ],
                        raw_mechanism=raw_causal_mechanism,
                    )
            else:
                plan = validate_work_plan_v2(
                    task=self.task,
                    catalog=catalog,
                    arguments=arguments,
                    trigger=trigger,
                    revision_index=revision_index,
                    parent_plan_hash=parent_plan_hash,
                    trigger_check_id=trigger_check_id,
                    trigger_event_sequence=trigger_event_sequence,
                )
            validate_semantic_progress_revision(
                semantic_progress_state=(
                    semantic_progress_state if isinstance(decision, WorkflowDecisionV3) else None
                ),
                prior_hypothesis_disposition=(
                    plan.prior_hypothesis_disposition if revision else None
                ),
                trigger_event_sequence=(plan.trigger_event_sequence if revision else None),
            )
        except ContractError as exc:
            prior_attempts = sum(
                event.type == EventType.TOOL_ADMISSION_BLOCKED
                and event.payload.get("policy_version") == admission_policy
                and event.payload.get("plan_gate_id") == decision.plan_gate_id
                for event in events
            )
            reason_codes = exc.details.get("reason_codes")
            if not isinstance(reason_codes, list) or not reason_codes:
                reason_codes = ["work_plan_contract_invalid"]
            raise WorkPlanAdmissionRejectedError(
                str(exc),
                details={
                    "schema_version": "work-plan-admission-feedback-v1",
                    "policy_version": admission_policy,
                    "plan_gate_id": decision.plan_gate_id,
                    "attempt": prior_attempts + 1,
                    "reason_codes": reason_codes,
                    "eligible_catalog_hash": catalog.content_hash,
                    "eligible_plan_evidence_catalog": catalog.model_dump(mode="json"),
                    **(
                        {"lifecycle_relation_mismatch": exc.details["lifecycle_relation_mismatch"]}
                        if self.tool_schema_version == "v29"
                        and isinstance(exc.details.get("lifecycle_relation_mismatch"), dict)
                        else {}
                    ),
                    **(
                        {
                            "activated_exploration_plan_request": (
                                activated_exploration_request.model_dump(mode="json")
                            ),
                            "activated_exploration_plan_request_hash": (
                                activated_exploration_request.content_hash
                            ),
                        }
                        if activated_exploration_request is not None
                        else {}
                    ),
                    **(
                        {
                            "causal_plan_request_projection": (
                                causal_plan_request_projection.model_dump(mode="json")
                            ),
                            "causal_plan_request_projection_hash": (
                                causal_plan_request_projection.content_hash
                            ),
                        }
                        if causal_plan_request_projection is not None
                        else {}
                    ),
                    **(
                        {
                            "cross_reset_failure_trigger": (
                                cross_reset_trigger.model_dump(mode="json")
                            ),
                            "causal_mechanism_history": [
                                item.model_dump(mode="json") for item in causal_history
                            ],
                        }
                        if cross_reset_trigger is not None
                        else {}
                    ),
                    **(
                        {
                            "semantic_progress_state": (
                                semantic_progress_state.model_dump(mode="json")
                                if semantic_progress_state is not None
                                else None
                            ),
                            "required_prior_hypothesis_disposition": (
                                decision.required_prior_hypothesis_disposition
                            ),
                        }
                        if isinstance(decision, WorkflowDecisionV3)
                        else {}
                    ),
                    "worktree_diff_hash": current_diff_hash,
                    "request_artifact_id": request_artifact_id,
                    "request_body_hash": request_body_hash,
                    "execution": "not_dispatched",
                    "guidance": (
                        "Retry once using only the exact cspan and support IDs in "
                        "causal_plan_request_projection. Do not supply paths, ranges, roles, "
                        "evidence bindings, observation status, or check order."
                        if causal_plan_request_projection is not None
                        else "Retry once using only the exact IDs and candidate/read pairs "
                        "enumerated in eligible_plan_evidence_catalog."
                    ),
                },
            ) from exc
        prior = [
            event
            for event in events
            if event.type == EventType.PLAN_RECORDED
            and event.payload.get("schema_version") == PLAN_RECORDED_EVENT_SCHEMA_V2
            and event.payload.get("plan_hash") == plan.content_hash
        ]
        if len(prior) > 1:
            raise RecoveryError("work-plan idempotency event repeats")
        if prior:
            plan_event = prior[0]
            expected_semantic_hash = (
                semantic_progress_state.content_hash
                if isinstance(decision, WorkflowDecisionV3) and semantic_progress_state is not None
                else None
            )
            if plan_event.payload.get("semantic_progress_state_hash") != expected_semantic_hash:
                raise RecoveryError("work-plan idempotency semantic state differs")
            expected_domain_hash = (
                semantic_progress_event_domain.content_hash
                if self.tool_schema_version in {"v24", "v25", "v26", "v27", "v28", "v29"}
                and semantic_progress_event_domain is not None
                else None
            )
            if plan_event.payload.get("semantic_progress_event_domain_hash") != (
                expected_domain_hash
            ):
                raise RecoveryError("work-plan idempotency semantic event domain differs")
            expected_binding_hash = (
                candidate_binding_normalization.content_hash
                if candidate_binding_normalization is not None
                else None
            )
            if (
                plan_event.payload.get("candidate_binding_normalization_hash")
                != expected_binding_hash
            ):
                raise RecoveryError("work-plan idempotency candidate binding differs")
            if self.tool_schema_version in {
                "v22",
                "v23",
                "v24",
                "v25",
                "v26",
                "v27",
                "v28",
                "v29",
            } and (
                projected_causal_plan is None
                or causal_plan_request_projection is None
                or plan_event.payload.get("projected_causal_plan_hash")
                != projected_causal_plan.content_hash
                or plan_event.payload.get("causal_plan_request_projection_hash")
                != causal_plan_request_projection.content_hash
            ):
                raise RecoveryError("projected work-plan idempotency projection differs")
            if self.tool_schema_version in {"v23", "v24", "v25"} and (
                activated_exploration_request is None
                or exploration_closure_receipt is None
                or plan_event.payload.get("activated_exploration_request_hash")
                != activated_exploration_request.content_hash
                or plan_event.payload.get("exploration_closure_receipt_hash")
                != exploration_closure_receipt.content_hash
            ):
                raise RecoveryError("V23 work-plan idempotency exploration closure differs")
            if self.tool_schema_version == "v26" and (
                not isinstance(activated_exploration_request, SelfDirectedPlanRequest)
                or not isinstance(
                    exploration_closure_receipt,
                    SelfDirectedExplorationClosureReceipt,
                )
                or plan_event.payload.get("activated_exploration_request_hash")
                != activated_exploration_request.content_hash
                or plan_event.payload.get("self_directed_closure_receipt_hash")
                != exploration_closure_receipt.content_hash
            ):
                raise RecoveryError("V26 work-plan idempotency exploration closure differs")
            if self.tool_schema_version in {"v27", "v28"} and (
                not isinstance(activated_exploration_request, LifecycleBoundPlanRequest)
                or not isinstance(
                    exploration_closure_receipt,
                    SelfDirectedExplorationClosureReceipt,
                )
                or lifecycle_state_transition is None
                or plan_event.payload.get("activated_exploration_request_hash")
                != activated_exploration_request.content_hash
                or plan_event.payload.get("self_directed_closure_receipt_hash")
                != exploration_closure_receipt.content_hash
                or plan_event.payload.get("lifecycle_state_transition_hash")
                != lifecycle_state_transition.content_hash
            ):
                raise RecoveryError("V27 work-plan idempotency lifecycle closure differs")
            if self.tool_schema_version == "v29" and (
                not isinstance(
                    activated_exploration_request,
                    LifecycleComponentBoundPlanRequest,
                )
                or not isinstance(
                    exploration_closure_receipt,
                    SelfDirectedExplorationClosureReceipt,
                )
                or lifecycle_component_binding is None
                or plan_event.payload.get("activated_exploration_request_hash")
                != activated_exploration_request.content_hash
                or plan_event.payload.get("self_directed_closure_receipt_hash")
                != exploration_closure_receipt.content_hash
                or plan_event.payload.get("lifecycle_component_binding_hash")
                != lifecycle_component_binding.content_hash
            ):
                raise RecoveryError("V29 work-plan idempotency component closure differs")
        else:
            plan_event = self.state.append_event(
                self.run_id,
                EventType.PLAN_RECORDED,
                actor="workflow-state-machine",
                payload={
                    "schema_version": PLAN_RECORDED_EVENT_SCHEMA_V2,
                    "task_id": plan.task_id,
                    "task_version": plan.task_version,
                    "public_task_hash": plan.public_task_hash,
                    "worktree_diff_hash": plan.worktree_diff_hash,
                    "plan_hash": plan.content_hash,
                    "observation_status": plan.observation_status,
                    "evidence_catalog_hash": plan.evidence_catalog_hash,
                    "candidate_files": [item.path for item in plan.candidate_files],
                    "planned_check_ids": list(plan.planned_check_ids),
                    "revision_index": plan.revision_index,
                    "parent_plan_hash": plan.parent_plan_hash,
                    "trigger": plan.trigger,
                    "trigger_check_id": plan.trigger_check_id,
                    "trigger_event_sequence": plan.trigger_event_sequence,
                    "plan_gate_id": decision.plan_gate_id,
                    "request_artifact_id": request_artifact_id,
                    "request_body_hash": request_body_hash,
                    "plan": plan.model_dump(mode="json"),
                    "public_evidence_only": True,
                    "private_evidence_used": False,
                    "reasoning_text_used": False,
                    **(
                        {
                            "causal_plan_projection_activation_policy_version": (
                                CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY
                            ),
                            "projected_causal_plan_hash": projected_causal_plan.content_hash,
                            "projected_causal_plan": projected_causal_plan.model_dump(mode="json"),
                            "causal_plan_request_projection_hash": (
                                causal_plan_request_projection.content_hash
                            ),
                            "causal_plan_request_projection": (
                                causal_plan_request_projection.model_dump(mode="json")
                            ),
                        }
                        if projected_causal_plan is not None
                        and causal_plan_request_projection is not None
                        else {}
                    ),
                    **(
                        {
                            "exploration_gate_activation_policy_version": (
                                activated_exploration_request.policy_version
                            ),
                            "activated_exploration_request_hash": (
                                activated_exploration_request.content_hash
                            ),
                            "activated_exploration_request": (
                                activated_exploration_request.model_dump(mode="json")
                            ),
                            "exploration_closure_receipt_hash": (
                                exploration_closure_receipt.content_hash
                            ),
                            "exploration_closure_receipt": (
                                exploration_closure_receipt.model_dump(mode="json")
                            ),
                        }
                        if activated_exploration_request is not None
                        and exploration_closure_receipt is not None
                        and self.tool_schema_version not in {"v26", "v27", "v28", "v29"}
                        else {}
                    ),
                    **(
                        {
                            "self_directed_exploration_policy_version": (
                                SELF_DIRECTED_EXPLORATION_POLICY
                            ),
                            "activated_exploration_request_hash": (
                                activated_exploration_request.content_hash
                            ),
                            "activated_exploration_request": (
                                activated_exploration_request.model_dump(mode="json")
                            ),
                            "self_directed_closure_receipt_hash": (
                                exploration_closure_receipt.content_hash
                            ),
                            "self_directed_closure_receipt": (
                                exploration_closure_receipt.model_dump(mode="json")
                            ),
                        }
                        if isinstance(
                            activated_exploration_request,
                            (
                                SelfDirectedPlanRequest,
                                LifecycleBoundPlanRequest,
                                LifecycleComponentBoundPlanRequest,
                            ),
                        )
                        and isinstance(
                            exploration_closure_receipt,
                            SelfDirectedExplorationClosureReceipt,
                        )
                        else {}
                    ),
                    **(
                        {
                            "lifecycle_plan_policy_version": LIFECYCLE_PLAN_POLICY,
                            "lifecycle_state_transition_hash": (
                                lifecycle_state_transition.content_hash
                            ),
                            "lifecycle_state_transition": (
                                lifecycle_state_transition.model_dump(mode="json")
                            ),
                        }
                        if lifecycle_state_transition is not None
                        else {}
                    ),
                    **(
                        {
                            "lifecycle_plan_policy_version": (LIFECYCLE_COMPONENT_BINDING_POLICY),
                            "lifecycle_component_binding_hash": (
                                lifecycle_component_binding.content_hash
                            ),
                            "lifecycle_component_binding": (
                                lifecycle_component_binding.model_dump(mode="json")
                            ),
                        }
                        if lifecycle_component_binding is not None
                        else {}
                    ),
                    **(
                        {
                            "candidate_binding_policy_version": (CANDIDATE_BINDING_POLICY_V16),
                            "candidate_binding_normalization_hash": (
                                candidate_binding_normalization.content_hash
                            ),
                            "candidate_binding_normalization": (
                                candidate_binding_normalization.model_dump(mode="json")
                            ),
                        }
                        if candidate_binding_normalization is not None
                        else {}
                    ),
                    **(
                        {
                            "semantic_progress_state_hash": (
                                semantic_progress_state.content_hash
                                if semantic_progress_state is not None
                                else None
                            ),
                            "semantic_reset_required": bool(
                                semantic_progress_state
                                and semantic_progress_state.semantic_reset_required
                            ),
                            "failure_signature_hash": (
                                semantic_progress_state.failure_signature_hash
                                if semantic_progress_state is not None
                                else None
                            ),
                            "same_signature_failed_diff_count": (
                                semantic_progress_state.same_signature_failed_diff_count
                                if semantic_progress_state is not None
                                else 0
                            ),
                        }
                        if isinstance(decision, WorkflowDecisionV3)
                        else {}
                    ),
                    **(
                        {
                            "semantic_progress_event_domain_hash": (
                                semantic_progress_event_domain.content_hash
                            ),
                            "semantic_progress_event_domain": (
                                semantic_progress_event_domain.model_dump(mode="json")
                            ),
                        }
                        if self.tool_schema_version in {"v24", "v25", "v26", "v27", "v28", "v29"}
                        and semantic_progress_event_domain is not None
                        else {}
                    ),
                },
            )
        causal_binding = None
        causal_binding_event = None
        if self.tool_schema_version in {"v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29"}:
            if (
                projected_causal_plan is None
                or causal_plan_request_projection is None
                or not isinstance(causal_mechanism, PublicCausalMechanismV2)
            ):
                raise RecoveryError("projected work plan lost its causal binding")
            causal_binding = build_causal_work_plan_binding_v2(
                plan=plan,
                plan_event_sequence=plan_event.sequence,
                projected=projected_causal_plan,
                request_projection=causal_plan_request_projection,
                cross_reset_trigger_hash=(
                    cross_reset_trigger.content_hash if cross_reset_trigger is not None else None
                ),
            )
            matching_bindings = [
                event
                for event in self.state.list_events(self.run_id)
                if event.type == EventType.CAUSAL_MECHANISM_RECORDED
                and event.payload.get("binding_hash") == causal_binding.content_hash
            ]
            if len(matching_bindings) > 1:
                raise RecoveryError("causal work-plan v2 binding repeats")
            if matching_bindings:
                causal_binding_event = matching_bindings[0]
                try:
                    recorded_binding = CausalWorkPlanBindingV2.model_validate_json(
                        canonical_json(causal_binding_event.payload.get("binding"))
                    )
                except ValueError as exc:
                    raise RecoveryError("causal work-plan v2 binding is invalid") from exc
                if recorded_binding != causal_binding:
                    raise RecoveryError("causal work-plan v2 binding differs")
            else:
                causal_binding_event = self.state.append_event(
                    self.run_id,
                    EventType.CAUSAL_MECHANISM_RECORDED,
                    actor="workflow-state-machine",
                    payload={
                        "schema_version": "causal-mechanism-recorded-v2",
                        "policy_version": CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY,
                        "plan_hash": plan.content_hash,
                        "plan_event_sequence": plan_event.sequence,
                        "binding_hash": causal_binding.content_hash,
                        "binding": causal_binding.model_dump(mode="json"),
                        "public_evidence_only": True,
                        "private_evidence_used": False,
                        "reasoning_text_used": False,
                    },
                )
        elif self.tool_schema_version == "v21":
            if causal_mechanism is None:
                raise RecoveryError("V21 work plan lost its causal mechanism")
            causal_binding = build_causal_work_plan_binding(
                plan=plan,
                plan_event_sequence=plan_event.sequence,
                mechanism=causal_mechanism,
                alternative_plan=causal_alternative,
                cross_reset_trigger_hash=(
                    cross_reset_trigger.content_hash if cross_reset_trigger is not None else None
                ),
            )
            matching_bindings = [
                event
                for event in self.state.list_events(self.run_id)
                if event.type == EventType.CAUSAL_MECHANISM_RECORDED
                and event.payload.get("binding_hash") == causal_binding.content_hash
            ]
            if len(matching_bindings) > 1:
                raise RecoveryError("causal work-plan binding repeats")
            if matching_bindings:
                causal_binding_event = matching_bindings[0]
                try:
                    recorded_binding = CausalWorkPlanBinding.model_validate_json(
                        canonical_json(causal_binding_event.payload.get("binding"))
                    )
                except ValueError as exc:
                    raise RecoveryError("causal work-plan binding is invalid") from exc
                if recorded_binding != causal_binding:
                    raise RecoveryError("causal work-plan binding differs")
            else:
                causal_binding_event = self.state.append_event(
                    self.run_id,
                    EventType.CAUSAL_MECHANISM_RECORDED,
                    actor="workflow-state-machine",
                    payload={
                        "schema_version": "causal-mechanism-recorded-v1",
                        "policy_version": CAUSAL_ACTIVATION_POLICY,
                        "plan_hash": plan.content_hash,
                        "plan_event_sequence": plan_event.sequence,
                        "binding_hash": causal_binding.content_hash,
                        "binding": causal_binding.model_dump(mode="json"),
                        "public_evidence_only": True,
                        "private_evidence_used": False,
                        "reasoning_text_used": False,
                    },
                )
        exploration_binding = None
        exploration_binding_event = None
        if self.tool_schema_version in {"v23", "v24", "v25"}:
            if (
                projected_causal_plan is None
                or exploration_closure_receipt is None
                or activated_exploration_request is None
            ):
                raise RecoveryError("V23 work plan lost its exploration closure")
            exploration_binding = build_exploration_work_plan_binding(
                plan=plan,
                plan_event_sequence=plan_event.sequence,
                projected=projected_causal_plan,
                receipt=exploration_closure_receipt,
            )
            matching_exploration = [
                event
                for event in self.state.list_events(self.run_id)
                if event.type == EventType.EXPLORATION_CLOSURE_RECORDED
                and event.payload.get("binding_hash") == exploration_binding.content_hash
            ]
            if len(matching_exploration) > 1:
                raise RecoveryError("exploration closure binding repeats")
            if matching_exploration:
                exploration_binding_event = matching_exploration[0]
                recorded = exploration_binding_for_hash(
                    run_id=self.run_id,
                    plan_hash=plan.content_hash,
                    events=self.state.list_events(self.run_id),
                )
                if recorded != exploration_binding:
                    raise RecoveryError("exploration closure binding differs")
            else:
                exploration_binding_event = self.state.append_event(
                    self.run_id,
                    EventType.EXPLORATION_CLOSURE_RECORDED,
                    actor="workflow-state-machine",
                    payload=exploration_closure_event_payload(
                        binding=exploration_binding,
                        request_projection=activated_exploration_request,
                    ),
                )
        if self.tool_schema_version in {"v26", "v27", "v28", "v29"}:
            if (
                projected_causal_plan is None
                or not isinstance(
                    exploration_closure_receipt,
                    SelfDirectedExplorationClosureReceipt,
                )
                or not isinstance(
                    activated_exploration_request,
                    (
                        SelfDirectedPlanRequest,
                        LifecycleBoundPlanRequest,
                        LifecycleComponentBoundPlanRequest,
                    ),
                )
            ):
                raise RecoveryError("self-directed work plan lost its exploration closure")
            exploration_binding = build_self_directed_work_plan_binding(
                plan=plan,
                plan_event_sequence=plan_event.sequence,
                projected=projected_causal_plan,
                receipt=exploration_closure_receipt,
            )
            matching_exploration = [
                event
                for event in self.state.list_events(self.run_id)
                if event.type == EventType.EXPLORATION_CLOSURE_RECORDED
                and event.payload.get("binding_hash") == exploration_binding.content_hash
            ]
            if len(matching_exploration) > 1:
                raise RecoveryError("self-directed exploration closure binding repeats")
            if matching_exploration:
                exploration_binding_event = matching_exploration[0]
                recorded = self_directed_binding_for_hash(
                    run_id=self.run_id,
                    plan_hash=plan.content_hash,
                    events=self.state.list_events(self.run_id),
                )
                if recorded != exploration_binding:
                    raise RecoveryError("self-directed exploration closure binding differs")
            else:
                exploration_binding_event = self.state.append_event(
                    self.run_id,
                    EventType.EXPLORATION_CLOSURE_RECORDED,
                    actor="workflow-state-machine",
                    payload=self_directed_closure_event_payload(
                        binding=exploration_binding,
                        request_projection=(
                            activated_exploration_request.source_request
                            if isinstance(
                                activated_exploration_request,
                                (
                                    LifecycleBoundPlanRequest,
                                    LifecycleComponentBoundPlanRequest,
                                ),
                            )
                            else activated_exploration_request
                        ),
                    ),
                )
        return {
            "plan_hash": plan.content_hash,
            "plan_event_sequence": plan_event.sequence,
            "observation_status": plan.observation_status,
            "candidate_files": [item.path for item in plan.candidate_files],
            "planned_check_ids": list(plan.planned_check_ids),
            "revision_index": plan.revision_index,
            "parent_plan_hash": plan.parent_plan_hash,
            "trigger": plan.trigger,
            "plan_gate_id": decision.plan_gate_id,
            "worktree_diff_hash": current_diff_hash,
            "idempotent": bool(prior),
            **(
                {
                    "candidate_binding_policy_version": CANDIDATE_BINDING_POLICY_V16,
                    "candidate_binding_normalization_hash": (
                        candidate_binding_normalization.content_hash
                    ),
                    "candidate_binding_normalization": (
                        candidate_binding_normalization.model_dump(mode="json")
                    ),
                }
                if candidate_binding_normalization is not None
                else {}
            ),
            **(
                {
                    "semantic_progress_state_hash": (
                        semantic_progress_state.content_hash
                        if semantic_progress_state is not None
                        else None
                    ),
                    "semantic_reset_required": bool(
                        semantic_progress_state and semantic_progress_state.semantic_reset_required
                    ),
                }
                if isinstance(decision, WorkflowDecisionV3)
                else {}
            ),
            **(
                {
                    "semantic_progress_event_domain_hash": (
                        semantic_progress_event_domain.content_hash
                    ),
                }
                if self.tool_schema_version in {"v24", "v25", "v26", "v27", "v28", "v29"}
                and semantic_progress_event_domain is not None
                else {}
            ),
            **(
                {
                    "causal_activation_policy_version": (
                        CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY
                        if self.tool_schema_version
                        in {"v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29"}
                        else CAUSAL_ACTIVATION_POLICY
                    ),
                    "causal_mechanism_hash": causal_mechanism.content_hash,
                    "causal_plan_binding_hash": causal_binding.content_hash,
                    "causal_plan_binding_event_sequence": causal_binding_event.sequence,
                    "cross_reset_failure_trigger_hash": (
                        cross_reset_trigger.content_hash
                        if cross_reset_trigger is not None
                        else None
                    ),
                    **(
                        {
                            "projected_causal_plan_hash": projected_causal_plan.content_hash,
                            "causal_plan_request_projection_hash": (
                                causal_plan_request_projection.content_hash
                            ),
                        }
                        if projected_causal_plan is not None
                        and causal_plan_request_projection is not None
                        else {}
                    ),
                }
                if causal_binding is not None
                and causal_binding_event is not None
                and causal_mechanism is not None
                else {}
            ),
            **(
                {
                    "exploration_gate_activation_policy_version": (
                        activated_exploration_request.policy_version
                    ),
                    "exploration_closure_receipt_hash": (exploration_closure_receipt.content_hash),
                    "exploration_work_plan_binding_hash": exploration_binding.content_hash,
                    "exploration_closure_event_sequence": exploration_binding_event.sequence,
                }
                if activated_exploration_request is not None
                and exploration_closure_receipt is not None
                and exploration_binding is not None
                and exploration_binding_event is not None
                else {}
            ),
            **(
                {
                    "lifecycle_plan_policy_version": LIFECYCLE_PLAN_POLICY,
                    "lifecycle_state_transition_hash": (lifecycle_state_transition.content_hash),
                }
                if lifecycle_state_transition is not None
                else {}
            ),
            **(
                {
                    "lifecycle_plan_policy_version": LIFECYCLE_COMPONENT_BINDING_POLICY,
                    "lifecycle_component_binding_hash": (lifecycle_component_binding.content_hash),
                }
                if lifecycle_component_binding is not None
                else {}
            ),
        }

    def _current_work_plan_v2(
        self,
        worktree_diff_hash: str,
    ) -> RecordedWorkPlanV2 | None:
        events = self.state.list_events(self.run_id)
        active = project_active_work_state(
            run_id=self.run_id,
            task=self.task,
            current_diff_hash=worktree_diff_hash,
            events=events,
        )
        if active is None:
            return None
        if (
            self.tool_schema_version == "v21"
            and causal_plan_binding_for_hash(
                run_id=self.run_id,
                plan_hash=active.latest_plan.content_hash,
                events=events,
            )
            is None
        ):
            raise RecoveryError("V21 current work plan lacks its causal binding")
        if (
            self.tool_schema_version in {"v22", "v23", "v24", "v25", "v26", "v27", "v28", "v29"}
            and causal_plan_binding_for_hash_v2(
                run_id=self.run_id,
                plan_hash=active.latest_plan.content_hash,
                events=events,
            )
            is None
        ):
            raise RecoveryError("projected current work plan lacks its causal binding")
        if (
            self.tool_schema_version in {"v23", "v24", "v25"}
            and exploration_binding_for_hash(
                run_id=self.run_id,
                plan_hash=active.latest_plan.content_hash,
                events=events,
            )
            is None
        ):
            raise RecoveryError("V23 current work plan lacks its exploration closure")
        if (
            self.tool_schema_version in {"v26", "v27", "v28", "v29"}
            and self_directed_binding_for_hash(
                run_id=self.run_id,
                plan_hash=active.latest_plan.content_hash,
                events=events,
            )
            is None
        ):
            raise RecoveryError("current work plan lacks its self-directed closure")
        if self.tool_schema_version in {"v27", "v28"}:
            plan_events = [
                event
                for event in events
                if event.type == EventType.PLAN_RECORDED
                and event.payload.get("plan_hash") == active.latest_plan.content_hash
            ]
            if len(plan_events) != 1:
                raise RecoveryError("V27 current work plan lacks one durable plan event")
            raw_lifecycle = plan_events[0].payload.get("lifecycle_state_transition")
            try:
                lifecycle = RecordedLifecycleStateTransition.model_validate_json(
                    canonical_json(raw_lifecycle)
                )
            except ValueError as exc:
                raise RecoveryError("V27 lifecycle work-plan record is invalid") from exc
            if (
                lifecycle.plan_hash != active.latest_plan.content_hash
                or plan_events[0].payload.get("lifecycle_state_transition_hash")
                != lifecycle.content_hash
            ):
                raise RecoveryError("V27 lifecycle work-plan binding differs")
        if self.tool_schema_version == "v29":
            plan_events = [
                event
                for event in events
                if event.type == EventType.PLAN_RECORDED
                and event.payload.get("plan_hash") == active.latest_plan.content_hash
            ]
            if len(plan_events) != 1:
                raise RecoveryError("V29 current work plan lacks one durable plan event")
            raw_lifecycle = plan_events[0].payload.get("lifecycle_component_binding")
            try:
                lifecycle = RecordedLifecycleComponentBinding.model_validate_json(
                    canonical_json(raw_lifecycle)
                )
            except ValueError as exc:
                raise RecoveryError("V29 lifecycle work-plan record is invalid") from exc
            if (
                lifecycle.plan_hash != active.latest_plan.content_hash
                or plan_events[0].payload.get("lifecycle_component_binding_hash")
                != lifecycle.content_hash
            ):
                raise RecoveryError("V29 lifecycle work-plan binding differs")
        return active.latest_plan

    def _validate_probe_arguments(
        self,
        arguments: dict[str, Any],
    ) -> RegisteredProbeProfile:
        if set(arguments) != {"probe_id", "source"}:
            raise ContractError("run_probe requires only probe_id and source")
        probe_id = arguments.get("probe_id")
        source = arguments.get("source")
        if not isinstance(probe_id, str) or not probe_id:
            raise ContractError("run_probe probe_id must be a non-empty string")
        profiles = {profile.id: profile for profile in self.task.probe_profiles}
        profile = profiles.get(probe_id)
        if profile is None:
            raise PolicyViolation(
                f"unregistered probe profile: {probe_id}",
                details={
                    "stage": "probe",
                    "reason": "unregistered_probe_profile",
                },
            )
        if not isinstance(source, str) or not source.strip():
            raise ContractError("run_probe source must be a non-empty string")
        if "\x00" in source:
            raise ContractError("run_probe source cannot contain NUL bytes")
        source_bytes = len(source.encode("utf-8"))
        if source_bytes > _PROBE_SOURCE_LIMIT_BYTES or source_bytes > profile.source_limit_bytes:
            raise PolicyViolation(
                "run_probe source exceeds its registered profile limit",
                details={
                    "stage": "probe",
                    "reason": "probe_source_too_large",
                    "source_bytes": source_bytes,
                    "source_limit_bytes": profile.source_limit_bytes,
                },
            )
        _validate_probe_source_policy(source)
        return profile

    def _read_file(self, path: str, start_line: int, end_line: int) -> dict[str, Any]:
        validate_inspection_arguments(
            self.workspace,
            "read_file",
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
            },
        )
        target = ensure_within(self.workspace, path)
        raw = target.read_text(encoding="utf-8", errors="replace")
        lines = raw.splitlines()
        selected = lines[start_line - 1 : end_line]
        line_count = len(selected)
        actual_start_line = start_line if selected else None
        actual_end_line = start_line + line_count - 1 if selected else None
        result = {
            "path": path,
            "start_line": start_line,
            "end_line": end_line,
            "content": "\n".join(selected),
        }
        if self.context_policy_version not in _INVESTIGATION_CONTEXT_POLICIES:
            return result
        return {
            **result,
            "actual_start_line": actual_start_line,
            "actual_end_line": actual_end_line,
            "line_count": line_count,
            "total_lines": len(lines),
            "eof_reached": end_line >= len(lines),
            "file_content_hash": sha256_text(raw),
        }

    def _search_files(self, query: str, path_glob: str = "**/*") -> dict[str, Any]:
        validate_inspection_arguments(
            self.workspace,
            "search_files",
            {"query": query, "path_glob": path_glob},
        )
        executed_path_glob = path_glob
        normalization_reasons: list[str] = []
        if self.tool_schema_version in _SEARCH_GLOB_NORMALIZATION_TOOL_SCHEMAS:
            canonical_glob = safe_relative_path(path_glob, field_name="path_glob")
            if canonical_glob == "**" or canonical_glob.endswith("/**"):
                executed_path_glob = canonical_glob + "/*"
                normalization_reasons = ["trailing_recursive_directory_pattern"]

        def normalization_evidence() -> dict[str, Any]:
            return {
                "schema_version": "search-glob-normalization-evidence-v1",
                "policy_version": _SEARCH_GLOB_NORMALIZATION_POLICY_VERSION,
                "raw_path_glob": path_glob,
                "executed_path_glob": executed_path_glob,
                "changed": executed_path_glob != path_glob,
                "reasons": normalization_reasons,
                "raw_path_glob_hash": sha256_text(path_glob),
                "executed_path_glob_hash": sha256_text(executed_path_glob),
            }

        matches: list[dict[str, Any]] = []
        for path in self.workspace.glob(executed_path_glob):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for line_number, line in enumerate(lines, 1):
                if query in line:
                    matches.append(
                        {
                            "path": path.relative_to(self.workspace).as_posix(),
                            "line": line_number,
                            "text": line[:500],
                        }
                    )
                    if len(matches) >= 100:
                        result = {
                            "query": query,
                            "matches": matches,
                            "truncated": True,
                        }
                        if self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES:
                            result.update(
                                {
                                    "path_glob": path_glob,
                                    "match_count": len(matches),
                                }
                            )
                            if self.tool_schema_version in _SEARCH_GLOB_NORMALIZATION_TOOL_SCHEMAS:
                                result["search_glob_normalization"] = normalization_evidence()
                        return result
        result = {
            "query": query,
            "matches": matches,
            "truncated": False,
        }
        if self.context_policy_version in _INVESTIGATION_CONTEXT_POLICIES:
            result.update(
                {
                    "path_glob": path_glob,
                    "match_count": len(matches),
                }
            )
            if self.tool_schema_version in _SEARCH_GLOB_NORMALIZATION_TOOL_SCHEMAS:
                result["search_glob_normalization"] = normalization_evidence()
        return result

    def _bounded_patch_source_snapshot(
        self,
        patch: str,
        *,
        candidate_content_hash: str,
        input_hash: str,
        worktree_diff_hash: str,
    ) -> dict[str, Any]:
        """Capture small current-source slices without relaxing patch validation."""

        entries: list[dict[str, Any]] = []
        unavailable: list[dict[str, Any]] = []
        remaining_characters = _PATCH_SOURCE_MAX_CHARACTERS
        sections: list[list[str]] = []
        for line in patch.splitlines():
            if line.startswith("diff --git "):
                sections.append([line])
            elif sections:
                sections[-1].append(line)

        for section_index, section in enumerate(sections, 1):
            old_header = next(
                (line for line in section if line.startswith("--- ")),
                None,
            )
            if old_header is None:
                unavailable.append(
                    {
                        "section": section_index,
                        "reason": "missing_old_header",
                    }
                )
                continue
            raw_path = _header_path(old_header)
            try:
                path = safe_relative_path(
                    raw_path,
                    field_name="patch source snapshot path",
                )
                target = self._prepared_workspace_target(
                    path,
                    recovery=False,
                )
            except (ContractError, PolicyViolation):
                unavailable.append(
                    {
                        "section": section_index,
                        "path": raw_path[:500],
                        "reason": "unsafe_target",
                    }
                )
                continue
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", path],
                cwd=self.workspace,
                capture_output=True,
                check=False,
            )
            if tracked.returncode != 0 or not target.is_file():
                unavailable.append(
                    {
                        "section": section_index,
                        "path": path,
                        "reason": "untracked_or_missing_target",
                    }
                )
                continue
            try:
                raw = target.read_bytes()
                text = raw.decode("utf-8", errors="strict")
            except (OSError, UnicodeDecodeError):
                unavailable.append(
                    {
                        "section": section_index,
                        "path": path,
                        "reason": "source_not_utf8_text",
                    }
                )
                continue
            lines = text.splitlines()
            hunk_headers = [
                (line_index, line, _HUNK_HEADER.fullmatch(line))
                for line_index, line in enumerate(section)
                if line.startswith("@@")
            ]
            valid_hunks = [
                (line_index, line, match)
                for line_index, line, match in hunk_headers
                if match is not None
            ]
            if not valid_hunks:
                unavailable.append(
                    {
                        "section": section_index,
                        "path": path,
                        "reason": (
                            "invalid_hunk_header" if hunk_headers else "missing_hunk_header"
                        ),
                    }
                )
                continue

            for hunk_index, (line_index, header, match) in enumerate(
                valid_hunks,
                1,
            ):
                if len(entries) >= _PATCH_SOURCE_MAX_ENTRIES:
                    unavailable.append(
                        {
                            "section": section_index,
                            "path": path,
                            "hunk": hunk_index,
                            "reason": "entry_limit",
                        }
                    )
                    continue
                assert match is not None
                old_start = int(match.group(1))
                declared_old_count = int(match.group(2)) if match.group(2) is not None else 1
                next_hunk = next(
                    (
                        candidate_index
                        for candidate_index, _, _ in valid_hunks
                        if candidate_index > line_index
                    ),
                    len(section),
                )
                body = section[line_index + 1 : next_hunk]
                recounted_old_count = sum(
                    1
                    for body_line in body
                    if body_line.startswith((" ", "-")) and not body_line.startswith("--- ")
                )
                effective_old_count = max(
                    declared_old_count,
                    recounted_old_count,
                    1,
                )
                requested_start = max(1, old_start - 3)
                requested_end = old_start + effective_old_count + 2
                requested_end = min(
                    requested_end,
                    requested_start + _PATCH_SOURCE_MAX_LINES_PER_ENTRY - 1,
                )
                actual_start = requested_start if requested_start <= len(lines) else None
                actual_end = min(requested_end, len(lines)) if actual_start is not None else None
                content = (
                    "\n".join(lines[actual_start - 1 : actual_end])
                    if actual_start is not None and actual_end is not None
                    else ""
                )
                characters = len(content)
                if characters > remaining_characters:
                    unavailable.append(
                        {
                            "section": section_index,
                            "path": path,
                            "hunk": hunk_index,
                            "reason": "character_limit",
                        }
                    )
                    continue
                remaining_characters -= characters
                entries.append(
                    {
                        "section": section_index,
                        "hunk": hunk_index,
                        "path": path,
                        "header": header,
                        "requested_start_line": requested_start,
                        "requested_end_line": requested_end,
                        "actual_start_line": actual_start,
                        "actual_end_line": actual_end,
                        "total_lines": len(lines),
                        "file_content_hash": sha256_bytes(raw),
                        "content": content,
                        "content_hash": sha256_text(content),
                    }
                )

        snapshot = {
            "schema_version": "patch-source-snapshot-v1",
            "candidate_content_hash": candidate_content_hash,
            "input_hash": input_hash,
            "worktree_diff_hash": worktree_diff_hash,
            "limits": {
                "max_entries": _PATCH_SOURCE_MAX_ENTRIES,
                "max_lines_per_entry": _PATCH_SOURCE_MAX_LINES_PER_ENTRY,
                "max_characters": _PATCH_SOURCE_MAX_CHARACTERS,
            },
            "entries": entries,
            "unavailable": unavailable,
        }
        snapshot["content_hash"] = sha256_text(canonical_json(snapshot))
        return snapshot

    @staticmethod
    def _edit_correction_reason(name: str, error: Exception) -> str:
        details = getattr(error, "details", {})
        if name == "apply_patch" and isinstance(details, dict):
            reason = details.get("reason")
            if isinstance(reason, str) and reason:
                return reason
        lowered = str(error).lower()
        if "expected text is absent" in lowered:
            return "expected_text_absent"
        if "expected text is ambiguous" in lowered:
            return "expected_text_ambiguous"
        if "logical diff limit" in lowered:
            return "logical_diff_limit"
        if "changed-file limit" in lowered:
            return "changed_file_limit"
        if "arguments are invalid" in lowered:
            return "invalid_arguments"
        if "source diff is stale" in lowered:
            return "source_diff_stale"
        if "target is unavailable" in lowered:
            return "target_unavailable"
        if "outside allowed paths" in lowered or "forbidden" in lowered:
            return "path_scope"
        return "structured_edit_rejected" if name == STRUCTURED_EDIT_TOOL_NAME else "edit_rejected"

    def _path_is_publicly_editable(self, path: str) -> bool:
        def matches(pattern: str) -> bool:
            return (
                pattern == "**"
                or fnmatch.fnmatchcase(path, pattern)
                or PurePosixPath(path).match(pattern)
            )

        return any(matches(pattern) for pattern in self.task.constraints.allowed_paths) and not any(
            matches(pattern) for pattern in self.task.constraints.forbidden_paths
        )

    def _bounded_structured_source_correction(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Return bounded public preimage excerpts; never infer or apply an edit."""

        entries: list[dict[str, Any]] = []
        unavailable: list[dict[str, Any]] = []
        remaining_characters = _EDIT_CORRECTION_MAX_CHARACTERS
        raw_files = arguments.get("files")
        if not isinstance(raw_files, list):
            return {
                "schema_version": "structured-current-source-correction-v1",
                "limits": {
                    "max_files": _EDIT_CORRECTION_MAX_FILES,
                    "max_excerpts": _EDIT_CORRECTION_MAX_EXCERPTS,
                    "max_characters": _EDIT_CORRECTION_MAX_CHARACTERS,
                    "context_lines": _EDIT_CORRECTION_CONTEXT_LINES,
                },
                "entries": [],
                "unavailable": [{"reason": "invalid_files_argument"}],
                "transport_newlines_normalized_for_display": True,
            }

        for file_index, raw_file in enumerate(raw_files[:_EDIT_CORRECTION_MAX_FILES], 1):
            if not isinstance(raw_file, dict) or not isinstance(raw_file.get("path"), str):
                unavailable.append({"file": file_index, "reason": "invalid_file_argument"})
                continue
            raw_path = str(raw_file["path"])
            try:
                path = safe_relative_path(raw_path, field_name="edit correction path")
                if path != raw_path or not self._path_is_publicly_editable(path):
                    raise ContractError("edit correction path is outside public task scope")
                target = self._prepared_workspace_target(path, recovery=False)
            except (ContractError, PolicyViolation):
                unavailable.append(
                    {"file": file_index, "path": raw_path[:500], "reason": "unsafe_target"}
                )
                continue
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", path],
                cwd=self.workspace,
                capture_output=True,
                check=False,
            )
            if tracked.returncode != 0 or not target.is_file():
                unavailable.append(
                    {"file": file_index, "path": path, "reason": "untracked_or_missing_target"}
                )
                continue
            try:
                raw = target.read_bytes()
                text = raw.decode("utf-8", errors="strict")
            except (OSError, UnicodeDecodeError):
                unavailable.append(
                    {"file": file_index, "path": path, "reason": "source_not_utf8_text"}
                )
                continue
            lines = text.splitlines()
            replacements = raw_file.get("replacements")
            if not isinstance(replacements, list):
                unavailable.append(
                    {"file": file_index, "path": path, "reason": "invalid_replacements_argument"}
                )
                continue
            for replacement_index, replacement in enumerate(replacements, 1):
                if len(entries) >= _EDIT_CORRECTION_MAX_EXCERPTS:
                    unavailable.append(
                        {
                            "file": file_index,
                            "path": path,
                            "replacement": replacement_index,
                            "reason": "excerpt_limit",
                        }
                    )
                    continue
                if not isinstance(replacement, dict) or not isinstance(
                    replacement.get("expected_text"), str
                ):
                    unavailable.append(
                        {
                            "file": file_index,
                            "path": path,
                            "replacement": replacement_index,
                            "reason": "invalid_expected_text",
                        }
                    )
                    continue
                expected = str(replacement["expected_text"])
                replacement_text = replacement.get("replacement_text")
                occurrences: list[int] = []
                cursor = 0
                while expected and len(occurrences) < 4:
                    position = text.find(expected, cursor)
                    if position < 0:
                        break
                    occurrences.append(position)
                    cursor = position + 1
                occurrence_count = text.count(expected) if expected else 0
                candidate_lines = [text.count("\n", 0, position) + 1 for position in occurrences]
                match_ratio: float | None = None
                if candidate_lines:
                    center_line = candidate_lines[0]
                else:
                    expected_lines = [
                        line.strip() for line in expected.splitlines() if line.strip()
                    ]
                    anchor = max(expected_lines, key=len, default="")
                    if anchor and lines:
                        ratios = [
                            difflib.SequenceMatcher(
                                None, anchor, line.strip(), autojunk=False
                            ).ratio()
                            for line in lines
                        ]
                        best_index = max(range(len(ratios)), key=lambda index: ratios[index])
                        center_line = best_index + 1
                        match_ratio = round(ratios[best_index], 4)
                    else:
                        center_line = 1
                start_line = max(1, center_line - _EDIT_CORRECTION_CONTEXT_LINES)
                end_line = min(
                    len(lines),
                    center_line + _EDIT_CORRECTION_CONTEXT_LINES,
                )
                content = "\n".join(lines[start_line - 1 : end_line])
                if len(content) > remaining_characters:
                    unavailable.append(
                        {
                            "file": file_index,
                            "path": path,
                            "replacement": replacement_index,
                            "reason": "character_limit",
                        }
                    )
                    continue
                remaining_characters -= len(content)
                entries.append(
                    {
                        "file": file_index,
                        "replacement": replacement_index,
                        "path": path,
                        "file_content_hash": sha256_bytes(raw),
                        "total_lines": len(lines),
                        "expected_text_hash": sha256_text(expected),
                        "expected_line_count": len(expected.splitlines()) or 1,
                        "replacement_line_count": (
                            len(replacement_text.splitlines()) or 1
                            if isinstance(replacement_text, str)
                            else None
                        ),
                        "exact_occurrence_count": occurrence_count,
                        "exact_occurrence_start_lines": candidate_lines,
                        "closest_line_match_ratio": match_ratio,
                        "start_line": start_line,
                        "end_line": end_line,
                        "content": content,
                        "content_hash": sha256_text(content),
                    }
                )
        if len(raw_files) > _EDIT_CORRECTION_MAX_FILES:
            unavailable.append({"reason": "file_limit", "omitted_files": len(raw_files) - 4})
        return {
            "schema_version": "structured-current-source-correction-v1",
            "limits": {
                "max_files": _EDIT_CORRECTION_MAX_FILES,
                "max_excerpts": _EDIT_CORRECTION_MAX_EXCERPTS,
                "max_characters": _EDIT_CORRECTION_MAX_CHARACTERS,
                "context_lines": _EDIT_CORRECTION_CONTEXT_LINES,
            },
            "entries": entries,
            "unavailable": unavailable,
            "transport_newlines_normalized_for_display": True,
        }

    def _edit_correction_evidence(
        self,
        *,
        name: str,
        arguments: dict[str, Any],
        error: Exception,
        pre_call_worktree_diff_hash: str,
        patch_source_snapshot: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if self.tool_schema_version not in {"v11", "v12"} or name not in _MUTATION_TOOL_NAMES:
            return None
        reason = self._edit_correction_reason(name, error)
        if name == "apply_patch":
            current_source = patch_source_snapshot or {
                "schema_version": "patch-source-snapshot-v1",
                "entries": [],
                "unavailable": [{"reason": "candidate_source_unavailable"}],
            }
            guidance = (
                "Regenerate a complete raw Git diff from the exact current-source excerpts. "
                "Do not reuse stale hunk context or invent missing numeric ranges."
            )
        else:
            current_source = self._bounded_structured_source_correction(arguments)
            guidance = (
                "Retry one smallest unique current expected_text span. Every removed and "
                "added logical line counts toward max_diff_lines; split independent edits "
                "across successful mutation turns instead of replacing a whole function."
            )
        body = {
            "schema_version": "edit-correction-evidence-v1",
            "policy_version": "bounded-public-current-source-v1",
            "tool": name,
            "failure_reason": reason,
            "pre_call_worktree_diff_hash": pre_call_worktree_diff_hash,
            "current_worktree_diff_hash": WorkspaceManager.diff_summary(self.workspace).patch_hash,
            "task_constraints": {
                "max_changed_files": self.task.constraints.max_changed_files,
                "max_diff_lines": self.task.constraints.max_diff_lines,
            },
            "guidance": guidance,
            "current_source": current_source,
            "public_task_source_only": True,
            "mutation_synthesized": False,
            "workspace_writes_performed": 0,
            "provider_calls_authorized": False,
        }
        return {**body, "content_hash": sha256_text(canonical_json(body))}

    def _prepare_patch_mutation(
        self,
        action_id: str,
        input_hash: str,
        patch: str,
        patch_artifact: Artifact,
    ) -> dict[str, Any]:
        if len(patch.encode("utf-8")) > 500_000:
            raise PolicyViolation(
                "patch exceeds the tool input limit",
                details={
                    "stage": "policy",
                    "reason": "input_too_large",
                    "guidance": "Reduce the patch to the smallest scoped change.",
                },
            )
        if self.tool_schema_version in _PATCH_RETRY_TOOL_SCHEMAS:
            _validate_raw_git_patch(
                patch,
                diagnose_hunk_headers=True,
                diagnose_wrappers=(
                    self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS
                ),
            )
        else:
            _validate_raw_git_patch(patch)
        baseline = WorkspaceManager.diff_summary(self.workspace)
        baseline_untracked = WorkspaceManager.untracked_files(self.workspace)
        if baseline_untracked:
            raise RecoveryError("agent workspace contains untracked files before patch application")
        paths = _patch_paths(patch)
        expected_diff_hash = self._preview_expected_diff_hash(
            patch,
            baseline.patch_hash,
        )
        if expected_diff_hash == baseline.patch_hash:
            raise PolicyViolation(
                "patch does not change the tracked worktree",
                details={
                    "stage": "policy",
                    "reason": "no_effect",
                    "guidance": "Submit a patch that changes the implicated tracked code.",
                },
            )
        files = self._prepare_file_images(patch, paths)
        intent = {
            "schema_version": "patch-mutation-intent-v1",
            "run_id": self.run_id,
            "action_id": action_id,
            "input_hash": input_hash,
            "patch_artifact": patch_artifact.model_dump(mode="json"),
            "baseline_worktree_diff_hash": baseline.patch_hash,
            "expected_worktree_diff_hash": expected_diff_hash,
            "files": files,
        }
        artifact = self.artifacts.put_json(intent)
        self.state.append_event(
            self.run_id,
            EventType.PATCH_PREPARED,
            actor="tool-gateway",
            correlation_id=action_id,
            payload={
                "schema_version": "patch-mutation-intent-v1",
                "artifact_id": artifact.artifact_id,
                "artifact_path": artifact.path,
                "content_hash": artifact.content_hash,
                "size_bytes": artifact.size_bytes,
                "intent_artifact": artifact.model_dump(mode="json"),
                "baseline_worktree_diff_hash": baseline.patch_hash,
                "expected_worktree_diff_hash": expected_diff_hash,
            },
        )
        return intent

    def _preview_expected_diff_hash(
        self,
        patch: str,
        baseline_diff_hash: str,
    ) -> str:
        with tempfile.TemporaryDirectory(prefix="patchloop-index-") as temporary:
            index_path = Path(temporary) / "index"
            object_path = Path(temporary) / "objects"
            object_path.mkdir()
            git_objects = subprocess.run(
                ["git", "rev-parse", "--git-path", "objects"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if git_objects.returncode != 0:
                raise RecoveryError("patch preview could not resolve the repository object store")
            alternate_objects = Path(git_objects.stdout.strip())
            if not alternate_objects.is_absolute():
                alternate_objects = (self.workspace / alternate_objects).resolve()
            environment = os.environ.copy()
            environment["GIT_INDEX_FILE"] = str(index_path)
            environment["GIT_OBJECT_DIRECTORY"] = str(object_path)
            environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(alternate_objects)

            def run(*args: str, input_bytes: bytes | None = None) -> bytes:
                completed = subprocess.run(
                    ["git", *args],
                    cwd=self.workspace,
                    env=environment,
                    input=input_bytes,
                    capture_output=True,
                    check=False,
                )
                if completed.returncode != 0:
                    message = completed.stderr.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()
                    raise ContractError(
                        f"patch preview failed during git {' '.join(args)}: {message}"
                    )
                return completed.stdout

            run("read-tree", "HEAD")
            run("add", "-u", "--", ".")
            baseline_patch = run(
                "diff",
                "--cached",
                "--no-ext-diff",
                "--binary",
            ).decode("utf-8", errors="strict")
            if sha256_text(baseline_patch) != baseline_diff_hash:
                raise RecoveryError("temporary patch preview does not match the current worktree")
            try:
                run(
                    "apply",
                    "--cached",
                    "--recount",
                    "--whitespace=nowarn",
                    "-",
                    input_bytes=patch.encode("utf-8"),
                )
            except ContractError as exc:
                if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS:
                    raise _git_apply_contract_error(
                        f"patch application failed during preparation: {exc}",
                        str(exc),
                    ) from exc
                raise _patch_contract_error(
                    f"patch application failed during preparation: {exc}",
                    reason="git_apply_failed",
                    stage="context",
                ) from exc
            expected_patch = run(
                "diff",
                "--cached",
                "--no-ext-diff",
                "--binary",
            ).decode("utf-8", errors="strict")
        return sha256_text(expected_patch)

    def _hypothetical_preimage_diff_hash(
        self,
        intent: dict[str, Any],
    ) -> str:
        """Hash current tracked state with touched paths reset in a temp index."""

        with tempfile.TemporaryDirectory(prefix="patchloop-reconcile-index-") as temporary:
            index_path = Path(temporary) / "index"
            object_path = Path(temporary) / "objects"
            object_path.mkdir()
            git_objects = subprocess.run(
                ["git", "rev-parse", "--git-path", "objects"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if git_objects.returncode != 0:
                raise RecoveryError("mixed-state preview could not resolve the object store")
            alternate_objects = Path(git_objects.stdout.strip())
            if not alternate_objects.is_absolute():
                alternate_objects = (self.workspace / alternate_objects).resolve()
            environment = os.environ.copy()
            environment["GIT_INDEX_FILE"] = str(index_path)
            environment["GIT_OBJECT_DIRECTORY"] = str(object_path)
            environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(alternate_objects)

            def run(
                *args: str,
                input_bytes: bytes | None = None,
            ) -> bytes:
                completed = subprocess.run(
                    ["git", *args],
                    cwd=self.workspace,
                    env=environment,
                    input=input_bytes,
                    capture_output=True,
                    check=False,
                )
                if completed.returncode != 0:
                    message = completed.stderr.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()
                    raise RecoveryError(
                        f"mixed-state preview failed during git {' '.join(args)}: {message}"
                    )
                return completed.stdout

            run("read-tree", "HEAD")
            run("add", "-u", "--", ".")
            for entry in intent["files"]:
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                preimage = self.artifacts.read_bytes(
                    Artifact.model_validate(entry["preimage_artifact"])
                )
                object_id = (
                    run(
                        "hash-object",
                        "-w",
                        "--stdin",
                        input_bytes=preimage,
                    )
                    .decode("ascii")
                    .strip()
                )
                run(
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    str(entry["git_mode"]),
                    object_id,
                    path,
                )
            patch = run(
                "diff",
                "--cached",
                "--no-ext-diff",
                "--binary",
            ).decode("utf-8", errors="strict")
        return sha256_text(patch)

    def _prepare_file_images(
        self,
        patch: str,
        paths: list[str],
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="patchloop-preview-") as temporary:
            scratch = Path(temporary)
            initialize = subprocess.run(
                ["git", "init", "--quiet"],
                cwd=scratch,
                capture_output=True,
                check=False,
            )
            if initialize.returncode != 0:
                raise RecoveryError("patch preview repository initialization failed")
            for path in paths:
                source = self._prepared_workspace_target(
                    path,
                    recovery=False,
                )
                tracked = subprocess.run(
                    ["git", "ls-files", "--stage", "-z", "--", path],
                    cwd=self.workspace,
                    capture_output=True,
                    check=False,
                )
                tracked_entries = [item for item in tracked.stdout.split(b"\0") if item]
                git_mode = None
                if len(tracked_entries) == 1:
                    try:
                        stage, tracked_path = tracked_entries[0].split(
                            b"\t",
                            1,
                        )
                        stage_fields = stage.decode("ascii").split()
                        decoded_path = tracked_path.decode("utf-8")
                        if (
                            len(stage_fields) == 3
                            and stage_fields[2] == "0"
                            and decoded_path.replace("\\", "/") == path
                        ):
                            git_mode = stage_fields[0]
                    except (UnicodeDecodeError, ValueError):
                        git_mode = None
                source_stat = source.lstat() if source.exists() else None
                if (
                    tracked.returncode != 0
                    or git_mode not in {"100644", "100755"}
                    or source_stat is None
                    or not stat.S_ISREG(source_stat.st_mode)
                ):
                    raise _patch_contract_error(
                        f"patch target must be an existing tracked regular file: {path}",
                        reason="unsupported_target",
                        stage="policy",
                    )
                preimage = source.read_bytes()
                pre_artifact = self.artifacts.put_bytes(preimage)
                target = ensure_within(scratch, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(preimage)
                os.chmod(target, stat.S_IMODE(source_stat.st_mode))
                entries.append(
                    {
                        "path": path,
                        "mode": stat.S_IMODE(source_stat.st_mode),
                        "git_mode": git_mode,
                        "preimage_artifact": pre_artifact.model_dump(mode="json"),
                    }
                )

            completed = subprocess.run(
                ["git", "apply", "--recount", "--whitespace=nowarn", "-"],
                cwd=scratch,
                input=patch.encode("utf-8"),
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                error = completed.stderr.decode(
                    "utf-8",
                    errors="replace",
                ).strip()
                if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS:
                    raise _git_apply_contract_error(
                        f"patch preview application failed: {error}",
                        error,
                    )
                raise _patch_contract_error(
                    f"patch preview application failed: {error}",
                    reason="git_apply_failed",
                    stage="context",
                )
            for entry in entries:
                target = ensure_within(scratch, str(entry["path"]))
                entry["postimage_artifact"] = (
                    self.artifacts.put_bytes(target.read_bytes()).model_dump(mode="json")
                    if target.exists()
                    else None
                )
        return entries

    def _apply_patch(
        self,
        patch: str,
        *,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if len(patch.encode("utf-8")) > 500_000:
            raise PolicyViolation(
                "patch exceeds the tool input limit",
                details={
                    "stage": "policy",
                    "reason": "input_too_large",
                    "guidance": "Reduce the patch to the smallest scoped change.",
                },
            )
        if self.tool_schema_version in _PATCH_RETRY_TOOL_SCHEMAS:
            _validate_raw_git_patch(
                patch,
                diagnose_hunk_headers=True,
                diagnose_wrappers=(
                    self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS
                ),
            )
        else:
            _validate_raw_git_patch(patch)
        baseline = WorkspaceManager.diff_summary(self.workspace)
        baseline_untracked = WorkspaceManager.untracked_files(self.workspace)
        if baseline_untracked:
            raise RecoveryError("agent workspace contains untracked files before patch application")
        expected_diff_hash = None
        if intent is not None:
            if intent.get("baseline_worktree_diff_hash") != baseline.patch_hash:
                raise RecoveryError("prepared patch baseline does not match the current worktree")
            expected_diff_hash = intent.get("expected_worktree_diff_hash")
            self._apply_patch_postimages(intent)
        else:
            completed = subprocess.run(
                ["git", "apply", "--recount", "--whitespace=nowarn", "-"],
                cwd=self.workspace,
                input=patch.encode("utf-8"),
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                error = completed.stderr.decode(
                    "utf-8",
                    errors="replace",
                ).strip()
                if self.tool_schema_version in _SAFE_PATCH_NORMALIZATION_TOOL_SCHEMAS:
                    raise _git_apply_contract_error(
                        f"patch application failed: {error}",
                        error,
                    )
                line_match = re.search(
                    r"(?:corrupt patch at line|patch at line) (\d+)",
                    error,
                )
                raise _patch_contract_error(
                    f"patch application failed: {error}",
                    reason="git_apply_failed",
                    stage="syntax" if line_match else "context",
                    line=(int(line_match.group(1)) if line_match else None),
                )
        return self._finalize_applied_patch(
            patch,
            baseline.patch_hash,
            expected_diff_hash=expected_diff_hash,
            intent=intent,
        )

    def _apply_patch_postimages(self, intent: dict[str, Any]) -> None:
        recovery_root = self.artifacts.root / "recovery-tmp" / self.run_id
        recovery_root.mkdir(parents=True, exist_ok=True)
        prepared: list[tuple[dict[str, Any], str, Path, bytes | None]] = []
        for entry in intent["files"]:
            try:
                path = safe_relative_path(
                    str(entry["path"]),
                    field_name="prepared patch path",
                )
                target = self._prepared_workspace_target(
                    path,
                    recovery=True,
                )
                preimage = self.artifacts.read_bytes(
                    Artifact.model_validate(entry["preimage_artifact"])
                )
                mode = int(entry["mode"])
                post_raw = entry.get("postimage_artifact")
                postimage = (
                    self.artifacts.read_bytes(Artifact.model_validate(post_raw))
                    if post_raw is not None
                    else None
                )
                target_stat = target.lstat() if target.exists() else None
            except (ContractError, KeyError, TypeError, ValueError) as exc:
                raise RecoveryError("prepared patch contains invalid file image evidence") from exc
            if target_stat is None or not stat.S_ISREG(target_stat.st_mode):
                raise RecoveryError(f"prepared patch target is not in its pre-state: {path}")
            if target.read_bytes() != preimage or stat.S_IMODE(target_stat.st_mode) != mode:
                raise RecoveryError(f"prepared patch target is not in its pre-state: {path}")
            prepared.append((entry, path, target, postimage))

        try:
            for entry, _, target, postimage in prepared:
                if postimage is None:
                    target.unlink()
                    continue
                temporary = recovery_root / f"{uuid.uuid4().hex}.tmp"
                try:
                    with temporary.open("xb") as stream:
                        stream.write(postimage)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary, int(entry["mode"]))
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
        except Exception as exc:
            try:
                self._restore_patch_preimages(intent)
            except Exception as rollback_error:
                raise RecoveryError(
                    "prepared patch write failed and preimage restoration failed"
                ) from rollback_error
            raise RecoveryError("prepared patch write failed; preimages were restored") from exc

    def _finalize_applied_patch(
        self,
        patch: str,
        baseline_diff_hash: str,
        *,
        expected_diff_hash: str | None = None,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            summary = WorkspaceManager.diff_summary(self.workspace)
            if expected_diff_hash is not None and summary.patch_hash != expected_diff_hash:
                raise RecoveryError("applied patch does not match its prepared post-state")
            outcomes = [
                verify_scope(summary, self.task.constraints),
                verify_dependencies(summary, self.task.constraints),
                verify_test_tampering(summary),
                verify_public_api(summary, self.task.constraints, self.workspace),
            ]
            violations = [item for outcome in outcomes for item in outcome.violations]
            untracked = WorkspaceManager.untracked_files(self.workspace)
            if untracked:
                violations.append("patch produced untracked files: " + ", ".join(untracked))
        except Exception:
            self._rollback_patch(
                patch,
                baseline_diff_hash,
                intent=intent,
            )
            raise
        if violations:
            self._rollback_patch(
                patch,
                baseline_diff_hash,
                intent=intent,
            )
            raise PolicyViolation(
                "; ".join(violations),
                details={
                    "stage": "policy",
                    "reason": "deterministic_policy_violation",
                    "guidance": "Limit the patch to the declared task scope and retry.",
                },
            )
        return {
            "patch_hash": sha256_text(patch),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "diff_lines": summary.diff_lines,
        }

    def _rollback_patch(
        self,
        patch: str,
        baseline_diff_hash: str,
        *,
        intent: dict[str, Any] | None = None,
    ) -> None:
        if intent is not None:
            self._restore_patch_preimages(intent)
            return
        rollback = subprocess.run(
            [
                "git",
                "apply",
                "--reverse",
                "--recount",
                "--whitespace=nowarn",
                "-",
            ],
            cwd=self.workspace,
            input=patch.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if rollback.returncode != 0:
            error = rollback.stderr.decode("utf-8", errors="replace").strip()
            raise RecoveryError(f"policy rollback failed: {error}")
        try:
            restored = WorkspaceManager.diff_summary(self.workspace)
            untracked = WorkspaceManager.untracked_files(self.workspace)
        except Exception as exc:
            raise RecoveryError("policy rollback state could not be verified") from exc
        if restored.patch_hash != baseline_diff_hash or untracked:
            raise RecoveryError("policy rollback did not restore the pre-call workspace state")

    def _run_check(self, check_id: str) -> dict[str, Any]:
        checks = {check.id: check for check in self.task.visible_checks}
        if check_id not in checks:
            raise PolicyViolation(f"unregistered check: {check_id}")
        repeated_timeout = any(
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("check_id") == check_id
            and event.payload.get("timed_out") is True
            for event in self.state.list_events(self.run_id)
        )
        if repeated_timeout:
            raise PolicyViolation(
                "loop detector rejected an unchanged check after timeout; use a targeted check"
            )
        before = WorkspaceManager.diff_summary(self.workspace)
        outcome = self.sandbox.run_check(self.workspace, checks[check_id])
        after = WorkspaceManager.diff_summary(self.workspace)
        if before.patch_hash != after.patch_hash:
            raise RecoveryError("registered check modified the tracked worktree")
        passed = not outcome.timed_out and outcome.exit_code in checks[check_id].expected_exit_codes
        result = {
            "check_id": check_id,
            "exit_code": outcome.exit_code,
            "passed": passed,
            "timed_out": outcome.timed_out,
            "truncated": outcome.truncated,
            "stdout": outcome.stdout,
            "stderr": outcome.stderr,
            "worktree_diff_hash": before.patch_hash,
        }
        if self.tool_schema_version in {
            "v10",
            "v11",
            "v12",
            "v15",
            "v16",
            "v17",
            "v18",
            "v19",
            "v20",
            "v21",
            "v22",
            "v23",
            "v24",
            "v25",
            "v26",
            "v27",
            "v28",
            "v29",
        }:
            typed = project_registered_check_outcome(
                check_id=check_id,
                exit_code=outcome.exit_code,
                passed=passed,
                timed_out=outcome.timed_out,
                truncated=outcome.truncated,
                stdout=outcome.stdout,
                stderr=outcome.stderr,
                worktree_diff_hash=before.patch_hash,
            )
            result.update(typed.model_dump(mode="python"))
        return result

    def _run_probe(
        self,
        probe_id: str,
        source: str,
        *,
        source_artifact: Artifact | None,
    ) -> dict[str, Any]:
        arguments = {
            "probe_id": probe_id,
            "source": source,
        }
        profile = self._validate_probe_arguments(arguments)
        if source_artifact is None:
            raise RecoveryError("run_probe lacks its pre-dispatch source artifact")
        if self.artifacts.read_bytes(source_artifact) != source.encode("utf-8"):
            raise RecoveryError("run_probe source artifact conflicts with its tool input")
        if getattr(self.sandbox, "official", False) is not True:
            raise PolicyViolation(
                "run_probe requires the isolated Docker sandbox",
                details={
                    "stage": "sandbox",
                    "reason": "probe_requires_docker",
                    "guidance": (
                        "Use registered checks locally; agent-authored code "
                        "is never executed on the host."
                    ),
                },
            )
        manifest = self.state.get_manifest(self.run_id)
        if manifest.probe_image_digest is None:
            raise RecoveryError("run_probe requires a manifest-bound probe image identity")
        before = WorkspaceManager.diff_summary(self.workspace)
        before_untracked = WorkspaceManager.untracked_files(self.workspace)
        if before_untracked:
            raise RecoveryError("agent workspace contains untracked files before probe")
        outcome = self.sandbox.run_probe(
            self.workspace,
            source,
            timeout_seconds=min(profile.timeout_seconds, 60),
            output_limit_bytes=min(
                profile.output_limit_bytes,
                _PROBE_OUTPUT_LIMIT_BYTES,
            ),
            image_identity=manifest.probe_image_digest,
        )
        expected_execution_policy = probe_execution_policy(
            image_identity=manifest.probe_image_digest,
            timeout_seconds=profile.timeout_seconds,
            output_limit_bytes=profile.output_limit_bytes,
        )
        if outcome.execution_policy != expected_execution_policy:
            raise RecoveryError(
                "run_probe sandbox execution policy does not match "
                "the manifest-bound hardened profile"
            )
        after = WorkspaceManager.diff_summary(self.workspace)
        after_untracked = WorkspaceManager.untracked_files(self.workspace)
        if before.patch_hash != after.patch_hash or before_untracked != after_untracked:
            raise RecoveryError("ephemeral probe modified the persistent agent workspace")
        return {
            "schema_version": "ephemeral-python-probe-result-v2",
            "probe_policy_version": "ephemeral-python-probe-v2",
            "authoritative": False,
            "probe_id": profile.id,
            "probe_runtime": profile.runtime,
            "timeout_seconds": profile.timeout_seconds,
            "output_limit_bytes": profile.output_limit_bytes,
            "source_limit_bytes": profile.source_limit_bytes,
            "execution_policy": expected_execution_policy,
            "source_artifact": source_artifact.model_dump(mode="json"),
            "source_hash": source_artifact.content_hash,
            "command": outcome.command,
            "exit_code": outcome.exit_code,
            "passed": (not outcome.timed_out and outcome.exit_code == 0),
            "timed_out": outcome.timed_out,
            "truncated": outcome.truncated,
            "original_output_bytes": outcome.original_output_bytes,
            "stdout": outcome.stdout,
            "stderr": outcome.stderr,
            "duration_ms": outcome.duration_ms,
            "worktree_diff_hash": before.patch_hash,
        }

    def _review_task(
        self,
        requirements: list[dict[str, Any]],
        targeted_validation: list[dict[str, Any]],
        residual_risks: list[Any],
        coverage_targets: list[dict[str, Any]] | None = None,
        *,
        execution_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        review_input = {
            "requirements": requirements,
            "targeted_validation": targeted_validation,
            "residual_risks": residual_risks,
            **(
                {"coverage_targets": coverage_targets}
                if self.tool_schema_version in {"v5", "v6"}
                else {}
            ),
        }
        review_input_limit = (
            16_000 if self.tool_schema_version in {"v5", "v6"} else _REVIEW_INPUT_LIMIT_BYTES
        )
        if len(canonical_json(review_input).encode("utf-8")) > review_input_limit:
            raise PolicyViolation(
                f"review_task input exceeds {review_input_limit} bytes",
                details={
                    "stage": "review",
                    "reason": "review_input_too_large",
                },
            )
        if not isinstance(execution_context, dict):
            raise ContractError("review_task requires exact model-request evidence")
        request_artifact_id = execution_context.get("request_artifact_id")
        request_phase = execution_context.get("phase")
        presented = execution_context.get("presented_tool_results")
        if (
            not isinstance(request_artifact_id, str)
            or request_phase != "REVIEW"
            or not isinstance(presented, list)
        ):
            raise ContractError("review_task must run in REVIEW with bound request evidence")
        summary = WorkspaceManager.diff_summary(self.workspace)
        events = self.state.list_events(self.run_id)
        readiness = diff_bound_evidence(
            self.task,
            events,
            summary.patch_hash,
            presented_tool_results=presented,
            phase=Phase.REVIEW,
        )
        missing = [
            item
            for item in readiness.missing_evidence
            if item != "structured_task_review_current_diff"
        ]
        if missing:
            raise PolicyViolation(
                "review_task is not ready: " + ", ".join(missing),
                details={
                    "stage": "review",
                    "reason": "review_preconditions_missing",
                    "missing_evidence": missing,
                },
            )
        source_get_diff_sequence = readiness.review_event_sequence
        mutation_sequence = readiness.mutation_event_sequence
        if source_get_diff_sequence is None or mutation_sequence is None:
            raise RecoveryError("review_task readiness lacks mutation or diff provenance")
        presented_sequences = {
            int(item["event_sequence"])
            for item in presented
            if (
                isinstance(item, dict)
                and type(item.get("event_sequence")) is int
                and item.get("available") is True
                and item.get("truncated") is False
            )
        }
        events_by_sequence = {event.sequence: event for event in events}
        citable_sequences = set(presented_sequences)
        review_evidence: dict[str, Any] | None = None
        passing_validation_sequences = {
            sequence
            for sequence in presented_sequences
            if (
                (event := events_by_sequence.get(sequence)) is not None
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("worktree_diff_hash") == summary.patch_hash
                and event.payload.get("tool") in {"run_check", "run_probe"}
                and event.payload.get("passed") is True
            )
        }
        if self.context_policy_version in {
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            review_evidence = execution_context.get("review_evidence")
            if not isinstance(review_evidence, dict):
                raise ContractError(
                    "review_task requires bound review evidence",
                    details={
                        "schema_version": "review-citation-error-v1",
                        "stage": "review",
                        "reason": "review_evidence_missing",
                    },
                )
            raw_citable = review_evidence.get("citable_event_sequences")
            raw_passing = review_evidence.get("passing_check_event_sequences")
            raw_source_diff = review_evidence.get("source_get_diff_sequence")
            raw_mutation = review_evidence.get("mutation_event_sequence")
            expected_review_evidence_schema = (
                "review-evidence-v2"
                if self.context_policy_version in {"phase-evidence-v10", "phase-evidence-v11"}
                else "review-evidence-v1"
            )
            if (
                review_evidence.get("schema_version") != expected_review_evidence_schema
                or review_evidence.get("pinning_active") is not True
                or review_evidence.get("worktree_diff_hash") != summary.patch_hash
                or not isinstance(raw_citable, list)
                or not isinstance(raw_passing, list)
                or any(type(sequence) is not int for sequence in raw_citable)
                or any(type(sequence) is not int for sequence in raw_passing)
                or len(set(raw_citable)) != len(raw_citable)
                or len(set(raw_passing)) != len(raw_passing)
                or type(raw_source_diff) is not int
                or type(raw_mutation) is not int
                or raw_mutation != mutation_sequence
                or raw_source_diff != source_get_diff_sequence
                or (
                    self.context_policy_version == "phase-evidence-v9"
                    and raw_citable != [*raw_passing, raw_source_diff]
                )
                or not set(raw_citable).issubset(presented_sequences)
                or set(raw_passing) != set(readiness.current_diff_check_event_sequences)
            ):
                raise ContractError(
                    "review_task review evidence is inconsistent",
                    details={
                        "schema_version": "review-citation-error-v1",
                        "stage": "review",
                        "reason": "review_evidence_inconsistent",
                    },
                )
            citable_sequences = set(raw_citable)
            passing_validation_sequences = set(raw_passing)

        if not isinstance(requirements, list) or not 1 <= len(requirements) <= 20:
            raise ContractError("review_task requirements must contain 1 to 20 entries")
        review_contract = self.state.get_manifest(self.run_id).public_review_contract
        contract_review = self.tool_schema_version in {"v4", "v5", "v6"}
        coverage_review = self.tool_schema_version in {"v5", "v6"}
        structured_coverage_rejection = bool(
            self.tool_schema_version == "v6" and self.context_policy_version == "phase-evidence-v11"
        )
        active_coverage_rejection = (
            execution_context.get("coverage_rejection_feedback")
            if structured_coverage_rejection
            else None
        )
        if active_coverage_rejection is not None and (
            not isinstance(active_coverage_rejection, dict)
            or active_coverage_rejection.get("schema_version") != "coverage-rejection-feedback-v1"
            or not isinstance(
                active_coverage_rejection.get("coverage_target_id"),
                str,
            )
            or type(active_coverage_rejection.get("source_failure_sequence")) is not int
            or active_coverage_rejection["source_failure_sequence"] < 1
            or active_coverage_rejection.get("worktree_diff_hash") != summary.patch_hash
        ):
            raise RecoveryError("v11 review has invalid active coverage rejection feedback")
        if contract_review and review_contract is None:
            raise RecoveryError("contract-bound review lacks its public review contract")
        expected_contract_schema = (
            "public-review-contract-v2" if coverage_review else "public-review-contract-v1"
        )
        if (
            contract_review
            and review_contract is not None
            and review_contract.schema_version != expected_contract_schema
        ):
            raise RecoveryError("public review contract version conflicts with the tool schema")
        authoritative_requirements = {
            item.requirement_id: item.source_excerpt
            for item in (review_contract.requirements if review_contract is not None else [])
        }
        authoritative_targets: dict[str, Any] = {}
        target_parent_requirement: dict[str, str] = {}
        if coverage_review:
            assert review_contract is not None
            for requirement in review_contract.requirements:
                for target in requirement.coverage_targets:
                    authoritative_targets[target.coverage_target_id] = target
                    target_parent_requirement[target.coverage_target_id] = (
                        requirement.requirement_id
                    )
            if review_evidence is None:
                raise RecoveryError("coverage review lacks its request-bound review evidence")
            raw_target_evidence = review_evidence.get("coverage_target_event_sequences")
            if (
                not isinstance(raw_target_evidence, dict)
                or len(raw_target_evidence) != len(authoritative_targets)
                or set(raw_target_evidence) != set(authoritative_targets)
                or any(
                    not isinstance(sequences, list)
                    or any(type(sequence) is not int for sequence in sequences)
                    or sequences != sorted(set(sequences))
                    for sequences in raw_target_evidence.values()
                )
            ):
                raise ContractError("review_task coverage evidence target mapping is inconsistent")
            expected_citable: list[int] = []
            for target_id in authoritative_targets:
                sequences = raw_target_evidence[target_id]
                for sequence in sequences:
                    if sequence not in expected_citable:
                        expected_citable.append(sequence)
            for sequence in review_evidence["passing_check_event_sequences"]:
                if sequence not in expected_citable:
                    expected_citable.append(sequence)
            if source_get_diff_sequence not in expected_citable:
                expected_citable.append(source_get_diff_sequence)
            if review_evidence["citable_event_sequences"] != expected_citable:
                raise ContractError("review_task coverage evidence citations are not canonical")
            for target_id in authoritative_targets:
                sequences = raw_target_evidence[target_id]
                target = authoritative_targets[target_id]
                for sequence in sequences:
                    event = self._validate_review_evidence_sequence(
                        sequence,
                        events_by_sequence=events_by_sequence,
                        presented_sequences=presented_sequences,
                        citable_sequences=citable_sequences,
                        passing_validation_sequences=(passing_validation_sequences),
                        source_get_diff_sequence=source_get_diff_sequence,
                        mutation_sequence=mutation_sequence,
                        worktree_diff_hash=summary.patch_hash,
                    )
                    self._validate_coverage_target_evidence(
                        target,
                        event,
                    )
        normalized_requirements: list[dict[str, Any]] = []
        observed_requirement_ids: list[str] = []
        for item in requirements:
            expected_requirement_keys = (
                {
                    "requirement_id",
                    "status",
                    "evidence_event_sequences",
                    "notes",
                }
                if contract_review
                else {
                    "requirement",
                    "status",
                    "evidence_event_sequences",
                    "notes",
                }
            )
            if not isinstance(item, dict) or set(item) != expected_requirement_keys:
                raise ContractError("review_task requirement has an invalid shape")
            requirement_id = item.get("requirement_id")
            requirement = (
                authoritative_requirements.get(requirement_id)
                if contract_review
                else item["requirement"]
            )
            status = item["status"]
            sequences = item["evidence_event_sequences"]
            notes = item["notes"]
            if (
                not isinstance(requirement, str)
                or not requirement.strip()
                or len(requirement) > 1000
                or status
                not in {
                    "verified",
                    "partially_verified",
                    "unverified",
                }
                or not isinstance(sequences, list)
                or len(sequences) > 20
                or len(set(sequences)) != len(sequences)
                or any(type(sequence) is not int for sequence in sequences)
                or not isinstance(notes, str)
                or not notes.strip()
                or len(notes) > 2000
            ):
                raise ContractError("review_task requirement fields are invalid")
            if contract_review:
                if (
                    not isinstance(requirement_id, str)
                    or requirement_id not in authoritative_requirements
                    or requirement_id in observed_requirement_ids
                ):
                    raise ContractError("review_task requirement ID is unknown or duplicated")
                observed_requirement_ids.append(requirement_id)
            if status != "unverified" and not sequences:
                raise ContractError("verified review requirements need cited evidence")
            # V11 validates citations at the coverage-target boundary below.
            # Deferring the parent roll-up prevents a globally uncitable child
            # sequence from being reduced to a generic requirement error before
            # the gateway can return the offending target and its exact public
            # recovery evidence. V10 and earlier keep their historical order.
            if not structured_coverage_rejection:
                for sequence in sequences:
                    self._validate_review_evidence_sequence(
                        sequence,
                        events_by_sequence=events_by_sequence,
                        presented_sequences=presented_sequences,
                        citable_sequences=citable_sequences,
                        passing_validation_sequences=(passing_validation_sequences),
                        source_get_diff_sequence=source_get_diff_sequence,
                        mutation_sequence=mutation_sequence,
                        worktree_diff_hash=summary.patch_hash,
                    )
            normalized_requirement = {
                "status": status,
                "evidence_event_sequences": list(sequences),
                "notes": notes.strip(),
            }
            if contract_review:
                normalized_requirement.update(
                    {
                        "requirement_id": requirement_id,
                        "source_excerpt": requirement.strip(),
                    }
                )
            else:
                normalized_requirement["requirement"] = requirement.strip()
            normalized_requirements.append(normalized_requirement)

        if contract_review and set(observed_requirement_ids) != set(authoritative_requirements):
            raise ContractError(
                "review_task must assess every public review requirement exactly once"
            )
        if contract_review:
            requirement_rows_by_id = {
                item["requirement_id"]: item for item in normalized_requirements
            }
            normalized_requirements = [
                requirement_rows_by_id[requirement_id]
                for requirement_id in authoritative_requirements
            ]

        normalized_coverage_targets: list[dict[str, Any]] = []
        coverage_statuses: dict[str, str] = {}
        if coverage_review:
            if not isinstance(coverage_targets, list) or len(coverage_targets) != len(
                authoritative_targets
            ):
                raise ContractError(
                    "review_task must assess every public coverage target exactly once"
                )
            observed_target_ids: set[str] = set()
            assert review_evidence is not None
            target_evidence = review_evidence["coverage_target_event_sequences"]
            for item in coverage_targets:
                if not isinstance(item, dict) or set(item) != {
                    "coverage_target_id",
                    "status",
                    "evidence_event_sequences",
                    "notes",
                }:
                    raise ContractError("review_task coverage target has an invalid shape")
                target_id = item["coverage_target_id"]
                status = item["status"]
                sequences = item["evidence_event_sequences"]
                notes = item["notes"]
                if (
                    not isinstance(target_id, str)
                    or target_id not in authoritative_targets
                    or target_id in observed_target_ids
                    or status
                    not in {
                        "verified",
                        "partially_verified",
                        "unverified",
                    }
                    or not isinstance(sequences, list)
                    or len(sequences) > 20
                    or len(set(sequences)) != len(sequences)
                    or any(type(sequence) is not int for sequence in sequences)
                    or not isinstance(notes, str)
                    or not notes.strip()
                    or len(notes) > 2000
                ):
                    raise ContractError("review_task coverage target fields are invalid")
                authoritative_sequences = target_evidence[target_id]
                if not set(sequences).issubset(authoritative_sequences):
                    if structured_coverage_rejection:
                        raise self._coverage_citation_error(
                            reason="target_evidence_not_allowed",
                            target=authoritative_targets[target_id],
                            requirement_id=target_parent_requirement[target_id],
                            submitted_sequences=sequences,
                            allowed_sequences=authoritative_sequences,
                            mutation_sequence=mutation_sequence,
                            worktree_diff_hash=summary.patch_hash,
                            source_get_diff_sequence=source_get_diff_sequence,
                        )
                    raise ContractError("review_task coverage target cites unrelated evidence")
                if status == "verified" and (
                    not authoritative_sequences or sequences != authoritative_sequences
                ):
                    if structured_coverage_rejection:
                        raise self._coverage_citation_error(
                            reason="verified_target_evidence_mismatch",
                            target=authoritative_targets[target_id],
                            requirement_id=target_parent_requirement[target_id],
                            submitted_sequences=sequences,
                            allowed_sequences=authoritative_sequences,
                            mutation_sequence=mutation_sequence,
                            worktree_diff_hash=summary.patch_hash,
                            source_get_diff_sequence=source_get_diff_sequence,
                        )
                    raise ContractError("verified coverage target requires all advertised evidence")
                if (
                    structured_coverage_rejection
                    and isinstance(active_coverage_rejection, dict)
                    and active_coverage_rejection.get("coverage_target_id") == target_id
                    and (
                        status != "verified"
                        or not any(
                            sequence > active_coverage_rejection["source_failure_sequence"]
                            for sequence in sequences
                        )
                    )
                ):
                    raise self._coverage_citation_error(
                        reason="fresh_target_evidence_required",
                        target=authoritative_targets[target_id],
                        requirement_id=target_parent_requirement[target_id],
                        submitted_sequences=sequences,
                        allowed_sequences=authoritative_sequences,
                        mutation_sequence=mutation_sequence,
                        worktree_diff_hash=summary.patch_hash,
                        source_get_diff_sequence=source_get_diff_sequence,
                    )
                if status == "partially_verified" and not sequences:
                    raise ContractError("partially verified coverage target requires evidence")
                if status == "unverified" and sequences:
                    raise ContractError(
                        "unverified coverage target cannot cite supporting evidence"
                    )
                observed_target_ids.add(target_id)
                coverage_statuses[target_id] = status
                normalized_coverage_targets.append(
                    {
                        "coverage_target_id": target_id,
                        "requirement_id": target_parent_requirement[target_id],
                        "status": status,
                        "evidence_event_sequences": list(sequences),
                        "notes": notes.strip(),
                    }
                )
            if observed_target_ids != set(authoritative_targets):
                raise ContractError("review_task coverage targets are missing or duplicated")
            coverage_rows_by_id = {
                item["coverage_target_id"]: item for item in normalized_coverage_targets
            }
            normalized_coverage_targets = [
                coverage_rows_by_id[target_id] for target_id in authoritative_targets
            ]
            requirement_rows = {item["requirement_id"]: item for item in normalized_requirements}
            for requirement in review_contract.requirements:
                target_ids = [target.coverage_target_id for target in requirement.coverage_targets]
                statuses = [coverage_statuses[target_id] for target_id in target_ids]
                expected_status = (
                    "verified"
                    if all(status == "verified" for status in statuses)
                    else (
                        "unverified"
                        if all(status == "unverified" for status in statuses)
                        else "partially_verified"
                    )
                )
                row = requirement_rows[requirement.requirement_id]
                expected_sequences: list[int] = []
                for target_id in target_ids:
                    target_row = next(
                        item
                        for item in normalized_coverage_targets
                        if item["coverage_target_id"] == target_id
                    )
                    for sequence in target_row["evidence_event_sequences"]:
                        if sequence not in expected_sequences:
                            expected_sequences.append(sequence)
                if row["status"] != expected_status:
                    raise ContractError(
                        "review_task requirement status conflicts with target roll-up"
                    )
                if row["evidence_event_sequences"] != expected_sequences:
                    raise ContractError(
                        "review_task requirement evidence conflicts with target roll-up"
                    )
        elif coverage_targets is not None:
            raise ContractError("coverage_targets requires tool schema v5")

        if not isinstance(targeted_validation, list) or not 1 <= len(targeted_validation) <= 20:
            raise ContractError("review_task targeted_validation must contain 1 to 20 entries")
        normalized_validation: list[dict[str, Any]] = []
        current_validation_passed = False
        seen_validation_sequences: set[int] = set()
        for item in targeted_validation:
            if not isinstance(item, dict) or set(item) != {
                "kind",
                "event_sequence",
                "outcome",
                "notes",
            }:
                raise ContractError("review_task targeted validation has an invalid shape")
            kind = item["kind"]
            sequence = item["event_sequence"]
            declared_outcome = item["outcome"]
            notes = item["notes"]
            if (
                kind
                not in {
                    "probe",
                    "registered_check",
                    "repository_evidence",
                }
                or type(sequence) is not int
                or sequence in seen_validation_sequences
                or declared_outcome not in {"passed", "failed", "inconclusive"}
                or not isinstance(notes, str)
                or not notes.strip()
                or len(notes) > 2000
            ):
                raise ContractError("review_task targeted validation fields are invalid")
            event = self._validate_review_evidence_sequence(
                sequence,
                events_by_sequence=events_by_sequence,
                presented_sequences=presented_sequences,
                citable_sequences=citable_sequences,
                passing_validation_sequences=(passing_validation_sequences),
                source_get_diff_sequence=source_get_diff_sequence,
                mutation_sequence=mutation_sequence,
                worktree_diff_hash=summary.patch_hash,
            )
            expected_tools = {
                "probe": {"run_probe"},
                "registered_check": {"run_check"},
                "repository_evidence": {
                    "read_file",
                    "search_files",
                    "get_diff",
                },
            }[kind]
            if event.payload.get("tool") not in expected_tools:
                raise ContractError("review_task validation kind conflicts with cited tool")
            if event.payload.get("timed_out") is True:
                actual_outcome = "inconclusive"
            elif kind in {"probe", "registered_check"}:
                actual_outcome = "passed" if event.payload.get("passed") is True else "failed"
            else:
                actual_outcome = "passed"
            if declared_outcome != actual_outcome:
                raise ContractError("review_task outcome conflicts with cited trace evidence")
            if kind in {"probe", "registered_check"} and actual_outcome == "passed":
                current_validation_passed = True
            seen_validation_sequences.add(sequence)
            normalized_validation.append(
                {
                    "kind": kind,
                    "event_sequence": sequence,
                    "outcome": declared_outcome,
                    "notes": notes.strip(),
                }
            )
        if not current_validation_passed:
            raise PolicyViolation(
                "review_task needs a passing current-diff probe or registered check",
                details={
                    "schema_version": "review-citation-error-v1",
                    "stage": "review",
                    "reason": "targeted_validation_missing",
                    "citable_event_sequences": sorted(citable_sequences),
                    "passing_validation_event_sequences": sorted(passing_validation_sequences),
                    "source_get_diff_sequence": (source_get_diff_sequence),
                },
            )
        normalized_residual_risks: list[Any] = []
        if contract_review:
            if not isinstance(residual_risks, list) or len(residual_risks) > 20:
                raise ContractError("review_task residual risks have an invalid shape")
            risk_requirement_ids: set[str] = set()
            for item in residual_risks:
                if not isinstance(item, dict) or set(item) != {
                    "requirement_ids",
                    "risk",
                    "mitigation",
                }:
                    raise ContractError("review_task residual risk has an invalid shape")
                requirement_ids = item["requirement_ids"]
                risk = item["risk"]
                mitigation = item["mitigation"]
                if (
                    not isinstance(requirement_ids, list)
                    or not requirement_ids
                    or len(requirement_ids) > 20
                    or len(set(requirement_ids)) != len(requirement_ids)
                    or any(
                        not isinstance(requirement_id, str)
                        or requirement_id not in authoritative_requirements
                        for requirement_id in requirement_ids
                    )
                    or not isinstance(risk, str)
                    or not risk.strip()
                    or len(risk) > 1000
                    or not isinstance(mitigation, str)
                    or not mitigation.strip()
                    or len(mitigation) > 1000
                ):
                    raise ContractError("review_task residual risk fields are invalid")
                risk_requirement_ids.update(requirement_ids)
                normalized_residual_risks.append(
                    {
                        "requirement_ids": list(requirement_ids),
                        "risk": risk.strip(),
                        "mitigation": mitigation.strip(),
                    }
                )
            nonverified_ids = {
                item["requirement_id"]
                for item in normalized_requirements
                if item["status"] != "verified"
            }
            if not nonverified_ids.issubset(risk_requirement_ids):
                raise ContractError("every partial or unverified requirement needs a residual risk")
        else:
            if (
                not isinstance(residual_risks, list)
                or len(residual_risks) > 20
                or any(
                    not isinstance(item, str) or not item.strip() or len(item) > 1000
                    for item in residual_risks
                )
            ):
                raise ContractError("review_task residual_risks must contain bounded strings")
            normalized_residual_risks = [item.strip() for item in residual_risks]
        verified_coverage_target_ids = [
            target_id
            for target_id in authoritative_targets
            if coverage_statuses.get(target_id) == "verified"
        ]
        unresolved_coverage_target_ids = [
            target_id
            for target_id in authoritative_targets
            if coverage_statuses.get(target_id) != "verified"
        ]
        coverage_complete = bool(coverage_review and not unresolved_coverage_target_ids)
        public_review_coverage = (
            {
                "schema_version": "public-review-coverage-v1",
                "authoritative_coverage_target_ids": list(authoritative_targets),
                "verified_coverage_target_ids": (verified_coverage_target_ids),
                "unresolved_coverage_target_ids": (unresolved_coverage_target_ids),
                "coverage_complete": coverage_complete,
                "ready_for_submission": coverage_complete,
                "deterministic_correctness_claimed": False,
            }
            if coverage_review
            else None
        )
        review = {
            "schema_version": (
                "task-review-v3"
                if coverage_review
                else ("task-review-v2" if contract_review else "task-review-v1")
            ),
            "run_id": self.run_id,
            "request_artifact_id": request_artifact_id,
            "worktree_diff_hash": summary.patch_hash,
            "mutation_event_sequence": mutation_sequence,
            "source_get_diff_sequence": source_get_diff_sequence,
            "requirements": normalized_requirements,
            **(
                {
                    "coverage_targets": normalized_coverage_targets,
                    "public_review_coverage": public_review_coverage,
                }
                if coverage_review
                else {}
            ),
            "targeted_validation": normalized_validation,
            "residual_risks": normalized_residual_risks,
            "deterministic_correctness_claimed": False,
        }
        if contract_review:
            assert review_contract is not None
            review.update(
                {
                    "public_review_contract_hash": review_contract.content_hash,
                    "public_review_contract_schema_version": (review_contract.schema_version),
                    "authoritative_requirement_ids": list(authoritative_requirements),
                }
            )
        review_artifact = self.artifacts.put_json(review)
        result = {
            "schema_version": (
                "task-review-result-v3"
                if coverage_review
                else ("task-review-result-v2" if contract_review else "task-review-result-v1")
            ),
            "review_schema_version": review["schema_version"],
            "review_artifact": review_artifact.model_dump(mode="json"),
            "review_content_hash": review_artifact.content_hash,
            "review": review,
            "request_artifact_id": request_artifact_id,
            "worktree_diff_hash": summary.patch_hash,
            "mutation_event_sequence": mutation_sequence,
            "source_get_diff_sequence": source_get_diff_sequence,
            "requirement_count": len(normalized_requirements),
            **(
                {
                    "coverage_target_count": len(normalized_coverage_targets),
                    "coverage_complete": coverage_complete,
                    "verified_coverage_target_ids": (verified_coverage_target_ids),
                    "unresolved_coverage_target_ids": (unresolved_coverage_target_ids),
                    "public_review_coverage": public_review_coverage,
                }
                if coverage_review
                else {}
            ),
            "targeted_validation_count": len(normalized_validation),
            "residual_risk_count": len(residual_risks),
            "self_attestation": True,
            "deterministic_correctness_claimed": False,
        }
        if contract_review:
            assert review_contract is not None
            result["public_review_contract_hash"] = review_contract.content_hash
        review_result_limit = 24_000 if coverage_review else 12_000
        if len(canonical_json(result).encode("utf-8")) > review_result_limit:
            raise PolicyViolation(
                "review_task result cannot be presented completely",
                details={
                    "stage": "review",
                    "reason": "review_result_too_large",
                },
            )
        return result

    @staticmethod
    def _coverage_citation_error(
        *,
        reason: str,
        target: PublicReviewCoverageTarget,
        requirement_id: str,
        submitted_sequences: list[int],
        allowed_sequences: list[int],
        mutation_sequence: int,
        worktree_diff_hash: str,
        source_get_diff_sequence: int,
    ) -> CoverageCitationError:
        """Build bounded, public-only feedback for one V11 target rejection."""

        invalid_sequences = [
            sequence for sequence in submitted_sequences if sequence not in allowed_sequences
        ]
        if target.evidence_kind == "current_diff_inspection":
            required_evidence: dict[str, Any] = {
                "tool": "read_file",
                "path": target.path,
                "anchor": target.anchor,
            }
            guidance = (
                "Locate the exact public anchor if needed, then use read_file "
                "to obtain a complete current-diff result containing it. Retry "
                "with only the refreshed target-specific advertised sequences."
            )
        else:
            required_evidence = {
                "tool": "run_check",
                "check_ids": list(target.check_ids),
            }
            guidance = (
                "Run an allowed registered check for this target on the current "
                "diff, then retry with only the refreshed target-specific "
                "advertised sequences."
            )
        details = {
            "schema_version": "coverage-citation-error-v1",
            "stage": "review",
            "reason": reason,
            "coverage_target_id": target.coverage_target_id,
            "requirement_id": requirement_id,
            "submitted_event_sequences": list(submitted_sequences),
            "allowed_event_sequences": list(allowed_sequences),
            "invalid_event_sequences": invalid_sequences,
            "evidence_kind": target.evidence_kind,
            "required_evidence": required_evidence,
            "mutation_event_sequence": mutation_sequence,
            "worktree_diff_hash": worktree_diff_hash,
            "source_get_diff_sequence": source_get_diff_sequence,
            "guidance": guidance,
        }
        return CoverageCitationError(
            "review_task coverage target citation was rejected",
            details=details,
        )

    def _validate_coverage_target_evidence(
        self,
        target: PublicReviewCoverageTarget,
        event: Any,
    ) -> None:
        """Independently bind one V10 citation to its public target kind."""

        try:
            descriptor = Artifact.model_validate(event.payload.get("result_artifact"))
            if (
                event.payload.get("artifact_id") != descriptor.artifact_id
                or event.payload.get("artifact_path") != descriptor.path
            ):
                raise ValueError("descriptor identity mismatch")
            document = json.loads(
                self.artifacts.read_bytes(descriptor).decode(
                    "utf-8",
                    errors="strict",
                )
            )
        except (
            OSError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError("coverage evidence lacks a valid result artifact") from exc
        if (
            event.type != EventType.TOOL_SUCCEEDED
            or event.actor != "tool-gateway"
            or event.payload.get("status") != "succeeded"
            or not isinstance(document, dict)
            or not isinstance(event.payload.get("worktree_diff_hash"), str)
            or document.get("worktree_diff_hash") != event.payload.get("worktree_diff_hash")
        ):
            raise ContractError("coverage evidence conflicts with its current-diff result")

        if target.evidence_kind == "passing_validation":
            if (
                event.payload.get("tool") != "run_check"
                or event.payload.get("passed") is not True
                or event.payload.get("check_id") not in target.check_ids
                or document.get("check_id") != event.payload.get("check_id")
                or document.get("passed") is not event.payload.get("passed")
                or document.get("timed_out") is not event.payload.get("timed_out")
                or document.get("timed_out") is not False
                or document.get("truncated") is not False
            ):
                raise ContractError(
                    "coverage target requires a complete passing allowed validation"
                )
            return
        if event.payload.get("tool") != "read_file":
            raise ContractError("coverage target requires current-diff file inspection")
        if (
            document.get("path") != target.path
            or not isinstance(document.get("content"), str)
            or target.anchor not in document["content"]
            or document.get("truncated") is True
        ):
            raise ContractError("coverage inspection evidence does not match its path and anchor")

    @staticmethod
    def _validate_review_evidence_sequence(
        sequence: Any,
        *,
        events_by_sequence: dict[int, Any],
        presented_sequences: set[int],
        citable_sequences: set[int],
        passing_validation_sequences: set[int],
        source_get_diff_sequence: int,
        mutation_sequence: int,
        worktree_diff_hash: str,
    ):
        details = {
            "schema_version": "review-citation-error-v1",
            "stage": "review",
            "invalid_event_sequence": (sequence if type(sequence) is int else None),
            "citable_event_sequences": sorted(citable_sequences),
            "passing_validation_event_sequences": sorted(passing_validation_sequences),
            "source_get_diff_sequence": source_get_diff_sequence,
        }
        if type(sequence) is not int or sequence <= mutation_sequence:
            details["reason"] = (
                "invalid_event_sequence"
                if type(sequence) is not int
                else "evidence_precedes_current_mutation"
            )
            raise ContractError(
                "review_task evidence must follow the current mutation",
                details=details,
            )
        event = events_by_sequence.get(sequence)
        if event is None:
            details["reason"] = "evidence_event_missing"
        elif event.type != EventType.TOOL_SUCCEEDED:
            details["reason"] = "evidence_not_tool_succeeded"
        elif event.payload.get("worktree_diff_hash") != worktree_diff_hash:
            details["reason"] = "evidence_not_current_diff"
        elif sequence not in presented_sequences:
            details["reason"] = "evidence_not_presented"
        elif sequence not in citable_sequences:
            details["reason"] = "evidence_not_citable"
        else:
            return event
        if "reason" in details:
            raise ContractError(
                "review_task evidence must be a complete current-diff "
                "ToolSucceeded result in this request",
                details=details,
            )
        raise RecoveryError("review citation validation reached invalid state")

    def _get_diff(self) -> dict[str, Any]:
        summary = WorkspaceManager.diff_summary(self.workspace)
        return {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
        }
