"""Bounded whole-body Responses transport with zero SDK retries.

The caller owns cost admission and the shared execution deadline. This facade owns
only its async client and waits. Closing it never claims remote cancellation.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from dataclasses import asdict, dataclass
from types import SimpleNamespace

import httpx
import openai

from patchloop.agent import rate_limit_retry
from patchloop.agent.model import OFFICIAL_API_BASE_URL
from patchloop.errors import ContractError
from patchloop.util import sha256_json


@dataclass(frozen=True)
class RequestWaits:
    input_count_seconds: float = 30.0
    provider_response_seconds: float = 300.0
    client_cleanup_seconds: float = 5.0

    def contract(self):
        return {
            **asdict(self),
            "kind": "episode-request-waits-v1",
            "effective_limit": "min(per-request limit, remaining execution deadline)",
            "mechanism": "async SDK cancellation; local parsing checked before actions",
            "sdk_retries": 0,
            "automatic_retry": False,
        }


WAITS = RequestWaits()
PHASES = frozenset({
    "input_count_wait", "input_count_response_processing", "provider_response_wait",
    "provider_response_processing", "provider_usage_validation", "continuation_processing",
    "pre_tool_admission", "client_cleanup", "compaction_wait", "compaction_processing",
})


class RequestWaitExpired(TimeoutError):
    """The collector's outer request timer expired (not an SDK I/O timeout)."""


def exception_evidence(exc):
    """Only fixed labels; never str/repr, class names, causes, headers or response bodies."""
    for cls, category in (
        (RequestWaitExpired, "request_wait_limit"),
        (openai.APITimeoutError, "sdk_timeout"),
        (httpx.TimeoutException, "transport_timeout"),
        (TimeoutError, "timeout"),
        (openai.APIConnectionError, "connection_error"),
        (httpx.TransportError, "connection_error"),
        (openai.APIStatusError, "http_status_error"),
        (openai.APIResponseValidationError, "response_validation_error"),
        (ValueError, "value_error"),
        (TypeError, "type_error"),
        (ContractError, "contract_error"),
        (OSError, "io_error"),
        (KeyboardInterrupt, "interrupted"),
        (SystemExit, "interrupted"),
    ):
        if isinstance(exc, cls):
            return {"category": category, "exception_type": cls.__name__}
    return {"category": "unexpected_error", "exception_type": "Exception"}


