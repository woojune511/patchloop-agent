from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_sandbox_capture import fake_capture

import patchloop.repository as repository
import patchloop.sandbox.runner as sandbox_module
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import ModelConfig, RegisteredCheck, RunManifest, TaskConstraints
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.repository import DiffSummary, WorkspaceManager
from patchloop.sandbox.runner import DockerSandbox, LocalSandbox, SandboxResult
from patchloop.util import sha256_bytes, utc_now
from patchloop.verifier.core import EvaluationEngine


def _git(workspace: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=workspace, check=True, capture_output=True)


def test_candidate_diff_preview_binds_other_files_without_changing_workspace(tmp_path) -> None:
    workspace = tmp_path / "run" / "repo"
    workspace.mkdir(parents=True)
    (workspace / "a.py").write_bytes(b"a = 1\n")
    (workspace / "b.py").write_bytes(b"b = 1\r\n")
    _git(workspace, "init", "-q")
    _git(workspace, "config", "core.autocrlf", "false")
    _git(workspace, "add", ".")
    _git(
        workspace, "-c", "user.email=audit@example.invalid", "-c", "user.name=Audit",
        "commit", "-qm", "base",
    )
    (workspace / "a.py").write_bytes(b"a = 2\n")
    baseline = WorkspaceManager.diff_summary(workspace)
    index_bytes = (workspace / ".git" / "index").read_bytes()
    candidate = WorkspaceManager.preview_text_replacement(
        workspace, "b.py", b"b = 2\r\n", baseline_diff_hash=baseline.patch_hash,
    )
    assert (workspace / ".git" / "index").read_bytes() == index_bytes
    assert (workspace / "b.py").read_bytes() == b"b = 1\r\n"
    assert WorkspaceManager.diff_summary(workspace).patch_hash == baseline.patch_hash
    WorkspaceManager.atomic_replace_source(workspace, "b.py", b"b = 2\r\n")
    assert WorkspaceManager.diff_summary(workspace).patch_hash == candidate.patch_hash
    (workspace / "a.py").write_bytes(b"a = 3\n")
    assert WorkspaceManager.diff_summary(workspace).patch_hash != candidate.patch_hash
    assert candidate.changed_files == ["a.py", "b.py"]


def test_atomic_source_replacement_keeps_preimage_if_replace_fails(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "run" / "repo"
    workspace.mkdir(parents=True)
    target = workspace / "source.py"
    target.write_bytes(b"before\n")

    def interrupted_replace(source, destination):
        assert Path(source).parent == workspace.parent
        assert Path(destination) == target
        raise OSError("injected replacement interruption")

    monkeypatch.setattr(repository.os, "replace", interrupted_replace)
    with pytest.raises(OSError, match="injected"):
        WorkspaceManager.atomic_replace_source(workspace, "source.py", b"after\n")
    assert target.read_bytes() == b"before\n"
    assert list(workspace.parent.iterdir()) == [workspace]


def test_local_check_clips_timeout_to_active_deadline(tmp_path, monkeypatch) -> None:
    clock = [0.0]
    deadline = ExecutionDeadline.from_remaining(0.1, clock=lambda: clock[0])

    def timed_out(command, **kwargs):
        assert kwargs["timeout"] == pytest.approx(0.05)
        clock[0] = 0.05
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"partial")

    monkeypatch.setattr(sandbox_module, "capture_process", fake_capture(timed_out))
    result = LocalSandbox().run_check(
        tmp_path, RegisteredCheck(id="public-check", command=["python", "-V"], timeout_seconds=30),
        deadline=deadline,
    )
    assert result.timed_out and result.deadline_exhausted
    assert result.stdout == "partial"


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_docker_deadline_cleans_only_owned_container(tmp_path, monkeypatch, cleanup_fails) -> None:
    clock = [0.0]
    deadline = ExecutionDeadline.from_remaining(20, clock=lambda: clock[0])
    commands: list[list[str]] = []
    running = False

    def execute(command, **kwargs):
        nonlocal running
        commands.append(command)
        if command[1] == "container":
            if not running:
                return subprocess.CompletedProcess(
                    command, 1, b"", b"No such container: " + command[-1].encode(),
                )
            return subprocess.CompletedProcess(command, 0, command[-1].encode(), b"")
        if command[1] == "rm":
            if running and cleanup_fails:
                return subprocess.CompletedProcess(command, 1, b"", b"daemon unavailable")
            return subprocess.CompletedProcess(command, 0, b"", b"")
        assert command[1] == "run"
        assert kwargs["timeout"] == 15
        assert command[command.index("--name") + 1] == commands[0][-1]
        assert "never" in command and "--rm" in command
        running = True
        clock[0] = 15
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"public partial")

    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: "fake-docker"))
    monkeypatch.setattr(sandbox_module.subprocess, "run", execute)
    monkeypatch.setattr(sandbox_module, "capture_process", fake_capture(execute))
    result = DockerSandbox("test@sha256:" + "a" * 64).run_check(
        tmp_path, RegisteredCheck(id="public-check", command=["python", "-V"], timeout_seconds=30),
        deadline=deadline, execution_identity={"run_id": "run_dev_test", "action_id": "check1"},
    )
    assert len(commands) == 4
    assert commands[-1] == ["fake-docker", "rm", "--force", commands[0][-1]]
    assert result.deadline_exhausted
    assert result.cleanup_failed is cleanup_fails
    assert result.execution_policy["requested_timeout_seconds"] == 30
    assert result.execution_policy["effective_timeout_seconds"] == 15
    assert result.execution_policy["cleanup_status"] == ("failed" if cleanup_fails else "confirmed")


