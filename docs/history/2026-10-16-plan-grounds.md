# Plan revision grounds: C/D comparison results

Date: 2026-10-16. Allocation closed at **USD 5.74993635 of USD 19.20**.
All sixteen fresh solves submitted and passed their final required public checks.
Previous C and new D each received **0/8 independent PASS**. D performed one
post-PASS probe; neither arm edited after first PASS. All runs are official=false,
claim-ineligible and development-exposed.

## Question and decision

The [C exit audit](2026-10-16-assessment-gap-exit-analysis.md) found verification
commitments disappearing during whole-plan replacement and regression PASS being
used to support claims about a specific requirement. This matters because a written
assessment can preserve the same unsupported completion decision.

The user approved the [C/D protocol](../../.agent/plan-revision-comparison.md):
compare C with the implementation retaining predecessor plans and revision reasons,
binding the final plan review to the submitted diff, and marking requirement
verification as unassessed by generic check receipts. Additional verification remains
optional. The question separates traceability, actual verification/repair and correctness.
Already-sufficient verification, explicit source inference and reasons that merely
justify an unchanged decision remain plausible outcomes.

The traceability mechanism was exposed and used: all 31 D plan revisions retained
their predecessor and reason, and all eight submissions retained a bound plan review.
The public audit classified unsupported closure in 4/8 C runs and 2/8 D runs. This
is a descriptive observation from a small, unblinded panel, not an established rate
improvement. D's one post-PASS probe supplied narrower execution evidence without
changing its patch. The prespecified quality criterion was **not met**: 0/8 versus
0/8, no late repair and no FAIL-to-PASS transition.

The requested evidence-retention contract remains implemented. This result provides
no quality-based adoption claim, new mandatory-check gate, further runtime change or
automatic paid follow-up. The unresolved question is why particular verification
purposes are treated as dispensable, including the two D astroid closures whose
recorded reasons still fail to support their specific claims. Another comparison
requires a new evidence-based reason; remaining budget is not authorization.

## Frozen scope and preparation

| Version | Frozen commit | Artifact arm |
| --- | --- | --- |
| Previous C | `b34e911d88acab74e431120c8e39760cc2656c25` | A |
| New D | `fcfa496dfb57f7e0d79616e5389fac034cfbc6b2` | B |

D is a report label, not a runtime version. Report C1-7 maps to artifact A1-7;
D1-7 maps to B1-7. Historical C outcomes are background, not pooled controls.
This compares the whole runtime intervention from the first turn, including changes
before first PASS. It does not isolate a sentence, reason field or post-PASS effect.

- Tasks: `tasks/dev-train/current-dev20/{7,10,13,19}/public.yaml`, two fresh solves
  per task per arm. Waves C1, D1, D2, C2; task order 7,10,13,19; two workers.
