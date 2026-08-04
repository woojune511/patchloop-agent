from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from patchloop.contracts import EventType, RunEvent
from patchloop.evals.policy_replay import (
    ObservedSuffix,
    PolicyReplayError,
    PolicyReplayResult,
    aggregate_policy_replays,
    project_public_trajectory,
    public_event_projection_hash,
    replay_absolute_context_ceiling,
    replay_relative_context_growth,
    replay_repeated_rejection,
    select_panel_decision,
)
from patchloop.util import sha256_json

_START = datetime(2026, 8, 4, tzinfo=UTC)
_WORKTREE_A = "sha256:" + "a" * 64
_WORKTREE_B = "sha256:" + "b" * 64


def _event(
    sequence: int,
    event_type: EventType,
    *,
    payload: dict[str, object] | None = None,
    run_id: str = "run_synthetic",
    correlation_id: str | None = None,
) -> RunEvent:
    return RunEvent(
        event_id=f"evt_{run_id}_{sequence}",
        run_id=run_id,
        sequence=sequence,
        type=event_type,
        timestamp=_START + timedelta(seconds=sequence),
        actor="test",
        correlation_id=correlation_id,
        payload=payload or {},
    )


def _context(sequence: int, characters: int, *, run_id: str = "run_synthetic") -> RunEvent:
    return _event(
        sequence,
        EventType.CONTEXT_BUILT,
        run_id=run_id,
        payload={
            "context_characters": characters,
            "included_event_count": 12,
            "omitted_event_count": max(0, sequence - 12),
        },
    )


def _model(sequence: int, total_tokens: int, *, run_id: str = "run_synthetic") -> RunEvent:
    input_tokens = total_tokens - 1
    return _event(
        sequence,
        EventType.MODEL_CALLED,
        run_id=run_id,
        payload={
            "requested_input_tokens": input_tokens,
            "input_tokens": input_tokens,
            "output_tokens": 1,
            "total_tokens": total_tokens,
            "duration_ms": 10,
        },
    )


def _apply_call(
    sequence: int,
    correlation_id: str,
    *,
    worktree_diff_hash: str = _WORKTREE_A,
    run_id: str = "run_synthetic",
    extra: dict[str, object] | None = None,
) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_CALLED,
        run_id=run_id,
        correlation_id=correlation_id,
        payload={
            "tool": "apply_patch",
            "worktree_diff_hash": worktree_diff_hash,
            **(extra or {}),
        },
    )


def _apply_failure(
    sequence: int,
    correlation_id: str,
    *,
    run_id: str = "run_synthetic",
    extra_payload: dict[str, object] | None = None,
    extra_details: dict[str, object] | None = None,
) -> RunEvent:
    return _event(
        sequence,
        EventType.TOOL_FAILED,
        run_id=run_id,
        correlation_id=correlation_id,
        payload={
            "tool": "apply_patch",
            "status": "rejected",
            "error_code": "CONTRACT_ERROR",
            "error_details": {
                "stage": "context",
                "reason": "git_apply_failed",
                **(extra_details or {}),
            },
            **(extra_payload or {}),
        },
    )


def _rejection_stream(*, later_progress: bool) -> tuple[RunEvent, ...]:
    tail_event = (
        _event(10, EventType.PATCH_APPLIED)
        if later_progress
        else _event(10, EventType.FAILURE_TAGGED)
    )
    return (
        _event(1, EventType.RUN_STARTED),
        _event(
            2,
            EventType.PHASE_CHANGED,
            payload={"from": "INTAKE", "to": "REPRODUCE"},
        ),
        _apply_call(3, "action_1"),
        _apply_failure(4, "action_1"),
        _model(5, 30),
        _apply_call(6, "action_2"),
        _apply_failure(7, "action_2"),
        _model(8, 70),
        _event(9, EventType.TOOL_CALLED, payload={"tool": "search_files"}),
        tail_event,
        _event(
            11,
            EventType.RUN_FAILED,
            payload={
                "error_code": "MODEL_GENERATION_BUDGET_EXCEEDED",
                "error_type": "ModelGenerationBudgetError",
                "outcome_kind": "agent_failure",
            },
        ),
    )


