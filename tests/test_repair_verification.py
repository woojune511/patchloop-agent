from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from patchloop import repair_verification as verification
from patchloop.cli import app
from patchloop.dev.state import DevJournal
from patchloop.errors import ContractError
from patchloop.git_execution import run_git
from patchloop.repair import load_repair_request
from patchloop.sandbox.runner import LocalSandbox, SandboxResult
from patchloop.test_additions import UnsupportedTestChange, added_tests

BASE_TEST = """import pytest
from sample import resolve

@pytest.mark.parametrize("env,expected", [({"b": "c"}, "c")])
def test_default(env, expected):
    assert resolve(env) == expected
"""
BASE_SOURCE = 'def resolve(env):\n    return env.get("b", "d")\n'
FIXED_SOURCE = 'def resolve(env):\n    return env.get("b") or "d"\n'


@pytest.fixture
def project(tmp_path):
    source = tmp_path / "source"
    (source / "tests").mkdir(parents=True)
    (source / "sample.py").write_text(BASE_SOURCE)
    (source / "tests/test_sample.py").write_text(BASE_TEST)
    (source / "tests/conftest.py").write_text("")
    (source / "pytest.ini").write_text("[pytest]\n")
    run_git(source, "init", "-q")
    run_git(source, "add", ".")
    run_git(
        source,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "base",
    )
    task = {
        "schema_version": "repair-task-v1",
        "task_id": "public-test-addition",
        "repository": {
            "url": "https://example.invalid/repo.git",
            "base_commit": run_git(source, "rev-parse", "HEAD").stdout.strip(),
        },
        "issue": {"title": "Empty fallback", "description": "Use the default for an empty value"},
        "constraints": {"allowed_paths": ["**"], "max_diff_lines": 200},
        "visible_checks": [
            {
                "id": "public-tests",
                "command": ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
                "timeout_seconds": 10,
                "environment": {
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                    **({"SYSTEMROOT": os.environ["SYSTEMROOT"]} if os.name == "nt" else {}),
                },
            }
        ],
    }
    (tmp_path / "public.yaml").write_text(yaml.safe_dump(task))
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "task": "public.yaml",
                "source": "source",
                "state_root": "state",
                "provider": "mock",
                "model": "mock-dev",
                "sandbox": {"backend": "local"},
                "limits": {"wall_time_seconds": 60},
            }
        )
    )
    return request, source


def make_patch(project, test_source=None, implementation=FIXED_SOURCE, extras=None):
    request, source = project
    if test_source is None:
        test_source = BASE_TEST.replace('({"b": "c"}, "c")', '({"b": "c"}, "c"), ({"b": ""}, "d")')
    (source / "sample.py").write_text(implementation)
    (source / "tests/test_sample.py").write_text(test_source)
    for name, text in (extras or {}).items():
        (source / name).write_text(text)
    patch = request.parent / "returned.patch"
    patch.write_bytes(run_git(source, "diff", "--binary", text=False).stdout)
    run_git(source, "restore", ".")
    return patch


def test_cli_identical_parameter_case_fails_then_passes_and_preserves_source(project, monkeypatch):
    from patchloop.dev import runner

    monkeypatch.setattr(
        runner, "_run_invocation", lambda *a, **kw: pytest.fail("model loop called")
    )
    request, source = project
    patch = make_patch(project)
    output = CliRunner().invoke(
        app, ["repair-verify", "--request", str(request), "--patch", str(patch)]
    )
    assert output.exit_code == 0, output.stdout
    result = json.loads(output.stdout)
    assert result["status"] == "COMPLETE"
    assert result["comparison"]["status"] == "OBSERVED_FAIL_THEN_PASS"
    assert result["acceptance"] == "NOT_RUN" and result["requirement_fit"] == "NOT_ASSESSED"
    assert result["model_calls"] == 0
    assert [row["exit_code"] for row in result["checks"]] == [0, 1, 0]
    before, after = [Path(result["workspaces"][phase]) for phase in ("base_with_tests", "patched")]
    assert (before / "sample.py").read_text() == BASE_SOURCE
    assert (after / "sample.py").read_text() == FIXED_SOURCE
    assert (before / "tests/test_sample.py").read_bytes() == (
        after / "tests/test_sample.py"
    ).read_bytes()
    assert not run_git(source, "status", "--porcelain").stdout
    events = DevJournal(request.parent / "state", result["run_id"]).events()
    assert [e["event_type"] for e in events].count("verification_check_finished") == 3
    assert events[-1]["event_type"] == "verification_finished"
    stored = json.loads(Path(result["result_artifact"]["path"]).read_text())
    assert stored["comparison"] == result["comparison"]


