# Why C still closed verification after public PASS

Date: 2026-10-16. Offline follow-up to the closed
[B/C comparison](2026-10-16-assessment-gap-comparison-results.md).
No provider call, solver check/probe, candidate replay or evaluator run was added.
Runtime and frozen comparison evidence are unchanged. All underlying runs are
development-exposed, `official=false` and claim-ineligible.

## Question, scope and finding

C added instructions to retain unfinished verification and connect completion to
public requirements. Seven of eight C runs still selected finish immediately after
their first current-diff required PASS. This audit asks how their declared plans
were closed, using actual delivered requests and public actions, not another run.
It matters because a stronger explanation can leave an insufficient evidence
standard unchanged.

The seven exits are not seven abandoned tests. Two PN runs completed their scoped
test plans before PASS. Of the other five, three rewrote the remaining plan to
regression-only verification, one retained an explicit unperformed test plan, and
one weakened an initial test commitment to a conditional check. Their assessments
then treated source plausibility or suite PASS as sufficient, sometimes claiming
coverage or reproduction results that the observed evidence did not establish.

This is evidence of incomplete compliance with C's evidence standard, not a missing
instruction or forced automatic finish. C made justification more explicit in
several rows, but did not reliably preserve the purpose of the unfinished check in
the completion decision. The logs establish recorded decisions and actions, not
the content or quality of internal deliberation.

Here **B means the fresh previous-B arm in this latest comparison**, frozen at
`a18976699ed16533516b4347df935e0dea51d161`; C is
`b34e911d88acab74e431120c8e39760cc2656c25`. Raw launcher A maps to report B;
raw launcher B maps to report C. Thus C1-10 below is artifact `B1-10`, compared with
artifact `A1-10`. The earlier [original-B exit audit](2026-10-16-assessment-exit-analysis.md)
is background, not pooled data. Same-task/repetition pairs are independent solves,
not identical trajectories or a controlled replay of one completion decision.

## Actual prompt exposure and the unchanged completion contract

Verified all 16 journal hash chains, 246 prepared request artifacts and canonical
request hashes; 240 requests have a provider dispatch. The six undispatched
preparations are not extra calls. All 18 post-PASS requests have exactly one matching
dispatch. The system instruction, finish schema and completion message match within
each version: eight B requests and ten C requests, including C2-19's three turns.

The actual B system asks for review and an assessment of readiness and limits. C's
delivered replacement explicitly says:

> regression PASS alone does not prove the reported problem is fixed.
> Revisit unfinished planned checks and unsupported requirements.
> Skipped/rejected verification remains unperformed.

It continues:

> Otherwise explain what evidence meets the planned check's purpose or why the gap
> does not affect completion; listing a limitation is insufficient.

The planning instruction also changed from keeping unresolved requirements visible
to keeping unfinished verification until its purpose is addressed or its irrelevance
is explained. The actual completion message begins `Current required checks pass;
this establishes eligibility, not correctness`, and the finish assessment field
explicitly asks for unfinished or rejected planned checks to be accounted for.
These changes reached every C exit under review.

The change is a bundle, not simply an appended warning. It replaced B's more specific
system explanation that `mutation_expectation` is intent rather than coverage and
that `recent_checks.evidence_review` does not certify execution of each case.
The remaining common instructions still limit conclusions to observations, and C
states the general regression warning more directly. The saved prompts show this
tradeoff; this sample cannot isolate an effect of the removed sentences.

Both versions still say no separate call or mandatory experiment is required.
Their common mutation guidance also permits abandoning a rejected proposal and says
a rejected optional edit does not invalidate a visibly checked baseline. That rule
concerns candidate eligibility; it does not establish the rejected test's purpose
was satisfied. Its individual influence on C1-10 cannot be isolated here.
`ready_to_submit`, `submission_ready=true` and `next_action=null` express mechanical
eligibility. Both allow finish with a nonblank assessment of 1-1,500 characters,
a nonempty tracked patch and current required PASS; neither validates semantic
sufficiency of the prose. `plan_update` replaces the complete plan; the projection
keeps the latest plan and a review signal, not an independently checked list of
unfinished obligations. A null update can preserve an unresolved plan while finish
succeeds. This implements the requested discretionary judgment contract, rather
than establishing that the model met the judgment standard.

