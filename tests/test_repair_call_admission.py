"""Correction time admission and safe transport evidence, without external calls."""

from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import common, no_external, stop_call  # noqa: F401
from test_feedback_repair_cycle import setup

from diagnostics import exception_frame_repair as loop
from diagnostics import feedback_source as feedback
from diagnostics.checkpoint_continuation import ScriptedClient
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.util import sha256_json


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


def exercise(gateway_factory, tmp_path, monkeypatch, *, usable_seconds=6.0,
             correction_count_seconds=0.0, cycle_enabled=True, failure_phase=None,
             exception=None, minimum_correction_seconds=30.0):
    gateway, journal, loaded, cycle, _ = setup(gateway_factory, tmp_path, monkeypatch)
    clock = Clock()
    gateway.deadline = ExecutionDeadline.from_remaining(600, clock=clock)
    monkeypatch.setattr(loop, "monotonic", clock)
    # Known 60s caller execution plus the existing 5s reserve, with no actual probes.
    monkeypatch.setattr(cycle, "needed_original_seconds", lambda **_: 60.0)
    if cycle_enabled:
        arm, profile, builder = "R1", feedback.PROFILE, feedback.request_payload
        reserve = 65.0
    else:
        gateway.agent_policy = "current"
        arm, profile, builder = "B", loop.DEFAULT_PROFILE, loop.request_payload
        loaded = SimpleNamespace(common=common(gateway.public_task))
        cycle, reserve = None, 0.0
    client = ScriptedClient([[], [stop_call()]])
    adapter = loop.OpenAIResponsesAdapter(loop.config(), api_key="", client=client)
    original_count, original_execute = adapter.count_input_tokens_v2, adapter.execute_request
    counts, generations = [], []

    def count(payload, *, timeout_seconds):
        counts.append(timeout_seconds)
        if failure_phase == "input_count":
            clock.now += 1.25
            raise exception
        result = original_count(payload, timeout_seconds=timeout_seconds)
        if len(counts) > 1:
            clock.now += correction_count_seconds
        return result

    def execute(payload, *, requested_input_tokens, timeout_seconds):
        generations.append(timeout_seconds)
        if failure_phase == "generation":
            clock.now += 2.5
            raise exception
        result = original_execute(payload, requested_input_tokens=requested_input_tokens,
                                  timeout_seconds=timeout_seconds)
        if len(generations) == 1:
            clock.now = 600 - reserve - usable_seconds
        return result

    monkeypatch.setattr(adapter, "count_input_tokens_v2", count)
    monkeypatch.setattr(adapter, "execute_request", execute)
    result = loop.run_model(loaded, arm, gateway, adapter,
        DevCostLedger(Decimal("2.40"), pricing_for_model(loop.MODEL)),
        first_hash=sha256_json(builder(loaded.common, arm, profile=profile)),
        profile=profile, request_builder=builder, cycle=cycle,
        minimum_correction_seconds=minimum_correction_seconds)
    return result, journal.events(), counts, generations


def payloads(events, kind):
    return [event["payload"] for event in events if event["event_type"] == kind]


@pytest.mark.parametrize("usable_seconds", [6.0, -1.0])
def test_short_correction_is_rejected_before_count_or_generation(
    gateway_factory, tmp_path, monkeypatch, usable_seconds,
):
    result, events, counts, generations = exercise(gateway_factory, tmp_path, monkeypatch,
                                                  usable_seconds=usable_seconds)
    assert result["terminal"] == "CORRECTION_TIME_UNAVAILABLE"
    assert result["billing_known"] and not result["stop_remaining"]
    assert result["normal_calls"] == 1 and result["correction_calls"] == 0
    assert counts == generations == [535.0]
    rejection = payloads(events, "correction_time_unavailable")[-1]
    assert rejection == {"phase": "before_count", "timeout_s": usable_seconds,
                         "minimum_correction_seconds": 30.0,
                         "original_recheck_reserve_s": 65.0}
    assert not payloads(events, "repair_cycle_time_reserved")


@pytest.mark.parametrize("floor", [30.0, 45.0])
def test_exact_configured_floor_is_admitted_without_shortening_normal_timeout(
    gateway_factory, tmp_path, monkeypatch, floor,
):
    result, events, counts, generations = exercise(gateway_factory, tmp_path, monkeypatch,
        usable_seconds=floor, minimum_correction_seconds=floor)
    assert result["terminal"] == "AGENT_STOPPED" and result["correction_calls"] == 1
    assert counts == generations == [535.0, floor]
    assert not payloads(events, "correction_time_unavailable")
    starts = payloads(events, "provider_call_started")
    finishes = payloads(events, "provider_call_finished")
    assert starts[-1]["timeout_s"] == floor and starts[-1]["phase"] == "generation"
    assert finishes[-1]["timeout_s"] == floor and finishes[-1]["elapsed_s"] == 0
    assert finishes[-1]["request_hash"] == starts[-1]["request_hash"]


