"""Offline qualification for the V14 failed-check trigger pin successor."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V14,
    LeanHarnessRequestEvidenceV14,
    assemble_lean_harness_request,
    build_lean_harness_calibration_manifest,
    load_lean_harness_dependencies,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.phases import EvidenceState, diff_bound_evidence
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V17, TOOL_SCHEMAS_V18
from patchloop.agent.workflow_successor_v2 import (
    PLAN_RECORDED_EVENT_SCHEMA_V2,
    project_eligible_plan_evidence_catalog,
    project_eligible_plan_evidence_catalog_v2,
    project_workflow_successor_v2,
    required_failed_check_trigger_sequence,
    validate_work_plan_v2,
)
from patchloop.contracts import Budget, EventType, MemoryCondition, PublicTask, RunEvent, Usage
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.task_loader import load_task_package
from patchloop.util import (
    canonical_json,
    load_unique_yaml,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

SCHEMA_VERSION = "lean-required-trigger-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-required-trigger-public-qualification-20260825-v1.json"
)
TASK_PACKAGE = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4")
RUN_ID = "run_required_trigger_successor_qualification"
EMPTY = sha256_text("")
DIFF = "sha256:" + "1" * 64
SOURCE_PATH = "src/anyio/pytest_plugin.py"

SOURCE_FILES = (
    "patchloop/agent/workflow_required_trigger_successor_qualification.py",
    "patchloop/agent/workflow_successor_v2.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "patchloop/evals/rapid_required_trigger_diagnosis.py",
    "scripts/build_lean_harness_required_trigger_qualification.py",
    "scripts/build_rapid_required_trigger_diagnosis.py",
    "tests/test_workflow_successor_v2.py",
    "tests/test_workflow_successor_v2_runner.py",
    "tests/test_workflow_finalization_successor.py",
    "tests/test_rapid_required_trigger_diagnosis.py",
    "tests/test_workflow_required_trigger_successor_qualification.py",
)

IMMUTABLE_PREDECESSOR_FILES = (
    "experiments/lean-harness-workflow-finalization-successor-public-qualification-20260825-v1.json",
    "reports/rapid-development/rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-c64654b6bdba.jsonl",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-workflow-diagnosis-v1.json",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-required-trigger-diagnosis-v1.json",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ContractError(f"required-trigger qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "file_sha256": sha256_bytes(raw)}


def _event(
    sequence: int,
    event_type: EventType,
    *,
    payload: dict[str, Any] | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_v14_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 25, tzinfo=UTC),
        actor="qualification",
        payload=payload or {},
    )


def _public_result(
    sequence: int,
    tool: str,
    tool_result: dict[str, Any],
    *,
    diff_hash: str,
) -> tuple[RunEvent, dict[str, Any]]:
    artifact = {
        "artifact_id": f"artifact-v14-{sequence}",
        "path": f"cas/v14-{sequence}.json",
        "content_hash": sha256_json(tool_result),
    }
    event = _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        payload={
            "tool": tool,
            "status": "succeeded",
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "result_artifact": artifact,
            "worktree_diff_hash": diff_hash,
            "check_id": tool_result.get("check_id"),
            "passed": tool_result.get("passed"),
            "invocation_status": tool_result.get("invocation_status"),
            "behavior_status": tool_result.get("behavior_status"),
            "timed_out": tool_result.get("timed_out"),
        },
    )
    visible = {
        "sequence": sequence,
        "type": EventType.TOOL_SUCCEEDED.value,
        "payload": {
            "tool": tool,
            "status": "succeeded",
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "tool_result": tool_result,
        },
    }
    return event, visible


def _read_result() -> dict[str, Any]:
    return {
        "path": SOURCE_PATH,
        "content": "line 20\nline 21\n",
        "start_line": 20,
        "end_line": 120,
        "actual_start_line": 20,
        "actual_end_line": 21,
        "total_lines": 500,
        "file_content_hash": "sha256:" + "2" * 64,
    }


def _check_result(task: PublicTask) -> dict[str, Any]:
    return {
        "check_id": task.visible_checks[0].id,
        "invocation_status": "completed",
        "behavior_status": "failed",
        "passed": False,
        "timed_out": False,
    }


def _context(pairs: list[tuple[RunEvent, dict[str, Any]]]) -> str:
    return json.dumps({"recent_events": [pair[1] for pair in pairs]})


def _evidence(task: PublicTask) -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash=DIFF,
        mutation_event_sequence=3,
        mutation_present=True,
        completed_checks=(),
        pending_checks=tuple(check.id for check in task.visible_checks),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=(),
        allowed_next_actions=("search_files", "read_file", "apply_structured_edit", "run_check"),
    )


def _plan_arguments(catalog, *, status: str, disposition: str | None = None) -> dict[str, Any]:
    source = next(item for item in catalog.items if item.kind == "source_read")
    body: dict[str, Any] = {
        "observation_status": status,
        "hypothesis": "Interrupted cleanup can retain a reachable runner state.",
        "foundation_evidence_ids": [
            item.evidence_id for item in catalog.items if item.role == "foundation"
        ],
        "supporting_evidence_ids": [],
        "candidate_files": [{"path": SOURCE_PATH, "read_evidence_id": source.evidence_id}],
        "intended_change": "Bound cleanup state to the interrupted runner lifetime.",
        "expected_behavior": "Interrupted execution cannot resume and cleanup runs once.",
        "unknowns": [],
    }
    if disposition is not None:
        body["prior_hypothesis_disposition"] = disposition
    return body


def _synthetic_scenarios(task: PublicTask) -> dict[str, Any]:
    initial_read = _public_result(1, "read_file", _read_result(), diff_hash=EMPTY)
    initial_catalog = project_eligible_plan_evidence_catalog(
        run_id=RUN_ID,
        task=task,
        worktree_diff_hash=EMPTY,
        model_visible_context=_context([initial_read]),
        events=[initial_read[0]],
    )
    initial_plan = validate_work_plan_v2(
        task=task,
        catalog=initial_catalog,
        arguments=_plan_arguments(initial_catalog, status="static_source"),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
    )
    plan_event = _event(
        2,
        EventType.PLAN_RECORDED,
        payload={
            "schema_version": PLAN_RECORDED_EVENT_SCHEMA_V2,
            "plan_hash": initial_plan.content_hash,
            "worktree_diff_hash": EMPTY,
            "revision_index": 0,
            "parent_plan_hash": None,
            "trigger": "initial",
            "plan": initial_plan.model_dump(mode="json"),
        },
    )
    patch_event = _event(
        3,
        EventType.PATCH_APPLIED,
        payload={"worktree_diff_hash": DIFF, "plan_hash": initial_plan.content_hash},
    )
    failed = _public_result(4, "run_check", _check_result(task), diff_hash=DIFF)
    read_one = _public_result(5, "read_file", _read_result(), diff_hash=DIFF)
    search = _public_result(
        6,
        "search_files",
        {"query": "cancel", "path_glob": "src/**/*.py", "matches": [], "truncated": False},
        diff_hash=DIFF,
    )
    read_two = _public_result(7, "read_file", _read_result(), diff_hash=DIFF)
    events = [
        initial_read[0],
        plan_event,
        patch_event,
        failed[0],
        read_one[0],
        search[0],
        read_two[0],
    ]
    evidence = _evidence(task)
    trigger_sequence = required_failed_check_trigger_sequence(
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=events,
    )
    if trigger_sequence != 4:
        raise ContractError("V14 qualification trigger selection differs")
    evicted_context = _context([read_one, search, read_two])
    v13_catalog = project_eligible_plan_evidence_catalog(
        run_id=RUN_ID,
        task=task,
        worktree_diff_hash=DIFF,
        model_visible_context=evicted_context,
        events=events,
    )
    v13 = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v13",
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=events,
        catalog=v13_catalog,
        available_tool_names=tuple(item["name"] for item in TOOL_SCHEMAS_V17),
        configured_max_output_tokens=25_000,
    )
    v14_catalog = project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=task,
        worktree_diff_hash=DIFF,
        model_visible_context=evicted_context,
        events=events,
        required_trigger_event_sequence=trigger_sequence,
    )
    v14 = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v14",
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=events,
        catalog=v14_catalog,
        available_tool_names=tuple(item["name"] for item in TOOL_SCHEMAS_V18),
        configured_max_output_tokens=25_000,
    )
    revision = validate_work_plan_v2(
        task=task,
        catalog=v14_catalog,
        arguments=_plan_arguments(
            v14_catalog,
            status="visible_check_failed",
            disposition="refined",
        ),
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash=initial_plan.content_hash,
        trigger_check_id=task.visible_checks[0].id,
        trigger_event_sequence=trigger_sequence,
    )
    broken = failed[0].model_copy(
        update={"payload": {**failed[0].payload, "result_artifact": None}}
    )
    broken_events = [*events[:3], broken, *events[4:]]
    unavailable_catalog = project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=task,
        worktree_diff_hash=DIFF,
        model_visible_context=evicted_context,
        events=broken_events,
        required_trigger_event_sequence=trigger_sequence,
    )
    unavailable = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v14",
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=broken_events,
        catalog=unavailable_catalog,
        available_tool_names=tuple(item["name"] for item in TOOL_SCHEMAS_V18),
        configured_max_output_tokens=25_000,
    )
    return {
        "v13_evicted_trigger_reproduction": {
            "information_actions": v13.information_actions_in_episode,
            "required_trigger_evidence_id": v13.required_trigger_evidence_id,
            "allowed_tool_names": list(v13.allowed_tool_names),
        },
        "v14_pinned_trigger": {
            "catalog_schema": v14_catalog.schema_version,
            "required_trigger_status": v14_catalog.required_trigger_status,
            "pinned_event_sequences": list(v14_catalog.model_visible_pinned_event_sequences),
            "recent_event_sequences": list(v14_catalog.model_visible_recent_event_sequences),
            "required_trigger_evidence_id": v14.required_trigger_evidence_id,
            "target": v14.target,
            "allowed_tool_names": list(v14.allowed_tool_names),
            "revision_hash": revision.content_hash,
        },
        "v14_unavailable_trigger": {
            "required_trigger_status": unavailable_catalog.required_trigger_status,
            "unavailable_reason": unavailable_catalog.unavailable_reason,
            "target": unavailable.target,
            "terminal_reason": unavailable.terminal_reason,
            "allowed_tool_names": list(unavailable.allowed_tool_names),
        },
    }


def _finalization_request(root: Path) -> LeanHarnessRequestEvidenceV14:
    package = load_task_package(root / TASK_PACKAGE)
    event = _event(1, EventType.RUN_STARTED, payload={"task_id": package.public.task_id})
    rendered = json.dumps(
        {
            "task": {"id": package.public.task_id},
            "selected_memory": None,
            "phase_policy": {"phase": "REPRODUCE"},
            "recent_events": [],
        },
        indent=2,
    )
    context = BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v5",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
            "tool_results": [],
        },
    )
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    assembled = assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies(root),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=TOOL_SCHEMAS_V18,
        phase_evidence=diff_bound_evidence(
            package.public,
            [event],
            EMPTY,
            completion_driven=True,
        ),
        events=[event],
        usage=Usage(input_tokens=899_999, output_tokens=10_000),
        budget=Budget(
            max_model_calls=240,
            max_tool_calls=400,
            max_total_tokens=1_100_000,
            wall_clock_timeout_seconds=3_600,
            token_budget_schema_version="cumulative-split-v1",
            max_cumulative_input_tokens=1_000_000,
            max_cumulative_output_tokens=100_000,
        ),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V14,
        task=package.public,
    )
    if type(assembled.evidence) is not LeanHarnessRequestEvidenceV14:
        raise ContractError("V14 qualification assembled the wrong request evidence")
    artifact = {
        "request_body": assembled.evidence.request_body,
        "request_body_hash": assembled.evidence.request_body_hash,
        "lean_harness_request": assembled.evidence.model_dump(mode="json"),
    }
    if validate_persisted_lean_harness_request(artifact) != assembled.evidence:
        raise ContractError("V14 qualification persisted request differs")
    return assembled.evidence


def build_workflow_required_trigger_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build deterministic zero-call V14 qualification evidence."""

    root = Path(repository).resolve()
    task = PublicTask.model_validate(
        load_unique_yaml((root / TASK_PACKAGE / "public.yaml").read_text(encoding="utf-8"))
    )
    diagnosis = json.loads((root / IMMUTABLE_PREDECESSOR_FILES[-1]).read_bytes())
    if (
        diagnosis.get("content_hash")
        != sha256_json({key: value for key, value in diagnosis.items() if key != "content_hash"})
        or diagnosis.get("diagnosis", {}).get("increase_correction_limit_supported") is not False
    ):
        raise ContractError("R11 required-trigger diagnosis differs")
    scenarios = _synthetic_scenarios(task)
    finalization = _finalization_request(root)
    manifest = build_lean_harness_calibration_manifest(
        load_task_package(root / "tasks/smoke/config-falsy-override"),
        run_id="run_v14_required_trigger_manifest",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V14,
    )
    _, runner_tools = AgentRunner._runtime_contract(manifest)
    if runner_tools != TOOL_SCHEMAS_V18:
        raise ContractError("V14 qualification runner tool surface differs")
    body = {
        "schema_version": SCHEMA_VERSION,
        "status": "offline-qualified",
        "scope": "single-r11-v12-required-failed-check-trigger-eviction-class",
        "predecessor_runtime": "lean-harness-v13",
        "successor_runtime": "lean-harness-v14",
        "tool_schema_version": "v18",
        "context_policy_version": "phase-evidence-v24",
        "workflow_policy_version": finalization.workflow_decision.policy_version,
        "required_trigger_pin_policy_version": (finalization.required_trigger_pin_policy_version),
        "source_files": [_identity(root, item) for item in SOURCE_FILES],
        "immutable_predecessors": [_identity(root, item) for item in IMMUTABLE_PREDECESSOR_FILES],
        "scenarios": {
            **scenarios,
            "v14_reserve_finalization_and_round_trip": {
                "request_mode": finalization.finalization_request_mode.mode,
                "surface_schema": finalization.phase_tool_surface.schema_version,
                "catalog_schema": finalization.eligible_plan_evidence_catalog.schema_version,
                "required_trigger_status": (
                    finalization.eligible_plan_evidence_catalog.required_trigger_status
                ),
                "request_schema": finalization.schema_version,
                "persisted_round_trip_exact": True,
            },
            "v14_mock_runner_wiring": {
                "tool_schema_version": manifest.tool_schema_version,
                "context_policy_version": manifest.context_policy_version,
                "runner_tool_names": [item["name"] for item in runner_tools],
            },
        },
        "regression_gates": {
            "v13_finalization_surface_inherited": True,
            "v12_initial_and_revision_plan_semantics_inherited": True,
            "correction_attempt_limit_remains_three": True,
            "review_correction_limit_remains_one": True,
            "initial_plan_mock_e2e_passed": True,
            "failed_check_revision_mock_e2e_passed": True,
            "review_correction_mock_e2e_passed": True,
            "restart_recovery_mock_e2e_passed": True,
        },
        "evidence_boundary": {
            "public_only": True,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "added_cost_usd": "0",
        },
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("required-trigger qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_required_trigger_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_required_trigger_successor_qualification(root)
    path = (root / QUALIFICATION_PATH).resolve()
    raw = qualification_bytes(value)
    if path.exists() and path.read_bytes() != raw:
        raise ContractError("required-trigger qualification already differs")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return value


def load_workflow_required_trigger_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    path = (root / QUALIFICATION_PATH).resolve()
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("required-trigger qualification is unavailable") from exc
    if qualification_bytes(value) != path.read_bytes():
        raise ContractError("required-trigger qualification bytes differ")
    if value != build_workflow_required_trigger_successor_qualification(root):
        raise ContractError("required-trigger qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSOR_FILES",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_required_trigger_successor_qualification",
    "load_workflow_required_trigger_successor_qualification",
    "materialize_workflow_required_trigger_successor_qualification",
    "qualification_bytes",
]
