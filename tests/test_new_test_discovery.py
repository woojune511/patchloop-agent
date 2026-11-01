"""New regression files must survive ordinary directory discovery."""

from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest
from test_file_edits import batch, edit, expanded_gateway, restart

from patchloop.contracts import PublicTestSuite
from patchloop.dev.file_transaction import FileChange
from patchloop.dev.test_discovery import filename_rule, validate_new_test_names
from patchloop.git_execution import run_git


@pytest.mark.parametrize("config,content,patterns", [
    ("pytest.ini", "[pytest]\npython_files = check_*.py\n", ["check_*.py"]),
    (".pytest.ini", "", ["test_*.py", "*_test.py"]),
    ("tox.ini", "[pytest]\npython_files = *_test.py\n", ["*_test.py"]),
    ("setup.cfg", "[tool:pytest]\npython_files = *test_*.py\n", ["*test_*.py"]),
    ("pyproject.toml", '[tool.pytest.ini_options]\npython_files = ["spec_*.py"]\n',
     ["spec_*.py"]),
])
def test_project_patterns_and_precedence(config, content, patterns):
    files = {config: content.encode()}
    rule = filename_rule(".", set(files), files.__getitem__)
    assert rule["python_files"] == patterns and rule["config_path"] == config
    assert rule["config_hash"].startswith("sha256:")
    files["pytest.ini"] = b"[pytest]\npython_files = primary_*.py\n"
    assert filename_rule(".", set(files), files.__getitem__)["python_files"] == ["primary_*.py"]


@pytest.mark.parametrize("files", [
    {"pytest.ini": b"[pytest\n"},
    {"pytest.ini": b"[pytest]\npython_files = " + b"a" * 65_536},
    {"pytest.ini": b"[pytest]\naddopts = -o python_files=*.py\n"},
    {"pyproject.toml": b'[tool.pytest]\npython_files = ["*.py"]\n'},
    {"pytest.toml": b""},
])
def test_unknown_configuration_is_not_a_guessed_rejection(files):
    assert filename_rule(".", set(files), files.__getitem__) is None


def test_default_and_parent_settings_are_bounded_to_public_repository():
    assert filename_rule("tests", set(), lambda _: pytest.fail("unexpected read")) == {
        "python_files": ["test_*.py", "*_test.py"], "config_path": None, "config_hash": None,
    }
    files = {"setup.cfg": b"[tool:pytest]\npython_files = *_test.py\n",
             "pyproject.toml": b"[tool.other]\nvalue = 1\n"}
    assert filename_rule("tests", set(files), files.__getitem__)["config_path"] == "setup.cfg"


def test_transaction_changing_config_does_not_apply_the_old_naming_rule():
    # The pure filename check must defer to execution, not reject by stale config.
    gateway = SimpleNamespace(_tracked_paths=lambda: pytest.fail("old config must not be read"))
    validate_new_test_names(gateway, [
        FileChange("pytest.ini", b"[pytest]\n", b"[pytest]\npython_files = check_*.py\n"),
        FileChange("tests/check_value.py", None, b"def test_value():\n    assert True\n"),
    ])


def test_misnamed_file_is_rejected_atomically_then_corrected_file_is_discovered(gateway_factory):
    gateway, journal, workspace = expanded_gateway(gateway_factory)
    (workspace / "tox.ini").write_text("[pytest]\npython_files = *_test.py\n", encoding="utf-8")
    run_git(workspace, "add", "tox.ini")
    run_git(workspace, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-m", "Public pytest naming configuration")
    gateway.public_task.constraints.allowed_paths.append("tests/**")
    gateway.public_task.constraints.forbidden_paths.remove("tests/**")
    gateway.public_task.constraints.additive_test_roots = ["tests"]
    # Match the registered inline wrapper contract used by the real regression.
    gateway.public_task.test_suites = [PublicTestSuite(
        id="public-tests", runner="pytest", test_roots=["tests"],
        command=["python", "-B", "-c", "import pytest,sys; sys.exit(pytest.main(sys.argv[1:]))"],
    )]
    gateway = restart(gateway)
    before = gateway.current_diff_hash
    test = "def test_detect_remaining_defect():\n    assert False, 'original obligation'\n"
    proposed = batch("bad-name", [edit("tests/regression_case.py", None, test),
                                   edit("mini_data_utils/new_helper.py", None, "VALUE = 1\n")])
    result = gateway.execute(proposed)
    assert result.status == "failed", result.message
    assert "python_files" in result.message and "*_test.py" in result.message
    assert gateway.current_diff_hash == before and gateway.accepted_mutations == 0
    assert not (workspace / "mini_data_utils/new_helper.py").exists()
    assert not (workspace / "tests/regression_case.py").exists()
    durable = journal.path.read_bytes()
    repeated = restart(gateway).execute(proposed)
    assert repeated.replayed and journal.path.read_bytes() == durable

    # Show why direct selection is insufficient, independently of admission.
    folder = workspace.parent / "discovery-proof"
    folder.mkdir()
    (folder / "tox.ini").write_bytes((workspace / "tox.ini").read_bytes())
    (folder / "regression_case.py").write_text(test, encoding="utf-8")
    explicit = subprocess.run([sys.executable, "-m", "pytest", "-q", "regression_case.py"],
                              cwd=folder, capture_output=True, text=True, check=False)
    ordinary = subprocess.run([sys.executable, "-m", "pytest", "-q", "."], cwd=folder,
                              capture_output=True, text=True, check=False)
    assert explicit.returncode == 1 and "1 failed" in explicit.stdout
    assert ordinary.returncode == 5 and "no tests ran" in ordinary.stdout

    accepted = gateway.execute(batch(
        "good-name", [edit("tests/regression_case_test.py", None, test)],
    ))
    assert accepted.status == "succeeded", accepted.message
    checked = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=workspace,
                             capture_output=True, text=True, check=False)
    assert checked.returncode == 1 and "original obligation" in checked.stdout
    assert "1 failed" in checked.stdout
    assert "test_discovery" not in json.dumps(accepted.output)  # Filename match is not coverage.
