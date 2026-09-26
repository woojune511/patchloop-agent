from __future__ import annotations

import copy
import json
from dataclasses import dataclass

import pytest
from pydantic import ValidationError
from test_dev_probes import FakeProbe

from diagnostics import paired_observation as paired
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ActionConflict, ContractError


def design():
    return {
        "requirement_ids": ["issue-1"],
        "cases": [
            {"input": "A quoted field with an embedded newline", "expected_json": '[["x\\ny"]]',
             "evidence_ref": None},
            {"input": "An ordinary single field", "expected_json": '[["x"]]',
             "evidence_ref": None},
        ],
        "justification": "The public issue requires quoted newlines and ordinary CSV behavior.",
        "refutation": "Separate records for a quoted field or changed ordinary CSV output.",
        "limitations": "These two selected inputs do not cover every CSV feature.",
    }


def call(action_id="comparison", value=None):
    return RequestedTool(
        name="run_probe", action_id=action_id,
        arguments={"question": "Do both public CSV cases behave as required?",
                   "python_source": "print('public fixture')",
                   "comparison": design() if value is None else value},
        turn_decision=PublicTurnDecision(mode="verify", basis="Compare two public inputs."),
    )


class JSONProbe(FakeProbe):
    stdout = '{"a":[["x"],["y"]],"b":[["x"]]}'

    def run_probe(self, *args, **kwargs):
        result = super().run_probe(*args, **kwargs)
        result.update(status="passed", exit_code=0, stdout=self.stdout)
        return result


@pytest.fixture
def gateway(gateway_factory):
    original, journal, workspace = gateway_factory()
    backend = JSONProbe()
    gateway = paired.gateway_type(DevToolGateway)(
        workspace=workspace, public_task=original.public_task, sandbox=original.sandbox,
        journal=journal, limits=DevLimits(), probe_sandbox=backend,
    )
    return gateway, backend


@pytest.mark.parametrize("change", [
    "reference", "probe_reference", "count", "extra", "nan", "duplicate", "oversize",
])
def test_invalid_design_fails_before_execution(gateway, change):
    selected, backend = gateway
    value = design()
    if change == "reference":
        value["requirement_ids"] = ["not-public"]
    elif change == "probe_reference":
        value["cases"][0]["evidence_ref"] = "check:existing-unit-tests"
    elif change == "count":
        value["cases"].pop()
    elif change == "extra":
        value["hidden_verdict"] = "untrusted"
    else:
        value["cases"][0]["expected_json"] = {
            "nan": "NaN", "duplicate": '{"x":1,"x":2}', "oversize": '"' + "x" * 2047 + '"',
        }[change]
    result = selected.execute(call(value=value))
    assert result.status == "failed" and backend.calls == 0
    assert result.output[paired.FIELD]["status"] == "declaration_rejected"
    assert result.output[paired.FIELD]["execution_started"] is False
    assert selected.checks_by_diff == {}


def test_action_freezes_design_before_probe_and_replay_checks_it(gateway):
    selected, backend = gateway
    original = backend.run_probe

    def observe(*args, **kwargs):
        start = selected.journal.events()[-1]
        assert start["event_type"] == "action_started"
        assert start["payload"]["arguments"]["comparison"] == design()
        assert "expected_json" not in kwargs and "comparison" not in kwargs
        return original(*args, **kwargs)

    backend.run_probe = observe
    requested = call()
    result = selected.execute(requested)
    receipt = result.output[paired.FIELD]
    assert result.status == "succeeded"
    assert receipt["observation"]["status"] == "mismatched"
    assert receipt["observation"]["semantic_verdict"] is None
    assert receipt["observation"]["diff_hash"] == result.workspace_diff_hash
    reference = receipt["requirement_references"][0]
    assert reference["id"] == "issue-1"
    assert reference["text"] == selected.public_task.issue.description.strip()
    assert selected.checks_by_diff == {}  # A probe never becomes a required check PASS.
    assert selected.execute(requested).replayed and backend.calls == 1
    changed = copy.deepcopy(requested)
    changed.arguments["comparison"]["cases"][0]["expected_json"] = "[]"
    with pytest.raises(ActionConflict):
        selected.execute(changed)
    assert backend.calls == 1


