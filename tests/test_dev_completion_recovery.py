"""One funded protocol correction, independent of the renewable protocol permission."""

from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_minimum import SingleReadAdapter
from test_dev_completion_resources import Gateway, counters
from test_dev_planning import request as mock_request
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from test_finish_reproduction_budget import snapshot
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import cost, runner, segments
from patchloop.dev.contracts import DevLimits, DevRunEnvelope, DevRunRequest
from patchloop.errors import ResumeContractMismatch

POLICY = cost.COMPLETION_RECOVERY_POLICY


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("completion recovery tests cannot dispatch network requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def funding(slots, *, output=25_000, extra=0):
    ledger = ledger_for_slots(slots)
    bounded = min(output, cost.FINALIZATION_OUTPUT_FLOOR)
    normal_path = (ledger.future_call_reservation_nanos(output_ceiling=output)
                   + (slots - 1) * ledger.future_call_reservation_nanos(output_ceiling=bounded)
                   if slots else finalization_premium(ledger, output))
    ledger.cap_nanos = (normal_path
                        + ledger.future_call_reservation_nanos(output_ceiling=output) + extra)
    return ledger


def finalization_premium(ledger, output=25_000):
    return ledger.future_call_reservation_nanos(
        output_ceiling=min(output, cost.FINALIZATION_OUTPUT_FLOOR),
    ) - ledger.future_call_reservation_nanos()


def select(gateway, ledger, *, counts=None, state=None, output=25_000, limits=None):
    return runner._tool_policy(
        gateway, counts or counters(model=40, tools=100), limits or DevLimits(),
        snapshot=state, cost_ledger=ledger, completion_cost_policy=POLICY,
        desired_output_ceiling=output,
    )


def admit(ledger, selected, *, input_tokens=60_000, output=25_000):
    details = selected.completion_cost
    return ledger.admit(
        input_tokens, desired_output_ceiling=output,
        minimum_output_ceiling=details["current_minimum_output_ceiling"],
        future_cost_reserve_nanos=details["future_cost_reserve_nanos"],
    )


@pytest.mark.parametrize("output", [128, 8_192, 25_000])
def test_one_no_action_response_preserves_full_correction_and_successor_checks(output):
    gateway = Gateway()
    ledger = funding(3, output=output)
    counts = counters(model=4, tools=3)
    before = select(gateway, ledger, counts=counts, output=output)
    assert before.allowed_tools == {"replace_text", "stop_task"}
    assert before.minimum_completion_tool_actions == 3  # No tool action for an invalid response.
    assert before.completion_cost["correction_model_calls_reserved"] == 1
    normal = admit(ledger, before, output=output)
    assert normal is not None and normal.output_ceiling == output
    ledger.settle(input_tokens=60_000, cached_input_tokens=0, output_tokens=output)
    counts.model_calls += 1
    counts.protocol_recoveries = counts.protocol_corrections_total = 1
    after = select(gateway, ledger, counts=counts, output=output)
    assert after.allowed_tools == {"replace_text", "stop_task"}
    assert after.completion_cost["correction_pending"]
    assert after.completion_cost["correction_credits_remaining"] == 0
    corrected = admit(ledger, after, output=output)
    assert corrected is not None and corrected.output_ceiling == output
    ledger.settle(input_tokens=60_000, cached_input_tokens=0, output_tokens=output)
    assert ledger.remaining_nanos == 2 * ledger.future_call_reservation_nanos(
        output_ceiling=min(output, cost.FINALIZATION_OUTPUT_FLOOR),
    )


@pytest.mark.parametrize("short", ["money", "model", "tool"])
def test_recovery_needs_a_real_call_slot_and_does_not_add_a_tool_slot(short):
    gateway = Gateway()
    ledger = funding(3, extra=-int(short == "money"))
    counts = counters(model=4-int(short == "model"), tools=3-int(short == "tool"))
    selected = select(gateway, ledger, counts=counts)
    assert not selected.completion_possible
    assert selected.allowed_tools == {"stop_task"}
    horizon = runner._completion_horizon_payload(gateway, counts, DevLimits(), selected)
    assert {"money": "cost", "model": "model_calls", "tool": "tool_actions"}[short] in (
        horizon["blocking_resources"]
    )


def test_disabled_or_spent_correction_credit_does_not_tax_later_valid_actions():
    gateway = Gateway()
    ledger = ledger_for_slots(3)
    ledger.cap_nanos = (ledger.future_call_reservation_nanos(output_ceiling=25_000)
                       + 2 * ledger.future_call_reservation_nanos(output_ceiling=8_192))
    disabled = select(gateway, ledger, limits=DevLimits(max_protocol_recoveries=0))
    spent = select(gateway, ledger, counts=counters(protocol_corrections_total=1))
    later_error = select(
        gateway, ledger, counts=counters(protocol_recoveries=1, protocol_corrections_total=2),
    )
    for selected in (disabled, spent, later_error):
        assert selected.allowed_tools == {"replace_text", "stop_task"}
        assert selected.completion_cost["correction_credits_remaining"] == 0
        assert selected.completion_cost["correction_cost_reserved_nanos"] == 0
        assert not selected.completion_cost["correction_pending"]
        assert admit(ledger, selected).output_ceiling == 25_000


def test_ready_exact_count_keeps_unused_correction_and_all_case_replay_actions():
    gateway = Gateway(("PASS",), initial=False)
    state = snapshot(gateway, case_count=4, pending_count=4)
    ledger = funding(0, extra=20_400_000)
    selected = select(gateway, ledger, counts=counters(model=2, tools=5), state=state)
    assert selected.allowed_tools == {"finish_task", "stop_task"}
    assert selected.minimum_completion_tool_actions == 5
    assert selected.completion_cost["funded_calls"] == 0
    assert selected.completion_cost["future_calls_reserved"] == 0
    full_correction = ledger.future_call_reservation_nanos(output_ceiling=25_000)
    assert selected.completion_cost["future_cost_reserve_nanos"] == full_correction
    assert admit(ledger, selected, input_tokens=26_313).output_ceiling >= 8_192
    assert admit(ledger, selected) is None
    for model, tools in [(1, 5), (2, 4)]:
        assert not select(gateway, ledger, counts=counters(model=model, tools=tools),
                          state=state).completion_possible
    pending = counters(model=1, tools=5, protocol_recoveries=1, protocol_corrections_total=1)
    correction = select(gateway, ledger, counts=pending, state=state)
    assert correction.allowed_tools == {"finish_task", "stop_task"}
    assert correction.completion_cost["future_cost_reserve_nanos"] == 0
    assert admit(ledger, correction).output_ceiling == 25_000


def paid_fixture(monkeypatch, tmp_path, *, policy=POLICY, incomplete=(1,), cap="0.60"):
    request, inputs, counts, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", incomplete_at=incomplete,
        script=SingleReadAdapter("csv-quoted-newline"),
    )
    request = request.model_copy(update={"completion_cost_policy": policy,
                                         "max_cost_usd": Decimal(cap)})
    adapter = runner.OpenAIResponsesAdapter
    count, execute = adapter.count_input_tokens_v2, adapter.execute_request
    ceilings = []

    def bound(self, payload, **kwargs):
        count(self, payload, **kwargs)
        return segments.MAX_INPUT_TOKENS

    def spend(self, payload, **kwargs):
        ceilings.append(payload["max_output_tokens"])
        return replace(execute(self, payload, **kwargs), output_tokens=payload["max_output_tokens"])

    monkeypatch.setattr(adapter, "count_input_tokens_v2", bound)
    monkeypatch.setattr(adapter, "execute_request", spend)
    return request, inputs, counts, views, ceilings


