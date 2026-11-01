"""Cumulative continuation budgets; all provider traffic is local synthetic HTTP."""
from __future__ import annotations

import json
import shutil
import socket
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import yaml
from test_checkpoint_continuation import call, stop_steps
from test_observation_comparison import resolver
from test_rate_limit_retry import rejection, response, transport

from diagnostics import observation_exposure as diagnostic
from diagnostics.checkpoint_continuation import ScriptedClient, inherited_reads
from diagnostics.declaration_checkpoint import Source
from patchloop.agent import rate_limit_retry
from patchloop.agent.model import OpenAIResponsesAdapter
from patchloop.agent.request_transport import RequestWaitExpired
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.util import sha256_bytes


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    root = tmp_path_factory.mktemp("continuation-budget-source")
    task = root / "task"
    shutil.copytree(repository_root() / "tasks/smoke/csv-quoted-newline", task)
    public = task / "public.yaml"
    spec = yaml.safe_load(public.read_text(encoding="utf-8"))
    spec["split"] = "dev-train"
    spec["constraints"].update(max_changed_files=3, max_diff_lines=80,
                               public_api_changes_allowed=True)
    public.write_text(yaml.safe_dump(spec), encoding="utf-8")
    clock = [0.0]

    def edit(action_id, path, old_text, new_text):
        row = call("edit_files", {
            "edits": [{"path": path, "old_text": old_text, "new_text": new_text,
                       "occurrence": 1}],
            "undo_action_id": None,
            "hypothesis": "Restore the exact accepted public file transaction.",
            "expected_behavior": "Preserve the created helper without reapplying rejected edits.",
        }, "mutate")
        row["action_id"] = action_id
        return row

    read = call("read_file", {"path": "mini_data_utils/csvlite.py",
                              "start_line": 1, "end_line": 90}, "inspect")
    read["arguments"]["turn_decision"]["evidence_goal"] = "Observe the exact edit target."
    created = call("read_file", {"path": "mini_data_utils/resumed_helper.py",
                                 "start_line": 1, "end_line": 10}, "inspect")
    created["action_id"] = "read-created"
    created["arguments"]["turn_decision"]["evidence_goal"] = "Observe the accepted helper."
    accepted = edit("accepted-edit", "mini_data_utils/resumed_helper.py", None, "VALUE = 7\n")
    accepted["arguments"]["edits"].append({
        "path": "mini_data_utils/csvlite.py", "old_text": "physical_line",
        "new_text": "record_line", "occurrence": "all",
    })
    client = ScriptedClient([
        [read],
        [edit("rejected-edit", "mini_data_utils/csvlite.py", "ABSENT_ANCHOR", "invalid")],
        [accepted],
        [created],
    ])
    original_create = client.create

    def create(**kwargs):
        if not client.steps:
            clock[0] += 55
            raise RequestWaitExpired("synthetic final generation exceeded its caller wait")
        clock[0] += 5
        return original_create(**kwargs)

    client.responses.create = create
    request = DevRunRequest(
        provider="openai", task=public, model="gpt-5.4-2026-03-05",
        reasoning_effort="xhigh", max_cost_usd=Decimal("4"),
        env_file=root / "absent.env", state_root=root / "state",
        context_policy="segmented-v1", planning_policy="brief-v1",
        verification_policy="public-checks-v1", evaluation_reserve_seconds=330,
        rate_limit_policy=rate_limit_retry.POLICY,
        limits=DevLimits(max_model_calls=40, max_tool_actions=100,
                         max_accepted_mutations=12, wall_time_seconds=1800),
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("socket.socket.connect", lambda *_: pytest.fail("network forbidden"))
        patch.setattr(runner, "monotonic", lambda: clock[0])
        patch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))
        patch.setattr(runner, "_live_task_is_admitted", lambda *a, **k: None)
        patch.setattr(runner, "_live_source_preflight", lambda *a, **k: None)
        patch.setattr(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox())
        patch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
        patch.setattr(runner, "BoundedResponsesClient",
                      lambda **_: SimpleNamespace(close=lambda: None))
        patch.setattr(runner, "OpenAIResponsesAdapter", lambda config, **kw:
                      OpenAIResponsesAdapter(config, api_key="synthetic", client=client))
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN", result
    assert result["accepted_mutations"] == 1
    assert result["call_counts"]["model"] == 5
    journal = DevJournal(request.state_root, result["run_id"])
    finished = [e["payload"]["result"] for e in journal.events()
                if e["event_type"] == "action_finished"]
    failed = next(r for r in finished if r["action_id"] == "rejected-edit")
    assert failed["status"] == "failed" and failed["error_code"] is not None
    return Source(request.state_root, result["run_id"], sha256_bytes(journal.path.read_bytes()),
                  sha256_bytes(journal.envelope_path.read_bytes()), public,
                  sha256_bytes(public.read_bytes()))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    connect = socket.socket.connect

    def local_event_loop_only(sock, address):
        # Windows implements asyncio's internal socketpair with a loopback connection.
        # HTTP is independently constrained to httpx.MockTransport below.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return connect(sock, address)
        pytest.fail("external network forbidden")

    monkeypatch.setattr("socket.socket.connect", local_event_loop_only)
    monkeypatch.setattr(runner, "_resolve_task_file", resolver(runner._resolve_task_file))