@pytest.mark.parametrize("stdout,changes,status,reason", [
    ('{"a":[["x\\ny"]],"b":[["x"]]}', {}, "matched", None),
    ('{"a":1,"b":2}', {}, "mismatched", None),
    ('{"a":1}', {}, "not_compared", "both_case_observations_required"),
    ('[1,2]', {}, "not_compared", "both_case_observations_required"),
    ('{"a":1,"b":2}', {"exit_code": 1}, "not_compared", "execution_not_healthy"),
    ('{"a":1,"b":2}', {"cleanup_failed": True}, "not_compared", "execution_not_healthy"),
    ('{"a":1,"b":2}', {"timed_out": True}, "not_compared", "execution_not_healthy"),
    ('partial', {}, "not_compared", "stdout_not_json"),
])
def test_observation_is_not_execution_or_semantic_correctness(
    smoke_package, stdout, changes, status, reason,
):
    prepared = paired.prepare(design(), smoke_package.public)
    result = paired.probe_comparison(prepared, {
        "status": "passed", "exit_code": 0, "stdout": stdout,
        "source_hash": "source", "diff_hash": "diff", **changes,
    })["observation"]
    assert (result["status"], result["reason"]) == (status, reason)
    assert result["semantic_verdict"] is None and result["coverage_status"] == "not_assessed"


def test_check_reuse_selects_current_public_reference_ids(smoke_package):
    prepared = paired.prepare(design(), smoke_package.public)
    for case in prepared["design"]["cases"]:
        case["evidence_ref"] = "read:read-check"
    result = {"action_id": "read-check", "tool": "read_file", "status": "succeeded",
              "workspace_diff_hash": "diff", "output": {
                  "spans": [{"content": "assert parse_rows('x') == [['x']]",
                             "path": "tests/test_csv.py", "start_line": 1, "end_line": 1}],
              }}
    events = [{"event_type": "action_finished", "payload": {"result": result}}]
    args = dict(check_id="existing-unit-tests", public_task=smoke_package.public,
                events=events, diff_hash="diff")
    assert len(paired.bind_check(prepared, **args)) == 2
    result["workspace_diff_hash"] = "older"
    with pytest.raises(ContractError, match="current read"):
        paired.bind_check(prepared, **args)
    result["workspace_diff_hash"] = "diff"
    prepared["design"]["cases"][1]["evidence_ref"] = "check:not-selected"
    with pytest.raises(ContractError, match="select this check"):
        paired.bind_check(prepared, **args)
    for case in prepared["design"]["cases"]:
        case["evidence_ref"] = "check:existing-unit-tests"
    assert len(paired.bind_check(prepared, **args)) == 2  # Linkage only, not coverage.


@pytest.mark.parametrize("mode", ["reuse", "limitation", "missing_reference", "unknown_check"])
def test_selected_check_uses_normal_execution_and_replay(gateway, mode):
    selected, backend = gateway
    value = design() if mode != "limitation" else None
    if value is not None:
        for case in value["cases"]:
            case["evidence_ref"] = (
                "check:existing-unit-tests" if mode != "missing_reference" else "missing case")
    requested = RequestedTool(
        name="run_check", action_id="compare-check",
        arguments={"check_id": "unknown" if mode == "unknown_check" else "existing-unit-tests",
                   "comparison": value},
        turn_decision=PublicTurnDecision(mode="verify", basis="Public check scope is limited."),
    )
    result = selected.execute(requested)
    assert backend.calls == 0
    if mode in {"missing_reference", "unknown_check"}:
        assert result.status == "failed" and selected.checks_by_diff == {}
        return
    assert result.status == "succeeded" and result.output["passed"] is True
    observed = result.output[paired.FIELD]
    assert observed["observation"]["status"] == "check_passed"
    assert observed["observation"]["semantic_verdict"] is None
    assert (observed["design"] is None) is (mode == "limitation")
    assert observed["observation"]["comparison_status"] == (
        "not_requested" if mode == "limitation" else "model_interpretation_required")
    assert selected.execute(requested).replayed


def event(kind, **payload):
    return {"event_type": kind, "payload": payload}


