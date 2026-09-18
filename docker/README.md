# Optional public Python probes

Active dev-head probes are enabled explicitly with `patchloop dev --enable-probes`.
They use the fixed clean official Python image below, which must already exist locally:

```text
python@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
```

`patchloop/sandbox/probes.py` owns this identity as `PROBE_IMAGE`. Preflight verifies
the exact local image and the trusted wrapper before execution. Docker records
`name:tag@digest` as `name@digest` in `RepoDigests`; lookup and comparison ignore only
the optional final-component tag, preserving the repository, registry port, and exact
digest. The fixed probe image uses this canonical reference for execution too; the
digest still pins the same reviewed Python 3.12-slim content.
PatchLoop never pulls
or builds an image, starts Docker Desktop, or falls back to another image. The
historical `patchloop-sandbox:py312` image and task evaluator images are not used by
this capability. `Dockerfile.sandbox` remains a tracked historical image recipe;
building it is unnecessary for the active probe path.

The host exports a separate current tracked public snapshot and mounts it read-only
at `/workspace`. Git metadata, `.env*`, `.patchloop-hidden`, untracked files, symlinks,
and reparse points are excluded or rejected. The agent worktree and private task
package are not mounted. Snapshot bytes are bounded to 128 MiB and hashed. The trusted
`docker/probe_runner.py` is separately copied outside the workspace and mounted
read-only at `/opt/patchloop`; its raw-byte hash is part of the immutable run's probe
profile. Both this wrapper and the Dockerfile are bound in the runtime content hash.

V26 also copies `patchloop/sandbox/line_trace.py` into that existing trusted mount when
current changed Python lines are selected. The profile includes `line_trace_hash`, and
the runtime hashes the Python file. This stdlib-only helper needs no image rebuild.
It observes line entries in the child launch thread and emits a separately bounded
report frame; stdout/stderr retention and excess-output termination remain unchanged.
Only host-selected current public paths, raw file hashes and changed line numbers are
reported, never values or source bodies. Missing, invalid or interrupted collection is
unknown. The report is a diagnostic, not tamper-resistant attestation, semantic coverage,
required-check credit or a mandatory-probe/submission policy. The same helper can instrument
registered public Python checks in a separate read-only trusted mount. Interpreter
recognition uses the executable basename, including absolute POSIX/Windows paths,
versioned Python 3 and `.exe`, without replacing the declared binary or arguments.
Private evaluator checks never receive collection targets. Current-diff summaries derive
from durable tool results, so completed-action replay does not execute the experiment again.

The model supplies a public question and Python source, not Docker arguments. Source
is limited to 8,000 characters and 32,000 UTF-8 bytes. The host caps combined stdout
and stderr at 12,000 bytes during collection and terminates excess output. Execution
is at most 30 seconds, shortened when necessary by the shared active deadline. Up to
five seconds of the remaining row budget is reserved for cleanup.

Containers run as numeric user `10001:10001` with no network, a read-only root,
all capabilities dropped, `no-new-privileges`, one CPU, 512 MiB memory with no extra
swap, and a two-process limit. A 64 MiB `/tmp` tmpfs provides scratch storage with
`noexec,nosuid,nodev`. The Python entrypoint and mounted wrapper are selected by the
host, and provider credentials are not injected into the container.

Python source is not filtered through an import/AST denylist. The trusted wrapper
runs as PID 1, compiles stdin source, forks one untrusted child, and installs a
seccomp filter in that child. The parent retains timeout and reaping authority.
The child cannot fork/clone/exec, signal its parent, or trace another process through
the restricted system calls. Reserved timeout exit code `124` is distinguished from
an agent-chosen exit code. By default, only `/workspace` is added to `sys.path`; a src
layout may require the probe to add its observed source root explicitly, such as
`sys.path.insert(0, '/workspace/src')`. Project dependencies are not installed;
unavailable imports fail as ordinary diagnostic experiments. There is no runtime
dependency installation or evaluator-image fallback. The tool description explains
these limits before execution. A failed probe reporting ModuleNotFoundError or
ImportError in stderr receives generic model-facing guidance to inspect the traceback
and, if useful, isolate a mechanism with the standard library. A reduction does not
execute or verify the project implementation, and import failure alone does not test
the intended behavior. Raw receipts, execution policy and sandbox identity are unchanged.

