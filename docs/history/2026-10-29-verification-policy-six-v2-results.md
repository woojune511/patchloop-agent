# Six-run submission-policy comparison: three accepted repairs, two failures, one stop

Status: LIVE_EXECUTED; allocation CLOSED. official=false, claim-ineligible.
Six authorized attempts completed once each; five reached isolated evaluation.
No retry, cap transfer, runtime change or extra target execution was performed.

## Question, authority and frozen conditions

The [v2 plan](2026-10-29-verification-policy-six-v2-plan.md) compares the existing
bounded reproduction policy A with public-check-based submission B. Both include
the same new observation correction. The intervention was selected because earlier
diagnostic failures blocked otherwise testable repairs; the alternative was that
easier submission would deliver more wrong patches. Acceptance, not submission
counts or diagnostic completeness, is the primary outcome.

The user explicitly approved the prepared v2 conditions, three tasks A/B once each
and USD27 total. Approval receipt: C:/pt/verification-policy-six-plan-v2/approval.json.
Command: & 'C:/pt/verification-policy-six-plan-v2/run.ps1'. Manifest:
sha256:5353179b8560416f0dc1ac7ca4b0859e6661a86284dfd132b7bff9f9a4dc0549.

Runtime content stayed at
sha256:db3e1e79a63f9091d1de51ebee32a5bc68df8a62409f5b1aa7247294bf414950,
implemented in 0e7d1c20627e647d42f07e4e6944a07f5ed75248 and sealed at docs commit
1a48653ca3507b0fe349a3a65b86b9198d223123. All 58 bound files remained unchanged.
The fresh sources, dependencies, model gpt-5.4-2026-03-05/xhigh and credential path
C:/Users/geonj/Documents/PatchLoop/.env matched the manifest.

Order was 5-A, 5-B, 9-A, 9-B, 18-A, 18-B. Per row: USD4.50, 20 responses including
at most one protocol correction, 40 tools, three accepted edits, context 60K,
output 40K/25K, 2,400 seconds including 390 for evaluation. No prior patches,
observations or operator counterexamples were injected. The pydicom public report
already includes a repair suggestion. No private evaluator contents were read for
this analysis or passed into solver context.

## Results

| Task/arm | Public regression | Isolated task acceptance | Safety | Model/tool/edit counts | Active seconds | USD |
| --- | --- | --- | --- | --- | --- | --- |
| pvlib-1707 A | 31 PASS | PASS | PASS | 11 / 15 / 2 | 566.257 | 1.014384 |
| pvlib-1707 B | 31 PASS | FAIL | PASS | 10 / 12 / 3 | 319.885 | 0.541741 |
| pydicom-1694 A | 26 PASS | PASS | PASS | 10 / 17 / 1 | 307.403 | 0.720366 |
| pydicom-1694 B | 26 PASS | PASS | PASS | 12 / 26 / 1 | 199.580 | 0.5556425 |
| SQLFluff-1733 A | 506 PASS | FAIL | PASS | 13 / 23 / 1 | 470.930 | 0.9777855 |
| SQLFluff-1733 B | NOT_RUN | NOT_RUN | NOT_RUN | 1 / 1 / 0 | 18.657 | 0.031122 |

A: two PASS, one FAIL; USD2.7125355. B: one PASS, one FAIL, one NOT_RUN;
USD1.1285055. Total: USD3.841041 of the USD27 ceiling, 57 model calls and
1,882.712 summed active seconds. Lower B cost includes an immediate stop and is not
quality-adjusted efficiency evidence. NOT_RUN is not a hidden-test failure.

All five edited candidates passed their required public checks and submitted
normally. Three were accepted by the unchanged isolated evaluator and two were not.
All five safety verdicts were PASS. All five submissions retained the diagnostic
label unverified_delivery; that label did not replace the benchmark verdict.

The executor returned exit0. All six provider/count/action/probe pairings were
complete, usage and accounting SETTLED, and hazards empty. Allocation CLOSED has
no unstarted row and no remaining repeat authorization. No row ended on a money,
time, response or output ceiling. No new image was pulled or built.

## What the public trajectory shows

**pvlib:** A's first probe lacked a complete observation; a second baseline probe
reproduced the declared failure. After the first edit, the original call changed
from high_aoi_output="nan" to 0.0 while zero_aoi_output stayed 1.0. Desired comparison
matched and declared failure mismatched. The hash-verified next model input
(turn prefix turn_dd1ee031, artifact prefix sha256:a88a502d) carried that replay action and both
comparisons. The first unhealthy case remained unverified, so aggregate delivery
remained unverified despite the later valid case and accepted repair.

B also observed NaNs in a model-selected helper; it did not blindly skip diagnosis.
A's public patch uses abs(aoi)>=90 directly and restores Series form. B uses a mask
derived from clipped cosd(aoi), with separate scalar/array output handling. These
conditions are not mathematically equivalent for all angles because cosine is
periodic. Existing nearby public source uses the direct angle guard. This is a
static public-source difference and possible coverage gap, not a verified cause
of the hidden acceptance failure. No extra target test was run to investigate it.

