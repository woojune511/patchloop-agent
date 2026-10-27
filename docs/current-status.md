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

The [single-A live regression trial](history/2026-10-27-public-regression-cycle-results.md)
exercised the intended revision path successfully. The first edit resolved F0010
but failed a public symlink regression. The model received that current-diff failure,
revised once, received original and regression PASS, and stopped. Registered
regression finished with 1,231 passed / 69 skipped / 15 xfailed; supplementary public
cases passed 5/5. Isolated acceptance, scope and safety each passed.

Retain the [regression repair cycle](history/2026-10-27-public-regression-repair-cycle.md):
original and registered public checks precede the next response, public failure
opens one bounded revision, and final checks reuse exact-diff receipts. The real
handoff reduced a 62,946-token successor to 55,068 while preserving fresh feedback
and counters. Final success reached the model at 55,488 tokens. The 60K context
ceiling did not need an increase in this trial.

Used: 3 ordinary responses, 0 corrections, 3 tools, 2 edits, 3 host original actions,
2 regression passes, 1 handoff. Cost $0.38928225 / $1.20; all usage known and allocation
closed. Collection through model completion took 558.49s; through final checks and
closure, 661.35s. No repeat or operator repair occurred. Local mechanism coverage
remains 472 quick PASS/119.15s including isolated mock, with focused evidence linked
in the implementation record.

This is one saved-evidence integration result, not fresh-solve or general quality
evidence. First-original-call identity holds; the second call retains a cache/input
identity limitation. The stop summary recognized both passes, but its raw diagnostic
reason code was `public_task_conflict`, not a success verdict. Host receipts establish
success independently. Diagnostic stop plus synthetic operator submission does not
exercise the product's complete `finish_task` flow.

The [ordinary-runner transfer](history/2026-10-27-normal-recovery-transfer.md) is now
implemented and locally tested. Actual request tests confirm failure/source delivery
through normal handoff and input overflow; no context rewrite was needed. The opt-in
recovery cost policy now protects role-sized successor output and check/finish time,
including one possible revision when physical capacity exists. It preserves a fully
funded current repair before admitting optional exploration. Quick: 500 PASS/61.887s,
including isolated mock evaluation; Ruff PASS. These are local mechanism results.

The next evidence gap remains a clean-start run through normal `finish_task`.
Preparation uses the same mini model, 60K input and 40K/25K output, with a proposed
fresh $4.50 cap for exploration and completion. The ordinary helper can inspect
public caller source; diagnostic dependency read/search scope is not transferred.
General settings above remain unchanged. All paid allocations are closed; the new
trial is NOT_RUN and requires exact plan-bound approval after sealing.

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
