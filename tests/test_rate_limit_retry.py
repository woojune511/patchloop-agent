from __future__ import annotations

import json
from datetime import UTC, datetime
from email.utils import format_datetime

import httpx
import openai
import pytest
from test_dev_conversation_v22 import _provider_smoke
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash

from patchloop.agent import rate_limit_retry as retry
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.request_transport import BoundedResponsesClient, RequestWaitExpired
from patchloop.dev import runner
from patchloop.dev.cost import pricing_for_model
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError


def rejection(code="rate_limit_exceeded", *, status=429, headers=None):
    return httpx.Response(status, json={"error": {
        "code": code, "type": "tokens", "message": "PRIVATE_ERROR_BODY",
    }}, headers={"retry-after": "0", "x-request-id": "req_test", **(headers or {})})


def response():
    return {"id": "resp_mock", "object": "response", "created_at": 0,
            "status": "completed", "model": "gpt-5.4-mini-2026-03-17", "output": [],
            "usage": {"input_tokens": 1000, "output_tokens": 10, "total_tokens": 1010,
                      "input_tokens_details": {"cached_tokens": 0},
                      "output_tokens_details": {"reasoning_tokens": 0}}}


def transport(handler, events, *, policy=retry.POLICY, record=None):
    return BoundedResponsesClient(
        api_key="unused", retry_policy=policy,
        record=record or (lambda kind, value: events.append((kind, value))),
        client=openai.AsyncOpenAI(api_key="unused", max_retries=0,
                                 http_client=httpx.AsyncClient(
                                     transport=httpx.MockTransport(handler), trust_env=False)),
    )


@pytest.fixture(autouse=True)
def no_random_wait(monkeypatch):
    monkeypatch.setattr("patchloop.agent.request_transport.random.uniform", lambda *args: 0)


@pytest.mark.parametrize("kind", ["input_count", "provider_response"])
def test_explicit_rejection_retries_same_payload_and_records_every_send(kind):
    seen, events = [], []

    def handler(request):
        seen.append(json.loads(request.content))
        if len(seen) == 1:
            return rejection()
        return httpx.Response(200, json=(response() if kind == "provider_response" else {
            "input_tokens": 1000, "object": "response.input_tokens"}))

    client = transport(handler, events)
    try:
        method = (client.responses.create if kind == "provider_response"
                  else client.responses.input_tokens.count)
        method(model="gpt-5.4-mini-2026-03-17", input=[], timeout=5)
        assert seen[0] == seen[1]
        assert [v["attempt_no"] for k, v in events if k.endswith("attempt_started")] == [1, 2]
        assert len({v["request_hash"] for _, v in events}) == 1
        assert [k for k, _ in events] == [
            "provider_transport_attempt_started", "provider_transport_rejected429",
            "provider_transport_retry_scheduled", "provider_transport_attempt_started",
            "provider_transport_attempt_received",
        ]
        rejected = events[1][1]
        assert rejected["usage_receipt"] is False and "cost_nanos" not in rejected
        assert "PRIVATE_ERROR_BODY" not in json.dumps(events)
    finally:
        client.close()


@pytest.mark.parametrize("code,status", [
    ("insufficient_quota", 429), ("credit_balance_exhausted", 429),
    ("project_spend_limit_exceeded", 429), ("unexpected", 429),
    (None, 429), ("rate_limit_exceeded", 500), ("rate_limit_exceeded", 503),
])
def test_non_temporary_or_unknown_failure_never_retries(code, status):
    seen, events = [], []

    def handler(request):
        seen.append(request)
        return rejection(code, status=status)

    client = transport(handler, events)
    try:
        with pytest.raises(openai.APIStatusError):
            client.responses.create(model="test", input=[], timeout=5)
        assert len(seen) == 1
        assert [k for k, _ in events] == ["provider_transport_attempt_started"]
    finally:
        client.close()


def test_three_sends_are_hard_bound_and_default_none_never_retries():
    for policy, expected in ((retry.POLICY, 3), ("none", 1)):
        seen, events = [], []

        def handler(request, seen=seen):
            seen.append(request)
            return rejection("slow_down")

        client = transport(handler, events, policy=policy)
        try:
            with pytest.raises(openai.RateLimitError):
                client.responses.create(model="test", input=[], timeout=5)
            assert len(seen) == expected
            if policy == "none":
                assert events == []
        finally:
            client.close()


