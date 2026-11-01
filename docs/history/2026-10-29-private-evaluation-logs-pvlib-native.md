# Private evaluation logs and saved pvlib native reassessment

## Material Passport

- Workflow: academic-research-suite experiment-agent, local execution/validation.
- Status: LOCAL_EXECUTED; two saved patches reassessed, no new solver run.
- Task: dev-train current-dev20/5, pvlib-1707; official=false, claim-ineligible.
- New provider calls: zero. No credential file loaded, image pulled or built.
- Operator artifacts: `C:/pt/pvlib-native-reevaluation-v1/`.
- Private assertion details remain in that operator directory, not this guidance,
  public tasks, solver requests, working notes or repair-feedback paths.

## Problem and decision

The [public-only comparison](2026-10-29-pvlib-saved-candidate-comparison.md)
could distinguish some candidate behavior but could not establish which assertion
caused B's historical acceptance failure. The registered oracle already uses
original SWE-bench test patches, commands and grading. Its wrapper discarded raw
test stdout/stderr with its temporary directory, leaving only the grading report.
This was a concrete observability defect, not evidence of a stricter custom oracle.

The user authorized preserving private diagnostics and reassessing the saved A/B
with upstream SWE-bench, while prohibiting new model calls or solver reinjection.
The smallest discriminating test was the same two source patches in the existing
pinned image. An incomplete native execution or disagreement would have weakened
the proposed patch-level explanation and stopped the comparison without retry.

## Change

`diagnostics/swebench_lite_oracle.py` now includes bounded private stdout/stderr in
its evaluator receipt for normal results, patch failure, timeout and grading
failure. Each stream retains its final 24,000 bytes, full-stream hash and explicit
omission count. Native evaluation retains full output files and an exclusive
hash/size manifest, including unsuccessful outcomes. Verdict rules remain the same.

The 20 active current-dev20 adapter copies and their declared hashes were updated;
their oracle and reference files remained byte-identical. Historical packages,
saved patches and closed records were not edited. New task identities invalidate
old prepared execution packets. No solver behavior, budget or submission gate was
changed. Existing CAS storage retains the operator receipt; evaluator completion
still has `agent_context_reinjected=false` and no diagnostic body in its summary.

## Executed comparison

`plan.json` binds original full-patch hashes, source-only projections, the existing
image, upstream harness revision `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`, runner
hash, A/B order, one execution each and stop conditions. Added candidate tests were
integrity-checked and preserved with the full patch, then excluded from native
grading. Original benchmark test patches and scoring were not modified.

| Saved arm | Native result | Repair cases | Existing cases | Elapsed |
|---|---|---|---|---|
| A | PASS, complete | 1/1 pass | 30/30 pass | 37.929 s |
| B | FAIL, complete | 0/1 pass | 30/30 pass | 28.180 s |

Both results match historical registered acceptance. All 31 required cases were
reported; container cleanup was confirmed. The detailed B assertion and its
connection to the saved branch condition are recorded in `operator-analysis.md`
and `analysis.json`. The earlier boundary suspicion is now linked to an actual
benchmark failure. It does not establish that A/B policy caused the different code.

The original native setup script attempted a dependency install with networking
disabled; that step reported a build-dependency download error in both arms. The
existing preinstalled environment nevertheless executed all 31 required tests,
and upstream grading reported no infrastructure failure. This is a reassessment
in the existing pinned offline image, not a claim that fresh environment setup
would succeed. Full setup output is retained rather than suppressed or repaired.

## Validation and limits

Validation results and hashes are in `validation.json` under the operator root:
33 focused tests PASS in 7.190 seconds; 923 quick tests PASS in 123.273 seconds;
Ruff and `git diff --check` PASS. All 20 active packages load with matching hashes.
Focused tests cover pass/fail/error output, timeout bytes, explicit clipping,
native full-log manifests and retained-private-log isolation from actual mock
solver requests. Quick includes isolated mock evaluation; Ruff and documentation
checks cover the changed code and current contracts.

The append-only `dev-run-v1` journal binds preparation, both native receipts and
analysis. Historical journals and submitted patches remain unchanged. This closes
the saved B failure-cause question. It provides no new repair, policy adoption,
held-out result, population estimate or general improvement claim. The next live
study, if requested, must not import these private diagnostics into the solver.
