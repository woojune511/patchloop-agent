from __future__ import annotations

import json
import subprocess
import sys

import pytest
from test_prepared_probe_dependencies import (  # noqa: F401
    DependencyProbe,
    prepare_fixture,
)
from test_prepared_probe_dependencies import (
    test_actual_inputs_evaluation_and_closed_replay_bind_dependencies as actual_inputs_case,
)
from test_probe_dependency_resolution import REAL_SUBPROCESS_RUN, resolved_fixture  # noqa: F401

from patchloop import prepared_probe_dependencies as prepared
from patchloop import probe_project_files as project_files
from patchloop.dev import runner
from patchloop.dev.contracts import DevRunRequest
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox import probes
from patchloop.util import canonical_json, sha256_bytes

HOOK = ('\n[tool.hatch]\nversion.source = "vcs"\n'
        'build.hooks.vcs.version-file = "src/fixture_project/_version.py"\n')


@pytest.fixture
def generated_request(resolved_fixture):  # noqa: F811
    request, repo, _ = resolved_fixture
    metadata = repo / "pyproject.toml"
    original = metadata.read_text().replace('"never-build-this-project"', '"hatch-vcs>=0.5"')
    original = original.replace('"never_import_this"', '"hatchling.build"')
    metadata.write_text(original + HOOK)
    package = repo / "src/fixture_project"
    package.mkdir()
    (package / "__init__.py").write_text(
        "from ._version import version\nfrom .logic import value\n")
    (package / "logic.py").write_text("value = 41\n")
    return request, repo


@pytest.fixture
def generated_bundle(generated_request, monkeypatch):
    request, repo = generated_request
    manifest = prepared.prepare_dependencies(**request)
    monkeypatch.setattr(prepared.subprocess, "run", REAL_SUBPROCESS_RUN)
    monkeypatch.setattr(prepared, "_download", lambda *a: pytest.fail("network after preparation"))
    monkeypatch.setattr(prepared.httpx, "Client", lambda *a, **kw: pytest.fail("network"))
    return manifest, repo


def dependency(manifest, public):
    return prepared.load_dependencies(manifest, public, prepared.admit(manifest))


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, timeout=10)


def test_prepare_offline_independent_snapshots_execute_current_source(
    generated_bundle, smoke_package, tmp_path,
):
    manifest, repo = generated_bundle
    dep = dependency(manifest, smoke_package.public)
    item, = dep.generated_project_files
    assert item.pyproject_hash == sha256_bytes((repo / "pyproject.toml").read_bytes())
    assert item.version == "0+patchloop." + "a" * 40
    original = (manifest.parent / project_files.DIRECTORY / item.path).read_bytes()
    assert not (repo / item.path).exists()
    git(repo, "init")
    git(repo, "add", ".")
    digests = []
    for index, expected in enumerate((42, 43)):
        (repo / "src/fixture_project/logic.py").write_text(f"value = {expected}\n")
        target = tmp_path / f"snapshot-{index}"
        target.mkdir()
        dep.verify(target=tmp_path / f"dependencies-{index}")
        digests.append(probes._snapshot(repo, target, None, source_roots=["src"],
                                       omit_symlinks=True, dependencies=dep))
        code = (f"import sys; sys.path.insert(0, {str(target / 'src')!r}); "
                "import fixture_project; "
                f"assert fixture_project.value == {expected}; "
                f"assert fixture_project.version == {item.version!r}")
        subprocess.run([sys.executable, "-I", "-S", "-c", code], check=True,
                       capture_output=True, timeout=10)
    assert digests[0] != digests[1]
    assert (tmp_path / "snapshot-0/src/fixture_project/logic.py").read_text() == "value = 42\n"
    assert (manifest.parent / project_files.DIRECTORY / item.path).read_bytes() == original
    assert not (repo / item.path).exists()
    # Newly tracked implementation bytes always win over a prepared artifact.
    (repo / item.path).write_text("version = 'current edit'\n")
    git(repo, "add", item.path)
    target = tmp_path / "tracked"
    probes._snapshot(repo, target, None, source_roots=["src"], dependencies=dep)
    assert (target / item.path).read_text() == "version = 'current edit'\n"


