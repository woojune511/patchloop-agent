# Current status

Updated: 2026-10-31. Runtime source owns behavior. Historical reports are evidence,
not an active queue.

## Product and working baseline

Build a single coding agent that repairs public software tasks, verifies changes
and submits within bounded resources. Start improvements from observed failures.
Recovery, sandboxing and isolated evaluation support that product.

- dev-head is the sole mutable runtime; official=false and claim-ineligible.
- Selected model: gpt-5.4-2026-03-05, xhigh, 25,000 output tokens.
- Policies: segmented-v1, result-or-size-v1, brief-v1, probes enabled/none,
  repair-recheck, protected-v1 inspection, per-call-v1, public-checks-v1.
- Limits: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds.
  Evaluation reserve is inside the total; solver time can expire earlier.
  Paid work requires exact task/model/credential/repeat scope and a positive cap.
- Cross-run memory, held-out tuning and claim execution are disabled. Bounded
  run-local notes remain available. Historical Rapid executables are absent.
- These settings are a development baseline, not CLI defaults or general accuracy.

See [guide](../.agent/guide.md), [operations](operations.md), [product](product.md)
and [evidence boundaries](evidence.md).

## Active decision

Keep the integrated development loop: choose fixes from observed correctness,
reliability and completion failures, validate locally, then exercise a frozen
configuration on public development tasks. A separate one-factor study is not a
prerequisite for every routine change.

The [full fixed dev20 run](history/2026-10-31-verification-reuse-dev20-results.md)
remains CLOSED: 11 independent PASS, 8 FAIL, 1 unsubmitted/NOT_RUN; all 19 submitted
candidates have safety PASS. Its USD20.2818755 cost and USD80 allocation are closed.
It exposed original-input/oracle gaps on tasks 8/10/12, diagnostic latency on task 18
and residual selected-test overlap. Task 14 demonstrated autonomous counterexample
execution and repair; that observation is not an estimate of a guidance effect.

The [verification continuity correction](history/2026-10-31-verification-continuity.md)
retains exact bound recent probe programs and the latest rejected test proposal
across handoffs. Historical proposals remain unapplied/unverified; no new tool,
model call, obligation or finish gate is added. YAML rejection now distinguishes
a declared but unsupported file type from an undeclared test root.

The [fresh task 8/10 run](history/2026-10-31-verification-continuity-0810-results.md)
is now CLOSED: **both independent FAIL / safety PASS**. Code was **4559062d**,
runtime `sha256:832d5d3f6c58da7a64af4743794f1557fa1b307245110c7e86ce98b89f453ab3`.
Each was attempted once from pristine source with the same baseline, USD4 each /
USD8 total and two workers; no old patch or operator counterexample was supplied.
Total **USD1.1940825**, 19 model calls, 32 actions, two accepted edits, one probe;
batch wall **278.086 seconds (4m38s)**. All 19 counts and calls settled, with no
retry, uncertainty stop or extra independent evaluation. This allocation is closed.

Task 8 independently found the missing OL/OD binary setter exclusions before any
probe, added a bytes-preserving writer regression, and passed 213 public tests.
Its later probe confirmed OL/OD byte preservation plus LO text splitting. The exact
program survived into completion input and the final assessment used the results.
However, no later counterexample or repair followed that delivery, and the original
array('H') -> Dataset.add_new -> Dataset.save_as caller was not executed on either
base or candidate. Program retention cannot explain the earlier source discovery.

Task 10 changed import-time logging setup and passed 96 tests with one skip, but its
new test checks handlers/level/debugging state without emitting or counting records.
No mutation was rejected and no probe was run: both retention mechanisms were
unexercised. There was no stronger earlier assertion lost during this fresh attempt.
Its original duplicate-output behavior remains unobserved. These public records do
not establish a remaining source defect or the private FAIL's exact cause.

Both submissions remain unverified_delivery, with zero registered original-case
executions. Their acquisition states ended at preparation_action_limit; whole-run
resources were not exhausted and ordinary probes/checks remained available. Neither
this limit nor incomplete caller evidence is a demonstrated cause of private FAIL.

