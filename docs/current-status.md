# Current status

Updated: 2026-10-25. Runtime source owns behavior. Historical reports are evidence,
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

The [new live pilot](history/2026-10-25-callpath-live.md) acquired the original
F0010 failure but made no mutation. It spent USD1.050511650 in 650.323 seconds:
31 model calls, 27 source inspections and two probes. The helper probe failed with
NameError; that error and the original failure reached subsequent model inputs.
After exploration closed, the ordinary response exhausted 40,000 output tokens
and its single correction exhausted 25,000. Terminal: INCOMPLETE_RESPONSE.
No submission, required checks or independent acceptance occurred. Allocation closed.

The [call-path mechanism](../.agent/repair-path.md) activates after a comparable
failed mutation with unobserved changed lines. This run never reached that trigger:
diagnostic request, execution, evidence-linked revision and paired selected tests
were all NOT_EXERCISED. It neither validates nor rejects their repair benefit.
The [implementation](history/2026-10-25-callpath-repair.md) retains its local evidence:
54 core tests in 64.191 seconds and 318 quick tests in 67.612 seconds, including
isolated mock evaluation. The selected task's pytest wrapper is also outside the
new direct-pytest comparison contract; no comparison was attempted in this pilot.

The active bottleneck is reaching an evidence-based first repair under the existing
limits. The next question is whether a valid bounded diagnostic before that first
repair can replace unproductive source exploration. After that, actual uptake of
the conditional path diagnosis remains unresolved. The earlier [call-path audit](history/2026-10-25-judgment-callpath-analysis.md)
still explains the previous four ineffective edits; this fresh trajectory failed
at an earlier stage. Keep original-failure gating, [host judgment](../.agent/observation-judgment.md)
and [completion reserves](../.agent/completion-resources.md), without inferring
repair gain or increasing limits from unused budget.

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
retains unknown billing; later settled allocations do not resolve it.

Fresh solves, seeded repairs, funded continuations, saved-patch evaluations,
operator replays and scripted tests are different evidence. Do not pool them as
solve rates or expose private evaluator details to the agent. Public case support,
submission, independent task acceptance and safety are separate. Mock safety is NOT_RUN.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
uncertainty. The latest live run acquired the original failure but never mutated
source; finish and independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
