"""Stdlib-only v21 offline fixture for the two-pipe process boundary.

This script never reads repository state, environment variables, ``.env``, or
credentials and never imports an SDK.  It launches only another copy of itself
in an explicit fixed-fixture mode.  Both process boundaries use an inherited
anonymous pipe carrying one length-and-digest framed canonical JSON object.

Invalid frame bytes are classified and discarded.  They are never returned,
printed, hashed into evidence, or otherwise exposed by a decode result.
Importing this module performs no observation or process launch.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

WORKER_SCHEMA_VERSION = "offline-fixed-no-call-worker-fixture-v21"
SUPERVISOR_SCHEMA_VERSION = "offline-fixed-no-call-supervisor-envelope-v21"
FIXTURE_ID = "v21-public-fixed-placeholder-no-dispatch"
CHILD_FLAGS = ("-I", "-E", "-s", "-B")
FIXED_PROCESS_ENVIRONMENT = {
    "PYTHONHASHSEED": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "SYSTEMROOT": r"C:\Windows",
}
FRAME_LENGTH_BYTES = 4
FRAME_DIGEST_BYTES = 32
FRAME_HEADER_BYTES = FRAME_LENGTH_BYTES + FRAME_DIGEST_BYTES
FRAME_BODY_LIMIT = 262_144
FRAME_OUTPUT_LIMIT = FRAME_HEADER_BYTES + FRAME_BODY_LIMIT
WORKER_TIMEOUT_SECONDS = 15


class FrameStage(StrEnum):
    NO_MESSAGE = "no_message"
    NOT_EVALUATED = "not_evaluated"
    READ_ERROR = "read_error"
    OUTPUT_LIMIT = "output_limit"
    HEADER_INVALID = "header_invalid"
    BODY_LENGTH_INVALID = "body_length_invalid"
    FRAME_LENGTH_INVALID = "frame_length_invalid"
    DIGEST_INVALID = "digest_invalid"
    UTF8_INVALID = "utf8_invalid"
    JSON_INVALID = "json_invalid"
    OBJECT_INVALID = "object_invalid"
    SCHEMA_INVALID = "schema_invalid"
    SEMANTIC_INVALID = "semantic_invalid"
    VALID = "valid"


class SupervisorCode(StrEnum):
    WORKER_LAUNCH_ERROR = "worker_launch_error"
    WORKER_NONZERO_EXIT = "worker_nonzero_exit"
    WORKER_PROCESS_INCOMPLETE = "worker_process_incomplete"
    WORKER_FRAME_INVALID = "worker_frame_invalid"
    SUPERVISOR_INTERNAL_ERROR = "supervisor_internal_error"


@dataclass(frozen=True)
class FrameDecodeResult:
    """A sanitized parse result; invalid bytes and metadata are never retained."""

    stage: FrameStage
    value: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if (self.stage == FrameStage.VALID) != (self.value is not None):
            raise ValueError("frame decode result shape differs")


@dataclass(frozen=True)
class WorkerProcessOutcome:
    launch_attempt_count: int
    process_return_count: int
    returncode: int | None
    frame: FrameDecodeResult
    activity_accounting_complete: bool
    unknown_process_activity_possible: bool


def _canonical(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_all(
    descriptor: int,
    data: bytes,
    *,
    write: Callable[[int, bytes | memoryview], int] = os.write,
    limit: int = FRAME_OUTPUT_LIMIT,
) -> None:
    """Write a complete bounded frame, retrying only interrupted writes."""

    if not data or len(data) > limit:
        raise RuntimeError("framed write size differs")
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        try:
            written = write(descriptor, view[offset:])
        except InterruptedError:
            continue
        if written <= 0 or written > len(view) - offset:
            raise RuntimeError("framed write did not advance")
        offset += written


def encode_frame(value: dict[str, Any]) -> bytes:
    """Encode one canonical JSON object with a bounded length and SHA-256 header."""

    if not isinstance(value, dict):
        raise TypeError("frame value must be an object")
    body = _canonical(value)
    if not body or len(body) > FRAME_BODY_LIMIT:
        raise ValueError("frame body size differs")
    return len(body).to_bytes(FRAME_LENGTH_BYTES, "big") + hashlib.sha256(body).digest() + body


def decode_frame(
    raw: bytes,
    *,
    expected_schema_version: str,
    semantic_validator: Callable[[dict[str, Any]], bool],
) -> FrameDecodeResult:
    """Classify one frame without returning invalid bytes, size, or digest metadata."""

    if raw == b"":
        return FrameDecodeResult(FrameStage.NO_MESSAGE)
    if not isinstance(raw, bytes) or len(raw) < FRAME_HEADER_BYTES:
        return FrameDecodeResult(FrameStage.HEADER_INVALID)
    declared = int.from_bytes(raw[:FRAME_LENGTH_BYTES], "big")
    if declared <= 0 or declared > FRAME_BODY_LIMIT:
        return FrameDecodeResult(FrameStage.BODY_LENGTH_INVALID)
    if len(raw) != FRAME_HEADER_BYTES + declared:
        return FrameDecodeResult(FrameStage.FRAME_LENGTH_INVALID)
    expected_digest = raw[FRAME_LENGTH_BYTES:FRAME_HEADER_BYTES]
    body = raw[FRAME_HEADER_BYTES:]
    if not hmac.compare_digest(hashlib.sha256(body).digest(), expected_digest):
        return FrameDecodeResult(FrameStage.DIGEST_INVALID)
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return FrameDecodeResult(FrameStage.UTF8_INVALID)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (json.JSONDecodeError, RecursionError):
        return FrameDecodeResult(FrameStage.JSON_INVALID)
    except (TypeError, ValueError):
        return FrameDecodeResult(FrameStage.JSON_INVALID)
    if not isinstance(value, dict):
        return FrameDecodeResult(FrameStage.OBJECT_INVALID)
    if value.get("schema_version") != expected_schema_version:
        return FrameDecodeResult(FrameStage.SCHEMA_INVALID)
    if body != _canonical(value):
        return FrameDecodeResult(FrameStage.SCHEMA_INVALID)
    try:
        valid = semantic_validator(value)
    except BaseException:
        valid = False
    if valid is not True:
        return FrameDecodeResult(FrameStage.SEMANTIC_INVALID)
    return FrameDecodeResult(FrameStage.VALID, value)


def emit_frame(
    descriptor: int,
    value: dict[str, Any],
    *,
    write: Callable[[int, bytes | memoryview], int] = os.write,
) -> None:
    _write_all(descriptor, encode_frame(value), write=write)


def fixed_worker_fixture() -> dict[str, Any]:
    """Return the sole public fixture available to the worker process."""

    return {
        "schema_version": WORKER_SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "fixture_kind": "fixed-public-placeholder-no-dispatch",
        "activity": {
            "environment_read_count": 0,
            "dotenv_read_count": 0,
            "credential_value_read_count": 0,
            "sdk_import_count": 0,
            "transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "raw_output_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def validate_worker_fixture(value: dict[str, Any]) -> bool:
    expected = fixed_worker_fixture()
    if value != expected or set(value) != set(expected):
        return False
    activity = value.get("activity")
    if not isinstance(activity, dict) or set(activity) != set(expected["activity"]):
        return False
    if any(type(activity[key]) is not int for key in activity):
        return False
    return all(
        type(value[key]) is bool
        for key in (
            "raw_output_returned",
            "credential_value_hash_prefix_or_length_returned",
            "exception_message_type_repr_or_traceback_returned",
        )
    )


def decode_worker_frame(raw: bytes) -> FrameDecodeResult:
    return decode_frame(
        raw,
        expected_schema_version=WORKER_SCHEMA_VERSION,
        semantic_validator=validate_worker_fixture,
    )


class _BoundedFrameReader:
    """Temporarily holds at most one bounded frame and releases it immediately."""

    def __init__(self, descriptor: int) -> None:
        self.descriptor = descriptor
        self._buffer = bytearray()
        self.failed = False
        self.over_limit = False

    def consume(self) -> None:
        try:
            while True:
                chunk = os.read(self.descriptor, 8192)
                if not chunk:
                    break
                remaining = FRAME_OUTPUT_LIMIT + 1 - len(self._buffer)
                if remaining > 0:
                    self._buffer.extend(chunk[:remaining])
                if len(self._buffer) > FRAME_OUTPUT_LIMIT:
                    self.over_limit = True
        except BaseException:
            self.failed = True
        finally:
            with contextlib.suppress(OSError):
                os.close(self.descriptor)

    def decode_and_discard(self) -> FrameDecodeResult:
        if self.failed:
            self._buffer.clear()
            return FrameDecodeResult(FrameStage.READ_ERROR)
        if self.over_limit:
            self._buffer.clear()
            return FrameDecodeResult(FrameStage.OUTPUT_LIMIT)
        raw = bytes(self._buffer)
        self._buffer.clear()
        return decode_worker_frame(raw)


def _open_result_descriptor(*, raw_handle: int | None, descriptor: int | None) -> int:
    if os.name == "nt":
        if raw_handle is None or descriptor is not None:
            raise RuntimeError("result handle binding differs")
        import msvcrt

        return msvcrt.open_osfhandle(raw_handle, os.O_WRONLY | os.O_BINARY)
    if descriptor is None or raw_handle is not None:
        raise RuntimeError("result descriptor binding differs")
    return descriptor


def emit_worker_fixture(*, raw_handle: int | None, descriptor: int | None) -> None:
    result_descriptor = _open_result_descriptor(raw_handle=raw_handle, descriptor=descriptor)
    try:
        emit_frame(result_descriptor, fixed_worker_fixture())
    finally:
        os.close(result_descriptor)


def _failed_worker_outcome(
    stage: FrameStage,
    *,
    process_return_count: int = 0,
    returncode: int | None = None,
) -> WorkerProcessOutcome:
    return WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=process_return_count,
        returncode=returncode,
        frame=FrameDecodeResult(stage),
        activity_accounting_complete=False,
        unknown_process_activity_possible=True,
    )


def run_worker_process(
    *,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> WorkerProcessOutcome:
    """Launch exactly one same-script worker under the fixed minimal environment."""

    script = Path(__file__).resolve(strict=True)
    python = Path(sys.executable).resolve(strict=True)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedFrameReader(read_descriptor)
    thread = threading.Thread(target=reader.consume, daemon=True)
    process: subprocess.Popen[bytes] | None = None
    argv = [
        str(python),
        *CHILD_FLAGS,
        str(script),
        "--offline-fixed-fixture",
        "--worker",
    ]
    kwargs: dict[str, Any] = {
        "cwd": script.parent,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "shell": False,
        "env": dict(FIXED_PROCESS_ENVIRONMENT),
        "close_fds": True,
    }
    try:
        if os.name == "nt":
            import msvcrt

            raw_handle = msvcrt.get_osfhandle(write_descriptor)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.lpAttributeList = {"handle_list": [raw_handle]}
            argv.extend(("--worker-result-handle", str(raw_handle)))
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            argv.extend(("--worker-result-fd", str(write_descriptor)))
            kwargs["pass_fds"] = (write_descriptor,)
        process = popen(argv, **kwargs)
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(write_descriptor)
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        return _failed_worker_outcome(FrameStage.NOT_EVALUATED)

    os.close(write_descriptor)
    thread.start()
    timed_out = False
    try:
        returncode = process.wait(timeout=WORKER_TIMEOUT_SECONDS)
    except BaseException:
        timed_out = True
        try:
            process.kill()
            returncode = process.wait(timeout=5)
        except BaseException:
            returncode = None
    thread.join(timeout=5)
    if thread.is_alive():
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        thread.join(timeout=1)
    if timed_out or thread.is_alive():
        reader._buffer.clear()
        return _failed_worker_outcome(
            FrameStage.READ_ERROR,
            process_return_count=int(returncode is not None),
            returncode=returncode,
        )
    decoded = reader.decode_and_discard()
    process_return_count = int(returncode is not None)
    if returncode != 0:
        return _failed_worker_outcome(
            FrameStage.NOT_EVALUATED,
            process_return_count=process_return_count,
            returncode=returncode,
        )
    if decoded.stage != FrameStage.VALID:
        return WorkerProcessOutcome(
            launch_attempt_count=1,
            process_return_count=process_return_count,
            returncode=returncode,
            frame=decoded,
            activity_accounting_complete=False,
            unknown_process_activity_possible=True,
        )
    return WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=decoded,
        activity_accounting_complete=True,
        unknown_process_activity_possible=False,
    )


def _activity(outcome: WorkerProcessOutcome) -> dict[str, Any]:
    return {
        "worker_launch_attempt_count": outcome.launch_attempt_count,
        "worker_process_return_count": outcome.process_return_count,
        "worker_result_message_count": int(outcome.frame.stage == FrameStage.VALID),
        "worker_returncode": outcome.returncode,
        "worker_valid_frame_count": int(outcome.frame.stage == FrameStage.VALID),
        "environment_read_count": 0,
        "dotenv_read_count": 0,
        "credential_value_read_count": 0,
        "sdk_import_count": 0,
        "transport_dispatch_count": 0,
        "network_call_count": 0,
        "provider_evaluator_agent_call_count": 0,
        "activity_accounting_complete": outcome.activity_accounting_complete,
        "unknown_process_activity_possible": outcome.unknown_process_activity_possible,
    }


def build_supervisor_envelope(
    *, worker_runner: Callable[[], WorkerProcessOutcome] = run_worker_process
) -> dict[str, Any]:
    """Build one sanitized envelope from the exact fixed worker chain."""

    try:
        outcome = worker_runner()
    except BaseException:
        outcome = _failed_worker_outcome(FrameStage.NOT_EVALUATED)
        code = SupervisorCode.SUPERVISOR_INTERNAL_ERROR
    else:
        if outcome.process_return_count != 1 or outcome.returncode is None:
            code = SupervisorCode.WORKER_LAUNCH_ERROR
        elif outcome.returncode != 0:
            code = SupervisorCode.WORKER_NONZERO_EXIT
        elif outcome.frame.stage in {FrameStage.NOT_EVALUATED, FrameStage.READ_ERROR}:
            code = SupervisorCode.WORKER_PROCESS_INCOMPLETE
        elif outcome.frame.stage != FrameStage.VALID:
            code = SupervisorCode.WORKER_FRAME_INVALID
        elif not outcome.activity_accounting_complete:
            code = SupervisorCode.WORKER_PROCESS_INCOMPLETE
        else:
            code = None
    fixture = outcome.frame.value if code is None else None
    return {
        "schema_version": SUPERVISOR_SCHEMA_VERSION,
        "fixture": fixture,
        "code": None if code is None else code.value,
        "worker_frame_stage": outcome.frame.stage.value,
        "activity": _activity(outcome),
        "raw_output_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def validate_supervisor_envelope(value: dict[str, Any]) -> bool:
    if set(value) != {
        "schema_version",
        "fixture",
        "code",
        "worker_frame_stage",
        "activity",
        "raw_output_returned",
        "credential_value_hash_prefix_or_length_returned",
        "exception_message_type_repr_or_traceback_returned",
    }:
        return False
    try:
        stage = FrameStage(value["worker_frame_stage"])
        code = None if value["code"] is None else SupervisorCode(value["code"])
    except (TypeError, ValueError):
        return False
    if any(
        value[field] is not False
        for field in (
            "raw_output_returned",
            "credential_value_hash_prefix_or_length_returned",
            "exception_message_type_repr_or_traceback_returned",
        )
    ):
        return False
    if (value["fixture"] is None) == (code is None):
        return False
    if code is None:
        if stage != FrameStage.VALID or not validate_worker_fixture(value["fixture"]):
            return False
    elif stage == FrameStage.VALID:
        return False
    activity = value["activity"]
    if not isinstance(activity, dict) or set(activity) != {
        "worker_launch_attempt_count",
        "worker_process_return_count",
        "worker_result_message_count",
        "worker_returncode",
        "worker_valid_frame_count",
        "environment_read_count",
        "dotenv_read_count",
        "credential_value_read_count",
        "sdk_import_count",
        "transport_dispatch_count",
        "network_call_count",
        "provider_evaluator_agent_call_count",
        "activity_accounting_complete",
        "unknown_process_activity_possible",
    }:
        return False
    count_fields = (
        "worker_launch_attempt_count",
        "worker_process_return_count",
        "worker_result_message_count",
        "worker_valid_frame_count",
        "environment_read_count",
        "dotenv_read_count",
        "credential_value_read_count",
        "sdk_import_count",
        "transport_dispatch_count",
        "network_call_count",
        "provider_evaluator_agent_call_count",
    )
    if any(type(activity[field]) is not int for field in count_fields):
        return False
    if type(activity["activity_accounting_complete"]) is not bool:
        return False
    if type(activity["unknown_process_activity_possible"]) is not bool:
        return False
    if activity["worker_returncode"] is not None and type(activity["worker_returncode"]) is not int:
        return False
    for field in (
        "environment_read_count",
        "dotenv_read_count",
        "credential_value_read_count",
        "sdk_import_count",
        "transport_dispatch_count",
        "network_call_count",
        "provider_evaluator_agent_call_count",
    ):
        if activity[field] != 0:
            return False
    if activity["worker_launch_attempt_count"] != 1:
        return False
    if activity["worker_process_return_count"] not in {0, 1}:
        return False
    if activity["worker_process_return_count"] != int(activity["worker_returncode"] is not None):
        return False
    if activity["worker_result_message_count"] != int(stage == FrameStage.VALID):
        return False
    if activity["worker_valid_frame_count"] != int(stage == FrameStage.VALID):
        return False
    if activity["activity_accounting_complete"] == activity["unknown_process_activity_possible"]:
        return False
    returncode = activity["worker_returncode"]
    complete = activity["activity_accounting_complete"]
    if code is None:
        return returncode == 0 and complete and stage == FrameStage.VALID
    if code == SupervisorCode.WORKER_LAUNCH_ERROR:
        return (
            activity["worker_process_return_count"] == 0
            and returncode is None
            and stage == FrameStage.NOT_EVALUATED
            and not complete
        )
    if code == SupervisorCode.WORKER_NONZERO_EXIT:
        return returncode is not None and returncode != 0 and not complete
    if code == SupervisorCode.WORKER_FRAME_INVALID:
        return (
            returncode == 0
            and stage not in {FrameStage.VALID, FrameStage.NOT_EVALUATED, FrameStage.READ_ERROR}
            and not complete
        )
    if code == SupervisorCode.WORKER_PROCESS_INCOMPLETE:
        return (
            returncode == 0
            and stage in {FrameStage.NOT_EVALUATED, FrameStage.READ_ERROR}
            and not complete
        )
    return (
        code == SupervisorCode.SUPERVISOR_INTERNAL_ERROR
        and stage == FrameStage.NOT_EVALUATED
        and not complete
    )


def decode_supervisor_frame(raw: bytes) -> FrameDecodeResult:
    return decode_frame(
        raw,
        expected_schema_version=SUPERVISOR_SCHEMA_VERSION,
        semantic_validator=validate_supervisor_envelope,
    )


def emit_supervisor_envelope(*, raw_handle: int | None, descriptor: int | None) -> None:
    result_descriptor = _open_result_descriptor(raw_handle=raw_handle, descriptor=descriptor)
    try:
        try:
            envelope = build_supervisor_envelope()
        except BaseException:
            envelope = build_supervisor_envelope(
                worker_runner=lambda: _failed_worker_outcome(FrameStage.NOT_EVALUATED)
            )
        emit_frame(result_descriptor, envelope)
    finally:
        os.close(result_descriptor)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-fixed-fixture", action="store_true", required=True)
    role = parser.add_mutually_exclusive_group(required=True)
    role.add_argument("--supervisor", action="store_true")
    role.add_argument("--worker", action="store_true")
    parser.add_argument("--parent-result-handle", type=int)
    parser.add_argument("--parent-result-fd", type=int)
    parser.add_argument("--worker-result-handle", type=int)
    parser.add_argument("--worker-result-fd", type=int)
    args = parser.parse_args()
    parent_bound = (args.parent_result_handle is not None) + (args.parent_result_fd is not None)
    worker_bound = (args.worker_result_handle is not None) + (args.worker_result_fd is not None)
    if args.supervisor and (parent_bound != 1 or worker_bound != 0):
        parser.error("supervisor requires exactly one parent result channel")
    if args.worker and (worker_bound != 1 or parent_bound != 0):
        parser.error("worker requires exactly one worker result channel")
    return args


def main() -> None:
    args = _arguments()
    if args.worker:
        emit_worker_fixture(
            raw_handle=args.worker_result_handle,
            descriptor=args.worker_result_fd,
        )
    else:
        emit_supervisor_envelope(
            raw_handle=args.parent_result_handle,
            descriptor=args.parent_result_fd,
        )


if __name__ == "__main__":
    main()


__all__ = [
    "CHILD_FLAGS",
    "FIXED_PROCESS_ENVIRONMENT",
    "FRAME_BODY_LIMIT",
    "FRAME_OUTPUT_LIMIT",
    "FrameDecodeResult",
    "FrameStage",
    "SUPERVISOR_SCHEMA_VERSION",
    "SupervisorCode",
    "WORKER_SCHEMA_VERSION",
    "WorkerProcessOutcome",
    "_write_all",
    "build_supervisor_envelope",
    "decode_frame",
    "decode_supervisor_frame",
    "decode_worker_frame",
    "emit_frame",
    "emit_supervisor_envelope",
    "emit_worker_fixture",
    "encode_frame",
    "fixed_worker_fixture",
    "run_worker_process",
    "validate_supervisor_envelope",
    "validate_worker_fixture",
]
