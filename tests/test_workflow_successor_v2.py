from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from patchloop.agent.phases import EvidenceState
from patchloop.agent.tools import (
    TOOL_SCHEMAS_V15,
    TOOL_SCHEMAS_V16,
    TOOL_SCHEMAS_V17,
    TOOL_SCHEMAS_V18,
)
from patchloop.agent.workflow_successor_v2 import (
    PLAN_RECORDED_EVENT_SCHEMA_V2,
    WORK_PLAN_ADMISSION_POLICY,
    project_active_work_state,
    project_eligible_plan_evidence_catalog,
    project_eligible_plan_evidence_catalog_v2,
    project_workflow_successor_v2,
    project_workflow_tool_surface_v2,
    required_failed_check_trigger_sequence,
    validate_work_plan_v2,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError
from patchloop.util import load_unique_yaml, sha256_json, sha256_text

ROOT = Path(__file__).resolve().parents[1]
TASK = PublicTask.model_validate(
    load_unique_yaml(
        (ROOT / "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml").read_text(
            encoding="utf-8"
        )
    )
)
RUN_ID = "run_workflow_v2"
EMPTY = sha256_text("")
DIFF = "sha256:" + "1" * 64
SOURCE_PATH = "src/anyio/pytest_plugin.py"


def _event(
    sequence: int,
    event_type: EventType,
    *,
    payload: dict | None = None,
    correlation_id: str | None = None,
    run_id: str = RUN_ID,
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_{sequence}",
        run_id=run_id,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 25, tzinfo=UTC),
        actor="test",
        correlation_id=correlation_id,
        payload=payload or {},
    )


