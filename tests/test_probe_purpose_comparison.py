"""Compact offline checks for the exact comparison and its additional audit."""
from __future__ import annotations

import ast
import copy
import json
import multiprocessing
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from test_dev_probe_action_replay import restore
from test_dev_probe_cases import TEXT, ExecutingProbe, mock_request
from test_dev_tools import mutation_call, read_calls
from test_probe_purpose import probe
from test_verification_state_comparison import frozen_prompt
from test_verification_state_grading import event, reviewed_row

from diagnostics import probe_purpose_control as control
from diagnostics import probe_purpose_execution as execution
from diagnostics import probe_purpose_grading as grading
from diagnostics import probe_purpose_panel as panel
from diagnostics import verification_state_execution as shared
from patchloop.dev import model, reproduction, runner
from patchloop.dev import tools as tools_module
from patchloop.dev.contracts import DEV_READ_TOOLS, DEV_SINGLE_ACTION_TOOLS, DevModelTurn
from patchloop.dev.conversation import assemble_model_input
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ContractError, RecoveryError
from patchloop.util import sha256_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("comparison preparation must not use provider/network")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    with frozen_prompt(control.BASE):
        yield


def historical_schema(ref):
    source = subprocess.check_output([
        "git", "show", ref + ":patchloop/dev/reproduction.py",
    ], text=True)
    tree = ast.parse(source)
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                   and any(getattr(t, "id", "") in {"DESCRIPTION", "REPLAY_DESCRIPTION"}
                           for t in n.targets)]
    old = {}
    exec(compile(ast.Module(body=assignments, type_ignores=[]), "old-guidance", "exec"), old)
    function = next(n for n in ast.parse(subprocess.check_output([
        "git", "show", ref + ":patchloop/dev/tools.py",
    ], text=True)).body if isinstance(n, ast.FunctionDef) and n.name == "dev_tool_schemas")
    scope = dict(vars(tools_module))
    scope["reproduction"] = SimpleNamespace(
        schema=reproduction.schema, purpose_schema=reproduction.purpose_schema,
        DESCRIPTION=old["DESCRIPTION"])
    exec(compile(ast.Module(body=[function], type_ignores=[]), "old-schema", "exec"), scope)
    return scope["dev_tool_schemas"], old["DESCRIPTION"]


def test_control_is_exact_prior_schema_and_only_probe_surface_changes(monkeypatch):
    legacy_schema, legacy_description = historical_schema(control.LEGACY)
    base_schema, base_description = historical_schema(control.BASE)
    assert legacy_description == control.LEGACY_DESCRIPTION
    # The closed comparison's common finish prose predates finish-time replay.
    # Exercise its actual BASE/LEGACY inputs, not a projection of today's finish tool.
    monkeypatch.setattr(reproduction, "DESCRIPTION", base_description)
    monkeypatch.setattr(runner, "dev_tool_schemas", base_schema)
    schemas = base_schema(finish_enabled=True, allowed_tools=["run_probe", "finish_task"])
    before = copy.deepcopy(schemas)
    a = control.project_tools(schemas, "A")
    assert a == legacy_schema(
        finish_enabled=True, allowed_tools=["run_probe", "finish_task"])
    # Cover the distinct pinned schema configurations in the fast regression suite.
    for options in (
        {"allowed_tools": ["read_file", "search_files", "replace_text", "run_check",
                           "run_tests", "run_probe", "finish_task", "stop_task"],
         "check_ids": ["public-check"], "test_suite_ids": ["public-tests"]},
        {"allowed_tools": tools_module.ALL_DEV_TOOLS},
        {"allowed_tools": tools_module.ALL_DEV_TOOLS, "check_ids": ["first", "second"]},
        {"allowed_tools": DEV_READ_TOOLS | DEV_SINGLE_ACTION_TOOLS,
         "check_ids": ["first", "second"]},
    ):
        current = base_schema(finish_enabled=True, **options)
        restored = control.project_tools(current, "A")
        legacy = legacy_schema(finish_enabled=True, **options)
        assert json.dumps(restored) == json.dumps(legacy)  # Includes field order.
    assert schemas == before == control.project_tools(schemas, "B")
    assert [t for t in a if t["name"] != "run_probe"] == [
        t for t in schemas if t["name"] != "run_probe"]
    current_probe = next(t for t in schemas if t["name"] == "run_probe")
    old_probe = next(t for t in a if t["name"] == "run_probe")
    assert old_probe["parameters"]["properties"]["reproduction"] == reproduction.schema()
    assert "purpose" not in old_probe["parameters"]["properties"]
    with control.assigned("A"):
        assert runner.dev_tool_schemas(
            finish_enabled=True, allowed_tools=["run_probe", "finish_task"]) == a
        assert model.DEV_SYSTEM_PROMPT == runner.DEV_SYSTEM_PROMPT
        assert reproduction.review([], "D1")["required"]["status"] == "UNKNOWN"
    assert len(current_probe["parameters"]["required"]) == len(old_probe["parameters"]["required"])
    with pytest.raises(RuntimeError), control.assigned("A"):
        raise RuntimeError("restore on exception")
    assert runner.dev_tool_schemas(
        finish_enabled=True, allowed_tools=["run_probe", "finish_task"]) == schemas


