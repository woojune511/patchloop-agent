# MontePy public-check integer conversion diagnostic

Completed 2026-09-30. Provider-free operator diagnostic; official=false.
No task, agent runtime, public test, dependency or image was changed.

## Problem and competing explanations

The [repair preparation](../../.agent/next-montepy-repair.md) found a failure on
unchanged base `fbc03d10eb552cf82acc788ef70d120adec8130c` in the registered public
`TestFill.test_fill_index_setter` check. Its generated indices were `[0, 0, 0]`
and widths `[1, 1, 9223372036854775808]`; the setter rejected `1.0` as noninteger.
The original check output was truncated; retain that limitation.

Candidate explanations were conversion of generated integers by NumPy, an integer
range limitation in the Fill setter, or environment/version behavior. The task's
requested `Cell.universe` nullification behavior was not part of this failure.

## Frozen diagnostic

One container execution exercised six predetermined cases using the public
`TestFill.setup_method` fixture and unchanged setter. It did not run Hypothesis
search or repeat pytest until green. For each case it recorded operand/result
dtypes, values, element types, Integral membership and setter outcome.

Used the registered check's `/opt/conda/envs/testbed/bin/python`, environment and
existing image
`sha256:d79f83f33b0f25749596dd0038adecb80e9b443300200890dca0f6d23488567c`.
DockerSandbox supplied network isolation, read-only mounts/root, bounded resources
and owned-container cleanup. No private task files or evaluator checks were read.
The diagnostic is operator evidence, not a new registered task check.

## Result

Observed environment: Python 3.13.13, NumPy 2.4.5, Hypothesis 6.152.7.
All cases used zero minimum indices.

| Width/input construction | Width dtype | Result dtype | Original setter |
| --- | --- | --- | --- |
| `[1, 1, 2**63]`, original NumPy expression | float64 | float64 | TypeError on 1.0 |
| `[1, 1, 2**63 - 1]`, original expression | int64 | int64 | Accepted, preserved |
| `[1, 1, 2**64]`, original expression | object | object | Accepted, preserved |
| Exact failing values, Python list arithmetic | list | list | Accepted, preserved |
| Exact failing values, explicit object arrays | object | object | Accepted, preserved |
| Small `[1, 1, 2]` result explicitly cast to float | int64 | float64 | TypeError on 1.0 |

For the exact failure, type loss occurs at `np.array(width)`, before addition.
The setter consistently enforces its Integral validator: it accepts the exact
large integers when preserved and rejects even small floats. This resolves the
observed failure as a mismatch between the public test's unbounded integer domain
and its inferred NumPy dtype. It does not establish a NumPy regression across
versions, correctness of all Fill behavior, or a failure of an agent repair.

## Evidence and validation

External root: `C:\pt\analyses\montepy-index-diagnostic-20260930-v1`.
Append-only dev-run-v1 journal: `run_dev_montepyindexdiagnostic`, four events,
with content-addressed frozen program, full receipt and six-row summary.
Source was recreated from the verified preparation descriptor; the independent
workspace had no tracked or untracked changes after execution.

An initial operator setup used the wrong constructor field `check_id` instead of
`id`. Validation rejected it before container dispatch. The journal preserves the
correction; the frozen diagnostic program did not change. Exactly one diagnostic
container ran: exit 0, 1,779 ms, no truncation, timeout or cleanup failure.
Model calls zero; acceptance and safety NOT_RUN. No private evaluation, full-suite
rerun, paid invocation or runtime/mock regression was needed for this diagnosis.

## Decision and next question

Keep paid MontePy execution blocked. The appropriate next change is a separately
reviewed development-task revision that preserves exact integer arithmetic in this
public property test, with deterministic boundary controls. Retain the original
package/evidence and its existing result; do not silently alter the baseline.
Do not make Fill accept floats, drop the property test, narrow its generated domain
or pin dependencies merely to suppress this failure.

Before admitting the revised task, establish that its original base can run the
corrected public regression check and that the requested universe-nullification
failure remains distinguishable. This diagnostic supplies neither a repaired
agent patch nor live-run authorization.
