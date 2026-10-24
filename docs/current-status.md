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
and credits correction only after actual argument changes pass full preflight.
The [size repair](history/2026-10-24-size.md) separates 8,000-character authored and
host observer allowances while preserving bounded transport and replay identities.
The [call adapter and capture](history/2026-10-24-capture.md) now use native Python
argument syntax and expose each call's return value, stdout/stderr and outcome.
Fresh cases use invocation v3 / tool contract v53. Truncated or unexpected results
remain unverified; old v1/v2 programs replay exact bytes. Frozen comparisons,
original-failure acquisition and completion semantics are unchanged.

The closed [invocation pilot](history/2026-10-24-invoke-live.md) used correct list
arguments and captured F0010 on stdout, but checked stderr, mixed execution metadata
into a different observation shape and omitted a normal-input control. Original-case
acquisition failed. After 27 further inspections and no edit, the run ended
COST_CAP_REACHED. Independent acceptance/safety and post-submission checks are NOT_RUN.

The [observation-contract fix](history/2026-10-25-observation.md) separates small
comparison values from existing call diagnostics in tool guidance, clarifies
channel/outcome/exit-code interpretation, and adds bounded field differences to
healthy v3 comparison receipts. It retains exact frozen equality and unverified
results for incomplete observations. A mismatch is explained, never auto-corrected;
there is no universal same-shape gate or new exploration/budget policy.

The [fresh observation pilot](history/2026-10-25-observation-live.md) is closed.
It observed F0010 on the failing call and not on the control, with a small consistent
JSON value. The host qualified original-failure acquisition; field feedback reached
the next actual model request. This sample supports observation construction, not
the usefulness of feedback for correcting a malformed predicate: none occurred.

Nineteen subsequent inspections produced no edit, although mutation was offered
from model call 4. Calls 1, 22 and 23 exhausted their output ceilings without a tool
call; the last occurred after inspection closed. The run ended INCOMPLETE_RESPONSE
after 517.658 seconds at USD 0.788844900 of its USD 0.88 cap. Candidate replay,
required checks, submission, independent acceptance/safety and post-submission
public checks are NOT_RUN. This was not a COST_CAP_REACHED terminal.

The first unresolved executed stage is now evidence-to-edit. Cross-execution
condition stability also remains untested: the probe used a random temporary cwd,
HOME pointing there and no selected input fingerprints. One exposed-task sample
does not establish repair gain or a causal effect. No new remedy or paid allocation
is selected; prior local 271-case split validation and 35 observation controls stand.
The [operator oracle experiment](history/2026-10-24-oracle.md) remains separate;
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
