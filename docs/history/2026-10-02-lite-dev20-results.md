# SWE-bench Lite dev20 baseline results

Date: 2026-10-02. Execution head `3077f81afe3d85e301e3af99b09bf4c117425f52`.
Both exact-head Ubuntu and Windows fast-dev-head CI passed before dispatch.
Every run is official=false and claim-ineligible. The allocation is closed.

## Question and decision

The three-task mini pilot resolved one task. Its fixed twenty-task dev-split
remainder was selected to measure the unchanged agent across the rest of the
available development panel, rather than choosing only promising cases. Package
calibration had removed known evaluation-environment blockers before execution.
See [registration](2026-10-02-lite-dev20-registration.md) and the
[closed execution plan](../../.agent/swebench-lite-dev20-batch.md).

The user approved one sequential fresh solve per task with
`gpt-5.4-mini-2026-03-17`, xhigh, 25,000 output tokens, USD 1.20 per task and USD 24
total. Policies and 40-call/100-action/four-edit/1,800-second per-task limits stayed
fixed. There were no retries, replacements, resumes, added images or post-result
solver interventions. The credential remained in the approved local file, outside
all solver/evaluator context and logs.

The result establishes an operational baseline: 20 submitted patches, ten original
hidden-evaluation successes and ten failures. All final public regressions and
safety checks passed. Final acceptance agrees in all twenty registered and native
original evaluations, with every required test represented. The leading remaining
question concerns incorrect repairs that pass public checks, rather than an
observed infrastructure failure in this completed batch. A shared cause is not yet
established: incomplete requirement interpretation, repair logic and insufficient
verification remain hypotheses to distinguish through the public traces.

Keep the baseline. This measurement neither tests a particular mechanism nor
justifies a new prompt/tool intervention. No additional paid run is queued.

## Results

| Measure | Observed |
| --- | --- |
| Attempted / completed / submitted | 20 / 20 / 20 |
| Original hidden resolved | 10 / 20 |
| Registered/native verdict agreement | 20 / 20 |
| Final public regression PASS | 20 / 20 |
| Safety PASS | 20 / 20 |
| NOT_RUN / infrastructure or billing uncertainty | 0 / 0 |
| Model calls / input-count calls | 245 / 251 |
| Settled cost | USD 5.01124395 |
| Sum of per-task solve times | 4,703.530 seconds (78m 23.530s) |

Solve time includes per-task agent execution and registered evaluation; it excludes
CI waiting, prior calibration and the subsequent original-native evaluation.

All rows below submitted, passed final public regressions and safety, and received
a complete original-native result that agreed with the registered result.

| Instance | Original resolved | Model calls | USD | Solve seconds |
| --- | --- | ---: | ---: | ---: |
| marshmallow-code__marshmallow-1343 | PASS | 11 | 0.20549610 | 130.556 |
| pvlib__pvlib-python-1072 | PASS | 5 | 0.05904045 | 52.711 |
| pvlib__pvlib-python-1154 | PASS | 10 | 0.17880435 | 152.339 |
| pvlib__pvlib-python-1606 | PASS | 5 | 0.09856320 | 83.731 |
| pvlib__pvlib-python-1707 | PASS | 8 | 0.17888040 | 152.891 |
| pvlib__pvlib-python-1854 | PASS | 5 | 0.09364725 | 91.705 |
| pydicom__pydicom-1139 | FAIL | 8 | 0.11702355 | 83.031 |
| pydicom__pydicom-1413 | FAIL | 11 | 0.18829920 | 146.037 |
| pydicom__pydicom-1694 | PASS | 5 | 0.04838250 | 59.244 |
| pydicom__pydicom-901 | FAIL | 9 | 0.18246090 | 167.437 |
| pylint-dev__astroid-1196 | PASS | 10 | 0.14570325 | 134.428 |
| pylint-dev__astroid-1268 | FAIL | 10 | 0.15791235 | 131.010 |
| pylint-dev__astroid-1333 | FAIL | 35 | 0.56343060 | 366.972 |
| pylint-dev__astroid-1866 | FAIL | 5 | 0.06107460 | 86.833 |
| pyvista__pyvista-4315 | PASS | 5 | 0.11260260 | 122.864 |
| sqlfluff__sqlfluff-1517 | FAIL | 24 | 0.35719980 | 321.880 |
| sqlfluff__sqlfluff-1625 | FAIL | 35 | 1.07266485 | 1142.948 |
| sqlfluff__sqlfluff-1733 | FAIL | 22 | 0.83133450 | 769.076 |
| sqlfluff__sqlfluff-1763 | FAIL | 16 | 0.29217750 | 332.362 |
| sqlfluff__sqlfluff-2419 | PASS | 6 | 0.06654600 | 175.475 |

## Interpretation and limits

Failures recur across pydicom (three of four), astroid (three of four) and sqlfluff
(four of five); this table does not diagnose their mechanism. Public-check success
alone was insufficient for ten submitted patches. Prioritize a comparison of the
failed public task/source/action/check traces before choosing another intervention;
private test content must not become repair guidance for a subsequent solver.

The twenty packages were calibrated with known-reference controls before these
fresh solves. Twelve use original images and eight use pinned, previously verified
derivative images. Two pvlib tasks use the documented public regression projections
that remove expectations contradicted by their public issues. Original hidden tests,
reference patches and grading stayed unchanged. These conditions limit comparability
with an unmodified benchmark harness and must accompany any descriptive result.

This is an exposed development split, not the 300-task test split or a held-out
accuracy estimate. There is no A/B control, model comparison or causal evidence for
memory, probes, prompts or planning. The earlier three-task pilot remains 1/3 at
USD 0.29098320; a descriptive combined dev total would be 11/23 at USD 5.30222715,
not a uniform official benchmark score. Do not pool calibration/reference replays
with these fresh agent solves.

## Evidence and validation

External root: `C:/pt/analyses/lite-dev20-registration-20261002-v1`.

- `manifest.json` and `preflight.json`: frozen task/source/image/model/resource
  scope, exact clean tracked execution bytes, runtime and driver identities.
- `runs/run_dev_litedev20cigate.jsonl`: explicit human approval and exact-head CI.
- `runs/run_dev_litedev20live.jsonl`: one-shot allocations, settled costs and
  invocation completion. Child journals are under `C:/pt/ld20live01/1` through `/20`.
- `predictions.jsonl`: all twenty exact submitted diffs in original prediction format.
- `native-summary.json` and `C:/pt/ld20native01`: original-native test outcomes,
  original evaluation logs, and confirmed cleanup of all twenty owned containers.
- `summary.json` and `runs/run_dev_litedev20audit.jsonl`: reconciled per-task
  outcomes, usage, costs, elapsed times, patch identities and evidence checks.

Final audit revalidated twenty task hashes and child journal chains, matched all
submitted patches to predictions, reconciled provider-settled costs and call counts,
and verified 231 final artifact references. Runtime, execution head, image and task
identities match their frozen receipts. No unresolved provider/count operation or
owned native container remained. Final public regressions and original required
case presence are established by executed evidence, not inferred from submission.

This follow-up changes documentation only. Runtime/package source remains at the
executed baseline. Historical records and all original failure evidence are preserved.

Reconciled summary content hash: `sha256:647846ac463d7cf090395de6c37aa282b413a7debf6c12c6eaa1ae3491be7fa0`.
