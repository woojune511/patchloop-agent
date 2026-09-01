"""Offline activation review for Lean V22 bounded plan feedback.

The review reads only persisted public mock request artifacts and the matching
durable public failure/result payloads.  It neither changes the runtime nor
creates a Rapid candidate.  Canonical JSON byte counts are request-structure
measurements, not provider token, latency, cost, or coding-quality evidence.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V22,
    LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
    LEAN_RUNTIME_POLICY_VERSION_V22,
    LEAN_TOOL_SCHEMA_VERSION_V22,
    LeanHarnessRequestEvidenceV22,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.workflow_plan_admission_feedback_successor import (
    BoundedWorkPlanAdmissionFeedback,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-plan-admission-feedback-activation-review-v1"
MEASUREMENT_SCHEMA_VERSION = "lean-v22-plan-feedback-request-measurement-v1"
PAIR_ASSESSMENT_SCHEMA_VERSION = "lean-v22-plan-feedback-request-pair-assessment-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-plan-admission-feedback-activation-review-20260827-v1.json"
)

ADMISSION_THRESHOLDS = {
    "current_plan_request_max_bytes": 65_000,
    "recovered_retry_request_max_bytes": 90_000,
    "recovered_retry_growth_ratio_max": 1.25,
    "minimum_context_bytes_saved": 30_000,
    "projected_error_details_max_bytes": 4_096,
    "residual_full_projection_duplicate_max_count": 0,
}

IMMUTABLE_INPUTS = {
    "experiments/lean-harness-plan-admission-feedback-public-qualification-20260827-v1.json": {
        "bytes": 5_281,
        "file_sha256": ("sha256:abeed7280c1f8fdd1e32c90e7a10c09da0c55647be81c711839d53470c3cf0dc"),
        "content_hash": ("sha256:57f3b3e5cf9e58f3318da5d60b5dbee4d2fe050b72ee09a3b19b6462e9a0d30e"),
    },
    "experiments/lean-harness-plan-gate-liveness-public-qualification-20260827-v1.json": {
        "bytes": 5_617,
        "file_sha256": ("sha256:e45a36b595b64cdb5a098615a471fbb2c95c0e75301c1019c3ea8b19c10467bb"),
        "content_hash": ("sha256:dc1c5be75723ff9bd8269be362ee49c5c821f89f70a169ec4052a6edfbb71867"),
    },
    "experiments/lean-harness-plan-gate-liveness-activation-review-20260827-v1.json": {
        "bytes": 5_559,
        "file_sha256": ("sha256:aabe212ab3c036cc39c96cc933dd27faf4355b2de7b000381bd135224aa2a69d"),
        "content_hash": ("sha256:86a5800969eabd7327d37f5e6414f9ba279ee094cbcc417679b6e176a26b18f9"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_plan_admission_feedback_activation_review.py",
    "patchloop/agent/workflow_plan_admission_feedback_successor.py",
    "patchloop/agent/workflow_plan_admission_feedback_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/context.py",
    "patchloop/agent/context_event_compaction.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_plan_admission_feedback_activation_review.py",
    "tests/test_workflow_plan_admission_feedback_activation_review.py",
    "tests/test_workflow_plan_admission_feedback_runner.py",
)

_OMITTED_WORKFLOW_FIELDS = (
    "eligible_plan_evidence_catalog",
    "activated_exploration_plan_request",
    "causal_plan_request_projection",
    "semantic_progress_state",
    "cross_reset_failure_trigger",
    "causal_mechanism_history",
)
_RETAINED_ACTION_FIELDS = (
    "plan_gate_id",
    "attempt",
    "reason_codes",
    "guidance",
    "eligible_catalog_hash",
    "activated_exploration_plan_request_hash",
    "causal_plan_request_projection_hash",
    "required_prior_hypothesis_disposition",
    "worktree_diff_hash",
    "request_artifact_id",
    "request_body_hash",
    "execution",
)


def _bytes(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def _content_hash(value: dict[str, Any], *, label: str) -> str:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    expected = sha256_json(body)
    if value.get("content_hash") != expected:
        raise ContractError(f"{label} content hash differs")
    return expected


def _workflow_key_counts(value: Any) -> dict[str, int]:
    counts = {field: 0 for field in _OMITTED_WORKFLOW_FIELDS}

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if key in counts:
                    counts[key] += 1
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(value)
    return counts


def _plan_feedback_events(context: dict[str, Any]) -> list[dict[str, Any]]:
    events = context.get("recent_events")
    if not isinstance(events, list):
        raise ContractError("V22 activation review context lacks recent events")
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
        raise ContractError("V22 activation review repeats plan feedback")
    return selected


def _validate_omitted_source_values(
    *,
    feedback: dict[str, Any],
    source_details: dict[str, Any],
) -> tuple[int, int]:
    descriptors = feedback.get("omitted_details")
    if not isinstance(descriptors, list):
        raise ContractError("V22 activation review lacks omission descriptors")
    source_value_bytes = 0
    embedded_values = 0
    feedback_text = canonical_json(feedback)
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ContractError("V22 activation review omission descriptor differs")
        field = descriptor.get("field")
        if field not in source_details:
            raise ContractError("V22 activation review omitted source field is unavailable")
        value = source_details[field]
        canonical_bytes = _bytes(value)
        if (
            descriptor.get("value_hash") != sha256_json(value)
            or descriptor.get("canonical_bytes") != canonical_bytes
        ):
            raise ContractError("V22 activation review omission binding differs")
        source_value_bytes += canonical_bytes
        if isinstance(value, (dict, list)) and canonical_json(value) in feedback_text:
            embedded_values += 1
    return source_value_bytes, embedded_values


def measure_plan_feedback_request_artifact(
    payload: dict[str, Any],
    *,
    durable_error_details: dict[str, Any] | None = None,
    result_error_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure one forced-plan V22 request and verify its public bindings."""

    evidence = validate_persisted_lean_harness_request(payload)
    if not isinstance(evidence, LeanHarnessRequestEvidenceV22):
        raise ContractError("activation review requires a Lean V22 request")
    if evidence.workflow_decision.allowed_tool_names != ("record_work_plan",):
        raise ContractError("activation review requires a forced plan request")
    body = evidence.request_body
    raw_context = body.get("context")
    if not isinstance(raw_context, str):
        raise ContractError("activation review request lacks string context")
    try:
        context = json.loads(raw_context)
    except json.JSONDecodeError as exc:
        raise ContractError("activation review request context is not JSON") from exc
    if not isinstance(context, dict) or not isinstance(context.get("workflow"), dict):
        raise ContractError("activation review workflow context differs")

    projection = evidence.plan_admission_feedback_projection
    feedback_events = _plan_feedback_events(context)
    if len(feedback_events) != projection.projected_event_count:
        raise ContractError("activation review projected feedback inventory differs")
    key_counts = _workflow_key_counts(context)
    if any(count != 1 for count in key_counts.values()):
        raise ContractError("activation review retains residual workflow projection duplication")

    feedback: dict[str, Any] | None = None
    source_value_bytes = 0
    embedded_source_values = 0
    durable_binding_validated = False
    result_binding_validated = False
    projected_details_bytes = 0
    source_details_bytes = 0
    full_nested_feedback_fields: list[str] = []
    actionable_fields_retained = False

    if projection.projected_event_count == 0:
        if durable_error_details is not None or result_error_details is not None:
            raise ContractError("current V22 request received unexpected durable feedback")
    else:
        if (
            len(projection.event_projections) != 1
            or durable_error_details is None
            or result_error_details is None
        ):
            raise ContractError("recovered V22 request requires one durable result binding")
        feedback = feedback_events[0]["payload"].get("error_details")
        if not isinstance(feedback, dict):
            raise ContractError("activation review projected feedback differs")
        try:
            delivered = BoundedWorkPlanAdmissionFeedback.model_validate_json(
                canonical_json(feedback)
            )
        except ValueError as exc:
            raise ContractError("activation review projected feedback is invalid") from exc
        record = projection.event_projections[0]
        if (
            sha256_json(durable_error_details) != record.source_error_details_hash
            or delivered.source_error_details_hash != record.source_error_details_hash
        ):
            raise ContractError("activation review durable detail binding differs")
        if result_error_details != durable_error_details:
            raise ContractError("activation review durable result artifact differs")
        if (
            sha256_json(feedback) != record.projected_error_details_hash
            or _bytes(feedback) != record.projected_error_details_bytes
        ):
            raise ContractError("activation review projected detail binding differs")
        source_value_bytes, embedded_source_values = _validate_omitted_source_values(
            feedback=feedback,
            source_details=durable_error_details,
        )
        full_nested_feedback_fields = sorted(set(feedback) & set(_OMITTED_WORKFLOW_FIELDS))
        if full_nested_feedback_fields or embedded_source_values:
            raise ContractError("activation review feedback retains full omitted values")
        actionable_fields_retained = all(field in feedback for field in _RETAINED_ACTION_FIELDS)
        if not actionable_fields_retained:
            raise ContractError("activation review feedback lost actionable fields")
        durable_binding_validated = True
        result_binding_validated = True
        projected_details_bytes = _bytes(feedback)
        source_details_bytes = _bytes(durable_error_details)

    workflow = context["workflow"]
    residual_duplicate_count = sum(max(0, count - 1) for count in key_counts.values())
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
        "source_context_bytes": projection.source_context_bytes,
        "projected_context_bytes": projection.projected_context_bytes,
        "context_bytes_saved": projection.context_bytes_saved,
        "projected_event_count": projection.projected_event_count,
        "plan_feedback_event_bytes": _bytes(feedback_events[0]) if feedback_events else 0,
        "durable_error_details_bytes": source_details_bytes,
        "projected_error_details_bytes": projected_details_bytes,
        "omitted_source_value_bytes": source_value_bytes,
        "embedded_full_omitted_value_count": embedded_source_values,
        "full_nested_feedback_fields": full_nested_feedback_fields,
        "workflow_projection_field_occurrences": key_counts,
        "residual_full_projection_duplicate_count": residual_duplicate_count,
        "actionable_feedback_fields_retained": actionable_fields_retained,
        "durable_event_detail_binding_validated": durable_binding_validated,
        "durable_result_artifact_binding_validated": result_binding_validated,
        "projection_evidence_hash": projection.content_hash,
        "raw_reasoning_read": False,
        "private_task_material_read": False,
        "hidden_evaluator_material_read": False,
        "reference_patch_read": False,
    }
    return {**result, "content_hash": sha256_json(result)}


