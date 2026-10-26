"""Short, offline first-observation -> small edit and recovery controls."""

import copy
from dataclasses import replace

import pytest
from test_dev_completion_cost import ledger_for_slots
from test_dev_completion_resources import Gateway, counters
from test_dev_probe_action_replay import restore
from test_dev_segments import assert_submitted, configured, records
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction_budget import snapshot
from test_judgment_integration import diagnostic_probe
from test_repair_path_diagnosis import PATH, TracedProbe

from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevModelTurn, RequestedTool
from patchloop.dev.cost import COMPLETION_MINIMUM_POLICY
from patchloop.dev.model import MockDevAdapter
from patchloop.util import sha256_json


def observe(action="observe-first", function="parse_rows"):
    return RequestedTool(name="observe_original", action_id=action, arguments={
        "hypothesis": "The original failing input reaches this parser before record splitting.",
        "candidates": [{"origin": "workspace", "path": PATH, "function": function,
                        "prediction": "entered"}],
    })


def edit():
    call = mutation_call(None)
    return RequestedTool(name="replace_text", action_id=call.action_id,
                         arguments={k: v for k, v in call.arguments.items()
                                    if k != "causal_revision"})


def prepare(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = TracedProbe(status="passed")
    gateway.execute(read_calls()[1])
    original = gateway.execute(diagnostic_probe(gateway.public_task, "original", corrected=True))
    assert original.status == "succeeded"
    assert gateway.completion_verification(diff_hash=gateway.current_diff_hash)[
        "first_observation"]["available"]
    return gateway, journal, workspace, backend, original


@pytest.mark.parametrize("rejected_first", [False, True])
def test_observe_original_small_edit_recovery_and_receipt_link(gateway_factory, rejected_first):
    gateway, journal, workspace, backend, original = prepare(gateway_factory)
    if rejected_first:
        failed = gateway.execute(observe("bad-function", "absent_function"))
        assert failed.status == "failed" and backend.calls == 1
        assert failed.output["invalid_fields"][0]["path"] == "/candidates"
    call = observe()
    raw = copy.deepcopy(call.model_dump(mode="json"))
    result = gateway.execute_batch([call])[0]
    assert result.status == "succeeded", result
    state = gateway.completion_verification(
        diff_hash=gateway.current_diff_hash)["first_observation"]
    assert state["status"] == "observed", state
    assert state["observation"]["candidates"][0]["status"] == "prediction_matched"
    assert result.output["source_hash"] == original.output["source_hash"]
    assert result.output["reproduction"]["binding"] == original.output["reproduction"]["binding"]
    assert result.output["reproduction"]["observed_json"] == original.output["reproduction"][
        "observed_json"]
    assert call.model_dump(mode="json") == raw and backend.calls == 2
    start = next(e["payload"] for e in journal.events()
                 if e["event_type"] == "action_started"
                 and e["payload"]["action_id"] == call.action_id)
    assert "turn_decision" not in start
    assert start["input_hash"] == sha256_json({"tool": call.name, "arguments": call.arguments})
    gateway = restore(gateway, journal, workspace, gateway.public_task, backend)
    assert gateway.execute(call).replayed and backend.calls == 2
    assert gateway.execute(observe("new-name")).status == "failed" and backend.calls == 2
    mutation = edit()
    repaired = gateway.execute_batch([mutation])[0]
    assert repaired.status == "succeeded", repaired
    assert repaired.output["mutation"]["first_observation_link"][
        "observation_action_id"] == call.action_id
    card = runner._batch_attempt_card(turn_id="small-edit", calls=[mutation],
                                      results=[repaired], gateway=gateway)
    assert "turn_decision" not in card
    assert gateway.completion_verification(diff_hash=gateway.current_diff_hash)[
        "first_observation"]["evidence_currency"] == "historical"
    assert gateway.execute(mutation).replayed and gateway.accepted_mutations == 1


@pytest.mark.parametrize("remaining,expected", [(3, False), (4, True), (5, True)])
def test_observation_shares_existing_reserve_and_leaves_completion(remaining, expected):
    gateway = Gateway(initial=False)
    state = snapshot(gateway, status="refuted", pending_count=0)
    state.completion_verification.update(
        early_replay_reusable=True, baseline_failure_case_ids=["original"],
        first_observation={"status": "available", "available": True})
    policy = runner._tool_policy(gateway, counters(model=remaining), DevLimits(), snapshot=state)
    direct = runner._tool_policy(gateway, counters(model=remaining), DevLimits(), snapshot=replace(
        state, completion_verification={**state.completion_verification, "first_observation": {}}))
    assert policy.minimum_completion_calls == direct.minimum_completion_calls == 3
    assert policy.completion_budget_calls == direct.completion_budget_calls
    assert ("observe_original" in policy.allowed_tools) == expected
    assert "replace_text" in policy.allowed_tools
    if remaining == 4:
        assert "read_file" not in policy.allowed_tools
    cost_policy = runner._tool_policy(
        gateway, counters(model=40), DevLimits(), snapshot=state,
        cost_ledger=ledger_for_slots(remaining), completion_cost_policy=COMPLETION_MINIMUM_POLICY)
    assert ("observe_original" in cost_policy.allowed_tools) == expected
    if remaining == 4:
        assert "read_file" not in cost_policy.allowed_tools


def test_no_action_correction_keeps_observation_in_small_fresh_context(
    tmp_path, monkeypatch, smoke_package,
):
    backend = TracedProbe(status="passed")
    steps = iter([read_calls()[1], diagnostic_probe(
        smoke_package.public, "original", corrected=True),
                  observe(), edit()])

    class Script(MockDevAdapter):
        def next_turn(self, context, tools):
            call = next(steps, None)
            return DevModelTurn(tool_calls=[call]) if call else super().next_turn(context, tools)

    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", incomplete_at=(3,),
        script=Script("csv-quoted-newline"))
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    request = request.model_copy(update={"enable_probes": True})
    assert_submitted(runner.run_dev(request)["runs"][0])
    assert backend.calls == 3 and len(inputs) == len(counted)
    before, corrected = views[3:5]
    assert before["repair_stage"]["first_observation"]["status"] == "observed"
    assert before["repair_stage"] == corrected["repair_stage"]
    assert not {"working_plan", "working_notes"} & set(corrected)
    assert corrected["protocol_correction"]["repair_correction"]["kind"] == "no_action"
    assert corrected["segment_handoff"]["reason"] == "repair_no_action"
    assert corrected["remaining_budget"]["model_calls"] == before["remaining_budget"][
        "model_calls"] - 1
    assert corrected["remaining_budget"]["tool_actions"] == before["remaining_budget"][
        "tool_actions"]
    assert not any(i.get("type") == "reasoning" for i in inputs[4])
    journal, _ = records(request)
    assert sum(e["event_type"] == "protocol_correction" for e in journal.events()) == 1


