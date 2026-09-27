from pathlib import Path

import pytest

from diagnostics.original_pilot_packages import production_patch
from patchloop.artifacts import ArtifactStore
from patchloop.contracts import RegisteredCheck, VerdictState
from patchloop.errors import ContractError
from patchloop.sandbox.runner import SandboxResult
from patchloop.verifier.core import EvaluationEngine


@pytest.mark.parametrize(
    "code,timeout,expected",
    [
        (0, False, VerdictState.PASS),
        (1, False, VerdictState.FAIL),
        (2, False, VerdictState.ERROR),
        (None, True, VerdictState.ERROR),
    ],
)
def test_original_oracle_setup_errors_are_not_wrong_answers(tmp_path, code, timeout, expected):
    class Sandbox:
        def run_check(self, workspace, check):
            return SandboxResult(check.command, code, "", "", 1, timeout, False, 0)

    engine = EvaluationEngine(None, Sandbox(), ArtifactStore(tmp_path / "artifacts"))
    check = RegisteredCheck(id="oracle", command=["python"], infrastructure_exit_codes=[2])
    results = []
    if expected == VerdictState.ERROR:
        with pytest.raises(ContractError, match="infrastructure failure"):
            engine._run_checks("run_dev_test", tmp_path, [check], "hidden", results, [])
    else:
        engine._run_checks("run_dev_test", tmp_path, [check], "hidden", results, [])
    assert results[0].state == expected


def test_old_check_serialization_unchanged_and_codes_do_not_overlap():
    check = RegisteredCheck(id="old", command=["python"])
    assert "infrastructure_exit_codes" not in check.model_dump()
    with pytest.raises(ValueError, match="disjoint"):
        RegisteredCheck(id="bad", command=["python"], infrastructure_exit_codes=[0])


def test_reference_projection_removes_tests_without_using_test_assertions():
    patch = "diff --git a/lib/core.py b/lib/core.py\nsource\n"
    tests = "diff --git a/lib/tests/test_core.py b/lib/tests/test_core.py\nprivate\n"
    assert production_patch(patch + tests, "lib") == patch


def test_task_public_input_has_no_hidden_assets():
    from patchloop.runtime import repository_root
    from patchloop.task_loader import load_task_package

    for name in ("original-toqito-1538", "original-montepy-933", "original-darts-3065"):
        package = load_task_package(repository_root() / "tasks/dev-train" / name)
        check = package.public.visible_checks[0]
        assert "oracle.json" not in str(check.command)
        assert "test_patch" not in package.public.model_dump_json()
        assert package.public.constraints.forbidden_paths == [
            "tests/**",
            "**/tests/**",
            ".patchloop-hidden/**",
        ]
        assert Path(package.root, "hidden", "run_oracle.py").is_file()
