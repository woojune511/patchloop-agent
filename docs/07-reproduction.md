# Clean-machine reproduction

## Supported environment

- Windows 11 + WSL2 + Docker Desktop for official evaluator results
- Python 3.12 and `uv`
- Git; `gh` is optional and only required for the GitHub demo

## Offline validation

```powershell
git clone <repository-url> PatchLoop
Set-Location PatchLoop
uv sync --extra dev
uv run ruff check patchloop tests
uv run pytest -q
uv run patchloop task validate tasks/smoke/csv-quoted-newline
uv run patchloop run --task tasks/smoke/csv-quoted-newline/public.yaml --model mock
uv run patchloop evaluate --suite experiments/smoke.yaml
uv run patchloop report --experiment offline-smoke --output reports/offline-smoke
```

The mock run does not need an API key. It creates `.patchloop/state.sqlite3`, immutable run manifests,
ordered events, checkpoints, submitted patches and content-addressed evidence. Local backend results have
`official=false` by design.

## Official Docker boundary

```powershell
uv run patchloop doctor
docker pull python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
docker build --network=none --provenance=false -f docker/Dockerfile.sandbox -t patchloop-sandbox:py312 docker
uv run patchloop eval-task tasks/smoke/csv-quoted-newline `
  --patch tasks/smoke/csv-quoted-newline/reference.patch --backend docker
```

The Dockerfile pins the base digest used by the 2026-07-23 evaluator gate. Before a frozen experiment,
re-audit the base digest deliberately and record the built image digest in the experiment manifest; do not
silently float the tag. A Docker result is official only when the daemon is available and the evaluator
actually runs with the Docker backend.

If Docker Desktop is installed per-user outside `PATH`, `patchloop doctor` checks its standard Windows
location. Set `PATCHLOOP_DOCKER_CLI` to an existing CLI path for a non-standard install.

## Recovery demonstration

Start with any completed mock run ID:

```powershell
uv run patchloop inject-fault --run <baseline-run-id> --fault worker-kill-after-patch
uv run patchloop resume --run-id <fault-run-id>
```

Inspect the derived run in the viewer. It must have one `PatchApplied`, one `FaultInjected`, durable
checkpoint evidence and a final evaluator result.

## Live API gate

Do not set `live_cost_approved: true` until the dated Terra model alias/snapshot, SDK version and price
estimate have been recorded and the user has approved the projected spend. CI never performs live calls.

## Memory freeze gate

```powershell
uv sync --extra dev --extra memory
uv run patchloop memory build --split dev-train --embedding-revision <hugging-face-commit>
uv run patchloop memory freeze --index <index-id> --embedding-revision <same-commit>
```

A non-empty index is freezeable only when its vectors were created by
`sentence-transformers/all-MiniLM-L6-v2` at the recorded commit. Empty or lexical placeholder indexes
are rejected before any memory-condition campaign.
