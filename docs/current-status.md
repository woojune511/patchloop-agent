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

[Two-probe recovery preparation](history/2026-11-01-two-probe-recovery-preparation.md)
revises the last interpretation: one new probe was insufficient to allow the
observed meaningful setup correction. The user requested proceeding with a small
resource adjustment. Prepare two new probes and 600 seconds at the same task8
post-probe public checkpoint; keep the USD1.5431895 proposed new cap, four model
calls, ten actions, 60k input and full 25k-output reservation or stop. Keep the
model, fixed be082f27 patch, report guidance, tool policy and other conditions.
No new hint, failed-v1 program or corrected UID setup is added to the model input.

The source checkpoint remains run_dev_62da82f8f7e34345 sequence38/ancestor138 with
its recorded one-probe/265-second remainder. The new allocation is separately
bound and consistently reflected in current state/budget. Fresh usage starts at
zero. Public reconstruction excludes opaque continuation and later reports; it is
not exact resume. No core runtime or normal-dev probe policy changes are needed.
Normal runtime remains
`sha256:4fdcc4fb9eb3d71ad81a5d929a0af689cecd876fbd39c212204d0c6343b608c7`.

The [previous live diagnostic](history/2026-11-01-goal-grounded-stopping-results.md)
is CLOSED on code515338cf: two model/count calls, one probe, USD0.4662705 generation
cost, 231.511 seconds, PROBE_CALL_LIMIT and no final report. It selected a relevant
extension from write_dataset to save_as, but failed importing an unavailable UID
symbol before exercising the target. It then correctly classified setup failure
and proposed a corrected helper. Explicit probe0 blocked that execution; this was
not an unnecessary repetition of a passed check. About33.5 seconds remained at
termination, so probe count alone did not establish enough time for recovery/report.

The earlier priority against raising resources was too strong; the separate
follow-up records this correction without rewriting closed evidence. A useful
next observation is actual target execution and a properly bounded report, with
setup-repair behavior observed if needed. Two probes are permitted, not required.
The count/time intervention and one stochastic rerun cannot isolate each change's
causal effect or establish general repair gains. No independent evaluation or
candidate mutation is permitted. No retry, resume or extra sample on uncertainty.

Preparation: C:/pt/stop-review-20261101-v2/. Intended live root:
C:/pt/stop-review-run-20261101-v2/ (must remain absent until exact-scope approval).
No new paid run has occurred. The previous unused USD1.076919 and all older
allocations remain closed; they do not authorize this invocation.

The [report-description change](history/2026-11-01-goal-grounded-diagnostic-stopping.md)
remains implemented: ground the conclusion and stopping rationale in the original
public task and authorized review objective. No new field or semantic gate.
Prior validation remains27 focused PASS and1,437 quick PASS/one platform symlink
skip including isolated mock evaluation. This turn changes external diagnostic
allocation/tests and documentation only; focused external validation and docs-only
repository checks are recorded in the linked preparation.

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
