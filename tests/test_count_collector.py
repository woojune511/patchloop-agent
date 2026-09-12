from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest
from test_count_replay import SECRET, snapshot
from test_count_replay import frozen as frozen

from diagnostics import count_collector as collector
from diagnostics import count_replay as replay
from diagnostics.episode_requests import DiagnosticClient
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture(autouse=True)
def no_live_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("live credential, network or generation forbidden")

    monkeypatch.setattr(collector, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(collector.transport, "DiagnosticClient", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    # Windows asyncio uses a local socketpair for its event loop. Block real HTTP
    # transports, not that internal pair; MockTransport never enters either path.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    monkeypatch.setattr(replay.OpenAIResponsesAdapter, "execute_request", forbidden)


@pytest.fixture
def prepared(frozen, tmp_path, monkeypatch):
    env_file = tmp_path / "fake.env"
    env_file.write_text(SECRET, encoding="utf-8")
    envelope = json.loads(frozen.journal.envelope_path.read_bytes())
    envelope["credential_file_path_hash"] = sha256_bytes(str(env_file.resolve()).encode())
    frozen.journal.envelope_path.write_text(canonical_json(envelope), encoding="utf-8")
    monkeypatch.setattr(replay, "SOURCE_HASHES", {
        **replay.SOURCE_HASHES,
        ".envelope.json": sha256_bytes(frozen.journal.envelope_path.read_bytes()),
    })
    verification = replay.prepare(frozen.root, frozen.output)
    return SimpleNamespace(
        source=frozen, kwargs={"packet_root": frozen.output,
                               "packet_hash": verification["packet_hash"],
                               "output": tmp_path / "collection", "env_file": env_file,
                               "accept_unconfirmed_count_billing": True},
    )


def success(count=replay.CONTROL_COUNT):
    return SimpleNamespace(object="response.input_tokens", input_tokens=count)


class Client:
    max_retries = 0

    def __init__(self, replies, *, cleanup_error=None):
        self.replies, self.cleanup_error = iter(replies), cleanup_error
        self.calls, self.closes = [], []
        self.responses = SimpleNamespace(input_tokens=SimpleNamespace(count=self.count))

    def count(self, **payload):
        self.calls.append(payload)
        result = next(self.replies)
        if isinstance(result, BaseException):
            raise result
        return result() if callable(result) else result

    def close(self, *, timeout):
        self.closes.append(timeout)
        if self.cleanup_error:
            raise self.cleanup_error


def run(prepared, client, **overrides):
    return collector.collect(
        **{**prepared.kwargs, **overrides}, client_factory=lambda **_: client,
        credential_loader=lambda _: "mock-only-key",
    )


def events(prepared):
    path = next((prepared.kwargs["output"] / "runs").glob("*.jsonl"))
    return DevJournal(prepared.kwargs["output"], path.stem).events()


def test_exact_two_count_bodies_and_durable_outcomes_without_other_execution(prepared):
    env_file = prepared.kwargs["env_file"]
    before = {**snapshot(prepared.source.root), **snapshot(prepared.source.output),
              str(env_file): sha256_bytes(env_file.read_bytes())}

    def reply():
        assert events(prepared)[-1]["event_type"] == "input_count_started"
        return success()

    client = Client([reply, reply])
    result = run(prepared, client)
    assert result["result"] == result["protocol_result"] == "NOT_REPRODUCED"
    assert result["generation_requests"] == result["task_executions"] == 0
    assert result["docker_operations"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert result["official"] is result["claim_eligible"] is False
    assert result["observed_cost_usd"] is None
    assert result["count_endpoint_pricing"] == "UNCONFIRMED"
    assert result["admitted_count_attempts"] == 2
    for payload, original in zip(client.calls, prepared.source.payloads, strict=True):
        assert 0 < payload["timeout"] <= 30
        assert {k: v for k, v in payload.items() if k != "timeout"} == original
        assert "max_output_tokens" not in payload
    assert len(client.closes) == 1 and 0 < client.closes[0] <= 5
    assert [e["event_type"] for e in events(prepared)] == [
        "count_collection_started", "input_count_started", "input_count_finished",
        "input_count_started", "input_count_finished", "count_client_cleanup", "terminal",
    ]
    assert events(prepared)[-1]["payload"]["result_hash"] == sha256_json(result)
    assert all(sha256_bytes(Path(p).read_bytes()) == digest for p, digest in before.items())
    for path in prepared.kwargs["output"].rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
            assert b"ciphertext" not in path.read_bytes()
    with pytest.raises(ContractError, match="new; no resume"):
        run(prepared, client)
    assert len(client.calls) == 2


@pytest.mark.parametrize("first,second,expected,attempts", [
    (success(97809), success(), "BASELINE_NOT_REPRODUCED", 1),
    (TimeoutError(SECRET), success(), "STOP_ERROR", 1),
    (KeyboardInterrupt(SECRET), success(), "STOP_ERROR", 1),
    (SystemExit(SECRET), success(), "STOP_ERROR", 1),
    (success(), TimeoutError(SECRET), "STOP_ERROR", 2),
    (success(), KeyboardInterrupt(SECRET), "STOP_ERROR", 2),
])
def test_error_interruption_and_changed_control_stop_all(
    prepared, first, second, expected, attempts,
):
    client = Client([first, second])
    result = run(prepared, client)
    assert result["result"] == expected
    assert len(client.calls) == result["admitted_count_attempts"] == attempts
    assert len(client.closes) == 1
    assert SECRET not in canonical_json(result)


@pytest.mark.parametrize("response", [success(True), success(-1), success("97810"),
                                    success(97810.0), success(None),
                                    SimpleNamespace(input_tokens=1)])
def test_malformed_count_never_unlocks_second_case(prepared, response):
    client = Client([response, success()])
    result = run(prepared, client)
    assert result["result"] == "STOP_ERROR"
    assert len(client.calls) == 1
    assert result["receipts"][0]["status"] == "failed"


@pytest.mark.parametrize("change", ["grant", "hash", "source", "runtime", "credential", "output"])
def test_preflight_fails_before_client_or_credential(prepared, monkeypatch, change):
    kw = prepared.kwargs.copy()
    if change == "grant":
        kw["accept_unconfirmed_count_billing"] = False
    elif change == "hash":
        kw["packet_hash"] = sha256_json("wrong")
    elif change == "source":
        prepared.source.journal.path.write_bytes(b"tampered")
    elif change == "runtime":
        monkeypatch.setattr(replay, "runtime_content_hash", lambda: sha256_json("changed"))
    elif change == "credential":
        kw["env_file"] = kw["env_file"].with_name("other.env")
    else:
        kw["output"] = prepared.source.output / "nested"
    with pytest.raises(ContractError):
        collector.collect(**kw)
    assert not kw["output"].exists()


def test_retrying_client_is_rejected_without_request(prepared):
    client = Client([success()])
    client.max_retries = 2
    result = run(prepared, client)
    assert result["result"] == "STOP_ERROR" and result["failure"]["phase"] == "client_setup"
    assert not client.calls and len(client.closes) == 1


@pytest.mark.parametrize("elapsed,attempts,expected", [(31, 2, "NOT_REPRODUCED"),
                                                     (60, 1, "STOP_ERROR"),
                                                     (66, 1, "STOP_ERROR")])
def test_shared_deadline_clips_second_request_and_preserves_late_result(
    prepared, elapsed, attempts, expected,
):
    now = [0.0]

    def first():
        now[0] += elapsed
        return success()

    client = Client([first, success()])
    result = run(prepared, client, clock=lambda: now[0])
    assert len(client.calls) == attempts and result["result"] == expected
    assert result["receipts"][0]["status"] == "succeeded"
    if attempts == 2:
        assert client.calls[1]["timeout"] == 29
    else:
        assert result["failure"]["category"] == "execution_deadline"
    assert client.closes == [min(5, max(0, 65 - elapsed))]


def test_admission_io_is_inside_deadline(prepared, monkeypatch):
    now = [0.0]
    append = DevJournal.append

    def delayed(self, kind, payload):
        result = append(self, kind, payload)
        if kind == "input_count_started":
            now[0] = 61
        return result

    monkeypatch.setattr(DevJournal, "append", delayed)
    client = Client([success()])
    result = run(prepared, client, clock=lambda: now[0])
    assert not client.calls and result["admitted_count_attempts"] == 1
    assert result["failure"]["category"] == "execution_deadline"


def test_cleanup_failure_retains_counts_but_never_reports_clean_completion(prepared):
    client = Client([success(), success()], cleanup_error=TimeoutError(SECRET))
    result = run(prepared, client)
    assert result["result"] == "STOP_CLEANUP_UNKNOWN"
    assert result["protocol_result"] == "NOT_REPRODUCED"
    assert result["cleanup"]["status"] == "UNKNOWN"
    assert SECRET not in canonical_json(result)
    assert len(client.calls) == 2 and len(client.closes) == 1


class Crash(BaseException):
    pass


@pytest.mark.parametrize("point", ["input_count_started", "input_count_finished"])
def test_crash_after_durable_event_never_retries_same_invocation(prepared, monkeypatch, point):
    append = DevJournal.append

    def crash(self, kind, payload):
        result = append(self, kind, payload)
        if kind == point:
            raise Crash()
        return result

    client = Client([success(), success()])
    with monkeypatch.context() as patch:
        patch.setattr(DevJournal, "append", crash)
        with pytest.raises(Crash):
            run(prepared, client)
    calls = len(client.calls)
    assert calls == (point == "input_count_finished")
    assert any(e["event_type"] == point for e in events(prepared))
    with pytest.raises(ContractError, match="no resume"):
        collector.collect(**prepared.kwargs)
    assert len(client.calls) == calls


def test_sdk_wire_request_and_allowlisted_http_error_without_retry_or_message(prepared):
    visited = []

    async def handler(request):
        visited.append(request)
        assert request.url == replay.PROTOCOL["endpoint"] and request.method == "POST"
        body = json.loads(request.content)
        assert body == prepared.source.payloads[len(visited) - 1]
        if len(visited) == 1:
            return httpx.Response(200, json={"input_tokens": 97810,
                                             "object": "response.input_tokens"})
        return httpx.Response(400, headers={"x-request-id": "req_" + "a" * 32}, json={"error": {
            "message": SECRET, "code": "invalid_encrypted_content",
            "type": "invalid_request_error", "param": "input[78].encrypted_content",
        }})

    client = DiagnosticClient(api_key="", client=openai.AsyncOpenAI(
        api_key="mock-only-key", max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False),
    ))
    result = run(prepared, client)
    assert len(visited) == 2 and result["result"] == "STOP_ERROR"
    error = result["receipts"][1]["error"]
    assert error["http_status"] == 400 and error["code"] == "invalid_encrypted_content"
    assert error["param"] == "input[78].encrypted_content"
    assert error["request_id"] == "req_" + "a" * 32
    assert error["observed_request_body_bytes"] == len(visited[1].content)
    assert error["observed_request_body_hash"] == sha256_bytes(visited[1].content)
    assert SECRET not in canonical_json(result) and "ciphertext" not in canonical_json(result)
    assert client.closed


@pytest.mark.parametrize("status", [429, 500])
def test_retryable_http_status_still_has_one_sdk_attempt(prepared, status):
    visited = []

    async def handler(request):
        visited.append(request)
        return httpx.Response(status, json={"error": {"message": SECRET}})

    client = DiagnosticClient(api_key="", client=openai.AsyncOpenAI(
        api_key="mock-only-key", max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False),
    ))
    result = run(prepared, client)
    assert len(visited) == 1 and result["result"] == "STOP_ERROR"
    assert result["receipts"][0]["error"]["http_status"] == status


def test_outer_count_wait_cancels_before_second_case(prepared, monkeypatch):
    # Keep the immutable protocol intact; shorten only the injected transport's
    # real asyncio wait. Existing transport tests also cover trickling bodies.
    visited, cancelled = [], []

    async def handler(request):
        visited.append(request)
        try:
            await asyncio.sleep(30)
        finally:
            cancelled.append(True)

    client = DiagnosticClient(api_key="", client=openai.AsyncOpenAI(
        api_key="mock-only-key", max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False),
    ))
    count = client.responses.input_tokens.count
    monkeypatch.setattr(client.responses.input_tokens, "count",
                        lambda **kw: count(**{**kw, "timeout": 0.1}))
    result = run(prepared, client)
    assert len(visited) == 1 and cancelled and client.closed
    assert result["result"] == "STOP_ERROR"
    assert result["receipts"][0]["error"]["category"] == "timeout"


def test_cli_never_prints_exception_or_traceback(prepared, monkeypatch, capsys):
    def secret_failure(**kwargs):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(collector, "collect", secret_failure)
    monkeypatch.setattr("sys.argv", ["count_collector", "--packet-root", "unused",
                                   "--packet-hash", "unused", "--output", "unused",
                                   "--env-file", "unused"])
    with pytest.raises(SystemExit) as error:
        collector.main()
    captured = capsys.readouterr()
    assert error.value.code == 2 and not captured.err
    assert SECRET not in captured.out and "Traceback" not in captured.out
