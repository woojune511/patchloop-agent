"""Post-edit review is current public context, not an extra call or semantic verdict."""

from __future__ import annotations

import json

import pytest
from test_dev_planning import call, put
from test_dev_planning import request as smoke_request

from patchloop.artifacts import ArtifactStore
from patchloop.dev import repair_guidance, runner
from patchloop.dev import working_plan as plans
from patchloop.dev.contracts import dev_tool_surface_hash
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.dev.tools import dev_tool_schemas
from patchloop.util import canonical_json, sha256_json

BASE = "sha256:" + "a" * 64
CURRENT = "sha256:" + "b" * 64
NEXT = "sha256:" + "c" * 64


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
def test_scope_review_reaches_real_completion_and_finish_without_extra_calls(
    tmp_path, monkeypatch, context_policy,
):
    original = MockDevAdapter.next_turn

    def annotated(self, context, tools):
        turn = original(self, context, tools)
        state = json.loads(context)
        selected = turn.tool_calls[0]
        if selected.name in {"run_check", "finish_task"}:
            checks = state.get("recent_checks", [])
            evidence = checks[-1]["action_id"] if selected.name == "finish_task" else None
            selected.turn_decision.scope_review = {
                "scope": "Public CSV record boundaries; other dialects are unassessed.",
                "source_action_ids": [],
                "cases": [{
                    "input": {"public_conditions": state["public_task"]["issue"]["title"],
                              "case_conditions": "Quoted multiline CSV through parse_rows."},
                    "expected_observation": {
                        "outcome": "The quoted newline remains within one record.",
                        "public_basis": (
                            "The public issue requires preserving quoted multiline fields."
                        ),
                    },
                    "disposition": "executed" if evidence else "untested",
                    "evidence_action_id": evidence,
                    "interpretation": "Public check receipt, not general parser coverage.",
                }],
            }
        return turn

    monkeypatch.setattr(MockDevAdapter, "next_turn", annotated)
    req = smoke_request(tmp_path).model_copy(update={"context_policy": context_policy})
    result = runner.run_dev(req)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    events = DevJournal(tmp_path, result["run_id"]).events()
    store = ArtifactStore(tmp_path / "artifacts")
    completion = next(
        event for event in events if event["event_type"] == "turn_started"
        and event["payload"]["workflow_gate"] == "ready_to_submit"
    )
    actual = reconstruct_state(
        runner._load_active_model_input(
            completion["payload"], store, context_policy=context_policy,
        ),
        context_policy=context_policy,
    )
    pending = actual["working_plan"]["plan"]["scope_review"]
    assert pending["diff_currency"] == "current"
    assert pending["cases"][0]["disposition"] == "untested"
    assert pending["cases"][0]["expected_observation"] == {
        "outcome": "The quoted newline remains within one record.",
        "public_basis": "The public issue requires preserving quoted multiline fields.",
    }
    finished = next(event["payload"]["result"] for event in events
                    if event["event_type"] == "action_finished"
                    and event["payload"]["result"]["tool"] == "finish_task")
    review = finished["output"]["plan_review"]["plan"]["scope_review"]
    execution = review["cases"][0]["execution"]
    assert review["coverage_status"] == "not_certified"
    assert execution["diff_hash"] == finished["output"]["patch_hash"]
    assert execution["observation"]["passed"] is True
    assert execution["currency"] == "current"
    assert review["mutation"]["candidate_diff_hash"] == execution["diff_hash"]
    assert not any(event["event_type"] == "protocol_correction" for event in events)


def mutation(journal, *, action="edit", tool="edit_files", baseline=BASE, current=CURRENT,
             start_changes=None, result_changes=None, output_changes=None, include_start=True):
    input_hash = sha256_json({"action": action})
    start = {
        "action_id": action, "input_hash": input_hash, "tool": tool, "arguments": {},
        "mutation_admitted": True, "baseline_diff_hash": baseline,
        "mutation_expected_worktree_diff_hash": current,
        **(start_changes or {}),
    }
    result = {
        "action_id": action, "input_hash": input_hash, "tool": tool, "status": "succeeded",
        "workspace_diff_hash": current, "replayed": False,
        "output": {"baseline_diff_hash": baseline, "worktree_diff_hash": current,
                   **(output_changes or {})},
        **(result_changes or {}),
    }
    if include_start:
        journal.append("action_started", start)
    journal.append("action_finished", {"action_id": action, "input_hash": input_hash,
                                        "result": result})
    return {"action_id": action, "input_hash": input_hash,
            "baseline_diff_hash": baseline, "candidate_diff_hash": current,
            "guidance": repair_guidance.BEHAVIOR_CHANGE_INSTRUCTIONS}


def projection(journal, diff=CURRENT):
    return plans.project(journal.events(), diff_hash=diff, gate="needs_visible_checks")


def focus(journal, diff=CURRENT):
    return projection(journal, diff)["review_request"].get("behavior_change")


