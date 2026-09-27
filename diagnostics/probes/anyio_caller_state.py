"""Public observation program; MODE is supplied by the isolated probe driver."""

import asyncio
import json
import sys

from anyio._backends._asyncio import TestRunner

events = []
observations = []
caller = None
owner = None


def state(task):
    if task is None:
        return None
    return {"done": task.done(), "cancelled": task.cancelled(), "cancelling": task.cancelling()}


def observe(stage, **extra):
    observations.append({"stage": stage, "caller": state(caller),
                         "runner": state(runner._runner_task), "events": list(events), **extra})


def event(name):
    current = asyncio.current_task()
    events.append({"name": name, "same_fixture_task": current is owner})


async def resource():
    global owner
    owner = asyncio.current_task()
    event("fixture_setup")
    try:
        yield {"owner": owner}
    finally:
        event("fixture_cleanup_started")
        await asyncio.sleep(0)
        event("fixture_cleanup_completed")


def trigger():
    observe("before_trigger")
    if MODE == "callback_interrupt":  # noqa: F821
        event("callback_keyboard_interrupt")
        raise KeyboardInterrupt
    event("callback_caller_cancel")
    accepted = caller.cancel()
    observe("after_cancel_request", cancel_returned=accepted)


async def test(resource):
    global caller
    event("test_started")
    # Capture the existing waiting task; do not wrap, schedule, cancel or await it.
    candidates = [task for task in asyncio.all_tasks()
                  if task is not asyncio.current_task()
                  and task.get_coro().__qualname__ == "TestRunner._call_in_runner_task"]
    assert len(candidates) == 1, "expected exactly one existing caller task"
    caller = candidates[0]
    assert caller is not runner._runner_task
    loop = asyncio.get_running_loop()
    loop.call_soon(trigger)
    try:
        await asyncio.sleep(0)
        event("post_interrupt")
    finally:
        event("test_finally")


assert MODE in {"callback_interrupt", "explicit_caller_cancel"}  # noqa: F821
with TestRunner() as runner:
    assert runner._runner_task is None
    fixture_iter = runner.run_asyncgen_fixture(resource, {})
    resource_value = next(fixture_iter)
    assert runner._runner_task is owner
    observe("after_setup")
    try:
        runner.run_test(test, {"resource": resource_value})
    except BaseException as exc:
        observe("run_test_raised", exception=type(exc).__name__)
    else:
        observe("run_test_returned")
    observe("before_teardown")
    try:
        next(fixture_iter)
    except StopIteration:
        observe("after_teardown")
observe("after_exit")
print(json.dumps({"mode": MODE, "python": sys.version.split()[0],  # noqa: F821
                  "observations": observations}))