def test_docker_cleanup_does_not_remove_container_with_another_owner(tmp_path, monkeypatch) -> None:
    commands = []

    def inspect_other_owner(command, **kwargs):
        commands.append(command)
        assert command[1] == "container"
        return subprocess.CompletedProcess(command, 0, b"another-owner", b"")

    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: "fake-docker"))
    monkeypatch.setattr(sandbox_module.subprocess, "run", inspect_other_owner)
    result = DockerSandbox("test@sha256:" + "a" * 64).run_check(
        tmp_path, RegisteredCheck(id="public-check", command=["python", "-V"]),
        execution_identity={"run_id": "run_dev_test", "action_id": "check1"},
    )
    assert len(commands) == 1
    assert result.cleanup_failed and not result.passed


def test_docker_does_not_start_when_cleanup_reserve_cannot_fit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(DockerSandbox, "cli_path", staticmethod(lambda: "fake-docker"))

    def forbidden(*args, **kwargs):
        raise AssertionError("expired execution must not launch Docker")

    monkeypatch.setattr(sandbox_module.subprocess, "run", forbidden)
    with pytest.raises(ExecutionDeadlineExceeded):
        DockerSandbox("test@sha256:" + "a" * 64).run_check(
            tmp_path, RegisteredCheck(id="public-check", command=["python", "-V"]),
            deadline=ExecutionDeadline.from_remaining(4),
        )


def test_evaluator_deadline_preserves_completed_check_artifact(tmp_path) -> None:
    class ExpiringSandbox:
        calls = 0

        def run_check(self, workspace, check):
            self.calls += 1
            return SandboxResult(
                command=check.command, exit_code=None, stdout="public partial", stderr="",
                duration_ms=1, timed_out=True, truncated=False, original_output_bytes=14,
                deadline_exhausted=True,
            )

    sandbox = ExpiringSandbox()
    store = ArtifactStore(tmp_path / "artifacts")
    engine = EvaluationEngine(None, sandbox, store)
    results, recorded = [], []
    checks = [RegisteredCheck(id=f"public-check-{i}", command=["python", "-V"]) for i in range(2)]
    with pytest.raises(ExecutionDeadlineExceeded):
        engine._run_checks("run_dev_test", tmp_path, checks, "regression", results, recorded)
    assert sandbox.calls == 1
    assert len(results) == len(recorded) == 1
    assert results[0].state.value == "error"
    evidence = json.loads(store.read_bytes(recorded[0].artifact))
    assert evidence["deadline_exhausted"] is True
    assert evidence["stdout"] == "public partial"