def test_behavior_review_revision_changes_enabled_identity_without_new_schema(
    tmp_path, monkeypatch,
):
    policies = ("none", plans.POLICY, plans.EVIDENCE_POLICY)
    requests = {policy: smoke_request(tmp_path, policy) for policy in policies}
    identities = {
        policy: (runner._model_hash(request, None),
                 dev_tool_surface_hash(planning_policy=policy))
        for policy, request in requests.items()
    }
    schemas = {
        policy: dev_tool_schemas(finish_enabled=True, check_ids=["public"], planning_policy=policy)
        for policy in policies
    }
    before = plans.contract()
    monkeypatch.setattr(plans, "BEHAVIOR_CHANGE_INSTRUCTIONS",
                        plans.BEHAVIOR_CHANGE_INSTRUCTIONS + "\nPublic review revision.")
    after = plans.contract()
    assert before["behavior_change"]["instructions_hash"] != (
        after["behavior_change"]["instructions_hash"]
    )
    after["behavior_change"]["instructions_hash"] = before["behavior_change"]["instructions_hash"]
    assert after == before
    for policy, request in requests.items():
        revised = (runner._model_hash(request, None),
                   dev_tool_surface_hash(planning_policy=policy))
        for old, new in zip(identities[policy], revised, strict=True):
            assert (old == new) == (policy == "none")
        assert dev_tool_schemas(
            finish_enabled=True, check_ids=["public"], planning_policy=policy,
        ) == schemas[policy]


@pytest.mark.parametrize("tool", ["edit_files", "replace_text"])
@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("gate", ["needs_visible_checks", "ready_to_submit"])
def test_actual_request_delivers_current_focus_without_replacing_plan_or_evidence(
    tmp_path, tool, context_policy, gate,
):
    journal = DevJournal(tmp_path, "run_dev_semanticfocus")
    plan = "Required rejection behavior remains untested; retain input on failure."
    put(journal, plan, turn="before", diff=BASE)
    selected_source = {
        "path": "source.py", "start_line": 1, "end_line": 2,
        "content": "def accepts(value):\n    return True",
        "file_hash": "sha256:" + "d" * 64, "span_id": "public-span",
    }
    journal.append("action_finished", {"result": {
        "action_id": "read-public-scope", "input_hash": sha256_json({"path": "source.py"}),
        "tool": "read_file", "status": "succeeded", "workspace_diff_hash": BASE,
        "output": {"spans": [selected_source]},
    }})
    expected = mutation(journal, tool=tool)
    assert focus(journal) == expected
    state = {
        "public_task": {"task_id": "synthetic-public", "issue": "Preserve public behavior."},
        "workflow_gate": gate,
        "completion_guidance": {"verification_policy": "public-checks-v1"},
        "available_tool_names": ["read_file", "run_probe", "run_check", "edit_files",
                                 "finish_task", "stop_task"],
        "remaining_budget": {"model_calls": 7, "tool_actions": 9, "accepted_mutations": 2},
        "current_diff": {"patch_hash": CURRENT, "patch": "-return False\n+return True\n",
                         "changed_files": ["source.py"]},
        "working_plan": plans.project(journal.events(), diff_hash=CURRENT, gate=gate),
        "working_notes": {"findings": [], "verification": {"unresolved_ids": ["v1"], "items": [{
            "concern_id": "v1", "status": "open", "question": "Does invalid input reject?",
        }]}},
        "source_spans": [selected_source],
        "latest_tool_results": [{"tool": tool, "status": "succeeded",
                                 "action_id": "edit", "workspace_diff_hash": CURRENT,
                                 "output": {"worktree_diff_hash": CURRENT}}],
    }
    with journal.execution_lock():
        items = runner._build_model_input(
            journal=journal, artifact_store=ArtifactStore(tmp_path / "artifacts"),
            context=canonical_json(state), latest_tool_results=[],
            context_policy=context_policy, planning_policy=plans.POLICY,
        )
    actual = reconstruct_state(items, context_policy=context_policy)
    assert actual["working_plan"]["review_request"]["behavior_change"] == expected
    assert plans.contract()["behavior_change"]["instructions_hash"] == sha256_json(
        expected["guidance"],
    )
    assert actual["working_plan"]["plan"]["text"] == plan
    assert actual["working_plan"]["interpretation_status"] == "model_authored_unverified"
    receipts = actual["working_plan"]["source_receipts"]
    assert receipts["omitted_action_count"] == 0
    assert [item["action_id"] for item in receipts["items"]] == ["read-public-scope"]
    source_receipt = receipts["items"][0]
    assert source_receipt["diff_hash"] == BASE
    assert source_receipt["ranges"] == [{
        "source_scope": "repository", "path": "source.py",
        "file_hash": selected_source["file_hash"], "start_line": 1, "end_line": 2,
    }]
    assert "content" not in canonical_json(receipts)
    for key in ("public_task", "workflow_gate", "available_tool_names", "remaining_budget",
                "current_diff"):
        assert actual[key] == state[key]
    notes = actual["working_notes"]
    assert notes["findings"] == []
    assert notes["verification"] == {
        "model_open_concern_ids": ["v1"],
        "items": [{"concern_id": "v1", "question": "Does invalid input reject?",
                   "model_position": "open", "behavior_coverage": "not_assessed"}],
    }
    if context_policy == "segmented-v1":
        assert notes["interpretation_status"] == "model_authored_unverified"
    assert actual["current_sources"] == [{
        "path": "source.py", "file_hash": "sha256:" + "d" * 64,
        "content_delivery": {}, "inline_spans": [{
            "start_line": 1, "end_line": 2,
            "content": "def accepts(value):\n    return True",
        }],
    }]
    if gate == "needs_visible_checks":
        assert actual["latest_tool_results"] == state["latest_tool_results"]
    else:
        result = actual["latest_tool_results"][0]
        assert (result["action_id"], result["tool"], result["status"],
                result["workspace_diff_hash"]) == ("edit", tool, "succeeded", CURRENT)
    assert not any(event["event_type"] == "provider_call_started" for event in journal.events())