def test_counting_can_consume_correction_time_without_spending_dispatch_credit(
    gateway_factory, tmp_path, monkeypatch,
):
    result, events, counts, generations = exercise(gateway_factory, tmp_path, monkeypatch,
        usable_seconds=30.0, correction_count_seconds=1.0)
    assert result["terminal"] == "CORRECTION_TIME_UNAVAILABLE"
    assert result["correction_calls"] == 0 and result["normal_calls"] == 1
    assert counts == [535.0, 30.0] and generations == [535.0]
    rejection = payloads(events, "correction_time_unavailable")[-1]
    assert rejection["phase"] == "before_generation" and rejection["timeout_s"] == 29.0
    assert rejection["original_recheck_reserve_s"] == 65.0
    count_finish = payloads(events, "input_count_finished")[-1]
    assert count_finish["elapsed_s"] == 1.0 and count_finish["timeout_s"] == 30.0
    assert rejection["count_id"] == count_finish["count_id"]
    assert rejection["request_hash"] == count_finish["request_hash"]
    assert len(payloads(events, "provider_call_started")) == 1


def test_cost_narrowing_cannot_release_original_check_time_for_correction(
    gateway_factory, tmp_path, monkeypatch,
):
    admit = DevCostLedger.admit

    def no_correction_successors(book, input_tokens, **options):
        if (options["desired_output_ceiling"] == loop.CORRECTION_OUTPUT
                and options["future_cost_reserve_nanos"]):
            return None
        return admit(book, input_tokens, **options)

    monkeypatch.setattr(DevCostLedger, "admit", no_correction_successors)
    result, events, counts, generations = exercise(gateway_factory, tmp_path, monkeypatch,
                                                  usable_seconds=30.0)
    assert result["terminal"] == "AGENT_STOPPED" and result["correction_calls"] == 1
    narrowed = payloads(events, "opportunity_cost_narrowed")
    assert narrowed and "replace_text" not in narrowed[-1]["after"]["allowed_tools"]
    assert len(counts) > 2 and set(counts[1:]) == {30.0}
    assert generations == [535.0, 30.0]  # The retained 65s never becomes model time.


@pytest.mark.parametrize("phase,event_type,error_class,duration", [
    ("input_count", "input_count_failed", "TimeoutError", 1.25),
    ("generation", "provider_usage_unknown", "RuntimeError", 2.5),
    ("generation", "provider_usage_unknown", "OtherException", 2.5),
])
def test_request_exception_records_safe_identity_and_stops_all_work(
    gateway_factory, tmp_path, monkeypatch, phase, event_type, error_class, duration,
):
    secret = "SECRET_API_KEY_MUST_NOT_BE_LOGGED"
    exception_type = {"TimeoutError": TimeoutError, "RuntimeError": RuntimeError}.get(
        error_class, type(secret, (Exception,), {}))
    result, events, counts, generations = exercise(gateway_factory, tmp_path, monkeypatch,
        failure_phase=phase, exception=exception_type(secret))
    assert result["terminal"] == ("COUNT_UNCERTAIN" if phase == "input_count"
                                   else "PROVIDER_UNCERTAIN")
    assert result["stop_remaining"] and not result["billing_known"]
    assert len(counts) == 1 and len(generations) == int(phase == "generation")
    failure = payloads(events, event_type)[-1]
    assert failure["error_class"] == error_class and failure["phase"] == phase
    assert failure["timeout_s"] == 535.0 and failure["elapsed_s"] == duration
    assert failure["usage_unknown"] and failure["request_hash"].startswith("sha256:")
    assert failure["count_id"] == payloads(events, "input_count_started")[0]["count_id"]
    if phase == "generation":
        assert failure["call_id"] == payloads(events, "provider_call_started")[0]["call_id"]
    assert secret not in json.dumps(events) and secret not in json.dumps(result)
    assert not payloads(events, "provider_call_finished")


def test_legacy_path_keeps_short_correction_admission(gateway_factory, tmp_path, monkeypatch):
    result, events, counts, generations = exercise(gateway_factory, tmp_path, monkeypatch,
                                                  cycle_enabled=False)
    assert result["terminal"] == "AGENT_STOPPED" and result["correction_calls"] == 1
    assert counts == generations == [600.0, 6.0]
    assert not payloads(events, "correction_time_unavailable")
