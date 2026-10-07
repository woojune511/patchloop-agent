"""Provider-free parity at the actual policy/runner/recovery boundary."""

from __future__ import annotations

import copy
import inspect
import json
from typing import get_args, get_type_hints

import httpx
import pytest
from test_dev_planning import request as mock_request
from test_dev_probe_action_replay import probe
from test_dev_probes import FakeProbe
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from test_thin_policy_gateway import PassingSandbox, call, mutation, restart

from patchloop.agent.model import EncryptedReasoningContinuationItem as ProviderReasoning
from patchloop.agent.model import FunctionCallContinuationRef as ProviderCallRef
from patchloop.agent.model import ModelTurn
from patchloop.agent.model import RequestedTool as ProviderCall
from patchloop.cli import dev
from patchloop.dev import runner, segments, thin_policy
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.inspection_projection import project_inspection_context
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, public_exchanges
from patchloop.errors import RecoveryError, ResumeContractMismatch
from patchloop.util import canonical_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("policy parity must not dispatch network requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def test_cli_policy_is_explicit_and_default_stays_current():
    parameter = inspect.signature(dev).parameters["agent_policy"]
    assert parameter.default == "current"
    annotation = get_type_hints(dev, include_extras=True)["agent_policy"]
    assert get_args(get_args(annotation)[0]) == ("current", "thin")
    option = get_args(annotation)[1]
    assert "--agent-policy" in (option.default, *option.param_decls)


def test_named_projection_preserves_facts_and_arbitrary_observation_keys():
    observed = {"turn_decision": "source string", "next_question": "test stdout",
                "message": "public result", "working_plan": "task data"}
    state = {
        "public_task": observed, "latest_tool_results": [{"output": observed}],
        "source_spans": [{"content": canonical_json(observed)}],
        "completion_guidance": {"stage": "ready", "diff_hash": "h", "submission_ready": True,
                                "message": "submit", "next_action": "finish_task"},
        "commitment_signal": {"message": "act", "count": 3},
        "working_plan": {"plan": "narration"},
        "working_notes": {"findings": [observed]},
        "recent_attempt_result_next_question": [{
            "action_id": "batch:1", "attempt": "inspect", "next_question": "act",
            "result": {"actions": [{"action_id": "r1", "turn_decision": {}, "span_count": 2}]},
            "mutation_expectation": observed,
        }],
    }
    before = copy.deepcopy(state)
    expected = copy.deepcopy(state)
    del expected["working_plan"]
    del expected["completion_guidance"]["message"]
    del expected["completion_guidance"]["next_action"]
    del expected["commitment_signal"]["message"]
    del expected["recent_attempt_result_next_question"][0]["next_question"]
    del expected["recent_attempt_result_next_question"][0]["result"]["actions"][0]["turn_decision"]
    assert thin_policy.project_state(state, "thin") == expected
    assert state == before == thin_policy.project_state(state)
    # No reference to nonexistent model intent is invented for actual B observations.
    ledger = {"evidence_ledger": {"recent_inspection_outcomes": [{"action_id": "r1"}]}}
    assert project_inspection_context(ledger, agent_policy="thin") == ledger


@pytest.mark.parametrize("update", [None, {"findings": [], "open_question": "public question"}, 7])
def test_actual_provider_annotations_round_trip_even_when_independently_invalid(update):
    arguments = {"path": "src.py", "start_line": 1, "end_line": 4, "memory_update": update}
    parsed = runner._requested_tool_from_openai(
        ProviderCall("read_file", "r1", arguments), agent_policy="thin",
    )
    restored = RequestedTool.model_validate(parsed.model_dump(mode="json"))
    assert "turn_decision" not in restored.model_fields_set
    assert runner._provider_tool_arguments(restored) == arguments
    assert runner._provider_rejected_call_arguments(restored) == arguments


@pytest.mark.parametrize("context", ["append-v1", "native-window-v1", "segmented-v1"])
def test_thin_mock_reaches_isolated_evaluation_and_rejects_cross_policy_resume(tmp_path, context):
    request = mock_request(tmp_path, "none").model_copy(update={
        "agent_policy": "thin", "context_policy": context,
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    journal, store = records(request)
    assert not any(e["event_type"].startswith("working_plan") for e in journal.events())
    envelope = json.loads(next((tmp_path / "runs").glob("*.envelope.json")).read_text())
    assert envelope["agent_policy"] == "thin"
    for event in journal.events():
        if event["event_type"] == "turn_started":
            items = runner._load_active_model_input(event["payload"], store, context_policy=context)
            assert items[0]["content"].startswith(thin_policy.SYSTEM_PROMPT)
            assert "Reuse current facts, notes, uncertainties and plans" not in items[0]["content"]
        if event["event_type"] == "action_started":
            assert "turn_decision" not in event["payload"]
            assert event["payload"]["memory_update"] is None
    before = journal.path.read_bytes()
    resumed = request.model_copy(update={"resume_run_id": journal.run_id})
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"agent_policy": "current"}))
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("incomplete", [False, True])
def test_thin_native_continuation_and_handoff_preserve_real_wire(tmp_path, monkeypatch, incomplete):
    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, incomplete_at=(1,) if incomplete else (),
    )
    request = request.model_copy(update={"agent_policy": "thin"})
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)
    assert len(inputs) == len(counted) == (5 if incomplete else 4)
    assert inputs == counted
    for view in views:
        assert "message" not in view["completion_guidance"]
        assert "next_action" not in view["completion_guidance"]
        assert "working_plan" not in view
        assert "message" not in (view["commitment_signal"] or {})
        for card in view["recent_attempt_result_next_question"]:
            assert "next_question" not in card and "turn_decision" not in card
    assert views[-1]["visible_check_status"][0]["status"] == "PASS"
    for items in inputs:
        for item in public_exchanges(items, archive_kind=PUBLIC_EVIDENCE_KIND):
            if item["type"] == "function_call":
                wire = json.loads(item["arguments"])
                assert "memory_update" in wire and "turn_decision" not in wire
    if incomplete:
        assert any(i.get("encrypted_content") == "cipher-1" for i in inputs[2])
    journal, store = records(request)
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before
    with pytest.raises(RecoveryError, match="agent policy changed"):
        segments.active(journal, store, agent_policy="current")


