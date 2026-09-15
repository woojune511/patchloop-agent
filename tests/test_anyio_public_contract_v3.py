"""Versioned public lifecycle checks; no hidden oracle or model-generated repair."""

from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path
from types import ModuleType

import pytest
from test_anyio_public_contract_v2 import (
    test_current_failure_blocks_finish_and_new_diff_can_recheck as _workflow,
)

from patchloop.runtime import repository_root
from patchloop.task_loader import load_task_package

TASKS = repository_root() / "tasks/dev-train"
NAME = "anyio-interrupt-runner-cleanup"


@pytest.fixture(scope="module")
def package():
    return load_task_package(TASKS / (NAME + "-v3"))


@pytest.fixture(scope="module")
def program(package):
    namespace = {"__name__": "public_contract_test"}
    exec(compile(package.public.visible_checks[0].command[-1], "<public-contract-v3>", "exec"),
         namespace)
    return namespace


def test_successor_preserves_source_constraints_and_private_bytes(package):
    previous = load_task_package(TASKS / (NAME + "-v2"))
    assert previous.task_content_hash == (
        "sha256:eddc56cdb046406027cad1ed30f7788f50327de98e6a40ac387fbfe25b73478d"
    )
    assert package.public.task_version == package.private.task_version == 3
    before, after = previous.public.model_dump(), package.public.model_dump()
    assert after.pop("visible_checks")[1:] == before.pop("visible_checks")[1:]
    before.pop("task_version")
    after.pop("task_version")
    assert before == after
    for path in Path(previous.root).rglob("*"):
        if not path.is_file() or path.name in {"public.yaml", "audit.md"}:
            continue
        expected = path.read_bytes()
        if path.name == "private.yaml":
            expected = expected.replace(b"task_version: 2", b"task_version: 3", 1)
        assert (Path(package.root) / path.relative_to(previous.root)).read_bytes() == expected


def records(program):
    """Synthetic valid observations; these do not represent a working AnyIO repair."""
    rows = []
    for case_id, kind, scope, fixture in program["CASES"]:
        def observation(event, value=None, fixture=fixture):
            return {"event": event, "resource_id": 1, "task_id": 10, "same_task": True,
                    "value": value if value is not None else (
                        "fixture" if fixture == "context" else "unset")}

        events = [observation("fixture_setup")]
        if kind == "ordinary":
            tests = [("test_1_pass", "passed", "ordinary_pass"),
                     ("test_2_failure", "failed", "ordinary_failure"),
                     ("test_3_skip", "skipped", "ordinary_skip"),
                     ("test_4_xfail", "xfailed", "ordinary_xfail")]
        elif kind in {"context", "skip"}:
            tests = ([("test_0_skip", "skipped", "ordinary_skip")] if kind == "skip" else [])
            tests += [("test_1_context", "passed", "context_read")]
        else:
            tests = ([("test_0_prior", "passed", "prior_test")] if scope == "module" else [])
            tests += [("test_1_interruption", None if kind == "interrupt" else "failed",
                       "test_started")]
        for name, outcome, event in tests:
            report = {"event": "pytest_report", "nodeid": "test_public.py::" + name}
            events += [{**report, "phase": "setup", "outcome": "passed"}, observation(event)]
            if outcome is not None:
                events += [{**report, "phase": "call", "outcome": outcome},
                           {**report, "phase": "teardown", "outcome": "passed"}]
        if kind == "interrupt":
            events += [{"event": "callback_keyboard_interrupt"},
                       {"event": "keyboard_interrupt_observed", "exception": "KeyboardInterrupt"}]
        if kind == "cancel":
            events.append({"event": "test_cancel_handler"})
        if kind in {"interrupt", "cancel"}:
            events.append({"event": "test_finally"})
        events.append(observation("fixture_cleanup_started"))
        if fixture == "context":
            events.append({"event": "context_restored", "value": "unset"})
        elif fixture == "taskgroup":
            events.append({"event": "fixture_cleanup_body_completed"})
        events += [observation("fixture_cleanup_completed", "unset"), {"event": "session_finished"}]
        rows.append({"case_id": case_id, "kind": kind, "fixture_scope": scope, "fixture": fixture,
                     "events": events, "timed_out": False, "stdout": "", "stderr": "",
                     "exit_code": 2 if kind == "interrupt" else (
                         0 if kind in {"context", "skip"} else 1)})
    return rows


def test_expected_call_fail_skip_xfail_are_accepted_with_successful_teardown(program, capsys):
    assert program["report"](records(program)) == 0
    assert "7 passed, 0 failed" in capsys.readouterr().out


def test_explicit_cancellation_keeps_v2_plain_fixture_contract(program):
    rows = records(program)
    row = next(row for row in rows if row["kind"] == "cancel")
    assert row["fixture"] == "plain"
    next(e for e in row["events"] if e["event"] == "fixture_cleanup_started").update(
        task_id=20, same_task=False)
    assert program["assess"](row)["passed"]


