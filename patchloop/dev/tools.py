"""Constrained tools for ``dev-head`` with a single mutation contract."""

from __future__ import annotations

import copy
import fnmatch
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import PublicTask
from patchloop.dev.contracts import (
    DEV_READ_TOOLS,
    DEV_SINGLE_ACTION_TOOLS,
    DevLimits,
    DevToolResult,
    MutationIntent,
    RequestedTool,
)
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, PatchLoopError, RecoveryError
from patchloop.repository import WorkspaceManager
from patchloop.sandbox.runner import Sandbox
from patchloop.util import ensure_within, safe_relative_path, sha256_bytes, sha256_json
from patchloop.verifier.policy import verify_scope

READ_TOOLS = DEV_READ_TOOLS
SINGLE_ACTION_TOOLS = DEV_SINGLE_ACTION_TOOLS
ALL_DEV_TOOLS = READ_TOOLS | SINGLE_ACTION_TOOLS
_PATCH_PATH = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)
_MAX_MUTATION_HUNK_CHARS = 24_000
_MAX_FAILED_MUTATION_DIFF_CHARS = 24_000
_PATCH_ERROR_LINE = re.compile(r"corrupt patch at (?:<stdin>:|line )(\d+)")
_PATCH_SOURCE_LINE = re.compile(r"patch failed: ([^:\r\n]+):(\d+)")


