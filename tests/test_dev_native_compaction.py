from __future__ import annotations

import copy
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from test_dev_compaction import Client, response
from test_dev_context_window import build, group, read
from test_dev_conversation_v22 import _provider_smoke
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash

from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig
from patchloop.deadline import ExecutionDeadline
from patchloop.dev import native_compaction as compact
from patchloop.dev import runner
from patchloop.dev.compacted_window import CompactedWindow
from patchloop.dev.compaction_cost import RATES
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import (
    WINDOW_POLICY,
    WINDOW_RULES,
    assemble_model_input,
    history_metadata,
    reconstruct_state,
    validate_model_input,
)
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("real provider transport is forbidden")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def configured(monkeypatch, tmp_path, **changes):
    request, inputs, counted = _provider_smoke(monkeypatch, tmp_path)
    request = request.model_copy(
        update={
            "model": "gpt-5.4-mini-2026-03-17",
            "context_policy": WINDOW_POLICY,
            "compact_at_input_tokens": 1,
            "accept_compaction_model_limit_reservation": True,
            **changes,
        }
    )
    clients = []

    def factory(**kwargs):
        client = Client()
        clients.append(client)
        return client

    monkeypatch.setattr(runner, "BoundedResponsesClient", factory)
    return request, inputs, counted, clients


@pytest.mark.parametrize("retained", ["none", "messages", "all", "normalized"])
def test_whole_seed_and_public_evidence_reenter_once_without_historical_authority(retained):
    source = build(
        {
            "current_sources": [group()],
            "public_observation": "PUBLIC_FACT",
            "working_notes": {"open_question": "OLD_NOTE"},
            "visible_check_status": {"status": "PASS"},
        },
        previous=build(),
        history=read(),
    )
    kept = (
        []
        if retained == "none"
        else [i for i in source if "role" in i]
        if retained in {"messages", "normalized"}
        else source
    )
    kept = copy.deepcopy(kept)
    if retained == "normalized":
        for item in kept:
            item["type"] = "message"
            item["content"] = [{"type": "input_text", "text": item["content"]}]
    output = response(*kept)["output"]
    window = CompactedWindow(source, output, WINDOW_RULES)
    state = {
        "public_task": window.public_task,
        "remaining_budget": {"model": 2},
        "visible_check_status": {"status": "NOT_RUN"},
    }
    items = assemble_model_input(
        system_prompt="unused", state=state, history=[], context_policy=WINDOW_POLICY, window=window
    )
    assert items[: len(output)] == output
    assert window.rules.inventory(items) == WINDOW_RULES.inventory(source)
    assert reconstruct_state(items, context_policy=WINDOW_POLICY, window=window) == state
    metadata = history_metadata(items, context_policy=WINDOW_POLICY, window=window)
    assert (
        validate_model_input(items, metadata, context_policy=WINDOW_POLICY, window=window) == items
    )
    exchanges = list(
        public_exchanges(window.delivery_history(items), archive_kind=PUBLIC_EVIDENCE_KIND)
    )
    assert [e["call_id"] for e in exchanges] == ["read", "read"]
    newer = assemble_model_input(
        system_prompt="unused",
        state={**state, "remaining_budget": {}},
        previous_input=items,
        history=read("helper", path="helper.py"),
        context_policy=WINDOW_POLICY,
        window=window,
    )
    assert newer[: len(output)] == output
    assert (
        history_metadata(newer, context_policy=WINDOW_POLICY, window=window)["state_update_count"]
        == 1
    )
    assert "PRIVATE_HIDDEN_REFERENCE_PLAINTEXT_REASONING_SENTINEL" not in canonical_json(newer)


@pytest.mark.parametrize(
    "threshold,remaining,cap,correction,expected",
    [
        (100, 5, "1.20", None, True),
        (101, 5, "1.20", None, False),
        (100, 4, "1.20", None, False),
        (100, 5, "0.50", None, False),
        (100, 5, "1.20", {"code": "incomplete"}, False),
    ],
)
def test_threshold_and_minimum_completion_reservation(
    tmp_path, threshold, remaining, cap, correction, expected
):
    journal = DevJournal(tmp_path, "run_dev_eligibility")
    journal.append(
        "turn_decision_recorded", {"turn_id": "t", "tool_calls": [{"name": "read_file"}]}
    )
    journal.append("tool_batch_finished", {"turn_id": "t", "action_ids": ["a"]})
    assert (
        compact.eligible(
            journal,
            threshold=threshold,
            input_tokens=100,
            remaining_model_calls=remaining,
            minimum_completion_calls=4,
            ledger=DevCostLedger(Decimal(cap), RATES),
            deadline=ExecutionDeadline.from_remaining(20),
            correction=correction,
        )
        is expected
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"context_policy": "append-v1"},
        {"accept_compaction_model_limit_reservation": False},
        {"model": "gpt-5.4-mini"},
        {"compact_at_input_tokens": 272_000},
        {"compact_at_input_tokens": 0},
        {"compact_at_input_tokens": None},
    ],
)
def test_opt_in_contract_is_exact_and_explicit(tmp_path, monkeypatch, changes):
    request, *_ = configured(monkeypatch, tmp_path, **changes)
    with pytest.raises(ValueError):
        DevRunRequest.model_validate(request.model_dump())