@pytest.mark.parametrize("boundary", ["model", "tools", "money"])
def test_rejected_first_edit_cannot_spend_observation_on_other_diagnostics(boundary):
    gateway = Gateway(initial=True)
    state = snapshot(gateway, status="refuted", pending_count=0)
    state.completion_verification.update(
        early_replay_reusable=True, baseline_failure_case_ids=["original"],
        first_observation={"status": "available", "available": True})
    counts = counters(model=4 if boundary == "model" else 20,
                      tools=5 if boundary == "tools" else 20, mutation_recovery_used=True)
    options = ({"cost_ledger": ledger_for_slots(4),
                "completion_cost_policy": COMPLETION_MINIMUM_POLICY}
               if boundary == "money" else {})
    policy = runner._tool_policy(gateway, counts, DevLimits(max_accepted_mutations=1),
                                 snapshot=state, **options)
    assert policy.minimum_completion_calls == policy.completion_budget_calls == 3
    assert policy.minimum_completion_tool_actions == 4
    assert policy.allowed_tools == {"replace_text", "observe_original", "stop_task"}


@pytest.mark.parametrize("tools,comparison", [(6, False), (7, True)])
def test_two_child_test_comparison_also_preserves_original_observation(tools, comparison):
    gateway = Gateway(initial=True)
    state = snapshot(gateway, status="refuted", pending_count=0)
    state.completion_verification.update(
        early_replay_reusable=True, baseline_failure_case_ids=["original"],
        first_observation={"status": "available", "available": True})
    counts = counters(model=20, tools=tools, mutation_recovery_used=True)
    limits = DevLimits(max_accepted_mutations=1)
    policy = runner._tool_policy(gateway, counts, limits, snapshot=state)
    assert "run_tests" in policy.allowed_tools  # Single execution remains affordable.
    assert runner._test_comparison_enabled(policy, counts, limits) is comparison
    call = RequestedTool(name="run_tests", action_id="comparison", arguments={
        "comparison": {"against": "original_base", "mutation_action_id": None}})
    assert runner._batch_fits_tool_budget([call], counts, limits, policy) is comparison
