"""Only a bound evaluator deadline may bypass a batch-wide disagreement stop."""

from types import SimpleNamespace

import pytest

from diagnostics import current_dev20 as panel


def evidence(tmp_path, monkeypatch):
    run = {
        "run_id": "run_dev_deadline", "terminal": "LIMIT_REACHED",
        "evaluator": {"failure_class": "ACTIVE_DEADLINE_EXHAUSTED"},
        "artifact_hashes": {"submitted_patch": "sha256:bound"},
    }
    completion = SimpleNamespace(
        terminal="LIMIT_REACHED", stop_remaining=False,
        summary=SimpleNamespace(task_acceptance="ERROR", failure_class="ACTIVE_DEADLINE_EXHAUSTED"),
        artifact_hashes=dict(run["artifact_hashes"]),
    )
    monkeypatch.setattr(panel.DevJournal, "load_envelope", lambda _: "bound-envelope")
    monkeypatch.setattr(panel, "load_evaluation_completion", lambda *args: completion)
    native = {"status": "FAIL", "cleanup_confirmed": True, "error_type": None}
    return SimpleNamespace(state_root=tmp_path), run, native, completion


def test_known_deadline_is_local_without_changing_error_or_native_verdict(tmp_path, monkeypatch):
    req, run, native, _ = evidence(tmp_path, monkeypatch)
    assert panel.known_evaluation_deadline(req, run, native)
    assert run["terminal"] == "LIMIT_REACHED"
    assert native["status"] == "FAIL"


@pytest.mark.parametrize("corruption", [
    "cleanup", "native_error", "native_incomplete", "not_deadline", "stop_required",
    "patch_binding", "missing_completion", "registered_not_error",
])
def test_unconfirmed_or_different_failure_is_not_treated_as_local_limit(
    tmp_path, monkeypatch, corruption,
):
    req, run, native, completion = evidence(tmp_path, monkeypatch)
    if corruption == "cleanup":
        native["cleanup_confirmed"] = False
    elif corruption == "native_error":
        native["error_type"] = "TimeoutExpired"
    elif corruption == "native_incomplete":
        native["status"] = "ERROR"
    elif corruption == "not_deadline":
        run["evaluator"]["failure_class"] = "EVALUATOR_INFRA_FAILURE"
    elif corruption == "stop_required":
        completion.stop_remaining = True
    elif corruption == "patch_binding":
        completion.artifact_hashes = {"submitted_patch": "sha256:different"}
    elif corruption == "missing_completion":
        monkeypatch.setattr(panel, "load_evaluation_completion", lambda *args: None)
    elif corruption == "registered_not_error":
        completion.summary.task_acceptance = "FAIL"
    assert not panel.known_evaluation_deadline(req, run, native)
