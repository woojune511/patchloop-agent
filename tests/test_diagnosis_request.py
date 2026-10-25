"""Host-owned diagnostic coordinates and exact recovery; no provider or Docker."""

import copy
import json

import pytest
from test_dev_tools import mutation_call
from test_repair_path_diagnosis import PATH, diagnosis, setup, state

from patchloop.dev import diagnosis_request
from patchloop.dev.tools import dev_tool_schemas
from patchloop.sandbox import call_path_trace as trace
from patchloop.util import sha256_json


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("diagnostic construction controls must not access the network")
    monkeypatch.setattr("socket.socket.connect", forbidden)


def symbolic(gateway, action="symbolic-diagnosis"):
    call = diagnosis(gateway, action)
    call.arguments["replay_action_id"] = None
    del call.arguments["call_path"]["call_id"]
    for watch in call.arguments["call_path"]["watches"]:
        del watch["lines"]
    return call


def test_model_schema_selects_functions_and_fields_without_host_coordinates():
    tool = dev_tool_schemas(finish_enabled=False, allowed_tools={"run_probe"})[0]
    properties = tool["parameters"]["properties"]
    shape = properties["call_path"]["anyOf"][1]
    assert set(shape["properties"]) == set(shape["required"]) == {"focus", "watches"}
    watch = shape["properties"]["watches"]["items"]
    assert set(watch["required"]) == {"origin", "path", "function", "fields"}
    assert "lines" not in watch["properties"]
    assert properties["python_source"]["maxLength"] == 8000
    assert properties["replay_action_id"]["maxLength"] == 500  # Ordinary replay remains.


def static_fixture(tmp_path):
    source = "# Public source is compiled, never executed.\n\n"
    source += "def selected(value):\n" + "".join(f"    value += {i}\n" for i in range(60))
    source += "    return value\n\ndef other():\n    return 'not selected'\n"
    source += "\nraise AssertionError('must never execute public source during binding')\n"
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    selection = {"focus": {"origin": "workspace", "path": "sample.py", "function": "selected"},
                 "watches": [{"origin": "workspace", "path": "sample.py",
                              "function": "selected", "fields": ["value"]}]}
    request = trace.selection_request(selection, "call-1")
    return path, request


def test_ast_selection_prioritizes_changed_body_lines_and_reports_omission(tmp_path):
    _, request = static_fixture(tmp_path)
    bound = trace.bind_request(request, tmp_path,
        line_changes=[{"path": "sample.py", "ranges": [[60, 64]]}])
    watch = bound["watches"][0]
    assert len(watch["lines"]) == trace.MAX_LINES == 32
    assert {60, 61, 62, 63, 64} <= set(watch["lines"])
    assert all(watch["def_line"] < n <= watch["last_line"] for n in watch["lines"])
    assert watch["line_selection"]["omitted_line_count"] == 29
    assert request["watches"][0]["lines"] == []  # Never mutates author/raw request.


def test_fixed_source_hash_rejects_drift_before_dispatch(tmp_path):
    path, request = static_fixture(tmp_path)
    bound = trace.bind_request(request, tmp_path, line_changes=[])
    request["focus"]["file_hash"] = bound["focus"]["file_hash"]
    request["watches"][0].update(lines=bound["watches"][0]["lines"],
                                 file_hash=bound["watches"][0]["file_hash"])
    path.write_bytes(path.read_bytes() + b"# changed outside selected function\n")
    with pytest.raises(ValueError, match="admitted bytes"):
        trace.bind_request(request, tmp_path)


def test_selection_omits_artificial_exception_lines_and_nested_function_body(tmp_path):
    path, request = static_fixture(tmp_path)
    path.write_text("def selected(value):\n"
                    "    def nested():\n        return value\n"
                    "    try:\n        return value[0]\n"
                    "    except IndexError:\n        return None\n", encoding="utf-8")
    watch = trace.bind_request(request, tmp_path, line_changes=[])["watches"][0]
    assert {5, 6, 7} <= set(watch["lines"])
    assert 3 not in watch["lines"]  # A different frame, not a missed outer branch.
    assert all(isinstance(line, int) and 1 < line <= 7 for line in watch["lines"])


