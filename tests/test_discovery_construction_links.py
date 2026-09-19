"""Selected code is inspectable evidence, never an origin or behavior oracle."""
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
from diagnostics import discovery_construction_links as links
from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.errors import ActionConflict, ContractError
from patchloop.util import canonical_json, sha256_bytes, utc_now

inputs = source_inputs


def annotation(**changes):
    return {"target": "fresh", "source": "supplied", "line": None,
            "requirement_excerpt": "value() returns zero.", **changes}


@pytest.fixture
def public(inputs):  # noqa: F811 - shared fixture
    return design.load_public_task(inputs.public_task)


def inspect(public, python_source, **changes):
    return links.inspect_links(python_source, [annotation(**changes)], public)["links"][0]


@pytest.mark.parametrize("source,names,reference", [
    ('fresh = Settings(mode="field")', ["Settings"], False),
    ('fresh = supplied.copy(update={"field": "other"})', ["supplied"], True),
    ('fresh: Settings = supplied', ["supplied"], True),
    ('alias = supplied\nfresh = alias.copy()', ["alias"], False),
    ('fresh = factory(supplied)', ["factory", "supplied"], True),
    ('fresh = other.supplied', ["other"], False),
    ('fresh = {"label": "supplied"} # supplied', [], False),
    ('if False:\n    fresh = supplied', ["supplied"], True),
])
def test_reports_only_direct_rhs_names_without_inferring_origin(public, source, names, reference):
    receipt = links.inspect_links(source, [annotation()], public)
    item = receipt["links"][0]
    assert item["status"] == "inspected" and item["referenced_names"] == names
    assert item["direct_reference"] is reference and item["excerpt_matches_issue"]
    assert receipt["semantic_verdict"] is None and receipt["coverage_status"] == "not_assessed"
    assert "No alias, factory, scope, control-flow or runtime value analysis" in receipt[
        "interpretation"]


def test_multiline_exact_statement_and_ambiguous_assignment_selection(public):
    source = 'fresh = Settings()\nfresh = supplied.copy(\n    label="한글",\n)\n'
    assert inspect(public, source)["status"] == "ambiguous"
    selected = inspect(public, source, line=2)
    assert selected["statement"] == 'fresh = supplied.copy(\n    label="한글",\n)'
    assert (selected["start_line"], selected["end_line"]) == (2, 4)
    assert selected["direct_reference"] is True
    assert inspect(public, source, line=3)["reason"] == "assignment_not_found"
    assert inspect(public, "fresh: Settings")["reason"] == "assignment_not_found"


def test_null_source_and_nonliteral_excerpt_remain_unverified(public):
    item = inspect(public, 'fresh = Settings()', source=None,
                   requirement_excerpt="value() ... returns zero.")
    assert item["direct_reference"] is None and item["referenced_names"] == ["Settings"]
    assert item["excerpt_matches_issue"] is False


@pytest.mark.parametrize("expression", [
    'lambda supplied: supplied', '[supplied for supplied in values]',
    '{supplied for supplied in values}', '{supplied: x for supplied in values}',
    '(supplied for supplied in values)', '(supplied := other)',
])
def test_scoped_expressions_remain_unknown(public, expression):
    item = inspect(public, 'fresh = ' + expression)
    assert item["reason"] == "unsupported_expression_scope"
    assert item["referenced_names"] is item["direct_reference"] is None
    assert item["statement"] == 'fresh = ' + expression


@pytest.mark.parametrize("source,reason", [
    ('fresh = "' + 'x' * 1700 + '"', "statement_too_large_or_unavailable"),
    ('fresh = (' + ','.join(f'x{i}' for i in range(33)) + ')', "references_too_large"),
    ('fresh = ' + 'x' * 81, "references_too_large"),
], ids=["long-statement", "many-names", "long-name"])
def test_bounded_feedback_never_returns_a_partial_reference_list(public, source, reason):
    item = inspect(public, source)
    assert item["reason"] == reason and item["status"] == "unknown"
    assert item["direct_reference"] is item["referenced_names"] is None


@pytest.mark.parametrize("value", [
    {}, [annotation()] * 5, [annotation(line=True)], [annotation(line=0)],
    [annotation(target="a.b")], [annotation(source="class")], [annotation(extra="no")],
    [annotation(requirement_excerpt="x" * 601)], [annotation(target="x" * 81)],
])
def test_malformed_annotations_are_advisory(public, value):
    receipt = links.inspect_links('fresh = supplied', value, public)
    assert receipt["status"] == "invalid" and receipt["links"] == []


