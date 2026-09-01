# PatchLoop

PatchLoop is a single coding agent. The active product path is one mutable,
unofficial development runtime named `dev-head`; task loading, constrained tools,
recovery state, sandboxing, and private evaluation support that agent.

The old Rapid, candidate, qualification, activation, adoption, and claim runners
are not part of the current checkout. Their code is recoverable from Git history,
and their immutable results remain under `experiments/`, `reports/`, and
`docs/archive/`.

## Fast local loop

Use an external state directory. Mock mode forbids credentials and cost options.

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run ruff check patchloop tests
uv run pytest tests
uv run patchloop dev `
  --provider mock `
  --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock-dev `
  --repeat 1
```

## One-row live development

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-mini-2026-03-17 `
  --reasoning-effort medium `
  --env-file <credential-file> `
  --max-cost-usd <positive-decimal> `
  --repeat 1
```

That exact invocation is the approval for its provider, task, model, repetition
count, and total cap. Live mode accepts only `dev-train`, requires a local
digest-pinned evaluator image, never pulls or builds an image, and uses zero SDK
transport retries. A run remains `official=false` even when its private evaluator
passes.

Start at [docs/00-index.md](docs/00-index.md). Current behavior is owned by
[docs/current-status.md](docs/current-status.md); measured facts and explicit
non-results are in [docs/09-evidence.md](docs/09-evidence.md).
