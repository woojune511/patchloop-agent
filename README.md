# PatchLoop

> A recoverable single coding agent for bounded, evidence-driven repository repair.

PatchLoop reads a public software task, inspects the target repository, edits code
through constrained tools, runs registered checks, and submits a patch for isolated
evaluation. Its reliability layer records every run in an append-only hash chain,
binds mutations and checks to exact inputs, and recovers interrupted work without
silently repeating side effects.

The agent is the product. Sandboxing, cost control, recovery, and evaluation exist
to make its repairs measurable and trustworthy.

## What it does

1. Loads a public task and an isolated source workspace.
2. Searches and reads only through registered, bounded tools.
3. Applies exact text mutations inside the task's allowed scope.
4. Runs public checks against the current diff; stale results cannot validate a
   later edit.
5. Submits a content-bound manifest to a separate evaluator.
6. Records task acceptance, safety, cost, tokens, actions, and recovery state as
   separate evidence.

The coding model never receives unrestricted shell access, private evaluator
details, hidden tests, or reference patches.

## Runtime architecture

```text
public task + isolated source
             |
             v
  single model/tool loop  ----->  append-only run journal
             |
             v
     verified current diff
             |
             v
 content-bound submission  ----->  isolated evaluator
             |
             v
 task acceptance + separate safety state
```

The active runtime is `dev-head`. It uses a fixed tool protocol, bounded model and
tool budgets, zero SDK retries, exact cost admission before dispatch, and
`action_id + input_hash` idempotency for mutation/check recovery.

## Evidence snapshot

The latest matched development pilot used six checked-in OSS repair tasks, the same
GPT-5.4 snapshot and resource limits, and one fresh run per task and arm.

| Configuration | Accepted | Safety | Cost | Active time |
| --- | ---: | ---: | ---: | ---: |
| Basic agent | 4/6 | 6/6 PASS | $2.777399 | 1,159.5 s |
| Current bundle | 5/6 | 6/6 PASS | $3.338190 | 1,431.5 s |

The paired result was one Current win, zero Basic wins, and five ties. Current cost
20.2% more and used 23.5% more active time. This is a small, single-repeat,
three-feature comparison—not a general success-rate or causal-improvement claim.
All current runs are development-only and `official=false`.

See the [full comparison](docs/history/2026-09-28-basic-current-baseline-comparison.md),
[current status](docs/current-status.md), and [evidence boundaries](docs/evidence.md).

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

Live execution requires an exact task, model, credential file, repetition count,
and positive invocation-wide cost cap. PatchLoop does not automatically start
Docker Desktop or pull/build evaluator images. Read [operations](docs/operations.md)
before running a live task.

## Project status

PatchLoop is an active engineering and evaluation project, not a production service
or an official benchmark. Cross-run memory, held-out tuning, and claim execution are
currently disabled. Planning, probes, and repair rechecks are optional mechanisms;
their presence alone does not establish better task solving.

Development starts from observed agent failures and tests the smallest useful change.
Negative results, `NOT_RUN`, safety, acceptance, cost, and time remain distinct.

## Repository map

```text
patchloop/dev/       agent loop, tools, context, cost, and recovery
patchloop/verifier/  isolated evaluator and safety boundary
patchloop/sandbox/   registered checks and bounded diagnostics
tasks/               versioned public/private task packages
fixtures/            provider-free smoke repositories
tests/               runtime, recovery, safety, and CLI contracts
docs/                current product, operation, and evidence guidance
docs/history/        completed investigations and comparison records
```

Start with [product and architecture](docs/product.md),
[run and validation](docs/operations.md), or the [documentation index](docs/README.md).
Historical Rapid artifacts remain preserved for evidence, but do not describe the
current runtime.
