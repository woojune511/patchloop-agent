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

The [search overlap and diagnostic budget change](history/2026-11-01-search-span-coalescing-and-diagnostic-budget.md)
is implemented. Both repository and registered dependency searches now merge
same-source overlapping windows after the existing 20-hit/24,000-character
selection. Exact selected lines, source authority, gaps and truncation are
preserved; freed space does not select more matches. Existing replay output stays
unchanged. No new reasoning prompt, tool, mandatory probe or finish gate is added.

Offline replay of the prior selected search spans preserves all 45 unique lines
and 20 query matches while reducing displayed lines 100 -> 45, spans 20 -> 5,
and source characters 11,209 -> 4,694. This is not a new full-request token count
or evidence of live counterexample construction, repair gain or generalization.

The new external diagnostic preparation is `C:/pt/active8-review-20261101-v2/`:
saved task8 input138 and candidate be082f27, gpt-5.4-2026-03-05/xhigh, maximum six
model calls and 60,000 input tokens. USD2, 600 seconds, 12 actions, two probes and
25,000 output tokens remain unchanged. Developer state and the latest budget
message now share one current snapshot. The driver reserves the full output cap
or stops; six maximal calls would cost USD3.15, so USD2 does not guarantee six.
This changes diagnostic limits only; the normal solve baseline above is unchanged.
No new paid invocation is approved or executed, and the v2 live root is absent.

Local validation: 22 focused PASS (9.244 seconds), 28 external-driver mocks PASS
(109.12 seconds), 1,435 quick PASS / one host-symlink SKIP (445.102 seconds),
isolated mock evaluation and Ruff. Five stale planning tests were corrected and
passed separately; no additional production rule was needed. Details and failed
baseline evidence are in the linked follow-up. Live model uptake remains unverified.
Runtime is `sha256:4fdcc4fb9eb3d71ad81a5d929a0af689cecd876fbd39c212204d0c6343b608c7`.

Why this change: the [active input138 diagnostic](history/2026-11-01-task8-active-review-results.md)
is CLOSED on f3d2f8d7. Active behavior_change was delivered; the model named two
untested groups and a grouped probe, then made two reads and one search. The fourth
count was 43,789 > 40,000 tokens, blocking generation. Three calls cost USD0.4259615
over 250.368 seconds; USD1.5740385, two probes and about 350 seconds remained.
No executable probe, report, mutation or evaluation occurred. Count-endpoint billing
and invoice reconciliation remain unverified. That is an input-admission stop,
not a proven capability ceiling or observed choice to abandon execution.

The [execution-linked scope review](history/2026-10-31-execution-linked-scope-review.md)
remains selected. It links public case groups to current-diff executions, source
inference or explicitly untested cases. The host checks reference validity/currency,
not semantic coverage. Retained source IDs remain discoverable across handoffs.
The [input171 diagnostic](history/2026-10-31-execution-linked-task8-diagnostic-results.md)
used an inactive behavior_change point and returned an immediate report; it did
not test the active review. Both prior allocations and result roots remain closed.

Next unresolved question: with room to proceed, does the active review construct
and execute a discriminating public case, then interpret its result? The diagnostic
cannot show repair because mutation is disabled. The original bytes/caller path
still differs from the model's raw-array helper; do not import a task-specific
answer or private evaluation criterion. Cross-read overlap also remains, and
fresh-session source-gain counters do not subtract imported inline spans. They
cannot establish novelty relative to the saved packet. Do not add state or gates
without evidence that these remaining limitations obstruct the next decision.

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
