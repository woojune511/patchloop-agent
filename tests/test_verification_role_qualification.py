"""Offline qualification of selected evidence delivery and shared resource limits."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest
from frozen_stage_support import pin_pre_stage_prompt
from test_dev_probe_cases import ExecutingProbe
from test_dev_segments import assert_submitted, configured, records
from test_probe_purpose import probe
from test_verification_role import report, run_phases

from diagnostics import verification_role as role
from diagnostics import verification_role_panel as panel
from diagnostics import verification_role_qualification as qualification
from patchloop.contracts import Artifact
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevLimits, DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import SEGMENT_RULES, reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.util import canonical_json, sha256_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    pin_pre_stage_prompt(monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail("return qualification must not contact a provider")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def selection_script(public_task):
    class Phases(MockDevAdapter):
        probes = 0

        def next_turn(self, context, tools):
            state = json.loads(context)
            if state["verification_phase"]["phase"] != "verify":
                return super().next_turn(context, tools)
            if self.probes < 2:
                self.probes += 1
                call = probe(public_task, "selected-probe-" + str(self.probes))
                call.turn_decision.basis = "VERIFIER_NATIVE_ONLY"
                return DevModelTurn(tool_calls=[call])
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
    return Phases


def selected_outputs(items):
    _, exchanges, _ = SEGMENT_RULES.inventory(items)
    return {i["call_id"]: json.loads(i["output"]) for i in exchanges.values()
            if i["type"] == "function_call_output" and i["call_id"].startswith("selected-probe-")}


@pytest.mark.parametrize("arm", ["A", "B"])
def test_selected_probe_return_qualification(tmp_path, monkeypatch, smoke_package, arm):

    result, journal, store, backend = run_phases(
        tmp_path, monkeypatch, smoke_package, arm, adapter=selection_script(smoke_package.public))
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
    assert receipt["passed"]
    assert all(r["evidence_delivery"] == "complete" for r in question["evidence"])
    assert {r["action_id"] for r in receipt["report"]["output"]["references"]} == selected
    assert {r["input_hash"] for r in question["evidence"]} == {
        r["input_hash"] for r in selected_outputs(items).values()}
    if arm == "B":
        assert "VERIFIER_NATIVE_ONLY" not in canonical_json(items)
        assert "select-observations" not in ids  # Unselected verifier exchange is excluded.
        for value in selected_outputs(items).values():
            assert not {"memory_update_result", "working_notes_after_batch"} & value.keys()
        controller = role.VerificationRun.__new__(role.VerificationRun)
        controller.arm, controller.phase, controller.journal = "B", "final", journal
        assert len(controller.public_evidence(state)) == 4
        changed = {**state, "current_diff": {"patch_hash": "different-candidate"}}
        assert controller.public_evidence(changed) == []
        # Exercise the same assembly with a valid, still-open repair segment:
        # the first inspection precedes any major-result boundary.
        events = journal.events()
        last = next(i for i, e in enumerate(events) if e["event_type"] == "tool_batch_finished")
        continuation = DevJournal(tmp_path / "continuation", journal.run_id)
        continuation.path.parent.mkdir(parents=True, exist_ok=True)
        continuation.path.write_bytes(b"".join(journal.path.read_bytes().splitlines(True)[:last+1]))
        before, _ = segments.active(continuation, store)
        extra = [i for i in exchanges.values() if i.get("call_id") in selected]
        continued = runner._build_model_input(journal=continuation, artifact_store=store,
            context=store.read_bytes(Artifact.model_validate(
                final["payload"]["context_artifact"])).decode(),
            latest_tool_results=continuation.latest_tool_batch_results(),
            context_policy="segmented-v1", planning_policy="brief-v1",
            additional_public_exchanges=extra)
        assert segments.active(continuation, store)[0] == before
        assert set(selected_outputs(continued)) == selected
        assert not any(i.get("call_id") in selected for i in continued)
        assert reconstruct_state(continued, context_policy="segmented-v1")["working_notes"][
            "open_question"][
            "evidence_delivery"] == "complete"


@pytest.mark.parametrize("limit", ["tokens", "bytes", "unknown"])
def test_return_evidence_obeys_existing_size_and_uncertainty_stops(
    tmp_path, monkeypatch, smoke_package, limit,
):
    request, inputs, counted, states = configured(monkeypatch, tmp_path, planning="brief-v1",
        script=selection_script(smoke_package.public)("csv-quoted-newline"))
    backend = ExecutingProbe()
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    request = request.model_copy(update={
        "enable_probes": True, "history_search_policy": "public-v1",
        "max_cost_usd": Decimal("0.88"), "limits": DevLimits(max_accepted_mutations=4),
        "completion_cost_policy": "per-call-v1"})
    count = runner.OpenAIResponsesAdapter.count_input_tokens_v2
    sizes = segments.request_sizes

    def selected_return(items):
        return (reconstruct_state(items, context_policy="segmented-v1")[
                    "verification_phase"]["phase"] == "final"
                and bool(selected_outputs(items)))

    def limited_count(self, payload, **kwargs):
        if limit in {"tokens", "unknown"} and selected_return(payload["input"]):
            counted.append(payload["input"])
            if limit == "unknown":
                raise TimeoutError("unknown fake count")
            return segments.MAX_INPUT_TOKENS + 1
        return count(self, payload, **kwargs)

    def limited_sizes(payload):
        value = sizes(payload)
        if limit == "bytes" and selected_return(payload["input"]):
            value["request_bytes"] = segments.MAX_REQUEST_BYTES + 1
        return value

    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", limited_count)
    monkeypatch.setattr(segments, "request_sizes", limited_sizes)
    with role.assigned("B"):
        result = runner.run_dev(request)["runs"][0]
    assert backend.calls == 2  # Public quotations never re-execute the probes.
    if limit == "unknown":
        assert result["terminal"] == "COUNT_TIMEOUT_OR_UNKNOWN"
        assert len(inputs) == 7 and len(counted) == 8
        assert selected_return(counted[-1])
        assert all(s["verification_phase"]["phase"] != "final" for s in states)
        return
    assert_submitted(result)
    assert not selected_outputs(inputs[-1])
    assert states[-1]["working_notes"]["open_question"]["evidence_delivery"] == "incomplete"
    assert len(states[-1]["verification_phase"]["report"]["output"]["references"]) == 2
    journal, store = records(request)
    owner = type("Owner", (), {"phase": "final", "stream": "repair"})()
    _, handoff = segments.active(role.JournalView(journal, owner, stream=True), store)
    assert handoff["evidence_manifest"]["optional_bodies_omitted"]
    assert len(inputs) == 8 and len(counted) == (9 if limit == "tokens" else 8)


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
