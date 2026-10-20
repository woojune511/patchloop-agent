from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

import patchloop.dev.runner as runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError, ResumeContractMismatch
from patchloop.git_execution import GitExecutionUncertain
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox


class SimulatedCrash(BaseException):
    pass


def request(root, reserve=330):
    return DevRunRequest(
        provider="mock", model="mock-dev", state_root=root,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        evaluation_reserve_seconds=reserve,
    )


def journal_for(root):
    return DevJournal(root, next((root / "runs").glob("*.jsonl")).stem)


def paced_pipeline(monkeypatch, *, model_seconds=340, evaluation_seconds=300):
    """Exercise real mock decisions, edits, public checks and isolated evaluation."""
    clock = [0.0]
    contexts, calls, checks, evaluations = [], [], [], []
    monkeypatch.setattr(runner, "monotonic", lambda: clock[0])
    original_check = LocalSandbox.run_check
    original_evaluate = runner.EvaluationEngine.evaluate

    class PacedMock(MockDevAdapter):
        def next_turn(self, context, tools):
            contexts.append(json.loads(context))
            clock[0] += model_seconds
            turn = super().next_turn(context, tools)
            calls.append([call.name for call in turn.tool_calls])
            return turn

    def check(self, workspace, declaration, *, deadline=None, **kwargs):
        checks.append((workspace.parent.name.startswith("eval_"), deadline.expires_at))
        result = original_check(self, workspace, declaration, deadline=deadline, **kwargs)
        if not workspace.parent.name.startswith("eval_"):
            clock[0] += 20
        deadline.check()
        return result

    def evaluate(self, *args, deadline=None, **kwargs):
        evaluations.append((clock[0], deadline.expires_at))
        # Emulate finite isolated checkout/check overhead under its passed deadline.
        clock[0] += evaluation_seconds
        deadline.check()
        return original_evaluate(self, *args, deadline=deadline, **kwargs)

    monkeypatch.setattr(runner, "MockDevAdapter", PacedMock)
    monkeypatch.setattr(LocalSandbox, "run_check", check)
    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", evaluate)
    return clock, contexts, calls, checks, evaluations


def test_solver_and_evaluator_use_distinct_portions_of_same_total_limit(tmp_path, monkeypatch):
    clock, contexts, calls, checks, evaluations = paced_pipeline(monkeypatch)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    assert calls[-1] == ["finish_task"]
    assert clock[0] == 1_680
    assert evaluations == [(1_380, 1_800)]
    assert (False, 1_470) in checks and (True, 1_800) in checks
    first = contexts[0]["remaining_budget"]
    assert first["active_wall_time_seconds"] == 1_470
    assert first["total_active_wall_time_seconds"] == 1_800
    assert first["evaluation_reserve_seconds"] == 330
    assert first["active_wall_time_scope"] == "solver"
    assert all("hidden-multiline-csv" not in json.dumps(context) for context in contexts)
    journal = journal_for(tmp_path)
    receipt = next(e["payload"] for e in journal.events() if e["event_type"] == "solver_finished")
    assert receipt["active_elapsed_ms"] == 1_380_000
    assert journal.load_envelope().evaluation_reserve_seconds == 330


def test_solver_cannot_spend_evaluation_time_or_force_submit(tmp_path, monkeypatch):
    clock, contexts, calls, _, evaluations = paced_pipeline(monkeypatch, model_seconds=430)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED" and result["evaluator"] is None
    assert calls[-1] == ["finish_task"]  # Returned too late to execute the requested finish.
    assert clock[0] < 1_800 and contexts[-1]["remaining_budget"]["active_wall_time_seconds"] > 0
    assert evaluations == []
    events = journal_for(tmp_path).events()
    assert not any(e["event_type"] in {"solver_finished", "submission_recorded"} for e in events)
    assert not any(e["event_type"] == "action_started"
                   and e["payload"]["tool"] == "finish_task" for e in events)


def test_finish_storage_crossing_solver_cutoff_is_not_admitted(tmp_path, monkeypatch):
    clock, _, _, _, evaluations = paced_pipeline(monkeypatch)
    append = DevJournal.append

    def slow_finish_storage(self, event_type, payload=None):
        result = append(self, event_type, payload)
        if (event_type == "action_finished"
                and payload["result"]["tool"] == "finish_task"):
            clock[0] = 1_471
        return result

    monkeypatch.setattr(DevJournal, "append", slow_finish_storage)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert result["terminal"] == "LIMIT_REACHED" and result["evaluator"] is None
    assert evaluations == []
    assert not any(e["event_type"] in {"solver_finished", "submission_recorded"}
                   for e in journal_for(tmp_path).events())