def assert_accounting(request, result):
    journal, _ = records(request)
    spent = 0
    for event in journal.events():
        row = event["payload"]
        if event["event_type"] == "provider_call_started":
            assert row["reserved_cost_nanos"] + row["completion_cost"][
                "future_cost_reserve_nanos"
            ] <= cost.usd_to_nanos(request.max_cost_usd) - spent
        elif event["event_type"] == "provider_call_finished":
            spent += row["cost_nanos"]
    assert result["cost_nanos"] == spent <= cost.usd_to_nanos(request.max_cost_usd)
    return journal


@pytest.mark.parametrize("policy", [cost.COMPLETION_MINIMUM_POLICY, POLICY])
def test_same_cap_incomplete_response_correction_has_meaningful_output_allowance(
    tmp_path, monkeypatch, policy,
):
    request, inputs, counts, views, ceilings = paid_fixture(monkeypatch, tmp_path, policy=policy)
    result = runner.run_dev(request)["runs"][0]
    # Scripted actions establish admission, not useful LLM output or repair quality.
    assert_submitted(result)
    assert inputs == counts and len(inputs) == 5
    assert views[2]["current_diff"] == views[1]["current_diff"]
    # At the shared $0.60 cap, charging every admitted output token leaves the
    # minimum policy 22,949 correction tokens; recovery preserves its full 25K.
    assert ceilings[2] == (25_000 if policy == POLICY else 22_949)
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"
    journal = assert_accounting(request, result)
    assert len([e for e in journal.events() if e["event_type"] == "protocol_correction"]) == 1
    if policy == POLICY:
        first, correction, next_action = [views[i]["remaining_budget"]["cost"][
            "completion_cost"
        ] for i in (0, 2, 3)]
        assert first["correction_credits_remaining"] == 1
        assert views[1]["remaining_budget"]["cost"]["completion_cost"][
            "current_minimum_output_ceiling"] == ceilings[1] == 25_000
        assert correction["correction_pending"]
        assert correction["current_minimum_output_ceiling"] == 25_000
        assert next_action["correction_credits_remaining"] == 0
        assert not next_action["correction_pending"]
        assert next_action["current_minimum_output_ceiling"] == 8_192


