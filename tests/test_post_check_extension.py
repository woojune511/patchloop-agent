"""Time extension is a new prefix fork, never uncertainty reconciliation."""
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import call, stop_steps
from test_deferred_scope_cue import correct_source as correct_source  # noqa: F401
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_comparison as live
from diagnostics import checkpoint_continuation as c
from diagnostics import completion_advice_continuation as advice
from diagnostics import post_check_extension as checkpoint
from diagnostics import post_check_extension_collector as collector
from diagnostics import post_edit_budget_checkpoint as budget
from diagnostics.declaration_checkpoint import Source
from patchloop.errors import ContractError
from patchloop.util import sha256_bytes


@pytest.fixture(scope="module")
def packet(correct_source, tmp_path_factory):
    root = tmp_path_factory.mktemp("uncertain")
    prep = budget.prepare(correct_source, root / "budget", Decimal("3"))
    branch = c.restore(Path(prep["packet"]), prep["packet_hash"], root / "source", "A")
    client = c.ScriptedClient([[call("run_check", {"check_id": "existing-unit-tests"},
                                  "verify")], *stop_steps()])
    original = client.responses.create

    def create(**request):
        if client.created:
            client.failure = "transport"
        return original(**request)

    client.responses.create = create
    result = advice.rehearse(branch, client)
    assert result["result"]["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    unknown = branch.journal.unresolved_provider_call()
    source = Source(branch.root, branch.journal.run_id,
        sha256_bytes(branch.journal.path.read_bytes()),
        sha256_bytes(branch.journal.envelope_path.read_bytes()),
        correct_source.public_path, correct_source.public_hash)
    return checkpoint.prepare(source, unknown["turn_id"], root / "packet")


@pytest.mark.parametrize("failure", [None, "count", "transport"])
def test_extension(packet, correct_source, source, tmp_path, monkeypatch, failure):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.setattr(collector.runner, "_require_tracked_clean_paths", lambda *a: None)
    monkeypatch.setattr(live, "check_environment", lambda *a: {"status": "READY"})
    prepared = collector.prepare(Path(packet["packet"]), packet["packet_hash"],
        source.root.parent / "absent.env", tmp_path / "result", tmp_path / "plan", Decimal("3"))
    client = c.ScriptedClient(stop_steps(), failure=failure)
    install_sdk(monkeypatch, correct_source, [client])
    result = collector.collect(Path(prepared["manifest"]), prepared["manifest_hash"], Decimal("3"))
    row = result["rows"][0]
    assert row["first_state_restored"], result
    assert result["source_billing_remains_unknown"]
    expected = {None: "AGENT_STOPPED", "count": "COUNT_TIMEOUT_OR_UNKNOWN",
                "transport": "PROVIDER_TIMEOUT_OR_UNKNOWN"}
    assert row["result"]["terminal"] == expected[failure], result
    assert result["new_cost_nanos"] == (550_000 if failure is None else
                                        0 if failure == "count" else None)
    request = client.counted[0]
    state = json.loads(request["input"][-1]["content"])["state"]
    assert state["remaining_budget"]["active_wall_time_seconds"] > 3600
    assert state["remaining_budget"]["cost"]["remaining"] == 3_000_000_000
    assert "expectation_review" not in state
    with pytest.raises(ContractError, match="fresh output"):
        collector.collect(Path(prepared["manifest"]), prepared["manifest_hash"], Decimal("3"))
