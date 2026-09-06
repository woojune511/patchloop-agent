"""Single-inspection closure advice must describe, not alter, actual admission."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_dev_budget_v16 import PolicyGateway
from test_dev_context_v12 import observe
from test_dev_context_v12 import source_gateway as source_gateway

import patchloop.dev.runner as runner
from patchloop.dev.contracts import DevLimits, DevToolResult
from patchloop.util import sha256_json


def _row25_policy_state(*, remaining=11, repair_read_used=True, probes=True):
    gateway = PolicyGateway()
    gateway.current_diff.patch = ""
    gateway.current_diff.changed_files = []
    gateway.accepted_mutations = 0
    gateway.statuses = {"first": "FAIL", "second": "NOT_RUN"}
    gateway.probe_sandbox = object() if probes else None
    limits = DevLimits()
    counters = runner._RunCounters(
        model_calls=limits.max_model_calls - remaining,
        tool_actions=30,
        failed_check_pending=True,
        check_recovery_used=True,
        check_recovery_used_ids={"first"},
        failed_check_repair_read_used=repair_read_used,
    )
    return gateway, limits, counters


def _complete_read(counters):
    after = copy.deepcopy(counters)
    after.model_calls += 1
    after.tool_actions += 1
    result = DevToolResult(
        action_id="read-next", input_hash=sha256_json("read-next"),
        tool="read_file", status="succeeded", output={"spans": []},
    )
    runner._update_inspection_counters(after, [result])
    return after


def test_row25_forecast_names_every_tool_closing_after_one_more_inspection():
    gateway, limits, counters = _row25_policy_state()
    policy = runner._tool_policy(gateway, counters, limits)
    assert policy.allowed_tools == {
        "read_file", "search_files", "run_probe", "run_check", "replace_text", "stop_task",
    }
    assert policy.completion_budget_calls == 10
    assert policy.exploration_state == "last_opportunity"
    assert policy.tools_closing_after_this_turn == (
        "read_file", "run_check", "run_probe", "search_files",
    )
    after = runner._tool_policy(gateway, _complete_read(counters), limits)
    assert after.allowed_tools == {"replace_text", "stop_task"}
    assert set(policy.tools_closing_after_this_turn) == policy.allowed_tools - after.allowed_tools


@pytest.mark.parametrize("repair_read_used", [False, True])
@pytest.mark.parametrize("probes", [False, True])
@pytest.mark.parametrize("remaining", [4, 10, 11, 12, 20])
def test_forecast_does_not_change_admission_or_live_counters(
    remaining, repair_read_used, probes,
):
    gateway, limits, counters = _row25_policy_state(
        remaining=remaining, repair_read_used=repair_read_used, probes=probes,
    )
    before_counters = copy.deepcopy(counters)
    before_statuses = dict(gateway.statuses)
    without_forecast = runner._tool_policy(
        gateway, counters, limits, _preview_inspection=False,
    )
    with_forecast = runner._tool_policy(gateway, counters, limits)
    assert replace(with_forecast, tools_closing_after_this_turn=()) == without_forecast
    assert counters == before_counters
    assert gateway.statuses == before_statuses
    assert gateway.accepted_mutations == 0
    if with_forecast.exploration_allowed:
        after = runner._tool_policy(gateway, _complete_read(counters), limits)
        assert set(with_forecast.tools_closing_after_this_turn) == (
            with_forecast.allowed_tools - after.allowed_tools
        )
    else:
        assert with_forecast.tools_closing_after_this_turn == ()
    if not probes:
        assert "run_probe" not in with_forecast.allowed_tools
        assert "run_probe" not in with_forecast.tools_closing_after_this_turn


def test_forecast_spends_current_failed_check_read_credit_in_successor():
    gateway, limits, counters = _row25_policy_state(remaining=12, repair_read_used=False)
    before = runner._tool_policy(gateway, counters, limits)
    assert before.inspection_uses_repair_credit
    assert before.current_repair_read_reserve_calls == 1
    after_counters = _complete_read(counters)
    assert after_counters.failed_check_repair_read_used
    after = runner._tool_policy(gateway, after_counters, limits)
    assert after.current_repair_read_reserve_calls == 0
    assert {"run_probe", "run_check", "read_file", "search_files"} <= after.allowed_tools
    assert before.tools_closing_after_this_turn == ()
    # Merely charging a model/tool call without consuming its repair credit
    # falsely predicts that optional checks/probes disappear at this boundary.
    wrong = runner._tool_policy(
        gateway,
        replace(
            counters, model_calls=counters.model_calls + 1, tool_actions=counters.tool_actions + 1,
        ),
        limits, _preview_inspection=False,
    )
    assert {"run_probe", "run_check"} <= before.allowed_tools - wrong.allowed_tools


def test_parallel_batch_is_not_claimed_to_match_single_inspection_forecast():
    gateway, limits, counters = _row25_policy_state(remaining=20)
    counters.tool_actions = limits.max_tool_actions - 12
    before = runner._tool_policy(gateway, counters, limits)
    assert before.max_parallel_reads == 2
    assert before.tools_closing_after_this_turn == ()
    two_reads = replace(counters, model_calls=counters.model_calls + 1, tool_actions=90)
    after = runner._tool_policy(gateway, two_reads, limits)
    assert {"read_file", "search_files", "run_probe"} <= before.allowed_tools - after.allowed_tools


def test_newly_acquired_anchor_can_change_the_conditional_successor():
    gateway, limits, counters = _row25_policy_state(remaining=5)
    gateway.anchor = False
    before = runner._tool_policy(gateway, counters, limits)
    assert before.required_inspection_for_completion
    assert "replace_text" not in before.allowed_tools
    after_counters = _complete_read(counters)
    unchanged = runner._tool_policy(gateway, after_counters, limits)
    assert unchanged.allowed_tools == {"stop_task"}
    assert set(before.tools_closing_after_this_turn) == (
        before.allowed_tools - unchanged.allowed_tools
    )
    gateway.anchor = True
    with_new_evidence = runner._tool_policy(gateway, after_counters, limits)
    assert with_new_evidence.completion_possible
    assert "replace_text" in with_new_evidence.allowed_tools


def test_context_projects_delivered_navigation_and_conditional_forecast(source_gateway):
    gateway, sources, _ = source_gateway
    sources["src.py"] = (
        b"def editable():\n    return 1\n\ndef not_observed():\n    return 2\n"
    )
    sources["helper.py"] = b"class PublicHelper:\n    pass\n"
    observe(gateway, "src.py", 1, 2, action_id="editable-source")
    latest = observe(gateway, "helper.py", 1, 2, action_id="helper-source")
    before = gateway.journal.path.read_bytes()
    context = json.loads(runner._build_context(
        package=SimpleNamespace(public=gateway.public_task), gateway=gateway,
        journal=gateway.journal, correction=None, latest_tool_results=[latest],
        counters=runner._RunCounters(), elapsed_seconds=0, limits=DevLimits(),
    ))
    index = context["observed_source_index"]
    assert [(row["path"], row["name"], row["start_line"]) for row in index["entries"]] == [
        ("src.py", "editable", 1), ("helper.py", "PublicHelper", 1),
    ]
    assert "not_observed" not in json.dumps(index)
    assert "content" not in json.dumps(index)
    assert all(span["path"] != "helper.py" for span in context["source_spans"])
    assert context["latest_tool_results"][0]["output"]["spans"][0]["path"] == "helper.py"
    assert context["action_horizon"]["tool_closure_prediction_basis"] == (
        "after_one_read_or_search_with_unchanged_evidence; "
        "larger_parallel_batches_or_other_actions_may_differ"
    )
    assert gateway.journal.path.read_bytes() == before
