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

The [execution-linked scope review](history/2026-10-31-execution-linked-scope-review.md)
is implemented and locally validated. At the existing brief-plan review, the model
can group public input/caller/outcome cases and link them to already returned
current-diff checks/probes, source inference or an explicit untested disposition.
The host validates references/currency, not semantic coverage or family completeness.
Failure and partial execution remain observations. The review stays in the existing
plan/event across prose replacement and completion; new edits mark old evidence
historical. No new tool, mandatory probe, reviewer agent or finish gate is added.

The triggering [fresh task 8 run](history/2026-10-31-affected-family-task8-results.md)
is CLOSED: independent FAIL / safety PASS, 213 public tests PASS, USD0.921602,
475.843 seconds, 12 calls/18 actions/one edit/two probes on code 60029805. Public
family source and exact helper programs were delivered, yet the model chose checks
and replay without a new family/input case. Its raw-array helper differs from the
reporter's bytes/caller construction, which it explicitly left unverified. Resources
remained available. This shows a verification-selection gap, not a proven model
capability ceiling or the latest private failure's exact cause.

A small diagnostic is being prepared at that run's public input 171, immediately
before submission, with candidate be082f27 fixed. Existing source/check/probe facts
remain available; no later verdict or operator counterexample enters its context.
The new review must lead to an actually executed, publicly grounded unverified case
to support uptake. A populated format, probe count or generic report alone is not
success. It cannot establish repair or independent acceptance because mutation and
private evaluation are excluded. Proposed scope is one GPT-5.4/xhigh attempt,
USD2 total, four calls/12 actions/two probes/600 seconds; new exact-scope approval
is pending. Prior paid allocations remain closed.

Final local checks: **92 focused PASS in 46.16 seconds**, **1,418 quick PASS /
1 host-symlink SKIP in 402.42 seconds**, isolated mock evaluation and Ruff. Quick
used four workers with no restart. The external diagnostic driver passed **19
mocked tests in 60.23 seconds**. These are mechanism/transport checks, not model
uptake. Runtime is
`sha256:0963cb074795d1809310160f02dd3c2bc42efe892af302846c3a6454bf598e75`.
The unchanged system-prompt ceiling is respected (10,778 characters).

The new execution-reference contract also needs discoverable source IDs. A bounded
index now links only retained repository source_spans to their prior public reads
by exact scope/path/file hash/range, including inline delivery after segment reset.
It adds no source text or edit permission and uses the same helper in the diagnostic.
Candidate/source/dependency/image and credential-shape preparation passed without
provider, target or evaluator calls. The exact sealed plan and approval gate live
under `C:/pt/evidence8-review-20261031-v1/`; no paid diagnostic has run.

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
