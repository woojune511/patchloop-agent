from __future__ import annotations

import pytest

from patchloop.agent.model import ModelTurn, RequestedTool
from patchloop.agent.runner import AgentRunner
from patchloop.contracts import EventType, Phase, RunOutcomeKind
from patchloop.errors import InjectedFault

TASK = "tasks/smoke/csv-quoted-newline/public.yaml"


def _finish_events(runner: AgentRunner, run_id: str, event_type: EventType):
    return [
        event
        for event in runner.state.list_events(run_id)
        if event.type == event_type
        and (
            event.payload.get("tool") == "finish_task"
            or event.type
            in {
                EventType.REVIEW_RECORDED,
                EventType.SUBMISSION_ATTEMPTED,
                EventType.SUBMISSION_ACCEPTED,
                EventType.SUBMISSION_REJECTED,
            }
        )
        and event.payload.get("submission_method")
        != "legacy_done_text"
    ]


@pytest.mark.parametrize(
    "crash_stage",
    [
        "tool_called",
        "action_result",
        "review",
        "attempt",
        "tool_succeeded",
        "accepted",
        "done_transition",
        "before_done_checkpoint_event",
        "after_done_checkpoint",
    ],
)
def test_finish_task_recovery_appends_only_missing_lifecycle_suffix(
    tmp_path,
    monkeypatch,
    crash_stage: str,
) -> None:
    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")
    original_append = runner.state.append_event
    original_reconcile = runner._reconcile_finish_task_lifecycle
    original_complete = runner._complete_accepted_submission
    armed = True
    accepted_seen = False

    def crash_after_selected_event(
        run_id,
        event_type,
        *,
        actor,
        payload=None,
        correlation_id=None,
    ):
        nonlocal armed, accepted_seen
        payload = payload or {}
        is_finish_call = (
            event_type == EventType.TOOL_CALLED
            and payload.get("tool") == "finish_task"
        )
        is_finish_success = (
            event_type == EventType.TOOL_SUCCEEDED
            and payload.get("tool") == "finish_task"
        )
        is_done_transition = (
            event_type == EventType.PHASE_CHANGED
            and payload.get("to") == Phase.DONE.value
        )
        is_done_checkpoint = (
            event_type == EventType.CHECKPOINT_SAVED and accepted_seen
        )
        if (
            armed
            and crash_stage == "before_done_checkpoint_event"
            and is_done_checkpoint
        ):
            armed = False
            raise InjectedFault("crash before durable checkpoint event")
        event = original_append(
            run_id,
            event_type,
            actor=actor,
            payload=payload,
            correlation_id=correlation_id,
        )
        if event_type == EventType.SUBMISSION_ACCEPTED:
            accepted_seen = True
        should_crash = {
            "tool_called": is_finish_call,
            "review": event_type == EventType.REVIEW_RECORDED,
            "attempt": (
                event_type == EventType.SUBMISSION_ATTEMPTED
                and payload.get("submission_method") == "finish_task"
            ),
            "tool_succeeded": is_finish_success,
            "accepted": event_type == EventType.SUBMISSION_ACCEPTED,
            "done_transition": is_done_transition,
        }.get(crash_stage, False)
        if armed and should_crash:
            armed = False
            raise InjectedFault(f"crash after {crash_stage}")
        return event

    def crash_after_action_result(*args, **kwargs):
        nonlocal armed
        if armed:
            armed = False
            raise InjectedFault("crash after durable action result")
        return original_reconcile(*args, **kwargs)

    def crash_after_done_checkpoint(*args, **kwargs):
        nonlocal armed
        completed = original_complete(*args, **kwargs)
        if armed:
            armed = False
            raise InjectedFault("crash after durable DONE checkpoint")
        return completed

    monkeypatch.setattr(runner.state, "append_event", crash_after_selected_event)
    if crash_stage == "action_result":
        monkeypatch.setattr(
            runner,
            "_reconcile_finish_task_lifecycle",
            crash_after_action_result,
        )
    if crash_stage == "after_done_checkpoint":
        monkeypatch.setattr(
            runner,
            "_complete_accepted_submission",
            crash_after_done_checkpoint,
        )

    suspended = runner.start(TASK, model="mock")

    assert suspended["status"] == "suspended"
    monkeypatch.setattr(runner.state, "append_event", original_append)
    monkeypatch.setattr(
        runner,
        "_reconcile_finish_task_lifecycle",
        original_reconcile,
    )
    monkeypatch.setattr(
        runner,
        "_complete_accepted_submission",
        original_complete,
    )

    result = runner.resume(suspended["run_id"])
    events = runner.state.list_events(suspended["run_id"])
    done_transitions = [
        event
        for event in events
        if event.type == EventType.PHASE_CHANGED
        and event.payload.get("from") == Phase.REVIEW.value
        and event.payload.get("to") == Phase.DONE.value
    ]

    assert result["scope_compliant_success"] is True
    assert len(_finish_events(runner, suspended["run_id"], EventType.TOOL_CALLED)) == 1
    assert len(_finish_events(runner, suspended["run_id"], EventType.REVIEW_RECORDED)) == 1
    assert len(
        _finish_events(
            runner,
            suspended["run_id"],
            EventType.SUBMISSION_ATTEMPTED,
        )
    ) == 1
    assert len(_finish_events(runner, suspended["run_id"], EventType.TOOL_SUCCEEDED)) == 1
    assert len(
        _finish_events(
            runner,
            suspended["run_id"],
            EventType.SUBMISSION_ACCEPTED,
        )
    ) == 1
    assert len(done_transitions) == 1
    checkpoint = runner.state.latest_checkpoint(suspended["run_id"])
    assert checkpoint is not None
    assert checkpoint.phase == Phase.DONE
    assert sum(
        event.type == EventType.CHECKPOINT_SAVED
        and event.payload.get("checkpoint_id") == checkpoint.checkpoint_id
        for event in events
    ) == 1


