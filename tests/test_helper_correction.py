"""Short offline controls for first-repair helper correction and resource limits."""

from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_recovery import funding
from test_dev_completion_resources import Gateway, counters
from test_dev_planning import request as mock_request
from test_dev_probe_cases import ExecutingProbe
from test_dev_probe_cases import call as saved_call
from test_dev_probes import FakeProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_tools import read_calls
from test_finish_reproduction_budget import snapshot
from test_original_obligation import restore

from patchloop.dev import helper_recovery, runner
from patchloop.dev.completion_budget import (
    CompletionState,
    completion_budget,
    minimum_successor_calls,
)
from patchloop.dev.contracts import DevLimits, DevModelTurn, RequestedTool
from patchloop.dev.cost import COMPLETION_MINIMUM_POLICY, COMPLETION_RECOVERY_POLICY
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.errors import ActionConflict

QUESTION = "Can the diagnostic fixture preserve this input text?"
BAD = "from pathlib import Path\nroot = Path(reproduction_workspace())\n"
GOOD = (
    "from pathlib import Path\nfrom tempfile import TemporaryDirectory\n"
    "with TemporaryDirectory() as directory:\n"
    "    root = Path(directory)\n"
    "    (root / 'input.txt').write_text('public fixture')\n"
    "    print((root / 'input.txt').read_text())\n"
)


def helper(action="bad", source=BAD):
    return RequestedTool(name="run_probe", action_id=action, arguments={
        "question": QUESTION, "python_source": source, "purpose": {"kind": "helper"},
        "replay_action_id": None, "call_path": None,
    }, turn_decision={"mode": "verify", "basis": "Observe the same diagnostic question."})


def state(gateway):
    return gateway.completion_verification(diff_hash=gateway.current_diff_hash)["helper_correction"]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("offline only"))


def test_preflight_correction_executes_once_and_survives_completed_result_recovery(
    gateway_factory, monkeypatch,
):
    gateway, journal, _ = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    bad = helper()
    rejected = gateway.execute(bad)
    assert rejected.status == "failed" and backend.calls == 0
    assert rejected.output["probe_stage"] == "preflight_rejected"
    assert rejected.output["helper_program_error"]["kind"] == "unavailable_api"
    assert state(gateway)["status"] == "pending"
    assert state(gateway)["python_source"] == BAD
    assert gateway.execute(bad).replayed
    correction = helper("corrected", GOOD)
    _crash_journal_once(monkeypatch, event_type="probe_execution_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(correction)
    assert backend.calls == 1
    gateway = restore(gateway, backend=backend, policy="none")
    completed = gateway.execute(correction)
    assert backend.calls == 1 and "public fixture" in completed.output["stdout"]
    assert completed.output["request_validation"]["correction"]["status"] == "corrected"
    assert completed.output["helper_recovery_link"]["root_action_id"] == "bad"
    assert state(gateway)["status"] == "execution_returned"
    assert state(gateway)["behavior_verdict"] == "not_assessed"
    assert gateway.completion_verification(diff_hash=gateway.current_diff_hash)[
        "baseline_failure_case_ids"] == []
    before = journal.path.read_bytes()
    assert gateway.execute(correction).replayed and journal.path.read_bytes() == before
    changed = copy.deepcopy(correction)
    changed.arguments["python_source"] += "\n# other input"
    with pytest.raises(ActionConflict):
        gateway.execute(changed)
    # A second malformed helper never mints a fresh correction ticket.
    assert gateway.execute(helper("another-bad")).status == "failed"
    assert state(gateway)["root_action_id"] == "bad" and state(gateway)["remaining_attempts"] == 0


@pytest.mark.parametrize("mode", ["unchanged", "new_question", "read", "syntax"])
def test_only_one_changed_source_for_the_same_question_is_admitted(gateway_factory, mode):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status="passed")
    gateway.execute(helper())
    attempted = helper("attempt", GOOD)
    if mode == "unchanged":
        attempted.arguments["python_source"] = BAD
    elif mode == "new_question":
        attempted.arguments["question"] += " A different question."
    elif mode == "syntax":
        attempted.arguments["python_source"] = "if :"
    else:
        attempted = read_calls()[0]
    result = gateway.execute(attempted)
    assert result.status == "failed" and gateway.probe_sandbox.calls == 0
    assert state(gateway)["status"] == "verification_incomplete"
    gateway = restore(gateway, policy="none")
    assert gateway.execute(helper("too-late", GOOD)).status == "failed"
    assert gateway.probe_sandbox.calls == 0


