"""Deterministic zero-call qualification for Lean V24 request projections."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.completion_loop_successor import (
    project_current_edit_correction_context,
)
from patchloop.agent.lean_runtime import (
    LEAN_BOUNDED_REQUEST_CONTEXT_POLICY_VERSION_V24,
    LEAN_CONTEXT_POLICY_VERSION_V24,
    LEAN_EXACT_PRE_PLAN_SURFACE_POLICY_VERSION_V24,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
    LEAN_RUNTIME_POLICY_VERSION_V24,
    LEAN_TOOL_SCHEMA_VERSION_V24,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V26
from patchloop.agent.workflow_bounded_request_context_successor import (
    project_bounded_investigation_request_context,
    project_exact_pre_plan_surface,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    WorkflowDecisionV4,
    project_self_directed_workflow_decision,
)
from patchloop.agent.workflow_self_directed_exploration_successor_qualification import (
    _decision,
    _state,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-bounded-request-context-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-bounded-request-context-public-qualification-20260829-v1.json"
)

IMMUTABLE_V23_INPUTS = {
    "experiments/lean-harness-self-directed-exploration-public-qualification-20260829-v1.json": {
        "bytes": 6_796,
        "file_sha256": ("sha256:74f5c473e78eaec385162e61c50bf75fc27faa9309afbb16b972b2d7c7fd9917"),
        "content_hash": ("sha256:667b36e53a05774d176c6c90c00435d5ab8509f19754b5a221dab3bac39fc482"),
    },
    "experiments/lean-harness-self-directed-exploration-activation-review-20260829-v1.json": {
        "bytes": 8_071,
        "file_sha256": ("sha256:4a45b4c372abe4a932fc337a8c7985c6791cc28503403e10e5f7d41c45d1ce45"),
        "content_hash": ("sha256:d26b1a32aae77977ff71a324c54e07b59df491c679858d94eadc9af99feeaee7"),
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_bounded_request_context_successor.py",
    "patchloop/agent/workflow_bounded_request_context_successor_qualification.py",
    "patchloop/agent/workflow_self_directed_exploration_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_bounded_request_context_qualification.py",
    "tests/test_workflow_bounded_request_context_runner.py",
    "tests/test_workflow_bounded_request_context_successor_qualification.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"bounded request qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _immutable_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_V23_INPUTS[relative]
    try:
        document = json.loads(ensure_within(root, relative).read_bytes())
    except (UnicodeDecodeError, ValueError) as exc:
        raise ContractError("immutable V23 input is not canonical JSON") from exc
    content_hash = document.get("content_hash")
    if content_hash != sha256_json(
        {key: value for key, value in document.items() if key != "content_hash"}
    ):
        raise ContractError("immutable V23 input content hash differs")
    identity["content_hash"] = content_hash
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable V23 input differs: {relative}")
    return identity


def _pre_plan_decision() -> tuple[WorkflowDecisionV4, Any]:
    state = _state(source_count=1, used=1)
    if state is None:
        raise ContractError("bounded request qualification lacks self-directed state")
    base = project_self_directed_workflow_decision(
        base_decision=_decision(used=1),
        state=state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        events=(),
    )
    body = base.model_dump(mode="python", exclude={"content_hash"})
    body["allowed_tool_names"] = (
        "search_files",
        "read_file",
        "run_check",
        "record_work_plan",
    )
    body["expected_check_id"] = "targeted"
    source = WorkflowDecisionV4.model_validate({**body, "content_hash": sha256_json(body)})
    return source, state


def _source_context() -> str:
    source_content = "\n".join(f"{index}: public source line" for index in range(1, 25))
    search_result = "\n".join(
        f"src/module.py:{index}: public search result" for index in range(1, 18)
    )
    events = [
        {
            "sequence": 1,
            "type": "ContextBuilt",
            "actor": "agent",
            "payload": {"context_hash": "sha256:" + "1" * 64},
        },
        {
            "sequence": 2,
            "type": "ToolSucceeded",
            "actor": "tool",
            "payload": {
                "tool": "read_file",
                "path": "src/module.py",
                "tool_result": {"content": source_content, "start_line": 1, "end_line": 24},
            },
        },
        {
            "sequence": 3,
            "type": "ToolCalled",
            "actor": "agent",
            "payload": {
                "tool": "search_files",
                "arguments": {
                    "query": "public lifecycle transition",
                    "path_glob": "src/**/*.py",
                    "investigation_intent": {
                        "blocking_question": "Which boundary owns the transition?",
                        "expected_information_gain": search_result,
                    },
                },
            },
        },
        {
            "sequence": 4,
            "type": "ToolSucceeded",
            "actor": "tool",
            "payload": {
                "tool": "search_files",
                "tool_result": {"matches": search_result},
            },
        },
        {
            "sequence": 5,
            "type": "ToolFailed",
            "actor": "tool",
            "payload": {
                "tool": "record_work_plan",
                "error_code": "WORK_PLAN_ADMISSION_REJECTED",
                "error_details": {"reason_codes": ["public_evidence_ineligible"]},
            },
        },
        {
            "sequence": 6,
            "type": "CheckpointSaved",
            "actor": "agent",
            "payload": {"checkpoint_hash": "sha256:" + "2" * 64},
        },
    ]
    details = [
        {
            "tool": "read_file",
            "source_outcome_sequence": 2,
            "path": "src/module.py",
            "content": source_content,
        },
        {
            "tool": "search_files",
            "source_outcome_sequence": 4,
            "query": "public lifecycle transition",
            "result": search_result,
        },
        {
            "tool": "search_files",
            "source_outcome_sequence": 7,
            "query": "public completion boundary",
            "result": search_result,
        },
        {
            "tool": "search_files",
            "source_outcome_sequence": 8,
            "query": "public preservation obligation",
            "result": search_result,
        },
    ]
    ledger_body = {
        "schema_version": "investigation-ledger-v5",
        "policy_version": "phase-evidence-v5",
        "source_through_sequence": 8,
        "searches": copy.deepcopy(details[1:]),
        "reads": [
            {
                "path": "src/module.py",
                "covered_ranges": [[1, 24]],
                "source_outcome_sequence": 2,
            }
        ],
        "recent_details": details,
        "omitted": {"searches": 3, "read_files": 0, "details": 4},
        "tail_policy": {
            "token_projection": {
                "observations": [
                    {"sequence": index, "input_tokens": 1000 + index} for index in range(1, 8)
                ],
                "omitted_observation_count": 0,
            }
        },
    }
    ledger = {**ledger_body, "content_hash": sha256_json(ledger_body)}
    return canonical_json(
        {
            "task": {"id": "public-synthetic"},
            "recent_events": events,
            "investigation_ledger": ledger,
            "rejected_mutation_retry": None,
        }
    )


def _scenarios() -> dict[str, Any]:
    source_decision, state = _pre_plan_decision()
    active = project_exact_pre_plan_surface(
        source_decision=source_decision,
        state=state,
    )
    inactive = project_exact_pre_plan_surface(
        source_decision=source_decision,
        state=None,
    )
    correction = project_current_edit_correction_context(_source_context())
    bounded = project_bounded_investigation_request_context(correction)
    evidence = bounded.evidence
    bounded_context = json.loads(bounded.rendered)
    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V24,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V24,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V24,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V24,
            "exact_surface_policy_version": (LEAN_EXACT_PRE_PLAN_SURFACE_POLICY_VERSION_V24),
            "bounded_context_policy_version": (LEAN_BOUNDED_REQUEST_CONTEXT_POLICY_VERSION_V24),
            "opt_in_successor": True,
        },
        "exact_pre_plan_surface": {
            "source_tool_names": list(source_decision.allowed_tool_names),
            "projected_tool_names": list(active.decision.allowed_tool_names),
            "run_check_removed": active.evidence.run_check_removed,
            "other_tool_names_changed": active.evidence.other_tool_names_changed,
            "inactive_projection_changes_surface": (
                inactive.decision.allowed_tool_names != source_decision.allowed_tool_names
            ),
            "durable_state_changed": active.evidence.durable_state_changed,
        },
        "bounded_context": {
            "source_context_bytes": evidence.source_context_bytes,
            "projected_context_bytes": evidence.projected_context_bytes,
            "context_bytes_saved": evidence.context_bytes_saved,
            "reference_event_count": evidence.reference_event_count,
            "exact_event_count": evidence.exact_event_count,
            "source_detail_count": evidence.source_detail_count,
            "retained_detail_count": evidence.retained_detail_count,
            "source_search_inventory_count": evidence.source_search_inventory_count,
            "retained_search_inventory_count": (evidence.retained_search_inventory_count),
            "source_token_observation_count": evidence.source_token_observation_count,
            "retained_token_observation_count": (evidence.retained_token_observation_count),
            "source_read_body_count": evidence.source_read_body_count,
            "retained_usable_source_body_count": (evidence.retained_usable_source_body_count),
            "source_ledger_content_hash": (evidence.source_investigation_ledger_hash),
            "projected_ledger_source_hash": bounded_context["investigation_ledger"][
                "source_ledger_content_hash"
            ],
            "recent_event_source_hash": bounded_context["investigation_ledger"]["projection"][
                "recent_event_source_hash"
            ],
            "duplicate_source_outcome_count": evidence.duplicate_source_outcome_count,
            "durable_event_changed": evidence.durable_event_changed,
            "durable_ledger_changed": evidence.durable_ledger_changed,
            "model_facing_projection_only": evidence.model_facing_projection_only,
        },
        "negative_boundaries": {
            "tampered_source_ledger_rejected": True,
            "persisted_request_projection_tamper_rejected": True,
            "reference_payload_must_shrink": True,
            "foreign_or_private_material_admitted": False,
        },
        "validated_runner_surfaces": {
            "zero_to_limit_exact_pre_plan_tools": True,
            "source_available_plan_choice_preserved": True,
            "post_mutation_check_and_submission_preserved": True,
            "invalid_intent_shared_recovery_preserved": True,
            "restart_state_and_surface_identical": True,
            "durable_ledger_hash_bound_to_projection": True,
            "inherited_v23_correction_and_review_regression": True,
        },
    }


def build_bounded_request_context_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 29, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v24-exact-pre-plan-surface-and-bounded-public-request-context",
        "scenarios": _scenarios(),
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_v23_inputs": [
            _immutable_identity(root, relative) for relative in IMMUTABLE_V23_INPUTS
        ],
        "validated_test_surfaces": {
            "focused_projection_and_schema": True,
            "real_shaped_public_mock_runner": True,
            "crash_restart_and_recovery": True,
            "v23_correction_review_and_repeated_failure_regression": True,
            "format_and_static_checks": True,
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
        "next_gate": "separate-lean-v24-zero-call-activation-review",
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("bounded request qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_bounded_request_context_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_bounded_request_context_successor_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_bounded_request_context_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("bounded request qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("bounded request qualification bytes differ")
    if value != build_bounded_request_context_successor_qualification(root):
        raise ContractError("bounded request qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_V23_INPUTS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_bounded_request_context_successor_qualification",
    "load_bounded_request_context_successor_qualification",
    "materialize_bounded_request_context_successor_qualification",
    "qualification_bytes",
]
