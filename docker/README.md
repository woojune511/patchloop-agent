# Optional public Python probes

Active dev-head probes are enabled explicitly with `patchloop dev --enable-probes`.
They use the fixed clean official Python image below, which must already exist locally:

```text
python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
```

`patchloop/sandbox/probes.py` owns this identity as `PROBE_IMAGE`. Preflight verifies
the exact local image and the trusted wrapper before execution. PatchLoop never pulls
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

Probe results are diagnostic and grant no required-check PASS or submission credit.
Receipts bind action/input, source, diff, snapshot, image/profile, and execution-policy
hashes. The evaluator validates their integrity before creating its workspace and
keeps safety separate from task acceptance. No real Docker probe or new live row is
authorized by implementation or mocked tests. Future live authorization must explicitly
include `--enable-probes`, and resume must retain the original capability setting.
