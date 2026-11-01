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

[Requirement comparison continuity](history/2026-11-01-requirement-comparison-continuity.md)
is implemented and locally validated. A plan orders work toward the immutable public
issue; it cannot replace that requirement. Existing scope_review.public_conditions
now quotes the public issue literally and binds the issue/quote hashes. Invalid
paraphrases reject only the annotation. The latest bound helper remains review_needed
through null reviews and plan changes until a case links that execution and a public
quote. review_recorded is an unverified model interpretation, not semantic acceptance.
An exact replay on another diff retains its base/current results within the existing
three-probe limit, including bounded historical output in compact completion.
No new tool, model step, mandatory probe, finish gate or resource increase was added.
The combined brief prompt stays within its prior 11,164-character bound (11,123).

Local evidence: 96 focused PASS in 48.441s; 1,520 quick-manifest cases PASS and one
host skip across the full run and corrected focused rerun, including one added
retention integration case. Ruff and isolated mock EVALUATOR_PASS (safety NOT_RUN)
passed. Frozen task8 public prefixes keep the pending comparison in calls 7-11,
including after plan replacement, and the final replay references both observations.
That diagnostic recomputes state without new model/probe/evaluation execution.
It proves continuity, not autonomous use or repair improvement. No paid run occurred.

The motivating [causal-link task8 run](history/2026-11-01-causal-link-task8-results.md)
remains CLOSED: code 9b2e2a73, independent FAIL/safety PASS, public 213 PASS, 11 model
calls, 16 actions, one edit, USD0.8620045, 393.872 task seconds. Its USD4 allocation
and unused USD3.1379955 are closed. All counts/generation calls were settled and
actual public inputs matched the frozen projection; no retry or operator hint ran.
The [causal-link guidance](history/2026-11-01-causal-link-repair-guidance.md) reached
pre-edit inputs, but the agent broadened serialized bytes into bytes-like input and
adopted array/bytearray helper failures in both OL and OB. This did not explain the
report's OL-only failure with OB/OF success. The helper repair passed its replay;
the original failure condition remained undiscovered despite available resources.

The observed structural gap was that a valid next decision consumed the one-shot
review request without a recorded original/helper comparison; free paraphrases could
also describe the helper as the public requirement. The new local control retains
that comparison. It does not prove this gap caused the model's stopping decision.
Next unresolved question: does the model use the preserved discrepancy to inspect a
different cause, execute a discriminating case and repair the original behavior?
A quoted clause may still be incomplete and an execution interpretation may be wrong.
Do not add another semantic gate or claim a reasoning ceiling from this one failure.
No additional paid run is scheduled.

The [previous task8 run](history/2026-11-01-completion-reserve-task8-results.md),
[added-test comparison](history/2026-11-01-task8-public-test-comparison.md) and
[bytes/caller comparison](history/2026-11-01-task8-bytes-call-path.md) remain separate
evidence. The last reproduced a public bytes failure on base and that earlier patch;
the latest patch's remaining setter defect is source-predicted, not a new execution.
No new private failing assertion was inspected or supplied to the solver.

Keep [completion-reserve clarity](history/2026-11-01-completion-reserve-clarity.md),
[repair-plan delivery](history/2026-11-01-repair-planning-continuity.md),
[capability-aligned review](history/2026-11-01-capability-aligned-verification-review.md),
and [test filename/expectation corrections](history/2026-11-01-failed8-and-test-discovery.md).
The [failed-eight rerun](history/2026-11-01-failed8-rerun-results.md) remains CLOSED:
task13 independent PASS, seven FAIL, eight safety PASS, USD10.8253535. The omitted
twelve passes prevent a full20 regression claim. The [task18 continuity run](history/2026-11-01-repair-continuity-task18-results.md)
remains separate independent/safety PASS evidence with one repeated base probe.
All allocations and unused amounts remain closed. Missing original replay is not
automatic failure: task13 passed independently while retaining unverified_delivery.

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
