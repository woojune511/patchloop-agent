"""Lifecycle-internal v25 adapter for the source-qualified v24 projection.

Importing this stdlib-only module performs no observation or process launch.
The worker passes the direct, pre-canonical child to v24, so the legacy
order-sensitive validator runs before canonical framing.  Only v24's
value-free projection crosses either anonymous-pipe boundary.  Invalid bytes,
exception details, and credential metadata are discarded.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

CHILD_FLAGS = ("-I", "-E", "-s", "-B")
FIXED_PROCESS_ENVIRONMENT = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "SYSTEMROOT": r"C:\Windows",
}
PROCESS_TIMEOUT_SECONDS = 30
SUPERVISOR_SCHEMA_VERSION = "order-stable-typed-diagnostic-supervisor-envelope-v25"


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
    WORKER_FRAME_INVALID = "worker_frame_invalid"


@dataclass(frozen=True)
class FrameDecodeResult:
    stage: FrameStage
    value: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if (self.stage == FrameStage.VALID) != (self.value is not None):
            raise ValueError("v25 frame decode result shape differs")


@dataclass(frozen=True)
class WorkerProcessOutcome:
    launch_attempt_count: int
    process_return_count: int
    returncode: int | None
    frame: FrameDecodeResult
    activity_accounting_complete: bool
    unknown_process_activity_possible: bool


def _root(repository: str | Path) -> Path:
    return Path(repository).resolve(strict=True)


def _add_root(root: Path) -> None:
    selected = str(root)
    if selected not in sys.path:
        sys.path.insert(0, selected)


def _load_framing(root: Path) -> Any:
    _add_root(root)
    from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v21 as framing

    return framing


def _load_projection(root: Path) -> Any:
    _add_root(root)
    from scripts import run_order_stable_typed_diagnostic_projection_v24 as projection

    return projection


def _launch_kwargs(
    root: Path,
    write_descriptor: int,
    *,
    role: str,
    result_role: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    python = Path(sys.executable).resolve(strict=True)
    script = Path(__file__).resolve(strict=True)
    argv = [
        str(python),
        *CHILD_FLAGS,
        str(script),
        "--repository",
        str(root),
        f"--{role}",
    ]
    kwargs: dict[str, Any] = {
        "cwd": root,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "shell": False,
        "close_fds": True,
        "env": dict(FIXED_PROCESS_ENVIRONMENT),
    }
    selected_result_role = role if result_role is None else result_role
    if os.name == "nt":
        import msvcrt

        raw_handle = msvcrt.get_osfhandle(write_descriptor)
        argv.extend((f"--{selected_result_role}-result-handle", str(raw_handle)))
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        startupinfo.lpAttributeList = {"handle_list": [raw_handle]}
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        argv.extend((f"--{selected_result_role}-result-fd", str(write_descriptor)))
        kwargs["pass_fds"] = (write_descriptor,)
    return argv, kwargs


def _open_result_descriptor(
    repository: str | Path,
    *,
    raw_handle: int | None,
    descriptor: int | None,
) -> int:
    framing = _load_framing(_root(repository))
    return framing._open_result_descriptor(raw_handle=raw_handle, descriptor=descriptor)


def _convert_decode(value: Any) -> FrameDecodeResult:
    return FrameDecodeResult(FrameStage(value.stage.value), value.value)


def encode_frame(repository: str | Path, value: dict[str, Any]) -> bytes:
    return _load_framing(_root(repository)).encode_frame(value)


def emit_frame(repository: str | Path, descriptor: int, value: dict[str, Any]) -> None:
    _load_framing(_root(repository)).emit_frame(descriptor, value)


def decode_worker_frame(repository: str | Path, raw: bytes) -> FrameDecodeResult:
    projection = _load_projection(_root(repository))
    return _convert_decode(projection.decode_projection_frame(raw))


def _exact_count(value: Any, *, maximum: int = 1) -> bool:
    return type(value) is int and 0 <= value <= maximum


def validate_live_supervisor_envelope(
    value: dict[str, Any], repository: str | Path | None = None
) -> bool:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "code",
        "worker_frame_stage",
        "projection",
        "activity",
        "raw_output_returned",
        "exception_message_type_repr_or_traceback_returned",
        "credential_value_hash_prefix_or_length_returned",
    }:
        return False
    if value["schema_version"] != SUPERVISOR_SCHEMA_VERSION:
        return False
    if any(
        type(value[key]) is not bool or value[key]
        for key in (
            "raw_output_returned",
            "exception_message_type_repr_or_traceback_returned",
            "credential_value_hash_prefix_or_length_returned",
        )
    ):
        return False
    try:
        stage = FrameStage(value["worker_frame_stage"])
    except (TypeError, ValueError):
        return False
    activity = value["activity"]
    if type(activity) is not dict or set(activity) != {
        "worker_launch_attempt_count",
        "worker_process_return_count",
        "worker_returncode",
        "activity_accounting_complete",
        "unknown_process_activity_possible",
    }:
        return False
    if not _exact_count(activity["worker_launch_attempt_count"]) or not _exact_count(
        activity["worker_process_return_count"]
    ):
        return False
    if activity["worker_returncode"] is not None and type(activity["worker_returncode"]) is not int:
        return False
    if any(
        type(activity[key]) is not bool
        for key in ("activity_accounting_complete", "unknown_process_activity_possible")
    ):
        return False
    if activity["worker_process_return_count"] != int(activity["worker_returncode"] is not None):
        return False
    projection = value["projection"]
    if projection is not None:
        try:
            root = Path(__file__).resolve().parents[1] if repository is None else _root(repository)
            projection_valid = _load_projection(root).validate_projection(projection)
        except BaseException:
            return False
        projection_activity = projection.get("activity") if type(projection) is dict else None
        return bool(
            value["code"] is None
            and stage == FrameStage.VALID
            and activity["worker_launch_attempt_count"] == 1
            and activity["worker_process_return_count"] == 1
            and activity["worker_returncode"] == 0
            and projection_valid is True
            and type(projection_activity) is dict
            and activity["activity_accounting_complete"]
            == projection_activity["activity_accounting_complete"]
            and activity["unknown_process_activity_possible"]
            == projection_activity["unknown_workload_activity_possible"]
        )
    if value["code"] == SupervisorCode.WORKER_LAUNCH_ERROR.value:
        expected = (0, None, FrameStage.NOT_EVALUATED)
    elif value["code"] == SupervisorCode.WORKER_NONZERO_EXIT.value:
        if activity["worker_returncode"] in {None, 0}:
            return False
        expected = (1, activity["worker_returncode"], FrameStage.NOT_EVALUATED)
    elif value["code"] == SupervisorCode.WORKER_FRAME_INVALID.value:
        expected = (1, 0, stage)
        if stage == FrameStage.VALID:
            return False
    else:
        return False
    return (
        (
            activity["worker_process_return_count"],
            activity["worker_returncode"],
            stage,
        )
        == expected
        and activity["activity_accounting_complete"] is False
        and activity["unknown_process_activity_possible"] is True
    )


def decode_supervisor_frame(repository: str | Path, raw: bytes) -> FrameDecodeResult:
    root = _root(repository)
    framing = _load_framing(root)
    decoded = framing.decode_frame(
        raw,
        expected_schema_version=SUPERVISOR_SCHEMA_VERSION,
        semantic_validator=lambda value: validate_live_supervisor_envelope(value, root),
    )
    return _convert_decode(decoded)


class _BoundedFrameReader:
    def __init__(self, repository: Path, descriptor: int, *, supervisor: bool) -> None:
        self.repository = repository
        self.descriptor = descriptor
        self.supervisor = supervisor
        self._buffer = bytearray()
        self.failed = False
        self.over_limit = False

    def consume(self) -> None:
        limit = _load_framing(self.repository).FRAME_OUTPUT_LIMIT
        try:
            while True:
                chunk = os.read(self.descriptor, 8192)
                if not chunk:
                    break
                remaining = limit + 1 - len(self._buffer)
                if remaining > 0:
                    self._buffer.extend(chunk[:remaining])
                if len(self._buffer) > limit:
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
        if self.supervisor:
            return decode_supervisor_frame(self.repository, raw)
        return decode_worker_frame(self.repository, raw)


def emit_live_worker(
    repository: str | Path,
    *,
    raw_handle: int | None,
    descriptor: int | None,
) -> None:
    root = _root(repository)
    selected = _open_result_descriptor(
        root,
        raw_handle=raw_handle,
        descriptor=descriptor,
    )
    projection = _load_projection(root)
    try:
        try:
            from scripts.run_sanitized_sdk_diagnostic_child import _run

            observed = _run(root)
            value = projection.project_observed_child(root, observed)
        except BaseException:
            value = projection.project_observed_child(root, {"schema_version": "invalid"})
        emit_frame(root, selected, value)
    finally:
        os.close(selected)


def _failed_worker_outcome(
    stage: FrameStage,
    *,
    returned: int = 0,
    returncode: int | None = None,
) -> WorkerProcessOutcome:
    return WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=returned,
        returncode=returncode,
        frame=FrameDecodeResult(stage),
        activity_accounting_complete=False,
        unknown_process_activity_possible=True,
    )


def run_live_worker_process(
    repository: str | Path,
    *,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> WorkerProcessOutcome:
    root = _root(repository)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedFrameReader(root, read_descriptor, supervisor=False)
    thread = threading.Thread(target=reader.consume, daemon=True)
    argv, kwargs = _launch_kwargs(root, write_descriptor, role="worker")
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
            returned=int(returncode is not None),
            returncode=returncode,
        )
    decoded = reader.decode_and_discard()
    if returncode != 0:
        return _failed_worker_outcome(
            FrameStage.NOT_EVALUATED,
            returned=int(returncode is not None),
            returncode=returncode,
        )
    projection_activity = None if decoded.value is None else decoded.value.get("activity")
    complete = bool(
        decoded.stage == FrameStage.VALID
        and type(projection_activity) is dict
        and projection_activity.get("activity_accounting_complete") is True
    )
    unknown = bool(
        decoded.stage != FrameStage.VALID
        or type(projection_activity) is not dict
        or projection_activity.get("unknown_workload_activity_possible") is True
    )
    return WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=decoded,
        activity_accounting_complete=complete,
        unknown_process_activity_possible=unknown,
    )


def build_supervisor_envelope(outcome: WorkerProcessOutcome) -> dict[str, Any]:
    projection = outcome.frame.value if outcome.frame.stage == FrameStage.VALID else None
    if projection is not None:
        code = None
    elif outcome.process_return_count == 0:
        code = SupervisorCode.WORKER_LAUNCH_ERROR.value
    elif outcome.returncode not in {None, 0}:
        code = SupervisorCode.WORKER_NONZERO_EXIT.value
    else:
        code = SupervisorCode.WORKER_FRAME_INVALID.value
    value = {
        "schema_version": SUPERVISOR_SCHEMA_VERSION,
        "code": code,
        "worker_frame_stage": outcome.frame.stage.value,
        "projection": projection,
        "activity": {
            "worker_launch_attempt_count": outcome.launch_attempt_count,
            "worker_process_return_count": outcome.process_return_count,
            "worker_returncode": outcome.returncode,
            "activity_accounting_complete": outcome.activity_accounting_complete,
            "unknown_process_activity_possible": outcome.unknown_process_activity_possible,
        },
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }
    if not validate_live_supervisor_envelope(value):
        raise ValueError("v25 supervisor envelope is invalid")
    return value


def emit_live_supervisor(
    repository: str | Path,
    *,
    raw_handle: int | None,
    descriptor: int | None,
) -> None:
    root = _root(repository)
    selected = _open_result_descriptor(
        root,
        raw_handle=raw_handle,
        descriptor=descriptor,
    )
    try:
        value = build_supervisor_envelope(run_live_worker_process(root))
        emit_frame(root, selected, value)
    finally:
        os.close(selected)


def run_live_supervisor_process(
    repository: str | Path,
    *,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> dict[str, Any]:
    """Launch one supervisor and return only a sanitized typed projection."""

    root = _root(repository)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedFrameReader(root, read_descriptor, supervisor=True)
    thread = threading.Thread(target=reader.consume, daemon=True)
    argv, kwargs = _launch_kwargs(
        root,
        write_descriptor,
        role="supervisor",
        result_role="parent",
    )
    try:
        process = popen(argv, **kwargs)
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(write_descriptor)
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        return {
            "launch_attempt_count": 1,
            "process_return_count": 0,
            "returncode": None,
            "frame_stage": FrameStage.NOT_EVALUATED.value,
            "envelope": None,
            "activity_accounting_complete": False,
            "unknown_process_activity_possible": True,
        }
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
    if timed_out or thread.is_alive() or returncode != 0:
        reader._buffer.clear()
        return {
            "launch_attempt_count": 1,
            "process_return_count": int(returncode is not None),
            "returncode": returncode,
            "frame_stage": FrameStage.READ_ERROR.value,
            "envelope": None,
            "activity_accounting_complete": False,
            "unknown_process_activity_possible": True,
        }
    decoded = reader.decode_and_discard()
    valid = decoded.stage == FrameStage.VALID and decoded.value is not None
    envelope = decoded.value if valid else None
    inner_activity = None if envelope is None else envelope.get("activity")
    inner_complete = isinstance(inner_activity, dict) and (
        inner_activity.get("activity_accounting_complete") is True
    )
    inner_unknown = not isinstance(inner_activity, dict) or (
        inner_activity.get("unknown_process_activity_possible") is True
    )
    return {
        "launch_attempt_count": 1,
        "process_return_count": 1,
        "returncode": 0,
        "frame_stage": decoded.stage.value,
        "envelope": envelope,
        "activity_accounting_complete": bool(valid and inner_complete),
        "unknown_process_activity_possible": bool(not valid or inner_unknown),
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    role = parser.add_mutually_exclusive_group(required=True)
    role.add_argument("--worker", action="store_true")
    role.add_argument("--supervisor", action="store_true")
    parser.add_argument("--worker-result-handle", type=int)
    parser.add_argument("--worker-result-fd", type=int)
    parser.add_argument("--parent-result-handle", type=int)
    parser.add_argument("--parent-result-fd", type=int)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    if args.worker:
        if args.parent_result_handle is not None or args.parent_result_fd is not None:
            raise SystemExit("worker rejects parent result channel")
        emit_live_worker(
            args.repository,
            raw_handle=args.worker_result_handle,
            descriptor=args.worker_result_fd,
        )
    else:
        if args.worker_result_handle is not None or args.worker_result_fd is not None:
            raise SystemExit("supervisor rejects worker result channel")
        emit_live_supervisor(
            args.repository,
            raw_handle=args.parent_result_handle,
            descriptor=args.parent_result_fd,
        )


if __name__ == "__main__":
    main()
