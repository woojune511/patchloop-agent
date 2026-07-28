"""Rebuild model context from durable public state on every turn."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.contracts import Checkpoint, PublicTask, RunEvent
from patchloop.util import sha256_text

RECENT_EVENT_LIMIT = 12
TOOL_RESULT_CHARACTER_LIMIT = 12_000


@dataclass(frozen=True)
class BuiltContext:
    rendered: str
    content_hash: str
    evidence: dict[str, Any]


def _context_event(event: RunEvent) -> tuple[dict[str, Any], dict[str, Any] | None]:
    payload = dict(event.payload)
    artifact_path = payload.get("artifact_path")
    tool_result_evidence: dict[str, Any] | None = None
    if event.type.value in {"ToolSucceeded", "ToolFailed"} and artifact_path:
        try:
            raw = Path(artifact_path).read_text(encoding="utf-8")
            original_characters = len(raw)
            truncated = original_characters > TOOL_RESULT_CHARACTER_LIMIT
            if truncated:
                raw = (
                    raw[:TOOL_RESULT_CHARACTER_LIMIT]
                    + "\n...[tool result truncated for model context]"
                )
            try:
                payload["tool_result"] = json.loads(raw)
            except json.JSONDecodeError:
                payload["tool_result"] = {"unavailable": True}
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
            "available": original_characters is not None,
        }
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
) -> BuiltContext:
    eligible_events = [
        event
        for event in events
        if event.type.value not in {"ContextBuilt", "ModelCalled"}
    ]
    selected_events = [
        event
        for event in events[-RECENT_EVENT_LIMIT:]
        if event.type.value not in {"ContextBuilt", "ModelCalled"}
    ]
    recent: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    for event in selected_events:
        rendered_event, tool_result_evidence = _context_event(event)
        recent.append(rendered_event)
        if tool_result_evidence is not None:
            tool_results.append(tool_result_evidence)

    payload = {
        "public_task": task.model_dump(mode="json"),
        "phase": checkpoint.phase.value if checkpoint else "INTAKE",
        "checkpoint": checkpoint.model_dump(mode="json") if checkpoint else None,
        "recent_events": recent,
        "selected_memory": memory_text or None,
        "rules": {
            "private_evaluator_data_unavailable": True,
            "done_is_submission_not_success": True,
            "registered_checks_only": True,
        },
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    component_characters = {
        key: len(json.dumps(value, ensure_ascii=False, default=str))
        for key, value in payload.items()
    }
    evidence = {
        "schema_version": "context-build-evidence-v1",
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
) -> tuple[str, str]:
    built = build_context_with_evidence(task, events, checkpoint, memory_text)
    return built.rendered, built.content_hash
