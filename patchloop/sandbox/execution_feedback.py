"""Bounded public changed-line feedback, separate from source admission and PASS."""

from __future__ import annotations

import json
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from patchloop.errors import ContractError
from patchloop.sandbox.line_trace import marker
from patchloop.util import canonical_json, sha256_json

TRACE_WRAPPER = Path(__file__).with_name("line_trace.py")
MAX_FILES = 8
MAX_LINES = 256
MAX_REPORT_BYTES = 16_000
MAX_FEEDBACK_BYTES = 12_000
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_REASONS = {"source_hash_mismatch", "source_unavailable_or_uncompilable", "trace_or_source_changed"}
INTERPRETATION = (
    "Python line entry in the launch thread only; not branch coverage, assertion coverage, "
    "semantic correctness or source-read evidence. Other threads/subprocesses are unmeasured. "
    "Use relevant unobserved ranges for an optional public question in existing notes/probes; "
    "this adds no required action or submission gate."
)


def changed_lines(patch: str) -> dict[str, set[int]]:
    """Only added/replacement post-image lines; deleted lines have no current coordinate."""
    paths: dict[str, set[int]] = {}
    path = None
    line_number = None
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            path = None
            line_number = None
        elif line.startswith("+++ b/") and line_number is None:
            path = line[6:]
            paths.setdefault(path, set())
        elif match := _HUNK.match(line):
            line_number = int(match[1])
        elif path is not None and line_number is not None:
            if line.startswith("+"):
                paths[path].add(line_number)
                line_number += 1
            elif line.startswith(" "):
                line_number += 1
    return paths


def make_request(
    diff_hash: str, files: list[dict[str, Any]], *,
    execution_identity: dict[str, str] | None, omitted_file_count: int, deleted_line_count: int,
) -> dict[str, Any]:
    request = {
        "schema_version": "public-changed-line-request-v1", "diff_hash": diff_hash,
        "execution_identity_hash": sha256_json(execution_identity), "files": files,
        "omitted_file_count": omitted_file_count, "deleted_line_count": deleted_line_count,
    }
    return {**request, "request_hash": sha256_json(request)}


def ranges(lines) -> list[list[int]]:
    result = []
    for line in sorted(set(lines)):
        if result and line == result[-1][1] + 1:
            result[-1][1] = line
        else:
            result.append([line, line])
    return result


def summarize_execution(records: list[dict], diff_hash: str, current_hashes: dict) -> dict:
    """Union only measured current-byte/current-diff evidence; no historical PASS promotion."""
    files: dict[str, dict] = {}
    action_ids = []

    def expand(value):
        return {line for start, end in value for line in range(start, end + 1)}

    for record in records:
        feedback = record["feedback"]
        if feedback["diff_hash"] != diff_hash:
            continue
        action_ids.append(record["action_id"])
        for file in feedback["files"]:
            if current_hashes.get(file["path"]) != file["file_hash"]:
                continue
            row = files.setdefault(file["path"], {
                "path": file["path"], "file_hash": file["file_hash"],
                "executed": set(), "executable": set(), "measured": False,
            })
            if file["status"] == "collected":
                row["measured"] = True
                row["executed"].update(expand(file["executed_changed_ranges"]))
                row["executable"].update(expand(file["not_observed_changed_ranges"]))
                row["executable"].update(row["executed"])
    return {
        "diff_hash": diff_hash, "diagnostic_only": True, "scope": "python_launch_thread",
        "interpretation": INTERPRETATION,
        "observation_count": len(action_ids), "recent_action_ids": action_ids[-8:],
        "files": [{
            "path": row["path"], "file_hash": row["file_hash"],
            "status": "collected" if row["measured"] else "unknown",
            "executed_changed_ranges": ranges(row["executed"]),
            "not_observed_changed_ranges": (
                ranges(row["executable"] - row["executed"]) if row["measured"] else None
            ),
        } for row in files.values()],
    }


def public_feedback(request: dict, report: object = None, *, reason="report_unavailable") -> dict:
    """Rebuild from host-bound identities; never echo arbitrary reported paths/prose."""
    rows = None
    if (isinstance(report, dict) and report.get("request_hash") == request["request_hash"]
            and isinstance(report.get("files"), list)
            and len(report["files"]) == len(request["files"])):
        rows = report["files"]
    files = []
    for index, target in enumerate(request["files"]):
        row = rows[index] if rows is not None else None
        valid = isinstance(row, dict) and type(row.get("index")) is int and row["index"] == index
        executable = row.get("executable") if valid else None
        executed = row.get("executed") if valid else None
        valid = (valid and row.get("status") == "collected"
                 and all(isinstance(values, list) and len(values) <= MAX_LINES
                         and all(type(n) is int for n in values)
                         and len(set(values)) == len(values)
                         for values in (executable, executed)))
        valid = bool(valid and set(executed) <= set(executable) <= set(target["changed_lines"]))
        file = {
            "path": target["path"], "file_hash": target["file_hash"],
            "changed_ranges": ranges(target["changed_lines"]),
            "status": "collected" if valid else "unknown",
            "executed_changed_ranges": ranges(executed) if valid else [],
            "not_observed_changed_ranges": (
                ranges(set(executable) - set(executed)) if valid else None
            ),
            "no_line_event_ranges": (
                ranges(set(target["changed_lines"]) - set(executable)) if valid else None
            ),
        }
        if not valid:
            file["reason"] = (
                row["reason"] if isinstance(row, dict) and isinstance(row.get("reason"), str)
                and row["reason"] in _REASONS else reason
            )
        files.append(file)
    collected = sum(file["status"] == "collected" for file in files)
    feedback = {
        "schema_version": "public-changed-line-feedback-v1", "diff_hash": request["diff_hash"],
        "request_hash": request["request_hash"], "diagnostic_only": True,
        "scope": "python_launch_thread", "interpretation": INTERPRETATION,
        "status": ("not_applicable" if not files else "collected" if collected == len(files)
                   else "partial" if collected else "unknown"),
        "files": files, "omitted_file_count": request["omitted_file_count"],
        "deleted_line_count": request["deleted_line_count"],
    }
    if len(canonical_json(feedback).encode()) > MAX_FEEDBACK_BYTES:
        feedback["omitted_file_count"] += len(files)
        feedback.update(status="unknown", files=[], reason="feedback_size_limit")
    return feedback


