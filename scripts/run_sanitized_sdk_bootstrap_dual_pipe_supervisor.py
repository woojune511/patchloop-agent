"""Stdlib-only parent-result shim for the v19 dual-pipe successor.

The process starts with stdout and stderr owned by its parent as null devices.
It delegates the unchanged v17 supervisor/worker logic, then writes exactly one
sanitized v17 envelope to a separately inherited anonymous result channel.
Importing this module performs no observation or launch.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "sanitized-sdk-bootstrap-supervised-frame-envelope-v1"


def _canonical(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _fixed_error_envelope() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "child": None,
        "code": "supervisor_internal_error",
        "activity": {
            "worker_launch_attempt_count": 0,
            "worker_process_return_count": 0,
            "worker_result_message_count": 0,
            "diagnostic_invocation_count": 0,
            "typed_validation_count": 0,
            "worker_stdout_suppressed_from_process_start_count": 0,
            "worker_stderr_suppressed_from_process_start_count": 0,
            "raw_workload_output_return_count": 0,
            "exception_message_type_repr_or_traceback_return_count": 0,
            "credential_value_return_hash_prefix_or_length_count": 0,
            "activity_accounting_complete": False,
            "unknown_workload_activity_possible": True,
        },
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def build_pipe_envelope(
    repository: str | Path,
    *,
    supervisor_builder: Callable[[Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one v17 envelope; injected builders are offline-test only."""

    try:
        root = Path(repository).resolve(strict=True)
    except BaseException:
        return _fixed_error_envelope()
    if supervisor_builder is None:
        try:
            sys.path.insert(0, str(root))
            from scripts import run_sanitized_sdk_bootstrap_supervised_frame_child as v17
        except BaseException:
            return _fixed_error_envelope()
        builder = v17.build_supervised_envelope
    else:
        builder = supervisor_builder
    try:
        value = builder(root)
        if not isinstance(value, dict):
            return _fixed_error_envelope()
        return value
    except BaseException:
        return _fixed_error_envelope()


def _open_parent_result_descriptor(*, raw_handle: int | None, descriptor: int | None) -> int:
    if os.name == "nt":
        if raw_handle is None or descriptor is not None:
            raise RuntimeError("parent result handle binding differs")
        import msvcrt

        return msvcrt.open_osfhandle(raw_handle, os.O_WRONLY | os.O_BINARY)
    if descriptor is None or raw_handle is not None:
        raise RuntimeError("parent result descriptor binding differs")
    return descriptor


def emit_pipe_envelope(
    repository: str | Path,
    *,
    raw_handle: int | None,
    descriptor: int | None,
    supervisor_builder: Callable[[Path], dict[str, Any]] | None = None,
) -> None:
    """Write one canonical envelope only to the inherited parent channel."""

    result_descriptor = _open_parent_result_descriptor(
        raw_handle=raw_handle,
        descriptor=descriptor,
    )
    try:
        try:
            raw = _canonical(
                build_pipe_envelope(
                    repository,
                    supervisor_builder=supervisor_builder,
                )
            )
        except BaseException:
            raw = _canonical(_fixed_error_envelope())
        os.write(result_descriptor, raw)
    finally:
        os.close(result_descriptor)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    channel = parser.add_mutually_exclusive_group(required=True)
    channel.add_argument("--parent-result-handle", type=int)
    channel.add_argument("--parent-result-fd", type=int)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    emit_pipe_envelope(
        args.repository,
        raw_handle=args.parent_result_handle,
        descriptor=args.parent_result_fd,
    )


if __name__ == "__main__":
    main()