@pytest.mark.parametrize(
    ("addition", "expected_state", "comparison"),
    [
        (
            'def test_added():\n    assert resolve({"b": ""}) == "d"\n',
            "TEST_FAILED",
            "OBSERVED_FAIL_THEN_PASS",
        ),
        ('def test_added():\n    assert resolve({"b": "c"}) == "c"\n', "PASSED", "PASSED_BOTH"),
        ('def test_added():\n    pytest.skip("unsupported platform")\n', "SKIPPED", "INCONCLUSIVE"),
        (
            "def test_added(missing_fixture):\n    assert False\n",
            "SETUP_OR_TEARDOWN_ERROR",
            "INCONCLUSIVE",
        ),
        (
            "@pytest.mark.xfail\ndef test_added():\n    assert False\n",
            "XFAIL_OR_XPASS",
            "INCONCLUSIVE",
        ),
    ],
)
def test_test_outcomes_are_distinct(project, addition, expected_state, comparison):
    request, _ = project
    result = verification.verify_repair(request, make_patch(project, BASE_TEST + "\n" + addition))
    assert result["status"] == "COMPLETE", result
    before = result["checks"][1]["observation"]
    assert before["tests"][0]["status"] == expected_state
    assert result["comparison"]["status"] == comparison


def test_collection_error_is_not_test_failure(project):
    request, _ = project
    tests = BASE_TEST + '\n@pytest.mark.parametrize("x", [1 / 0])\ndef test_added(x): pass\n'
    result = verification.verify_repair(request, make_patch(project, tests))
    assert result["checks"][1]["observation"]["status"] == "COLLECTION_ERROR"
    assert result["comparison"]["status"] == "INCONCLUSIVE"


def test_added_case_not_selected_is_not_pass(project):
    request, _ = project
    public = request.parent / "public.yaml"
    task = yaml.safe_load(public.read_text())
    task["visible_checks"][0]["command"].extend(["-k", "not test_added"])
    public.write_text(yaml.safe_dump(task))
    patch = make_patch(project, BASE_TEST + "\ndef test_added(): assert False\n")
    result = verification.verify_repair(request, patch)
    assert result["comparison"]["status"] == "NOT_COLLECTED"


@pytest.mark.parametrize(
    "extra",
    [
        {"tests/conftest.py": "import pytest\n"},
        {"pytest.ini": "[pytest]\naddopts=-x\n"},
    ],
)
def test_fixture_and_configuration_changes_are_reported_unsupported(project, extra):
    request, _ = project
    result = verification.verify_repair(request, make_patch(project, extras=extra))
    assert result["status"] == "UNSUPPORTED"
    assert next(iter(extra)) in result["changed_files"]
    assert result["checks"] == []


@pytest.mark.parametrize(
    "test_source",
    [
        BASE_TEST.replace("assert resolve(env) == expected", "assert True"),
        BASE_TEST.replace('({"b": "c"}, "c")', '({"b": ""}, "d")'),
        BASE_TEST.replace("import pytest", "import pytest\nimport os"),
        BASE_TEST + "\n@pytest.fixture\ndef test_added(): return 1\n",
    ],
)
def test_unsafe_separation_does_not_run_checks(project, test_source):
    request, _ = project
    result = verification.verify_repair(request, make_patch(project, test_source))
    assert result["status"] == "UNSUPPORTED", result
    assert result["checks"] == [] and result["comparison"]["status"] == "NOT_RUN"


def test_no_tests_or_no_pytest_is_unsupported(project):
    request, _ = project
    result = verification.verify_repair(request, make_patch(project, BASE_TEST))
    assert result["status"] == "UNSUPPORTED"
    public = request.parent / "public.yaml"
    task = yaml.safe_load(public.read_text())
    task["visible_checks"][0]["command"] = ["python", "-c", "print('ok')"]
    public.write_text(yaml.safe_dump(task))
    result = verification.verify_repair(request, make_patch(project))
    assert result["status"] == "UNSUPPORTED"


def test_invalid_patch_records_error_without_model(project):
    request, _ = project
    patch = request.parent / "bad.patch"
    patch.write_text("not a patch")
    result = verification.verify_repair(request, patch)
    assert result["status"] == "ERROR" and result["checks"] == []
    assert result["result_artifact"]


@pytest.mark.parametrize(
    "body",
    [
        "diff --git a/tests/test_old.py b/tests/test_new.py\n"
        "similarity index 100%\nrename from tests/test_old.py\nrename to tests/test_new.py\n",
        "diff --git a/tests/test_new.py b/tests/test_new.py\nnew file mode 100644\n",
        "diff --git a/sample.py b/sample.py\nold mode 100644\nnew mode 100755\n",
    ],
)
def test_unsupported_file_operations_are_not_executed(project, body):
    request, _ = project
    patch = request.parent / "returned.patch"
    patch.write_text(body)
    result = verification.verify_repair(request, patch)
    assert result["status"] == "UNSUPPORTED"
    assert result["checks"] == [] and result["patch"]


