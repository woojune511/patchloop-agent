"""Edit-assumption content contrast: transport contracts, not model-quality evidence."""
from __future__ import annotations

import copy
import json

import httpx
import pytest
from pydantic import ValidationError
from test_dev_planning import call, request
from test_dev_runner import _crash_journal_once, _enveloped_run_id, _SimulatedCrash
from test_dev_segments import assert_submitted, configured, records
from typer.testing import CliRunner

from patchloop.cli import app
from patchloop.dev import runner
from patchloop.dev import working_plan as plans
from patchloop.dev.contracts import DevRunRequest, dev_tool_surface_hash
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.errors import ResumeContractMismatch
from patchloop.repository import WorkspaceManager
from patchloop.util import canonical_json, sha256_json

POLICY = plans.ASSUMPTION_POLICY
INITIAL = "Behavior: preserve public record boundaries.\nEvidence / open assumptions: untested."
POST_EDIT = (
    "Behavior: preserve public record boundaries.\n"
    "Evidence / open assumptions: UNTESTED_PUBLIC_ASSUMPTION: the stream iterator "
    "preserves an empty field. Input/setup: a record with adjacent delimiters. "
    "Observation: the result retains an empty field, not a missing column.\n"
    "Next discriminating action: inspect what the available public check exercises."
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("assumption-planning tests must not dispatch real provider requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def test_instruction_only_contrast_preserves_old_identities_and_schemas(tmp_path, monkeypatch):
    old_hashes = {
        "none": "sha256:391175f5c53df0f2bf809567956fcc625117f21bb3d5e522105de2ad53932c4b",
        plans.POLICY: "sha256:7569bdf3ed73010cb4250000637e0346d5502ef29bce0f15d8769120ce734d56",
        plans.EVIDENCE_POLICY:
            "sha256:693d6aea237a7cd8f0fd7de70f139e0baa6dfe859eb1b78f05484e20a88a2af5",
    }
    assert {p: dev_tool_surface_hash(planning_policy=p) for p in old_hashes} == old_hashes
    old = plans.instructions(plans.EVIDENCE_POLICY)
    assert plans.instructions(POLICY) == old + "\n\n" + plans.EDIT_ASSUMPTION_GUIDANCE
    assert "concrete public input/setup" in plans.EDIT_ASSUMPTION_GUIDANCE
    assert "current rollback baseline" in plans.EDIT_ASSUMPTION_GUIDANCE
    assert "null remains allowed" in plans.EDIT_ASSUMPTION_GUIDANCE
    for hint in ("hidden", "reference_patch", "pyfakefs", "makedirs", "0o700", "loguru",
                 "hf-hub", "run_dev_", "../", "exist_ok", "UNTESTED_PUBLIC_ASSUMPTION"):
        assert hint not in plans.instructions(POLICY)
    old_contract, new_contract = plans.contract(plans.EVIDENCE_POLICY), plans.contract(POLICY)
    for field in ("policy", "instructions_hash"):
        assert old_contract.pop(field) != new_contract.pop(field)
    assert old_contract == new_contract
    # Ordered input schemas (including probes) do not change with this content contrast.
    for probe in ("none", "cases-v1"):
        options = dict(finish_enabled=True, check_ids=["c"], probe_policy=probe,
                       allowed_tools=["read_file", "search_files", "replace_text", "run_probe",
                                      "run_check", "finish_task", "stop_task"])
        assert dev_tool_schemas(**options, planning_policy=POLICY) == dev_tool_schemas(
            **options, planning_policy=plans.EVIDENCE_POLICY,
        )
    policies = (*old_hashes, POLICY)
    before = {p: (runner._model_hash(request(tmp_path, p), None),
                  dev_tool_surface_hash(planning_policy=p)) for p in policies}
    assert len(set(before.values())) == 4
    monkeypatch.setattr(plans, "EDIT_ASSUMPTION_GUIDANCE", plans.EDIT_ASSUMPTION_GUIDANCE + ".")
    for p in policies:
        after = (runner._model_hash(request(tmp_path, p), None),
                 dev_tool_surface_hash(planning_policy=p))
        assert (before[p] == after) == (p != POLICY)


@pytest.mark.parametrize("context", ["append-v1", "segmented-v1"])
def test_cli_and_context_options(tmp_path, monkeypatch, context):
    base = request(tmp_path, POLICY)
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda req: captured.append(req) or {})
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(base.task), "--model", "mock-dev",
        "--planning-policy", POLICY, "--context-policy", context,
    ])
    assert result.exit_code == 0, result.output
    assert captured[0].planning_policy == POLICY
    assert captured[0].context_policy == context
    assert DevRunRequest.model_validate({**base.model_dump(), "context_policy": context})
    with pytest.raises(ValidationError, match="requires append-v1 or segmented-v1"):
        DevRunRequest.model_validate({**base.model_dump(), "context_policy": "native-window-v1"})


@pytest.mark.parametrize("update", [None, "", " \n", {}, True, "x" * 3001])
@pytest.mark.parametrize("mutation_status", ["succeeded", "failed"])
def test_rejected_or_null_update_keeps_action_and_historical_plan(
    tmp_path, update, mutation_status,
):
    journal = DevJournal(tmp_path, "run_dev_plan")
    plans.record(journal, [call(INITIAL)], turn_id="t1", diff_hash="d1",
                 gate="needs_mutation", policy=POLICY)
    journal.append("action_finished", {"result": {
        "tool": "replace_text", "status": mutation_status, "action_id": "edit", "output": {},
    }})
    before = plans.project(journal.events(), diff_hash="d2", gate="needs_visible_checks",
                           policy=POLICY)
    assert before["review_request"]["reasons"] == ["mutation_result"]
    assert before["plan"]["diff_currency"] == "historical"
    selected = call(update)
    assert validate_tool_batch([selected]) == "parallel_read"
    receipt = plans.record(journal, [selected], turn_id="t2", diff_hash="d2",
                           gate="needs_visible_checks", policy=POLICY)
    assert receipt["status"] == ("not_requested" if update is None else "rejected")
    after = plans.project(DevJournal(tmp_path, journal.run_id).events(), diff_hash="d2",
                          gate="needs_visible_checks", policy=POLICY)
    assert after["plan"] == before["plan"]
    assert after["interpretation_status"] == "model_authored_unverified"
    assert not after["review_request"]["requested"]


