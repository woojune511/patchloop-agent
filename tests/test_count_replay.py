from __future__ import annotations

import json
import socket
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError

from diagnostics import count_replay as replay
from patchloop.agent.count_diagnostics import input_count_error_metadata
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.dev.conversation import assemble_model_input, history_metadata
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json

SECRET = "credential-private-spec-hidden-path-reference-patch-plaintext-reasoning-sentinel"


@pytest.fixture(autouse=True)
def no_live_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no credential/client/network/task execution allowed")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(replay.shared, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(replay.shared, "create_openai_client", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "__init__", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "count_input_tokens_v2", forbidden)
    monkeypatch.setattr(OpenAIResponsesAdapter, "execute_request", forbidden)


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    root = tmp_path / "source"
    store = ArtifactStore(root / "artifacts")
    journal = DevJournal(root, "run_dev_frozen")
    public_task = {"task_id": "public-fixture", "goal": "Repair public behavior"}
    envelope = {
        "run_id": journal.run_id, "provider": "openai", "split": "dev-train",
        "model": replay.shared.MODEL, "reasoning_effort": "medium",
        "task_id": "public-fixture", "task_version": 2,
        "task_content_hash": sha256_json("task"), "public_spec_hash": sha256_json(public_task),
        "runtime_hash": sha256_json("old runtime"), "model_hash": sha256_json("model"),
        "credential_file_path_hash": sha256_json(".env path only"),
        "private_path_not_for_projection": SECRET,
    }
    ArtifactStore(root).write_text_immutable(journal.envelope_path, canonical_json(envelope))
    # A harness action must not be confused with a missing native call/output pair.
    for action_id in ("call_1", "call_2", "harness_check"):
        journal.append("action_finished", {"result": {"action_id": action_id}})
    history = [{"type": "reasoning", "id": "rs_1", "summary": [],
                "encrypted_content": "ciphertext-first"}]
    for action_id in ("call_1", "call_2"):
        history.append({"type": "function_call", "call_id": action_id,
                        "name": "read_file", "arguments": '{"path":"public.py"}'})
    for action_id in ("call_1", "call_2"):
        history.append({"type": "function_call_output", "call_id": action_id,
                        "output": canonical_json({"source": "observed public source"})})
    payloads, previous = [], None
    for number in (1, 2):
        state = {
            "public_task": public_task, "current_diff": "observed diff",
            "remaining_budget": {"model": 22 - number},
            "available_tool_names": ["read_file", "run_check", "stop_task"],
            "visible_check_status": [{"check_id": "public-check", "status": "NOT_RUN"}],
        }
        if number == 2:
            state["protocol_correction"] = "Choose an allowed action."
            history = [{"type": "reasoning", "id": "rs_2", "summary": [],
                        "encrypted_content": "ciphertext-second" * 100}]
        items = assemble_model_input(
            system_prompt=DEV_SYSTEM_PROMPT, state=state, history=history, previous_input=previous,
        )
        previous = items
        context_artifact = store.put_json(state)
        turn = {
            "turn_id": f"turn_{number}", "available_tool_names": state["available_tool_names"],
            "context_artifact": context_artifact.model_dump(mode="json"),
            "context_hash": context_artifact.content_hash,
            "model_input_artifact": store.put_json(items).model_dump(mode="json"),
            "model_input_hash": sha256_json(items), "native_history": history_metadata(items),
            "targeted_read_paths": [], "transcript_action_ids": ["call_1", "call_2"],
        }
        journal.append("turn_started", turn)
        request = OpenAIResponsesAdapter.request_payload(
            SimpleNamespace(config=replay.shared.model_config("medium")), items,
            replay.dev_tool_schemas(finish_enabled=False, check_ids=["public-check"],
                                    allowed_tools=state["available_tool_names"], read_paths=[]),
            system_prompt=DEV_SYSTEM_PROMPT,
        )
        payloads.append(OpenAIResponsesAdapter._count_payload(request))
        journal.append("input_count_started", {"turn_id": turn["turn_id"],
                       "count_id": f"count_{number}", "request_hash": sha256_json(request)})
        if number == 1:
            journal.append("input_count_finished", {"turn_id": turn["turn_id"],
                           "count_id": "count_1", "input_tokens": replay.CONTROL_COUNT})
    journal.append("unrelated_future_evidence", {
        "artifact": store.put_text(SECRET).model_dump(mode="json"), "text": SECRET,
    })
    journal.append("terminal", {"terminal": "COUNT_TIMEOUT_OR_UNKNOWN"})
    monkeypatch.setattr(replay, "SOURCE_ID", journal.run_id)
    monkeypatch.setattr(replay, "TURNS", (1, 2))
    monkeypatch.setattr(replay, "COUNT_HASHES", tuple(sha256_json(p) for p in payloads))
    monkeypatch.setattr(replay, "SOURCE_HASHES", {
        ".jsonl": sha256_bytes(journal.path.read_bytes()),
        ".envelope.json": sha256_bytes(journal.envelope_path.read_bytes()),
    })
    return SimpleNamespace(
        root=root, journal=journal, payloads=payloads, output=tmp_path / "packet",
    )