@pytest.mark.parametrize("arm", ["A", "B"])
def test_both_arms_bind_replay_and_preserve_separate_task_scope(gateway_factory, arm):
    with control.assigned(arm):
        gateway, journal, workspace = gateway_factory()
        backend = gateway.probe_sandbox = ExecutingProbe()
        call = selected_probe(gateway.public_task, arm)
        first = gateway.execute(call)
        assert first.output["reproduction"]["comparison"] == "mismatched"
        if arm == "A":
            rejected = gateway.execute(probe(gateway.public_task, "unoffered"))
            assert rejected.status == "failed" and backend.calls == 1
        gateway.execute_batch(read_calls())
        assert gateway.execute(mutation_call(gateway)).status == "succeeded"
        current = restore(gateway, journal, workspace, gateway.public_task, backend)
        replay = selected_probe(gateway.public_task, arm, replay=True)
        after = current.execute(replay)
        assert after.output["reproduction"]["comparison"] == "matched"
        assert after.output["reproduction"]["binding"] == first.output["reproduction"]["binding"]
        assert current.execute(replay).replayed and backend.calls == 2
        review = current.reproduction_review(diff_hash=current.current_diff_hash)
        assert review["items"][0]["evidence"]["status"] == "SUPPORTED"
        assert review["required"]["status"] == "UNKNOWN"


def selected_probe(task, arm, *, replay=False):
    call = probe(task, "replay" if replay else "original", replay="original" if replay else None)
    if arm == "A":
        purpose = call.arguments.pop("purpose")
        call.arguments["reproduction"] = (
            {k: v for k, v in purpose.items() if k != "kind"} if purpose else None)
        if not replay:
            call.arguments["python_source"] = (
                "import json\nfrom mini_data_utils.csvlite import parse_rows\n"
                f"print(json.dumps(parse_rows({TEXT!r})))")
    return call


@pytest.mark.parametrize("arm", ["A", "B"])
def test_both_arms_reach_isolated_mock_evaluation(tmp_path, monkeypatch, smoke_package, arm):
    backend = ExecutingProbe()

    class ReproduceThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            review = json.loads(context)["reproduction_review"]
            if not review["items"]:
                return DevModelTurn(tool_calls=[selected_probe(smoke_package.public, arm)])
            if review["items"][0]["comparison_status"] == "current_diff_not_observed":
                return DevModelTurn(tool_calls=[
                    selected_probe(smoke_package.public, arm, replay=True)])
            return super().next_turn(context, tools)

    monkeypatch.setattr(runner, "DockerProbeSandbox", lambda: backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ReproduceThenMock)
    request = mock_request(tmp_path, policy="none").model_copy(update={
        "enable_probes": True, "context_policy": "segmented-v1",
        "history_search_policy": "public-v1",
    })
    with control.assigned(arm):
        result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert backend.calls == 2 and result["evaluator"]["claim_eligible"] is False


def _child(queue, arm):
    with control.assigned(arm):
        schema = runner.dev_tool_schemas(finish_enabled=False, allowed_tools=["run_probe"])[0]
        queue.put(list(schema["parameters"]["properties"]))


def test_spawned_control_cannot_leak_to_treatment():
    ctx = multiprocessing.get_context("spawn")
    for arm in "AB":
        queue = ctx.Queue()
        child = ctx.Process(target=_child, args=(queue, arm))
        child.start()
        fields = queue.get(timeout=20)
        child.join(20)
        assert child.exitcode == 0
        assert ("purpose" in fields) is (arm == "B")
        queue.close()


