from __future__ import annotations

import copy
import itertools
import json
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from test_dev_budget_v16 import PolicyGateway
from test_dev_planning import request as mock_request
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segment_boundary import RepairAdapter
from test_dev_segments import assert_submitted, configured, records
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import cost, runner, segments
from patchloop.dev.contracts import DevLimits, DevRunEnvelope, DevRunRequest
from patchloop.dev.model import MockDevAdapter
from patchloop.errors import ResumeContractMismatch

POLICY = cost.COMPLETION_RESERVE_POLICY


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("completion cost tests must not dispatch a real provider request")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def ledger_for_slots(slots, *, extra_nanos=0):
    ledger = cost.DevCostLedger(Decimal("10"), cost.pricing_for_model("gpt-5.4-mini-2026-03-17"))
    ledger.cap_nanos = max(1, slots * ledger.future_call_reservation_nanos() + extra_nanos)
    return ledger


def funded_policy(gateway, ledger, counters=None, limits=None, **kwargs):
    return runner._tool_policy(
        gateway, counters or runner._RunCounters(), limits or DevLimits(),
        cost_ledger=ledger, completion_cost_policy=POLICY, **kwargs,
    )


@pytest.mark.parametrize("model,unit", [
    ("gpt-5.4-mini-2026-03-17", 45_576_000),
    ("gpt-5.4-2026-03-05", 151_920_000),
])
def test_reservation_survives_worst_case_spend_and_cache_only_returns_real_savings(model, unit):
    ledger = cost.DevCostLedger(Decimal("1.20"), cost.pricing_for_model(model))
    assert ledger.future_call_reservation_nanos() == unit
    reserve = 3 * unit
    admission = ledger.admit(60_000, future_cost_reserve_nanos=reserve)
    assert admission is not None
    assert admission.reserved_cost_nanos + reserve <= ledger.remaining_nanos
    assert ledger.spent_nanos == 0  # Reservation is not a charge.
    charged = ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                            output_tokens=admission.output_ceiling)
    assert charged == admission.reserved_cost_nanos
    assert ledger.remaining_nanos >= reserve
    discounted = cost.DevCostLedger(Decimal("1.20"), ledger.pricing)
    discounted.settle(input_tokens=60_000, cached_input_tokens=60_000,
                      output_tokens=admission.output_ceiling)
    assert discounted.remaining_nanos > ledger.remaining_nanos
    ledger.restore_settled_usage([{"cost_nanos": charged}])
    assert ledger.remaining_nanos >= reserve


def test_output_floor_reserve_and_one_nanodollar_boundary():
    ledger = ledger_for_slots(2)
    unit = ledger.future_call_reservation_nanos()
    admission = ledger.admit(60_000, future_cost_reserve_nanos=unit)
    assert admission.output_ceiling == 128
    ledger.cap_nanos -= 1
    assert ledger.admit(60_000, future_cost_reserve_nanos=unit) is None
    assert ledger.admit(60_000) is not None  # Default still admits this current call.
    with pytest.raises(ValueError, match="negative"):
        ledger.admit(1, future_cost_reserve_nanos=-1)


def test_two_checks_then_finish_retain_a_funded_successor():
    gateway = PolicyGateway()
    gateway.statuses = {"first": "NOT_RUN", "second": "NOT_RUN"}
    ledger = ledger_for_slots(3)
    for check_id, future_calls in [("first", 2), ("second", 1), (None, 0)]:
        policy = funded_policy(gateway, ledger)
        expected_tools = {"run_check", "stop_task"} if check_id else {"finish_task", "stop_task"}
        assert policy.allowed_tools == expected_tools
        assert policy.completion_cost["future_calls_reserved"] == future_calls
        admission = ledger.admit(
            60_000, future_cost_reserve_nanos=policy.completion_cost["future_cost_reserve_nanos"],
        )
        assert admission is not None
        ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                      output_tokens=admission.output_ceiling)
        if check_id:
            gateway.statuses[check_id] = "PASS"
    assert ledger.remaining_nanos == 0


def test_optional_read_probe_and_edit_cannot_spend_the_finish_slot():
    gateway = PolicyGateway()
    ledger = ledger_for_slots(2)
    policy = funded_policy(gateway, ledger)
    assert {"read_file", "search_files", "run_probe", "finish_task"} <= policy.allowed_tools
    assert "replace_text" not in policy.allowed_tools
    assert policy.completion_cost["future_calls_reserved"] == 1
    assert {"read_file", "search_files", "run_probe"} <= set(policy.tools_closing_after_this_turn)
    admission = ledger.admit(
        60_000, future_cost_reserve_nanos=policy.completion_cost["future_cost_reserve_nanos"],
    )
    ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                  output_tokens=admission.output_ceiling)
    assert funded_policy(gateway, ledger).allowed_tools == {"finish_task", "stop_task"}


