"""Mutation-attempt forecasts include initial rejection without tightening admission."""

from __future__ import annotations

from functools import cache
from types import SimpleNamespace

import pytest

from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevToolResult


class _Gateway:
    """Pure policy state: no workspace, source reads, sandbox or provider execution."""

    def __init__(self, statuses, *, mutations=1, anchor=True, untracked=False):
        self.statuses = dict(statuses)
        self.accepted_mutations = 4 - mutations
        self.anchor = anchor
        self.public_task = SimpleNamespace(
            visible_checks=[SimpleNamespace(id=check_id) for check_id in self.statuses],
        )
        self.current_diff = SimpleNamespace(
            patch="public diff", patch_hash="current", changed_files=["source.py"],
            untracked_files=["new.py"] if untracked else [],
        )
        self.probe_sandbox = object()

    def visible_check_status(self):
        return [{"check_id": key, "status": value} for key, value in self.statuses.items()]

    def remaining_visible_check_ids(self):
        return [key for key, value in self.statuses.items() if value != "PASS"]

    def unrun_visible_check_ids(self):
        return [key for key, value in self.statuses.items() if value == "NOT_RUN"]

    def has_current_mutation_evidence(self):
        return self.anchor

    def ready_to_submit(self):
        return not self.current_diff.untracked_files and not self.remaining_visible_check_ids()


def _state(
    statuses=("PASS", "PASS"), *, model=40, tools=100, mutations=1,
    retry=True, used=(), read_used=True, anchor=True, untracked=False,
):
    gateway = _Gateway(
        {f"check-{index}": value for index, value in enumerate(statuses)},
        mutations=mutations, anchor=anchor, untracked=untracked,
    )
    counters = runner._RunCounters(
        model_calls=40 - model, tool_actions=100 - tools,
        mutation_recovery_used=not retry,
        check_recovery_used_ids=set(used), check_recovery_used=bool(used),
        failed_check_pending="FAIL" in statuses,
        failed_check_repair_read_used=read_used,
    )
    return gateway, counters


def _policy(gateway, counters):
    return runner._tool_policy(gateway, counters, DevLimits())


@cache
def _protected_steps(
    count, passed, unused, mutations, pending_mutation, anchor, read_credit, retry,
):
    """Enumerate steps/outcomes, never use the production B/P arithmetic."""
    if pending_mutation:
        assert mutations > 0
        if not anchor:
            return 1 + _protected_steps(
                count, passed, unused, mutations, True, True, False, retry,
            )
        paths = [1 + _protected_steps(
            count, 0, unused, mutations - 1, False, True, False, retry,
        )]
        if read_credit:
            paths.append(1 + _protected_steps(
                count, passed, unused, mutations, True, True, False, retry,
            ))
        if retry:
            # Rejection preserves mutation capacity but may require a fresh exact read.
            paths.append(1 + _protected_steps(
                count, passed, unused, mutations, True, False, read_credit, False,
            ))
        return max(paths)
    if passed == (1 << count) - 1:
        return 1  # Finish is an action, even for an already checked baseline.
    paths = []
    for index in range(count):
        bit = 1 << index
        if passed & bit:
            continue
        paths.append(1 + _protected_steps(
            count, passed | bit, unused, mutations, False, anchor, False, retry,
        ))
        if unused & bit and mutations:
            paths.append(1 + _protected_steps(
                count, passed, unused & ~bit, mutations, True, anchor, True, retry,
            ))
    return max(paths)


def test_mutation_attempt_forecast_matches_2728_independent_failure_paths():
    cases = 0
    mismatches = []
    try:
        for count in range(5):
            for passed in range(1 << count):
                statuses = [
                    "PASS" if passed & (1 << index) else "NOT_RUN"
                    for index in range(count)
                ]
                for unused in range(1 << count):
                    used = {
                        f"check-{index}" for index in range(count)
                        if not unused & (1 << index)
                    }
                    for mutations in range(1, 5):
                        for retry in (False, True):
                            gateway, counters = _state(
                                statuses, mutations=mutations, retry=retry, used=used,
                            )
                            policy = _policy(gateway, counters)
                            expected = _protected_steps(
                                count, passed, unused, mutations, True, True, False, retry,
                            )
                            assert policy.optional_mutation_completion_calls == count + 2
                            assert "replace_text" in policy.allowed_tools
                            if policy.optional_mutation_protected_calls != expected:
                                mismatches.append((
                                    count, passed, unused, mutations, retry,
                                    policy.optional_mutation_protected_calls, expected,
                                ))
                            cases += 1
        assert cases == 2728
        assert not mismatches, (len(mismatches), mismatches[:5])
    finally:
        _protected_steps.cache_clear()


@pytest.mark.parametrize("statuses", [("PASS", "PASS"), ("FAIL", "NOT_RUN")])
@pytest.mark.parametrize("model,tools", [(4, 100), (5, 100), (6, 100), (40, 4), (40, 5), (40, 6)])
def test_last_mutation_reserves_initial_rejection_without_hiding_edit(statuses, model, tools):
    gateway, counters = _state(statuses, model=model, tools=tools)
    policy = _policy(gateway, counters)
    horizon = runner._mutation_completion_horizon(policy)
    assert policy.minimum_completion_calls == (4 if "FAIL" in statuses else 1)
    assert policy.completion_budget_calls == (6 if "FAIL" in statuses else 1)
    assert horizon["minimum_calls"] == 4
    assert horizon["protected_calls"] == 6
    assert horizon["minimum_possible"] is True
    assert "replace_text" in policy.allowed_tools
    protected = min(model, tools) >= 6
    assert horizon["protected_possible"] is protected
    assert bool(horizon["recovery_warning"]) is not protected


