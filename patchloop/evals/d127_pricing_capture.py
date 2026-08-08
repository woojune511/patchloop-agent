"""Replayable, bounded capture of the official GPT-5.4 mini pricing page.

The capture API deliberately accepts no client, fetcher, URL, body, or clock
override.  Artifact-producing code therefore cannot substitute a test document
through the public API.  Tests replace only the lower ``httpx.Client`` boundary.
"""

from __future__ import annotations

import base64
import binascii
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from patchloop.util import canonical_json, sha256_bytes, sha256_text

SCHEMA_VERSION = "patchloop.d127.official-pricing-decoded-entity.v1"
OFFICIAL_HOST = "developers.openai.com"
OFFICIAL_MODEL_PAGE_URL = (
    "https://developers.openai.com/api/docs/models/gpt-5.4-mini.md"
)
MAX_REDIRECTS = 3
MAX_DECODED_ENTITY_BYTES = 128_000
STREAM_CHUNK_BYTES = 8_192
REQUEST_TIMEOUT_SECONDS = 30.0

MODEL_LABEL = "GPT-5.4 mini"
MODEL_ID = "gpt-5.4-mini-2026-03-17"
INPUT_RATE = Decimal("0.75")
CACHED_INPUT_RATE = Decimal("0.075")
OUTPUT_RATE = Decimal("4.5")
MAX_TOTAL_TOKENS = 3_000_000
MAX_OUTPUT_TOKENS = 25_000
SCHEDULED_ROWS = 4
PER_ROW_RESERVE = Decimal("13.6125")
FULL_SCHEDULE_RESERVE = Decimal("54.45")
HARD_CAP = Decimal("55.00")

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_REQUEST_HEADERS = {
    "Accept": "text/markdown",
    "Accept-Encoding": "identity",
    "User-Agent": "PatchLoop-D127-Pricing-Evidence/1",
}
_FORBIDDEN_REQUEST_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})
_EVIDENCE_KEYS = (
    "schema_version",
    "observed_at",
    "source_url",
    "final_url",
    "official_host",
    "http_status",
    "content_type",
    "content_encoding",
    "etag",
    "redirect_count",
    "public_get_request_count",
    "max_decoded_entity_bytes",
    "decoded_entity_base64",
    "decoded_entity_bytes",
    "decoded_entity_sha256",
    "wire_bytes_retained",
    "origin_signature",
    "request_auth_or_cookie_sent",
    "proxy_use_disabled",
    "manual_redirects",
    "required_evidence_lines",
    "required_evidence_sha256",
    "facts",
    "facts_sha256",
    "planning_math",
    "planning_math_sha256",
)


