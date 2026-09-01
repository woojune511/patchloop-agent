"""Deterministic zero-call qualification for Lean V23 self-directed exploration."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V23,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
    LEAN_RUNTIME_POLICY_VERSION_V23,
    LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23,
    LEAN_TOOL_SCHEMA_VERSION_V23,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V26
from patchloop.agent.workflow_causal_plan_projection_activation import (
    project_activated_causal_plan_request,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    RUNTIME_PATH,
    _arguments,
    _catalog,
    _task,
)
from patchloop.agent.workflow_self_directed_exploration_successor import (
    EligiblePlanEvidenceCatalogV4,
    normalize_self_directed_plan,
    project_self_directed_evidence_catalog,
    project_self_directed_exploration_state,
    project_self_directed_plan_request,
    project_self_directed_tool_surface,
    project_self_directed_workflow_decision,
    validate_exploration_stop,
    validate_investigation_action,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    WORKFLOW_POLICY_V15,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-self-directed-exploration-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-self-directed-exploration-public-qualification-20260829-v1.json"
)

IMMUTABLE_PREDECESSORS = {
    "patchloop/agent/workflow_plan_admission_feedback_successor.py": {
        "bytes": 19_687,
        "file_sha256": "sha256:fc3061ca0f1721c3ea8f37552d61ae85508998ca15d72eeefe8923d5f861de58",
    },
    "patchloop/agent/workflow_plan_gate_liveness_successor.py": {
        "bytes": 25_461,
        "file_sha256": "sha256:1d14c302ba0f62032ec61a6d7a948afdccc8a40d385981896f1d5baa4c5372a1",
    },
    "patchloop/agent/workflow_plan_admission_feedback_successor_qualification.py": {
        "bytes": 15_394,
        "file_sha256": "sha256:7ddd60ae8b5d0ae8ddd73493cfed7649fd2261c77a3a04b953e478b1fe0583da",
    },
    "experiments/lean-harness-plan-admission-feedback-public-qualification-20260827-v1.json": {
        "bytes": 5_281,
        "file_sha256": "sha256:abeed7280c1f8fdd1e32c90e7a10c09da0c55647be81c711839d53470c3cf0dc",
        "content_hash": "sha256:57f3b3e5cf9e58f3318da5d60b5dbee4d2fe050b72ee09a3b19b6462e9a0d30e",
    },
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-v5-plan-feedback-ab-20260828-r19-ed5c319756ed.jsonl"
    ): {
        "bytes": 44_890,
        "file_sha256": "sha256:8647dfdfcc44ba479bcf36304b543778bf3fd2c8c818c1c705fa6a553e7a939c",
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_self_directed_exploration_successor.py",
    "patchloop/agent/workflow_self_directed_exploration_successor_qualification.py",
    "patchloop/agent/investigation.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "scripts/build_lean_harness_self_directed_exploration_qualification.py",
    "tests/test_workflow_self_directed_exploration_successor.py",
    "tests/test_workflow_self_directed_exploration_runner.py",
    "tests/test_workflow_self_directed_exploration_successor_qualification.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"self-directed qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _predecessor_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_PREDECESSORS[relative]
    if "content_hash" in expected:
        try:
            document = json.loads(ensure_within(root, relative).read_bytes())
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("self-directed predecessor is not canonical JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: value for key, value in document.items() if key != "content_hash"}
        ):
            raise ContractError("self-directed predecessor content hash differs")
        identity["content_hash"] = content_hash
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable self-directed predecessor differs: {relative}")
    return identity


def _catalog_v2(*, source_count: int) -> EligiblePlanEvidenceCatalogV2:
    source = _catalog(include_failed_check=False)
    source_items = [item for item in source.items if item.kind == "source_read"]
    support_items = [item for item in source.items if item.kind != "source_read"]
    items = tuple(source_items[:source_count] + support_items)
    body = {
        **source.model_dump(mode="python", exclude={"schema_version", "content_hash", "items"}),
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "items": tuple(item.model_dump(mode="python") for item in items),
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _decision(*, used: int) -> WorkflowDecisionV3:
    catalog = _catalog_v2(source_count=2)
    body = {
        "schema_version": "lean-workflow-decision-v3",
        "runtime_policy_version": "lean-harness-v15",
        "policy_version": WORKFLOW_POLICY_V15,
        "target": "pre-mutation-exploration",
        "current_diff_hash": catalog.worktree_diff_hash,
        "expected_check_id": None,
        "allowed_tool_names": ("search_files", "read_file", "record_work_plan"),
        "information_actions_in_episode": 0,
        "fresh_current_read": False,
        "corrective_mutations_for_check": 0,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": used,
        "active_plan_hash": None,
        "plan_gate_id": "sha256:" + "4" * 64,
        "plan_admission_recovery_used": False,
        "plan_admission_recovery_remaining": 1,
        "required_trigger_evidence_id": None,
        "revision_trigger": None,
        "terminal_reason": None,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 4_096,
        "reasoning_effort": "medium",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
        "semantic_progress_state_hash": None,
        "semantic_reset_required": False,
        "required_prior_hypothesis_disposition": None,
    }
    return WorkflowDecisionV3.model_validate({**body, "content_hash": sha256_json(body)})


def _catalog_v4(*, source_count: int) -> EligiblePlanEvidenceCatalogV4:
    return project_self_directed_evidence_catalog(
        base=_catalog_v2(source_count=source_count), pin=None
    )


def _state(*, source_count: int, used: int):
    return project_self_directed_exploration_state(
        task=_task(),
        decision=_decision(used=used),
        catalog=_catalog_v4(source_count=source_count),
        events=(),
        active_work_state=None,
    )


def _linked(span_id: str, symbol: str) -> dict[str, Any]:
    return {
        "source_span_id": span_id,
        "symbol": symbol,
        "observation": "The public source controls one visible lifecycle step.",
        "relationship_to_next": "The current state reaches the next public boundary.",
    }


def _plan_arguments(*, co_located: bool) -> dict[str, Any]:
    arguments = _arguments()
    question = arguments.pop("unknowns")[0]
    if co_located:
        ownership = execution = mutation = "cspan:10:0"
        basis = [mutation]
        intermediate_steps: list[dict[str, Any]] = []
    else:
        ownership = mutation = "cspan:10:0"
        execution = "cspan:11:0"
        basis = [mutation, execution]
        intermediate_steps = [_linked(execution, "handler")]
    arguments["causal_mechanism"]["causal_boundary"] = _linked(ownership, "entry_boundary")
    arguments["causal_mechanism"]["intermediate_steps"] = intermediate_steps
    arguments["causal_mechanism"]["mutation_site"]["source_span_id"] = mutation
    arguments["candidate_source_span_ids"] = [mutation]
    arguments["exploration_state"] = {
        "boundary_coverage": {
            "ownership_boundary_span_ids": [ownership],
            "execution_boundary_span_ids": [execution],
            "mutation_boundary_span_ids": [mutation],
        },
        "invariants": [
            {
                "subject": "Public lifecycle ownership",
                "claim": "The cited source controls the bounded transition.",
                "evidence_source_span_ids": list(dict.fromkeys(basis)),
            }
        ],
        "preservation_obligations": [
            {
                "public_requirement": "Preserve the later visible lifecycle step.",
                "expected_behavior": "Visible checks remain ordered after the edit.",
                "evidence_source_span_ids": [mutation if co_located else execution],
            }
        ],
        "unknown_dispositions": [
            {
                "question": question,
                "disposition": "non_blocking",
                "explanation": "The bounded transition does not depend on this question.",
                "evidence_source_span_ids": [mutation],
            }
        ],
        "open_blocking_unknowns": [],
    }
    arguments["readiness_assessment"] = {
        "readiness_status": "ready_to_plan",
        "sufficiency_mode": "co_located_boundary" if co_located else "multi_range",
        "basis_source_span_ids": basis,
        "sufficiency_rationale": "The current public ranges bind the proposed change.",
        "remaining_unknowns_non_blocking": True,
    }
    return arguments


def _request(catalog: EligiblePlanEvidenceCatalogV4):
    base = project_activated_causal_plan_request(
        task=_task(),
        catalog=catalog,
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )
    return project_self_directed_plan_request(base)


def _reason_code(call) -> str:
    try:
        call()
    except ContractError as exc:
        reasons = exc.details.get("reason_codes", [])
        return reasons[0] if reasons else str(exc)
    raise ContractError("self-directed negative scenario did not reject")


def _scenarios() -> dict[str, Any]:
    task = _task()
    one_catalog = _catalog_v4(source_count=1)
    one_state = _state(source_count=1, used=1)
    if one_state is None:
        raise ContractError("self-directed one-read state is unavailable")
    one_decision = project_self_directed_workflow_decision(
        base_decision=_decision(used=1),
        state=one_state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        events=(),
    )
    one_surface, one_request = project_self_directed_tool_surface(
        task=task,
        decision=one_decision,
        catalog=one_catalog,
        state=one_state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        cross_reset_trigger=None,
    )
    read_schema = next(
        item for item in one_surface.selected_tool_schemas if item["name"] == "read_file"
    )

    zero_state = _state(source_count=0, used=0)
    if zero_state is None:
        raise ContractError("self-directed zero-read state is unavailable")
    zero_decision = project_self_directed_workflow_decision(
        base_decision=_decision(used=0),
        state=zero_state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        events=(),
    )

    two_catalog = _catalog_v4(source_count=2)
    readiness: dict[str, Any] = {}
    for co_located in (False, True):
        plan, receipt = normalize_self_directed_plan(
            task=task,
            catalog=two_catalog,
            request_projection=_request(two_catalog),
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
            cross_reset_trigger=None,
            history=(),
            raw_arguments=_plan_arguments(co_located=co_located),
        )
        key = "co_located_boundary" if co_located else "multi_range"
        readiness[key] = {
            "admitted": True,
            "candidate_source_span_ids": [
                item.source_span_id for item in plan.candidate_source_spans
            ],
            "selected_coverage_count": len(receipt.selected_source_coverage_keys),
            "semantic_truth_verified": receipt.semantic_truth_verified,
        }

    missing_preservation = _plan_arguments(co_located=True)
    missing_preservation["exploration_state"]["preservation_obligations"][0][
        "evidence_source_span_ids"
    ] = ["cspan:11:0"]

    span_id = one_state.source_spans[0].source_span_id
    inspection_arguments = {
        "path": RUNTIME_PATH,
        "start_line": 58,
        "end_line": 89,
        "investigation_intent": {
            "status": "need_more_evidence",
            "blocking_question": "Where is the public transition completed?",
            "basis_source_span_ids": [span_id],
            "target_role": "execution_path",
            "expected_information_gain": ("This read can locate the public completion boundary."),
        },
    }
    _, target = validate_investigation_action(
        task=task,
        state=one_state,
        tool="read_file",
        arguments=inspection_arguments,
    )
    outside = copy.deepcopy(inspection_arguments)
    outside["path"] = "tests/private.py"

    limit_state = _state(source_count=1, used=10)
    if limit_state is None:
        raise ContractError("self-directed limit state is unavailable")
    limit_decision = project_self_directed_workflow_decision(
        base_decision=_decision(used=10),
        state=limit_state,
        source_tool_schemas=tuple(TOOL_SCHEMAS_V26),
        events=(),
    )
    stop_arguments = {
        "status": "not_ready",
        "blocking_question": "Which public boundary owns the state transition?",
        "basis_source_span_ids": [limit_state.source_spans[0].source_span_id],
        "reason": "evidence_budget_exhausted",
    }
    stop = validate_exploration_stop(state=limit_state, arguments=stop_arguments)

    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V23,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V23,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V23,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V23,
            "exploration_policy_version": (LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23),
            "opt_in_successor": True,
        },
        "tool_contract": {
            "v26_tool_names": [item["name"] for item in TOOL_SCHEMAS_V26],
            "explicit_stop_registered": any(
                item["name"] == "declare_exploration_exhausted" for item in TOOL_SCHEMAS_V26
            ),
            "single_model_turn_choice": True,
        },
        "minimum_floor_and_choice": {
            "before_source_read": list(zero_decision.allowed_tool_names),
            "after_first_source_read": list(one_decision.allowed_tool_names),
            "plan_request_present": one_request is not None,
            "investigation_intent_required_after_first_read": (
                one_decision.investigation_intent_required
            ),
            "intent_is_dynamic_enum": read_schema["parameters"]["properties"][
                "investigation_intent"
            ]["properties"]["basis_source_span_ids"]["items"]["enum"],
            "search_counts_as_source_coverage": False,
        },
        "readiness": {
            **readiness,
            "co_located_missing_preservation_reason": _reason_code(
                lambda: normalize_self_directed_plan(
                    task=task,
                    catalog=two_catalog,
                    request_projection=_request(two_catalog),
                    trigger="initial",
                    revision_index=0,
                    parent_plan_hash=None,
                    trigger_check_id=None,
                    trigger_event_sequence=None,
                    cross_reset_trigger=None,
                    history=(),
                    raw_arguments=missing_preservation,
                )
            ),
            "confidence_score_used": False,
            "semantic_understanding_verified_by_admission": False,
        },
        "investigation_admission": {
            "valid_target_hash": target.target_hash,
            "duplicate_target_reason": _reason_code(
                lambda: validate_investigation_action(
                    task=task,
                    state=one_state,
                    tool="read_file",
                    arguments=inspection_arguments,
                    prior_target_hashes=(target.target_hash,),
                )
            ),
            "outside_scope_reason": _reason_code(
                lambda: validate_investigation_action(
                    task=task,
                    state=one_state,
                    tool="read_file",
                    arguments=outside,
                )
            ),
            "intent_semantic_truth_judged": False,
        },
        "bounded_stop": {
            "information_actions_used": limit_state.information_actions_used,
            "information_action_limit": limit_state.information_action_limit,
            "allowed_tools": list(limit_decision.allowed_tool_names),
            "stop_receipt_hash": sha256_json(stop),
            "patch_created": False,
            "submission_created": False,
        },
        "durable_context": {
            "recent_investigation_cards": 3,
            "chain_hash_retained": True,
            "active_plan_and_latest_disposition_retained": True,
            "raw_source_body_duplicated": False,
            "raw_reasoning_retained": False,
            "private_or_hidden_material_used": False,
        },
        "validated_runner_surfaces": {
            "optional_second_read_then_plan": True,
            "invalid_intent_shared_recovery_then_terminal": True,
            "failed_check_exploration_revision_same_check": True,
            "review_revision_full_revalidation": True,
            "explicit_exhaustion_no_patch_or_submission": True,
            "restart_state_and_surface_identical": True,
            "edit_rejection_fresh_reread_without_revision": True,
            "v22_repeated_failure_pivot_preserved": True,
        },
    }


def build_workflow_self_directed_exploration_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 29, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v23-bounded-self-directed-public-exploration",
        "policy_version": LEAN_SELF_DIRECTED_EXPLORATION_POLICY_VERSION_V23,
        "scenarios": _scenarios(),
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_predecessors": [
            _predecessor_identity(root, relative) for relative in IMMUTABLE_PREDECESSORS
        ],
        "validated_test_surfaces": {
            "focused_schema_and_admission": True,
            "real_shaped_public_mock_runner": True,
            "crash_restart_and_replay": True,
            "v19_v20_v21_v22_regression": True,
            "format_and_static_checks": True,
        },
        "evidence_boundary": {
            "qualification_builder_uses_public_synthetic_inputs_only": True,
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
        "runtime_contract_available": True,
        "external_activation_performed": False,
        "external_calls": 0,
        "candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
        "next_gate": "separate-lean-v23-activation-review",
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("self-directed qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_self_directed_exploration_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_self_directed_exploration_successor_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_self_directed_exploration_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("self-directed qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("self-directed qualification bytes differ")
    if value != build_workflow_self_directed_exploration_successor_qualification(root):
        raise ContractError("self-directed qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_self_directed_exploration_successor_qualification",
    "load_workflow_self_directed_exploration_successor_qualification",
    "materialize_workflow_self_directed_exploration_successor_qualification",
    "qualification_bytes",
]
