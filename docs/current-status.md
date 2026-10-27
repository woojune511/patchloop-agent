# Current status

Updated: 2026-10-27. Runtime source owns behavior. Historical reports are evidence,
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

The [original-call repair cycle](history/2026-10-27-original-repair-cycle.md) now
rechecks every accepted edit and feeds current-diff public failures into the next
response. The saved-candidate diagnostic permits further reads and up to three
edits, with separate future-response funding and host verification allowances.
Final public checks reuse matching original receipts; incomplete rechecks stop
the run. Local validation: 82 focused PASS/27.91s; 472 quick PASS/105.36s including
isolated mock evaluation; Ruff PASS. Live use is NOT_RUN.
Production defaults and legacy one-edit profiles stay unchanged. The changed
16-response/24-action/2-probe scope needs new preparation for a future authorized
run; all preceding allocations are closed.

The unresolved question is whether the model uses that feedback to revise its
premise and repair the caller. The [preceding R0/R1 pair](history/2026-10-27-feedback-source-results.md)
retained F0010 despite complete assigned source delivery and no input/output/cost
cutoff. R0 undid the seed (empty diff, acceptance NOT_RUN); R1 added a namespace
fallback and failed acceptance. Neither selected/parsed the namespace child,
although public regression passed. Each row stopped at its first edit, so it did
not test recovery after feedback. Total cost $0.33463995; allocation closed.
The [empty-diff fix](history/2026-10-27-feedback-source-empty-diff.md) preserved the
R0 incident and ran only the unstarted R1. The [selected-file read API](history/2026-10-27-feedback-source-implementation.md)
is locally tested; that pair retained range-only tools, so live API uptake is
still untested. The v2 horizon also differs; do not infer a feedback-only effect
from a future cross-version result. Broader-suite failures remain unresolved.

An independent [relative-root operator repair](history/2026-10-27-relative-root-repair.md)
passes isolated acceptance, regression, scope and safety on Astroid-1333. It
normalizes the search root before comparing absolute filenames and contains no
synthetic namespace builder edits. This is an accepted local operator repair,
not a fresh benchmark-model solve. Public child selection and parsing distinguish
it from the [earlier apparent success](history/2026-10-27-namespace-selection-diagnostic.md).
That known solution is excluded from model packets and these scripted fixtures.

The [clean-base A/B](history/2026-10-27-selection-observation-results.md) and its
[failure analysis](history/2026-10-27-selection-observation-failure-analysis.md)
identified a false source premise, untested helper alternatives and the first-edit
feedback cutoff. Source delivery, action selection, original-call behavior and
independent acceptance remain separate evidence. No successful new model repair
has been established in these follow-ups.

Context continuity is a separate question. The preceding fresh-solve pilot had
no size-triggered reset; raising 60K alone would preserve stage/result resets.
Historical mini-SWE-agent accumulated history without that extra cap, with observed
maximum input 77,660, not a full model window. Tools and budgets differed; no
context-only quality effect is established. See the
[context analysis](history/2026-10-26-target-failure-context-analysis.md).

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
resolver candidate now passes. No live model has newly achieved an accepted solution
in these follow-ups.
Public-check PASS, safety PASS and successful submission do not establish repair
correctness. Linux CI and general improvement remain unverified.
