# Verification purpose comparison: stopped before E

Date: 2026-10-16. Allocation closed at **USD 1.47315645 of USD 19.20**.
Four of sixteen planned solves ran, all in previous D's first wave. Three submitted
and passed their required public checks; all three failed both independent graders.
Astroid ended with `INCOMPLETE_RESPONSE` before an edit or submission. The frozen
launcher stopped subsequent waves: D's second four solves and all eight E solves
were **NOT_STARTED**. The D/E mechanism and quality comparisons are **NOT_ASSESSABLE**.
All runs are official=false, claim-ineligible and development-exposed.

## Question and decision

The [D astroid audit](2026-10-16-astroid-plan-closure.md) found the original
verification purpose replaced with a neighboring path or made conditional on suite
failure, despite retained plans and revision reasons. This matters because recording
a rationale does not establish that the original observable behavior was checked.

The user approved the immediately preceding [D/E proposal](../../.agent/verification-purpose-comparison.md)
with "그럼 실험해볼까". E changes only two guidance constants: preserve the original
input/path/outcome and base completion on current-diff execution or specific source
inference. It adds no tool, mandatory extra check or resource allowance. The panel
separates purpose preservation and closure grounds, actual verification/repair, and
independent correctness. Plausible alternatives were adequate existing D behavior,
wording-only changes in E, and repair failures outside this mechanism.

The three submitted D rows had executed evidence for their named verification
purposes. One ran a direct probe after public PASS; none edited afterward. These
observations do not establish full requirement coverage or repair correctness.
The target astroid closure was not exercised: its original verification remained
unfinished when generation failed. E had no live exposure, so neither prevention
nor absence of benefit can be inferred. Historical D outcomes are not substituted
for the missing fresh controls or pooled into this panel.

The requested guidance remains implemented, with no effectiveness or adoption claim
from this panel. No runtime change, retry, replacement solve, continuation or further
paid run followed. The unspent USD 17.72684355 is closed allocation, not permission
to continue. The unresolved questions are the unmeasured D/E effect and why this
astroid trajectory failed to produce an edit before two output-limited responses.
The saved public trace supports further offline diagnosis; private reasoning content
was not inspected and no causal explanation for generation failure is established.

## Frozen scope and environment

| Report arm | Solver commit | Artifact arm | Planned / started |
| --- | --- | --- | ---: |
| Previous D | `fcfa496dfb57f7e0d79616e5389fac034cfbc6b2` | A | 8 / 4 |
| This change E | `5fbce0c59ef5359393e67b09ce5ff4bf0de715dc` | B | 8 / 0 |

Report D1-7 maps to artifact A1-7; E1-7 maps to B1-7. E is a report label, not a
runtime version. The proposal was recorded at `26d15ca`; approval binding at
`ae93d2b` left the exact revisions, roster, resources and criteria unchanged.
Later runner changes in the working checkout were excluded from both arms.

- Tasks: `tasks/dev-train/current-dev20/{7,10,13,19}/public.yaml`, two fresh solves
  per task per arm. Planned waves D1, E1, E2, D2; task order 7,10,13,19; two workers.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000, standard/global;
  credential file `C:/Users/geonj/Documents/PatchLoop/.env`.
- Limits per solve: USD 1.20, 40 model calls, 100 actions, four accepted edits,
  1,800 seconds including 330 seconds reserved for registered evaluation.
- Current policy, brief-v1, segmented-v1, result-or-size-v1, retained source 24,000,
  probes enabled with policy/recheck none, repair-recheck, protected-v1, per-call-v1.
- Same task/source/dependency/image/native-grader identities; fresh isolated
  workspaces and journals. No shared notes, matched-seed claim, paid judge, budget
  transfer or SDK retry. The normal one-consecutive-error protocol correction remains.

The manifest and approval bound exact source/runtime/helper/prompt hashes, effective
requests, task packages, installed images, interpreters, reviewed pricing and caps
before dispatch. Runtime ASTs match outside the two guidance constants; task and
lock bytes match. Actual worker import origins and two distinct worker processes per
arm were verified. Both exact-arm mocks reached isolated evaluation PASS at zero
provider cost, with mock safety NOT_RUN. Four-task public import, ordinary-operation
and selected-test canaries passed in both arms.

SQLFluff passed in both the actual probe and registered public-check environments:
exactly one core entry point and loaded core plugin, default configuration,
ANSI/Jinja Linter construction, and parse/lint of `SELECT 1`. The copied diagnostic
was adapted to the older metadata API via `distribution("sqlfluff").entry_points`;
no task, dependency or image change was used. Initial evidence was preserved.

E's fresh checkout initially had CRLF-converted `pyproject.toml` and `uv.lock`.
Those files were restored to exact HEAD bytes; the Git stat cache was refreshed
with an empty staged diff. The authoritative final inspection confirms raw-byte
identity and a clean solver checkout. Initial and intermediate inspections remain
preserved. Manifest and environment gates passed before any paid dispatch.

