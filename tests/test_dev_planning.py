from __future__ import annotations

import json

import pytest
from native_history_support import input_context
from pydantic import ValidationError
from repair_mechanism_expectations import FROZEN_ARM
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


def call(update=None, *, action="read", tool="read_file",
         reason="Refine the next action; unfinished verification remains in scope."):
    inspect = tool == "read_file"
    return RequestedTool(
        name=tool, action_id=action, arguments={}, turn_decision=PublicTurnDecision(
            mode="inspect" if inspect else "verify", basis="public evidence",
            evidence_goal="public question" if inspect else None, plan_update=update,
            plan_update_reason=reason,
        ),
    )


def put(journal, update=None, *, turn="t1", diff="d1", gate="needs_mutation", calls=None):
    return plans.record(journal, calls or [call(update)], turn_id=turn, diff_hash=diff, gate=gate)


def view(journal, diff="d1", gate="needs_mutation"):
    return plans.project(journal.events(), diff_hash=diff, gate=gate)


def test_off_wire_and_prompt_are_unchanged():
    assert dev_tool_surface_hash() == (
        "sha256:0ef66556483325c857181c7890c086a2d96822939f1cdc9db14a04222dbded7e"
        if FROZEN_ARM is None else
        "sha256:57193859890419b79cb7f4927c37796d044bc4bf7159c51ddf17723849529e26"
    )
    assert sha256_json(dev_tool_schemas(finish_enabled=True, check_ids=["check"])) == (
        "sha256:8d20edab1779773045db4e3a0459424a07cb734ea8bfaf23f020cb7c0a714090"
        if FROZEN_ARM is None else
        "sha256:e8ac4db103389896d6df2061340f328e1c400ee83cb439a4c4f1ed4529f50036"
    )
    decision = PublicTurnDecision(mode="verify", basis="baseline")
    assert "plan_update" not in decision.model_dump(mode="json")
    assert "plan_update_reason" not in decision.model_dump(mode="json")
    assert "scope_review" not in decision.model_dump(mode="json")
    restored = PublicTurnDecision.model_validate(decision.model_dump(mode="json"))
    assert restored.model_dump() == decision.model_dump()
    assert "Brief planning is enabled" not in DEV_SYSTEM_PROMPT
    explicit = decision.model_copy(update={"plan_update": None})
    assert "plan_update" in explicit.model_dump(mode="json")
    explicit_review = decision.model_copy(update={"scope_review": None})
    assert explicit_review.model_dump(mode="json")["scope_review"] is None


def test_enabled_schema_only_adds_annotation():
    from patchloop.dev.scope_review import schema as scope_review_schema

    before = dev_tool_schemas(finish_enabled=True, check_ids=["c"])
    after = dev_tool_schemas(finish_enabled=True, check_ids=["c"], planning_policy=plans.POLICY)
    for tool in after:
        properties = tool["parameters"]["properties"]
        if FROZEN_ARM is None and "turn_decision" not in properties:
            assert "plan_update" not in properties and "plan_update_reason" not in properties
            continue
        decision = properties["turn_decision"]
        assert decision["properties"].pop("plan_update") == plans.update_schema()
        assert decision["properties"].pop("plan_update_reason") == plans.reason_schema()
        assert decision["properties"].pop("scope_review") == scope_review_schema()
        assert decision["required"].pop() == "scope_review"
        assert decision["required"].pop() == "plan_update_reason"
        assert decision["required"].pop() == "plan_update"
    assert after == before
    assert dev_tool_surface_hash(planning_policy=plans.POLICY) != dev_tool_surface_hash()


