# Validation and runbook

## Focused local verification

```powershell
$testRoot = 'C:\patchloop-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
uv run ruff check patchloop tests
uv run pytest tests --basetemp $testRoot
```

Use a short external `--basetemp` on Windows if the default temporary directory is
permission-restricted or too long. No provider or Docker call is needed.

## Mock end-to-end

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop dev `
  --provider mock `
  --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock-dev `
  --repeat 1
```

Expected stages are parallel public inspection, admitted mutation, visible check,
automatic diff projection, finish, isolated private evaluation, and a durable
`EVALUATOR_PASS` terminal. The result remains unofficial.

## Live preflight and one row

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop doctor
uv run patchloop task validate tasks/dev-train/<task>
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-mini-2026-03-17 `
  --reasoning-effort medium `
  --env-file <credential-file> `
  --max-cost-usd <positive-decimal> `
  --repeat 1
```

The credential file must contain only one `OPENAI_API_KEY=...` assignment. Do not
put it in the repository. The model must have a reviewed price in
`patchloop/dev/cost.py`. The evaluator image must already exist locally with the
exact declared digest. The command never starts Docker Desktop or pulls/builds.

Operational acceptance requires the JSONL terminal and evaluator summary within
30 minutes. Preserve the run directory; do not edit or replay it.

## Historical-byte audit

```powershell
git diff --name-only b71ddeee -- reports experiments docs/archive
```

Expected output is empty.
