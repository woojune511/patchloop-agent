"""Shared diagnosis exploration budgets; no model, target process or container."""

from dataclasses import replace

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_repair_path_policy import path_state

from patchloop.dev import runner
from patchloop.dev.completion_budget import CompletionState
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import (
    COMPLETION_MINIMUM_POLICY,
    COMPLETION_RECOVERY_POLICY,
    FINALIZATION_OUTPUT_FLOOR,
    recovery_successor_output_ceilings,
)
from patchloop.dev.recovery_resources import (
    CHECK_OVERHEAD_SECONDS,
    FOLLOWUP_SECONDS,
    successor_resources,
)


def pending(gateway, *, ruleless=False):
    state = path_state(gateway)
    if ruleless:
        state.completion_verification["repair_path"].update(
            call_id=None, call_selection_required=True,
            call_choices=[{"call_id": "call-1"}, {"call_id": "call-2"}],
            call_mapping="model_selected_unverified")
    return state


@pytest.mark.parametrize("ruleless", [False, True])
def test_repeated_exploration_and_reconstruction_keep_the_original_trace_and_correction(ruleless):
    gateway = Gateway(initial=False)
    state = pending(gateway, ruleless=ruleless)
    path = state.completion_verification["repair_path"]
    for used in range(4):
        path["preparation_action_ids"] = [f"read-{index}" for index in range(used)]
        counts = counters(model=8-used, tools=9-used)
        policy = runner._tool_policy(gateway, counts, DevLimits(), snapshot=state)
        assert "run_probe" in policy.allowed_tools and "replace_text" not in policy.allowed_tools
        assert policy.model_turns_available_for_exploration == max(0, 3-used)
        assert policy.repair_path_diagnosis["preparation_model_turns_available"] == max(0, 3-used)
        assert policy.repair_path_diagnosis["preparation_tool_actions_available"] == max(0, 3-used)
        assert policy.repair_path_diagnosis["preparation_completion_calls_reserved"] == 4
        assert policy.repair_path_diagnosis["preparation_completion_tool_actions_reserved"] == 5
        assert policy.repair_path_diagnosis["preparation_request_correction_reserved"]
        assert ("read_file" in policy.allowed_tools) is (used < 3)
        assert runner._tool_policy(gateway, replace(counts), DevLimits(), snapshot=state) == policy
    assert path["preparation_available"] and not path["execution_attempted"]
    assert path["rejected_requests"] == 0


def test_exploration_releases_correction_slack_only_after_the_request_was_rejected():
    gateway = Gateway(initial=False)
    state = pending(gateway)
    counts = counters(model=5, tools=6)
    before = runner._tool_policy(gateway, counts, DevLimits(), snapshot=state)
    assert before.allowed_tools == {"run_probe", "stop_task"}
    state.completion_verification["repair_path"]["rejected_requests"] = 1
    after = runner._tool_policy(gateway, counts, DevLimits(), snapshot=state)
    assert after.allowed_tools == {"read_file", "search_files", "run_probe", "stop_task"}
    assert after.model_turns_available_for_exploration == 1
    assert not after.repair_path_diagnosis["preparation_request_correction_reserved"]
    assert after.minimum_completion_calls == before.minimum_completion_calls == 4


def test_caller_read_does_not_claim_the_still_missing_source_anchor():
    gateway = Gateway(initial=False, anchor=False)
    state = pending(gateway)
    policy = runner._tool_policy(
        gateway, counters(model=7, tools=8), DevLimits(), snapshot=state,
        cost_ledger=ledger_for_slots(7), completion_cost_policy=COMPLETION_MINIMUM_POLICY)
    assert policy.model_turns_available_for_exploration == 1
    assert policy.minimum_completion_calls == 5
    assert policy.inspection_reserve_calls == 6  # Includes missing anchor + request correction.
    assert policy.completion_cost["future_calls_reserved"] == 6
    assert "reading a caller or test does not establish it" in (
        runner._completion_guidance(state, policy)["message"])
    state.completion_verification["repair_path"]["preparation_action_ids"] = ["caller-read"]
    after = runner._tool_policy(gateway, counters(model=6, tools=7), DevLimits(), snapshot=state)
    assert after.allowed_tools == {"run_probe", "stop_task"}
    assert after.minimum_completion_calls == 5
    # Only actual current mutation evidence can release that separate read reservation.
    state = replace(state, mutation_evidence_paths=("src.py",))
    anchored = runner._tool_policy(gateway, counters(model=6, tools=7), DevLimits(), snapshot=state)
    assert anchored.minimum_completion_calls == 4 and "read_file" in anchored.allowed_tools


