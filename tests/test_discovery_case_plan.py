"""Candidate disclosure must follow a frozen, unverified public case proposal."""
from __future__ import annotations

import copy
import json
import socket
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_counterexample_discovery import inputs as source_inputs
from test_counterexample_discovery_rollout import (
    Adapter,
    MockProbe,
    action,
    probe_call,
    read_call,
    report_call,
    run_mock,
)

from diagnostics import counterexample_discovery as design
from diagnostics import counterexample_discovery_rollout as rollout
from diagnostics import discovery_case_plan as cases
from patchloop.dev.contracts import DevLimits
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import canonical_json, sha256_bytes, sha256_json, utc_now

inputs = source_inputs


def proposal(**changes):
    value = {"cases": [{
        "case_id": "zero", "purpose": "preserve", "requirement_excerpt": "value() returns zero.",
        "applicability": "The public value function, without extra conditions.",
        "setup": "Call value() with no arguments.", "expected": "0",
    }], "limitations": "Source and candidate have not been inspected."}
    value.update(changes)
    return value


def plan_call(action_id="plan", **changes):
    return action(cases.TOOL, action_id, **proposal(**changes))


@pytest.fixture
def frozen(inputs, tmp_path, monkeypatch):  # noqa: F811 - shared fixture
    monkeypatch.setattr(design, "EXPECTED_HASHES", {
        name: sha256_bytes(path.read_bytes()) for name, path in inputs.paths().items()
    })

    def forbidden(*args, **kwargs):
        pytest.fail("unexpected network, credential or real Docker access")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(rollout, "load_exact_openai_api_key", forbidden)
    monkeypatch.setattr(rollout, "DockerProbeSandbox", forbidden)
    parent, root, result = (tmp_path / p for p in ("design", "executable", "result"))
    design.prepare(inputs, parent, review_guidance="applicability-contrast-v1",
                   case_design=cases.MODE)
    plan = rollout.prepare(parent, root, result, utc_now().date().isoformat())
    return SimpleNamespace(inputs=inputs, design=parent, root=root, plan=plan, result=result,
                           plan_hash=sha256_bytes((root / "plan.json").read_bytes()))


def test_initial_input_has_only_public_task_and_case_tool(frozen):
    request = rollout.read(frozen.root / "request.json")
    review = rollout.read(frozen.design / "review-request.json")
    first, later = (json.loads(r["input"][1]["content"]) for r in (request, review))
    assert first["public_task"] == later["public_task"]
    assert set(first) == {"phase", "public_task", "review_limits"}
    assert [tool["name"] for tool in request["tools"]] == [cases.TOOL]
    body = canonical_json(request)
    assert "return 1" not in body and later["candidate"]["patch_hash"] not in body
    assert "FORBIDDEN_SIBLING_SENTINEL" not in body
    assert all(str(path) not in body for path in frozen.inputs.paths().values())
    assert request["input"][0]["content"] == cases.GUIDANCE + review["input"][0]["content"]
    assert frozen.plan["case_design"] == cases.MODE
    assert frozen.plan["cap_usd"] == "1.20" and frozen.plan["max_model_calls"] == 40
    assert {k:v for k,v in request.items() if k not in {"input", "tools"}} == {
        k:v for k,v in review.items() if k not in {"input", "tools"}}


def test_frozen_cases_precede_disclosure_and_survive_native_review(frozen):
    result, adapter, probes = run_mock(
        frozen, [[plan_call()], [read_call()], [probe_call()], [report_call()]])
    assert result["terminal"] == "REPORT_RECORDED"
    assert result["model_calls"] == result["input_count_calls"] == result["tool_actions"] == 4
    assert adapter.counts == adapter.requests and adapter.closed == 1 and probes[0].calls == 1
    assert result["live_provider_calls"] == 0
    assert result["discovery_outcome"] is None
    assert result["report"]["evidence"]["semantic_verdict"] is None
    initial = rollout.read(frozen.root / "request.json")
    review = rollout.read(frozen.design / "review-request.json")
    assert adapter.requests[0] == initial
    for before, after in zip(adapter.requests[:-1], adapter.requests[1:], strict=True):
        assert after["input"][:len(before["input"])] == before["input"]
        assert after["tools"] == review["tools"]
    native = adapter.requests[1]["input"][2:]
    assert [item["type"] for item in native] == [
        "reasoning", "function_call", "function_call_output"]
    assert native[0]["encrypted_content"] == "cipher-1" and native[0]["summary"] == []
    assert json.loads(native[1]["arguments"]) == proposal()
    reveal = json.loads(native[2]["output"])
    assert reveal["candidate"] == json.loads(review["input"][1]["content"])["candidate"]
    assert "plan_artifact" not in reveal and "turn_id" not in reveal
    assert reveal["case_plan_hash"] == sha256_json(proposal())
    assert reveal["coverage_status"] == "not_assessed"
    assert reveal["interpretation_status"] == "model_authored_unverified"
    assert "MOCK_OBSERVATION" in canonical_json(adapter.requests[-1])
    journal = DevJournal(frozen.result, rollout.RUN_ID)
    events = journal.events()
    planned = [(i, e["payload"]) for i, e in enumerate(events) if e["event_type"] == cases.EVENT]
    assert len(planned) == 1
    index, receipt = planned[0]
    assert receipt == result["case_plan"]
    assert receipt["input_hash"] == sha256_json({"tool": cases.TOOL, "arguments": proposal()})
    assert rollout.read(frozen.result / "artifacts" / "objects" / "sha256"
                        / receipt["plan_hash"][7:9] / receipt["plan_hash"][9:]) == proposal()
    assert receipt["requirement_bindings"] == [{"case_id": "zero", "excerpt_matches_issue": True}]
    second_count = [i for i, e in enumerate(events) if e["event_type"] == "input_count_started"][1]
    assert index < second_count
    gates = [e["payload"] for e in events if e["event_type"] == "turn_started"]
    assert gates[0]["available_tool_names"] == [cases.TOOL]
    assert gates[0]["workflow_gate"] == "design_cases_before_candidate"
    assert gates[1]["workflow_gate"] == "fixed_candidate_review"
    assert rollout.inspect(frozen.result) == result


