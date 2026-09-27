# Waiting caller cancellation preservation diagnostic

## Question and scope

The four cleanup-information continuations passed public checks and acceptance.
Could they also stop an active submission and complete fixture cleanup when the
existing waiting caller task is directly cancelled? This operator diagnostic tests
that additional path against the original base, without supplying agent inputs or
running any model. It does not redefine the completed task's acceptance contract.

Implementation: `diagnostics/anyio_caller_preservation.py` and
`diagnostics/probes/anyio_caller_cancel_preservation.py`, commit `16e9f117`.
Contract: [caller preservation](../../.agent/caller-preservation.md).
Exactly ten existing-image probes: BASE/A1/A2/B1/B2, each normal release and direct
caller.cancel(). Public source and pinned dependency/image identities were retained.
Two accepted historical edits per final candidate were reconstructed into fresh
workspaces with pre/post file and complete-diff verification. No old workspace changed.

## Program and observations

The test coroutine awaits an unset Event before a scheduled callback. The normal
callback sets the Event; the cancellation callback cancels the existing waiting
_call_in_runner_task task and leaves the Event unset. This makes cancellation
propagation observable while avoiding a coroutine that already completed after
sleep(0). No wrapper task, source trace or monkeypatched TestRunner method is used.
A ContextVar fixture records ownership and resets its token during async teardown.

| Candidate | Normal completion and same-task cleanup | Caller-cancel completion |
| --- | --- | --- |
| BASE | PASS, exactly once | stalled |
| A1 | PASS, exactly once | stalled |
| A2 | PASS, exactly once | stalled |
| B1 | PASS, exactly once | stalled |
| B2 | PASS, exactly once | stalled |

In all cancellation cases caller.cancel() returned True, run_test raised
CancelledError, and the caller reached done=True/cancelled=True/cancelling=1.
At the two-second diagnostic watchdog the shared runner was still pending with
cancelled=False/cancelling=0. The test's finally and fixture cleanup had not started;
the teardown caller was also pending. The normal cases reached test finally and
exactly one same-task cleanup including ContextVar reset and normal runner exit.
The watchdog exits the process without extra cancellation; its exit code zero is
not successful fixture cleanup. These are bounded observed stalls, not an assertion
about all schedules or every cancellation entry point.

## Interpretation and next decision

Direct caller cancellation did not propagate to the active coroutine in this
reproduction, on base or any new candidate. This does not establish an introduced
regression, an A/B advantage, or failure of the original KeyboardInterrupt repair.
The task issue names KeyboardInterrupt and normal pytest outcomes; its visible
explicit_cancel case cancels the test coroutine, not the separate waiting caller.
This synthetic internal-task cancellation is a distinct support/coverage decision.
Before adding it as a required check, establish that cancelling this internal caller
is an intended supported operation or corresponds to a real supported entry point.
If it is in scope, define propagation plus same-task cleanup together; do not merely
require the caller to report CancelledError. No task or runtime change was adopted.

## Evidence and validation

Raw packet: `C:\pt\analyses\anyio-caller-preservation-20260927-v1`.
Analysis: `C:\pt\analyses\anyio-caller-preservation-analysis-20260927-v1`.
The analysis verifies CAS/program/stdout bindings, normal cleanup counts and task
ownership, cancellation states, and unchanged prior candidate journals. All ten
owned probe containers were confirmed absent; candidate diffs stayed unchanged.
No provider calls, API input counts or API cost. No new isolated acceptance/safety.
All older acceptance results and closed allocations remain unchanged.

Focused diagnostics/documentation tests passed (15); Ruff passed. Mock smoke
`C:\pt\caller-preservation-smoke-0927a`, run `run_dev_fe2bfa291f6f4a03`, reached
EVALUATOR_PASS with safety NOT_RUN. Full test suite was not rerun for this standalone
diagnostic. Generated receipts and analysis use external CAS and hash-chained journals.
