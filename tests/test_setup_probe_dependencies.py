from __future__ import annotations

import json
from importlib.metadata import distributions

import pytest
from test_prepared_probe_dependencies import prepare_fixture  # noqa: F401
from test_probe_dependency_resolution import resolved_fixture  # noqa: F401

from diagnostics import setup_probe_dependencies as setup
from patchloop.errors import ContractError
from patchloop.probe_project_files import prepare as prepare_project_files
from patchloop.util import sha256_bytes

SOURCE = '''from setuptools import setup
deps = ["requests>=2", "colorama; sys_platform == 'win32'"]
raise RuntimeError("Must never execute this setup program")
setup(name="public-demo", install_requires=deps, python_requires=">=3.10", version=get_version())
'''


def fixture(tmp_path, source=SOURCE):
    (tmp_path / "pyproject.toml").write_text("[tool.example]\n", encoding="utf-8")
    (tmp_path / "setup.py").write_text(source, encoding="utf-8")
    return tmp_path


def test_literal_metadata_never_executes_setup_and_uses_target_markers(tmp_path):
    repo = fixture(tmp_path)
    actual = setup.metadata(repo, groups=[], extras=[])
    assert actual["requirements"] == ["requests>=2"]
    assert actual["hash"] == sha256_bytes((repo / "setup.py").read_bytes())
    assert actual["path"] == "setup.py" and actual["project_name"] == "public-demo"


@pytest.mark.parametrize("change", ["mutation", "conditional", "dynamic", "kwargs",
                                    "url", "self", "python", "extra", "pep621"])
def test_unsupported_metadata_is_not_silently_guessed(tmp_path, change):
    source = SOURCE
    if change == "mutation":
        source = source.replace("raise RuntimeError", 'deps.append("extra")\nraise RuntimeError')
    elif change == "conditional":
        source = source.replace("deps =", "if True:\n    deps =")
    elif change == "dynamic":
        source = source.replace("install_requires=deps", "install_requires=compute()")
    elif change == "kwargs":
        source = source.replace("version=get_version()", "**options")
    elif change == "url":
        source = source.replace("requests>=2", "pkg @ https://example.test/pkg.whl")
    elif change == "self":
        source = source.replace("requests>=2", "public-demo")
    elif change == "python":
        source = source.replace(">=3.10", "<3.12")
    repo = fixture(tmp_path, source)
    if change == "pep621":
        (repo / "pyproject.toml").write_text('[project]\nname="public-demo"\n')
    with pytest.raises(ContractError):
        setup.metadata(repo, groups=[], extras=["test"] if change == "extra" else [])


