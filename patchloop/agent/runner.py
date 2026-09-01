"""Durable single-agent loop with deterministic evaluation and recovery."""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from patchloop.agent.batch_image_authority import (
    IMAGE_ADMISSION_CONTRACT,
    BatchImageAuthorization,
    validate_row_batch_image,
)
from patchloop.agent.batch_image_authority import (
    POLICY_VERSION as BATCH_IMAGE_POLICY_VERSION,
)
from patchloop.agent.completion_loop_successor import (
    ProviderTerminalAttribution,
    project_provider_terminal_attribution,
)
from patchloop.agent.context import BuiltContext, build_context_with_evidence
from patchloop.agent.investigation import load_inspection_records
from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION,
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
    assemble_lean_harness_request,
    load_lean_harness_dependencies,
    recover_plan_gate_readiness_pins,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.model import (
    SYSTEM_PROMPT_V1,
    SYSTEM_PROMPT_V2,
    SYSTEM_PROMPT_V3,
    SYSTEM_PROMPT_V4,
    SYSTEM_PROMPT_V5,
    SYSTEM_PROMPT_V6,
    SYSTEM_PROMPT_V7,
    SYSTEM_PROMPT_V8,
    MockModelAdapter,
    ModelAdapter,
    ModelTurnError,
    OpenAIResponsesAdapter,
    ReplayModelAdapter,
)
from patchloop.agent.phases import diff_bound_evidence, validate_transition
from patchloop.agent.provider_count_accounting import (
    assert_input_token_count_recoverable,
    counted_request_with_receipts,
    project_input_token_count_attempts,
)
from patchloop.agent.provider_schema_adapter import StrictOpenAIResponsesAdapter
from patchloop.agent.provider_schema_admission import (
    ProviderToolSchemaError,
    normalize_strict_read_arguments,
)
from patchloop.agent.review import (
    build_public_review_base_provenance,
    validate_public_review_base_provenance_document,
)
from patchloop.agent.tools import (
    TOOL_SCHEMAS_V1,
    TOOL_SCHEMAS_V2,
    TOOL_SCHEMAS_V3,
    TOOL_SCHEMAS_V4,
    TOOL_SCHEMAS_V5,
    TOOL_SCHEMAS_V6,
    TOOL_SCHEMAS_V7,
    TOOL_SCHEMAS_V8,
    TOOL_SCHEMAS_V9,
    TOOL_SCHEMAS_V10,
    TOOL_SCHEMAS_V11,
    TOOL_SCHEMAS_V12,
    TOOL_SCHEMAS_V13,
    TOOL_SCHEMAS_V14,
    TOOL_SCHEMAS_V15,
    TOOL_SCHEMAS_V16,
    TOOL_SCHEMAS_V17,
    TOOL_SCHEMAS_V18,
    TOOL_SCHEMAS_V19,
    TOOL_SCHEMAS_V20,
    TOOL_SCHEMAS_V21,
    TOOL_SCHEMAS_V22,
    TOOL_SCHEMAS_V23,
    TOOL_SCHEMAS_V24,
    TOOL_SCHEMAS_V25,
    TOOL_SCHEMAS_V26,
    TOOL_SCHEMAS_V27,
    TOOL_SCHEMAS_V28,
    TOOL_SCHEMAS_V29,
    ToolGateway,
)
from patchloop.agent.workflow_r21_reliability_successor import (
    GENERATION_INCOMPLETE_RECOVERY_POLICY,
    project_generation_incomplete_recovery,
    resolve_anchored_read,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SelfDirectedExplorationState,
    WorkflowDecisionV4,
    project_episode_investigation_target_hashes,
    validate_exploration_stop,
    validate_investigation_action,
)
from patchloop.agent.workflow_successor import PROTOCOL_RECOVERY_POLICY
from patchloop.agent.workflow_successor_v2 import project_active_work_state
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    AC_FIXED_BUNDLE_ALL_COST_EXPERIMENT_IDS,
    AC_FIXED_BUNDLE_ALL_EXPERIMENT_IDS,
    AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_IDS,
    CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID,
    CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID,
    CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
    GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID,
    Artifact,
    Budget,
    Checkpoint,
    DatasetRole,
    EvaluatorV2EvaluationReceipt,
    EventType,
    ExperimentPurpose,
    ExperimentRunContext,
    MemoryCondition,
    Phase,
    PublicTask,
    RunManifest,
    RunOutcomeKind,
    RunResult,
    RunStatus,
    TaskPackage,
    ToolResult,
    Usage,
    Verdicts,
    build_evidence_artifact_ref,
)
from patchloop.errors import (
    ContractError,
    HarnessAdmissionError,
    InjectedFault,
    ModelActionContractRepeatedError,
    ModelGenerationBudgetError,
    ModelGenerationIncompleteRepeatedError,
    RecoveryError,
    ReviewCorrectionLimitError,
    RunOwnershipConflict,
    SelfDirectedExplorationExhaustedError,
    SubmissionProtocolError,
)
from patchloop.evals.failures import classify_failure
from patchloop.memory import retrieve_memory
from patchloop.memory.fixed_bundle import (
    D110_INDEX_CONTENT_HASH,
    D110_INDEX_VERSION,
    FIXED_BUNDLE_POLICY_VERSION,
    FixedMemoryDelivery,
    FixedMemoryRequestEvidence,
    build_fixed_memory_delivery,
    validate_fixed_memory_request_artifact,
)
from patchloop.repository import WorkspaceManager
from patchloop.runtime import (
    build_manifest,
    calculate_model_cost,
    repository_root,
    runtime_root,
)
from patchloop.sandbox import DockerSandbox, LocalSandbox, TimeoutOnceSandbox
from patchloop.state import RunOwnershipCoordinator, StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import (
    canonical_json,
    ensure_within,
    safe_relative_path,
    sha256_bytes,
    sha256_json,
    sha256_text,
    utc_now,
)
from patchloop.verifier import EvaluationEngine
from patchloop.verifier.receipt import (
    EvaluatorV2QualificationAuthority,
    issue_evaluator_v2_evaluation_receipt,
    validate_evaluator_v2_manifest_authority,
    validate_persisted_evaluator_v2_evaluation_receipt,
)

_LIVE_AUTHORIZATION_GUARD = object()
_BATCH_EXECUTION_AUTHORIZATION_GUARD = object()
_ROW_EXECUTION_AUTHORIZATION_GUARD = object()
_CAMPAIGN_COST_RESERVATION_GUARD = object()
_CAMPAIGN_COST_CONTROL_SCHEMA = "campaign-cost-control-evidence-v1"
_CAMPAIGN_COST_POLICY_SCHEMA = "campaign-list-price-accrual-cap-v1"
_CAMPAIGN_JOURNAL_EVENT_SCHEMA = "experiment-journal-event-v1"
_CAMPAIGN_RESERVATION_CONSUMPTION_SCHEMA = "campaign-cost-reservation-consumption-v1"
_AC_ROW_START_CONSUMPTION_MARKER_SCHEMA = "ac-fixed-bundle-row-start-consumption-marker-v1"
_MAX_RECOVERABLE_SUBMISSION_REJECTIONS = 2
_MAX_RECOVERABLE_REVIEW_REJECTIONS = 2
_EVALUATION_RECEIPT_SCHEMA = "evaluation-receipt-v1"
_EXACT_REQUEST_GENERATION_BLOCK_SCHEMA = "model-generation-block-v1"
_COUNTER_GENERATION_BLOCK_SCHEMA = "model-generation-block-v2"
_OPTIONAL_COUNTER_GENERATION_BLOCK_SCHEMA = "model-generation-block-v3"
_SPLIT_TOKEN_GENERATION_BLOCK_SCHEMA = "model-generation-block-v4"
_SPLIT_TOKEN_BUDGET_SCHEMA = "cumulative-split-v1"
_SPLIT_TOKEN_DIMENSION_ORDER = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
_CONDITION_NEUTRAL_COMPARISON_RUNTIME_EVIDENCE_SCHEMA = (
    "condition-neutral-comparison-runtime-evidence-v1"
)
_CONDITION_NEUTRAL_COMPARISON_RUNTIME_EVIDENCE_SCHEMA_V2 = (
    "condition-neutral-comparison-runtime-evidence-v2"
)
_AC_FIXED_BUNDLE_RUNTIME_EVIDENCE_SCHEMA = "ac-fixed-bundle-runtime-evidence-v1"
_AC_FIXED_BUNDLE_ROW_ORDER = {
    ("moto-query-scanned-count", MemoryCondition.NO_MEMORY): 1,
    ("moto-query-scanned-count", MemoryCondition.STRUCTURED): 2,
    ("babel-strict-grouped-decimal-trailing-zeroes", MemoryCondition.STRUCTURED): 3,
    ("babel-strict-grouped-decimal-trailing-zeroes", MemoryCondition.NO_MEMORY): 4,
}
_CONDITION_NEUTRAL_FULL_SCHEDULE_COST_CONTROL_SCHEMA = (
    "campaign-full-schedule-cost-control-evidence-v1"
)
_CONDITION_NEUTRAL_FULL_SCHEDULE_COST_POLICY_SCHEMA = "campaign-list-price-full-schedule-reserve-v1"
_AC_FIXED_BUNDLE_FULL_SCHEDULE_COST_CONTROL_SCHEMA = (
    "ac-fixed-bundle-full-schedule-cost-control-evidence-v1"
)
_AC_FIXED_BUNDLE_FULL_SCHEDULE_COST_POLICY_SCHEMA = "ac-fixed-bundle-full-schedule-reserve-v1"
_AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY_SCHEMA = (
    "ac-fixed-bundle-split-token-full-schedule-reserve-v1"
)
_CONDITION_NEUTRAL_NO_MEMORY_ROW_ORDER = {
    ("pyfakefs-makedirs-parent-traversal", 1): 1,
    ("pyfakefs-makedirs-parent-traversal", 2): 2,
    ("anyio-interrupt-runner-cleanup", 1): 3,
    ("hf-hub-xet-endpoint-propagation", 1): 4,
    ("pdm-ignore-active-venv-resolution", 1): 5,
    ("hf-hub-xet-endpoint-propagation", 2): 6,
    ("anyio-interrupt-runner-cleanup", 2): 7,
    ("loguru-invalid-format-feedback", 1): 8,
    ("loguru-invalid-format-feedback", 2): 9,
    ("tox-cross-section-empty-substitution", 2): 10,
    ("tox-cross-section-empty-substitution", 1): 11,
    ("pdm-ignore-active-venv-resolution", 2): 12,
}
_CONDITION_NEUTRAL_COMPARISON_CALL_GUARD_POLICY = "model-tool-observability-only-v1"
_COUNTER_GENERATION_BLOCK_REASONS = frozenset(
    {
        "model_call_budget_exhausted",
        "tool_call_budget_exhausted",
        "wall_clock_budget_exhausted",
    }
)