def test_phase_is_bounded_and_observation_survives_mutation_and_handoff():
    events = [event("diagnostic_candidate_seeded", seed_hash="seed")]
    assert paired.project(events)["phase"] == "observe"
    original = copy.deepcopy(events)
    assert paired.project(events) == paired.project(events) and events == original
    events.extend([event("turn_started")] * paired.MAX_TURNS)
    assert paired.project(events)["phase"] == "unobserved_limit"
    assert paired.project(original, "changed")["phase"] == "unobserved_candidate_changed"
    events = original + [event("turn_started"), event("action_started", action_id="check",
              arguments={"comparison": None}, turn_decision={"basis": "Scope unclear."})]
    result = {"action_id": "check", "input_hash": "hash", "tool": "run_check",
              "status": "succeeded", "workspace_diff_hash": "seed", "output": {}}
    events.append(event("action_finished", result=result))
    events.extend([event("context_segment_started"), event("turn_started")])
    current = paired.project(events, "seed")
    stale = paired.project(events, "changed")
    assert current["phase"] == stale["phase"] == "returned_to_repair"
    assert current["phase_calls_started"] == 1
    assert current["result"]["currency"] == "current"
    assert stale["result"]["currency"] == "historical"
    assert stale["result"]["public_basis"] == "Scope unclear."


def test_phase_never_adds_tools_or_spends_the_protected_completion_budget():
    @dataclass(frozen=True)
    class Policy:
        allowed_tools: frozenset

    enabled = Policy(frozenset({"read_file", "run_probe", "replace_text", "finish_task"}))
    assert paired.restrict(enabled, {"phase": "observe"}).allowed_tools == {
        "read_file", "run_probe",
    }
    exhausted = Policy(frozenset({"finish_task", "stop_task"}))
    assert paired.restrict(exhausted, {"phase": "observe"}) is exhausted
    assert paired.restrict(enabled, {"phase": "returned_to_repair"}) is enabled


def test_completed_mutation_cannot_rearm_phase_even_after_reverting_to_seed():
    events = [event("diagnostic_candidate_seeded", seed_hash="seed")]
    for diff in ("changed", "seed"):
        events.append(event("action_finished", result={
            "action_id": "edit-" + diff, "tool": "replace_text", "status": "succeeded",
            "output": {"worktree_diff_hash": diff},
        }))
    assert paired.project(events, "seed")["phase"] == "unobserved_candidate_changed"


def test_schema_is_strict_and_rejects_unbounded_or_missing_case_fields(smoke_package):
    schema = paired.design_schema(nullable=False)
    assert "$defs" not in schema and "$ref" not in json.dumps(schema)
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    item = schema["properties"]["cases"]["items"]
    assert set(item["required"]) == set(item["properties"])
    value = design()
    del value["cases"][0]["expected_json"]
    with pytest.raises(ValidationError):
        paired.prepare(value, smoke_package.public)


def test_catalog_uses_public_paragraphs_and_bounded_current_successful_reads(smoke_package):
    public = smoke_package.public.model_dump(mode="json")
    public["issue"]["description"] = "First condition.\n\nPreserve another condition."
    events = [event("action_finished", result={
        "action_id": str(i), "tool": "read_file", "status": "succeeded",
        "workspace_diff_hash": "current", "output": {"spans": [{
            "path": "public.py", "start_line": i + 1, "end_line": i + 1, "content": "public",
        }]},
    }) for i in range(20)]
    for change in ({"workspace_diff_hash": "old"}, {"status": "failed"}, {"tool": "search_files"}):
        row = copy.deepcopy(events[-1])
        row["payload"]["result"].update(change)
        row["payload"]["result"]["action_id"] = "excluded"
        events.append(row)
    original = copy.deepcopy(events)
    catalog = paired.evidence_catalog(public, events, "current")
    assert catalog == paired.evidence_catalog(public, events, "current") and events == original
    assert catalog["requirements"][1]["text"] == "First condition."
    assert catalog["requirements"][2]["text"] == "Preserve another condition."
    assert [r["id"] for r in catalog["reads"]] == [f"read:{i}" for i in range(4, 20)]
    assert "content" not in catalog["reads"][0]["spans"][0]
    schema = paired.design_schema(nullable=True, catalog=catalog)
    assert schema["properties"]["requirement_ids"]["items"]["enum"] == [
        "issue-title", "issue-1", "issue-2"]
    assert schema["properties"]["cases"]["items"]["properties"]["evidence_ref"]["enum"] == [
        "check:existing-unit-tests", *[f"read:{i}" for i in range(4, 20)]]
    assert schema["type"] == ["object", "null"]
    probe_schema = paired.design_schema(nullable=False, catalog=catalog)
    probe_ref = probe_schema["properties"]["cases"]["items"]["properties"]["evidence_ref"]
    assert probe_ref["enum"] == [None]
    changed = copy.deepcopy(public)
    changed["issue"]["description"] = "Changed requirement."
    assert paired.evidence_catalog(changed)["public_task_hash"] != catalog["public_task_hash"]