class BoundedResponsesClient:
    """Sync facade over one owned async SDK client, reused by the existing parser."""

    max_retries = 0

    def __init__(self, *, api_key: str, client=None, retry_policy="none", record=None):
        if retry_policy not in {"none", rate_limit_retry.POLICY}:
            raise ContractError("unknown provider rate-limit policy")
        if retry_policy != "none" and record is None:
            raise ContractError("rate-limit retries require a durable event recorder")
        if client is not None and client.max_retries != 0:
            raise ContractError("bounded transport requires zero SDK retries")
        self.runner = asyncio.Runner()
        self.closed = False
        self.phase = None
        self.observe_response = lambda _: None
        self.response_received = False
        self.received_response = None
        self.received_http_response = None
        self.retry_policy, self.record = retry_policy, record

        async def create():
            transport = httpx.AsyncClient(trust_env=False)
            try:
                return openai.AsyncOpenAI(
                    api_key=api_key, base_url=OFFICIAL_API_BASE_URL,
                    http_client=transport, max_retries=0,
                )
            except BaseException:
                await transport.aclose()
                raise

        try:
            self.client = client if client is not None else self.runner.run(create())
        except BaseException:
            self.runner.close()
            raise
        self.responses = SimpleNamespace(
            create=lambda **kw: self._request("provider_response", **kw),
            compact=lambda **kw: self._request("compaction", **kw),
            input_tokens=SimpleNamespace(count=lambda **kw: self._request("input_count", **kw)),
        )

    def _request(self, kind, *, timeout, **payload):
        if self.closed or timeout <= 0:
            raise ContractError("bounded request requires an open client and positive wait")
        self.phase = kind + "_wait"
        self.response_received, self.received_response = False, None
        self.received_http_response = None

        async def fetch():
            timer = asyncio.timeout(timeout)
            try:
                async with timer:
                    api = self.client.responses
                    if kind == "compaction":
                        method = api.with_raw_response.compact
                    elif kind == "provider_response":
                        method = api.with_raw_response.create
                    else:
                        method = api.input_tokens.with_raw_response.count
                    if self.retry_policy == "none" or kind == "compaction":
                        return await method(**payload, timeout=timeout)
                    identity = {
                        "transport_request_id": "transport_" + uuid.uuid4().hex,
                        "request_kind": kind, "request_hash": sha256_json(payload),
                    }
                    waited = 0.0
                    for attempt in range(1, rate_limit_retry.MAX_ATTEMPTS + 1):
                        remaining = timer.when() - asyncio.get_running_loop().time()
                        if remaining <= 0:
                            raise RequestWaitExpired()
                        attempt_identity = {**identity, "attempt_no": attempt}
                        # The parallel journal checks its shared stop latch here;
                        # a rejected or failed append prevents this physical send.
                        self.record("provider_transport_attempt_started", attempt_identity)
                        remaining = timer.when() - asyncio.get_running_loop().time()
                        if remaining <= 0:
                            raise RequestWaitExpired()
                        try:
                            raw = await method(**payload, timeout=remaining)
                        except openai.RateLimitError as exc:
                            rejection = rate_limit_retry.temporary_rejection(exc)
                            if rejection is None:
                                raise
                            self.record("provider_transport_rejected429", {
                                **attempt_identity, **rejection,
                            })
                            if attempt == rate_limit_retry.MAX_ATTEMPTS:
                                raise
                            hint = rate_limit_retry.retry_after_seconds(exc.response.headers)
                            delay = (hint if hint is not None else 2.0 ** attempt)
                            delay += random.uniform(0.1, 1.0)
                            remaining = timer.when() - asyncio.get_running_loop().time()
                            if (waited + delay > rate_limit_retry.MAX_BACKOFF_SECONDS
                                    or delay >= remaining):
                                raise
                            self.record("provider_transport_retry_scheduled", {
                                **attempt_identity, "delay_seconds": delay,
                                "delay_source": "retry-after" if hint is not None else "backoff",
                            })
                            await asyncio.sleep(delay)
                            waited += delay
                        else:
                            self.record("provider_transport_attempt_received", {
                                **attempt_identity, "http_status": raw.http_response.status_code,
                            })
                            return raw
                    raise AssertionError("bounded attempts did not return or raise")
            except TimeoutError as exc:
                if timer.expired():
                    raise RequestWaitExpired() from exc
                raise

        raw = self.runner.run(fetch())
        self.received_http_response = raw.http_response if kind == "provider_response" else None
        self.response_received = True
        self.phase = kind + "_processing" if kind in {"provider_response", "compaction"} else (
            "input_count_response_processing"
        )
        self.observe_response(self.phase)
        # The pinned SDK's raw-response parse is synchronous and performs no I/O.
        response = raw.parse()
        self.received_response = response
        return response

    def close(self, timeout=WAITS.client_cleanup_seconds):
        if self.closed:
            return
        self.closed = True
        self.phase = "client_cleanup"

        async def cleanup():
            async with asyncio.timeout(timeout):
                await self.client.close()

        try:
            self.runner.run(cleanup())
        finally:
            self.received_response = None
            self.received_http_response = None
            # Runner.close() joins its default executor for up to five minutes.
            # An OS DNS lookup may outlive coroutine cancellation; it must not hold
            # up the durable failure receipt. Closing the loop prevents re-entry.
            # This does not assert OS-thread termination or remote cancellation.
            self.runner.get_loop().close()