def test_empty_unknown_proposal_can_report_without_probe(frozen):
    unknown = {"cases": [], "limitations": "No justified input known before source inspection."}
    result, adapter, probes = run_mock(frozen, [
        [plan_call(**unknown)],
        [report_call("blocked", probe_action_id=None, requirement_excerpt=None)],
    ])
    assert result["terminal"] == "REPORT_RECORDED" and result["model_calls"] == 2
    assert result["case_plan"]["requirement_bindings"] == [] and probes[0].calls == 0
    assert json.loads(adapter.requests[1]["input"][-2]["arguments"]) == unknown


def test_excerpt_and_duplicate_diagnostics_do_not_claim_semantics_or_block_review(frozen):
    value = proposal()
    value["cases"][0]["requirement_excerpt"] = " "
    value["cases"] *= 2
    result, adapter, _ = run_mock(frozen, [[plan_call(**value)], [report_call("blocked")]])
    assert result["terminal"] == "REPORT_RECORDED"
    receipt = result["case_plan"]
    assert receipt["diagnostics"] == ["duplicate_case_ids"]
    assert not any(binding["excerpt_matches_issue"] for binding in receipt["requirement_bindings"])
    reveal = json.loads(adapter.requests[1]["input"][-1]["output"])
    assert reveal["coverage_status"] == "not_assessed"


@pytest.mark.parametrize("batch", [
    [read_call()], [probe_call()], [report_call()], [plan_call(), read_call()],
    [plan_call(), plan_call("other-plan")],
    [plan_call(cases=[{**proposal()["cases"][0], "expected": 1}])],
])
def test_stage_escape_or_bad_plan_stops_before_disclosure_or_tools(frozen, batch):
    result, adapter, probes = run_mock(frozen, [batch])
    assert result["terminal"] == "PROTOCOL_VIOLATION"
    assert result["model_calls"] == len(adapter.requests) == 1
    assert result["tool_actions"] == probes[0].calls == 0 and "case_plan" not in result
    assert "return 1" not in canonical_json(adapter.requests)
    assert rollout.inspect(frozen.result) == result


def test_second_plan_cannot_overwrite_the_frozen_proposal(frozen):
    result, adapter, probes = run_mock(frozen, [[plan_call()], [plan_call("replacement")]])
    assert result["terminal"] == "PROTOCOL_VIOLATION" and result["tool_actions"] == 1
    assert result["case_plan"]["action_id"] == "plan" and probes[0].calls == 0
    assert len(adapter.requests) == 2


@pytest.mark.parametrize("limit,expected", [("max_model_calls", "MODEL_CALL_LIMIT"),
                                           ("max_tool_actions", "TOOL_ACTION_LIMIT")])
def test_case_stage_consumes_shared_limits(frozen, monkeypatch, limit, expected):
    monkeypatch.setattr(rollout, "DevLimits", lambda: DevLimits(**{limit: 1}))
    result, adapter, probes = run_mock(frozen, [[plan_call()], [read_call()]])
    assert result["terminal"] == expected
    assert len(adapter.counts) == len(adapter.requests) == result["tool_actions"] == 1
    assert "case_plan" in result and probes[0].calls == 0


def test_case_stage_spend_is_not_reset_at_reveal(frozen):
    adapter = Adapter(rollout.configuration(), [[plan_call()], [read_call()]], count=60_000)
    execute = adapter.execute_request
    adapter.execute_request = lambda *a, **kw: replace(execute(*a, **kw), output_tokens=25_000)
    result = rollout.run(frozen.root, plan_hash=frozen.plan_hash,
                         adapter_factory=lambda _: adapter, probe_factory=MockProbe)
    assert result["terminal"] == "COST_CAP_REACHED"
    assert result["model_calls"] == 2 and result["input_count_calls"] == 3
    assert result["recorded_cost_nanos"] == 1_049_550_000
    assert len(adapter.requests) == 2 and rollout.inspect(frozen.result) == result


