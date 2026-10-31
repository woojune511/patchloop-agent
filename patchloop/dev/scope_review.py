"""Bounded plan annotation linking scope claims to existing public observations."""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

MAX_TEXT_CHARS = 500
MAX_SOURCE_ACTIONS = 4
MAX_CASES = 4
MAX_ACTION_ID_CHARS = 500
MAX_SOURCE_RECEIPTS = 8
MAX_SOURCE_RANGES = 8
_EXECUTION_TOOLS = frozenset({"run_check", "run_tests", "run_probe"})
_SOURCE_TOOLS = frozenset({"read_file", "search_files"})
_OBSERVATION_FIELDS = (
    "passed", "status", "test_status", "exit_code", "timed_out", "truncated",
    "deadline_exhausted", "cleanup_failed", "execution_uncertain", "check_id", "suite_id",
)


class _Case(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    input: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    expected_observation: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    disposition: Literal["executed", "source_inferred", "untested"]
    evidence_action_id: str | None = Field(min_length=1, max_length=MAX_ACTION_ID_CHARS)
    interpretation: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)

    @field_validator("input", "expected_observation", "interpretation", "evidence_action_id")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("scope review text must be nonblank")
        return value


class _Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    scope: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    source_action_ids: list[str] = Field(max_length=MAX_SOURCE_ACTIONS)
    cases: list[_Case] = Field(min_length=1, max_length=MAX_CASES)

    @field_validator("scope")
    @classmethod
    def nonblank_scope(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scope must be nonblank")
        return value

    @field_validator("source_action_ids")
    @classmethod
    def source_ids(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > MAX_ACTION_ID_CHARS for value in values):
            raise ValueError("source action IDs must be bounded and nonblank")
        return values


def schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1, "maxLength": MAX_TEXT_CHARS}
    case = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "input": {**text, "description": "Public caller and input construction or group."},
            "expected_observation": {**text, "description": "Required observable outcome."},
            "disposition": {"type": "string", "enum": [
                "executed", "source_inferred", "untested",
            ]},
            "evidence_action_id": {
                "type": ["string", "null"], "minLength": 1,
                "maxLength": MAX_ACTION_ID_CHARS,
                "description": "Executed: completed current-diff check/probe ID; otherwise null.",
            },
            "interpretation": {**text, "description": "What evidence supports or leaves open."},
        },
        "required": ["input", "expected_observation", "disposition", "evidence_action_id",
                     "interpretation"],
    }
    return {
        "anyOf": [
            {"type": "object", "additionalProperties": False,
             "properties": {
                 "scope": {**text, "description": "Affected public scope and its limits."},
                 "source_action_ids": {
                     "type": "array", "maxItems": MAX_SOURCE_ACTIONS,
                     "items": {"type": "string", "minLength": 1,
                               "maxLength": MAX_ACTION_ID_CHARS},
                     "description": (
                         "Completed public read/search IDs; required for source inference."
                     ),
                 },
                 "cases": {"type": "array", "minItems": 1, "maxItems": MAX_CASES,
                           "items": case},
             }, "required": ["scope", "source_action_ids", "cases"]},
            {"type": "null"},
        ],
        "description": (
            "Replace this plan's bounded scope/evidence review, or null to preserve it. "
            "Executed means observed execution, not verified coverage; retain failures and gaps. "
            "The scope and evidence interpretation are model-authored, not certified complete."
        ),
    }


def contract() -> dict[str, Any]:
    return {
        "policy": "plan-scope-public-result-binding-v1",
        "max_text_chars": MAX_TEXT_CHARS, "max_source_actions": MAX_SOURCE_ACTIONS,
        "max_cases": MAX_CASES, "max_action_id_chars": MAX_ACTION_ID_CHARS,
        "execution": "completed-current-diff-public-result-not-semantic-coverage",
        "source": "completed-public-read-search-prior-diff-retained",
        "storage": "existing-working-plan-event-nonblocking-null-preserves",
        "source_catalog": {
            "policy": "selected-scope-path-file-hash-range-intersection-v1",
            "max_receipts": MAX_SOURCE_RECEIPTS, "max_ranges_per_receipt": MAX_SOURCE_RANGES,
            "authority": "reference-metadata-only-no-source-selection-or-permission",
        },
        "schema": schema(),
    }


def _span_range(span: Any, default_scope: str = "repository") -> tuple | None:
    if not isinstance(span, dict):
        return None
    identity = (span.get("source_scope", default_scope), span.get("path"), span.get("file_hash"))
    start, end = span.get("start_line"), span.get("end_line")
    if (not all(isinstance(value, str) and value for value in identity)
            or type(start) is not int or type(end) is not int or not 1 <= start <= end):
        return None
    return identity, start, end