@pytest.mark.parametrize("fault", ["missing", "tamper", "extra", "manifest"])
def test_generated_corruption_stops_before_model(
    generated_bundle, smoke_package, tmp_path, monkeypatch, fault,
):
    manifest, _ = generated_bundle
    dep = dependency(manifest, smoke_package.public)
    artifact = manifest.parent / project_files.DIRECTORY / dep.generated_project_files[0].path
    if fault == "missing":
        artifact.unlink()
    elif fault == "tamper":
        artifact.write_bytes(b"version = 'changed'\n")
    elif fault == "extra":
        artifact.with_name("extra.py").write_bytes(b"extra")
    else:
        data = json.loads(manifest.read_bytes())
        data["generated_project_files"][0]["pyproject_hash"] = "sha256:" + "f" * 64
        manifest.write_text(canonical_json(data))
    with pytest.raises(ContractError):
        dep.verify()
    monkeypatch.setattr(runner, "DockerProbeSandbox", DependencyProbe)
    monkeypatch.setattr(runner.MockDevAdapter, "next_turn", lambda *a: pytest.fail("model called"))
    result = runner.run_dev(DevRunRequest(
        task=repository_root() / "tasks/smoke/csv-quoted-newline/public.yaml",
        provider="mock", model="mock-dev", enable_probes=True,
        prepared_probe_dependencies=manifest, state_root=tmp_path / "run-state",
    ))["runs"][0]
    assert result["terminal"] == "PREFLIGHT_FAILED"


@pytest.mark.parametrize("fault", ["escape", "private", "template", "extension", "roots",
                                    "existing", "backend", "external_config", "target_hook",
                                    "drive", "drive_relative", "backslash", "alias", "ads"])
def test_unsupported_declarations_publish_no_descriptor(generated_request, fault):
    request, repo = generated_request
    metadata = repo / "pyproject.toml"
    content = metadata.read_text()
    replacements = {"escape": "../outside.py", "private": ".env/version.py",
                    "extension": "src/version.txt", "roots": "other/version.py",
                    "drive": (repo.parent / "outside.py").as_posix(),
                    "drive_relative": "C:outside.py", "backslash": r"src\outside.py",
                    "alias": ".. /outside.py", "ads": "src/file:stream.py"}
    if fault in replacements:
        content = content.replace('"src/fixture_project/_version.py"',
                                  json.dumps(replacements[fault]))
        request = {**request, "source_roots": []} if fault != "roots" else request
    elif fault == "template":
        content += 'build.hooks.vcs.template = "custom version output"\n'
    elif fault == "existing":
        (repo / "src/fixture_project/_version.py").write_bytes(b"original")
    elif fault == "backend":
        content = content.replace("hatchling.build", "custom.build")
    elif fault == "external_config":
        (repo / "hatch.toml").write_text("# separate configuration")
    else:
        content += 'build.targets.wheel.hooks.vcs.version-file = "src/other.py"\n'
    metadata.write_text(content)
    with pytest.raises(ContractError):
        prepared.prepare_dependencies(**request)
    assert not (request["output"] / prepared.MANIFEST).exists()
    assert not (repo.parent / "outside.py").exists()
    assert DevJournal(request["output"], "run_dev_preparedependencies").events()[
        -1]["event_type"] == "probe_dependency_preparation_failed"


@pytest.mark.parametrize("fault", ["interruption", "tamper"])
def test_interrupted_generation_never_publishes(generated_request, monkeypatch, fault):
    request, _ = generated_request
    original = project_files.prepare
    def interrupt(*args):
        result = original(*args)
        if fault == "tamper":
            artifact = request["output"] / project_files.DIRECTORY / result[0]["path"]
            artifact.write_bytes(b"changed before publication")
            return result
        raise OSError("interrupted after artifact creation")
    monkeypatch.setattr(project_files, "prepare", interrupt)
    with pytest.raises(ContractError):
        prepared.prepare_dependencies(**request)
    assert list((request["output"] / project_files.DIRECTORY).rglob("*.py"))
    assert not (request["output"] / prepared.MANIFEST).exists()


def test_changed_build_metadata_rejects_stale_generated_output(generated_bundle, smoke_package,
                                                              tmp_path):
    manifest, repo = generated_bundle
    dep = dependency(manifest, smoke_package.public)
    git(repo, "init")
    git(repo, "add", ".")
    with (repo / "pyproject.toml").open("a") as stream:
        stream.write("\n# changed configuration\n")
    with pytest.raises(ContractError, match="unchanged public build metadata"):
        probes._snapshot(repo, tmp_path / "snapshot", None, dependencies=dep)


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_generated_bundle_mock_reaches_evaluation_and_actual_inputs(
    generated_bundle, smoke_package, tmp_path, monkeypatch, policy,
):
    manifest, _ = generated_bundle
    assert dependency(manifest, smoke_package.public).environment["generated_version_files"]
    actual_inputs_case(
        manifest, smoke_package, tmp_path, monkeypatch, policy,
    )