def test_snapshot_metadata_and_scoped_hook_restoration(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    target = tmp_path / "installed"
    target.mkdir()
    records = setup.workspace_metadata(repo,
        [{"name": "public-demo", "source": {"editable": "."}}], [], "a" * 40, target)
    record = json.loads(next(target.glob("*/PATCHLOOP-SOURCE.json")).read_text())
    assert records == [record]
    assert record["version"] == "0+patchloop." + "a" * 40
    assert record["setup_hash"] == sha256_bytes((repo / "setup.py").read_bytes())
    previous = setup.resolution.project_requirements, setup.prepared._workspace_metadata

    def fail(**kwargs):
        assert setup.resolution.project_requirements is setup.metadata
        assert setup.prepared._workspace_metadata is setup.workspace_metadata
        raise RuntimeError("preparation fails")

    monkeypatch.setattr(setup.prepared, "prepare_dependencies", fail)
    with pytest.raises(RuntimeError, match="preparation fails"):
        setup.prepare(public=None, prepared_source=repo, output=tmp_path / "out", source_roots=[])
    assert previous == (setup.resolution.project_requirements, setup.prepared._workspace_metadata)


def test_explicit_requirements_file_binds_bytes_without_running_setup(tmp_path):
    repo = fixture(tmp_path, SOURCE.replace("install_requires=deps", "install_requires=load()"))
    requirements = repo / "requirements.txt"
    requirements.write_text("# public dependencies\nrequests>=2\n\n"
                            "colorama; sys_platform == 'win32'\n", encoding="utf-8")
    actual = setup.metadata(repo, groups=[], extras=[], requirements_file="requirements.txt")
    assert actual["requirements"] == ["requests>=2"]
    assert actual["adapter"] == "operator-selected-requirements-v1"
    assert actual["requirements_file"] == {
        "path": "requirements.txt", "hash": sha256_bytes(requirements.read_bytes()),
    }
    target = repo / "installed"
    target.mkdir()
    records = setup.workspace_metadata(repo,
        [{"name": "public-demo", "source": {"editable": "."}}], [], "a" * 40, target,
        requirements_file="requirements.txt")
    assert records[0]["requirements_file"] == actual["requirements_file"]
    with pytest.raises(ContractError):
        setup.metadata(repo, groups=[], extras=[])


@pytest.mark.parametrize("line", ["-r other.txt", "--index-url https://example.test",
                                  "pkg @ https://example.test/a.whl", "public-demo",
                                  "./local", "requests \\", "--editable ."])
def test_explicit_file_rejects_pip_options_and_non_index_sources(tmp_path, line):
    repo = fixture(tmp_path)
    (repo / "requirements.txt").write_text(line, encoding="utf-8")
    with pytest.raises(ContractError):
        setup.metadata(repo, groups=[], extras=[], requirements_file="requirements.txt")


@pytest.mark.parametrize("path", ["../outside.txt", "/absolute.txt", "C:/outside.txt"])
def test_explicit_requirements_path_must_stay_in_source(tmp_path, path):
    repo = fixture(tmp_path)
    with pytest.raises(ContractError):
        setup.metadata(repo, groups=[], extras=[], requirements_file=path)


def test_selected_file_composes_with_existing_receipt_admission(tmp_path, monkeypatch):
    repo = fixture(tmp_path)
    (repo / "requirements.txt").write_text("requests>=2", encoding="utf-8")
    previous = setup.resolution.project_requirements, setup.prepared._workspace_metadata
    receipt = tmp_path / "receipt.json"

    def fail(**kwargs):
        assert kwargs["generated_wheel_receipt"] == receipt
        assert kwargs["generated_wheel_receipt_hash"] == "sha256:" + "a" * 64
        assert kwargs["resolve"] is True
        value = setup.resolution.project_requirements(repo, groups=[], extras=[])
        assert value["requirements_file"]["path"] == "requirements.txt"
        raise ContractError("receipt rejected")

    monkeypatch.setattr(setup.prepared, "prepare_dependencies", fail)
    with pytest.raises(ContractError, match="receipt rejected"):
        setup.prepare(public=None, prepared_source=repo, output=tmp_path / "out",
                      source_roots=[], requirements_file="requirements.txt",
                      generated_wheel_receipt=receipt,
                      generated_wheel_receipt_hash="sha256:" + "a" * 64)
    assert previous == (setup.resolution.project_requirements, setup.prepared._workspace_metadata)


def test_legacy_setup_preparation_publishes_discoverable_plugins(resolved_fixture):  # noqa: F811
    request, repo, calls = resolved_fixture
    (repo / "pyproject.toml").unlink()
    (repo / "setup.py").write_text(
        'from setuptools import setup\n'
        'raise RuntimeError("must not execute")\n'
        'setup(name="public-demo", install_requires=["fixture>=1"], '
        'entry_points={"public.plugins": ["Demo = demo.plugin:factory"]})\n'
    )
    path = setup.prepare(public=request["public"], prepared_source=request["prepared_source"],
                         output=request["output"], source_roots=["src"],
                         supplemental_requirements=["fixture<2"])
    descriptor = json.loads(path.read_bytes())
    source = descriptor["wheel_lock"]["source_metadata"]
    assert source["pyproject_hash"] is None
    assert source["operator_supplemental_requirements"] == ["fixture<2"]
    assert source["requirements"] == ["fixture<2", "fixture>=1"]
    installed = path.parent / "site-packages"
    plugins = [ep for dist in distributions(path=[str(installed)])
               for ep in dist.entry_points if ep.group == "public.plugins"]
    assert [(ep.name, ep.value) for ep in plugins] == [("Demo", "demo.plugin:factory")]
    setup.prepared.load_dependencies(path, request["public"], setup.prepared.admit(path)).verify()
    assert len(calls) == 2  # Public resolution and offline wheel installation only.
    metadata = descriptor["workspace_metadata"]
    assert prepare_project_files(repo, metadata, ["src"], path.parent) == []
    (repo / "pyproject.toml").write_text("[tool.new]\n")
    with pytest.raises(ContractError, match="metadata changed"):
        prepare_project_files(repo, metadata, ["src"], path.parent)


@pytest.mark.parametrize("entry_points", [
    'compute()', '{"plugins": ["same=a", "same=b"]}',
    '{"plugins": ["item=module:factory [extra]"]}',
    '{"plugins\\nother": ["item=module"]}', '{"plugins": ["item=../../private"]}',
])
def test_unsupported_entry_points_fail_without_evaluation(tmp_path, entry_points):
    repo = fixture(tmp_path, 'from setuptools import setup\n'
                   f'setup(name="demo", entry_points={entry_points})\n')
    with pytest.raises(ContractError):
        setup.metadata(repo, groups=[], extras=[])


@pytest.mark.parametrize("requirement", ["demo", "pkg @ https://example.test/a.whl",
                                          "--index-url=https://example.test", "pkg\nother"])
def test_supplements_cannot_bypass_public_index_validation(tmp_path, requirement):
    repo = fixture(tmp_path, 'from setuptools import setup\nsetup(name="demo")\n')
    with pytest.raises(ContractError):
        setup.metadata(repo, groups=[], extras=[], supplemental_requirements=[requirement])
