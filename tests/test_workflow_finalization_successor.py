from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V12,
    LEAN_RUNTIME_POLICY_VERSION_V13,
    LEAN_RUNTIME_POLICY_VERSION_V14,
    LeanHarnessRequestEvidenceV13,
    LeanHarnessRequestEvidenceV14,
    assemble_lean_harness_request,
    build_lean_harness_calibration_manifest,
    load_lean_harness_dependencies,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.phases import diff_bound_evidence
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V16, TOOL_SCHEMAS_V17, TOOL_SCHEMAS_V18
from patchloop.agent.workflow_successor_v2 import WorkflowToolSurfaceV2
from patchloop.contracts import Budget, EventType, MemoryCondition, RunEvent, Usage
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_text

TASK_PACKAGE = "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4"
RUN_ID = "run_workflow_finalization_successor"


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


def _budget() -> Budget:
    return Budget(
        max_model_calls=240,
        max_tool_calls=400,
        max_total_tokens=1_100_000,
        wall_clock_timeout_seconds=3_600,
        token_budget_schema_version="cumulative-split-v1",
        max_cumulative_input_tokens=1_000_000,
        max_cumulative_output_tokens=100_000,
    )


def _assemble(runtime: str, schemas: list[dict]):
    package = load_task_package(TASK_PACKAGE)
    events = (
        RunEvent(
            event_id="evt_v13_start",
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
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
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
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=runtime,
        task=package.public,
    )


def test_consumed_v12_reproduces_finalization_surface_schema_mismatch() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _assemble(LEAN_RUNTIME_POLICY_VERSION_V12, TOOL_SCHEMAS_V16)

    message = str(exc_info.value)
    assert "LeanHarnessRequestEvidenceV12" in message
    assert "phase_tool_surface.mode" in message
    assert "Extra inputs are not permitted" in message


def test_v13_retains_the_workflow_surface_through_reserve_finalization() -> None:
    assembled = _assemble(LEAN_RUNTIME_POLICY_VERSION_V13, TOOL_SCHEMAS_V17)
    evidence = assembled.evidence

    assert type(evidence) is LeanHarnessRequestEvidenceV13
    assert evidence.finalization_request_mode.mode == "finalization"
    assert type(evidence.phase_tool_surface) is WorkflowToolSurfaceV2
    assert evidence.phase_tool_surface.decision_hash == evidence.workflow_decision.content_hash
    assert evidence.phase_tool_surface.selected_tool_names == (
        evidence.workflow_decision.allowed_tool_names
    )
    assert evidence.effective_max_output_tokens == (
        evidence.workflow_decision.effective_max_output_tokens
    )
    assert evidence.request_body["tools"] == list(evidence.phase_tool_surface.selected_tool_schemas)
    assert "mode" not in evidence.phase_tool_surface.model_dump(mode="json")

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v13_manifest_is_opt_in_and_runner_wired() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_v13_manifest",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V13,
    )

    assert manifest.tool_schema_version == "v17"
    assert manifest.context_policy_version == "phase-evidence-v23"
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V17


def test_v14_inherits_reserve_safe_surface_and_persisted_request_validation() -> None:
    assembled = _assemble(LEAN_RUNTIME_POLICY_VERSION_V14, TOOL_SCHEMAS_V18)
    evidence = assembled.evidence

    assert type(evidence) is LeanHarnessRequestEvidenceV14
    assert evidence.finalization_request_mode.mode == "finalization"
    assert type(evidence.phase_tool_surface) is WorkflowToolSurfaceV2
    assert evidence.eligible_plan_evidence_catalog.schema_version == (
        "eligible-plan-evidence-catalog-v2"
    )
    assert evidence.eligible_plan_evidence_catalog.required_trigger_status == "not_required"
    assert evidence.phase_tool_surface.decision_hash == evidence.workflow_decision.content_hash
    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v14_manifest_is_opt_in_and_runner_wired() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_v14_manifest",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V14,
    )

    assert manifest.tool_schema_version == "v18"
    assert manifest.context_policy_version == "phase-evidence-v24"
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V18
