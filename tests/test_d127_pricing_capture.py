from __future__ import annotations

import base64
import copy
import inspect
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from patchloop.evals import d127_pricing_capture as d127
from patchloop.util import canonical_json, sha256_bytes, sha256_text

MODEL_PAGE = (
    b"# GPT-5.4 mini\n"
    b"Default snapshot: `gpt-5.4-mini-2026-03-17`\n"
    b"| Input | $0.75 | 1M tokens |\n"
    b"| Cached input | $0.075 | 1M tokens |\n"
    b"| Output | $4.5 | 1M tokens |\n"
    b"| Responses | `v1/responses` | Supported |\n"
    b"| GPT-5.4 mini | $0.75 | $0.075 | $4.5 |\n"
)


@dataclass
class ResponsePlan:
    status_code: int = 200
    url: str = d127.OFFICIAL_MODEL_PAGE_URL
    headers: dict[str, str] = field(
        default_factory=lambda: {
            "Content-Type": "text/markdown; charset=utf-8",
            "ETag": '"d127-test-etag"',
        }
    )
    chunks: tuple[bytes, ...] = (MODEL_PAGE,)


class FakeResponse:
    def __init__(
        self,
        plan: ResponsePlan,
        *,
        method: str,
        requested_url: str,
        request_headers: dict[str, str],
        request: httpx.Request | None = None,
    ) -> None:
        self.status_code = plan.status_code
        self.url = httpx.URL(plan.url)
        self.headers = httpx.Headers(plan.headers)
        self.request = request or httpx.Request(method, requested_url, headers=request_headers)
        self._chunks = plan.chunks
        self.iteration_count = 0

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def iter_bytes(self, *, chunk_size: int) -> Iterator[bytes]:
        assert chunk_size == d127.STREAM_CHUNK_BYTES
        for chunk in self._chunks:
            self.iteration_count += 1
            yield chunk


class FakeClient:
    def __init__(self, plans: list[ResponsePlan]) -> None:
        self.plans = plans
        self.constructor_calls: list[dict[str, Any]] = []
        self.stream_calls: list[tuple[str, str, dict[str, str]]] = []
        self.responses: list[FakeResponse] = []
        self.closed = False
        self.cookies = httpx.Cookies()

    def factory(self, **kwargs: Any) -> FakeClient:
        self.constructor_calls.append(dict(kwargs))
        return self

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.closed = True

    def build_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
    ) -> httpx.Request:
        request = httpx.Request(method, url, headers=headers)
        self.cookies.set_cookie_header(request)
        return request

    def send(
        self,
        request: httpx.Request,
        *,
        stream: bool,
        follow_redirects: bool,
    ) -> FakeResponse:
        assert stream is True
        assert follow_redirects is False
        method = request.method
        url = str(request.url)
        headers = dict(request.headers)
        self.stream_calls.append((method, url, dict(headers)))
        if not self.plans:
            raise AssertionError("unexpected HTTP request")
        plan = self.plans.pop(0)
        response = FakeResponse(
            plan,
            method=method,
            requested_url=url,
            request_headers=headers,
            request=request,
        )
        if "Set-Cookie" in plan.headers:
            self.cookies.set(
                "d127-test-cookie",
                "credential-like-cookie",
                domain="developers.openai.com",
                path="/",
            )
        self.responses.append(response)
        return response


def _install_httpx(
    monkeypatch: pytest.MonkeyPatch,
    *plans: ResponsePlan,
) -> FakeClient:
    client = FakeClient(list(plans))
    monkeypatch.setattr(d127.httpx, "Client", client.factory)
    return client


def _capture(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes = MODEL_PAGE,
) -> tuple[dict[str, Any], FakeClient]:
    client = _install_httpx(monkeypatch, ResponsePlan(chunks=(body,)))
    return d127.capture_official_pricing_evidence(), client


def test_production_capture_is_noninjectable_and_uses_exact_httpx_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(inspect.signature(d127.capture_official_pricing_evidence).parameters) == ()
    evidence, client = _capture(monkeypatch)

    assert client.constructor_calls == [
        {
            "trust_env": False,
            "follow_redirects": False,
            "timeout": 30.0,
            "auth": None,
            "cookies": None,
        }
    ]
    assert client.stream_calls == [
        (
            "GET",
            d127.OFFICIAL_MODEL_PAGE_URL,
            {
                "host": "developers.openai.com",
                "accept": "text/markdown",
                "accept-encoding": "identity",
                "user-agent": "PatchLoop-D127-Pricing-Evidence/1",
            },
        )
    ]
    assert client.closed is True
    assert evidence["source_url"] == d127.OFFICIAL_MODEL_PAGE_URL
    assert evidence["final_url"] == d127.OFFICIAL_MODEL_PAGE_URL
    assert evidence["request_auth_or_cookie_sent"] is False
    assert evidence["proxy_use_disabled"] is True