def test_initial_pair_rejects_any_other_wire_difference():
    state = {"public_task": {"issue": {"title": "Public task"}},
             "current_diff": {"patch": "", "patch_hash": "D1"},
             "segment_handoff": {"segment_id": "derived"}, "remaining_budget": {"calls": 40}}
    wire = {"input": assemble_model_input(system_prompt="same", state=state, history=[],
                                          context_policy="segmented-v1"),
            "tools": dev_tool_schemas(finish_enabled=False, allowed_tools=["run_probe"])}
    a = copy.deepcopy(wire)
    a["tools"] = control.project_tools(a["tools"], "A")
    assert panel.initial_pair({"A": a, "B": wire})["input_equal_after_segment_normalization"]
    for key, value, error in (
        ("max_output_tokens", 1, ContractError), ("input", [], RecoveryError),
    ):
        bad = copy.deepcopy(a)
        bad[key] = value
        with pytest.raises(error):
            panel.initial_pair({"A": bad, "B": wire})


def audit_fixture():
    row, old = reviewed_row("UNKNOWN")
    observed = old["events"][0]["payload"]["result"]["output"]["stdout"]
    raw = {"name": "run_probe", "action_id": "probe", "arguments": {
        "purpose": {"kind": "original_requirement"}, "python_source": "public caller"}}
    wire = old["events"][1]["payload"]["wire"]
    calls = [
        event(0, "provider_call_started", {"turn_id": "probe-turn", "wire": wire,
                                          "actual_request_hash": sha256_json(wire)}),
        event(1, "turn_decision_recorded", {"turn_id": "probe-turn", "tool_calls": [raw]}),
        event(2, "action_finished", {"result": {
            **old["events"][0]["payload"]["result"],
            "input_hash": grading.common.input_hash(raw),
            "output": {"stdout": observed, "reproduction": {
                "binding": {"case_id": "case-fixture"}, "observed_json": "false",
                "comparison": "mismatched", "reason": None}}}}),
    ]
    # Delivered case and value are synthetic public fields, not semantic ground truth.
    later_wire = copy.deepcopy(wire)
    state = {"public_task": {"issue": {"title": "Original issue"}},
             "current_diff": {"patch_hash": "D1"}, "observed": observed,
             "case": "case-fixture", "value": "false"}
    later_wire["input"] = assemble_model_input(
        system_prompt="same", state=state, history=[], context_policy="segmented-v1")
    later = copy.deepcopy(old["events"][1:])
    for e in later:
        e["sequence"] += 1
    later[0]["payload"].update(wire=later_wire, actual_request_hash=sha256_json(later_wire))
    public = {"public_id": row["public_id"], "events": calls + later}
    row.update(public_hash=sha256_json(public), reviewed_decisions=[1, 4])
    claim = row["claims"][0]
    claim.update(decision_sequence=4, request_sequence=3,
                 request_hash=sha256_json(later_wire))
    claim["evidence"][0].update(sequence=2, event_hash=calls[-1]["event_hash"])
    item, = grading.inventory(public)
    use = {k: claim[k] for k in ("decision_sequence", "action_id", "input_hash",
                                 "request_sequence", "request_hash", "diff_hash")}
    use.update(text=claim["text"], rationale="Fixture tests provenance only.", semantic_review=True)
    row["probes"] = [{"mechanical": item, "intent_scope": "ORIGINAL",
                      "execution_scope": "ORIGINAL", "scope_rationale": "Synthetic mapping.",
                      "evidence": [{"sequence": 1, "event_hash": calls[1]["event_hash"],
                                    "text": "public caller"}], "use": use}]
    return row, public


def test_grader_separates_binding_delivery_use_and_judgment():
    row, public = audit_fixture()
    result = grading.validate_annotation(row, public)
    assert result["bound_comparison_uses"] == 1
    assert result["unknown_claim"] and not result["bad_claim"]
    for alteration in ("omit", "wrong_receipt", "wrong_input", "helper", "unbound"):
        bad = copy.deepcopy(row)
        if alteration == "omit":
            bad["probes"] = []
        elif alteration == "wrong_receipt":
            bad["probes"][0]["mechanical"]["receipt_hash"] = "wrong"
        elif alteration == "wrong_input":
            bad["probes"][0]["use"]["request_hash"] = "wrong"
        elif alteration == "helper":
            bad["probes"][0]["execution_scope"] = "HELPER"
        else:
            bad["probes"][0]["mechanical"]["bound"] = False
        with pytest.raises(ContractError):
            grading.validate_annotation(bad, public)
    row["probes"][0]["use"] = None
    assert grading.validate_annotation(row, public)["bound_comparison_uses"] == 0


