# Existing-run audit of segment boundaries

Analysis: 2026-10-16; closeout: 2026-10-17 (Asia/Seoul).
Offline public-evidence analysis; official=false,
claim_eligible=false. No live provider, Docker, probe, evaluator or solver execution;
existing focused tests exercised mocked runtime paths.

## Question and decision

The user asked whether the current segment boundary is appropriate, specifically
whether false hypotheses persist or needed information disappears. We inspected
saved model inputs, public decisions and results around actual boundaries. The
question matters because replacing native history at handoff can remove public
source evidence along with encrypted continuation, while a model-authored
interpretation remains in notes or plans.

The size guard works as a resource boundary. The result-triggered boundary is
not evidence of semantic review: it checks that a normal subsequent decision and
its tool batch finished. It neither establishes that a hypothesis was reconsidered
nor ensures that the active question's evidence survives. Actual source loss and
immediate reacquisition are demonstrated; unsupported interpretations also survive
fresh segments with zero encrypted reasoning. Their effect on final repair quality
is not isolated by these logs.

Preserve the runtime pending a better-supported intervention. These observations
do not justify globally earlier/later resets, retaining all reasoning, deleting
reasoning after every call, another wording-only comparison or a paid follow-up.
The specific next question is whether already-observed evidence cited by an active
question can survive handoff within the existing source budget, without displacing
more important current evidence. Notes' semantic validity remains a separate issue.

## Scope, identities and method

- Latest panel: all 20 journals under `C:/pt/plmini20live02`, bound by
  `C:/pt/plmini20prep02/manifest.json`; model `gpt-5.4-mini-2026-03-17`, xhigh,
  segmented-v1/result-or-size-v1, brief-v1, 24,000 retained source characters.
  These were existing exposed development runs, not a new sample or a test of
  the currently selected full-model baseline.
- Frozen core `fcfa496dfb57f7e0d79616e5389fac034cfbc6b2`, operator checkout
  `22d8217fba31b2d85dec086e6f634d8d02c94774`; audit HEAD
  `e589f881e2947075483f878496ab30e246d294b0`.
  Boundary, source-selection, delivery and notes code are unchanged. The full
  runtime diff is prompt text in model.py/working_plan.py preserving verification
  purpose; that later instruction was not retroactively present in the panel.
- Historical cases: SQLFluff row08 under `C:/pt/vcl06/08` and B1/B2 under
  `C:/pt/sretcl01/{1,2}`. Their boundary_reason and project_observed_sources
  function ASTs match current source; other runtime/resource conditions differ.
- Validate journal chains and artifact hashes, reconstruct delivered public
  content including native results, quoted exchanges, archived source arrays and
  current inline/reference source, then inspect the next declared action.
  Never decrypt or publish ciphertext. Final grades are descriptive metadata;
  no private evaluator content was opened.

Input event numbers below identify `model_input_prepared` receipts unless stated
otherwise. A prepared artifact wraps the request; `turn_started` stores its input
list. Fourteen selected prepared/dispatched input pairs matched exactly. A prepared
input above a limit can be replaced without ever reaching the model.

Competing explanations were retained: evidence can disappear at handoff, remain
visible but be misinterpreted, or be present while the model chooses more inspection.
Unchanged notes are not automatically false; absent source is not automatically
necessary. A pre-edit failure cannot directly falsify a later patch.

## Whole-panel observations

| Measure | Observed |
| --- | ---: |
| Original journals / actual generations | 20 / 285 |
| Saved turn_started inputs | 287; two later blocked by row cost caps |
| Initial segments / later handoffs | 20 / 75 |
| Handoff reasons | 66 major_result_reviewed, 7 input_tokens, 2 encrypted_item_bytes |
| First post-handoff input actually dispatched | 74/75 |
| Segments with at least one generation | 94 |
| Segments with exactly one generation | 56/94 |
| Minimum / median / maximum generations per nonempty segment | 1 / 1 / 22 |
| Maximum encrypted reasoning items in a dispatched input | 21 |
| Maximum counted input actually dispatched | 59,461 tokens |
| Same plan text across adjacent inputs around handoff | 38/75 |
| At least one identical note statement survives | 31/75 |
| Some previously delivered source line-version disappears | 46/75 |

