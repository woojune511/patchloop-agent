"""Plan-content contrast: transport/identity evidence, not model-quality evidence."""
from __future__ import annotations

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

POLICY = plans.EVIDENCE_POLICY
HEADINGS = ("Behavior:", "Evidence / open assumptions:", "Next discriminating action:")
INITIAL = (
    "Behavior: preserve public record boundaries.\n"
    "Evidence / open assumptions: a source observation is not execution evidence; "
    "UNTESTED_PUBLIC_REQUIREMENT remains open.\n"
    "Next discriminating action: read the public parser to locate its record iterator."
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("planning-content tests must not send real provider requests")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def project(journal, diff="d1", gate="needs_mutation"):
    return plans.project(journal.events(), diff_hash=diff, gate=gate, policy=POLICY)


def record(journal, text, *, turn="t1", calls=None, diff="d1", gate="needs_mutation"):
    return plans.record(journal, calls or [call(text)], turn_id=turn, diff_hash=diff,
                        gate=gate, policy=POLICY)


def test_old_contract_and_schema_unchanged_new_guidance_is_task_independent(tmp_path, monkeypatch):
    assert plans.instructions() == plans.INSTRUCTIONS
    assert dev_tool_surface_hash(planning_policy=plans.POLICY) == (
        "sha256:e9a1a5de627227db9bcd3ee26d3ff7f55391f21c8775f814a81dcc282fc0bf65"
    )
    old, new = plans.contract(), plans.contract(POLICY)
    assert {k: v for k, v in old.items() if k not in {"policy", "instructions_hash"}} == {
        k: v for k, v in new.items() if k not in {"policy", "instructions_hash"}
    }
    instructions = plans.instructions(POLICY)
    assert instructions == plans.INSTRUCTIONS + "\n\n" + plans.EVIDENCE_FORMAT
    assert all(h in instructions for h in HEADINGS)
    for private_or_hint in ("hidden", "reference_patch", "pyfakefs", "makedirs",
                            "staging", "0o700", "0o755", "loguru", "hf-hub"):
        assert private_or_hint not in instructions
    options = {"finish_enabled": True, "check_ids": ["check"]}
    assert dev_tool_schemas(**options, planning_policy=POLICY) == dev_tool_schemas(
        **options, planning_policy=plans.POLICY,
    )
    policies = ("none", plans.POLICY, POLICY)
    before = {p: (runner._model_hash(request(tmp_path, p), None),
                  dev_tool_surface_hash(planning_policy=p)) for p in policies}
    assert len(set(before.values())) == 3
    monkeypatch.setattr(plans, "EVIDENCE_FORMAT", plans.EVIDENCE_FORMAT + "\nFormat revision.")
    for policy in policies:
        after = (runner._model_hash(request(tmp_path, policy), None),
                 dev_tool_surface_hash(planning_policy=policy))
        assert (before[policy] == after) == (policy != POLICY)


@pytest.mark.parametrize("context", ["append-v1", "segmented-v1"])
def test_cli_and_request_identity(tmp_path, monkeypatch, context):
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
    assert DevRunRequest.model_validate({**base.model_dump(),
                                        "context_policy": context}).planning_policy == POLICY
    with pytest.raises(ValidationError, match="requires append-v1 or segmented-v1"):
        DevRunRequest.model_validate({**base.model_dump(), "context_policy": "native-window-v1"})


@pytest.mark.parametrize("update", [None, "", " \n", "x" * 3001, {}, 1, True, []])
def test_invalid_or_null_update_preserves_unresolved_text_and_action(tmp_path, update):
    journal = DevJournal(tmp_path, "run_dev_plans")
    record(journal, INITIAL)
    selected = call(update)
    assert validate_tool_batch([selected]) == "parallel_read"
    receipt = record(journal, update, turn="t2", calls=[selected])
    assert receipt["status"] == ("not_requested" if update is None else "rejected")
    view = project(journal)
    assert view["policy"] == POLICY
    assert view["interpretation_status"] == "model_authored_unverified"
    assert view["plan"]["text"] == INITIAL
    assert view["plan"]["revision"] == 1


def test_whole_replacement_parallel_replay_and_nonconforming_text(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_plans")
    receipt = record(journal, None, calls=[call(None, action="a"), call(INITIAL, action="b"),
                                         call("ignored", action="c")])
    assert receipt["action_id"] == "b"
    assert receipt["diagnostics"] == ["ignored_additional_plan_updates"]
    before = journal.path.read_bytes()
    assert record(journal, "different after restart") == receipt
    assert journal.path.read_bytes() == before
    assert record(journal, INITIAL, turn="t2")["status"] == "unchanged"
    # Headings are guidance, not a schema, content validator, or action gate.
    assert record(journal, "A valid short plan without headings", turn="t3")["revision"] == 2
    assert project(journal)["plan"]["text"] == "A valid short plan without headings"
    assert project(DevJournal(tmp_path, journal.run_id)) == project(journal)


@pytest.mark.parametrize("event,reason", [
    ("replace_text", "mutation_result"), ("run_check", "check_result"),
    ("run_probe", "probe_result"), ("context_segment_started", "context_handoff"),
])
def test_result_review_does_not_erase_authored_open_question(tmp_path, event, reason):
    journal = DevJournal(tmp_path, "run_dev_plans")
    record(journal, INITIAL)
    if event == "context_segment_started":
        journal.append(event, {})
    else:
        journal.append("action_finished", {"result": {
            "tool": event, "status": "succeeded", "action_id": "result", "output": {},
        }})
    journal.append("turn_started", {"turn_id": "unconsumed"})
    view = project(journal, diff="d2", gate="ready_to_submit")
    assert view["review_request"]["reasons"] == [reason, "first_ready_to_submit"]
    assert view["plan"]["text"] == INITIAL
    assert view["plan"]["diff_currency"] == "historical"
    record(journal, None, turn="t2", diff="d2", gate="ready_to_submit")
    view = project(DevJournal(tmp_path, journal.run_id), diff="d2", gate="ready_to_submit")
    assert not view["review_request"]["requested"]
    assert view["plan"]["text"] == INITIAL
    assert view["plan"]["diff_currency"] == "historical"
    # This proves preservation of authored text, not that a real model retains an assumption.


@pytest.mark.parametrize("boundary", ["turn_decision_recorded", plans.EVENT, "tool_batch_finished"])
def test_segmented_crash_exact_resume_and_actual_plan_delivery(tmp_path, monkeypatch, boundary):
    req, inputs, counted, views = configured(monkeypatch, tmp_path, planning=POLICY)

    def mutation_turn(payload):
        if boundary == "turn_decision_recorded":
            return any(c["name"] == "replace_text" for c in payload["tool_calls"])
        if boundary == plans.EVENT:
            return payload["receipt"]["action_id"] == "mock-apply-mutation"
        return payload["action_ids"] == ["mock-apply-mutation"]

    _crash_journal_once(monkeypatch, event_type=boundary, predicate=mutation_turn, when="after")
    with pytest.raises(_SimulatedCrash):
        runner.run_dev(req)
    resumed = req.model_copy(update={"resume_run_id": _enveloped_run_id(req.state_root)})
    journal, _ = records(resumed)
    before, dispatched = journal.path.read_bytes(), len(inputs)
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"planning_policy": plans.POLICY}))
    assert journal.path.read_bytes() == before and len(inputs) == dispatched
    result = runner.run_dev(resumed)["runs"][0]
    assert_submitted(result)  # Synthetic Docker identity must still fail isolated verification.
    assert result["accepted_mutations"] == 1
    assert len(inputs) == len(counted) == 4
    assert counted == inputs
    events = journal.events()
    receipts = [e for e in events if e["event_type"] == plans.EVENT]
    assert len(receipts) == len({e["payload"]["turn_id"] for e in receipts}) == 4
    assert sum(e["event_type"] == "action_started" and e["payload"]["tool"] == "replace_text"
               for e in events) == 1
    turns = [e for e in events if e["event_type"] == "turn_started"]
    for items, view, turn in zip(inputs, views, turns, strict=True):
        assert plans.instructions(POLICY) in items[0]["content"]
        assert view["working_plan"]["policy"] == POLICY
        preceding = [e for e in receipts if e["sequence"] < turn["sequence"]]
        if preceding:
            plan = view["working_plan"]["plan"]
            assert plan["text"] == preceding[-1]["payload"]["plan"]["text"]
            assert plan["text_hash"] == sha256_json(plan["text"])
            assert all(h in plan["text"] for h in HEADINGS)
        for private in ("hidden-multiline-csv", "reference_patch", "reasoning_transcript"):
            assert private not in canonical_json(view)
    assert "context_handoff" in views[-1]["working_plan"]["review_request"]["reasons"]
    before = journal.path.read_bytes()
    assert runner.run_dev(resumed)["runs"][0] == result
    assert journal.path.read_bytes() == before
    assert len(inputs) == 4


