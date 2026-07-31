# Sandbox image

Build the pinned, repository-free Python 3.12 sandbox image. PatchLoop resolves
the local `patchloop-sandbox:py312` tag during preflight, binds its `sha256:...`
image ID into the manifest, and creates each probe container from that immutable
ID rather than the mutable tag. It verifies the created container's `.Image`
before starting it. Probes never execute in a task's evaluator/SWE-bench image.
Keep this image free of target repositories, Git metadata, benchmark patches,
credentials, and task-specific dependencies.

Docker Desktop may install its CLI outside `PATH`; `patchloop doctor` also checks
the standard per-user Windows location and supports the `PATCHLOOP_DOCKER_CLI`
override.

```powershell
docker pull python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
docker build --network=none --provenance=false -f docker/Dockerfile.sandbox -t patchloop-sandbox:py312 docker
docker run --rm --network none --read-only patchloop-sandbox:py312
```

PatchLoop applies runtime limits (`--network none`, CPU, memory, PIDs, read-only
root and a bounded tmpfs). Probe runs additionally use a read-only public checkout,
mask its `.git`, clear proxy variables, drop all capabilities, label their container
for stale-worker cleanup, and record the image identity and sanitized execution
policy. The host orchestrator owns API and GitHub credentials; neither is mounted
into this image.

Before dispatch, the gateway rejects direct imports and calls for common
process/native/dynamic-code capabilities. The bootstrap audit hook is an
additional early-rejection layer, not a security boundary: untrusted Python can
use reflection or a subinterpreter. The hard process boundary is installed in
the untrusted child by the trusted runner with a seccomp BPF filter. It returns
`EPERM` for fork/clone/exec, parent signaling and process tracing even when the
Python-level checks are bypassed.

The repository-free `/opt/patchloop/probe_runner.py` is PID 1 for every probe.
It compiles the stdin source, forks exactly one untrusted Python child without a
second interpreter exec, installs `no_new_privs` plus the seccomp filter in that
child, and retains the trusted parent as the timeout/reaping authority. The
container PID cgroup is capped at two. A timeout exits with reserved code `124`;
an agent-chosen `124` is remapped and is not misreported as a timeout. The host
launcher keeps a separate grace-bounded fallback and always independently
confirms that the labeled container is absent after forced cleanup.

Because the clean probe image intentionally has no task-specific dependency layer,
a probe that imports an unavailable third-party dependency fails closed. Adding
dependencies or repository content to this image requires a new audited image
contract rather than reusing evaluator images.
