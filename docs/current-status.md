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

The next decision concerns diagnosis quality and continuity, not blanket budget
expansion or another generic instruction to test more:

- Task8 failed again despite the same runtime's
  [preceding single-task PASS](history/2026-11-01-pre-edit-normal-task8-results.md).
  Its actual pre-edit request contained the correspondence guidance. Ordinary bytes
  samples did not reproduce the issue; it then fixed array/bytearray helper inputs
  without explaining the report's bytes-to-MultiValue transformation. It submitted
  with resources remaining and acknowledged missing original-case evidence.
  Instruction delivery and gap disclosure did not ensure correct target selection.
  The exact independent failing assertion was not inspected in this batch.
- Task18 passed after fixing a public regression without weakening its tests, but
  took all 40 calls. It repeated L036-only and L036-then-L003 questions on the unchanged
  base. Before those repeats, the recent three-probe window no longer held earlier
  discriminating results; findings/verification notes were empty and the plan
  remained its generic initial revision. Investigate how existing run-local notes
  and plan carry conclusions and remaining questions across handoffs. Retention's
  repair benefit is unproven; this does not justify a new memory subsystem or gate.
- Task16 executed broader parser cases, including whitespace and invalid-middle
  branches, yet failed independent evaluation. Two earlier probes failed before
  target execution because test fixtures were absent from the probe snapshot.
  Scope expansion, valid setup, oracle correctness and acceptance remain distinct.
- Task4 and task18 repaired public-test failures while preserving expectations,
  then independently passed. These are behaviors, not a causal prompt-effect estimate.

Prioritize a focused diagnosis of repeated decision questions and missing retained
conclusions using existing structures; keep task8's public-input mismatch as a
correctness check on any intervention. No further runtime change or paid experiment
has been performed or authorized by this closed allocation.

[Pre-edit task correspondence](history/2026-11-01-pre-edit-task-correspondence.md)
uses existing hypothesis/expected_behavior fields to connect public input, caller
and setup to a repair. Changed helpers need source or comparable execution support;
unexplained transformations remain questions. Source evidence can support repair
without exact reproduction. No new fields, gate, mandatory probe or call. Local
validation: focused 133 PASS; quick 1,457 PASS/one host skip after six fingerprint
rechecks; isolated mock PASS. The full20 used that unchanged tested runtime.

[Public-condition comparison](history/2026-11-01-public-input-comparison.md)
separates known public_conditions from actual case_conditions. Interpretation
explains substitutions, missing setup and materiality. This is model-authored
comparison, not verified correspondence. Legacy strings remain compatible.
[Capability-aligned decisions](history/2026-11-01-capability-aligned-verification-review.md)
keep fixed-candidate diagnostics within offered read/search/probe/report capabilities;
the pure discovery_review_context projector runs after the last overlay. Closed
diagnostics cannot be upgraded into new repair/evaluation authority. The normal
runner's required public-check gate was not diagnosed as broken.

Task12's historical oracle ambiguity and public-versus-stronger-private expectations
remain separate questions. Earlier saved-patch audits do not establish exact failure
causes for fresh submissions. The [8/10 operator audit](history/2026-10-31-continuity-0810-failure-attribution.md)
did not change grading or create new public task requirements.

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
