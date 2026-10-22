"""Integration boundaries for minimum successful completion funding."""

from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from test_dev_budget_v16 import PolicyGateway
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_dev_planning import request as mock_request
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from test_finish_reproduction_budget import snapshot
from test_original_obligation_admission import (
    SUCCESSOR_MODELS,
    SUCCESSOR_TOOLS,
    pending_snapshot,
)
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import cost, runner, segments
from patchloop.dev.contracts import DevLimits, DevRunEnvelope, DevRunRequest
from patchloop.dev.model import MockDevAdapter
from patchloop.errors import ResumeContractMismatch

POLICY = cost.COMPLETION_MINIMUM_POLICY


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("completion-minimum tests must not send a network request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def select(gateway, ledger, *, counts=None, state=None, policy=POLICY, auto=False):
    return runner._tool_policy(
        gateway, counts or counters(model=40, tools=100), DevLimits(), snapshot=state,
        cost_ledger=ledger, completion_cost_policy=policy, repair_recheck=auto,
    )


def test_minimum_money_keeps_investigation_without_buying_speculative_recovery():
    gateway = Gateway()
    ledger = ledger_for_slots(4)
    selected = select(gateway, ledger, auto=True)
    protected = select(gateway, ledger, policy=cost.COMPLETION_RESERVE_POLICY, auto=True)
    assert {"read_file", "search_files", "run_probe", "run_check"} <= selected.allowed_tools
    assert protected.allowed_tools == {"replace_text", "stop_task"}
    assert selected.protected_completion_possible  # Physical call/action slots still fit.
    assert selected.completion_budget_calls == 7
    assert selected.completion_cost["funded_calls"] == 4
    assert selected.completion_cost["future_calls_reserved"] == 3
    assert selected.max_parallel_reads == 4
    assert selected.exploration_state == "last_opportunity"
    assert "not failure recovery" in selected.completion_cost["recovery_scope"]
    next_policy = select(gateway, ledger_for_slots(3), auto=True)
    assert set(selected.tools_closing_after_this_turn) == (
        selected.allowed_tools - next_policy.allowed_tools
    )
    assert next_policy.allowed_tools == {"replace_text", "stop_task"}
    assert not next_policy.exploration_allowed
    assert next_policy.exploration_state == "closed"
    assert next_policy.max_parallel_reads == 0
    assert next_policy.model_turns_available_for_exploration == 0
    assert next_policy.tool_actions_available_for_exploration == 0
    assert next_policy.check_ids == ()
    assert next_policy.mutation_completion_possible
    impossible = select(gateway, ledger_for_slots(2), auto=True)
    assert not impossible.completion_possible
    assert impossible.allowed_tools == {"stop_task"}
    assert not impossible.mutation_completion_possible
    assert impossible.check_ids == () and impossible.max_parallel_reads == 0
    assert impossible.completion_cost["future_calls_reserved"] == 0


def test_multiple_required_checks_remain_funded_when_optional_edit_is_too_expensive():
    gateway = PolicyGateway()
    gateway.statuses = {"first": "NOT_RUN", "second": "NOT_RUN"}
    ledger = ledger_for_slots(3)
    counts = counters(model=40, tools=100)
    for check_id, future in [("first", 2), ("second", 1), (None, 0)]:
        selected = select(gateway, ledger, counts=counts)
        expected = {"run_check", "stop_task"} if check_id else {"finish_task", "stop_task"}
        assert selected.allowed_tools == expected
        assert not selected.mutation_completion_possible
        assert selected.check_ids == tuple(gateway.remaining_visible_check_ids())
        assert selected.completion_cost["future_calls_reserved"] == future
        admission = ledger.admit(
            60_000, future_cost_reserve_nanos=selected.completion_cost["future_cost_reserve_nanos"],
        )
        assert admission is not None and admission.output_ceiling == 128
        ledger.settle(input_tokens=60_000, cached_input_tokens=0,
                      output_tokens=admission.output_ceiling)
        counts.model_calls += 1
        counts.tool_actions += 1
        if check_id:
            gateway.statuses[check_id] = "PASS"
    assert ledger.remaining_nanos == 0


@pytest.mark.parametrize("cases", [0, 4])
def test_ready_exact_count_exception_preserves_all_original_replay_tool_slots(cases):
    gateway = Gateway(("PASS",), initial=False)
    state = snapshot(gateway, case_count=cases, pending_count=cases)
    ledger = ledger_for_slots(0, extra_nanos=20_400_000)
    selected = select(gateway, ledger, counts=counters(model=1, tools=cases + 1), state=state)
    assert selected.allowed_tools == {"finish_task", "stop_task"}
    assert selected.minimum_completion_tool_actions == cases + 1
    assert selected.completion_cost["funded_calls"] == 0
    assert selected.completion_cost["admitted_call_slots"] == 1
    assert selected.completion_cost["future_cost_reserve_nanos"] == 0
    assert ledger.admit(26_313).output_ceiling >= 128
    assert ledger.admit(60_000) is None
    short = select(gateway, ledger, counts=counters(model=1, tools=cases), state=state)
    assert not short.completion_possible
    assert short.allowed_tools == {"stop_task"}


def test_original_refutation_cannot_use_ready_finish_exact_count_escape():
    gateway = Gateway(("PASS",), initial=False)
    state = snapshot(gateway, status="refuted", pending_count=0)
    selected = select(gateway, ledger_for_slots(0, extra_nanos=20_400_000), state=state)
    assert selected.workflow_gate == "needs_mutation"
    assert not selected.completion_possible
    assert selected.allowed_tools == {"stop_task"}
    horizon = runner._completion_horizon_payload(
        gateway, counters(model=40, tools=100), DevLimits(), selected, snapshot=state,
    )
    assert horizon["blocking_resources"] == ["cost"]


def test_diagnostic_check_does_not_spend_the_old_automatic_recheck_credit():
    gateway = Gateway(("FAIL", "NOT_RUN"))
    gateway.observation()
    narrow = select(gateway, ledger_for_slots(4), auto=True)
    assert narrow.minimum_completion_calls == 3  # edit, one requested check, finish
    assert "replace_text" in narrow.allowed_tools
    assert "run_check" not in narrow.allowed_tools
    assert narrow.check_ids == ()
    funded = select(gateway, ledger_for_slots(5), auto=True)
    assert "run_check" in funded.allowed_tools
    assert funded.check_ids == ("check-1",)
    # The offered check class conservatively covers retiring the auto-recheck
    # eligibility. A later edit may need both requested checks and finish.
    assert funded.completion_cost["future_calls_reserved"] == 4
    before = ledger_for_slots(5)
    admission = before.admit(
        60_000, future_cost_reserve_nanos=funded.completion_cost["future_cost_reserve_nanos"],
    )
    before.settle(input_tokens=60_000, cached_input_tokens=0,
                  output_tokens=admission.output_ceiling)
    assert before.remaining_nanos == 4 * before.future_call_reservation_nanos()


@pytest.mark.parametrize("short_resource", [None, "model", "tool"])
def test_pending_acquisition_keeps_physical_new_case_recovery_with_minimum_money(short_resource):
    gateway = Gateway()
    state = pending_snapshot(gateway)
    selected = select(
        gateway, ledger_for_slots(4), state=state,
        counts=counters(model=SUCCESSOR_MODELS + 1 - int(short_resource == "model"),
                        tools=SUCCESSOR_TOOLS + 1 - int(short_resource == "tool")),
    )
    assert ("run_probe" in selected.allowed_tools) is (short_resource is None)
    assert "replace_text" not in selected.allowed_tools
    if short_resource is None:
        assert selected.completion_cost["future_calls_reserved"] == 3
        assert selected.completion_cost["funded_calls"] < SUCCESSOR_MODELS


class SingleReadAdapter(MockDevAdapter):
    def _next_action(self, context, tools):
        turn = super()._next_action(context, tools)
        if len(turn.tool_calls) > 1:
            turn = turn.model_copy(update={
                "tool_calls": [call for call in turn.tool_calls if call.name == "read_file"],
            })
        return turn


@pytest.mark.parametrize("policy", [cost.DEFAULT_COMPLETION_COST_POLICY, POLICY])
def test_worst_case_paid_usage_fixture_funds_check_and_finish_within_same_cap(
    tmp_path, monkeypatch, policy,
):
    request, inputs, counts, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=SingleReadAdapter("csv-quoted-newline"),
    )
    request = request.model_copy(update={"completion_cost_policy": policy,
                                         "max_cost_usd": Decimal("0.30")})
    implementation = runner.OpenAIResponsesAdapter
    count, execute = implementation.count_input_tokens_v2, implementation.execute_request
    ceilings = []

    def bounded_count(self, payload, **kwargs):
        count(self, payload, **kwargs)
        return segments.MAX_INPUT_TOKENS

    def spend_ceiling(self, payload, **kwargs):
        ceilings.append(payload["max_output_tokens"])
        return replace(execute(self, payload, **kwargs), output_tokens=payload["max_output_tokens"])

    monkeypatch.setattr(implementation, "count_input_tokens_v2", bounded_count)
    monkeypatch.setattr(implementation, "execute_request", spend_ceiling)
    result = runner.run_dev(request)["runs"][0]
    assert result["cost_nanos"] <= 300_000_000
    journal, _ = records(request)
    if policy == cost.DEFAULT_COMPLETION_COST_POLICY:
        assert result["terminal"] == "COST_CAP_REACHED"
        assert result["evaluator"] is None
        assert len(inputs) == 2 and len(counts) == 3
        return
    assert_submitted(result)  # Synthetic identity deliberately cannot pass real evaluation.
    assert inputs == counts and len(inputs) == 4
    # Unlike protected funding, minimum funding also offers a diagnostic check;
    # dispatch must reserve that longer successor before the chosen action is known.
    assert 128 < ceilings[0] < 25_000 and min(ceilings) == 128
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"
    assert {"finish_task", "stop_task"} <= set(views[-1]["available_tool_names"])
    assert "replace_text" not in views[-1]["available_tool_names"]
    # The selected successful path was shorter than the largest offered path.
    # The remaining optional read is still funded when the fixture chooses finish.
    assert views[-1]["remaining_budget"]["cost"]["completion_cost"]["future_calls_reserved"] == 1
    events = journal.events()
    for event in events:
        if event["event_type"] != "provider_call_started":
            continue
        row = event["payload"]
        turn = next(e["payload"] for e in events if e["event_type"] == "turn_started"
                    and e["payload"]["turn_id"] == row["turn_id"])
        assert row["completion_cost"] == turn["completion_cost"]
        spent = sum(e["payload"]["cost_nanos"] for e in events
                    if e["event_type"] == "provider_call_finished"
                    and e["sequence"] < event["sequence"])
        assert row["reserved_cost_nanos"] + row["completion_cost"]["future_cost_reserve_nanos"] <= (
            300_000_000 - spent
        )


