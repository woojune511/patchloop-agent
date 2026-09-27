"""Matched funding and fail-stop collection, with network forbidden."""
import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import stop_steps
from test_deferred_scope_cue import correct_source as correct_source  # noqa: F401
from test_expectation_review_continuation import packet as packet  # noqa: F401
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_comparison as live
from diagnostics import checkpoint_continuation as c
from diagnostics import expectation_review_checkpoint as review
from diagnostics import expectation_review_collector as collector
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


@pytest.mark.parametrize("failure", [None, "count", "transport", "usage"])
def test_matched_collection(packet, source, correct_source, tmp_path, monkeypatch, failure):
    def forbidden(*args, **kwargs):
        pytest.fail("network forbidden")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(collector.runner, "_require_tracked_clean_paths", lambda *a: None)
    monkeypatch.setattr(live, "check_environment", lambda *a: {"status": "READY"})
    prepared = collector.prepare(Path(packet["packet"]), packet["packet_hash"],
        source.root.parent / "absent.env", tmp_path / "result", tmp_path / "plan", Decimal("6"))
    manifest = Path(prepared["manifest"])
    plan = json.loads(manifest.read_bytes())
    with pytest.raises(ContractError, match="approved cap differs"):
        collector.collect(manifest, prepared["manifest_hash"], Decimal("3"))
    clients = [c.ScriptedClient(stop_steps(), failure=failure), c.ScriptedClient(stop_steps())]
    install_sdk(monkeypatch, correct_source, clients)
    result = collector.collect(manifest, prepared["manifest_hash"], Decimal("6"))
    first, second = result["rows"]
    expected = {None: "AGENT_STOPPED", "count": "COUNT_TIMEOUT_OR_UNKNOWN",
                "transport": "PROVIDER_TIMEOUT_OR_UNKNOWN", "usage": "PROVIDER_TIMEOUT_OR_UNKNOWN"}
    assert first["result"]["terminal"] == expected[failure], result
    assert first["first_state_restored"]
    assert first["historical_spent_nanos"] > 0
    assert result["new_cost_nanos"] == (1_100_000 if failure is None else
                                        0 if failure == "count" else None)
    if failure:
        assert second["status"] == "NOT_RUN" and not clients[1].counted
    else:
        assert second["first_state_restored"]
        requests = [{k: v for k, v in client.created[0].items() if k != "timeout"}
                    for client in clients]
        assert [sha256_json(r) for r in requests] == list(plan["first_request_hashes"].values())
        normalized = copy.deepcopy(requests[1])
        state = json.loads(normalized["input"][-1]["content"])
        assert state["state"].pop(review.FIELD) == review.CUE
        assert state["state"]["remaining_budget"]["cost"]["remaining"] == 3_000_000_000
        normalized["input"][-1]["content"] = canonical_json(state)
        assert normalized == requests[0]
    with pytest.raises(ContractError, match="fresh output root required"):
        collector.collect(manifest, prepared["manifest_hash"], Decimal("6"))
