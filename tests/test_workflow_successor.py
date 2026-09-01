from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from patchloop.agent.phases import EvidenceState
from patchloop.agent.workflow_successor import (
    PROTOCOL_RECOVERY_POLICY,
    project_public_task_spec,
    project_workflow_successor,
    validate_record_work_plan,
)
from patchloop.contracts import EventType, PublicTask, RunEvent
from patchloop.errors import ContractError
from patchloop.util import load_unique_yaml, sha256_text

ROOT = Path(__file__).resolve().parents[1]
TASK = PublicTask.model_validate(
    load_unique_yaml(
        (ROOT / "fixtures/task-packages/anyio-interrupt-runner-cleanup-v4/public.yaml").read_text(
            encoding="utf-8"
        )
    )
)
EMPTY = sha256_text("")
DIFF = "sha256:" + "1" * 64


def _event(
    sequence: int,
    event_type: EventType,
    *,
    tool: str | None = None,
    passed: bool | None = None,
    check_id: str | None = None,
    diff: str = DIFF,
    reason_code: str | None = None,
) -> RunEvent:
    payload = {}
    if tool is not None:
        payload.update({"tool": tool, "worktree_diff_hash": diff})
    if passed is not None:
        payload["passed"] = passed
    if check_id is not None:
        payload["check_id"] = check_id
    if reason_code is not None:
        payload.update({"reason_code": reason_code, "policy_version": PROTOCOL_RECOVERY_POLICY})
    return RunEvent(
        event_id=f"evt_{sequence}",
        run_id="run_test",
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 24, tzinfo=UTC),
        actor="test",
        payload=payload,
    )


def _evidence(
    *,
    completed: tuple[str, ...] = (),
    review_sequence: int | None = None,
    review_presented: bool = False,
    mutation: bool = True,
    diff: str = DIFF,
) -> EvidenceState:
    all_checks = tuple(check.id for check in TASK.visible_checks)
    return EvidenceState(
        worktree_diff_hash=diff,
        mutation_event_sequence=1 if mutation else None,
        mutation_present=mutation,
        completed_checks=completed,
        pending_checks=tuple(item for item in all_checks if item not in completed),
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


AVAILABLE = (
    "search_files",
    "read_file",
    "apply_patch",
    "run_check",
    "get_diff",
    "finish_task",
    "apply_structured_edit",
    "record_work_plan",
)


def _project(events, evidence=None, runtime="lean-harness-v9"):
    return project_workflow_successor(
        runtime_policy_version=runtime,
        task=TASK,
        evidence=evidence or _evidence(),
        events=events,
        available_tool_names=AVAILABLE,
        configured_max_output_tokens=25_000,
    )


def test_v9_allows_second_file_after_a_wrong_first_read() -> None:
    events = [
        _event(1, EventType.PATCH_APPLIED),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            tool="run_check",
            passed=False,
            check_id="public-interrupt-runner-lifecycle",
        ),
        _event(3, EventType.TOOL_SUCCEEDED, tool="read_file"),
    ]
    decision = _project(events)
    assert decision.target == "correction-investigation"
    assert decision.fresh_current_read is True
    assert decision.allowed_tool_names == (
        "search_files",
        "read_file",
        "apply_structured_edit",
    )


def test_v9_forces_third_investigation_to_read_and_edit_after_three() -> None:
    prefix = [
        _event(1, EventType.PATCH_APPLIED),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            tool="run_check",
            passed=False,
            check_id="public-interrupt-runner-lifecycle",
        ),
        _event(3, EventType.TOOL_SUCCEEDED, tool="search_files"),
        _event(4, EventType.TOOL_SUCCEEDED, tool="search_files"),
    ]
    assert _project(prefix).allowed_tool_names == ("read_file",)
    after_read = _project([*prefix, _event(5, EventType.TOOL_SUCCEEDED, tool="read_file")])
    assert after_read.target == "corrective-mutation"
    assert after_read.allowed_tool_names == ("apply_structured_edit",)


def test_v9_edit_rejection_invalidates_read_and_requires_reread() -> None:
    decision = _project(
        [
            _event(1, EventType.PATCH_APPLIED),
            _event(
                2,
                EventType.TOOL_SUCCEEDED,
                tool="run_check",
                passed=False,
                check_id="public-interrupt-runner-lifecycle",
            ),
            _event(3, EventType.TOOL_SUCCEEDED, tool="read_file"),
            _event(4, EventType.TOOL_FAILED, tool="apply_structured_edit"),
        ]
    )
    assert decision.fresh_current_read is False
    assert decision.allowed_tool_names == ("read_file",)


def test_v9_gates_upstream_and_limits_correction_mutations() -> None:
    first = "public-interrupt-runner-lifecycle"
    events = [_event(1, EventType.PATCH_APPLIED)]
    for sequence in (2, 4, 6):
        events.extend(
            [
                _event(
                    sequence,
                    EventType.TOOL_SUCCEEDED,
                    tool="run_check",
                    passed=False,
                    check_id=first,
                ),
                _event(sequence + 1, EventType.PATCH_APPLIED),
            ]
        )
    events.append(
        _event(
            8,
            EventType.TOOL_SUCCEEDED,
            tool="run_check",
            passed=False,
            check_id=first,
        )
    )
    decision = _project(events)
    assert decision.target == "terminal"
    assert decision.terminal_reason == "correction_attempt_limit"
    assert "run_check" not in decision.allowed_tool_names


