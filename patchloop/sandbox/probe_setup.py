"""Bounded scalar setup comparisons, copied into the public probe's trusted mount.

The probe chooses the values and can interfere with this in-process helper. These
observations are not attestations, coverage, or judgments about candidate behavior.
This file must remain stdlib-only so the standalone probe runner can load it.
"""

from __future__ import annotations

import json
import math
import os
import runpy
import threading
from contextlib import suppress
from functools import wraps
from pathlib import Path

# Load the exact adjacent trusted copy before candidate imports become available.
_API = runpy.run_path(str(Path(__file__).with_name("probe_api.py")))

MAX_CHECKS = _API["MAX_SETUP_CHECKS"]
MAX_LABEL_CHARS = _API["MAX_SETUP_LABEL_CHARS"]
MAX_VALUE_CHARS = _API["MAX_SETUP_VALUE_CHARS"]
MAX_REPORT_BYTES = 8_000
ERRORS = {"invalid_label", "unsupported_value", "check_limit", "report_limit", "api_usage"}


def marker(request: dict) -> bytes:
    return b"\x1ePATCHLOOP-SETUP:" + request["request_hash"].encode("ascii") + b":"


def _scalar(value: object) -> bool:
    # Never invoke arbitrary equality, repr, or JSON hooks on project objects.
    kind = type(value)
    return (value is None or kind is bool
            or (kind is str and len(value) <= MAX_VALUE_CHARS)
            or (kind is int and value.bit_length() <= _API["MAX_SETUP_INTEGER_BITS"])
            or (kind is float and math.isfinite(value)))


def _encode(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()


class SetupMismatchError(AssertionError):
    """A supplied actual setup value differs from the supplied expectation."""


class SetupChecks:
    def __init__(self, request: dict) -> None:
        self.request = request
        self.checks: list[dict] = []
        self.error: str | None = None
        self.api_error: dict | None = None
        self.lock = threading.Lock()
        self.write = os.write

        @wraps(self.check)
        def invoke(*args, **kwargs):
            try:
                values = _API["bind_setup"](args, kwargs)
            except _API["HelperAPIError"] as error:
                with self.lock:
                    self.api_error = dict(error.details)
                    self.error = "api_usage"
                raise
            return self.check(**values)

        self.invoke = invoke

    validate_observer_settings = staticmethod(_API["validate_observer_settings"])

    def _report(self, checks: list[dict]) -> dict:
        report = {"request_hash": self.request["request_hash"],
                  "checks": checks, "error": self.error}
        if self.api_error is not None:
            report["api_error"] = self.api_error
            if len(_encode(report)) > MAX_REPORT_BYTES:
                report.update(checks=[], error="report_limit")
        return report

    def check(self, label: str, actual: object, expected: object) -> None:
        """Record type-strict scalar equality; raise on mismatch or invalid usage."""
        with self.lock:
            error = None
            if type(label) is not str or not 1 <= len(label) <= MAX_LABEL_CHARS:
                error = "invalid_label"
            elif not _scalar(actual) or not _scalar(expected):
                error = "unsupported_value"
            elif len(self.checks) >= MAX_CHECKS:
                error = "check_limit"
            else:
                row = {"label": label, "actual": actual, "expected": expected}
                # Reserve room for an error reported by a later invalid call.
                if len(_encode(self._report([*self.checks, row]))) > MAX_REPORT_BYTES - 64:
                    error = "report_limit"
            if error is not None:
                self.error = error
                raise ValueError("check_setup: " + error)
            self.checks.append(row)
            if type(actual) is not type(expected) or actual != expected:
                raise SetupMismatchError("check_setup mismatch: " + label)

    def finish(self) -> None:
        with self.lock, suppress(OSError):
            self.write(2, marker(self.request) + _encode(self._report(self.checks)) + b"\n")


def public_feedback(request: dict, report: object) -> dict:
    """Validate the frame; derive comparisons on the host, never accept its verdict."""
    feedback = {
        "schema_version": "probe-setup-checks-v1", "request_hash": request["request_hash"],
        "source_hash": request["source_hash"], "status": "unknown", "checks": [],
        "diagnostic_only": True, "selection": "model_authored",
        "interpretation": (
            "Only supplied scalar values are compared, with equal types required. A mismatch "
            "raises before the next statement unless the program catches it. It does not prove "
            "that candidate code was not executed. Passing comparisons do not establish complete "
            "setup, public applicability, behavior correctness or a counterexample. The "
            "in-process report can be interfered with; it is not an attestation."
        ),
    }
    fields = {"request_hash", "checks", "error"}
    if not isinstance(report, dict) or set(report) not in (fields, fields | {"api_error"}):
        return {**feedback, "reason": "missing_or_invalid_report"}
    checks, error = report["checks"], report["error"]
    if (report["request_hash"] != request["request_hash"] or not isinstance(checks, list)
            or len(checks) > MAX_CHECKS or (error is not None and
                                         (not isinstance(error, str) or error not in ERRORS))):
        return {**feedback, "reason": "missing_or_invalid_report"}
    if "api_error" in report and (
            not _API["valid_error"](report["api_error"])
            or report["api_error"]["api"] != "check_setup"
            or error not in {"api_usage", "report_limit"}):
        return {**feedback, "reason": "missing_or_invalid_report"}
    for row in checks:
        if (not isinstance(row, dict) or set(row) != {"label", "actual", "expected"}
                or type(row["label"]) is not str or not 1 <= len(row["label"]) <= MAX_LABEL_CHARS
                or not _scalar(row["actual"]) or not _scalar(row["expected"])):
            return {**feedback, "reason": "missing_or_invalid_report"}
    if len(_encode(report)) > MAX_REPORT_BYTES:
        return {**feedback, "reason": "missing_or_invalid_report"}
    if "api_error" in report:
        feedback["api_error"] = dict(report["api_error"])
    rows = [{**row, "matched": type(row["actual"]) is type(row["expected"])
             and row["actual"] == row["expected"]} for row in checks]
    if error is not None:
        return {**feedback, "checks": rows, "reason": error}
    return {**feedback, "checks": rows, "status": (
        "not_checked" if not rows else "passed" if all(row["matched"] for row in rows) else "failed"
    )}
