"""Read-only, agent-visible projections for the local trace viewer.

The web surface deliberately excludes evaluator-private material, qualification
artifacts, checkpoints, and raw verifier evidence. It reads only the run
manifest/result, agent-visible events, and content-addressed artifacts already
referenced by those events.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

from patchloop.contracts import EventType, RunEvent, RunManifest
from patchloop.errors import RecoveryError

_MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
_MAX_RENDERED_CHARACTERS = 1_000_000
_MAX_VISUAL_LINES = 5_000
_MAX_JSON_CHILDREN = 250
_MAX_JSON_DEPTH = 12
_LANGUAGE_BY_SUFFIX = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".css": "css",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "jsx",
    ".md": "markdown",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "shell",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}
_CODE_VALUE_KEYS = frozenset({"content", "expected_text", "replacement_text", "source"})
_DIFF_VALUE_KEYS = frozenset({"diff", "patch", "submitted_patch"})
_TERMINAL_VALUE_KEYS = frozenset(
    {
        "error",
        "error_message",
        "failure_summary",
        "output",
        "stderr",
        "stdout",
        "test_output",
    }
)
_TOOL_TERMINALS = {
    EventType.TOOL_SUCCEEDED,
    EventType.TOOL_FAILED,
    EventType.TOOL_REPLAYED,
    EventType.TOOL_ADMISSION_BLOCKED,
    EventType.SUBMISSION_ACCEPTED,
    EventType.SUBMISSION_REJECTED,
}
_PHASE_LABELS = {
    "INTAKE": "접수",
    "REPRODUCE": "조사",
    "PLAN": "계획",
    "IMPLEMENT": "편집",
    "VERIFY": "검증",
    "REVIEW": "검토",
    "DONE": "완료",
}
_WORKFLOW_STAGES = (
    ("inspect", "조사", frozenset({"search_files", "read_file"})),
    ("edit", "편집", frozenset({"apply_patch", "apply_structured_edit"})),
    ("verify", "검증", frozenset({"run_check"})),
    ("review", "검토", frozenset({"get_diff"})),
    ("submit", "제출", frozenset({"finish_task"})),
)
_WORKFLOW_LABELS = {key: label for key, label, _names in _WORKFLOW_STAGES}
_WORKFLOW_TOOL_KIND = {name: key for key, _label, names in _WORKFLOW_STAGES for name in names}
_AGENT_WORK_TOOLS = frozenset(
    {
        "search_files",
        "read_file",
        "record_work_plan",
        "revise_work_plan",
        "apply_patch",
        "apply_structured_edit",
        "run_check",
        "get_diff",
        "finish_task",
    }
)
_DEFINITION_RE = re.compile(r"^\s*(?:async\s+def|def|class)\s+[^(:]+")
_DIFF_FILE_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_DIFF_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


class ReadOnlyTraceStore:
    """Minimal SQLite reader that never initializes or migrates runtime state."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise RecoveryError(f"trace state does not exist: {self.path}")
        sidecars = tuple(Path(str(self.path) + suffix) for suffix in ("-wal", "-shm", "-journal"))
        if any(path.exists() for path in sidecars):
            raise RecoveryError(
                "trace state still has SQLite sidecars; wait for the active run to close"
            )
        connection = sqlite3.connect(
            self.path.as_uri() + "?mode=ro&immutable=1",
            uri=True,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            yield connection
        finally:
            connection.close()

    def list_runs(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id, status, created_at, manifest_json, result_json "
                "FROM runs ORDER BY created_at DESC"
            ).fetchall()
        output: list[dict[str, Any]] = []
        for row in rows:
            manifest = RunManifest.model_validate_json(row["manifest_json"])
            result = json.loads(row["result_json"]) if row["result_json"] else None
            output.append(
                {
                    "run_id": row["run_id"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "manifest": manifest.model_dump(mode="json"),
                    "result": result,
                }
            )
        return output

    def has_run(self, run_id: str) -> bool:
        if not self.path.is_file():
            return False
        with self._connect() as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
                is not None
            )

    def get_manifest(self, run_id: str) -> RunManifest:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT manifest_json FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise RecoveryError(f"unknown run: {run_id}")
        return RunManifest.model_validate_json(row["manifest_json"])

    def list_events(self, run_id: str) -> list[RunEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_json FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return [RunEvent.model_validate_json(row["event_json"]) for row in rows]


def _json_text(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    if len(text) <= _MAX_RENDERED_CHARACTERS:
        return text
    omitted = len(text) - _MAX_RENDERED_CHARACTERS
    return text[:_MAX_RENDERED_CHARACTERS] + f"\n\n[viewer omitted {omitted:,} characters]"


def _visual_text(value: str) -> str:
    if len(value) <= _MAX_RENDERED_CHARACTERS:
        return value
    omitted = len(value) - _MAX_RENDERED_CHARACTERS
    return value[:_MAX_RENDERED_CHARACTERS] + f"\n\n[viewer omitted {omitted:,} characters]"


def _language_for_path(path: str | None, fallback: str = "text") -> str:
    if not path:
        return fallback
    return _LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower(), fallback)


def _visual_lines(
    text: str,
    *,
    start_line: int = 1,
    tones: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    normalized = _visual_text(text).replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = normalized.split("\n")
    omitted = max(0, len(raw_lines) - _MAX_VISUAL_LINES)
    output: list[dict[str, Any]] = []
    for offset, line in enumerate(raw_lines[:_MAX_VISUAL_LINES]):
        row: dict[str, Any] = {"number": start_line + offset, "text": line}
        if tones:
            lowered = line.lower()
            if re.search(
                r"traceback|assertionerror|\berror\b|\bexception\b|"
                r"\bfailed\b|\bfailure\b|timed out|^\s*e\s+",
                lowered,
            ):
                row["tone"] = "bad"
            elif re.search(r"\bpassed\b|\bsuccess(?:ful)?\b|\bok\b", lowered):
                row["tone"] = "good"
            else:
                row["tone"] = "neutral"
        output.append(row)
    return output, omitted


def _code_view(
    text: str,
    *,
    path: str | None = None,
    language: str | None = None,
    start_line: int = 1,
) -> dict[str, Any]:
    lines, omitted = _visual_lines(text, start_line=start_line)
    return {
        "kind": "code",
        "path": path,
        "language": language or _language_for_path(path),
        "start_line": start_line,
        "lines": lines,
        "omitted_line_count": omitted,
    }


def _diff_view(text: str) -> dict[str, Any]:
    lines, omitted = _visual_lines(text)
    for line in lines:
        content = line["text"]
        if content.startswith(("diff --git ", "index ", "--- ", "+++ ", "\\ No newline")):
            line["tone"] = "meta"
        elif content.startswith("@@"):
            line["tone"] = "hunk"
        elif content.startswith("+"):
            line["tone"] = "add"
        elif content.startswith("-"):
            line["tone"] = "delete"
        else:
            line["tone"] = "context"
    return {
        "kind": "diff",
        "lines": lines,
        "omitted_line_count": omitted,
    }


def _terminal_view(text: str) -> dict[str, Any]:
    lines, omitted = _visual_lines(text, tones=True)
    return {
        "kind": "terminal",
        "lines": lines,
        "omitted_line_count": omitted,
    }


def _text_view(text: str) -> dict[str, Any]:
    normalized = _visual_text(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    omitted = max(0, len(lines) - _MAX_VISUAL_LINES)
    lines = lines[:_MAX_VISUAL_LINES]
    blocks: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            language = stripped[3:].strip() or "text"
            index += 1
            code_start = index + 1
            code_lines: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            blocks.append(
                _code_view(
                    "\n".join(code_lines),
                    language=language,
                    start_line=code_start,
                )
            )
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            blocks.append(
                {
                    "kind": "heading",
                    "level": len(heading.group(1)),
                    "text": heading.group(2),
                }
            )
            index += 1
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            items: list[str] = []
            while index < len(lines):
                match = re.match(r"^\s*[-*]\s+(.+)$", lines[index])
                if not match:
                    break
                items.append(match.group(1))
                index += 1
            blocks.append({"kind": "list", "items": items})
            continue
        paragraph = [line]
        index += 1
        while index < len(lines):
            candidate = lines[index]
            candidate_stripped = candidate.strip()
            if (
                not candidate_stripped
                or candidate_stripped.startswith("```")
                or re.match(r"^(#{1,4})\s+", candidate_stripped)
                or re.match(r"^\s*[-*]\s+", candidate)
            ):
                break
            paragraph.append(candidate)
            index += 1
        blocks.append({"kind": "paragraph", "text": "\n".join(paragraph)})
    return {
        "kind": "text",
        "blocks": blocks,
        "omitted_line_count": omitted,
    }


def _parse_json_container(text: str) -> dict[str, Any] | list[Any] | None:
    stripped = text.strip()
    if not stripped.startswith(("{", "[")):
        return None
    try:
        value = json.loads(stripped)
    except ValueError:
        return None
    return value if isinstance(value, (dict, list)) else None


def _string_view(
    text: str,
    *,
    key_hint: str | None = None,
    path_hint: str | None = None,
    start_line: int = 1,
) -> dict[str, Any]:
    parsed = _parse_json_container(text)
    if parsed is not None:
        return _render_view(parsed)
    lowered_key = (key_hint or "").lower()
    if lowered_key in _DIFF_VALUE_KEYS or text.startswith("diff --git "):
        return _diff_view(text)
    if lowered_key in _CODE_VALUE_KEYS and path_hint:
        return _code_view(text, path=path_hint, start_line=start_line)
    if lowered_key in _TERMINAL_VALUE_KEYS:
        return _terminal_view(text)
    return _text_view(text)


def _scalar_display(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        compact = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ↵ ")
        if len(compact) > 180:
            compact = compact[:179].rstrip() + "…"
        return json.dumps(compact, ensure_ascii=False)
    return str(value)


def _json_node(
    value: Any,
    *,
    key_hint: str | None = None,
    path_hint: str | None = None,
    start_line: int = 1,
    depth: int = 0,
) -> dict[str, Any]:
    if depth >= _MAX_JSON_DEPTH and isinstance(value, (dict, list)):
        return {
            "kind": "limit",
            "summary": "depth limit",
            "display": f"viewer stopped expanding below depth {_MAX_JSON_DEPTH}",
        }
    if isinstance(value, dict):
        local_path = value.get("path") if isinstance(value.get("path"), str) else path_hint
        local_start = value.get("actual_start_line")
        if type(local_start) is not int:
            local_start = value.get("start_line")
        if type(local_start) is not int:
            local_start = start_line
        items = sorted(value.items(), key=lambda item: str(item[0]))
        children = [
            {
                "key": str(key),
                "node": _json_node(
                    child,
                    key_hint=str(key),
                    path_hint=local_path,
                    start_line=local_start,
                    depth=depth + 1,
                ),
            }
            for key, child in items[:_MAX_JSON_CHILDREN]
        ]
        return {
            "kind": "object",
            "summary": f"{len(value)} fields",
            "children": children,
            "omitted_child_count": max(0, len(items) - _MAX_JSON_CHILDREN),
            "open": depth < 2,
        }
    if isinstance(value, list):
        children = [
            {
                "key": f"[{index}]",
                "node": _json_node(
                    child,
                    key_hint=key_hint,
                    path_hint=path_hint,
                    start_line=start_line,
                    depth=depth + 1,
                ),
            }
            for index, child in enumerate(value[:_MAX_JSON_CHILDREN])
        ]
        return {
            "kind": "array",
            "summary": f"{len(value)} items",
            "children": children,
            "omitted_child_count": max(0, len(value) - _MAX_JSON_CHILDREN),
            "open": depth < 2,
        }
    scalar_type = (
        "null"
        if value is None
        else "boolean"
        if isinstance(value, bool)
        else "number"
        if isinstance(value, (int, float))
        else "string"
    )
    rendered = None
    if isinstance(value, str):
        parsed = _parse_json_container(value)
        should_render = bool(
            value.strip()
            and (
                parsed is not None
                or "\n" in value
                or len(value) > 180
                or (key_hint or "").lower()
                in (_CODE_VALUE_KEYS | _DIFF_VALUE_KEYS | _TERMINAL_VALUE_KEYS)
            )
        )
        if should_render:
            rendered = _string_view(
                value,
                key_hint=key_hint,
                path_hint=path_hint,
                start_line=start_line,
            )
    return {
        "kind": "scalar",
        "scalar_type": scalar_type,
        "display": _scalar_display(value),
        "rendered": rendered,
    }


def _render_view(
    value: Any,
    *,
    key_hint: str | None = None,
    path_hint: str | None = None,
    start_line: int = 1,
) -> dict[str, Any]:
    if isinstance(value, str):
        return _string_view(
            value,
            key_hint=key_hint,
            path_hint=path_hint,
            start_line=start_line,
        )
    if isinstance(value, (dict, list)):
        return {
            "kind": "json",
            "node": _json_node(
                value,
                key_hint=key_hint,
                path_hint=path_hint,
                start_line=start_line,
            ),
        }
    return {"kind": "json", "node": _json_node(value)}


def _artifact_object(path_value: Any, runtime: Path) -> dict[str, Any] | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    objects = (runtime / "artifacts" / "objects" / "sha256").resolve()
    lexical = Path(path_value)
    if not lexical.is_absolute():
        lexical = runtime / lexical
    if lexical.is_symlink():
        return None
    selected = lexical.resolve()
    if not selected.is_relative_to(objects) or not selected.is_file() or selected.is_symlink():
        return None
    if len(selected.parent.name) != 2 or len(selected.name) != 62:
        return None
    expected_digest = selected.parent.name + selected.name
    raw = selected.read_bytes()
    if len(raw) > _MAX_ARTIFACT_BYTES:
        return None
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        return None
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _message_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
                    continue
            parts.append(_json_text(item))
        return "\n\n".join(parts)
    return _json_text(value)


def _request_messages(request_artifact: dict[str, Any] | None) -> list[dict[str, Any]]:
    if request_artifact is None:
        return []
    request_body = request_artifact.get("request_body")
    if not isinstance(request_body, dict):
        return []
    raw_input = request_body.get("input")
    if not isinstance(raw_input, list):
        return []
    messages: list[dict[str, Any]] = []
    for item in raw_input:
        if not isinstance(item, dict):
            content = _message_content(item)
            messages.append(
                {
                    "role": "input",
                    "content": content,
                    "view": _render_view(content),
                }
            )
            continue
        role = item.get("role")
        content = _message_content(item.get("content", item))
        messages.append(
            {
                "role": role if isinstance(role, str) else "input",
                "content": content,
                "view": _render_view(content),
            }
        )
    return messages


def _turn_cost_usd(payload: dict[str, Any], manifest: RunManifest) -> Decimal:
    input_tokens = int(payload.get("input_tokens", 0) or 0)
    cached = min(int(payload.get("cached_input_tokens", 0) or 0), input_tokens)
    cache_write = min(
        int(payload.get("cache_write_input_tokens", 0) or 0),
        input_tokens - cached,
    )
    uncached = input_tokens - cached - cache_write
    output = int(payload.get("output_tokens", 0) or 0)
    model = manifest.model
    return (
        Decimal(uncached) * Decimal(str(model.input_price_per_million_usd))
        + Decimal(cached) * Decimal(str(model.cached_input_price_per_million_usd))
        + Decimal(cache_write) * Decimal(str(model.cache_write_input_price_per_million_usd))
        + Decimal(output) * Decimal(str(model.output_price_per_million_usd))
    ) / Decimal(1_000_000)


def _response_view(response: dict[str, Any] | None) -> dict[str, Any]:
    if response is None:
        return {
            "available": False,
            "text": "",
            "text_view": None,
            "tool_calls": [],
            "status": "artifact unavailable",
            "incomplete_reason": None,
            "error": None,
            "error_view": None,
        }
    calls: list[dict[str, Any]] = []
    raw_calls = response.get("tool_calls")
    if isinstance(raw_calls, list):
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                continue
            name = raw_call.get("name")
            arguments = raw_call.get("arguments", {})
            calls.append(
                {
                    "name": name if isinstance(name, str) else "tool",
                    "arguments": _json_text(arguments),
                    "arguments_view": _render_view(arguments),
                }
            )
    text = response.get("text")
    error = response.get("response_error")
    response_text = text if isinstance(text, str) else ""
    return {
        "available": True,
        "text": response_text,
        "text_view": _render_view(response_text) if response_text else None,
        "tool_calls": calls,
        "status": response.get("response_status") or "unknown",
        "incomplete_reason": response.get("response_incomplete_reason"),
        "error": _json_text(error) if error is not None else None,
        "error_view": _render_view(error) if error is not None else None,
    }


def _compact_text(value: Any, *, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _nonempty_lines(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [line.strip() for line in value.replace("\r\n", "\n").split("\n") if line.strip()]


def _last_line(value: Any) -> str | None:
    lines = _nonempty_lines(value)
    return lines[-1] if lines else None


def _line_count(value: Any) -> int:
    return len(value.splitlines()) if isinstance(value, str) and value else 0


def _changed_line_counts(before: str, after: str) -> tuple[int, int, int, int]:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    removed = 0
    added = 0
    first_old = 0
    first_new = 0
    first_seen = False
    for tag, old_start, old_end, new_start, new_end in difflib.SequenceMatcher(
        a=before_lines,
        b=after_lines,
        autojunk=False,
    ).get_opcodes():
        if tag == "equal":
            continue
        if not first_seen:
            first_old = old_start if old_start < len(before_lines) else max(0, old_start - 1)
            first_new = new_start if new_start < len(after_lines) else max(0, new_start - 1)
            first_seen = True
        removed += old_end - old_start
        added += new_end - new_start
    return removed, added, first_old, first_new


def _diff_preview(before: str, after: str, *, limit: int = 18) -> tuple[list[str], bool]:
    raw = list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="before",
            tofile="after",
            n=2,
            lineterm="",
        )
    )
    lines = [line for line in raw if not line.startswith(("--- ", "+++ "))]
    return lines[:limit], len(lines) > limit


def _definition_anchor(
    before_lines: list[str],
    after_lines: list[str],
    old_index: int,
    new_index: int,
    added_lines: int,
) -> str | None:
    changed_after = after_lines[new_index : new_index + max(added_lines, 1)]
    for line in changed_after:
        if _DEFINITION_RE.match(line):
            return _compact_text(line, limit=120)
    upper = min(max(old_index, 0), max(0, len(before_lines) - 1))
    for line in reversed(before_lines[: upper + 1]):
        if _DEFINITION_RE.match(line):
            return _compact_text(line, limit=120)
    for line in changed_after or before_lines[upper:]:
        if line.strip():
            return _compact_text(line, limit=120)
    return None


def _locate_visible_text(
    path: str,
    expected: str,
    read_history: dict[str, list[dict[str, Any]]],
) -> int | None:
    for read in reversed(read_history.get(path, [])):
        content = read.get("content")
        start_line = read.get("start_line")
        if not isinstance(content, str) or type(start_line) is not int:
            continue
        offset = content.find(expected)
        if offset >= 0:
            return start_line + content[:offset].count("\n")
    return None


def _structured_edit_changes(
    tool_input: dict[str, Any],
    read_history: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    raw_files = tool_input.get("files")
    if not isinstance(raw_files, list):
        return []
    changes: list[dict[str, Any]] = []
    for raw_file in raw_files:
        if not isinstance(raw_file, dict) or not isinstance(raw_file.get("path"), str):
            continue
        path = raw_file["path"]
        replacements = raw_file.get("replacements")
        if not isinstance(replacements, list):
            continue
        for index, replacement in enumerate(replacements, 1):
            if not isinstance(replacement, dict):
                continue
            before = replacement.get("expected_text")
            after = replacement.get("replacement_text")
            if not isinstance(before, str) or not isinstance(after, str):
                continue
            before_lines = before.splitlines()
            after_lines = after.splitlines()
            removed, added, old_index, new_index = _changed_line_counts(before, after)
            visible_start = _locate_visible_text(path, before, read_history)
            changed_start = visible_start + old_index if visible_start is not None else None
            changed_end = changed_start + max(removed, 1) - 1 if changed_start is not None else None
            preview, preview_truncated = _diff_preview(before, after)
            changes.append(
                {
                    "path": path,
                    "replacement": index,
                    "anchor": _definition_anchor(
                        before_lines,
                        after_lines,
                        old_index,
                        new_index,
                        added,
                    ),
                    "line_start": changed_start,
                    "line_end": changed_end,
                    "removed_lines": removed,
                    "added_lines": added,
                    "preview": preview,
                    "preview_truncated": preview_truncated,
                }
            )
    return changes


def _patch_changes(patch: Any, *, limit: int = 24) -> list[dict[str, Any]]:
    if not isinstance(patch, str):
        return []
    changes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in patch.replace("\r\n", "\n").split("\n"):
        file_match = _DIFF_FILE_RE.match(line)
        if file_match:
            current = {
                "path": file_match.group(2),
                "hunks": [],
                "removed_lines": 0,
                "added_lines": 0,
                "preview": [],
                "preview_truncated": False,
            }
            changes.append(current)
            continue
        if current is None:
            continue
        hunk_match = _DIFF_HUNK_RE.match(line)
        if hunk_match:
            current["hunks"].append(
                {
                    "old_start": int(hunk_match.group(1)),
                    "old_count": int(hunk_match.group(2) or 1),
                    "new_start": int(hunk_match.group(3)),
                    "new_count": int(hunk_match.group(4) or 1),
                    "context": _compact_text(hunk_match.group(5), limit=100),
                }
            )
        elif line.startswith("-") and not line.startswith("---"):
            current["removed_lines"] += 1
        elif line.startswith("+") and not line.startswith("+++"):
            current["added_lines"] += 1
        if line.startswith(("@@", "+", "-", " ")):
            if len(current["preview"]) < limit:
                current["preview"].append(line)
            else:
                current["preview_truncated"] = True
    return changes


def _plan_paths(tool_input: dict[str, Any]) -> list[str]:
    candidates = tool_input.get("candidate_files")
    if not isinstance(candidates, list):
        return []
    paths: list[str] = []
    for item in candidates:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            paths.append(item["path"])
    return paths


def _check_summary(
    tool_input: dict[str, Any],
    result: dict[str, Any] | None,
    outcome_payload: dict[str, Any],
    *,
    status: str,
    error_message: str | None,
) -> dict[str, Any]:
    public_result = result if result and result.get("public_visible_only") is True else None
    check_id = tool_input.get("check_id") or outcome_payload.get("check_id")
    passed = outcome_payload.get("passed")
    if passed is None and public_result is not None:
        passed = public_result.get("passed")
    timed_out = bool(
        outcome_payload.get("timed_out")
        or (public_result is not None and public_result.get("timed_out"))
    )
    failure_summary = public_result.get("failure_summary") if public_result else None
    reason = _last_line(failure_summary) or error_message
    stdout_summary = _last_line(public_result.get("stdout")) if public_result else None
    if timed_out:
        status_label = "시간 초과"
    elif passed is True:
        status_label = "통과"
    elif passed is False or status == "failed":
        status_label = "실패"
    else:
        status_label = "결과 없음"
    return {
        "kind": "check",
        "kind_label": "검증",
        "title": str(check_id or "visible check"),
        "detail": reason or stdout_summary or "공개 결과 요약이 없습니다.",
        "status_label": status_label,
        "check_id": check_id,
        "passed": passed is True,
        "timed_out": timed_out,
        "failure_excerpt": (_compact_text(failure_summary, limit=700) if failure_summary else None),
        "stdout_summary": stdout_summary,
    }


def _agent_tool_summary(
    *,
    name: str,
    tool_input: dict[str, Any],
    result: dict[str, Any] | None,
    outcome_payload: dict[str, Any],
    status: str,
    error_message: str | None,
    read_history: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    if name not in _AGENT_WORK_TOOLS:
        return None
    status_label = {
        "succeeded": "완료",
        "failed": "실패",
        "replayed": "재사용",
        "pending": "대기",
    }.get(status, status)
    if name == "read_file":
        path = tool_input.get("path")
        start = result.get("actual_start_line") if result else tool_input.get("start_line")
        end = result.get("actual_end_line") if result else tool_input.get("end_line")
        if type(start) is int and type(end) is int:
            detail = f"{start}–{end}행 · {max(0, end - start + 1)}줄"
        else:
            detail = "읽은 범위 정보 없음"
        return {
            "kind": "read",
            "kind_label": "파일 읽기",
            "title": str(path or "경로 정보 없음"),
            "detail": detail,
            "status_label": status_label,
            "path": path,
            "line_start": start,
            "line_end": end,
        }
    if name == "search_files":
        query = tool_input.get("query")
        path_glob = tool_input.get("path_glob")
        matches = result.get("matches") if result else None
        count = len(matches) if isinstance(matches, list) else None
        detail_parts = []
        if isinstance(path_glob, str) and path_glob:
            detail_parts.append(path_glob)
        if count is not None:
            detail_parts.append(f"{count}개 결과")
        return {
            "kind": "search",
            "kind_label": "코드 검색",
            "title": str(query or "검색어 정보 없음"),
            "detail": " · ".join(detail_parts) or "허용된 소스에서 검색",
            "status_label": status_label,
            "query": query,
            "path_glob": path_glob,
        }
    if name in {"record_work_plan", "revise_work_plan"}:
        initial = name == "record_work_plan"
        disposition = tool_input.get("prior_hypothesis_disposition")
        detail = _compact_text(tool_input.get("hypothesis"), limit=900)
        return {
            "kind": "plan",
            "kind_label": "초기 계획" if initial else "수정 계획",
            "title": "작업 가설 기록" if initial else "실패 후 가설 수정",
            "detail": detail or "구조화된 가설 없음",
            "status_label": status_label,
            "hypothesis": detail,
            "intended_change": _compact_text(
                tool_input.get("intended_change"),
                limit=600,
            ),
            "expected_behavior": _compact_text(
                tool_input.get("expected_behavior"),
                limit=600,
            ),
            "candidate_files": _plan_paths(tool_input),
            "disposition": disposition if isinstance(disposition, str) else None,
            "unknowns": [
                _compact_text(item, limit=220)
                for item in tool_input.get("unknowns", [])[:5]
                if isinstance(item, str)
            ]
            if isinstance(tool_input.get("unknowns"), list)
            else [],
        }
    if name == "apply_structured_edit":
        changes = _structured_edit_changes(tool_input, read_history)
        files = list(dict.fromkeys(change["path"] for change in changes))
        removed = sum(change["removed_lines"] for change in changes)
        added = sum(change["added_lines"] for change in changes)
        return {
            "kind": "edit",
            "kind_label": "코드 수정",
            "title": files[0] if len(files) == 1 else f"{len(files)}개 파일 수정",
            "detail": (
                f"{len(changes)}개 변경 · -{removed}/+{added}줄"
                if changes
                else error_message or "구조화된 수정 정보 없음"
            ),
            "status_label": status_label,
            "files": files,
            "changes": changes,
            "failure_reason": error_message if status == "failed" else None,
        }
    if name == "apply_patch":
        changes = _patch_changes(tool_input.get("patch"))
        files = [change["path"] for change in changes]
        return {
            "kind": "edit",
            "kind_label": "코드 수정",
            "title": files[0] if len(files) == 1 else f"{len(files)}개 파일 patch",
            "detail": error_message or f"{len(changes)}개 파일 diff",
            "status_label": status_label,
            "files": files,
            "changes": changes,
            "failure_reason": error_message if status == "failed" else None,
        }
    if name == "run_check":
        return _check_summary(
            tool_input,
            result,
            outcome_payload,
            status=status,
            error_message=error_message,
        )
    if name == "get_diff":
        changes = _patch_changes(result.get("patch") if result else None)
        changed_files = result.get("changed_files") if result else None
        files = (
            [item for item in changed_files if isinstance(item, str)]
            if isinstance(changed_files, list)
            else [change["path"] for change in changes]
        )
        added = result.get("added_lines") if result else None
        deleted = result.get("deleted_lines") if result else None
        return {
            "kind": "review",
            "kind_label": "최종 diff",
            "title": f"{len(files)}개 변경 파일 확인",
            "detail": (
                f"-{deleted}/+{added}줄"
                if type(added) is int and type(deleted) is int
                else "diff 요약"
            ),
            "status_label": status_label,
            "files": files,
            "changes": changes,
        }
    return {
        "kind": "submit",
        "kind_label": "제출",
        "title": "Task 제출 요청",
        "detail": error_message or ("제출 완료" if status == "succeeded" else status_label),
        "status_label": status_label,
    }


def _public_task_view(turns: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract only the explicitly public task envelope from agent input."""

    for turn in turns:
        for message in turn["messages"]:
            if message["role"] != "user":
                continue
            try:
                envelope = json.loads(message["content"])
            except (TypeError, ValueError):
                continue
            if not isinstance(envelope, dict):
                continue
            public_task = envelope.get("public_task")
            if not isinstance(public_task, dict):
                continue
            issue = public_task.get("issue")
            issue = issue if isinstance(issue, dict) else {}
            constraints = public_task.get("constraints")
            constraints = constraints if isinstance(constraints, dict) else {}
            raw_paths = constraints.get("allowed_paths")
            allowed_paths = (
                [item for item in raw_paths if isinstance(item, str)][:20]
                if isinstance(raw_paths, list)
                else []
            )
            raw_forbidden = constraints.get("forbidden_paths")
            forbidden_paths = (
                [item for item in raw_forbidden if isinstance(item, str)][:20]
                if isinstance(raw_forbidden, list)
                else []
            )
            visible_checks = public_task.get("visible_checks")
            visible_check_ids = (
                [
                    item["id"]
                    for item in visible_checks
                    if isinstance(item, dict) and isinstance(item.get("id"), str)
                ][:20]
                if isinstance(visible_checks, list)
                else []
            )
            repository = public_task.get("repository")
            repository = repository if isinstance(repository, dict) else {}
            raw_tags = public_task.get("tags")
            return {
                "title": issue.get("title") if isinstance(issue.get("title"), str) else None,
                "description": (
                    issue.get("description") if isinstance(issue.get("description"), str) else None
                ),
                "allowed_paths": allowed_paths,
                "forbidden_paths": forbidden_paths,
                "max_changed_files": constraints.get("max_changed_files"),
                "max_diff_lines": constraints.get("max_diff_lines"),
                "dependency_changes_allowed": constraints.get("dependency_changes_allowed"),
                "public_api_changes_allowed": constraints.get("public_api_changes_allowed"),
                "visible_check_count": len(visible_check_ids),
                "visible_check_ids": visible_check_ids,
                "repository_url": (
                    repository.get("url") if isinstance(repository.get("url"), str) else None
                ),
                "language": (
                    repository.get("language")
                    if isinstance(repository.get("language"), str)
                    else None
                ),
                "tags": (
                    [item for item in raw_tags if isinstance(item, str)][:20]
                    if isinstance(raw_tags, list)
                    else []
                ),
            }
    return {
        "title": None,
        "description": None,
        "allowed_paths": [],
        "forbidden_paths": [],
        "max_changed_files": None,
        "max_diff_lines": None,
        "dependency_changes_allowed": None,
        "public_api_changes_allowed": None,
        "visible_check_count": 0,
        "visible_check_ids": [],
        "repository_url": None,
        "language": None,
        "tags": [],
    }


def _turns(
    events: list[RunEvent],
    manifest: RunManifest,
    runtime: Path,
) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for number, event in enumerate(
        (item for item in events if item.type == EventType.MODEL_CALLED),
        1,
    ):
        request = _artifact_object(event.payload.get("request_artifact_path"), runtime)
        response = _artifact_object(event.payload.get("artifact_path"), runtime)
        request_body = request.get("request_body") if isinstance(request, dict) else None
        settings = request_body if isinstance(request_body, dict) else {}
        response_view = _response_view(response)
        if not response_view["available"]:
            event_status = event.payload.get("response_status")
            event_reason = event.payload.get("response_incomplete_reason")
            if isinstance(event_status, str):
                response_view["status"] = event_status
            if isinstance(event_reason, str):
                response_view["incomplete_reason"] = event_reason
        turns.append(
            {
                "number": number,
                "sequence": event.sequence,
                "model": event.payload.get("response_model")
                or event.payload.get("model")
                or manifest.model.model_id,
                "input_tokens": int(event.payload.get("input_tokens", 0) or 0),
                "output_tokens": int(event.payload.get("output_tokens", 0) or 0),
                "reasoning_tokens": int(event.payload.get("reasoning_output_tokens", 0) or 0),
                "cached_input_tokens": int(event.payload.get("cached_input_tokens", 0) or 0),
                "cost_usd": _turn_cost_usd(event.payload, manifest),
                "max_output_tokens": settings.get("max_output_tokens"),
                "messages": _request_messages(request),
                "response": response_view,
            }
        )
    return turns


def _tools(events: list[RunEvent], runtime: Path) -> list[dict[str, Any]]:
    outcomes = {
        event.correlation_id: event
        for event in events
        if event.type in _TOOL_TERMINALS and event.correlation_id
    }
    rows: list[dict[str, Any]] = []
    read_history: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event.type != EventType.TOOL_CALLED:
            continue
        outcome = outcomes.get(event.correlation_id)
        descriptor = event.payload.get("input_artifact")
        input_artifact = _artifact_object(
            descriptor.get("path") if isinstance(descriptor, dict) else None,
            runtime,
        )
        result_descriptor = outcome.payload.get("result_artifact") if outcome else None
        result_artifact = _artifact_object(
            result_descriptor.get("path") if isinstance(result_descriptor, dict) else None,
            runtime,
        )
        tool_input = input_artifact.get("input", {}) if isinstance(input_artifact, dict) else {}
        check_failed = bool(
            outcome
            and event.payload.get("tool") == "run_check"
            and (outcome.payload.get("passed") is False or outcome.payload.get("timed_out") is True)
        )
        if outcome and (
            outcome.type
            in {
                EventType.TOOL_FAILED,
                EventType.TOOL_ADMISSION_BLOCKED,
                EventType.SUBMISSION_REJECTED,
            }
            or check_failed
        ):
            status = "failed"
        elif outcome and outcome.type in {
            EventType.TOOL_SUCCEEDED,
            EventType.SUBMISSION_ACCEPTED,
        }:
            status = "succeeded"
        elif outcome and outcome.type == EventType.TOOL_REPLAYED:
            status = "replayed"
        else:
            status = "pending"
        error_message = outcome.payload.get("error_message") if outcome else None
        error_code = outcome.payload.get("error_code") if outcome else None
        if check_failed and not error_code:
            error_code = (
                "CHECK_TIMED_OUT" if outcome.payload.get("timed_out") is True else "CHECK_FAILED"
            )
            if not error_message:
                error_message = "registered visible check did not pass"
        if outcome and outcome.type == EventType.SUBMISSION_REJECTED and not error_code:
            error_code = "SUBMISSION_REJECTED"
        name = str(event.payload.get("tool", "tool"))
        summary = _agent_tool_summary(
            name=name,
            tool_input=tool_input,
            result=result_artifact,
            outcome_payload=outcome.payload if outcome else {},
            status=status,
            error_message=error_message if isinstance(error_message, str) else None,
            read_history=read_history,
        )
        rows.append(
            {
                "sequence": event.sequence,
                "terminal_sequence": outcome.sequence if outcome else None,
                "name": name,
                "status": status,
                "tone": "bad" if status == "failed" else "good",
                "input": _json_text(tool_input),
                "input_view": _render_view(
                    tool_input,
                    path_hint=(
                        tool_input.get("path") if isinstance(tool_input.get("path"), str) else None
                    ),
                ),
                "output": _json_text(result_artifact) if result_artifact is not None else "",
                "output_view": (
                    _render_view(
                        result_artifact,
                        path_hint=(
                            tool_input.get("path")
                            if isinstance(tool_input.get("path"), str)
                            else None
                        ),
                        start_line=(
                            result_artifact.get("actual_start_line")
                            if isinstance(result_artifact, dict)
                            and type(result_artifact.get("actual_start_line")) is int
                            else 1
                        ),
                    )
                    if result_artifact is not None
                    else None
                ),
                "duration_ms": outcome.payload.get("duration_ms") if outcome else None,
                "error_code": error_code,
                "error_message": error_message if isinstance(error_message, str) else None,
                "agent_summary": summary,
            }
        )
        if (
            name == "read_file"
            and status in {"succeeded", "replayed"}
            and isinstance(tool_input.get("path"), str)
            and isinstance(result_artifact, dict)
            and isinstance(result_artifact.get("content"), str)
        ):
            start_line = result_artifact.get("actual_start_line")
            if type(start_line) is not int:
                start_line = tool_input.get("start_line")
            if type(start_line) is int:
                read_history.setdefault(tool_input["path"], []).append(
                    {
                        "start_line": start_line,
                        "content": result_artifact["content"],
                    }
                )
    return rows


def _turn_number_for_sequence(turns: list[dict[str, Any]], sequence: int) -> int | None:
    selected = None
    for turn in turns:
        if turn["sequence"] >= sequence:
            break
        selected = turn["number"]
    return selected


def _cycle_view(label: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [action for action in actions if action["summary"]["kind"] == "check"]
    last_check = checks[-1]["summary"] if checks else None
    failed = any(action["status"] == "failed" for action in actions)
    if last_check is not None:
        headline = f"{last_check['title']} · {last_check['status_label']}"
        detail = last_check["detail"]
    elif any(action["summary"]["kind"] == "submit" for action in actions):
        submission = next(
            action["summary"]
            for action in reversed(actions)
            if action["summary"]["kind"] == "submit"
        )
        headline = submission["title"]
        detail = submission["detail"]
    elif any(action["summary"]["kind"] == "edit" for action in actions):
        headline = "코드 수정 후 검증 전 종료"
        detail = "이 시도에는 뒤따르는 visible check 결과가 없습니다."
    else:
        headline = "조사 또는 계획 단계"
        detail = actions[-1]["summary"]["detail"] if actions else ""
    return {
        "label": label,
        "headline": headline,
        "detail": detail,
        "tone": "bad" if failed else "good",
        "open": bool(last_check and last_check["status_label"] != "통과"),
        "actions": actions,
        "read_count": sum(action["summary"]["kind"] == "read" for action in actions),
        "edit_count": sum(action["summary"]["kind"] == "edit" for action in actions),
        "check_count": len(checks),
    }


def _agent_work_log(
    tools: list[dict[str, Any]],
    turns: list[dict[str, Any]],
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for tool in tools:
        summary = tool.get("agent_summary")
        if not isinstance(summary, dict):
            continue
        actions.append(
            {
                "sequence": tool["sequence"],
                "terminal_sequence": tool["terminal_sequence"],
                "turn_number": _turn_number_for_sequence(turns, tool["sequence"]),
                "tool": tool["name"],
                "status": tool["status"],
                "tone": tool["tone"],
                "duration_ms": tool["duration_ms"],
                "error_code": tool["error_code"],
                "summary": summary,
            }
        )

    cycles: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    previous_check: dict[str, Any] | None = None
    correction_index = 0
    current_label = "초기 시도"
    for action in actions:
        if not current:
            kind = action["summary"]["kind"]
            if kind in {"review", "submit"}:
                current_label = "최종 검토와 제출"
            elif previous_check and previous_check["status_label"] != "통과":
                correction_index += 1
                current_label = f"수정 시도 {correction_index}"
            elif previous_check:
                current_label = "후속 검증"
            else:
                current_label = "초기 시도"
        current.append(action)
        if action["summary"]["kind"] == "check":
            cycles.append(_cycle_view(current_label, current))
            previous_check = action["summary"]
            current = []
    if current:
        cycles.append(_cycle_view(current_label, current))

    read_files = sorted(
        {
            str(action["summary"]["path"])
            for action in actions
            if action["summary"]["kind"] == "read" and action["summary"].get("path")
        }
    )
    edited_files = sorted(
        {
            str(path)
            for action in actions
            if action["summary"]["kind"] in {"edit", "review"}
            for path in action["summary"].get("files", [])
        }
    )
    edits = [action for action in actions if action["summary"]["kind"] == "edit"]
    checks = [action for action in actions if action["summary"]["kind"] == "check"]
    plans = [action for action in actions if action["summary"]["kind"] == "plan"]
    return {
        "schema_version": "agent-work-log-v1",
        "cycles": cycles,
        "action_count": len(actions),
        "read_count": sum(action["summary"]["kind"] == "read" for action in actions),
        "read_files": read_files,
        "edit_attempts": len(edits),
        "edits_applied": sum(action["status"] == "succeeded" for action in edits),
        "edited_files": edited_files,
        "checks_run": len(checks),
        "checks_passed": sum(action["summary"].get("passed") is True for action in checks),
        "checks_failed": sum(
            action["summary"].get("status_label") in {"실패", "시간 초과"} for action in checks
        ),
        "plans_recorded": len(plans),
    }


def _phase_transitions(events: list[RunEvent]) -> list[tuple[int, str]]:
    transitions = [(0, "INTAKE")]
    for event in events:
        if event.type != EventType.PHASE_CHANGED:
            continue
        target = event.payload.get("to")
        if isinstance(target, str):
            transitions.append((event.sequence, target))
    return transitions


def _phase_at(sequence: int, transitions: list[tuple[int, str]]) -> str:
    phase = "INTAKE"
    for transition_sequence, target in transitions:
        if transition_sequence > sequence:
            break
        phase = target
    return phase


def _action_counts(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(tool["name"]) for tool in tools)
    return [{"name": name, "count": count} for name, count in counts.items()]


def _turn_kind(turn: dict[str, Any]) -> str:
    if _response_is_terminal(str(turn["response"]["status"])):
        return "terminal"
    kinds = {_WORKFLOW_TOOL_KIND.get(str(tool["name"]), "other") for tool in turn["tools"]}
    for kind in ("submit", "verify", "review", "edit", "inspect", "other"):
        if kind in kinds:
            return kind
    return "response"


def _response_is_terminal(status: str) -> bool:
    return status not in {"completed", "artifact unavailable", "unknown"}


def _turn_timeline(
    turns: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    events: list[RunEvent],
) -> list[dict[str, Any]]:
    transitions = _phase_transitions(events)
    timeline: list[dict[str, Any]] = []
    cumulative_tokens = 0
    cumulative_cost = Decimal(0)
    for index, turn in enumerate(turns):
        upper_bound = turns[index + 1]["sequence"] if index + 1 < len(turns) else None
        turn_tools = [
            tool
            for tool in tools
            if tool["sequence"] > turn["sequence"]
            and (upper_bound is None or tool["sequence"] < upper_bound)
        ]
        compact_tools = [
            {
                "sequence": tool["sequence"],
                "terminal_sequence": tool["terminal_sequence"],
                "name": tool["name"],
                "status": tool["status"],
                "tone": tool["tone"],
                "error_code": tool["error_code"],
                "error_message": _compact_text(tool["error_message"]),
            }
            for tool in turn_tools
        ]
        failed = sum(tool["status"] == "failed" for tool in compact_tools)
        response_status = str(turn["response"]["status"])
        response_failed = _response_is_terminal(response_status)
        tone = "bad" if failed or response_failed else "good" if turn_tools else "neutral"
        total_tokens = turn["input_tokens"] + turn["output_tokens"]
        cumulative_tokens += total_tokens
        cumulative_cost += turn["cost_usd"]
        phase = _phase_at(turn["sequence"], transitions)
        row = {
            "number": turn["number"],
            "sequence": turn["sequence"],
            "phase": phase,
            "phase_label": _PHASE_LABELS.get(phase, phase.title()),
            "input_tokens": turn["input_tokens"],
            "output_tokens": turn["output_tokens"],
            "reasoning_tokens": turn["reasoning_tokens"],
            "total_tokens": total_tokens,
            "cost_usd": turn["cost_usd"],
            "cumulative_tokens": cumulative_tokens,
            "cumulative_cost_usd": cumulative_cost,
            "response_status": response_status,
            "incomplete_reason": turn["response"]["incomplete_reason"],
            "tools": compact_tools,
            "action_counts": _action_counts(turn_tools),
            "failed_tool_count": failed,
            "tone": tone,
        }
        row["kind"] = _turn_kind({**turn, "tools": compact_tools})
        row["kind_label"] = {
            **_WORKFLOW_LABELS,
            "terminal": "중단",
            "response": "응답",
            "other": "기타",
        }[row["kind"]]
        if row["action_counts"]:
            row["action_label"] = " · ".join(
                f"{item['name']} ×{item['count']}" for item in row["action_counts"]
            )
        elif response_failed:
            row["action_label"] = f"LLM 응답 중단 · {row['incomplete_reason'] or response_status}"
        elif response_status == "artifact unavailable":
            row["action_label"] = "response artifact unavailable"
        else:
            row["action_label"] = "text response"
        timeline.append(row)
    if timeline:
        largest = max(timeline, key=lambda item: item["cost_usd"])
        largest["largest_cost_turn"] = True
    return timeline


def _episodes(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    for turn in timeline:
        key = (turn["phase"], turn["kind"], turn["tone"])
        if not episodes or episodes[-1]["key"] != key:
            episodes.append(
                {
                    "key": key,
                    "phase": turn["phase"],
                    "phase_label": turn["phase_label"],
                    "kind": turn["kind"],
                    "kind_label": turn["kind_label"],
                    "tone": turn["tone"],
                    "turn_start": turn["number"],
                    "turn_end": turn["number"],
                    "turn_count": 0,
                    "tool_count": 0,
                    "failed_tool_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": Decimal(0),
                    "turns": [],
                }
            )
        episode = episodes[-1]
        episode["turn_end"] = turn["number"]
        episode["turn_count"] += 1
        episode["tool_count"] += len(turn["tools"])
        episode["failed_tool_count"] += turn["failed_tool_count"]
        episode["input_tokens"] += turn["input_tokens"]
        episode["output_tokens"] += turn["output_tokens"]
        episode["total_tokens"] += turn["total_tokens"]
        episode["cost_usd"] += turn["cost_usd"]
        episode["turns"].append(turn)
    for episode in episodes:
        tools = [tool for turn in episode["turns"] for tool in turn["tools"]]
        episode["action_counts"] = _action_counts(tools)
        episode["action_label"] = (
            " · ".join(f"{item['name']} ×{item['count']}" for item in episode["action_counts"])
            or episode["turns"][-1]["action_label"]
        )
        episode["turn_label"] = (
            f"Turn {episode['turn_start']}"
            if episode["turn_start"] == episode["turn_end"]
            else f"Turns {episode['turn_start']}–{episode['turn_end']}"
        )
        episode["status_label"] = (
            "중단"
            if episode["kind"] == "terminal"
            else "실패 포함"
            if episode["failed_tool_count"]
            else "완료"
        )
        del episode["key"]
    return episodes


def _workflow(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for key, label, names in _WORKFLOW_STAGES:
        selected = [tool for tool in tools if tool["name"] in names]
        failed = sum(tool["status"] == "failed" for tool in selected)
        output.append(
            {
                "key": key,
                "label": label,
                "calls": len(selected),
                "failed": failed,
                "tone": "bad" if failed else "good" if selected else "neutral",
                "status_label": (
                    f"{len(selected)}회 · {failed} 실패"
                    if failed
                    else f"{len(selected)}회"
                    if selected
                    else "미도달"
                ),
            }
        )
    return output


def _result_summary(result: dict[str, Any]) -> str:
    outcome = result["outcome"]
    submission = result["submission_status"]
    evaluation = result["evaluation_status"]
    if outcome == "resolved":
        return "제출과 evaluator 검사가 완료되어 성공으로 판정됐습니다."
    if outcome == "task_failure":
        return "제출은 완료됐지만 evaluator 판정에서 실패했습니다."
    if outcome == "agent_failure" and evaluation == "not_run":
        return "Agent가 제출을 완료하지 못해 evaluator에 도달하지 못했습니다."
    if outcome == "infrastructure_error":
        return "인프라 오류로 실행 결과를 정상적으로 판정하지 못했습니다."
    return f"submission={submission} · evaluation={evaluation} 상태입니다."


def _failure_chain(
    timeline: list[dict[str, Any]],
    events: list[RunEvent],
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    for turn in timeline:
        for tool in turn["tools"]:
            if tool["status"] != "failed":
                continue
            detail = " · ".join(
                item for item in (tool["error_code"], tool["error_message"]) if item
            )
            chain.append(
                {
                    "sequence": tool["terminal_sequence"] or tool["sequence"],
                    "kind": "tool_failure",
                    "label": f"{tool['name']} 거절",
                    "detail": detail or "tool failure",
                    "tone": "bad",
                }
            )
        if _response_is_terminal(turn["response_status"]):
            chain.append(
                {
                    "sequence": turn["sequence"],
                    "kind": "model_incomplete",
                    "label": "LLM 응답 중단",
                    "detail": turn["incomplete_reason"] or turn["response_status"],
                    "tone": "bad",
                }
            )
    matched_tool_terminals = {
        tool["terminal_sequence"]
        for turn in timeline
        for tool in turn["tools"]
        if tool["terminal_sequence"] is not None
    }
    for event in events:
        if event.type == EventType.SUBMISSION_REJECTED:
            if event.sequence in matched_tool_terminals:
                continue
            chain.append(
                {
                    "sequence": event.sequence,
                    "kind": "submission_rejected",
                    "label": "제출 거절",
                    "detail": "finish_task submission was rejected",
                    "tone": "bad",
                }
            )
    terminal_events = [
        event for event in events if event.type in {EventType.RUN_FAILED, EventType.RUN_COMPLETED}
    ]
    if result["outcome"] in {"agent_failure", "infrastructure_error", "task_failure"}:
        terminal = result["terminal_error"] or {}
        terminal_detail = " · ".join(
            item
            for item in (
                terminal.get("code") if isinstance(terminal, dict) else None,
                _compact_text(terminal.get("message")) if isinstance(terminal, dict) else None,
            )
            if item
        )
        failed_verdicts = [
            name.replace("_", " ")
            for name, value in result["verdicts"].items()
            if value in {"fail", "error"}
        ]
        if result["outcome"] == "task_failure" and failed_verdicts:
            terminal_detail = "evaluator fail · " + ", ".join(failed_verdicts)
        chain.append(
            {
                "sequence": terminal_events[-1].sequence if terminal_events else None,
                "kind": "run_terminal",
                "label": result["outcome_label"],
                "detail": terminal_detail
                or (
                    f"submission={result['submission_status']} · "
                    f"evaluation={result['evaluation_status']}"
                ),
                "tone": "bad",
            }
        )
    return sorted(
        chain,
        key=lambda item: (item["sequence"] is None, item["sequence"] or 0),
    )


def _observations(
    workflow: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    result: dict[str, Any],
) -> list[dict[str, str]]:
    stages = {stage["key"]: stage for stage in workflow}
    output: list[dict[str, str]] = []
    total_tools = len(tools)
    inspect_calls = stages["inspect"]["calls"]
    if total_tools >= 8 and inspect_calls / total_tools >= 0.7:
        output.append(
            {
                "tone": "warn",
                "title": "조사 반복",
                "detail": f"tool {total_tools}회 중 search/read가 {inspect_calls}회입니다.",
            }
        )
    failed = sum(tool["status"] == "failed" for tool in tools)
    if failed:
        output.append(
            {
                "tone": "bad",
                "title": "Tool 거절",
                "detail": f"{failed}개 tool 호출이 실패했습니다.",
            }
        )
    terminal_failure = result["outcome"] in {
        "agent_failure",
        "task_failure",
        "infrastructure_error",
    }
    if terminal_failure and stages["verify"]["calls"] == 0:
        output.append(
            {
                "tone": "bad",
                "title": "검증 미도달",
                "detail": "run_check 호출이 관찰되지 않았습니다.",
            }
        )
    if terminal_failure and stages["submit"]["calls"] == 0:
        output.append(
            {
                "tone": "bad",
                "title": "제출 미도달",
                "detail": "finish_task 호출이 관찰되지 않았습니다.",
            }
        )
    return output


def _story_view(
    turns: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    events: list[RunEvent],
    result: dict[str, Any],
) -> dict[str, Any]:
    timeline = _turn_timeline(turns, tools, events)
    workflow = _workflow(tools)
    return {
        "schema_version": "trace-story-v1",
        "summary": _result_summary(result),
        "terminal_detail": (
            _compact_text(result["terminal_error"].get("message"))
            if isinstance(result["terminal_error"], dict)
            else None
        ),
        "workflow": workflow,
        "observations": _observations(workflow, tools, result),
        "failure_chain": _failure_chain(timeline, events, result),
        "episodes": _episodes(timeline),
        "timeline": timeline,
    }


def _variant_label(manifest: RunManifest) -> str:
    experiment = manifest.experiment
    if experiment and experiment.purpose.value == "rapid-public-development":
        if manifest.tool_schema_version == "v8":
            return "Lean Harness V2"
        if manifest.tool_schema_version == "v7":
            return "Lean Harness"
        if manifest.tool_schema_version == "v2":
            return "Baseline"
    return f"{manifest.tool_schema_version} · {manifest.context_policy_version}"


def _outcome_label(outcome: Any) -> str:
    return {
        "resolved": "성공",
        "task_failure": "평가 실패",
        "agent_failure": "Agent 실패",
        "infrastructure_error": "인프라 오류",
    }.get(str(outcome), str(outcome or "진행 중"))


def build_run_list_view(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        manifest = RunManifest.model_validate(row["manifest"])
        result = row.get("result") if isinstance(row.get("result"), dict) else None
        usage = result.get("usage", {}) if result else {}
        outcome = result.get("outcome_kind") if result else None
        experiment = manifest.experiment
        output.append(
            {
                "run_id": row["run_id"],
                "created_at": row["created_at"],
                "task_id": manifest.task_id,
                "variant": _variant_label(manifest),
                "model": manifest.model.model_id,
                "experiment_id": experiment.experiment_id if experiment else None,
                "purpose": experiment.purpose.value if experiment else None,
                "schedule_order": experiment.schedule_order if experiment else None,
                "repetition": experiment.repetition if experiment else None,
                "outcome": outcome,
                "outcome_label": _outcome_label(outcome),
                "tone": "good" if outcome == "resolved" else "bad" if outcome else "neutral",
                "total_tokens": int(usage.get("input_tokens", 0) or 0)
                + int(usage.get("output_tokens", 0) or 0),
                "cost_usd": Decimal(str(usage.get("model_cost_usd", 0) or 0)),
            }
        )
    return output


def build_run_index_view(rows: list[dict[str, Any]]) -> dict[str, Any]:
    runs = build_run_list_view(rows)
    default_experiment_id = next(
        (
            run["experiment_id"]
            for run in runs
            if run["purpose"] == "rapid-public-development" and run["experiment_id"]
        ),
        None,
    )
    for run in runs:
        run["default_visible"] = (
            not default_experiment_id or run["experiment_id"] == default_experiment_id
        )
    return {
        "schema_version": "trace-index-v2",
        "runs": runs,
        "default_experiment_id": default_experiment_id,
        "default_count": (
            sum(run["experiment_id"] == default_experiment_id for run in runs)
            if default_experiment_id
            else len(runs)
        ),
        "total_count": len(runs),
    }


def build_run_detail_view(
    *,
    row: dict[str, Any],
    manifest: RunManifest,
    events: list[RunEvent],
    runtime: str | Path,
) -> dict[str, Any]:
    """Project only public task, LLM, tool, usage, cost, and result surfaces."""

    runtime_path = Path(runtime).resolve()
    result = row.get("result") if isinstance(row.get("result"), dict) else None
    usage = result.get("usage", {}) if result else {}
    outcome = result.get("outcome_kind") if result else None
    terminal = result.get("terminal_error") if result else None
    verdicts = result.get("verdicts", {}) if result else {}
    experiment = manifest.experiment
    turns = _turns(events, manifest, runtime_path)
    tools = _tools(events, runtime_path)
    public_task = _public_task_view(turns)
    result_view = {
        "outcome": outcome,
        "outcome_label": _outcome_label(outcome),
        "tone": "good" if outcome == "resolved" else "bad" if outcome else "neutral",
        "success": bool(result and result.get("scope_compliant_success")),
        "evaluation_status": result.get("evaluation_status") if result else "not_run",
        "submission_status": result.get("agent_submission_status") if result else "not_run",
        "verdicts": verdicts if isinstance(verdicts, dict) else {},
        "terminal_error": terminal if isinstance(terminal, dict) else None,
    }
    return {
        "raw_render_schema_version": "raw-render-v1",
        "run_id": manifest.run_id,
        "created_at": row.get("created_at"),
        "task": {
            "task_id": manifest.task_id,
            "task_version": manifest.task_version,
            "base_commit": manifest.base_commit,
            "public_spec_hash": manifest.public_spec_hash,
            "variant": _variant_label(manifest),
            "repetition": experiment.repetition if experiment else None,
            "schedule_order": experiment.schedule_order if experiment else None,
            **public_task,
            "description_view": (
                _render_view(public_task["description"])
                if isinstance(public_task["description"], str)
                else None
            ),
        },
        "model": {
            "provider": manifest.model.provider,
            "model_id": manifest.model.model_id,
            "reasoning_effort": manifest.model.reasoning_effort,
            "service_tier": manifest.model.service_tier,
        },
        "usage": {
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "reasoning_tokens": int(usage.get("reasoning_output_tokens", 0) or 0),
            "total_tokens": int(usage.get("input_tokens", 0) or 0)
            + int(usage.get("output_tokens", 0) or 0),
            "model_calls": int(usage.get("model_calls", 0) or 0),
            "tool_calls": int(usage.get("tool_calls", 0) or 0),
            "wall_clock_ms": int(usage.get("wall_clock_ms", 0) or 0),
            "cost_usd": Decimal(str(usage.get("model_cost_usd", 0) or 0)),
        },
        "result": result_view,
        "work_log": _agent_work_log(tools, turns),
        "story": _story_view(turns, tools, events, result_view),
        "turns": turns,
        "tools": tools,
    }


__all__ = [
    "ReadOnlyTraceStore",
    "build_run_detail_view",
    "build_run_index_view",
    "build_run_list_view",
]
