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

The [causal-link task8 run](history/2026-11-01-causal-link-task8-results.md) is CLOSED.
Code 9b2e2a73 ran fresh dev-train task8 (pydicom1413) once without old patches,
helpers, notes or counterexample hints: **independent FAIL, safety PASS**, public
213 PASS, 11 model calls, 16 actions, one edit, USD0.8620045, 393.872 task seconds.
All 11 input counts and generation calls are settled and actual public inputs match
the frozen projection. The new USD4 allocation and unused USD3.1379955 are closed;
there was no retry, extra evaluation, runtime edit or operator hint during execution.

The [guidance change](history/2026-11-01-causal-link-repair-guidance.md) is implemented:
existing hypothesis links public caller/input/setup -> cause precondition -> wrong
result; unexplained intermediate states direct existing reads/searches to their
producing step. expected_behavior preserves representation/caller while comparing
a source-supported discriminating case and normal control. No new fields, gates,
tools, required probe, model step or resource increase. Source evidence still permits
direct repair. Local validation: 54 focused PASS in 19.089s; 1,508 quick PASS/one
host skip across the full run and corrected description-pin rerun; seven schemas
match prior bytes after restoring only the two intended descriptions. Ruff and
isolated mock EVALUATOR_PASS (safety NOT_RUN) passed. These establish compatibility.

Live delivery was verified in pre-edit calls 1-8 and mutation schemas in calls 2-11,
but autonomous original-path discovery did not occur. The agent read conversion and
writer code, not the earlier value setter. Its plan generalized the report's
serialized bytes to bytes-like input, then adopted direct array/bytearray helper
failures for both OL and OB as the repair target. That leaves the report's OL-only
failure / OB-and-OF success unexplained. Ordinary bytes already passed on base.
The patch repaired the helper; replay on the changed diff succeeded. Finish called
that helper sufficient while acknowledging missing bound original verification.
The final input still offered further reads/searches/probes/edits and showed 30
remaining calls, 1,104 solver seconds and USD3.211710: exhaustion did not force it.

Decision: wording delivery alone did not change target selection in this attempt.
Do not claim quality or efficiency gain from fewer calls or lower cost. Next question
is where a public requirement becomes a broader repair target and why contradictory
conditions are treated as a formal verification gap instead of a reason to inspect
another producing step. Do not prescribe another reminder, gate, memory layer or
cap increase without evidence. No additional paid run is scheduled. One selected
stochastic failure does not establish an inherent reasoning ceiling or a universal
rejection of the change. The new private failing assertions were not inspected.

The [previous task8 run](history/2026-11-01-completion-reserve-task8-results.md)
remains closed: independent FAIL/safety PASS, USD1.797247, 16 calls, 786.524s.
Its [added-test comparison](history/2026-11-01-task8-public-test-comparison.md)
proved a buffer repair only. The [bytes/caller comparison](history/2026-11-01-task8-bytes-call-path.md)
preserved serialized bytes and sequence-item add_new -> parent save_as, finding
OL failure on base and that earlier submission when one payload byte was 0x5c.
The latest submission still leaves that setter before its patched conversion;
source inspection predicts the same early transformation remains. The operator did
not execute a new counterexample on this latest patch. This is not exact private
assertion attribution, and the reporter's complete data/setup remain unavailable.

Keep [completion-reserve clarity](history/2026-11-01-completion-reserve-clarity.md),
[repair-plan delivery](history/2026-11-01-repair-planning-continuity.md),
[capability-aligned review](history/2026-11-01-capability-aligned-verification-review.md),
and [test filename/expectation corrections](history/2026-11-01-failed8-and-test-discovery.md).
The [failed-eight rerun](history/2026-11-01-failed8-rerun-results.md) remains CLOSED:
task13 independent PASS, seven FAIL, eight safety PASS, USD10.8253535; only task13
changed from its prior failure. The omitted twelve passes prevent a full20 regression
claim. The [task18 continuity run](history/2026-11-01-repair-continuity-task18-results.md)
remains separate independent/safety PASS evidence with retained findings and one
repeated base probe. All allocations and unused amounts remain closed.

Do not equate missing registered original replay with failure: task13 independently
passed while retaining unverified_delivery. Public PASS, independent acceptance,
valid receipts and semantic correctness stay distinct.

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

The latest SQLFluff16 candidate passed its public subset and observed non-crashing
`;;` plus a single-semicolon control, then failed independent evaluation. Broader
grammar behavior remains unresolved by those observations. The public report alone
does not settle every parser contract. Do not import private expectations into public
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
