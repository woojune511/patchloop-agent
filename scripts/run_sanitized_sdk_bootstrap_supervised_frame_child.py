"""Stdlib-only supervisor and isolated worker for the v17 frame successor.

The supervisor never imports the diagnostic runtime or reads ``.env``.  It
starts one worker whose stdout and stderr are null from process creation, and
the worker returns one sanitized message over a dedicated anonymous pipe.  The
supervisor alone owns the stdout inherited from its parent and always emits one
canonical envelope.  Importing this module performs no observation or launch.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "sanitized-sdk-bootstrap-supervised-frame-envelope-v1"
WORKER_SCHEMA_VERSION = "sanitized-sdk-bootstrap-supervised-worker-result-v1"
CHILD_FLAGS = ("-I", "-E", "-s", "-B")
FIXED_WORKER_ENVIRONMENT = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
WORKER_TIMEOUT_SECONDS = 45
WORKER_OUTPUT_LIMIT = 262_144


def _canonical(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


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


def _worker_error(
    code: str,
    *,
    diagnostic_invocation_count: int,
    typed_validation_count: int,
    complete: bool,
) -> dict[str, Any]:
    return {
        "schema_version": WORKER_SCHEMA_VERSION,
        "child": None,
        "code": code,
        "activity": _worker_activity(
            diagnostic_invocation_count=diagnostic_invocation_count,
            typed_validation_count=typed_validation_count,
            complete=complete,
        ),
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def _worker_success(child: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": WORKER_SCHEMA_VERSION,
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


def build_worker_message(
    repository: str | Path,
    *,
    diagnostic_runner: Callable[[Path], dict[str, Any]] | None = None,
    typed_validator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one typed worker message; injected callables are offline-test only."""

    root = Path(repository).resolve(strict=True)
    if diagnostic_runner is None or typed_validator is None:
        try:
            sys.path.insert(0, str(root))
            from patchloop.evals.sanitized_sdk_parent_integration import (
                IsolatedDiagnosticChild,
            )
            from scripts.run_sanitized_sdk_diagnostic_child import _run
        except BaseException:
            return _worker_error(
                "diagnostic_wrapper_import_error",
                diagnostic_invocation_count=0,
                typed_validation_count=0,
                complete=True,
            )

        run_diagnostic = _run

        def validate(value: dict[str, Any]) -> dict[str, Any]:
            return IsolatedDiagnosticChild.model_validate(value).model_dump(mode="json")

    else:
        run_diagnostic = diagnostic_runner
        validate = typed_validator

    try:
        raw_child = run_diagnostic(root)
    except BaseException:
        return _worker_error(
            "diagnostic_execution_error",
            diagnostic_invocation_count=1,
            typed_validation_count=0,
            complete=False,
        )
    try:
        child = validate(raw_child)
    except BaseException:
        return _worker_error(
            "diagnostic_result_invalid",
            diagnostic_invocation_count=1,
            typed_validation_count=1,
            complete=False,
        )
    return _worker_success(child)


def _open_worker_result_descriptor(*, raw_handle: int | None, descriptor: int | None) -> int:
    if os.name == "nt":
        if raw_handle is None or descriptor is not None:
            raise RuntimeError("worker result handle binding differs")
        import msvcrt

        return msvcrt.open_osfhandle(raw_handle, os.O_WRONLY | os.O_BINARY)
    if descriptor is None or raw_handle is not None:
        raise RuntimeError("worker result descriptor binding differs")
    return descriptor