def snapshot(root):
    return {str(p): sha256_bytes(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


def test_freeze_and_two_readonly_rehearsals_preserve_exact_inputs_and_source(frozen):
    before = snapshot(frozen.root)
    prepared = replay.prepare(frozen.root, frozen.output)
    assert prepared == replay.verify(frozen.output, prepared["packet_hash"])
    assert prepared == replay.verify(frozen.output, prepared["packet_hash"])
    assert before == snapshot(frozen.root)
    packet = json.loads((frozen.output / "packet.json").read_bytes())
    assert packet["billing"]["count_cost_usd"] is None
    assert packet["billing"]["live_execution_enabled"] is False
    assert packet["task_acceptance"] == packet["safety_state"] == "NOT_RUN"
    assert prepared["api_requests"] == prepared["task_executions"] == 0
    assert prepared["native_call_output_pairs"] == [2, 2]
    for case, original in zip(packet["cases"], frozen.payloads, strict=True):
        raw = replay.shared.read_source_artifact(frozen.output, case["count_payload_artifact"])
        assert raw == canonical_json(original).encode("utf-8")
        assert "max_output_tokens" not in json.loads(raw)
    for path in frozen.output.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()
    journal_text = next((frozen.output / "runs").glob("*.jsonl")).read_text()
    assert "ciphertext" not in journal_text
    assert "ciphertext" not in (frozen.output / "packet.json").read_text()
    with pytest.raises(ContractError, match="must be new"):
        replay.prepare(frozen.root, frozen.output)


@pytest.mark.parametrize("location", ["packet", "payload", "journal", "envelope"])
def test_tampering_rejected_before_any_dispatch(frozen, location):
    receipt = replay.prepare(frozen.root, frozen.output)
    if location == "packet":
        path = frozen.output / "packet.json"
    elif location == "payload":
        packet = json.loads((frozen.output / "packet.json").read_bytes())
        path = Path(packet["cases"][1]["count_payload_artifact"]["path"])
    else:
        path = frozen.journal.path if location == "journal" else frozen.journal.envelope_path
    path.write_bytes(path.read_bytes() + b" ")
    # Packet whitespace is not a semantic change. Other identity checks use raw bytes.
    if location == "packet":
        packet = json.loads(path.read_bytes())
        packet["protocol"]["sdk_retries"] = 1
        path.write_text(canonical_json(packet), encoding="utf-8")
    with pytest.raises((ContractError, RecoveryError)):
        replay.verify(frozen.output, receipt["packet_hash"])


@pytest.mark.parametrize("change", ["runtime", "tool_order", "credential_path", "billing"])
def test_rehash_does_not_bypass_frozen_contract(frozen, monkeypatch, change):
    receipt = replay.prepare(frozen.root, frozen.output)
    packet_path = frozen.output / "packet.json"
    packet = json.loads(packet_path.read_bytes())
    if change == "runtime":
        monkeypatch.setattr(replay, "runtime_content_hash", lambda: sha256_json("changed"))
    elif change == "tool_order":
        original = replay.dev_tool_schemas
        monkeypatch.setattr(replay, "dev_tool_schemas", lambda **kw: list(reversed(original(**kw))))
    elif change == "credential_path":
        packet["source_contract"]["credential_file_path_hash"] = sha256_json("different .env")
    else:
        packet["billing"]["live_execution_enabled"] = True
    packet_path.write_text(canonical_json(packet), encoding="utf-8")
    with pytest.raises(ContractError):
        replay.verify(frozen.output, sha256_json(packet))
    assert receipt["api_requests"] == 0


def test_no_packet_created_on_source_mismatch_or_unsafe_destination(frozen):
    for target in (frozen.root, frozen.root / "new", frozen.root.parent):
        with pytest.raises(ContractError, match="outside"):
            replay.prepare(frozen.root, target)
    frozen.journal.path.write_bytes(frozen.journal.path.read_bytes() + b" ")
    with pytest.raises(ContractError, match="source identity"):
        replay.prepare(frozen.root, frozen.output)
    assert not frozen.output.exists()


@pytest.mark.parametrize("change", ["reasoning", "call_order", "missing_prior", "context"])
def test_source_integrity_includes_reasoning_native_order_and_observation(frozen, change):
    events, envelope = replay.source_events(frozen.root)
    turn = next(e["payload"] for e in events if e["event_type"] == "turn_started")
    store = ArtifactStore(frozen.root / "artifacts")
    items = json.loads(replay.shared.read_source_artifact(
        frozen.root, turn["model_input_artifact"],
    ))
    if change == "reasoning":
        next(i for i in items if i.get("type") == "reasoning")["summary"] = [SECRET]
    elif change == "call_order":
        next(i for i in items if i.get("type") == "function_call_output")["call_id"] = "call_2"
    elif change == "missing_prior":
        events[0]["payload"]["result"]["action_id"] = "not_observed"
    else:
        context = json.loads(replay.shared.read_source_artifact(
            frozen.root, turn["context_artifact"],
        ))
        context["current_diff"] = "future diff"
        artifact = store.put_json(context)
        turn["context_artifact"] = artifact.model_dump(mode="json")
        turn["context_hash"] = artifact.content_hash
    turn["model_input_artifact"] = store.put_json(items).model_dump(mode="json")
    turn["model_input_hash"] = sha256_json(items)
    turn["native_history"] = history_metadata(items)
    with pytest.raises(ContractError):
        replay.cutoff_request(events, envelope, frozen.root, 1)


def success(index, count):
    return {"case_id": replay.CASE_IDS[index], "status": "succeeded", "input_tokens": count}


@pytest.mark.parametrize("first", [None, -1, True, "97810"])
def test_invalid_count_is_not_success(first):
    with pytest.raises(ContractError, match="invalid input token"):
        replay.protocol_state([success(0, first)])


@pytest.mark.parametrize("fail_at,status", [(0, "failed"), (0, "started"), (1, "failed"),
                                            (1, "started"), (0, "changed_count"), (None, None)])
def test_mock_sequence_stops_without_retry_or_third_request(fail_at, status):
    receipts, attempts = [], []
    while replay.protocol_state(receipts)["next_case"] is not None:
        index = len(receipts)
        attempts.append(replay.CASE_IDS[index])
        if fail_at == index and status != "changed_count":
            receipts.append({"case_id": replay.CASE_IDS[index], "status": status})
        else:
            receipts.append(success(index, replay.CONTROL_COUNT + (status == "changed_count")))
    result = replay.protocol_state(receipts)
    assert len(attempts) == (1 if fail_at == 0 else 2)
    assert len(attempts) == len(set(attempts))
    assert result["result"] == {
        "failed": "STOP_ERROR", "started": "UNKNOWN", "changed_count": "BASELINE_NOT_REPRODUCED",
        None: "NOT_REPRODUCED",
    }[status]
    assert result["next_case"] is None


def test_dispatch_after_error_or_interruption_or_control_mismatch_rejects():
    for receipt in (
        {"case_id": replay.CASE_IDS[0], "status": "failed"},
        {"case_id": replay.CASE_IDS[0], "status": "started"},
        success(0, replay.CONTROL_COUNT + 1),
    ):
        with pytest.raises(ContractError, match="dispatch after"):
            replay.protocol_state([receipt, success(1, 5)])
    with pytest.raises(ContractError, match="too many"):
        replay.protocol_state([success(0, replay.CONTROL_COUNT)] * 3)
    with pytest.raises(ContractError, match="order"):
        replay.protocol_state([success(1, 5)])


def test_safe_error_receipt_excludes_provider_message_and_encrypted_content():
    error = BadRequestError(
        SECRET, response=httpx.Response(400, request=httpx.Request(
            "POST", replay.PROTOCOL["endpoint"], headers={"Authorization": SECRET},
            json={"input": "ciphertext-only-in-request"},
        )), body={"message": SECRET, "code": "invalid_encrypted_content",
                  "type": "invalid_request_error", "param": "input[78].encrypted_content"},
    )
    receipt = {"case_id": replay.CASE_IDS[0], "status": "failed",
               "error": input_count_error_metadata(error)}
    assert SECRET not in canonical_json(receipt)
    assert "ciphertext-only-in-request" not in canonical_json(receipt)
    assert receipt["error"]["code"] == "invalid_encrypted_content"
    assert replay.protocol_state([receipt])["next_case"] is None


def test_cli_has_no_execution_or_approval_mode(monkeypatch):
    monkeypatch.setattr("sys.argv", ["count_replay", "collect", "--approved"])
    with pytest.raises(SystemExit) as error:
        replay.main()
    assert error.value.code == 2
