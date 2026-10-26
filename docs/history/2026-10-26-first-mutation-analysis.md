# First-mutation stall: unresolved evidence and repeated no-action generation

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent.
- Origin Mode: validate; Origin Date: 2026-10-26.
- Verification Status: **ANALYZED**, saved public evidence and static source review.
- Version Label: `first-mutation-analysis-v1`; `official=false`, `claim_eligible=false`.
- Source run: `run_dev_65272138acea4650`; [closed result](2026-10-26-diagnosis-stage-live.md).
- Runtime: `9e8c953feb4b638018c3f2e4202943fe8a14e4c3`, source hash
  `sha256:f37a81117ad7fe0cd87005aa062f2d994ce213cbac9661b745ad9188b77967ac`.
- Documentation baseline: `121082bcb23ddfddcbb3f181c63cb8a894d8ff3f`.

## Question and scope

The pilot acquired F0010 immediately but made no first mutation. This blocked the
new post-mutation diagnosis stage and cost $1.078465800 without a repair. The user
asked why inspection failed to become a mutation and why both ordinary and correction
responses exhausted output without a tool call. This analysis examines the original
public receipts, delivered source/notes/plan, exact request schemas and resource code.
It does not reopen the paid allocation or modify runtime behavior.

Two native peer reviews covered policy and public hypothesis evidence respectively;
the parent independently checked delivered contracts, request hashes and budget
arithmetic. These are shared-context code/evidence reviews, not blinded or cross-model
causal experiments. No private evaluator, reference patch or provider reasoning text
was read. Additional provider calls and target executions were both zero.

## Confirmed sequence

| Stage | Evidence |
| --- | --- |
| Call 1 | Original F0010 acquired with consistent host/authored judgment |
| Calls 3-29 | replace_text available throughout; model continued inspection |
| Inspection | 27 read/search actions; 25 added newly covered source lines, two isolated zero-gain actions |
| Call 28 | Helper's directory and file inputs both produced caught ImportError |
| Call 29 | Model recorded helper as inconclusive, then used the last inspection opportunity to read tests |
| Call 30 | Exploration closed by protected model-call horizon; replace_text and stop_task remained |
| Calls 30/31 | 30,704 and 25,000 output tokens; reasoning-only incomplete responses, no function call |

The two no-action responses each returned HTTP 200 with response status incomplete,
reason max_output_tokens, output_item_types=[reasoning], tool_calls=[] and
tool_contract_failure=null. SDK/HTTP diagnostic fields matched. There was no
generated mutation request for the host to reject, nor a parser, transport, billing
or sandbox failure at this point. The request had tool_choice=required, but no
function-call item was returned before the limit.

## Why exploration remained open without yielding a repair

The inspection accounting measures new public source coverage on the same diff,
not whether competing causal explanations have been separated. Of 27 inspections,
25 obtained new source lines. The two zero-gain inspections, calls 22 and 25, were
not consecutive. All repetition counts were 1, stagnation_signal was false, and
commitment_action_state stayed inactive. Even an activated commitment is advisory.
The model's inspection_intent records its question; the host does not establish that
the returned source answered it. See `patchloop/dev/tools.py:1124,1307,1427` and
`patchloop/dev/runner.py:1511,3686`.

This was therefore not a mechanical ban on early editing. replace_text was offered
from call 3. The accounting allowed distinct nearby reads to continue, while the
model's public notes still contained a conditional causal hypothesis. New lines
are genuine observations, but do not certify progress toward a specific edit.

The final notes did narrow the leading candidate to `modpath_from_file_with_callback`.
They did not settle an exact condition/return value/change with a discriminating
observation. The plan still asked whether misclassification occurred in module-path
discovery or the manager's directory-to-module fallback. Notes also retained the
conditional possibility that discovery allows the directory and import-spec handling
then treats it as a package. This is more specific than having no hypothesis, but
less than an observed failing path and a supported minimal replacement.