- Model: `gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000, standard/global;
  credential path `C:/Users/geonj/Documents/PatchLoop/.env`.
- Per solve: USD 1.20, 40 model calls, 100 actions, four accepted edits and 1,800
  seconds including 330 seconds reserved for registered evaluation. No budget transfer.
- Current policy, brief-v1, segmented-v1, result-or-size-v1, retained source 24,000,
  probes enabled, probe-policy/recheck none, repair-recheck, protected-v1, per-call-v1.
- Same task/source/dependency/image/native-grader identities; isolated workspaces,
  journals and ledgers. No shared notes, seed-matching claim, retries or resumptions.

The manifest, approval, helper/runtime hashes, effective request, task identities,
installed images and registered pricing were frozen before dispatch. Both exact-arm
mock runs reached isolated acceptance PASS with zero provider calls; mock safety was
NOT_RUN. Two distinct worker processes per arm verified their import origins.
Four-task import, ordinary-operation and public selected-test canaries passed.

SQLFluff was checked in both the prepared probe and registered public-check
environments: one core entry point and loaded core plugin, successful default config,
ANSI/Jinja linter construction, and parse/lint of `SELECT 1` without violations.
The first diagnostic's `entry_points(group=...)` call was incompatible with the
registered environment's older Python metadata API. Only the operator diagnostic
changed to filter `distribution("sqlfluff").entry_points`; both corrected checks
passed before dispatch. Initial failure logs remain preserved. No solver task hint,
source/dependency repair or image pull/build was used to obtain readiness.

The new checkout initially had CRLF-converted `pyproject.toml` and `uv.lock`.
Both were restored to raw HEAD bytes, with empty staged/tracked diffs and verified
runtime/import identities before dispatch. Initial and final inspections are preserved.
The separate mini-SWE runner and its historical environment mismatch are not this
comparison's runtime or evidence.

## Plan closure grounds

Public judgments were sealed before the operator inspected independent grade results.
Automated agreement guards still inspected grades for stop conditions. The public
audit used actual requests, plan changes, assessments, tools, public selectors and
receipts; it received no private grader details. Arm blinding is not claimed because
D's fields identify it. Each judgment binds the original journal hash and event sequence.

| Public audit classification | C | D | Meaning |
| --- | ---: | ---: | --- |
| Executed support for the named purpose | 2/8 | 3/8 | Current-diff input/assertion/result; not whole-task correctness |
| Explicit source inference | 2/8 | 3/8 | Unexecuted verification acknowledged; source facts support the judgment |
| Unsupported closure | 4/8 | 2/8 | Purpose omitted/weakened without sufficient accounting, or unrelated PASS promoted |

No row used public-scope exclusion as its closure category. Source inference is not
executed proof, and it does not automatically make a completion judgment invalid.
Verification completed before first PASS can support closure without a redundant check.

| Run | Ground | Public evidence and remaining boundary |
| --- | --- | --- |
| C1-7 | Unsupported | Adds `test_charset.py` case, but registered check selects `test_valuerep.py`; no separate execution, despite claiming the added case was exercised. |
| C1-10 | Unsupported | Adds reload test in `test_filereader.py`, outside the two selected files; passing regression is treated as its execution. |
| C1-13 | Unsupported | Promised missing-init regression disappears; source guard and existing suite substitute for the specific F0010 verification. |
| C1-19 | Unsupported | Promised Unicode regression is absent; base-regression PASS is promoted to evidence of the encoding-failure path. |
| C2-7 | Executed | New membership/iteration test is in the actual registered target and passes. |
| C2-10 | Inference | Acknowledges no dedicated side-effect test; reasons from removal of initialization statements. |
| C2-13 | Executed | Diagnostic reproduces a module-path failure; new regression fails, a later edit repairs it, then the suite including that test passes. All before first PASS. |
| C2-19 | Inference | Explicitly omits the encoding reproducer and reasons from encoding before opening; exception/CLI behavior remains unexecuted. |
| D1-7 | Executed | New positive/negative substring test executes in `test_valuerep.py`. |
| D1-10 | Inference | Repairs an actual regression before first PASS; acknowledges its added reload test was not executed and closes from source alignment. |
| D1-13 | Unsupported | Pre-edit probe distinguishes directory/module loading, but no rerun after the guard edit; existing suite substitutes for the promised targeted case. |
| D1-19 | Executed | Keeps Unicode/file-preservation purpose open after PASS, runs a probe, and separates that result from unexecuted full-CLI inference. |
| D2-7 | Executed | New membership/iteration test executes in the actual public target. |
| D2-10 | Inference | Reads/searches after PASS; acknowledges the promised reload test was not added, relying on source removal. |
| D2-13 | Unsupported | Pre-edit probe does not exercise the changed path; reason makes the targeted regression conditional on existing-suite failure, then omits it. |
| D2-19 | Inference | Explicitly removes the Unicode probe with a retained pre-encoding rationale; finish acknowledges no Unicode/noqa reproduction. |

C's 58 plan revisions have no new reason field by design, not a schema violation.
D retained reasons for 31/31 revisions with no annotation rejection. Actual post-PASS
model requests exposed the new reason schema, predecessor plan and requirement
`not_assessed` evidence in 8/8 D runs. Finish preserved a diff-bound `plan_review`
in 8/8. Seven D finishes used a null plan update; their existing plan/reason remained
available. D2-19 changed the plan at finish and retained the reason for removing its
probe. Thus field delivery worked, while evidence sufficiency remained a model judgment.

For D1-19, artifact B1-19 sequences 176/178/192 show the reason, probe and finish:
the reason treats regression as non-regression evidence; the probe writes an ASCII
file, attempts an arrow-containing replacement through `persist_tree()`, and asserts
a false return plus preserved `ORIGINAL` content. It exits zero. Full CLI behavior
is explicitly inferred from inspected `do_fixes` source, not reported as executed.
For D2-13, sequences 504/522 retain conditional weakening and the unsupported finish.
These contrasting traces show why preserving a reason is not certifying its truth.

## Actual verification and changes

First PASS is the first nonempty candidate with healthy required receipts for its
exact diff. Post-PASS counts begin after the model receives that result. Reads,
searches, authored tests and internal deliberation are not executed verification.

| Observation | C | D |
| --- | ---: | ---: |
| Submitted / final public PASS | 8/8 | 8/8 |
| First post-PASS action is finish | 8/8 | 6/8 |
| Rows with post-PASS executed verification | 0/8 | 1/8 |
| Rows with only post-PASS reads/searches before finish | 0/8 | 1/8 |
| Post-PASS edit attempts / accepted edits | 0 / 0 | 0 / 0 |
| First-PASS patch equals submitted patch | 8/8 | 8/8 |
| Whole-trajectory probe actions | 1 | 3 |
| Whole-trajectory selected-test actions | 0 | 0 |
| Whole-trajectory required-check actions | 9 | 9 |
| Whole-trajectory accepted edits | 13 | 13 |

D1-19 accounts for the only post-PASS probe. D2-10 performs one `read_file` and one
`search_files`, then finishes; that is source review, not an additional test.
The other two D probes are pre-edit astroid diagnostics. C's probe is also a
pre-edit astroid diagnostic. C2-13 and D1-10 each repair a failing public check
before their first PASS. Neither is evidence of repair caused by post-PASS review.
D1-10 has no accepted edits left at first PASS, but verification is still available.
No redundant check or mandatory follow-up action was required for any row.

## Independent results and cost

| Task | C independent PASS | D independent PASS | C cost USD | D cost USD |
| --- | ---: | ---: | ---: | ---: |
| 7: pydicom__pydicom-1139 | 0/2 | 0/2 | 0.32628615 | 0.36629685 |
| 10: pydicom__pydicom-901 | 0/2 | 0/2 | 0.37863960 | 0.61894980 |
| 13: pylint-dev__astroid-1333 | 0/2 | 0/2 | 1.56519570 | 1.40093070 |
| 19: sqlfluff__sqlfluff-1763 | 0/2 | 0/2 | 0.50690130 | 0.58673625 |
| Total | 0/8 | 0/8 | 2.77702275 | 2.97291360 |

Each arm has eight FAIL, zero ERROR and zero NOT_RUN. Registered/native graders
agree on all sixteen; live safety is PASS and native cleanup is confirmed for all.
All original and intermediate patch hashes were reconstructed successfully. Since
first-PASS and final patches match in all sixteen, first-PASS evaluation reuses the
same-row final receipts: **zero additional candidate evaluations**, sixteen
FAIL-to-FAIL transitions, zero FAIL-to-PASS or PASS-to-FAIL transitions. This is
receipt reuse, not a second independent measurement of an unchanged candidate.
Native evaluation uses the frozen registered projection of additive test paths;
public checks, independent task acceptance and safety remain separate results.

C used 147 model calls and D 153; total 300. Counting and billing are known,
allocation CLOSED, stopped=false. Offline audit/reconstruction used zero provider
calls. Exact cost is 5,749,936,350 nanos; unused USD 13.45006365 is unallocated.
No transport/billing uncertainty, retry, resume, replacement or paid judge occurred.

The quality criterion required more D successes with no per-task decrease and complete
grades/accounting. Complete grading was achieved, but no success increase occurred.
Four previously exposed tasks with two stochastic repetitions per arm support neither
generalization nor statistical significance. Executed support for one chosen plan
purpose, including the SQLFluff probe, does not establish complete requirement coverage.

## Validation and evidence

Preparation/helper tests: 67 PASS in 39.099 seconds. Planning/check-review/documentation
tests: 55 PASS in 67.063 seconds. Both focused groups meet two minutes. Helper Ruff
passed with the recorded formatting-only exemptions; both exact-arm mock smokes passed.
No runtime code changed in this execution/closeout turn. Documentation closeout checks
and final hashes are recorded separately in the closeout artifact.

The pre-documentation integrity pass checked 38,188 existing files with no changes,
including closed experiment records and the user's AGENTS.md edit. Only the mutable
history index is intentionally updated among that preserved set; closed reports and
external historical packets are untouched. This report is a separate follow-up.

- Frozen manifest: `C:/pt/planrev16prep01/manifest.json`,
  `sha256:e0774dce57eade8b95430a40505047f9bf9502603252dc6ca2b33778e91f06ba`.
- Approval, initial/final inspections, corrected SQLFluff capabilities, validation,
  two-worker smoke and preflight: `C:/pt/planrev16prep01/`.
- Public-only prompts/actions: `C:/pt/planrev16prep01/public-evidence.json`.
- Sealed rubric and row judgments: `C:/pt/planrev16prep01/public-review-frozen.json`;
  sealing/closeout journal: `C:/pt/planrev16prep01/runs/run_dev_planrevisionpublicreview.jsonl`.
- Paid closure and original journals: `C:/pt/planrev16live01/result.json` and row roots.
- Verified reconstruction/receipt reuse: `C:/pt/planrev16post01/result.json`.
- Derived grades/cost: `C:/pt/planrev16post01/summary.json`.
- Final validation/integrity bindings: `C:/pt/planrev16prep01/closeout.json`.

Implemented evidence retention, local validation, live behavior and independent
acceptance are distinct evidence axes. No claim-producing or held-out evaluation ran.
