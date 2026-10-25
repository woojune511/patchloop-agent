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

The [resource pilot](history/2026-10-25-completion-resources-live.md) ran once with
normal output 40K, independent correction 25K and the same USD1.20 cap. It ended
INCOMPLETE_RESPONSE after 30 model calls, 28 actions and USD1.080337500, with no
edits, regression checks, submission or independent acceptance.

Actual original-call stdout contained F0010. The authored probe checked stderr
only and recorded false/false; the exact captures reached the next model input,
but its public notes treated the failure as absent. Two original attempts ended
without formal acquisition, followed by 26 source inspections. The final normal
response exhausted its admitted 15,154 tokens; the reserved 25K correction then
also exhausted without a tool call. Counting/billing were known; allocation closed.

The [resource follow-up](history/2026-10-25-completion-resources.md) and its
[contract](../.agent/completion-resources.md) remain implemented: reuse-aware
completion forecasts, an independent correction allowance and one bounded
diagnostic after comparable original failure on a candidate. The separate
correction reservation/dispatch was exercised. Reuse savings and the diagnostic
opportunity were not exercised because no acquired failed candidate existed.
The earlier [40K pilot](history/2026-10-25-output40-live.md) acquired a failure and
made three ineffective edits; one stochastic trajectory per condition does not
establish a causal regression or improvement.

Next question: how to check that an authored baseline observation agrees with
captured diagnostic output before its interpretation drives repair planning.
The current evidence distinguishes a predicate/channel error from lost capture;
no corrective implementation or new paid run is implied. The original invocation
v4 identity and finish gates remain: comparable failure blocks finish, and
missing/incomparable evidence stays unverified. Local validation remains 56 focused
checks (45s), 12 final diagnostic checks (15s), 305 quick checks (31s), Ruff and
isolated mock evaluation. Live repair gain and useful diagnosis remain unverified;
general output and cost-policy defaults are unchanged.

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
uncertainty. The latest live run captured the original symptom but failed formal
acquisition because of the authored predicate; it did not reach mutation, finish
or independent evaluation. Linux CI and general improvement remain unverified.
