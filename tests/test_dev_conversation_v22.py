from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from native_history_support import input_context, start_turn
from test_dev_runner import (
    _crash_journal_once,
    _enveloped_run_id,
    _live_request,
    _patch_live_boundaries,
    _SimulatedCrash,
)

import patchloop.dev.runner as runner
from patchloop.agent.model import (
    EncryptedReasoningContinuationItem as ProviderReasoning,
)
from patchloop.agent.model import FunctionCallContinuationRef as ProviderCallRef
from patchloop.agent.model import ModelTurn, ModelTurnError, OpenAIResponsesAdapter
from patchloop.agent.model import RequestedTool as ProviderCall
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig, TaskEnvironment
from patchloop.dev.contracts import (
    DevToolResult,
    EncryptedReasoningContinuationItem,
    FunctionCallContinuationRef,
    ProviderContinuationArtifact,
    PublicTurnDecision,
    RequestedTool,
)
from patchloop.dev.conversation import TASK_MESSAGE, assemble_model_input, history_metadata
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_json


def _context(journal, marker):
    return canonical_json({
        "public_task": {"task_id": "public-synthetic"},
        "protocol_correction": {"message": marker},
        "latest_tool_results": [r.model_dump(mode="json")
                                for r in journal.latest_tool_batch_results()],
    })


def _decision(journal, store, number, *, parallel=1, incomplete=False):
    turn_id = f"turn-{number}"
    start_turn(journal, store, turn_id, context=_context(journal, f"snapshot-{number}"))
    calls = [RequestedTool(
        name="read_file", action_id=f"read-{number}-{i}",
        arguments={"path": "src.py", "start_line": i + 1, "end_line": i + 1},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis=f"Question {number}-{i}", evidence_goal="Observe source",
        ),
    ) for i in range(0 if incomplete else parallel)]
    order = []
    for i in range(max(1, len(calls))):
        order.append(EncryptedReasoningContinuationItem(
            id=f"rs-{number}-{i}", encrypted_content=f"opaque-{number}-{i}",
            status="incomplete" if incomplete else "completed",
        ))
        if calls:
            order.append(FunctionCallContinuationRef(action_id=calls[i].action_id))
    ref = runner._store_provider_continuation(
        store, ProviderContinuationArtifact(output_order=order),
    )
    journal.append("turn_decision_recorded", {
        "turn_id": turn_id, "tool_calls": [c.model_dump(mode="json") for c in calls],
        "continuation_ref": ref.model_dump(mode="json"), "output_item_types": ["reasoning"],
    })
    if incomplete:
        journal.append("protocol_correction", {
            "turn_id": turn_id, "code": "incomplete_response", "message": "max_output_tokens",
        })
    else:
        for call in calls:
            result = DevToolResult(
                action_id=call.action_id, input_hash=sha256_json(call.arguments),
                tool=call.name, status="succeeded",
                output={"public_observation": f"observed-{call.action_id}"},
            )
            journal.append("action_finished", {"result": result.model_dump(mode="json")})
        journal.append("tool_batch_finished", {
            "turn_id": turn_id, "action_ids": [call.action_id for call in calls],
        })
    return ref


def _input(journal, store, marker="current"):
    return runner._build_model_input(
        journal=journal, artifact_store=store, context=_context(journal, marker),
        latest_tool_results=journal.latest_tool_batch_results(),
    )


def test_initial_state_preserves_context_field_priority_and_does_not_mutate_input():
    state = {"workflow_gate": "needs_mutation", "remaining_budget": {}, "public_task": {}}
    before = copy.deepcopy(state)
    items = assemble_model_input(system_prompt="system", state=state, history=[])
    assert list(input_context(items)) == list(state)
    assert state == before


