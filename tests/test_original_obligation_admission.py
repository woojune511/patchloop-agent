"""Acquisition must fund its new case and survive ordinary invalid tool arguments."""

from __future__ import annotations

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_dev_probe_cases import ExecutingProbe
from test_dev_tools import read_calls
from test_finish_reproduction_budget import snapshot
from test_original_obligation import restore
from test_probe_purpose import probe

from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import COMPLETION_RESERVE_POLICY
from patchloop.dev.tools import validate_tool_batch
from patchloop.errors import ContractError

# One new original case, one registered check, three accepted edits within the
# four-edit limit. A rejected edit is retried, a failed check is repaired, then a
# failing finish replay is repaired. Only the two host replays need no model call.
RECOVERY_PATH = (
    "edit_rejected", "read_retry", "edit", "check_failed", "read_check", "repair_check",
    "check_pass", "finish", "replay_failed", "read_original", "repair_original",
    "check_pass", "finish", "replay_pass",
)
SUCCESSOR_MODELS = sum(not step.startswith("replay_") for step in RECOVERY_PATH)
SUCCESSOR_TOOLS = len(RECOVERY_PATH)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("original-obligation admission tests must not use the network")

    monkeypatch.setattr("socket.socket.connect", forbidden)


def pending_snapshot(gateway, *, controls=0, actions=0):
    state = snapshot(gateway, status="cases_verified" if controls else "unverified",
                     case_count=controls, pending_count=0)
    state.completion_verification["original_obligation"] = {
        "stage": "pending", "status": "unverified", "acquisition_policy": "bounded-v1",
        "original_attempts": controls, "max_original_attempts": 2,
        "investigation_actions": actions, "max_investigation_actions": 6,
        "preparation_actions_remaining": max(0, 6 - actions),
        "baseline_failure_case_ids": [],
    }
    return state


def policy(gateway, state, *, model=40, tools=100, ledger=None):
    options = ({"cost_ledger": ledger, "completion_cost_policy": COMPLETION_RESERVE_POLICY}
               if ledger is not None else {})
    return runner._tool_policy(
        gateway, counters(model=model, tools=tools), DevLimits(), snapshot=state,
        repair_recheck=False, _preview_inspection=False, **options,
    )


@pytest.mark.parametrize("controls", [0, 1])
@pytest.mark.parametrize("short_resource", ["model", "tool", None])
def test_original_probe_reserves_new_case_successor_resources(controls, short_resource):
    gateway = Gateway()
    # A previously passing control must also replay at both finishes after edits.
    model = SUCCESSOR_MODELS + 1 - int(short_resource == "model")
    tools = SUCCESSOR_TOOLS + 2 * controls + 1 - int(short_resource == "tool")
    selected = policy(gateway, pending_snapshot(gateway, controls=controls),
                      model=model, tools=tools)
    assert ("run_probe" in selected.allowed_tools) is (short_resource is None)
    successor = policy(
        gateway, snapshot(gateway, status="refuted", case_count=controls + 1, pending_count=0),
        model=model - 1, tools=tools - 1,
    )
    assert successor.protected_completion_possible is (short_resource is None)


@pytest.mark.parametrize("funded_slots", [SUCCESSOR_MODELS, SUCCESSOR_MODELS + 1])
def test_acquisition_cost_funds_new_case_before_offering_probe(funded_slots):
    gateway = Gateway()
    selected = policy(gateway, pending_snapshot(gateway), ledger=ledger_for_slots(funded_slots))
    assert selected.completion_cost["funded_calls"] == funded_slots
    assert ("run_probe" in selected.allowed_tools) is (funded_slots > SUCCESSOR_MODELS)


def test_probe_dispatch_cannot_spend_acquired_case_recovery_funds():
    gateway = Gateway()
    ledger = ledger_for_slots(SUCCESSOR_MODELS + 1)
    selected = policy(gateway, pending_snapshot(gateway),
                      tools=SUCCESSOR_TOOLS + 1, ledger=ledger)
    assert "run_probe" in selected.allowed_tools
    reserve = selected.completion_cost["future_cost_reserve_nanos"]
    assert reserve >= SUCCESSOR_MODELS * ledger.future_call_reservation_nanos()
    admission = ledger.admit(60_000, future_cost_reserve_nanos=reserve)
    assert admission is not None
    ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                  output_tokens=admission.output_ceiling)
    acquired = policy(
        gateway, snapshot(gateway, status="refuted", case_count=1, pending_count=0),
        model=39, tools=SUCCESSOR_TOOLS, ledger=ledger,
    )
    assert acquired.protected_completion_possible
    assert "replace_text" in acquired.allowed_tools