def test_plan_guidance_connects_public_results_to_remaining_work():
    guidance = " ".join(plans.INSTRUCTIONS.split())
    assert "current hypotheses or untested assumptions" in guidance
    assert "observation or public check that could settle them" in guidance
    if FROZEN_ARM is None:
        assert "compare known public conditions with actual/planned case conditions" in guidance
        assert ("do not narrow the public objective to an inherited plan's finish criterion"
                in guidance)
        assert "Explain substitutions/gaps in interpretation" in guidance
        assert "Observe the named property, retain material gaps" in guidance
    else:
        assert "Use scope_review for a bounded affected-scope -> case/setup" in guidance
        assert "check must observe its named property" in guidance
        assert "support, contradict or leave open" in guidance
        assert "Retain material gaps" in guidance
    assert "current-diff execution IDs" in guidance
    assert "review_request.behavior_change" in guidance
    assert "before carrying forward a check-then-submit plan" in guidance
    assert "Listing unknowns alone does not justify stopping" in guidance
    assert "patch/submission decision over repeating supported examples" in guidance
    assert "null keeps it when there is no useful revision" in guidance
    assert "not a generic inspect/edit/check outline" in guidance
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


@pytest.mark.parametrize("policy", ["none", "brief-v1", "brief-evidence-v1", "brief-assumption-v1"])
def test_native_plan_delivery_and_mock_end_to_end(tmp_path, policy):
    result = runner.run_dev(request(tmp_path, policy))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["cost_nanos"] == 0
    assert result["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    events = DevJournal(tmp_path, result["run_id"]).events()
    store = ArtifactStore(tmp_path / "artifacts")
    previous = None
    plans_seen = []
    receipts_seen = []
    repair_turns = 0
    for event in events:
        if event["event_type"] != "turn_started":
            continue
        items = runner._load_active_model_input(event["payload"], store)
        context = input_context(items)
        assert "hidden-multiline-csv" not in json.dumps(context)
        assert "reference_patch" not in json.dumps(context)
        repairing = (FROZEN_ARM is None and context.get("repair_stage", {}).get("policy")
                     == "small-repair-context-v1")
        repair_turns += repairing
        assert ("working_plan" in context) == (policy != "none")
        assert (plans.INSTRUCTIONS in items[0]["content"]) == (policy != "none")
        if policy != "none":
            assert context["working_plan"]["policy"] == policy
            plans_seen.append(context["working_plan"]["plan"])
            receipts_seen.append(context["working_plan"]["last_update_result"])
        if previous:
            assert items[:len(previous)] == previous
        previous = items
        # The public plan has no private task input even though evaluation runs later.
        assert "reference_patch" not in json.dumps(context.get("working_plan"))
    if policy != "none":
        assert len(plans_seen) == 4
        assert plans_seen[0] is None
        assert all(p is not None for p in plans_seen[1:])
        outputs = [json.loads(i["output"]) for i in previous
                   if i.get("type") == "function_call_output"]
        assert not any("plan_update_result" in r for r in outputs)
        durable = [event["payload"]["receipt"] for event in events
                   if event["event_type"] == plans.EVENT]
        assert len(durable) == 4
        if FROZEN_ARM is None:
            # Compact repair retains the plan; the edit still has no annotation.
            assert durable[1]["status"] == "not_requested"
            assert durable[1]["revision"] == durable[0]["revision"]
        assert receipts_seen == [None, *durable[:3]]
    else:
        assert not any(e["event_type"] == plans.EVENT for e in events)
    assert repair_turns == (1 if FROZEN_ARM is None else 0)


def test_bad_annotation_does_not_add_model_correction(tmp_path, monkeypatch):
    original = MockDevAdapter.next_turn

    def bad(self, context, tools):
        turn = original(self, context, tools)
        if turn.tool_calls[0].turn_decision is not None:
            turn.tool_calls[0].turn_decision.plan_update = {"wrong": True}
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", bad)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["call_counts"]["model"] == 4
    events = DevJournal(tmp_path, result["run_id"]).events()
    assert not any(e["event_type"] == "protocol_correction" for e in events)
    statuses = [e["payload"]["receipt"]["status"] for e in events
                if e["event_type"] == plans.EVENT]
    assert statuses == (["rejected", "not_requested", "rejected", "rejected"]
                        if FROZEN_ARM is None else ["rejected"] * 4)


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