## Stop and accounting

Astroid made 35 model calls and 53 tool actions: 35 searches, 17 reads and one
baseline probe. It made no edit, required public check or finish call. Model calls
34 and 35 both returned `incomplete_reason=max_output_tokens`, 25,000 output tokens
and no tool call. Usage metadata attributes those tokens to reasoning output;
this is token accounting, not access to private deliberation.

The first incomplete result is journal event 494; the normal protocol correction is
496. The correction names the `needs_mutation` gate and available `replace_text` /
`stop_task` actions. The next incomplete result is 503 and terminal event 505 records
`INCOMPLETE_RESPONSE`. Thus this was not exhaustion of the 40-call or USD 1.20 row
cap: the row settled at USD 0.87300075, with zero accepted edits and about 811 seconds
of active time. There was no caller-initiated retry or resumed solve.

The common frozen launcher's `wave_valid()` closes subsequent waves for a non-ok
row unless its disposition is the recognized `task_limit`. This output/protocol
failure triggered that path after D1. The condition's local variable name `known`
also covers row success; it must not be interpreted as uncertain accounting.
Final `billing_known` and `counting_known` are both true, with no recovered/unknown
usage or reported infrastructure failure. The stop rule was not changed mid-panel.

| D1 task | Model / tool / input-count calls | Accepted edits | Solver + registered seconds | Native seconds | Settled USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| pydicom-1139 | 9 / 15 / 9 | 2 | 168.607 | 25.111 | 0.15197340 |
| pydicom-901 | 13 / 17 / 13 | 2 | 308.973 | 20.575 | 0.25845570 |
| astroid-1333 | 35 / 53 / 37 | 0 | 811.579 | NOT_RUN | 0.87300075 |
| sqlfluff-1763 | 13 / 21 / 13 | 2 | 256.758 | 23.045 | 0.18972660 |

Total: 70 generation calls, 106 tool actions, 72 input-count calls, six accepted
edits and USD 1.47315645. Times are per-row measurements, not summed panel wall time;
the two workers overlap. Postprocessing made zero provider calls.

## Original purpose, closure grounds and behavior

The public requirement map and audit rubric were frozen before dispatch. Public-log
judgments were sealed before the operator inspected independent grades; automated
agreement guards used grades only for stop decisions. Judgments use actual delivered
requests, plans, reasons, current diffs, public selectors and execution receipts.
No private grader details entered the solver or public classifications. Arm blinding
is not claimed. The retained full public evidence includes unstarted rows explicitly.

All 70 actual D requests contained its system/planning guidance. All eight D plan
revisions retained their predecessor and reason; all three finishes had a bound plan
review. E's instruction hashes were prepared, but it received no live requests.

| D1 task | Original purpose and closure evidence | After first PASS reaches model |
| --- | --- | --- |
| pydicom-1139 | Containment and iteration of PersonName. Added assertions test `S`/`Some` membership and joined iteration. Their module was executed by the registered check: 39 passed. | Immediate finish; no extra check or edit. |
| pydicom-901 | Import must not configure logger handlers/level; explicit debug remains usable. Direct probe observes zero handlers and NOTSET before/after import, then DEBUG/WARNING after explicit calls. Regression: 95 passed, 1 skipped. | One successful probe; no edit. |
| astroid-1333 | Repair missing-init directory loading, then verify the resulting diff. One baseline discovery probe; no candidate or closure. | No PASS boundary; NOT_EXERCISED. |
| sqlfluff-1763 | An unencodable fix must not wipe the original file. Added test forces UnicodeEncodeError and asserts unchanged contents; its module ran in the registered 147-test PASS. | Immediate finish; no extra check or edit. |

The public audit classified **three eligible closures as executed current-diff
support**, with zero unsupported closures among those three. The fourth executed row
has no closure to classify. Four further D rows and eight E rows are NOT_RUN; they
do not count as preservation successes. The strong mechanism criterion remains
NOT_ASSESSABLE because the target closure did not recur and E was never exposed.

Specific grounds and limits:

- Pydicom-1139: plan 15 originally named a focused probe plus regression. Revision
  120 kept the observable purpose in an added test (edit 107/result 108), executed
  by check 121/result 122. First PASS reaches request 126; finish is 136/result 137.
  This changes the verification method, not the intended membership/iteration
  outcome. Dataset assignment was not separately executed. Generic suite PASS alone
  is not the support being credited.
- Pydicom-901: plans 16, 31 and 144 retain import-state verification. Revision 158
  defers a dedicated-test decision but leaves the behavior unresolved; after check
  result 160, revision 172 requests the direct probe despite PASS. Probe 173/result
  174 runs on the current diff; finish 188/result 189 explains why an additional
  persistent test is unnecessary. This is observed verification, not a promise to
  test only if regression fails.
