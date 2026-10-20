# Mini/full completion-cost results

2026-10-04. Approved allocation closed; 24 fresh solves executed, official=false.
Execution commit: 09bc548a4ef23739dd8c4cac37502551744bbe87.
[Preparation](2026-10-04-mini-full-preparation.md) and
[frozen design](../../.agent/model-cost-comparison.md).

The question was whether mini improves cost versus completed repairs under the
existing runtime. Six prepared dev-train tasks cover four repositories and three
historical successes/three failures. Historical outcomes only selected the roster;
both models ran twice from fresh source/history/ledgers. Model was the only intended
condition difference. Both used xhigh, desired 25,000 output tokens, 40 model calls,
100 actions, four edits, 1,800 active seconds and USD 3 per solve. No operator
program or solution was injected. The exact USD 72 scope was approved by the user
with "승인할게"; authorization binds the frozen manifest, not prior approvals.

## Observed results

| Metric | mini: gpt-5.4-mini-2026-03-17 | full: gpt-5.4-2026-03-05 |
| --- | --- | --- |
| Fresh solves | 12 | 12 |
| Original acceptance PASS / FAIL | 6 / 6 | 4 / 8 |
| PASS by repetition | 3 / 3 | 2 / 2 |
| Unsubmitted / NOT_RUN / ERROR | 0 / 0 / 0 | 0 / 0 / 0 |
| Safety PASS | 12 | 12 |
| Settled cost USD | 2.28419415 | 3.138664 |
| Cost per accepted solve USD, including failed-run costs | 0.380699025 | 0.784666 |
| Sum of solve elapsed seconds, including evaluation | 2253.639 | 1830.051 |

| Task suffix | mini repetition 1 / 2 | full repetition 1 / 2 |
| --- | --- | --- |
| marshmallow-code-marshmallow-1343 | PASS / PASS | PASS / PASS |
| pydicom-pydicom-1694 | PASS / PASS | PASS / PASS |
| pylint-dev-astroid-1196 | PASS / PASS | FAIL / FAIL |
| pydicom-pydicom-1139 | FAIL / FAIL | FAIL / FAIL |
| pylint-dev-astroid-1268 | FAIL / FAIL | FAIL / FAIL |
| sqlfluff-sqlfluff-1517 | FAIL / FAIL | FAIL / FAIL |

Total settled spending was USD 5.42285815, below the USD 72 allocation. All 24 rows
were settled within their caps. The accounting audit matched row costs to 203
unique finished model calls (maximum 27 in one solve), found no unresolved counts
or dispatches, and reproduced the saved aggregate. No retry, resume, replacement,
budget transfer, model instruction change or extra paid call was made.

## Operating decision and limits

Select mini for this six-task development panel under the unchanged four-edit
settings. It met every predeclared condition: 3 versus 2 acceptances in each
repetition, no more unsubmitted solves, 27.224% lower total cost, 23.146% more elapsed
time (within the 25% ceiling), and safety PASS on all submissions. Cost per accepted
solve was 51.483% lower. The time result has only 1.854 percentage points of margin
to that operational ceiling; the slower execution remains part of the tradeoff.

The acceptance difference is two repetitions of one task, astroid-1196. This small,
development-exposed panel does not establish general model superiority or behavior
on other tasks. The general full-model baseline and CLI defaults remain unchanged.
The batch is closed; unused allocation does not authorize further work. No individual
failure diagnosis or follow-up experiment was created. C2 and pydicom-1413 remain closed.

## Reproducible evidence

External root: C:/pt/analyses/mini-full-20261004-v1/.
Manifest hash: sha256:9a086d4a3d439f536b2dce09cc4d57c8987eca48c250e422cadce6fb0885a1c0.
The root holds manifest.json, authorization.json, preflight.json, result.json,
summary.json, accounting-audit.json and the hash-chained run_dev_modelcostpanel
journal. Solve journals and submitted artifacts remain at C:/pt/mflive01/.
audit-results.py performs read-only aggregation/accounting checks and saves its
receipt once; it never executes a solver or evaluator. Preparation validation remains
at C:/pt/analyses/mini-full-prep-20261004-v1/validation.json. Runtime code is unchanged;
the post-run repository update only records the decision and evidence.
