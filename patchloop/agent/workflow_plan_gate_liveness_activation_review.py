"""Offline activation review for the Lean V21 plan-gate liveness surface.

This module does not alter the runtime.  It measures already model-visible
public mock request artifacts, projects one explicitly counterfactual compact
feedback shape, and records why paid candidate preparation remains blocked.
"""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
    LeanHarnessRequestEvidenceV21,
    validate_persisted_lean_harness_request,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-plan-gate-liveness-activation-review-v1"
MEASUREMENT_SCHEMA_VERSION = "lean-v21-plan-request-size-measurement-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-plan-gate-liveness-activation-review-20260827-v1.json"
)

IMMUTABLE_INPUTS = {
    ("experiments/lean-harness-plan-gate-liveness-public-qualification-20260827-v1.json"): {
        "bytes": 5_617,
        "file_sha256": ("sha256:e45a36b595b64cdb5a098615a471fbb2c95c0e75301c1019c3ea8b19c10467bb"),
        "content_hash": ("sha256:dc1c5be75723ff9bd8269be362ee49c5c821f89f70a169ec4052a6edfbb71867"),
    }
}

SOURCE_FILES = (
    "patchloop/agent/workflow_plan_gate_liveness_activation_review.py",
    "patchloop/agent/workflow_plan_gate_liveness_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/context.py",
    "patchloop/agent/context_event_compaction.py",
    "patchloop/agent/tools.py",
    "scripts/build_lean_harness_plan_gate_liveness_activation_review.py",
    "tests/test_workflow_plan_gate_liveness_activation_review.py",
    "tests/test_workflow_successor_v2_runner.py",
)

_COMPACT_FEEDBACK_KEYS = (
    "schema_version",
    "policy_version",
    "execution",
    "attempt",
    "reason_codes",
    "guidance",
    "eligible_catalog_hash",
    "activated_exploration_plan_request_hash",
    "causal_plan_request_projection_hash",
    "plan_gate_id",
    "worktree_diff_hash",
    "request_artifact_id",
    "request_body_hash",
    "required_prior_hypothesis_disposition",
)


def _bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def _plan_feedback_event(context: dict[str, Any]) -> dict[str, Any] | None:
    events = context.get("recent_events")
    if not isinstance(events, list):
        raise ContractError("activation review context lacks recent events")
    selected = [
        event
        for event in events
        if isinstance(event, dict)
        and event.get("type") == "ToolFailed"
        and isinstance(event.get("payload"), dict)
        and event["payload"].get("tool") == "record_work_plan"
        and event["payload"].get("error_code") == "WORK_PLAN_ADMISSION_REJECTED"
    ]
    if len(selected) > 1:
        raise ContractError("activation review context repeats plan feedback")
    return selected[0] if selected else None


def measure_plan_request_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    """Measure one persisted V21 forced-plan request without reading reasoning."""

    evidence = validate_persisted_lean_harness_request(payload)
    if not isinstance(evidence, LeanHarnessRequestEvidenceV21):
        raise ContractError("activation review requires a Lean V21 request")
    if evidence.workflow_decision.allowed_tool_names != ("record_work_plan",):
        raise ContractError("activation review requires a forced plan request")
    body = evidence.request_body
    raw_context = body.get("context")
    if not isinstance(raw_context, str):
        raise ContractError("activation review request lacks string context")
    try:
        context = json.loads(raw_context)
    except json.JSONDecodeError as exc:
        raise ContractError("activation review context is not JSON") from exc
    if not isinstance(context, dict) or not isinstance(context.get("workflow"), dict):
        raise ContractError("activation review workflow context differs")
    workflow = context["workflow"]
    feedback = _plan_feedback_event(context)
    details = feedback["payload"].get("error_details") if feedback else None
    if details is not None and not isinstance(details, dict):
        raise ContractError("activation review plan feedback differs")

    result = {
        "schema_version": MEASUREMENT_SCHEMA_VERSION,
        "request_evidence_schema": evidence.schema_version,
        "readiness_source": evidence.plan_gate_readiness_source,
        "input_count_method": evidence.input_count_method,
        "canonical_request_body_bytes": _bytes(body),
        "model_context_utf8_bytes": len(raw_context.encode("utf-8")),
        "workflow_projection_bytes": _bytes(workflow),
        "recent_events_bytes": _bytes(context["recent_events"]),
        "tool_schema_bytes": _bytes(body.get("tools", [])),
        "eligible_catalog_bytes": _bytes(workflow.get("eligible_plan_evidence_catalog")),
        "readiness_snapshot_bytes": _bytes(workflow.get("plan_gate_readiness_snapshot")),
        "recovered_pin_bytes": _bytes(workflow.get("recovered_plan_gate_pin")),
        "activated_plan_request_bytes": _bytes(workflow.get("activated_exploration_plan_request")),
        "causal_plan_projection_bytes": _bytes(workflow.get("causal_plan_request_projection")),
        "plan_feedback_present": feedback is not None,
        "plan_feedback_event_bytes": _bytes(feedback) if feedback else 0,
        "plan_feedback_error_details_bytes": _bytes(details) if details else 0,
        "plan_feedback_nested_projection_bytes": (
            sum(
                _bytes(details.get(key))
                for key in (
                    "activated_exploration_plan_request",
                    "causal_plan_request_projection",
                    "eligible_plan_evidence_catalog",
                )
            )
            if details
            else 0
        ),
        "raw_reasoning_read": False,
        "private_task_material_read": False,
        "hidden_evaluator_material_read": False,
        "reference_patch_read": False,
    }
    return {**result, "content_hash": sha256_json(result)}


