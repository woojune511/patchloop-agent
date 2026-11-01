# Five-task frozen-agent results: four accepted, one logging-contract failure

## Material Passport

- Workflow: academic-research-suite experiment-agent, approved execution and analysis.
- Status: LIVE_EXECUTED, allocation CLOSED; official=false, claim-ineligible.
- Scope: five existing dev-train issues, one fresh solve each; no concurrent control.
- Preparation: [frozen plan](2026-10-29-repair-five-plan.md), unchanged after approval.
- External plan: `C:/pt/repair-five-plan-v1/manifest.json` and `approval.json`.
- Results: `C:/pt/repair-five-run-v1/batch-collection.json` and
  `C:/pt/repair-five-plan-v1/results-summary.json`.
- Operator evaluation audit: `C:/pt/repair-five-plan-v1/operator-evaluation-audit.json`.
  Private test details and logs remain external and were not sent to a solver.

## Question, scope and execution

After the saved pvlib failure was explained, the remaining question was what
repair or reliability failures appear on other public issues with the current
agent. The selected tasks span five repositories and public problem types. This
panel describes observed behavior; it does not isolate a policy effect or measure
held-out generalization. Selection used public material, not candidate outcomes.

The user approved the exact command `& 'C:/pt/repair-five-plan-v1/run.ps1'`, one
run each in order 1, 3, 10, 11, 15, USD4.50 per task and USD22.50 total without
transfers. Approved manifest identity:
`sha256:8a0b84a735bd4fc1c7b3563d4f7ec1471f55d2fe66b641086035078de2306fb9`.
Preparation/launch commit was `5ca44681`; implementation baseline `98a0f5b6`.
The runtime stayed
`sha256:08b32133d33201efb3b55cd44db917ff76ffc8752676e00f5cdc366280b16b1e`.

All rows used gpt-5.4-2026-03-05(xhigh), the repository `.env`, public-checks-v1,
thin and segmented-v1, 60K input, 40K/25K normal/correction output, 20 total
responses including at most one correction, 40 actions, three mutations and
2,400 seconds including 390 seconds reserved for evaluation. Each started from
the original prepared source. No earlier patch, checkpoint, operator diagnosis
or private evaluation output was injected. No condition changed between rows.

The approved executor ran once, from 2026-10-29 08:23:02 to 08:46:16 KST
(about 23m13s including batch overhead). All five rows reached normal submission
and registered isolated evaluation. No retry, extra solve, image pull/build,
native duplicate evaluation or runtime change was performed.

## Results

Primary outcome is registered original SWE-bench acceptance. The registered
oracle applies the original test patch and upstream grading. Public regression,
submission, diagnostic completeness and safety are separate measurements.

| Index / issue | Acceptance | Public suite | Edits | Model / tools | Active seconds | USD |
|---|---|---|---:|---:|---:|---:|
| 1 marshmallow-1343 | PASS | 779 passed | 1 | 9 / 13 | 252.279 | 0.4980390 |
| 3 pvlib-1154 | PASS | 98 passed, declared projection | 1 | 6 / 7 | 141.239 | 0.2537815 |
| 10 pydicom-901 | FAIL | 95 passed, 1 skipped | 1 | 12 / 15 | 230.709 | 0.4366615 |
| 11 astroid-1196 | PASS | 1293 passed, 76 skipped, 14 xfailed | 3 | 18 / 18 | 460.495 | 0.8757000 |
| 15 pyvista-4315 | PASS | 115 passed, 1 skipped | 1 | 9 / 17 | 274.940 | 0.4810145 |

Acceptance: **4 PASS / 1 FAIL / 0 ERROR / 0 NOT_RUN**. All five submitted current
diffs with required public checks PASS and received safety PASS. All original
oracles completed with no missing expected results; pydicom was a settled test
failure, not an infrastructure error. Full retained evaluator streams fit the
configured bounds in all five rows and their recorded hashes were checked.

Cost: **USD2.5451965 / 22.50**. The unused USD19.9548035 is closed, not transferable.
Active row time totals 1,359.662 seconds. All 54 provider/count pairs, 70 action
pairs and four probe execution pairs reconcile. Independent read-only audit
recomputed costs from usage, checked count-to-dispatch identities, journal hash
chains, frozen requests/runtime and the one durable batch closure. No accounting,
transport, execution or cleanup uncertainty was found. No protocol correction ran.

## What the trajectories show

### Simple repairs without task-specific execution

Marshmallow added two `None` guards around field validators, passed the public
suite and submitted. Pvlib masked zero-GHI outputs and suppressed the intermediate
division warning, then passed its public suite and submitted. Neither used a
helper, original replay or new test. Pvlib's declared public projection excludes
the old zero-GHI expectation; it does not newly assert the requested zero result.
Their acceptance PASS therefore remains distinct from public behavioral evidence.

