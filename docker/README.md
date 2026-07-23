# Sandbox image

Build the pinned Python 3.12 evaluator image. Docker Desktop may install its CLI outside `PATH`;
`patchloop doctor` also checks the standard per-user Windows location and supports the
`PATCHLOOP_DOCKER_CLI` override.

```powershell
docker pull python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
docker build --network=none --provenance=false -f docker/Dockerfile.sandbox -t patchloop-sandbox:py312 docker
docker run --rm --network none --read-only patchloop-sandbox:py312
```

PatchLoop applies runtime limits (`--network none`, CPU, memory, PIDs, read-only root and a
bounded tmpfs) at every registered-check invocation. The host orchestrator owns API and GitHub
credentials; neither is mounted into this image.
