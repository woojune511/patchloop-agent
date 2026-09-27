"""Readiness timing through the actual collector, using a finite synthetic SDK."""
import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_checkpoint_comparison import install_sdk
from test_checkpoint_continuation import call, stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_comparison as live
from diagnostics import checkpoint_continuation as continuation
from diagnostics import mutation_advice_checkpoint as original
from diagnostics import post_edit_budget_checkpoint as checkpoint
from diagnostics import post_edit_budget_continuation as collector
from diagnostics.cleanup_information_checkpoint import ForkStore
from diagnostics.declaration_checkpoint import Source
from diagnostics.segmented_input_audit import verify_turn
from patchloop.contracts import Artifact
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(scope="module")
def correct_source(source, tmp_path_factory):
    root = tmp_path_factory.mktemp("correct-post-edit")
    packet = original.prepare(source, root / "packet")
    branch = continuation.restore(Path(packet["packet"]), packet["packet_hash"], root / "fork", "A")
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {k: getattr(mutation, k) for k in
            ("path", "old_text", "new_text", "hypothesis", "expected_behavior")}
    args.update(occurrence=1, causal_revision=None)
    result = continuation.rehearse(branch, continuation.ScriptedClient([
        [call("replace_text", args, "mutate")],
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")], *stop_steps()]))
    assert result["result"]["terminal"] == "AGENT_STOPPED"
    return Source(branch.root, branch.journal.run_id,
                  sha256_bytes(branch.journal.path.read_bytes()),
                  sha256_bytes(branch.journal.envelope_path.read_bytes()),
                  source.public_path, source.public_hash)


@pytest.mark.parametrize("behavior", ["ready", "stop_early", "count_failure"])
def test_deferred_delivery_and_no_reinjection(
    correct_source, source, tmp_path, monkeypatch, behavior,
):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("network forbidden"))
    packet = checkpoint.prepare(correct_source, tmp_path / "packet", Decimal("3"),
                                verification_scope=True, scope_timing="ready-to-submit")
    monkeypatch.setattr(collector.runner, "_require_tracked_clean_paths", lambda *a: None)
    monkeypatch.setattr(live, "check_environment", lambda *a: {"status": "READY"})
    prepared = collector.prepare(
        Path(packet["packet"]), packet["packet_hash"], source.root.parent / "absent.env",
        tmp_path / "result", tmp_path / "plan")
    steps = stop_steps() if behavior == "stop_early" else [
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        [call("read_file", {"path": "mini_data_utils/csvlite.py", "start_line": 1,
                            "end_line": 90}, "inspect")], *stop_steps()]
    client = continuation.ScriptedClient(steps)
    if behavior == "count_failure":
        original_count = client.responses.input_tokens.count

        def count(**request):
            if client.counted:
                client.failure = "count"
            return original_count(**request)

        client.responses.input_tokens.count = count
    install_sdk(monkeypatch, correct_source, [client])
    result = collector.collect(Path(prepared["manifest"]), prepared["manifest_hash"], Decimal("3"))
    assert result["row"]["first_state_restored"], result
    assert result["row"]["result"]["terminal"] == (
        "COUNT_TIMEOUT_OR_UNKNOWN" if behavior == "count_failure" else "AGENT_STOPPED"), result
    states = [json.loads(r["input"][-1]["content"])["state"] for r in client.created]
    assert checkpoint.SCOPE_FIELD not in states[0]
    branch = DevJournal(tmp_path / "result" / "A1", correct_source.run_id)
    events = branch.events()
    reader = ForkStore(branch.root, events)
    markers = [e["payload"] for e in events if e["event_type"] == "diagnostic_scope_cue_prepared"]
    assert len(markers) == (0 if behavior == "stop_early" else 1)
    if behavior == "ready":
        assert states[1][checkpoint.SCOPE_FIELD] == checkpoint.SCOPE_CUE
        assert states[1]["completion_guidance"]["submission_ready"]
        assert checkpoint.SCOPE_FIELD not in states[2]
        normalized = copy.deepcopy(client.created[1])
        normalized.pop("timeout", None)
        view = json.loads(normalized["input"][-1]["content"])
        view["state"].pop(checkpoint.SCOPE_FIELD)
        normalized["input"][-1]["content"] = canonical_json(view)
        baseline = json.loads(reader.read_bytes(
            Artifact.model_validate(markers[0]["baseline_request"])))
        assert normalized == baseline
        turn = next(e for e in events if e["event_type"] == "turn_started"
                    and e["payload"]["turn_id"] == markers[0]["boundary_id"])
        verified = verify_turn(turn, events, reader, actual_input=client.created[1]["input"])
        assert verified["verified"]
    elif behavior == "count_failure":
        assert result["row"]["billing_known"] and result["row"]["stop_remaining"]
        assert len(client.created) == 1 and result["new_cost_nanos"] == 550_000
