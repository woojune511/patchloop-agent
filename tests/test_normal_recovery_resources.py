"""Normal-loop repair funding and bounded provider time, no live transport."""

from dataclasses import replace
from decimal import Decimal

from test_dev_completion_resources import Gateway, counters
from test_dev_segments import assert_submitted, configured, records

from patchloop.dev import cost, runner
from patchloop.dev.completion_budget import CompletionState
from patchloop.dev.contracts import DevLimits
from patchloop.dev.recovery_resources import successor_resources


def state(**changes):
    return replace(CompletionState(
        check_count=1, remaining_check_count=1, unused_check_count=1,
        unrun_recoverable_check=True, requires_mutation=True, anchor_available=True,
        remaining_mutations=2, mutation_retry_available=False, automatic_recheck=True,
    ), **changes)


def route(tool, *, calls, selected=None, **changes):
    return successor_resources(selected or state(), tool, calls=calls,
        max_output_tokens=40_000, check_seconds=(305,), remaining_check_seconds=(305,),
        probe_seconds=35, **changes)


def test_read_preserves_a_full_edit_and_one_regression_revision():
    value = route("read_file", calls=3, protect_failure=True)
    assert value.output_ceilings == (8192, 40000, 40000, 8192, 8192)
    assert value.seconds == 2 * 305 + 5 * 30
    assert value.failure_recovery


def test_original_only_failure_does_not_borrow_registered_recheck_discount():
    original = state(reproduction_case_count=1, unused_check_count=0)
    value = route("replace_text", calls=2, selected=original, protect_failure=True)
    assert len(value.output_ceilings) == 5  # check, read, edit, check, finish
    assert value.seconds == 2 * 305 + 2 * 35 + 5 * 30
    no_checks = replace(original, check_count=0, remaining_check_count=0)
    value = successor_resources(no_checks, "replace_text", calls=1, max_output_tokens=40000,
        check_seconds=(), remaining_check_seconds=(), probe_seconds=35, protect_failure=True)
    assert value.output_ceilings == (8192, 40000, 8192)


def test_paired_selected_tests_keep_both_execution_timeouts():
    one = route("run_tests", calls=3, optional_check_seconds=65)
    pair = route("run_tests", calls=3, optional_check_seconds=65, test_comparison=True)
    assert pair.seconds - one.seconds == 65


def test_test_addition_preserves_pair_and_both_mutations_host_checks():
    original = state(reproduction_case_count=1, current_recheck_eligible=True)
    value = route("replace_text", calls=4, selected=original, test_edit=True,
                  optional_check_seconds=65)
    assert 40000 in value.output_ceilings
    assert value.seconds == 305 + 305 + 2 * 65 + 2 * 35 + 4 * 30


def choose(gateway, *, seconds=1800, money="4.50", counts=None):
    # The synthetic Gateway counts consumed edits from four, independently of CLI defaults.
    return runner._tool_policy(gateway, counts or counters(model=18, tools=38),
        DevLimits(max_accepted_mutations=4),
        cost_ledger=cost.DevCostLedger(Decimal(money), cost.pricing_for_model(
            "gpt-5.4-mini-2026-03-17")), completion_cost_policy=cost.COMPLETION_RECOVERY_POLICY,
        desired_output_ceiling=40000, max_correction_output_tokens=25000,
        repair_recheck=True, remaining_seconds=seconds)


def test_low_time_closes_exploration_but_keeps_a_verified_completion_route():
    gateway = Gateway()
    gateway.public_task.visible_checks[0].timeout_seconds = 300
    roomy = choose(gateway)
    assert "read_file" in roomy.allowed_tools
    assert roomy.completion_cost["failure_recovery_reserved"]["read_file"]
    # Current response, check/finish successors and the unused protocol correction.
    limited = choose(gateway, seconds=450)
    assert "replace_text" in limited.allowed_tools and "read_file" not in limited.allowed_tools
    assert not limited.completion_cost["failure_recovery_reserved"]["replace_text"]
    blocked = choose(gateway, seconds=360)
    assert blocked.allowed_tools == {"stop_task"} and not blocked.completion_possible
    assert "time" in blocked.completion_cost["resource_rejections"].values()


def test_last_edit_does_not_reserve_an_impossible_extra_revision():
    gateway = Gateway()
    gateway.accepted_mutations = 3
    selected = choose(gateway)
    assert not any(selected.completion_cost["failure_recovery_reserved"].values())
    assert selected.completion_cost["successor_output_ceilings"]["replace_text"] == [8192, 8192]


def test_optional_inspection_cannot_starve_the_current_full_repair():
    gateway = Gateway()
    selected = choose(gateway, money="0.60")
    assert selected.allowed_tools == {"replace_text", "edit_files", "stop_task"}
    details = selected.completion_cost
    ledger = cost.DevCostLedger(Decimal("0.60"), cost.pricing_for_model(
        "gpt-5.4-mini-2026-03-17"))
    admitted = ledger.admit(60000, desired_output_ceiling=40000,
        minimum_output_ceiling=details["current_minimum_output_ceiling"],
        future_cost_reserve_nanos=details["future_cost_reserve_nanos"])
    assert admitted is not None and admitted.output_ceiling == 40000


def test_actual_count_and_generation_leave_the_same_verification_deadline(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"completion_cost_policy": cost.COMPLETION_RECOVERY_POLICY,
        "max_output_tokens": 40000, "max_correction_output_tokens": 25000,
        "max_cost_usd": Decimal("4.50")})
    adapter = runner.OpenAIResponsesAdapter
    count, generate = adapter.count_input_tokens_v2, adapter.execute_request
    timeouts = []

    def counted_call(self, payload, *, timeout_seconds):
        timeouts.append(("count", timeout_seconds))
        return count(self, payload, timeout_seconds=timeout_seconds)

    def generated_call(self, payload, *, requested_input_tokens, timeout_seconds):
        timeouts.append(("generate", timeout_seconds))
        return generate(self, payload, requested_input_tokens=requested_input_tokens,
                        timeout_seconds=timeout_seconds)

    monkeypatch.setattr(adapter, "count_input_tokens_v2", counted_call)
    monkeypatch.setattr(adapter, "execute_request", generated_call)
    assert_submitted(runner.run_dev(request)["runs"][0])
    assert inputs == counted
    journal, _ = records(request)
    starts = [e["payload"] for e in journal.events() if e["event_type"] == "provider_call_started"]
    assert len(timeouts) == 2 * len(starts)
    assert starts[0]["future_time_reserve_seconds"] > 0
    for index, row in enumerate(starts):
        assert timeouts[2 * index][0] == "count"
        assert timeouts[2 * index + 1][0] == "generate"
        assert timeouts[2 * index + 1][1] <= timeouts[2 * index][1]
        assert row["timeout_seconds"] == timeouts[2 * index + 1][1]
        assert row["timeout_seconds"] + row["future_time_reserve_seconds"] <= (
            request.limits.wall_time_seconds - row["active_elapsed_ms"] / 1000 + .1)
    assert starts[-1]["completion_cost"]["successor_output_ceilings"]["finish_task"] == []


def test_exhausted_time_stops_before_counting_or_dispatch(tmp_path, monkeypatch):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"completion_cost_policy": cost.COMPLETION_RECOVERY_POLICY,
        "limits": request.limits.model_copy(update={"wall_time_seconds": 30})})
    row = runner.run_dev(request)["runs"][0]
    assert row["terminal"] == "LIMIT_REACHED"
    assert not inputs and not counted and row["cost_nanos"] == 0
