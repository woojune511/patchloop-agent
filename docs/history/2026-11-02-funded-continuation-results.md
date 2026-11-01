# Funded continuation: six evaluations completed, four PASS and two FAIL

Closed: 2026-11-02 KST. Execution commit: `508aa6965baca22a90d62d97811464a7f14f6453`.
Lane: dev-head, official=false, claim-ineligible. All six new allocations are CLOSED;
the original batch and its unresolved billing record remain unchanged.

## Why this investigation

The [eight-worker batch](2026-11-01-parallel429-dev20-results.md) left six verdicts
unavailable after task18 exhausted solver time while awaiting a generation. Four
peers had confirmed public progress; task6 had never started. The user requested
more time and separately funded continuation rather than discarding that progress.
The question was whether confirmed state could support further repair and evaluation
without refunding consumed resources or resolving the lost response by assumption.
Additional capacity could enable work; it would not itself establish better diagnosis.

The [preparation record](2026-11-01-funded-continuation-preparation.md) describes
restoration, resource accounting and local validation. This record closes the live
invocation, not a controlled comparison of time, state retention or reasoning ability.

## Intervention and completed results

Tasks18/9/10/7/14 continued from confirmed public checkpoints; task6 started fresh.
Each ran once, with six workers, gpt-5.4-2026-03-05/xhigh and the existing credential
file. Limits were a cumulative 3,600 seconds including 330 seconds for evaluation,
40 model calls, 100 actions and 12 edits; new funds were USD4 per row/USD24 total.
Task18 retained its excluded historical call in cumulative consumption. No private
evaluation feedback or operator diagnosis entered the resumed context.

The batch completed in **1,409.815489 seconds, approximately 23m30s**, spending
**USD4.974666 in new settled generation cost**. All 40 new generations and 44 input counts
settled; 84 physical attempt admissions had 84 response receipts. There were no
429 rejections, retries or shared stop. All six safety verdicts were PASS.

| Task | Start | Independent acceptance | New generations | New USD |
| --- | --- | --- | ---: | ---: |
| 18 | Confirmed-state branch | PASS | 13 | 2.245917 |
| 9 | Confirmed-state branch | PASS | 3 | 0.394422 |
| 10 | Confirmed-state branch | FAIL | 6 | 0.660947 |
| 7 | Confirmed-state branch | FAIL | 4 | 0.4935115 |
| 14 | Confirmed-state branch | PASS | 3 | 0.302404 |
| 6 | Fresh | PASS | 11 | 0.8774645 |

Combining the original fourteen evaluations (9 PASS/5 FAIL) with these six gives
**13 PASS/7 FAIL across twenty task identities**. That is a mixed result containing
fifteen fresh solves and five continuations with added resources, not a new fresh20
score, full20 runtime, generalization result or causal improvement estimate.
The original task18 response remains UNKNOWN. Its USD0.524015 reservation is not
an observed charge; total cost across both invocations remains unknown.

## What the public records establish

The five continuation audits retained non-budget public context. Task18 was compared
directly with its parent public projection; tasks9/10/7/14 used the original
hash-bound restoration rehearsals. Only remaining-budget fields changed, plus
task18's action horizon. This verifies recorded public continuity, not complete
provider-wire delivery or model utilization.

Task18 did continue its inherited investigation. It began with the unchanged
eight-space expectation and a public result of one failure/507 passes, plus a plan
to investigate repeated-fix convergence. Its first resumed edit failed that same
regression. One helper crashed in instrumentation; the plan treated it as no
transition evidence. Corrected instrumentation then observed L003 producing eight
spaces, L039 changing eight to five, and L003 changing five to nine. Another edit
returned to the exact known-failing candidate, an observed inefficiency. The final
L039 change preserved start-of-line state across leading whitespace. The unchanged
default-caller regression and public suite passed 508 tests; a helper replay showed
eight-space WITH and four-space top-level SELECT output. Independent acceptance
subsequently passed. This supports successful continuation of this investigation,
without attributing success solely to more time or retained state.

Task7 made no further edit: required regression passed 39 tests, selected iterable
and formatting tests passed, and the reported Dataset/SomeName helper succeeded.
Its before/after comparison recorded iterable failure before and success after,
but remained INCONCLUSIVE for original-requirement credit. Task10 removed import-time
handler/formatter/level setup, passed 96 tests with one skip, and passed a reset/reload
logging helper. That helper did not reproduce first-import duplicate records under
a preconfigured client logger. Both final assessments explicitly retained original
verification gaps. Their saved plans still selected submission after visible PASS.
At submission, task7/task10 retained 31/29 calls, 89/82 actions, 11 edits each and
about 47m32s/43m52s of solver time. Exploration and further verification tools
remained available. Their independent failure details were not inspected; the
public evidence identifies a stopping decision, not the hidden failure cause.

## Operator defects, closure and decision

Provider-free v1 preparation failed because the rehearsal parent directory was
absent. Its receipt was preserved; v2 created only that parent and passed 15 local
collector/launcher fixtures. During live execution, the frozen collector incorrectly
required effective inherited elapsed time to equal the parent's latest event value.
Runtime correctly used the maximum of prepared-turn and parent time, conservatively
adding 505/11/444/477ms for tasks9/10/7/14. A separate observer corrected that projection,
with 19 tests; approved runtime, manifest and original collector stayed frozen.

Closure audit passed with no issues, backed by 14 helper tests. It checked immutable
parent metadata, new-only settlement, cumulative resources, manifest authority and
transport receipts. No additional API calls or evaluations were used for these audits.
Keep separately funded continuation as an explicit operation, not automatic retry.
The remaining question is why known verification gaps are judged sufficient for
submission despite available capacity; the public traces favor investigating that
decision over assuming lost context or insufficient budget. Specific independent
failure causes and broader checking benefits remain unresolved.

## Evidence

- [Closed summary](C:/pt/funded-continuation-run-20261101-v2/summary.json) and [result](C:/pt/funded-continuation-run-20261101-v2/result.json).
- [Closure audit](C:/pt/funded-continuation-closure-20261102-v1/closure-audit.json) and [bound closure receipt](C:/pt/funded-continuation-closure-20261102-v1/closure-receipt.json).
- [Five public-context comparisons](C:/pt/funded-continuation-closure-20261102-v1/continuity/receipt.json).
- [Task18 public investigation](C:/pt/funded-continuation-closure-20261102-v1/task18-public.json) and [tasks7/10 public audits](C:/pt/funded-continuation-closure-20261102-v1/public-failed-rows/summary.json).
- [v1 preparation failure](C:/pt/funded-continuation-20261101-v1/preparation-failure.json), [v2 preparation validation](C:/pt/funded-continuation-20261101-v2/collection-validation.json), and [observer correction](C:/pt/funded-continuation-closure-20261102-v1/observer-correction.json).
