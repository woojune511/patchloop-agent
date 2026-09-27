import copy

import pytest

from diagnostics.anyio_caller_probe import MODES, interpret, parity, program
from patchloop.errors import ContractError


def observations():
    pending = {"done": False, "cancelled": False, "cancelling": 0}
    return [
        {"mode": "callback_interrupt", "observations": [
            {"stage": stage, "caller": dict(pending), "exception": "KeyboardInterrupt"}
            for stage in ("before_trigger", "run_test_raised", "before_teardown")
        ]},
        {"mode": "explicit_caller_cancel", "observations": [
            {"stage": "after_cancel_request", "cancel_returned": True,
             "caller": {"done": False, "cancelled": False, "cancelling": 1}},
            {"stage": "run_test_raised", "exception": "CancelledError",
             "caller": {"done": True, "cancelled": True, "cancelling": 1}},
        ]},
    ]


def test_positive_control_required_before_zero_can_be_interpreted():
    rows = observations()
    assert interpret(rows)["verdict"] == "INTERRUPT_WITHOUT_CALLER_CANCELLATION"
    broken = copy.deepcopy(rows)
    broken[1]["observations"][0]["caller"]["cancelling"] = 0
    with pytest.raises(ContractError, match="control"):
        interpret(broken)


def test_completed_is_not_cancelled_and_unknown_is_not_a_contradiction():
    rows = observations()
    rows[0]["observations"][1]["caller"]["done"] = True
    result = interpret(rows)
    assert result["verdict"] == "INCONCLUSIVE"
    assert result["caller_cancellation_observed_after_interrupt"] is False
    rows[0]["observations"][1]["caller"]["cancelling"] = 1
    assert interpret(rows)["verdict"] == "CALLER_CANCELLATION_OBSERVED"


def test_control_program_only_changes_trigger_mode():
    a, b = [program(mode).splitlines() for mode in MODES]
    assert a[0] != b[0] and a[1:] == b[1:]
    assert len(program(MODES[0])) < 8000
    with pytest.raises(ContractError, match="unknown"):
        program("unregistered")


@pytest.mark.parametrize("change", ["event", "owner"])
def test_instrumentation_parity_rejects_changed_behavior(change):
    original = repr({"stage": "after_setup", "events": [("fixture_setup", 10)],
                     "runner_task_done": False})
    new = {"observations": [{"stage": "after_setup", "runner": {"done": False},
                             "events": [{"name": "fixture_setup", "same_fixture_task": True}]}]}
    assert parity(original, new)["matched_stages"] == 1
    event = new["observations"][0]["events"][0]
    event["name" if change == "event" else "same_fixture_task"] = (
        "changed" if change == "event" else False)
    with pytest.raises(ContractError):
        parity(original, new)