def _aggregate_row(
    *,
    run_id: str,
    task_id: str,
    policy_kind: str = "repeated_rejection",
    policy_id: str = "repeated-rejection-n3",
    false_stop: bool = False,
) -> PolicyReplayResult:
    return PolicyReplayResult(
        policy_id=policy_id,
        policy_kind=policy_kind,  # type: ignore[arg-type]
        run_id=run_id,
        task_id=task_id,
        triggered=True,
        trigger_sequence=3,
        trigger_fingerprint="sha256:" + "c" * 64,
        trigger_context_characters=None,
        trigger_baseline_context_characters=None,
        trigger_completed_model_calls_since_progress=None,
        later_progress_sequences=(4,) if false_stop else (),
        false_stop=false_stop,
        observed_suffix=ObservedSuffix(
            model_tokens=30,
            model_calls=2,
            tool_calls=1,
            wall_clock_ms=300,
        ),
        run_total_model_tokens=100,
        run_duration_ms=1_000,
    )


def test_apply_rejection_fingerprint_recovers_correlated_call_worktree_hash() -> None:
    events = (
        _event(1, EventType.RUN_STARTED),
        _apply_call(2, "action_a", worktree_diff_hash=_WORKTREE_A),
        _apply_failure(3, "action_a"),
        _apply_call(4, "action_b", worktree_diff_hash=_WORKTREE_B),
        _apply_failure(5, "action_b"),
    )

    trajectory = project_public_trajectory(events, task_id="task-a")

    expected_a = sha256_json(
        {
            "schema_version": "public-apply-rejection-fingerprint-v1",
            "tool": "apply_patch",
            "status": "rejected",
            "error_code": "CONTRACT_ERROR",
            "stage": "context",
            "reason": "git_apply_failed",
            "worktree_diff_hash": _WORKTREE_A,
        }
    )
    expected_b = sha256_json(
        {
            "schema_version": "public-apply-rejection-fingerprint-v1",
            "tool": "apply_patch",
            "status": "rejected",
            "error_code": "CONTRACT_ERROR",
            "stage": "context",
            "reason": "git_apply_failed",
            "worktree_diff_hash": _WORKTREE_B,
        }
    )
    assert [item.fingerprint for item in trajectory.rejections] == [
        expected_a,
        expected_b,
    ]
    assert expected_a != expected_b


def test_projection_ignores_candidate_and_error_message_metadata() -> None:
    first = (
        _event(1, EventType.RUN_STARTED),
        _apply_call(
            2,
            "first-correlation",
            extra={
                "patch_artifact": {"content_hash": "sha256:" + "1" * 64},
                "input_hash": "sha256:" + "2" * 64,
            },
        ),
        _apply_failure(
            3,
            "first-correlation",
            extra_payload={"error_message": "candidate one failed"},
            extra_details={
                "guidance": "retry candidate one",
                "candidate_content_hash": "sha256:" + "3" * 64,
            },
        ),
    )
    second = (
        _event(1, EventType.RUN_STARTED),
        _apply_call(
            2,
            "second-correlation",
            extra={
                "patch_artifact": {"content_hash": "sha256:" + "4" * 64},
                "input_hash": "sha256:" + "5" * 64,
            },
        ),
        _apply_failure(
            3,
            "second-correlation",
            extra_payload={"error_message": "different private candidate failed"},
            extra_details={
                "guidance": "different guidance",
                "candidate_content_hash": "sha256:" + "6" * 64,
            },
        ),
    )

    first_trajectory = project_public_trajectory(first, task_id="task-a")
    second_trajectory = project_public_trajectory(second, task_id="task-a")

    assert public_event_projection_hash(first) == public_event_projection_hash(second)
    assert first_trajectory.rejections == second_trajectory.rejections


def test_repeated_rejection_distinguishes_false_stop_from_safe_suffix() -> None:
    false_stop = replay_repeated_rejection(
        project_public_trajectory(
            _rejection_stream(later_progress=True), task_id="task-a"
        ),
        threshold=2,
    )
    safe = replay_repeated_rejection(
        project_public_trajectory(
            _rejection_stream(later_progress=False), task_id="task-a"
        ),
        threshold=2,
    )

    assert false_stop.trigger_sequence == safe.trigger_sequence == 7
    assert false_stop.false_stop is True
    assert false_stop.later_progress_sequences == (10,)
    assert safe.false_stop is False
    assert safe.later_progress_sequences == ()
    assert safe.observed_suffix == ObservedSuffix(
        model_tokens=70,
        model_calls=1,
        tool_calls=1,
        wall_clock_ms=4_000,
    )
    assert safe.run_total_model_tokens == 100


