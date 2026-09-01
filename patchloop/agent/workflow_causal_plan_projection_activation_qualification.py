"""Deterministic zero-call qualification for the Lean V18 projection activation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V18,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V18,
    LEAN_RUNTIME_POLICY_VERSION_V18,
    LEAN_TOOL_SCHEMA_VERSION_V18,
)
from patchloop.agent.workflow_causal_alternative_activation import (
    CrossResetFailureTrigger,
    causal_reset_gate_id,
)
from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
)
from patchloop.agent.workflow_causal_plan_projection_activation import (
    CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY,
    CausalMechanismHistoryEntryV2,
    build_causal_work_plan_binding_v2,
    normalize_activated_causal_plan,
    project_activated_causal_plan_request,
    project_causal_mechanism_history_v2,
    project_causal_reset_decision_v2,
    standard_plan_from_projected_causal_plan,
)
from patchloop.agent.workflow_causal_plan_projection_successor import (
    normalize_causal_plan_request,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    EMPTY_DIFF,
    HANDLER_PATH,
    RUN_ID,
    RUNTIME_PATH,
    _arguments,
    _catalog,
    _read,
    _support,
    _task,
    load_workflow_causal_plan_projection_successor_qualification,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    IMMUTABLE_PREDECESSORS as SOURCE_IMMUTABLE_PREDECESSORS,
)
from patchloop.agent.workflow_causal_plan_projection_successor_qualification import (
    QUALIFICATION_PATH as SOURCE_QUALIFICATION_PATH,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    PublicSemanticProgressState,
    WorkflowDecisionV3,
)
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import (
    canonical_json,
    ensure_within,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

SCHEMA_VERSION = "lean-causal-plan-projection-activation-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/"
    "lean-harness-causal-plan-projection-activation-public-qualification-20260826-v1.json"
)
SOURCE_QUALIFICATION_BYTES = 4_864
SOURCE_QUALIFICATION_FILE_SHA256 = (
    "sha256:ec44c6aefa6d4963e1bd4aaf52483e1dc387b9f5b2cb1cb643e5bb1d2e4dd5fd"
)
SOURCE_QUALIFICATION_CONTENT_HASH = (
    "sha256:be4d3c7d779f6ce6dd80b5ff40f8eda4fabab9120798b8529dc145e1aa2aa64b"
)

IMMUTABLE_PREDECESSORS = {
    SOURCE_QUALIFICATION_PATH.as_posix(): {
        "bytes": SOURCE_QUALIFICATION_BYTES,
        "file_sha256": SOURCE_QUALIFICATION_FILE_SHA256,
        "content_hash": SOURCE_QUALIFICATION_CONTENT_HASH,
    },
    **SOURCE_IMMUTABLE_PREDECESSORS,
}

SOURCE_FILES = (
    "patchloop/agent/workflow_causal_plan_projection_activation.py",
    "patchloop/agent/workflow_causal_plan_projection_activation_qualification.py",
    "patchloop/agent/workflow_causal_plan_projection_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_causal_plan_projection_activation_qualification.py",
    "tests/test_workflow_causal_plan_projection_activation.py",
    "tests/test_workflow_causal_plan_projection_activation_qualification.py",
    "tests/test_workflow_successor_v2_runner.py",
)


def _identity(root: Path, relative: str, *, canonical_document: bool) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"projection activation input is unavailable: {relative}")
    raw = selected.read_bytes()
    value: dict[str, Any] = {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }
    if canonical_document:
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ContractError("projection activation predecessor is not JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: item for key, item in document.items() if key != "content_hash"}
        ):
            raise ContractError("projection activation predecessor content hash differs")
        value["content_hash"] = content_hash
    return value


def _catalog_v2() -> EligiblePlanEvidenceCatalogV2:
    task = _task()
    items = (
        _read(20, RUNTIME_PATH, ((20, 57), (90, 118))),
        _read(21, HANDLER_PATH, ((120, 170),)),
        _support(24),
    )
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": EMPTY_DIFF,
        "model_visible_context_hash": "sha256:" + "d" * 64,
        "model_visible_recent_event_sequences": tuple(
            item.canonical_event_sequence for item in items
        ),
        "items": tuple(item.model_dump(mode="python") for item in items),
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _history() -> tuple[CausalMechanismHistoryEntryV2, ...]:
    projected = normalize_causal_plan_request(
        task=_task(),
        catalog=_catalog(include_failed_check=False),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        raw_arguments=_arguments(),
    )
    return (
        CausalMechanismHistoryEntryV2(
            revision_index=0,
            plan_hash=sha256_json({"standard_plan": 0}),
            parent_plan_hash=None,
            trigger="initial",
            mechanism=projected.causal_mechanism,
            projected_plan_hash=projected.content_hash,
        ),
    )


def _state() -> PublicSemanticProgressState:
    failure = "same bounded public failure"
    body = {
        "schema_version": "public-semantic-progress-state-v1",
        "run_id": RUN_ID,
        "worktree_diff_hash": sha256_json({"diff": 2}),
        "check_id": "targeted",
        "current_failure_event_sequence": 41,
        "failure_signature": failure,
        "failure_signature_hash": sha256_text(failure),
        "same_signature_failed_diff_count": 2,
        "failure_event_sequences": (31, 41),
        "failed_diff_hashes": (
            sha256_json({"diff": 1}),
            sha256_json({"diff": 2}),
        ),
        "semantic_reset_required": True,
        "public_check_output_only": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return PublicSemanticProgressState.model_validate({**body, "content_hash": sha256_json(body)})


def _trigger(state: PublicSemanticProgressState) -> CrossResetFailureTrigger:
    body = {
        "schema_version": "cross-reset-public-failure-trigger-v1",
        "policy_version": "gateway-owned-causal-baseline-reset-v1",
        "run_id": RUN_ID,
        "check_id": "targeted",
        "failure_signature": state.failure_signature,
        "failure_signature_hash": state.failure_signature_hash,
        "failure_event_sequences": state.failure_event_sequences,
        "failed_diff_hashes": state.failed_diff_hashes,
        "source_semantic_progress_state_hash": state.content_hash,
        "mutation_baseline_projection_hash": sha256_json({"baseline": 1}),
        "mutation_baseline_restore_receipt_hash": sha256_json({"receipt": 1}),
        "restored_baseline_diff_hash": EMPTY_DIFF,
        "restored_event_sequence": 50,
        "public_check_output_only": True,
        "stale_check_authorizes_mutation": False,
        "current_source_read_required": True,
        "private_evidence_used": False,
        "hidden_evaluator_used": False,
        "reference_patch_used": False,
        "reasoning_text_used": False,
    }
    return CrossResetFailureTrigger.model_validate({**body, "content_hash": sha256_json(body)})


def _arguments_for(span_id: str) -> dict[str, Any]:
    arguments = _arguments()
    arguments["supporting_evidence_ids"] = []
    arguments["candidate_source_span_ids"] = [span_id]
    arguments["prior_hypothesis_disposition"] = "rejected"
    arguments["causal_mechanism"] = {
        "summary": "One current public source span owns the alternative transition.",
        "causal_boundary": {
            "source_span_id": span_id,
            "symbol": "alternative_boundary",
            "observation": "This current source span receives the public transition.",
            "relationship_to_next": "The same span commits the visible transition.",
        },
        "intermediate_steps": [],
        "mutation_site": {
            "source_span_id": span_id,
            "symbol": "alternative_mutation",
            "observation": "This current source span commits the visible transition.",
        },
        "mutation_site_rationale": "The evidence-bound assignment is the minimal edit site.",
        "expected_observable_effect": "The targeted check observes the corrected transition.",
        "falsification_condition": "The same public failure remains after the edit.",
    }
    return arguments


def _decision(
    state: PublicSemanticProgressState,
    history: tuple[CausalMechanismHistoryEntryV2, ...],
) -> WorkflowDecisionV3:
    body = {
        "schema_version": "lean-workflow-decision-v3",
        "runtime_policy_version": "lean-harness-v15",
        "policy_version": "public-failure-signature-no-progress-reset-v1",
        "target": "correction-investigation",
        "current_diff_hash": EMPTY_DIFF,
        "expected_check_id": None,
        "allowed_tool_names": ("search_files", "read_file"),
        "information_actions_in_episode": 0,
        "fresh_current_read": False,
        "corrective_mutations_for_check": 2,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": 0,
        "active_plan_hash": history[-1].plan_hash,
        "plan_gate_id": None,
        "plan_admission_recovery_used": False,
        "plan_admission_recovery_remaining": 1,
        "required_trigger_evidence_id": "pev:41",
        "revision_trigger": "check_failure",
        "terminal_reason": None,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 4_096,
        "reasoning_effort": "low",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
        "semantic_progress_state_hash": state.content_hash,
        "semantic_reset_required": True,
        "required_prior_hypothesis_disposition": "rejected",
    }
    return WorkflowDecisionV3.model_validate({**body, "content_hash": sha256_json(body)})


def _event(sequence: int, event_type: EventType, payload: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=f"evt_projection_activation_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 26, tzinfo=UTC),
        actor="qualification",
        correlation_id=None,
        payload=payload,
    )


def _reason_code(callable_: Any) -> str:
    try:
        callable_()
    except ContractError as exc:
        codes = exc.details.get("reason_codes", [])
        if isinstance(codes, list) and len(codes) == 1 and isinstance(codes[0], str):
            return codes[0]
        raise ContractError("projection activation rejection code differs") from exc
    raise ContractError("projection activation expected rejection")


def _scenarios() -> dict[str, Any]:
    task = _task()
    catalog = _catalog_v2()
    history = _history()
    state = _state()
    trigger = _trigger(state)
    projection = project_activated_causal_plan_request(
        task=task,
        catalog=catalog,
        trigger="check_failure",
        trigger_check_id="targeted",
        trigger_event_sequence=41,
        cross_reset_trigger=trigger,
    )
    common = {
        "task": task,
        "catalog": catalog,
        "request_projection": projection,
        "trigger": "check_failure",
        "revision_index": 1,
        "parent_plan_hash": history[-1].plan_hash,
        "trigger_check_id": "targeted",
        "trigger_event_sequence": 41,
        "cross_reset_trigger": trigger,
        "history": history,
    }
    projected = normalize_activated_causal_plan(
        **common, raw_arguments=_arguments_for("cspan:21:0")
    )
    standard = standard_plan_from_projected_causal_plan(
        task=task, catalog=catalog, projected=projected
    )
    binding = build_causal_work_plan_binding_v2(
        plan=standard,
        plan_event_sequence=60,
        projected=projected,
        request_projection=projection,
        cross_reset_trigger_hash=trigger.content_hash,
    )
    plan_event = _event(
        60,
        EventType.PLAN_RECORDED,
        {
            "plan_hash": standard.content_hash,
            "revision_index": 1,
            "parent_plan_hash": history[-1].plan_hash,
            "trigger": "check_failure",
        },
    )
    binding_event = _event(
        61,
        EventType.CAUSAL_MECHANISM_RECORDED,
        {
            "schema_version": "causal-mechanism-recorded-v2",
            "binding_hash": binding.content_hash,
            "binding": binding.model_dump(mode="json"),
        },
    )
    recovered = project_causal_mechanism_history_v2(
        run_id=RUN_ID, events=(plan_event, binding_event)
    )
    tampered_projection = projection.model_copy(
        update={"parameter_schema_hash": sha256_json({"tampered": True})}
    )
    try:
        normalize_activated_causal_plan(
            **{**common, "request_projection": tampered_projection},
            raw_arguments=_arguments_for("cspan:21:0"),
        )
    except RecoveryError:
        tampered_projection_rejected = True
    else:
        tampered_projection_rejected = False

    base_decision = _decision(state, history)
    read = _event(
        51,
        EventType.TOOL_SUCCEEDED,
        {"tool": "read_file", "worktree_diff_hash": EMPTY_DIFF},
    )
    search = _event(
        52,
        EventType.TOOL_SUCCEEDED,
        {"tool": "search_files", "worktree_diff_hash": EMPTY_DIFF},
    )
    ready = project_causal_reset_decision_v2(
        base_decision=base_decision,
        semantic_progress_state=state,
        trigger=trigger,
        history=history,
        events=(read, search),
        accepted_plan_hash=None,
    )
    gate_id = causal_reset_gate_id(trigger, history[-1].plan_hash)
    blocked = _event(
        53,
        EventType.TOOL_ADMISSION_BLOCKED,
        {
            "policy_version": CAUSAL_ALTERNATIVE_POLICY,
            "plan_gate_id": gate_id,
        },
    )
    after_one = project_causal_reset_decision_v2(
        base_decision=base_decision,
        semantic_progress_state=state,
        trigger=trigger,
        history=history,
        events=(read, search, blocked),
        accepted_plan_hash=None,
    )
    repeated = _event(
        54,
        EventType.TOOL_ADMISSION_BLOCKED,
        {
            "policy_version": CAUSAL_ALTERNATIVE_POLICY,
            "plan_gate_id": gate_id,
        },
    )
    repeated_code = _reason_code(
        lambda: project_causal_reset_decision_v2(
            base_decision=base_decision,
            semantic_progress_state=state,
            trigger=trigger,
            history=history,
            events=(read, search, blocked, repeated),
            accepted_plan_hash=None,
        )
    )
    schema_text = canonical_json(projection.parameters)
    forbidden = (
        "observation_status",
        "foundation_evidence_ids",
        "candidate_files",
        "planned_check_ids",
        "role",
        "path",
        "start_line",
        "end_line",
        "read_evidence_id",
    )
    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V18,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V18,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V18,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V18,
            "activation_policy_version": CAUSAL_PLAN_PROJECTION_ACTIVATION_POLICY,
        },
        "dynamic_model_surface": {
            "runtime_surface_activated": projection.runtime_surface_activated,
            "span_ids": [
                item.source_span_id
                for item in projection.source_projection.source_span_catalog.spans
            ],
            "forbidden_server_fields_absent": all(
                f'"{field}"' not in schema_text for field in forbidden
            ),
            "stale_span_rejection": _reason_code(
                lambda: normalize_activated_causal_plan(
                    **common, raw_arguments=_arguments_for("cspan:10:0")
                )
            ),
            "tampered_projection_rejected_before_normalization": (tampered_projection_rejected),
        },
        "cross_reset_evidence_boundary": {
            "stale_check_observation_only": projection.stale_check_observation_only,
            "observation_evidence": projected.observation_evidence,
            "current_foundation_ids": [item.evidence_id for item in projected.foundation_evidence],
            "candidate_read_id": projected.candidate_files[0].read_evidence_id,
            "exhausted_current_boundary_rejection": _reason_code(
                lambda: normalize_activated_causal_plan(
                    **common, raw_arguments=_arguments_for("cspan:20:0")
                )
            ),
            "same_span_boundary_and_mutation_accepted": (
                projected.causal_mechanism.source_coverage_keys[0]
                == projected.causal_mechanism.source_coverage_keys[-1]
            ),
        },
        "durable_v2_binding": {
            "schema_version": binding.schema_version,
            "round_trip_exact": recovered[0].plan_hash == standard.content_hash,
            "projected_plan_hash": binding.projected_plan_hash,
            "request_projection_hash": binding.request_projection_hash,
            "stale_check_observation_only": binding.stale_check_observation_only,
        },
        "preserved_limits": {
            "after_read_search_target": ready.target,
            "after_read_search_tools": list(ready.allowed_tool_names),
            "first_rejection_consumes_recovery": (
                after_one.plan_admission_recovery_used
                and after_one.plan_admission_recovery_remaining == 0
            ),
            "second_rejection_reason": repeated_code,
            "third_plan_dispatch_blocked": repeated_code == "causal_alternative_admission_repeated",
            "corrective_mutation_limit": base_decision.corrective_mutations_for_check,
            "review_correction_limit": base_decision.review_corrections_used,
            "targeted_first_changed": False,
        },
    }


def build_workflow_causal_plan_projection_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    source_qualification = load_workflow_causal_plan_projection_successor_qualification(root)
    if (
        source_qualification.get("content_hash") != SOURCE_QUALIFICATION_CONTENT_HASH
        or source_qualification.get("runtime_surface_activated") is not False
    ):
        raise ContractError("source-qualified projection predecessor differs")

    predecessors: list[dict[str, Any]] = []
    for relative, expected in IMMUTABLE_PREDECESSORS.items():
        observed = _identity(root, relative, canonical_document=relative.endswith(".json"))
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable projection activation predecessor differs: {relative}")
        predecessors.append(observed)

    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 26, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v18-server-owned-causal-plan-projection-activation",
        "scenarios": _scenarios(),
        "source_files": [
            _identity(root, relative, canonical_document=False) for relative in SOURCE_FILES
        ],
        "immutable_predecessors": predecessors,
        "preservation_boundary": {
            "lean_v17_behavior_modified": False,
            "r13_retry_allowed": False,
            "source_projection_requalified": False,
            "activation_is_opt_in": True,
        },
        "evidence_boundary": {
            "public_synthetic_source_only": True,
            "task_fixture_files_read": False,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "workspace_mutations": 0,
            "added_cost_usd": "0",
        },
        "runtime_activation_authorized": True,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("projection activation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_causal_plan_projection_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_causal_plan_projection_activation_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_workflow_causal_plan_projection_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("projection activation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("projection activation qualification bytes differ")
    if value != build_workflow_causal_plan_projection_activation_qualification(root):
        raise ContractError("projection activation qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_causal_plan_projection_activation_qualification",
    "load_workflow_causal_plan_projection_activation_qualification",
    "materialize_workflow_causal_plan_projection_activation_qualification",
    "qualification_bytes",
]