def _exact_typed_equal(actual: object, expected: object) -> bool:
    """Compare persisted machine values without Python's bool/int coercion."""

    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        if not isinstance(expected, dict) or set(actual) != set(expected):
            return False
        return all(_exact_typed_equal(actual[key], expected[key]) for key in actual)
    if isinstance(actual, list):
        if not isinstance(expected, list) or len(actual) != len(expected):
            return False
        return all(
            _exact_typed_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return actual == expected


@dataclass(frozen=True)
class LiveExecutionAuthorization:
    """Ephemeral capability issued only after an approved live preflight."""

    execution_hash: str
    plan_path: str
    plan_hash: str
    _guard: object


@dataclass
class _BatchExecutionAuthorizationState:
    next_order: int = 1
    image_admission_attempted: bool = False
    image_authorization: object | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class _RowExecutionAuthorizationState:
    consumed: bool = False
    provider_dispatch_started: bool = False
    provider_dispatch_rehearsed: bool = False
    # R24 integration begin: count-rehearsal-state
    input_count_rehearsed: bool = False
    # R24 integration end: count-rehearsal-state
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass(frozen=True)
class BatchExecutionAuthorization:
    """Batch-scoped authority from one complete candidate verification."""

    authority_kind: str
    execution_hash: str
    plan_hash: str
    runtime_build_hash: str
    schedule_hash: str
    cost_control_hash: str
    manifest_hashes: tuple[str, ...]
    _state: _BatchExecutionAuthorizationState
    _guard: object
    image_admission_policy: str | None = None
    image_admission_image: str | None = None
    # R24 integration begin: batch-request-policy
    provider_request_policy: str | None = None
    # R24 integration end: batch-request-policy


@dataclass(frozen=True)
class RowExecutionAuthorization:
    """Typed one-use capability for one exact prevalidated schedule row."""

    authority_kind: str
    execution_hash: str
    plan_hash: str
    schedule_order: int
    schedule_row_id: str
    run_id: str
    manifest_hash: str
    _state: _RowExecutionAuthorizationState
    _guard: object
    image_admission_policy: str | None = None
    _batch_state: _BatchExecutionAuthorizationState | None = None
    # R24 integration begin: row-request-policy
    provider_request_policy: str | None = None
    # R24 integration end: row-request-policy


@dataclass(frozen=True)
class CampaignCostReservationAuthorization:
    """One-use D-087 capability for one exact scheduled paid run."""

    execution_hash: str
    campaign_cost_control_hash: str
    schedule_row_id: str
    run_id: str
    journal_path: str
    journal_hash: str
    reservation_event_hash: str
    _guard: object


def issue_live_execution_authorization(
    execution_hash: str,
    *,
    root: str | Path | None = None,
) -> LiveExecutionAuthorization:
    """Issue a capability only when the approved execution plan is durable."""

    if re.fullmatch(r"sha256:[0-9a-f]{64}", execution_hash) is None:
        raise ContractError("live execution hash must be a SHA-256 identity")
    plan_path = (
        (Path(root) if root is not None else runtime_root())
        / "experiments"
        / "plans"
        / f"{execution_hash.removeprefix('sha256:')}.json"
    )
    try:
        plan_bytes = plan_path.read_bytes()
        plan = json.loads(plan_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(
            "live execution capability requires a persisted approved execution plan"
        ) from exc
    approval = plan.get("approval") if isinstance(plan, dict) else None
    plan_schema = plan.get("schema_version") if isinstance(plan, dict) else None
    from patchloop.evals.live_verifier_registry import live_verifier_registry

    registry_decision = (
        live_verifier_registry().validate_authorization_plan(plan)
        if isinstance(plan, dict)
        else None
    )
    plan_schema_supported = bool(
        registry_decision is not None
        and (
            registry_decision.accepted
            if registry_decision.handled
            else plan_schema in {"experiment-execution-plan-v1", "experiment-execution-plan-v2"}
        )
    )
    if (
        not isinstance(plan, dict)
        or not plan_schema_supported
        or plan.get("ready") is not True
        or plan.get("blockers") != []
        or plan.get("execution_hash") != execution_hash
        or not isinstance(approval, dict)
        or approval.get("invocation_approve_live_cost") is not True
        or approval.get("invocation_approved_execution_hash") != execution_hash
        or approval.get("matches_execution_hash") is not True
    ):
        raise ContractError("persisted execution plan does not authorize this live execution hash")
    return LiveExecutionAuthorization(
        execution_hash=execution_hash,
        plan_path=str(plan_path),
        plan_hash=sha256_bytes(plan_bytes),
        _guard=_LIVE_AUTHORIZATION_GUARD,
    )


def issue_batch_execution_authorization(
    *,
    authority_kind: str,
    execution_hash: str,
    plan_hash: str,
    runtime_build_hash: str,
    schedule_hash: str,
    cost_control_hash: str,
    manifests: tuple[RunManifest, ...],
    live_authorization: LiveExecutionAuthorization | None = None,
    image_admission_policy: str | None = None,
    image_admission_image: str | None = None,
    # R24 integration begin: issuer-request-policy
    provider_request_policy: str | None = None,
    # R24 integration end: issuer-request-policy
) -> BatchExecutionAuthorization:
    """Issue one batch capability after all row manifests were prevalidated."""

    identities = (
        execution_hash,
        plan_hash,
        runtime_build_hash,
        schedule_hash,
        cost_control_hash,
    )
    if authority_kind not in {"live", "rehearsal"} or any(
        re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None for value in identities
    ):
        raise HarnessAdmissionError("batch execution authorization identity is invalid")
    if image_admission_policy not in {None, BATCH_IMAGE_POLICY_VERSION}:
        raise HarnessAdmissionError("batch image admission policy is unsupported")
    if (image_admission_policy is None and image_admission_image is not None) or (
        image_admission_policy is not None
        and (
            not isinstance(image_admission_image, str)
            or re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image_admission_image) is None
        )
    ):
        raise HarnessAdmissionError("batch image reference is invalid")
    if not manifests:
        raise HarnessAdmissionError("batch execution authorization has no manifests")
    # R24 integration begin: validate-request-policy
    from patchloop.agent.provider_request_gate import REQUEST_CONTRACT, REQUEST_POLICY

    if provider_request_policy not in {None, REQUEST_POLICY}:
        raise HarnessAdmissionError("batch provider-request policy is unsupported")
    if provider_request_policy is not None and any(
        (m.tool_schema_version, m.context_policy_version)
        not in {
            ("v26", "phase-evidence-v35"),
            ("v28", "phase-evidence-v37"),
            ("v29", "phase-evidence-v38"),
        }
        for m in manifests
    ):
        raise HarnessAdmissionError("batch provider-request runtime differs")
    # R24 integration end: validate-request-policy
    for order, manifest in enumerate(manifests, start=1):
        experiment = manifest.experiment
        if (
            experiment is None
            or experiment.execution_hash != execution_hash
            or experiment.schedule_order != order
        ):
            raise HarnessAdmissionError("batch manifest order or execution identity differs")
    if authority_kind == "live":
        try:
            unchanged = bool(
                live_authorization is not None
                and live_authorization._guard is _LIVE_AUTHORIZATION_GUARD
                and live_authorization.execution_hash == execution_hash
                and live_authorization.plan_hash == plan_hash
                and sha256_bytes(Path(live_authorization.plan_path).read_bytes()) == plan_hash
            )
        except OSError:
            unchanged = False
        if not unchanged:
            raise HarnessAdmissionError("live batch capability lacks its unchanged approved plan")
        assert live_authorization is not None
        approved_plan = json.loads(Path(live_authorization.plan_path).read_bytes())
        # R24 integration begin: bind-request-policy
        if not _exact_typed_equal(
            approved_plan.get("provider_request_contract"),
            REQUEST_CONTRACT if provider_request_policy is not None else None,
        ):
            raise HarnessAdmissionError("batch provider-request policy differs from approval")
        # R24 integration end: bind-request-policy
        expected_image_contract = (
            IMAGE_ADMISSION_CONTRACT if image_admission_policy is not None else None
        )
        if not _exact_typed_equal(
            approved_plan.get("image_admission_contract"), expected_image_contract
        ):
            raise HarnessAdmissionError("batch image policy differs from its approved plan")
        if image_admission_policy is not None:
            bindings = approved_plan.get("task_bindings")
            if not (
                isinstance(bindings, list)
                and len(bindings) == 1
                and isinstance(bindings[0], dict)
                and bindings[0].get("evaluator_image") == image_admission_image
                and bindings[0].get("evaluator_image_digest")
                == image_admission_image.rsplit("@", 1)[1]
            ):
                raise HarnessAdmissionError("batch image reference differs from its approved plan")
    elif live_authorization is not None:
        raise HarnessAdmissionError("rehearsal batch cannot carry live execution authority")
    return BatchExecutionAuthorization(
        authority_kind=authority_kind,
        execution_hash=execution_hash,
        plan_hash=plan_hash,
        runtime_build_hash=runtime_build_hash,
        schedule_hash=schedule_hash,
        cost_control_hash=cost_control_hash,
        manifest_hashes=tuple(
            sha256_json(manifest.model_dump(mode="json")) for manifest in manifests
        ),
        _state=_BatchExecutionAuthorizationState(),
        _guard=_BATCH_EXECUTION_AUTHORIZATION_GUARD,
        image_admission_policy=image_admission_policy,
        image_admission_image=image_admission_image,
        # R24 integration begin: issue-batch-request-policy
        provider_request_policy=provider_request_policy,
        # R24 integration end: issue-batch-request-policy
    )


def issue_row_execution_authorization(
    batch: BatchExecutionAuthorization,
    manifest: RunManifest,
    *,
    active_schedule_order: int,
) -> RowExecutionAuthorization:
    """Derive one exact, sequential, one-use row capability from a batch."""

    experiment = manifest.experiment
    manifest_hash = sha256_json(manifest.model_dump(mode="json"))
    if (
        batch._guard is not _BATCH_EXECUTION_AUTHORIZATION_GUARD
        or experiment is None
        or experiment.execution_hash != batch.execution_hash
        or experiment.schedule_order != active_schedule_order
        or active_schedule_order < 1
        or active_schedule_order > len(batch.manifest_hashes)
        or manifest_hash != batch.manifest_hashes[active_schedule_order - 1]
    ):
        raise HarnessAdmissionError("row capability does not match the prevalidated batch")
    with batch._state.lock:
        if batch._state.next_order != active_schedule_order:
            raise HarnessAdmissionError("row capability order was already issued or skipped")
        batch._state.next_order += 1
    return RowExecutionAuthorization(
        authority_kind=batch.authority_kind,
        execution_hash=batch.execution_hash,
        plan_hash=batch.plan_hash,
        schedule_order=active_schedule_order,
        schedule_row_id=experiment.schedule_row_id,
        run_id=manifest.run_id,
        manifest_hash=manifest_hash,
        _state=_RowExecutionAuthorizationState(),
        _guard=_ROW_EXECUTION_AUTHORIZATION_GUARD,
        image_admission_policy=batch.image_admission_policy,
        _batch_state=batch._state,
        # R24 integration begin: issue-row-request-policy
        provider_request_policy=batch.provider_request_policy,
        # R24 integration end: issue-row-request-policy
    )


def batch_execution_authorization_receipt(
    authorization: BatchExecutionAuthorization,
) -> dict[str, Any]:
    """Project bounded batch state for post-row continuation admission."""

    if authorization._guard is not _BATCH_EXECUTION_AUTHORIZATION_GUARD:
        raise HarnessAdmissionError("batch execution capability receipt is invalid")
    with authorization._state.lock:
        body = {
            "schema_version": "batch-execution-capability-receipt-v1",
            "authority_kind": authorization.authority_kind,
            "execution_hash": authorization.execution_hash,
            "plan_hash": authorization.plan_hash,
            "runtime_build_hash": authorization.runtime_build_hash,
            "schedule_hash": authorization.schedule_hash,
            "cost_control_hash": authorization.cost_control_hash,
            "manifest_count": len(authorization.manifest_hashes),
            "next_order": authorization._state.next_order,
        }
    return {**body, "content_hash": sha256_json(body)}


def row_execution_authorization_receipt(
    authorization: RowExecutionAuthorization,
) -> dict[str, Any]:
    """Project one row capability's exact one-use and provider-boundary state."""

    if authorization._guard is not _ROW_EXECUTION_AUTHORIZATION_GUARD:
        raise HarnessAdmissionError("row execution capability receipt is invalid")
    with authorization._state.lock:
        body = {
            "schema_version": "row-execution-capability-receipt-v1",
            "authority_kind": authorization.authority_kind,
            "execution_hash": authorization.execution_hash,
            "plan_hash": authorization.plan_hash,
            "schedule_order": authorization.schedule_order,
            "schedule_row_id": authorization.schedule_row_id,
            "run_id": authorization.run_id,
            "manifest_hash": authorization.manifest_hash,
            "consumed": authorization._state.consumed,
            "provider_dispatch_started": authorization._state.provider_dispatch_started,
            "provider_dispatch_rehearsed": authorization._state.provider_dispatch_rehearsed,
        }
        # R24 integration begin: request-policy-receipt
        if authorization.provider_request_policy is not None:
            body["provider_request_policy"] = authorization.provider_request_policy
            body["input_count_rehearsed"] = authorization._state.input_count_rehearsed
        # R24 integration end: request-policy-receipt
    return {**body, "content_hash": sha256_json(body)}


def _consume_row_execution_authorization(
    manifest: RunManifest,
    authorization: RowExecutionAuthorization,
    *,
    expected_authority_kind: str,
    live_authorization: LiveExecutionAuthorization | None,
) -> None:
    experiment = manifest.experiment
    valid = bool(
        authorization._guard is _ROW_EXECUTION_AUTHORIZATION_GUARD
        and authorization.authority_kind == expected_authority_kind
        and experiment is not None
        and authorization.execution_hash == experiment.execution_hash
        and authorization.schedule_order == experiment.schedule_order
        and authorization.schedule_row_id == experiment.schedule_row_id
        and authorization.run_id == manifest.run_id
        and authorization.manifest_hash == sha256_json(manifest.model_dump(mode="json"))
    )
    if expected_authority_kind == "live":
        valid = bool(
            valid
            and live_authorization is not None
            and live_authorization._guard is _LIVE_AUTHORIZATION_GUARD
            and live_authorization.execution_hash == authorization.execution_hash
            and live_authorization.plan_hash == authorization.plan_hash
        )
        try:
            valid = bool(
                valid
                and live_authorization is not None
                and sha256_bytes(Path(live_authorization.plan_path).read_bytes())
                == authorization.plan_hash
            )
        except OSError:
            valid = False
    elif live_authorization is not None:
        valid = False
    if not valid:
        raise HarnessAdmissionError("row execution capability is invalid")
    with authorization._state.lock:
        if authorization._state.consumed:
            raise HarnessAdmissionError("row execution capability was already consumed")
        authorization._state.consumed = True


def _provider_dispatch_boundary(
    manifest: RunManifest,
    authorization: RowExecutionAuthorization,
    *,
    stop_before_dispatch: bool,
) -> dict[str, Any] | None:
    """Shared last contract gate immediately before the provider adapter call."""

    experiment = manifest.experiment
    expected_kind = "rehearsal" if stop_before_dispatch else "live"
    valid = bool(
        authorization._guard is _ROW_EXECUTION_AUTHORIZATION_GUARD
        and authorization.authority_kind == expected_kind
        and experiment is not None
        and authorization.execution_hash == experiment.execution_hash
        and authorization.schedule_order == experiment.schedule_order
        and authorization.schedule_row_id == experiment.schedule_row_id
        and authorization.run_id == manifest.run_id
        and authorization.manifest_hash == sha256_json(manifest.model_dump(mode="json"))
    )
    if not valid:
        raise HarnessAdmissionError("provider dispatch capability is invalid")
    with authorization._state.lock:
        if not authorization._state.consumed:
            raise HarnessAdmissionError("provider dispatch precedes row admission")
        if stop_before_dispatch:
            if (
                authorization._state.provider_dispatch_rehearsed
                or authorization._state.provider_dispatch_started
            ):
                raise HarnessAdmissionError("provider dispatch boundary was already visited")
            authorization._state.provider_dispatch_rehearsed = True
        elif authorization._state.provider_dispatch_rehearsed:
            raise HarnessAdmissionError("a rehearsal capability cannot enter live dispatch")
        else:
            authorization._state.provider_dispatch_started = True
    if not stop_before_dispatch:
        return None
    return {
        "stage": "provider-dispatch-boundary",
        "provider_dispatch_blocked": True,
        "execution_hash": experiment.execution_hash,
        "schedule_order": experiment.schedule_order,
        "schedule_row_id": experiment.schedule_row_id,
        "run_id": manifest.run_id,
        "manifest_hash": authorization.manifest_hash,
    }


def _provider_input_count_boundary(
    manifest: RunManifest,
    authorization: RowExecutionAuthorization | None,
) -> None:
    """Validate live count authority without falsely marking generation as started."""
    if type(authorization) is not RowExecutionAuthorization:
        raise HarnessAdmissionError("provider input count lacks a live row capability")
    receipt = row_execution_authorization_receipt(authorization)
    experiment = manifest.experiment
    if (
        experiment is None
        or receipt["authority_kind"] != "live"
        or receipt["execution_hash"] != experiment.execution_hash
        or receipt["schedule_order"] != experiment.schedule_order
        or receipt["schedule_row_id"] != experiment.schedule_row_id
        or receipt["run_id"] != manifest.run_id
        or receipt["manifest_hash"] != sha256_json(manifest.model_dump(mode="json"))
        or not receipt["consumed"]
        or receipt["provider_dispatch_rehearsed"]
    ):
        raise HarnessAdmissionError("provider input-count capability is invalid")


def issue_campaign_cost_reservation_authorization(
    manifest: RunManifest,
    live_authorization: LiveExecutionAuthorization,
    *,
    journal_path: str | Path,
    reservation_event_hash: str,
) -> CampaignCostReservationAuthorization:
    """Issue one D-087 paid-run capability from an fsynced journal prefix."""

    AgentRunner._require_live_authorization(manifest, live_authorization)
    if not _is_d087_paid_manifest(manifest):
        raise ContractError("campaign cost reservation capabilities are reserved for D-087")
    assert manifest.experiment is not None
    plan = _load_live_execution_plan(live_authorization)
    cost_control = plan.get("campaign_cost_control")
    expected_journal_path = plan.get("journal_path")
    resolved_journal_path, journal_root = _d087_journal_identity(
        expected_journal_path,
        journal_path,
    )
    if not isinstance(cost_control, dict):
        raise ContractError(
            "campaign reservation journal does not match the approved execution plan"
        )
    consumption_store = StateStore(journal_root / "state.sqlite3")
    consumed_rows = consumption_store.list_d087_reservation_consumptions(
        live_authorization.execution_hash
    )
    journal_hash = _validate_campaign_reservation_journal(
        resolved_journal_path,
        cost_control=cost_control,
        execution_hash=live_authorization.execution_hash,
        campaign_cost_control_hash=(manifest.experiment.campaign_cost_control_hash),
        schedule_row_id=manifest.experiment.schedule_row_id,
        run_id=manifest.run_id,
        reservation_event_hash=reservation_event_hash,
        run_root=journal_root,
        consumed_rows=consumed_rows,
    )
    authorization = CampaignCostReservationAuthorization(
        execution_hash=live_authorization.execution_hash,
        campaign_cost_control_hash=(manifest.experiment.campaign_cost_control_hash),
        schedule_row_id=manifest.experiment.schedule_row_id,
        run_id=manifest.run_id,
        journal_path=str(resolved_journal_path),
        journal_hash=journal_hash,
        reservation_event_hash=reservation_event_hash,
        _guard=_CAMPAIGN_COST_RESERVATION_GUARD,
    )
    if _campaign_reservation_consumption_path(authorization).exists():
        raise ContractError("campaign cost reservation was already consumed")
    if any(row["schedule_row_id"] == authorization.schedule_row_id for row in consumed_rows):
        raise ContractError("campaign cost reservation was already consumed")
    return authorization


def _is_d087_paid_manifest(manifest: RunManifest | None) -> bool:
    return bool(
        manifest is not None
        and manifest.model.provider == "openai"
        and manifest.experiment is not None
        and manifest.experiment.experiment_id
        == CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID
    )


def _load_live_execution_plan(
    authorization: LiveExecutionAuthorization,
) -> dict[str, Any]:
    try:
        raw = Path(authorization.plan_path).read_bytes()
        if sha256_bytes(raw) != authorization.plan_hash:
            raise ValueError("approved plan hash changed")
        plan = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError("approved live execution plan is unavailable") from exc
    if not isinstance(plan, dict):
        raise ContractError("approved live execution plan must be an object")
    return plan


def _d087_journal_identity(
    expected_path: Any,
    supplied_path: str | Path,
) -> tuple[Path, Path]:
    """Require the exact canonical D-087 journal path and return its root."""

    if not isinstance(expected_path, str):
        raise ContractError("approved D-087 plan has no journal path")
    supplied_text = str(supplied_path)
    expected = Path(expected_path)
    supplied = Path(supplied_text)
    expected_resolved = expected.resolve(strict=False)
    supplied_resolved = supplied.resolve(strict=False)
    if not (
        expected.is_absolute()
        and supplied.is_absolute()
        and expected_path == str(expected_resolved)
        and supplied_text == expected_path
        and supplied_text == str(supplied_resolved)
        and supplied_resolved.name
        == f"{CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID}.jsonl"
        and supplied_resolved.parent.name == "journals"
        and supplied_resolved.parent.parent.name == "experiments"
    ):
        raise ContractError("D-087 journal path must be the exact canonical approved path")
    return supplied_resolved, supplied_resolved.parents[2]


def _campaign_reservation_consumption_path(
    authorization: CampaignCostReservationAuthorization,
) -> Path:
    journal_path = Path(authorization.journal_path)
    digest = authorization.reservation_event_hash.removeprefix("sha256:")
    # Keep the marker next to the journal with a compact name.  The full
    # digest still supplies collision resistance while avoiding Windows'
    # legacy path-length boundary in deeply nested test/runtime roots.
    return journal_path.parent / f".{digest}.consumed"


def _ac_row_start_consumption_path(
    *,
    journal_path: str | Path,
    execution_hash: str,
    schedule_row_id: str,
) -> Path:
    claim_key = sha256_text(
        canonical_json(
            {
                "execution_hash": execution_hash,
                "schedule_row_id": schedule_row_id,
            }
        )
    ).removeprefix("sha256:")
    return Path(journal_path).parent / f".{claim_key}.ac-row-consumed"


def _write_ac_row_start_consumption_marker(
    path: Path,
    marker: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json(marker) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ContractError("A/C row start was already consumed") from exc


def _valid_sha256_identity(value: Any) -> bool:
    return bool(isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None)


def _validate_campaign_reservation_journal(
    path: Path,
    *,
    cost_control: dict[str, Any],
    execution_hash: str,
    campaign_cost_control_hash: str,
    schedule_row_id: str,
    run_id: str,
    reservation_event_hash: str,
    run_root: Path,
    consumed_rows: list[dict[str, str]],
) -> str:
    """Validate the full D-087 cost state and its exact latest reservation."""

    descriptor = cost_control.get("descriptor")
    control_hash = cost_control.get("content_hash")
    if not (
        cost_control.get("schema_version") == _CAMPAIGN_COST_CONTROL_SCHEMA
        and isinstance(descriptor, dict)
        and descriptor.get("schema_version") == _CAMPAIGN_COST_POLICY_SCHEMA
        and _valid_sha256_identity(control_hash)
        and sha256_text(canonical_json(descriptor)) == control_hash
        and control_hash == campaign_cost_control_hash
        and _valid_sha256_identity(execution_hash)
        and _valid_sha256_identity(schedule_row_id)
        and _valid_sha256_identity(reservation_event_hash)
        and isinstance(run_id, str)
        and bool(run_id)
    ):
        raise ContractError("invalid D-087 campaign reservation identity")
    cap_nanos = descriptor.get("hard_cap_nanos")
    reserve_nanos = descriptor.get("per_run_reserve_nanos")
    if (
        type(cap_nanos) is not int
        or cap_nanos <= 0
        or type(reserve_nanos) is not int
        or reserve_nanos <= 0
    ):
        raise ContractError("invalid D-087 campaign reservation policy")
    try:
        raw = path.read_bytes()
        if not raw or not raw.endswith(b"\n"):
            raise ValueError("campaign journal is not newline-terminated")
        events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError("invalid D-087 campaign reservation journal") from exc

    previous_hash: str | None = None
    accrued_nanos = 0
    stage = "before_campaign"
    active_row_id: str | None = None
    active_run_id: str | None = None
    active_usage_evidence: dict[str, Any] | None = None
    active_usage_evidence_hash: str | None = None
    active_usage_reconciliation_passed: bool | None = None
    reserved_rows: set[str] = set()
    reservation_events: dict[str, dict[str, str]] = {}
    latest_reservation: dict[str, Any] | None = None
    spend_halted = False
    for sequence, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            raise ContractError("campaign journal event must be an object")
        event_hash = event.get("event_hash")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        if not (
            set(event)
            == {
                "schema_version",
                "sequence",
                "event_type",
                "recorded_at",
                "previous_event_hash",
                "payload",
                "event_hash",
            }
            and event.get("schema_version") == _CAMPAIGN_JOURNAL_EVENT_SCHEMA
            and type(event.get("sequence")) is int
            and event.get("sequence") == sequence
            and event.get("previous_event_hash") == previous_hash
            and isinstance(event.get("recorded_at"), str)
            and bool(event.get("recorded_at"))
            and _valid_sha256_identity(event_hash)
            and sha256_text(canonical_json(body)) == event_hash
            and isinstance(event.get("payload"), dict)
        ):
            raise ContractError("campaign reservation journal hash chain mismatch")
        previous_hash = event_hash
        event_type = event["event_type"]
        payload = event["payload"]

        if event_type == "CampaignStarted":
            if not (
                sequence == 1
                and stage == "before_campaign"
                and payload.get("campaign_cost_control_hash") == control_hash
                and payload.get("execution_hash") == execution_hash
            ):
                raise ContractError("invalid D-087 campaign journal start")
            stage = "idle"
            continue
        if stage == "before_campaign":
            raise ContractError("D-087 campaign journal has no start event")

        if event_type == "RunCostReserved":
            row_id = payload.get("schedule_row_id")
            reserved_run_id = payload.get("run_id")
            if not (
                stage == "idle"
                and not spend_halted
                and isinstance(row_id, str)
                and row_id not in reserved_rows
                and isinstance(reserved_run_id, str)
                and bool(reserved_run_id)
                and payload.get("campaign_cost_control_hash") == control_hash
                and payload.get("cap_nanos") == cap_nanos
                and payload.get("reserve_nanos") == reserve_nanos
                and payload.get("accrued_cost_nanos_before") == accrued_nanos
                and payload.get("held_reserve_nanos_after") == reserve_nanos
                and accrued_nanos + reserve_nanos <= cap_nanos
            ):
                raise ContractError("invalid D-087 campaign cost reservation")
            active_row_id = row_id
            active_run_id = reserved_run_id
            reserved_rows.add(row_id)
            latest_reservation = event
            reservation_events[event_hash] = {
                "schedule_row_id": row_id,
                "run_id": reserved_run_id,
                "control_hash": control_hash,
            }
            stage = "reserved"
            continue
        if event_type == "RunStarted":
            if not (
                stage == "reserved"
                and payload.get("schedule_row_id") == active_row_id
                and payload.get("run_id") == active_run_id
            ):
                raise ContractError("invalid D-087 campaign run start")
            stage = "started"
            continue
        if event_type == "RunTerminal":
            usage_evidence = payload.get("usage_evidence")
            usage_evidence_hash = payload.get("usage_evidence_hash")
            usage_reconciliation_passed = payload.get("usage_reconciliation_passed")
            if not (
                stage == "started"
                and payload.get("schedule_row_id") == active_row_id
                and payload.get("run_id") == active_run_id
                and isinstance(usage_evidence, dict)
                and _valid_sha256_identity(usage_evidence_hash)
                and usage_evidence.get("content_hash") == usage_evidence_hash
                and usage_reconciliation_passed is True
                and usage_evidence.get("descriptor", {}).get("qualification_hash")
                == payload.get("qualification_hash")
            ):
                raise ContractError("invalid D-087 campaign run terminal event")
            try:
                from patchloop.evals.runner import (
                    _validate_d087_usage_evidence,
                )

                _validate_d087_usage_evidence(
                    usage_evidence,
                    run_id=active_run_id or "",
                    schedule_row_id=active_row_id or "",
                )
            except (ContractError, ImportError, TypeError, ValueError) as exc:
                raise ContractError("invalid D-087 terminal durable usage descriptor") from exc
            active_usage_evidence = usage_evidence
            active_usage_evidence_hash = usage_evidence_hash
            active_usage_reconciliation_passed = usage_reconciliation_passed
            stage = "terminal"
            continue
        if event_type == "RunCostSettled":
            run_cost_nanos = payload.get("actual_run_cost_nanos")
            try:
                from patchloop.evals.runner import (
                    _load_d087_durable_usage_evidence,
                    _validate_d087_usage_evidence,
                )

                durable_usage_evidence = _load_d087_durable_usage_evidence(
                    active_run_id or "",
                    active_row_id or "",
                    run_root,
                )
                durable_cost_nanos = _validate_d087_usage_evidence(
                    durable_usage_evidence,
                    run_id=active_run_id or "",
                    schedule_row_id=active_row_id or "",
                )
            except (ContractError, ImportError, OSError, TypeError, ValueError) as exc:
                raise ContractError(
                    "D-087 prior settlement durable usage could not be revalidated"
                ) from exc
            if not (
                stage == "terminal"
                and payload.get("schedule_row_id") == active_row_id
                and payload.get("run_id") == active_run_id
                and payload.get("campaign_cost_control_hash") == control_hash
                and payload.get("cap_nanos") == cap_nanos
                and payload.get("reserve_nanos") == reserve_nanos
                and type(run_cost_nanos) is int
                and isinstance(active_usage_evidence, dict)
                and canonical_json(active_usage_evidence) == canonical_json(durable_usage_evidence)
                and payload.get("usage_evidence_hash") == active_usage_evidence_hash
                and active_usage_reconciliation_passed is True
                and payload.get("usage_reconciliation_passed") is True
                and run_cost_nanos == durable_cost_nanos
                and 0 <= run_cost_nanos <= reserve_nanos
                and payload.get("accrued_cost_nanos_before") == accrued_nanos
                and payload.get("accrued_cost_nanos_after") == accrued_nanos + run_cost_nanos
                and payload.get("held_reserve_nanos_after") == 0
                and payload.get("usage_reconciliation_passed") is True
                and _valid_sha256_identity(payload.get("usage_evidence_hash"))
            ):
                raise ContractError("invalid D-087 campaign cost settlement")
            accrued_nanos += run_cost_nanos
            active_row_id = None
            active_run_id = None
            active_usage_evidence = None
            active_usage_evidence_hash = None
            active_usage_reconciliation_passed = None
            stage = "idle"
            continue
        if event_type == "CostReserveUnavailable":
            if not (
                stage == "idle"
                and not spend_halted
                and payload.get("campaign_cost_control_hash") == control_hash
                and payload.get("cap_nanos") == cap_nanos
                and payload.get("reserve_nanos") == reserve_nanos
                and payload.get("accrued_cost_nanos") == accrued_nanos
                and payload.get("held_reserve_nanos") == 0
                and accrued_nanos + reserve_nanos > cap_nanos
            ):
                raise ContractError("invalid D-087 unavailable-reserve event")
            spend_halted = True
            stage = "halted"
            continue
        if event_type == "RunNotStarted":
            if stage != "halted":
                raise ContractError("invalid D-087 not-started event")
            continue
        if event_type == "CampaignCompleted":
            if stage not in {"idle", "terminal", "halted"}:
                raise ContractError("invalid D-087 campaign completion")
            stage = "completed"
            continue
        raise ContractError(f"unsupported D-087 campaign journal event: {event_type}")

    for consumed in consumed_rows:
        reservation = reservation_events.get(consumed.get("reservation_event_hash", ""))
        if not (
            consumed.get("execution_hash") == execution_hash
            and consumed.get("control_hash") == control_hash
            and reservation is not None
            and reservation.get("schedule_row_id") == consumed.get("schedule_row_id")
            and reservation.get("run_id") == consumed.get("run_id")
            and reservation.get("control_hash") == consumed.get("control_hash")
        ):
            raise ContractError("D-087 journal omits or rewrites a consumed reservation")

    if not (
        stage == "started"
        and latest_reservation is not None
        and latest_reservation.get("event_hash") == reservation_event_hash
        and latest_reservation.get("payload", {}).get("schedule_row_id") == schedule_row_id
        and latest_reservation.get("payload", {}).get("run_id") == run_id
        and events[-1].get("event_type") == "RunStarted"
        and events[-1].get("payload", {}).get("schedule_row_id") == schedule_row_id
        and events[-1].get("payload", {}).get("run_id") == run_id
        and events[-1].get("sequence") == latest_reservation.get("sequence", 0) + 1
    ):
        raise ContractError("D-087 capability requires the exact latest reserved and started run")
    return sha256_bytes(raw)


class AgentRunner:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else runtime_root()
        self.state = StateStore(self.root / "state.sqlite3")
        self.artifacts = ArtifactStore(self.root / "artifacts")
        self.ownership = RunOwnershipCoordinator(self.root / "worker-locks")
        self.workspaces = WorkspaceManager(
            repository_root() / "fixtures" / "repositories", self.root / "workspaces"
        )

    def start(
        self,
        task_path: str | Path,
        *,
        model: str = "mock",
        memory_condition: MemoryCondition = MemoryCondition.NO_MEMORY,
        memory_policy_version: str = "v1",
        manifest: RunManifest | None = None,
        input_price_per_million_usd: float | None = None,
        cached_input_price_per_million_usd: float | None = None,
        cache_write_input_price_per_million_usd: float | None = None,
        output_price_per_million_usd: float | None = None,
        model_id: str | None = None,
        reasoning_effort: str = "medium",
        reasoning_mode: str = "standard",
        service_tier: str = "default",
        max_output_tokens: int = 4096,
        budget: Budget | None = None,
        experiment_context: ExperimentRunContext | None = None,
        self_validation: bool = False,
        live_authorization: LiveExecutionAuthorization | None = None,
        row_execution_authorization: RowExecutionAuthorization | None = None,
        batch_image_authorization: BatchImageAuthorization | None = None,
        campaign_cost_reservation: (CampaignCostReservationAuthorization | None) = None,
        evaluator_v2_authority: EvaluatorV2QualificationAuthority | None = None,
        _allowed_worker_statuses: set[RunStatus] | None = None,
    ) -> dict[str, Any]:
        task_dir = self._task_dir(task_path)
        package = load_task_package(task_dir)
        normalized_model = model
        replay_hash = None
        if model.startswith("replay:"):
            normalized_model, _, replay_hash = self._replay_identity(model)
            selected_provider = "replay"
        elif model in {"mock", "openai"}:
            selected_provider = model
        else:
            raise ContractError(f"unknown model adapter: {model}")

        if manifest is not None:
            package_identity = (
                package.public.task_id,
                package.public.task_version,
                package.public.repository.base_commit,
                package.public_spec_hash,
                package.private_spec_hash,
            )
            manifest_identity = (
                manifest.task_id,
                manifest.task_version,
                manifest.base_commit,
                manifest.public_spec_hash,
                manifest.private_spec_hash,
            )
            if package_identity != manifest_identity:
                raise ContractError("task package does not match the immutable run manifest")
        if manifest is not None and manifest.model.provider != selected_provider:
            raise ContractError("model selector does not match the immutable run manifest provider")
        if manifest is None and evaluator_v2_authority is not None:
            raise ContractError("evaluator-v2 authority requires a prebuilt v2 manifest")
        if manifest is not None:
            if manifest.schema_version == "run-manifest-v2":
                if evaluator_v2_authority is None:
                    raise ContractError(
                        "run-manifest-v2 requires separately qualified evaluator authority"
                    )
                evaluator_v2_authority = validate_evaluator_v2_manifest_authority(
                    manifest,
                    evaluator_v2_authority,
                )
            elif evaluator_v2_authority is not None:
                raise ContractError("evaluator-v2 authority cannot be attached to a v1 manifest")
        if selected_provider == "openai" and (
            self_validation
            or (
                manifest is not None
                and (
                    manifest.tool_schema_version == "v3"
                    or manifest.context_policy_version == "phase-evidence-v6"
                )
            )
        ):
            raise ContractError(
                "self-validation v3/v6 is offline-only and unavailable for the OpenAI provider"
            )
        if selected_provider == "openai":
            if row_execution_authorization is None:
                self._require_live_authorization(
                    manifest,
                    live_authorization,
                    runner_root=self.root,
                    evaluator_v2_authority=evaluator_v2_authority,
                )
            elif manifest is None:
                raise HarnessAdmissionError("row capability requires a prebuilt manifest")
            else:
                _consume_row_execution_authorization(
                    manifest,
                    row_execution_authorization,
                    expected_authority_kind="live",
                    live_authorization=live_authorization,
                )
            self._require_campaign_cost_reservation(
                manifest,
                live_authorization,
                campaign_cost_reservation,
            )
        elif campaign_cost_reservation is not None or row_execution_authorization is not None:
            raise ContractError("live execution capabilities are only valid for OpenAI")

        docker_sandbox = self._docker_sandbox(package)
        if batch_image_authorization is not None or (
            row_execution_authorization is not None
            and row_execution_authorization.image_admission_policy is not None
        ):
            image_identity = validate_row_batch_image(
                batch_image_authorization,
                row_execution_authorization,
                manifest,
                expected_kind="live",
                expected_image=(
                    package.environment.evaluator_image if package.environment else None
                ),
                expected_digest=(package.environment.image_digest if package.environment else None),
            )
            backend = "docker"
        else:
            backend = (
                "docker"
                if DockerSandbox.available() and docker_sandbox.image_identity() is not None
                else "local"
            )
            if package.environment is not None:
                image_identity = docker_sandbox.image_identity()
                if backend != "docker":
                    raise ContractError(
                        "task requires its digest-pinned Docker evaluator image, "
                        "but it is unavailable"
                    )
                if image_identity != package.environment.image_digest:
                    raise ContractError(
                        "task evaluator image identity does not match environment.yaml: "
                        f"{image_identity} != {package.environment.image_digest}"
                    )
        if manifest is None:
            selected_model_id = "mock-v1" if selected_provider == "mock" else normalized_model
            image_identity = docker_sandbox.image_identity() if backend == "docker" else None
            probe_image_identity = (
                docker_sandbox.probe_image_identity()
                if (self_validation and package.public.probe_profiles and backend == "docker")
                else None
            )
            manifest = build_manifest(
                package,
                provider=selected_provider,
                model_id=selected_model_id,
                memory_condition=memory_condition,
                memory_policy_version=memory_policy_version,
                sandbox_backend=backend,
                agent_image_digest=image_identity,
                evaluator_image_digest=image_identity,
                probe_image_digest=probe_image_identity,
                input_price_per_million_usd=input_price_per_million_usd,
                cached_input_price_per_million_usd=cached_input_price_per_million_usd,
                cache_write_input_price_per_million_usd=(cache_write_input_price_per_million_usd),
                output_price_per_million_usd=output_price_per_million_usd,
                reasoning_effort=reasoning_effort,
                reasoning_mode=reasoning_mode,
                service_tier=service_tier,
                max_output_tokens=max_output_tokens,
                budget=budget,
                replay_hash=replay_hash,
                experiment_context=experiment_context,
                self_validation=self_validation,
            )
        if (
            manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}
            and package.public.probe_profiles
            and manifest.probe_image_digest is None
        ):
            raise ContractError(
                "registered probe profiles require the dedicated Docker "
                "probe image and a manifest-bound image identity"
            )
        allowed_statuses = _allowed_worker_statuses or {RunStatus.CREATED}
        with self.ownership.acquire(manifest.run_id) as worker:
            worker_claim = self.state.claim_run_for_worker(
                manifest.run_id,
                owner_id=worker.owner_id,
                owner_pid=worker.pid,
                owner_hostname=worker.hostname,
                allowed_statuses=allowed_statuses,
                manifest=manifest,
            )
            try:
                if selected_provider == "openai" and (
                    self._is_ac_fixed_bundle_cost_completion_manifest(manifest)
                    or self._is_heldout_ac_experiment(manifest)
                ):
                    self._consume_ac_row_start_once(
                        manifest,
                        live_authorization,
                    )
                workspace = self.root / "workspaces" / manifest.run_id / "repo"
                if not workspace.exists():
                    workspace = self.workspaces.create(
                        manifest.run_id,
                        package.public.repository.url,
                        package.public.repository.base_commit,
                    )
                workspace = self.workspaces.validate_managed_workspace(workspace)
                if self.state.latest_checkpoint(manifest.run_id) is None:
                    self.workspaces.validate_pristine(
                        workspace,
                        package.public.repository.url,
                        package.public.repository.base_commit,
                    )
                public_review_base_provenance = self._prepare_public_review_base_provenance(
                    manifest=manifest,
                    task=package.public,
                    workspace=workspace,
                )
                if selected_provider == "openai":
                    self._consume_campaign_cost_reservation(
                        manifest,
                        live_authorization,
                        campaign_cost_reservation,
                    )
                return self._execute(
                    package,
                    workspace,
                    manifest,
                    normalized_model,
                    public_review_base_provenance=(public_review_base_provenance),
                    worker_claim=worker_claim,
                    evaluator_v2_authority=evaluator_v2_authority,
                    row_execution_authorization=row_execution_authorization,
                )
            except RunOwnershipConflict:
                raise
            except Exception as exc:
                events = self.state.list_events(manifest.run_id)
                if any(
                    event.type in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
                    for event in events
                ):
                    raise
                if self._evaluation_receipt_path(manifest.run_id).exists():
                    raise
                checkpoint = self.state.latest_checkpoint(manifest.run_id)
                self._terminal_failure(
                    task_dir,
                    manifest,
                    checkpoint.phase if checkpoint is not None else Phase.INTAKE,
                    self._usage(manifest.run_id),
                    exc,
                    RunOutcomeKind.INFRASTRUCTURE_ERROR,
                )
                raise

    def resume(
        self,
        run_id: str,
        *,
        live_authorization: LiveExecutionAuthorization | None = None,
        evaluator_v2_authority: EvaluatorV2QualificationAuthority | None = None,
    ) -> dict[str, Any]:
        manifest = self.state.get_manifest(run_id)
        if (
            manifest.model.provider == "openai"
            and manifest.experiment is not None
            and manifest.experiment.purpose == ExperimentPurpose.RAPID_PUBLIC_DEVELOPMENT
        ):
            raise ContractError("rapid public development live resume is disabled")
        if (
            manifest.model.provider == "openai"
            and manifest.experiment is not None
            and manifest.experiment.experiment_id
            in {
                CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID,
                CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID,
                *AC_FIXED_BUNDLE_ALL_COST_EXPERIMENT_IDS,
                "core-ac-fixed-bundle-heldout-20260814-v1",
            }
        ):
            if (
                manifest.experiment.experiment_id
                == CONDITION_NEUTRAL_COMPARISON_ACCRUED_CAP_EXPERIMENT_ID
            ):
                raise ContractError(
                    "D-087 live resume is disabled until request-level billing "
                    "reservations are durable"
                )
            raise ContractError("full-schedule live resume is disabled by its frozen policy")
        task_dir = self._find_task(manifest)
        if manifest.model.provider == "mock":
            model = "mock"
        elif manifest.model.provider == "replay":
            model = manifest.model.model_id
        else:
            model = "openai"
        return self.start(
            task_dir,
            model=model,
            memory_condition=manifest.memory.condition,
            manifest=manifest,
            live_authorization=live_authorization,
            evaluator_v2_authority=evaluator_v2_authority,
            _allowed_worker_statuses={
                RunStatus.CREATED,
                RunStatus.SUSPENDED,
                RunStatus.RUNNING,
            },
        )

    @staticmethod
    def _is_frozen_comparison_runtime_manifest(
        manifest: RunManifest,
    ) -> bool:
        experiment = manifest.experiment
        comparison_pilot = bool(
            experiment is not None
            and experiment.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_LIVE_PILOT
            and experiment.experiment_id == CONDITION_NEUTRAL_COMPARISON_PILOT_EXPERIMENT_ID
            and manifest.task_id == "babel-strict-grouped-decimal-trailing-zeroes"
            and experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
            and experiment.schedule_seed == 20260723
            and experiment.schedule_order == 1
            and experiment.repetition == 1
        )
        return bool(
            experiment is not None
            and (
                experiment.purpose
                in {
                    ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY,
                    ExperimentPurpose.CORE,
                }
                or comparison_pilot
            )
            and manifest.tool_schema_version == "v2"
            and manifest.context_policy_version == "phase-evidence-v5"
            and manifest.model.provider == "openai"
            and manifest.model.model_id == "gpt-5.4-mini-2026-03-17"
            and manifest.model.reasoning_effort == "medium"
            and manifest.model.reasoning_mode == "standard"
            and manifest.model.service_tier == "default"
            and manifest.model.transport_max_retries == 0
            and manifest.model.max_output_tokens == 25_000
            and manifest.budget.max_model_calls is None
            and manifest.budget.max_tool_calls is None
            and manifest.budget.max_total_tokens == 1_600_000
            and manifest.budget.wall_clock_timeout_seconds == 1_800
            and manifest.memory.max_context_tokens == 2_000
            and (
                experiment.purpose == ExperimentPurpose.CORE
                or manifest.memory.condition == MemoryCondition.NO_MEMORY
            )
            and manifest.fault.type == "none"
            and manifest.public_review_contract is None
        )

    @staticmethod
    def _is_condition_neutral_runtime_v2_manifest(
        manifest: RunManifest,
    ) -> bool:
        experiment = manifest.experiment
        return bool(
            experiment is not None
            and experiment.experiment_id == CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID
            and experiment.purpose == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY
            and experiment.dataset_role == DatasetRole.MEMORY_DEVELOPMENT
            and experiment.schedule_seed == 20260723
            and experiment.repetition in {1, 2}
            and experiment.schedule_order
            == _CONDITION_NEUTRAL_NO_MEMORY_ROW_ORDER.get((manifest.task_id, experiment.repetition))
            and _valid_sha256_identity(experiment.campaign_cost_control_hash)
            and manifest.tool_schema_version == "v2"
            and manifest.context_policy_version == "phase-evidence-v5"
            and manifest.model.provider == "openai"
            and manifest.model.model_id == "gpt-5.4-mini-2026-03-17"
            and manifest.model.reasoning_effort == "medium"
            and manifest.model.reasoning_mode == "standard"
            and manifest.model.service_tier == "default"
            and manifest.model.transport_max_retries == 0
            and manifest.model.max_output_tokens == 25_000
            and manifest.budget.max_model_calls is None
            and manifest.budget.max_tool_calls is None
            and manifest.budget.max_total_tokens == 3_000_000
            and manifest.budget.wall_clock_timeout_seconds == 3_600
            and manifest.memory.condition == MemoryCondition.NO_MEMORY
            and manifest.memory.max_context_tokens == 2_000
            and manifest.fault.type == "none"
            and manifest.public_review_contract is None
        )

    @staticmethod
    def _is_ac_fixed_bundle_readiness_manifest(
        manifest: RunManifest,
    ) -> bool:
        experiment = manifest.experiment
        expected_order = _AC_FIXED_BUNDLE_ROW_ORDER.get(
            (manifest.task_id, manifest.memory.condition)
        )
        expected_index = (
            (None, None)
            if manifest.memory.condition == MemoryCondition.NO_MEMORY
            else (D110_INDEX_VERSION, D110_INDEX_CONTENT_HASH)
        )
        return bool(
            experiment is not None
            and experiment.experiment_id in AC_FIXED_BUNDLE_ALL_EXPERIMENT_IDS
            and experiment.purpose == ExperimentPurpose.DEVELOPMENT_VALIDATION_AC_READINESS
            and experiment.dataset_role == DatasetRole.DEVELOPMENT_VALIDATION
            and experiment.schedule_seed == 20260723
            and experiment.repetition == 1
            and expected_order is not None
            and experiment.schedule_order == expected_order
            and manifest.tool_schema_version == "v2"
            and manifest.context_policy_version == "phase-evidence-v5"
            and manifest.model.provider == "openai"
            and manifest.model.model_id == "gpt-5.4-mini-2026-03-17"
            and manifest.model.reasoning_effort == "medium"
            and manifest.model.reasoning_mode == "standard"
            and manifest.model.service_tier == "default"
            and manifest.model.transport_max_retries == 0
            and manifest.model.max_output_tokens == 25_000
            and (
                (
                    experiment.experiment_id not in AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_IDS
                    and manifest.budget.max_model_calls is None
                    and manifest.budget.max_tool_calls is None
                    and manifest.budget.max_total_tokens == 3_000_000
                    and manifest.budget.token_budget_schema_version is None
                )
                or (
                    experiment.experiment_id in AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_IDS
                    and manifest.budget.max_model_calls == 180
                    and manifest.budget.max_tool_calls == 300
                    and manifest.budget.max_total_tokens == 3_350_000
                    and manifest.budget.token_budget_schema_version == _SPLIT_TOKEN_BUDGET_SCHEMA
                    and manifest.budget.max_cumulative_input_tokens == 3_000_000
                    and manifest.budget.max_cumulative_output_tokens == 350_000
                )
            )
            and manifest.budget.wall_clock_timeout_seconds == 3_600
            and manifest.memory.condition in {MemoryCondition.NO_MEMORY, MemoryCondition.STRUCTURED}
            and manifest.memory_policy_version == FIXED_BUNDLE_POLICY_VERSION
            and manifest.memory.max_context_tokens == 2_000
            and (manifest.memory.index_version, manifest.memory.index_hash) == expected_index
            and manifest.fault.type == "none"
            and manifest.public_review_contract is None
        )

    @staticmethod
    def _is_ac_fixed_bundle_cost_completion_manifest(manifest: RunManifest) -> bool:
        return bool(
            AgentRunner._is_ac_fixed_bundle_readiness_manifest(manifest)
            and manifest.experiment is not None
            and manifest.experiment.experiment_id in AC_FIXED_BUNDLE_ALL_COST_EXPERIMENT_IDS
            and _valid_sha256_identity(manifest.experiment.campaign_cost_control_hash)
        )

    @staticmethod
    def _is_heldout_ac_experiment(manifest: RunManifest | None) -> bool:
        from patchloop.evals.heldout_ac_live_contract import is_heldout_ac_experiment

        return is_heldout_ac_experiment(manifest)

    @staticmethod
    def rehearse_provider_dispatch(
        manifest: RunManifest,
        row_execution_authorization: RowExecutionAuthorization,
        *,
        batch_image_authorization: BatchImageAuthorization | None = None,
    ) -> dict[str, Any]:
        """Consume the real row gate and stop before any provider adapter call."""

        _consume_row_execution_authorization(
            manifest,
            row_execution_authorization,
            expected_authority_kind="rehearsal",
            live_authorization=None,
        )
        if batch_image_authorization is not None or (
            row_execution_authorization.image_admission_policy is not None
        ):
            validate_row_batch_image(
                batch_image_authorization,
                row_execution_authorization,
                manifest,
                expected_kind="rehearsal",
                expected_image=(
                    batch_image_authorization.image if batch_image_authorization else None
                ),
                expected_digest=manifest.evaluator_image_digest,
            )
        boundary = _provider_dispatch_boundary(
            manifest,
            row_execution_authorization,
            stop_before_dispatch=True,
        )
        assert boundary is not None
        return boundary

    @staticmethod
    def _require_live_authorization(
        manifest: RunManifest | None,
        authorization: LiveExecutionAuthorization | None,
        *,
        runner_root: Path | None = None,
        evaluator_v2_authority: EvaluatorV2QualificationAuthority | None = None,
    ) -> None:
        try:
            plan = _load_live_execution_plan(authorization) if authorization is not None else None
        except ContractError:
            plan = None
        if (
            manifest is None
            or manifest.experiment is None
            or authorization is None
            or authorization._guard is not _LIVE_AUTHORIZATION_GUARD
            or authorization.execution_hash != manifest.experiment.execution_hash
            or not AgentRunner._live_plan_matches_manifest(
                manifest,
                authorization,
                plan=plan,
                runner_root=runner_root,
            )
        ):
            raise HarnessAdmissionError(
                "live model execution requires an approved experiment execution capability"
            )
        assert isinstance(plan, dict)
        if "evaluator_v2_qualification" in plan:
            try:
                from patchloop.evals.evaluator_v2_source_qualification import (
                    validate_evaluator_v2_ac_paid_authority,
                )

                if evaluator_v2_authority is None:
                    raise ContractError("paid evaluator-v2 authority is missing")
                validate_evaluator_v2_ac_paid_authority(
                    manifest,
                    evaluator_v2_authority,
                    plan["evaluator_v2_qualification"],
                )
            except (ContractError, ImportError, TypeError, ValueError) as exc:
                raise ContractError(
                    "live model execution requires the exact qualified evaluator-v2 authority"
                ) from exc
        if (
            AgentRunner._is_condition_neutral_runtime_v2_manifest(manifest)
            or AgentRunner._is_ac_fixed_bundle_cost_completion_manifest(manifest)
            or AgentRunner._is_heldout_ac_experiment(manifest)
        ):
            AgentRunner._require_full_schedule_reservation(
                manifest,
                authorization,
                plan=plan,
                runner_root=runner_root,
            )

    @staticmethod
    def _require_full_schedule_reservation(
        manifest: RunManifest,
        authorization: LiveExecutionAuthorization,
        *,
        plan: dict[str, Any] | None = None,
        runner_root: Path | None = None,
    ) -> dict[str, str]:
        """Require an exact up-front reserve journal before every paid row."""

        assert manifest.experiment is not None
        if AgentRunner._is_heldout_ac_experiment(manifest):
            from patchloop.evals.heldout_ac_live_contract import (
                validate_heldout_ac_reservation_journal_prefix,
            )

            if runner_root is None:
                raise ContractError("held-out reservation requires the exact runtime root")
            if plan is None:
                plan = _load_live_execution_plan(authorization)
            return validate_heldout_ac_reservation_journal_prefix(
                plan=plan,
                manifest=manifest,
                plan_path=authorization.plan_path,
                plan_file_sha256=authorization.plan_hash,
                runner_root=runner_root,
            )
        ac_cost_profile = AgentRunner._is_ac_fixed_bundle_cost_completion_manifest(manifest)
        expected_experiment_id = (
            manifest.experiment.experiment_id
            if ac_cost_profile
            else CONDITION_NEUTRAL_NO_MEMORY_V2_EXPERIMENT_ID
        )
        expected_purpose = (
            ExperimentPurpose.DEVELOPMENT_VALIDATION_AC_READINESS.value
            if ac_cost_profile
            else ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY.value
        )
        expected_control_schema = (
            _AC_FIXED_BUNDLE_FULL_SCHEDULE_COST_CONTROL_SCHEMA
            if ac_cost_profile
            else _CONDITION_NEUTRAL_FULL_SCHEDULE_COST_CONTROL_SCHEMA
        )
        expected_policy_schema = (
            (
                _AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY_SCHEMA
                if manifest.experiment.experiment_id in AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_IDS
                else _AC_FIXED_BUNDLE_FULL_SCHEDULE_COST_POLICY_SCHEMA
            )
            if ac_cost_profile
            else _CONDITION_NEUTRAL_FULL_SCHEDULE_COST_POLICY_SCHEMA
        )
        expected_count = 4 if ac_cost_profile else 12
        expected_dataset_role = (
            DatasetRole.DEVELOPMENT_VALIDATION.value
            if ac_cost_profile
            else DatasetRole.MEMORY_DEVELOPMENT.value
        )
        if plan is None:
            plan = _load_live_execution_plan(authorization)
        cost_control = plan.get("campaign_cost_control")
        descriptor = cost_control.get("descriptor") if isinstance(cost_control, dict) else None
        control_hash = cost_control.get("content_hash") if isinstance(cost_control, dict) else None
        schedule_row_ids = (
            descriptor.get("schedule_row_ids") if isinstance(descriptor, dict) else None
        )
        journal_path_raw = plan.get("journal_path")
        if not (
            isinstance(cost_control, dict)
            and cost_control.get("schema_version") == expected_control_schema
            and isinstance(descriptor, dict)
            and descriptor.get("schema_version") == expected_policy_schema
            and descriptor.get("experiment_id") == expected_experiment_id
            and _valid_sha256_identity(control_hash)
            and sha256_text(canonical_json(descriptor)) == control_hash
            and control_hash == manifest.experiment.campaign_cost_control_hash
            and isinstance(schedule_row_ids, list)
            and len(schedule_row_ids) == expected_count
            and manifest.experiment.schedule_row_id in schedule_row_ids
            and isinstance(journal_path_raw, str)
        ):
            raise ContractError("approved full-schedule cost control is invalid")
        journal_path = Path(journal_path_raw)
        expected_name = f"{expected_experiment_id}.jsonl"
        if not (
            journal_path.is_absolute()
            and str(journal_path.resolve(strict=False)) == journal_path_raw
            and journal_path.name == expected_name
            and journal_path.parent.name == "journals"
            and journal_path.parent.parent.name == "experiments"
        ):
            raise ContractError("approved full-schedule campaign journal path is invalid")
        approved_root = Path(authorization.plan_path).resolve(strict=False).parents[2]
        if (
            journal_path.parents[2].resolve(strict=False) != approved_root
            or runner_root is None
            or Path(runner_root).resolve(strict=False) != approved_root
        ):
            raise ContractError("full-schedule journal root differs from the runtime root")
        try:
            raw = journal_path.read_bytes()
            if not raw.endswith(b"\n"):
                raise ValueError("journal is not newline terminated")
            events = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ContractError("full-schedule reservation journal is invalid") from exc
        previous_hash: str | None = None
        previous_recorded_at: datetime | None = None
        ac_payload_keys: dict[str, set[str]] | None = None
        if ac_cost_profile:
            from patchloop.evals.runner import _ac_full_schedule_event_payload_keys

            ac_payload_keys = _ac_full_schedule_event_payload_keys()
        for sequence, event in enumerate(events, start=1):
            if not isinstance(event, dict):
                raise ContractError("full-schedule campaign journal event is invalid")
            recorded_hash = event.get("event_hash")
            body = {key: value for key, value in event.items() if key != "event_hash"}
            if not (
                set(event)
                == {
                    "schema_version",
                    "sequence",
                    "event_type",
                    "recorded_at",
                    "previous_event_hash",
                    "payload",
                    "event_hash",
                }
                and event.get("schema_version") == _CAMPAIGN_JOURNAL_EVENT_SCHEMA
                and type(event.get("sequence")) is int
                and event.get("sequence") == sequence
                and event.get("previous_event_hash") == previous_hash
                and isinstance(event.get("recorded_at"), str)
                and bool(event.get("recorded_at"))
                and _valid_sha256_identity(recorded_hash)
                and sha256_text(canonical_json(body)) == recorded_hash
            ):
                raise ContractError("full-schedule campaign journal hash chain is invalid")
            try:
                recorded_at = datetime.fromisoformat(str(event.get("recorded_at")))
            except ValueError as exc:
                raise ContractError("full-schedule campaign chronology is invalid") from exc
            if not (
                recorded_at.tzinfo is not None
                and recorded_at.utcoffset() == timedelta(0)
                and (previous_recorded_at is None or recorded_at >= previous_recorded_at)
            ):
                raise ContractError("full-schedule campaign chronology is invalid")
            previous_recorded_at = recorded_at
            payload = event.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("full-schedule campaign journal payload is invalid")
            if ac_payload_keys is not None and (
                event.get("event_type") not in ac_payload_keys
                or set(payload) != ac_payload_keys[event["event_type"]]
            ):
                raise ContractError("A/C full-schedule event payload fields differ")
            previous_hash = recorded_hash
            if event.get("event_type") == "CostReserveUnavailable":
                raise ContractError("full-schedule policy forbids cost-censoring events")
        if len(events) < 2:
            raise ContractError("full-schedule reservation is missing")
        started = events[0].get("payload")
        reserved = events[1].get("payload")
        policy = descriptor.get("policy")
        expected_plan_content_hash = sha256_text(canonical_json(plan))
        if not (
            events[0].get("event_type") == "CampaignStarted"
            and isinstance(started, dict)
            and started.get("experiment_id") == expected_experiment_id
            and started.get("purpose") == expected_purpose
            and started.get("execution_hash") == authorization.execution_hash
            and started.get("execution_plan_hash") == expected_plan_content_hash
            and started.get("schedule_hash") == descriptor.get("schedule_hash")
            and started.get("campaign_cost_control_hash") == control_hash
            and events[1].get("event_type") == "FullScheduleCostReserved"
            and isinstance(reserved, dict)
            and reserved.get("experiment_id") == expected_experiment_id
            and reserved.get("execution_hash") == authorization.execution_hash
            and reserved.get("execution_plan_hash") == expected_plan_content_hash
            and reserved.get("campaign_cost_control_hash") == control_hash
            and reserved.get("schedule_hash") == descriptor.get("schedule_hash")
            and reserved.get("schedule_row_ids") == schedule_row_ids
            and isinstance(policy, dict)
            and type(policy.get("per_run_reserve_nanos")) is int
            and type(policy.get("full_schedule_reserve_nanos")) is int
            and type(policy.get("hard_cap_nanos")) is int
            and type(reserved.get("per_run_reserve_nanos")) is int
            and reserved.get("per_run_reserve_nanos") == policy.get("per_run_reserve_nanos")
            and type(reserved.get("full_schedule_reserve_nanos")) is int
            and reserved.get("full_schedule_reserve_nanos")
            == policy.get("full_schedule_reserve_nanos")
            and type(reserved.get("hard_cap_nanos")) is int
            and reserved.get("hard_cap_nanos") == policy.get("hard_cap_nanos")
            and type(reserved.get("row_reserve_count")) is int
            and reserved.get("row_reserve_count") == expected_count
            and reserved.get("cost_censoring_allowed") is False
        ):
            raise ContractError("full-schedule reserve does not match the plan")
        current = events[-1]
        current_payload = current.get("payload")
        approved_schedule = plan.get("schedule")
        if not (
            isinstance(approved_schedule, list)
            and len(approved_schedule) == expected_count
            and all(isinstance(row, dict) for row in approved_schedule)
            and [row.get("schedule_row_id") for row in approved_schedule] == schedule_row_ids
            and sha256_text(canonical_json(approved_schedule)) == descriptor.get("schedule_hash")
        ):
            raise ContractError("approved schedule does not match its reserve")
        expected_order = schedule_row_ids.index(manifest.experiment.schedule_row_id) + 1
        expected_row = approved_schedule[expected_order - 1]
        prefix = events[2:]
        expected_prefix_types = [
            event_type
            for _ in range(expected_order - 1)
            for event_type in ("RunStarted", "RunTerminal", "RunCostSettled")
        ] + ["RunStarted"]
        if [event.get("event_type") for event in prefix] != expected_prefix_types:
            raise ContractError("full-schedule prior row prefix is not fully settled")
        accrued_nanos = 0
        prior_run_ids: set[str] = set()
        row_identity_fields = (
            "order",
            "schedule_row_id",
            "task_id",
            "split",
            "dataset_role",
            "condition",
            "repetition",
        )
        for index in range(expected_order - 1):
            expected_prior = approved_schedule[index]
            started_event, terminal_event, settled_event = prefix[index * 3 : index * 3 + 3]
            started_payload = started_event.get("payload")
            terminal_payload = terminal_event.get("payload")
            settled_payload = settled_event.get("payload")
            if not all(
                isinstance(payload, dict)
                for payload in (started_payload, terminal_payload, settled_payload)
            ):
                raise ContractError("full-schedule prior row payload is invalid")
            assert isinstance(started_payload, dict)
            assert isinstance(terminal_payload, dict)
            assert isinstance(settled_payload, dict)
            prior_run_id = started_payload.get("run_id")
            usage_evidence = terminal_payload.get("usage_evidence")
            usage_evidence_hash = terminal_payload.get("usage_evidence_hash")
            run_cost_nanos = settled_payload.get("actual_run_cost_nanos")
            try:
                from patchloop.evals.runner import (
                    _load_full_schedule_durable_usage_evidence,
                    _validate_full_schedule_usage_evidence,
                )

                durable_usage_evidence = _load_full_schedule_durable_usage_evidence(
                    prior_run_id if isinstance(prior_run_id, str) else "",
                    str(expected_prior.get("schedule_row_id", "")),
                    approved_root,
                    experiment_id=expected_experiment_id,
                )
                durable_run_cost_nanos = _validate_full_schedule_usage_evidence(
                    durable_usage_evidence,
                    experiment_id=expected_experiment_id,
                    run_id=prior_run_id if isinstance(prior_run_id, str) else "",
                    schedule_row_id=str(expected_prior.get("schedule_row_id", "")),
                )
            except (ContractError, OSError, TypeError, ValueError) as exc:
                raise ContractError(
                    "full-schedule prior row durable settlement is invalid"
                ) from exc
            if not (
                isinstance(prior_run_id, str)
                and bool(prior_run_id)
                and prior_run_id not in prior_run_ids
                and all(
                    payload.get("run_id") == prior_run_id
                    for payload in (terminal_payload, settled_payload)
                )
                and all(
                    all(
                        _exact_typed_equal(payload.get(field), expected_prior.get(field))
                        for field in row_identity_fields
                    )
                    for payload in (started_payload, terminal_payload, settled_payload)
                )
                and all(
                    payload.get("execution_hash") == authorization.execution_hash
                    and payload.get("execution_plan_hash") == expected_plan_content_hash
                    and payload.get("campaign_cost_control_hash") == control_hash
                    for payload in (started_payload, terminal_payload, settled_payload)
                )
                and isinstance(usage_evidence, dict)
                and canonical_json(usage_evidence) == canonical_json(durable_usage_evidence)
                and _valid_sha256_identity(usage_evidence_hash)
                and usage_evidence.get("content_hash") == usage_evidence_hash
                and terminal_payload.get("usage_reconciliation_passed") is True
                and settled_payload.get("usage_evidence_hash") == usage_evidence_hash
                and settled_payload.get("usage_reconciliation_passed") is True
                and type(run_cost_nanos) is int
                and run_cost_nanos == durable_run_cost_nanos
                and 0 <= run_cost_nanos <= policy.get("per_run_reserve_nanos", -1)
                and type(settled_payload.get("accrued_cost_nanos_before")) is int
                and settled_payload.get("accrued_cost_nanos_before") == accrued_nanos
                and type(settled_payload.get("accrued_cost_nanos_after")) is int
                and settled_payload.get("accrued_cost_nanos_after")
                == accrued_nanos + run_cost_nanos
                and type(settled_payload.get("remaining_reserved_rows_after")) is int
                and settled_payload.get("remaining_reserved_rows_after")
                == expected_count - index - 1
            ):
                raise ContractError("full-schedule prior row settlement is invalid")
            prior_run_ids.add(prior_run_id)
            accrued_nanos += run_cost_nanos
        prior_starts = [
            event
            for event in events[:-1]
            if event.get("event_type") == "RunStarted"
            and isinstance(event.get("payload"), dict)
            and event["payload"].get("schedule_row_id") == manifest.experiment.schedule_row_id
        ]
        if not (
            current.get("event_type") == "RunStarted"
            and isinstance(current_payload, dict)
            and not prior_starts
            and expected_order == manifest.experiment.schedule_order
            and _exact_typed_equal(current_payload.get("order"), expected_order)
            and current_payload.get("schedule_row_id") == manifest.experiment.schedule_row_id
            and current_payload.get("task_id") == manifest.task_id
            and current_payload.get("dataset_role") == expected_dataset_role
            and current_payload.get("condition") == manifest.memory.condition.value
            and current_payload.get("repetition") == manifest.experiment.repetition
            and current_payload.get("run_id") == manifest.run_id
            and all(
                _exact_typed_equal(current_payload.get(field), expected_row.get(field))
                for field in (
                    "order",
                    "schedule_row_id",
                    "task_id",
                    "split",
                    "dataset_role",
                    "condition",
                    "repetition",
                )
            )
            and current_payload.get("execution_hash") == authorization.execution_hash
            and current_payload.get("execution_plan_hash") == expected_plan_content_hash
            and current_payload.get("campaign_cost_control_hash") == control_hash
        ):
            raise ContractError("current paid row is not uniquely bound to the journal")
        return {
            "journal_path": journal_path_raw,
            "journal_prefix_file_sha256": sha256_bytes(raw),
            "row_started_event_hash": str(current["event_hash"]),
        }

    def _consume_ac_row_start_once(
        self,
        manifest: RunManifest,
        live_authorization: LiveExecutionAuthorization | None,
    ) -> dict[str, str] | None:
        """Consume one exact A/C schedule row before entering the paid runtime."""

        if not (
            self._is_ac_fixed_bundle_cost_completion_manifest(manifest)
            or self._is_heldout_ac_experiment(manifest)
        ):
            return None
        if live_authorization is None or manifest.experiment is None:
            raise ContractError("A/C row-start consumption requires exact live authorization")
        binding = self._require_full_schedule_reservation(
            manifest,
            live_authorization,
            runner_root=self.root,
        )
        execution_hash = manifest.experiment.execution_hash
        schedule_row_id = manifest.experiment.schedule_row_id
        control_hash = manifest.experiment.campaign_cost_control_hash
        if control_hash is None:
            raise ContractError("A/C row-start consumption has no cost-control hash")
        marker_path = _ac_row_start_consumption_path(
            journal_path=binding["journal_path"],
            execution_hash=execution_hash,
            schedule_row_id=schedule_row_id,
        )
        existing = self.state.list_ac_row_start_consumptions(execution_hash)
        if any(
            row["schedule_row_id"] == schedule_row_id
            or row["run_id"] == manifest.run_id
            or row["row_started_event_hash"] == binding["row_started_event_hash"]
            for row in existing
        ):
            raise ContractError("A/C row start was already consumed")
        if marker_path.exists() or marker_path.is_symlink():
            self._require_valid_ac_row_start_marker(
                marker_path,
                execution_hash=execution_hash,
                schedule_row_id=schedule_row_id,
                control_hash=control_hash,
                journal_path=binding["journal_path"],
            )
            raise ContractError("A/C row start was already consumed")

        consumption = self.state.record_ac_row_start_consumption(
            execution_hash=execution_hash,
            schedule_row_id=schedule_row_id,
            run_id=manifest.run_id,
            row_started_event_hash=binding["row_started_event_hash"],
            journal_prefix_file_sha256=binding["journal_prefix_file_sha256"],
            control_hash=control_hash,
        )
        marker_body = {
            "schema_version": _AC_ROW_START_CONSUMPTION_MARKER_SCHEMA,
            "execution_hash": execution_hash,
            "schedule_row_id": schedule_row_id,
            "run_id": manifest.run_id,
            "row_started_event_hash": binding["row_started_event_hash"],
            "journal_prefix_file_sha256": binding["journal_prefix_file_sha256"],
            "control_hash": control_hash,
            "journal_path": binding["journal_path"],
            "consumed_at": consumption["consumed_at"],
            "state_consumption_content_hash": consumption["content_hash"],
        }
        marker = {
            **marker_body,
            "content_hash": sha256_text(canonical_json(marker_body)),
        }
        _write_ac_row_start_consumption_marker(marker_path, marker)
        return consumption

    @staticmethod
    def _require_valid_ac_row_start_marker(
        path: Path,
        *,
        execution_hash: str,
        schedule_row_id: str,
        control_hash: str,
        journal_path: str,
    ) -> None:
        try:
            raw = path.read_bytes()
            if not raw.endswith(b"\n") or len(raw.splitlines()) != 1:
                raise ValueError("marker is not one newline-terminated record")
            marker = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise RecoveryError("A/C row-start marker is invalid") from exc
        expected_keys = {
            "schema_version",
            "execution_hash",
            "schedule_row_id",
            "run_id",
            "row_started_event_hash",
            "journal_prefix_file_sha256",
            "control_hash",
            "journal_path",
            "consumed_at",
            "state_consumption_content_hash",
            "content_hash",
        }
        body = (
            {key: value for key, value in marker.items() if key != "content_hash"}
            if isinstance(marker, dict)
            else None
        )
        if not (
            isinstance(marker, dict)
            and set(marker) == expected_keys
            and isinstance(body, dict)
            and marker.get("schema_version") == _AC_ROW_START_CONSUMPTION_MARKER_SCHEMA
            and marker.get("execution_hash") == execution_hash
            and marker.get("schedule_row_id") == schedule_row_id
            and isinstance(marker.get("run_id"), str)
            and bool(marker.get("run_id"))
            and _valid_sha256_identity(marker.get("row_started_event_hash"))
            and _valid_sha256_identity(marker.get("journal_prefix_file_sha256"))
            and marker.get("control_hash") == control_hash
            and marker.get("journal_path") == journal_path
            and isinstance(marker.get("consumed_at"), str)
            and bool(marker.get("consumed_at"))
            and _valid_sha256_identity(marker.get("state_consumption_content_hash"))
            and _valid_sha256_identity(marker.get("content_hash"))
            and sha256_text(canonical_json(body)) == marker["content_hash"]
        ):
            raise RecoveryError("A/C row-start marker is invalid")

    def _require_campaign_cost_reservation(
        self,
        manifest: RunManifest | None,
        live_authorization: LiveExecutionAuthorization | None,
        authorization: CampaignCostReservationAuthorization | None,
    ) -> None:
        required = _is_d087_paid_manifest(manifest)
        if not required:
            if authorization is not None:
                raise ContractError("campaign cost reservation capability is reserved for D-087")
            return
        if (
            manifest is None
            or manifest.experiment is None
            or live_authorization is None
            or authorization is None
            or authorization._guard is not _CAMPAIGN_COST_RESERVATION_GUARD
            or authorization.execution_hash != manifest.experiment.execution_hash
            or authorization.execution_hash != live_authorization.execution_hash
            or authorization.campaign_cost_control_hash
            != manifest.experiment.campaign_cost_control_hash
            or authorization.schedule_row_id != manifest.experiment.schedule_row_id
            or authorization.run_id != manifest.run_id
            or not _valid_sha256_identity(authorization.journal_hash)
            or not _valid_sha256_identity(authorization.reservation_event_hash)
        ):
            raise ContractError(
                "D-087 live execution requires an exact campaign cost reservation capability"
            )
        plan = _load_live_execution_plan(live_authorization)
        expected_journal_path = plan.get("journal_path")
        cost_control = plan.get("campaign_cost_control")
        journal_path, journal_root = _d087_journal_identity(
            expected_journal_path,
            authorization.journal_path,
        )
        if (
            self.root.resolve(strict=False) != journal_root
            or self.state.path.resolve(strict=False)
            != (journal_root / "state.sqlite3").resolve(strict=False)
            or not isinstance(cost_control, dict)
        ):
            raise ContractError("D-087 runner root and reservation journal root must match")
        consumed_rows = self.state.list_d087_reservation_consumptions(authorization.execution_hash)
        observed_journal_hash = _validate_campaign_reservation_journal(
            journal_path,
            cost_control=cost_control,
            execution_hash=authorization.execution_hash,
            campaign_cost_control_hash=(authorization.campaign_cost_control_hash),
            schedule_row_id=authorization.schedule_row_id,
            run_id=authorization.run_id,
            reservation_event_hash=authorization.reservation_event_hash,
            run_root=journal_root,
            consumed_rows=consumed_rows,
        )
        if observed_journal_hash != authorization.journal_hash:
            raise ContractError("D-087 campaign journal bytes changed after capability issuance")
        if _campaign_reservation_consumption_path(authorization).exists():
            raise ContractError("D-087 campaign cost reservation was already consumed")
        if any(row["schedule_row_id"] == authorization.schedule_row_id for row in consumed_rows):
            raise ContractError("D-087 campaign cost reservation was already consumed")

    def _consume_campaign_cost_reservation(
        self,
        manifest: RunManifest,
        live_authorization: LiveExecutionAuthorization | None,
        authorization: CampaignCostReservationAuthorization | None,
    ) -> None:
        if not _is_d087_paid_manifest(manifest):
            return
        self._require_campaign_cost_reservation(
            manifest,
            live_authorization,
            authorization,
        )
        assert authorization is not None
        consumption = self.state.record_d087_reservation_consumption(
            execution_hash=authorization.execution_hash,
            schedule_row_id=authorization.schedule_row_id,
            run_id=authorization.run_id,
            reservation_event_hash=authorization.reservation_event_hash,
            control_hash=authorization.campaign_cost_control_hash,
        )
        marker_path = _campaign_reservation_consumption_path(authorization)
        marker = {
            "schema_version": _CAMPAIGN_RESERVATION_CONSUMPTION_SCHEMA,
            "execution_hash": authorization.execution_hash,
            "campaign_cost_control_hash": (authorization.campaign_cost_control_hash),
            "schedule_row_id": authorization.schedule_row_id,
            "run_id": authorization.run_id,
            "journal_path": authorization.journal_path,
            "journal_hash": authorization.journal_hash,
            "reservation_event_hash": authorization.reservation_event_hash,
            "consumed_at": consumption["consumed_at"],
            "state_consumption_content_hash": consumption["content_hash"],
        }
        marker["content_hash"] = sha256_text(canonical_json(marker))
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with marker_path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical_json(marker) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise ContractError("D-087 campaign cost reservation was already consumed") from exc

    @staticmethod
    def _live_plan_unchanged(authorization: LiveExecutionAuthorization) -> bool:
        try:
            return sha256_bytes(Path(authorization.plan_path).read_bytes()) == (
                authorization.plan_hash
            )
        except OSError:
            return False

    @staticmethod
    def _live_plan_matches_manifest(
        manifest: RunManifest,
        authorization: LiveExecutionAuthorization,
        *,
        plan: dict[str, Any] | None = None,
        runner_root: Path | None = None,
    ) -> bool:
        """Bind the complete hash-approved plan at the paid-call boundary."""

        if plan is None:
            try:
                plan = _load_live_execution_plan(authorization)
            except ContractError:
                return False
        if not isinstance(plan, dict):
            return False
        from patchloop.evals.live_verifier_registry import live_verifier_registry

        registry_decision = live_verifier_registry().verify_manifest(
            plan=plan,
            manifest=manifest,
            authorization_plan_path=authorization.plan_path,
            authorization_plan_hash=authorization.plan_hash,
            repository=repository_root(),
            runner_root=runner_root,
        )
        if registry_decision.handled:
            return registry_decision.accepted
        runtime_contract = plan.get("runtime_contract")
        corrective = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_CORRECTIVE_PILOT
        )
        saturation = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_SATURATION_PILOT
        )
        review_evidence = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_REVIEW_EVIDENCE_PILOT
        )
        coverage_review = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REVIEW_PILOT
        )
        coverage_rejection = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose
            == ExperimentPurpose.MEMORY_DEVELOPMENT_NO_MEMORY_COVERAGE_REJECTION_PILOT
        )
        generic_baseline_readiness = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS
        )
        workflow_completion_probe = bool(
            manifest.experiment is not None
            and manifest.experiment.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        )
        frozen_comparison_live = bool(
            AgentRunner._is_frozen_comparison_runtime_manifest(manifest)
            and manifest.experiment is not None
            and manifest.experiment.purpose != ExperimentPurpose.CORE
        )
        condition_neutral_v2_live = bool(
            AgentRunner._is_condition_neutral_runtime_v2_manifest(manifest)
        )
        ac_fixed_bundle_live = bool(AgentRunner._is_ac_fixed_bundle_readiness_manifest(manifest))
        if not any(
            (
                generic_baseline_readiness,
                workflow_completion_probe,
                frozen_comparison_live,
                condition_neutral_v2_live,
                ac_fixed_bundle_live,
                corrective,
                saturation,
                review_evidence,
                coverage_review,
                coverage_rejection,
            )
        ):
            return runtime_contract is None
        try:
            # Keep start/resume on the same complete suite, task, schedule,
            # model, budget, pricing, review and runtime comparison used by
            # post-run qualification. This import is local to avoid making
            # the agent runner depend on evaluation modules at import time.
            from patchloop.evals.qualification import (
                _execution_plan_matches,
            )

            return _execution_plan_matches(
                plan=plan,
                manifest=manifest,
            )
        except Exception:
            return False

    def _prepare_public_review_base_provenance(
        self,
        *,
        manifest: RunManifest,
        task: PublicTask,
        workspace: Path,
    ) -> Artifact | None:
        """Build once, then validate and reuse V10/V11 base-anchor provenance."""

        if manifest.context_policy_version not in {
            "phase-evidence-v10",
            "phase-evidence-v11",
        }:
            return None
        contract = manifest.public_review_contract
        if contract is None:
            raise ContractError("V10/V11 requires a public review contract for base provenance")
        expected = build_public_review_base_provenance(
            contract,
            repository_url=task.repository.url,
            base_commit=task.repository.base_commit,
            read_base_file=lambda path: self.workspaces.read_base_file(
                workspace,
                path,
            ),
        )
        events = self.state.list_events(manifest.run_id)
        if not events:
            return self.artifacts.put_json(expected)
        started = [event for event in events if event.type == EventType.RUN_STARTED]
        if (
            len(started) != 1
            or started[0].actor != "runner"
            or started[0].payload.get("task_id") != manifest.task_id
        ):
            raise RecoveryError("V10/V11 run lacks one authoritative base provenance source")
        try:
            artifact = Artifact.model_validate(
                started[0].payload.get("public_review_base_provenance_artifact")
            )
            document = json.loads(self.artifacts.read_bytes(artifact).decode("utf-8"))
            validate_public_review_base_provenance_document(
                document,
                contract=contract,
                repository_url=task.repository.url,
                base_commit=task.repository.base_commit,
            )
        except (UnicodeDecodeError, ValueError, RecoveryError, ContractError) as exc:
            raise RecoveryError("V10/V11 public review base provenance is invalid") from exc
        if document != expected:
            raise RecoveryError("V10/V11 public review base provenance does not match Git HEAD")
        return artifact

    def _execute(
        self,
        package: TaskPackage,
        workspace: Path,
        manifest: RunManifest,
        model: str,
        *,
        public_review_base_provenance: Artifact | None = None,
        worker_claim: dict[str, Any] | None = None,
        evaluator_v2_authority: EvaluatorV2QualificationAuthority | None = None,
        row_execution_authorization: RowExecutionAuthorization | None = None,
    ) -> dict[str, Any]:
        task_dir = package.root
        system_prompt, tool_schemas = self._runtime_contract(manifest)
        if manifest.context_policy_version == "phase-evidence-v11" and worker_claim is None:
            raise RecoveryError("phase-evidence-v11 requires an active worker claim")
        sandbox = (
            self._docker_sandbox(package)
            if manifest.sandbox_backend == "docker"
            else LocalSandbox()
        )
        if (
            package.environment is not None
            and manifest.evaluator_image_digest != package.environment.image_digest
        ):
            raise ContractError("run manifest evaluator image does not match the task environment")
        if (
            manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}
            and manifest.probe_image_digest is not None
            and (
                not isinstance(sandbox, DockerSandbox)
                or sandbox.probe_image_identity() != manifest.probe_image_digest
            )
        ):
            raise ContractError(
                "run manifest probe image does not match the dedicated "
                "self-validation sandbox image"
            )
        gateway_sandbox = (
            TimeoutOnceSandbox(sandbox) if manifest.fault.type == "test-timeout" else sandbox
        )
        gateway = ToolGateway(
            run_id=manifest.run_id,
            workspace=workspace,
            task=package.public,
            state=self.state,
            artifacts=self.artifacts,
            sandbox=gateway_sandbox,
            tool_schema_version=manifest.tool_schema_version,
            context_policy_version=manifest.context_policy_version,
            fault=manifest.fault,
        )
        existing_events = self.state.list_events(manifest.run_id)
        if existing_events:
            self._validate_generic_baseline_runtime_resume_contract(
                manifest=manifest,
                events=existing_events,
                system_prompt=system_prompt,
                tool_schemas=tool_schemas,
            )
        if (
            manifest.context_policy_version in {"phase-evidence-v10", "phase-evidence-v11"}
            and public_review_base_provenance is None
        ):
            raise ContractError("V10/V11 execution requires public review base provenance")
        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        recovered_initial_phase: Phase | None = None
        if existing_events:
            if checkpoint is None:
                recovered_initial_phase = self._recover_initial_prefix(
                    manifest,
                    workspace,
                    existing_events,
                )
            else:
                self._reconcile_workspace_head(checkpoint, workspace)
                causal_trigger = gateway.reconcile_causal_mutation_baseline_restore()
                if causal_trigger is not None and (
                    checkpoint.through_sequence < causal_trigger.restored_event_sequence
                    or checkpoint.worktree_diff_hash != causal_trigger.restored_baseline_diff_hash
                ):
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        self._phase_after_checkpoint(checkpoint),
                        self._usage(manifest.run_id),
                        task=package.public,
                    )
                recovered_patch = gateway.reconcile_interrupted_patch(checkpoint)
                recovered_tool: tuple[str, ToolResult] | None = None
                if recovered_patch is not None:
                    recovered_tool = ("apply_patch", recovered_patch)
                else:
                    # Only a prepared patch may legitimately move the
                    # worktree away from the last checkpoint. Validate the
                    # old durable boundary before replaying a read/check
                    # action or promoting any event suffix into a checkpoint.
                    self._reconcile_checkpoint_workspace(
                        checkpoint,
                        workspace,
                    )
                    recovered_tool = gateway.reconcile_interrupted_action(checkpoint)
                if recovered_tool is not None:
                    tool_name, recovered_result = recovered_tool
                    if (
                        recovered_result.status == "failed"
                        and recovered_result.output.get("fatal") is True
                    ):
                        raise RecoveryError(
                            recovered_result.error_message or "interrupted tool recovery failed"
                        )
                    phase = self._phase_after_checkpoint(checkpoint)
                    phase = self._phase_after_tool(
                        manifest.run_id,
                        phase,
                        tool_name,
                        recovered_result,
                        package.public,
                        workspace,
                    )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        self._usage(manifest.run_id),
                        recovered_result,
                        task=package.public,
                    )
                else:
                    phase = self._phase_after_checkpoint(checkpoint)
                    suffix_events = [
                        event
                        for event in self.state.list_events(manifest.run_id)
                        if event.sequence > checkpoint.through_sequence
                        and event.type != EventType.CHECKPOINT_SAVED
                    ]
                    if suffix_events:
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            self._usage(manifest.run_id),
                            task=package.public,
                        )
                    else:
                        self._ensure_checkpoint_event(checkpoint)
                recovered_barriers = gateway.reconcile_same_turn_barriers()
                if recovered_barriers:
                    checkpoint = self.state.latest_checkpoint(manifest.run_id)
                    if checkpoint is None:
                        raise RecoveryError("same-turn barrier recovery lacks a durable checkpoint")
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        self._phase_after_checkpoint(checkpoint),
                        self._usage(manifest.run_id),
                        task=package.public,
                    )
                self._reconcile_workspace(manifest, workspace)
        else:
            generic_runtime_document = self._generic_baseline_runtime_evidence_document(
                manifest=manifest,
                system_prompt=system_prompt,
                tool_schemas=tool_schemas,
            )
            runtime_contract_metadata: dict[str, Any] = {}
            if generic_runtime_document is None and manifest.context_policy_version in {
                "phase-evidence-v8",
                "phase-evidence-v9",
                "phase-evidence-v10",
                "phase-evidence-v11",
            }:
                runtime_contract_metadata = {
                    "schema_version": (
                        "corrective-runtime-contract-v5"
                        if manifest.context_policy_version == "phase-evidence-v11"
                        else (
                            "corrective-runtime-contract-v4"
                            if manifest.context_policy_version == "phase-evidence-v10"
                            else (
                                "corrective-runtime-contract-v3"
                                if manifest.context_policy_version == "phase-evidence-v9"
                                else "corrective-runtime-contract-v2"
                            )
                        )
                    )
                }
            elif generic_runtime_document is None and manifest.context_policy_version in {
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
            }:
                lean_dependencies = load_lean_harness_dependencies(repository_root())
                runtime_contract_metadata = {
                    "schema_version": "lean-harness-runtime-contract-v1",
                    "preregistration_id": (lean_dependencies.preregistration.preregistration_id),
                    "preregistration_content_hash": (
                        lean_dependencies.preregistration.content_hash
                    ),
                    "runtime_contract": (
                        lean_dependencies.preregistration.runtime_contract.model_dump(mode="json")
                    ),
                }
            runtime_contract = self.artifacts.put_json(
                generic_runtime_document
                or {
                    **runtime_contract_metadata,
                    "system_prompt": system_prompt,
                    "tools": tool_schemas,
                    "tool_schema_version": manifest.tool_schema_version,
                    "context_policy_version": manifest.context_policy_version,
                }
            )
            self.state.append_event(
                manifest.run_id,
                EventType.RUN_STARTED,
                actor="runner",
                payload={
                    "task_id": manifest.task_id,
                    "artifact_id": runtime_contract.artifact_id,
                    "artifact_path": runtime_contract.path,
                    "artifact_role": "runtime-contract",
                    **(
                        {"runtime_contract_artifact": (runtime_contract.model_dump(mode="json"))}
                        if generic_runtime_document is not None
                        or manifest.tool_schema_version
                        in {
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
                        else {}
                    ),
                    **(
                        {
                            "public_review_base_provenance_artifact": (
                                public_review_base_provenance.model_dump(mode="json")
                            )
                        }
                        if public_review_base_provenance is not None
                        else {}
                    ),
                },
            )
            if generic_runtime_document is not None:
                self._validate_generic_baseline_runtime_resume_contract(
                    manifest=manifest,
                    events=self.state.list_events(manifest.run_id),
                    system_prompt=system_prompt,
                    tool_schemas=tool_schemas,
                )
            if manifest.fault.type in {"context-reset", "test-timeout"}:
                self.state.append_event(
                    manifest.run_id,
                    EventType.FAULT_INJECTED,
                    actor="fault-injector",
                    payload={"fault": manifest.fault.type},
                )
        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        phase = checkpoint.phase if checkpoint else recovered_initial_phase or Phase.INTAKE
        if phase == Phase.INTAKE:
            phase = self._transition(manifest.run_id, phase, Phase.REPRODUCE)
        if checkpoint is None:
            checkpoint = self._checkpoint(
                manifest,
                workspace,
                phase,
                task=package.public,
            )

        usage = self._usage(manifest.run_id)
        try:
            if manifest.context_policy_version in {"phase-evidence-v37", "phase-evidence-v38"}:
                assert_input_token_count_recoverable(
                    manifest.run_id, self.state.list_events(manifest.run_id)
                )
            phase, checkpoint, recovered_submission = self._reconcile_submission_recovery(
                manifest=manifest,
                task=package.public,
                workspace=workspace,
                phase=phase,
                usage=usage,
            )
            usage = self._usage(manifest.run_id)
            if recovered_submission is not None:
                return self._evaluate(
                    task_dir,
                    workspace,
                    manifest,
                    sandbox,
                    usage,
                    evaluator_v2_authority=evaluator_v2_authority,
                )
            adapter = self._model_adapter(
                model,
                manifest,
                self._completed_tools(manifest.run_id),
                bool(package.public.probe_profiles),
            )
            while True:
                if (
                    manifest.context_policy_version
                    in {
                        "phase-evidence-v9",
                        "phase-evidence-v10",
                        "phase-evidence-v11",
                    }
                    and self._review_rejection_count(manifest.run_id)
                    > _MAX_RECOVERABLE_REVIEW_REJECTIONS
                ):
                    raise SubmissionProtocolError(
                        "structured review evidence was rejected three times"
                    )
                if manifest.context_policy_version not in {
                    "phase-evidence-v3",
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
                }:
                    self._assert_budget(manifest, usage)
                events = self.state.list_events(manifest.run_id)
                if manifest.context_policy_version in {
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
                    before_restore_hash = WorkspaceManager.diff_summary(workspace).patch_hash
                    restore_evidence = diff_bound_evidence(
                        package.public,
                        events,
                        before_restore_hash,
                        phase=phase,
                        completion_driven=True,
                    )
                    causal_trigger = gateway.activate_causal_mutation_baseline_restore(
                        restore_evidence
                    )
                    after_restore_hash = WorkspaceManager.diff_summary(workspace).patch_hash
                    if after_restore_hash != before_restore_hash:
                        if causal_trigger is None:
                            raise RecoveryError("causal restore changed worktree without a trigger")
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            usage,
                            task=package.public,
                        )
                    events = self.state.list_events(manifest.run_id)
                fixed_delivery: FixedMemoryDelivery | None = None
                if manifest.memory_policy_version == FIXED_BUNDLE_POLICY_VERSION:
                    fixed_runtime_pair = (
                        manifest.tool_schema_version,
                        manifest.context_policy_version,
                    )
                    if fixed_runtime_pair not in {
                        ("v2", "phase-evidence-v5"),
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
                        raise ContractError(
                            "fixed D-110 bundle requires the exact v2/v5, v7/v12, "
                            "v8/v13, v9/v13, v9/v14, v10/v15, v10/v16, or "
                            "v11/v17, v12/v18, v13/v19, v14/v20, v15/v21, "
                            "v16/v22, v17/v23, v18/v24, v19/v25, v20/v26, "
                            "v21/v27, v22/v28, v23/v29, v24/v30, v25/v31, "
                            "v25/v32, v26/v33, v26/v34, v26/v35, or v27/v36 runtime"
                        )
                    fixed_delivery = build_fixed_memory_delivery(
                        condition=manifest.memory.condition,
                        token_budget=manifest.memory.max_context_tokens,
                    )
                    if (
                        manifest.memory.index_version != fixed_delivery.evidence.index_version
                        or manifest.memory.index_hash != fixed_delivery.evidence.index_content_hash
                    ):
                        raise ContractError("fixed D-110 manifest differs from its delivery inputs")
                    memory_text = fixed_delivery.text
                    retrieval = None
                else:
                    memory_text, retrieval = retrieve_memory(
                        run_id=manifest.run_id,
                        query=(
                            package.public.issue.title
                            + "\n"
                            + package.public.issue.description
                            + "\n"
                            + " ".join(package.public.tags)
                        ),
                        phase=phase,
                        condition=manifest.memory.condition,
                        token_budget=manifest.memory.max_context_tokens,
                    )
                if retrieval is not None:
                    retrieval_artifact = self.artifacts.put_json(retrieval.model_dump(mode="json"))
                    self.state.append_event(
                        manifest.run_id,
                        EventType.MEMORY_RETRIEVED,
                        actor="memory-retriever",
                        payload={
                            "index_version": retrieval.index_version,
                            "selected_memory_ids": retrieval.selected_memory_ids,
                            "no_match": retrieval.no_match,
                            "artifact_id": retrieval_artifact.artifact_id,
                            "artifact_path": retrieval_artifact.path,
                        },
                    )
                if manifest.context_policy_version in {
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
                }:
                    # V5 binds the ledger to the exact durable prefix. A
                    # MemoryRetrieved event appended above must therefore be
                    # included before ContextBuilt is emitted.
                    events = self.state.list_events(manifest.run_id)
                context_build_policy_version = (
                    "phase-evidence-v5"
                    if manifest.context_policy_version
                    in {
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
                    else manifest.context_policy_version
                )
                built_context = build_context_with_evidence(
                    package.public,
                    events,
                    checkpoint,
                    memory_text,
                    policy_version=context_build_policy_version,
                    artifact_store=self.artifacts,
                    budget=manifest.budget,
                    max_output_tokens=manifest.model.max_output_tokens,
                    public_review_contract=(manifest.public_review_contract),
                    model_provider=manifest.model.provider,
                )
                context = built_context.rendered
                coverage_rejection_feedback = (
                    json.loads(context).get("coverage_rejection_feedback")
                    if manifest.context_policy_version == "phase-evidence-v11"
                    else None
                )
                if isinstance(adapter, OpenAIResponsesAdapter):
                    request_body = adapter.request_payload(
                        context,
                        tool_schemas,
                        system_prompt=system_prompt,
                    )
                    request_endpoint = "/v1/responses"
                else:
                    request_body = {
                        "model": manifest.model.model_id,
                        "system_prompt": system_prompt,
                        "context": context,
                        "tools": tool_schemas,
                    }
                    request_endpoint = None
                request_body_hash = sha256_text(canonical_json(request_body))
                fixed_memory_request_evidence = None
                lean_request_evidence = None
                lean_request_context: str | None = None
                lean_input_count_calls = 0
                lean_input_count_duration_ms = 0
                provider_terminal_attribution: ProviderTerminalAttribution | None = None
                request_tool_schemas = tool_schemas
                if fixed_delivery is not None:
                    try:
                        rendered_payload = json.loads(context)
                    except json.JSONDecodeError as exc:
                        raise ContractError("fixed D-110 bundle requires a JSON context") from exc
                    expected_selected_memory = fixed_delivery.text or None
                    if rendered_payload.get("selected_memory") != expected_selected_memory:
                        raise ContractError(
                            "fixed D-110 delivery differs from the rendered context"
                        )
                    normalized_payload = dict(rendered_payload)
                    normalized_payload["selected_memory"] = None
                    normalized_context_build = built_context
                    if fixed_delivery.evidence.selected_memory_present:
                        normalized_context_build = build_context_with_evidence(
                            package.public,
                            events,
                            checkpoint,
                            "",
                            policy_version=context_build_policy_version,
                            artifact_store=self.artifacts,
                            budget=manifest.budget,
                            max_output_tokens=manifest.model.max_output_tokens,
                            public_review_contract=manifest.public_review_contract,
                            model_provider=manifest.model.provider,
                        )
                        normalized_context = normalized_context_build.rendered
                        if json.loads(normalized_context) != normalized_payload:
                            raise ContractError("fixed D-110 treatment changes non-memory context")
                    if manifest.context_policy_version in {
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
                    }:
                        current_diff_hash = WorkspaceManager.diff_summary(workspace).patch_hash
                        phase_evidence = diff_bound_evidence(
                            package.public,
                            events,
                            current_diff_hash,
                            presented_tool_results=built_context.evidence["tool_results"],
                            phase=phase,
                            completion_driven=(
                                manifest.context_policy_version
                                in {
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
                            ),
                        )

                        def lean_provider_request_builder(
                            selected_context: str,
                            selected_tools: tuple[dict[str, Any], ...],
                            selected_max_output_tokens: int,
                        ) -> dict[str, Any]:
                            if not isinstance(adapter, OpenAIResponsesAdapter):
                                raise ContractError("Lean live request requires OpenAI adapter")
                            body = adapter.request_payload(
                                selected_context,
                                list(selected_tools),
                                system_prompt=system_prompt,
                            )
                            body["max_output_tokens"] = selected_max_output_tokens
                            return body

                        def lean_provider_input_token_counter(
                            body: dict[str, Any],
                        ) -> int:
                            nonlocal lean_input_count_calls, lean_input_count_duration_ms
                            nonlocal usage
                            if not isinstance(adapter, OpenAIResponsesAdapter):
                                raise ContractError("Lean live count requires OpenAI adapter")
                            # R24 integration begin: production-count-gate
                            from patchloop.agent.provider_request_gate import (
                                admit_request,
                                request_admission_required,
                            )

                            if request_admission_required(manifest, row_execution_authorization):
                                admit_request(
                                    manifest,
                                    row_execution_authorization,
                                    body,
                                    adapter,
                                    stop_before_count=False,
                                )
                            # R24 integration end: production-count-gate
                            if manifest.context_policy_version in {
                                "phase-evidence-v37",
                                "phase-evidence-v38",
                            }:
                                adapter.admit_request_v3(body)
                                if manifest.model.provider == "openai":
                                    _provider_input_count_boundary(
                                        manifest, row_execution_authorization
                                    )
                                try:
                                    return counted_request_with_receipts(
                                        state=self.state,
                                        run_id=manifest.run_id,
                                        request=body,
                                        count=adapter.count_input_tokens_v3,
                                    )
                                finally:
                                    usage = self._usage(manifest.run_id)
                            count_started = time.monotonic()
                            counted = (
                                adapter.count_input_tokens_v2(body)
                                if manifest.context_policy_version
                                in {
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
                                else adapter.count_input_tokens(body)
                            )
                            lean_input_count_duration_ms += int(
                                (time.monotonic() - count_started) * 1000
                            )
                            lean_input_count_calls += 1
                            return counted

                        def load_plan_gate_request_artifact(
                            artifact_path: str,
                            artifact_hash: str,
                        ) -> dict[str, Any]:
                            hex_digest = artifact_hash.removeprefix("sha256:")
                            if len(hex_digest) != 64 or not re.fullmatch(
                                r"[0-9a-f]{64}", hex_digest
                            ):
                                raise RecoveryError(
                                    "plan-gate request artifact identity is invalid"
                                )
                            expected = (
                                self.artifacts.objects / hex_digest[:2] / hex_digest[2:]
                            ).resolve()
                            try:
                                actual = Path(artifact_path).resolve()
                                content = actual.read_bytes()
                            except OSError as exc:
                                raise RecoveryError(
                                    "plan-gate request artifact is unavailable"
                                ) from exc
                            if actual != expected or sha256_bytes(content) != artifact_hash:
                                raise RecoveryError("plan-gate request artifact binding differs")
                            try:
                                payload = json.loads(content)
                            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                                raise RecoveryError(
                                    "plan-gate request artifact is not canonical JSON"
                                ) from exc
                            if not isinstance(payload, dict):
                                raise RecoveryError("plan-gate request artifact must be an object")
                            return payload

                        recovered_plan_gate_pins = (
                            recover_plan_gate_readiness_pins(
                                run_id=manifest.run_id,
                                events=events,
                                request_artifact_loader=load_plan_gate_request_artifact,
                            )
                            if manifest.context_policy_version
                            in {
                                "phase-evidence-v31",
                                "phase-evidence-v32",
                                "phase-evidence-v33",
                                "phase-evidence-v34",
                                "phase-evidence-v35",
                                "phase-evidence-v36",
                                "phase-evidence-v37",
                                "phase-evidence-v38",
                            }
                            else ()
                        )

                        lean_request = assemble_lean_harness_request(
                            dependencies=load_lean_harness_dependencies(repository_root()),
                            built_context=built_context,
                            normalized_no_memory_context=normalized_context_build,
                            base_tool_schemas=tool_schemas,
                            phase_evidence=phase_evidence,
                            events=events,
                            usage=usage,
                            budget=manifest.budget,
                            model_id=manifest.model.model_id,
                            system_prompt=system_prompt,
                            configured_max_output_tokens=manifest.model.max_output_tokens,
                            memory_delivery_evidence_sha256=fixed_delivery.evidence_sha256,
                            runtime_policy_version={
                                "phase-evidence-v12": LEAN_RUNTIME_POLICY_VERSION,
                                "phase-evidence-v13": (
                                    LEAN_RUNTIME_POLICY_VERSION_V3
                                    if manifest.tool_schema_version == "v9"
                                    else LEAN_RUNTIME_POLICY_VERSION_V2
                                ),
                                "phase-evidence-v14": LEAN_RUNTIME_POLICY_VERSION_V4,
                                "phase-evidence-v15": LEAN_RUNTIME_POLICY_VERSION_V5,
                                "phase-evidence-v16": LEAN_RUNTIME_POLICY_VERSION_V6,
                                "phase-evidence-v17": LEAN_RUNTIME_POLICY_VERSION_V7,
                                "phase-evidence-v18": LEAN_RUNTIME_POLICY_VERSION_V8,
                                "phase-evidence-v19": LEAN_RUNTIME_POLICY_VERSION_V9,
                                "phase-evidence-v20": LEAN_RUNTIME_POLICY_VERSION_V10,
                                "phase-evidence-v21": LEAN_RUNTIME_POLICY_VERSION_V11,
                                "phase-evidence-v22": LEAN_RUNTIME_POLICY_VERSION_V12,
                                "phase-evidence-v23": LEAN_RUNTIME_POLICY_VERSION_V13,
                                "phase-evidence-v24": LEAN_RUNTIME_POLICY_VERSION_V14,
                                "phase-evidence-v25": LEAN_RUNTIME_POLICY_VERSION_V15,
                                "phase-evidence-v26": LEAN_RUNTIME_POLICY_VERSION_V16,
                                "phase-evidence-v27": LEAN_RUNTIME_POLICY_VERSION_V17,
                                "phase-evidence-v28": LEAN_RUNTIME_POLICY_VERSION_V18,
                                "phase-evidence-v29": LEAN_RUNTIME_POLICY_VERSION_V19,
                                "phase-evidence-v30": LEAN_RUNTIME_POLICY_VERSION_V20,
                                "phase-evidence-v31": LEAN_RUNTIME_POLICY_VERSION_V21,
                                "phase-evidence-v32": LEAN_RUNTIME_POLICY_VERSION_V22,
                                "phase-evidence-v33": LEAN_RUNTIME_POLICY_VERSION_V23,
                                "phase-evidence-v34": LEAN_RUNTIME_POLICY_VERSION_V24,
                                "phase-evidence-v35": LEAN_RUNTIME_POLICY_VERSION_V25,
                                "phase-evidence-v36": LEAN_RUNTIME_POLICY_VERSION_V26,
                                "phase-evidence-v37": LEAN_RUNTIME_POLICY_VERSION_V27,
                                "phase-evidence-v38": LEAN_RUNTIME_POLICY_VERSION_V28,
                            }[manifest.context_policy_version],
                            task=(
                                package.public
                                if manifest.context_policy_version
                                in {
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
                                else None
                            ),
                            provider_request_builder=(
                                lean_provider_request_builder
                                if isinstance(adapter, OpenAIResponsesAdapter)
                                else None
                            ),
                            provider_input_token_counter=(
                                lean_provider_input_token_counter
                                if isinstance(adapter, OpenAIResponsesAdapter)
                                else None
                            ),
                            live_input_count_method=(
                                "openai-input-token-count-v2-parallel-bound"
                                if manifest.context_policy_version
                                in {
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
                                and isinstance(adapter, OpenAIResponsesAdapter)
                                else "openai-input-token-count-v1"
                            ),
                            recovered_plan_gate_pins=recovered_plan_gate_pins,
                        )
                        context = lean_request.context
                        lean_request_context = lean_request.context
                        request_tool_schemas = list(lean_request.tool_schemas)
                        request_body = lean_request.request_body
                        request_body_hash = lean_request.evidence.request_body_hash
                        normalized_request_body_hash = (
                            lean_request.evidence.normalized_no_memory_request_body_sha256
                        )
                        lean_request_evidence = lean_request.evidence
                    else:
                        if fixed_delivery.evidence.selected_memory_present:
                            if isinstance(adapter, OpenAIResponsesAdapter):
                                normalized_request_body = adapter.request_payload(
                                    normalized_context,
                                    tool_schemas,
                                    system_prompt=system_prompt,
                                )
                            else:
                                normalized_request_body = {
                                    "model": manifest.model.model_id,
                                    "system_prompt": system_prompt,
                                    "context": normalized_context,
                                    "tools": tool_schemas,
                                }
                            normalized_request_body_hash = sha256_text(
                                canonical_json(normalized_request_body)
                            )
                        else:
                            normalized_request_body_hash = request_body_hash
                    fixed_memory_request_evidence = FixedMemoryRequestEvidence(
                        delivery=fixed_delivery.evidence,
                        delivery_evidence_sha256=fixed_delivery.evidence_sha256,
                        request_body_sha256=request_body_hash,
                        normalized_no_memory_request_body_sha256=(normalized_request_body_hash),
                    )
                worker_claim_evidence = (
                    {
                        "schema_version": "worker-claim-evidence-v1",
                        **worker_claim,
                    }
                    if manifest.context_policy_version == "phase-evidence-v11"
                    and worker_claim is not None
                    else None
                )
                request_artifact_payload = {
                    "schema_version": "model-request-evidence-v1",
                    "provider": manifest.model.provider,
                    "endpoint": request_endpoint,
                    "request_body": request_body,
                    "request_body_hash": request_body_hash,
                    "context_build": built_context.evidence,
                    **(
                        {
                            "fixed_memory_delivery": (
                                fixed_memory_request_evidence.model_dump(mode="json")
                            )
                        }
                        if fixed_memory_request_evidence is not None
                        else {}
                    ),
                    **(
                        {"lean_harness_request": lean_request_evidence.model_dump(mode="json")}
                        if lean_request_evidence is not None
                        else {}
                    ),
                    **(
                        {"worker_claim": worker_claim_evidence}
                        if worker_claim_evidence is not None
                        else {}
                    ),
                }
                if fixed_memory_request_evidence is not None:
                    validate_fixed_memory_request_artifact(request_artifact_payload)
                if lean_request_evidence is not None:
                    validate_persisted_lean_harness_request(request_artifact_payload)
                request_artifact = self.artifacts.put_json(request_artifact_payload)
                self.state.append_event(
                    manifest.run_id,
                    EventType.CONTEXT_BUILT,
                    actor="context-builder",
                    payload={
                        "context_hash": (
                            getattr(
                                lean_request_evidence,
                                "recovery_context_hash",
                                lean_request_evidence.context_compaction.projected_context_hash,
                            )
                            if lean_request_evidence is not None
                            else built_context.content_hash
                        ),
                        "context_characters": (
                            len(lean_request_context)
                            if lean_request_context is not None
                            else (
                                lean_request_evidence.context_compaction.projected_context_characters
                            )
                            if lean_request_evidence is not None
                            else built_context.evidence["rendered_characters"]
                        ),
                        "context_bytes": (
                            len(lean_request_context.encode("utf-8"))
                            if lean_request_context is not None
                            else lean_request_evidence.context_compaction.projected_context_bytes
                            if lean_request_evidence is not None
                            else built_context.evidence["rendered_bytes"]
                        ),
                        "eligible_event_count": built_context.evidence["events"]["eligible_count"],
                        "included_event_count": built_context.evidence["events"]["included_count"],
                        "omitted_event_count": built_context.evidence["events"]["omitted_count"],
                        "truncated_tool_result_count": sum(
                            bool(item["truncated"])
                            for item in built_context.evidence["tool_results"]
                        ),
                        "request_body_hash": request_body_hash,
                        "artifact_id": request_artifact.artifact_id,
                        "artifact_path": request_artifact.path,
                        "artifact_role": "model-request-evidence",
                        "provider_state_used": False,
                        **(
                            {
                                "lean_harness_request_evidence_hash": (
                                    lean_request_evidence.content_hash
                                ),
                                "lean_harness_requested_input_tokens": (
                                    lean_request_evidence.requested_input_tokens
                                ),
                                "lean_harness_effective_max_output_tokens": (
                                    lean_request_evidence.effective_max_output_tokens
                                ),
                                "lean_harness_phase_tool_surface_hash": (
                                    lean_request_evidence.phase_tool_surface_hash
                                ),
                                **(
                                    {
                                        "lean_incomplete_recovery_mode": (
                                            lean_request_evidence.incomplete_recovery.mode
                                        ),
                                        "lean_incomplete_recovery_hash": (
                                            lean_request_evidence.incomplete_recovery_hash
                                        ),
                                    }
                                    if hasattr(
                                        lean_request_evidence,
                                        "incomplete_recovery",
                                    )
                                    else {}
                                ),
                            }
                            if lean_request_evidence is not None
                            else {}
                        ),
                        **(
                            {
                                "memory_delivery_policy_version": (FIXED_BUNDLE_POLICY_VERSION),
                                "memory_delivery_evidence_sha256": (
                                    fixed_memory_request_evidence.delivery_evidence_sha256
                                ),
                                "memory_delivery_entry_count": (
                                    fixed_memory_request_evidence.delivery.entry_count
                                ),
                                "memory_delivery_bundle_sha256": (
                                    fixed_memory_request_evidence.delivery.bundle_sha256
                                ),
                                "normalized_no_memory_request_body_sha256": (
                                    fixed_memory_request_evidence.normalized_no_memory_request_body_sha256
                                ),
                            }
                            if fixed_memory_request_evidence is not None
                            else {}
                        ),
                        **(
                            {"worker_claim": worker_claim_evidence}
                            if worker_claim_evidence is not None
                            else {}
                        ),
                        **(
                            {
                                "investigation_ledger_hash": (
                                    built_context.evidence["investigation_ledger"]["content_hash"]
                                ),
                                "investigation_source_through_sequence": (
                                    built_context.evidence["investigation_ledger"][
                                        "source_through_sequence"
                                    ]
                                ),
                                "investigation_no_progress_streak": (
                                    built_context.evidence["investigation_ledger"][
                                        "no_progress_streak"
                                    ]
                                ),
                                "investigation_exploration_admitted": (
                                    built_context.evidence["investigation_ledger"][
                                        "exploration_admitted"
                                    ]
                                ),
                                **(
                                    {
                                        "investigation_tail_block_reasons": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_block_reasons"
                                            ]
                                        ),
                                        "investigation_tail_remaining_tokens": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_remaining_tokens"
                                            ]
                                        ),
                                        "investigation_tail_observation_count": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_observation_count"
                                            ]
                                        ),
                                        "investigation_tail_max_observed_input_tokens": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_max_observed_input_tokens"
                                            ]
                                        ),
                                        "investigation_tail_max_positive_growth": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_max_positive_growth"
                                            ]
                                        ),
                                        "investigation_tail_projected_next_input_tokens": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_projected_next_input_tokens"
                                            ]
                                        ),
                                        "investigation_tail_projected_model_turns": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_projected_model_turns"
                                            ]
                                        ),
                                        "investigation_tail_reserved_tokens": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_reserved_tokens"
                                            ]
                                        ),
                                        "investigation_tail_max_output_tokens": (
                                            built_context.evidence["investigation_ledger"][
                                                "tail_max_output_tokens"
                                            ]
                                        ),
                                    }
                                    if manifest.context_policy_version
                                    in {
                                        "phase-evidence-v5",
                                        "phase-evidence-v6",
                                        "phase-evidence-v7",
                                        "phase-evidence-v8",
                                        "phase-evidence-v9",
                                        "phase-evidence-v10",
                                        "phase-evidence-v11",
                                    }
                                    else {}
                                ),
                                **(
                                    {
                                        "probe_ledger_hash": (
                                            built_context.evidence["probe_ledger"]["content_hash"]
                                        ),
                                        "probe_ledger_source_through_sequence": (
                                            built_context.evidence["probe_ledger"][
                                                "source_through_sequence"
                                            ]
                                        ),
                                        "probe_ledger_entry_count": (
                                            built_context.evidence["probe_ledger"]["entry_count"]
                                        ),
                                    }
                                    if manifest.context_policy_version
                                    in {
                                        "phase-evidence-v6",
                                        "phase-evidence-v7",
                                        "phase-evidence-v8",
                                        "phase-evidence-v9",
                                        "phase-evidence-v10",
                                        "phase-evidence-v11",
                                    }
                                    else {}
                                ),
                            }
                            if manifest.context_policy_version
                            in {
                                "phase-evidence-v4",
                                "phase-evidence-v5",
                                "phase-evidence-v6",
                                "phase-evidence-v7",
                                "phase-evidence-v8",
                                "phase-evidence-v9",
                                "phase-evidence-v10",
                                "phase-evidence-v11",
                            }
                            else {}
                        ),
                        **(
                            {
                                "investigation_read_search_admitted": (
                                    built_context.evidence["read_search_policy"]["admitted"]
                                ),
                                "investigation_read_search_reason_codes": (
                                    built_context.evidence["read_search_policy"]["reason_codes"]
                                ),
                                "investigation_semantic_replay_count": (
                                    built_context.evidence["read_search_policy"][
                                        "semantic_replay_count"
                                    ]
                                ),
                                "investigation_semantic_replay_threshold": (
                                    built_context.evidence["read_search_policy"][
                                        "semantic_replay_threshold"
                                    ]
                                ),
                                "investigation_saturation_mutation_epoch_sequence": (
                                    built_context.evidence["read_search_policy"][
                                        "mutation_epoch_sequence"
                                    ]
                                ),
                            }
                            if manifest.context_policy_version
                            in {
                                "phase-evidence-v8",
                                "phase-evidence-v9",
                                "phase-evidence-v10",
                                "phase-evidence-v11",
                            }
                            else {}
                        ),
                        **(
                            {
                                "review_evidence_pinning_active": (
                                    built_context.evidence["review_evidence"]["pinning_active"]
                                ),
                                "review_evidence_worktree_diff_hash": (
                                    built_context.evidence["review_evidence"]["worktree_diff_hash"]
                                ),
                                "review_evidence_mutation_event_sequence": (
                                    built_context.evidence["review_evidence"][
                                        "mutation_event_sequence"
                                    ]
                                ),
                                "review_evidence_passing_check_event_sequences": (
                                    built_context.evidence["review_evidence"][
                                        "passing_check_event_sequences"
                                    ]
                                ),
                                "review_evidence_source_get_diff_sequence": (
                                    built_context.evidence["review_evidence"][
                                        "source_get_diff_sequence"
                                    ]
                                ),
                                "review_evidence_citable_event_sequences": (
                                    built_context.evidence["review_evidence"][
                                        "citable_event_sequences"
                                    ]
                                ),
                                "review_evidence_incomplete_event_sequences": (
                                    built_context.evidence["review_evidence"][
                                        "incomplete_event_sequences"
                                    ]
                                ),
                            }
                            if manifest.context_policy_version
                            in {
                                "phase-evidence-v9",
                                "phase-evidence-v10",
                                "phase-evidence-v11",
                            }
                            else {}
                        ),
                        **(
                            {
                                "review_evidence_coverage_target_event_sequences": (
                                    built_context.evidence["review_evidence"][
                                        "coverage_target_event_sequences"
                                    ]
                                )
                            }
                            if manifest.context_policy_version
                            in {"phase-evidence-v10", "phase-evidence-v11"}
                            else {}
                        ),
                        **(
                            {
                                "coverage_rejection_feedback": (
                                    built_context.evidence.get("coverage_rejection_feedback")
                                )
                            }
                            if manifest.context_policy_version == "phase-evidence-v11"
                            else {}
                        ),
                    },
                )
                if manifest.context_policy_version in {
                    "phase-evidence-v3",
                    "phase-evidence-v4",
                    "phase-evidence-v5",
                    "phase-evidence-v6",
                    "phase-evidence-v7",
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                    "phase-evidence-v11",
                }:
                    pre_generation_reason = self._pre_generation_budget_reason(
                        manifest,
                        usage,
                    )
                    if pre_generation_reason is not None:
                        self._block_model_generation(
                            manifest=manifest,
                            built_context=built_context,
                            request_artifact=request_artifact,
                            request_body_hash=request_body_hash,
                            reason_code=pre_generation_reason,
                            usage=usage,
                        )
                if lean_request_evidence is not None:
                    try:
                        persisted_request_payload = json.loads(
                            self.artifacts.read_bytes(request_artifact).decode(
                                "utf-8", errors="strict"
                            )
                        )
                    except (UnicodeDecodeError, ValueError) as exc:
                        raise ContractError(
                            "persisted Lean request evidence is unavailable"
                        ) from exc
                    persisted_lean = validate_persisted_lean_harness_request(
                        persisted_request_payload
                    )
                    if persisted_lean != lean_request_evidence:
                        raise ContractError("persisted Lean request evidence differs")
                model_started = time.monotonic()
                if isinstance(adapter, OpenAIResponsesAdapter):
                    if lean_request_evidence is not None:
                        requested_input_tokens = lean_request_evidence.requested_input_tokens
                    else:
                        requested_input_tokens = adapter.count_input_tokens(request_body)
                        split_budget_evidence = self._split_token_request_budget_evidence(
                            manifest,
                            usage,
                            requested_input_tokens=requested_input_tokens,
                        )
                        remaining_tokens = (
                            manifest.budget.max_total_tokens
                            - usage.input_tokens
                            - usage.output_tokens
                        )
                        legacy_budget_exceeded = bool(
                            split_budget_evidence is None
                            and requested_input_tokens + manifest.model.max_output_tokens
                            > remaining_tokens
                        )
                        split_budget_exceeded = bool(
                            split_budget_evidence is not None
                            and split_budget_evidence["exceeded_dimensions"]
                        )
                        if legacy_budget_exceeded or split_budget_exceeded:
                            if manifest.context_policy_version in {
                                "phase-evidence-v3",
                                "phase-evidence-v4",
                                "phase-evidence-v5",
                                "phase-evidence-v6",
                                "phase-evidence-v7",
                                "phase-evidence-v8",
                                "phase-evidence-v9",
                                "phase-evidence-v10",
                                "phase-evidence-v11",
                            }:
                                usage.input_token_count_calls += 1
                                self._block_model_generation(
                                    manifest=manifest,
                                    built_context=built_context,
                                    request_artifact=request_artifact,
                                    request_body_hash=request_body_hash,
                                    reason_code="exact_request_budget_exceeded",
                                    usage=usage,
                                    requested_input_tokens=requested_input_tokens,
                                    remaining_tokens=remaining_tokens,
                                    input_token_count_calls=1,
                                    split_budget_evidence=(
                                        split_budget_evidence if split_budget_exceeded else None
                                    ),
                                )
                            raise ContractError(
                                "remaining token budget cannot fund the exact input "
                                "plus one bounded model response"
                            )
                    if manifest.context_policy_version in {
                        "phase-evidence-v37",
                        "phase-evidence-v38",
                    }:
                        adapter.admit_request_v3(request_body)
                    # R24 integration begin: production-create-gate
                    from patchloop.agent.provider_request_gate import (
                        admit_request,
                        request_admission_required,
                    )

                    if request_admission_required(manifest, row_execution_authorization):
                        admit_request(
                            manifest,
                            row_execution_authorization,
                            request_body,
                            adapter,
                            stop_before_count=False,
                        )
                    # R24 integration end: production-create-gate
                    if row_execution_authorization is not None:
                        _provider_dispatch_boundary(
                            manifest,
                            row_execution_authorization,
                            stop_before_dispatch=False,
                        )
                    execute_request = (
                        adapter.execute_request_v3
                        if manifest.context_policy_version
                        in {"phase-evidence-v37", "phase-evidence-v38"}
                        else adapter.execute_request
                    )
                    turn = execute_request(
                        request_body,
                        requested_input_tokens=requested_input_tokens,
                    )
                    if lean_request_evidence is not None:
                        turn = replace(
                            turn,
                            input_token_count_calls=lean_input_count_calls,
                        )
                    if manifest.context_policy_version in {
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
                    }:
                        provider_terminal_attribution = project_provider_terminal_attribution(
                            response_status=turn.response_status,
                            response_incomplete_reason=turn.response_incomplete_reason,
                            usage_present=bool(
                                turn.input_tokens or turn.output_tokens or turn.total_tokens
                            ),
                            input_token_count_match=(turn.input_token_count_match is True),
                        )
                        if (
                            provider_terminal_attribution.primary_error_code
                            == "incomplete_response"
                            and (
                                turn.error is None
                                or turn.error.code == "input_token_count_mismatch"
                            )
                        ):
                            turn = replace(
                                turn,
                                error=ModelTurnError(
                                    code="incomplete_response",
                                    message=(
                                        "provider response was incomplete"
                                        + (
                                            f": {turn.response_incomplete_reason}"
                                            if turn.response_incomplete_reason
                                            else ""
                                        )
                                    ),
                                ),
                            )
                else:
                    if (
                        manifest.context_policy_version
                        in {
                            "phase-evidence-v3",
                            "phase-evidence-v4",
                            "phase-evidence-v5",
                            "phase-evidence-v6",
                            "phase-evidence-v7",
                            "phase-evidence-v8",
                            "phase-evidence-v9",
                            "phase-evidence-v10",
                            "phase-evidence-v11",
                        }
                        and usage.input_tokens + usage.output_tokens
                        >= manifest.budget.max_total_tokens
                    ):
                        self._block_model_generation(
                            manifest=manifest,
                            built_context=built_context,
                            request_artifact=request_artifact,
                            request_body_hash=request_body_hash,
                            reason_code="token_budget_exhausted",
                            usage=usage,
                        )
                    if row_execution_authorization is not None:
                        _provider_dispatch_boundary(
                            manifest,
                            row_execution_authorization,
                            stop_before_dispatch=False,
                        )
                    turn = adapter.next_turn(context, request_tool_schemas)
                model_duration_ms = (
                    int((time.monotonic() - model_started) * 1000) + lean_input_count_duration_ms
                )
                usage.model_calls += 1
                usage.input_tokens += turn.input_tokens
                usage.cached_input_tokens += turn.cached_input_tokens
                usage.cache_write_input_tokens += turn.cache_write_input_tokens
                usage.output_tokens += turn.output_tokens
                usage.reasoning_output_tokens += turn.reasoning_output_tokens
                usage.input_token_count_calls += turn.input_token_count_calls
                usage.wall_clock_ms += model_duration_ms
                turn_artifact = self.artifacts.put_json(
                    {
                        "text": turn.text,
                        "done": turn.done,
                        "tool_calls": [call.__dict__ for call in turn.tool_calls],
                        "response_id": turn.response_id,
                        "response_model": turn.response_model,
                        "response_service_tier": turn.response_service_tier,
                        "system_fingerprint": turn.system_fingerprint,
                        "response_status": turn.response_status,
                        "response_truncation": turn.response_truncation,
                        "response_incomplete_reason": turn.response_incomplete_reason,
                        "requested_input_tokens": turn.requested_input_tokens,
                        "input_tokens": turn.input_tokens,
                        "cached_input_tokens": turn.cached_input_tokens,
                        "cache_write_input_tokens": turn.cache_write_input_tokens,
                        "output_tokens": turn.output_tokens,
                        "reasoning_output_tokens": turn.reasoning_output_tokens,
                        "total_tokens": turn.total_tokens,
                        "input_token_count_match": turn.input_token_count_match,
                        "total_token_count_match": turn.total_token_count_match,
                        "response_error": (
                            {
                                "code": turn.error.code,
                                "message": turn.error.message,
                            }
                            if turn.error is not None
                            else None
                        ),
                        **(
                            {
                                "provider_terminal_attribution": (
                                    provider_terminal_attribution.model_dump(mode="json")
                                )
                            }
                            if provider_terminal_attribution is not None
                            else {}
                        ),
                    }
                )
                model_event = self.state.append_event(
                    manifest.run_id,
                    EventType.MODEL_CALLED,
                    actor="model-adapter",
                    payload={
                        "model": manifest.model.model_id,
                        "store": False,
                        "previous_response_id_used": False,
                        "input_tokens": turn.input_tokens,
                        "cached_input_tokens": turn.cached_input_tokens,
                        "cache_write_input_tokens": turn.cache_write_input_tokens,
                        "output_tokens": turn.output_tokens,
                        "reasoning_output_tokens": turn.reasoning_output_tokens,
                        "total_tokens": turn.total_tokens,
                        "requested_input_tokens": turn.requested_input_tokens,
                        "input_token_count_match": turn.input_token_count_match,
                        "total_token_count_match": turn.total_token_count_match,
                        "input_token_count_calls": turn.input_token_count_calls,
                        "prompt_telemetry_version": (
                            "prompt-token-integrity-v1"
                            if turn.requested_input_tokens is not None
                            else None
                        ),
                        "request_artifact_id": request_artifact.artifact_id,
                        "request_artifact_path": request_artifact.path,
                        "request_artifact_hash": request_artifact.content_hash,
                        "request_body_hash": request_body_hash,
                        "response_model": turn.response_model,
                        "response_service_tier": turn.response_service_tier,
                        "system_fingerprint": turn.system_fingerprint,
                        "response_status": turn.response_status,
                        "response_truncation": turn.response_truncation,
                        "response_incomplete_reason": turn.response_incomplete_reason,
                        "response_error_code": (
                            turn.error.code if turn.error is not None else None
                        ),
                        **(
                            {
                                "provider_terminal_attribution_hash": (
                                    provider_terminal_attribution.content_hash
                                ),
                                "provider_terminal_accounting_mismatch_preserved": (
                                    provider_terminal_attribution.accounting_mismatch_preserved
                                ),
                            }
                            if provider_terminal_attribution is not None
                            else {}
                        ),
                        "response_text_present": bool(turn.text.strip()),
                        "response_tool_call_count": len(turn.tool_calls),
                        **(
                            {
                                "lean_workflow_target": (
                                    lean_request_evidence.workflow_decision.target
                                ),
                                "lean_workflow_decision_hash": (
                                    lean_request_evidence.workflow_decision_hash
                                ),
                                "lean_shared_recovery_used": (
                                    getattr(
                                        lean_request_evidence.workflow_decision,
                                        "shared_recovery_used",
                                        False,
                                    )
                                ),
                            }
                            if lean_request_evidence is not None
                            and hasattr(lean_request_evidence, "workflow_decision")
                            else {}
                        ),
                        **(
                            {
                                "lean_incomplete_recovery_mode": (
                                    lean_request_evidence.incomplete_recovery.mode
                                ),
                                "lean_reserved_retry_output_tokens": (
                                    lean_request_evidence.incomplete_recovery.reserved_retry_output_tokens
                                ),
                                "lean_incomplete_recovery_hash": (
                                    lean_request_evidence.incomplete_recovery_hash
                                ),
                            }
                            if lean_request_evidence is not None
                            and hasattr(
                                lean_request_evidence,
                                "incomplete_recovery",
                            )
                            else {}
                        ),
                        **(
                            {
                                "lean_completion_recovery_mode": (
                                    lean_request_evidence.completion_response_recovery.mode
                                ),
                                "lean_reserved_completion_retry_output_tokens": (
                                    lean_request_evidence.completion_response_recovery.reserved_retry_output_tokens
                                ),
                                "lean_completion_recovery_hash": (
                                    lean_request_evidence.completion_response_recovery_hash
                                ),
                                "lean_completion_lane_active": (
                                    lean_request_evidence.completion_response_recovery.completion_lane_active
                                ),
                                "lean_response_done": turn.done,
                            }
                            if lean_request_evidence is not None
                            and hasattr(
                                lean_request_evidence,
                                "completion_response_recovery",
                            )
                            else {}
                        ),
                        "artifact_id": turn_artifact.artifact_id,
                        "artifact_path": turn_artifact.path,
                        "duration_ms": model_duration_ms,
                    },
                )
                self._assert_consumed_budget(manifest, usage)
                successor_workflow = manifest.context_policy_version in {
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
                if manifest.context_policy_version in {
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
                    allowed_request_tools = tuple(
                        str(schema.get("name"))
                        for schema in request_tool_schemas
                        if isinstance(schema.get("name"), str)
                    )
                    protocol_reason: str | None = None
                    protocol_error_details: dict[str, Any] = {}
                    if len(turn.tool_calls) > 1:
                        protocol_reason = "multiple_tool_calls"
                    elif turn.tool_calls and turn.tool_calls[0].name not in allowed_request_tools:
                        protocol_reason = "unavailable_tool"
                    elif turn.tool_calls and turn.tool_calls[0].name == "run_check":
                        run_check_schema = next(
                            (
                                schema
                                for schema in request_tool_schemas
                                if schema.get("name") == "run_check"
                            ),
                            {},
                        )
                        expected_check_ids = (
                            run_check_schema.get("parameters", {})
                            .get("properties", {})
                            .get("check_id", {})
                            .get("enum")
                        )
                        if turn.tool_calls[0].arguments.get("check_id") not in (
                            expected_check_ids or []
                        ):
                            protocol_reason = "wrong_check_id"
                    elif (
                        turn.tool_calls
                        and manifest.tool_schema_version in {"v26", "v27", "v28", "v29"}
                        and turn.tool_calls[0].name in {"search_files", "read_file"}
                    ):
                        state = (
                            lean_request_evidence.self_directed_exploration_state
                            if lean_request_evidence is not None
                            and hasattr(
                                lean_request_evidence,
                                "self_directed_exploration_state",
                            )
                            else None
                        )
                        decision = (
                            lean_request_evidence.workflow_decision
                            if lean_request_evidence is not None
                            and hasattr(lean_request_evidence, "workflow_decision")
                            else None
                        )
                        if not isinstance(decision, WorkflowDecisionV4):
                            raise RecoveryError(
                                "V23 inspection lacks its exact self-directed request state"
                            )
                        inspection_arguments = turn.tool_calls[0].arguments
                        if (
                            manifest.tool_schema_version in {"v28", "v29"}
                            and turn.tool_calls[0].name == "read_file"
                        ):
                            try:
                                inspection_arguments = normalize_strict_read_arguments(
                                    inspection_arguments
                                )
                                if "search_anchor" in inspection_arguments:
                                    current_diff = WorkspaceManager.diff_summary(
                                        workspace
                                    ).patch_hash
                                    resolved = resolve_anchored_read(
                                        run_id=manifest.run_id,
                                        task=package.public,
                                        worktree_diff_hash=current_diff,
                                        records=load_inspection_records(
                                            self.state.list_events(manifest.run_id),
                                            self.artifacts,
                                            worktree_diff_hash=current_diff,
                                        ),
                                        raw_anchor=inspection_arguments["search_anchor"],
                                    )
                                    inspection_arguments = {
                                        **{
                                            key: value
                                            for key, value in inspection_arguments.items()
                                            if key != "search_anchor"
                                        },
                                        "path": resolved.path,
                                        "start_line": resolved.start_line,
                                        "end_line": resolved.end_line,
                                    }
                            except ContractError as exc:
                                protocol_reason = "self_directed_investigation_read_mode_invalid"
                                protocol_error_details = {
                                    "reason_codes": [protocol_reason],
                                    "read_admission": dict(exc.details),
                                }
                        if decision.investigation_intent_required and protocol_reason is None:
                            if not isinstance(state, SelfDirectedExplorationState):
                                raise RecoveryError(
                                    "V23 investigation lacks its exact self-directed state"
                                )
                            try:
                                prior_target_hashes = project_episode_investigation_target_hashes(
                                    events=self.state.list_events(manifest.run_id),
                                    decision=decision,
                                    worktree_diff_hash=state.worktree_diff_hash,
                                )
                                validate_investigation_action(
                                    task=package.public,
                                    state=state,
                                    tool=turn.tool_calls[0].name,
                                    arguments=inspection_arguments,
                                    prior_target_hashes=prior_target_hashes,
                                )
                            except ContractError as exc:
                                reason_codes = exc.details.get("reason_codes", [])
                                if not reason_codes or any(
                                    not isinstance(item, str)
                                    or not item.startswith("self_directed_investigation_")
                                    for item in reason_codes
                                ):
                                    raise
                                protocol_reason = reason_codes[0]
                                protocol_error_details = dict(exc.details)
                        elif (
                            not decision.investigation_intent_required
                            and "investigation_intent" in turn.tool_calls[0].arguments
                        ):
                            protocol_reason = "self_directed_investigation_intent_premature"
                            protocol_error_details = {"reason_codes": [protocol_reason]}
                    reasoning_only_incomplete = bool(
                        turn.error is not None
                        and turn.error.code == "incomplete_response"
                        and turn.response_incomplete_reason == "max_output_tokens"
                        and turn.output_tokens > 0
                        and turn.reasoning_output_tokens == turn.output_tokens
                        and not turn.text.strip()
                        and not turn.tool_calls
                    )
                    if (
                        manifest.context_policy_version
                        in {
                            "phase-evidence-v36",
                            "phase-evidence-v37",
                            "phase-evidence-v38",
                        }
                        and reasoning_only_incomplete
                    ):
                        generation_recovery = project_generation_incomplete_recovery(
                            self.state.list_events(manifest.run_id)
                        )
                        if generation_recovery.used:
                            raise ModelGenerationIncompleteRepeatedError(
                                "model exhausted the dedicated reasoning-only generation retry"
                            )
                        self.state.append_event(
                            manifest.run_id,
                            EventType.TOOL_ADMISSION_BLOCKED,
                            actor="workflow-state-machine",
                            correlation_id=model_event.event_id,
                            payload={
                                "policy_version": GENERATION_INCOMPLETE_RECOVERY_POLICY,
                                "reason_code": "reasoning_incomplete",
                                "execution": "not_dispatched",
                                "model_event_sequence": model_event.sequence,
                                "request_artifact_id": request_artifact.artifact_id,
                                "request_body_hash": request_body_hash,
                                "allowed_tool_names": list(allowed_request_tools),
                                "response_tool_names": [],
                                "generation_recovery_slot": 1,
                                "shared_protocol_recovery_slot_consumed": False,
                            },
                        )
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            usage,
                            task=package.public,
                        )
                        continue
                    if successor_workflow and reasoning_only_incomplete:
                        protocol_reason = "reasoning_incomplete"
                    elif (
                        successor_workflow
                        and protocol_reason is None
                        and turn.error is None
                        and (turn.done or not turn.tool_calls)
                    ):
                        protocol_reason = "actionless_response"
                    if protocol_reason is not None:
                        if not successor_workflow:
                            legacy_messages = {
                                "multiple_tool_calls": (
                                    "Lean V8 response emitted more than one tool call"
                                ),
                                "unavailable_tool": "Lean V8 response used an unavailable tool",
                                "wrong_check_id": (
                                    "Lean V8 response used a check outside the request binding"
                                ),
                            }
                            raise ContractError(legacy_messages[protocol_reason])
                        prior_recoveries = [
                            event
                            for event in self.state.list_events(manifest.run_id)
                            if event.type == EventType.TOOL_ADMISSION_BLOCKED
                            and event.payload.get("policy_version") == PROTOCOL_RECOVERY_POLICY
                        ]
                        if prior_recoveries:
                            raise ModelActionContractRepeatedError(
                                "model violated the one-action request contract after recovery"
                            )
                        self.state.append_event(
                            manifest.run_id,
                            EventType.TOOL_ADMISSION_BLOCKED,
                            actor="workflow-state-machine",
                            correlation_id=model_event.event_id,
                            payload={
                                "policy_version": PROTOCOL_RECOVERY_POLICY,
                                "reason_code": protocol_reason,
                                "execution": "not_dispatched",
                                "model_event_sequence": model_event.sequence,
                                "request_artifact_id": request_artifact.artifact_id,
                                "request_body_hash": request_body_hash,
                                "allowed_tool_names": list(allowed_request_tools),
                                "response_tool_names": [call.name for call in turn.tool_calls],
                                "expected_check_ids": (
                                    list(expected_check_ids)
                                    if protocol_reason == "wrong_check_id"
                                    else []
                                ),
                                "error_details": protocol_error_details or None,
                                "shared_recovery_slot": 1,
                            },
                        )
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            usage,
                            task=package.public,
                        )
                        continue
                if turn.error is not None:
                    recovery = (
                        lean_request_evidence.incomplete_recovery
                        if lean_request_evidence is not None
                        and hasattr(lean_request_evidence, "incomplete_recovery")
                        else None
                    )
                    completion_recovery = (
                        lean_request_evidence.completion_response_recovery
                        if lean_request_evidence is not None
                        and hasattr(
                            lean_request_evidence,
                            "completion_response_recovery",
                        )
                        else None
                    )
                    reasoning_only_incomplete = bool(
                        turn.error.code == "incomplete_response"
                        and turn.response_incomplete_reason == "max_output_tokens"
                        and turn.output_tokens > 0
                        and turn.reasoning_output_tokens == turn.output_tokens
                        and not turn.text.strip()
                        and not turn.tool_calls
                    )
                    if reasoning_only_incomplete and (
                        (
                            recovery is not None
                            and recovery.mode == "primary-reserved"
                            and recovery.retry_available_after_response
                        )
                        or (
                            completion_recovery is not None
                            and completion_recovery.mode == "primary-reserved"
                            and completion_recovery.retry_available_after_response
                        )
                    ):
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            usage,
                            task=package.public,
                        )
                        continue
                    raise ContractError(f"model response rejected: {turn.error.code}")
                if turn.done:
                    if manifest.tool_schema_version == "v1":
                        self._validate_legacy_submission(
                            package.public,
                            manifest.run_id,
                            phase,
                        )
                        phase = self._transition(
                            manifest.run_id,
                            phase,
                            Phase.DONE,
                        )
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            usage,
                            task=package.public,
                        )
                        return self._evaluate(
                            task_dir,
                            workspace,
                            manifest,
                            sandbox,
                            usage,
                            evaluator_v2_authority=evaluator_v2_authority,
                        )
                    should_stop = self._reject_unstructured_submission(
                        manifest.run_id,
                        workspace,
                        correlation_id=model_event.event_id,
                    )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        usage,
                        task=package.public,
                    )
                    if should_stop:
                        raise SubmissionProtocolError(
                            "structured finish_task submission was rejected three times"
                        )
                    continue
                if not turn.tool_calls:
                    completion_recovery = (
                        lean_request_evidence.completion_response_recovery
                        if lean_request_evidence is not None
                        and hasattr(
                            lean_request_evidence,
                            "completion_response_recovery",
                        )
                        else None
                    )
                    if (
                        completion_recovery is not None
                        and completion_recovery.mode == "primary-reserved"
                        and completion_recovery.retry_available_after_response
                    ):
                        checkpoint = self._checkpoint(
                            manifest,
                            workspace,
                            phase,
                            usage,
                            task=package.public,
                        )
                        continue
                    raise ContractError("model returned neither a tool call nor a submission")
                finish_calls = [call for call in turn.tool_calls if call.name == "finish_task"]
                v4_apply_precedes_finish = (
                    manifest.tool_schema_version
                    in {
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
                    and bool(finish_calls)
                    and any(
                        call.name in {"apply_patch", "apply_structured_edit"}
                        for call in turn.tool_calls[: turn.tool_calls.index(finish_calls[0])]
                    )
                )
                if finish_calls and len(turn.tool_calls) != 1 and not v4_apply_precedes_finish:
                    if (
                        manifest.budget.max_tool_calls is not None
                        and usage.tool_calls >= manifest.budget.max_tool_calls
                    ):
                        raise ContractError("tool call budget exhausted")
                    finish_call = finish_calls[0]
                    result, _, should_stop = self._finish_task(
                        run_id=manifest.run_id,
                        task=package.public,
                        workspace=workspace,
                        phase=phase,
                        action_id=finish_call.action_id,
                        arguments=finish_call.arguments,
                        context_evidence=built_context.evidence,
                        request_artifact_id=request_artifact.artifact_id,
                        tool_schema_version=manifest.tool_schema_version,
                        additional_missing_evidence=["finish_task_must_be_only_action"],
                    )
                    if not result.output.get("replayed") and not result.output.get(
                        "admission_blocked"
                    ):
                        usage.tool_calls += 1
                        usage.wall_clock_ms += int(
                            (result.finished_at - result.started_at).total_seconds() * 1000
                        )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        usage,
                        result,
                        task=package.public,
                    )
                    if should_stop:
                        raise SubmissionProtocolError(
                            "submission preconditions were rejected three times"
                        )
                    continue
                for call_index, call in enumerate(turn.tool_calls, 1):
                    if (
                        successor_workflow
                        and call.name in {"apply_patch", "apply_structured_edit"}
                        and lean_request_evidence is not None
                        and hasattr(lean_request_evidence, "workflow_decision")
                        and lean_request_evidence.workflow_decision.target == "review-decision"
                        and lean_request_evidence.workflow_decision.review_corrections_used >= 1
                    ):
                        raise ReviewCorrectionLimitError(
                            "a second review correction was rejected before tool dispatch"
                        )
                    if call.name == "declare_exploration_exhausted":
                        if manifest.tool_schema_version not in {"v26", "v27", "v28", "v29"}:
                            raise ContractError(
                                "declare_exploration_exhausted requires tool schema v26+"
                            )
                        state = (
                            lean_request_evidence.self_directed_exploration_state
                            if lean_request_evidence is not None
                            and hasattr(
                                lean_request_evidence,
                                "self_directed_exploration_state",
                            )
                            else None
                        )
                        if not isinstance(state, SelfDirectedExplorationState):
                            raise RecoveryError(
                                "exploration stop lacks its exact self-directed request state"
                            )
                        self._record_self_directed_exploration_stop(
                            run_id=manifest.run_id,
                            state=state,
                            action_id=call.action_id,
                            arguments=call.arguments,
                            model_event_sequence=model_event.sequence,
                            request_artifact_id=request_artifact.artifact_id,
                            request_body_hash=request_body_hash,
                        )
                        raise SelfDirectedExplorationExhaustedError(
                            "bounded public exploration ended without a safe plan"
                        )
                    if (
                        manifest.budget.max_tool_calls is not None
                        and usage.tool_calls >= manifest.budget.max_tool_calls
                    ):
                        raise ContractError("tool call budget exhausted")
                    if call.name == "finish_task":
                        if manifest.tool_schema_version not in {
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
                        }:
                            raise ContractError("finish_task is unavailable in tool schema v1")
                        result, accepted, should_stop = self._finish_task(
                            run_id=manifest.run_id,
                            task=package.public,
                            workspace=workspace,
                            phase=phase,
                            action_id=call.action_id,
                            arguments=call.arguments,
                            context_evidence=built_context.evidence,
                            request_artifact_id=request_artifact.artifact_id,
                            tool_schema_version=(manifest.tool_schema_version),
                            additional_missing_evidence=[],
                        )
                        if not result.output.get("replayed"):
                            usage.tool_calls += 1
                            usage.wall_clock_ms += int(
                                (result.finished_at - result.started_at).total_seconds() * 1000
                            )
                        if isinstance(adapter, MockModelAdapter) and (result.status == "succeeded"):
                            adapter.record_completed(call.name)
                        if accepted:
                            phase, checkpoint = self._complete_accepted_submission(
                                manifest=manifest,
                                task=package.public,
                                workspace=workspace,
                                phase=phase,
                                usage=usage,
                                result=result,
                            )
                        else:
                            checkpoint = self._checkpoint(
                                manifest,
                                workspace,
                                phase,
                                usage,
                                result,
                                task=package.public,
                            )
                        if should_stop:
                            raise SubmissionProtocolError(
                                "submission preconditions were rejected three times"
                            )
                        if accepted:
                            return self._evaluate(
                                task_dir,
                                workspace,
                                manifest,
                                sandbox,
                                usage,
                                evaluator_v2_authority=evaluator_v2_authority,
                            )
                        continue
                    execution_context = (
                        {
                            "request_artifact_id": (request_artifact.artifact_id),
                            "phase": phase.value,
                            "presented_tool_results": (
                                built_context.evidence.get(
                                    "tool_results",
                                    [],
                                )
                            ),
                            **(
                                {"review_evidence": (built_context.evidence.get("review_evidence"))}
                                if manifest.context_policy_version
                                in {
                                    "phase-evidence-v9",
                                    "phase-evidence-v10",
                                    "phase-evidence-v11",
                                }
                                else {}
                            ),
                            **(
                                {"coverage_rejection_feedback": (coverage_rejection_feedback)}
                                if manifest.context_policy_version == "phase-evidence-v11"
                                else {}
                            ),
                        }
                        if call.name == "review_task"
                        else (
                            {
                                "request_artifact_id": request_artifact.artifact_id,
                                "request_body_hash": request_body_hash,
                                "eligible_plan_evidence_catalog": (
                                    lean_request_evidence.eligible_plan_evidence_catalog.model_dump(
                                        mode="json"
                                    )
                                ),
                                "workflow_decision": (
                                    lean_request_evidence.workflow_decision.model_dump(mode="json")
                                ),
                                "active_work_state": (
                                    lean_request_evidence.active_work_state.model_dump(mode="json")
                                    if lean_request_evidence.active_work_state is not None
                                    else None
                                ),
                                **(
                                    {
                                        "phase_evidence": lean_request_evidence.phase_evidence,
                                        "semantic_progress_state": (
                                            lean_request_evidence.semantic_progress_state.model_dump(
                                                mode="json"
                                            )
                                            if lean_request_evidence.semantic_progress_state
                                            is not None
                                            else None
                                        ),
                                        **(
                                            {
                                                "semantic_progress_event_domain": (
                                                    lean_request_evidence.semantic_progress_event_domain.model_dump(
                                                        mode="json"
                                                    )
                                                )
                                            }
                                            if hasattr(
                                                lean_request_evidence,
                                                "semantic_progress_event_domain",
                                            )
                                            else {}
                                        ),
                                    }
                                    if hasattr(
                                        lean_request_evidence,
                                        "semantic_progress_state",
                                    )
                                    else {}
                                ),
                                **(
                                    {
                                        "cross_reset_failure_trigger": (
                                            lean_request_evidence.cross_reset_failure_trigger.model_dump(
                                                mode="json"
                                            )
                                            if lean_request_evidence.cross_reset_failure_trigger
                                            is not None
                                            else None
                                        ),
                                        "mutation_baseline_projection": (
                                            lean_request_evidence.mutation_baseline_projection.model_dump(
                                                mode="json"
                                            )
                                            if lean_request_evidence.mutation_baseline_projection
                                            is not None
                                            else None
                                        ),
                                        "mutation_baseline_restore_receipt": (
                                            lean_request_evidence.mutation_baseline_restore_receipt.model_dump(
                                                mode="json"
                                            )
                                            if (
                                                lean_request_evidence.mutation_baseline_restore_receipt
                                                is not None
                                            )
                                            else None
                                        ),
                                        "causal_mechanism_history": [
                                            item.model_dump(mode="json")
                                            for item in (
                                                lean_request_evidence.causal_mechanism_history
                                            )
                                        ],
                                        **(
                                            {
                                                "causal_plan_request_projection": (
                                                    lean_request_evidence.causal_plan_request_projection.model_dump(
                                                        mode="json"
                                                    )
                                                )
                                            }
                                            if hasattr(
                                                lean_request_evidence,
                                                "causal_plan_request_projection",
                                            )
                                            and lean_request_evidence.causal_plan_request_projection
                                            is not None
                                            else {}
                                        ),
                                        **(
                                            {
                                                "activated_exploration_plan_request": (
                                                    lean_request_evidence.activated_exploration_plan_request.model_dump(
                                                        mode="json"
                                                    )
                                                )
                                            }
                                            if hasattr(
                                                lean_request_evidence,
                                                "activated_exploration_plan_request",
                                            )
                                            and (
                                                lean_request_evidence.activated_exploration_plan_request
                                                is not None
                                            )
                                            else {}
                                        ),
                                    }
                                    if hasattr(
                                        lean_request_evidence,
                                        "cross_reset_failure_trigger",
                                    )
                                    else {}
                                ),
                            }
                            if call.name in {"record_work_plan", "revise_work_plan"}
                            and lean_request_evidence is not None
                            and hasattr(
                                lean_request_evidence,
                                "eligible_plan_evidence_catalog",
                            )
                            else (
                                {
                                    "self_directed_exploration_state": (
                                        lean_request_evidence.self_directed_exploration_state.model_dump(
                                            mode="json"
                                        )
                                        if isinstance(
                                            getattr(
                                                lean_request_evidence,
                                                "self_directed_exploration_state",
                                                None,
                                            ),
                                            SelfDirectedExplorationState,
                                        )
                                        else None
                                    ),
                                    "workflow_decision": (
                                        lean_request_evidence.workflow_decision.model_dump(
                                            mode="json"
                                        )
                                    ),
                                }
                                if manifest.tool_schema_version in {"v26", "v27", "v28", "v29"}
                                and call.name in {"search_files", "read_file"}
                                and lean_request_evidence is not None
                                and isinstance(
                                    getattr(lean_request_evidence, "workflow_decision", None),
                                    WorkflowDecisionV4,
                                )
                                else None
                            )
                        )
                    )
                    result = gateway.execute(
                        call.name,
                        call.action_id,
                        call.arguments,
                        execution_context=execution_context,
                    )
                    if manifest.tool_schema_version in {
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
                    } and call.name in {
                        "apply_patch",
                        "apply_structured_edit",
                    }:
                        for blocked_index, blocked_call in enumerate(
                            turn.tool_calls[call_index:],
                            call_index + 1,
                        ):
                            gateway.block_same_turn_action(
                                blocked_call.name,
                                blocked_call.action_id,
                                blocked_call.arguments,
                                source_action_id=call.action_id,
                                source_result_status=result.status,
                                source_model_event_id=model_event.event_id,
                                source_call_index=call_index,
                                blocked_call_index=blocked_index,
                            )
                    if not result.output.get("replayed") and not result.output.get(
                        "admission_blocked"
                    ):
                        usage.tool_calls += 1
                        if not result.output.get("semantic_replay"):
                            usage.wall_clock_ms += int(
                                (result.finished_at - result.started_at).total_seconds() * 1000
                            )
                    if isinstance(adapter, MockModelAdapter) and result.status == "succeeded":
                        adapter.record_completed(call.name)
                    if result.status == "failed" and result.output.get("fatal") is True:
                        raise RecoveryError(
                            result.error_message or "tool execution failed with a fatal state error"
                        )
                    phase = self._phase_after_tool(
                        manifest.run_id,
                        phase,
                        call.name,
                        result,
                        package.public,
                        workspace,
                    )
                    checkpoint = self._checkpoint(
                        manifest,
                        workspace,
                        phase,
                        usage,
                        result,
                        task=package.public,
                    )
                    if (
                        manifest.context_policy_version
                        in {
                            "phase-evidence-v9",
                            "phase-evidence-v10",
                            "phase-evidence-v11",
                        }
                        and call.name == "review_task"
                        and result.status != "succeeded"
                        and self._review_rejection_count(manifest.run_id)
                        > _MAX_RECOVERABLE_REVIEW_REJECTIONS
                    ):
                        raise SubmissionProtocolError(
                            "structured review evidence was rejected three times"
                        )
                    if (
                        call.name == "run_check"
                        and result.status == "succeeded"
                        and result.output.get("timed_out") is True
                    ):
                        raise ContractError(
                            "visible check timed out; the unchanged command will not be repeated"
                        )
                    if (
                        manifest.fault.type == "worker-kill-after-patch"
                        and call.name in {"apply_patch", "apply_structured_edit"}
                        and result.status == "succeeded"
                    ):
                        self.state.append_event(
                            manifest.run_id,
                            EventType.FAULT_INJECTED,
                            actor="fault-injector",
                            payload={
                                "fault": manifest.fault.type,
                                "after_action": call.action_id,
                            },
                        )
                        raise InjectedFault(
                            "worker terminated immediately after durable patch checkpoint"
                        )
                    if manifest.tool_schema_version in {
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
                    } and call.name in {
                        "apply_patch",
                        "apply_structured_edit",
                    }:
                        break
        except InjectedFault as exc:
            self.state.set_run_status(manifest.run_id, RunStatus.SUSPENDED)
            return {
                "run_id": manifest.run_id,
                "status": "suspended",
                "fault": manifest.fault.type,
                "message": str(exc),
                "resume_command": f"patchloop resume --run-id {manifest.run_id}",
            }
        except Exception as exc:
            if self._evaluation_receipt_path(manifest.run_id).exists():
                raise
            if manifest.context_policy_version in {"phase-evidence-v37", "phase-evidence-v38"}:
                usage = self._usage(manifest.run_id)
            outcome_kind = (
                RunOutcomeKind.AGENT_FAILURE
                if isinstance(exc, ContractError)
                and not isinstance(exc, ProviderToolSchemaError)
                and not (
                    manifest.context_policy_version in {"phase-evidence-v37", "phase-evidence-v38"}
                    and isinstance(exc, HarnessAdmissionError)
                )
                else RunOutcomeKind.INFRASTRUCTURE_ERROR
            )
            return self._terminal_failure(
                task_dir,
                manifest,
                phase,
                usage,
                exc,
                outcome_kind,
            )

    def _evaluate(
        self,
        task_dir: str | Path,
        workspace: Path,
        manifest: RunManifest,
        sandbox: DockerSandbox | LocalSandbox,
        usage: Usage,
        *,
        evaluator_v2_authority: EvaluatorV2QualificationAuthority | None = None,
    ) -> dict[str, Any]:
        usage.model_cost_usd = calculate_model_cost(usage, manifest.model)
        summary = WorkspaceManager.diff_summary(workspace)
        submitted_patch_artifact: Artifact | None = None
        if manifest.tool_schema_version in {
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
        }:
            accepted_events = [
                event
                for event in self.state.list_events(manifest.run_id)
                if event.type == EventType.SUBMISSION_ACCEPTED
            ]
            if len(accepted_events) != 1:
                raise RecoveryError("v2 evaluation requires one accepted submission")
            try:
                submitted_patch_artifact = Artifact.model_validate(
                    accepted_events[0].payload["submitted_patch_artifact"]
                )
                submitted_patch_bytes = self.artifacts.read_bytes(submitted_patch_artifact)
            except (
                KeyError,
                OSError,
                RecoveryError,
                TypeError,
                ValueError,
            ) as exc:
                raise RecoveryError("accepted submission patch artifact is unavailable") from exc
            if (
                submitted_patch_artifact.content_hash
                != accepted_events[0].payload.get("worktree_diff_hash")
                or sha256_bytes(submitted_patch_bytes) != submitted_patch_artifact.content_hash
                or summary.patch_hash != submitted_patch_artifact.content_hash
            ):
                raise RecoveryError("accepted patch artifact, event, and worktree differ")
        else:
            submitted_patch_bytes = summary.patch.encode("utf-8")
        run_dir = self.root / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        patch_path = run_dir / "submitted.patch"
        self._write_runtime_bytes_atomic(
            patch_path,
            submitted_patch_bytes,
        )
        evaluator_v2_receipt: EvaluatorV2EvaluationReceipt | None = None
        if manifest.schema_version == "run-manifest-v2":
            if evaluator_v2_authority is None or submitted_patch_artifact is None:
                raise ContractError(
                    "evaluator-v2 requires qualified authority and an accepted patch"
                )
            package = load_task_package(task_dir)
            if self._evaluation_receipt_path(manifest.run_id).exists():
                persisted = validate_persisted_evaluator_v2_evaluation_receipt(
                    state_store=self.state,
                    artifact_store=self.artifacts,
                    run_id=manifest.run_id,
                    package=package,
                    authority=evaluator_v2_authority,
                )
                result = persisted.result
                evaluator_v2_receipt = persisted.receipt
                evaluator_duration_ms = persisted.receipt.evaluator_duration_ms
            else:
                evaluator = EvaluationEngine(
                    self.workspaces,
                    sandbox,
                    self.artifacts,
                    self.state,
                )
                evaluator_started = time.monotonic()
                production = evaluator.evaluate_v2_candidate(
                    task_dir,
                    patch_path,
                    manifest,
                    usage=usage,
                    submitted_patch_artifact=submitted_patch_artifact,
                    authority=evaluator_v2_authority.runtime,
                )
                evaluator_duration_ms = int((time.monotonic() - evaluator_started) * 1000)
                persisted = issue_evaluator_v2_evaluation_receipt(
                    state_store=self.state,
                    artifact_store=self.artifacts,
                    package=package,
                    production=production,
                    authority=evaluator_v2_authority,
                    evaluator_duration_ms=evaluator_duration_ms,
                )
                result = persisted.result
                evaluator_v2_receipt = persisted.receipt
        else:
            completed_evaluation = self._load_completed_evaluation(
                manifest,
                expected_patch_hash=summary.patch_hash,
                submitted_patch_artifact=submitted_patch_artifact,
                expected_official=sandbox.official,
            )
            if completed_evaluation is None:
                evaluator = EvaluationEngine(
                    self.workspaces,
                    sandbox,
                    self.artifacts,
                )
                evaluator_started = time.monotonic()
                result = evaluator.evaluate(
                    task_dir,
                    patch_path,
                    manifest,
                    usage=usage,
                    submitted_patch_artifact=submitted_patch_artifact,
                )
                evaluator_duration_ms = int((time.monotonic() - evaluator_started) * 1000)
                self._persist_evaluation_receipt(
                    manifest,
                    result,
                    evaluator_duration_ms=evaluator_duration_ms,
                    expected_patch_hash=summary.patch_hash,
                    submitted_patch_artifact=submitted_patch_artifact,
                    expected_official=sandbox.official,
                )
            else:
                result, evaluator_duration_ms = completed_evaluation
        classification_error: dict[str, str] | None = None
        try:
            failure = classify_failure(
                result,
                load_task_package(task_dir).public.split,
                root=self.root,
                phase=Phase.REVIEW,
                events=self.state.list_events(manifest.run_id),
            )
        except (ContractError, OSError, ValueError) as exc:
            failure = None
            classification_error = {
                "type": type(exc).__name__,
                "message": self._safe_error_message(exc),
            }
        failure_payload = None
        if failure is not None:
            failure_payload = {
                "failure_id": failure.failure_id,
                "primary_cause": failure.primary_cause,
                "classification_method": failure.classification_method,
            }
        self.state.finalize_run(
            manifest.run_id,
            status=RunStatus.COMPLETED,
            result=result,
            event_type=EventType.RUN_COMPLETED,
            actor="evaluator",
            payload={
                "scope_compliant_success": result.scope_compliant_success,
                "official": result.official,
                "duration_ms": evaluator_duration_ms,
                "failure_classification_error": classification_error,
            },
            failure_payload=failure_payload,
            evaluator_v2_receipt=evaluator_v2_receipt,
        )
        return result.model_dump(mode="json")

    def _load_completed_evaluation(
        self,
        manifest: RunManifest,
        *,
        expected_patch_hash: str,
        submitted_patch_artifact: Artifact | None,
        expected_official: bool,
    ) -> tuple[RunResult, int] | None:
        receipt_path = self._evaluation_receipt_path(manifest.run_id)
        if not receipt_path.exists():
            return None
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RecoveryError("completed evaluation receipt is unreadable") from exc
        if not isinstance(receipt, dict):
            raise RecoveryError("completed evaluation receipt is malformed")
        file_hashes = receipt.get("file_hashes")
        duration_ms = receipt.get("evaluator_duration_ms")
        result_artifact_id = receipt.get("submitted_patch_artifact_id")
        if (
            receipt.get("schema_version") != _EVALUATION_RECEIPT_SCHEMA
            or receipt.get("run_id") != manifest.run_id
            or receipt.get("worktree_diff_hash") != expected_patch_hash
            or not isinstance(result_artifact_id, str)
            or not result_artifact_id
            or (
                submitted_patch_artifact is not None
                and result_artifact_id != submitted_patch_artifact.artifact_id
            )
            or not isinstance(duration_ms, int)
            or duration_ms < 0
            or not isinstance(file_hashes, dict)
            or set(file_hashes) != {"manifest.json", "result.json", "provenance.json"}
        ):
            raise RecoveryError("completed evaluation receipt conflicts with the run")
        result = self._validate_completed_evaluation_files(
            manifest,
            file_hashes=file_hashes,
            expected_patch_hash=expected_patch_hash,
            expected_result_artifact_id=result_artifact_id,
            submitted_patch_artifact=submitted_patch_artifact,
            expected_official=expected_official,
        )
        return result, duration_ms

    def _persist_evaluation_receipt(
        self,
        manifest: RunManifest,
        result: RunResult,
        *,
        evaluator_duration_ms: int,
        expected_patch_hash: str,
        submitted_patch_artifact: Artifact | None,
        expected_official: bool,
    ) -> None:
        run_dir = self.artifacts.root / "runs" / manifest.run_id
        result_artifact_id = result.submitted_patch_artifact_id
        if not isinstance(result_artifact_id, str) or not result_artifact_id:
            raise RecoveryError("completed evaluation lacks its submitted patch artifact")
        if (
            submitted_patch_artifact is not None
            and result_artifact_id != submitted_patch_artifact.artifact_id
        ):
            raise RecoveryError(
                "completed evaluation patch artifact conflicts with the accepted submission"
            )
        file_hashes: dict[str, str] = {}
        for name in ("manifest.json", "result.json", "provenance.json"):
            try:
                file_hashes[name] = sha256_bytes((run_dir / name).read_bytes())
            except OSError as exc:
                raise RecoveryError("evaluator did not persist a complete result bundle") from exc
        persisted = self._validate_completed_evaluation_files(
            manifest,
            file_hashes=file_hashes,
            expected_patch_hash=expected_patch_hash,
            expected_result_artifact_id=result_artifact_id,
            submitted_patch_artifact=submitted_patch_artifact,
            expected_official=expected_official,
        )
        if persisted != result:
            raise RecoveryError("evaluator return value differs from its persisted result")
        receipt = {
            "schema_version": _EVALUATION_RECEIPT_SCHEMA,
            "run_id": manifest.run_id,
            "worktree_diff_hash": expected_patch_hash,
            "submitted_patch_artifact_id": result_artifact_id,
            "evaluator_duration_ms": evaluator_duration_ms,
            "file_hashes": file_hashes,
        }
        self.artifacts.write_text_atomic(
            run_dir / "evaluation-receipt.json",
            json.dumps(receipt, indent=2, sort_keys=True),
        )

    def _validate_completed_evaluation_files(
        self,
        manifest: RunManifest,
        *,
        file_hashes: dict[str, Any],
        expected_patch_hash: str,
        expected_result_artifact_id: str,
        submitted_patch_artifact: Artifact | None,
        expected_official: bool,
    ) -> RunResult:
        run_dir = self.artifacts.root / "runs" / manifest.run_id
        contents: dict[str, bytes] = {}
        try:
            for name in (
                "manifest.json",
                "result.json",
                "provenance.json",
            ):
                declared_hash = file_hashes.get(name)
                content = (run_dir / name).read_bytes()
                if not isinstance(declared_hash, str) or sha256_bytes(content) != declared_hash:
                    raise RecoveryError(
                        f"completed evaluation file hash does not match its receipt: {name}"
                    )
                contents[name] = content
            persisted_manifest = RunManifest.model_validate_json(contents["manifest.json"])
            result = RunResult.model_validate_json(contents["result.json"])
            provenance = json.loads(contents["provenance.json"])
        except RecoveryError:
            raise
        except (
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError("completed evaluation bundle is invalid") from exc
        if not isinstance(provenance, dict):
            raise RecoveryError("completed evaluation provenance is malformed")
        verifier_evidence = self._validated_verifier_evidence(result)
        if (
            persisted_manifest != manifest
            or result.run_id != manifest.run_id
            or result.evaluation_status != "completed"
            or result.official is not expected_official
            or provenance.get("patch_hash") != expected_patch_hash
            or provenance.get("diff_hash") != expected_patch_hash
            or provenance.get("submitted_patch_content_hash") != expected_patch_hash
            or provenance.get("submitted_patch_artifact_id") != expected_result_artifact_id
            or result.submitted_patch_artifact_id != expected_result_artifact_id
            or provenance.get("verifier_evidence_schema_version") != "verifier-evidence-v1"
            or provenance.get("verifier_evidence_artifacts") != verifier_evidence
        ):
            raise RecoveryError("completed evaluation bundle conflicts with immutable run evidence")
        if submitted_patch_artifact is not None and (
            submitted_patch_artifact.artifact_id != expected_result_artifact_id
            or submitted_patch_artifact.content_hash != expected_patch_hash
        ):
            raise RecoveryError("accepted patch artifact conflicts with completed evaluation")
        return result

    def _validated_verifier_evidence(
        self,
        result: RunResult,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for verifier_result in result.verifier_results:
            raw_artifacts = verifier_result.details.get("evidence_artifacts")
            if not verifier_result.evidence_artifact_ids:
                if raw_artifacts not in (None, []):
                    raise RecoveryError("verifier result has unreferenced evidence artifacts")
                continue
            if not isinstance(raw_artifacts, list) or len(raw_artifacts) != len(
                verifier_result.evidence_artifact_ids
            ):
                raise RecoveryError("verifier result lacks complete evidence descriptors")
            descriptors: list[dict[str, Any]] = []
            for expected_id, raw_artifact in zip(
                verifier_result.evidence_artifact_ids,
                raw_artifacts,
                strict=True,
            ):
                try:
                    artifact = Artifact.model_validate(raw_artifact)
                    self.artifacts.read_bytes(artifact)
                except (RecoveryError, TypeError, ValueError) as exc:
                    raise RecoveryError(
                        "verifier evidence artifact failed integrity validation"
                    ) from exc
                if artifact.artifact_id != expected_id:
                    raise RecoveryError("verifier evidence identity conflicts with its result")
                descriptors.append(artifact.model_dump(mode="json"))
            evidence.extend(descriptors)
        return evidence

    def _evaluation_receipt_path(self, run_id: str) -> Path:
        return self.artifacts.root / "runs" / run_id / "evaluation-receipt.json"

    def _terminal_failure(
        self,
        task_dir: str | Path,
        manifest: RunManifest,
        phase: Phase,
        usage: Usage,
        error: Exception,
        outcome_kind: RunOutcomeKind,
    ) -> dict[str, Any]:
        """Persist a schema-valid terminal attempt even when evaluation is not reached."""

        usage.model_cost_usd = calculate_model_cost(usage, manifest.model)
        safe_message = self._safe_error_message(error)
        events = self.state.list_events(manifest.run_id)
        submission_accepted = any(event.type == EventType.SUBMISSION_ACCEPTED for event in events)
        terminal_error: dict[str, Any] = {
            "type": type(error).__name__,
            "message": safe_message,
        }
        error_code = getattr(error, "code", None)
        if isinstance(error_code, str):
            terminal_error["code"] = error_code
        error_details = self._safe_error_details(error)
        if error_details:
            terminal_error["details"] = error_details
        effective_outcome = outcome_kind
        if manifest.schema_version == "run-manifest-v2":
            submitted_patch_ref = None
            submitted_patch_id = None
            if submission_accepted:
                accepted = [
                    event for event in events if event.type == EventType.SUBMISSION_ACCEPTED
                ]
                try:
                    artifact = Artifact.model_validate(
                        accepted[0].payload["submitted_patch_artifact"]
                    )
                    self.artifacts.read_bytes(artifact)
                    submitted_patch_ref = build_evidence_artifact_ref(
                        artifact,
                        role="submitted_patch",
                    )
                    submitted_patch_id = artifact.artifact_id
                except (IndexError, KeyError, RecoveryError, ValueError) as exc:
                    raise RecoveryError(
                        "accepted v2 failure lacks its submitted patch evidence"
                    ) from exc
                typed_terminal = {
                    "code": "EVALUATOR_INFRASTRUCTURE_ERROR",
                    "phase": "evaluator",
                }
                effective_outcome = RunOutcomeKind.INFRASTRUCTURE_ERROR
            else:
                typed_terminal = {
                    "code": "AGENT_SUBMISSION_FAILED",
                    "phase": "agent",
                }
                effective_outcome = RunOutcomeKind.AGENT_FAILURE
            result = RunResult(
                schema_version="run-result-v2",
                run_id=manifest.run_id,
                agent_submission_status=("completed" if submission_accepted else "failed"),
                evaluation_status="not_run",
                scope_compliant_success=False,
                official=False,
                verdicts=Verdicts(),
                usage=usage,
                submitted_patch_artifact_id=submitted_patch_id,
                submitted_patch_artifact=submitted_patch_ref,
                outcome_kind=effective_outcome,
                terminal_error=typed_terminal,
                evaluator_contract=manifest.evaluator_contract,
            )
        else:
            result = RunResult(
                run_id=manifest.run_id,
                agent_submission_status=("completed" if submission_accepted else "failed"),
                evaluation_status="not_run",
                scope_compliant_success=False,
                official=False,
                verdicts=Verdicts(),
                usage=usage,
                outcome_kind=outcome_kind,
                terminal_error=terminal_error,
            )
        failure = classify_failure(
            result,
            load_task_package(task_dir).public.split,
            root=self.root,
            phase=phase,
            events=events,
        )
        failure_payload = None
        if failure is not None:
            failure_payload = {
                "failure_id": failure.failure_id,
                "primary_cause": failure.primary_cause,
                "classification_method": failure.classification_method,
            }
        run_dir = self.artifacts.root / "runs" / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "evaluation-receipt.json").unlink(missing_ok=True)
        self.artifacts.write_text_atomic(
            run_dir / "manifest.json",
            manifest.model_dump_json(indent=2),
        )
        self.artifacts.write_text_atomic(
            run_dir / "result.json",
            result.model_dump_json(indent=2),
        )
        self.artifacts.write_text_atomic(
            run_dir / "provenance.json",
            json.dumps(
                {
                    "evaluation_reached": False,
                    "outcome_kind": effective_outcome.value,
                    "error_type": type(error).__name__,
                    "error_code": error_code,
                },
                indent=2,
            ),
        )
        self.state.finalize_run(
            manifest.run_id,
            status=RunStatus.FAILED,
            result=result,
            event_type=EventType.RUN_FAILED,
            actor="runner",
            payload={
                "outcome_kind": effective_outcome.value,
                "error_type": type(error).__name__,
                "error_code": error_code,
                "error_details": error_details or None,
                "message": safe_message,
                "model_cost_usd": usage.model_cost_usd,
            },
            failure_payload=failure_payload,
        )
        return result.model_dump(mode="json")

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        message = str(error)
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            message = message.replace(api_key, "[REDACTED]")
        return message[:2_000]

    @staticmethod
    def _safe_error_details(error: Exception) -> dict[str, Any]:
        raw = getattr(error, "details", None)
        if not isinstance(raw, dict) or not raw:
            return {}
        api_key = os.environ.get("OPENAI_API_KEY")

        def redact(value: Any) -> Any:
            if isinstance(value, str):
                return value.replace(api_key, "[REDACTED]") if api_key else value
            if isinstance(value, list):
                return [redact(item) for item in value]
            if isinstance(value, dict):
                return {str(key): redact(item) for key, item in value.items()}
            if value is None or isinstance(value, (bool, int, float)):
                return value
            return str(value)

        return redact(raw)

    def _write_runtime_bytes_atomic(
        self,
        path: Path,
        content: bytes,
    ) -> None:
        try:
            root = self.root.resolve()
            resolved = path.resolve()
        except OSError as exc:
            raise RecoveryError("runtime artifact path cannot be resolved") from exc
        if not resolved.is_relative_to(root) or path.is_symlink():
            raise RecoveryError("runtime artifact path escapes the run root")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _checkpoint(
        self,
        manifest: RunManifest,
        workspace: Path,
        phase: Phase,
        usage: Usage | None = None,
        last_result: ToolResult | None = None,
        *,
        task: PublicTask | None = None,
    ) -> Checkpoint:
        if WorkspaceManager.untracked_files(workspace):
            raise RecoveryError("agent workspace contains untracked files at checkpoint")
        summary = WorkspaceManager.diff_summary(workspace)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        completed_actions = list(
            dict.fromkeys(
                event.correlation_id
                for event in self.state.list_events(manifest.run_id)
                if event.type == EventType.TOOL_SUCCEEDED and event.correlation_id
            )
        )
        events = self.state.list_events(manifest.run_id)
        if manifest.context_policy_version in {
            "phase-evidence-v2",
            "phase-evidence-v3",
            "phase-evidence-v4",
            "phase-evidence-v5",
            "phase-evidence-v6",
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
            "phase-evidence-v11",
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
        }:
            evidence_task = task or load_task_package(self._find_task(manifest)).public
            evidence = diff_bound_evidence(
                evidence_task,
                events,
                summary.patch_hash,
                structured_review_required=(
                    manifest.context_policy_version
                    in {
                        "phase-evidence-v6",
                        "phase-evidence-v7",
                        "phase-evidence-v8",
                        "phase-evidence-v9",
                        "phase-evidence-v10",
                        "phase-evidence-v11",
                    }
                ),
                coverage_review_required=(
                    manifest.context_policy_version in {"phase-evidence-v10", "phase-evidence-v11"}
                ),
                probe_available=bool(evidence_task.probe_profiles),
                completion_driven=(
                    manifest.context_policy_version
                    in {
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
                ),
            )
            completed_checks = list(evidence.completed_checks)
            pending_checks = list(evidence.pending_checks)
            # The next model context recalculates presented-result evidence.
            # V10 persists only the diff-bound durable plan hash, never a stale
            # tool prescription.
            current_plan: list[str] = []
            reproduction_status = "unknown"
            if manifest.context_policy_version == "phase-evidence-v20":
                all_plan_events = [
                    event
                    for event in events
                    if event.type == EventType.PLAN_RECORDED
                    and isinstance(event.payload.get("plan_hash"), str)
                ]
                plan_events = [
                    event
                    for event in all_plan_events
                    if event.payload.get("worktree_diff_hash") == summary.patch_hash
                ]
                if not plan_events:
                    linked_patch = next(
                        (
                            event
                            for event in reversed(events)
                            if event.type == EventType.PATCH_APPLIED
                            and event.payload.get("worktree_diff_hash") == summary.patch_hash
                            and isinstance(event.payload.get("plan_hash"), str)
                        ),
                        None,
                    )
                    if linked_patch is not None:
                        plan_events = [
                            event
                            for event in all_plan_events
                            if event.payload.get("plan_hash")
                            == linked_patch.payload.get("plan_hash")
                        ]
                plan_hashes = {str(event.payload["plan_hash"]) for event in plan_events}
                if len(plan_hashes) > 1:
                    raise RecoveryError("checkpoint found conflicting current-diff work plans")
                if plan_events:
                    current_plan = [str(plan_events[-1].payload["plan_hash"])]
                    plan_reproduction_status = plan_events[-1].payload.get("reproduction_status")
                    reproduction_status = (
                        "confirmed"
                        if plan_reproduction_status == "confirmed_failure"
                        else plan_reproduction_status
                    )
                    if reproduction_status not in {
                        "confirmed",
                        "not_reproduced",
                        "static_evidence",
                    }:
                        raise RecoveryError("checkpoint work plan status differs")
            elif manifest.context_policy_version in {
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
                active_work_state = project_active_work_state(
                    run_id=manifest.run_id,
                    task=evidence_task,
                    current_diff_hash=summary.patch_hash,
                    events=events,
                )
                if active_work_state is not None:
                    current_plan = [active_work_state.latest_plan.content_hash]
                    reproduction_status = {
                        "targeted_check_failed": "confirmed",
                        "targeted_check_passed": "not_reproduced",
                        "static_source": "static_evidence",
                    }.get(active_work_state.initial_plan.observation_status, "unknown")
            patch_events = [
                event
                for event in events
                if event.type == EventType.PATCH_APPLIED and event.payload.get("patch_hash")
            ]
            last_patch_hash = str(patch_events[-1].payload["patch_hash"]) if patch_events else None
            important_decisions = [
                {
                    "event_sequence": event.sequence,
                    "type": event.type.value,
                    "reason_code": event.payload.get("reason_code"),
                    "worktree_diff_hash": event.payload.get("worktree_diff_hash"),
                }
                for event in events
                if event.type
                in {
                    EventType.REVIEW_RECORDED,
                    EventType.PLAN_RECORDED,
                    EventType.EXPLORATION_STOP_RECORDED,
                    EventType.SUBMISSION_REJECTED,
                    EventType.SUBMISSION_ACCEPTED,
                }
            ][-5:]
        else:
            completed_checks = list(
                dict.fromkeys(
                    str(event.payload["check_id"])
                    for event in events
                    if event.type == EventType.TOOL_SUCCEEDED
                    and event.payload.get("tool") == "run_check"
                    and event.payload.get("passed") is True
                    and event.payload.get("check_id")
                )
            )
            pending_checks = []
            current_plan = []
            reproduction_status = "unknown"
            important_decisions = []
            last_patch_hash = (
                last_result.output.get("patch_hash")
                if last_result and last_result.status == "succeeded"
                else None
            )
        usage = usage or Usage()
        checkpoint = Checkpoint(
            checkpoint_id=f"ckpt_{uuid.uuid4().hex}",
            run_id=manifest.run_id,
            through_sequence=self.state.last_sequence(manifest.run_id),
            phase=phase,
            task_summary=manifest.task_id,
            reproduction_status=reproduction_status,
            current_plan=current_plan,
            modified_files=summary.changed_files,
            completed_action_ids=completed_actions,
            completed_checks=completed_checks,
            pending_checks=pending_checks,
            important_decisions=important_decisions,
            repository_head=head,
            worktree_diff_hash=summary.patch_hash,
            last_patch_hash=last_patch_hash,
            remaining_budget={
                **(
                    {"model_calls": (manifest.budget.max_model_calls - usage.model_calls)}
                    if manifest.budget.max_model_calls is not None
                    else {}
                ),
                **(
                    {"tool_calls": (manifest.budget.max_tool_calls - usage.tool_calls)}
                    if manifest.budget.max_tool_calls is not None
                    else {}
                ),
                "tokens": manifest.budget.max_total_tokens
                - usage.input_tokens
                - usage.output_tokens,
            },
            created_at=utc_now(),
        )
        self.state.save_checkpoint(checkpoint)
        self.state.append_event(
            manifest.run_id,
            EventType.CHECKPOINT_SAVED,
            actor="state-store",
            payload={
                "checkpoint_id": checkpoint.checkpoint_id,
                "through_sequence": checkpoint.through_sequence,
                "worktree_diff_hash": checkpoint.worktree_diff_hash,
            },
        )
        return checkpoint

    def _transition(self, run_id: str, current: Phase, target: Phase) -> Phase:
        validate_transition(current, target)
        self.state.append_event(
            run_id,
            EventType.PHASE_CHANGED,
            actor="phase-machine",
            payload={"from": current.value, "to": target.value},
        )
        return target

    @staticmethod
    def _generic_baseline_runtime_evidence_document(
        *,
        manifest: RunManifest,
        system_prompt: str,
        tool_schemas: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        frozen_comparison = AgentRunner._is_frozen_comparison_runtime_manifest(manifest)
        condition_neutral_v2 = AgentRunner._is_condition_neutral_runtime_v2_manifest(manifest)
        ac_fixed_bundle = AgentRunner._is_ac_fixed_bundle_readiness_manifest(manifest)
        heldout_ac = AgentRunner._is_heldout_ac_experiment(manifest)
        if manifest.experiment is None or (
            manifest.experiment.purpose
            not in {
                ExperimentPurpose.GENERIC_BASELINE_READINESS,
                ExperimentPurpose.WORKFLOW_COMPLETION_PROBE,
            }
            and not frozen_comparison
            and not condition_neutral_v2
            and not ac_fixed_bundle
            and not heldout_ac
        ):
            return None
        if heldout_ac:
            from patchloop.evals.heldout_ac_live_contract import (
                heldout_ac_runtime_evidence_document,
            )

            return heldout_ac_runtime_evidence_document(
                manifest=manifest,
                system_prompt=system_prompt,
                tool_schemas=tool_schemas,
            )
        if ac_fixed_bundle:
            from patchloop.evals.runner import (
                AC_FIXED_BUNDLE_COST_POLICY,
                AC_FIXED_BUNDLE_SPLIT_CALL_GUARD_POLICY,
                AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY,
                _ac_fixed_bundle_descriptor,
            )

            return {
                "schema_version": _AC_FIXED_BUNDLE_RUNTIME_EVIDENCE_SCHEMA,
                "experiment_id": manifest.experiment.experiment_id,
                "purpose": manifest.experiment.purpose.value,
                "suite_hash": manifest.experiment.suite_hash,
                "execution_hash": manifest.experiment.execution_hash,
                **(
                    {"campaign_cost_control_hash": (manifest.experiment.campaign_cost_control_hash)}
                    if manifest.experiment.experiment_id in AC_FIXED_BUNDLE_ALL_COST_EXPERIMENT_IDS
                    else {}
                ),
                "schedule_seed": manifest.experiment.schedule_seed,
                "schedule_order": manifest.experiment.schedule_order,
                "schedule_row_id": manifest.experiment.schedule_row_id,
                "repetition": manifest.experiment.repetition,
                "model_provider": manifest.model.provider,
                "model_id": manifest.model.model_id,
                "reasoning_effort": manifest.model.reasoning_effort,
                "reasoning_mode": manifest.model.reasoning_mode,
                "service_tier": manifest.model.service_tier,
                "transport_max_retries": manifest.model.transport_max_retries,
                "max_output_tokens": manifest.model.max_output_tokens,
                "budget": manifest.budget.model_dump(mode="json"),
                "memory_max_context_tokens": manifest.memory.max_context_tokens,
                "memory_condition": manifest.memory.condition.value,
                "memory_policy_version": manifest.memory_policy_version,
                "memory_index_version": manifest.memory.index_version,
                "memory_index_hash": manifest.memory.index_hash,
                "fixed_bundle": _ac_fixed_bundle_descriptor(),
                "full_schedule_cost_policy": (
                    AC_FIXED_BUNDLE_SPLIT_TOKEN_COST_POLICY
                    if manifest.experiment.experiment_id
                    in AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_IDS
                    else AC_FIXED_BUNDLE_COST_POLICY
                ),
                "system_prompt": system_prompt,
                "tools": tool_schemas,
                "tool_schema_version": manifest.tool_schema_version,
                "context_policy_version": manifest.context_policy_version,
                "call_guard_policy": (
                    AC_FIXED_BUNDLE_SPLIT_CALL_GUARD_POLICY
                    if manifest.experiment.experiment_id
                    in AC_FIXED_BUNDLE_SPLIT_BUDGET_EXPERIMENT_IDS
                    else _CONDITION_NEUTRAL_COMPARISON_CALL_GUARD_POLICY
                ),
            }
        if condition_neutral_v2:
            from patchloop.evals.runner import (
                _validated_comparison_resource_policy_v2,
                _validated_no_memory_admission_v1,
            )

            return {
                "schema_version": (_CONDITION_NEUTRAL_COMPARISON_RUNTIME_EVIDENCE_SCHEMA_V2),
                "comparison_resource_policy": (_validated_comparison_resource_policy_v2()),
                "baseline_admission": _validated_no_memory_admission_v1(),
                "experiment_id": manifest.experiment.experiment_id,
                "purpose": manifest.experiment.purpose.value,
                "suite_hash": manifest.experiment.suite_hash,
                "execution_hash": manifest.experiment.execution_hash,
                "campaign_cost_control_hash": (manifest.experiment.campaign_cost_control_hash),
                "schedule_seed": manifest.experiment.schedule_seed,
                "schedule_order": manifest.experiment.schedule_order,
                "schedule_row_id": manifest.experiment.schedule_row_id,
                "repetition": manifest.experiment.repetition,
                "model_provider": manifest.model.provider,
                "model_id": manifest.model.model_id,
                "reasoning_effort": manifest.model.reasoning_effort,
                "reasoning_mode": manifest.model.reasoning_mode,
                "service_tier": manifest.model.service_tier,
                "transport_max_retries": manifest.model.transport_max_retries,
                "max_output_tokens": manifest.model.max_output_tokens,
                "budget": manifest.budget.model_dump(mode="json"),
                "memory_max_context_tokens": manifest.memory.max_context_tokens,
                "memory_condition": manifest.memory.condition.value,
                "system_prompt": system_prompt,
                "tools": tool_schemas,
                "tool_schema_version": manifest.tool_schema_version,
                "context_policy_version": manifest.context_policy_version,
                "call_guard_policy": (_CONDITION_NEUTRAL_COMPARISON_CALL_GUARD_POLICY),
            }
        if frozen_comparison:
            # Local import avoids an import cycle while making RunStarted
            # evidence fail closed if the immutable D-083 policy bytes drift.
            from patchloop.evals.runner import (
                _validated_comparison_budget_policy,
            )

            return {
                "schema_version": (_CONDITION_NEUTRAL_COMPARISON_RUNTIME_EVIDENCE_SCHEMA),
                "comparison_budget_policy": (_validated_comparison_budget_policy()),
                "purpose": manifest.experiment.purpose.value,
                "model_provider": manifest.model.provider,
                "model_id": manifest.model.model_id,
                "reasoning_effort": manifest.model.reasoning_effort,
                "reasoning_mode": manifest.model.reasoning_mode,
                "service_tier": manifest.model.service_tier,
                "transport_max_retries": (manifest.model.transport_max_retries),
                "max_output_tokens": manifest.model.max_output_tokens,
                "budget": manifest.budget.model_dump(mode="json"),
                "memory_max_context_tokens": (manifest.memory.max_context_tokens),
                "memory_condition": manifest.memory.condition.value,
                "system_prompt": system_prompt,
                "tools": tool_schemas,
                "tool_schema_version": manifest.tool_schema_version,
                "context_policy_version": manifest.context_policy_version,
                "call_guard_policy": (_CONDITION_NEUTRAL_COMPARISON_CALL_GUARD_POLICY),
            }
        workflow_completion_probe = bool(
            manifest.experiment.purpose == ExperimentPurpose.WORKFLOW_COMPLETION_PROBE
        )
        generic_count_observability = bool(
            manifest.experiment.purpose == ExperimentPurpose.GENERIC_BASELINE_READINESS
            and manifest.experiment.experiment_id
            in {
                "generic-baseline-readiness-v2v5-20260803-r3",
                GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID,
            }
        )
        generic_high_headroom_readiness = bool(
            manifest.experiment.experiment_id == GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID
        )
        document = {
            "schema_version": (
                "workflow-completion-runtime-evidence-v1"
                if workflow_completion_probe
                else "generic-high-headroom-readiness-runtime-evidence-v1"
                if manifest.experiment.experiment_id
                == GENERIC_HIGH_HEADROOM_READINESS_EXPERIMENT_ID
                else "generic-baseline-runtime-evidence-v2"
                if generic_count_observability
                else "generic-baseline-runtime-evidence-v1"
            ),
            "transport_max_retries": manifest.model.transport_max_retries,
            "system_prompt": system_prompt,
            "tools": tool_schemas,
            "tool_schema_version": manifest.tool_schema_version,
            "context_policy_version": manifest.context_policy_version,
        }
        if workflow_completion_probe or generic_count_observability:
            document["call_guard_policy"] = "model-tool-observability-only-v1"
        if generic_high_headroom_readiness:
            document.update(
                {
                    "purpose": manifest.experiment.purpose.value,
                    "model_provider": manifest.model.provider,
                    "model_id": manifest.model.model_id,
                    "reasoning_effort": manifest.model.reasoning_effort,
                    "reasoning_mode": manifest.model.reasoning_mode,
                    "service_tier": manifest.model.service_tier,
                    "max_output_tokens": manifest.model.max_output_tokens,
                    "budget": manifest.budget.model_dump(mode="json"),
                    "memory_max_context_tokens": (manifest.memory.max_context_tokens),
                    "memory_condition": manifest.memory.condition.value,
                }
            )
        return document

    def _validate_generic_baseline_runtime_resume_contract(
        self,
        *,
        manifest: RunManifest,
        events: list[Any],
        system_prompt: str,
        tool_schemas: list[dict[str, Any]],
    ) -> None:
        expected = self._generic_baseline_runtime_evidence_document(
            manifest=manifest,
            system_prompt=system_prompt,
            tool_schemas=tool_schemas,
        )
        if expected is None:
            return
        started = [event for event in events if event.type == EventType.RUN_STARTED]
        try:
            if len(started) != 1:
                raise ValueError("expected one RunStarted event")
            event = started[0]
            artifact = Artifact.model_validate(event.payload.get("runtime_contract_artifact"))
            if (
                event.actor != "runner"
                or event.run_id != manifest.run_id
                or event.payload.get("task_id") != manifest.task_id
                or event.payload.get("artifact_role") != "runtime-contract"
                or event.payload.get("artifact_id") != artifact.artifact_id
                or event.payload.get("artifact_path") != artifact.path
                or artifact.media_type != "application/json; charset=utf-8"
            ):
                raise ValueError("runtime descriptor does not match RunStarted")
            observed = json.loads(self.artifacts.read_bytes(artifact).decode("utf-8"))
            if observed != expected:
                raise ValueError("runtime evidence bytes do not match the manifest")
        except (
            UnicodeDecodeError,
            ValueError,
            RecoveryError,
        ) as exc:
            raise RecoveryError("runtime contract artifact is invalid during recovery") from exc

    @staticmethod
    def _runtime_contract(
        manifest: RunManifest,
    ) -> tuple[str, list[dict[str, Any]]]:
        if manifest.tool_schema_version == "v1" and manifest.context_policy_version == "v1":
            return SYSTEM_PROMPT_V1, TOOL_SCHEMAS_V1
        if manifest.tool_schema_version == "v2" and manifest.context_policy_version in {
            "phase-evidence-v2",
            "phase-evidence-v3",
        }:
            return SYSTEM_PROMPT_V2, TOOL_SCHEMAS_V2
        if manifest.tool_schema_version == "v2" and manifest.context_policy_version in {
            "phase-evidence-v4",
            "phase-evidence-v5",
        }:
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V2
        if (
            manifest.tool_schema_version == "v3"
            and manifest.context_policy_version == "phase-evidence-v6"
        ):
            return SYSTEM_PROMPT_V4, TOOL_SCHEMAS_V3
        if manifest.tool_schema_version == "v4" and manifest.context_policy_version in {
            "phase-evidence-v7",
            "phase-evidence-v8",
        }:
            return SYSTEM_PROMPT_V5, TOOL_SCHEMAS_V4
        if (
            manifest.tool_schema_version == "v4"
            and manifest.context_policy_version == "phase-evidence-v9"
        ):
            return SYSTEM_PROMPT_V6, TOOL_SCHEMAS_V4
        if (
            manifest.tool_schema_version == "v5"
            and manifest.context_policy_version == "phase-evidence-v10"
        ):
            return SYSTEM_PROMPT_V7, TOOL_SCHEMAS_V5
        if (
            manifest.tool_schema_version == "v6"
            and manifest.context_policy_version == "phase-evidence-v11"
        ):
            return SYSTEM_PROMPT_V8, TOOL_SCHEMAS_V6
        if (
            manifest.tool_schema_version == "v7"
            and manifest.context_policy_version == "phase-evidence-v12"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V7
        if (
            manifest.tool_schema_version == "v8"
            and manifest.context_policy_version == "phase-evidence-v13"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V8
        if (
            manifest.tool_schema_version == "v9"
            and manifest.context_policy_version == "phase-evidence-v13"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V9
        if (
            manifest.tool_schema_version == "v9"
            and manifest.context_policy_version == "phase-evidence-v14"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V9
        if (
            manifest.tool_schema_version == "v10"
            and manifest.context_policy_version == "phase-evidence-v15"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V10
        if (
            manifest.tool_schema_version == "v10"
            and manifest.context_policy_version == "phase-evidence-v16"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V10
        if (
            manifest.tool_schema_version == "v11"
            and manifest.context_policy_version == "phase-evidence-v17"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V11
        if (
            manifest.tool_schema_version == "v12"
            and manifest.context_policy_version == "phase-evidence-v18"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V12
        if (
            manifest.tool_schema_version == "v13"
            and manifest.context_policy_version == "phase-evidence-v19"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V13
        if (
            manifest.tool_schema_version == "v14"
            and manifest.context_policy_version == "phase-evidence-v20"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V14
        if (
            manifest.tool_schema_version == "v15"
            and manifest.context_policy_version == "phase-evidence-v21"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V15
        if (
            manifest.tool_schema_version == "v16"
            and manifest.context_policy_version == "phase-evidence-v22"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V16
        if (
            manifest.tool_schema_version == "v17"
            and manifest.context_policy_version == "phase-evidence-v23"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V17
        if (
            manifest.tool_schema_version == "v18"
            and manifest.context_policy_version == "phase-evidence-v24"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V18
        if (
            manifest.tool_schema_version == "v19"
            and manifest.context_policy_version == "phase-evidence-v25"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V19
        if (
            manifest.tool_schema_version == "v20"
            and manifest.context_policy_version == "phase-evidence-v26"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V20
        if (
            manifest.tool_schema_version == "v21"
            and manifest.context_policy_version == "phase-evidence-v27"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V21
        if (
            manifest.tool_schema_version == "v22"
            and manifest.context_policy_version == "phase-evidence-v28"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V22
        if (
            manifest.tool_schema_version == "v23"
            and manifest.context_policy_version == "phase-evidence-v29"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V23
        if (
            manifest.tool_schema_version == "v24"
            and manifest.context_policy_version == "phase-evidence-v30"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V24
        if manifest.tool_schema_version == "v25" and manifest.context_policy_version in {
            "phase-evidence-v31",
            "phase-evidence-v32",
        }:
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V25
        if manifest.tool_schema_version == "v26" and manifest.context_policy_version in {
            "phase-evidence-v33",
            "phase-evidence-v34",
            "phase-evidence-v35",
        }:
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V26
        if (
            manifest.tool_schema_version == "v27"
            and manifest.context_policy_version == "phase-evidence-v36"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V27
        if manifest.tool_schema_version == "v28" and manifest.context_policy_version in {
            "phase-evidence-v37",
            "phase-evidence-v38",
        }:
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V28
        if (
            manifest.tool_schema_version == "v29"
            and manifest.context_policy_version == "phase-evidence-v38"
        ):
            return SYSTEM_PROMPT_V3, TOOL_SCHEMAS_V29
        raise ContractError("unsupported tool schema and context policy version combination")

    def _validate_legacy_submission(
        self,
        task: PublicTask,
        run_id: str,
        phase: Phase,
    ) -> None:
        passed_checks = {
            event.payload.get("check_id")
            for event in self.state.list_events(run_id)
            if event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "run_check"
            and event.payload.get("passed") is True
        }
        required_checks = {check.id for check in task.visible_checks}
        if not required_checks.issubset(passed_checks):
            raise ContractError(
                "DONE requires every registered visible check to have a passing result"
            )
        if phase != Phase.REVIEW:
            raise ContractError("DONE requires REVIEW phase under legacy schema v1")

    def _reject_unstructured_submission(
        self,
        run_id: str,
        workspace: Path,
        *,
        correlation_id: str,
    ) -> bool:
        summary = WorkspaceManager.diff_summary(workspace)
        attempt_number = 1 + sum(
            event.type == EventType.SUBMISSION_ATTEMPTED for event in self.state.list_events(run_id)
        )
        self.state.append_event(
            run_id,
            EventType.SUBMISSION_ATTEMPTED,
            actor="submission-gate",
            correlation_id=correlation_id,
            payload={
                "attempt_number": attempt_number,
                "worktree_diff_hash": summary.patch_hash,
                "submission_method": "legacy_done_text",
            },
        )
        self.state.append_event(
            run_id,
            EventType.SUBMISSION_REJECTED,
            actor="submission-gate",
            correlation_id=correlation_id,
            payload={
                "attempt_number": attempt_number,
                "worktree_diff_hash": summary.patch_hash,
                "submission_method": "legacy_done_text",
                "reason_code": "structured_finish_task_required",
                "missing_evidence": ["structured_finish_task"],
            },
        )
        return self._submission_rejection_count(run_id) > (_MAX_RECOVERABLE_SUBMISSION_REJECTIONS)

    def _finish_task(
        self,
        *,
        run_id: str,
        task: PublicTask,
        workspace: Path,
        phase: Phase,
        action_id: str,
        arguments: dict[str, Any],
        context_evidence: dict[str, Any],
        request_artifact_id: str,
        tool_schema_version: str,
        additional_missing_evidence: list[str],
    ) -> tuple[ToolResult, bool, bool]:
        input_hash = sha256_text(canonical_json({"tool": "finish_task", "input": arguments}))
        prior = self.state.get_action_result(run_id, action_id, input_hash)
        if prior is not None:
            accepted, should_stop = self._reconcile_finish_task_lifecycle(
                run_id,
                action_id,
                input_hash,
                prior,
            )
            replayed = prior.model_copy(update={"output": {**prior.output, "replayed": True}})
            return replayed, accepted, should_stop

        started = utc_now()
        summary = WorkspaceManager.diff_summary(workspace)
        readiness = diff_bound_evidence(
            task,
            self.state.list_events(run_id),
            summary.patch_hash,
            presented_tool_results=context_evidence.get("tool_results", []),
            phase=phase,
            structured_review_required=(tool_schema_version in {"v3", "v4", "v5", "v6"}),
            coverage_review_required=(tool_schema_version in {"v5", "v6"}),
        )
        missing_evidence = list(readiness.missing_evidence)
        missing_evidence.extend(additional_missing_evidence)
        if arguments:
            missing_evidence.append("empty_finish_arguments")
        attempt_number = 1 + sum(
            event.type == EventType.SUBMISSION_ATTEMPTED for event in self.state.list_events(run_id)
        )
        accepted = not missing_evidence
        if accepted:
            task_review_event = None
            task_review_artifact = None
            if tool_schema_version in {"v3", "v4", "v5", "v6"}:
                task_review_event = next(
                    (
                        event
                        for event in self.state.list_events(run_id)
                        if event.sequence == readiness.task_review_event_sequence
                    ),
                    None,
                )
                try:
                    task_review_artifact = Artifact.model_validate(
                        task_review_event.payload.get("review_artifact")
                        if task_review_event is not None
                        else None
                    )
                    review_document = json.loads(
                        self.artifacts.read_bytes(task_review_artifact).decode(
                            "utf-8", errors="strict"
                        )
                    )
                except (
                    OSError,
                    TypeError,
                    ValueError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ) as exc:
                    raise RecoveryError(
                        "accepted structured review artifact is unavailable"
                    ) from exc
                if (
                    review_document.get("schema_version")
                    != (
                        "task-review-v3"
                        if tool_schema_version in {"v5", "v6"}
                        else ("task-review-v2" if tool_schema_version == "v4" else "task-review-v1")
                    )
                    or review_document.get("run_id") != run_id
                    or review_document.get("worktree_diff_hash") != summary.patch_hash
                    or review_document.get("source_get_diff_sequence")
                    != readiness.review_event_sequence
                    or review_document.get("request_artifact_id")
                    != task_review_event.payload.get("request_artifact_id")
                    or task_review_artifact.content_hash
                    != task_review_event.payload.get("review_content_hash")
                ):
                    raise RecoveryError(
                        "structured review artifact conflicts with current trace evidence"
                    )
                if tool_schema_version in {"v4", "v5", "v6"}:
                    review_contract = self.state.get_manifest(run_id).public_review_contract
                    requirement_rows = review_document.get("requirements")
                    if (
                        review_contract is None
                        or review_document.get("public_review_contract_hash")
                        != review_contract.content_hash
                        or not isinstance(requirement_rows, list)
                        or {
                            item.get("requirement_id")
                            for item in requirement_rows
                            if isinstance(item, dict)
                        }
                        != {item.requirement_id for item in review_contract.requirements}
                        or len(requirement_rows) != len(review_contract.requirements)
                    ):
                        raise RecoveryError("task review does not cover its public contract")
                    if tool_schema_version in {"v5", "v6"}:
                        coverage_rows = review_document.get("coverage_targets")
                        coverage = review_document.get("public_review_coverage")
                        authoritative_target_ids = [
                            target.coverage_target_id
                            for requirement in review_contract.requirements
                            for target in requirement.coverage_targets
                        ]
                        if (
                            not isinstance(coverage_rows, list)
                            or [
                                item.get("coverage_target_id")
                                for item in coverage_rows
                                if isinstance(item, dict)
                            ]
                            != authoritative_target_ids
                            or not isinstance(coverage, dict)
                            or coverage.get("schema_version") != "public-review-coverage-v1"
                            or coverage.get("coverage_complete") is not True
                            or coverage.get("ready_for_submission") is not True
                            or coverage.get("authoritative_coverage_target_ids")
                            != authoritative_target_ids
                            or coverage.get("verified_coverage_target_ids")
                            != authoritative_target_ids
                            or coverage.get("unresolved_coverage_target_ids") != []
                            or task_review_event.payload.get("coverage_complete") is not True
                        ):
                            raise RecoveryError(
                                "task-review-v3 coverage decision is not submission-ready"
                            )
            submitted_patch_artifact = self.artifacts.put_text(
                summary.patch,
                "text/x-diff",
            )
            submitted_patch = submitted_patch_artifact.model_dump(mode="json")
            artifact_payload = {
                "tool": "finish_task",
                "status": "succeeded",
                "worktree_diff_hash": summary.patch_hash,
                "accepted_for_evaluation": True,
                "submitted_patch_artifact": submitted_patch,
                **(
                    {
                        "source_task_review_sequence": (readiness.task_review_event_sequence),
                        "task_review_artifact": (task_review_artifact.model_dump(mode="json")),
                        "task_review_content_hash": (task_review_artifact.content_hash),
                    }
                    if task_review_artifact is not None
                    else {}
                ),
            }
            artifact = self.artifacts.put_json(artifact_payload)
            result = ToolResult(
                action_id=action_id,
                status="succeeded",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    "worktree_diff_hash": summary.patch_hash,
                    "accepted_for_evaluation": True,
                    "submission_attempt_number": attempt_number,
                    "submission_method": "finish_task",
                    "source_get_diff_sequence": readiness.review_event_sequence,
                    "request_artifact_id": request_artifact_id,
                    "complete_tool_result": True,
                    "submitted_patch_artifact": submitted_patch,
                    **(
                        {
                            "source_task_review_sequence": (readiness.task_review_event_sequence),
                            "task_review_artifact": (task_review_artifact.model_dump(mode="json")),
                            "task_review_content_hash": (task_review_artifact.content_hash),
                        }
                        if task_review_artifact is not None
                        else {}
                    ),
                },
            )
        else:
            message = "submission is not ready: " + ", ".join(missing_evidence)
            artifact_payload = {
                "tool": "finish_task",
                "status": "rejected",
                "error_code": "SUBMISSION_NOT_READY",
                "error_message": message,
                "error_details": {
                    "missing_evidence": missing_evidence,
                    "recoverable": True,
                },
                "worktree_diff_hash": summary.patch_hash,
            }
            artifact = self.artifacts.put_json(artifact_payload)
            result = ToolResult(
                action_id=action_id,
                status="rejected",
                started_at=started,
                finished_at=utc_now(),
                output={
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                    "worktree_diff_hash": summary.patch_hash,
                    "error_details": artifact_payload["error_details"],
                    "submission_attempt_number": attempt_number,
                    "submission_method": "finish_task",
                },
                error_code="SUBMISSION_NOT_READY",
                error_message=message,
            )
        self.state.append_event(
            run_id,
            EventType.TOOL_CALLED,
            actor="agent",
            correlation_id=action_id,
            payload={
                "tool": "finish_task",
                "input_hash": input_hash,
                "recovery_result": result.model_dump(mode="json"),
            },
        )
        self.state.record_action_result(run_id, action_id, input_hash, result)
        durable_result = self.state.get_action_result(
            run_id,
            action_id,
            input_hash,
        )
        if durable_result is None:
            raise RecoveryError("finish_task action result was not durable after recording")
        accepted, should_stop = self._reconcile_finish_task_lifecycle(
            run_id,
            action_id,
            input_hash,
            durable_result,
        )
        return durable_result, accepted, should_stop

    def _reconcile_finish_task_lifecycle(
        self,
        run_id: str,
        action_id: str,
        input_hash: str,
        result: ToolResult,
    ) -> tuple[bool, bool]:
        """Append only a missing suffix for one durable finish_task decision."""

        attempt_number = result.output.get("submission_attempt_number")
        diff_hash = result.output.get("worktree_diff_hash")
        if not isinstance(attempt_number, int) or not isinstance(diff_hash, str):
            raise RecoveryError("finish_task result lacks durable submission decision metadata")
        accepted = bool(
            result.status == "succeeded" and result.output.get("accepted_for_evaluation") is True
        )
        manifest = self.state.get_manifest(run_id)
        source_tool_schema = manifest.tool_schema_version
        structured_review_required = source_tool_schema in {
            "v3",
            "v4",
            "v5",
            "v6",
        }
        source_task_review_sequence = None
        task_review_artifact = None
        task_review_content_hash = None
        expected: list[tuple[EventType, str, dict[str, Any]]] = [
            (
                EventType.TOOL_CALLED,
                "agent",
                {
                    "tool": "finish_task",
                    "input_hash": input_hash,
                },
            )
        ]
        if accepted:
            source_sequence = result.output.get("source_get_diff_sequence")
            request_artifact_id = result.output.get("request_artifact_id")
            if not isinstance(source_sequence, int) or not isinstance(
                request_artifact_id,
                str,
            ):
                raise RecoveryError("accepted finish_task result lacks final-review provenance")
            review_payload = {
                "worktree_diff_hash": diff_hash,
                "source_get_diff_sequence": source_sequence,
                "request_artifact_id": request_artifact_id,
                "complete_tool_result": True,
            }
            source_task_review_sequence = result.output.get("source_task_review_sequence")
            task_review_artifact = result.output.get("task_review_artifact")
            task_review_content_hash = result.output.get("task_review_content_hash")
            review_provenance_present = any(
                value is not None
                for value in (
                    source_task_review_sequence,
                    task_review_artifact,
                    task_review_content_hash,
                )
            )
            if structured_review_required or review_provenance_present:
                if (
                    not isinstance(source_task_review_sequence, int)
                    or not isinstance(task_review_artifact, dict)
                    or not isinstance(task_review_content_hash, str)
                ):
                    raise RecoveryError(
                        "accepted structured finish result has incomplete review provenance"
                    )
                try:
                    review_descriptor = Artifact.model_validate(task_review_artifact)
                    review_document = json.loads(
                        self.artifacts.read_bytes(review_descriptor).decode(
                            "utf-8", errors="strict"
                        )
                    )
                except (
                    OSError,
                    TypeError,
                    ValueError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ) as exc:
                    raise RecoveryError(
                        "accepted v3 finish result has an invalid review artifact"
                    ) from exc
                source_review = next(
                    (
                        event
                        for event in self.state.list_events(run_id)
                        if event.sequence == source_task_review_sequence
                    ),
                    None,
                )
                expected_review_schema = (
                    "task-review-v3"
                    if source_tool_schema in {"v5", "v6"}
                    else ("task-review-v2" if source_tool_schema == "v4" else "task-review-v1")
                )
                coverage_consistent = True
                if source_tool_schema in {"v5", "v6"}:
                    review_contract = manifest.public_review_contract
                    coverage_rows = review_document.get("coverage_targets")
                    coverage = review_document.get("public_review_coverage")
                    authoritative_target_ids = (
                        [
                            target.coverage_target_id
                            for requirement in review_contract.requirements
                            for target in requirement.coverage_targets
                        ]
                        if review_contract is not None
                        else []
                    )
                    coverage_consistent = bool(
                        review_contract is not None
                        and review_document.get("public_review_contract_hash")
                        == review_contract.content_hash
                        and isinstance(coverage_rows, list)
                        and all(isinstance(item, dict) for item in coverage_rows)
                        and [item.get("coverage_target_id") for item in coverage_rows]
                        == authoritative_target_ids
                        and isinstance(coverage, dict)
                        and coverage.get("schema_version") == "public-review-coverage-v1"
                        and coverage.get("authoritative_coverage_target_ids")
                        == authoritative_target_ids
                        and coverage.get("verified_coverage_target_ids") == authoritative_target_ids
                        and coverage.get("unresolved_coverage_target_ids") == []
                        and coverage.get("coverage_complete") is True
                        and coverage.get("ready_for_submission") is True
                        and source_review is not None
                        and source_review.payload.get("coverage_target_count")
                        == len(authoritative_target_ids)
                        and source_review.payload.get("coverage_complete") is True
                        and source_review.payload.get("verified_coverage_target_ids")
                        == authoritative_target_ids
                        and source_review.payload.get("unresolved_coverage_target_ids") == []
                    )
                if (
                    review_descriptor.content_hash != task_review_content_hash
                    or review_document.get("schema_version") != expected_review_schema
                    or review_document.get("run_id") != run_id
                    or review_document.get("worktree_diff_hash") != diff_hash
                    or source_review is None
                    or source_review.type != EventType.TOOL_SUCCEEDED
                    or source_review.payload.get("tool") != "review_task"
                    or source_review.payload.get("review_artifact") != task_review_artifact
                    or source_review.payload.get("review_content_hash") != task_review_content_hash
                    or source_review.payload.get("source_get_diff_sequence") != source_sequence
                    or not coverage_consistent
                ):
                    raise RecoveryError(
                        "accepted structured finish review provenance is inconsistent"
                    )
                review_payload.update(
                    {
                        "source_task_review_sequence": (source_task_review_sequence),
                        "task_review_artifact": task_review_artifact,
                        "task_review_content_hash": (task_review_content_hash),
                        "self_attestation": True,
                        "deterministic_correctness_claimed": False,
                    }
                )
            expected.append(
                (
                    EventType.REVIEW_RECORDED,
                    "submission-gate",
                    review_payload,
                )
            )
        expected.append(
            (
                EventType.SUBMISSION_ATTEMPTED,
                "submission-gate",
                {
                    "attempt_number": attempt_number,
                    "worktree_diff_hash": diff_hash,
                    "submission_method": "finish_task",
                },
            )
        )
        expected.append(
            (
                (EventType.TOOL_SUCCEEDED if accepted else EventType.TOOL_FAILED),
                "submission-gate",
                {
                    "tool": "finish_task",
                    "status": result.status,
                    "artifact_id": result.output.get("artifact_id"),
                    "artifact_path": result.output.get("artifact_path"),
                    "worktree_diff_hash": diff_hash,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "duration_ms": int(
                        (result.finished_at - result.started_at).total_seconds() * 1000
                    ),
                    "submitted_patch_artifact": result.output.get("submitted_patch_artifact"),
                    **(
                        {
                            "source_task_review_sequence": (source_task_review_sequence),
                            "task_review_artifact": task_review_artifact,
                            "task_review_content_hash": (task_review_content_hash),
                        }
                        if source_task_review_sequence is not None
                        else {}
                    ),
                },
            )
        )
        if accepted:
            expected.append(
                (
                    EventType.SUBMISSION_ACCEPTED,
                    "submission-gate",
                    {
                        "attempt_number": attempt_number,
                        "worktree_diff_hash": diff_hash,
                        "accepted_for": "deterministic_evaluation",
                        "evaluation_success_claimed": False,
                        "submitted_patch_artifact": result.output.get("submitted_patch_artifact"),
                        **(
                            {
                                "source_task_review_sequence": (source_task_review_sequence),
                                "task_review_artifact": (task_review_artifact),
                                "task_review_content_hash": (task_review_content_hash),
                            }
                            if source_task_review_sequence is not None
                            else {}
                        ),
                    },
                )
            )
        else:
            missing_evidence = result.output.get("error_details", {}).get(
                "missing_evidence",
                [],
            )
            expected.append(
                (
                    EventType.SUBMISSION_REJECTED,
                    "submission-gate",
                    {
                        "attempt_number": attempt_number,
                        "worktree_diff_hash": diff_hash,
                        "submission_method": "finish_task",
                        "reason_code": "submission_preconditions_missing",
                        "missing_evidence": missing_evidence,
                    },
                )
            )

        relevant_types = {
            EventType.TOOL_CALLED,
            EventType.TOOL_SUCCEEDED,
            EventType.TOOL_FAILED,
            EventType.REVIEW_RECORDED,
            EventType.SUBMISSION_ATTEMPTED,
            EventType.SUBMISSION_REJECTED,
            EventType.SUBMISSION_ACCEPTED,
        }
        existing = [
            event
            for event in self.state.list_events(run_id)
            if event.correlation_id == action_id and event.type in relevant_types
        ]
        expected_types = [item[0] for item in expected]
        existing_types = [event.type for event in existing]
        if existing_types != expected_types[: len(existing_types)]:
            raise RecoveryError("finish_task lifecycle is not a valid durable prefix")
        for event, (_, actor, payload) in zip(
            existing,
            expected[: len(existing)],
            strict=True,
        ):
            if event.actor != actor or any(
                event.payload.get(key) != value for key, value in payload.items()
            ):
                raise RecoveryError("finish_task lifecycle conflicts with its action result")
        for event_type, actor, payload in expected[len(existing) :]:
            self.state.append_event(
                run_id,
                event_type,
                actor=actor,
                correlation_id=action_id,
                payload=payload,
            )
        return (
            accepted,
            (
                not accepted
                and self._submission_rejection_count(run_id)
                > _MAX_RECOVERABLE_SUBMISSION_REJECTIONS
            ),
        )

    def _submission_rejection_count(self, run_id: str) -> int:
        return sum(
            event.type == EventType.SUBMISSION_REJECTED for event in self.state.list_events(run_id)
        )

    def _review_rejection_count(self, run_id: str) -> int:
        """Count failed structured reviews in the active mutation epoch."""

        events = self.state.list_events(run_id)
        mutation_sequence = max(
            (event.sequence for event in events if event.type == EventType.PATCH_APPLIED),
            default=0,
        )
        return sum(
            event.sequence > mutation_sequence
            and event.type == EventType.TOOL_FAILED
            and event.payload.get("tool") == "review_task"
            for event in events
        )

    def _reconcile_submission_recovery(
        self,
        *,
        manifest: RunManifest,
        task: PublicTask,
        workspace: Path,
        phase: Phase,
        usage: Usage,
    ) -> tuple[Phase, Checkpoint | None, ToolResult | None]:
        """Repair an interrupted structured submission before another call."""

        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        if manifest.tool_schema_version not in {
            "v2",
            "v3",
            "v4",
            "v5",
            "v6",
        }:
            return phase, checkpoint, None
        self._reconcile_unstructured_submission_lifecycle(manifest.run_id)
        calls: dict[str, Any] = {}
        for event in self.state.list_events(manifest.run_id):
            if event.type == EventType.TOOL_CALLED and event.payload.get("tool") == "finish_task":
                if event.correlation_id is None:
                    raise RecoveryError("finish_task ToolCalled event lacks correlation identity")
                if event.correlation_id in calls:
                    raise RecoveryError("finish_task action has duplicate ToolCalled events")
                calls[event.correlation_id] = event

        accepted_results: list[ToolResult] = []
        latest_rejected: ToolResult | None = None
        for action_id, call_event in calls.items():
            input_hash = call_event.payload.get("input_hash")
            if not isinstance(input_hash, str):
                raise RecoveryError("finish_task ToolCalled event lacks its input hash")
            result = self.state.get_action_result(
                manifest.run_id,
                action_id,
                input_hash,
            )
            if result is None:
                result = self._restore_finish_task_action_result(
                    manifest.run_id,
                    action_id,
                    input_hash,
                    call_event.payload.get("recovery_result"),
                )
            accepted, _ = self._reconcile_finish_task_lifecycle(
                manifest.run_id,
                action_id,
                input_hash,
                result,
            )
            if accepted:
                accepted_results.append(result)
            else:
                latest_rejected = result

        if len(accepted_results) > 1:
            raise RecoveryError("run contains more than one accepted finish_task action")
        rejection_count = self._submission_rejection_count(manifest.run_id)
        if accepted_results and rejection_count > _MAX_RECOVERABLE_SUBMISSION_REJECTIONS:
            raise RecoveryError("submission was accepted after the terminal rejection limit")
        if accepted_results:
            phase, checkpoint = self._complete_accepted_submission(
                manifest=manifest,
                task=task,
                workspace=workspace,
                phase=phase,
                usage=usage,
                result=accepted_results[0],
            )
            return phase, checkpoint, accepted_results[0]

        if rejection_count > _MAX_RECOVERABLE_SUBMISSION_REJECTIONS:
            raise SubmissionProtocolError("submission preconditions were rejected three times")
        if latest_rejected is not None:
            rejected_event = next(
                event
                for event in reversed(self.state.list_events(manifest.run_id))
                if event.type == EventType.SUBMISSION_REJECTED
                and event.correlation_id == latest_rejected.action_id
            )
            checkpoint = self.state.latest_checkpoint(manifest.run_id)
            if checkpoint is None or checkpoint.through_sequence < rejected_event.sequence:
                checkpoint = self._checkpoint(
                    manifest,
                    workspace,
                    phase,
                    usage,
                    latest_rejected,
                    task=task,
                )
            else:
                self._ensure_checkpoint_event(checkpoint)
        return phase, checkpoint, None

    def _restore_finish_task_action_result(
        self,
        run_id: str,
        action_id: str,
        input_hash: str,
        raw_result: Any,
    ) -> ToolResult:
        try:
            result = ToolResult.model_validate(raw_result)
        except (TypeError, ValueError) as exc:
            raise RecoveryError(
                "interrupted finish_task lacks a recoverable action result"
            ) from exc
        if result.action_id != action_id:
            raise RecoveryError("finish_task recovery result has a conflicting action identity")
        self.state.record_action_result(
            run_id,
            action_id,
            input_hash,
            result,
        )
        restored = self.state.get_action_result(
            run_id,
            action_id,
            input_hash,
        )
        if restored is None:
            raise RecoveryError("restored finish_task action result was not durable")
        return restored

    def _reconcile_unstructured_submission_lifecycle(
        self,
        run_id: str,
    ) -> None:
        attempts = [
            event
            for event in self.state.list_events(run_id)
            if event.type == EventType.SUBMISSION_ATTEMPTED
            and event.payload.get("submission_method") == "legacy_done_text"
        ]
        for attempt in attempts:
            if attempt.correlation_id is None:
                raise RecoveryError("v2 legacy-DONE rejection lacks correlation identity")
            outcomes = [
                event
                for event in self.state.list_events(run_id)
                if event.type == EventType.SUBMISSION_REJECTED
                and event.correlation_id == attempt.correlation_id
            ]
            if len(outcomes) > 1:
                raise RecoveryError("legacy-DONE attempt has duplicate rejection outcomes")
            expected_payload = {
                "attempt_number": attempt.payload.get("attempt_number"),
                "worktree_diff_hash": attempt.payload.get("worktree_diff_hash"),
                "submission_method": "legacy_done_text",
                "reason_code": "structured_finish_task_required",
                "missing_evidence": ["structured_finish_task"],
            }
            if outcomes:
                outcome = outcomes[0]
                if outcome.sequence <= attempt.sequence or any(
                    outcome.payload.get(key) != value for key, value in expected_payload.items()
                ):
                    raise RecoveryError("legacy-DONE rejection conflicts with its attempt")
                continue
            self.state.append_event(
                run_id,
                EventType.SUBMISSION_REJECTED,
                actor="submission-gate",
                correlation_id=attempt.correlation_id,
                payload=expected_payload,
            )

    def _complete_accepted_submission(
        self,
        *,
        manifest: RunManifest,
        task: PublicTask,
        workspace: Path,
        phase: Phase,
        usage: Usage,
        result: ToolResult,
    ) -> tuple[Phase, Checkpoint]:
        diff_hash = result.output.get("worktree_diff_hash")
        summary = WorkspaceManager.diff_summary(workspace)
        if not isinstance(diff_hash, str) or summary.patch_hash != diff_hash:
            raise RecoveryError("accepted submission does not match the current worktree diff")
        try:
            submitted_patch_artifact = Artifact.model_validate(
                result.output["submitted_patch_artifact"]
            )
            submitted_patch_bytes = Path(submitted_patch_artifact.path).read_bytes()
        except (KeyError, OSError, TypeError, ValueError) as exc:
            raise RecoveryError("accepted finish_task lacks its immutable patch artifact") from exc
        if (
            submitted_patch_artifact.content_hash != diff_hash
            or sha256_bytes(submitted_patch_bytes) != diff_hash
        ):
            raise RecoveryError("accepted finish_task patch artifact does not match its diff")
        accepted_events = [
            event
            for event in self.state.list_events(manifest.run_id)
            if event.type == EventType.SUBMISSION_ACCEPTED
        ]
        if (
            len(accepted_events) != 1
            or accepted_events[0].correlation_id != result.action_id
            or accepted_events[0].payload.get("worktree_diff_hash") != diff_hash
            or accepted_events[0].payload.get("submitted_patch_artifact")
            != submitted_patch_artifact.model_dump(mode="json")
        ):
            raise RecoveryError("accepted finish_task lacks one matching lifecycle event")
        accepted_event = accepted_events[0]
        done_transitions = [
            event
            for event in self.state.list_events(manifest.run_id)
            if event.type == EventType.PHASE_CHANGED
            and event.sequence > accepted_event.sequence
            and event.payload.get("from") == Phase.REVIEW.value
            and event.payload.get("to") == Phase.DONE.value
        ]
        if len(done_transitions) > 1:
            raise RecoveryError("accepted submission has duplicate DONE transitions")
        if done_transitions:
            phase = Phase.DONE
            done_transition = done_transitions[0]
        else:
            if phase != Phase.REVIEW:
                raise RecoveryError(
                    f"accepted submission cannot transition to DONE from {phase.value}"
                )
            phase = self._transition(
                manifest.run_id,
                phase,
                Phase.DONE,
            )
            done_transition = next(
                event
                for event in reversed(self.state.list_events(manifest.run_id))
                if event.type == EventType.PHASE_CHANGED
                and event.payload.get("from") == Phase.REVIEW.value
                and event.payload.get("to") == Phase.DONE.value
            )

        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        if (
            checkpoint is not None
            and checkpoint.phase == Phase.DONE
            and checkpoint.worktree_diff_hash == diff_hash
            and checkpoint.through_sequence >= done_transition.sequence
        ):
            self._ensure_checkpoint_event(checkpoint)
            return phase, checkpoint
        if checkpoint is not None and checkpoint.through_sequence >= done_transition.sequence:
            raise RecoveryError("checkpoint after submission acceptance is not a DONE checkpoint")
        checkpoint = self._checkpoint(
            manifest,
            workspace,
            phase,
            usage,
            result,
            task=task,
        )
        return phase, checkpoint

    def _ensure_checkpoint_event(self, checkpoint: Checkpoint) -> None:
        events = [
            event
            for event in self.state.list_events(checkpoint.run_id)
            if event.type == EventType.CHECKPOINT_SAVED
            and event.payload.get("checkpoint_id") == checkpoint.checkpoint_id
        ]
        if len(events) > 1:
            raise RecoveryError("checkpoint has duplicate CheckpointSaved events")
        expected = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "through_sequence": checkpoint.through_sequence,
            "worktree_diff_hash": checkpoint.worktree_diff_hash,
        }
        if events:
            if any(events[0].payload.get(key) != value for key, value in expected.items()):
                raise RecoveryError("CheckpointSaved event conflicts with durable checkpoint")
            return
        self.state.append_event(
            checkpoint.run_id,
            EventType.CHECKPOINT_SAVED,
            actor="state-store",
            payload=expected,
        )

    def _phase_after_tool(
        self,
        run_id: str,
        phase: Phase,
        tool: str,
        result: ToolResult,
        task: PublicTask,
        workspace: Path,
    ) -> Phase:
        if result.status != "succeeded":
            return phase
        if result.output.get("replayed") or result.output.get("admission_blocked"):
            return phase
        if tool == "record_work_plan":
            if phase != Phase.REPRODUCE:
                raise ContractError("record_work_plan requires the REPRODUCE phase")
            return self._transition(run_id, phase, Phase.PLAN)
        if tool in {"apply_patch", "apply_structured_edit"}:
            if phase == Phase.REPRODUCE:
                phase = self._transition(run_id, phase, Phase.PLAN)
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            if phase == Phase.PLAN:
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            if phase in {Phase.VERIFY, Phase.REVIEW}:
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            return phase
        if tool == "run_check":
            if phase == Phase.REVIEW:
                phase = self._transition(run_id, phase, Phase.IMPLEMENT)
            if result.output.get("passed") is True:
                if phase == Phase.IMPLEMENT:
                    return self._transition(run_id, phase, Phase.VERIFY)
                return phase
            if phase == Phase.VERIFY:
                return self._transition(run_id, phase, Phase.IMPLEMENT)
            return phase
        if (
            tool == "review_task"
            and result.output.get("review_schema_version") == "task-review-v3"
            and result.output.get("coverage_complete") is False
            and phase == Phase.REVIEW
        ):
            return self._transition(run_id, phase, Phase.IMPLEMENT)
        if tool == "get_diff":
            summary = WorkspaceManager.diff_summary(workspace)
            evidence = diff_bound_evidence(
                task,
                self.state.list_events(run_id),
                summary.patch_hash,
            )
            if (
                not evidence.mutation_present
                or evidence.pending_checks
                or evidence.review_event_sequence is None
            ):
                return phase
            if phase == Phase.REPRODUCE:
                phase = self._transition(run_id, phase, Phase.PLAN)
            if phase == Phase.PLAN:
                phase = self._transition(run_id, phase, Phase.IMPLEMENT)
            if phase == Phase.IMPLEMENT:
                phase = self._transition(run_id, phase, Phase.VERIFY)
            if phase == Phase.VERIFY:
                return self._transition(run_id, phase, Phase.REVIEW)
        return phase

    def _record_self_directed_exploration_stop(
        self,
        *,
        run_id: str,
        state: SelfDirectedExplorationState,
        action_id: str,
        arguments: dict[str, Any],
        model_event_sequence: int,
        request_artifact_id: str,
        request_body_hash: str,
    ) -> None:
        input_hash = sha256_text(
            canonical_json(
                {
                    "tool": "declare_exploration_exhausted",
                    "input": arguments,
                }
            )
        )
        prior = [
            event
            for event in self.state.list_events(run_id)
            if event.type == EventType.EXPLORATION_STOP_RECORDED
            and event.payload.get("plan_gate_id") == state.plan_gate_id
            and event.payload.get("worktree_diff_hash") == state.worktree_diff_hash
        ]
        if len(prior) > 1:
            raise RecoveryError("self-directed exploration stop repeats")
        if prior:
            if (
                prior[0].payload.get("action_id") != action_id
                or prior[0].payload.get("input_hash") != input_hash
            ):
                raise RecoveryError("self-directed exploration stop replay differs")
            return
        receipt = validate_exploration_stop(state=state, arguments=arguments)
        self.state.append_event(
            run_id,
            EventType.EXPLORATION_STOP_RECORDED,
            actor="workflow-state-machine",
            correlation_id=action_id,
            payload={
                **receipt,
                "action_id": action_id,
                "input_hash": input_hash,
                "model_event_sequence": model_event_sequence,
                "request_artifact_id": request_artifact_id,
                "request_body_hash": request_body_hash,
                "execution": "not_dispatched",
                "agent_terminal_code": SelfDirectedExplorationExhaustedError.code,
            },
        )

    @staticmethod
    def _task_dir(task_path: str | Path) -> Path:
        path = Path(task_path).resolve()
        return path.parent if path.is_file() else path

    def _find_task(self, manifest: RunManifest) -> Path:
        roots = (
            repository_root() / "tasks",
            repository_root() / "fixtures" / "task-packages",
        )
        for root in roots:
            if not root.is_dir():
                continue
            for public_path in root.rglob("public.yaml"):
                package = load_task_package(public_path.parent)
                if (
                    package.public.task_id == manifest.task_id
                    and package.public.task_version == manifest.task_version
                    and package.public_spec_hash == manifest.public_spec_hash
                ):
                    return public_path.parent
        raise RecoveryError(f"task package for run {manifest.run_id} is unavailable")

    def _model_adapter(
        self,
        model: str,
        manifest: RunManifest,
        completed_tools: list[str],
        probe_available: bool = False,
    ) -> ModelAdapter:
        if model == "mock":
            return MockModelAdapter(
                manifest.task_id,
                completed_tools,
                structured_finish=manifest.tool_schema_version
                in {
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
                },
                structured_review=manifest.tool_schema_version in {"v3", "v4", "v5", "v6"},
                structured_probe=(
                    manifest.tool_schema_version in {"v3", "v4", "v5", "v6"}
                    and manifest.probe_image_digest is not None
                    and probe_available
                ),
            )
        if model.startswith("replay:"):
            normalized_model, replay_path, replay_hash = self._replay_identity(model)
            if (
                manifest.model.provider != "replay"
                or manifest.model.model_id != normalized_model
                or manifest.model.replay_hash != replay_hash
            ):
                raise ContractError("replay source does not match the immutable run manifest")
            return ReplayModelAdapter(
                replay_path,
                len(completed_tools),
                expected_hash=manifest.model.replay_hash,
            )
        if model == "openai":
            if manifest.context_policy_version in {"phase-evidence-v37", "phase-evidence-v38"}:
                return StrictOpenAIResponsesAdapter(manifest.model)
            return OpenAIResponsesAdapter(manifest.model)
        raise ContractError(f"unknown model adapter: {model}")

    @staticmethod
    def _replay_identity(model: str) -> tuple[str, Path, str]:
        raw_path = model.split(":", 1)[1]
        relative = safe_relative_path(raw_path, field_name="replay path")
        replay_path = ensure_within(repository_root(), relative)
        if not replay_path.is_file():
            raise ContractError(f"replay file does not exist: {relative}")
        return (
            f"replay:{Path(relative).as_posix()}",
            replay_path,
            sha256_bytes(replay_path.read_bytes()),
        )

    def _reconcile_workspace(self, manifest: RunManifest, workspace: Path) -> None:
        checkpoint = self.state.latest_checkpoint(manifest.run_id)
        if checkpoint is None:
            raise RecoveryError("run has events but no durable checkpoint")
        self._reconcile_checkpoint_workspace(checkpoint, workspace)

    def _reconcile_checkpoint_workspace(
        self,
        checkpoint: Checkpoint,
        workspace: Path,
    ) -> None:
        if WorkspaceManager.untracked_files(workspace):
            raise RecoveryError("agent workspace contains untracked files during recovery")
        summary = WorkspaceManager.diff_summary(workspace)
        if summary.patch_hash != checkpoint.worktree_diff_hash:
            raise RecoveryError("workspace diff hash does not match the latest durable checkpoint")
        self._reconcile_workspace_head(checkpoint, workspace)

    def _recover_initial_prefix(
        self,
        manifest: RunManifest,
        workspace: Path,
        events,
    ) -> Phase:
        """Recover the narrow startup prefix before the first checkpoint."""

        expected_fault = (
            manifest.fault.type
            if manifest.fault.type in {"context-reset", "test-timeout"}
            else None
        )
        types = [event.type for event in events]
        allowed_prefix = [EventType.RUN_STARTED]
        if types[:1] != allowed_prefix:
            raise RecoveryError("run without a checkpoint has an invalid startup prefix")
        run_started = events[0]
        try:
            runtime_artifact = Path(str(run_started.payload["artifact_path"]))
        except KeyError as exc:
            raise RecoveryError("startup prefix lacks its runtime contract artifact") from exc
        if (
            run_started.actor != "runner"
            or run_started.payload.get("task_id") != manifest.task_id
            or not runtime_artifact.is_file()
        ):
            raise RecoveryError("startup prefix conflicts with the immutable run contract")

        index = 1
        if expected_fault is not None and len(events) > index:
            fault_event = events[index]
            if (
                fault_event.type != EventType.FAULT_INJECTED
                or fault_event.actor != "fault-injector"
                or fault_event.payload != {"fault": expected_fault}
            ):
                raise RecoveryError("run without a checkpoint has an invalid fault prefix")
            index += 1
        if expected_fault is not None and len(events) == 1:
            self.state.append_event(
                manifest.run_id,
                EventType.FAULT_INJECTED,
                actor="fault-injector",
                payload={"fault": expected_fault},
            )

        phase = Phase.INTAKE
        if len(events) > index:
            transition = events[index]
            if (
                transition.type != EventType.PHASE_CHANGED
                or transition.actor != "phase-machine"
                or transition.payload
                != {
                    "from": Phase.INTAKE.value,
                    "to": Phase.REPRODUCE.value,
                }
            ):
                raise RecoveryError("run without a checkpoint has an invalid phase prefix")
            phase = Phase.REPRODUCE
            index += 1
        if len(events) != index:
            raise RecoveryError("run without a checkpoint contains non-startup events")
        if WorkspaceManager.untracked_files(workspace):
            raise RecoveryError("startup workspace contains untracked files")
        summary = WorkspaceManager.diff_summary(workspace)
        if summary.patch_hash != sha256_text(""):
            raise RecoveryError("startup workspace changed before its first checkpoint")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if head.returncode != 0 or not head.stdout.strip():
            raise RecoveryError("startup workspace has no valid Git HEAD")
        return phase

    @staticmethod
    def _reconcile_workspace_head(
        checkpoint: Checkpoint,
        workspace: Path,
    ) -> None:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if head != checkpoint.repository_head:
            raise RecoveryError("workspace HEAD does not match the latest durable checkpoint")

    def _phase_after_checkpoint(self, checkpoint: Checkpoint) -> Phase:
        phase = checkpoint.phase
        for event in self.state.list_events(checkpoint.run_id):
            if (
                event.sequence <= checkpoint.through_sequence
                or event.type != EventType.PHASE_CHANGED
            ):
                continue
            try:
                source = Phase(str(event.payload["from"]))
                target = Phase(str(event.payload["to"]))
            except (KeyError, ValueError) as exc:
                raise RecoveryError("phase transition after checkpoint is malformed") from exc
            if source != phase:
                raise RecoveryError("phase transition after checkpoint is not contiguous")
            validate_transition(source, target)
            phase = target
        return phase

    def _completed_tools(self, run_id: str) -> list[str]:
        return [
            str(event.payload["tool"])
            for event in self.state.list_events(run_id)
            if event.type == EventType.TOOL_SUCCEEDED and event.payload.get("tool")
        ]

    @staticmethod
    def _docker_sandbox(package) -> DockerSandbox:
        if package.environment is not None:
            return DockerSandbox(package.environment.evaluator_image)
        return DockerSandbox()

    def _usage(self, run_id: str) -> Usage:
        usage = Usage()
        manifest = self.state.get_manifest(run_id)
        durable_counts = manifest.context_policy_version in {
            "phase-evidence-v37",
            "phase-evidence-v38",
        }
        for event in self.state.list_events(run_id):
            if event.type == EventType.MODEL_CALLED:
                usage.model_calls += 1
                usage.input_tokens += int(event.payload.get("input_tokens", 0))
                usage.cached_input_tokens += int(event.payload.get("cached_input_tokens", 0))
                usage.cache_write_input_tokens += int(
                    event.payload.get("cache_write_input_tokens", 0)
                )
                usage.output_tokens += int(event.payload.get("output_tokens", 0))
                usage.reasoning_output_tokens += int(
                    event.payload.get("reasoning_output_tokens", 0)
                )
                if not durable_counts:
                    usage.input_token_count_calls += int(
                        event.payload.get("input_token_count_calls", 0)
                    )
                usage.wall_clock_ms += int(event.payload.get("duration_ms", 0))
            elif event.type == EventType.TOOL_CALLED:
                usage.tool_calls += 1
            elif event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}:
                usage.wall_clock_ms += int(event.payload.get("duration_ms", 0))
            elif event.type == EventType.MODEL_GENERATION_BLOCKED:
                if not durable_counts:
                    usage.input_token_count_calls += int(
                        event.payload.get("input_token_count_calls", 0)
                    )
        if durable_counts:
            accounting = project_input_token_count_attempts(run_id, self.state.list_events(run_id))
            usage.input_token_count_calls = accounting["logical_attempts"]
            usage.wall_clock_ms += accounting["duration_ms"]
        usage.model_cost_usd = calculate_model_cost(usage, manifest.model)
        return usage

    @staticmethod
    def _pre_generation_budget_reason(
        manifest: RunManifest,
        usage: Usage,
    ) -> str | None:
        if (
            manifest.budget.max_model_calls is not None
            and usage.model_calls >= manifest.budget.max_model_calls
        ):
            return "model_call_budget_exhausted"
        if (
            manifest.budget.max_tool_calls is not None
            and usage.tool_calls >= manifest.budget.max_tool_calls
        ):
            return "tool_call_budget_exhausted"
        if usage.wall_clock_ms >= manifest.budget.wall_clock_timeout_seconds * 1000:
            return "wall_clock_budget_exhausted"
        return None

    def _block_model_generation(
        self,
        *,
        manifest: RunManifest,
        built_context: BuiltContext,
        request_artifact: Artifact,
        request_body_hash: str,
        reason_code: str,
        usage: Usage,
        requested_input_tokens: int | None = None,
        remaining_tokens: int | None = None,
        input_token_count_calls: int = 0,
        split_budget_evidence: dict[str, Any] | None = None,
    ) -> None:
        retry_evidence = built_context.evidence.get("rejected_mutation_retry")
        retry_present = bool(
            isinstance(retry_evidence, dict) and retry_evidence.get("included") is True
        )
        retry_candidate = (
            retry_evidence.get("candidate", {}) if isinstance(retry_evidence, dict) else {}
        )
        payload = {
            "reason_code": reason_code,
            "error_code": ModelGenerationBudgetError.code,
            "generation_started": False,
            "request_artifact_id": request_artifact.artifact_id,
            "request_artifact_path": request_artifact.path,
            "request_artifact_hash": request_artifact.content_hash,
            "request_body_hash": request_body_hash,
            "requested_input_tokens": requested_input_tokens,
            "remaining_tokens": remaining_tokens,
            "max_output_tokens": manifest.model.max_output_tokens,
            "input_token_count_calls": input_token_count_calls,
            "retry_context_present": retry_present,
            "retry_candidate_content_hash": (
                retry_candidate.get("content_hash") if isinstance(retry_candidate, dict) else None
            ),
        }
        if reason_code == "exact_request_budget_exceeded":
            if split_budget_evidence is None:
                payload["schema_version"] = _EXACT_REQUEST_GENERATION_BLOCK_SCHEMA
            else:
                payload.pop("remaining_tokens")
                payload.update(split_budget_evidence)
                payload["schema_version"] = _SPLIT_TOKEN_GENERATION_BLOCK_SCHEMA
        elif reason_code in _COUNTER_GENERATION_BLOCK_REASONS:
            optional_call_limits = bool(
                manifest.budget.max_model_calls is None or manifest.budget.max_tool_calls is None
            )
            payload.update(
                {
                    "schema_version": (
                        _OPTIONAL_COUNTER_GENERATION_BLOCK_SCHEMA
                        if optional_call_limits
                        else _COUNTER_GENERATION_BLOCK_SCHEMA
                    ),
                    "model_calls_used": usage.model_calls,
                    "max_model_calls": manifest.budget.max_model_calls,
                    "tool_calls_used": usage.tool_calls,
                    "max_tool_calls": manifest.budget.max_tool_calls,
                    "wall_clock_ms": usage.wall_clock_ms,
                    "wall_clock_timeout_ms": (manifest.budget.wall_clock_timeout_seconds * 1000),
                    "total_tokens_used": (usage.input_tokens + usage.output_tokens),
                    "max_total_tokens": manifest.budget.max_total_tokens,
                }
            )
            if optional_call_limits:
                payload["disabled_budget_dimensions"] = [
                    dimension
                    for dimension, limit in (
                        ("model_calls", manifest.budget.max_model_calls),
                        ("tool_calls", manifest.budget.max_tool_calls),
                    )
                    if limit is None
                ]
        self.state.append_event(
            manifest.run_id,
            EventType.MODEL_GENERATION_BLOCKED,
            actor="budget-guard",
            payload=payload,
        )
        if reason_code == "exact_request_budget_exceeded":
            message = (
                "remaining token budget cannot fund the exact input plus one bounded model response"
            )
        else:
            message = f"model generation blocked: {reason_code}"
        raise ModelGenerationBudgetError(message, details=payload)

    @staticmethod
    def _split_token_request_budget_evidence(
        manifest: RunManifest,
        usage: Usage,
        *,
        requested_input_tokens: int,
    ) -> dict[str, Any] | None:
        """Project one exact request against the versioned cumulative split limits."""

        budget = manifest.budget
        if budget.token_budget_schema_version != _SPLIT_TOKEN_BUDGET_SCHEMA:
            return None
        input_limit = budget.max_cumulative_input_tokens
        output_limit = budget.max_cumulative_output_tokens
        if input_limit is None or output_limit is None:
            raise ContractError("cumulative-split-v1 token limits are incomplete")

        input_used = usage.input_tokens
        output_used = usage.output_tokens
        total_used = input_used + output_used
        remaining_input = input_limit - input_used
        remaining_output = output_limit - output_used
        remaining_total = budget.max_total_tokens - total_used
        exceeded = {
            "input_tokens": requested_input_tokens > remaining_input,
            "output_tokens": manifest.model.max_output_tokens > remaining_output,
            "total_tokens": (
                requested_input_tokens + manifest.model.max_output_tokens > remaining_total
            ),
        }
        exceeded_dimensions = [
            dimension for dimension in _SPLIT_TOKEN_DIMENSION_ORDER if exceeded[dimension]
        ]
        return {
            "token_budget_schema_version": budget.token_budget_schema_version,
            "binding_dimension": (exceeded_dimensions[0] if exceeded_dimensions else None),
            "exceeded_dimensions": exceeded_dimensions,
            "input_tokens_used": input_used,
            "output_tokens_used": output_used,
            "total_tokens_used": total_used,
            "max_cumulative_input_tokens": input_limit,
            "max_cumulative_output_tokens": output_limit,
            "max_total_tokens": budget.max_total_tokens,
            "remaining_input_tokens": remaining_input,
            "remaining_output_tokens": remaining_output,
            "remaining_total_tokens": remaining_total,
        }

    def _assert_budget(self, manifest: RunManifest, usage: Usage) -> None:
        if (
            manifest.budget.max_model_calls is not None
            and usage.model_calls >= manifest.budget.max_model_calls
        ):
            raise ContractError("model call budget exhausted")
        if (
            manifest.budget.max_tool_calls is not None
            and usage.tool_calls >= manifest.budget.max_tool_calls
        ):
            raise ContractError("tool call budget exhausted")
        if usage.input_tokens + usage.output_tokens >= manifest.budget.max_total_tokens:
            raise ContractError("token budget exhausted")
        if manifest.budget.token_budget_schema_version == _SPLIT_TOKEN_BUDGET_SCHEMA and (
            usage.input_tokens >= manifest.budget.max_cumulative_input_tokens
            or usage.output_tokens >= manifest.budget.max_cumulative_output_tokens
        ):
            raise ContractError("split token budget exhausted")
        if usage.wall_clock_ms >= manifest.budget.wall_clock_timeout_seconds * 1000:
            raise ContractError("wall clock budget exhausted")

    @staticmethod
    def _assert_consumed_budget(manifest: RunManifest, usage: Usage) -> None:
        if (
            manifest.budget.max_model_calls is not None
            and usage.model_calls > manifest.budget.max_model_calls
        ):
            raise ContractError("model call budget exceeded")
        if usage.input_tokens + usage.output_tokens > manifest.budget.max_total_tokens:
            raise ContractError("token budget exceeded")
        if manifest.budget.token_budget_schema_version == _SPLIT_TOKEN_BUDGET_SCHEMA and (
            usage.input_tokens > manifest.budget.max_cumulative_input_tokens
            or usage.output_tokens > manifest.budget.max_cumulative_output_tokens
        ):
            raise ContractError("split token budget exceeded")
        if usage.wall_clock_ms > manifest.budget.wall_clock_timeout_seconds * 1000:
            raise ContractError("wall clock budget exceeded")


def run_from_cli(
    task: str | Path,
    *,
    model: str,
    memory_condition: MemoryCondition,
    self_validation: bool = False,
) -> dict[str, Any]:
    if model == "openai":
        raise ContractError("direct live runs are disabled; use an approved experiment-v2 suite")
    return AgentRunner().start(
        task,
        model=model,
        memory_condition=memory_condition,
        self_validation=self_validation,
    )


def resume_from_cli(run_id: str) -> dict[str, Any]:
    runner = AgentRunner()
    manifest = runner.state.get_manifest(run_id)
    if manifest.model.provider == "openai":
        raise ContractError(
            "direct live resume is disabled; approved campaign resume is not implemented"
        )
    return runner.resume(run_id)
