"""Synthetic checkpoint restoration; no provider, credential or Docker access."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from test_checkpoint_continuation import call, stop_steps
from test_mutation_advice_checkpoint import source as source  # noqa: F401

from diagnostics import checkpoint_continuation as continuation
from diagnostics import saved_caller_checkpoint as checkpoint
from diagnostics.caller_uptake import file_ref
from patchloop.dev.model import MOCK_MUTATIONS
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_bytes

ORDER = [f"{a}{n}" for n in range(1, 7) for a in ("AB" if n % 2 else "BA")]


@pytest.fixture
def saved_packet(source, tmp_path, monkeypatch):
    events = DevJournal(source.root, source.run_id).events()
    turn = [e for e in events if e["event_type"] == "turn_started"][-1]
    loaded = checkpoint.load(source, turn["payload"]["turn_id"])
    observation = {"origin": "operator", "observation": "PUBLIC_CALLER_COUNTEREVIDENCE"}
    (tmp_path / "specification").mkdir()
    spec = tmp_path / "specification/spec.json"
    spec.write_text("{}", encoding="utf-8")
    # A small local task exercises the backend/loop; real frozen evidence loading
    # is additionally checked in the external actual-checkpoint rehearsal.
    monkeypatch.setattr(checkpoint, "checked_spec", lambda _: (
        {"order": ORDER}, source, loaded, observation))
    return checkpoint.prepare(file_ref(spec), tmp_path / "packet")


@pytest.mark.parametrize("arm", ["A", "B"])
def test_selected_prefix_and_first_only_delivery(saved_packet, source, tmp_path, arm):
    branch = continuation.restore(Path(saved_packet["packet"]), saved_packet["packet_hash"],
                                  tmp_path / arm, arm)
    inherited = branch.journal.events()[:branch.inherited_events]
    target = branch.packet["checkpoint"]["source_turn_id"]
    assert not any(e["event_type"] in {"input_count_started", "provider_call_started"}
                   and e["payload"].get("turn_id") == target for e in inherited)
    assert not any(e["event_type"] == "turn_decision_recorded"
                   and e["payload"]["turn_id"] == target for e in inherited)
    old = DevJournal(source.root, source.run_id).path.read_bytes()
    steps = [[call("search_files", {"query": "parse_rows", "glob": "*.py"}, "inspect")],
             *stop_steps()]
    client = continuation.ScriptedClient(steps)
    result = continuation.rehearse(branch, client)
    assert result["result"]["terminal"] == "AGENT_STOPPED", result
    assert result["first_state_restored"] and result["new_billed_cost_nanos"] == 0
    first = {k: v for k, v in client.created[0].items() if k != "timeout"}
    assert first == branch.selected
    assert ("operator_caller_observation" in first["input"][-1]["content"]) == (arm == "B")
    assert "operator_caller_observation" not in client.created[1]["input"][-1]["content"]
    assert old == DevJournal(source.root, source.run_id).path.read_bytes()


def test_repair_check_finish_and_accounting(saved_packet, tmp_path):
    branch = continuation.restore(Path(saved_packet["packet"]), saved_packet["packet_hash"],
                                  tmp_path / "repair", "B")
    mutation = MOCK_MUTATIONS["csv-quoted-newline"]
    args = {k: getattr(mutation, k) for k in
            ("path", "old_text", "new_text", "hypothesis", "expected_behavior")}
    args.update(occurrence=1, causal_revision=None)
    client = continuation.ScriptedClient([
        [call("replace_text", args, "mutate")],
        [call("run_check", {"check_id": "existing-unit-tests"}, "verify")],
        [call("finish_task", {}, "finish")]])
    result = continuation.rehearse(branch, client)
    assert result["result"]["terminal"] == "EVALUATOR_PASS", result
    assert result["source_settled_nanos"] == branch.initial_spent_nanos > 0
    assert result["simulated_calls"] == 3 and result["new_billed_cost_nanos"] == 0
    assert result["result"]["cost_nanos"] == (result["source_settled_nanos"]
                                              + result["simulated_new_cost_nanos"])


def test_nondefault_reserve_and_retention_are_restored(source, tmp_path):
    envelope = DevJournal(source.root, source.run_id).load_envelope().model_copy(update={
        "evaluation_reserve_seconds": 330, "retained_source_chars": 48000})
    request = continuation.restored_request(source, envelope, tmp_path)
    assert request.evaluation_reserve_seconds == 330 and request.retained_source_chars == 48000
    assert request.limits == envelope.limits


def test_time_normalization_does_not_hide_budget_or_plan_drift():
    from types import SimpleNamespace
    from unittest.mock import patch

    from patchloop.dev import native_compaction

    state = {"remaining_budget": {"active_wall_time_seconds": 1200,
             "total_active_wall_time_seconds": 1530, "evaluation_reserve_seconds": 330,
             "model_calls": 16}, "working_plan": "unchanged"}
    original = {"input": [{"content": canonical_json({"state": state})}]}
    branch = SimpleNamespace(original=original, packet={})
    current = copy.deepcopy(original)
    def change(key, value):
        view = json.loads(current["input"][-1]["content"])
        view["state"]["remaining_budget"][key] = value
        current["input"][-1]["content"] = canonical_json(view)
    change("active_wall_time_seconds", 1190)
    change("total_active_wall_time_seconds", 1520)
    with patch.object(native_compaction, "prepared_input", lambda *a: "ok"):
        with continuation.first_input(branch) as first:
            assert native_compaction.prepared_input(None, None, None, current, None) == "ok"
            assert first == [True]
        change("model_calls", 40)
        with continuation.first_input(branch), pytest.raises(ContractError, match="elapsed time"):
            native_compaction.prepared_input(None, None, None, current, None)


def test_packet_tamper_and_variant_identity(saved_packet, tmp_path):
    path = Path(saved_packet["packet"])
    assert checkpoint.validate(path, saved_packet["packet_hash"])["verified"]
    with pytest.raises(ContractError, match="packet identity"):
        checkpoint.validate(path, sha256_bytes(b"different"))
    assert checkpoint.program_variant("FLAG = False\nrun()\n",
        "Replace the single line FLAG = False with FLAG = True.") == "FLAG = True\nrun()\n"
    with pytest.raises(ContractError, match="unique"):
        checkpoint.program_variant("FLAG = False\nFLAG = False\n",
            "Replace the single line FLAG = False with FLAG = True.")


def test_unknown_target_rejected(source):
    with pytest.raises(ContractError, match="unique selected"):
        checkpoint.load(source, "unknown")
