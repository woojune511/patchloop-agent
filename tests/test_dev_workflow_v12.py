"""Budget-only workflow regressions, including an independent exhaustive oracle."""

from functools import cache
from types import SimpleNamespace

from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevToolResult


@cache
def _protected_oracle(
    count: int,
    passed: int,
    unused: int,
    mutations: int,
    pending: bool,
    anchor: bool,
    read_credit: bool,
    retry: bool,
) -> int:
    """Enumerate actual steps/orders/outcomes rather than the production formula."""

    if pending:
        assert mutations > 0
        if not anchor:
            return 1 + _protected_oracle(
                count, passed, unused, mutations, True, True, False, retry
            )
        paths = [
            1 + _protected_oracle(
                count, 0, unused, mutations - 1, False, True, False, retry
            )
        ]
        if read_credit:
            paths.append(
                1 + _protected_oracle(
                    count, passed, unused, mutations, True, True, False, retry
                )
            )
        if retry:
            paths.append(
                1 + _protected_oracle(
                    count, passed, unused, mutations, True, False, read_credit, False
                )
            )
        return max(paths)
    if passed == (1 << count) - 1:
        return 1
    paths = []
    for index in range(count):
        bit = 1 << index
        if passed & bit:
            continue
        paths.append(
            1 + _protected_oracle(
                count, passed | bit, unused, mutations, False, anchor, False, retry
            )
        )
        if unused & bit and mutations:
            paths.append(
                1 + _protected_oracle(
                    count, passed, unused & ~bit, mutations, True, anchor, True, retry
                )
            )
    return max(paths)


def test_completion_formula_matches_all_small_failure_orders() -> None:
    for count in range(5):
        all_checks = (1 << count) - 1
        for passed in range(1 << count):
            for unused in range(1 << count):
                for mutations in range(5):
                    for pending in (False, True):
                        if pending and not mutations:
                            continue
                        for anchor in (False, True):
                            for retry in (False, True):
                                for credit in ((False, True) if pending else (False,)):
                                    state = runner._CompletionState(
                                        check_count=count,
                                        remaining_check_count=count - passed.bit_count(),
                                        unused_check_count=unused.bit_count(),
                                        unrun_recoverable_check=bool(
                                            unused & (all_checks ^ passed)
                                        ),
                                        requires_mutation=pending,
                                        anchor_available=anchor,
                                        remaining_mutations=mutations,
                                        mutation_retry_available=retry,
                                        repair_read_credit=credit,
                                    )
                                    budget = runner._completion_budget(state)
                                    expected = _protected_oracle(
                                        count, passed, unused, mutations,
                                        pending, anchor, credit, retry,
                                    )
                                    assert budget.protected == expected, state
    _protected_oracle.cache_clear()


class _Gateway:
    def __init__(
        self,
        states: dict[str, str],
        *,
        accepted: int = 1,
        anchor: bool = True,
        patch: str = "diff",
    ) -> None:
        self.states = states
        self.accepted_mutations = accepted
        self.anchor = anchor
        self.last_failed_mutation = None
        self.public_task = SimpleNamespace(
            visible_checks=[SimpleNamespace(id=check_id) for check_id in states]
        )
        self.current_diff = SimpleNamespace(
            patch=patch, patch_hash="current", changed_files=["source.py"], untracked_files=[]
        )
        self.current_diff_hash = "current"

    def visible_check_status(self):
        return [{"check_id": key, "status": value} for key, value in self.states.items()]

    def remaining_visible_check_ids(self):
        return [key for key, value in self.states.items() if value != "PASS"]

    def unrun_visible_check_ids(self):
        return [key for key, value in self.states.items() if value == "NOT_RUN"]

    def has_current_mutation_evidence(self):
        return self.anchor

    def ready_to_submit(self):
        return bool(self.current_diff.patch) and all(
            value == "PASS" for value in self.states.values()
        )


def test_late_failure_cannot_claim_a_cheaper_passed_check_reserve() -> None:
    gateway = _Gateway({"A": "PASS", "B": "PASS", "C": "NOT_RUN"}, accepted=3)
    counters = runner._RunCounters(model_calls=35, mutation_recovery_used=True)
    policy = runner._tool_policy(gateway, counters, DevLimits())
    assert policy.minimum_completion_calls == 2
    assert policy.completion_budget_calls == 7
    assert policy.future_check_failure_slots == 1
    assert policy.protected_completion_possible is False
    assert policy.check_recovery_reserve_ids == ("A", "B", "C")
    gateway.states = {"A": "NOT_RUN", "B": "PASS", "C": "PASS"}
    reversed_order = runner._tool_policy(gateway, counters, DevLimits())
    assert reversed_order.completion_budget_calls == 7