def test_parallel_whole_text_and_exact_replay_without_semantic_validator(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_plan")
    options = dict(turn_id="t1", diff_hash="d1", gate="needs_mutation", policy=POLICY)
    receipt = plans.record(journal, [call(None, action="a"), call(POST_EDIT, action="b"),
                                    call("ignored", action="c")], **options)
    assert receipt["action_id"] == "b"
    assert receipt["diagnostics"] == ["ignored_additional_plan_updates"]
    before = journal.path.read_bytes()
    assert plans.record(journal, [call("different")], **options) == receipt
    assert journal.path.read_bytes() == before
    assert plans.record(journal, [call(POST_EDIT)], **{**options, "turn_id": "t2"})[
        "status"] == "unchanged"
    # No input/outcome/headings quota, semantic approval or forced revision.
    for turn, text in [("t3", "No useful revision of the assumption."), ("t4", "x" * 3000)]:
        receipt = plans.record(journal, [call(text)], **{**options, "turn_id": turn})
        assert receipt["status"] == "updated"
        assert plans.project(journal.events(), diff_hash="d1", gate="needs_mutation",
                             policy=POLICY)["plan"]["text"] == text


@pytest.mark.parametrize("boundary", ["turn_decision_recorded", plans.EVENT, "tool_batch_finished"])
def test_post_edit_plan_delivery_exact_resume_and_no_new_gate(tmp_path, monkeypatch, boundary):
    # Authored fixture data is deliberately not scored as real planning quality.
    original = MockDevAdapter.next_turn

    def authored(self, context, tools):
        turn = original(self, context, tools)
        view = json.loads(context)["working_plan"]
        update = INITIAL if view["plan"] is None else None
        if "mutation_result" in view["review_request"]["reasons"]:
            update = POST_EDIT
        turn.tool_calls[0].turn_decision.plan_update = update
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", authored)
    req, inputs, counted, views = configured(monkeypatch, tmp_path, planning=POLICY)

    def after_edit_review(payload):
        if boundary == plans.EVENT:
            return payload["plan"] is not None and payload["plan"]["text"] == POST_EDIT
        if boundary == "turn_decision_recorded":
            return any(c["name"] == "run_check" for c in payload["tool_calls"])
        return any(a.startswith("mock-visible-check-") for a in payload["action_ids"])

    _crash_journal_once(monkeypatch, event_type=boundary, predicate=after_edit_review, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(req)
    resumed = req.model_copy(update={"resume_run_id": _enveloped_run_id(req.state_root)})
    journal, _ = records(resumed)
    before, dispatched = journal.path.read_bytes(), copy.deepcopy(inputs)
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"planning_policy": plans.EVIDENCE_POLICY}))
    assert journal.path.read_bytes() == before and inputs == dispatched
    result = runner.run_dev(resumed)["runs"][0]
    assert_submitted(result)  # Synthetic image is not promoted to successful private evaluation.
    assert result["accepted_mutations"] == 1
    assert inputs == counted and len(inputs) == 4
    assert views[2]["working_plan"]["review_request"]["reasons"] == ["mutation_result"]
    final = views[-1]["working_plan"]
    assert final["plan"]["text"] == POST_EDIT
    assert final["plan"]["revision"] == 2
    assert final["plan"]["text_hash"] == sha256_json(POST_EDIT)
    assert final["interpretation_status"] == "model_authored_unverified"
    assert "context_handoff" in final["review_request"]["reasons"]
    assert "check_result" in final["review_request"]["reasons"]
    assert views[-1]["workflow_gate"] == "ready_to_submit"  # An open assumption is not a gate.
    for items in inputs:
        assert plans.instructions(POLICY) in items[0]["content"]
        for sentinel in ("hidden-multiline-csv", "reference_patch", "reasoning_transcript"):
            assert sentinel not in canonical_json(items)
    receipts = [e for e in journal.events() if e["event_type"] == plans.EVENT]
    assert len(receipts) == len({e["payload"]["turn_id"] for e in receipts}) == 4
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before and len(inputs) == 4


def test_manifest_mismatch_rejected_before_evaluator_workspace(tmp_path, monkeypatch):
    original, create = runner._manifest, WorkspaceManager.create
    evaluator_workspaces = []

    def wrong(**kwargs):
        manifest = original(**kwargs)
        assert manifest.planning_policy == POLICY
        manifest.tool_surface_hash = dev_tool_surface_hash(planning_policy=plans.EVIDENCE_POLICY)
        return manifest

    def guarded(self, name, *args, **kwargs):
        if name.startswith("eval_"):
            evaluator_workspaces.append(name)
        return create(self, name, *args, **kwargs)

    monkeypatch.setattr(runner, "_manifest", wrong)
    monkeypatch.setattr(WorkspaceManager, "create", guarded)
    result = runner.run_dev(request(tmp_path, POLICY))["runs"][0]
    assert result["terminal"] == "EVALUATOR_ERROR"
    assert result["artifact_hashes"]["submitted_patch"]
    assert not evaluator_workspaces
