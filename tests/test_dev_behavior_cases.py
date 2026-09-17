"""Separate changed/preserved expectations without certifying semantic coverage."""

from __future__ import annotations

import copy

import httpx
import pytest
from test_dev_notes_lifecycle_v15 import SimulatedCrash, _mutation, _restart
from test_dev_requirement_reference import public_task, setup_gateway
from test_dev_verification_flow_v17 import _completed_check

from patchloop.agent.model import ModelTurn
from patchloop.agent.model import RequestedTool as ProviderTool
from patchloop.artifacts import ArtifactStore
from patchloop.dev import behavior_cases as cases
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest, TextReplacementIntent
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ActionConflict
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.util import canonical_json, sha256_json

CONTRAST = {
    "change": {"setup": 'CSV text with a newline inside a quoted field: "a\nb",c',
               "expected": "One record with two fields; the first retains its embedded newline."},
    "preserve": {"setup": "CSV text with a newline outside quotes: a,b\nc,d",
                 "expected": "Two records with two fields each."},
    "scope_basis": "Quoting determines whether a newline is field data or a record boundary.",
}


@pytest.mark.parametrize("value", [
    None, "contrast", {}, [], {**CONTRAST, "private_path": "untrusted-value"},
    {**CONTRAST, "change": None}, {**CONTRAST, "scope_basis": 1},
    {**CONTRAST, "scope_basis": "x" * 301},
    {**CONTRAST, "preserve": {"setup": "", "expected": "unchanged"}},
])
def test_invalid_optional_cases_are_bounded_annotations_not_action_errors(value):
    receipt = cases.bind(value, public_task())
    assert receipt["status"] == ("omitted" if value is None else "invalid")
    assert "cases" not in receipt and len(canonical_json(receipt)) < 200
    call = _mutation("edit")
    call.arguments["behavior_cases"] = value
    converted = runner._turn_from_openai(ModelTurn(tool_calls=[ProviderTool(
        name=call.name, action_id=call.action_id,
        arguments={**call.arguments, "turn_decision": call.turn_decision.model_dump(mode="json")},
    )]))
    assert converted.error_code is None
    assert converted.tool_calls[0].arguments == call.arguments
    assert TextReplacementIntent.model_validate(call.arguments).behavior_cases == value


@pytest.mark.parametrize("preservation", [CONTRAST["preserve"], None])
def test_recording_cases_does_not_validate_their_meaning_or_invent_a_boundary(preservation):
    value = {**CONTRAST, "preserve": preservation}
    task = public_task()  # Deliberately unrelated: shape and identity are not entailment.
    receipt = cases.bind(value, task)
    assert receipt["status"] == "recorded" and receipt["cases"] == value
    assert receipt["public_task_hash"] == sha256_json(task.model_dump(mode="json"))
    assert receipt["coverage_status"] == "not_assessed"
    assert receipt["interpretation_status"] == "model_authored_unverified"
    projected = cases.project(receipt, task)
    projected["cases"]["scope_basis"] = "local change"
    assert receipt["cases"] == value
    task.issue.description += " More public requirements."
    assert cases.project(receipt, task)["status"] == "stale"
    assert receipt["status"] == "recorded"


@pytest.mark.parametrize("value", [CONTRAST, None, {"change": "invalid"}])
def test_annotation_and_check_review_are_nonblocking_and_replay_exactly(tmp_path, value):
    gateway = setup_gateway(tmp_path)
    call = _mutation("edit")
    call.arguments["behavior_cases"] = value
    result = gateway.execute(call)
    assert result.status == "succeeded"
    receipt = result.output["mutation"]["behavior_cases"]
    assert receipt == cases.bind(value, gateway.public_task)
    assert result.output["mutation"]["plan_hash"] == sha256_json(call.arguments)
    checked = _completed_check(gateway, "check")
    card = runner._attempt_card(checked, gateway)
    assert card["mutation_expectation"]["behavior_cases"] == receipt
    assert gateway.ready_to_submit()
    before = gateway.journal.path.read_bytes()
    restored = _restart(gateway)
    replay = restored.execute(call)
    assert replay.replayed and replay.output == result.output
    assert runner._attempt_card(checked, restored) == card
    assert gateway.journal.path.read_bytes() == before
    call.arguments["behavior_cases"] = {**CONTRAST, "scope_basis": "changed raw input"}
    with pytest.raises(ActionConflict, match="different input"):
        restored.execute(call)


def test_failed_proposal_and_later_edit_do_not_replace_or_inherit_the_cases(tmp_path):
    gateway = setup_gateway(tmp_path)
    first = _mutation("first")
    first.arguments["behavior_cases"] = CONTRAST
    gateway.execute(first)
    old_check = _completed_check(gateway, "first-check")
    old_card = runner._attempt_card(old_check, gateway)
    frozen = copy.deepcopy(old_card)
    rejected = _mutation("rejected", old="not present")
    rejected.arguments["behavior_cases"] = {**CONTRAST, "preserve": None}
    assert gateway.execute(rejected).status == "failed"
    assert runner._attempt_card(old_check, gateway) == frozen
    second = _mutation("second", "editable = 1", "editable = 2")
    assert TextReplacementIntent.model_validate(second.arguments).model_dump(mode="json") == (
        second.arguments
    )
    result = gateway.execute(second)
    assert "behavior_cases" not in result.output["mutation"]
    assert result.output["mutation"]["plan_hash"] == sha256_json(second.arguments)
    assert "mutation_expectation" not in runner._attempt_card(old_check, gateway)
    current = runner._attempt_card(_completed_check(gateway, "second-check"), gateway)
    assert "behavior_cases" not in current["mutation_expectation"]
    assert old_card == frozen