def test_source_is_only_parsed_never_executed(public, tmp_path):
    marker = tmp_path / 'must-not-exist'
    source = f'open({str(marker)!r}, "w").write("executed")\nfresh = supplied\n'
    assert inspect(public, source)["direct_reference"] is True
    assert not marker.exists()
    for invalid in ('fresh = (', 'fresh = \x00', 'x' * 8001):
        receipt = links.inspect_links(invalid, [annotation()], public)
        assert receipt["status"] == "unknown" and receipt["links"] == []
    for empty in (None, []):
        assert links.inspect_links(source, empty, public)["status"] == "omitted"


@pytest.mark.parametrize("guidance", design.REVIEW_GUIDANCE)
def test_schema_only_extends_probe_and_keeps_task_first_input(public, inputs, guidance):  # noqa: F811
    _, identity = design.read_descriptor(inputs.prepared_dependencies)
    environment = design.load_dependencies(
        inputs.prepared_dependencies, public, identity).environment
    args = (public, inputs.candidate_patch.read_text(), environment)
    before = design.initial_request(*args, review_guidance=guidance,
                                    probe_expectation_mode=design.probe_expectation.MODE)
    after = design.initial_request(*args, review_guidance=guidance,
                                   probe_expectation_mode=design.probe_expectation.MODE,
                                   construction_evidence_mode=links.MODE)
    assert after["input"] == before["input"]
    assert design.case_plan.initial_request(after) == design.case_plan.initial_request(before)
    for old, new in zip(before["tools"], after["tools"], strict=True):
        if old["name"] != "run_probe":
            assert new == old
            continue
        params = new["parameters"]
        assert new["strict"] and set(params["required"]) == set(params["properties"])
        schema = params["properties"]["construction_links"]
        assert schema["type"] == ["array", "null"] and schema["maxItems"] == 4
        item = schema["items"]
        assert not item["additionalProperties"] and set(item["required"]) == set(item["properties"])
        new = copy.deepcopy(new)
        new["description"] = old["description"]
        del new["parameters"]["properties"]["construction_links"]
        new["parameters"]["required"].remove("construction_links")
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
                   case_design=design.case_plan.MODE,
                   probe_expectation_mode=design.probe_expectation.MODE,
                   construction_evidence_mode=links.MODE)
    plan = rollout.prepare(parent, root, result, utc_now().date().isoformat())
    return SimpleNamespace(inputs=inputs, design=parent, root=root, result=result, plan=plan,
                           plan_hash=sha256_bytes((root / "plan.json").read_bytes()))


def linked_probe():
    call = probe_call()
    call.arguments.update(python_source='import toy\nfresh = toy.value()\nprint(fresh)\n',
                          construction_links=[annotation()], expected_json='0', case_selection=None)
    return call


