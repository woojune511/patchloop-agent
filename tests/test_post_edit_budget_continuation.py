"""Cost-only intervention and inherited post-edit state, without paid work."""
import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import call, stop_steps
from test_cleanup_information_checkpoint import failed_source as failed_source  # noqa: F401
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_comparison as live
from diagnostics import checkpoint_continuation as continuation
from diagnostics import post_edit_budget_checkpoint as checkpoint
from diagnostics import post_edit_budget_continuation as collector
from patchloop.artifacts import ArtifactStore
from patchloop.dev.cost import DevCostLedger
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(scope="module")
def packet(failed_source, tmp_path_factory):
    return checkpoint.prepare(failed_source, tmp_path_factory.mktemp("post-edit") / "packet",
                              Decimal("3"))


def restore(packet, tmp_path):
    return continuation.restore(Path(packet["packet"]), packet["packet_hash"], tmp_path / "A", "A")


def test_cost_only_and_persistent_budget(packet, failed_source, tmp_path):
    before = (failed_source.root / "runs" / f"{failed_source.run_id}.jsonl").read_bytes()
    branch = restore(packet, tmp_path)
    projected = copy.deepcopy(branch.selected)
    view = json.loads(projected["input"][-1]["content"])
    old = json.loads(branch.source_request["input"][-1]["content"])
    view["state"]["remaining_budget"]["cost"] = old["state"]["remaining_budget"]["cost"]
    projected["input"][-1]["content"] = canonical_json(view)
    assert projected == branch.source_request
    assert branch.ledger.remaining_nanos == 3_000_000_000
    assert branch.ledger.spent_nanos == branch.initial_spent_nanos > 0
    assert branch.envelope.max_cost_nanos != branch.ledger.cap_nanos
    client = continuation.ScriptedClient([
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")], *stop_steps()])
    result = continuation.rehearse(branch, client)
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["first_state_restored"] and result["result"]["accepted_mutations"] == 1
    assert {k: v for k, v in client.created[0].items() if k != "timeout"} == branch.selected
    later = json.loads(client.created[1]["input"][-1]["content"])["state"]["remaining_budget"]
    assert later["cost"]["invocation_cap"] == branch.initial_spent_nanos + 3_000_000_000
    assert later["cost"]["settled_usage"] > branch.initial_spent_nanos
    assert later["cost"]["remaining"] < 3_000_000_000
    assert (failed_source.root / "runs" / f"{failed_source.run_id}.jsonl").read_bytes() == before
    assert result["new_billed_cost_nanos"] == 0


@pytest.mark.parametrize("failure", ["count", "transport", "usage"])
def test_uncertainty_stops(packet, tmp_path, failure):
    branch = restore(packet, tmp_path)
    result = continuation.rehearse(
        branch, continuation.ScriptedClient(stop_steps(), failure=failure))
    assert result["stop_remaining"]
    assert result["simulated_billing_known"] == (failure == "count")
    assert not any(e["event_type"] == "action_started"
                   for e in branch.journal.events()[branch.inherited_events:])


def test_new_ledger_excludes_history(packet, tmp_path):
    branch = restore(packet, tmp_path)
    group = DevCostLedger(Decimal("3"), branch.pricing)
    ledger = live.ContinuationLedger(branch, group, DevJournal(tmp_path, "run_dev_ledger"), "A1")
    assert ledger.spent_nanos == branch.initial_spent_nanos and group.spent_nanos == 0
    admitted = ledger.admit(42_012, desired_output_ceiling=25_000)
    assert admitted.output_ceiling == 25_000
    new_cost = ledger.settle(input_tokens=42_012, cached_input_tokens=0, output_tokens=100)
    assert group.spent_nanos == new_cost
    assert ledger.spent_nanos == branch.initial_spent_nanos + new_cost


@pytest.mark.parametrize("failure", [None, "count", "transport", "usage"])
def test_live_collector_with_synthetic_provider(
    packet, failed_source, source, tmp_path, monkeypatch, failure,
):
    def forbidden(*args, **kwargs):
        pytest.fail("network forbidden")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(collector.runner, "_require_tracked_clean_paths", lambda *args: None)
    monkeypatch.setattr(live, "check_environment", lambda *args: {"status": "READY"})
    prepared = collector.prepare(
        Path(packet["packet"]), packet["packet_hash"],
        source.root.parent / "absent.env", tmp_path / "result", tmp_path / "plan")
    client = continuation.ScriptedClient(stop_steps(), failure=failure)
    install_sdk(monkeypatch, failed_source, [client])
    result = collector.collect(Path(prepared["manifest"]), prepared["manifest_hash"], Decimal("3"))
    expected = {None: "AGENT_STOPPED", "count": "COUNT_TIMEOUT_OR_UNKNOWN",
                "transport": "PROVIDER_TIMEOUT_OR_UNKNOWN", "usage": "PROVIDER_TIMEOUT_OR_UNKNOWN"}
    assert result["row"]["result"]["terminal"] == expected[failure], result
    assert result["row"]["first_state_restored"]
    assert result["new_cost_nanos"] == (
        550_000 if failure is None else 0 if failure == "count" else None)
    assert result["row"]["historical_spent_nanos"] > 0
    assert len(client.created) == (0 if failure == "count" else 1)


def test_reject_tampering_and_second_arm(packet, tmp_path):
    with pytest.raises(ContractError, match="one unhinted arm"):
        continuation.restore(Path(packet["packet"]), packet["packet_hash"], tmp_path / "B", "B")
    with pytest.raises(ContractError, match="positive new cap"):
        checkpoint.project({}, 0)
    with pytest.raises(ContractError, match="approved manifest hash"):
        collector.collect(Path(packet["packet"]), "wrong", Decimal("3"))


def test_collector_cap_and_single_use(packet, tmp_path, monkeypatch):
    branch = restore(packet, tmp_path)
    root = tmp_path / "live"
    env = tmp_path / "dummy.env"
    env.write_text("not read")
    plan = {"packet": packet["packet"], "packet_hash": packet["packet_hash"],
            "env_file": str(env), "result_root": str(root), "model": branch.envelope.model,
            "new_cap_nanos": 3_000_000_000}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(canonical_json(plan))
    digest = sha256_bytes(manifest.read_bytes())
    with pytest.raises(ContractError, match="approved cap differs"):
        collector.collect(manifest, digest, Decimal("4"))
    assert not root.exists()
    monkeypatch.setattr(collector, "controls", lambda *args: plan)
    monkeypatch.setattr(collector.runner, "_require_tracked_clean_paths", lambda *args: None)
    monkeypatch.setattr(live, "check_environment", lambda *args: {"status": "PREFLIGHT_FAILED"})
    result = collector.collect(manifest, digest, Decimal("3"))
    assert result["row"]["status"] == "NOT_RUN" and result["new_cost_nanos"] == 0
    assert ArtifactStore(root / "artifacts").root.exists()
    with pytest.raises(FileExistsError):
        collector.collect(manifest, digest, Decimal("3"))
