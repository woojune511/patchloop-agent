# Current status

Updated: 2026-11-01. Runtime source owns behavior. Historical reports are evidence,
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

Keep the integrated development loop: fix observed correctness, reliability and
completion failures, validate locally, then exercise a frozen configuration.
A separate one-factor study is not required for every routine change.

[Goal-grounded diagnostic stopping](history/2026-11-01-goal-grounded-diagnostic-stopping.md)
is implemented in two existing report-tool descriptions. report_discovery's required
justification now grounds both the expected/observed conclusion and the decision to
stop against the original public task and authorized review objective. It asks for
the most consequential remaining uncertainty, a small allowed discriminating
observation, and evidence or concrete constraints explaining why to omit it.
Completing a self-chosen helper plan or listing limitations alone is not that reason.
Evidence already settling the review objective can justify immediate reporting.

The seven report fields, outcomes, parser, budgets and report availability are
unchanged. No new field, semantic gate or mandatory probe is introduced. The normal
solver's prompt and finish_task behavior are unchanged; this is diagnostic terminal
guidance, not a demonstrated repair improvement. Plausible rationales still require
public evidence review and may be unsupported.

The new saved-state diagnostic preparation uses the actual post-probe counted
request from run_dev_62da82f8f7e34345 at sequence 38, before its final reporting
response. Public calls/results and the original input138 ancestry are bound;
opaque reasoning continuation and later reporting output are excluded. The active
review is probe_result, not a reactivated behavior_change. Prior same-candidate
probe evidence can support references without importing execution/cache/check,
mutation or cost authority. This is public reconstruction, not exact resume.

Proposed new scope: task8/pydicom1413, fixed be082f27, gpt-5.4-2026-03-05/xhigh,
one attempt, USD1.5431895, four calls/ten actions/one new probe/265 seconds,
60k input/full 25k-output reservation or stop. It mirrors the source request's
displayed remaining resources; a new allocation still needs authorization.
Preparation: C:/pt/stop-review-20261101-v1/. Live root must remain absent until
authorized: C:/pt/stop-review-run-20261101-v1/. No new paid run has occurred.

Local focused validation: 27 PASS in 27.472 seconds. Quick: 1,437 PASS, one
platform symlink skip in 485.301 seconds, including isolated mock evaluation.
External packet validation and immutable bindings are in the linked follow-up.
Normal runtime remains
`sha256:4fdcc4fb9eb3d71ad81a5d929a0af689cecd876fbd39c212204d0c6343b608c7`.
Diagnostic implementation and request identities change with the descriptions.

Why this decision: the [last task8 diagnostic](history/2026-11-01-task8-expanded-budget-results.md)
is CLOSED on f06e50dc: three calls, one read, one probe, one report,
USD0.6170485 recorded generation usage/432.903 seconds, maximum 39,650 input tokens.
It executed nine cases with exact encoded-byte assertions, all PASS; final
scope_review correctly bound current execution and left one group untested.
No counterexample, mutation, original-caller reproduction or independent evaluation.
Generation usage is known; count-endpoint billing/invoice reconciliation is not.

The original H-array -> bytes -> lineSeq.add_new -> ds.save_as path remained
unverified. The public stop rationale described completion of its helper plan;
it did not explain whether the remaining gap could change the conclusion or why
another observation was infeasible. This is an unresolved selection/stopping
question, not proven premature normal submission: reporting with limitations was
allowed, and normal checks were not offered. Remaining resources do not guarantee
that a new response, probe and report fit. Do not require more probes as the metric.

Three calls/max 39,650 tokens also fit the former caps, and no search occurred.
Do not attribute progression to higher limits or deduplication, or raise caps again.
The [search coalescing implementation](history/2026-11-01-search-span-coalescing-and-diagnostic-budget.md)
and [execution-linked scope review](history/2026-10-31-execution-linked-scope-review.md)
remain selected. Cross-read/inline overlap and imported-span novelty limitations
remain; no new mechanism is justified by this preparation alone.

Both prior input138 allocations and the [inactive input171 diagnostic](history/2026-10-31-execution-linked-task8-diagnostic-results.md)
are closed. Their approvals and unused balances do not carry forward. The new
observation sought is a grounded action OR justified stop at the post-probe state,
not exhaustive coverage, extra probe counts, repair gain or generalization.

Relevant closed evidence:

- [Full fixed dev20](history/2026-10-31-verification-reuse-dev20-results.md):
  11 independent PASS, 8 FAIL, 1 unsubmitted/NOT_RUN; 19 safety PASS. USD20.2818755
  against the closed USD80 allocation. Task 14 demonstrated autonomous
  counterexample execution and repair, without attribution to a particular rule.
- [Verification continuity](history/2026-10-31-verification-continuity.md) retains
  exact recent probes and the latest rejected test proposal across handoffs;
  historical proposals remain unapplied/unverified. No new tool or gate. YAML
  rejection distinguishes unsupported type from undeclared test root.
- [Prior fresh 8/10](history/2026-10-31-verification-continuity-0810-results.md):
  both independent FAIL / safety PASS at 4559062d, USD1.1940825, 278.086 seconds;
  closed USD8 allocation. Input retention alone did not establish repair gain.
- [Saved-failure operator audit](history/2026-10-31-continuity-0810-failure-attribution.md):
  prior task 8 retained a sibling-class defect; task 10 failed extra concrete
  initialization/API expectations not explicit in the public issue, before its
  output assertions. Private specifics stay outside solver hints/tests/guidance.
  Neither audit changes grading or applies its exact cause to the latest patch.

Task 12's oracle ambiguity, task 18's diagnostic delay and selected-test overlap
remain open. Public requirements versus stronger benchmark expectations remain a
separate issue; do not treat undisclosed API expectations as generic reasoning failure.

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

Earlier local validation belongs to the corresponding closed records above.
Focused delivery controls stayed under two minutes; local mechanism checks remain
separate from the fresh task outcomes.
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
and scripted local tests are distinct evidence. The full20, prior 8/10 and latest
task 8 submissions remain unverified_delivery for registered original-case proof,
independently of acceptance.
Never expose private evaluator bodies, hidden tests or reference patches to the
solver. Public PASS, successful delivery and safety PASS do not establish correctness.
The latest public run audit read no private bodies. The earlier user-requested
operator attribution read prior saved failures/criteria, separate from solver context;
raw provider reasoning and reference-patch contents were not used.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
or cleanup uncertainty. The current 20 tasks are development-exposed, not held out.
Repeated performance, general improvement and Linux CI remain unverified.
[History](history/README.md) indexes closed records; their approvals and next steps
do not carry forward.
