"""Independent resource-boundary checks for original-case completion replay."""

from __future__ import annotations

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters

from patchloop.dev import runner
from patchloop.dev.completion_budget import CompletionState, completion_budget
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import COMPLETION_RESERVE_POLICY
from patchloop.dev.tools import DevGatewayStateSnapshot


def test_protected_tools_include_original_replays_on_every_repaired_diff():
    state = CompletionState(
        check_count=2, remaining_check_count=2, unused_check_count=2,
        unrun_recoverable_check=True, requires_mutation=True, anchor_available=True,
        remaining_mutations=3, mutation_retry_available=False,
        reproduction_case_count=3, pending_reproduction_count=3, early_reproduction_count=3,
    )
    budget = completion_budget(state)
    # edit + 3 replays + 2 checks, twice(read + edit + 3 replays + 2 checks), finish.
    assert budget.protected_tool_actions >= 6 + 2 * 7 + 1
    assert budget.minimum == 4  # Host replay never consumes a model call.


def snapshot(gateway, *, status="pending", case_count=1, pending_count=1):
    return DevGatewayStateSnapshot(
        diff=gateway.current_diff,
        mutation_evidence_paths=("src.py",) if gateway.anchor else (),
        evidence_paths=("src.py",),
        visible_check_status=tuple(gateway.visible_check_status()),
        remaining_visible_check_ids=tuple(gateway.remaining_visible_check_ids()),
        unrun_visible_check_ids=tuple(gateway.unrun_visible_check_ids()),
        ready_to_submit=gateway.ready_to_submit(),
        completion_verification={
            "status": status, "case_count": case_count,
            "replayable_case_count": case_count, "pending_count": pending_count,
        },
    )


def policy(gateway, state, *, model=8, tools=8):
    # Gateway's consumed-edit fixture is expressed against a four-edit budget.
    return runner._tool_policy(
        gateway, counters(model=model, tools=tools), DevLimits(max_accepted_mutations=4),
        snapshot=state,
        repair_recheck=False, _preview_inspection=False,
    )


def test_successful_finish_replay_costs_one_model_call_and_all_original_case_actions():
    gateway = Gateway(("PASS",), initial=False)
    state = snapshot(gateway, case_count=4, pending_count=4)
    fits = policy(gateway, state, model=1, tools=5)
    assert fits.minimum_completion_calls == 1
    assert fits.minimum_completion_tool_actions == 5
    assert fits.allowed_tools == {"finish_task", "stop_task"}
    short = policy(gateway, state, model=1, tools=4)
    assert not short.completion_possible
    assert "finish_task" not in short.allowed_tools


def test_current_verified_cases_need_no_replay_until_a_new_edit():
    gateway = Gateway(("PASS",), initial=False)
    state = snapshot(gateway, status="cases_verified", case_count=4, pending_count=0)
    result = policy(gateway, state, model=1, tools=1)
    assert result.minimum_completion_calls == result.minimum_completion_tool_actions == 1
    assert "finish_task" in result.allowed_tools
    # An optional candidate invalidates every original result, including controls.
    assert result.optional_mutation_completion_tool_actions == 7  # edit, check, 4 replays, finish
    assert "replace_text" not in result.allowed_tools


def test_protected_check_failure_path_includes_replays_invalidated_by_its_repair():
    state = CompletionState(
        check_count=1, remaining_check_count=1, unused_check_count=1,
        unrun_recoverable_check=True, requires_mutation=False, anchor_available=True,
        remaining_mutations=1, mutation_retry_available=False,
        reproduction_case_count=1, pending_reproduction_count=0,
    )
    budget = completion_budget(state)
    # Public case is already current, so the minimum successful check/finish path
    # needs no replay. A protected failed check changes that:
    # check FAIL -> inspect -> repair -> check PASS -> original replay -> finish.
    actions = ["failed_check", "inspect", "repair", "check", "original_replay", "finish"]
    assert budget.minimum_tool_actions == 2
    assert budget.protected_tool_actions >= len(actions)
    assert budget.protected >= len(actions) - 1  # The replay has no provider call.


def test_last_finish_can_fit_without_claiming_replay_failure_recovery_is_protected():
    gateway = Gateway(("PASS",), initial=False, mutations=1)
    state = snapshot(gateway)
    result = policy(gateway, state, model=1, tools=2)
    assert result.completion_possible
    assert "finish_task" in result.allowed_tools
    # Success fits, but a mismatching replay consumes the last call and both tool
    # slots. Calling this protected would incorrectly promise a recovery path.
    assert not result.protected_completion_possible


