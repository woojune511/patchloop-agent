"""Small source-backed public working notes, separate from reasoning state."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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


_NOTE_FEEDBACK = {
    "unknown_note_id": (
        "This note was not stored: the requested note_id does not exist. Use "
        "note_id=null to create a note with already observed evidence, or choose an "
        "ID from available_note_ids to update an existing note."
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
        "A requested removal was not applied: that ID is not in available_note_ids. "
        "Remove only existing notes, or use an empty remove_note_ids list."
    ),
    "cannot_remove_updated_note": (
        "A requested removal was not applied: this update also revises that note. "
        "Keep the revised note and remove only the redundant notes."
    ),
}


def note_feedback(code: str, **location: int | str) -> dict[str, Any]:
    """Bounded public feedback, never raw rejected text or unobserved references."""

    return {"code": code, "message": _NOTE_FEEDBACK[code], **location}


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
            "Optional concise public observations, current implementation approach, and "
            "unverified behavior, not a reasoning transcript. Cite already observed public "
            "ranges or prior public tool action IDs. Use note_id=null to create a note or "
            "an existing note_id to update it, independent of citation ranges. Consolidate "
            "duplicates by updating one note and removing the others. Only the first "
            "non-null update in a batch is used, before that batch executes. Do not "
            "cite pending/current-batch results. Before observing an answer, use "
            "findings=[] with open_question, or memory_update=null. After observing "
            "it, create a note with note_id=null and use the returned allocated ID "
            "for later updates. Main action success does not mean a note was stored; "
            "check memory_update_result. Null preserves notes and the question."
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
                        "statement": {"type": "string", "minLength": 1, "maxLength": 400},
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
            "open_question": {"type": ["string", "null"], "maxLength": 500},
        },
        "required": ["findings", "remove_note_ids", "open_question"],
        "additionalProperties": False,
    }
