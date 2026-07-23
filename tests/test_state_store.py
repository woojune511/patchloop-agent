from __future__ import annotations

import uuid

import pytest

from patchloop.contracts import (
    Checkpoint,
    EventType,
    Phase,
    ToolResult,
)
from patchloop.errors import ActionConflict
from patchloop.runtime import build_manifest
from patchloop.state import StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import utc_now


def _manifest():
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    return build_manifest(package, run_id=f"run_test_{uuid.uuid4().hex[:8]}")


def test_events_are_monotonic_and_checkpoint_is_durable(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    store.create_run(manifest)
    first = store.append_event(manifest.run_id, EventType.RUN_STARTED, actor="test")
    second = store.append_event(manifest.run_id, EventType.PHASE_CHANGED, actor="test")
    assert [first.sequence, second.sequence] == [1, 2]
    checkpoint = Checkpoint(
        checkpoint_id="ckpt_test",
        run_id=manifest.run_id,
        through_sequence=2,
        phase=Phase.REPRODUCE,
        repository_head="abc",
        worktree_diff_hash="sha256:empty",
        created_at=utc_now(),
    )
    store.save_checkpoint(checkpoint)
    assert store.latest_checkpoint(manifest.run_id) == checkpoint


def test_action_id_is_idempotent_but_input_hash_cannot_change(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    store.create_run(manifest)
    result = ToolResult(
        action_id="action-1",
        status="succeeded",
        started_at=utc_now(),
        finished_at=utc_now(),
    )
    store.record_action_result(manifest.run_id, "action-1", "sha256:a", result)
    store.record_action_result(manifest.run_id, "action-1", "sha256:a", result)
    assert store.get_action_result(manifest.run_id, "action-1", "sha256:a") == result
    with pytest.raises(ActionConflict):
        store.get_action_result(manifest.run_id, "action-1", "sha256:b")