- Astroid: plan 16 remains incomplete through revisions 292 and 481. Probe 266/result
  267 is on the empty diff and explores module discovery with a missing `__init__.py`.
  It cannot verify a later repair, and no repair or successful-completion claim follows.
- SQLFluff: plan 15 and revision 177 retain encoding-failure/file-preservation
  verification. Test edit 163/result 164 runs in check 178/result 179. First PASS
  reaches request 183; finish 194/result 195 cites encoding before opening the file
  and the executed preservation assertion. Full dbt/postgres reproduction and `--noqa`
  behavior were not executed; the persistence-boundary explanation is source inference.

Across the full trajectories, two probes ran: astroid's baseline diagnostic and
pydicom-901's verification. Three required checks ran; no selected-test action or
repeated required check ran. Six accepted edits comprise four source edits and two
test edits, all before first PASS. There were no rejected edit attempts. After PASS,
one probe ran and zero edits occurred. More text or tool activity is not counted as
quality improvement, and private deliberation is unmeasured.

## Independent evaluation

| Public task | D repetition 1 | D repetition 2 | E repetition 1 | E repetition 2 |
| --- | --- | --- | --- | --- |
| pydicom__pydicom-1139 | FAIL | NOT_STARTED | NOT_STARTED | NOT_STARTED |
| pydicom__pydicom-901 | FAIL | NOT_STARTED | NOT_STARTED | NOT_STARTED |
| pylint-dev__astroid-1333 | NOT_RUN: no submission | NOT_STARTED | NOT_STARTED | NOT_STARTED |
| sqlfluff__sqlfluff-1763 | FAIL | NOT_STARTED | NOT_STARTED | NOT_STARTED |

D has 0 PASS, 3 FAIL and 5 NOT_RUN out of eight planned rows. E has eight NOT_RUN;
it has no observed accuracy denominator. Across the panel, thirteen independent
evaluations were NOT_RUN: one unsubmitted trajectory and twelve unstarted solves.
The three submitted rows have final public PASS, registered/native FAIL agreement,
safety PASS and confirmed evaluator cleanup. Unsubmitted/unstarted evaluation and
safety remain NOT_RUN rather than PASS or FAIL.

Offline reconstruction verified every accepted intermediate diff and the public
receipt boundary without executing checks. Each submitted first-PASS patch equals
its final patch, so its two grader receipts were **REUSED_FINAL**, not measured
again. Astroid has no first-PASS candidate. Additional candidate evaluations: zero.
All three observed first/final transitions are FAIL-to-FAIL; no late repair or
regression was measured. The prespecified quality criterion requires all sixteen
known outcomes and a favorable E comparison; this incomplete panel cannot satisfy it.

## Evidence and local validation

External evidence is bound by append-only, hash-chained `dev-run-v1` journals.
The manifest hash is
`sha256:ed009d02eed71bcd378633290d2856254d940061e459ccba644d6d20ca459055`.

- Preparation and approval: `C:/pt/purpose16prep01/manifest.json`, `approval.json`,
  `validation.json`, `final-preflight.json`, `prompt-bindings.json`,
  `public-audit-rubric.json` and `runs/run_dev_purposeprep.jsonl`.
- Frozen public audit: `C:/pt/purpose16prep01/public-evidence.json`,
  `public-review-frozen.json` and `runs/run_dev_planrevisionpublicreview.jsonl`.
- Paid closure: `C:/pt/purpose16live01/result.json`; original row journals under
  `C:/pt/purpose16live01/{A1-7,A1-10,A1-13,A1-19}/runs/`.
- Offline reconstruction and comparison: `C:/pt/purpose16post01/result.json` and
  `summary.json`. Their `provider_calls=0` describes offline processing, not the
  paid panel's 70 generation calls. Postprocessing `stopped=false` means that offline
  work completed; the paid panel remains `stopped=true`.
- Final reconciliation: `C:/pt/purpose16prep01/closeout.json`, documentation-test
  receipt and documentation commit binding. These follow-ups do not rewrite sealed
  public labels, solver logs, frozen protocol or independent outcomes.

Preparation's focused launcher/observer/replay tests passed 72 tests in 55.37 seconds;
the final builder/documentation subset passed 20 tests in 0.62 seconds. These overlap
and are not 92 distinct tests. Ruff passed. Both exact-arm isolated mocks and all
environment canaries passed before dispatch. The closing documentation checks are
recorded separately. The full repository suite was NOT_RUN this turn: only operator
preparation and evidence documentation changed, with no runtime-source change.

The preflight preserved 1,147 protected files, including the preexisting user edit
to AGENTS.md. Final reconciliation checks historical bytes again, with only the
mutable history index changed to link this new record. Current status is replaced
with this closed result; historical results remain untouched.
