from pathlib import Path
from types import SimpleNamespace

import pytest

from diagnostics import boundary_pair_panel as p
from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner, working_plan
from patchloop.dev.state import DevJournal


def test_instruction_identity_and_restore():
    original = working_plan.instructions("brief-v1")
    req = p.request("P", Path("C:/pt/not-executed"))
    a = runner._model_hash(req, None)
    with pytest.raises(RuntimeError), p.arm_instructions("B"):
        assert working_plan.instructions("brief-v1") == original + "\n\n" + p.TREATMENT
        assert runner._model_hash(req, None) != a
        raise RuntimeError("exercise restoration")
    assert working_plan.instructions("brief-v1") == original
    assert runner._model_hash(req, None) == a
    assert len(p.ORDER) == 24
    for case in p.TASKS:
        assert [(arm, n) for c, arm, n in p.ORDER if c == case] in (
            [("A", 1), ("B", 1), ("B", 2), ("A", 2)],
            [("B", 1), ("A", 1), ("A", 2), ("B", 2)],
        )


@pytest.mark.parametrize("arm", ["A", "B"])
def test_mock_to_evaluation_and_delivered_instructions(tmp_path, arm, monkeypatch):
    monkeypatch.setattr(runner.DockerProbeSandbox, "preflight",
                        lambda self, **kwargs: self.identity)
    root = tmp_path / arm
    req = p.request("P", root, mock=True)
    with p.arm_instructions(arm):
        result = runner.run_dev(req)
    run = result["runs"][0]
    assert run["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(root, run["run_id"])
    store = ArtifactStore(root / "artifacts")
    turns = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"]
    assert turns
    for turn in turns:
        items = runner._load_active_model_input(turn, store, context_policy="segmented-v1")
        assert (p.TREATMENT in items[0]["content"]) == (arm == "B")


def test_loop_uncertainty_stops_panel_and_forbids_restart(tmp_path, monkeypatch):
    root = tmp_path / "panel"
    root.mkdir()
    control = DevJournal(root, "run_dev_boundarypanel")
    control.append("preflight_passed", {"test": True})
    monkeypatch.setattr(p, "validate", lambda *args: {
        "runtime_hash": "frozen", "cases": {"P": {"model_hashes": {"A": "model"}}}})
    monkeypatch.setattr(runner, "_require_tracked_clean_paths", lambda *args: None)
    monkeypatch.setattr(runner, "_resolve_task_file", lambda *args: (None, None))
    monkeypatch.setattr(runner, "_model_hash", lambda *args: "model")
    seen = []

    def uncertain(**kwargs):
        seen.append(kwargs["request"])
        return SimpleNamespace(public={"terminal": "PROVIDER_TIMEOUT_OR_UNKNOWN"},
                               stop_remaining=True)

    monkeypatch.setattr(runner, "_run_one", uncertain)
    result = p.run(root, "frozen")
    assert len(seen) == result["completed"] == 1
    assert result["planned"] == 24 and not result["resume_allowed"]
    with pytest.raises(p.ContractError, match="no restart"):
        p.run(root, "frozen")
