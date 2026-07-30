from __future__ import annotations

import json
import sqlite3
import uuid

import pytest

from patchloop.contracts import (
    Checkpoint,
    EventType,
    Phase,
    RunResult,
    RunStatus,
    ToolResult,
    Verdicts,
)
from patchloop.errors import (
    ActionConflict,
    ContractError,
    RunOwnershipConflict,
)
from patchloop.runtime import build_manifest
from patchloop.state import RunOwnershipCoordinator, StateStore
from patchloop.task_loader import load_task_package
from patchloop.util import utc_now


def _manifest():
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    return build_manifest(package, run_id=f"run_test_{uuid.uuid4().hex[:8]}")


def _result(run_id: str) -> RunResult:
    return RunResult(
        run_id=run_id,
        agent_submission_status="completed",
        evaluation_status="completed",
        scope_compliant_success=True,
        verdicts=Verdicts(),
    )


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


def test_worker_claim_is_atomic_and_records_running_reclaim(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    ownership = RunOwnershipCoordinator(tmp_path / "worker-locks")
    manifest = _manifest()
    store.create_run(manifest)

    with ownership.acquire(manifest.run_id) as first:
        initial = store.claim_run_for_worker(
            manifest.run_id,
            owner_id=first.owner_id,
            owner_pid=first.pid,
            owner_hostname=first.hostname,
            allowed_statuses={RunStatus.CREATED},
        )
        assert initial["prior_status"] == RunStatus.CREATED.value
        assert initial["reclaimed"] is False
        with (
            pytest.raises(RunOwnershipConflict, match="active worker"),
            ownership.acquire(manifest.run_id),
        ):
            pass

    with ownership.acquire(manifest.run_id) as second:
        reclaimed = store.claim_run_for_worker(
            manifest.run_id,
            owner_id=second.owner_id,
            owner_pid=second.pid,
            owner_hostname=second.hostname,
            allowed_statuses={RunStatus.RUNNING},
        )

    assert reclaimed["prior_status"] == RunStatus.RUNNING.value
    assert reclaimed["reclaimed"] is True
    assert store.get_run_status(manifest.run_id) == RunStatus.RUNNING
    claims = store.list_worker_claims(manifest.run_id)
    assert [claim["owner_id"] for claim in claims] == [
        first.owner_id,
        second.owner_id,
    ]


def test_initial_worker_claim_creates_and_claims_run_atomically(
    tmp_path,
) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()

    claim = store.claim_run_for_worker(
        manifest.run_id,
        owner_id="worker_initial",
        owner_pid=123,
        owner_hostname="test-host",
        allowed_statuses={RunStatus.CREATED},
        manifest=manifest,
    )

    assert claim["prior_status"] == RunStatus.CREATED.value
    assert store.get_manifest(manifest.run_id) == manifest
    assert store.get_run_status(manifest.run_id) == RunStatus.RUNNING


def test_initial_worker_claim_rolls_back_run_when_claim_insert_fails(
    tmp_path,
) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    with store._connect() as connection:
        connection.execute(
            "CREATE TRIGGER reject_worker_claim "
            "BEFORE INSERT ON run_worker_claims "
            "BEGIN SELECT RAISE(ABORT, 'synthetic claim failure'); END"
        )

    with pytest.raises(sqlite3.IntegrityError, match="synthetic claim failure"):
        store.claim_run_for_worker(
            manifest.run_id,
            owner_id="worker_initial",
            owner_pid=123,
            owner_hostname="test-host",
            allowed_statuses={RunStatus.CREATED},
            manifest=manifest,
        )

    assert store.has_run(manifest.run_id) is False


def test_existing_run_rejects_different_immutable_manifest(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    store.create_run(manifest)
    changed = manifest.model_copy(
        update={
            "budget": manifest.budget.model_copy(
                update={
                    "max_model_calls": manifest.budget.max_model_calls + 1
                }
            )
        }
    )

    with pytest.raises(ContractError, match="stored immutable manifest"):
        store.claim_run_for_worker(
            manifest.run_id,
            owner_id="worker_changed",
            owner_pid=123,
            owner_hostname="test-host",
            allowed_statuses={RunStatus.CREATED},
            manifest=changed,
        )

    assert store.get_run_status(manifest.run_id) == RunStatus.CREATED
    assert store.list_worker_claims(manifest.run_id) == []


def test_worker_claim_accepts_semantically_equal_legacy_manifest_json(
    tmp_path,
) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    store.create_run(manifest)
    legacy_payload = manifest.model_dump(mode="json")
    legacy_payload.pop("memory_policy_version")
    legacy_json = json.dumps(
        legacy_payload,
        separators=(",", ":"),
        sort_keys=True,
    )
    with store._connect() as connection:
        connection.execute(
            "UPDATE runs SET manifest_json = ? WHERE run_id = ?",
            (legacy_json, manifest.run_id),
        )

    store.claim_run_for_worker(
        manifest.run_id,
        owner_id="worker_legacy_manifest",
        owner_pid=123,
        owner_hostname="test-host",
        allowed_statuses={RunStatus.CREATED},
        manifest=manifest,
    )

    assert store.get_manifest(manifest.run_id) == manifest
    with store._connect() as connection:
        row = connection.execute(
            "SELECT manifest_json FROM runs WHERE run_id = ?",
            (manifest.run_id,),
        ).fetchone()
    assert row["manifest_json"] == legacy_json


def test_terminal_run_cannot_be_reclaimed_even_when_lock_is_free(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    ownership = RunOwnershipCoordinator(tmp_path / "worker-locks")
    manifest = _manifest()
    store.create_run(manifest)
    store.claim_run_for_worker(
        manifest.run_id,
        owner_id="worker_terminal",
        owner_pid=123,
        owner_hostname="test-host",
        allowed_statuses={RunStatus.CREATED},
        manifest=manifest,
    )
    store.finalize_run(
        manifest.run_id,
        status=RunStatus.COMPLETED,
        result=_result(manifest.run_id),
        event_type=EventType.RUN_COMPLETED,
        actor="test",
    )

    with (
        ownership.acquire(manifest.run_id) as worker,
        pytest.raises(RunOwnershipConflict, match="cannot be claimed"),
    ):
        store.claim_run_for_worker(
            manifest.run_id,
            owner_id=worker.owner_id,
            owner_pid=worker.pid,
            owner_hostname=worker.hostname,
            allowed_statuses={RunStatus.COMPLETED},
        )


def test_terminal_event_status_and_result_roll_back_together(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    store.create_run(manifest)
    store.claim_run_for_worker(
        manifest.run_id,
        owner_id="worker_terminal_rollback",
        owner_pid=123,
        owner_hostname="test-host",
        allowed_statuses={RunStatus.CREATED},
        manifest=manifest,
    )
    with store._connect() as connection:
        connection.execute(
            "CREATE TRIGGER reject_terminal_event "
            "BEFORE INSERT ON events "
            "BEGIN SELECT RAISE(ABORT, 'synthetic terminal failure'); END"
        )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="synthetic terminal failure",
    ):
        store.finalize_run(
            manifest.run_id,
            status=RunStatus.COMPLETED,
            result=_result(manifest.run_id),
            event_type=EventType.RUN_COMPLETED,
            actor="test",
        )

    assert store.get_run_status(manifest.run_id) == RunStatus.RUNNING
    row = next(
        item
        for item in store.list_runs()
        if item["run_id"] == manifest.run_id
    )
    assert row["result"] is None
    assert store.list_events(manifest.run_id) == []


def test_patch_action_result_and_outcome_events_roll_back_together(
    tmp_path,
) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    store.create_run(manifest)
    action_id = "action-atomic-patch"
    input_hash = "sha256:" + ("1" * 64)
    patch_hash = "sha256:" + ("2" * 64)
    diff_hash = "sha256:" + ("3" * 64)
    store.append_event(
        manifest.run_id,
        EventType.TOOL_CALLED,
        actor="agent",
        correlation_id=action_id,
        payload={"tool": "apply_patch", "input_hash": input_hash},
    )
    result = ToolResult(
        action_id=action_id,
        status="succeeded",
        started_at=utc_now(),
        finished_at=utc_now(),
        output={
            "patch_hash": patch_hash,
            "worktree_diff_hash": diff_hash,
        },
    )
    outcome_payload = {
        "tool": "apply_patch",
        "status": "succeeded",
        "patch_hash": patch_hash,
        "worktree_diff_hash": diff_hash,
    }
    patch_payload = {
        "patch_hash": patch_hash,
        "worktree_diff_hash": diff_hash,
    }
    with store._connect() as connection:
        connection.execute(
            "CREATE TRIGGER reject_patch_applied "
            "BEFORE INSERT ON events "
            "WHEN instr(NEW.event_json, 'PatchApplied') > 0 "
            "BEGIN SELECT RAISE(ABORT, 'synthetic patch event failure'); END"
        )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="synthetic patch event failure",
    ):
        store.complete_action(
            manifest.run_id,
            action_id,
            input_hash,
            result,
            outcome_type=EventType.TOOL_SUCCEEDED,
            outcome_payload=outcome_payload,
            patch_payload=patch_payload,
        )

    assert (
        store.get_action_result(
            manifest.run_id,
            action_id,
            input_hash,
        )
        is None
    )
    events = store.list_events(manifest.run_id)
    assert [event.type for event in events] == [EventType.TOOL_CALLED]


def test_semantic_replay_action_and_events_commit_atomically(
    tmp_path,
) -> None:
    store = StateStore(tmp_path / "state.sqlite3")
    manifest = _manifest()
    store.create_run(manifest)
    action_id = "semantic-replay-atomic"
    input_hash = "sha256:" + ("4" * 64)
    result = ToolResult(
        action_id=action_id,
        status="succeeded",
        started_at=utc_now(),
        finished_at=utc_now(),
        output={"semantic_replay": True},
    )
    specs = [
        (
            EventType.TOOL_CALLED,
            "agent",
            {"tool": "search_files", "input_hash": input_hash},
        ),
        (
            EventType.LOOP_DETECTED,
            "tool-gateway",
            {"schema_version": "investigation-loop-v1"},
        ),
        (
            EventType.TOOL_REPLAYED,
            "semantic-cache",
            {"schema_version": "tool-replayed-v2"},
        ),
    ]
    with store._connect() as connection:
        connection.execute(
            "CREATE TRIGGER reject_semantic_replay "
            "BEFORE INSERT ON events "
            "WHEN instr(NEW.event_json, 'ToolReplayed') > 0 "
            "BEGIN SELECT RAISE(ABORT, 'synthetic replay failure'); END"
        )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="synthetic replay failure",
    ):
        store.complete_nonexecuted_action(
            manifest.run_id,
            action_id,
            input_hash,
            result,
            event_specs=specs,
        )

    assert store.get_action_result(
        manifest.run_id,
        action_id,
        input_hash,
    ) is None
    assert store.list_events(manifest.run_id) == []


def test_worker_identity_failure_releases_process_guard(
    tmp_path,
    monkeypatch,
) -> None:
    ownership = RunOwnershipCoordinator(tmp_path / "worker-locks")
    run_id = _manifest().run_id

    def fail_hostname() -> str:
        raise RuntimeError("synthetic hostname failure")

    monkeypatch.setattr(
        "patchloop.state.ownership.socket.gethostname",
        fail_hostname,
    )
    with (
        pytest.raises(RuntimeError, match="synthetic hostname failure"),
        ownership.acquire(run_id),
    ):
        pass

    monkeypatch.setattr(
        "patchloop.state.ownership.socket.gethostname",
        lambda: "test-host",
    )
    with ownership.acquire(run_id) as worker:
        assert worker.hostname == "test-host"
