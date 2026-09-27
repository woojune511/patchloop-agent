# Caller cancellation observation, 2026-09-27

## Problem and hypothesis

In the closed checkpoint comparison, B1, B2 and A2 conditioned their first repair
on cancellation of the waiting caller. Their inherited public probe measured shared
runner liveness and test resumption, but never measured caller cancellation. The
same three interrupt cases failed in those first repairs. The immediate question
was factual: does the callback KeyboardInterrupt actually cancel that caller?

This operator diagnostic adds observations to the existing reproduction and checks
an explicit-caller-cancel positive control. It does not change task source, runtime,
agent guidance or any old episode. It is not a new paid comparison.

## Design and provenance

- Task base: AnyIO `cb245dba9883516f2ed4c23899de157183a1cb50`, v3 public task.
- Fresh workspace from the existing hash-bound prepared source; no source fetch.
- Existing selected pytest dependency manifest:
  `sha256:ae8d0a01dd8c67305ea620a885a75c73344979104f6d067e83dc3aebc79f143e`.
- Probe environment: pinned Python 3.12 image/profile, actual Python **3.12.13**;
  two isolated executions, unchanged source, no network, normal 30-second probe cap.
- Driver: `diagnostics/anyio_caller_probe.py`; program:
  `diagnostics/probes/anyio_caller_state.py`; hidden contract:
  `.agent/caller-state-probe.md`.
- Packet: `C:\pt\analyses\anyio-caller-state-20260927-v1`; journal:
  `run_dev_callerstateprobe`. Exact programs, source hashes, receipts, runtime and
  implementation identities were bound before execution. The execution HEAD is
  the pre-commit repository HEAD; the newly added diagnostic's own hash binds its bytes.

The program captures the one existing `_call_in_runner_task` Task while the shared
task executes the test. It creates no new Tasks, changes no methods and inserts no
awaits. State reads occur synchronously before the trigger, after `run_test` raises,
before/after fixture teardown and after normal runner exit. Only the positive-control
mode calls `caller.cancel()`. Program bodies are otherwise identical.

## Results

Both probes exited zero, without timeout/truncation/cleanup failure. The callback
case reproduced the original lifecycle: test resumes only on teardown, and fixture
cleanup completes on the shared task. All four original observation stages matched
event order, task ownership and runner completion after ignoring process-local IDs.
That is discrete observation parity, not proof that instrumentation cannot affect
any timing-sensitive execution.

| Case / boundary | Caller done | Caller cancelled | Caller cancelling | Shared runner cancelling |
| --- | --- | --- | --- | --- |
| Callback KI, before trigger | false | false | 0 | 0 |
| Callback KI, after run_test raises | false | false | 0 | 0 |
| Callback KI, before teardown | false | false | 0 | 0 |
| Callback KI, after teardown | true | false | 0 | 0 |
| Explicit cancel, just after accepted request | false | false | 1 | 0 |
| Explicit cancel, after run_test raises CancelledError | true | true | 1 | 0 |

The explicit control demonstrates that the observation can detect cancellation
requests and completed cancellation. Cancelling the caller did not itself cancel
the shared runner in this base program. Both test bodies eventually progressed;
the positive control validates instrumentation, not desired task semantics.

Normal context-manager exit later cancelled the shared runner in both cases
(`done=true`, `cancelled=true`, `cancelling=1`). That later shutdown must not be
mistaken for cancellation at the interrupted test boundary.

**Conclusion:** this callback interrupt leaves an uncancelled waiting caller.
A repair guard requiring that caller's cancellation does not match the observed
condition. This conclusion is scoped to the unmodified task base, this callback
reproduction and the pinned probe environment. It is not a universal claim about
OS SIGINT, asyncio.Runner signal handlers or all cancellation propagation paths.

## Validation, limits and next decision

Five focused tests cover the positive control requirement, completed-versus-cancelled
distinction, inconclusive observations, mode-only program variation, and detection
of changed event order/task ownership. Documentation checks and Ruff pass. Real
probe receipts establish the measured behavior; unit fixtures are not that evidence.
The new workspace remained unchanged and both exact owned containers are absent.
Runtime hash remains
`sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.

Model calls/counts and new billed cost are zero. Acceptance, task safety and agent
improvement are NOT_RUN. No final candidate was repaired or evaluated, no old probe
output/history was overwritten, and no paid allocation was reopened. The existing
explicit-cancel plain-fixture same-task coverage gap is not closed: this positive
control cancels the waiting caller, not the test coroutine used by that public check.

The next causal question is whether adding the measured caller state, with guidance
and other controls fixed, changes the first repair and regression outcome. A future
comparison must represent this as later operator evidence, preserve original history,
freeze exact inputs and get separate task/model/repeat/cap approval before dispatch.
No generic prompt rule or adoption follows merely from knowing the correct fact.
