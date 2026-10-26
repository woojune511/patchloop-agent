"""Host-owned diagnostic coordinates and exact recovery; no provider or Docker."""

import copy
import json

import pytest
from test_dev_tools import mutation_call
from test_repair_path_diagnosis import PATH, diagnosis, setup, state

from patchloop.dev import diagnosis_request, probe_cases
from patchloop.dev.contracts import RequestedTool
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.errors import ContractError
from patchloop.sandbox import call_path_trace as trace
from patchloop.util import sha256_bytes, sha256_json


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


def focused(action="host-diagnosis", function="parse_rows"):
    return RequestedTool(name="run_probe", action_id=action, preserve_annotation_presence=True,
                         arguments={"focus": {"origin": "workspace", "path": PATH,
                                               "function": function}})


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
    assert [tool] == dev_tool_schemas(
        finish_enabled=False, allowed_tools={"run_probe"}, path_diagnosis_pending=False)


@pytest.mark.parametrize("probe_policy", ["none", *sorted(probe_cases.POLICIES)])
@pytest.mark.parametrize("agent_policy", ["current", "thin"])
def test_pending_schema_allows_only_diagnostic_selection(probe_policy, agent_policy):
    tool = dev_tool_schemas(
        finish_enabled=False, allowed_tools={"run_probe"}, probe_policy=probe_policy,
        agent_policy=agent_policy, path_diagnosis_pending=True,
    )[0]
    parameters = tool["parameters"]
    properties = parameters["properties"]
    assert set(parameters["required"]) == set(properties) == {"focus"}
    assert set(properties["focus"]["required"]) == {"origin", "path", "function"}
    assert validate_tool_batch([focused()], agent_policy=agent_policy,
                               path_diagnosis_pending=True) == "single_action"
    assert parameters["additionalProperties"] is False
    assert len(tool["description"]) < 1_200
    assert "observed_target" not in tool["description"]
    assert "Choose purpose" not in tool["description"]


@pytest.mark.parametrize("extra", ["turn_decision", "memory_update", "question", "call_path"])
def test_diagnosis_validator_matches_the_small_schema(extra):
    call = focused()
    if extra in {"turn_decision", "memory_update"}:
        call = call.model_copy(update={extra: None})
    else:
        call.arguments[extra] = None
    with pytest.raises(ContractError, match="diagnosis"):
        validate_tool_batch([call], path_diagnosis_pending=True)
    with pytest.raises(ContractError):
        validate_tool_batch([focused()])  # General mode still requires a decision.


def test_focus_field_errors_do_not_suggest_incompatible_legacy_nulls():
    arguments = {**focused().arguments, "purpose": {"kind": "helper"}}
    with pytest.raises(ContractError) as caught:
        diagnosis_request.prepare(arguments, {"status": "needs_path_diagnosis"}, None, None)
    assert caught.value.details["invalid_fields"] == [
        {"path": "/purpose", "requirement": "only focus is accepted"}]


@pytest.mark.parametrize("agent_policy", ["current", "thin"])
def test_other_offered_diagnosis_tools_share_annotation_absence(agent_policy):
    names = {"read_file", "search_files", "stop_task"}
    tools = dev_tool_schemas(finish_enabled=False, allowed_tools=names,
                             path_diagnosis_pending=True, agent_policy=agent_policy)
    for tool in tools:
        assert not {"turn_decision", "memory_update"} & set(tool["parameters"]["properties"])
        call = RequestedTool(name=tool["name"], action_id=tool["name"],
                             preserve_annotation_presence=True)
        validate_tool_batch([call], allowed_tools=names, path_diagnosis_pending=True,
                            agent_policy=agent_policy)


@pytest.mark.parametrize(("key", "value", "required_value"), [
    ("question", "Which caller reaches this branch?", "null"),
    ("python_source", "print('new program')", "null"),
    ("replay_action_id", "another-call", "null"),
    ("purpose", {"kind": "helper"}, "null"),
    ("reproduction", {}, "null"),
    ("case_id", "case-1", "null"),
    ("reference_action_id", "prior-call", "null"),
    ("save_program", True, "false"),
])
def test_incompatible_fields_are_identified_before_source_construction(key, value, required_value):
    def unexpected_preflight(*_args, **_kwargs):
        pytest.fail("invalid fields must be rejected before source construction")

    with pytest.raises(ContractError) as caught:
        diagnosis_request.prepare({key: value}, {"status": "needs_path_diagnosis"},
                                  None, unexpected_preflight)
    fields = caught.value.details["invalid_fields"]
    assert len(fields) == 1 and fields[0]["path"] == f"/{key}"
    assert f"must be {required_value}" in fields[0]["requirement"]
    assert f"/{key}" in str(caught.value)


