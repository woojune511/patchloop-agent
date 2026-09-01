from __future__ import annotations

from typing import Any

from patchloop.agent.investigation import nominal_tail_reserve
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


def test_v6_reserves_one_review_tool_and_model_turn_without_changing_v5() -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    v5 = nominal_tail_reserve(
        task,
        context_policy_version="phase-evidence-v5",
    )
    v6 = nominal_tail_reserve(
        task,
        context_policy_version="phase-evidence-v6",
    )

    assert v5 == {
        "tool_calls": 6,
        "model_calls": 3,
        "feedback_model_calls": 1,
    }
    assert v6 == {
        "tool_calls": 7,
        "model_calls": 4,
        "feedback_model_calls": 1,
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


def test_v13_completion_policy_forces_check_review_and_submission() -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    check_id = task.visible_checks[0].id
    diff_hash = "sha256:completion-driven"
    events = [
        _event(
            1,
            EventType.PATCH_APPLIED,
            {
                "patch_hash": "sha256:patch",
                "worktree_diff_hash": diff_hash,
            },
        )
    ]

    after_mutation = diff_bound_evidence(
        task,
        events,
        diff_hash,
        phase=Phase.IMPLEMENT,
        completion_driven=True,
    )
    assert after_mutation.allowed_next_actions == ("run_check",)

    events.append(
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": False,
                "worktree_diff_hash": diff_hash,
            },
        )
    )
    after_failed_check = diff_bound_evidence(
        task,
        events,
        diff_hash,
        phase=Phase.IMPLEMENT,
        completion_driven=True,
    )
    assert after_failed_check.allowed_next_actions == (
        "apply_patch",
        "read_file",
        "search_files",
    )

    events.append(
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": True,
                "worktree_diff_hash": diff_hash,
            },
        )
    )
    after_passing_check = diff_bound_evidence(
        task,
        events,
        diff_hash,
        phase=Phase.VERIFY,
        completion_driven=True,
    )
    assert after_passing_check.allowed_next_actions == ("get_diff",)

    events.append(
        _event(
            4,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "worktree_diff_hash": diff_hash},
        )
    )
    ready = diff_bound_evidence(
        task,
        events,
        diff_hash,
        presented_tool_results=[_presented_result(4)],
        phase=Phase.REVIEW,
        completion_driven=True,
    )
    assert ready.submission_ready is True
    assert ready.allowed_next_actions == ("finish_task",)


def test_completion_policy_binds_successful_correction_to_recheck() -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    check_id = task.visible_checks[0].id
    failed_diff = "sha256:failed-diff"
    corrected_diff = "sha256:corrected-diff"
    events = [
        _event(
            1,
            EventType.PATCH_APPLIED,
            {"worktree_diff_hash": failed_diff},
        ),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": False,
                "worktree_diff_hash": failed_diff,
            },
        ),
    ]
    correction = diff_bound_evidence(
        task,
        events,
        failed_diff,
        phase=Phase.IMPLEMENT,
        completion_driven=True,
    )
    assert correction.allowed_next_actions == (
        "apply_patch",
        "read_file",
        "search_files",
    )

    events.append(
        _event(
            3,
            EventType.PATCH_APPLIED,
            {"worktree_diff_hash": corrected_diff},
        )
    )
    recheck = diff_bound_evidence(
        task,
        events,
        corrected_diff,
        phase=Phase.IMPLEMENT,
        completion_driven=True,
    )
    assert recheck.latest_check_sequence is None
    assert recheck.pending_checks == (check_id,)
    assert recheck.allowed_next_actions == ("run_check",)


