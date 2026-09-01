from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V2,
    LEAN_RUNTIME_POLICY_VERSION_V3,
    LEAN_RUNTIME_POLICY_VERSION_V4,
    LEAN_RUNTIME_POLICY_VERSION_V5,
    LEAN_RUNTIME_POLICY_VERSION_V6,
    LEAN_RUNTIME_POLICY_VERSION_V7,
    LEAN_RUNTIME_POLICY_VERSION_V8,
    LeanHarnessRequestEvidence,
    LeanHarnessRequestEvidenceV2,
    LeanHarnessRequestEvidenceV3,
    LeanHarnessRequestEvidenceV4,
    LeanHarnessRequestEvidenceV5,
    LeanHarnessRequestEvidenceV6,
    LeanHarnessRequestEvidenceV7,
    LeanHarnessRequestEvidenceV8,
    assemble_lean_harness_request,
    build_lean_harness_calibration_manifest,
    load_lean_harness_dependencies,
    validate_persisted_lean_harness_request,
)
from patchloop.agent.model import MockModelAdapter, ModelTurn, RequestedTool
from patchloop.agent.phases import EvidenceState, diff_bound_evidence
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import (
    TOOL_SCHEMAS_V7,
    TOOL_SCHEMAS_V8,
    TOOL_SCHEMAS_V9,
    TOOL_SCHEMAS_V10,
    TOOL_SCHEMAS_V11,
    TOOL_SCHEMAS_V12,
)
from patchloop.contracts import (
    Budget,
    EventType,
    MemoryCondition,
    RunEvent,
    ToolCall,
    Usage,
)
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_json, sha256_text


def _context(*, selected_memory: str | None = None) -> BuiltContext:
    payload = {
        "task": {"id": "config-falsy-override"},
        "selected_memory": selected_memory,
        "phase_policy": {"phase": "REPRODUCE"},
        "recent_events": [],
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
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


def _role_distinct_event_context() -> BuiltContext:
    def descriptor(identity: str) -> dict[str, object]:
        return {
            "artifact_id": f"art_{identity}",
            "content_hash": sha256_text(identity),
            "media_type": "application/json; charset=utf-8",
            "size_bytes": len(identity),
            "path": f"objects/{identity}.json",
            "created_at": "2026-08-23T00:00:00Z",
        }

    edit_input = descriptor("structured-input")
    patch = descriptor("generated-patch")
    blocked_input = descriptor("blocked-input")
    blocked_result = descriptor("blocked-result")
    payload = json.loads(_context().rendered)
    payload["recent_events"] = [
        {
            "sequence": 227,
            "type": "ToolCalled",
            "actor": "agent",
            "payload": {
                "tool": "apply_structured_edit",
                "input_artifact": edit_input,
                "patch_artifact": patch,
                "artifact_id": patch["artifact_id"],
                "artifact_path": patch["path"],
            },
        },
        {
            "sequence": 229,
            "type": "ToolSucceeded",
            "actor": "tool-gateway",
            "payload": {
                "tool": "apply_structured_edit",
                "status": "succeeded",
                "result_artifact": None,
                "artifact_id": "art_mutation-result",
                "artifact_path": "objects/mutation-result.json",
            },
        },
        {
            "sequence": 231,
            "type": "ToolAdmissionBlocked",
            "actor": "tool-admission-policy",
            "payload": {
                "tool": "run_check",
                "status": "rejected",
                "input_artifact": blocked_input,
                "result_artifact": blocked_result,
                "artifact_id": blocked_result["artifact_id"],
                "artifact_path": blocked_result["path"],
            },
        },
    ]
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
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


def _phase() -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash=sha256_text(""),
        mutation_event_sequence=None,
        mutation_present=False,
        completed_checks=(),
        pending_checks=("public-check",),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=(
            "successful_mutation_current_diff",
            "visible_checks_current_diff",
            "final_diff_review_current_diff",
            "review_phase",
        ),
        allowed_next_actions=("apply_patch", "run_check", "read_file", "search_files"),
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


def _event(sequence: int, event_type: EventType, payload: dict[str, object]) -> RunEvent:
    return RunEvent(
        event_id=f"evt_{sequence}",
        run_id="run_lean_request",
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 16, tzinfo=UTC),
        actor="test",
        payload=payload,
    )


def _assemble(
    *,
    usage: Usage | None = None,
    events: tuple[RunEvent, ...] = (),
):
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=_context(),
        normalized_no_memory_context=_context(),
        base_tool_schemas=TOOL_SCHEMAS_V7,
        phase_evidence=_phase(),
        events=events,
        usage=usage or Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
    )


def _completion_phase() -> EvidenceState:
    return EvidenceState(
        worktree_diff_hash="sha256:current",
        mutation_event_sequence=1,
        mutation_present=True,
        completed_checks=(),
        pending_checks=("public-check",),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=None,
        review_presented_to_model=False,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=(
            "visible_checks_current_diff",
            "final_diff_review_current_diff",
        ),
        allowed_next_actions=("run_check",),
    )


