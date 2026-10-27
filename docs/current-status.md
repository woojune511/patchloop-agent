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

The [registered dependency-source intervention](history/2026-10-27-dependency-source-access.md)
adds explicit read-only caller scopes to ordinary reads/searches. The diagnostic
v4 profile registers Pylint 2.12.2 from the pinned public bundle, reports scope on
zero-file repository searches, and retains verified dependency observations
separately from editable workspace anchors. Normal action limits apply; helper
and original-replay quotas, money and context limits are unchanged.
Focused validation: 79 PASS/3 platform SKIP in 48.85s; fast suite 472 PASS/106.52s
including isolated mock evaluation; Ruff PASS. One fresh R1 trial is being prepared;
model uptake, first edit and repair remain untested with this intervention.

The [preceding R1](history/2026-10-27-repair-entry-single-results.md) stopped after
15 responses and zero edits ($0.22311930; allocation closed). Three Pylint searches
scanned zero repository files. The [audit](history/2026-10-27-caller-access-analysis.md)
confirmed that helper source access was already advertised, but the model did not
switch methods. Interface burden is a hypothesis. Original failure was already
supplied, so an unchanged replay would not fetch the missing caller body. No fresh
original/public/isolated verification ran in that trial.

The [repair entry contracts](history/2026-10-27-repair-entry-contracts.md) are now
implemented for feedback-source-pair-v3: whole/page file reads, a small registered
original-call selector, required executable helper source, and a provider parallel
flag matching the actual read limit. An over-limit request can rebuild once from
current public evidence, then recount and pass cost admission with unchanged
global allowances. Opaque prior reasoning stays in local artifacts. The optional
original selection uses one of 24 model-tool slots; host replays allow at most
five including the baseline and three edits. Input/output caps remain unchanged.
Focused owner/legacy validation: 121 PASS/63.49s; fast suite: 472 PASS/106.60s,
including isolated mock evaluation; Ruff PASS. Live ordinary context recovery is
now observed; first-edit repair, original selection and feedback use remain unobserved.

The [live repair-cycle pilot](history/2026-10-27-repair-cycle-results.md) completed
R0/R1 once each, with zero edits. R0 used 15 responses on source exploration and
stopped for insufficient evidence; R1 made a probe request with null source,
then violated the offered one-read batch limit. Its undispatched correction counted
68,124 input tokens against 60K. Both retained the seed diff; original rechecks,
final public checks and acceptance were NOT_RUN. Total settled cost $0.32811825;
all 24 generation calls settled and the $2.40 allocation is closed.

The [original-call repair cycle](history/2026-10-27-original-repair-cycle.md) is
implemented and locally verified (82 focused PASS/27.91s; 472 quick PASS/105.36s
including isolated mock evaluation; Ruff PASS), but its post-edit path was not
exercised by this live pair. Production defaults and legacy profiles stay unchanged.
The next unresolved bottleneck is reaching a justified first edit and revising it
from failure feedback. The new contracts remove demonstrated request mismatches;
they do not establish better diagnosis or repair. Future paid work needs a new
evidence-based scope and prepared identities.

Whether the model uses post-edit feedback to repair the caller remains unresolved.
The [preceding R0/R1 pair](history/2026-10-27-feedback-source-results.md)
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