def _comparison_result(action_id, *, rejected=False, legacy=False):
    return {"action_id": action_id, "input_hash": "hash-" + action_id,
            "tool": "run_probe", "status": "failed", "error_code": "CONTRACT_ERROR",
            "message": "Invalid declaration" if rejected else "Execution failed",
            "workspace_diff_hash": "seed", "output": {
                paired.FIELD: {"status": "declaration_rejected", "execution_started": False},
            } if rejected and not legacy else {}}


def test_declaration_corrections_use_original_four_calls_without_handoff_reset():
    events = [event("diagnostic_candidate_seeded", seed_hash="seed")]
    for index in range(paired.MAX_TURNS):
        action = str(index)
        events.extend([event("turn_started"), event("action_started", action_id=action,
            arguments={"comparison": {}}, turn_decision={"basis": "Correct declaration."}),
            event("action_finished", result=_comparison_result(action, rejected=True)),
            event("context_segment_started")])
        view = paired.project(events, "seed")
        assert view["rejected_declarations"] == index + 1 and view["result"] is None
        assert view["last_declaration_error"]["action_id"] == action
        assert view["phase"] == ("observe" if index < 3 else "unobserved_limit")
    final = paired.project(events + [event("context_segment_started")])
    assert final["phase"] == "unobserved_limit"


@pytest.mark.parametrize("legacy", [False, True])
def test_execution_and_legacy_errors_do_not_reopen_comparison(legacy):
    events = [event("diagnostic_candidate_seeded", seed_hash="seed"), event("turn_started"),
        event("action_started", action_id="first", arguments={"comparison": {}}),
        event("action_finished", result=_comparison_result(
            "first", rejected=legacy, legacy=legacy))]
    view = paired.project(events)
    assert view["phase"] == "returned_to_repair" and view["rejected_declarations"] == 0
    assert view["last_declaration_error"] is None and view["result"]["status"] == "failed"


def test_rejected_check_correction_preserves_replay_identity(gateway, monkeypatch):
    selected, _ = gateway
    selected.journal.append("diagnostic_candidate_seeded", {
        "seed_hash": selected.current_diff.patch_hash})
    executions = []
    original = selected.sandbox.run_check

    def counted(*args, **kwargs):
        executions.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(selected.sandbox, "run_check", counted)
    invalid = RequestedTool(name="run_check", action_id="bad-check", arguments={
        "check_id": "existing-unit-tests", "comparison": design(),
    }, turn_decision=PublicTurnDecision(mode="verify", basis="Select check evidence."))
    selected.journal.append("turn_started", {"turn_id": "declaration-1"})
    rejected = selected.execute(invalid)
    assert rejected.status == "failed" and not executions
    assert selected.execute(invalid).replayed and not executions
    assert paired.project(selected.journal.events())["rejected_declarations"] == 1
    corrected = copy.deepcopy(invalid)
    for case in corrected.arguments["comparison"]["cases"]:
        case["evidence_ref"] = "check:existing-unit-tests"
    with pytest.raises(ActionConflict):
        selected.execute(corrected)
    corrected.action_id = "corrected-check"
    selected.journal.append("turn_started", {"turn_id": "declaration-2"})
    result = selected.execute(corrected)
    assert result.status == "succeeded" and len(executions) == 1
    assert selected.execute(corrected).replayed and len(executions) == 1
    view = paired.project(selected.journal.events())
    assert view["phase"] == "returned_to_repair" and view["phase_calls_started"] == 2
    assert view["result"]["action_id"] == "corrected-check"
    assert view["last_declaration_error"]["action_id"] == "bad-check"


def test_gateway_execution_error_has_no_declaration_correction_marker(gateway, monkeypatch):
    selected, backend = gateway

    def failure(*args, **kwargs):
        backend.calls += 1
        raise ContractError("execution fixture failure")

    monkeypatch.setattr(backend, "run_probe", failure)
    result = selected.execute(call())
    assert result.status == "failed" and backend.calls == 1
    assert paired.FIELD not in result.output
