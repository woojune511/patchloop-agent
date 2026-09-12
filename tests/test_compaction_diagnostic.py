from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import openai
import pytest
from test_count_replay import SECRET, snapshot
from test_count_replay import frozen as _frozen

from diagnostics import compaction_replay as design
from diagnostics import compaction_state as state
from diagnostics import count_replay
from diagnostics import episode_requests as transport
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_json

frozen = _frozen


@pytest.fixture(autouse=True)
def no_live_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no real network, credential or task execution")

    # Windows asyncio uses a local socketpair; block real HTTP, not that internal pipe.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    monkeypatch.setattr(count_replay.shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(count_replay.shared, "create_openai_client", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "execute_request", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "count_input_tokens_v2", forbidden)


@pytest.fixture
def packet(frozen):
    report = design.prepare(frozen.root, frozen.output)
    trial = frozen.output.parent / "trial"
    state.reserve(frozen.output, report["packet_hash"], trial)
    return frozen, report, trial


def response(*retained):
    return {
        "id": "resp_compacted", "object": "response.compaction", "created_at": 1,
        "output": [*retained, {"id": "cmp_1", "type": "compaction",
                                  "encrypted_content": "opaque-compressed-state"}],
        "usage": {"input_tokens": 1000, "output_tokens": 40, "total_tokens": 1040,
                  "input_tokens_details": {"cached_tokens": 10},
                  "output_tokens_details": {"reasoning_tokens": 20}},
    }


def trial_journal(trial):
    binding = json.loads((trial / "trial.json").read_bytes())
    return DevJournal(trial, binding["run_id"])


def artifact(root, ref):
    return json.loads(design.read_source_artifact(root, ref))


def test_frozen_healthy_input_no_future_data_or_rewrites(packet):
    frozen, report, _ = packet
    before = snapshot(frozen.root)
    first, values = design.verify(frozen.output, report["packet_hash"])
    assert (first, values) == design.verify(frozen.output, report["packet_hash"])
    assert snapshot(frozen.root) == before
    assert values["compact"]["input"] == frozen.payloads[0]["input"]
    assert set(values["compact"]) == {"model", "input", "service_tier"}
    control = values["control"]
    assert control["model"] == "gpt-5.4-mini-2026-03-17"
    assert control["reasoning"] == {"effort": "medium"}
    assert control["max_output_tokens"] == 25_000 and control["store"] is False
    assert first["protocol"]["live_execution_enabled"] is False
    assert first["billing"]["compaction_cost_usd"] is None
    for path in frozen.output.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
            assert b"ciphertext-second" not in path.read_bytes()
    with pytest.raises(ContractError, match="new"):
        design.prepare(frozen.root, frozen.output)


def observation_input():
    raw_hash = sha256_json("public.py raw bytes")
    span = {"path": "public.py", "file_hash": raw_hash, "start_line": 10,
            "end_line": 13, "content": "observed10\nobserved11\nunselected12\nobserved13"}
    history = []
    for call_id, name, output in (
        ("read_1", "read_file", {"spans": [span]}),
        ("check_1", "run_check", {"passed": False, "stderr": "EXACT_PUBLIC_CHECK_ERROR"}),
    ):
        history.extend([
            {"type": "function_call", "call_id": call_id, "name": name, "arguments": "{}"},
            {"type": "function_call_output", "call_id": call_id,
             "output": canonical_json({"action_id": call_id, "tool": name,
                                       "status": "succeeded", "output": output})},
        ])
    public = {
        "public_task": {"goal": "ULTIMATE_PUBLIC_GOAL"}, "current_diff": "EXACT_CURRENT_DIFF",
        "current_sources": [{"path": "public.py", "file_hash": raw_hash,
                             "edit_permission": "allowed", "content_delivery": {
                                 "read_1": {"output.spans[0]": [[10, 11], [13, 13]]}}}],
        "visible_check_status": [{"check_id": "visible", "status": "NOT_RUN"}],
        "recent_checks": [{"action_id": "check_1", "evidence_currency": "historical",
                           "delivery": "preceding_function_call_output"}],
        "remaining_budget": {"model_calls": 10}, "available_tool_names": ["replace_text"],
    }
    return assemble_model_input(system_prompt="Fixed coding instruction", state=public,
                                history=history)


