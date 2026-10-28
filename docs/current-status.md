# Current status

Updated: 2026-10-29. Runtime source owns behavior. Historical reports are evidence,
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

Keep the [required-public-check design](history/2026-10-28-required-public-checks.md):
known FAIL and required NOT_RUN block successful finish; edits require fresh
current-diff checks and deliver their failures. The assisted saved-candidate
[continuation](history/2026-10-28-required-public-check-repair-results.md) passed11
public cases,1231 regressions and isolated acceptance/safety. That is not a fresh
solve or generalization estimate; its allocation is CLOSED.

The prior [clean-original attempt](history/2026-10-28-autonomous-fresh-results.md)
reproduced F0010 but left processing unverified after two downstream repairs and
exhausted its tool horizon. The [public analysis](history/2026-10-28-autonomous-fresh-analysis.md)
identified unequal read/probe cost admission and an inactive ruleless call selector.
The [observation-opportunity change](history/2026-10-28-observation-opportunity.md)
restores those choices with shared minimum completion reservations and keeps the
original verification requirement. Typed v10 settings rejection separates a known
pre-target request error from UNKNOWN; it refunds no costs or attempts.

The [latest live follow-up](history/2026-10-29-observation-opportunity-fresh-results.md)
ended EVALUATOR_FAIL/unverified_delivery: public regression1231 PASS, isolated task
acceptance FAIL, safety PASS. It spent USD1.476264,12 responses,22 actions and851.269
active seconds. Its allocation is CLOSED. Two helper construction errors prevented
any original reproduction, so post-reproduction observation uptake remains untested.
The first description omitted check_setup's signature; descriptions omitted input_paths
maximum4, and the runtime message did not identify the offending field. The model
corrected the first error, then hit the second constraint. Overall budget exhaustion
was not the terminal cause.

The [helper API contract change](history/2026-10-29-helper-api-contract.md) now shares
signatures, mode availability and limits between descriptions and trusted runtime.
Definite direct-call mistakes are rejected before dispatch in both helper and
original modes. Dynamic calls receive precise runtime errors: setup binding metadata
or observed-target field/count/limit stderr. Both error paths reach the next counted
model request, and corrected calls execute without resetting counters or replaying
settled actions. Unknown execution and original verification remain independent.

Fresh v11 uses the same validator from a hash-bound trusted module; saved v1-v10
programs stay byte-exact. Observer 8K, authored-source and total resource limits are
unchanged. Core validation: 161 PASS in 42.162 seconds; quick integration: 855 PASS
in 115.437 seconds, including isolated mock evaluation. Ruff passes. This is local
mechanism evidence; commands and limits are in the linked implementation report.
No live model call, benchmark rerun or new allocation was made for this change.

The [clean-start helper follow-up](history/2026-10-29-helper-contract-fresh-plan.md)
is prepared for Astroid-1333, the same full model and limits, one run and a proposed
new USD 4.50 cap. Offline first-request and read-only identity preflight pass; new
exact execution/cap approval is pending. It asks whether valid original execution
now enables useful observation and repair. No live call or F0010 repair gain is
established. Previous paid allocations remain closed.

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