def test_v6_requires_same_diff_structured_review_presented_to_model() -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    check_id = task.visible_checks[0].id
    diff_hash = "sha256:current"
    events = [
        _event(
            1,
            EventType.PATCH_APPLIED,
            {
                "patch_hash": "sha256:patch",
                "worktree_diff_hash": diff_hash,
            },
        ),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": True,
                "worktree_diff_hash": diff_hash,
            },
        ),
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "worktree_diff_hash": diff_hash},
        ),
    ]

    needs_review = diff_bound_evidence(
        task,
        events,
        diff_hash,
        presented_tool_results=[_presented_result(2), _presented_result(3)],
        phase=Phase.REVIEW,
        structured_review_required=True,
    )

    assert needs_review.submission_ready is False
    assert needs_review.allowed_next_actions == ("review_task", "apply_patch")
    assert "structured_task_review_current_diff" in (
        needs_review.missing_evidence
    )

    events.append(
        _event(
            4,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "review_task",
                "worktree_diff_hash": diff_hash,
                "source_get_diff_sequence": 3,
            },
        )
    )
    not_presented = diff_bound_evidence(
        task,
        events,
        diff_hash,
        presented_tool_results=[_presented_result(2), _presented_result(3)],
        phase=Phase.REVIEW,
        structured_review_required=True,
    )
    assert not_presented.submission_ready is False
    assert "structured_task_review_not_presented" in (
        not_presented.missing_evidence
    )

    ready = diff_bound_evidence(
        task,
        events,
        diff_hash,
        presented_tool_results=[
            _presented_result(2),
            _presented_result(3),
            _presented_result(4),
        ],
        phase=Phase.REVIEW,
        structured_review_required=True,
    )
    assert ready.submission_ready is True
    assert ready.task_review_event_sequence == 4
    assert ready.allowed_next_actions == ("finish_task", "apply_patch")

    events.append(
        _event(
            5,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_probe",
                "passed": False,
                "timed_out": False,
                "worktree_diff_hash": diff_hash,
            },
        )
    )
    invalidated = diff_bound_evidence(
        task,
        events,
        diff_hash,
        presented_tool_results=[
            _presented_result(2),
            _presented_result(3),
            _presented_result(4),
            _presented_result(5),
        ],
        phase=Phase.REVIEW,
        structured_review_required=True,
        probe_available=True,
    )
    assert invalidated.submission_ready is False
    assert invalidated.task_review_event_sequence is None
    assert invalidated.allowed_next_actions == (
        "review_task",
        "apply_patch",
        "run_probe",
    )


def test_v6_rejects_structured_review_from_prior_diff() -> None:
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    check_id = task.visible_checks[0].id
    old_hash = "sha256:old"
    new_hash = "sha256:new"
    events = [
        _event(
            1,
            EventType.PATCH_APPLIED,
            {
                "patch_hash": "sha256:patch-1",
                "worktree_diff_hash": old_hash,
            },
        ),
        _event(
            2,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": True,
                "worktree_diff_hash": old_hash,
            },
        ),
        _event(
            3,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "worktree_diff_hash": old_hash},
        ),
        _event(
            4,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "review_task",
                "worktree_diff_hash": old_hash,
                "source_get_diff_sequence": 3,
            },
        ),
        _event(
            5,
            EventType.PATCH_APPLIED,
            {
                "patch_hash": "sha256:patch-2",
                "worktree_diff_hash": new_hash,
            },
        ),
        _event(
            6,
            EventType.TOOL_SUCCEEDED,
            {
                "tool": "run_check",
                "check_id": check_id,
                "passed": True,
                "worktree_diff_hash": new_hash,
            },
        ),
        _event(
            7,
            EventType.TOOL_SUCCEEDED,
            {"tool": "get_diff", "worktree_diff_hash": new_hash},
        ),
    ]

    evidence = diff_bound_evidence(
        task,
        events,
        new_hash,
        presented_tool_results=[
            _presented_result(4),
            _presented_result(6),
            _presented_result(7),
        ],
        phase=Phase.REVIEW,
        structured_review_required=True,
    )

    assert evidence.task_review_event_sequence is None
    assert evidence.submission_ready is False
