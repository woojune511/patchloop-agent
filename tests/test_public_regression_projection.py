"""Public expectation projection composes with admitted regression additions."""

import os
import subprocess
import sys

import pytest

from patchloop.contracts import TaskConstraints
from patchloop.git_execution import run_git
from patchloop.runtime import repository_root
from patchloop.sandbox.public_pytest import PVLIB_REINDL_PUBLIC_RUNNER
from patchloop.task_loader import load_public_task
from patchloop.test_additions import UnsupportedTestChange
from patchloop.verifier.policy import validate_test_addition

TEST_PATH = "pvlib/tests/test_irradiance.py"
OLD_ASSERTION = "    assert_allclose(result, [np.nan, 27.9412, 104.1317, 34.1663], atol=1e-4)"
# The public base function is retained verbatim. Small local doubles exercise its
# registered projection without installing pvlib or its scientific dependencies.
TARGET = """def test_reindl(irrad_data, ephem_data, dni_et):
    result = irradiance.reindl(
        40, 180, irrad_data['dhi'], irrad_data['dni'], irrad_data['ghi'],
        dni_et, ephem_data['apparent_zenith'], ephem_data['azimuth'])
    # values from matlab 1.4 code
    assert_allclose(result, [np.nan, 27.9412, 104.1317, 34.1663], atol=1e-4)
"""
BASE = """import pytest
from types import SimpleNamespace

class Array(list):
    def to_numpy(self):
        return self
    def __ne__(self, other):
        return [value != other for value in self]
    def __getitem__(self, index):
        if isinstance(index, list):
            return [value for value, keep in zip(self, index) if keep]
        return super().__getitem__(index)

np = SimpleNamespace(nan=None, asarray=Array, array=Array)
irradiance = SimpleNamespace(reindl=lambda *args: [0, 27.9412, 104.1317, 34.1663])

def assert_allclose(actual, expected, **kwargs):
    assert list(actual) == list(expected)

@pytest.fixture
def irrad_data():
    return {'ghi': Array([0, 1, 1, 1]), 'dhi': 1, 'dni': 1}

@pytest.fixture
def ephem_data():
    return {'apparent_zenith': 1, 'azimuth': 1}

@pytest.fixture
def dni_et():
    return 1

@pytest.mark.parametrize('value', [1])
def test_existing(value):
    assert value > 0

class TestExisting:
    def test_original(self):
        assert True

""" + TARGET
CONSTRAINTS = TaskConstraints(additive_test_roots=["pvlib/tests"])


