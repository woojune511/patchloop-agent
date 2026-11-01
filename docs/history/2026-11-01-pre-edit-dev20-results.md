# Frozen full dev20 after pre-edit task correspondence

Date: 2026-11-01 KST. Status: CLOSED. All runs official=false, claim_eligible=false.

## Question, selection and decision

After the [single task8 PASS](2026-11-01-pre-edit-normal-task8-results.md), the user
accepted a frozen full20 run to find remaining correctness, verification and
completion failures. A successful selected example does not show that the agent
consistently chooses the right repair target across tasks. The pre-dispatch manifest
recorded the question, baseline, integrated intervention, fixed task selection,
resource limits, criteria and stop conditions.

All development-exposed current-dev20 tasks 1-20 ran once, in ascending order with
two workers. No midway runtime edits, retries, prior patches, diagnostic seeds,
earlier answers or counterexample hints were supplied. This exercises the integrated
agent; it is not a one-feature causal comparison.

**12 independent PASS, 8 FAIL, 20 safety PASS; all 20 submitted.** Task18 changed
from the [previous full20](2026-10-31-verification-reuse-dev20-results.md)'s
unsubmitted/NOT_RUN to PASS. The other 19 acceptance verdicts are unchanged.
No previously passing full20 task became FAIL. However, task8 did not reproduce
its immediately preceding single-task success on this same runtime.

Keep the runtime unchanged for this record. The next diagnostic question is how
obtained conclusions survive handoffs and guide the next action, using existing
run-local structures first. Task18 repeats provide a concrete efficiency case;
task8's unsupported helper-to-original correspondence remains a correctness case.
More probes or higher limits alone are not justified by this run.

## Frozen scope and preparation

- Execution HEAD: `f994a2b6885545391da8178c46b82e19c5390220`.
- Runtime implementation: `e6374d6fb481f0e94d2164cea5ac3177f78b3c03`.
- Runtime hash: `sha256:a1c2a5948d4cb0992f1cdecbe49e1af4a5566dae69145eab2d131f8d20213b20`.
- Manifest: `sha256:ff5dcbad4317131c18e61ce2802cbd0201b41d93ec7b64e81bdac38150884ea7`.
- Model `gpt-5.4-2026-03-05`, xhigh, 25,000 maximum output tokens, default service tier.
  Credential file `C:/Users/geonj/Documents/PatchLoop/.env`; no secret contents recorded.
- Fresh task1-20, once each, maximum two parallel. USD4 per task and USD80 total,
  no transfers. Limits: 40 model calls, 100 actions, 12 accepted edits, 1,800 seconds
  including the same 330-second evaluation reserve.
- segmented-v1, result-or-size-v1, brief-v1, current agent, probes enabled/none,
  probe-recheck none, repair-recheck, protected-v1, per-call-v1, public-checks-v1.
- Input counting before every dispatch, zero SDK retries. Count, transport, billing,
  continuation or cleanup uncertainty would stop new admissions; admitted work settles.
  Known task failure or resource exhaustion remains task-local.

All 20 source/task/dependency/image identities and public import/operation/selected-test
canaries passed before dispatch. Requests differ from the previous full20 only in
state_root. Task13 reuses the corrected existing pylint dependency descriptor;
no new dependency preparation, Docker startup or image pull/build occurred.
Preflight binds the exact unchanged runtime and its prior local validation.

