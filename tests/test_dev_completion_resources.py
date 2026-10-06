"""Model/tool completion horizons account for harness-owned registered rechecks."""

from dataclasses import asdict, replace
from functools import cache
from types import SimpleNamespace

import pytest
from test_dev_completion_cost import ledger_for_slots

from patchloop.dev import runner
from patchloop.dev.completion_budget import CompletionState, completion_budget
from patchloop.dev.contracts import DevLimits, DevToolResult
from patchloop.dev.cost import COMPLETION_RESERVE_POLICY
from patchloop.dev.model_state import compact_model_state


class Gateway:
    def __init__(self, statuses=("NOT_RUN",), *, initial=True, mutations=4, anchor=True):
        self.statuses = {f"check-{i}": value for i, value in enumerate(statuses)}
        self.accepted_mutations = 4 - mutations
        self.anchor = anchor
        self.current_diff = SimpleNamespace(
            patch="" if initial else "public diff", patch_hash="candidate",
            changed_files=[] if initial else ["src.py"], untracked_files=[],
        )
        self.public_task = SimpleNamespace(
            visible_checks=[SimpleNamespace(id=key) for key in self.statuses],
            test_suites=[object()],
        )
        self.probe_sandbox = object()
        self.events = []
        self.journal = SimpleNamespace(events=lambda: self.events)

    def visible_check_status(self):
        return [{"check_id": key, "status": value} for key, value in self.statuses.items()]

    def remaining_visible_check_ids(self):
        return [key for key, value in self.statuses.items() if value != "PASS"]

    def unrun_visible_check_ids(self):
        return [key for key, value in self.statuses.items() if value == "NOT_RUN"]

    def has_current_mutation_evidence(self):
        return self.anchor

    def ready_to_submit(self):
        return bool(self.current_diff.patch) and not self.remaining_visible_check_ids()

    def observation(self, **output):
        result = DevToolResult(
            action_id=f"observed-{len(self.events)}", input_hash="sha256:" + "0" * 64,
            tool="run_check", status="succeeded", workspace_diff_hash="candidate",
            output={"check_id": "check-0", "diff_hash": "candidate", "passed": False, **output},
        )
        self.events.append({"sequence": len(self.events), "event_type": "action_finished",
                            "payload": {"result": result.model_dump(mode="json")}})
        return result


def counters(model=8, tools=58, **kwargs):
    return runner._RunCounters(model_calls=40-model, tool_actions=100-tools, **kwargs)


def policy(gateway, counts=None, *, auto=True, **kwargs):
    return runner._tool_policy(
        gateway, counts or counters(), DevLimits(), repair_recheck=auto, **kwargs,
    )


def test_eight_model_calls_preserve_seven_model_eight_tool_path_with_one_more_read():
    gateway = Gateway()
    enabled = policy(gateway)
    assert (enabled.minimum_completion_calls, enabled.minimum_completion_tool_actions) == (3, 3)
    assert (enabled.completion_budget_calls, enabled.completion_budget_tool_actions) == (7, 8)
    assert enabled.exploration_state == "last_opportunity"
    assert enabled.model_turns_available_for_exploration == 1
    assert enabled.max_parallel_reads == 4
    assert {"read_file", "search_files", "run_probe", "run_tests", "run_check"} <= (
        enabled.allowed_tools
    )
    assert policy(gateway, auto=False).allowed_tools == {"replace_text", "stop_task"}
    after = policy(gateway, counters(model=7, tools=57))
    assert after.allowed_tools == {"replace_text", "stop_task"}
    assert set(enabled.tools_closing_after_this_turn) == enabled.allowed_tools - after.allowed_tools


@pytest.mark.parametrize("tools", [7, 8])
def test_automatic_recheck_never_releases_tool_reservations(tools):
    selected = policy(Gateway(), counters(tools=tools))
    assert selected.allowed_tools == {"replace_text", "stop_task"}
    assert selected.completion_budget_tool_actions == 8
    assert selected.protected_completion_possible is (tools == 8)


def test_pass_reopens_observation_but_optional_edit_keeps_its_separate_failure_path():
    selected = policy(Gateway(("PASS",), initial=False, mutations=3), counters(model=6))
    assert selected.minimum_completion_calls == selected.completion_budget_calls == 1
    assert selected.minimum_completion_tool_actions == selected.completion_budget_tool_actions == 1
    assert {"finish_task", "run_probe", "run_tests", "read_file"} <= selected.allowed_tools
    assert selected.model_turns_available_for_exploration == 5
    assert runner._mutation_completion_horizon(selected) == {
        "minimum_calls": 3, "protected_calls": 7,
        "minimum_tool_actions": 3, "protected_tool_actions": 8,
        "minimum_possible": True, "protected_possible": False,
        "recovery_warning": "An edit, all checks, and finish fit if the edit succeeds; "
        "full failure-recovery reserves do not fit.",
    }