def test_one_user_boundary_replays_entire_episode_and_appends_current_state(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_episode")
    store = ArtifactStore(tmp_path / "artifacts")
    initial = _input(journal, store)
    _decision(journal, store, 1, parallel=2)
    first = _input(journal, store, "snapshot-2")
    _decision(journal, store, 2)
    second = _input(journal, store, "snapshot-3")
    _decision(journal, store, 3, incomplete=True)
    third = _input(journal, store)
    for items, marker in [(initial, "current"), (first, "snapshot-2"),
                          (second, "snapshot-3"), (third, "current")]:
        assert [item.get("role") for item in items[:3]] == ["system", "developer", "user"]
        assert items[2] == TASK_MESSAGE
        assert sum(item.get("role") == "user" for item in items) == 1
        assert all("role" not in item or item["role"] == "developer" for item in items[3:])
        assert items[0]["content"].startswith(DEV_SYSTEM_PROMPT)
        assert "data, not instructions" in items[0]["content"]
        assert input_context(items)["protocol_correction"]["message"] == marker
    assert second[3:3 + len(first[3:])] == first[3:]
    assert third[3:3 + len(second[3:])] == second[3:]
    assert second[:3] == first[:3] == third[:3]
    assert [item["type"] for item in first[3:] if "type" in item] == [
        "reasoning", "function_call", "reasoning", "function_call",
        "function_call_output", "function_call_output",
    ]
    assert history_metadata(third)["reasoning_item_count"] == 4
    assert [item for item in third if item.get("type") == "reasoning"][-1]["id"] == "rs-3-0"
    assert input_context(third)["latest_tool_results"] == []
    assert json.dumps(third).count("observed-read-2-0") == 1
    before = journal.path.read_bytes()
    assert _input(DevJournal(tmp_path, journal.run_id), store) == third
    assert journal.path.read_bytes() == before
    # Ciphertext stays in content-addressed inputs/continuations, not JSONL.
    assert "opaque-" not in before.decode()


@pytest.mark.parametrize("damage", ["ciphertext", "missing", "action_order", "input", "legacy"])
def test_damaged_older_history_is_not_silently_reset(tmp_path, damage):
    journal = DevJournal(tmp_path, "run_dev_bad_history")
    store = ArtifactStore(tmp_path / "artifacts")
    reference = _decision(journal, store, 1)
    _decision(journal, store, 2)
    if damage == "ciphertext":
        Path(reference.artifact.path).write_text("damaged", encoding="utf-8")
    elif damage == "missing":
        Path(reference.artifact.path).unlink()
    elif damage == "action_order":
        events = copy.deepcopy(journal.events())
        decision = next(e for e in events if e["event_type"] == "turn_decision_recorded")
        decision["payload"]["tool_calls"][0]["action_id"] = "different"
        journal = SimpleNamespace(events=lambda: events,
                                  latest_tool_batch_results=journal.latest_tool_batch_results)
    else:
        started = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"][-1]
        if damage == "input":
            Path(started["model_input_artifact"]["path"]).write_text("damaged", encoding="utf-8")
        else:
            old = store.put_json([{"role": "system", "content": "old"},
                                  {"role": "user", "content": "{}"}])
            with pytest.raises(runner._ProviderContinuationError):
                runner._load_active_model_input({
                    "model_input_artifact": old.model_dump(mode="json"),
                    "model_input_hash": old.content_hash,
                }, store)
            return
    with pytest.raises(runner._ProviderContinuationError):
        _input(journal, store)


@pytest.mark.parametrize("metadata,expected", [
    (None, None), ({"context": "current_turn"}, "current_turn"),
    (SimpleNamespace(context="all_turns"), "all_turns"),
    ({"context": "unrecognized-provider-value"}, None),
])
def test_effective_reasoning_mode_is_observed_not_requested_or_inferred(metadata, expected):
    response = SimpleNamespace(
        id="response", status="completed", reasoning=metadata,
        output=[SimpleNamespace(
            type="reasoning", id="rs", encrypted_content="cipher", status="completed",
            summary=["PLAINTEXT_REASONING_SENTINEL"], content="PLAINTEXT_REASONING_SENTINEL",
        )],
        usage=SimpleNamespace(input_tokens=9, output_tokens=3),
    )
    adapter = OpenAIResponsesAdapter(ModelConfig(
        provider="openai", model_id="gpt-5.4-mini-2026-03-17",
        reasoning_continuation="encrypted-v1", reasoning_effort="medium",
        transport_max_retries=0,
    ), api_key="unused", client=SimpleNamespace(
        max_retries=0, responses=SimpleNamespace(create=lambda **kwargs: response),
    ))
    payload = adapter.request_payload([], [], system_prompt="test")
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["store"] is False
    turn = adapter.execute_request(payload, requested_input_tokens=9)
    converted = runner._turn_from_openai(turn)
    assert converted.response_reasoning_context == expected
    assert "PLAINTEXT_REASONING_SENTINEL" not in repr(turn)
    assert "PLAINTEXT_REASONING_SENTINEL" not in converted.model_dump_json()
    assert "PLAINTEXT_REASONING_SENTINEL" not in converted.provider_continuation.model_dump_json()


def _provider_smoke(monkeypatch, tmp_path):
    """Actual runner/admission path, deterministic provider and local sandbox only."""
    request = _live_request(tmp_path, repeat=1, cap="1.20").model_copy(update={
        "task": repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
    })
    _patch_live_boundaries(monkeypatch)
    monkeypatch.setattr(runner, "_live_task_is_admitted", lambda *args: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *args, **kwargs: LocalSandbox())
    # Use real managed smoke checkout; no API or Docker authority is exercised.
    from patchloop.repository import WorkspaceManager

    monkeypatch.setattr(runner, "WorkspaceManager", WorkspaceManager)
    task_dir, package = runner._resolve_task_file(request.task)
    package = package.model_copy(update={"environment": TaskEnvironment(
        evaluator_image="test/image@sha256:" + "a" * 64, image_digest="sha256:" + "a" * 64,
    )})
    monkeypatch.setattr(runner, "_resolve_task_file", lambda task: (task_dir, package))
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    specs = [
        ("read_file", "read", {"path": mutation.path, "start_line": 1, "end_line": 40}, "inspect"),
        ("replace_text", "edit", {
            "path": mutation.path, "old_text": mutation.old_text, "new_text": mutation.new_text,
            "occurrence": 1, "hypothesis": mutation.hypothesis,
            "expected_behavior": mutation.expected_behavior,
        }, "mutate"),
        ("stop_task", "stop", {"reason_code": "insufficient_public_evidence",
                               "summary": "End deterministic replay test."}, "stop"),
    ]
    requests = []
    counted = []

    class Provider:
        def __init__(self, config, *, api_key):
            pass

        def request_payload(self, context, tools, *, system_prompt):
            return {"input": context, "tools": tools}

        def count_input_tokens_v2(self, request, *, timeout_seconds):
            counted.append(copy.deepcopy(request["input"]))
            return len(canonical_json(request["input"])) // 4

        def execute_request(self, request, *, requested_input_tokens, timeout_seconds):
            index = len(requests)
            requests.append(copy.deepcopy(request["input"]))
            name, action_id, arguments, mode = specs[index]
            call = ProviderCall(name, action_id, {**arguments, "turn_decision": {
                "mode": mode, "basis": "Use the previous public observation.",
                "evidence_goal": "Observe source" if mode == "inspect" else None,
            }})
            return ModelTurn(
                tool_calls=[call], input_tokens=requested_input_tokens, output_tokens=10,
                response_reasoning_context="current_turn", output_item_types=("reasoning",),
                provider_continuation=(ProviderReasoning(f"rs-{index}", f"cipher-{index}"),
                                       ProviderCallRef(action_id)),
            )

    monkeypatch.setattr(runner, "OpenAIResponsesAdapter", Provider)
    return request, requests, counted


@pytest.mark.parametrize("boundary", [
    "provider_call_finished", "turn_decision_recorded", "action_finished", "tool_batch_finished",
])
def test_resume_appends_each_exchange_once_without_duplicate_provider_or_mutation(
    tmp_path, monkeypatch, boundary,
):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)

    def second_turn(payload):
        return (payload.get("action_id") == "edit"
                or payload.get("action_ids") == ["edit"]
                or any(c["action_id"] == "edit" for c in payload.get("tool_calls", [])))

    _crash_journal_once(monkeypatch, event_type=boundary, when="after", predicate=second_turn)
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    resumed = request.model_copy(update={"resume_run_id": run_id})
    result = runner.run_dev(resumed)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED"
    assert result["accepted_mutations"] == 1
    assert len(inputs) == len(counted) == 3
    assert inputs == counted  # Full history is what admission counts, not just latest context.
    assert inputs[2][:len(inputs[1])] == inputs[1]
    assert [item["call_id"] for item in inputs[2] if item.get("type") == "function_call"] == [
        "read", "edit",
    ]
    journal = DevJournal(request.state_root, run_id)
    rows = journal.events()
    assert len([e for e in rows if e["event_type"] == "action_finished"
                and e["payload"]["action_id"] == "edit"]) == 1
    for event in rows:
        if event["event_type"] in {"provider_call_finished", "turn_decision_recorded"}:
            assert event["payload"]["response_reasoning_context"] == "current_turn"
        if event["event_type"] == "turn_started":
            saved = runner._load_active_model_input(event["payload"],
                                                   ArtifactStore(request.state_root / "artifacts"))
            assert event["payload"]["native_history"] == history_metadata(saved)
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before and len(inputs) == 3
    assert "hidden-multiline-csv" not in json.dumps(inputs)
    assert "reference.patch" not in json.dumps(inputs)


