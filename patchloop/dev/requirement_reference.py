"""Optional public-task quotations: source identity only, never semantic coverage."""

from __future__ import annotations

import copy
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from patchloop.contracts import PublicTask
from patchloop.util import sha256_json

MAX_EXCERPT_CHARS = 600


class RequirementReference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    task_id: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_CHARS)


def reference_schema() -> dict[str, Any]:
    return {
        "type": ["object", "null"],
        "description": (
            "Optional excerpt from public_task.issue.description supporting expected_behavior; "
            "copy public_task.task_id, or use null. Only whitespace differences are allowed; "
            "the excerpt must identify one unique source span. The gateway retains the original "
            "text and span with the public task hash. A match validates source identity only, not "
            "the interpretation or check coverage. This annotation never gates the action."
        ),
        "properties": {
            "task_id": {"type": "string", "minLength": 1, "maxLength": 200},
            "excerpt": {"type": "string", "minLength": 1, "maxLength": MAX_EXCERPT_CHARS},
        },
        "required": ["task_id", "excerpt"],
        "additionalProperties": False,
    }


def _diagnostic(status: str, code: str) -> dict[str, Any]:
    # Do not echo a malformed or mismatched model-authored quotation as source evidence.
    return {"status": status, "diagnostics": [code],
            "validation_scope": "public_source_identity_only"}


def bind(value: Any, public_task: PublicTask) -> dict[str, Any]:
    """Bind once at action admission using only the already supplied public task."""

    if value is None:
        return _diagnostic("omitted", "missing_reference")
    try:
        request = RequirementReference.model_validate(value)
    except ValidationError:
        return _diagnostic("invalid", "invalid_reference_shape")
    if request.task_id != public_task.task_id:
        return _diagnostic("invalid", "task_id_mismatch")
    words = request.excerpt.split()
    if not words:
        return _diagnostic("invalid", "excerpt_mismatch")
    description = public_task.issue.description
    pattern = r"\s+".join(re.escape(word) for word in words)
    # Lookahead includes overlapping occurrences; an exact spelling must not hide
    # a second occurrence with different whitespace. Stop at the first ambiguity.
    matches = re.finditer(f"(?=({pattern}))", description)
    match = next(matches, None)
    if match is None:
        return _diagnostic("invalid", "excerpt_mismatch")
    if next(matches, None) is not None:
        return _diagnostic("invalid", "ambiguous_excerpt")
    start, end = match.span(1)
    exact_start = description.find(request.excerpt)
    if exact_start >= 0:
        # Keep submitted edge whitespace when it already matches the original.
        start, end = exact_start, exact_start + len(request.excerpt)
    original = description[start:end]
    if len(original) > MAX_EXCERPT_CHARS:
        return _diagnostic("invalid", "source_excerpt_too_long")
    return {
        "status": "matched",
        "reference": {
            "task_id": public_task.task_id,
            "task_version": public_task.task_version,
            "public_task_hash": sha256_json(public_task.model_dump(mode="json")),
            "field": "issue.description",
            "excerpt": original,
            "source_span": {"start": start, "end": end},
            "match_mode": "exact" if original == request.excerpt else "whitespace",
        },
        "diagnostics": [],
        "validation_scope": "public_source_identity_only",
    }


def _source_span_matches(reference: dict[str, Any], description: str) -> bool:
    if "source_span" not in reference:
        # Legacy admission receipts did not bind offsets. Do not rematch them or
        # reinterpret completed exact/invalid receipts under the new rule.
        return reference["excerpt"] in description
    span = reference["source_span"]
    if not isinstance(span, dict):
        return False
    start, end = span.get("start"), span.get("end")
    return (type(start) is int and type(end) is int
            and 0 <= start < end <= len(description)
            and description[start:end] == reference["excerpt"])


def project(receipt: dict[str, Any], public_task: PublicTask) -> dict[str, Any]:
    """Keep an admission-time identity; never silently rebind a saved quotation."""

    if receipt["status"] == "matched":
        reference = receipt["reference"]
        if (reference["task_id"] != public_task.task_id
                or reference["task_version"] != public_task.task_version
                or reference["public_task_hash"] != sha256_json(public_task.model_dump(mode="json"))
                or reference["field"] != "issue.description"
                or not _source_span_matches(reference, public_task.issue.description)):
            return _diagnostic("stale", "public_task_identity_changed")
    return copy.deepcopy(receipt)
