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

The [two-probe allocation diagnostic](history/2026-11-01-two-probe-recovery-results.md)
is CLOSED on f927b04c. Same task8/pydicom1413 public post-probe sequence38/ancestor138,
fixed be082f27, gpt-5.4-2026-03-05/xhigh; only the new probe cap1->2 and time265->600s
changed. USD1.5431895, four model calls, ten actions,60k input/full25k reservation
and all agent guidance/tool policies remained. The prior failed program and UID
correction were excluded. This was public reconstruction, not exact native resume.

Observed: REPORT_RECORDED/no_counterexample_found, two model/count calls, one new
probe and one report,145.441s, USD0.2787685 recorded generation usage (USD0.3818725
cache-neutral). The new helper actually ran save_as for six cases: OL array/OL
bytes/UL list crossed with implicit/explicit little-endian. Encoded-byte assertions
passed; four OL cases also passed read-back and array/bytes output equality.
Saved same-patch write_dataset evidence was referenced, not rerun.

The helper worked on its first try. Setup correction and a second probe were not
exercised. Actual one-probe/145.441s usage fits the former1/265 limits, so neither
a causal budget benefit nor live recovery is established. The earlier v1 run did
show a meaningful setup correction blocked by probe1; its remaining33.5s also did
not establish enough room for execution and reporting. Keep two probes/600s for
this small diagnostic as reasonable capacity for one correction; do not raise it
again or change normal dev defaults from this result.

The report's limited observations are supported. Its stopping rationale remains
weak: it identifies regression coverage as material, then argues that no further
check is needed to say no counterexample was found. That does not fully justify
omitting a potentially useful observation. Direct run_check was not offered; it
also gave no concrete probe alternative. This does not mean more testing was
mandatory. Original H-array/lineSeq setup was not reproduced exactly (the helper
used an I-array and flat Dataset), the unchanged base was not tested, and public
regressions/independent acceptance remain unassessed. No candidate mutation.

All generation usage is known, no provider call is unresolved, cleanup is confirmed,
and count-endpoint billing/invoice remains UNVERIFIED. Unused USD1.264421 and all
prior allocations are closed. No retry, resume or extra sample is authorized.
Roots: C:/pt/stop-review-20261101-v2/ (preparation),
C:/pt/stop-review-run-20261101-v2/ (live),
C:/pt/stop-review-closure-20261101-v2/ (public audit and immutable closure).

The [resource preparation](history/2026-11-01-two-probe-recovery-preparation.md)
passed10 focused mock cases in25.40s, Ruff and6 docs checks. Only external allocation,
tests and docs changed; no redundant full quick rerun. The previous report-guidance
change retains27 focused PASS and1,437 quick PASS/one platform symlink skip including
isolated mock evaluation. The [report guidance](history/2026-11-01-goal-grounded-diagnostic-stopping.md)
asks for goal-grounded stopping without a new field, gate or mandatory probe.
Normal runtime remains
`sha256:4fdcc4fb9eb3d71ad81a5d929a0af689cecd876fbd39c212204d0c6343b608c7`.

Further work requires a concrete unresolved public requirement or stopping decision,
not just an unused probe. No new gate, additional prompt rule or paid run is selected.

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
