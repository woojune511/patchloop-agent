# B1 cleanup stall: cancellation origin and a second runner cancellation

Date: 2026-09-27. Provider-free operator diagnostic; official=false.

## Problem, alternatives and controlled reproduction

The [closed information comparison](2026-09-27-caller-information-results.md)
left B1's first patch blocking fixture cleanup while B2's first patch completed.
Repeated runner cancellation and failure to drain pending work were competing
explanations, not established causes. The user authorized the proposed bounded
provider-free investigation; no previous paid allocation was reopened.

`diagnostics/anyio_cleanup_probe.py` restored each first accepted patch from its
closed public action journal in a fresh prepared-source workspace. Original
preimage, postimage and complete-diff hashes matched. These are first patches,
not B1's later final workspace. Existing source, dependency and probe image/profile
identities were retained. No evaluator inputs were inspected or projected.

The public program drives TestRunner with a ContextVar async-generator fixture
and a callback KeyboardInterrupt, matching the relevant public lifecycle pattern.
It captures the existing caller and runner, without task wrappers, extra awaits
or method monkeypatching. Each candidate ran once with filtered synchronous Python
source-line tracing and once without it. A two-second diagnostic timer captures
stalled state and exits the isolated process, without requesting extra cancellations.
That watchdog exit is an incomplete lifecycle, not a successful task or cleanup.
The sandbox deadline and cleanup receipt remain independent checks.

Four original-patch executions were followed by a two-execution B1 ablation, after
the B1 trace showed the second cancellation. The ablation removes only
`self._runner_task.cancel()` in the waiting caller's CancelledError handler.
It retains the run_test cancellation, all future logic and the rest of B1's code.
No uncancel call or explicit drain was added. The driver/program bytes stayed
fixed across both phases; the source delta was verified as exactly one deleted line.

## Observations and causal result

| Candidate | Tracing off / on | Runner requests before cleanup | Fixture cleanup |
| --- | --- | --- | --- |
| B1 first patch | Both watchdog exits | run_test, then waiting caller | Never starts; teardown caller waits |
| B2 first patch | Both complete | run_test only | Once, same original task |
| B1 minus caller-side cancel | Both complete | run_test only | Once, same original task |

At B1's run_test escape, the original waiting caller is pending and has zero
Task.cancel requests. run_test cancels its submission future and the runner.
On loop re-entry, the runner handles cancellation of the test coroutine and
returns to `async for coro, future in receive_stream` outside the per-coroutine
try/except. The caller then receives CancelledError from its already-cancelled
future. Its own cancelling() remains zero, yet its unconditional handler issues
a second runner cancellation. The trace observes runner cancelling 0 -> 1 -> 2.
At the watchdog boundary, the runner is done/cancelled and a separate teardown
_call_in_runner_task remains pending on its future. No fixture-cleanup-start event
was emitted, and post_interrupt did not execute.

On the saved B1 first source these runner.cancel sites are run_test line 2336
and _call_in_runner_task line 2285. The submitted-coroutine handler has already
returned to receive_stream before the second site runs. The second cancellation
therefore terminates the shared worker rather than merely stopping the old test.

B2 uses a guarded caller-cancellation path, uncancels the runner after a submitted
coroutine cancellation and drains the existing caller from run_test. The measured
caller has cancelling() == 0, so it does not issue another runner cancellation.
The worker remains alive for fixture teardown. These B2 differences are bundled;
their individual necessity cannot be inferred from B1/B2 alone.

The B1 one-line removal isolates the second request: without adding uncancel or
draining code, it prevents post_interrupt execution, propagates KeyboardInterrupt,
completes fixture cleanup once on the original task, restores the ContextVar token
and exits normally. The runner remains pending with cancelling() == 1 after
teardown. A nonzero cancellation counter by itself is therefore not the cause of
this stall. The normal subsequent shutdown adds another cancellation, producing
2 after exit; that late count must not be confused with B1's early double cancel.

For all three candidate pairs, tracing on/off produced identical recorded lifecycle
boundary states and event order/ownership. This supports those discrete observations;
it is not proof of general timing neutrality. All six processes exited under the
intended diagnostic protocol, with no sandbox timeout/truncation/cleanup uncertainty.
All six owned containers were absent and candidate workspaces stayed unchanged
during execution. Original live histories and saved patches remain immutable.

## Meaning for the agent and next question

The local failure was a distinction between an exception received from a cancelled
future and an explicit cancellation request on the waiting task. Both can surface
as CancelledError; they do not justify the same additional runner action. The earlier
supplied observation changed B1's first interrupt handling but did not ensure this
second distinction was implemented correctly. This diagnostic measures candidate
behavior, not the model's private reasoning or a general model capability.

The ablation is not adopted as a repair. Removing the caller-side action may affect
actual caller.cancel() handling, which this callback reproduction did not execute.
The next useful check distinguishes those cancellation origins while preserving
interrupted-test termination and same-task fixture cleanup. Registered checks,
isolated acceptance/safety and agent improvement for the ablated patch are NOT_RUN.
The old public explicit-cancel case targets the test coroutine, so it does not
substitute for explicit cancellation of the waiting caller. No new prompt, memory
policy, live comparison or paid retry follows automatically from this result.

## Evidence and validation

- Original first patches: `C:\pt\analyses\anyio-cleanup-trace-20260927-v1`.
- One-line ablation: `C:\pt\analyses\anyio-cleanup-ablation-20260927-v1`.
- Verified synthesis/script: `C:\pt\analyses\anyio-cleanup-analysis-20260927-v1`.
- B1 first diff: `sha256:98f2a7addca143126102a85752908891b2e33fbd0330851dca55bb80c4feb243`.
- B2 first diff: `sha256:c99241fc8be70143e2d2203102b6f52107ee2f29cec88142d1a5f080d27de854`.
- Ablated B1 diff: `sha256:f485f75c517a81e054e5b364b46a1661df6213fd561777f2f1c03a9642aaa429`.

Focused tests cover unique one-line removal, preservation of the outer request,
changed/failed source-journal rejection and identical traced/untraced program bodies.
Documentation checks and scoped Ruff pass; exact final reports and hashes are in
the external validation receipt. Mock smoke `run_dev_65e0259c43c44ec3` reached isolated
EVALUATOR_PASS, with mock Docker safety NOT_RUN. The full repository pytest suite
was not rerun for this operator diagnostic. Actual model calls/counts/cost are zero.
Runtime remains `sha256:e3b533ac585ea2b48d159a6f8449d3996cd991b3da73fa268dbda71f8d5230c3`.
