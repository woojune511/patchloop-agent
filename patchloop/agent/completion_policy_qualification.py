"""Deterministic zero-call qualification for the opt-in V7 completion policy."""

from __future__ import annotations

import gc
import json
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext
from patchloop.agent.event_descriptor_role_qualification import (
    build_event_descriptor_role_qualification,
    load_event_descriptor_role_qualification,
)
from patchloop.agent.lean_runtime import (
    LEAN_RUNTIME_POLICY_VERSION_V7,
    LeanHarnessRequestEvidenceV7,
    assemble_lean_harness_request,
    build_lean_harness_calibration_manifest,
    load_lean_harness_dependencies,
)
from patchloop.agent.mechanical_friction import project_completion_response_recovery
from patchloop.agent.phases import EvidenceState
from patchloop.agent.tools import TOOL_SCHEMAS_V11, ToolGateway
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Budget, EventType, MemoryCondition, RunEvent, Usage
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.repository import WorkspaceManager
from patchloop.sandbox import LocalSandbox
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

QUALIFICATION_PATH = Path(
    "experiments/lean-harness-completion-policy-public-qualification-20260823-v1.json"
)
SPEC_PATH = Path("experiments/lean-harness-completion-policy-successor-spec-20260823-v1.json")
R7_DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-event-role-20260823-r7-public-trace-diagnosis-v1.json"
)
R7_DIAGNOSIS_BYTES = 11_566
R7_DIAGNOSIS_SHA256 = "sha256:1d55ec573c5caf554b530af264d49fa6da30230293320e8c459db020d83faab5"

SOURCE_FILES = (
    "patchloop/agent/completion_policy_qualification.py",
    "patchloop/agent/mechanical_friction.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
)


class FileBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1)
    bytes: int = Field(ge=1)
    file_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class QualificationScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    scenario_id: str = Field(min_length=1)
    observed: dict[str, Any]
    observation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_scenario(self) -> Self:
        if self.observation_hash != sha256_json(self.observed):
            raise ValueError("completion qualification observation hash differs")
        return self


class CompletionPolicyQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-completion-policy-qualification-v1"]
    qualification_id: Literal["lean-harness-completion-policy-public-20260823-v1"]
    status: Literal["PUBLIC_OFFLINE_COMPLETION_POLICY_QUALIFIED_RUNTIME_CLOSED"]
    official: Literal[False]
    source_diagnosis: FileBinding
    source_spec: FileBinding
    source_files: tuple[FileBinding, ...]
    runtime_policy_version: Literal["lean-harness-v7"]
    tool_schema_version: Literal["v11"]
    context_policy_version: Literal["phase-evidence-v17"]
    completion_policy_version: Literal["state-driven-current-diff-v3"]
    response_recovery_policy_version: Literal["completion-response-single-shared-retry-v1"]
    edit_correction_policy_version: Literal["bounded-public-current-source-v1"]
    scenarios: tuple[QualificationScenario, ...] = Field(min_length=9)
    scenario_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    r7_actionless_rows: Literal[2]
    r7_edit_tool_failures: Literal[32]
    r7_provider_incomplete_rows: Literal[1]
    v6_consumed_scenario_set_preserved: Literal[True]
    cumulative_budget_limits_changed: Literal[False]
    historical_runtime_bytes_mutated: Literal[False]
    task_or_evaluator_contract_changed: Literal[False]
    task_repository_mutated: Literal[False]
    hidden_or_private_data_read: Literal[False]
    reference_patch_read: Literal[False]
    reasoning_text_read: Literal[False]
    provider_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    added_cost_usd: Literal["0"]
    runtime_activation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    quality_improvement_established: Literal[False]
    completion_paths_offline_qualified: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.source_diagnosis.path != R7_DIAGNOSIS_PATH.as_posix():
            raise ValueError("completion qualification diagnosis path differs")
        if (
            self.source_diagnosis.bytes != R7_DIAGNOSIS_BYTES
            or self.source_diagnosis.file_sha256 != R7_DIAGNOSIS_SHA256
        ):
            raise ValueError("completion qualification diagnosis binding differs")
        if self.source_spec.path != SPEC_PATH.as_posix():
            raise ValueError("completion qualification spec path differs")
        if tuple(item.path for item in self.source_files) != SOURCE_FILES:
            raise ValueError("completion qualification source inventory differs")
        scenario_ids = tuple(item.scenario_id for item in self.scenarios)
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("completion qualification scenarios repeat")
        if self.scenario_set_hash != sha256_json(
            [item.model_dump(mode="json") for item in self.scenarios]
        ):
            raise ValueError("completion qualification scenario set differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("completion qualification content hash differs")
        return self


def _binding(root: Path, relative: Path | str) -> FileBinding:
    relative_path = Path(relative)
    raw = (root / relative_path).read_bytes()
    return FileBinding(
        path=relative_path.as_posix(),
        bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _scenario(scenario_id: str, observed: dict[str, Any]) -> QualificationScenario:
    return QualificationScenario(
        scenario_id=scenario_id,
        observed=observed,
        observation_hash=sha256_json(observed),
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


def _context() -> BuiltContext:
    payload = {
        "task": {"id": "config-falsy-override"},
        "selected_memory": None,
        "phase_policy": {"phase": "REPRODUCE"},
        "recent_events": [],
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
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


def _event(sequence: int, event_type: EventType, payload: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=f"qualification-event-{sequence}",
        run_id="qualification-run",
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 23, tzinfo=UTC),
        actor="qualification",
        payload=payload,
    )


def _assemble(
    root: Path,
    *,
    phase: EvidenceState,
    events: tuple[RunEvent, ...] = (),
    usage: Usage | None = None,
) -> LeanHarnessRequestEvidenceV7:
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    context = _context()
    assembled = assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies(root),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=TOOL_SCHEMAS_V11,
        phase_evidence=phase,
        events=events,
        usage=usage or Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public mock prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V7,
    )
    if not isinstance(assembled.evidence, LeanHarnessRequestEvidenceV7):
        raise ContractError("completion qualification assembled the wrong runtime")
    return assembled.evidence


def _gateway_edit_observations(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    package = load_task_package(root / "tasks/smoke/csv-quoted-newline")
    with tempfile.TemporaryDirectory(prefix="patchloop-completion-qualification-") as temporary:
        temporary_root = Path(temporary)
        manifest = build_lean_harness_calibration_manifest(
            package,
            run_id="run_completion_qualification_gateway",
            condition=MemoryCondition.NO_MEMORY,
            runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V7,
        )
        state = StateStore(temporary_root / "state.sqlite3")
        state.create_run(manifest)
        manager = WorkspaceManager(
            root / "fixtures/repositories",
            temporary_root / "workspaces",
        )
        workspace = manager.create(
            manifest.run_id,
            package.public.repository.url,
            package.public.repository.base_commit,
        )
        gateway = ToolGateway(
            run_id=manifest.run_id,
            workspace=workspace,
            task=package.public,
            state=state,
            artifacts=ArtifactStore(temporary_root / "artifacts"),
            sandbox=LocalSandbox(),
            tool_schema_version="v11",
            context_policy_version="phase-evidence-v17",
        )
        baseline = manager.diff_summary(workspace).patch_hash
        stale_patch = (
            "diff --git a/mini_data_utils/csvlite.py b/mini_data_utils/csvlite.py\n"
            "--- a/mini_data_utils/csvlite.py\n"
            "+++ b/mini_data_utils/csvlite.py\n"
            "@@ -1,4 +1,4 @@\n"
            "-A source line that is not present\n"
            "+A replacement line\n"
            " \n"
            " import csv\n"
            " \n"
        )
        raw = gateway.execute(
            "apply_patch",
            "qualification-stale-raw",
            {"patch": stale_patch},
        )
        structured = gateway.execute(
            "apply_structured_edit",
            "qualification-stale-structured",
            {
                "schema_version": "structured-edit-arguments-v2",
                "files": [
                    {
                        "path": "mini_data_utils/csvlite.py",
                        "replacements": [
                            {
                                "expected_text": (
                                    "A deliberately tiny CSV reader with one audited defect."
                                ),
                                "replacement_text": (
                                    "A deliberately tiny CSV reader with one documented defect."
                                ),
                            }
                        ],
                    }
                ],
            },
        )
        if (
            raw.status != "rejected"
            or structured.status != "rejected"
            or manager.diff_summary(workspace).patch_hash != baseline
        ):
            raise ContractError("completion edit qualification mutated or admitted a rejection")
        raw_correction = raw.output["error_details"]["edit_correction"]
        structured_correction = structured.output["error_details"]["edit_correction"]
        raw_entries = raw_correction["current_source"]["entries"]
        structured_entries = structured_correction["current_source"]["entries"]
        observations = (
            {
                "failure_reason": raw_correction["failure_reason"],
                "policy_version": raw_correction["policy_version"],
                "source_excerpt_count": len(raw_entries),
                "source_excerpt_hashes": [item["content_hash"] for item in raw_entries],
                "mutation_synthesized": raw_correction["mutation_synthesized"],
                "worktree_unchanged": raw_correction["current_worktree_diff_hash"] == baseline,
            },
            {
                "failure_reason": structured_correction["failure_reason"],
                "policy_version": structured_correction["policy_version"],
                "source_excerpt_count": len(structured_entries),
                "exact_occurrence_counts": [
                    item["exact_occurrence_count"] for item in structured_entries
                ],
                "closest_line_match_ratios": [
                    item["closest_line_match_ratio"] for item in structured_entries
                ],
                "mutation_synthesized": structured_correction["mutation_synthesized"],
                "worktree_unchanged": (
                    structured_correction["current_worktree_diff_hash"] == baseline
                ),
            },
        )
        del gateway, state, manager
        gc.collect()
        return observations


def build_completion_policy_qualification(
    repository: str | Path = ".",
) -> CompletionPolicyQualification:
    root = Path(repository).resolve()
    diagnosis = _binding(root, R7_DIAGNOSIS_PATH)
    if diagnosis.bytes != R7_DIAGNOSIS_BYTES or diagnosis.file_sha256 != R7_DIAGNOSIS_SHA256:
        raise ContractError("R7 public trace diagnosis differs")
    diagnosis_document = json.loads((root / R7_DIAGNOSIS_PATH).read_text(encoding="utf-8"))
    rows = diagnosis_document["rows"]
    actionless_rows = sum(
        item.get("terminal_classification") == "ACTIONLESS_MODEL_RESPONSE" for item in rows
    )
    edit_tool_failures = sum(
        failure["count"]
        for item in rows
        for failure in item.get("failed_tools", [])
        if failure["tool"] in {"apply_patch", "apply_structured_edit"}
    )
    incomplete_rows = sum(
        item.get("terminal_classification") == "PROVIDER_INCOMPLETE_RESPONSE_AT_OUTPUT_CAP"
        for item in rows
    )
    if (actionless_rows, edit_tool_failures, incomplete_rows) != (2, 32, 1):
        raise ContractError("R7 public completion diagnosis tuple differs")

    current_v6 = build_event_descriptor_role_qualification(root)
    consumed_v6 = load_event_descriptor_role_qualification(root)
    if current_v6.scenario_set_hash != consumed_v6.scenario_set_hash:
        raise ContractError("V6 consumed behavior scenario set drifted")

    phase = _phase()
    check = _assemble(root, phase=phase)
    correction_phase = replace(
        phase,
        latest_check_sequence=2,
        allowed_next_actions=("apply_patch", "read_file", "search_files"),
    )
    correction = _assemble(root, phase=correction_phase)
    checked_phase = replace(
        phase,
        completed_checks=("public-check",),
        pending_checks=(),
        current_diff_check_event_sequences=(2,),
        latest_check_sequence=2,
        missing_evidence=("final_diff_review_current_diff",),
        allowed_next_actions=("get_diff",),
    )
    diff_review = _assemble(root, phase=checked_phase)
    reviewed_phase = replace(
        checked_phase,
        review_event_sequence=3,
        review_presented_to_model=True,
        submission_ready=True,
        missing_evidence=(),
        allowed_next_actions=("finish_task",),
    )
    submission = _assemble(root, phase=reviewed_phase)

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
    checkpoint = _event(2, EventType.CHECKPOINT_SAVED, {"through_sequence": 1})
    actionless_retry = _assemble(
        root,
        phase=phase,
        events=(actionless, checkpoint),
        usage=Usage(input_tokens=5_000, output_tokens=1_000, model_calls=1),
    )
    incomplete = _event(
        3,
        EventType.MODEL_CALLED,
        {
            "response_error_code": "incomplete_response",
            "response_incomplete_reason": "max_output_tokens",
            "output_tokens": 22_952,
            "reasoning_output_tokens": 22_952,
            "response_text_present": False,
            "response_tool_call_count": 0,
            "lean_response_done": False,
            "lean_completion_recovery_mode": "primary-reserved",
            "lean_reserved_completion_retry_output_tokens": 2_048,
        },
    )
    incomplete_retry = _assemble(
        root,
        phase=phase,
        events=(incomplete, _event(4, EventType.CHECKPOINT_SAVED, {"through_sequence": 3})),
        usage=Usage(input_tokens=5_000, output_tokens=22_952, model_calls=1),
    )
    consumed = _event(
        5,
        EventType.MODEL_CALLED,
        {
            "response_error_code": None,
            "response_tool_call_count": 1,
            "lean_response_done": False,
            "lean_completion_recovery_mode": "retry-actionless",
        },
    )
    after_retry = project_completion_response_recovery(
        phase_mode="exploration",
        completion_lane_active=True,
        events=(actionless, checkpoint, consumed),
        usage=Usage(input_tokens=10_000, output_tokens=3_048, model_calls=2),
        budget=_budget(),
        requested_input_tokens=5_000,
        configured_max_output_tokens=25_000,
    )
    raw_edit, structured_edit = _gateway_edit_observations(root)

    scenarios = (
        _scenario(
            "post-mutation-exploration-forces-visible-check",
            {
                "reserve_mode": check.finalization_request_mode.mode,
                "completion_target": check.phase_tool_surface.completion_target,
                "selected_tool_names": check.phase_tool_surface.selected_tool_names,
                "completion_lane_active": check.phase_tool_surface.completion_lane_active,
            },
        ),
        _scenario(
            "failed-check-forces-correction",
            {
                "completion_target": correction.phase_tool_surface.completion_target,
                "selected_tool_names": correction.phase_tool_surface.selected_tool_names,
                "recheck_required": (correction.phase_tool_surface.recheck_after_mutation_required),
            },
        ),
        _scenario(
            "passing-check-forces-diff-review",
            {
                "completion_target": diff_review.phase_tool_surface.completion_target,
                "selected_tool_names": diff_review.phase_tool_surface.selected_tool_names,
            },
        ),
        _scenario(
            "presented-diff-forces-submission",
            {
                "completion_target": submission.phase_tool_surface.completion_target,
                "selected_tool_names": submission.phase_tool_surface.selected_tool_names,
            },
        ),
        _scenario(
            "checkpoint-safe-actionless-retry",
            actionless_retry.completion_response_recovery.model_dump(mode="json"),
        ),
        _scenario(
            "checkpoint-safe-reasoning-incomplete-retry",
            incomplete_retry.completion_response_recovery.model_dump(mode="json"),
        ),
        _scenario(
            "shared-retry-disables-second-reserve",
            after_retry.model_dump(mode="json"),
        ),
        _scenario("raw-edit-bounded-current-source", raw_edit),
        _scenario("structured-edit-bounded-current-source", structured_edit),
        _scenario(
            "v6-consumed-scenario-set-preserved",
            {
                "consumed_scenario_set_hash": consumed_v6.scenario_set_hash,
                "current_scenario_set_hash": current_v6.scenario_set_hash,
                "equal": True,
            },
        ),
    )
    body: dict[str, Any] = {
        "schema_version": "lean-harness-completion-policy-qualification-v1",
        "qualification_id": "lean-harness-completion-policy-public-20260823-v1",
        "status": "PUBLIC_OFFLINE_COMPLETION_POLICY_QUALIFIED_RUNTIME_CLOSED",
        "official": False,
        "source_diagnosis": diagnosis.model_dump(mode="python"),
        "source_spec": _binding(root, SPEC_PATH).model_dump(mode="python"),
        "source_files": tuple(
            _binding(root, relative).model_dump(mode="python") for relative in SOURCE_FILES
        ),
        "runtime_policy_version": "lean-harness-v7",
        "tool_schema_version": "v11",
        "context_policy_version": "phase-evidence-v17",
        "completion_policy_version": "state-driven-current-diff-v3",
        "response_recovery_policy_version": "completion-response-single-shared-retry-v1",
        "edit_correction_policy_version": "bounded-public-current-source-v1",
        "scenarios": tuple(item.model_dump(mode="python") for item in scenarios),
        "scenario_set_hash": sha256_json([item.model_dump(mode="json") for item in scenarios]),
        "r7_actionless_rows": 2,
        "r7_edit_tool_failures": 32,
        "r7_provider_incomplete_rows": 1,
        "v6_consumed_scenario_set_preserved": True,
        "cumulative_budget_limits_changed": False,
        "historical_runtime_bytes_mutated": False,
        "task_or_evaluator_contract_changed": False,
        "task_repository_mutated": False,
        "hidden_or_private_data_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "added_cost_usd": "0",
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "completion_paths_offline_qualified": True,
    }
    return CompletionPolicyQualification.model_validate({**body, "content_hash": sha256_json(body)})


def qualification_bytes(qualification: CompletionPolicyQualification) -> bytes:
    return (canonical_json(qualification.model_dump(mode="json")) + "\n").encode("utf-8")


def load_completion_policy_qualification(
    repository: str | Path = ".",
) -> CompletionPolicyQualification:
    path = Path(repository).resolve() / QUALIFICATION_PATH
    raw = path.read_bytes()
    try:
        qualification = CompletionPolicyQualification.model_validate_json(raw)
    except ValueError as exc:
        raise ContractError("completion policy qualification is invalid") from exc
    if qualification_bytes(qualification) != raw:
        raise ContractError("completion policy qualification bytes are not canonical")
    return qualification