def _assemble_v2(
    *,
    usage: Usage | None = None,
    phase_evidence: EvidenceState | None = None,
):
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=_context(),
        normalized_no_memory_context=_context(),
        base_tool_schemas=TOOL_SCHEMAS_V8,
        phase_evidence=phase_evidence or _completion_phase(),
        events=(),
        usage=usage or Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V2,
    )


def _assemble_v3(
    *,
    usage: Usage | None = None,
    phase_evidence: EvidenceState | None = None,
):
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=_context(),
        normalized_no_memory_context=_context(),
        base_tool_schemas=TOOL_SCHEMAS_V9,
        phase_evidence=phase_evidence or _completion_phase(),
        events=(),
        usage=usage or Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V3,
    )


def _assemble_v4(
    *,
    usage: Usage | None = None,
    phase_evidence: EvidenceState | None = None,
):
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=_context(),
        normalized_no_memory_context=_context(),
        base_tool_schemas=TOOL_SCHEMAS_V9,
        phase_evidence=phase_evidence or _completion_phase(),
        events=(),
        usage=usage or Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V4,
    )


def _assemble_v5(
    *,
    usage: Usage | None = None,
    phase_evidence: EvidenceState | None = None,
    events: tuple[RunEvent, ...] = (),
    built_context: BuiltContext | None = None,
):
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=built_context or _context(),
        normalized_no_memory_context=built_context or _context(),
        base_tool_schemas=TOOL_SCHEMAS_V10,
        phase_evidence=phase_evidence or _completion_phase(),
        events=events,
        usage=usage or Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V5,
    )


def _assemble_v6(
    *,
    built_context: BuiltContext | None = None,
    phase_evidence: EvidenceState | None = None,
):
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    context = built_context or _context()
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=TOOL_SCHEMAS_V10,
        phase_evidence=phase_evidence or _completion_phase(),
        events=(),
        usage=Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V6,
    )


def _assemble_v7(
    *,
    built_context: BuiltContext | None = None,
    phase_evidence: EvidenceState | None = None,
    events: tuple[RunEvent, ...] = (),
    usage: Usage | None = None,
):
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    context = built_context or _context()
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=TOOL_SCHEMAS_V11,
        phase_evidence=phase_evidence or _completion_phase(),
        events=events,
        usage=usage or Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V7,
    )


def _assemble_v8(
    *,
    events: tuple[RunEvent, ...],
    diff_hash: str,
    built_context: BuiltContext | None = None,
):
    package = load_task_package("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4")
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    context = built_context or _context()
    phase_evidence = diff_bound_evidence(
        package.public,
        events,
        diff_hash,
        completion_driven=True,
    )
    return assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=TOOL_SCHEMAS_V12,
        phase_evidence=phase_evidence,
        events=events,
        usage=Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V8,
        task=package.public,
    )


def test_exact_v7_manifest_is_opt_in_and_legacy_tool_call_still_parses() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest",
        condition=MemoryCondition.NO_MEMORY,
    )

    assert manifest.tool_schema_version == "v7"
    assert manifest.context_policy_version == "phase-evidence-v12"
    assert manifest.model.model_id == "patchloop-public-calibration-mock-v1"
    assert manifest.experiment is None
    assert (
        ToolCall(
            tool="read_file",
            tool_schema_version="v1",
            action_id="legacy",
            run_id="run_legacy",
            input={},
            input_hash=sha256_text("legacy"),
        ).tool_schema_version
        == "v1"
    )


