"""Bounded response usage evidence, before compatibility zero defaults.

Never dump the response, unknown fields, field values of unexpected types, or
reasoning. HTTP evidence is a field projection, not a raw HTTP-body capture.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

_MISSING = object()
_MAX_COUNTER = (1 << 63) - 1
_MAX_DIAGNOSTIC_BODY_BYTES = 1_048_576
_REQUEST_ID = re.compile(r"req_(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-"
                         r"[a-fA-F0-9]{12})")
_RESPONSE_ID = re.compile(r"resp_[a-fA-F0-9]{16,128}")
_STATUSES = frozenset({"completed", "incomplete", "failed", "in_progress", "cancelled", "queued"})
_INCOMPLETE_REASONS = frozenset({"max_output_tokens", "content_filter"})


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name, _MISSING)
    # SDK models default an omitted optional field to None. fields_set preserves
    # omission versus explicit null; getattr alone loses that distinction.
    fields_set = getattr(value, "model_fields_set", None)
    if isinstance(fields_set, (set, frozenset)) and name not in fields_set:
        return _MISSING
    return getattr(value, name, _MISSING)


def _object_state(value: Any) -> str:
    if value is _MISSING:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, dict) or hasattr(value, "__dict__"):
        return "object"
    return "invalid_type"


def _counter(container: Any, field: str) -> dict[str, Any]:
    if _object_state(container) != "object":
        return {"state": "unavailable"}
    value = _field(container, field)
    if value is _MISSING:
        return {"state": "missing"}
    if value is None:
        return {"state": "null"}
    if type(value) is not int:
        return {"state": "invalid_type"}
    if not 0 <= value <= _MAX_COUNTER:
        return {"state": "invalid_value"}
    return {"state": "integer", "value": value}


def usage_token_value(evidence: dict[str, Any], name: str) -> int:
    """Compatibility counters alone are NOT proof that provider usage was zero."""
    return evidence["fields"][name].get("value", 0)


def provider_usage_evidence(response: Any, requested_input_tokens: int) -> dict[str, Any]:
    usage = _field(response, "usage")
    input_details = _field(usage, "input_tokens_details")
    output_details = _field(usage, "output_tokens_details")
    fields = {
        "input_tokens": _counter(usage, "input_tokens"),
        "output_tokens": _counter(usage, "output_tokens"),
        "cached_input_tokens": _counter(input_details, "cached_tokens"),
        "reasoning_output_tokens": _counter(output_details, "reasoning_tokens"),
        "total_tokens": _counter(usage, "total_tokens"),
    }
    observed_input = fields["input_tokens"].get("value")
    relation = (
        "unavailable" if observed_input is None else
        "matched" if observed_input == requested_input_tokens else "mismatched"
    )
    usage_state = _object_state(usage)
    failure = None
    if usage_state != "object":
        failure = f"usage_{usage_state}"
    else:
        for name in ("input_tokens", "output_tokens"):
            if fields[name]["state"] != "integer":
                failure = f"{name}_{fields[name]['state']}"
                break
        cached = fields["cached_input_tokens"]
        if failure is None and (
            _object_state(input_details) == "invalid_type"
            or cached["state"] in {"invalid_type", "invalid_value"}
            or cached.get("value", 0) > observed_input
        ):
            failure = "cached_input_tokens_invalid"
        if failure is None and relation == "mismatched":
            failure = "input_token_count_mismatch"
    return {
        "schema_version": "provider-usage-evidence-v1",
        "observation_layer": "sdk_response",
        "usage_state": usage_state,
        "input_details_state": _object_state(input_details),
        "output_details_state": _object_state(output_details),
        "fields": fields,
        "requested_input_tokens": requested_input_tokens,
        "input_count_relation": relation,
        "input_token_delta": (
            observed_input - requested_input_tokens if observed_input is not None else None
        ),
        # Preserve the existing conservative no-cache-discount default when the
        # optional breakdown is absent. Missing input/output is NOT free usage.
        "cached_tokens_defaulted": fields["cached_input_tokens"]["state"] != "integer",
        "failure_kind": failure,
    }


def _label(value: Any, allowed: Any) -> dict[str, Any]:
    if value is _MISSING:
        return {"state": "missing"}
    if value is None:
        return {"state": "null"}
    if not isinstance(value, str):
        return {"state": "invalid_type"}
    if len(value) <= 133 and (
        allowed.fullmatch(value) if isinstance(allowed, re.Pattern) else value in allowed
    ):
        return {"state": "value", "value": value}
    return {"state": "redacted"}


def _response_metadata(response: Any) -> dict[str, Any]:
    details = _field(response, "incomplete_details")
    return {
        "response_id": _label(_field(response, "id"), _RESPONSE_ID),
        "status": _label(_field(response, "status"), _STATUSES),
        "incomplete_details_state": _object_state(details),
        "incomplete_reason": _label(_field(details, "reason"), _INCOMPLETE_REASONS),
    }


def response_diagnostics(
    http_response: httpx.Response | None, response: Any, requested_input_tokens: int,
) -> dict[str, Any]:
    """Compare buffered HTTP JSON with SDK fields; no I/O or accounting decisions.

    Call only for a failed/incomplete parsed response. Unknown labels and invalid
    counter values are not retained. Missing HTTP evidence cannot certify agreement.
    """
    result: dict[str, Any] = {
        "schema_version": "provider-response-diagnostics-v1",
        "http_status": None,
        "request_id": {"state": "unavailable"},
        "body_state": "unavailable",
        "comparison": "unavailable",
        "changed_fields": [],
        "sdk_metadata": _response_metadata(response),
    }
    if not isinstance(http_response, httpx.Response):
        return result
    result["http_status"] = http_response.status_code
    result["request_id"] = _label(http_response.headers.get("x-request-id", _MISSING), _REQUEST_ID)
    try:
        content = http_response.content  # Never read an unconsumed stream.
    except httpx.ResponseNotRead:
        result["body_state"] = "not_buffered"
        return result
    result["body_bytes"] = len(content)
    if len(content) > _MAX_DIAGNOSTIC_BODY_BYTES:
        result["body_state"] = "over_limit"
        return result
    try:
        body = json.loads(content)
    except (ValueError, UnicodeError, RecursionError):
        result["body_state"] = "invalid_json"
        return result
    if not isinstance(body, dict):
        result["body_state"] = "invalid_object"
        return result
    result["body_state"] = "json_object"
    raw_metadata = _response_metadata(body)
    raw_usage = provider_usage_evidence(body, requested_input_tokens)
    raw_usage["observation_layer"] = "http_json"
    sdk_usage = provider_usage_evidence(response, requested_input_tokens)
    result["raw_metadata"], result["raw_usage"] = raw_metadata, raw_usage
    changed = [key for key in raw_metadata if raw_metadata[key] != result["sdk_metadata"][key]]
    changed += [f"usage.{key}" for key in
                ("usage_state", "input_details_state", "output_details_state")
                if raw_usage[key] != sdk_usage[key]]
    changed += [f"usage.{key}" for key in raw_usage["fields"]
                if raw_usage["fields"][key] != sdk_usage["fields"][key]]
    result["changed_fields"] = changed
    states = [value["state"] for metadata in (raw_metadata, result["sdk_metadata"])
              for value in metadata.values() if isinstance(value, dict)]
    states += [metadata["incomplete_details_state"]
               for metadata in (raw_metadata, result["sdk_metadata"])]
    for usage in (raw_usage, sdk_usage):
        states += [usage[key] for key in
                   ("usage_state", "input_details_state", "output_details_state")]
        states += [value["state"] for value in usage["fields"].values()]
    unverifiable = any(state in {"redacted", "invalid_type", "invalid_value"} for state in states)
    result["comparison"] = (
        "different" if changed else "unverifiable_selected_fields" if unverifiable
        else "matched_selected_fields"
    )
    return result


def usage_failure_message(evidence: dict[str, Any] | None) -> str:
    failure = evidence.get("failure_kind") if evidence else None
    if failure in {"usage_missing", "usage_null"}:
        return f"provider usage is {failure.removeprefix('usage_')}; billing is unknown"
    if failure and failure != "input_token_count_mismatch":
        return "provider usage has unavailable or invalid billing fields; billing is unknown"
    return "provider usage disagreed with the pre-dispatch input count"
