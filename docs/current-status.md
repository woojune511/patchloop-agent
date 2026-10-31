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

The [affected-family review](history/2026-10-31-affected-family-review.md) asks the
agent to derive affected members from public definitions/registries/callers/tests,
compare edited and verified members, and inspect relevant unverified cases while
preserving the public caller/input construction/outcome assertion. Existing adequate
results are reused. This is guidance in the existing post-edit decision, not
automatic family extraction, a new tool/state/required check or a finish gate.

The [fresh task 8 run](history/2026-10-31-affected-family-task8-results.md) is CLOSED:
**independent FAIL / safety PASS**, required public check **213 PASS**. Solver code
was **60029805**, runtime
`sha256:dcc04d586ddb7554c3fc2c735577f6ca91676b0dcb0b5ca172d53a0b0c6acaa7`.
One pristine attempt used GPT-5.4/xhigh, one worker and the baseline limits under a
new USD4 cap. Cost **USD0.921602**, batch wall **475.843 seconds (7m56s)**,
12 model calls, 18 actions, one accepted edit and two probes. All counts/calls
settled; no retry, uncertainty stop or extra independent evaluation.

**Public family information was acquired and retained, but did not become missing
cases after review.** Before editing, the agent read writer registrations and an
existing parameter list; their union includes all seven types added to its patch.
The source spans, exact helper program and new review were still delivered after
the edit and at completion. There is no observed source/program delivery loss.
Initial patch breadth precedes the new review, so it cannot be attributed to that
review's delivery. No explicit complete-family/coverage comparison is established.

The first helper found that bytes controls for OB/OF/OL already worked, while raw
OL array input became MultiValue and failed. The agent preserved buffer values for
seven types and added an exact-encoding assertion for raw OL array input. After
review it ran the public check, replayed the same helper on the changed diff and
finished; no new family cases, source reads or second repair followed. This replay
was useful repair verification, not redundant unchanged-diff repetition.

The reporter's array('H') -> bytes -> sequence/add_new -> save_as path differs from
the helper's raw array('I') and lower-level writer. The final assessment explicitly
left the mapping unverified. Registered original-case executions remain zero and
delivery is unverified_delivery. Acquisition reached preparation_action_limit, but
ordinary tools and substantial whole-run resources remained. At completion input,
29 calls, 83 actions, 11 edits, USD3.238008 and about 1,108 solver seconds were left.

The requested discovery -> missing-case execution -> further repair behavior was
not demonstrated. The active question is why available public scope did not become
unverified member/input cases before finish. Existing coverage may have been
misjudged or the helper fix treated as sufficient; the public trace does not settle
that explanation. More reminders or budget are not supported by this result alone.
No further runtime edit or paid run is scheduled. The new private evaluator body
was not read; an earlier patch's private failure is not evidence of this one's exact
failure. One development-exposed attempt establishes no causal repair or speed gain.

The implementation's local checks remain **66 focused PASS in 21.10 seconds**,
**1,363 quick PASS / 1 host-symlink SKIP**, isolated mock and Ruff; quick wall was
310.94 seconds with four workers. The live record separately validates **82/82**
metadata/settlement/patch-identity checks. These are different evidence layers.

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
