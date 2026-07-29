"""Rebuild model context from durable public state on every turn."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.agent.phases import diff_bound_evidence
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Checkpoint,
    EventType,
    Phase,
    PublicTask,
    RunEvent,
)
from patchloop.errors import RecoveryError
from patchloop.util import canonical_json, sha256_text

RECENT_EVENT_LIMIT = 12
TOOL_RESULT_CHARACTER_LIMIT = 12_000


@dataclass(frozen=True)
class BuiltContext:
    rendered: str
    content_hash: str
    evidence: dict[str, Any]


def _rejected_mutation_retry(
    events: list[RunEvent],
    *,
    artifact_store: ArtifactStore | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Rehydrate the latest rejected model patch for exactly one next turn."""

    latest_model_sequence = max(
        (
            event.sequence
            for event in events
            if event.type == EventType.MODEL_CALLED
        ),
        default=0,
    )
    failures = [
        event
        for event in events
        if event.sequence > latest_model_sequence
        and event.type == EventType.TOOL_FAILED
        and event.actor == "tool-gateway"
        and event.payload.get("tool") == "apply_patch"
        and event.payload.get("status") == "rejected"
    ]
    if not failures:
        return None, {"included": False, "truncated": False}
    if artifact_store is None:
        raise RecoveryError(
            "phase-evidence-v3 requires the artifact store to rehydrate "
            "a rejected patch"
        )

    failure = max(failures, key=lambda event: event.sequence)
    action_id = failure.correlation_id
    if not isinstance(action_id, str) or not action_id:
        raise RecoveryError("rejected patch outcome lacks an action identity")
    calls = [
        event
        for event in events
        if latest_model_sequence < event.sequence < failure.sequence
        and event.type == EventType.TOOL_CALLED
        and event.actor == "agent"
        and event.correlation_id == action_id
        and event.payload.get("tool") == "apply_patch"
    ]
    if len(calls) != 1:
        raise RecoveryError(
            "rejected patch outcome does not have one correlated model call"
        )
    call = calls[0]

    try:
        patch_artifact = Artifact.model_validate(
            call.payload.get("patch_artifact")
        )
    except ValueError as exc:
        raise RecoveryError(
            "rejected patch call lacks a valid candidate artifact"
        ) from exc
    if (
        call.payload.get("artifact_id") != patch_artifact.artifact_id
        or call.payload.get("artifact_path") != patch_artifact.path
    ):
        raise RecoveryError(
            "rejected patch call conflicts with its candidate artifact"
        )
    patch_bytes = artifact_store.read_bytes(patch_artifact)
    try:
        patch = patch_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RecoveryError("rejected patch candidate is not valid UTF-8") from exc
    input_hash = call.payload.get("input_hash")
    expected_input_hash = sha256_text(
        canonical_json({"tool": "apply_patch", "input": {"patch": patch}})
    )
    if input_hash != expected_input_hash:
        raise RecoveryError(
            "rejected patch candidate does not match its tool input hash"
        )

    try:
        result_artifact = Artifact.model_validate(
            failure.payload.get("result_artifact")
        )
    except ValueError as exc:
        raise RecoveryError(
            "rejected patch outcome lacks a valid result artifact"
        ) from exc
    if (
        failure.payload.get("artifact_id") != result_artifact.artifact_id
        or failure.payload.get("artifact_path") != result_artifact.path
    ):
        raise RecoveryError(
            "rejected patch outcome conflicts with its result artifact"
        )
    result_bytes = artifact_store.read_bytes(result_artifact)
    try:
        result_payload = json.loads(result_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "rejected patch result artifact is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(result_payload, dict):
        raise RecoveryError("rejected patch result artifact must be an object")
    rejection = {
        "status": result_payload.get("status"),
        "error_code": result_payload.get("error_code"),
        "error_message": result_payload.get("error_message"),
        "error_details": result_payload.get("error_details"),
    }
    event_message = failure.payload.get("error_message")
    if (
        result_payload.get("tool") != "apply_patch"
        or rejection["status"] != "rejected"
        or not isinstance(rejection["error_code"], str)
        or not isinstance(rejection["error_message"], str)
        or not isinstance(rejection["error_details"], dict)
        or failure.payload.get("status") != rejection["status"]
        or failure.payload.get("error_code") != rejection["error_code"]
        or failure.payload.get("error_details") != rejection["error_details"]
        or not isinstance(event_message, str)
        or not rejection["error_message"].startswith(event_message)
    ):
        raise RecoveryError(
            "rejected patch event conflicts with its structured result"
        )

    rendered = {
        "schema_version": "rejected-mutation-retry-v1",
        "tool": "apply_patch",
        "action_id": action_id,
        "source_call_sequence": call.sequence,
        "source_failure_sequence": failure.sequence,
        "candidate": {
            "patch": patch,
            "content_hash": patch_artifact.content_hash,
            "size_bytes": patch_artifact.size_bytes,
            "input_hash": input_hash,
        },
        "rejection": rejection,
    }
    evidence = {
        "included": True,
        "truncated": False,
        "action_id": action_id,
        "source_call_sequence": call.sequence,
        "source_failure_sequence": failure.sequence,
        "candidate": {
            "artifact_id": patch_artifact.artifact_id,
            "content_hash": patch_artifact.content_hash,
            "size_bytes": patch_artifact.size_bytes,
            "input_hash": input_hash,
        },
        "rejection": {
            "artifact_id": result_artifact.artifact_id,
            "content_hash": result_artifact.content_hash,
            "size_bytes": result_artifact.size_bytes,
        },
    }
    return rendered, evidence


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
    policy_version: str = "phase-evidence-v3",
    artifact_store: ArtifactStore | None = None,
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
    elif policy_version in {"phase-evidence-v2", "phase-evidence-v3"}:
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
    if policy_version in {"phase-evidence-v2", "phase-evidence-v3"}:
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
    rejected_mutation_retry = None
    rejected_mutation_retry_evidence = None
    if policy_version == "phase-evidence-v3":
        (
            rejected_mutation_retry,
            rejected_mutation_retry_evidence,
        ) = _rejected_mutation_retry(
            events,
            artifact_store=artifact_store,
        )
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
        if policy_version == "phase-evidence-v3":
            payload["rejected_mutation_retry"] = rejected_mutation_retry
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    component_characters = {
        key: len(json.dumps(value, ensure_ascii=False, default=str))
        for key, value in payload.items()
    }
    evidence = {
        "schema_version": (
            "context-build-evidence-v1"
            if policy_version == "v1"
            else (
                "context-build-evidence-v2"
                if policy_version == "phase-evidence-v2"
                else "context-build-evidence-v3"
            )
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
    if policy_version == "phase-evidence-v3":
        evidence["rejected_mutation_retry"] = (
            rejected_mutation_retry_evidence
        )
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
    policy_version: str = "phase-evidence-v3",
    artifact_store: ArtifactStore | None = None,
) -> tuple[str, str]:
    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        memory_text,
        policy_version=policy_version,
        artifact_store=artifact_store,
    )
    return built.rendered, built.content_hash
