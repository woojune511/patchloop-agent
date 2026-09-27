# Original benchmark preparation

`diagnostics/anyio_benchmark_prepare.py` prepares one pinned AnyIO benchmark row
and inspects an already available evaluator image. It is operator-only and is not
connected to agent tools or the current task loader. Run with the optional analysis
dependency: `uv run --with pyarrow python -m diagnostics.anyio_benchmark_prepare
--output <new-external-directory>`.

The dataset file hash and revision are fixed. Original issue input uses an explicit
allowlist; original tests, reference patch and grading metadata stay in evaluator-only
content-addressed storage. The external `dev-run-v1` journal binds inputs, selected
upstream harness sources and environment receipts. Never mount this store in an
agent workspace. A source pin is not proof that the original parser was executed.

Environment inspection uses an existing digest, no pulls/builds, no network, no host
mounts and a read-only container. It records interpreter, packages, source HEAD and
tracked status, then removes its named container. Errors require inspection of the
closed output; no resume/retry is implied. Each invocation requires a new directory.

The preparation command alone does not execute tests or scoring.
`diagnostics/anyio_benchmark_calibrate.py --prepared <prepared-directory> --output
<new-external-directory>` runs fixed BASE and REFERENCE controls in separate disposable
network-disabled containers with no host mounts. It applies original test material
only evaluator-side and executes the original command without deselections or installs.
The image's writable container layer is discarded after each control.

Calibration executes selected unchanged upstream parser/grading definitions, extracted
from the pinned source with their enum definitions. It does not run the complete upstream
CLI. Raw output, extracted source, script identity, per-case verdicts and cleanup receipts
remain evaluator-only. `infrastructure_complete` in this diagnostic means required cases
were reported without timeout/collection exit; it does not mean the entire suite is clean.
Report command exit, extra results, required-case coverage and resolution separately.
No model calls, candidate performance claims or task/default changes follow from calibration.