def test_v9_review_allows_one_correction_and_then_preserves_submission_choice() -> None:
    checks = tuple(check.id for check in TASK.visible_checks)
    evidence = _evidence(completed=checks, review_sequence=4, review_presented=True)
    first = _project(
        [
            _event(1, EventType.PATCH_APPLIED),
            _event(4, EventType.TOOL_SUCCEEDED, tool="get_diff"),
        ],
        evidence,
    )
    assert first.target == "review-decision"
    assert first.review_corrections_used == 0
    assert first.allowed_tool_names[0] == "finish_task"
    second = _project(
        [
            _event(1, EventType.PATCH_APPLIED),
            _event(4, EventType.TOOL_SUCCEEDED, tool="get_diff"),
            _event(5, EventType.PATCH_APPLIED),
            _event(8, EventType.TOOL_SUCCEEDED, tool="get_diff"),
        ],
        evidence,
    )
    assert second.review_corrections_used == 1
    assert "finish_task" in second.allowed_tool_names
    assert "apply_structured_edit" in second.allowed_tool_names


def test_v9_shared_protocol_recovery_is_reconstructed_from_events() -> None:
    events = [
        _event(
            1,
            EventType.TOOL_ADMISSION_BLOCKED,
            reason_code="multiple_tool_calls",
        )
    ]
    decision = _project(events, _evidence(mutation=False, diff=EMPTY))
    assert decision.shared_recovery_used is True
    assert decision.shared_recovery_remaining == 0
    with pytest.raises(ContractError, match="more than once"):
        _project(
            [
                *events,
                _event(
                    2,
                    EventType.TOOL_ADMISSION_BLOCKED,
                    reason_code="actionless_response",
                ),
            ],
            _evidence(mutation=False, diff=EMPTY),
        )


def test_v10_task_spec_contains_public_fields_only() -> None:
    spec = project_public_task_spec(TASK)
    assert spec.visible_check_ids == tuple(check.id for check in TASK.visible_checks)
    assert spec.hidden_acceptance_used is False
    assert spec.private_spec_used is False
    assert spec.reference_patch_used is False


def test_v10_plan_requires_current_read_allowed_candidate_and_exact_check_order() -> None:
    read = _event(1, EventType.TOOL_SUCCEEDED, tool="read_file", diff=EMPTY)
    arguments = {
        "reproduction_status": "static_evidence",
        "hypothesis": "The public source lifecycle needs one bounded correction.",
        "evidence_event_sequences": [1],
        "candidate_files": ["src/anyio/pytest_plugin.py"],
        "planned_check_ids": [check.id for check in TASK.visible_checks],
        "unknowns": [],
    }
    plan = validate_record_work_plan(
        run_id="run_test",
        task=TASK,
        worktree_diff_hash=EMPTY,
        events=[read],
        read_paths_by_sequence={1: "src/anyio/pytest_plugin.py"},
        arguments=arguments,
    )
    assert plan.reproduction_status == "static_evidence"
    with pytest.raises(ContractError, match="unread or outside scope"):
        validate_record_work_plan(
            run_id="run_test",
            task=TASK,
            worktree_diff_hash=EMPTY,
            events=[read],
            read_paths_by_sequence={1: "src/anyio/pytest_plugin.py"},
            arguments={**arguments, "candidate_files": ["tests/test_pytest_plugin.py"]},
        )
    with pytest.raises(ContractError, match="check order"):
        validate_record_work_plan(
            run_id="run_test",
            task=TASK,
            worktree_diff_hash=EMPTY,
            events=[read],
            read_paths_by_sequence={1: "src/anyio/pytest_plugin.py"},
            arguments={
                **arguments,
                "planned_check_ids": list(reversed(arguments["planned_check_ids"])),
            },
        )


def test_v10_plan_rejects_stale_or_other_run_evidence() -> None:
    stale = _event(1, EventType.TOOL_SUCCEEDED, tool="read_file", diff=DIFF)
    arguments = {
        "reproduction_status": "static_evidence",
        "hypothesis": "Public static evidence.",
        "evidence_event_sequences": [1],
        "candidate_files": ["src/anyio/pytest_plugin.py"],
        "planned_check_ids": [check.id for check in TASK.visible_checks],
        "unknowns": [],
    }
    with pytest.raises(ContractError, match="stale"):
        validate_record_work_plan(
            run_id="run_test",
            task=TASK,
            worktree_diff_hash=EMPTY,
            events=[stale],
            read_paths_by_sequence={1: "src/anyio/pytest_plugin.py"},
            arguments=arguments,
        )
    with pytest.raises(ContractError, match="run binding"):
        validate_record_work_plan(
            run_id="run_other",
            task=TASK,
            worktree_diff_hash=DIFF,
            events=[stale],
            read_paths_by_sequence={1: "src/anyio/pytest_plugin.py"},
            arguments=arguments,
        )


def test_v10_removes_mutation_before_plan_and_fails_closed_at_action_limit() -> None:
    evidence = _evidence(mutation=False, diff=EMPTY)
    first = _project([], evidence, runtime="lean-harness-v10")
    assert "apply_structured_edit" not in first.allowed_tool_names
    no_evidence = [
        _event(sequence, EventType.TOOL_CALLED, tool="search_files", diff=EMPTY)
        for sequence in range(1, 11)
    ]
    terminal = _project(no_evidence, evidence, runtime="lean-harness-v10")
    assert terminal.terminal_reason == "pre_mutation_evidence_exhausted"