def test_native_feedback_freeze_replay_and_conflict(frozen, monkeypatch):
    original = MockProbe.run_probe

    def run(probe, *args, **kwargs):
        assert "construction_links" not in kwargs
        event = DevJournal(frozen.result, rollout.RUN_ID).events()[-1]
        assert event["event_type"] == "action_started"
        assert event["payload"]["arguments"]["construction_links"] == [annotation()]
        return original(probe, *args, **kwargs)

    monkeypatch.setattr(MockProbe, "run_probe", run)
    call = linked_probe()
    setup = {"status": "passed", "checks": [{"label": "fixture", "matched": True}]}
    result, adapter, probes = run_mock(
        frozen, [[plan_call()], [call], [report_call()]],
        probe_change={"stdout": '1', "setup_checks": setup})
    assert result["terminal"] == "REPORT_RECORDED" and result["discovery_outcome"] is None
    assert adapter.requests == adapter.counts and probes[0].calls == 1
    assert result["model_calls"] == result["tool_actions"] == 3
    assert adapter.requests[0] == rollout.read(frozen.design / "request.json")
    review = rollout.read(frozen.design / "review-request.json")
    assert adapter.requests[1]["tools"] == review["tools"]
    native = next(json.loads(item["output"]) for item in adapter.requests[2]["input"]
                  if item.get("type") == "function_call_output" and item["call_id"] == "probe")
    probe_result = result["report"]["evidence"]["probe_result"]
    output = probe_result["output"]
    receipt = output["construction_evidence"]
    assert native["output"]["construction_evidence"] == receipt
    assert receipt["source_hash"] == output["source_hash"] == sha256_bytes(
        call.arguments["python_source"].encode())
    assert receipt["diff_hash"] == probe_result["workspace_diff_hash"]
    assert receipt["links"][0]["statement"] == 'fresh = toy.value()'
    assert receipt["links"][0]["direct_reference"] is False
    assert native["output"]["setup_checks"] == setup
    assert native["output"]["expectation_comparison"]["status"] == "mismatched"
    assert native["output"]["case_selection"]["status"] == "omitted"
    gateway = links.gateway_type(design.probe_expectation.gateway_type(
        design.case_selection.ApplicabilityGateway))(
            workspace=frozen.result / "workspaces/candidate/repo",
            public_task=design.load_public_task(frozen.design / "public.yaml"), sandbox=None,
            probe_sandbox=probes[0], journal=DevJournal(frozen.result, rollout.RUN_ID),
            limits=DevLimits())
    replay = gateway.execute(rollout.loop._requested_tool_from_openai(call))
    assert replay.replayed and replay.output == output and probes[0].calls == 1
    changed = copy.deepcopy(call)
    changed.arguments["construction_links"][0]["source"] = "toy"
    with pytest.raises(ActionConflict):
        gateway.execute(rollout.loop._requested_tool_from_openai(changed))
    assert rollout.inspect(frozen.result) == result and probes[0].calls == 1


@pytest.mark.parametrize("value,status", [(None, "omitted"), ("omitted", "omitted"),
                                         ({"bad": True}, "invalid")])
def test_optional_or_invalid_links_never_gate_probe_or_report(frozen, value, status):
    call = linked_probe()
    call.arguments["construction_links"] = value
    if value == "omitted":
        del call.arguments["construction_links"]
    result, adapter, probes = run_mock(frozen, [[plan_call()], [call], [report_call()]])
    assert result["terminal"] == "REPORT_RECORDED" and probes[0].calls == 1
    receipt = result["report"]["evidence"]["probe_result"]["output"]["construction_evidence"]
    assert receipt["status"] == status and len(adapter.requests) == 3


def test_failed_probe_syntax_evidence_is_not_execution_evidence(frozen):
    result, adapter, probes = run_mock(
        frozen, [[plan_call()], [linked_probe()], [report_call()]],
        probe_change={"status": "failed", "exit_code": 1, "stdout": "", "stderr": "ImportError"})
    assert result["terminal"] == "REPORT_RECORDED" and probes[0].calls == 1
    output = result["report"]["evidence"]["probe_result"]["output"]
    assert output["construction_evidence"]["status"] == "recorded"
    assert output["expectation_comparison"]["status"] == "not_compared"
    assert output["construction_evidence"]["semantic_verdict"] is None
    assert len(adapter.requests) == 3


@pytest.mark.parametrize("field", ["construction_evidence",
                                   "construction_evidence_implementation_hash"])
def test_tamper_fails_before_consumption(frozen, field):
    path = frozen.design / "packet.json"
    packet = rollout.read(path)
    packet[field] = "changed"
    path.write_bytes(design.wire(packet))
    with pytest.raises(ContractError):
        run_mock(frozen, [[report_call()]])
    assert not frozen.result.exists()


def test_cli_freezes_option_without_provider_access(frozen, monkeypatch, capsys):
    target = frozen.design.parent / "cli"
    args = ["discovery", "prepare", "--output", str(target),
            "--construction-evidence", links.MODE]
    for name, path in frozen.inputs.paths().items():
        args.extend(["--" + name.replace("_", "-"), str(path)])
    monkeypatch.setattr(sys, "argv", args)
    design.main()
    assert json.loads(capsys.readouterr().out)["provider_calls"] == 0
    assert design.validate(target)["construction_evidence"] == links.MODE
    assert frozen.plan["construction_evidence"] == links.MODE
    assert frozen.plan["cap_usd"] == "1.20" and frozen.plan["repeat"] == 1
    assert "FORBIDDEN_SIBLING_SENTINEL" not in canonical_json(rollout.read(target / "request.json"))