def _public_result(
    sequence: int,
    tool: str,
    tool_result: dict,
    *,
    diff: str,
    event_type: EventType = EventType.TOOL_SUCCEEDED,
    correlation_id: str | None = None,
    run_id: str = RUN_ID,
) -> tuple[RunEvent, dict]:
    artifact = {
        "artifact_id": f"artifact-{sequence}",
        "path": f"cas/{sequence}.json",
        "content_hash": sha256_json(tool_result),
    }
    status = "succeeded" if event_type == EventType.TOOL_SUCCEEDED else "rejected"
    durable_payload = {
        "tool": tool,
        "status": status,
        "artifact_id": artifact["artifact_id"],
        "artifact_path": artifact["path"],
        "result_artifact": artifact,
        "worktree_diff_hash": diff,
        "check_id": tool_result.get("check_id"),
        "passed": tool_result.get("passed"),
        "invocation_status": tool_result.get("invocation_status"),
        "behavior_status": tool_result.get("behavior_status"),
        "timed_out": tool_result.get("timed_out"),
    }
    event = _event(
        sequence,
        event_type,
        payload=durable_payload,
        correlation_id=correlation_id,
        run_id=run_id,
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
    return event, visible


def _read_result(*, truncated: bool = False) -> dict:
    content = "line 20\nline 21\n"
    if truncated:
        content = "line 20\nline 21\n\n...[field truncated for model context]"
    return {
        "path": SOURCE_PATH,
        "content": content,
        "start_line": 20,
        "end_line": 120,
        "actual_start_line": 20,
        "actual_end_line": 120 if truncated else 21,
        "total_lines": 500,
        "file_content_hash": "sha256:" + "2" * 64,
    }


def _check_result(*, passed: bool, timed_out: bool = False) -> dict:
    return {
        "check_id": TASK.visible_checks[0].id,
        "invocation_status": "timed_out" if timed_out else "completed",
        "behavior_status": "not_observed" if timed_out else ("passed" if passed else "failed"),
        "passed": passed,
        "timed_out": timed_out,
    }


def _catalog(
    pairs: list[tuple[RunEvent, dict]],
    *,
    diff: str = EMPTY,
    events: list[RunEvent] | None = None,
):
    durable = events if events is not None else [pair[0] for pair in pairs]
    context = json.dumps({"recent_events": [pair[1] for pair in pairs]})
    return project_eligible_plan_evidence_catalog(
        run_id=RUN_ID,
        task=TASK,
        worktree_diff_hash=diff,
        model_visible_context=context,
        events=durable,
    )


def _evidence(
    *,
    diff: str,
    mutation: bool,
    completed: tuple[str, ...] = (),
    mutation_sequence: int | None = None,
    review_sequence: int | None = None,
    review_presented: bool = False,
) -> EvidenceState:
    check_order = tuple(check.id for check in TASK.visible_checks)
    return EvidenceState(
        worktree_diff_hash=diff,
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
        allowed_next_actions=("search_files", "read_file", "apply_structured_edit", "run_check"),
    )


def _plan_arguments(catalog, *, status: str, disposition: str | None = None) -> dict:
    source = next(item for item in catalog.items if item.kind == "source_read")
    foundation = [item.evidence_id for item in catalog.items if item.role == "foundation"]
    body = {
        "observation_status": status,
        "hypothesis": "Public cleanup state can remain reachable after interruption.",
        "foundation_evidence_ids": foundation,
        "supporting_evidence_ids": [],
        "candidate_files": [{"path": SOURCE_PATH, "read_evidence_id": source.evidence_id}],
        "intended_change": "Bound interrupted runner cleanup to the current fixture.",
        "expected_behavior": "The interrupted test cannot resume and cleanup runs once.",
        "unknowns": [],
    }
    if disposition is not None:
        body["prior_hypothesis_disposition"] = disposition
    return body


def test_catalog_uses_only_exact_model_visible_successes_and_typed_outcomes() -> None:
    read = _public_result(1, "read_file", _read_result(), diff=EMPTY)
    failed_check = _public_result(2, "run_check", _check_result(passed=False), diff=EMPTY)
    timeout = _public_result(
        3,
        "run_check",
        _check_result(passed=False, timed_out=True),
        diff=EMPTY,
    )
    failed_tool = _public_result(
        4,
        "read_file",
        _read_result(),
        diff=EMPTY,
        event_type=EventType.TOOL_FAILED,
    )
    catalog = _catalog([read, failed_check, timeout, failed_tool])

    assert [item.kind for item in catalog.items] == [
        "source_read",
        "targeted_check_result",
    ]
    assert catalog.items[1].check is not None
    assert catalog.items[1].check.behavior_status == "failed"
    assert catalog.private_evidence_used is False
    assert catalog.reasoning_text_used is False


def test_search_only_and_stale_or_foreign_results_cannot_be_foundation() -> None:
    search = _public_result(
        1,
        "search_files",
        {"query": "cancel", "path_glob": "src/**/*.py", "matches": [], "truncated": False},
        diff=EMPTY,
    )
    stale = _public_result(2, "read_file", _read_result(), diff=DIFF)
    catalog = _catalog([search, stale], diff=EMPTY)
    assert [item.role for item in catalog.items] == ["support"]

    foreign_event, foreign_visible = _public_result(
        3,
        "read_file",
        _read_result(),
        diff=EMPTY,
        run_id="run_foreign",
    )
    with pytest.raises(ContractError, match="run binding"):
        _catalog(
            [(foreign_event, foreign_visible)],
            events=[foreign_event],
        )


def test_catalog_marks_only_displayed_read_ranges_and_canonicalizes_exact_replay() -> None:
    read = _public_result(
        2,
        "read_file",
        _read_result(truncated=True),
        diff=EMPTY,
        correlation_id="read-1",
    )
    original_call = _event(
        1,
        EventType.TOOL_CALLED,
        correlation_id="read-1",
        payload={"tool": "read_file", "input_hash": "sha256:" + "3" * 64},
    )
    replay_event = _event(
        3,
        EventType.TOOL_REPLAYED,
        correlation_id="read-1",
        payload={
            **read[0].payload,
            "status": "succeeded",
            "input_hash": "sha256:" + "3" * 64,
        },
    )
    replay_visible = {**read[1], "sequence": 3, "type": EventType.TOOL_REPLAYED.value}
    catalog = _catalog(
        [read, (replay_event, replay_visible)],
        events=[original_call, read[0], replay_event],
    )

    assert len(catalog.items) == 1
    item = catalog.items[0]
    assert item.evidence_id == "pev:2"
    assert item.model_visible_event_sequences == (2, 3)
    assert item.replay_alias_event_sequences == (3,)
    assert item.source is not None
    assert item.source.visible_ranges == ((20, 21),)
    assert item.source.omitted_ranges == ((22, 120),)


def test_dynamic_plan_schema_and_validator_bind_candidate_to_current_read() -> None:
    read = _public_result(1, "read_file", _read_result(), diff=EMPTY)
    check = _public_result(2, "run_check", _check_result(passed=False), diff=EMPTY)
    catalog = _catalog([read, check])
    decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v11",
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(diff=EMPTY, mutation=False),
        events=[read[0], check[0]],
        catalog=catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V15),
        configured_max_output_tokens=25_000,
    )
    surface = project_workflow_tool_surface_v2(
        decision=decision,
        catalog=catalog,
        source_tool_schemas=TOOL_SCHEMAS_V15,
    )
    plan_schema = next(
        schema for schema in surface.selected_tool_schemas if schema["name"] == "record_work_plan"
    )
    properties = plan_schema["parameters"]["properties"]
    assert properties["foundation_evidence_ids"]["items"]["enum"] == ["pev:1", "pev:2"]
    assert properties["candidate_files"]["items"]["properties"]["path"]["enum"] == [SOURCE_PATH]

    valid = validate_work_plan_v2(
        task=TASK,
        catalog=catalog,
        arguments=_plan_arguments(catalog, status="targeted_check_failed"),
        trigger="initial",
        revision_index=0,
        parent_plan_hash=None,
        trigger_check_id=None,
        trigger_event_sequence=None,
    )
    assert valid.planned_check_ids == tuple(check.id for check in TASK.visible_checks)
    tampered = _plan_arguments(catalog, status="targeted_check_failed")
    tampered["candidate_files"][0]["read_evidence_id"] = "pev:2"
    with pytest.raises(ContractError, match="candidate lacks"):
        validate_work_plan_v2(
            task=TASK,
            catalog=catalog,
            arguments=tampered,
            trigger="initial",
            revision_index=0,
            parent_plan_hash=None,
            trigger_check_id=None,
            trigger_event_sequence=None,
        )


