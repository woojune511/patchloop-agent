"""Deterministic, public-only qualification for the opt-in Lean V8 loop.

The builder evaluates pure state projections and assembles one V8 request.  It
does not dispatch a provider, start Docker, run a task check/evaluator, or
mutate a task workspace.  The resulting artifact qualifies only the runtime
contract; it is not evidence that the policy improves task success.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.completion_loop_successor import (
    COMPLETION_LOOP_POLICY,
    CORRECTION_CONTEXT_POLICY,
    PROVIDER_TERMINAL_ATTRIBUTION_POLICY,
    completion_instruction,
    project_completion_loop_successor,
    project_completion_tool_surface,
    project_current_edit_correction_context,
    project_provider_terminal_attribution,
)
from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V8,
    LEAN_RUNTIME_POLICY_VERSION_V8,
    LEAN_TOOL_SCHEMA_VERSION_V8,
    LeanHarnessRequestEvidenceV8,
    assemble_lean_harness_request,
    load_lean_harness_dependencies,
)
from patchloop.agent.phases import diff_bound_evidence
from patchloop.agent.structured_edit import STRUCTURED_EDIT_TOOL_SCHEMA_V2
from patchloop.agent.tools import TOOL_SCHEMAS_V12
from patchloop.contracts import (
    Budget,
    EventType,
    MemoryCondition,
    PublicTask,
    RunEvent,
    Usage,
)
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.util import canonical_json, sha256_bytes, sha256_json, sha256_text

QUALIFICATION_PATH = Path(
    "experiments/lean-harness-ordered-correction-public-qualification-20260824-v2.json"
)
SPEC_PATH = Path(
    "experiments/lean-harness-ordered-correction-successor-spec-20260824-v1.json"
)
DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-completion-policy-20260823-r8-public-trace-diagnosis-v2.json"
)
DIAGNOSIS_BYTES = 15_358
DIAGNOSIS_SHA256 = (
    "sha256:419b42b8188f0efbaa228f711a1d963e8c945d56936d7a95c519f87b6480dddf"
)
DIAGNOSIS_CONTENT_HASH = (
    "sha256:021af168a0fb1fb699641a6689fb5089c5f91780065cf215d5c95552ea682898"
)
PUBLIC_TASK_PATH = Path(
    "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml"
)
PREDECESSOR_QUALIFICATION_PATH = Path(
    "experiments/lean-harness-completion-policy-public-qualification-20260823-v1.json"
)
PREVIOUS_ORDERED_QUALIFICATION_PATH = Path(
    "experiments/lean-harness-ordered-correction-public-qualification-20260824-v1.json"
)
SOURCE_FILES = (
    "patchloop/agent/completion_loop_successor_qualification.py",
    "patchloop/agent/completion_loop_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/runner.py",
    "patchloop/contracts.py",
)
SCENARIO_IDS = (
    "post-mutation-binds-first-public-check",
    "failed-check-requires-current-source-read",
    "fresh-read-exposes-one-structured-correction",
    "edit-rejection-invalidates-prior-read",
    "passing-targeted-check-binds-upstream-check",
    "all-public-checks-pass-before-diff-review",
    "presented-diff-review-binds-submission",
    "latest-public-edit-correction-appears-once",
    "explicit-provider-incomplete-precedes-accounting-mismatch",
    "v8-request-binds-task-surface-and-small-ceiling",
)

_DIFF_HASH = sha256_text("ordered-correction-qualification-current-diff")
_AVAILABLE_TOOL_SCHEMAS = (
    *TOOL_SCHEMAS_V12,
    STRUCTURED_EDIT_TOOL_SCHEMA_V2,
)
_AVAILABLE_TOOL_NAMES = tuple(item["name"] for item in _AVAILABLE_TOOL_SCHEMAS)


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
    def validate_observation(self) -> Self:
        if self.observation_hash != sha256_json(self.observed):
            raise ValueError("ordered-correction observation hash differs")
        return self


class OrderedCorrectionQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-harness-ordered-correction-qualification-v2"]
    qualification_id: Literal[
        "lean-harness-ordered-correction-public-20260824-v2"
    ]
    status: Literal[
        "PUBLIC_OFFLINE_ORDERED_CORRECTION_RUNTIME_QUALIFIED_LIVE_CLOSED"
    ]
    official: Literal[False]
    source_diagnosis: FileBinding
    source_spec: FileBinding
    public_task_source: FileBinding
    predecessor_qualification: FileBinding
    previous_ordered_qualification: FileBinding
    source_files: tuple[FileBinding, ...]
    runtime_policy_version: Literal["lean-harness-v8"]
    tool_schema_version: Literal["v12"]
    context_policy_version: Literal["phase-evidence-v18"]
    completion_policy_version: Literal[
        "ordered-check-refresh-structured-correction-v1"
    ]
    correction_context_policy_version: Literal[
        "latest-public-edit-correction-once-v1"
    ]
    provider_terminal_attribution_policy_version: Literal[
        "explicit-terminal-before-accounting-v1"
    ]
    scenarios: tuple[QualificationScenario, ...] = Field(min_length=10, max_length=10)
    scenario_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    v7_consumed_artifact_preserved: Literal[True]
    cumulative_budget_limits_changed: Literal[False]
    task_or_evaluator_contract_changed: Literal[False]
    task_repository_mutated: Literal[False]
    hidden_or_private_data_read: Literal[False]
    reference_patch_read: Literal[False]
    reasoning_text_read: Literal[False]
    provider_calls: Literal[0]
    docker_calls: Literal[0]
    evaluator_calls: Literal[0]
    visible_check_calls: Literal[0]
    added_cost_usd: Literal["0"]
    runtime_activation_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    quality_improvement_established: Literal[False]
    runtime_contract_offline_qualified: Literal[True]
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_qualification(self) -> Self:
        if self.source_diagnosis.path != DIAGNOSIS_PATH.as_posix():
            raise ValueError("ordered-correction diagnosis path differs")
        if (
            self.source_diagnosis.bytes != DIAGNOSIS_BYTES
            or self.source_diagnosis.file_sha256 != DIAGNOSIS_SHA256
        ):
            raise ValueError("ordered-correction diagnosis binding differs")
        if self.source_spec.path != SPEC_PATH.as_posix():
            raise ValueError("ordered-correction spec path differs")
        if self.public_task_source.path != PUBLIC_TASK_PATH.as_posix():
            raise ValueError("ordered-correction public task path differs")
        if (
            self.predecessor_qualification.path
            != PREDECESSOR_QUALIFICATION_PATH.as_posix()
        ):
            raise ValueError("ordered-correction predecessor path differs")
        if (
            self.previous_ordered_qualification.path
            != PREVIOUS_ORDERED_QUALIFICATION_PATH.as_posix()
        ):
            raise ValueError("ordered-correction format predecessor path differs")
        if tuple(item.path for item in self.source_files) != SOURCE_FILES:
            raise ValueError("ordered-correction source inventory differs")
        if tuple(item.scenario_id for item in self.scenarios) != SCENARIO_IDS:
            raise ValueError("ordered-correction scenario inventory differs")
        scenario_payload = [item.model_dump(mode="json") for item in self.scenarios]
        if self.scenario_set_hash != sha256_json(scenario_payload):
            raise ValueError("ordered-correction scenario set differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("ordered-correction qualification hash differs")
        return self


def _binding(root: Path, relative: Path | str) -> FileBinding:
    path = Path(relative)
    raw = (root / path).read_bytes()
    return FileBinding(
        path=path.as_posix(),
        bytes=len(raw),
        file_sha256=sha256_bytes(raw),
    )


def _scenario(scenario_id: str, observed: dict[str, Any]) -> QualificationScenario:
    return QualificationScenario(
        scenario_id=scenario_id,
        observed=observed,
        observation_hash=sha256_json(observed),
    )


def _event(sequence: int, event_type: EventType, payload: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=f"ordered-correction-qualification-{sequence}",
        run_id="ordered-correction-qualification",
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 24, tzinfo=UTC),
        actor="offline-qualification",
        payload=payload,
    )


def _public_task(root: Path) -> PublicTask:
    payload = yaml.safe_load((root / PUBLIC_TASK_PATH).read_text(encoding="utf-8"))
    return PublicTask.model_validate(payload)


def _patch_event() -> RunEvent:
    return _event(
        1,
        EventType.PATCH_APPLIED,
        {"tool": "apply_structured_edit", "worktree_diff_hash": _DIFF_HASH},
    )


def _check_event(sequence: int, check_id: str, *, passed: bool) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "run_check",
            "check_id": check_id,
            "passed": passed,
            "worktree_diff_hash": _DIFF_HASH,
        },
    )


def _decision(
    task: PublicTask,
    events: tuple[RunEvent, ...],
    *,
    presented_sequences: tuple[int, ...] = (),
):
    evidence = diff_bound_evidence(
        task,
        events,
        _DIFF_HASH,
        presented_tool_results=tuple(
            {"event_sequence": sequence, "available": True, "truncated": False}
            for sequence in presented_sequences
        ),
        completion_driven=True,
    )
    decision = project_completion_loop_successor(
        task=task,
        evidence=evidence,
        events=events,
        available_tool_names=_AVAILABLE_TOOL_NAMES,
        configured_max_output_tokens=25_000,
    )
    surface = project_completion_tool_surface(
        decision=decision,
        source_tool_schemas=_AVAILABLE_TOOL_SCHEMAS,
    )
    return evidence, decision, surface


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
        "task": {"id": "anyio-interrupt-runner-cleanup", "version": 4},
        "selected_memory": None,
        "phase_policy": {"phase": "IMPLEMENT"},
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


def _request_evidence(
    root: Path,
    task: PublicTask,
    events: tuple[RunEvent, ...],
) -> LeanHarnessRequestEvidenceV8:
    phase, _, _ = _decision(task, events)
    context = _context()
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    assembled = assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies(root),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=TOOL_SCHEMAS_V12,
        phase_evidence=phase,
        events=events,
        usage=Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public offline qualification prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=LEAN_RUNTIME_POLICY_VERSION_V8,
        task=task,
    )
    evidence = assembled.evidence
    if type(evidence) is not LeanHarnessRequestEvidenceV8:
        raise TypeError("ordered-correction assembly did not produce exact V8 evidence")
    return evidence


def build_ordered_correction_qualification(
    root: str | Path,
) -> OrderedCorrectionQualification:
    repository = Path(root).resolve()
    task = _public_task(repository)
    check_ids = tuple(check.id for check in task.visible_checks)
    if check_ids != (
        "public-interrupt-runner-lifecycle",
        "upstream-pytest-plugin-regression",
    ):
        raise ValueError("ordered-correction public check order differs")

    patch = _patch_event()
    initial_events = (patch,)
    _, initial, initial_surface = _decision(task, initial_events)

    failed = _check_event(2, check_ids[0], passed=False)
    failed_events = (patch, failed)
    _, after_failure, failure_surface = _decision(task, failed_events)

    read = _event(
        3,
        EventType.TOOL_SUCCEEDED,
        {"tool": "read_file", "worktree_diff_hash": _DIFF_HASH},
    )
    read_events = (*failed_events, read)
    _, after_read, read_surface = _decision(task, read_events)

    edit_rejection = _event(
        4,
        EventType.TOOL_FAILED,
        {"tool": "apply_structured_edit", "reason": "expected_text_absent"},
    )
    _, after_edit_rejection, rejection_surface = _decision(
        task, (*read_events, edit_rejection)
    )

    first_pass = _check_event(2, check_ids[0], passed=True)
    first_pass_events = (patch, first_pass)
    _, after_first_pass, first_pass_surface = _decision(task, first_pass_events)

    second_pass = _check_event(3, check_ids[1], passed=True)
    both_pass_events = (*first_pass_events, second_pass)
    _, after_both_pass, both_pass_surface = _decision(task, both_pass_events)

    diff_review = _event(
        4,
        EventType.TOOL_SUCCEEDED,
        {"tool": "get_diff", "worktree_diff_hash": _DIFF_HASH},
    )
    reviewed_events = (*both_pass_events, diff_review)
    _, after_review, review_surface = _decision(
        task, reviewed_events, presented_sequences=(4,)
    )

    correction = {
        "schema_version": "edit-correction-v1",
        "failure_reason": "expected_text_absent",
        "current_source_excerpt": "async def runner(...):",
    }
    correction_context = canonical_json(
        {
            "task": {"id": task.task_id},
            "recent_events": [
                {
                    "sequence": 7,
                    "payload": {
                        "tool": "apply_structured_edit",
                        "edit_correction": correction,
                        "result": {"edit_correction": correction},
                    },
                }
            ],
            "rejected_mutation_retry": {"edit_correction": correction},
        }
    )
    projected_correction = project_current_edit_correction_context(correction_context)
    provider_terminal = project_provider_terminal_attribution(
        response_status="incomplete",
        response_incomplete_reason="max_output_tokens",
        usage_present=True,
        input_token_count_match=False,
    )
    request = _request_evidence(repository, task, initial_events)

    run_check_schema = initial_surface.tool_schemas[0]
    bound_enum = run_check_schema["parameters"]["properties"]["check_id"]["enum"]
    upstream_enum = (
        first_pass_surface.tool_schemas[0]["parameters"]["properties"]["check_id"][
            "enum"
        ]
    )
    instruction = completion_instruction(after_read)
    scenarios = (
        _scenario(
            SCENARIO_IDS[0],
            {
                "target": initial.target,
                "expected_check_id": initial.expected_check_id,
                "selected_tool_names": initial_surface.selected_tool_names,
                "bound_check_enum": bound_enum,
                "effective_max_output_tokens": initial.effective_max_output_tokens,
                "parallel_tool_calls": initial.parallel_tool_calls,
                "one_tool_call_per_response": initial.one_tool_call_per_response,
            },
        ),
        _scenario(
            SCENARIO_IDS[1],
            {
                "target": after_failure.target,
                "selected_tool_names": failure_surface.selected_tool_names,
                "latest_failed_check_sequence": after_failure.latest_failed_check_sequence,
                "fresh_read_required": after_failure.fresh_read_required,
                "effective_max_output_tokens": after_failure.effective_max_output_tokens,
            },
        ),
        _scenario(
            SCENARIO_IDS[2],
            {
                "target": after_read.target,
                "selected_tool_names": read_surface.selected_tool_names,
                "latest_correction_read_sequence": after_read.latest_correction_read_sequence,
                "fresh_read_required": after_read.fresh_read_required,
                "effective_max_output_tokens": after_read.effective_max_output_tokens,
                "instruction_target": instruction["target"],
            },
        ),
        _scenario(
            SCENARIO_IDS[3],
            {
                "target": after_edit_rejection.target,
                "selected_tool_names": rejection_surface.selected_tool_names,
                "latest_edit_failure_sequence": after_edit_rejection.latest_edit_failure_sequence,
                "fresh_read_required": after_edit_rejection.fresh_read_required,
            },
        ),
        _scenario(
            SCENARIO_IDS[4],
            {
                "target": after_first_pass.target,
                "expected_check_id": after_first_pass.expected_check_id,
                "preserve_check_ids": after_first_pass.preserve_check_ids,
                "selected_tool_names": first_pass_surface.selected_tool_names,
                "bound_check_enum": upstream_enum,
            },
        ),
        _scenario(
            SCENARIO_IDS[5],
            {
                "target": after_both_pass.target,
                "completed_check_ids": after_both_pass.completed_check_ids,
                "selected_tool_names": both_pass_surface.selected_tool_names,
                "effective_max_output_tokens": after_both_pass.effective_max_output_tokens,
            },
        ),
        _scenario(
            SCENARIO_IDS[6],
            {
                "target": after_review.target,
                "selected_tool_names": review_surface.selected_tool_names,
                "effective_max_output_tokens": after_review.effective_max_output_tokens,
            },
        ),
        _scenario(
            SCENARIO_IDS[7],
            {
                "source_full_correction_occurrences": (
                    projected_correction.evidence.source_full_correction_occurrences
                ),
                "projected_full_correction_occurrences": (
                    projected_correction.evidence.projected_full_correction_occurrences
                ),
                "removed_full_correction_occurrences": (
                    projected_correction.evidence.removed_full_correction_occurrences
                ),
                "selected_event_sequence": (
                    projected_correction.evidence.selected_event_sequence
                ),
                "raw_trace_mutated": projected_correction.evidence.raw_trace_mutated,
            },
        ),
        _scenario(
            SCENARIO_IDS[8],
            {
                "primary_error_code": provider_terminal.primary_error_code,
                "accounting_mismatch_preserved": (
                    provider_terminal.accounting_mismatch_preserved
                ),
                "historical_adapter_precedence_differs": (
                    provider_terminal.historical_adapter_precedence_differs
                ),
                "fail_closed": provider_terminal.fail_closed,
            },
        ),
        _scenario(
            SCENARIO_IDS[9],
            {
                "request_evidence_schema": request.schema_version,
                "runtime_policy_version": request.runtime_policy_version,
                "tool_schema_version": request.tool_schema_version,
                "context_policy_version": request.context_policy_version,
                "public_task_hash": request.public_task_hash,
                "public_check_order": request.public_check_order,
                "decision_hash": request.completion_loop_decision.content_hash,
                "tool_surface_hash": request.phase_tool_surface.content_hash,
                "instruction_hash": request.completion_instruction_hash,
                "request_tool_names": tuple(
                    item["name"] for item in request.request_body["tools"]
                ),
                "max_output_tokens": request.request_body["max_output_tokens"],
                "parallel_tool_calls": request.request_body["parallel_tool_calls"],
                "one_tool_call_per_response": request.one_tool_call_per_response,
            },
        ),
    )

    diagnosis_binding = _binding(repository, DIAGNOSIS_PATH)
    diagnosis_payload = json.loads((repository / DIAGNOSIS_PATH).read_text(encoding="utf-8"))
    if diagnosis_payload.get("content_hash") != DIAGNOSIS_CONTENT_HASH:
        raise ValueError("ordered-correction diagnosis content hash differs")
    scenario_payload = tuple(item.model_dump(mode="json") for item in scenarios)
    body = {
        "schema_version": "lean-harness-ordered-correction-qualification-v2",
        "qualification_id": "lean-harness-ordered-correction-public-20260824-v2",
        "status": "PUBLIC_OFFLINE_ORDERED_CORRECTION_RUNTIME_QUALIFIED_LIVE_CLOSED",
        "official": False,
        "source_diagnosis": diagnosis_binding.model_dump(mode="python"),
        "source_spec": _binding(repository, SPEC_PATH).model_dump(mode="python"),
        "public_task_source": _binding(repository, PUBLIC_TASK_PATH).model_dump(
            mode="python"
        ),
        "predecessor_qualification": _binding(
            repository, PREDECESSOR_QUALIFICATION_PATH
        ).model_dump(mode="python"),
        "previous_ordered_qualification": _binding(
            repository, PREVIOUS_ORDERED_QUALIFICATION_PATH
        ).model_dump(mode="python"),
        "source_files": tuple(
            _binding(repository, path).model_dump(mode="python") for path in SOURCE_FILES
        ),
        "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V8,
        "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V8,
        "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V8,
        "completion_policy_version": COMPLETION_LOOP_POLICY,
        "correction_context_policy_version": CORRECTION_CONTEXT_POLICY,
        "provider_terminal_attribution_policy_version": (
            PROVIDER_TERMINAL_ATTRIBUTION_POLICY
        ),
        "scenarios": scenario_payload,
        "scenario_set_hash": sha256_json(scenario_payload),
        "v7_consumed_artifact_preserved": True,
        "cumulative_budget_limits_changed": False,
        "task_or_evaluator_contract_changed": False,
        "task_repository_mutated": False,
        "hidden_or_private_data_read": False,
        "reference_patch_read": False,
        "reasoning_text_read": False,
        "provider_calls": 0,
        "docker_calls": 0,
        "evaluator_calls": 0,
        "visible_check_calls": 0,
        "added_cost_usd": "0",
        "runtime_activation_authorized": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "runtime_contract_offline_qualified": True,
    }
    return OrderedCorrectionQualification.model_validate(
        {**body, "content_hash": sha256_json(body)}
    )


def qualification_bytes(qualification: OrderedCorrectionQualification) -> bytes:
    return (canonical_json(qualification.model_dump(mode="json")) + "\n").encode("utf-8")


def load_ordered_correction_qualification(
    root: str | Path,
) -> OrderedCorrectionQualification:
    path = Path(root).resolve() / QUALIFICATION_PATH
    return OrderedCorrectionQualification.model_validate_json(path.read_bytes())


__all__ = [
    "DIAGNOSIS_PATH",
    "OrderedCorrectionQualification",
    "PUBLIC_TASK_PATH",
    "QUALIFICATION_PATH",
    "SOURCE_FILES",
    "SPEC_PATH",
    "build_ordered_correction_qualification",
    "load_ordered_correction_qualification",
    "qualification_bytes",
]