All 75 constructed fresh inputs have zero encrypted reasoning items. These
counts describe transport and state, not harmful-loss rates. Source line-versions
include obsolete or irrelevant code; mutations between adjacent inputs can change
their identity. Note/plan persistence can be useful. The terminal, undispatched
row17 handoff has no subsequent model behavior to assess.

The current contract lets inspection continue for many calls before a major
result, while consecutive edits/checks can lead to one-call segments. The 56 short
segments and the 22-call initial astroid inspection show this asymmetry; they do
not estimate its quality effect. Result-trigger counts identify the recorded
trigger, not whether an unsegmented next request would also have hit a size limit.

## Cases grounded in exact delivered inputs

| Case | Public evidence | Interpretation |
| --- | --- | --- |
| Current row13, astroid-1333 | Prepared 287 has builder.py file_build/open_source_file; candidate 300 counts 60,609 tokens. Boundary 303 produces input 304 at 22,303 tokens, omitting builder lines 12-260. Decision 310 rereads 110-170; result 315 has zero new coverage. | Needed source genuinely disappears and is immediately reacquired. |
| Historical SQLFluff row08 | Input 393 includes L003 lines 406-799; result boundary 408 removes them from 409, including arithmetic at 706. Search 419 seeks that logic; subsequent reads miss 706. Input 491 restores the code, then the model submits. | Result handoff removes relevant prior evidence; final failure also includes later decision/verification choices. |
| Current row18, SQLFluff-1733 | After boundaries 204/220, original probe equals_expected=False and the regression failure remain. Plan 221 says the WITH/SELECT fix remains; decision 227 says the edit already fixes it, without post-edit target verification. | Unsupported confirmation survives through public plan/decision state. Not a proven falsification of the new patch. |
| Historical SQLFluff B1/B2 | Final inputs 509/526 contain zero reasoning, historical partial-path probe results and unresolved questions. Decisions 519/536 still treat old partial evidence or regression PASS as enough to submit. | Resetting reasoning does not prevent an unsupported interpretation when its public premises remain. |
| Current row20, SQLFluff-2419 | Candidate 233 counts 60,549; boundary 236/input 237 retains all observed source, with zero omitted lines. Source and two IFNULL/NVL description assertions survive later resets; public suite reports 836 passed. | Same policy can preserve necessary evidence and permit concrete verification. A boundary or another inspection is not itself evidence of harm. |

### Source eviction mechanism

Row13's last dispatched pre-boundary input 287 contains 21 encrypted items and
counts 59,461 tokens. Input 300 is an undispatched size candidate, not an additional
generation. Input 304 retains 23,948 of 24,000 source characters but only builder 1-11;
the function body is absent from every public input component. Note n1 still cites
builder 122-126 and asks about its missing-init path. A citation and short
interpretation survive while their code is unavailable. The next read's declared
purpose is to inspect that control flow. This establishes a continuity cost, not
that eviction caused the eventual wrong repair: 22 inspection calls had already
occurred, and the exact behavior was never probed afterward.

Historical row08 provides a separate result-triggered example. Delivered source
shrinks 42,859 to 24,124 characters across 393/409; the old L003 calculation survives
beforehand in archived public source, beyond the 24k selected current-source budget.
The reset removes this backup. Input 393 counted 50,260 tokens; that is a prior
request count, not a count of the hypothetical unsegmented next request.
The model later reads 1-250 and 330-430, missing the function body and arithmetic.
After regression PASS the source and optional tools return in 491, yet it finishes.
This weakens an explanation in which information loss alone caused submission.

### Public hypotheses outlive a reasoning reset