def test_two_plan_admission_rejections_stop_before_another_provider_request() -> None:
    read = _public_result(1, "read_file", _read_result(), diff=EMPTY)
    catalog = _catalog([read])
    initial = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v11",
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(diff=EMPTY, mutation=False),
        events=[read[0]],
        catalog=catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V15),
        configured_max_output_tokens=25_000,
    )
    assert initial.plan_gate_id is not None
    blocked = [
        _event(
            index,
            EventType.TOOL_ADMISSION_BLOCKED,
            payload={
                "policy_version": WORK_PLAN_ADMISSION_POLICY,
                "plan_gate_id": initial.plan_gate_id,
            },
        )
        for index in (2, 3)
    ]
    terminal = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v11",
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(diff=EMPTY, mutation=False),
        events=[read[0], *blocked],
        catalog=catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V15),
        configured_max_output_tokens=25_000,
    )
    assert terminal.target == "terminal"
    assert terminal.terminal_reason == "work_plan_admission_repeated"
    assert terminal.allowed_tool_names == ()


def test_v12_failed_check_requires_linked_revision_and_pins_plan_after_long_tail() -> None:
    initial_read = _public_result(1, "read_file", _read_result(), diff=EMPTY)
    initial_catalog = _catalog([initial_read])
    initial_plan = validate_work_plan_v2(
        task=TASK,
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
            "revision_index": initial_plan.revision_index,
            "parent_plan_hash": initial_plan.parent_plan_hash,
            "trigger": initial_plan.trigger,
            "plan": initial_plan.model_dump(mode="json"),
        },
    )
    patch_event = _event(
        3,
        EventType.PATCH_APPLIED,
        payload={"worktree_diff_hash": DIFF, "plan_hash": initial_plan.content_hash},
    )
    failed_check = _public_result(4, "run_check", _check_result(passed=False), diff=DIFF)
    current_read = _public_result(5, "read_file", _read_result(), diff=DIFF)
    events = [initial_read[0], plan_event, patch_event, failed_check[0], current_read[0]]
    catalog = _catalog([failed_check, current_read], diff=DIFF, events=events)
    evidence = _evidence(diff=DIFF, mutation=True, mutation_sequence=3)
    decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v12",
        run_id=RUN_ID,
        task=TASK,
        evidence=evidence,
        events=events,
        catalog=catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V17),
        configured_max_output_tokens=25_000,
    )
    assert decision.revision_trigger == "check_failure"
    assert decision.required_trigger_evidence_id == "pev:4"
    assert "apply_structured_edit" not in decision.allowed_tool_names
    assert "revise_work_plan" in decision.allowed_tool_names

    revision = validate_work_plan_v2(
        task=TASK,
        catalog=catalog,
        arguments=_plan_arguments(
            catalog,
            status="visible_check_failed",
            disposition="refined",
        ),
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash=initial_plan.content_hash,
        trigger_check_id=TASK.visible_checks[0].id,
        trigger_event_sequence=4,
    )
    revision_event = _event(
        6,
        EventType.PLAN_RECORDED,
        payload={
            "schema_version": PLAN_RECORDED_EVENT_SCHEMA_V2,
            "plan_hash": revision.content_hash,
            "worktree_diff_hash": DIFF,
            "revision_index": revision.revision_index,
            "parent_plan_hash": revision.parent_plan_hash,
            "trigger": revision.trigger,
            "plan": revision.model_dump(mode="json"),
        },
    )
    long_tail = [
        _event(index, EventType.MODEL_CALLED, payload={"public": True}) for index in range(7, 22)
    ]
    active = project_active_work_state(
        run_id=RUN_ID,
        task=TASK,
        current_diff_hash=DIFF,
        events=[*events, revision_event, *long_tail],
    )
    assert active is not None
    assert active.initial_plan.content_hash == initial_plan.content_hash
    assert active.latest_plan.content_hash == revision.content_hash
    assert active.chain_hash == sha256_json([initial_plan.content_hash, revision.content_hash])