def test_reentry_restores_only_selected_lines_and_exact_referenced_check():
    items = observation_input()
    before = copy.deepcopy(items)
    reentry, metrics = design.public_reentry(items)
    assert items == before
    payload = json.loads(reentry[-1]["content"])
    group, = payload["state"]["current_sources"]
    assert group["content_delivery"] == {}
    assert group["inline_spans"] == [
        {"start_line": 10, "end_line": 11, "content": "observed10\nobserved11"},
        {"start_line": 13, "end_line": 13, "content": "observed13"},
    ]
    assert "unselected12" not in canonical_json(payload)
    assert metrics["selected_line_count"] == 3
    assert payload["state"]["public_task"]["goal"] == "ULTIMATE_PUBLIC_GOAL"
    assert payload["state"]["current_diff"] == "EXACT_CURRENT_DIFF"
    assert payload["state"]["visible_check_status"][0]["status"] == "NOT_RUN"
    assert payload["state"]["recent_checks"][0]["evidence_currency"] == "historical"
    assert [i["call_id"] for i in payload["referenced_public_exchanges"]] == ["check_1"] * 2
    assert "EXACT_PUBLIC_CHECK_ERROR" in canonical_json(payload)
    assert design.public_reentry(items) == (reentry, metrics)


def test_dangling_source_reference_does_not_read_workspace():
    items = observation_input()
    initial = json.loads(items[1]["content"])
    initial["current_sources"][0]["content_delivery"] = {"missing": {"output.spans.0": [[1, 3]]}}
    items[1]["content"] = canonical_json(initial)
    with pytest.raises(ValueError, match="missing source"):
        design.public_reentry(items)


def test_missing_check_delivery_is_not_silently_discarded():
    items = observation_input()
    initial = json.loads(items[1]["content"])
    initial["recent_checks"][0]["action_id"] = "missing_check"
    items[1]["content"] = canonical_json(initial)
    with pytest.raises(ContractError, match="missing referenced public action"):
        design.public_reentry(items)


def test_canonical_window_order_parallel_pairs_settings_and_recovery(packet):
    frozen, report, trial = packet
    _, values = design.verify(frozen.output, report["packet_hash"])
    items = values["control"]["input"]
    native = [i for i in items if i.get("type") in {"function_call", "function_call_output"}]
    compacted = response(items[2], items[3], *native)
    receipt = state.record_response(trial, compacted)
    assert receipt["status"] == "READY_FOR_REVIEW"
    window = artifact(trial, receipt["window_artifact"])
    assert window == compacted["output"]
    request = artifact(trial, receipt["next_request_artifact"])
    assert request["input"] == [*window, *values["reentry"]]
    assert {k: v for k, v in request.items() if k != "input"} == {
        k: v for k, v in values["control"].items() if k != "input"
    }
    count = artifact(trial, receipt["next_count_artifact"])
    assert count == OpenAIResponsesAdapter._count_payload(request)
    assert request["input"].count(compacted["output"][-1]) == 1
    assert not any(i.get("type") == "reasoning" for i in request["input"][len(window):])
    before = snapshot(trial)
    assert state.recover(trial) == receipt == state.recover(trial)
    assert snapshot(trial) == before
    assert "opaque-compressed-state" not in trial_journal(trial).path.read_text()
    assert receipt["usage"]["output_tokens"] == 40
    assert receipt["compaction_cost_usd"] is receipt["next_input_tokens"] is None


@pytest.mark.parametrize("bad", ["summary", "content", "no_cipher", "unknown", "changed_call",
                                "no_compaction", "duplicate", "unpaired"])