@pytest.mark.parametrize(
    ("changes", "state"),
    [
        ({"timed_out": True}, "TIMEOUT"),
        ({"truncated": True}, "INCOMPLETE_OUTPUT"),
        ({"cleanup_failed": True}, "EXECUTION_ERROR"),
        ({"stdout": "incomplete pytest output"}, "INVALID_REPORT"),
    ],
)
def test_execution_failures_are_not_success(project, monkeypatch, changes, state):
    request, _ = project
    raw = SandboxResult([], 0, "", "", 1, False, False, 0)
    monkeypatch.setattr(LocalSandbox, "run_check", lambda *a, **kw: replace(raw, **changes))
    result = verification.verify_repair(request, make_patch(project))
    assert result["checks"][0]["observation"]["status"] == state
    assert result["comparison"]["status"] != "OBSERVED_FAIL_THEN_PASS"


def test_no_case_removed_or_reordered_in_parametrization():
    old = BASE_TEST.replace('({"b": "c"}, "c")', "(1, 1), (2, 2)")
    new = old.replace("(1, 1), (2, 2)", "(2, 2), (1, 1), (3, 3)")
    with pytest.raises(UnsupportedTestChange):
        added_tests(old.encode(), new.encode(), "tests/test_example.py")


def test_request_loader_does_not_read_credentials(project):
    request, _ = project
    raw = json.loads(request.read_text())
    raw.update(
        provider="openai",
        model="gpt-5.4-mini-2026-03-17",
        max_cost_usd="3",
        env_file="missing.env",
        sandbox={
            "backend": "docker",
            "image": "test@sha256:" + "a" * 64,
            "image_digest": "sha256:" + "a" * 64,
        },
    )
    request.write_text(json.dumps(raw))
    assert load_repair_request(request).env_file == request.parent / "missing.env"


def test_original_public_failures_remain_visible_and_nonpytest_check_is_reused(project):
    request, _ = project
    public = request.parent / "public.yaml"
    task = yaml.safe_load(public.read_text())
    task["visible_checks"].append(
        {"id": "other-public", "command": ["python", "-c", "raise SystemExit(7)"]}
    )
    public.write_text(yaml.safe_dump(task))
    result = verification.verify_repair(request, make_patch(project))
    assert result["comparison"]["status"] == "OBSERVED_FAIL_THEN_PASS"
    other = [r for r in result["checks"] if r["check_id"] == "other-public"]
    assert len(other) == 3 and all(r["exit_code"] == 7 for r in other)
    assert all(r["observation"]["status"] == "NONZERO_EXIT" for r in other)
    assert result["acceptance"] == "NOT_RUN"


def test_missing_prepared_environment_is_error_and_does_not_run_checks(project, monkeypatch):
    request, _ = project

    def missing(*args, **kwargs):
        raise ContractError("prepared repair image unavailable or mismatched; no pull/build")

    monkeypatch.setattr(verification, "prepared_sandbox", missing)
    result = verification.verify_repair(request, make_patch(project))
    assert result["status"] == "ERROR" and result["checks"] == []
    assert "no pull/build" in result["reason"]


@pytest.mark.parametrize(
    ("code", "skips", "expected"),
    [
        (5, [], "NOT_COLLECTED"),
        (5, ["module skip"], "COLLECTION_SKIPPED"),
        (4, [], "PYTEST_ERROR"),
    ],
)
def test_zero_collection_skip_and_usage_error_are_distinct(code, skips, expected):
    report = {"exit_code": code, "tests": [], "collection_errors": [], "collection_skips": skips}
    raw = {
        "cleanup_failed": False,
        "deadline_exhausted": False,
        "timed_out": False,
        "truncated": False,
        "exit_code": code,
        "stdout": "MARK:" + json.dumps(report),
    }
    assert verification._observation(raw, "MARK:")["status"] == expected


def test_request_scope_is_preserved(project):
    request, _ = project
    public = request.parent / "public.yaml"
    task = yaml.safe_load(public.read_text())
    task["constraints"]["forbidden_paths"] = ["tests/**"]
    public.write_text(yaml.safe_dump(task))
    result = verification.verify_repair(request, make_patch(project))
    assert result["status"] == "UNSUPPORTED" and not result["scope"]["passed"]
    assert result["checks"] == []


def test_partial_parameter_collection_cannot_be_positive():
    item = {
        "path": "tests/test_a.py",
        "function": "test_a",
        "nodeid": "test_a[0]",
        "parameter_index": 0,
        "status": "PASSED",
    }
    rows = [
        {
            "phase": phase,
            "pytest": True,
            "check_id": "c",
            "observation": {"status": "COMPLETED", "tests": [item]},
        }
        for phase in ("base_with_tests", "patched")
    ]
    selectors = [{"path": item["path"], "function": "test_a", "indices": [0, 1]}]
    result = verification._compare(rows, selectors)
    assert result["status"] == "NOT_COLLECTED"
    assert result["missing_selectors"][0]["missing_index"] == 1
