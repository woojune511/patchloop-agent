"""Optional public-task quotations: source identity only, never semantic coverage."""

from __future__ import annotations

import copy
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
            "Optional exact excerpt from public_task.issue.description supporting the "
            "expected_behavior; copy public_task.task_id, or use null. The gateway binds "
            "the public task content hash. A match validates source identity only, not "
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
    if not request.excerpt.strip() or request.excerpt not in public_task.issue.description:
        return _diagnostic("invalid", "excerpt_mismatch")
    return {
        "status": "matched",
        "reference": {
            "task_id": public_task.task_id,
            "task_version": public_task.task_version,
            "public_task_hash": sha256_json(public_task.model_dump(mode="json")),
            "field": "issue.description",
            "excerpt": request.excerpt,
        },
        "diagnostics": [],
        "validation_scope": "public_source_identity_only",
    }


def project(receipt: dict[str, Any], public_task: PublicTask) -> dict[str, Any]:
    """Keep an admission-time identity; never silently rebind a saved quotation."""

    if receipt["status"] == "matched":
        reference = receipt["reference"]
        if (reference["task_id"] != public_task.task_id
                or reference["task_version"] != public_task.task_version
                or reference["public_task_hash"] != sha256_json(public_task.model_dump(mode="json"))
                or reference["field"] != "issue.description"
                or reference["excerpt"] not in public_task.issue.description):
            return _diagnostic("stale", "public_task_identity_changed")
    return copy.deepcopy(receipt)