def test_submitted_candidate_recovers_after_solver_cutoff_without_new_actions(
    tmp_path, monkeypatch,
):
    clock, _, calls, _, evaluations = paced_pipeline(monkeypatch, evaluation_seconds=250)
    append = DevJournal.append
    crashed = False

    def crash_after_submission(self, event_type, payload=None):
        nonlocal crashed
        result = append(self, event_type, payload)
        if event_type == "submission_recorded" and not crashed:
            crashed = True
            clock[0] = 1_500
            append(self, "metadata_progress", {"active_elapsed_ms": 1_500_000})
            raise SimulatedCrash()
        return result

    monkeypatch.setattr(DevJournal, "append", crash_after_submission)
    original = request(tmp_path)
    with pytest.raises(SimulatedCrash):
        runner.run_dev(original)
    journal = journal_for(tmp_path)
    assert len(calls) == 4
    before_actions = [
        e["event_hash"] for e in journal.events() if e["event_type"] == "action_started"
    ]
    resumed = original.model_copy(update={"resume_run_id": journal.run_id})
    result = runner.run_dev(resumed)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS" and len(calls) == 4
    assert evaluations == [(1_500, 1_800)] and clock[0] == 1_750
    assert [e["event_hash"] for e in journal.events()
            if e["event_type"] == "action_started"] == before_actions
    assert sum(e["event_type"] == "solver_finished" for e in journal.events()) == 1
    assert sum(e["event_type"] == "action_started" and e["payload"]["tool"] == "finish_task"
               for e in journal.events()) == 1
    # The reserve is resume identity, not a fresh allowance on each process.
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(resumed.model_copy(update={"evaluation_reserve_seconds": 329}))


def test_late_or_mismatched_finish_receipt_cannot_unlock_evaluation(tmp_path, monkeypatch):
    _, _, calls, _, evaluations = paced_pipeline(monkeypatch)
    append = DevJournal.append
    crashed = False

    def crash_after_solver_finish(self, event_type, payload=None):
        nonlocal crashed
        result = append(self, event_type, payload)
        if event_type == "solver_finished" and not crashed:
            crashed = True
            raise SimulatedCrash()
        return result

    monkeypatch.setattr(DevJournal, "append", crash_after_solver_finish)
    original = request(tmp_path)
    with pytest.raises(SimulatedCrash):
        runner.run_dev(original)
    journal = journal_for(tmp_path)
    resume = original.model_copy(update={"resume_run_id": journal.run_id})
    original_events = DevJournal.events
    before = journal.path.read_bytes()
    for field, value in (("active_elapsed_ms", 1_470_000), ("patch_hash", "sha256:" + "0" * 64)):
        def damaged_events(self, field=field, value=value):
            events = original_events(self)
            for event in events:
                if event["event_type"] == "solver_finished":
                    event["payload"][field] = value
            return events

        with monkeypatch.context() as guard:
            guard.setattr(DevJournal, "events", damaged_events)
            with pytest.raises(RecoveryError, match="timely submitted candidate"):
                runner.run_dev(resume)
        assert journal.path.read_bytes() == before
        assert len(calls) == 4 and evaluations == []
    assert runner.run_dev(resume)["runs"][0]["terminal"] == "EVALUATOR_PASS"
    assert len(calls) == 4


def test_evaluation_still_stops_at_original_total_limit(tmp_path, monkeypatch):
    _, _, _, _, evaluations = paced_pipeline(monkeypatch, evaluation_seconds=500)
    result = runner.run_dev(request(tmp_path))["runs"][0]
    assert evaluations == [(1_380, 1_800)]
    assert result["terminal"] == "LIMIT_REACHED"
    assert result["evaluator"]["failure_class"] == "ACTIVE_DEADLINE_EXHAUSTED"


def test_default_zero_preserves_legacy_request_envelope_and_solver_deadline(tmp_path, monkeypatch):
    _, contexts, _, checks, evaluations = paced_pipeline(monkeypatch, model_seconds=10)
    req = request(tmp_path, 0)
    assert "evaluation_reserve_seconds" not in req.model_dump(mode="json")
    assert runner.run_dev(req)["runs"][0]["terminal"] == "EVALUATOR_PASS"
    raw = json.loads(journal_for(tmp_path).envelope_path.read_bytes())
    assert "evaluation_reserve_seconds" not in raw
    assert all(expires == 1_800 for _, expires in checks)
    assert evaluations == [(60, 1_800)]
    assert "evaluation_reserve_seconds" not in contexts[0]["remaining_budget"]
    assert not any(e["event_type"] == "solver_finished" for e in journal_for(tmp_path).events())


@pytest.mark.parametrize("reserve", [-1, 1_800, 1_801, True])
def test_reserve_must_leave_solver_time_within_existing_total(tmp_path, reserve):
    with pytest.raises(ValidationError):
        request(tmp_path, reserve)


def test_invocation_preserves_uncertain_stop_even_when_terminal_is_limit(tmp_path, monkeypatch):
    calls = []

    def uncertain_evaluation(*args, **kwargs):
        calls.append(True)
        raise GitExecutionUncertain("evaluation child cleanup is uncertain", details={
            "deadline_exhausted": True,
        })

    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", uncertain_evaluation)
    result = runner.run_dev(request(tmp_path).model_copy(update={"repeat": 2}))
    assert result["completed_repetitions"] == 1 and calls == [True]
    assert result["runs"][0]["terminal"] == "LIMIT_REACHED"
    assert result["stop_remaining"] is True
