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
_PYTHON_SWITCHES = {"-B", "-E", "-I", "-O", "-OO", "-s", "-S", "-u"}
_SELECTION_FILTERS = {
    "-k", "-m", "--deselect", "--ignore", "--ignore-glob", "--lf", "--last-failed",
    "--stepwise", "--sw", "--stepwise-skip", "--sw-skip", "--collect-only", "--co",
}


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
    return _pytest_positions(command, index)


def _pytest_positions(command: list[str], index: int) -> tuple[str, list[int]]:
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


def _inline_prefix(command: list[str]) -> list[str] | None:
    """Find only the Python invocation boundary, without interpreting its program."""
    if not command or not _PYTHON.fullmatch(command[0].replace("\\", "/").rsplit("/", 1)[-1]):
        return None
    index = 1
    while index < len(command) and command[index] in _PYTHON_SWITCHES:
        index += 1
    if command[index:index + 1] == ["-c"] and index + 1 < len(command):
        return command[:index + 2]
    return None


def _registered_selection(
    check: dict[str, Any], suites: list[dict[str, Any]],
) -> tuple[str, list[int]]:
    command = check.get("command", [])
    kind, positions = _selection(command)
    prefix = _inline_prefix(command)
    if prefix is not None and any(
        suite.get("runner") == "pytest"
        and suite.get("working_directory", ".") == check.get("working_directory", ".")
        and _inline_prefix(suite.get("command", [])) == prefix
        for suite in suites
    ):
        # Registration establishes the pytest argument contract. In particular,
        # suite-only options need not occur in a required check using this wrapper.
        kind, positions = _pytest_positions(command, len(prefix))
        if kind == "pytest_literals":
            kind = "registered_pytest_arguments"
    return kind, positions


def _target(argument: str, directory: str) -> tuple[str, str | None, str] | None:
    if len(argument) > MAX_TARGET_CHARS:
        return None
    raw_path, separator, node = argument.partition("::")
    raw_path = raw_path.replace("\\", "/")
    path = PurePosixPath(directory) / raw_path
    if (not raw_path or path.is_absolute() or ".." in path.parts
            or any(ord(char) < 32 for char in argument)
            or any(char in str(path) for char in ":*?[]${}")):
        return None
    # The registered working directory is already a validated relative path.
    if len(str(path)) > MAX_TARGET_CHARS:
        return None
    kind = "file" if raw_path.endswith(".py") else "discovery"
    if separator and kind != "file":
        return None
    return str(path), node if separator else None, kind


def _selection_filters(command: list[str]) -> list[str]:
    """Report literal pytest filters, without interpreting Python or configuration."""
    prefix = _inline_prefix(command)
    index = len(prefix) if prefix else (3 if command[1:3] == ["-m", "pytest"] else 1)
    filters = set()
    while index < len(command):
        argument = command[index]
        if argument == "--":
            break
        option = argument.partition("=")[0]
        if option in _SELECTION_FILTERS:
            filters.add(option)
        index += 2 if argument in _VALUE_OPTIONS else 1
    return sorted(filters)


