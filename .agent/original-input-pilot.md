# Original-input pilot v1

## Purpose and fixed sample

Measure fresh single-attempt development performance with original issue text and
original benchmark scoring. This is a three-task pilot, not a general performance
estimate or a held-out claim. AnyIO is calibration-only and excluded from scoring.

Dataset: `nebius/SWE-rebench-leaderboard`, revision
`ab4805dae879e4f4ef81bf9e5cf5afa849f7c55b`, split `2026_03`.
File hash: `18e198ac18b3c25b307c0aa5d9b6e20d338886e186bf7c12addb759ad4165a61`.

Execution order, one fresh solve each:

| Instance | Base commit |
| --- | --- |
| `vprusso__toqito-1538` | `396ba18ba1fa3e2b8d4eed682562a454d85f5c91` |
| `idaholab__montepy-933_interface` | `fbc03d10eb552cf82acc788ef70d120adec8130c` |
| `unit8co__darts-3065` | `6bfda77e4afc9c123740ab6cc52ca39a7ab92d84` |

Selection is implemented in `diagnostics/original_baseline_select.py`: exclude every
repository in the candidate ledger and checked-in public task packages, case-insensitively;
require a nonempty issue/image and `parse_log_pytest`; sort by SHA-256 of
`patchloop-original-input-pilot-v1` + newline + instance ID; take the first three
distinct repositories. This selected 3 from 87 eligible rows of 110. No patch,
test-patch, hint, F2P/P2P identity or agent outcome was decoded to select tasks.
Local image availability does not affect selection. A failed environment stays in
the denominator as NOT_RUN; do not silently substitute a more convenient task.

The exclusion audit covers current ledger/task inventory, not all historical
conversations or model training data. Therefore call these previously unlisted
repositories, not proven uncontaminated held-out tasks. The first screening before
the finalized union exclusion had 90 eligible rows; union exclusion reduced that
to 87 without changing the selected three. This was not an outcome-based reselection.

## Input and execution protocol

- Use `problem_statement` verbatim, preserving code blocks and whitespace. Deliver
  repository/base identity alongside it. No rewritten task-specific requirements,
  hints_text, previous patches, AnyIO observations or evaluator output in agent context.
- Start each solve at clean base with empty conversation and no cross-run memory.
  No checkpoint continuation, operator rescue, retry or best-of selection.
- Fixed model: `gpt-5.4-2026-03-05`, xhigh, desired output 25,000 tokens;
  segmented-v1, result-or-size-v1, brief-v1, probes enabled / policy none,
  repair-recheck, protected-v1, per-call-v1. These are pilot choices, not CLI defaults.
- Each task: repeat 1, 40 model calls, 100 tool actions, four accepted mutations,
  1,800 active seconds. Proposed paid allocation: $1.20 per task, $3.60 aggregate;
  no transfer between tasks or automatic replenishment. This is not authorization.
- Keep registered tools; no unrestricted agent shell. Use existing base-repository
  tests for visible feedback, without reference-added tests or operator-authored
  semantic cases. Freeze exact public commands/source paths before any model run.
  Commands now copy the public checkout into temporary storage before running existing
  tests. Toqito excludes the public test asserting uparrow is unimplemented, which
  conflicts with the original feature request; no hidden assertion was made public.
- Amended before any paid run: at most four changed production files and 1,000 diff
  lines, no dependency or test/evaluator edits. Public API changes are permitted:
  the original tasks explicitly request an API extension and a property deleter.
  The earlier 120-line/no-API proposal was incompatible with these tasks and was
  rejected during package validation. Concrete source allowlists are now bound.
  Report these harness restrictions;
  this is not an unrestricted benchmark agent or a comparison to historical scores.
- Fix collector/runtime hash, original issue hash, exact task package hash, public
  check commands, image digest, credential path and approved cap in the execution
  manifest. Original-input packages now exist at `tasks/dev-train/original-toqito-1538`,
  `original-montepy-933` and `original-darts-3065`; never substitute adapted packages.
  No paid dispatch until the credential, allocation and execution manifest are bound.

## Evaluation and reporting

Use original test patches and F2P/P2P sets in an isolated evaluator after submission.
Pin parser/grading implementation to `e4907b7a90eafaa1f0a6428fd04fe31cdd8b4284`.
Calibrate each base/reference before paid solves. Do not assume AnyIO's successful
calibration establishes another repository's collection, dependencies or scoring.
Record required-case coverage, full command exit, extra failures and parser result
separately. Explicitly distinguish selected-function execution from full upstream CLI.

Report all three fixed rows: preparation status, submitted/not submitted, original
resolution, cost, time and limit/transport errors. Missing required tests, timeout or
collection/setup failure cannot be labelled an incorrect repair. Non-submission from
resource limits is NOT_RUN for correctness, but stays in completion statistics.
Show resolved/submitted and resolved/three planned separately; do not hide missing
attempts. No evaluator feedback is returned to a solver during this fixed pilot.
Later developer use of results is development feedback, not forbidden in principle;
it must not be represented as an untouched final evaluation.

## Current readiness

All three original issue hashes and metadata are journal-bound at
`C:/pt/analyses/original-input-pilot-selection-20260927-v1`.
After explicit user authorization, all three images were acquired and calibrated.
The fixed execution digests are:

- `swerebench/sweb.eval.x86_64.vprusso_1776_toqito-1538@sha256:4a79ab796ad10cb18c3d805895977fbf119b16db4a9bd4b815678459846a6b86`
- `swerebench/sweb.eval.x86_64.idaholab_1776_montepy-933_interface@sha256:d79f83f33b0f25749596dd0038adecb80e9b443300200890dca0f6d23488567c`
- `swerebench/sweb.eval.x86_64.unit8co_1776_darts-3065@sha256:ce882b8e668e4a6d5452c6612cd5dc9227839f21efc3bde67437603e4d14b7d0`

All three use Python 3.13.13 and verified clean base commits. Six isolated controls
confirmed original BASE failures and REFERENCE successes, with no missing required
cases or timeouts. Reference full-command exits are all zero. See
[calibration](../docs/history/2026-09-27-original-pilot-calibration.md).

`diagnostics/original_pilot_calibrate.py` is an operator-only acquisition/calibration
driver requiring `--authorized-image-acquisition`; that flag is not user permission.
It binds the saved selection, original oracle and prior pinned parser. It never
mounts evaluator material into an agent workspace or calls a model.

Packages passed the actual isolated evaluator with production-only reference patches,
including regression, original oracle, scope and safety checks. Runtime/package hashes
are recorded in [package validation](../docs/history/2026-09-27-original-pilot-packages.md).
Original test-patch application runs on an evaluator-only temporary copy. Explicit
infrastructure exit code 2 becomes evaluator ERROR, not a wrong-answer verdict.

The no-dispatch manifest draft and probe blockers are recorded in
[readiness](../docs/history/2026-09-27-original-pilot-readiness.md). Resolve the public
probe preparation blockers before requesting a paid allocation. The
[OpenBLAS fix](../docs/history/2026-09-27-probe-openblas-default.md) records MontePy
canary success and a successor draft; toqito/darts remain blocked. Enabled
optional probes retain their separate environment requirements; package validation
does not establish dependency completeness for arbitrary probes. No paid run is authorized; image approval
does not authorize model use, another sample or unbounded retries. All evidence is
`official=false`; calibration is not agent performance.
