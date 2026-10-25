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

The [diagnosis-mode change](history/2026-10-26-diagnosis-mode.md) projects the existing
run_probe from the host workflow gate: pending diagnosis requires a symbolic
call_path, with question/source/replay/purpose restricted to null. Its description
covers only selecting public functions/fields. The host still binds the frozen
original and current source. Exact invalid-field feedback is preserved through
later preparation; request correction and actual execution remain separately bounded.

Core local validation: 96 PASS in 45.373 seconds, Ruff PASS. The saved rejected
request reports question/purpose precisely; clearing just those fields passes
static construction. Nine ordinary-mode schemas are byte-identical to baseline.
A scripted mixed-request rejection, correction, diagnosis, repair, original recheck
and submission reaches isolated mock evaluation. Quick integration: 366 PASS in
73.608 seconds, including isolated mock evaluation.

The [last live pilot](history/2026-10-26-diagnosis-request-live.md), before this change,
ended VERIFICATION_INCOMPLETE: one mutation left F0010 unchanged and its diagnostic
request was rejected before construction. It spent $1.059124500 of $1.20; that
allocation is closed. Checks, submission and independent evaluation were NOT_RUN.
Both path-preparation projections matched offered tools; helper correction was
NOT_EXERCISED. Current changes have not had a live model pilot.

The remaining question is whether the narrowed contract enables an informative
diagnostic and an evidence-based repair within the existing limits. Static request
admission, shorter descriptions and local mock completion do not establish model
uptake, output-token savings or F0010 repair. No automatic continuation is authorized.

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
uncertainty. The latest live run acquired the original failure and made one
ineffective mutation; checks, finish and independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
