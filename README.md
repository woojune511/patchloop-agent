# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and the R8 split-budget runtime tuple

R3 attempted the four-row readiness panel once and sealed it `inconclusive`: Moto A resolved through receipt-qualified
evaluator v2, Moto C could not fund the exact next request within the 3M ceiling before submission, and both Babel
rows were not started.
R3 through R6 are sealed `inconclusive`. R4 stopped before provider dispatch at `$0`; R5 and R6 each resolved Moto A
through evaluator v2 but failed distinct post-evaluator qualification contracts, so their remaining rows did not
start. R7/R9 was superseded unexecuted after offline contract audits found type and evidence-binding gaps. R10 now
qualifies the contract-hardened R8 source offline; R8 has no preflight candidate, approval or run.
`docs/current-status.md` owns the exact tuple and next gate.

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
- R3 preserves one receipt-qualified live v2 success; R5 and R6 add resolved/evaluated but trace-unqualified rows. None
  yields an analyzable A/C pair or memory-effect claim.
- R10/R8 applies equal A/C limits of 3M input, 350k output, 3.35M aggregate, 25k per response, 180/300 model/tool calls
  and 3,600 seconds. Its price-aware reserve is `$3.825`/row, `$15.30`/panel and `$18` hard cap.
- Those thresholds come from one observed R3 development row: they are neither held-out-safe nor a completion claim.
  The old R7 candidate `sha256:8b962b80...bf6c` is superseded and cannot authorize R8. R8 needs a clean-commit
  no-call preflight and a newly bound approval; R3-R6 are never resumed. Held-out A/C and B/D remain closed.

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

`uv run --offline --frozen patchloop --help` lists the CLI. The supported fast preflight is no-call. Any future
provider campaign requires a fresh exact execution hash and explicit cost approval.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
