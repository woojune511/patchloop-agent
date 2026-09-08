"""Bounded observations from public check output, never inferred task verdicts."""

from __future__ import annotations

import re
from typing import Any

_EXCEPTION = re.compile(
    r"(?P<type>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)(?::.*)?"
)
_FRAME = re.compile(r'  File "[^"\r\n]+", line [1-9]\d*(?:, in .*)?')
_PYTEST_SUMMARY = re.compile(r"(?:FAILED|ERROR) \S+(?: - (?P<message>.*))?")
_PYTEST_EXCEPTION = re.compile(r"E[ \t]+(?P<message>.+)")
_MAX_DIAGNOSTIC_LINES = 8
_MAX_DIAGNOSTIC_CHARS = 4_000


def output_tail(text: str, limit: int) -> tuple[str, bool]:
    """Retain a suffix of complete observed LF/CRLF lines within a character cap.

    An unterminated line at observed EOF is intact unless the cap cuts into it.
    In that case omit it, rather than publishing its suffix as a different line.
    """
    if len(text) <= limit:
        return text, False
    start = len(text) - limit
    if text[start - 1] != "\n":
        boundary = text.find("\n", start)
        start = len(text) if boundary < 0 else boundary + 1
    return text[start:], True


def _exception_name(message: str) -> str | None:
    match = _EXCEPTION.fullmatch(message)
    if match is None or len(match["type"]) > 200:
        return None
    return match["type"]


def _pytest_exception_name(message: str) -> str | None:
    name = _exception_name(message)
    if name is None:
        return None
    # Pytest can also report source comparisons and generic failure messages.
    if (":" in message and name.rsplit(".", 1)[-1][0].isupper()
            or name.endswith(("Error", "Exception"))
            or name in {"KeyboardInterrupt", "SystemExit", "StopIteration",
                        "StopAsyncIteration", "GeneratorExit"}):
        return name
    return None


def _traceback_terminal(stream: str) -> tuple[str, str | None] | None:
    has_frame = False
    terminal = None
    for line in stream.splitlines():
        if _FRAME.fullmatch(line):
            # Also covers SyntaxError's frame without a Traceback header.
            has_frame = True
        elif line and not line[0].isspace():
            if has_frame and _EXCEPTION.fullmatch(line):
                terminal = line, _exception_name(line)
            has_frame = False
    return terminal


def check_failure_diagnostics(stdout: str, stderr: str) -> tuple[str | None, dict[str, Any]]:
    """Prefer final pytest summaries over intermediate exceptions in chained traces.

    Preserve literal public diagnostics, including test IDs and comparison text.
    Unknown/heterogeneous terminal types stay null; no expected/actual direction,
    causal explanation, or PASS/FAIL is inferred from these strings.
    """
    lines = [*stderr.splitlines(), *stdout.splitlines()]
    records = [
        (line, _pytest_exception_name(match["message"] or ""))
        for line in lines if (match := _PYTEST_SUMMARY.fullmatch(line)) is not None
    ]
    if not records:
        for line in lines:
            match = _PYTEST_EXCEPTION.fullmatch(line)
            if match is None:
                continue
            name = _pytest_exception_name(match["message"])
            if name is None:
                continue
            records.append((line, name))
    if not records:
        terminal = _traceback_terminal(stderr) or _traceback_terminal(stdout)
        if terminal is not None:
            records = [terminal]

    records = list(dict.fromkeys(records))
    names = {name for _, name in records}
    exception_type = next(iter(names)) if len(names) == 1 else None
    retained: list[str] = []
    remaining = _MAX_DIAGNOSTIC_CHARS
    for line, _ in records:
        if len(retained) < _MAX_DIAGNOSTIC_LINES and len(line) <= remaining:
            retained.append(line)
            remaining -= len(line)
    return exception_type, {
        "lines": retained,
        "observed_count": len(records),
        "truncated": len(retained) < len(records),
    }
