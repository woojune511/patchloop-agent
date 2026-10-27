# Current status

Updated: 2026-10-28. Runtime source owns behavior. Historical reports are evidence,
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

The [post-reproduction repair trial](history/2026-10-28-post-reproduction-repair-results.md)
executed once on Astroid-1333 using the acquired public baseline. The first two
candidate failures reached the next actual model requests; all three edits were
followed by identical original-call replay. The third edit removed F0010 but
produced empty original-call output with no W0611 processing witness. All three
desired comparisons remained mismatched; the normal package control stayed intact.

The same-case/caller/fixture identities and complete captures were preserved.
Independent output-code extraction agrees with the authored booleans. The case
still has null diagnostic_rules; this is not a canonical-host-rule improvement.
W0611 is an added processing criterion beyond the issue's explicit error absence.
Known missing processing was retained as failure rather than converted to PASS.

The run ended LIMIT_REACHED at three accepted edits. New usage:11 responses,
17 actions, USD0.977534. The USD4.13241570 allocation is CLOSED; unused
USD3.1548817 does not authorize continuation. Responses4, tools16 and about1293
solver seconds remained. Context/output/cost/time were not exhausted. Public
regressions, finish_task and isolated acceptance are NOT_RUN. The final failure
was not followed by another model request because the mutation limit ended the run.

Keep the [restored public handoff](history/2026-10-28-post-reproduction-repair-plan.md)
and same-call processing check. The next question is whether initial repair
hypotheses establish caller exception handling and traversal before spending edits.
Here the model first instrumented that path after two failures, then changed the
builder to return an empty module. The final traversal mechanism remains untraced;
an earlier diagnosis or extra edit is a hypothesis, not a demonstrated fix.

The preceding [signature-guided trial](history/2026-10-28-argument-first-reproduction-results.md)
reproduced the original F0010 with correct arguments. Adaptive signature use and
live argument-correction uptake remain unestablished. This continuation is one
checkpoint repair attempt, not a clean-start solve or generalization result.
No new execution is currently funded.

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
