"""Focused public diagnosis and recovery with a fake provider and tiny local code."""

import copy
from types import SimpleNamespace

import pytest
from test_dev_runner import _crash_journal_once, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from test_dev_tools import mutation_call, read_calls
from test_diagnosis_request import focused
from test_judgment_integration import diagnostic_probe
from test_repair_path_diagnosis import TracedProbe

from patchloop.dev import diagnosis_request, runner, segments
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.tools import validate_tool_batch
from patchloop.util import canonical_json, sha256_bytes


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("diagnosis context controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def test_watch_plan_uses_nested_function_frame_and_reports_unsupported_source():
    source = (b"class C:\n    def outer(self, x):\n        def inner(y):\n"
              b"            return y\n        return inner(x)\n")
    state = {"unobserved_changes": [{"path": "public.py", "file_hash": sha256_bytes(source),
                                      "ranges": [[4, 4]]}]}
    plan = diagnosis_request.watch_plan(state, lambda _: source)
    assert plan["watches"] == [{"origin": "workspace", "path": "public.py",
                                 "function": "C.outer.inner", "fields": ["y"]}]
    state["unobserved_changes"][0]["ranges"] = [[1, 1]]
    assert diagnosis_request.watch_plan(state, lambda _: source)["status"] == "unavailable"
    state["unobserved_changes"][0]["ranges"] = [[4, 4]]
    assert diagnosis_request.watch_plan(state, lambda _: source + b"# drift")["status"] == (
        "unavailable")


@pytest.mark.parametrize("agent_policy", ["current", "thin"])
def test_provider_focus_roundtrip_has_no_synthetic_annotations(agent_policy):
    original = focused()
    call = runner._requested_tool_from_openai(SimpleNamespace(
        name=original.name, action_id=original.action_id, arguments=original.arguments),
        agent_policy=agent_policy, path_diagnosis_pending=True)
    restored = RequestedTool.model_validate(call.model_dump(mode="json"))
    assert runner._provider_tool_arguments(restored) == original.arguments
    assert not {"turn_decision", "memory_update"} & restored.model_fields_set
    assert validate_tool_batch([restored], agent_policy=agent_policy,
                               path_diagnosis_pending=True) == "single_action"


def stage_run(monkeypatch, tmp_path, smoke_package, failure):
    backend = TracedProbe(status="passed")
    wrong = mutation_call(None, action_id="wrong-repair")
    wrong.arguments["new_text"] = wrong.arguments["old_text"].replace(
        "    rows: list[list[str]] = []", "    if text == '__unreached__':\n"
        "        return []\n    rows: list[list[str]] = []")
    fixed = mutation_call(None, action_id="diagnosed-repair", alternative=True)
    fixed.arguments["old_text"] = wrong.arguments["new_text"]
    correction_step = []
    if failure == "missing_tool":
        correction_step = [DevModelTurn(tool_calls=[])]
    elif failure == "request_fields":
        invalid = focused("invalid-fields")
        invalid.arguments["question"] = None
        correction_step = [DevModelTurn(tool_calls=[invalid])]
    first = read_calls()[1]
    first.turn_decision.plan_update = (
        "Observe original, diagnose the missed branch, repair and verify.")
    steps = iter([DevModelTurn(tool_calls=[c]) for c in [first, diagnostic_probe(
        smoke_package.public, "original", corrected=True), wrong]] + correction_step
        + [DevModelTurn(tool_calls=[focused()]), DevModelTurn(tool_calls=[fixed])])

    class Script(MockDevAdapter):
        def next_turn(self, context, tools):
            return next(steps, None) or super().next_turn(context, tools)

    request, inputs, counted, views = configured(
        monkeypatch, tmp_path, planning="brief-v1", script=Script("csv-quoted-newline"),
        incomplete_at=((3, 4) if failure == "exhausted" else
                       (3,) if failure == "incomplete_response" else ()))
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    return (request.model_copy(update={"enable_probes": True}), inputs, counted, views, backend)


@pytest.mark.parametrize("failure", ["incomplete_response", "missing_tool", "request_fields"])
def test_diagnosis_stage_correction_and_return_preserve_budgets(
    tmp_path, monkeypatch, smoke_package, failure,
):
    request, inputs, counted, views, backend = stage_run(
        monkeypatch, tmp_path, smoke_package, failure)
    assert_submitted(runner.run_dev(request)["runs"][0])
    assert backend.calls == 4 and len(inputs) == len(counted)
    before, corrected, returned = views[3:6]
    assert before["workflow_gate"] == corrected["workflow_gate"] == "needs_path_diagnosis"
    assert returned["workflow_gate"] != "needs_path_diagnosis"
    for index in (3, 4):
        assert "working_plan" not in views[index] and "working_notes" not in views[index]
        assert "reconsider model-authored notes" not in inputs[index][0]["content"]
        assert views[index]["diagnosis_stage"]["host_watches"]["status"] == "ready"
        assert views[index]["diagnosis_stage"]["path"]["call_id"] == "call-1"
        assert len(views[index]["diagnosis_stage"]["observations"]) == 2
    assert "working_plan" in returned and "diagnosis_stage" not in returned
    assert returned["working_plan"]["plan"]["text"] == views[2]["working_plan"]["plan"]["text"]
    assert returned["working_plan"]["plan"]["text"] not in canonical_json(inputs[3])
    assert before["diagnosis_stage"] == corrected["diagnosis_stage"]
    assert corrected["remaining_budget"]["model_calls"] == before["remaining_budget"][
        "model_calls"] - 1
    assert corrected["remaining_budget"]["tool_actions"] == before["remaining_budget"][
        "tool_actions"]
    assert corrected["remaining_budget"]["consecutive_protocol_corrections"] == 0
    assert corrected["remaining_budget"]["cost"]["settled_usage"] > before[
        "remaining_budget"]["cost"]["settled_usage"]
    correction = corrected["protocol_correction"]["diagnosis_correction"]
    if failure == "request_fields":
        assert correction["kind"] == "request_fields" and not correction["fresh_segment"]
        assert before["segment_handoff"]["segment_id"] == corrected["segment_handoff"]["segment_id"]
    else:
        assert correction["kind"] == "no_action" and correction["fresh_segment"]
        assert corrected["segment_handoff"]["reason"] == "path_diagnosis_no_action"
        assert not any(i.get("type") == "reasoning" for i in inputs[4])
    journal, _ = records(request)
    assert sum(e["event_type"] == "protocol_correction" for e in journal.events()) == 1
    assert not any(e["event_type"] == "working_plan_updated" and e["payload"].get("turn_id")
                   in {r["payload"]["turn_id"] for r in journal.events()
                       if r["event_type"] == "turn_started"
                       and r["payload"]["workflow_gate"] == "needs_path_diagnosis"}
                   for e in journal.events())


@pytest.mark.parametrize("boundary", [
    "protocol_correction", "context_segment_started", "action_finished",
])
def test_diagnosis_fresh_correction_recovers_once(tmp_path, monkeypatch, smoke_package, boundary):
    request, inputs, counted, views, backend = stage_run(
        monkeypatch, tmp_path, smoke_package, "incomplete_response")
    _crash_journal_once(monkeypatch, event_type=boundary, when="after", predicate=lambda p:
        p.get("workflow_gate") == "needs_path_diagnosis" if boundary == "protocol_correction"
        else p.get("action_id") == "host-diagnosis" if boundary == "action_finished"
        else p["reason"] == "path_diagnosis_no_action")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    journal, _ = records(request)
    assert_submitted(runner.run_dev(request.model_copy(update={
        "resume_run_id": journal.run_id}))["runs"][0])
    assert backend.calls == 4 and len(inputs) == len(counted)
    assert views[4]["protocol_correction"]["diagnosis_correction"]["kind"] == "no_action"
    assert views[4]["remaining_budget"]["consecutive_protocol_corrections"] == 0
    assert sum(e["event_type"] == segments.EVENT and e["payload"]["reason"] == (
        "path_diagnosis_no_action") for e in journal.events()) == 1


def test_repeated_no_action_cannot_refill_the_correction_allowance(
    tmp_path, monkeypatch, smoke_package,
):
    request, inputs, _, _, backend = stage_run(monkeypatch, tmp_path, smoke_package, "exhausted")
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "VERIFICATION_INCOMPLETE", result
    assert len(inputs) == 5 and backend.calls == 2
    journal, _ = records(request)
    assert not any(e["event_type"] in {"submission_recorded", "evaluator_finished"}
                   for e in journal.events())
    assert sum(e["event_type"] == "protocol_correction" for e in journal.events()) == 1


def test_unknown_trace_stays_incomplete_with_host_watches(gateway_factory):
    from test_repair_path_diagnosis import setup, state
    gateway, _, _, backend = setup(gateway_factory)
    backend.unknown = True
    original = copy.deepcopy(focused().arguments)
    result = gateway.execute(focused())
    assert result.output["call_path"]["status"] == "unknown"
    assert state(gateway)["status"] == "verification_incomplete"
    assert canonical_json(original) == canonical_json(focused().arguments)