def source_catalog(
    events: list[dict[str, Any]], selected_spans: list[dict[str, Any]],
) -> dict[str, Any]:
    """Identify receipts for already selected spans, without reading/selecting source."""
    selected: dict[tuple, list[tuple[int, int]]] = {}
    for span in selected_spans:
        if parsed := _span_range(span):
            identity, start, end = parsed
            selected.setdefault(identity, []).append((start, end))
    items, seen = [], set()
    for event in reversed(events):
        if event.get("event_type") != "action_finished":
            continue
        result = event.get("payload", {}).get("result")
        if (not isinstance(result, dict) or result.get("status") != "succeeded"
                or result.get("tool") not in _SOURCE_TOOLS
                or not isinstance(result.get("action_id"), str) or not result["action_id"]
                or result["action_id"] in seen
                or not isinstance(result.get("input_hash"), str) or not result["input_hash"]
                or not isinstance(result.get("output"), dict)):
            continue
        output = result["output"]
        intersections: dict[tuple, list[tuple[int, int]]] = {}
        for field in ("spans", "dependency_spans"):
            for span in output.get(field, []):
                parsed = _span_range(span, output.get("source_scope", "repository"))
                if parsed is None:
                    continue
                identity, start, end = parsed
                for selected_start, selected_end in selected.get(identity, []):
                    first, last = max(start, selected_start), min(end, selected_end)
                    if first <= last:
                        intersections.setdefault(identity, []).append((first, last))
        if not intersections:
            continue
        ranges = []
        for (scope, path, file_hash), intervals in sorted(intersections.items()):
            merged: list[list[int]] = []
            for start, end in sorted(intervals):
                if merged and start <= merged[-1][1] + 1:
                    merged[-1][1] = max(merged[-1][1], end)
                else:
                    merged.append([start, end])
            ranges.extend({"source_scope": scope, "path": path, "file_hash": file_hash,
                           "start_line": start, "end_line": end} for start, end in merged)
        seen.add(result["action_id"])
        items.append({
            "action_id": result["action_id"], "input_hash": result["input_hash"],
            "tool": result["tool"], "diff_hash": result.get("workspace_diff_hash"),
            "ranges": ranges[:MAX_SOURCE_RANGES],
            "omitted_range_count": max(0, len(ranges) - MAX_SOURCE_RANGES),
        })
    return {
        "items": items[:MAX_SOURCE_RECEIPTS],
        "omitted_action_count": max(0, len(items) - MAX_SOURCE_RECEIPTS),
        "interpretation": "Receipt IDs for selected public source ranges only; no new source "
                          "or edit permission. Reading source is not execution or coverage proof.",
    }


def _results(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results = {}
    for event in events:
        if event.get("event_type") != "action_finished":
            continue
        result = event.get("payload", {}).get("result")
        if (isinstance(result, dict) and isinstance(result.get("action_id"), str)
                and isinstance(result.get("input_hash"), str) and result["input_hash"]
                and result.get("status") == "succeeded"
                and isinstance(result.get("output"), dict)):
            results[result["action_id"]] = result
    return results


def parse(
    raw: Any, *, events: list[dict[str, Any]], diff_hash: str, turn_id: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Bind a model claim to prior results; never infer that those results cover it."""
    try:
        review = _Review.model_validate(raw)
    except ValidationError:
        return None, "invalid_scope_review"
    results = _results(events)
    sources = []
    for action_id in review.source_action_ids:
        result = results.get(action_id)
        if result is None or result.get("tool") not in _SOURCE_TOOLS:
            return None, "scope_review_source_not_observed"
        sources.append({
            "action_id": action_id, "input_hash": result["input_hash"],
            "tool": result["tool"], "diff_hash": result.get("workspace_diff_hash"),
        })
    cases = []
    for case in review.cases:
        value = case.model_dump(mode="json")
        value["execution"] = None
        if case.disposition == "executed":
            result = results.get(case.evidence_action_id)
            if result is None or result.get("tool") not in _EXECUTION_TOOLS:
                return None, "scope_review_execution_not_observed"
            output = result["output"]
            if (result.get("workspace_diff_hash") != diff_hash
                    or output.get("diff_hash") != diff_hash):
                return None, "scope_review_execution_not_current"
            value["execution"] = {
                "action_id": result["action_id"], "input_hash": result["input_hash"],
                "tool": result["tool"], "diff_hash": diff_hash,
                "observation": {key: copy.deepcopy(output[key]) for key in _OBSERVATION_FIELDS
                                if key in output},
            }
        elif case.evidence_action_id is not None:
            return None, "scope_review_nonexecution_has_execution_id"
        elif case.disposition == "source_inferred" and not sources:
            return None, "scope_review_source_inference_without_source"
        cases.append(value)
    return {
        "scope": review.scope, "source_action_ids": list(review.source_action_ids),
        "source_evidence": sources, "cases": cases, "diff_hash": diff_hash,
        "turn_id": turn_id, "interpretation_status": "model_authored_unverified",
        "coverage_status": "not_certified",
    }, None


def project(review: dict[str, Any], diff_hash: str) -> dict[str, Any]:
    result = copy.deepcopy(review)

    def currency(value: dict[str, Any]) -> str:
        origin = value.get("diff_hash")
        return "unknown" if origin is None else "current" if origin == diff_hash else "historical"

    result["diff_currency"] = currency(result)
    for source in result.get("source_evidence", []):
        source["currency"] = currency(source)
    for case in result.get("cases", []):
        if isinstance(case.get("execution"), dict):
            case["execution"]["currency"] = currency(case["execution"])
    return result