def test_ready_exact_count_can_use_less_than_the_future_input_bound():
    ledger = ledger_for_slots(0, extra_nanos=20_400_000)
    policy = funded_policy(PolicyGateway(), ledger)
    assert policy.completion_cost["funded_calls"] == 0
    assert policy.completion_cost["admitted_call_slots"] == 1
    assert policy.completion_cost["future_cost_reserve_nanos"] == 0
    assert policy.allowed_tools == {"finish_task", "stop_task"}
    assert ledger.admit(26_313).output_ceiling >= 128
    assert ledger.admit(60_000) is None


def test_current_failure_still_requires_repair_and_does_not_release_finish_money():
    gateway = PolicyGateway()
    gateway.statuses["first"] = "FAIL"
    policy = funded_policy(gateway, ledger_for_slots(4))
    assert policy.allowed_tools == {"replace_text", "stop_task"}
    assert policy.completion_cost["future_calls_reserved"] == 3
    impossible = funded_policy(gateway, ledger_for_slots(3))
    assert not impossible.completion_possible
    detail = runner._completion_horizon_payload(
        gateway, runner._RunCounters(), DevLimits(), impossible,
    )
    assert detail["blocking_resources"] == ["cost"]


def test_offered_actions_always_leave_an_affordable_successor_at_input_bound():
    stages = [("PASS", "PASS"), ("NOT_RUN", "NOT_RUN"), ("FAIL", "PASS"), ("FAIL", "NOT_RUN")]
    for statuses, anchor, accepted, slots, model_left in itertools.product(
        stages, [False, True], [0, 1, 3, 4], [1, 2, 3, 4, 5, 8, 16, 30], [3, 40],
    ):
        gateway = PolicyGateway()
        gateway.statuses = dict(zip(gateway.statuses, statuses, strict=True))
        gateway.anchor, gateway.accepted_mutations = anchor, accepted
        ledger = ledger_for_slots(slots)
        counters = runner._RunCounters(model_calls=40 - model_left, failed_check_pending=True)
        policy = funded_policy(gateway, ledger, counters)
        if not policy.completion_possible:
            continue
        reserve = policy.completion_cost["future_cost_reserve_nanos"]
        admission = ledger.admit(60_000, future_cost_reserve_nanos=reserve)
        assert admission is not None, (statuses, anchor, accepted, slots, model_left, policy)
        assert admission.reserved_cost_nanos + reserve <= ledger.remaining_nanos


@pytest.mark.parametrize("context", ["append-v1", "native-window-v1"])
def test_invalid_context_is_rejected_before_run(tmp_path, context):
    with pytest.raises(ValidationError, match="completion-cost-policy"):
        DevRunRequest.model_validate({**mock_request(tmp_path).model_dump(),
                                      "context_policy": context, "completion_cost_policy": POLICY})


def test_cli_and_default_identity(tmp_path, monkeypatch):
    base = mock_request(tmp_path).model_copy(update={"context_policy": segments.POLICY})
    explicit = base.model_copy(update={"completion_cost_policy": "per-call-v1"})
    assert runner._model_hash(base, None) == runner._model_hash(explicit, None)
    captures = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captures.append(request) or {})
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
        "--context-policy", "segmented-v1", "--planning-policy", "brief-v1",
        "--completion-cost-policy", POLICY,
    ])
    assert result.exit_code == 0, result.output
    assert captures[0].completion_cost_policy == POLICY
    assert runner._model_hash(captures[0], None) != runner._model_hash(base, None)
    gateway = PolicyGateway()
    original = runner._tool_policy(gateway, runner._RunCounters(), base.limits)
    assert runner._tool_policy(gateway, runner._RunCounters(), base.limits,
                               cost_ledger=ledger_for_slots(1)) == original


def test_actual_count_dispatch_and_recovery_keep_reserve_and_public_state(tmp_path, monkeypatch):
    request, inputs, counts, views = configured(monkeypatch, tmp_path, planning="brief-v1")
    request = request.model_copy(update={"completion_cost_policy": POLICY})
    _crash_journal_once(monkeypatch, event_type="tool_batch_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    before = copy.deepcopy(journal.provider_usage())
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"completion_cost_policy": "per-call-v1"}))
    result = runner.run_dev(resumed)["runs"][0]
    assert_submitted(result)
    assert counts == inputs
    assert journal.provider_usage()[:len(before)] == before
    assert all(view["public_task"] and view["current_diff"] is not None for view in views)
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"
    assert views[-1]["completion_guidance"]["submission_ready"]
    for event in journal.events():
        if event["event_type"] == "provider_call_started":
            row = event["payload"]
            turn = next(e["payload"] for e in journal.events()
                        if e["event_type"] == "turn_started"
                        and e["payload"]["turn_id"] == row["turn_id"])
            assert row["completion_cost"] == turn["completion_cost"]
            prior_cost = sum(e["payload"]["cost_nanos"] for e in journal.events()
                             if e["event_type"] == "provider_call_finished"
                             and e["sequence"] < event["sequence"])
            reserved = row["completion_cost"]["future_cost_reserve_nanos"]
            assert row["reserved_cost_nanos"] + reserved <= (
                journal.load_envelope().max_cost_nanos - prior_cost
            )
    envelope = journal.load_envelope()
    assert envelope.completion_cost_contract == cost.completion_cost_contract()
    altered = envelope.model_dump(mode="json")
    altered["completion_cost_contract"]["future_output_tokens"] += 1
    with pytest.raises(ValidationError, match="exact contract"):
        DevRunEnvelope.model_validate(altered)