def dev_tool_schemas(*, finish_enabled: bool) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = [
        {
            "type": "function",
            "name": "search_files",
            "description": (
                "Search tracked public repository text and return bounded evidence spans."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "path_glob": {"type": "string", "default": "**/*"},
                },
                "required": ["query", "path_glob"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "read_file",
            "description": "Read one bounded line range from a tracked public source file.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "start_line": {"type": "integer", "minimum": 1},
                    "end_line": {"type": "integer", "minimum": 1},
                },
                "required": ["path", "start_line", "end_line"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "run_check",
            "description": "Run exactly one public registered check against the current diff.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"check_id": {"type": "string", "minLength": 1}},
                "required": ["check_id"],
                "additionalProperties": False,
            },
        },
        {
            "type": "function",
            "name": "apply_git_diff",
            "description": (
                "Apply one scoped raw Git unified diff. git_diff must begin exactly with "
                "'diff --git a/<path> b/<path>'. Never use '*** Begin Patch', "
                "'*** Update File', or another patch wrapper. The minimal plan, fresh "
                "evidence, and exact current source anchor are part of this mutation; "
                "there is no separate planning tool."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "git_diff": {
                        "type": "string",
                        "minLength": 1,
                        "pattern": "^diff --git a/",
                        "description": (
                            "Raw Git unified diff starting with "
                            "'diff --git a/<path> b/<path>'; no patch wrapper markers."
                        ),
                    },
                    "hypothesis": {"type": "string", "minLength": 1},
                    "expected_behavior": {"type": "string", "minLength": 1},
                    "evidence_span_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 8,
                    },
                    "edit_anchor": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "minLength": 1},
                            "old_text": {"type": "string", "minLength": 1},
                            "occurrence": {"type": "integer", "minimum": 1},
                        },
                        "required": ["path", "old_text", "occurrence"],
                        "additionalProperties": False,
                    },
                    "falsified_prior_hypothesis": {"type": ["string", "null"]},
                    "alternative_mechanism": {"type": ["string", "null"]},
                },
                "required": [
                    "git_diff",
                    "hypothesis",
                    "expected_behavior",
                    "evidence_span_ids",
                    "edit_anchor",
                    "falsified_prior_hypothesis",
                    "alternative_mechanism",
                ],
                "additionalProperties": False,
            },
        },
    ]
    if finish_enabled:
        schemas.append(
            {
                "type": "function",
                "name": "finish_task",
                "description": (
                    "Submit the automatically projected current diff after all checks pass."
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            }
        )
    return schemas


def validate_tool_batch(calls: list[RequestedTool], *, max_parallel_reads: int = 4) -> str:
    """Return ``parallel_read`` or ``single_action``; reject every mixed shape."""

    if not calls:
        raise ContractError("model response must request at least one tool")
    names = [call.name for call in calls]
    action_ids = [call.action_id for call in calls]
    if len(action_ids) != len(set(action_ids)):
        raise ContractError("one model response cannot reuse an action ID")
    if any(name not in ALL_DEV_TOOLS for name in names):
        raise ContractError("model response requested an unknown dev-head tool")
    if all(name in READ_TOOLS for name in names):
        if len(calls) > max_parallel_reads:
            raise ContractError(f"a read batch may contain at most {max_parallel_reads} calls")
        return "parallel_read"
    if len(calls) == 1 and names[0] in SINGLE_ACTION_TOOLS:
        return "single_action"
    raise ContractError(
        "a response must contain only up to four reads/searches or exactly one action"
    )


class DevToolGateway:
    def __init__(
        self,
        *,
        workspace: Path,
        public_task: PublicTask,
        sandbox: Sandbox,
        journal: DevJournal,
        limits: DevLimits,
    ) -> None:
        self.workspace = workspace.resolve()
        self.public_task = public_task
        self.sandbox = sandbox
        self.journal = journal
        self.limits = limits
        self._lock = threading.RLock()
        self.spans: dict[str, dict[str, Any]] = {}
        self._observation_seq = 0
        self._read_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._evidence_repetitions: dict[str, int] = {}
        self.checks_by_diff: dict[str, dict[str, dict[str, Any]]] = {}
        self.failure_diffs: dict[str, set[str]] = {}
        self.requires_alternative = False
        self.accepted_mutations = 0
        self.last_successful_mutation: dict[str, Any] | None = None
        self.last_failed_mutation: dict[str, Any] | None = None
        self._hydrate()

    def _hydrate(self) -> None:
        mutation_starts: dict[str, dict[str, Any]] = {}
        for event in self.journal.events():
            if event["event_type"] == "action_started":
                payload = event["payload"]
                if payload.get("tool") == "apply_git_diff" and isinstance(
                    payload.get("action_id"), str
                ):
                    mutation_starts[payload["action_id"]] = payload
                continue
            if event["event_type"] != "action_finished":
                continue
            result = DevToolResult.model_validate(event["payload"]["result"])
            if result.tool == "apply_git_diff":
                if result.status == "failed":
                    started = mutation_starts.get(result.action_id)
                    if started is not None and isinstance(started.get("arguments"), dict):
                        self.last_failed_mutation = self._failed_mutation_context(
                            arguments=started["arguments"],
                            action_id=result.action_id,
                            input_hash=result.input_hash,
                            baseline_diff_hash=started.get("baseline_diff_hash"),
                            result=result,
                        )
                    continue
                self.accepted_mutations += 1
                self.last_successful_mutation = result.output.get("mutation")
                self.last_failed_mutation = None
                self._invalidate_spans(result.output.get("changed_files", []))
                if result.output.get("alternative_requirement_satisfied") is True:
                    self.requires_alternative = False
                continue
            if result.status != "succeeded":
                continue
            if result.tool in READ_TOOLS:
                self._restore_read_result(result)
            elif result.tool == "run_check":
                self._reset_evidence_progress()
                self._remember_check(result.output)

    @staticmethod
    def _bounded_string(value: Any, limit: int) -> str | None:
        return value[:limit] if isinstance(value, str) else None

    @staticmethod
    def _mutation_error_location(message: str | None) -> dict[str, Any] | None:
        if not message:
            return None
        patch_line = _PATCH_ERROR_LINE.search(message)
        if patch_line is not None:
            return {"patch_line": int(patch_line.group(1))}
        source_line = _PATCH_SOURCE_LINE.search(message)
        if source_line is not None:
            return {"path": source_line.group(1), "line": int(source_line.group(2))}
        return None

    @classmethod
    def _failed_mutation_context(
        cls,
        *,
        arguments: dict[str, Any],
        action_id: str,
        input_hash: str,
        baseline_diff_hash: Any,
        result: DevToolResult,
    ) -> dict[str, Any]:
        patch = arguments.get("git_diff")
        patch_text = patch if isinstance(patch, str) else None
        anchor_value = arguments.get("edit_anchor")
        anchor = None
        if isinstance(anchor_value, dict):
            occurrence = anchor_value.get("occurrence")
            anchor = {
                "path": cls._bounded_string(anchor_value.get("path"), 1_000),
                "old_text": cls._bounded_string(anchor_value.get("old_text"), 20_000),
                "occurrence": occurrence
                if type(occurrence) is int and 1 <= occurrence <= 100
                else None,
            }
        evidence_span_ids = arguments.get("evidence_span_ids")
        if not isinstance(evidence_span_ids, list):
            evidence_span_ids = []
        return {
            "action_id": action_id,
            "input_hash": input_hash,
            "baseline_diff_hash": (
                baseline_diff_hash if isinstance(baseline_diff_hash, str) else None
            ),
            "git_diff": (
                patch_text[:_MAX_FAILED_MUTATION_DIFF_CHARS]
                if patch_text is not None
                else None
            ),
            "git_diff_hash": (
                sha256_bytes(patch_text.encode("utf-8")) if patch_text is not None else None
            ),
            "git_diff_truncated": (
                len(patch_text) > _MAX_FAILED_MUTATION_DIFF_CHARS
                if patch_text is not None
                else False
            ),
            "hypothesis": cls._bounded_string(arguments.get("hypothesis"), 1_500),
            "expected_behavior": cls._bounded_string(
                arguments.get("expected_behavior"), 1_500
            ),
            "evidence_span_ids": [
                value[:500]
                for value in evidence_span_ids[:8]
                if isinstance(value, str)
            ],
            "edit_anchor": anchor,
            "falsified_prior_hypothesis": cls._bounded_string(
                arguments.get("falsified_prior_hypothesis"), 1_500
            ),
            "alternative_mechanism": cls._bounded_string(
                arguments.get("alternative_mechanism"), 1_500
            ),
            "error_code": result.error_code,
            "error_message": result.message,
            "error_location": cls._mutation_error_location(result.message),
            "next_action": (
                "Repair or explicitly replace this failed mutation. Use read/search only "
                "when needed for that repair."
            ),
        }

    @staticmethod
    def _cache_key(input_hash: str, workspace_diff_hash: str) -> tuple[str, str]:
        return input_hash, workspace_diff_hash

    def _reset_evidence_progress(self) -> None:
        with self._lock:
            self._evidence_repetitions.clear()

    def _restore_read_result(self, result: DevToolResult) -> None:
        spans = result.output.get("spans", [])
        with self._lock:
            for span in spans:
                if not isinstance(span, dict) or not isinstance(span.get("span_id"), str):
                    continue
                self._observation_seq += 1
                restored = dict(span)
                restored["last_observed_seq"] = self._observation_seq
                self.spans[restored["span_id"]] = restored
            fingerprint = result.output.get("evidence_fingerprint")
            if result.output.get("new_span_count", 0):
                self._evidence_repetitions.clear()
            if isinstance(fingerprint, str):
                self._evidence_repetitions[fingerprint] = (
                    self._evidence_repetitions.get(fingerprint, 0) + 1
                )
            if result.workspace_diff_hash is not None:
                self._read_cache[self._cache_key(result.input_hash, result.workspace_diff_hash)] = (
                    copy.deepcopy(result.output)
                )

    def _decorate_read_output(
        self,
        *,
        tool: str,
        input_hash: str,
        workspace_diff_hash: str,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        decorated = copy.deepcopy(output)
        spans = decorated.get("spans", [])
        with self._lock:
            new_count = 0
            span_ids: list[str] = []
            for span in spans:
                if not isinstance(span, dict) or not isinstance(span.get("span_id"), str):
                    continue
                span_id = span["span_id"]
                span_ids.append(span_id)
                if span_id not in self.spans:
                    new_count += 1
                self._observation_seq += 1
                span["last_observed_seq"] = self._observation_seq
                self.spans[span_id] = dict(span)
            fingerprint = sha256_json(
                {
                    "tool": tool,
                    "input_hash": input_hash,
                    "workspace_diff_hash": workspace_diff_hash,
                    "span_ids": span_ids,
                }
            )
            if new_count:
                self._evidence_repetitions.clear()
            repetition = self._evidence_repetitions.get(fingerprint, 0) + 1
            self._evidence_repetitions[fingerprint] = repetition
        decorated.update(
            {
                "new_span_count": new_count,
                "evidence_fingerprint": fingerprint,
                "evidence_repetition": repetition,
                "stagnation_signal": repetition >= 2 and new_count == 0,
            }
        )
        return decorated

    def _invalidate_spans(self, paths: list[str]) -> None:
        changed = {str(path).replace("\\", "/") for path in paths}
        with self._lock:
            self.spans = {
                span_id: span
                for span_id, span in self.spans.items()
                if span.get("path") not in changed
            }
            self._read_cache.clear()
            self._evidence_repetitions.clear()

    def context_spans(self, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
        excluded = exclude or set()
        with self._lock:
            candidates = [
                dict(span) for span_id, span in self.spans.items() if span_id not in excluded
            ]
        candidates.sort(key=lambda span: int(span.get("last_observed_seq", 0)), reverse=True)
        return candidates[:8]

    @property
    def current_diff(self):
        return WorkspaceManager.diff_summary(self.workspace)

    @property
    def current_diff_hash(self) -> str:
        return self.current_diff.patch_hash

    def visible_checks_pass(self) -> bool:
        expected = {check.id for check in self.public_task.visible_checks}
        if not expected:
            return bool(self.current_diff.patch)
        rows = self.checks_by_diff.get(self.current_diff_hash, {})
        return expected == {check_id for check_id, row in rows.items() if row.get("passed") is True}

    def execute_batch(self, calls: list[RequestedTool]) -> list[DevToolResult]:
        shape = validate_tool_batch(calls, max_parallel_reads=self.limits.max_parallel_reads)
        if shape == "single_action":
            return [self.execute(calls[0])]
        with ThreadPoolExecutor(max_workers=len(calls), thread_name_prefix="dev-read") as pool:
            futures = [pool.submit(self.execute, call) for call in calls]
            return [future.result() for future in futures]

    def execute(self, call: RequestedTool) -> DevToolResult:
        input_hash = sha256_json({"tool": call.name, "arguments": call.arguments})
        replay = self.journal.action_result(call.action_id, input_hash)
        if replay is not None:
            if replay.status == "succeeded" and replay.tool in READ_TOOLS:
                self._restore_read_result(replay)
            return replay
        pending = self.journal.pending_action(call.action_id, input_hash)
        baseline = self.current_diff_hash
        preflight_error: Exception | None = None
        mutation_admitted: bool | None = None
        if pending is None:
            if call.name == "apply_git_diff":
                try:
                    self._validate_intent(call.arguments)
                    mutation_admitted = True
                except (PatchLoopError, ValidationError, ValueError, OSError) as exc:
                    preflight_error = exc
                    mutation_admitted = False
            self.journal.append(
                "action_started",
                {
                    "action_id": call.action_id,
                    "input_hash": input_hash,
                    "tool": call.name,
                    "arguments": call.arguments,
                    "baseline_diff_hash": baseline,
                    "mutation_admitted": mutation_admitted,
                },
            )
        try:
            if preflight_error is not None:
                raise preflight_error
            if pending is not None and call.name == "apply_git_diff":
                output = self._reconcile_or_apply(call.arguments, pending)
                evidence_cache_hit = False
            elif call.name in READ_TOOLS:
                cache_key = self._cache_key(input_hash, baseline)
                with self._lock:
                    cached = copy.deepcopy(self._read_cache.get(cache_key))
                evidence_cache_hit = cached is not None
                output = cached if cached is not None else self._perform(call.name, call.arguments)
                output = self._decorate_read_output(
                    tool=call.name,
                    input_hash=input_hash,
                    workspace_diff_hash=baseline,
                    output=output,
                )
                with self._lock:
                    self._read_cache[cache_key] = copy.deepcopy(output)
            else:
                output = self._perform(call.name, call.arguments)
                evidence_cache_hit = False
            result = DevToolResult(
                action_id=call.action_id,
                input_hash=input_hash,
                tool=call.name,
                status="succeeded",
                output=output,
                evidence_cache_hit=evidence_cache_hit,
                workspace_diff_hash=baseline,
            )
        except (PatchLoopError, ValidationError, ValueError, OSError, RuntimeError) as exc:
            code = exc.code if isinstance(exc, PatchLoopError) else "TOOL_CONTRACT_ERROR"
            result = DevToolResult(
                action_id=call.action_id,
                input_hash=input_hash,
                tool=call.name,
                status="failed",
                error_code=code,
                message=str(exc)[:1_000],
            )
        self.journal.append(
            "action_finished",
            {
                "action_id": call.action_id,
                "input_hash": input_hash,
                "result": result.model_dump(mode="json"),
            },
        )
        if result.status == "succeeded":
            if result.tool == "apply_git_diff":
                self.accepted_mutations += 1
                self.last_successful_mutation = result.output["mutation"]
                self.last_failed_mutation = None
                self._invalidate_spans(result.output.get("changed_files", []))
                if result.output.get("alternative_requirement_satisfied") is True:
                    self.requires_alternative = False
            elif result.tool == "run_check":
                self._reset_evidence_progress()
                self._remember_check(result.output)
        elif result.tool == "apply_git_diff":
            self.last_failed_mutation = self._failed_mutation_context(
                arguments=call.arguments,
                action_id=result.action_id,
                input_hash=result.input_hash,
                baseline_diff_hash=baseline,
                result=result,
            )
        return result

    def _perform(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "read_file":
            return self._read_file(**arguments)
        if name == "search_files":
            return self._search_files(**arguments)
        if name == "apply_git_diff":
            return self._apply_git_diff(arguments)
        if name == "run_check":
            return self._run_check(**arguments)
        if name == "finish_task":
            return self._finish_task(arguments)
        raise ContractError(f"unknown dev-head tool: {name}")

    def _tracked_path(self, relative: str) -> tuple[str, Path]:
        normalized = safe_relative_path(relative)
        if normalized.startswith(".patchloop-hidden/"):
            raise ContractError("private evaluator paths are never agent-readable")
        path = ensure_within(self.workspace, normalized)
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", normalized],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if tracked.returncode != 0 or not path.is_file() or path.is_symlink():
            raise ContractError(f"path is not a tracked public file: {normalized}")
        return normalized, path

    @staticmethod
    def _span(path: str, start: int, end: int, content: str, file_hash: str) -> dict[str, Any]:
        identity = {
            "path": path,
            "start_line": start,
            "end_line": end,
            "content": content,
            "file_hash": file_hash,
        }
        return {"span_id": f"span_{sha256_json(identity).split(':', 1)[1][:16]}", **identity}

    def _read_file(self, path: str, start_line: int, end_line: int) -> dict[str, Any]:
        if type(start_line) is not int or type(end_line) is not int:
            raise ContractError("read_file line bounds must be integers")
        if start_line < 1 or end_line < start_line or end_line - start_line + 1 > 400:
            raise ContractError("read_file accepts a 1-400 line inclusive range")
        normalized, selected = self._tracked_path(path)
        raw = selected.read_bytes()
        if len(raw) > 2_000_000:
            raise ContractError("read_file refuses files larger than 2 MB")
        text = raw.decode("utf-8")
        lines = text.splitlines()
        actual_end = min(end_line, len(lines))
        content = "\n".join(lines[start_line - 1 : actual_end])
        span = self._span(normalized, start_line, actual_end, content[:24_000], sha256_bytes(raw))
        return {
            "path": normalized,
            "start_line": start_line,
            "end_line": actual_end,
            "spans": [span],
            "line_count": len(lines),
        }

    def _search_files(self, query: str, path_glob: str = "**/*") -> dict[str, Any]:
        if not isinstance(query, str) or not query or len(query) > 500:
            raise ContractError("search query must contain 1-500 characters")
        pattern = safe_relative_path(path_glob, field_name="search path_glob")
        spans: list[dict[str, Any]] = []
        for selected in sorted(self.workspace.rglob("*")):
            if len(spans) >= 20 or not selected.is_file() or selected.is_symlink():
                continue
            relative = selected.relative_to(self.workspace).as_posix()
            if ".git" in selected.relative_to(self.workspace).parts:
                continue
            if relative.startswith(".patchloop-hidden/") or not fnmatch.fnmatchcase(
                relative, pattern
            ):
                continue
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", relative],
                cwd=self.workspace,
                capture_output=True,
                check=False,
            )
            if tracked.returncode != 0 or selected.stat().st_size > 1_000_000:
                continue
            try:
                raw = selected.read_bytes()
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            lines = text.splitlines()
            for index, line in enumerate(lines, start=1):
                if query not in line:
                    continue
                start = max(1, index - 2)
                end = min(len(lines), index + 2)
                content = "\n".join(lines[start - 1 : end])
                spans.append(self._span(relative, start, end, content, sha256_bytes(raw)))
                if len(spans) >= 20:
                    break
        return {
            "query": query,
            "path_glob": pattern,
            "spans": spans,
            "truncated": len(spans) >= 20,
        }

    def _patch_paths(self, patch: str) -> list[str]:
        if not isinstance(patch, str) or not patch.startswith("diff --git "):
            raise ContractError(
                "apply_git_diff git_diff must begin exactly with "
                "'diff --git a/<path> b/<path>'; patch wrapper markers are not accepted"
            )
        matches = _PATCH_PATH.findall(patch)
        if not matches:
            raise ContractError("apply_git_diff has no Git diff header")
        paths: list[str] = []
        for before, after in matches:
            if before != after:
                raise ContractError("renames and copies are not allowed")
            paths.append(safe_relative_path(after, field_name="patch path"))
        return sorted(set(paths))

    def _path_allowed(self, path: str) -> bool:
        constraints = self.public_task.constraints
        return any(
            fnmatch.fnmatchcase(path, item) for item in constraints.allowed_paths
        ) and not any(fnmatch.fnmatchcase(path, item) for item in constraints.forbidden_paths)

    @staticmethod
    def _changed_hunk(patch: str, path: str, anchor: str) -> str:
        lines = patch.splitlines(keepends=True)
        header = f"diff --git a/{path} b/{path}"
        try:
            section_start = next(
                index for index, line in enumerate(lines) if line.rstrip("\r\n") == header
            )
        except StopIteration as exc:
            raise ContractError("edit-anchor path has no matching Git diff section") from exc
        section_end = next(
            (
                index
                for index in range(section_start + 1, len(lines))
                if lines[index].startswith("diff --git ")
            ),
            len(lines),
        )
        starts = [
            index for index in range(section_start, section_end) if lines[index].startswith("@@ ")
        ]
        if not starts:
            raise ContractError("edit-anchor path has no changed hunk")
        candidates: list[str] = []
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else section_end
            hunk_lines = lines[start:end]
            hunk = "".join(hunk_lines)
            preimage = "".join(
                line[1:]
                for line in hunk_lines[1:]
                if line.startswith((" ", "-")) and not line.startswith("---")
            )
            candidates.append(hunk)
            if anchor in preimage:
                break
        else:
            hunk = candidates[0]
        if len(hunk) > _MAX_MUTATION_HUNK_CHARS:
            raise ContractError("changed hunk exceeds the bounded mutation context limit")
        return hunk

    def _validate_intent(self, arguments: dict[str, Any]) -> tuple[str, MutationIntent, list[str]]:
        patch = arguments.get("git_diff")
        if not isinstance(patch, str):
            raise ContractError("apply_git_diff git_diff must be a string")
        intent = MutationIntent.model_validate(
            {key: value for key, value in arguments.items() if key != "git_diff"}
        )
        if self.requires_alternative and (
            intent.falsified_prior_hypothesis is None or intent.alternative_mechanism is None
        ):
            raise ContractError(
                "repeated public failure across two diffs requires falsified_prior_hypothesis "
                "and alternative_mechanism on the next mutation"
            )
        paths = self._patch_paths(patch)
        if any(not self._path_allowed(path) for path in paths):
            raise ContractError("patch changes a path outside the public task allowance")
        for path in paths:
            self._tracked_path(path)
        anchor_path, anchor_file = self._tracked_path(intent.edit_anchor.path)
        if anchor_path not in paths:
            raise ContractError("exact edit anchor must belong to a patched file")
        anchor_text = anchor_file.read_text(encoding="utf-8")
        positions = [
            match.start()
            for match in re.finditer(re.escape(intent.edit_anchor.old_text), anchor_text)
        ]
        if len(positions) < intent.edit_anchor.occurrence:
            raise ContractError("exact edit anchor is stale or absent from the current source")
        evidence = []
        with self._lock:
            for span_id in intent.evidence_span_ids:
                span = self.spans.get(span_id)
                if span is None:
                    raise ContractError(f"unknown evidence span: {span_id}")
                _, current = self._tracked_path(span["path"])
                if sha256_bytes(current.read_bytes()) != span["file_hash"]:
                    raise ContractError(f"evidence span is stale: {span_id}")
                evidence.append(span)
        if anchor_path not in {span["path"] for span in evidence}:
            raise ContractError(
                "at least one current evidence span must cover the edit-anchor file"
            )
        return patch, intent, paths

    def _run_git_apply(self, patch: str, *extra: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "apply", "--whitespace=nowarn", *extra, "-"],
            cwd=self.workspace,
            input=patch.encode("utf-8"),
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _git_apply_error(result: subprocess.CompletedProcess[bytes]) -> str:
        return result.stderr.decode("utf-8", errors="replace").strip()[:800]

    def _apply_git_diff(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.accepted_mutations >= self.limits.max_accepted_mutations:
            raise ContractError("accepted mutation limit reached")
        patch, intent, paths = self._validate_intent(arguments)
        changed_hunk = self._changed_hunk(
            patch,
            safe_relative_path(intent.edit_anchor.path),
            intent.edit_anchor.old_text,
        )
        checked = self._run_git_apply(patch, "--check")
        if checked.returncode != 0:
            raise ContractError(f"git apply check failed: {self._git_apply_error(checked)}")
        applied = self._run_git_apply(patch)
        if applied.returncode != 0:
            raise ContractError(f"git apply failed: {self._git_apply_error(applied)}")
        summary = self.current_diff
        scope = verify_scope(summary, self.public_task.constraints)
        if not scope.passed:
            reverted = self._run_git_apply(patch, "--reverse")
            if reverted.returncode != 0:
                raise RecoveryError("out-of-scope mutation could not be rolled back safely")
            raise ContractError("mutation violates allowed paths or diff-size constraints")
        mutation = {
            "hypothesis": intent.hypothesis,
            "expected_behavior": intent.expected_behavior,
            "plan_hash": sha256_json(intent.model_dump(mode="json")),
            "evidence_span_ids": intent.evidence_span_ids,
            "edit_anchor": intent.edit_anchor.model_dump(mode="json"),
            "changed_hunk": changed_hunk,
            "falsified_prior_hypothesis": intent.falsified_prior_hypothesis,
            "alternative_mechanism": intent.alternative_mechanism,
            "changed_files": summary.changed_files,
            "diff_hash": summary.patch_hash,
        }
        return {
            "patch_hash": sha256_bytes(patch.encode("utf-8")),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": paths,
            "mutation": mutation,
            "alternative_requirement_satisfied": self.requires_alternative,
        }

    def _reconcile_or_apply(
        self, arguments: dict[str, Any], pending: dict[str, Any]
    ) -> dict[str, Any]:
        baseline = pending.get("baseline_diff_hash")
        current = self.current_diff_hash
        if current == baseline:
            return self._apply_git_diff(arguments)
        if pending.get("mutation_admitted") is not True:
            raise RecoveryError("pending mutation was not admitted before the crash")
        patch = arguments.get("git_diff")
        if not isinstance(patch, str):
            raise RecoveryError("pending mutation patch is invalid")
        intent = MutationIntent.model_validate(
            {key: value for key, value in arguments.items() if key != "git_diff"}
        )
        paths = self._patch_paths(patch)
        changed_hunk = self._changed_hunk(
            patch,
            safe_relative_path(intent.edit_anchor.path),
            intent.edit_anchor.old_text,
        )
        reverse_check = self._run_git_apply(patch, "--reverse", "--check")
        if reverse_check.returncode != 0:
            raise RecoveryError("pending mutation cannot be reconciled with the current workspace")
        summary = self.current_diff
        mutation = {
            "hypothesis": intent.hypothesis,
            "expected_behavior": intent.expected_behavior,
            "plan_hash": sha256_json(intent.model_dump(mode="json")),
            "evidence_span_ids": intent.evidence_span_ids,
            "edit_anchor": intent.edit_anchor.model_dump(mode="json"),
            "changed_hunk": changed_hunk,
            "falsified_prior_hypothesis": intent.falsified_prior_hypothesis,
            "alternative_mechanism": intent.alternative_mechanism,
            "changed_files": summary.changed_files,
            "diff_hash": summary.patch_hash,
        }
        return {
            "patch_hash": sha256_bytes(patch.encode("utf-8")),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": paths,
            "mutation": mutation,
            "recovered_after_crash": True,
            "alternative_requirement_satisfied": self.requires_alternative,
        }

    def _run_check(self, check_id: str) -> dict[str, Any]:
        checks = {check.id: check for check in self.public_task.visible_checks}
        try:
            check = checks[check_id]
        except KeyError as exc:
            raise ContractError(f"unknown public check: {check_id}") from exc
        diff_hash = self.current_diff_hash
        outcome = self.sandbox.run_check(self.workspace, check)
        passed = not outcome.timed_out and outcome.exit_code in check.expected_exit_codes
        execution_policy_hash = (
            sha256_json(outcome.execution_policy)
            if outcome.execution_policy is not None
            else None
        )
        signature = sha256_json(
            {
                "check_id": check_id,
                "exit_code": outcome.exit_code,
                "timed_out": outcome.timed_out,
                "stdout": outcome.stdout[-8_000:],
                "stderr": outcome.stderr[-8_000:],
            }
        )
        return {
            "check_id": check_id,
            "diff_hash": diff_hash,
            "passed": passed,
            "failure_signature": None if passed else signature,
            "exit_code": outcome.exit_code,
            "timed_out": outcome.timed_out,
            "truncated": outcome.truncated,
            "stdout": outcome.stdout[-12_000:],
            "stderr": outcome.stderr[-12_000:],
            "execution_policy": outcome.execution_policy,
            "execution_policy_hash": execution_policy_hash,
        }

    def _remember_check(self, output: dict[str, Any]) -> None:
        diff_hash = str(output["diff_hash"])
        check_id = str(output["check_id"])
        self.checks_by_diff.setdefault(diff_hash, {})[check_id] = output
        signature = output.get("failure_signature")
        if isinstance(signature, str):
            diffs = self.failure_diffs.setdefault(signature, set())
            diffs.add(diff_hash)
            if len(diffs) >= 2:
                self.requires_alternative = True

    def _finish_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise ContractError("finish_task accepts no arguments")
        summary = self.current_diff
        if not summary.patch:
            raise ContractError("cannot submit an empty diff")
        if summary.untracked_files:
            raise ContractError(
                "cannot submit with untracked files: " + ", ".join(summary.untracked_files)
            )
        if not self.visible_checks_pass():
            raise ContractError("all visible checks must pass against the current diff")
        return {
            "patch": summary.patch,
            "patch_hash": summary.patch_hash,
            "changed_files": summary.changed_files,
            "added_lines": summary.added_lines,
            "deleted_lines": summary.deleted_lines,
            "untracked_files": summary.untracked_files,
        }
