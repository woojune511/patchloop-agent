from pathlib import Path

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
def test_mock_exposes_retired_treatment_incompatibility_without_changing_prompts(
    tmp_path, arm, monkeypatch,
):
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
    prompts = [runner._load_active_model_input(turn, store, context_policy="segmented-v1")
               [0]["content"] for turn in turns]
    if arm == "A":
        p.require_treatment_delivery(prompts, arm)
    else:
        assert any(p.TREATMENT in prompt for prompt in prompts)
        assert any(p.TREATMENT not in prompt for prompt in prompts)
        with pytest.raises(p.ContractError, match="treatment delivery incompatible"):
            p.require_treatment_delivery(prompts, arm)


@pytest.mark.parametrize("action", ["freeze", "preflight", "run"])
def test_retired_entry_points_reject_before_any_io(tmp_path, monkeypatch, action):
    root = tmp_path / "must-not-exist"

    def forbidden(*args, **kwargs):
        pytest.fail("retired panel must not access files, tasks, sandbox or provider")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(p, "request", forbidden)
    monkeypatch.setattr(p, "save", forbidden)
    monkeypatch.setattr(runner, "_resolve_task_file", forbidden)
    monkeypatch.setattr(runner, "_live_sandbox_preflight", forbidden)
    monkeypatch.setattr(runner, "_run_one", forbidden)
    with pytest.raises(p.ContractError, match="execution is retired"):
        getattr(p, action)(root, *([] if action == "freeze" else ["unused-hash"]))
    assert not root.exists()


def test_treatment_audit_preserves_all_turns_and_control_absence():
    p.require_treatment_delivery(["baseline", "compact baseline"], "A")
    p.require_treatment_delivery([p.TREATMENT, "later " + p.TREATMENT], "B")
    for prompts, arm in (([p.TREATMENT], "A"), ([p.TREATMENT, "lost"], "B")):
        with pytest.raises(p.ContractError, match="treatment delivery incompatible"):
            p.require_treatment_delivery(prompts, arm)
