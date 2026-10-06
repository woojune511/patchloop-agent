# Current dev20 capabilities and parallel execution

The user requested a measurement of the current agent with useful verification
capabilities enabled, automatic probe replay excluded, and independent tasks run
concurrently. `diagnostics/current_dev20.py` owns the separate current panel;
`diagnostics/parallel_dev_batch.py` schedules independent processes. Historical
Lite packages and saved evidence remain unchanged. Current package constraints
and runtime identities change with fixes; old allocations cannot resume with them.

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

The current panel reserves the public check timeouts plus 30 seconds for checkout
inside each task's existing total: 330 seconds for evaluation, leaving 1,470 for
the solver. This is a scheduling allowance, not a completion guarantee. The general
development request default remains zero. The reserve is envelope-bound; it neither
extends the total nor automatically submits a patch. Only a timely, durable
`solver_finished` receipt permits evaluation recovery after the solver cutoff.

## Test integrity and evaluation

Each current package declares its existing pytest root for optional `run_tests`
and additive test edits. The gateway accepts new `test_` functions and methods,
new `Test*` classes containing tests, and additional literal parameter cases in an
existing tracked file. Direct `pytest.param` cases may contain literal positional
values and an optional string `id`; new marks or computed cases remain unsupported.
See [selected tests](selected-tests.md). New tests can use decorators such as `mock.patch`.
Existing test bodies, imports, fixtures, class headers and helper definitions must
remain structurally unchanged. Imports needed for a new test can be local to that
function. New files and conftest changes remain unsupported. Additions consume the
same edit budget as source edits. The separate `repair-verify` comparison keeps its
existing top-level selector contract.

The five current SQLFluff packages explicitly forbid mutations under
`src/sqlfluff/testing/**`. These verification helpers remain readable. The existing
scope rule protects them at mutation admission, isolated evaluation, and native
assessment before source-only projection; their source location is not treated as
evidence that they are safe repair targets.

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
solver processes. Completed registered/native verdicts must agree. A registered
evaluation deadline may be a task-local limit only when its durable, artifact-bound
completion receipt confirms the deadline without cleanup uncertainty, accounting is
settled, and native assessment completed with confirmed cleanup. That row remains
unsuccessful with the original ERROR and native verdict; independent rows continue.
Other disagreements, missing receipts, and operational uncertainty still stop the batch.
Settled exhaustion of one row's fixed cost cap also stays local; the runtime's
stop-repetitions flag must not cancel independent rows with separate allocations.

## Preparation and evidence

`register` creates separate task packages once. `dependencies --root <external>
--index N` reads public static setup.py, setup.cfg or PEP 621 metadata without
executing setup/build hooks. Compatibility pins are recorded separately from
source requirements. Most probes use the original clean Python 3.12 profile.
Marshmallow uses a digest-pinned clean public Python 3.9 image because its ordinary
validation API needs legacy collections aliases. The two Astroid snapshots requiring
old wrapt use the pinned public Python 3.10 image. PyVista uses a pinned clean
Python 3.12 image with X11/OpenGL libraries from `docker/probe-graphics.Dockerfile`.
It contains no task or evaluator material. Interpreter markers, wheel ABI,
descriptor, probe receipt, envelope and evaluator evidence bind the same profile.
No runtime path pulls/builds images; the graphics and Python 3.9 images were explicitly
prepared under the user's request to expand environment support. Selected pytest runs use
the existing registered task image. These environments are not interchangeable.

Use fresh external paths, for example `C:/pt/cd20p06b` for preparation and a
separate live directory. Failed preparation remains evidence and is not overwritten.
Freeze after focused/full/Ruff/mock validation and a clean tracked implementation.
`capabilities --root <external>` records public imports, ordinary library operations,
and selected tests with two provider-free workers.
`freeze --root <external> --live-root <separate-external>`
binds the final implementation, roster and limits. `preflight --root <external>
--packet-hash <hash>` verifies those capability receipts against the frozen inputs.
Preflight requires all three capability results and binds each operation program
hash and the current driver before the live run. A successful import alone does not
establish that library operations work. Availability is distinct from the model
choosing to use a capability, and neither proves task correctness.
