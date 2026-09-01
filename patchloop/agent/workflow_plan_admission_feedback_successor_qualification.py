"""Deterministic zero-call qualification for Lean V22 bounded plan feedback."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors_v2,
)
from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V22,
    LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
    LEAN_RUNTIME_POLICY_VERSION_V22,
    LEAN_TOOL_SCHEMA_VERSION_V22,
)
from patchloop.agent.workflow_plan_admission_feedback_successor import (
    project_bounded_plan_admission_feedback,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json, sha256_text

SCHEMA_VERSION = "lean-plan-admission-feedback-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-plan-admission-feedback-public-qualification-20260827-v1.json"
)

IMMUTABLE_PREDECESSORS = {
    "experiments/lean-harness-plan-gate-liveness-public-qualification-20260827-v1.json": {
        "bytes": 5_617,
        "file_sha256": "sha256:e45a36b595b64cdb5a098615a471fbb2c95c0e75301c1019c3ea8b19c10467bb",
        "content_hash": "sha256:dc1c5be75723ff9bd8269be362ee49c5c821f89f70a169ec4052a6edfbb71867",
    },
    "experiments/lean-harness-plan-gate-liveness-activation-review-20260827-v1.json": {
        "bytes": 5_559,
        "file_sha256": "sha256:aabe212ab3c036cc39c96cc933dd27faf4355b2de7b000381bd135224aa2a69d",
        "content_hash": "sha256:86a5800969eabd7327d37f5e6414f9ba279ee094cbcc417679b6e176a26b18f9",
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_plan_admission_feedback_successor.py",
    "patchloop/agent/workflow_plan_admission_feedback_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_plan_admission_feedback_qualification.py",
    "tests/test_workflow_plan_admission_feedback_successor.py",
    "tests/test_workflow_plan_admission_feedback_runner.py",
    "tests/test_workflow_plan_admission_feedback_successor_qualification.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"plan-feedback qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _predecessor_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_PREDECESSORS[relative]
    try:
        document = json.loads(ensure_within(root, relative).read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("plan-feedback predecessor is not JSON") from exc
    content_hash = document.get("content_hash")
    if content_hash != sha256_json(
        {key: value for key, value in document.items() if key != "content_hash"}
    ):
        raise ContractError("plan-feedback predecessor content hash differs")
    identity["content_hash"] = content_hash
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable plan-feedback predecessor differs: {relative}")
    return identity


def _document(schema: str, payload: str) -> dict[str, Any]:
    body = {"schema_version": schema, "payload": payload}
    return {**body, "content_hash": sha256_json(body)}


def _feedback_details() -> dict[str, Any]:
    catalog = _document("eligible-plan-evidence-catalog-v3", "c" * 2_000)
    causal = _document("activated-causal-plan-request-v1", "p" * 8_000)
    activated_body = {
        "schema_version": "pinned-exploration-plan-request-v1",
        "source_request": {"base_request": causal},
        "payload": "a" * 18_000,
    }
    activated = {**activated_body, "content_hash": sha256_json(activated_body)}
    return {
        "schema_version": "work-plan-admission-feedback-v1",
        "policy_version": "work-plan-admission-recovery-v1",
        "plan_gate_id": sha256_text("gate"),
        "attempt": 1,
        "reason_codes": ["exploration_blocking_unknowns_open"],
        "eligible_catalog_hash": catalog["content_hash"],
        "eligible_plan_evidence_catalog": catalog,
        "activated_exploration_plan_request": activated,
        "activated_exploration_plan_request_hash": activated["content_hash"],
        "causal_plan_request_projection": causal,
        "causal_plan_request_projection_hash": causal["content_hash"],
        "semantic_progress_state": None,
        "required_prior_hypothesis_disposition": None,
        "worktree_diff_hash": sha256_text(""),
        "request_artifact_id": "art_request",
        "request_body_hash": sha256_text("request"),
        "execution": "not_dispatched",
        "guidance": (
            "Retry once using only the exact cspan and support IDs in "
            "causal_plan_request_projection. Do not supply paths, ranges, roles, "
            "evidence bindings, observation status, or check order."
        ),
    }


def _built_context(details: dict[str, Any] | None) -> BuiltContext:
    payload = {
        "public_task": {"task_id": "bounded-plan-feedback"},
        "phase": "PLAN",
        "checkpoint": None,
        "phase_contract": {"current_phase": "PLAN"},
        "recent_events": (
            [
                {
                    "sequence": 17,
                    "type": "ToolFailed",
                    "actor": "tool-gateway",
                    "payload": {
                        "tool": "record_work_plan",
                        "status": "rejected",
                        "error_code": "WORK_PLAN_ADMISSION_REJECTED",
                        "error_message": "public plan is incomplete",
                        "error_details": details,
                        "admission_blocked": True,
                        "artifact_id": "art_result",
                        "artifact_path": "objects/result.json",
                    },
                }
            ]
            if details is not None
            else []
        ),
        "execution_signals": {"repeated_calls": []},
        "selected_memory": None,
        "rules": {"private_evaluator_data_unavailable": True},
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v11",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )


def _rejection_message(call: Callable[[], Any]) -> str:
    try:
        call()
    except ContractError as exc:
        return str(exc)
    raise ContractError("plan-feedback negative scenario did not reject")


def _scenarios() -> dict[str, Any]:
    source_details = _feedback_details()
    durable_before = sha256_json(source_details)
    compacted = project_lean_context_event_descriptors_v2(_built_context(source_details))
    first = project_bounded_plan_admission_feedback(compacted)
    second = project_bounded_plan_admission_feedback(compacted)
    projected_context = json.loads(first.rendered)
    projected_details = projected_context["recent_events"][0]["payload"]["error_details"]
    event = first.evidence.event_projections[0]
    empty = project_lean_context_event_descriptors_v2(_built_context(None))
    empty_projection = project_bounded_plan_admission_feedback(empty)

    unknown = copy.deepcopy(source_details)
    unknown["unversioned_nested_value"] = {"large": "x"}
    tampered = copy.deepcopy(source_details)
    tampered["eligible_catalog_hash"] = sha256_text("tampered")

    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V22,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V22,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V22,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V22,
            "projection_policy_version": LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22,
            "tool_contract_changed_from_v21": False,
        },
        "bounded_projection": {
            "source_context_bytes": first.evidence.source_context_bytes,
            "projected_context_bytes": first.evidence.projected_context_bytes,
            "context_bytes_saved": first.evidence.context_bytes_saved,
            "source_error_details_bytes": event.source_error_details_bytes,
            "projected_error_details_bytes": event.projected_error_details_bytes,
            "projected_event_count": first.evidence.projected_event_count,
            "projected_feedback_schema": projected_details["schema_version"],
            "source_event_hash_bound_in_projection": (
                projected_details["source_event_hash"] == event.source_event_hash
            ),
            "durable_details_hash_preserved": sha256_json(source_details) == durable_before,
            "durable_event_changed": first.evidence.durable_event_changed,
            "durable_result_artifact_changed": (first.evidence.durable_result_artifact_changed),
            "deterministic_projection": first == second,
        },
        "empty_context": {
            "exact_noop": empty_projection.rendered == empty.rendered,
            "projected_event_count": empty_projection.evidence.projected_event_count,
            "context_bytes_saved": empty_projection.evidence.context_bytes_saved,
        },
        "fail_closed": {
            "unversioned_field": _rejection_message(
                lambda: project_bounded_plan_admission_feedback(
                    project_lean_context_event_descriptors_v2(_built_context(unknown))
                )
            ),
            "tampered_nested_binding": _rejection_message(
                lambda: project_bounded_plan_admission_feedback(
                    project_lean_context_event_descriptors_v2(_built_context(tampered))
                )
            ),
            "persisted_projection_tamper_tested": True,
        },
        "observed_public_mock_runner": {
            "provenance": "focused-real-shaped-public-mock-runner-test",
            "canonical_raw_trace": False,
            "current_plan_request_bytes": 63_932,
            "recovered_retry_request_bytes": 74_013,
            "recovered_source_context_bytes": 103_587,
            "recovered_projected_context_bytes": 21_318,
            "recovered_context_bytes_saved": 82_269,
            "durable_error_details_bytes": 34_598,
            "projected_error_details_bytes": 2_055,
            "admission_thresholds": {
                "current_plan_request_max_bytes": 65_000,
                "recovered_retry_request_max_bytes": 90_000,
                "minimum_context_bytes_saved": 30_000,
            },
            "exact_provider_input_tokens_measured": False,
        },
        "preserved_limits": {
            "v21_request_or_artifact_modified": False,
            "raw_reasoning_replayed": False,
            "private_or_hidden_material_projected": False,
            "runtime_activation_is_opt_in": True,
            "rapid_candidate_created": False,
        },
    }


def build_workflow_plan_admission_feedback_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v22-bounded-model-facing-plan-admission-feedback",
        "policy_version": LEAN_PLAN_ADMISSION_FEEDBACK_POLICY_VERSION_V22,
        "scenarios": _scenarios(),
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_predecessors": [
            _predecessor_identity(root, relative) for relative in IMMUTABLE_PREDECESSORS
        ],
        "validated_test_surfaces": {
            "focused_projection_unit": True,
            "real_shaped_public_mock_runner_success_and_rejection": True,
            "crash_restart_between_rejection_and_retry": True,
            "persisted_request_tamper": True,
            "v21_runner_regression": True,
        },
        "evidence_boundary": {
            "qualification_builder_uses_public_synthetic_projection_only": True,
            "runner_tests_executed_separately": True,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "added_cost_usd": "0",
        },
        "runtime_surface_activated": True,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
        "next_gate": "fresh-zero-call-v22-activation-review-and-candidate-decision",
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("plan-feedback qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_plan_admission_feedback_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_plan_admission_feedback_successor_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_plan_admission_feedback_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("plan-feedback qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("plan-feedback qualification bytes differ")
    if value != build_workflow_plan_admission_feedback_successor_qualification(root):
        raise ContractError("plan-feedback qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_plan_admission_feedback_successor_qualification",
    "load_workflow_plan_admission_feedback_successor_qualification",
    "materialize_workflow_plan_admission_feedback_successor_qualification",
    "qualification_bytes",
]
