"""Value-free framed child for the v13 no-call preflight successor.

The diagnostic workload runs while process stdout/stderr point at the OS null
device.  Only one canonical JSON envelope is written after both descriptors
are restored.  Exceptions and rejected payloads are represented by fixed
codes; raw output, exception text and credential material are never returned.
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


def _under_null_streams(action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Run ``action`` with fd 1/2 redirected, restoring both before return."""

    sys.stdout.flush()
    sys.stderr.flush()
    saved_stdout = os.dup(1)
    saved_stderr = os.dup(2)
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
                try:
                    return action()
                finally:
                    sys.stdout.flush()
                    sys.stderr.flush()
    finally:
        os.dup2(saved_stdout, 1)
        os.dup2(saved_stderr, 2)
        os.close(saved_stdout)
        os.close(saved_stderr)


def build_framed_envelope(
    repository: str | Path,
    *,
    diagnostic_runner: Callable[[Path], dict[str, Any]] | None = None,
    typed_validator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one sanitized envelope; injected callables are for offline tests."""

    def work() -> dict[str, Any]:
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

    try:
        return _under_null_streams(work)
    except BaseException:
        return _error(
            "framed_child_internal_error",
            diagnostic_invocation_count=0,
            typed_validation_count=0,
            complete=False,
            unknown=True,
        )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    envelope = build_framed_envelope(args.repository)
    raw = (
        json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    os.write(1, raw)


if __name__ == "__main__":
    main()
