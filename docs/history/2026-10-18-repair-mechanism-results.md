# Evidence retention and judgment support: fresh repair results

Date: 2026-10-18. Allocation **CLOSED**. All 12 authorized rows ran; no follow-up
spending, adoption, rollback or exposed-case tuning is authorized by this result.

Each of the four arms accepted the same two of three tasks. Registered and native
evaluation agreed on all ten submitted patches: eight PASS, two FAIL. Two Astroid
rows ended without submission and retain acceptance **NOT_RUN**. Every prespecified
acceptance contrast is zero. This panel establishes no repair-quality gain.

## Question and controlled scope

The [frozen protocol](../../.agent/plans/question-support-comparison.md) separates
focused evidence retention (E) from incremental interpretation/purpose guidance (J).
Earlier saved-input work changed evidence selection with operator-authored references;
earlier plan work did not establish repair gains. This experiment tested whether
either intervention helps autonomous repairs under the same limits. Competing
explanations included absent usable references, ordinary recency already preserving
the evidence, displaced counterevidence, and wrong judgments despite adequate input.

The user explicitly requested execution of the prepared specification. Authorization
and preflight are bound to the [readiness packet](2026-10-18-repair-mechanism-readiness.md).
The protocol's dated pre-authorization wording and all prior records remain unchanged;
this follow-up records the later authorization, execution and closure.

- Manifest: `C:/pt/analyses/repair-mechanisms-readiness-20261018-v1/execution-manifest.json`.
  SHA-256: `5d3304caf267cf01bccfbb86021def126a5af9b506a6a09932267654d6a2019b`.
- Operator checkout HEAD during execution: `5cc77b9b29042c966bfe1a5d1ae820522e410550`.
  All tracked bytes, including the user's pre-existing `AGENTS.md` edit, matched
  the before snapshot through public review and acceptance unblinding.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000 tokens,
  standard/global Responses, `store=false`, zero SDK retries. The normal runtime
  used the exact credential file `C:/Users/geonj/Documents/PatchLoop/.env`.
- Three development-exposed tasks, four arms, one fresh repetition per cell.
  No historical run enters these denominators. Fixed task order and single-row
  waves used each arm's own frozen interpreter; no forced questions or citations.
- USD 0.88 per row, 2.64 per arm, 3.52 per task, **10.56 invocation-wide**.
  No transfers, replacements, manual retries, resumes, continuations or paid judges.
- Unchanged `segmented-v1`, `result-or-size-v1`, `brief-v1`, two references,
  24,000 retained source characters, 60,000 counted input tokens, 1,048,576 request
  bytes and 262,144 encrypted-item bytes. Base/combined prompt maxima remained
  8,000/10,809 characters; all schema, note and admission bounds stayed fixed.
- Per row: 40 model calls, 100 actions, four accepted edits, 1,800 seconds including
  the 330-second registered-evaluation reserve. Existing pinned registered/native
  images and native harness were revalidated; none was pulled or built.

| Arm | E | J | Frozen commit |
| --- | --- | --- | --- |
| E0J0 | Off | Off | `33e95588a9fb204fd7a7635393004a38c026e3a8` |
| E1J0 | On | Off | `6c8e929a40f6de9d422ce87559ad968c83c91a24` |
| E0J1 | Off | On | `bd2125757b711ad7bfe3de1adf5779173de35a0d` |
| E1J1 | On | On | `116e970b6a51a7c921b278f60ccd39b5854b3037` |

E1J1 matches the common product runtime. E0 keeps the same observed candidates,
anchors, native result delivery and validity rules, but removes question-reference
priority and optional cited-result replay. J0 retains the existing unverified-data
warnings, concern persistence and plan history; it removes only the specified newer
interpretation presentation and purpose guidance. This is not an ablation of all
memory, all planning or all evidence handling.

## Repair outcomes and resources

PASS/FAIL below require agreeing registered/native results. NOT_RUN means no
submitted patch, not an inferred graded failure. Each cell represents one intended row.

| Task | E0J0 | E1J0 | E0J1 | E1J1 |
| --- | --- | --- | --- | --- |
| Astroid-1333 (13) | NOT_RUN: incomplete response | FAIL | NOT_RUN: completion limit | FAIL |
| Marshmallow-1343 (1) | PASS | PASS | PASS | PASS |
| Pydicom-1694 (9) | PASS | PASS | PASS | PASS |
| Accepted / intended | **2/3** | **2/3** | **2/3** | **2/3** |
| Submitted | 2/3 | 3/3 | 2/3 | 3/3 |
| Settled USD | 1.23786825 | 1.22824875 | 1.37192760 | 1.09780485 |

