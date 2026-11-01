"""Completion requirements must not masquerade as the remaining run allowance."""

import copy
import json

import pytest
from test_completion_context import state
from test_dev_completion_resources import Gateway, counters

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json


def public_budget_state(remaining):
    gateway = Gateway(statuses=("PASS",), initial=False, mutations=3)
    gateway.verification_policy = "public-checks-v1"
    policy = runner._tool_policy(
        gateway, counters(model=remaining, tools=87), DevLimits(max_accepted_mutations=4),
        repair_recheck=True,
    )
    original = state()
    original["latest_tool_results"] = []
    original["current_public_failure"] = None
    original["working_notes"] = {"findings": [], "verification": {"items": []}}
    original["source_spans"][0]["content"] = "CURRENT_REPAIR_ANCHOR"
    original["source_spans"][0]["end_line"] = 10
    original["available_tool_names"] = sorted(policy.allowed_tools)
    original["remaining_budget"] = {
        "model_calls": remaining, "tool_actions": 87, "accepted_mutations": 3,
        "active_wall_time_seconds": 1209, "cost": {"remaining": 3504356000},
    }
    original["action_horizon"] = {
        "minimum_completion_calls": policy.minimum_completion_calls,
        "completion_budget_calls": policy.completion_budget_calls,
        **runner._completion_resources_payload(policy),
        "completion_possible": policy.completion_possible,
        "protected_completion_possible": policy.protected_completion_possible,
        "exploration_state": policy.exploration_state,
        "model_turns_available_for_exploration": policy.model_turns_available_for_exploration,
        "tool_actions_available_for_exploration": policy.tool_actions_available_for_exploration,
        "closure_reason": policy.closure_reason,
        "action_budget": policy.action_budget,
    }
    return original


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("agent_policy", ["current", "thin"])
@pytest.mark.parametrize("remaining", [32, 1])
def test_actual_completion_input_distinguishes_one_step_reserve_from_remaining_calls(
    tmp_path, context_policy, agent_policy, remaining,
):
    original = public_budget_state(remaining)
    before = copy.deepcopy(original)
    journal = DevJournal(tmp_path, "run_dev_completionreserve")
    with journal.execution_lock():
        items = runner._build_model_input(
            journal=journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
            context=canonical_json(original), latest_tool_results=[],
            context_policy=context_policy, planning_policy="none",
            agent_policy=agent_policy,
        )
    actual = reconstruct_state(items, context_policy=context_policy)
    assert actual["remaining_budget"] == original["remaining_budget"]
    assert actual["available_tool_names"] == original["available_tool_names"]
    horizon = actual["action_horizon"]
    reserve = horizon["completion_reserve"]
    assert reserve["minimum"] == {"model_calls": 1, "tool_actions": 1}
    assert reserve["with_bounded_recovery"] == {"model_calls": 1, "tool_actions": 1}
    assert "not remaining-call or action caps" in reserve["interpretation"]
    for field in ("minimum_completion_calls", "completion_budget_calls",
                  "minimum_completion_tool_actions", "completion_budget_tool_actions"):
        assert field not in horizon
    assert horizon["action_budget"] == original["action_horizon"]["action_budget"]
    assert horizon["closure_reason"] == original["action_horizon"]["closure_reason"]
    if remaining == 32:
        assert horizon["exploration_state"] == "open"
        assert horizon["model_turns_available_for_exploration"] == 31
        assert {"run_probe", "replace_text", "read_file"} <= set(actual["available_tool_names"])
    else:
        assert horizon["exploration_state"] == "closed"
        assert horizon["model_turns_available_for_exploration"] == 0
        assert set(actual["available_tool_names"]) == {"finish_task", "stop_task"}
    # Accounting and recovery retain their canonical legacy fields and exact values.
    assert original == before


def test_reservation_projection_preserves_missing_and_zero_resources_and_is_repeatable():
    original = {"remaining_budget": {"model_calls": 0}, "action_horizon": {
        "minimum_completion_calls": 0, "completion_budget_calls": 2,
        "completion_possible": False, "exploration_state": "closed",
    }}
    before = copy.deepcopy(original)
    view = compact_model_state(original, [])
    reserve = view["action_horizon"]["completion_reserve"]
    assert reserve["minimum"] == {"model_calls": 0}
    assert reserve["with_bounded_recovery"] == {"model_calls": 2}
    assert view["remaining_budget"] == {"model_calls": 0}
    assert compact_model_state(view, []) == view
    assert original == before
    assert compact_model_state({"action_horizon": {}}, []) == {"action_horizon": {}}


def test_probe_diagnostic_accepts_current_reserve_and_preserves_saved_legacy_input():
    from test_probe_first_view import frozen_request

    from diagnostics import probe_first_view

    for current in (False, True):
        request = frozen_request()
        if current:
            record = json.loads(request["input"][-1]["content"])
            horizon = record["state"]["action_horizon"]
            horizon["completion_reserve"] = {"minimum": {
                "model_calls": horizon.pop("minimum_completion_calls"),
            }}
            request["input"][-1]["content"] = canonical_json(record)
        before = copy.deepcopy(request)
        changed, _ = probe_first_view.force_probe(request)
        assert request == before
        assert changed["input"] == request["input"]
