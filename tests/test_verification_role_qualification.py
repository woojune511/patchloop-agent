"""Offline qualification checks, including a currently blocking return-path defect."""
from __future__ import annotations

import json

import pytest
from test_probe_purpose import probe
from test_verification_role import report, run_phases

from diagnostics import verification_role as role
from diagnostics import verification_role_panel as panel
from diagnostics import verification_role_qualification as qualification
from patchloop.contracts import Artifact
from patchloop.dev.contracts import DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import SEGMENT_RULES, reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.errors import ContractError
from patchloop.util import sha256_json


@pytest.mark.parametrize("arm", ["A", "B"])
def test_selected_probe_return_qualification(tmp_path, monkeypatch, smoke_package, arm):
    class Phases(MockDevAdapter):
        probes = 0

        def next_turn(self, context, tools):
            state = json.loads(context)
            if state["verification_phase"]["phase"] != "verify":
                return super().next_turn(context, tools)
            if self.probes < 2:
                self.probes += 1
                return DevModelTurn(tool_calls=[probe(
                    smoke_package.public, "selected-probe-" + str(self.probes))])
            if self.probes > 2:
                return DevModelTurn(tool_calls=[report()])
            self.probes += 1
            call = RequestedTool(name="read_file", action_id="select-observations", arguments={
                "path": self.mutation.path, "start_line": 1, "end_line": 80},
                turn_decision=PublicTurnDecision(
                mode="inspect", basis="Review both executed observations.",
                evidence_goal="Relate the current source to the two observations.", memory_update={
                    "findings": [], "open_question": {
                        "text": "What do these two public executions establish?", "evidence": [
                            {"kind": "tool_result", "action_id": "selected-probe-1",
                             "role": "primary"},
                            {"kind": "tool_result", "action_id": "selected-probe-2",
                                 "role": "countercheck"},
                            ]}}))
            return DevModelTurn(tool_calls=[call])

    result, journal, store, backend = run_phases(
        tmp_path, monkeypatch, smoke_package, arm, adapter=Phases)
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 2
    final = next(e for e, phase, _ in role.phased_events(journal.events())
                 if phase == "final" and e["event_type"] == "turn_started")
    items = json.loads(store.read_bytes(Artifact.model_validate(
        final["payload"]["model_input_artifact"])))
    state = reconstruct_state(items, context_policy="segmented-v1")
    question = state["working_notes"]["open_question"]
    assert len(question["evidence"]) == 2
    _, exchanges, _ = SEGMENT_RULES.inventory(items)
    ids = {x["call_id"] for x in exchanges.values() if x["type"] == "function_call_output"}
    selected = {"selected-probe-1", "selected-probe-2"}
    receipt = {"arm": arm, "selected_action_ids": sorted(selected),
        "delivered_selected_action_ids": sorted(ids & selected),
        "question": question, "report": state["verification_phase"]["report"],
        "input_artifact": final["payload"]["model_input_artifact"],
        "request_sizes": final["payload"]["context_request_sizes"],
        "passed": selected <= ids}
    qualification.save(tmp_path, "return-qualification.json", receipt)
    # This is a defect detector, not permission to accept the B packet. The
    # qualification receipt remains failed until the production path is repaired.
    assert receipt["passed"] == (arm == "A")
    assert all(r["evidence_delivery"] == ("complete" if arm == "A" else "incomplete")
               for r in question["evidence"])


def test_minimum_funding_is_not_a_useful_output_guarantee():
    state = {"action_horizon": {"mutation_completion_horizon": {"minimum_calls": 3}}}
    result = qualification.funding(60_000, state)
    assert result["verification"]["funded"] and result["final"]["funded"]
    assert result["maximum_calls_at_floor"] == 4
    assert result["six_full_outputs_cost_nanos"] == 945_000_000
    assert not result["useful_output_guaranteed"]
    assert not result["verification"]["funded_after_max_first_output"]


def test_failed_return_delivery_blocks_freeze_even_when_entry_and_funding_pass(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(panel, "initial_pair", lambda _: {"tools_equal": True})
    state = {"action_horizon": {"mutation_completion_horizon": {"minimum_calls": 3}}}
    arm = {"sizes": {"request_bytes": 90_000, "largest_encrypted_item_bytes": 0},
           "tokens": {"upper": 30_000}, "funding": qualification.funding(30_000, state)}
    summary = {"head": "fixture", "runtime_hash": "fixture", "implementation": {},
        "contract_hash": sha256_json(role.contract()), "provider_calls": 0, "input_count_calls": 0,
        "baseline_exact_requests": 1, "rows": [{"common_context_equal": True,
            "schemas_equal": True, "contrast_present": True, "arms": {"A": arm, "B": arm}}]}
    qualification.save(tmp_path, "summary.json", summary)
    gates = qualification.qualification_receipts(tmp_path, summary, {},
                                                 {"A": {"passed": True}, "B": {"passed": False}})
    validation = {**summary, "verification_role": gates}
    qualification.save(tmp_path, "validation.json", validation)
    with pytest.raises(ContractError, match="same_snapshot_capture"):
        panel.qualification(tmp_path / "validation.json")
