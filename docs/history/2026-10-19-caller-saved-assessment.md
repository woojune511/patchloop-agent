# Saved caller assessment: storage fix and separate local evaluation

Date: 2026-10-19 KST. Operator-only, provider-free follow-up to the
[stopped caller A/B study](2026-10-19-caller-uptake-results.md).
The original Astroid-1333 panel assigned six solves per arm with
`gpt-5.4-mini-2026-03-17`; this follow-up uses only its ten saved submissions.

The post-processing storage defect is fixed, and all ten saved submissions have
now received separate local native evaluation: ten FAIL, matching their original
registered FAIL. Both public caller cases were executed once for each submission.
Nine retain the original missing-initializer failure; A4 crashes in that caller
and retains ERROR. All ten pass the initializer-present control. After A4 stopped
the first follow-up, the user explicitly authorized only the unexecuted slots in
a separate record. **All authorized slots are accounted for; the frozen oracle
remains incomplete because A4's ERROR is preserved.** No outcome, stop or pre-grade
audit label was rewritten.

## Selected problem and repair

The original frozen assessment failed before its first probe. It attempted to
write `assessments/<row>/source-only.patch` through an ArtifactStore rooted at
`artifacts/`. The store correctly rejected a path outside its root. The correction
uses the owning assessment folder as the store root, keeping containment checks
and atomic writes unchanged. A regression test traverses actual Git diffs and
real ArtifactStore writes instead of replacing the storage boundary with a fake.
The earlier assessment test stopped at the unsealed-audit rejection and never
exercised that first derived-file write; the new tests cover the successful path,
tests-only projection, caller ERROR, acceptance disagreement and original-file
preservation with only sandbox/native execution replaced.

Preflight also found that B3 changed only tests. Restoring original tests leaves
an exactly empty source projection, which the native prediction loader previously
rejected. The saved-submission operator now passes an explicit
`--empty-source-projection` flag for this case. It leaves source unchanged and
runs the full native assessment. Ordinary empty predictions, whitespace patches,
missing predictions and invalid submission lineage remain rejected. B3 actually
completed the native assessment as FAIL; empty source receives no success credit.

Implementation commit: `b3666b87b89600860fea08aef4809af02dc28108`.
The [operator contract](../../.agent/caller-uptake-followup.md) and
`diagnostics/caller_uptake_followup.py` define a fresh output root, exact saved
submission count, frozen input validation and explicit local authorization. The
original `assess` entry still refuses a retry. Only the assessment execution and
native wrapper may differ from the old implementation bindings; the task, oracle,
programs, dependencies, images and installed native harness must match.

## Executed scope and preserved boundaries

The user authorized fixing post-processing and separately evaluating the ten saved
submissions. No new solve, continuation, model judge, provider call or input count
was invoked. Additional paid cost is USD 0; the original USD 7.10243790 remains a
closed allocation. No image was pulled or built.

The new manifest binds the original packet hash
`sha256:9beb906624af117c098d93334268744c47021ee3a0a29eb6b5997a947ef7e7cb`,
original solve commit `b6be08e6ed439141bffc5bced532f5c97586545d`, and the repaired
operator commit separately. Runtime content remains
`sha256:90f3b4f2467cb802e89bd27997e69bc8233e041db18105c7f0a557b5586693f7`.
Transition rules, two references, 24,000 retained characters and all solver/probe
budgets are unchanged. Two caller cases and native assessment share 600 seconds
per submitted row; probe timeout stays 30 seconds and native tests 300 seconds.

Original submitted artifacts were read and verified against their durable
evaluation completion and exact workspace diff before execution. Original tests
were restored in a separate public checkout; submitted and source-only hashes
remain distinct. Both arms were assessed in the frozen common B environment with
the original missing/present programs and unchanged grading rules.
Only B3 and A6 had additive test edits omitted by this fixed projection: B3's
`tests/unittest_manager.py` leaves no source change; A6's
`tests/unittest_builder.py` is omitted while its 814-byte source patch is retained.
Their submitted artifacts remain intact, and the receipt set binds both hashes.

