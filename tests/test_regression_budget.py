"""Bound revision opportunities and reserve verification without external execution."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_exception_frame_repair import no_external, stop_call  # noqa: F401
from test_feedback_repair_cycle import setup
from test_first_edit_checkpoint import evidence

from diagnostics import first_edit_checkpoint as d
from diagnostics.checkpoint_continuation import ScriptedClient
from diagnostics.repair_cycle_budget import regression_opportunity
from patchloop.deadline import ExecutionDeadline
from patchloop.dev.cost import DevCostLedger, pricing_for_model
from patchloop.util import sha256_json


def opportunity(*, original=None, regression=None, initial=False,
                normal=3, tools=4, edits=1):
    return regression_opportunity(
        original_feedback=original, regression_feedback=regression, initial=initial,
        normal_remaining=normal, tool_remaining=tools, edits_remaining=edits,
        probes_remaining=0, original_remaining=0, limits=d.LIMITS)


def test_first_edit_keeps_three_successors_without_opening_exploration():
    first = opportunity(initial=True, normal=4, tools=5, edits=2)
    assert first.allowed == {"replace_text", "stop_task"}
    assert first.max_parallel_reads == 0
    assert first.continuation_reserved
    assert first.successor_calls == 3
    assert first.successor_output_ceilings == (8_192, 40_000, 8_192)


@pytest.mark.parametrize("original,regression", [
    ("failed", "passed"), ("supported", "failed"),
])
def test_either_public_failure_reopens_one_bounded_diagnostic_then_edit(original, regression):
    feedback = {"original": {"status": original}, "regression": {"status": regression}}
    failed = opportunity(**feedback)
    assert failed.allowed == {"read_file", "search_files", "replace_text", "stop_task"}
    assert failed.max_parallel_reads == 2
    assert failed.successor_output_ceilings == (40_000, 8_192)
    assert not failed.continuation_reserved
    # One response can read twice, preserving one edit action and its final response.
    after_reads = opportunity(**feedback, normal=2, tools=2)
    assert after_reads.allowed == {"replace_text", "stop_task"}
    assert after_reads.max_parallel_reads == 0
    assert after_reads.successor_output_ceilings == (8_192,)


def test_all_public_checks_passing_releases_revision_and_successor_reserves():
    passed = opportunity(original={"status": "supported"}, regression={"status": "passed"})
    assert passed.allowed == {"stop_task"}
    assert passed.max_parallel_reads == passed.successor_calls == 0
    assert not passed.continuation_reserved


@pytest.mark.parametrize("resource", ["cost", "time"])
def test_unfunded_verification_prevents_an_unchecked_mutation(
    gateway_factory, tmp_path, monkeypatch, resource,
):
    gateway, journal, loaded, cycle, baseline = setup(
        gateway_factory, tmp_path, monkeypatch, limits=d.LIMITS)
    # 800 seconds funds the immediate checks but not both possible edits' checks.
    gateway.deadline = ExecutionDeadline.from_remaining(800 if resource == "time" else 1_200)
    loaded.common = evidence()
    before = gateway.current_diff_hash
    regression = SimpleNamespace(
        needed_seconds=lambda **_: 300, host_actions=0,
        check=lambda: pytest.fail("no unchecked mutation may reach regression execution"))
    client = ScriptedClient([[stop_call()]])
    adapter = d.loop.OpenAIResponsesAdapter(d.loop.config(), api_key="", client=client)
    group = DevCostLedger(Decimal("0.16" if resource == "cost" else "1.20"),
                          pricing_for_model(d.loop.MODEL))
    actual = d.loop.run_model(loaded, "A", gateway, adapter, group,
        first_hash=sha256_json(d.request_payload(loaded.common, "A")), profile=d.PROFILE,
        request_builder=d.request_payload, cycle=cycle, regression=regression)
    assert actual["new_mutations"] == actual["host_original_actions"] == 0
    assert actual["host_regression_actions"] == baseline.dispatches == 0
    assert actual["candidate_diff_hash"] == before == gateway.current_diff_hash
    assert actual["billing_known"] and not actual["stop_remaining"]
    if resource == "time":
        assert actual["terminal"] == "RECHECK_TIME_UNAVAILABLE"
        assert not client.counted and not client.created
    else:
        assert actual["terminal"] == "AGENT_STOPPED" and len(client.created) == 1
        assert {tool["name"] for tool in client.created[0]["tools"]} == {"stop_task"}
        assert any(e["event_type"] == "opportunity_cost_narrowed" for e in journal.events())
        assert [e["payload"]["tool"] for e in journal.events()
                if e["event_type"] == "action_started"] == ["stop_task"]
        assert group.spent_nanos <= group.cap_nanos


def test_pinned_cap_covers_all_full_responses_without_cached_input_credit():
    ledger = DevCostLedger(d.PROFILE.row_cap, pricing_for_model(d.loop.MODEL))
    maximum = (d.PROFILE.normal_calls * ledger.future_call_reservation_nanos(
        output_ceiling=d.loop.NORMAL_OUTPUT)
        + ledger.future_call_reservation_nanos(output_ceiling=d.loop.CORRECTION_OUTPUT))
    assert maximum == 1_057_500_000 < ledger.cap_nanos
