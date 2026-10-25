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

The [judgment pilot](history/2026-10-25-judgment-correction-live.md) ran once on
Astroid-1333 with gpt-5.4-mini xhigh, normal output 40K, protocol correction 25K
and the unchanged USD1.20 cap. It ended LIMIT_REACHED at four accepted mutations
after 23 model calls, 26 actions, 18m05s and USD1.031992500. No submission or
independent acceptance occurred; counting/billing are known and allocation closed.

The first authored original probe used declared diagnostic rules and acquired the
actual F0010 failure. Host/authored judgments agreed in all five probes: one
baseline and four same-condition candidate replays. Every candidate still failed.
The first three candidate failures reached the next dispatched model input; the
last was followed by termination. The four edits were three implementation changes
and one test addition. A 1,232-pass regression and one selected test passed after
edit 2; final-diff regression is NOT_RUN and the original obligation remains refuted.

The [judgment implementation](history/2026-10-25-judgment-correction.md) and
[contract](../.agent/observation-judgment.md) remain. Host calculation was selected
live, but no mismatch occurred: baseline correction, supersession, linked-note
revalidation and their extra reserve remain locally tested only. Literal choice
and requirement mapping remain model-authored; null rules retain legacy semantics.

The [resource changes](history/2026-10-25-completion-resources.md) also remain.
Call 22 exhausted its admitted 8,979 normal tokens. Reserved protocol correction
used 13,265 of 25K tokens and generated edit 4, which still failed. Early replay was
reusable; finish reuse and exceptional minimum-funded diagnosis were not exercised.
See the [completion resource contract](../.agent/completion-resources.md).

The [preceding pilot](history/2026-10-25-completion-resources-live.md) misclassified
captured stdout and never edited. The current run establishes consistency and
failure retention for its selected case, not causal repair gain. The unresolved
question is whether the modified namespace/path helpers participate in the actual
caller failure, or their result is ignored downstream. No further paid diagnostic,
continuation or cap increase is authorized by the observed unused budget.

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
uncertainty. The latest live run acquired the original failure and retained it
through four ineffective edits; finish and independent evaluation were NOT_RUN.
Linux CI and general improvement remain unverified.
