"""Original-call diagnosis and repair linkage, using tiny trusted local programs."""

import copy
import json
import sys

import pytest
from test_dev_probes import FakeProbe
from test_dev_tools import mutation_call, read_calls
from test_finish_reproduction import finish_call
from test_judgment_integration import diagnostic_probe
from test_probe_purpose import probe

from patchloop.contracts import RegisteredCheck
from patchloop.dev import repair_path
from patchloop.dev.contracts import RequestedTool
from patchloop.sandbox import LocalSandbox, call_path_trace
from patchloop.util import sha256_json

PATH = "mini_data_utils/csvlite.py"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("call-path local controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


class TracedProbe(FakeProbe):
    """Fixture-only backend: production still requires the Docker probe sandbox."""

    supports_public_execution = True
    unknown = False

    def validate_call_path(self, workspace, request, *, deadline=None, line_changes=None):
        del deadline
        return call_path_trace.bind_request(request, workspace, line_changes=line_changes)

    def run_probe(self, workspace, question, python_source, *, deadline, execution_identity,
                  execution_targets=None, call_path_request=None):
        receipt = super().run_probe(workspace, question, python_source, deadline=deadline,
                                    execution_identity=execution_identity)
        # Local -c and traced launch differ in sys.path[0]; hold this fixture's
        # import condition fixed instead of weakening production comparability.
        prefix = f"import sys\nsys.path[0] = {str(workspace)!r}\n"
        source = prefix + python_source
        bound = None
        if call_path_request is not None:
            bound = call_path_trace.bind_request(
                call_path_request, workspace, snapshot_hash=receipt["snapshot_hash"],
                execution_identity_hash=sha256_json(execution_identity))
            # This wrapper is trusted fixture code; only source inside the fixture runs.
            source = prefix + (
                f"_trace_namespace = {{'__file__': {str(call_path_trace.WRAPPER)!r}, "
                "'__name__': 'fixture_trace'}\n"
                f"exec(compile(open({str(call_path_trace.WRAPPER)!r}, encoding='utf-8').read(), "
                "'<fixture-tracer>', 'exec'), _trace_namespace)\n"
                "from types import SimpleNamespace\n"
                f"_fixture_trace = _trace_namespace['CallPathTrace']({bound!r}, "
                f"{{'workspace': {str(workspace)!r}}}, "
                "line_trace=SimpleNamespace(trace=sys.gettrace()))\n"
                "_patchloop_call_path_begin = _fixture_trace.begin\n"
                "_patchloop_call_path_end = _fixture_trace.end\n"
                f"exec({python_source!r})\n_fixture_trace.finish()\n"
            )
        result = LocalSandbox().run_check(workspace, RegisteredCheck(
            id="tiny-path-control", command=[sys.executable, "-c", source], timeout_seconds=10,
        ), execution_identity=execution_identity, execution_targets=execution_targets)
        stderr = result.stderr
        if bound is not None:
            prefix = call_path_trace.marker(bound).decode()
            assert prefix in stderr, (result.stdout, stderr)
            start = stderr.index(prefix)
            payload, _, tail = stderr[start + len(prefix):].partition("\n")
            report = json.loads(payload)
            if self.unknown:
                report.update(status="unknown", reason="collector_truncated")
            receipt["call_path"] = call_path_trace.public_feedback(bound, report)
            stderr = stderr[:start] + tail
        return {**receipt, "status": "passed" if result.passed else "failed",
                "exit_code": result.exit_code, "stdout": result.stdout, "stderr": stderr,
                "public_execution": result.public_execution}


def state(gateway):
    return gateway.completion_verification(diff_hash=gateway.current_diff_hash)["repair_path"]


def setup(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    backend = gateway.probe_sandbox = TracedProbe(status="passed")
    assert gateway.execute(read_calls()[1]).status == "succeeded"
    result = gateway.execute(diagnostic_probe(gateway.public_task, "original", corrected=True))
    assert result.output["reproduction"]["declared_failure_comparison"] == "matched"
    edit = mutation_call(gateway, action_id="wrong-repair")
    edit.arguments["new_text"] = edit.arguments["old_text"].replace(
        "    rows: list[list[str]] = []", "    if text == '__unreached__':\n"
        "        return []\n    rows: list[list[str]] = []")
    assert gateway.execute(edit).status == "succeeded"
    replay = gateway.execute(probe(gateway.public_task, "failed-current", replay="original"))
    assert replay.output["reproduction"]["comparison"] == "mismatched"
    assert state(gateway)["status"] == "needs_path_diagnosis", state(gateway)
    return gateway, journal, workspace, backend


def diagnosis(gateway, action="path-diagnosis"):
    current = state(gateway)
    lines = [start for start, _ in current["unobserved_changes"][0]["ranges"]]
    call = probe(gateway.public_task, action, replay="original")
    call.arguments["call_path"] = {
        "call_id": "call-1", "focus": {"origin": "workspace", "path": PATH,
                                       "function": "parse_rows"},
        "watches": [{"origin": "workspace", "path": PATH, "function": "parse_rows",
                     "lines": lines, "fields": ["text"]}],
    }
    return call


def test_failed_repair_requires_path_then_links_next_hypothesis(gateway_factory):
    gateway, journal, _, backend = setup(gateway_factory)
    blocked = gateway.execute(mutation_call(gateway, action_id="premature"))
    assert blocked.status == "failed" and gateway.accepted_mutations == 1
    assert gateway.execute(finish_call()).status == "failed"
    # One source preparation does not consume the actual diagnostic attempt.
    read = read_calls()[1].model_copy(update={"action_id": "path-read"})
    assert gateway.execute(read).status == "succeeded"
    assert not state(gateway)["preparation_available"] and not state(gateway)["execution_attempted"]
    assert gateway.execute(read.model_copy(update={"action_id": "extra-read"})).status == "failed"
    result = gateway.execute(diagnosis(gateway))
    assert result.status == "succeeded", result
    trace = result.output["call_path"]
    assert trace["status"] == "complete"
    assert trace["focus"]["entries"] == 1  # Control is a separate call.
    assert trace["watches"][0]["not_observed_lines"]
    assert state(gateway)["status"] == "diagnosed"
    retained = state(gateway)["diagnosis_observation"]
    assert retained["focus"]["entries"] == 1
    assert retained["watches"][0]["not_observed_lines"]
    completion = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert completion["status"] == "refuted"
    assert gateway.execute(diagnosis(gateway)).replayed and backend.calls == 3
    fixed = mutation_call(gateway, action_id="repair-from-diagnosis", alternative=True)
    fixed.arguments["old_text"] = next(
        e["payload"]["arguments"]["new_text"] for e in journal.events()
        if e["event_type"] == "action_started" and e["payload"]["action_id"] == "wrong-repair")
    missing = fixed.model_copy(deep=True, update={"action_id": "missing-hypothesis"})
    missing.arguments["hypothesis"] = ""
    assert gateway.execute(missing).status == "failed"
    fixed.arguments.pop("causal_revision")
    repaired = gateway.execute(fixed)
    assert repaired.status == "succeeded", repaired
    assert repaired.output["mutation"]["repair_path_link"]["diagnosis_action_id"] == (
        "path-diagnosis")
    assert state(gateway)["status"] == "not_needed"
    checked = gateway.execute(probe(gateway.public_task, "fixed-original", replay="original"))
    assert checked.output["reproduction"]["comparison"] == "matched"


@pytest.mark.parametrize("source_error", [False, True])
def test_rejected_request_can_be_corrected_without_an_execution(gateway_factory, source_error):
    gateway, _, _, backend = setup(gateway_factory)
    bad = diagnosis(gateway, "bad-request")
    if source_error:
        bad.arguments["call_path"]["focus"]["function"] = "missing_function"
    else:
        bad.arguments["call_path"]["call_id"] = "call-2"
    assert gateway.execute(bad).status == "failed"
    assert backend.calls == 2 and state(gateway)["rejected_requests"] == 1
    assert gateway.execute(bad).replayed
    assert state(gateway)["rejected_requests"] == 1
    good = gateway.execute(diagnosis(gateway))
    assert good.status == "succeeded" and state(gateway)["status"] == "diagnosed"


@pytest.mark.parametrize("mode", ["unknown", "rejections", "pending_execution"])
def test_bounded_failure_stays_incomplete_without_more_mutations(gateway_factory, mode):
    gateway, journal, _, backend = setup(gateway_factory)
    call = diagnosis(gateway)
    if mode == "unknown":
        backend.unknown = True
        assert gateway.execute(call).status == "succeeded"
    elif mode == "rejections":
        call.arguments["call_path"]["call_id"] = "call-2"
        assert gateway.execute(call).status == "failed"
        second = gateway.execute(call.model_copy(update={"action_id": "second-bad"}))
        assert second.status == "failed"
    else:
        append = journal.append
        def crash(kind, payload):
            result = append(kind, payload)
            if kind == "probe_execution_started":
                raise KeyboardInterrupt("synthetic crash after durable dispatch start")
            return result
        journal.append = crash
        with pytest.raises(KeyboardInterrupt):
            gateway.execute(call)
        journal.append = append
        recovered = gateway.execute(call)
        assert recovered.output["execution_uncertain"]
    assert state(gateway)["status"] == "verification_incomplete"
    calls = backend.calls
    assert gateway.execute(diagnosis(gateway, "retry-diagnosis")).status == "failed"
    assert gateway.execute(mutation_call(gateway, action_id="speculative-edit")).status == "failed"
    assert backend.calls == calls and gateway.accepted_mutations == 1


def test_finished_execution_recovers_without_duplicate_diagnosis(gateway_factory):
    gateway, journal, _, backend = setup(gateway_factory)
    call = diagnosis(gateway)
    append = journal.append
    def crash(kind, payload):
        if kind == "action_finished" and payload["action_id"] == call.action_id:
            raise KeyboardInterrupt("synthetic crash before parent receipt")
        return append(kind, payload)
    journal.append = crash
    with pytest.raises(KeyboardInterrupt):
        gateway.execute(call)
    journal.append = append
    assert backend.calls == 3
    assert gateway.execute(call).status == "succeeded"
    assert backend.calls == 3 and state(gateway)["status"] == "diagnosed"


@pytest.mark.parametrize("condition", ["trace_unknown", "file_changed", "helper", "different_call"])
def test_only_bound_original_and_measured_changed_branch_trigger_diagnosis(
    gateway_factory, condition,
):
    gateway, journal, _, _ = setup(gateway_factory)
    events = copy.deepcopy(journal.events())
    failure = next(e["payload"]["result"] for e in events if e["event_type"] == "action_finished"
                   and e["payload"]["action_id"] == "failed-current")
    if condition == "trace_unknown":
        failure["output"]["public_execution"]["files"][0]["status"] = "unknown"
    elif condition == "file_changed":
        failure["output"]["public_execution"]["files"][0]["file_hash"] = "other"
    elif condition == "helper":
        del failure["output"]["reproduction"]
    else:
        failure["output"]["reproduction"]["call_observation"]["calls"][0]["arguments"][
            "args"] = ["other"]
    completed = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert repair_path.review(events, gateway.current_diff_hash, completed)["status"] == (
        "not_needed")


def test_call_path_cannot_be_added_to_helper(gateway_factory):
    gateway, _, _ = gateway_factory()
    gateway.probe_sandbox = TracedProbe(status="passed")
    call = RequestedTool(name="run_probe", action_id="unbound", arguments={
        "question": "helper", "python_source": "print('helper')", "call_path": {},
    })
    assert gateway.execute(call).status == "failed" and gateway.probe_sandbox.calls == 0
