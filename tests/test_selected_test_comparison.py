"""Selected comparison mechanics; only tiny public fixtures and a fake sandbox run."""

import ast
import json
import os
import sys

import pytest

from patchloop.dev import test_comparison
from patchloop.dev.contracts import DevLimits, PublicTurnDecision, RequestedTool
from patchloop.dev.state import DevJournal
from patchloop.dev.test_selection import SelectedTests, selected_check
from patchloop.dev.tools import DevToolGateway
from patchloop.errors import ContractError, RecoveryError
from patchloop.git_execution import run_git
from patchloop.repair_verification import _observation, compare_selected_observations
from patchloop.runtime import repository_root
from patchloop.sandbox.public_pytest import PUBLIC_RUNNER
from patchloop.sandbox.runner import SandboxResult
from patchloop.task_loader import load_public_task

TARGET = "tests/unittest_value.py::ValueTests::test_value"
TEST_SOURCE = ("import unittest\nfrom sample import value\n\n"
               "class ValueTests(unittest.TestCase):\n"
               "    def test_value(self):\n        self.assertEqual(value, 2)\n")


class Sandbox:
    supports_execution_deadline = True

    def __init__(self, mode="assert"):
        self.mode, self.calls = mode, []

    def run_check(self, workspace, check, **kwargs):
        value = int((workspace / "sample.py").read_text().split("=")[1])
        self.calls.append((workspace, value, (workspace / "tests/unittest_value.py").read_bytes(),
                           check, kwargs))
        if self.mode == "real":
            from patchloop.sandbox.runner import LocalSandbox

            return LocalSandbox().run_check(workspace, check, **kwargs)
        if self.mode == "interrupt" and len(self.calls) == 2:
            raise KeyboardInterrupt("lost child response")
        _, _, _, marker = ast.literal_eval(check.command[-1].split("\nmain(*", 1)[1][:-1])
        failed = self.mode != "helper" and value < 2
        phase = "setup" if self.mode == "setup" and failed else "call"
        exception = ("builtins.ImportError" if self.mode == "body_error"
                     else "builtins.AssertionError")
        phases = [{"when": when, "outcome": "failed" if failed and when == phase else "passed",
                   "exception_type": exception if failed and when == phase else None,
                   "wasxfail": None, "detail": "fixture observation" if failed else None}
                  for when in ("setup", "call", "teardown")]
        report = {"exit_code": int(failed), "collection_errors": [], "collection_skips": [],
                  "tests": [{"nodeid": TARGET, "path": "tests/unittest_value.py",
                             "function": "test_value", "parameter_index": None,
                             "xfail_marked": False, "phases": phases}]}
        if self.mode == "collection" and failed:
            report["collection_errors"] = ["broken collection"]
        return SandboxResult(command=check.command, exit_code=int(failed),
                             stdout=marker + json.dumps(report), stderr="", duration_ms=1,
                             timed_out=self.mode == "timeout" and failed, truncated=False,
                             original_output_bytes=1)


@pytest.fixture
def project(tmp_path, smoke_package):
    source = tmp_path / "source"
    source.mkdir()
    (source / "tests").mkdir()
    (source / "sample.py").write_text("value = 0\n")
    (source / "tests/unittest_value.py").write_text(TEST_SOURCE)
    run_git(source, "init", "--quiet")
    run_git(source, "add", ".")
    run_git(source, "-c", "user.name=test", "-c", "user.email=test@example.invalid",
            "commit", "--quiet", "-m", "public fixture")
    task = smoke_package.public.model_copy(deep=True)
    task.constraints.allowed_paths = ["**"]
    task.constraints.forbidden_paths = []
    task.constraints.additive_test_roots = ["tests"]
    task.constraints.max_changed_files = 4
    task.constraints.max_diff_lines = 1000
    from patchloop.contracts import PublicTestSuite

    task.test_suites = [PublicTestSuite(
        id="public-pytest", test_roots=["tests"],
        environment={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                     **({"SYSTEMROOT": os.environ["SYSTEMROOT"]} if os.name == "nt" else {})},
        command=["python", "-W", "ignore", "-m", "pytest", "-q"])]
    journal = DevJournal(tmp_path / "state", "run_dev_comparison")
    gateway = DevToolGateway(workspace=source, public_task=task, sandbox=Sandbox(),
                             journal=journal, limits=DevLimits())
    return gateway


def invoke(gateway, tool, action, arguments, mode="verify"):
    return gateway.execute(RequestedTool(
        name=tool, action_id=action, arguments=arguments,
        turn_decision=PublicTurnDecision(mode=mode, basis="Check the fixture behavior.",
                                        evidence_goal="Read the exact source."
                                        if mode == "inspect" else None)))