Opt-in `--prepared-probe-dependencies` uses the same clean image and process boundary.
The operator prepares exact public PyPI wheels from the public source's lock before the
run. Each probe verifies an independent read-only dependency snapshot; source import
roots precede dependencies and `.pth` hooks are not processed. Nonempty configured roots
limit source copies to those trees and root files; tracked symlinks are omitted without
following targets. Source size, process and output limits remain fixed. Descriptor/content
identity and the source-selection policy enter the profile hash, envelope and evaluator
receipt validation. No evaluator image extraction, runtime installation or network
fallback. See [the preparation contract](../.agent/prepared-probe-dependencies.md).

Each container has an exact run/action-derived name and ownership label. Timeout,
excess output, and interruption cleanup target only that owned container, and cleanup
uncertainty stops execution. A completed action replays its durable result. An
interrupted action without a result can clean up and rerun its isolated experiment;
this is not an exactly-once process guarantee. Temporary experiments never become
part of the submitted patch.

Output retention and pipe draining are separate: after the 12,000-byte cap, readers
discard further bytes until EOF while the main thread tears down the owned container.
Leaving attach pipes unread can stall that teardown. `observed_output_bytes` counts
all drained public stdout/stderr bytes and may exceed the fixed retained/public-output
limit. The separately framed line report has its own 16,000-byte body allowance and is
excluded from those public-output counters. A malformed report alone means unknown
execution feedback, not a failed probe; only excess public/report output triggers the
existing output-limit outcome. Repeated report frames cannot bypass this byte bound.

Probe results are diagnostic and grant no required-check PASS or submission credit.
The sandbox's stored `status=passed` still means exit zero only. V28's model projection
labels this `observation.execution_status=completed`, always with
`behavior_verdict=not_assessed`, and removes the ambiguous status from the projected body.
It places bounded public line-entry excerpts before detailed output, without changing
the collector, process, image/profile, timeout, raw receipt or safety interpretation.
Receipts bind action/input, source, diff, snapshot, image/profile, and execution-policy
hashes. The evaluator validates their integrity before creating its workspace and
keeps safety separate from task acceptance. No real Docker probe or new live row is
authorized by implementation or mocked tests. Future live authorization must explicitly
include `--enable-probes`, and resume must retain the original capability setting.

## Explicit local verification

After separate permission for real Docker execution and with the fixed image already
present, `tests/test_dev_probe_docker.py` checks synthetic-source isolation and completed
replay, output flooding, and shortened-deadline cleanup. Set `PATCHLOOP_TEST_REAL_PROBES=1`
only for that invocation and use a new external `--basetemp` with `-x`. It records public
receipts and hash-chained action journals under that temporary root. Default pytest
skips these three cases; it must not start Docker or acquire images to unskip them.
This diagnostic matrix is not a paid live row or a comprehensive sandbox-security claim.

For v26 line collection alone, `tests/test_dev_execution_docker.py` is a separate,
default-skipped case enabled only with `PATCHLOOP_TEST_REAL_EXECUTION=1`. With explicit
permission, run that exact file with `-x` and a new external `--basetemp`. It uses the
already-local fixed Python image for one synthetic registered check and one probe;
it does not run the three-probe matrix above. The probe deliberately raises an error
to verify that failed execution still records entered lines. Public receipts verify
current diff/file binding, unobserved versus non-line positions, combined observations,
exact-container cleanup and completed replay without another launch. Missing preflight
or the first unexpected result stops execution without retry or image acquisition.
The initial approved v26 pair passed under `C:\pt\pl26-docker-real-a` with bare `python`.
The current test uses `/usr/local/bin/python` to match the task's real interpreter spelling;
its separately approved pair passed in 7.96 seconds under `C:\pt\pl26-abs-docker-a`, with
exactly one check and one probe, confirmed cleanup and replay without another launch.
Provider-free tests also read the actual task's `-c`/`-m` declarations and verify launch
wiring with Docker mocked. These tests do not establish improved live model decisions,
exact task-evaluator workload coverage, or new execution authority.