def test_bad_output_is_not_persisted_and_never_silently_pruned(packet, bad):
    _, _, trial = packet
    result = response()
    reasoning = {"type": "reasoning", "id": "rs_bad", "encrypted_content": "opaque"}
    if bad == "summary":
        reasoning["summary"] = [{"type": "summary_text", "text": SECRET}]
        result["output"].append(reasoning)
    elif bad == "content":
        reasoning["content"] = SECRET
        result["output"].append(reasoning)
    elif bad == "no_cipher":
        result["output"][0].pop("encrypted_content")
    elif bad == "unknown":
        result["output"].append({"type": "unknown", "text": SECRET})
    elif bad == "changed_call":
        result["output"].append({"type": "function_call", "call_id": "new_call",
                                  "name": "replace_text", "arguments": SECRET})
    elif bad == "no_compaction":
        result["output"] = [reasoning]
    elif bad == "duplicate":
        result["output"] *= 2
    else:
        result["output"].append({"type": "function_call", "call_id": "call_1",
                                  "name": "read_file", "arguments": '{"path":"public.py"}'})
    receipt = state.record_response(trial, result)
    assert receipt["status"] == "COMPACTION_OUTPUT_CONTRACT_ERROR"
    assert receipt["usage"]["total_tokens"] == 1040
    assert "window_artifact" not in receipt
    assert state.recover(trial) == receipt
    for path in trial.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()


@pytest.mark.parametrize("field,value", [("usage", None), ("input_tokens", -1),
                                        ("total_tokens", 1), ("output_tokens", True)])
def test_invalid_usage_does_not_unlock_a_followup(packet, field, value):
    _, _, trial = packet
    result = response()
    if field == "usage":
        result["usage"] = value
    else:
        result["usage"][field] = value
    receipt = state.record_response(trial, result)
    assert receipt["status"] == "COMPACTION_USAGE_ERROR"
    assert receipt["usage"] is None and "next_request_artifact" not in receipt


def test_pending_attempt_resolves_unknown_once_without_retries(packet):
    _, _, trial = packet
    # Even an orphan output object does not establish provider completion.
    ArtifactStore(trial / "artifacts").put_json(response())
    result = state.recover(trial)
    assert result["status"] == "COMPACTION_OUTCOME_UNKNOWN"
    before = snapshot(trial)
    assert state.recover(trial) == result and before == snapshot(trial)
    with pytest.raises(ContractError, match="already resolved"):
        state.record_response(trial, response())


def test_crash_after_atomic_receipt_recovers_without_reexecution(packet, monkeypatch):
    _, _, trial = packet
    original = DevJournal.append

    def crash(self, event, payload=None):
        if event == "compaction_result_recorded":
            raise KeyboardInterrupt()
        return original(self, event, payload)

    with monkeypatch.context() as patch:
        patch.setattr(DevJournal, "append", crash)
        with pytest.raises(KeyboardInterrupt):
            state.record_response(trial, response())
    assert len(trial_journal(trial).events()) == 1
    assert state.recover(trial)["status"] == "READY_FOR_REVIEW"
    assert len(trial_journal(trial).events()) == 2
    before = snapshot(trial)
    state.recover(trial)
    assert snapshot(trial) == before


def test_crash_before_receipt_never_reexecutes_orphan_output(packet, monkeypatch):
    _, _, trial = packet
    original = ArtifactStore.write_text_immutable

    def crash(self, path, content):
        if Path(path).name == "receipt.json":
            raise KeyboardInterrupt()
        return original(self, path, content)

    with monkeypatch.context() as patch:
        patch.setattr(ArtifactStore, "write_text_immutable", crash)
        with pytest.raises(KeyboardInterrupt):
            state.record_response(trial, response())
    assert list((trial / "artifacts" / "objects").rglob("*"))
    assert state.recover(trial)["status"] == "COMPACTION_OUTCOME_UNKNOWN"


