"""Several bounded public reads inform one diagnosis without changing failure credit."""

import json

import pytest
from test_dev_probe_action_replay import restore
from test_dev_segments import configured, records
from test_dev_tools import mutation_call, read_calls
from test_diagnosis_request import focused
from test_judgment_integration import diagnostic_probe
from test_probe_purpose import probe
from test_repair_path_diagnosis import PATH, TracedProbe, state

from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, RequestedTool
from patchloop.dev.native_sources import PUBLIC_EVIDENCE_KIND, _SourceIndex
from patchloop.dev.tools import validate_tool_batch
from patchloop.errors import ContractError

ENTRYPOINT = "mini_data_utils/__init__.py"
CALLER_TEST = "tests/test_csvlite.py"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("diagnosis exploration controls must remain offline")

    monkeypatch.setattr("socket.socket.connect", forbidden)


def preparation_reads():
    return [RequestedTool(name="read_file", action_id=action,
        preserve_annotation_presence=True,
        arguments={"path": path, "start_line": 1, "end_line": 80})
        for action, path in (("inspect-entrypoint", ENTRYPOINT),
                             ("inspect-caller-tests", CALLER_TEST),
                             ("inspect-focus", PATH))]


def wrong_edit():
    call = mutation_call(None, action_id="wrong-repair")
    call.arguments["new_text"] = call.arguments["old_text"].replace(
        "    rows: list[list[str]] = []", "    if text == '__unreached__':\n"
        "        return []\n    rows: list[list[str]] = []")
    return call


@pytest.mark.parametrize("ruleless", [False, True])
def test_several_reads_survive_recovery_before_one_linked_diagnosis(gateway_factory, ruleless):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = TracedProbe(status="passed")
    assert gateway.execute(read_calls()[1]).status == "succeeded"
    original = diagnostic_probe(gateway.public_task, "original", corrected=True, legacy=ruleless)
    if ruleless:
        original.arguments["purpose"]["diagnostic_rules"] = None
    assert gateway.execute(original).status == "succeeded"
    wrong = wrong_edit()
    assert gateway.execute(wrong).status == "succeeded"
    assert gateway.execute(probe(gateway.public_task, "failed-current", replay="original")).output[
        "reproduction"]["comparison"] == "mismatched"
    initial = state(gateway)
    reads = preparation_reads()
    with pytest.raises(ContractError):
        validate_tool_batch([reads[0], focused()], path_diagnosis_pending=True)
    for index, read in enumerate(reads):
        assert validate_tool_batch([read], path_diagnosis_pending=True) == "parallel_read"
        assert gateway.execute(read).status == "succeeded"
        if index == 0:
            gateway = restore(gateway, journal, workspace, gateway.public_task, backend)
            durable = journal.path.read_bytes()
            assert gateway.execute(read).replayed
            assert journal.path.read_bytes() == durable
        current = state(gateway)
        assert current["status"] == "needs_path_diagnosis" and current["preparation_available"]
        assert current["preparation_action_ids"] == [item.action_id for item in reads[:index + 1]]
        assert not current["execution_attempted"] and current["rejected_requests"] == 0
        assert current["case_id"] == initial["case_id"]
        assert current["failure_action_id"] == initial["failure_action_id"]
        assert gateway.completion_verification(diff_hash=gateway.current_diff_hash)["status"] == (
            "refuted")
        assert backend.calls == 2
    diagnosis = focused("one-diagnosis")
    if ruleless:
        diagnosis.arguments["call_id"] = "call-1"
    diagnosed = gateway.execute(diagnosis)
    assert diagnosed.status == "succeeded" and diagnosed.output["call_path"]["status"] == "complete"
    assert state(gateway)["status"] == "diagnosed" and backend.calls == 3
    assert gateway.execute(diagnosis).replayed and backend.calls == 3
    assert gateway.completion_verification(diff_hash=gateway.current_diff_hash)["status"] == (
        "refuted")
    fixed = mutation_call(gateway, action_id="repair-after-exploration", alternative=True)
    fixed.arguments["old_text"] = wrong.arguments["new_text"]
    fixed.arguments.pop("causal_revision")
    fixed.arguments["repair_prediction"] = {
        "kind": "source", "target": -1, "event": "original_failure_absent"}
    repaired = gateway.execute(fixed)
    assert repaired.status == "succeeded", repaired
    link = repaired.output["mutation"]["repair_path_link"]
    assert link["diagnosis_action_id"] == diagnosis.action_id
    assert link["case_id"] == initial["case_id"] and link["call_id"] == "call-1"
    assert backend.calls == 3  # Source reads and mutation never manufacture another diagnosis.


def test_next_diagnostic_request_retains_entrypoint_and_caller_test_source(
    tmp_path, monkeypatch, smoke_package,
):
    backend = TracedProbe(status="passed")
    reads = preparation_reads()
    stop = RequestedTool(name="stop_task", action_id="stop-after-diagnosis", arguments={
        "reason_code": "insufficient_public_evidence",
        "summary": "Local source-delivery control ends without claiming a repair.",
    })
    steps = iter([read_calls()[1], diagnostic_probe(smoke_package.public, "original",
                                                   corrected=True),
                  wrong_edit(), *reads, focused("one-diagnosis"), stop])

    class Script:
        def next_turn(self, context, tools):
            call = next(steps)
            view = json.loads(context)
            assert call.name in {tool["name"] for tool in tools}
            if call.action_id == "one-diagnosis":
                assert view["diagnosis_stage"]["path"]["preparation_action_ids"] == [
                    read.action_id for read in reads]
                assert view["diagnosis_stage"]["observations"][-1]["comparison"] == "mismatched"
            return DevModelTurn(tool_calls=[call])

    request, inputs, counted, views = configured(monkeypatch, tmp_path, script=Script())
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    request = request.model_copy(update={"enable_probes": True})
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "AGENT_STOPPED" and result["accepted_mutations"] == 1
    assert backend.calls == 3 and len(inputs) == len(counted) == 8
    before_diagnosis = views[6]
    assert before_diagnosis["workflow_gate"] == "needs_path_diagnosis"
    # The actual request may retain bodies inline or refer to native tool outputs.
    # Both are public evidence; compact source headers alone are not source delivery.
    retained = {
        group["path"]: "\n".join(span["content"] for span in group.get("inline_spans", []))
        for group in before_diagnosis["current_sources"]
        if group.get("inline_spans")
    }
    source = _SourceIndex(inputs[6], archive_kind=PUBLIC_EVIDENCE_KIND)
    for (path, _), lines in source.observed.items():
        retained[path] = retained.get(path, "") + "\n".join(
            value[0] for _, value in sorted(lines.items()))
    assert {ENTRYPOINT, CALLER_TEST, PATH} <= retained.keys()
    assert "from mini_data_utils.csvlite import parse_rows" in retained[ENTRYPOINT]
    assert "def test_preserves_quoted_comma" in retained[CALLER_TEST]
    for earlier, later in zip(views[3:6], views[4:7], strict=True):
        assert later["remaining_budget"]["model_calls"] == (
            earlier["remaining_budget"]["model_calls"] - 1)
        assert later["diagnosis_stage"]["path"]["status"] == "needs_path_diagnosis"
    journal, _ = records(request)
    assert all(len(event["payload"]["tool_calls"]) == 1 for event in journal.events()
               if event["event_type"] == "tool_batch_started")
    assert not any(event["event_type"] == "evaluator_finished" for event in journal.events())
