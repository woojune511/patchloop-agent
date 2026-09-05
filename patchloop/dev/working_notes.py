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
            "non-null update in a batch is used; null preserves notes and the question."
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
