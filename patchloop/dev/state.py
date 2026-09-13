"""Append-only, hash-chained JSONL state for development runs."""

from __future__ import annotations

import json
import math
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from patchloop.dev.contracts import DEV_RUN_SCHEMA, DevRunEnvelope, DevToolResult
from patchloop.errors import ActionConflict, RecoveryError
from patchloop.util import canonical_json, sha256_json, utc_now

_PROCESS_LOCK = threading.RLock()
_ACTIVE_EXECUTIONS: dict[str, int] = {}
_UNIQUE_TURN_EVENTS = {
    "working_notes_updated",
    "turn_started",
    "turn_decision_recorded",
    "tool_batch_started",
    "tool_batch_finished",
    "protocol_correction",
    "tool_policy_transition",
}
_UNIQUE_ACTION_EVENTS = {"attempt_card", "repair_recheck_started", "repair_recheck_finished"}
_UNIQUE_RUN_EVENTS = {"manifest_recorded", "submission_recorded", "evaluator_finished",
                      "context_window_activated"}


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
        self.envelope_path = self.run_dir / f"{run_id}.envelope.json"
        self.lock_path = self.run_dir / f".{run_id}.lock"
        self.execution_lock_path = self.run_dir / f".{run_id}.execution.lock"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def execution_lock(self) -> Iterator[None]:
        key = str(self.execution_lock_path)
        with _PROCESS_LOCK:
            if key in _ACTIVE_EXECUTIONS:
                raise RecoveryError("development run is already active")
            _ACTIVE_EXECUTIONS[key] = threading.get_ident()
        stream = None
        acquired = False
        try:
            self.execution_lock_path.parent.mkdir(parents=True, exist_ok=True)
            stream = self.execution_lock_path.open("a+b")
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RecoveryError("development run is already active") from exc
            acquired = True
            yield
        finally:
            if stream is not None:
                if acquired:
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
                stream.close()
            with _PROCESS_LOCK:
                _ACTIVE_EXECUTIONS.pop(key, None)

    def require_execution_lock(self) -> None:
        """Compose a run-scoped helper without nesting the run-lifetime OS lock."""
        with _PROCESS_LOCK:
            if _ACTIVE_EXECUTIONS.get(str(self.execution_lock_path)) != threading.get_ident():
                raise RecoveryError("current thread does not own the development run lock")

    def write_envelope(self, envelope: DevRunEnvelope) -> None:
        if envelope.run_id != self.run_id:
            raise RecoveryError("run envelope identity does not match its journal")
        encoded = (canonical_json(envelope.model_dump(mode="json")) + "\n").encode("utf-8")
        if self.envelope_path.exists():
            existing = self.load_envelope()
            if existing != envelope:
                raise RecoveryError("development run envelope is immutable")
            return
        temporary = self.envelope_path.with_name(f".{self.envelope_path.name}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.envelope_path)
        finally:
            temporary.unlink(missing_ok=True)

    def load_envelope(self) -> DevRunEnvelope:
        if not self.envelope_path.is_file() or self.envelope_path.is_symlink():
            raise RecoveryError("development run predates resumable envelopes")
        try:
            raw = json.loads(self.envelope_path.read_text(encoding="utf-8"))
            envelope = DevRunEnvelope.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise RecoveryError("development run envelope is invalid") from exc
        if envelope.run_id != self.run_id:
            raise RecoveryError("development run envelope identity mismatch")
        return envelope

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
            if event_type in _UNIQUE_RUN_EVENTS:
                recorded = [event for event in events if event["event_type"] == event_type]
                if recorded:
                    if recorded[-1]["payload"] != normalized_payload:
                        raise ActionConflict(f"run has conflicting {event_type}")
                    return recorded[-1]
            if event_type in _UNIQUE_TURN_EVENTS:
                turn_id = normalized_payload.get("turn_id")
                if not isinstance(turn_id, str) or not turn_id:
                    raise RecoveryError(f"{event_type} requires a turn ID")
                recorded = [
                    event
                    for event in events
                    if event["event_type"] == event_type
                    and event["payload"].get("turn_id") == turn_id
                ]
                if recorded:
                    if recorded[-1]["payload"] != normalized_payload:
                        raise ActionConflict(f"turn {turn_id} has conflicting {event_type}")
                    return recorded[-1]
            if event_type in _UNIQUE_ACTION_EVENTS:
                action_id = normalized_payload.get("action_id")
                if not isinstance(action_id, str) or not action_id:
                    raise RecoveryError(f"{event_type} requires an action ID")
                recorded = [
                    event
                    for event in events
                    if event["event_type"] == event_type
                    and event["payload"].get("action_id") == action_id
                ]
                if recorded:
                    if recorded[-1]["payload"] != normalized_payload:
                        raise ActionConflict(f"action {action_id} has conflicting {event_type}")
                    return recorded[-1]
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
            if event_type == "input_count_failed":
                count_id = normalized_payload.get("count_id")
                if not isinstance(count_id, str) or not count_id:
                    raise RecoveryError("input count failure requires a count ID")
                recorded = [event for event in events if event["event_type"] == event_type
                            and event["payload"].get("count_id") == count_id]
                if recorded:
                    if recorded[-1]["payload"] != normalized_payload:
                        raise ActionConflict(f"input count {count_id} has conflicting failure")
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
        for event in self.events():
            if event["event_type"] == "compaction_usage_recorded":
                payload = event["payload"]
                amount = payload["accounting"]["model_rate_cost_nanos"]
                if amount is not None:
                    rows.append({"call_id": payload["call_id"], "cost_nanos": amount})
        call_ids = [row.get("call_id") for row in rows]
        if len(call_ids) != len(set(call_ids)):
            raise RecoveryError("development journal contains duplicate provider usage")
        return rows

    def unresolved_input_count(self) -> dict[str, Any] | None:
        """Recover a failed/interrupted count without another network request."""
        pending = None
        failure = None
        for event in self.events():
            kind, payload = event["event_type"], event["payload"]
            if kind == "input_count_started":
                if pending is not None:
                    raise RecoveryError("input counting continued after an unresolved attempt")
                pending = payload
            elif kind in {"input_count_finished", "input_count_failed"}:
                if pending is None or any(
                    payload.get(key) != pending.get(key) for key in ("count_id", "turn_id")
                ):
                    raise RecoveryError("input count outcome does not match its admission")
                if failure is not None:
                    raise RecoveryError("input count has conflicting outcomes")
                if kind == "input_count_failed":
                    if payload.get("request_hash") != pending.get("request_hash"):
                        raise RecoveryError("input count failure request hash mismatch")
                    failure = payload["error"]
                else:
                    pending = None
        if pending is None:
            return None
        return {
            "count_id": pending["count_id"], "turn_id": pending["turn_id"],
            "request_hash": pending["request_hash"],
            "request_metadata": pending.get("request_metadata"),
            "error": failure or {"category": "interrupted", "exception_type": None},
        }

    def latest_active_elapsed_ms(self) -> int:
        values = [
            event["payload"].get("active_elapsed_ms")
            for event in self.events()
            if type(event["payload"].get("active_elapsed_ms")) is int
        ]
        for event in self.events():
            if "active_elapsed_seconds" in event["payload"]:
                seconds = event["payload"]["active_elapsed_seconds"]
                if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
                    raise RecoveryError("invalid compaction active time")
                values.append(math.ceil(seconds * 1_000))
        if any(value < 0 for value in values):
            raise RecoveryError("development journal has invalid active elapsed time")
        return max(values, default=0)

    def latest_tool_batch_results(self) -> list[DevToolResult]:
        batches = [
            event for event in self.events() if event["event_type"] == "tool_batch_finished"
        ]
        if not batches:
            return []
        action_ids = batches[-1]["payload"].get("action_ids")
        if not isinstance(action_ids, list) or not all(
            isinstance(action_id, str) for action_id in action_ids
        ):
            raise RecoveryError("tool batch action IDs are invalid")
        results: dict[str, DevToolResult] = {}
        for event in self.events():
            if event["event_type"] != "action_finished":
                continue
            result = DevToolResult.model_validate(event["payload"]["result"])
            if result.action_id in action_ids:
                results[result.action_id] = result
        if set(results) != set(action_ids):
            raise RecoveryError("completed tool batch is missing an action result")
        return [results[action_id] for action_id in action_ids]
