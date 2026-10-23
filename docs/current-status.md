# Current status

Updated: 2026-10-23. Runtime source owns behavior. Historical reports are evidence,
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

[The live oracle/correction pilot](history/2026-10-23-oracle-live.md) reached edit,
required check and submission within USD 0.864747450 of its USD 0.88 cap. It did not
repair Astroid-1333: independent acceptance FAIL, public missing-initializer condition
FAIL, present control PASS. Safety PASS is separate. The one-run allocation is closed.

A naturally incomplete first response spent its full 25,000 output tokens without
action. The reserved correction received 25,000 and restored a valid tool-call shape,
but its reproduction request was rejected. The same invalid quote/program was then
repeated despite visible primary-error feedback: two request rejections, zero actual
caller attempts. The declared failure/desired values were distinct, but execution
and issue-to-caller mapping remain unverified.

The cost horizon retained edit/check/finish after 32 reads/searches. The submitted
patch changed a successful file-lookup branch, while the public failure passes a
missing initializer with `source=True` through the unchanged exception branch.
Regression PASS did not establish the original requirement. The runtime correctly
retained `unverified_delivery`, zero bound cases and the unresolved original obligation.

[The implementation and local controls](history/2026-10-23-oracles.md) remain valid:
separate reported-failure/desired oracles; rejected requests excluded from completion
cases; one run-wide funded correction without renewal; comparable original evidence
required for `cases_verified_delivery`. Other successors retain only minimum output
admission. Completion-recovery-v1 remains opt-in; the general baseline is unchanged.

The open question is why an unchanged invalid request was repeated after its error,
then a repair selected for an unobserved input path. Request-construction friction
and feedback use need a bounded diagnostic before another paid solve. This single
exposed task with bundled changes establishes neither causal improvement nor
generalization. No follow-up implementation or additional paid run is authorized.

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
