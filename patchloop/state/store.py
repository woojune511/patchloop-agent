"""SQLite-backed append-only events, checkpoints, and idempotent actions."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path

from patchloop.contracts import (
    Checkpoint,
    EventType,
    RunEvent,
    RunManifest,
    RunStatus,
    ToolResult,
)
from patchloop.errors import ActionConflict, RecoveryError
from patchloop.util import canonical_json, utc_now


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    manifest_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    result_json TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    event_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, sequence),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    through_sequence INTEGER NOT NULL,
                    checkpoint_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS action_results (
                    run_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, action_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                """
            )

    def create_run(self, manifest: RunManifest) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, manifest_json, status, created_at) VALUES (?, ?, ?, ?)",
                (
                    manifest.run_id,
                    canonical_json(manifest.model_dump(mode="json")),
                    RunStatus.CREATED.value,
                    manifest.created_at.isoformat(),
                ),
            )

    def has_run(self, run_id: str) -> bool:
        with self._connect() as connection:
            return (
                connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone()
                is not None
            )

    def get_manifest(self, run_id: str) -> RunManifest:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT manifest_json FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise RecoveryError(f"unknown run: {run_id}")
        return RunManifest.model_validate_json(row["manifest_json"])

    def list_runs(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id, status, created_at, manifest_json, result_json "
                "FROM runs ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "status": row["status"],
                "created_at": row["created_at"],
                "manifest": json.loads(row["manifest_json"]),
                "result": json.loads(row["result_json"]) if row["result_json"] else None,
            }
            for row in rows
        ]

    def set_run_status(self, run_id: str, status: RunStatus, result: dict | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status = ?, result_json = COALESCE(?, result_json) "
                "WHERE run_id = ?",
                (status.value, canonical_json(result) if result is not None else None, run_id),
            )

    def append_event(
        self,
        run_id: str,
        event_type: EventType,
        *,
        actor: str,
        payload: dict | None = None,
        correlation_id: str | None = None,
    ) -> RunEvent:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            sequence = int(row["value"]) + 1
            event = RunEvent(
                event_id=f"evt_{uuid.uuid4().hex}",
                run_id=run_id,
                sequence=sequence,
                type=event_type,
                timestamp=utc_now(),
                actor=actor,
                correlation_id=correlation_id,
                payload=payload or {},
            )
            connection.execute(
                "INSERT INTO events(run_id, sequence, event_id, event_json) VALUES (?, ?, ?, ?)",
                (run_id, sequence, event.event_id, canonical_json(event.model_dump(mode="json"))),
            )
            connection.commit()
        return event

    def list_events(self, run_id: str) -> list[RunEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence", (run_id,)
            ).fetchall()
        return [RunEvent.model_validate_json(row["event_json"]) for row in rows]

    def last_sequence(self, run_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value FROM events WHERE run_id = ?", (run_id,)
            ).fetchone()
        return int(row["value"])

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        if checkpoint.through_sequence > self.last_sequence(checkpoint.run_id):
            raise RecoveryError("checkpoint references a future event sequence")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO checkpoints("
                "checkpoint_id, run_id, through_sequence, checkpoint_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    checkpoint.checkpoint_id,
                    checkpoint.run_id,
                    checkpoint.through_sequence,
                    canonical_json(checkpoint.model_dump(mode="json")),
                    checkpoint.created_at.isoformat(),
                ),
            )

    def latest_checkpoint(self, run_id: str) -> Checkpoint | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT checkpoint_json FROM checkpoints WHERE run_id = ? "
                "ORDER BY through_sequence DESC, created_at DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        return Checkpoint.model_validate_json(row["checkpoint_json"]) if row else None

    def list_checkpoints(self, run_id: str) -> list[Checkpoint]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT checkpoint_json FROM checkpoints WHERE run_id = ? "
                "ORDER BY through_sequence, created_at",
                (run_id,),
            ).fetchall()
        return [Checkpoint.model_validate_json(row["checkpoint_json"]) for row in rows]

    def record_action_result(
        self, run_id: str, action_id: str, input_hash: str, result: ToolResult
    ) -> None:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT input_hash FROM action_results WHERE run_id = ? AND action_id = ?",
                (run_id, action_id),
            ).fetchone()
            if existing:
                if existing["input_hash"] != input_hash:
                    raise ActionConflict(f"action {action_id} was reused with different input")
                return
            connection.execute(
                "INSERT INTO action_results("
                "run_id, action_id, input_hash, result_json) VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    action_id,
                    input_hash,
                    canonical_json(result.model_dump(mode="json")),
                ),
            )

    def get_action_result(self, run_id: str, action_id: str, input_hash: str) -> ToolResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT input_hash, result_json FROM action_results "
                "WHERE run_id = ? AND action_id = ?",
                (run_id, action_id),
            ).fetchone()
        if row is None:
            return None
        if row["input_hash"] != input_hash:
            raise ActionConflict(f"action {action_id} was reused with different input")
        return ToolResult.model_validate_json(row["result_json"])