@pytest.mark.parametrize(
    "boundary",
    [
        None,
        "model_input_prepared",
        "input_count_finished",
        "compaction_prepared",
        "compaction_finished",
        "context_window_activated",
        "turn_started",
        "provider_call_finished",
        "turn_decision_recorded",
        "action_finished",
        "tool_batch_finished",
    ],
)
def test_runner_compact_recount_resume_and_exchange_exactness(tmp_path, monkeypatch, boundary):
    request, inputs, counted, clients = configured(monkeypatch, tmp_path)
    if boundary:
        _crash_journal_once(monkeypatch, event_type=boundary, when="after")
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(request)
        run_id = _enveloped_run_id(request.state_root)
        request = request.model_copy(update={"resume_run_id": run_id})
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert result["accepted_mutations"] == 1
    assert len(clients) == len(clients[0].calls) == 1
    assert len(inputs) == 3 and len(counted) == 4
    assert inputs[0] == counted[0] and inputs[1:] == counted[2:]
    assert result["call_counts"] == {
        "model": 4,
        "decision": 3,
        "compaction": 1,
        "input_count": 4,
        "tool": 3,
    }
    journal = DevJournal(request.state_root, result["run_id"])
    store = ArtifactStore(request.state_root / "artifacts")
    activation, window = compact.active_window(journal, store)
    assert inputs[1][: len(window.seed)] == window.seed
    for supplied in inputs[1:]:
        public = list(
            public_exchanges(window.delivery_history(supplied), archive_kind=PUBLIC_EVIDENCE_KIND)
        )
        assert (
            len([e for e in public if e.get("type") == "function_call" and e["call_id"] == "read"])
            == 1
        )
    assert (
        len(
            [
                e
                for e in journal.events()
                if e["event_type"] == "action_finished" and e["payload"]["action_id"] == "edit"
            ]
        )
        == 1
    )
    for event in journal.events():
        if event["event_type"] == "turn_started":
            runner._load_active_model_input(event["payload"], store, context_policy=WINDOW_POLICY)
    assert result["cost_nanos"] == sum(p["cost_nanos"] for p in journal.provider_usage())
    before = journal.path.read_bytes()
    assert (
        runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"]}))["runs"][0]
        == result
    )
    assert journal.path.read_bytes() == before


def test_threshold_noop_does_not_add_a_count_or_compaction(tmp_path, monkeypatch):
    request, inputs, counted, clients = configured(
        monkeypatch, tmp_path, compact_at_input_tokens=271_999
    )
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED" and not clients
    assert len(inputs) == len(counted) == 3
    assert inputs == counted


def test_compacted_authority_supersedes_the_retained_no_compaction_system_description():
    source = build(previous=build(), history=read())
    output = response(*source)["output"]
    window = CompactedWindow(source, output, WINDOW_RULES)
    assert "no compaction occurs" in source[0]["content"]
    assert window.base[:len(output)] == output
    authority = window.base[-1]
    assert authority["role"] == "system"
    assert "supersedes the earlier no-compaction" in authority["content"]
    assert "including the exact public_task" in authority["content"]
    assert "Missing fields are absent, never inherited" in authority["content"]


