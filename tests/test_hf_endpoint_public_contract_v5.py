"""Public environment regressions and delivery through the existing repair loop."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from test_anyio_public_contract_v2 import check_call, cycle
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _restart

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.check_feedback import check_failure_diagnostics
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox.runner import SandboxResult
from patchloop.task_loader import load_task_package
from patchloop.util import sha256_bytes

TASKS = repository_root() / "tasks/dev-train"
NAME = "hf-hub-xet-endpoint-propagation"
CONTRACT = "xet-endpoint-contract"
REGRESSION = "upstream-xet-regression"
FAILURES = (
    "env-same-default",
    "env-same-already-custom",
    "env-other-default",
    "env-other-ambient-foreign",
)


@pytest.fixture(scope="module")
def package():
    return load_task_package(TASKS / (NAME + "-v5"))


def compile_program(package):
    namespace = {"__name__": "public_contract_test"}
    source = package.public.visible_checks[0].command[-1]
    exec(compile(source, "<public-hf-origin-contract>", "exec"), namespace)
    return namespace


@pytest.fixture(scope="module")
def program(package):
    return compile_program(package)


def records(program, *, environment_only=False):
    """Synthetic observed values, not an execution of a replacement HF repair."""
    rows = []
    for case in program["cases"]():
        route = case["expected"]
        if environment_only and "environment" in case and case["entry"] != "direct-no-endpoint":
            if case["route_kind"] == "default":
                route = case["route"]
            elif case["kind"] == "env-same-already-custom":
                route = program["REQUEST"] + "/hub" + program["REFRESH_PATH"]
            elif case["kind"] == "env-other-ambient-foreign":
                route = program["REQUEST"] + "/global" + program["REFRESH_PATH"]
        row = {
            "id": case["id"],
            "route": route,
            "file_hash": program["FILE_HASH"],
            "requests": [case["url"]],
            "transfer_count": int("download-" in case["entry"]),
            "error": None,
        }
        if "environment" in case:
            row.update(environment=case["environment"], default_origin=program["DEFAULT"])
        rows.append(row)
    return rows


def test_successor_preserves_issue_scope_checks_image_and_opaque_private_bytes(package):
    previous = load_task_package(TASKS / (NAME + "-v4"))
    assert previous.task_content_hash == (
        "sha256:c199ae1f1dfd163c88a328cf31bad7069503c9225bcc4d93be43c0cb484f2847"
    )
    assert previous.public.task_version == previous.private.task_version == 4
    assert package.public.task_version == package.private.task_version == 5
    before, after = previous.public.model_dump(), package.public.model_dump()
    before_checks, after_checks = before.pop("visible_checks"), after.pop("visible_checks")
    assert after_checks[1:] == before_checks[1:]
    old_command = before_checks[0].pop("command")
    new_command = after_checks[0].pop("command")
    assert old_command[:-1] == new_command[:-2]
    assert (
        new_command[-2] == "import sys\nexec(compile(sys.argv[1], '<public-xet-contract>', 'exec'))"
    )
    assert after_checks[0] == before_checks[0]
    before.pop("task_version")
    after.pop("task_version")
    assert before == after
    for path in Path(previous.root).rglob("*"):
        if not path.is_file() or path.name in {"public.yaml", "audit.md"}:
            continue
        expected = path.read_bytes()
        if path.name == "private.yaml":
            expected = expected.replace(b"task_version: 4", b"task_version: 5", 1)
        # Do not print hidden bytes if an equality check fails.
        actual = (Path(package.root) / path.relative_to(previous.root)).read_bytes()
        assert sha256_bytes(actual) == sha256_bytes(expected), path.name


def test_all_previous_public_cases_remain_exactly_represented(program):
    previous = compile_program(load_task_package(TASKS / (NAME + "-v4")))
    cases = {case["id"]: case for case in program["cases"]()}
    assert len(cases) == 292
    assert len(previous["cases"]()) == 196
    for old in previous["cases"]():
        assert cases[old["id"]] == old


def test_environment_matrix_keeps_explicit_request_and_preservation_controls(program):
    cases = program["cases"]()
    assert len(cases) == len({case["id"] for case in cases}) == 292
    for case in cases:
        parsed = urlsplit(case["route"])
        same_origin = (parsed.scheme.lower(), parsed.hostname, parsed.port or 443) == (
            "https",
            "huggingface.co",
            443,
        )
        should_rebase = same_origin and case["entry"] != "direct-no-endpoint"
        expected = (
            case.get("endpoint", program["CUSTOM"]) + program["REFRESH_PATH"]
            if should_rebase
            else case["route"]
        )
        assert case["expected"] == expected
    added = [case for case in cases if "environment" in case]
    assert len(added) == 96 and len({case["entry"] for case in added}) == 6
    assert {case["endpoint"] for case in added} == {"https://mirror.example.test:8443/hub"}
    assert {case["route_kind"] for case in added} == {
        "default",
        "relative",
        "already-custom",
        "ambient-foreign",
    }
    assert sum(case["entry"] == "direct-no-endpoint" for case in added) == 16
    for environment in program["ENVIRONMENTS"].values():
        assert sum(case["environment"] == environment for case in added) == 48


def test_no_new_direct_metadata_or_parser_signature_is_required(package):
    tree = ast.parse(package.public.visible_checks[0].command[-1])
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    for call in calls:
        if isinstance(call.func, ast.Attribute):
            assert call.func.attr != "parse_xet_file_data_from_response"
            if call.func.attr == "get_hf_file_metadata":
                assert all(keyword.arg != "endpoint" for keyword in call.keywords)


@pytest.mark.parametrize(
    "problem",
    [
        "relative",
        "already-custom",
        "ambient-foreign",
        "no-endpoint",
        "client-transfer",
        "environment",
        "default_origin",
    ],
)
def test_environment_controls_and_actual_imported_configuration_are_obligations(program, problem):
    cases = program["cases"]()
    rows = records(program)
    if problem in {"environment", "default_origin"}:
        index = next(i for i, case in enumerate(cases) if "environment" in case)
        rows[index][problem] = (
            program["DEFAULT"] if problem == "environment" else program["REQUEST"]
        )
    elif problem == "client-transfer":
        index = next(
            i
            for i, case in enumerate(cases)
            if "environment" in case and case["entry"] == "client-download-local"
        )
        rows[index]["transfer_count"] = 0
    else:
        index = next(
            i
            for i, case in enumerate(cases)
            if "environment" in case
            and (
                case["entry"] == "direct-no-endpoint"
                if problem == "no-endpoint"
                else case["route_kind"] == problem
            )
        )
        rows[index]["route"] = program["CUSTOM"] + "/wrong"
    assert program["report"](rows) == 1


def test_environment_counterexamples_are_compact_and_all_kinds_reach_diagnostics(program, capsys):
    assert program["report"](records(program)) == 0
    assert "292 passed, 0 failed" in capsys.readouterr().out
    assert program["report"](records(program, environment_only=True)) == 1
    output = capsys.readouterr().out
    assert "252 passed, 40 failed" in output
    assert all(f"FAILED {kind} - 10 cases;" in output for kind in FAILURES)
    assert len(output) < 4000
    exception_type, diagnostic = check_failure_diagnostics(output, "")
    assert exception_type is None
    assert diagnostic["observed_count"] == len(diagnostic["lines"]) == 4
    assert not diagnostic["truncated"]
    assert all(any(f"FAILED {kind} -" in line for line in diagnostic["lines"]) for kind in FAILURES)


@pytest.mark.parametrize(
    "problem",
    [
        "relative_changed",
        "foreign_changed",
        "hash_lost",
        "no_head",
        "wrong_head",
        "no_transfer",
        "double_transfer",
        "error",
        "missing_case",
        "duplicate",
        "reordered",
    ],
)
def test_wrong_or_incomplete_observations_cannot_pass(program, problem):
    rows = records(program)
    if problem in {"relative_changed", "foreign_changed"}:
        rows[1 if problem == "relative_changed" else 2]["route"] = (
            program["CUSTOM"] + program["REFRESH_PATH"]
        )
    elif problem == "hash_lost":
        rows[0]["file_hash"] = None
    elif problem in {"no_head", "wrong_head"}:
        rows[0]["requests"] = [] if problem == "no_head" else [program["DEFAULT"]]
    elif problem in {"no_transfer", "double_transfer"}:
        rows[-1]["transfer_count"] = 0 if problem == "no_transfer" else 2
    elif problem == "error":
        rows[0]["error"] = "RuntimeError: metadata path failed"
    elif problem == "missing_case":
        rows.pop()
    elif problem == "duplicate":
        rows[-1] = rows[0].copy()
    else:
        rows.reverse()
    assert program["report"](rows) == 1


class WorkflowSandbox:
    """Synthetic source repair used only to test public feedback and submission gates."""

    official = False

    def __init__(self, program):
        self.program = program
        self.calls = []

    def run_check(self, workspace, check):
        self.calls.append(check.id)
        stdout = StringIO()
        with redirect_stdout(stdout):
            if check.id == CONTRACT:
                failed = "editable = 2" not in (workspace / "src.py").read_text()
                exit_code = self.program["report"](records(self.program, environment_only=failed))
            else:
                assert check.id == REGRESSION
                print("15 passed")
                exit_code = 0
        text = stdout.getvalue()
        return SandboxResult(
            command=check.command,
            exit_code=exit_code,
            stdout=text,
            stderr="",
            duration_ms=1,
            timed_out=False,
            truncated=False,
            original_output_bytes=len(text.encode()),
        )


@pytest.mark.parametrize("policy_name", ["append-v1", "segmented-v1"])
def test_failures_reach_actual_inputs_and_require_a_new_diff(
    tmp_path, package, program, policy_name
):
    gateway = _gateway(tmp_path)
    gateway.public_task = package.public.model_copy(
        update={
            "constraints": package.public.constraints.model_copy(
                update={"allowed_paths": ["src.py"], "forbidden_paths": []}
            )
        }
    )
    sandbox = WorkflowSandbox(program)
    gateway.sandbox = sandbox
    path = gateway.workspace / "src.py"
    path.write_bytes(path.read_bytes().replace(b"editable = 0", b"editable = 1"))
    assert cycle(gateway, check_call("regression_before", REGRESSION), policy_name)[0].output[
        "passed"
    ]
    call = check_call("contract_before", CONTRACT)
    failed, _ = cycle(gateway, call, policy_name)
    assert failed.output["passed"] is False
    old_hash = gateway.current_diff_hash
    policy = runner._tool_policy(gateway, runner._restore_counters(gateway.journal), gateway.limits)
    assert "finish_task" not in policy.allowed_tools and CONTRACT not in policy.check_ids
    with pytest.raises(ContractError, match="all visible checks"):
        gateway._finish_task({})
    before = gateway.journal.path.read_bytes()
    gateway = _restart(gateway)
    assert gateway.execute(call).replayed
    assert len(sandbox.calls) == 2 and gateway.journal.path.read_bytes() == before
    read = RequestedTool(
        name="read_file",
        action_id="read_after_failure",
        arguments={"path": "src.py", "start_line": 1, "end_line": 60},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Read repair anchor", evidence_goal="Find current anchor"
        ),
    )
    _, state = cycle(gateway, read, policy_name)
    assert state["completion_guidance"]["submission_ready"] is False
    assert any(
        row["check_id"] == CONTRACT and row["status"] == "FAIL" and row["diff_hash"] == old_hash
        for row in state["visible_check_status"]
    )
    assert state["public_task"] == gateway.public_task.model_dump(mode="json")
    assert state["current_diff"]["patch_hash"] == old_hash
    turn = [e["payload"] for e in gateway.journal.events() if e["event_type"] == "turn_started"][-1]
    store = ArtifactStore(gateway.journal.root / "artifacts")
    native = store.read_bytes(Artifact.model_validate(turn["model_input_artifact"])).decode()
    assert all(f"FAILED {kind} - 10 cases;" in native for kind in FAILURES)
    assert "252 passed, 40 failed" in native
    changed, _ = cycle(
        gateway, _mutation("repair_fixture", "editable = 1", "editable = 2"), policy_name
    )
    assert changed.status == "succeeded" and gateway.current_diff_hash != old_hash
    policy = runner._tool_policy(gateway, runner._restore_counters(gateway.journal), gateway.limits)
    assert CONTRACT in policy.check_ids and "finish_task" not in policy.allowed_tools
    passed, state = cycle(gateway, check_call("contract_after", CONTRACT), policy_name)
    assert passed.output["passed"] is True
    old = next(row for row in state["recent_checks"] if row["check_id"] == CONTRACT)
    assert old["passed"] is False and old["counts_toward_completion"] is False
    assert cycle(gateway, check_call("regression_after", REGRESSION), policy_name)[0].output[
        "passed"
    ]
    finish = RequestedTool(
        name="finish_task",
        action_id="finish",
        arguments={},
        turn_decision=PublicTurnDecision(mode="finish", basis="Checks pass"),
    )
    result, state = cycle(gateway, finish, policy_name)
    assert result.status == "succeeded" and state["completion_guidance"]["submission_ready"] is True
    assert sandbox.calls == [REGRESSION, CONTRACT, CONTRACT, REGRESSION]


def test_launcher_preserves_public_program_as_single_source_argument(package):
    launcher = package.public.visible_checks[0].command[1:-1]
    code = "import json,sys; print(json.dumps([__name__, sys.argv[1]]))"
    result = subprocess.run(
        [sys.executable, *launcher, code],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert json.loads(result.stdout) == ["__main__", code]


def test_environment_workers_start_with_configured_environment_and_fixed_cases(
    program, monkeypatch
):
    by_id = {row["id"]: row for row in records(program)}
    observed = []
    monkeypatch.setitem(program, "observe", lambda cases: [by_id[case["id"]] for case in cases])

    def run(command, **kwargs):
        cases = json.loads(kwargs["input"])
        environment = kwargs["env"]["HF_ENDPOINT"]
        assert command == [
            sys.executable,
            "-B",
            "-c",
            "frozen-public-source",
            "--environment-worker",
        ]
        assert kwargs["env"]["HUGGINGFACE_CO_STAGING"] == "0"
        assert kwargs["check"] and kwargs["capture_output"] and kwargs["text"]
        assert kwargs["timeout"] == 20
        assert len(cases) == 48 and all(case["environment"] == environment for case in cases)
        observed.append(environment)
        return SimpleNamespace(stdout=json.dumps([by_id[case["id"]] for case in cases]))

    monkeypatch.setattr(program["subprocess"], "run", run)
    rows = program["observe_all"]("frozen-public-source")
    assert rows == records(program)
    assert observed == list(program["ENVIRONMENTS"].values())


@pytest.mark.parametrize("problem", ["exit", "timeout", "invalid-json"])
def test_worker_execution_failure_never_becomes_a_passing_partial_check(
    program, monkeypatch, problem
):
    monkeypatch.setitem(program, "observe", lambda cases: [])

    def run(command, **kwargs):
        if problem == "exit":
            raise subprocess.CalledProcessError(1, command)
        if problem == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return SimpleNamespace(stdout="invalid-json")

    monkeypatch.setattr(program["subprocess"], "run", run)
    with pytest.raises((subprocess.SubprocessError, json.JSONDecodeError)):
        program["observe_all"]("frozen-public-source")
