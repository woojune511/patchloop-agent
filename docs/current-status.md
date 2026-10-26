# Current status

Updated: 2026-10-26. Runtime source owns behavior. Historical reports are evidence,
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

The [request-continuity change](history/2026-10-26-request-continuity.md) addresses
observed request/correction failures from the closed completion-feedback pilot.
Fresh probe modes now match their stage; original acquisition offers an executable
new original program, and pending diagnosis offers the small focus schema. Parallel
provider generation is enabled only when the gate can accept a read batch.

Rejected edit batches retain up to two exact unexecuted drafts, bounded to 32 KB of
canonical argument bytes. The journal, refreshed correction and compact segment
preserve these bodies on the same diff. Stale or oversized bodies are explicitly
withheld. Drafts grant no execution, source or verification credit; corrected single
actions still pass normal anchor/scope checks. Tool surface v62 binds the change.

Fresh bounded acquisition separates six preparation actions from two actual
original dispatches and two request errors. At the preparation limit only the
original request or stop remains. Reads preserve a funded original request and its
completion route. Existing receipts retain legacy limits; uncertainty and budget
release remain unverified. The invocation cap and ordinary/correction output
ceilings have not increased.

Core local validation: 70 PASS in 28.95 seconds; quick: 450 PASS in 37.81 seconds.
Ruff and isolated mock evaluation passed. Offline projection retains both actual
rejected drafts exactly (6,605 argument bytes). Actual model progress, F0010 repair
and the effect on output exhaustion remain untested with this change.
No paid continuation is active. The next live question is whether a fresh solve
executes the original call and turns its first edit proposal into a single applied
action within the same previously selected limits.

The [closed completion-feedback pilot](history/2026-10-26-completion-feedback-live.md)
ended INCOMPLETE_RESPONSE: 34 model calls, USD 0.843607950, 33 reads/searches, one
preflight-rejected probe, and no edit or target execution. Its [analysis](history/2026-10-26-completion-feedback-analysis.md)
confirmed invalid general diagnosis options, parallel generation at a mutation-only
gate and missing rejected new-text bodies after rollover. Their contribution to
model output exhaustion was not isolated. Existing [target-failure feedback and
finalization](history/2026-10-26-completion-feedback.md) remain implemented; the pilot
did not reach those conditional stages. Prior public PASS and isolated acceptance
remain separate from original-call verification.

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
uncertainty. The latest live run applied no patch and performed no target execution.
Original verification, public checks, finish, frozen post-submission checks and
independent evaluation were NOT_RUN. Its conditional mechanism effects remain untested.
Linux CI and general improvement remain unverified.
