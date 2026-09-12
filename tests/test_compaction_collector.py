from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest
from test_compaction_diagnostic import response
from test_count_replay import SECRET, snapshot
from test_count_replay import frozen as frozen

from diagnostics import compaction_collector as collector
from diagnostics import compaction_cost as cost
from diagnostics import compaction_replay as design
from diagnostics import compaction_state as state
from diagnostics import count_replay as source
from diagnostics.episode_requests import DiagnosticClient
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json


@pytest.fixture(autouse=True)
def no_live_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("real credential/client/network/tool use forbidden")

    monkeypatch.setattr(collector, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(collector.transport, "DiagnosticClient", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture
def prepared(frozen, tmp_path, monkeypatch):
    env = tmp_path / "fake.env"
    env.write_text(SECRET, encoding="utf-8")
    envelope = json.loads(frozen.journal.envelope_path.read_bytes())
    envelope["credential_file_path_hash"] = sha256_bytes(str(env.resolve()).encode())
    frozen.journal.envelope_path.write_text(canonical_json(envelope), encoding="utf-8")
    monkeypatch.setattr(source, "SOURCE_HASHES", {
        **source.SOURCE_HASHES,
        ".envelope.json": sha256_bytes(frozen.journal.envelope_path.read_bytes()),
    })
    packet = design.prepare(frozen.root, frozen.output)
    kwargs = {"packet_root": frozen.output, "packet_hash": packet["packet_hash"],
              "env_file": env, "output": tmp_path / "collected",
              "max_cost_usd": Decimal("1.20"), "repeat": 1}
    inspection = collector.inspect(**kwargs)
    return SimpleNamespace(source=frozen, kwargs=kwargs, inspection=inspection)


class Client:
    max_retries = 0

    def __init__(self, reply=None, close_error=None):
        self.reply = response() if reply is None else reply
        self.close_error = close_error
        self.calls, self.closes = [], []
        self.responses = SimpleNamespace(compact=self.compact)

    def compact(self, **request):
        self.calls.append(request)
        if isinstance(self.reply, BaseException):
            raise self.reply
        return self.reply() if callable(self.reply) else self.reply

    def close(self, *, timeout):
        self.closes.append(timeout)
        if self.close_error:
            raise self.close_error


def run(prepared, client, **changes):
    return collector.collect(
        **{**prepared.kwargs, "execution_plan_hash": prepared.inspection["execution_plan_hash"],
           "accept_model_limit_reservation": True, **changes},
        client_factory=lambda **_: client, credential_loader=lambda _: "mock-only-key",
    )


def journal(prepared):
    root = prepared.kwargs["output"]
    binding = json.loads((root / "execution.json").read_bytes())
    return DevJournal(root, binding["run_id"])


def test_cost_full_limit_reservation_not_25k_or_historical_input_count():
    quote = cost.reserve(Decimal("0.876"))
    assert quote["reserved_cost_nanos"] == 876_000_000
    assert quote["endpoint_enforced_dollar_cap"] is False
    assert cost.CONTRACT["reserved_output_tokens"] == 128_000
    assert cost.CONTRACT["reserved_input_tokens"] == 400_000
    with pytest.raises(ContractError, match="full model-limit"):
        cost.reserve(Decimal("0.875999999"))


@pytest.mark.parametrize("cap", ["0", "-1", "NaN", "Infinity"])
def test_invalid_cap_is_rejected(cap):
    with pytest.raises(ContractError):
        cost.reserve(Decimal(cap))


def test_usage_charged_once_with_cache_discount_not_reasoning_double_count():
    # 990 uncached*750 + 10 cached*75 + 40 output*4500 = 923250 nanos.
    counted = cost.account(response()["usage"], Decimal("1.20"))
    assert counted["model_rate_cost_nanos"] == 923250
    assert counted["status"] == "ACCOUNTED_AT_MODEL_RATES"
    assert counted["invoice_cost_usd"] is None


def test_usage_boundary_and_unknown_write_pricing():
    usage = response()["usage"]
    usage.update(input_tokens=400_000, output_tokens=128_000, total_tokens=528_000)
    usage["input_tokens_details"]["cached_tokens"] = 0
    assert cost.account(usage, Decimal("0.876"))["model_rate_cost_nanos"] == 876_000_000
    usage.update(output_tokens=128_001, total_tokens=528_001)
    assert cost.account(usage, Decimal("1.20"))["status"] == "RESERVATION_EXCEEDED"
    usage["input_tokens_details"]["cache_write_tokens"] = 1
    assert cost.account(usage, Decimal("1.20"))["status"] == "BILLING_UNKNOWN"


def test_inspection_and_success_one_compaction_no_other_requests(prepared):
    before = {**snapshot(prepared.source.root), **snapshot(prepared.source.output)}
    assert collector.inspect(**prepared.kwargs) == prepared.inspection
    assert collector.inspect(**{**prepared.kwargs, "max_cost_usd": Decimal("1.2")}) == (
        prepared.inspection
    )
    assert prepared.inspection["api_requests"] == 0
    assert not prepared.kwargs["output"].exists()

    def reply():
        assert journal(prepared).events()[-1]["event_type"] == "compaction_dispatch_started"
        return response()

    client = Client(reply)
    result = run(prepared, client)
    assert result["result"] == "COMPACTION_COMPLETE"
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert result["provider_request_attempts"] == len(client.calls) == len(client.closes) == 1
    assert result["admitted_compaction_attempts"] == 1
    assert result["count_requests"] == result["generation_requests"] == 0
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert result["official"] is False
    call, = client.calls
    assert set(call) == {"model", "input", "service_tier", "timeout"}
    assert 0 < call["timeout"] <= 300 and 0 < client.closes[0] <= 5
    assert "max_output_tokens" not in call and "reasoning" not in call
    assert all(sha256_bytes(Path(p).read_bytes()) == h for p, h in before.items())
    after = snapshot(prepared.kwargs["output"])
    assert collector.recover(prepared.kwargs["output"]) == result
    assert collector.recover(prepared.kwargs["output"]) == result
    assert snapshot(prepared.kwargs["output"]) == after
    for path in prepared.kwargs["output"].rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
    with pytest.raises(ContractError, match="new"):
        run(prepared, client)
    assert len(client.calls) == 1


@pytest.mark.parametrize("change", ["ack", "plan", "cap", "cap_change", "repeat", "packet",
                                    "env", "runtime"])
def test_rejection_precedes_credential_and_client(prepared, monkeypatch, change):
    args = {**prepared.kwargs, "execution_plan_hash": prepared.inspection["execution_plan_hash"],
            "accept_model_limit_reservation": True}
    if change == "ack":
        args["accept_model_limit_reservation"] = False
    elif change == "plan":
        args["execution_plan_hash"] = sha256_json("changed")
    elif change == "cap":
        args["max_cost_usd"] = Decimal("0.10")
    elif change == "cap_change":
        args["max_cost_usd"] = Decimal("2.00")
    elif change == "repeat":
        args["repeat"] = 2
    elif change == "packet":
        args["packet_hash"] = sha256_json("changed")
    elif change == "env":
        args["env_file"] = prepared.source.root / "not-the-env"
    else:
        monkeypatch.setattr(design, "runtime_content_hash", lambda: sha256_json("changed"))
    with pytest.raises(ContractError):
        collector.collect(**args)
    assert not prepared.kwargs["output"].exists()


@pytest.mark.parametrize("error", [TimeoutError(SECRET), KeyboardInterrupt(SECRET),
                                  RuntimeError(SECRET)])
def test_request_error_never_retries_or_discloses_body(prepared, error):
    client = Client(error)
    result = run(prepared, client)
    assert result["result"] == "STOP_ERROR"
    assert result["accounting"]["status"] == "BILLING_UNKNOWN"
    assert result["accounting"]["model_rate_cost_nanos"] is None
    assert SECRET not in canonical_json(result)
    assert collector.recover(prepared.kwargs["output"]) == result
    assert len(client.calls) == len(client.closes) == 1


def test_invalid_output_retains_usage_without_reasoning_plaintext(prepared):
    bad = response()
    bad["output"].append({"type": "reasoning", "id": "rs_bad", "encrypted_content": "opaque",
                          "summary": [{"type": "summary_text", "text": SECRET}]})
    result = run(prepared, Client(bad))
    assert result["result"] == "STOP_RESPONSE_CONTRACT"
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert "window_artifact" not in result["compact_receipt"]
    for path in prepared.kwargs["output"].rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()


def test_cleanup_failure_preserves_output_and_stops(prepared):
    result = run(prepared, Client(close_error=TimeoutError(SECRET)))
    assert result["result"] == "STOP_CLEANUP_UNKNOWN"
    assert result["compact_receipt"]["status"] == "READY_FOR_REVIEW"
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert result["generation_requests"] == 0


def test_deadline_during_setup_prevents_dispatch(prepared):
    now = [0.0]

    def load_key(_):
        now[0] = 303
        return "fake"

    client = Client()
    result = collector.collect(
        **prepared.kwargs, execution_plan_hash=prepared.inspection["execution_plan_hash"],
        accept_model_limit_reservation=True, client_factory=lambda **_: client,
        credential_loader=load_key, clock=lambda: now[0],
    )
    assert not client.calls
    assert client.closes == [2]
    assert result["result"] == "STOP_ERROR"


def test_crash_after_response_receipt_preserves_usage(prepared, monkeypatch):
    original = state.record_response

    def crash(root, reply):
        original(root, reply)
        raise KeyboardInterrupt()

    monkeypatch.setattr(state, "record_response", crash)
    client = Client()
    result = run(prepared, client)
    assert result["result"] == "STOP_ERROR"
    assert result["compact_receipt"]["status"] == "READY_FOR_REVIEW"
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert len(client.calls) == 1


def test_crash_before_receipt_keeps_durable_usage_and_no_retry(prepared, monkeypatch):
    def crash(*_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(state, "record_response", crash)
    client = Client()
    result = run(prepared, client)
    assert result["compact_receipt"] is None
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert collector.recover(prepared.kwargs["output"]) == result
    assert len(client.calls) == 1


def test_interrupted_publication_is_recovered_readonly_no_provider(prepared, monkeypatch):
    def crash(*_):
        raise KeyboardInterrupt()

    client = Client()
    with monkeypatch.context() as patch:
        patch.setattr(collector, "_publish", crash)
        with pytest.raises(KeyboardInterrupt):
            run(prepared, client)
    result = collector.recover(prepared.kwargs["output"])
    assert result["compact_receipt"]["status"] == "READY_FOR_REVIEW"
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    after = snapshot(prepared.kwargs["output"])
    assert collector.recover(prepared.kwargs["output"]) == result
    assert snapshot(prepared.kwargs["output"]) == after
    assert len(client.calls) == 1


def test_active_collection_cannot_be_recovered(prepared):
    run(prepared, Client())
    with (journal(prepared).execution_lock(),
          pytest.raises(RecoveryError, match="already active")):
        collector.recover(prepared.kwargs["output"])


def test_crash_after_dispatch_intent_does_not_prove_http_or_allow_retry(prepared, monkeypatch):
    class PowerLoss(BaseException):
        pass

    original = DevJournal.append

    def crash(self, event, payload=None):
        result = original(self, event, payload)
        if event == "compaction_dispatch_started":
            raise PowerLoss()
        return result

    client = Client()
    with monkeypatch.context() as patch:
        patch.setattr(DevJournal, "append", crash)
        with pytest.raises(PowerLoss):
            run(prepared, client)
    assert client.calls == []
    result = collector.recover(prepared.kwargs["output"])
    assert result["provider_request_attempts"] is None
    assert result["admitted_compaction_attempts"] == 1
    assert result["accounting"]["status"] == "BILLING_UNKNOWN"
    assert collector.recover(prepared.kwargs["output"]) == result
    assert client.calls == []


def test_missing_derived_result_is_restored_from_terminal(prepared):
    result = run(prepared, Client())
    (prepared.kwargs["output"] / "result.json").unlink()
    assert collector.recover(prepared.kwargs["output"]) == result
    assert json.loads((prepared.kwargs["output"] / "result.json").read_bytes()) == result


def test_reported_reservation_violation_stops_and_is_not_a_task_failure(prepared):
    replied = response()
    replied["usage"].update(output_tokens=128_001, total_tokens=129_001)
    result = run(prepared, Client(replied))
    assert result["result"] == "STOP_RESERVATION_EXCEEDED"
    assert result["accounting"]["within_model_limit_reservation"] is False
    assert result["compact_receipt"]["status"] == "READY_FOR_REVIEW"
    assert result["task_acceptance"] == "NOT_RUN"


def test_sdk_mock_only_compact_endpoint_is_reachable(prepared):
    visits = []

    async def handler(request):
        visits.append(request)
        assert request.url.path == "/v1/responses/compact"
        return httpx.Response(200, json=response())

    client = DiagnosticClient(api_key="", client=openai.AsyncOpenAI(
        api_key="mock-key", max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False),
    ))
    result = run(prepared, client)
    assert result["result"] == "COMPACTION_COMPLETE"
    assert len(visits) == 1
