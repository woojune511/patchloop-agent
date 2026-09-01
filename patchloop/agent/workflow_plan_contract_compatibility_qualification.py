"""Deterministic zero-call qualification for Lean V25 plan compatibility."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.context import BuiltContext
from patchloop.agent.context_event_compaction import (
    project_lean_context_event_descriptors_v2,
)
from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V25,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
    LEAN_RUNTIME_POLICY_VERSION_V25,
    LEAN_TOOL_SCHEMA_VERSION_V25,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V26
from patchloop.agent.workflow_causal_plan_projection_activation import (
    project_activated_causal_plan_request,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    _catalog,
    _task,
)
from patchloop.agent.workflow_plan_admission_feedback_successor import (
    project_bounded_plan_admission_feedback,
    project_compatible_bounded_plan_admission_feedback,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY,
    project_trigger_bound_self_directed_plan_request,
    project_trigger_bound_self_directed_workflow_decision,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    SELF_DIRECTED_EXPLORATION_POLICY,
)
from patchloop.agent.workflow_self_directed_exploration_successor_qualification import (
    _decision,
    _state,
)
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.util import (
    canonical_json,
    ensure_within,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

SCHEMA_VERSION = "lean-plan-contract-compatibility-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-plan-contract-compatibility-public-qualification-20260830-v1.json"
)

IMMUTABLE_INPUTS = {
    "experiments/lean-harness-bounded-request-context-public-qualification-20260829-v1.json": {
        "bytes": 5_482,
        "file_sha256": "sha256:818d9ce5842a4bad5ad318b87d65aca6018dfc97dc84dc0d61eb9a9c57acf2e6",
        "content_hash": "sha256:581b7485abab5941cbf71d8def52d5ee9a1e504b539df16b838b9f2a180b99bd",
    },
    "experiments/lean-harness-bounded-request-context-activation-review-20260829-v1.json": {
        "bytes": 6_110,
        "file_sha256": "sha256:18d4d769f486f053e1a71681111de20d2186b092245e8f7001bd51b055b1cf59",
        "content_hash": "sha256:8959a06ecf95fcd4b0701c77e93aa67d62648e02e09761e129effb5539498423",
    },
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-v5-self-directed-bounded-ab-20260830-r20-d7710f25ffd2.jsonl"
    ): {
        "bytes": 40_871,
        "file_sha256": "sha256:95e2e0cc7616cfad7e461a8458cbd330340c0d19e36f52aee826a0e0da3a655a",
    },
    "reports/rapid-development/rapid-workflow-diagnosis-r20-d7710f25ffd2.json": {
        "bytes": 16_140,
        "file_sha256": "sha256:0d05e847661a026dd513720d6508705a01eef3e8c8bd0b678350ae95fe41ea75",
        "content_hash": "sha256:740e73dde73543e8b12ad70dc7aab580be27034b799d4fc7fff594c1a7ecb26d",
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_plan_contract_compatibility_successor.py",
    "patchloop/agent/workflow_plan_contract_compatibility_qualification.py",
    "patchloop/agent/workflow_plan_admission_feedback_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_plan_contract_compatibility_qualification.py",
    "tests/test_workflow_plan_contract_compatibility_runner.py",
    "tests/test_workflow_self_directed_exploration_successor.py",
    "tests/test_workflow_plan_admission_feedback_successor.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"plan compatibility input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    if "content_hash" in expected:
        try:
            document = json.loads(ensure_within(root, relative).read_bytes())
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("plan compatibility immutable JSON is invalid") from exc
        body = {key: value for key, value in document.items() if key != "content_hash"}
        identity["content_hash"] = document.get("content_hash")
        if identity["content_hash"] != sha256_json(body):
            raise ContractError("plan compatibility immutable content hash differs")
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"plan compatibility immutable input differs: {relative}")
    return identity


def _plan_schema_scenarios() -> dict[str, Any]:
    task = _task()
    initial_base = project_activated_causal_plan_request(
        task=task,
        catalog=_catalog(include_failed_check=False),
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )
    revision_base = project_activated_causal_plan_request(
        task=task,
        catalog=_catalog(include_failed_check=True),
        trigger="check_failure",
        trigger_check_id="targeted",
        trigger_event_sequence=13,
        cross_reset_trigger=None,
    )
    initial = project_trigger_bound_self_directed_plan_request(initial_base)
    revision = project_trigger_bound_self_directed_plan_request(revision_base)
    return {
        "initial_trigger": initial.source_request.base_request.source_projection.trigger,
        "initial_disposition_schema": initial.parameters["properties"][
            "prior_hypothesis_disposition"
        ],
        "revision_trigger": revision.source_request.base_request.source_projection.trigger,
        "revision_disposition_schema": revision.parameters["properties"][
            "prior_hypothesis_disposition"
        ],
        "initial_request_hash": initial.content_hash,
        "revision_request_hash": revision.content_hash,
        "server_semantic_admission_reused": True,
    }


def _feedback_details() -> dict[str, Any]:
    def document(schema: str, payload: str) -> dict[str, Any]:
        body = {"schema_version": schema, "payload": payload}
        return {**body, "content_hash": sha256_json(body)}

    catalog = document("eligible-plan-evidence-catalog-v4", "c" * 2_000)
    causal = document("activated-causal-plan-request-v1", "p" * 8_000)
    activated_body = {
        "schema_version": "self-directed-exploration-plan-request-v2",
        "source_request": {"base_request": causal},
        "payload": "a" * 18_000,
    }
    activated = {**activated_body, "content_hash": sha256_json(activated_body)}
    return {
        "schema_version": "work-plan-admission-feedback-v1",
        "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
        "plan_gate_id": sha256_text("gate"),
        "attempt": 1,
        "reason_codes": ["causal_plan_revision_binding_invalid"],
        "eligible_catalog_hash": catalog["content_hash"],
        "eligible_plan_evidence_catalog": catalog,
        "activated_exploration_plan_request": activated,
        "activated_exploration_plan_request_hash": activated["content_hash"],
        "causal_plan_request_projection": causal,
        "causal_plan_request_projection_hash": causal["content_hash"],
        "semantic_progress_state": None,
        "required_prior_hypothesis_disposition": None,
        "worktree_diff_hash": sha256_text(""),
        "request_artifact_id": "art_public_request",
        "request_body_hash": sha256_text("request"),
        "execution": "not_dispatched",
        "guidance": (
            "Retry once using only the exact cspan and support IDs in "
            "causal_plan_request_projection. Do not supply paths, ranges, roles, "
            "evidence bindings, observation status, or check order."
        ),
    }


def _feedback_scenario() -> dict[str, Any]:
    details = _feedback_details()
    payload = {
        "public_task": {"task_id": "public-plan-compatibility"},
        "phase": "PLAN",
        "checkpoint": None,
        "phase_contract": {"current_phase": "PLAN"},
        "recent_events": [
            {
                "sequence": 17,
                "type": "ToolFailed",
                "actor": "tool-gateway",
                "payload": {
                    "tool": "record_work_plan",
                    "status": "rejected",
                    "error_code": "WORK_PLAN_ADMISSION_REJECTED",
                    "error_message": "public plan is invalid",
                    "error_details": details,
                    "admission_blocked": True,
                },
            }
        ],
        "execution_signals": {"repeated_calls": []},
        "selected_memory": None,
        "rules": {"private_evaluator_data_unavailable": True},
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    built = BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v11",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
        },
    )
    compacted = project_lean_context_event_descriptors_v2(built)
    predecessor_rejected = False
    try:
        project_bounded_plan_admission_feedback(compacted)
    except ContractError:
        predecessor_rejected = True
    projected = project_compatible_bounded_plan_admission_feedback(compacted)
    return {
        "v24_predecessor_rejects_self_directed_policy": predecessor_rejected,
        "v25_projected_event_count": projected.evidence.projected_event_count,
        "v25_context_bytes_saved": projected.evidence.context_bytes_saved,
        "durable_event_changed": projected.evidence.durable_event_changed,
        "durable_result_artifact_changed": projected.evidence.durable_result_artifact_changed,
    }


def _recovery_scenario() -> dict[str, Any]:
    state = _state(source_count=1, used=1)
    if state is None:
        raise ContractError("plan compatibility qualification lacks public source state")
    timestamp = datetime(2026, 8, 30, tzinfo=UTC)

    def blocked(sequence: int) -> RunEvent:
        return RunEvent(
            event_id=f"evt_{sequence}",
            run_id=state.run_id,
            sequence=sequence,
            type=EventType.TOOL_ADMISSION_BLOCKED,
            timestamp=timestamp,
            actor="tool-gateway",
            payload={
                "policy_version": SELF_DIRECTED_EXPLORATION_POLICY,
                "plan_gate_id": state.plan_gate_id,
            },
        )

    source = tuple(TOOL_SCHEMAS_V26)
    first = project_trigger_bound_self_directed_workflow_decision(
        base_decision=_decision(used=1),
        state=state,
        source_tool_schemas=source,
        events=(blocked(1),),
    )
    second = project_trigger_bound_self_directed_workflow_decision(
        base_decision=_decision(used=1),
        state=state,
        source_tool_schemas=source,
        events=(blocked(1), blocked(2)),
    )
    return {
        "first_rejection_recovery_used": first.plan_admission_recovery_used,
        "first_rejection_recovery_remaining": first.plan_admission_recovery_remaining,
        "first_rejection_provider_retry_available": "record_work_plan" in first.allowed_tool_names,
        "second_rejection_target": second.target,
        "second_rejection_terminal_reason": second.terminal_reason,
        "second_rejection_allowed_tool_names": list(second.allowed_tool_names),
        "third_provider_dispatch_allowed": False,
    }


def build_plan_contract_compatibility_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    scenarios = {
        "trigger_bound_plan_schema": _plan_schema_scenarios(),
        "bounded_self_directed_feedback": _feedback_scenario(),
        "one_retry_recovery": _recovery_scenario(),
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 30, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v25-trigger-bound-plan-and-self-directed-feedback-compatibility",
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V25,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V25,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V25,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
            "compatibility_policy_version": TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY,
        },
        "scenarios": scenarios,
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_inputs": [_immutable_identity(root, relative) for relative in IMMUTABLE_INPUTS],
        "validated_test_surfaces": {
            "trigger_specific_dynamic_schema": True,
            "server_side_semantic_admission": True,
            "v24_fail_closed_behavior_preserved": True,
            "self_directed_feedback_bounded": True,
            "first_rejection_retry_succeeds": True,
            "second_rejection_terminal_before_provider_dispatch": True,
            "restart_recovers_retry_slot": True,
            "request_hash_tamper_fails_closed": True,
            "v23_v24_regression": True,
        },
        "evidence_boundary": {
            "public_synthetic_and_public_mock_inputs_only": True,
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
        "external_activation_performed": False,
        "external_calls": 0,
        "candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
        "next_gate": "separate-lean-v25-zero-call-activation-review",
    }
    if (
        scenarios["trigger_bound_plan_schema"]["initial_disposition_schema"]
        != {"type": "null", "enum": [None]}
        or scenarios["trigger_bound_plan_schema"]["revision_disposition_schema"]
        != {"type": "string", "enum": ["retained", "refined", "rejected"]}
        or scenarios["one_retry_recovery"]["second_rejection_terminal_reason"]
        != "work_plan_admission_repeated"
    ):
        raise ContractError("plan compatibility qualification criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("plan compatibility qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_plan_contract_compatibility_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_plan_contract_compatibility_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_plan_contract_compatibility_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("plan compatibility qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("plan compatibility qualification bytes differ")
    if value != build_plan_contract_compatibility_qualification(root):
        raise ContractError("plan compatibility qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_INPUTS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_plan_contract_compatibility_qualification",
    "load_plan_contract_compatibility_qualification",
    "materialize_plan_contract_compatibility_qualification",
    "qualification_bytes",
]
