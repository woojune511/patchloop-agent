# Portfolio v1 dev20 remeasurement: closed

## Requirement and fixed scope

Measure the current agent once on the original development-exposed dev20 before
spending on Lite test300, then finish repository-centered public evidence. The user
approved the exact frozen packet with “승인할게” after offline validation. No new
solver intervention was tested. A historical/current difference is descriptive,
not a causal feature effect or a statistically established performance change.

Execution commit: `59d90f6b5fbf1ff61f8b756a030b580e621e7c76`.
Historical commit: `3077f81afe3d85e301e3af99b09bf4c117425f52`.
Canonical packet hash:
`sha256:b275d168b095b3cba4b8e4dc4e284550b35802afe3c16527d571b2c184c1c0f3`.
The [preparation record](2026-10-05-portfolio-preparation.md) contains input matching,
validation and the separate byte-exact SQLFluff-1625 package. Its initially proposed
live path was already occupied by a closed older batch; the freeze rejected it.
The approved fresh replacement was `C:/pt/pv1d20live05`. Old state was preserved.

Twenty fresh solves, one per task, original order; model
`gpt-5.4-mini-2026-03-17`, xhigh, desired output 25,000; USD 1.20/task and USD 24
invocation-wide; 40 calls / 100 actions / 4 edits / 1,800 seconds per task.
Policies remained segmented-v1, result-or-size-v1, brief-v1, probes enabled with
policy none, repair-recheck, protected-v1, per-call-v1; saved-program recheck off.
No past patches, operator programs or closed diagnoses were supplied to the solver.
The existing registered evaluation and native harness revision
`02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` assessed the same original submissions.
No retries, resumes, replacements, budget transfers, image acquisition or remote
publication occurred.

## Results and decision

**9/20 resolved**, versus historical **10/20**. All twenty submitted and completed
both evaluations; twenty agreements and confirmed native cleanups; safety PASS
for all twenty. Non-submissions, infrastructure errors, evaluation disagreement,
unknown billing and unexecuted tasks: **0** each.

- PASS->PASS: 9; FAIL->PASS: 0; PASS->FAIL: 1; FAIL->FAIL: 10.
- The only changed outcome was pvlib #1707 (PASS->FAIL). No follow-up diagnosis was
  opened, and no internal causal explanation is inferred from that transition.
- Recorded model spend: **USD 3.46111455**, 204 settled generation calls.
- Panel start/end: 2026-10-05 13:30:03.264255 to 15:12:22.133090 UTC
  (2026-10-05 22:30 to 2026-10-06 00:12 KST).
- Panel wall time: **6,138.868835 seconds (102m19s)**. Summed solver invocations:
  5,587.366 seconds, including registered evaluation; additional native evaluation:
  466.989 seconds. Between-row validation/orchestration accounts for the remaining
  wall time. These are execution times, not human preparation or review time.
- All submitted diffs passed their configured public checks; that did not imply
  acceptance. Twenty-four public-check receipts are retained in the public export.

The complete result is below the **11/20 expenditure threshold**. Decision:
`CLOSE_WITH_DOCUMENTATION`. Test300 preparation and execution remain NOT_RUN.
No leftover allocation carries forward. Keep the runtime and default configuration;
do not tune prompts, rerun tasks or initiate per-failure diagnoses. Portfolio v1's
approved measurement and local material preparation are complete; publishing is
separate and unexecuted.

## Ordered comparison

All rows submitted; registered and native verdicts agree. Public check pass is
bound to each submitted diff. The patch links are local original evidence, not
hosted public downloads. Exact bases, patch hashes and public-check receipt
summaries are in the [portable result JSON](../../examples/portfolio-dev20/results.json).
Times are seconds; solve includes registered evaluation, native is additional.