### Pydicom: literal issue repair, insufficient acceptance

The model removed import-time StreamHandler/Formatter attachment and the call
that set the default logger level. It retained the existing `debug()` function.
It searched logging/debug usages extensively but ran only the registered
`test_misc.py` and `test_dataset.py` check. No logging-specific execution or new
test was performed. After the check it reread `config.py` and submitted without
another edit. Public journal evidence is at sequences 102-103 (edit), 136-137
(check), 151-153 (question/read) and 167-175 (finish/evaluation).

The original oracle completed and rejected this candidate. Its exact assertions
and exception evidence are retained only in the external operator audit. The
public description chiefly asks to remove import-time logging configuration;
static inspection confirms the patch targets that request. The preserved opt-in
debug behavior is an untested compatibility question, while private acceptance
also requires behavior not spelled out by that short description. Thus neither
"the model ignored the issue" nor "a mandatory reproduction would necessarily
solve every acceptance failure" is established. This is an acceptance/coverage
gap requiring contract analysis, not evidence of insufficient money or time.

### Astroid: delivered observation followed by repair

The first source edit inferred unpacked dictionaries before lookup. A candidate
helper returned the expected named value but observed `NameInferenceError` on an
uninferable name (sequence 157). Its program caught and printed the exception,
so exit 0 did not mean the desired behavior passed.

The actual request artifact at sequence 160 contains that output; provider
dispatch 164 has the same request hash. The next source edit (183-184) catches
inference failure and follows the lookup fallback. A third mutation (195-196)
adds two tests. The same helper replay then raised the intended exception class,
but formatting that exception caused a separate error (213). That traceback also
reached a counted/dispatched request (217/222).

The model used its last mutation on the tests; more diagnostics remained offered.
It ran the full required suite, passed, and disclosed the helper formatting error
and missing bound original reproduction at finish. The added test file is in the
suite's collection pattern, but only aggregate test output is retained, not an
individual result for each added test. Acceptance PASS does not establish that
the formatting error was repaired. This row demonstrates observation delivery
and a corresponding revision, without establishing a causal policy gain.

### Pyvista: public before/after observation

Before editing, an empty-diff helper called
`RectilinearGrid([0, 1], [0, 1], [0, 1])` and observed `TypeError` (85). Its output
reached the next actual request/dispatch (88/92). The single edit (96-97) permits
non-path sequences as well as ndarrays and normalizes axes with `np.asarray`.
After the public check (110-111), `replay_action_id` reran the same helper and
observed no constructor exception (125-128). Final acceptance was PASS.

This is actual public before/after evidence, despite the formal original
obligation remaining unverified. The helper did not assert grid coordinates,
dimensions, tuple input or the entire sequence-input contract. No new test was
added. Its scope is the observed three-list constructor call.

## Diagnostic labels and decision

All five collections retain `unverified_delivery` and unverified bound original
obligations. Those labels do not erase four independent acceptance successes or
Pyvista's real unbound before/after observation. Astroid's two helpers compare
candidate revisions, not an unchanged-base reproduction. The three remaining
rows have no helper observation. Required-check changed-line feedback was
`unknown / unsupported_python_options`; it cannot prove unexecuted edits.

Keep solver rules and budgets unchanged. This panel contains no output-budget
exhaustion, uncertain execution or repeated submission failure to justify another
budget increase or a new diagnostic gate. Optional execution was chosen on two
tasks, and both useful replay and feedback-driven revision occurred. The sole
acceptance failure deserves a focused public-contract/coverage analysis before
choosing any intervention; private test details must not become repair hints.
One sample per exposed issue cannot establish repeatability or superiority over
another agent/policy. Unused funds authorize no further run.

## Validation and evidence locations

No runtime/source change was made during or after the panel. Reuse the unchanged
runtime's recorded 33 focused and 923 quick PASS results, including isolated mock
smoke. The result-document change receives the five documentation tests and
`git diff --check`; this is not new runtime coverage. The five live evaluations
and separate read-only result/accounting audits are the new execution evidence.

Row journals and collections are under `C:/pt/repair-five-run-v1/<index>/`:

| Index | Run id |
|---|---|
| 1 | run_dev_0a5a4eaf7a2c4de8 |
| 3 | run_dev_e77ee2f5c8574891 |
| 10 | run_dev_2493a63f02844db0 |
| 11 | run_dev_67864cc929e648b1 |
| 15 | run_dev_5bc1cde5d495457b |

`results-summary.json` binds each collection, journal and submitted patch hash.
The plan's hash-chained `run_dev_repairfivepreparation` journal records direct
human approval, exact dispatch order, settlement, closure and operator audits.
