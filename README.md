# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair.
Agent, hidden evaluator, recovery state and cross-run memory evidence remain separate.

## Current direction

The 96-run A/B/C/D campaign is deferred. The checked-in readiness panel is:

- A: no cross-run memory
- C: the exact three-entry structured bundle
- Moto and Babel, one A/C pair each
- identical model, prompt, tools, context policy and the R8 split-budget runtime tuple

R3-R6 are sealed `inconclusive`; their distinct stops are indexed in `docs/09-evidence.md`. R7/R9 was superseded
unexecuted after offline contract audits. R10 qualified the exact R8 source. R8 completed all four rows at `$0.3664215`; an append-only
correction fixes its stale v1/v2 completion projection without rewriting runtime evidence.
The 48-row held-out A/C design has a metadata-only suite. R7 sealed after one unsettled row. R11 candidate
`sha256:f48a0de...a6b0` then consumed its `$252`/`$275` approval and sealed 2 settled/1 observed-unsettled/45
not-started: settled cost was `$0.15699525`, total observed-started cost was `$0.41801625`, and no complete matrix or
memory claim follows. Development-only evidence lowers a future equal-A/C campaign to 1M/100k/1.1M and `$57.60`/`$60`.
Contract R8 → binding R9 → materialization R5 → execution R6 → preflight R14 remains zero-authority.

## Implemented product path

- Agent phases: INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE
- Constrained search/read/patch/check/diff/submission tools; no unrestricted agent shell
- Stateless provider turns plus append-only events, checkpoints, CAS and workspace reconciliation
- Rejected-patch recovery and token/cost accounting
- Separate hidden evaluator, receipt-bound v2, opaque private-control identities and reusable no-call preflight
- Audited dataset roles and a frozen, human-reviewed three-entry memory index
- Exact A-null/C-D110 delivery, atomic cost/journal evidence and authenticated completion replay

## Evidence boundary

- D-098 is a development baseline (12 terminal, 11 evaluated, 2 scope-compliant), not held-out evidence.
- D-110 froze three entries; D-112/D-115 left selective scoring unready. No memory-effect claim exists.
- D-121/D-129-D-141 remain immutable; D-142 stays source-qualified/unactivated and deferred.
- Evaluator-v1 safety was literal PASS, so historical results are not independently safety-verified.
- V3-v23 attempts are immutable historical evidence; V23 ended before evaluator execution at
  `diagnostic_result_invalid`. V24/V25 are source corrections, not readiness evidence.
- R8 is the first complete four-row receipt-qualified development matrix. Both A and C resolved twice; this enables
  descriptive paired analysis, not a causal, held-out or general memory-effect claim.
- R10/R8 applies equal A/C limits of 3M input, 350k output, 3.35M aggregate, 25k per response, 180/300 model/tool calls
  and 3,600 seconds. Its price-aware reserve is `$3.825`/row, `$15.30`/panel and `$18` hard cap.
- Those thresholds come from one observed R3 development row: they are neither held-out-safe nor a completion claim.
  R8 candidate `sha256:60c67908...cff9e` and all R3-R8 approvals are consumed; no identity may resume.
- Held-out R7 and R11 are inconclusive and consumed. R11's evaluator-private redaction false positive and control
  self-collision are corrected only in successor source; historical verdicts stay immutable. There is no current
  candidate, approval, B/D authority or official held-out analysis.

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

`uv run --offline --frozen patchloop --help` lists the CLI. R8, held-out R7 and held-out R11 are historical/consumed.
Any future provider campaign requires a fresh clean no-call output, exact execution hash and explicit cost approval.

## Documentation

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
