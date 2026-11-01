"""Independent ordinary paths and bounded exploration admission; no target execution."""

from dataclasses import replace
from decimal import Decimal

import pytest
from test_dev_completion_resources import Gateway, counters
from test_finish_reproduction_budget import snapshot
from test_repair_path_policy import path_state

from patchloop.dev import runner
from patchloop.dev.completion_budget import CompletionState
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.dev.recovery_resources import ordinary_completion_routes, successor_resources


def state(**changes):
    baseline = CompletionState(
        check_count=1, remaining_check_count=1, unused_check_count=1,
        unrun_recoverable_check=True, requires_mutation=True, anchor_available=True,
        remaining_mutations=2, mutation_retry_available=True, automatic_recheck=True,
        reproduction_case_count=1, early_reproduction_count=1, early_replay_reusable=True)
    return replace(baseline, **changes)


def routes(current, **changes):
    return ordinary_completion_routes(
        state(**changes), current, max_output_tokens=40_000,
        check_seconds=(15,), remaining_check_seconds=(15,), probe_seconds=35)


@pytest.mark.parametrize("tool,model,actions,seconds,roles", [
    ("read_file", 4, 5, 140, ["repair", "original_replay", "public_check", "finish"]),
    ("replace_text", 3, 4, 110, ["original_replay", "public_check", "finish"]),
    ("run_check", 4, 5, 155, ["repair", "original_replay", "public_check", "finish"]),
])
def test_ordinary_paths_count_host_execution_without_fabricated_model_call(
    tool, model, actions, seconds, roles,
):
    route, = routes(tool)
    assert [step.role for step in route.successors] == roles
    assert (route.model_calls, route.tool_actions, route.seconds(30)) == (model, actions, seconds)
    replay = next(step for step in route.successors if step.role == "original_replay")
    assert not replay.model_call and replay.tool_actions == 1 and replay.execution_seconds == 35


def test_current_check_and_finish_are_not_reserved_twice():
    checked, = routes("run_check", requires_mutation=False, reproduction_case_count=0,
                      early_reproduction_count=0)
    assert (checked.model_calls, checked.tool_actions, checked.seconds(30)) == (2, 2, 45)
    finished, = ordinary_completion_routes(
        state(requires_mutation=False, remaining_check_count=0, reproduction_case_count=0),
        "finish_task", max_output_tokens=40_000, check_seconds=(15,),
        remaining_check_seconds=(), probe_seconds=35)
    assert (finished.model_calls, finished.tool_actions, finished.seconds(30)) == (1, 1, 0)


@pytest.mark.parametrize("tool,model,actions,seconds", [
    ("read_file", 6, 7, 235), ("run_probe", 5, 6, 205),
])
def test_pending_diagnostic_retains_one_rejection_without_a_phantom_execution(
    tool, model, actions, seconds,
):
    route, = routes(tool, path_diagnosis_pending=True, path_request_correction_available=True)
    assert (route.model_calls, route.tool_actions, route.seconds(30)) == (model, actions, seconds)
    steps = (route.current, *route.successors)
    rejection, = [step for step in steps if step.role == "diagnostic_request_rejection"]
    assert rejection.model_call and rejection.tool_actions == 1 and rejection.execution_seconds == 0
    assert sum(step.execution_seconds == 35 for step in steps) == 2


def test_caller_read_keeps_a_separate_missing_edit_anchor():
    route, = ordinary_completion_routes(
        state(anchor_available=False), "read_file", max_output_tokens=40_000,
        check_seconds=(15,), remaining_check_seconds=(15,), probe_seconds=35,
        preserve_read_anchor=True)
    assert route.successors[0].role == "source_anchor"
    assert (route.model_calls, route.tool_actions) == (5, 6)


def test_future_original_failure_keeps_diagnosis_and_does_not_reuse_passed_check_credit():
    alternatives = ordinary_completion_routes(
        state(current_recheck_eligible=True), "replace_text", max_output_tokens=40_000,
        check_seconds=(15,), remaining_check_seconds=(15,), probe_seconds=35,
        protect_failure=True)
    required, original, diagnosed, public = alternatives
    assert [step.role for step in required.successors] == [
        "original_replay", "registered_recheck", "finish"]
    assert original.successors[-2].role == diagnosed.successors[-2].role == "public_check"
    assert [step.role for step in diagnosed.successors].count("failure_path_diagnosis") == 1
    assert [step.role for step in diagnosed.successors].count(
        "failure_diagnostic_request_rejection") == 1
    assert all(step.execution_seconds == 0 for step in diagnosed.successors
               if step.role == "failure_diagnostic_request_rejection")
    # A newly failed public check, unlike an original failure, supplies new recheck credit.
    assert public.successors[-2].role == "registered_recheck"
    assert diagnosed.model_calls == original.model_calls + 2
    assert diagnosed.tool_actions == original.tool_actions + 2
    assert diagnosed.seconds(30) == original.seconds(30) + 95