def mutate(gateway, action, old, new, path="sample.py"):
    assert invoke(gateway, "read_file", "read-" + action,
                  {"path": path, "start_line": 1, "end_line": 100}, "inspect").status == "succeeded"
    result = invoke(gateway, "replace_text", action,
                    {"path": path, "old_text": old, "new_text": new, "occurrence": 1,
                     "hypothesis": "Change the selected observable value.",
                     "expected_behavior": "The selected assertion changes."}, "mutate")
    assert result.status == "succeeded", result.message
    return result


def comparison(gateway, baseline="original_base", mutation=None, action="compare"):
    return invoke(gateway, "run_tests", action,
                  {"suite_id": "public-pytest", "targets": [TARGET],
                   "comparison": {"baseline": baseline, "mutation_action_id": mutation}})


@pytest.mark.parametrize("mode,status", [
    ("real", "OBSERVED_FAIL_THEN_PASS"), ("helper", "PASSED_BOTH"),
])
def test_pair_distinguishes_behavior_from_unusable_failure(project, mode, status):
    gateway = project
    gateway.sandbox.mode = mode
    mutate(gateway, "repair", "value = 0", "value = 2")
    before = gateway.current_diff_hash
    result = comparison(gateway)
    assert result.status == "succeeded", result.message
    evidence = result.output["comparison"]
    assert evidence["status"] == status
    assert evidence["requirement_fit"] == "UNVERIFIED"
    assert evidence["original_requirement_credit"] is False
    assert [call[1] for call in gateway.sandbox.calls] == [0, 2]
    assert gateway.sandbox.calls[0][2] == gateway.sandbox.calls[1][2]
    assert all(call[0] != gateway.workspace for call in gateway.sandbox.calls)
    assert all(call[3].command[:3] == ["python", "-W", "ignore"]
               for call in gateway.sandbox.calls)
    assert gateway.current_diff_hash == before
    assert result.output["counts_toward_completion"] is False


@pytest.mark.parametrize("problem", ["body_error", "setup", "collection", "timeout"])
def test_unrelated_exceptions_and_execution_errors_never_gain_repair_credit(problem):
    def observed(failed):
        phases = [{"when": phase, "outcome": "failed" if failed and phase == (
            "setup" if problem == "setup" else "call") else "passed",
                   "exception_type": "builtins.ImportError" if problem == "body_error"
                   else "builtins.AssertionError", "wasxfail": None}
                  for phase in ("setup", "call", "teardown")]
        report = {"exit_code": int(failed), "collection_errors": ["configuration"]
                  if failed and problem == "collection" else [], "collection_skips": [],
                  "tests": [{"nodeid": TARGET, "path": "tests/unittest_value.py",
                             "function": "test_value", "parameter_index": None,
                             "xfail_marked": False, "phases": phases}]}
        return _observation({"exit_code": int(failed), "cleanup_failed": False,
                             "deadline_exhausted": False, "truncated": False,
                             "timed_out": failed and problem == "timeout",
                             "stdout": "MARK:" + json.dumps(report)}, "MARK:")

    result = compare_selected_observations(observed(True), observed(False), "public-pytest")
    assert result["status"] == "INCONCLUSIVE"
    assert result["original_requirement_credit"] is False


def test_pre_state_reverses_named_implementation_and_later_test_addition(project):
    first = mutate(project, "first", "value = 0", "value = 1")
    mutate(project, "repair", "value = 1", "value = 2")
    mutate(project, "added-test", TEST_SOURCE, TEST_SOURCE +
           "\n    def test_control(self):\n        self.assertGreaterEqual(value, 0)\n",
           "tests/unittest_value.py")
    result = comparison(project, "before_mutation", "repair")
    assert result.status == "succeeded", result.message
    assert [call[1] for call in project.sandbox.calls] == [1, 2]
    assert result.output["comparison"]["baseline_diff_hash"] == first.output["worktree_diff_hash"]
    assert project.sandbox.calls[0][2] == project.sandbox.calls[1][2]
    assert b"test_control" in project.sandbox.calls[0][2]
    rejected = comparison(project, "before_mutation", "added-test", "reject-test-mutation")
    assert rejected.status == "failed" and "implementation edit" in rejected.message
    assert len(project.sandbox.calls) == 2


def test_exact_finished_comparison_reuses_children_after_parent_delivery_loss(project):
    mutate(project, "repair", "value = 0", "value = 2")
    result = comparison(project)
    arguments = {"suite_id": "public-pytest", "targets": [TARGET],
                 "comparison": {"baseline": "original_base", "mutation_action_id": None}}
    replay = project._run_tests(arguments, execution_identity={
        "run_id": project.journal.run_id, "action_id": "compare"})
    assert replay == result.output
    assert len(project.sandbox.calls) == 2


