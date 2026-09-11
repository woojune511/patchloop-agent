from __future__ import annotations

import asyncio
import json
import threading
from time import monotonic
from types import SimpleNamespace

import httpx
import openai
import pytest
from test_dev_tools import read_calls
from test_fresh_state_rollout import Adapter, ledger, start
from test_fresh_state_rollout import branch as _branch

from diagnostics import episode_requests as requests
from diagnostics import fresh_state_rollout as engine
from diagnostics import model_state_episode_collector as collector
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.util import canonical_json

branch = _branch
SECRET = "SECRET_SDK_BODY_HEADER_AND_REASONING_SENTINEL"


def response(*, output=None):
    return {
        "id": "resp_mock", "object": "response", "created_at": 0,
        "status": "completed", "model": engine.shared.MODEL,
        "output": output if output is not None else [{
            "id": "rs_mock", "type": "reasoning", "encrypted_content": "cipher-mock",
            "summary": [{"type": "summary_text", "text": SECRET}],
        }],
        "usage": {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100,
                  "input_tokens_details": {"cached_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 20}},
    }


def client(handler):
    return requests.DiagnosticClient(
        api_key="", client=openai.AsyncOpenAI(
            api_key="mock-not-a-credential", max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False),
        ),
    )


def prepared(branch, adapter):
    start(branch, "observed", read_calls())
    return branch.prepare_request(SimpleNamespace(public=branch.gateway.public_task), adapter)


@pytest.mark.parametrize("kind", ["input_count", "provider_response"])
def test_whole_request_timer_cancels_trickling_body_once(kind):
    visits, cancelled, closed = [], [], []
    warmed = [False]

    class Trickle(httpx.AsyncByteStream):
        async def __aiter__(self):
            try:
                while True:
                    yield b" "
                    await asyncio.sleep(0.005)
            finally:
                cancelled.append(True)

        async def aclose(self):
            closed.append(True)

    async def handler(request):
        visits.append(request)
        if not warmed[0]:
            return httpx.Response(200, json=response() if kind == "provider_response" else {
                "input_tokens": 1000, "object": "response.input_tokens"})
        return httpx.Response(200, stream=Trickle())

    transport = client(handler)
    try:
        method = (transport.responses.create if kind == "provider_response"
                  else transport.responses.input_tokens.count)
        # Warm local SDK schema imports; only the next, trickling request is timed.
        method(model=engine.shared.MODEL, input=[], timeout=5)
        visits.clear()
        warmed[0] = True
        started = monotonic()
        with pytest.raises(requests.RequestWaitExpired):
            method(model=engine.shared.MODEL, input=[], timeout=0.1)
        assert len(visits) == 1 and cancelled and closed
        assert transport.phase == kind + "_wait" and not transport.response_received
        assert not asyncio.all_tasks(transport.runner.get_loop())
    finally:
        transport.close()
    assert monotonic() - started < 3


@pytest.mark.parametrize("remaining,expected", [(1800, (30, 300)), (9, (9, 9))])
def test_limits_are_per_request_and_clipped_by_shared_deadline(branch, remaining, expected):
    adapter = Adapter(read_calls())
    request = prepared(branch, adapter)
    now, received = [0.0], []
    branch.clock = engine.ActiveClock(lambda: now[0])
    branch.gateway.deadline = ExecutionDeadline.from_remaining(remaining, clock=branch.clock)
    original_count, original_create = adapter.count_input_tokens_v2, adapter.execute_request

    def count(request, *, timeout_seconds):
        received.append(timeout_seconds)
        return original_count(request)

    def create(request, *, timeout_seconds, **kwargs):
        received.append(timeout_seconds)
        return original_create(request, **kwargs)

    adapter.count_input_tokens_v2, adapter.execute_request = count, create
    with branch.clock.active():
        engine.dispatch(branch, adapter, ledger(), request, request_waits=requests.WAITS)
    assert received == list(expected)
    assert "SECRET" not in branch.journal.path.read_text()


def test_no_remaining_deadline_means_no_count_or_dispatch(branch):
    adapter = Adapter([])
    request = prepared(branch, adapter)
    branch.gateway.deadline = ExecutionDeadline.from_remaining(0)
    with pytest.raises(ExecutionDeadlineExceeded):
        engine.dispatch(branch, adapter, ledger(), request, request_waits=requests.WAITS)
    assert adapter.sequence == []
    assert not any(e["event_type"] == "input_count_started" for e in branch.journal.events())


@pytest.mark.parametrize("stage", ["count", "response"])
def test_late_return_preserves_known_results_without_next_action(branch, stage):
    adapter = Adapter(read_calls())
    request = prepared(branch, adapter)
    before = branch.new_tools
    now = [0.0]
    branch.clock = engine.ActiveClock(lambda: now[0])
    branch.gateway.deadline = ExecutionDeadline.from_remaining(1800, clock=branch.clock)
    name = "count_input_tokens_v2" if stage == "count" else "execute_request"
    original = getattr(adapter, name)

    def late(*args, **kwargs):
        result = original(*args, **kwargs)
        now[0] += 31 if stage == "count" else 301
        return result

    setattr(adapter, name, late)
    with branch.clock.active(), pytest.raises(engine.AbortExperiment) as error:
        engine.dispatch(branch, adapter, ledger(), request, request_waits=requests.WAITS)
    assert error.value.code == "LIMIT_REACHED"
    assert branch.new_tools == before
    events = branch.journal.events()
    assert sum(e["event_type"] == "input_count_finished" for e in events) == 1
    assert sum(e["event_type"] == "provider_call_finished" for e in events) == (stage == "response")
    if stage == "response":
        late_record = next(e["payload"] for e in events
                           if e["event_type"] == "diagnostic_response_processed")
        record = json.loads(branch.store.read_bytes(
            engine.Artifact.model_validate(late_record["decision_artifact"])))
        assert record["continuation_ref"] is not None
        assert branch.new_cost_nanos == 1200000
    assert adapter.sequence == (["count"] if stage == "count" else ["count", "create"])


@pytest.mark.parametrize("failure,phase,known", [
    ("network", "provider_response_wait", False),
    ("sdk_parse", "provider_response_processing", False),
    ("output_parse", "provider_response_processing", True),
])
def test_failure_phases_are_sanitized_and_parsed_usage_survives(branch, failure, phase, known):
    visits = []

    async def handler(request):
        visits.append(request)
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={
                "input_tokens": 1000, "object": "response.input_tokens"})
        if failure == "network":
            raise httpx.ConnectError(SECRET, request=request)
        if failure == "sdk_parse":
            return httpx.Response(200, content=SECRET.encode(),
                                  headers={"content-type": "application/json", "secret": SECRET})
        return httpx.Response(200, json=response(output=123))

    transport = client(handler)
    adapter = OpenAIResponsesAdapter(engine.shared.model_config("medium"), api_key="",
                                     client=transport)
    request = prepared(branch, adapter)
    before = branch.new_tools
    try:
        with pytest.raises(engine.AbortExperiment) as error:
            engine.dispatch(branch, adapter, ledger(), request, request_waits=requests.WAITS)
        assert len(visits) == 2 and branch.new_tools == before
        assert error.value.failure["phase"] == phase
        assert error.value.failure["response_received"] == (failure != "network")
        assert error.value.code == (
            "PROVIDER_RESPONSE_PROCESSING_ERROR" if known else "PROVIDER_TIMEOUT_OR_UNKNOWN")
        finished = [e["payload"] for e in branch.journal.events()
                    if e["event_type"] == "provider_call_finished"]
        assert bool(finished) == known
        if known:
            assert finished[0]["billing_known"] and finished[0]["cost_nanos"] == 1200000
        for path in branch.journal.root.rglob("*"):
            if path.is_file():
                assert SECRET.encode() not in path.read_bytes()
    finally:
        transport.close()