def assess_plan_feedback_request_pair(
    current: dict[str, Any],
    recovered: dict[str, Any],
) -> dict[str, Any]:
    """Apply the activation thresholds to one current/recovered request pair."""

    _content_hash(current, label="current request measurement")
    _content_hash(recovered, label="recovered request measurement")
    if (
        current.get("schema_version") != MEASUREMENT_SCHEMA_VERSION
        or recovered.get("schema_version") != MEASUREMENT_SCHEMA_VERSION
        or current.get("readiness_source") != "current_request"
        or recovered.get("readiness_source") != "recovered_pin"
        or current.get("projected_event_count") != 0
        or recovered.get("projected_event_count") != 1
    ):
        raise ContractError("activation review request pair differs")

    current_bytes = current["canonical_request_body_bytes"]
    recovered_bytes = recovered["canonical_request_body_bytes"]
    growth_ratio = round(recovered_bytes / current_bytes, 6)
    checks = {
        "current_request_within_ceiling": (
            current_bytes <= ADMISSION_THRESHOLDS["current_plan_request_max_bytes"]
        ),
        "recovered_request_within_ceiling": (
            recovered_bytes <= ADMISSION_THRESHOLDS["recovered_retry_request_max_bytes"]
        ),
        "retry_growth_within_ceiling": (
            growth_ratio <= ADMISSION_THRESHOLDS["recovered_retry_growth_ratio_max"]
        ),
        "minimum_context_savings_met": (
            recovered["context_bytes_saved"] >= ADMISSION_THRESHOLDS["minimum_context_bytes_saved"]
        ),
        "projected_details_within_ceiling": (
            recovered["projected_error_details_bytes"]
            <= ADMISSION_THRESHOLDS["projected_error_details_max_bytes"]
        ),
        "no_full_projection_duplication": (
            recovered["residual_full_projection_duplicate_count"]
            <= ADMISSION_THRESHOLDS["residual_full_projection_duplicate_max_count"]
            and recovered["embedded_full_omitted_value_count"] == 0
            and recovered["full_nested_feedback_fields"] == []
        ),
        "actionable_feedback_retained": recovered["actionable_feedback_fields_retained"],
        "durable_event_and_result_bound": (
            recovered["durable_event_detail_binding_validated"]
            and recovered["durable_result_artifact_binding_validated"]
        ),
    }
    body = {
        "schema_version": PAIR_ASSESSMENT_SCHEMA_VERSION,
        "thresholds": ADMISSION_THRESHOLDS,
        "current_measurement_hash": current["content_hash"],
        "recovered_measurement_hash": recovered["content_hash"],
        "current_request_body_bytes": current_bytes,
        "recovered_request_body_bytes": recovered_bytes,
        "recovered_retry_growth_ratio": growth_ratio,
        "checks": checks,
        "candidate_preparation_pair_ready": all(checks.values()),
        "provider_input_tokens_measured": False,
        "provider_latency_measured": False,
        "agent_quality_measured": False,
    }
    return {**body, "content_hash": sha256_json(body)}


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
    identity["content_hash"] = _content_hash(document, label="activation review input")
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable activation review input differs: {relative}")
    return identity


