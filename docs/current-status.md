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

The [latest frozen full dev20](history/2026-11-01-pre-edit-dev20-results.md) is CLOSED:
**12 independent PASS, 8 FAIL, 20 safety PASS**, all 20 submitted once. Execution
HEAD f994a2b6 retains runtime implementation e6374d6f. Recorded generation cost is
USD20.972777 under a new USD80 cap; batch wall is 4,916.317 seconds (81m56s), excluding
preparation. All 274 model calls and 276 input counts settled. No retry, extra
evaluation or mid-batch runtime change occurred. USD59.027223 remains closed.

Against the [previous full20](history/2026-10-31-verification-reuse-dev20-results.md),
task18 changed from unsubmitted/NOT_RUN to PASS; the other 19 acceptance verdicts
are unchanged. Previous totals were 11 PASS/8 FAIL/1 NOT_RUN, USD20.2818755 and
5,513.593 seconds. Requests differ only in fresh state roots, but multiple runtime
changes and one attempt per task prevent attributing the difference to one feature.

The current [failed-eight/discovery follow-up](history/2026-11-01-failed8-and-test-discovery.md)
implements two bounded corrections before another paid panel:

- New pytest modules must match confirmed public filename patterns. A known
  mismatch rejects the atomic edit before any file changes, with the config/hash
  and naming rules. Explicit selection does not ensure ordinary directory discovery.
  Unresolved configuration remains unknown; matching a filename is not collection
  or assertion coverage. Original tests and existing-file selection are preserved.
- Existing scope review separates the required `outcome` from its `public_basis`,
  within the previous 500-character expectation budget. Unknown values use null;
  legacy strings remain readable. Post-edit guidance compares literal public
  conditions and selects relevant compatibility controls. A new test's expected
  value or suite PASS cannot supply its own oracle. Receipt validity is not semantic
  validation. No extra model call, mandatory probe or finish gate was added.

All eight failed tasks (7/8/10/12/13/16/17/19) were audited from saved public inputs,
source/actions/checks and submitted patches. The immutable evidence is under
`C:/pt/failed8-public-20261101-v1/`, with per-task event/hash references. No private
bodies were read. Public specs were checked against actual dispatched requests.
The audit found condition substitutions (8/13), insufficiently grounded exact
expectations (12/16), and compatibility claims lacking specific evidence (10/17/19).
Task7's public example and task19's minimum preservation requirement have supporting
executions; a universal explanation for all eight FAILs is not established. Exact
private failing assertions remain uninspected. The implementation is locally tested,
not live evidence that these tasks now pass or cost/time improved.
Final focused validation is 88 PASS in 20.65s. Quick resolves to 1,494 PASS/one
host skip across the initial run and corrected contract-expectation rechecks;
isolated mock evaluation, Ruff and documentation checks pass. Details and limits
are in the follow-up record; prior private grading and frozen identities are unchanged.

Retain the [planning delivery correction](history/2026-11-01-repair-planning-continuity.md):
compact repair now carries canonical plans, notes and review requests. The
[fresh task18 run](history/2026-11-01-repair-continuity-task18-results.md) at 21793a4b
is CLOSED: **independent PASS, safety PASS**, 34 calls, 45 actions, two edits,
13 probes, USD3.568309 and 1,473.436 seconds. Its USD4 allocation and remainder are
closed. All actual inputs and costs settled. The model stored and reused the finding
that L039 undid correct indentation, reverted an ineffective L003 edit and repaired
L039 while preserving the new test's input/assertions. One unchanged-base probe
still repeated; that earlier finding was never stored. Residual semantic probe
repetition is not addressed by the current discovery/oracle change.

Task18's final 506 required tests and one explicitly selected test passed, but the
new test filename missed ordinary collection; that concrete omission motivates the
new filename admission. Calls fell from 40 to 34 versus the preceding run while
cost and time rose, so no efficiency effect is claimed. No paid run is scheduled.
A future authorized integrated failed-task panel with passing controls can assess
repair decisions, independent acceptance and regressions together.

Earlier [input correspondence](history/2026-11-01-pre-edit-task-correspondence.md),
[condition comparison](history/2026-11-01-public-input-comparison.md) and
[capability-aligned diagnostic](history/2026-11-01-capability-aligned-verification-review.md)
mechanisms remain selected. Task12's oracle ambiguity and stronger private versus
public expectations remain separate questions. Earlier saved-patch attribution
cannot establish the exact failure cause for a fresh submission.

## Selected mechanisms and evidence limits

Keep the [reuse correction](history/2026-10-31-verification-reuse-decision.md),
[post-mutation review](history/2026-10-30-post-mutation-review.md),
[observation retention](history/2026-10-30-verification-evidence-reuse.md),
[source retention](history/2026-10-30-plan-action-delivery-audit.md), and
[test execution visibility](history/2026-10-30-test-execution-visibility-and-latency.md).
The [test-validation conflicts](history/2026-10-30-test-validation-fixes.md) and
[file lifecycle](history/2026-10-29-file-lifecycle-followup.md) fixes remain selected:
multiple/new files, receipt undo, original-byte restoration and bounded recovery.
The [verification continuity](history/2026-10-31-verification-continuity.md) change
retains recent probe programs and rejected test proposals; YAML rejection identifies
unsupported type. Task17 recovered from that contract rejection but still failed grading.

Earlier local validation belongs to the corresponding closed records above.
Focused delivery controls stayed under two minutes; local mechanism checks remain
separate from the fresh task outcomes.
The [prior three-task run](history/2026-10-31-verification-reuse-1411-results.md)
and [older full 20 run](history/2026-10-29-repair-dev20-results.md) remain closed
historical context. Different task paths/settings and single attempts do not
establish a causal quality or speed gain.

The latest SQLFluff16 candidate passed 167 public tests and broader self-authored
branch checks, then failed independent evaluation. The public report alone does
not settle every parser contract. Do not import private expectations into public
requirements. The [earlier operator assertion replay](history/2026-10-31-sqlfluff-assertion-log-replay.md)
concerns a different saved patch and unchanged grading, not this candidate.

## Execution and claim boundaries

All paid allocations are closed. The earlier
[interrupted normal task8](history/2026-11-01-condition-normal-task8-results.md) fourth
response still has UNKNOWN usage. Older unresolved billing, including the
[interrupted expectation review](history/2026-09-28-expectation-review-results.md)
and [focused diagnostic history](history/2026-10-30-sqlfluff-deadline-review.md),
is not reconciled by this batch's known generation usage. Invoice and input-count
endpoint billing have not been independently verified.

Fresh solves, seeded repairs, saved-patch evaluations, operator public comparisons
and scripted local tests are distinct evidence. All latest full20 submissions remain
unverified_delivery for registered original-case proof, independently of acceptance.
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
