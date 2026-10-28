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
current-diff checks and deliver their failures. Keep the restored caller observation
choices and minimum completion admission from the
[observation-opportunity change](history/2026-10-28-observation-opportunity.md).

The [helper API contract change](history/2026-10-29-helper-api-contract.md) now shares
signatures, mode availability and limits between descriptions and trusted runtime.
Definite direct-call mistakes are rejected before dispatch in both helper and
original modes. Dynamic calls receive precise runtime errors: setup binding metadata
or observed-target field/count/limit stderr. Both error paths reach the next counted
model request, and corrected calls execute without resetting counters or replaying
settled actions. Unknown execution and original verification remain independent.

Fresh v11 uses a hash-bound trusted module; saved v1-v10 programs remain byte-exact.
Observer/source/resource limits are unchanged. Local evidence: focused 161 PASS in
42.162 seconds, quick 855 PASS in 115.437 seconds including isolated mock evaluation,
and Ruff PASS. That evidence is separate from the live outcome below.

The [latest clean-start result](history/2026-10-29-helper-contract-fresh-results.md)
is EVALUATOR_PASS with cases_verified_delivery on Astroid-1333. The full model
gpt-5.4-2026-03-05(xhigh) acquired original F0010 without API correction, made one
edit to normalize caller-supplied search paths, and passed the identical original
replay with F0010 absent and W0611 processing markers in both calls. Current-diff
regression passed 1231 tests; isolated acceptance and safety both passed.
It spent USD 2.0153455/4.50, 18 responses, 32 actions and 609.474 active seconds.
The allocation is CLOSED. No prior patch, checkpoint or operator observations were seeded.

The model chose observe_original, but call tracing hit its 200000-event limit and
remained UNKNOWN/insufficient. A general helper also caught an AttributeError in
result formatting. Do not describe the repair as confirmed by a complete call trace.
API correction and failed-repair/regression revision were NOT_EXERCISED. Fifteen
responses were used before the first edit. Keep the contract fix; repeatability,
observation usefulness and generalization remain unresolved by this one exposed
development task. Prior paid allocations remain closed.

Next, the [frozen-runtime three-task check](history/2026-10-29-helper-transfer-three-plan.md)
is prepared on current-dev20 rows 5/9/18 (pvlib, pydicom, SQLFluff), one fresh run
each. Model and per-task limits stay fixed; proposed caps are USD4.50 each and
USD13.50 total. New dependencies, public capability checks, first-request audits
and batch stop rules passed locally. Paid execution is NOT_RUN and exact new
scope approval is pending. This exposed development panel cannot establish
held-out generalization or a causal improvement over another agent.

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
uncertainty. Saved-candidate and operator successes remain distinct from the single
clean-start development success above. Repeated fresh-solve performance and held-out
improvement remain unverified.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