def test_v8_v13_successor_is_opt_in_and_binds_completion_contract() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_v13",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V2,
    )
    assembled = _assemble_v2(usage=Usage(input_tokens=890_000, output_tokens=60_000))
    initial_finalization = _assemble_v2(
        usage=Usage(input_tokens=890_000, output_tokens=60_000),
        phase_evidence=_phase(),
    )
    evidence = assembled.evidence

    assert manifest.tool_schema_version == "v8"
    assert manifest.context_policy_version == "phase-evidence-v13"
    assert isinstance(evidence, LeanHarnessRequestEvidenceV2)
    assert evidence.runtime_policy_version == "lean-harness-v2"
    assert evidence.completion_policy_version == ("completion-driven-current-diff-v1")
    assert evidence.patch_normalization_policy_version == ("safe-raw-diff-normalization-v1")
    assert evidence.finalization_request_mode.mode == "finalization"
    assert evidence.phase_tool_surface.selected_tool_names == ("run_check",)
    assert initial_finalization.evidence.phase_tool_surface.completion_target == ("mutation")
    assert initial_finalization.evidence.phase_tool_surface.selected_tool_names == ("apply_patch",)
    assert (
        ToolCall(
            tool="run_check",
            tool_schema_version="v8",
            action_id="successor",
            run_id="run_successor",
            input={"check_id": "public-check"},
            input_hash=sha256_text("successor"),
        ).tool_schema_version
        == "v8"
    )

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v9_v13_search_glob_successor_binds_runtime_and_request_evidence() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_v13_search_glob_v3",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V3,
    )
    assembled = _assemble_v3(usage=Usage(input_tokens=890_000, output_tokens=60_000))
    evidence = assembled.evidence

    assert manifest.tool_schema_version == "v9"
    assert manifest.context_policy_version == "phase-evidence-v13"
    assert isinstance(evidence, LeanHarnessRequestEvidenceV3)
    assert evidence.runtime_policy_version == "lean-harness-v3"
    assert evidence.completion_policy_version == "completion-driven-current-diff-v1"
    assert evidence.patch_normalization_policy_version == ("safe-raw-diff-normalization-v1")
    assert evidence.search_glob_policy_version == ("recursive-file-glob-normalization-v1")
    assert evidence.finalization_request_mode.mode == "finalization"
    assert evidence.phase_tool_surface.selected_tool_names == ("run_check",)
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V9
    assert (
        ToolCall(
            tool="search_files",
            tool_schema_version="v9",
            action_id="search-glob-successor",
            run_id="run_search_glob_successor",
            input={"query": "needle", "path_glob": "src/**"},
            input_hash=sha256_text("search-glob-successor"),
        ).tool_schema_version
        == "v9"
    )

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v9_v14_successor_prefers_check_and_uses_split_bounded_ceiling() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_v14_finalization",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V4,
    )
    both_allowed = replace(
        _completion_phase(),
        allowed_next_actions=(
            "run_check",
            "apply_patch",
            "read_file",
            "search_files",
        ),
    )
    assembled = _assemble_v4(
        usage=Usage(input_tokens=890_000, output_tokens=60_000),
        phase_evidence=both_allowed,
    )
    evidence = assembled.evidence

    assert manifest.tool_schema_version == "v9"
    assert manifest.context_policy_version == "phase-evidence-v14"
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V9
    assert isinstance(evidence, LeanHarnessRequestEvidenceV4)
    assert evidence.runtime_policy_version == "lean-harness-v4"
    assert evidence.completion_policy_version == "completion-driven-current-diff-v2"
    assert evidence.finalization_allowance_policy_version == ("configured-ceiling-split-bounded-v1")
    assert evidence.finalization_request_mode.mode == "finalization"
    assert evidence.phase_tool_surface.completion_target == "visible-check"
    assert evidence.phase_tool_surface.selected_tool_names == ("run_check",)
    assert evidence.phase_tool_surface.registered_check_preferred is True
    assert evidence.phase_tool_surface.recheck_after_mutation_required is False
    assert evidence.effective_max_output_tokens == 25_000
    assert evidence.provider_authority_granted is False

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v14_failed_check_requires_correction_then_recheck() -> None:
    failed_check = replace(
        _completion_phase(),
        latest_check_sequence=2,
        allowed_next_actions=("apply_patch", "read_file", "search_files"),
    )
    correction = _assemble_v4(
        usage=Usage(input_tokens=890_000, output_tokens=60_000),
        phase_evidence=failed_check,
    ).evidence.phase_tool_surface
    recheck = _assemble_v4(
        usage=Usage(input_tokens=890_000, output_tokens=60_000),
        phase_evidence=_completion_phase(),
    ).evidence.phase_tool_surface

    assert correction.completion_target == "corrective-mutation"
    assert correction.selected_tool_names == ("apply_patch",)
    assert correction.recheck_after_mutation_required is True
    assert recheck.completion_target == "visible-check"
    assert recheck.selected_tool_names == ("run_check",)
    assert recheck.recheck_after_mutation_required is False


def test_v14_finalization_ceiling_is_reduced_only_by_split_budget() -> None:
    full = _assemble_v4(usage=Usage(input_tokens=890_000, output_tokens=60_000)).evidence
    reduced = _assemble_v4(usage=Usage(input_tokens=890_000, output_tokens=90_000)).evidence

    assert full.effective_max_output_tokens == 25_000
    assert full.split_allowance.decision == "admit_full"
    assert reduced.effective_max_output_tokens == 10_000
    assert reduced.split_allowance.decision == "admit_reduced"
    assert reduced.split_allowance.binding_dimension == "output_tokens"