def test_allocation_and_serial_adapter_preserve_exact_new_authorization():
    assert panel.allocation(3)["total_cap_usd"] == "5.28"
    with pytest.raises(ContractError):
        panel.allocation(6)
    original_panel = shared.panel
    with execution.configured():
        assert shared.panel is panel and shared.off is control and shared.grading is grading
        for authorization in ({}, {"repeat_per_arm": 6}, {"repeat_per_arm": 3}):
            with pytest.raises(ContractError):
                shared.authorize("unapproved", authorization)
    assert shared.panel is original_panel


@pytest.mark.parametrize("uncertain", [False, True])
def test_serial_comparison_stops_without_retry_on_unknown_billing(tmp_path, monkeypatch, uncertain):
    assigned = panel.allocation(3)
    packet = {**assigned, "live_root": str(tmp_path / "live"), "pricing": {"test": "only"},
              "rows": [{"row_id": label, "arm": label[0]} for label in assigned["order"]]}
    monkeypatch.setattr(panel, "validate", lambda *_: packet)
    calls = []

    def worker(rows, **kwargs):
        row, = rows
        calls.append(row["row_id"])
        assert kwargs["total_cap"] == Decimal("0.88") and kwargs["workers"] == 1
        assert kwargs["initializer"] is (
            control.initialize_off_worker if row["arm"] == "A"
            else shared.parallel_dev_batch.initialize_worker)
        known = not uncertain or row["arm"] == "A"
        return {"rows": [{"row_id": row["row_id"], "ok": known, "accounting": {
            "billing_known": known, "counting_known": True, "cost_nanos": 880_000_000}}],
            "stopped": not known}

    monkeypatch.setattr(shared.parallel_dev_batch, "run_parallel_rows", worker)
    authorization = {
        "approved": True, "manifest_hash": "fixture",
        "task": str(shared.repository_root() / panel.TASK), "model": panel.MODEL,
        "credential_file": str(shared.repository_root() / ".env"), "repeat_per_arm": 3,
        "total_cap_usd": "5.28", "human_message": "TEST FIXTURE, no dispatch authority.",
    }
    rates = {"verified_on": datetime.now(UTC).date().isoformat(),
             "source": "https://developers.openai.com/api/docs/pricing",
             "prices": packet["pricing"]}
    with execution.configured():
        with pytest.raises(ContractError):
            shared.collect(tmp_path, "fixture", {**authorization, "total_cap_usd": "10.56"}, rates)
        assert not calls
        result = shared.collect(tmp_path, "fixture", authorization, rates)
        with pytest.raises(ContractError):
            shared.collect(tmp_path, "fixture", authorization, rates)
    assert calls == assigned["order"][:2 if uncertain else 6]
    assert result["stopped"] is uncertain
    assert result["not_run"] == assigned["order"][len(calls):]


def test_packet_rejects_wrong_comparison_and_allocation(tmp_path, monkeypatch):
    current = {"head": "fixture", "comparison": "probe-purpose-v1"}
    monkeypatch.setattr(panel, "identity", lambda *_: current)
    monkeypatch.setattr(panel.prior, "read_ref", lambda _: b"")
    assigned = panel.allocation(3)
    packet = {"schema": "verification-state-comparison-v2", **current, **assigned,
              "paid_authorized": False, "live_root": str(tmp_path / "live"),
              "specification": panel.prior.file_ref(panel.repository_root() / panel.SPEC),
              "validation": {}, "preexisting_guidance": {}, "files": [],
              "initial": {}, "programs": {}, "rows": [
                  {"row_id": label, "arm": label[0],
                   "public_id": "case-" + sha256_json({"head": "fixture", "row": label})[-12:],
                   "request": panel.request(tmp_path / "live", label).model_dump(mode="json")}
                  for label in assigned["order"]]}

    def validate(value):
        (tmp_path / "manifest.json").write_text(json.dumps(value), encoding="utf-8")
        return panel.validate(tmp_path, sha256_json(value))

    assert validate(packet)["comparison"] == "probe-purpose-v1"
    for key, value in (("comparison", "other"), ("repeat_per_arm", 6),
                       ("total_cap_usd", "10.56"), ("rows", packet["rows"][:-1])):
        with pytest.raises(ContractError):
            validate({**packet, key: value})
