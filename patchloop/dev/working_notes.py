"""Small source-backed public working notes, separate from reasoning state."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from patchloop.dev.verification_concerns import verification_updates_schema


class _NoteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SourceNoteEvidence(_NoteModel):
    kind: Literal["source"]
    path: str = Field(min_length=1, max_length=1_000)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class ToolNoteEvidence(_NoteModel):
    kind: Literal["tool_result"]
    action_id: str = Field(min_length=1, max_length=500)


class PublicFinding(_NoteModel):
    # Defaults permit reading earlier synthetic decisions; the provider wire shape
    # requires explicit create/update intent for every finding.
    note_id: str | None = Field(default=None, pattern=r"^n[1-9][0-9]*$", max_length=30)
    statement: str = Field(min_length=1, max_length=400)
    evidence: list[
        Annotated[SourceNoteEvidence | ToolNoteEvidence, Field(discriminator="kind")]
    ] = Field(min_length=1, max_length=2)


class WorkingNotesUpdate(_NoteModel):
    findings: list[PublicFinding] = Field(max_length=2)
    remove_note_ids: list[
        Annotated[str, Field(pattern=r"^n[1-9][0-9]*$", max_length=30)]
    ] = Field(default_factory=list, max_length=6)
    open_question: str | None = Field(max_length=500)
    # Independently validated annotations must not reject valid source findings
    # or the focus question. Old durable/synthetic updates omit this field.
    verification_updates: Any = Field(default_factory=list)


_NOTE_FEEDBACK = {
    "unknown_note_id": (
        "This note was not stored: the requested note_id does not exist. Use "
        "note_id=null to create a note with already observed evidence, or choose an "
        "ID from working_notes.available_note_ids to update a currently retained note."
    ),
    "unobserved_tool_result": (
        "This note was not stored: its tool result has not been observed. Cite an "
        "already completed public action, not pending or this batch's action. After "
        "receiving this batch's result, cite it in a later update."
    ),
    "unobserved_source_range": (
        "This note was not stored: its complete source range was not observed before "
        "this batch. Cite an already returned range; use open_question for what you "
        "still need to learn, then record the finding after observing the result."
    ),
    "note_source_body_unavailable": (
        "This note was not stored: its observed source body could not be retained. "
        "Use a narrower already observed citation; source bodies for one note must "
        "fit within 24000 characters."
    ),
    "duplicate_note_update": (
        "This entry was not stored: the same existing note is updated twice in one "
        "update. Submit one revision per note ID."
    ),
    "invalid_memory_update_shape": (
        "No note changes were applied: memory_update does not match its schema. "
        "Use up to two findings, remove_note_ids, and a nullable open_question, or "
        "memory_update=null to leave notes unchanged. The main action is independent."
    ),
    "ignored_additional_memory_updates": (
        "Only the first non-null memory_update in this batch was processed. Put "
        "the combined update on one call and use null on the other calls."
    ),
    "removals_skipped_after_invalid_finding": (
        "Requested removals were not applied because a replacement finding was "
        "rejected. Correct the finding before consolidating the existing notes."
    ),
    "unknown_remove_note_id": (
        "A requested removal was not applied: that ID did not exist before this batch. "
        "Consult working_notes.available_note_ids for currently retained IDs, or use "
        "an empty remove_note_ids list."
    ),
    "cannot_remove_updated_note": (
        "A requested removal was not applied: this update also revises that note. "
        "Keep the revised note and remove only the redundant notes."
    ),
}


_SOURCE_RANGE_FEEDBACK = {
    "never_observed": (
        "This note was not stored: part of its cited range has no prior public "
        "source observation. Pending reads are not evidence. Use an already "
        "observed range, or record the finding after a useful read returns."
    ),
    "stale_current_range": (
        "This note was not stored: the missing range was observed previously, "
        "but is not bound as current source evidence. Historical coordinates "
        "do not prove current text. Use the reported current ranges or an "
        "already completed public result; no extra action is required for the note."
    ),
}
_SOURCE_RANGE_DETAIL_LIMIT = 8


def source_note_range_details(
    evidence: SourceNoteEvidence,
    current_spans: list[dict[str, Any]],
    historical_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    """Describe coverage, not source bodies or permission to admit a partial note."""

    def ranges(spans):
        observed = []
        for span in spans:
            start, end = span.get("start_line"), span.get("end_line")
            content = span.get("content")
            if (
                span.get("path") == evidence.path
                and type(start) is int and type(end) is int and 1 <= start <= end
                and isinstance(span.get("file_hash"), str) and span["file_hash"]
                and isinstance(content, str)
                and len(content.replace("\r\n", "\n").split("\n")) == end - start + 1
            ):
                observed.append((start, end))
        merged = []
        for start, end in sorted(observed):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    def missing(start, end, covered):
        gaps = []
        next_line = start
        for left, right in covered:
            if right < next_line:
                continue
            if left > end:
                break
            if left > next_line:
                gaps.append((next_line, left - 1))
            next_line = max(next_line, right + 1)
        if next_line <= end:
            gaps.append((next_line, end))
        return gaps

    current = ranges(current_spans)
    historical = ranges(historical_spans)
    requested_valid = evidence.start_line <= evidence.end_line
    gaps = missing(evidence.start_line, evidence.end_line, current) if requested_valid else []
    previously_observed = bool(gaps) and all(
        not missing(start, end, historical) for start, end in gaps
    )
    # Useful nearby ranges precede unrelated early-file observations when bounded.
    current.sort(key=lambda pair: (
        max(evidence.start_line - pair[1], pair[0] - evidence.end_line, 0), pair,
    ))

    def bounded(values):
        return [{"start_line": start, "end_line": end}
                for start, end in values[:_SOURCE_RANGE_DETAIL_LIMIT]]

    return {
        "reason": "stale_current_range" if previously_observed else "never_observed",
        "range_details": {
            "requested_range": {
                # Do not echo an unknown/private-looking rejected path.
                "path": evidence.path if current or historical else None,
                "start_line": evidence.start_line, "end_line": evidence.end_line,
            },
            "requested_range_valid": requested_valid,
            "current_observed_ranges": bounded(current),
            "missing_ranges": bounded(gaps),
            "current_observed_range_count": len(current),
            "missing_range_count": len(gaps),
            "range_limit": _SOURCE_RANGE_DETAIL_LIMIT,
            "ranges_truncated": {
                "current_observed_ranges": len(current) > _SOURCE_RANGE_DETAIL_LIMIT,
                "missing_ranges": len(gaps) > _SOURCE_RANGE_DETAIL_LIMIT,
            },
        },
    }


def note_feedback(code: str, **location: int | str) -> dict[str, Any]:
    """Bounded public feedback, never raw rejected text or unobserved references."""

    message = _NOTE_FEEDBACK[code]
    if code == "unobserved_source_range":
        message = _SOURCE_RANGE_FEEDBACK.get(location.get("reason"), message)
    return {"code": code, "message": message, **location}


def check_note_result(result: dict[str, Any]) -> dict[str, Any] | None:
    """Label a completed public check, not the model's interpretation of it."""

    if result.get("tool") != "run_check" or result.get("status") != "succeeded":
        return None
    output = result.get("output", {})
    check_id, passed = output.get("check_id"), output.get("passed")
    if not isinstance(check_id, str) or type(passed) is not bool:
        return None
    focus = output.get("public_check_failure")
    exception = focus.get("exception_type") if isinstance(focus, dict) else None
    return {
        "check_id": check_id,
        "passed": passed,
        # Reuse the bounded public failure field; never copy traceback/message text.
        "exception_type": exception[:200] if not passed and isinstance(exception, str) else None,
    }