@pytest.mark.parametrize("cap", ["0.40", "0.560591"])
def test_insufficient_role_allowance_stops_before_first_provider_dispatch(
    tmp_path, monkeypatch, cap,
):
    # Five 60K inputs plus 8,192 preparation/check/finish and two 25K
    # edit/correction outputs require $0.560592 before the first dispatch.
    request, inputs, _, _, ceilings = paid_fixture(monkeypatch, tmp_path, cap=cap)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "COST_CAP_REACHED"
    assert inputs == ceilings == []
    assert result["accepted_mutations"] == result["call_counts"]["tool"] == 0
    journal = assert_accounting(request, result)
    assert result["cost_nanos"] == 0
    assert not any(event["event_type"] == "provider_call_started" for event in journal.events())


def test_valid_batch_resets_protocol_permission_without_renewing_financial_credit(
    tmp_path, monkeypatch,
):
    request, inputs, counts, views, _ = paid_fixture(
        monkeypatch, tmp_path, incomplete=(1, 3), cap="0.88",
    )
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert inputs == counts and len(inputs) == 6
    journal = assert_accounting(request, result)
    assert len([e for e in journal.events() if e["event_type"] == "protocol_correction"]) == 2
    second = views[4]["remaining_budget"]["cost"]["completion_cost"]
    assert second["correction_credits_remaining"] == 0 and not second["correction_pending"]
    assert second["current_minimum_output_ceiling"] == 8_192
    restored = runner._restore_counters(journal)
    assert restored.protocol_recoveries == 0 and restored.protocol_corrections_total == 2


def test_full_correction_can_still_be_incomplete_and_stops_without_another_retry(
    tmp_path, monkeypatch,
):
    request, inputs, counts, _, ceilings = paid_fixture(monkeypatch, tmp_path, incomplete=(1, 2))
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "INCOMPLETE_RESPONSE"
    assert inputs == counts and len(inputs) == 3
    assert ceilings[2] == 25_000
    assert result["accepted_mutations"] == 0 and result["call_counts"]["tool"] == 1
    journal = assert_accounting(request, result)
    assert len([e for e in journal.events() if e["event_type"] == "protocol_correction"]) == 1