The helper did not resolve that distinction. It created an absolute temporary
fixture outside every lookup root, then called `modpath_from_file` for both the
directory and its file without supplying path= or putting the fixture on sys.path.
Delivered `astroid/modutils.py:274-305,308-323` shows this can fail before the package
callback being investigated. Both calls printed "Unable to find module" ImportError;
the helper caught the exceptions, so the process returned PASS. It did not reproduce
the original linter's full calling setup or supply a successful contrast.
The original entry snapshot also lacked the fixture in sys.path; the linter's
internal path preparation was not observed. This diagnoses the helper comparison,
not the root cause of F0010 itself.

The model recognized that limitation in call 29's public note n3: the fixture was
not on sys.path and the helper was inconclusive. It nevertheless chose a read of
`tests/unittest_modutils.py` while run_probe was still offered. No corrected helper
or original-call path trace followed. This was not another NameError or a broken
helper API; it was a diagnostic design that failed to isolate the intended behavior.

## Why the host then narrowed the choice to edit or stop

Call 29 explicitly exposed one inspection turn remaining. At call 30 there were
11 physical model calls left. Reserving one protocol correction left 10, exactly
the protected completion/recovery forecast, so discretionary inspection slack was
zero. Available anchor evidence meant the exception for a necessary anchor read
did not apply. `patchloop/dev/runner.py:859,958,1016,1171` owns these decisions.

The minimum path was three model calls: edit, required check, finish. The protected
path was ten: the minimum three, mutation-retry allowance two, original-failure
recovery three and an earlier possible check-failure recovery two. The ordinary
check-only alternative was seven, so the forecast took max(7,10). The separate
protocol correction was outside this ten. See `patchloop/dev/completion_budget.py:65-126`.
Diagnosis/preparation/request-correction terms were all zero at this stage.

The cost forecast funded five minimal calls; it would still fund a read plus the
three-call minimum successor. Thus dollar affordability was not the direct reason
inspection closed. The protected physical model-call horizon closed it first.
Cost and physical-call forecasts protect different paths and should not be conflated.

The last states still supplied `mutation_readiness=ready_to_attempt`, four edit
slots, and source anchors. In particular, `modutils.py:229-674` and
`manager.py:80-260` were retained, with no omitted pinned ranges. The observed problem
was not loss of these source anchors. This does not establish complete source context:
23,974 of 24,000 source characters were retained, and builder.py ranges 22-143 and
150-260 were omitted. Here ready_to_attempt means an edit can be admitted against
observed code; it does not mean the causal repair is known.

## Why the correction did not change the problem to solve

Both last calls used the same ordinary tool schemas. The compact JSON schema for
replace_text was 7,063 characters, of which its turn_decision property was 5,173.
Alongside exact path/old_text/new_text/occurrence, hypothesis and expected behavior,
the model still saw the general decision, notes and plan contract. Only the separate
post-mutation diagnosis stage had the new focus-only schema. Nullable memory/plan
fields could remain null; these schema sizes are not mandatory response lengths.
They show residual contract complexity, not proof that schema complexity caused
the no-action response.

The public source, notes, plan, probe summaries, reproduction review, task and
mutation_readiness were byte/value-equivalent across calls 30 and 31. The correction
message was delivered in the recent protocol attempt: return a valid call and use
replace_text for a supported repair or stop_task to abandon. There was no malformed
field to correct, no new execution evidence, and no smaller first-mutation contract.
Source, hypothesis selection and ordinary call construction therefore remained the
same unresolved work for the correction.

Call 30 itself began a fresh ordinary segment after the helper follow-up. Call 31
began another fresh segment because the preceding encrypted item exceeded its bound;
the recorded reason was encrypted_item_bytes. Its prior reasoning was unavailable,
while the public evidence persisted. The correction was a fresh generation from
the same public facts, not continuation of call 30's unfinished reasoning. Restart
may have increased repeated work, but its causal contribution is unmeasured.
Raising this bound alone would not add diagnostic evidence or simplify the contract.

