"""First-plan timing contracts; authored smoke plans are not quality evidence."""
from __future__ import annotations

import copy

import httpx
import pytest
from pydantic import ValidationError
from test_dev_planning import call, request
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from typer.testing import CliRunner

from diagnostics.segmented_input_audit import verify_turn
from patchloop.artifacts import ArtifactStore
from patchloop.cli import app
from patchloop.dev import runner
from patchloop.dev import working_plan as plans
from patchloop.dev.contracts import DevRunRequest, dev_tool_surface_hash
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.errors import ResumeContractMismatch
from patchloop.util import canonical_json

POLICY = plans.AFTER_SOURCE_POLICY
SOURCE = {"path": "module.py", "file_hash": "source-hash", "start_line": 1,
          "end_line": 1, "content": "def parse_rows(text):"}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("first-plan timing verification must not dispatch real provider requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def view(journal, *, gate="needs_mutation"):
    return plans.project(journal.events(), diff_hash="d1", gate=gate, policy=POLICY)


def record(journal, text=None, *, turn="t1"):
    return plans.record(journal, [call(text)], turn_id=turn, diff_hash="d1",
                        gate="needs_mutation", policy=POLICY)


def result(journal, tool="read_file", *, status="succeeded", spans=()):
    return journal.append("action_finished", {"result": {
        "tool": tool, "status": status, "action_id": "a1", "output": {"spans": list(spans)},
    }})


def test_timing_only_identity_and_schema_contrast(tmp_path, monkeypatch):
    old_hashes = {
        "none": "sha256:25f1db63f18b3f138ee8bdc8686ad320d7c9a3965d4e10acd1055fdd590555b7",
        plans.POLICY: "sha256:e9a1a5de627227db9bcd3ee26d3ff7f55391f21c8775f814a81dcc282fc0bf65",
        plans.EVIDENCE_POLICY:
            "sha256:678b4ce80bc4fa2061b3c0594ac3ecd75f64f18668f8f9fbe9316792b9b053aa",
        plans.ASSUMPTION_POLICY:
            "sha256:dedce78bfb34a2dc417e1a59cdd65e596562e1a25d648cb3bef9c4533bc912fb",
    }
    assert {p: dev_tool_surface_hash(planning_policy=p) for p in old_hashes} == old_hashes
    old, new = plans.instructions(), plans.instructions(POLICY)
    assert old.partition("State the required behavior")[2] == new.partition(
        "State the required behavior")[2]
    assert "In the first tool response" not in new
    assert plans.AFTER_SOURCE_TIMING in new
    for hint in ("pydantic", "hf-hub", "endpoint", "thinking_field", "reference_patch"):
        assert hint not in new
    before, after = plans.contract(), plans.contract(POLICY)
    for key in ("policy", "review", "instructions_hash"):
        assert before.pop(key) != after.pop(key)
    assert before == after
    for probe in ("none", "cases-v1"):
        options = dict(finish_enabled=True, check_ids=["c"], probe_policy=probe,
                       allowed_tools=["read_file", "search_files", "replace_text", "run_probe",
                                      "run_check", "finish_task", "stop_task"])
        assert dev_tool_schemas(**options, planning_policy=POLICY) == dev_tool_schemas(
            **options, planning_policy=plans.POLICY)
    policies = (*old_hashes, POLICY)
    hashes = {p: (runner._model_hash(request(tmp_path, p), None),
                  dev_tool_surface_hash(planning_policy=p)) for p in policies}
    assert len(set(hashes.values())) == 5
    monkeypatch.setattr(plans, "AFTER_SOURCE_TIMING", plans.AFTER_SOURCE_TIMING + ".")
    for p in policies:
        changed = (runner._model_hash(request(tmp_path, p), None),
                   dev_tool_surface_hash(planning_policy=p))
        assert (hashes[p] == changed) == (p != POLICY)


@pytest.mark.parametrize("context", ["append-v1", "segmented-v1"])
def test_cli_and_context_contract(tmp_path, monkeypatch, context):
    base, captured = request(tmp_path, POLICY), []
    default = DevRunRequest(provider="mock", task=base.task, model="mock-dev")
    assert default.planning_policy == "none"
    monkeypatch.setattr(runner, "run_dev", lambda req: captured.append(req) or {})
    selected = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
        "--planning-policy", POLICY, "--context-policy", context,
    ])
    assert selected.exit_code == 0, selected.output
    assert captured[0].planning_policy == POLICY and captured[0].context_policy == context
    with pytest.raises(ValidationError, match="requires append-v1 or segmented-v1"):
        DevRunRequest.model_validate({**base.model_dump(), "context_policy": "native-window-v1"})