@pytest.mark.parametrize("ruleless", [False, True])
@pytest.mark.parametrize("anchor", [False, True])
def test_role_cost_and_time_preserve_pending_diagnostic_missing_anchor_and_correction(
    ruleless, anchor,
):
    gateway = Gateway(initial=False, mutations=1, anchor=anchor)
    gateway.public_task.visible_checks[0].timeout_seconds = 10
    state = pending(gateway, ruleless=ruleless)
    limits = DevLimits(max_protocol_recoveries=0)
    calls = 5 + int(not anchor)  # Current minimum, plus one rejected-request correction.
    outputs = recovery_successor_output_ceilings(
        calls=calls, max_output_tokens=40_000, repair_calls=1,
        preparation_calls=int(not anchor))
    ledger = ledger_for_slots(100)
    read_cost = ledger.future_call_reservation_nanos(output_ceiling=FINALIZATION_OUTPUT_FLOOR)
    successor_cost = sum(ledger.future_call_reservation_nanos(output_ceiling=n) for n in outputs)
    ledger.cap_nanos = read_cost + successor_cost
    probe_seconds = runner.PROBE_TIMEOUT_SECONDS + CHECK_OVERHEAD_SECONDS
    # One pending diagnostic and one post-edit original replay. The rejected
    # request consumes a response/action, but has no phantom target execution.
    future_seconds = 15 + 2 * probe_seconds + FOLLOWUP_SECONDS * calls

    def choose(seconds):
        return runner._tool_policy(
            gateway, counters(model=20, tools=30), limits, snapshot=state,
            cost_ledger=ledger, completion_cost_policy=COMPLETION_RECOVERY_POLICY,
            desired_output_ceiling=40_000, remaining_seconds=seconds)

    fits = choose(future_seconds + FOLLOWUP_SECONDS)
    assert "read_file" in fits.allowed_tools and fits.model_turns_available_for_exploration == 1
    assert fits.completion_cost["successor_output_ceilings"]["read_file"] == list(outputs)
    assert fits.completion_cost["future_cost_reserve_nanos"] == successor_cost
    assert fits.completion_cost["future_time_reserve_seconds"] == future_seconds
    assert fits.tools_closing_after_this_turn == ("read_file", "search_files")
    short_time = choose(future_seconds + FOLLOWUP_SECONDS - 1)
    assert "read_file" not in short_time.allowed_tools and "run_probe" in short_time.allowed_tools
    assert short_time.completion_cost["resource_rejections"]["read_file"] == "time"
    ledger.cap_nanos -= 1
    short_money = choose(future_seconds + FOLLOWUP_SECONDS)
    assert "read_file" not in short_money.allowed_tools and "run_probe" in short_money.allowed_tools
    assert short_money.completion_cost["resource_rejections"]["read_file"] == "cost"


def test_non_diagnosis_successor_time_and_anchor_roles_remain_unchanged():
    state = CompletionState(
        check_count=1, remaining_check_count=1, unused_check_count=0,
        unrun_recoverable_check=False, requires_mutation=True, anchor_available=False,
        remaining_mutations=1, mutation_retry_available=False, reproduction_case_count=1)
    options = dict(calls=6, max_output_tokens=40_000, check_seconds=(15,),
                   remaining_check_seconds=(15,), probe_seconds=80)
    baseline = successor_resources(state, "read_file", **options)
    explicit = successor_resources(state, "read_file", preserve_pending_diagnosis=False, **options)
    diagnostic = successor_resources(state, "read_file", preserve_pending_diagnosis=True, **options)
    assert baseline == explicit
    assert diagnostic.seconds == baseline.seconds + 80
    assert baseline.output_ceilings[0] == 40_000
    assert diagnostic.output_ceilings[:2] == (FINALIZATION_OUTPUT_FLOOR, 40_000)
