"""Public wheel preparation, offline snapshots and run/evaluation binding."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError
from test_dev_probe_sandbox import FakeProcess, mock_launch, public_repo  # noqa: F401
from test_dev_probes import FakeProbe, probe_call
from test_probe_provenance import _prepared

import patchloop.prepared_probe_dependencies as prepared
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact, VerdictState
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError, ResumeContractMismatch
from patchloop.runtime import repository_root
from patchloop.sandbox import probes
from patchloop.util import canonical_json, sha256_bytes, sha256_json

WHEEL = {"url": "https://files.pythonhosted.org/packages/aa/fixture-1.0-py3-none-any.whl",
         "hash": sha256_bytes(b"wheel"), "size": 5}


def write_bundle(root, public, *, roots=()):
    target = root / "site-packages"
    target.mkdir(parents=True)
    (target / "public_dependency.py").write_bytes(b"VALUE = 42\n")
    files = prepared._inventory(target)
    path = root / prepared.MANIFEST
    path.write_text(canonical_json({
        "schema_version": "prepared-probe-dependencies-v1", "image": probes.PROBE_IMAGE,
        "python": "3.12", "platform": "linux/amd64", "source_roots": list(roots),
        "repository_url": public.repository.url, "base_commit": public.repository.base_commit,
        "content_hash": sha256_json(files), "files": files,
    }), encoding="utf-8")
    return path


@pytest.fixture
def bundle(tmp_path, smoke_package):
    return write_bundle(tmp_path / "prepared", smoke_package.public)


@pytest.fixture
def prepare_fixture(tmp_path, monkeypatch, smoke_package):
    repo = tmp_path / "source"
    repo.mkdir()
    (repo / "src").mkdir()
    lock_bytes = ("[[package]]\nname = 'fixture'\nversion = '1.0'\n"
                  "source = {registry = 'https://pypi.org/simple'}\n"
                  f"wheels = [{{url = '{WHEEL['url']}', hash = '{WHEEL['hash']}', size = 5}}]\n"
                  ).encode()
    (repo / "uv.lock").write_bytes(lock_bytes)
    selected = tmp_path / "selected.json"
    selected.write_text(canonical_json({
        "source_lock": "uv.lock", "source_lock_hash": sha256_bytes(lock_bytes),
        "source_roots": ["src"], "wheels": [WHEEL],
    }))
    monkeypatch.setattr(prepared, "load_source", lambda *a, **kw:
                        (SimpleNamespace(content_hash=sha256_json("public source"),
                                         git_commit="a" * 40), repo))
    monkeypatch.setattr(prepared.shutil, "which", lambda _: sys.executable)
    monkeypatch.setattr(prepared, "_download", lambda wheel, target: target.write_bytes(b"wheel"))

    def install(command, **kwargs):
        for flag in ("--offline", "--no-index", "--no-build", "--no-config", "--no-cache",
                     "--no-python-downloads"):
            assert flag in command
        assert command[command.index("--python-platform") + 1] == "x86_64-manylinux_2_28"
        assert "SECRET_API_KEY" not in kwargs["env"]
        target = Path(command[command.index("--target") + 1])
        target.mkdir()
        (target / "public_dependency.py").write_bytes(b"VALUE = 42\n")
        metadata = target / "fixture-1.0.dist-info"
        metadata.mkdir()
        (metadata / "direct_url.json").write_text(json.dumps({"url": Path(command[-1]).as_uri()}))
        return subprocess.CompletedProcess(command, 0, b"", b"installed")

    monkeypatch.setattr(prepared.subprocess, "run", install)
    monkeypatch.setenv("SECRET_API_KEY", "not passed")
    return {"public": smoke_package.public, "prepared_source": tmp_path / "source.json",
            "wheel_lock": selected, "output": tmp_path / "output"}


def test_prepare_publishes_last_and_never_overwrites(prepare_fixture):
    path = prepared.prepare_dependencies(**prepare_fixture)
    dependency = prepared.load_dependencies(path, prepare_fixture["public"], prepared.admit(path))
    dependency.verify()
    origin = json.loads((path.parent / "site-packages/fixture-1.0.dist-info/direct_url.json")
                        .read_bytes())
    assert origin["url"] == WHEEL["url"] and "file:" not in canonical_json(origin)
    events = DevJournal(path.parent, "run_dev_preparedependencies").events()
    assert events[-1]["payload"]["manifest_hash"] == sha256_bytes(path.read_bytes())
    before = path.read_bytes()
    with pytest.raises(ContractError, match="already exists"):
        prepared.prepare_dependencies(**prepare_fixture)
    assert path.read_bytes() == before


@pytest.mark.parametrize("fault", ["download", "install", "lock", "unpinned", "missing_root"])
def test_interrupted_or_invalid_preparation_has_no_descriptor(prepare_fixture, monkeypatch, fault):
    if fault == "download":
        def fail(*args):
            raise OSError("interrupted transfer")
        monkeypatch.setattr(prepared, "_download", fail)
    elif fault == "install":
        monkeypatch.setattr(prepared.subprocess, "run", lambda *a, **kw:
                            subprocess.CompletedProcess([], 1, b"", b"not installed"))
    else:
        path = prepare_fixture["wheel_lock"]
        lock = json.loads(path.read_bytes())
        if fault == "lock":
            lock["source_lock_hash"] = sha256_json("different")
        elif fault == "unpinned":
            lock["wheels"][0]["hash"] = sha256_json("different")
        else:
            lock["source_roots"] = ["missing"]
        path.write_text(canonical_json(lock))
    with pytest.raises(ContractError):
        prepared.prepare_dependencies(**prepare_fixture)
    assert not (prepare_fixture["output"] / prepared.MANIFEST).exists()
    assert DevJournal(prepare_fixture["output"], "run_dev_preparedependencies").events()[-1][
        "event_type"] == "probe_dependency_preparation_failed"


@pytest.mark.parametrize("url", ["http://files.pythonhosted.org/packages/a.whl",
                                "https://example.com/packages/a.whl",
                                "https://files.pythonhosted.org/packages/a.tar.gz",
                                "https://files.pythonhosted.org/packages/a.whl?secret=x"])
def test_only_public_pypi_wheels_are_admitted(url):
    with pytest.raises(ValidationError):
        prepared.PublicWheel.model_validate({**WHEEL, "url": url})


@pytest.mark.parametrize("path", ["../secret", ".git/objects", ".ENV", ".PatchLoop-Hidden/x"])
def test_public_paths_reject_private_or_escaping_roots(path):
    with pytest.raises((ValueError, ContractError)):
        prepared.WheelLock.lock_path(path)
    with pytest.raises((ValueError, ContractError)):
        prepared.WheelLock.import_roots([path])


@pytest.mark.parametrize("body", [b"bad", b"too long", b"wheel"])
def test_download_checks_exact_bytes_without_redirect_or_environment(tmp_path, monkeypatch, body):
    client = httpx.Client
    def factory(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        return client(transport=httpx.MockTransport(lambda req: httpx.Response(200, content=body)),
                      **kwargs)
    monkeypatch.setattr(prepared.httpx, "Client", factory)
    if body == b"wheel":
        prepared._download(prepared.PublicWheel.model_validate(WHEEL), tmp_path / "wheel")
    else:
        with pytest.raises(ContractError):
            prepared._download(prepared.PublicWheel.model_validate(WHEEL), tmp_path / "wheel")


def test_reuse_is_offline_and_copies_independent_bytes(
    bundle, smoke_package, monkeypatch, tmp_path,
):
    def forbidden(*a, **kw):
        pytest.fail("offline reuse attempted a download/install")
    monkeypatch.setattr(prepared, "_download", forbidden)
    monkeypatch.setattr(prepared.subprocess, "run", forbidden)
    dependency = prepared.load_dependencies(bundle, smoke_package.public, prepared.admit(bundle))
    first, second = tmp_path / "one", tmp_path / "two"
    dependency.verify(target=first)
    dependency.verify(target=second)
    file = first / "public_dependency.py"
    file.chmod(0o666)
    file.write_bytes(b"changed")
    assert (second / file.name).read_bytes() == b"VALUE = 42\n"
    dependency.verify()


@pytest.mark.parametrize("fault", ["missing", "content", "extra", "manifest", "identity"])
def test_missing_changed_sources_fail_closed(bundle, smoke_package, fault):
    dependency = prepared.load_dependencies(bundle, smoke_package.public, prepared.admit(bundle))
    target = bundle.parent / "site-packages/public_dependency.py"
    if fault == "missing":
        target.unlink()
    elif fault == "content":
        target.write_bytes(b"tamper")
    elif fault == "extra":
        (target.parent / "extra.py").write_bytes(b"unadmitted")
    elif fault == "manifest":
        bundle.unlink()
    else:
        bundle.write_bytes(bundle.read_bytes() + b" ")
    with pytest.raises(ContractError):
        dependency.verify()


@pytest.mark.parametrize("field", ["repository_url", "base_commit", "files", "source_roots"])
def test_incomplete_descriptor_uses_normal_contract_failure(bundle, field):
    data = json.loads(bundle.read_bytes())
    del data[field]
    bundle.write_text(canonical_json(data))
    assert prepared.admit(bundle) is None
    with pytest.raises(ContractError):
        prepared.read_descriptor(bundle)


def test_sandbox_adds_only_readonly_snapshot_and_ordered_imports(
    bundle, smoke_package, public_repo, monkeypatch,  # noqa: F811
):
    dependency = prepared.load_dependencies(bundle, smoke_package.public, prepared.admit(bundle))
    backend = probes.DockerProbeSandbox(dependencies=dependency)
    monkeypatch.setattr(probes.DockerSandbox, "image_identity", lambda *a, **kw:
                        probes.PROBE_IMAGE_DIGEST)
    monkeypatch.setattr(probes.DockerSandbox, "cli_path", lambda: "docker")
    monkeypatch.setattr(backend, "_cleanup", lambda *a: True)
    backend.preflight()

    def launch(command, **kwargs):
        mounts = [item for item in command if item.startswith("type=bind")]
        assert len(mounts) == 3 and all(item.endswith(",readonly") for item in mounts)
        assert command[command.index("--network") + 1] == "none"
        assert command[command.index("--pids-limit") + 1] == "2"
        assert command[command.index("--platform") + 1] == "linux/amd64"
        paths = {m.split(",target=")[1].split(",")[0]:
                 Path(m.split("source=")[1].split(",target=")[0]) for m in mounts}
        assert paths[prepared.MOUNT] != bundle.parent / "site-packages"
        assert (paths[prepared.MOUNT] / "public_dependency.py").read_bytes() == b"VALUE = 42\n"
        config = json.loads((paths["/opt/patchloop"] / "dependencies.json").read_bytes())
        assert config["import_paths"] == ["/workspace", prepared.MOUNT]
        assert not (paths["/workspace"] / ".env").exists()
        return FakeProcess()
    mock_launch(monkeypatch, launch)
    receipt = backend.run_probe(public_repo, "check", "import public_dependency", deadline=None,
                                execution_identity={"run_id": "r", "action_id": "a"})
    assert receipt["profile_hash"] == probes.probe_profile_hash(dependency.identity)
    assert receipt["execution_policy"]["dependencies"] == dependency.identity.model_dump()


def test_dependency_snapshot_omits_git_links_without_reading_targets(tmp_path, monkeypatch):
    monkeypatch.setattr(probes.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess([], 0, b"120000 abc 0\tlink.py\0", b""))
    # No filesystem link or destination exists. Neither is opened or followed.
    digest = probes._snapshot(tmp_path, tmp_path / "absent", None, omit_symlinks=True)
    assert digest == sha256_json([{"path": "link.py", "omitted": "tracked_symlink"}])
    with pytest.raises(ContractError, match="regular"):
        probes._snapshot(tmp_path, tmp_path / "absent", None)


def test_declared_roots_copy_current_source_and_root_files_without_large_other_trees(
    tmp_path, monkeypatch,
):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/module.py").write_bytes(b"current edit")
    (tmp_path / "pyproject.toml").write_bytes(b"public metadata")
    monkeypatch.setattr(probes.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess([], 0,
                            b"100644 abc 0\tsrc/module.py\0"
                            b"100644 abc 0\tpyproject.toml\0"
                            b"100644 abc 0\ttests/large-dataset\0", b""))
    target = tmp_path / "snapshot"
    probes._snapshot(tmp_path, target, None, omit_symlinks=True, source_roots=["src"])
    assert (target / "src/module.py").read_bytes() == b"current edit"
    assert (target / "pyproject.toml").read_bytes() == b"public metadata"
    assert not (target / "tests").exists()


class DependencyProbe(FakeProbe):
    def __init__(self, *, dependencies):
        super().__init__(status="passed")
        self.dependencies = dependencies
        self.environment = dependencies.environment

    def preflight(self, **kwargs):
        self.dependencies.verify()
        return {"image_digest": probes.PROBE_IMAGE_DIGEST,
                "profile_hash": probes.probe_profile_hash(self.dependencies.identity)}

    def run_probe(self, *args, **kwargs):
        output = super().run_probe(*args, **kwargs)
        output.update(self.preflight())
        output["execution_policy"] = probes.probe_execution_policy(
            effective_timeout_seconds=30.0, row_deadline_limited=False, cleanup_status="confirmed",
            profile=probes.probe_profile(self.dependencies.identity),
        )
        output["execution_policy_hash"] = sha256_json(output["execution_policy"])
        return output


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_actual_inputs_evaluation_and_closed_replay_bind_dependencies(
    bundle, smoke_package, tmp_path, monkeypatch, policy,
):
    backends = []
    def backend(**kwargs):
        instance = DependencyProbe(**kwargs)
        backends.append(instance)
        return instance
    class ProbeThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            if not json.loads(context).get("recent_probes"):
                description = next(t["description"] for t in tools if t["name"] == "run_probe")
                assert "Prepared public wheel" in description
                assert str(bundle) not in description
                return DevModelTurn(tool_calls=[probe_call()])
            return super().next_turn(context, tools)
    monkeypatch.setattr(runner, "DockerProbeSandbox", backend)
    monkeypatch.setattr(runner, "MockDevAdapter", ProbeThenMock)
    request = DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True, context_policy=policy,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        state_root=tmp_path / "state",
        prepared_probe_dependencies=bundle,
    )
    result = runner.run_dev(request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(request.state_root, result["run_id"])
    store = ArtifactStore(request.state_root / "artifacts")
    for event in journal.events():
        if event["event_type"] != "turn_started":
            continue
        turn = event["payload"]
        inputs = runner._load_active_model_input(turn, store, context_policy=policy)
        context = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
        state = reconstruct_state(inputs, context_policy=policy)
        for field in ("public_task", "current_diff", "visible_check_status"):
            assert state[field] == context[field]
        assert str(bundle) not in canonical_json(inputs)
    bound = [e for e in journal.events() if e["event_type"] == "probe_dependencies_bound"]
    assert len(bound) == 1
    assert bound[0]["payload"]["identity"] == prepared.admit(bundle).model_dump()
    before = journal.path.read_bytes()
    assert runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"]}))[
        "runs"][0] == result
    assert journal.path.read_bytes() == before and sum(b.calls for b in backends) == 1
    with pytest.raises(ResumeContractMismatch):
        runner.run_dev(request.model_copy(update={"resume_run_id": result["run_id"],
                                                  "prepared_probe_dependencies": None}))


@pytest.mark.parametrize("fault", ["missing", "tamper", "wrong_task"])
def test_bad_dependencies_stop_before_model(bundle, smoke_package, tmp_path, monkeypatch, fault):
    if fault == "missing":
        bundle.unlink()
    elif fault == "tamper":
        (bundle.parent / "site-packages/public_dependency.py").write_bytes(b"tamper")
    else:
        data = json.loads(bundle.read_bytes())
        data["base_commit"] = "f" * 40
        bundle.write_text(canonical_json(data))
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    monkeypatch.setattr(MockDevAdapter, "next_turn", lambda *a, **kw: pytest.fail("model called"))
    result = runner.run_dev(DevRunRequest(
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        provider="mock", model="mock-dev", enable_probes=True,
        prepared_probe_dependencies=bundle, state_root=tmp_path / "state",
    ))["runs"][0]
    assert result["terminal"] == "PREFLIGHT_FAILED"


def test_option_requires_enabled_probes(bundle, smoke_package):
    with pytest.raises(ValidationError, match="enable-probes"):
        DevRunRequest(task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
                      provider="mock", model="mock-dev", prepared_probe_dependencies=bundle)


@pytest.mark.parametrize("dynamic", [False, True])
def test_workspace_metadata_uses_public_static_or_explicit_snapshot_version(tmp_path, dynamic):
    project = tmp_path / "src"
    project.mkdir()
    version = "dynamic = ['version']" if dynamic else "version = '2.3.4'"
    (project / "pyproject.toml").write_text(f"[project]\nname = 'public-project'\n{version}\n")
    target = tmp_path / "deps"
    target.mkdir()
    records = prepared._workspace_metadata(tmp_path,
        [{"name": "public-project", "source": {"editable": "src"}}], ["src"], "a" * 40, target)
    expected = "0+patchloop." + "a" * 40 if dynamic else "2.3.4"
    assert records[0]["version"] == expected
    assert records[0]["version_basis"] == (
        "source_snapshot_not_release_version" if dynamic else "public_pyproject")
    # Read distribution identity without importing a project or executing build hooks.
    from importlib.metadata import distributions
    assert [(d.metadata['Name'], d.version) for d in distributions(path=[str(target)])] == [
        ('public-project', expected)]
    assert not list(target.glob("public_project/*.py"))


@pytest.mark.parametrize("mismatch", [False, True])
def test_evaluator_requires_matching_dependency_receipt(bundle, tmp_path, mismatch):
    _, engine, store, _, _, _, manifest, receipt = _prepared(tmp_path)
    identity = prepared.admit(bundle)
    profile = probes.probe_profile(identity)
    manifest = manifest.model_copy(update={
        "probe_dependencies": identity, "probe_profile_hash": sha256_json(profile),
    })
    if not mismatch:
        receipt["profile_hash"] = manifest.probe_profile_hash
        receipt["execution_policy"] = probes.probe_execution_policy(
            profile=profile, effective_timeout_seconds=8.0, row_deadline_limited=True,
            cleanup_status="confirmed",
        )
        receipt["execution_policy_hash"] = sha256_json(receipt["execution_policy"])
    manifest = manifest.model_copy(update={"probe_evidence": [store.put_json(receipt)],
                                           "probe_execution_count": 1})
    evidence = engine._probe_policy_evidence(manifest)
    assert evidence.state == (VerdictState.ERROR if mismatch else VerdictState.PASS)


def test_active_resume_revalidates_contents_before_another_model_call(
    bundle, tmp_path, monkeypatch,
):
    class Crash(BaseException):
        pass
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    def crash(*a, **kw):
        raise Crash()
    monkeypatch.setattr(MockDevAdapter, "next_turn", crash)
    request = DevRunRequest(
        provider="mock", model="mock-dev", enable_probes=True,
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        state_root=tmp_path / "state", prepared_probe_dependencies=bundle,
    )
    with pytest.raises(Crash):
        runner.run_dev(request)
    journals = list((request.state_root / "runs").glob("*.jsonl"))
    assert len(journals) == 1
    (bundle.parent / "site-packages/public_dependency.py").write_bytes(b"changed while paused")
    result = runner.run_dev(request.model_copy(update={"resume_run_id": journals[0].stem}))[
        "runs"][0]
    assert result["terminal"] == "PREFLIGHT_FAILED"
