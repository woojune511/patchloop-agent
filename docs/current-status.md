# Current status

Updated: 2026-10-24. Runtime source owns behavior. Historical reports are evidence,
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

[Request construction and correction](history/2026-10-23-requests.md)
implements the first step after the [request audit](history/2026-10-23-request.md).
Fresh original probes no longer generate a literal quotation: the host binds the
complete public task and issue-content identities. Field diagnostics identify the
request problem; durable receipts distinguish unchanged arguments, changed but
invalid arguments, and a fully valid correction. Decision text grants no correction
credit. Legacy admitted bindings and action recovery preserve their identities.

The [closed live pilot](history/2026-10-24-request-live.md) exposed a host-size
defect: observer overhead rejected both original requests despite a real source
correction. Original acquisition and repair failed; the allocation is closed.

The [size repair](history/2026-10-24-size.md) separates the unchanged 8,000-character
authored allowance from an 8,000-character host observer allowance. Serialized
execution has a derived, bounded transport allowance in both launcher and reader.
Saved observer/program bytes and replay identities are preserved. The v3 probe
profile and v50 tool contract identify the change; old manifests cannot authorize
execution against it.

The [frozen caller diagnostic](history/2026-10-24-run.md) executed both rejected
requests unchanged, with zero model calls. Both reached `pylint.lint.Run`, reproduced
F0010 on the missing-init fixture and avoided F0010 on the init-present control.
Both nevertheless failed their declared JSON oracle: ordinary control lint
warnings were summarized as `other_error`, while the failure value required `ok`.
Caller/symptom reproduction is supported in this pinned environment; formal
acquisition, repair and fresh-model uptake are not established. Allocation closed.

Routine verification uses the short quick selection plus changed-owner cases.
The size repair has 242 distinct local tests passing across a 55.19-second combined
run and a 1.05-second identity-pin recheck, including isolated mock evaluation.
See its record for split-validation details. Full tests remain available; repeated
A/B loops are outside routine quick validation.

Acquisition release, edit-time replay scheduling, cost reservations and completion
semantics are unchanged. The next question is an observation contract focused on
the original F0010 condition, with other lint diagnostics and execution/setup
failures kept separate. Preserve the frozen oracle mismatch; do not relabel it
after observing the outcome or loosen completion to erase it. No further
experiment or general improvement claim is authorized.

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
uncertainty. Linux CI, live replay/rejection of an acquired original case, and
general improvement are unverified.
