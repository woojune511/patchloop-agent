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
is CLOSED: **11 independent PASS, 8 FAIL, 1 unsubmitted/NOT_RUN**. All 19 submitted
candidates have safety PASS; task 18 has safety NOT_RUN. Code at execution was
1ec9198a (solver 1569ec49), runtime
`sha256:06b0bbc8bd933616c7e40495a87bdaf76207db10f477263d98bbb6ab0cb8e866`.
All 20 were attempted once with two workers, USD4 each / USD80 invocation cap.
Cost **USD20.2818755**, 300 model calls, 472 actions, 30 accepted edits, 39 probes;
batch wall **5,513.593 seconds (91m54s)**. All 302 input counts and billing settled,
with no retry, uncertainty stop or extra independent evaluation. Unused allowance is closed.

Task 14 demonstrated the intended autonomous sequence: 1,380 tests PASS, a new
string-type counterexample exposed ValueError, production code plus an asserting
regression changed, then replay and independent acceptance passed. This is live
behavior evidence, not a causal estimate of guidance effectiveness.

Task 8 instead repaired a bytearray/array conversion while missing the upstream
setter for the original bytes path. After batch closure, an operator-only public
base/candidate comparison confirmed that OL bytes containing 0x5c still become
MultiValue and fail Dataset.save_as; normal OL and same-byte OB controls passed.
That is a confirmed residual public defect, with zero additional model/private
calls. It was not discovered by the solver and does not identify the private
failure's exact assertion. The submitted patch remains unchanged.

Task 18 reproduced the bug but spent 868.456 seconds from baseline observation to
first edit. Several helper API/configuration mistakes delayed useful evidence.
The first patch changed 9-space indentation to 5 instead of 8. A second production
edit was accepted, but its recheck had only 11.493514 seconds and timed out after
the last model decision consumed 96.600140 seconds of 117 remaining solver seconds.
Cleanup was confirmed; all usage settled. The last candidate is unverified and
unsubmitted, not an independent FAIL. Increasing the edit cap would not address
this deadline mechanism.

Six tasks (4,8,11,13,15,20) selected tests within an already-passing declared scope,
despite delivered PASS/reuse guidance. Actual previous collection is unreported;
this is declared overlap, not an execution-equivalence attestation. Task 6's new
file was outside its required file and needed the extra selection. No strict
unchanged-diff successful check/probe replay was identified. Task 10 replayed an
identical helper after a test-only diff change under whole-diff freshness rules.
Useful new controls and changed-source replays must not be counted as waste.

The [verification continuity correction](history/2026-10-31-verification-continuity.md)
now addresses two delivered-context gaps. Recent probes retain exact bound programs
through handoffs so their inputs/callers/assertions can be compared; finalization
keeps historical program identity without promoting old output to current evidence.
The latest rejected test proposal remains visible after successful source-only
recovery, with bounded exact text and explicit unapplied/unverified status. This
preserves task 10's proposed output-count assertion for review instead of discarding
it once mutation admission succeeds. Existing instructions already require fidelity;
the change supplies missing factual content rather than another general reminder.
Task 17's YAML rejection now names the Python-only restriction correctly. YAML
support and test-preservation policy are unchanged.

These changes establish delivery, not model uptake or improved repair accuracy.
Task 8's issue text was always visible; program omission is not a proven cause of
its missed path. Task 12's self-selected output semantics and task 18's diagnostic
delays remain unresolved. Bounded execution receipts for residual selection overlap
are still only a candidate. No further paid run is authorized or scheduled.

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
workers. Focused delivery controls stayed under two minutes. These are local
mechanism checks, not a new model run or repair-quality measurement.
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
and scripted local tests are distinct evidence. All 19 submissions above remain
unverified_delivery for registered original-case proof, independently of acceptance.
Never expose private evaluator bodies, hidden tests or reference patches to the
solver. Public PASS, successful delivery and safety PASS do not establish correctness.
No private evaluator bodies or raw provider reasoning were used in this public audit.

Do not start Docker Desktop or pull/build evaluator images automatically. Preserve
exact recovery identities, zero SDK retries and stop-all on count/transport/billing
or cleanup uncertainty. The current 20 tasks are development-exposed, not held out.
Repeated performance, general improvement and Linux CI remain unverified.
[History](history/README.md) indexes closed records; their approvals and next steps
do not carry forward.