Row18's first probe runs only L003 and returns unchanged SQL/equals_expected=False.
It does not reproduce the full reported rule interaction. The later assertion that
the helper edit already fixes the target is unsupported, rather than disproved by
that pre-edit probe. Existing failure evidence remains in the inspected fresh
inputs; later BigQuery failures do lead to mechanism revisions. The run reaches
its cost cap unsubmitted and remains NOT_RUN, not a graded FAIL.

B1's final decision cites an old sequential-rule eight-space result as support for
its current full-pipeline repair. B2 declares no remaining public uncertainty
despite unresolved v1 requiring eight-space WITH verification. Historical labels,
exact partial-rule output and available probe tools remain. Saved later public
operator observations expose the missing L039/fix-loop interaction; the agent had
not seen those later observations. This supports an evidence-interpretation
failure, not a claim that the runtime should already have known the hidden cause.

## Assessment of the boundary criterion

`major_result_reviewed` means: a replace_text/run_check/run_tests/run_probe result
precedes a later normal decision, and that decision's batch completes. A read can
satisfy it; notes/plan updates and semantic reassessment are not required. The
old interpretation may therefore survive even as its detailed evidence disappears.
The contract's name must not be read as proof that the model understood the result.

The source selector uses structure and recency under a 24k budget, not demonstrated
relevance to the active hypothesis. A note's current status validates
cited-evidence currency, not its statement's truth. These two mechanisms explain
how loss and unsupported persistence can coexist without a transport-integrity defect.

The decision is to treat source continuity at handoff as an observed design
limitation, and hypothesis invalidation as a separate unresolved decision problem.
Preserving cited ranges is only a candidate: it can displace other useful source,
and previous file-recency/larger-retention work did not establish a general gain.
Neither changing the size threshold nor requiring another generic review follows
from these observations. No runtime implementation change was made.

## Verification and immutable evidence

Main evidence root: `C:/pt/analyses/segment-boundary-audit-20261016-v1`.
Use `summary-v2.json`, `rows-v2.json`, `turns-v2.json`, `boundaries-v2.json`,
`dispatch-reconciliation-v2.json`, `case-verification-v2.json`, and `closeout.json`.
The operator and its output identities are bound in new dev-run-v1 journals.

- Twenty current and three historical journal chains were checked. The root
  verification passed 17 independent case assertions plus 484 original-file hash
  rechecks. No original artifact or runtime source changed.
- Contract audit: 11 existing focused tests passed. A default temporary-directory
  permission error preceded a successful retry in a new external directory. Its
  saved verification record is a retrospective tool-output transcription, not a
  separately captured raw pytest log. Documentation tests are recorded at closeout.
- Initial parent verification attempts exposed request-wrapper/list differences
  and an omitted archived-sources path in the analysis operator. Attempts remain
  preserved. The corrected v2 aggregate includes archived public source arrays;
  its 46 loss-containing handoffs supersede the preliminary 44. Other aggregate
  counts and the manually checked case findings are unchanged.
- No full runtime suite or Docker smoke was necessary for this documentation-only
  result. No new live inference, input count, probe, solve or evaluation was performed.

Delegated evidence roots, each separate from the original execution artifacts:

- `C:/pt/analyses/segment-boundary-audit-20261016-current-cases-v1`:
  findings.md, evidence.json, dispatch-verification.json, verification-complete.json.
- `C:/pt/analyses/segment-boundary-audit-20261016-historical-v1`:
  findings.md, evidence.json, supplement.json and the new diagnostic journal.
- `C:/pt/analyses/segment-boundary-audit-20261016-contract-v1`:
  contract_report.json, source_identities.json, focused_validation.json, manifest.json.

Related prior records: [source/verification diagnosis](2026-10-06-verification-context-budget-diagnosis.md),
[public rule-interaction diagnosis](2026-10-07-public-verification-failure-diagnosis.md),
[latest panel](2026-10-16-patchloop-mini-dev20-results.md).
