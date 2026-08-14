# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that constrain current work.

## Effective decisions

Order: evaluator correctness v2 -> successor A/C qualification -> local preflight -> exact campaign approval ->
four-run development A/C readiness -> preregister held-out A/C -> separately authorize execution -> B/D.

### 2026-08-14 — isolate held-out contracts from historical execution

- The 48-row suite uses dedicated strict models and a metadata-only loader, not `ExperimentSuite` or the live runner.
- Historical completion fixtures remain unofficial. Official held-out analysis may be produced only by the R7
  dispatcher after 48 exact persisted-v2 authenticated and settled rows; any confound seals the matrix inconclusive.
- R1 is the pre-seal-race predecessor; R2 binds fixture source. R5 binds the 12-task metadata plan and hardened
  materializer/authenticator while replaying R2. R3/R4 preserve pre-hardening/pre-format source.
- Materialization R1 records 12 opaque evaluator templates and one fresh public pricing GET. It deliberately excludes
  runtime secrets/final contracts, outcomes, candidate and spend; existing R8 authority cannot transfer.
- Execution-contract R1 source-qualifies candidate/manifest/ephemeral marker expansion; preflight R2 source-qualifies
  clean Git, local image, SDK and credential-presence checks. Their source artifacts authorize no observation or run.
- Preflight/dispatcher R7 binds current preflight, approval plan, dispatcher, finalizer and replay; pre-row guard
  failure now consumes the plan at `$0`. R3-R6 are predecessors. It grants no
  candidate, approval, provider call or spend; execution still needs a fresh clean candidate and exact approval.

### 2026-08-14 — preserve R3-R6 and correct runtime evidence before a fresh panel

- R3-R6 are sealed; R7/R9 is superseded. R10/R8 completed four exact qualified rows for `$0.3664215`; its stale
  v1/v2 projection is corrected append-only. Exact limits, failures and hashes live in `docs/09-evidence.md`.
- R8 cannot rerun or transfer approval. Its successes and lower observed C usage are development descriptions, not
  causal, held-out, retrieval or general memory-effect evidence.

### 2026-08-13 — fast-track attempts, not one-use configurations

- Attempts remain append-only; semantic changes require a successor, while unchanged source may use a new attempt ID.
  Local preflight is read-only and bounded to three attempts.
- Paid execution needs one approval binding exact source/hash/schedule/runtime/reserve/cap. Rows are one-use; a
  confound seals the panel, and any rerun is a disclosed fresh full campaign.

### 2026-08-11 — evaluator correctness precedes paid A/C

- Evaluator-v1's literal safety PASS is not independent four-verdict evidence. V2 uses typed evidence and receipts;
  raw results remain `official=false`. D-142 stays source-qualified, unactivated and deferred.

### 2026-08-08 — start with A/C readiness

- First matrix: Moto and Babel development-validation tasks × A/C × one repetition = four rows.
- A uses null memory. C receives the exact three D-105 texts in frozen D-110 `group_provenance` order on every model
  request. No embedding, similarity, rerank or threshold participates.
- The panel diagnoses workflow delivery/readiness, not held-out performance. One repetition provides no variance
  estimate and supports no causal, general, cross-repository, per-rule or negative-transfer claim.
- Full A/B/C/D is deferred. B/D require independent redaction/calibration and, if designed after A/C unblinding, a
  separate fresh held-out panel.

## Historical execution boundaries

D-122 through D-141 and V1-V25 attempt artifacts remain immutable. They are not repaired, overwritten or deleted.
Their old one-use gates do not prohibit new fast-track attempts with unchanged source; neither do they authorize paid
execution. `docs/current-status.md` owns the current path, `reports/` owns exact artifacts and Git/archive own history.

## Open questions

1. Should later B/D use this design family or a fresh panel?
2. What separately qualified source and refreshed price should back a future candidate?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
