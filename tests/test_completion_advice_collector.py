"""Exercise manifest binding and uncertainty through the production collector."""
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import call, stop_steps
from test_cleanup_information_checkpoint import failed_source as failed_source  # noqa: F401
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_continuation as continuation
from diagnostics import completion_advice_collector as collector
from diagnostics import post_edit_budget_checkpoint as checkpoint
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.errors import ContractError
from patchloop.util import sha256_json


@pytest.mark.parametrize("failure", [None, "count", "transport", "usage", "repair"])
def test_collector(failed_source, source, tmp_path, monkeypatch, failure):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("network forbidden"))
    monkeypatch.setattr(collector.base.runner, "_require_tracked_clean_paths", lambda *a: None)
    monkeypatch.setattr(collector.base.live, "check_environment", lambda *a: {"status": "READY"})
    packet = checkpoint.prepare(failed_source, tmp_path / "packet", Decimal("3"))
    prepared = collector.prepare(Path(packet["packet"]), packet["packet_hash"],
        source.root.parent / "absent.env", tmp_path / "result", tmp_path / "plan")
    path = Path(prepared["manifest"])
    plan = json.loads(path.read_bytes())
    with pytest.raises(ContractError, match="approved cap differs"):
        collector.collect(path, prepared["manifest_hash"], Decimal("4"))
    assert not (tmp_path / "result").exists()
    steps = [[call("run_check", {"check_id": "existing-unit-tests"}, "verify")], *stop_steps()]
    if failure == "repair":
        mutation = MOCK_MUTATIONS["csv-quoted-newline"]
        edit = call("replace_text", {
            "path": mutation.path,
            "old_text": mutation.old_text.replace("return rows", "return []"),
            "new_text": mutation.new_text, "occurrence": 1, "causal_revision": None,
            "hypothesis": "Use CSV parsing to preserve quoted rows.",
            "expected_behavior": "The regression preserves quoted newlines."}, "mutate")
        edit["action_id"] = "offline_repair_second_edit"
        check = call("run_check", {"check_id": "existing-unit-tests"}, "verify")
        check["action_id"] = "offline_check_repaired"
        steps = [steps[0], [call("read_file", {"path": mutation.path,
                 "start_line": 1, "end_line": 90}, "inspect")], [edit], [check], *stop_steps()]
    client = continuation.ScriptedClient(steps, failure=None if failure == "repair" else failure)
    install_sdk(monkeypatch, failed_source, [client])
    result = collector.collect(path, prepared["manifest_hash"], Decimal("3"))
    expected = {None: "AGENT_STOPPED", "repair": "AGENT_STOPPED",
                "count": "COUNT_TIMEOUT_OR_UNKNOWN",
                "transport": "PROVIDER_TIMEOUT_OR_UNKNOWN", "usage": "PROVIDER_TIMEOUT_OR_UNKNOWN"}
    assert result["row"]["result"]["terminal"] == expected[failure], result
    assert result["row"]["first_state_restored"]
    assert result["new_cost_nanos"] == (
        2_750_000 if failure == "repair" else
        1_100_000 if failure is None else 0 if failure == "count" else None)
    if client.created:
        request = {k: v for k, v in client.created[0].items() if k != "timeout"}
        assert sha256_json(request) == plan["treatment_first_request_hash"]
    if failure in (None, "repair"):
        state = json.loads(client.created[1]["input"][-1]["content"])["state"]
        assert state["completion_guidance"]["stage"] == "needs_mutation"
        assert state["completion_guidance"]["next_action"] is None
    if failure == "repair":
        state = json.loads(client.created[-1]["input"][-1]["content"])["state"]
        assert state["completion_guidance"]["submission_ready"]
        assert state["completion_guidance"]["next_action"] is None
        assert result["row"]["result"]["accepted_mutations"] == 2
    with pytest.raises(ContractError, match="fresh output root required"):
        collector.collect(path, prepared["manifest_hash"], Decimal("3"))