@pytest.mark.parametrize("tool,status,spans", [
    ("search_files", "succeeded", []),
    ("read_file", "succeeded", []),  # EOF, empty file, or a line over the output limit.
    ("read_file", "failed", [SOURCE]),
    ("search_files", "failed", [SOURCE]),
    ("read_file", "succeeded", [{**SOURCE, "content": ""}]),
    ("read_file", "succeeded", [{k: v for k, v in SOURCE.items() if k != "content"}]),
    ("run_check", "succeeded", [SOURCE]),
    ("run_probe", "succeeded", [SOURCE]),
    ("replace_text", "failed", [SOURCE]),
])
def test_no_source_defers_all_review_requests(tmp_path, tool, status, spans):
    journal = DevJournal(tmp_path, "run_dev_plan")
    journal.append("context_segment_started", {"reason": "initial"})
    journal.append("action_started", {"tool": "read_file"})
    assert not view(journal)["review_request"]["requested"]
    assert record(journal)["status"] == "not_requested"
    result(journal, tool, status=status, spans=spans)
    journal.append("context_segment_started", {"reason": "request_bytes"})
    current = view(journal, gate="ready_to_submit")
    assert current["plan"] is None
    assert current["review_request"] == {
        "requested": False, "reasons": [], "action_ids": [], "omitted_action_count": 0,
    }


@pytest.mark.parametrize("tool", ["read_file", "search_files"])
def test_first_source_starts_persistent_initial_request_then_normal_reviews(tmp_path, tool):
    journal = DevJournal(tmp_path, "run_dev_plan")
    journal.append("context_segment_started", {"reason": "initial"})
    record(journal)
    result(journal, tool, spans=[SOURCE])
    assert view(journal)["review_request"]["reasons"] == ["initial_plan"]
    journal.append("turn_started", {"turn_id": "not-a-decision"})
    assert view(journal)["review_request"]["reasons"] == ["initial_plan"]
    assert record(journal, turn="t2")["status"] == "not_requested"
    assert view(journal)["review_request"]["reasons"] == ["initial_plan"]
    saved = record(journal, "Public task and observed source leave an open question.", turn="t3")
    before = journal.path.read_bytes()
    assert record(journal, "Do not overwrite on replay.", turn="t3") == saved
    assert journal.path.read_bytes() == before
    result(journal, tool, spans=[SOURCE])
    assert not view(journal)["review_request"]["requested"]
    for action in ("replace_text", "run_check", "run_probe"):
        result(journal, action, status="failed")
    journal.append("context_segment_started", {"reason": "major_result_reviewed"})
    assert view(journal, gate="ready_to_submit")["review_request"]["reasons"] == [
        "context_handoff", "mutation_result", "check_result", "probe_result",
        "first_ready_to_submit",
    ]
    record(journal, turn="t4")
    assert not view(journal)["review_request"]["requested"]
    assert view(journal)["plan"]["revision"] == 1


