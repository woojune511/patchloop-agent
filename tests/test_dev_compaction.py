from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest

from patchloop.agent.compaction import validated_window
from patchloop.agent.request_transport import BoundedResponsesClient
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import compaction as handoff
from patchloop.dev import compaction_cost as cost
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json

SECRET = "PRIVATE_HIDDEN_REFERENCE_PLAINTEXT_REASONING_SENTINEL"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no real network or credential use")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def source_items():
    return [
        {"role": "system", "content": "Public coding contract"},
        {"role": "developer", "content": '{"public_task":{"goal":"public goal"}}'},
        {"role": "user", "content": "Complete the public task"},
        {"type": "reasoning", "id": "rs_old", "encrypted_content": "old-cipher"},
        {"type": "function_call", "call_id": "read_1", "name": "read_file",
         "arguments": '{"path":"public.py"}'},
        {"type": "function_call", "call_id": "read_2", "name": "read_file",
         "arguments": '{"path":"helper.py"}'},
        {"type": "function_call_output", "call_id": "read_1", "output": "EXACT_SOURCE_ONE"},
        {"type": "function_call_output", "call_id": "read_2", "output": "EXACT_SOURCE_TWO"},
        {"role": "developer", "content": '{"current_diff":"public diff"}'},
    ]


def response(*items):
    return {
        "id": "resp_compacted", "object": "response.compaction", "created_at": 1,
        "output": [*copy.deepcopy(items), {"id": "cmp_1", "type": "compaction",
                                          "encrypted_content": "opaque-compressed-state"}],
        "usage": {"input_tokens": 1000, "output_tokens": 40, "total_tokens": 1040,
                  "input_tokens_details": {"cached_tokens": 10},
                  "output_tokens_details": {"reasoning_tokens": 20}},
    }


class Client:
    max_retries = 0

    def __init__(self, reply=None, cleanup=None):
        self.reply = response() if reply is None else reply
        self.cleanup = cleanup
        self.calls, self.closes = [], []
        self.responses = SimpleNamespace(compact=self.compact)

    def compact(self, **request):
        self.calls.append(request)
        if isinstance(self.reply, BaseException):
            raise self.reply
        return self.reply() if callable(self.reply) else self.reply

    def close(self, *, timeout):
        self.closes.append(timeout)
        if self.cleanup:
            self.cleanup()