@pytest.mark.parametrize("invalid", ["call_id", "lines", "file_hash", "private", "expression"])
def test_symbolic_request_cannot_supply_host_fields_or_unrestricted_targets(tmp_path, invalid):
    _, request = static_fixture(tmp_path)
    selection = {"focus": request["focus"], "watches": request["watches"]}
    del selection["watches"][0]["lines"]
    if invalid == "call_id":
        selection["call_id"] = "call-2"
    elif invalid in {"lines", "file_hash"}:
        selection["watches"][0][invalid] = [4] if invalid == "lines" else "sha256:" + "0" * 64
    elif invalid == "private":
        selection["watches"][0]["path"] = ".patchloop-hidden/secret.py"
    else:
        selection["watches"][0]["fields"] = ["value.__class__"]
    with pytest.raises(ValueError):
        trace.selection_request(selection, "call-1")


def test_symbolic_diagnosis_uses_original_root_and_retains_actual_trace(gateway_factory):
    gateway, journal, _, backend = setup(gateway_factory)
    call = symbolic(gateway)
    raw = copy.deepcopy(call.arguments)
    result = gateway.execute(call)
    assert result.status == "succeeded", result
    assert result.output["call_path"]["status"] == "complete"
    assert result.output["call_path"]["focus"]["entries"] == 1
    assert result.output["call_path"]["watches"][0]["not_observed_lines"]
    admission = result.output["diagnosis_request"]
    assert admission["replay_action_id"] == "original"
    assert result.output["replayed_from"]["action_id"] == "original"
    assert admission["call_path"]["call_id"] == "call-1"
    assert admission["call_path"]["watches"][0]["lines"]
    assert call.arguments == raw and raw["replay_action_id"] is None
    assert state(gateway)["status"] == "diagnosed"
    completion = gateway.completion_verification(diff_hash=gateway.current_diff_hash)
    assert completion["status"] == "refuted"  # Trace is not repair.
    started = next(e["payload"] for e in journal.events() if e["event_type"] == "action_started"
                   and e["payload"]["action_id"] == call.action_id)
    assert started["arguments"] == raw and started["diagnosis_request"] == admission
    assert result.output["call_path"]["raw_request_hash"] == sha256_json(admission["call_path"])
    assert gateway.execute(call).replayed and backend.calls == 3
    original = next(e["payload"]["result"] for e in journal.events()
                    if e["event_type"] == "action_finished"
                    and e["payload"]["action_id"] == "original")
    assert result.output["source_hash"] == original["output"]["source_hash"]
    assert result.output["reproduction"]["binding"] == original["output"]["reproduction"]["binding"]
    assert json.loads(result.output["reproduction"]["observed_json"])["bug_has_error"]


@pytest.mark.parametrize("boundary", ["admitted", "dispatched", "returned", "rejected"])
def test_symbolic_recovery_preserves_admission_and_never_repeats_execution(
    gateway_factory, monkeypatch, boundary,
):
    gateway, journal, _, backend = setup(gateway_factory)
    call = symbolic(gateway)
    if boundary == "rejected":
        call.arguments["replay_action_id"] = "failed-current"
    append = journal.append

    def crash(kind, payload):
        if (boundary in {"returned", "rejected"} and kind == "action_finished"
                and payload["action_id"] == call.action_id):
            raise KeyboardInterrupt("lost parent result")
        result = append(kind, payload)
        if (payload.get("action_id") == call.action_id
                and kind == {"admitted": "action_started", "dispatched": "probe_execution_started"
                             }.get(boundary)):
            raise KeyboardInterrupt("lost after durable admission/dispatch")
        return result

    journal.append = crash
    with pytest.raises(KeyboardInterrupt):
        gateway.execute(call)
    journal.append = append
    # Recovery must use the saved construction, not today's selection/projection.
    monkeypatch.setattr(diagnosis_request, "prepare",
                        lambda *_a, **_kw: pytest.fail("reconstructed pending diagnosis"))
    recovered = gateway.execute(call)
    if boundary == "dispatched":
        assert recovered.error_code == "RECOVERY_ERROR"
        assert recovered.output["execution_uncertain"] and backend.calls == 2
    elif boundary == "rejected":
        assert recovered.status == "failed" and backend.calls == 2
        assert state(gateway)["rejected_requests"] == 1
    else:
        assert recovered.status == "succeeded" and backend.calls == 3
        assert state(gateway)["status"] == "diagnosed"
    assert gateway.execute(call).replayed
    assert backend.calls == (2 if boundary in {"dispatched", "rejected"} else 3)


