# MontePy v2 public integer-test correction

Completed 2026-09-30. Provider-free development-task validation; official=false.
Follows the [integer conversion diagnosis](2026-09-30-montepy-index-diagnostic.md).

## Problem and change

The original public property test generated arbitrary Python integers, then lost
their integer type while inferring NumPy arrays. The original Fill setter correctly
rejected the resulting floats. This unrelated failure could obstruct the requested
Cell.universe repair.

Created `tasks/dev-train/original-montepy-933-v2`, retaining the same task ID and
incrementing its public/private version to 2. Version 1 remains byte-for-byte
unchanged. The repository, base, issue, scope and image are unchanged. Private
checks, assets and production reference bytes are unchanged; only private task
version metadata differs.

The public wrapper changes one test expression in its disposable source copy:
both arrays use `dtype=object`, preserving Python integer arithmetic. All original
assertions, unbounded Hypothesis strategies and both test modules remain active.
Five explicit examples cover signed maximum, the observed 2**63 failure, 2**64,
values below signed minimum and addition across signed maximum. Anchor mismatch
or ambiguity exits 2, classified as infrastructure failure before pytest dispatch.
No production code, submitted patch or prepared source is modified.

The first corrected public run passed but retained the original -rA output
truncation. Final v2 uses -ra to omit successful tests' captured output while
retaining failure/skip summaries. This changed reporting, not test selection or
the property. The earlier truncated receipt remains intact.

## Executed evidence

- Local package/wrapper/error-path tests: 11 passed. With documentation layout
  checks: 16 passed. Ruff passed over patchloop and tests.
- Final v2 public check on unchanged base: 44 passed; full output, exit 0,
  3,230 ms container receipt.
- Final v2 public check on production reference: 44 passed; full output, exit 0,
  3,364 ms container receipt.
- Inherited private check, operator-only: base exit 1 / FAIL; reference exit 0 /
  PASS, 3,221 / 3,380 ms. No private output or repair patch was sent to a model.
- Public issue reproduction on unchanged base: assigning None raises TypeError;
  deleting the property raises AttributeError. The requested defect remains.
- All final calibration receipts have no truncation, timeout or cleanup failure.
  No model call, image acquisition, dependency change or runtime change occurred.
- Separate CSV mock smoke reached isolated EVALUATOR_PASS with task acceptance
  PASS and safety NOT_RUN: `run_dev_a43fe9594ed94767` under
  `C:\pt\runs\montepy-v2-mock-20260930-v1`. Four mock calls, five tools, one edit,
  zero provider cost. This does not validate a MontePy agent solve or Docker safety.

Task-loader validation passes. Unit tests compare the inherited private data and
asset bytes, unchanged public issue/scope, disposable-only edits, and missing or
duplicate anchors refusing to dispatch pytest. The source workspace used for the
public issue reproduction remained unchanged.

Evidence roots:

- `C:\pt\analyses\montepy-public-check-v2-20260930-v1`:
  journal `run_dev_montepypublicv2`, initial public result and original issue reproduction.
- `C:\pt\analyses\montepy-public-check-v2-calibration-20260930-v1`:
  journal `run_dev_montepyv2calibration`, final task hash and base/reference receipts.

Both roots use append-only dev-run-v1 journals and immutable artifact hashes.
Private calibration workspaces remain operator-only; never reuse them for an agent.

## Decision and limits

The observed public-check obstruction is corrected in a separate development
version. The one base/reference calibration preserves the expected distinction.
It does not prove stability for every generated input, an agent quality gain or a
runtime safety verdict. A full repository regression and live agent run were not
part of this bounded task-package check; CI remains separate evidence.

Use the reviewed v2 package for any subsequently authorized MontePy exercise;
the existing public source/dependency descriptors remain applicable because the
upstream source identity did not change. Revalidate them before execution. Do not
resume a v1 run under v2 or reinterpret prior results as v2 evidence. No paid
allocation is opened by this work.
