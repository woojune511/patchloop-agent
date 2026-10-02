from decimal import Decimal
from types import SimpleNamespace

import pytest

from diagnostics.review_context_offline import (
    INSTRUCTION,
    SharedBudget,
    handoff_report,
    reviewer_request,
)
from patchloop.errors import ContractError
from patchloop.util import canonical_json


def test_fresh_projection_removes_history_but_preserves_facts():
    public = {"issue": {"description": "public issue"}}
    loaded = SimpleNamespace(
        package=SimpleNamespace(public=SimpleNamespace(model_dump=lambda **kw: public)),
        diff={"patch": "public diff", "patch_hash": "candidate"},
        checks=[{"output": {"stdout": "public observation"}}],
        bundle={"request": {"model": "model", "input": [
            {"role": "system", "content": "old system"},
            {"type": "reasoning", "encrypted_content": "old encrypted"},
            {"role": "user", "content": "old plan"},
        ], "tools": [{"name": n} for n in [
            "read_file", "run_probe", "replace_text", "finish_task", "shell"]]}}
    )
    a, b = reviewer_request(loaded, "A"), reviewer_request(loaded, "B")
    assert a["input"][0] == b["input"][0] == {"role": "system", "content": INSTRUCTION}
    assert a["input"][-1] == b["input"][-1]
    assert a["tools"] == b["tools"] == [{"name": "read_file"}, {"name": "run_probe"}]
    assert "old encrypted" in canonical_json(a)
    for marker in ["old encrypted", "old plan", "old system"]:
        assert marker not in canonical_json(b)
    assert "public observation" in canonical_json(b)
    assert loaded.bundle["request"]["input"][0]["content"] == "old system"


def test_shared_cost_and_call_allowances_survive_handoff():
    budget = SharedBudget(clock=lambda: 0)
    for _ in range(4):
        budget.admit(100)
        budget.settle(100, 0, 10)
    spent = budget.ledger.spent_nanos
    with pytest.raises(ContractError, match="call budget"):
        budget.admit(100)
    budget.repair()
    assert budget.ledger.spent_nanos == spent
    for _ in range(12):
        budget.admit(100)
        budget.settle(100, 0, 10)
    with pytest.raises(ContractError, match="call budget"):
        budget.admit(100)
    assert budget.calls == 16


def test_phase_tools_and_action_budget():
    budget = SharedBudget(clock=lambda: 0)
    with pytest.raises(ContractError, match="tool not allowed"):
        budget.action("replace_text")
    for _ in range(12):
        budget.action("read_file")
    with pytest.raises(ContractError, match="action budget"):
        budget.action("run_probe")
    budget.repair()
    for _ in range(2):
        budget.action("replace_text")
    with pytest.raises(ContractError, match="edit budget"):
        budget.action("replace_text")
    for _ in range(34):
        budget.action("read_file")
    with pytest.raises(ContractError, match="action budget"):
        budget.action("read_file")


def test_review_time_is_charged_to_episode():
    now = [0]
    budget = SharedBudget(clock=lambda: now[0])
    now[0] = 180
    with pytest.raises(ContractError, match="review time"):
        budget.admit(100)
    budget.repair()
    now[0] = 900
    with pytest.raises(ContractError, match="episode time"):
        budget.admit(100)


@pytest.mark.parametrize("failure", ["count", "transport", "billing", "cleanup"])
def test_uncertainty_stops_both_roles(failure):
    budget = SharedBudget(clock=lambda: 0)
    if failure != "count":
        budget.admit(100)
    budget.fail()
    with pytest.raises(ContractError):
        budget.repair()
    with pytest.raises(ContractError):
        budget.admit(100)
    with pytest.raises(ContractError):
        budget.action("read_file")


def test_pending_dispatch_blocks_handoff_and_second_dispatch():
    budget = SharedBudget(clock=lambda: 0)
    budget.admit(100)
    with pytest.raises(ContractError, match="unsettled"):
        budget.admit(100)
    with pytest.raises(ContractError, match="uncertain"):
        budget.repair()
    with pytest.raises(ValueError, match="uncertain usage"):
        budget.settle(100, 0, -1)
    assert budget.stopped


def test_cost_cap_applies_across_roles():
    budget = SharedBudget(cap=Decimal("0.1"), clock=lambda: 0)
    admission = budget.admit(100)
    budget.settle(100, 0, admission.output_ceiling)
    budget.repair()
    with pytest.raises(ContractError, match="cost budget"):
        budget.admit(100)


def test_report_never_becomes_execution_credit():
    report = dict(suspected_behavior="none established", evidence="public input",
                  observation="unverified model statement", candidate_hash="old",
                  limitations="none")
    packet = handoff_report(report, "old")
    assert packet["is_execution_receipt"] is False
    with pytest.raises(ContractError, match="candidate changed"):
        handoff_report(report, "new")
    with pytest.raises(ContractError, match="fields"):
        handoff_report({**report, "passed": True}, "old")


def test_billing_overrun_is_not_reusable():
    budget = SharedBudget(clock=lambda: 0)
    budget.admit(1)
    with pytest.raises(ValueError, match="billing"):
        budget.settle(10_000_000, 0, 1)
    assert budget.stopped
    with pytest.raises(ContractError):
        budget.repair()
