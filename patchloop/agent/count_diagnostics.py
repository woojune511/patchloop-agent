"""Operator-only input-count diagnostics; never retain free-form provider errors."""

from __future__ import annotations

import re
from typing import Any

import httpx
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.util import canonical_json, sha256_bytes

# Provider fields can echo input. Unknown values are omitted, not truncated into logs.
_ERROR_CODES = frozenset({
    "array_above_max_length", "context_length_exceeded", "invalid_api_key",
    "invalid_encrypted_content", "invalid_json", "invalid_parameter", "invalid_prompt",
    "invalid_request_error", "invalid_type", "invalid_value", "missing_required_parameter",
    "model_not_found", "request_too_large", "string_above_max_length", "unsupported_parameter",
    "unsupported_value", "rate_limit_exceeded", "insufficient_quota", "server_error",
})
_ERROR_TYPES = frozenset({
    "invalid_request_error", "authentication_error", "permission_error", "not_found_error",
    "rate_limit_error", "rate_limit_exceeded", "insufficient_quota", "server_error",
    "api_error", "tokens", "requests",
})
_EXCEPTION_TYPES = frozenset({
    "APIError", "APIStatusError", "APIResponseValidationError", "APIConnectionError",
    "APITimeoutError", "BadRequestError", "AuthenticationError", "PermissionDeniedError",
    "NotFoundError", "ConflictError", "UnprocessableEntityError", "RateLimitError",
    "InternalServerError", "TimeoutError", "ConnectTimeout", "ReadTimeout", "WriteTimeout",
    "PoolTimeout", "ConnectError", "ReadError", "WriteError", "RemoteProtocolError",
})
_PARAMETER = re.compile(
    r"(?:model|input|tools|tool_choice|reasoning|truncation|parallel_tool_calls)"
    r"(?:(?:\[[0-9]{1,6}\]|\.[0-9]{1,6})|\."
    r"(?:type|id|role|content|text|encrypted_content|status|call_id|name|arguments|output|"
    r"parameters|properties|required|additionalProperties|description|strict|effort|"
    r"summary|mode|context)){0,12}"
)
_REQUEST_ID = re.compile(r"req_(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-"
                         r"[a-fA-F0-9]{12})")


def input_count_request_metadata(request: dict[str, Any]) -> dict[str, Any]:
    """Measure the count body, not the generation body or its SDK timeout option.

    Canonical UTF-8 bytes are explicitly NOT claimed to be observed wire bytes.
    The exception's already-buffered HTTP request supplies that separate evidence.
    """
    payload = OpenAIResponsesAdapter._count_payload(request)
    encoded = canonical_json(payload).encode("utf-8")
    items = payload.get("input", [])
    items = items if isinstance(items, list) else []
    reasoning = [item for item in items if isinstance(item, dict)
                 and item.get("type") == "reasoning"]
    sizes = [len(item["encrypted_content"]) for item in reasoning
             if isinstance(item.get("encrypted_content"), str)]
    return {
        "schema_version": "input-count-diagnostics-v1",
        "count_payload_canonical_utf8_bytes": len(encoded),
        "count_payload_canonical_hash": sha256_bytes(encoded),
        "input_item_count": len(items),
        "reasoning_item_count": len(reasoning),
        "encrypted_content_characters": sum(sizes),
        "largest_encrypted_content_characters": max(sizes, default=0),
    }


def input_count_error_metadata(error: Exception) -> dict[str, Any]:
    """Extract a bounded allowlist; never stringify exceptions, messages or bodies."""
    name = type(error).__name__
    if isinstance(error, (APITimeoutError, TimeoutError, httpx.TimeoutException)):
        category = "timeout"
    elif isinstance(error, APIStatusError):
        category = "http_error"
    elif isinstance(error, (APIConnectionError, httpx.TransportError)):
        category = "transport_error"
    else:
        category = "unknown"
    result: dict[str, Any] = {
        "category": category,
        "exception_type": name if name in _EXCEPTION_TYPES else "Exception",
        "http_status": None, "code": None, "type": None, "param": None,
        "request_id": None, "redacted_fields": [],
    }
    if isinstance(error, APIStatusError):
        status = error.status_code
        if type(status) is int and 400 <= status <= 599:
            result["http_status"] = status
        request_id = error.request_id
        if isinstance(request_id, str) and len(request_id) <= 64 and _REQUEST_ID.fullmatch(
            request_id,
        ):
            result["request_id"] = request_id
        elif request_id is not None:
            result["redacted_fields"].append("request_id")
    if isinstance(error, APIError):
        body = error.body if isinstance(error.body, dict) else {}
        # Also accept a nested error object from injected clients; do not retain it.
        if isinstance(body.get("error"), dict):
            body = body["error"]
        for field, allowed in (("code", _ERROR_CODES), ("type", _ERROR_TYPES)):
            value = body.get(field)
            if isinstance(value, str) and len(value) <= 64 and value in allowed:
                result[field] = value
            elif value is not None:
                result["redacted_fields"].append(field)
        param = body.get("param")
        if isinstance(param, str) and len(param) <= 256 and _PARAMETER.fullmatch(param):
            result["param"] = param
        elif param is not None:
            result["redacted_fields"].append("param")
        if isinstance(error.request, httpx.Request):
            try:
                encoded = error.request.content  # Never consume an unread request stream.
            except httpx.RequestNotRead:
                pass
            else:
                result["observed_request_body_bytes"] = len(encoded)
                result["observed_request_body_hash"] = sha256_bytes(encoded)
    return result
