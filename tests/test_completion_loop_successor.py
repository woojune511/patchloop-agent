from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from patchloop.agent.completion_loop_successor import (
    CompletionLoopDecision,
    completion_instruction,
    project_completion_loop_successor,
    project_completion_tool_surface,
    project_current_edit_correction_context,
    project_provider_terminal_attribution,
)
from patchloop.agent.phases import diff_bound_evidence
from patchloop.agent.structured_edit import STRUCTURED_EDIT_TOOL_SCHEMA_V2
from patchloop.agent.tools import TOOL_SCHEMAS_V11
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import ContractError
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_text

TASK = load_task_package(
    "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4"
).public
CHECK_IDS = tuple(check.id for check in TASK.visible_checks)
DIFF_1 = sha256_text("diff-1")
SUCCESSOR_TOOL_SCHEMAS = tuple([*TOOL_SCHEMAS_V11, STRUCTURED_EDIT_TOOL_SCHEMA_V2])


def _event(sequence: int, event_type: EventType, payload: dict) -> RunEvent:
    return RunEvent(
        event_id=f"event-{sequence}",
        run_id="run-successor",
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 23, tzinfo=UTC),
        actor="tool-gateway" if "Tool" in event_type.value else "agent",
        payload=payload,
    )


def _mutation(sequence: int = 1, diff_hash: str = DIFF_1) -> RunEvent:
    return _event(
        sequence,
        EventType.PATCH_APPLIED,
        {"tool": "apply_patch", "worktree_diff_hash": diff_hash},
    )


def _check(
    sequence: int,
    check_id: str,
    *,
    passed: bool,
    diff_hash: str = DIFF_1,
) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "run_check",
            "check_id": check_id,
            "passed": passed,
            "worktree_diff_hash": diff_hash,
        },
    )


def _read(sequence: int, diff_hash: str = DIFF_1) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_SUCCEEDED,
        {
            "tool": "read_file",
            "path": "src/anyio/pytest_plugin.py",
            "worktree_diff_hash": diff_hash,
        },
    )


def _edit_failure(sequence: int, diff_hash: str = DIFF_1) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_FAILED,
        {
            "tool": "apply_structured_edit",
            "error_code": "INVALID_TOOL_INPUT",
            "worktree_diff_hash": diff_hash,
        },
    )


def _decision(events: list[RunEvent], diff_hash: str = DIFF_1) -> CompletionLoopDecision:
    evidence = diff_bound_evidence(
        TASK,
        events,
        diff_hash,
        completion_driven=True,
    )
    return project_completion_loop_successor(
        task=TASK,
        evidence=evidence,
        events=events,
        available_tool_names=tuple(item["name"] for item in SUCCESSOR_TOOL_SCHEMAS),
        configured_max_output_tokens=25_000,
    )


def _count_key(value, key: str) -> int:
    if isinstance(value, dict):
        return int(key in value) + sum(_count_key(child, key) for child in value.values())
    if isinstance(value, list):
        return sum(_count_key(child, key) for child in value)
    return 0


def test_successor_keeps_initial_exploration_but_gates_first_post_mutation_check() -> None:
    initial = _decision([], sha256_text(""))
    mutated = _decision([_mutation()])

    assert initial.target == "phase-policy"
    assert initial.effective_max_output_tokens == 25_000
    assert mutated.target == "visible-check"
    assert mutated.expected_check_id == CHECK_IDS[0]
    assert mutated.allowed_tool_names == ("run_check",)
    assert mutated.effective_max_output_tokens == 2_048
    assert mutated.reasoning_effort == "low"
    assert mutated.parallel_tool_calls is False


def test_failed_check_requires_current_read_then_one_structured_correction() -> None:
    failed = [_mutation(), _check(2, CHECK_IDS[0], passed=False)]
    inspection = _decision(failed)
    correction = _decision([*failed, _read(3)])
    inspect_again = _decision([*failed, _read(3), _edit_failure(4)])

    assert inspection.target == "correction-inspection"
    assert inspection.allowed_tool_names == ("read_file",)
    assert inspection.fresh_read_required is True
    assert inspection.effective_max_output_tokens == 4_096
    assert correction.target == "corrective-mutation"
    assert correction.allowed_tool_names == ("apply_structured_edit",)
    assert correction.fresh_read_required is False
    assert correction.effective_max_output_tokens == 8_192
    assert correction.reasoning_effort == "medium"
    assert inspect_again.target == "correction-inspection"
    assert inspect_again.latest_edit_failure_sequence == 4


