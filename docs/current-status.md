# Current status

Updated: 2026-10-24. Runtime source owns behavior. Historical reports are evidence,
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

[Request correction](history/2026-10-23-requests.md) binds public task/issue identity
and credits correction only after actual argument changes pass full preflight.
The [size repair](history/2026-10-24-size.md) separates 8,000-character authored and
host observer allowances while preserving bounded transport and replay identities.
The [call adapter and capture](history/2026-10-24-capture.md) now use native Python
argument syntax and expose each call's return value, stdout/stderr and outcome.
Fresh cases use invocation v3 / tool contract v52. Truncated or unexpected results
remain unverified; old v1/v2 programs replay exact bytes. Frozen comparisons,
original-failure acquisition and completion semantics are unchanged.

The preceding [repair pilot](history/2026-10-24-repair-live.md) failed original
acquisition and repair: a string was passed where pylint expected a list, and the
model searched the returned object instead of emitted diagnostics. The new local
four-condition experiment held the unchanged Astroid base, fixtures and predicate
fixed. Only correct arguments plus consuming captured output distinguished the
declared failure from the normal control. Four Docker probes completed in 44.608
seconds with complete capture and confirmed cleanup; provider calls/cost were zero.

This supports the local calling/observation mechanism. It does not establish that
the model will choose the correct arguments or predicate, acquire the failure or
repair the task. The adapter checks Python binding, not semantic input validity.
Autonomous uptake and repair remain the next unresolved question; no fresh paid
run is authorized by these local results. The [operator oracle experiment](history/2026-10-24-oracle.md)
remains separate. Prior mismatches and submitted repairs are never regraded.

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
uncertainty. A live replay of an unacquired case is observed; replay/rejection after
a faithfully acquired original failure, Linux CI and general improvement remain
unverified.