@pytest.mark.parametrize("purpose", ["original_requirement", [1]])
def test_malformed_purpose_stays_a_recoverable_failure(gateway_factory, purpose):
    gateway, journal, _ = gateway_factory()
    backend = ExecutingProbe()
    gateway = restore(gateway, backend=backend)
    call = probe(gateway.public_task, "malformed-purpose")
    call.arguments["purpose"] = purpose
    result = gateway.execute(call)
    assert result.status == "failed" and result.error_code == "CONTRACT_ERROR"
    assert backend.calls == 0
    before = journal.path.read_bytes()
    state = gateway.state_snapshot().completion_verification["original_obligation"]
    assert state["status"] == "unverified" and state["stage"] == "pending"
    assert state["original_attempts"] == 0 and state["investigation_actions"] == 1
    assert state["request_errors"] == 1 and state["max_request_errors"] == 2
    assert result.output["probe_stage"] == "preflight_rejected"
    assert state["baseline_failure_case_ids"] == []
    restored = restore(gateway)
    assert restored.state_snapshot().completion_verification["original_obligation"] == state
    assert restored.execute(call).replayed
    assert backend.calls == 0 and journal.path.read_bytes() == before


@pytest.mark.parametrize("actions,remaining", [(4, 2), (5, 1)])
def test_pending_phase_blocks_edits_and_bounds_parallel_investigation(actions, remaining):
    gateway = Gateway(anchor=True)
    selected = policy(gateway, pending_snapshot(gateway, actions=actions))
    assert selected.workflow_gate == "needs_original_reproduction"
    assert "replace_text" not in selected.allowed_tools
    assert not selected.mutation_completion_possible
    assert "read_file" in selected.allowed_tools
    assert selected.max_parallel_reads == remaining
    reads = [read_calls()[0].model_copy(update={"action_id": f"read-{index}"})
             for index in range(remaining + 1)]
    assert validate_tool_batch(reads[:-1], max_parallel_reads=selected.max_parallel_reads,
                               allowed_tools=selected.allowed_tools) == "parallel_read"
    with pytest.raises(ContractError, match="at most"):
        validate_tool_batch(reads, max_parallel_reads=selected.max_parallel_reads,
                            allowed_tools=selected.allowed_tools)


def test_six_preparations_leave_only_original_request_and_stop():
    gateway = Gateway()
    selected = policy(gateway, pending_snapshot(gateway, actions=6))
    assert selected.workflow_gate == "needs_original_reproduction"
    assert selected.allowed_tools == {"run_probe", "stop_task"}
    assert selected.max_parallel_reads == 0
    assert selected.exploration_state == "closed"


@pytest.mark.parametrize("resource", ["model", "tool", "cost"])
def test_preparation_cannot_spend_last_original_request_opportunity(resource):
    gateway = Gateway()
    selected = policy(gateway, pending_snapshot(gateway),
                      model=SUCCESSOR_MODELS + 1 if resource == "model" else 40,
                      tools=SUCCESSOR_TOOLS + 1 if resource == "tool" else 100,
                      ledger=ledger_for_slots(SUCCESSOR_MODELS + 1)
                      if resource == "cost" else None)
    assert "run_probe" in selected.allowed_tools
    assert not {"read_file", "search_files", "search_history"} & selected.allowed_tools


def test_read_then_original_probe_fits_reserved_successor():
    gateway = Gateway()
    before = policy(gateway, pending_snapshot(gateway), model=SUCCESSOR_MODELS + 2,
                    tools=SUCCESSOR_TOOLS + 2)
    assert "read_file" in before.allowed_tools and before.max_parallel_reads == 1
    after = policy(gateway, pending_snapshot(gateway, actions=1), model=SUCCESSOR_MODELS + 1,
                   tools=SUCCESSOR_TOOLS + 1)
    assert after.allowed_tools == {"run_probe", "stop_task"}
