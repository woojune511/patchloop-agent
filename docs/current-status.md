# Current status

Updated: 2026-10-25. Runtime source owns behavior. Historical reports are evidence,
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
and credits correction only after changed arguments pass full preflight. The
[size repair](history/2026-10-24-size.md) separates authored and host observer
allowances. The [call adapter/capture](history/2026-10-24-capture.md) uses native
Python arguments and per-call return/stdout/stderr/outcome receipts. Fresh cases
use invocation v3 / tool contract v53; old v1/v2 programs retain exact bytes.

The [observation-contract fix](history/2026-10-25-observation.md) separates small
comparison values from diagnostic metadata, clarifies channel/outcome semantics
and supplies bounded field differences for healthy v3 comparisons. Strict frozen
equality and unverified results for incomplete observations remain unchanged.
Its local evidence is 271 selected passes in split validation, including 35
observation controls, plus Ruff and isolated mock evaluation.

The [observation pilot](history/2026-10-25-observation-live.md) acquired a faithful
failure/control but made no edit after 19 inspections. Three responses exhausted
their output limits; the final two allowances were admission-reduced. It ended
INCOMPLETE_RESPONSE at USD 0.788844900 of its USD 0.88 cap, without submission.

The [cap-only pilot](history/2026-10-25-budget-live.md) changed the invocation cap
to USD 1.20 with identical runtime/task/model/policies and a fresh run. All 30
model calls received 25,000 output tokens; no response was incomplete. After 24
inspections it made a source edit and a helper regression test, passed the public
regression (1,232 passed, 69 skipped, 15 xfailed), and submitted. Cost was USD
0.821097150 over 655.403 seconds. These are two single stochastic samples on an
exposed task; cap-induced improvement and generalization remain unestablished.

The submitted patch still produced F0010 on the original failing input. Separate
frozen public checks returned failure-input FAIL / normal-control PASS; registered
independent acceptance was FAIL and safety PASS. Terminal: EVALUATOR_FAIL. This
is progress to submission, not a successful repair. The allocation is closed;
unused budget does not authorize another solve or a default cap increase.

The first unresolved repair question is whether the helper-based hypothesis
changes the original caller's failing path before finish. Automatic replay ran
inside the final finish request, with no later model turn to use its failure or
changed-line feedback. Its launch-thread collector did not observe the newly
added resolution branch; this is bounded line evidence, not full branch coverage.

Completion also stayed unverified: normalized caller arguments and selected input
content matched, but random HOME/PYLINTHOME hashes and the host line-tracing argv
changed call identity. Keep repair correctness and this comparability defect
separate; delivery was correctly labeled unverified_delivery, not cases_verified.
No runtime fix or further paid run has been selected. The
[operator oracle experiment](history/2026-10-24-oracle.md) remains separate;
historical observations and submissions are never regraded.

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
