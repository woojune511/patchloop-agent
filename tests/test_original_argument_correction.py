"""Short local controls for original-call binding correction, never repair efficacy."""

from __future__ import annotations

import copy
import json

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_dev_planning import request as mock_request
from test_dev_probe_cases import ExecutingProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_finish_reproduction_budget import snapshot
from test_original_obligation import restore

from patchloop.dev import helper_recovery, runner
from patchloop.dev.contracts import DevLimits, DevModelTurn, RequestedTool
from patchloop.dev.cost import COMPLETION_MINIMUM_POLICY, COMPLETION_RECOVERY_POLICY
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ActionConflict

QUESTION = "Does the zero-argument public callable return its current directory?"
BAD = "target = observed_target()\ntarget(['unexpected'])\n"
GOOD = (
    "target = observed_target()\nassert target.signature() == '()'\n"
    "call = target()\nrecord_observation(not bool(call.value))\n"
)
PURPOSE = {
    "kind": "original_requirement", "entrypoint": "os.getcwd",
    "input_conditions": "Use the unchanged workspace cwd with no Python arguments.",
    "environment_conditions": "The ordinary local fixture interpreter.",
    "expected_json": "true", "reported_failure_json": "false",
    "diagnostic_rules": None, "corrects_action_id": None,
}


class FixtureProbe(ExecutingProbe):
    def run_probe(self, *args, **kwargs):
        return {**super().run_probe(*args, **kwargs), "truncated": False}


def original(action="bad", source=BAD, *, entrypoint="os.getcwd"):
    return RequestedTool(name="run_probe", action_id=action, arguments={
        "question": QUESTION, "python_source": source, "replay_action_id": None,
        "call_path": None, "purpose": {**PURPOSE, "entrypoint": entrypoint},
    }, turn_decision={"mode": "verify", "basis": "Observe a trusted local fixture."})


def verification(gateway):
    return gateway.completion_verification(diff_hash=gateway.current_diff_hash)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *a, **k: pytest.fail("offline only"))


@pytest.mark.parametrize("corrected", [True, False])
def test_normal_runner_delivers_original_binding_feedback_and_bounds_next_turn(
    tmp_path, monkeypatch, corrected,
):
    backend, seen = FixtureProbe(), []

    class Corrector(MockDevAdapter):
        def next_turn(self, context, tools):
            current = json.loads(context)
            seen.append(current)
            if len(seen) == 1:
                return DevModelTurn(tool_calls=[original()])
            if len(seen) == 2:
                assert current["workflow_gate"] == "needs_original_argument_correction"
                assert {tool["name"] for tool in tools} == {"run_probe", "stop_task"}
                schema = next(t for t in tools if t["name"] == "run_probe")["parameters"]
                assert schema["properties"]["purpose"]["properties"]["kind"]["enum"] == [
                    "original_requirement"
                ]
                assert schema["properties"]["replay_action_id"] == {"type": "null"}
                ticket = current["action_horizon"]["helper_correction"]
                assert ticket["policy"] == helper_recovery.ARGUMENT_POLICY
                assert ticket["python_source"] == BAD and ticket["purpose"] == PURPOSE
                assert ticket["error"]["calls"][0]["signature"] == "()"
                assert ticket["error"]["calls"][0]["arguments"]["args"] == [["unexpected"]]
                review = current["reproduction_review"]["completion"]
                assert review["original_obligation"]["status"] == "unverified"
                assert review["baseline_failure_case_ids"] == []
                source = GOOD if corrected else BAD + "# still wrong\n"
                return DevModelTurn(tool_calls=[original("corrected", source)])
            assert corrected and len(seen) == 3
            review = current["reproduction_review"]["completion"]
            assert review["helper_correction"]["status"] == "execution_returned"
            assert review["helper_correction"]["behavior_verdict"] == "not_assessed"
            assert len(review["baseline_failure_case_ids"]) == 1
            assert review["case_count"] == review["replayable_case_count"] == 1
            assert review["request_attempt_count"] == 1
            assert review["request_attempts"][0]["root_action_id"] == "bad"
            assert review["original_obligation"]["stage"] == "acquired"
            assert review["original_obligation"]["status"] != "verified"
            return DevModelTurn(tool_calls=[RequestedTool(
                name="stop_task", action_id="stop", arguments={
                    "reason_code": "insufficient_public_evidence",
                    "summary": "Local mechanism observation complete; no repair attempted.",
                }, turn_decision={"mode": "stop", "basis": "End the local control."},
            )])

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", Corrector)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
        "reproduction_acquisition": "bounded-v1",
        "limits": DevLimits(max_protocol_recoveries=0),
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == ("AGENT_STOPPED" if corrected else "VERIFICATION_INCOMPLETE")
    assert result["call_counts"]["model"] == len(seen) == (3 if corrected else 2)
    assert result["accepted_mutations"] == 0 and result["evaluator"] is None
    assert backend.calls == 2
    events = DevJournal(tmp_path, result["run_id"]).events()
    starts = [e["payload"] for e in events if e["event_type"] == "action_started"]
    assert starts[1]["helper_recovery_link"]["root_action_id"] == "bad"
    assert starts[1]["probe_request"]["kind"] == "original_requirement"