def test_third_rejected_finish_is_terminal_when_action_result_is_restored(
    tmp_path,
    monkeypatch,
) -> None:
    class PrematureSubmissionAdapter:
        def __init__(self) -> None:
            self.offset = 0

        def next_turn(self, _context, _tools):
            self.offset += 1
            return ModelTurn(
                tool_calls=[
                    RequestedTool(
                        "finish_task",
                        f"premature-finish-{self.offset}",
                        {},
                    )
                ]
            )

    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: PrematureSubmissionAdapter(),
    )
    original_append = runner.state.append_event
    armed = True

    def crash_after_third_call(
        run_id,
        event_type,
        *,
        actor,
        payload=None,
        correlation_id=None,
    ):
        nonlocal armed
        payload = payload or {}
        event = original_append(
            run_id,
            event_type,
            actor=actor,
            payload=payload,
            correlation_id=correlation_id,
        )
        recovery_result = payload.get("recovery_result", {})
        output = (
            recovery_result.get("output", {})
            if isinstance(recovery_result, dict)
            else {}
        )
        if (
            armed
            and event_type == EventType.TOOL_CALLED
            and payload.get("tool") == "finish_task"
            and output.get("submission_attempt_number") == 3
        ):
            armed = False
            raise InjectedFault("crash before third action result")
        return event

    monkeypatch.setattr(runner.state, "append_event", crash_after_third_call)
    suspended = runner.start(TASK, model="mock")
    assert suspended["status"] == "suspended"
    monkeypatch.setattr(runner.state, "append_event", original_append)

    result = runner.resume(suspended["run_id"])
    events = runner.state.list_events(suspended["run_id"])

    assert result["outcome_kind"] == RunOutcomeKind.AGENT_FAILURE.value
    assert result["terminal_error"]["type"] == "SubmissionProtocolError"
    assert sum(
        event.type == EventType.SUBMISSION_REJECTED for event in events
    ) == 3
    assert sum(
        event.type == EventType.TOOL_CALLED
        and event.payload.get("tool") == "finish_task"
        for event in events
    ) == 3


def test_legacy_done_attempts_and_rejections_have_one_to_one_correlations(
    tmp_path,
    monkeypatch,
) -> None:
    class LegacyDoneAdapter:
        def next_turn(self, _context, _tools):
            return ModelTurn(text="DONE", done=True)

    monkeypatch.setattr(
        "patchloop.agent.runner.DockerSandbox.available",
        lambda: False,
    )
    runner = AgentRunner(tmp_path / "runtime")
    monkeypatch.setattr(
        runner,
        "_model_adapter",
        lambda *_args: LegacyDoneAdapter(),
    )

    result = runner.start(TASK, model="mock")
    events = runner.state.list_events(result["run_id"])
    attempts = [
        event
        for event in events
        if event.type == EventType.SUBMISSION_ATTEMPTED
    ]
    rejections = [
        event
        for event in events
        if event.type == EventType.SUBMISSION_REJECTED
    ]

    assert result["terminal_error"]["type"] == "SubmissionProtocolError"
    assert len(attempts) == len(rejections) == 3
    assert all(event.correlation_id is not None for event in attempts)
    assert len({event.correlation_id for event in attempts}) == 3
    assert {
        (
            event.correlation_id,
            event.payload["attempt_number"],
            event.payload["worktree_diff_hash"],
        )
        for event in attempts
    } == {
        (
            event.correlation_id,
            event.payload["attempt_number"],
            event.payload["worktree_diff_hash"],
        )
        for event in rejections
    }