def test_v15_successor_binds_all_three_mechanical_friction_policies() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_v15_mechanical",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V5,
    )
    evidence = _assemble_v5(usage=Usage(input_tokens=890_000, output_tokens=60_000)).evidence

    assert manifest.tool_schema_version == "v10"
    assert manifest.context_policy_version == "phase-evidence-v15"
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V10
    assert isinstance(evidence, LeanHarnessRequestEvidenceV5)
    assert evidence.structured_edit_policy_version == ("gateway-fresh-preimage-unique-text-v1")
    assert evidence.check_outcome_policy_version == "invocation-vs-behavior-v1"
    assert evidence.incomplete_recovery_policy_version == (
        "reasoning-only-single-retry-split-reserved-v1"
    )
    assert evidence.incomplete_recovery.mode == "primary-reserved"
    assert evidence.incomplete_recovery.reserved_retry_output_tokens == 2_048
    assert evidence.phase_tool_surface.selected_tool_names == ("run_check",)
    assert "response_recovery" in json.loads(evidence.request_body["context"])

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v16_successor_builds_next_request_after_production_descriptor_composition() -> None:
    source = _role_distinct_event_context()
    with pytest.raises(ValueError, match="artifact binding differs"):
        _assemble_v5(built_context=source)

    evidence = _assemble_v6(built_context=source).evidence
    context = json.loads(evidence.request_body["context"])

    assert isinstance(evidence, LeanHarnessRequestEvidenceV6)
    assert evidence.tool_schema_version == "v10"
    assert evidence.context_policy_version == "phase-evidence-v16"
    assert evidence.event_descriptor_role_policy_version == ("typed-distinct-input-role-v1")
    assert evidence.context_compaction.preserved_distinct_descriptor_count == 2
    assert "input_artifact" in context["recent_events"][0]["payload"]
    assert "input_artifact" in context["recent_events"][2]["payload"]
    assert "result_artifact" not in context["recent_events"][2]["payload"]
    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v16_manifest_is_opt_in_and_reuses_the_v10_tool_surface() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_v16_descriptor_roles",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V6,
    )

    assert manifest.tool_schema_version == "v10"
    assert manifest.context_policy_version == "phase-evidence-v16"
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V10


def test_v17_enters_completion_during_exploration_after_mutation() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_v17_completion",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V7,
    )
    evidence = _assemble_v7().evidence

    assert manifest.tool_schema_version == "v11"
    assert manifest.context_policy_version == "phase-evidence-v17"
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V11
    assert isinstance(evidence, LeanHarnessRequestEvidenceV7)
    assert evidence.finalization_request_mode.mode == "exploration"
    assert evidence.phase_tool_surface.state_driven_after_mutation is True
    assert evidence.phase_tool_surface.completion_lane_active is True
    assert evidence.phase_tool_surface.completion_target == "visible-check"
    assert evidence.phase_tool_surface.selected_tool_names == ("run_check",)
    assert evidence.completion_response_recovery.mode == "primary-reserved"
    assert evidence.completion_response_recovery.reserved_retry_output_tokens == 2_048
    assert evidence.effective_max_output_tokens == 22_952
    recovery_context = json.loads(evidence.request_body["context"])["response_recovery"]
    assert recovery_context["completion_target"] == "visible-check"
    assert recovery_context["available_tool_names"] == ["run_check"]

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_v17_state_sequence_is_correction_recheck_diff_then_submission() -> None:
    failed_check = replace(
        _completion_phase(),
        latest_check_sequence=2,
        allowed_next_actions=("apply_patch", "read_file", "search_files"),
    )
    checked = replace(
        _completion_phase(),
        completed_checks=("public-check",),
        pending_checks=(),
        current_diff_check_event_sequences=(2,),
        latest_check_sequence=2,
        missing_evidence=("final_diff_review_current_diff",),
        allowed_next_actions=("get_diff",),
    )
    reviewed = replace(
        checked,
        review_event_sequence=3,
        review_presented_to_model=True,
        submission_ready=True,
        missing_evidence=(),
        allowed_next_actions=("finish_task",),
    )

    correction = _assemble_v7(phase_evidence=failed_check).evidence.phase_tool_surface
    recheck = _assemble_v7().evidence.phase_tool_surface
    diff = _assemble_v7(phase_evidence=checked).evidence.phase_tool_surface
    submission = _assemble_v7(phase_evidence=reviewed).evidence.phase_tool_surface

    assert (correction.completion_target, correction.selected_tool_names) == (
        "corrective-mutation",
        ("apply_patch",),
    )
    assert (recheck.completion_target, recheck.selected_tool_names) == (
        "visible-check",
        ("run_check",),
    )
    assert (diff.completion_target, diff.selected_tool_names) == (
        "diff-review",
        ("get_diff",),
    )
    assert (submission.completion_target, submission.selected_tool_names) == (
        "submission",
        ("finish_task",),
    )


def test_v17_actionless_primary_rebuilds_one_action_only_retry() -> None:
    actionless = _event(
        1,
        EventType.MODEL_CALLED,
        {
            "response_error_code": None,
            "response_text_present": True,
            "response_tool_call_count": 0,
            "lean_response_done": False,
            "lean_completion_recovery_mode": "primary-reserved",
            "lean_reserved_completion_retry_output_tokens": 2_048,
        },
    )
    evidence = _assemble_v7(
        events=(actionless,),
        usage=Usage(input_tokens=5_000, output_tokens=1_000, model_calls=1),
    ).evidence

    assert evidence.completion_response_recovery.mode == "retry-actionless"
    assert evidence.completion_response_recovery.reasoning_effort == "low"
    assert evidence.effective_max_output_tokens == 2_048
    recovery_context = json.loads(evidence.request_body["context"])["response_recovery"]
    assert recovery_context["source_response_kind"] == "actionless"
    assert "exactly one" in recovery_context["instruction"]


