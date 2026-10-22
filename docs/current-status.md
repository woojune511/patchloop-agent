# Current status

Updated: 2026-10-22. Runtime source owns behavior. Historical reports are evidence,
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

[Original obligation and delivery](history/2026-10-22-original-obligation.md) are
implemented in dev-head. A public-task obligation survives plan/helper changes.
Opt-in `--reproduction-acquisition bounded-v1` requires probes and offers two
original attempts or six investigation actions before edits, releasing earlier
to preserve the protected completion budget. Only an unchanged-base failure
acquires original evidence. Normal/helper PASS and stage release leave it unmet.
The flag defaults to `none`; selected live settings have not changed.

Finish retains/replays acquired cases and rejects current mismatch/conflict.
Fresh invocation receipts also bind sys.argv, preserving legacy replay bytes.
Missing/incomplete original evidence returns `unverified_delivery`; verified
selected cases return `cases_verified_delivery`. Independent acceptance stays
separate and cannot upgrade missing original verification.

Final local controls passed 8/8, with matching paired patch hashes and zero
duplicate-finish probe executions. Focused tests cover malformed requests, phase
limits, added-case replay budgets, recovery and context delivery. CLI mock smoke
reached isolated evaluation PASS with safety NOT_RUN and unverified delivery.
These are scripted protocol controls, not evidence of better LLM repairs.

The [fresh Astroid pilot](history/2026-10-22-original-case-live-results.md) acquired
zero original cases; regression PASS accompanied original-caller and acceptance
failure. The unresolved question is whether bounded acquisition yields faithful
cases and repairs within the same live budget. Mapping/expectations remain
model-authored and unverified. All paid allocations are closed; no follow-up is
queued or authorized. See the [protocol](../.agent/plans/original-obligation.md).

## Supporting evidence

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
uncertainty. Linux CI, live replay/rejection of an acquired original case, and
general improvement are unverified.
