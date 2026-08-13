# Current reproduction and execution path

Historical D/V commands are preserved in Git and `docs/archive/`; they are not the current runbook.

## Install and validate offline

```powershell
uv sync --offline --frozen --extra dev
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  tests/test_fast_preflight.py `
  tests/test_evaluator_v2_source_qualification.py `
  tests/test_evaluator_v2_contracts.py `
  tests/test_ac_fixed_bundle_cost_completion.py `
  tests/test_documentation_structure.py
& .\.venv\Scripts\python.exe -E -s -B `
  scripts/build_evaluator_v2_ac_source_qualification.py
```

These are offline-only; the builder verifies R10/v11/R8 while preserving R9/R7 and earlier evidence, but grants no preflight, runtime or
paid authority.

## Build a future execution candidate

The root `.env` must contain only `OPENAI_API_KEY`. Preflight checks presence, local Git/SDK and read-only Docker/image
state without printing/exporting the value or making container, network, provider, evaluator or agent calls.

```powershell
& .\.venv\Scripts\patchloop.exe preflight `
  --suite experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml `
  --env-file .env `
  --max-attempts 3
```

Only transient pre-provider failures retry. A pass emits a candidate, not paid readiness. The prior R7 candidate
`sha256:8b962b80...bf6c` is superseded and must not be used. R8 currently has no candidate; run this command only
after the R10 artifact is final, source is committed and the execution worktree is clean.

## Paid execution boundary

R3 through R6 are sealed and their approvals consumed. R9/R10 creates no paid authority. One new approval must bind a
future exact R8 hash, Moto A/C + Babel C/A schedule, `$15.30` reserve and `$18` cap before this form may be instantiated:

```powershell
& .\.venv\Scripts\patchloop.exe evaluate `
  --suite experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml `
  --env-file .env `
  --approve-live-cost `
  --approved-execution-hash sha256:<exact-candidate-hash>
```

This is the provider boundary. Rows never retry/replace and all must qualify or the panel is inconclusive. R8's equal
A/C limits are 3M input, 350k output, 3.35M aggregate, 25k/response, 180 model, 300 tool and 3,600 seconds. They are
R3-informed diagnostics, not held-out-safe or completion-guaranteed; approval grants no held-out or B/D authority.

## Verify the sealed R3-R6 evidence

Use the checked-in R3-R6 evidence indices read-only; never evaluate, finalize, recover or resume these identities.
Raw state stays under `.patchloop`.

## Static checks

```powershell
& .\.venv\Scripts\ruff.exe check patchloop tests
& .\.venv\Scripts\ruff.exe format --check patchloop tests
& .\.venv\Scripts\python.exe -E -s -B -m compileall -q patchloop tests
git diff --check
```

Historical attempts stay immutable. Their old one-use configuration policy does not govern this reusable preflight.
