# Bounded threads in public Python probes

`docker-python-probe-v2` supports ordinary same-process threads. The former v1
profile denied every `clone`/`clone3` call and counted only a supervisor and child
with `pids_limit=2`. This prevented `asyncio.to_thread`, including OpenAI SDK
2.29.0's local platform initialization with a completely offline HTTP transport.
Suppressing that SDK initializer would leave other normal threaded libraries broken.

## Boundary and identity

- The trusted supervisor still forks once before installing the child's seccomp filter.
- On x86_64 and aarch64, `clone` must include `CLONE_VM`, `CLONE_FS`, `CLONE_FILES`,
  `CLONE_SIGHAND`, `CLONE_THREAD` and `CLONE_SYSVSEM`. Only TLS and parent/child TID
  bookkeeping flags are additionally allowed. Exit signals, namespaces, unknown
  flags, the high argument word and alternate syscall ABIs are rejected.
- `clone3` returns `ENOSYS` without executing. Classic seccomp cannot inspect its
  pointer-based argument structure; libc can fall back to the checked `clone` path.
- Docker's fixed `pids_limit=8` counts the supervisor, probe main thread and up to
  six additional threads. They inherit the seccomp filter and share the existing
  CPU, memory, scratch, output and execution-time limits. This is no promise of
  compatibility with libraries that need larger thread pools.
- Fork-like process creation, exec, supervisor signaling, ptrace and cross-process
  memory operations remain denied. Network, nonroot user, read-only source/root/
  dependency mounts, cap-drop and no-new-privileges remain in force.
- The trusted child uses `os._exit`, which ends unjoined threads too. The supervisor
  kills the child process group at timeout; the host still confirms exact owned
  container cleanup before accepting the receipt or allowing another execution.

`probe_profile()` binds v2, `same-process-pthreads-only-v1`, PID limit and wrapper
bytes. Runtime/profile changes reject active recovery against an old identity;
closed records remain immutable and readable. No tool schema, plan instruction,
segment rule, acceptance credit or automatic retry changes.

Changed-line collection still covers the launch thread only. Worker-thread source
execution must not be reported as covered by that collector.

## Validation

The filter interpreter tests both supported ABIs, required/missing/disallowed bits,
clone3 fallback errno and alternate ABI rejection. Real Docker tests require explicit
`PATCHLOOP_TEST_REAL_PROBES=1` and the already-existing pinned Python image; they never
start Docker or acquire images. The SDK fixture additionally takes
`PATCHLOOP_TEST_PROBE_DEPENDENCIES=<existing public descriptor>`, verifies and copies
that bundle, and uses a synthetic source workspace, dummy key and `httpx.MockTransport`.
Actual socket connection attempts are rejected by the fixture as well as network=none.

Evidence: `C:\pt\analyses\probe-thread-compatibility-20260918-v1`.
Both old-filter cases reproduced `can't start new thread`. After the fix, all seven
real Docker tests pass: SDK request/async shutdown, inherited isolation, six-worker
limit, unjoined-worker exit, output bound, deadline cleanup and durable replay.
Real execution is Linux amd64; aarch64 has filter-unit coverage only. This demonstrates
probe compatibility, not model counterexample discovery or task acceptance. The prior
fixed-candidate discovery sample and its budget remain closed.

Kernel contracts: [seccomp filters](https://docs.kernel.org/userspace-api/seccomp_filter.html),
[clone flags](https://man7.org/linux/man-pages/man2/clone.2.html),
[PID controller](https://docs.kernel.org/admin-guide/cgroup-v1/pids.html).
