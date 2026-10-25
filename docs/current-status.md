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

The [helper correction](../.agent/helper-correction.md) now makes mode-specific APIs
explicit and catches syntax/unbound original-only names before a fresh helper runs.
Before the first accepted mutation, one same-question corrected source request can
use existing minimum completion resources. Unrelated inspection cannot spend that
opportunity; rejection or unaffordable correction returns verification incomplete.
Returned execution remains diagnostic evidence, not original-call verification.
The implementation deliberately does not infer pre-target failure from arbitrary
runtime exceptions. Saved programs, exact action recovery and original-case replay
keep their existing identities. No resource cap is increased.

The [implementation record](history/2026-10-25-helper-correction.md) records 64 core
tests in 23.548 seconds and 346 quick tests in 66.949 seconds, including isolated
mock evaluation; Ruff passes. The saved failed source's line-8 unavailable API is
rejected without executing the target. Actual model uptake and F0010 repair benefit remain
unmeasured. The next evidence question is whether this bounded correction produces
a usable diagnostic before the first repair under the same live limits.

The [previous live pilot](history/2026-10-25-callpath-live.md) reproduced F0010 but
made no mutation before exhausting 40K normal and 25K correction output; allocation
closed. The [audit](history/2026-10-25-helper-stop-analysis.md) found delivered error
feedback and four available probe opportunities spent on source inspection. Thus
the post-mutation [call-path mechanism](../.agent/repair-path.md) remains locally
tested but NOT_EXERCISED by that live model. New runtime preparation and exact live
authorization remain separate from this implementation's local validation.

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
uncertainty. The latest live run acquired the original failure but never mutated
source; finish and independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
