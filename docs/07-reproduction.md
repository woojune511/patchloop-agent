# Current reproduction and execution path

Historical D/V commands are preserved in Git and `docs/archive/`; they are not the current runbook.

## Install and validate offline

```powershell
uv sync --offline --frozen --extra dev
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  tests/test_evaluator_v2_contracts.py `
  tests/test_heldout_ac_source_qualification.py `
  tests/test_heldout_ac_binding_source_qualification.py `
  tests/test_heldout_ac_task_pricing_materialization.py `
  tests/test_heldout_ac_execution_source_qualification.py `
  tests/test_heldout_ac_r14_runtime_evidence_index.py `
  tests/test_heldout_ac_persisted_adapter.py `
  tests/test_heldout_ac_completion.py `
  tests/test_heldout_ac_preflight.py `
  tests/test_heldout_ac_dispatcher.py `
  tests/test_heldout_ac_preflight_source_qualification.py `
  tests/test_documentation_structure.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_source_qualification.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_binding_source_qualification.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_task_pricing_materialization.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_execution_source_qualification.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_preflight_source_qualification.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_r14_campaign_evidence.py
```

These are offline-only. The builders validate Contract R10, binding R10, materialization R6, execution R7 and
preflight/dispatcher R15, plus the immutable R14 attribution index. They preserve every seal, rerun no row and grant
no runtime/paid authority. The successor creates no candidate, plan or journal.

## Current held-out no-call preflight

After the exact source is committed and execution-clean, this command checks key presence, Git, SDK and digest-pinned
local Docker images. `--output` is required and must name a nonexistent append-only UTF-8 JSON handoff. The command
neither exports/prints the key nor calls a provider/evaluator/agent and always leaves paid approval false:

```powershell
& .\.venv\Scripts\python.exe -E -s -B scripts/run_heldout_ac_preflight.py `
  --env-file .env `
  --output .patchloop/heldout-ac-preflight-<fresh-id>.json
```

A successful result is only a secret-free candidate for the fixed 48 rows and `$57.60`/`$60`; it cannot dispatch the
campaign. Do not run this form until the R15-bound source is committed and clean. Any later source change requires a
successor qualification and candidate.

## Future held-out paid form — closed until exact approval

After a fresh READY preflight is saved to `candidate.json`, a separate user approval must name its exact execution
hash, 48 rows, `$57.60` reserve and `$60` cap. Only then is this form valid:

```powershell
& .\.venv\Scripts\python.exe -E -s -B scripts/run_heldout_ac_campaign.py `
  --candidate-file candidate.json `
  --env-file .env `
  --approve-live-cost `
  --approved-execution-hash sha256:<exact-new-candidate>
```

Do not run it now. Held-out R7/R11/R14 and their approvals are consumed; current R15 has no candidate or approval.
Rows and semantic paid-campaign identity are one-use, with no retry, replacement or resume.

## Historical commands

R3-R8 development and held-out R7/R11/R14 commands, candidates and approvals are audit-only and must not be instantiated
again. `docs/09-evidence.md`, Git and append-only artifacts preserve their exact forms and limits.

## Verify sealed evidence

Use the checked-in R3-R8 development and held-out R7/R11/R14 evidence indices read-only; never evaluate, finalize,
recover or resume these identities. R11/R14 corrections add accounting/attribution only. Raw state
stays under `.patchloop`.

## Static checks

```powershell
& .\.venv\Scripts\ruff.exe check patchloop tests
& .\.venv\Scripts\ruff.exe format --check patchloop tests
& .\.venv\Scripts\python.exe -E -s -B -m compileall -q patchloop tests
git diff --check
```

Historical attempts stay immutable. Their old one-use configuration policy does not govern this reusable preflight.
