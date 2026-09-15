"""Public check semantics and its existing fail/edit/recheck path; no provider."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dev_notes_lifecycle_v15 import _gateway, _mutation, _restart

from patchloop.artifacts import ArtifactStore
from patchloop.dev import runner
from patchloop.dev.contracts import PublicTurnDecision, RequestedTool
from patchloop.dev.conversation import history_metadata, reconstruct_state
from patchloop.errors import ContractError
from patchloop.runtime import repository_root
from patchloop.sandbox.runner import SandboxResult
from patchloop.task_loader import load_task_package
from patchloop.util import canonical_json, sha256_bytes, sha256_json

TASK_ROOT = repository_root() / "tasks/dev-train"
NAME = "anyio-interrupt-runner-cleanup"


@pytest.fixture(scope="module")
def package():
    return load_task_package(TASK_ROOT / (NAME + "-v2"))


@pytest.fixture(scope="module")
def program(package):
    check = package.public.visible_checks[0]
    assert check.id == "interrupt-lifecycle-contract"
    namespace = {"__name__": "public_contract_test"}
    exec(compile(check.command[-1], "<public-contract>", "exec"), namespace)
    return namespace


def records(program):
    results = []
    for case_id, kind, scope in program["CASES"]:
        events = [{"event": "fixture_setup", "resource_id": 1}]
        if kind == "interrupt":
            events += [
                {"event": "test_started"},
                {"event": "callback_keyboard_interrupt"},
                {"event": "keyboard_interrupt_observed", "exception": "KeyboardInterrupt"},
            ]
        elif kind == "cancel":
            events += [{"event": "test_started"}, {"event": "test_cancel_handler"}]
        else:
            events += [
                {"event": "pytest_report", "phase": "call", "outcome": outcome}
                for outcome in ("passed", "failed", "skipped", "xfailed")
            ]
        events += [
            {"event": "session_finished"},
            {"event": "fixture_cleanup_started"},
            {"event": "fixture_cleanup_completed"},
        ]
        results.append(
            {
                "case_id": case_id,
                "kind": kind,
                "fixture_scope": scope,
                "events": events,
                "exit_code": 2 if kind == "interrupt" else 1,
                "timed_out": False,
                "stdout": "",
                "stderr": "",
            }
        )
    return results


def test_successor_changes_only_version_and_public_check(package):
    predecessor = load_task_package(TASK_ROOT / NAME)
    assert predecessor.task_content_hash == (
        "sha256:fd4296c47cbc9ef4ad0035cde643c534772238086784744f044500fcb9a1203e"
    )
    assert predecessor.public.task_version == predecessor.private.task_version == 1
    assert package.public.task_version == package.private.task_version == 2
    previous = predecessor.public.model_dump(mode="json")
    current = package.public.model_dump(mode="json")
    assert current.pop("visible_checks")[1:] == previous.pop("visible_checks")
    previous.pop("task_version")
    current.pop("task_version")
    assert current == previous
    previous = predecessor.private.model_dump(mode="json")
    current = package.private.model_dump(mode="json")
    previous.pop("task_version")
    current.pop("task_version")
    assert current == previous
    for path in (TASK_ROOT / NAME).rglob("*"):
        if path.is_file() and path.name not in {"public.yaml", "private.yaml", "audit.md"}:
            assert (
                path.read_bytes()
                == (Path(package.root) / path.relative_to(TASK_ROOT / NAME)).read_bytes()
            )


def test_public_reproduction_functions_preserve_frozen_source(package):
    source = package.public.visible_checks[0].command[-1]
    module = ast.parse(source)
    # AST dump formatting varies across Python versions; frozen source bytes do not.
    functions = {
        node.name: ast.get_source_segment(source, node)
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name in {"module_text", "assess"}
    }
    assert sha256_json(functions) == (
        "sha256:0dfb0916fca1c51f730af8dc31827508c09be1f99b85d14993bc16e2cfd2bcd2"
    )


def test_all_assertions_pass_even_when_expected_pytest_exits_are_nonzero(program, capsys):
    assert program["report"](records(program)) == 0
    assert "4 passed, 0 failed" in capsys.readouterr().out


@pytest.mark.parametrize("case", [0, 1])
def test_resumed_interrupted_test_fails_the_registered_process(program, capsys, case):
    observed = records(program)
    observed[case]["events"].append({"event": "post_interrupt"})
    assert program["report"](observed) == 1
    output = capsys.readouterr().out
    assert f"FAIL {observed[case]['case_id']}: interrupted_test_never_resumed" in output
    assert '"post_interrupt": 1' in output


@pytest.mark.parametrize(
    "problem",
    ["timeout", "missing_case", "missing_events", "wrong_exit", "double_cleanup", "lost_xfail"],
)
def test_incomplete_or_wrong_behavior_never_becomes_pass(program, problem):
    observed = records(program)
    if problem == "timeout":
        observed[0]["timed_out"] = True
    elif problem == "missing_case":
        observed.pop()
    elif problem == "missing_events":
        observed[0]["events"] = []
    elif problem == "wrong_exit":
        observed[0]["exit_code"] = 0
    elif problem == "double_cleanup":
        observed[0]["events"].append({"event": "fixture_cleanup_completed"})
    else:
        for event in observed[-1]["events"]:
            if event.get("outcome") == "xfailed":
                event["outcome"] = "skipped"
    assert program["report"](observed) == 1


class WorkflowSandbox:
    """Deterministic source fixture, not a claim that an AnyIO repair passed."""

    official = False

    def __init__(self):
        self.calls = []

    def run_check(self, workspace, check):
        self.calls.append(check.id)
        passed = (
            check.id != "interrupt-lifecycle-contract"
            or "editable = 2" in (workspace / "src.py").read_text()
        )
        text = (
            "4 passed, 0 failed"
            if passed
            else (
                "FAIL interrupt_function: interrupted_test_never_resumed\n"
                '  observed_event_counts={"post_interrupt": 1}\n'
            )
        )
        return SandboxResult(
            command=check.command,
            exit_code=0 if passed else 1,
            stdout=text,
            stderr="",
            duration_ms=1,
            timed_out=False,
            truncated=False,
            original_output_bytes=len(text),
        )


def cycle(gateway, call, policy_name):
    journal = gateway.journal
    store = ArtifactStore(journal.root / "artifacts")
    counters = runner._restore_counters(journal)
    latest = journal.latest_tool_batch_results()
    turn_id = "turn_" + call.action_id
    with journal.execution_lock():
        context = runner._build_context(
            package=SimpleNamespace(public=gateway.public_task),
            gateway=gateway,
            journal=journal,
            correction=None,
            latest_tool_results=latest,
            counters=counters,
            elapsed_seconds=0,
            limits=gateway.limits,
            planning_policy="brief-v1",
        )
        inputs = runner._build_model_input(
            journal=journal,
            artifact_store=store,
            context=context,
            latest_tool_results=latest,
            context_policy=policy_name,
            planning_policy="brief-v1",
        )
        reference = store.put_text(canonical_json(inputs), "application/json")
        journal.append(
            "turn_started",
            {
                "turn_id": turn_id,
                "model_input_artifact": reference.model_dump(mode="json"),
                "model_input_hash": reference.content_hash,
                "native_history": history_metadata(inputs, context_policy=policy_name),
                **(
                    {"context_segment": runner._segment_input_binding(journal, store)}
                    if policy_name == "segmented-v1"
                    else {}
                ),
            },
        )
        journal.append("model_call_finished", {"turn_id": turn_id, "provider": "mock"})
        journal.append(
            "turn_decision_recorded",
            {"turn_id": turn_id, "tool_calls": [call.model_dump(mode="json")]},
        )
        journal.append(
            "tool_batch_started", {"turn_id": turn_id, "tool_calls": [call.model_dump(mode="json")]}
        )
        results = gateway.execute_batch([call])
        runner._record_tool_batch(
            journal=journal,
            gateway=gateway,
            turn_id=turn_id,
            calls=[call],
            results=results,
            active_elapsed_ms=0,
        )
    return results[0], reconstruct_state(inputs, context_policy=policy_name)


def check_call(action_id, check_id):
    return RequestedTool(
        name="run_check",
        action_id=action_id,
        arguments={"check_id": check_id},
        turn_decision=PublicTurnDecision(mode="verify", basis="Run public check"),
    )


@pytest.mark.parametrize("policy_name", ["append-v1", "segmented-v1"])
def test_current_failure_blocks_finish_and_new_diff_can_recheck(tmp_path, package, policy_name):
    gateway = _gateway(tmp_path)
    # Only this local workflow fixture uses a synthetic repository/constraint.
    gateway.public_task = package.public.model_copy(
        update={
            "constraints": package.public.constraints.model_copy(
                update={"allowed_paths": ["src.py"], "forbidden_paths": []}
            )
        }
    )
    sandbox = WorkflowSandbox()
    gateway.sandbox = sandbox
    path = gateway.workspace / "src.py"
    path.write_bytes(path.read_bytes().replace(b"editable = 0", b"editable = 1"))
    regression = "upstream-pytest-plugin-regression"
    contract = "interrupt-lifecycle-contract"
    assert cycle(gateway, check_call("regression_before", regression), policy_name)[0].output[
        "passed"
    ]
    call = check_call("contract_before", contract)
    failed, _ = cycle(gateway, call, policy_name)
    assert failed.output["passed"] is False
    old_hash = gateway.current_diff_hash
    policy = runner._tool_policy(gateway, runner._restore_counters(gateway.journal), gateway.limits)
    assert "finish_task" not in policy.allowed_tools
    assert contract not in policy.check_ids  # no repeated failed check on the same diff
    with pytest.raises(ContractError, match="all visible checks"):
        gateway._finish_task({})
    before = gateway.journal.path.read_bytes()
    gateway = _restart(gateway)
    assert gateway.execute(call).replayed
    assert len(sandbox.calls) == 2
    assert gateway.journal.path.read_bytes() == before
    read_call = RequestedTool(
        name="read_file",
        action_id="read_after_failure",
        arguments={"path": "src.py", "start_line": 1, "end_line": 60},
        turn_decision=PublicTurnDecision(
            mode="inspect", basis="Read repair anchor", evidence_goal="Find current anchor"
        ),
    )
    _, state = cycle(gateway, read_call, policy_name)
    assert state["completion_guidance"]["submission_ready"] is False
    assert any(
        row["check_id"] == contract and row["status"] == "FAIL" and row["diff_hash"] == old_hash
        for row in state["visible_check_status"]
    )
    assert state["public_task"]["visible_checks"][0] == package.public.visible_checks[0].model_dump(
        mode="json"
    )
    mutation = _mutation("repair_fixture", "editable = 1", "editable = 2")
    changed, _ = cycle(gateway, mutation, policy_name)
    assert changed.status == "succeeded"
    assert gateway.current_diff_hash != old_hash
    policy = runner._tool_policy(gateway, runner._restore_counters(gateway.journal), gateway.limits)
    assert contract in policy.check_ids and "finish_task" not in policy.allowed_tools
    passed, state = cycle(gateway, check_call("contract_after", contract), policy_name)
    assert passed.output["passed"] is True
    old = next(row for row in state["recent_checks"] if row["check_id"] == contract)
    assert old["passed"] is False and old["counts_toward_completion"] is False
    assert cycle(gateway, check_call("regression_after", regression), policy_name)[0].output[
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
    assert sandbox.calls == [regression, contract, contract, regression]
    assert sha256_bytes(result.output["patch"].encode()) == gateway.current_diff_hash
