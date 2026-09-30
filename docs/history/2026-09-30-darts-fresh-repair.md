# Darts fresh repair: acceptance failure and public mapping regression

Completed 2026-09-30 on head `ac8655a7` under the user-approved
[single-invocation scope](../../.agent/next-darts-repair.md). Allocation closed.
official=false, claim_eligible=false. No retry, continuation or second model run.

## Run result

Task `original-darts-3065`, version 1, dev-train; original upstream source and
selected working baseline unchanged. Model gpt-5.4-2026-03-05, xhigh, desired
25,000 output tokens; one invocation, USD 3.00 cap and 1,800-second limit.

| Measure | Result |
| --- | --- |
| Terminal / isolated acceptance | EVALUATOR_FAIL / FAIL |
| Evaluator safety state | PASS |
| Failure class | PRIVATE_EVALUATION_FAILED |
| Registered public regression | 8 passed, full output, confirmed cleanup |
| Model / input-count calls | 7 / 7 |
| Tool actions / accepted edits | 8 / 1 |
| Submitted scope | static_covariates_transformer.py only; 71 added / 15 deleted |
| Active elapsed time | 343.782 seconds |
| Usage-accounted cost | USD 0.607473 of USD 3.00 |
| Optional probe calls | 0 |

The patch groups encoder output names by the longest matching input-column name
prefix, with a dropped-category fallback, to construct forward/inverse column
maps. After one edit the agent ran the public regression and submitted. Public
changed-line feedback was unknown/report_unavailable; no branch-coverage claim
follows from the public PASS.

## Provider-free public diagnosis

Without reading hidden test or reference-patch content, froze four public
transform/inverse-transform roundtrips and ran them on independent base and
submitted-patch workspaces. Used the existing registered-check image/interpreter
(scikit-learn 1.8.0), not the separate prepared probe environment (1.9.1).
The same version and source base were used in both replay arms.

| Public case | Base | Submitted patch |
| --- | --- | --- |
| One column, three categories, no drop | Roundtrip PASS | Roundtrip PASS |
| Same column, drop="first" | Transform IndexError | Roundtrip PASS |
| Overlapping column names, no drop | Roundtrip PASS | Inverse result loses a column |
| Overlapping column names, drop="first" | Roundtrip PASS | Inverse result loses a column |

Overlap inputs are columns `c` with values `[a, a_x, a]` and `c_a` with values
`[u, v, u]`, attached to a deterministic three-component TimeSeries. Both failing
inverse results have shape (3, 1), while the original static covariates have shape
(3, 2). Output names such as `c_a_x` match the longer `c_a` prefix even when
generated from column `c`; display-name parsing loses feature ownership.

The submitted patch repairs the reported ordinary first-drop case but introduces
a concrete public roundtrip regression. This is not proof that the same cases
explain the entire private failure. The diagnostic was constructed after the run
from public APIs and the submitted patch; it was never delivered to that agent.
Both diagnostic processes exited successfully with complete observations, no
timeout/cleanup failure, and unchanged before/after patch identities.

## Accounting and evidence

All seven provider responses completed with matched input counts and no reported
transport/usage uncertainty. Their costs sum exactly to USD 0.607473. This is
usage-based accounting, not an independently reconciled invoice. The hash-chained
109-event journal, six terminal artifact hashes and seven actual inputs verified.
Prepared source remains unchanged. Preparation metadata and host paths were absent
from actual model inputs. No image acquisition/build or additional provider call.

Run root: `C:\pt\runs\darts-next-repair-20260930-v1`;
run ID `run_dev_d9f3c8ef78484e12`.
Operator scope, frozen public replay, receipts and review:
`C:\pt\analyses\darts-fresh-repair-20260930-v1`, append-only journal
`run_dev_dartsfreshaudit`. Private verdict/provenance remain outside agent input.
Submitted patch hash:
`sha256:91ec17474c12305f1f70259a4c6848131310d394a73949907b5537bc603565a5`.
Run journal tail:
`sha256:6ef0e1077cff9c1370921e2958634dbca791285490c3db3aa1d3b5378b3e6278`.

## Next decision

Do not start another paid solve or add a prompt/memory rule from this one result.
The next useful bounded question is how to preserve per-input-feature output
ownership without inferring it from display-name prefixes, while retaining the
original first-drop repair and both overlap roundtrips. Any later seeded repair
must be distinguished from this failed fresh run; do not rewrite its outcome.
No task, runtime or submitted agent patch was changed during diagnosis. Only
current guidance and this result record change; runtime regression/mock smoke are
not rerun for documentation. This exposed task is not general-performance evidence.