def test_client_payload_and_parser_match_default_without_plain_reasoning():
    visits = []

    async def handler(request):
        visits.append(json.loads(request.content))
        return httpx.Response(200, json=response())

    transport = client(handler)
    adapter = OpenAIResponsesAdapter(engine.shared.model_config("medium"), api_key="",
                                     client=transport)
    request = adapter.request_payload([], [], system_prompt="ignored for native items")
    try:
        turn = adapter.execute_request(request, requested_input_tokens=1000, timeout_seconds=1)
        assert visits == [request]  # Timeout belongs to transport, never wire/model input.
        assert turn.provider_continuation[0].encrypted_content == "cipher-mock"
        assert SECRET not in canonical_json(engine.loop._turn_from_openai(turn).model_dump())
    finally:
        transport.close()


def test_cleanup_is_bounded_and_leaves_no_pending_request():
    cancelled = []

    async def close():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    transport = requests.DiagnosticClient(api_key="", client=SimpleNamespace(
        max_retries=0, close=close))
    with pytest.raises(TimeoutError):
        transport.close(timeout=0.01)
    assert cancelled and transport.closed
    transport.close()  # Idempotent cleanup, never a second provider request.


def test_os_lookup_does_not_delay_cleanup_and_durable_receipt():
    release, entered = threading.Event(), threading.Event()

    def lookup():
        entered.set()
        release.wait()

    async def close():
        pass

    async def begin_lookup():
        task = asyncio.create_task(asyncio.to_thread(lookup))
        while not entered.is_set():
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    transport = requests.DiagnosticClient(api_key="", client=SimpleNamespace(
        max_retries=0, close=close))
    transport.runner.run(begin_lookup())
    # A bounded escape also makes regression failure safe on the old executor join.
    escape = threading.Timer(1, release.set)
    escape.start()
    started = monotonic()
    try:
        transport.close()
        assert monotonic() - started < 0.5
    finally:
        release.set()
        escape.cancel()
        escape.join()


