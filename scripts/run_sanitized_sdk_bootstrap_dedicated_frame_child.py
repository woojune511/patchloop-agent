"""Value-free child that emits one envelope through a dedicated descriptor.

The result descriptor is duplicated before the diagnostic workload receives
stdout/stderr.  Workload output is redirected to the OS null device, and the
canonical envelope is written directly to the saved descriptor without
restoring fd 1 or fd 2.  Importing this module performs no diagnostic work.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "sanitized-sdk-bootstrap-framed-child-envelope-v1"


def _activity(
    *,
    diagnostic_invocation_count: int,
    typed_validation_count: int,
    complete: bool,
    unknown: bool,
) -> dict[str, Any]:
    return {
        "diagnostic_invocation_count": diagnostic_invocation_count,
        "typed_validation_count": typed_validation_count,
        "suppressed_stdout_channel_count": 1,
        "suppressed_stderr_channel_count": 1,
        "raw_workload_output_return_count": 0,
        "exception_message_type_repr_or_traceback_return_count": 0,
        "credential_value_return_hash_prefix_or_length_count": 0,
        "activity_accounting_complete": complete,
        "unknown_workload_activity_possible": unknown,
    }


def _error(
    code: str,
    *,
    diagnostic_invocation_count: int,
    typed_validation_count: int,
    complete: bool,
    unknown: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "child": None,
        "code": code,
        "activity": _activity(
            diagnostic_invocation_count=diagnostic_invocation_count,
            typed_validation_count=typed_validation_count,
            complete=complete,
            unknown=unknown,
        ),
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def _success(child: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "child": child,
        "code": None,
        "activity": _activity(
            diagnostic_invocation_count=1,
            typed_validation_count=1,
            complete=True,
            unknown=False,
        ),
        "raw_output_returned": False,
        "exception_message_type_repr_or_traceback_returned": False,
        "credential_value_hash_prefix_or_length_returned": False,
    }


def build_envelope(
    repository: str | Path,
    *,
    diagnostic_runner: Callable[[Path], dict[str, Any]] | None = None,
    typed_validator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a sanitized envelope while the caller suppresses fd 1 and fd 2."""

    root = Path(repository).resolve(strict=True)
    if diagnostic_runner is None or typed_validator is None:
        try:
            sys.path.insert(0, str(root))
            from patchloop.evals.sanitized_sdk_parent_integration import (
                IsolatedDiagnosticChild,
            )
            from scripts.run_sanitized_sdk_diagnostic_child import _run
        except BaseException:
            return _error(
                "diagnostic_wrapper_import_error",
                diagnostic_invocation_count=0,
                typed_validation_count=0,
                complete=True,
                unknown=False,
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
        return _error(
            "diagnostic_execution_error",
            diagnostic_invocation_count=1,
            typed_validation_count=0,
            complete=False,
            unknown=True,
        )
    try:
        child = validate(raw_child)
    except BaseException:
        return _error(
            "diagnostic_result_invalid",
            diagnostic_invocation_count=1,
            typed_validation_count=1,
            complete=False,
            unknown=True,
        )
    return _success(child)


def _canonical(envelope: dict[str, Any]) -> bytes:
    return (
        json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def emit_dedicated_envelope(
    repository: str | Path,
    *,
    diagnostic_runner: Callable[[Path], dict[str, Any]] | None = None,
    typed_validator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> None:
    """Suppress workload streams and write one envelope to a pre-work duplicate."""

    result_descriptor = os.dup(1)
    raw: bytes
    try:
        with (
            open(os.devnull, "wb", buffering=0) as descriptor_sink,
            open(os.devnull, "w", encoding="utf-8") as stream_sink,
        ):
            os.dup2(descriptor_sink.fileno(), 1)
            os.dup2(descriptor_sink.fileno(), 2)
            with (
                contextlib.redirect_stdout(stream_sink),
                contextlib.redirect_stderr(stream_sink),
            ):
                envelope = build_envelope(
                    repository,
                    diagnostic_runner=diagnostic_runner,
                    typed_validator=typed_validator,
                )
                try:
                    raw = _canonical(envelope)
                except BaseException:
                    raw = _canonical(
                        _error(
                            "framed_child_internal_error",
                            diagnostic_invocation_count=0,
                            typed_validation_count=0,
                            complete=False,
                            unknown=True,
                        )
                    )
    except BaseException:
        raw = _canonical(
            _error(
                "framed_child_internal_error",
                diagnostic_invocation_count=0,
                typed_validation_count=0,
                complete=False,
                unknown=True,
            )
        )
    try:
        os.write(result_descriptor, raw)
    finally:
        os.close(result_descriptor)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    emit_dedicated_envelope(args.repository)


if __name__ == "__main__":
    main()
