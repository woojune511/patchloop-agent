"""Zero-call qualification for one ordered three-check Lean V19 task surface."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from patchloop.agent.investigation import nominal_tail_reserve
from patchloop.agent.lean_runtime import (
    LEAN_CONTEXT_POLICY_VERSION_V19,
    LEAN_REQUEST_EVIDENCE_SCHEMA_V19,
    LEAN_RUNTIME_POLICY_VERSION_V19,
    LEAN_TOOL_SCHEMA_VERSION_V19,
)
from patchloop.agent.phases import diff_bound_evidence, validate_transition
from patchloop.agent.runner import AgentRunner
from patchloop.agent.tools import TOOL_SCHEMAS_V23
from patchloop.agent.workflow_causal_plan_projection_activation import (
    standard_plan_from_projected_causal_plan,
)
from patchloop.agent.workflow_exploration_gate_activation import (
    normalize_activated_exploration_plan,
    project_exploration_readiness_decision,
    project_exploration_workflow_tool_surface,
)
from patchloop.agent.workflow_semantic_progress_successor import (
    WorkflowDecisionV3,
    current_public_failure_event_sequence,
    project_public_semantic_progress_state,
    project_workflow_semantic_progress_successor,
)
from patchloop.agent.workflow_successor import project_public_task_spec
from patchloop.agent.workflow_successor_v2 import (
    EligiblePlanEvidence,
    EligiblePlanEvidenceCatalogV2,
    SearchEvidenceProjection,
    SourceEvidenceProjection,
    project_eligible_plan_evidence_catalog_v2,
)
from patchloop.contracts import EventType, Phase, PublicTask, RunEvent, ToolResult
from patchloop.errors import ContractError
from patchloop.util import (
    canonical_json,
    ensure_within,
    sha256_bytes,
    sha256_json,
    sha256_text,
)

SCHEMA_VERSION = "three-visible-check-runtime-compatibility-qualification-v1"
QUALIFICATION_PATH = Path(
    "experiments/anyio-v5-three-visible-check-runtime-compatibility-"
    "source-qualification-20260827-v1.json"
)
TASK_PUBLIC_PATH = Path("fixtures/task-packages/anyio-interrupt-runner-cleanup-v5/public.yaml")

EXPECTED_CHECK_ORDER = (
    "public-interrupt-runner-lifecycle",
    "public-ordinary-failure-preservation",
    "upstream-pytest-plugin-regression",
)
RUN_ID = "run_three_visible_check_source_qualification"
CURRENT_DIFF = sha256_json({"three_check_diff": 1})
CORRECTED_DIFF = sha256_json({"three_check_diff": 2})
SOURCE_PATH = "src/anyio/pytest_plugin.py"

IMMUTABLE_PREDECESSORS = {
    (
        "experiments/anyio-ordinary-failure-public-task-successor-"
        "source-qualification-20260827-v1.json"
    ): {
        "bytes": 7_838,
        "file_sha256": ("sha256:f0d0c375c37b6c601dcc5364e0294be0fa4b14576194bceb833aa674c59735bf"),
        "content_hash": ("sha256:5e5f1fd0db95cdf1221f11db0222a2b69aa39ddf36ba6755fd4b1f396216d489"),
    },
    "experiments/lean-harness-exploration-gate-activation-public-qualification-20260827-v1.json": {
        "bytes": 4_925,
        "file_sha256": ("sha256:a25881f54e66a11ef6f3ca9b41d0cf44ce7a37ec1b2fe7fd1efbade0994462c5"),
        "content_hash": ("sha256:1beb02b77f1b4d9985babe4e64dab4e09cc805bc87fabfa9733dec3f0d2bcb9a"),
    },
}

SOURCE_FILES = (
    TASK_PUBLIC_PATH.as_posix(),
    "patchloop/agent/phases.py",
    "patchloop/agent/runner.py",
    "patchloop/agent/tools.py",
    "patchloop/agent/lean_runtime.py",
    "patchloop/agent/workflow_successor.py",
    "patchloop/agent/workflow_successor_v2.py",
    "patchloop/agent/workflow_semantic_progress_successor.py",
    "patchloop/agent/workflow_causal_plan_projection_activation.py",
    "patchloop/agent/workflow_exploration_gate_activation.py",
    "patchloop/agent/three_visible_check_runtime_compatibility_qualification.py",
    "patchloop/contracts.py",
    "scripts/build_three_visible_check_runtime_compatibility_qualification.py",
    "tests/test_three_visible_check_runtime_compatibility_qualification.py",
)


def _identity(root: Path, relative: str, *, canonical_document: bool) -> dict[str, Any]:
    selected = ensure_within(root, relative)
    if selected.is_symlink() or not selected.is_file():
        raise ContractError(f"three-check compatibility input is unavailable: {relative}")
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
            raise ContractError("three-check predecessor is not JSON") from exc
        content_hash = document.get("content_hash")
        if content_hash != sha256_json(
            {key: item for key, item in document.items() if key != "content_hash"}
        ):
            raise ContractError("three-check predecessor content hash differs")
        value["content_hash"] = content_hash
    return value


def _public_task(root: Path) -> PublicTask:
    selected = ensure_within(root, TASK_PUBLIC_PATH.as_posix())
    try:
        document = yaml.safe_load(selected.read_text(encoding="utf-8"))
        task = PublicTask.model_validate(document)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        raise ContractError("AnyIO-v5 public task is unavailable") from exc
    if (
        task.task_id != "anyio-interrupt-runner-cleanup"
        or task.task_version != 5
        or task.split != "dev-validation"
        or tuple(check.id for check in task.visible_checks) != EXPECTED_CHECK_ORDER
    ):
        raise ContractError("AnyIO-v5 public three-check identity differs")
    return task


def _event(sequence: int, event_type: EventType, payload: dict[str, Any]) -> RunEvent:
    return RunEvent(
        event_id=f"evt_three_check_{sequence}",
        run_id=RUN_ID,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 27, tzinfo=UTC),
        actor="three-check-source-qualification",
        correlation_id=None,
        payload=payload,
    )


def _mutation(sequence: int, diff_hash: str) -> RunEvent:
    return _event(
        sequence,
        EventType.PATCH_APPLIED,
        {
            "patch_hash": sha256_json({"patch": sequence}),
            "worktree_diff_hash": diff_hash,
        },
    )


def _check_event(
    sequence: int,
    check_id: str,
    *,
    passed: bool,
    diff_hash: str = CURRENT_DIFF,
) -> RunEvent:
    descriptor = {
        "artifact_id": f"art_{sequence:032x}",
        "path": f"artifacts/public-check-{sequence}.json",
        "content_hash": sha256_json({"sequence": sequence, "check_id": check_id, "passed": passed}),
        "size_bytes": 128,
        "media_type": "application/json; charset=utf-8",
    }
    return _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "run_check",
            "status": "succeeded",
            "check_id": check_id,
            "invocation_status": "completed",
            "behavior_status": "passed" if passed else "failed",
            "passed": passed,
            "timed_out": False,
            "failure_summary": None if passed else "PUBLIC_CASE:anyio:ordinary-failure",
            "worktree_diff_hash": diff_hash,
            "artifact_id": descriptor["artifact_id"],
            "artifact_path": descriptor["path"],
            "result_artifact": descriptor,
        },
    )


def _visible_context(event: RunEvent) -> str:
    descriptor = event.payload["result_artifact"]
    tool_result = {
        "check_id": event.payload["check_id"],
        "invocation_status": event.payload["invocation_status"],
        "behavior_status": event.payload["behavior_status"],
        "passed": event.payload["passed"],
        "timed_out": event.payload["timed_out"],
    }
    return canonical_json(
        {
            "recent_events": [
                {
                    "sequence": event.sequence,
                    "type": event.type.value,
                    "payload": {
                        "tool": "run_check",
                        "artifact_id": descriptor["artifact_id"],
                        "artifact_path": descriptor["path"],
                        "tool_result": tool_result,
                    },
                }
            ]
        }
    )


def _empty_catalog(task: PublicTask, diff_hash: str) -> EligiblePlanEvidenceCatalogV2:
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": diff_hash,
        "model_visible_context_hash": sha256_text(canonical_json({"recent_events": []})),
        "model_visible_recent_event_sequences": (),
        "items": (),
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


def _failed_catalog(
    task: PublicTask,
    events: tuple[RunEvent, ...],
    failure: RunEvent,
) -> EligiblePlanEvidenceCatalogV2:
    return project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=task,
        worktree_diff_hash=CURRENT_DIFF,
        model_visible_context=_visible_context(failure),
        events=events,
        required_trigger_event_sequence=failure.sequence,
    )


def _source_read(
    sequence: int,
    ranges: tuple[tuple[int, int], ...],
) -> EligiblePlanEvidence:
    source = SourceEvidenceProjection(
        path=SOURCE_PATH,
        requested_range=(ranges[0][0], ranges[-1][1]),
        actual_range=(ranges[0][0], ranges[-1][1]),
        visible_ranges=ranges,
        omitted_ranges=(),
        partial_line=False,
        total_lines=1_000,
        file_content_hash="sha256:" + f"{sequence:064x}",
    )
    return EligiblePlanEvidence(
        evidence_id=f"pev:{sequence}",
        kind="source_read",
        role="foundation",
        run_id=RUN_ID,
        worktree_diff_hash=sha256_text(""),
        canonical_event_sequence=sequence,
        model_visible_event_sequences=(sequence,),
        replay_alias_event_sequences=(),
        artifact_hash="sha256:" + f"{sequence + 100:064x}",
        visible_projection_hash=sha256_json(source.model_dump(mode="json")),
        source=source,
        check=None,
        diff_review=None,
        search=None,
    )


def _search_support(sequence: int) -> EligiblePlanEvidence:
    search = SearchEvidenceProjection(
        query_hash=sha256_text("runner lifecycle"),
        path_glob="src/anyio/**/*.py",
        match_count=3,
        truncated=False,
    )
    return EligiblePlanEvidence(
        evidence_id=f"pev:{sequence}",
        kind="search_support",
        role="support",
        run_id=RUN_ID,
        worktree_diff_hash=sha256_text(""),
        canonical_event_sequence=sequence,
        model_visible_event_sequences=(sequence,),
        replay_alias_event_sequences=(),
        artifact_hash="sha256:" + f"{sequence + 100:064x}",
        visible_projection_hash=sha256_json(search.model_dump(mode="json")),
        source=None,
        check=None,
        diff_review=None,
        search=search,
    )


def _plan_catalog(task: PublicTask) -> EligiblePlanEvidenceCatalogV2:
    items = (
        _source_read(20, ((100, 130), (300, 340))),
        _source_read(21, ((500, 530),)),
        _search_support(24),
    )
    body = {
        "schema_version": "eligible-plan-evidence-catalog-v2",
        "run_id": RUN_ID,
        "task_id": task.task_id,
        "task_version": task.task_version,
        "public_task_hash": sha256_json(task.model_dump(mode="json")),
        "worktree_diff_hash": sha256_text(""),
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


def _initial_plan_decision(task: PublicTask) -> WorkflowDecisionV3:
    body = {
        "schema_version": "lean-workflow-decision-v3",
        "runtime_policy_version": "lean-harness-v15",
        "policy_version": "public-failure-signature-no-progress-reset-v1",
        "target": "pre-mutation-exploration",
        "current_diff_hash": sha256_text(""),
        "expected_check_id": EXPECTED_CHECK_ORDER[0],
        "allowed_tool_names": (
            "search_files",
            "read_file",
            "run_check",
            "record_work_plan",
        ),
        "information_actions_in_episode": 0,
        "fresh_current_read": True,
        "corrective_mutations_for_check": 0,
        "review_corrections_used": 0,
        "pre_mutation_actions_used": 2,
        "active_plan_hash": None,
        "plan_gate_id": None,
        "plan_admission_recovery_used": False,
        "plan_admission_recovery_remaining": 1,
        "required_trigger_evidence_id": None,
        "revision_trigger": None,
        "terminal_reason": None,
        "configured_max_output_tokens": 12_288,
        "effective_max_output_tokens": 8_192,
        "reasoning_effort": "medium",
        "parallel_tool_calls": False,
        "one_tool_call_per_response": True,
        "provider_calls_authorized": False,
        "semantic_progress_state_hash": None,
        "semantic_reset_required": False,
        "required_prior_hypothesis_disposition": None,
    }
    decision = WorkflowDecisionV3.model_validate({**body, "content_hash": sha256_json(body)})
    if decision.expected_check_id != task.visible_checks[0].id:
        raise ContractError("initial plan decision check binding differs")
    return decision


def _plan_arguments(request: Any) -> dict[str, Any]:
    spans = request.source_request.base_request.source_projection.source_span_catalog.spans
    if len(spans) < 3:
        raise ContractError("three-check plan projection lacks source coverage")
    boundary, execution, mutation = spans[0], spans[1], spans[-1]
    return {
        "hypothesis": "A bounded public lifecycle path controls the observed transition.",
        "supporting_evidence_ids": ["pev:24"],
        "candidate_source_span_ids": [mutation.source_span_id],
        "intended_change": "Adjust only the evidence-bound lifecycle transition.",
        "expected_behavior": "All three public checks retain their declared order.",
        "unknowns": [],
        "prior_hypothesis_disposition": None,
        "causal_mechanism": {
            "summary": "Public ownership reaches execution and one mutation boundary.",
            "causal_boundary": {
                "source_span_id": boundary.source_span_id,
                "symbol": "public_owner",
                "observation": "This range owns the public lifecycle entry.",
                "relationship_to_next": "The entry reaches the execution boundary.",
            },
            "intermediate_steps": [
                {
                    "source_span_id": execution.source_span_id,
                    "symbol": "public_execution",
                    "observation": "This range executes the public lifecycle transition.",
                    "relationship_to_next": "Execution reaches the mutation boundary.",
                }
            ],
            "mutation_site": {
                "source_span_id": mutation.source_span_id,
                "symbol": "public_mutation",
                "observation": "This range commits the visible lifecycle state.",
            },
            "mutation_site_rationale": "The final public boundary is the minimal edit site.",
            "expected_observable_effect": "The ordered checks observe the preserved lifecycle.",
            "falsification_condition": "A registered public check still fails after the edit.",
        },
        "exploration_state": {
            "boundary_coverage": {
                "ownership_boundary_span_ids": [boundary.source_span_id],
                "execution_boundary_span_ids": [execution.source_span_id],
                "mutation_boundary_span_ids": [mutation.source_span_id],
            },
            "invariants": [
                {
                    "subject": "Public lifecycle ordering",
                    "claim": "Ownership and execution precede the mutation boundary.",
                    "evidence_source_span_ids": [
                        boundary.source_span_id,
                        execution.source_span_id,
                    ],
                }
            ],
            "preservation_obligations": [
                {
                    "public_requirement": "Preserve ordinary failure and upstream behavior.",
                    "expected_behavior": "The added guard runs before upstream regression.",
                    "evidence_source_span_ids": [
                        execution.source_span_id,
                        mutation.source_span_id,
                    ],
                }
            ],
            "unknown_dispositions": [],
            "open_blocking_unknowns": [],
        },
    }


def _plan_projection(task: PublicTask) -> dict[str, Any]:
    catalog = _plan_catalog(task)
    schemas = tuple(copy.deepcopy(item) for item in TOOL_SCHEMAS_V23)
    decision = project_exploration_readiness_decision(
        task=task,
        decision=_initial_plan_decision(task),
        catalog=catalog,
        source_tool_schemas=schemas,
        cross_reset_trigger=None,
    )
    surface, request = project_exploration_workflow_tool_surface(
        task=task,
        decision=decision,
        catalog=catalog,
        source_tool_schemas=schemas,
        cross_reset_trigger=None,
    )
    if request is None:
        raise ContractError("three-check V19 plan request was not activated")
    projected, _ = normalize_activated_exploration_plan(
        task=task,
        catalog=catalog,
        request_projection=request,
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
        cross_reset_trigger=None,
        history=(),
        raw_arguments=_plan_arguments(request),
    )
    standard = standard_plan_from_projected_causal_plan(
        task=task,
        catalog=catalog,
        projected=projected,
    )
    return {
        "task_spec_check_order": list(project_public_task_spec(task).visible_check_ids),
        "projected_plan_check_order": list(projected.planned_check_ids),
        "durable_plan_check_order": list(standard.planned_check_ids),
        "dynamic_initial_check_enum": next(
            item["parameters"]["properties"]["check_id"]["enum"]
            for item in surface.selected_tool_schemas
            if item.get("name") == "run_check"
        ),
        "model_authors_check_order": False,
        "server_owned_check_order": True,
        "runtime_surface_activated": request.runtime_surface_activated,
    }


def _workflow_projection(
    task: PublicTask,
    events: tuple[RunEvent, ...],
    diff_hash: str,
    *,
    catalog: EligiblePlanEvidenceCatalogV2 | None = None,
    phase: Phase = Phase.IMPLEMENT,
) -> tuple[Any, Any, Any]:
    evidence = diff_bound_evidence(
        task,
        events,
        diff_hash,
        phase=phase,
        completion_driven=True,
    )
    selected_catalog = catalog or _empty_catalog(task, diff_hash)
    failure_sequence = current_public_failure_event_sequence(
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=events,
    )
    progress = project_public_semantic_progress_state(
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=events,
        current_failure_event_sequence=failure_sequence,
    )
    decision = project_workflow_semantic_progress_successor(
        run_id=RUN_ID,
        task=task,
        evidence=evidence,
        events=events,
        catalog=selected_catalog,
        semantic_progress_state=progress,
        active_work_state=None,
        available_tool_names=tuple(str(item["name"]) for item in TOOL_SCHEMAS_V23),
        configured_max_output_tokens=12_288,
    )
    decision = project_exploration_readiness_decision(
        task=task,
        decision=decision,
        catalog=selected_catalog,
        source_tool_schemas=tuple(copy.deepcopy(item) for item in TOOL_SCHEMAS_V23),
        cross_reset_trigger=None,
    )
    surface, request = project_exploration_workflow_tool_surface(
        task=task,
        decision=decision,
        catalog=selected_catalog,
        source_tool_schemas=tuple(copy.deepcopy(item) for item in TOOL_SCHEMAS_V23),
        cross_reset_trigger=None,
    )
    if request is not None:
        raise ContractError("three-check completion path unexpectedly exposed a plan")
    return evidence, decision, surface


def _surface_check_enum(surface: Any) -> list[str] | None:
    schema = next(
        (item for item in surface.selected_tool_schemas if item.get("name") == "run_check"),
        None,
    )
    if schema is None:
        return None
    return schema["parameters"]["properties"]["check_id"].get("enum")


class _PhaseHarness:
    def __init__(self) -> None:
        self.transitions: list[tuple[str, str]] = []

    def _transition(self, _run_id: str, current: Phase, target: Phase) -> Phase:
        validate_transition(current, target)
        self.transitions.append((current.value, target.value))
        return target


def _phase_projection(task: PublicTask) -> dict[str, Any]:
    harness = _PhaseHarness()
    passed = ToolResult(
        action_id="act_three_check_pass",
        status="succeeded",
        started_at=datetime(2026, 8, 27, tzinfo=UTC),
        finished_at=datetime(2026, 8, 27, tzinfo=UTC),
        output={"passed": True},
    )
    failed = ToolResult(
        action_id="act_three_check_fail",
        status="succeeded",
        started_at=datetime(2026, 8, 27, tzinfo=UTC),
        finished_at=datetime(2026, 8, 27, tzinfo=UTC),
        output={"passed": False},
    )
    phase = AgentRunner._phase_after_tool(  # noqa: SLF001
        harness,
        RUN_ID,
        Phase.IMPLEMENT,
        "run_check",
        passed,
        task,
        Path("unused"),
    )
    after_first = phase
    after_second = AgentRunner._phase_after_tool(  # noqa: SLF001
        harness,
        RUN_ID,
        phase,
        "run_check",
        passed,
        task,
        Path("unused"),
    )
    after_third = AgentRunner._phase_after_tool(  # noqa: SLF001
        harness,
        RUN_ID,
        after_second,
        "run_check",
        passed,
        task,
        Path("unused"),
    )
    after_middle_failure = AgentRunner._phase_after_tool(  # noqa: SLF001
        harness,
        RUN_ID,
        Phase.VERIFY,
        "run_check",
        failed,
        task,
        Path("unused"),
    )
    return {
        "after_first_pass": after_first.value,
        "after_second_pass": after_second.value,
        "after_third_pass": after_third.value,
        "after_middle_failure": after_middle_failure.value,
        "recorded_transitions": [list(item) for item in harness.transitions],
        "workspace_accessed": False,
    }


def _completion_scenarios(task: PublicTask) -> dict[str, Any]:
    mutation = _mutation(1, CURRENT_DIFF)
    first = _check_event(2, EXPECTED_CHECK_ORDER[0], passed=True)
    second = _check_event(3, EXPECTED_CHECK_ORDER[1], passed=True)
    third = _check_event(4, EXPECTED_CHECK_ORDER[2], passed=True)

    states: list[dict[str, Any]] = []
    for events, phase in (
        ((mutation,), Phase.IMPLEMENT),
        ((mutation, first), Phase.VERIFY),
        ((mutation, first, second), Phase.VERIFY),
        ((mutation, first, second, third), Phase.VERIFY),
    ):
        evidence, decision, surface = _workflow_projection(
            task,
            events,
            CURRENT_DIFF,
            phase=phase,
        )
        states.append(
            {
                "phase": phase.value,
                "completed_checks": list(evidence.completed_checks),
                "pending_checks": list(evidence.pending_checks),
                "target": decision.target,
                "selected_tools": list(surface.selected_tool_names),
                "run_check_enum": _surface_check_enum(surface),
            }
        )

    failure = _check_event(3, EXPECTED_CHECK_ORDER[1], passed=False)
    failure_events = (mutation, first, failure)
    failure_catalog = _failed_catalog(task, failure_events, failure)
    failed_evidence, failed_decision, failed_surface = _workflow_projection(
        task,
        failure_events,
        CURRENT_DIFF,
        catalog=failure_catalog,
    )
    trigger = next(
        item
        for item in failure_catalog.items
        if item.evidence_id == failure_catalog.required_trigger_evidence_id
    )

    corrected_events = (*failure_events, _mutation(4, CORRECTED_DIFF))
    corrected_evidence, corrected_decision, corrected_surface = _workflow_projection(
        task,
        corrected_events,
        CORRECTED_DIFF,
    )
    return {
        "ordered_states": states,
        "middle_check_failure": {
            "completed_checks": list(failed_evidence.completed_checks),
            "pending_checks": list(failed_evidence.pending_checks),
            "target": failed_decision.target,
            "selected_tools": list(failed_surface.selected_tool_names),
            "upstream_exposed": EXPECTED_CHECK_ORDER[2]
            in canonical_json(failed_surface.model_dump(mode="json")),
            "trigger_kind": trigger.kind,
            "trigger_check_index": trigger.check.check_index if trigger.check else None,
            "trigger_check_id": trigger.check.check_id if trigger.check else None,
        },
        "post_correction_invalidation": {
            "completed_checks": list(corrected_evidence.completed_checks),
            "pending_checks": list(corrected_evidence.pending_checks),
            "target": corrected_decision.target,
            "run_check_enum": _surface_check_enum(corrected_surface),
        },
    }


def _scenarios(task: PublicTask) -> dict[str, Any]:
    task_spec = project_public_task_spec(task)
    return {
        "runtime_identity": {
            "runtime_policy_version": LEAN_RUNTIME_POLICY_VERSION_V19,
            "tool_schema_version": LEAN_TOOL_SCHEMA_VERSION_V19,
            "context_policy_version": LEAN_CONTEXT_POLICY_VERSION_V19,
            "request_evidence_schema": LEAN_REQUEST_EVIDENCE_SCHEMA_V19,
        },
        "public_task_projection": {
            "task_id": task.task_id,
            "task_version": task.task_version,
            "visible_check_count": len(task.visible_checks),
            "visible_check_order": list(task_spec.visible_check_ids),
            "public_task_hash": task_spec.public_task_hash,
            "task_spec_hash": task_spec.content_hash,
        },
        "plan_projection": _plan_projection(task),
        "completion_projection": _completion_scenarios(task),
        "phase_projection": _phase_projection(task),
        "tail_reserve": nominal_tail_reserve(
            task,
            context_policy_version=LEAN_CONTEXT_POLICY_VERSION_V19,
        ),
        "preserved_boundaries": {
            "v4_task_modified": False,
            "v18_or_v19_runtime_modified": False,
            "consumed_rapid_builder_modified": False,
            "registered_checks_executed": False,
            "hidden_failure_attributed": False,
        },
    }


def build_three_visible_check_runtime_compatibility_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    task = _public_task(root)
    predecessors: list[dict[str, Any]] = []
    for relative, expected in IMMUTABLE_PREDECESSORS.items():
        observed = _identity(root, relative, canonical_document=True)
        if any(observed.get(key) != value for key, value in expected.items()):
            raise ContractError(f"immutable three-check predecessor differs: {relative}")
        predecessors.append(observed)

    body = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime(2026, 8, 27, tzinfo=UTC).isoformat(),
        "status": "offline-source-qualified",
        "scope": "anyio-v5-lean-v19-three-visible-check-runtime-phase-compatibility",
        "scenarios": _scenarios(task),
        "source_files": [
            _identity(root, relative, canonical_document=False) for relative in SOURCE_FILES
        ],
        "immutable_predecessors": predecessors,
        "evidence_boundary": {
            "public_task_yaml_read": True,
            "public_synthetic_events_only": True,
            "private_task_spec_read": False,
            "hidden_evaluator_content_read": False,
            "reference_patch_read": False,
            "reasoning_text_read": False,
            "provider_calls": 0,
            "docker_calls": 0,
            "evaluator_calls": 0,
            "visible_check_calls": 0,
            "network_calls": 0,
            "workspace_mutations": 0,
            "added_cost_usd": "0",
        },
        "runtime_source_compatible": True,
        "runtime_source_modified": False,
        "rapid_candidate_created": False,
        "paid_execution_authorized": False,
        "quality_improvement_established": False,
        "hidden_failure_cause_established": False,
        "next_gate": "anyio-v5-rapid-candidate-formation",
    }
    return {**body, "content_hash": sha256_json(body)}


def qualification_bytes(value: dict[str, Any]) -> bytes:
    body = {key: item for key, item in value.items() if key != "content_hash"}
    if value.get("content_hash") != sha256_json(body):
        raise ContractError("three-check compatibility qualification hash differs")
    return (canonical_json(value) + "\n").encode("utf-8")


def materialize_three_visible_check_runtime_compatibility_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    value = build_three_visible_check_runtime_compatibility_qualification(root)
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(qualification_bytes(value))
    return value


def load_three_visible_check_runtime_compatibility_qualification(
    repository: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repository).resolve()
    target = ensure_within(root, QUALIFICATION_PATH.as_posix())
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ContractError("three-check compatibility qualification is unavailable") from exc
    if qualification_bytes(value) != raw:
        raise ContractError("three-check compatibility qualification bytes differ")
    if value != build_three_visible_check_runtime_compatibility_qualification(root):
        raise ContractError("three-check compatibility source binding differs")
    return value


__all__ = [
    "EXPECTED_CHECK_ORDER",
    "IMMUTABLE_PREDECESSORS",
    "QUALIFICATION_PATH",
    "SCHEMA_VERSION",
    "SOURCE_FILES",
    "TASK_PUBLIC_PATH",
    "build_three_visible_check_runtime_compatibility_qualification",
    "load_three_visible_check_runtime_compatibility_qualification",
    "materialize_three_visible_check_runtime_compatibility_qualification",
    "qualification_bytes",
]
