from __future__ import annotations

import json

import pytest
from native_history_support import input_context
from pydantic import ValidationError
from typer.testing import CliRunner

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.cli import app
from patchloop.dev import working_plan as plans
from patchloop.dev.contracts import (
    DevRunRequest,
    PublicTurnDecision,
    RequestedTool,
    dev_tool_surface_hash,
)
from patchloop.dev.model import DEV_SYSTEM_PROMPT, MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas, validate_tool_batch
from patchloop.errors import ResumeContractMismatch
from patchloop.runtime import repository_root
from patchloop.util import sha256_json


def request(root, policy="brief-v1"):
    return DevRunRequest(
        provider="mock", task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        model="mock-dev", state_root=root, planning_policy=policy,
    )


def call(update=None, *, action="read", tool="read_file"):
    inspect = tool == "read_file"
    return RequestedTool(
        name=tool, action_id=action, arguments={}, turn_decision=PublicTurnDecision(
            mode="inspect" if inspect else "verify", basis="public evidence",
            evidence_goal="public question" if inspect else None, plan_update=update,
        ),
    )


def put(journal, update=None, *, turn="t1", diff="d1", gate="needs_mutation", calls=None):
    return plans.record(journal, calls or [call(update)], turn_id=turn, diff_hash=diff, gate=gate)


def view(journal, diff="d1", gate="needs_mutation"):
    return plans.project(journal.events(), diff_hash=diff, gate=gate)


def test_off_wire_and_prompt_are_unchanged():
    assert dev_tool_surface_hash() == (
        "sha256:a076ac52db8457c004fc689272bdd557e4911e19c98517e4530fbf32a3dc0745"
    )
    assert sha256_json(dev_tool_schemas(finish_enabled=True, check_ids=["check"])) == (
        "sha256:51235786aca769125bf35abcc04af115290258ac4200804b09aebeff442c69c1"
    )
    decision = PublicTurnDecision(mode="verify", basis="baseline")
    assert "plan_update" not in decision.model_dump(mode="json")
    restored = PublicTurnDecision.model_validate(decision.model_dump(mode="json"))
    assert restored.model_dump() == decision.model_dump()
    assert "Brief planning is enabled" not in DEV_SYSTEM_PROMPT
    explicit = decision.model_copy(update={"plan_update": None})
    assert "plan_update" in explicit.model_dump(mode="json")


def test_enabled_schema_only_adds_annotation():
    before = dev_tool_schemas(finish_enabled=True, check_ids=["c"])
    after = dev_tool_schemas(finish_enabled=True, check_ids=["c"], planning_policy=plans.POLICY)
    for tool in after:
        decision = tool["parameters"]["properties"]["turn_decision"]
        assert decision["properties"].pop("plan_update") == plans.update_schema()
        assert decision["required"].pop() == "plan_update"
    assert after == before
    assert dev_tool_surface_hash(planning_policy=plans.POLICY) != dev_tool_surface_hash()


def test_plan_guidance_connects_public_results_to_remaining_work():
    assert "current hypotheses or untested assumptions" in plans.INSTRUCTIONS
    assert "observation or public check that could settle them" in plans.INSTRUCTIONS
    assert "confirmed, contradicted, or left unresolved" in plans.INSTRUCTIONS
    assert "remaining work and verification" in plans.INSTRUCTIONS
    assert "Do not invent a change" in plans.INSTRUCTIONS
    assert "null keeps it when there is no useful revision" in plans.INSTRUCTIONS
    assert "not a generic inspect/edit/check outline" in plans.INSTRUCTIONS
    # Guidance is task-independent; it must not import repairs from diagnostic runs.
    for hint in ("pyfakefs", "loguru", "hf-hub", "parent-traversal", "0o700"):
        assert hint not in plans.INSTRUCTIONS


def test_content_guidance_changes_on_identity_not_schema_or_off(tmp_path, monkeypatch):
    requests = {policy: request(tmp_path, policy) for policy in ("none", plans.POLICY)}
    before = {
        policy: (runner._model_hash(req, None), dev_tool_surface_hash(planning_policy=policy))
        for policy, req in requests.items()
    }
    schemas = {
        policy: dev_tool_schemas(finish_enabled=True, check_ids=["c"], planning_policy=policy)
        for policy in requests
    }
    instructions_hash = plans.contract()["instructions_hash"]
    monkeypatch.setattr(plans, "INSTRUCTIONS", plans.INSTRUCTIONS + "\nPublic guidance revision.")
    assert plans.contract()["instructions_hash"] != instructions_hash
    for policy, req in requests.items():
        after = (runner._model_hash(req, None), dev_tool_surface_hash(planning_policy=policy))
        assert (after == before[policy]) == (policy == "none")
        assert schemas[policy] == dev_tool_schemas(
            finish_enabled=True, check_ids=["c"], planning_policy=policy,
        )