@pytest.mark.parametrize("annotation", [{"wrong": True}, "Missing headings are not a tool error."])
def test_plan_errors_and_format_do_not_block_real_mock_actions(tmp_path, monkeypatch, annotation):
    original = MockDevAdapter.next_turn

    def annotated(self, context, tools):
        turn = original(self, context, tools)
        turn.tool_calls[0].turn_decision.plan_update = annotation
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", annotated)
    result = runner.run_dev(request(tmp_path, POLICY))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    events = DevJournal(tmp_path, result["run_id"]).events()
    assert not any(e["event_type"] == "protocol_correction" for e in events)
    updates = [e["payload"] for e in events if e["event_type"] == plans.EVENT]
    if isinstance(annotation, str):
        assert all(e["plan"]["text"] == annotation for e in updates)
    else:
        assert all(e["receipt"]["status"] == "rejected" for e in updates)


def test_manifest_rejects_old_policy_hash_before_evaluator_workspace(tmp_path, monkeypatch):
    original, create = runner._manifest, WorkspaceManager.create
    evaluator_workspaces = []

    def wrong(**kwargs):
        manifest = original(**kwargs)
        assert manifest.planning_policy == POLICY
        manifest.tool_surface_hash = dev_tool_surface_hash(planning_policy=plans.POLICY)
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
    assert '"official": true' not in json.dumps(result)
