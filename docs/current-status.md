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

The [canonical diagnosis](history/2026-10-28-canonical-diagnostic-analysis.md)
identified skipped target processing hidden by error absence, generated cache in
fixture identity, and pre-target request errors entering case accounting. The
[processing-evidence implementation](history/2026-10-28-processing-evidence-implementation.md)
addresses these mechanisms in invocation v7 / diagnostic v2. Surface v66 additionally
shortens only first-reproduction instructions; schemas and host checks remain intact.

The [fresh pilot](history/2026-10-28-processing-evidence-fresh-results.md) exhausted
40K ordinary and 25K correction output before an original probe or edit. Its
USD 0.40966830 allocation is closed. The subsequent
[description A/B](history/2026-10-28-first-reproduction-description-results.md)
completed both responses within their limits. Long A produced an admitted call and
reproduced F0010 but selected only error-presence booleans, without positive intended-
file processing evidence. Short B was rejected for callable/code-format errors before
execution. Total new cost USD 0.1688805; that allocation is also closed. Neither arm
repaired, submitted or evaluated. B's post-validation correction was not tested.

The [model-only pair](history/2026-10-28-first-reproduction-model-results.md) has
now run once per snapshot with the same long description, public input, xhigh and
60K/40K/25K limits. First requests differed only in model ID after symmetric removal
of a stale mini-priced cost forecast. Actual first inputs were both 19,947 tokens.
Mini exhausted 40K then 25K with reasoning-only responses and zero tool calls.
Full completed a 21,356-token response and an admitted probe, but failed before
both declared target calls: expected_exceptions=(SystemExit,) violates an unstated
Exception-subclass restriction, although SystemExit is already captured separately.
Setup checks passed; calls remained empty and reproduction was not compared.

Full's authored observations also selected positive W0611 only on the direct-file
control, leaving the original directory's processing unproven even after fixing
that helper setting. This is a static observation gap, not an executed repair.
The model change cleared request completion in this pair but met neither actual
reproduction nor positive target processing. It does not justify default-model
adoption, a context increase or a repair-quality claim. Each snapshot ran once.

The next bounded work is to resolve the SystemExit helper-contract inconsistency
locally and keep same-call positive processing distinct from control success.
The model's ability to correct the observed helper error after feedback remains
untested: the approved endpoint stopped at the first settled probe. Do not reopen
this allocation for a corrected probe or another model run.

Total new cost USD 0.6721752; all three count/model calls settled, no pending actions
or probes, independent metadata audit PASS. Allocation CLOSED. No edit, regression,
submission or isolated evaluation occurred. Result root:
C:/pt/first-reproduction-model-run-v1. Implementation commit e974094c; runtime unchanged.
Local owner/fork/ledger checks: 14 PASS/21.15s; quick 577 PASS (isolated mock included),
Ruff PASS. Both offline rehearsals admitted full 40K then 25K at 60K uncached input.
The preceding [saved-evidence repair](history/2026-10-27-public-regression-cycle-results.md)
passed isolated acceptance after public failure feedback; it does not establish
clean-start normal completion. Keep these evidence scopes separate.

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