@pytest.mark.parametrize("boundary", ["compaction_started", "compaction_usage_recorded"])
def test_incomplete_compaction_never_retries_or_runs_a_pending_mutation(
    tmp_path, monkeypatch, boundary
):
    request, inputs, counted, clients = configured(monkeypatch, tmp_path)
    _crash_journal_once(monkeypatch, event_type=boundary, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    monkeypatch.setattr(
        runner, "load_exact_openai_api_key", lambda *a: pytest.fail("loaded credential")
    )
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert len(inputs) == 1 and len(counted) == 2 and len(clients) == 1
    assert result["accepted_mutations"] == 0
    journal = DevJournal(request.state_root, run_id)
    assert result["cost_nanos"] == sum(p["cost_nanos"] for p in journal.provider_usage())


@pytest.mark.parametrize(
    "event_type",
    ["provider_call_finished", "turn_decision_recorded", "action_finished", "tool_batch_finished"],
)
def test_post_compaction_pending_mutation_is_replayed_once(tmp_path, monkeypatch, event_type):
    request, inputs, counted, clients = configured(monkeypatch, tmp_path)
    _crash_journal_once(
        monkeypatch,
        event_type=event_type,
        when="after",
        predicate=lambda p: (
            p.get("action_id") == "edit"
            or p.get("action_ids") == ["edit"]
            or any(c["action_id"] == "edit" for c in p.get("tool_calls", []))
        ),
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED" and result["accepted_mutations"] == 1
    assert len(inputs) == 3 and len(counted) == 4 and len(clients) == 1


@pytest.mark.parametrize("damage", ["seed", "receipt", "source", "prepared"])
def test_activation_integrity_fails_before_credentials_or_new_actions(
    tmp_path, monkeypatch, damage
):
    request, inputs, counted, clients = configured(monkeypatch, tmp_path)
    _crash_journal_once(monkeypatch, event_type="compaction_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    journal = DevJournal(request.state_root, run_id)
    store = ArtifactStore(request.state_root / "artifacts")
    events = {e["event_type"]: e["payload"] for e in journal.events()}
    target = {
        "seed": Path(events["compaction_response_recorded"]["window_artifact"]["path"]),
        "receipt": store.root / "compaction" / f"{run_id}.json",
        "source": Path(events["compaction_prepared"]["source_input"]["path"]),
        "prepared": Path(events["model_input_prepared"]["artifact"]["path"]),
    }[damage]
    target.write_bytes(b"corrupted test fixture")
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda *a: pytest.fail("credential"))
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "PROVIDER_CONTINUATION_ERROR"
    assert len(inputs) == 1 and len(counted) == 2 and len(clients) == 1


@pytest.mark.parametrize("when", ["before", "after"])
def test_count_unknown_is_not_replaced_by_compaction(tmp_path, monkeypatch, when):
    request, inputs, counted, clients = configured(monkeypatch, tmp_path)
    _crash_journal_once(monkeypatch, event_type="input_count_started", when=when)
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    if when == "after":
        assert result["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"
        assert not inputs and not counted and not clients
    else:
        assert result["terminal"] == "AGENT_STOPPED"
        assert len(inputs) == 3 and len(counted) == 4 and len(clients) == 1


def test_parallel_public_reentry_and_actual_request_keep_whole_provider_output():
    a, b = read("a"), read("b", path="helper.py")
    source = build(previous=build(), history=[a[0], b[0], a[1], b[1]])
    output = response()["output"]
    window = CompactedWindow(source, output, WINDOW_RULES)
    state = {"public_task": window.public_task, "remaining_budget": {"model": 3}}
    items = assemble_model_input(
        system_prompt="unused", state=state, history=[], context_policy=WINDOW_POLICY, window=window
    )
    config = ModelConfig(
        provider="openai",
        model_id="gpt-5.4-mini-2026-03-17",
        reasoning_effort="medium",
        reasoning_continuation="encrypted-v1",
        transport_max_retries=0,
        max_output_tokens=25_000,
    )
    adapter = OpenAIResponsesAdapter(
        config, api_key="unused", client=SimpleNamespace(max_retries=0)
    )
    request = adapter.request_payload(items, [], system_prompt="unused")
    assert request["input"][: len(output)] == output
    assert request["store"] is False and request["max_output_tokens"] == 25_000
    exchange = list(public_exchanges(items, archive_kind=PUBLIC_EVIDENCE_KIND))
    assert [(e["type"], e["call_id"]) for e in exchange] == [
        ("function_call", "a"),
        ("function_call", "b"),
        ("function_call_output", "a"),
        ("function_call_output", "b"),
    ]
    assert not [i for i in items if i.get("type") == "function_call"]


def test_compaction_time_and_shared_cost_survive_downtime(tmp_path, monkeypatch):
    request, inputs, counted, clients = configured(monkeypatch, tmp_path)
    now = [0.0]
    monkeypatch.setattr(runner, "monotonic", lambda: now[0])
    original = Client.compact

    def compacting(self, **kwargs):
        now[0] += 3
        return original(self, **kwargs)

    monkeypatch.setattr(Client, "compact", compacting)
    _crash_journal_once(monkeypatch, event_type="context_window_activated", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    run_id = _enveloped_run_id(request.state_root)
    journal = DevJournal(request.state_root, run_id)
    assert journal.latest_active_elapsed_ms() == 3000
    before_cost = sum(p["cost_nanos"] for p in journal.provider_usage())
    now[0] += 9_000  # This is downtime, not another 9,000 active seconds.
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED" and result["cost_nanos"] > before_cost
    assert journal.latest_active_elapsed_ms() == 3000
    assert len(clients) == 1


@pytest.mark.parametrize("maximum,compactions", [(4, 0), (5, 1)])
def test_runner_keeps_B_calls_and_only_compacts_with_B_plus_one(
    tmp_path, monkeypatch, maximum, compactions
):
    request, inputs, counted, clients = configured(monkeypatch, tmp_path)
    request = request.model_copy(
        update={
            "limits": request.limits.model_copy(
                update={
                    "max_model_calls": maximum,
                }
            )
        }
    )
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED", result
    assert result["call_counts"]["compaction"] == len(clients) == compactions
    assert len(inputs) == 3 and len(counted) == 3 + compactions
