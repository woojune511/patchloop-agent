"""Small request and resource controls for an explicitly selected captured call."""

import copy

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_diagnosis_request import focused
from test_repair_path_policy import path_state

from patchloop.dev import diagnosis_request, runner
from patchloop.dev.contracts import DevLimits
from patchloop.dev.cost import COMPLETION_MINIMUM_POLICY
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError


def selection_state():
    return {"status": "needs_path_diagnosis", "call_id": None,
            "call_selection_required": True,
            "call_choices": [{"call_id": "call-1"}, {"call_id": "call-2"}]}


def test_small_schema_offers_only_captured_calls_without_changing_fixed_call_requests():
    state = selection_state()
    tool = dev_tool_schemas(finish_enabled=False, allowed_tools={"run_probe"},
                           path_diagnosis_pending=True, repair_revision=state)[0]
    assert tool["parameters"]["required"] == ["focus", "call_id"]
    assert tool["parameters"]["properties"]["call_id"]["enum"] == ["call-1", "call-2"]
    call = focused()
    call.arguments["call_id"] = "call-1"
    assert validate_tool_batch([call], path_diagnosis_pending=True) == "single_action"
    assert diagnosis_request.tool_schema()["parameters"]["required"] == ["focus"]


@pytest.mark.parametrize("call_id", [None, "call-3"])
def test_missing_or_unoffered_call_is_rejected_before_source_binding(call_id):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid call selection must not reach source binding")

    arguments = focused().arguments
    if call_id:
        arguments["call_id"] = call_id
    with pytest.raises(ContractError, match="/call_id"):
        diagnosis_request.prepare(arguments, selection_state(), None, unexpected)


def test_fixed_call_schema_cannot_accept_an_unoffered_selection():
    state = {**selection_state(), "call_selection_required": False, "call_id": "call-1"}
    with pytest.raises(ContractError, match="/call_id"):
        diagnosis_request.prepare({**focused().arguments, "call_id": "call-1"},
                                  state, None, None)


@pytest.mark.parametrize("short", [False, True])
def test_call_selection_keeps_existing_diagnosis_repair_and_finish_reserves(short):
    gateway = Gateway(initial=False)
    snapshot = path_state(gateway)
    original = copy.deepcopy(snapshot.completion_verification["repair_path"])
    snapshot.completion_verification["repair_path"].update(selection_state())
    policy = runner._tool_policy(
        gateway, counters(model=3 if short else 4, tools=5), DevLimits(), snapshot=snapshot,
        cost_ledger=ledger_for_slots(4), completion_cost_policy=COMPLETION_MINIMUM_POLICY,
        _preview_inspection=False)
    assert policy.minimum_completion_calls == 4
    assert policy.minimum_completion_tool_actions == 5
    if short:
        assert policy.allowed_tools == {"stop_task"}
        assert policy.workflow_gate == "verification_incomplete"
    else:
        assert policy.allowed_tools == {"run_probe", "stop_task"}
        guidance = runner._completion_guidance(snapshot, policy)
        assert guidance["next_action"]["selection"] == "focus_and_call_id"
        assert "model-selected and unverified" in guidance["message"]
        assert policy.repair_path_diagnosis["call_choices"] == selection_state()["call_choices"]
    assert snapshot.completion_verification["repair_path"]["rejected_requests"] == (
        original["rejected_requests"])
