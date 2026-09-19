"""A predeclared value stays outside the program and inside the existing action identity."""
from __future__ import annotations

import copy
import json
import socket
import sys
from types import SimpleNamespace

import pytest
from test_counterexample_discovery import inputs as source_inputs
from test_counterexample_discovery_rollout import MockProbe, probe_call, report_call, run_mock
from test_discovery_case_plan import plan_call

from diagnostics import counterexample_discovery as design
from diagnostics import counterexample_discovery_rollout as rollout
from diagnostics import discovery_probe_expectation as expectation
from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.errors import ActionConflict, ContractError
from patchloop.util import canonical_json, sha256_bytes, utc_now

inputs = source_inputs


def output(stdout, **changes):
    return {"status": "passed", "exit_code": 0, "stdout": stdout,
            "diff_hash": "diff", "source_hash": "source", **changes}


@pytest.mark.parametrize("expected,observed,status", [
    ('{ "b": 2, "a": 1 }', '{"a":1,"b":2}', "matched"),
    ('[1,2]', '[2,1]', "mismatched"),
    ('[1,2]', '[1]', "mismatched"),
    ('1', 'true', "mismatched"), ('1', '1.0', "mismatched"),
    ('null', 'null', "matched"), ('""', '"made up"', "mismatched"),
    ('{"items":["one"],"count":1}', '{"items":[],"count":0}', "mismatched"),
    ('{"id":"x","payload":"original"}', '{"id":"x","payload":"changed"}', "mismatched"),
    ('{"value":0}', '{"expected":1,"observed":1}', "mismatched"),
])
def test_host_compares_complete_values_and_never_takes_expected_from_stdout(
    expected, observed, status,
):
    frozen = expectation.freeze(expected)
    result = expectation.compare(frozen, output(observed))
    assert result["status"] == status and result["reason"] is None
    assert result["expected_json"] == frozen
    assert result["expected_hash"] == sha256_bytes(frozen.encode())
    assert result["semantic_verdict"] is None and result["coverage_status"] == "not_assessed"


@pytest.mark.parametrize("value", [
    '', 'NaN', 'Infinity', '1e999', '{"x":1,"x":2}', 'null null', 0, {}, True,
    '"' + 'x' * 2047 + '"', '"' + '한' * 683 + '"', '"\\ud800"',
])
def test_invalid_expectation_fails_before_execution(value):
    class NeverRun:
        def _run_probe(self, *args, **kwargs):
            pytest.fail("invalid expectation reached sandbox")

    with pytest.raises(ContractError, match="invalid expected_json"):
        expectation.gateway_type(NeverRun)()._run_probe("why", "print(0)", expected_json=value)


@pytest.mark.parametrize("changes,reason", [
    ({"status": "failed", "exit_code": 1}, "execution_not_healthy"),
    ({"exit_code": False}, "execution_not_healthy"),
    ({"truncated": True}, "execution_not_healthy"),
    ({"timed_out": True}, "execution_not_healthy"),
    ({"cleanup_failed": True}, "execution_not_healthy"),
    ({"deadline_exhausted": True}, "execution_not_healthy"),
    ({"stdout": '{"a":0,"a":0}'}, "stdout_not_json"),
    ({"stdout": 'NaN'}, "stdout_not_json"),
    ({"stdout": 'LOG\n0'}, "stdout_not_json"),
    ({"stdout": '0' * 2049}, "observation_too_large"),
])
def test_unusable_output_is_not_a_mismatch(changes, reason):
    actual = output('0') | changes
    result = expectation.compare('0', actual)
    assert result["status"] == "not_compared" and result["reason"] == reason
    assert result["observed_json"] is result["observed_hash"] is None


def test_omission_and_json_null_are_distinct():
    assert expectation.freeze(None) is None
    assert expectation.compare(None, output('null'))["status"] == "not_compared"
    assert expectation.compare(expectation.freeze('null'), output('null'))["status"] == "matched"


@pytest.mark.parametrize("guidance", design.REVIEW_GUIDANCE)
def test_schema_is_strict_nullable_and_only_extends_probe(inputs, guidance):
    public = design.load_public_task(inputs.public_task)
    _, identity = design.read_descriptor(inputs.prepared_dependencies)
    environment = design.load_dependencies(
        inputs.prepared_dependencies, public, identity).environment
    args = (public, inputs.candidate_patch.read_text(), environment)
    before = design.initial_request(*args, review_guidance=guidance)
    after = design.initial_request(*args, review_guidance=guidance,
                                   probe_expectation_mode=expectation.MODE)
    assert after["input"] == before["input"]
    assert design.case_plan.initial_request(after) == design.case_plan.initial_request(before)
    for old, new in zip(before["tools"], after["tools"], strict=True):
        if old["name"] != "run_probe":
            assert old == new
            continue
        assert new["strict"] and not new["parameters"]["additionalProperties"]
        params = new["parameters"]
        assert set(params["required"]) == set(params["properties"])
        assert params["properties"]["expected_json"]["type"] == ["string", "null"]
        new = copy.deepcopy(new)
        new["description"] = old["description"]
        del new["parameters"]["properties"]["expected_json"]
        new["parameters"]["required"].remove("expected_json")
        assert new == old