def policy(*, pending=True, model=10, tools=22, edits=2, money="3.74106870",
           early=True, seconds=2000, protocol=1):
    gateway = Gateway(initial=False, mutations=edits)
    gateway.public_task.visible_checks[0].timeout_seconds = 300
    snapshot = path_state(gateway)
    if not pending:
        snapshot.completion_verification["repair_path"] = {"status": "not_needed"}
    snapshot.completion_verification["early_replay_reusable"] = early
    ledger = DevCostLedger(Decimal(money), pricing_for_model("gpt-5.4-2026-03-05"))
    return runner._tool_policy(
        gateway, counters(model=model, tools=tools), DevLimits(max_protocol_recoveries=protocol),
        snapshot=snapshot, repair_recheck=True, cost_ledger=ledger,
        completion_cost_policy="completion-recovery-v1", desired_output_ceiling=40_000,
        max_correction_output_tokens=25_000, remaining_seconds=seconds, _preview_inspection=False)


@pytest.mark.parametrize("pending,model,tools,edits,money,readable", [
    (False, 11, 24, 3, "3.87309870", True),
    (True, 10, 22, 2, "3.74106870", True),
    (True, 8, 19, 1, "3.45626870", True),
    (True, 6, 17, 1, "3.35774270", False),
])
def test_known_failure_exploration_uses_route_not_old_multiple_failure_floor(
    pending, model, tools, edits, money, readable,
):
    actual = policy(pending=pending, model=model, tools=tools, edits=edits, money=money)
    assert ("read_file" in actual.allowed_tools) is readable
    if readable:
        row = actual.completion_cost["completion_routes"]["read_file"]
        assert row["model_calls"] <= model - 1 and row["tool_actions"] <= tools
        assert actual.completion_cost["correction_cost_reserved_nanos"] == 525_000_000
        assert actual.minimum_completion_calls == (4 if pending else 3)
    else:
        assert actual.allowed_tools == {"run_probe", "stop_task"}


@pytest.mark.parametrize("boundary", ["money", "model", "tools", "time"])
def test_speculative_release_preserves_exact_mandatory_and_correction_boundary(boundary):
    # read, rejected diagnostic, diagnostic, repair, host replay, public check, finish.
    # Protocol recovery is one separate response with 25K output and 30 seconds.
    options = dict(money="2.63940000", model=7, tools=7, seconds=585)
    fit = policy(**options)
    assert "read_file" in fit.allowed_tools
    route = fit.completion_cost["completion_routes"]["read_file"]
    assert (route["model_calls"], route["tool_actions"]) == (6, 7)
    assert route["kind"] == "required_completion" and route["released_reason"]
    assert fit.completion_cost["future_time_reserve_seconds"] == 555
    if boundary == "money":
        options["money"] = "2.639399999"
    elif boundary == "model":
        options["model"] -= 1
    elif boundary == "tools":
        options["tools"] -= 1
    else:
        options["seconds"] -= 1
    short = policy(**options)
    assert "read_file" not in short.allowed_tools
    assert "run_probe" in short.allowed_tools


def test_deferred_replay_adapter_cannot_claim_unfunded_physical_failure_recovery():
    actual = policy(pending=False, early=False, model=5, tools=5, money="20")
    assert "read_file" in actual.allowed_tools
    assert not actual.completion_cost["failure_recovery_reserved"]["read_file"]
    assert actual.completion_cost["completion_routes"]["read_file"]["adapter"]


def test_special_obligation_adapter_is_explicit_and_keeps_old_resource_forecast():
    options = dict(calls=5, max_output_tokens=40_000, check_seconds=(15,),
                   remaining_check_seconds=(15,), probe_seconds=35, acquisition_pending=True)
    legacy = successor_resources(state(), "read_file", **options)
    adapted = successor_resources(state(), "read_file", ordinary_routes=True, **options)
    assert adapted.output_ceilings == legacy.output_ceilings and adapted.seconds == legacy.seconds
    assert not adapted.routes and adapted.adapter_reason == "special_obligations"


def test_general_probe_retains_its_possible_new_case_adapter():
    options = dict(calls=5, max_output_tokens=40_000, check_seconds=(15,),
                   remaining_check_seconds=(15,), probe_seconds=35)
    adapted = successor_resources(state(), "run_probe", ordinary_routes=True, **options)
    assert not adapted.routes and adapted.adapter_reason == "special_obligations"


def test_optional_edit_adapter_uses_mutation_tools_before_claiming_future_recovery():
    gateway = Gateway(statuses=("PASS",), initial=False, mutations=2)
    gateway.public_task.visible_checks[0].timeout_seconds = 10
    current = snapshot(gateway, status="cases_verified", pending_count=0)
    ledger = DevCostLedger(Decimal("20"), pricing_for_model("gpt-5.4-2026-03-05"))
    actual = runner._tool_policy(
        gateway, counters(model=6, tools=6), DevLimits(max_protocol_recoveries=0),
        snapshot=current, cost_ledger=ledger, repair_recheck=True,
        completion_cost_policy="completion-recovery-v1", desired_output_ceiling=40_000,
        remaining_seconds=2000, _preview_inspection=False)
    assert "replace_text" in actual.allowed_tools
    assert not actual.completion_cost["failure_recovery_reserved"]["replace_text"]