def project_compact_feedback_counterfactual(payload: dict[str, Any]) -> dict[str, Any]:
    """Estimate request bytes after a bounded model-facing feedback projection.

    The durable ToolFailed event and result artifact are not changed.  This is
    an offline projection, not an implemented successor result.
    """

    measurement = measure_plan_request_artifact(payload)
    evidence = validate_persisted_lean_harness_request(payload)
    body = copy.deepcopy(evidence.request_body)
    context = json.loads(body["context"])
    feedback = _plan_feedback_event(context)
    if feedback is None:
        raise ContractError("compact feedback projection requires one rejection")
    details = feedback["payload"].get("error_details")
    if not isinstance(details, dict):
        raise ContractError("compact feedback projection lacks typed details")
    feedback["payload"]["error_details"] = {
        key: details[key] for key in _COMPACT_FEEDBACK_KEYS if key in details
    }
    body["context"] = canonical_json(context)
    projected_bytes = _bytes(body)
    original_bytes = measurement["canonical_request_body_bytes"]
    result = {
        "schema_version": "lean-v21-compact-feedback-counterfactual-v1",
        "implemented": False,
        "durable_event_changed": False,
        "durable_result_artifact_changed": False,
        "original_request_body_bytes": original_bytes,
        "projected_request_body_bytes": projected_bytes,
        "projected_saved_bytes": original_bytes - projected_bytes,
        "projected_saved_ratio": round((original_bytes - projected_bytes) / original_bytes, 6),
        "retained_feedback_keys": _COMPACT_FEEDBACK_KEYS,
        "provider_input_tokens_measured": False,
    }
    return {**result, "content_hash": sha256_json(result)}


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"activation review source is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    try:
        document = json.loads(ensure_within(root, relative).read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("activation review input is not JSON") from exc
    content_hash = document.get("content_hash")
    if content_hash != sha256_json(
        {key: value for key, value in document.items() if key != "content_hash"}
    ):
        raise ContractError("activation review input content hash differs")
    identity["content_hash"] = content_hash
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable activation review input differs: {relative}")
    return identity


def build_plan_gate_liveness_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "candidate-preparation-blocked",
        "scope": "lean-v21-public-plan-gate-activation-review",
        "runtime_identity": {
            "runtime_policy_version": "lean-harness-v21",
            "tool_schema_version": "v25",
            "context_policy_version": "phase-evidence-v31",
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
        },
        "observed_offline_mock_request_ranges": {
            "provenance": "repeated-real-shaped-public-mock-runner-artifacts",
            "canonical_raw_traces": False,
            "current_request_observations": 8,
            "recovered_retry_observations": 5,
            "current_request_body_bytes": {"min": 63_846, "max": 63_958},
            "recovered_retry_body_bytes": {"min": 110_264, "max": 110_503},
            "current_recent_events_bytes": {"min": 6_111, "max": 6_135},
            "recovered_recent_events_bytes": {"min": 42_954, "max": 43_130},
            "paired_request_growth_ratio": {"min": 1.7257, "max": 1.7277},
            "exact_provider_input_tokens_measured": False,
            "request_artifact_bytes_are_provider_input": False,
        },
        "representative_retry_attribution": {
            "request_body_bytes": 110_264,
            "model_context_bytes": 94_057,
            "workflow_projection_bytes": 45_349,
            "recent_events_bytes": 42_954,
            "recovered_pin_bytes": 4_865,
            "plan_feedback_event_bytes": 36_123,
            "plan_feedback_error_details_bytes": 34_598,
            "duplicated_nested_projection_bytes": 33_360,
            "nested_projection_components": {
                "activated_exploration_plan_request": 21_287,
                "causal_plan_request_projection": 9_342,
                "eligible_plan_evidence_catalog": 2_731,
            },
        },
        "counterfactual_compact_projection": {
            "implemented": False,
            "representative_original_request_body_bytes": 110_264,
            "representative_projected_request_body_bytes": 72_965,
            "representative_projected_saved_bytes": 37_299,
            "representative_projected_saved_ratio": 0.338,
            "durable_event_or_result_changed": False,
        },
        "trace_shape_audit": {
            "successful_plan": [
                "ModelCalled(current_request)",
                "ToolCalled(record_work_plan)",
                "PlanRecorded",
                "CausalMechanismRecorded",
                "ExplorationClosureRecorded",
                "ToolSucceeded(record_work_plan)",
            ],
            "bounded_rejection": [
                "ModelCalled(current_request)",
                "ToolFailed(record_work_plan)",
                "ToolAdmissionBlocked(attempt=1)",
                "ModelCalled(recovered_pin)",
                "ToolFailed(record_work_plan)",
                "ToolAdmissionBlocked(attempt=2)",
                "RunFailed(WORK_PLAN_ADMISSION_REPEATED)",
            ],
            "restart": [
                "ToolAdmissionBlocked(attempt=1)",
                "restart",
                "ModelCalled(recovered_pin)",
                "PlanRecorded(exactly_once)",
            ],
            "model_call_after_second_rejection": False,
            "patch_before_valid_plan": False,
        },
        "fail_closed_audit": {
            "exact_cas_path_and_sha_checked": True,
            "persisted_request_schema_and_content_hash_checked": True,
            "model_event_request_body_hash_checked": True,
            "prior_recovered_pin_chain_checked": True,
            "stale_run_diff_gate_rejected": True,
            "missing_artifact_fault_injection": True,
            "tampered_body_binding_fault_injection": True,
            "tampered_pin_chain_fault_injection": True,
        },
        "decision": {
            "candidate_preparation_ready": False,
            "blocking_failure_class": "model-visible-plan-admission-feedback-bloat",
            "reason": (
                "The forced retry is correct but repeats full plan projections in recent "
                "ToolFailed feedback, confounding the next paid comparison with avoidable "
                "input overhead."
            ),
            "next_work": "versioned-bounded-plan-admission-feedback-projection",
            "runtime_source_change_in_this_review": False,
            "rapid_candidate_created": False,
        },
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_inputs": [_immutable_identity(root, relative) for relative in IMMUTABLE_INPUTS],
        "evidence_boundary": {
            "public_mock_request_structure_only": True,
            "raw_reasoning_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
        },
        "quality_improvement_established": False,
        "generalization_established": False,
        "paid_execution_authorized": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("activation review content hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_plan_gate_liveness_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_plan_gate_liveness_activation_review(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(review_bytes(value))
    return value


def load_plan_gate_liveness_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("activation review is unavailable") from exc
    if review_bytes(value) != raw:
        raise ContractError("activation review bytes differ")
    if value != build_plan_gate_liveness_activation_review(root):
        raise ContractError("activation review source binding differs")
    return value


__all__ = [
    "IMMUTABLE_INPUTS",
    "MEASUREMENT_SCHEMA_VERSION",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_plan_gate_liveness_activation_review",
    "load_plan_gate_liveness_activation_review",
    "materialize_plan_gate_liveness_activation_review",
    "measure_plan_request_artifact",
    "project_compact_feedback_counterfactual",
    "review_bytes",
]
