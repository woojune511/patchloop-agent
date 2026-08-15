# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair. The agent
is the product; hidden evaluation, recovery state and cross-run memory evidence are supporting layers.

## Current direction

The 96-run A/B/C/D campaign is deferred. The consumed development-readiness panel compared no memory (A) with the
exact three-entry D-110 bundle (C) on Moto and Babel under an otherwise fixed runtime. R10-qualified R8 completed all
four rows for `$0.3664215`; its stale v1/v2 completion projection is corrected append-only. This is descriptive
workflow readiness, not a causal or general memory result.

The preregistered held-out A/C panel is now complete. R16 candidate `sha256:24044c1e...8813` consumed one exact
48-row `$57.60`/`$60` approval and settled all 48 rows for `$27.24465825`: 15 resolved, 14 task failures and
19 typed agent failures. No-memory succeeded on 8/24 rows and structured on 7/24, an official frozen-panel
structured-minus-no-memory estimate of `-1/24` (-4.17 percentage points). The deterministic descriptive stability
interval is `[-1/4, 1/6]`; it is not a population confidence interval or a causal/general memory result.

Earlier R7/R11/R14/R15 campaigns remain immutable inconclusive predecessors. R11 sealed 2 settled/1
observed-unsettled/45 not-started at `$0.41801625` observed-started; R14 sealed 0/1/47 at `$0.126342`; R15 sealed
2/1/45 at `$1.112112` observed-started.

R14's historical `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` is unchanged. Deterministic successor attribution is
`TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH`: candidate 1M/100k/1.1M limits were compared with immutable
suite 4M/500k/4.5M limits. No retry, reauthentication, reclassification, official analysis or memory claim follows.
R15's historical reason is also unchanged; its successor diagnosis is
`TRACE_QUALIFICATION_V2_TERMINAL_RESULT_SCHEMA_MISMATCH`.
Contract R11 → binding R11 → materialization R7 → execution R8 → preflight R16 is the consumed source chain for
the complete R16 result; its append-only index made no new runtime call or spend.

## Implemented path

- INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE with constrained tools, append-only events,
  checkpoints, CAS, reconciliation, rejected-patch recovery and token/cost accounting
- Separate hidden evaluator; receipt-bound v2, opaque private-control identities and authenticated completion
- Audited dataset roles; A-null/C-D110 delivery; no selective retrieval authority
- Candidate-v3 realized-schedule identity, candidate-bound runtime/cost, atomic evidence and exact historical replay

Evaluator-v1 still assigns literal safety PASS, so historical results are not independently safety-verified. D-142
stays source-qualified/unactivated/deferred. R8 and held-out R7/R11/R14/R15/R16 are consumed; none may resume or
transfer approval. R16 has official analysis for this frozen panel only. There is no current candidate, approval,
provider/B/D authority or causal/general memory-benefit claim.

Exact tuples, provenance and zero-activity limits are in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --offline --frozen --extra dev
$docsBasetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-docs-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

These checks make no external or paid call. `uv run --offline --frozen patchloop --help` lists the CLI. Any future
campaign needs a separately preregistered fresh design, committed qualified source, a clean no-call output and an
exact new cost approval.

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