def test_public_checks_are_serial_and_upstream_is_gated_by_targeted_pass() -> None:
    targeted_pass = [_mutation(), _check(2, CHECK_IDS[0], passed=True)]
    decision = _decision(targeted_pass)
    surface = project_completion_tool_surface(
        decision=decision,
        source_tool_schemas=SUCCESSOR_TOOL_SCHEMAS,
    )
    check_id_schema = surface.tool_schemas[0]["parameters"]["properties"]["check_id"]

    assert decision.target == "visible-check"
    assert decision.expected_check_id == CHECK_IDS[1]
    assert decision.preserve_check_ids == (CHECK_IDS[0],)
    assert surface.selected_tool_names == ("run_check",)
    assert check_id_schema["enum"] == [CHECK_IDS[1]]
    assert surface.parallel_tool_calls is False
    assert surface.one_tool_call_per_response is True
    instruction = completion_instruction(decision)
    assert instruction["preserve_check_ids"] == [CHECK_IDS[0]]
    assert "exactly" in instruction["instruction"]
    assert instruction["content_hash"].startswith("sha256:")


def test_targeted_failure_cannot_advance_to_upstream_check() -> None:
    decision = _decision([_mutation(), _check(2, CHECK_IDS[0], passed=False)])

    assert decision.expected_check_id == CHECK_IDS[0]
    assert decision.target == "correction-inspection"
    assert "run_check" not in decision.allowed_tool_names
    assert CHECK_IDS[1] not in decision.completed_check_ids


def test_latest_edit_correction_is_present_once_and_older_bodies_become_refs() -> None:
    first = {
        "schema_version": "edit-correction-evidence-v1",
        "failure_reason": "invalid_hunk_header",
        "current_source": {"content": "old source"},
    }
    latest = {
        "schema_version": "edit-correction-evidence-v1",
        "failure_reason": "context_mismatch",
        "current_source": {"content": "latest source"},
    }
    source = {
        "public_task": {"task_id": TASK.task_id},
        "recent_events": [
            {
                "sequence": 10,
                "type": "ToolFailed",
                "payload": {
                    "tool": "apply_patch",
                    "error_details": {"edit_correction": first},
                    "tool_result": {"error_details": {"edit_correction": first}},
                },
            },
            {
                "sequence": 20,
                "type": "ToolFailed",
                "payload": {
                    "tool": "apply_structured_edit",
                    "error_details": {"edit_correction": latest},
                    "tool_result": {"error_details": {"edit_correction": latest}},
                },
            },
        ],
        "rejected_mutation_retry": {"edit_correction": latest},
    }
    rendered = json.dumps(source, indent=2)

    projection = project_current_edit_correction_context(rendered)
    projected = json.loads(projection.rendered)
    evidence = projection.evidence

    assert projected["current_edit_correction"]["source_event_sequence"] == 20
    assert projected["current_edit_correction"]["correction"] == latest
    assert _count_key(projected, "edit_correction") == 0
    assert _count_key(projected, "current_edit_correction") == 1
    assert evidence.source_full_correction_occurrences == 5
    assert evidence.projected_full_correction_occurrences == 1
    assert evidence.removed_full_correction_occurrences == 4
    assert [item.occurrence_count for item in evidence.references] == [2, 3]
    assert [item.selected_current for item in evidence.references] == [False, True]
    assert evidence.raw_trace_mutated is False
    assert evidence.provider_calls_authorized is False


def test_conflicting_corrections_inside_one_event_fail_closed() -> None:
    rendered = json.dumps(
        {
            "recent_events": [
                {
                    "sequence": 1,
                    "payload": {
                        "tool": "apply_patch",
                        "edit_correction": {"value": "a"},
                        "tool_result": {"edit_correction": {"value": "b"}},
                    },
                }
            ]
        }
    )

    with pytest.raises(ContractError, match="conflicting edit corrections"):
        project_current_edit_correction_context(rendered)


def test_context_without_edit_correction_is_byte_preserving() -> None:
    rendered = '{"recent_events": [], "selected_memory": null}'

    projection = project_current_edit_correction_context(rendered)

    assert projection.rendered == rendered
    assert projection.evidence.source_context_hash == projection.content_hash
    assert projection.evidence.source_full_correction_occurrences == 0
    assert projection.evidence.removed_full_correction_occurrences == 0


def test_explicit_incomplete_terminal_precedes_but_preserves_usage_mismatch() -> None:
    row6 = project_provider_terminal_attribution(
        response_status="incomplete",
        response_incomplete_reason="max_output_tokens",
        usage_present=False,
        input_token_count_match=False,
    )
    completed_without_usage = project_provider_terminal_attribution(
        response_status="completed",
        response_incomplete_reason=None,
        usage_present=False,
        input_token_count_match=False,
    )

    assert row6.primary_error_code == "incomplete_response"
    assert row6.accounting_mismatch_preserved is True
    assert row6.historical_adapter_precedence_differs is True
    assert row6.runtime_activation_authorized is False
    assert completed_without_usage.primary_error_code == "input_token_count_mismatch"
    assert completed_without_usage.historical_adapter_precedence_differs is False


def test_successor_projection_grants_no_runtime_or_provider_authority() -> None:
    decision = _decision([_mutation()])
    surface = project_completion_tool_surface(
        decision=decision,
        source_tool_schemas=SUCCESSOR_TOOL_SCHEMAS,
    )

    assert decision.runtime_activation_authorized is False
    assert decision.provider_calls_authorized is False
    assert surface.runtime_activation_authorized is False
    assert surface.provider_calls_authorized is False
