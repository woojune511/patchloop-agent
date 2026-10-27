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

The active question is whether the model snapshot changes valid callable and
observation construction at this same public checkpoint. A
[model-only comparison](history/2026-10-28-first-reproduction-model-plan.md) is
prepared and sealed: new mini/full snapshot runs, both xhigh, recorded long description,
identical public evidence, 60K input, 40K/25K output and first-settled-probe endpoint.
The checkpoint's mini-derived completion-cost forecast is omitted symmetrically
from the first visible state; actual host reservation and accounting remain active.
No prior response, repair or observation choice enters the new model inputs.

Offline cost/policy admission confirms both models retain the same tools and full
output allowances at 60K uncached input. Proposed new cap is USD 4.41415320 per arm,
USD 8.82830640 total; full's initial request plus successor/correction reservation
needs USD 3.866520. Time eligibility remains independently enforced. The exact new
allocation is pending confirmation against the sealed executable plan. No new paid
calls have occurred. This is a first-request diagnostic, not a clean-start repair
or a reason to adopt a model by default. One pair cannot establish stable superiority.

New model-comparison owner/fork/ledger checks: 14 PASS/21.15s; quick 577 PASS
(isolated mock included), Ruff PASS. Both actual-checkpoint offline rehearsals
admitted 40K then 25K at 60K uncached input with correct mixed-model accounting.
Manifest: C:/pt/first-reproduction-model-plan-v1/manifest.json; exact launcher
and read-only validator are in the same directory. Runtime is unchanged.
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
