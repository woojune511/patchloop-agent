from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest

from diagnostics import oversized_compaction as diagnostic
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.request_transport import BoundedResponsesClient
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import assemble_model_input, history_metadata
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

SECRET = "PRIVATE_HIDDEN_REFERENCE_PLAINTEXT_REASONING_CREDENTIAL_SENTINEL"


@pytest.fixture(autouse=True)
def no_live_io(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("real credential, client, count, generation or HTTP use forbidden")

    monkeypatch.setattr(diagnostic, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(diagnostic, "BoundedResponsesClient", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "execute_request", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "count_input_tokens_v2", forbidden)


def snapshot(root):
    return {str(p): sha256_bytes(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def prepared(tmp_path):
    source = tmp_path / "source"
    env = tmp_path / "fake.env"
    env.write_text(SECRET, encoding="utf-8")
    journal = DevJournal(source, "run_dev_fixture")
    native = [
        {"type": "function_call", "call_id": "call_1", "name": "read_file", "arguments": "{}"},
        {"type": "function_call", "call_id": "call_2", "name": "read_file", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": "observed public source"},
        {"type": "function_call_output", "call_id": "call_2", "output": "public check result"},
        {"type": "reasoning", "id": "rs_large", "summary": [], "status": "incomplete",
         "encrypted_content": "opaque-" * 100},
    ]
    items = assemble_model_input(system_prompt="PUBLIC_SYSTEM", state={
        "public_task": {"goal": "PUBLIC_ULTIMATE_GOAL"}, "current_diff": "PUBLIC_DIFF",
        "protocol_correction": "Choose one allowed action.",
    }, history=native)
    ref = ArtifactStore(source / "artifacts").put_text(canonical_json(items), "application/json")
    journal.append("turn_started", {"turn_id": "turn_correction",
                   "model_input_artifact": ref.model_dump(mode="json"),
                   "model_input_hash": ref.content_hash, "native_history": history_metadata(items)})
    journal.append("unrelated_future_evidence", {"private": SECRET})
    journal.append("terminal", {"terminal": "COUNT_TIMEOUT_OR_UNKNOWN"})
    envelope = {"task_id": "public-fixture", "task_version": 2,
                "runtime_hash": sha256_json("different historical runtime"),
                "model": diagnostic.cost.MODEL,
                "credential_file_path_hash": sha256_bytes(str(env.resolve()).encode()),
                "private_path": SECRET}
    journal.envelope_path.write_text(canonical_json(envelope), encoding="utf-8")
    request = {"model": diagnostic.cost.MODEL, "input": items, "service_tier": "default"}
    proposal = {
        "schema": diagnostic.PROPOSAL_SCHEMA,
        "source": {"run_id": journal.run_id, "journal_path": str(journal.path),
                   "journal_hash": sha256_bytes(journal.path.read_bytes()),
                   "turn_id": "turn_correction", "input_artifact_hash": ref.content_hash,
                   "input_artifact_path": ref.path, "input_artifact_bytes": ref.size_bytes,
                   **{k: envelope[k] for k in ("task_id", "task_version", "runtime_hash")}},
        "proposed_request": {"model": request["model"], "service_tier": "default",
                             "endpoint": diagnostic.cost.CONTRACT["endpoint"],
                             "canonical_hash": sha256_json(request),
                             "canonical_utf8_bytes": len(canonical_json(request).encode()),
                             "credential_file_if_authorized": str(env)},
    }
    path = tmp_path / "proposal" / "proposal.json"
    path.parent.mkdir()
    path.write_text(canonical_json(proposal), encoding="utf-8")
    kwargs = {"proposal": path, "proposal_hash": sha256_json(proposal),
              "root": tmp_path / "packet", "env_file": env,
              "max_cost_usd": Decimal("1.20"), "repeat": 1,
              "pricing_verified_on": utc_now().date().isoformat()}
    before = snapshot(source)
    receipt = diagnostic.prepare(**kwargs)
    assert before == snapshot(source)
    return SimpleNamespace(root=kwargs["root"], packet_hash=receipt["packet_hash"],
                           kwargs=kwargs, receipt=receipt, source=source, journal=journal,
                           proposal=proposal, request=request, items=items)


def response(*retained):
    return {"id": "resp_fixture", "object": "response.compaction",
            "output": [*copy.deepcopy(retained), {"type": "compaction", "id": "cmp_new",
                                                 "encrypted_content": "opaque-new-window"}],
            "usage": {"input_tokens": 1000, "output_tokens": 40, "total_tokens": 1040,
                      "input_tokens_details": {"cached_tokens": 10},
                      "output_tokens_details": {"reasoning_tokens": 20}}}


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


def run(prepared, client, **kwargs):
    return diagnostic.collect(prepared.root, prepared.packet_hash,
                              **{"accept_model_limit_reservation": True,
                                 "credential_loader": lambda _: "mock-key",
                                 "client_factory": lambda **_: client, **kwargs})


def execution_journal(prepared):
    return DevJournal(prepared.root / "execution", diagnostic.RUN_ID)


def check_no_plaintext(root):
    for path in root.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()


def test_prepare_inspect_exact_input_no_credentials_or_source_writes(prepared):
    before = snapshot(prepared.source)
    first = diagnostic.inspect(prepared.root, prepared.packet_hash)
    assert first == prepared.receipt == diagnostic.inspect(prepared.root, prepared.packet_hash)
    packet, request = diagnostic._load(prepared.root, prepared.packet_hash)
    assert request == prepared.request
    assert packet["request_metrics"]["largest_encrypted_chars"] == 700
    assert packet["source_fits_model_context"] == "UNVERIFIED"
    assert packet["reservation"]["reserved_cost_nanos"] == 876_000_000
    assert packet["reservation"]["endpoint_enforced_dollar_cap"] is False
    assert first["api_requests"] == first["credentials_loaded"] == 0
    assert not first["execution_granted"] and not (prepared.root / "execution").exists()
    assert not list(prepared.root.rglob("*.jsonl"))
    assert before == snapshot(prepared.source)
    check_no_plaintext(prepared.root)
    assert "opaque-" not in (prepared.root / "packet.json").read_text()


def test_entire_window_preserved_once_and_readonly_recovery(prepared):
    before = snapshot(prepared.source)
    expected = response(*prepared.items)

    def reply():
        assert execution_journal(prepared).events()[-1]["event_type"] == "compact_dispatch_started"
        return expected

    client = Client(reply)
    result = run(prepared, client)
    assert result["result"] == "COMPACT_WINDOW_OBSERVED_ONLY"
    assert result["provider_request_attempts"] == len(client.calls) == len(client.closes) == 1
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert result["accounting"]["invoice_cost_usd"] is None
    assert result["next_request_admission"] == "NOT_TESTED"
    assert result["count_requests"] == result["generation_requests"] == 0
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert not result["official"] and not result["native_window_activation"]
    call, = client.calls
    assert set(call) == {"model", "input", "service_tier", "timeout"}
    assert call["input"] == prepared.items and 0 < call["timeout"] <= 300
    assert 0 < client.closes[0] <= 5
    window = json.loads(diagnostic.read_source_artifact(prepared.root / "execution",
                        result["response"]["window_artifact"]))
    assert window == expected["output"]  # Including all retained public/native/opaque items.
    after = snapshot(prepared.root)
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert snapshot(prepared.root) == after
    assert snapshot(prepared.source) == before
    with pytest.raises(FileExistsError):
        run(prepared, client)
    assert len(client.calls) == 1
    check_no_plaintext(prepared.root)
    assert b"opaque-" not in execution_journal(prepared).path.read_bytes()


@pytest.mark.parametrize("changed", ["proposal", "journal", "envelope", "input", "packet",
                                     "runtime", "sdk", "ack", "price_date", "root_copy"])
def test_changed_input_and_duplicate_binding_rejected_before_client(prepared, monkeypatch, changed):
    if changed in {"runtime", "sdk"}:
        if changed == "runtime":
            monkeypatch.setattr(diagnostic, "runtime_content_hash", lambda: sha256_json("changed"))
        else:
            monkeypatch.setattr(diagnostic, "version", lambda _: "different-installed-version")
    elif changed in {"ack", "price_date"}:
        if changed == "price_date":
            monkeypatch.setattr(diagnostic, "utc_now", lambda: SimpleNamespace(
                date=lambda: SimpleNamespace(isoformat=lambda: "2000-01-01")))
    elif changed == "root_copy":
        target = prepared.root.with_name("copy")
        target.mkdir()
        (target / "packet.json").write_bytes((prepared.root / "packet.json").read_bytes())
        prepared.root = target
    else:
        path = {"proposal": prepared.kwargs["proposal"], "journal": prepared.journal.path,
                "envelope": prepared.journal.envelope_path,
                "input": Path(prepared.proposal["source"]["input_artifact_path"]),
                "packet": prepared.root / "packet.json"}[changed]
        if changed == "proposal":
            value = json.loads(path.read_bytes())
            value["proposed_request"]["model"] = "unapproved-model"
            path.write_text(canonical_json(value), encoding="utf-8")
        elif changed == "packet":
            value = json.loads(path.read_bytes())
            value["repeat"] = 2
            path.write_text(canonical_json(value), encoding="utf-8")
        else:
            path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((ContractError, RecoveryError)):
        diagnostic.collect(prepared.root, prepared.packet_hash,
                           accept_model_limit_reservation=changed != "ack")
    assert not (prepared.root / "execution").exists()


@pytest.mark.parametrize("field,value", [("max_cost_usd", Decimal("0.875")),
                                         ("max_cost_usd", Decimal("NaN")), ("repeat", 2)])
def test_prepare_reservation_and_repeat_limits(prepared, field, value):
    kwargs = {**prepared.kwargs, "root": prepared.root.with_name("invalid"), field: value}
    with pytest.raises(ContractError):
        diagnostic.prepare(**kwargs)
    assert not kwargs["root"].exists()


@pytest.mark.parametrize("bad", ["summary", "content", "action", "message", "missing_cipher",
                                 "unknown_item", "result_order"])
def test_reject_whole_invalid_window_but_keep_usage(prepared, bad):
    reply = response(*prepared.items)
    if bad in {"summary", "content"}:
        reply["output"][-2][bad] = [{"text": SECRET}]
    elif bad == "action":
        reply["output"][3]["arguments"] = SECRET
    elif bad == "message":
        reply["output"][0]["content"] = SECRET
    elif bad == "missing_cipher":
        del reply["output"][-1]["encrypted_content"]
    elif bad == "unknown_item":
        reply["output"].append({"type": "unknown", "text": SECRET})
    else:
        reply["output"][3], reply["output"][5] = reply["output"][5], reply["output"][3]
    result = run(prepared, Client(reply))
    assert result["result"] == "COMPACTION_OUTPUT_CONTRACT_ERROR"
    assert result["response"]["window_artifact"] is None
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    check_no_plaintext(prepared.root)


@pytest.mark.parametrize("bad", ["usage_missing", "negative", "over_budget", "unpriced_tier"])
def test_billing_failure_preserves_valid_whole_window_and_stops(prepared, bad):
    reply = response()
    if bad == "usage_missing":
        del reply["usage"]
    elif bad == "negative":
        reply["usage"]["input_tokens"] = -1
    elif bad == "unpriced_tier":
        reply["service_tier"] = SECRET
    else:
        reply["usage"].update(input_tokens=400001, output_tokens=128000, total_tokens=528001)
    client = Client(reply)
    result = run(prepared, client)
    assert result["result"] in {"STOP_BILLING_UNKNOWN", "STOP_RESERVATION_EXCEEDED"}
    assert result["response"]["window_artifact"]
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert len(client.calls) == 1
    check_no_plaintext(prepared.root)


def test_known_size_http_error_is_not_a_timeout_or_free_call(prepared):
    error = openai.BadRequestError(SECRET, response=httpx.Response(400,
        request=httpx.Request("POST", diagnostic.cost.CONTRACT["endpoint"])), body={
            "message": SECRET, "code": "string_above_max_length",
            "type": "invalid_request_error", "param": "input[83].encrypted_content"})
    client = Client(error)
    result = run(prepared, client)
    assert result["result"] == "COMPACT_ENDPOINT_REJECTED_INPUT_SIZE"
    assert result["failure"]["category"] == "http_error"
    assert result["failure"]["param"] == "input[83].encrypted_content"
    assert result["accounting"]["status"] == "BILLING_UNKNOWN"
    assert result["accounting"]["model_rate_cost_nanos"] is None
    assert len(client.calls) == 1
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    check_no_plaintext(prepared.root)


@pytest.mark.parametrize("error", [TimeoutError(SECRET), KeyboardInterrupt(SECRET)])
def test_transport_uncertainty_has_no_retry(prepared, error):
    client = Client(error)
    result = run(prepared, client)
    assert result["result"] == "STOP_ERROR"
    assert result["accounting"]["status"] == "BILLING_UNKNOWN"
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert len(client.calls) == len(client.closes) == 1
    check_no_plaintext(prepared.root)


def test_cleanup_failure_preserves_usage_and_window(prepared):
    client = Client(close_error=TimeoutError(SECRET))
    result = run(prepared, client)
    assert result["result"] == "STOP_CLEANUP_UNKNOWN"
    assert result["response"]["status"] == "COMPACT_WINDOW_OBSERVED_ONLY"
    assert result["observed_usage"] == response()["usage"]
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert len(client.calls) == 1


def test_setup_deadline_prevents_dispatch(prepared):
    now = [0.0]

    def load_key(_):
        now[0] = 303
        return "mock"

    client = Client()
    result = run(prepared, client, clock=lambda: now[0], credential_loader=load_key)
    assert not client.calls and client.closes == [2]
    assert result["provider_request_attempts"] == result["admitted_compaction_attempts"] == 0
    assert result["accounting"]["status"] == "NOT_DISPATCHED"


@pytest.mark.parametrize("point", ["compact_dispatch_started", "compact_usage_recorded",
                                   "compact_response_recorded", "compact_client_cleanup",
                                   "terminal"])
def test_crash_recovery_never_calls_provider_again(prepared, monkeypatch, point):
    class SimulatedCrash(BaseException):
        pass

    append = DevJournal.append

    def crash(self, event, payload=None):
        result = append(self, event, payload)
        if event == point:
            raise SimulatedCrash()
        return result

    client = Client(response(*prepared.items))
    with monkeypatch.context() as scoped:
        scoped.setattr(DevJournal, "append", crash)
        with pytest.raises(SimulatedCrash):
            run(prepared, client)
    calls_before = len(client.calls)
    result = diagnostic.recover(prepared.root, prepared.packet_hash)
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert len(client.calls) == calls_before == (0 if point == "compact_dispatch_started" else 1)
    if point == "compact_dispatch_started":
        assert result["provider_request_attempts"] is None  # Intent != proven HTTP attempt.
        assert result["accounting"]["model_rate_cost_nanos"] is None
    else:
        assert result["observed_usage"] == response()["usage"]
    if point in {"compact_response_recorded", "compact_client_cleanup", "terminal"}:
        assert result["response"]["window_artifact"]
    with pytest.raises(FileExistsError):
        run(prepared, client)


def test_orphan_window_keeps_usage_and_does_not_retry(prepared, monkeypatch):
    original = diagnostic.put_json

    def crash(store, value):
        artifact = original(store, value)
        if isinstance(value, list):
            raise KeyboardInterrupt()
        return artifact

    monkeypatch.setattr(diagnostic, "put_json", crash)
    client = Client()
    result = run(prepared, client)
    assert result["response"] is None
    assert result["observed_usage"] == response()["usage"]
    assert result["result"] == "STOP_ERROR"
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert len(client.calls) == 1


def test_crash_immediately_after_response_has_unknown_usage_no_retry(prepared, monkeypatch):
    class SimulatedCrash(BaseException):
        pass

    def crash(*args):
        raise SimulatedCrash()

    client = Client()
    monkeypatch.setattr(diagnostic, "_record_response", crash)
    with pytest.raises(SimulatedCrash):
        run(prepared, client)
    result = diagnostic.recover(prepared.root, prepared.packet_hash)
    assert result["observed_usage"] is None
    assert result["accounting"]["status"] == "BILLING_UNKNOWN"
    assert result["provider_request_attempts"] is None
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert len(client.calls) == 1


def test_source_drift_during_setup_stops_before_dispatch(prepared):
    def load_key(_):
        path = Path(prepared.proposal["source"]["input_artifact_path"])
        path.write_bytes(path.read_bytes() + b" ")
        return "mock"

    client = Client()
    result = run(prepared, client, credential_loader=load_key)
    assert not client.calls
    assert result["accounting"]["status"] == "NOT_DISPATCHED"
    assert result["admitted_compaction_attempts"] == 0


def test_concurrent_recovery_rejected_by_execution_lock(prepared):
    def reply():
        with pytest.raises(RecoveryError, match="already active"):
            diagnostic.recover(prepared.root, prepared.packet_hash)
        with pytest.raises(FileExistsError):
            diagnostic.collect(prepared.root, prepared.packet_hash,
                               accept_model_limit_reservation=True)
        return response()

    client = Client(reply)
    assert run(prepared, client)["result"] == "COMPACT_WINDOW_OBSERVED_ONLY"
    assert len(client.calls) == 1


def test_corrupt_window_is_not_repaired_or_ignored(prepared):
    result = run(prepared, Client())
    path = Path(result["response"]["window_artifact"]["path"])
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ContractError):
        diagnostic.recover(prepared.root, prepared.packet_hash)


def test_terminal_recovery_with_changed_runtime_is_readonly(prepared, monkeypatch):
    result = run(prepared, Client())
    (prepared.root / "execution/result.json").unlink()
    monkeypatch.setattr(diagnostic, "runtime_content_hash", lambda: sha256_json("new runtime"))
    assert diagnostic.recover(prepared.root, prepared.packet_hash) == result
    assert json.loads((prepared.root / "execution/result.json").read_bytes()) == result


def test_sdk_transport_preserves_oversized_field_once_no_count_or_create(prepared):
    calls = []
    request = copy.deepcopy(prepared.request)
    request["input"][-1]["encrypted_content"] = "x" * 1717452

    async def handler(http_request):
        calls.append(http_request)
        return httpx.Response(200, json=response())

    sdk = openai.AsyncOpenAI(api_key="mock-only", max_retries=0,
                            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    client = BoundedResponsesClient(api_key="mock-only", client=sdk)
    try:
        reply = client.responses.compact(**request, timeout=5)
        assert reply.object == "response.compaction"
    finally:
        client.close(timeout=5)
    call, = calls
    assert call.url.path == "/v1/responses/compact"
    body = json.loads(call.content)
    assert body == request and set(body) == {"model", "input", "service_tier"}
    assert call.content.count(("x" * 1717452).encode()) == 1