## Output and cost were accounted for as configured

| Call | Actual input | Admitted output | Output reported as reasoning | Tool calls |
| --- | ---: | ---: | ---: | ---: |
| 30, ordinary | 25,877 | 30,704 | 30,704 | 0 |
| 31, correction | 25,596 | 25,000 | 25,000 | 0 |

The configured 40,000 was an upper bound. Before call 30, $0.406227750 remained;
the input reserve was $0.019407750 and future reserve $0.248652000. At the frozen
output price, the remainder funds exactly 30,704 tokens. The prepared artifact's
40,000 is replaced by the admitted ceiling before dispatch. Applying that replacement
reconstructs the actual recorded request hash, including the same tools and input.
See `patchloop/dev/runner.py:5745-5807` and `patchloop/dev/cost.py:175-205`.

The correction received all 25,000 reserved output tokens. The final two calls cost
$0.284693550; $0.121534200 remained when the second incomplete response stopped the
run. Neither input approached 60,000. This excludes absent correction funding and
input-limit termination as direct explanations. It does not show that reservations
were optimal or that more output would have returned a valid repair.

## Interpretation, alternatives and next question

The strongest supported account is a mismatch between *having observed editable
source* and *having distinguished a first repair hypothesis*. Exploration generated
coverage but the late helper was inconclusive. The resource boundary then removed
further evidence collection, leaving a full ordinary mutation or stop decision.
The correction supplied more output for essentially the same unresolved decision.

This is a structural account from public observations, not a reconstruction of model
thought. Unresolved causal localization, ordinary action-construction burden, and
fresh-segment regeneration are plausible contributors. Their relative causal weight
is not identified. A concrete, evidence-backed replacement in the last public notes
would weaken the first explanation; a smaller schema alone succeeding on the same
frozen state would support the second; continuation with unchanged public evidence
would test the third. None of those comparisons was run here.

The new diagnosis stage requires a successful implementation mutation and then an
unchanged original failure with unobserved changed lines (`repair_path.py:66` and
`diagnosis_request.py:110`). With zero mutations, it could not help locate the first
repair. Its effectiveness remains NOT_EXERCISED.

The next useful design question is a bounded original-caller observation before the
first edit when the leading hypothesis remains unresolved, followed by a control
that actually reaches the intended branch. Separately, test whether the ordinary
mutation/no-action correction can use a smaller action contract while preserving
host-owned source and completion checks. Keep these as distinguishable interventions;
additional broad reads or larger limits alone do not address the observed evidence gap.
No implementation change, paid rerun or continuation is authorized by this analysis.

## Validation and evidence

The audit checked 11/11 statistical-fallacy categories for applicability. There are
no p-values or population effect estimates. Relevant cautions are failure-case
selection, historical stochastic comparisons, post-hoc causal attribution and reverse
direction between unresolved reasoning and resource depletion. All failed calls were
retained; unrelated categories are marked N/A in the machine-readable report.

Artifacts: `C:/pt/first-mutation-analysis-v1/analysis.json`, its reproducible
read-only extractor `analyze.py`, and external hash-chained dev-run-v1 journal.
Analysis hash: `sha256:76b12ae7a6ae5dd10ef7d9a1ec3f2e140d5107b6575dff99944b5224e7b86b64`.
The extractor verifies source identities, reconstructs dispatch hashes and asserts
inspection totals, identical correction components and cost arithmetic. Its initial
attempt assumed every successful response had optional HTTP diagnostics; that reader
assumption was corrected before the completed report. The live run was not retried.

Final documentation checks, unchanged prior-run hashes and documentation commit are
recorded in `closeout.json`. No runtime code changed; no full runtime suite or target
reproduction was run. Closed historical records and unrelated working-tree changes
remain preserved.
