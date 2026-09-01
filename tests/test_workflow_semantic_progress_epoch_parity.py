from __future__ import annotations

from datetime import UTC, datetime

import pytest

from patchloop.agent.workflow_semantic_progress_epoch_parity import (
    project_semantic_progress_event_domain,
    select_semantic_progress_epoch_events,
)
from patchloop.contracts import EventType, RunEvent
from patchloop.errors import RecoveryError

RUN_ID = "run_semantic_progress_epoch_parity"


def _event(sequence: int, event_type: EventType, *, run_id: str = RUN_ID) -> RunEvent:
    return RunEvent(
        event_id=f"evt_epoch_parity_{sequence}",
        run_id=run_id,
        sequence=sequence,
        type=event_type,
        timestamp=datetime(2026, 8, 27, tzinfo=UTC),
        actor="test",
        payload={},
    )


def _r15_shaped_events() -> tuple[RunEvent, ...]:
    return (
        _event(74, EventType.TOOL_SUCCEEDED),
        _event(103, EventType.TOOL_SUCCEEDED),
        _event(106, EventType.MUTATION_BASELINE_RESTORED),
        _event(135, EventType.TOOL_SUCCEEDED),
        _event(152, EventType.MODEL_CALLED),
    )


def test_r15_shaped_domain_selects_only_the_post_restore_suffix() -> None:
    events = _r15_shaped_events()

    first = project_semantic_progress_event_domain(run_id=RUN_ID, events=events)
    second = project_semantic_progress_event_domain(run_id=RUN_ID, events=list(events))

    assert first == second
    assert first.latest_restore_event_sequence == 106
    assert first.epoch_event_sequences == (135, 152)
    assert select_semantic_progress_epoch_events(domain=first, events=events) == events[-2:]
    dispatch_events = (*events, _event(153, EventType.TOOL_CALLED))
    assert (
        select_semantic_progress_epoch_events(
            domain=first,
            events=dispatch_events,
        )
        == events[-2:]
    )


def test_request_domain_tampering_fails_closed_before_event_selection() -> None:
    events = _r15_shaped_events()
    domain = project_semantic_progress_event_domain(run_id=RUN_ID, events=events)
    tampered = domain.model_copy(update={"epoch_event_sequences": (103, 135, 152)})

    with pytest.raises(RecoveryError, match="event domain differs"):
        select_semantic_progress_epoch_events(domain=tampered, events=events)


def test_foreign_run_and_non_monotonic_event_prefixes_fail_closed() -> None:
    foreign = (*_r15_shaped_events(), _event(153, EventType.MODEL_CALLED, run_id="foreign"))
    with pytest.raises(RecoveryError, match="foreign run"):
        project_semantic_progress_event_domain(run_id=RUN_ID, events=foreign)

    non_monotonic = (_event(2, EventType.MODEL_CALLED), _event(1, EventType.TOOL_CALLED))
    with pytest.raises(RecoveryError, match="sequence order"):
        project_semantic_progress_event_domain(run_id=RUN_ID, events=non_monotonic)
