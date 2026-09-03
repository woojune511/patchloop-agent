"""Constrained tools for ``dev-head`` with a single mutation contract."""

from __future__ import annotations

import copy
import fnmatch
import re
import subprocess
import threading
from collections.abc import Sequence
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
    StopIntent,
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
_HUNK_RANGE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_MAX_MUTATION_HUNK_CHARS = 24_000
_MAX_FAILED_MUTATION_DIFF_CHARS = 24_000
_PATCH_ERROR_LINE = re.compile(r"corrupt patch at (?:<stdin>:|line )(\d+)")
_PATCH_SOURCE_LINE = re.compile(r"patch failed: ([^:\r\n]+):(\d+)")


def _public_turn_decision_schema(mode: str) -> dict[str, Any]:
    return {
        "type": "object",
        "description": (
            "The concise public action decision for this tool call; not private data or "
            "chain-of-thought. Parallel reads share inspect mode but may have different "
            "call-specific rationales and evidence goals."
        ),
        "properties": {
            "mode": {"type": "string", "enum": [mode]},
            "basis": {"type": "string", "minLength": 1, "maxLength": 800},
            "evidence_goal": (
                {"type": "string", "minLength": 1, "maxLength": 500}
                if mode == "inspect"
                else {
                    "type": ["string", "null"],
                    "description": "Must be null unless mode is inspect.",
                }
            ),
        },
        "required": ["mode", "basis", "evidence_goal"],
        "additionalProperties": False,
    }


def dev_tool_schemas(
    *,
    finish_enabled: bool,
    check_ids: Sequence[str] = (),
    allowed_tools: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    check_id_schema: dict[str, Any] = {"type": "string", "minLength": 1}
    if check_ids:
        check_id_schema["enum"] = list(check_ids)
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
                "properties": {"check_id": check_id_schema},
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
                "'*** Update File', or another patch wrapper. The minimal plan, current "
                "evidence, and exact current source anchor are part of this mutation. "
                "An accepted mutation's bounded post-image is current evidence for a "
                "same-file repair; there is no separate planning tool."
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
                        "description": (
                            "Current actionable public evidence span IDs only. For a "
                            "same-file repair, use an ID listed in "
                            "last_successful_mutation.actionable_evidence_span_ids; "
                            "earlier pre-image IDs are provenance and do not authorize edits."
                        ),
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
        {
            "type": "function",
            "name": "stop_task",
            "description": (
                "End the run without submission only when no registered read, check, or "
                "safe scoped mutation can make progress. Give a concise public conclusion, "
                "not chain-of-thought."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason_code": {
                        "type": "string",
                        "enum": [
                            "insufficient_public_evidence",
                            "no_safe_scoped_mutation",
                            "public_task_conflict",
                        ],
                    },
                    "summary": {"type": "string", "minLength": 1, "maxLength": 1_000},
                    "evidence_span_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 8,
                    },
                },
                "required": ["reason_code", "summary", "evidence_span_ids"],
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
    decision_modes = {
        "search_files": "inspect",
        "read_file": "inspect",
        "run_check": "verify",
        "apply_git_diff": "mutate",
        "finish_task": "finish",
        "stop_task": "stop",
    }
    enabled = (
        set(allowed_tools)
        if allowed_tools is not None
        else {schema["name"] for schema in schemas}
    )
    unknown = enabled - ALL_DEV_TOOLS
    if unknown:
        raise ContractError(f"unknown tools requested for schema: {sorted(unknown)}")
    projected: list[dict[str, Any]] = []
    for schema in schemas:
        name = schema["name"]
        if name not in enabled:
            continue
        parameters = schema["parameters"]
        parameters["properties"]["turn_decision"] = _public_turn_decision_schema(
            decision_modes[name]
        )
        parameters["required"].append("turn_decision")
        projected.append(schema)
    return projected


