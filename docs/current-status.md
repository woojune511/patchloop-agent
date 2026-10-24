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

The [cap-only pilot](history/2026-10-25-budget-live.md) submitted a patch after
public regression PASS, but the original failing input still produced F0010 and
independent acceptance was FAIL. Replay occurred inside the final finish request,
leaving no subsequent model turn. Host tracing argv and random HOME/PYLINTHOME
hashes also made the otherwise matching target calls incomparable. That allocation
is closed; its results and historical submissions remain unchanged.

The [original-feedback implementation](history/2026-10-25-original-feedback.md)
addresses both mechanisms. Fresh invocation v4 / tool contract v54 clears host
launch arguments before authored setup and offers a fresh stable fixture workspace.
Explicit CLI arguments and selected environment/input identities are still checked;
HOME/cache variables must be set explicitly using the stable workspace when needed.
Exact invocation v1/v2/v3 programs and observer bytes remain replayable.

After each accepted edit, acquired original cases replay before the next model
input, using the same case/diff child IDs as the finish fallback. The completion
view retains current observations and condition differences separately. Comparable
failure blocks finish; missing or incomparable evidence remains unverified.
Scheduling uses already reserved completion actions and reconciles started children
even after admission closes. Tool forecasts include replay on each future repair;
minimum monetary admission does not promise recovery from a semantic repair failure.

Local four-condition controls and short owner validation support these mechanics.
The [fresh live pilot](history/2026-10-25-original-feedback-live.md) stopped with
INCOMPLETE_RESPONSE before any tool action: the initial response and one protocol
correction each exhausted a full 25,000-token output allowance. Cost was USD
0.235849950 of 1.20; reproduction, repair, feedback uptake and acceptance were
not assessed. That allocation is closed. This does not establish a regression in
the new mechanisms or support increasing the invocation cap. The immediate
unresolved question is how to obtain the first bounded valid tool response;
stable original-call repair and use of pre-submission feedback remain unmeasured.
The [operator oracle experiment](history/2026-10-24-oracle.md) remains separate.

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
uncertainty. A live replay of an unacquired case is observed; replay/rejection after
a faithfully acquired original failure, Linux CI and general improvement remain
unverified.
