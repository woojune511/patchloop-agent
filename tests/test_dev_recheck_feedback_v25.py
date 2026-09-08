"""Separate a historical failure from the current candidate's completion path."""

from __future__ import annotations

import copy
import json
from itertools import permutations
from types import SimpleNamespace

import pytest
from native_history_support import input_context
from test_dev_budget_v16 import PolicyGateway
from test_dev_feedback_integration_v18 import _completed_batch, _context, _input
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart

import patchloop.dev.runner as runner
from patchloop.contracts import RegisteredCheck
from patchloop.dev.contracts import (
    DEV_RUN_SCHEMA,
    DevLimits,
    DevToolResult,
    PublicTurnDecision,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT
from patchloop.dev.tools import ALL_DEV_TOOLS, DevToolGateway, dev_tool_schemas, validate_tool_batch
from patchloop.util import sha256_json


def _failure(diff_hash):
    return {
        "check_id": "first", "diff_hash": diff_hash,
        "exception_type": "AssertionError",
        "comparison_with_previous_failure": {"relation": "first_observation"},
        "execution_boundary": {"later_source_lines_observed": None},
    }


def _focus(failure, *, remaining=0, allowed=frozenset(), current="current"):
    gateway = SimpleNamespace(
        _active_failed_check={"public_check_failure": failure},
        limits=DevLimits(), accepted_mutations=4 - remaining,
    )
    return DevToolGateway.current_public_failure(
        gateway, diff_hash=current, allowed_tools=allowed,
    )


@pytest.mark.parametrize("diff,currency", [
    ("current", "current"), ("previous", "historical"), (None, "unknown"),
])
@pytest.mark.parametrize("allowed", [
    frozenset({"stop_task"}),
    frozenset({"run_check", "stop_task"}),
    frozenset({"replace_text", "read_file", "search_files", "stop_task"}),
])
def test_failure_currency_and_advice_follow_evidence_and_offered_tools(diff, currency, allowed):
    failure = _failure(diff)
    before = copy.deepcopy(failure)
    focus = _focus(failure, remaining=2, allowed=allowed)
    assert focus["evidence_currency"] == currency
    assert focus["phase"] == (
        "repair_current_diff" if currency == "current" else "awaiting_recheck"
    )
    assert focus["diff_hash"] == diff and focus["current_diff_hash"] == "current"
    guidance = focus["mutation_pressure"]["guidance"]
    assert len(guidance) <= 600
    assert all(tool not in guidance for tool in ALL_DEV_TOOLS - allowed)
    if currency != "current":
        assert (
            "not the current candidate" in guidance or "not a current-candidate verdict" in guidance
        )
        assert "replace_text" not in guidance
        assert ("run_check" in guidance) == ("run_check" in allowed)
    else:
        assert guidance.startswith("This check failed on the current diff.")
        assert ("replace_text" in guidance) == ("replace_text" in allowed)
    assert failure == before


def test_zero_mutations_is_not_presented_as_zero_verification_capacity():
    failure = _failure("previous")
    checking = _focus(failure, allowed=frozenset({"run_check", "stop_task"}))
    assert checking["mutation_pressure"]["accepted_mutations_remaining"] == 0
    assert "do not require another mutation" in checking["mutation_pressure"]["guidance"]
    closed = _focus(failure, allowed=frozenset({"stop_task"}))
    assert "run_check" not in closed["mutation_pressure"]["guidance"]
    assert "available checks" not in closed["mutation_pressure"]["guidance"]
    # A real current-diff failure is not softened into an untested candidate.
    current = _focus(_failure("current"), allowed=frozenset({"stop_task"}))
    assert current["evidence_currency"] == "current"
    assert current["mutation_pressure"]["guidance"] == "This check failed on the current diff."


@pytest.mark.parametrize("order", list(permutations(("first", "second"))))
@pytest.mark.parametrize("remaining_calls", [3, 7])
def test_last_mutation_keeps_conditional_check_check_finish_path(order, remaining_calls):
    gateway = PolicyGateway()
    gateway.accepted_mutations = 4
    gateway.statuses = {"first": "NOT_RUN", "second": "NOT_RUN"}
    limits = DevLimits()
    counters = runner._RunCounters(model_calls=40 - remaining_calls, tool_actions=33)
    stop = RequestedTool(
        name="stop_task", action_id="voluntary-stop",
        arguments={"reason_code": "no_safe_scoped_mutation", "summary": "Model judgment."},
        turn_decision=PublicTurnDecision(mode="stop", basis="A public judgment."),
    )
    for step in range(3):
        before = copy.deepcopy((gateway.statuses, counters))
        policy = runner._tool_policy(gateway, counters, limits)
        assert (gateway.statuses, counters) == before
        assert policy.completion_possible
        assert policy.minimum_completion_calls == 3 - step
        assert "replace_text" not in policy.allowed_tools
        assert validate_tool_batch([stop], allowed_tools=policy.allowed_tools) == "single_action"
        if step < 2:
            assert "run_check" in policy.allowed_tools and order[step] in policy.check_ids
            # Conditional policy oracle only: no claim that a real candidate passed.
            gateway.statuses[order[step]] = "PASS"
            counters.model_calls += 1
            counters.tool_actions += 1
        else:
            assert policy.workflow_gate == "ready_to_submit"
            assert "finish_task" in policy.allowed_tools


@pytest.mark.parametrize("statuses,remaining_calls", [
    ({"first": "FAIL", "second": "NOT_RUN"}, 7),
    ({"first": "NOT_RUN", "second": "NOT_RUN"}, 2),
])
def test_real_failure_or_insufficient_completion_budget_still_closes_dispatch(
    statuses, remaining_calls,
):
    gateway = PolicyGateway()
    gateway.accepted_mutations = 4
    gateway.statuses = statuses
    policy = runner._tool_policy(
        gateway, runner._RunCounters(model_calls=40 - remaining_calls), DevLimits(),
    )
    assert not policy.completion_possible
    assert policy.allowed_tools == {"stop_task"}


def test_last_edit_feedback_survives_native_delivery_restart_and_action_replay(tmp_path):
    gateway = _gateway(tmp_path)
    gateway.limits = DevLimits(max_accepted_mutations=1)
    gateway.public_task.visible_checks = [
        RegisteredCheck(id=name, command=["python", "-c", "assert True"])
        for name in ("first", "second")
    ]
    _read(gateway)
    baseline = gateway.current_diff_hash
    check = DevToolResult(
        action_id="old-public-check", input_hash=sha256_json("old-public-check"),
        tool="run_check", status="succeeded", workspace_diff_hash=baseline,
        output={"check_id": "first", "diff_hash": baseline, "passed": False,
                "failure_signature": sha256_json("public failure"),
                "public_check_failure": _failure(baseline)},
    )
    gateway.journal.append("action_finished", {"result": check.model_dump(mode="json")})
    gateway._remember_check(check.output)
    call = _mutation("last-repair")
    _, results = _completed_batch(gateway, [call], "last-repair-turn")
    context = _context(gateway, results)
    canonical = json.loads(context)
    items = _input(gateway, results, tmp_path, context=context)
    view = input_context(items)
    focus = canonical["current_public_failure"]
    assert view["current_public_failure"] is None
    assert view["pending_recheck"]["current_check_status"] == "NOT_RUN"
    assert view["pending_recheck"]["previous_failure"]["diff_hash"] == baseline
    assert focus["evidence_currency"] == "historical" and focus["phase"] == "awaiting_recheck"
    assert "run_check" in focus["mutation_pressure"]["guidance"]
    assert "replace_text" not in focus["mutation_pressure"]["guidance"]
    assert view["remaining_budget"]["accepted_mutations"] == 0
    assert view["action_horizon"]["completion_possible"]
    assert [c["status"] for c in view["visible_check_status"]] == ["NOT_RUN", "NOT_RUN"]
    assert focus["diff_hash"] == baseline != focus["current_diff_hash"]
    before = gateway.journal.path.read_bytes()
    before_source = (gateway.workspace / "src.py").read_bytes()
    restored = _restart(gateway)
    replay = restored.execute(call)
    assert replay.replayed and restored.accepted_mutations == 1
    assert _input(restored, results, tmp_path, context=context) == items
    restored_view = input_context(_input(restored, results, tmp_path))
    assert restored_view["current_public_failure"] is None
    assert restored_view["pending_recheck"] == view["pending_recheck"]
    assert gateway.journal.path.read_bytes() == before
    assert (gateway.workspace / "src.py").read_bytes() == before_source
    # A successful recheck clears the latest failure, not every other unchecked obligation.
    restored._remember_check({"check_id": "first", "diff_hash": restored.current_diff_hash,
                              "passed": True, "failure_signature": None})
    assert restored.current_public_failure() is None
    assert restored.visible_check_status()[1]["status"] == "NOT_RUN"


def test_feedback_changes_preserve_wire_limits_and_bounded_prompt():
    # V34 compresses memory descriptions only; ordered input shapes and non-memory
    # descriptions are independently pinned in test_dev_memory_guidance_v34.
    assert sha256_json(dev_tool_schemas(
        finish_enabled=True, allowed_tools=ALL_DEV_TOOLS, check_ids=["first", "second"],
    )) == "sha256:ec8bf855315bce7c01143b5717d3173dc61b105b4d8e7f59ac656fb38d637f37"
    assert dev_tool_surface_hash() != (
        "sha256:3a114a877f58c774aca0f555b106d7361df7b3087b4c04aa2903cbb9a49853cc"
    )
    assert DEV_RUN_SCHEMA == "dev-run-v1"
    assert len(DEV_SYSTEM_PROMPT) <= 8007
    assert "Zero remaining mutations forbids further" in DEV_SYSTEM_PROMPT
    assert "mutation_completion_horizon describes another edit" in DEV_SYSTEM_PROMPT
    limits = DevLimits()
    assert (limits.max_model_calls, limits.max_tool_actions,
            limits.max_accepted_mutations, limits.wall_time_seconds) == (40, 100, 4, 1800)