def validate_tool_batch(
    calls: list[RequestedTool],
    *,
    max_parallel_reads: int = 4,
    allowed_tools: set[str] | frozenset[str] | None = None,
) -> str:
    """Return ``parallel_read`` or ``single_action``; reject every mixed shape."""

    if not calls:
        raise ContractError("model response must request at least one tool")
    names = [call.name for call in calls]
    action_ids = [call.action_id for call in calls]
    if len(action_ids) != len(set(action_ids)):
        raise ContractError("one model response cannot reuse an action ID")
    if any(name not in ALL_DEV_TOOLS for name in names):
        raise ContractError("model response requested an unknown dev-head tool")
    if allowed_tools is not None and any(name not in allowed_tools for name in names):
        raise ContractError("model response requested a tool unavailable at the current gate")
    if any(call.turn_decision is None for call in calls):
        raise ContractError("every tool call requires one bounded public turn_decision")
    expected_modes = {
        "search_files": "inspect",
        "read_file": "inspect",
        "run_check": "verify",
        "apply_git_diff": "mutate",
        "finish_task": "finish",
        "stop_task": "stop",
    }
    if any(call.turn_decision.mode != expected_modes[call.name] for call in calls):
        raise ContractError("turn_decision mode must match the requested tool family")
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
        self._latest_historical_evidence_span_ids: set[str] = set()
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
                started = mutation_starts.get(result.action_id, {})
                arguments = started.get("arguments", {})
                historical_ids = (
                    arguments.get("evidence_span_ids", [])
                    if isinstance(arguments, dict)
                    else []
                )
                self._accept_successful_mutation(
                    result.output,
                    historical_evidence_span_ids=historical_ids,
                )
                continue
            if result.status != "succeeded":
                continue
            if result.tool in READ_TOOLS:
                self._restore_read_result(result)
            elif result.tool == "run_check":
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

    @staticmethod
    def _cacheable_read_output(output: dict[str, Any]) -> dict[str, Any]:
        cached = copy.deepcopy(output)
        # Older development journals may contain this retired projection field.
        cached.pop("working_state", None)
        return cached

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
            if isinstance(fingerprint, str):
                self._evidence_repetitions[fingerprint] = (
                    self._evidence_repetitions.get(fingerprint, 0) + 1
                )
            if result.workspace_diff_hash is not None:
                read_request_hash = result.output.get("read_request_hash", result.input_hash)
                if isinstance(read_request_hash, str):
                    self._read_cache[
                        self._cache_key(read_request_hash, result.workspace_diff_hash)
                    ] = self._cacheable_read_output(result.output)

    def _restore_mutation_evidence(self, output: dict[str, Any]) -> None:
        span = output.get("mutation_evidence")
        if not isinstance(span, dict) or not isinstance(span.get("span_id"), str):
            return
        with self._lock:
            self._observation_seq += 1
            restored = dict(span)
            restored["last_observed_seq"] = self._observation_seq
            self.spans[restored["span_id"]] = restored

    def _accept_successful_mutation(
        self,
        output: dict[str, Any],
        *,
        historical_evidence_span_ids: Any = (),
    ) -> None:
        self.accepted_mutations += 1
        self.last_successful_mutation = output.get("mutation")
        evidence_values = (
            historical_evidence_span_ids
            if isinstance(historical_evidence_span_ids, (list, tuple, set))
            else ()
        )
        self._latest_historical_evidence_span_ids = {
            span_id
            for span_id in evidence_values
            if isinstance(span_id, str)
        }
        self.last_failed_mutation = None
        self._invalidate_spans(output.get("changed_files", []))
        self._restore_mutation_evidence(output)
        if output.get("alternative_requirement_satisfied") is True:
            self.requires_alternative = False

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
            repetition = self._evidence_repetitions.get(fingerprint, 0) + 1
            self._evidence_repetitions[fingerprint] = repetition
        decorated.update(
            {
                "new_span_count": new_count,
                "read_request_hash": input_hash,
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

    def current_mutation_evidence_paths(self) -> tuple[str, ...]:
        """Return allowed files backed by at least one current public evidence span."""

        with self._lock:
            candidates = sorted(
                (dict(span) for span in self.spans.values()),
                key=lambda span: int(span.get("last_observed_seq", 0)),
                reverse=True,
            )
        current_paths: set[str] = set()
        for span in candidates:
            path = span.get("path")
            file_hash = span.get("file_hash")
            if not isinstance(path, str) or not isinstance(file_hash, str):
                continue
            if not self._path_allowed(path) or path in current_paths:
                continue
            try:
                normalized, current = self._tracked_path(path)
                if sha256_bytes(current.read_bytes()) == file_hash:
                    current_paths.add(normalized)
            except (PatchLoopError, OSError):
                continue
        return tuple(sorted(current_paths))

    def has_current_mutation_evidence(self) -> bool:
        return bool(self.current_mutation_evidence_paths())

    def actionable_last_successful_mutation(self) -> dict[str, Any] | None:
        """Project current repair evidence without stale pre-image identifiers."""

        if not isinstance(self.last_successful_mutation, dict):
            return None
        projected = copy.deepcopy(self.last_successful_mutation)
        projected.pop("evidence_span_ids", None)
        projected.pop("anchor_evidence_span_id", None)
        projected.pop("edit_anchor", None)
        postimage = self._current_postimage_evidence()
        actionable_ids = (
            [str(postimage["span_id"])] if postimage is not None else []
        )
        projected["postimage_evidence_span_id"] = (
            actionable_ids[0] if actionable_ids else None
        )
        projected["actionable_evidence_span_ids"] = actionable_ids
        return projected

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

    def visible_check_status(self) -> list[dict[str, Any]]:
        diff_hash = self.current_diff_hash
        rows = self.checks_by_diff.get(diff_hash, {})
        status: list[dict[str, Any]] = []
        for check in self.public_task.visible_checks:
            row = rows.get(check.id)
            if row is None:
                status.append(
                    {
                        "check_id": check.id,
                        "diff_hash": diff_hash,
                        "status": "NOT_RUN",
                        "failure_signature": None,
                    }
                )
                continue
            status.append(
                {
                    "check_id": check.id,
                    "diff_hash": diff_hash,
                    "status": "PASS" if row.get("passed") is True else "FAIL",
                    "failure_signature": row.get("failure_signature"),
                }
            )
        return status

    def remaining_visible_check_ids(self) -> list[str]:
        return [
            row["check_id"]
            for row in self.visible_check_status()
            if row["status"] != "PASS"
        ]

    def unrun_visible_check_ids(self) -> list[str]:
        return [
            row["check_id"]
            for row in self.visible_check_status()
            if row["status"] == "NOT_RUN"
        ]

    def ready_to_submit(self) -> bool:
        summary = self.current_diff
        return bool(summary.patch) and not summary.untracked_files and self.visible_checks_pass()

    def execute_batch(self, calls: list[RequestedTool]) -> list[DevToolResult]:
        shape = validate_tool_batch(calls, max_parallel_reads=self.limits.max_parallel_reads)
        if shape == "single_action":
            return [self.execute(calls[0])]
        with ThreadPoolExecutor(max_workers=len(calls), thread_name_prefix="dev-read") as pool:
            futures = [pool.submit(self.execute, call) for call in calls]
            return [future.result() for future in futures]

    def execute(self, call: RequestedTool) -> DevToolResult:
        turn_decision = (
            call.turn_decision.model_dump(mode="json")
            if call.turn_decision is not None
            else None
        )
        executable_input = {"tool": call.name, "arguments": call.arguments}
        action_input = dict(executable_input)
        if turn_decision is not None:
            action_input["turn_decision"] = turn_decision
        input_hash = sha256_json(action_input)
        read_request_hash = sha256_json(executable_input)
        replay = self.journal.action_result(call.action_id, input_hash)
        if replay is not None:
            if replay.status == "succeeded" and replay.tool in READ_TOOLS:
                self._restore_read_result(replay)
            return replay
        pending = self.journal.pending_action(call.action_id, input_hash)
        baseline = self.current_diff_hash
        preflight_error: Exception | None = None
        mutation_admitted: bool | None = None
        mutation_anchor_evidence_span_id: str | None = None
        mutation_actionable_evidence_span_ids: list[str] = []
        mutation_ignored_historical_evidence_span_ids: list[str] = []
        if pending is None:
            if call.name == "apply_git_diff":
                try:
                    (
                        _,
                        _,
                        _,
                        mutation_anchor_evidence_span_id,
                        mutation_actionable_evidence_span_ids,
                        mutation_ignored_historical_evidence_span_ids,
                    ) = self._validate_intent(call.arguments)
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
                    "turn_decision": turn_decision,
                    "baseline_diff_hash": baseline,
                    "mutation_admitted": mutation_admitted,
                    "mutation_anchor_evidence_span_id": (
                        mutation_anchor_evidence_span_id
                    ),
                    "mutation_actionable_evidence_span_ids": (
                        mutation_actionable_evidence_span_ids
                    ),
                    "mutation_ignored_historical_evidence_span_ids": (
                        mutation_ignored_historical_evidence_span_ids
                    ),
                },
            )
        try:
            if preflight_error is not None:
                raise preflight_error
            if pending is not None and call.name == "apply_git_diff":
                output = self._reconcile_or_apply(call.arguments, pending)
                evidence_cache_hit = False
            elif call.name in READ_TOOLS:
                cache_key = self._cache_key(read_request_hash, baseline)
                with self._lock:
                    cached = copy.deepcopy(self._read_cache.get(cache_key))
                evidence_cache_hit = cached is not None
                output = cached if cached is not None else self._perform(call.name, call.arguments)
                output = self._decorate_read_output(
                    tool=call.name,
                    input_hash=read_request_hash,
                    workspace_diff_hash=baseline,
                    output=output,
                )
                with self._lock:
                    self._read_cache[cache_key] = self._cacheable_read_output(output)
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
            failure_output = {}
            if call.name in READ_TOOLS:
                failure_output["read_request_hash"] = read_request_hash
            result = DevToolResult(
                action_id=call.action_id,
                input_hash=input_hash,
                tool=call.name,
                status="failed",
                output=failure_output,
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
                self._accept_successful_mutation(
                    result.output,
                    historical_evidence_span_ids=call.arguments.get(
                        "evidence_span_ids", []
                    ),
                )
            elif result.tool == "run_check":
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
        if name == "stop_task":
            return self._stop_task(arguments)
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

    def _current_postimage_evidence(self) -> dict[str, Any] | None:
        latest = self.last_successful_mutation or {}
        expected_span_id = latest.get("postimage_evidence_span_id")
        current_diff_hash = self.current_diff_hash
        if (
            not isinstance(expected_span_id, str)
            or latest.get("diff_hash") != current_diff_hash
        ):
            return None
        with self._lock:
            raw = self.spans.get(expected_span_id)
            span = dict(raw) if isinstance(raw, dict) else None
        if (
            span is None
            or span.get("origin") != "accepted_mutation"
            or span.get("span_id") != expected_span_id
            or span.get("source_diff_hash") != current_diff_hash
            or not isinstance(span.get("path"), str)
            or not isinstance(span.get("content"), str)
            or not isinstance(span.get("file_hash"), str)
        ):
            return None
        try:
            _, current = self._tracked_path(str(span["path"]))
            if sha256_bytes(current.read_bytes()) == span["file_hash"]:
                return span
        except (PatchLoopError, OSError):
            pass
        return None

    def _accepted_mutation_anchor_evidence_id(
        self,
        *,
        anchor_path: str,
        anchor_text: str,
    ) -> str | None:
        span = self._current_postimage_evidence()
        if (
            span is not None
            and span.get("path") == anchor_path
            and anchor_text in str(span["content"])
        ):
            return str(span["span_id"])
        return None

    def _historical_mutation_evidence_ids(self) -> set[str]:
        return set(self._latest_historical_evidence_span_ids)

    def _mutation_postimage_evidence(
        self,
        *,
        path: str,
        changed_hunk: str,
        diff_hash: str,
    ) -> dict[str, Any]:
        normalized, current = self._tracked_path(path)
        raw = current.read_bytes()
        current_lines = raw.decode("utf-8").splitlines()
        hunk_lines = changed_hunk.splitlines()
        match = _HUNK_RANGE.match(hunk_lines[0]) if hunk_lines else None
        if match is None:
            raise RecoveryError("accepted mutation has an invalid changed-hunk range")
        expected_start = max(0, int(match.group(1)) - 1)
        postimage_lines: list[str] = []
        added_offsets: list[int] = []
        for line in hunk_lines[1:]:
            if line.startswith("+"):
                added_offsets.append(len(postimage_lines))
                postimage_lines.append(line[1:])
            elif line.startswith(" "):
                postimage_lines.append(line[1:])

        positions: list[int] = []
        if postimage_lines and len(postimage_lines) <= len(current_lines):
            first_line = postimage_lines[0]
            positions = [
                index
                for index, line in enumerate(current_lines)
                if line == first_line
                and current_lines[index : index + len(postimage_lines)]
                == postimage_lines
            ]
        hunk_start = (
            min(positions, key=lambda value: abs(value - expected_start))
            if positions
            else min(expected_start, max(0, len(current_lines) - 1))
        )
        if not current_lines:
            start_index = 0
            end_index = 0
        elif len(postimage_lines) <= 400:
            start_index = hunk_start
            end_index = min(len(current_lines), hunk_start + max(1, len(postimage_lines)))
        else:
            focus = added_offsets[0] if added_offsets else 0
            relative_start = min(max(0, focus - 200), len(postimage_lines) - 400)
            start_index = min(len(current_lines) - 1, hunk_start + relative_start)
            end_index = min(len(current_lines), start_index + 400)
        content = "\n".join(current_lines[start_index:end_index])[:24_000]
        span = self._span(
            normalized,
            start_index + 1,
            max(start_index + 1, end_index),
            content,
            sha256_bytes(raw),
        )
        return {
            **span,
            "origin": "accepted_mutation",
            "source_diff_hash": diff_hash,
        }

    def _validate_intent(
        self, arguments: dict[str, Any]
    ) -> tuple[str, MutationIntent, list[str], str, list[str], list[str]]:
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
        evidence: list[dict[str, Any]] = []
        ignored_historical_ids: list[str] = []
        historical_ids = self._historical_mutation_evidence_ids()
        with self._lock:
            for span_id in intent.evidence_span_ids:
                span = self.spans.get(span_id)
                if span is None:
                    if span_id in historical_ids:
                        ignored_historical_ids.append(span_id)
                        continue
                    raise ContractError(f"unknown evidence span: {span_id}")
                _, current = self._tracked_path(span["path"])
                if sha256_bytes(current.read_bytes()) != span["file_hash"]:
                    if span_id in historical_ids:
                        ignored_historical_ids.append(span_id)
                        continue
                    raise ContractError(f"evidence span is stale: {span_id}")
                evidence.append(span)
        matching_ids = [
            str(span["span_id"]) for span in evidence if span["path"] == anchor_path
        ]
        anchor_evidence_span_id = matching_ids[0] if matching_ids else None
        if anchor_evidence_span_id is None:
            anchor_evidence_span_id = self._accepted_mutation_anchor_evidence_id(
                anchor_path=anchor_path,
                anchor_text=intent.edit_anchor.old_text,
            )
        if anchor_evidence_span_id is None:
            raise ContractError(
                "at least one current evidence span must cover the edit-anchor file"
            )
        actionable_ids = list(
            dict.fromkeys(
                [
                    *(str(span["span_id"]) for span in evidence),
                    anchor_evidence_span_id,
                ]
            )
        )
        return (
            patch,
            intent,
            paths,
            anchor_evidence_span_id,
            actionable_ids,
            ignored_historical_ids,
        )

    def _mutation_result_output(
        self,
        *,
        patch: str,
        intent: MutationIntent,
        paths: list[str],
        changed_hunk: str,
        summary: Any,
        actionable_evidence_span_ids: list[str],
        ignored_historical_evidence_span_ids: list[str],
        recovered_after_crash: bool = False,
    ) -> dict[str, Any]:
        anchor_path = safe_relative_path(intent.edit_anchor.path)
        postimage_path = ensure_within(self.workspace, anchor_path)
        mutation_evidence = (
            self._mutation_postimage_evidence(
                path=anchor_path,
                changed_hunk=changed_hunk,
                diff_hash=summary.patch_hash,
            )
            if postimage_path.is_file() and not postimage_path.is_symlink()
            else None
        )
        mutation = {
            "hypothesis": intent.hypothesis,
            "expected_behavior": intent.expected_behavior,
            "plan_hash": sha256_json(intent.model_dump(mode="json")),
            "postimage_evidence_span_id": (
                mutation_evidence["span_id"] if mutation_evidence is not None else None
            ),
            "actionable_evidence_span_ids": (
                [str(mutation_evidence["span_id"])]
                if mutation_evidence is not None
                else []
            ),
            "input_evidence_counts": {
                "current": len(actionable_evidence_span_ids),
                "historical_ignored": len(ignored_historical_evidence_span_ids),
            },
            "changed_hunk": changed_hunk,
            "falsified_prior_hypothesis": intent.falsified_prior_hypothesis,
            "alternative_mechanism": intent.alternative_mechanism,
            "changed_files": summary.changed_files,
            "diff_hash": summary.patch_hash,
        }
        output = {
            "patch_hash": sha256_bytes(patch.encode("utf-8")),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": paths,
            "mutation": mutation,
            "mutation_evidence": mutation_evidence,
            "alternative_requirement_satisfied": self.requires_alternative,
        }
        if recovered_after_crash:
            output["recovered_after_crash"] = True
        return output

    def _run_git_apply(self, patch: str, *extra: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "--recount", *extra, "-"],
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
        (
            patch,
            intent,
            paths,
            _,
            actionable_evidence_span_ids,
            ignored_historical_evidence_span_ids,
        ) = self._validate_intent(arguments)
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
        return self._mutation_result_output(
            patch=patch,
            intent=intent,
            paths=paths,
            changed_hunk=changed_hunk,
            summary=summary,
            actionable_evidence_span_ids=actionable_evidence_span_ids,
            ignored_historical_evidence_span_ids=(
                ignored_historical_evidence_span_ids
            ),
        )

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
        anchor_evidence_span_id = pending.get("mutation_anchor_evidence_span_id")
        if not isinstance(anchor_evidence_span_id, str):
            with self._lock:
                anchor_evidence_span_id = next(
                    (
                        span_id
                        for span_id in intent.evidence_span_ids
                        if self.spans.get(span_id, {}).get("path")
                        == safe_relative_path(intent.edit_anchor.path)
                    ),
                    None,
                )
        actionable_evidence_span_ids = pending.get(
            "mutation_actionable_evidence_span_ids"
        )
        if not isinstance(actionable_evidence_span_ids, list) or not all(
            isinstance(span_id, str) for span_id in actionable_evidence_span_ids
        ):
            actionable_evidence_span_ids = [
                span_id
                for span_id in intent.evidence_span_ids
                if isinstance(span_id, str) and span_id in self.spans
            ]
            if isinstance(anchor_evidence_span_id, str):
                actionable_evidence_span_ids = list(
                    dict.fromkeys(
                        [*actionable_evidence_span_ids, anchor_evidence_span_id]
                    )
                )
        ignored_historical_evidence_span_ids = pending.get(
            "mutation_ignored_historical_evidence_span_ids"
        )
        if not isinstance(ignored_historical_evidence_span_ids, list) or not all(
            isinstance(span_id, str)
            for span_id in ignored_historical_evidence_span_ids
        ):
            ignored_historical_evidence_span_ids = []
        return self._mutation_result_output(
            patch=patch,
            intent=intent,
            paths=paths,
            changed_hunk=changed_hunk,
            summary=summary,
            actionable_evidence_span_ids=actionable_evidence_span_ids,
            ignored_historical_evidence_span_ids=(
                ignored_historical_evidence_span_ids
            ),
            recovered_after_crash=True,
        )

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

    def _stop_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        intent = StopIntent.model_validate(arguments)
        unknown = [span_id for span_id in intent.evidence_span_ids if span_id not in self.spans]
        if unknown:
            raise ContractError("stop_task evidence contains an unknown or stale public span")
        return {
            **intent.model_dump(mode="json"),
            "diff_hash": self.current_diff_hash,
        }
