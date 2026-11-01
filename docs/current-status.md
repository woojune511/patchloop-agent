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

The [latest failed-eight rerun](history/2026-11-01-failed8-rerun-results.md) is CLOSED.
Code 062dde2e ran tasks 7/8/10/12/13/16/17/19 once each: **task13 independent PASS,
seven FAIL, eight safety PASS**, all submitted. Against the same failed rows from
the [previous full20](history/2026-11-01-pre-edit-dev20-results.md), only task13
changed to PASS. Recorded generation cost is **USD10.8253535**, batch wall
**2,277.183 seconds (37m57s)**, 121 model calls and 124 input counts, all settled.
Actual dispatched public inputs, costs and artifact/journal hashes were verified.
The new USD32 allocation and unused USD21.1746465 are closed. There was no retry,
extra evaluation, runtime edit or operator hint during the run.

Task13 preserved the reported parent initializer and relative search path, reproduced
F0010 through pylint, then repaired path normalization. Its first edit exposed an
existing symlink regression; the second repaired production code while preserving
the new test. Public recheck reached 1,232 PASS, the caller probe stopped emitting
F0010, and independent evaluation passed. This supports that repair trajectory.
The eight baseline rows cost USD10.2215815 with 122 calls; the new panel does not
establish efficiency gains or a one-feature causal effect. Twelve prior passes
were omitted, so it is not a full20 regression/generalization result.

The [filename and expectation corrections](history/2026-11-01-failed8-and-test-discovery.md)
remain implemented. Known mismatched new pytest names reject the atomic edit before
writing, with public config/hash/patterns; unknown configuration is not guessed.
Scope review separates required `outcome` and `public_basis`, while post-edit guidance
compares original conditions and relevant controls. No extra model step, mandatory
probe or finish gate was added. Local validation remains 88 focused PASS in 20.65s,
1,494 quick PASS/one host skip across corrected runs, Ruff/docs and isolated mock PASS.

Live uptake is narrower than correctness: 37 scope-case occurrences used the new
structured expectation, but seven tasks still failed. Tasks10/19 created correctly
named new modules and explicitly executed them; no bad-name rejection occurred.
Naming/selection do not prove ordinary directory collection. Task17 recovered from
YAML and duplicate-file edit rejections; task19 corrected a failing test setup.
No identical same-diff AST/selection repeat was found, which does not exclude
semantic repetition or overlapping test coverage. Private failing assertions were
not inspected in this rerun analysis.

The [completion-reserve clarification](history/2026-11-01-completion-reserve-clarity.md)
addresses task8's one-call-stage explanation despite 32 calls, 31 exploration calls,
1,209 solver seconds and USD3.504356 remaining, with probes and edits offered.
The model view now groups minimum and bounded-recovery requirements under
`completion_reserve`, explicitly distinct from `remaining_budget` and offered tools.
Canonical accounting, admission, limits, recovery and finish eligibility are unchanged.
Local request controls and the saved public budget projection verify the distinction;
152 focused and 1,504 fast-suite tests pass, with one host symlink skip; Ruff and
isolated mock evaluation pass.

The [fresh task8 follow-up](history/2026-11-01-completion-reserve-task8-results.md)
at a1833855 is CLOSED: **independent FAIL, safety PASS**, USD1.797247, 16 model calls,
23 actions and 786.524 seconds. All 16 dispatched inputs carry the new reserve and
match the frozen projection; counts and usage are settled. At reserve one / 30 calls
left it chose a probe, then further reads, a new writer test, recheck and helper
replay. The final submission at 25 calls left cited low expected information value
and the missing original reproduction, not a one-call cap. The baseline already
used one probe before its mistaken final explanation; more work alone is not gain.

The base OL-bytes approximation already wrote successfully. Later checks addressed
array/bytearray inputs; the original failure-to-repair transition remains unverified.
Public checks rose from 212 to 213 PASS, with the writer file explicitly selected;
the original broad-check stdout lacked exact node telemetry. The new USD4 allocation
and unused USD2.202753 are closed; no further paid work is scheduled.

The [provider-free paired test](history/2026-11-01-task8-public-test-comparison.md)
uses the unchanged submitted regression on base and candidate. Each collects one
node: **base assertion FAIL, candidate PASS**, with setup/teardown PASS, complete
output and identical test bytes. Base stops at the first bytearray input's bytes-type
assertion; later base writer/array outcomes were not observed. The 20.171s comparison
confirms that case's patch effect, not its mapping to the reported bytes failure or
the public basis for its expectation. Prior bytes evidence was reused. There were
zero model calls or independent evaluations, and runtime/source remained unchanged.
The next question is repair selection after the base approximation succeeds and
the judgment that further original-case discrimination is unhelpful. Keep the
clarification and existing comparison tool; no cap increase or new finish gate.
Autonomous comparison uptake, field causality and the private FAIL's exact cause
remain unestablished.

Keep [repair-plan delivery](history/2026-11-01-repair-planning-continuity.md),
[input correspondence](history/2026-11-01-pre-edit-task-correspondence.md), and
[capability-aligned review](history/2026-11-01-capability-aligned-verification-review.md).
The [task18 continuity run](history/2026-11-01-repair-continuity-task18-results.md)
remains separate closed evidence: independent/safety PASS, retained L039 finding,
one repeated base probe and a misnamed new test that motivated filename admission.
Do not equate missing registered original replay with failure: task13 independently
passed while the separate `unverified_delivery` label remained. Public PASS,
independent acceptance, valid receipts and semantic correctness stay distinct.

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
