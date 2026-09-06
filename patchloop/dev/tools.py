"""Constrained tools for ``dev-head`` with a single mutation contract."""

from __future__ import annotations

import copy
import difflib
import fnmatch
import re
import subprocess
import threading
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from patchloop.contracts import PublicTask, RegisteredCheck
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev.context import (
    SourceProjection,
    bounded_lines,
    project_observed_sources,
    source_lines,
    spans_cover_range,
    valid_observed_span,
)
from patchloop.dev.contracts import (
    DEV_READ_TOOLS,
    DEV_SINGLE_ACTION_TOOLS,
    DevLimits,
    DevToolResult,
    RequestedTool,
    StopIntent,
    TextReplacementIntent,
)
from patchloop.dev.source_glob import matches_source_glob
from patchloop.dev.source_rebinding import SourceReplacement
from patchloop.dev.state import DevJournal
from patchloop.dev.verification_concerns import (
    empty_verification_state,
    project_verification_concerns,
    update_verification_concerns,
)
from patchloop.dev.working_notes import (
    SourceNoteEvidence,
    WorkingNotesUpdate,
    check_note_result,
    memory_update_schema,
    note_feedback,
    source_note_range_details,
)
from patchloop.errors import ContractError, PatchLoopError, RecoveryError
from patchloop.repository import DiffSummary, WorkspaceManager
from patchloop.sandbox.probes import DockerProbeSandbox
from patchloop.sandbox.runner import Sandbox
from patchloop.util import ensure_within, safe_relative_path, sha256_bytes, sha256_json
from patchloop.verifier.policy import verify_scope

READ_TOOLS = DEV_READ_TOOLS
SINGLE_ACTION_TOOLS = DEV_SINGLE_ACTION_TOOLS
ALL_DEV_TOOLS = READ_TOOLS | SINGLE_ACTION_TOOLS
_MAX_MUTATION_HUNK_CHARS = 24_000
_MAX_NOTE_SOURCE_BODY_CHARS = 24_000
_PATCH_ERROR_LINE = re.compile(r"corrupt patch at (?:<stdin>:|line )(\d+)")
_PATCH_SOURCE_LINE = re.compile(r"patch failed: ([^:\r\n]+):(\d+)")
_INLINE_PYTHON = re.compile(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", re.IGNORECASE)
_INLINE_PYTHON_FRAME = re.compile(
    r'File "<string>", line (?P<line>\d+)(?:, in (?P<scope>[^\r\n]+))?'
)
_TRACEBACK_EXCEPTION = re.compile(r"^(?P<type>[A-Za-z_][A-Za-z0-9_.]*)(?::.*)?$")
_MUTATION_TOOLS = frozenset({"replace_text", "apply_git_diff"})


@dataclass(frozen=True)
class _ValidatedReplacement:
    intent: TextReplacementIntent
    path: str
    before_bytes: bytes
    after_bytes: bytes
    generated_patch: str
    anchor_offset: int
    anchor_start_line: int
    anchor_end_line: int
    postimage_start_line: int
    anchor_evidence_span_id: str
    anchor_evidence_span_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DevGatewayStateSnapshot:
    """One coherent public workspace observation for a model-turn decision."""

    diff: DiffSummary
    mutation_evidence_paths: tuple[str, ...]
    evidence_paths: tuple[str, ...]
    visible_check_status: tuple[dict[str, Any], ...]
    remaining_visible_check_ids: tuple[str, ...]
    unrun_visible_check_ids: tuple[str, ...]
    ready_to_submit: bool


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
                    "type": "null",
                    "description": "Exactly null unless mode is inspect.",
                }
            ),
            "memory_update": memory_update_schema(),
        },
        "required": ["mode", "basis", "evidence_goal", "memory_update"],
        "additionalProperties": False,
    }


