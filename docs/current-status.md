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

[Failure oracles and correction funding](history/2026-10-23-oracles.md) address two
gaps from the [closed pilot](history/2026-10-23-repro-live.md): the bug was encoded as
the desired result, and an incomplete response exhausted its current allowance while
only two minimum calls remained for a three-call completion path.

Fresh original purposes require distinct `reported_failure_json` and desired
`expected_json`. Failure acquisition needs a healthy unchanged-base root matching
the former and mismatching the latter. A third value cannot acquire the failure.
Known preflight rejections leave no completion case; uncertain accepted execution
remains unverified. Existing binding/replay identities and legacy rules are retained.

Opt-in `completion-recovery-v1` requires segmented-v1. In addition to successful
minimum successors, it reserves one correction at 60K uncached input plus the
requested output ceiling and one model slot. The first durable protocol correction
consumes this run-wide credit; valid actions and restart never renew it. The correction
requires the full output allowance. Other successors still have only 128-token minimum
admission. Existing policies/defaults remain unchanged.

The public-task obligation survives plans and helper cases. Only an acquired baseline
failure plus current comparable support permits `cases_verified_delivery`. Missing
evidence returns `unverified_delivery`; current mismatch/conflict blocks finish.
Both oracles and the issue-to-caller mapping remain model-authored. Independent
acceptance cannot upgrade original verification.

Focused local controls: 35 PASS in 114.85 seconds. Under virtual USD 0.40, both policies
reach scripted check/finish; the new policy increases correction output allowance
from 128 to 25,000 while reducing the first call from 25,000 to 3,376. This proves
allocation behavior, not useful model output. Standard mock smoke reaches isolated
evaluation PASS, safety NOT_RUN, with unverified delivery. Quick selection: 335 PASS.
Full local regression: 5,779 PASS, 20 SKIP, no failures; a subsequent legacy test-fixture
correction passed its entire 13-case file with the same production runtime. Ruff
passed. Commands, skip reasons and preserved earlier failures are in the linked report.

The unresolved question is whether the fresh oracle pair is faithful to the public
report and whether funded correction produces useful action in a real solve. No
repair improvement, default adoption or fresh paid run is established or authorized.
All previous allocations remain closed.

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
