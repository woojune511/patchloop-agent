from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
import tox.version as installed_tox_version

WORKSPACE = Path("/workspace").resolve()

PROBE = r"""
import json
import sys

import tox.tox_env.python.api as api_module
from tox.tox_env.python.api import Python

mode = sys.argv[1]
env_name = sys.argv[2]
base_pythons = json.loads(sys.argv[3])
ignore = sys.argv[4] == "true"

try:
    if mode == "extract":
        value = Python.extract_base_python(env_name)
    elif mode == "validate":
        value = Python._validate_base_python(  # noqa: SLF001
            env_name,
            base_pythons,
            ignore_base_python_conflict=ignore,
        )
    elif mode == "default":
        class Dummy:
            core = {"ignore_base_python_conflict": ignore}
            conf = {"default_base_python": base_pythons}
            extract_base_python = staticmethod(Python.extract_base_python)

        value = Python._base_python_default(Dummy(), None, env_name)  # noqa: SLF001
    else:
        raise AssertionError(f"unknown mode {mode}")
except BaseException as exc:
    result = {
        "ok": False,
        "error_type": type(exc).__name__,
        "message": str(exc),
        "module": api_module.__file__,
    }
else:
    result = {
        "ok": True,
        "value": value,
        "module": api_module.__file__,
    }

print(json.dumps(result))
"""


@pytest.fixture(scope="session")
def submitted_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source_root = tmp_path_factory.mktemp("tox-submitted-source") / "src"
    shutil.copytree(WORKSPACE / "src", source_root)
    installed_version = Path(installed_tox_version.__file__).resolve()
    shutil.copy2(installed_version, source_root / "tox" / "version.py")
    return source_root


def _source_env(source_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(source_root)
        if not inherited
        else os.pathsep.join((str(source_root), inherited))
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = "/tmp/pycache"
    return env


def _probe(
    source_root: Path,
    mode: str,
    env_name: str,
    *,
    base_pythons: list[str] | None = None,
    ignore: bool = False,
) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            PROBE,
            mode,
            env_name,
            json.dumps(base_pythons or []),
            str(ignore).lower(),
        ],
        env=_source_env(source_root),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, (
        f"probe failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    module_path = Path(result["module"]).resolve()
    assert module_path.is_relative_to(source_root.resolve()), (
        f"Python API loaded from {module_path}, not submitted source {source_root}"
    )
    return result


@pytest.mark.parametrize(
    ("env_name", "expected"),
    [
        ("lint-3.12-docs", "3.12"),
        ("qa-3.13t", "3.13t"),
        ("legacy-2.7", "2.7"),
        ("docs-py312", "py312"),
        ("cpython-3.12", "3.12"),
        ("pypy-3.9t", "pypy3.9t"),
    ],
)
def test_supported_factors_preserve_normalization(
    submitted_source: Path,
    env_name: str,
    expected: str,
) -> None:
    result = _probe(submitted_source, "extract", env_name)
    assert result == {
        "ok": True,
        "value": expected,
        "module": result["module"],
    }


@pytest.mark.parametrize(
    "env_name",
    ["eslint-8.3-check", "tool-4.2", "v3.12-check", "3.12rc1-check"],
)
def test_non_python_dotted_factors_are_not_claimed(
    submitted_source: Path,
    env_name: str,
) -> None:
    result = _probe(submitted_source, "extract", env_name)
    assert result["ok"]
    assert result["value"] is None


@pytest.mark.parametrize(
    ("env_name", "candidates"),
    [
        ("matrix-py3.12-2.18", ("py3.12", "2.18")),
        ("3.11-docs-3.12t", ("3.11", "3.12t")),
    ],
)
def test_multiple_python_factors_remain_an_error(
    submitted_source: Path,
    env_name: str,
    candidates: tuple[str, str],
) -> None:
    result = _probe(submitted_source, "extract", env_name)
    assert not result["ok"]
    assert result["error_type"] == "ValueError"
    assert env_name in result["message"]
    for candidate in candidates:
        assert candidate in result["message"]


def test_default_resolution_honors_ignore_policy_in_both_directions(
    submitted_source: Path,
) -> None:
    env_name = "matrix-py3.12-2.18"
    ignored = _probe(
        submitted_source,
        "default",
        env_name,
        base_pythons=["python3.11"],
        ignore=True,
    )
    assert ignored["ok"]
    assert ignored["value"] == ["python3.11"]

    strict = _probe(
        submitted_source,
        "default",
        env_name,
        base_pythons=["python3.11"],
        ignore=False,
    )
    assert not strict["ok"]
    assert strict["error_type"] == "ValueError"


def test_validation_honors_ignore_policy_in_both_directions(
    submitted_source: Path,
) -> None:
    env_name = "matrix-py3.12-2.18"
    ignored = _probe(
        submitted_source,
        "validate",
        env_name,
        base_pythons=["python3.11"],
        ignore=True,
    )
    assert ignored["ok"]
    assert ignored["value"] == ["python3.11"]

    strict = _probe(
        submitted_source,
        "validate",
        env_name,
        base_pythons=["python3.11"],
        ignore=False,
    )
    assert not strict["ok"]
    assert strict["error_type"] == "ValueError"


def test_ignore_keeps_older_single_factor_override_contract(
    submitted_source: Path,
) -> None:
    result = _probe(
        submitted_source,
        "validate",
        "lint-3.12",
        base_pythons=["python3.11"],
        ignore=True,
    )
    assert result["ok"]
    assert result["value"] == ["3.12"]


def _run_config(
    source_root: Path,
    tmp_path: Path,
    *,
    ignore: bool,
) -> subprocess.CompletedProcess[str]:
    env_name = "matrix-py3.12-2.18"
    (tmp_path / "tox.ini").write_text(
        textwrap.dedent(
            f"""
            [tox]
            env_list = {env_name}
            ignore_base_python_conflict = {str(ignore).lower()}

            [testenv]
            package = skip
            default_base_python = python3.11
            """
        ),
        encoding="utf-8",
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tox",
            "config",
            "-e",
            env_name,
            "-k",
            "base_python",
        ],
        cwd=tmp_path,
        env=_source_env(source_root),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_cli_uses_default_base_python_when_conflict_is_ignored(
    submitted_source: Path,
    tmp_path: Path,
) -> None:
    completed = _run_config(submitted_source, tmp_path, ignore=True)
    assert completed.returncode == 0, (
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    assert "base_python = python3.11" in completed.stdout


def test_cli_reports_conflict_when_ignore_is_disabled(
    submitted_source: Path,
    tmp_path: Path,
) -> None:
    completed = _run_config(submitted_source, tmp_path, ignore=False)
    assert completed.returncode != 0
    combined = f"{completed.stdout}\n{completed.stderr}"
    assert "conflicting factors" in combined
    assert "py3.12" in combined
    assert "2.18" in combined
