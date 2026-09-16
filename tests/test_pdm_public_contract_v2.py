"""Public PDM selection semantics and delivery through the existing repair loop."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest
from test_anyio_public_contract_v2 import check_call, cycle
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _restart

from patchloop.artifacts import ArtifactStore
from patchloop.contracts import Artifact
from patchloop.dev import runner
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox.runner import SandboxResult
from patchloop.task_loader import load_task_package

TASKS = repository_root() / "tasks/dev-train"
NAME = "pdm-ignore-active-venv-resolution"
CONTRACT = "active-venv-exclusion-contract"
REGRESSION = "upstream-project-regression"
DESCENDANTS = [
    f"{key}-{scenario}"
    for key in ("VIRTUAL_ENV", "CONDA_PREFIX")
    for scenario in ("descendant", "create-after-descendant")
]


@pytest.fixture(scope="module")
def package():
    return load_task_package(TASKS / (NAME + "-v2"))


@pytest.fixture(scope="module")
def program(package):
    check = package.public.visible_checks[0]
    assert check.id == CONTRACT
    namespace = {"__name__": "public_contract_test"}
    exec(compile(check.command[-1], "<public-pdm-contract>", "exec"), namespace)
    return namespace


def records(program, *, descendants_fail=False):
    """Synthetic observations; no claim that a new PDM repair has passed."""
    return [
        {
            "id": case["id"],
            "selected": "nested"
            if descendants_fail and (case["id"] in DESCENDANTS)
            else case["expected"],
            "error": None,
            "create_calls": int(
                case["expected"] == "created"
                and not (descendants_fail and case["id"] in DESCENDANTS)
            ),
        }
        for case in program["cases"]()
    ]


def test_successor_preserves_issue_constraints_image_and_private_bytes(package):
    previous = load_task_package(TASKS / NAME)
    assert previous.task_content_hash == (
        "sha256:15a8f420a7480984daf8148a45bc22e81640ccbceaece04a63ea2be3eb45168c"
    )
    assert previous.public.task_version == previous.private.task_version == 1
    assert package.public.task_version == package.private.task_version == 2
    before, after = previous.public.model_dump(), package.public.model_dump()
    assert after.pop("visible_checks")[1:] == before.pop("visible_checks")
    before.pop("task_version")
    after.pop("task_version")
    assert before == after
    for path in Path(previous.root).rglob("*"):
        if not path.is_file() or path.name in {"public.yaml", "audit.md"}:
            continue
        expected = path.read_bytes()
        if path.name == "private.yaml":
            expected = expected.replace(b"task_version: 1", b"task_version: 2", 1)
        assert (Path(package.root) / path.relative_to(previous.root)).read_bytes() == expected


def test_public_cases_cover_reuse_exclusion_siblings_and_creation(program):
    cases = program["cases"]()
    assert len(cases) == len({case["id"] for case in cases}) == 24
    for key in ("VIRTUAL_ENV", "CONDA_PREFIX"):
        rows = [case for case in cases if case["key"] == key]
        assert [row["flag"] for row in rows[:7]] == [None, "", "0", "false", "FALSE", "no", "off"]
        assert all(row["expected"] == "active" for row in rows[:7])
        assert [(row["candidates"], row["expected"]) for row in rows[7:]] == [
            (["active", "other"], "other"),
            (["nested", "other"], "other"),
            (["sibling", "other"], "sibling"),
            (["active"], "created"),
            (["active", "nested"], "created"),
        ]


def test_valid_observations_pass_and_descendant_selection_fails(program, capsys):
    assert program["report"](records(program)) == 0
    assert "24 passed, 0 failed" in capsys.readouterr().out
    assert program["report"](records(program, descendants_fail=True)) == 1
    output = capsys.readouterr().out
    assert "20 passed, 4 failed" in output
    assert all(f"FAILED {case_id}:" in output for case_id in DESCENDANTS)


@pytest.mark.parametrize(
    "problem",
    [
        "wrong_reuse",
        "wrong_sibling",
        "missing_creation",
        "extra_creation",
        "resolution_error",
        "missing_case",
        "duplicate_case",
        "reordered_cases",
    ],
)
def test_incorrect_or_incomplete_observations_cannot_pass(program, problem):
    observed = records(program)
    if problem == "wrong_reuse":
        observed[0]["selected"] = "other"
    elif problem == "wrong_sibling":
        observed[9]["selected"] = "other"
    elif problem == "missing_creation":
        observed[10]["create_calls"] = 0
    elif problem == "extra_creation":
        observed[0]["create_calls"] = 1
    elif problem == "resolution_error":
        observed[0]["error"] = "NoPythonVersion"
    elif problem == "missing_case":
        observed.pop()
    elif problem == "duplicate_case":
        observed[-1] = observed[0]
    else:
        observed.reverse()
    assert program["report"](observed) == 1


class WorkflowSandbox:
    """Deliver the public check's verdicts using a deterministic source fixture."""

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
                exit_code = self.program["report"](records(self.program, descendants_fail=failed))
            else:
                assert check.id == REGRESSION
                print("36 passed")
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
    # Check failure lines, not just the case IDs already present in the public task.
    assert all(f"FAILED {case_id}:" in native for case_id in DESCENDANTS)
    assert "20 passed, 4 failed" in native
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