Owning code at the frozen revisions: `patchloop/dev/model.py`,
`runner.py::_completion_guidance`, `tools.py::dev_tool_schemas` and `_finish_task`,
`contracts.py::FinishIntent`, and `working_plan.py::project/record`. The executable
finish/plan validation did not change in C; the changes here were guidance.

## Seven task/repetition comparisons

Sequences identify public journal events. All seven C rows have exactly one model
response after first PASS, selecting finish with `plan_update=null`. Their first-PASS
and final patches are identical. None of these pairs ran a separate `run_tests` action.
Added tests can still execute inside `run_check`, so test additions and test execution
are distinguished below.

| Pair | Fresh previous B | C's plan, action and closure | Interpretation |
| --- | --- | --- | --- |
| 1-7, pydicom-1139 | Plan 13 promised a membership test. Added only `__iter__`; no test or probe. Finish cites a small direct fix and regression PASS. | Added `__contains__` and positive/negative substring assertions in `test_valuerep.py`; required check executes that file. Finish 164 explicitly dismisses broader iteration as outside the membership example. | C completed the scoped test plan. Remaining issue is scope judgment: the public title asks to make PN iterable. This is not an abandoned membership test or proof of complete correctness. |
| 2-7, pydicom-1139 | Added `__contains__` and membership tests; required check executes them. | Added both `__contains__` and `__iter__`, with membership and `list(pn)` assertions; 39 tests passed. Finish 104 says missing line-coverage detail does not invalidate these direct assertions. | The planned behavior check was completed in both. C's immediate exit does not by itself demonstrate a verification-process failure. |
| 1-10, pydicom-901 | Plans 126/140 promise executing the new logger test in `test_filereader.py`. It was added, but required check selects only `test_misc.py` and `test_dataset.py`; no selected-test/probe run follows. Finish nevertheless says the new test confirms behavior. | Plans 13/29 promise logger-state testing. Test mutation rejected at 148 and rolled back. Plan 158 becomes only required regression, then submit. After 95 passed/1 skipped, finish 173 relies on source removal and unchanged explicit `debug()`; no test or probe substitute. | B confused an added test with executed evidence. C replaced rejected verification with source-based confidence, despite receiving both the rejection and the new warning. |
| 2-10, pydicom-901 | Added a config-reload logger-state test to selected `test_misc.py`; check reports 96 passed/1 skipped. | Plans 95/109 promise a sentinel logger-state test. Only source changes occur. Plan 124 becomes regression-only; check reports 95 passed/1 skipped. Finish 140 says another check is unlikely to change judgment and refers to source plus unmeasured line coverage. | C dropped an explicit behavior test. Earlier test promises remain quoted in the final request, so this is not solely loss of context. B had more direct observed verification in this pair. |
| 1-13, astroid-1333 | Two baseline probes; the second fails to import pytest in the probe environment. Plan 277 promises a namespace-directory test, then 295 makes it contingent on suite results. No test added. Finish claims suite PASS confirms the visible reproduction and affected path. | Baseline probe 173 observes directory-load errors; it does not validate the later edit. Plan 444 explicitly promises a regular-package-directory test and possibly a namespace test. It is still the final working plan. No test or post-edit probe. Finish 472 says the changed path is directly exercised by the full regression and the gap does not block completion. | Same unsupported coverage substitution as B, with an explicit nonblocking-gap justification in C. The test plan was visible, not forgotten by the projection. |
| 2-13, astroid-1333 | Added a namespace-directory test to `unittest_manager.py`; selected suite reports 1,232 passed. | Plans 13/32 promise a regression test. Only `builder.py` changes. Plan 267 becomes required regression, then ready; suite reports 1,231 passed. Finish 283 says the concrete failure is no longer reproduced. | C erased the test from the current plan and promoted regression success to an issue-specific reproduction claim. No observed targeted run supports that conclusion. B completed a narrower manager-level test, which also does not prove the entire pylint issue fixed. |
| 1-19, sqlfluff-1763 | Several explicit Unicode/file-preservation test plans, including 236, remain unperformed. Atomic-write edit passes regression; finish admits no exact repro. | Plan 13 promises a preservation/encoding regression; plan 154 weakens it to a focused test `if needed`. Edits encoding autodetection fallback only. No test or probe. Finish 273 declares this the exact failure point and the omitted arrow-character repro nonblocking. | The requirement-specific experiment became optional and the source hypothesis was treated as established. C gives a reason for closure, but the observed evidence does not establish the claimed failure path. |