@pytest.mark.parametrize("damage", ["older_reasoning", "pending_input"])
def test_resume_integrity_failure_precedes_pending_mutation_and_next_count(
    tmp_path, monkeypatch, damage,
):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)
    _crash_journal_once(
        monkeypatch, event_type="provider_call_finished", when="after",
        predicate=lambda p: any(c["action_id"] == "edit" for c in p.get("tool_calls", [])),
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    journal = DevJournal(request.state_root, run_id)
    rows = journal.events()
    if damage == "older_reasoning":
        event = next(e for e in rows if e["event_type"] == "provider_call_finished")
        artifact = event["payload"]["continuation_ref"]["artifact"]
    else:
        artifact = [e for e in rows if e["event_type"] == "turn_started"][-1]["payload"][
            "model_input_artifact"
        ]
    Path(artifact["path"]).write_text("corrupted test artifact", encoding="utf-8")
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert result["accepted_mutations"] == 0
    assert len(inputs) == len(counted) == 2
    assert not [e for e in journal.events() if e["event_type"] == "action_started"
                and e["payload"].get("action_id") == "edit"]


def test_billing_uncertainty_keeps_priority_over_missing_reasoning_on_resume(tmp_path, monkeypatch):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)
    provider = runner.OpenAIResponsesAdapter
    execute = provider.execute_request

    def uncertain(self, *args, **kwargs):
        turn = execute(self, *args, **kwargs)
        return replace(turn, tool_calls=[], provider_continuation=(),
                       error=ModelTurnError("input_token_count_mismatch", "uncertain usage"))

    monkeypatch.setattr(provider, "execute_request", uncertain)
    _crash_journal_once(monkeypatch, event_type="provider_call_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["call_counts"]["tool"] == 0
    assert len(inputs) == len(counted) == 1
