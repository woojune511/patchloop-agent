"""Bounded diagnosis after comparable original failure; offline mechanics only."""

from dataclasses import replace

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_dev_probe_action_replay import restore
from test_dev_tools import read_calls
from test_finish_reproduction import mutate, prepare
from test_finish_reproduction_budget import snapshot
from test_probe_purpose import probe

from patchloop.dev import completion_reproduction, runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import COMPLETION_MINIMUM_POLICY
from patchloop.dev.model_state import compact_model_state


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("bounded diagnosis controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def failed_snapshot(gateway, *, status="available"):
    state = snapshot(gateway, status="refuted", pending_count=0)
    state.completion_verification.update({
        "early_replay_reusable": True, "baseline_failure_case_ids": ["original"],
        "original_failure_diagnostic": {
            "candidate_diff_hash": "candidate", "failure_action_id": "failed-original",
            "status": status, "spent_action_id": "diagnostic" if status == "spent" else None,
        },
    })
    return state


@pytest.mark.parametrize("tool_slots,probe_allowed", [(5, False), (6, True)])
def test_one_diagnostic_fits_minimum_repair_replay_checks_and_finish(tool_slots, probe_allowed):
    gateway = Gateway(initial=False)
    selected = runner._tool_policy(
        gateway, counters(model=4, tools=tool_slots), DevLimits(),
        snapshot=failed_snapshot(gateway), repair_recheck=True,
    )
    assert selected.minimum_completion_calls == 3
    assert selected.minimum_completion_tool_actions == 4
    assert not selected.protected_completion_possible
    assert {"read_file", "search_files", "replace_text"} <= selected.allowed_tools
    # A diagnostic probe may introduce another case, whose next-diff replay also needs a slot.
    assert ("run_probe" in selected.allowed_tools) == probe_allowed
    assert not {"run_tests", "run_check", "finish_task"} & selected.allowed_tools
    assert selected.max_parallel_reads == selected.model_turns_available_for_exploration == 1
    assert selected.exploration_state == "last_opportunity"
    assert {"read_file", "search_files"} <= set(selected.tools_closing_after_this_turn)
    assert selected.original_failure_diagnostic["uses_minimum_completion_reserve"]
    public = compact_model_state({
        "action_horizon": runner._repair_inspection_payload(selected),
    }, [])
    assert public["action_horizon"]["original_failure_diagnostic"] == (
        selected.original_failure_diagnostic)


@pytest.mark.parametrize("blocked", ["spent", "model", "tool", "money", "candidate"])
def test_diagnostic_credit_does_not_bypass_identity_or_completion_resources(blocked):
    gateway = Gateway(initial=False)
    state = failed_snapshot(gateway, status="spent" if blocked == "spent" else "available")
    if blocked == "candidate":
        state.completion_verification["original_failure_diagnostic"]["candidate_diff_hash"] = "old"
    selected = runner._tool_policy(
        gateway, counters(model=3 if blocked == "model" else 4,
                          tools=4 if blocked == "tool" else 6), DevLimits(), snapshot=state,
        cost_ledger=ledger_for_slots(3) if blocked == "money" else None,
        completion_cost_policy=COMPLETION_MINIMUM_POLICY,
    )
    assert selected.completion_possible
    assert not {"read_file", "search_files", "run_probe", "finish_task"} & selected.allowed_tools


@pytest.mark.parametrize("action", ["read", "rejected_probe"])
def test_failure_credit_survives_restart_and_only_new_candidate_renews_it(gateway_factory, action):
    gateway, journal, workspace, backend, _ = prepare(gateway_factory, correct=False)
    before = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert not before["early_replay_reusable"] and before["original_failure_diagnostic"] is None

    def replay():
        runner._replay_original_cases(
            journal=journal, gateway=gateway, counters=runner._restore_counters(journal),
            active_elapsed_ms=lambda: 20, acquired_only=True,
        )
        return gateway.completion_verification(diff_hash=gateway.current_diff_hash)

    observed = replay()
    assert observed["early_replay_reusable"] and observed["status"] == "refuted"
    credit = observed["original_failure_diagnostic"]
    assert credit["status"] == "available" and backend.calls == 2
    call = read_calls()[1].model_copy(update={"action_id": "diagnostic-read"})
    if action == "rejected_probe":
        call = probe(gateway.public_task, "diagnostic-rejected", replay="missing-action")
    journal.append("tool_batch_started", {
        "turn_id": "diagnostic-turn", "tool_calls": [call.model_dump(mode="json")],
        "active_elapsed_ms": 21,
    })
    expected_status = "spent" if action == "rejected_probe" else "available"
    assert gateway.completion_verification(diff_hash=gateway.current_diff_hash)[
        "original_failure_diagnostic"]["status"] == expected_status
    result = gateway.execute(call)
    assert result.status == ("failed" if action == "rejected_probe" else "succeeded")
    # Preparation and probe starts persist independently even without a result.
    events = journal.events()
    start = next(e["sequence"] for e in events if e["event_type"] == "action_started"
                 and e["payload"]["action_id"] == call.action_id)
    partial = completion_reproduction.review(
        [e for e in events if e["sequence"] <= start], gateway.current_diff_hash,
        public_task=gateway.public_task, run_id=journal.run_id,
    )
    assert partial["original_failure_diagnostic"]["status"] == expected_status
    assert gateway.execute(call).replayed
    gateway = restore(gateway, journal, workspace, gateway.public_task, backend)
    repeated = replay()
    assert backend.calls == 2
    assert repeated["original_failure_diagnostic"] == {
        **credit, "status": expected_status,
        "spent_action_id": call.action_id if action == "rejected_probe" else None,
        "preparation_available": action != "read",
        "preparation_action_id": call.action_id if action == "read" else None,
    }
    # A newly requested replay on the same diff must not reset the first failure boundary.
    gateway.execute(probe(gateway.public_task, "repeat-original", replay="original"))
    assert replay()["original_failure_diagnostic"]["status"] == expected_status
    old_diff = gateway.current_diff_hash
    mutate(gateway, correct=False, action="candidate-2")
    assert gateway.current_diff_hash != old_diff
    after = replay()
    assert after["original_failure_diagnostic"]["status"] == "available"
    assert after["original_failure_diagnostic"]["candidate_diff_hash"] == gateway.current_diff_hash


def test_unhealthy_or_changed_current_evidence_cannot_claim_reuse_or_diagnosis(gateway_factory):
    gateway, journal, _, _, _ = prepare(gateway_factory, correct=False)
    runner._replay_original_cases(
        journal=journal, gateway=gateway, counters=runner._restore_counters(journal),
        active_elapsed_ms=lambda: 20, acquired_only=True,
    )
    # Project a failed/unknown observation without changing the stored receipt.
    events = journal.events()
    last = next(e for e in reversed(events) if e["event_type"] == "action_finished"
                and e["payload"]["result"]["tool"] == "run_probe")
    last["payload"]["result"]["output"]["timed_out"] = True
    unknown = completion_reproduction.review(
        events, gateway.current_diff_hash, public_task=gateway.public_task, run_id=journal.run_id,
    )
    assert not unknown["early_replay_reusable"]
    assert unknown["original_failure_diagnostic"] is None


def test_early_receipt_eligibility_changes_forecast_but_pending_retains_fallback():
    gateway = Gateway(initial=False)
    state = failed_snapshot(gateway)
    before = runner._tool_policy(gateway, counters(model=20), DevLimits(), snapshot=state)
    deferred = replace(state, completion_verification={**state.completion_verification,
                                                       "early_replay_reusable": False})
    after = runner._tool_policy(gateway, counters(model=20), DevLimits(), snapshot=deferred)
    assert before.completion_budget_calls == after.completion_budget_calls - 1
    assert before.completion_budget_tool_actions == after.completion_budget_tool_actions - 1


def test_cached_model_replay_spends_diagnosis_but_host_replay_does_not():
    events = [{"sequence": 1, "event_type": "action_finished", "payload": {"result": {
        "action_id": "original-replay", "workspace_diff_hash": "candidate",
    }}}]
    assert completion_reproduction._failure_diagnostic(
        events, "candidate", {"original-replay"})["status"] == "available"
    events.append({"sequence": 2, "event_type": "tool_batch_started", "payload": {
        "tool_calls": [{"name": "run_probe", "action_id": "original-replay"}],
    }})
    # Reusing a completed action creates no action_started/result, but costs a model turn.
    spent = completion_reproduction._failure_diagnostic(events, "candidate", {"original-replay"})
    assert spent["status"] == "spent" and spent["spent_action_id"] == "original-replay"
