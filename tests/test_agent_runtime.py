from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from patchloop.agent.runner import AgentRunner
from patchloop.contracts import EventType, FaultSpec
from patchloop.errors import ContractError, RecoveryError
from patchloop.runtime import build_manifest
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes, utc_now

TASK = "tasks/smoke/csv-quoted-newline/public.yaml"
SMOKE_TASKS = {
    "csv-quoted-newline": TASK,
    "config-falsy-override": "tasks/smoke/config-falsy-override/public.yaml",
    "path-prefix-boundary": "tasks/smoke/path-prefix-boundary/public.yaml",
}
SMOKE_REPLAYS = {
    task_id: f"replays/smoke/{task_id}.jsonl" for task_id in SMOKE_TASKS
}


def _assert_public_trace_boundary(runner: AgentRunner, run_id: str, task_path: str) -> None:
    package = load_task_package(Path(task_path).parent)
    hidden_check_ids = {check.id for check in package.private.hidden_checks}
    contexts: list[str] = []
    for event in runner.state.list_events(run_id):
        if event.type != EventType.CONTEXT_BUILT:
            continue
        context = Path(event.payload["artifact_path"]).read_text(encoding="utf-8")
        contexts.append(context)
        assert "reference.patch" not in context
        assert all(check_id not in context for check_id in hidden_check_ids)
    assert contexts
    assert package.private.reference_patch.sha256 not in contexts[0]


@pytest.mark.parametrize(("task_id", "task_path"), SMOKE_TASKS.items())
def test_offline_mock_agent_creates_complete_trace(
    tmp_path, monkeypatch, task_id: str, task_path: str
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_path, model="mock")
    events = runner.state.list_events(result["run_id"])
    assert result["scope_compliant_success"] is True
    assert result["official"] is False
    assert runner.state.get_manifest(result["run_id"]).task_id == task_id
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 5
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 4
    assert any(event.type == EventType.PATCH_APPLIED for event in events)
    assert any(event.type == EventType.RUN_COMPLETED for event in events)
    workspace = tmp_path / "runtime" / "workspaces" / result["run_id"] / "repo"
    assert not (workspace / ".patchloop-hidden").exists()
    _assert_public_trace_boundary(runner, result["run_id"], task_path)


@pytest.mark.parametrize(
    ("task_id", "task_path", "replay_path"),
    [
        (task_id, task_path, SMOKE_REPLAYS[task_id])
        for task_id, task_path in SMOKE_TASKS.items()
    ],
)
def test_offline_replay_agent_creates_hashed_complete_trace(
    tmp_path,
    monkeypatch,
    task_id: str,
    task_path: str,
    replay_path: str,
) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    result = runner.start(task_path, model=f"replay:{replay_path}")
    manifest = runner.state.get_manifest(result["run_id"])
    events = runner.state.list_events(result["run_id"])

    assert result["scope_compliant_success"] is True
    assert result["official"] is False
    assert manifest.task_id == task_id
    assert manifest.model.provider == "replay"
    assert manifest.model.model_id == f"replay:{replay_path}"
    assert manifest.model.replay_hash == sha256_bytes(Path(replay_path).read_bytes())
    assert sum(event.type == EventType.MODEL_CALLED for event in events) == 5
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 4
    _assert_public_trace_boundary(runner, result["run_id"], task_path)


def test_replay_path_must_be_repository_relative(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    runner = AgentRunner(tmp_path / "runtime")
    with pytest.raises(ContractError, match="safe relative path"):
        runner.start(TASK, model="replay:../outside.jsonl")


def test_worker_restart_resumes_without_duplicate_patch(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_recovery_test",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(TASK, model="mock", manifest=manifest)
    assert suspended["status"] == "suspended"
    resumed = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    assert resumed["scope_compliant_success"] is True
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_replay_worker_restart_preserves_source_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    replay_path = SMOKE_REPLAYS["config-falsy-override"]
    replay_hash = sha256_bytes(Path(replay_path).read_bytes())
    package = load_task_package("tasks/smoke/config-falsy-override")
    manifest = build_manifest(
        package,
        run_id="run_replay_recovery",
        provider="replay",
        model_id=f"replay:{replay_path}",
        replay_hash=replay_hash,
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    suspended = runner.start(
        SMOKE_TASKS["config-falsy-override"],
        model=f"replay:{replay_path}",
        manifest=manifest,
    )
    assert suspended["status"] == "suspended"

    resumed = runner.resume(manifest.run_id)
    events = runner.state.list_events(manifest.run_id)
    assert resumed["scope_compliant_success"] is True
    assert runner.state.get_manifest(manifest.run_id).model.replay_hash == replay_hash
    assert sum(event.type == EventType.PATCH_APPLIED for event in events) == 1


def test_resume_rejects_checkpoint_worktree_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_corrupt_checkpoint",
        sandbox_backend="local",
        fault=FaultSpec(type="worker-kill-after-patch"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    runner.start(TASK, model="mock", manifest=manifest)
    checkpoint = runner.state.latest_checkpoint(manifest.run_id)
    assert checkpoint is not None
    corrupt = checkpoint.model_copy(
        update={
            "checkpoint_id": f"ckpt_{uuid.uuid4().hex}",
            "through_sequence": runner.state.last_sequence(manifest.run_id),
            "worktree_diff_hash": "sha256:corrupt",
            "created_at": utc_now(),
        }
    )
    runner.state.save_checkpoint(corrupt)
    with pytest.raises(RecoveryError, match="diff hash"):
        runner.resume(manifest.run_id)


def test_timeout_fault_is_recorded_without_repeating_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("patchloop.agent.runner.DockerSandbox.available", lambda: False)
    package = load_task_package("tasks/smoke/csv-quoted-newline")
    manifest = build_manifest(
        package,
        run_id="run_timeout_fault",
        sandbox_backend="local",
        fault=FaultSpec(type="test-timeout"),
    )
    runner = AgentRunner(tmp_path / "runtime")
    with pytest.raises(ContractError, match="visible check"):
        runner.start(TASK, model="mock", manifest=manifest)
    events = runner.state.list_events(manifest.run_id)
    timed_out_checks = [
        event
        for event in events
        if event.type == EventType.TOOL_SUCCEEDED
        and event.payload.get("tool") == "run_check"
        and event.payload.get("timed_out") is True
    ]
    assert len(timed_out_checks) == 1
    assert sum(event.type == EventType.TOOL_CALLED for event in events) == 4
    assert events[-1].type == EventType.RUN_FAILED