def test_unfunded_success_path_stops_all_repetitions_before_count_or_dispatch(
    tmp_path, monkeypatch,
):
    request, inputs, counts, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"completion_cost_policy": POLICY,
                                         "max_cost_usd": Decimal("0.01"), "repeat": 2})
    result = runner.run_dev(request)
    assert len(result["runs"]) == 1
    assert result["runs"][0]["terminal"] == "COST_CAP_REACHED"
    assert not inputs and not counts
    journal, _ = records(request)
    assert journal.terminal()["payload"]["completion_horizon"]["blocking_resources"] == ["cost"]


def test_recovery_keeps_accounting_and_rejects_policy_or_contract_changes(tmp_path, monkeypatch):
    request, inputs, counts, _ = configured(monkeypatch, tmp_path, planning="brief-v1")
    request = request.model_copy(update={"completion_cost_policy": POLICY})
    _crash_journal_once(monkeypatch, event_type="tool_batch_finished", when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    before = copy.deepcopy(journal.provider_usage())
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    for changed in [cost.DEFAULT_COMPLETION_COST_POLICY, cost.COMPLETION_RESERVE_POLICY]:
        with pytest.raises(ResumeContractMismatch):
            runner.run_dev(resumed.model_copy(update={"completion_cost_policy": changed}))
    result = runner.run_dev(resumed)["runs"][0]
    assert_submitted(result)
    assert counts == inputs and len(inputs) == 4
    assert journal.provider_usage()[:len(before)] == before
    action_ids = [e["payload"]["action_id"] for e in journal.events()
                  if e["event_type"] == "action_started"]
    assert len(action_ids) == len(set(action_ids))
    envelope = journal.load_envelope()
    assert envelope.completion_cost_policy == POLICY
    assert envelope.completion_cost_contract == cost.completion_cost_contract(POLICY)
    altered = envelope.model_dump(mode="json")
    altered["completion_cost_contract"]["future_output_tokens"] += 1
    with pytest.raises(ValidationError, match="exact contract"):
        DevRunEnvelope.model_validate(altered)


def test_cli_identity_is_opt_in_and_legacy_context_defaults_are_unchanged(tmp_path, monkeypatch):
    base = mock_request(tmp_path)
    assert base.context_policy == "append-v1"
    assert base.completion_cost_policy == cost.DEFAULT_COMPLETION_COST_POLICY
    with pytest.raises(ValidationError, match="requires segmented-v1"):
        DevRunRequest.model_validate({**base.model_dump(), "completion_cost_policy": POLICY})
    captures = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captures.append(request) or {})
    invocation = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
        "--context-policy", "segmented-v1", "--planning-policy", "brief-v1",
        "--completion-cost-policy", POLICY,
    ])
    assert invocation.exit_code == 0, invocation.output
    actual = captures[0]
    assert actual.completion_cost_policy == POLICY
    hashes = {runner._model_hash(actual.model_copy(update={"completion_cost_policy": policy}), None)
              for policy in [POLICY, cost.DEFAULT_COMPLETION_COST_POLICY,
                             cost.COMPLETION_RESERVE_POLICY]}
    assert len(hashes) == 3