@pytest.mark.parametrize("output,eligible", [
    ({}, True), ({"diff_hash": "old"}, False), ({"check_id": "unregistered"}, False),
    ({"passed": True}, False), ({"deadline_exhausted": True}, False),
    ({"cleanup_failed": True}, False),
])
def test_current_recheck_credit_uses_same_bound_healthy_registered_failure(output, eligible):
    gateway = Gateway(("FAIL",), initial=False, mutations=3)
    gateway.observation(**output)
    counts = counters(model=3, check_recovery_used_ids={"check-0"}, check_recovery_used=True)
    selected = policy(gateway, counts)
    assert selected.minimum_completion_calls == (2 if eligible else 3)
    assert selected.minimum_completion_tool_actions == 3
    assert selected.completion_budget_calls == (4 if eligible else 5)
    assert selected.completion_budget_tool_actions == 5
    assert policy(gateway, counts, auto=False).minimum_completion_calls == 3
    assert selected.optional_mutation_completion_calls == (2 if eligible else 3)


def test_later_pass_replaces_failure_and_multicheck_repair_saves_only_one_current_call():
    gateway = Gateway(("FAIL", "NOT_RUN", "PASS"), initial=False, mutations=3)
    gateway.observation()
    selected = policy(gateway)
    assert selected.minimum_completion_calls == 4
    assert selected.minimum_completion_tool_actions == 5
    gateway.observation(passed=True)
    assert policy(gateway).minimum_completion_calls == 5


def test_current_read_credit_and_rejected_mutation_successor_remain_budgeted():
    gateway = Gateway(("FAIL",), initial=False, mutations=3)
    failure = gateway.observation()
    counts = counters(model=6)
    runner._update_inspection_counters(counts, [failure])
    selected = policy(gateway, counts)
    assert selected.current_repair_read_reserve_calls == 1
    assert selected.completion_budget_calls == 5
    assert selected.completion_budget_tool_actions == 6
    # Spending the reserved failure inspection removes its credit from both resources.
    inspected = replace(counts, model_calls=counts.model_calls+1,
                        tool_actions=counts.tool_actions+1, failed_check_repair_read_used=True)
    assert policy(gateway, inspected).completion_budget_calls == 4
    # A rejected initial edit uses the rejection allowance, not an accepted-mutation slot.
    initial = Gateway()
    rejected = DevToolResult(action_id="reject", input_hash="sha256:"+"1"*64,
                             tool="replace_text", status="failed", output={})
    counts = counters(model=6, tools=56)
    runner._update_inspection_counters(counts, [rejected])
    successor = policy(initial, counts)
    assert (successor.completion_budget_calls, successor.completion_budget_tool_actions) == (5, 6)
    assert "read_file" in successor.allowed_tools
    assert initial.accepted_mutations == 0


def test_horizon_names_tool_exhaustion_even_when_current_automatic_recheck_saves_model_call():
    gateway = Gateway(("FAIL",), initial=False)
    gateway.observation()
    counts = counters(model=2, tools=2, check_recovery_used_ids={"check-0"})
    selected = policy(gateway, counts)
    assert not selected.completion_possible
    payload = runner._completion_horizon_payload(gateway, counts, DevLimits(), selected)
    assert payload["blocking_resources"] == ["tool_actions"]
    assert payload["minimum_completion_calls"] == 2
    assert payload["minimum_completion_tool_actions"] == 3


def test_missing_anchor_read_preserves_resource_specific_minimum_repair_path():
    gateway = Gateway(("FAIL",), initial=False, anchor=False)
    gateway.observation()
    counts = counters(model=3, tools=4, check_recovery_used_ids={"check-0"})
    selected = policy(gateway, counts)
    assert selected.minimum_completion_calls == 3
    assert selected.minimum_completion_tool_actions == 4
    assert selected.required_inspection_for_completion and selected.max_parallel_reads == 1
    assert selected.allowed_tools == {"read_file", "search_files", "stop_task"}
    assert policy(gateway, counts, auto=False).allowed_tools == {"stop_task"}
    assert policy(gateway, replace(counts, tool_actions=97)).allowed_tools == {"stop_task"}


