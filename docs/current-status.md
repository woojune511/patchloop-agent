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

The [single full-model helper follow-up](history/2026-10-28-helper-first-reproduction-results.md)
executed once at the same public checkpoint, using fresh v8 and only the updated
helper paragraph in the long description. The prior SystemExit settings error did
not recur; helper construction and three setup comparisons passed. But the model
called the zero-parameter pylint.run_pylint entrypoint with a positional list after
setting sys.argv. Signature binding rejected it before entry: target_started=false,
TypeError: too many positional arguments. F0010 and same-call processing are NOT_RUN.
The first settled probe ended the diagnostic; there was no feedback correction.

The response completed with 19,997 input and 9,111 output tokens, below 60K/40K limits.
New cost USD 0.1866575; all usage settled, independent metadata audit PASS, allocation
CLOSED. No repair, checks, submission or isolated evaluation occurred. The desired
observation now includes positive processing from the same problematic call, but
that unexecuted design is not evidence of processing. The explicit SystemExit option
was omitted in this fresh code, so its new acceptance was not exercised live.

The [helper implementation](history/2026-10-28-helper-system-exit-fix.md) remains:
fresh v8 accepts explicit SystemExit subclasses, descriptions share the API contract,
and saved v1-v7 observers remain byte-exact. Its focused 89 tests passed in 28.176s;
follow-up preparation quick passed 594 cases including isolated mock evaluation.
Runtime was unchanged during the live follow-up. The preceding [model pair](history/2026-10-28-first-reproduction-model-results.md)
remains a separate closed experiment, not a new control or model-adoption result.

The next unresolved question is callable-signature adaptation and bounded correction
of an error before target entry. Exposing the actual signature is a more direct
intervention than raising output/context ceilings; do not coerce arbitrary arguments
or erase original verification obligations. This first-probe endpoint did not test
whether a model could correct the returned error. Any feedback trial needs a new
scope and exact allocation; no automatic retry or default adoption follows.

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