def test_option_and_cli(tmp_path, monkeypatch):
    off, on = request(tmp_path, "none"), request(tmp_path)
    assert runner._model_hash(off, None) != runner._model_hash(on, None)
    with pytest.raises(ValidationError, match="append-v1"):
        DevRunRequest.model_validate({**on.model_dump(), "context_policy": "native-window-v1"})
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda req: captured.append(req) or {})
    result = CliRunner().invoke(app, ["dev", "--provider", "mock", "--task", str(on.task),
                                    "--model", "mock-dev", "--planning-policy", "brief-v1"])
    assert result.exit_code == 0, result.output
    assert captured[0].planning_policy == plans.POLICY


@pytest.mark.parametrize("update", [None, "", "  \n", "x" * 3001, {}, 1, True, []])
def test_invalid_or_null_plan_never_rejects_action(tmp_path, update):
    journal = DevJournal(tmp_path, "run_dev_plans")
    put(journal, "Original public plan")
    selected = call(update)
    assert validate_tool_batch([selected]) == "parallel_read"
    receipt = put(journal, turn="t2", calls=[selected])
    assert receipt["status"] == ("not_requested" if update is None else "rejected")
    assert view(journal)["plan"]["text"] == "Original public plan"
    assert view(journal)["plan"]["revision"] == 1


def test_whole_plan_revision_parallel_and_replay(tmp_path):
    journal = DevJournal(tmp_path, "run_dev_plans")
    assert view(journal)["review_request"]["reasons"] == ["initial_plan"]
    receipt = put(journal, calls=[call(None, action="a"), call("first", action="b"),
                                 call("ignored", action="c")])
    assert receipt["action_id"] == "b"
    assert receipt["diagnostics"] == ["ignored_additional_plan_updates"]
    before = journal.path.read_bytes()
    assert put(journal, "different after restart") == receipt
    assert journal.path.read_bytes() == before
    assert put(journal, "first", turn="t2")["status"] == "unchanged"
    assert put(journal, "revised", turn="t3")["revision"] == 2
    assert view(DevJournal(tmp_path, "run_dev_plans")) == view(journal)
    assert view(journal, "d2")["plan"]["diff_currency"] == "historical"
    assert view(journal, "d1")["plan"]["diff_currency"] == "current"


@pytest.mark.parametrize("tool,reason", [("read_file", None), ("search_files", None),
    ("replace_text", "mutation_result"), ("run_check", "check_result"),
    ("run_probe", "probe_result")])
@pytest.mark.parametrize("status", ["succeeded", "failed"])
def test_review_triggers_and_valid_decision_consumption(tmp_path, tool, reason, status):
    journal = DevJournal(tmp_path, "run_dev_plans")
    put(journal, "Plan")
    journal.append("action_finished", {"result": {
        "tool": tool, "status": status, "action_id": "a", "output": {},
    }})
    expected = [reason] if reason else []
    assert view(journal)["review_request"]["reasons"] == expected
    journal.append("turn_started", {"turn_id": "unconsumed"})
    assert view(journal)["review_request"]["reasons"] == expected
    put(journal, turn="t2")
    assert not view(journal)["review_request"]["requested"]
    ready = view(journal, gate="ready_to_submit")
    assert ready["review_request"]["reasons"] == ["first_ready_to_submit"]
    put(journal, turn="t3", gate="ready_to_submit")
    assert not view(journal, gate="ready_to_submit")["review_request"]["requested"]


class Crash(BaseException):
    pass