def test_model_projection_preserves_resource_split_and_default_metadata_shape():
    selected = policy(Gateway())
    horizon = {"minimum_completion_calls": selected.minimum_completion_calls,
               **runner._completion_resources_payload(selected),
               "mutation_completion_horizon": runner._mutation_completion_horizon(selected)}
    assert compact_model_state({"action_horizon": horizon}, [])["action_horizon"] == horizon
    assert runner._completion_resources_payload(policy(Gateway(), auto=False)) == {}
    assert "minimum_tool_actions" not in runner._mutation_completion_horizon(
        policy(Gateway(), auto=False),
    )


def test_completion_cost_reserves_model_successors_without_releasing_tool_slots():
    gateway = Gateway()
    ledger = ledger_for_slots(8)
    enabled = policy(gateway, counters(model=40), cost_ledger=ledger,
                     completion_cost_policy=COMPLETION_RESERVE_POLICY)
    assert enabled.completion_cost["future_calls_reserved"] == 7
    assert enabled.completion_cost["future_cost_reserve_nanos"] == (
        7 * ledger.future_call_reservation_nanos()
    )
    assert "read_file" in enabled.allowed_tools
    disabled = policy(gateway, counters(model=40), auto=False, cost_ledger=ledger,
                      completion_cost_policy=COMPLETION_RESERVE_POLICY)
    assert disabled.allowed_tools == {"replace_text", "stop_task"}
    blocked = policy(gateway, counters(model=40, tools=7), cost_ledger=ledger,
                     completion_cost_policy=COMPLETION_RESERVE_POLICY)
    assert "read_file" not in blocked.allowed_tools
    assert blocked.completion_budget_tool_actions == 8


@cache
def path_costs(count, passed, unused, mutations, pending, anchor, credit, retry, recheck, auto):
    """Independent executable-step oracle; automatic child has zero model/one tool cost."""
    def step(args, model=1, tools=1):
        result = path_costs(*args)
        return result[0]+model, result[1]+tools

    if pending:
        if not anchor:
            return step((count, passed, unused, mutations, True, True, False, retry, recheck, auto))
        automatic = auto and recheck is not None
        paths = [step((count, (1 << recheck) if automatic else 0, unused, mutations-1,
                       False, True, False, retry, None, auto), tools=2 if automatic else 1)]
        if credit:
            paths.append(step((count, passed, unused, mutations, True, True, False,
                               retry, recheck, auto)))
        if retry:
            paths.append(step((count, passed, unused, mutations, True, False, credit,
                               False, recheck, auto)))
        return max(p[0] for p in paths), max(p[1] for p in paths)
    if passed == (1 << count)-1:
        return 1, 1
    paths = []
    for index in range(count):
        bit = 1 << index
        if passed & bit:
            continue
        paths.append(step((count, passed | bit, unused, mutations, False, anchor,
                           False, retry, None, auto)))
        if unused & bit and mutations:
            paths.append(step((count, passed, unused & ~bit, mutations, True, anchor,
                               True, retry, index, auto)))
    return max(p[0] for p in paths), max(p[1] for p in paths)


def test_resource_forecast_matches_independent_multicheck_failure_paths():
    cases = 0
    try:
        for count in range(4):
            for passed in range(1 << count):
                for unused in range(1 << count):
                    for mutations in range(1, 5):
                        for auto in (False, True):
                            for pending in (False, True):
                                # A current failed check cannot also be unused or passing.
                                rechecks = [None] + [i for i in range(count)
                                    if pending and not (passed | unused) & (1 << i)]
                                for recheck in rechecks:
                                    for retry in (False, True):
                                        state = CompletionState(count, count-passed.bit_count(),
                                            unused.bit_count(), bool(unused & ~passed), pending,
                                            True, mutations, retry, pending, auto,
                                            recheck is not None)
                                        value = completion_budget(state)
                                        expected = path_costs(count, passed, unused, mutations,
                                            pending, True, pending, retry, recheck, auto)
                                        assert (value.protected, value.protected_tool_actions) == (
                                            expected
                                        ), (asdict(state), asdict(value), expected)
                                        if not auto:
                                            assert value.minimum == value.minimum_tool_actions
                                            assert value.protected == value.protected_tool_actions
                                        cases += 1
        assert cases > 3000
    finally:
        path_costs.cache_clear()