The original packet/journal, pre-grade audit and historical report are untouched.
The original journal still ends at event 67, `assessment_stopped` with RecoveryError,
and has no fabricated `result.json`. The separate local assessments have their own
hash-chained journals, manifests, stop record and receipt verification.

## Observed results

These are saved-patch results, not extra fresh trials. The two unsubmitted rows
remain NOT_RUN. All submitted patches already had registered FAIL and safety PASS.

| Original row | Submitted | Missing-init caller | Present-init control | Native |
| --- | --- | --- | --- | --- |
| A1 | yes | FAIL | PASS | FAIL |
| A2 | yes | FAIL | PASS | FAIL |
| A3 | no | NOT_RUN | NOT_RUN | NOT_RUN |
| A4 | yes | ERROR | PASS | FAIL |
| A5 | yes | FAIL | PASS | FAIL |
| A6 | yes | FAIL | PASS | FAIL |
| B1 | yes | FAIL | PASS | FAIL |
| B2 | yes | FAIL | PASS | FAIL |
| B3 | yes, tests only | FAIL | PASS | FAIL |
| B4 | yes | FAIL | PASS | FAIL |
| B5 | yes | FAIL | PASS | FAIL |
| B6 | no | NOT_RUN | NOT_RUN | NOT_RUN |

Executed across the two separate records: 20 unique caller probes, comprising
nine FAIL, ten PASS and one ERROR; ten unique native assessments, all FAIL and
agreeing with registered evaluation. All executed containers have confirmed
cleanup. No retry occurred. Rows used 37.30-56.90 seconds of their shared
600-second allowance, including A4's conservative charge for its earlier probe.

A4's patch returns `_build_namespace_module` when a missing `__init__.py` belongs
to an existing directory. The saved public traceback shows Pylint raising
`AttributeError: __enter__` while tokenizing that module, followed by
`FileNotFoundError` when its crash-report path opens `src/project/__init__.py`.
All nine setup comparisons passed; the probe finished in 7.730 seconds, without
timeout, truncation, deadline exhaustion or cleanup failure. It emitted only
`before_call`, not the final `result` record. The frozen observer catches
SystemExit but does not catch this exception chain.

This is an observed candidate/caller crash and an incomplete oracle observation,
not a recurrence of the storage defect or evidence of an infrastructure outage.
The strict grade remains ERROR, not a retroactive FAIL. The program, parser and
submitted patch were not changed after observing it.

The pre-grade evidence-use labels remain identical: each arm has zero YES, five
NO_OBSERVED and one UNKNOWN for both source and execution uptake. The new operator
observations were never available to the original solver and cannot change those
labels. Each arm has zero native successes out of five saved submissions; retaining
the original intended denominator gives zero confirmed S/T/Q successes out of six
assigned solves per arm. S requires registered/native PASS agreement, T requires
both public caller cases to PASS, and Q requires both S and T. These are success
counts, not a claim that every caller outcome is fully classified: A4's
missing-input ERROR remains unresolved, and the
frozen aggregate has `complete=false` and `favorable_local_signal=false`. A3 and
B6 remain unsubmitted, not fabricated native failures.

The saved public receipts distinguish the symptom from the adoption question.
Every classified missing-input case exits 1 with F0010 and never analyzes the
child module; every present-input control exits 0, analyzes the child and has no
F0010. Native evaluation independently finds no repaired submission. The pre-grade
audit separately finds no qualifying use of the new caller evidence by the model.
Thus this panel supplies neither observed evidence-use improvement nor repair
improvement. It cannot establish whether correct use of that evidence would have
helped, or whether obtaining evidence versus subsequent judgment is the dominant
general limitation. No adjacent paid comparison or runtime change follows from
these negative saved-patch results.

## Authorized remaining slots and validation

