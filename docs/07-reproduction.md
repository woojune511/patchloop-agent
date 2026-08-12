# Current reproduction and validation

Historical per-milestone commands are archived at
`docs/archive/snapshots/d121/07-reproduction.full.md`. Commands below are the supported current paths.

## Environment

- Windows/PowerShell
- Python 3.12+
- `uv` with the repository lockfile
- Docker Desktop only for a separately approved Docker step

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

These are offline checks for the four-row source, A-null/C-exact bundle contract, trace qualification and
historical D-122 bytes. They grant no live, retrieval, provider, Docker, hash/candidate or cost authority.

## Validate the evaluator-v2 successor qualification

```powershell
uv run --offline --frozen pytest -q tests/test_evaluator_v2_contracts.py `
  tests/test_evaluator_v2_source_qualification.py
uv run --offline --frozen python scripts/build_evaluator_v2_ac_source_qualification.py
```

The second command must leave the append-only artifact's mtime unchanged. Both commands are local-only and create
no Docker/network/credential/provider/evaluator/agent activity, execution hash or candidate.

## Validate the sealed no-call contract

```powershell
uv run --offline --frozen pytest -q tests/test_versioned_no_call_preflight_contract.py
uv run --offline --frozen python scripts/build_versioned_no_call_preflight_contract.py --validate
```

Validation reads committed Git blobs and must not change artifact mtime. Materialization/qualification were
one-time source steps; the CLI has no attempt or observation mode and grants no provisioning or live authority.

The current validators recursively bind the sealed v5-v8 predecessor chain:

```powershell
uv run --offline --frozen pytest -q tests/test_sanitized_sdk_import_bootstrap_successor.py
uv run --offline --frozen python scripts/build_sanitized_sdk_import_bootstrap_successor.py --validate-contract
uv run --offline --frozen python scripts/build_sanitized_sdk_import_bootstrap_successor.py --validate-source
uv run --offline --frozen pytest -q tests/test_sanitized_sdk_bootstrap_parent_successor.py
uv run --offline --frozen python scripts/build_sanitized_sdk_bootstrap_parent_successor.py --validate-contract
uv run --offline --frozen python scripts/build_sanitized_sdk_bootstrap_parent_successor.py --validate-source
```

These validations do not read/stat `.env` or grant an attempt. Historical v1-v6 read-only commands remain in their
own scripts and Git history; do not use creation/run modes. V7 is consumed and validation is read-only.

## Audit the sealed D-142 source

D-142's post-commit validator is bound to its exact clean historical gate+10-doc evidence checkout. It correctly
rejects a later documentation HEAD, so it is not a current quickstart. Audit it only in a separate clean checkout
of that historical commit; never use a creation/external mode. The recorded 170/170 injected/mocked count remains
separate local contract evidence and performs no external observation.

## Historical validators

D-123 through D-142 commands remain in their owning scripts, tests and Git history. Use only explicit
sealed/read-only modes in an exact clean historical checkout. D-132 is a consumed incident; D-136 pricing,
D-137 no-call phases and D-138 through D-141 SDK are consumed. D-142 is unactivated and deferred.

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

Large repository-wide suites may include historical tests that intentionally assert a superseded absent state.
Prefer the current focused bundles and explain any historical-state mismatch instead of rewriting sealed
evidence.

## Live execution

There is no supported live A/C or D-142 activation command. The current sequence is offline only:

1. Validate evaluator-v2, consumed v3/v5/v7 and source-qualified v8/v9 read-only.
2. Stop. Next create only a fresh offline v9 state-binding successor; do not observe current state.

Do not repurpose a historical receipt, attempt, marker, gate, template or CLI flag to bypass this sequence.
