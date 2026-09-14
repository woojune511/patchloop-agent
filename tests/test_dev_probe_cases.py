"""Reusable public observations: execution/identity tests, not agent-quality evidence."""

from __future__ import annotations

import json
import sys

import httpx
import pytest
from pydantic import ValidationError
from test_dev_planning import request as mock_request
from test_dev_probes import FakeProbe, context
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash
from test_dev_segments import assert_submitted, configured
from test_dev_tools import mutation_call, read_calls
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.contracts import RegisteredCheck
from patchloop.dev import probe_cases as cases
from patchloop.dev import runner, segments
from patchloop.dev.contracts import (
    DevModelTurn,
    DevRunRequest,
    PublicTurnDecision,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.conversation import (
    assemble_model_input,
    reconstruct_state,
    segment_seed,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import DevToolGateway, dev_tool_schemas
from patchloop.errors import ActionConflict, ContractError, RecoveryError, ResumeContractMismatch
from patchloop.sandbox import LocalSandbox
from patchloop.util import canonical_json, sha256_bytes, sha256_json

TEXT = 'h,v\n"first\nsecond",x\n'
REFERENCE = (
    "import csv, io, json\n"
    f"print(json.dumps(list(csv.reader(io.StringIO({TEXT!r}, newline='')))))"
)
CANDIDATE = (
    "import json\nfrom mini_data_utils.csvlite import parse_rows\n"
    f"print(json.dumps(parse_rows({TEXT!r})))"
)


@pytest.fixture(autouse=True)
def no_provider_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("probe case validation must not send real provider requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


class ExecutingProbe(FakeProbe):
    """Trusted test programs only; the production path remains DockerProbeSandbox."""

    def __init__(self):
        super().__init__(status="passed")
        self.sources = []

    def run_probe(self, workspace, question, python_source, *, deadline, execution_identity):
        receipt = super().run_probe(workspace, question, python_source, deadline=deadline,
                                    execution_identity=execution_identity)
        self.sources.append(python_source)
        output = LocalSandbox().run_check(workspace, RegisteredCheck(
            id="trusted-test-probe", command=[sys.executable, "-c", python_source],
            timeout_seconds=10, environment={"PYTHONPATH": str(workspace)},
        ), deadline=deadline, execution_identity=execution_identity)
        return {**receipt, "status": "passed" if output.passed else "failed",
                "exit_code": output.exit_code, "stdout": output.stdout, "stderr": output.stderr}


def call(action="case-new", *, source=CANDIDATE, reference="case-reference", case_id=None):
    replay = case_id is not None
    return RequestedTool(name="run_probe", action_id=action, arguments={
        "question": None if replay else "Does the project preserve quoted record boundaries?",
        "python_source": None if replay else source,
        "reference_action_id": None if replay else reference,
        "case_id": case_id,
    }, turn_decision=PublicTurnDecision(mode="verify", basis="Compare public observations."))


def setup_gateway(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    gateway.probe_policy = cases.POLICY
    backend = ExecutingProbe()
    gateway.probe_sandbox = backend
    return gateway, journal, workspace, backend


def seed(gateway):
    reference = call("case-reference", source=REFERENCE, reference=None)
    assert gateway.execute(reference).status == "succeeded"
    result = gateway.execute(call())
    assert result.status == "succeeded"
    return result, result.output["case_comparison"]["case_id"]


def test_off_schema_prompt_and_identity_are_unchanged():
    options = {"finish_enabled": True, "allowed_tools": [
        "read_file", "search_files", "replace_text", "run_check", "run_probe",
        "finish_task", "stop_task",
    ]}
    before = dev_tool_schemas(**options)
    assert sha256_json(before) == (
        "sha256:83a9b5a089857a52c3edd8e20b36b4be8823030af0f89595d2d0c4e2472da0d7"
    )
    assert dev_tool_surface_hash() == (
        "sha256:a076ac52db8457c004fc689272bdd557e4911e19c98517e4530fbf32a3dc0745"
    )
    assert sha256_bytes(DEV_SYSTEM_PROMPT.encode()) == (
        "sha256:9d947f3fedcdddd15da57951dab6b34e0345f44e9a47d057df0bd2ae45bf058b"
    )
    after = dev_tool_schemas(**options, probe_policy=cases.POLICY)
    assert [t for t in before if t["name"] != "run_probe"] == [
        t for t in after if t["name"] != "run_probe"]
    schema = next(t for t in after if t["name"] == "run_probe")
    parameters = schema["parameters"]
    assert set(parameters["required"]) == set(parameters["properties"])
    assert not parameters["additionalProperties"]
    for field in ("question", "python_source", "case_id", "reference_action_id"):
        assert parameters["properties"][field]["type"] == ["string", "null"]
    for hint in ("pyfakefs", "makedirs", "csvlite", "reference_patch", "hidden-multiline"):
        assert hint not in canonical_json(cases.contract())


def test_cli_and_exact_contract_identity(tmp_path, monkeypatch):
    base = mock_request(tmp_path, "none")
    with pytest.raises(ValidationError, match="requires --enable-probes"):
        DevRunRequest.model_validate({**base.model_dump(), "probe_policy": cases.POLICY})
    on = DevRunRequest.model_validate({**base.model_dump(), "enable_probes": True,
                                      "probe_policy": cases.POLICY})
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda request: captured.append(request) or {})
    result = CliRunner().invoke(app, ["dev", "--provider", "mock", "--task", str(base.task),
                                    "--model", "mock-dev", "--enable-probes",
                                    "--probe-policy", cases.POLICY])
    assert result.exit_code == 0, result.output
    assert captured[0].probe_policy == cases.POLICY
    before = {p: (runner._model_hash(r, None), dev_tool_surface_hash(probe_policy=p))
              for p, r in (("none", base), (cases.POLICY, on))}
    monkeypatch.setattr(cases, "MAX_OBSERVATION_BYTES", 2047)
    for p, r in (("none", base), (cases.POLICY, on)):
        assert ((runner._model_hash(r, None), dev_tool_surface_hash(probe_policy=p))
                == before[p]) == (p == "none")


@pytest.mark.parametrize("stdout,reason", [
    ('{"a":1,"a":2}', "stdout_not_json"), ("NaN", "stdout_not_json"),
    ("1e9999", "stdout_not_json"), ("1\n2", "stdout_not_json"),
    ('"' + "한" * 700 + '"', "observation_too_large"), ("", "stdout_not_json"),
    ('"\\ud800"', "stdout_not_json"),
])
def test_reference_json_is_complete_bounded_and_not_a_partial_observation(stdout, reason):
    assert cases.observation_json({"status": "passed", "exit_code": 0,
                                   "stdout": stdout}) == (None, reason)


def test_json_object_order_is_irrelevant_but_types_and_array_order_are_not():
    def value(text):
        return cases.observation_json({"status": "passed", "exit_code": 0, "stdout": text})[0]
    assert value('{"a":1,"b":2}') == value('{"b":2, "a":1}')
    assert value("true") != value("1") != value("1.0")
    assert value("[1,2]") != value("[2,1]")


def test_case_mismatch_replay_after_edit_and_gateway_restart(gateway_factory, smoke_package):
    gateway, journal, workspace, backend = setup_gateway(gateway_factory)
    result, case_id = seed(gateway)
    assert result.output["case_comparison"]["status"] == "mismatched"
    assert not gateway.checks_by_diff and not gateway.has_current_mutation_evidence()
    assert gateway.execute(call()).replayed
    assert backend.calls == 2
    with pytest.raises(ActionConflict):
        gateway.execute(call(source="print(1)"))
    gateway.execute_batch(read_calls())
    assert gateway.execute(mutation_call(gateway)).status == "succeeded"
    projected = context(gateway, smoke_package)["probe_cases"]["items"][0]
    assert projected["last_candidate_result"]["currency"] == "historical"
    restored = DevToolGateway(
        workspace=workspace, journal=journal, public_task=smoke_package.public,
        sandbox=gateway.sandbox, limits=gateway.limits,
        probe_sandbox=backend, probe_policy=cases.POLICY,
    )
    assert context(restored, smoke_package)["probe_cases"] == context(gateway, smoke_package)[
        "probe_cases"]
    replay = call("case-rerun", case_id=case_id)
    after = restored.execute(replay)
    assert after.output["case_comparison"]["status"] == "matched"
    assert after.workspace_diff_hash == restored.current_diff_hash != result.workspace_diff_hash
    assert not after.output["case_comparison"]["counts_toward_completion"]
    assert backend.sources == [REFERENCE, CANDIDATE, CANDIDATE]
    assert restored.execute(replay).replayed and backend.calls == 3
    # A diagnostic, even a mismatch, cannot create or withhold visible-check credit.
    for check in smoke_package.public.visible_checks:
        restored.execute(RequestedTool(name="run_check", action_id=check.id,
                                       arguments={"check_id": check.id}))
    assert restored.execute(RequestedTool(name="finish_task", action_id="finish",
                                          arguments={})).status == "succeeded"


@pytest.mark.parametrize("fault", ["unknown", "bad_json", "check", "pending", "oversize",
                                   "truncated", "failed"])
def test_invalid_reference_never_executes_candidate(gateway_factory, fault):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    if fault in {"bad_json", "oversize", "truncated", "failed"}:
        source = {"bad_json": "print('not json')", "oversize": "print('1' * 2049)",
                  "truncated": "print(1)", "failed": "raise ValueError('public')"}[fault]
        gateway.execute(call("case-reference", source=source, reference=None))
        if fault == "truncated":
            events = journal.events()
            events[-1]["payload"]["result"]["output"]["truncated"] = True
            with pytest.raises(ContractError, match="execution_not_healthy"):
                cases.prepare(call().arguments, events)
            return
    elif fault in {"check", "pending"}:
        events = [{"event_type": "action_started" if fault == "pending" else "action_finished",
                   "payload": {"result": {"action_id": "case-reference", "tool": "run_check",
                                          "status": "succeeded", "output": {}}}}]
        with pytest.raises(ContractError, match="prior completed public probe"):
            cases.prepare(call().arguments, events)
        return
    previous = backend.calls
    result = gateway.execute(call())
    assert result.status == "failed" and backend.calls == previous
    assert not cases.saved_cases(journal.events())
    # Existing ad-hoc diagnostics remain usable after a case contract failure.
    ordinary = gateway.execute(call("ordinary", source="print(1)", reference=None))
    assert ordinary.status == "succeeded"


def test_failed_candidate_is_retained_but_never_counted_as_a_match(gateway_factory):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    gateway.execute(call("case-reference", source="print(1)", reference=None))
    result = gateway.execute(call(source="raise ValueError('public experiment error')"))
    assert result.output["case_comparison"]["status"] == "not_compared"
    assert result.output["case_comparison"]["reason"] == "execution_not_healthy"
    assert len(cases.saved_cases(journal.events())) == 1
    assert backend.calls == 2


def test_native_only_match_is_not_project_behavior_or_a_new_gate(gateway_factory, smoke_package):
    gateway, journal, _, _ = setup_gateway(gateway_factory)
    before = runner._tool_policy(gateway, runner._RunCounters(), gateway.limits)
    gateway.execute(call("case-reference", source=REFERENCE, reference=None))
    matched = gateway.execute(call(source=REFERENCE))  # Intentionally never calls the project.
    assert matched.output["case_comparison"]["status"] == "matched"
    view = context(gateway, smoke_package)["probe_cases"]["items"][0]
    assert view["program_authorship"] == "model_authored_unverified"
    assert not view["last_candidate_result"]["counts_toward_completion"]
    assert view["last_candidate_result"]["observed_json_matches_reference"]
    assert "observed_json" not in view["last_candidate_result"]
    assert "expected_json" not in view["last_candidate_result"]
    assert runner._tool_policy(gateway, runner._RunCounters(), gateway.limits) == before
    assert len(cases.saved_cases(journal.events())) == 1


def test_bounded_case_catalog_no_silent_source_substitution(gateway_factory):
    gateway, journal, _, backend = setup_gateway(gateway_factory)
    gateway.execute(call("case-reference", source="print(1)", reference=None))
    ids = []
    for number in range(4):
        result = gateway.execute(call(f"new-{number}", source=f"print({number})"))
        ids.append(result.output["case_comparison"]["case_id"])
    assert list(cases.saved_cases(journal.events())) == ids[1:]
    previous = backend.calls
    assert gateway.execute(call("expired", case_id=ids[0])).status == "failed"
    assert backend.calls == previous
    mixed = call("mixed", case_id=ids[1])
    mixed.arguments["python_source"] = "print(9)"
    assert gateway.execute(mixed).status == "failed" and backend.calls == previous
    events = journal.events()
    event = next(e for e in events if e["event_type"] == "action_finished"
                 and "probe_case" in e["payload"])
    event["payload"]["probe_case"]["python_source"] += "\nprint(9)"
    with pytest.raises(RecoveryError, match="identity"):
        cases.saved_cases(events)


@pytest.mark.parametrize("policy", ["append-v1", "native-window-v1", "segmented-v1"])
def test_current_catalog_and_handoff_do_not_resurrect_historical_matches(policy):
    original = {"public_task": {"goal": "PUBLIC_GOAL"}, "probe_cases": {
        "items": [{"case_id": "old", "last_candidate_result": {"currency": "current"}}],
    }}
    first = assemble_model_input(system_prompt="fixed", state=original, history=[],
                                 context_policy=policy)
    current = {**original, "probe_cases": {"items": []}}
    native = [{"type": "reasoning", "id": "r1", "encrypted_content": "opaque", "summary": []},
              {"type": "function_call", "call_id": "a", "name": "run_probe", "arguments": "{}"},
              {"type": "function_call_output", "call_id": "a", "output": "{}"}]
    after = assemble_model_input(system_prompt="fixed", state=current, history=native,
                                 previous_input=first, context_policy=policy)
    assert [i for i in after if "type" in i] == native
    assert reconstruct_state(after, context_policy=policy) == current
    if policy != "append-v1":
        assert '"case_id":"old"' not in canonical_json(after)
    if policy == "segmented-v1":
        fresh = assemble_model_input(system_prompt="fixed", state=current, history=[],
                                     previous_input=segment_seed("fixed", original["public_task"]),
                                     context_policy=policy)
        assert reconstruct_state(fresh, context_policy=policy) == current
        assert not any("encrypted_content" in i for i in fresh)


def scripted_cases(monkeypatch):
    backend = ExecutingProbe()
    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    original = MockDevAdapter.next_turn

    def next_turn(self, context_text, tools):
        state = json.loads(context_text)
        items = state["probe_cases"]["items"]
        if not state.get("recent_probes"):
            chosen = call("case-reference", source=REFERENCE, reference=None)
        elif not items:
            chosen = call()
        elif state["current_diff"]["patch"] and items[0]["last_candidate_result"][
            "currency"] == "historical":
            chosen = call("case-rerun", case_id=items[0]["case_id"])
        else:
            return original(self, context_text, tools)
        assert "run_probe" in {t["name"] for t in tools}
        return DevModelTurn(tool_calls=[chosen])
    monkeypatch.setattr(MockDevAdapter, "next_turn", next_turn)
    return backend


@pytest.mark.parametrize("boundary", ["turn_decision_recorded", "action_started",
                                      "action_finished", "tool_batch_finished"])
def test_mock_smoke_resume_keeps_one_case_and_no_duplicate_model_or_mutation(
    tmp_path, monkeypatch, boundary,
):
    backend = scripted_cases(monkeypatch)
    request = mock_request(tmp_path, "none").model_copy(update={
        "enable_probes": True, "probe_policy": cases.POLICY, "context_policy": segments.POLICY,
    })

    def selected(payload):
        if boundary == "turn_decision_recorded":
            return any(c["action_id"] == "case-new" for c in payload["tool_calls"])
        if boundary == "tool_batch_finished":
            return payload["action_ids"] == ["case-new"]
        return payload.get("action_id") == "case-new"

    _crash_journal_once(monkeypatch, event_type=boundary, predicate=selected, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(request)
    resumed = request.model_copy(update={"resume_run_id": _enveloped_run_id(tmp_path)})
    journal = DevJournal(tmp_path, resumed.resume_run_id)
    before = journal.path.read_bytes()
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"probe_policy": "none"}))
    assert journal.path.read_bytes() == before
    result = runner.run_dev(resumed)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_mutations"] == 1
    assert result["call_counts"] == {"model": 7, "input_count": 0, "tool": 8}
    assert backend.sources == [REFERENCE, CANDIDATE, CANDIDATE]
    assert len(cases.saved_cases(journal.events())) == 1
    assert result["evaluator"]["safety_state"] == "NOT_RUN"
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before and backend.calls == 3


def test_pending_case_binds_program_and_other_file_drift_stops_before_execution(
    tmp_path, gateway_factory, smoke_package, monkeypatch,
):
    gateway, journal, workspace, backend = setup_gateway(gateway_factory)
    gateway.execute(call("case-reference", source=REFERENCE, reference=None))
    _crash_journal_once(monkeypatch, event_type="action_started",
                        predicate=lambda p: p["action_id"] == "case-new", when="after")
    with pytest.raises(_SimulatedCrash):
        gateway.execute(call())
    started = journal.events()[-1]["payload"]
    assert started["probe_case_request"]["python_source"] == CANDIDATE
    source = workspace / "mini_data_utils/csvlite.py"
    source.write_bytes(source.read_bytes() + b"\n# external drift\n")
    restored = DevToolGateway(
        workspace=workspace, journal=journal, public_task=smoke_package.public,
        sandbox=gateway.sandbox, limits=gateway.limits, probe_sandbox=backend,
        probe_policy=cases.POLICY,
    )
    result = restored.execute(call())
    assert result.error_code == "RECOVERY_ERROR"
    assert backend.calls == 1  # Only the previously completed reference executed.
    assert not cases.saved_cases(journal.events())


def test_actual_native_inputs_deliver_cases_across_segments_with_continuation_unchanged(
    tmp_path, monkeypatch,
):
    backend = scripted_cases(monkeypatch)
    request, inputs, counted, views = configured(monkeypatch, tmp_path)
    request = request.model_copy(update={"enable_probes": True, "probe_policy": cases.POLICY})
    result = runner.run_dev(request)["runs"][0]
    assert_submitted(result)  # Synthetic Docker provenance still fails closed.
    assert len(inputs) == len(counted) == 7 and inputs == counted
    assert backend.sources == [REFERENCE, CANDIDATE, CANDIDATE]
    final = views[-1]["probe_cases"]["items"][0]
    assert final["last_candidate_result"]["status"] == "matched"
    assert final["last_candidate_result"]["currency"] == "current"
    assert any(v["probe_cases"]["items"] and v["probe_cases"]["items"][0][
        "last_candidate_result"]["currency"] == "historical" for v in views)
    for items, view in zip(inputs, views, strict=True):
        assert view["public_task"]["task_id"] == "csv-quoted-newline"
        for forbidden in ("hidden-multiline-csv", "reference_patch", "reasoning_transcript"):
            assert forbidden not in canonical_json(view)
        # Existing adapter's native validation already checks exact call/result IDs and order.
        for item in items:
            if item.get("type") == "reasoning":
                assert item["encrypted_content"].startswith("cipher-")
    journal = DevJournal(request.state_root, result["run_id"])
    assert len([e for e in journal.events() if e["event_type"] == segments.EVENT]) >= 2


def test_case_identity_is_checked_before_private_evaluator_workspace(tmp_path, monkeypatch):
    scripted_cases(monkeypatch)
    request = mock_request(tmp_path, "none").model_copy(update={
        "enable_probes": True, "probe_policy": cases.POLICY,
    })
    original = runner._manifest

    def wrong(**kwargs):
        manifest = original(**kwargs)
        assert manifest.probe_policy == cases.POLICY
        manifest.tool_surface_hash = dev_tool_surface_hash()
        return manifest

    monkeypatch.setattr(runner, "_manifest", wrong)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_ERROR"
    assert result["artifact_hashes"]["submitted_patch"]
    assert not list((tmp_path / "workspaces").glob("eval_*"))
