from __future__ import annotations

import json

import pytest

from diagnostics import setup_probe_dependencies as setup
from patchloop.errors import ContractError
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