def test_v17_pre_mutation_exploration_does_not_reserve_a_retry() -> None:
    evidence = _assemble_v7(phase_evidence=_phase()).evidence

    assert evidence.phase_tool_surface.completion_lane_active is False
    assert evidence.phase_tool_surface.completion_target == "phase-policy"
    assert evidence.completion_response_recovery.mode == "not-applicable"
    assert evidence.effective_max_output_tokens == 25_000


def test_v18_binds_one_targeted_check_and_small_request_ceiling() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_v18_ordered_completion",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V8,
    )
    diff_hash = sha256_text("v18-current-diff")
    events = (
        _event(
            1,
            EventType.PATCH_APPLIED,
            {"tool": "apply_patch", "worktree_diff_hash": diff_hash},
        ),
    )
    assembled = _assemble_v8(events=events, diff_hash=diff_hash)
    evidence = assembled.evidence

    assert manifest.tool_schema_version == "v12"
    assert manifest.context_policy_version == "phase-evidence-v18"
    assert AgentRunner._runtime_contract(manifest)[1] == TOOL_SCHEMAS_V12
    assert isinstance(evidence, LeanHarnessRequestEvidenceV8)
    assert evidence.completion_loop_decision.target == "visible-check"
    assert evidence.phase_tool_surface.selected_tool_names == ("run_check",)
    check_id = evidence.phase_tool_surface.tool_schemas[0]["parameters"]["properties"][
        "check_id"
    ]
    assert check_id["enum"] == ["public-interrupt-runner-lifecycle"]
    assert evidence.effective_max_output_tokens == 2_048
    assert evidence.request_body["parallel_tool_calls"] is False
    assert json.loads(evidence.request_body["context"])["completion_loop"]["target"] == (
        "visible-check"
    )
    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence
    assert (
        ToolCall(
            tool="run_check",
            tool_schema_version="v12",
            action_id="ordered-check",
            run_id="run_ordered_check",
            input={"check_id": "public-interrupt-runner-lifecycle"},
            input_hash=sha256_text("ordered-check"),
        ).tool_schema_version
        == "v12"
    )


def test_v18_failed_check_requires_read_before_structured_correction() -> None:
    diff_hash = sha256_text("v18-failed-diff")
    mutation = _event(
        1,
        EventType.PATCH_APPLIED,
        {"tool": "apply_patch", "worktree_diff_hash": diff_hash},
    )
    failed = _event(
        2,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "run_check",
            "check_id": "public-interrupt-runner-lifecycle",
            "passed": False,
            "worktree_diff_hash": diff_hash,
        },
    )
    current_read = _event(
        3,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "read_file",
            "path": "src/anyio/pytest_plugin.py",
            "worktree_diff_hash": diff_hash,
        },
    )

    inspection = _assemble_v8(
        events=(mutation, failed),
        diff_hash=diff_hash,
    ).evidence
    correction = _assemble_v8(
        events=(mutation, failed, current_read),
        diff_hash=diff_hash,
    ).evidence

    assert inspection.completion_loop_decision.target == "correction-inspection"
    assert inspection.phase_tool_surface.selected_tool_names == ("read_file",)
    assert inspection.effective_max_output_tokens == 4_096
    assert correction.completion_loop_decision.target == "corrective-mutation"
    assert correction.phase_tool_surface.selected_tool_names == (
        "apply_structured_edit",
    )
    assert correction.effective_max_output_tokens == 8_192
    assert correction.completion_loop_decision.latest_correction_read_sequence == 3


def test_v15_structured_fallback_omits_model_hashes_and_byte_offsets() -> None:
    events = (
        _event(1, EventType.TOOL_FAILED, {"tool": "apply_patch"}),
        _event(2, EventType.TOOL_FAILED, {"tool": "apply_patch"}),
    )
    evidence = _assemble_v5(events=events, phase_evidence=_phase()).evidence
    schema = next(
        item
        for item in evidence.phase_tool_surface.selected_tool_schemas
        if item["name"] == "apply_structured_edit"
    )
    file_properties = schema["parameters"]["properties"]["files"]["items"]["properties"]
    replacement_properties = file_properties["replacements"]["items"]["properties"]

    assert "apply_structured_edit" in (evidence.phase_tool_surface.selected_tool_names)
    assert "apply_patch" not in evidence.phase_tool_surface.selected_tool_names
    assert schema["parameters"]["properties"]["schema_version"]["enum"] == [
        "structured-edit-arguments-v2"
    ]
    assert "preimage_file_sha256" not in file_properties
    assert "start_byte" not in replacement_properties
    assert "end_byte" not in replacement_properties