def test_relative_and_absolute_context_replay_use_public_progress_epoch() -> None:
    events = (
        _event(1, EventType.RUN_STARTED),
        _event(
            2,
            EventType.PHASE_CHANGED,
            payload={"from": "INTAKE", "to": "REPRODUCE"},
        ),
        _context(3, 100),
        _model(4, 10),
        _context(5, 190),
        _event(6, EventType.PATCH_APPLIED),
        _context(7, 300),
        _model(8, 20),
        _context(9, 599),
        _model(10, 30),
        _context(11, 600),
        _event(12, EventType.SUBMISSION_ATTEMPTED),
        _event(13, EventType.RUN_COMPLETED),
    )
    trajectory = project_public_trajectory(events, task_id="task-context")

    relative = replay_relative_context_growth(
        trajectory,
        multiplier=2,
        minimum_completed_model_calls=2,
    )
    too_high = replay_relative_context_growth(
        trajectory,
        multiplier=3,
        minimum_completed_model_calls=2,
    )
    absolute = replay_absolute_context_ceiling(
        trajectory,
        maximum_context_characters=500,
    )

    assert relative.trigger_sequence == 11
    assert relative.trigger_context_characters == 600
    assert relative.trigger_baseline_context_characters == 300
    assert relative.trigger_completed_model_calls_since_progress == 2
    assert relative.later_progress_sequences == (12,)
    assert relative.false_stop is True
    assert too_high.triggered is False
    assert too_high.false_stop is None
    assert absolute.policy_kind == "absolute_context_ceiling_sensitivity"
    assert absolute.trigger_sequence == 9
    assert absolute.trigger_context_characters == 599
    assert absolute.trigger_baseline_context_characters == 300
    assert absolute.trigger_completed_model_calls_since_progress == 1


def test_policy_aggregation_applies_loto_and_admission_scope() -> None:
    four_tasks = tuple(
        _aggregate_row(run_id=f"run_{index}", task_id=f"task-{index}")
        for index in range(4)
    )
    admitted = aggregate_policy_replays(
        four_tasks,
        panel_task_ids=[item.task_id for item in four_tasks],
    )

    assert admitted.zero_false_stops_passed is True
    assert admitted.minimum_task_coverage_passed is True
    assert admitted.minimum_savings_passed is True
    assert admitted.leave_one_task_out_passed is True
    assert admitted.observed_suffix_token_fraction_ppm == 300_000
    assert admitted.observed_suffix_wall_fraction_ppm == 300_000
    assert admitted.admitted is True
    assert select_panel_decision([admitted]) == (
        "admit-generic-repeated-rejection-fail-fast-for-offline-runtime-e2e"
    )

    three_tasks = four_tasks[:3]
    loto_failure = aggregate_policy_replays(
        three_tasks,
        panel_task_ids=[item.task_id for item in three_tasks],
    )
    assert loto_failure.minimum_task_coverage_passed is True
    assert loto_failure.leave_one_task_out_passed is False
    assert loto_failure.admitted is False

    sensitivity_rows = tuple(
        _aggregate_row(
            run_id=f"sensitivity_{index}",
            task_id=f"task-{index}",
            policy_kind="absolute_context_ceiling_sensitivity",
            policy_id="absolute-context-100000",
        )
        for index in range(4)
    )
    sensitivity = aggregate_policy_replays(
        sensitivity_rows,
        panel_task_ids=[item.task_id for item in sensitivity_rows],
        admission_scope=False,
    )
    assert sensitivity.leave_one_task_out_passed is True
    assert sensitivity.admission_scope is False
    assert sensitivity.admitted is False
    assert select_panel_decision([sensitivity]) == (
        "retain-current-policy-and-count-qualified-budget-terminal-as-agent-failure"
    )


@pytest.mark.parametrize(
    "events, message",
    [
        (
            (
                _event(1, EventType.RUN_STARTED),
                _apply_failure(2, "missing-call"),
            ),
            "must correlate",
        ),
        (
            (
                _event(1, EventType.RUN_STARTED),
                _apply_failure(2, "late-call"),
                _apply_call(3, "late-call"),
            ),
            "must follow",
        ),
        (
            (
                _event(1, EventType.RUN_STARTED),
                _apply_call(2, "duplicate-call"),
                _apply_call(3, "duplicate-call"),
            ),
            "must be unique",
        ),
        (
            (
                _event(1, EventType.RUN_STARTED),
                _context(3, 100),
            ),
            "sequence is not contiguous",
        ),
    ],
)
def test_malformed_correlation_and_order_fail_closed(
    events: tuple[RunEvent, ...], message: str
) -> None:
    with pytest.raises(PolicyReplayError, match=message):
        project_public_trajectory(events, task_id="task-malformed")
