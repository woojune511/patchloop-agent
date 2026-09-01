# PatchLoop

PatchLoop is a single coding agent with a deliberately short development loop.
Its mutable runtime, `dev-head`, inspects a public task, edits through constrained
tools, runs registered checks, submits a patch, and receives an isolated private
evaluator summary. Every current run is development-only and `official=false`.

## Start here

- [Current status](docs/current-status.md) — what works now and what remains
- [Product and architecture](docs/product.md) — what PatchLoop is and how it fits together
- [Run and validate](docs/operations.md) — local, mock, and explicitly approved live commands
- [Evidence and limitations](docs/evidence.md) — measured facts, non-results, and claim boundaries
- [Documentation index](docs/README.md) — the complete human-facing set

## Try the local loop

Mock mode uses no credentials, provider call, or Docker image.

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run pytest tests
uv run patchloop dev `
  --provider mock `
  --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock-dev `
  --repeat 1
```

Live development has a stricter boundary: the exact invocation is the approval
for one declared task/model/repetition/cost envelope. See
[Run and validate](docs/operations.md) before using it.

## Repository map

```text
patchloop/dev/       mutable agent loop, tools, context, cost, and journal
patchloop/verifier/  separate private evaluator
tasks/               audited task packages
fixtures/            local smoke repositories and task fixtures
docs/                current human documentation
reports/             immutable historical evidence
experiments/         immutable historical plans and results
```

Historical Rapid and claim executables are recoverable from checkpoint commit
`b71ddeee`. Their immutable artifacts and archived documentation remain in the
repository, but they do not describe the current runtime.
