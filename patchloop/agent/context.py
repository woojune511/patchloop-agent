"""Rebuild model context from durable public state on every turn."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from patchloop.agent.investigation import (
    EVIDENCE_SATURATION_POLICY_VERSION,
    READ_SEARCH_POLICY_SCHEMA,
    build_investigation_ledger,
    evidence_saturation_state,
    investigation_ledger_schema,
)
from patchloop.agent.phases import diff_bound_evidence
from patchloop.agent.review import validate_public_review_contract
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import (
    Artifact,
    Budget,
    Checkpoint,
    EventType,
    Phase,
    PublicReviewContract,
    PublicTask,
    RunEvent,
)
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import (
    canonical_json,
    safe_relative_path,
    sha256_json,
    sha256_text,
)

RECENT_EVENT_LIMIT = 12
TOOL_RESULT_CHARACTER_LIMIT = 12_000
REVIEW_EVIDENCE_SCHEMA = "review-evidence-v1"
REVIEW_EVIDENCE_V2_SCHEMA = "review-evidence-v2"
INVESTIGATION_CONTEXT_POLICIES = {
    "phase-evidence-v4",
    "phase-evidence-v5",
    "phase-evidence-v6",
    "phase-evidence-v7",
    "phase-evidence-v8",
    "phase-evidence-v9",
    "phase-evidence-v10",
}
RETRY_CONTEXT_POLICIES = {
    "phase-evidence-v3",
    *INVESTIGATION_CONTEXT_POLICIES,
}
PERSISTENT_RETRY_CONTEXT_POLICIES = {
    "phase-evidence-v7",
    "phase-evidence-v8",
    "phase-evidence-v9",
    "phase-evidence-v10",
}


@dataclass(frozen=True)
class BuiltContext:
    rendered: str
    content_hash: str
    evidence: dict[str, Any]


def _build_probe_ledger(
    events: list[RunEvent],
    artifact_store: ArtifactStore | None,
) -> dict[str, Any]:
    """Rehydrate bounded agent-authored probe source without repository files."""

    if artifact_store is None:
        raise RecoveryError("phase-evidence-v6 requires the artifact store")
    outcomes = {
        event.correlation_id: event
        for event in events
        if event.correlation_id is not None
        and event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.payload.get("tool") == "run_probe"
    }
    items: list[dict[str, Any]] = []
    total_source_bytes = 0
    for call in reversed(events):
        if (
            call.type != EventType.TOOL_CALLED
            or call.payload.get("tool") != "run_probe"
            or call.correlation_id is None
        ):
            continue
        try:
            descriptor = Artifact.model_validate(
                call.payload["input_artifact"]
            )
            raw = artifact_store.read_bytes(descriptor)
            document = json.loads(raw.decode("utf-8", errors="strict"))
            arguments = document["input"]
            source = arguments["source"]
            probe_id = arguments["probe_id"]
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RecoveryError(
                "v6 probe call lacks valid public input evidence"
            ) from exc
        if (
            document.get("tool") != "run_probe"
            or not isinstance(arguments, dict)
            or not isinstance(source, str)
            or not isinstance(probe_id, str)
            or call.payload.get("artifact_id") != descriptor.artifact_id
            or call.payload.get("artifact_path") != descriptor.path
        ):
            raise RecoveryError(
                "v6 probe call conflicts with its input artifact"
            )
        source_bytes = len(source.encode("utf-8"))
        if items and total_source_bytes + source_bytes > 12_000:
            continue
        if source_bytes > 12_000:
            raise RecoveryError("v6 probe source exceeds its trace limit")
        outcome = outcomes.get(call.correlation_id)
        items.append(
            {
                "action_id": call.correlation_id,
                "call_sequence": call.sequence,
                "outcome_sequence": (
                    outcome.sequence if outcome is not None else None
                ),
                "source": source,
                "source_hash": sha256_text(source),
                "probe_id": probe_id,
                "worktree_diff_hash": (
                    outcome.payload.get("worktree_diff_hash")
                    if outcome is not None
                    else call.payload.get("worktree_diff_hash")
                ),
                "passed": (
                    outcome.payload.get("passed")
                    if outcome is not None
                    else None
                ),
                "timed_out": (
                    outcome.payload.get("timed_out")
                    if outcome is not None
                    else None
                ),
            }
        )
        total_source_bytes += source_bytes
        if len(items) >= 3:
            break
    items.reverse()
    body = {
        "schema_version": "probe-ledger-v1",
        "source_through_sequence": events[-1].sequence if events else 0,
        "entries": items,
        "source_bytes": total_source_bytes,
        "authoritative": False,
    }
    return {
        **body,
        "content_hash": sha256_text(canonical_json(body)),
    }


def _patch_source_snapshot(
    call: RunEvent,
    *,
    patch_artifact: Artifact,
    input_hash: str,
    artifact_store: ArtifactStore,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        descriptor = Artifact.model_validate(
            call.payload.get("source_snapshot_artifact")
        )
    except ValueError as exc:
        raise RecoveryError(
            "v7 rejected patch call lacks a valid source snapshot artifact"
        ) from exc
    try:
        raw = artifact_store.read_bytes(descriptor)
        snapshot = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "v7 patch source snapshot is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(snapshot, dict):
        raise RecoveryError("v7 patch source snapshot must be an object")
    declared_content_hash = snapshot.get("content_hash")
    content_body = {
        key: value
        for key, value in snapshot.items()
        if key != "content_hash"
    }
    entries = snapshot.get("entries")
    unavailable = snapshot.get("unavailable")
    if (
        snapshot.get("schema_version") != "patch-source-snapshot-v1"
        or call.payload.get("source_snapshot_schema_version")
        != "patch-source-snapshot-v1"
        or snapshot.get("candidate_content_hash")
        != patch_artifact.content_hash
        or snapshot.get("input_hash") != input_hash
        or snapshot.get("worktree_diff_hash")
        != call.payload.get("worktree_diff_hash")
        or declared_content_hash != sha256_text(canonical_json(content_body))
        or not isinstance(entries, list)
        or len(entries) > 8
        or not isinstance(unavailable, list)
    ):
        raise RecoveryError("v7 patch source snapshot binding is invalid")
    for entry in entries:
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("path"), str)
            or not isinstance(entry.get("content"), str)
            or entry.get("content_hash")
            != sha256_text(entry["content"])
        ):
            raise RecoveryError("v7 patch source snapshot entry is invalid")
        try:
            safe_relative_path(
                entry["path"],
                field_name="patch source snapshot path",
            )
        except ContractError as exc:
            raise RecoveryError(
                "v7 patch source snapshot path is invalid"
            ) from exc
        for field in (
            "section",
            "hunk",
            "requested_start_line",
            "requested_end_line",
            "total_lines",
        ):
            if type(entry.get(field)) is not int:
                raise RecoveryError(
                    "v7 patch source snapshot line metadata is invalid"
                )
        for field in ("actual_start_line", "actual_end_line"):
            if entry.get(field) is not None and type(entry.get(field)) is not int:
                raise RecoveryError(
                    "v7 patch source snapshot returned range is invalid"
                )
    return snapshot, {
        "artifact_id": descriptor.artifact_id,
        "content_hash": descriptor.content_hash,
        "size_bytes": descriptor.size_bytes,
    }


def _rejected_mutation_retry(
    events: list[RunEvent],
    *,
    artifact_store: ArtifactStore | None,
    policy_version: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Rehydrate one rejected model patch under the selected versioned policy."""

    persistent = policy_version in PERSISTENT_RETRY_CONTEXT_POLICIES
    latest_model_sequence = max(
        (
            event.sequence
            for event in events
            if event.type == EventType.MODEL_CALLED
        ),
        default=0,
    )
    apply_outcomes = [
        event
        for event in events
        if event.type in {EventType.TOOL_SUCCEEDED, EventType.TOOL_FAILED}
        and event.payload.get("tool") == "apply_patch"
    ]
    if persistent:
        latest_outcome = (
            max(apply_outcomes, key=lambda event: event.sequence)
            if apply_outcomes
            else None
        )
        failures = [
            latest_outcome
        ] if (
            latest_outcome is not None
            and latest_outcome.type == EventType.TOOL_FAILED
            and latest_outcome.actor == "tool-gateway"
            and latest_outcome.payload.get("status") == "rejected"
        ) else []
    else:
        failures = [
            event
            for event in apply_outcomes
            if event.sequence > latest_model_sequence
            and event.type == EventType.TOOL_FAILED
            and event.actor == "tool-gateway"
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
        if (
            (persistent or event.sequence > latest_model_sequence)
            and event.sequence < failure.sequence
        )
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
        "schema_version": (
            "rejected-mutation-retry-v2"
            if persistent
            else "rejected-mutation-retry-v1"
        ),
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
    if persistent:
        snapshot, snapshot_evidence = _patch_source_snapshot(
            call,
            patch_artifact=patch_artifact,
            input_hash=input_hash,
            artifact_store=artifact_store,
        )
        rendered["persistence"] = {
            "state": "pending",
            "resolution": "next_apply_patch_outcome",
        }
        rendered["source_snapshot"] = snapshot
        evidence["persistence"] = {
            "state": "pending",
            "resolution": "next_apply_patch_outcome",
        }
        evidence["source_snapshot"] = snapshot_evidence
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


def _validate_v10_review_result_document(
    event: RunEvent,
    *,
    document: Any,
    rendered_result: Any,
    rendered_truncated: bool,
) -> bool:
    """Bind V10 review evidence metadata to the exact CAS result document.

    V9 intentionally keeps its historical event-only interpretation.  V10 is
    stricter: metadata may select a result only when it agrees with the result
    bytes that were written by the tool gateway.  The return value reports an
    authoritative tool-side truncation that makes the result non-citable.
    """

    tool = event.payload.get("tool")
    if (
        event.type != EventType.TOOL_SUCCEEDED
        or event.actor != "tool-gateway"
        or event.payload.get("status") != "succeeded"
        or tool not in {"run_check", "read_file"}
        or not isinstance(document, dict)
        or not isinstance(rendered_result, dict)
    ):
        raise RecoveryError("v10 review evidence has an invalid tool identity")
    event_diff_hash = event.payload.get("worktree_diff_hash")
    document_diff_hash = document.get("worktree_diff_hash")
    if (
        not isinstance(event_diff_hash, str)
        or document_diff_hash != event_diff_hash
        or rendered_result.get("worktree_diff_hash") != document_diff_hash
    ):
        raise RecoveryError(
            "v10 review evidence conflicts with its current-diff result"
        )

    if tool == "run_check":
        if (
            not isinstance(document.get("check_id"), str)
            or type(document.get("passed")) is not bool
            or type(document.get("timed_out")) is not bool
            or type(document.get("truncated")) is not bool
            or event.payload.get("check_id") != document.get("check_id")
            or event.payload.get("passed") is not document.get("passed")
            or event.payload.get("timed_out") is not document.get("timed_out")
            or (
                not rendered_truncated
                and any(
                    rendered_result.get(key) != document.get(key)
                    for key in (
                        "check_id",
                        "passed",
                        "timed_out",
                        "truncated",
                        "worktree_diff_hash",
                    )
                )
            )
        ):
            raise RecoveryError(
                "v10 run_check event conflicts with its result document"
            )
        if document["passed"] is True and document["timed_out"] is True:
            raise RecoveryError(
                "v10 run_check result has inconsistent completion semantics"
            )
        return bool(document["timed_out"] or document["truncated"])

    if (
        not isinstance(document.get("path"), str)
        or not isinstance(document.get("content"), str)
        or (
            "truncated" in document
            and type(document.get("truncated")) is not bool
        )
        or (
            not rendered_truncated
            and (
                rendered_result.get("path") != document.get("path")
                or rendered_result.get("content") != document.get("content")
                or rendered_result.get("worktree_diff_hash")
                != document.get("worktree_diff_hash")
            )
        )
    ):
        raise RecoveryError(
            "v10 read_file evidence conflicts with its result document"
        )
    return document.get("truncated") is True


def _context_event(
    event: RunEvent,
    *,
    policy_version: str,
    artifact_store: ArtifactStore | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    payload = dict(event.payload)
    artifact_path = payload.get("artifact_path")
    tool_result_evidence: dict[str, Any] | None = None
    result_event_types = {"ToolSucceeded", "ToolFailed"}
    if policy_version in INVESTIGATION_CONTEXT_POLICIES:
        result_event_types.add("ToolReplayed")
    if event.type.value in result_event_types and artifact_path:
        parsed_available = False
        try:
            v4_inspection_outcome = (
                event.payload.get("tool") in {"read_file", "search_files"}
                and event.type
                in {
                    EventType.TOOL_SUCCEEDED,
                    EventType.TOOL_FAILED,
                    EventType.TOOL_REPLAYED,
                }
            )
            v4_semantic_replay = (
                event.type == EventType.TOOL_REPLAYED
                and event.payload.get("semantic_replay") is True
            )
            v9_review_anchor_outcome = bool(
                policy_version == "phase-evidence-v9"
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool")
                in {"run_check", "get_diff"}
            )
            v10_review_anchor_outcome = bool(
                policy_version == "phase-evidence-v10"
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool")
                in {"run_check", "get_diff"}
            )
            v10_coverage_outcome = bool(
                policy_version == "phase-evidence-v10"
                and event.type == EventType.TOOL_SUCCEEDED
                and event.payload.get("tool") in {"run_check", "read_file"}
            )
            if policy_version in INVESTIGATION_CONTEXT_POLICIES and (
                v4_inspection_outcome
                or v4_semantic_replay
                or v9_review_anchor_outcome
                or v10_review_anchor_outcome
            ):
                if artifact_store is None:
                    raise RecoveryError(
                        f"{policy_version} requires the artifact store"
                    )
                try:
                    result_artifact = Artifact.model_validate(
                        event.payload.get("result_artifact")
                    )
                except ValueError as exc:
                    raise RecoveryError(
                        "v9 review anchor lacks a result artifact"
                        if v9_review_anchor_outcome
                        else (
                            "v10 review anchor lacks a result artifact"
                            if v10_review_anchor_outcome
                            else (
                                "investigation outcome lacks a result artifact"
                            )
                        )
                    ) from exc
                if (
                    event.payload.get("artifact_id")
                    != result_artifact.artifact_id
                    or event.payload.get("artifact_path")
                    != result_artifact.path
                ):
                    raise RecoveryError(
                        "v9 review anchor conflicts with its artifact"
                        if v9_review_anchor_outcome
                        else (
                            "v10 review anchor conflicts with its artifact"
                            if v10_review_anchor_outcome
                            else (
                                "v4 inspection outcome conflicts with its artifact"
                            )
                        )
                    )
                try:
                    raw = artifact_store.read_bytes(result_artifact).decode(
                        "utf-8",
                        errors="strict",
                    )
                except UnicodeDecodeError as exc:
                    raise RecoveryError(
                        "v9 review anchor is not valid UTF-8"
                        if v9_review_anchor_outcome
                        else (
                            "v10 review anchor is not valid UTF-8"
                            if v10_review_anchor_outcome
                            else (
                                "v4 inspection outcome is not valid UTF-8"
                            )
                        )
                    ) from exc
            else:
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
                if v10_coverage_outcome:
                    document = json.loads(raw)
                    truncated = bool(
                        truncated
                        or _validate_v10_review_result_document(
                            event,
                            document=document,
                            rendered_result=payload["tool_result"],
                            rendered_truncated=truncated,
                        )
                    )
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


def _pinned_review_evidence(
    task: PublicTask,
    events: list[RunEvent],
    *,
    phase: Phase,
    worktree_diff_hash: str,
    artifact_store: ArtifactStore | None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Render bounded, current-diff citations outside the recent-event window."""

    readiness = diff_bound_evidence(
        task,
        events,
        worktree_diff_hash,
        phase=phase,
        structured_review_required=True,
        probe_available=bool(task.probe_profiles),
    )
    pinning_active = bool(
        phase == Phase.REVIEW
        and readiness.mutation_present
        and not readiness.pending_checks
        and readiness.review_event_sequence is not None
    )
    requested_sequences = (
        [
            *readiness.current_diff_check_event_sequences,
            readiness.review_event_sequence,
        ]
        if pinning_active
        else []
    )
    events_by_sequence = {event.sequence: event for event in events}
    pinned_results: list[dict[str, Any]] = []
    pinned_tool_results: list[dict[str, Any]] = []
    complete_sequences: list[int] = []
    incomplete_sequences: list[int] = []
    for sequence in requested_sequences:
        event = events_by_sequence.get(sequence)
        if event is None:
            raise RecoveryError(
                "v9 review evidence references a missing durable event"
            )
        rendered_event, result_evidence = _context_event(
            event,
            policy_version="phase-evidence-v9",
            artifact_store=artifact_store,
        )
        if result_evidence is None:
            raise RecoveryError(
                "v9 review evidence is not a durable tool result"
            )
        pinned_results.append(rendered_event)
        pinned_tool_results.append(result_evidence)
        if (
            result_evidence.get("available") is True
            and result_evidence.get("truncated") is False
        ):
            complete_sequences.append(sequence)
        else:
            incomplete_sequences.append(sequence)

    passing_check_sequences = [
        sequence
        for sequence in readiness.current_diff_check_event_sequences
        if sequence in complete_sequences
    ]
    source_get_diff_sequence = (
        readiness.review_event_sequence
        if readiness.review_event_sequence in complete_sequences
        else None
    )
    citable_sequences = [
        *passing_check_sequences,
        *(
            [source_get_diff_sequence]
            if source_get_diff_sequence is not None
            else []
        ),
    ]
    visible = {
        "schema_version": REVIEW_EVIDENCE_SCHEMA,
        "pinning_active": pinning_active,
        "worktree_diff_hash": worktree_diff_hash,
        "mutation_event_sequence": readiness.mutation_event_sequence,
        "passing_check_event_sequences": passing_check_sequences,
        "source_get_diff_sequence": source_get_diff_sequence,
        "citable_event_sequences": citable_sequences,
        "incomplete_event_sequences": incomplete_sequences,
        "pinned_results": pinned_results,
        "citation_rule": (
            "review_task may cite only citable_event_sequences; "
            "investigation_ledger source_call_sequence values are not "
            "review citations"
        ),
    }
    evidence = {
        key: value
        for key, value in visible.items()
        if key not in {"pinned_results", "citation_rule"}
    }
    evidence["pinned_tool_results"] = pinned_tool_results
    return visible, evidence, pinned_tool_results


def _pinned_review_evidence_v10(
    task: PublicTask,
    events: list[RunEvent],
    *,
    phase: Phase,
    worktree_diff_hash: str,
    artifact_store: ArtifactStore | None,
    public_review_contract: PublicReviewContract,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Pin exact public coverage evidence for the current mutation and diff."""

    readiness = diff_bound_evidence(
        task,
        events,
        worktree_diff_hash,
        phase=phase,
        structured_review_required=True,
        coverage_review_required=True,
        probe_available=bool(task.probe_profiles),
    )
    pinning_active = bool(
        phase == Phase.REVIEW
        and readiness.mutation_present
        and not readiness.pending_checks
        and readiness.review_event_sequence is not None
    )
    events_by_sequence = {event.sequence: event for event in events}
    rendered_by_sequence: dict[
        int,
        tuple[dict[str, Any], dict[str, Any]],
    ] = {}

    def render_tool_result(
        event: RunEvent,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        cached = rendered_by_sequence.get(event.sequence)
        if cached is not None:
            return cached
        rendered_event, result_evidence = _context_event(
            event,
            policy_version="phase-evidence-v10",
            artifact_store=artifact_store,
        )
        if result_evidence is None:
            raise RecoveryError(
                "v10 review evidence is not a durable tool result"
            )
        rendered_by_sequence[event.sequence] = (
            rendered_event,
            result_evidence,
        )
        return rendered_event, result_evidence

    coverage_target_event_sequences: dict[str, list[int]] = {
        target.coverage_target_id: []
        for requirement in public_review_contract.requirements
        for target in requirement.coverage_targets
    }
    if pinning_active:
        mutation_sequence = readiness.mutation_event_sequence
        assert mutation_sequence is not None
        passing_events = [
            events_by_sequence[sequence]
            for sequence in readiness.current_diff_check_event_sequences
        ]
        inspection_candidates = [
            event
            for event in reversed(events)
            if event.sequence > mutation_sequence
            and event.type == EventType.TOOL_SUCCEEDED
            and event.payload.get("tool") == "read_file"
            and event.payload.get("worktree_diff_hash")
            == worktree_diff_hash
        ]
        for requirement in public_review_contract.requirements:
            for target in requirement.coverage_targets:
                if target.evidence_kind == "passing_validation":
                    target_sequences = sorted(
                        {
                            event.sequence
                            for event in passing_events
                            if event.payload.get("check_id")
                            in target.check_ids
                        }
                    )
                    coverage_target_event_sequences[
                        target.coverage_target_id
                    ] = target_sequences
                    continue

                assert target.path is not None
                assert target.anchor is not None
                for event in inspection_candidates:
                    rendered_event, result_evidence = render_tool_result(event)
                    if (
                        result_evidence.get("available") is not True
                        or result_evidence.get("truncated") is not False
                    ):
                        continue
                    tool_result = rendered_event["payload"].get("tool_result")
                    if not isinstance(tool_result, dict):
                        continue
                    content = tool_result.get("content")
                    if (
                        tool_result.get("path") == target.path
                        and isinstance(content, str)
                        and target.anchor in content
                    ):
                        coverage_target_event_sequences[
                            target.coverage_target_id
                        ] = [event.sequence]
                        break

    target_sequences_in_order: list[int] = []
    seen_sequences: set[int] = set()
    for sequences in coverage_target_event_sequences.values():
        for sequence in sequences:
            if sequence not in seen_sequences:
                target_sequences_in_order.append(sequence)
                seen_sequences.add(sequence)
    requested_sequences = list(target_sequences_in_order)
    if pinning_active:
        for sequence in readiness.current_diff_check_event_sequences:
            if sequence not in seen_sequences:
                requested_sequences.append(sequence)
                seen_sequences.add(sequence)
        assert readiness.review_event_sequence is not None
        if readiness.review_event_sequence not in seen_sequences:
            requested_sequences.append(readiness.review_event_sequence)

    pinned_results: list[dict[str, Any]] = []
    pinned_tool_results: list[dict[str, Any]] = []
    complete_sequences: list[int] = []
    incomplete_sequences: list[int] = []
    for sequence in requested_sequences:
        event = events_by_sequence.get(sequence)
        if event is None:
            raise RecoveryError(
                "v10 review evidence references a missing durable event"
            )
        rendered_event, result_evidence = render_tool_result(event)
        pinned_results.append(rendered_event)
        pinned_tool_results.append(result_evidence)
        if (
            result_evidence.get("available") is True
            and result_evidence.get("truncated") is False
        ):
            complete_sequences.append(sequence)
        else:
            incomplete_sequences.append(sequence)

    complete_sequence_set = set(complete_sequences)
    coverage_target_event_sequences = {
        target_id: [
            sequence
            for sequence in sequences
            if sequence in complete_sequence_set
        ]
        for target_id, sequences in coverage_target_event_sequences.items()
    }
    passing_check_sequences = [
        sequence
        for sequence in readiness.current_diff_check_event_sequences
        if sequence in complete_sequence_set
    ]
    source_get_diff_sequence = (
        readiness.review_event_sequence
        if readiness.review_event_sequence in complete_sequence_set
        else None
    )
    citable_sequences: list[int] = []
    seen_citable: set[int] = set()
    for sequences in coverage_target_event_sequences.values():
        for sequence in sequences:
            if sequence not in seen_citable:
                citable_sequences.append(sequence)
                seen_citable.add(sequence)
    for sequence in passing_check_sequences:
        if sequence not in seen_citable:
            citable_sequences.append(sequence)
            seen_citable.add(sequence)
    if (
        source_get_diff_sequence is not None
        and source_get_diff_sequence not in seen_citable
    ):
        citable_sequences.append(source_get_diff_sequence)

    visible = {
        "schema_version": REVIEW_EVIDENCE_V2_SCHEMA,
        "pinning_active": pinning_active,
        "worktree_diff_hash": worktree_diff_hash,
        "mutation_event_sequence": readiness.mutation_event_sequence,
        "coverage_target_event_sequences": (
            coverage_target_event_sequences
        ),
        "passing_check_event_sequences": passing_check_sequences,
        "source_get_diff_sequence": source_get_diff_sequence,
        "citable_event_sequences": citable_sequences,
        "incomplete_event_sequences": incomplete_sequences,
        "pinned_results": pinned_results,
        "citation_rule": (
            "review_task may cite only citable_event_sequences and must "
            "resolve every public coverage target; investigation_ledger "
            "source_call_sequence values are not review citations"
        ),
    }
    evidence = {
        key: value
        for key, value in visible.items()
        if key not in {"pinned_results", "citation_rule"}
    }
    evidence["pinned_tool_results"] = pinned_tool_results
    return visible, evidence, pinned_tool_results


def build_context_with_evidence(
    task: PublicTask,
    events: list[RunEvent],
    checkpoint: Checkpoint | None,
    memory_text: str = "",
    *,
    policy_version: str = "phase-evidence-v3",
    artifact_store: ArtifactStore | None = None,
    budget: Budget | None = None,
    max_output_tokens: int | None = None,
    public_review_contract: PublicReviewContract | None = None,
) -> BuiltContext:
    self_validation_policy = policy_version in {
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
    }
    investigation_compat_policy = (
        "phase-evidence-v6"
        if policy_version
        in {
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
        }
        else policy_version
    )
    if policy_version == "phase-evidence-v10":
        if (
            public_review_contract is None
            or public_review_contract.schema_version
            != "public-review-contract-v2"
        ):
            raise RecoveryError(
                "phase-evidence-v10 requires a public-review-contract-v2"
            )
        try:
            validate_public_review_contract(
                public_review_contract,
                task=task,
                public_spec_hash=sha256_json(task.model_dump(mode="json")),
            )
        except ContractError as exc:
            raise RecoveryError(
                "phase-evidence-v10 public review contract is not public-bound"
            ) from exc
    elif policy_version in {
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
    }:
        if public_review_contract is None:
            raise RecoveryError(
                "phase-evidence-v7/v8/v9 requires a public review contract"
            )
        try:
            validate_public_review_contract(
                public_review_contract,
                task=task,
                public_spec_hash=sha256_json(task.model_dump(mode="json")),
            )
        except ContractError as exc:
            raise RecoveryError(
                "phase-evidence-v7/v8/v9 public review contract is not public-bound"
            ) from exc
    elif public_review_contract is not None:
        raise RecoveryError(
            "public review contract is valid only for phase-evidence-v7/v8/v9"
        )
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
    elif policy_version in {
        "phase-evidence-v2",
        "phase-evidence-v3",
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
    }:
        selected_events = eligible_events[-RECENT_EVENT_LIMIT:]
    else:
        raise ValueError(f"unsupported context policy: {policy_version}")
    recent: list[dict[str, Any]] = []
    recent_tool_results: list[dict[str, Any]] = []
    for event in selected_events:
        rendered_event, tool_result_evidence = _context_event(
            event,
            policy_version=policy_version,
            artifact_store=artifact_store,
        )
        recent.append(rendered_event)
        if tool_result_evidence is not None:
            recent_tool_results.append(tool_result_evidence)

    phase = checkpoint.phase if checkpoint else Phase.INTAKE
    probe_available = bool(task.probe_profiles)
    diff_hash = checkpoint.worktree_diff_hash if checkpoint else sha256_text("")
    review_evidence = None
    review_evidence_build = None
    pinned_tool_results: list[dict[str, Any]] = []
    if policy_version == "phase-evidence-v9":
        (
            review_evidence,
            review_evidence_build,
            pinned_tool_results,
        ) = _pinned_review_evidence(
            task,
            events,
            phase=phase,
            worktree_diff_hash=diff_hash,
            artifact_store=artifact_store,
        )
        pinned_sequences = {
            item["sequence"]
            for item in review_evidence["pinned_results"]
        }
        # V9 makes the review envelope the single model-visible authority for
        # current-diff citations. When an anchor is still inside the ordinary
        # recent-event window, omit that duplicate rendering here while
        # retaining its independently tracked tool-result evidence below.
        recent = [
            item for item in recent if item["sequence"] not in pinned_sequences
        ]
        recent_tool_results = [
            item
            for item in recent_tool_results
            if item["event_sequence"] not in pinned_sequences
        ]
        visible_selected_events = [
            event
            for event in selected_events
            if event.sequence not in pinned_sequences
        ]
    elif policy_version == "phase-evidence-v10":
        assert public_review_contract is not None
        (
            review_evidence,
            review_evidence_build,
            pinned_tool_results,
        ) = _pinned_review_evidence_v10(
            task,
            events,
            phase=phase,
            worktree_diff_hash=diff_hash,
            artifact_store=artifact_store,
            public_review_contract=public_review_contract,
        )
        pinned_sequences = {
            item["sequence"]
            for item in review_evidence["pinned_results"]
        }
        recent = [
            item for item in recent if item["sequence"] not in pinned_sequences
        ]
        recent_tool_results = [
            item
            for item in recent_tool_results
            if item["event_sequence"] not in pinned_sequences
        ]
        visible_selected_events = [
            event
            for event in selected_events
            if event.sequence not in pinned_sequences
        ]
    else:
        visible_selected_events = selected_events
    tool_results_by_sequence = {
        item["event_sequence"]: item
        for item in [*recent_tool_results, *pinned_tool_results]
    }
    tool_results = [
        tool_results_by_sequence[sequence]
        for sequence in sorted(tool_results_by_sequence)
    ]
    phase_contract = None
    if policy_version in {
        "phase-evidence-v2",
        "phase-evidence-v3",
        "phase-evidence-v4",
        "phase-evidence-v5",
        "phase-evidence-v6",
        "phase-evidence-v7",
        "phase-evidence-v8",
        "phase-evidence-v9",
        "phase-evidence-v10",
    }:
        readiness = diff_bound_evidence(
            task,
            events,
            diff_hash,
            presented_tool_results=tool_results,
            phase=phase,
            structured_review_required=self_validation_policy,
            coverage_review_required=(
                policy_version == "phase-evidence-v10"
            ),
            probe_available=probe_available,
        )
        phase_contract = {
            "schema_version": (
                "phase-contract-v4"
                if policy_version == "phase-evidence-v10"
                else (
                    "phase-contract-v3"
                    if policy_version
                    in {"phase-evidence-v8", "phase-evidence-v9"}
                    else (
                        "phase-contract-v2"
                        if self_validation_policy
                        else "phase-contract-v1"
                    )
                )
            ),
            "current_phase": phase.value,
            "submission_ready": readiness.submission_ready,
            "missing_evidence": list(readiness.missing_evidence),
            "allowed_next_actions": list(readiness.allowed_next_actions),
            "required_sequence": (
                [
                    "apply_patch",
                    "run_check",
                    "get_diff",
                    "review_task",
                    "finish_task",
                ]
                if self_validation_policy
                else [
                    "apply_patch",
                    "run_check",
                    "get_diff",
                    "finish_task",
                ]
            ),
            "completed_checks": list(readiness.completed_checks),
            "pending_checks": list(readiness.pending_checks),
            "current_diff_hash": readiness.worktree_diff_hash,
            "mutation_event_sequence": readiness.mutation_event_sequence,
            "mutation_present": readiness.mutation_present,
            "review_event_sequence": readiness.review_event_sequence,
        }
        if self_validation_policy:
            phase_contract.update(
                {
                    "optional_actions": (
                        ["run_probe"] if probe_available else []
                    ),
                    "registered_probe_profile_ids": [
                        profile.id for profile in task.probe_profiles
                    ],
                    "task_review_event_sequence": (
                        readiness.task_review_event_sequence
                    ),
                }
            )
        if policy_version == "phase-evidence-v10":
            phase_contract.update(
                {
                    "task_review_coverage_complete": (
                        readiness.task_review_coverage_complete
                    ),
                    "unresolved_coverage_target_ids": list(
                        readiness.unresolved_coverage_target_ids
                    ),
                }
            )
    latest_model_sequence = max(
        (
            event.sequence
            for event in events
            if event.type == EventType.MODEL_CALLED
        ),
        default=0,
    )
    repeat_events = []
    for event in eligible_events:
        if not (
            event.type == EventType.LOOP_DETECTED
            and event.sequence > latest_model_sequence
        ):
            continue
        item = {
            "sequence": event.sequence,
            "tool": event.payload.get("tool"),
            "occurrences": event.payload.get("occurrences"),
            "enforcement": event.payload.get("enforcement"),
        }
        if policy_version in INVESTIGATION_CONTEXT_POLICIES:
            item.update(
                {
                    "schema_version": event.payload.get("schema_version"),
                    "reason_code": event.payload.get("reason_code"),
                    "no_progress_streak": event.payload.get(
                        "no_progress_streak"
                    ),
                    "strategy_change_required": event.payload.get(
                        "strategy_change_required"
                    ),
                    "source_call_sequences": event.payload.get(
                        "source_call_sequences"
                    ),
                }
            )
        repeat_events.append(item)
    admission_blocks = [
        {
            "sequence": event.sequence,
            "tool": event.payload.get("tool"),
            "reason_codes": event.payload.get("reason_codes"),
            "error_code": event.payload.get("error_code"),
            "error_message": event.payload.get("error_message"),
        }
        for event in eligible_events
        if event.type == EventType.TOOL_ADMISSION_BLOCKED
        and event.sequence > latest_model_sequence
    ]
    rejected_mutation_retry = None
    rejected_mutation_retry_evidence = None
    if policy_version in RETRY_CONTEXT_POLICIES:
        (
            rejected_mutation_retry,
            rejected_mutation_retry_evidence,
        ) = _rejected_mutation_retry(
            events,
            artifact_store=artifact_store,
            policy_version=policy_version,
        )
    checkpoint_payload = (
        checkpoint.model_dump(mode="json") if checkpoint else None
    )
    if (
        policy_version in INVESTIGATION_CONTEXT_POLICIES
        and checkpoint_payload is not None
    ):
        # The in-memory checkpoint and its SQLite round-trip must render
        # byte-identically for request-by-request qualification.
        checkpoint_payload = json.loads(
            canonical_json(checkpoint_payload)
        )
    payload = {
        "public_task": task.model_dump(mode="json"),
        "phase": phase.value,
        "checkpoint": checkpoint_payload,
        "recent_events": recent,
        "selected_memory": memory_text or None,
        "rules": {
            "private_evaluator_data_unavailable": True,
            "done_is_submission_not_success": True,
            "registered_checks_only": True,
            **(
                {
                    "registered_checks_are_only_authoritative_checks": True,
                    "registered_probe_profiles_only": True,
                    "agent_probe_is_non_authoritative": True,
                    "structured_review_is_self_attestation": True,
                }
                if self_validation_policy
                else {}
            ),
        },
    }
    if public_review_contract is not None:
        payload["public_review_contract"] = (
            public_review_contract.model_dump(mode="json")
        )
    if policy_version != "v1":
        payload = {
            "public_task": payload["public_task"],
            **(
                {
                    "public_review_contract": payload[
                        "public_review_contract"
                    ]
                }
                if "public_review_contract" in payload
                else {}
            ),
            "phase": payload["phase"],
            "checkpoint": payload["checkpoint"],
            "phase_contract": phase_contract,
            **(
                {"review_evidence": review_evidence}
                if policy_version
                in {"phase-evidence-v9", "phase-evidence-v10"}
                else {}
            ),
            "recent_events": payload["recent_events"],
            "execution_signals": {"repeated_calls": repeat_events},
            "selected_memory": payload["selected_memory"],
            "rules": payload["rules"],
        }
        if policy_version in RETRY_CONTEXT_POLICIES:
            payload["rejected_mutation_retry"] = rejected_mutation_retry
        if policy_version in INVESTIGATION_CONTEXT_POLICIES:
            payload["execution_signals"][
                "tool_admission_blocks"
            ] = admission_blocks
            if artifact_store is None:
                raise RecoveryError(
                    f"{policy_version} requires the artifact store"
                )
            investigation_ledger = build_investigation_ledger(
                task,
                events,
                checkpoint,
                artifact_store,
                context_policy_version=investigation_compat_policy,
                budget=budget,
                max_output_tokens=max_output_tokens,
            )
            payload["investigation_ledger"] = investigation_ledger
            if self_validation_policy:
                payload["probe_ledger"] = _build_probe_ledger(
                    events,
                    artifact_store,
                )
            if phase_contract is not None:
                tail = investigation_ledger["tail_policy"]
                if not tail["exploration_admitted"]:
                    phase_contract["allowed_next_actions"] = [
                        action
                        for action in phase_contract["allowed_next_actions"]
                        if action
                        not in {"read_file", "search_files", "run_probe"}
                    ]
                if policy_version in {
                    "phase-evidence-v8",
                    "phase-evidence-v9",
                    "phase-evidence-v10",
                }:
                    saturation = evidence_saturation_state(events)
                    reason_codes = list(tail["block_reasons"])
                    if saturation.saturated:
                        reason_codes.append("evidence_saturated")
                        phase_contract["allowed_next_actions"] = [
                            action
                            for action in phase_contract["allowed_next_actions"]
                            if action not in {"read_file", "search_files"}
                        ]
                    phase_contract["read_search_policy"] = {
                        "schema_version": READ_SEARCH_POLICY_SCHEMA,
                        "policy_version": (
                            EVIDENCE_SATURATION_POLICY_VERSION
                        ),
                        "admitted": not reason_codes,
                        "reason_codes": reason_codes,
                        "semantic_replay_count": (
                            saturation.semantic_replay_count
                        ),
                        "semantic_replay_threshold": (
                            saturation.semantic_replay_threshold
                        ),
                        "mutation_epoch_sequence": (
                            saturation.mutation_epoch_sequence
                        ),
                    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    component_characters = {
        key: len(json.dumps(value, ensure_ascii=False, default=str))
        for key, value in payload.items()
    }
    evidence = {
        "schema_version": (
            "context-build-evidence-v10"
            if policy_version == "phase-evidence-v10"
            else (
                "context-build-evidence-v1"
                if policy_version == "v1"
                else (
                    "context-build-evidence-v2"
                    if policy_version == "phase-evidence-v2"
                    else (
                        "context-build-evidence-v3"
                        if policy_version == "phase-evidence-v3"
                        else (
                            "context-build-evidence-v4"
                            if policy_version == "phase-evidence-v4"
                            else (
                                "context-build-evidence-v5"
                                if policy_version == "phase-evidence-v5"
                                else (
                                    "context-build-evidence-v9"
                                    if policy_version == "phase-evidence-v9"
                                    else (
                                        "context-build-evidence-v8"
                                        if policy_version == "phase-evidence-v8"
                                        else (
                                            "context-build-evidence-v7"
                                            if policy_version
                                            == "phase-evidence-v7"
                                            else "context-build-evidence-v6"
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        ),
        "policy": {
            "recent_event_limit": RECENT_EVENT_LIMIT,
            "tool_result_character_limit": TOOL_RESULT_CHARACTER_LIMIT,
        },
        "events": {
            "eligible_count": len(eligible_events),
            "included_count": len(visible_selected_events),
            "omitted_count": (
                len(eligible_events) - len(visible_selected_events)
            ),
            "included_sequences": [
                event.sequence for event in visible_selected_events
            ],
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
    if public_review_contract is not None:
        evidence["public_review_contract_content_hash"] = (
            public_review_contract.content_hash
        )
    if policy_version in RETRY_CONTEXT_POLICIES:
        evidence["rejected_mutation_retry"] = (
            rejected_mutation_retry_evidence
        )
    if policy_version in {
        "phase-evidence-v9",
        "phase-evidence-v10",
    }:
        assert review_evidence_build is not None
        evidence["review_evidence"] = review_evidence_build
    if policy_version in INVESTIGATION_CONTEXT_POLICIES:
        ledger = payload["investigation_ledger"]
        evidence["investigation_ledger"] = {
            "schema_version": investigation_ledger_schema(
                investigation_compat_policy
            ),
            "content_hash": ledger["content_hash"],
            "source_through_sequence": ledger[
                "source_through_sequence"
            ],
            "mutation_epoch_sequence": ledger[
                "mutation_epoch_sequence"
            ],
            "worktree_diff_hash": ledger["worktree_diff_hash"],
            "search_count": len(ledger["searches"]),
            "read_file_count": len(ledger["reads"]),
            "detail_count": len(ledger["recent_details"]),
            "semantic_replay_count": ledger["no_progress"][
                "total_semantic_replays"
            ],
            "no_progress_streak": ledger["no_progress"]["streak"],
            "strategy_change_required": ledger["no_progress"][
                "strategy_change_required"
            ],
            "exploration_admitted": ledger["tail_policy"][
                "exploration_admitted"
            ],
        }
        if policy_version in {
            "phase-evidence-v5",
            "phase-evidence-v6",
            "phase-evidence-v7",
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
        }:
            tail = ledger["tail_policy"]
            projection = tail["token_projection"]
            evidence["investigation_ledger"].update(
                {
                    "tail_block_reasons": tail["block_reasons"],
                    "tail_projection_stage": tail["projection_stage"],
                    "tail_remaining_tokens": tail["remaining_budget"]["tokens"],
                    "tail_observation_count": projection[
                        "observed_model_call_count"
                    ],
                    "tail_max_observed_input_tokens": projection[
                        "max_observed_input_tokens"
                    ],
                    "tail_max_positive_growth": projection[
                        "max_positive_consecutive_growth"
                    ],
                    "tail_projected_next_input_tokens": projection[
                        "projected_next_input_tokens"
                    ],
                    "tail_projected_model_turns": projection[
                        "projected_model_turns"
                    ],
                    "tail_reserved_tokens": projection["reserved_tokens"],
                    "tail_max_output_tokens": projection["max_output_tokens"],
                }
            )
        if self_validation_policy:
            probe_ledger = payload["probe_ledger"]
            evidence["probe_ledger"] = {
                "schema_version": probe_ledger["schema_version"],
                "content_hash": probe_ledger["content_hash"],
                "source_through_sequence": probe_ledger[
                    "source_through_sequence"
                ],
                "entry_count": len(probe_ledger["entries"]),
                "source_bytes": probe_ledger["source_bytes"],
                "authoritative": False,
            }
        if policy_version in {
            "phase-evidence-v8",
            "phase-evidence-v9",
            "phase-evidence-v10",
        }:
            evidence["read_search_policy"] = phase_contract[
                "read_search_policy"
            ]
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
    budget: Budget | None = None,
    max_output_tokens: int | None = None,
    public_review_contract: PublicReviewContract | None = None,
) -> tuple[str, str]:
    built = build_context_with_evidence(
        task,
        events,
        checkpoint,
        memory_text,
        policy_version=policy_version,
        artifact_store=artifact_store,
        budget=budget,
        max_output_tokens=max_output_tokens,
        public_review_contract=public_review_contract,
    )
    return built.rendered, built.content_hash
