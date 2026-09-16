"""Public origin regressions and delivery through the existing repair loop."""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
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
FAILURES = ("host-case", "scheme-case", "default-port")


@pytest.fixture(scope="module")
def package():
    return load_task_package(TASKS / (NAME + "-v3"))


def compile_program(package):
    namespace = {"__name__": "public_contract_test"}
    source = package.public.visible_checks[0].command[-1]
    exec(compile(source, "<public-hf-origin-contract>", "exec"), namespace)
    return namespace


@pytest.fixture(scope="module")
def program(package):
    return compile_program(package)


def records(program, *, prefix_only=False):
    """Synthetic outcomes, not execution of a replacement HF repair."""
    return [
        {
            "id": case["id"],
            "route": case["route"]
            if prefix_only and case["kind"] in FAILURES
            else case["expected"],
            "file_hash": program["FILE_HASH"],
            "requests": [case["url"]],
            "transfer_count": int(case["entry"].startswith("download-")),
            "error": None,
        }
        for case in program["cases"]()
    ]


def test_successor_preserves_issue_scope_checks_image_and_opaque_private_bytes(package):
    previous = load_task_package(TASKS / (NAME + "-v2"))
    assert previous.task_content_hash == (
        "sha256:f22262330bb6ce1fedc7b6785140ec474ce943fc10e71634e55a4e69a04572a7"
    )
    assert previous.public.task_version == previous.private.task_version == 2
    assert package.public.task_version == package.private.task_version == 3
    before, after = previous.public.model_dump(), package.public.model_dump()
    before_checks, after_checks = before.pop("visible_checks"), after.pop("visible_checks")
    assert after_checks[1:] == before_checks[1:]
    old_command = before_checks[0].pop("command")
    new_command = after_checks[0].pop("command")
    assert old_command[:-1] == new_command[:-1]
    assert after_checks[0] == before_checks[0]
    before.pop("task_version")
    after.pop("task_version")
    assert before == after
    for path in Path(previous.root).rglob("*"):
        if not path.is_file() or path.name in {"public.yaml", "audit.md"}:
            continue
        expected = path.read_bytes()
        if path.name == "private.yaml":
            expected = expected.replace(b"task_version: 2", b"task_version: 3", 1)
        # Do not print hidden bytes if an equality check fails.
        actual = (Path(package.root) / path.relative_to(previous.root)).read_bytes()
        assert sha256_bytes(actual) == sha256_bytes(expected), path.name


def test_all_previous_public_cases_remain_exactly_represented(program):
    previous = compile_program(load_task_package(TASKS / (NAME + "-v2")))
    cases = {case["id"]: case for case in program["cases"]()}
    assert len(cases) == 100
    assert len(previous["cases"]()) == 24
    for old in previous["cases"]():
        assert {key: cases[old["id"]][key] for key in old} == old


def test_origin_matrix_keeps_relative_foreign_and_no_endpoint_controls(program):
    cases = program["cases"]()
    assert len(cases) == len({case["id"] for case in cases}) == 100
    assert len({case["entry"] for case in cases}) == 5
    for case in cases:
        parsed = urlsplit(case["route"])
        same_origin = (parsed.scheme.lower(), parsed.hostname, parsed.port or 443) == (
            "https",
            "huggingface.co",
            443,
        )
        should_rebase = same_origin and case["entry"] != "direct-no-endpoint"
        expected = program["CUSTOM"] + program["REFRESH_PATH"] if should_rebase else case["route"]
        assert case["expected"] == expected
    assert sum(case["entry"] == "direct-no-endpoint" for case in cases) == 20
    assert sum(case["kind"] not in (*FAILURES, "default") for case in cases) == 60


def test_no_new_direct_metadata_or_parser_signature_is_required(package):
    tree = ast.parse(package.public.visible_checks[0].command[-1])
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    for call in calls:
        if isinstance(call.func, ast.Attribute):
            assert call.func.attr != "parse_xet_file_data_from_response"
            if call.func.attr == "get_hf_file_metadata":
                assert all(keyword.arg != "endpoint" for keyword in call.keywords)


def test_prefix_counterexamples_are_compact_and_all_kinds_reach_diagnostics(program, capsys):
    assert program["report"](records(program)) == 0
    assert "100 passed, 0 failed" in capsys.readouterr().out
    assert program["report"](records(program, prefix_only=True)) == 1
    output = capsys.readouterr().out
    assert "76 passed, 24 failed" in output
    assert all(f"FAILED {kind} - 8 cases;" in output for kind in FAILURES)
    assert len(output) < 4000
    exception_type, diagnostic = check_failure_diagnostics(output, "")
    assert exception_type is None
    assert diagnostic["observed_count"] == len(diagnostic["lines"]) == 3
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
                exit_code = self.program["report"](records(self.program, prefix_only=failed))
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
    assert all(f"FAILED {kind} - 8 cases;" in native for kind in FAILURES)
    assert "76 passed, 24 failed" in native
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