def dev_tool_schemas(
    *,
    finish_enabled: bool,
    check_ids: Sequence[str] = (),
    allowed_tools: Sequence[str] | None = None,
    read_paths: Sequence[str] = (),
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
                    "path_glob": {
                        "type": "string", "default": "**/*",
                        "description": (
                            "Case-sensitive repository-rooted path glob. * and ? stay within "
                            "one path component; a whole ** matches zero or more directories. "
                            "**/* includes root files. Query matching is literal text."
                        ),
                    },
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
                    "path": {
                        "type": "string",
                        "minLength": 1,
                        **({"enum": list(read_paths)} if read_paths else {}),
                    },
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
            "name": "replace_text",
            "description": (
                "Replace one exact occurrence in one tracked, allowed public file. The "
                "gateway validates the current anchor and constructs the canonical Git "
                "diff; never provide diff syntax or patch wrappers. The minimal plan, "
                "hypothesis, and exact current source anchor are part of this mutation. "
                "The gateway binds the anchor to the contiguous union of current observed "
                "public source. An accepted mutation's bounded post-image is current evidence "
                "for a same-file repair; there is no separate planning tool."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1, "maxLength": 1_000},
                    "old_text": {
                        "type": "string",
                        "minLength": 1,
                        "description": (
                            "Exact current source text to replace; it must be covered by "
                            "current evidence for this file. Prefer the smallest sufficient "
                            "unique anchor; omit unchanged signatures or docstrings when "
                            "only executable lines change. Copy the observed normalized text, "
                            "including its line breaks; do not reconstruct the text."
                        ),
                        "maxLength": 20_000,
                    },
                    "new_text": {"type": "string", "maxLength": 20_000},
                    "occurrence": {"type": "integer", "minimum": 1, "maximum": 100},
                    "hypothesis": {"type": "string", "minLength": 1},
                    "expected_behavior": {"type": "string", "minLength": 1},
                    "causal_revision": {
                        "type": ["object", "null"],
                        "description": (
                            "Optional concise revision of the public hypothesis after "
                            "observed failure; it is never required for mutation admission."
                        ),
                        "properties": {
                            "falsified_prior_hypothesis": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 1_500,
                            },
                            "alternative_mechanism": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 1_500,
                            },
                        },
                        "required": [
                            "falsified_prior_hypothesis",
                            "alternative_mechanism",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "path",
                    "old_text",
                    "new_text",
                    "occurrence",
                    "hypothesis",
                    "expected_behavior",
                    "causal_revision",
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
    if allowed_tools is not None and "run_probe" in allowed_tools:
        schemas.append({
            "type": "function",
            "name": "run_probe",
            "description": (
                "Run a small public Python experiment in clean isolated scratch space. "
                "Current tracked public project files, including accepted edits, are importable "
                "read-only from /workspace; writable scratch is /tmp. Only base Python and "
                "public project code are supplied, with no network or dependency installation. "
                "Results are model-authored diagnostics, not required visible-check verdicts."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "minLength": 1, "maxLength": 500},
                    "python_source": {"type": "string", "minLength": 1, "maxLength": 8_000},
                },
                "required": ["question", "python_source"],
                "additionalProperties": False,
            },
        })
    decision_modes = {
        "search_files": "inspect",
        "read_file": "inspect",
        "run_check": "verify",
        "run_probe": "verify",
        "replace_text": "mutate",
        "finish_task": "finish",
        "stop_task": "stop",
    }
    enabled = (
        set(allowed_tools) if allowed_tools is not None else {schema["name"] for schema in schemas}
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
    allowed_read_paths: Sequence[str] = (),
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
        "run_probe": "verify",
        "replace_text": "mutate",
        "finish_task": "finish",
        "stop_task": "stop",
    }
    if any(call.turn_decision.mode != expected_modes[call.name] for call in calls):
        raise ContractError("turn_decision mode must match the requested tool family")
    if allowed_read_paths:
        allowed_paths = set(allowed_read_paths)
        if any(
            call.name == "read_file" and call.arguments.get("path") not in allowed_paths
            for call in calls
        ):
            raise ContractError("read_file path is unavailable in the targeted repair window")
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
        deadline: ExecutionDeadline | None = None,
        probe_sandbox: DockerProbeSandbox | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.public_task = public_task
        self.sandbox = sandbox
        self.journal = journal
        self.limits = limits
        self.deadline = deadline
        self.probe_sandbox = probe_sandbox
        self._lock = threading.RLock()
        self.spans: dict[str, dict[str, Any]] = {}
        self._observation_seq = 0
        self._read_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._evidence_repetitions: dict[str, int] = {}
        self._coverage_by_diff: dict[str, dict[str, list[tuple[int, int]]]] = {}
        self._search_ledger_by_diff: dict[str, dict[str, dict[str, Any]]] = {}
        self._recorded_search_actions_by_diff: dict[str, set[str]] = {}
        self._search_observations_by_diff: dict[str, list[dict[str, Any]]] = {}
        self._search_result_fingerprints_by_diff: dict[str, set[str]] = {}
        self._latest_inspection_by_diff: dict[str, dict[str, Any]] = {}
        self._recent_inspections_by_diff: dict[str, list[dict[str, Any]]] = {}
        self._observed_read_actions: set[str] = set()
        self._ledger_seq = 0
        self.checks_by_diff: dict[str, dict[str, dict[str, Any]]] = {}
        self.failure_diffs: dict[str, set[str]] = {}
        self._failed_check_history: list[dict[str, Any]] = []
        self._active_failed_check: dict[str, Any] | None = None
        self.requires_alternative = False
        self.accepted_mutations = 0
        self.last_successful_mutation: dict[str, Any] | None = None
        self.last_failed_mutation: dict[str, Any] | None = None
        self._working_findings: list[dict[str, Any]] = []
        self._working_note_source_bodies: dict[str, list[str | None]] = {}
        self._working_notes_lifecycle: dict[str, Any] | None = None
        self._working_open_question: str | None = None
        self._verification_state = empty_verification_state()
        self._working_notes_turns: dict[str, dict[str, Any]] = {}
        self._next_working_note_id = 1
        self._legacy_working_note_ids: dict[str, str] = {}
        self._hydrate()

    def _hydrate(self) -> None:
        action_starts: dict[str, dict[str, Any]] = {}
        for event in self.journal.events():
            if event["event_type"] == "working_notes_updated":
                self._restore_working_notes(event["payload"])
                continue
            if event["event_type"] == "action_started":
                payload = event["payload"]
                if isinstance(payload.get("action_id"), str):
                    action_starts[payload["action_id"]] = payload
                continue
            if event["event_type"] != "action_finished":
                continue
            result = DevToolResult.model_validate(event["payload"]["result"])
            if result.tool in _MUTATION_TOOLS:
                if result.status == "failed":
                    started = action_starts.get(result.action_id)
                    if started is not None and isinstance(started.get("arguments"), dict):
                        self.last_failed_mutation = self._failed_mutation_context(
                            arguments=started["arguments"],
                            action_id=result.action_id,
                            input_hash=result.input_hash,
                            baseline_diff_hash=started.get("baseline_diff_hash"),
                            result=result,
                        )
                    continue
                notes_state = event["payload"].get("working_notes_state")
                if isinstance(notes_state, dict):
                    self._restore_working_notes_state(notes_state)
                # Historical mutations must never be compared with the final
                # workspace to recompute historical note lifecycle decisions.
                self._accept_successful_mutation(result.output, refresh_notes=False)
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

    @staticmethod
    def _inline_python_source(check: RegisteredCheck) -> str | None:
        command = check.command
        try:
            marker = command.index("-c")
        except ValueError:
            return None
        if marker == 0 or marker + 1 >= len(command):
            return None
        executable = command[marker - 1].replace("\\", "/").rsplit("/", 1)[-1]
        if _INLINE_PYTHON.fullmatch(executable) is None:
            return None
        return command[marker + 1]

    @staticmethod
    def _exception_type(stdout: str, stderr: str) -> str | None:
        for stream in (stderr, stdout):
            for raw_line in reversed(stream.splitlines()):
                if raw_line != raw_line.strip():
                    continue
                match = _TRACEBACK_EXCEPTION.fullmatch(raw_line)
                if match is not None:
                    return match.group("type")[:200]
        return None

    def _previous_failed_check(self, check_id: str) -> dict[str, Any] | None:
        for output in reversed(self._failed_check_history):
            if output.get("check_id") == check_id:
                return output
        return None

    @staticmethod
    def _failure_identity(output: dict[str, Any]) -> str | None:
        focus = output.get("public_check_failure")
        if isinstance(focus, dict):
            site = focus.get("failure_site_fingerprint")
            if isinstance(site, str):
                return f"site:{site}"
        signature = output.get("failure_signature")
        return f"raw:{signature}" if isinstance(signature, str) else None

    @staticmethod
    def _failure_comparison(
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> dict[str, Any]:
        if previous is None:
            return {
                "relation": "first_observation",
                "previous_diff_hash": None,
                "previous_public_line": None,
                "inference": "No earlier failed execution of this public check is recorded.",
            }
        prior_focus = previous.get("public_check_failure")
        if not isinstance(prior_focus, dict):
            return {
                "relation": "not_comparable",
                "previous_diff_hash": previous.get("diff_hash"),
                "previous_public_line": None,
                "inference": "The earlier failure has no mapped public failure site.",
            }
        prior_site = prior_focus.get("failure_site_fingerprint")
        current_site = current.get("failure_site_fingerprint")
        prior_location = prior_focus.get("public_location")
        current_location = current.get("public_location")
        prior_line = (
            prior_location.get("line") if isinstance(prior_location, dict) else None
        )
        current_line = (
            current_location.get("line") if isinstance(current_location, dict) else None
        )
        if isinstance(prior_site, str) and prior_site == current_site:
            relation = "same_public_failure_site"
            inference = "The changed diff did not move the mapped public failure site."
        elif (
            isinstance(prior_location, dict)
            and isinstance(current_location, dict)
            and prior_location.get("source_hash") == current_location.get("source_hash")
            and isinstance(prior_line, int)
            and isinstance(current_line, int)
        ):
            if current_line > prior_line:
                relation = "public_failure_location_moved_later"
                inference = (
                    "The observed traceback location has a later source line number; "
                    "execution of other statements is not established."
                )
            elif current_line < prior_line:
                relation = "public_failure_location_moved_earlier"
                inference = (
                    "The observed traceback location has an earlier source line number; "
                    "execution of other statements is not established."
                )
            else:
                relation = "different_public_failure_site"
                inference = (
                    "The mapped public statement changed at the same source line; causal "
                    "direction is not established."
                )
        else:
            relation = "different_or_unmapped_public_failure"
            inference = "The failures do not have comparable mapped public locations."
        return {
            "relation": relation,
            "previous_diff_hash": previous.get("diff_hash"),
            "previous_public_line": prior_line,
            "inference": inference,
        }

    def _public_check_failure(
        self,
        *,
        check: RegisteredCheck,
        diff_hash: str,
        failure_signature: str,
        stdout: str,
        stderr: str,
    ) -> dict[str, Any]:
        exception_type = self._exception_type(stdout, stderr)
        focus: dict[str, Any] = {
            "check_id": check.id,
            "diff_hash": diff_hash,
            "failure_signature": failure_signature,
            "exception_type": exception_type,
            "mapping_status": "unmapped",
            "failure_site_fingerprint": None,
            "public_location": None,
            "execution_boundary": {
                "later_source_lines_observed": None,
                "reason": "No safe public inline-source execution boundary was mapped.",
            },
        }
        source = self._inline_python_source(check)
        diagnostic = stderr if "<string>" in stderr else stdout
        frames = list(_INLINE_PYTHON_FRAME.finditer(diagnostic))
        if source is not None and frames:
            lines = source.splitlines()
            frame = frames[-1]
            line = int(frame.group("line"))
            scope = (frame.group("scope") or "").strip() or None
            if 1 <= line <= len(lines):
                source_hash = sha256_bytes(source.encode("utf-8"))
                statement = lines[line - 1].strip()[:1_000]
                site = sha256_json(
                    {
                        "check_id": check.id,
                        "source_hash": source_hash,
                        "line": line,
                        "statement": statement,
                        "exception_type": exception_type,
                    }
                )
                focus.update(
                    {
                        "mapping_status": "mapped_public_inline_python",
                        "failure_site_fingerprint": site,
                        "public_location": {
                            "source": "<string>",
                            "source_hash": source_hash,
                            "line": line,
                            "scope": scope,
                            "statement": statement,
                        },
                        "execution_boundary": {
                            "later_source_lines_observed": None,
                            "reason": (
                                "A traceback identifies the failing frame, not the earlier "
                                "execution of other lines through loops or branches."
                            ),
                        },
                    }
                )
        previous = self._previous_failed_check(check.id)
        focus["comparison_with_previous_failure"] = self._failure_comparison(previous, focus)
        identity = (
            f"site:{focus['failure_site_fingerprint']}"
            if isinstance(focus.get("failure_site_fingerprint"), str)
            else f"raw:{failure_signature}"
        )
        focus["recurrence_across_distinct_diffs"] = len(
            self.failure_diffs.get(identity, set()) | {diff_hash}
        )
        return focus

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
        raw_path = arguments.get("path")
        raw_old_text = arguments.get("old_text")
        raw_new_text = arguments.get("new_text")
        path = cls._bounded_string(raw_path, 1_000)
        old_text = cls._bounded_string(raw_old_text, 20_000)
        new_text = cls._bounded_string(raw_new_text, 20_000)
        replacement_overflow = max(
            0,
            sum(len(value) for value in (old_text, new_text) if isinstance(value, str))
            - _MAX_MUTATION_HUNK_CHARS,
        )
        if replacement_overflow and isinstance(new_text, str):
            keep = max(0, len(new_text) - replacement_overflow)
            replacement_overflow -= len(new_text) - keep
            new_text = new_text[:keep]
        if replacement_overflow and isinstance(old_text, str):
            old_text = old_text[: max(0, len(old_text) - replacement_overflow)]
        occurrence_value = arguments.get("occurrence")
        occurrence = (
            occurrence_value
            if type(occurrence_value) is int and 1 <= occurrence_value <= 100
            else None
        )
        causal_revision = arguments.get("causal_revision")
        raw_replacement = {
            "path": raw_path,
            "old_text": raw_old_text,
            "new_text": raw_new_text,
            "occurrence": occurrence_value,
        }
        replacement = {
            "path": path,
            "old_text": old_text,
            "new_text": new_text,
            "occurrence": occurrence,
        }
        mutation_failure = result.output.get("mutation_failure")
        failure_class = (
            mutation_failure.get("class") if isinstance(mutation_failure, dict) else None
        )
        if failure_class in {"anchor_invalid", "evidence_invalid"}:
            next_action = (
                "Inspect the missing current source range if needed and budget permits, "
                "then repair or replace the failed mutation using exact observed evidence."
            )
        else:
            next_action = (
                "Repair or explicitly replace this failed mutation using the preserved exact "
                "replacement and typed feedback. Available inspection remains budget-governed."
            )
        return {
            "action_id": action_id,
            "input_hash": input_hash,
            "baseline_diff_hash": (
                baseline_diff_hash if isinstance(baseline_diff_hash, str) else None
            ),
            "replacement": replacement,
            "replacement_hash": sha256_json(raw_replacement),
            "replacement_truncated": any(
                isinstance(raw, str) and raw != bounded
                for raw, bounded in (
                    (raw_path, path),
                    (raw_old_text, old_text),
                    (raw_new_text, new_text),
                )
            ),
            "hypothesis": cls._bounded_string(arguments.get("hypothesis"), 1_500),
            "expected_behavior": cls._bounded_string(arguments.get("expected_behavior"), 1_500),
            "causal_revision": copy.deepcopy(causal_revision)
            if isinstance(causal_revision, dict)
            else None,
            "error_code": result.error_code,
            "error_message": result.message,
            "error_location": (
                cls._mutation_error_location(result.message) or ({"path": path} if path else None)
            ),
            "mutation_failure": (
                copy.deepcopy(mutation_failure) if isinstance(mutation_failure, dict) else None
            ),
            "next_action": next_action,
        }

    @staticmethod
    def _cache_key(input_hash: str, workspace_diff_hash: str) -> tuple[str, str]:
        return input_hash, workspace_diff_hash

    @staticmethod
    def _cacheable_read_output(output: dict[str, Any]) -> dict[str, Any]:
        cached = copy.deepcopy(output)
        # Older development journals may contain this retired projection field.
        cached.pop("working_state", None)
        # Gain and intent belong to the current observation, not the cached request.
        cached.pop("evidence_gain", None)
        cached.pop("inspection_intent", None)
        cached.pop("read_observation_seq", None)
        return cached

    @staticmethod
    def _merge_ranges(ranges: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
        merged: list[tuple[int, int]] = []
        for start, end in sorted(ranges):
            if not merged or start > merged[-1][1] + 1:
                merged.append((start, end))
                continue
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        return merged

    @staticmethod
    def _range_size(ranges: Sequence[tuple[int, int]]) -> int:
        return sum(end - start + 1 for start, end in ranges)

    @staticmethod
    def _search_result_fingerprint(
        spans: Sequence[dict[str, Any]], *, truncated: bool
    ) -> str:
        findings = sorted(
            (
                {
                    "path": span.get("path"),
                    "start_line": span.get("start_line"),
                    "end_line": span.get("end_line"),
                    "file_hash": span.get("file_hash"),
                }
                for span in spans
            ),
            key=lambda item: (
                str(item["path"]),
                int(item["start_line"] or 0),
                int(item["end_line"] or 0),
                str(item["file_hash"]),
            ),
        )
        return sha256_json({"findings": findings, "truncated": truncated})

    def _record_read_ledger(
        self,
        *,
        tool: str,
        workspace_diff_hash: str,
        output: dict[str, Any],
        turn_decision: dict[str, Any] | None,
        action_id: str | None,
        replay: bool = False,
    ) -> dict[str, Any]:
        spans = [span for span in output.get("spans", []) if isinstance(span, dict)]
        with self._lock:
            observation_seq = output.get("read_observation_seq")
            if type(observation_seq) is not int or observation_seq < 1:
                observation_seq = self._ledger_seq + 1
                output["read_observation_seq"] = observation_seq
            self._ledger_seq = max(self._ledger_seq, observation_seq)
            coverage = self._coverage_by_diff.setdefault(workspace_diff_hash, {})
            new_lines = 0
            relevant_new_lines = 0
            new_files = 0
            relevant_new_files = 0
            for span in spans:
                path = span.get("path")
                start = span.get("start_line")
                end = span.get("end_line")
                if (
                    not isinstance(path, str)
                    or type(start) is not int
                    or type(end) is not int
                    or start < 1
                    or end < start
                ):
                    continue
                previous = coverage.get(path, [])
                was_new_file = not previous
                previous_size = self._range_size(previous)
                current = self._merge_ranges([*previous, (start, end)])
                gained = self._range_size(current) - previous_size
                coverage[path] = current
                new_lines += gained
                editable = self._path_allowed(path)
                if editable:
                    relevant_new_lines += gained
                if was_new_file:
                    new_files += 1
                    if editable:
                        relevant_new_files += 1

            saved_gain = output.get("evidence_gain") if replay else None
            if isinstance(saved_gain, dict):
                new_lines = saved_gain.get("new_covered_line_count", new_lines)
                relevant_new_lines = saved_gain.get(
                    "new_editable_line_count", relevant_new_lines
                )
                new_files = saved_gain.get("new_file_count", new_files)
                relevant_new_files = saved_gain.get("new_editable_file_count", relevant_new_files)
            supporting_new_lines = new_lines - relevant_new_lines
            supporting_new_files = new_files - relevant_new_files
            first_search_observation = False
            if tool == "search_files":
                query = output.get("query")
                path_glob = output.get("path_glob")
                if isinstance(query, str) and isinstance(path_glob, str):
                    search_key = sha256_json({"query": query, "path_glob": path_glob})
                    searches = self._search_ledger_by_diff.setdefault(workspace_diff_hash, {})
                    first_search_observation = search_key not in searches
                    if isinstance(saved_gain, dict):
                        first_search_observation = saved_gain.get(
                            "first_search_observation", first_search_observation
                        )
                    truncated = bool(output.get("truncated"))
                    result_fingerprint = self._search_result_fingerprint(
                        spans,
                        truncated=truncated,
                    )
                    if not spans:
                        outcome = "zero_match"
                    elif new_lines == 0:
                        outcome = "covered_only"
                    elif relevant_new_lines == 0:
                        outcome = "supporting_coverage"
                    else:
                        outcome = "new_coverage"
                    recorded_actions = self._recorded_search_actions_by_diff.setdefault(
                        workspace_diff_hash, set()
                    )
                    if action_id is None or action_id not in recorded_actions:
                        if action_id is not None:
                            recorded_actions.add(action_id)
                        previous = searches.get(search_key, {})
                        outcome_counts = copy.deepcopy(previous.get("outcome_counts", {}))
                        outcome_counts[outcome] = int(outcome_counts.get(outcome, 0)) + 1
                        current_observation = {
                            "query": query,
                            "path_glob": path_glob,
                            "evidence_goal": self._bounded_string(
                                (turn_decision or {}).get("evidence_goal"), 500
                            ),
                            "span_count": len(spans),
                            "zero_match": not spans,
                            "truncated": truncated,
                            "result_fingerprint": result_fingerprint,
                            "outcome": outcome,
                            "outcome_counts": outcome_counts,
                            "observation_count": int(previous.get("observation_count", 0)) + 1,
                            "new_covered_line_count": new_lines,
                            "new_editable_line_count": relevant_new_lines,
                            "new_supporting_line_count": supporting_new_lines,
                            "findings": [
                                {
                                    "path": span.get("path"),
                                    "range": [span.get("start_line"), span.get("end_line")],
                                }
                                for span in spans[:20]
                            ],
                            "last_observed_seq": observation_seq,
                        }
                        if int(previous.get("last_observed_seq", 0)) > observation_seq:
                            searches[search_key] = {
                                **previous,
                                "outcome_counts": outcome_counts,
                                "observation_count": current_observation["observation_count"],
                            }
                        else:
                            searches[search_key] = current_observation
                        observation = copy.deepcopy(current_observation)
                        observation.pop("outcome_counts", None)
                        observation.pop("observation_count", None)
                        self._search_observations_by_diff.setdefault(
                            workspace_diff_hash, []
                        ).append(observation)
                        self._search_result_fingerprints_by_diff.setdefault(
                            workspace_diff_hash, set()
                        ).add(result_fingerprint)
            if turn_decision is not None:
                latest_intent = {
                    "basis": self._bounded_string(turn_decision.get("basis"), 800),
                    "evidence_goal": self._bounded_string(turn_decision.get("evidence_goal"), 500),
                    "evidence_span_ids": [
                        str(span["span_id"])
                        for span in spans[:8]
                        if isinstance(span.get("span_id"), str)
                    ],
                    "last_observed_seq": observation_seq,
                    "marginal_evidence_gain": new_lines > 0,
                }
                previous_intent = self._latest_inspection_by_diff.get(workspace_diff_hash, {})
                if int(previous_intent.get("last_observed_seq", 0)) <= observation_seq:
                    self._latest_inspection_by_diff[workspace_diff_hash] = latest_intent
            if tool in READ_TOOLS:
                recent = self._recent_inspections_by_diff.setdefault(workspace_diff_hash, [])
                recent.append({
                    "tool": tool,
                    "action_id": action_id,
                    **(
                        {"query": output.get("query"), "path_glob": output.get("path_glob")}
                        if tool == "search_files"
                        else {
                            "path": spans[0].get("path") if spans else output.get("path"),
                            "start_line": spans[0].get("start_line") if spans else None,
                            "end_line": spans[0].get("end_line") if spans else None,
                        }
                    ),
                    "evidence_goal": self._bounded_string(
                        (turn_decision or {}).get("evidence_goal"), 500
                    ),
                    "outcome": (
                        "zero_match" if not spans
                        else "covered_only" if not new_lines
                        else "supporting_coverage" if not relevant_new_lines
                        else "new_coverage"
                    ),
                    "new_covered_line_count": new_lines,
                    "new_editable_line_count": relevant_new_lines,
                    "new_supporting_line_count": supporting_new_lines,
                    "last_observed_seq": observation_seq,
                })
                recent.sort(key=lambda item: item["last_observed_seq"], reverse=True)
                del recent[3:]
        gain_units = new_lines
        return {
            "new_covered_line_count": new_lines,
            "new_editable_line_count": relevant_new_lines,
            "new_supporting_line_count": supporting_new_lines,
            "new_task_relevant_line_count": relevant_new_lines,
            "new_file_count": new_files,
            "new_editable_file_count": relevant_new_files,
            "new_supporting_file_count": supporting_new_files,
            "new_task_relevant_file_count": relevant_new_files,
            "first_search_observation": first_search_observation,
            "marginal_evidence_gain": gain_units > 0,
            "marginal_evidence_gain_units": gain_units,
        }

    def _restore_read_result(self, result: DevToolResult) -> None:
        spans = result.output.get("spans", [])
        with self._lock:
            if result.action_id in self._observed_read_actions:
                return
            for span in spans:
                if not isinstance(span, dict) or not isinstance(span.get("span_id"), str):
                    continue
                restored = dict(span)
                sequence = restored.get("last_observed_seq")
                if type(sequence) is not int or sequence < 1:
                    sequence = self._observation_seq + 1
                    restored["last_observed_seq"] = sequence
                self._observation_seq = max(self._observation_seq, sequence)
                previous = self.spans.get(restored["span_id"], {})
                if int(previous.get("last_observed_seq", 0)) <= sequence:
                    self.spans[restored["span_id"]] = restored
            fingerprint = result.output.get("evidence_fingerprint")
            if isinstance(fingerprint, str):
                repetition = result.output.get("evidence_repetition")
                previous_repetition = self._evidence_repetitions.get(fingerprint, 0)
                self._evidence_repetitions[fingerprint] = (
                    max(previous_repetition, repetition)
                    if type(repetition) is int
                    else previous_repetition + 1
                )
            if result.workspace_diff_hash is not None:
                read_request_hash = result.output.get("read_request_hash", result.input_hash)
                if isinstance(read_request_hash, str):
                    self._read_cache[
                        self._cache_key(read_request_hash, result.workspace_diff_hash)
                    ] = self._cacheable_read_output(result.output)
                intent = result.output.get("inspection_intent")
                self._record_read_ledger(
                    tool=result.tool,
                    workspace_diff_hash=result.workspace_diff_hash,
                    output=result.output,
                    turn_decision=intent if isinstance(intent, dict) else None,
                    action_id=result.action_id,
                    replay=True,
                )
            self._observed_read_actions.add(result.action_id)

    def _restore_mutation_evidence(self, output: dict[str, Any]) -> None:
        span = output.get("mutation_evidence")
        candidates = [span, *output.get("revalidated_spans", [])]
        restored_candidates: list[dict[str, Any]] = []
        with self._lock:
            for candidate in candidates:
                if not isinstance(candidate, dict) or not isinstance(candidate.get("span_id"), str):
                    continue
                self._observation_seq += 1
                restored = dict(candidate)
                restored["last_observed_seq"] = self._observation_seq
                self.spans[restored["span_id"]] = restored
                restored_candidates.append(restored)
        diff_hash = output.get("worktree_diff_hash")
        if restored_candidates and isinstance(diff_hash, str):
            self._record_read_ledger(
                tool="mutation_evidence",
                workspace_diff_hash=diff_hash,
                output={"spans": restored_candidates},
                turn_decision=None,
                action_id=None,
            )

    def _accept_successful_mutation(
        self, output: dict[str, Any], *, refresh_notes: bool = True,
    ) -> None:
        self.accepted_mutations += 1
        self.last_successful_mutation = output.get("mutation")
        self.last_failed_mutation = None
        if refresh_notes:
            self._refresh_working_source_notes()
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
        turn_decision: dict[str, Any] | None,
        action_id: str,
    ) -> dict[str, Any]:
        decorated = copy.deepcopy(output)
        spans = decorated.get("spans", [])
        # Filesystem scans already finished outside this small metadata section.
        # Spans, coverage and zero-result observations receive one consistent order.
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
            decorated["evidence_gain"] = self._record_read_ledger(
                tool=tool,
                workspace_diff_hash=workspace_diff_hash,
                output=decorated,
                turn_decision=turn_decision,
                action_id=action_id,
            )
            if turn_decision is not None:
                # The original call is retained in native continuation. Do not echo
                # its unvalidated annotation as part of a successful read result.
                decorated["inspection_intent"] = {
                    key: copy.deepcopy(value) for key, value in turn_decision.items()
                    if key != "memory_update"
                }
            self._observed_read_actions.add(action_id)
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

    def _revalidated_spans(
        self, *, paths: Sequence[str], diff_hash: str,
        replacement: SourceReplacement | None = None,
    ) -> list[dict[str, Any]]:
        """Rebind observed untouched lines by exact edit, or unique whole-body fallback."""

        changed = {str(path).replace("\\", "/") for path in paths}
        with self._lock:
            candidates = sorted(
                (
                    dict(span)
                    for span in self.spans.values()
                    if span.get("path") in changed
                    and isinstance(span.get("content"), str)
                    and span.get("content")
                ),
                key=lambda span: int(span.get("last_observed_seq", 0)),
                reverse=True,
            )
        if replacement is not None:
            if len(changed) != 1:
                raise ContractError("source rebinding requires one exact replacement path")
            path, = changed
            normalized, current = self._tracked_path(path)
            if current.read_bytes() != replacement.after_bytes:
                raise RecoveryError("source rebinding target differs from the admitted postimage")
            return [
                {
                    **self._span(
                        normalized, fragment["start_line"], fragment["end_line"],
                        fragment["content"], sha256_bytes(replacement.after_bytes),
                    ),
                    "origin": "revalidated_after_mutation",
                    "source_diff_hash": diff_hash,
                }
                for fragment in replacement.observed_fragments(candidates)
            ]
        rebound: list[dict[str, Any]] = []
        seen: set[str] = set()
        for span in candidates:
            path = str(span["path"])
            try:
                normalized, current = self._tracked_path(path)
                raw = current.read_bytes()
                text, _ = self._source_text(raw)
            except (PatchLoopError, OSError, UnicodeDecodeError):
                continue
            content = str(span["content"])
            positions = [
                match.start() for match in re.finditer(re.escape(content), text)
                if (match.start() == 0 or text[match.start() - 1] == "\n")
                and (match.end() == len(text) or text[match.end()] == "\n")
            ]
            if len(positions) != 1:
                continue
            start_line = text[: positions[0]].count("\n") + 1
            end_line = start_line + content.count("\n")
            restored = {
                **self._span(
                    normalized,
                    start_line,
                    end_line,
                    content,
                    sha256_bytes(raw),
                ),
                "origin": "revalidated_after_mutation",
                "source_diff_hash": diff_hash,
            }
            if restored["span_id"] in seen:
                continue
            seen.add(restored["span_id"])
            rebound.append(restored)
            if len(rebound) >= 8:
                break
        return rebound

    def _validated_source_spans(self) -> list[dict[str, Any]]:
        """Check content as well as hashes before claiming any observed range."""

        with self._lock:
            candidates = [dict(span) for span in self.spans.values()]
        sources: dict[str, tuple[list[str], str] | None] = {}
        valid: list[dict[str, Any]] = []
        for span in candidates:
            path = span.get("path")
            if not isinstance(path, str):
                continue
            if path not in sources:
                try:
                    _, current = self._tracked_path(path)
                    raw = current.read_bytes()
                    sources[path] = (source_lines(raw.decode("utf-8")), sha256_bytes(raw))
                except (PatchLoopError, OSError, UnicodeDecodeError):
                    sources[path] = None
            current_source = sources[path]
            if current_source is not None and valid_observed_span(span, *current_source):
                valid.append(span)
        return valid

    def _source_projection_priorities(self) -> list[tuple[str, int, int, int]]:
        priorities: list[tuple[str, int, int, int]] = []
        failed = self.last_failed_mutation or {}
        replacement = failed.get("replacement")
        if isinstance(replacement, dict) and isinstance(replacement.get("path"), str):
            path = replacement["path"]
            try:
                _, current = self._tracked_path(path)
                text, _ = self._source_text(current.read_bytes())
                old_text = replacement.get("old_text")
                occurrence = replacement.get("occurrence", 1)
                positions = (
                    [match.start() for match in re.finditer(re.escape(old_text), text)]
                    if isinstance(old_text, str) and old_text else []
                )
                if type(occurrence) is int and 1 <= occurrence <= len(positions):
                    start = text[:positions[occurrence - 1]].count("\n") + 1
                    priorities.append((path, start, start + old_text.count("\n"), 0))
            except (PatchLoopError, OSError, UnicodeDecodeError):
                pass
            failure = failed.get("mutation_failure")
            anchor = failure.get("required_anchor") if isinstance(failure, dict) else None
            if isinstance(anchor, dict) and type(anchor.get("start_line")) is int:
                priorities.append((
                    path, anchor["start_line"],
                    anchor.get("end_line", anchor["start_line"]), 0,
                ))
        latest = self.last_successful_mutation or {}
        postimage_id = latest.get("postimage_evidence_span_id")
        with self._lock:
            postimage = self.spans.get(postimage_id)
        if isinstance(postimage, dict):
            priorities.append((
                postimage["path"], postimage["start_line"], postimage["end_line"], 1,
            ))
        for finding in self._working_findings:
            for evidence in finding.get("evidence", []):
                if evidence.get("kind") == "source":
                    priorities.append((
                        evidence["path"], evidence["start_line"], evidence["end_line"], 3,
                    ))
        return priorities

    def prepare_context_projection(
        self, latest_results: Sequence[DevToolResult] = ()
    ) -> SourceProjection:
        """Select bounded retained source; native latest results already carry their text."""

        self._refresh_working_source_notes()
        valid = self._validated_source_spans()
        valid_by_id = {span["span_id"]: span for span in valid}
        native: list[dict[str, Any]] = []
        seen_native: set[str] = set()
        for result in latest_results:
            output = result.output
            candidates = [
                *output.get("spans", []),
                output.get("mutation_evidence"),
                *output.get("revalidated_spans", []),
            ]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                span_id = candidate.get("span_id")
                if span_id in valid_by_id and span_id not in seen_native:
                    native.append(valid_by_id[span_id])
                    seen_native.add(span_id)
        return project_observed_sources(
            valid,
            native_spans=native,
            priorities=self._source_projection_priorities(),
            editable_paths={span["path"] for span in valid if self._path_allowed(span["path"])},
        )

    def _restore_working_notes(self, payload: dict[str, Any]) -> None:
        turn_id = payload.get("turn_id")
        if not isinstance(turn_id, str) or turn_id in self._working_notes_turns:
            return
        self._working_notes_turns[turn_id] = copy.deepcopy(payload)
        if "verification_state" in payload:
            self._verification_state = copy.deepcopy(payload["verification_state"])
        removed = set(payload.get("removed_note_ids", []))
        self._working_findings = [
            finding for finding in self._working_findings
            if finding.get("note_id") not in removed
        ]
        for finding in payload.get("findings", []):
            restored = copy.deepcopy(finding)
            identity = restored.get("note_id")
            if identity is None:
                # Legacy journals remain read-only. Preserve their evidence upsert
                # semantics while providing deterministic IDs in the projection.
                legacy_id = restored.pop("finding_id", None)
                identity = self._legacy_working_note_ids.get(legacy_id)
                if identity is None:
                    identity = f"n{self._next_working_note_id}"
                    self._legacy_working_note_ids[legacy_id] = identity
                restored["note_id"] = identity
            self._next_working_note_id = max(self._next_working_note_id, int(identity[1:]) + 1)
            self._working_findings = [
                previous for previous in self._working_findings
                if previous.get("note_id") != identity
            ]
            self._working_findings.append(restored)
            bodies = payload.get("source_bodies_by_note_id", {}).get(identity)
            if bodies is None:
                # Read-only legacy hydration may use the observations preceding
                # this event, never unobserved/final workspace bytes.
                bodies = self._capture_working_note_source_bodies(
                    restored.get("evidence", []), list(self.spans.values()),
                )
            if bodies is not None:
                self._working_note_source_bodies[identity] = copy.deepcopy(bodies)
            else:
                self._working_note_source_bodies.pop(identity, None)
        evicted = set(payload.get("evicted_note_ids", []))
        self._working_findings = [
            finding for finding in self._working_findings
            if finding.get("note_id") not in evicted
        ][-6:]
        if "retained_note_ids" in payload:
            retained = set(payload["retained_note_ids"])
            self._working_findings = [
                finding for finding in self._working_findings if finding["note_id"] in retained
            ]
        if payload.get("update_valid") is True:
            self._working_open_question = payload.get("open_question")
        retained_ids = {finding["note_id"] for finding in self._working_findings}
        self._working_note_source_bodies = {
            note_id: bodies for note_id, bodies in self._working_note_source_bodies.items()
            if note_id in retained_ids
        }

    @staticmethod
    def _capture_working_note_source_bodies(
        evidence: Sequence[dict[str, Any]], spans: Sequence[dict[str, Any]],
    ) -> list[str | None] | None:
        """Preserve bounded, actually observed source independently of active spans."""

        bodies: list[str | None] = []
        total_chars = 0
        for reference in evidence:
            if reference.get("kind") != "source":
                bodies.append(None)
                continue
            observed: dict[int, str] = {}
            for span in spans:
                if (
                    span.get("path") != reference["path"]
                    or span.get("file_hash") != reference["file_hash"]
                ):
                    continue
                lines = span.get("content", "").replace("\r\n", "\n").split("\n")
                for offset, line in enumerate(lines):
                    observed[span["start_line"] + offset] = line
            numbers = range(reference["start_line"], reference["end_line"] + 1)
            if not all(number in observed for number in numbers):
                return None
            content = "\n".join(observed[number] for number in numbers)
            total_chars += len(content)
            if not content or total_chars > _MAX_NOTE_SOURCE_BODY_CHARS:
                return None
            bodies.append(content)
        return bodies

    def _source_note_range_diagnostic(
        self, evidence: SourceNoteEvidence, current_spans: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Use prior completed public observations only for a bounded error detail."""

        historical: list[dict[str, Any]] = []
        for event in self.journal.events():
            if event["event_type"] != "action_finished":
                continue
            result = event["payload"].get("result", {})
            if result.get("status") != "succeeded" or result.get("tool") not in {
                *READ_TOOLS, "replace_text",
            }:
                continue
            output = result.get("output", {})
            candidates = (
                output.get("spans", []) if result["tool"] in READ_TOOLS else
                [output.get("mutation_evidence"), *output.get("revalidated_spans", [])]
            )
            historical.extend(span for span in candidates if isinstance(span, dict))
        return source_note_range_details(evidence, current_spans, historical)

    def record_working_notes_update(
        self, calls: Sequence[RequestedTool], *, turn_id: str
    ) -> dict[str, Any]:
        """Record the first update once, before this batch; bad notes cannot block it."""

        existing = self._working_notes_turns.get(turn_id)
        if existing is not None:
            return copy.deepcopy(existing)
        updates = [
            (call.action_id, getattr(call.turn_decision, "memory_update", None))
            for call in calls
            if getattr(call.turn_decision, "memory_update", None) is not None
        ]
        if not updates:
            return {"status": "not_requested"}
        self._refresh_working_source_notes()
        action_id, selected = updates[0]
        diff_hash_at_update = self.current_diff_hash
        receipt: dict[str, Any] = {
            "scope": "before_tool_batch",
            "diff_hash_at_update": diff_hash_at_update,
            "turn_id": turn_id,
            "action_id": action_id,
            "status": "rejected",
            "findings": [],
            "diagnostics": [],
            "note_ids_after_update": [],
            "removed_note_ids": [],
            "evicted_note_ids": [],
            "open_question_applied": False,
        }
        payload: dict[str, Any] = {
            "turn_id": turn_id,
            "action_id": action_id,
            "findings": [],
            "source_bodies_by_note_id": {},
            "allocated_note_ids": [],
            "removed_note_ids": [],
            "evicted_note_ids": [],
            "retained_note_ids": [note["note_id"] for note in self._working_findings],
            "open_question": None,
            "update_valid": False,
            "diagnostics": [],
            "receipt": receipt,
        }

        def diagnose(code: str, *, legacy_code: str | None = None, **location: int | str):
            payload["diagnostics"].append(legacy_code or code)
            feedback = note_feedback(code, **location)
            # Per-finding failures already carry their feedback in findings.
            if "finding_index" not in location:
                receipt["diagnostics"].append(feedback)
            return feedback

        if len(updates) > 1:
            diagnose("ignored_additional_memory_updates")
        try:
            update = WorkingNotesUpdate.model_validate(selected)
        except ValidationError:
            diagnose("invalid_memory_update_shape")
        else:
            payload["update_valid"] = True
            payload["open_question"] = update.open_question
            receipt["open_question_applied"] = True
            question_changed = update.open_question != self._working_open_question
            existing_ids = {finding["note_id"] for finding in self._working_findings}
            updated_ids: set[str] = set()
            next_note_number = self._next_working_note_id
            all_findings_valid = True
            spans = self._validated_source_spans()
            prior_results = {
                event["payload"]["result"]["action_id"]: event["payload"]["result"]
                for event in self.journal.events()
                if event["event_type"] == "action_finished"
            }
            for index, finding in enumerate(update.findings):
                entry: dict[str, Any] = {
                    "finding_index": index,
                    "note_id": finding.note_id,
                    "status": "rejected",
                    "code": None,
                    "message": "",
                }
                receipt["findings"].append(entry)
                if finding.note_id is not None and finding.note_id not in existing_ids:
                    entry.update(diagnose(
                        "unknown_note_id", finding_index=index, note_id=finding.note_id,
                    ))
                    all_findings_valid = False
                    continue
                if finding.note_id in updated_ids:
                    entry.update(diagnose(
                        "duplicate_note_update", finding_index=index,
                        note_id=finding.note_id,
                    ))
                    all_findings_valid = False
                    continue
                bound: list[dict[str, Any]] = []
                for evidence_index, evidence in enumerate(finding.evidence):
                    if isinstance(evidence, SourceNoteEvidence):
                        matches = [span for span in spans if span["path"] == evidence.path]
                        if (
                            evidence.end_line < evidence.start_line
                            or not spans_cover_range(
                                matches, evidence.start_line, evidence.end_line
                            )
                        ):
                            range_diagnostic = self._source_note_range_diagnostic(evidence, matches)
                            entry.update(diagnose(
                                "unobserved_source_range",
                                legacy_code="unobserved_public_evidence",
                                finding_index=index, evidence_index=evidence_index,
                                reason=range_diagnostic["reason"],
                            ))
                            entry["range_details"] = range_diagnostic["range_details"]
                            break
                        bound.append({
                            **evidence.model_dump(), "file_hash": matches[0]["file_hash"],
                        })
                    else:
                        result = prior_results.get(evidence.action_id)
                        if result is None:
                            entry.update(diagnose(
                                "unobserved_tool_result",
                                legacy_code="unobserved_public_evidence",
                                finding_index=index, evidence_index=evidence_index,
                            ))
                            break
                        bound.append({
                            **evidence.model_dump(),
                            "tool": result["tool"],
                            "input_hash": result["input_hash"],
                            "diff_hash": (
                                result.get("output", {}).get("worktree_diff_hash")
                                or result.get("output", {}).get("diff_hash")
                                or result.get("workspace_diff_hash")
                            ),
                        })
                        check_result = check_note_result(result)
                        if check_result is not None:
                            bound[-1]["check_result"] = check_result
                if len(bound) != len(finding.evidence):
                    all_findings_valid = False
                    continue
                bodies = self._capture_working_note_source_bodies(bound, spans)
                if bodies is None:
                    entry.update(diagnose("note_source_body_unavailable", finding_index=index))
                    all_findings_valid = False
                    continue
                note_id = finding.note_id
                if note_id is None:
                    note_id = f"n{next_note_number}"
                    next_note_number += 1
                    payload["allocated_note_ids"].append(note_id)
                updated_ids.add(note_id)
                stored = {"statement": finding.statement, "evidence": bound}
                payload["findings"].append({
                    "note_id": note_id,
                    "author": "model_public_note",
                    "model_authored": True,
                    **stored,
                })
                payload["source_bodies_by_note_id"][note_id] = bodies
                entry.update({
                    "note_id": note_id,
                    "status": "created" if finding.note_id is None else "updated",
                    "message": (
                        "Note update recorded before this tool batch. Consult "
                        "working_notes.available_note_ids for currently retained IDs."
                    ),
                })
            if update.remove_note_ids and not all_findings_valid:
                diagnose("removals_skipped_after_invalid_finding")
            elif update.remove_note_ids:
                for note_id in dict.fromkeys(update.remove_note_ids):
                    if note_id not in existing_ids:
                        diagnose("unknown_remove_note_id", note_id=note_id)
                    elif note_id in updated_ids:
                        diagnose("cannot_remove_updated_note", note_id=note_id)
                    else:
                        payload["removed_note_ids"].append(note_id)
            removed = set(payload["removed_note_ids"])
            resulting_ids = [
                note["note_id"] for note in self._working_findings
                if note["note_id"] not in updated_ids | removed
            ] + [note["note_id"] for note in payload["findings"]]
            payload["evicted_note_ids"] = resulting_ids[:-6]
            payload["retained_note_ids"] = resulting_ids[-6:]
            applied = bool(payload["findings"] or payload["removed_note_ids"] or question_changed)
            receipt["status"] = (
                "applied" if not payload["diagnostics"]
                else "partially_applied" if applied else "rejected"
            )
        # Verification concerns have a separate lifetime and independent annotation
        # validation. Changing focus or rejecting a source finding must not erase them.
        if isinstance(selected, dict) and selected.get("verification_updates", []) != []:
            prior_results = {
                event["payload"]["result"]["action_id"]: event["payload"]["result"]
                for event in self.journal.events()
                if event["event_type"] == "action_finished"
            }
            state, verification_receipt = update_verification_concerns(
                self._verification_state, selected["verification_updates"],
                diff_hash=diff_hash_at_update, prior_results=prior_results,
                turn_id=turn_id,
            )
            payload["verification_state"] = state
            receipt["verification"] = verification_receipt
            verification_status = verification_receipt["status"]
            if verification_status in {"rejected", "partially_applied"}:
                payload["diagnostics"].append("verification_update_rejected")
            if verification_status != "not_requested" and verification_status != receipt["status"]:
                receipt["status"] = "partially_applied"
        receipt["note_ids_after_update"] = list(payload["retained_note_ids"])
        receipt["removed_note_ids"] = list(payload["removed_note_ids"])
        receipt["evicted_note_ids"] = list(payload["evicted_note_ids"])
        # At most two findings, six removals, and batch/shape diagnostics. Never
        # include rejected prose or unknown path/result strings in this receipt.
        receipt["diagnostics"] = receipt["diagnostics"][:10]
        self.journal.append("working_notes_updated", payload)
        self._restore_working_notes(payload)
        return copy.deepcopy(payload)

    def _refresh_working_source_notes(self) -> None:
        self._restore_working_notes_state(self._refreshed_working_notes_state())

    def _refreshed_working_notes_state(
        self, *, action_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute lifecycle without applying it until its action is durable."""

        current_sources: dict[str, tuple[str, str] | None] = {}
        retained: list[dict[str, Any]] = []
        rebound: list[str] = []
        expired: list[dict[str, str]] = []
        for original in self._working_findings:
            finding = copy.deepcopy(original)
            note_id = finding["note_id"]
            bodies = self._working_note_source_bodies.get(note_id, [])
            reason: str | None = None
            source_rebound = False
            for index, evidence in enumerate(finding["evidence"]):
                if evidence["kind"] != "source":
                    continue
                path = evidence["path"]
                if path not in current_sources:
                    try:
                        _, selected = self._tracked_path(path)
                        raw = selected.read_bytes()
                        text, _ = self._source_text(raw)
                        current_sources[path] = text, sha256_bytes(raw)
                    except (PatchLoopError, OSError, UnicodeDecodeError):
                        current_sources[path] = None
                source = current_sources[path]
                if source is None:
                    reason = "source_unavailable"
                    break
                text, file_hash = source
                if file_hash == evidence["file_hash"]:
                    continue
                content = bodies[index] if index < len(bodies) else None
                if not content:
                    reason = "observed_body_unavailable"
                    break
                positions = [
                    match.start() for match in re.finditer(f"(?={re.escape(content)})", text)
                    if content and (match.start() == 0 or text[match.start() - 1] == "\n")
                    and (
                        match.start() + len(content) == len(text)
                        or text[match.start() + len(content)] == "\n"
                    )
                ]
                if len(positions) != 1:
                    reason = "source_ambiguous" if positions else "source_changed"
                    break
                start = text[:positions[0]].count("\n") + 1
                evidence.update({
                    "file_hash": file_hash, "start_line": start,
                    "end_line": start + content.count("\n"),
                })
                source_rebound = True
            if reason is None:
                retained.append(finding)
                if source_rebound:
                    rebound.append(note_id)
            else:
                expired.append({"note_id": note_id, "reason": reason})
        lifecycle = copy.deepcopy(self._working_notes_lifecycle)
        if rebound or expired:
            lifecycle = {
                "trigger_action_id": action_id,
                "rebound_note_ids": rebound,
                "expired_notes": expired,
            }
        return {
            "findings": retained,
            "source_bodies_by_note_id": {
                finding["note_id"]: copy.deepcopy(
                    self._working_note_source_bodies[finding["note_id"]]
                )
                for finding in retained
                if finding["note_id"] in self._working_note_source_bodies
            },
            "lifecycle": lifecycle,
        }

    def _restore_working_notes_state(self, state: dict[str, Any]) -> None:
        self._working_findings = copy.deepcopy(state["findings"])
        self._working_note_source_bodies = copy.deepcopy(state["source_bodies_by_note_id"])
        self._working_notes_lifecycle = copy.deepcopy(state.get("lifecycle"))

    def working_notes_lifecycle_receipt(self) -> dict[str, Any] | None:
        """Public lifecycle decisions exclude independently retained source bodies."""

        return copy.deepcopy(self._working_notes_lifecycle)

    def verification_concerns(self, *, diff_hash: str | None = None) -> dict[str, Any]:
        """Project advisory concerns without refreshing/expiring source observations."""

        return project_verification_concerns(
            self._verification_state,
            diff_hash=diff_hash if diff_hash is not None else self.current_diff_hash,
        )

    def working_notes(self, *, diff_hash: str | None = None) -> dict[str, Any]:
        self._refresh_working_source_notes()
        current_hash = diff_hash if diff_hash is not None else self.current_diff_hash
        findings = copy.deepcopy(self._working_findings)
        source_hashes: dict[str, str | None] = {}
        for finding in findings:
            current = True
            for evidence in finding["evidence"]:
                if evidence["kind"] == "source":
                    path = evidence["path"]
                    if path not in source_hashes:
                        try:
                            _, selected = self._tracked_path(path)
                            source_hashes[path] = sha256_bytes(selected.read_bytes())
                        except (PatchLoopError, OSError):
                            source_hashes[path] = None
                    current &= source_hashes[path] == evidence["file_hash"]
                else:
                    current &= evidence.get("diff_hash") in {None, current_hash}
                    if "check_result" in evidence:
                        observed_hash = evidence.get("diff_hash")
                        evidence["check_result"]["currency"] = (
                            "unknown" if observed_hash is None else
                            "current" if observed_hash == current_hash else "historical"
                        )
            finding["status"] = "current" if current else "historical"
            finding["interpretation_status"] = "model_authored_unverified"
        return {
            "findings": findings,
            "available_note_ids": [finding["note_id"] for finding in findings],
            "open_question": self._working_open_question,
            "verification": self.verification_concerns(diff_hash=current_hash),
            "last_update_diagnostics": (
                list(self._working_notes_turns.values())[-1].get("diagnostics", [])[:3]
                if self._working_notes_turns else []
            ),
            "last_update_result": (
                copy.deepcopy(list(self._working_notes_turns.values())[-1].get("receipt"))
                if self._working_notes_turns else None
            ),
            "last_source_lifecycle": self.working_notes_lifecycle_receipt(),
            "interpretation": (
                "Model-authored public observations, approach, and unverified behavior; "
                "status=current means cited evidence is current, not that the statement "
                "was revalidated. Sources are validated, interpretations are not. "
                "Cite behavior-bearing lines for behavior claims and revisit them after edits. "
                "available_note_ids is the current retained-ID authority; update receipts "
                "describe the earlier before-tool-batch state. Update an existing note_id "
                "to refine it even when citations change; null creates a separate note."
            ),
        }

    def context_spans(self, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
        excluded = exclude or set()
        candidates = self._validated_source_spans()
        return list(project_observed_sources(
            candidates,
            native_spans=[span for span in candidates if span["span_id"] in excluded],
            priorities=self._source_projection_priorities(),
            editable_paths={
                span["path"] for span in candidates if self._path_allowed(span["path"])
            },
        ).source_spans)

    def evidence_ledger(self, *, diff_hash: str | None = None) -> dict[str, Any]:
        """Project bounded, public, deterministic facts about observed evidence."""

        current_hash = diff_hash if diff_hash is not None else self.current_diff_hash
        with self._lock:
            coverage = copy.deepcopy(self._coverage_by_diff.get(current_hash, {}))
            searches = copy.deepcopy(self._search_observations_by_diff.get(current_hash, []))
            canonical_searches = self._search_ledger_by_diff.get(current_hash, {})
            result_fingerprints = self._search_result_fingerprints_by_diff.get(
                current_hash, set()
            )
            latest = copy.deepcopy(self._latest_inspection_by_diff.get(current_hash))
            recent_inspections = copy.deepcopy(
                self._recent_inspections_by_diff.get(current_hash, [])
            )
        covered_files = [
            {
                "path": path,
                "editable": self._path_allowed(path),
                "ranges": [[start, end] for start, end in ranges[:16]],
                "covered_line_count": self._range_size(ranges),
            }
            for path, ranges in sorted(coverage.items())[:16]
        ]
        searches.sort(key=lambda item: int(item.get("last_observed_seq", 0)), reverse=True)
        aggregate_counts = {
            "total_search_count": len(searches),
            "unique_query_count": len(canonical_searches),
            "zero_match_count": sum(item.get("outcome") == "zero_match" for item in searches),
            "covered_only_count": sum(item.get("outcome") == "covered_only" for item in searches),
            "new_coverage_count": sum(
                item.get("outcome") in {"new_coverage", "supporting_coverage"}
                for item in searches
            ),
            "supporting_coverage_count": sum(
                item.get("outcome") == "supporting_coverage" for item in searches
            ),
            "unique_result_fingerprint_count": len(result_fingerprints),
        }
        for item in searches:
            item.pop("last_observed_seq", None)
        if latest is not None:
            latest.pop("last_observed_seq", None)
        for observation in recent_inspections:
            observation.pop("last_observed_seq", None)
        return {
            "diff_hash": current_hash,
            "covered_files": covered_files,
            "search_summary": aggregate_counts,
            "canonical_searches": searches[:12],
            "latest_inspection_intent": latest,
            "recent_inspections": recent_inspections,
        }

    def mutation_readiness(
        self,
        *,
        current_paths: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        paths = list(
            self.current_mutation_evidence_paths()
            if current_paths is None
            else current_paths
        )
        return {
            "state": "ready_to_attempt" if paths else "needs_anchor_evidence",
            "readiness_basis": "current_delivered_editable_source_evidence",
            "current_anchor_evidence_paths": paths,
            "visible_check_contract_available": bool(self.public_task.visible_checks),
            "rule": (
                "ready_to_attempt means this input delivers non-empty current editable source. "
                "The exact proposed replacement still requires contiguous evidence validation "
                "at admission; neither anchor coverage for an unspecified edit nor semantic "
                "sufficiency is established by readiness."
            ),
        }

    def mutation_scope_budget(self, *, summary: DiffSummary | None = None) -> dict[str, Any]:
        current = summary if summary is not None else self.current_diff
        constraints = self.public_task.constraints
        return {
            "current_diff_lines": current.diff_lines,
            "max_diff_lines": constraints.max_diff_lines,
            "remaining_diff_line_headroom": max(
                0, constraints.max_diff_lines - current.diff_lines
            ),
            "current_changed_file_count": len(current.changed_files),
            "max_changed_files": constraints.max_changed_files,
            "remaining_changed_file_headroom": max(
                0, constraints.max_changed_files - len(current.changed_files)
            ),
            "rule": (
                "Headroom is not the replacement line count; the gateway validates the "
                "complete candidate diff."
            ),
        }

    def last_mutation_failure_class(self) -> str | None:
        failure = (
            self.last_failed_mutation.get("mutation_failure")
            if isinstance(self.last_failed_mutation, dict)
            else None
        )
        value = failure.get("class") if isinstance(failure, dict) else None
        return value if isinstance(value, str) else None

    def failed_mutation_target_path(self) -> str | None:
        replacement = (
            self.last_failed_mutation.get("replacement")
            if isinstance(self.last_failed_mutation, dict)
            else None
        )
        path = replacement.get("path") if isinstance(replacement, dict) else None
        if not isinstance(path, str):
            return None
        try:
            normalized, _ = self._tracked_path(path)
        except (PatchLoopError, OSError):
            return None
        return normalized

    def current_mutation_evidence_paths(self) -> tuple[str, ...]:
        """Return allowed files backed by at least one current public evidence span."""

        current = self._current_evidence_path_rows()
        return tuple(sorted(path for _, path in current if self._path_allowed(path)))

    def current_evidence_paths(self) -> tuple[str, ...]:
        """Return a bounded set of current public files available for repair rereads."""

        return tuple(sorted(path for _, path in self._current_evidence_path_rows()[:8]))

    def _current_evidence_path_rows(self) -> list[tuple[int, str]]:
        """Validate each observed path once, then rank its current observations."""

        observations: dict[str, int] = {}
        for span in self._validated_source_spans():
            if span["content"]:
                observations[span["path"]] = max(
                    observations.get(span["path"], 0), int(span.get("last_observed_seq", 0))
                )
        current_paths = [(sequence, path) for path, sequence in observations.items()]
        current_paths.sort(key=lambda item: (-item[0], item[1]))
        return current_paths

    def has_current_mutation_evidence(self) -> bool:
        return bool(self.current_mutation_evidence_paths())

    def actionable_last_successful_mutation(
        self,
        *,
        diff_hash: str | None = None,
    ) -> dict[str, Any] | None:
        """Project accepted mutation facts without asking the model to select evidence."""

        if not isinstance(self.last_successful_mutation, dict):
            return None
        projected = copy.deepcopy(self.last_successful_mutation)
        projected.pop("evidence_span_ids", None)
        projected.pop("anchor_evidence_span_id", None)
        projected.pop("edit_anchor", None)
        postimage = self._current_postimage_evidence(diff_hash=diff_hash)
        projected.pop("postimage_evidence_span_id", None)
        projected.pop("actionable_evidence_span_ids", None)
        projected["postimage_evidence_available"] = postimage is not None
        return projected

    @property
    def current_diff(self):
        return WorkspaceManager.diff_summary(self.workspace)

    @property
    def current_diff_hash(self) -> str:
        return self.current_diff.patch_hash

    def visible_checks_pass(self, *, diff_hash: str | None = None) -> bool:
        expected = {check.id for check in self.public_task.visible_checks}
        if not expected:
            return bool(self.current_diff.patch)
        current_hash = diff_hash if diff_hash is not None else self.current_diff_hash
        rows = self.checks_by_diff.get(current_hash, {})
        return expected == {check_id for check_id, row in rows.items() if row.get("passed") is True}

    def visible_check_status(self, *, diff_hash: str | None = None) -> list[dict[str, Any]]:
        current_hash = diff_hash if diff_hash is not None else self.current_diff_hash
        rows = self.checks_by_diff.get(current_hash, {})
        status: list[dict[str, Any]] = []
        for check in self.public_task.visible_checks:
            row = rows.get(check.id)
            if row is None:
                status.append(
                    {
                        "check_id": check.id,
                        "diff_hash": current_hash,
                        "status": "NOT_RUN",
                        "failure_signature": None,
                    }
                )
                continue
            status.append(
                {
                    "check_id": check.id,
                    "diff_hash": current_hash,
                    "status": "PASS" if row.get("passed") is True else "FAIL",
                    "failure_signature": row.get("failure_signature"),
                }
            )
        return status

    def current_public_failure(self, *, diff_hash: str | None = None) -> dict[str, Any] | None:
        """Return the active public counterexample through inspection and repair turns."""

        if self._active_failed_check is None:
            return None
        stored = self._active_failed_check.get("public_check_failure")
        if not isinstance(stored, dict):
            return None
        projected = copy.deepcopy(stored)
        current_hash = diff_hash if diff_hash is not None else self.current_diff_hash
        failure_hash = projected.get("diff_hash")
        projected["current_diff_hash"] = current_hash
        projected["phase"] = (
            "repair_current_diff" if failure_hash == current_hash else "awaiting_recheck"
        )
        comparison = projected.get("comparison_with_previous_failure")
        same_site = (
            isinstance(comparison, dict)
            and comparison.get("relation") == "same_public_failure_site"
        )
        remaining = max(0, self.limits.max_accepted_mutations - self.accepted_mutations)
        projected["mutation_pressure"] = {
            "same_public_failure_site": same_site,
            "accepted_mutations_remaining": remaining,
            "guidance": (
                "Use the observed failure to choose a public inspection or repair; "
                "source-line order does not establish execution history."
            ),
        }
        return projected

    def remaining_visible_check_ids(self, *, diff_hash: str | None = None) -> list[str]:
        return [
            row["check_id"]
            for row in self.visible_check_status(diff_hash=diff_hash)
            if row["status"] != "PASS"
        ]

    def unrun_visible_check_ids(self, *, diff_hash: str | None = None) -> list[str]:
        return [
            row["check_id"]
            for row in self.visible_check_status(diff_hash=diff_hash)
            if row["status"] == "NOT_RUN"
        ]

    def ready_to_submit(self) -> bool:
        summary = self.current_diff
        return (
            bool(summary.patch)
            and not summary.untracked_files
            and self.visible_checks_pass(diff_hash=summary.patch_hash)
        )

    def state_snapshot(
        self, *, projection: SourceProjection | None = None
    ) -> DevGatewayStateSnapshot:
        """Capture diff, evidence, and check state once for one scheduler decision."""

        summary = self.current_diff
        current_paths = self._current_evidence_path_rows() if projection is None else []
        mutation_paths = (
            tuple(sorted(path for _, path in current_paths if self._path_allowed(path)))
            if projection is None else projection.editable_paths
        )
        evidence_paths = (
            tuple(sorted(path for _, path in current_paths[:8]))
            if projection is None else projection.evidence_paths
        )
        status = tuple(self.visible_check_status(diff_hash=summary.patch_hash))
        remaining = tuple(row["check_id"] for row in status if row["status"] != "PASS")
        unrun = tuple(row["check_id"] for row in status if row["status"] == "NOT_RUN")
        ready = (
            bool(summary.patch)
            and not summary.untracked_files
            and all(row["status"] == "PASS" for row in status)
        )
        return DevGatewayStateSnapshot(
            diff=summary,
            mutation_evidence_paths=mutation_paths,
            evidence_paths=evidence_paths,
            visible_check_status=status,
            remaining_visible_check_ids=remaining,
            unrun_visible_check_ids=unrun,
            ready_to_submit=ready,
        )

    def execute_batch(self, calls: list[RequestedTool]) -> list[DevToolResult]:
        shape = validate_tool_batch(calls, max_parallel_reads=self.limits.max_parallel_reads)
        if shape == "single_action":
            return [self.execute(calls[0])]
        with ThreadPoolExecutor(max_workers=len(calls), thread_name_prefix="dev-read") as pool:
            futures = [pool.submit(self.execute, call) for call in calls]
            return [future.result() for future in futures]

    def execute(self, call: RequestedTool) -> DevToolResult:
        turn_decision = (
            call.turn_decision.model_dump(mode="json") if call.turn_decision is not None else None
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
        # Durable results above are safe to replay even after the active deadline.
        if self.deadline is not None and pending is None:
            self.deadline.check()
        baseline_summary = self.current_diff
        baseline = (
            str(pending["baseline_diff_hash"])
            if pending is not None and call.name == "replace_text"
            else baseline_summary.patch_hash
        )
        preflight_error: Exception | None = None
        mutation_admitted: bool | None = None
        mutation_anchor_evidence_span_id: str | None = None
        candidate_summary: DiffSummary | None = None
        if pending is None:
            if call.name == "replace_text":
                try:
                    validated = self._validate_replacement_intent(call.arguments)
                    mutation_anchor_evidence_span_id = validated.anchor_evidence_span_id
                    candidate_summary = WorkspaceManager.preview_text_replacement(
                        self.workspace,
                        validated.path,
                        validated.after_bytes,
                        baseline_diff_hash=baseline,
                    )
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
                    "baseline_changed_files": baseline_summary.changed_files,
                    "mutation_expected_worktree_diff_hash": (
                        candidate_summary.patch_hash if candidate_summary is not None else None
                    ),
                    "mutation_preimage_file_hash": (
                        sha256_bytes(validated.before_bytes)
                        if call.name == "replace_text" and mutation_admitted is True else None
                    ),
                    "mutation_preimage_newline": (
                        self._source_text(validated.before_bytes)[1]
                        if call.name == "replace_text" and mutation_admitted is True else None
                    ),
                    "mutation_anchor_offset": (
                        validated.anchor_offset
                        if call.name == "replace_text" and mutation_admitted is True else None
                    ),
                    "execution_identity": (
                        {"run_id": self.journal.run_id, "action_id": call.action_id}
                        if call.name in {"run_check", "run_probe"} else None
                    ),
                    "mutation_admitted": mutation_admitted,
                    "mutation_anchor_evidence_span_id": (mutation_anchor_evidence_span_id),
                    "mutation_anchor_evidence_span_ids": (
                        list(validated.anchor_evidence_span_ids)
                        if call.name == "replace_text" and mutation_admitted is True else []
                    ),
                    "mutation_anchor_start_line": (
                        validated.anchor_start_line
                        if call.name == "replace_text" and mutation_admitted is True
                        else None
                    ),
                    "mutation_anchor_end_line": (
                        validated.anchor_end_line
                        if call.name == "replace_text" and mutation_admitted is True
                        else None
                    ),
                    "mutation_target_path": (
                        validated.path
                        if call.name == "replace_text" and mutation_admitted is True
                        else None
                    ),
                    "mutation_expected_postimage_file_hash": (
                        sha256_bytes(validated.after_bytes)
                        if call.name == "replace_text" and mutation_admitted is True
                        else None
                    ),
                    "mutation_generated_patch": (
                        validated.generated_patch
                        if call.name == "replace_text" and mutation_admitted is True
                        else None
                    ),
                    "mutation_postimage_start_line": (
                        validated.postimage_start_line
                        if call.name == "replace_text" and mutation_admitted is True
                        else None
                    ),
                },
            )
        try:
            if preflight_error is not None:
                raise preflight_error
            if pending is not None and call.name == "replace_text":
                output = self._reconcile_or_apply(call.arguments, pending)
                evidence_cache_hit = False
            elif call.name == "replace_text":
                assert candidate_summary is not None
                output = self._apply_text_replacement(
                    call.arguments,
                    expected_candidate_hash=candidate_summary.patch_hash,
                    baseline_diff_hash=baseline,
                )
                evidence_cache_hit = False
            elif call.name == "run_check":
                output = self._run_check(
                    call.arguments["check_id"],
                    execution_identity={"run_id": self.journal.run_id, "action_id": call.action_id},
                )
                evidence_cache_hit = False
            elif call.name == "run_probe":
                if pending is not None and pending["baseline_diff_hash"] != baseline:
                    raise RecoveryError("pending probe workspace no longer matches admitted diff")
                output = self._run_probe(
                    **call.arguments,
                    execution_identity={"run_id": self.journal.run_id, "action_id": call.action_id},
                )
                evidence_cache_hit = False
            elif call.name in READ_TOOLS:
                if self.deadline is not None:
                    self.deadline.check()
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
                    turn_decision=turn_decision,
                    action_id=call.action_id,
                )
                with self._lock:
                    self._read_cache[cache_key] = self._cacheable_read_output(output)
            else:
                if self.deadline is not None:
                    self.deadline.check()
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
        except ExecutionDeadlineExceeded:
            raise
        except (PatchLoopError, ValidationError, ValueError, OSError, RuntimeError) as exc:
            code = exc.code if isinstance(exc, PatchLoopError) else "TOOL_CONTRACT_ERROR"
            failure_output = (
                copy.deepcopy(exc.details) if isinstance(exc, PatchLoopError) else {}
            )
            if call.name in READ_TOOLS:
                failure_output["read_request_hash"] = read_request_hash
            elif call.name == "replace_text" and "mutation_failure" not in failure_output:
                failure_output["mutation_failure"] = self._replacement_failure_details(
                    message=str(exc),
                    baseline=baseline_summary,
                )
            if call.name == "replace_text":
                mutation_failure = failure_output.get("mutation_failure")
                if isinstance(mutation_failure, dict):
                    required_anchor = failure_output.get("required_anchor")
                    if isinstance(required_anchor, dict):
                        mutation_failure.setdefault("required_anchor", required_anchor)
                    mutation_failure.setdefault(
                        "recovery_key",
                        self._mutation_recovery_key(call.arguments, baseline),
                    )
            result = DevToolResult(
                action_id=call.action_id,
                input_hash=input_hash,
                tool=call.name,
                status="failed",
                output=failure_output,
                error_code=code,
                message=str(exc)[:1_000],
                workspace_diff_hash=(
                    self.current_diff_hash if call.name == "replace_text" else baseline
                ),
            )
        finished_payload: dict[str, Any] = {
            "action_id": call.action_id,
            "input_hash": input_hash,
            "result": result.model_dump(mode="json"),
        }
        if result.status == "succeeded" and result.tool == "replace_text":
            finished_payload["working_notes_state"] = self._refreshed_working_notes_state(
                action_id=call.action_id,
            )
        self.journal.append(
            "action_finished",
            finished_payload,
        )
        if result.status == "succeeded":
            if result.tool == "replace_text":
                self._restore_working_notes_state(finished_payload["working_notes_state"])
                self._accept_successful_mutation(result.output, refresh_notes=False)
            elif result.tool == "run_check":
                self._remember_check(result.output)
        elif result.tool == "replace_text":
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
        if name == "replace_text":
            return self._apply_text_replacement(arguments)
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
        lines = source_lines(raw.decode("utf-8"))
        content, actual_end, truncated = bounded_lines(lines, start_line, end_line)
        spans = (
            [self._span(normalized, start_line, actual_end, content, sha256_bytes(raw))]
            if actual_end >= start_line else []
        )
        return {
            "path": normalized,
            "start_line": start_line,
            "end_line": actual_end if spans else None,
            "spans": spans,
            "line_count": len(lines),
            "truncated": truncated,
            "eof": start_line > len(lines),
            "next_start_line": actual_end + 1 if truncated else None,
            "diagnostic": (
                "requested source line exceeds the 24000-character output limit"
                if truncated and not spans else None
            ),
        }

    def _search_files(self, query: str, path_glob: str = "**/*") -> dict[str, Any]:
        if not isinstance(query, str) or not query or len(query) > 500:
            raise ContractError("search query must contain 1-500 characters")
        pattern = safe_relative_path(path_glob, field_name="search path_glob")
        spans: list[dict[str, Any]] = []
        content_chars = 0
        searched_file_count = 0
        truncated = False
        for selected in sorted(self.workspace.rglob("*")):
            if len(spans) >= 20 or content_chars >= 24_000:
                truncated = True
                break
            if not selected.is_file() or selected.is_symlink():
                continue
            relative = selected.relative_to(self.workspace).as_posix()
            if ".git" in selected.relative_to(self.workspace).parts:
                continue
            if relative.startswith(".patchloop-hidden/") or not matches_source_glob(
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
            searched_file_count += 1
            lines = source_lines(text)
            for index, line in enumerate(lines, start=1):
                if query not in line:
                    continue
                start = max(1, index - 2)
                end = min(len(lines), index + 2)
                content, actual_end, clipped = bounded_lines(
                    lines, start, end, max_chars=24_000 - content_chars
                )
                if actual_end < index:
                    start = index
                    content, actual_end, clipped = bounded_lines(
                        lines, start, index, max_chars=24_000 - content_chars
                    )
                truncated |= clipped
                if actual_end < index:
                    continue
                spans.append(self._span(relative, start, actual_end, content, sha256_bytes(raw)))
                content_chars += len(content)
                if len(spans) >= 20:
                    truncated = True
                    break
        return {
            "query": query,
            "path_glob": pattern,
            "searched_file_count": searched_file_count,
            "spans": spans,
            "truncated": truncated,
        }

    def _path_allowed(self, path: str) -> bool:
        constraints = self.public_task.constraints
        return any(
            fnmatch.fnmatchcase(path, item) for item in constraints.allowed_paths
        ) and not any(fnmatch.fnmatchcase(path, item) for item in constraints.forbidden_paths)

    @staticmethod
    def _generated_replacement_patch(path: str, before: str, after: str) -> str:
        body = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                n=3,
                lineterm="\n",
            )
        )
        patch = f"diff --git a/{path} b/{path}\n{body}"
        if not body:
            raise ContractError("exact replacement produced no source change")
        if len(patch) > _MAX_MUTATION_HUNK_CHARS:
            raise ContractError("generated mutation diff exceeds the bounded context limit")
        return patch

    def _current_postimage_evidence(
        self,
        *,
        diff_hash: str | None = None,
    ) -> dict[str, Any] | None:
        latest = self.last_successful_mutation or {}
        expected_span_id = latest.get("postimage_evidence_span_id")
        current_diff_hash = diff_hash if diff_hash is not None else self.current_diff_hash
        if not isinstance(expected_span_id, str) or latest.get("diff_hash") != current_diff_hash:
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

    def _mutation_postimage_evidence(
        self,
        *,
        path: str,
        focus_start_line: int,
        focus_line_count: int,
        diff_hash: str,
    ) -> dict[str, Any] | None:
        normalized, current = self._tracked_path(path)
        raw = current.read_bytes()
        current_lines = source_lines(raw.decode("utf-8"))
        if not current_lines:
            start_index = 0
            end_index = 0
        else:
            focus_index = min(max(0, focus_start_line - 1), len(current_lines) - 1)
            start_index = max(0, focus_index - 3)
            end_index = min(
                len(current_lines),
                max(focus_index + max(1, focus_line_count) + 3, start_index + 1),
            )
        content, actual_end, truncated = bounded_lines(
            current_lines, start_index + 1, end_index
        )
        if current_lines and actual_end < focus_index + 1:
            start_index = focus_index
            content, actual_end, truncated = bounded_lines(
                current_lines, start_index + 1, end_index
            )
        if actual_end < start_index + 1:
            return None
        span = self._span(
            normalized,
            start_index + 1,
            actual_end,
            content,
            sha256_bytes(raw),
        )
        return {
            **span,
            "origin": "accepted_mutation",
            "source_diff_hash": diff_hash,
            "truncated": truncated,
        }

    @staticmethod
    def _source_text(raw: bytes) -> tuple[str, str]:
        decoded = raw.decode("utf-8")
        if "\r\n" in decoded and "\n" in decoded.replace("\r\n", ""):
            raise ContractError("replace_text refuses mixed newline styles")
        if "\r" in decoded.replace("\r\n", ""):
            raise ContractError("replace_text refuses legacy carriage-return newlines")
        newline = "\r\n" if "\r\n" in decoded else "\n"
        return decoded.replace("\r\n", "\n"), newline

    def _validate_replacement_intent(self, arguments: dict[str, Any]) -> _ValidatedReplacement:
        intent = TextReplacementIntent.model_validate(arguments)
        if self.current_diff.untracked_files:
            raise ContractError("replace_text refuses a workspace with untracked files")
        anchor_path, anchor_file = self._tracked_path(intent.path)
        if not self._path_allowed(anchor_path):
            raise ContractError("replacement changes a path outside the public task allowance")
        before_bytes = anchor_file.read_bytes()
        anchor_text, newline = self._source_text(before_bytes)
        positions = [
            match.start() for match in re.finditer(re.escape(intent.old_text), anchor_text)
        ]
        if len(positions) < intent.occurrence:
            raise ContractError("exact edit anchor is stale or absent from the current source")
        position = positions[intent.occurrence - 1]
        anchor_start_line = anchor_text[:position].count("\n") + 1
        anchor_end_line = anchor_text[:position + len(intent.old_text) - 1].count("\n") + 1
        after_text = (
            anchor_text[:position]
            + intent.new_text
            + anchor_text[position + len(intent.old_text) :]
        )
        after_bytes = after_text.replace("\n", newline).encode("utf-8")
        generated_patch = self._generated_replacement_patch(anchor_path, anchor_text, after_text)
        current_file_hash = sha256_bytes(before_bytes)
        lines = source_lines(anchor_text)
        with self._lock:
            covering_spans = sorted(
                (
                    dict(span)
                    for span in self.spans.values()
                    if span.get("path") == anchor_path
                    and span.get("file_hash") == current_file_hash
                    and valid_observed_span(span, lines, current_file_hash)
                    and span["start_line"] <= anchor_end_line
                    and span["end_line"] >= anchor_start_line
                    and isinstance(span.get("span_id"), str)
                ),
                key=lambda span: (
                    -int(span.get("last_observed_seq", 0)),
                    str(span["span_id"]),
                ),
            )
        if not spans_cover_range(covering_spans, anchor_start_line, anchor_end_line):
            raise ContractError(
                "current evidence spans do not cover the exact replacement anchor contiguously",
                details={
                    "required_anchor": {
                        "path": anchor_path,
                        "start_line": anchor_start_line,
                        "end_line": anchor_end_line,
                    }
                },
            )
        return _ValidatedReplacement(
            intent=intent,
            path=anchor_path,
            before_bytes=before_bytes,
            after_bytes=after_bytes,
            generated_patch=generated_patch,
            anchor_offset=position,
            anchor_start_line=anchor_start_line,
            anchor_end_line=anchor_end_line,
            postimage_start_line=anchor_start_line,
            anchor_evidence_span_id=str(covering_spans[0]["span_id"]),
            anchor_evidence_span_ids=tuple(str(span["span_id"]) for span in covering_spans),
        )

    def _mutation_result_output(
        self,
        *,
        generated_patch: str,
        intent: TextReplacementIntent,
        path: str,
        postimage_start_line: int,
        summary: Any,
        source_replacement: SourceReplacement,
        recovered_after_crash: bool = False,
    ) -> dict[str, Any]:
        postimage_path = ensure_within(self.workspace, path)
        mutation_evidence = (
            self._mutation_postimage_evidence(
                path=path,
                focus_start_line=postimage_start_line,
                focus_line_count=max(1, intent.new_text.count("\n") + 1),
                diff_hash=summary.patch_hash,
            )
            if postimage_path.is_file() and not postimage_path.is_symlink()
            else None
        )
        revalidated_spans = self._revalidated_spans(
            paths=[path], diff_hash=summary.patch_hash, replacement=source_replacement,
        )
        causal_revision = intent.causal_revision
        mutation = {
            "hypothesis": intent.hypothesis,
            "expected_behavior": intent.expected_behavior,
            "plan_hash": sha256_json(intent.model_dump(mode="json")),
            "postimage_evidence_span_id": (
                mutation_evidence["span_id"] if mutation_evidence is not None else None
            ),
            "evidence_binding": "gateway_current_observation",
            "changed_hunk": generated_patch,
            "replacement_hash": sha256_json(
                {
                    "path": path,
                    "old_text": intent.old_text,
                    "new_text": intent.new_text,
                    "occurrence": intent.occurrence,
                }
            ),
            "causal_revision": (
                causal_revision.model_dump(mode="json") if causal_revision is not None else None
            ),
            "changed_files": summary.changed_files,
            "diff_hash": summary.patch_hash,
        }
        output = {
            "patch_hash": sha256_bytes(generated_patch.encode("utf-8")),
            "worktree_diff_hash": summary.patch_hash,
            "changed_files": [path],
            "mutation": mutation,
            "mutation_evidence": mutation_evidence,
            "revalidated_spans": revalidated_spans,
            "alternative_requirement_satisfied": self.requires_alternative,
        }
        if recovered_after_crash:
            output["recovered_after_crash"] = True
        return output

    def _apply_text_replacement(
        self,
        arguments: dict[str, Any],
        *,
        expected_candidate_hash: str | None = None,
        baseline_diff_hash: str | None = None,
    ) -> dict[str, Any]:
        if self.accepted_mutations >= self.limits.max_accepted_mutations:
            raise ContractError("accepted mutation limit reached")
        validated = self._validate_replacement_intent(arguments)
        _, target = self._tracked_path(validated.path)
        if target.read_bytes() != validated.before_bytes:
            raise ContractError("exact replacement preimage changed before application")
        baseline_summary = self.current_diff
        if baseline_diff_hash is not None and baseline_summary.patch_hash != baseline_diff_hash:
            raise RecoveryError("mutation baseline changed after admission")
        if expected_candidate_hash is None:
            expected_candidate_hash = WorkspaceManager.preview_text_replacement(
                self.workspace, validated.path, validated.after_bytes,
                baseline_diff_hash=baseline_summary.patch_hash,
            ).patch_hash
        if self.deadline is not None:
            self.deadline.check()
        WorkspaceManager.atomic_replace_source(
            self.workspace, validated.path, validated.after_bytes,
        )
        try:
            summary = self.current_diff
            if summary.patch_hash != expected_candidate_hash:
                raise RecoveryError("applied worktree differs from admitted complete candidate")
            scope = verify_scope(summary, self.public_task.constraints)
            if not scope.passed:
                failure = {
                    "class": "scope_violation",
                    "baseline": self._bounded_diff_identity(baseline_summary),
                    "candidate": self._bounded_diff_identity(summary),
                    "delta_from_baseline": {
                        "diff_lines": summary.diff_lines - baseline_summary.diff_lines,
                        "changed_file_count": (
                            len(summary.changed_files) - len(baseline_summary.changed_files)
                        ),
                    },
                    "violations": copy.deepcopy(scope.details.get("typed_violations", [])),
                    "rolled_back": False,
                }
                raise ContractError(
                    "mutation violates scope: " + "; ".join(scope.violations),
                    details={"mutation_failure": failure},
                )
            output = self._mutation_result_output(
                generated_patch=validated.generated_patch,
                intent=validated.intent,
                path=validated.path,
                postimage_start_line=validated.postimage_start_line,
                summary=summary,
                source_replacement=SourceReplacement(
                    validated.before_bytes, validated.after_bytes, validated.anchor_offset,
                    validated.intent.old_text, validated.intent.new_text,
                ),
            )
        except Exception as exc:
            WorkspaceManager.atomic_replace_source(
                self.workspace, validated.path, validated.before_bytes,
            )
            if isinstance(exc, PatchLoopError):
                failure = exc.details.get("mutation_failure")
                if isinstance(failure, dict):
                    failure["rolled_back"] = True
            raise
        return output

    @staticmethod
    def _bounded_diff_identity(summary: Any) -> dict[str, Any]:
        return {
            "diff_hash": summary.patch_hash,
            "diff_lines": summary.diff_lines,
            "changed_files": list(summary.changed_files)[:16],
        }

    @classmethod
    def _replacement_failure_details(cls, *, message: str, baseline: Any) -> dict[str, Any]:
        lowered = message.lower()
        if any(
            fragment in lowered
            for fragment in ("anchor is stale", "anchor is absent", "preimage changed")
        ):
            failure_class = "anchor_invalid"
        elif any(
            fragment in lowered
            for fragment in ("evidence span", "current evidence", "cover the exact replacement")
        ):
            failure_class = "evidence_invalid"
        else:
            failure_class = "replacement_contract"
        return {
            "class": failure_class,
            "baseline": cls._bounded_diff_identity(baseline),
            "candidate": None,
            "delta_from_baseline": None,
            "violations": [],
            "rolled_back": True,
        }

    @staticmethod
    def _mutation_recovery_key(arguments: dict[str, Any], baseline_diff_hash: str) -> str:
        """Identify one failed replacement lineage without storing another raw copy."""

        return sha256_json(
            {
                "baseline_diff_hash": baseline_diff_hash,
                "anchor_hash": sha256_json(
                    {
                        "path": arguments.get("path"),
                        "old_text": arguments.get("old_text"),
                        "occurrence": arguments.get("occurrence"),
                    }
                ),
            }
        )

    def _reconcile_or_apply(
        self, arguments: dict[str, Any], pending: dict[str, Any]
    ) -> dict[str, Any]:
        baseline = pending.get("baseline_diff_hash")
        current = self.current_diff_hash
        if current == baseline:
            return self._apply_text_replacement(
                arguments,
                expected_candidate_hash=pending.get("mutation_expected_worktree_diff_hash"),
                baseline_diff_hash=baseline,
            )
        if pending.get("mutation_admitted") is not True:
            raise RecoveryError("pending mutation was not admitted before the crash")
        intent = TextReplacementIntent.model_validate(arguments)
        path = safe_relative_path(intent.path)
        if pending.get("mutation_target_path") != path:
            raise RecoveryError("pending mutation target does not match its admission")
        _, target = self._tracked_path(path)
        expected_postimage_hash = pending.get("mutation_expected_postimage_file_hash")
        if (
            not isinstance(expected_postimage_hash, str)
            or sha256_bytes(target.read_bytes()) != expected_postimage_hash
        ):
            raise RecoveryError("pending mutation cannot be reconciled with the current workspace")
        generated_patch = pending.get("mutation_generated_patch")
        if not isinstance(generated_patch, str) or not generated_patch:
            raise RecoveryError("pending mutation is missing its generated diff")
        summary = self.current_diff
        if summary.patch_hash != pending.get("mutation_expected_worktree_diff_hash"):
            raise RecoveryError("pending complete candidate diff does not match its admission")
        if summary.untracked_files:
            raise RecoveryError("reconciled mutation contains untracked files")
        # Recover the exact admitted map for both successful evidence rebinding and rollback.
        after_bytes = target.read_bytes()
        text, _ = self._source_text(after_bytes)
        newline = pending.get("mutation_preimage_newline")
        if newline not in {"\n", "\r\n"}:
            raise RecoveryError("mutation recovery is missing its original newline style")
        offset = pending.get("mutation_anchor_offset")
        if (
            type(offset) is not int or not 0 <= offset <= len(text)
            or text[offset:offset + len(intent.new_text)] != intent.new_text
        ):
            raise RecoveryError("mutation recovery is missing its admitted replacement offset")
        before = (text[:offset] + intent.old_text + text[offset + len(intent.new_text):])
        before_bytes = before.replace("\n", newline).encode("utf-8")
        if sha256_bytes(before_bytes) != pending.get("mutation_preimage_file_hash"):
            raise RecoveryError("mutation recovery does not match the admitted preimage")
        scope = verify_scope(summary, self.public_task.constraints)
        if not scope.passed:
            # Undo only the exact admitted replacement, never arbitrary workspace drift.
            WorkspaceManager.atomic_replace_source(self.workspace, path, before_bytes)
            restored = self.current_diff
            if restored.patch_hash != baseline:
                raise RecoveryError("scope rollback did not restore the complete baseline")
            raise ContractError(
                "mutation violates scope: " + "; ".join(scope.violations),
                details={"mutation_failure": {
                    "class": "scope_violation",
                    "baseline": self._bounded_diff_identity(restored),
                    "candidate": self._bounded_diff_identity(summary),
                    "delta_from_baseline": {
                        "diff_lines": summary.diff_lines - restored.diff_lines,
                        "changed_file_count": (
                            len(summary.changed_files) - len(restored.changed_files)
                        ),
                    },
                    "violations": copy.deepcopy(scope.details.get("typed_violations", [])),
                    "rolled_back": True,
                }},
            )
        anchor_evidence_span_id = pending.get("mutation_anchor_evidence_span_id")
        if not isinstance(anchor_evidence_span_id, str):
            raise RecoveryError("pending mutation is missing its gateway evidence binding")
        return self._mutation_result_output(
            generated_patch=generated_patch,
            intent=intent,
            path=path,
            postimage_start_line=int(pending.get("mutation_postimage_start_line", 1)),
            summary=summary,
            source_replacement=SourceReplacement(
                before_bytes, after_bytes, offset, intent.old_text, intent.new_text,
            ),
            recovered_after_crash=True,
        )

    def _run_check(
        self, check_id: str, *, execution_identity: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        checks = {check.id: check for check in self.public_task.visible_checks}
        try:
            check = checks[check_id]
        except KeyError as exc:
            raise ContractError(f"unknown public check: {check_id}") from exc
        diff_hash = self.current_diff_hash
        if self.deadline is not None:
            self.deadline.check()
        if getattr(self.sandbox, "supports_execution_deadline", False):
            outcome = self.sandbox.run_check(
                self.workspace, check,
                deadline=self.deadline, execution_identity=execution_identity,
            )
        else:
            outcome = self.sandbox.run_check(self.workspace, check)
        deadline_exhausted = getattr(outcome, "deadline_exhausted", False)
        cleanup_failed = getattr(outcome, "cleanup_failed", False)
        passed = (
            not outcome.timed_out and not deadline_exhausted and not cleanup_failed
            and outcome.exit_code in check.expected_exit_codes
        )
        execution_policy_hash = (
            sha256_json(outcome.execution_policy) if outcome.execution_policy is not None else None
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
        output = {
            "check_id": check_id,
            "diff_hash": diff_hash,
            "passed": passed,
            "failure_signature": None if passed else signature,
            "exit_code": outcome.exit_code,
            "timed_out": outcome.timed_out,
            "truncated": outcome.truncated,
            "deadline_exhausted": deadline_exhausted,
            "cleanup_failed": cleanup_failed,
            "stdout": outcome.stdout[-12_000:],
            "stderr": outcome.stderr[-12_000:],
            "execution_policy": outcome.execution_policy,
            "execution_policy_hash": execution_policy_hash,
        }
        if not passed and not deadline_exhausted and not cleanup_failed:
            output["public_check_failure"] = self._public_check_failure(
                check=check,
                diff_hash=diff_hash,
                failure_signature=signature,
                stdout=outcome.stdout[-12_000:],
                stderr=outcome.stderr[-12_000:],
            )
        return output

    def _run_probe(
        self, question: str, python_source: str, *, execution_identity: dict[str, str],
    ) -> dict[str, Any]:
        if self.probe_sandbox is None:
            raise ContractError("public probes are disabled for this run")
        if not isinstance(question, str) or not 1 <= len(question) <= 500:
            raise ContractError("probe question must contain 1-500 characters")
        if not isinstance(python_source, str) or not 1 <= len(python_source) <= 8_000:
            raise ContractError("probe source must contain 1-8000 characters")
        baseline = self.current_diff_hash
        output = self.probe_sandbox.run_probe(
            self.workspace, question, python_source,
            deadline=self.deadline, execution_identity=execution_identity,
        )
        observed_diff_hash = self.current_diff_hash
        receipt = {**output, "question": question, "diff_hash": baseline,
                   "workspace_diff_hash": baseline}
        if observed_diff_hash != baseline:
            raise RecoveryError(
                "managed workspace changed during probe execution",
                details={**receipt, "observed_diff_hash": observed_diff_hash},
            )
        return receipt

    def _remember_check(self, output: dict[str, Any]) -> None:
        diff_hash = str(output["diff_hash"])
        check_id = str(output["check_id"])
        self.checks_by_diff.setdefault(diff_hash, {})[check_id] = output
        if output.get("deadline_exhausted") or output.get("cleanup_failed"):
            return
        if output.get("passed") is True:
            if (
                self._active_failed_check is not None
                and self._active_failed_check.get("check_id") == check_id
            ):
                self._active_failed_check = None
                self.requires_alternative = False
            return
        stored = copy.deepcopy(output)
        self._failed_check_history.append(stored)
        self._active_failed_check = stored
        identity = self._failure_identity(output)
        if identity is not None:
            diffs = self.failure_diffs.setdefault(identity, set())
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