def test_capture_retains_exact_decoded_entity_and_replay_binds_facts_and_math(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence, _client = _capture(monkeypatch)
    decoded = base64.b64decode(evidence["decoded_entity_base64"], validate=True)

    assert decoded == MODEL_PAGE
    assert evidence["decoded_entity_bytes"] == len(MODEL_PAGE)
    assert evidence["decoded_entity_sha256"] == sha256_bytes(MODEL_PAGE)
    assert evidence["wire_bytes_retained"] is False
    assert evidence["origin_signature"] is False
    assert evidence["facts"] == {
        "model_label": "GPT-5.4 mini",
        "dated_model_id": "gpt-5.4-mini-2026-03-17",
        "service_tier": "default-standard",
        "unit": "usd-per-1m-text-tokens",
        "input_usd": "0.75",
        "cached_input_usd": "0.075",
        "cache_write_input_usd": None,
        "output_usd": "4.5",
        "responses_endpoint_supported": True,
    }
    assert evidence["planning_math"] == {
        "max_total_tokens": 3_000_000,
        "max_output_tokens": 25_000,
        "conservative_worst_rate_usd_per_million": "4.5",
        "per_row_reserve_usd": "13.6125",
        "scheduled_rows": 4,
        "full_schedule_reserve_usd": "54.45",
        "hard_cap_usd": "55.00",
        "per_row_reserve_nanos": 13_612_500_000,
        "full_schedule_reserve_nanos": 54_450_000_000,
        "hard_cap_nanos": 55_000_000_000,
    }
    assert d127.validate_official_pricing_evidence(evidence) is evidence


def test_decoded_entity_is_streamed_and_exact_128kb_bound_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = MODEL_PAGE + b"x" * (d127.MAX_DECODED_ENTITY_BYTES - len(MODEL_PAGE))
    split = (body[:64_000], body[64_000:120_000], body[120_000:])
    client = _install_httpx(monkeypatch, ResponsePlan(chunks=split))

    evidence = d127.capture_official_pricing_evidence()

    assert evidence["decoded_entity_bytes"] == 128_000
    assert base64.b64decode(evidence["decoded_entity_base64"], validate=True) == body
    assert client.responses[0].iteration_count == 3


def test_decoded_entity_over_128kb_fails_during_chunk_iteration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = (MODEL_PAGE, b"x" * (128_000 - len(MODEL_PAGE)), b"y")
    client = _install_httpx(monkeypatch, ResponsePlan(chunks=chunks))

    with pytest.raises(d127.D127PricingCaptureError, match="exceeds the 128KB bound"):
        d127.capture_official_pricing_evidence()

    assert client.responses[0].iteration_count == 3


def test_three_manual_self_redirects_are_allowed_without_reading_redirect_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirect = ResponsePlan(
        status_code=302,
        headers={
            "Location": d127.OFFICIAL_MODEL_PAGE_URL,
            "Set-Cookie": "d127-test-cookie=credential-like-cookie; Secure; Path=/",
        },
        chunks=(b"redirect body must not be read",),
    )
    client = _install_httpx(
        monkeypatch,
        copy.deepcopy(redirect),
        copy.deepcopy(redirect),
        copy.deepcopy(redirect),
        ResponsePlan(),
    )

    evidence = d127.capture_official_pricing_evidence()

    assert evidence["redirect_count"] == 3
    assert evidence["public_get_request_count"] == 4
    assert len(client.stream_calls) == 4
    assert all("cookie" not in headers for _method, _url, headers in client.stream_calls)
    assert [response.iteration_count for response in client.responses] == [0, 0, 0, 1]


def test_fourth_redirect_and_nonexact_origin_redirect_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirects = [
        ResponsePlan(
            status_code=307,
            headers={"Location": d127.OFFICIAL_MODEL_PAGE_URL},
            chunks=(),
        )
        for _ in range(4)
    ]
    client = _install_httpx(monkeypatch, *redirects)
    with pytest.raises(d127.D127PricingCaptureError, match="redirect limit exceeded"):
        d127.capture_official_pricing_evidence()
    assert len(client.stream_calls) == 4

    hostile = _install_httpx(
        monkeypatch,
        ResponsePlan(
            status_code=302,
            headers={"Location": "https://example.com/hostile.md"},
            chunks=(),
        ),
    )
    with pytest.raises(d127.D127PricingCaptureError, match="official docs URL differs"):
        d127.capture_official_pricing_evidence()
    assert len(hostile.stream_calls) == 1


@pytest.mark.parametrize(
    ("status", "headers", "chunks", "match"),
    [
        (503, {"Content-Type": "text/markdown"}, (MODEL_PAGE,), "status differs"),
        (200, {"Content-Type": "text/html"}, (MODEL_PAGE,), "content type differs"),
        (
            200,
            {"Content-Type": "text/markdown", "Content-Encoding": "gzip"},
            (MODEL_PAGE,),
            "content encoding is not identity",
        ),
        (
            200,
            {"Content-Type": "text/markdown"},
            (b"not the required official model page",),
            "pricing facts differ",
        ),
        (200, {"Content-Type": "text/markdown"}, (b"\xff",), "not UTF-8"),
    ],
)
def test_bad_final_response_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    headers: dict[str, str],
    chunks: tuple[bytes, ...],
    match: str,
) -> None:
    _install_httpx(
        monkeypatch,
        ResponsePlan(status_code=status, headers=headers, chunks=chunks),
    )
    with pytest.raises(d127.D127PricingCaptureError, match=match):
        d127.capture_official_pricing_evidence()


