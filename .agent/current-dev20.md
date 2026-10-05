# Current dev20 capabilities and parallel execution

The user requested a measurement of the current agent with useful verification
capabilities enabled, automatic probe replay excluded, and independent tasks run
concurrently. `diagnostics/current_dev20.py` owns the separate current panel;
`diagnostics/parallel_dev_batch.py` schedules independent processes. Historical
packages and evidence remain unchanged.

## Question and fixed comparison

Does exposing the current verification capabilities improve the agent's repairs
on the same development-exposed 20 tasks? Compare per-task original acceptance,
regressions, settled cost and elapsed time with the last 9/20 and historical 10/20.
One run per task is descriptive, not a causal attribution to individual features
or a general performance claim. No held-out tasks, tuning, automatic follow-up,
or test300 run is included.

The prepared configuration uses gpt-5.4-mini-2026-03-17, xhigh, 25,000 desired
output tokens, `.env`, segmented-v1, brief-v1, ordinary probes, repair recheck,
and protected-v1 inspection. Automatic probe replay stays `none`. Each task keeps
40 model calls, 100 actions, four accepted edits and 1,800 seconds. Twenty fixed
USD 1.20 allocations sum to a USD 24 invocation cap. Two task processes run at
once; caps cannot be transferred. Preparation is provider-free. Live scope is
bound to its final manifest and human authorization before dispatch.

## Test integrity and evaluation

Each current package declares its existing pytest root for optional `run_tests`
and additive test edits. The gateway accepts new `test_` functions and methods,
new `Test*` classes containing tests, and additional literal parameter cases in an
existing tracked file. New tests can use decorators such as `mock.patch`.
Existing test bodies, imports, fixtures, class headers and helper definitions must
remain structurally unchanged. Imports needed for a new test can be local to that
function. New files and conftest changes remain unsupported. Additions consume the
same edit budget as source edits. The separate `repair-verify` comparison keeps its
existing top-level selector contract.

The required public check runs on the full submitted patch. Isolated private
evaluation restores original test files only for hidden grading, then restores
the submitted test bytes. Native SWE-bench evaluation uses a separately hashed
source-only patch; the full submitted patch is preserved alongside it. Neither
private results nor original/reference test patches enter solver context.

## Parallel stop and accounting

Every worker has its own source checkout, journal, provider client, model context,
and cost ledger. A process-shared lock coordinates the stop flag with durable
input-count and generation admission. Count, transport, billing or cleanup
uncertainty stops new admissions across the batch. Already admitted calls finish
and retain their usage; uncertainty is never reported as zero spend. No automatic
retry, restart or resume is supported. Native evaluation remains isolated from
solver processes and original registered/native verdicts must agree.

## Preparation and evidence

`register` creates separate task packages once. `dependencies --root <external>
--index N` reads public static setup.py, setup.cfg or PEP 621 metadata without
executing setup/build hooks. Compatibility pins are recorded separately from
source requirements. Most probes use the original clean Python 3.12 profile.
Marshmallow and the two Astroid snapshots requiring old wrapt use the already
installed, digest-pinned public Python 3.10 image. PyVista uses a pinned clean
Python 3.12 image with X11/OpenGL libraries from `docker/probe-graphics.Dockerfile`.
It contains no task or evaluator material. Interpreter markers, wheel ABI,
descriptor, probe receipt, envelope and evaluator evidence bind the same profile.
No runtime path pulls/builds images; the graphics image was explicitly prepared
under the user's request to expand environment support. Selected pytest runs use
the existing registered task image. These environments are not interchangeable.

Use fresh external paths, for example `C:/pt/cd20p06b` for preparation and a
separate live directory. Failed preparation remains evidence and is not overwritten.
Freeze after focused/full/Ruff/mock validation and a clean tracked implementation.
`capabilities --root <external>` records public imports and selected tests with two
provider-free workers. `freeze --root <external> --live-root <separate-external>`
binds the final implementation, roster and limits. `preflight --root <external>
--packet-hash <hash>` verifies those capability receipts against the frozen inputs.
Preflight must record public import and selected-test capability results before
the live run. A capability's availability is distinct from the model choosing to
use it, and neither proves task correctness.
