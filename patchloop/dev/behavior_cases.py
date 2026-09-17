"""Optional public case contrasts: model-authored expectations, never coverage proof."""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from patchloop.contracts import PublicTask
from patchloop.util import sha256_json

MAX_TEXT_CHARS = 300


class CaseExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    setup: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    expected: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


class BehaviorCases(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    change: CaseExpectation
    preserve: CaseExpectation | None
    scope_basis: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


def cases_schema() -> dict[str, Any]:
    case = {
        "type": "object",
        "properties": {
            "setup": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT_CHARS,
                      "description": "Concrete public input or setup, including the trigger."},
            "expected": {"type": "string", "minLength": 1, "maxLength": MAX_TEXT_CHARS,
                         "description": "Observable expected output or effect for that setup."},
        },
        "required": ["setup", "expected"],
        "additionalProperties": False,
    }
    return {
        "type": ["object", "null"],
        "description": (
            "Optional changed/preserved case contrast from the complete public task, including "
            "its limits and exceptions. Separate a setup requiring change from a nearby setup "
            "that must keep its behavior even if it shares the proposed code trigger. "
            "Use preserve=null when no preservation boundary is known; explain that in "
            "scope_basis instead of inventing a case. Expectations are unverified, and "
            "recording them never gates an edit or submission."
        ),
        "properties": {
            "change": copy.deepcopy(case),
            "preserve": {**copy.deepcopy(case), "type": ["object", "null"]},
            "scope_basis": {
                "type": "string", "minLength": 1, "maxLength": MAX_TEXT_CHARS,
                "description": (
                    "Public requirement separating the two setups; distinguish that requirement "
                    "from the proposed implementation condition. State unknown or not applicable "
                    "when the public task does not establish a boundary."
                ),
            },
        },
        "required": ["change", "preserve", "scope_basis"],
        "additionalProperties": False,
    }


def _diagnostic(status: str, code: str) -> dict[str, Any]:
    return {"status": status, "diagnostics": [code],
            "interpretation_status": "model_authored_unverified"}


def bind(value: Any, public_task: PublicTask) -> dict[str, Any]:
    if value is None:
        return _diagnostic("omitted", "missing_behavior_cases")
    try:
        cases = BehaviorCases.model_validate(value)
    except ValidationError:
        return _diagnostic("invalid", "invalid_behavior_cases")
    return {
        "status": "recorded", "cases": cases.model_dump(mode="json"),
        "public_task_hash": sha256_json(public_task.model_dump(mode="json")),
        "interpretation_status": "model_authored_unverified",
        "coverage_status": "not_assessed", "diagnostics": [],
    }


def project(receipt: dict[str, Any], public_task: PublicTask) -> dict[str, Any]:
    if (receipt["status"] == "recorded"
            and receipt["public_task_hash"] != sha256_json(public_task.model_dump(mode="json"))):
        return _diagnostic("stale", "public_task_identity_changed")
    return copy.deepcopy(receipt)
