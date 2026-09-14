"""Bounded SDK-observed usage evidence, before compatibility zero defaults.

Never dump the response, unknown fields, field values of unexpected types, or
reasoning. SDK decoding may coerce types: this is not a raw HTTP-body capture.
"""

from __future__ import annotations

from typing import Any

_MISSING = object()
_MAX_COUNTER = (1 << 63) - 1


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


def usage_failure_message(evidence: dict[str, Any] | None) -> str:
    failure = evidence.get("failure_kind") if evidence else None
    if failure in {"usage_missing", "usage_null"}:
        return f"provider usage is {failure.removeprefix('usage_')}; billing is unknown"
    if failure and failure != "input_token_count_mismatch":
        return "provider usage has unavailable or invalid billing fields; billing is unknown"
    return "provider usage disagreed with the pre-dispatch input count"
