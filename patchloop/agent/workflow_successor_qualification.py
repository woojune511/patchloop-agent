"""Deterministic public-only qualification for Lean workflow V9 and V10.

The builder exercises pure event projections and mock request assembly only. It
does not call a provider, Docker, a registered visible check, or an evaluator,
and it does not mutate a task repository.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LeanHarnessRequestEvidenceV9,
    LeanHarnessRequestEvidenceV10,
    assemble_lean_harness_request,
    load_lean_harness_dependencies,
)
from patchloop.agent.phases import EvidenceState, diff_bound_evidence
from patchloop.agent.tools import TOOL_SCHEMAS_V13, TOOL_SCHEMAS_V14
from patchloop.agent.workflow_successor import (
    PLAN_RECORDED_EVENT_SCHEMA,
    PROTOCOL_RECOVERY_POLICY,
    project_public_task_spec,
    project_workflow_successor,
    validate_record_work_plan,
)
from patchloop.contracts import (
    Budget,
    EventType,
    MemoryCondition,
    Phase,
    PublicTask,
    RunEvent,
    Usage,
)
from patchloop.errors import ContractError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.util import (
    canonical_json,
    load_unique_yaml,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

QUALIFICATION_PATH = Path(
    "experiments/lean-harness-workflow-successor-public-qualification-20260824-v1.json"
)
R9_DIAGNOSIS_PATH = Path(
    "reports/rapid-development/artifacts/"
    "rapid-public-dev-anyio-ordered-correction-20260824-r9-workflow-diagnosis-v1.json"
)
PUBLIC_TASK_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml")
SOURCE_FILES = (
    "patchloop/agent/workflow_successor_qualification.py",
    "patchloop/agent/workflow_successor.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/model.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "tests/test_workflow_successor.py",
    "tests/test_workflow_successor_runner.py",
)
SCENARIO_IDS = (
    "v9-first-visible-check-bound",
    "v9-third-investigation-forces-read",
    "v9-third-investigation-then-edit",
    "v9-edit-rejection-requires-reread",
    "v9-correction-attempt-limit",
    "v9-review-repair-surface",
    "v9-shared-recovery-reconstructed",
    "v10-public-task-spec",
    "v10-mutation-hidden-before-plan",
    "v10-static-plan-validated",
    "v10-stale-evidence-rejected",
    "v10-plan-propagates-through-mutation",
    "v9-request-assembled",
    "v10-request-assembled",
)

_RUN_ID = "workflow-successor-offline-qualification"
_EMPTY_DIFF_HASH = sha256_text("")
_DIFF_HASH = sha256_text("workflow-successor-qualified-diff")


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
            raise ValueError("workflow qualification observation hash differs")
        return self


class WorkflowSuccessorQualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-workflow-successor-qualification-v1"]
    qualification_id: Literal["lean-workflow-successor-public-20260824-v1"]
    status: Literal["PUBLIC_OFFLINE_WORKFLOW_SUCCESSORS_QUALIFIED_LIVE_CLOSED"]
    official: Literal[False]
    r9_diagnosis: FileBinding
    public_task_source: FileBinding
    source_files: tuple[FileBinding, ...]
    runtime_versions: tuple[Literal["lean-harness-v9", "lean-harness-v10"], ...]
    tool_schema_versions: tuple[Literal["v13", "v14"], ...]
    context_policy_versions: tuple[Literal["phase-evidence-v19", "phase-evidence-v20"], ...]
    scenarios: tuple[QualificationScenario, ...] = Field(min_length=14, max_length=14)
    scenario_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    r9_artifact_modified: Literal[False]
    v8_runtime_modified: Literal[False]
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
        if self.r9_diagnosis.path != R9_DIAGNOSIS_PATH.as_posix():
            raise ValueError("workflow qualification R9 diagnosis path differs")
        if self.public_task_source.path != PUBLIC_TASK_PATH.as_posix():
            raise ValueError("workflow qualification public task path differs")
        if tuple(item.path for item in self.source_files) != SOURCE_FILES:
            raise ValueError("workflow qualification source inventory differs")
        if self.runtime_versions != ("lean-harness-v9", "lean-harness-v10"):
            raise ValueError("workflow qualification runtime order differs")
        if self.tool_schema_versions != ("v13", "v14"):
            raise ValueError("workflow qualification tool schema order differs")
        if self.context_policy_versions != (
            "phase-evidence-v19",
            "phase-evidence-v20",
        ):
            raise ValueError("workflow qualification context policy order differs")
        if tuple(item.scenario_id for item in self.scenarios) != SCENARIO_IDS:
            raise ValueError("workflow qualification scenario inventory differs")
        scenario_payload = [item.model_dump(mode="json") for item in self.scenarios]
        if self.scenario_set_hash != sha256_json(scenario_payload):
            raise ValueError("workflow qualification scenario set differs")
        expected_hash = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected_hash:
            raise ValueError("workflow qualification content hash differs")
        return self


def _binding(root: Path, relative: str | Path) -> FileBinding:
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


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict[str, Any],
) -> RunEvent:
    return RunEvent(
        event_id=f"workflow-successor-qualification-{sequence}",
        run_id=_RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 24, tzinfo=UTC),
        actor="offline-qualification",
        payload=payload,
    )


def _task(root: Path) -> PublicTask:
    return PublicTask.model_validate(
        load_unique_yaml((root / PUBLIC_TASK_PATH).read_text(encoding="utf-8"))
    )


def _evidence(
    task: PublicTask,
    *,
    mutation: bool = True,
    completed: tuple[str, ...] = (),
    review_sequence: int | None = None,
    review_presented: bool = False,
    diff_hash: str = _DIFF_HASH,
) -> EvidenceState:
    check_ids = tuple(check.id for check in task.visible_checks)
    return EvidenceState(
        worktree_diff_hash=diff_hash,
        mutation_event_sequence=1 if mutation else None,
        mutation_present=mutation,
        completed_checks=completed,
        pending_checks=tuple(item for item in check_ids if item not in completed),
        current_diff_check_event_sequences=(),
        latest_check_sequence=None,
        review_event_sequence=review_sequence,
        review_presented_to_model=review_presented,
        task_review_event_sequence=None,
        task_review_presented_to_model=False,
        task_review_coverage_complete=None,
        unresolved_coverage_target_ids=(),
        submission_ready=False,
        missing_evidence=(),
        allowed_next_actions=(
            "search_files",
            "read_file",
            "apply_patch",
            "apply_structured_edit",
            "run_check",
        ),
    )


def _project(
    task: PublicTask,
    events: tuple[RunEvent, ...],
    *,
    runtime: Literal["lean-harness-v9", "lean-harness-v10"] = "lean-harness-v9",
    evidence: EvidenceState | None = None,
):
    schemas = TOOL_SCHEMAS_V13 if runtime == "lean-harness-v9" else TOOL_SCHEMAS_V14
    return project_workflow_successor(
        runtime_policy_version=runtime,
        task=task,
        evidence=evidence or _evidence(task),
        events=events,
        available_tool_names=tuple(item["name"] for item in schemas),
        configured_max_output_tokens=25_000,
    )


def _context() -> BuiltContext:
    payload = {
        "task": {"id": "anyio-interrupt-runner-cleanup", "version": 4},
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


def _assembled_request(
    root: Path,
    task: PublicTask,
    *,
    runtime: Literal["lean-harness-v9", "lean-harness-v10"],
) -> LeanHarnessRequestEvidenceV9 | LeanHarnessRequestEvidenceV10:
    context = _context()
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
    if runtime == "lean-harness-v9":
        events = (
            _event(
                1,
                EventType.PATCH_APPLIED,
                {"worktree_diff_hash": _DIFF_HASH},
            ),
        )
        phase = diff_bound_evidence(
            task,
            events,
            _DIFF_HASH,
            phase=Phase.IMPLEMENT,
            completion_driven=True,
        )
        schemas = TOOL_SCHEMAS_V13
    else:
        events = ()
        phase = diff_bound_evidence(
            task,
            events,
            _EMPTY_DIFF_HASH,
            phase=Phase.REPRODUCE,
            completion_driven=True,
        )
        schemas = TOOL_SCHEMAS_V14
    assembled = assemble_lean_harness_request(
        dependencies=load_lean_harness_dependencies(root),
        built_context=context,
        normalized_no_memory_context=context,
        base_tool_schemas=schemas,
        phase_evidence=phase,
        events=events,
        usage=Usage(),
        budget=_budget(),
        model_id="patchloop-public-calibration-mock-v1",
        system_prompt="public offline workflow qualification prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=runtime,
        task=task,
    )
    evidence = assembled.evidence
    if runtime == "lean-harness-v9" and type(evidence) is not LeanHarnessRequestEvidenceV9:
        raise TypeError("workflow qualification did not assemble exact V9 evidence")
    if runtime == "lean-harness-v10" and type(evidence) is not LeanHarnessRequestEvidenceV10:
        raise TypeError("workflow qualification did not assemble exact V10 evidence")
    return evidence


def build_workflow_successor_qualification(
    root: str | Path,
) -> WorkflowSuccessorQualification:
    repository = Path(root).resolve()
    task = _task(repository)
    first_check, upstream_check = (check.id for check in task.visible_checks)
    patch = _event(
        1,
        EventType.PATCH_APPLIED,
        {"worktree_diff_hash": _DIFF_HASH},
    )
    failed = _event(
        2,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "run_check",
            "check_id": first_check,
            "passed": False,
            "worktree_diff_hash": _DIFF_HASH,
        },
    )
    searches = (
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {"tool": "search_files", "worktree_diff_hash": _DIFF_HASH},
        ),
        _event(
            4,
            EventType.TOOL_SUCCEEDED,
            {"tool": "search_files", "worktree_diff_hash": _DIFF_HASH},
        ),
    )
    forced_read = _project(task, (patch, failed, *searches))
    read = _event(
        5,
        EventType.TOOL_SUCCEEDED,
        {"tool": "read_file", "worktree_diff_hash": _DIFF_HASH},
    )
    forced_edit = _project(task, (patch, failed, *searches, read))
    rejection = _event(
        6,
        EventType.TOOL_FAILED,
        {"tool": "apply_structured_edit", "worktree_diff_hash": _DIFF_HASH},
    )
    reread = _project(task, (patch, failed, read, rejection))

    correction_events: list[RunEvent] = [patch]
    sequence = 2
    for _ in range(3):
        correction_events.extend(
            [
                _event(
                    sequence,
                    EventType.TOOL_SUCCEEDED,
                    {
                        "tool": "run_check",
                        "check_id": first_check,
                        "passed": False,
                        "worktree_diff_hash": _DIFF_HASH,
                    },
                ),
                _event(
                    sequence + 1,
                    EventType.PATCH_APPLIED,
                    {"worktree_diff_hash": _DIFF_HASH},
                ),
            ]
        )
        sequence += 2
    correction_events.append(
        _event(
            sequence,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": first_check,
                "passed": False,
                "worktree_diff_hash": _DIFF_HASH,
            },
        )
    )
    correction_limit = _project(task, tuple(correction_events))

    checks = (first_check, upstream_check)
    review = _project(
        task,
        (
            patch,
            _event(
                4,
                EventType.TOOL_SUCCEEDED,
                {"tool": "get_diff", "worktree_diff_hash": _DIFF_HASH},
            ),
        ),
        evidence=_evidence(
            task,
            completed=checks,
            review_sequence=4,
            review_presented=True,
        ),
    )
    recovery = _project(
        task,
        (
            _event(
                1,
                EventType.TOOL_ADMISSION_BLOCKED,
                {
                    "policy_version": PROTOCOL_RECOVERY_POLICY,
                    "reason_code": "multiple_tool_calls",
                },
            ),
        ),
        evidence=_evidence(
            task,
            mutation=False,
            diff_hash=_EMPTY_DIFF_HASH,
        ),
    )

    task_spec = project_public_task_spec(task)
    preplan = _project(
        task,
        (),
        runtime="lean-harness-v10",
        evidence=_evidence(
            task,
            mutation=False,
            diff_hash=_EMPTY_DIFF_HASH,
        ),
    )
    plan_read = _event(
        1,
        EventType.TOOL_SUCCEEDED,
        {"tool": "read_file", "worktree_diff_hash": _EMPTY_DIFF_HASH},
    )
    plan_arguments = {
        "reproduction_status": "static_evidence",
        "hypothesis": "The public lifecycle source needs one bounded correction.",
        "evidence_event_sequences": [1],
        "candidate_files": ["src/anyio/pytest_plugin.py"],
        "planned_check_ids": list(checks),
        "unknowns": [],
    }
    plan = validate_record_work_plan(
        run_id=_RUN_ID,
        task=task,
        worktree_diff_hash=_EMPTY_DIFF_HASH,
        events=(plan_read,),
        read_paths_by_sequence={1: "src/anyio/pytest_plugin.py"},
        arguments=plan_arguments,
    )
    stale_rejected = False
    try:
        validate_record_work_plan(
            run_id=_RUN_ID,
            task=task,
            worktree_diff_hash=_DIFF_HASH,
            events=(plan_read,),
            read_paths_by_sequence={1: "src/anyio/pytest_plugin.py"},
            arguments=plan_arguments,
        )
    except ContractError:
        stale_rejected = True
    plan_event = _event(
        2,
        EventType.PLAN_RECORDED,
        {
            "schema_version": PLAN_RECORDED_EVENT_SCHEMA,
            "task_id": plan.task_id,
            "task_version": plan.task_version,
            "public_task_hash": plan.public_task_hash,
            "worktree_diff_hash": plan.worktree_diff_hash,
            "plan_hash": plan.content_hash,
        },
    )
    planned_patch = _event(
        3,
        EventType.PATCH_APPLIED,
        {"worktree_diff_hash": _DIFF_HASH, "plan_hash": plan.content_hash},
    )
    propagated = _project(
        task,
        (plan_read, plan_event, planned_patch),
        runtime="lean-harness-v10",
        evidence=_evidence(task),
    )

    v9_request = _assembled_request(repository, task, runtime="lean-harness-v9")
    v10_request = _assembled_request(repository, task, runtime="lean-harness-v10")
    scenarios = (
        _scenario(
            "v9-first-visible-check-bound",
            {
                "target": _project(task, (patch,)).target,
                "expected_check_id": _project(task, (patch,)).expected_check_id,
                "upstream_available": False,
            },
        ),
        _scenario(
            "v9-third-investigation-forces-read",
            {
                "target": forced_read.target,
                "allowed_tool_names": list(forced_read.allowed_tool_names),
                "information_actions": forced_read.information_actions_in_episode,
            },
        ),
        _scenario(
            "v9-third-investigation-then-edit",
            {
                "target": forced_edit.target,
                "allowed_tool_names": list(forced_edit.allowed_tool_names),
                "fresh_current_read": forced_edit.fresh_current_read,
            },
        ),
        _scenario(
            "v9-edit-rejection-requires-reread",
            {
                "allowed_tool_names": list(reread.allowed_tool_names),
                "fresh_current_read": reread.fresh_current_read,
            },
        ),
        _scenario(
            "v9-correction-attempt-limit",
            {
                "target": correction_limit.target,
                "terminal_reason": correction_limit.terminal_reason,
                "provider_tools": list(correction_limit.allowed_tool_names),
            },
        ),
        _scenario(
            "v9-review-repair-surface",
            {
                "target": review.target,
                "allowed_tool_names": list(review.allowed_tool_names),
                "review_corrections_used": review.review_corrections_used,
            },
        ),
        _scenario(
            "v9-shared-recovery-reconstructed",
            {
                "shared_recovery_used": recovery.shared_recovery_used,
                "shared_recovery_remaining": recovery.shared_recovery_remaining,
            },
        ),
        _scenario(
            "v10-public-task-spec",
            {
                "visible_check_ids": list(task_spec.visible_check_ids),
                "hidden_acceptance_used": task_spec.hidden_acceptance_used,
                "private_spec_used": task_spec.private_spec_used,
                "reference_patch_used": task_spec.reference_patch_used,
            },
        ),
        _scenario(
            "v10-mutation-hidden-before-plan",
            {
                "target": preplan.target,
                "allowed_tool_names": list(preplan.allowed_tool_names),
                "mutation_available": "apply_structured_edit" in preplan.allowed_tool_names,
            },
        ),
        _scenario(
            "v10-static-plan-validated",
            {
                "plan_hash": plan.content_hash,
                "reproduction_status": plan.reproduction_status,
                "candidate_files": list(plan.candidate_files),
                "planned_check_ids": list(plan.planned_check_ids),
            },
        ),
        _scenario(
            "v10-stale-evidence-rejected",
            {"rejected": stale_rejected, "current_diff_hash": _DIFF_HASH},
        ),
        _scenario(
            "v10-plan-propagates-through-mutation",
            {
                "plan_hash": propagated.plan_hash,
                "expected_check_id": propagated.expected_check_id,
                "target": propagated.target,
            },
        ),
        _scenario(
            "v9-request-assembled",
            {
                "schema_version": v9_request.schema_version,
                "runtime_policy_version": v9_request.runtime_policy_version,
                "tool_schema_version": v9_request.tool_schema_version,
                "context_policy_version": v9_request.context_policy_version,
                "parallel_tool_calls": v9_request.parallel_tool_calls,
                "one_tool_call_per_response": v9_request.one_tool_call_per_response,
            },
        ),
        _scenario(
            "v10-request-assembled",
            {
                "schema_version": v10_request.schema_version,
                "runtime_policy_version": v10_request.runtime_policy_version,
                "tool_schema_version": v10_request.tool_schema_version,
                "context_policy_version": v10_request.context_policy_version,
                "public_task_spec_hash": v10_request.public_task_spec_hash,
                "parallel_tool_calls": v10_request.parallel_tool_calls,
                "one_tool_call_per_response": v10_request.one_tool_call_per_response,
            },
        ),
    )
    body = {
        "schema_version": "lean-workflow-successor-qualification-v1",
        "qualification_id": "lean-workflow-successor-public-20260824-v1",
        "status": "PUBLIC_OFFLINE_WORKFLOW_SUCCESSORS_QUALIFIED_LIVE_CLOSED",
        "official": False,
        "r9_diagnosis": _binding(repository, R9_DIAGNOSIS_PATH).model_dump(mode="json"),
        "public_task_source": _binding(repository, PUBLIC_TASK_PATH).model_dump(mode="json"),
        "source_files": [
            _binding(repository, path).model_dump(mode="json") for path in SOURCE_FILES
        ],
        "runtime_versions": ["lean-harness-v9", "lean-harness-v10"],
        "tool_schema_versions": ["v13", "v14"],
        "context_policy_versions": ["phase-evidence-v19", "phase-evidence-v20"],
        "scenarios": [item.model_dump(mode="json") for item in scenarios],
        "scenario_set_hash": sha256_json([item.model_dump(mode="json") for item in scenarios]),
        "r9_artifact_modified": False,
        "v8_runtime_modified": False,
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
    return WorkflowSuccessorQualification.model_validate_json(
        canonical_json({**body, "content_hash": sha256_json(body)})
    )


def qualification_bytes(qualification: WorkflowSuccessorQualification) -> bytes:
    return (canonical_json(qualification.model_dump(mode="json")) + "\n").encode("utf-8")


def load_workflow_successor_qualification(
    root: str | Path,
) -> WorkflowSuccessorQualification:
    repository = Path(root).resolve()
    stored = WorkflowSuccessorQualification.model_validate_json(
        (repository / QUALIFICATION_PATH).read_text(encoding="utf-8")
    )
    current = build_workflow_successor_qualification(repository)
    if stored != current or qualification_bytes(stored) != qualification_bytes(current):
        raise ContractError("workflow successor qualification source differs")
    return stored


__all__ = [
    "QUALIFICATION_PATH",
    "SCENARIO_IDS",
    "SOURCE_FILES",
    "WorkflowSuccessorQualification",
    "build_workflow_successor_qualification",
    "load_workflow_successor_qualification",
    "qualification_bytes",
]