@pytest.mark.parametrize("policy", [cost.DEFAULT_COMPLETION_COST_POLICY, POLICY])
def test_expensive_responses_leave_check_and_finish_requests_funded(tmp_path, monkeypatch, policy):
    class SingleReadAdapter(MockDevAdapter):
        def _next_action(self, context, tools):
            turn = super()._next_action(context, tools)
            if len(turn.tool_calls) > 1:
                turn = turn.model_copy(update={
                    "tool_calls": [c for c in turn.tool_calls if c.name == "read_file"],
                })
            return turn

    request, inputs, counts, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=SingleReadAdapter("csv-quoted-newline"),
    )
    request = request.model_copy(update={"completion_cost_policy": policy,
                                         "max_cost_usd": Decimal("0.30")})
    implementation = runner.OpenAIResponsesAdapter
    count = implementation.count_input_tokens_v2
    execute = implementation.execute_request
    ceilings = []

    def bounded_count(self, payload, **kwargs):
        count(self, payload, **kwargs)
        return segments.MAX_INPUT_TOKENS

    def spend_ceiling(self, payload, **kwargs):
        ceilings.append(payload["max_output_tokens"])
        result = execute(self, payload, **kwargs)
        return replace(result, output_tokens=payload["max_output_tokens"])

    monkeypatch.setattr(implementation, "count_input_tokens_v2", bounded_count)
    monkeypatch.setattr(implementation, "execute_request", spend_ceiling)
    result = runner.run_dev(request)["runs"][0]
    if policy == cost.DEFAULT_COMPLETION_COST_POLICY:
        assert result["terminal"] == "COST_CAP_REACHED"
        assert result["evaluator"] is None
        assert len(inputs) == 2 and len(counts) == 3
        assert ceilings == [25_000, 21_666]
        return
    assert_submitted(result)
    assert inputs == counts and len(inputs) == 4
    assert ceilings[0] == 25_000 and min(ceilings) == 128
    assert result["cost_nanos"] <= 300_000_000
    assert views[-1]["available_tool_names"] == ["finish_task", "stop_task"]
    assert views[-1]["remaining_budget"]["cost"]["completion_cost"]["future_calls_reserved"] == 0


def test_failed_check_read_repair_and_recheck_keep_existing_recovery_rules(tmp_path, monkeypatch):
    request, inputs, counts, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=RepairAdapter("csv-quoted-newline"),
    )
    request = request.model_copy(update={"completion_cost_policy": POLICY, "repair_recheck": True})
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 2
    assert counts == inputs
    failures = [view for view in views if view["current_public_failure"]]
    assert len(failures) == 2
    assert all("replace_text" in view["available_tool_names"] for view in failures)
    assert all("finish_task" not in view["available_tool_names"] for view in failures)
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"


def test_unfunded_completion_stops_before_count_or_generation(tmp_path, monkeypatch):
    request, inputs, counts, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"completion_cost_policy": POLICY,
                                         "max_cost_usd": Decimal("0.01"), "repeat": 2})
    result = runner.run_dev(request)
    assert len(result["runs"]) == 1
    assert result["runs"][0]["terminal"] == "COST_CAP_REACHED"
    assert not inputs and not counts
    journal, _ = records(request)
    assert journal.terminal()["payload"]["completion_horizon"]["blocking_resources"] == ["cost"]


@pytest.mark.parametrize("boundary,terminal", [
    ("input_count_started", "COUNT_TIMEOUT_OR_UNKNOWN"),
    ("provider_call_started", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
])
def test_unknown_dispatch_still_stops_without_retry(tmp_path, monkeypatch, boundary, terminal):
    request, inputs, counts, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"completion_cost_policy": POLICY})
    _crash_journal_once(monkeypatch, event_type=boundary, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert result["terminal"] == terminal
    assert not inputs and len(counts) == (boundary == "provider_call_started")


@pytest.mark.parametrize("policy", [cost.DEFAULT_COMPLETION_COST_POLICY, POLICY])
def test_mock_smoke_reaches_isolated_evaluation_and_preserves_old_envelope(tmp_path, policy):
    request = mock_request(tmp_path).model_copy(update={
        "context_policy": segments.POLICY, "completion_cost_policy": policy,
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    journal, _ = records(request)
    raw = json.loads(journal.envelope_path.read_bytes())
    assert ("completion_cost_policy" in raw) is (policy == POLICY)
    assert ("completion_cost_contract" in raw) is (policy == POLICY)
    assert DevRunEnvelope.model_validate(raw).model_dump(mode="json") == raw