def test_voluntary_early_plan_is_retained_without_an_action_gate(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_plan")
    assert record(journal, "An early public hypothesis.")["status"] == "created"
    result(journal, "run_check", status="failed")
    assert view(journal)["review_request"]["reasons"] == ["check_result"]
    assert record(journal, {}, turn="t2")["status"] == "rejected"
    assert view(journal)["plan"]["text"] == "An early public hypothesis."
    assert not view(journal)["review_request"]["requested"]


@pytest.mark.parametrize("context", ["append-v1", "segmented-v1"])
def test_actual_input_timing_and_isolated_smoke_preserve_public_authority(tmp_path, context):
    arms = {}
    for policy in (plans.POLICY, POLICY):
        req = request(tmp_path / policy, policy).model_copy(update={"context_policy": context})
        run = runner.run_dev(req)["runs"][0]
        assert run["terminal"] == "EVALUATOR_PASS"
        assert run["evaluator"]["safety_state"] == "NOT_RUN"
        assert run["accepted_mutations"] == 1 and run["cost_nanos"] == 0
        assert run["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
        journal, store = DevJournal(req.state_root, run["run_id"]), ArtifactStore(
            req.state_root / "artifacts")
        events, views = journal.events(), []
        for event in events:
            if event["event_type"] != "turn_started":
                continue
            items = runner._load_active_model_input(event["payload"], store, context_policy=context)
            assert plans.instructions(policy) in items[0]["content"]
            views.append(reconstruct_state(items, context_policy=context))
            if context == "segmented-v1":
                assert verify_turn(event, events, store, actual_input=items)["verified"]
            for private in ("hidden-multiline-csv", "reference_patch", "reasoning_transcript"):
                assert private not in canonical_json(items)
        assert views[0]["working_plan"]["review_request"]["requested"] == (policy == plans.POLICY)
        assert (views[1]["working_plan"]["plan"] is None) == (policy == POLICY)
        if policy == POLICY:
            assert views[1]["working_plan"]["review_request"]["reasons"] == ["initial_plan"]
            assert views[2]["working_plan"]["plan"]["revision"] == 1
        assert "mutation_result" in views[2]["working_plan"]["review_request"]["reasons"]
        assert views[-1]["working_plan"]["plan"]["revision"] == 2
        assert "check_result" in views[-1]["working_plan"]["review_request"]["reasons"]
        assert views[-1]["visible_check_status"][0]["status"] == "PASS"
        arms[policy] = views
    for a, b in zip(arms[plans.POLICY], arms[POLICY], strict=True):
        for key in ("public_task", "current_diff", "visible_check_status", "workflow_gate",
                    "available_tool_names"):
            assert a[key] == b[key]


@pytest.mark.parametrize("boundary", [
    "context_segment_started", "tool_batch_finished", plans.EVENT,
])
def test_first_source_and_plan_receipt_recover_without_extra_calls(tmp_path, monkeypatch, boundary):
    req, inputs, counted, views = configured(monkeypatch, tmp_path, planning=POLICY)

    def selected(payload):
        if boundary == "context_segment_started":
            return payload["reason"] == "initial"
        if boundary == "tool_batch_finished":
            return "mock-read-source" in payload["action_ids"]
        return payload["plan"] is not None

    _crash_journal_once(monkeypatch, event_type=boundary, predicate=selected, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(req)
    resumed = req.model_copy(update={"resume_run_id": _enveloped_run_id(req.state_root)})
    journal, store = records(resumed)
    before, dispatched = journal.path.read_bytes(), copy.deepcopy(inputs)
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"planning_policy": plans.POLICY}))
    assert before == journal.path.read_bytes() and inputs == dispatched
    run = runner.run_dev(resumed)["runs"][0]
    assert_submitted(run)
    assert run["accepted_mutations"] == 1 and len(inputs) == 4 and inputs == counted
    assert not views[0]["working_plan"]["review_request"]["requested"]
    assert views[1]["working_plan"]["review_request"]["reasons"] == ["initial_plan"]
    assert views[2]["working_plan"]["plan"]["revision"] == 1
    events = journal.events()
    receipts = [e["payload"] for e in events if e["event_type"] == plans.EVENT]
    assert len(receipts) == len({r["turn_id"] for r in receipts}) == 4
    assert sum(e["event_type"] == "action_started" and e["payload"]["tool"] == "replace_text"
               for e in events) == 1
    for event in events:
        if event["event_type"] == "turn_started":
            assert verify_turn(event, events, store)["verified"]
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == run
    assert journal.path.read_bytes() == before and len(inputs) == 4
