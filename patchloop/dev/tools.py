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

from patchloop.contracts import PublicTask
from patchloop.dev.contracts import (
    DEV_READ_TOOLS,
    DEV_SINGLE_ACTION_TOOLS,
    DevLimits,
    DevToolResult,
    RequestedTool,
    StopIntent,
    TextReplacementIntent,
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
_MAX_MUTATION_HUNK_CHARS = 24_000
_PATCH_ERROR_LINE = re.compile(r"corrupt patch at (?:<stdin>:|line )(\d+)")
_PATCH_SOURCE_LINE = re.compile(r"patch failed: ([^:\r\n]+):(\d+)")
_MUTATION_TOOLS = frozenset({"replace_text", "apply_git_diff"})


@dataclass(frozen=True)
class _ValidatedReplacement:
    intent: TextReplacementIntent
    path: str
    before_bytes: bytes
    after_bytes: bytes
    generated_patch: str
    anchor_start_line: int
    anchor_end_line: int
    postimage_start_line: int
    actionable_evidence_span_ids: list[str]
    ignored_historical_evidence_span_ids: list[str]


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
                "current evidence, and exact current source anchor are part of this mutation. "
                "An accepted mutation's bounded post-image is current evidence for a "
                "same-file repair; there is no separate planning tool."
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
                            "current evidence for this file."
                        ),
                        "maxLength": 20_000,
                    },
                    "new_text": {"type": "string", "maxLength": 20_000},
                    "occurrence": {"type": "integer", "minimum": 1, "maximum": 100},
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
                    "causal_revision": {
                        "type": ["object", "null"],
                        "description": (
                            "Required only after the same public failure recurs across "
                            "distinct diffs."
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
                    "evidence_span_ids",
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
    decision_modes = {
        "search_files": "inspect",
        "read_file": "inspect",
        "run_check": "verify",
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
        self._coverage_by_diff: dict[str, dict[str, list[tuple[int, int]]]] = {}
        self._search_ledger_by_diff: dict[str, dict[str, dict[str, Any]]] = {}
        self._recorded_search_actions_by_diff: dict[str, set[str]] = {}
        self._search_observations_by_diff: dict[str, list[dict[str, Any]]] = {}
        self._search_result_fingerprints_by_diff: dict[str, set[str]] = {}
        self._latest_inspection_by_diff: dict[str, dict[str, Any]] = {}
        self._ledger_seq = 0
        self.checks_by_diff: dict[str, dict[str, dict[str, Any]]] = {}
        self.failure_diffs: dict[str, set[str]] = {}
        self.requires_alternative = False
        self.accepted_mutations = 0
        self.last_successful_mutation: dict[str, Any] | None = None
        self._latest_historical_evidence_span_ids: set[str] = set()
        self.last_failed_mutation: dict[str, Any] | None = None
        self._hydrate()

    def _hydrate(self) -> None:
        action_starts: dict[str, dict[str, Any]] = {}
        for event in self.journal.events():
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
                started = action_starts.get(result.action_id, {})
                arguments = started.get("arguments", {})
                historical_ids = (
                    arguments.get("evidence_span_ids", []) if isinstance(arguments, dict) else []
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
        evidence_span_ids = arguments.get("evidence_span_ids")
        if not isinstance(evidence_span_ids, list):
            evidence_span_ids = []
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
                "Use the one targeted read_file opportunity for this path, then repair or "
                "replace the failed mutation."
            )
        else:
            next_action = (
                "Repair or explicitly replace this failed mutation using the preserved exact "
                "replacement, or stop_task."
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
            "evidence_span_ids": [
                value[:500] for value in evidence_span_ids[:8] if isinstance(value, str)
            ],
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
    ) -> dict[str, Any]:
        spans = [span for span in output.get("spans", []) if isinstance(span, dict)]
        with self._lock:
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
                        self._ledger_seq += 1
                        searches[search_key] = {
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
                            "last_observed_seq": self._ledger_seq,
                        }
                        observation = copy.deepcopy(searches[search_key])
                        observation.pop("outcome_counts", None)
                        observation.pop("observation_count", None)
                        self._search_observations_by_diff.setdefault(
                            workspace_diff_hash, []
                        ).append(observation)
                        self._search_result_fingerprints_by_diff.setdefault(
                            workspace_diff_hash, set()
                        ).add(result_fingerprint)
            if turn_decision is not None:
                self._ledger_seq += 1
                self._latest_inspection_by_diff[workspace_diff_hash] = {
                    "basis": self._bounded_string(turn_decision.get("basis"), 800),
                    "evidence_goal": self._bounded_string(turn_decision.get("evidence_goal"), 500),
                    "evidence_span_ids": [
                        str(span["span_id"])
                        for span in spans[:8]
                        if isinstance(span.get("span_id"), str)
                    ],
                    "last_observed_seq": self._ledger_seq,
                }
        gain_units = new_lines
        if turn_decision is not None:
            with self._lock:
                self._latest_inspection_by_diff[workspace_diff_hash]["marginal_evidence_gain"] = (
                    gain_units > 0
                )
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
        if result.workspace_diff_hash is not None:
            intent = result.output.get("inspection_intent")
            self._record_read_ledger(
                tool=result.tool,
                workspace_diff_hash=result.workspace_diff_hash,
                output=result.output,
                turn_decision=intent if isinstance(intent, dict) else None,
                action_id=result.action_id,
            )

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
            span_id for span_id in evidence_values if isinstance(span_id, str)
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
        turn_decision: dict[str, Any] | None,
        action_id: str,
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
        decorated["evidence_gain"] = self._record_read_ledger(
            tool=tool,
            workspace_diff_hash=workspace_diff_hash,
            output=decorated,
            turn_decision=turn_decision,
            action_id=action_id,
        )
        if turn_decision is not None:
            decorated["inspection_intent"] = copy.deepcopy(turn_decision)
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

    def _revalidated_spans(self, *, paths: Sequence[str], diff_hash: str) -> list[dict[str, Any]]:
        """Rebind unchanged, uniquely occurring evidence to the post-mutation file hash."""

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
        rebound: list[dict[str, Any]] = []
        seen: set[str] = set()
        for span in candidates:
            path = str(span["path"])
            try:
                normalized, current = self._tracked_path(path)
                raw = current.read_bytes()
                text = raw.decode("utf-8")
            except (PatchLoopError, OSError, UnicodeDecodeError):
                continue
            content = str(span["content"])
            positions = [match.start() for match in re.finditer(re.escape(content), text)]
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

    def context_spans(self, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
        excluded = exclude or set()
        with self._lock:
            candidates = [
                dict(span) for span_id, span in self.spans.items() if span_id not in excluded
            ]
        candidates.sort(key=lambda span: int(span.get("last_observed_seq", 0)), reverse=True)
        return candidates[:8]

    def evidence_ledger(self) -> dict[str, Any]:
        """Project bounded, public, deterministic facts about observed evidence."""

        diff_hash = self.current_diff_hash
        with self._lock:
            coverage = copy.deepcopy(self._coverage_by_diff.get(diff_hash, {}))
            searches = copy.deepcopy(self._search_observations_by_diff.get(diff_hash, []))
            canonical_searches = self._search_ledger_by_diff.get(diff_hash, {})
            result_fingerprints = self._search_result_fingerprints_by_diff.get(diff_hash, set())
            latest = copy.deepcopy(self._latest_inspection_by_diff.get(diff_hash))
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
        return {
            "diff_hash": diff_hash,
            "covered_files": covered_files,
            "search_summary": aggregate_counts,
            "canonical_searches": searches[:12],
            "latest_inspection_intent": latest,
        }

    def mutation_readiness(self) -> dict[str, Any]:
        current_paths = list(self.current_mutation_evidence_paths())
        return {
            "state": "ready_to_attempt" if current_paths else "needs_anchor_evidence",
            "readiness_basis": "current_exact_anchor_only",
            "current_anchor_evidence_paths": current_paths,
            "visible_check_contract_available": bool(self.public_task.visible_checks),
            "rule": (
                "ready_to_attempt means only that a current exact mutation anchor exists; it "
                "does not assert that the semantic solution is sufficient. When the causal "
                "hypothesis and expected public behavior are also known, prefer replace_text."
            ),
        }

    def mutation_scope_budget(self) -> dict[str, Any]:
        summary = self.current_diff
        constraints = self.public_task.constraints
        return {
            "current_diff_lines": summary.diff_lines,
            "max_diff_lines": constraints.max_diff_lines,
            "remaining_diff_line_headroom": max(
                0, constraints.max_diff_lines - summary.diff_lines
            ),
            "current_changed_file_count": len(summary.changed_files),
            "max_changed_files": constraints.max_changed_files,
            "remaining_changed_file_headroom": max(
                0, constraints.max_changed_files - len(summary.changed_files)
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

    def current_evidence_paths(self) -> tuple[str, ...]:
        """Return a bounded set of current public files available for repair rereads."""

        with self._lock:
            candidates = sorted(
                (dict(span) for span in self.spans.values()),
                key=lambda span: int(span.get("last_observed_seq", 0)),
                reverse=True,
            )
        current_paths: list[str] = []
        for span in candidates:
            path = span.get("path")
            file_hash = span.get("file_hash")
            if not isinstance(path, str) or not isinstance(file_hash, str) or path in current_paths:
                continue
            try:
                normalized, current = self._tracked_path(path)
                if sha256_bytes(current.read_bytes()) == file_hash:
                    current_paths.append(normalized)
            except (PatchLoopError, OSError):
                continue
            if len(current_paths) >= 8:
                break
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
        actionable_ids = [str(postimage["span_id"])] if postimage is not None else []
        projected["postimage_evidence_span_id"] = actionable_ids[0] if actionable_ids else None
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
        return [row["check_id"] for row in self.visible_check_status() if row["status"] != "PASS"]

    def unrun_visible_check_ids(self) -> list[str]:
        return [
            row["check_id"] for row in self.visible_check_status() if row["status"] == "NOT_RUN"
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
        baseline_summary = self.current_diff
        baseline = baseline_summary.patch_hash
        preflight_error: Exception | None = None
        mutation_admitted: bool | None = None
        mutation_anchor_evidence_span_id: str | None = None
        mutation_actionable_evidence_span_ids: list[str] = []
        mutation_ignored_historical_evidence_span_ids: list[str] = []
        if pending is None:
            if call.name == "replace_text":
                try:
                    validated = self._validate_replacement_intent(call.arguments)
                    mutation_anchor_evidence_span_id = next(
                        (
                            span_id
                            for span_id in validated.actionable_evidence_span_ids
                            if self.spans.get(span_id, {}).get("path") == validated.path
                        ),
                        None,
                    )
                    mutation_actionable_evidence_span_ids = validated.actionable_evidence_span_ids
                    mutation_ignored_historical_evidence_span_ids = (
                        validated.ignored_historical_evidence_span_ids
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
                    "mutation_admitted": mutation_admitted,
                    "mutation_anchor_evidence_span_id": (mutation_anchor_evidence_span_id),
                    "mutation_actionable_evidence_span_ids": (
                        mutation_actionable_evidence_span_ids
                    ),
                    "mutation_ignored_historical_evidence_span_ids": (
                        mutation_ignored_historical_evidence_span_ids
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
                    turn_decision=turn_decision,
                    action_id=call.action_id,
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
            result = DevToolResult(
                action_id=call.action_id,
                input_hash=input_hash,
                tool=call.name,
                status="failed",
                output=failure_output,
                error_code=code,
                message=str(exc)[:1_000],
                workspace_diff_hash=baseline,
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
            if result.tool == "replace_text":
                self._accept_successful_mutation(
                    result.output,
                    historical_evidence_span_ids=call.arguments.get("evidence_span_ids", []),
                )
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

    def _current_postimage_evidence(self) -> dict[str, Any] | None:
        latest = self.last_successful_mutation or {}
        expected_span_id = latest.get("postimage_evidence_span_id")
        current_diff_hash = self.current_diff_hash
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
        focus_start_line: int,
        focus_line_count: int,
        diff_hash: str,
    ) -> dict[str, Any]:
        normalized, current = self._tracked_path(path)
        raw = current.read_bytes()
        current_lines = raw.decode("utf-8").splitlines()
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
        if self.requires_alternative and intent.causal_revision is None:
            raise ContractError(
                "repeated public failure across two diffs requires falsified_prior_hypothesis "
                "and alternative_mechanism in causal_revision on the next mutation"
            )
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
        anchor_end_line = anchor_start_line + intent.old_text.count("\n")
        after_text = (
            anchor_text[:position]
            + intent.new_text
            + anchor_text[position + len(intent.old_text) :]
        )
        after_bytes = after_text.replace("\n", newline).encode("utf-8")
        generated_patch = self._generated_replacement_patch(anchor_path, anchor_text, after_text)
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
        matching_ids = []
        for span in evidence:
            if span["path"] != anchor_path:
                continue
            start_line = span.get("start_line")
            end_line = span.get("end_line")
            if (
                type(start_line) is int
                and type(end_line) is int
                and start_line <= anchor_start_line
                and end_line >= anchor_end_line
            ):
                matching_ids.append(str(span["span_id"]))
        anchor_evidence_span_id = matching_ids[0] if matching_ids else None
        if anchor_evidence_span_id is None:
            anchor_evidence_span_id = self._accepted_mutation_anchor_evidence_id(
                anchor_path=anchor_path,
                anchor_text=intent.old_text,
            )
        if anchor_evidence_span_id is None:
            raise ContractError(
                "at least one current evidence span must cover the exact replacement anchor"
            )
        actionable_ids = list(
            dict.fromkeys(
                [
                    *(str(span["span_id"]) for span in evidence),
                    anchor_evidence_span_id,
                ]
            )
        )
        return _ValidatedReplacement(
            intent=intent,
            path=anchor_path,
            before_bytes=before_bytes,
            after_bytes=after_bytes,
            generated_patch=generated_patch,
            anchor_start_line=anchor_start_line,
            anchor_end_line=anchor_end_line,
            postimage_start_line=anchor_start_line,
            actionable_evidence_span_ids=actionable_ids,
            ignored_historical_evidence_span_ids=ignored_historical_ids,
        )

    def _mutation_result_output(
        self,
        *,
        generated_patch: str,
        intent: TextReplacementIntent,
        path: str,
        postimage_start_line: int,
        summary: Any,
        actionable_evidence_span_ids: list[str],
        ignored_historical_evidence_span_ids: list[str],
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
        revalidated_spans = self._revalidated_spans(paths=[path], diff_hash=summary.patch_hash)
        causal_revision = intent.causal_revision
        mutation = {
            "hypothesis": intent.hypothesis,
            "expected_behavior": intent.expected_behavior,
            "plan_hash": sha256_json(intent.model_dump(mode="json")),
            "postimage_evidence_span_id": (
                mutation_evidence["span_id"] if mutation_evidence is not None else None
            ),
            "actionable_evidence_span_ids": (
                [str(mutation_evidence["span_id"])] if mutation_evidence is not None else []
            ),
            "input_evidence_counts": {
                "current": len(actionable_evidence_span_ids),
                "historical_ignored": len(ignored_historical_evidence_span_ids),
            },
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

    def _apply_text_replacement(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.accepted_mutations >= self.limits.max_accepted_mutations:
            raise ContractError("accepted mutation limit reached")
        validated = self._validate_replacement_intent(arguments)
        _, target = self._tracked_path(validated.path)
        if target.read_bytes() != validated.before_bytes:
            raise ContractError("exact replacement preimage changed before application")
        baseline_summary = self.current_diff
        target.write_bytes(validated.after_bytes)
        try:
            summary = self.current_diff
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
                actionable_evidence_span_ids=(validated.actionable_evidence_span_ids),
                ignored_historical_evidence_span_ids=(
                    validated.ignored_historical_evidence_span_ids
                ),
            )
        except Exception as exc:
            target.write_bytes(validated.before_bytes)
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

    def _reconcile_or_apply(
        self, arguments: dict[str, Any], pending: dict[str, Any]
    ) -> dict[str, Any]:
        baseline = pending.get("baseline_diff_hash")
        current = self.current_diff_hash
        if current == baseline:
            return self._apply_text_replacement(arguments)
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
        baseline_changed_files = pending.get("baseline_changed_files")
        expected_changed_files = sorted(
            {
                path,
                *(
                    baseline_changed_files
                    if isinstance(baseline_changed_files, list)
                    and all(isinstance(item, str) for item in baseline_changed_files)
                    else []
                ),
            }
        )
        if summary.changed_files != expected_changed_files:
            raise RecoveryError("pending mutation changed files do not match its admission")
        if (
            summary.untracked_files
            or not verify_scope(summary, self.public_task.constraints).passed
        ):
            raise RecoveryError("reconciled mutation violates workspace scope")
        anchor_evidence_span_id = pending.get("mutation_anchor_evidence_span_id")
        if not isinstance(anchor_evidence_span_id, str):
            with self._lock:
                anchor_evidence_span_id = next(
                    (
                        span_id
                        for span_id in intent.evidence_span_ids
                        if self.spans.get(span_id, {}).get("path") == path
                    ),
                    None,
                )
        actionable_evidence_span_ids = pending.get("mutation_actionable_evidence_span_ids")
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
                    dict.fromkeys([*actionable_evidence_span_ids, anchor_evidence_span_id])
                )
        ignored_historical_evidence_span_ids = pending.get(
            "mutation_ignored_historical_evidence_span_ids"
        )
        if not isinstance(ignored_historical_evidence_span_ids, list) or not all(
            isinstance(span_id, str) for span_id in ignored_historical_evidence_span_ids
        ):
            ignored_historical_evidence_span_ids = []
        return self._mutation_result_output(
            generated_patch=generated_patch,
            intent=intent,
            path=path,
            postimage_start_line=int(pending.get("mutation_postimage_start_line", 1)),
            summary=summary,
            actionable_evidence_span_ids=actionable_evidence_span_ids,
            ignored_historical_evidence_span_ids=(ignored_historical_evidence_span_ids),
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
