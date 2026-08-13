"""V22 typed diagnostic envelopes over a strict two-hop result channel.

The public CLI exposes only a fixed, public, offline mock. The live adapter is
projection-only: callers supply an already observed child or a fixed error
code, and no v22 API or CLI invokes ``.env``, an SDK, Docker, or a network.

Invalid frame bytes are classified and immediately discarded.  Decode results
never retain invalid bytes, byte counts, digests, exception text, or traceback
material.  Importing this module performs no observation or process launch.
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

OFFLINE_WORKER_SCHEMA_VERSION = "offline-fixed-diagnostic-worker-mock-v22"
OFFLINE_SUPERVISOR_SCHEMA_VERSION = "offline-fixed-diagnostic-supervisor-mock-v22"
LIVE_WORKER_SCHEMA_VERSION = "live-no-call-diagnostic-worker-envelope-v22"
LIVE_SUPERVISOR_SCHEMA_VERSION = "live-no-call-diagnostic-supervisor-envelope-v22"
FIXTURE_ID = "v22-public-fixed-blocked-diagnostic-mock"

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
PROCESS_TIMEOUT_SECONDS = 30


class Mode(StrEnum):
    OFFLINE_FIXED_MOCK = "offline_fixed_mock"
    LIVE = "live"


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


class WorkerCode(StrEnum):
    DIAGNOSTIC_EXECUTION_ERROR = "diagnostic_execution_error"
    DIAGNOSTIC_RESULT_INVALID = "diagnostic_result_invalid"


@dataclass(frozen=True)
class FrameDecodeResult:
    """A sanitized result which contains a value only for a valid frame."""

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


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _write_all(
    descriptor: int,
    data: bytes,
    *,
    write: Callable[[int, bytes | memoryview], int] = os.write,
    limit: int = FRAME_OUTPUT_LIMIT,
) -> None:
    """Write one bounded frame completely, retrying interrupted writes."""

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
    """Decode one canonical frame without retaining invalid raw metadata."""

    if raw == b"":
        return FrameDecodeResult(FrameStage.NO_MESSAGE)
    if not isinstance(raw, bytes) or len(raw) < FRAME_HEADER_BYTES:
        return FrameDecodeResult(FrameStage.HEADER_INVALID)
    declared = int.from_bytes(raw[:FRAME_LENGTH_BYTES], "big")
    if declared <= 0 or declared > FRAME_BODY_LIMIT:
        return FrameDecodeResult(FrameStage.BODY_LENGTH_INVALID)
    if len(raw) != FRAME_HEADER_BYTES + declared:
        return FrameDecodeResult(FrameStage.FRAME_LENGTH_INVALID)
    digest = raw[FRAME_LENGTH_BYTES:FRAME_HEADER_BYTES]
    body = raw[FRAME_HEADER_BYTES:]
    if not hmac.compare_digest(hashlib.sha256(body).digest(), digest):
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
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
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


def _fixed_child() -> dict[str, Any]:
    """Return a public, value-free, blocked diagnostic payload."""

    return {
        "schema_version": "isolated-dotenv-sanitized-sdk-diagnostic-v1",
        "state": "blocked",
        "dotenv": {
            "file_present": False,
            "exact_subject_declared": False,
            "exact_subject_nonempty": False,
            "duplicate_subject": False,
            "error_code": "dotenv_missing",
            "raw_value_returned": False,
            "value_hash_prefix_or_length_returned": False,
        },
        "diagnostic": None,
        "error_code": "dotenv_missing",
        "activity": {
            "dotenv_file_read_count": 0,
            "dotenv_subject_membership_check_count": 0,
            "credential_assignment_parse_count": 0,
            "credential_value_return_count": 0,
            "credential_value_hash_prefix_or_length_count": 0,
            "exception_message_type_repr_or_traceback_return_count": 0,
            "transport_dispatch_count": 0,
            "network_call_count": 0,
            "provider_evaluator_agent_call_count": 0,
        },
        "raw_credential_value_returned": False,
        "credential_hash_prefix_or_length_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
    }


def _worker_activity(
    *, diagnostic_invocation_count: int, typed_validation_count: int, complete: bool
) -> dict[str, Any]:
    return {
        "diagnostic_invocation_count": diagnostic_invocation_count,
        "typed_validation_count": typed_validation_count,
        "raw_workload_output_return_count": 0,
        "exception_message_type_repr_or_traceback_return_count": 0,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "activity_accounting_complete": complete,
        "unknown_workload_activity_possible": not complete,
    }


def fixed_worker_fixture() -> dict[str, Any]:
    return {
        "schema_version": OFFLINE_WORKER_SCHEMA_VERSION,
        "fixture_id": FIXTURE_ID,
        "child": _fixed_child(),
        "code": None,
        "activity": _worker_activity(
            diagnostic_invocation_count=0,
            typed_validation_count=1,
            complete=True,
        ),
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def _strict_zero(value: Any) -> bool:
    return type(value) is int and value == 0


def _validate_child_shape(value: Any) -> bool:
    """Strictly recognize only the fixed public child without coercion."""

    expected = _fixed_child()
    if not isinstance(value, dict) or value != expected:
        return False
    activity = value.get("activity")
    return isinstance(activity, dict) and all(_strict_zero(item) for item in activity.values())


def _validate_worker_activity(value: Any, *, offline: bool, success: bool) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "diagnostic_invocation_count",
        "typed_validation_count",
        "raw_workload_output_return_count",
        "exception_message_type_repr_or_traceback_return_count",
        "credential_value_return_hash_prefix_or_length_count",
        "activity_accounting_complete",
        "unknown_workload_activity_possible",
    }:
        return False
    counts = (
        "diagnostic_invocation_count",
        "typed_validation_count",
        "raw_workload_output_return_count",
        "exception_message_type_repr_or_traceback_return_count",
        "credential_value_return_hash_prefix_or_length_count",
    )
    if any(type(value[key]) is not int for key in counts):
        return False
    if any(value[key] != 0 for key in counts[2:]):
        return False
    if type(value["activity_accounting_complete"]) is not bool:
        return False
    if type(value["unknown_workload_activity_possible"]) is not bool:
        return False
    if value["activity_accounting_complete"] == value["unknown_workload_activity_possible"]:
        return False
    if offline:
        return (
            value["diagnostic_invocation_count"] == 0
            and value["typed_validation_count"] == 1
            and value["activity_accounting_complete"]
            and success
        )
    expected = (1, 1) if success else None
    if expected is not None:
        return (
            value["diagnostic_invocation_count"],
            value["typed_validation_count"],
        ) == expected and value["activity_accounting_complete"]
    return (
        value["diagnostic_invocation_count"] == 1
        and value["typed_validation_count"] in {0, 1}
        and not value["activity_accounting_complete"]
    )


def validate_offline_worker_fixture(value: dict[str, Any]) -> bool:
    if value != fixed_worker_fixture() or set(value) != set(fixed_worker_fixture()):
        return False
    return _validate_worker_activity(value.get("activity"), offline=True, success=True)


def _strict_typed_child(repository: Path, value: dict[str, Any]) -> dict[str, Any]:
    """Revalidate a supplied child with the canonical project model."""

    root = repository.resolve(strict=True)
    added = False
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
        added = True
    try:
        from patchloop.evals.sanitized_sdk_parent_integration import IsolatedDiagnosticChild

        def has_exact_json_types(item: Any) -> bool:
            if item is None or type(item) in {str, int, float, bool}:
                return True
            if type(item) is list:
                return all(has_exact_json_types(nested) for nested in item)
            if type(item) is dict:
                return all(
                    type(key) is str and has_exact_json_types(nested)
                    for key, nested in item.items()
                )
            return False

        if not has_exact_json_types(value):
            raise ValueError("typed diagnostic input uses non-JSON runtime types")
        model = IsolatedDiagnosticChild.model_validate_json(_canonical(value), strict=True)
        projected = model.model_dump(mode="json")
        if _canonical(value) != _canonical(projected):
            raise ValueError("typed diagnostic input requires coercion")
        return projected
    finally:
        if added:
            with contextlib.suppress(ValueError):
                sys.path.remove(str(root))


def _worker_error(code: WorkerCode, *, typed_validation_count: int) -> dict[str, Any]:
    return {
        "schema_version": LIVE_WORKER_SCHEMA_VERSION,
        "child": None,
        "code": code.value,
        "activity": _worker_activity(
            diagnostic_invocation_count=1,
            typed_validation_count=typed_validation_count,
            complete=False,
        ),
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def project_worker_envelope(
    repository: str | Path,
    *,
    mode: Mode,
    observed_child: dict[str, Any] | None = None,
    observed_error: WorkerCode | None = None,
) -> dict[str, Any]:
    """Project an already observed child without invoking an observation callback."""

    if mode == Mode.OFFLINE_FIXED_MOCK:
        if observed_child is not None or observed_error is not None:
            raise ValueError("offline fixed mock rejects live observations")
        return fixed_worker_fixture()
    if mode != Mode.LIVE or (observed_child is None) == (observed_error is None):
        raise ValueError("exactly one live diagnostic observation is required")
    if observed_error is not None:
        code = WorkerCode(observed_error)
        return _worker_error(
            code,
            typed_validation_count=int(code == WorkerCode.DIAGNOSTIC_RESULT_INVALID),
        )
    root = Path(repository).resolve(strict=True)
    try:
        child = _strict_typed_child(root, observed_child)
    except BaseException:
        return _worker_error(WorkerCode.DIAGNOSTIC_RESULT_INVALID, typed_validation_count=1)
    return {
        "schema_version": LIVE_WORKER_SCHEMA_VERSION,
        "child": child,
        "code": None,
        "activity": _worker_activity(
            diagnostic_invocation_count=1,
            typed_validation_count=1,
            complete=True,
        ),
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def validate_live_worker_envelope(value: dict[str, Any]) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "child",
        "code",
        "activity",
        "raw_output_returned",
        "exception_message_type_repr_or_traceback_returned",
        "credential_value_hash_prefix_or_length_returned",
    }:
        return False
    if value.get("schema_version") != LIVE_WORKER_SCHEMA_VERSION:
        return False
    if any(
        value.get(key) is not False
        for key in (
            "raw_output_returned",
            "exception_message_type_repr_or_traceback_returned",
            "credential_value_hash_prefix_or_length_returned",
        )
    ):
        return False
    success = value.get("code") is None
    if success:
        if not isinstance(value.get("child"), dict):
            return False
        try:
            projected = _strict_typed_child(Path(__file__).resolve().parents[1], value["child"])
        except BaseException:
            return False
        if projected != value["child"]:
            return False
    else:
        if value.get("child") is not None or value.get("code") not in {
            item.value for item in WorkerCode
        }:
            return False
    activity = value.get("activity")
    if not _validate_worker_activity(activity, offline=False, success=success):
        return False
    if not success:
        expected_validations = int(value["code"] == WorkerCode.DIAGNOSTIC_RESULT_INVALID)
        if activity["typed_validation_count"] != expected_validations:
            return False
    return True


def decode_worker_frame(raw: bytes, *, mode: Mode) -> FrameDecodeResult:
    if mode == Mode.OFFLINE_FIXED_MOCK:
        schema = OFFLINE_WORKER_SCHEMA_VERSION
        validator = validate_offline_worker_fixture
    elif mode == Mode.LIVE:
        schema = LIVE_WORKER_SCHEMA_VERSION
        validator = validate_live_worker_envelope
    else:
        return FrameDecodeResult(FrameStage.SEMANTIC_INVALID)
    return decode_frame(raw, expected_schema_version=schema, semantic_validator=validator)


class _BoundedFrameReader:
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

    def decode_and_discard(self, *, mode: Mode, supervisor: bool = False) -> FrameDecodeResult:
        if self.failed:
            self._buffer.clear()
            return FrameDecodeResult(FrameStage.READ_ERROR)
        if self.over_limit:
            self._buffer.clear()
            return FrameDecodeResult(FrameStage.OUTPUT_LIMIT)
        raw = bytes(self._buffer)
        self._buffer.clear()
        if supervisor:
            return decode_supervisor_frame(raw, mode=mode)
        return decode_worker_frame(raw, mode=mode)


def _open_result_descriptor(*, raw_handle: int | None, descriptor: int | None) -> int:
    if os.name == "nt":
        if raw_handle is None or descriptor is not None:
            raise RuntimeError("result handle binding differs")
        import msvcrt

        return msvcrt.open_osfhandle(raw_handle, os.O_WRONLY | os.O_BINARY)
    if descriptor is None or raw_handle is not None:
        raise RuntimeError("result descriptor binding differs")
    return descriptor


def emit_offline_worker(*, raw_handle: int | None, descriptor: int | None) -> None:
    selected = _open_result_descriptor(raw_handle=raw_handle, descriptor=descriptor)
    try:
        emit_frame(selected, fixed_worker_fixture())
    finally:
        os.close(selected)


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


def _launch_kwargs(write_descriptor: int) -> tuple[list[str], dict[str, Any]]:
    script = Path(__file__).resolve(strict=True)
    python = Path(sys.executable).resolve(strict=True)
    argv = [str(python), *CHILD_FLAGS, str(script), "--offline-fixed-mock"]
    kwargs: dict[str, Any] = {
        "cwd": script.parent,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "shell": False,
        "env": dict(FIXED_PROCESS_ENVIRONMENT),
        "close_fds": True,
    }
    if os.name == "nt":
        import msvcrt

        raw_handle = msvcrt.get_osfhandle(write_descriptor)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.lpAttributeList = {"handle_list": [raw_handle]}
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return argv, kwargs


def _bind_result_channel(
    argv: list[str], kwargs: dict[str, Any], write_descriptor: int, *, role: str
) -> None:
    if os.name == "nt":
        import msvcrt

        raw_handle = msvcrt.get_osfhandle(write_descriptor)
        argv.extend((f"--{role}-result-handle", str(raw_handle)))
    else:
        argv.extend((f"--{role}-result-fd", str(write_descriptor)))
        kwargs["pass_fds"] = (write_descriptor,)


def run_worker_process(
    _repository: str | Path | None = None,
    *,
    mode: Mode = Mode.OFFLINE_FIXED_MOCK,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> WorkerProcessOutcome:
    """Launch the sole public worker mode; live process launch is unavailable."""

    if mode != Mode.OFFLINE_FIXED_MOCK:
        raise ValueError("live worker process entrypoint is closed")
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedFrameReader(read_descriptor)
    thread = threading.Thread(target=reader.consume, daemon=True)
    argv, kwargs = _launch_kwargs(write_descriptor)
    argv.append("--worker")
    _bind_result_channel(argv, kwargs, write_descriptor, role="worker")
    try:
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
        returncode = process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
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
    decoded = reader.decode_and_discard(mode=mode)
    if returncode != 0:
        return _failed_worker_outcome(
            FrameStage.NOT_EVALUATED,
            process_return_count=int(returncode is not None),
            returncode=returncode,
        )
    complete = decoded.stage == FrameStage.VALID
    return WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=decoded,
        activity_accounting_complete=complete,
        unknown_process_activity_possible=not complete,
    )


def _supervisor_activity(outcome: WorkerProcessOutcome) -> dict[str, Any]:
    complete = outcome.activity_accounting_complete
    unknown = outcome.unknown_process_activity_possible
    if outcome.frame.stage == FrameStage.VALID and outcome.frame.value is not None:
        inner = outcome.frame.value.get("activity")
        if isinstance(inner, dict):
            inner_complete = inner.get("activity_accounting_complete") is True
            inner_unknown = inner.get("unknown_workload_activity_possible") is True
            complete = complete and inner_complete
            unknown = unknown or inner_unknown
        else:
            complete = False
            unknown = True
    return {
        "worker_launch_attempt_count": outcome.launch_attempt_count,
        "worker_process_return_count": outcome.process_return_count,
        "worker_result_message_count": int(outcome.frame.stage == FrameStage.VALID),
        "worker_returncode": outcome.returncode,
        "worker_valid_frame_count": int(outcome.frame.stage == FrameStage.VALID),
        "raw_workload_output_return_count": 0,
        "exception_message_type_repr_or_traceback_return_count": 0,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "activity_accounting_complete": complete,
        "unknown_process_activity_possible": unknown,
    }


def _supervisor_code(outcome: WorkerProcessOutcome) -> SupervisorCode | None:
    if outcome.process_return_count != 1 or outcome.returncode is None:
        return SupervisorCode.WORKER_LAUNCH_ERROR
    if outcome.returncode != 0:
        return SupervisorCode.WORKER_NONZERO_EXIT
    if outcome.frame.stage in {FrameStage.NOT_EVALUATED, FrameStage.READ_ERROR}:
        return SupervisorCode.WORKER_PROCESS_INCOMPLETE
    if outcome.frame.stage != FrameStage.VALID:
        return SupervisorCode.WORKER_FRAME_INVALID
    if not outcome.activity_accounting_complete:
        return SupervisorCode.WORKER_PROCESS_INCOMPLETE
    return None


def build_supervisor_envelope(
    repository: str | Path | None,
    *,
    mode: Mode,
    worker_runner: Callable[..., WorkerProcessOutcome] | None = None,
    observed_outcome: WorkerProcessOutcome | None = None,
) -> dict[str, Any]:
    """Build an offline mock result or project an already observed live outcome."""

    if mode == Mode.OFFLINE_FIXED_MOCK:
        if observed_outcome is not None:
            raise ValueError("offline fixed mock rejects live observations")
        runner = run_worker_process if worker_runner is None else worker_runner
        try:
            outcome = runner(repository, mode=mode)
        except BaseException:
            outcome = _failed_worker_outcome(FrameStage.NOT_EVALUATED)
    elif mode == Mode.LIVE:
        if worker_runner is not None or observed_outcome is None:
            raise ValueError("live supervisor accepts only an observed outcome")
        outcome = observed_outcome
    else:
        raise ValueError("diagnostic mode differs")
    code = _supervisor_code(outcome)
    payload = outcome.frame.value if code is None else None
    base = {
        "schema_version": (
            OFFLINE_SUPERVISOR_SCHEMA_VERSION
            if mode == Mode.OFFLINE_FIXED_MOCK
            else LIVE_SUPERVISOR_SCHEMA_VERSION
        ),
        "code": None if code is None else code.value,
        "worker_frame_stage": outcome.frame.stage.value,
        "activity": _supervisor_activity(outcome),
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }
    if mode == Mode.OFFLINE_FIXED_MOCK:
        base["fixture"] = payload
    else:
        base["worker"] = payload
    return base


def _validate_supervisor_activity(value: Any, *, valid: bool) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "worker_launch_attempt_count",
        "worker_process_return_count",
        "worker_result_message_count",
        "worker_returncode",
        "worker_valid_frame_count",
        "raw_workload_output_return_count",
        "exception_message_type_repr_or_traceback_return_count",
        "credential_value_return_hash_prefix_or_length_count",
        "activity_accounting_complete",
        "unknown_process_activity_possible",
    }:
        return False
    count_fields = (
        "worker_launch_attempt_count",
        "worker_process_return_count",
        "worker_result_message_count",
        "worker_valid_frame_count",
        "raw_workload_output_return_count",
        "exception_message_type_repr_or_traceback_return_count",
        "credential_value_return_hash_prefix_or_length_count",
    )
    if any(type(value[key]) is not int for key in count_fields):
        return False
    if any(value[key] != 0 for key in count_fields[-3:]):
        return False
    if value["worker_returncode"] is not None and type(value["worker_returncode"]) is not int:
        return False
    if type(value["activity_accounting_complete"]) is not bool:
        return False
    if type(value["unknown_process_activity_possible"]) is not bool:
        return False
    if value["activity_accounting_complete"] == value["unknown_process_activity_possible"]:
        return False
    if value["worker_launch_attempt_count"] != 1:
        return False
    if value["worker_process_return_count"] != int(value["worker_returncode"] is not None):
        return False
    if value["worker_result_message_count"] != int(valid):
        return False
    return value["worker_valid_frame_count"] == int(valid)


def _validate_supervisor(value: dict[str, Any], *, mode: Mode) -> bool:
    payload_key = "fixture" if mode == Mode.OFFLINE_FIXED_MOCK else "worker"
    expected_schema = (
        OFFLINE_SUPERVISOR_SCHEMA_VERSION
        if mode == Mode.OFFLINE_FIXED_MOCK
        else LIVE_SUPERVISOR_SCHEMA_VERSION
    )
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        payload_key,
        "code",
        "worker_frame_stage",
        "activity",
        "raw_output_returned",
        "exception_message_type_repr_or_traceback_returned",
        "credential_value_hash_prefix_or_length_returned",
    }:
        return False
    if value.get("schema_version") != expected_schema:
        return False
    if any(
        value.get(key) is not False
        for key in (
            "raw_output_returned",
            "exception_message_type_repr_or_traceback_returned",
            "credential_value_hash_prefix_or_length_returned",
        )
    ):
        return False
    try:
        stage = FrameStage(value.get("worker_frame_stage"))
        code = None if value.get("code") is None else SupervisorCode(value.get("code"))
    except (TypeError, ValueError):
        return False
    payload = value.get(payload_key)
    success = code is None
    if success != (payload is not None) or success != (stage == FrameStage.VALID):
        return False
    if success:
        if mode == Mode.OFFLINE_FIXED_MOCK:
            if not validate_offline_worker_fixture(payload):
                return False
        elif not validate_live_worker_envelope(payload):
            return False
    activity = value.get("activity")
    if not _validate_supervisor_activity(activity, valid=stage == FrameStage.VALID):
        return False
    returncode = activity["worker_returncode"]
    complete = activity["activity_accounting_complete"]
    if code is None:
        inner_activity = payload["activity"]
        return (
            returncode == 0
            and complete == inner_activity["activity_accounting_complete"]
            and activity["unknown_process_activity_possible"]
            == inner_activity["unknown_workload_activity_possible"]
        )
    if code == SupervisorCode.WORKER_LAUNCH_ERROR:
        return returncode is None and stage == FrameStage.NOT_EVALUATED and not complete
    if code == SupervisorCode.WORKER_NONZERO_EXIT:
        return returncode is not None and returncode != 0 and not complete
    if code == SupervisorCode.WORKER_PROCESS_INCOMPLETE:
        return stage in {FrameStage.NOT_EVALUATED, FrameStage.READ_ERROR} and not complete
    if code == SupervisorCode.WORKER_FRAME_INVALID:
        return (
            returncode == 0
            and stage not in {FrameStage.VALID, FrameStage.NOT_EVALUATED, FrameStage.READ_ERROR}
            and not complete
        )
    return stage == FrameStage.NOT_EVALUATED and not complete


def validate_offline_supervisor_envelope(value: dict[str, Any]) -> bool:
    return _validate_supervisor(value, mode=Mode.OFFLINE_FIXED_MOCK)


def validate_live_supervisor_envelope(value: dict[str, Any]) -> bool:
    return _validate_supervisor(value, mode=Mode.LIVE)


def decode_supervisor_frame(raw: bytes, *, mode: Mode) -> FrameDecodeResult:
    if mode == Mode.OFFLINE_FIXED_MOCK:
        schema = OFFLINE_SUPERVISOR_SCHEMA_VERSION
        validator = validate_offline_supervisor_envelope
    elif mode == Mode.LIVE:
        schema = LIVE_SUPERVISOR_SCHEMA_VERSION
        validator = validate_live_supervisor_envelope
    else:
        return FrameDecodeResult(FrameStage.SEMANTIC_INVALID)
    return decode_frame(raw, expected_schema_version=schema, semantic_validator=validator)


def emit_offline_supervisor(*, raw_handle: int | None, descriptor: int | None) -> None:
    selected = _open_result_descriptor(raw_handle=raw_handle, descriptor=descriptor)
    try:
        try:
            value = build_supervisor_envelope(None, mode=Mode.OFFLINE_FIXED_MOCK)
        except BaseException:
            value = build_supervisor_envelope(
                None,
                mode=Mode.OFFLINE_FIXED_MOCK,
                worker_runner=lambda *_args, **_kwargs: _failed_worker_outcome(
                    FrameStage.NOT_EVALUATED
                ),
            )
        emit_frame(selected, value)
    finally:
        os.close(selected)


def _run_offline_supervisor_process(
    *, popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen
) -> FrameDecodeResult:
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedFrameReader(read_descriptor)
    thread = threading.Thread(target=reader.consume, daemon=True)
    argv, kwargs = _launch_kwargs(write_descriptor)
    argv.append("--supervisor")
    _bind_result_channel(argv, kwargs, write_descriptor, role="parent")
    try:
        process = popen(argv, **kwargs)
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(write_descriptor)
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        return FrameDecodeResult(FrameStage.NOT_EVALUATED)
    os.close(write_descriptor)
    thread.start()
    try:
        returncode = process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
    except BaseException:
        try:
            process.kill()
            process.wait(timeout=5)
        except BaseException:
            pass
        returncode = None
    thread.join(timeout=5)
    if thread.is_alive():
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        thread.join(timeout=1)
    if returncode != 0 or thread.is_alive():
        reader._buffer.clear()
        return FrameDecodeResult(FrameStage.READ_ERROR)
    return reader.decode_and_discard(mode=Mode.OFFLINE_FIXED_MOCK, supervisor=True)


def run_offline_fixed_mock_chain() -> dict[str, Any]:
    """Run exactly two local mock process hops; this is never qualification."""

    result = _run_offline_supervisor_process()
    if result.stage != FrameStage.VALID or result.value is None:
        raise RuntimeError("offline fixed mock chain failed")
    return result.value


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-fixed-mock", action="store_true", required=True)
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
        emit_offline_worker(
            raw_handle=args.worker_result_handle,
            descriptor=args.worker_result_fd,
        )
    else:
        emit_offline_supervisor(
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
    "LIVE_SUPERVISOR_SCHEMA_VERSION",
    "LIVE_WORKER_SCHEMA_VERSION",
    "Mode",
    "OFFLINE_SUPERVISOR_SCHEMA_VERSION",
    "OFFLINE_WORKER_SCHEMA_VERSION",
    "SupervisorCode",
    "WorkerCode",
    "WorkerProcessOutcome",
    "_write_all",
    "build_supervisor_envelope",
    "decode_frame",
    "decode_supervisor_frame",
    "decode_worker_frame",
    "emit_frame",
    "encode_frame",
    "fixed_worker_fixture",
    "project_worker_envelope",
    "run_offline_fixed_mock_chain",
    "run_worker_process",
    "validate_live_supervisor_envelope",
    "validate_live_worker_envelope",
    "validate_offline_supervisor_envelope",
    "validate_offline_worker_fixture",
]
