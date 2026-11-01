# Current status

Updated: 2026-11-02. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- Selected model: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled/none,
  repair-recheck, protected-v1 inspection, per-call-v1, public-checks-v1.
- Baseline: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds.
  Evaluation reserve is inside the total; solver time can expire earlier.
  Paid work requires exact task/model/credential/repeat scope and a positive cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These settings are a development baseline, not CLI defaults or general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

Keep the integrated development loop: fix observed correctness, reliability and
completion failures, validate locally, then exercise a frozen configuration.
A separate one-factor study is not required for every routine change.

The [eight-worker dev20 run](history/2026-11-01-parallel429-dev20-results.md) is CLOSED:
code c95fdda4, 19 tasks started, one not started, 9 independent PASS/5 FAIL/6 NOT_RUN
and 14 safety PASS/6 NOT_RUN. Its 1,583.372 seconds (26m23s) is an interrupted-batch
duration, not completed full20 throughput. The known settled generation cost is
USD22.435737 plus task18's final UNKNOWN response. Its USD0.524015 reservation is
not billed usage; actual total and unused allocation remain unknown. All allocations
are closed. Of 239 logical generations, 238 settled; all 245 input counts settled.
There were 484 physical attempt admissions and 483 responses, with no observed
429 or retry. No admission appears after the recorded stop-confirmed witness;
the actual shared-latch set time and the preceding interval were not recorded.

Task18 reached local solver-deadline expiry while awaiting a generation, after its
only accepted patch still failed a new public regression (9 leading spaces versus
8 expected). Task8 retained the original/helper discrepancy but submitted its
nearby-input repair and failed independently despite available resources. Task13
preserved the distinguishing public setup and passed independently. The six missing
verdicts prevent a new complete20 score or regression claim. See the result record
for public mechanisms, prior full20 comparison and evidence limits.

The requested [funded continuation](history/2026-11-01-funded-continuation-preparation.md)
is implemented and locally validated, not paid authorized or executed. The proposed scope is confirmed-state forks for tasks7/9/10/14,
a new task18 branch from the confirmed checkpoint after seq532 with its original
UNKNOWN ledger preserved, and a fresh task6 solve. Proposed limits are a cumulative
60 minutes per task and a new USD4 per task/USD24 total allocation; cumulative
40 model calls/100 actions/12 edits remain. Post-checkpoint consumption must still
count rather than reset. Focused coverage is 62 PASS/83.065 seconds; quick is
1,608 PASS/one host skip, including isolated mock evaluation. Exact provider-free
checkpoint/first-request binding precedes new paid authorization. This is a new
invocation proposal, not reopening the closed batch or silently retrying its lost call.
The task18 public projection retained 28 of 30 top-level fields identically; only
budget and action-horizon fields changed. Model utilization remains untested.

## Selected mechanisms and evidence limits

[Temporary-429 handling](history/2026-11-01-parallel429-preparation.md) is opt-in:
at most two retries per logical count/generation, Retry-After/backoff with jitter,
and at most 120 seconds scheduled backoff within the original deadline. Physical
attempts are journaled and obey the shared admission stop; SDK retries stay zero.
Quota, unknown errors, lost responses and usage uncertainty are not retry authority.
Local quick validation was 1,573 PASS/one host skip with retry/parallel/recovery and
isolated mock controls. This batch did not exercise live 429 recovery.

Keep [review lifecycle and delivery](history/2026-11-01-review-lifecycle-and-delivery-fixes.md)
and [requirement comparison](history/2026-11-01-requirement-comparison-continuity.md):
literal public quotes, bounded helper evidence, the latest matching recorded review,
historical diff currency and consistent completion guidance. Quoted identity and
recorded interpretation do not certify semantic completeness or current verification.
Task8 used historical comparison, but did not exercise every locally fixed fallback
path. More retained evidence alone does not establish autonomous repair improvement.

Keep [repair-plan delivery](history/2026-11-01-repair-planning-continuity.md),
[completion-reserve clarity](history/2026-11-01-completion-reserve-clarity.md),
[test discovery and expectation corrections](history/2026-11-01-failed8-and-test-discovery.md),
[verification reuse](history/2026-10-31-verification-reuse-decision.md),
[source retention](history/2026-10-30-plan-action-delivery-audit.md) and
[file lifecycle](history/2026-10-29-file-lifecycle-followup.md).
Their completed investigations and local checks belong in the linked records.
The [prior full20](history/2026-11-01-pre-edit-dev20-results.md),
[failed-eight rerun](history/2026-11-01-failed8-rerun-results.md) and
[earlier task8 analyses](history/2026-11-01-causal-link-task8-results.md) are separate
closed evidence, not active approval or combined current-code scores.

## Execution and claim boundaries

The latest task18 UNKNOWN does not reconcile older unresolved usage: the fourth
response of the [interrupted normal task8](history/2026-11-01-condition-normal-task8-results.md),
the [interrupted expectation review](history/2026-09-28-expectation-review-results.md)
and the [focused diagnostic history](history/2026-10-30-sqlfluff-deadline-review.md)
remain separate. Invoice and input-count endpoint billing are not independently
verified. All paid allocations are closed; no remainder grants new authorization.

Fresh solves, state forks, seeded repairs, saved-patch evaluations, operator public
comparisons and scripted local tests are distinct evidence. Public PASS, successful
delivery and safety PASS do not establish correctness; unverified_delivery does not
override an independent verdict. Never expose private evaluator bodies, hidden tests
or reference patches to the solver. Latest public audits read no private failing
assertions or response/continuation artifacts. Closure hashes encrypted request
material opaquely for identity without interpreting reasoning. Earlier operator
attribution remains separate from solver feedback.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact action/recovery identities, zero SDK retries and shared stop on uncertainty.
The current20 are development-exposed, not held out. Repeated performance, general
improvement and Linux CI remain unverified. [History](history/README.md) indexes
closed records; their approvals and next steps do not carry forward.