@pytest.fixture
def projected_source(tmp_path):
    path = tmp_path / TEST_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(BASE.encode())
    run_git(tmp_path, "init")
    run_git(tmp_path, "config", "core.autocrlf", "false")
    run_git(tmp_path, "add", TEST_PATH)
    run_git(tmp_path, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-m", "public base")
    return path


def run_projected(workspace, selection=TEST_PATH, runner=PVLIB_REINDL_PUBLIC_RUNNER):
    return subprocess.run(
        [sys.executable, "-B", "-c", runner, selection], cwd=workspace,
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )


def test_current_and_source_public_commands_match_projection_builder():
    root = repository_root() / "tasks/dev-train"
    for relative in ("current-dev20/3", "swebench-lite-dev-pvlib-pvlib-python-1154"):
        public = load_public_task(root / relative / "public.yaml")
        assert public.visible_checks[0].command[3] == PVLIB_REINDL_PUBLIC_RUNNER
        for suite in public.test_suites:
            assert suite.command[3] == PVLIB_REINDL_PUBLIC_RUNNER


def test_added_function_runs_and_its_failure_is_preserved(tmp_path, projected_source):
    candidate = BASE + "\ndef test_added():\n    assert False, 'ADDED_TEST_EXECUTED'\n"
    validate_test_addition(tmp_path, TEST_PATH, candidate.encode(), CONSTRAINTS)
    projected_source.write_bytes(candidate.encode())
    result = run_projected(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 failed, 3 passed" in result.stdout
    assert "ADDED_TEST_EXECUTED" in result.stdout
    assert projected_source.read_bytes() == candidate.encode()
    selected = run_projected(tmp_path, TEST_PATH + "::test_added")
    assert selected.returncode == 1 and "1 failed" in selected.stdout


@pytest.mark.parametrize("candidate,passed", [
    (BASE + "\ndef test_added():\n    assert True\n", 4),
    (BASE.replace("'value', [1]", "'value', [1, 2]"), 4),
    (BASE + "\nclass TestAdded:\n    def test_added(self):\n        assert True\n", 4),
    (BASE.replace("class TestExisting:\n", "class TestExisting:\n"
                  "    def test_added(self):\n        assert True\n"), 4),
    (BASE + "\ndef test_same_assertion():\n"
            "    result = [None, 27.9412, 104.1317, 34.1663]\n" + OLD_ASSERTION + "\n", 4),
], ids=["function", "literal-case", "class", "method", "same-anchor-elsewhere"])
def test_admitted_additions_survive_target_projection(
    tmp_path, projected_source, candidate, passed,
):
    validate_test_addition(tmp_path, TEST_PATH, candidate.encode(), CONSTRAINTS)
    projected_source.write_bytes(candidate.encode())
    result = run_projected(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{passed} passed" in result.stdout
    assert projected_source.read_bytes() == candidate.encode()


@pytest.mark.parametrize("candidate", [
    BASE.replace("27.9412, 104.1317, 34.1663], atol=1e-4)",
                 "27.9412, 104.1317, 34.1663], atol=1)"),
    BASE + "\ndef test_reindl():\n    assert True\n",
    BASE + "\nasync def test_reindl():\n    assert True\n",
    BASE + "\nif True:\n    def test_reindl():\n        assert True\n",
    BASE.replace("def test_reindl(", "def test_other("),
    BASE.replace(OLD_ASSERTION, OLD_ASSERTION.lstrip()),
], ids=["assertion", "duplicate", "async-duplicate", "conditional-shadow",
        "renamed", "moved-anchor"])
def test_projection_rejects_target_drift_before_pytest(tmp_path, projected_source, candidate):
    projected_source.write_bytes(candidate.encode())
    (tmp_path / "pytest.py").write_text("print('PYTEST_MUST_NOT_RUN')\n")
    result = run_projected(tmp_path)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "public regression" in result.stdout
    assert "PYTEST_MUST_NOT_RUN" not in result.stdout
    assert projected_source.read_bytes() == candidate.encode()


def test_projection_requires_anchor_inside_matching_target(tmp_path, projected_source):
    candidate = BASE.replace("atol=1e-4)", "atol = 1e-4)")
    candidate += "\ndef test_added():\n    assert True\n"
    validate_test_addition(tmp_path, TEST_PATH, candidate.encode(), CONSTRAINTS)
    projected_source.write_bytes(candidate.encode())
    (tmp_path / "pytest.py").write_text("print('PYTEST_MUST_NOT_RUN')\n")
    result = run_projected(tmp_path)
    assert result.returncode == 2
    assert "public regression anchor mismatch" in result.stdout
    assert "PYTEST_MUST_NOT_RUN" not in result.stdout


def test_projection_keeps_nonzero_ghi_regression_expectations(tmp_path, projected_source):
    candidate = BASE.replace("lambda *args: [0, 27.9412", "lambda *args: [0, 0")
    projected_source.write_bytes(candidate.encode())
    result = run_projected(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 failed, 2 passed" in result.stdout


@pytest.mark.parametrize("candidate", [
    BASE.replace("import pytest", "import pytest\nimport os"),
    BASE.replace("return {'apparent_zenith': 1", "return {'apparent_zenith': 2"),
    BASE.replace("assert value > 0", "assert True"),
    BASE.replace("27.9412, 104.1317, 34.1663], atol=1e-4)",
                 "27.9412, 104.1317, 34.1663], atol=1)"),
], ids=["import", "fixture", "other-test", "projection-target"])
def test_shared_admission_rejects_original_setup_or_assertion_changes(
    tmp_path, projected_source, candidate,
):
    candidate += "\ndef test_added():\n    assert True\n"
    with pytest.raises(UnsupportedTestChange):
        validate_test_addition(tmp_path, TEST_PATH, candidate.encode(), CONSTRAINTS)
