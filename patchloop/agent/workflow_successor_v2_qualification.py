"""Deterministic public-only qualification for Lean workflow V11 and V12.

The builder exercises pure public event projection, request assembly, plan
admission, revision recovery, and durable work-state reconstruction.  It never
dispatches a provider, Docker, a registered visible check, or an evaluator and
does not mutate a task repository.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from patchloop.agent.context import BuiltContext
from patchloop.agent.lean_runtime import (
    LeanHarnessRequestEvidenceV11,
    LeanHarnessRequestEvidenceV12,
    assemble_lean_harness_request,
    load_lean_harness_dependencies,
)
from patchloop.agent.phases import EvidenceState, diff_bound_evidence
from patchloop.agent.tools import TOOL_SCHEMAS_V15, TOOL_SCHEMAS_V16
from patchloop.agent.workflow_successor_v2 import (
    PLAN_RECORDED_EVENT_SCHEMA_V2,
    WORK_PLAN_ADMISSION_POLICY,
    EligiblePlanEvidenceCatalog,
    RecordedWorkPlanV2,
    project_active_work_state,
    project_eligible_plan_evidence_catalog,
    project_workflow_successor_v2,
    project_workflow_tool_surface_v2,
    validate_work_plan_v2,
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
from patchloop.errors import ContractError, RecoveryError
from patchloop.memory.fixed_bundle import build_fixed_memory_delivery
from patchloop.util import (
    canonical_json,
    load_unique_yaml,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

QUALIFICATION_PATH = Path(
    "experiments/lean-harness-workflow-successor-v2-public-qualification-20260825-v1.json"
)
PUBLIC_TASK_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml")
IMMUTABLE_PREDECESSOR_FILES = (
    "patchloop/agent/completion_loop_successor.py",
    "patchloop/agent/workflow_successor.py",
    "experiments/lean-harness-workflow-successor-public-qualification-20260824-v1.json",
    "reports/rapid-development/rapid-public-dev-anyio-ordered-correction-20260824-r9-db9e887fea43.jsonl",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-ordered-correction-20260824-r9-workflow-diagnosis-v1.json",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-ordered-correction-20260824-r9-candidate-v13.json",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-ordered-correction-20260824-r9-candidate-v13-rehearsal-v10.json",
    "reports/rapid-development/rapid-public-dev-anyio-workflow-ab-20260824-r10-cbe3f560b03b.jsonl",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-ab-20260824-r10-workflow-diagnosis-v1.json",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-ab-20260824-r10-candidate-v16.json",
    "reports/rapid-development/artifacts/rapid-public-dev-anyio-workflow-ab-20260824-r10-candidate-v16-rehearsal-v13.json",
)
SOURCE_FILES = (
    "patchloop/agent/workflow_successor_v2_qualification.py",
    "patchloop/agent/workflow_successor_v2.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/state/store.py",
    "patchloop/contracts.py",
    "patchloop/errors.py",
    "scripts/build_lean_harness_workflow_successor_v2_qualification.py",
    "tests/test_workflow_successor_v2.py",
    "tests/test_workflow_successor_v2_runner.py",
    "tests/test_workflow_successor_v2_qualification.py",
)
SCENARIO_IDS = (
    "v11-visible-source-and-typed-check-catalog",
    "v11-r10-failed-plan-one-shot",
    "v11-r10-passed-plan-one-shot",
    "v11-r10-static-plan-one-shot",
    "v11-search-stale-timeout-and-failure-excluded",
    "v11-truncated-read-visible-range",
    "v11-exact-replay-canonicalized",
    "v11-dynamic-enum-and-candidate-binding",
    "v11-first-admission-recovery",
    "v11-second-admission-terminal",
    "v11-request-assembled",
    "v12-failed-check-requires-revision",
    "v12-linked-revision-and-pinned-active-state",
    "v12-edit-rejection-reread-without-revision",
    "v12-review-correction-requires-revision",
    "v12-tampered-chain-fails-closed",
    "v12-request-assembled",
)

_RUN_ID = "workflow-successor-v2-offline-qualification"
_EMPTY_DIFF_HASH = sha256_text("")
_DIFF_HASH = sha256_text("workflow-successor-v2-qualified-diff")
_SOURCE_PATH = "src/anyio/pytest_plugin.py"


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
            raise ValueError("workflow v2 qualification observation hash differs")
        return self


class WorkflowSuccessorV2Qualification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["lean-workflow-successor-v2-qualification-v1"]
    qualification_id: Literal["lean-workflow-successor-v2-public-20260825-v1"]
    status: Literal["PUBLIC_OFFLINE_V11_V12_QUALIFIED_LIVE_CLOSED"]
    official: Literal[False]
    public_task_source: FileBinding
    immutable_predecessors: tuple[FileBinding, ...]
    source_files: tuple[FileBinding, ...]
    runtime_versions: tuple[Literal["lean-harness-v11", "lean-harness-v12"], ...]
    tool_schema_versions: tuple[Literal["v15", "v16"], ...]
    context_policy_versions: tuple[Literal["phase-evidence-v21", "phase-evidence-v22"], ...]
    scenarios: tuple[QualificationScenario, ...] = Field(min_length=17, max_length=17)
    scenario_set_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    predecessor_files_modified: Literal[False]
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
        if self.public_task_source.path != PUBLIC_TASK_PATH.as_posix():
            raise ValueError("workflow v2 qualification public task differs")
        if tuple(item.path for item in self.immutable_predecessors) != (
            IMMUTABLE_PREDECESSOR_FILES
        ):
            raise ValueError("workflow v2 predecessor inventory differs")
        if tuple(item.path for item in self.source_files) != SOURCE_FILES:
            raise ValueError("workflow v2 source inventory differs")
        if self.runtime_versions != ("lean-harness-v11", "lean-harness-v12"):
            raise ValueError("workflow v2 runtime order differs")
        if self.tool_schema_versions != ("v15", "v16"):
            raise ValueError("workflow v2 tool schema order differs")
        if self.context_policy_versions != ("phase-evidence-v21", "phase-evidence-v22"):
            raise ValueError("workflow v2 context policy order differs")
        if tuple(item.scenario_id for item in self.scenarios) != SCENARIO_IDS:
            raise ValueError("workflow v2 scenario inventory differs")
        scenario_payload = [item.model_dump(mode="json") for item in self.scenarios]
        if self.scenario_set_hash != sha256_json(scenario_payload):
            raise ValueError("workflow v2 scenario set differs")
        expected = sha256_json(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash != expected:
            raise ValueError("workflow v2 qualification content hash differs")
        return self


def _binding(root: Path, relative: str | Path) -> FileBinding:
    path = Path(relative)
    raw = (root / path).read_bytes()
    return FileBinding(path=path.as_posix(), bytes=len(raw), file_sha256=sha256_bytes(raw))


def _scenario(scenario_id: str, observed: dict[str, Any]) -> QualificationScenario:
    return QualificationScenario(
        scenario_id=scenario_id,
        observed=observed,
        observation_hash=sha256_json(observed),
    )


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict[str, Any] | None = None,
    *,
    correlation_id: str | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"workflow-successor-v2-qualification-{sequence}",
        run_id=_RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 25, tzinfo=UTC),
        actor="offline-qualification",
        correlation_id=correlation_id,
        payload=payload or {},
    )


def _public_result(
    sequence: int,
    tool: str,
    tool_result: dict[str, Any],
    *,
    diff_hash: str,
    event_type: EventType = EventType.TOOL_SUCCEEDED,
    correlation_id: str | None = None,
) -> tuple[RunEvent, dict[str, Any]]:
    artifact = {
        "artifact_id": f"workflow-v2-artifact-{sequence}",
        "path": f"cas/workflow-v2/{sequence}.json",
        "content_hash": sha256_json(tool_result),
    }
    status = "succeeded" if event_type == EventType.TOOL_SUCCEEDED else "rejected"
    durable = _event(
        sequence,
        event_type,
        {
            "tool": tool,
            "status": status,
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
        correlation_id=correlation_id,
    )
    visible = {
        "sequence": sequence,
        "type": event_type.value,
        "payload": {
            "tool": tool,
            "status": status,
            "artifact_id": artifact["artifact_id"],
            "artifact_path": artifact["path"],
            "tool_result": tool_result,
        },
    }
    return durable, visible


def _read_result(*, truncated: bool = False) -> dict[str, Any]:
    content = "line 20\nline 21\n"
    if truncated:
        content += "\n...[field truncated for model context]"
    return {
        "path": _SOURCE_PATH,
        "content": content,
        "start_line": 20,
        "end_line": 120,
        "actual_start_line": 20,
        "actual_end_line": 120 if truncated else 21,
        "total_lines": 500,
        "file_content_hash": sha256_text("qualified-public-source"),
    }


def _check_result(task: PublicTask, *, passed: bool, timed_out: bool = False) -> dict[str, Any]:
    return {
        "check_id": task.visible_checks[0].id,
        "invocation_status": "timed_out" if timed_out else "completed",
        "behavior_status": "not_observed" if timed_out else ("passed" if passed else "failed"),
        "passed": passed,
        "timed_out": timed_out,
    }


def _catalog(
    task: PublicTask,
    pairs: tuple[tuple[RunEvent, dict[str, Any]], ...],
    *,
    diff_hash: str,
    events: tuple[RunEvent, ...] | None = None,
) -> EligiblePlanEvidenceCatalog:
    durable = events or tuple(pair[0] for pair in pairs)
    context = canonical_json({"recent_events": [pair[1] for pair in pairs]})
    return project_eligible_plan_evidence_catalog(
        run_id=_RUN_ID,
        task=task,
        worktree_diff_hash=diff_hash,
        model_visible_context=context,
        events=durable,
    )


def _evidence(
    task: PublicTask,
    *,
    diff_hash: str,
    mutation: bool,
    completed: tuple[str, ...] = (),
    mutation_sequence: int | None = None,
    review_sequence: int | None = None,
    review_presented: bool = False,
) -> EvidenceState:
    check_order = tuple(check.id for check in task.visible_checks)
    return EvidenceState(
        worktree_diff_hash=diff_hash,
        mutation_event_sequence=mutation_sequence if mutation else None,
        mutation_present=mutation,
        completed_checks=completed,
        pending_checks=tuple(item for item in check_order if item not in completed),
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
            "apply_structured_edit",
            "run_check",
        ),
    )


def _plan_arguments(
    catalog: EligiblePlanEvidenceCatalog,
    *,
    status: str,
    disposition: str | None = None,
) -> dict[str, Any]:
    source = next(item for item in catalog.items if item.kind == "source_read")
    body: dict[str, Any] = {
        "observation_status": status,
        "hypothesis": "Public interruption cleanup state remains reachable.",
        "foundation_evidence_ids": [
            item.evidence_id for item in catalog.items if item.role == "foundation"
        ],
        "supporting_evidence_ids": [
            item.evidence_id for item in catalog.items if item.role == "support"
        ],
        "candidate_files": [{"path": _SOURCE_PATH, "read_evidence_id": source.evidence_id}],
        "intended_change": "Bound cleanup to the public interruption lifecycle.",
        "expected_behavior": "Interrupted execution cannot resume and cleanup runs once.",
        "unknowns": [],
    }
    if disposition is not None:
        body["prior_hypothesis_disposition"] = disposition
    return body


def _validate_initial_plan(
    task: PublicTask,
    catalog: EligiblePlanEvidenceCatalog,
    status: str,
) -> RecordedWorkPlanV2:
    return validate_work_plan_v2(
        task=task,
        catalog=catalog,
        arguments=_plan_arguments(catalog, status=status),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
    )


def _plan_event(sequence: int, plan: RecordedWorkPlanV2) -> RunEvent:
    return _event(
        sequence,
        EventType.PLAN_RECORDED,
        {
            "schema_version": PLAN_RECORDED_EVENT_SCHEMA_V2,
            "plan_hash": plan.content_hash,
            "worktree_diff_hash": plan.worktree_diff_hash,
            "revision_index": plan.revision_index,
            "parent_plan_hash": plan.parent_plan_hash,
            "trigger": plan.trigger,
            "plan": plan.model_dump(mode="json"),
        },
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
    runtime: Literal["lean-harness-v11", "lean-harness-v12"],
) -> LeanHarnessRequestEvidenceV11 | LeanHarnessRequestEvidenceV12:
    context = _context()
    events = (_event(1, EventType.RUN_STARTED, {"official": False}),)
    phase = diff_bound_evidence(
        task,
        events,
        _EMPTY_DIFF_HASH,
        phase=Phase.REPRODUCE,
        completion_driven=True,
    )
    schemas = TOOL_SCHEMAS_V15 if runtime == "lean-harness-v11" else TOOL_SCHEMAS_V16
    delivery = build_fixed_memory_delivery(
        condition=MemoryCondition.NO_MEMORY,
        token_budget=2_000,
    )
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
        system_prompt="public offline workflow v2 qualification prompt",
        configured_max_output_tokens=25_000,
        memory_delivery_evidence_sha256=delivery.evidence_sha256,
        runtime_policy_version=runtime,
        task=task,
    )
    evidence = assembled.evidence
    if runtime == "lean-harness-v11" and type(evidence) is not LeanHarnessRequestEvidenceV11:
        raise TypeError("workflow v2 qualification did not assemble exact V11 evidence")
    if runtime == "lean-harness-v12" and type(evidence) is not LeanHarnessRequestEvidenceV12:
        raise TypeError("workflow v2 qualification did not assemble exact V12 evidence")
    return evidence


def build_workflow_successor_v2_qualification(
    root: str | Path,
) -> WorkflowSuccessorV2Qualification:
    repository = Path(root).resolve()
    task = PublicTask.model_validate(
        load_unique_yaml((repository / PUBLIC_TASK_PATH).read_text(encoding="utf-8"))
    )
    available_v11 = tuple(schema["name"] for schema in TOOL_SCHEMAS_V15)
    available_v12 = tuple(schema["name"] for schema in TOOL_SCHEMAS_V16)

    read = _public_result(1, "read_file", _read_result(), diff_hash=_EMPTY_DIFF_HASH)
    failed = _public_result(
        2,
        "run_check",
        _check_result(task, passed=False),
        diff_hash=_EMPTY_DIFF_HASH,
    )
    passed = _public_result(
        2,
        "run_check",
        _check_result(task, passed=True),
        diff_hash=_EMPTY_DIFF_HASH,
    )
    failed_catalog = _catalog(task, (read, failed), diff_hash=_EMPTY_DIFF_HASH)
    passed_catalog = _catalog(task, (read, passed), diff_hash=_EMPTY_DIFF_HASH)
    static_catalog = _catalog(task, (read,), diff_hash=_EMPTY_DIFF_HASH)
    failed_plan = _validate_initial_plan(task, failed_catalog, "targeted_check_failed")
    passed_plan = _validate_initial_plan(task, passed_catalog, "targeted_check_passed")
    static_plan = _validate_initial_plan(task, static_catalog, "static_source")

    search = _public_result(
        3,
        "search_files",
        {"query": "cancel", "path_glob": "src/**/*.py", "matches": [], "truncated": False},
        diff_hash=_EMPTY_DIFF_HASH,
    )
    stale = _public_result(4, "read_file", _read_result(), diff_hash=_DIFF_HASH)
    timeout = _public_result(
        5,
        "run_check",
        _check_result(task, passed=False, timed_out=True),
        diff_hash=_EMPTY_DIFF_HASH,
    )
    failed_tool = _public_result(
        6,
        "read_file",
        _read_result(),
        diff_hash=_EMPTY_DIFF_HASH,
        event_type=EventType.TOOL_FAILED,
    )
    excluded_catalog = _catalog(
        task,
        (search, stale, timeout, failed_tool),
        diff_hash=_EMPTY_DIFF_HASH,
    )

    truncated = _public_result(
        7,
        "read_file",
        _read_result(truncated=True),
        diff_hash=_EMPTY_DIFF_HASH,
    )
    truncated_catalog = _catalog(task, (truncated,), diff_hash=_EMPTY_DIFF_HASH)

    replay_call = _event(
        8,
        EventType.TOOL_CALLED,
        {"tool": "read_file", "input_hash": sha256_text("qualified-read-input")},
        correlation_id="qualified-read",
    )
    replay_source = _public_result(
        9,
        "read_file",
        _read_result(),
        diff_hash=_EMPTY_DIFF_HASH,
        correlation_id="qualified-read",
    )
    replay_event = _event(
        10,
        EventType.TOOL_REPLAYED,
        {
            **replay_source[0].payload,
            "status": "succeeded",
            "input_hash": sha256_text("qualified-read-input"),
        },
        correlation_id="qualified-read",
    )
    replay_visible = {
        **replay_source[1],
        "sequence": 10,
        "type": EventType.TOOL_REPLAYED.value,
    }
    replay_catalog = _catalog(
        task,
        (replay_source, (replay_event, replay_visible)),
        diff_hash=_EMPTY_DIFF_HASH,
        events=(replay_call, replay_source[0], replay_event),
    )

    v11_decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v11",
        run_id=_RUN_ID,
        task=task,
        evidence=_evidence(task, diff_hash=_EMPTY_DIFF_HASH, mutation=False),
        events=(read[0], failed[0]),
        catalog=failed_catalog,
        available_tool_names=available_v11,
        configured_max_output_tokens=25_000,
    )
    surface = project_workflow_tool_surface_v2(
        decision=v11_decision,
        catalog=failed_catalog,
        source_tool_schemas=TOOL_SCHEMAS_V15,
    )
    plan_schema = next(
        schema for schema in surface.selected_tool_schemas if schema["name"] == "record_work_plan"
    )
    invalid_candidate_rejected = False
    invalid = _plan_arguments(failed_catalog, status="targeted_check_failed")
    invalid["candidate_files"][0]["read_evidence_id"] = failed_catalog.items[-1].evidence_id
    try:
        validate_work_plan_v2(
            task=task,
            catalog=failed_catalog,
            arguments=invalid,
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
        )
    except ContractError:
        invalid_candidate_rejected = True
    if not invalid_candidate_rejected:
        raise ContractError("workflow v2 qualification accepted an invalid candidate binding")

    assert v11_decision.plan_gate_id is not None
    first_block = _event(
        3,
        EventType.TOOL_ADMISSION_BLOCKED,
        {
            "policy_version": WORK_PLAN_ADMISSION_POLICY,
            "plan_gate_id": v11_decision.plan_gate_id,
            "reason_code": "foundation_evidence_ineligible",
        },
    )
    after_first_block = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v11",
        run_id=_RUN_ID,
        task=task,
        evidence=_evidence(task, diff_hash=_EMPTY_DIFF_HASH, mutation=False),
        events=(read[0], failed[0], first_block),
        catalog=failed_catalog,
        available_tool_names=available_v11,
        configured_max_output_tokens=25_000,
    )
    second_block = _event(
        4,
        EventType.TOOL_ADMISSION_BLOCKED,
        {
            "policy_version": WORK_PLAN_ADMISSION_POLICY,
            "plan_gate_id": v11_decision.plan_gate_id,
            "reason_code": "candidate_read_binding_invalid",
        },
    )
    after_second_block = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v11",
        run_id=_RUN_ID,
        task=task,
        evidence=_evidence(task, diff_hash=_EMPTY_DIFF_HASH, mutation=False),
        events=(read[0], failed[0], first_block, second_block),
        catalog=failed_catalog,
        available_tool_names=available_v11,
        configured_max_output_tokens=25_000,
    )

    initial_read = _public_result(11, "read_file", _read_result(), diff_hash=_EMPTY_DIFF_HASH)
    initial_catalog = _catalog(task, (initial_read,), diff_hash=_EMPTY_DIFF_HASH)
    initial_plan = _validate_initial_plan(task, initial_catalog, "static_source")
    initial_plan_event = _plan_event(12, initial_plan)
    patch_event = _event(
        13,
        EventType.PATCH_APPLIED,
        {"worktree_diff_hash": _DIFF_HASH, "plan_hash": initial_plan.content_hash},
    )
    correction_check = _public_result(
        14,
        "run_check",
        _check_result(task, passed=False),
        diff_hash=_DIFF_HASH,
    )
    correction_read = _public_result(15, "read_file", _read_result(), diff_hash=_DIFF_HASH)
    correction_events = (
        initial_read[0],
        initial_plan_event,
        patch_event,
        correction_check[0],
        correction_read[0],
    )
    correction_catalog = _catalog(
        task,
        (correction_check, correction_read),
        diff_hash=_DIFF_HASH,
        events=correction_events,
    )
    correction_decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v12",
        run_id=_RUN_ID,
        task=task,
        evidence=_evidence(
            task,
            diff_hash=_DIFF_HASH,
            mutation=True,
            mutation_sequence=13,
        ),
        events=correction_events,
        catalog=correction_catalog,
        available_tool_names=available_v12,
        configured_max_output_tokens=25_000,
    )
    revision = validate_work_plan_v2(
        task=task,
        catalog=correction_catalog,
        arguments=_plan_arguments(
            correction_catalog,
            status="visible_check_failed",
            disposition="refined",
        ),
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash=initial_plan.content_hash,
        trigger_check_id=task.visible_checks[0].id,
        trigger_event_sequence=14,
    )
    revision_event = _plan_event(16, revision)
    long_tail = tuple(
        _event(sequence, EventType.MODEL_CALLED, {"public": True}) for sequence in range(17, 32)
    )
    active = project_active_work_state(
        run_id=_RUN_ID,
        task=task,
        current_diff_hash=_DIFF_HASH,
        events=(*correction_events, revision_event, *long_tail),
    )
    if active is None:
        raise RecoveryError("workflow v2 qualification lost active work state")

    rejection = _event(
        17,
        EventType.TOOL_FAILED,
        {"tool": "apply_structured_edit", "worktree_diff_hash": _DIFF_HASH},
    )
    rejection_decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v12",
        run_id=_RUN_ID,
        task=task,
        evidence=_evidence(
            task,
            diff_hash=_DIFF_HASH,
            mutation=True,
            mutation_sequence=13,
        ),
        events=(*correction_events, revision_event, rejection),
        catalog=correction_catalog,
        available_tool_names=available_v12,
        configured_max_output_tokens=25_000,
    )

    review_diff_result = {
        "patch_hash": _DIFF_HASH,
        "worktree_diff_hash": _DIFF_HASH,
        "changed_files": [_SOURCE_PATH],
    }
    review_diff = _public_result(18, "get_diff", review_diff_result, diff_hash=_DIFF_HASH)
    review_read = _public_result(19, "read_file", _read_result(), diff_hash=_DIFF_HASH)
    review_events = (
        initial_read[0],
        initial_plan_event,
        patch_event,
        review_diff[0],
        review_read[0],
    )
    review_catalog = _catalog(
        task,
        (review_diff, review_read),
        diff_hash=_DIFF_HASH,
        events=review_events,
    )
    review_decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v12",
        run_id=_RUN_ID,
        task=task,
        evidence=_evidence(
            task,
            diff_hash=_DIFF_HASH,
            mutation=True,
            mutation_sequence=13,
            completed=tuple(check.id for check in task.visible_checks),
            review_sequence=18,
            review_presented=True,
        ),
        events=review_events,
        catalog=review_catalog,
        available_tool_names=available_v12,
        configured_max_output_tokens=25_000,
    )

    tampered_chain_rejected = False
    tampered_payload = revision_event.model_copy(deep=True).payload
    tampered_payload["parent_plan_hash"] = sha256_text("tampered-parent")
    tampered_event = _event(16, EventType.PLAN_RECORDED, tampered_payload)
    try:
        project_active_work_state(
            run_id=_RUN_ID,
            task=task,
            current_diff_hash=_DIFF_HASH,
            events=(*correction_events, tampered_event),
        )
    except RecoveryError:
        tampered_chain_rejected = True
    if not tampered_chain_rejected:
        raise ContractError("workflow v2 qualification accepted a tampered revision chain")

    v11_request = _assembled_request(repository, task, runtime="lean-harness-v11")
    v12_request = _assembled_request(repository, task, runtime="lean-harness-v12")
    plan_properties = plan_schema["parameters"]["properties"]
    truncated_source = truncated_catalog.items[0].source
    replay_item = replay_catalog.items[0]
    scenarios = (
        _scenario(
            "v11-visible-source-and-typed-check-catalog",
            {
                "kinds": [item.kind for item in failed_catalog.items],
                "roles": [item.role for item in failed_catalog.items],
                "check_status": failed_catalog.items[-1].check.behavior_status,
                "private_evidence_used": failed_catalog.private_evidence_used,
                "reasoning_text_used": failed_catalog.reasoning_text_used,
            },
        ),
        _scenario(
            "v11-r10-failed-plan-one-shot",
            {"plan_hash": failed_plan.content_hash, "status": failed_plan.observation_status},
        ),
        _scenario(
            "v11-r10-passed-plan-one-shot",
            {"plan_hash": passed_plan.content_hash, "status": passed_plan.observation_status},
        ),
        _scenario(
            "v11-r10-static-plan-one-shot",
            {"plan_hash": static_plan.content_hash, "status": static_plan.observation_status},
        ),
        _scenario(
            "v11-search-stale-timeout-and-failure-excluded",
            {
                "kinds": [item.kind for item in excluded_catalog.items],
                "foundation_count": sum(
                    item.role == "foundation" for item in excluded_catalog.items
                ),
                "support_count": sum(item.role == "support" for item in excluded_catalog.items),
            },
        ),
        _scenario(
            "v11-truncated-read-visible-range",
            {
                "visible_ranges": truncated_source.visible_ranges,
                "omitted_ranges": truncated_source.omitted_ranges,
                "partial_line": truncated_source.partial_line,
            },
        ),
        _scenario(
            "v11-exact-replay-canonicalized",
            {
                "evidence_id": replay_item.evidence_id,
                "visible_sequences": replay_item.model_visible_event_sequences,
                "replay_aliases": replay_item.replay_alias_event_sequences,
            },
        ),
        _scenario(
            "v11-dynamic-enum-and-candidate-binding",
            {
                "foundation_enum": plan_properties["foundation_evidence_ids"]["items"]["enum"],
                "candidate_path_enum": plan_properties["candidate_files"]["items"]["properties"][
                    "path"
                ]["enum"],
                "invalid_candidate_rejected": invalid_candidate_rejected,
            },
        ),
        _scenario(
            "v11-first-admission-recovery",
            {
                "target": after_first_block.target,
                "recovery_used": after_first_block.plan_admission_recovery_used,
                "recovery_remaining": after_first_block.plan_admission_recovery_remaining,
            },
        ),
        _scenario(
            "v11-second-admission-terminal",
            {
                "target": after_second_block.target,
                "terminal_reason": after_second_block.terminal_reason,
                "allowed_tools": after_second_block.allowed_tool_names,
            },
        ),
        _scenario(
            "v11-request-assembled",
            {
                "schema_version": v11_request.schema_version,
                "runtime_policy_version": v11_request.runtime_policy_version,
                "tool_schema_version": v11_request.tool_schema_version,
                "context_policy_version": v11_request.context_policy_version,
                "catalog_hash": v11_request.eligible_plan_evidence_catalog_hash,
                "parallel_tool_calls": v11_request.parallel_tool_calls,
            },
        ),
        _scenario(
            "v12-failed-check-requires-revision",
            {
                "target": correction_decision.target,
                "revision_trigger": correction_decision.revision_trigger,
                "required_evidence_id": correction_decision.required_trigger_evidence_id,
                "mutation_available": "apply_structured_edit"
                in correction_decision.allowed_tool_names,
            },
        ),
        _scenario(
            "v12-linked-revision-and-pinned-active-state",
            {
                "initial_plan_hash": active.initial_plan.content_hash,
                "latest_plan_hash": active.latest_plan.content_hash,
                "parent_plan_hash": revision.parent_plan_hash,
                "revision_index": revision.revision_index,
                "tail_events": len(long_tail),
                "chain_hash": active.chain_hash,
            },
        ),
        _scenario(
            "v12-edit-rejection-reread-without-revision",
            {
                "target": rejection_decision.target,
                "allowed_tools": rejection_decision.allowed_tool_names,
                "active_plan_hash": rejection_decision.active_plan_hash,
            },
        ),
        _scenario(
            "v12-review-correction-requires-revision",
            {
                "target": review_decision.target,
                "revision_trigger": review_decision.revision_trigger,
                "required_evidence_id": review_decision.required_trigger_evidence_id,
                "revision_available": "revise_work_plan" in review_decision.allowed_tool_names,
                "direct_mutation_available": "apply_structured_edit"
                in review_decision.allowed_tool_names,
            },
        ),
        _scenario(
            "v12-tampered-chain-fails-closed",
            {"tampered_chain_rejected": tampered_chain_rejected},
        ),
        _scenario(
            "v12-request-assembled",
            {
                "schema_version": v12_request.schema_version,
                "runtime_policy_version": v12_request.runtime_policy_version,
                "tool_schema_version": v12_request.tool_schema_version,
                "context_policy_version": v12_request.context_policy_version,
                "catalog_hash": v12_request.eligible_plan_evidence_catalog_hash,
                "active_work_state_hash": v12_request.active_work_state_hash,
                "parallel_tool_calls": v12_request.parallel_tool_calls,
            },
        ),
    )
    body = {
        "schema_version": "lean-workflow-successor-v2-qualification-v1",
        "qualification_id": "lean-workflow-successor-v2-public-20260825-v1",
        "status": "PUBLIC_OFFLINE_V11_V12_QUALIFIED_LIVE_CLOSED",
        "official": False,
        "public_task_source": _binding(repository, PUBLIC_TASK_PATH).model_dump(mode="json"),
        "immutable_predecessors": [
            _binding(repository, path).model_dump(mode="json")
            for path in IMMUTABLE_PREDECESSOR_FILES
        ],
        "source_files": [
            _binding(repository, path).model_dump(mode="json") for path in SOURCE_FILES
        ],
        "runtime_versions": ["lean-harness-v11", "lean-harness-v12"],
        "tool_schema_versions": ["v15", "v16"],
        "context_policy_versions": ["phase-evidence-v21", "phase-evidence-v22"],
        "scenarios": [item.model_dump(mode="json") for item in scenarios],
        "scenario_set_hash": sha256_json([item.model_dump(mode="json") for item in scenarios]),
        "predecessor_files_modified": False,
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
    return WorkflowSuccessorV2Qualification.model_validate_json(
        canonical_json({**body, "content_hash": sha256_json(body)})
    )


def qualification_bytes(qualification: WorkflowSuccessorV2Qualification) -> bytes:
    return (canonical_json(qualification.model_dump(mode="json")) + "\n").encode("utf-8")


def load_workflow_successor_v2_qualification(
    root: str | Path,
) -> WorkflowSuccessorV2Qualification:
    repository = Path(root).resolve()
    stored = WorkflowSuccessorV2Qualification.model_validate_json(
        (repository / QUALIFICATION_PATH).read_text(encoding="utf-8")
    )
    current = build_workflow_successor_v2_qualification(repository)
    if stored != current or qualification_bytes(stored) != qualification_bytes(current):
        raise ContractError("workflow successor v2 qualification source differs")
    return stored


__all__ = [
    "IMMUTABLE_PREDECESSOR_FILES",
    "QUALIFICATION_PATH",
    "SCENARIO_IDS",
    "SOURCE_FILES",
    "WorkflowSuccessorV2Qualification",
    "build_workflow_successor_v2_qualification",
    "load_workflow_successor_v2_qualification",
    "qualification_bytes",
]