@pytest.mark.parametrize("mutations", [1, 2, 4])
def test_no_unused_check_allowance_still_protects_initial_rejection(mutations):
    gateway, counters = _state(
        mutations=mutations, used={"check-0", "check-1"}, model=5,
    )
    policy = _policy(gateway, counters)
    assert policy.future_check_failure_slots == 0
    assert policy.optional_mutation_protected_calls == 6
    assert policy.mutation_completion_possible
    assert not policy.mutation_protected_completion_possible


def test_consumed_rejection_allowance_is_not_reserved_again():
    gateway, counters = _state(model=4, retry=False)
    policy = _policy(gateway, counters)
    assert policy.optional_mutation_completion_calls == 4
    assert policy.optional_mutation_protected_calls == 4
    assert policy.mutation_protected_completion_possible
    assert runner._mutation_completion_horizon(policy)["recovery_warning"] is None


@pytest.mark.parametrize("mutations,protected", [(2, 10), (4, 14)])
def test_initial_and_future_rejections_share_one_allowance(mutations, protected):
    gateway, counters = _state(mutations=mutations, model=protected)
    policy = _policy(gateway, counters)
    assert policy.optional_mutation_protected_calls == protected
    assert policy.mutation_protected_completion_possible


def test_immediate_mutation_does_not_reserve_the_optional_read_before_it():
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=6, read_used=False)
    policy = _policy(gateway, counters)
    assert policy.completion_budget_calls == 7
    assert not policy.protected_completion_possible
    assert policy.optional_mutation_protected_calls == 6
    assert policy.mutation_protected_completion_possible


@pytest.mark.parametrize("overrides,expected", [
    ({"model": 4}, {"finish_task", "replace_text", "read_file", "search_files", "run_probe"}),
    ({"model": 3}, {"finish_task", "read_file", "search_files", "run_probe"}),
    ({"statuses": ("FAIL", "NOT_RUN"), "model": 4}, {"replace_text"}),
    ({"statuses": ("FAIL", "NOT_RUN"), "model": 6}, {"replace_text"}),
    ({"statuses": ("NOT_RUN", "NOT_RUN"), "model": 4}, {"replace_text", "run_check"}),
    ({"statuses": ("NOT_RUN", "NOT_RUN"), "model": 6}, {"replace_text", "run_check"}),
    ({"statuses": ("NOT_RUN", "NOT_RUN"), "model": 10}, {
        "replace_text", "run_check", "read_file", "search_files", "run_probe",
    }),
    ({"mutations": 0}, {"finish_task", "read_file", "search_files", "run_probe"}),
    ({"anchor": False}, {"finish_task", "read_file", "search_files", "run_probe"}),
    ({"untracked": True}, set()),
    ({"statuses": ("FAIL", "NOT_RUN"), "mutations": 0}, set()),
])
def test_forecast_fix_preserves_existing_action_admission(overrides, expected):
    gateway, counters = _state(**overrides)
    policy = _policy(gateway, counters)
    assert policy.allowed_tools == expected | {"stop_task"}


def _consume(counters, tool, *, succeeded=True, output=None):
    counters.model_calls += 1
    counters.tool_actions += 1
    runner._update_inspection_counters(counters, [DevToolResult(
        action_id=f"step-{counters.model_calls}", input_hash="sha256:" + "0" * 64,
        tool=tool, status="succeeded" if succeeded else "failed", output=output or {},
    )])


def test_minimum_only_attempt_exhausts_horizon_after_rejection_without_new_admission():
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=4)
    before = _policy(gateway, counters)
    assert before.mutation_completion_possible
    assert not before.mutation_protected_completion_possible
    _consume(counters, "replace_text", succeeded=False)
    after = _policy(gateway, counters)
    assert after.minimum_completion_calls == 4
    assert not after.completion_possible
    assert after.allowed_tools == {"stop_task"}


def test_six_call_protected_path_survives_rejection_read_edit_checks_and_finish():
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=6)
    before = _policy(gateway, counters)
    assert before.optional_mutation_protected_calls == 6
    _consume(counters, "replace_text", succeeded=False)
    after_rejection = _policy(gateway, counters)
    assert after_rejection.completion_budget_calls == 4
    assert {"replace_text", "read_file"} <= after_rejection.allowed_tools
    _consume(counters, "read_file", output={"new_span_count": 0})
    assert "replace_text" in _policy(gateway, counters).allowed_tools
    _consume(counters, "replace_text")
    gateway.accepted_mutations += 1
    gateway.statuses = dict.fromkeys(gateway.statuses, "NOT_RUN")
    for check_id in gateway.statuses:
        policy = _policy(gateway, counters)
        assert "run_check" in policy.allowed_tools
        assert check_id in policy.check_ids
        _consume(counters, "run_check", output={"check_id": check_id, "passed": True})
        gateway.statuses[check_id] = "PASS"
    assert _policy(gateway, counters).allowed_tools == {"finish_task", "stop_task"}
    _consume(counters, "finish_task")
    assert counters.model_calls == 40