| # | Task | Historical->current | USD | Solve s | Native s | Original |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | [marshmallow-code/marshmallow #1343](https://github.com/marshmallow-code/marshmallow/issues/1343) | PASS->PASS | 0.15808650 | 907.282 | 25.774 | [patch](C:/pt/pv1dev20/native/1/submitted.patch) |
| 2 | [pvlib/pvlib-python #1072](https://github.com/pvlib/pvlib-python/issues/1072) | PASS->PASS | 0.08147475 | 106.350 | 24.231 | [patch](C:/pt/pv1dev20/native/2/submitted.patch) |
| 3 | [pvlib/pvlib-python #1154](https://github.com/pvlib/pvlib-python/issues/1154) | PASS->PASS | 0.14473995 | 174.429 | 25.902 | [patch](C:/pt/pv1dev20/native/3/submitted.patch) |
| 4 | [pvlib/pvlib-python #1606](https://github.com/pvlib/pvlib-python/issues/1606) | PASS->PASS | 0.15361260 | 180.419 | 28.149 | [patch](C:/pt/pv1dev20/native/4/submitted.patch) |
| 5 | [pvlib/pvlib-python #1707](https://github.com/pvlib/pvlib-python/issues/1707) | PASS->FAIL | 0.13114470 | 156.104 | 28.474 | [patch](C:/pt/pv1dev20/native/5/submitted.patch) |
| 6 | [pvlib/pvlib-python #1854](https://github.com/pvlib/pvlib-python/issues/1854) | PASS->PASS | 0.04361730 | 62.607 | 29.027 | [patch](C:/pt/pv1dev20/native/6/submitted.patch) |
| 7 | [pydicom/pydicom #1139](https://github.com/pydicom/pydicom/issues/1139) | FAIL->FAIL | 0.07082970 | 92.544 | 19.899 | [patch](C:/pt/pv1dev20/native/7/submitted.patch) |
| 8 | [pydicom/pydicom #1413](https://github.com/pydicom/pydicom/issues/1413) | FAIL->FAIL | 0.16660425 | 195.448 | 20.593 | [patch](C:/pt/pv1dev20/native/8/submitted.patch) |
| 9 | [pydicom/pydicom #1694](https://github.com/pydicom/pydicom/issues/1694) | PASS->PASS | 0.05969175 | 82.147 | 20.085 | [patch](C:/pt/pv1dev20/native/9/submitted.patch) |
| 10 | [pydicom/pydicom #901](https://github.com/pydicom/pydicom/issues/901) | FAIL->FAIL | 0.12951480 | 174.002 | 20.683 | [patch](C:/pt/pv1dev20/native/10/submitted.patch) |
| 11 | [pylint-dev/astroid #1196](https://github.com/pylint-dev/astroid/issues/1196) | PASS->PASS | 0.13225530 | 214.676 | 19.780 | [patch](C:/pt/pv1dev20/native/11/submitted.patch) |
| 12 | [pylint-dev/astroid #1268](https://github.com/pylint-dev/astroid/issues/1268) | FAIL->FAIL | 0.12260280 | 158.390 | 20.492 | [patch](C:/pt/pv1dev20/native/12/submitted.patch) |
| 13 | [pylint-dev/astroid #1333](https://github.com/pylint-dev/astroid/issues/1333) | FAIL->FAIL | 0.18564510 | 223.384 | 19.050 | [patch](C:/pt/pv1dev20/native/13/submitted.patch) |
| 14 | [pylint-dev/astroid #1866](https://github.com/pylint-dev/astroid/issues/1866) | FAIL->FAIL | 0.04826460 | 106.505 | 26.551 | [patch](C:/pt/pv1dev20/native/14/submitted.patch) |
| 15 | [pyvista/pyvista #4315](https://github.com/pyvista/pyvista/issues/4315) | PASS->PASS | 0.18402735 | 269.023 | 29.266 | [patch](C:/pt/pv1dev20/native/15/submitted.patch) |
| 16 | [sqlfluff/sqlfluff #1517](https://github.com/sqlfluff/sqlfluff/issues/1517) | FAIL->FAIL | 0.30395175 | 404.582 | 21.095 | [patch](C:/pt/pv1dev20/native/16/submitted.patch) |
| 17 | [sqlfluff/sqlfluff #1625](https://github.com/sqlfluff/sqlfluff/issues/1625) | FAIL->FAIL | 0.54726375 | 893.732 | 25.818 | [patch](C:/pt/pv1dev20/native/17/submitted.patch) |
| 18 | [sqlfluff/sqlfluff #1733](https://github.com/sqlfluff/sqlfluff/issues/1733) | FAIL->FAIL | 0.61201740 | 758.407 | 20.328 | [patch](C:/pt/pv1dev20/native/18/submitted.patch) |
| 19 | [sqlfluff/sqlfluff #1763](https://github.com/sqlfluff/sqlfluff/issues/1763) | FAIL->FAIL | 0.12725190 | 214.906 | 21.328 | [patch](C:/pt/pv1dev20/native/19/submitted.patch) |
| 20 | [sqlfluff/sqlfluff #2419](https://github.com/sqlfluff/sqlfluff/issues/2419) | PASS->PASS | 0.05851830 | 212.429 | 20.464 | [patch](C:/pt/pv1dev20/native/20/submitted.patch) |

## Evidence and verification

- [Frozen manifest](C:/pt/pv1dev20/manifest.json),
  [approval](C:/pt/pv1dev20/authorization.json),
  [environment preflight](C:/pt/pv1dev20/preflight.json).
- [Raw batch result](C:/pt/pv1dev20/result.json),
  [summary](C:/pt/pv1dev20/summary.json),
  [post-run audit](C:/pt/pv1dev20/postrun-audit.json).
- Original per-task model/tool journals and CAS artifacts: `C:/pt/pv1d20live05/<index>/`.
  Public `run_check` receipts remain in each run journal. Each submission manifest
  and patch hash links the public result to its exact diff.
- Native receipts/logs/cleanup: `C:/pt/pv1dev20/native/<index>/output/`.
  The batch journal is `C:/pt/pv1dev20/runs/run_dev_portfoliodev20.jsonl`.
- [Public export](../../examples/portfolio-dev20/README.md) omits host paths,
  credentials, provider state and private evaluator contents. It records source
  hashes and transformations; it is not an independently reconstructed run.

Read-only post-run audit recomputed the aggregate, verified all native file hashes
and original patch identities, reconciled each unique provider call with recorded
cost, and checked current-diff public PASS and registered/native agreement for
all twenty. No solver or evaluator was called by this audit. The pre-execution
full suite (4,179 passed / 18 skipped), final focused checks (37 passed), Ruff and
mock receipts remain linked by the frozen validation packet. Final documentation,
local links and public-export hashes were checked separately; no runtime code was
changed after execution. Linux CI and unlisted environments remain NOT_RUN.

## Interpretation boundaries

Eight historical environment corrections and two public-check projections remain
part of the [original panel construction](2026-10-02-lite-dev20-results.md).
This is an exposed development panel, not Lite test300, not an official leaderboard
entry, and not evidence of training-data non-exposure. The old runtime was not
rerun. Lower spend alongside one fewer resolved task is a measured tradeoff in this
single comparison, not a general efficiency or quality claim.

The saved public-repair/demo materials retain their separate limitations and human
approval fields: benchmark acceptance does not approve those patches. UNSUPPORTED,
public-repair acceptance NOT_RUN, unexecuted environments and unproven crash
resilience are not changed by this measurement. No new development question is
opened automatically.