The [saved-failure operator audit](history/2026-10-31-continuity-0810-failure-attribution.md)
has now attributed both independent failures without executing anything again.
Task 8 retains a sibling input-class defect; the public controls omitted that class.
Task 10 fails additional concrete initialization/API expectations not explicit in
the public issue. Its output assertions were not reached, so missing output-count
verification is not the captured failure cause. Both grading runs completed with
all required cases accounted for; no infrastructure or patch-identity error explains
them. Exact private assertions and actual/expected values remain external operator
evidence and must not enter solver hints, public tests or runtime guidance.

Keep the delivery correction without a repair-gain or causal efficiency claim.
The next design questions differ: deriving affected input families from public
source, and distinguishing public task requirements from stronger benchmark
expectations. Do not treat the latter as generic reasoning failure or change grading
from this audit alone. No runtime change or further execution was performed or
scheduled. Task 12's oracle ambiguity, task 18's diagnostic delay and selected-test
overlap remain open.

## Selected mechanisms and evidence limits

Keep the [reuse correction](history/2026-10-31-verification-reuse-decision.md),
[post-mutation review](history/2026-10-30-post-mutation-review.md),
[observation retention](history/2026-10-30-verification-evidence-reuse.md),
[source retention](history/2026-10-30-plan-action-delivery-audit.md), and
[test execution visibility](history/2026-10-30-test-execution-visibility-and-latency.md).
The [test-validation conflicts](history/2026-10-30-test-validation-fixes.md) and
[file lifecycle](history/2026-10-29-file-lifecycle-followup.md) fixes remain selected:
multiple/new files, receipt undo, original-byte restoration and bounded recovery.
The YAML diagnostic correction above preserves those earlier mutation policies.

The frozen run used a prior local baseline of quick 1,308 PASS / 1 host-symlink SKIP
with isolated mock, final wording/contract 156 PASS and Ruff. The subsequent
continuity correction passed **1,362 quick tests / 1 host-symlink SKIP**, including
isolated mock evaluation, plus Ruff; final quick wall was 281.54 seconds with four
workers. Focused delivery controls stayed under two minutes. These local
mechanism checks are separate from the fresh 8/10 outcomes above.
The [prior three-task run](history/2026-10-31-verification-reuse-1411-results.md)
and [older full 20 run](history/2026-10-29-repair-dev20-results.md) remain closed
historical context. Different task paths/settings and single attempts do not
establish a causal quality or speed gain.

The current SQLFluff 16 candidate restored its first success-guard regression and
passed 167 public tests, then failed independent evaluation. Its public helper
returns a whole-file parsing error without crashing; the public report alone does
not prohibit that behavior. Do not import private expectations into new public
requirements. The [earlier operator assertion replay](history/2026-10-31-sqlfluff-assertion-log-replay.md)
concerns a different saved patch and unchanged grading, not the current candidate.

## Execution and claim boundaries

All paid allocations are closed. Older unresolved billing, including the
[interrupted expectation review](history/2026-09-28-expectation-review-results.md)
and [focused diagnostic history](history/2026-10-30-sqlfluff-deadline-review.md),
is not reconciled by this batch's settled usage.

Fresh solves, seeded repairs, saved-patch evaluations, operator public comparisons
and scripted local tests are distinct evidence. The full20 submissions and both new 8/10 submissions remain
unverified_delivery for registered original-case proof, independently of acceptance.
Never expose private evaluator bodies, hidden tests or reference patches to the
solver. Public PASS, successful delivery and safety PASS do not establish correctness.
The public run audit read no private bodies. The subsequent user-requested operator
attribution read saved private failures/criteria, kept separate from solver context;
raw provider reasoning and reference-patch contents were not used.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
or cleanup uncertainty. The current 20 tasks are development-exposed, not held out.
Repeated performance, general improvement and Linux CI remain unverified.
[History](history/README.md) indexes closed records; their approvals and next steps
do not carry forward.