class D127PricingCaptureError(ValueError):
    """The official pricing response or retained evidence failed closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D127PricingCaptureError(message)


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validate_utc_text(value: Any) -> None:
    _require(isinstance(value, str) and value.endswith("Z"), "D-127 observed_at is not UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise D127PricingCaptureError("D-127 observed_at is invalid") from exc
    _require(parsed.utcoffset() is not None, "D-127 observed_at has no UTC offset")
    _require(parsed.utcoffset().total_seconds() == 0, "D-127 observed_at is not UTC")


def _validate_exact_url(value: str) -> httpx.URL:
    try:
        parsed = httpx.URL(value)
    except (TypeError, ValueError) as exc:
        raise D127PricingCaptureError("D-127 official docs URL is invalid") from exc
    _require(str(parsed) == OFFICIAL_MODEL_PAGE_URL, "D-127 official docs URL differs")
    _require(
        parsed.scheme == "https"
        and parsed.host == OFFICIAL_HOST
        and parsed.port in (None, 443)
        and not parsed.username
        and not parsed.password,
        "D-127 official docs origin differs",
    )
    return parsed


def _bounded_header(value: str | None, *, label: str, maximum: int) -> str | None:
    if value is None:
        return None
    _require(isinstance(value, str), f"D-127 {label} is not text")
    _require(len(value) <= maximum, f"D-127 {label} is too large")
    _require("\r" not in value and "\n" not in value, f"D-127 {label} is invalid")
    return value


def _required_evidence_lines() -> tuple[str, ...]:
    return (
        f"Default snapshot: `{MODEL_ID}`",
        "| Input | $0.75 | 1M tokens |",
        "| Cached input | $0.075 | 1M tokens |",
        "| Output | $4.5 | 1M tokens |",
        "| Responses | `v1/responses` | Supported |",
        "| GPT-5.4 mini | $0.75 | $0.075 | $4.5 |",
    )


def _validate_pricing_text(text: str) -> None:
    lines = _required_evidence_lines()
    _require(all(line in text for line in lines), "D-127 pricing facts differ")


def _expected_facts() -> dict[str, Any]:
    return {
        "model_label": MODEL_LABEL,
        "dated_model_id": MODEL_ID,
        "service_tier": "default-standard",
        "unit": "usd-per-1m-text-tokens",
        "input_usd": str(INPUT_RATE),
        "cached_input_usd": str(CACHED_INPUT_RATE),
        "cache_write_input_usd": None,
        "output_usd": str(OUTPUT_RATE),
        "responses_endpoint_supported": True,
    }


def _expected_planning_math() -> dict[str, Any]:
    worst_rate = max(INPUT_RATE, CACHED_INPUT_RATE, OUTPUT_RATE)
    per_row = (
        Decimal(MAX_TOTAL_TOKENS + MAX_OUTPUT_TOKENS) * worst_rate / Decimal(1_000_000)
    )
    full_schedule = per_row * Decimal(SCHEDULED_ROWS)
    _require(per_row == PER_ROW_RESERVE, "D-127 per-row reserve arithmetic differs")
    _require(full_schedule == FULL_SCHEDULE_RESERVE, "D-127 schedule reserve arithmetic differs")
    return {
        "max_total_tokens": MAX_TOTAL_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "conservative_worst_rate_usd_per_million": str(worst_rate),
        "per_row_reserve_usd": str(PER_ROW_RESERVE),
        "scheduled_rows": SCHEDULED_ROWS,
        "full_schedule_reserve_usd": str(FULL_SCHEDULE_RESERVE),
        "hard_cap_usd": str(HARD_CAP),
        "per_row_reserve_nanos": 13_612_500_000,
        "full_schedule_reserve_nanos": 54_450_000_000,
        "hard_cap_nanos": 55_000_000_000,
    }


def _assert_request_boundary(request: Any, expected_url: str) -> None:
    _require(request is not None, "D-127 request is unavailable")
    _require(str(request.method).upper() == "GET", "D-127 official docs method differs")
    _validate_exact_url(str(request.url))
    _require(str(request.url) == expected_url, "D-127 response request URL differs")
    header_names = {str(name).lower() for name in request.headers}
    _require(
        not header_names.intersection(_FORBIDDEN_REQUEST_HEADERS),
        "D-127 official docs request carried authority headers",
    )


def _read_decoded_entity(response: Any) -> bytes:
    chunks: list[bytes] = []
    observed_bytes = 0
    for chunk in response.iter_bytes(chunk_size=STREAM_CHUNK_BYTES):
        _require(isinstance(chunk, bytes), "D-127 decoded entity chunk is not bytes")
        if not chunk:
            continue
        observed_bytes += len(chunk)
        _require(
            observed_bytes <= MAX_DECODED_ENTITY_BYTES,
            "D-127 decoded entity exceeds the 128KB bound",
        )
        chunks.append(chunk)
    _require(observed_bytes > 0, "D-127 decoded entity is empty")
    # The full decoded entity is allocated only after its cumulative bound has passed.
    return b"".join(chunks)


def _capture_response() -> tuple[dict[str, Any], bytes]:
    current_url = OFFICIAL_MODEL_PAGE_URL
    redirects = 0
    with httpx.Client(
        trust_env=False,
        follow_redirects=False,
        timeout=REQUEST_TIMEOUT_SECONDS,
        auth=None,
        cookies=None,
    ) as client:
        while True:
            _validate_exact_url(current_url)
            client.cookies.clear()
            request = client.build_request("GET", current_url, headers=dict(_REQUEST_HEADERS))
            _assert_request_boundary(request, current_url)
            with client.send(
                request,
                stream=True,
                follow_redirects=False,
            ) as response:
                _require(response.request is request, "D-127 response request binding differs")
                status_code = int(response.status_code)
                response_url = str(response.url)
                _validate_exact_url(response_url)
                _require(response_url == current_url, "D-127 response URL differs from request")
                if status_code in _REDIRECT_STATUSES:
                    redirects += 1
                    _require(redirects <= MAX_REDIRECTS, "D-127 redirect limit exceeded")
                    location = _bounded_header(
                        response.headers.get("Location"),
                        label="redirect location",
                        maximum=2_048,
                    )
                    _require(
                        location is not None and location != "",
                        "D-127 redirect has no location",
                    )
                    current_url = str(httpx.URL(current_url).join(location))
                    _validate_exact_url(current_url)
                    continue

                _require(status_code == 200, "D-127 official model page status differs")
                content_type = _bounded_header(
                    response.headers.get("Content-Type"),
                    label="content type",
                    maximum=256,
                )
                _require(
                    content_type is not None
                    and content_type.partition(";")[0].strip().casefold() == "text/markdown",
                    "D-127 official model page content type differs",
                )
                content_encoding = _bounded_header(
                    response.headers.get("Content-Encoding"),
                    label="content encoding",
                    maximum=128,
                )
                _require(
                    content_encoding is None or content_encoding.casefold() == "identity",
                    "D-127 official model page content encoding is not identity",
                )
                etag = _bounded_header(response.headers.get("ETag"), label="ETag", maximum=512)
                decoded_entity = _read_decoded_entity(response)
                return (
                    {
                        "final_url": response_url,
                        "http_status": status_code,
                        "content_type": content_type,
                        "content_encoding": content_encoding,
                        "etag": etag,
                        "redirect_count": redirects,
                        "public_get_request_count": redirects + 1,
                    },
                    decoded_entity,
                )


def capture_official_pricing_evidence() -> dict[str, Any]:
    """Capture the exact decoded official Markdown entity without injectable inputs."""

    response, decoded_entity = _capture_response()
    try:
        text = decoded_entity.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise D127PricingCaptureError("D-127 decoded entity is not UTF-8") from exc
    _validate_pricing_text(text)
    required_lines = list(_required_evidence_lines())
    facts = _expected_facts()
    planning_math = _expected_planning_math()
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "observed_at": _utc_now_text(),
        "source_url": OFFICIAL_MODEL_PAGE_URL,
        "final_url": response["final_url"],
        "official_host": OFFICIAL_HOST,
        "http_status": response["http_status"],
        "content_type": response["content_type"],
        "content_encoding": response["content_encoding"],
        "etag": response["etag"],
        "redirect_count": response["redirect_count"],
        "public_get_request_count": response["public_get_request_count"],
        "max_decoded_entity_bytes": MAX_DECODED_ENTITY_BYTES,
        "decoded_entity_base64": base64.b64encode(decoded_entity).decode("ascii"),
        "decoded_entity_bytes": len(decoded_entity),
        "decoded_entity_sha256": sha256_bytes(decoded_entity),
        "wire_bytes_retained": False,
        "origin_signature": False,
        "request_auth_or_cookie_sent": False,
        "proxy_use_disabled": True,
        "manual_redirects": True,
        "required_evidence_lines": required_lines,
        "required_evidence_sha256": sha256_text(canonical_json(required_lines)),
        "facts": facts,
        "facts_sha256": sha256_text(canonical_json(facts)),
        "planning_math": planning_math,
        "planning_math_sha256": sha256_text(canonical_json(planning_math)),
    }
    validate_official_pricing_evidence(evidence)
    return evidence


def _decode_retained_entity(value: Any) -> bytes:
    _require(isinstance(value, str) and value != "", "D-127 decoded entity Base64 differs")
    maximum_base64_bytes = 4 * ((MAX_DECODED_ENTITY_BYTES + 2) // 3)
    _require(len(value) <= maximum_base64_bytes, "D-127 decoded entity Base64 is too large")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise D127PricingCaptureError("D-127 decoded entity Base64 is invalid") from exc
    _require(
        base64.b64encode(decoded).decode("ascii") == value,
        "D-127 decoded entity Base64 is noncanonical",
    )
    return decoded


def validate_official_pricing_evidence(value: Any) -> dict[str, Any]:
    """Replay the retained entity and validate all pricing and planning bindings."""

    _require(isinstance(value, dict), "D-127 pricing evidence is not an object")
    _require(tuple(value) == _EVIDENCE_KEYS, "D-127 pricing evidence fields differ")
    _require(value["schema_version"] == SCHEMA_VERSION, "D-127 pricing schema differs")
    _validate_utc_text(value["observed_at"])
    _require(value["source_url"] == OFFICIAL_MODEL_PAGE_URL, "D-127 pricing source differs")
    _require(value["final_url"] == OFFICIAL_MODEL_PAGE_URL, "D-127 pricing final URL differs")
    _validate_exact_url(value["source_url"])
    _validate_exact_url(value["final_url"])
    _require(value["official_host"] == OFFICIAL_HOST, "D-127 pricing host differs")
    _require(
        type(value["http_status"]) is int and value["http_status"] == 200,
        "D-127 status differs",
    )
    content_type = _bounded_header(value["content_type"], label="content type", maximum=256)
    _require(
        content_type is not None
        and content_type.partition(";")[0].strip().casefold() == "text/markdown",
        "D-127 content type differs",
    )
    content_encoding = _bounded_header(
        value["content_encoding"],
        label="content encoding",
        maximum=128,
    )
    _require(
        content_encoding is None or content_encoding.casefold() == "identity",
        "D-127 content encoding is not identity",
    )
    _bounded_header(value["etag"], label="ETag", maximum=512)
    _require(
        type(value["redirect_count"]) is int
        and 0 <= value["redirect_count"] <= MAX_REDIRECTS,
        "D-127 redirect count differs",
    )
    _require(
        type(value["public_get_request_count"]) is int
        and value["public_get_request_count"] == value["redirect_count"] + 1,
        "D-127 public GET count differs",
    )
    _require(
        value["max_decoded_entity_bytes"] == MAX_DECODED_ENTITY_BYTES,
        "D-127 decoded entity bound differs",
    )
    decoded_entity = _decode_retained_entity(value["decoded_entity_base64"])
    _require(
        0 < len(decoded_entity) <= MAX_DECODED_ENTITY_BYTES,
        "D-127 decoded entity size is outside the bound",
    )
    _require(
        type(value["decoded_entity_bytes"]) is int
        and value["decoded_entity_bytes"] == len(decoded_entity),
        "D-127 decoded entity byte count differs",
    )
    _require(
        value["decoded_entity_sha256"] == sha256_bytes(decoded_entity),
        "D-127 decoded entity SHA differs",
    )
    _require(value["wire_bytes_retained"] is False, "D-127 wire-byte claim differs")
    _require(value["origin_signature"] is False, "D-127 origin-signature claim differs")
    _require(
        value["request_auth_or_cookie_sent"] is False,
        "D-127 request authority claim differs",
    )
    _require(value["proxy_use_disabled"] is True, "D-127 proxy boundary differs")
    _require(value["manual_redirects"] is True, "D-127 redirect policy differs")
    try:
        text = decoded_entity.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise D127PricingCaptureError("D-127 retained entity is not UTF-8") from exc
    _validate_pricing_text(text)
    required_lines = list(_required_evidence_lines())
    _require(
        value["required_evidence_lines"] == required_lines,
        "D-127 evidence fragments differ",
    )
    _require(
        value["required_evidence_sha256"] == sha256_text(canonical_json(required_lines)),
        "D-127 evidence-line SHA differs",
    )
    facts = _expected_facts()
    _require(canonical_json(value["facts"]) == canonical_json(facts), "D-127 pricing facts differ")
    _require(
        value["facts_sha256"] == sha256_text(canonical_json(facts)),
        "D-127 pricing facts SHA differs",
    )
    planning_math = _expected_planning_math()
    _require(
        canonical_json(value["planning_math"]) == canonical_json(planning_math),
        "D-127 planning math differs",
    )
    _require(
        value["planning_math_sha256"] == sha256_text(canonical_json(planning_math)),
        "D-127 planning math SHA differs",
    )
    return value