@pytest.mark.parametrize("boundary", ["turn_decision_recorded", plans.EVENT, "tool_batch_finished"])
def test_plan_crash_resume_no_duplicate_action_or_model(tmp_path, monkeypatch, boundary):
    original = DevJournal.append
    crashed = False

    def append(self, event, payload=None):
        nonlocal crashed
        # Crash on the mutation turn, including after its action but before batch completion.
        mutation = any(e["event_type"] == "turn_decision_recorded" and any(
            c["name"] == "replace_text" for c in e["payload"].get("tool_calls", [])
        ) for e in self.events())
        if event == "tool_batch_finished" and mutation and boundary == event and not crashed:
            crashed = True
            raise Crash()
        result = original(self, event, payload)
        mutation = mutation or (event == "turn_decision_recorded" and any(
            c["name"] == "replace_text" for c in (payload or {}).get("tool_calls", [])))
        if mutation and event == boundary and not crashed:
            crashed = True
            raise Crash()
        return result

    monkeypatch.setattr(DevJournal, "append", append)
    req = request(tmp_path)
    with pytest.raises(Crash):
        runner.run_dev(req)
    run_id = next((tmp_path / "runs").glob("*.jsonl")).stem
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(req.model_copy(update={"resume_run_id": run_id, "planning_policy": "none"}))
    result = runner.run_dev(req.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["accepted_mutations"] == 1
    assert result["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    journal = DevJournal(tmp_path, run_id)
    events = journal.events()
    updates = [e for e in events if e["event_type"] == plans.EVENT]
    assert len(updates) == len({e["payload"]["turn_id"] for e in updates}) == 4
    assert sum(e["event_type"] == "action_started" and e["payload"]["tool"] == "replace_text"
               for e in events) == 1
    before = journal.path.read_bytes()
    assert runner.run_dev(req.model_copy(update={"resume_run_id": run_id}))["runs"][0] == result
    assert journal.path.read_bytes() == before


@pytest.mark.parametrize("policy", ["none", "brief-v1"])
def test_native_plan_delivery_and_mock_end_to_end(tmp_path, policy):
    result = runner.run_dev(request(tmp_path, policy))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["cost_nanos"] == 0
    assert result["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    events = DevJournal(tmp_path, result["run_id"]).events()
    store = ArtifactStore(tmp_path / "artifacts")
    previous = None
    plans_seen = []
    for event in events:
        if event["event_type"] != "turn_started":
            continue
        items = runner._load_active_model_input(event["payload"], store)
        context = input_context(items)
        assert "hidden-multiline-csv" not in json.dumps(context)
        assert "reference_patch" not in json.dumps(context)
        assert ("working_plan" in context) == (policy != "none")
        assert (plans.INSTRUCTIONS in items[0]["content"]) == (policy != "none")
        if policy != "none":
            plans_seen.append(context["working_plan"]["plan"])
        if previous:
            assert items[:len(previous)] == previous
        previous = items
        # The public plan has no private task input even though evaluation runs later.
        assert "reference_patch" not in json.dumps(context.get("working_plan"))
    if policy != "none":
        assert plans_seen[0] is None
        assert all(p is not None for p in plans_seen[1:])
        outputs = [json.loads(i["output"]) for i in previous
                   if i.get("type") == "function_call_output"]
        assert sum("plan_update_result" in r for r in outputs) == 3
    else:
        assert not any(e["event_type"] == plans.EVENT for e in events)


def test_bad_annotation_does_not_add_model_correction(tmp_path, monkeypatch):
    original = MockDevAdapter.next_turn

    def bad(self, context, tools):
        turn = original(self, context, tools)
        turn.tool_calls[0].turn_decision.plan_update = {"wrong": True}
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", bad)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["call_counts"]["model"] == 4
    events = DevJournal(tmp_path, result["run_id"]).events()
    assert not any(e["event_type"] == "protocol_correction" for e in events)
    assert all(e["payload"]["receipt"]["status"] == "rejected"
               for e in events if e["event_type"] == plans.EVENT)


def test_evaluator_rejects_planning_identity_mismatch_before_workspace(tmp_path, monkeypatch):
    from patchloop.repository import WorkspaceManager

    original = runner._manifest
    create = WorkspaceManager.create
    evaluator_workspaces = []

    def wrong(**kwargs):
        manifest = original(**kwargs)
        manifest.tool_surface_hash = dev_tool_surface_hash()
        return manifest

    def guarded(self, name, *args, **kwargs):
        if name.startswith("eval_"):
            evaluator_workspaces.append(name)
        return create(self, name, *args, **kwargs)

    monkeypatch.setattr(runner, "_manifest", wrong)
    monkeypatch.setattr(WorkspaceManager, "create", guarded)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert result["terminal"] == "EVALUATOR_ERROR"
    assert result["artifact_hashes"]["submitted_patch"]
    assert not evaluator_workspaces
