"""Static legacy metadata never runs repository setup code."""

import pytest

from diagnostics.legacy_probe_metadata import read_metadata
from patchloop.errors import ContractError
from patchloop.probe_project_files import prepare
from patchloop.util import sha256_bytes


def test_lazy_setup_keywords_and_markers(tmp_path):
    (tmp_path / "setup.py").write_text(
        "raise RuntimeError('must never run')\n"
        "deps = ['packaging>=24', 'old; python_version < \\\"3\\\"']\n".replace('\\"', '"')
        + "opts = dict(name='demo', install_requires=deps, version=calculate_version())\n"
        "setup(**opts)\n",
        encoding="utf-8",
    )
    result = read_metadata(tmp_path, groups=[], extras=[], supplements=["setuptools==80.9.0"])
    assert result["requirements"] == ["packaging>=24", "setuptools==80.9.0"]


def test_cfg_metadata_and_no_pyproject_generation(tmp_path):
    raw = b"[metadata]\nname = demo\n[options]\ninstall_requires =\n packaging>=24\n"
    (tmp_path / "setup.cfg").write_bytes(raw)
    result = read_metadata(tmp_path, groups=[], extras=[])
    assert result["requirements"] == ["packaging>=24"]
    record = {
        "project_path": ".",
        "metadata_path": "setup.cfg",
        "metadata_hash": sha256_bytes(raw),
        "pyproject_hash": None,
    }
    assert prepare(tmp_path, [record], [], tmp_path / "output") == []
    (tmp_path / "setup.cfg").write_bytes(raw + b"# drift\n")
    with pytest.raises(ContractError, match="metadata changed"):
        prepare(tmp_path, [record], [], tmp_path / "output")


@pytest.mark.parametrize(
    "field",
    [
        "install_requires=dynamic()",
        "python_requires='<3.10'",
        "install_requires=['x @ https://invalid/x.whl']",
    ],
)
def test_incompatible_or_nonliteral_inputs_rejected(tmp_path, field):
    (tmp_path / "setup.py").write_text(f"setup(name='demo', {field})", encoding="utf-8")
    with pytest.raises(ContractError):
        read_metadata(tmp_path, groups=[], extras=[])
