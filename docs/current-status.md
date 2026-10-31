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

[Capability-aligned verification decisions](history/2026-11-01-capability-aligned-verification-review.md)
addresses concrete mismatches found in the fixed-candidate diagnostic. The saved
current-state projection still carried normal edits/checks/submission instructions,
needs_visible_checks and run_check/automatic-recheck directions even though only
read/search/probe/report were offered. Saved replay/acquisition controls also looked
like current capability. An optional report annotation copied from read_file forced
inspect rather than terminal finish mode. These defects could distort the next
observation choice; a causal model effect is not yet demonstrated.

A shared diagnostics/discovery_review_context.py projector now aligns initial and
subsequent requests with the fixed-review capabilities. It preserves the public
task, current evidence and NOT_RUN facts while removing conflicting current control
instructions and distinguishing saved counters from new budget. Existing annotated
reports use finish/null evidence_goal; ordinary seven-field reports stay unchanged.
Projection is pure/idempotent and frozen seeds must already be projected. New saved
adapters must apply it after their last overlay and before freezing; old closed
requests/approvals are not silently upgraded or executable with changed code.

General tool basis and scope-review input/interpretation descriptions now connect
a remaining public condition to an actually offered observation and how its result
could change the decision. Preserve known original conditions and mark missing or
substituted setup; use concrete blockers or lack of relevance to justify stopping.
This reuses existing fields, limits and calls. No new semantic gate, required probe,
check backend, dependency installation, normal finish admission or budget change.
The normal runner's required public-check gate was not diagnosed as broken.

[Public-condition comparison](history/2026-11-01-public-input-comparison.md) now
separates fresh scope_review case input into public_conditions and case_conditions.
The former records known task caller/input/setup; the latter records what is
actually exercised or planned. Existing interpretation explains substitutions,
missing setup and evidence making a gap material or irrelevant. A plan's finish
condition is judged against the public task. Legacy strings remain unchanged;
null public conditions are allowed for unknown originals or separate controls.
This is bounded model-authored comparison, not verified correspondence. No new
tool, review call, mandatory probe, plan reset, semantic gate or paid run is added.

The [latest fixed-candidate diagnostic](history/2026-11-01-public-input-comparison-results.md)
is CLOSED on 0dfe7c6d: same task8 public seq38/be082f27, two model/count calls,
one source read, zero new probes, 232.128s and USD0.4385265 recorded generation.
It used four condition objects and disclosed direct-array versus bytes substitution,
but did not preserve the known H-array/bytes setup in public_conditions.

Its source read supports a local shared-writer inference, not full save_as/dcmwrite
equivalence. Relevant source was already delivered; no original-style execution
was added. Format uptake and clearer limitations are demonstrated, but verification
selection and evidence-sufficient stopping are not. Plan influence remains a
hypothesis. Do not infer invalid stopping from probe count alone or increase limits
when resources remained. Missing original setup and diagnostic capabilities also
limit what can be verified; see the linked audit. Original reproduction, registered
regressions and independent evaluation remain NOT_RUN. The separate two-probe
diagnostic was not supplied as evidence. Unused USD1.104663 is closed.

The [fresh normal task8 attempt](history/2026-11-01-condition-normal-task8-results.md)
on c855b0de was interrupted before mutation by InternalServerError; USD0.1686595
covers three settled responses and the fourth usage remains UNKNOWN. The user then
requested one retry. The [fresh retry](history/2026-11-01-condition-normal-task8-retry-results.md)
on 523e5da6 (same runtime) is CLOSED with independent acceptance PASS and safety
PASS: 10 model/count calls, 18 tools, one two-file edit, one public check (213 PASS),
one helper probe, 316.883 seconds and USD0.6997885 recorded generation usage.

The solver identified backslash splitting of binary bytes, added missing OD/OL/OV
VR exemptions and an OL save_as regression test. Its current-diff probe asserted
stored bytes and exact encoded OL output, with OF as a control. The post-edit
comparison schema and plan guidance were delivered and used. It still marked
OD/OV source-inferred, did not replay the original H-array/lineSeq setup on base
and candidate, and finished with those gaps disclosed. Original verification is
unverified_delivery despite acceptance PASS. No failing probe or second repair
occurred, so autonomous counterexample-driven revision is not demonstrated here.
One successful development-exposed solve does not isolate the review change's
effect or establish generalization. Retain the runtime without adding gates or
increasing limits on this evidence.

The new cap was USD3.3744305: original USD4 less prior settled USD0.1686595 and
the unknown call's conservative USD0.45691 reservation. The previous UNKNOWN
entry is unchanged; reservation is not actual billing. Both allocations are now
closed, including the retry's unused USD2.674642. Combined recorded generation is
USD0.868448 plus the earlier unknown call; invoice/count billing stays unverified.
No further paid invocation is authorized.

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

All paid allocations are closed. The fresh normal task8 fourth response has
unresolved usage. Older unresolved billing, including the
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
