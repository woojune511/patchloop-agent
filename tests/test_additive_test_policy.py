"""Added tests remain executable while original regression assertions are immutable."""

import pytest

from patchloop.contracts import TaskConstraints
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.verifier.policy import original_test_view, verify_test_tampering

BASE = b"def test_original():\n    assert 1 == 1\n"
ADDED = BASE + b"\ndef test_added():\n    assert 2 == 2\n"


def source(tmp_path):
    run_git(tmp_path, "init")
    run_git(tmp_path, "config", "user.email", "test@example.invalid")
    run_git(tmp_path, "config", "user.name", "Test")
    run_git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_api.py").write_bytes(BASE)
    run_git(tmp_path, "add", ".")
    run_git(tmp_path, "commit", "-m", "base")
    return tmp_path / "tests/test_api.py"


def test_policy_opt_in_and_restored_original_view(tmp_path):
    path = source(tmp_path)
    path.write_bytes(ADDED)
    diff = WorkspaceManager.diff_summary(tmp_path)
    assert not verify_test_tampering(diff).passed
    constraints = TaskConstraints(additive_test_roots=["tests"])
    result = verify_test_tampering(diff, constraints, tmp_path)
    assert result.passed
    with pytest.raises(RuntimeError), original_test_view(tmp_path, result):
        assert path.read_bytes() == BASE
        raise RuntimeError("simulated evaluator failure")
    assert path.read_bytes() == ADDED
    assert WorkspaceManager.diff_summary(tmp_path).patch_hash == diff.patch_hash


@pytest.mark.parametrize(
    "candidate",
    [
        BASE.replace(b"1 == 1", b"True"),
        b"import os\n" + ADDED,
        b"def test_replacement():\n    assert True\n",
        BASE + b"\ndef helper():\n    pass\n",
    ],
)
def test_original_tests_and_module_setup_cannot_change(tmp_path, candidate):
    path = source(tmp_path)
    path.write_bytes(candidate)
    result = verify_test_tampering(
        WorkspaceManager.diff_summary(tmp_path),
        TaskConstraints(additive_test_roots=["tests"]),
        tmp_path,
    )
    assert not result.passed


def test_empty_policy_preserves_old_serialization():
    assert "additive_test_roots" not in TaskConstraints().model_dump(mode="json")
    for invalid in [".", "../tests", ".patchloop-hidden", "tests/*"]:
        with pytest.raises((ValueError, ContractError)):
            TaskConstraints(additive_test_roots=[invalid])


def test_gateway_rejects_rewrite_before_mutation_and_accepts_new_test(gateway_factory):
    gateway, _, workspace = gateway_factory()
    directory = workspace / "tests"
    directory.mkdir(exist_ok=True)
    path = directory / "test_addition.py"
    path.write_bytes(BASE)
    run_git(workspace, "add", "tests/test_addition.py")
    run_git(
        workspace,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        "test fixture",
    )
    gateway.public_task.constraints = TaskConstraints(
        allowed_paths=["**"], additive_test_roots=["tests"], max_diff_lines=1000
    )
    gateway.execute(
        RequestedTool(
            name="read_file",
            action_id="read",
            arguments={"path": "tests/test_addition.py", "start_line": 1, "end_line": 20},
            turn_decision=PublicTurnDecision(
                mode="inspect", basis="Read test anchor", evidence_goal="Locate preserved tests"
            ),
        )
    )
    args = {
        "path": "tests/test_addition.py",
        "old_text": BASE.decode(),
        "new_text": BASE.decode().replace("1 == 1", "True"),
        "occurrence": 1,
        "hypothesis": "test",
        "expected_behavior": "test",
        "causal_revision": None,
    }
    with pytest.raises(ContractError, match="preserve existing"):
        gateway._validate_replacement_intent(args)
    assert path.read_bytes() == BASE
    args["new_text"] = ADDED.decode()
    assert gateway._validate_replacement_intent(args).after_bytes == ADDED