class ReportChannel:
    """Demultiplex one bounded report without charging it to public stderr's cap.

    The untrusted process can interfere with tracing. A frame is not an attestation;
    duplicate, oversized, malformed or missing frames yield unknown diagnostics.
    """

    def __init__(self, request: dict, emit, *, prefix: bytes | None = None,
                 limit_bytes: int = MAX_REPORT_BYTES) -> None:
        self.prefix = marker(request) if prefix is None else prefix
        self.limit_bytes = limit_bytes
        self.emit = emit
        self.pending = b""
        self.collecting = False
        self.invalid = False
        self.count = 0
        self.framed_bytes = 0
        self.report = None

    def feed(self, block: bytes) -> None:
        self.pending += block
        while self.pending:
            if self.collecting:
                end = self.pending.find(b"\n")
                if end < 0:
                    if len(self.pending) > self.limit_bytes:
                        self.invalid = True
                        self.framed_bytes += len(self.pending)
                        self.pending = b""
                    return
                body, self.pending = self.pending[:end], self.pending[end + 1:]
                self.framed_bytes += end + 1
                self.count += 1
                if self.count > 1:
                    self.invalid = True
                if not self.invalid and len(body) <= self.limit_bytes:
                    try:
                        self.report = json.loads(body)
                    except (ValueError, UnicodeDecodeError, RecursionError):
                        self.invalid = True
                else:
                    self.invalid = True
                self.collecting = False
            else:
                start = self.pending.find(self.prefix)
                if start < 0:
                    keep = min(len(self.pending), len(self.prefix) - 1)
                    self.emit(self.pending[:-keep] if keep else self.pending)
                    self.pending = self.pending[-keep:] if keep else b""
                    return
                self.emit(self.pending[:start])
                self.framed_bytes += len(self.prefix)
                self.pending = self.pending[start + len(self.prefix):]
                self.collecting = True

    def finish(self) -> object:
        if self.collecting:
            self.invalid = True
        else:
            self.emit(self.pending)
        self.pending = b""
        return self.report if self.count == 1 and not self.invalid else None


def split_report(stderr: bytes, request: dict) -> tuple[bytes, object]:
    parts = []
    channel = ReportChannel(request, parts.append)
    # Also keep parsing memory bounded for check backends with large captured output.
    for offset in range(0, len(stderr), 4096):
        channel.feed(stderr[offset:offset + 4096])
    report = channel.finish()
    return b"".join(parts), report


def prepare_trace(directory: Path, request: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "line_trace.py").write_bytes(TRACE_WRAPPER.read_bytes())
    (directory / "line_request.json").write_text(canonical_json(request), encoding="utf-8")


def python_command_supported(command: list[str]) -> bool:
    if len(command) < 2:
        return False
    # Identify the registered executable by name, not by host-side path resolution.
    # Docker paths can be POSIX paths on a Windows host; keep argv[0] unchanged.
    executable = re.split(r"[/\\]", command[0])[-1]
    return (
        re.fullmatch(r"python(?:3(?:\.\d+)?)?(?:\.exe)?", executable, re.IGNORECASE) is not None
        and (command[1] in {"-c", "-m"} and len(command) >= 3
             or not command[1].startswith("-"))
    )


@contextmanager
def trace_launch(command: list[str], request: dict | None, workspace: Path, *, docker=False):
    if not request or not request["files"] or not python_command_supported(command):
        yield list(command), []
        return
    with tempfile.TemporaryDirectory(
        prefix="patchloop-lines-", ignore_cleanup_errors=True,
    ) as temporary:
        directory = Path(temporary)
        if directory.resolve().is_relative_to(workspace.resolve()):
            raise ContractError("line collector temporary root must be outside the workspace")
        prepare_trace(directory, request)
        trusted = "/opt/patchloop-lines" if docker else str(directory)
        root = "/workspace" if docker else str(workspace.resolve())
        mounts = (["--mount", f"type=bind,source={directory},target={trusted},readonly"]
                  if docker else [])
        yield [command[0], f"{trusted}/line_trace.py", f"{trusted}/line_request.json", root,
               *command[1:]], mounts