**pydicom:** A's two original observations remained incomplete and the bounded
acquisition stage released at its attempt limit; one edit still passed public and
isolated checks. B used two helper probes without an original declaration. Its
longer exploration was mostly productive: 19 of 21 read/search operations added new
covered lines, two searches added none, and no exact request repeated. The first
helper did not raise for b'2.0 '; subsequent inspection and a strict-validation
helper established ValueError for that input. It then made one accepted repair.
Optional diagnosis allowed useful investigation here, but this single pair does
not establish a general efficiency gain.

**SQLFluff A:** Initial original probes failed on string-path division and a module
setup mismatch, both before a comparable original observation. Later helpers ran,
but formal original evidence remained missing. It spent 11 responses through its
first edit, then passed 506 public tests, submitted and failed isolated acceptance.
The hidden failure cause was not inspected or diagnosed in this execution task.

**SQLFluff B:** The model selected stop_task in its first response, reason
no_safe_scoped_mutation, saying there was no edit tool. It performed no read,
search, probe, edit or check and had no evaluated candidate. The initial tool set
does temporarily omit replace_text until current editable source is observed;
the host guidance describes reading an allowed source file and reevaluating edit
availability. That transition explanation was absent from the actual dispatched
request: completion_guidance retained only stage/submission information, and
mutation_readiness retained needs_anchor_evidence with no current source paths.
The request offered read/search and had 14 exploration responses and 34 tool actions
available, with the full USD4.50 remaining and no resource rejection.

This is traced to the delivered small repair view: thin_policy.project_state removes
completion_guidance.next_action and message; the actual system prompt comes from
repair_context rather than DEV_SYSTEM_PROMPT and also lacks the read-to-edit
transition instruction. The existence of that instruction in the ordinary prompt
does not repair this specialized path.
The runner's explanation at runner.py:812 therefore does not establish delivery.
Actual request hash:
sha256:7cd67208c0a89b86fab814f54eb52871ded35d7d76b8d5f92f1232ba8220b962;
model input hash:
sha256:71eda401574fead3d39f05ce98ca77042cb732377e93d2953590c1f086bf97fc.
Turn turn_b0a05504cdca43dcabb6208ec8ce8c24 selected stop action
call_SWofh7XUgeBs7GnZ9JvF3y9a. The lost transition explanation is observed; that it
alone caused the model's stop remains a causal hypothesis. No larger cap was needed
to perform the available prerequisite read.

## Observation correction and decisions

Across all six attempts: eligible object-field mismatch opportunities 0, linked
correction attempts 0, successful supersessions 0. Correction is NOT_EXERCISED in
every row. Missing observations, helper/setup failures and call-observation
incompleteness are different conditions. They do not test the new narrow shape
correction. Because correction exists in both arms, this design also cannot isolate
its causal effect even if a later run exercises it.

The comparison does not support switching the default to B: B did not improve
acceptance on this panel, and neither lower spend nor public PASS suffices. Keep
the explicit experimental policy and the current default unchanged. This is not
a universal rejection of optional diagnosis: three exposed tasks, fixed A-first
order and one stochastic draw per cell cannot establish general superiority.

Next unresolved question: does preserving the read-to-edit prerequisite in the
actual thin request prevent this immediate stop under otherwise fixed conditions? Also
retain the independent problems of helper/setup usability and repair coverage.
Unused allocation alone is not a reason to rerun. No follow-up implementation or
new paid experiment was authorized by this result collection.

## Evidence and validation

Frozen plan and hash-chained preparation/approval/execution journal:
C:/pt/verification-policy-six-plan-v2. Append-only row journals and artifacts:
C:/pt/verification-policy-six-run-v2/{5-A,5-B,9-A,9-B,18-A,18-B}.
Run IDs respectively: run_dev_dfbae7d4967e498f, run_dev_9dac6e6a0bde4039,
run_dev_77b3f074f58f4bbd, run_dev_bafd68cdc2534fd2, run_dev_db96ae88d98845bb,
run_dev_c56d04b63a2b4ed1.

Batch receipt: C:/pt/verification-policy-six-run-v2/batch-collection.json.
Prepared collector output: C:/pt/verification-policy-six-run-v2/summary.json.
Post-run audit: C:/pt/verification-policy-six-run-v2/post-run-audit.json. It checks
bound/runtime identity, one batch start, six settled rows, cost sum and closed
allocation, and records the exact SQLFluff B request evidence. Preparation's six
first-input audits, 19 batch controls and 12 correction-metric controls are local mechanism evidence only.
Result documentation: five checks PASS in 0.38 seconds
(C:/pt/verification-policy-six-run-v2/result-documentation-tests.xml); whitespace
check PASS. Runtime tests were not repeated for this report because no runtime
behavior changed.