@pytest.mark.parametrize("probe_policy", ["none", *sorted(probe_cases.POLICIES)])
def test_gateway_keeps_diagnosis_errors_before_other_probe_preparation(
    gateway_factory, probe_policy,
):
    from test_probe_purpose import probe

    gateway, _, _, backend = setup(gateway_factory)
    gateway.probe_policy = probe_policy
    call = symbolic(gateway, "incompatible-fields")
    call.arguments.update(question="Which path ran?",
                          purpose=probe(gateway.public_task).arguments["purpose"])
    expected = ["/question", "/purpose"]
    if probe_policy == "none":
        call.arguments["replay_action_id"] = "unknown-root"
        expected.insert(1, "/replay_action_id")
    result = gateway.execute(call)
    assert result.status == "failed" and result.output["probe_stage"] == "preflight_rejected"
    assert [f["path"] for f in result.output["invalid_fields"]] == expected
    assert all(path in result.message for path in expected)
    assert backend.calls == 2 and state(gateway)["rejected_requests"] == 1
    assert not state(gateway)["execution_attempted"]
    assert gateway.execute(call).replayed and backend.calls == 2


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
    assert "scope" not in admission["call_path"]  # Saved symbolic shape keeps focus scope.
    assert result.output["call_path"]["scope"] == "selected_call_focus_launch_thread"
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


def test_host_watches_follow_the_mutation_and_keep_raw_focus_identity(gateway_factory):
    gateway, journal, _, backend = setup(gateway_factory)
    call = focused()
    raw = copy.deepcopy(call.arguments)
    result = gateway.execute(call)
    assert result.status == "succeeded", result
    admission = result.output["diagnosis_request"]
    assert admission["host_watches"]["watches"] == [
        {"origin": "workspace", "path": PATH, "function": "parse_rows", "fields": ["text"]}]
    assert admission["call_path"]["call_id"] == "call-1"
    assert admission["call_path"]["scope"] == "selected_call"
    assert result.output["call_path"]["scope"] == "selected_call_launch_thread"
    assert call.arguments == raw and state(gateway)["status"] == "diagnosed"
    start = next(e["payload"] for e in journal.events() if e["event_type"] == "action_started"
                 and e["payload"]["action_id"] == call.action_id)
    assert start["arguments"] == raw and start["diagnosis_request"] == admission
    assert result.output["call_path"]["raw_request_hash"] == sha256_json(admission["call_path"])
    assert "scope" not in raw
    assert gateway.execute(call).replayed and backend.calls == 3


@pytest.mark.parametrize("call_focus", [False, True])
def test_fresh_diagnosis_observes_changed_function_outside_focus(tmp_path, call_focus):
    source = ("def focus(value):\n    return value\n\n"
              "def changed(value):\n    if value:\n        return 'new'\n"
              "    return 'original'\n")
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    pending = {"status": "needs_path_diagnosis", "blocked": True,
               "policy": "repair-call-path-v1", "candidate_diff_hash": "candidate",
               "case_id": "case", "replay_action_id": "original", "failure_action_id": "failed",
               "mutation_action_id": "edit", "call_id": "call-1", "unobserved_changes": [{
                   "path": "sample.py", "file_hash": sha256_bytes(path.read_bytes()),
                   "ranges": [[6, 6]]}]}
    raw = {"focus": {"origin": "workspace", "path": "sample.py", "function": "focus"}}

    def preflight(workspace, request, *, deadline=None, line_changes=None):
        del deadline
        return trace.bind_request(request, workspace, line_changes=line_changes)

    admission = diagnosis_request.prepare(
        raw, pending, tmp_path, preflight, read_source=lambda name: (tmp_path / name).read_bytes())
    request = admission["call_path"]
    assert request["scope"] == "selected_call"
    assert request["watches"][0]["function"] == "changed"
    bound = trace.bind_request(request, tmp_path)
    namespace = {"__name__": "diagnosis_scope_fixture"}
    exec(compile(source, str(path), "exec"), namespace)
    collector = trace.CallPathTrace(bound, {"workspace": tmp_path})
    collector.write = lambda *_: None
    collector.begin("call-1")
    if call_focus:
        assert namespace["focus"]("independent caller") == "independent caller"
    assert namespace["changed"](False) == "original"
    collector.end("call-1")
    feedback = trace.public_feedback(bound, collector.finish())
    assert feedback["status"] == "complete"
    assert feedback["focus"]["entries"] == int(call_focus)
    assert feedback["watches"][0]["entries"] == 1
    assert 6 in feedback["watches"][0]["not_observed_lines"]
    assert 7 in feedback["watches"][0]["observed_lines"]
    assert raw == {"focus": {"origin": "workspace", "path": "sample.py", "function": "focus"}}


