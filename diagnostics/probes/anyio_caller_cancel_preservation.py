"""Waiting-caller cancellation; CANCEL is supplied by the operator driver."""

import asyncio
import json
import os
import sys
from contextvars import ContextVar

from anyio._backends._asyncio import TestRunner

records = []
events = []
caller = owner = None
marker = ContextVar("fixture_marker", default="unset")


def state(task):
    return None if task is None else [task.done(), task.cancelled(), task.cancelling()]


def observe(at, **extra):
    assert len(records) < 80, "trace exceeded its bound"
    records.append(
        {"at": at, "caller": state(caller), "runner": state(runner._runner_task), **extra}
    )


def event(name):
    events.append({"name": name, "same_fixture_task": asyncio.current_task() is owner})


def emit(outcome):
    print(
        json.dumps(
            {
                "outcome": outcome,
                "cancel_requested": CANCEL,  # noqa: F821
                "python": sys.version.split()[0],
                "task_state_fields": ["done", "cancelled", "cancelling"],
                "records": records,
                "events": events,
            },
            separators=(",", ":"),
        ),
        flush=True,
    )


def watchdog():
    observe(
        "watchdog",
        pending=[
            {
                "coroutine": task.get_coro().__qualname__,
                "state": state(task),
                "stack": [frame.f_code.co_name for frame in task.get_stack()],
            }
            for task in asyncio.all_tasks()
        ],
    )
    emit("diagnostic_watchdog_exit")
    # Bound the diagnostic without issuing additional cancellation or allowing a
    # hanging TestRunner.__exit__ to change the state being observed.
    os._exit(0)


async def resource():
    global owner
    owner = asyncio.current_task()
    token = marker.set("fixture")
    event("fixture_setup")
    try:
        yield {"owner": owner}
    finally:
        event("fixture_cleanup_started")
        await asyncio.sleep(0)
        marker.reset(token)
        event("fixture_cleanup_completed")


def trigger():
    observe("before_trigger")
    if CANCEL:  # noqa: F821
        event("caller_cancel_requested")
        observe("after_cancel_request", accepted=caller.cancel())
    else:
        event("normal_release")
        gate.set()


async def test(resource):
    global caller, gate
    event("test_started")
    candidates = [
        task
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
        and task.get_coro().__qualname__ == "TestRunner._call_in_runner_task"
    ]
    assert len(candidates) == 1, "expected exactly one existing caller"
    caller = candidates[0]
    gate = asyncio.Event()
    asyncio.get_running_loop().call_soon(trigger)
    try:
        await gate.wait()
        event("test_completed")
    finally:
        event("test_finally")


with TestRunner() as runner:
    fixture_iter = runner.run_asyncgen_fixture(resource, {})
    value = next(fixture_iter)
    observe("after_setup")
    timer = runner.get_loop().call_later(2, watchdog)
    try:
        runner.run_test(test, {"resource": value})
    except BaseException as exc:
        observe("run_test_raised", exception=type(exc).__name__)
    else:
        observe("run_test_returned")
    observe("before_teardown")
    try:
        next(fixture_iter)
    except StopIteration:
        observe("after_teardown")
    timer.cancel()
observe("after_exit")
emit("completed")