def _changed_test_review(
    view: dict[str, Any], definitions: dict[str, tuple[str, dict[str, Any]]],
    suites: list[dict[str, Any]],
) -> None:
    """Describe visible selection receipts, never infer collection or execution coverage."""
    diff = view.get("current_diff", {})
    current_hash = diff.get("patch_hash")
    if not current_hash:
        return
    review: dict[str, Any] = {
        "files": [], "omitted_file_count": 0,
        "basis": (
            "Visible current-diff receipts only; missing does not mean never executed. "
            "File/node selection and command PASS do not prove collected test cases. "
            "Explicit file execution does not establish future directory discovery. "
            "Reuse matching input/assertion/scope evidence. Missing collection telemetry alone "
            "does not require rerunning. Optional selectors address a concrete scope gap, "
            "filter, or suspected discovery omission; they are not next-action recommendations."
        ),
    }
    for path in dict.fromkeys(diff.get("changed_files", [])):
        target = _target(path, ".")
        if target is None or target[2] != "file":
            continue
        path = target[0]
        if any(part.startswith((".", "-")) for part in PurePosixPath(path).parts):
            continue  # These cannot be selected by the registered run_tests contract.
        matching = [suite for suite in suites if suite.get("runner") == "pytest"
                    and PurePosixPath(path).is_relative_to(suite.get("working_directory", "."))
                    and any(PurePosixPath(path).is_relative_to(root)
                            for root in suite.get("test_roots", []))]
        if not matching:
            continue
        if len(review["files"]) == MAX_TARGETS:
            review["omitted_file_count"] += 1
            continue
        receipts = []
        for tool, key in (("run_check", "recent_checks"), ("run_tests", "recent_tests")):
            for row in view.get(key, []):
                if (row.get("diff_hash") != current_hash
                        or row.get("evidence_currency", "current") != "current"):
                    continue
                if tool == "run_check":
                    definition = definitions.get(row.get("check_id"))
                    if definition is None:
                        continue
                    check = definition[1]
                    command_kind, positions = _registered_selection(check, suites)
                    command = check.get("command", [])
                    targets = [_target(check["command"][i], check.get("working_directory", "."))
                               for i in positions]
                else:
                    suite = next((item for item in suites
                                  if item.get("id") == row.get("suite_id")), {})
                    command = suite.get("command", [])
                    command_kind, _ = _registered_selection(suite, suites)
                    targets = [_target(item, ".") for item in row.get("targets", [])]
                filters = _selection_filters(command)
                for selected in targets:
                    if selected is None:
                        continue
                    selected_path, node, kind = selected
                    if selected_path == path and kind == "file":
                        selection = "partial_nodes" if node is not None else "explicit_file"
                    elif kind == "discovery" and PurePosixPath(path).is_relative_to(selected_path):
                        selection = "directory_selected"
                    else:
                        continue
                    receipts.append({
                        "action_id": row.get("action_id"), "tool": tool, "selection": selection,
                        "node_selector": node, "command_passed": row.get("passed"),
                        **({"command_filters": filters} if filters else {}),
                        **({"command_scope": "unresolved"} if command_kind == "unresolved" else {}),
                        **({"test_status": row["test_status"]} if "test_status" in row else {}),
                    })
        status = next((kind for kind in ("explicit_file", "partial_nodes", "directory_selected")
                       if any(r["selection"] == kind for r in receipts)), "not_confirmed")
        passing_file = any(
            row["selection"] == "explicit_file" and row["command_passed"] is True
            and row.get("test_status", "PASS") == "PASS"
            and not row.get("command_filters") and row.get("command_scope") != "unresolved"
            for row in receipts
        ) and all(row["command_passed"] is True for row in receipts)
        review["files"].append({
            "path": path, "selection_status": status, "collection_status": "not_reported",
            **({"optional_run_tests_selection": {"suite_id": matching[0]["id"], "targets": [path]}}
               if not passing_file else {}),
            "visible_receipts": receipts[-MAX_RANGES:],
            "omitted_receipt_count": max(0, len(receipts) - MAX_RANGES),
        })
    while len(canonical_json(review)) > MAX_REVIEW_CHARS and review["files"]:
        review["files"].pop()
        review["omitted_file_count"] += 1
    if review["files"] or review["omitted_file_count"]:
        diff["test_execution_review"] = review


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
    suites = view.get("public_task", {}).get("test_suites", [])
    definitions = {check["id"]: (f"public_task.visible_checks[{index}]", check)
                   for index, check in enumerate(checks)}
    for index, descriptor in enumerate(view.get("supplemental_required_checks", [])):
        check = descriptor.get("check")
        if isinstance(check, dict) and check.get("id") not in definitions:
            definitions[check["id"]] = (f"supplemental_required_checks[{index}].check", check)
    for row in view.get("recent_checks", []):
        definition = definitions.get(row.get("check_id"))
        if definition is None:
            continue  # Legacy/minimal contexts cannot gain a guessed definition.
        reference, check = definition
        command = check.get("command", [])
        kind, positions = _registered_selection(check, suites)
        review: dict[str, Any] = {
            "definition_ref": reference,
            "command_hash": sha256_json(command), "selection_kind": kind,
            "declared_targets": [], "omitted_target_count": 0,
            "coverage_status": "not_assessed",
            "requirement_verification": "not_assessed",
            "interpretation": (
                "This receipt establishes only the registered execution result. Requirement "
                "coverage needs a matching executed input/assertion or observed output; "
                "PASS alone, test source/additions and mutation expectations do not establish it. "
                "Unmeasured coverage is unknown, not evidence of execution or non-execution."
            ),
        }
        for position in positions:
            target = _target(command[position], check.get("working_directory", "."))
            if target is None or len(review["declared_targets"]) == MAX_TARGETS:
                review["omitted_target_count"] += 1
                continue
            path, node, target_kind = target
            review["declared_targets"].append({
                "command_argument_index": position, "path": path, "node_selector": node,
                "selection": target_kind,
                "current_source_view": _source_ranges(path, view.get("source_spans", [])),
            })
        while len(canonical_json(review)) > MAX_REVIEW_CHARS and review["declared_targets"]:
            review["declared_targets"].pop()
            review["omitted_target_count"] += 1
        row["evidence_review"] = review
    _changed_test_review(view, definitions, suites)