def test_repair_credit_keeps_other_check_protection_continuous() -> None:
    gateway = _Gateway({"A": "PASS", "B": "FAIL"})
    counters = runner._RunCounters(
        model_calls=31,
        mutation_recovery_used=True,
        check_recovery_used=True,
        check_recovery_used_ids={"B"},
        failed_check_pending=True,
    )
    before = runner._tool_policy(gateway, counters, DevLimits())
    assert before.completion_budget_calls == 9
    assert before.check_recovery_reserve_ids == ("A",)
    assert before.inspection_uses_repair_credit
    assert {"read_file", "search_files", "replace_text"} <= before.allowed_tools
    assert before.targeted_read_paths == ()
    counters.model_calls += 1
    counters.failed_check_repair_read_used = True
    after_read = runner._tool_policy(gateway, counters, DevLimits())
    assert after_read.completion_budget_calls == 8
    assert after_read.protected_completion_possible
    counters.model_calls += 1
    counters.failed_check_pending = False
    gateway.accepted_mutations += 1
    gateway.states = {"A": "NOT_RUN", "B": "NOT_RUN"}
    after_repair = runner._tool_policy(gateway, counters, DevLimits())
    assert after_repair.completion_budget_calls == 7
    assert after_repair.protected_completion_possible


def test_coverage_plateau_and_mutation_failure_do_not_mask_inspection() -> None:
    gateway = _Gateway({"A": "NOT_RUN"}, accepted=0, patch="")
    gateway.last_failed_mutation = {"mutation_failure": {"class": "scope_violation"}}
    counters = runner._RunCounters(
        consecutive_no_evidence_gain_turns=20,
        commitment_diff_hash="current",
        failed_mutation_pending=True,
        failed_mutation_repair_turns=50,
    )
    policy = runner._tool_policy(gateway, counters, DevLimits())
    assert {"read_file", "search_files", "replace_text"} <= policy.allowed_tools
    assert policy.commitment_action_state == "advisory"
    assert policy.targeted_read_paths == ()
    assert runner._commitment_signal(gateway, counters, policy)["hard_gate"] is False


def test_rejected_optional_mutation_does_not_erase_checked_baseline() -> None:
    gateway = _Gateway({"A": "PASS", "B": "PASS"})
    gateway.last_failed_mutation = {"mutation_failure": {"class": "anchor_invalid"}}
    counters = runner._RunCounters(model_calls=39, failed_mutation_pending=True)
    policy = runner._tool_policy(gateway, counters, DevLimits())
    assert policy.workflow_gate == "ready_to_submit"
    assert policy.minimum_completion_calls == 1
    assert policy.allowed_tools == {"finish_task", "stop_task"}


def test_optional_edit_reserves_rechecks_but_missing_anchor_read_is_completion_work() -> None:
    gateway = _Gateway({"A": "PASS", "B": "NOT_RUN"})
    policy = runner._tool_policy(
        gateway, runner._RunCounters(model_calls=38), DevLimits()
    )
    assert policy.allowed_tools == {"run_check", "stop_task"}
    assert policy.optional_mutation_completion_calls > 2
    gateway = _Gateway({"A": "NOT_RUN", "B": "NOT_RUN"}, accepted=0, anchor=False, patch="")
    counters = runner._RunCounters(model_calls=35)
    required = runner._tool_policy(gateway, counters, DevLimits())
    assert required.minimum_completion_calls == 5
    assert required.required_inspection_for_completion
    assert required.max_parallel_reads == 1
    assert {"read_file", "search_files"} <= required.allowed_tools
    counters.model_calls += 1
    gateway.anchor = True
    repair = runner._tool_policy(gateway, counters, DevLimits())
    assert repair.allowed_tools == {"replace_text", "stop_task"}


def test_tool_execution_error_does_not_consume_semantic_check_allowance() -> None:
    counters = runner._RunCounters()
    runner._update_inspection_counters(
        counters,
        [DevToolResult(
            action_id="check-error", input_hash="sha256:" + "0" * 64,
            tool="run_check", status="failed", output={}, message="sandbox unavailable",
        )],
    )
    assert not counters.check_recovery_used
    assert not counters.failed_check_pending


def test_correction_only_names_available_actions() -> None:
    gateway = _Gateway({"A": "FAIL"})
    counters = runner._RunCounters(model_calls=37, mutation_recovery_used=True)
    policy = runner._tool_policy(gateway, counters, DevLimits())
    correction = runner._protocol_correction(
        turn_id="turn", code="INVALID_BATCH", issue="invalid batch", gateway=gateway,
        policy=policy,
    )
    assert policy.allowed_tools == {"replace_text", "stop_task"}
    assert "read_file" not in correction["message"]
    assert "search_files" not in correction["message"]
    assert "run_check" not in correction["message"]
