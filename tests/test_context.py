from __future__ import annotations

import json
from pathlib import Path

from patchloop.agent.context import (
    RECENT_EVENT_LIMIT,
    TOOL_RESULT_CHARACTER_LIMIT,
    build_context,
    build_context_with_evidence,
)
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import EventType, RunEvent
from patchloop.task_loader import load_task_package
from patchloop.util import utc_now


def test_context_rehydrates_recent_public_tool_result(tmp_path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {"path": "module.py", "content": "def broken(): return True"}
    )
    event = RunEvent(
        event_id="event-1",
        run_id="run_test",
        sequence=1,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload={
            "tool": "read_file",
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
        },
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public
    context, _ = build_context(task, [event], None)
    assert "def broken(): return True" in context
    assert "private.yaml" not in context


def test_context_records_policy_omission_and_tool_result_truncation(tmp_path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {"content": "x" * (TOOL_RESULT_CHARACTER_LIMIT + 1)}
    )
    events = [
        RunEvent(
            event_id=f"event-{sequence}",
            run_id="run_test",
            sequence=sequence,
            type=(
                EventType.TOOL_SUCCEEDED
                if sequence == RECENT_EVENT_LIMIT + 1
                else EventType.PHASE_CHANGED
            ),
            timestamp=utc_now(),
            actor="tool-gateway",
            payload=(
                {
                    "tool": "read_file",
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                }
                if sequence == RECENT_EVENT_LIMIT + 1
                else {"phase": "REPRODUCE"}
            ),
        )
        for sequence in range(1, RECENT_EVENT_LIMIT + 2)
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, events, None)
    original_characters = len(Path(artifact.path).read_text(encoding="utf-8"))

    assert built.evidence["events"]["eligible_count"] == RECENT_EVENT_LIMIT + 1
    assert built.evidence["events"]["included_count"] == RECENT_EVENT_LIMIT
    assert built.evidence["events"]["omitted_count"] == 1
    assert built.evidence["tool_results"] == [
        {
            "event_sequence": RECENT_EVENT_LIMIT + 1,
            "original_characters": original_characters,
            "included_characters": len(
                json.dumps({"unavailable": True}, ensure_ascii=False)
            ),
            "truncated": True,
            "available": True,
        }
    ]
    assert built.evidence["rendered_bytes"] == len(built.rendered.encode("utf-8"))


def test_context_evidence_preserves_last_twelve_raw_event_window() -> None:
    events = [
        RunEvent(
            event_id=f"event-{sequence}",
            run_id="run_test",
            sequence=sequence,
            type=(
                EventType.PHASE_CHANGED
                if sequence == 1
                else EventType.MODEL_CALLED
            ),
            timestamp=utc_now(),
            actor="runner",
            payload={},
        )
        for sequence in range(1, RECENT_EVENT_LIMIT + 2)
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, events, None)

    assert built.evidence["events"]["eligible_count"] == 1
    assert built.evidence["events"]["included_count"] == 0
    assert built.evidence["events"]["omitted_count"] == 1
