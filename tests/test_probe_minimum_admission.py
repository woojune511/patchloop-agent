"""Public observation choices retain actual completion work in every resource dimension."""

from copy import deepcopy
from decimal import Decimal

import pytest
from test_dev_completion_resources import Gateway, counters
from test_finish_reproduction_budget import snapshot

from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import DevCostLedger, pricing_for_model


def policy(*, calls=13, tools=31, money="3.861695", seconds=2000,
           cases=1, first=False, anchor=True):
    gateway = Gateway(initial=True, mutations=3, anchor=anchor)
    gateway.public_task.visible_checks[0].timeout_seconds = 300
    state = snapshot(gateway, status="refuted", pending_count=0, case_count=cases)
    state.completion_verification.update(
        early_replay_reusable=False,
        baseline_failure_case_ids=[f"original-{index}" for index in range(cases)],
        original_obligation={"stage": "acquired"},
        first_observation={"status": "available" if first else "observed", "available": first},
    )
    saved = deepcopy(state.completion_verification)
    ledger = DevCostLedger(Decimal(money), pricing_for_model("gpt-5.4-2026-03-05"))
    result = runner._tool_policy(gateway, counters(model=calls, tools=tools), DevLimits(),
        snapshot=state, repair_recheck=True, cost_ledger=ledger,
        completion_cost_policy="completion-recovery-v1", desired_output_ceiling=40_000,
        max_correction_output_tokens=25_000, remaining_seconds=seconds,
        _preview_inspection=False)
    assert ledger.spent_nanos == 0
    assert state.completion_verification == saved
    return result


def test_acquired_failure_probe_releases_future_failure_reserve_like_reading():
    # The saved seq114 inputs left USD3.861695. The protected general probe
    # cost USD3.866520; the mandatory route plus prospective replay fits.
    result = policy()
    assert {"read_file", "run_probe", "replace_text"} <= result.allowed_tools
    assert "finish_task" not in result.allowed_tools
    cost = result.completion_cost
    route = cost["completion_routes"]["run_probe"]
    assert route["released_reason"] == "speculative_future_failure_does_not_fit"
    assert not cost["failure_recovery_reserved"]["run_probe"]
    assert (route["model_calls"], route["tool_actions"]) == (4, 6)
    assert cost["correction_model_calls_reserved"] == 1


@pytest.mark.parametrize("boundary", ["calls", "tools", "cost", "time"])
def test_minimum_probe_preserves_originals_new_case_check_finish_and_correction(boundary):
    # Four responses: probe, repair, check, finish; two host replays (existing
    # original plus the possible new case) make six actions. One correction
    # response is additional. Probe/check execution and each follow-up are reserved.
    options = dict(calls=5, tools=6, money="2.570760000", seconds=560)
    assert "run_probe" in policy(**options).allowed_tools
    if boundary == "calls":
        options["calls"] = 4
    elif boundary == "tools":
        options["tools"] = 5
    elif boundary == "cost":
        options["money"] = "2.570759999"
    else:
        options["seconds"] = 559.999
    short = policy(**options)
    assert "run_probe" not in short.allowed_tools
    assert "finish_task" not in short.allowed_tools
    assert short.completion_cost["correction_model_calls_reserved"] == 1


def test_protected_route_remains_preferred_when_it_really_fits():
    fit = policy(calls=8, tools=11, money="20")
    route = fit.completion_cost["completion_routes"]["run_probe"]
    assert route["kind"] == "one_failure_revision"
    assert route["released_reason"] is None
    assert (route["model_calls"], route["tool_actions"]) == (7, 11)
    assert (route["required_model_calls"], route["required_tool_actions"]) == (4, 6)
    # The additional failure invalidates both originals, not just the old one.
    short = policy(calls=8, tools=10, money="20")
    assert "run_probe" in short.allowed_tools
    assert not short.completion_cost["failure_recovery_reserved"]["run_probe"]


