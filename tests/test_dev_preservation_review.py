"""Candidate-bound intent delivery, not semantic coverage or model-quality proof."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _read, _restart
from test_dev_verification_flow_v17 import _completed_check

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter
from patchloop.dev.model_state import compact_model_state
from patchloop.dev.state import DevJournal
from patchloop.runtime import repository_root


@pytest.mark.parametrize("final_check", [False, True])
def test_check_retains_bounded_accepted_intent_after_rejected_proposal_and_restart(
    tmp_path, final_check,
):
    gateway = _gateway(tmp_path)
    gateway.public_task.visible_checks = [SimpleNamespace(id="behavior")]
    if not final_check:
        gateway.public_task.visible_checks.append(SimpleNamespace(id="other"))
    _read(gateway)
    accepted = _mutation("accepted")
    # The gateway retains literal model intent, even a maximum-sized claim that
    # the synthetic check does not establish; it never emits a coverage verdict.
    accepted.arguments["expected_behavior"] = "Unverified preservation claim. ".ljust(1500, "x")
    assert len(accepted.arguments["expected_behavior"]) == 1500
    changed = gateway.execute(accepted)
    assert changed.status == "succeeded"
    rejected = _mutation("rejected", old="ABSENT_ANCHOR")
    rejected.arguments["expected_behavior"] = "Rejected intent must never replace accepted intent."
    assert gateway.execute(rejected).status == "failed"
    checked = _completed_check(gateway, "checked")
    card = runner._attempt_card(checked, gateway)
    expected = card["mutation_expectation"]
    assert expected == {
        "plan_hash": changed.output["mutation"]["plan_hash"],
        "diff_hash": checked.workspace_diff_hash,
        "expected_behavior": accepted.arguments["expected_behavior"],
        "interpretation_status": "model_authored_unverified",
        "scope": "at_check_completion",
    }
    before = gateway.journal.path.read_bytes()
    restored = _restart(gateway)
    assert runner._attempt_card(checked, restored) == card
    assert restored.journal.path.read_bytes() == before
    assert restored.ready_to_submit() is final_check


def test_later_mutation_cannot_be_bound_to_an_older_check_or_rewrite_its_card(tmp_path):
    gateway = _gateway(tmp_path)
    _read(gateway)
    assert gateway.execute(_mutation("first")).status == "succeeded"
    old_check = _completed_check(gateway, "old-check")
    card = runner._attempt_card(old_check, gateway)
    gateway.journal.append("attempt_card", card)
    frozen_card = json.dumps(card, sort_keys=True)
    second = _mutation("second", old="editable = 1", new="editable = 2")
    second.arguments["expected_behavior"] = "A second, distinct candidate expectation."
    assert gateway.execute(second).status == "succeeded"
    assert "mutation_expectation" not in runner._attempt_card(old_check, gateway)
    assert json.dumps(card, sort_keys=True) == frozen_card
    saved = next(e["payload"] for e in _restart(gateway).journal.events()
                 if e["event_type"] == "attempt_card")
    assert saved == card
    current_check = _completed_check(gateway, "new-check")
    assert runner._attempt_card(current_check, gateway)["mutation_expectation"][
        "expected_behavior"
    ] == second.arguments["expected_behavior"]


@pytest.mark.parametrize("condition", ["baseline", "failed_check", "unknown_diff", "wrong_diff"])
def test_only_a_pass_on_the_same_candidate_gets_an_expectation(tmp_path, condition):
    gateway = _gateway(tmp_path)
    if condition != "baseline":
        _read(gateway)
        assert gateway.execute(_mutation("edit")).status == "succeeded"
    checked = _completed_check(gateway, "check", passed=condition != "failed_check")
    if condition in {"unknown_diff", "wrong_diff"}:
        checked.workspace_diff_hash = None if condition == "unknown_diff" else "different-diff"
    assert "mutation_expectation" not in runner._attempt_card(checked, gateway)


def test_compact_view_keeps_only_latest_current_review_and_protocol_without_rewriting():
    old = {"action_id": "old", "mutation_expectation": {"diff_hash": "old-diff"}}
    first = {"action_id": "first", "mutation_expectation": {"diff_hash": "current-diff"}}
    latest = {"action_id": "latest", "mutation_expectation": {"diff_hash": "current-diff"}}
    protocol = {"attempt": "protocol"}
    state = {"current_diff": {"patch_hash": "current-diff"},
             "recent_attempt_result_next_question": [old, first, latest, protocol]}
    before = json.dumps(state)
    view = compact_model_state(state, [])
    assert view["recent_attempt_result_next_question"] == [latest, protocol]
    assert json.dumps(state) == before
    state["current_diff"]["patch_hash"] = "next-diff"
    assert compact_model_state(state, [])["recent_attempt_result_next_question"] == [protocol]


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_actual_mock_inputs_deliver_check_time_intent_without_an_extra_step(
    tmp_path, monkeypatch, context_policy,
):
    expectation = (
        "Trigger: a newline in the input. Scope: only a quoted newline belongs inside a field. "
        "Change: a quoted newline remains inside one CSV field. "
        "Preserve: the same newline outside quotes still separates records. "
        "These outcomes are expected, not observed proof."
    )

    class PreservationMock(MockDevAdapter):
        def next_turn(self, context, tools):
            turn = super().next_turn(context, tools)
            for call in turn.tool_calls:
                if call.name == "replace_text":
                    call.arguments["expected_behavior"] = expectation
            return turn

    def no_network(*args, **kwargs):
        pytest.fail("mock intent delivery must not dispatch a provider request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_network)
    monkeypatch.setattr(runner, "MockDevAdapter", PreservationMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy, planning_policy="brief-v1",
    )
    run = runner.run_dev(request)["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["evaluator"]["claim_eligible"] is False
    journal = DevJournal(tmp_path, run["run_id"])
    store = ArtifactStore(tmp_path / "artifacts")
    turns = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"]
    inputs = [
        runner._load_active_model_input(turn, store, context_policy=context_policy)
        for turn in turns
    ]
    # The interpretation guidance is present before the first inspection and after
    # the existing segment transitions, without adding a tool or scripted step.
    assert all(items[0]["content"].startswith(DEV_SYSTEM_PROMPT) for items in inputs)
    assert "same trigger outside that scope" in inputs[0][0]["content"]
    assert "justify their match or keep it uncertain" in inputs[0][0]["content"]
    assert "If no boundary is supported, say so" in inputs[0][0]["content"]
    states = [reconstruct_state(items, context_policy=context_policy) for items in inputs]
    assert states[0]["current_diff"]["patch"] == ""
    assert states[0]["last_successful_mutation"] is None
    final = states[-1]
    review = next(card for card in final["recent_attempt_result_next_question"]
                  if "mutation_expectation" in card)
    assert review["mutation_expectation"]["expected_behavior"] == expectation
    assert review["mutation_expectation"]["diff_hash"] == final["current_diff"]["patch_hash"]
    assert review["mutation_expectation"]["interpretation_status"] == "model_authored_unverified"
    assert final["public_task"] == states[0]["public_task"]
    assert final["visible_check_status"][0]["status"] == "PASS"
    assert "finish_task" in final["available_tool_names"]
    assert "review" in review["next_question"].lower()
    if context_policy == "segmented-v1":
        assert any(e["event_type"] == "context_segment_started" for e in journal.events())
