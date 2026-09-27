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

This is preparation only: no patch application, tests, parser execution, scoring or
live model calls. `ready_for_benchmark_score` remains false. Next implement isolated
base/reference calibration using the pinned upstream parser and original test patch;
separate infrastructure errors from oracle outcomes and report any missing dependencies.
