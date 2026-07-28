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
    tool_result = built.evidence["tool_results"][0]
    assert {
        key: value
        for key, value in tool_result.items()
        if key != "included_characters"
    } == {
        "event_sequence": RECENT_EVENT_LIMIT + 1,
        "original_characters": original_characters,
        "truncated": True,
        "available": True,
        "tool": "read_file",
        "worktree_diff_hash": None,
        "artifact_id": artifact.artifact_id,
    }
    assert tool_result["included_characters"] > len(
        json.dumps({"unavailable": True}, ensure_ascii=False)
    )
    assert '"unavailable": true' not in built.rendered
    assert "field truncated for model context" in built.rendered
    assert built.evidence["rendered_bytes"] == len(built.rendered.encode("utf-8"))


def test_context_evidence_filters_before_selecting_recent_window() -> None:
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
    assert built.evidence["events"]["included_count"] == 1
    assert built.evidence["events"]["omitted_count"] == 0
    assert built.evidence["events"]["included_sequences"] == [1]


def test_legacy_context_policy_preserves_raw_window_and_truncation(tmp_path) -> None:
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
                if sequence == 1
                else EventType.MODEL_CALLED
            ),
            timestamp=utc_now(),
            actor="runner",
            payload=(
                {
                    "tool": "read_file",
                    "artifact_id": artifact.artifact_id,
                    "artifact_path": artifact.path,
                }
                if sequence == 1
                else {}
            ),
        )
        for sequence in range(1, RECENT_EVENT_LIMIT + 2)
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(
        task,
        events,
        None,
        policy_version="v1",
    )

    assert built.evidence["schema_version"] == "context-build-evidence-v1"
    assert built.evidence["events"]["eligible_count"] == 1
    assert built.evidence["events"]["included_count"] == 0
    assert "phase_contract" not in built.rendered


def test_semantic_truncation_remains_bounded_for_large_result_lists(
    tmp_path,
) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {
            "matches": [
                {"path": f"module_{index}.py", "text": "x" * 200}
                for index in range(500)
            ],
            "truncated": False,
        }
    )
    event = RunEvent(
        event_id="event-large-list",
        run_id="run_test",
        sequence=1,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload={
            "tool": "search_files",
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
        },
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, [event], None)
    evidence = built.evidence["tool_results"][0]

    assert evidence["truncated"] is True
    assert evidence["available"] is True
    assert evidence["included_characters"] <= TOOL_RESULT_CHARACTER_LIMIT
    assert "top_level_keys" in built.rendered


def test_semantic_truncation_bounds_oversized_object_keys(tmp_path) -> None:
    artifact = ArtifactStore(tmp_path / "artifacts").put_json(
        {
            f"{'k' * 1_000}-{index}": {"value": "x" * 500}
            for index in range(50)
        }
    )
    event = RunEvent(
        event_id="event-large-keys",
        run_id="run_test",
        sequence=1,
        type=EventType.TOOL_SUCCEEDED,
        timestamp=utc_now(),
        actor="tool-gateway",
        payload={
            "tool": "search_files",
            "artifact_id": artifact.artifact_id,
            "artifact_path": artifact.path,
        },
    )
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, [event], None)
    evidence = built.evidence["tool_results"][0]

    assert evidence["truncated"] is True
    assert evidence["included_characters"] <= TOOL_RESULT_CHARACTER_LIMIT
    assert len(built.rendered) < 20_000


def test_next_context_keeps_current_turn_loop_signal_outside_recent_window() -> None:
    events = [
        RunEvent(
            event_id="event-1",
            run_id="run_test",
            sequence=1,
            type=EventType.MODEL_CALLED,
            timestamp=utc_now(),
            actor="model-adapter",
            payload={},
        ),
        RunEvent(
            event_id="event-2",
            run_id="run_test",
            sequence=2,
            type=EventType.LOOP_DETECTED,
            timestamp=utc_now(),
            actor="tool-gateway",
            payload={
                "tool": "search_files",
                "occurrences": 2,
                "enforcement": "advisory",
            },
        ),
        *[
            RunEvent(
                event_id=f"event-{sequence}",
                run_id="run_test",
                sequence=sequence,
                type=EventType.PHASE_CHANGED,
                timestamp=utc_now(),
                actor="runner",
                payload={"from": "REPRODUCE", "to": "REPRODUCE"},
            )
            for sequence in range(3, RECENT_EVENT_LIMIT + 4)
        ],
    ]
    task = load_task_package("tasks/smoke/csv-quoted-newline").public

    built = build_context_with_evidence(task, events, None)
    rendered = json.loads(built.rendered)

    assert 2 not in built.evidence["events"]["included_sequences"]
    assert rendered["execution_signals"]["repeated_calls"] == [
        {
            "sequence": 2,
            "tool": "search_files",
            "occurrences": 2,
            "enforcement": "advisory",
        }
    ]
