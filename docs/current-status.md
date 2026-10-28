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

The [caller/completion implementation](history/2026-10-28-caller-completion-paths.md)
connects registered dependency reads to ordinary `run_dev`. Use repeatable
`--caller-source distribution=directory` with prepared pinned caller dependencies;
no roots are inferred automatically. Actual counted/dispatched tools expose the
scope, and observed source reaches the next model input. Caller bodies remain
read-only, separately bounded, and cannot supply repository mutation anchors.
Registration and prepared identity are immutable across recovery.

Ordinary `completion-recovery-v1` admission derives response/action counts,
role-based cost and nominal time from shared completion-path steps. Required
completion retains diagnosis, unused request correction, missing anchor, repair,
original replay, fresh public checks and finish. One possible later original or
public-check failure is separately protected when feasible. Known-original-failure
exploration can release that speculative reserve; the selected guarantee is visible
per action. Actual mandatory floors and global caps remain. Acquisition, first
observation, general probes and special correction/test paths keep a labeled
conservative adapter.

Local caller controls passed 39 tests (three platform skips); budget controls
passed 97. Quick had 698 PASS and six contract/doc failures, all resolved by focused
rechecks; both isolated mock evaluations passed. Saved-state policy replay opens
reads at three previously closed points while preserving the final mandatory floor.
This is local mechanism evidence, not model uptake or a successful F0010 repair. The previous
[same-budget live follow-up](history/2026-10-28-diagnosis-exploration-results.md)
still failed after three edits: two retained F0010 and the third produced a
downstream caller exception. Public checks, finish and isolated acceptance were
NOT_RUN. The [analysis](history/2026-10-28-caller-budget-analysis.md) found source
access and inconsistent reservation constraints; neither alone proves the cause
of every ineffective edit. Its final required-completion response floor remains
binding. The unresolved question is whether the model now investigates the caller
and repairs correctly within the same caps. Latest live cost USD1.133929 of
USD4.13241570; this allocation and all earlier allocations are CLOSED. No further
run is funded.

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
