"""Funded workers account new settlements and share admission; no provider or task runs."""
from __future__ import annotations

import json
import socket
from decimal import Decimal
from threading import Event, Lock
from types import SimpleNamespace

import pytest

from diagnostics import funded_continuation as funded
from diagnostics import observation_comparison as live
from diagnostics import observation_exposure as exposure
from diagnostics import parallel_dev_batch as parallel
from diagnostics.checkpoint_comparison import ContinuationLedger
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.cost import pricing_for_model, usd_to_nanos
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@pytest.fixture
def worker(tmp_path, monkeypatch):
    def no_network(*_, **__):
        pytest.fail("worker accounting tests cannot access the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    # initialize_worker is process-local in production; restore all substitutions here.
    for owner, name in (
        (parallel, "_STOP"), (parallel, "_ADMISSION"),
        (runner, "DevJournal"), (runner, "OpenAIResponsesAdapter"),
        (exposure, "DevJournal"), (live, "OpenAIResponsesAdapter"),
    ):
        monkeypatch.setattr(owner, name, getattr(owner, name))
    stop = Event()
    funded.initialize_worker(stop, Lock())
    request = DevRunRequest(
        provider="openai", model="gpt-5.4-mini-2026-03-17",
        env_file=tmp_path / "NO_CREDENTIAL_FILE", task=tmp_path / "public.yaml",
        state_root=tmp_path / "new-allocation", max_cost_usd=Decimal("4"),
    )
    inherited = 1_200_000_000
    parent = DevJournal(tmp_path / "immutable-parent", "run_dev_oldunknown")
    parent.append("provider_call_started", {"call_id": "historical-settled"})
    parent.append("provider_call_finished", {
        "call_id": "historical-settled", "cost_nanos": inherited,
    })
    parent.append("provider_call_started", {
        "call_id": "historical-unknown", "reserved_cost_nanos": 500_000_000,
    })
    row = {
        "kind": "continuation", "task_index": 18,
        "request": request.model_dump(mode="json"), "first_request_hash": "frozen-input",
        "checkpoint": {
            "inherited_settled_cost_nanos": inherited,
            "excluded_model_calls": 1, "historical_unknown_resolved": False,
        },
    }
    manifest = tmp_path / "manifest.json"
    raw = json.dumps({"rows": [row]}).encode()
    manifest.write_bytes(raw)
    calls = []

    def restore(selected, output):
        calls.append((selected, output))
        journal = exposure.DevJournal(output, "run_dev_continued")
        for event in parent.events()[:2]:
            journal.append(event["event_type"], event["payload"])
        return SimpleNamespace(
            request=request.model_copy(update={
                "max_cost_usd": request.max_cost_usd + Decimal(inherited) / 10**9,
            }), pricing=pricing_for_model(request.model), initial_spent_nanos=inherited,
            journal=journal,
        )

    monkeypatch.setattr(funded, "restore_row", restore)
    return SimpleNamespace(
        request=request, row=row, stop=stop, manifest=manifest, manifest_hash=sha256_bytes(raw),
        parent=parent, parent_bytes=parent.path.read_bytes(), inherited=inherited,
        restore_calls=calls, observed={},
    )


def install_execution(monkeypatch, worker, *, unknown=False, mismatch=False):
    def execute(branch, group, operator, store, label, first_hash):
        assert first_hash == "frozen-input"
        assert group.spent_nanos == 0
        assert group.cap_nanos == usd_to_nanos(Decimal("4"))
        ledger = ContinuationLedger(branch, group, operator, label)
        assert ledger.spent_nanos == worker.inherited
        assert ledger.cap_nanos == worker.inherited + group.cap_nanos
        admission = ledger.admit(100, desired_output_ceiling=128)
        assert admission is not None
        journal = branch.journal
        journal.append("input_count_started", {"count_id": "new-count"})
        journal.append("input_count_finished", {"count_id": "new-count"})
        journal.append("provider_call_started", {
            "call_id": "new-settled", "reserved_cost_nanos": admission.reserved_cost_nanos,
        })
        journal.append("provider_transport_attempt_started", {"attempt_no": 1})
        cost = ledger.settle(input_tokens=100, cached_input_tokens=0, output_tokens=10)
        journal.append("provider_call_finished", {
            "call_id": "new-settled", "cost_nanos": cost,
        })
        if unknown:
            journal.append("provider_call_started", {
                "call_id": "new-unknown", "reserved_cost_nanos": 900_000,
            })
            journal.append("provider_transport_attempt_started", {"attempt_no": 1})
        worker.observed.update(cost=cost, group_spent=group.spent_nanos, journal=journal)
        return {
            "result": {"terminal": "PROVIDER_TIMEOUT_OR_UNKNOWN" if unknown else "AGENT_STOPPED"},
            "new_cost_nanos": None if unknown else cost + int(mismatch),
            "stop_remaining": unknown,
        }

    monkeypatch.setattr(live, "run_branch", execute)


def run(worker):
    return funded.solve_row(worker.row["request"], manifest_hash=worker.manifest_hash)


def test_only_new_settlements_consume_new_allocation(worker, monkeypatch):
    install_execution(monkeypatch, worker)
    result = run(worker)
    cost = worker.observed["cost"]
    assert result["ok"] is True and result["error_type"] is None
    assert result["result"]["cost_nanos"] == result["accounting"]["cost_nanos"] == cost
    assert worker.observed["group_spent"] == cost
    assert result["accounting"]["historical_settled_cost_nanos"] == worker.inherited
    assert result["accounting"]["runs"][0]["cost_nanos"] == worker.inherited + cost
    assert result["result"]["historical_funds_reopened"] is False
    assert worker.parent.path.read_bytes() == worker.parent_bytes
    assert worker.parent.unresolved_provider_call()["call_id"] == "historical-unknown"
    assert worker.observed["journal"].unresolved_provider_call() is None
    assert not worker.stop.is_set()


def test_unknown_new_call_stops_peers_and_retains_settled_lower_bound(worker, monkeypatch):
    install_execution(monkeypatch, worker, unknown=True)
    result = run(worker)
    assert result["ok"] is False and worker.stop.is_set()
    assert result["accounting"]["billing_known"] is False
    assert result["result"]["cost_nanos"] is None
    assert result["result"]["known_new_cost_nanos"] == worker.observed["cost"]
    assert worker.observed["journal"].unresolved_provider_call()["call_id"] == "new-unknown"
    assert worker.parent.path.read_bytes() == worker.parent_bytes


def test_durable_accounting_disagreement_stops_further_admission(worker, monkeypatch):
    install_execution(monkeypatch, worker, mismatch=True)
    result = run(worker)
    assert result["ok"] is False and worker.stop.is_set()
    assert result["accounting"]["billing_known"] is True
    assert result["result"]["known_new_cost_nanos"] == worker.observed["cost"]


def test_existing_peer_stop_prevents_restoration_or_new_spend(worker):
    worker.stop.set()
    result = run(worker)
    assert result["ok"] is False and result["error_type"] == "BatchStopped"
    assert result["accounting"]["cost_nanos"] == 0
    assert not worker.restore_calls and not worker.request.state_root.exists()


def test_peer_stop_after_restore_blocks_physical_retry_admission(worker, monkeypatch):
    def execute(branch, *_):
        # A request admitted before a peer's failure may have rejected with 429.
        branch.journal.append("provider_call_started", {"call_id": "new-inflight"})
        branch.journal.append("provider_transport_attempt_started", {"attempt_no": 1})
        branch.journal.append("provider_transport_rejected429", {"attempt_no": 1})
        parallel.stop_workers()
        branch.journal.append("provider_transport_attempt_started", {"attempt_no": 2})
        pytest.fail("physical retry was admitted after shared stop")

    monkeypatch.setattr(live, "run_branch", execute)
    result = run(worker)
    assert result["ok"] is False and result["error_type"] == "BatchStopped"
    events = DevJournal(worker.request.state_root, "run_dev_continued").events()
    assert [e["payload"]["attempt_no"] for e in events
            if e["event_type"] == "provider_transport_attempt_started"] == [1]
    assert events[-1]["event_type"] == "batch_call_prevented"
    assert result["accounting"]["cost_nanos"] == 0
    assert result["accounting"]["billing_known"] is False


def test_manifest_drift_cannot_change_checkpoint_with_same_outer_request(worker):
    plan = json.loads(worker.manifest.read_bytes())
    plan["rows"][0]["first_request_hash"] = "unapproved-checkpoint"
    worker.manifest.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(ContractError, match="manifest changed"):
        run(worker)
    assert not worker.restore_calls and not worker.request.state_root.exists()


def test_fresh_row_uses_ordinary_accounting(worker, monkeypatch):
    worker.row["kind"] = "fresh"
    raw = json.dumps({"rows": [worker.row]}).encode()
    worker.manifest.write_bytes(raw)
    worker.manifest_hash = sha256_bytes(raw)
    sentinel = {"ok": True, "accounting": {"cost_nanos": 75}}
    monkeypatch.setattr(parallel, "solve_row", lambda serialized: sentinel)
    assert run(worker) is sentinel
    assert not worker.restore_calls