def test_each_existing_original_keeps_its_action_and_timeout_in_addition_to_new_case():
    one = policy(calls=5, tools=6, money="2.570760000", seconds=560)
    two = policy(calls=5, tools=7, money="2.570760000", seconds=595, cases=2)
    assert "run_probe" in one.allowed_tools and "run_probe" in two.allowed_tools
    route = two.completion_cost["completion_routes"]["run_probe"]
    assert route["tool_actions"] == 7
    assert (two.completion_cost["future_time_reserve_seconds"]
            == one.completion_cost["future_time_reserve_seconds"] + 35)
    assert "run_probe" not in policy(calls=5, tools=6, money="20", cases=2).allowed_tools
    assert "run_probe" not in policy(calls=5, tools=7, money="20",
                                    seconds=594.999, cases=2).allowed_tools


def test_optional_probe_preserves_first_original_observation_until_it_is_spent():
    options = dict(calls=6, tools=7, money="2.843640000", seconds=625, first=True)
    result = policy(**options)
    assert {"run_probe", "observe_original"} <= result.allowed_tools
    route = result.completion_cost["completion_routes"]["run_probe"]
    assert (route["model_calls"], route["tool_actions"]) == (5, 7)
    assert "run_probe" not in policy(**{**options, "seconds": 624.999}).allowed_tools
    assert "run_probe" not in policy(**{**options, "calls": 5}).allowed_tools
    spent = policy(calls=5, tools=6, money="2.570760000", seconds=560, first=False)
    assert "run_probe" in spent.allowed_tools
    assert "observe_original" not in spent.allowed_tools


def test_probe_does_not_promise_a_missing_current_source_anchor():
    result = policy(calls=6, tools=7, money="20", anchor=False)
    assert "run_probe" in result.allowed_tools
    route = result.completion_cost["completion_routes"]["run_probe"]
    assert (route["model_calls"], route["tool_actions"]) == (5, 7)
    assert "run_probe" not in policy(calls=5, tools=7, money="20", anchor=False).allowed_tools


def test_ruleless_first_observation_does_not_close_other_observation_choices():
    result = policy(first=True)
    assert {"read_file", "search_files", "observe_original", "run_probe"} <= result.allowed_tools
    routes = result.completion_cost["completion_routes"]
    assert (routes["observe_original"]["model_calls"],
            routes["observe_original"]["tool_actions"]) == (4, 5)
    assert (routes["read_file"]["model_calls"], routes["read_file"]["tool_actions"]) == (5, 6)
    assert (routes["run_probe"]["model_calls"], routes["run_probe"]["tool_actions"]) == (5, 7)


@pytest.mark.parametrize("boundary", ["calls", "tools", "cost", "time"])
@pytest.mark.parametrize("tool,calls,tools,money,seconds", [
    ("observe_original", 5, 5, "2.570760000", 525),
    ("read_file", 6, 6, "2.843640000", 555),
])
def test_first_observation_and_preparation_share_exact_success_path_bounds(
    boundary, tool, calls, tools, money, seconds,
):
    # Observing the registered call adds no case. Reading keeps that observation
    # ahead instead: one response, one action, and 35 seconds of target execution.
    options = dict(calls=calls, tools=tools, money=money, seconds=seconds, first=True)
    fit = policy(**options)
    assert tool in fit.allowed_tools
    assert fit.completion_cost["correction_model_calls_reserved"] == 1
    if boundary == "calls":
        options["calls"] -= 1
    elif boundary == "tools":
        options["tools"] -= 1
    elif boundary == "cost":
        options["money"] = str(Decimal(money) - Decimal("0.000000001"))
    else:
        options["seconds"] -= 0.001
    short = policy(**options)
    assert tool not in short.allowed_tools
    assert "finish_task" not in short.allowed_tools
    if tool == "read_file":
        assert "search_files" not in short.allowed_tools
        assert "observe_original" in short.allowed_tools