The fixed execution rule, `caller assessment uncertain; stop remaining`, stopped
the first follow-up on A4's ERROR. The user then explicitly approved executing only
the seven unexecuted caller cases and four unexecuted native assessments in another
separate record. This narrowly approved exception does not rerun or reclassify A4's
failed input. Its conservative consumed allowance is 12 seconds, leaving 588
seconds; the other pending rows keep 600 seconds. Cumulative ceilings remain 20
caller probes and ten native assessments, with no provider calls. The continuation
retains the stop rule for any new ERROR, uncertain cleanup or acceptance disagreement.

The one-off operator `C:/pt/callerfollowup19/continue_remaining.py` binds the exact
stopped journal, receipt set and permitted slots in `evaluation-v2/manifest.json`.
A positive selection control and five rejection controls confirm that previously
observed cases, native reruns, extra cases and resetting either representation of
A4's consumed time cannot enter that scope. These controls executed no evaluations.
The repaired repository code stayed frozen at the same implementation commit.
The remaining seven caller cases and four native assessments all completed without
a new ERROR or registered/native disagreement. A4's present-input control passed
and its native assessment failed; its original missing-input receipt was not run
again. The continuation records `assessment_slots_accounted=true` separately from
the frozen oracle's `complete=false`.

Validation at the implementation commit:

- Focused regressions plus documentation checks: 91 passed in 25.06 seconds.
- Ruff: PASS for runtime, tests and the changed operator modules.
- Mock smoke: EVALUATOR_PASS through isolated evaluation; mock safety NOT_RUN.
- Full repository suite: 5,350 passed, 20 skipped in 6,579.48 seconds (1:49:39),
  with four workers, `--dist loadfile` and `--max-worker-restart 0`. Exit code 0;
  JUnit totals and the completion log agree. The final documentation commit
  changes no implementation or test bytes from the tested code commit.
- Receipt verification: all 20 public grades reclassified identically from saved
  bytes; all ten native receipt sets, source projections, prediction bytes,
  matching registered results and cleanup were verified without another
  evaluation. Exactly 20 distinct row/case keys and ten distinct native row keys
  are present. Original audit/input and user AGENTS.md hashes match their pre-run
  identities. A final read-only admission check also verified all ten original
  submitted artifacts and workspace diffs after the continuation.

## Evidence

External root: `C:/pt/callerfollowup19/`.

- `evaluation-v1/manifest.json`: authorization, original and repaired identities,
  exact ten submitted artifacts, original inputs and unchanged budgets.
- `evaluation-v1/runs/run_dev_callersavedassessment.jsonl`: executions, six finished
  rows, A4's ERROR, stop, and original-evidence preservation.
- `evaluation-v1/assessments/`: exact source-only patches, public receipts and
  isolated native receipt sets. No private evaluator contents entered the audit.
- `stopped-v1/result.json`: all twelve original rows and the exact unexecuted slots.
- `stopped-v1/verification.json`: independent hash/grade verification without reruns.
- `assessment-console.log`, `assessment-exit.json`: retained stop and nonzero exit.
- `evaluation-v2/manifest.json`: the user's exception for only the seven caller
  cases and four native assessments not previously executed, with consumed time
  bound to the stopped journal.
- `evaluation-v2/runs/run_dev_callersavedremaining.jsonl`: remaining executions,
  unchanged earlier observations and original-evidence preservation.
- `evaluation-v2/result.json`: combined row outcomes and separate completion axes.
- `remaining-console.log`, `remaining-exit.json`: continuation completion, exit 0.
- `validation/remaining-selection-v2.json`: one positive and five rejection
  controls for the exact unexecuted slots and remaining allowance.
- `combined-verification.json`: independent verification of all 20 caller and ten
  native observations, unchanged audit labels, lineage and original inputs.
- `original-preservation-final.json`: final verification of all ten original
  saved submissions and workspace diff identities; no additional evaluations.
- `validation/final.json`: focused, Ruff, mock and full-suite results bound to
  the tested implementation commit, with exact log and JUnit hashes.
- `closeout.json`: final documentation commit, source equality, documentation
  checks and the separate assessment/verification records.

The original frozen study, stopped follow-up and authorized continuation remain
separate evidence.
All work is official=false and claim-ineligible; no default change, quality gain,
causal mechanism claim, extra model execution or new paid allocation is authorized.