def test_v15_reasoning_only_incomplete_rebuilds_one_low_effort_retry() -> None:
    primary = _assemble_v5(usage=Usage(input_tokens=890_000, output_tokens=60_000)).evidence
    incomplete = _event(
        1,
        EventType.MODEL_CALLED,
        {
            "response_error_code": "incomplete_response",
            "response_incomplete_reason": "max_output_tokens",
            "output_tokens": 25_000,
            "reasoning_output_tokens": 25_000,
            "lean_incomplete_recovery_mode": "primary-reserved",
            "lean_reserved_retry_output_tokens": 2_048,
            "response_text_present": False,
            "response_tool_call_count": 0,
        },
    )
    retry = _assemble_v5(
        usage=Usage(
            input_tokens=895_000,
            output_tokens=85_000,
            model_calls=1,
        ),
        events=(incomplete,),
    ).evidence

    assert primary.incomplete_recovery.mode == "primary-reserved"
    assert retry.incomplete_recovery.mode == "retry"
    assert retry.effective_max_output_tokens == 2_048
    assert retry.incomplete_recovery.reasoning_effort == "low"
    assert retry.incomplete_recovery.retry_available_after_response is False
    recovery_context = json.loads(retry.request_body["context"])["response_recovery"]
    assert recovery_context["source_event_sequence"] == 1
    assert "Emit exactly one available tool call" in recovery_context["instruction"]


def test_runtime_manifest_pair_and_budget_drift_fail_closed() -> None:
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_manifest_drift",
        condition=MemoryCondition.STRUCTURED,
    )
    body = manifest.model_dump(mode="python")
    body["context_policy_version"] = "phase-evidence-v5"
    with pytest.raises(ValueError, match="Lean Harness"):
        type(manifest).model_validate(body)

    body = manifest.model_dump(mode="python")
    body["model"]["temperature"] = 0.0
    body["budget"]["max_cumulative_output_tokens"] = 100_001
    with pytest.raises(ValueError, match="Lean Harness"):
        type(manifest).model_validate(body)


def test_request_is_compacted_phase_filtered_counted_and_persistable() -> None:
    assembled = _assemble()
    evidence = assembled.evidence

    assert evidence.runtime_policy_version == "lean-harness-v1"
    assert evidence.context_policy_version == "phase-evidence-v12"
    assert evidence.finalization_request_mode.mode == "exploration"
    assert evidence.requested_input_tokens == len(
        json.dumps(
            evidence.request_body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )
    assert evidence.effective_max_output_tokens == 25_000
    assert evidence.request_body["context"] == assembled.context
    assert "finish_task" not in evidence.phase_tool_surface.selected_tool_names
    assert evidence.provider_authority_granted is False

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": evidence.request_body_hash,
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == evidence


def test_live_request_uses_exact_provider_body_count_and_filtered_tools() -> None:
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    counted_bodies: list[dict[str, object]] = []

    def build_provider_body(
        context: str,
        tools: tuple[dict[str, object], ...],
        max_output_tokens: int,
    ) -> dict[str, object]:
        return {
            "model": "gpt-5.4-mini-2026-03-17",
            "input": [
                {"role": "system", "content": "public live prompt"},
                {"role": "user", "content": context},
            ],
            "tools": list(tools),
            "store": False,
            "reasoning": {"effort": "medium"},
            "service_tier": "default",
            "max_output_tokens": max_output_tokens,
            "truncation": "disabled",
        }

    def count_provider_body(body: dict[str, object]) -> int:
        counted_bodies.append(body)
        return 321

    assembled = assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies("."),
        built_context=_context(),
        normalized_no_memory_context=_context(),
        base_tool_schemas=TOOL_SCHEMAS_V7,
        phase_evidence=_phase(),
        events=(),
        usage=Usage(),
        budget=_budget(),
        model_id="gpt-5.4-mini-2026-03-17",
        system_prompt="public live prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        provider_request_builder=build_provider_body,
        provider_input_token_counter=count_provider_body,
    )

    assert assembled.evidence.input_count_method == "openai-input-token-count-v1"
    assert assembled.evidence.requested_input_tokens == 321
    assert assembled.request_body["input"][1]["content"] == assembled.context
    assert assembled.request_body["tools"] == list(assembled.tool_schemas)
    assert len(counted_bodies) == 1
    artifact = {
        "request_body": assembled.evidence.request_body,
        "request_body_hash": assembled.evidence.request_body_hash,
        "lean_harness_request": assembled.evidence.model_dump(mode="json"),
    }
    assert validate_persisted_lean_harness_request(artifact) == assembled.evidence


def test_finalization_rebuild_filters_search_and_uses_reduced_output_allowance() -> None:
    assembled = _assemble(
        usage=Usage(input_tokens=890_000, output_tokens=60_000),
    )
    evidence = assembled.evidence

    assert evidence.finalization_request_mode.mode == "finalization"
    assert evidence.effective_max_output_tokens == 5_000
    assert "search_files" not in evidence.phase_tool_surface.selected_tool_names
    assert set(evidence.phase_tool_surface.selected_tool_names) <= {
        "read_file",
        "apply_patch",
        "run_check",
    }


def test_two_patch_rejections_replace_raw_patch_with_structured_edit() -> None:
    events = (
        _event(1, EventType.TOOL_FAILED, {"tool": "apply_patch"}),
        _event(2, EventType.TOOL_FAILED, {"tool": "apply_patch"}),
    )
    evidence = _assemble(events=events).evidence

    assert evidence.saturation_recovery.structured_edit_required is True
    assert "apply_patch" not in evidence.phase_tool_surface.selected_tool_names
    assert "apply_structured_edit" in evidence.phase_tool_surface.selected_tool_names
    assert (
        evidence.phase_tool_surface.finalization_capability_projection["apply_structured_edit"]
        == "apply_patch"
    )