[Official Standard pricing](https://developers.openai.com/api/docs/pricing) was
verified for this invocation: USD2.50 input, USD0.25 cached input, USD15 output per
million tokens. The 60K input limit is below the long-context tier boundary.
Closure recomputed every settled generation's cost from token counters and verified
its selected completed input count preceded dispatch.

## Results and resource accounting

| Measure | Previous full20 | Current full20 |
| --- | --- | --- |
| Independent acceptance | 11 PASS / 8 FAIL / 1 NOT_RUN | 12 PASS / 8 FAIL |
| Safety | 19 PASS / 1 NOT_RUN | 20 PASS |
| Recorded generation USD | 20.2818755 | 20.9727770 |
| Batch seconds | 5,513.593 | 4,916.317 |
| Model calls / input counts | 300 / 302 | 274 / 276 |
| Tool actions / accepted edits | 472 / 30 | 417 / 23 |
| Probes / required checks / selected-test actions | 39 / 30 / 7 | 50 / 22 / 8 |

The batch took **81m56s**, about 9m57s less than the prior batch, while recorded
generation cost increased by USD0.6909015. Preparation and the launcher's binding
revalidation are outside this batch measurement. Parallel row durations must not
be summed into wall time. Summed row duration is 9,759.695 seconds, of which
7,440.634 seconds (about 76.2%) is provider dispatch time. Lower calls/time and more
probes are descriptive observations, not a causal speed or correctness claim.

All 274 generations and 276 input counts settled; journal chains, selected count
identities, generation costs and all 20 submitted patch hashes verified. There was
no transport/count/billing/cleanup uncertainty, retry, batch stop or extra evaluation.
Allocation CLOSED: USD20.972777 recorded, USD59.027223 unused and closed. Invoice
and count-endpoint billing are not independently verified; earlier UNKNOWN calls
remain separate records.

Actions include harness rechecks. Edits are accepted mutations; task17 also had one
rejected mutation. Every row has safety PASS and delivery_state=unverified_delivery.
That delivery state concerns registered original-case proof, separately from grading.

| Task | Acceptance | Calls / actions | Edits / probes | Row seconds | USD |
| --- | --- | --- | --- | --- | --- |
| 1 marshmallow1343 | PASS | 14 / 23 | 1 / 3 | 480.750 | 1.0694115 |
| 2 pvlib1072 | PASS | 8 / 9 | 1 / 2 | 334.016 | 0.5366645 |
| 3 pvlib1154 | PASS | 14 / 14 | 1 / 1 | 398.761 | 0.7142600 |
| 4 pvlib1606 | PASS | 11 / 15 | 3 / 1 | 506.049 | 0.8706715 |
| 5 pvlib1707 | PASS | 6 / 7 | 1 / 1 | 479.712 | 0.6957885 |
| 6 pvlib1854 | PASS | 6 / 7 | 1 / 1 | 194.023 | 0.3376440 |
| 7 pydicom1139 | FAIL | 9 / 10 | 1 / 1 | 262.825 | 0.5349825 |
| 8 pydicom1413 | FAIL | 18 / 40 | 1 / 4 | 679.119 | 1.7084190 |
| 9 pydicom1694 | PASS | 12 / 15 | 1 / 3 | 323.655 | 0.7041760 |
| 10 pydicom901 | FAIL | 10 / 14 | 1 / 1 | 266.562 | 0.6099170 |
| 11 astroid1196 | PASS | 11 / 12 | 1 / 1 | 353.186 | 0.7066955 |
| 12 astroid1268 | FAIL | 9 / 19 | 1 / 1 | 264.284 | 0.6301715 |
| 13 astroid1333 | FAIL | 16 / 32 | 1 / 4 | 579.083 | 1.6082875 |
| 14 astroid1866 | PASS | 8 / 11 | 1 / 2 | 226.081 | 0.4414370 |
| 15 pyvista4315 | PASS | 11 / 12 | 1 / 2 | 421.718 | 0.7651950 |
| 16 sqlfluff1517 | FAIL | 28 / 41 | 1 / 9 | 1,104.816 | 2.8044820 |
| 17 sqlfluff1625 | FAIL | 16 / 28 | 1 / 1 | 564.631 | 1.1352050 |
| 18 sqlfluff1733 | PASS | 40 / 58 | 2 / 10 | 1,402.869 | 3.2595260 |
| 19 sqlfluff1763 | FAIL | 16 / 35 | 1 / 2 | 493.527 | 1.1901170 |
| 20 sqlfluff2419 | PASS | 11 / 15 | 1 / 0 | 424.028 | 0.6497260 |

## Public mechanisms observed

### Task8: delivered guidance did not prevent the repair target from drifting

The report supplies an H-array converted to bytes, then add_new/save_as, while
leaving indexData and lineSeq construction incomplete. Base probes used ordinary
I-array bytes: both direct writing and a constructed sequence/save_as path succeeded.
Those samples do not establish that all reported bytes inputs work. A later probe
found failures for direct array/bytearray inputs, a different representation.

At journal seq222, the actual public request contained the pre-edit instruction
to preserve input representation, connect changed helpers through source or comparable
execution, and investigate an unexplained transformation. Seq231 nevertheless
adopted a generic buffer-to-MultiValue hypothesis and modified _convert_value to
convert buffer-protocol inputs to bytes. Its new regression uses an OL bytearray
and a direct writer. The hypothesis does not explain how the report's already-bytes
value takes that failing branch. The original setter is unchanged in the submitted diff.

The fourth probe replayed the changed buffer case, and public required/selected tests
passed. Seq311 explicitly chose submission because helper/source evidence supported
that path and the exact original was unbound. It did not claim exact original proof,
but acknowledging the gap did not resolve the missing cause. It stopped after 18/40
calls, one/12 edits and USD1.708419, so resource exhaustion did not force this finish.

Independent acceptance is FAIL. The earlier same-runtime single run repaired the
bytes-splitting setter and passed. This contrast shows unstable target selection;
it does not isolate a prompt effect or prove a universal reasoning limitation.
No new operator counterexample or private assertion replay was performed here;
the precise independent failing assertion is not attributed by this public audit.

### Task18: regression repaired, with diagnostic repetition before the first edit

On the unchanged base, probe1 observed default CTE indentation 9 versus plain
SELECT 4, and L036-only indentation 0 for both. Probe2 observed L036-then-L003
CTE indentation 8. Probe4 separately confirmed the L003+L036 result. Later probes
printed richer lint/final-line details, but probes8/9 reopened the same central
L036-only and L036-then-L003 diagnostic questions. These were not retries of failed
setups: the first nine probe processes passed and no edit intervened.

The actual inputs preceding probes8/9 (seq461/476) retained probes5-7 and6-8,
respectively. The earlier discriminating probes were outside that three-probe list;
their distinctive output labels were absent from the filtered public request.
Findings, available note IDs and verification items were empty. The plan remained
revision1's generic inspect/edit/test route. Public action bases at seq466/481 again
described the L036/L003 distinction as the remaining ambiguity and requested those
observations. This is evidence of repeated decision questions alongside absent
explicit retained conclusions, not access to the model's internal reasoning.

The first edit changed L036 and added a CTE regression. Required check seq535
found one existing mixed-layout test failure (506 others passed). Seq569 narrowed
the source change to later targets on separate lines, preserving new and existing
test expectations; automatic recheck seq575 passed all 507 tests. A protocol
correction for a two-verification-action batch consumed one response, then a final
probe observed CTE8/plain4, and call40 submitted successfully. Independent PASS and
safety PASS followed within the original limits.

The working explanation is that diagnostic conclusions are not carried forward
reliably enough to prevent reopening answered questions. Intentional confirmation
and trajectory variation remain alternatives. Inspect how the existing plan/notes
capture settled questions and their evidence before adding state or increasing
budgets. If the conclusion is already delivered and correctly used when repetition
occurs, retention would be an insufficient intervention. Its benefit is not yet tested.

### Scope expansion and regression recovery are not universally absent

- Task4 added an equal-bounds regression, then its public check failed with scalar
  ZeroDivisionError. It changed source division to NumPy array/divide semantics;
  the test file stayed byte-identical after its initial addition. Public 258 PASS
  and independent PASS followed. Input/assertions were preserved during recovery.
- Task16 reproduced the public dropped-elements exception, then executed valid
  multi-statements, invalid-middle input, raw preservation and five direct grammar
  cases including strict whitespace and doubled delimiters. Two earlier probes
  could not load test fixtures inside the source-only probe snapshot; another
  control incorrectly demanded zero style violations. The agent later constructed
  self-contained segments and executed its branch assertions. Public 167 PASS
  still preceded independent FAIL. More scope was exercised, but self-authored
  expectations and final correctness are separate. No new private failure attribution.
- Task13 reached the actual public Pylint expand_modules caller and observed the
  synthetic initializer/missing-file behavior before repairing namespace resolution.
  That caller-stage check is narrower than full Pylint CLI behavior; acceptance FAIL
  does not by itself identify which remaining condition failed.
- Task17's additive YAML test attempt was rejected with the accurate Python-only
  contract message, rolled back, and followed by an accepted Python-test mutation.
  Public checks passed, independent evaluation failed. Contract recovery is not
  evidence of semantic correctness.

## Validation, limits and durable evidence

The run reused exact prior local runtime validation: focused 133 PASS, Ruff PASS,
quick 1,457 PASS/one host skip after six fingerprint rechecks, isolated mock PASS.
Only experiment documentation changed after execution. Documentation tests: 6 PASS
in 0.32 seconds. The external closure receipt binds validation and documentation;
runtime hash remains unchanged. No new runtime feature or additional paid execution
is included here.

This is one fresh attempt on each development-exposed task. Multiple integrated
changes separate the two full20 runs; outcome/time/cost differences are descriptive.
Task12's historical oracle ambiguity and older public/private criterion differences
remain separate questions, not newly established causes for these submissions.
Private evaluator bodies, hidden tests, reference patches and provider reasoning
were not inspected for this audit or supplied to the solver. Only evaluator verdict
summaries were joined to public action/source/check evidence.

External evidence is immutable or append-only; no prior record was rewritten:

- Preparation, scope and preflight: `C:/pt/pre-edit-dev20-20261101-v1/`.
  Includes manifest.json, approval.json, preflight.json, commands, canaries and pricing.
- Execution: `C:/pt/pre-edit-dev20-run-20261101-v1/result.json`, `summary.json`,
  per-task journals and artifacts, and `analysis/public-flow.json`.
- Closure: `C:/pt/pre-edit-dev20-closure-20261101-v1/metrics.json`,
  `public-focus.json`, submitted-1.diff through submitted-20.diff, validation/commit
  receipts and `runs/run_dev_preeditdev20closure.jsonl`.
- Public-flow artifact:
  `sha256:d9dab96eaaa7a5572e9057e253a8117ef1ccaad2123acaa03c4c4ce0a7f133a9`.
  Closure verifies manifest bindings, journal chains, accounting, request equivalence
  and submitted patch identity; it adds no model or target execution.