def test_v14_pins_evicted_failed_check_and_forces_revision_after_three_reads() -> None:
    initial_read = _public_result(1, "read_file", _read_result(), diff=EMPTY)
    initial_catalog = _catalog([initial_read])
    initial_plan = validate_work_plan_v2(
        task=TASK,
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
    failed_check = _public_result(4, "run_check", _check_result(passed=False), diff=DIFF)
    first_read = _public_result(5, "read_file", _read_result(), diff=DIFF)
    search = _public_result(
        6,
        "search_files",
        {
            "query": "cancel",
            "path_glob": "src/**/*.py",
            "matches": [],
            "truncated": False,
        },
        diff=DIFF,
    )
    second_read = _public_result(7, "read_file", _read_result(), diff=DIFF)
    events = [
        initial_read[0],
        plan_event,
        patch_event,
        failed_check[0],
        first_read[0],
        search[0],
        second_read[0],
    ]
    evidence = _evidence(diff=DIFF, mutation=True, mutation_sequence=3)
    trigger_sequence = required_failed_check_trigger_sequence(
        run_id=RUN_ID,
        task=TASK,
        evidence=evidence,
        events=events,
    )
    assert trigger_sequence == 4

    evicted_context = json.dumps({"recent_events": [first_read[1], search[1], second_read[1]]})
    v13_catalog = project_eligible_plan_evidence_catalog(
        run_id=RUN_ID,
        task=TASK,
        worktree_diff_hash=DIFF,
        model_visible_context=evicted_context,
        events=events,
    )
    v13_decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v13",
        run_id=RUN_ID,
        task=TASK,
        evidence=evidence,
        events=events,
        catalog=v13_catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V16),
        configured_max_output_tokens=25_000,
    )
    assert v13_decision.information_actions_in_episode == 3
    assert v13_decision.allowed_tool_names == ("read_file",)
    assert v13_decision.required_trigger_evidence_id is None

    v14_catalog = project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=TASK,
        worktree_diff_hash=DIFF,
        model_visible_context=evicted_context,
        events=events,
        required_trigger_event_sequence=trigger_sequence,
    )
    assert v14_catalog.required_trigger_status == "pinned"
    assert v14_catalog.model_visible_pinned_event_sequences == (4,)
    assert 4 not in v14_catalog.model_visible_recent_event_sequences
    assert v14_catalog.required_trigger_evidence_id == "pev:4"
    v14_decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v14",
        run_id=RUN_ID,
        task=TASK,
        evidence=evidence,
        events=events,
        catalog=v14_catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V18),
        configured_max_output_tokens=25_000,
    )
    assert v14_decision.target == "revise-work-plan"
    assert v14_decision.allowed_tool_names == ("revise_work_plan",)
    assert v14_decision.required_trigger_evidence_id == "pev:4"

    recent_catalog = project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=TASK,
        worktree_diff_hash=DIFF,
        model_visible_context=json.dumps({"recent_events": [failed_check[1], first_read[1]]}),
        events=events,
        required_trigger_event_sequence=trigger_sequence,
    )
    evicted_pin = next(item for item in v14_catalog.items if item.evidence_id == "pev:4")
    recent_pin = next(item for item in recent_catalog.items if item.evidence_id == "pev:4")
    assert recent_pin == evicted_pin


