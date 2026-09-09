from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import patchloop.dev.runner as runner
from patchloop.artifacts import ArtifactStore
from patchloop.deadline import ExecutionDeadlineExceeded
from patchloop.dev.contracts import DevRunRequest, DevTerminal
from patchloop.dev.evaluation_completion import EvaluationCompletion
from patchloop.dev.state import DevJournal
from patchloop.errors import RecoveryError
from patchloop.runtime import repository_root
from patchloop.sandbox import LocalSandbox
from patchloop.sandbox.runner import SandboxCleanupError
from patchloop.util import sha256_json


class SimulatedCrash(BaseException):
    pass


def _request(root: Path) -> DevRunRequest:
    return DevRunRequest(
        provider="mock", model="mock-dev", state_root=root,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
    )


def _crash_after_completion(monkeypatch, boundary="evaluator_finished"):
    original = DevJournal.append
    original_write = ArtifactStore.write_bytes_atomic
    fired = False

    def append(self, event_type, payload=None):
        nonlocal fired
        result = original(self, event_type, payload)
        if boundary == "evaluator_finished" and event_type == boundary and not fired:
            fired = True
            raise SimulatedCrash()
        return result

    def write(self, path, content):
        nonlocal fired
        original_write(self, path, content)
        if (boundary == "terminal_provenance" and not fired
                and Path(path).name == "terminal-provenance.json"):
            fired = True
            raise SimulatedCrash()

    monkeypatch.setattr(DevJournal, "append", append)
    monkeypatch.setattr(ArtifactStore, "write_bytes_atomic", write)


def _forbid_execution(*args, **kwargs):
    raise AssertionError("completed evaluation must not enter task execution or preflight")


def _completed_run(tmp_path, monkeypatch, *, outcome="pass", boundary="evaluator_finished"):
    request = _request(tmp_path)
    original_checks = runner.EvaluationEngine._run_checks
    original_check = LocalSandbox.run_check
    clock = [0.0]
    monkeypatch.setattr(runner, "monotonic", lambda: clock[0])

    def check(self, workspace, *args, **kwargs):
        result = original_check(self, workspace, *args, **kwargs)
        if outcome == "fail" and workspace.parent.name.startswith("eval_"):
            return replace(result, exit_code=1, stdout="synthetic check failure")
        return result

    def checks(self, run_id, workspace, declared, kind, results, recorded, deadline=None):
        selected = declared if outcome in {"pass", "fail"} else declared[:1]
        original_checks(self, run_id, workspace, selected, kind, results, recorded, deadline)
        if outcome not in {"pass", "fail"}:
            clock[0] = 1_801.0 if outcome == "deadline" else 5.0
            error = {
                "error": RuntimeError, "cleanup": SandboxCleanupError,
                "deadline": ExecutionDeadlineExceeded,
            }[outcome]
            raise error("synthetic evaluator interruption after one check")
        clock[0] = 5.0

    monkeypatch.setattr(LocalSandbox, "run_check", check)
    monkeypatch.setattr(runner.EvaluationEngine, "_run_checks", checks)
    _crash_after_completion(monkeypatch, boundary)
    with pytest.raises(SimulatedCrash):
        runner.run_dev(request)
    run_id = next((tmp_path / "runs").glob("*.jsonl")).stem
    journal = DevJournal(tmp_path, run_id)
    payload = next(e["payload"] for e in journal.events()
                   if e["event_type"] == "evaluator_finished")
    return request.model_copy(update={"resume_run_id": run_id}), journal, payload


