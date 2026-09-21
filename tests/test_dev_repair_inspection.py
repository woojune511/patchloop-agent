"""Opt-in inspection spending preserves the current repair, not future check recovery."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict

import pytest
import yaml
from pydantic import ValidationError
from test_dev_mutation_attempt_budget import _consume, _state
from test_dev_resume_v12 import SimulatedCrash, _request
from typer.testing import CliRunner

from patchloop.artifacts import ArtifactStore
from patchloop.cli import app
from patchloop.dev import runner
from patchloop.dev.contracts import DevLimits, DevModelTurn, DevRunRequest, RequestedTool
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ResumeContractMismatch
from patchloop.repository import WorkspaceManager

POLICY = "current-failure-v1"


def _policy(gateway, counters, policy=POLICY):
    return runner._tool_policy(
        gateway, counters, DevLimits(), repair_inspection_policy=policy,
    )


def test_only_future_check_recovery_is_released_at_the_ten_call_boundary():
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=10, mutations=3)
    default = _policy(gateway, counters, "protected-v1")
    selected = _policy(gateway, counters)
    assert default.allowed_tools == {"replace_text", "stop_task"}
    assert default.model_turns_available_for_exploration == 0
    assert selected.allowed_tools == default.allowed_tools | {"read_file", "search_files"}
    assert selected.model_turns_available_for_exploration == 4
    assert selected.max_parallel_reads == 4
    assert selected.inspection_reserve_calls == 6
    assert selected.minimum_completion_calls == 4
    assert selected.mutation_recovery_reserve_calls == 2
    assert selected.inspection_released_check_recovery_calls == 4
    # Full future-failure forecast and admission of every other action stay exact.
    assert selected.completion_budget_calls == default.completion_budget_calls == 10
    assert selected.check_ids == default.check_ids
    assert runner._mutation_completion_horizon(selected) == runner._mutation_completion_horizon(
        default,
    )


@pytest.mark.parametrize("model,tools", [(6, 100), (40, 6), (3, 100), (40, 3)])
def test_either_budget_closes_reads_before_spending_the_repair_reserve(model, tools):
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=model, tools=tools, mutations=3)
    selected = _policy(gateway, counters)
    assert not selected.exploration_allowed
    assert selected.max_parallel_reads == 0
    assert "read_file" not in selected.allowed_tools
    assert ("replace_text" in selected.allowed_tools) is (min(model, tools) >= 4)
    assert "finish_task" not in selected.allowed_tools


@pytest.mark.parametrize("model,tools", [(7, 100), (40, 7)])
def test_last_read_warning_uses_the_selected_policy_without_mutating_counters(model, tools):
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=model, tools=tools, mutations=3)
    before = asdict(counters)
    selected = _policy(gateway, counters)
    assert asdict(counters) == before
    assert selected.exploration_state == "last_opportunity"
    assert selected.max_parallel_reads == (1 if tools == 7 else 4)
    assert set(selected.tools_closing_after_this_turn) == {"read_file", "search_files"}
    _consume(counters, "read_file")
    assert _policy(gateway, counters).allowed_tools == {"replace_text", "stop_task"}


@pytest.mark.parametrize("statuses", [("PASS", "PASS"), ("NOT_RUN", "NOT_RUN")])
@pytest.mark.parametrize("pending_failure", [False, True])
def test_historical_failure_and_probe_failure_cannot_release_future_reserve(
    statuses, pending_failure,
):
    gateway, counters = _state(statuses, model=10, mutations=3)
    counters.failed_check_pending = pending_failure
    default = _policy(gateway, counters, "protected-v1")
    selected = _policy(gateway, counters)
    assert selected.inspection_released_check_recovery_calls == 0
    assert selected.allowed_tools == default.allowed_tools
    assert selected.inspection_reserve_calls == default.inspection_reserve_calls
    assert selected.model_turns_available_for_exploration == (
        default.model_turns_available_for_exploration
    )


@pytest.mark.parametrize("overrides", [
    {"mutations": 0}, {"untracked": True}, {"anchor": False, "model": 5},
    {"mutations": 1}, {"used": {"check-0", "check-1"}},
])
def test_infeasible_repairs_missing_anchors_and_no_future_allowance_keep_existing_rules(overrides):
    state = {"model": 10, "mutations": 3, **overrides}
    gateway, counters = _state(("FAIL", "NOT_RUN"), **state)
    default = _policy(gateway, counters, "protected-v1")
    selected = _policy(gateway, counters)
    assert selected.allowed_tools == default.allowed_tools
    assert selected.max_parallel_reads == default.max_parallel_reads
    assert selected.completion_possible == default.completion_possible


@pytest.mark.parametrize("read_used", [False, True])
@pytest.mark.parametrize("retry", [False, True])
def test_current_read_credit_and_rejection_allowance_are_not_reserved_twice(read_used, retry):
    gateway, counters = _state(
        ("FAIL", "NOT_RUN"), model=10, mutations=3, read_used=read_used, retry=retry,
    )
    selected = _policy(gateway, counters)
    assert selected.current_repair_read_reserve_calls == int(not read_used)
    assert selected.inspection_reserve_calls == (6 if retry else 4)
    assert selected.inspection_uses_repair_credit is not read_used
    assert selected.model_turns_available_for_exploration == (4 if retry else 6)


def test_spent_inspections_still_allow_rejection_read_repair_checks_and_finish():
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=10, mutations=3)
    for remaining in (4, 3, 2, 1):
        assert _policy(gateway, counters).model_turns_available_for_exploration == remaining
        _consume(counters, "read_file")
    assert _policy(gateway, counters).allowed_tools == {"replace_text", "stop_task"}
    _consume(counters, "replace_text", succeeded=False)
    gateway.anchor = False
    assert "read_file" in _policy(gateway, counters).allowed_tools
    _consume(counters, "read_file")
    gateway.anchor = True
    assert "replace_text" in _policy(gateway, counters).allowed_tools
    _consume(counters, "replace_text")
    gateway.accepted_mutations += 1
    gateway.statuses = dict.fromkeys(gateway.statuses, "NOT_RUN")
    assert _policy(gateway, counters).inspection_released_check_recovery_calls == 0
    for check_id in gateway.statuses:
        assert check_id in _policy(gateway, counters).check_ids
        _consume(counters, "run_check", output={"check_id": check_id, "passed": True})
        gateway.statuses[check_id] = "PASS"
    assert _policy(gateway, counters).allowed_tools == {"finish_task", "stop_task"}
    _consume(counters, "finish_task")
    assert counters.model_calls == 40


def test_a_later_failed_check_can_exhaust_recovery_without_false_submission_credit():
    gateway, counters = _state(("FAIL", "NOT_RUN"), model=10, mutations=3)
    for _ in range(4):
        _consume(counters, "read_file")
    _consume(counters, "replace_text", succeeded=False)
    _consume(counters, "read_file")
    _consume(counters, "replace_text")
    gateway.accepted_mutations += 1
    gateway.statuses = dict.fromkeys(gateway.statuses, "NOT_RUN")
    _consume(counters, "run_check", output={"check_id": "check-1", "passed": False})
    gateway.statuses["check-1"] = "FAIL"
    selected = _policy(gateway, counters)
    assert selected.minimum_completion_calls == 4
    assert not selected.completion_possible
    assert selected.allowed_tools == {"stop_task"}


@pytest.mark.parametrize("policy", ["protected-v1", POLICY])
def test_cli_and_request_identity(tmp_path, monkeypatch, policy):
    request = _request(tmp_path)
    assert request.repair_inspection_policy == "protected-v1"
    assert runner._model_hash(request, None) == (
        "sha256:c48a2d7968cd234a7caa928007f1caefeda63de4f90e0d25a3da03208b3076f2"
    )
    captured = []
    monkeypatch.setattr(runner, "run_dev", lambda req: captured.append(req) or {})
    result = CliRunner().invoke(app, [
        "dev", "--provider", "mock", "--task", str(request.task), "--model", "mock-dev",
        "--repair-inspection-policy", policy,
    ])
    assert result.exit_code == 0, result.output
    assert captured[0].repair_inspection_policy == policy
    assert (runner._model_hash(captured[0], None) == runner._model_hash(request, None)) == (
        policy == "protected-v1"
    )
    with pytest.raises(ValidationError, match="repair_inspection_policy"):
        DevRunRequest.model_validate({
            **request.model_dump(), "repair_inspection_policy": "unknown",
        })


def _smoke_request(root, context_policy, policy):
    task_dir = root / "task"
    original = _request(root)
    shutil.copytree(original.task.parent, task_dir)
    public_path = task_dir / "public.yaml"
    public = yaml.safe_load(public_path.read_text(encoding="utf-8"))
    public["visible_checks"].append({**public["visible_checks"][0], "id": "second-public-check"})
    public_path.write_text(yaml.safe_dump(public), encoding="utf-8")
    return original.model_copy(update={
        "task": public_path, "context_policy": context_policy, "planning_policy": "brief-v1",
        "repair_inspection_policy": policy, "repair_recheck": True,
        "limits": DevLimits(max_model_calls=13),
    })


def _script(monkeypatch):
    contexts = []

    class Adapter(MockDevAdapter):
        def _next_action(self, context, tools):
            state = json.loads(context)
            contexts.append(state)
            wrong = self.mutation.old_text.replace("return rows", "return []")
            if state["current_public_failure"]:
                if any(tool["name"] == "read_file" for tool in tools):
                    call = RequestedTool(
                        name="read_file", action_id="inspect", arguments={
                            "path": self.mutation.path, "start_line": 1, "end_line": 80,
                        }, turn_decision={"mode": "inspect", "basis": "Exercise the read boundary.",
                                          "evidence_goal": "Observe the current failed candidate."},
                    )
                else:
                    call = RequestedTool(
                        name="replace_text", action_id="repair", arguments={
                            "path": self.mutation.path, "old_text": wrong,
                            "new_text": self.mutation.new_text, "occurrence": 1,
                            "hypothesis": "Parse complete CSV input.",
                            "expected_behavior": "Preserve public CSV rows.",
                            "causal_revision": None,
                        }, turn_decision={"mode": "mutate", "basis": "Repair the failed candidate"},
                    )
                turn = DevModelTurn(tool_calls=[call])
            else:
                turn = super()._next_action(context, tools)
                if turn.tool_calls[0].name == "search_files":
                    # This short model budget admits only the required first anchor read.
                    turn.tool_calls = [turn.tool_calls[1]]
                if turn.tool_calls[0].name == "replace_text":
                    turn.tool_calls[0].arguments["new_text"] = wrong
            for index, call in enumerate(turn.tool_calls):
                call.action_id = f"boundary-{state['remaining_budget']['model_calls']}-{index}"
            return turn

    monkeypatch.setattr(runner, "MockDevAdapter", Adapter)
    return contexts


@pytest.mark.parametrize("context_policy", ["append-v1", "segmented-v1"])
@pytest.mark.parametrize("policy", ["protected-v1", POLICY])
def test_actual_inputs_repair_recheck_submission_isolated_evaluation_and_resume(
    tmp_path, monkeypatch, context_policy, policy,
):
    contexts = _script(monkeypatch)
    request = _smoke_request(tmp_path, context_policy, policy)
    workspaces = []
    create = WorkspaceManager.create

    def capture(self, name, *args, **kwargs):
        workspace = create(self, name, *args, **kwargs)
        workspaces.append((name, workspace))
        return workspace

    monkeypatch.setattr(WorkspaceManager, "create", capture)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["accepted_mutations"] == 2
    assert result["cost_nanos"] == result["call_counts"]["input_count"] == 0
    assert result["call_counts"]["model"] == (10 if policy == POLICY else 6)
    assert len(workspaces) == 2 and workspaces[1][0].startswith("eval_")
    assert workspaces[0][1] != workspaces[1][1]
    failures = [state for state in contexts if state["current_public_failure"]]
    assert len(failures) == (5 if policy == POLICY else 1)
    if policy == POLICY:
        assert [state["action_horizon"]["model_turns_available_for_exploration"]
                for state in failures] == [4, 3, 2, 1, 0]
    journal = DevJournal(tmp_path, result["run_id"])
    assert journal.load_envelope().repair_inspection_policy == policy
    started = next(event["payload"] for event in journal.events()
                   if event["event_type"] == "run_started")
    assert started.get("repair_inspection_policy", "protected-v1") == policy
    assert ("repair_inspection_policy" in json.loads(journal.envelope_path.read_text())) == (
        policy == POLICY
    )
    store = ArtifactStore(tmp_path / "artifacts")
    turns = [event["payload"] for event in journal.events()
             if event["event_type"] == "turn_started"]
    assert len(turns) == len(contexts)
    for turn, context in zip(turns, contexts, strict=True):
        native = runner._load_active_model_input(turn, store, context_policy=context_policy)
        actual = reconstruct_state(native, context_policy=context_policy)
        assert actual["public_task"] == context["public_task"]
        assert actual["current_diff"]["patch_hash"] == context["current_diff"]["patch_hash"]
        assert actual["visible_check_status"] == context["visible_check_status"]
        assert actual["action_horizon"].get("repair_inspection") == (
            context["action_horizon"].get("repair_inspection")
        )
        assert turn.get("repair_inspection") == actual["action_horizon"].get("repair_inspection")
        for forbidden in ("hidden-multiline-csv", "reference_patch", "private_spec"):
            assert forbidden not in json.dumps(native)
    before = journal.path.read_bytes()
    resumed = runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"]}))
    assert resumed["runs"][0] == result
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={
            "resume_run_id": result["run_id"],
            "repair_inspection_policy": "protected-v1" if policy == POLICY else POLICY,
        }))
    assert journal.path.read_bytes() == before


def test_resume_replays_extra_inspection_once_and_keeps_the_selected_horizon(tmp_path, monkeypatch):
    contexts = _script(monkeypatch)
    request = _smoke_request(tmp_path, "segmented-v1", POLICY)
    append = DevJournal.append
    crashed = False

    def crash(self, kind, payload=None):
        nonlocal crashed
        event = append(self, kind, payload)
        if (not crashed and kind == "action_finished"
                and payload["result"]["action_id"] == "boundary-10-0"):
            crashed = True
            raise SimulatedCrash()
        return event

    monkeypatch.setattr(DevJournal, "append", crash)
    with pytest.raises(SimulatedCrash):
        runner.run_dev(request)
    run_id = next((tmp_path / "runs").glob("*.jsonl")).stem
    result = runner.run_dev(request.model_copy(update={"resume_run_id": run_id}))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS", result
    assert result["call_counts"]["model"] == len(contexts) == 10
    events = DevJournal(tmp_path, run_id).events()
    assert sum(event["event_type"] == "action_finished"
               and event["payload"]["result"]["action_id"] == "boundary-10-0"
               for event in events) == 1
    assert contexts[4]["action_horizon"]["model_turns_available_for_exploration"] == 3
