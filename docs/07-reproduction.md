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
  scripts/build_r8_runtime_evidence.py
& .\.venv\Scripts\python.exe -E -s -B `
  scripts/build_heldout_ac_source_qualification.py
& .\.venv\Scripts\python.exe -E -s -B `
  scripts/build_heldout_ac_task_pricing_materialization.py
```

These are offline-only. The R8 evidence builder validates the checked-in correction index and immutable R10 binding;
when local `.patchloop` originals exist, it also rechecks the complete external chain. Current source intentionally
differs from consumed R10, so do not regenerate R10. The builder never reruns a row or grants runtime/paid authority.
The first held-out builder only revalidates append-only R1/R2 contract-source artifacts. The checked-in task/pricing
builder replays materialization R1: because the artifact already exists it makes no network call and does not rewrite
it, but it evaluator-side revalidates package hashes. It never reads credentials, observes Docker/SDK, creates a
candidate, authenticates a row or spends cost.

## Historical R8 command — do not run

The root `.env` must contain only `OPENAI_API_KEY`. Preflight checks presence, local Git/SDK and read-only Docker/image
state without printing/exporting the value or making container, network, provider, evaluator or agent calls.

```powershell
& .\.venv\Scripts\patchloop.exe preflight `
  --suite experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml `
  --env-file .env `
  --max-attempts 3
```

This was the bounded no-call form used before R8. R8 is now consumed and preflight returns
`HISTORICAL_SUITE_IMMUTABLE`; the command is retained only for audit and must not be used to create another attempt.
The prior R7 candidate `sha256:8b962b80...bf6c` is also superseded.

## Historical paid R8 form — do not run

R3 through R8 are sealed and their approvals consumed. This is the form used for R8 candidate
`sha256:60c67908...cff9e`; it is preserved for audit only and must never be instantiated again:

```powershell
& .\.venv\Scripts\patchloop.exe evaluate `
  --suite experiments/dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml `
  --env-file .env `
  --approve-live-cost `
  --approved-execution-hash sha256:60c679083ad7b995918e2ba5de79843be8b03ce0511b67eb859da437f16cff9e
```

That provider boundary was crossed once. R8's equal limits were 3M input, 350k output, 3.35M aggregate,
25k/response, 180 model, 300 tool and 3,600 seconds. The complete development matrix grants no held-out or B/D
authority. Any future provider campaign needs a new suite/source qualification, candidate and approval.

## Verify the sealed R3-R8 evidence

Use the checked-in R3-R8 evidence indices read-only; never evaluate, finalize, recover or resume these identities.
Raw state stays under `.patchloop`.

## Static checks

```powershell
& .\.venv\Scripts\ruff.exe check patchloop tests
& .\.venv\Scripts\ruff.exe format --check patchloop tests
& .\.venv\Scripts\python.exe -E -s -B -m compileall -q patchloop tests
git diff --check
```

Historical attempts stay immutable. Their old one-use configuration policy does not govern this reusable preflight.
