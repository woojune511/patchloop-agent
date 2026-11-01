"""Added tests remain executable while original regression assertions are immutable."""

import stat

import pytest

from patchloop.contracts import TaskConstraints
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.repository import WorkspaceManager
from patchloop.test_additions import UnsupportedTestChange
from patchloop.verifier.policy import (
    original_test_view,
    validate_test_addition,
    verify_test_tampering,
)

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


def test_new_test_module_is_absent_during_grading_and_restored_after_exception(tmp_path):
    original = source(tmp_path)
    original.write_bytes(ADDED)
    created = tmp_path / "tests/test_new.py"
    content = (b'"""New public regression.\r\n"""\r\nimport math\r\n'
               b'def test_new():\r\n    assert math.sqrt(4) == 2\r\n')
    created.write_bytes(content)
    run_git(tmp_path, "add", "--intent-to-add", "--", "tests/test_new.py")
    modes = {path: stat.S_IMODE(path.stat().st_mode) for path in (original, created)}
    diff = WorkspaceManager.diff_summary(tmp_path)
    index = run_git(tmp_path, "ls-files", "--stage").stdout
    result = verify_test_tampering(diff, TaskConstraints(additive_test_roots=["tests"]), tmp_path)
    assert result.passed, result.violations
    with (pytest.raises(RuntimeError, match="simulated evaluator failure"),
          original_test_view(tmp_path, result)):
        assert original.read_bytes() == BASE
        assert not created.exists()
        assert not WorkspaceManager.diff_summary(tmp_path).changed_files
        raise RuntimeError("simulated evaluator failure")
    assert original.read_bytes() == ADDED
    assert created.read_bytes() == content
    assert {path: stat.S_IMODE(path.stat().st_mode) for path in modes} == modes
    restored = WorkspaceManager.diff_summary(tmp_path)
    assert restored.patch == diff.patch and restored.patch_hash == diff.patch_hash
    assert run_git(tmp_path, "ls-files", "--stage").stdout == index


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


@pytest.mark.parametrize("path, roots, reason", [
    ("tests/fixtures/case.yaml", ["tests"], "only Python (.py) files"),
    ("tests/test_new.py", [], "declared additive test root"),
    ("tests/fixtures/case.yaml", ["tests_other"], "declared additive test root"),
])
def test_additive_rejection_distinguishes_file_type_from_missing_root(
    tmp_path, path, roots, reason,
):
    source(tmp_path)
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"case: value\n")
    run_git(tmp_path, "add", "--intent-to-add", "--", path)
    constraints = TaskConstraints(additive_test_roots=roots)
    with pytest.raises(UnsupportedTestChange) as rejected:
        validate_test_addition(tmp_path, path, target.read_bytes(), constraints)
    assert reason in str(rejected.value)
    if roots:
        result = verify_test_tampering(
            WorkspaceManager.diff_summary(tmp_path), constraints, tmp_path,
        )
        assert not result.passed
        assert reason in result.violations[0]


def test_exact_original_yaml_restoration_remains_allowed(tmp_path):
    source(tmp_path)
    path = "tests/case.yaml"
    original = b"case: original\n"
    (tmp_path / path).write_bytes(original)
    run_git(tmp_path, "add", "--", path)
    run_git(tmp_path, "commit", "-m", "original YAML fixture")
    constraints = TaskConstraints(additive_test_roots=["tests"])
    validate_test_addition(tmp_path, path, original, constraints)
    with pytest.raises(UnsupportedTestChange, match="only Python"):
        validate_test_addition(tmp_path, path, b"case: changed\n", constraints)


def test_gateway_reports_unsupported_fixture_without_applying_batch(gateway_factory):
    gateway, journal, workspace = gateway_factory()
    gateway.public_task.constraints = TaskConstraints(
        allowed_paths=["**"], additive_test_roots=["tests"], max_diff_lines=1000
    )
    fixture = workspace / "tests/case.yaml"
    original = "case: original\n"
    fixture.write_bytes(original.encode("utf-8"))
    run_git(workspace, "add", "tests/case.yaml")
    run_git(workspace, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-m", "original YAML fixture")
    observed = gateway.execute(RequestedTool(
        name="read_file", action_id="read-yaml", arguments={
            "path": "tests/case.yaml", "start_line": None, "end_line": None,
        }, turn_decision=PublicTurnDecision(
            mode="inspect", basis="Read the existing fixture.", evidence_goal="Find its test case.",
        ),
    ))
    assert observed.status == "succeeded"
    baseline = gateway.current_diff.patch
    call = RequestedTool(name="edit_files", action_id="yaml-fixture", arguments={
        "edits": [
            {"path": "helper.py", "old_text": None, "new_text": "VALUE = 1\n", "occurrence": 1},
            {"path": "tests/case.yaml", "old_text": original, "new_text": "case: value\n",
             "occurrence": 1},
        ],
        "undo_action_id": None,
        "hypothesis": "Add a helper and a regression fixture.",
        "expected_behavior": "Keep existing tests and add a new case.",
    })
    result = gateway.execute(call)
    assert result.status == "failed" and result.error_code == "CONTRACT_ERROR"
    assert "only Python (.py) files" in result.message
    assert "declared additive test root" not in result.message
    assert result.output["mutation_failure"]["rolled_back"]
    assert gateway.accepted_mutations == 0 and gateway.current_diff.patch == baseline
    assert not (workspace / "helper.py").exists()
    assert fixture.read_text(encoding="utf-8") == original
    journal_bytes = journal.path.read_bytes()
    replay = gateway.execute(call)
    assert replay.replayed and replay.message == result.message
    assert journal.path.read_bytes() == journal_bytes and gateway.accepted_mutations == 0


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
    args["new_text"] = "import math\n" + ADDED.decode()
    rejected = gateway.execute(RequestedTool(
        name="replace_text", action_id="shared-import", arguments=dict(args),
    ))
    assert rejected.status == "failed"
    assert "imports inside the new test function" in rejected.message
    assert path.read_bytes() == BASE and gateway.accepted_mutations == 0

    candidate = BASE + b"\ndef test_added():\n    import math\n    assert math.sqrt(4) == 2\n"
    args["new_text"] = candidate.decode()
    request = RequestedTool(name="replace_text", action_id="local-import", arguments=dict(args))
    accepted = gateway.execute(request)
    assert accepted.status == "succeeded", accepted.message
    assert path.read_bytes() == candidate and gateway.accepted_mutations == 1
    replayed = gateway.execute(request)
    assert replayed.replayed and replayed.output == accepted.output
    assert path.read_bytes() == candidate and gateway.accepted_mutations == 1
