# Current status

Updated: 2026-10-26. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- General baseline: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Selected policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled with
  policy none, repair-recheck, protected-v1 inspection, per-call-v1 cost admission.
- Limits: 40 model calls, 100 actions, four accepted edits, 1,800 seconds.
  Paid work also requires the exact task/model/credential/repeat scope and cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These are selected settings, not CLI defaults or evidence of general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

Implement the [first-repair observation and small request path](history/2026-10-26-first-repair.md).
After an acquired original failure and a distinct clean control, `observe_original`
selects one or two candidate functions and event predictions. The host replays the
frozen original program and derives parameter/line watches. Tracing covers the
selected call window even if the candidate never enters. Complete no-hit and
incomplete collection remain distinct; predictions test premises, not repairs.

Fresh `replace_text` uses six execution/intent fields; `stop_task` uses two.
Neither requires decision/plan/memory metadata. Legacy explicit annotations remain
recoverable. Ordinary repair has a small public evidence view; no-action correction
starts a fresh compact segment with original observations, source anchors and the
same budgets. Field/anchor errors retain typed correction. The existing post-edit
path diagnosis links the next explicit hypothesis without duplicate causal_revision.

One pre-edit observation is optional. Exploration preserves its successful
edit/replay/check/finish successor using existing protected slack, without adding
it twice. Request rejection, actual dispatch, completed reuse and uncertainty have
separate durable identities; restart or new action names do not renew allowances.
The next mutation links its observation receipt, which becomes historical after edit.

Final focused/resource controls: 154 PASS in 18.68 s. Earlier quick: 363 PASS and 11
old expectation/doc failures; those 11 pass after targeted fixes. A later audit fixed
the last-observation reserve after a rejected edit, including diagnostic checks and
two-child tests; the 154 controls verify that final runtime. Quick includes isolated
mock acceptance. Ruff passes; see the record for phase identities. No live model run was made.
The latest closed pilot still made zero edits; its diagnosis was NOT_EXERCISED.
The unresolved question is whether this intervention lets the model turn an
original-call observation into an effective first repair under the same limits.
Local controls do not establish F0010 repair success or general improvement.

## Supporting evidence

- [Security maintenance](history/2026-10-23-security.md): refreshed host dependencies
  and public Python 3.12 images after the emSign incident. Old task/legacy images
  remain offline-only. New runs need newly prepared identities; prior manifests
  do not authorize execution against the updated runtime.
- [Helper-path results](history/2026-10-22-helper-path-results.md): useful information,
  no repair in A1/B1/B2; partial comparison stopped on drift. Allocation closed.
- [Invocation linkage](history/2026-10-22-probe-invocation-results.md): submitted
  repairs 0/3; ON mechanism use 0/2. Partial run; no adoption or quality claim.
- [Caller evidence](history/2026-10-19-caller-evidence-results.md): A/B 0/6;
  original-caller verification remained missing.
- [Portfolio remeasurement](history/2026-10-06-portfolio-dev20-results.md): 9/20,
  below the 11/20 threshold; test300 remains unprepared and unauthorized.
- [History](history/README.md) indexes the closed investigations and allocations.
  Their past next steps, settings and approvals do not carry forward.

## Execution and claim boundaries

All prior paid allocations are closed. The [older interrupted call](history/2026-09-28-expectation-review-results.md)
retains unknown billing; later settled allocations do not resolve it.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. The latest live run acquired the original failure but made no mutation;
diagnosis was NOT_EXERCISED, and checks, finish and independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