@pytest.mark.parametrize("case", [
    "failed", "stale", "no_op", "wrong_input", "no_start", "not_admitted",
    "wrong_candidate", "wrong_output", "replay", "wrong_tool",
])
def test_focus_requires_a_new_accepted_current_mutation(tmp_path, case):
    journal = DevJournal(tmp_path, "run_dev_focusboundary")
    put(journal, "Existing public plan", turn="before", diff=BASE)
    kwargs = {
        "failed": {"result_changes": {"status": "failed"}},
        "stale": {"current": NEXT},
        "no_op": {"baseline": CURRENT},
        "wrong_input": {"start_changes": {"input_hash": "sha256:" + "e" * 64}},
        "no_start": {"include_start": False},
        "not_admitted": {"start_changes": {"mutation_admitted": False}},
        "wrong_candidate": {"start_changes": {"mutation_expected_worktree_diff_hash": NEXT}},
        "wrong_output": {"output_changes": {"worktree_diff_hash": NEXT}},
        "replay": {"result_changes": {"replayed": True}},
        "wrong_tool": {"start_changes": {"tool": "run_check"}},
    }[case]
    mutation(journal, **kwargs)
    assert focus(journal) is None
    assert projection(journal)["plan"]["text"] == "Existing public plan"


@pytest.mark.parametrize("plan_update", [None, ""])
def test_valid_batch_consumes_once_but_protocol_failure_and_turn_start_do_not(
    tmp_path, plan_update,
):
    journal = DevJournal(tmp_path, "run_dev_focusconsumption")
    put(journal, "Keep the untested rejection condition", turn="before", diff=BASE)
    first = mutation(journal)
    journal.append("turn_started", {"turn_id": "invalid"})
    journal.append("turn_decision_recorded", {"turn_id": "invalid",
                                               "error_code": "protocol_violation"})
    assert focus(journal) == first
    receipt = put(journal, turn="valid", diff=CURRENT, gate="needs_visible_checks",
                  calls=[call(plan_update, action="verify")])
    assert receipt["status"] == ("not_requested" if plan_update is None else "rejected")
    assert focus(journal) is None
    assert projection(journal)["last_update_result"]["review_request"]["behavior_change"] == first
    before = journal.path.read_bytes()
    assert put(journal, turn="valid", diff=CURRENT) == receipt
    assert journal.path.read_bytes() == before
    second = mutation(journal, action="next-edit", baseline=CURRENT, current=NEXT,
                      output_changes={"recovered_after_crash": True})
    assert focus(DevJournal(tmp_path, journal.run_id), NEXT) == second
    assert projection(journal, NEXT)["plan"]["text"] == "Keep the untested rejection condition"


@pytest.mark.parametrize("agent_policy,planning_policy", [
    ("current", "brief-v1"), ("current", "none"), ("thin", "none"),
])
def test_native_mock_run_uses_existing_calls_and_reaches_isolated_evaluation(
    tmp_path, agent_policy, planning_policy,
):
    request = smoke_request(tmp_path, planning_policy).model_copy(update={
        "agent_policy": agent_policy,
    })
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert result["call_counts"] == {"model": 4, "tool": 5, "input_count": 0}
    assert result["cost_nanos"] == 0
    events = DevJournal(tmp_path, result["run_id"]).events()
    store = ArtifactStore(tmp_path / "artifacts")
    delivered = []
    for event in events:
        if event["event_type"] != "turn_started":
            continue
        items = runner._load_active_model_input(event["payload"], store)
        state = reconstruct_state(items)
        current = state.get("working_plan", {}).get("review_request", {}).get("behavior_change")
        if current is not None:
            delivered.append((state, current))
        assert "reference_patch" not in json.dumps(state)
    assert len(delivered) == (1 if planning_policy == "brief-v1" else 0)
    if delivered:
        state, current = delivered[0]
        assert current["candidate_diff_hash"] == state["current_diff"]["patch_hash"]
        assert current["baseline_diff_hash"] != current["candidate_diff_hash"]
        assert state["workflow_gate"] == "needs_visible_checks"
        assert "run_check" in state["available_tool_names"]
        assert state["working_plan"]["plan"] is not None
    assert sum(event["event_type"] == "action_started"
               and event["payload"]["tool"] == "replace_text" for event in events) == 1
