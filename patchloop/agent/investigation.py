"""Deterministic within-run investigation evidence for stateless agents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, Budget, Checkpoint, EventType, PublicTask, RunEvent
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import (
    canonical_json,
    ensure_within,
    safe_relative_path,
    sha256_text,
)

INVESTIGATION_POLICY_VERSION = "investigation-policy-v1"
INVESTIGATION_LEDGER_SCHEMA = "investigation-ledger-v1"
INVESTIGATION_LOOP_SCHEMA = "investigation-loop-v1"
TOOL_REPLAY_SCHEMA = "tool-replayed-v2"
TOOL_ADMISSION_SCHEMA = "tool-admission-blocked-v1"
INVESTIGATION_POLICY_VERSION_V2 = "investigation-policy-v2"
INVESTIGATION_LEDGER_SCHEMA_V2 = "investigation-ledger-v2"
TOOL_ADMISSION_SCHEMA_V2 = "tool-admission-blocked-v2"
EVIDENCE_SATURATION_POLICY_VERSION = "evidence-saturation-v1"
EVIDENCE_SATURATION_THRESHOLD = 6
READ_SEARCH_POLICY_SCHEMA = "read-search-policy-v1"
INSPECTION_ADMISSION_PREFLIGHT_SCHEMA = (
    "inspection-admission-preflight-v1"
)

NO_PROGRESS_STRATEGY_THRESHOLD = 2
SEARCH_QUERY_CHARACTER_LIMIT = 500
SEARCH_GLOB_CHARACTER_LIMIT = 500
SEARCH_GLOB_SEGMENT_LIMIT = 100
LEDGER_MAX_READ_FILES = 64
LEDGER_MAX_SEARCHES = 64
LEDGER_MAX_DETAILS = 24
LEDGER_DETAIL_CHARACTER_LIMIT = 24_000
LEDGER_READ_CONTENT_LIMIT = 4_000
LEDGER_MATCH_SAMPLE_LIMIT = 12


@dataclass(frozen=True)
class InspectionRecord:
    tool: str
    arguments: dict[str, Any]
    input_hash: str
    normalized_call_hash: str
    worktree_diff_hash: str
    mutation_epoch_sequence: int | None
    call_sequence: int
    outcome_sequence: int
    action_id: str
    result: dict[str, Any]
    result_artifact: Artifact


@dataclass(frozen=True)
class EvidenceSaturationState:
    mutation_epoch_sequence: int | None
    semantic_replay_count: int
    semantic_replay_threshold: int
    saturated: bool


def validate_inspection_arguments(
    workspace: Path | None,
    tool: str,
    arguments: dict[str, Any],
    *,
    require_current_target: bool = True,
) -> None:
    """Apply the same no-side-effect validation before dispatch or admission."""

    if (
        require_current_target
        and (workspace is None or not workspace.is_dir())
    ):
        raise ContractError("inspection workspace does not exist")
    if tool == "read_file":
        if set(arguments) != {"path", "start_line", "end_line"}:
            raise ContractError("read_file requires path, start_line, and end_line")
        path = arguments.get("path")
        start_line = arguments.get("start_line")
        end_line = arguments.get("end_line")
        if (
            not isinstance(path, str)
            or type(start_line) is not int
            or type(end_line) is not int
            or start_line < 1
            or end_line < start_line
            or end_line - start_line > 500
        ):
            raise ContractError(
                "read_file range must contain at most 501 ordered lines"
            )
        safe_relative_path(path)
        if require_current_target:
            assert workspace is not None
            target = ensure_within(workspace, path)
            if not target.is_file():
                raise ContractError(f"file does not exist: {path}")
        return
    if tool == "search_files":
        if (
            not set(arguments).issubset({"query", "path_glob"})
            or "query" not in arguments
        ):
            raise ContractError("search_files requires query and optional path_glob")
        query = arguments.get("query")
        path_glob = arguments.get("path_glob", "**/*")
        if (
            not isinstance(query, str)
            or not query
            or len(query) > SEARCH_QUERY_CHARACTER_LIMIT
        ):
            raise ContractError("search query must contain between 1 and 500 characters")
        if (
            not isinstance(path_glob, str)
            or len(path_glob) > SEARCH_GLOB_CHARACTER_LIMIT
        ):
            raise ContractError(
                "path_glob must contain at most 500 characters"
            )
        normalized_glob = safe_relative_path(
            path_glob,
            field_name="path_glob",
        )
        glob_segments = normalized_glob.split("/")
        if len(glob_segments) > SEARCH_GLOB_SEGMENT_LIMIT:
            raise ContractError(
                "path_glob must contain at most 100 path segments"
            )
        if normalized_glob == "." or (
            len(normalized_glob) >= 2
            and normalized_glob[0].isalpha()
            and normalized_glob[1] == ":"
        ):
            raise ContractError(
                "path_glob must be a non-drive relative glob pattern"
            )
        if any(
            "**" in segment and segment != "**"
            for segment in glob_segments
        ):
            raise ContractError(
                "path_glob recursive wildcard must occupy an entire path segment"
            )
        return
    raise ContractError(f"unsupported inspection tool: {tool}")


def mutation_epoch(events: list[RunEvent]) -> int | None:
    """Return the latest successful mutation boundary."""

    return max(
        (
            event.sequence
            for event in events
            if event.type == EventType.PATCH_APPLIED
        ),
        default=None,
    )


def active_epoch_events(events: list[RunEvent]) -> tuple[int | None, list[RunEvent]]:
    epoch = mutation_epoch(events)
    return epoch, [
        event
        for event in events
        if epoch is None or event.sequence > epoch
    ]


def evidence_saturation_state(
    events: list[RunEvent],
) -> EvidenceSaturationState:
    """Derive the v8 read/search saturation state from the durable prefix."""

    epoch = mutation_epoch(events)
    replay_count = sum(
        event.type == EventType.TOOL_REPLAYED
        and event.payload.get("semantic_replay") is True
        and (epoch is None or event.sequence > epoch)
        for event in events
    )
    return EvidenceSaturationState(
        mutation_epoch_sequence=epoch,
        semantic_replay_count=replay_count,
        semantic_replay_threshold=EVIDENCE_SATURATION_THRESHOLD,
        saturated=replay_count >= EVIDENCE_SATURATION_THRESHOLD,
    )


def _artifact_from_payload(
    payload: dict[str, Any],
    *,
    descriptor_key: str,
    role: str,
) -> Artifact:
    try:
        artifact = Artifact.model_validate(payload.get(descriptor_key))
    except ValueError as exc:
        raise RecoveryError(f"{role} lacks a valid artifact descriptor") from exc
    if (
        payload.get("artifact_id") != artifact.artifact_id
        or payload.get("artifact_path") != artifact.path
    ):
        raise RecoveryError(f"{role} conflicts with its artifact descriptor")
    return artifact


def _read_json_artifact(
    store: ArtifactStore,
    artifact: Artifact,
    *,
    role: str,
) -> dict[str, Any]:
    raw = store.read_bytes(artifact)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"{role} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryError(f"{role} must contain a JSON object")
    return value


def _validate_read_result(
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    required = {
        "path": str,
        "start_line": int,
        "end_line": int,
        "content": str,
        "actual_start_line": (int, type(None)),
        "actual_end_line": (int, type(None)),
        "line_count": int,
        "total_lines": int,
        "eof_reached": bool,
        "file_content_hash": str,
        "worktree_diff_hash": str,
    }
    if any(not isinstance(result.get(key), kind) for key, kind in required.items()):
        raise RecoveryError("read_file result artifact has invalid investigation metadata")
    if (
        result["path"] != arguments.get("path")
        or result["start_line"] != arguments.get("start_line")
        or result["end_line"] != arguments.get("end_line")
        or result["line_count"] < 0
        or result["total_lines"] < 0
    ):
        raise RecoveryError("read_file result conflicts with its recorded input")
    if result["line_count"] == 0:
        if (
            result["actual_start_line"] is not None
            or result["actual_end_line"] is not None
        ):
            raise RecoveryError("empty read_file result declares a returned range")
    elif (
        result["actual_start_line"] != result["start_line"]
        or result["actual_end_line"]
        != result["actual_start_line"] + result["line_count"] - 1
        or result["actual_end_line"] > result["total_lines"]
    ):
        raise RecoveryError("read_file returned range metadata is inconsistent")


def _validate_search_result(
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if (
        not isinstance(result.get("query"), str)
        or not isinstance(result.get("path_glob"), str)
        or not isinstance(result.get("matches"), list)
        or type(result.get("match_count")) is not int
        or not isinstance(result.get("truncated"), bool)
        or not isinstance(result.get("worktree_diff_hash"), str)
        or result["query"] != arguments.get("query")
        or result["path_glob"] != arguments.get("path_glob", "**/*")
        or result["match_count"] != len(result["matches"])
    ):
        raise RecoveryError("search_files result artifact has invalid investigation metadata")
    for match in result["matches"]:
        if (
            not isinstance(match, dict)
            or not isinstance(match.get("path"), str)
            or type(match.get("line")) is not int
            or not isinstance(match.get("text"), str)
        ):
            raise RecoveryError("search_files result contains an invalid match")


def load_inspection_records(
    events: list[RunEvent],
    artifact_store: ArtifactStore,
    *,
    worktree_diff_hash: str | None = None,
) -> list[InspectionRecord]:
    """Load successful read/search evidence from the active mutation epoch."""

    epoch, active = active_epoch_events(events)
    outcomes = {
        event.correlation_id: event
        for event in active
        if event.type == EventType.TOOL_SUCCEEDED
        and event.correlation_id
        and event.payload.get("tool") in {"read_file", "search_files"}
    }
    records: list[InspectionRecord] = []
    for call in active:
        if (
            call.type != EventType.TOOL_CALLED
            or call.payload.get("tool") not in {"read_file", "search_files"}
            or not call.correlation_id
        ):
            continue
        outcome = outcomes.get(call.correlation_id)
        if outcome is None:
            continue
        call_diff_hash = call.payload.get("worktree_diff_hash")
        if not isinstance(call_diff_hash, str):
            raise RecoveryError(
                "v4 inspection call lacks a worktree diff identity"
            )
        if worktree_diff_hash is not None and call_diff_hash != worktree_diff_hash:
            continue
        input_artifact = _artifact_from_payload(
            call.payload,
            descriptor_key="input_artifact",
            role="inspection call",
        )
        input_payload = _read_json_artifact(
            artifact_store,
            input_artifact,
            role="inspection input artifact",
        )
        tool = str(call.payload["tool"])
        arguments = input_payload.get("input")
        if input_payload.get("tool") != tool or not isinstance(arguments, dict):
            raise RecoveryError("inspection input artifact conflicts with its call")
        expected_input_hash = sha256_text(
            canonical_json({"tool": tool, "input": arguments})
        )
        input_hash = call.payload.get("input_hash")
        normalized_call_hash = call.payload.get("normalized_call_hash")
        if input_hash != expected_input_hash or not isinstance(
            normalized_call_hash, str
        ):
            raise RecoveryError("inspection call identity failed verification")
        expected_normalized_hash = sha256_text(
            canonical_json(
                {
                    "tool": tool,
                    "input": arguments,
                    "worktree_diff_hash": call_diff_hash,
                    "state_marker": None,
                }
            )
        )
        if normalized_call_hash != expected_normalized_hash:
            raise RecoveryError("inspection normalized call hash is invalid")

        result_artifact = _artifact_from_payload(
            outcome.payload,
            descriptor_key="result_artifact",
            role="inspection outcome",
        )
        result = _read_json_artifact(
            artifact_store,
            result_artifact,
            role="inspection result artifact",
        )
        if result.get("worktree_diff_hash") != call_diff_hash:
            raise RecoveryError("inspection result belongs to a different worktree")
        if tool == "read_file":
            _validate_read_result(arguments, result)
        else:
            _validate_search_result(arguments, result)
        records.append(
            InspectionRecord(
                tool=tool,
                arguments=arguments,
                input_hash=input_hash,
                normalized_call_hash=normalized_call_hash,
                worktree_diff_hash=call_diff_hash,
                mutation_epoch_sequence=epoch,
                call_sequence=call.sequence,
                outcome_sequence=outcome.sequence,
                action_id=call.correlation_id,
                result=result,
                result_artifact=result_artifact,
            )
        )
    return sorted(records, key=lambda item: item.call_sequence)


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(ranges):
        if end < start:
            continue
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def range_is_covered(
    ranges: list[tuple[int, int]],
    start: int,
    end: int,
) -> bool:
    return any(left <= start and right >= end for left, right in merge_ranges(ranges))


def read_coverage(
    records: list[InspectionRecord],
    path: str,
) -> list[tuple[int, int]]:
    return merge_ranges(
        [
            (
                int(record.result["actual_start_line"]),
                int(record.result["actual_end_line"]),
            )
            for record in records
            if record.tool == "read_file"
            and record.result["path"] == path
            and record.result["actual_start_line"] is not None
            and record.result["actual_end_line"] is not None
        ]
    )


def requested_read_is_covered(
    records: list[InspectionRecord],
    *,
    path: str,
    start_line: int,
    end_line: int,
    total_lines: int,
) -> bool:
    if start_line > total_lines:
        return any(
            record.tool == "read_file"
            and record.result["path"] == path
            and record.result["total_lines"] == total_lines
            and record.result["eof_reached"] is True
            and record.result["end_line"] >= total_lines
            for record in records
        )
    effective_end = min(end_line, total_lines)
    return range_is_covered(
        read_coverage(records, path),
        start_line,
        effective_end,
    )


def reconstruct_covered_read(
    records: list[InspectionRecord],
    *,
    path: str,
    start_line: int,
    end_line: int,
    worktree_diff_hash: str,
) -> tuple[dict[str, Any], list[InspectionRecord]] | None:
    """Reconstruct a requested range exclusively from verified result CAS."""

    sources = [
        record
        for record in records
        if record.tool == "read_file" and record.result["path"] == path
    ]
    if not sources:
        return None
    total_lines = int(sources[-1].result["total_lines"])
    file_content_hash = str(sources[-1].result["file_content_hash"])
    if any(
        record.result["total_lines"] != total_lines
        or record.result["file_content_hash"] != file_content_hash
        for record in sources
    ):
        raise RecoveryError("read coverage contains conflicting file identities")
    if not requested_read_is_covered(
        records,
        path=path,
        start_line=start_line,
        end_line=end_line,
        total_lines=total_lines,
    ):
        return None

    actual_end = min(end_line, total_lines)
    if start_line > total_lines:
        used_sources = [
            record
            for record in sources
            if record.result["eof_reached"] is True
        ][-1:]
        return (
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "content": "",
                "actual_start_line": None,
                "actual_end_line": None,
                "line_count": 0,
                "total_lines": total_lines,
                "eof_reached": True,
                "file_content_hash": file_content_hash,
                "worktree_diff_hash": worktree_diff_hash,
            },
            used_sources,
        )

    lines: dict[int, str] = {}
    used: dict[int, InspectionRecord] = {}
    for record in sources:
        line_count = int(record.result["line_count"])
        if line_count == 0:
            continue
        content_lines = str(record.result["content"]).split("\n")
        if len(content_lines) != line_count:
            raise RecoveryError(
                "read result content conflicts with its line count"
            )
        source_start = int(record.result["actual_start_line"])
        for offset, content in enumerate(content_lines):
            line_number = source_start + offset
            existing = lines.get(line_number)
            if existing is not None and existing != content:
                raise RecoveryError("read coverage contains conflicting line content")
            lines[line_number] = content
            if start_line <= line_number <= actual_end:
                used[record.call_sequence] = record
    try:
        content = "\n".join(
            lines[line_number]
            for line_number in range(start_line, actual_end + 1)
        )
    except KeyError as exc:
        raise RecoveryError("read coverage could not reconstruct a covered range") from exc
    return (
        {
            "path": path,
            "start_line": start_line,
            "end_line": end_line,
            "content": content,
            "actual_start_line": start_line,
            "actual_end_line": actual_end,
            "line_count": actual_end - start_line + 1,
            "total_lines": total_lines,
            "eof_reached": end_line >= total_lines,
            "file_content_hash": file_content_hash,
            "worktree_diff_hash": worktree_diff_hash,
        },
        list(used.values()),
    )


def search_match_key(match: dict[str, Any]) -> tuple[str, int, str]:
    return str(match["path"]), int(match["line"]), str(match["text"])


def prior_search_match_keys(
    records: list[InspectionRecord],
) -> set[tuple[str, int, str]]:
    return {
        search_match_key(match)
        for record in records
        if record.tool == "search_files"
        for match in record.result["matches"]
    }


def nominal_tail_reserve(
    task: PublicTask,
    *,
    context_policy_version: str = "phase-evidence-v4",
) -> dict[str, int]:
    """Reserve room for one corrective lifecycle and one feedback turn."""

    lifecycle_tools = (
        4
        + 2 * len(task.visible_checks)
        + (
            1
            if context_policy_version
            in {
                "phase-evidence-v6",
                "phase-evidence-v7",
                "phase-evidence-v8",
            }
            else 0
        )
    )
    return {
        "tool_calls": lifecycle_tools,
        "model_calls": (
            4
            if context_policy_version
            in {
                "phase-evidence-v6",
                "phase-evidence-v7",
                "phase-evidence-v8",
            }
            else 3
        ),
        "feedback_model_calls": 1,
    }


def investigation_policy_version(context_policy_version: str) -> str:
    if context_policy_version in {
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
    }:
        return INVESTIGATION_POLICY_VERSION_V2
    return INVESTIGATION_POLICY_VERSION


def investigation_ledger_schema(context_policy_version: str) -> str:
    if context_policy_version in {
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
    }:
        return INVESTIGATION_LEDGER_SCHEMA_V2
    return INVESTIGATION_LEDGER_SCHEMA


def tool_admission_schema(context_policy_version: str) -> str:
    if context_policy_version in {
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
    }:
        return TOOL_ADMISSION_SCHEMA_V2
    return TOOL_ADMISSION_SCHEMA


def _token_tail_projection(
    events: list[RunEvent],
    *,
    budget: Budget,
    max_output_tokens: int,
    projection_stage: str,
    reserve: dict[str, int],
) -> dict[str, Any]:
    if projection_stage not in {"pre_generation", "post_generation"}:
        raise ValueError(
            "token tail projection stage must be pre_generation or post_generation"
        )

    observations: list[dict[str, Any]] = []
    total_tokens_used = 0
    for event in events:
        if event.type != EventType.MODEL_CALLED:
            continue
        requested = event.payload.get("requested_input_tokens")
        actual_input = event.payload.get("input_tokens")
        actual_output = event.payload.get("output_tokens")
        if type(actual_input) is not int or actual_input < 0:
            raise RecoveryError(
                "v5 token tail source has invalid input token usage"
            )
        if type(actual_output) is not int or actual_output < 0:
            raise RecoveryError(
                "v5 token tail source has invalid output token usage"
            )
        total_tokens_used += actual_input + actual_output
        if type(requested) is int and requested >= 0:
            input_tokens = requested
            source = "requested_input_tokens"
        elif requested is None:
            input_tokens = actual_input
            source = "input_tokens_fallback"
        else:
            raise RecoveryError(
                "v5 token tail source has invalid requested input tokens"
            )
        observations.append(
            {
                "event_sequence": event.sequence,
                "input_tokens": input_tokens,
                "source": source,
            }
        )

    observed_values = [item["input_tokens"] for item in observations]
    max_observed = max(observed_values, default=None)
    max_positive_growth = max(
        [0]
        + [
            current - previous
            for previous, current in zip(
                observed_values,
                observed_values[1:],
                strict=False,
            )
            if current > previous
        ]
    )
    projected_next_input = (
        max_observed + max_positive_growth
        if max_observed is not None
        else None
    )
    projected_model_turns = (
        reserve["model_calls"]
        + reserve["feedback_model_calls"]
        + (1 if projection_stage == "pre_generation" else 0)
    )
    reserved_tokens = (
        max_output_tokens + projected_next_input * projected_model_turns
        if projected_next_input is not None
        else max_output_tokens
    )
    remaining_tokens = budget.max_total_tokens - total_tokens_used
    return {
        "projection_stage": projection_stage,
        "observations": observations,
        "observed_model_call_count": len(observations),
        "max_observed_input_tokens": max_observed,
        "max_positive_consecutive_growth": max_positive_growth,
        "projected_next_input_tokens": projected_next_input,
        "projected_model_turns": projected_model_turns,
        "max_output_tokens": max_output_tokens,
        "reserved_tokens": reserved_tokens,
        "total_tokens_used": total_tokens_used,
        "max_total_tokens": budget.max_total_tokens,
        "remaining_tokens": remaining_tokens,
        "admission_threshold_reached": bool(
            max_observed is not None
            and max_observed > 0
            and remaining_tokens <= reserved_tokens
        ),
    }


def tail_policy(
    task: PublicTask,
    checkpoint: Checkpoint | None,
    *,
    context_policy_version: str = "phase-evidence-v4",
    events: list[RunEvent] | None = None,
    budget: Budget | None = None,
    max_output_tokens: int | None = None,
    projection_stage: str = "pre_generation",
) -> dict[str, Any]:
    reserve = nominal_tail_reserve(
        task,
        context_policy_version=context_policy_version,
    )
    if context_policy_version in {
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
    }:
        if budget is None or max_output_tokens is None:
            raise ValueError(
                f"{context_policy_version} tail policy requires budget and "
                "max_output_tokens"
            )
        source_events = events or []
        model_calls_used = sum(
            event.type == EventType.MODEL_CALLED for event in source_events
        )
        tool_calls_used = sum(
            event.type == EventType.TOOL_CALLED for event in source_events
        )
        model_remaining = (
            budget.max_model_calls - model_calls_used
            if budget.max_model_calls is not None
            else None
        )
        tool_remaining = (
            budget.max_tool_calls - tool_calls_used
            if budget.max_tool_calls is not None
            else None
        )
        model_remaining_after_next_generation = (
            max(0, model_remaining - 1)
            if (
                projection_stage == "pre_generation"
                and model_remaining is not None
            )
            else model_remaining
        )
        tool_blocked = bool(
            tool_remaining is not None
            and tool_remaining <= reserve["tool_calls"]
        )
        model_blocked = bool(
            model_remaining_after_next_generation is not None
            and model_remaining_after_next_generation
            <= reserve["model_calls"] + reserve["feedback_model_calls"]
        )
        token_projection = _token_tail_projection(
            source_events,
            budget=budget,
            max_output_tokens=max_output_tokens,
            projection_stage=projection_stage,
            reserve=reserve,
        )
        reasons = []
        if tool_blocked:
            reasons.append("tool_tail_reserved")
        if model_blocked:
            reasons.append("model_tail_reserved")
        if token_projection["admission_threshold_reached"]:
            reasons.append("token_tail_reserved")
        return {
            "schema_version": "investigation-tail-policy-v2",
            "policy_version": INVESTIGATION_POLICY_VERSION_V2,
            "projection_stage": projection_stage,
            "nominal_reserve": reserve,
            "remaining_budget": {
                "tool_calls": tool_remaining,
                "model_calls": model_remaining,
                "model_calls_after_next_generation": (
                    model_remaining_after_next_generation
                ),
                "tokens": token_projection["remaining_tokens"],
            },
            "token_projection": token_projection,
            "exploration_admitted": not reasons,
            "block_reasons": reasons,
        }

    remaining = checkpoint.remaining_budget if checkpoint else {}
    tool_remaining = remaining.get("tool_calls")
    model_remaining = remaining.get("model_calls")
    model_remaining_after_next_generation = (
        max(0, model_remaining - 1)
        if type(model_remaining) is int
        else None
    )
    tool_blocked = (
        type(tool_remaining) is int
        and tool_remaining <= reserve["tool_calls"]
    )
    model_blocked = (
        type(model_remaining_after_next_generation) is int
        and model_remaining_after_next_generation
        <= reserve["model_calls"] + reserve["feedback_model_calls"]
    )
    reasons = []
    if tool_blocked:
        reasons.append("tool_tail_reserved")
    if model_blocked:
        reasons.append("model_tail_reserved")
    return {
        "schema_version": "investigation-tail-policy-v1",
        "policy_version": INVESTIGATION_POLICY_VERSION,
        "nominal_reserve": reserve,
        "remaining_budget": {
            "tool_calls": tool_remaining,
            "model_calls": model_remaining,
            "model_calls_after_next_generation": (
                model_remaining_after_next_generation
            ),
        },
        "exploration_admitted": not reasons,
        "block_reasons": reasons,
    }


def _detail_for_record(record: InspectionRecord) -> dict[str, Any]:
    if record.tool == "read_file":
        content = str(record.result["content"])
        truncated = len(content) > LEDGER_READ_CONTENT_LIMIT
        if truncated:
            content = content[:LEDGER_READ_CONTENT_LIMIT] + (
                "\n...[investigation detail truncated]"
            )
        return {
            "tool": record.tool,
            "source_call_sequence": record.call_sequence,
            "source_outcome_sequence": record.outcome_sequence,
            "path": record.result["path"],
            "actual_start_line": record.result["actual_start_line"],
            "actual_end_line": record.result["actual_end_line"],
            "content": content,
            "content_truncated": truncated,
            "result_content_hash": record.result_artifact.content_hash,
        }
    matches = record.result["matches"]
    return {
        "tool": record.tool,
        "source_call_sequence": record.call_sequence,
        "source_outcome_sequence": record.outcome_sequence,
        "query": record.result["query"],
        "path_glob": record.result["path_glob"],
        "match_count": record.result["match_count"],
        "truncated": record.result["truncated"],
        "sample_matches": matches[:LEDGER_MATCH_SAMPLE_LIMIT],
        "sample_omitted_count": max(0, len(matches) - LEDGER_MATCH_SAMPLE_LIMIT),
        "result_content_hash": record.result_artifact.content_hash,
    }


def _no_progress_state(
    events: list[RunEvent],
    *,
    epoch: int | None,
) -> dict[str, Any]:
    streak = 0
    max_streak = 0
    total_replays = 0
    last_progress_sequence: int | None = None
    for event in events:
        if epoch is not None and event.sequence <= epoch:
            continue
        if (
            event.type == EventType.LOOP_DETECTED
            and event.payload.get("schema_version") == INVESTIGATION_LOOP_SCHEMA
        ):
            streak += 1
            total_replays += 1
            max_streak = max(max_streak, streak)
            continue
        if (
            event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") in {"read_file", "search_files"}
        ):
            novelty = event.payload.get("novelty")
            classification = (
                novelty.get("classification")
                if isinstance(novelty, dict)
                else None
            )
            if classification == "seen_only":
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
                last_progress_sequence = event.sequence
            continue
        if (
            event.type in {EventType.TOOL_SUCCEEDED, EventType.PATCH_APPLIED}
            and event.payload.get("tool")
            not in {"read_file", "search_files"}
        ):
            streak = 0
            last_progress_sequence = event.sequence
    return {
        "streak": streak,
        "max_streak": max_streak,
        "total_semantic_replays": total_replays,
        "last_progress_sequence": last_progress_sequence,
        "strategy_change_required": streak >= NO_PROGRESS_STRATEGY_THRESHOLD,
        "strategy_threshold": NO_PROGRESS_STRATEGY_THRESHOLD,
    }


def build_investigation_ledger(
    task: PublicTask,
    events: list[RunEvent],
    checkpoint: Checkpoint | None,
    artifact_store: ArtifactStore,
    *,
    context_policy_version: str = "phase-evidence-v4",
    budget: Budget | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, Any]:
    diff_hash = checkpoint.worktree_diff_hash if checkpoint else sha256_text("")
    epoch = mutation_epoch(events)
    records = load_inspection_records(
        events,
        artifact_store,
        worktree_diff_hash=diff_hash,
    )

    grouped_reads: dict[str, list[InspectionRecord]] = {}
    searches: dict[str, InspectionRecord] = {}
    for record in records:
        if record.tool == "read_file":
            grouped_reads.setdefault(str(record.result["path"]), []).append(record)
        else:
            searches[record.normalized_call_hash] = record

    read_items = []
    for path, items in grouped_reads.items():
        latest = items[-1]
        read_items.append(
            {
                "path": path,
                "file_content_hash": latest.result["file_content_hash"],
                "total_lines": latest.result["total_lines"],
                "covered_ranges": [
                    [start, end]
                    for start, end in read_coverage(records, path)
                ],
                "source_call_sequences": [
                    item.call_sequence for item in items
                ],
                "source_outcome_sequences": [
                    item.outcome_sequence for item in items
                ],
            }
        )
    read_items.sort(key=lambda item: item["source_call_sequences"][-1])
    omitted_read_files = max(0, len(read_items) - LEDGER_MAX_READ_FILES)
    read_items = read_items[-LEDGER_MAX_READ_FILES:]

    search_items = [
        {
            "normalized_call_hash": record.normalized_call_hash,
            "query": record.result["query"],
            "path_glob": record.result["path_glob"],
            "source_call_sequence": record.call_sequence,
            "source_outcome_sequence": record.outcome_sequence,
            "result_content_hash": record.result_artifact.content_hash,
            "match_count": record.result["match_count"],
            "truncated": record.result["truncated"],
        }
        for record in searches.values()
    ]
    search_items.sort(key=lambda item: item["source_call_sequence"])
    omitted_searches = max(0, len(search_items) - LEDGER_MAX_SEARCHES)
    search_items = search_items[-LEDGER_MAX_SEARCHES:]

    details: list[dict[str, Any]] = []
    detail_characters = 0
    omitted_details = 0
    for record in reversed(records):
        detail = _detail_for_record(record)
        characters = len(
            json.dumps(detail, ensure_ascii=False, sort_keys=True)
        )
        if (
            len(details) >= LEDGER_MAX_DETAILS
            or detail_characters + characters > LEDGER_DETAIL_CHARACTER_LIMIT
        ):
            omitted_details += 1
            continue
        details.append(detail)
        detail_characters += characters
    details.reverse()

    ledger = {
        "schema_version": investigation_ledger_schema(context_policy_version),
        "policy_version": investigation_policy_version(context_policy_version),
        "source_through_sequence": max(
            (event.sequence for event in events),
            default=0,
        ),
        "mutation_epoch_sequence": epoch,
        "worktree_diff_hash": diff_hash,
        "searches": search_items,
        "reads": read_items,
        "recent_details": details,
        "omitted": {
            "searches": omitted_searches,
            "read_files": omitted_read_files,
            "details": omitted_details,
        },
        "no_progress": _no_progress_state(events, epoch=epoch),
        "tail_policy": tail_policy(
            task,
            checkpoint,
            context_policy_version=context_policy_version,
            events=events,
            budget=budget,
            max_output_tokens=max_output_tokens,
            projection_stage="pre_generation",
        ),
    }
    ledger["content_hash"] = sha256_text(canonical_json(ledger))
    return ledger