## How unfinished verification disappeared or was dismissed

**Latest-plan replacement is a real mechanism, but not the whole explanation.**
C1-10 replaces its earlier test commitment at decision 158 after the rejected edit;
C2-10 does so at 124; C2-13 at 267. At their final requests the active plan names
only regression verification. C1-19's plan 154 makes its initial promised check
conditional. These revisions do not supply an equivalent behavior observation or
explain why the original check's purpose ceased to matter.

Literal plan-retention analysis of the actual public message bodies sharpens this:
C1-10's final request 166 retains only plan 158, but also delivers the rejected
test's purpose and error in `last_failed_mutation`. C2-13's request 276 retains only
plan 267, omitting the earlier plan texts 13/32. C2-10's request 133 still quotes
plans 95/109 as well as current plan 124. Thus removing an obligation from the
current plan can lower its salience, but two of these cases still had its purpose
available. Whole-text absence is not proof that every concept was absent.

**The clearest counterexample to a pure retention explanation is C1-13.** Its final
request 465 still says `After that, add a regression test in tests/unittest_manager.py`.
Its assessment instead says:

> the code path change is directly exercised by the full public regression run
> ... so the remaining verification gap does not block completion.

The delivered check records say `coverage_status=not_assessed`,
`selection_kind=unresolved`, `declared_targets=[]`. This does not prove that the path
was unexecuted; it means the result does not substantiate the stated direct-coverage
claim. The only targeted probe preceded the edit and observed failures. Fresh B1-13
made substantially the same leap: the suite `confirms the reported failure is fixed
for the visible reproduction`. C adds a justification for dismissal, not a new
observation validating that dismissal.

**Rejected tests were not impossible to replace.** C1-10's rejection explains that
new tests must preserve existing imports, helpers, fixtures and tests. Its rejected
proposal did not become candidate evidence. Further edits, `run_tests` and `run_probe`
were still offered. The final assessment explains why no probe was run, but does not
account for the rejected test as an outstanding logger-state check. This local
friction explains one route being abandoned, not all seven exits.

