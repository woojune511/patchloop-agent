"""Operator continuation accounting and checkpoint exclusion boundaries; no network."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from diagnostics import funded_continuation as diagnostic
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@pytest.fixture
def parent(tmp_path, monkeypatch):
    public = tmp_path / "public.yaml"
    public.write_text("public fixture", encoding="utf-8")
    journal = DevJournal(tmp_path / "parent", "run_dev_fundedfixture")
    journal.envelope_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(DevJournal, "load_envelope", lambda _: SimpleNamespace(
        split="dev-train", provider="openai", cost_start_nanos=0,
    ))
    journal.append("provider_call_started", {"call_id": "settled"})
    journal.append("provider_call_finished", {"call_id": "settled", "cost_nanos": 120})
    journal.append("tool_batch_finished", {"turn_id": "old", "active_elapsed_ms": 123000})
    cut = journal.append("model_input_prepared", {"turn_id": "next"})
    return journal, public, cut


def select(parent):
    journal, public, _ = parent
    return diagnostic.saved_checkpoint(journal.root, journal.run_id, public)


def test_settled_peer_boundary_keeps_resources_and_immutable_parent(parent):
    journal, _, cut = parent
    journal.append("batch_call_prevented", {"operation": "input_count_started"})
    before = journal.path.read_bytes()
    result = select(parent)
    assert result["cut_sequence"] == cut["sequence"]
    assert result["parent_active_elapsed_ms"] == 123000
    assert result["inherited_settled_cost_nanos"] == 120
    assert result["excluded_model_calls"] == 0
    assert result["parent_billing_known"] is True
    assert journal.path.read_bytes() == before
    assert result["source"]["journal_hash"] == sha256_bytes(before)


def test_unknown_tail_remains_separate_from_settled_prefix(parent):
    journal, _, _ = parent
    journal.append("provider_call_started", {
        "call_id": "lost", "request_hash": "opaque-request-hash",
        "reserved_cost_nanos": 500, "active_elapsed_ms": 125000,
    })
    journal.append("terminal", {
        "terminal": "PROVIDER_TIMEOUT_OR_UNKNOWN", "active_elapsed_ms": 180000,
    })
    result = select(parent)
    assert result["parent_billing_known"] is False
    assert result["historical_unknown_resolved"] is False
    assert result["inherited_settled_cost_nanos"] == 120
    assert result["excluded_model_calls"] == 1
    assert result["excluded_generation"]["reserved_cost_nanos"] == 500
    assert result["parent_active_elapsed_ms"] == 180000
    assert journal.unresolved_provider_call()["call_id"] == "lost"


@pytest.mark.parametrize("kind,payload", [
    ("action_started", {"action_id": "late"}),
    ("tool_batch_started", {"turn_id": "late"}),
    ("provider_call_finished", {"call_id": "late", "cost_nanos": 10}),
    ("evaluator_started", {}),
    ("solver_finished", {}),
])
def test_never_discard_a_received_decision_action_or_submission(parent, kind, payload):
    parent[0].append(kind, payload)
    with pytest.raises(ContractError):
        select(parent)


def test_uncertain_count_is_not_a_generation_abandonment(parent):
    parent[0].append("input_count_started", {
        "count_id": "unresolved", "turn_id": "next", "request_hash": "opaque-request-hash",
    })
    with pytest.raises(ContractError, match="count remains uncertain"):
        select(parent)


@pytest.mark.parametrize("known", [True, False])
def test_new_accounting_never_spends_inherited_usage_again(known):
    value = diagnostic.new_accounting({
        "cost_nanos": 170, "billing_known": known, "counting_known": True,
    }, 120)
    assert value["cost_nanos"] == value["known_new_cost_nanos"] == 50
    assert value["historical_settled_cost_nanos"] == 120
    assert value["billing_known"] is known


def test_unknown_or_regressed_accounting_is_not_zero_cost():
    value = diagnostic.new_accounting({"cost_nanos": None, "billing_known": False}, 120)
    assert value["cost_nanos"] is None
    with pytest.raises(ContractError, match="regressed"):
        diagnostic.new_accounting({"cost_nanos": 119, "billing_known": True}, 120)
