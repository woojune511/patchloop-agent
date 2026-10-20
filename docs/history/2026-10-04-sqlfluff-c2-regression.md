# SQLFluff C2 regression localization and public repair path

Date: 2026-10-04. Provider-free operator replay completed. Baseline retained;
no recognition diagnostic, runtime policy, submission gate or budget change.

## Selected problem and scope

The [closed ABC comparison](2026-10-03-probe-recheck-results.md) established that
SQLFluff-1733 C2 noticed the mismatch and revised its patch. The user explicitly
accepted that observation and asked to locate the first regression in the saved
candidates, then verify a repair against both the issue output and that regression.
Recognition and feedback delivery were not re-investigated. No model was resumed.

The source run is run_dev_8ae27bd1b3464578 under C:/pt/prlive01/1733C2. Its fourth
edit produced the issue's eight-space output but failed two public L036 tests,
exhausting the four-edit completion horizon without submission. The leading
explanation was that its indentation-copy condition applied to middle targets as
well as the first target. Replaying the exact earlier candidates could falsify the
claim that this last edit introduced the regression; narrowing that condition could
falsify the proposed repair if either public requirement still failed.

Independent external workspaces were created from the existing prepared public
base. Each saved replacement was applied using its recorded preimage, postimage
and cumulative diff hash. Original journals, candidates, task tests and expected
outputs were not edited. Existing image identities were verified; no image was
pulled or built. Checks used the existing independent full-output formatter program
and registered base-regression check over test/rules, on the same candidate hash.

## First regression and correction

| Candidate | Issue first-target indentation | Issue expected output | Public rule tests |
| --- | ---: | --- | --- |
| Public base | 9 spaces | FAIL | 506 PASS |
| After edit 1, L036 separator replacement | 9 spaces | FAIL | 506 PASS |
| After edit 2, L003 whitespace removal | 5 spaces | FAIL | 506 PASS |
| After edit 3, L003 hanging-indent guard | 5 spaces | FAIL | 506 PASS |
| After edit 4, L036 indentation copy | 8 spaces | PASS | 504 PASS, 2 FAIL |
| Edit 4 candidate plus first-target guard | 8 spaces | PASS | 506 PASS |
| Corrected L036 with original L003 restored | 8 spaces | PASS | 506 PASS |

The first regression is edit 4, action call_zN0LqyJqqeuRu9vKmLEvEMlW. Its condition
copies the later line's indentation whenever the next target is on a different
line. In the existing partially wrapped multi-target cases, that includes middle
targets c and g. L036 therefore adds two spaces to those targets, contrary to its
public tests' expected line-splitting behavior. Those tests explicitly preserve
existing indentation on already separate lines; they do not ask L036 to indent
every newly split target.

The two failing public case IDs are:

- L036_test_multiple_select_targets_some_newlines_missing_1
- L036_test_multiple_select_targets_some_newlines_missing_2

The local correction adds `i == 0` to the indentation-copy condition. The remaining
conditions still require the next target to be on a different line and a known
later-line whitespace segment. This retains the issue's first-target indentation
while avoiding new indentation for middle targets. Both checks then pass on the
same diff. Removing the earlier L003 edits also passes both checks, so those edits
are unnecessary within this tested scope; the smaller saved repair changes L036 only.

## Edit budget, execution policy and interpretation

| Path | Observed result | Interpretation |
| --- | --- | --- |
| Actual C2, four historical edits | Public regression failed; no submission | Original outcome remains unchanged. |
| Closed C2 candidate plus one operator edit | Issue and all 506 tests pass | A fifth-edit repair path exists with an operator-selected correction. |
| Historical prefix of three edits plus a revised fourth edit | Exact same repaired diff as the fifth-edit path | The solution is representable within four edits; the model did not execute this counterfactual path. Paired results are reused by exact source/diff identity. |
| A model run with a larger edit budget | NOT_RUN | Causal effect of increasing the model's budget is NOT_ASSESSED. |

The operator used exposed failure evidence and selected the correction. This is
not a fresh autonomous solve, an improvement score, or proof that one more model
edit would find the same repair. Extra-budget rescue and within-budget patch choice
remain separate questions. No provider or input-count calls were made; model cost
was USD 0. No private acceptance evaluation was run on the new candidates.

No new runtime execution policy is justified by this replay. The earlier candidates
had no registered regression for more frequent checks to expose, and the first bad
candidate was already checked and rejected in the original run. The useful change
is the narrower source condition, not a new recognition gate. For this operator
verification, the existing issue and regression checks ran against each unchanged
candidate; no new planner, state, tool, mandatory annotation or submission rule
was introduced.

## Evidence and validation

External immutable evidence: C:/pt/analyses/c2-regression-20261004-v1.

- driver.py and reduce.py preserve the exact operator reconstruction/check procedures.
- c0.json through c4.json and corresponding diffs bind the historical candidates.
- repair5.json/diff bind the one-extra-edit correction; replacement4.json records
  the equivalent revised-fourth-edit path without a redundant execution.
- l036only.json/diff and reduction.json retain the smaller one-file repair.
- result.json consolidates results and separates the budget interpretations.
- Hash-chained dev-run-v1 journals retain starts, source/environment bindings and
  content-addressed execution receipts. Workspaces are under C:/pt/c2reg01.

Historical final diff:
sha256:2cd0d145339894d6d133a19c77054e2acc66295b7203aee4d3f84f4255e176c5.
Corrected fifth/revised-fourth diff:
sha256:2c0c19ffbab7ea0eb9c6813e66792b805c7b34269e81b5924fb49e8e32030c59.
Reduced L036-only diff:
sha256:abeee4539143b264d7259dfeb31318adab3cec1dbba3e6fa7ce13a7427d4ed2f.

Seven candidates each received the full issue-output check and all 506 public rule
tests. Each pair took 39.060-40.656 seconds of recorded sandbox time, below two
minutes; the complete historical investigation took multiple such pairs. All
executions had complete output, no timeout and confirmed cleanup. Source journal
bytes and the historical final workspace diff were checked unchanged after every
pair. The historical NOT_RUN acceptance and closed ABC results remain unchanged.

This repository change records the investigation only. The verified SQLFluff patch
is an external artifact, not a PatchLoop runtime change or an upstream submission.
Closeout validation covers documentation layout/links and Ruff. PatchLoop's full
suite and mock smoke are not repeated because its runtime and tests are unchanged.
The remaining question is whether the agent can choose the narrow correction
within its existing limits; this operator replay does not answer it or authorize
another model run.