def test_rehashed_request_or_authority_drift_is_rejected() -> None:
    evidence = _assemble().evidence
    body = evidence.model_dump(mode="python")
    body["request_body"]["max_output_tokens"] = 24_999
    body["request_body_hash"] = sha256_text(
        json.dumps(
            body["request_body"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )
    body["content_hash"] = sha256_json(
        {key: value for key, value in body.items() if key != "content_hash"}
    )
    with pytest.raises(ValueError, match="output allowance"):
        LeanHarnessRequestEvidence.model_validate(body)

    artifact = {
        "request_body": evidence.request_body,
        "request_body_hash": sha256_text("wrong"),
        "lean_harness_request": evidence.model_dump(mode="json"),
    }
    with pytest.raises(ContractError, match="persisted request hash"):
        validate_persisted_lean_harness_request(artifact)


def test_exhausted_split_budget_blocks_before_request_evidence() -> None:
    with pytest.raises(ContractError, match="reserve is exhausted"):
        _assemble(usage=Usage(input_tokens=1_000_000, output_tokens=99_999))


def test_legacy_runtime_source_files_are_not_rewritten() -> None:
    paths = (
        Path("patchloop/agent/context.py"),
        Path("patchloop/agent/model.py"),
    )
    assert all(path.is_file() for path in paths)


def test_public_mock_smoke_persists_every_v12_request_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v12_public_smoke",
        condition=MemoryCondition.NO_MEMORY,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    context_events = [event for event in events if event.type == EventType.CONTEXT_BUILT]
    model_events = [event for event in events if event.type == EventType.MODEL_CALLED]

    assert result["scope_compliant_success"] is True
    assert len(context_events) == len(model_events) == 5
    for event in context_events:
        artifact = json.loads(Path(str(event.payload["artifact_path"])).read_text(encoding="utf-8"))
        evidence = validate_persisted_lean_harness_request(artifact)
        assert evidence.request_evidence_persisted_before_dispatch is True
        assert evidence.tool_schema_version == "v7"
        assert evidence.context_policy_version == "phase-evidence-v12"
        assert evidence.provider_authority_granted is False


def test_public_mock_v13_completes_check_review_and_submission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v13_public_smoke",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V2,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    context_events = [event for event in events if event.type == EventType.CONTEXT_BUILT]
    selected_surfaces: list[tuple[str, ...]] = []
    for event in context_events:
        artifact = json.loads(Path(str(event.payload["artifact_path"])).read_text(encoding="utf-8"))
        evidence = validate_persisted_lean_harness_request(artifact)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV2)
        selected_surfaces.append(evidence.phase_tool_surface.selected_tool_names)

    assert result["scope_compliant_success"] is True
    assert ("run_check",) in selected_surfaces
    assert ("get_diff",) in selected_surfaces
    assert ("finish_task",) in selected_surfaces
    assert (
        selected_surfaces.index(("run_check",))
        < selected_surfaces.index(("get_diff",))
        < selected_surfaces.index(("finish_task",))
    )


def test_public_mock_v9_persists_v3_evidence_before_every_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v9_public_smoke",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V3,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    context_events = [event for event in events if event.type == EventType.CONTEXT_BUILT]
    selected_surfaces: list[tuple[str, ...]] = []
    for event in context_events:
        artifact = json.loads(Path(str(event.payload["artifact_path"])).read_text(encoding="utf-8"))
        evidence = validate_persisted_lean_harness_request(artifact)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV3)
        assert evidence.tool_schema_version == "v9"
        assert evidence.search_glob_policy_version == ("recursive-file-glob-normalization-v1")
        selected_surfaces.append(evidence.phase_tool_surface.selected_tool_names)

    assert result["scope_compliant_success"] is True
    assert ("run_check",) in selected_surfaces
    assert ("get_diff",) in selected_surfaces
    assert ("finish_task",) in selected_surfaces


def test_public_mock_v14_persists_v4_evidence_and_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v14_public_smoke",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V4,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    context_events = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.CONTEXT_BUILT
    ]
    selected_surfaces: list[tuple[str, ...]] = []
    for event in context_events:
        artifact = json.loads(Path(str(event.payload["artifact_path"])).read_text(encoding="utf-8"))
        evidence = validate_persisted_lean_harness_request(artifact)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV4)
        assert evidence.tool_schema_version == "v9"
        assert evidence.context_policy_version == "phase-evidence-v14"
        assert evidence.finalization_allowance_policy_version == (
            "configured-ceiling-split-bounded-v1"
        )
        selected_surfaces.append(evidence.phase_tool_surface.selected_tool_names)

    assert result["scope_compliant_success"] is True
    assert ("run_check",) in selected_surfaces
    assert ("get_diff",) in selected_surfaces
    assert ("finish_task",) in selected_surfaces