@pytest.mark.parametrize("hint,timeout", [("121", 180), ("3", 1)])
def test_retry_after_longer_than_backoff_or_task_budget_is_not_shortened(hint, timeout):
    seen, events = [], []

    def handler(request):
        seen.append(request)
        return rejection(headers={"retry-after": hint})

    client = transport(handler, events)
    try:
        with pytest.raises(openai.RateLimitError):
            client.responses.create(model="test", input=[], timeout=timeout)
        assert len(seen) == 1
        assert not any(k.endswith("retry_scheduled") for k, _ in events)
    finally:
        client.close()


def test_retry_after_date_invalid_and_zero_hints():
    epoch = 1_700_000_000
    date = format_datetime(datetime.fromtimestamp(epoch + 17, UTC), usegmt=True)
    assert retry.retry_after_seconds({"retry-after": date}, now=epoch) == 17
    assert retry.retry_after_seconds({"retry-after": "0"}) == 0
    for value in ("NaN", "Infinity", "-1", "not-a-date", ""):
        assert retry.retry_after_seconds({"retry-after": value}) is None


def test_stop_or_failed_durable_record_prevents_retry_send():
    seen, events = [], []

    def handler(request):
        seen.append(request)
        return rejection()

    def record(kind, value):
        events.append((kind, value))
        if kind.endswith("attempt_started") and value["attempt_no"] == 2:
            raise ContractError("batch already stopped")

    client = transport(handler, events, record=record)
    try:
        with pytest.raises(ContractError, match="batch already stopped"):
            client.responses.create(model="test", input=[], timeout=5)
        assert len(seen) == 1
    finally:
        client.close()


def test_connection_timeout_and_cancellation_are_not_retried():
    seen, events = [], []

    def handler(request):
        seen.append(request)
        raise httpx.ReadTimeout("unknown remote result", request=request)

    client = transport(handler, events)
    try:
        with pytest.raises(openai.APITimeoutError):
            client.responses.create(model="test", input=[], timeout=5)
        assert len(seen) == 1
    finally:
        client.close()


def test_outer_timer_includes_retry_wait(monkeypatch):
    import asyncio

    original_sleep = asyncio.sleep
    seen, events = [], []

    async def slow_sleep(_):
        await original_sleep(1)

    monkeypatch.setattr("patchloop.agent.request_transport.asyncio.sleep", slow_sleep)

    def handler(request):
        seen.append(request)
        return rejection()

    client = transport(handler, events)
    try:
        with pytest.raises(RequestWaitExpired):
            client.responses.create(model="test", input=[], timeout=0.1)
        assert len(seen) == 1
    finally:
        client.close()


def test_opt_in_is_model_and_envelope_bound_default_wire_unchanged(tmp_path, monkeypatch):
    request, _, _ = _provider_smoke(monkeypatch, tmp_path)
    opted = request.model_copy(update={"rate_limit_policy": retry.POLICY})
    assert "rate_limit_policy" not in request.model_dump()
    assert opted.model_dump()["rate_limit_policy"] == retry.POLICY
    pricing = pricing_for_model(request.model)
    assert runner._model_hash(request, pricing) != runner._model_hash(opted, pricing)
    assert runner._model_hash(request, pricing) == runner._model_hash(
        request.model_copy(update={"rate_limit_policy": "none"}), pricing)