@pytest.mark.parametrize("status", ["failed", "timeout"])
def test_runtime_failures_do_not_create_a_setup_correction(gateway_factory, status):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status=status)
    gateway.execute(helper("runtime-error", "raise NameError('target or setup unknown')"))
    assert state(gateway)["status"] == "not_needed"
    gateway.execute(helper())
    result = gateway.execute(helper("corrected", "assert False, 'observed target result'"))
    assert result.output["status"] == status
    expected = "execution_returned" if status == "failed" else "verification_incomplete"
    assert state(gateway)["status"] == expected
    assert state(gateway)["behavior_verdict"] == "not_assessed"


def test_uncertain_dispatch_is_never_reexecuted(gateway_factory, monkeypatch):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status="passed")
    gateway.execute(helper())
    _crash_journal_once(monkeypatch, event_type="probe_execution_started", when="after")
    corrected = helper("corrected", GOOD)
    with pytest.raises(_SimulatedCrash):
        gateway.execute(corrected)
    gateway = restore(gateway, policy="none")
    result = gateway.execute(corrected)
    assert result.error_code == "RECOVERY_ERROR"
    assert gateway.probe_sandbox.calls == 0
    assert state(gateway)["status"] == "verification_incomplete"


@pytest.mark.parametrize("phase", ["first_rejection", "correction_rejection"])
def test_lost_preflight_rejection_is_restored_without_dispatch(gateway_factory, monkeypatch, phase):
    gateway, journal, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status="passed")
    call = helper()
    if phase == "correction_rejection":
        gateway.execute(call)
        call = helper("wrong-question", GOOD)
        call.arguments["question"] += " changed"
    _crash_journal_once(monkeypatch, event_type="action_started", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(call)
    gateway = restore(gateway, policy="none")
    recovered = gateway.execute(call)
    assert recovered.status == "failed" and gateway.probe_sandbox.calls == 0
    assert not any(e["event_type"] == "probe_execution_started" for e in journal.events())
    expected = "pending" if phase == "first_rejection" else "verification_incomplete"
    assert state(gateway)["status"] == expected


def test_saved_and_legacy_programs_keep_exact_replay_without_a_null_question_ticket(
    gateway_factory,
):
    gateway, _, _ = gateway_factory()
    gateway.probe_policy = "cases-v1"
    backend = gateway.probe_sandbox = FakeProbe(status="failed")
    original = saved_call("legacy", source=BAD, reference=None, save=True)
    result = gateway.execute(original)
    assert result.status == "succeeded" and backend.calls == 1
    case_id = result.output["case_comparison"]["case_id"]
    selected = saved_call("case-replay", case_id=case_id)
    selected.arguments["purpose"] = {"kind": "helper"}
    # Both absent and explicit-null raw fields resolve the same saved program.
    selected.arguments.pop("question")
    selected.arguments.pop("python_source")
    assert gateway.execute(selected).status == "succeeded"
    assert backend.calls == 2 and state(gateway)["status"] == "not_needed"


@pytest.mark.parametrize("short", [None, "model", "tool", "money"])
def test_correction_keeps_minimum_repair_original_replay_check_and_finish(short):
    gateway = Gateway(initial=True)
    snap = snapshot(gateway, status="unverified", pending_count=0)
    snap.completion_verification["helper_correction"] = {
        "status": "pending", "blocked": True, "question": QUESTION,
    }
    selected = runner._tool_policy(
        gateway, counters(model=3 if short == "model" else 4,
                          tools=4 if short == "tool" else 5), DevLimits(), snapshot=snap,
        cost_ledger=ledger_for_slots(3 if short == "money" else 4),
        completion_cost_policy=COMPLETION_MINIMUM_POLICY, _preview_inspection=False,
    )
    assert selected.minimum_completion_calls == 4
    assert selected.minimum_completion_tool_actions == 5
    if short:
        assert selected.workflow_gate == "verification_incomplete"
        assert selected.allowed_tools == {"stop_task"}
    else:
        assert selected.workflow_gate == "needs_helper_correction"
        assert selected.allowed_tools == {"run_probe", "stop_task"}
        assert selected.max_parallel_reads == 0
        guidance = runner._completion_guidance(snap, selected)
        assert guidance["next_action"]["question"] == QUESTION
        public = compact_model_state({"action_horizon": runner._repair_inspection_payload(
            selected)}, [])
        assert public["action_horizon"]["helper_correction"] == selected.helper_correction


def test_forecast_counts_the_corrected_execution_once_and_never_grows_limits():
    baseline = CompletionState(
        check_count=1, remaining_check_count=1, unused_check_count=1,
        unrun_recoverable_check=True, requires_mutation=True, anchor_available=True,
        remaining_mutations=4, mutation_retry_available=True, reproduction_case_count=1,
    )
    before = completion_budget(baseline)
    pending = replace(baseline, helper_correction_pending=True)
    after = completion_budget(pending)
    assert after.minimum == before.minimum + 1
    assert after.protected == before.protected + 1
    assert after.minimum_tool_actions == before.minimum_tool_actions + 1
    assert after.protected_tool_actions == before.protected_tool_actions + 1
    assert minimum_successor_calls(pending, "run_probe") == before.minimum


@pytest.mark.parametrize("slots,available", [(4, False), (5, True)])
def test_protocol_output_reserve_stays_separate_from_helper_correction(slots, available):
    gateway = Gateway(initial=True)
    snap = snapshot(gateway, status="unverified", pending_count=0)
    snap.completion_verification["helper_correction"] = {
        "status": "pending", "blocked": True, "question": QUESTION,
    }
    # Fund the ordinary 40K repair route; protocol correction remains 25K below.
    ledger = funding(4, output=40_000)
    cap = ledger.cap_nanos
    selected = runner._tool_policy(
        gateway, counters(model=slots, tools=5), DevLimits(), snapshot=snap,
        cost_ledger=ledger, completion_cost_policy=COMPLETION_RECOVERY_POLICY,
        desired_output_ceiling=40_000, max_correction_output_tokens=25_000,
    )
    assert ("run_probe" in selected.allowed_tools) is available
    assert selected.minimum_completion_calls == 4
    assert selected.completion_cost["correction_model_calls_reserved"] == 1
    assert ledger.cap_nanos == cap


def test_ticket_never_activates_after_first_accepted_mutation(gateway_factory):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = FakeProbe(status="passed")
    gateway.execute(helper())
    events = gateway.journal.events()
    mutation = {"event_type": "action_finished", "payload": {"result": {
        "action_id": "edit", "tool": "replace_text", "status": "succeeded",
    }}}
    assert helper_recovery.review([mutation, *events], gateway.current_diff_hash)[
        "status"] == "not_needed"
    gateway.execute(helper("corrected", GOOD))
    assert helper_recovery.review(gateway.journal.events(), "a-later-diff")[
        "status"] == "execution_returned"


@pytest.mark.parametrize("outcome", ["bad_correction", "no_response"])
def test_runner_returns_incomplete_before_any_further_exploration(tmp_path, monkeypatch, outcome):
    backend = FakeProbe(status="passed")
    calls = []

    class Corrector(MockDevAdapter):
        def next_turn(self, context, tools):
            calls.append(json.loads(context))
            if len(calls) == 1:
                return DevModelTurn(tool_calls=[helper()])
            assert len(calls) == 2
            assert calls[-1]["workflow_gate"] == "needs_helper_correction"
            assert {t["name"] for t in tools} == {"run_probe", "stop_task"}
            if outcome == "no_response":
                return DevModelTurn(error_code="incomplete_response",
                                    incomplete_reason="max_output_tokens")
            return DevModelTurn(tool_calls=[helper("still-bad", BAD + "\n# changed comment")])

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", Corrector)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
        "limits": DevLimits(max_protocol_recoveries=0),
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "VERIFICATION_INCOMPLETE", result
    assert result["call_counts"]["model"] == len(calls) == 2
    assert result["accepted_mutations"] == 0 and result["evaluator"] is None
    assert backend.calls == 0
    final = DevJournal(tmp_path, result["run_id"]).events()[-1]["payload"]
    assert final["completion_horizon"]["helper_correction"]["blocked"]
    if outcome == "no_response":
        assert final["completion_horizon"]["stop_cause"] == "INCOMPLETE_RESPONSE"


def test_corrected_helper_releases_first_repair_and_reaches_isolated_mock_evaluation(
    tmp_path, monkeypatch,
):
    backend = ExecutingProbe()
    seen = []

    class CorrectThenRepair(MockDevAdapter):
        def next_turn(self, context, tools):
            current = json.loads(context)
            seen.append(current)
            if len(seen) == 1:
                return DevModelTurn(tool_calls=[helper()])
            if len(seen) == 2:
                assert current["workflow_gate"] == "needs_helper_correction"
                return DevModelTurn(tool_calls=[helper("corrected", GOOD)])
            correction = current["reproduction_review"]["completion"]["helper_correction"]
            assert correction["status"] == "execution_returned"
            assert correction["behavior_verdict"] == "not_assessed"
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", CorrectThenRepair)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_mutations"] == 1 and backend.calls == 1
    events = DevJournal(tmp_path, result["run_id"]).events()
    finished = [e["payload"]["result"] for e in events if e["event_type"] == "action_finished"]
    assert [r["tool"] for r in finished[:2]] == ["run_probe", "run_probe"]
    finish = next(r for r in finished if r["tool"] == "finish_task")
    assert finish["output"]["reproduction_review"]["completion"][
        "baseline_failure_case_ids"] == []  # Helper success cannot acquire the original.
