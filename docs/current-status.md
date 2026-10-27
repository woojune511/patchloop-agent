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

The approved [single-A delivery trial](history/2026-10-27-checkpoint-feedback-single-results.md)
executed once from the same saved public checkpoint with unchanged first request
and row limits. The first input was 56,199 tokens. After one accepted edit and a
successful original-call recheck, the next actual request fit at 59,142 tokens
and contained the exact current-diff verification. Two source references expand
exactly to the durable result. The model accurately recognized original-call
success and called stop_task. No handoff or correction was needed.

The original F0010 resolved and all five public cases passed, but the later public
regression failed one symlink-path test (1,230 passed). Isolated evaluation was
NOT_RUN_PUBLIC_CHECKS with zero evaluator dispatches. That regression happened
after the model stopped and was not model-visible. Original-feedback delivery
and accurate diagnostic stop passed; full repair and acceptance remain incomplete.
The second original call's input identity changed due to cache output in the input
root; first-call identity and control output were preserved.

Retain the [delivery fix](history/2026-10-27-checkpoint-feedback-delivery.md) on local
and live delivery evidence. Do not increase context based on this run: the next
question is making final public regression model-visible before completion and
funding a bounded response or repair. Preserve raw/symlink path matching when
investigating the new patch. The 858-token remaining input margin and unexercised
handoff do not establish future fit or general quality. One saved-evidence trial
is not a fresh solve or a controlled repair-gain comparison.

Two counts and two generation calls settled; $0.19439055 under $1.20, allocation
closed, no execution/billing uncertainty. Model+intermediate 175.42s; through final
checks 307.75s. Result: `C:/pt/checkpoint-feedback-single-run-v1/result.json`.
Preparation/delivery checks: 47 focused PASS across 1.83s and 19.47s runs; 472 quick
PASS/129.97s including isolated mock; Ruff PASS. No code changed during the run.

The [previous A/B result](history/2026-10-27-first-edit-checkpoint-results.md)
remains historical: A repaired the task but could not receive its result at
65,982 input tokens; B received failure feedback and failed acceptance. The new
A chose a different patch despite identical first input. Cost/cache and patch
variation preclude attributing repair quality or spend changes to compression.
All older allocations are closed; previous approvals do not authorize another run.

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