def test_evaluator_deadline_keeps_failure_provenance(tmp_path, monkeypatch) -> None:
    patch_text = "audit patch\n"
    digest = sha256_bytes(patch_text.encode())
    store = ArtifactStore(tmp_path / "artifacts")
    artifact = store.put_text(patch_text)
    manifest = RunManifest(
        run_id="run_dev_deadline", task_id="audit-task", task_version=1, base_commit="a" * 40,
        public_spec_hash=digest, private_spec_hash=digest, task_content_hash=digest,
        runtime_content_hash=digest, model_hash=digest, tool_surface_hash=digest,
        sandbox_identity_hash=digest, submitted_patch_content_hash=digest,
        visible_check_diff_hash=digest, submitted_changed_files=["a.py"],
        model=ModelConfig(provider="mock", model_id="mock"), created_at=utc_now(),
    )
    check = RegisteredCheck(id="public-check", command=["python", "-V"])
    package = SimpleNamespace(
        root=tmp_path / "task",
        public=SimpleNamespace(
            repository=SimpleNamespace(url="snapshot://audit", base_commit="a" * 40),
            visible_checks=[check], constraints=TaskConstraints(),
        ),
        private=SimpleNamespace(hidden_checks=[]),
    )
    manager = SimpleNamespace(
        create=lambda *args, **kwargs: tmp_path,
        validate_managed_workspace=lambda workspace, **kwargs: workspace,
        apply_patch=lambda *args, **kwargs: digest,
        diff_summary=lambda workspace, **kwargs: DiffSummary(["a.py"], 1, 1, patch_text, []),
    )

    class ExpiringSandbox:
        backend = "local"

        def run_check(self, workspace, registered):
            return SandboxResult(
                command=registered.command, exit_code=None, stdout="partial", stderr="",
                duration_ms=1, timed_out=True, truncated=False, original_output_bytes=7,
                deadline_exhausted=True,
            )

    engine = EvaluationEngine(manager, ExpiringSandbox(), store)
    monkeypatch.setattr(engine, "_validate_manifest_inputs", lambda *args: (package, b"patch"))
    with pytest.raises(ExecutionDeadlineExceeded):
        engine.evaluate(tmp_path, artifact.path, manifest, submitted_patch_artifact=artifact)
    provenance = json.loads(
        (store.root / "runs" / manifest.run_id / "provenance.json").read_text()
    )
    assert provenance["deadline_exhausted"] is True
    assert provenance["submitted_patch_content_hash"] == digest
    assert len(provenance["completed_check_results"]) == 1
    assert provenance["completed_check_results"][0]["state"] == "error"


@pytest.mark.parametrize("expires_after", ["manifest_validation", "workspace_validation"])
def test_evaluator_starts_no_workspace_or_patch_after_deadline(
    tmp_path, monkeypatch, expires_after,
) -> None:
    digest = sha256_bytes(b"audit")
    manifest = RunManifest(
        run_id="run_dev_deadline_boundary", task_id="audit-task", task_version=1,
        base_commit="a" * 40, public_spec_hash=digest, private_spec_hash=digest,
        task_content_hash=digest, runtime_content_hash=digest, model_hash=digest,
        tool_surface_hash=digest, sandbox_identity_hash=digest,
        submitted_patch_content_hash=digest, visible_check_diff_hash=digest,
        submitted_changed_files=["a.py"], model=ModelConfig(provider="mock", model_id="mock"),
        created_at=utc_now(),
    )
    clock = [0.0]
    created = []
    package = SimpleNamespace(public=SimpleNamespace(
        repository=SimpleNamespace(url="snapshot://audit", base_commit="a" * 40),
    ))

    def validate_manifest(*args):
        if expires_after == "manifest_validation":
            clock[0] = 1
        return package, b"audit"

    def create(*args, **kwargs):
        assert clock[0] < 1
        created.append(True)
        return tmp_path

    def validate_workspace(workspace, **kwargs):
        clock[0] = 1
        return workspace

    def forbidden_patch(*args, **kwargs):
        raise AssertionError("evaluator applied a patch after the active deadline")

    manager = SimpleNamespace(
        create=create, validate_managed_workspace=validate_workspace, apply_patch=forbidden_patch,
    )
    store = ArtifactStore(tmp_path / "artifacts")
    engine = EvaluationEngine(manager, LocalSandbox(), store)
    monkeypatch.setattr(engine, "_validate_manifest_inputs", validate_manifest)
    with pytest.raises(ExecutionDeadlineExceeded):
        engine.evaluate(
            tmp_path, tmp_path / "unused.patch", manifest,
            deadline=ExecutionDeadline.from_remaining(1, clock=lambda: clock[0]),
        )
    assert len(created) == int(expires_after == "workspace_validation")
    provenance = json.loads(
        (store.root / "runs" / manifest.run_id / "provenance.json").read_text()
    )
    assert provenance["deadline_exhausted"] is True
    assert provenance["applied_patch_hash"] is None