Both conditional E contrasts, both conditional J contrasts, their interaction and
the combined contrast are **zero accepted repairs**. No per-task acceptance changes.
The E-on rows submitted more Astroid patches, but both failed independent evaluation;
submission is not repair improvement. Cost differences are descriptive, not a reliable
efficiency estimate from one sample per cell.

| Row, in dispatch order | Calls | Latest required public check | Terminal | USD |
| --- | ---: | --- | --- | ---: |
| E0J0-r1-t13 | 36 | NOT_RUN | INCOMPLETE_RESPONSE | 0.87576225 |
| E1J0-r1-t1 | 16 | PASS | EVALUATOR_PASS | 0.51439530 |
| E0J1-r1-t9 | 13 | PASS | EVALUATOR_PASS | 0.36678570 |
| E1J0-r1-t13 | 20 | PASS | EVALUATOR_FAIL | 0.44029455 |
| E0J1-r1-t1 | 9 | PASS | EVALUATOR_PASS | 0.14799210 |
| E1J1-r1-t9 | 12 | PASS | EVALUATOR_PASS | 0.30037935 |
| E0J1-r1-t13 | 39 | FAIL | LIMIT_REACHED | 0.85714980 |
| E1J1-r1-t1 | 9 | PASS | EVALUATOR_PASS | 0.16969260 |
| E0J0-r1-t9 | 8 | PASS | EVALUATOR_PASS | 0.13075065 |
| E1J1-r1-t13 | 33 | PASS | EVALUATOR_FAIL | 0.62773290 |
| E0J0-r1-t1 | 10 | PASS | EVALUATOR_PASS | 0.23135535 |
| E1J0-r1-t9 | 11 | PASS | EVALUATOR_PASS | 0.27355890 |

Total **USD 4.93584945 / 10.56**, 216 model calls, 221 settled input counts, 289
actions. Serial dispatcher wall time was 3,744.86 seconds; row wall times summed
to 3,713.037 seconds. Per-task costs were USD 2.80093950 / 1.06343535 / 1.07147460
for tasks 13 / 1 / 9. No row, arm, task or invocation cap was exceeded.

