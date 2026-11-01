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

The [funded continuation](history/2026-11-02-funded-continuation-results.md) is CLOSED:
code 508aa696, five confirmed-state branches (7/9/10/14/18) and one fresh task6,
maximum six workers, new USD4 per task/USD24 total, cumulative 3,600 seconds per
task including 330 seconds for evaluation. Cumulative 40 model calls/100 actions/
12 accepted edits and all prior consumed resources were retained. This explicit
invocation did not change the normal 1,800-second baseline.

All six submitted and were independently evaluated: **4 PASS (6/9/14/18), 2 FAIL
(7/10), safety 6 PASS**. New generation cost is USD4.974666 and batch duration is
1,409.815 seconds (23m30s). All 40 new generations, 44 input counts and 84 physical
attempts settled; no 429, retry, new UNKNOWN or shared stop occurred. The allocation
is closed; unused funds grant no further invocation.

The [original interrupted batch](history/2026-11-01-parallel429-dev20-results.md)
had 9 PASS/5 FAIL/6 NOT_RUN, known settled cost USD22.435737 and one UNKNOWN task18
response. Its USD0.524015 reservation remains unknown usage, not a billed amount.
Original and new allocations stay separate; combined actual cost remains unknown.
Combining the fourteen original verdicts with these six yields **13 PASS/7 FAIL,
safety 20 PASS**. That is a mixed completion record containing five state branches,
not a new fresh20 score or evidence of a controlled performance improvement.

All five first live public contexts retained their comparison baseline's patch,
plans, open questions, checks and source facts; budget/time fields changed as
expected. Task18 was compared directly with its original public context; the other
four used the approved reconstruction baseline bound to the immutable prefix.
This establishes public-state continuity, not complete provider-wire delivery or
use of every field by the model.

Task18 carried its unresolved public failure through further probing and three
accepted edits. The final patch preserved the inherited WITH regression input and eight-space
assertion, changed the regression from 1 FAIL/507 PASS to 508 PASS, then passed
independently. It used all thirteen new model slots (39 child calls plus the old
excluded UNKNOWN call = 40 cumulative). It also revisited the exact previously
failed patch before finding the final L039 line-start-state repair. More available
time enabled this observed continuation; the run does not isolate a general time
or memory effect.

Tasks7/10 submitted with acknowledged original-verification gaps and 31/29 model
calls still available. Their retained plans treated passing visible checks plus
reporting the gap as sufficient to submit. Resource exhaustion or missing stored
state does not explain those observed choices; the private failing assertions were
not inspected. The unresolved questions are how completion judgments use retained
gaps and how repairs avoid known failed candidates. The completion policy remained
unchanged during this run.

Preparation and runtime remained frozen during execution. An operator-only
collector incorrectly required inherited elapsed time to equal the last parent
event, rejecting the reconstruction's conservative extra 11-505 ms. A separate,
tested observer corrected this projection without changing the approved runtime
or parent records. Final scope/accounting/resource audit passed. See the result
record for preparation failures, local controls and immutable evidence links.

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
The current20 are development-exposed, not held out. Repeated performance and general
improvement remain unverified. The [integration audit](history/2026-11-02-main-integration-contract-audit.md)
records bounded evidence delivery, recovery and Git-index fixes plus refreshed
regression controls. Full Ubuntu/Windows validation is tracked in
[PR #23](https://github.com/woojune511/patchloop-agent/pull/23).
[History](history/README.md) indexes
closed records; their approvals and next steps do not carry forward.
