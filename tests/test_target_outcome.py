"""Captured target exceptions remain actionable without whole-case equality credit."""
from __future__ import annotations

import copy

import pytest
from test_completion_reproduction import observation, project
from test_completion_reproduction import original as original
from test_dev_probe_action_replay import restore
from test_dev_probe_cases import TEXT, ExecutingProbe
from test_dev_probes import context
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction import finish_call
from test_probe_purpose import SOURCE, probe

from patchloop.dev import completion_reproduction, repair_context, runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.model_state import compact_model_state


def raised(trace):
    trace["incomplete"] = True
    trace["calls"][0].update(
        outcome="raised", exception={"type": "FileNotFoundError", "message": "missing input"},
        exit_code=None,
    )


@pytest.mark.parametrize("helper_raises", [False, True], ids=["helper-passed", "helper-failed"])
def test_real_target_exception_survives_compaction_and_restart_without_replay(
    gateway_factory, smoke_package, monkeypatch, helper_raises,
):
    gateway, journal, _ = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    source = (
        f"call = observed_target()({TEXT!r})\n"
        "if call.exception is not None:\n"
        "    raise RuntimeError('helper after target exception')\n"
        "record_observation(call.value)\n"
    ) if helper_raises else SOURCE
    baseline = gateway.execute(probe(gateway.public_task, source=source))
    assert baseline.output["status"] == "passed" and baseline.output["exit_code"] == 0
    assert baseline.output["reproduction"]["declared_failure_comparison"] == "matched"
    gateway.execute_batch(read_calls())
    call = mutation_call(gateway)
    call.arguments["new_text"] = (
        "def parse_rows(text):\n    raise FileNotFoundError('missing original target')")
    assert gateway.execute(call).status == "succeeded"
    runner._replay_original_cases(
        journal=journal, gateway=gateway, counters=runner._restore_counters(journal),
        active_elapsed_ms=lambda: 20, acquired_only=True,
    )
    output = next(event["payload"]["result"]["output"] for event in reversed(journal.events())
                  if event["event_type"] == "action_finished"
                  and event["payload"]["result"]["tool"] == "run_probe")
    assert (output["status"], output["exit_code"]) == (
        ("failed", 1) if helper_raises else ("passed", 0))
    assert backend.sources[0] == backend.sources[1]
    if helper_raises:
        assert "RuntimeError: helper after target exception" in output["stderr"]
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


@pytest.mark.parametrize("phase", ["before-target", "after-return"])
def test_helper_failure_without_a_target_exception_remains_unverified(gateway_factory, phase):
    gateway, journal, _ = gateway_factory()
    backend = gateway.probe_sandbox = ExecutingProbe()
    fault = (
        "if csvlite.parse_rows.__doc__ == 'helper failure':\n"
        "    raise RuntimeError('helper only')\n"
    )
    source = "from mini_data_utils import csvlite\n"
    source += fault if phase == "before-target" else ""
    source += f"call = observed_target()({TEXT!r})\n"
    source += fault if phase == "after-return" else ""
    source += "record_observation(call.value)\n"
    baseline = gateway.execute(probe(gateway.public_task, source=source))
    assert baseline.output["reproduction"]["declared_failure_comparison"] == "matched"
    gateway.execute_batch(read_calls())
    call = mutation_call(gateway)
    call.arguments["new_text"] = (
        "def parse_rows(text):\n    '''helper failure'''\n    return []\n")
    assert gateway.execute(call).status == "succeeded"
    runner._replay_original_cases(
        journal=journal, gateway=gateway, counters=runner._restore_counters(journal),
        active_elapsed_ms=lambda: 20, acquired_only=True,
    )
    result = next(event["payload"]["result"] for event in reversed(journal.events())
                  if event["event_type"] == "action_finished"
                  and event["payload"]["result"]["tool"] == "run_probe")
    output = result["output"]
    assert result["status"] == "succeeded"
    assert (output["status"], output["exit_code"]) == ("failed", 1)
    calls = output["reproduction"]["call_observation"]["calls"]
    assert len(calls) == (0 if phase == "before-target" else 1)
    if calls:
        assert calls[0]["outcome"] == "returned" and calls[0]["exception"] is None
        assert calls[0]["capture"]["status"] == "complete"
    projected = project(gateway, journal)
    assert projected["status"] == "unverified" and projected["target_failure_count"] == 0
    assert projected["cases"][0]["evidence"]["status"] == "UNKNOWN"
    assert projected["original_failure_diagnostic"] is None
    assert backend.sources[0] == backend.sources[1] and backend.calls == 2


@pytest.mark.parametrize("invalid", [
    "expected", "system_exit", "capture", "inputs", "environment", "duplicate", "timed_out",
    "cleanup", "binding", "setup", "truncated", "deadline_exhausted", "missing_exit",
    "inconsistent_exit", "unsettled_status", "action_failure",
])
def test_missing_uncertain_expected_or_changed_calls_do_not_gain_repair_credit(original, invalid):
    gateway, journal, _ = original
    events = journal.events()
    row = observation(events, "raised", "D1", comparison="not_compared", change=raised)
    result = row["payload"]["result"]
    result["output"].update(status="failed", exit_code=1)
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
    elif invalid in {"timed_out", "truncated", "deadline_exhausted"}:
        result["output"][invalid] = True
    elif invalid == "cleanup":
        result["output"]["execution_policy"]["cleanup_status"] = "unknown"
    elif invalid == "binding":
        repro["binding"]["program_hash"] = "different"
    elif invalid == "setup":
        result["output"]["setup_checks"] = {"status": "failed"}
    elif invalid == "missing_exit":
        result["output"]["exit_code"] = None
    elif invalid == "inconsistent_exit":
        result["output"]["exit_code"] = 0
    elif invalid == "unsettled_status":
        result["output"]["status"] = "output_limit"
    elif invalid == "action_failure":
        result["status"] = "failed"
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
