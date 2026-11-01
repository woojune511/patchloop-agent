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

The active question is whether a repair explains the original public input path,
not only a helper with different inputs. The [latest task8 run](history/2026-11-01-completion-reserve-task8-results.md)
at a1833855 is CLOSED: independent FAIL, safety PASS, USD1.797247, 16 model calls,
23 actions and 786.524 seconds. It used the clarified remaining budget for further
checks, but repaired array/bytearray inputs without explaining the reported bytes
failure. Its USD4 allocation and unused USD2.202753 are closed.

The [unchanged added test](history/2026-11-01-task8-public-test-comparison.md)
failed on base and passed on the submission, establishing that buffer repair only.
The [bytes/caller follow-up](history/2026-11-01-task8-bytes-call-path.md) preserved
serialized bytes and sequence-item add_new -> parent save_as. One payload byte
changed to 0x5c made OL fail on both base and submission with MultiValue/TypeError;
ordinary OL and OB/OF controls passed. The setter splits bytes before the patched
conversion, which receives a list too late. This public reconstruction used no
provider call or independent evaluation; the reporter's complete setup is missing.
The exact private failing assertion remains uninspected for this submission.

The [causal-link guidance change](history/2026-11-01-causal-link-repair-guidance.md)
replaces the general correspondence reminder with a brief contrast in the existing
hypothesis: public caller/input/setup -> cause precondition -> wrong result, backed
by source/results and explicit gaps. If an intermediate state is unexplained,
existing reads/searches should locate its producing caller, assignment or conversion
before adopting a helper as the repair target. expected_behavior distinguishes a
source-supported discriminating case from a relevant normal control, retaining the
public representation and caller. There are no new fields, gates, tools, required
probe, model step or resource increase. Source evidence still permits direct repair.

Focused request-delivery controls pass: 54 tests in 19.089 seconds, including both
verification policies, context policies and agent policies. The quick suite reaches
1,508 PASS/one host skip across the original run and corrected description-pin
rerun. All seven pinned schemas match the prior bytes when only the two intended
descriptions are restored. Ruff passes; mock smoke reaches isolated EVALUATOR_PASS
(safety NOT_RUN). These establish compatibility, not autonomous discovery.

Next: freeze the validated code and prepare one fresh task8 solve with the same
model, policies and limits. No prior patch, helper, diagnostic output, notes or
counterexample hint enters solver context. Inspect actual source selection,
causal correspondence, executed discriminating checks, repair and independent result;
wording compliance or more probes alone is insufficient. A new positive cost cap
must be authorized after preflight; no new provider call has been made.

Keep [completion-reserve clarity](history/2026-11-01-completion-reserve-clarity.md),
[repair-plan delivery](history/2026-11-01-repair-planning-continuity.md),
[input correspondence](history/2026-11-01-pre-edit-task-correspondence.md),
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