def test_corrected_original_durable_return_is_not_executed_twice(gateway_factory, monkeypatch):
    base, _, _ = gateway_factory()
    backend = FixtureProbe()
    gateway = restore(base, backend=backend)
    failed = gateway.execute(original())
    assert failed.output["reproduction"]["call_observation"]["calls"][0]["binding_error"]
    assert verification(gateway)["helper_correction"]["status"] == "pending"
    call = original("fixed", GOOD)
    _crash_journal_once(monkeypatch, event_type="probe_execution_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(call)
    assert backend.calls == 2
    gateway = restore(gateway, backend=backend)
    result = gateway.execute(call)
    assert backend.calls == 2
    assert result.output["reproduction"]["declared_failure_comparison"] == "matched"
    assert verification(gateway)["helper_correction"]["status"] == "execution_returned"
    before = gateway.journal.path.read_bytes()
    assert gateway.execute(call).replayed and gateway.journal.path.read_bytes() == before
    changed = copy.deepcopy(call)
    changed.arguments["python_source"] += "# changed\n"
    with pytest.raises(ActionConflict):
        gateway.execute(changed)


@pytest.mark.parametrize("source,entrypoint", [
    ("target = observed_target()\ntarget()\ntarget(['wrong'])\n", "os.getcwd"),
    ("observed_target()([])\n", "operator.index"),
])
def test_any_target_entry_prevents_original_argument_ticket(gateway_factory, source, entrypoint):
    base, _, _ = gateway_factory()
    gateway = restore(base, backend=FixtureProbe())
    result = gateway.execute(original(source=source, entrypoint=entrypoint))
    calls = result.output["reproduction"]["call_observation"]["calls"]
    assert any(call["target_started"] for call in calls)
    assert verification(gateway)["helper_correction"]["status"] == "not_needed"


def test_exhausted_original_slots_cannot_offer_or_dispatch_correction(gateway_factory):
    base, _, _ = gateway_factory()
    backend = FixtureProbe()
    gateway = restore(base, backend=backend)
    gateway.execute(original("entered-error", "observed_target()([])\n",
                             entrypoint="operator.index"))
    gateway.execute(original())
    view = verification(gateway)
    assert view["original_obligation"]["original_attempts_reserved"] == 2
    assert view["helper_correction"]["status"] == "pending"
    policy = runner._tool_policy(
        gateway, counters(), DevLimits(), snapshot=gateway.state_snapshot(),
        _preview_inspection=False,
    )
    assert policy.allowed_tools == {"stop_task"}
    assert policy.workflow_gate == "verification_incomplete"
    result = gateway.execute(original("unfunded-third", GOOD))
    assert result.status == "failed" and backend.calls == 2
    assert verification(gateway)["helper_correction"]["status"] == "verification_incomplete"


def pending_original_snapshot():
    gateway = Gateway(initial=True)
    snap = snapshot(gateway, status="unverified", case_count=0, pending_count=0)
    snap.completion_verification.update({
        "helper_correction": {"policy": helper_recovery.ARGUMENT_POLICY,
                              "status": "pending", "blocked": True, "question": QUESTION,
                              "purpose": PURPOSE, "call_path": None},
        "original_obligation": {
            "stage": "pending", "reason": "awaiting_original",
            "original_attempts_reserved": 1, "max_original_attempts": 2,
            "request_errors": 0, "max_request_errors": 2,
            "pending_original_requests": 0, "pending_original_dispatches": 0,
            "pending_original_results": 0, "uncertain_original_dispatches": 0,
            "preparation_actions_remaining": 0, "max_investigation_actions": 10,
            "investigation_actions": 7,
        },
    })
    return gateway, snap


@pytest.mark.parametrize("short", [None, "model", "tool", "money"])
def test_pending_original_reserves_correction_and_one_future_replay_once(short):
    gateway, snap = pending_original_snapshot()
    limits = DevLimits()
    original_limits = limits.model_dump()
    ledger = ledger_for_slots(3 if short == "money" else 4)
    cap = ledger.cap_nanos
    selected = runner._tool_policy(
        gateway, counters(model=3 if short == "model" else 4,
                          tools=4 if short == "tool" else 5), limits, snapshot=snap,
        cost_ledger=ledger, completion_cost_policy=COMPLETION_MINIMUM_POLICY,
        _preview_inspection=False,
    )
    assert selected.minimum_completion_calls == 4
    assert selected.minimum_completion_tool_actions == 5
    assert limits.model_dump() == original_limits and ledger.cap_nanos == cap
    assert ledger.spent_nanos == 0
    if short:
        assert selected.allowed_tools == {"stop_task"}
        assert selected.workflow_gate == "verification_incomplete"
    else:
        assert selected.allowed_tools == {"run_probe", "stop_task"}
        assert selected.workflow_gate == "needs_original_argument_correction"
        assert selected.completion_cost["future_calls_reserved"] == 3


def test_recovery_keeps_role_outputs_and_only_two_original_probe_windows():
    gateway, snap = pending_original_snapshot()
    gateway.public_task.visible_checks[0].timeout_seconds = 17
    limits, counts = DevLimits(), counters(model=5, tools=5)
    initial_limits = limits.model_dump()
    ledger = ledger_for_slots(1)
    # Current original correction, future repair/check/finish, and one independent
    # malformed-response correction. No speculative second repair is affordable.
    ledger.cap_nanos = sum(ledger.future_call_reservation_nanos(output_ceiling=n)
                           for n in (40_000, 40_000, 8_192, 8_192, 25_000))
    cap = ledger.cap_nanos

    def policy():
        return runner._tool_policy(
            gateway, counts, limits, snapshot=snap, cost_ledger=ledger,
            completion_cost_policy=COMPLETION_RECOVERY_POLICY,
            desired_output_ceiling=40_000, max_correction_output_tokens=25_000,
            remaining_seconds=212, _preview_inspection=False,
        )

    selected = policy()
    costs = selected.completion_cost
    assert selected.allowed_tools == {"run_probe", "stop_task"}
    assert selected.minimum_completion_calls == 4  # This correction + 3 successors.
    assert selected.minimum_completion_tool_actions == 5  # Includes future original replay.
    assert costs["future_calls_reserved"] == 3
    assert costs["successor_output_ceilings"]["run_probe"] == [40_000, 8_192, 8_192]
    assert not costs["failure_recovery_reserved"]["run_probe"]
    assert costs["correction_output_ceiling"] == 25_000
    assert costs["correction_model_calls_reserved"] == 1
    # Current original attempt and one post-repair replay, one public check,
    # and three follow-up model windows. No second acquisition case/window.
    assert costs["future_time_reserve_seconds"] == 2 * (30 + 5) + (17 + 5) + 3 * 30
    admitted = ledger.admit(60_000, desired_output_ceiling=40_000,
                           minimum_output_ceiling=costs["current_minimum_output_ceiling"],
                           future_cost_reserve_nanos=costs["future_cost_reserve_nanos"])
    assert admitted is not None and admitted.output_ceiling == 40_000
    ledger.settle(input_tokens=60_000, cached_input_tokens=0, output_tokens=40_000)
    counts.model_calls += 1
    counts.protocol_recoveries = counts.protocol_corrections_total = 1
    corrected = policy()
    assert corrected.allowed_tools == {"run_probe", "stop_task"}
    costs = corrected.completion_cost
    assert costs["correction_pending"] and costs["future_calls_reserved"] == 3
    admitted = ledger.admit(60_000, desired_output_ceiling=25_000,
                           minimum_output_ceiling=costs["current_minimum_output_ceiling"],
                           future_cost_reserve_nanos=costs["future_cost_reserve_nanos"])
    assert admitted is not None and admitted.output_ceiling == 25_000
    assert ledger.cap_nanos == cap and limits.model_dump() == initial_limits