**Test source, selected execution and requirement coverage remained conflated.**
Fresh B1-10 added `test_filereader.py` but did not execute it. C1-19 read known-encoding
tests in `test/core/file_helpers_test.py` at decision 219, then cited those tests in
its assessment. Its actual required check selects `test/cli` and
`test/core/linter_test.py`, not that helper-test module. Those source assertions may
inform the design, but their presence is not observed execution of autodetect-None
or failure-time preservation. Similarly, C2-13's `so the concrete failure ... is no
longer reproduced` exceeds a suite result without a target-specific observation.

For PN, the opposite distinction matters: C really did add assertions in the selected
test file. Requiring another external action merely because the hidden outcome is
FAIL would misclassify those two processes and impose a rule the user did not request.

## Why the eighth C run continued

C2-19 also temporarily rewrote its plan to finish after regression (149), after
promising an encoding-failure preservation test (121). Both texts were still in
its first post-PASS request 156. Decision 163 reopened the concrete question:

> The regression suite passes, but the issue also claims a UnicodeEncodeError can
> wipe the file; a direct probe ... can confirm the original file is preserved
> when the write itself fails.

Probe result 167 observed `UnicodeEncodeError` for an unencodable arrow under cp1252
and `after: ORIGINAL`. It then searched existing persistence tests (177), and finished
(191) citing that observation. No further edit occurred. The probe supplies evidence
for the earlier test's preservation purpose even though no test file was added.
The registered/native independent verdict still failed; extra verification is not
itself evidence of a correct complete repair.

This contrast supports concrete requirement-to-observation matching as the relevant
behavioral distinction. It does not prove C caused the probe: the same historical B
version also produced one such trajectory in the earlier experiment. Nor is explicit
concern registration necessary to explain this row: at its first post-PASS request,
as in the seven exits, `working_notes.verification.items` was empty.

## Alternative explanations and decision

- Missing new instructions or automatic finish: contradicted by actual dispatched
  requests and subsequent model-selected finish calls.
- Hard resource/tool closure: contradicted for all seven. Exploration was open,
  closure reason null, protected mutation completion feasible, and probe/selected
  tests/read/search/edit tools available. Final-input budgets ranged from 7-34 model
  calls, 2-3 accepted edits, 56-91 actions, USD 0.62883930-1.10147370 and 1,115-1,391
  remaining solver seconds. These are offered-state facts, not guarantees that every
  possible experiment would work. C1-13 had the least call headroom, but was not forced
  to finish.
- General context loss: incomplete explanation. All seven had the public task,
  complete untruncated patch and current PASS, and requested working-plan review.
  Five omitted no observed source lines; C1-13 omitted 679 and C1-19 omitted 375.
  All crossed a `major_result_reviewed` handoff with previous reasoning unavailable;
  the contrast C2-19 did too. Some older plan texts were absent, others demonstrably
  retained. Retention may affect individual decisions but cannot explain all exits.
- Existing verification sufficient for the scoped plan: supported for the two PN
  test plans. This does not prove their full repairs correct.
- Gap dismissal without purpose-equivalent behavior verification: supported by the other five
  plan/action/assessment trajectories. Whether each omitted check would have exposed
  the independent-evaluation failure remains unknown.

The measured comparison remains B 0/8 versus C 0/8 independent acceptance, all public
PASS, no post-PASS edits, and post-PASS verification 0/8 versus 1/8. In the seven paired
rows, B added test files in four runs (one outside the executed selection), while C
did so in two. The small independent samples do not establish deterioration or a
reliable prompt effect; they do show that C did not consistently increase actual
verification. No hidden failure cause is inferred from these public traces.

This investigation preserves the runtime and closes without a paid follow-up or a
mandatory-probe rule. The unresolved engineering question is how an agent preserves
the purpose of an unfinished public requirement check and distinguishes observed
support from its own source hypothesis when closing that purpose. Another general
instruction to review, or counting assessments, would not directly test that failure
mechanism. This audit adopts no new architecture, gate or intervention.

## Reproducible evidence

New offline artifacts are under `C:/pt/assessgap16exit01/`:

- `audit.py`: public-only extractor; reads frozen C's journal/hash helpers and never
  calls a solver, provider, sandbox or evaluator.
- `evidence.json`: SHA256
  `599703cf392876eaa02caf706242ac172c02b61cf6a3d69b6c9533bc14fcfe1e`.
  Contains plans, decisions, delivered plan-retention checks, public results, post-PASS
  messages/states, patches, request artifact references and journal identities.
- `prompts.json`: SHA256
  `16a959723a3d8feffc2dbca1aeaba7c9b66c2c6cacd5951399cbd4ea1b22271d`.
  Contains actual B/C instruction, finish-schema and completion-message comparisons.
- `runs/run_dev_assessmentgapexitaudit.jsonl`: append-only `dev-run-v1` hash chain
  binding extractor, source closeout, new evidence, report and local validation.

Source manifest is
`sha256:c6347da2905205d1d2e465e84f1ec4aff027f036f4f627834fc2446c4beaf0a1`.
The 17 prior closeout-bound files remain unchanged. The saved-request references in
`evidence.json` resolve below `C:/pt/assessgap16live01/<raw row>/artifacts/objects/sha256/`.
No private tests/reference patches/grader detail or provider reasoning continuation
was read for this analysis. Extracted plans, bases and assessments are public
declarations, not a reasoning transcript.

| C row (raw) | First PASS / final input / dispatch / decision / finish | Paired B raw row: final input / decision |
| --- | --- | --- |
| C1-7 (`B1-7`) | 153 / 157 / 162 / 164 / 168 | `A1-7`: 139 / 146 |
| C1-10 (`B1-10`) | 162 / 166 / 171 / 173 / 177 | `A1-10`: 162 / 169 |
| C1-13 (`B1-13`) | 461 / 465 / 470 / 472 / 476 | `A1-13`: 304 / 311 |
| C1-19 (`B1-19`) | 262 / 266 / 271 / 273 / 277 | `A1-19`: 270 / 277 |
| C2-7 (`B2-7`) | 93 / 97 / 102 / 104 / 108 | `A2-7`: 155 / 162 |
| C2-10 (`B2-10`) | 129 / 133 / 138 / 140 / 144 | `A2-10`: 207 / 214 |
| C2-13 (`B2-13`) | 272 / 276 / 281 / 283 / 287 | `A2-13`: 236 / 243 |

Validation: source/hash-chain/request checks above; documentation layout 5 PASS,
extractor Ruff PASS, report links valid and `git diff --check` clean. Receipts are
recorded in the offline closeout. No runtime tests or mock smoke were needed for this
analysis-only documentation change.