@pytest.mark.parametrize(("boundary", "legacy"), [
    ("admitted", False), ("dispatched", False), ("returned", False), ("rejected", False),
    ("admitted", True), ("returned", True),
])
def test_symbolic_recovery_preserves_admission_and_never_repeats_execution(
    gateway_factory, monkeypatch, boundary, legacy,
):
    gateway, journal, _, backend = setup(gateway_factory)
    call = symbolic(gateway) if legacy else focused()
    if boundary == "rejected":
        call.arguments["focus"]["function"] = "missing_function"
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
    saved = next(e["payload"] for e in journal.events() if e["event_type"] == "action_started"
                 and e["payload"]["action_id"] == call.action_id)
    if boundary != "rejected":
        request = saved["diagnosis_request"]["call_path"]
        assert ("scope" not in request) if legacy else request["scope"] == "selected_call"
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
    assert next(e["payload"] for e in journal.events() if e["event_type"] == "action_started"
                and e["payload"]["action_id"] == call.action_id) == saved
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
    selected = focused()
    incompatible = focused("mixed-diagnosis", "missing_function")
    steps = iter([read_calls()[1], diagnostic_probe(smoke_package.public, "original",
                  corrected=True), wrong, incompatible, selected, fixed])

    class ScriptedDiagnosis(MockDevAdapter):
        def next_turn(self, context, tools):
            call = next(steps, None)
            if call is not None:
                assert call.name in {tool["name"] for tool in tools}
                if call.name == "run_probe":
                    properties = next(t for t in tools if t["name"] == "run_probe")[
                        "parameters"]["properties"]
                    if call.arguments.get("focus"):
                        assert set(properties) == {"focus"}
                    else:
                        assert properties["question"]["type"] == ["string", "null"]
                        assert "anyOf" in properties["purpose"]
                return DevModelTurn(tool_calls=[call])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ScriptedDiagnosis)
    request = mock_request(tmp_path, "none").model_copy(update={"enable_probes": True})
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 4
    events = DevJournal(tmp_path, result["run_id"]).events()
    results = {event["payload"]["action_id"]: event["payload"]["result"]
               for event in events
               if event["event_type"] == "action_finished"}
    rejected = results["mixed-diagnosis"]
    assert rejected["status"] == "failed"
    validation = rejected["output"]["request_validation"]
    assert [f["path"] for f in validation["invalid_fields"]] == ["/focus"]
    correction = results["host-diagnosis"]["output"]["request_validation"]["correction"]
    assert correction == {"status": "corrected", "previous_action_id": "mixed-diagnosis",
                          "changed_error_fields": ["/focus"]}
    starts = {e["payload"]["action_id"]: e["payload"] for e in events
              if e["event_type"] == "action_started"}
    assert starts["mixed-diagnosis"]["repair_path_link"] == starts["host-diagnosis"][
        "repair_path_link"]
    assert starts["mixed-diagnosis"]["arguments"] == incompatible.arguments
    assert starts["host-diagnosis"]["arguments"] == selected.arguments
    dispatched = [e["payload"]["action_id"] for e in events
                  if e["event_type"] == "probe_execution_started"]
    assert "mixed-diagnosis" not in dispatched and dispatched.count("host-diagnosis") == 1
    assert results["host-diagnosis"]["output"]["call_path"]["status"] == "complete"
    assert results["diagnosed-repair"]["output"]["mutation"]["repair_path_link"][
        "diagnosis_action_id"] == "host-diagnosis"
    replays = [r["output"]["reproduction"]["comparison"] for action, r in results.items()
               if action.startswith("completion-reproduction-")]
    assert replays == ["mismatched", "matched"]  # Fresh automatic checks; finish reuses success.
    assert all(r["status"] == "succeeded" for a, r in results.items() if a != "mixed-diagnosis")
    assert result["evaluator"]["claim_eligible"] is False
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
