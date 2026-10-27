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

The [clean-start ordinary trial](history/2026-10-27-normal-recovery-fresh-results.md)
reached original-call observation and one accepted repair, then stopped with
VERIFICATION_INCOMPLETE before another model response. F0010 remained; its text
changed from `Unable to load file` to `Failed to import module project`. Helper
code correctly detected either the old phrase or F0010, while the host rule searched
only the old phrase. Their verdicts diverged, and baseline-only observation correction
blocked the candidate replay. The repair did not resolve the observed failure.

This was not resource exhaustion: USD 0.40596195 / 4.50, about 7m38s, 10 responses,
15 tools and one edit. Ten model calls, 25 tools and about 1,552 solver seconds
remained. Maximum input/output were 49,059/21,068 tokens. No registered public check,
normal finish or isolated evaluation ran. All usage settled; no retry or operator
repair occurred, and the allocation is closed.

The [canonical diagnostic change](history/2026-10-27-canonical-diagnostic-feedback.md)
now defines fresh code observations once on the host. Helpers invoke targets;
they no longer need a second Boolean extractor. Stable code tokens survive changed
wording, and incomplete execution stays unknown. v6 computed evidence connects to
the existing repair loop; saved v1-v5 judgments retain their semantics.

Local normal-runner tests delivered changed-text F0010 failure and current source
to the next request, executed a second edit, checked and finished with exact-diff
receipt reuse. Both result and forced-token handoffs passed without expanding
limits. This is scripted-provider evidence; real-model uptake and Astroid repair
remain untested. Do not increase context/cost limits on the preceding failure.
New core coverage is 25 PASS. Quick covered 526 cases/82.779s including isolated
mock; all failed schema-hash/document nodes passed targeted reruns. Ruff PASS.

The [ordinary transfer implementation](history/2026-10-27-normal-recovery-transfer.md)
retains current feedback/source across handoffs and reserves useful successor
output plus verification time under opt-in recovery. Quick: 500 PASS/61.887s with
isolated mock; Ruff PASS. Those tests did not cover the live predicate divergence.
General settings above remain unchanged. No further paid execution is authorized.

The preceding [saved-evidence trial](history/2026-10-27-public-regression-cycle-results.md)
did receive regression failure, revise and pass isolated acceptance. It used a
diagnostic loop, prepared evidence and synthetic submission, so it does not establish
clean-start normal completion. Keep these evidence scopes separate.

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
