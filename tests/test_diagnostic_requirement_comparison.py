"""Diagnostic re-projection preserves current public comparison evidence."""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from test_dev_history_search import items as history_items
from test_requirement_comparison import CURRENT, ISSUE, helper, put, scoped
from test_size_only_replay import saved as saved

from diagnostics import history_search_replay, size_only_replay, verification_role
from patchloop.dev import history_search, working_plan
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.util import canonical_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("diagnostic comparison tests must not contact a provider")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.mark.parametrize("phase", ["initial", "verify"])
def test_verification_role_retains_helper_but_respects_phase_plan_boundary(tmp_path, phase):
    journal = DevJournal(tmp_path, "run_dev_diagnosticcomparison")
    gateway = SimpleNamespace(journal=journal, current_diff_hash=CURRENT)
    controller = verification_role.VerificationRun(gateway, "B")
    controller.request = SimpleNamespace(planning_policy="brief-v1")
    controller.remaining = lambda: {}
    put(journal, "initial", plan="PRIOR_PHASE_PLAN")
    helper(journal)
    put(journal, "helper-reviewed", scope=scoped())
    initial = working_plan.project(journal.events(), diff_hash=CURRENT,
                                   gate="needs_mutation", public_issue=ISSUE)
    assert initial["review_request"]["requirement_comparison"]["status"] == "review_recorded"
    if phase == "verify":
        journal.append(verification_role.PHASE_EVENT, {"phase": "verify", "stream": "verifier"})
        controller.phase, controller.stream = "verify", "verifier"
    state = {"public_task": {"issue": ISSUE}, "working_plan": initial,
             "workflow_gate": "needs_mutation", "working_notes": {}, "latest_tool_results": []}
    actual = json.loads(controller.context(canonical_json(state)))
    comparison = actual["working_plan"]["review_request"]["requirement_comparison"]
    assert comparison["action_id"] == "helper"
    assert comparison["task_reference"] == initial["review_request"][
        "requirement_comparison"]["task_reference"]
    if phase == "initial":
        assert comparison["status"] == "review_recorded"
    else:
        # The independent verifier receives observations, not the prior phase's judgment.
        assert actual["working_plan"]["plan"] is None
        assert comparison["status"] == "review_needed"
        assert "PRIOR_PHASE_PLAN" not in canonical_json(actual)


@pytest.fixture
def pending_turn(saved, tmp_path):
    turn = copy.deepcopy(saved[1])
    journal = DevJournal(tmp_path, "run_dev_diagnostichelper")
    result = helper(journal, diff=turn.state["current_diff"]["patch_hash"])
    offset = max(e["sequence"] for e in turn.prefix)
    turn.prefix.extend({**event, "sequence": offset + event["sequence"]}
                       for event in journal.events())
    turn.state["working_plan"] = working_plan.project(
        turn.prefix, diff_hash=turn.state["current_diff"]["patch_hash"],
        gate=turn.state["workflow_gate"], public_issue=turn.state["public_task"]["issue"],
    )
    turn.state["recent_probes"] = [{"action_id": result["action_id"],
                                   "diff_hash": result["workspace_diff_hash"],
                                   "historical": False, "stdout": result["output"]["stdout"]}]
    return turn


@pytest.mark.parametrize("fresh", [False, True])
def test_size_replay_keeps_pending_comparison_in_reconstructed_input(pending_turn, fresh):
    turn = pending_turn
    expected = turn.state["working_plan"]["review_request"]["requirement_comparison"]
    handoff = {**turn.handoff, "review_requested": fresh}
    items = size_only_replay.compose(
        turn, copy.deepcopy(turn.wire["input"]), handoff,
        base=turn.base, replay_boundary=turn.sequence if fresh else None,
    )
    actual = reconstruct_state(items, context_policy="segmented-v1")
    assert actual["working_plan"]["review_request"]["requirement_comparison"] == expected
    assert actual["working_plan"]["review_request"]["requested"]
    assert actual["recent_probes"][0]["action_id"] == expected["action_id"]


def test_history_search_replay_keeps_pending_comparison_in_reconstructed_input(pending_turn):
    turn = pending_turn
    turn.usage["input_tokens"] = 20_000
    estimator = size_only_replay.TokenEstimator(lambda text: list(text[::4]), {}, [turn])
    history = history_search.PublicHistory()
    history.ingest(history_items(observation={"caller": "read_rows", "input": "quoted newline"}),
                   sequence=1, turn_id="earlier-public-input", input_hash="earlier-input")
    history.ingest(history_items(), sequence=2,
                   turn_id="later-public-input", input_hash="later-input")
    result = history.search("read_rows", current_diff_hash="different")
    assert result["records"]
    expected = turn.state["working_plan"]["review_request"]["requirement_comparison"]
    packed, items = history_search_replay.pack_result(turn, result, estimator)
    assert packed["fits_known_content"]
    actual = reconstruct_state(items, context_policy="segmented-v1")
    assert actual["working_plan"]["review_request"]["requirement_comparison"] == expected
    assert actual["working_plan"]["review_request"]["requested"]
    assert actual["recent_probes"][0]["action_id"] == expected["action_id"]