def test_uncertain_child_is_never_dispatched_again(project):
    mutate(project, "repair", "value = 0", "value = 2")
    project.sandbox.mode = "interrupt"
    arguments = {"suite_id": "public-pytest", "targets": [TARGET],
                 "comparison": {"baseline": "original_base", "mutation_action_id": None}}
    selection = SelectedTests.model_validate(arguments)
    check, targets = selected_check(project.public_task.test_suites[0], selection,
                                    project.workspace, project._tracked_path)
    identity = {"run_id": project.journal.run_id, "action_id": "interrupted"}
    with pytest.raises(KeyboardInterrupt):
        test_comparison.run(project, selection, check, targets, identity)
    with pytest.raises(RecoveryError, match="uncertain"):
        test_comparison.run(project, selection, check, targets, identity)
    assert len(project.sandbox.calls) == 2


def test_nullable_comparison_preserves_legacy_identity_and_execution_cost():
    legacy = {"suite_id": "public-pytest", "targets": [TARGET]}
    assert SelectedTests.model_validate(legacy).model_dump(mode="json") == legacy
    assert SelectedTests.model_validate({**legacy, "comparison": None}).model_dump() == legacy
    assert test_comparison.execution_cost(legacy) == 1
    assert test_comparison.execution_cost({**legacy, "comparison": {}}) == 2


def test_reporter_captures_registered_unittest_method_without_filename_conventions():
    from pathlib import Path
    from types import SimpleNamespace

    from patchloop.sandbox.pytest_report import Reporter

    reporter = Reporter(None, ".")
    item = SimpleNamespace(path=Path.cwd() / "tests/unittest_value.py", name="test_value",
                           nodeid=TARGET, get_closest_marker=lambda _: None)
    reporter.pytest_collection_finish(SimpleNamespace(items=[item]))
    assert reporter.items[TARGET]["function"] == "test_value"


def test_missing_selected_method_cannot_get_paired_pass():
    observation = {"status": "COMPLETED", "tests": [{"nodeid": TARGET,
                   "path": "tests/unittest_value.py"}]}
    assert test_comparison._selected_observation(observation, [TARGET])["status"] == "COMPLETED"
    target = "tests/unittest_value.py::ValueTests::test_other"
    assert test_comparison._selected_observation(observation, [TARGET, target])[
        "missing_targets"] == [target]


def test_actual_astroid_suite_copy_wrapper_is_supported_without_changing_public_command():
    task = load_public_task(repository_root() / "tasks/dev-train/current-dev20/13/public.yaml")
    command = task.test_suites[0].command
    assert command[3] == PUBLIC_RUNNER
    before = list(command)
    selected = task.visible_checks[0].model_copy(update={"command": [*command, "--", TARGET]})
    result = test_comparison._python_command(selected, "def main(*args): pass", "marker")
    assert result[:3] == command[:3] and result[4:] == ["--", TARGET]
    assert command == before
    assert "cwd=checkout, env=env" in result[3]
    assert 'raise SystemExit(result.returncode)' in result[3]
    with pytest.raises(ContractError, match="registered public copy wrapper"):
        test_comparison._python_command(selected.model_copy(update={
            "command": [*command[:3], command[3] + "# changed", TARGET]}), "", "marker")


def test_copy_wrapper_comparison_runs_same_test_and_preserves_isolation(project):
    project.public_task.test_suites[0].command = [sys.executable, "-B", "-c", PUBLIC_RUNNER]
    project.sandbox.mode = "real"
    # The registered wrapper must preserve source priority and a writable temporary home.
    test = project.workspace / "tests/unittest_value.py"
    test.write_text(TEST_SOURCE.replace("        self.assertEqual", (
        "        import os\n        from pathlib import Path\n"
        "        self.assertFalse(Path('.patchloop-hidden').exists())\n"
        "        self.assertNotEqual(Path.cwd(), Path(os.environ['HOME']))\n"
        "        (Path(os.environ['HOME']) / 'cache').write_text('temporary')\n"
        "        self.assertEqual")))
    run_git(project.workspace, "add", ".")
    run_git(project.workspace, "-c", "user.name=test", "-c", "user.email=test@example.invalid",
            "commit", "--quiet", "-m", "public isolation assertions")
    mutate(project, "repair", "value = 0", "value = 2")
    result = comparison(project, baseline="before_mutation", mutation="repair")
    assert result.status == "succeeded", result.message
    assert result.output["comparison"]["status"] == "OBSERVED_FAIL_THEN_PASS"
    assert not result.output["comparison"]["original_requirement_credit"]
    assert [call[1] for call in project.sandbox.calls] == [0, 2]
    assert project.sandbox.calls[0][2] == project.sandbox.calls[1][2]
    assert not (project.workspace / "cache").exists()
