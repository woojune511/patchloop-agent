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

The [captured-exception fix](history/2026-10-26-target-exception-preservation.md)
preserves a complete, identity-matched target exception after a settled nonzero
helper exit. Existing diagnosis, repair-stage and finish-blocking paths now consume
that evidence. Helper-only failures, changed identity and uncertain/incomplete
capture remain excluded. Actual outer failure and whole-case UNKNOWN are retained;
there is no new success credit, tool, gate, budget or context policy.

Local validation: the new real regression failed before the fix; target-outcome21
passed in 28.67 seconds, quick451 passed in 61.16 seconds, Ruff and isolated mock
evaluation passed. The unchanged saved live receipt now projects one target failure
and diagnosis available, while whole-case verification stays unverified. This is
offline projection and local mechanism evidence.

The [live pilot](history/2026-10-26-target-exception-live.md) is now closed. It acquired
the original failure/control, completed a pre-edit path observation and applied two
edits; both candidates still raised `FileNotFoundError`. The host retained the
exception and excluded finish, but the model did not complete a repair. It stopped
with INCOMPLETE_RESPONSE after 36 model calls, USD 1.071262200 and 894.56 seconds.
No public regression, submission or independent evaluation occurred. All helper
executions exited zero, so the new nonzero-helper classifier branch was NOT_EXERCISED.
Existing failure propagation was observed; live efficacy of the new condition
remains unresolved.

Before the first edit response, 29 calls and USD 0.648690600 were spent. After the
first failed candidate the model repeated the same replay; after the second it
read the edited builder again, without a new call-path diagnosis. Three responses
exhausted admitted ceilings of 19,880, 8,620 and 6,144 tokens. Future completion
reservations reduced these ceilings within the unchanged USD 1.20 cap; the whole
cap was not spent. The next question is how to obtain a discriminating diagnostic
and a supported revision earlier. This single run does not justify a context
increase or establish that the reserved budget was excessive.

The closed [request-continuity pilot](history/2026-10-26-request-continuity-live.md)
is the preceding live result: one Astroid-1333 solve with mini/xhigh, 40K/25K output
ceilings and a USD 1.20 cap. One edit and submission occurred; public regression
passed, original replay raised `FileNotFoundError`, delivery was unverified,
independent acceptance FAIL and safety PASS. It used 20 model calls, USD 0.544587150
and 347.78 seconds. No response exhausted its output ceiling. The builder edit
bypassed the initial missing-file error but a later source-stream read still opened
the nonexistent initializer. Whether corrected failure feedback leads to a repair
of that path remains unresolved; the historical result is unchanged.

Context continuity is a separate unresolved question. That preceding run used at most 56,977
input tokens; all five post-initial resets were stage/result triggered, with no
size-triggered reset. Raising the 60K ceiling alone retains those transitions.
Historical mini-SWE-agent used accumulated history without the extra 60K cap,
but maximum actual input was 77,660, not a full model window. Its tools, budgets
and outcomes differ; no context-only quality effect has been established. See the
[context analysis](history/2026-10-26-target-failure-context-analysis.md).

Keep the [request-continuity contracts](history/2026-10-26-request-continuity.md):
stage-valid probe modes, parallel generation matching gate capacity, bounded exact
unexecuted drafts and separate preparation/dispatch/request-error acquisition
budgets. Tool surface v62 binds them. Their combined pilot does not establish
separate causal effects or repair gain. No paid allocation is active.

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
uncertainty. The latest run stopped with an unresolved target failure and no
submission or independent evaluation. Public-check PASS, safety PASS and successful
submission do not establish repair correctness. Linux CI and general improvement
remain unverified.