@pytest.mark.parametrize("where", ["runtime", "packet", "window", "request", "receipt"])
def test_tampering_or_runtime_change_prevents_recovery(packet, monkeypatch, where):
    frozen, _, trial = packet
    receipt = state.record_response(trial, response())
    if where == "runtime":
        monkeypatch.setattr(design, "runtime_content_hash", lambda: sha256_json("changed"))
    else:
        path = {"packet": frozen.output / "packet.json", "receipt": trial / "receipt.json",
                "window": Path(receipt["window_artifact"]["path"]),
                "request": Path(receipt["next_request_artifact"]["path"])}[where]
        obj = json.loads(path.read_bytes())
        if isinstance(obj, dict):
            obj["tampered"] = True
        else:
            obj.append({"type": "compaction", "encrypted_content": "changed"})
        path.write_text(canonical_json(obj), encoding="utf-8")
    before = snapshot(trial)
    with pytest.raises((ContractError, RecoveryError)):
        state.recover(trial)
    assert before == snapshot(trial)


def test_concurrent_record_is_rejected(packet):
    _, _, trial = packet
    with (trial_journal(trial).execution_lock(),
          pytest.raises(RecoveryError, match="already active")):
        state.record_response(trial, response())
    assert len(trial_journal(trial).events()) == 1


def test_missing_committed_receipt_is_integrity_error_not_unknown_retry(packet):
    _, _, trial = packet
    state.record_response(trial, response())
    (trial / "receipt.json").unlink()
    before = snapshot(trial)
    with pytest.raises(ContractError, match="receipt is missing"):
        state.recover(trial)
    assert snapshot(trial) == before


def test_large_compaction_item_is_measured_not_truncated_or_assumed_safe(packet):
    _, _, trial = packet
    result = response()
    result["output"][0]["encrypted_content"] = "x" * 1_701_176
    receipt = state.record_response(trial, result)
    assert receipt["after"]["largest_encrypted_chars"] == 1_701_176
    assert artifact(trial, receipt["window_artifact"]) == result["output"]
    assert receipt["automatic_generation_requests"] == 0
    assert receipt["next_input_tokens"] is None


def client(handler):
    return transport.DiagnosticClient(api_key="", client=openai.AsyncOpenAI(
        api_key="mock-not-a-credential", max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False),
    ))


def test_real_sdk_mock_compaction_preserves_items_and_only_uses_supported_parameters(packet):
    frozen, report, trial = packet
    _, values = design.verify(frozen.output, report["packet_hash"])
    visits = []

    async def handler(request):
        visits.append(request)
        assert request.url.path == "/v1/responses/compact"
        assert json.loads(request.content) == values["compact"]
        return httpx.Response(200, json=response(values["control"]["input"][2]))

    adapter = client(handler)
    try:
        result = adapter.responses.compact(**values["compact"], timeout=5)
        receipt = state.record_response(trial, result)
        assert adapter.phase == "compaction_processing"
    finally:
        adapter.close()
    assert receipt["status"] == "READY_FOR_REVIEW"
    assert len(visits) == 1 and state.recover(trial) == receipt


def test_compact_request_whole_body_timeout_cancels_once():
    visits, cancelled = [], []

    class Trickle(httpx.AsyncByteStream):
        async def __aiter__(self):
            try:
                while True:
                    yield b" "
                    await asyncio.sleep(0.005)
            finally:
                cancelled.append(True)

    async def handler(request):
        visits.append(request)
        return httpx.Response(200, stream=Trickle())

    adapter = client(handler)
    try:
        with pytest.raises(transport.RequestWaitExpired):
            adapter.responses.compact(model=count_replay.shared.MODEL, input=[], timeout=0.2)
        assert len(visits) == 1 and cancelled
        assert adapter.phase == "compaction_wait"
        assert not asyncio.all_tasks(adapter.runner.get_loop())
    finally:
        adapter.close()
