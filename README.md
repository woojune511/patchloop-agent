# PatchLoop

> A recoverable single coding agent for bounded, evidence-driven repository repair.

PatchLoop reads a public software task, inspects the target repository, edits code
through constrained tools and runs registered checks. `repair` returns a patch and
public evidence; `dev` also submits it for isolated evaluation. Its reliability layer records every run in an append-only hash chain,
binds mutations and checks to exact inputs, and recovers interrupted work without
silently repeating side effects.

## What it does

1. Loads a public task and an isolated source workspace.
2. Searches and reads only through registered, bounded tools.
3. Applies exact text mutations inside the task's allowed scope.
4. Runs public checks against the current diff; stale results cannot validate a
   later edit.
5. Returns a patch and public receipts (`repair`), or submits a content-bound
   manifest to a separate evaluator (`dev`).
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
 content-bound patch  ----->  public receipts (repair)
             |
             v (dev)
     isolated evaluator
             |
             v
 task acceptance + separate safety state
```

The active runtime is `dev-head`. It uses a fixed tool protocol, bounded model and
tool budgets, zero SDK retries, exact cost admission before dispatch, and
`action_id + input_hash` idempotency for mutation/check recovery.

For public-only tasks, use `patchloop repair --request request.json`; see the
[executable example and request format](examples/repair/README.md).

## Public repair and verification

```powershell
patchloop repair --request request.json
# Save runs[0].delivery.patch.path as returned.patch.
patchloop repair-verify --request request.json --patch returned.patch --state-root verify-state
```

Prepare an exact public request, local source and sandbox first; live generation
requires explicit cost approval. Verification makes no model calls. It runs the
same added pytest cases on the base and patched implementations and records public
checks. Unsupported separation remains `UNSUPPORTED`; this is not acceptance or a
judgment that model-authored expectations match the issue.

See the [request and command example](examples/repair/README.md) and the
[saved dotenv walkthrough](examples/saved-repair/README.md) with the original patch,
portable request, sanitized result JSON and source hashes. The demo reuses a closed
run; it is not live inference or another successful solve.

## Evidence snapshot

| Evidence | Observed result | Boundary |
| --- | --- | --- |
| [Lite dev20 rerun](examples/portfolio-dev20/README.md), 2026-10-06 | 9/20 resolved; USD 3.46111455 (historical 10/20) | Exposed dev tasks; not Lite test score or causal comparison |
| dotenv #715 public repair | Implementation + model test; before failure / after pass | One use, acceptance NOT_RUN |
| Three public uses | All 3 test comparisons passed; code review: 1 candidate, 2 need changes | Automatic verification did not establish patch acceptability |
| Two Click corrections | Both addressed supplied review feedback | Feedback-informed repair; human approval unreported |

See [evidence and limitations](docs/evidence.md) and [current status](docs/current-status.md).
The earlier [Basic/Current 4/6 versus 5/6 pilot](docs/history/2026-09-28-basic-current-baseline-comparison.md)
is a dated, single-repeat development comparison, not a general improvement claim.
All current runs are `official=false`. The 11/20 threshold was not met; test300
was not prepared or executed. Portfolio v1 measurement and local materials are closed.

## Try the local loop

Mock runs use no provider or Docker.

```powershell
$env:PATCHLOOP_STATE_ROOT = 'C:\patchloop-state'
uv sync --extra dev --locked
uv run ruff check patchloop tests
uv run pytest @tests/quick.txt --basetemp ("C:\pt\tmp\" + [IO.Path]::GetRandomFileName())
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
