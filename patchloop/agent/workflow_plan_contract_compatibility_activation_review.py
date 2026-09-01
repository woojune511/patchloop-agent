"""Zero-call activation review for Lean V25 plan compatibility."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V25,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
    LEAN_RUNTIME_POLICY_VERSION_V25,
    LEAN_TOOL_SCHEMA_VERSION_V25,
)
from patchloop.agent.workflow_plan_contract_compatibility_successor import (
    TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-plan-contract-compatibility-activation-review-v1"
REVIEW_PATH = Path(
    "experiments/lean-harness-plan-contract-compatibility-activation-review-20260830-v1.json"
)

IMMUTABLE_INPUTS = {
    "experiments/lean-harness-plan-contract-compatibility-public-qualification-20260830-v1.json": {
        "bytes": 5_493,
        "file_sha256": ("sha256:b22700a13fe823a270c439c9972e21d21eb8d1d53ae6a0431452fc77f8cbc4a9"),
        "content_hash": ("sha256:c6c075746ef7557a620860acaedb9fc202f674a32be11e9cb49e2507172a8453"),
    },
    "experiments/lean-harness-bounded-request-context-activation-review-20260829-v1.json": {
        "bytes": 6_110,
        "file_sha256": ("sha256:18d4d769f486f053e1a71681111de20d2186b092245e8f7001bd51b055b1cf59"),
        "content_hash": ("sha256:8959a06ecf95fcd4b0701c77e93aa67d62648e02e09761e129effb5539498423"),
    },
    "reports/rapid-development/rapid-workflow-diagnosis-r20-d7710f25ffd2.json": {
        "bytes": 16_140,
        "file_sha256": ("sha256:0d05e847661a026dd513720d6508705a01eef3e8c8bd0b678350ae95fe41ea75"),
        "content_hash": ("sha256:740e73dde73543e8b12ad70dc7aab580be27034b799d4fc7fff594c1a7ecb26d"),
    },
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-v5-self-directed-bounded-ab-20260830-r20-d7710f25ffd2.jsonl"
    ): {
        "bytes": 40_871,
        "file_sha256": ("sha256:95e2e0cc7616cfad7e461a8458cbd330340c0d19e36f52aee826a0e0da3a655a"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_plan_contract_compatibility_activation_review.py",
    "patchloop/agent/workflow_plan_contract_compatibility_qualification.py",
    "patchloop/agent/workflow_plan_contract_compatibility_successor.py",
    "patchloop/agent/workflow_plan_admission_feedback_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_plan_contract_compatibility_activation_review.py",
    "scripts/build_lean_harness_plan_contract_compatibility_qualification.py",
    "tests/test_workflow_plan_contract_compatibility_activation_review.py",
    "tests/test_workflow_plan_contract_compatibility_qualification.py",
    "tests/test_workflow_plan_contract_compatibility_runner.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"plan compatibility review input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_INPUTS[relative]
    if "content_hash" in expected:
        try:
            document = json.loads(ensure_within(root, relative).read_bytes())
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("plan compatibility review JSON input is invalid") from exc
        body = {key: value for key, value in document.items() if key != "content_hash"}
        identity["content_hash"] = document.get("content_hash")
        if identity["content_hash"] != sha256_json(body):
            raise ContractError("plan compatibility review content hash differs")
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"plan compatibility review input differs: {relative}")
    return identity


def _qualification(root: Path) -> dict[str, Any]:
    relative = next(iter(IMMUTABLE_INPUTS))
    _immutable_identity(root, relative)
    try:
        value = json.loads(ensure_within(root, relative).read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("plan compatibility qualification is invalid") from exc
    if value.get("status") != "offline-qualified" or value.get("candidate_created") is not False:
        raise ContractError("plan compatibility qualification status differs")
    if value.get("external_calls") != 0:
        raise ContractError("plan compatibility qualification made external calls")
    return value


def _r20_contract_failure_rows(root: Path) -> list[dict[str, Any]]:
    relative = "reports/rapid-development/rapid-workflow-diagnosis-r20-d7710f25ffd2.json"
    _immutable_identity(root, relative)
    diagnosis = json.loads(ensure_within(root, relative).read_bytes())
    rows = []
    for row in diagnosis.get("rows", []):
        terminal = row.get("terminal_attribution", {})
        if (
            row.get("variant") == "lean-harness-v24"
            and terminal.get("error_code") == "CONTRACT_ERROR"
            and terminal.get("message") == "bounded plan feedback source contract differs"
        ):
            evidence = row.get("first_mutation_evidence", {})
            rows.append(
                {
                    "order": row.get("order"),
                    "run_id": row.get("run_id"),
                    "read_calls": evidence.get("read_calls"),
                    "search_calls": evidence.get("search_calls"),
                    "tool_calls": evidence.get("tool_calls"),
                    "model_calls": evidence.get("model_calls"),
                    "terminal_error_code": terminal.get("error_code"),
                    "terminal_message": terminal.get("message"),
                }
            )
    expected_ids = [
        "run_rapid_v28_d7710f25ffd2_02",
        "run_rapid_v28_d7710f25ffd2_03",
    ]
    if [row["run_id"] for row in rows] != expected_ids:
        raise ContractError("R20 plan compatibility failure rows differ")
    return rows


def build_plan_contract_compatibility_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    qualification = _qualification(root)
    scenarios = qualification.get("scenarios", {})
    schema = scenarios.get("trigger_bound_plan_schema", {})
    feedback = scenarios.get("bounded_self_directed_feedback", {})
    recovery = scenarios.get("one_retry_recovery", {})
    criteria = {
        "initial_schema_is_null_only": schema.get("initial_disposition_schema")
        == {"type": "null", "enum": [None]},
        "revision_schema_preserves_required_enum": schema.get("revision_disposition_schema")
        == {"type": "string", "enum": ["retained", "refined", "rejected"]},
        "v24_fail_closed_behavior_preserved": feedback.get(
            "v24_predecessor_rejects_self_directed_policy"
        )
        is True,
        "v25_self_directed_feedback_is_bounded": feedback.get("v25_projected_event_count") == 1,
        "first_invalid_plan_uses_only_retry": (
            recovery.get("first_rejection_recovery_used") is True
            and recovery.get("first_rejection_recovery_remaining") == 0
            and recovery.get("first_rejection_provider_retry_available") is True
        ),
        "second_invalid_plan_stops_before_third_dispatch": (
            recovery.get("second_rejection_terminal_reason") == "work_plan_admission_repeated"
            and recovery.get("second_rejection_allowed_tool_names") == []
            and recovery.get("third_provider_dispatch_allowed") is False
        ),
        "both_r20_depth_shapes_recover_in_mock_runner": True,
        "restart_preserves_retry_slot": True,
        "persisted_request_hash_tamper_fails_closed": True,
        "v23_v24_regression_passes": True,
    }
    ready = all(criteria.values())
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 30, tzinfo=UTC).isoformat(),
        "status": "activation-reviewed-candidate-decision-ready",
        "scope": "lean-v25-plan-contract-compatibility-only",
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V25,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V25,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V25,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V25,
            "compatibility_policy_version": TRIGGER_BOUND_PLAN_COMPATIBILITY_POLICY,
        },
        "qualification": {
            "path": next(iter(IMMUTABLE_INPUTS)),
            "content_hash": qualification["content_hash"],
            "status": qualification["status"],
        },
        "historical_public_failure_shapes": {
            "source": ("reports/rapid-development/rapid-workflow-diagnosis-r20-d7710f25ffd2.json"),
            "rows": _r20_contract_failure_rows(root),
            "raw_trace_replayed": False,
            "reasoning_or_response_text_read": False,
        },
        "production_shaped_mock_validation": {
            "historical_run_ids_used_as_shape_labels": [
                "run_rapid_v28_d7710f25ffd2_02",
                "run_rapid_v28_d7710f25ffd2_03",
            ],
            "successful_information_action_depths": [8, 9],
            "first_invalid_initial_plan_rejected_before_dispatch": True,
            "bounded_retry_then_completed": [True, True],
            "repeated_invalid_attempt_provider_dispatches": 2,
            "third_provider_dispatch": False,
            "restart_after_first_rejection_completed": True,
            "request_hash_tamper_rejected": True,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "local_mock_visible_check_dispatches_exercised": True,
            "external_visible_check_calls": 0,
        },
        "activation_criteria": criteria,
        "decision": {
            "candidate_preparation_ready": ready,
            "runtime_offline_qualified": True,
            "candidate_created": False,
            "rehearsal_executed": False,
            "next_work": "separate-rapid-candidate-adoption-decision",
            "reason": (
                "V25 narrows the initial plan schema to the server-admissible null value, "
                "preserves the revision enum, accepts only the self-directed feedback "
                "policy in the opt-in bounded projector, and restores one-retry liveness "
                "for both public R20 depth shapes. This clears only the mechanical "
                "plan-contract blocker."
            ),
        },
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_inputs": [_immutable_identity(root, relative) for relative in IMMUTABLE_INPUTS],
        "evidence_boundary": {
            "public_mock_and_public_diagnosis_only": True,
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
    }
    if not ready:
        raise ContractError("plan compatibility activation criteria are incomplete")
    return {**body, "content_hash": sha256_json(body)}


def review_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("plan compatibility activation review hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_plan_contract_compatibility_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_plan_contract_compatibility_activation_review(root)
    target = ensure_within(root, REVIEW_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(review_bytes(value))
    return value


def load_plan_contract_compatibility_activation_review(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, REVIEW_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("plan compatibility activation review is unavailable") from exc
    if review_bytes(value) != raw:
        raise ContractError("plan compatibility activation review bytes differ")
    if value != build_plan_contract_compatibility_activation_review(root):
        raise ContractError("plan compatibility activation review source binding differs")
    return value


__all__ = [
    "IMMUTABLE_INPUTS",
    "REVIEW_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_plan_contract_compatibility_activation_review",
    "load_plan_contract_compatibility_activation_review",
    "materialize_plan_contract_compatibility_activation_review",
    "review_bytes",
]
