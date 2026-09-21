"""Public metadata resolution, source binding, target selection and offline reuse."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_prepared_probe_dependencies import prepare_fixture  # noqa: F401
from typer.testing import CliRunner

import patchloop.prepared_probe_dependencies as prepared
import patchloop.probe_dependency_resolution as resolution
from patchloop.cli import app
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import DevModelTurn, DevRunRequest
from patchloop.dev.conversation import reconstruct_state
from patchloop.dev.model import MockDevAdapter
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.prepared_source import PreparedSource
from patchloop.runtime import repository_root
from patchloop.util import sha256_bytes

REAL_SUBPROCESS_RUN = subprocess.run

PROJECT = '''[project]
name = "fixture-project"
dynamic = ["version"]
requires-python = ">=3.10"
dependencies = ["fixture>=1", "win-only; sys_platform == 'win32'",
                "old-python; python_version < '3.11'"]
[project.optional-dependencies]
feature = ["optional[extra]>=2"]
[dependency-groups]
base = ["base>=3"]
test = [{include-group = "base"}, "test-lib>=4"]
[build-system]
requires = ["never-build-this-project"]
build-backend = "never_import_this"
[tool.uv.sources]
fixture = {path = "not-a-public-source"}
'''


def wheel(name="fixture", version="1.0", tag="py3-none-any"):
    return {"url": f"https://files.pythonhosted.org/packages/aa/{name}-{version}-{tag}.whl",
            "hash": sha256_bytes(b"wheel"), "size": 5}


def lock_bytes(packages=None):
    packages = packages if packages is not None else [("fixture", "1.0", [wheel()], None)]
    text = 'lock-version = "1.0"\ncreated-by = "uv"\nrequires-python = ">=3.12"\n'
    for name, version, wheels, marker in packages:
        text += f'\n[[packages]]\nname = "{name}"\nversion = "{version}"\n'
        if marker:
            text += f'marker = "{marker}"\n'
        for entry in wheels:
            text += ('[[packages.wheels]]\n'
                     f'url = "{entry["url"]}"\nsize = {entry["size"]}\n'
                     f'hashes = {{sha256 = "{entry["hash"].split(":")[1]}"}}\n')
    return text.encode()


@pytest.fixture
def resolved_fixture(prepare_fixture, monkeypatch):  # noqa: F811
    request = {**prepare_fixture, "resolve": True, "groups": ["test"],
               "extras": ["feature"], "source_roots": ["src"]}
    request.pop("wheel_lock")
    repo = request["output"].parent / "source"
    (repo / "pyproject.toml").write_text(PROJECT)
    source = PreparedSource(repository_url=request["public"].repository.url,
                            base_commit=request["public"].repository.base_commit,
                            git_commit="a" * 40, git_tree="b" * 40,
                            content_hash=sha256_bytes(b"source"))
    request["prepared_source"].write_text(source.model_dump_json())
    monkeypatch.setattr(prepared, "load_source", lambda *a, **kw: (source, repo))
    install = prepared.subprocess.run
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1:3] != ["pip", "compile"]:
            assert (request["output"] / "resolved-wheel-lock.json").exists()
            return install(command, **kwargs)
        for flag in ("--no-config", "--no-cache", "--no-sources", "--no-python-downloads",
                     "--only-binary"):
            assert flag in command
        assert command[command.index("--python-version") + 1] == "3.12"
        assert command[command.index("--python-platform") + 1] == "x86_64-manylinux_2_28"
        assert command[command.index("--default-index") + 1] == "https://pypi.org/simple"
        assert kwargs["cwd"] == request["output"]
        assert kwargs["timeout"] == 120
        assert kwargs["env"]["UV_HTTP_RETRIES"] == "0"
        assert Path(kwargs["env"]["NETRC"]).read_bytes() == b""
        assert Path(kwargs["env"]["UV_CREDENTIALS_DIR"]).parent == request["output"]
        assert "SECRET_API_KEY" not in kwargs["env"]
        Path(command[command.index("--output-file") + 1]).write_bytes(lock_bytes())
        return subprocess.CompletedProcess(command, 0, b"", b"Resolved fixture")

    monkeypatch.setattr(prepared.subprocess, "run", run)
    return request, repo, calls


def test_resolved_preparation_binds_public_inputs_and_reuses_offline(resolved_fixture, monkeypatch):
    request, repo, calls = resolved_fixture
    original = (repo / "pyproject.toml").read_bytes()
    path = prepared.prepare_dependencies(**request)
    descriptor = json.loads(path.read_bytes())
    lock = descriptor["wheel_lock"]
    assert lock["schema_version"] == "resolved-public-probe-wheel-lock-v1"
    assert lock == json.loads((path.parent / "resolved-wheel-lock.json").read_bytes())
    assert lock["prepared_source_hash"] == sha256_bytes(request["prepared_source"].read_bytes())
    assert lock["prepared_source"]["git_tree"] == "b" * 40
    assert lock["source_metadata"]["hash"] == sha256_bytes(original)
    assert lock["source_metadata"]["requirements"] == [
        "base>=3", "fixture>=1", "optional[extra]>=2", "test-lib>=4"]
    assert lock["pylock_hash"] == sha256_bytes((path.parent / "pylock.toml").read_bytes())
    assert lock["resolver_hash"] == sha256_bytes(Path(sys.executable).read_bytes())
    assert descriptor["workspace_metadata"][0]["version"] == "0+patchloop." + "a" * 40
    assert len(calls) == 2 and (repo / "pyproject.toml").read_bytes() == original
    monkeypatch.setattr(resolution.subprocess, "run", lambda *a, **k: pytest.fail("subprocess"))
    monkeypatch.setattr(prepared, "_download", lambda *a: pytest.fail("network"))
    dependency = prepared.load_dependencies(path, request["public"], prepared.admit(path))
    first, second = path.parent / "copy-1", path.parent / "copy-2"
    dependency.verify(target=first)
    dependency.verify(target=second)
    changed = first / "public_dependency.py"
    changed.chmod(0o644)
    changed.write_bytes(b"changed")
    assert (second / changed.name).read_bytes() == b"VALUE = 42\n"
    dependency.verify()
    with pytest.raises(ContractError, match="already exists"):
        prepared.prepare_dependencies(**request)


@pytest.mark.parametrize("change", [
    lambda s: s.replace('dynamic = ["version"]', 'dynamic = ["version", "dependencies"]'),
    lambda s: s.replace('requires-python = ">=3.10"', 'requires-python = ">=3.13"'),
    lambda s: s.replace('"fixture>=1"', '"fixture @ https://example.com/archive.whl"'),
    lambda s: s.replace('"fixture>=1"', '"./local-package"'),
    lambda s: s.replace('"fixture>=1"', '"fixture-project[feature]"'),
    lambda s: s.replace('base = ["base>=3"]', 'base = [{include-group = "test"}]'),
    lambda s: s.replace('base = ["base>=3"]', 'base = [{include-group = "absent"}]'),
    lambda s: s.replace('base = ["base>=3"]', 'base = [{unsupported = "value"}]'),
    lambda s: s.replace('[project.optional-dependencies]', '[not-project-optional]'),
])
def test_unsupported_declarations_fail_before_resolution(resolved_fixture, change):
    request, repo, calls = resolved_fixture
    (repo / "pyproject.toml").write_text(change(PROJECT))
    with pytest.raises(ContractError):
        prepared.prepare_dependencies(**request)
    assert calls == []
    assert not (request["output"] / prepared.MANIFEST).exists()
    assert DevJournal(request["output"], "run_dev_preparedependencies").events()[-1][
        "event_type"] == "probe_dependency_preparation_failed"


@pytest.mark.parametrize("fault", ["exit", "timeout", "malformed", "sdist", "origin", "mismatch"])
def test_failed_resolution_never_downloads_or_publishes(resolved_fixture, monkeypatch, fault):
    request, _, _ = resolved_fixture
    def resolve(command, **kwargs):
        assert command[1:3] == ["pip", "compile"]
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, 120)
        raw = lock_bytes()
        if fault == "malformed":
            raw = b"this is not a lock"
        elif fault == "sdist":
            raw = lock_bytes([("fixture", "1.0", [], None)])
        elif fault == "origin":
            raw = raw.replace(b"files.pythonhosted.org", b"example.com")
        elif fault == "mismatch":
            raw = raw.replace(b'"1.0"\n[[packages.wheels]]', b'"2.0"\n[[packages.wheels]]')
        Path(command[command.index("--output-file") + 1]).write_bytes(raw)
        return subprocess.CompletedProcess(command, int(fault == "exit"), b"", b"failed")
    monkeypatch.setattr(resolution.subprocess, "run", resolve)
    monkeypatch.setattr(prepared, "_download", lambda *a: pytest.fail("downloaded"))
    with pytest.raises(ContractError):
        prepared.prepare_dependencies(**request)
    assert not (request["output"] / prepared.MANIFEST).exists()


def test_target_wheels_and_markers_do_not_follow_windows_host():
    binary = [wheel(tag="cp312-cp312-win_amd64"),
              wheel(tag="cp312-cp312-manylinux_2_31_x86_64"),
              wheel(tag="cp312-cp312-manylinux_2_28_x86_64"),
              wheel(tag="cp311-abi3-manylinux_2_17_x86_64"), wheel()]
    raw = lock_bytes([("fixture", "1.0", binary, "sys_platform == 'linux'"),
                      ("windows-only", "1.0", [], "sys_platform == 'win32'"),
                      ("transitive", "1.0", [wheel("transitive")], None)])
    result = resolution.select_wheels(raw, project_name="workspace")
    assert [w.url for w in result] == [binary[2]["url"], wheel("transitive")["url"]]


def test_runtime_dependencies_are_default_and_no_wheels_is_supported(resolved_fixture):
    request, repo, _ = resolved_fixture
    metadata = resolution.project_requirements(repo, groups=[], extras=[])
    assert metadata["requirements"] == ["fixture>=1"]
    assert resolution.select_wheels(lock_bytes([]), project_name="workspace") == []


def test_project_without_dependencies_still_publishes_source_metadata(
    resolved_fixture, monkeypatch,
):
    request, repo, _ = resolved_fixture
    (repo / "pyproject.toml").write_text('[project]\nname = "fixture-project"\nversion = "1"\n')
    def resolve(command, **kwargs):
        assert command[1:3] == ["pip", "compile"]
        Path(command[command.index("--output-file") + 1]).write_bytes(lock_bytes([]))
        return subprocess.CompletedProcess(command, 0, b"", b"")
    monkeypatch.setattr(resolution.subprocess, "run", resolve)
    monkeypatch.setattr(prepared, "_download", lambda *a: pytest.fail("downloaded"))
    path = prepared.prepare_dependencies(**{**request, "groups": [], "extras": []})
    data = json.loads(path.read_bytes())
    assert data["wheel_lock"]["wheels"] == [] and data["workspace_metadata"][0]["version"] == "1"
    prepared.load_dependencies(path, request["public"], prepared.admit(path)).verify()


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_resolved_bundle_reaches_probe_submit_and_isolated_evaluation(
    resolved_fixture, monkeypatch, tmp_path, policy,
):
    from test_dev_probes import probe_call
    from test_prepared_probe_dependencies import DependencyProbe

    from patchloop.artifacts import ArtifactStore

    request, _, _ = resolved_fixture
    path = prepared.prepare_dependencies(**request)
    monkeypatch.setattr(prepared.subprocess, "run", REAL_SUBPROCESS_RUN)
    monkeypatch.setattr(prepared, "_download", lambda *a: pytest.fail("network"))
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    class ProbeThenMock(MockDevAdapter):
        def next_turn(self, context, tools):
            if not json.loads(context).get("recent_probes"):
                return DevModelTurn(tool_calls=[probe_call()])
            return super().next_turn(context, tools)
    monkeypatch.setattr(runner, "MockDevAdapter", ProbeThenMock)
    run_request = DevRunRequest(
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        provider="mock", model="mock-dev", enable_probes=True, context_policy=policy,
        prepared_probe_dependencies=path, state_root=tmp_path / "run-state",
    )
    result = runner.run_dev(run_request)["runs"][0]
    assert result["terminal"] == "EVALUATOR_PASS"
    journal = DevJournal(run_request.state_root, result["run_id"])
    store = ArtifactStore(run_request.state_root / "artifacts")
    turns = 0
    for event in journal.events():
        if event["event_type"] != "turn_started":
            continue
        turns += 1
        turn = event["payload"]
        inputs = runner._load_active_model_input(turn, store, context_policy=policy)
        state = reconstruct_state(inputs, context_policy=policy)
        context = json.loads(store.read_bytes(Artifact.model_validate(turn["context_artifact"])))
        for key in ("public_task", "current_diff", "visible_check_status"):
            assert state[key] == context[key]
        assert "resolved-public-probe-wheel-lock" not in json.dumps(inputs)
        assert str(path) not in json.dumps(inputs)
    assert turns >= 4


@pytest.mark.parametrize("choices", [[], ["--resolve", "--wheel-lock", "lock.json"],
                                     ["--wheel-lock", "lock.json", "--group", "test"]])
def test_cli_rejects_ambiguous_modes_without_creating_output(tmp_path, choices):
    output = tmp_path / "out"
    result = CliRunner().invoke(app, ["task", "prepare-probe-dependencies",
        str(repository_root() / "tasks/smoke/csv-quoted-newline"),
        "--prepared-source", "source.json", "--output", str(output), *choices])
    assert result.exit_code != 0 and not output.exists()


def test_cli_passes_explicit_groups_extras_and_roots(tmp_path, monkeypatch):
    seen = []
    def prepare(**kwargs):
        seen.append(kwargs)
        return tmp_path / prepared.MANIFEST
    monkeypatch.setattr(prepared, "prepare_dependencies", prepare)
    result = CliRunner().invoke(app, ["task", "prepare-probe-dependencies",
        str(repository_root() / "tasks/smoke/csv-quoted-newline"),
        "--prepared-source", "source.json", "--output", str(tmp_path / "out"),
        "--resolve", "--group", "test", "--group", "base", "--extra", "feature",
        "--source-root", "src"])
    assert result.exit_code == 0, result.stdout
    assert seen[0]["groups"] == ["test", "base"] and seen[0]["extras"] == ["feature"]
    assert seen[0]["source_roots"] == ["src"] and seen[0]["resolve"] is True
