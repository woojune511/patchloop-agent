# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and 3M/3600 resource ceiling

`docs/current-status.md` owns the evaluator-v2, reusable-preflight and A/C boundary.

## Implemented product path

- Agent phases: INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE
- Constrained search/read/patch/check/diff/submission tools; no unrestricted agent shell
- Stateless provider turns plus append-only events, checkpoints, CAS and workspace reconciliation
- Rejected-patch recovery and token/cost accounting
- Separate hidden evaluator, receipt-bound v2, successor identity and reusable no-call preflight
- Audited dataset roles and a frozen, human-reviewed three-entry memory index
- Exact A-null/C-D110 delivery with replay and condition-aware trace qualification

## Evidence boundary

- D-098 is a development baseline (12 terminal, 11 evaluated, 2 scope-compliant), not held-out evidence.
- D-110 froze three entries; D-112/D-115 left selective scoring unready. No memory-effect claim exists.
- D-121/D-129-D-141 remain immutable; D-142 stays source-qualified/unactivated and deferred.
- Evaluator-v1 safety was literal PASS, so historical results are not independently safety-verified.
- V3-v23 attempts are immutable historical evidence; V23 ended before evaluator execution at
  `diagnostic_result_invalid`. V24/V25 are source corrections, not readiness evidence.
- The active path reuses unchanged preflight source with append-only attempt IDs. Paid A/C remains blocked until a
  clean execution hash and one campaign-level cost approval exist.

Exact tuples, zero-activity limits and machine-readable evidence are indexed in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --offline --frozen --extra dev
$docsBasetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-docs-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

These validate documentation only and make no external or paid call.

## CLI surface

`uv run --offline --frozen patchloop --help` lists the CLI. The supported fast preflight is no-call; provider
execution still requires its exact execution hash and explicit campaign cost approval.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