@pytest.mark.parametrize("boundary", [
    "provider_call_finished", "turn_decision_recorded", "protocol_correction",
])
def test_known_incomplete_recovery_restores_one_credit_and_charges_each_dispatch_once(
    tmp_path, monkeypatch, boundary,
):
    request, inputs, counts, views, ceilings = paid_fixture(monkeypatch, tmp_path)
    _crash_journal_once(
        monkeypatch, event_type=boundary, when="after",
        predicate=lambda p: boundary == "protocol_correction"
        or p.get("error_code") == "incomplete_response",
    )
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    before = copy.deepcopy(journal.provider_usage())
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    for changed in [cost.DEFAULT_COMPLETION_COST_POLICY, cost.COMPLETION_RESERVE_POLICY,
                    cost.COMPLETION_MINIMUM_POLICY]:
        with pytest.raises(ResumeContractMismatch):
            runner.run_dev(resumed.model_copy(update={"completion_cost_policy": changed}))
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"max_output_tokens": 8_192}))
    result = runner.run_dev(resumed)["runs"][0]
    assert_submitted(result)
    assert inputs == counts and len(inputs) == 5 and ceilings[2] == 25_000
    assert views[2]["remaining_budget"]["cost"]["completion_cost"]["correction_pending"]
    assert journal.provider_usage()[:len(before)] == before
    journal = assert_accounting(request, result)
    assert len([e for e in journal.events() if e["event_type"] == "protocol_correction"]) == 1
    action_ids = [e["payload"]["action_id"] for e in journal.events()
                  if e["event_type"] == "action_started"]
    assert len(action_ids) == len(set(action_ids))


@pytest.mark.parametrize("boundary,terminal", [
    ("input_count_started", "COUNT_TIMEOUT_OR_UNKNOWN"),
    ("provider_call_started", "PROVIDER_TIMEOUT_OR_UNKNOWN"),
])
def test_funded_correction_does_not_retry_an_unknown_dispatch(
    tmp_path, monkeypatch, boundary, terminal,
):
    request, inputs, counts, _, _ = paid_fixture(monkeypatch, tmp_path)
    seen = 0

    def correction_request(payload):
        nonlocal seen
        seen += 1
        return seen == 3

    _crash_journal_once(monkeypatch, event_type=boundary, when="after",
                        predicate=correction_request)
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert result["terminal"] == terminal
    assert len(inputs) == 2 and len(counts) == 2 + int(boundary == "provider_call_started")
    assert len([e for e in journal.events() if e["event_type"] == "protocol_correction"]) == 1


def test_new_policy_is_opt_in_and_its_exact_contract_is_recoverable(tmp_path, monkeypatch):
    base = mock_request(tmp_path)
    assert base.context_policy == "append-v1"
    assert base.completion_cost_policy == cost.DEFAULT_COMPLETION_COST_POLICY
    with pytest.raises(ValidationError, match="requires segmented-v1"):
        DevRunRequest.model_validate({**base.model_dump(), "completion_cost_policy": POLICY})
    captures = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captures.append(request) or {})
    invocation = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
        "--context-policy", "segmented-v1", "--completion-cost-policy", POLICY,
    ])
    assert invocation.exit_code == 0, invocation.output
    actual = captures[0]
    assert actual.completion_cost_policy == POLICY
    policies = [POLICY, cost.DEFAULT_COMPLETION_COST_POLICY, cost.COMPLETION_RESERVE_POLICY,
                cost.COMPLETION_MINIMUM_POLICY]
    assert len({runner._model_hash(actual.model_copy(update={"completion_cost_policy": p}), None)
                for p in policies}) == 4


def test_new_envelope_contract_cannot_change_its_correction_allowance(tmp_path, monkeypatch):
    request, _, _, _, _ = paid_fixture(monkeypatch, tmp_path, incomplete=())
    _crash_journal_once(monkeypatch, event_type="tool_batch_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    envelope = journal.load_envelope()
    assert envelope.completion_cost_contract == cost.completion_cost_contract(POLICY)
    altered = envelope.model_dump(mode="json")
    altered["completion_cost_contract"]["correction_credits_per_run"] = 2
    with pytest.raises(ValidationError, match="exact contract"):
        DevRunEnvelope.model_validate(altered)
