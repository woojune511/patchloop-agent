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

The [last live checkpoint trial](history/2026-10-27-checkpoint-feedback-single-results.md)
received original-call success at 59,142 input tokens and stopped accurately, but
later public regression exposed a symlink-path failure. Isolated evaluation was
NOT_RUN_PUBLIC_CHECKS. This established original-feedback delivery, not full repair.
Its $0.19439055 allocation is closed and the candidate/evidence remain immutable.

The [public regression repair cycle](history/2026-10-27-public-regression-repair-cycle.md)
is now implemented for the saved-checkpoint diagnostic. After each accepted edit,
the host verifies the original call and all registered public checks before the
next model response. Failure in either opens a bounded diagnostic response and
one additional edit. Both checks passing closes mutation and offers stop; exhausted
or incomplete verification is not promoted to success. Correction/handoff retain
current-diff feedback and counters. Completed exact-diff receipts are reused at
final checks; uncertain execution is never retried automatically. Known exit results
with clipped logs remain usable with explicit omission flags.

Updated diagnostic allowances: 4 ordinary responses, 1 correction, 5 tools, 2 edits,
0 helpers/original selections, up to 3 host original actions and 2 candidate regression
passes; model+intermediate deadline 1,200s. Input 60K and output 40K/25K stay unchanged.
Future diagnostic/repair/final output reserves are 8,192/40,000/8,192. The configured
uncached maximum token envelope is $1.0575 under the unchanged $1.20 single-row cap.
These are prepared implementation settings, not new paid authorization.

Focused validation: 108 PASS/109.69s, then log-clipping correction with 21 controller
PASS/30.19s and 9 integration/legacy PASS/69.68s. Actual public request construction
was verified offline; 472 quick PASS/119.15s including isolated mock, Ruff PASS.
No provider, API count, Astroid target or private evaluation
was executed for this change. Local evidence does not establish live repair gain.

Five supplementary public controls and isolated evaluation still follow the model
phase; their outcomes remain separate. The general production profile above and
hidden-evaluation boundary are unchanged. The next question is whether a real model
can use this feedback to make a successful revision within the reserved allowance.
All older allocations are closed; a future run needs a newly bound exact approval.

The requested [single-A live trial](history/2026-10-27-public-regression-cycle-plan.md)
is prepared and preflighted at `C:/pt/public-regression-cycle-plan-v1`: one run,
$1.20 cap, same public seed/evidence, updated bounded regression-repair cycle.
Actual first-regression failure delivery and successful second-edit verification
are the primary criteria. If the first edit already passes, regression revision is
NOT_EXERCISED; no automatic retry. Exact new paid approval is pending. Provider,
API-count, credential-read and target-execution counts remain zero.

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
