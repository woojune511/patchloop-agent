# PatchLoop

PatchLoop is a recoverable single coding agent and evaluation harness for scope-compliant software repair. The agent
is the product; hidden evaluation, recovery state and cross-run memory evidence are supporting layers.

## Current direction

The 96-run A/B/C/D campaign is deferred. The consumed development-readiness panel compared no memory (A) with the
exact three-entry D-110 bundle (C) on Moto and Babel under an otherwise fixed runtime. R10-qualified R8 completed all
four rows for `$0.3664215`; its stale v1/v2 completion projection is corrected append-only. This is descriptive
workflow readiness, not a causal or general memory result.

The held-out 48-row design remains incomplete. R7 sealed 0 settled/1 unsettled/47 not-started. R11 candidate
`sha256:f48a0de...a6b0` sealed 2 settled/1 observed-unsettled/45 not-started with `$0.15699525` settled and
`$0.41801625` observed-started. R14 candidate `sha256:67475f57...307fd` consumed its `$57.60`/`$60` approval and
sealed 0 settled/1 observed-unsettled/47 not-started with `$0.126342` observed.

R14's historical `DURABLE_EVIDENCE_AUTHENTICATION_FAILED` is unchanged. Deterministic successor attribution is
`TRACE_QUALIFICATION_RUNTIME_BUDGET_AUTHORITY_MISMATCH`: candidate 1M/100k/1.1M limits were compared with immutable
suite 4M/500k/4.5M limits. No retry, reauthentication, reclassification, official analysis or memory claim follows.
Contract R10 → binding R10 → materialization R6 → execution R7 → preflight R15 is current zero-authority source.

## Implemented path

- INTAKE → REPRODUCE → PLAN → IMPLEMENT → VERIFY → REVIEW → DONE with constrained tools, append-only events,
  checkpoints, CAS, reconciliation, rejected-patch recovery and token/cost accounting
- Separate hidden evaluator; receipt-bound v2, opaque private-control identities and authenticated completion
- Audited dataset roles; A-null/C-D110 delivery; no selective retrieval authority
- Candidate-v3 realized-schedule identity, candidate-bound runtime/cost, atomic evidence and exact historical replay

Evaluator-v1 still assigns literal safety PASS, so historical results are not independently safety-verified. D-142
stays source-qualified/unactivated/deferred. R8 and held-out R7/R11/R14 are consumed; none may resume or transfer
approval. There is no current candidate, approval, provider/B/D authority or official held-out analysis.

Exact tuples, provenance and zero-activity limits are in `docs/09-evidence.md`.

## Offline quickstart

```powershell
uv sync --offline --frozen --extra dev
$docsBasetemp = Join-Path 'C:\Users\geonj\AppData\Local\Temp' ('patchloop-docs-' + [guid]::NewGuid())
& .\.venv\Scripts\python.exe -E -s -B -m pytest -q -p no:cacheprovider `
  --basetemp $docsBasetemp tests/test_documentation_structure.py
git diff --check
```

These checks make no external or paid call. `uv run --offline --frozen patchloop --help` lists the CLI. A future
provider campaign needs committed qualified source, a fresh clean no-call output and separate exact cost approval.

Use `docs/00-index.md` for active authority/navigation. Historical narratives live under `docs/archive/`.
