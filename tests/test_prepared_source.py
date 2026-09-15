"""Prepared source identity, offline clone isolation and run recovery boundaries."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

import patchloop.prepared_source as prepared
import patchloop.repository as repository
from patchloop.artifacts import ArtifactStore
from patchloop.cli import app
from patchloop.contracts import Artifact
from patchloop.deadline import ExecutionDeadline, ExecutionDeadlineExceeded
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunEnvelope, DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, ResumeContractMismatch
from patchloop.git_execution import GitExecutionUncertain, run_git
from patchloop.repository import WorkspaceManager
from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, directory_hash, sha256_bytes

REMOTE = "https://github.com/pytest-dev/pyfakefs.git"
TASK = repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml"


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("prepared source tests must not call a provider")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


def forbid_fetch(monkeypatch):
    def guarded(repo, *args, **kwargs):
        assert not {"fetch", "pull", "ls-remote"}.intersection(args), args
        return run_git(repo, *args, **kwargs)
    monkeypatch.setattr(repository, "_git", guarded)
    monkeypatch.setattr(prepared, "run_git", guarded)


@pytest.fixture
def remote_source(tmp_path, monkeypatch):
    origin = tmp_path / "origin"
    origin.mkdir()
    (origin / "example.py").write_bytes(b"value = 1\n")
    run_git(origin, "init", "-q")
    run_git(origin, "add", ".")
    run_git(origin, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "base")
    commit = run_git(origin, "rev-parse", "HEAD").stdout.strip()
    fetches = []

    def local_fetch(repo, *args, **kwargs):
        if args and args[0] == "fetch":
            fetches.append(args)
            args = tuple(str(origin) if a == "origin" else a for a in args)
        return run_git(repo, *args, **kwargs)
    monkeypatch.setattr(repository, "_git", local_fetch)
    manifest = prepared.prepare_source(
        repository_url=REMOTE, base_commit=commit, output=tmp_path / "prepared",
        fixture_root=tmp_path / "fixtures",
    )
    assert len(fetches) == 1
    forbid_fetch(monkeypatch)
    return manifest, commit


def manager(tmp_path, manifest):
    return WorkspaceManager(
        tmp_path / "absent-fixtures", tmp_path / "workspaces", prepared_source=manifest,
        prepared_source_hash=prepared.admission_hash(manifest),
    )


def test_remote_shallow_source_clones_offline_without_shared_objects(remote_source, tmp_path):
    manifest, commit = remote_source
    source_repo = manifest.parent / prepared.REPO_PATH
    assert (source_repo / ".git/shallow").is_file()
    source_hash = directory_hash(source_repo)
    selected = manager(tmp_path, manifest)
    first = selected.create("run_dev_one", REMOTE, commit)
    second = selected.create("eval_two", REMOTE, commit)
    assert directory_hash(first) == directory_hash(second) == source_hash
    original_objects = [p for p in (source_repo / ".git/objects").rglob("*") if p.is_file()]
    cloned_objects = [p for p in (first / ".git/objects").rglob("*") if p.is_file()]
    assert original_objects and cloned_objects
    assert all(not os.path.samefile(a, b) for a in original_objects for b in cloned_objects)
    assert not (first / ".git/objects/info/alternates").exists()
    (first / "example.py").write_bytes(b"value = 2\n")
    assert directory_hash(source_repo) == directory_hash(second) == source_hash
    assert directory_hash(first) != source_hash
    selected.validate_pristine(second, REMOTE, commit)


@pytest.mark.parametrize("damage", ["content", "untracked", "ignored", "manifest", "missing",
                                   "commit", "tree", "url", "alternates", "promisor"])
def test_damaged_source_fails_without_remote_fallback(remote_source, tmp_path, damage):
    manifest, commit = remote_source
    selected = manager(tmp_path, manifest)
    source_repo = manifest.parent / prepared.REPO_PATH
    if damage == "content":
        (source_repo / "example.py").write_text("changed", encoding="utf-8")
    elif damage in {"untracked", "ignored"}:
        if damage == "ignored":
            (source_repo / ".git/info/exclude").write_text("extra\n", encoding="utf-8")
        (source_repo / "extra").write_text("not in task", encoding="utf-8")
    elif damage == "manifest":
        manifest.write_bytes(b"{}")
    elif damage == "missing":
        manifest.unlink()
    elif damage == "alternates":
        dest = source_repo / ".git/objects/info/alternates"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text("outside", encoding="utf-8")
    elif damage == "promisor":
        dest = source_repo / ".git/objects/pack/test.promisor"
        dest.parent.mkdir(exist_ok=True)
        dest.write_bytes(b"")
    else:
        data = json.loads(manifest.read_bytes())
        data[{"commit": "git_commit", "tree": "git_tree", "url": "repository_url"}[damage]] = (
            "https://example.invalid/repo" if damage == "url" else "0" * 40
        )
        manifest.write_text(canonical_json(data), encoding="utf-8")
        selected.prepared_source_hash = prepared.admission_hash(manifest)
    with pytest.raises(ContractError):
        selected.create("run_dev_invalid", REMOTE, commit)
    assert not (tmp_path / "workspaces/run_dev_invalid/repo").exists()


def test_source_task_binding_and_new_output_are_required(remote_source, tmp_path):
    manifest, commit = remote_source
    with pytest.raises(ContractError, match="task repository"):
        manager(tmp_path, manifest).create("wrong", REMOTE, "0" * 40)
    with pytest.raises(ContractError, match="new external"):
        prepared.prepare_source(repository_url=REMOTE, base_commit=commit,
                                output=manifest.parent, fixture_root=tmp_path)


@pytest.mark.parametrize("failure", ["fetch", "deadline", "uncertain"])
def test_failed_preparation_never_publishes_manifest(tmp_path, monkeypatch, failure):
    def fail(*args, **kwargs):
        if failure == "deadline":
            raise ExecutionDeadlineExceeded("test")
        if failure == "uncertain":
            raise GitExecutionUncertain("test")
        raise ContractError("unavailable exact SHA")
    monkeypatch.setattr(WorkspaceManager, "create", fail)
    output = tmp_path / "incomplete"
    with pytest.raises((ContractError, ExecutionDeadlineExceeded, GitExecutionUncertain)):
        prepared.prepare_source(repository_url=REMOTE, base_commit="0" * 40,
                                output=output, fixture_root=tmp_path)
    assert not (output / prepared.MANIFEST_NAME).exists()


@pytest.mark.parametrize("raw", [None, b"{", b"{}", b"x" * (prepared.MAX_MANIFEST_BYTES + 1)])
def test_invalid_manifest_never_reaches_model(tmp_path, monkeypatch, raw):
    manifest = tmp_path / prepared.MANIFEST_NAME
    if raw is not None:
        manifest.write_bytes(raw)
    def fail(*args, **kwargs):
        pytest.fail("model must not run")
    monkeypatch.setattr(MockDevAdapter, "next_turn", fail)
    result = runner.run_dev(DevRunRequest(
        provider="mock", task=TASK, model="mock-dev", state_root=tmp_path / "state",
        prepared_source=manifest,
    ))["runs"][0]
    assert result["terminal"] == "PREFLIGHT_FAILED"
    assert result["call_counts"] == {"model": 0, "input_count": 0, "tool": 0}


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_cli_prepared_smoke_uses_source_for_runner_and_evaluator(tmp_path, monkeypatch, policy):
    result = CliRunner().invoke(app, ["task", "prepare-source", str(TASK.parent),
                                    "--output", str(tmp_path / "prepared")])
    assert result.exit_code == 0, result.output
    manifest = Path(json.loads(result.output)["prepared_source"])
    forbid_fetch(monkeypatch)
    creates = []
    create = WorkspaceManager.create
    def track(self, run_id, *args, **kwargs):
        assert self.prepared_source == manifest
        creates.append(run_id)
        return create(self, run_id, *args, **kwargs)
    monkeypatch.setattr(WorkspaceManager, "create", track)
    inputs = []
    next_turn = MockDevAdapter.next_turn
    def capture(self, context, tools):
        inputs.append(json.loads(context))
        return next_turn(self, context, tools)
    monkeypatch.setattr(MockDevAdapter, "next_turn", capture)
    request = DevRunRequest(provider="mock", task=TASK, model="mock-dev",
                            state_root=tmp_path / "state", prepared_source=manifest,
                            planning_policy="brief-v1", context_policy=policy)
    output = runner.run_dev(request)["runs"][0]
    assert output["terminal"] == "EVALUATOR_PASS", output
    assert output["call_counts"] == {"model": 4, "input_count": 0, "tool": 5}
    assert len(creates) == 2 and creates[1].startswith("eval_")
    public = load_task_package(TASK.parent).public.model_dump(mode="json")
    for value in inputs:
        assert value["public_task"] == public
        assert "prepared_source" not in canonical_json(value)
        assert prepared.admission_hash(manifest) not in canonical_json(value)
    journal = DevJournal(request.state_root, output["run_id"])
    store = ArtifactStore(request.state_root / "artifacts")
    turns = [e["payload"] for e in journal.events() if e["event_type"] == "turn_started"]
    assert len(turns) == 4
    for turn in turns:
        native = runner._load_active_model_input(turn, store, context_policy=policy)
        state = reconstruct_state(native, context_policy=policy)
        canonical = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
        assert state["public_task"] == public
        assert state["current_diff"] == canonical["current_diff"]
        assert state["visible_check_status"] == canonical["visible_check_status"]
        assert "prepared_source" not in canonical_json(native)
    envelope = journal.load_envelope()
    assert envelope.prepared_source_hash == sha256_bytes(manifest.read_bytes())
    assert sum(e["event_type"] == "prepared_source_bound" for e in journal.events()) == 1
    saved = journal.path.read_bytes()
    manifest.unlink()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": output["run_id"]}))[
        "runs"][0] == output
    assert journal.path.read_bytes() == saved
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={"resume_run_id": output["run_id"],
                                                 "prepared_source": tmp_path / "other.json"}))
    # Older envelopes without these optional fields still decode with their old meaning.
    old = envelope.model_dump(mode="json")
    old.pop("prepared_source_path")
    old.pop("prepared_source_hash")
    assert DevRunEnvelope.model_validate(old).prepared_source_path is None


def test_source_validation_obeys_active_deadline(remote_source, tmp_path):
    manifest, commit = remote_source
    with pytest.raises(ExecutionDeadlineExceeded):
        manager(tmp_path, manifest).create("expired", REMOTE, commit,
                                           deadline=ExecutionDeadline.from_remaining(0))


@pytest.mark.parametrize("damage", ["manifest", "checkout"])
def test_active_resume_rejects_changed_source_before_another_action(tmp_path, monkeypatch, damage):
    package = load_task_package(TASK.parent)
    manifest = prepared.prepare_source(
        repository_url=package.public.repository.url,
        base_commit=package.public.repository.base_commit, output=tmp_path / "prepared",
        fixture_root=repository_root() / "fixtures/repositories",
    )
    request = DevRunRequest(provider="mock", task=TASK, model="mock-dev",
                            state_root=tmp_path / "state", prepared_source=manifest)
    append = DevJournal.append
    class Interrupted(BaseException):
        pass
    def crash(self, kind, payload=None):
        result = append(self, kind, payload)
        if kind == "action_started":
            raise Interrupted()
        return result
    monkeypatch.setattr(DevJournal, "append", crash)
    with pytest.raises(Interrupted):
        runner.run_dev(request)
    monkeypatch.setattr(DevJournal, "append", append)
    journal_path = next((request.state_root / "runs").glob("*.jsonl"))
    before = journal_path.read_bytes()
    if damage == "manifest":
        manifest.write_bytes(manifest.read_bytes() + b"\n")
    else:
        (manifest.parent / prepared.REPO_PATH / "README.md").write_text("changed", encoding="utf-8")
    forbid_fetch(monkeypatch)
    with pytest.raises(ContractError):
        runner.run_dev(request.model_copy(update={"resume_run_id": journal_path.stem}))
    assert journal_path.read_bytes() == before


def test_cli_forwards_prepared_source_and_refuses_repository_output(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "run_dev", lambda request: calls.append(request) or {})
    path = tmp_path / "prepared-source.json"
    result = CliRunner().invoke(app, ["dev", "--provider", "mock", "--task", str(TASK),
                                    "--model", "mock-dev", "--prepared-source", str(path)])
    assert result.exit_code == 0, result.output
    assert calls[0].prepared_source == path
    result = CliRunner().invoke(app, ["task", "prepare-source", str(TASK.parent),
                                    "--output", str(repository_root() / ".must-not-create")])
    assert result.exit_code == 1 and "outside" in result.output
    assert not (repository_root() / ".must-not-create").exists()


def test_snapshot_drift_during_preparation_is_not_published(tmp_path, monkeypatch):
    package = load_task_package(TASK.parent)
    original = WorkspaceManager.create
    def drift(self, *args, **kwargs):
        repo = original(self, *args, **kwargs)
        (repo / "README.md").write_text("concurrent change", encoding="utf-8")
        return repo
    monkeypatch.setattr(WorkspaceManager, "create", drift)
    output = tmp_path / "prepared"
    with pytest.raises(ContractError, match="changed during"):
        prepared.prepare_source(
            repository_url=package.public.repository.url,
            base_commit=package.public.repository.base_commit, output=output,
            fixture_root=repository_root() / "fixtures/repositories",
        )
    assert not (output / prepared.MANIFEST_NAME).exists()