@pytest.fixture
def prepared(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_compacttest")
    adapter = handoff.CompactionAdapter(journal, policy_hash=sha256_json("bound policy"))
    items = source_items()
    refs = [adapter.store.put_text(canonical_json(i), "application/json")
            for i in (items, items[:3])]
    ledger = DevCostLedger(Decimal("1.20"), cost.RATES)
    ledger.spent_nanos = 200_000_000
    args = dict(source_input=refs[0], source_seed=refs[1], boundary_id="boundary_3",
                ledger=ledger, accept_model_limit_reservation=True, active_elapsed_seconds=100.0)
    binding = adapter.prepare(**args)
    return SimpleNamespace(adapter=adapter, journal=journal, items=items,
                           ledger=ledger, args=args, binding=binding, refs=refs)


def run(prepared, client=None, *, seconds=305, now=None, factory=None):
    client = client or Client()
    return prepared.adapter.execute(
        client_factory=factory or (lambda: client), ledger=prepared.ledger,
        deadline=(ExecutionDeadline.from_remaining(seconds) if now is None else
                  ExecutionDeadline.from_remaining(seconds, clock=lambda: now[0])),
        active_elapsed_seconds=100.0,
    )


def snapshot(root):
    return {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def assert_private_absent(root):
    for content in snapshot(root).values():
        assert SECRET.encode() not in content


def assert_stable(prepared, result):
    before = snapshot(prepared.journal.root)
    fresh = handoff.CompactionAdapter(prepared.journal, policy_hash=prepared.adapter.policy_hash)
    assert fresh.recover() == result == fresh.recover()
    # Completed recovery uses no client, ledger reservation or current deadline.
    prepared.ledger.spent_nanos = prepared.ledger.cap_nanos
    assert run(prepared, seconds=0, factory=lambda: pytest.fail("replay dispatched")) == result
    assert snapshot(prepared.journal.root) == before


def test_preparation_recovery_does_not_consume_the_unstarted_attempt(prepared):
    before = snapshot(prepared.journal.root)
    assert prepared.adapter.prepare(**prepared.args) == prepared.binding
    assert prepared.adapter.recover()["status"] == "NOT_STARTED"
    assert snapshot(prepared.journal.root) == before
    assert prepared.binding["reservation"]["available_nanos"] == 1_000_000_000
    assert prepared.binding["reservation"]["reserved_cost_nanos"] == 876_000_000
    client = Client()
    assert run(prepared, client)["ready_for_activation"]
    assert len(client.calls) == 1


def test_whole_window_order_usage_binding_and_no_action_execution(prepared):
    reply = response(*prepared.items)
    # The API can normalize a string message into text parts; preserve its output shape.
    reply["output"][0] = {"id": "msg_1", "type": "message", "role": "system",
                          "status": "completed", "content": [{"type": "input_text",
                                                               "text": "Public coding contract"}]}
    client = Client(reply)
    result = run(prepared, client)
    assert result["ready_for_activation"] and result["terminal"] is None
    window = prepared.adapter._read(result["window_artifact"])
    assert window == reply["output"]
    assert result["item_order_hash"] == sha256_json([sha256_json(i) for i in window])
    assert result["source_input_hash"] == prepared.refs[0].content_hash
    assert result["source_seed_hash"] == prepared.refs[1].content_hash
    assert result["binding_hash"] == sha256_json(prepared.binding)
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert prepared.ledger.spent_nanos == 200_000_000  # Caller settles unique durable usage later.
    assert result["usage"] == reply["usage"]
    assert result["admitted_compaction_attempts"] == result["provider_request_attempts"] == 1
    assert result["generation_requests"] == result["count_requests"] == 0
    assert result["tool_executions"] == 0
    assert result["task_acceptance"] == result["safety_state"] == "NOT_RUN"
    assert not result["official"] and not result["endpoint_enforced_dollar_cap"]
    assert set(client.calls[0]) == {"model", "input", "service_tier", "timeout"}
    assert client.calls[0]["input"] == prepared.items
    assert client.calls[0]["model"] == cost.MODEL
    assert 0 < client.calls[0]["timeout"] <= 300 and 0 < client.closes[0] <= 5
    assert "opaque-compressed-state" not in prepared.journal.path.read_text()
    assert_stable(prepared, result)


@pytest.mark.parametrize("bad", ["summary", "reasoning_body", "invented_message",
                                "invented_action", "changed_action", "unpaired", "duplicate",
                                "cipher", "unknown", "annotation", "status", "phase"])
def test_bad_output_retains_usage_not_unvalidated_plaintext(prepared, bad):
    reply = response()
    if bad in {"summary", "reasoning_body"}:
        item = {"type": "reasoning", "id": "rs_2", "encrypted_content": "cipher"}
        item["summary" if bad == "summary" else "content"] = SECRET
        reply["output"].append(item)
    elif bad == "invented_message":
        reply["output"].append({"role": "assistant", "content": SECRET})
    elif bad in {"invented_action", "changed_action", "unpaired"}:
        item = copy.deepcopy(prepared.items[4])
        if bad == "invented_action":
            item["call_id"] = "never_observed"
        elif bad == "changed_action":
            item["arguments"] = SECRET
        reply["output"].append(item)
    elif bad == "duplicate":
        reply["output"] *= 2
    elif bad == "cipher":
        reply["output"][0].pop("encrypted_content")
    elif bad == "unknown":
        reply["output"].append({"type": "unknown", "content": SECRET})
    elif bad == "annotation":
        reply["output"].append({"role": "user", "content": [
            {"type": "input_text", "text": "Complete the public task", "annotations": [SECRET]}]})
    else:
        reply["output"].append({"role": "user", "content": "Complete the public task", bad: SECRET})
    result = run(prepared, Client(reply))
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert result["window_artifact"] is None and not result["ready_for_activation"]
    assert_private_absent(prepared.journal.root)
    assert_stable(prepared, result)


@pytest.mark.parametrize("bad", ["missing", "cached_missing", "total", "boolean", "cache_write",
                                "input_limit", "output_limit"])
def test_billing_uncertainty_or_reservation_exceeded_stops(prepared, bad):
    reply = response()
    usage = reply["usage"]
    if bad == "missing":
        reply.pop("usage")
    elif bad == "cached_missing":
        usage["input_tokens_details"] = {}
    elif bad == "total":
        usage["total_tokens"] = 1
    elif bad == "boolean":
        usage["output_tokens"] = True
    elif bad == "cache_write":
        usage["input_tokens_details"]["cache_write_tokens"] = 1
    elif bad == "input_limit":
        usage["input_tokens"] = 400_001
        usage["total_tokens"] = 400_041
    else:
        usage["output_tokens"] = 128_001
        usage["total_tokens"] = 129_001
    result = run(prepared, Client(reply))
    assert result["terminal"] == "COST_CAP_REACHED"
    assert not result["ready_for_activation"] and result["accounting"]["invoice_cost_usd"] is None
    assert_stable(prepared, result)


@pytest.mark.parametrize("change", ["policy", "runtime", "source", "seed", "budget"])
def test_changed_inputs_rejected_before_factory_or_journal_write(prepared, monkeypatch, change):
    if change == "policy":
        prepared.adapter.policy_hash = sha256_json("different policy")
    elif change == "runtime":
        monkeypatch.setattr(handoff, "runtime_content_hash", lambda: sha256_json("changed"))
    elif change in {"source", "seed"}:
        Path(prepared.refs[change == "seed"].path).write_bytes(b"[]")
    else:
        prepared.ledger.spent_nanos += 1
    before = snapshot(prepared.journal.root)
    with pytest.raises((ContractError, RecoveryError)):
        run(prepared, factory=lambda: pytest.fail("unapproved dispatch"))
    assert snapshot(prepared.journal.root) == before


@pytest.mark.parametrize("change", ["ack", "cap", "prefix", "boundary", "elapsed", "terminal"])
def test_preparation_rejects_wrong_contract_without_provider(tmp_path, change):
    fixture = SimpleNamespace()
    fixture.journal = DevJournal(tmp_path, "run_dev_preflight")
    adapter = handoff.CompactionAdapter(fixture.journal, policy_hash=sha256_json("policy"))
    items = source_items()
    source = adapter.store.put_text(canonical_json(items))
    seed = adapter.store.put_text(canonical_json(items[:3] if change != "prefix" else items[3:]))
    if change == "terminal":
        fixture.journal.append("terminal", {"terminal": "AGENT_STOPPED"})
    before = snapshot(tmp_path)
    with pytest.raises(ContractError):
        adapter.prepare(source_input=source, source_seed=seed,
                        boundary_id="../unsafe" if change == "boundary" else "boundary",
                        ledger=DevCostLedger(Decimal("0.10" if change == "cap" else "1.20"),
                                             cost.RATES),
                        accept_model_limit_reservation=change != "ack",
                        active_elapsed_seconds=float("nan") if change == "elapsed" else 10)
    assert not [e for e in fixture.journal.events() if e["event_type"] == "compaction_prepared"]
    assert all(Path(p).read_bytes() == b for p, b in before.items())


def test_concurrent_run_lock_rejects_before_factory(prepared):
    with prepared.journal.execution_lock(), pytest.raises(RecoveryError, match="already active"):
        run(prepared, factory=lambda: pytest.fail("parallel provider call"))


def test_expired_deadline_never_constructs_client_or_dispatches(prepared):
    result = run(prepared, seconds=0, factory=lambda: pytest.fail("expired client setup"))
    assert result["terminal"] == "LIMIT_REACHED"
    assert result["provider_request_attempts"] == result["admitted_compaction_attempts"] == 0
    assert result["accounting"]["status"] == "NOT_RUN"
    assert_stable(prepared, result)


def test_shared_deadline_clips_request_and_excludes_process_downtime(prepared):
    now = [999_000.0]

    def reply():
        now[0] += 2
        return response()

    def cleanup():
        now[0] += 1

    client = Client(reply, cleanup)
    result = run(prepared, client, seconds=9, now=now)
    assert client.calls[0]["timeout"] == 4 and client.closes == [5]
    assert result["active_elapsed_seconds"] == 103
    now[0] += 999_000
    assert_stable(prepared, result)


def test_setup_consumes_shared_deadline_and_only_owned_client_is_closed(prepared):
    now = [0.0]
    client, unrelated = Client(), Client()

    def factory():
        now[0] = 7
        return client

    result = run(prepared, seconds=9, now=now, factory=factory)
    assert result["terminal"] == "LIMIT_REACHED" and not client.calls
    assert client.closes == [2] and not unrelated.closes
    assert result["active_elapsed_seconds"] == 107


@pytest.mark.parametrize("late", ["response", "cleanup"])
def test_late_completion_preserves_usage_but_never_activates(prepared, late):
    now = [0.0]

    def reply():
        now[0] = 9 if late == "response" else 2
        return response()

    def cleanup():
        now[0] = 9

    client = Client(reply, cleanup)
    result = run(prepared, client, seconds=9, now=now)
    assert result["terminal"] == ("PROVIDER_TIMEOUT_OR_UNKNOWN" if late == "response"
                                  else "LIMIT_REACHED")
    assert not result["ready_for_activation"]
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert result["window_artifact"] is not None
    assert_stable(prepared, result)


@pytest.mark.parametrize("stage", ["request", "cleanup"])
def test_transport_or_cleanup_uncertainty_is_sanitized_and_never_retried(prepared, stage, capsys):
    def fail():
        raise TimeoutError(SECRET)

    client = Client(fail if stage == "request" else None, fail if stage == "cleanup" else None)
    result = run(prepared, client)
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert len(client.calls) == len(client.closes) == 1
    assert result["accounting"]["model_rate_cost_nanos"] == (None if stage == "request" else 923250)
    assert_private_absent(prepared.journal.root)
    assert SECRET not in str(capsys.readouterr())
    assert_stable(prepared, result)


class Crash(BaseException):
    pass


@pytest.mark.parametrize("event,attempts,known,ready", [
    ("compaction_started", None, False, False),
    ("compaction_usage_recorded", 1, True, False),
    ("compaction_response_recorded", 1, True, True),
    ("compaction_finished", 1, True, True),
])
def test_fault_after_durable_boundary_never_replays_request(prepared, monkeypatch,
                                                          event, attempts, known, ready):
    original = prepared.journal.append

    def crash(name, payload=None):
        result = original(name, payload)
        if name == event:
            raise Crash()
        return result

    client = Client()
    with monkeypatch.context() as patch:
        patch.setattr(prepared.journal, "append", crash)
        with pytest.raises(Crash):
            run(prepared, client)
    result = prepared.adapter.recover()
    assert result["provider_request_attempts"] == attempts
    assert result["accounting"]["model_rate_cost_nanos"] == (923250 if known else None)
    assert result["ready_for_activation"] is ready
    assert len(client.calls) == int(attempts == 1)
    assert_stable(prepared, result)


@pytest.mark.parametrize("stage", ["window", "window_event", "cleanup_event", "receipt_event"])
def test_incomplete_storage_boundaries_preserve_cost_without_salvage(prepared, monkeypatch, stage):
    original_put, original_append = prepared.adapter._put, prepared.journal.append

    def put(value):
        original_put(value)  # Orphan CAS is not an accepted window.
        raise Crash()

    def append(name, payload=None):
        target = {"window_event": "compaction_response_recorded",
                  "cleanup_event": "compaction_cleanup_recorded",
                  "receipt_event": "compaction_finished"}.get(stage)
        if name == target:
            raise Crash()
        return original_append(name, payload)

    client = Client()
    with monkeypatch.context() as patch:
        if stage == "window":
            patch.setattr(prepared.adapter, "_put", put)
        patch.setattr(prepared.journal, "append", append)
        with pytest.raises(Crash):
            run(prepared, client)
    result = prepared.adapter.recover()
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert result["ready_for_activation"] is (stage == "receipt_event")
    assert len(client.calls) == 1
    if stage in {"window", "window_event"}:
        assert result["window_artifact"] is None
    if stage == "cleanup_event":
        assert result["cleanup"]["status"] == "UNKNOWN"
    assert_stable(prepared, result)


@pytest.mark.parametrize("where", ["window", "receipt", "receipt_space", "missing", "marker"])
def test_completed_receipt_integrity_failure_never_modifies_journal(prepared, where):
    result = run(prepared)
    if where == "window":
        Path(result["window_artifact"]["path"]).write_bytes(b"[]")
    elif where == "missing":
        prepared.adapter.receipt_path.unlink()
    elif where == "receipt_space":
        with prepared.adapter.receipt_path.open("ab") as stream:
            stream.write(b" ")
    elif where == "marker":
        prepared.journal.append("compaction_finished", {"receipt_hash": sha256_json("other")})
    else:
        saved = json.loads(prepared.adapter.receipt_path.read_bytes())
        saved["item_order_hash"] = sha256_json("tampered")
        prepared.adapter.receipt_path.write_text(canonical_json(saved))
    before = snapshot(prepared.journal.root)
    with pytest.raises((ContractError, RecoveryError)):
        prepared.adapter.recover()
    assert snapshot(prepared.journal.root) == before


def test_large_ciphertext_is_exact_and_not_a_token_or_output_cap(prepared):
    reply = response()
    reply["output"][0]["encrypted_content"] = "x" * 1_701_176
    result = run(prepared, Client(reply))
    assert prepared.adapter._read(result["window_artifact"]) == reply["output"]
    assert result["usage"]["output_tokens"] == 40
    assert "x" * 1024 not in prepared.journal.path.read_text()


def test_retained_public_message_multiplicity_and_role_must_match_source(prepared):
    repeated = response(prepared.items[2], prepared.items[2])
    with pytest.raises(ContractError, match="invented a public message"):
        validated_window(repeated, prepared.items)
    repeated = response({**prepared.items[2], "role": "system"})
    with pytest.raises(ContractError, match="invented a public message"):
        validated_window(repeated, prepared.items)


def test_sdk_compact_adapter_mock_uses_shared_transport_without_schema_warning(prepared, capsys):
    visits = []
    reply = response(prepared.items[2], *prepared.items[4:8])

    async def handler(request):
        visits.append(request)
        assert request.url.path == "/v1/responses/compact"
        assert json.loads(request.content) == {
            "model": cost.MODEL, "service_tier": "default", "input": prepared.items}
        return httpx.Response(200, json=reply)

    def factory():
        return BoundedResponsesClient(api_key="", client=openai.AsyncOpenAI(
            api_key="mock-not-a-credential", max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False)))

    result = run(prepared, factory=factory)
    assert result["ready_for_activation"] and len(visits) == 1
    assert prepared.adapter._read(result["window_artifact"]) == reply["output"]
    assert not capsys.readouterr().err
    assert_stable(prepared, result)


def test_serialization_failure_keeps_previously_recorded_usage(prepared):
    class BrokenResponse:
        usage = response()["usage"]
        id = "resp_broken"

        def model_dump(self, **kwargs):
            assert kwargs["warnings"] is False
            raise ValueError(SECRET)

    result = run(prepared, Client(BrokenResponse()))
    assert result["accounting"]["model_rate_cost_nanos"] == 923250
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert_private_absent(prepared.journal.root)


def test_compaction_remains_separate_from_the_generation_adapter():
    from patchloop.dev.contracts import dev_tool_surface_hash

    assert dev_tool_surface_hash().startswith("sha256:")
    # Phase 3 connects an explicitly opted-in runner, not the default adapter.
    root = Path(handoff.__file__).resolve().parents[1]
    assert "CompactionAdapter" not in (root / "agent" / "model.py").read_text(encoding="utf-8")


def test_recovery_does_not_accept_orphan_compaction_artifacts(tmp_path):
    adapter = handoff.CompactionAdapter(DevJournal(tmp_path, "run_dev_orphan"),
                                        policy_hash=sha256_json("policy"))
    ArtifactStore(tmp_path / "artifacts").put_text(canonical_json(response()["output"]))
    assert adapter.recover() is None
    with pytest.raises(ContractError, match="prepared"):
        adapter.execute(client_factory=lambda: pytest.fail("orphan dispatch"),
                        ledger=DevCostLedger(Decimal("1.2"), cost.RATES),
                        deadline=ExecutionDeadline.from_remaining(305), active_elapsed_seconds=0)


def test_window_artifact_descriptor_hash_is_enforced(prepared):
    result = run(prepared)
    ref = Artifact.model_validate(result["window_artifact"])
    assert ref.content_hash == sha256_json(prepared.adapter._read(ref))