def branch_for(source, tmp_path, **kwargs):
    journal = DevJournal(source.root, source.run_id)
    cut = [e for e in journal.events() if e["event_type"] == "model_input_prepared"][-1]
    return diagnostic.fork(source, cut["sequence"], tmp_path / "child", "B",
                           synthetic_cap_usd=Decimal("4"),
                           preserve_parent_configuration=True, **kwargs)


def test_extended_fork_preserves_candidate_parent_and_cumulative_budget(source, tmp_path):
    parent = DevJournal(source.root, source.run_id)
    before = parent.path.read_bytes(), parent.envelope_path.read_bytes()
    old = parent.load_envelope()
    branch = branch_for(source, tmp_path, total_wall_time_seconds=3600)
    marker = branch.journal.events()[branch.inherited_events]["payload"]
    budget = marker["continuation_budget"]
    assert branch.request.limits.wall_time_seconds == 3600
    assert branch.envelope.limits.wall_time_seconds == 3600
    assert branch.request.limits.max_model_calls == 39
    assert branch.request.limits.max_tool_actions == old.limits.max_tool_actions == 100
    assert branch.request.limits.max_accepted_mutations == old.limits.max_accepted_mutations == 12
    assert branch.request.evaluation_reserve_seconds == old.evaluation_reserve_seconds == 330
    assert runner._restore_counters(branch.journal).model_calls == 4
    assert runner._restore_counters(branch.journal).tool_actions == 4
    assert branch.request.limits.max_model_calls - 4 == old.limits.max_model_calls - 5
    assert budget["prefix_active_elapsed_ms"] == 20_000
    assert budget["inherited_active_elapsed_ms"] == parent.latest_active_elapsed_ms() == 75_000
    assert branch.journal.latest_active_elapsed_ms() == branch.active_elapsed_ms == 75_000
    assert branch.remaining_budget["active_wall_time_seconds"] == 3600 - 330 - 75
    assert branch.remaining_budget["total_active_wall_time_seconds"] == 3600 - 75
    assert branch.ledger.cap_nanos - branch.ledger.spent_nanos == 4_000_000_000
    assert branch.envelope.max_cost_nanos == branch.ledger.cap_nanos
    assert branch.request.rate_limit_policy == rate_limit_retry.POLICY
    assert branch.envelope.rate_limit_policy == rate_limit_retry.POLICY
    assert branch.envelope.model_hash == runner._model_hash(branch.request, branch.pricing)
    assert branch.journal.load_envelope() == branch.envelope
    assert (branch.workspace / "mini_data_utils/resumed_helper.py").read_bytes() == b"VALUE = 7\n"
    restored_source = (branch.workspace / "mini_data_utils/csvlite.py").read_text()
    assert "record_line" in restored_source
    assert "physical_line" not in restored_source and "invalid" not in restored_source
    assert WorkspaceManager.diff_summary(branch.workspace).changed_files == [
        "mini_data_utils/csvlite.py", "mini_data_utils/resumed_helper.py"]
    assert branch.remaining_budget["accepted_mutations"] == 11
    assert (parent.path.read_bytes(), parent.envelope_path.read_bytes()) == before