@pytest.mark.parametrize("boundary", ["evaluator_finished", "terminal_provenance"])
@pytest.mark.parametrize("outcome", ["pass", "fail", "error", "cleanup", "deadline"])
def test_durable_evaluation_resume_finishes_without_execution(
    tmp_path, monkeypatch, outcome, boundary,
):
    request, journal, payload = _completed_run(
        tmp_path, monkeypatch, outcome=outcome, boundary=boundary,
    )
    completion = EvaluationCompletion.model_validate(payload)
    run_dir = tmp_path / "artifacts/runs" / journal.run_id
    before = {p.name: p.read_bytes() for p in run_dir.iterdir() if p.is_file()}
    expected_terminal = {
        "pass": "EVALUATOR_PASS", "fail": "EVALUATOR_FAIL", "error": "EVALUATOR_ERROR",
        "cleanup": "EVALUATOR_ERROR", "deadline": "LIMIT_REACHED",
    }[outcome]
    finalizations = []
    original_finish = runner._finish_evaluation_metadata

    def finalize(**kwargs):
        result = original_finish(**kwargs)
        finalizations.append(result.stop_remaining)
        return result

    monkeypatch.setattr(runner, "_run_one_locked", _forbid_execution)
    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", _forbid_execution)
    monkeypatch.setattr(runner, "_finish_evaluation_metadata", finalize)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == expected_terminal
    assert result["evaluator"] == payload["summary"]
    assert result["artifact_hashes"] == completion.artifact_hashes
    assert result["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert result["cost_nanos"] == 0
    assert finalizations == [outcome == "cleanup"]
    terminal = journal.terminal()["payload"]
    assert terminal["message"] == payload["message"]
    assert terminal["active_elapsed_ms"] == payload["active_elapsed_ms"]
    assert terminal["active_elapsed_ms"] == (1_801_000 if outcome == "deadline" else 5_000)
    assert all((run_dir / name).read_bytes() == raw for name, raw in before.items())
    assert len(list((tmp_path / "workspaces").glob("eval_*"))) == 1
    assert sum(e["event_type"] == "evaluator_finished" for e in journal.events()) == 1
    provenance = json.loads((run_dir / "provenance.json").read_bytes())
    assert provenance["completed_check_results"]
    if outcome not in {"pass", "fail"}:
        assert len(provenance["completed_check_results"]) == 1
    journal_bytes = journal.path.read_bytes()
    assert runner.run_dev(request)["runs"][0] == result
    assert journal.path.read_bytes() == journal_bytes


def test_changed_second_verdict_is_never_requested(tmp_path, monkeypatch):
    request, journal, payload = _completed_run(tmp_path, monkeypatch)
    original = runner.EvaluationEngine.evaluate
    calls = []

    def changed_verdict(self, *args, **kwargs):
        calls.append(True)
        result = original(self, *args, **kwargs)
        return result.model_copy(update={"scope_compliant_success": False})

    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", changed_verdict)
    assert runner.run_dev(request)["runs"][0]["terminal"] == "EVALUATOR_PASS"
    assert calls == []
    assert journal.terminal()["payload"]["evaluator"] == payload["summary"]


@pytest.mark.parametrize("name", [
    "submitted_patch", "manifest", "evaluator_summary", "evaluator_provenance",
    "terminal_provenance",
])
def test_corrupt_completion_artifact_stops_before_execution_or_journal_change(
    tmp_path, monkeypatch, name,
):
    request, journal, payload = _completed_run(tmp_path, monkeypatch)
    Path(payload["artifacts"][name]["path"]).write_bytes(b"synthetic corrupted CAS")
    before = journal.path.read_bytes()
    monkeypatch.setattr(runner, "_run_one_locked", _forbid_execution)
    with pytest.raises(RecoveryError):
        runner.run_dev(request)
    assert journal.path.read_bytes() == before
    assert journal.terminal() is None


@pytest.mark.parametrize("damage", ["missing", "tampered"])
def test_completed_check_leaf_evidence_must_survive_metadata_resume(
    tmp_path, monkeypatch, damage,
):
    request, journal, payload = _completed_run(tmp_path, monkeypatch)
    provenance = json.loads(Path(payload["artifacts"]["evaluator_provenance"]["path"]).read_bytes())
    leaf = next(
        artifact for result in provenance["completed_check_results"]
        for artifact in result.get("details", {}).get("evidence_artifacts", [])
    )
    leaf_path = Path(leaf["path"]).resolve()
    assert leaf_path.is_relative_to(tmp_path.resolve())
    if damage == "missing":
        leaf_path.unlink()
    else:
        leaf_path.write_bytes(b"synthetic corrupted check evidence")
    before = journal.path.read_bytes()
    monkeypatch.setattr(runner, "_run_one_locked", _forbid_execution)
    monkeypatch.setattr(runner.EvaluationEngine, "evaluate", _forbid_execution)
    with pytest.raises(RecoveryError):
        runner.run_dev(request)
    assert journal.path.read_bytes() == before
    assert journal.terminal() is None


@pytest.mark.parametrize("field", ["summary", "message", "active_elapsed_ms", "stop_remaining"])
def test_invalid_completion_receipt_cannot_enter_execution(tmp_path, monkeypatch, field):
    request, journal, _ = _completed_run(tmp_path, monkeypatch)
    original_events = DevJournal.events

    def events(self):
        rows = original_events(self)
        for row in rows:
            if row["event_type"] == "evaluator_finished":
                row["payload"][field] = {
                    "summary": {"task_acceptance": "FAIL"}, "message": "x" * 1_001,
                    "active_elapsed_ms": -1, "stop_remaining": "false",
                }[field]
        return rows

    monkeypatch.setattr(DevJournal, "events", events)
    monkeypatch.setattr(runner, "_run_one_locked", _forbid_execution)
    before = journal.path.read_bytes()
    with pytest.raises(RecoveryError):
        runner.run_dev(request)
    assert journal.path.read_bytes() == before


def test_provider_uncertainty_precedes_completed_evaluation(tmp_path, monkeypatch):
    request, journal, _ = _completed_run(tmp_path, monkeypatch)
    journal.append("provider_call_started", {"call_id": "synthetic-unsettled-call"})
    monkeypatch.setattr(runner, "_run_one_locked", _forbid_execution)
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == DevTerminal.PROVIDER_TIMEOUT_OR_UNKNOWN
    assert result["evaluator"] is None


def test_consistent_but_wrong_summary_binding_is_rejected(tmp_path, monkeypatch):
    request, journal, payload = _completed_run(tmp_path, monkeypatch)
    original_events = DevJournal.events
    changed = dict(payload["summary"], task_acceptance="FAIL")

    def events(self):
        rows = original_events(self)
        for row in rows:
            if row["event_type"] == "evaluator_finished":
                row["payload"].update(summary=changed, summary_hash=sha256_json(changed),
                                      terminal="EVALUATOR_FAIL")
        return rows

    monkeypatch.setattr(DevJournal, "events", events)
    monkeypatch.setattr(runner, "_run_one_locked", _forbid_execution)
    before = journal.path.read_bytes()
    with pytest.raises(RecoveryError, match="artifact binding"):
        runner.run_dev(request)
    assert journal.path.read_bytes() == before
