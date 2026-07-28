"""Rebuild model context from durable public state on every turn."""

from __future__ import annotations

import json
from pathlib import Path

from patchloop.contracts import Checkpoint, PublicTask, RunEvent
from patchloop.util import sha256_text


def _context_event(event: RunEvent) -> dict:
    payload = dict(event.payload)
    artifact_path = payload.get("artifact_path")
    if event.type.value in {"ToolSucceeded", "ToolFailed"} and artifact_path:
        try:
            raw = Path(artifact_path).read_text(encoding="utf-8")
            if len(raw) > 12_000:
                raw = raw[:12_000] + "\n...[tool result truncated for model context]"
            payload["tool_result"] = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            payload["tool_result"] = {"unavailable": True}
    return {
        "sequence": event.sequence,
        "type": event.type.value,
        "actor": event.actor,
        "payload": payload,
    }


def build_context(
    task: PublicTask,
    events: list[RunEvent],
    checkpoint: Checkpoint | None,
    memory_text: str = "",
) -> tuple[str, str]:
    recent = [
        _context_event(event)
        for event in events[-12:]
        if event.type.value not in {"ContextBuilt", "ModelCalled"}
    ]
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
    return rendered, sha256_text(rendered)
