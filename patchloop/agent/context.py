"""Rebuild model context from durable public state on every turn."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.agent.phases import diff_bound_evidence
from patchloop.contracts import Checkpoint, EventType, Phase, PublicTask, RunEvent
from patchloop.util import sha256_text

RECENT_EVENT_LIMIT = 12
TOOL_RESULT_CHARACTER_LIMIT = 12_000


@dataclass(frozen=True)
class BuiltContext:
    rendered: str
    content_hash: str
    evidence: dict[str, Any]


def _truncate_json_strings(value: Any, limit: int) -> Any:
    if isinstance(value, str):
        if len(value) <= limit:
            return value
        marker = "\n...[field truncated for model context]"
        return value[: max(0, limit - len(marker))] + marker
    if isinstance(value, list):
        return [_truncate_json_strings(item, limit) for item in value]
    if isinstance(value, dict):
        return {
            key: _truncate_json_strings(item, limit)
            for key, item in value.items()
        }
    return value


def _semantic_tool_result(raw: str) -> tuple[Any, bool]:
    parsed = json.loads(raw)
    if len(raw) <= TOOL_RESULT_CHARACTER_LIMIT:
        return parsed, False
    per_string_limit = TOOL_RESULT_CHARACTER_LIMIT
    truncated = parsed
    while per_string_limit > 256:
        truncated = _truncate_json_strings(parsed, per_string_limit)
        if len(json.dumps(truncated, ensure_ascii=False, default=str)) <= (
            TOOL_RESULT_CHARACTER_LIMIT
        ):
            return truncated, True
        per_string_limit //= 2
    truncated = _truncate_json_strings(parsed, 256)
    if len(json.dumps(truncated, ensure_ascii=False, default=str)) <= (
        TOOL_RESULT_CHARACTER_LIMIT
    ):
        return truncated, True
    top_level_keys = (
        [str(key)[:120] for key in list(parsed)[:20]]
        if isinstance(parsed, dict)
        else []
    )
    return {
        "truncated": True,
        "original_characters": len(raw),
        "top_level_keys": top_level_keys,
        "summary": (
            "Tool result exceeded the context limit after semantic field "
            "truncation; inspect targeted evidence instead."
        ),
    }, True


def _context_event(
    event: RunEvent,
    *,
    policy_version: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    payload = dict(event.payload)
    artifact_path = payload.get("artifact_path")
    tool_result_evidence: dict[str, Any] | None = None
    if event.type.value in {"ToolSucceeded", "ToolFailed"} and artifact_path:
        parsed_available = False
        try:
            raw = Path(artifact_path).read_text(encoding="utf-8")
            original_characters = len(raw)
            try:
                if policy_version == "v1":
                    truncated = original_characters > TOOL_RESULT_CHARACTER_LIMIT
                    if truncated:
                        raw = (
                            raw[:TOOL_RESULT_CHARACTER_LIMIT]
                            + "\n...[tool result truncated for model context]"
                        )
                    payload["tool_result"] = json.loads(raw)
                else:
                    payload["tool_result"], truncated = _semantic_tool_result(raw)
                parsed_available = True
            except json.JSONDecodeError:
                payload["tool_result"] = {"unavailable": True}
                truncated = original_characters > TOOL_RESULT_CHARACTER_LIMIT
            included_characters = len(
                json.dumps(
                    payload["tool_result"],
                    ensure_ascii=False,
                    default=str,
                )
            )
        except OSError:
            payload["tool_result"] = {"unavailable": True}
            original_characters = None
            included_characters = None
            truncated = False
        tool_result_evidence = {
            "event_sequence": event.sequence,
            "original_characters": original_characters,
            "included_characters": included_characters,
            "truncated": truncated,
            "available": (
                original_characters is not None
                if policy_version == "v1"
                else parsed_available
            ),
        }
        if policy_version != "v1":
            tool_result_evidence.update(
                {
                    "tool": payload.get("tool"),
                    "worktree_diff_hash": payload.get("worktree_diff_hash"),
                    "artifact_id": payload.get("artifact_id"),
                }
            )
    return (
        {
            "sequence": event.sequence,
            "type": event.type.value,
            "actor": event.actor,
            "payload": payload,
        },
        tool_result_evidence,
    )


def build_context_with_evidence(
    task: PublicTask,
    events: list[RunEvent],
    checkpoint: Checkpoint | None,
    memory_text: str = "",
    *,
    policy_version: str = "phase-evidence-v2",
) -> BuiltContext:
    eligible_events = [
        event
        for event in events
        if event.type.value not in {"ContextBuilt", "ModelCalled"}
    ]
    if policy_version == "v1":
        selected_events = [
            event
            for event in events[-RECENT_EVENT_LIMIT:]
            if event.type.value not in {"ContextBuilt", "ModelCalled"}
        ]
    elif policy_version == "phase-evidence-v2":
        selected_events = eligible_events[-RECENT_EVENT_LIMIT:]
    else:
        raise ValueError(f"unsupported context policy: {policy_version}")
    recent: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    for event in selected_events:
        rendered_event, tool_result_evidence = _context_event(
            event,
            policy_version=policy_version,
        )
        recent.append(rendered_event)
        if tool_result_evidence is not None:
            tool_results.append(tool_result_evidence)

    phase = checkpoint.phase if checkpoint else Phase.INTAKE
    phase_contract = None
    if policy_version == "phase-evidence-v2":
        diff_hash = checkpoint.worktree_diff_hash if checkpoint else sha256_text("")
        readiness = diff_bound_evidence(
            task,
            events,
            diff_hash,
            presented_tool_results=tool_results,
            phase=phase,
        )
        phase_contract = {
            "schema_version": "phase-contract-v1",
            "current_phase": phase.value,
            "submission_ready": readiness.submission_ready,
            "missing_evidence": list(readiness.missing_evidence),
            "allowed_next_actions": list(readiness.allowed_next_actions),
            "required_sequence": [
                "apply_patch",
                "run_check",
                "get_diff",
                "finish_task",
            ],
            "completed_checks": list(readiness.completed_checks),
            "pending_checks": list(readiness.pending_checks),
            "current_diff_hash": readiness.worktree_diff_hash,
            "mutation_event_sequence": readiness.mutation_event_sequence,
            "mutation_present": readiness.mutation_present,
            "review_event_sequence": readiness.review_event_sequence,
        }
    latest_model_sequence = max(
        (
            event.sequence
            for event in events
            if event.type == EventType.MODEL_CALLED
        ),
        default=0,
    )
    repeat_events = [
        {
            "sequence": event.sequence,
            "tool": event.payload.get("tool"),
            "occurrences": event.payload.get("occurrences"),
            "enforcement": event.payload.get("enforcement"),
        }
        for event in eligible_events
        if event.type == EventType.LOOP_DETECTED
        and event.sequence > latest_model_sequence
    ]
    payload = {
        "public_task": task.model_dump(mode="json"),
        "phase": phase.value,
        "checkpoint": checkpoint.model_dump(mode="json") if checkpoint else None,
        "recent_events": recent,
        "selected_memory": memory_text or None,
        "rules": {
            "private_evaluator_data_unavailable": True,
            "done_is_submission_not_success": True,
            "registered_checks_only": True,
        },
    }
    if policy_version != "v1":
        payload = {
            "public_task": payload["public_task"],
            "phase": payload["phase"],
            "checkpoint": payload["checkpoint"],
            "phase_contract": phase_contract,
            "recent_events": payload["recent_events"],
            "execution_signals": {"repeated_calls": repeat_events},
            "selected_memory": payload["selected_memory"],
            "rules": payload["rules"],
        }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    component_characters = {
        key: len(json.dumps(value, ensure_ascii=False, default=str))
        for key, value in payload.items()
    }
    evidence = {
        "schema_version": (
            "context-build-evidence-v1"
            if policy_version == "v1"
            else "context-build-evidence-v2"
        ),
        "policy": {
            "recent_event_limit": RECENT_EVENT_LIMIT,
            "tool_result_character_limit": TOOL_RESULT_CHARACTER_LIMIT,
        },
        "events": {
            "eligible_count": len(eligible_events),
            "included_count": len(selected_events),
            "omitted_count": len(eligible_events) - len(selected_events),
            "included_sequences": [event.sequence for event in selected_events],
        },
        "tool_results": tool_results,
        "memory": {
            "provided": bool(memory_text),
            "characters": len(memory_text),
        },
        "component_characters": component_characters,
        "rendered_characters": len(rendered),
        "rendered_bytes": len(rendered.encode("utf-8")),
    }
    if policy_version != "v1":
        evidence["policy"]["version"] = policy_version
    return BuiltContext(
        rendered=rendered,
        content_hash=sha256_text(rendered),
        evidence=evidence,
    )


def build_context(
    task: PublicTask,
    events: list[RunEvent],
    checkpoint: Checkpoint | None,
    memory_text: str = "",
    *,
    policy_version: str = "phase-evidence-v2",
) -> tuple[str, str]:
    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        memory_text,
        policy_version=policy_version,
    )
    return built.rendered, built.content_hash
