from __future__ import annotations

from typing import Any

from patchloop.agent.phases import diff_bound_evidence
from patchloop.contracts import EventType, Phase, RunEvent
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_text, utc_now


def _event(
    sequence: int,
    event_type: EventType,
    payload: dict[str, Any],
) -> RunEvent:
    return RunEvent(
        event_id=f"event-{sequence}",
        run_id="run_test",
        sequence=sequence,
        type=event_type,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload=payload,
    )


def _presented_result(sequence: int) -> dict[str, Any]:
    return {
        "event_sequence": sequence,
        "available": True,
        "truncated": False,
    }


def test_returning_to_prior_diff_starts_a_new_mutation_epoch() -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    check_id = task.visible_checks[0].id
    h1 = "sha256:h1"
    h2 = "sha256:h2"
    events = [
        _event(
            1,
            EventType.PATCH_APPLIED,
            {"patch_hash": "sha256:patch-1", "worktree_diff_hash": h1},
        ),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": True,
                "worktree_diff_hash": h1,
            },
        ),
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "worktree_diff_hash": h1},
        ),
        _event(
            4,
            EventType.PATCH_APPLIED,
            {"patch_hash": "sha256:patch-2", "worktree_diff_hash": h2},
        ),
        _event(
            5,
            EventType.PATCH_APPLIED,
            {"patch_hash": "sha256:patch-3", "worktree_diff_hash": h1},
        ),
    ]

    stale = diff_bound_evidence(
        task,
        events,
        h1,
        presented_tool_results=[_presented_result(3)],
        phase=Phase.REVIEW,
    )

    assert stale.completed_checks == ()
    assert stale.pending_checks == (check_id,)
    assert stale.review_event_sequence is None
    assert stale.submission_ready is False

    events.append(
        _event(
            6,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": True,
                "worktree_diff_hash": h1,
            },
        )
    )
    checked = diff_bound_evidence(
        task,
        events,
        h1,
        presented_tool_results=[_presented_result(3)],
        phase=Phase.REVIEW,
    )

    assert checked.completed_checks == (check_id,)
    assert checked.review_event_sequence is None
    assert checked.submission_ready is False

    events.append(
        _event(
            7,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "worktree_diff_hash": h1},
        )
    )
    current = diff_bound_evidence(
        task,
        events,
        h1,
        presented_tool_results=[_presented_result(7)],
        phase=Phase.REVIEW,
    )

    assert current.completed_checks == (check_id,)
    assert current.review_event_sequence == 7
    assert current.submission_ready is True


def test_passing_base_checks_and_review_cannot_submit_a_noop() -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    check_id = task.visible_checks[0].id
    empty_diff = sha256_text("")
    events = [
        _event(
            1,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": True,
                "worktree_diff_hash": empty_diff,
            },
        ),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "worktree_diff_hash": empty_diff},
        ),
    ]

    evidence = diff_bound_evidence(
        task,
        events,
        empty_diff,
        presented_tool_results=[_presented_result(2)],
        phase=Phase.REVIEW,
    )

    assert evidence.mutation_present is False
    assert evidence.submission_ready is False
    assert "successful_mutation_current_diff" in evidence.missing_evidence
    assert evidence.allowed_next_actions[0] == "apply_patch"