def test_multiple_failures_keep_actionable_feedback_bounded(program, capsys):
    rows = records(program)
    for row in rows:
        row["exit_code"] = 1
        row["stdout"] = "large child trace\n" * 1000
        for event in row["events"]:
            if "same_task" in event and event["event"] != "fixture_setup":
                event.update(same_task=False, task_id=20, value="unset")
        row["events"] = [e for e in row["events"] if e["event"] != "fixture_cleanup_completed"]
    assert program["report"](rows) == 1
    output = capsys.readouterr().out
    assert len(output.encode()) < 8000
    assert "same_fixture_task" in output and '"cleanup_completed": 0' in output


@pytest.mark.parametrize("phase", ["setup", "teardown"])
@pytest.mark.parametrize("outcome", ["failed", "skipped", "xfailed"])
def test_fixture_outcomes_are_independent_of_expected_call_xfail(program, phase, outcome):
    rows = records(program)
    event = next(e for e in reversed(rows[-1]["events"])
                 if e["event"] == "pytest_report" and e["phase"] == phase)
    event["outcome"] = outcome
    assert not program["assess"](rows[-1])["assertions"]["setup_and_teardown_passed"]
    assert program["report"](rows) == 1


@pytest.mark.parametrize("problem", ["different_task", "lost_context", "missing_context_reset",
                                    "body_only", "double_cleanup", "resumed_test", "timeout",
                                    "wrong_exit", "missing_case", "missing_teardown"])
def test_observed_regressions_or_incomplete_execution_fail(program, problem):
    rows = records(program)
    if problem == "different_task":
        event = next(e for e in rows[-1]["events"] if e["event"] == "fixture_cleanup_started")
        event.update(task_id=20, same_task=False)
    elif problem == "lost_context":
        next(e for e in rows[-2]["events"] if e["event"] == "context_read")["value"] = "unset"
    elif problem == "missing_context_reset":
        rows[0]["events"] = [e for e in rows[0]["events"] if e["event"] != "context_restored"]
    elif problem == "body_only":
        rows[-1]["events"] = [e for e in rows[-1]["events"]
                              if e["event"] != "fixture_cleanup_completed"]
    elif problem == "double_cleanup":
        rows[0]["events"].append({"event": "fixture_cleanup_completed"})
    elif problem == "resumed_test":
        rows[0]["events"].append({"event": "post_interrupt"})
    elif problem == "timeout":
        rows[0]["timed_out"] = True
    elif problem == "wrong_exit":
        rows[0]["exit_code"] = 1
    elif problem == "missing_case":
        rows.pop()
    else:
        rows[-1]["events"] = [e for e in rows[-1]["events"] if e.get("phase") != "teardown"]
    assert program["report"](rows) == 1


@pytest.mark.parametrize("fixture", ["context", "taskgroup"])
@pytest.mark.parametrize("switch_task", [False, True])
def test_generated_fixture_only_completes_after_context_exit(program, monkeypatch, fixture,
                                                           switch_task):
    events = []
    emitter = ModuleType("event_log")
    emitter.emit = lambda event, **details: events.append({"event": event, **details})
    monkeypatch.setitem(sys.modules, "event_log", emitter)
    namespace = {}
    exec(compile(program["module_text"]("context", "module", fixture), "<fixture>", "exec"),
         namespace)

    async def exercise():
        generator = namespace["resource"].__wrapped__()
        await anext(generator)
        if switch_task:
            exception = ValueError if fixture == "context" else RuntimeError
            with pytest.raises(exception):
                await asyncio.create_task(anext(generator))
        else:
            with pytest.raises(StopAsyncIteration):
                await anext(generator)

    asyncio.run(exercise())
    names = [e["event"] for e in events]
    assert ("fixture_cleanup_completed" in names) is not switch_task
    assert next(e["same_task"] for e in events
                if e["event"] == "fixture_cleanup_started") is not switch_task
    if fixture == "taskgroup":
        assert "fixture_cleanup_body_completed" in names


def test_generated_modules_compile_and_xfail_is_limited_to_assertion(program):
    for _, kind, scope, fixture in program["CASES"]:
        tree = ast.parse(program["module_text"](kind, scope, fixture))
        compile(tree, "<generated-case>", "exec")
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "xfail"):
                raises = next(k.value for k in node.keywords if k.arg == "raises")
                assert isinstance(raises, ast.Name) and raises.id == "AssertionError"
    compile(program["CONFTEST"], "<generated-conftest>", "exec")
    compile(program["EMITTER"], "<generated-emitter>", "exec")


@pytest.mark.parametrize("policy", ["append-v1", "segmented-v1"])
def test_v3_public_failure_and_task_reach_actual_inputs(tmp_path, package, policy):
    _workflow(tmp_path, package, policy)
