# Current reproduction and validation

Historical commands are archived at `docs/archive/snapshots/d121/07-reproduction.full.md`; only paths below are current.

## Environment

- Windows/PowerShell, Python 3.12+ and locked `uv`; Docker only under separate exact authority

```powershell
uv sync --offline --frozen --extra dev
```

## Validate the A/C sources and fixed-bundle delivery

```powershell
uv run --offline --frozen pytest -q tests/test_ac_structured_pilot_plan.py tests/test_ac_fixed_bundle_readiness.py
uv run --offline --frozen pytest -q tests/test_ac_fixed_bundle_cost_completion.py
uv run --offline --frozen pytest -q tests/test_fixed_bundle_delivery.py tests/test_d122_ac_fixed_bundle_qualification.py
uv run --offline --frozen python scripts/build_d122_ac_fixed_bundle_qualification.py --validate-sealed-historical
```

These offline checks grant no live, retrieval, Docker, provider, candidate or cost authority.

## Validate the evaluator-v2 successor qualification

```powershell
uv run --offline --frozen pytest -q tests/test_evaluator_v2_contracts.py `
  tests/test_evaluator_v2_source_qualification.py
uv run --offline --frozen python scripts/build_evaluator_v2_ac_source_qualification.py
```

The second command leaves artifact mtime unchanged; neither command creates external activity or a candidate.

## Validate the sealed no-call contract

```powershell
uv run --offline --frozen pytest -q tests/test_versioned_no_call_preflight_contract.py
uv run --offline --frozen python scripts/build_versioned_no_call_preflight_contract.py --validate
```

Validation reads committed blobs without changing mtime and grants no live authority.

V13-v18 remain consumed. V20 validation binds the exact v19 source/qualification without external observation:

```powershell
uv run --offline --frozen python scripts/build_dual_pipe_activation_successor.py --validate-contract
uv run --offline --frozen python scripts/build_dual_pipe_activation_successor.py --validate-source
uv run --offline --frozen python scripts/build_dual_pipe_activation_successor.py --show-approval-template
$v20Basetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-v20-' + [guid]::NewGuid())
uv run --offline --frozen pytest -q -p no:cacheprovider --basetemp $v20Basetemp `
  -k 'not source_modes_have_no_runtime_side_effects' tests/test_dual_pipe_activation_successor.py
```

These validation modes create no artifact or external observation. The excluded source-bound test asserts the
pre-state checkout; current v20 is state-bound and approval-closed. V18 remains consumed.

## Audit the sealed D-142 source

D-142 validation is bound to its exact clean historical checkout and rejects current HEAD. Audit only there in
sealed/read-only mode. Its 170/170 mocked count is local evidence, not external observation.

## Static and documentation checks

```powershell
& .\.venv\Scripts\ruff.exe check patchloop tests
& .\.venv\Scripts\ruff.exe format --check patchloop tests
& .\.venv\Scripts\python.exe -E -s -B -m compileall -q patchloop tests
$docsBasetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-docs-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

Historical absent-state assertions never justify rewriting sealed evidence.

## Live execution

There is no supported live A/C, D-142, v18 retry or v20 activation command. Validate read-only, then stop: no
attempt, candidate or cost gate is open.