def test_deadline_does_not_restart_after_case_design(frozen):
    now = [0.0]
    adapter = Adapter(rollout.configuration(), [[plan_call()]])

    def checkpoint(stage):
        if stage == "case_plan_history_recorded":
            now[0] = 1801.0

    result = rollout.run(frozen.root, plan_hash=frozen.plan_hash,
                         adapter_factory=lambda _: adapter, probe_factory=MockProbe,
                         clock=lambda: now[0], checkpoint=checkpoint)
    assert result["terminal"] == "LIMIT_REACHED"
    assert len(adapter.counts) == len(adapter.requests) == result["tool_actions"] == 1
    assert rollout.inspect(frozen.result) == result


def test_provider_uncertainty_after_reveal_stops_without_extra_action(frozen):
    adapter = Adapter(rollout.configuration(), [[plan_call()]])
    execute = adapter.execute_request

    def fail_second(*args, **kwargs):
        if adapter.requests:
            raise TimeoutError("transport stopped")
        return execute(*args, **kwargs)

    adapter.execute_request = fail_second
    result = rollout.run(frozen.root, plan_hash=frozen.plan_hash,
                         adapter_factory=lambda _: adapter, probe_factory=MockProbe)
    assert result["terminal"] == "PROVIDER_TIMEOUT_OR_UNKNOWN"
    assert result["model_calls"] == result["input_count_calls"] == 2
    assert result["tool_actions"] == 1
    assert result["case_plan"]["plan_hash"] == sha256_json(proposal())
    assert not result["provider_cost_known"] and adapter.closed == 1
    assert rollout.inspect(frozen.result) == result


def test_changed_frozen_case_artifact_is_rejected_by_inspection(frozen):
    result, _, _ = run_mock(frozen, [[plan_call()], [report_call("blocked")]])
    artifact = result["case_plan"]["plan_artifact"]
    Path(artifact["path"]).write_bytes(b"changed proposal")
    with pytest.raises(RecoveryError):
        rollout.inspect(frozen.result)


@pytest.mark.parametrize("stage", ["case_plan_frozen", "case_plan_history_recorded"])
def test_interruption_preserves_proposal_without_resume(frozen, stage):
    def stop(actual):
        if actual == stage:
            raise KeyboardInterrupt

    result, adapter, probes = run_mock(frozen, [[plan_call()]], checkpoint=stop)
    assert result["terminal"] == "EXECUTION_STOPPED"
    assert result["case_plan"]["plan_hash"] == sha256_json(proposal())
    assert len(adapter.requests) == 1 and probes[0].calls == 0
    before = {str(p): sha256_bytes(p.read_bytes()) for p in frozen.result.rglob("*") if p.is_file()}
    assert rollout.inspect(frozen.result) == result
    assert before == {str(p): sha256_bytes(p.read_bytes())
                      for p in frozen.result.rglob("*") if p.is_file()}
    with pytest.raises(ContractError, match="fresh external"):
        run_mock(frozen, [[plan_call()]])


@pytest.mark.parametrize("name", ["request.json", "review-request.json", "packet.json"])
def test_staged_packet_tamper_fails_before_sample_creation(frozen, name):
    path = frozen.design / name
    if name == "packet.json":
        packet = rollout.read(path)
        packet.pop("case_design")
        path.write_bytes(design.wire(packet))
    else:
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ContractError, match="changed"):
        run_mock(frozen, [[plan_call()]])
    assert not frozen.result.exists()


def test_unknown_case_design_fails_before_input_reads(tmp_path):
    missing = design.Inputs(*(tmp_path / name for name in design.EXPECTED_HASHES))
    with pytest.raises(ContractError, match="unknown case design"):
        design.compile_packet(missing, case_design="unknown")


@pytest.mark.parametrize("change", [
    {"cases": proposal()["cases"] * 5}, {"limitations": "x" * 601}, {"extra": True},
    {"cases": [{**proposal()["cases"][0], "setup": "x" * 601}]},
])
def test_case_plan_bounds(change):
    with pytest.raises(ValidationError):
        cases.CasePlan.model_validate(proposal(**change))


def test_schema_requires_every_property_and_rejects_extra_keys():
    schema = copy.deepcopy(cases.schema())

    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert set(node["required"]) == set(node["properties"])
                assert node["additionalProperties"] is False
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    assert schema["strict"] is True
    visit(schema["parameters"])


def test_cli_prepares_staged_design_without_live_access(frozen, tmp_path, monkeypatch, capsys):
    root = tmp_path / "cli"
    args = ["prepare", "--output", str(root), "--case-design", cases.MODE]
    for name, path in frozen.inputs.paths().items():
        args.extend(["--" + name.replace("_", "-"), str(path)])
    monkeypatch.setattr(sys, "argv", ["counterexample_discovery", *args])
    design.main()
    assert json.loads(capsys.readouterr().out)["provider_calls"] == 0
    assert design.validate(root)["case_design"] == cases.MODE