def test_failure_sanitizer_never_uses_arbitrary_exception_name_or_message():
    evil = type(SECRET, (Exception,), {})(SECRET)
    assert requests.exception_evidence(evil) == {
        "category": "unexpected_error", "exception_type": "Exception"}


def test_crash_after_receipt_preserves_last_phase_without_replay(branch, monkeypatch):
    class ProcessKilled(BaseException):
        pass

    visits = []

    async def handler(request):
        visits.append(request)
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={"input_tokens": 1000})
        return httpx.Response(200, json=response())

    transport = client(handler)
    adapter = OpenAIResponsesAdapter(engine.shared.model_config("medium"), api_key="",
                                     client=transport)
    request = prepared(branch, adapter)
    append = branch.journal.append

    def crash(event, payload):
        result = append(event, payload)
        if (event == "diagnostic_response_received"
                and payload["request_kind"] == "provider_response"):
            raise ProcessKilled()
        return result

    monkeypatch.setattr(branch.journal, "append", crash)
    before = branch.new_tools
    try:
        with pytest.raises(ProcessKilled):
            engine.dispatch(branch, adapter, ledger(), request, request_waits=requests.WAITS)
        original_bytes = branch.journal.path.read_bytes()
        monkeypatch.setattr(collector, "_events", lambda *_: branch.journal.events())
        result = collector.evidence_totals(branch.journal.root, [{
            "event_type": "branch_registered", "payload": {"anonymous_id": "mock"}}])
        assert result["total_cost_known"] is False
        assert result["pending_request_phases"][0]["last_recorded_phase"] == (
            "provider_response_processing")
        assert branch.journal.path.read_bytes() == original_bytes
        assert branch.new_tools == before and len(visits) == 2
    finally:
        transport.close()
