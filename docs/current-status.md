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

The [latest live pilot](history/2026-10-25-helper-correction-live.md) ended
VERIFICATION_INCOMPLETE: one accepted mutation after 28 source inspections left
F0010 unchanged on a comparable original replay. Two call-path diagnostic requests
were rejected before execution: first the wrong replay identity, then watched lines
outside their selected function. The unsuccessful candidate was not submitted.
Cost was $0.979441500 of $1.20; the unused allocation is closed.

The [helper correction](../.agent/helper-correction.md) clarifies APIs and gives one
same-question correction for a confirmed preflight error before the first mutation.
This run requested no helper, so its live correction mechanism was NOT_EXERCISED;
absence of the previous NameError does not establish prevention or repair gain.
The [implementation record](history/2026-10-25-helper-correction.md) retains 64 core
tests in 23.548 seconds and 346 quick tests in 66.949 seconds, including isolated
mock evaluation, plus Ruff PASS. No runtime change followed the pilot.

The active question is usable [call-path diagnosis](../.agent/repair-path.md):
correct replay identity and current function/line constraints were not assembled
into an executable request. After the first rejection, completion-horizon closure
removed source preparation tools even though nested path state still reported a
preparation allowance. The final stop was two rejected requests, with money and
model slots remaining; the separate 25K protocol correction did return an action.
Diagnosis request construction and the consistency of offered preparation resources
need examination before another paid pilot. No automatic continuation is authorized.

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
uncertainty. The latest live run acquired the original failure and made one
ineffective mutation; checks, finish and independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
