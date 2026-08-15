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
  tests/test_heldout_ac_r16_runtime_evidence_index.py `
  tests/test_heldout_ac_r15_runtime_evidence_index.py `
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
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_r16_campaign_evidence.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_r15_campaign_evidence.py
& .\.venv\Scripts\python.exe -E -s -B scripts/build_heldout_ac_r14_campaign_evidence.py
```

These are offline-only. The builders validate Contract R11, binding R11, materialization R7, execution R8 and
preflight/dispatcher R16, plus immutable R14/R15 and completed R16 indices. They preserve every seal, rerun no row and
grant no runtime/paid authority. The R16 evidence builder reads exact source/candidate/plan/journal/result bytes and
recomputes the matrix summary without provider, evaluator, Docker, SDK or agent calls.

## Paid and preflight forms are closed

The R16 candidate, approval, 48 rows and semantic campaign identity are consumed. Do not instantiate the historical
preflight or campaign command, change its timestamps, resume it or replay rows. The panel is now unblinded, so a future
experiment must first add a separately preregistered fresh design and source-qualified runbook. Only that future
design may define a new no-call output and exact approval form. None exists now.

## Historical commands

R3-R8 development and held-out R7/R11/R14/R15/R16 commands, candidates and approvals are audit-only and must not be
instantiated again. `docs/09-evidence.md`, Git and append-only artifacts preserve their exact forms and limits.

## Verify sealed evidence

Use the checked-in R3-R8 development and held-out R7/R11/R14/R15/R16 evidence indices read-only; never evaluate,
finalize, recover or resume these identities. R11/R14/R15 corrections add accounting/attribution only; R16 records
the completed official frozen-panel analysis. Raw state stays under `.patchloop`.

## Static checks

```powershell
& .\.venv\Scripts\ruff.exe check patchloop tests
& .\.venv\Scripts\ruff.exe format --check patchloop tests
& .\.venv\Scripts\python.exe -E -s -B -m compileall -q patchloop tests
git diff --check
```

Historical attempts stay immutable. No current preflight or paid execution is authorized.
