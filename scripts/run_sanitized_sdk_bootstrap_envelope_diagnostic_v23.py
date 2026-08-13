"""Lifecycle-internal live adapter for the qualified v22 typed channel.

The module has no observation at import time.  Its worker and supervisor roles
require an inherited result descriptor and are launched only by the v23
activation runtime after ``ACTION_STARTED``.  Invalid bytes and exception
details are discarded rather than returned or persisted.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
import threading
from collections.abc import Callable
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


def _root(repository: str | Path) -> Path:
    return Path(repository).resolve(strict=True)


def _load_channel(root: Path) -> Any:
    selected = str(root)
    if selected not in sys.path:
        sys.path.insert(0, selected)
    from scripts import run_sanitized_sdk_bootstrap_envelope_diagnostic_v22 as channel

    return channel


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
    channel: Any,
    *,
    raw_handle: int | None,
    descriptor: int | None,
) -> int:
    return channel._open_result_descriptor(
        raw_handle=raw_handle,
        descriptor=descriptor,
    )


def emit_live_worker(
    repository: str | Path,
    *,
    raw_handle: int | None,
    descriptor: int | None,
) -> None:
    root = _root(repository)
    channel = _load_channel(root)
    selected = _open_result_descriptor(
        channel,
        raw_handle=raw_handle,
        descriptor=descriptor,
    )
    try:
        try:
            from scripts.run_sanitized_sdk_diagnostic_child import _run

            observed = _run(root)
            value = channel.project_worker_envelope(
                root,
                mode=channel.Mode.LIVE,
                observed_child=observed,
            )
        except BaseException:
            value = channel.project_worker_envelope(
                root,
                mode=channel.Mode.LIVE,
                observed_error=channel.WorkerCode.DIAGNOSTIC_EXECUTION_ERROR,
            )
        channel.emit_frame(selected, value)
    finally:
        os.close(selected)


def _failed_worker_outcome(
    channel: Any,
    stage: Any,
    *,
    returned: int = 0,
    returncode: int | None = None,
) -> Any:
    return channel.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=returned,
        returncode=returncode,
        frame=channel.FrameDecodeResult(stage),
        activity_accounting_complete=False,
        unknown_process_activity_possible=True,
    )


def run_live_worker_process(
    repository: str | Path,
    *,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> Any:
    root = _root(repository)
    channel = _load_channel(root)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = channel._BoundedFrameReader(read_descriptor)
    thread = threading.Thread(target=reader.consume, daemon=True)
    argv, kwargs = _launch_kwargs(root, write_descriptor, role="worker")
    try:
        process = popen(argv, **kwargs)
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(write_descriptor)
        with contextlib.suppress(OSError):
            os.close(read_descriptor)
        return _failed_worker_outcome(channel, channel.FrameStage.NOT_EVALUATED)
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
            channel,
            channel.FrameStage.READ_ERROR,
            returned=int(returncode is not None),
            returncode=returncode,
        )
    decoded = reader.decode_and_discard(mode=channel.Mode.LIVE)
    if returncode != 0:
        return _failed_worker_outcome(
            channel,
            channel.FrameStage.NOT_EVALUATED,
            returned=int(returncode is not None),
            returncode=returncode,
        )
    complete = decoded.stage == channel.FrameStage.VALID
    return channel.WorkerProcessOutcome(
        launch_attempt_count=1,
        process_return_count=1,
        returncode=0,
        frame=decoded,
        activity_accounting_complete=complete,
        unknown_process_activity_possible=not complete,
    )


def emit_live_supervisor(
    repository: str | Path,
    *,
    raw_handle: int | None,
    descriptor: int | None,
) -> None:
    root = _root(repository)
    channel = _load_channel(root)
    selected = _open_result_descriptor(
        channel,
        raw_handle=raw_handle,
        descriptor=descriptor,
    )
    try:
        outcome = run_live_worker_process(root)
        value = channel.build_supervisor_envelope(
            root,
            mode=channel.Mode.LIVE,
            observed_outcome=outcome,
        )
        channel.emit_frame(selected, value)
    finally:
        os.close(selected)


def run_live_supervisor_process(
    repository: str | Path,
    *,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> dict[str, Any]:
    """Launch one supervisor and return only a sanitized typed projection."""

    root = _root(repository)
    channel = _load_channel(root)
    read_descriptor, write_descriptor = os.pipe()
    os.set_inheritable(write_descriptor, True)
    reader = channel._BoundedFrameReader(read_descriptor)
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
            "frame_stage": channel.FrameStage.NOT_EVALUATED.value,
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
            "frame_stage": channel.FrameStage.READ_ERROR.value,
            "envelope": None,
            "activity_accounting_complete": False,
            "unknown_process_activity_possible": True,
        }
    decoded = reader.decode_and_discard(mode=channel.Mode.LIVE, supervisor=True)
    valid = decoded.stage == channel.FrameStage.VALID and decoded.value is not None
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
