"""Bounded integration checks for shared-budget verification roles; no provider I/O."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest
from test_dev_probe_cases import ExecutingProbe, mock_request
from test_dev_segments import assert_submitted, configured, records
from test_dev_tools import mutation_call, read_calls
from test_probe_purpose import probe

from diagnostics import verification_role as role
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner, segments
from patchloop.dev.contracts import DevLimits, DevModelTurn, PublicTurnDecision, RequestedTool
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("verification-role tests cannot contact a provider")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def report(action_id="verify-report"):
    return RequestedTool(name=role.REPORT_TOOL, action_id=action_id,
        arguments={"assessment": "Current public caller reproduces the expected output. "
                   "Helper/suite results alone would not establish it; no hidden-test claim."},
        turn_decision=PublicTurnDecision(mode="finish", basis="Review the observed public result."))


def run_phases(tmp_path, monkeypatch, smoke_package, arm, *, adapter=None):
    backend = ExecutingProbe()

    class Phases(MockDevAdapter):
        checked = False

        def next_turn(self, context, tools):
            phase = json.loads(context)["verification_phase"]["phase"]
            if phase == "verify":
                if not self.checked:
                    self.checked = True
                    return DevModelTurn(tool_calls=[probe(smoke_package.public, "verify-probe")])
                return DevModelTurn(tool_calls=[report()])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", adapter or Phases)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1", "planning_policy": "brief-v1",
        "history_search_policy": "public-v1", "limits": DevLimits(),
    })
    with role.assigned(arm):
        result = runner.run_dev(request)["runs"][0]
    path, = (request.state_root / "runs").glob("*.jsonl")
    journal = DevJournal(request.state_root, path.stem)
    return result, journal, ArtifactStore(request.state_root / "artifacts"), backend


@pytest.mark.parametrize("arm", ["A", "B"])
def test_both_arms_reach_isolated_evaluation_and_share_accounting(
    tmp_path, monkeypatch, smoke_package, arm,
):
    result, journal, store, backend = run_phases(tmp_path, monkeypatch, smoke_package, arm)
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 1
    events = journal.events()
    boundaries = [e["payload"] for e in events if e["event_type"] == role.PHASE_EVENT]
    assert [r["phase"] for r in boundaries] == ["initial", "verify", "final"]
    assert boundaries[1]["candidate_present"]
    assert [r["usage"]["model_calls"] for r in boundaries] == [0, 3, 5]
    assert runner._restore_counters(journal).model_calls == 6
    # The first inspection is a real two-action read batch, not one action.
    assert runner._restore_counters(journal).tool_actions == 7
    assert result["evaluator"]["claim_eligible"] is False
    phases = list(role.phased_events(events))
    initial_ids = {e["payload"]["action_id"] for e, phase, _ in phases
                   if phase == "initial" and e["event_type"] == "action_finished"}
    verify_ids = {e["payload"]["action_id"] for e, phase, _ in phases
                  if phase == "verify" and e["event_type"] == "action_finished"}
    for e, phase, _ in phases:
        if e["event_type"] != "turn_started":
            continue
        items = json.loads(store.read_bytes(Artifact.model_validate(
            e["payload"]["model_input_artifact"])))
        native_ids = {v["call_id"] for v in items if v.get("type") == "function_call"}
        if arm == "B" and phase == "verify":
            assert not native_ids & initial_ids
        if arm == "B" and phase == "final":
            assert not native_ids & verify_ids
        assert e["payload"]["context_request_sizes"]["request_bytes"] <= 1_048_576
    delivered = [e["payload"] for e in events
                 if e["event_type"] == "verification_phase_dispatched"]
    assert [v["phase"] for v in delivered] == ["initial"] * 3 + ["verify"] * 2 + ["final"]
    for stream in {"repair", "verifier"} if arm == "B" else {"repair"}:
        owner = type("Owner", (), {"phase": "final", "stream": stream})()
        binding, _ = segments.active(role.JournalView(journal, owner, stream=True), store)
        assert binding is not None
        segments.load_binding(binding, store)


def bound(gateway_factory, tmp_path, *, arm="B"):
    gateway, journal, _ = gateway_factory()
    controller = role.VerificationRun(gateway, arm)
    ledger = DevCostLedger(Decimal("0.88"), pricing_for_model("gpt-5.4-mini-2026-03-17"))
    counters = runner._RunCounters()
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "limits": DevLimits(), "context_policy": "segmented-v1", "planning_policy": "brief-v1"})
    controller.bind(request=request, counters=counters, ledger=ledger,
                    store=ArtifactStore(journal.root / "artifacts"), resuming=False)
    return controller, gateway, journal, counters, ledger


def test_phase_caps_preserve_counters_and_unused_budget(gateway_factory, tmp_path):
    controller, gateway, journal, counters, ledger = bound(gateway_factory, tmp_path)
    counters.model_calls = 28
    counters.protocol_recoveries = 1
    ledger.spent_nanos = 300_000_000
    controller.before_turn()
    assert controller.phase == "verify" and not gateway.current_diff.patch
    assert counters.model_calls == 28 and counters.protocol_recoveries == 1
    assert controller.cost_reserve() == 380_000_000
    admission = ledger.admit(60_000, future_cost_reserve_nanos=controller.cost_reserve())
    assert admission.reserved_cost_nanos <= 200_000_000
    counters.model_calls += 6
    ledger.spent_nanos += 150_000_000
    controller.before_turn()
    assert controller.phase == "final"
    assert controller.remaining()["model_calls"] == 6
    assert controller.remaining()["cost_nanos"] == 430_000_000
    assert controller.report["status"] == "VERIFICATION_INCOMPLETE"
    assert controller.cost_reserve() == 0
    assert [e["event_type"] for e in journal.events()].count("verification_incomplete") == 1


def test_cost_phase_switch_and_uncertain_action_stop(gateway_factory, tmp_path):
    controller, _, journal, _, ledger = bound(gateway_factory, tmp_path)
    ledger.spent_nanos = 479_999_999
    assert ledger.admit(60_000, future_cost_reserve_nanos=controller.cost_reserve()) is None
    assert controller.cost_limited(60_000) and controller.phase == "verify"
    journal.append("action_started", {"action_id": "unfinished", "input_hash": "H"})
    with pytest.raises(RecoveryError, match="unresolved action"):
        controller._incomplete("test")


def test_report_grammar_is_scoped_and_cannot_mix_with_actions():
    call = report()
    with pytest.raises(ContractError, match="unknown"):
        role._BASE_VALIDATE([call])
    with role.assigned("A"):
        assert runner.validate_tool_batch(
            [call], allowed_tools={role.REPORT_TOOL}) == "single_action"
        with pytest.raises(ContractError):
            runner.validate_tool_batch([call], allowed_tools={"read_file"})
        with pytest.raises(ContractError):
            runner.validate_tool_batch([call, call.model_copy(update={"action_id": "second"})])
    with pytest.raises(ContractError, match="unknown"):
        role._BASE_VALIDATE([call])


def test_history_exact_pages_and_keyword_search_exclude_repair_interpretations():
    owner = type("Owner", (), {"phase": "verify"})()
    history = role.ObservationHistory(owner)
    body = {"call": {"action_id": "a", "tool": "read_file", "arguments": {
        "path": "module.py", "turn_decision": {"basis": "REPAIR_HYPOTHESIS"}}},
        "result": {"tool": "read_file", "status": "succeeded", "output": {
            "inspection_intent": "REPAIR_HYPOTHESIS", "spans": [
                {"path": "module.py", "content": "def original(): return 1", "start_line": 1,
                 "end_line": 1, "file_hash": "H"}]}}}
    original = history._add("public_tool_exchange", body,
                            {"first_delivered_sequence": 1}, "D")
    for query in ("original", original):
        output = history.search(query, current_diff_hash="D")
        assert "REPAIR_HYPOTHESIS" not in json.dumps(output)
        assert "def original()" in json.dumps(output)
        assert output["records"][0]["origin"]["original_record_id"] == original
    owner.phase = "final"
    assert "REPAIR_HYPOTHESIS" in json.dumps(history.search(original, current_diff_hash="D"))
    from patchloop.dev.conversation import SEGMENT_RULES

    assert "verification_phase" in SEGMENT_RULES.mutable_fields
    supplied, = list(SEGMENT_RULES.observations({
        "verification_phase": {"phase": "initial", "report": "MUTABLE_REPORT"},
        "supplied_public_case": {"observed": "ORIGINAL_PUBLIC_OBSERVATION"},
    }))
    history._add("supplied_public_observation", supplied, {"first_delivered_sequence": 1}, "D")
    owner.phase = "verify"
    found = json.dumps(history.search("ORIGINAL_PUBLIC_OBSERVATION", current_diff_hash="D"))
    assert "ORIGINAL_PUBLIC_OBSERVATION" in found and "MUTABLE_REPORT" not in found


@pytest.mark.parametrize("arm", ["A", "B"])
def test_counted_wire_and_native_reasoning_follow_one_ledger(tmp_path, monkeypatch, arm):
    class Phases(MockDevAdapter):
        def next_turn(self, context, tools):
            phase = json.loads(context)["verification_phase"]["phase"]
            if phase == "verify":
                assert role.REPORT_TOOL in {t["name"] for t in tools}
                assert not {"replace_text", "finish_task"} & {t["name"] for t in tools}
                call = report()
                call.turn_decision.basis = "VERIFIER_NATIVE_ONLY"
                return DevModelTurn(tool_calls=[call])
            turn = super().next_turn(context, tools)
            if phase == "initial":
                for call in turn.tool_calls:
                    call.turn_decision.basis = "REPAIR_AUTHORED_SENTINEL"
            return turn

    request, inputs, counted, states = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=Phases("csv-quoted-newline"))
    request = request.model_copy(update={"max_cost_usd": Decimal("0.88"),
        "limits": DevLimits(), "completion_cost_policy": "per-call-v1"})
    with role.assigned(arm):
        result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert inputs == counted
    journal, _ = records(request)
    events = journal.events()
    assert result["call_counts"]["model"] == len(inputs) == 5
    assert [s["verification_phase"]["phase"] for s in states] == [
        "initial", "initial", "initial", "verify", "final"]
    verify_cipher = [i for i in inputs[3] if i.get("type") == "reasoning"]
    # In this repair the unchanged result boundary also resets A at entry.
    assert not verify_cipher
    boundaries = [e["payload"]["reason"] for e in events
                  if e["event_type"] == segments.EVENT]
    assert boundaries[1] == ("initial" if arm == "B"
                             else "major_result_followup_completed")
    if arm == "B":
        assert "cipher-3" not in canonical_json(inputs[4])
        assert "REPAIR_AUTHORED_SENTINEL" not in canonical_json(inputs[3])
        assert "VERIFIER_NATIVE_ONLY" not in canonical_json(inputs[4])
    assert states[4]["verification_phase"]["report"]["output"]["repair_success"] == "not_assessed"
    assert states[4]["verification_phase"]["report_currency"] == "current"
    assert len([e for e in events if e["event_type"] == "provider_call_finished"]) == 5
    ledger_events = [e for e in events if e["event_type"] == "provider_call_started"]
    assert len(ledger_events) == 5
    assert all(s["verification_phase"]["remaining"]["cost_nanos"] > 0 for s in states)


def test_verification_rejects_mutation_and_persists_report_once(
    gateway_factory, tmp_path, monkeypatch,
):
    # Exercise the real gateway idempotency and read-only mask without another runner.
    monkeypatch.setattr("conftest.DevToolGateway", lambda **kw:
                        role.VerificationGateway(arm="B", **kw))
    gateway, journal, _ = gateway_factory()
    controller = gateway.run_extension
    controller.bind(request=mock_request(tmp_path, policy="none").model_copy(update={
        "limits": DevLimits(), "context_policy": "segmented-v1"}),
        counters=runner._RunCounters(), ledger=None,
        store=ArtifactStore(journal.root / "artifacts"), resuming=False)
    controller._start("verify", "fixture")
    for name in ("replace_text", "finish_task"):
        with pytest.raises(ContractError, match="read-only"):
            gateway.execute(report().model_copy(update={"name": name}))
    with role.assigned("B"):
        first = gateway.execute(report())
        replayed = gateway.execute(report())
        assert replayed.replayed and replayed.model_copy(update={"replayed": False}) == first
    assert first.status == "succeeded"
    controller.before_turn()
    assert controller.phase == "final" and controller.report["action_id"] == "verify-report"
    assert sum(e["event_type"] == "action_finished" for e in journal.events()) == 1
    with pytest.raises(ContractError, match="unavailable"):
        gateway.execute(report("another"))
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    feedback = json.loads(controller.context("{}"))["verification_phase"]
    assert feedback["report_currency"] == "historical"
    assert feedback["report"] == controller.report
    with pytest.raises(ContractError, match="resume"):
        controller.bind(request=controller.request, counters=controller.counters, ledger=None,
                        store=controller.store, resuming=True)


def test_phase_transition_accepts_only_settled_rejection_and_rejects_overrun(
    gateway_factory, tmp_path,
):
    controller, _, journal, counters, _ = bound(gateway_factory, tmp_path)
    counters.model_calls = 28
    counters.protocol_recoveries = 1
    journal.append("turn_decision_recorded", {"turn_id": "rejected"})
    with pytest.raises(RecoveryError, match="unfinished batch"):
        controller.before_turn()
    journal.append("protocol_correction", {"turn_id": "rejected"})
    controller.before_turn()
    assert controller.phase == "verify" and counters.protocol_recoveries == 1
    counters.model_calls += 7
    with pytest.raises(RecoveryError, match="envelope exceeded"):
        controller.before_turn()


def test_interrupted_report_delivery_cannot_resume_or_duplicate_actions(
    tmp_path, monkeypatch, smoke_package,
):
    from test_dev_runner import _crash_journal_once, _SimulatedCrash

    _crash_journal_once(monkeypatch, event_type=role.PHASE_EVENT, when="after",
                        predicate=lambda p: p["phase"] == "final")
    with pytest.raises(_SimulatedCrash):
        run_phases(tmp_path, monkeypatch, smoke_package, "B")
    root = mock_request(tmp_path, policy="none").state_root
    journal_path, = (root / "runs").glob("*.jsonl")
    journal = DevJournal(root, journal_path.stem)
    before = journal.path.read_bytes()
    assert sum(e["event_type"] == "action_finished"
               and e["payload"]["result"]["tool"] == role.REPORT_TOOL
               for e in journal.events()) == 1
    # The fixed allocation has no continuation approval or reconstructed role state.
    owner = role.VerificationRun.__new__(role.VerificationRun)
    owner.journal = journal
    with pytest.raises(ContractError, match="does not resume"):
        owner.bind(request=None, counters=None, ledger=None, store=None, resuming=True)
    assert journal.path.read_bytes() == before


def test_b_rejected_batch_crosses_existing_size_boundary_without_new_correction(
    tmp_path, monkeypatch,
):
    from test_dev_segment_rejection import RejectedEdits

    class Phases(RejectedEdits):
        def next_turn(self, context, tools):
            if json.loads(context)["verification_phase"]["phase"] == "verify":
                return DevModelTurn(tool_calls=[report()])
            return super().next_turn(context, tools)

    request, inputs, counted, states = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=Phases())
    request = request.model_copy(update={"max_cost_usd": Decimal("0.88"),
        "limits": DevLimits(), "completion_cost_policy": "per-call-v1"})
    count = runner.OpenAIResponsesAdapter.count_input_tokens_v2

    def size(self, payload, **kwargs):
        actual = count(self, payload, **kwargs)
        return 60_001 if len(counted) == 3 else actual

    monkeypatch.setattr(runner.OpenAIResponsesAdapter, "count_input_tokens_v2", size)
    with role.assigned("B"):
        result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert len(counted) == len(inputs) + 1 == 7
    assert states[2]["remaining_budget"]["consecutive_protocol_corrections"] == 0
    journal, _ = records(request)
    events = journal.events()
    rejected, = [e for e in events if e["event_type"] == "protocol_correction"]
    assert not any(e["payload"].get("turn_id") == rejected["payload"]["turn_id"]
                   for e in events if e["event_type"] == "tool_batch_started")