def build_plan_admission_feedback_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build the deterministic decision artifact without running the mock runner."""

    root = Path(repository).resolve()
    criteria = {
        "sample_current_request_max_within_ceiling": (
            ADMISSION_THRESHOLDS["current_plan_request_max_bytes"] >= 64_197
        ),
        "sample_recovered_request_max_within_ceiling": (
            ADMISSION_THRESHOLDS["recovered_retry_request_max_bytes"] >= 74_383
        ),
        "sample_growth_max_within_ceiling": (
            ADMISSION_THRESHOLDS["recovered_retry_growth_ratio_max"] >= 1.160489
        ),
        "sample_context_savings_minimum_met": (
            ADMISSION_THRESHOLDS["minimum_context_bytes_saved"] <= 82_291
        ),
        "sample_projected_details_within_ceiling": (
            ADMISSION_THRESHOLDS["projected_error_details_max_bytes"] >= 2_055
        ),
        "residual_full_projection_duplicate_count_zero": True,
        "durable_event_and_result_payload_match": True,
        "restart_recovered_pin_exactly_once": True,
        "second_rejection_stops_before_third_model_call": True,
        "persisted_projection_tamper_fails_closed": True,
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "candidate-preparation-ready",
        "scope": "lean-v22-public-plan-admission-feedback-activation-review",
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V22,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V22,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V22,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
            "projection_policy_version": LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22,
        },
        "admission_thresholds": ADMISSION_THRESHOLDS,
        "observed_offline_public_mock_sample": {
            "provenance": "three-real-shaped-public-mock-request-pairs",
            "canonical_raw_traces": False,
            "request_pairs": 3,
            "restart_pairs": 1,
            "current_request_body_bytes": {"min": 63_839, "max": 64_197},
            "recovered_retry_body_bytes": {"min": 73_930, "max": 74_383},
            "paired_request_growth_ratio": {"min": 1.15807, "max": 1.160489},
            "recovered_source_context_bytes": {"min": 103_484, "max": 103_747},
            "recovered_projected_context_bytes": {"min": 21_193, "max": 21_377},
            "recovered_context_bytes_saved": {"min": 82_291, "max": 82_500},
            "durable_error_details_bytes": {"min": 34_620, "max": 34_829},
            "projected_error_details_bytes": {"min": 2_055, "max": 2_055},
            "full_projection_field_occurrences_per_request": 1,
            "residual_full_projection_duplicate_count": 0,
            "visible_check_calls": 0,
            "provider_input_tokens_measured": False,
            "request_artifact_bytes_are_provider_input": False,
        },
        "binding_and_recovery_audit": {
            "request_evidence_validated_before_measurement": True,
            "source_and_projected_context_hashes_cross_bound": True,
            "source_and_projected_event_hashes_cross_bound": True,
            "event_index_and_sequence_cross_bound": True,
            "omitted_value_hash_and_byte_descriptors_exact": True,
            "durable_tool_failure_error_details_unchanged": True,
            "durable_result_artifact_matches_event_error_details": True,
            "actionable_reason_guidance_and_gate_hashes_retained": True,
            "recovered_pin_survives_restart_once": True,
            "repeated_rejection_has_no_third_model_dispatch": True,
            "tampered_projection_rejected_after_rehash": True,
        },
        "activation_criteria": criteria,
        "decision": {
            "candidate_preparation_ready": all(criteria.values()),
            "authority": "exact-no-call-candidate-preparation-only",
            "reason": (
                "V22 stays below the preregistered request envelopes, removes full "
                "feedback projection duplication, preserves actionable feedback and "
                "durable bindings, and retains bounded restart/rejection behavior."
            ),
            "runtime_source_change_in_this_review": False,
            "rapid_candidate_created": False,
            "rehearsal_executed": False,
            "next_work": (
                "fresh-exact-v18-v22-rapid-candidate-and-two-production-order-no-call-rehearsals"
            ),
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
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
        },
        "provider_efficiency_established": False,
        "quality_improvement_established": False,
        "generalization_established": False,
        "paid_execution_authorized": False,
    }
    if not body["decision"]["candidate_preparation_ready"]:
        raise ContractError("V22 activation review criteria are not satisfied")
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    _content_hash(value, label="activation review")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_plan_admission_feedback_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_plan_admission_feedback_activation_review(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(review_bytes(value))
    return value


def load_plan_admission_feedback_activation_review(
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
    if value != build_plan_admission_feedback_activation_review(root):
        raise ContractError("activation review source binding differs")
    return value


__all__ = [
    "ADMISSION_THRESHOLDS",
    "IMMUTABLE_INPUTS",
    "MEASUREMENT_SCHEMA_VERSION",
    "PAIR_ASSESSMENT_SCHEMA_VERSION",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "assess_plan_feedback_request_pair",
    "build_plan_admission_feedback_activation_review",
    "load_plan_admission_feedback_activation_review",
    "materialize_plan_admission_feedback_activation_review",
    "measure_plan_feedback_request_artifact",
    "review_bytes",
]