@pytest.mark.parametrize("boundary", ["admission", "replace", "result"])
def test_recovery_uses_admitted_cases_without_rebinding_or_duplicate_write(
    tmp_path, monkeypatch, boundary,
):
    gateway = setup_gateway(tmp_path)
    call = _mutation("interrupted")
    call.arguments["behavior_cases"] = CONTRAST
    append, replace = DevJournal.append, WorkspaceManager.atomic_replace_source
    crashed, writes = False, 0

    def intercept_append(self, event_type, payload=None):
        nonlocal crashed
        event = append(self, event_type, payload)
        target = "action_started" if boundary == "admission" else "action_finished"
        if not crashed and boundary != "replace" and event_type == target:
            crashed = True
            raise SimulatedCrash()
        return event

    def intercept_replace(*args):
        nonlocal crashed, writes
        replace(*args)
        writes += 1
        if not crashed and boundary == "replace":
            crashed = True
            raise SimulatedCrash()

    monkeypatch.setattr(DevJournal, "append", intercept_append)
    monkeypatch.setattr(WorkspaceManager, "atomic_replace_source", staticmethod(intercept_replace))
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    admitted = next(e["payload"]["mutation_behavior_cases"] for e in gateway.journal.events()
                    if e["event_type"] == "action_started"
                    and e["payload"]["tool"] == "replace_text")

    def no_rebind(*args):
        pytest.fail("pending/completed replay must use the original case receipt")

    monkeypatch.setattr(cases, "bind", no_rebind)
    restored = _restart(gateway)
    restored.public_task.issue.description += " Changed public requirement."
    result = restored.execute(call)
    assert result.status == "succeeded" and writes == restored.accepted_mutations == 1
    expected = admitted if boundary == "result" else {
        "status": "stale", "diagnostics": ["public_task_identity_changed"],
        "interpretation_status": "model_authored_unverified",
    }
    assert result.output["mutation"]["behavior_cases"] == expected
    assert restored.actionable_last_successful_mutation()["behavior_cases"]["status"] == "stale"


@pytest.mark.parametrize("completed", [False, True])
def test_legacy_missing_field_pending_and_completed_recovery(tmp_path, monkeypatch, completed):
    gateway = setup_gateway(tmp_path)
    call = _mutation("legacy")
    append = DevJournal.append
    crashed = False

    def intercept(self, event_type, payload=None):
        nonlocal crashed
        event = append(self, event_type, payload)
        if not crashed and event_type == ("action_finished" if completed else "action_started"):
            crashed = True
            raise SimulatedCrash()
        return event

    monkeypatch.setattr(DevJournal, "append", intercept)
    with pytest.raises(SimulatedCrash):
        gateway.execute(call)
    result = _restart(gateway).execute(call)
    assert result.status == "succeeded" and result.replayed is completed
    assert "behavior_cases" not in result.output["mutation"]
    assert result.output["mutation"]["plan_hash"] == sha256_json(call.arguments)


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("invalid", [False, True])
def test_actual_inputs_keep_both_cases_with_check_result_and_reach_isolated_evaluation(
    tmp_path, monkeypatch, context_policy, invalid,
):
    value = {"change": "bad shape"} if invalid else CONTRAST

    class CaseMock(MockDevAdapter):
        def next_turn(self, context, tools):
            turn = super().next_turn(context, tools)
            for call in turn.tool_calls:
                if call.name == "replace_text":
                    call.arguments["behavior_cases"] = value
            return turn

    def no_network(*args, **kwargs):
        pytest.fail("case annotation tests cannot make provider/count calls")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_network)
    monkeypatch.setattr(runner, "MockDevAdapter", CaseMock)
    run = runner.run_dev(DevRunRequest(
        provider="mock", model="mock-dev", state_root=tmp_path,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        context_policy=context_policy, planning_policy="brief-v1",
    ))["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    assert run["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert run["evaluator"]["claim_eligible"] is False
    journal, store = DevJournal(tmp_path, run["run_id"]), ArtifactStore(tmp_path / "artifacts")
    turns = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"]
    states = [reconstruct_state(runner._load_active_model_input(
        turn, store, context_policy=context_policy,
    ), context_policy=context_policy) for turn in turns]
    final = states[-1]
    review = next(card for card in final["recent_attempt_result_next_question"]
                  if "mutation_expectation" in card)
    annotation = review["mutation_expectation"]["behavior_cases"]
    assert annotation["status"] == ("invalid" if invalid else "recorded")
    if not invalid:
        assert annotation["cases"] == CONTRAST and annotation["coverage_status"] == "not_assessed"
        assert "unexercised or unspecified cases remain untested" in review["next_question"]
    assert final["public_task"] == states[0]["public_task"]
    assert review["mutation_expectation"]["diff_hash"] == final["current_diff"]["patch_hash"]
    assert final["visible_check_status"][0]["status"] == "PASS"
    assert "finish_task" in final["available_tool_names"]


def test_only_mutation_schema_adds_bounded_optional_cases():
    for schema in dev_tool_schemas(finish_enabled=True, planning_policy="brief-v1"):
        params = schema["parameters"]
        if schema["name"] == "replace_text":
            field = params["properties"]["behavior_cases"]
            assert field["type"] == ["object", "null"]
            for key in ("change", "preserve"):
                assert all(item["maxLength"] == 300
                           for item in field["properties"][key]["properties"].values())
        else:
            assert "behavior_cases" not in params["properties"]