def test_public_mock_v15_persists_mechanical_successor_and_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v15_public_smoke",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V5,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    context_events = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.CONTEXT_BUILT
    ]
    selected_surfaces: list[tuple[str, ...]] = []
    for event in context_events:
        artifact = json.loads(Path(str(event.payload["artifact_path"])).read_text(encoding="utf-8"))
        evidence = validate_persisted_lean_harness_request(artifact)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV5)
        assert evidence.tool_schema_version == "v10"
        assert evidence.context_policy_version == "phase-evidence-v15"
        assert evidence.incomplete_recovery.provider_calls_authorized is False
        selected_surfaces.append(evidence.phase_tool_surface.selected_tool_names)

    assert result["scope_compliant_success"] is True
    assert ("run_check",) in selected_surfaces
    assert ("get_diff",) in selected_surfaces
    assert ("finish_task",) in selected_surfaces


def test_public_mock_v16_persists_role_aware_successor_and_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v16_public_smoke",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V6,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    context_events = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.CONTEXT_BUILT
    ]
    for event in context_events:
        artifact = json.loads(Path(str(event.payload["artifact_path"])).read_text(encoding="utf-8"))
        evidence = validate_persisted_lean_harness_request(artifact)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV6)
        assert evidence.context_policy_version == "phase-evidence-v16"
        assert evidence.context_compaction.schema_version == (
            "lean-harness-context-event-compaction-evidence-v2"
        )

    assert result["scope_compliant_success"] is True
    assert context_events


def test_public_mock_v17_recovers_one_actionless_completion_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v17_actionless_smoke",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V7,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    class ActionlessOnceAdapter(MockModelAdapter):
        def __init__(self) -> None:
            super().__init__(package.public.task_id, structured_finish=True)
            self.injected = False

        def next_turn(self, context, tools):
            names = {item["name"] for item in tools}
            if names == {"run_check"} and not self.injected:
                self.injected = True
                return ModelTurn(text="The patch should be checked now.")
            return super().next_turn(context, tools)

    adapter = ActionlessOnceAdapter()
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(runner, "_model_adapter", lambda *_args, **_kwargs: adapter)

    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    completion_modes = [
        event.payload.get("lean_completion_recovery_mode")
        for event in events
        if event.type == EventType.MODEL_CALLED
        and event.payload.get("lean_completion_recovery_mode") is not None
    ]

    assert result["scope_compliant_success"] is True
    assert adapter.injected is True
    assert completion_modes.count("retry-actionless") == 1
    assert any(
        event.payload.get("lean_response_done") is False
        and event.payload.get("response_tool_call_count") == 0
        and event.payload.get("lean_completion_recovery_mode") == "primary-reserved"
        for event in events
        if event.type == EventType.MODEL_CALLED
    )


def test_public_mock_v18_persists_ordered_surfaces_and_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v18_ordered_smoke",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V8,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    context_events = [
        event
        for event in runner.state.list_events(manifest.run_id)
        if event.type == EventType.CONTEXT_BUILT
    ]
    surfaces: list[tuple[str, ...]] = []
    for event in context_events:
        artifact = json.loads(Path(str(event.payload["artifact_path"])).read_text(encoding="utf-8"))
        evidence = validate_persisted_lean_harness_request(artifact)
        assert isinstance(evidence, LeanHarnessRequestEvidenceV8)
        assert evidence.request_body["parallel_tool_calls"] is False
        if evidence.completion_loop_decision.target != "phase-policy":
            assert len(evidence.phase_tool_surface.selected_tool_names) == 1
        surfaces.append(evidence.phase_tool_surface.selected_tool_names)

    assert result["scope_compliant_success"] is True
    assert ("run_check",) in surfaces
    assert ("get_diff",) in surfaces
    assert ("finish_task",) in surfaces
    assert surfaces.index(("run_check",)) < surfaces.index(("get_diff",)) < surfaces.index(
        ("finish_task",)
    )


def test_public_mock_v18_rejects_multiple_calls_before_tool_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_root = Path("tasks/smoke/config-falsy-override")
    package = load_task_package(task_root)
    manifest = build_lean_harness_calibration_manifest(
        package,
        run_id="run_lean_v18_multi_call_rejection",
        condition=MemoryCondition.NO_MEMORY,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V8,
    )
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)

    class MultiCallAdapter(MockModelAdapter):
        def next_turn(self, context, tools):
            if {item["name"] for item in tools} == {"run_check"}:
                return ModelTurn(
                    tool_calls=[
                        RequestedTool(
                            "run_check",
                            "multi-check-1",
                            {"check_id": "existing-unit-tests"},
                        ),
                        RequestedTool(
                            "run_check",
                            "multi-check-2",
                            {"check_id": "existing-unit-tests"},
                        ),
                    ]
                )
            return super().next_turn(context, tools)

    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args, **_kwargs: MultiCallAdapter(package.public.task_id),
    )
    result = runner.start(task_root / "public.yaml", model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)

    assert result["outcome_kind"] == "agent_failure"
    assert "more than one tool call" in result["terminal_error"]["message"]
    assert not any(
        event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        for event in events
    )