@pytest.mark.parametrize(
    "tamper",
    [
        "unknown-field",
        "body-bytes",
        "body-sha",
        "retained-body",
        "required-lines",
        "facts",
        "math",
        "wire-retention",
        "origin-signature",
        "request-authority",
        "content-encoding",
    ],
)
def test_validator_rejects_rehashed_or_boundary_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    evidence, _client = _capture(monkeypatch)
    value = copy.deepcopy(evidence)
    if tamper == "unknown-field":
        value["future_field"] = False
    elif tamper == "body-bytes":
        value["decoded_entity_bytes"] += 1
    elif tamper == "body-sha":
        value["decoded_entity_sha256"] = "sha256:" + "0" * 64
    elif tamper == "retained-body":
        body = MODEL_PAGE.replace(
            b"gpt-5.4-mini-2026-03-17",
            b"gpt-5.4-mini-missing",
        )
        value["decoded_entity_base64"] = base64.b64encode(body).decode("ascii")
        value["decoded_entity_bytes"] = len(body)
        value["decoded_entity_sha256"] = sha256_bytes(body)
    elif tamper == "required-lines":
        value["required_evidence_lines"] = value["required_evidence_lines"][:-1]
        value["required_evidence_sha256"] = sha256_text(
            canonical_json(value["required_evidence_lines"])
        )
    elif tamper == "facts":
        value["facts"]["input_usd"] = "0.76"
        value["facts_sha256"] = sha256_text(canonical_json(value["facts"]))
    elif tamper == "math":
        value["planning_math"]["per_row_reserve_nanos"] += 1
        value["planning_math_sha256"] = sha256_text(canonical_json(value["planning_math"]))
    elif tamper == "wire-retention":
        value["wire_bytes_retained"] = True
    elif tamper == "origin-signature":
        value["origin_signature"] = True
    elif tamper == "content-encoding":
        value["content_encoding"] = "gzip"
    else:
        value["request_auth_or_cookie_sent"] = True

    with pytest.raises(d127.D127PricingCaptureError):
        d127.validate_official_pricing_evidence(value)


def test_validator_rejects_malformed_oversized_and_non_utf8_base64(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence, _client = _capture(monkeypatch)
    malformed = copy.deepcopy(evidence)
    malformed["decoded_entity_base64"] = "%%%"
    with pytest.raises(d127.D127PricingCaptureError, match="Base64 is invalid"):
        d127.validate_official_pricing_evidence(malformed)

    oversized = copy.deepcopy(evidence)
    oversized["decoded_entity_base64"] = "A" * (
        4 * ((d127.MAX_DECODED_ENTITY_BYTES + 2) // 3) + 4
    )
    with pytest.raises(d127.D127PricingCaptureError, match="Base64 is too large"):
        d127.validate_official_pricing_evidence(oversized)

    non_utf8 = copy.deepcopy(evidence)
    body = b"\xff"
    non_utf8["decoded_entity_base64"] = base64.b64encode(body).decode("ascii")
    non_utf8["decoded_entity_bytes"] = len(body)
    non_utf8["decoded_entity_sha256"] = sha256_bytes(body)
    with pytest.raises(d127.D127PricingCaptureError, match="retained entity is not UTF-8"):
        d127.validate_official_pricing_evidence(non_utf8)