def memory_update_schema() -> dict[str, Any]:
    """Strict wire shape; semantic validation must never reject the main action."""

    source = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["source"]},
            "path": {"type": "string", "minLength": 1, "maxLength": 1_000},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
        },
        "required": ["kind", "path", "start_line", "end_line"],
        "additionalProperties": False,
    }
    result = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["tool_result"]},
            "action_id": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "required": ["kind", "action_id"],
        "additionalProperties": False,
    }
    return {
        "type": ["object", "null"],
        "description": (
            "Optional reusable behavior rules, implementation assumptions, and unverified "
            "behavior, not a reasoning transcript or a copy of current_public_failure. "
            "Cite already observed public "
            "ranges or prior public tool action IDs. Use note_id=null to create a note or "
            "an existing note_id to refine the same fact, independent of citation ranges. "
            "Keep distinct facts in separate notes. Consolidate "
            "duplicates by updating one note and removing the others. Only the first "
            "non-null update in a batch is used, before that batch executes. Do not "
            "cite pending/current-batch results. Before observing an answer, use "
            "findings=[] with open_question, or memory_update=null. After observing "
            "it, create a note with note_id=null. memory_update_result records the "
            "before-tool-batch update; its note_ids_after_update is historical, not "
            "current availability. Consult working_notes.available_note_ids before "
            "updating a retained note. Main action success does not mean a note was "
            "stored. Null preserves notes and the question."
        ),
        "properties": {
            "findings": {
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "note_id": {
                            "type": ["string", "null"], "pattern": r"^n[1-9][0-9]*$",
                            "maxLength": 30,
                            "description": "null creates; an existing note ID updates that note.",
                        },
                        "statement": {
                            "type": "string", "minLength": 1, "maxLength": 400,
                            "description": (
                                "A useful public mechanism, observation, or explicitly untested "
                                "assumption; not just a repeated function location. Cite the "
                                "behavior-bearing source or observed result."
                            ),
                        },
                        "evidence": {
                            "type": "array", "minItems": 1, "maxItems": 2,
                            "items": {"anyOf": [source, result]},
                        },
                    },
                    "required": ["note_id", "statement", "evidence"],
                    "additionalProperties": False,
                },
            },
            "remove_note_ids": {
                "type": "array", "maxItems": 6,
                "items": {
                    "type": "string", "pattern": r"^n[1-9][0-9]*$", "maxLength": 30,
                },
                "description": "Existing notes to remove; use [] to retain them.",
            },
            "open_question": {
                "type": ["string", "null"], "maxLength": 500,
                "description": (
                    "The remaining uncertainty that could change an edit or experiment. "
                    "Resolve an answered question with null, or replace it with the next one. "
                    "Changing focus does not address retained verification concerns."
                ),
            },
            "verification_updates": verification_updates_schema(),
        },
        "required": ["findings", "remove_note_ids", "open_question", "verification_updates"],
        "additionalProperties": False,
    }
