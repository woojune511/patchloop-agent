"""Deterministic zero-call qualification for opt-in Lean V21 plan-gate liveness."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V21,
    LEAN_PLAN_GATE_LIVENESS_POLICY_VERSION_V21,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
    LEAN_RUNTIME_POLICY_VERSION_V21,
    LEAN_TOOL_SCHEMA_VERSION_V21,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    project_activated_causal_plan_request,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    _arguments,
    _catalog,
    _task,
)
from patchloop.agent.workflow_plan_gate_liveness_successor import (
    PLAN_GATE_LIVENESS_POLICY,
    bind_recovered_plan_gate_pin,
    normalize_pinned_exploration_plan,
    project_pinned_evidence_catalog,
    project_pinned_exploration_plan_request,
    project_pinned_plan_gate_decision,
    project_plan_gate_readiness_snapshot,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    WORKFLOW_POLICY_V15,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-plan-gate-liveness-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-plan-gate-liveness-public-qualification-20260827-v1.json"
)

IMMUTABLE_PREDECESSORS = {
    (
        "experiments/"
        "lean-harness-semantic-progress-epoch-parity-public-qualification-20260827-v1.json"
    ): {
        "bytes": 4_750,
        "file_sha256": "sha256:88d5e7881cade273e2b9a31652ea4d6ace29e572970a47a0bc04a528cf345ceb",
        "content_hash": "sha256:ec05fe5665686deafbdfb16d5d5dd50c7089845cb3c0b99bf4da697b3ecfe5f7",
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-v5-terminal-parity-ab-20260827-r18-candidate-v26.json"
    ): {
        "bytes": 15_734,
        "file_sha256": "sha256:f5e3d50d4c4368d1a283d7a0b732397c956077d5e4da6f5b421d205745949a8e",
        "content_hash": "sha256:073d744112cf39f1046ef0414f0cf2c22b13abc3dfc76bc84eec110d6283da17",
    },
    (
        "reports/rapid-development/"
        "rapid-public-dev-anyio-v5-terminal-parity-ab-20260827-r18-afcc526c747f.jsonl"
    ): {
        "bytes": 40_736,
        "file_sha256": "sha256:0731a2ec33329430b981186913385b185b6a172943604727e9b54be35a1798bd",
        "final_event_hash": (
            "sha256:05bff5ae9e2a2f4bc160453fa9e7ce975f82889f8e0fa0b1b4574962d187e606"
        ),
    },
    (
        "reports/rapid-development/artifacts/"
        "rapid-public-dev-anyio-v5-terminal-parity-ab-20260827-r18-"
        "v20-exploration-diagnosis-v1.json"
    ): {
        "bytes": 31_828,
        "file_sha256": "sha256:15a3b155b089443f262c815c7ad3ab97dfe0507f63a0b3886b1f82f4b2e4ced3",
        "content_hash": "sha256:1e83ccc28c8f9c196ba51e551ba8c9044d36af6a734559301df92a65a99c560f",
    },
}

SOURCE_FILES = (
    "patchloop/agent/workflow_plan_gate_liveness_successor.py",
    "patchloop/agent/workflow_plan_gate_liveness_successor_qualification.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_plan_gate_liveness_qualification.py",
    "tests/test_workflow_plan_gate_liveness_successor.py",
    "tests/test_workflow_plan_gate_liveness_successor_qualification.py",
    "tests/test_workflow_successor_v2_runner.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = ensure_within(root, relative)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"plan-gate liveness input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _predecessor_identity(root: Path, relative: str) -> dict[str, Any]:
    identity = _identity(root, relative)
    expected = IMMUTABLE_PREDECESSORS[relative]
    raw = ensure_within(root, relative).read_bytes()
    if "content_hash" in expected:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("plan-gate predecessor is not JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: value for key, value in document.items() if key != "content_hash"}
        ):
            raise ContractError("plan-gate predecessor content hash differs")
        identity["content_hash"] = content_hash
    if "final_event_hash" in expected:
        try:
            final_event = json.loads(raw.splitlines()[-1])
        except (IndexError, UnicodeDecodeError, ValueError) as exc:
            raise ContractError("plan-gate predecessor is not JSONL") from exc
        if final_event.get("event") != "batch-completed":
            raise ContractError("plan-gate predecessor lacks completion")
        identity["final_event_hash"] = final_event.get("content_hash")
    if {key: identity.get(key) for key in expected} != expected:
        raise ContractError(f"immutable plan-gate predecessor differs: {relative}")
    return identity


def _catalog_v2(*, keep_source: bool = True) -> EligiblePlanEvidenceCatalogV2:
    source = _catalog(include_failed_check=False)
    items = (
        source.items
        if keep_source
        else tuple(item for item in source.items if item.kind != "source_read")
    )
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


def _decision(
    *,
    recovery_used: bool = False,
    terminal_reason: str | None = None,
) -> WorkflowDecisionV3:
    terminal = terminal_reason is not None
    body = {
        "schema_version": "lean-workflow-decision-v3",
        "runtime_policy_version": "lean-harness-v15",
        "policy_version": WORKFLOW_POLICY_V15,
        "target": "terminal" if terminal else "pre-mutation-exploration",
        "current_diff_hash": _catalog_v2().worktree_diff_hash,
        "expected_check_id": None,
        "allowed_tool_names": () if terminal else ("search_files", "read_file"),
        "information_actions_in_episode": 0,
        "fresh_current_read": False,
        "corrective_mutations_for_check": 0,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": 4,
        "active_plan_hash": None,
        "plan_gate_id": "sha256:" + "4" * 64,
        "plan_admission_recovery_used": recovery_used,
        "plan_admission_recovery_remaining": 0 if recovery_used else 1,
        "required_trigger_evidence_id": None,
        "revision_trigger": None,
        "terminal_reason": terminal_reason,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 1 if terminal else 4_096,
        "reasoning_effort": "low",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
        "semantic_progress_state_hash": None,
        "semantic_reset_required": False,
        "required_prior_hypothesis_disposition": None,
    }
    return WorkflowDecisionV3.model_validate({**body, "content_hash": sha256_json(body)})


def _single_unknown_arguments() -> dict[str, Any]:
    arguments = _arguments()
    question = arguments.pop("unknowns")[0]
    arguments["exploration_state"] = {
        "boundary_coverage": {
            "ownership_boundary_span_ids": ["cspan:10:0"],
            "execution_boundary_span_ids": ["cspan:11:0"],
            "mutation_boundary_span_ids": ["cspan:10:0"],
        },
        "invariants": [
            {
                "subject": "Public lifecycle ownership",
                "claim": "Two current-source ranges jointly own the transition.",
                "evidence_source_span_ids": ["cspan:10:0", "cspan:11:0"],
            }
        ],
        "preservation_obligations": [
            {
                "public_requirement": "Preserve the later visible lifecycle step.",
                "expected_behavior": "Visible checks remain ordered after the edit.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "unknown_dispositions": [
            {
                "question": question,
                "disposition": "non_blocking",
                "explanation": "The bounded transition does not depend on this question.",
                "evidence_source_span_ids": ["cspan:11:0"],
            }
        ],
        "open_blocking_unknowns": [],
    }
    return arguments


def _reason_code(call: Callable[[], Any]) -> str:
    try:
        call()
    except ContractError as exc:
        reasons = exc.details.get("reason_codes")
        if isinstance(reasons, list) and len(reasons) == 1:
            return str(reasons[0])
        raise ContractError("plan-gate rejection lacks one typed reason") from exc
    raise ContractError("plan-gate negative scenario did not reject")


def _recovery_message(call: Callable[[], Any]) -> str:
    try:
        call()
    except RecoveryError as exc:
        return str(exc)
    raise ContractError("plan-gate recovery scenario did not reject")


def _request():
    catalog = project_pinned_evidence_catalog(base=_catalog_v2(), pin=None)
    base = project_activated_causal_plan_request(
        task=_task(),
        catalog=catalog,
        trigger="initial",
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
    )
    return project_pinned_exploration_plan_request(base)


def _scenarios() -> dict[str, Any]:
    catalog = _catalog_v2()
    decision = _decision()
    readiness = project_plan_gate_readiness_snapshot(
        task=_task(), decision=decision, catalog=catalog
    )
    if readiness is None:
        raise ContractError("constructible plan gate was not detected")
    forced = project_pinned_plan_gate_decision(decision=decision, readiness=readiness, pin=None)
    pin = bind_recovered_plan_gate_pin(
        snapshot=readiness,
        source_model_event_sequence=20,
        source_request_artifact_hash="sha256:" + "a" * 64,
        source_request_body_hash="sha256:" + "b" * 64,
    )
    recovered_catalog = project_pinned_evidence_catalog(
        base=_catalog_v2(keep_source=False), pin=pin
    )
    recovered = project_pinned_plan_gate_decision(
        decision=_decision(recovery_used=True), readiness=None, pin=pin
    )
    repeated = _decision(recovery_used=True, terminal_reason="work_plan_admission_repeated")
    repeated_after_projection = project_pinned_plan_gate_decision(
        decision=repeated, readiness=None, pin=pin
    )

    request = _request()
    arguments = _single_unknown_arguments()
    plan, receipt = normalize_pinned_exploration_plan(
        task=_task(),
        catalog=project_pinned_evidence_catalog(base=catalog, pin=None),
        request_projection=request,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=arguments,
    )
    duplicated = copy.deepcopy(arguments)
    duplicated["unknowns"] = ["duplicate"]
    stale = _catalog_v2().model_copy(update={"worktree_diff_hash": "sha256:" + "f" * 64})
    wrong_gate = _decision().model_copy(update={"plan_gate_id": "sha256:" + "9" * 64})

    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V21,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V21,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V21,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V21,
            "plan_gate_liveness_policy_version": (LEAN_PLAN_GATE_LIVENESS_POLICY_VERSION_V21),
        },
        "constructible_initial_plan": {
            "readiness_hash": readiness.content_hash,
            "distinct_source_coverage_keys": len(readiness.distinct_source_coverage_keys),
            "forced_target": forced.target,
            "forced_tools": list(forced.allowed_tool_names),
            "raw_source_body_retained": readiness.raw_source_body_retained,
            "raw_reasoning_retained": readiness.raw_reasoning_retained,
        },
        "one_recovered_retry": {
            "pin_hash": pin.content_hash,
            "actual_model_visible_request": pin.actual_model_visible_request,
            "source_model_event_sequence": pin.source_model_event_sequence,
            "recovered_catalog_status": recovered_catalog.plan_gate_readiness_status,
            "recovered_evidence_ids": list(recovered_catalog.plan_gate_pinned_evidence_ids),
            "retry_target": recovered.target,
            "retry_tools": list(recovered.allowed_tool_names),
            "repeated_terminal_preserved": repeated_after_projection == repeated,
            "repeated_terminal_reason": repeated_after_projection.terminal_reason,
        },
        "canonical_unknown": {
            "top_level_unknown_schema_present": (
                "unknowns" in request.parameters.get("properties", {})
            ),
            "recorded_unknowns": list(plan.unknowns),
            "unknown_disposition_questions": [
                item["question"] for item in arguments["exploration_state"]["unknown_dispositions"]
            ],
            "closure_receipt_hash": receipt.content_hash,
            "duplicate_rejection": _reason_code(
                lambda: normalize_pinned_exploration_plan(
                    task=_task(),
                    catalog=project_pinned_evidence_catalog(base=catalog, pin=None),
                    request_projection=request,
                    trigger="initial",
                    revision_index=0,
                    parent_plan_hash=None,
                    trigger_check_id=None,
                    trigger_event_sequence=None,
                    cross_reset_trigger=None,
                    history=(),
                    raw_arguments=duplicated,
                )
            ),
        },
        "fail_closed": {
            "stale_diff": _recovery_message(
                lambda: project_pinned_evidence_catalog(base=stale, pin=pin)
            ),
            "foreign_gate": _recovery_message(
                lambda: project_pinned_plan_gate_decision(
                    decision=wrong_gate, readiness=None, pin=pin
                )
            ),
        },
        "preserved_limits": {
            "v20_behavior_modified": False,
            "r18_retry_allowed": False,
            "raw_request_or_reasoning_replayed": False,
            "runtime_activation_is_opt_in": True,
            "rapid_candidate_created": False,
        },
    }


def build_workflow_plan_gate_liveness_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v21-public-plan-gate-liveness",
        "policy_version": PLAN_GATE_LIVENESS_POLICY,
        "scenarios": _scenarios(),
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
        "immutable_predecessors": [
            _predecessor_identity(root, relative) for relative in IMMUTABLE_PREDECESSORS
        ],
        "validated_test_surfaces": {
            "focused_unit": True,
            "real_shaped_mock_runner": True,
            "crash_restart_between_rejection_and_retry": True,
            "broad_v19_v20_gateway_regression": True,
        },
        "evidence_boundary": {
            "public_synthetic_projection_only": True,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "workspace_runtime_mutations": 0,
            "added_cost_usd": "0",
        },
        "runtime_surface_activated": True,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("plan-gate liveness qualification hash differs")
    return (canonical_json(value) + "\n").encode()


def materialize_workflow_plan_gate_liveness_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_plan_gate_liveness_successor_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_plan_gate_liveness_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("plan-gate liveness qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("plan-gate liveness qualification bytes differ")
    if value != build_workflow_plan_gate_liveness_successor_qualification(root):
        raise ContractError("plan-gate liveness source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_plan_gate_liveness_successor_qualification",
    "load_workflow_plan_gate_liveness_successor_qualification",
    "materialize_workflow_plan_gate_liveness_successor_qualification",
    "qualification_bytes",
]
