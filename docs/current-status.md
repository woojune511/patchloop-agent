# Current status

Updated: 2026-10-28. Runtime source owns behavior. Historical reports are evidence,
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

The [required-public-check continuation](history/2026-10-28-required-public-check-repair-results.md)
repaired the saved candidate's three public regressions in two new edits. The first
edit still failed the required matrix; its exact output reached the next request.
The second edit passed all 11 required public cases while preserving the original
call and positive processing evidence. Public regression passed 1231 tests; normal
finish then reached isolated task acceptance PASS and safety PASS.

The [required-public-check design](history/2026-10-28-required-public-checks.md)
is retained: explicit host-registered public counterexamples join execution,
current-diff status, automatic repair feedback, completion and budget paths.
Initial imported failures retain their provenance; recovery preserves their binding.
Model notes and speculative questions remain advisory.

Known FAIL and required NOT_RUN block successful finish regardless of unused budget.
An accepted edit needs the same check on the new diff; its result reaches the next
model response. Resource exhaustion or explicit stop preserves unresolved status.
The frozen diagnostic's 11-case host assessment now runs before completion through
its prepared environment. The old separate final replay reservation is removed;
normal check actions/time are budgeted, and final reporting reuses receipts.

The authorized single run used five model responses, nine actions and USD0.90023750
of its USD3.38078870 cap. Its allocation is CLOSED. This is a successful assisted
checkpoint repair, not a fresh solve or a causal/generalization estimate. F0010
already passed at the starting candidate. One preexisting public discrepancy stays
excluded from the mandatory 11 and is still reported as FAIL.

Caller-source access, original-call/processing verification, bounded exploration
and shared completion-path reservations remain active. The first request allowed
repair/stop; optional inspection reopened after the first failed repair. Successful
delivery, public PASS, isolated acceptance and safety remain separate evidence.
The [clean-original follow-up](history/2026-10-28-autonomous-fresh-plan.md) is prepared
to test the whole normal runner on Astroid-1333 with the same full model and original
USD4.50/2400-second limits. It supplies no saved patch, prior observations or operator
counterexamples; explicit read-only pylint access remains. No supplemental registry
is injected, so the new required-counterexample mechanism is NOT_EXERCISED in this
trial. Offline first-request audit and read-only preflight passed; exact command
confirmation is pending. No new paid execution has started.

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
retains unknown billing; later settled allocations do not resolve it. The latest
source-ready diagnostic also retains one unsettled response.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. Earlier saved candidates failed isolated acceptance; the clean-source operator
resolver candidate passes. The saved-evidence A model trial now passes acceptance;
fresh-solve and held-out improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