@pytest.mark.parametrize("failure", [None, "crash_after_rejection", "cleanup"])
def test_actual_runner_count_and_generation_retry_keep_logical_usage_and_close(
    tmp_path, monkeypatch, failure,
):
    request, _, _ = _provider_smoke(monkeypatch, tmp_path)
    request = request.model_copy(update={"rate_limit_policy": retry.POLICY})
    counts, generations, clients = [], [], []

    def handler(wire):
        if wire.url.path.endswith("input_tokens"):
            counts.append(wire)
            if len(counts) == 1:
                return rejection()
            return httpx.Response(200, json={
                "object": "response.input_tokens", "input_tokens": 1000,
            })
        generations.append(wire)
        if len(generations) == 1:
            return rejection()
        body = response()
        body["output"] = [{"type": "function_call", "id": "fc_stop", "call_id": "stop",
                           "name": "stop_task", "arguments": json.dumps({
                               "reason_code": "insufficient_public_evidence",
                               "summary": "Finish deterministic transport test.",
                           })}]
        return httpx.Response(200, json=body)

    def factory(*, api_key, retry_policy, record):
        client = transport(handler, [], policy=retry_policy, record=record)
        if failure == "cleanup":
            original_close = client.close

            def fail_close():
                if client.closed:
                    return
                original_close()
                raise RuntimeError("simulated cleanup failure")

            client.close = fail_close
        clients.append(client)
        return client

    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", OpenAIResponsesAdapter)
    monkeypatch.setattr(runner, "BoundedResponsesClient", factory)
    if failure == "cleanup":
        with pytest.raises(RuntimeError, match="simulated cleanup failure"):
            runner.run_dev(request)
        run_id = _enveloped_run_id(request.state_root)
        journal = DevJournal(request.state_root, run_id)
        assert journal.terminal() is None
        assert any(e["event_type"] == "provider_transport_cleanup_failed"
                   for e in journal.events())
        before = len(counts), len(generations)
        with pytest.raises(RecoveryError, match="cleanup remains uncertain"):
            runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))
        assert (len(counts), len(generations)) == before
        return
    if failure == "crash_after_rejection":
        _crash_journal_once(
            monkeypatch, event_type="provider_transport_rejected429", when="after",
            predicate=lambda p: p["request_kind"] == "provider_response",
        )
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(request)
        assert clients[0].closed
        before = len(counts), len(generations)
        run_id = _enveloped_run_id(request.state_root)
        result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
        assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
        assert (len(counts), len(generations)) == before
        return
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED"
    assert result["call_counts"]["model"] == result["call_counts"]["input_count"] == 1
    assert len(counts) == len(generations) == 2
    assert clients[0].closed
    journal = DevJournal(request.state_root, _enveloped_run_id(request.state_root))
    events = journal.events()
    assert sum(e["event_type"] == "provider_transport_rejected429" for e in events) == 2
    started = [e["payload"] for e in events if e["event_type"] == "provider_call_started"]
    finished = [e["payload"] for e in events if e["event_type"] == "provider_call_finished"]
    assert len(started) == len(finished) == 1
    assert finished[0]["cost_nanos"] > 0
    assert finished[0]["input_tokens"] == started[0]["input_tokens"] == 1000
    assert journal.load_envelope().rate_limit_policy == retry.POLICY


def test_backoff_is_exponential_and_shared_sleep_budget_is_cumulative(monkeypatch):
    seen, events, waits = [], [], []

    async def no_sleep(delay):
        waits.append(delay)

    monkeypatch.setattr("patchloop.agent.request_transport.asyncio.sleep", no_sleep)

    def handler(request):
        seen.append(request)
        return rejection(headers={"retry-after": "invalid"})

    client = transport(handler, events)
    try:
        with pytest.raises(openai.RateLimitError):
            client.responses.create(model="test", input=[], timeout=10)
        assert waits == [2, 4]
        assert len(seen) == 3
    finally:
        client.close()

    seen.clear()
    waits.clear()
    client = transport(lambda r: (seen.append(r) or rejection(
        headers={"retry-after": "70"})), events)
    try:
        with pytest.raises(openai.RateLimitError):
            client.responses.create(model="test", input=[], timeout=300)
        assert waits == [70] and len(seen) == 2
    finally:
        client.close()


def test_slow_durable_admission_does_not_send_after_deadline():
    from time import sleep

    seen = []

    def record(kind, value):
        if kind.endswith("attempt_started"):
            sleep(0.02)

    client = transport(lambda r: (seen.append(r) or rejection()), [], record=record)
    try:
        with pytest.raises(RequestWaitExpired):
            client.responses.create(model="test", input=[], timeout=0.01)
        assert seen == []
    finally:
        client.close()