@pytest.mark.parametrize("boundary", ["provider_call_finished", "action_finished",
                                      "context_segment_started"])
def test_thin_interrupted_execution_resumes_without_repeated_work(tmp_path, monkeypatch, boundary):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"agent_policy": "thin"})

    def predicate(payload):
        if boundary == "provider_call_finished":
            return any(c["name"] == "replace_text" for c in payload["tool_calls"])
        if boundary == "action_finished":
            return payload["result"]["tool"] == "replace_text"
        return payload["reason"] != "initial"

    _crash_journal_once(monkeypatch, event_type=boundary, predicate=predicate,
                        when="before" if boundary == "action_finished" else "after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journal.run_id}))["runs"][0]
    assert_submitted(result)
    assert result["accepted_mutations"] == 1
    assert len(inputs) == len(counted) == 4


def test_scheduler_has_identical_completion_and_scarcity_decisions(gateway_factory):
    policies = []
    for policy in ("current", "thin"):
        gateway, _, _ = gateway_factory()
        gateway.agent_policy = policy
        gateway.sandbox = PassingSandbox()
        snapshots = []
        for step in (None, call(policy), mutation(policy), call(
            policy, "run_check", "check", {"check_id": gateway.public_task.visible_checks[0].id},
        )):
            if step is not None:
                assert gateway.execute(step).status == "succeeded"
            snapshots.append([runner._tool_policy(gateway, runner._RunCounters(
                model_calls=calls, tool_actions=actions), gateway.limits, repair_recheck=True)
                for calls, actions in ((0, 0), (37, 95), (39, 99))])
        policies.append(snapshots)
    assert policies[0] == policies[1]


def test_thin_probe_program_replay_binds_actual_root_annotation(gateway_factory):
    gateway, _, _ = gateway_factory()
    gateway.agent_policy = "thin"
    backend = FakeProbe(status="passed")
    gateway.probe_sandbox = backend

    def thin_probe(action, replay=None):
        original = probe(action, replay=replay, source="print('public-only')")
        return RequestedTool(name=original.name, action_id=action,
                             arguments=original.arguments, memory_update=None)

    original = gateway.execute(thin_probe("probe"))
    assert original.status == "succeeded"
    restored = restart(gateway, "thin")
    restored.probe_sandbox = backend
    replay = restored.execute(thin_probe("replay", replay="probe"))
    assert replay.status == "succeeded", replay
    assert replay.output["replayed_from"]["input_hash"] == original.input_hash
    assert replay.output["source_hash"] == original.output["source_hash"]
    assert not restored.checks_by_diff
    assert restored.execute(thin_probe("replay", replay="probe")).replayed
    assert backend.calls == 2


@pytest.mark.parametrize("annotations", [
    {}, {"turn_decision": None}, {"turn_decision": None, "memory_update": None},
    {"turn_decision": {"mode": "inspect", "basis": "bad", "evidence_goal": "unchanged"}},
    {"turn_decision": ["invalid shape"], "memory_update": None},
])
def test_malformed_thin_annotation_presence_survives_durable_round_trip(annotations):
    arguments = {"path": "src.py", "start_line": 1, "end_line": 4, **annotations}
    parsed = runner._requested_tool_from_openai(
        ProviderCall("read_file", "bad", arguments), agent_policy="thin",
    )
    restored = RequestedTool.model_validate_json(parsed.model_dump_json())
    assert runner._provider_rejected_call_arguments(restored) == arguments
    assert "preserve_annotation_presence" not in runner._provider_rejected_call_arguments(restored)


@pytest.mark.parametrize("repeated", [False, True])
def test_malformed_thin_native_call_is_preserved_and_correction_is_bounded(
    tmp_path, monkeypatch, repeated,
):
    request, inputs, counted, _ = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"agent_policy": "thin"})
    provider = runner.OpenAIResponsesAdapter
    execute = provider.execute_request
    malformed = {"path": "mini_data_utils/csvlite.py", "start_line": 1,
                 "end_line": 4, "turn_decision": None}

    def dispatch(self, payload, *, requested_input_tokens, timeout_seconds):
        if inputs and not repeated:
            return execute(self, payload, requested_input_tokens=requested_input_tokens,
                           timeout_seconds=timeout_seconds)
        number = len(inputs)
        inputs.append(copy.deepcopy(payload["input"]))
        action_id = f"bad-{number}"
        return ModelTurn(
            tool_calls=[ProviderCall("read_file", action_id, malformed)],
            input_tokens=requested_input_tokens, output_tokens=100,
            provider_continuation=(ProviderReasoning(f"r-bad-{number}", f"cipher-bad-{number}"),
                                   ProviderCallRef(action_id)),
        )

    monkeypatch.setattr(provider, "execute_request", dispatch)
    result = runner.run_dev(request)["runs"][0]
    if repeated:
        assert result["terminal"] == "PROTOCOL_VIOLATION", result
        assert result["call_counts"]["tool"] == 0
    else:
        assert_submitted(result)
    assert len(inputs) == len(counted) == (2 if repeated else 5)
    native = next(i for i in inputs[1] if i.get("call_id") == "bad-0"
                  and i.get("type") == "function_call")
    assert json.loads(native["arguments"]) == malformed
    journal, _ = records(request)
    assert sum(e["event_type"] == "protocol_correction" for e in journal.events()) == 1
