"""Bounded selectors for registered public pytest suites, never shell commands."""
from __future__ import annotations

import stat
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Annotated, Any

from pydantic import Field

from patchloop.contracts import PublicTestSuite, RegisteredCheck, StrictModel
from patchloop.dev.check_feedback import output_tail
from patchloop.errors import ContractError
from patchloop.util import safe_relative_path, sha256_json

MAX_TARGETS = 8
MAX_TARGET_CHARS = 500


class SelectedTests(StrictModel):
    suite_id: str = Field(min_length=1)
    targets: list[Annotated[str, Field(min_length=1, max_length=MAX_TARGET_CHARS)]] = Field(
        min_length=1, max_length=MAX_TARGETS,
    )


def selected_check(
    suite: PublicTestSuite, selection: SelectedTests, workspace: Path,
    tracked_path: Callable[[str], tuple[str, Path]],
) -> tuple[RegisteredCheck, list[str]]:
    normalized_targets, arguments = [], []
    for target in selection.targets:
        if any(ord(char) < 32 or ord(char) == 127 for char in target):
            raise ContractError("test targets cannot contain control characters")
        path, separator, node = target.partition("::")
        relative = safe_relative_path(path, field_name="test target")
        parts = PurePosixPath(relative).parts
        if (not relative.endswith(".py") or any(
            part.startswith((".", "-")) or ":" in part for part in parts
        ) or (separator and (not node or any(not part for part in node.split("::"))))):
            raise ContractError("select a public Python test file or pytest node ID")
        if not any(PurePosixPath(relative).is_relative_to(root) for root in suite.test_roots):
            raise ContractError("test target is outside the registered test roots")
        # Reject links before resolving them: resolving first can hide a tracked
        # symlink to another file inside the same repository, including on Windows.
        current = workspace
        for part in parts:
            current /= part
            try:
                info = current.lstat()
            except OSError as exc:
                raise ContractError("test target does not exist") from exc
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ContractError("test targets cannot traverse symlinks or reparse points")
        normalized, _ = tracked_path(relative)
        try:
            argument = PurePosixPath(normalized).relative_to(suite.working_directory).as_posix()
        except ValueError as exc:
            raise ContractError("test target is outside the suite working directory") from exc
        suffix = separator + node
        normalized_targets.append(normalized + suffix)
        arguments.append(argument + suffix)
    if len(set(normalized_targets)) != len(normalized_targets):
        raise ContractError("test targets must be unique")
    identity = sha256_json({"suite_id": suite.id, "targets": normalized_targets})[7:31]
    check = RegisteredCheck.model_validate({
        **suite.model_dump(exclude={"runner", "test_roots"}),
        "id": f"selected-{identity}",
        "command": [*suite.command, "--", *arguments],
    })
    return check, normalized_targets


def recent_tests(events: list[dict[str, Any]], diff_hash: str) -> list[dict[str, Any]]:
    """Retain a small public result set across native/segmented context changes."""
    rows = []
    for event in events:
        if event["event_type"] != "action_finished":
            continue
        result = event["payload"]["result"]
        if result["tool"] != "run_tests" or result["status"] != "succeeded":
            continue
        output = result["output"]
        stdout, clipped_out = output_tail(output.get("stdout", ""), 4_000)
        stderr, clipped_err = output_tail(output.get("stderr", ""), 4_000)
        rows.append({
            "action_id": result["action_id"], "input_hash": result["input_hash"],
            **{key: output.get(key) for key in (
                "suite_id", "targets", "diff_hash", "passed", "test_status", "exit_code",
                "timed_out", "deadline_exhausted", "cleanup_failed",
            )},
            "evidence_currency": (
                "current" if output.get("diff_hash") == diff_hash else "historical"
            ),
            "counts_toward_completion": False,
            "stdout": stdout, "stderr": stderr,
            "truncated": bool(output.get("truncated")) or clipped_out or clipped_err,
        })
    return rows[-3:]
