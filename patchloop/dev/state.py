"""Append-only, hash-chained JSONL state for development runs."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from patchloop.dev.contracts import DEV_RUN_SCHEMA, DevToolResult
from patchloop.errors import ActionConflict, RecoveryError
from patchloop.util import canonical_json, sha256_json, utc_now

_PROCESS_LOCK = threading.RLock()


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[None]:
    """Take a tiny cross-process lock without replacing the append-only ledger."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class DevJournal:
    """One immutable event stream per run plus content-addressed artifacts."""

    def __init__(self, root: str | Path, run_id: str) -> None:
        if not run_id.startswith("run_dev_") or not run_id.replace("_", "").isalnum():
            raise RecoveryError("invalid development run ID")
        self.root = Path(root).resolve()
        self.run_id = run_id
        self.run_dir = self.root / "runs"
        self.path = self.run_dir / f"{run_id}.jsonl"
        self.lock_path = self.run_dir / f".{run_id}.lock"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        previous_hash: str | None = None
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise RecoveryError("development journal is unreadable") from exc
        for expected_sequence, line in enumerate(lines, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RecoveryError("development journal contains invalid JSONL") from exc
            claimed_hash = event.pop("event_hash", None)
            if (
                event.get("schema_version") != DEV_RUN_SCHEMA
                or event.get("official") is not False
                or event.get("run_id") != self.run_id
                or event.get("sequence") != expected_sequence
                or event.get("previous_event_hash") != previous_hash
                or claimed_hash != sha256_json(event)
            ):
                raise RecoveryError("development journal hash chain is invalid")
            event["event_hash"] = claimed_hash
            previous_hash = claimed_hash
            events.append(event)
        return events

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with _PROCESS_LOCK, _exclusive_file_lock(self.lock_path):
            events = self.events()
            normalized_payload = payload or {}
            if event_type == "provider_call_finished":
                call_id = normalized_payload.get("call_id")
                if not isinstance(call_id, str) or not call_id:
                    raise RecoveryError("provider usage requires a call ID")
                recorded = [
                    event
                    for event in events
                    if event["event_type"] == event_type
                    and event["payload"].get("call_id") == call_id
                ]
                if recorded:
                    if recorded[-1]["payload"] != normalized_payload:
                        raise ActionConflict(f"provider call {call_id} has conflicting usage")
                    return recorded[-1]
            prior_hash = events[-1]["event_hash"] if events else None
            body = {
                "schema_version": DEV_RUN_SCHEMA,
                "official": False,
                "run_id": self.run_id,
                "sequence": len(events) + 1,
                "timestamp": utc_now().isoformat(),
                "event_type": event_type,
                "previous_event_hash": prior_hash,
                "payload": normalized_payload,
            }
            record = {**body, "event_hash": sha256_json(body)}
            encoded = (canonical_json(record) + "\n").encode("utf-8")
            flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            descriptor = os.open(self.path, flags, 0o600)
            try:
                os.write(descriptor, encoded)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return record

    def terminal(self) -> dict[str, Any] | None:
        rows = [event for event in self.events() if event["event_type"] == "terminal"]
        if len(rows) > 1:
            raise RecoveryError("development run has multiple terminal records")
        return rows[0] if rows else None

    def action_result(self, action_id: str, input_hash: str) -> DevToolResult | None:
        started_hashes: set[str] = set()
        matches: list[DevToolResult] = []
        for event in self.events():
            payload = event["payload"]
            if event["event_type"] == "action_started" and payload.get("action_id") == action_id:
                started_hashes.add(str(payload.get("input_hash")))
            if event["event_type"] == "action_finished" and payload.get("action_id") == action_id:
                matches.append(DevToolResult.model_validate(payload["result"]))
        known_hashes = started_hashes | {item.input_hash for item in matches}
        if known_hashes and known_hashes != {input_hash}:
            raise ActionConflict(f"action {action_id} was reused with different input")
        if len(matches) > 1:
            first = matches[0].model_dump(mode="json", exclude={"replayed"})
            if any(
                item.model_dump(mode="json", exclude={"replayed"}) != first for item in matches[1:]
            ):
                raise ActionConflict(f"action {action_id} has conflicting durable results")
        if not matches:
            return None
        return matches[-1].model_copy(update={"replayed": True})

    def pending_action(self, action_id: str, input_hash: str) -> dict[str, Any] | None:
        pending: dict[str, Any] | None = None
        for event in self.events():
            payload = event["payload"]
            if payload.get("action_id") != action_id:
                continue
            if payload.get("input_hash") not in {None, input_hash}:
                raise ActionConflict(f"action {action_id} was reused with different input")
            if event["event_type"] == "action_started":
                pending = payload
            elif event["event_type"] == "action_finished":
                pending = None
        return pending

    def unresolved_provider_call(self) -> dict[str, Any] | None:
        pending: dict[str, Any] | None = None
        for event in self.events():
            if event["event_type"] == "provider_call_started":
                pending = event["payload"]
            elif (
                event["event_type"] == "provider_call_finished"
                and pending
                and event["payload"].get("call_id") == pending.get("call_id")
            ):
                pending = None
        return pending

    def provider_usage(self) -> list[dict[str, Any]]:
        rows = [
            event["payload"]
            for event in self.events()
            if event["event_type"] == "provider_call_finished"
        ]
        call_ids = [row.get("call_id") for row in rows]
        if len(call_ids) != len(set(call_ids)):
            raise RecoveryError("development journal contains duplicate provider usage")
        return rows
