from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest
from openai.types.responses import Response
from test_compaction_collector import Client as CompactClient
from test_compaction_collector import prepared as _compact_prepared
from test_compaction_collector import run as run_compact
from test_count_replay import SECRET, snapshot
from test_count_replay import frozen as frozen

from diagnostics import compaction_followup as followup
from diagnostics.episode_requests import DiagnosticClient
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

PLAIN = "PLAINTEXT_REASONING_MUST_NEVER_BE_PERSISTED"
compact_prepared = _compact_prepared


@pytest.fixture(autouse=True)
def no_live_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no real credential, HTTP or tool execution")

    monkeypatch.setattr(followup, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(followup.transport, "DiagnosticClient", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture
def ready(compact_prepared, tmp_path):
    run_compact(compact_prepared, CompactClient())
    root = compact_prepared.kwargs["output"]
    kwargs = dict(collection_root=root,
                  result_hash=sha256_bytes((root / "result.json").read_bytes()),
                  output=tmp_path / "followup", env_file=compact_prepared.kwargs["env_file"],
                  max_generation_cost_usd=Decimal("1.20"), repeat=1)
    return SimpleNamespace(kwargs=kwargs, inspection=followup.inspect(**kwargs))


def reply(*, calls=True, incomplete=False):
    output = [{"id": "rs_next", "type": "reasoning", "encrypted_content": "cipher-next",
               "summary": [{"type": "summary_text", "text": PLAIN}]}]
    if calls:
        output.append({"id": "fc_next", "type": "function_call", "name": "stop_task",
                       "call_id": "call_next", "status": "completed", "arguments": canonical_json({
                           "turn_decision": {"mode": "stop", "basis": "public fixture"},
                           "reason_code": "insufficient_public_evidence", "summary": "fixture stop",
                       })})
    return Response.model_validate({
        "id": "resp_next", "object": "response", "created_at": 0,
        "status": "incomplete" if incomplete else "completed", "model": followup.prices.MODEL,
        "incomplete_details": {"reason": "max_output_tokens"} if incomplete else None,
        "output": output, "parallel_tool_calls": True, "tool_choice": "required", "tools": [],
        "usage": {"input_tokens": 1000, "output_tokens": 25_000 if incomplete else 100,
                  "total_tokens": 26_000 if incomplete else 1100,
                  "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 25_000 if incomplete else 20}},
    })


class Client:
    max_retries = 0

    def __init__(self, response=None, count=1000, close_error=None):
        self.reply = response if response is not None else reply()
        self.count, self.close_error = count, close_error
        self.calls, self.closes = [], []
        self.responses = SimpleNamespace(
            input_tokens=SimpleNamespace(count=self.input_count), create=self.create)

    def input_count(self, **payload):
        self.calls.append(("count", payload))
        if isinstance(self.count, BaseException):
            raise self.count
        return SimpleNamespace(object="response.input_tokens", input_tokens=self.count)

    def create(self, **payload):
        self.calls.append(("create", payload))
        if isinstance(self.reply, BaseException):
            raise self.reply
        return self.reply

    def close(self, *, timeout):
        self.closes.append(timeout)
        if self.close_error:
            raise self.close_error


def collect(ready, client=None, **kwargs):
    return followup.collect(**ready.kwargs,
                            execution_plan_hash=ready.inspection["execution_plan_hash"],
                            accept_unconfirmed_count_billing=True,
                            client_factory=lambda **_: client or Client(),
                            credential_loader=lambda _: "fake-key", **kwargs)


def test_inspect_preserves_source_and_freezes_unchanged_request(ready):
    old = snapshot(ready.kwargs["collection_root"])
    assert followup.inspect(**ready.kwargs) == ready.inspection
    assert followup.inspect(**{**ready.kwargs, "max_generation_cost_usd": Decimal("1.2")}) == (
        ready.inspection)
    assert snapshot(ready.kwargs["collection_root"]) == old
    assert not ready.kwargs["output"].exists()
    plan = ready.inspection["plan"]
    assert plan["reservation"]["reserved_generation_nanos"] == 316_500_000
    assert plan["maximum_count_requests"] == plan["maximum_generation_requests"] == 1
    assert plan["compaction_requests"] == plan["tool_executions"] == 0
    assert "UNCONFIRMED" in plan["count_billing"] and plan["total_invoice_cost_usd"] is None


@pytest.mark.parametrize("change", [{"result_hash": "sha256:wrong"}, {"repeat": 2},
                                  {"max_generation_cost_usd": Decimal("0.316499")},
                                  {"max_generation_cost_usd": Decimal("NaN")}])
def test_invalid_plan_rejected_without_credentials(ready, change):
    with pytest.raises(ContractError):
        followup.inspect(**{**ready.kwargs, **change})
    assert not ready.kwargs["output"].exists()


def test_unapproved_or_changed_hash_cannot_create_output(ready):
    with pytest.raises(ContractError, match="acknowledge"):
        followup.collect(**ready.kwargs,
                         execution_plan_hash=ready.inspection["execution_plan_hash"])
    with pytest.raises(ContractError, match="plan mismatch"):
        followup.collect(**ready.kwargs, execution_plan_hash="wrong",
                         accept_unconfirmed_count_billing=True)
    assert not ready.kwargs["output"].exists()


def test_one_count_one_response_no_execution_and_no_plain_reasoning(ready):
    client = Client()
    result = collect(ready, client)
    assert result["result"] == "RESPONSE_COLLECTED"
    assert [k for k, _ in client.calls] == ["count", "create"]
    assert result["assessment"]["tool_batch_contract"] == "PASS_SHAPE_ONLY"
    assert result["assessment"]["tool_names"] == ["stop_task"]
    assert result["assessment"]["encrypted_item_count"] == 1
    assert result["generation_model_rate_cost_nanos"] == 1_200_000
    assert result["total_invoice_cost_usd"] is None and result["tool_executions"] == 0
    generation = dict(client.calls[1][1])
    generation.pop("timeout")
    assert sha256_json(generation) == ready.inspection["plan"]["source"]["request_hash"]
    assert json.dumps(generation, ensure_ascii=False, separators=(",", ":")) == (
        canonical_json(generation))
    assert generation["max_output_tokens"] == 25_000 and generation["store"] is False
    for path in ready.kwargs["output"].rglob('*'):
        if path.is_file():
            assert PLAIN.encode() not in path.read_bytes()
            assert SECRET.encode() not in path.read_bytes()
    before = snapshot(ready.kwargs["output"])
    assert followup.inspect_result(ready.kwargs["output"]) == result
    assert followup.inspect_result(ready.kwargs["output"]) == result
    assert snapshot(ready.kwargs["output"]) == before
    with pytest.raises(ContractError, match="new"):
        collect(ready)


@pytest.mark.parametrize("count", [True, 0, 272001, RuntimeError(PLAIN)])
def test_invalid_count_stops_before_generation(ready, count):
    client = Client(count=count)
    result = collect(ready, client)
    assert result["result"] == "STOP_ERROR"
    assert [k for k, _ in client.calls] == ["count"]
    assert result["generation_attempts"] == 0 and len(client.closes) == 1
    assert PLAIN not in canonical_json(result)


def test_reasoning_only_incomplete_is_evidence_not_success_or_correction(ready):
    result = collect(ready, Client(reply(calls=False, incomplete=True)))
    assert result["result"] == "RESPONSE_COLLECTED"
    assert result["assessment"]["error_code"] == "incomplete_response"
    assert result["assessment"]["tool_batch_contract"] == "FAIL"
    assert result["assessment"]["tool_names"] == []
    assert result["assessment"]["encrypted_item_count"] == 1
    assert result["correction_requests"] == 0 and result["generation_attempts"] == 1


@pytest.mark.parametrize("bad", ["missing_cipher", "bad_json", "wrong_tool"])
def test_bad_continuation_or_tool_is_not_valid_action(ready, bad):
    response = reply()
    if bad == "missing_cipher":
        response.output[0].encrypted_content = None
    elif bad == "bad_json":
        response.output[1].arguments = "{" + PLAIN
    else:
        response.output[1].name = "unregistered_shell"
    result = collect(ready, Client(response))
    assert result["assessment"]["tool_batch_contract"] == "FAIL"
    assert result["generation_model_rate_cost_nanos"] == 1_200_000
    assert result["tool_executions"] == 0


@pytest.mark.parametrize("fault", ["count_recorded", "generation_dispatch_recorded",
                                 "usage_recorded", "assessment_recorded"])
def test_interruption_never_replays_requests(ready, fault):
    client = Client()

    def crash(label):
        if label == fault:
            raise KeyboardInterrupt()

    result = collect(ready, client, checkpoint=crash)
    assert result["result"] == "STOP_ERROR" and len(client.calls) <= 2
    count = len(client.calls)
    assert followup.inspect_result(ready.kwargs["output"]) == result
    assert len(client.calls) == count
    if fault in {"usage_recorded", "assessment_recorded"}:
        assert result["usage"]["input_tokens"] == 1000


def test_timeout_and_unknown_cleanup_preserve_usage_without_retry(ready):
    result = collect(ready, Client(close_error=TimeoutError(PLAIN)))
    assert result["result"] == "STOP_CLEANUP_UNKNOWN"
    assert result["usage"]["input_tokens"] == 1000
    assert result["generation_attempts"] == 1 and PLAIN not in canonical_json(result)


def test_count_uses_active_deadline_then_prevents_late_generation(ready):
    now, client = [0.0], Client()

    def advance(label):
        if label == "count_recorded":
            now[0] = 334.0

    result = collect(ready, client, clock=lambda: now[0], checkpoint=advance)
    assert result["result"] == "STOP_ERROR" and result["generation_attempts"] == 0
    assert client.calls[0][1]["timeout"] == 30
    assert client.closes == [1.0]


def test_hard_publication_failure_inspection_reads_durable_evidence(ready, monkeypatch):
    def crash(*_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(followup, "_publish", crash)
    with pytest.raises(KeyboardInterrupt):
        collect(ready)
    before = snapshot(ready.kwargs["output"])
    result = followup.inspect_result(ready.kwargs["output"])
    assert result["result"] == "INTERRUPTED_NO_RETRY"
    assert result["admitted_counts"] == result["admitted_generations"] == 1
    assert result["generation_attempts"] is None
    assert result["durable_usage"][0]["usage"]["input_tokens"] == 1000
    assert snapshot(ready.kwargs["output"]) == before


def test_source_artifact_tamper_is_rejected(ready):
    root = ready.kwargs["collection_root"] / "compact"
    receipt = json.loads((root / "receipt.json").read_bytes())
    path = Path(receipt["next_request_artifact"]["path"])
    path.write_bytes(b"changed")
    with pytest.raises(ContractError):
        followup.inspect(**ready.kwargs)


def test_real_sdk_mock_transport_hits_only_count_then_create(ready):
    paths = []
    response = reply()

    async def handler(request):
        paths.append(request.url.path)
        data = json.loads(request.content)
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={"object": "response.input_tokens",
                                            "input_tokens": 1000})
        assert sha256_json(data) == ready.inspection["plan"]["source"]["request_hash"]
        return httpx.Response(200, json=response.model_dump(mode="json"))

    client = DiagnosticClient(api_key="mock", client=openai.AsyncOpenAI(
        api_key="mock", max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    result = collect(ready, client)
    assert result["result"] == "RESPONSE_COLLECTED"
    assert paths == ["/v1/responses/input_tokens", "/v1/responses"]


def test_generation_count_mismatch_keeps_reported_usage(ready):
    response = copy.deepcopy(reply())
    response.usage.input_tokens = 1001
    response.usage.total_tokens = 1101
    result = collect(ready, Client(response))
    assert result["result"] == "STOP_ERROR"
    assert result["usage"]["input_tokens"] == 1001
    assert result["generation_model_rate_cost_nanos"] is None
    assert result["assessment"] is None