def emit_worker_message(
    repository: str | Path,
    *,
    raw_handle: int | None,
    descriptor: int | None,
    diagnostic_runner: Callable[[Path], dict[str, Any]] | None = None,
    typed_validator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> None:
    """Write the sanitized worker result only to its inherited result channel."""

    result_descriptor = _open_worker_result_descriptor(
        raw_handle=raw_handle, descriptor=descriptor
    )
    try:
        try:
            message = build_worker_message(
                repository,
                diagnostic_runner=diagnostic_runner,
                typed_validator=typed_validator,
            )
            raw = _canonical(message)
        except BaseException:
            raw = _canonical(
                _worker_error(
                    "worker_internal_error",
                    diagnostic_invocation_count=0,
                    typed_validation_count=0,
                    complete=False,
                )
            )
        os.write(result_descriptor, raw)
    finally:
        os.close(result_descriptor)


@dataclass(frozen=True)
class WorkerProcessOutcome:
    launch_attempt_count: int
    process_return_count: int
    result_bytes: bytes
    result_within_limit: bool
    returncode: int | None
    complete: bool
    unknown: bool


class _BoundedReader:
    def __init__(self, descriptor: int, limit: int) -> None:
        self.descriptor = descriptor
        self.limit = limit
        self.buffer = bytearray()
        self.total = 0
        self.failed = False

    def consume(self) -> None:
        try:
            while True:
                chunk = os.read(self.descriptor, 8192)
                if not chunk:
                    break
                self.total += len(chunk)
                remaining = self.limit + 1 - len(self.buffer)
                if remaining > 0:
                    self.buffer.extend(chunk[:remaining])
        except BaseException:
            self.failed = True
        finally:
            with contextlib.suppress(OSError):
                os.close(self.descriptor)


def _worker_environment() -> dict[str, str]:
    environment = dict(FIXED_WORKER_ENVIRONMENT)
    systemroot = os.environ.get("SYSTEMROOT")
    if systemroot:
        environment["SYSTEMROOT"] = systemroot
    return environment


def run_worker_process(
    repository: str | Path,
    *,
    worker_script: str | Path | None = None,
    python: str | Path | None = None,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> WorkerProcessOutcome:
    """Launch one worker with null stdio and a bounded anonymous result pipe."""

    root = Path(repository).resolve(strict=True)
    script = Path(worker_script or __file__).resolve(strict=True)
    python_path = Path(python or sys.executable).resolve(strict=True)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = _BoundedReader(read_descriptor, WORKER_OUTPUT_LIMIT)
    thread = threading.Thread(target=reader.consume, daemon=True)
    process: subprocess.Popen[bytes] | None = None
    try:
        argv = [
            str(python_path),
            *CHILD_FLAGS,
            str(script),
            "--repository",
            str(root),
        ]
        kwargs: dict[str, Any] = {
            "cwd": root,
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "shell": False,
            "env": _worker_environment(),
            "close_fds": True,
        }
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
        os.close(write_descriptor)
        os.close(read_descriptor)
        return WorkerProcessOutcome(1, 0, b"", True, None, False, True)

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
    complete = not timed_out and not reader.failed and not thread.is_alive()
    return WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=int(returncode is not None),
        result_bytes=bytes(reader.buffer),
        result_within_limit=reader.total <= WORKER_OUTPUT_LIMIT,
        returncode=returncode,
        complete=complete,
        unknown=not complete,
    )


def _supervisor_activity(
    *,
    launch_attempts: int,
    process_returns: int,
    result_messages: int,
    diagnostic_invocations: int,
    typed_validations: int,
    complete: bool,
) -> dict[str, Any]:
    return {
        "worker_launch_attempt_count": launch_attempts,
        "worker_process_return_count": process_returns,
        "worker_result_message_count": result_messages,
        "diagnostic_invocation_count": diagnostic_invocations,
        "typed_validation_count": typed_validations,
        "worker_stdout_suppressed_from_process_start_count": process_returns,
        "worker_stderr_suppressed_from_process_start_count": process_returns,
        "raw_workload_output_return_count": 0,
        "exception_message_type_repr_or_traceback_return_count": 0,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "activity_accounting_complete": complete,
        "unknown_workload_activity_possible": not complete,
    }


def _supervisor_envelope(
    *,
    child: dict[str, Any] | None,
    code: str | None,
    activity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "child": child,
        "code": code,
        "activity": activity,
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def _process_error(code: str, outcome: WorkerProcessOutcome) -> dict[str, Any]:
    return _supervisor_envelope(
        child=None,
        code=code,
        activity=_supervisor_activity(
            launch_attempts=outcome.launch_attempt_count,
            process_returns=outcome.process_return_count,
            result_messages=0,
            diagnostic_invocations=0,
            typed_validations=0,
            complete=False,
        ),
    )


def _parse_worker_message(raw: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(raw.decode("utf-8"))
    except BaseException:
        return None
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "child",
        "code",
        "activity",
        "raw_output_returned",
        "exception_message_type_repr_or_traceback_returned",
        "credential_value_hash_prefix_or_length_returned",
    }:
        return None
    if value["schema_version"] != WORKER_SCHEMA_VERSION:
        return None
    if (value["child"] is None) == (value["code"] is None):
        return None
    if value["child"] is not None and not isinstance(value["child"], dict):
        return None
    if value["code"] is not None and value["code"] not in {
        "diagnostic_wrapper_import_error",
        "diagnostic_execution_error",
        "diagnostic_result_invalid",
        "worker_internal_error",
    }:
        return None
    if (
        value["raw_output_returned"] is not False
        or value["exception_message_type_repr_or_traceback_returned"] is not False
        or value["credential_value_hash_prefix_or_length_returned"] is not False
    ):
        return None
    activity = value["activity"]
    if not isinstance(activity, dict) or set(activity) != {
        "diagnostic_invocation_count",
        "typed_validation_count",
        "raw_workload_output_return_count",
        "exception_message_type_repr_or_traceback_return_count",
        "credential_value_return_hash_prefix_or_length_count",
        "activity_accounting_complete",
        "unknown_workload_activity_possible",
    }:
        return None
    if activity["raw_workload_output_return_count"] != 0:
        return None
    if activity["exception_message_type_repr_or_traceback_return_count"] != 0:
        return None
    if activity["credential_value_return_hash_prefix_or_length_count"] != 0:
        return None
    if activity["activity_accounting_complete"] == activity["unknown_workload_activity_possible"]:
        return None
    if activity["diagnostic_invocation_count"] not in {0, 1}:
        return None
    if activity["typed_validation_count"] not in {0, 1}:
        return None
    if activity["typed_validation_count"] > activity["diagnostic_invocation_count"]:
        return None
    return value


def build_supervised_envelope(
    repository: str | Path,
    *,
    worker_runner: Callable[[Path], WorkerProcessOutcome] | None = None,
) -> dict[str, Any]:
    """Run the isolated worker and sanitize its result into one outer envelope."""

    try:
        root = Path(repository).resolve(strict=True)
    except BaseException:
        return _supervisor_envelope(
            child=None,
            code="supervisor_binding_error",
            activity=_supervisor_activity(
                launch_attempts=0,
                process_returns=0,
                result_messages=0,
                diagnostic_invocations=0,
                typed_validations=0,
                complete=True,
            ),
        )
    try:
        outcome = (worker_runner or (lambda value: run_worker_process(value)))(root)
    except BaseException:
        outcome = WorkerProcessOutcome(1, 0, b"", True, None, False, True)
    if outcome.process_return_count != 1 or outcome.returncode is None:
        return _process_error("worker_launch_error", outcome)
    if outcome.returncode != 0:
        return _process_error("worker_nonzero_exit", outcome)
    if not outcome.result_within_limit:
        return _process_error("worker_result_limit", outcome)
    if not outcome.complete or outcome.unknown:
        return _process_error("worker_result_invalid", outcome)
    message = _parse_worker_message(outcome.result_bytes)
    if message is None:
        return _process_error("worker_result_invalid", outcome)
    worker_activity = message["activity"]
    return _supervisor_envelope(
        child=message["child"],
        code=message["code"],
        activity=_supervisor_activity(
            launch_attempts=outcome.launch_attempt_count,
            process_returns=outcome.process_return_count,
            result_messages=1,
            diagnostic_invocations=worker_activity["diagnostic_invocation_count"],
            typed_validations=worker_activity["typed_validation_count"],
            complete=(
                outcome.complete and worker_activity["activity_accounting_complete"]
            ),
        ),
    )


def emit_supervised_envelope(
    repository: str | Path,
    *,
    worker_runner: Callable[[Path], WorkerProcessOutcome] | None = None,
) -> None:
    """Emit one canonical outer envelope; no workload runs in this process."""

    try:
        envelope = build_supervised_envelope(repository, worker_runner=worker_runner)
        raw = _canonical(envelope)
    except BaseException:
        raw = _canonical(
            _supervisor_envelope(
                child=None,
                code="supervisor_internal_error",
                activity=_supervisor_activity(
                    launch_attempts=0,
                    process_returns=0,
                    result_messages=0,
                    diagnostic_invocations=0,
                    typed_validations=0,
                    complete=False,
                ),
            )
        )
    os.write(1, raw)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    channel = parser.add_mutually_exclusive_group()
    channel.add_argument("--worker-result-handle", type=int)
    channel.add_argument("--worker-result-fd", type=int)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    worker_mode = args.worker_result_handle is not None or args.worker_result_fd is not None
    if worker_mode:
        emit_worker_message(
            args.repository,
            raw_handle=args.worker_result_handle,
            descriptor=args.worker_result_fd,
        )
    else:
        emit_supervised_envelope(args.repository)


if __name__ == "__main__":
    main()
