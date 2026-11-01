"""Offline resource boundaries for a diagnosed repair's one paired-test revision."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_repair_path_policy import path_state

from patchloop.dev import cost, runner
from patchloop.dev.completion_budget import (
    CompletionState,
    completion_budget,
    minimum_successor_calls,
)
from patchloop.dev.completion_budget import (
    test_addition_budget as addition_budget,
)
from patchloop.dev.contracts import DevLimits, RequestedTool

SELECTION = {"suite_id": "public-tests", "targets": ["tests/test_bug.py::test_original"],
             "comparison": {"baseline": "before_mutation", "mutation_action_id": "source-edit"}}


def source_state(**changes):
    return CompletionState(**{
        "check_count": 1, "remaining_check_count": 1, "unused_check_count": 0,
        "unrun_recoverable_check": False, "requires_mutation": True,
        "anchor_available": True, "remaining_mutations": 3, "mutation_retry_available": False,
        "reproduction_case_count": 1, "early_reproduction_count": 1,
        "early_replay_reusable": True, **changes,
    })


def diagnosed(*, status="available", mutations=3, path="diagnosed", replay_pending=False):
    gateway = Gateway(initial=False, mutations=mutations)
    gateway.public_task.constraints = SimpleNamespace(additive_test_roots=["tests"])
    state = path_state(gateway, status=path, preparation=False)
    state.completion_verification["repair_path"].update(
        mutation_action_id="source-edit", diagnosis_action_id="diagnosis")
    state.completion_verification["repair_prediction"] = {
        "status": status, "test_available": status == "available",
        "pending_test": SELECTION if status == "needs_test_comparison" else None,
    }
    if replay_pending:
        state.completion_verification.update(
            status="pending", pending_count=1, pending_cases=[{"case_id": "original"}])
    return gateway, state


def select(gateway, state, *, model=20, tools=50, money=20, recovery=False):
    ledger = ledger_for_slots(money)
    if recovery:
        # Price the actual roles: test edit and later source repair at the normal
        # ceiling, other continuations at the bounded floor, plus one correction.
        floor = ledger.future_call_reservation_nanos(output_ceiling=8_192)
        ledger.cap_nanos = (money * floor
                            + 2 * (ledger.future_call_reservation_nanos(
                                output_ceiling=40_000) - floor)
                            + ledger.future_call_reservation_nanos(output_ceiling=25_000))
    counts = counters(model=model, tools=tools, mutation_recovery_used=True)
    policy = runner._tool_policy(
        gateway, counts, DevLimits(max_accepted_mutations=4), snapshot=state, cost_ledger=ledger,
        completion_cost_policy=(cost.COMPLETION_RECOVERY_POLICY if recovery
                                else cost.COMPLETION_MINIMUM_POLICY),
        desired_output_ceiling=40_000, max_correction_output_tokens=25_000 if recovery else None,
        _preview_inspection=False,
    )
    return policy, counts, ledger


def test_test_addition_keeps_source_repair_and_charges_both_replays_and_comparison_children():
    source = source_state()
    base = completion_budget(source)
    assert (base.minimum, base.minimum_tool_actions) == (3, 4)
    added = addition_budget(source)
    # test edit, comparison, source repair, required check, finish; each edit also replays.
    assert (added.minimum, added.minimum_tool_actions) == (5, 8)
    pending = replace(source, test_comparison_pending=True, test_comparison_replay_count=1)
    before_replay = completion_budget(pending)
    assert (before_replay.minimum, before_replay.minimum_tool_actions) == (4, 7)
    after_replay = completion_budget(replace(pending, test_comparison_replay_count=0))
    assert (after_replay.minimum, after_replay.minimum_tool_actions) == (4, 6)
    assert minimum_successor_calls(pending, "run_tests") == 3
    assert addition_budget(replace(source, automatic_recheck=True,
                                  current_recheck_eligible=True)).minimum_tool_actions == 9


@pytest.mark.parametrize("short", [None, "model", "tool", "money", "mutation"])
def test_test_edit_offer_keeps_source_slot_and_unchanged_protocol_correction_reserve(short):
    gateway, state = diagnosed(mutations=1 if short == "mutation" else 3)
    policy, counts, ledger = select(
        gateway, state, model=5 if short == "model" else 6,
        tools=7 if short == "tool" else 8, money=4 if short == "money" else 5, recovery=True,
    )
    assert policy.repair_test_edit_enabled is (short is None)
    assert ("replace_text" in policy.allowed_tools) is (short != "money")
    if short == "money":
        assert policy.completion_cost["resource_rejections"]["replace_text"] == "cost"
    assert policy.completion_cost["correction_cost_reserved_nanos"] == 157_500_000
    if short is None:
        assert policy.completion_cost["future_calls_reserved"] >= 4
        admission = ledger.admit(60_000, desired_output_ceiling=40_000,
                                 future_cost_reserve_nanos=policy.completion_cost[
                                     "future_cost_reserve_nanos"])
        assert admission is not None
        assert admission.reserved_cost_nanos + policy.completion_cost[
            "future_cost_reserve_nanos"] <= ledger.remaining_nanos
    test_edit = RequestedTool(name="replace_text", action_id="test-edit", arguments={
        "repair_prediction": {"kind": "test", "suite_id": SELECTION["suite_id"],
                              "targets": SELECTION["targets"]}})
    assert runner._batch_fits_tool_budget(
        [test_edit], counts, DevLimits(max_accepted_mutations=4), policy,
    ) is (short is None)


@pytest.mark.parametrize("short", [None, "model", "tool", "money"])
def test_pending_comparison_is_one_model_two_actions_and_retains_source_completion(short):
    gateway, state = diagnosed(status="needs_test_comparison")
    policy, counts, _ = select(gateway, state, model=3 if short == "model" else 4,
                               tools=5 if short == "tool" else 6,
                               money=3 if short == "money" else 4)
    assert (policy.minimum_completion_calls, policy.minimum_completion_tool_actions) == (4, 6)
    assert not policy.repair_test_edit_enabled
    if short:
        assert policy.allowed_tools == {"stop_task"}
        assert policy.workflow_gate == "verification_incomplete"
    else:
        assert policy.allowed_tools == {"run_tests", "stop_task"}
        assert policy.workflow_gate == "needs_test_comparison"
        assert runner._test_comparison_enabled(policy, counts, DevLimits(max_accepted_mutations=4))
        assert policy.completion_cost["future_calls_reserved"] == 3
        assert runner._completion_guidance(state, policy)["next_action"] == {
            "tool": "run_tests", **SELECTION}
        pair = RequestedTool(name="run_tests", action_id="pair", arguments=SELECTION)
        assert runner._batch_fits_tool_budget(
            [pair], counts, DevLimits(max_accepted_mutations=4), policy,
        )
        single = pair.model_copy(update={"arguments": {**SELECTION, "comparison": None}})
        assert not runner._batch_fits_tool_budget(
            [single], counts, DevLimits(max_accepted_mutations=4), policy,
        )


def test_pending_original_replay_and_path_diagnosis_are_not_removed_from_forecast():
    gateway, state = diagnosed(status="needs_test_comparison", path="needs_path_diagnosis",
                               replay_pending=True)
    policy, _, _ = select(gateway, state, model=5, tools=8, money=5)
    assert (policy.minimum_completion_calls, policy.minimum_completion_tool_actions) == (5, 8)
    assert policy.allowed_tools == {"run_tests", "stop_task"}
    assert runner._completion_guidance(state, policy)["next_action"]["tool"] == "run_tests"


def test_available_pair_can_use_minimum_path_once_but_spent_comparison_does_not_reopen():
    gateway, state = diagnosed()
    policy, counts, _ = select(gateway, state, model=4, tools=6, money=4)
    assert "run_tests" in policy.allowed_tools
    assert not policy.repair_test_edit_enabled
    assert policy.completion_budget_calls > 4
    assert runner._test_comparison_enabled(policy, counts, DevLimits(max_accepted_mutations=4))
    one_short, _, _ = select(gateway, state, model=4, tools=5, money=4)
    assert "run_tests" not in one_short.allowed_tools
    state.completion_verification["repair_prediction"].update(
        status="observed", test_available=False)
    spent, _, _ = select(gateway, state)
    assert "run_tests" not in spent.allowed_tools
    assert "replace_text" in spent.allowed_tools
    assert spent.minimum_completion_calls == 3


def test_pending_test_parser_preserves_missing_annotations_and_exposes_explicit_null():
    raw = SimpleNamespace(name="run_tests", action_id="pair", arguments=dict(SELECTION))
    plain = runner._requested_tool_from_openai(raw, repair_test_comparison_pending=True)
    assert "turn_decision" not in plain.model_fields_set
    raw.arguments["turn_decision"] = None
    annotated = runner._requested_tool_from_openai(raw, repair_test_comparison_pending=True)
    assert "rejected_turn_decision" in annotated.model_fields_set


def test_resolved_source_restores_ordinary_selected_tests():
    gateway, state = diagnosed(status="observed")
    state.completion_verification.update(status="cases_verified")
    state.completion_verification["repair_path"].update(status="not_needed", blocked=False)
    policy, counts, _ = select(gateway, state)
    assert "run_tests" in policy.allowed_tools
    assert not policy.selected_test_comparison_required
    single = RequestedTool(name="run_tests", action_id="regression", arguments={
        **SELECTION, "comparison": None})
    assert runner._batch_fits_tool_budget(
        [single], counts, DevLimits(max_accepted_mutations=4), policy,
    )


def test_pending_comparison_does_not_discard_a_verified_original_result():
    gateway, state = diagnosed(status="needs_test_comparison")
    state.completion_verification.update(status="cases_verified")
    state.completion_verification["repair_path"].update(status="not_needed", blocked=False)
    policy, _, _ = select(gateway, state, model=3, tools=4, money=3)
    assert (policy.minimum_completion_calls, policy.minimum_completion_tool_actions) == (3, 4)
    assert policy.allowed_tools == {"run_tests", "stop_task"}
