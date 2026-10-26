"""Captured target exceptions remain actionable without whole-case equality credit."""
from __future__ import annotations

import copy

import pytest
from test_completion_reproduction import observation, project
from test_completion_reproduction import original as original
from test_dev_probe_action_replay import restore
from test_dev_probes import context
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction import finish_call

from patchloop.dev import completion_reproduction, repair_context, runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.model_state import compact_model_state


def raised(trace):
    trace["incomplete"] = True
    trace["calls"][0].update(
        outcome="raised", exception={"type": "FileNotFoundError", "message": "missing input"},
        exit_code=None,
    )


def test_real_target_exception_survives_compaction_and_restart_without_replay(
    original, smoke_package, monkeypatch,
):
    gateway, journal, backend = original
    gateway.execute_batch(read_calls())
    call = mutation_call(gateway)
    call.arguments["new_text"] = (
        "def parse_rows(text):\n    raise FileNotFoundError('missing original target')")
    assert gateway.execute(call).status == "succeeded"
    runner._replay_original_cases(
        journal=journal, gateway=gateway, counters=runner._restore_counters(journal),
        active_elapsed_ms=lambda: 20, acquired_only=True,
    )
    review = project(gateway, journal)
    assert review["status"] == "unverified" and review["target_failure_count"] == 1
    assert review["pending_count"] == 0 and not review["early_replay_reusable"]
    assert review["cases"][0]["evidence"]["status"] == "UNKNOWN"
    target = review["target_failures"][0]
    assert target["exception"] == {
        "type": "builtins.FileNotFoundError", "message": "missing original target"}
    assert target["capture_status"] == "complete" and target["observation_incomplete"]
    assert not target["original_verification_credit"]
    assert review["original_failure_diagnostic"]["status"] == "available"
    state = compact_model_state(repair_context.project(context(gateway, smoke_package)), [])
    assert state["current_public_failure"]["exception"] == target["exception"]
    selected = runner._tool_policy(gateway, runner._RunCounters(), DevLimits())
    assert selected.workflow_gate == "needs_mutation"
    assert "finish_task" not in selected.allowed_tools
    # A separate regression PASS cannot erase a positive original-call failure.
    monkeypatch.setattr(gateway, "visible_checks_pass", lambda **kwargs: True)
    result = gateway.execute(finish_call())
    assert result.status == "failed" and "regression PASS cannot close" in result.message
    assert backend.calls == 2
    restarted = restore(gateway, journal, gateway.workspace, gateway.public_task, backend)
    runner._replay_original_cases(
        journal=journal, gateway=restarted, counters=runner._restore_counters(journal),
        active_elapsed_ms=lambda: 30, acquired_only=True,
    )
    assert backend.calls == 2
    assert project(restarted, journal)["target_failures"] == review["target_failures"]
    assert project(restarted, journal, diff="different-candidate")["target_failure_count"] == 0


@pytest.mark.parametrize("invalid", [
    "expected", "system_exit", "capture", "inputs", "environment", "duplicate", "timeout",
    "cleanup", "binding",
])
def test_missing_uncertain_expected_or_changed_calls_do_not_gain_repair_credit(original, invalid):
    gateway, journal, _ = original
    events = journal.events()
    row = observation(events, "raised", "D1", comparison="not_compared", change=raised)
    result = row["payload"]["result"]
    repro = result["output"]["reproduction"]
    trace = repro["call_observation"]
    call = trace["calls"][0]
    if invalid == "expected":
        call["exception_policy"] = ["FileNotFoundError"]
    elif invalid == "system_exit":
        call.update(outcome="system_exit", exception={"type": "SystemExit", "message": "20"})
    elif invalid == "capture":
        call["capture"]["status"] = "truncated"
    elif invalid == "inputs":
        call["arguments"]["args"] = ["different"]
    elif invalid == "environment":
        trace["execution_environment"]["image_digest"] = "different"
    elif invalid == "duplicate":
        trace["calls"].append(copy.deepcopy(call))
    elif invalid == "timeout":
        result["output"]["timed_out"] = True
    elif invalid == "cleanup":
        result["output"]["execution_policy"]["cleanup_status"] = "unknown"
    else:
        repro["binding"]["program_hash"] = "different"
    projected = project(gateway, journal, events=[*events, row], diff="D1")
    assert projected["target_failure_count"] == 0
    assert projected["original_failure_diagnostic"] is None


def test_positive_selected_call_failure_survives_later_pass(original):
    gateway, journal, _ = original
    events = journal.events()
    row = observation(events, "raised", "D1", comparison="not_compared", change=raised)
    events.append(row)
    current = project(gateway, journal, events=events, diff="D1")
    assert current["target_failure_count"] == 1
    assert current["cases"][0]["evidence"]["status"] == "UNKNOWN"
    assert current["cases"][0]["current"]["execution_link"]["target_outcomes"]["calls"][0][
        "unexpected_exception"]
    events.append(observation(events, "later-match", "D1"))
    after = project(gateway, journal, events=events, diff="D1")
    assert after["target_failure_count"] == 1 and after["status"] == "unverified"
    # A durable diagnostic batch start spends the same existing candidate allowance.
    row["sequence"] = max(event.get("sequence", 0) for event in events) + 1
    events.append({"sequence": row["sequence"] + 1, "event_type": "tool_batch_started",
                   "payload": {"tool_calls": [{"name": "run_probe", "action_id": "diagnose"}]}})
    restarted = completion_reproduction.review(events, "D1", run_id=journal.run_id)
    assert restarted["original_failure_diagnostic"]["status"] == "spent"
