"""Final decision delivery and fixed-cap admission, with no live model claims."""
from __future__ import annotations

import copy
import json

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records

from patchloop.dev import cost, runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.mutation_tools import MUTATION_TOOLS


def choose(gateway, ledger, counts, ceiling=40_000):
    return runner._tool_policy(
        gateway, counts, DevLimits(), cost_ledger=ledger,
        completion_cost_policy=cost.COMPLETION_RECOVERY_POLICY,
        desired_output_ceiling=ceiling, max_correction_output_tokens=25_000,
    )


def test_finalization_floor_survives_successor_spend_under_same_cap():
    gateway = Gateway()
    ledger = ledger_for_slots(3)
    premium = ledger.future_call_reservation_nanos(output_ceiling=8_192) - (
        ledger.future_call_reservation_nanos())
    ledger.cap_nanos = sum(ledger.future_call_reservation_nanos(output_ceiling=ceiling)
                           for ceiling in (40_000, 8_192, 8_192))
    cap = ledger.cap_nanos
    counts = counters(model=3, tools=3, protocol_corrections_total=1)
    ceilings = []
    for step in range(3):
        policy = choose(gateway, ledger, counts)
        details = policy.completion_cost
        assert details["future_calls_reserved"] == 2 - step
        assert details["finalization_cost_reserved_nanos"] == (premium if step < 2 else 0)
        admitted = ledger.admit(
            60_000, desired_output_ceiling=40_000,
            minimum_output_ceiling=details["current_minimum_output_ceiling"],
            future_cost_reserve_nanos=details["future_cost_reserve_nanos"],
        )
        assert admitted is not None
        ceilings.append(admitted.output_ceiling)
        ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                      output_tokens=admitted.output_ceiling)
        counts.model_calls += 1
        counts.tool_actions += 1
        if step == 0:
            gateway.current_diff.patch = "current candidate"
            gateway.current_diff.changed_files = ["src.py"]
            gateway.accepted_mutations += 1
        if step == 1:
            gateway.statuses = {"check-0": "PASS"}
    assert ceilings == [40_000, 8_192, 8_192]
    assert ledger.spent_nanos == cap and ledger.remaining_nanos == 0


def test_exact_count_ready_floor_clips_to_configured_ceiling_and_blocks_insufficient_money():
    gateway = Gateway(("PASS",), initial=False)
    counts = counters(model=1, tools=1, protocol_corrections_total=1)
    ledger = ledger_for_slots(0, extra_nanos=40_000_000)
    policy = choose(gateway, ledger, counts)
    assert policy.allowed_tools == {"finish_task", "stop_task"}
    details = policy.completion_cost
    assert details["future_cost_reserve_nanos"] == 0
    assert ledger.admit(4_000, minimum_output_ceiling=details[
        "current_minimum_output_ceiling"]) is not None
    assert ledger.admit(10_000, minimum_output_ceiling=details[
        "current_minimum_output_ceiling"]) is None
    assert choose(gateway, ledger, counts, ceiling=256).completion_cost[
        "current_minimum_output_ceiling"] == 256


@pytest.mark.parametrize("resume", [False, True])
@pytest.mark.parametrize("repair_available", [False, True])
def test_finalization_and_correction_preserve_only_offered_repair_source(
    tmp_path, monkeypatch, resume, repair_available,
):
    request, inputs, counted, views = configured(monkeypatch, tmp_path, incomplete_at=(3,))
    request = request.model_copy(update={"limits": request.limits.model_copy(update={
        "max_accepted_mutations": 3 if repair_available else 1,
    })})
    raw_ready, count_payloads, dispatch_payloads = [], [], []
    build = runner._build_context
    adapter = runner.OpenAIResponsesAdapter
    count, dispatch = adapter.count_input_tokens_v2, adapter.execute_request

    def capture_context(**kwargs):
        context = build(**kwargs)
        state = json.loads(context)
        if state["workflow_gate"] == "ready_to_submit":
            raw_ready.append(state)
        return context

    def capture_count(self, payload, **kwargs):
        count_payloads.append(copy.deepcopy(payload))
        return count(self, payload, **kwargs)

    def capture_dispatch(self, payload, **kwargs):
        dispatch_payloads.append(copy.deepcopy(payload))
        return dispatch(self, payload, **kwargs)

    monkeypatch.setattr(runner, "_build_context", capture_context)
    monkeypatch.setattr(adapter, "count_input_tokens_v2", capture_count)
    monkeypatch.setattr(adapter, "execute_request", capture_dispatch)
    if resume:
        _crash_journal_once(monkeypatch, event_type="context_segment_started", when="after",
                            predicate=lambda p: p["reason"] == "completion_no_action")
        with pytest.raises(_SimulatedCrash):
            runner.run_dev(request)
        journal, _ = records(request)
        request = request.model_copy(update={"resume_run_id": journal.run_id})
    assert_submitted(runner.run_dev(request)["runs"][0])
    assert inputs == counted and count_payloads == dispatch_payloads
    ready = [view for view in views if view["workflow_gate"] == "ready_to_submit"]
    assert len(ready) == 2
    assert [view["segment_handoff"]["reason"] for view in ready] == [
        "completion_stage_entered", "completion_no_action"]
    assert all(view["completion_stage"]["active"] for view in ready)
    assert raw_ready[0]["source_spans"]  # Selected current evidence exists in both controls.
    selected = [{key: span[key] for key in (
        "path", "file_hash", "start_line", "end_line", "content",
    )} for span in raw_ready[0]["source_spans"]]
    for view in ready:
        assert bool(MUTATION_TOOLS.intersection(view["available_tool_names"])) == repair_available
        assert not view.get("recent_probes")
        source = view["completion_stage"]["source_retrieval"]
        assert source["source_bodies_delivered"] == repair_available
        if repair_available:
            delivered = [{"path": group["path"], "file_hash": group["file_hash"], **span}
                         for group in view["current_sources"]
                         for span in group.get("inline_spans", [])]
            assert delivered == selected
            assert view["context_projection"]["retained_content_limit"] == (
                request.retained_source_chars
            )
        else:
            assert not view.get("current_sources") and "context_projection" not in view
    assert ready[0]["current_diff"] == ready[1]["current_diff"]
    assert ready[1]["visible_check_status"][0]["status"] == "PASS"
    assert ready[1]["protocol_correction"]["completion_correction"]["fresh_segment"]
    assert not any(item.get("type") in {"reasoning", "function_call_output"}
                   for item in inputs[-1])
    journal, _ = records(request)
    actions = [event["payload"]["result"]["tool"] for event in journal.events()
               if event["event_type"] == "action_finished"]
    assert actions.count("read_file") == actions.count("replace_text") == 1
    assert actions[-3:] == ["replace_text", "run_check", "finish_task"]
