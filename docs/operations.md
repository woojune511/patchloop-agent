# Run and validate

All generated state must live outside the repository. The examples use short
Windows paths to avoid temporary-directory permission and path-length failures.

## Fast local verification

```powershell
$testRoot = 'C:\patchloop-test-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run pytest tests --basetemp $testRoot
```

This path uses no provider or Docker call.

## Mock end-to-end

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop dev `
  --provider mock `
  --task tasks/smoke/csv-quoted-newline/public.yaml `
  --model mock-dev `
  --repeat 1
```

Mock mode forbids credential and cost options. A successful smoke run performs
parallel public inspection, one admitted mutation, a visible check, automatic
full-diff projection, finish, and a separate private evaluation. Its result is
still unofficial.

## Explicitly approved live development

First inspect local prerequisites and the task package:

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv run patchloop doctor
uv run patchloop task validate tasks/dev-train/<task>
```

Then issue one fully specified invocation:

```powershell
uv run patchloop dev `
  --provider openai `
  --task tasks/dev-train/<task>/public.yaml `
  --model gpt-5.4-mini-2026-03-17 `
  --reasoning-effort medium `
  --env-file <credential-file> `
  --max-cost-usd <positive-decimal> `
  --repeat 1
```

That exact command is the development approval for its provider, task, model,
credential file, repeat count, and invocation-wide cap. Live mode accepts only
checked-in `dev-train` tasks. The credential file may contain only one
`OPENAI_API_KEY=...` assignment and must stay outside the repository.

The required evaluator image must already exist locally at the declared digest.
PatchLoop never starts Docker Desktop or pulls/builds an image. Unknown model
pricing fails before dispatch. The adapter counts the actual request immediately
before generation, reserves a conservative output allowance, uses zero SDK
transport retries, and stops all remaining repetitions when count, transport, or
billing state is uncertain.

Current GPT-5.4 mini pricing and supported reasoning effort are reviewed against
the official [API pricing](https://developers.openai.com/api/docs/pricing) and
[model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Input
counting follows the official
[token-counting guide](https://developers.openai.com/api/docs/guides/token-counting).

## Submission and evaluation

`finish_task` becomes available only after every visible check passes on the
current diff. The full submitted patch is stored by content hash. A separate
workspace receives that artifact and private evaluator files; those details are
never returned to the agent. The public result contains only PASS/FAIL and a safe
failure class.

Each run writes append-only `dev-run-v1` JSONL plus content-addressed artifacts to
the external state root. Operational acceptance requires a durable terminal and
evaluator summary within 30 minutes. Preserve the run directory and do not edit
or replay it.