def test_current_original_refutation_exposes_repair_and_truthful_completion_state():
    gateway = Gateway(("PASS",), initial=False)
    state = snapshot(gateway, status="refuted", pending_count=0)
    result = policy(gateway, state, model=20, tools=20)
    assert "finish_task" not in result.allowed_tools
    assert "replace_text" in result.allowed_tools
    assert result.minimum_completion_calls == 3  # edit, required check, finish request
    assert result.minimum_completion_tool_actions == 4  # plus the original replay
    guidance = runner._completion_guidance(state, result)
    assert guidance["stage"] == "needs_mutation"
    assert guidance["next_action"] == {"tool": "replace_text"}
    assert guidance["submission_ready"] is False
    assert result.workflow_gate == "needs_mutation"


@pytest.mark.parametrize("requires_mutation,remaining_edits", [(False, 0), (True, 1)])
def test_replay_recovery_does_not_reserve_an_unavailable_accepted_edit(
    requires_mutation, remaining_edits,
):
    state = CompletionState(
        check_count=1, remaining_check_count=int(requires_mutation), unused_check_count=1,
        unrun_recoverable_check=requires_mutation, requires_mutation=requires_mutation,
        anchor_available=True, remaining_mutations=remaining_edits, mutation_retry_available=False,
        reproduction_case_count=2, pending_reproduction_count=2,
    )
    result = completion_budget(state)
    assert result.protected == result.minimum
    assert result.protected_tool_actions == result.minimum_tool_actions


def test_current_verified_cases_without_a_future_edit_have_no_speculative_replay_path():
    state = CompletionState(
        check_count=1, remaining_check_count=0, unused_check_count=1,
        unrun_recoverable_check=False, requires_mutation=False,
        anchor_available=True, remaining_mutations=4, mutation_retry_available=True,
        reproduction_case_count=2, pending_reproduction_count=0,
    )
    result = completion_budget(state)
    assert result.minimum == result.protected == 1
    assert result.minimum_tool_actions == result.protected_tool_actions == 1


def test_one_remaining_edit_protects_the_larger_failure_path_without_combining_two_edits():
    state = CompletionState(
        check_count=1, remaining_check_count=1, unused_check_count=1,
        unrun_recoverable_check=True, requires_mutation=False,
        anchor_available=True, remaining_mutations=1, mutation_retry_available=False,
        reproduction_case_count=1, pending_reproduction_count=1,
    )
    result = completion_budget(state)
    # The original-case failure path is longest: initial check, finish request,
    # original replay FAIL, inspect, edit, check, finish request, original replay.
    # A registered-check failure cannot consume a second accepted edit as well.
    assert result.protected == 6
    assert result.protected_tool_actions == 8


def test_replay_failure_recovery_preserves_the_first_mutation_rejection_allowance():
    state = CompletionState(
        check_count=1, remaining_check_count=0, unused_check_count=1,
        unrun_recoverable_check=False, requires_mutation=False,
        anchor_available=True, remaining_mutations=1, mutation_retry_available=True,
        reproduction_case_count=1, pending_reproduction_count=1,
    )
    budget = completion_budget(state)
    # finish/replay FAIL -> inspect -> rejected edit -> inspect -> accepted edit
    # -> registered check -> final finish/replay. Rejection consumes no accepted edit.
    assert budget.protected >= 7
    assert budget.protected_tool_actions >= 9
    gateway = Gateway(("PASS",), initial=False, mutations=1)
    failed = snapshot(gateway, status="refuted", pending_count=0)
    successor = policy(gateway, failed, model=budget.protected - 1,
                       tools=budget.protected_tool_actions - 2)
    assert "read_file" in successor.allowed_tools


def test_finish_dispatch_cannot_spend_its_advertised_replay_failure_recovery_funds():
    gateway = Gateway(("PASS",), initial=False, mutations=1)
    ledger = ledger_for_slots(7)
    selected = runner._tool_policy(
        gateway, counters(model=7, tools=9), DevLimits(max_accepted_mutations=4),
        snapshot=snapshot(gateway),
        cost_ledger=ledger, completion_cost_policy=COMPLETION_RESERVE_POLICY,
    )
    assert selected.protected_completion_possible
    assert selected.allowed_tools == {"finish_task", "replace_text", "edit_files", "stop_task"}
    reserve = selected.completion_cost["future_cost_reserve_nanos"]
    assert reserve >= 6 * ledger.future_call_reservation_nanos()
    admission = ledger.admit(60_000, future_cost_reserve_nanos=reserve)
    assert admission is not None
    ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                  output_tokens=admission.output_ceiling)
    failed = runner._tool_policy(
        gateway, counters(model=6, tools=7), DevLimits(max_accepted_mutations=4),
        snapshot=snapshot(gateway, status="refuted", pending_count=0),
        cost_ledger=ledger, completion_cost_policy=COMPLETION_RESERVE_POLICY,
    )
    assert "read_file" in failed.allowed_tools
