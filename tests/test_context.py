from __future__ import annotations

from patchloop.agent.context import build_context
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
