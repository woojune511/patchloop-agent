"""Small model-authored public observations, separate from reasoning state."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from patchloop.util import canonical_json, sha256_json


def finding_identity(evidence: list[dict[str, Any]]) -> str:
    """Updated statements replace the same cited evidence, independent of ref order."""

    return sha256_json({"evidence": sorted(evidence, key=canonical_json)})


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
    statement: str = Field(min_length=1, max_length=400)
    evidence: list[
        Annotated[SourceNoteEvidence | ToolNoteEvidence, Field(discriminator="kind")]
    ] = Field(min_length=1, max_length=2)


class WorkingNotesUpdate(_NoteModel):
    findings: list[PublicFinding] = Field(max_length=2)
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
            "Optional small public source observations learned from preceding results, "
            "not reasoning or a plan. Only the first non-null update in a batch is used. "
            "Cite already observed public ranges or prior public tool action IDs."
        ),
        "properties": {
            "findings": {
                "type": "array",
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string", "minLength": 1, "maxLength": 400},
                        "evidence": {
                            "type": "array", "minItems": 1, "maxItems": 2,
                            "items": {"anyOf": [source, result]},
                        },
                    },
                    "required": ["statement", "evidence"],
                    "additionalProperties": False,
                },
            },
            "open_question": {"type": ["string", "null"], "maxLength": 500},
        },
        "required": ["findings", "open_question"],
        "additionalProperties": False,
    }
