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
registered public Python checks in a separate read-only trusted mount; private evaluator
checks never receive collection targets. Current-diff summaries derive from durable tool
results, so completed-action replay does not execute the experiment again.

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
an agent-chosen exit code. Source imports can use `/workspace`, but unavailable
third-party dependencies fail as ordinary diagnostic experiments; there is no runtime
dependency installation or evaluator-image fallback.

Each container has an exact run/action-derived name and ownership label. Timeout,
excess output, and interruption cleanup target only that owned container, and cleanup
uncertainty stops execution. A completed action replays its durable result. An
interrupted action without a result can clean up and rerun its isolated experiment;
this is not an exactly-once process guarantee. Temporary experiments never become
part of the submitted patch.

Output retention and pipe draining are separate: after the 12,000-byte cap, readers
discard further bytes until EOF while the main thread tears down the owned container.
Leaving attach pipes unread can stall that teardown. `observed_output_bytes` counts
all drained bytes and may exceed the fixed retained/public-output limit.

Probe results are diagnostic and grant no required-check PASS or submission credit.
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
