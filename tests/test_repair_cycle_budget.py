"""Future repair opportunities without provider, filesystem or target execution."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from diagnostics.repair_cycle_budget import CycleLimits, cycle_opportunity
from patchloop.dev.cost import DevCostLedger, pricing_for_model


def opportunity(**changes):
    return cycle_opportunity(**{
        "normal_remaining": 16, "tool_remaining": 24,
        "probes_remaining": 2, "edits_remaining": 3, **changes,
    })


def test_nonfinal_edit_funds_diagnosis_repair_and_feedback_without_raising_ceilings():
    selected = opportunity()
    assert selected.allowed == {
        "read_file", "search_files", "run_probe", "replace_text", "stop_task",
    }
    assert selected.successor_output_ceilings == (8192, 8192, 128)
    assert selected.successor_calls == 3 and selected.continuation_reserved
    assert selected.max_parallel_reads == 4
    book = DevCostLedger(Decimal("1.20"), pricing_for_model("gpt-5.4-mini-2026-03-17"))
    reserved = sum(book.future_call_reservation_nanos(output_ceiling=value)
                   for value in selected.successor_output_ceilings)
    reserved += book.future_call_reservation_nanos(output_ceiling=25_000)
    admitted = book.admit(60_000, desired_output_ceiling=40_000,
                          future_cost_reserve_nanos=reserved)
    assert admitted is not None and admitted.output_ceiling == 40_000
    assert book.spent_nanos == 0  # Reservations are not billed usage.


@pytest.mark.parametrize("changes", [{"normal_remaining": 1}, {"tool_remaining": 1},
                                      {"edits_remaining": 0}])
def test_last_response_action_or_exhausted_edits_cannot_create_unreported_edit(changes):
    selected = opportunity(**changes)
    assert selected.allowed == {"stop_task"}
    assert selected.successor_calls == 0


def test_last_edit_keeps_feedback_response_and_does_not_reserve_another_repair():
    selected = opportunity(normal_remaining=2, tool_remaining=2, edits_remaining=1)
    assert selected.allowed == {"replace_text", "stop_task"}
    assert selected.successor_output_ceilings == (128,)
    assert not selected.continuation_reserved


def test_inspection_batch_preserves_edit_and_final_actions():
    selected = opportunity(normal_remaining=3, tool_remaining=5)
    assert selected.max_parallel_reads == 3
    assert selected.successor_output_ceilings == (8192, 128)
    assert not selected.continuation_reserved


def test_cost_narrowing_releases_optional_work_but_not_post_edit_feedback():
    broad = opportunity()
    without_continuation = opportunity(allow_continuation=False)
    without_inspection = opportunity(allow_continuation=False, allow_inspection=False)
    edit_only = opportunity(allow_continuation=False, allow_inspection=False, allow_probe=False)
    assert broad.successor_output_ceilings == (8192, 8192, 128)
    assert without_continuation.successor_output_ceilings == (8192, 128)
    assert without_inspection.allowed == {"run_probe", "replace_text", "stop_task"}
    assert edit_only.allowed == {"replace_text", "stop_task"}
    assert edit_only.successor_output_ceilings == (128,)


def test_correction_uses_available_response_without_renewing_probe_or_edit_quotas():
    last = opportunity(normal_remaining=0, correction=True, probes_remaining=0)
    assert last.allowed == {"stop_task"}
    repaired_request = opportunity(normal_remaining=1, correction=True, probes_remaining=0)
    assert repaired_request.allowed == {"replace_text", "stop_task"}
    assert opportunity(correction=True, probes_remaining=0).allowed.isdisjoint({"run_probe"})
    assert opportunity(correction=True, edits_remaining=0).allowed == {"stop_task"}


@pytest.mark.parametrize("changes", [{"normal_remaining": 0}, {"tool_remaining": 0}])
def test_exhausted_budget_offers_no_action(changes):
    assert opportunity(**changes).allowed == frozenset()


def test_host_replay_and_final_verification_are_separate_from_model_probe_quota():
    limits = CycleLimits()
    assert limits.host_original_actions == 4 and limits.helper_probes == 2
    assert limits.final_public_actions == 11
    assert limits.final_public_seconds == limits.acceptance_seconds == 390
    assert replace(limits, accepted_edits=1).host_original_actions == 2
