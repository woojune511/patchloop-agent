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

The [argument-correction implementation](history/2026-10-28-original-argument-correction.md)
addresses the settled pre-target failure in the [single full-model helper follow-up](history/2026-10-28-helper-first-reproduction-results.md):
the model set sys.argv, then passed a positional list to zero-parameter
pylint.run_pylint. Fresh v9 now exposes the actual callable signature and records
explicit argument-binding failures separately from target exceptions. A proved
pre-target failure can use the existing one-per-run correction opportunity, with
the same question, purpose and call-path request. No resource limit is increased.

The next response receives the failed source, actual signature and supplied args.
A changed request must still fit acquisition quotas and completion reservations,
including its prospective original replay. Rejection/repeated failure cannot
renew the opportunity. Argument correction never establishes original verification.
Saved v1-v8 observer bytes and completed-action recovery remain fixed.

Local fixture execution and scripted model responses cover error delivery,
correction, exhausted budgets and recovery; the focused selection also reaches
isolated mock evaluation. The implementation record holds exact test receipts.
No paid model or benchmark execution occurred for this change. The unresolved
question is whether the actual model uses the signature and feedback to reach
the original failing call and establish same-call processing evidence. F0010
reproduction, repair gain and fresh-solve completion remain unverified.

A [single full-model trial](history/2026-10-28-argument-first-reproduction-plan.md)
is sealed and locally validated at the same public checkpoint. The initial request
changes only the long description's call paragraph; host v9 and one conditional
argument-correction continuation apply. Normal first entry ends immediately with
correction NOT_EXERCISED. The second probe, explicit stop or ordinary terminal
also ends the diagnostic; repair/submission/evaluation remain out of scope.
Read-only preflight is READY. Proposed new cap USD 4.41415320 is awaiting exact
authorization; no new paid collection has started.

The prior first-probe diagnostic stopped at its first result and could not test
feedback correction. Its USD 0.1866575 allocation is closed; any live continuation
needs a new scope and exact allocation. The preceding [model pair](history/2026-10-28-first-reproduction-model-results.md)
is a separate closed experiment, not a new control or model-adoption result.

The preceding [saved-evidence repair](history/2026-10-27-public-regression-cycle-results.md)
passed isolated acceptance after public failure feedback; it does not establish
clean-start normal completion. The [canonical diagnosis](history/2026-10-28-canonical-diagnostic-analysis.md)
and [processing-evidence contract](history/2026-10-28-processing-evidence-implementation.md)
remain the basis for same-call processing evidence, fixture identity and request accounting.

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