def test_excluded_unknown_is_provenance_not_an_automatic_retry_or_zero_bill(source, tmp_path):
    parent = DevJournal(source.root, source.run_id)
    pending = parent.unresolved_provider_call()
    assert pending is not None
    branch = branch_for(source, tmp_path, total_wall_time_seconds=3600)
    marker = branch.journal.events()[branch.inherited_events]["payload"]
    budget = marker["continuation_budget"]
    assert budget["parent_journal_hash"] == source.journal_hash
    assert budget["parent_terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert budget["excluded_model_calls"] == budget["excluded_input_count_calls"] == 1
    assert budget["parent_unknown_usage_resolved"] is False
    excluded = budget["excluded_provider_calls"]
    assert len(excluded) == 1
    assert excluded[0]["call_id"] == pending["call_id"]
    assert excluded[0]["request_hash"] == pending["request_hash"]
    assert excluded[0]["reserved_cost_nanos"] == pending["reserved_cost_nanos"] > 0
    assert excluded[0]["usage"] == "UNKNOWN" and excluded[0]["replayed"] is False
    assert budget["excluded_unknown_reservation_nanos"] == pending["reserved_cost_nanos"]
    assert branch.journal.unresolved_provider_call() is None
    assert branch.journal.unresolved_input_count() is None
    assert branch.journal.terminal() is None
    assert parent.unresolved_provider_call() == pending
    assert sha256_bytes(parent.path.read_bytes()) == source.journal_hash


def test_default_fork_keeps_old_wall_elapsed_and_call_limit(source, tmp_path):
    branch = branch_for(source, tmp_path)
    assert branch.request.limits.wall_time_seconds == 1800
    assert branch.request.limits.max_model_calls == 40
    assert branch.active_elapsed_ms == 20_000
    marker = branch.journal.events()[branch.inherited_events]["payload"]
    assert "continuation_budget" not in marker
    assert branch.request.rate_limit_policy == rate_limit_retry.POLICY


@pytest.mark.parametrize("seconds", [0, 1799, 1800, 3600.0, True])
def test_wall_override_rejects_invalid_or_nonincreasing_limits(source, tmp_path, seconds):
    with pytest.raises(ContractError):
        branch_for(source, tmp_path, total_wall_time_seconds=seconds)
    assert not (tmp_path / "child").exists()


def test_wall_override_accepts_other_valid_increased_total(source, tmp_path):
    branch = branch_for(source, tmp_path, total_wall_time_seconds=2700)
    assert branch.request.limits.wall_time_seconds == 2700
    assert branch.envelope.limits.wall_time_seconds == 2700
    assert branch.journal.latest_active_elapsed_ms() == 75_000
    assert branch.remaining_budget["active_wall_time_seconds"] == 2700 - 330 - 75


def test_changed_parent_identity_cannot_open_new_allowance(source, tmp_path):
    with pytest.raises(ContractError, match="source identity"):
        branch_for(replace(source, journal_hash="sha256:" + "0" * 64), tmp_path,
                   total_wall_time_seconds=3600)
    assert not (tmp_path / "child").exists()


def test_extension_cannot_discard_completed_parent_actions(source, tmp_path):
    events = DevJournal(source.root, source.run_id).events()
    cut = [e for e in events if e["event_type"] == "model_input_prepared"][1]
    with pytest.raises(ContractError, match="discards completed work or admitted actions"):
        diagnostic.fork(source, cut["sequence"], tmp_path / "child", "B",
                        synthetic_cap_usd=Decimal("4"), preserve_parent_configuration=True,
                        total_wall_time_seconds=3600)
    assert not (tmp_path / "child").exists()


def test_extension_requires_preserving_parent_configuration(source, tmp_path):
    events = DevJournal(source.root, source.run_id).events()
    cut = [e for e in events if e["event_type"] == "model_input_prepared"][-1]
    with pytest.raises(ContractError, match="preserved configuration"):
        diagnostic.fork(source, cut["sequence"], tmp_path / "child", "B",
                        synthetic_cap_usd=Decimal("4"), total_wall_time_seconds=3600)
    assert not (tmp_path / "child").exists()


@pytest.mark.parametrize("tool", ["edit_files", "run_check", "run_tests"])
def test_remote_task_rehearsal_cannot_execute_mutations_or_checks(source, tmp_path, tool):
    branch = branch_for(source, tmp_path, total_wall_time_seconds=3600)
    branch.package = branch.package.model_copy(deep=True)
    branch.package.public.repository.url = "https://example.invalid/public-repository"
    client = ScriptedClient([[call(tool, {}, "mutate" if tool == "edit_files" else "verify")]])
    before = branch.journal.path.read_bytes()
    with pytest.raises(ContractError, match="outside synthetic rehearsal"):
        diagnostic.rehearse(branch, client)
    assert branch.journal.path.read_bytes() == before
    assert client.created == client.counted == []


def test_offline_rehearsal_preserves_policy_without_constructing_http_client(
    source, tmp_path, monkeypatch,
):
    branch = branch_for(source, tmp_path, total_wall_time_seconds=3600)
    client = ScriptedClient(stop_steps())

    def forbidden(*args, **kwargs):
        pytest.fail("offline rehearsal constructed a real HTTP transport")

    monkeypatch.setattr("patchloop.agent.request_transport.BoundedResponsesClient.__init__",
                        forbidden)
    result = diagnostic.rehearse(branch, client)
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["synthetic_counts"] == result["synthetic_dispatches"] == 1
    assert result["provider_calls"] == result["billed_cost_nanos"] == 0
    assert len(client.counted) == len(client.created) == 1
    assert branch.request.rate_limit_policy == branch.envelope.rate_limit_policy
    assert branch.envelope.rate_limit_policy == rate_limit_retry.POLICY
    assert not any(e["event_type"] == "provider_transport_attempt_started"
                   for e in branch.journal.events()[branch.inherited_events:])


def test_continued_runner_uses_preserved_policy_for_real_mock_http(source, tmp_path, monkeypatch):
    branch = branch_for(source, tmp_path, total_wall_time_seconds=3600)
    seen, clients = [], []

    def handler(wire):
        seen.append(wire)
        if wire.url.path.endswith("input_tokens"):
            return httpx.Response(200, json={
                "object": "response.input_tokens", "input_tokens": 1000,
            })
        if sum(not row.url.path.endswith("input_tokens") for row in seen) == 1:
            return rejection()
        body = response()
        body["model"] = branch.request.model
        body["output"] = [{"type": "function_call", "id": "fc_stop", "call_id": "new-decision",
                           "name": "stop_task", "arguments": json.dumps({
                               "reason_code": "insufficient_public_evidence",
                               "summary": "End local continuation transport test.",
                           })}]
        return httpx.Response(200, json=body)

    def factory(*, api_key, retry_policy, record):
        assert retry_policy == rate_limit_retry.POLICY
        client = transport(handler, [], policy=retry_policy, record=record)
        clients.append(client)
        return client

    monkeypatch.setattr("patchloop.agent.request_transport.random.uniform", lambda *args: 0)
    monkeypatch.setattr(runner, "BoundedResponsesClient", factory)
    monkeypatch.setattr(runner, "load_exact_openai_api_key", lambda _: "synthetic")
    monkeypatch.setattr(runner, "_live_source_preflight", lambda *a, **k: None)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", lambda *a, **k: LocalSandbox())
    with inherited_reads(branch), branch.journal.execution_lock():
        result = runner._run_one_locked(
            request=branch.request, task_dir=branch.task_dir, package=branch.package,
            state_root=branch.root, pricing=branch.pricing, cost_ledger=branch.ledger,
            runtime_hash=branch.envelope.runtime_hash, model_hash=branch.envelope.model_hash,
            run_id=branch.journal.run_id, journal=branch.journal, envelope=branch.envelope,
            resuming=True,
        )
    assert result.public["terminal"] == "AGENT_STOPPED", result.public
    assert result.public["call_counts"]["model"] == 5
    assert result.public["accepted_mutations"] == 1
    assert len(seen) == 3 and len(clients) == 1 and clients[0].closed
    tail = branch.journal.events()[branch.inherited_events:]
    assert sum(e["event_type"] == "provider_call_started" for e in tail) == 1
    assert sum(e["event_type"] == "provider_call_finished" for e in tail) == 1
    assert sum(e["event_type"] == "provider_transport_rejected429" for e in tail) == 1
    current = next(e["payload"] for e in tail if e["event_type"] == "provider_call_started")
    parent = DevJournal(source.root, source.run_id)
    assert current["call_id"] != parent.unresolved_provider_call()["call_id"]
    state = json.loads(json.loads(seen[0].content)["input"][-1]["content"])["state"]
    assert state["remaining_budget"]["model_calls"] == 35
    assert state["remaining_budget"]["active_wall_time_seconds"] > 3100
    assert sha256_bytes(parent.path.read_bytes()) == source.journal_hash
