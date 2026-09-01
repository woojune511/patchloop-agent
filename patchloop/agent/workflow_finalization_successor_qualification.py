"""Offline qualification for the reserve-safe V13 workflow projection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LEAN_FINALIZATION_WORKFLOW_SURFACE_POLICY_VERSION_V13,
    LEAN_RUNTIME_POLICY_VERSION_V12,
    LEAN_RUNTIME_POLICY_VERSION_V13,
    LeanHarnessRequestEvidenceV13,
    assemble_lean_harness_request,
    build_lean_harness_calibration_manifest,
    load_lean_harness_dependencies,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.phases import diff_bound_evidence
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V16, TOOL_SCHEMAS_V17
from patchloop.agent.workflow_successor_v2 import WorkflowToolSurfaceV2
from patchloop.contracts import Budget, EventType, MemoryCondition, RunEvent, Usage
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

SCHEMA_VERSION = "lean-workflow-finalization-successor-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/lean-harness-workflow-finalization-successor-public-qualification-20260825-v1.json"
)
TASK_PACKAGE = "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4"
RUN_ID = "run_workflow_finalization_successor_qualification"

SOURCE_FILES = (
    "patchloop/agent/workflow_finalization_successor_qualification.py",
    "patchloop/agent/workflow_successor_v2.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/contracts.py",
    "scripts/build_lean_harness_workflow_finalization_successor_qualification.py",
    "tests/test_workflow_finalization_successor.py",
    "tests/test_workflow_successor_v2_runner.py",
    "tests/test_workflow_finalization_successor_qualification.py",
)

IMMUTABLE_PREDECESSOR_FILES = (
    "experiments/lean-harness-workflow-successor-v2-public-qualification-20260825-v1.json",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-candidate-v17.json",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-candidate-v17-rehearsal-v14.json",
    "reports/rapid-development/rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-c64654b6bdba.jsonl",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-revision-ab-20260825-r11-workflow-diagnosis-v1.json",
)


def _identity(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ContractError(f"qualification input is unavailable: {relative}")
    raw = path.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "file_sha256": sha256_bytes(raw),
    }


def _context() -> BuiltContext:
    rendered = json.dumps(
        {
            "task": {"id": "anyio-interrupt-runner-cleanup"},
            "selected_memory": None,
            "phase_policy": {"phase": "REPRODUCE"},
            "recent_events": [],
        },
        indent=2,
    )
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence={
            "schema_version": "context-build-evidence-v5",
            "rendered_characters": len(rendered),
            "rendered_bytes": len(rendered.encode("utf-8")),
            "tool_results": [],
        },
    )


def _assemble(root: Path, *, runtime: str, schemas: list[dict[str, Any]]):
    package = load_task_package(root / TASK_PACKAGE)
    events = (
        RunEvent(
            event_id="evt_v13_qualification_start",
            run_id=RUN_ID,
            sequence=1,
            type=EventType.RUN_STARTED,
            timestamp=datetime(2026, 8, 25, tzinfo=UTC),
            actor="runner",
            payload={"task_id": package.public.task_id},
        ),
    )
    context = _context()
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    budget = Budget(
        max_model_calls=240,
        max_tool_calls=400,
        max_total_tokens=1_100_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
    )
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies(root),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=schemas,
        phase_evidence=diff_bound_evidence(
            package.public,
            events,
            sha256_text(""),
            completion_driven=True,
        ),
        events=events,
        usage=Usage(input_tokens=899_999, output_tokens=10_000),
        budget=budget,
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=runtime,
        task=package.public,
    )


def build_workflow_finalization_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    """Build deterministic zero-call evidence for the single R11 infrastructure fix."""

    root = Path(repository).resolve()
    try:
        _assemble(root, runtime=LEAN_RUNTIME_POLICY_VERSION_V12, schemas=TOOL_SCHEMAS_V16)
    except ValidationError as exc:
        v12_errors = exc.errors(include_url=False, include_context=False, include_input=False)
    else:
        raise ContractError("consumed V12 finalization mismatch did not reproduce")
    error_locations = tuple(".".join(str(item) for item in error["loc"]) for error in v12_errors)
    if "phase_tool_surface.mode" not in error_locations:
        raise ContractError("V12 finalization mismatch lacks the observed surface field")

    assembled = _assemble(root, runtime=LEAN_RUNTIME_POLICY_VERSION_V13, schemas=TOOL_SCHEMAS_V17)
    evidence = assembled.evidence
    if type(evidence) is not LeanHarnessRequestEvidenceV13:
        raise ContractError("V13 qualification assembled the wrong request evidence")
    if type(evidence.phase_tool_surface) is not WorkflowToolSurfaceV2:
        raise ContractError("V13 qualification lost the workflow tool surface")
    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    persisted = validate_persisted_lean_harness_request(artifact)
    if persisted != evidence:
        raise ContractError("V13 persisted-request round trip differs")

    package = load_task_package(root / "tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_v13_qualification_manifest",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V13,
    )
    _, runner_tools = AgentRunner._runtime_contract(manifest)
    if runner_tools != TOOL_SCHEMAS_V17:
        raise ContractError("V13 runner tool surface is not wired")

    scenarios = [
        {
            "scenario_id": "consumed-v12-finalization-schema-mismatch-reproduced",
            "observed": {
                "validation_error": True,
                "error_count": len(v12_errors),
                "phase_tool_surface_mode_rejected": True,
                "provider_dispatches": 0,
            },
        },
        {
            "scenario_id": "v13-workflow-surface-retained-through-reserve",
            "observed": {
                "request_mode": evidence.finalization_request_mode.mode,
                "surface_schema": evidence.phase_tool_surface.schema_version,
                "decision_hash": evidence.workflow_decision.content_hash,
                "surface_decision_hash": evidence.phase_tool_surface.decision_hash,
                "selected_tool_names": list(evidence.phase_tool_surface.selected_tool_names),
                "effective_max_output_tokens": evidence.effective_max_output_tokens,
                "workflow_effective_max_output_tokens": (
                    evidence.workflow_decision.effective_max_output_tokens
                ),
                "legacy_phase_surface_accepted": False,
            },
        },
        {
            "scenario_id": "v13-persisted-request-round-trip",
            "observed": {
                "schema_version": persisted.schema_version,
                "request_body_hash": persisted.request_body_hash,
                "content_hash": persisted.content_hash,
                "round_trip_exact": True,
            },
        },
        {
            "scenario_id": "v13-mock-manifest-runner-wiring",
            "observed": {
                "tool_schema_version": manifest.tool_schema_version,
                "context_policy_version": manifest.context_policy_version,
                "runner_tool_names": [item["name"] for item in runner_tools],
                "provider": manifest.model.provider,
            },
        },
    ]
    body = {
        "schema_version": SCHEMA_VERSION,
        "status": "offline-qualified",
        "scope": "single-r11-v12-finalization-request-projection-failure-class",
        "predecessor_runtime": "lean-harness-v12",
        "successor_runtime": "lean-harness-v13",
        "tool_schema_version": "v17",
        "context_policy_version": "phase-evidence-v23",
        "workflow_policy_version": evidence.workflow_decision.policy_version,
        "finalization_workflow_surface_policy_version": (
            LEAN_FINALIZATION_WORKFLOW_SURFACE_POLICY_VERSION_V13
        ),
        "source_files": [_identity(root, item) for item in SOURCE_FILES],
        "immutable_predecessors": [_identity(root, item) for item in IMMUTABLE_PREDECESSOR_FILES],
        "scenarios": scenarios,
        "regression_gates": {
            "v12_workflow_semantics_inherited": True,
            "initial_plan_mock_e2e_required": True,
            "failed_check_revision_mock_e2e_required": True,
            "review_correction_mock_e2e_required": True,
            "restart_recovery_mock_e2e_required": True,
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
        raise ContractError("workflow finalization qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_workflow_finalization_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_workflow_finalization_successor_qualification(root)
    path = (root / QUALIFICATION_PATH).resolve()
    if not path.is_relative_to(root):
        raise ContractError("workflow finalization qualification escapes repository")
    raw = qualification_bytes(value)
    if path.exists() and path.read_bytes() != raw:
        raise ContractError("workflow finalization qualification already differs")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return value


def load_workflow_finalization_successor_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    path = (root / QUALIFICATION_PATH).resolve()
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("workflow finalization qualification is unavailable") from exc
    if raw != qualification_bytes(value):
        raise ContractError("workflow finalization qualification bytes differ")
    if value != build_workflow_finalization_successor_qualification(root):
        raise ContractError("workflow finalization qualification source binding differs")
    return value


__all__ = [
    "IMMUTABLE_PREDECESSOR_FILES",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "build_workflow_finalization_successor_qualification",
    "load_workflow_finalization_successor_qualification",
    "materialize_workflow_finalization_successor_qualification",
    "qualification_bytes",
]