@pytest.fixture
def frozen(inputs, tmp_path, monkeypatch):  # noqa: F811 - shared fixture
    monkeypatch.setattr(design, "EXPECTED_HASHES", {
        name: sha256_bytes(path.read_bytes()) for name, path in inputs.paths().items()
    })

    def forbidden(*args, **kwargs):
        pytest.fail("unexpected network, credential or Docker access")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(rollout, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout, "DockerProbeSandbox", forbidden)
    parent, root, result = (tmp_path / name for name in ("design", "plan", "result"))
    design.prepare(inputs, parent, review_guidance=design.case_selection.CONTRAST_POLICY,
                   case_design=design.case_plan.MODE, probe_expectation_mode=expectation.MODE)
    plan = rollout.prepare(parent, root, result, utc_now().date().isoformat())
    return SimpleNamespace(inputs=inputs, design=parent, root=root, result=result, plan=plan,
                           plan_hash=sha256_bytes((root / "plan.json").read_bytes()))


def expected_probe(value='{"value":0}'):
    call = probe_call()
    call.arguments.update(expected_json=value, case_selection=None)
    return call


def test_frozen_action_native_feedback_replay_and_conflict(frozen, monkeypatch):
    original = MockProbe.run_probe

    def run(probe, *args, **kwargs):
        assert "expected_json" not in kwargs
        events = DevJournal(frozen.result, rollout.RUN_ID).events()
        start = events[-1]
        assert start["event_type"] == "action_started"
        assert start["payload"]["arguments"]["expected_json"] == '{"value":0}'
        return original(probe, *args, **kwargs)

    monkeypatch.setattr(MockProbe, "run_probe", run)
    call = expected_probe()
    setup = {"status": "passed", "checks": [{"label": "fixture", "matched": True}]}
    result, adapter, probes = run_mock(
        frozen, [[plan_call()], [call], [report_call()]],
        probe_change={"stdout": '{"value":1}', "setup_checks": setup})
    assert result["terminal"] == "REPORT_RECORDED" and result["discovery_outcome"] is None
    assert result["model_calls"] == result["input_count_calls"] == result["tool_actions"] == 3
    assert adapter.requests == adapter.counts and probes[0].calls == 1
    assert adapter.requests[0] == rollout.read(frozen.design / "request.json")
    assert [t["name"] for t in adapter.requests[0]["tools"]] == [design.case_plan.TOOL]
    review = rollout.read(frozen.design / "review-request.json")
    assert adapter.requests[1]["tools"] == review["tools"]
    native = next(json.loads(item["output"]) for item in adapter.requests[2]["input"]
                  if item.get("type") == "function_call_output" and item["call_id"] == "probe")
    receipt = result["report"]["evidence"]["probe_result"]
    comparison = receipt["output"]["expectation_comparison"]
    assert native["output"]["expectation_comparison"] == comparison
    assert native["output"]["setup_checks"] == setup
    assert native["observation"]["setup_check_observation"]["status"] == "passed"
    assert comparison["status"] == "mismatched" and comparison["expected_json"] == '{"value":0}'
    assert receipt["output"]["case_selection"]["status"] == "omitted"
    assert comparison["diff_hash"] == receipt["workspace_diff_hash"]
    journal = DevJournal(frozen.result, rollout.RUN_ID)
    gateway = expectation.gateway_type(design.case_selection.ApplicabilityGateway)(
        workspace=frozen.result / "workspaces/candidate/repo",
        public_task=design.load_public_task(frozen.design / "public.yaml"), sandbox=None,
        probe_sandbox=probes[0], journal=journal, limits=DevLimits())
    replay = gateway.execute(rollout.loop._requested_tool_from_openai(call))
    assert replay.replayed and replay.output == receipt["output"] and probes[0].calls == 1
    changed = copy.deepcopy(call)
    changed.arguments["expected_json"] = '{"value":1}'
    with pytest.raises(ActionConflict):
        gateway.execute(rollout.loop._requested_tool_from_openai(changed))
    assert probes[0].calls == 1 and rollout.inspect(frozen.result) == result


