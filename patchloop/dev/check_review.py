"""Link public check receipts to definitions and already delivered source.

These are navigation hints, not collected test cases or assertion coverage. This
projection never reads files, resolves dynamic test selection, or runs a check.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from patchloop.util import canonical_json, sha256_json

MAX_TARGETS = 4
MAX_RANGES = 3
MAX_TARGET_CHARS = 256
MAX_REVIEW_CHARS = 2_000
_PYTHON = re.compile(r"python(?:3(?:\.\d+)?)?(?:\.exe)?", re.IGNORECASE)
_VALUE_OPTIONS = {
    "-c", "-k", "-m", "-o", "-p", "--override-ini", "--rootdir", "--confcutdir",
    "--basetemp", "--import-mode", "--tb", "--capture", "--color", "--code-highlight",
    "--maxfail", "--durations", "--durations-min", "--junitxml", "--junit-xml",
}
_SWITCHES = {"-q", "-v", "-s", "-x", "--quiet", "--verbose", "--exitfirst",
             "--disable-warnings", "--disable-pytest-warnings", "--strict-markers",
             "--strict-config"}


def _selection(command: list[str]) -> tuple[str, list[int]]:
    """Recognize literal argv only; unknown option arity keeps the definition link."""
    if not command:
        return "unresolved", []
    executable = command[0].replace("\\", "/").rsplit("/", 1)[-1]
    if _PYTHON.fullmatch(executable) and command[1:2] == ["-c"]:
        return "inline_python", []
    if executable in {"pytest", "pytest.exe"}:
        index = 1
    elif _PYTHON.fullmatch(executable) and command[1:3] == ["-m", "pytest"]:
        index = 3
    else:
        return "unresolved", []
    positional: list[int] = []
    while index < len(command):
        arg = command[index]
        if arg == "--":
            return "pytest_literals", [*positional, *range(index + 1, len(command))]
        if arg in _VALUE_OPTIONS:
            if index + 1 == len(command):
                return "unresolved", []
            index += 2
            continue
        if arg.startswith("-") and arg not in _SWITCHES:
            # An unknown flag may consume the next apparent path. Do not guess.
            if not (arg.startswith("--") and "=" in arg):
                return "unresolved", []
        elif not arg.startswith("-"):
            positional.append(index)
        index += 1
    return "pytest_literals", positional


def _target(argument: str, directory: str) -> tuple[str, str | None] | None:
    if len(argument) > MAX_TARGET_CHARS:
        return None
    raw_path, separator, node = argument.partition("::")
    raw_path = raw_path.replace("\\", "/")
    path = PurePosixPath(directory) / raw_path
    if (path.is_absolute() or ".." in path.parts or not raw_path.endswith(".py")
            or any(char in str(path) for char in ":*?[]${}")):
        return None
    # The registered working directory is already a validated relative path.
    if len(str(path)) > MAX_TARGET_CHARS:
        return None
    return str(path), node if separator else None


def _source_ranges(path: str, spans: list[dict[str, Any]]) -> dict[str, Any]:
    ranges: list[dict[str, Any]] = []
    coordinates = sorted({(span["file_hash"], span["start_line"], span["end_line"])
                          for span in spans if span["path"] == path})
    for file_hash, start, end in coordinates:
        if (ranges and ranges[-1]["file_hash"] == file_hash
                and start <= ranges[-1]["end_line"] + 1):
            ranges[-1]["end_line"] = max(ranges[-1]["end_line"], end)
        else:
            ranges.append({"file_hash": file_hash, "start_line": start, "end_line": end})
    return {"ranges": ranges[:MAX_RANGES], "omitted_range_count": max(0, len(ranges) - MAX_RANGES)}


def link_check_evidence(view: dict[str, Any]) -> None:
    """Enrich the existing bounded check rows; original receipts and gates stay exact."""
    checks = view.get("public_task", {}).get("visible_checks", [])
    definitions = {check["id"]: (index, check) for index, check in enumerate(checks)}
    for row in view.get("recent_checks", []):
        definition = definitions.get(row.get("check_id"))
        if definition is None:
            continue  # Legacy/minimal contexts cannot gain a guessed definition.
        index, check = definition
        command = check.get("command", [])
        kind, positions = _selection(command)
        review: dict[str, Any] = {
            "definition_ref": f"public_task.visible_checks[{index}]",
            "command_hash": sha256_json(command), "selection_kind": kind,
            "declared_targets": [], "omitted_target_count": 0,
            "coverage_status": "not_assessed",
        }
        for position in positions:
            target = _target(command[position], check.get("working_directory", "."))
            if target is None or len(review["declared_targets"]) == MAX_TARGETS:
                review["omitted_target_count"] += 1
                continue
            path, node = target
            review["declared_targets"].append({
                "command_argument_index": position, "path": path, "node_selector": node,
                "current_source_view": _source_ranges(path, view.get("source_spans", [])),
            })
        while len(canonical_json(review)) > MAX_REVIEW_CHARS and review["declared_targets"]:
            review["declared_targets"].pop()
            review["omitted_target_count"] += 1
        row["evidence_review"] = review
