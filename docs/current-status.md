# Current status

Updated: 2026-10-26. Runtime source owns behavior. Historical reports are evidence,
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

The [closed revision pilot](history/2026-10-26-repair-revision-live.md) completed
one authorized Astroid-1333 solve with gpt-5.4-mini-2026-03-17 xhigh and unchanged
40K/25K ceilings. Cost $1.199996700; 37 model calls, 39 actions, two source edits.
Both traces were complete. After the first edit retained F0010, the second revised
the mechanism using the observed import error and bound an original-effect prediction.
This exercises source revision; it does not establish repair success.

The final original call raised FileNotFoundError instead of emitting F0010. The
host kept the comparison and prediction unverified. The exception is present in
the durable receipt but absent from final public inputs, which retained UNKNOWN
and current_public_failure=null. Public regression passed 1,231 tests; that did
not resolve the original failure. The last two responses exhausted their admitted
4,677/4,157 output ceilings without calling finish. Terminal INCOMPLETE_RESPONSE;
no submission or independent evaluation. Direct-API equivalence and changed fresh
caller conditions still limit historical comparison.

The active problem is preserving unexpected target exceptions as actionable repair
feedback instead of collapsing them into missing-observation UNKNOWN, while keeping
verification and candidate-return eligibility distinct. Finalization context and
completion funding also remain unresolved; another ceiling increase alone is not
supported by this run. No new paid run is authorized.

The [revision contract](history/2026-10-26-repair-revision.md) retains host-bound
predictions checked in original replay, additive-test comparison funding, and strict
historical diagnosis reuse. A rejected directory-level test selection produced no
paired execution; added-test/reuse behavior remains locally validated only.
The [actual-task wrapper adapter](history/2026-10-26-repair-revision-live-plan.md)
preserves the registered pytest copy wrapper and unchanged task bytes.
Local core 68 PASS (37.93 s); wrapper/comparison 15 PASS (24.69 s); latest quick
378 PASS (35.30 s), including isolated mock evaluation; Ruff PASS.
The [collector](history/2026-10-26-trace-budget.md) and
[first-repair path](history/2026-10-26-first-repair.md) retain their bounded coverage
and recovery identities. No runtime change was made during this live closeout.

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
uncertainty. The latest live run passed public regression but the original call
raised a new exception. Paired tests, finish, frozen post-submission checks and
independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