@pytest.mark.parametrize("value", [None, "omitted"])
def test_ad_hoc_probe_and_report_still_available(frozen, value):
    call = expected_probe(value)
    if value == "omitted":
        del call.arguments["expected_json"]
    result, adapter, probes = run_mock(frozen, [[plan_call()], [call], [report_call()]])
    assert result["terminal"] == "REPORT_RECORDED" and len(adapter.requests) == 3
    comparison = result["report"]["evidence"]["probe_result"]["output"]["expectation_comparison"]
    assert comparison["reason"] == "expectation_not_supplied" and probes[0].calls == 1


def test_invalid_expectation_uses_existing_stop_path_before_sandbox(frozen):
    result, adapter, probes = run_mock(frozen, [[plan_call()], [expected_probe('NaN')]])
    assert result["terminal"] == "TOOL_EXECUTION_UNCERTAIN"
    assert len(adapter.requests) == 2 and probes[0].calls == 0
    assert rollout.inspect(frozen.result) == result


@pytest.mark.parametrize("change", [
    {"stdout": "unstructured observation"},
    {"status": "failed", "exit_code": 1, "stderr": "ImportError: mock fixture"},
    {"truncated": True},
])
def test_no_comparison_feedback_reaches_report_without_semantic_credit(frozen, change):
    result, adapter, _ = run_mock(
        frozen, [[plan_call()], [expected_probe()], [report_call()]], probe_change=change)
    assert result["terminal"] == "REPORT_RECORDED" and len(adapter.requests) == 3
    evidence = result["report"]["evidence"]
    receipt = evidence["probe_result"]["output"]["expectation_comparison"]
    assert receipt["status"] == "not_compared" and evidence["semantic_verdict"] is None
    native = next(json.loads(item["output"]) for item in adapter.requests[-1]["input"]
                  if item.get("type") == "function_call_output" and item["call_id"] == "probe")
    assert native["output"]["expectation_comparison"] == receipt


def test_no_probe_required_and_count_limit_still_prevents_dispatch(frozen):
    result, adapter, probes = run_mock(frozen, [[plan_call()], [report_call()]])
    assert result["terminal"] == "REPORT_RECORDED" and len(adapter.requests) == 2
    assert probes[0].calls == 0
    ledger = rollout.DiscoveryLedger(rollout.CAP, rollout.pricing_for_model(design.MODEL))
    with pytest.raises(rollout.engine.AbortExperiment, match="INPUT_LIMIT_EXCEEDED"):
        ledger.admit(60001, desired_output_ceiling=25000, minimum_output_ceiling=25000)


def test_interruption_after_probe_keeps_comparison_without_resume(frozen):
    def checkpoint(stage):
        if stage == "actions_finished":
            raise KeyboardInterrupt()

    result, adapter, probes = run_mock(
        frozen, [[plan_call()], [expected_probe()]], checkpoint=checkpoint,
        probe_change={"stdout": '{"value":1}'})
    assert result["terminal"] == "EXECUTION_STOPPED" and probes[0].calls == 1
    assert len(adapter.requests) == 2 and rollout.inspect(frozen.result) == result
    finished = [e["payload"]["result"] for e in DevJournal(frozen.result, rollout.RUN_ID).events()
                if e["event_type"] == "action_finished"]
    assert finished[-1]["output"]["expectation_comparison"]["status"] == "mismatched"
    with pytest.raises(ContractError):
        run_mock(frozen, [[report_call()]])
    assert probes[0].calls == 1


@pytest.mark.parametrize("field", ["probe_expectation", "probe_expectation_implementation_hash"])
def test_option_or_implementation_tamper_fails_before_consumption(frozen, field):
    path = frozen.design / "packet.json"
    packet = rollout.read(path)
    packet[field] = "changed"
    path.write_bytes(design.wire(packet))
    with pytest.raises(ContractError):
        run_mock(frozen, [[report_call()]])
    assert not frozen.result.exists()


def test_cli_binds_option_without_provider_access(frozen, monkeypatch, capsys):
    target = frozen.design.parent / "cli"
    args = ["discovery", "prepare", "--output", str(target),
            "--probe-expectation", expectation.MODE]
    for name, path in frozen.inputs.paths().items():
        args.extend(["--" + name.replace("_", "-"), str(path)])
    monkeypatch.setattr(sys, "argv", args)
    design.main()
    assert json.loads(capsys.readouterr().out)["provider_calls"] == 0
    packet = design.validate(target)
    assert packet["probe_expectation"] == expectation.MODE
    assert frozen.plan["probe_expectation"] == expectation.MODE
    assert frozen.plan["cap_usd"] == "1.20" and frozen.plan["repeat"] == 1
    assert "FORBIDDEN_SIBLING_SENTINEL" not in canonical_json(rollout.read(target / "request.json"))