def test_pending_symbolic_diagnosis_rejects_source_change(gateway_factory):
    gateway, journal, workspace, backend = setup(gateway_factory)
    call = symbolic(gateway)
    append = journal.append

    def crash(kind, payload):
        result = append(kind, payload)
        if kind == "action_started" and payload["action_id"] == call.action_id:
            raise KeyboardInterrupt("lost after source binding")
        return result

    journal.append = crash
    with pytest.raises(KeyboardInterrupt):
        gateway.execute(call)
    journal.append = append
    path = workspace / PATH
    path.write_bytes(path.read_bytes() + b"\n# candidate changed\n")
    result = gateway.execute(call)
    assert result.status == "failed" and result.error_code == "RECOVERY_ERROR"
    assert backend.calls == 2


def test_unknown_symbolic_trace_does_not_release_another_repair(gateway_factory):
    gateway, _, _, backend = setup(gateway_factory)
    backend.unknown = True
    result = gateway.execute(symbolic(gateway))
    assert result.status == "succeeded" and result.output["call_path"]["status"] == "unknown"
    assert state(gateway)["status"] == "verification_incomplete"
    blocked = gateway.execute(mutation_call(gateway, action_id="unsupported-repair"))
    assert blocked.status == "failed"
    assert gateway.accepted_mutations == 1


def test_scripted_diagnosis_repair_reaches_isolated_mock_evaluation(
    tmp_path, monkeypatch, smoke_package,
):
    from test_dev_probe_cases import mock_request
    from test_dev_tools import read_calls
    from test_judgment_integration import diagnostic_probe
    from test_probe_purpose import probe
    from test_repair_path_diagnosis import TracedProbe

    from patchloop.dev import runner
    from patchloop.dev.contracts import DevModelTurn
    from patchloop.dev.model import MockDevAdapter
    from patchloop.dev.state import DevJournal

    backend = TracedProbe(status="passed")
    wrong = mutation_call(None, action_id="wrong-repair")
    wrong.arguments["new_text"] = wrong.arguments["old_text"].replace(
        "    rows: list[list[str]] = []", "    if text == '__unreached__':\n"
        "        return []\n    rows: list[list[str]] = []")
    fixed = mutation_call(None, action_id="diagnosed-repair", alternative=True)
    fixed.arguments["old_text"] = wrong.arguments["new_text"]
    selected = probe(smoke_package.public, "host-diagnosis", replay="original")
    selected.arguments["replay_action_id"] = None
    selected.arguments["call_path"] = {
        "focus": {"origin": "workspace", "path": PATH, "function": "parse_rows"},
        "watches": [{"origin": "workspace", "path": PATH, "function": "parse_rows",
                     "fields": ["text"]}],
    }
    steps = iter([read_calls()[1], diagnostic_probe(smoke_package.public, "original",
                  corrected=True), wrong, selected, fixed])

    class ScriptedDiagnosis(MockDevAdapter):
        def next_turn(self, context, tools):
            call = next(steps, None)
            if call is not None:
                assert call.name in {tool["name"] for tool in tools}
                return DevModelTurn(tool_calls=[call])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ScriptedDiagnosis)
    request = mock_request(tmp_path, "none").model_copy(update={"enable_probes": True})
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 4
    results = {event["payload"]["action_id"]: event["payload"]["result"]
               for event in DevJournal(tmp_path, result["run_id"]).events()
               if event["event_type"] == "action_finished"}
    assert results["host-diagnosis"]["output"]["call_path"]["status"] == "complete"
    assert results["diagnosed-repair"]["output"]["mutation"]["repair_path_link"][
        "diagnosis_action_id"] == "host-diagnosis"
    replays = [r["output"]["reproduction"]["comparison"] for action, r in results.items()
               if action.startswith("completion-reproduction-")]
    assert replays == ["mismatched", "matched"]  # Fresh automatic checks; finish reuses success.
    assert all(r["status"] == "succeeded" for r in results.values())
    assert result["evaluator"]["claim_eligible"] is False
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
