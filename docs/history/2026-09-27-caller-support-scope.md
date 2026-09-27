# Waiting-caller support scope

## Question and inspected evidence

Does directly cancelling the waiting internal caller establish a required repair
path for the current AnyIO task? This is a source-only follow-up to
[caller preservation](2026-09-27-caller-cancel-preservation.md); that record and its
ten probe results remain unchanged.

Inspected public source at AnyIO commit
`cb245dba9883516f2ed4c23899de157183a1cb50`, in
`C:/pt/analyses/anyio-caller-preservation-20260927-v1/workspaces/cleanup_BASE/repo`:

- `src/anyio/abc/_testing.py`: synchronous runner methods expose fixture/test
  execution, with no waiting-caller cancellation handle or contract.
- `src/anyio/pytest_plugin.py:124,231,251`: pytest invokes those synchronous
  methods. It does not discover or directly cancel the waiting caller.
- `src/anyio/_backends/_asyncio.py:2261-2325`: the private helper queues the
  user coroutine and awaits a future; synchronous methods drive it through
  `run_until_complete`. The persistent worker executes the user coroutine.
- `docs/testing.rst:203,234,241-268`: examples cancel user task groups; the
  technical description promises shared task/context behavior for fixtures/tests.
  It does not specify externally cancelling the private waiting helper.
- `tests/test_pytest_plugin.py`: cancellation examples target user cancel scopes;
  the KeyboardInterrupt example raises from a child in a user task group.

Searched `src`, `tests` and `docs` for `_call_in_runner_task` and `all_tasks(`.
The asyncio helper's call sites are the runner methods above. Other task enumeration
includes loop shutdown and task inspection; enumeration alone does not establish
the probe's selective caller cancellation as a supported pytest operation.

The operator probe in `diagnostics/probes/anyio_caller_cancel_preservation.py`
discovers a task by the private coroutine qualified name through `asyncio.all_tasks()`
and calls `caller.cancel()` while the user coroutine waits on an Event. That is an
explicit synthetic intervention, distinct from cancelling the test coroutine or
raising KeyboardInterrupt. The v3 task audit already keeps native cancellation
separate from its task/context preservation requirements.

## Decision and limits

No support evidence was found in the inspected pinned public paths. This does not
prove external integrations never cancel that task or establish current upstream
policy. Close this diagnostic; do not add a required check, change prompts, or
invalidate existing acceptance based on it. All five probe candidates, including
base, stalled on this intervention, so it is not a newly introduced regression.

No runtime/task edits, new probes, Docker operations, provider calls or evaluations
were performed. Only current documentation, this follow-up and the history index
change. Historical evidence remains immutable; all runs remain `official=false`.

## Measurement correction and next question

The original task audit explicitly describes a stricter PatchLoop acceptance
oracle than the benchmark's original F2P/P2P oracle. The v2/v3 public lifecycle
checks were added during harness development, not autonomously by the evaluated
agent. Recent acceptance results therefore measure adapted development tasks;
they must not be reported as original SWE-rebench performance.

Next prepare a fixed original-benchmark evaluation specification: dataset revision,
instance IDs, original issue inputs, base commits, original oracle, dependency
availability and execution limits. Report adapted development results separately,
and separate development feedback from held-out evaluation. Merely re-evaluating
an already guided patch with the original oracle would not make it a fresh solve.
This decision does not authorize a paid invocation or a new experiment allocation.
