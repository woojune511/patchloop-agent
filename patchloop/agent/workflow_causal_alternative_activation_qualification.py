"""Deterministic zero-call qualification for the Lean V17 causal activation."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V17,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V17,
    LEAN_RUNTIME_POLICY_VERSION_V17,
    LEAN_TOOL_SCHEMA_VERSION_V17,
)
from patchloop.agent.tools import TOOL_SCHEMAS_V21
from patchloop.agent.workflow_causal_alternative_activation import (
    CAUSAL_ACTIVATION_POLICY,
    CausalWorkPlanBinding,
    build_causal_work_plan_binding,
    build_cross_reset_failure_trigger,
    causal_plan_binding_for_hash,
    causal_reset_gate_id,
    cross_reset_epoch_events,
    project_active_cross_reset_trigger,
    project_causal_reset_decision,
    project_causal_workflow_tool_surface,
    project_cross_reset_semantic_progress_state,
    standard_plan_from_causal_alternative,
    workflow_instruction_v4,
)
from patchloop.agent.workflow_causal_alternative_successor import (
    CAUSAL_ALTERNATIVE_POLICY,
    project_mutation_baseline,
    record_mutation_baseline_restore,
    validate_causal_alternative_plan,
)
from patchloop.agent.workflow_causal_alternative_successor_qualification import (
    ALTERNATIVE_PATH,
    EMPTY_DIFF,
    MUTATION_PATH,
    _alternative_raw,
    _arguments,
    _catalog,
    _events,
    _history,
    _state,
    _task,
)
from patchloop.agent.workflow_semantic_progress_successor import WorkflowDecisionV3
from patchloop.agent.workflow_successor import project_public_task_spec
from patchloop.agent.workflow_successor_v2 import EligiblePlanEvidenceCatalogV2
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.util import canonical_json, ensure_within, sha256_bytes, sha256_json

SCHEMA_VERSION = "lean-causal-alternative-activation-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-causal-alternative-activation-public-qualification-20260826-v1.json"
)
PREDECESSOR_PATH = Path(
    "experiments/lean-harness-causal-alternative-public-qualification-20260826-v1.json"
)
PREDECESSOR_BYTES = 5_415
PREDECESSOR_FILE_SHA256 = "sha256:6253dea939e818146bb63d7a848a524b79eceb7cc120a06c193e3ce4c5962247"
PREDECESSOR_CONTENT_HASH = "sha256:d496a68ee50c67ba5635cbe59a8acfe881d3476d98e867d9846d42bf8028321b"
SOURCE_FILES = (
    "patchloop/agent/workflow_causal_alternative_activation.py",
    "patchloop/agent/workflow_causal_alternative_activation_qualification.py",
    "patchloop/agent/workflow_causal_alternative_successor.py",
    "patchloop/agent/workflow_semantic_progress_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_causal_alternative_activation_qualification.py",
    "tests/test_tool_gateway.py",
    "tests/test_workflow_causal_alternative_activation_qualification.py",
    "tests/test_workflow_successor_v2_runner.py",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"causal activation source is unavailable: {relative}")
    raw = selected.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _predecessor(root: Path) -> dict[str, Any]:
    selected = ensure_within(root, PREDECESSOR_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal activation predecessor is unavailable") from exc
    if not (
        len(raw) == PREDECESSOR_BYTES
        and sha256_bytes(raw) == PREDECESSOR_FILE_SHA256
        and document.get("content_hash") == PREDECESSOR_CONTENT_HASH
        and document.get("runtime_activation_authorized") is False
        and document.get("rapid_candidate_created") is False
    ):
        raise ContractError("causal activation predecessor differs")
    return {
        "path": PREDECESSOR_PATH.as_posix(),
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
        "content_hash": document["content_hash"],
    }


def _event(sequence: int, event_type: EventType, payload: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=f"evt_causal_activation_{sequence}",
        run_id="run_causal_alternative_qualification",
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 26, tzinfo=UTC),
        actor="qualification",
        correlation_id=None,
        payload=payload,
    )


def _catalog_v2() -> EligiblePlanEvidenceCatalogV2:
    task = _task()
    predecessor = _catalog(task)
    body = {
        **predecessor.model_dump(mode="python", exclude={"schema_version", "content_hash"}),
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "required_trigger_status": "not_required",
        "required_trigger_event_sequence": None,
        "required_trigger_evidence_id": None,
        "model_visible_pinned_event_sequences": (),
        "unavailable_reason": None,
    }
    return EligiblePlanEvidenceCatalogV2.model_validate({**body, "content_hash": sha256_json(body)})


def _base_decision(state, history) -> WorkflowDecisionV3:
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
        "required_trigger_evidence_id": f"pev:{state.current_failure_event_sequence}",
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


def _scenarios() -> dict[str, Any]:
    task = _task()
    state = _state()
    catalog = _catalog_v2()
    history = _history(task, catalog)
    baseline = project_mutation_baseline(semantic_progress_state=state, events=_events())
    receipt = record_mutation_baseline_restore(
        baseline=baseline,
        observed_before_diff_hash=baseline.current_failed_diff_hash,
        observed_after_diff_hash=baseline.baseline_diff_hash,
        restored_action_ids=baseline.restore_action_ids,
        restored_intent_hashes=baseline.restore_intent_hashes,
    )
    trigger = build_cross_reset_failure_trigger(
        state=state,
        baseline=baseline,
        receipt=receipt,
        restored_event_sequence=7,
    )
    completion = _event(
        7,
        EventType.MUTATION_BASELINE_RESTORED,
        {
            "trigger": trigger.model_dump(mode="json"),
            "trigger_hash": trigger.content_hash,
            "baseline_projection": baseline.model_dump(mode="json"),
            "baseline_projection_hash": baseline.content_hash,
            "restore_receipt": receipt.model_dump(mode="json"),
            "restore_receipt_hash": receipt.content_hash,
            "semantic_progress_state": state.model_dump(mode="json"),
            "semantic_progress_state_hash": state.content_hash,
        },
    )
    active_trigger = project_active_cross_reset_trigger(
        run_id=state.run_id,
        current_diff_hash=EMPTY_DIFF,
        events=(*_events(), completion),
    )
    restored_state = project_cross_reset_semantic_progress_state(
        run_id=state.run_id,
        trigger=trigger,
        events=(*_events(), completion),
    )
    read = _event(
        8,
        EventType.TOOL_SUCCEEDED,
        {"tool": "read_file", "worktree_diff_hash": EMPTY_DIFF},
    )
    search = _event(
        9,
        EventType.TOOL_SUCCEEDED,
        {"tool": "search_files", "worktree_diff_hash": EMPTY_DIFF},
    )
    base_decision = _base_decision(state, history)
    initial_decision = project_causal_reset_decision(
        base_decision=base_decision,
        semantic_progress_state=state,
        trigger=trigger,
        history=history,
        events=(completion,),
        accepted_plan_hash=None,
    )
    read_decision = project_causal_reset_decision(
        base_decision=base_decision,
        semantic_progress_state=state,
        trigger=trigger,
        history=history,
        events=(completion, read),
        accepted_plan_hash=None,
    )
    revision_decision = project_causal_reset_decision(
        base_decision=base_decision,
        semantic_progress_state=state,
        trigger=trigger,
        history=history,
        events=(completion, read, search),
        accepted_plan_hash=None,
    )
    revise_schema = copy.deepcopy(
        next(item for item in TOOL_SCHEMAS_V21 if item["name"] == "revise_work_plan")
    )
    surface = project_causal_workflow_tool_surface(
        decision=revision_decision,
        catalog=catalog,
        source_tool_schemas=(revise_schema,),
        trigger=trigger,
        history=history,
    )
    parameters = surface.selected_tool_schemas[0]["parameters"]
    instruction = workflow_instruction_v4(
        revision_decision,
        public_task_spec=project_public_task_spec(task).model_dump(mode="json"),
        catalog=catalog,
        active_work_state=None,
        semantic_progress_state=state,
        trigger=trigger,
        history=history,
    )
    alternative, _ = validate_causal_alternative_plan(
        task=task,
        catalog=catalog,
        semantic_progress_state=state,
        baseline=baseline,
        restore_receipt=receipt,
        history=history,
        parent_plan_hash=history[-1].plan_hash,
        arguments=_arguments(history[-1].mechanism.content_hash, _alternative_raw()),
    )
    standard_plan = standard_plan_from_causal_alternative(
        task=task,
        catalog=catalog,
        alternative=alternative,
    )
    binding = build_causal_work_plan_binding(
        plan=standard_plan,
        plan_event_sequence=10,
        mechanism=alternative.alternative_causal_mechanism,
        alternative_plan=alternative,
        cross_reset_trigger_hash=trigger.content_hash,
    )
    binding_event = _event(
        11,
        EventType.CAUSAL_MECHANISM_RECORDED,
        {
            "binding_hash": binding.content_hash,
            "binding": binding.model_dump(mode="json"),
        },
    )
    restored_binding = causal_plan_binding_for_hash(
        run_id=state.run_id,
        plan_hash=standard_plan.content_hash,
        events=(binding_event,),
    )
    accepted_decision = project_causal_reset_decision(
        base_decision=base_decision,
        semantic_progress_state=state,
        trigger=trigger,
        history=history,
        events=(completion, read, search),
        accepted_plan_hash=standard_plan.content_hash,
    )
    gate_id = causal_reset_gate_id(trigger, history[-1].plan_hash)
    blocked = tuple(
        _event(
            sequence,
            EventType.TOOL_ADMISSION_BLOCKED,
            {
                "policy_version": CAUSAL_ALTERNATIVE_POLICY,
                "plan_gate_id": gate_id,
            },
        )
        for sequence in (12, 13)
    )
    try:
        project_causal_reset_decision(
            base_decision=base_decision,
            semantic_progress_state=state,
            trigger=trigger,
            history=history,
            events=(completion, *blocked),
            accepted_plan_hash=None,
        )
    except ContractError as exc:
        repeated_reason_codes = exc.details.get("reason_codes", [])
    else:
        raise ContractError("causal activation admitted a third plan attempt")
    tampered = binding.model_dump(mode="json")
    tampered["plan_hash"] = "sha256:" + "f" * 64
    try:
        CausalWorkPlanBinding.model_validate_json(canonical_json(tampered))
    except ValueError:
        tampered_binding_rejected = True
    else:
        tampered_binding_rejected = False
    if not tampered_binding_rejected:
        raise ContractError("causal activation accepted a tampered binding")
    later_patch = _event(
        14,
        EventType.PATCH_APPLIED,
        {"worktree_diff_hash": "sha256:" + "e" * 64},
    )
    trigger_after_mutation = project_active_cross_reset_trigger(
        run_id=state.run_id,
        current_diff_hash="sha256:" + "e" * 64,
        events=(completion, later_patch),
    )
    serialized = canonical_json(
        {
            "parameters": parameters,
            "instruction": instruction,
            "binding": binding.model_dump(mode="json"),
        }
    )
    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V17,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V17,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V17,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V17,
            "activation_policy_version": CAUSAL_ACTIVATION_POLICY,
        },
        "restore_trigger": {
            "baseline_projection_hash": baseline.content_hash,
            "restore_receipt_hash": receipt.content_hash,
            "trigger_hash": trigger.content_hash,
            "active_at_restored_baseline": active_trigger == trigger,
            "semantic_state_round_trip_exact": restored_state == state,
            "epoch_event_count_after_restore": len(
                cross_reset_epoch_events((*_events(), completion))
            ),
            "trigger_cleared_after_mutation": trigger_after_mutation is None,
            "failure_events_deleted": False,
        },
        "bounded_workflow": {
            "initial_allowed_tools": list(initial_decision.allowed_tool_names),
            "after_read_allowed_tools": list(read_decision.allowed_tool_names),
            "after_read_search_target": revision_decision.target,
            "after_plan_allowed_tools": list(accepted_decision.allowed_tool_names),
            "third_plan_dispatch_blocked": repeated_reason_codes
            == ["causal_alternative_admission_repeated"],
            "initial_plus_corrective_mutation_limit": "1+3",
            "correction_limit_changed": False,
            "review_correction_limit_changed": False,
        },
        "generic_plan_surface": {
            "top_level_keys": list(parameters["properties"]),
            "causal_mechanism_keys": list(
                parameters["properties"]["alternative_causal_mechanism"]["properties"]
            ),
            "task_specific_field_names": [],
            "exception_specific_key_present": ("why_exception_reaches_mutation_site" in serialized),
            "current_source_dynamic_enum": parameters["properties"]["foundation_evidence_ids"][
                "items"
            ]["enum"],
        },
        "durable_binding": {
            "plan_hash": standard_plan.content_hash,
            "binding_hash": binding.content_hash,
            "round_trip_exact": restored_binding == binding,
            "tampered_binding_rejected": tampered_binding_rejected,
            "cross_reset_trigger_hash": binding.cross_reset_failure_trigger_hash,
            "candidate_paths": [item.path for item in standard_plan.candidate_files],
            "alternative_paths": [ALTERNATIVE_PATH, MUTATION_PATH],
        },
    }


def build_workflow_causal_alternative_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 26, tzinfo=UTC).isoformat(),
        "status": "offline-qualified",
        "scope": "lean-v17-gateway-causal-baseline-reset-and-generic-plan-activation",
        "immutable_predecessor": _predecessor(root),
        "scenarios": _scenarios(),
        "source_files": [_identity(root, relative) for relative in SOURCE_FILES],
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
        "mocked_runner_e2e_required": True,
        "runtime_activation_authorized": False,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "generalization_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("causal activation qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_causal_alternative_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_causal_alternative_activation_qualification(root)
    selected = ensure_within(root, QUALIFICATION_PATH.as_posix())
    raw = qualification_bytes(value)
    if selected.exists() and selected.read_bytes() != raw:
        raise ContractError("causal activation qualification already differs")
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.write_bytes(raw)
    return value


def load_workflow_causal_alternative_activation_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    selected = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = selected.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("causal activation qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("causal activation qualification bytes differ")
    if value != build_workflow_causal_alternative_activation_qualification(root):
        raise ContractError("causal activation qualification source binding differs")
    return value


__all__ = [
    "PREDECESSOR_PATH",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_causal_alternative_activation_qualification",
    "load_workflow_causal_alternative_activation_qualification",
    "materialize_workflow_causal_alternative_activation_qualification",
    "qualification_bytes",
]
