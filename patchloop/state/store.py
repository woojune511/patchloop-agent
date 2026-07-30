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
    RunResult,
    RunStatus,
    ToolResult,
)
from patchloop.errors import (
    ActionConflict,
    ContractError,
    RecoveryError,
    RunOwnershipConflict,
)
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
                CREATE TABLE IF NOT EXISTS run_worker_claims (
                    claim_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    owner_pid INTEGER NOT NULL,
                    owner_hostname TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    prior_status TEXT NOT NULL,
                    reclaimed INTEGER NOT NULL,
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
        if status in {RunStatus.COMPLETED, RunStatus.FAILED}:
            raise ValueError(
                "terminal run state must be persisted with finalize_run"
            )
        if result is not None:
            raise ValueError("non-terminal run state cannot include a result")
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status = ? WHERE run_id = ?",
                (status.value, run_id),
            )

    def finalize_run(
        self,
        run_id: str,
        *,
        status: RunStatus,
        result: RunResult,
        event_type: EventType,
        actor: str,
        payload: dict | None = None,
        failure_payload: dict | None = None,
    ) -> RunEvent:
        """Atomically persist the one terminal event, status, and result."""

        expected_event = {
            RunStatus.COMPLETED: EventType.RUN_COMPLETED,
            RunStatus.FAILED: EventType.RUN_FAILED,
        }.get(status)
        if expected_event is None or event_type != expected_event:
            raise ValueError("terminal run status and event type do not match")
        if result.run_id != run_id:
            raise ValueError("terminal result belongs to a different run")
        result_json = canonical_json(result.model_dump(mode="json"))
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, result_json FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise RecoveryError(f"unknown run: {run_id}")
            event_rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchall()
            terminal_rows = [
                event
                for event in (
                    RunEvent.model_validate_json(item["event_json"])
                    for item in event_rows
                )
                if event.type
                in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
            ]
            if (
                row["status"] != RunStatus.RUNNING.value
                or row["result_json"] is not None
                or terminal_rows
            ):
                raise RecoveryError(
                    f"run cannot be finalized from status {row['status']}: {run_id}"
                )
            updated = connection.execute(
                "UPDATE runs SET status = ?, result_json = ? "
                "WHERE run_id = ? AND status = ? AND result_json IS NULL",
                (
                    status.value,
                    result_json,
                    run_id,
                    RunStatus.RUNNING.value,
                ),
            )
            if updated.rowcount != 1:
                raise RecoveryError(
                    f"run terminal state changed while finalizing: {run_id}"
                )
            sequence_row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value "
                "FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            sequence = int(sequence_row["value"])
            if failure_payload is not None:
                sequence += 1
                failure_event = RunEvent(
                    event_id=f"evt_{uuid.uuid4().hex}",
                    run_id=run_id,
                    sequence=sequence,
                    type=EventType.FAILURE_TAGGED,
                    timestamp=utc_now(),
                    actor="failure-classifier",
                    payload=failure_payload,
                )
                connection.execute(
                    "INSERT INTO events("
                    "run_id, sequence, event_id, event_json"
                    ") VALUES (?, ?, ?, ?)",
                    (
                        run_id,
                        failure_event.sequence,
                        failure_event.event_id,
                        canonical_json(
                            failure_event.model_dump(mode="json")
                        ),
                    ),
                )
            sequence += 1
            event = RunEvent(
                event_id=f"evt_{uuid.uuid4().hex}",
                run_id=run_id,
                sequence=sequence,
                type=event_type,
                timestamp=utc_now(),
                actor=actor,
                payload=payload or {},
            )
            connection.execute(
                "INSERT INTO events(run_id, sequence, event_id, event_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    event.sequence,
                    event.event_id,
                    canonical_json(event.model_dump(mode="json")),
                ),
            )
            connection.commit()
        return event

    def get_run_status(self, run_id: str) -> RunStatus:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise RecoveryError(f"unknown run: {run_id}")
        try:
            return RunStatus(row["status"])
        except ValueError as exc:
            raise RecoveryError(f"run has an invalid status: {run_id}") from exc

    def claim_run_for_worker(
        self,
        run_id: str,
        *,
        owner_id: str,
        owner_pid: int,
        owner_hostname: str,
        allowed_statuses: set[RunStatus],
        manifest: RunManifest | None = None,
    ) -> dict:
        if not allowed_statuses:
            raise ValueError("worker claim requires at least one allowed status")
        if manifest is not None and manifest.run_id != run_id:
            raise ValueError("worker claim manifest belongs to a different run")
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT manifest_json, status, result_json "
                "FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                if manifest is None:
                    raise RecoveryError(f"unknown run: {run_id}")
                manifest_json = canonical_json(
                    manifest.model_dump(mode="json")
                )
                connection.execute(
                    "INSERT INTO runs("
                    "run_id, manifest_json, status, created_at"
                    ") VALUES (?, ?, ?, ?)",
                    (
                        run_id,
                        manifest_json,
                        RunStatus.CREATED.value,
                        manifest.created_at.isoformat(),
                    ),
                )
                row = {
                    "manifest_json": manifest_json,
                    "status": RunStatus.CREATED.value,
                    "result_json": None,
                }
            elif manifest is not None:
                try:
                    stored_manifest = RunManifest.model_validate_json(
                        row["manifest_json"]
                    )
                except ValueError as exc:
                    raise RecoveryError(
                        f"run has an invalid immutable manifest: {run_id}"
                    ) from exc
                if stored_manifest != manifest:
                    raise ContractError(
                        "supplied run manifest does not match the stored "
                        "immutable manifest"
                    )
            try:
                prior_status = RunStatus(row["status"])
            except ValueError as exc:
                raise RecoveryError(f"run has an invalid status: {run_id}") from exc
            terminal_rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
            has_terminal_event = any(
                RunEvent.model_validate_json(item["event_json"]).type
                in {EventType.RUN_COMPLETED, EventType.RUN_FAILED}
                for item in terminal_rows
            )
            if (
                prior_status not in allowed_statuses
                or row["result_json"] is not None
                or has_terminal_event
            ):
                allowed = ", ".join(sorted(status.value for status in allowed_statuses))
                raise RunOwnershipConflict(
                    f"run cannot be claimed from status {prior_status.value}; "
                    f"allowed statuses: {allowed}",
                    details={
                        "run_id": run_id,
                        "status": prior_status.value,
                        "allowed_statuses": sorted(
                            status.value for status in allowed_statuses
                        ),
                    },
                )
            updated = connection.execute(
                "UPDATE runs SET status = ? "
                "WHERE run_id = ? AND status = ? AND result_json IS NULL",
                (RunStatus.RUNNING.value, run_id, prior_status.value),
            )
            if updated.rowcount != 1:
                raise RunOwnershipConflict(
                    f"run ownership changed while claiming: {run_id}",
                    details={"run_id": run_id},
                )
            claimed_at = utc_now()
            claim = {
                "claim_id": f"claim_{uuid.uuid4().hex}",
                "run_id": run_id,
                "owner_id": owner_id,
                "owner_pid": owner_pid,
                "owner_hostname": owner_hostname,
                "claimed_at": claimed_at.isoformat(),
                "prior_status": prior_status.value,
                "reclaimed": prior_status == RunStatus.RUNNING,
            }
            connection.execute(
                "INSERT INTO run_worker_claims("
                "claim_id, run_id, owner_id, owner_pid, owner_hostname, claimed_at, "
                "prior_status, reclaimed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    claim["claim_id"],
                    run_id,
                    owner_id,
                    owner_pid,
                    owner_hostname,
                    claim["claimed_at"],
                    claim["prior_status"],
                    int(claim["reclaimed"]),
                ),
            )
            connection.commit()
        return claim

    def list_worker_claims(self, run_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT claim_id, run_id, owner_id, owner_pid, owner_hostname, "
                "claimed_at, prior_status, reclaimed "
                "FROM run_worker_claims WHERE run_id = ? ORDER BY rowid",
                (run_id,),
            ).fetchall()
        return [
            {
                "claim_id": row["claim_id"],
                "run_id": row["run_id"],
                "owner_id": row["owner_id"],
                "owner_pid": int(row["owner_pid"]),
                "owner_hostname": row["owner_hostname"],
                "claimed_at": row["claimed_at"],
                "prior_status": row["prior_status"],
                "reclaimed": bool(row["reclaimed"]),
            }
            for row in rows
        ]

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
        result_json = canonical_json(result.model_dump(mode="json"))
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT input_hash, result_json FROM action_results "
                "WHERE run_id = ? AND action_id = ?",
                (run_id, action_id),
            ).fetchone()
            if existing:
                if existing["input_hash"] != input_hash:
                    raise ActionConflict(f"action {action_id} was reused with different input")
                if existing["result_json"] != result_json:
                    raise ActionConflict(
                        f"action {action_id} was completed with a different result"
                    )
                return
            connection.execute(
                "INSERT INTO action_results("
                "run_id, action_id, input_hash, result_json) VALUES (?, ?, ?, ?)",
                (
                    run_id,
                    action_id,
                    input_hash,
                    result_json,
                ),
            )

    def complete_action(
        self,
        run_id: str,
        action_id: str,
        input_hash: str,
        result: ToolResult,
        *,
        outcome_type: EventType,
        outcome_payload: dict,
        patch_payload: dict | None = None,
    ) -> None:
        if outcome_type not in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}:
            raise ValueError("action outcome must be ToolSucceeded or ToolFailed")
        if result.action_id != action_id:
            raise ValueError("tool result belongs to a different action")
        expected_outcome = (
            EventType.TOOL_SUCCEEDED
            if result.status == "succeeded"
            else EventType.TOOL_FAILED
        )
        if outcome_type != expected_outcome:
            raise ValueError("tool result status and outcome event do not match")
        if outcome_payload.get("status") != result.status:
            raise ValueError("tool outcome payload status conflicts with result")
        expected = [(outcome_type, outcome_payload)]
        if patch_payload is not None:
            if outcome_type != EventType.TOOL_SUCCEEDED:
                raise ValueError("PatchApplied requires a successful tool outcome")
            if (
                patch_payload.get("patch_hash")
                != result.output.get("patch_hash")
                or patch_payload.get("worktree_diff_hash")
                != result.output.get("worktree_diff_hash")
            ):
                raise ValueError("PatchApplied payload conflicts with tool result")
            expected.append((EventType.PATCH_APPLIED, patch_payload))
        result_json = canonical_json(result.model_dump(mode="json"))
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_result = connection.execute(
                "SELECT input_hash, result_json FROM action_results "
                "WHERE run_id = ? AND action_id = ?",
                (run_id, action_id),
            ).fetchone()
            if existing_result is None:
                connection.execute(
                    "INSERT INTO action_results("
                    "run_id, action_id, input_hash, result_json) VALUES (?, ?, ?, ?)",
                    (run_id, action_id, input_hash, result_json),
                )
            elif existing_result["input_hash"] != input_hash:
                raise ActionConflict(
                    f"action {action_id} was reused with different input"
                )
            elif existing_result["result_json"] != result_json:
                raise ActionConflict(
                    f"action {action_id} was completed with a different result"
                )

            rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
            parsed_events = [
                RunEvent.model_validate_json(row["event_json"])
                for row in rows
            ]
            relevant = [
                event
                for event in parsed_events
                if event.correlation_id == action_id
                and event.type
                in {
                    EventType.TOOL_SUCCEEDED,
                    EventType.TOOL_FAILED,
                    EventType.PATCH_APPLIED,
                }
            ]
            expected_types = [item[0] for item in expected]
            if [event.type for event in relevant] != expected_types[: len(relevant)]:
                raise RecoveryError(
                    f"action {action_id} has an invalid durable outcome prefix"
                )
            for event, (_, payload) in zip(
                relevant,
                expected[: len(relevant)],
                strict=True,
            ):
                if event.payload != payload:
                    raise RecoveryError(
                        f"action {action_id} outcome conflicts with its result"
                    )

            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value "
                "FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            sequence = int(row["value"])
            for event_type, payload in expected[len(relevant) :]:
                sequence += 1
                event = RunEvent(
                    event_id=f"evt_{uuid.uuid4().hex}",
                    run_id=run_id,
                    sequence=sequence,
                    type=event_type,
                    timestamp=utc_now(),
                    actor="tool-gateway",
                    correlation_id=action_id,
                    payload=payload,
                )
                connection.execute(
                    "INSERT INTO events(run_id, sequence, event_id, event_json) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        run_id,
                        sequence,
                        event.event_id,
                        canonical_json(event.model_dump(mode="json")),
                    ),
                )
            connection.commit()

    def complete_nonexecuted_action(
        self,
        run_id: str,
        action_id: str,
        input_hash: str,
        result: ToolResult,
        *,
        event_specs: list[tuple[EventType, str, dict]],
    ) -> None:
        """Atomically close a replayed or admission-blocked tool request."""

        allowed_shapes = {
            (
                EventType.TOOL_CALLED,
                EventType.LOOP_DETECTED,
                EventType.TOOL_REPLAYED,
            ),
            (EventType.TOOL_ADMISSION_BLOCKED,),
        }
        event_types = tuple(item[0] for item in event_specs)
        if event_types not in allowed_shapes:
            raise ValueError("invalid nonexecuted action event lifecycle")
        if result.action_id != action_id:
            raise ValueError("tool result belongs to a different action")
        if (
            event_types[-1] == EventType.TOOL_REPLAYED
            and result.status != "succeeded"
        ):
            raise ValueError("semantic replay requires a successful result")
        if (
            event_types[-1] == EventType.TOOL_ADMISSION_BLOCKED
            and result.status != "rejected"
        ):
            raise ValueError("tool admission block requires a rejected result")

        result_json = canonical_json(result.model_dump(mode="json"))
        relevant_types = {
            EventType.TOOL_CALLED,
            EventType.LOOP_DETECTED,
            EventType.TOOL_REPLAYED,
            EventType.TOOL_ADMISSION_BLOCKED,
        }
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_result = connection.execute(
                "SELECT input_hash, result_json FROM action_results "
                "WHERE run_id = ? AND action_id = ?",
                (run_id, action_id),
            ).fetchone()
            if existing_result is None:
                connection.execute(
                    "INSERT INTO action_results("
                    "run_id, action_id, input_hash, result_json) VALUES (?, ?, ?, ?)",
                    (run_id, action_id, input_hash, result_json),
                )
            elif existing_result["input_hash"] != input_hash:
                raise ActionConflict(
                    f"action {action_id} was reused with different input"
                )
            elif existing_result["result_json"] != result_json:
                raise ActionConflict(
                    f"action {action_id} was completed with a different result"
                )

            rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
            relevant = [
                event
                for event in (
                    RunEvent.model_validate_json(row["event_json"])
                    for row in rows
                )
                if event.correlation_id == action_id
                and event.type in relevant_types
            ]
            if [event.type for event in relevant] != list(
                event_types[: len(relevant)]
            ):
                raise RecoveryError(
                    f"action {action_id} has an invalid nonexecuted event prefix"
                )
            for event, (_, actor, payload) in zip(
                relevant,
                event_specs[: len(relevant)],
                strict=True,
            ):
                if event.actor != actor or event.payload != payload:
                    raise RecoveryError(
                        f"action {action_id} nonexecuted evidence conflicts"
                    )

            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value "
                "FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            sequence = int(row["value"])
            for event_type, actor, payload in event_specs[len(relevant) :]:
                sequence += 1
                event = RunEvent(
                    event_id=f"evt_{uuid.uuid4().hex}",
                    run_id=run_id,
                    sequence=sequence,
                    type=event_type,
                    timestamp=utc_now(),
                    actor=actor,
                    correlation_id=action_id,
                    payload=payload,
                )
                connection.execute(
                    "INSERT INTO events(run_id, sequence, event_id, event_json) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        run_id,
                        sequence,
                        event.event_id,
                        canonical_json(event.model_dump(mode="json")),
                    ),
                )
            connection.commit()

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