def test_v14_unavailable_required_trigger_fails_closed_without_a_tool_surface() -> None:
    initial_read = _public_result(1, "read_file", _read_result(), diff=EMPTY)
    initial_catalog = _catalog([initial_read])
    initial_plan = validate_work_plan_v2(
        task=TASK,
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
    failed_check = _public_result(4, "run_check", _check_result(passed=False), diff=DIFF)
    broken_check = failed_check[0].model_copy(
        update={"payload": {**failed_check[0].payload, "result_artifact": None}}
    )
    current_read = _public_result(5, "read_file", _read_result(), diff=DIFF)
    events = [initial_read[0], plan_event, patch_event, broken_check, current_read[0]]
    catalog = project_eligible_plan_evidence_catalog_v2(
        run_id=RUN_ID,
        task=TASK,
        worktree_diff_hash=DIFF,
        model_visible_context=json.dumps({"recent_events": [current_read[1]]}),
        events=events,
        required_trigger_event_sequence=4,
    )
    assert catalog.required_trigger_status == "unavailable"
    assert catalog.unavailable_reason == "artifact_binding_invalid"
    decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v14",
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(diff=DIFF, mutation=True, mutation_sequence=3),
        events=events,
        catalog=catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V18),
        configured_max_output_tokens=25_000,
    )
    assert decision.target == "terminal"
    assert decision.terminal_reason == "required_workflow_evidence_unavailable"
    assert decision.allowed_tool_names == ()


def test_v12_mechanical_edit_rejection_requires_reread_not_another_revision() -> None:
    initial_read = _public_result(1, "read_file", _read_result(), diff=EMPTY)
    initial_catalog = _catalog([initial_read])
    initial_plan = validate_work_plan_v2(
        task=TASK,
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
            "revision_index": initial_plan.revision_index,
            "parent_plan_hash": initial_plan.parent_plan_hash,
            "trigger": initial_plan.trigger,
            "plan": initial_plan.model_dump(mode="json"),
        },
    )
    patch_event = _event(
        3,
        EventType.PATCH_APPLIED,
        payload={"worktree_diff_hash": DIFF, "plan_hash": initial_plan.content_hash},
    )
    failed_check = _public_result(4, "run_check", _check_result(passed=False), diff=DIFF)
    current_read = _public_result(5, "read_file", _read_result(), diff=DIFF)
    base_events = [initial_read[0], plan_event, patch_event, failed_check[0], current_read[0]]
    catalog = _catalog([failed_check, current_read], diff=DIFF, events=base_events)
    revision = validate_work_plan_v2(
        task=TASK,
        catalog=catalog,
        arguments=_plan_arguments(
            catalog,
            status="visible_check_failed",
            disposition="refined",
        ),
        trigger="check_failure",
        revision_index=1,
        parent_plan_hash=initial_plan.content_hash,
        trigger_check_id=TASK.visible_checks[0].id,
        trigger_event_sequence=4,
    )
    revision_event = _event(
        6,
        EventType.PLAN_RECORDED,
        payload={
            "schema_version": PLAN_RECORDED_EVENT_SCHEMA_V2,
            "plan_hash": revision.content_hash,
            "worktree_diff_hash": DIFF,
            "revision_index": revision.revision_index,
            "parent_plan_hash": revision.parent_plan_hash,
            "trigger": revision.trigger,
            "plan": revision.model_dump(mode="json"),
        },
    )
    rejection = _event(
        7,
        EventType.TOOL_FAILED,
        payload={"tool": "apply_structured_edit", "worktree_diff_hash": DIFF},
    )
    events = [*base_events, revision_event, rejection]
    decision = project_workflow_successor_v2(
        runtime_policy_version="lean-harness-v12",
        run_id=RUN_ID,
        task=TASK,
        evidence=_evidence(diff=DIFF, mutation=True, mutation_sequence=3),
        events=events,
        catalog=catalog,
        available_tool_names=tuple(schema["name"] for schema in TOOL_SCHEMAS_V16),
        configured_max_output_tokens=25_000,
    )
    assert decision.target == "correction-investigation"
    assert decision.allowed_tool_names == ("read_file",)
    assert decision.active_plan_hash == revision.content_hash