Accounting rechecked every dispatched request against its selected count and actual
model, and recomputed usage at the frozen [official rates](https://developers.openai.com/api/docs/pricing):
USD 0.75 uncached input, 0.075 cached input and 4.50 output per million tokens.
Maximum admitted input was 58,200 tokens, request 422,486 bytes and encrypted item
168,996 bytes. No count/transport/billing uncertainty or scheduler-wide stop occurred.
All public execution cleanup receipts were confirmed; all ten native evaluations
confirmed cleanup and agreement. Safety was PASS for ten submitted rows and NOT_RUN
for the two unsubmitted rows. There were no acceptance ERROR rows. All runs remain
`official=false`, `claim_eligible=false`.

The Astroid E0J0 terminal was `max_output_tokens`, with its final output ceiling
reduced to 11,458 by existing cost admission. Its only accepted edit added a test;
the required check never ran. E0J1's final public test failed; after 39 calls, the
completion horizon required two calls with only one left. No following model request
received that last failure. Its last two output ceilings were 21,897 and 5,445.
These are accounted local non-successes, not hidden-evaluation FAIL or an ignored
failure observed by a later decision. Other rows kept the 25,000 output ceiling.

## Retention exposure, losses and displacement

Public annotations for all 12 rows were sealed before acceptance unblinding. Arms
were visible and historical selection outcomes known; neither arm blinding nor
complete historical grade blinding is claimed. Raw/encrypted reasoning content was
not inspected or decrypted. The audit used public tool decisions, source, results,
plans and the complete actual request, including alternate delivery routes.

There were **44 later transitions** and **352 provider-free compositions**:
four arms times both optional-exchange omission variants for each transition.
Original-arm source and result-body sets matched the actual request at **44/44**
boundaries. Replay used only autonomous references and observed source versions.

| Same-state opportunity classification | Boundaries |
| --- | ---: |
| NO_DECLARATION | 31 |
| ALREADY_RETAINED | 12 |
| DELIVERED_CHANGE, counterfactual result-body addition | 1 |

Toggling E gained **zero source line versions** and displaced **zero source line
versions** across these replays. The one changed result body was at E0J1 Pydicom
sequence 160: E1 would add the earlier failed check, but its material `DID NOT RAISE`
content was already delivered through verification observations in the actual E0
input. It was not a new material counterexample and was not an actual E1 exposure.
The 23 boundaries in the six E-on trajectories had **zero new evidence-body
exposures**. This limits the retention explanation; it does not show that useful
retention can never help.

E still changes the prespecified selection-disclosure sentence by four bytes.
Except for that counterfactual extra result, equal-body inputs matched after
normalizing exactly this sentence. Entire E prompts were not identical, and actual
trajectories may differ. Do not describe this as zero total factor exposure.

Toggling J preserved source and result bodies at all 44 saved boundaries in both
omission variants. Metadata/instructions added 666 to 1,796 input bytes at the
actual omission settings. Exact counterfactual token counts and full size admission
were **NOT_RUN**; the replay does not establish identical future transitions or
future model behavior under J.

Real transitions still lost previously delivered, current-version code. The four
Astroid rows contained 547 / 1,200 / 905 / 687 loss candidates in E0J0 / E1J0 /
E0J1 / E1J1, respectively; the other eight rows had zero. These 3,339 entries count
repeated line versions across boundaries, not distinct necessary facts. Material
examples, linked to request identities in the sealed annotations:

- E0J0: builder dispatch lines 118-126 disappeared at sequence 380 and were read
  again at turn 27. E had no usable reference at that boundary and changed no body.
- E1J0: builder code disappeared at sequence 214 and was read again at turns 15/17;
  manager caller code disappeared at 314 before finish.
- E0J1: callback/discovery/source-file code disappeared at 390 and was read again
  at turns 28/30/31. The spec finder body was lost at 511, **after** the bad edit;
  that later loss cannot explain the earlier incorrect source inference.
- E1J1: callback code disappeared at 379 and was read again at turn 28; manager
  lines 192-249 disappeared at 434. E again selected no additional body.

The original Pylint directory-entry/caller link was never successfully acquired in
these Astroid trajectories. Missing that link is **NOT_ACQUIRED**, distinct from
the documented **LOST_AT_HANDOFF** code. Neither absence alone assigns the failed
repair to retention. All gained/displaced line-version inventories, body identities,
text and omission metadata remain in the external replay evidence.

## Judgment with delivered evidence

The sealed audit identified **16 eligible public decision units**: 3 / 4 / 5 / 4
in E0J0 / E1J0 / E0J1 / E1J1. These are selected material decisions within different
trajectories, not matched or independent samples. J instruction presence alone did
not count as an eligible decision. Source-supported inference was allowed; there
was no requirement to add a check solely to justify a label.

| Public observation | Evidence and limit |
| --- | --- |
| Astroid E0J0 unsupported source inference | Turn 34 claimed directory discovery required init files despite the current `not list_all` guard and an existing non-package `list_all=True` test. It added only a test and never submitted. |
| Astroid E0J1 unsupported source inference | Turn 34 supplied a full module prefix with an already-advanced parent path to the finder. The actual request included both call construction and finder iteration. A later added test failed; no subsequent decision saw that failure. |
| Astroid E1J0 limited source support | The edited package-directory conversion was visible and supported conditionally. Reachability from the original Pylint caller remained unassessable because the caller link was missing. Public PASS did not settle that gap; independent acceptance failed. |
| Astroid E1J1 supported helper, overstated scope | A current-diff probe confirmed the namespace helper behavior. Calling this an end-to-end exercise overstated a probe that never ran Pylint directory scanning/AST construction. Both the original task and probe scope were present. Independent acceptance failed; this does not identify its private failure condition. |
| Marshmallow | All arms had source support for the `None` guard and passed acceptance. E0J1 executed the original scalar example; E1J1 added an accepted matching regression. E0J0/E1J0 acknowledged the missing dedicated test rather than inventing executed support. |
| Pydicom | All arms repaired the lookup/exception boundary and passed acceptance. E0J1/E1J1 corrected their failing test using strict conversion settings; E1J0 used a probe-confirmed malformed numeric value. These preserved the exception/suppression purpose. E0J0 acknowledged its probe did not reproduce the exact failure and finished on supported source inference. |

The labels include nine executed-support units, four supported source inferences,
two unsupported source inferences and one acknowledged gap followed by matching
execution. E1J1 Astroid additionally has an unsupported execution-scope claim;
that label overlaps its supported helper unit. Original caller decisions with
incomplete evidence remain separately unassessable. The narrowly recorded
`unsupported_final_closures=0` does not erase the source errors, caller gaps or
scope overclaim.

J-on trajectories sometimes obtained more direct public checks, but they still
contained a source-interpretation error and a scope overclaim. J0 Pydicom also
corrected a failed oracle while preserving its purpose. The panel does not establish
fewer unsupported judgments or improved acceptance from J. It shows that the current
presentation/guidance is insufficient to reliably prevent these observed errors.

## Separate current-contract defect and decision

Two Marshmallow trajectories received six test-edit rejections with the message
`duplicate definitions cannot be separated` (E1J0 four; E0J0 two). A provider-free
AST/policy replay fully audited **one** E1J0 candidate: every original statement and
class header remained unchanged and in order, with one added test method. The
baseline already contained two `test_nested_only_and_exclude` definitions. Both
unchanged input and that additive candidate triggered the same rejection in
`patchloop/test_additions.py` before unchanged definitions were matched.

This reproduces a structural-validator false rejection candidate independent of E/J;
it does not prove all six rejected proposals were safe. No production fix was mixed
into the frozen experiment. A useful next bounded task is to preserve identical
pre-existing duplicates while still rejecting new ambiguity and modifications to
protected tests, with provider-free regression coverage. It is a proposed follow-up,
not an automatically launched fix or another paid experiment.

The accepted-repair counts and no-new-body exposure preserve the decision to make
no default change from this panel. Retention's benefit under useful autonomous
references remains unresolved; judgment guidance did not eliminate the observed
errors or improve repair count. Three exposed tasks with one repetition cannot
estimate variance, individual causal attribution, statistical significance or
generalization. The next evidence-based step is the reproduced validator defect,
not another adjacent prompt/retention comparison or spending the unused allowance.

## Evidence and validation

All generated execution/audit state remains outside the repository:

- `C:/pt/analyses/repair-mechanisms-live-20261018-v1`: authorization, rates,
  before/preflight, closed execution, per-row outcomes, public audits and results.
- `C:/pt/repairmechanisms17live01`: twelve isolated solver stores and artifacts.
- Parent hash-chained journal: `runs/run_dev_repairlive18.jsonl` in the analysis root.
  Every public annotation seal precedes `acceptance_unblinding_started`; all 12 were
  sealed before any fresh final acceptance grade was opened for analysis.
- `results.json`: SHA-256
  `61080d9bc0e9be80c4a3177c4d2bbb278dd928b12755c359c5113e4a55a11c5e`.
- `mechanisms-final.json`: SHA-256
  `ddb57cb6f1b2199c989ca3b2804da2265703dc43e706a4975b94d4d43b571a40`.
- `pre-unblind-integrity.json`: SHA-256
  `f53a8a890d9643eb5f73c833d2fd1b29b434aede720fd38fb4ab5f40e76eaa41`;
  PASS for unchanged tracked/readiness bytes, all four arms and 44 calibrated boundaries.
- `operator-audit/<row>.json`, `audit-public/<row>/turn-index.json`,
  `replay-comparisons/<row>.json` and `replay/<row>/<arm>/`: actual request hashes,
  event sequences, candidate diffs, remaining budgets, source/results and full
  gained/lost inventories. Counterfactual compositions are not repair outcomes.
- `report-metrics.json`: post-unblinding aggregation of public checks, resource
  ceilings and already sealed judgment labels; it does not revise those labels.
- `test-preservation-followup.json`: recursive AST preservation and policy replay.
  Initial top-level-only inspection was insufficient for a class method; the
  corrected recursive check is the basis of the finding.

The readiness packet binds all four exact arms' 5,225-pass / 19-skip full-suite,
Ruff and mock isolated-evaluation receipts. Runtime bytes stayed frozen during
execution. This change adds only the result record and current indexes. Closeout
validation: documentation layout/link tests **5 passed**; Ruff and diff whitespace
checks **PASS**. Full runtime suites and mock smoke were not repeated for this
documentation-only closeout.
No private spec, hidden test, reference patch or evaluator case detail was projected
into a solver or used to author the public mechanism annotations.
