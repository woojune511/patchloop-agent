# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that constrain current work.

## Effective decisions

Order: evaluator correctness v2 -> successor A/C qualification -> local preflight -> exact campaign approval ->
four-run development A/C readiness -> preregister held-out A/C -> separately authorize execution -> B/D.

### 2026-08-15 — preserve R11 and split evaluator trust domains

- R11 is an immutable 2-settled/1-observed-unsettled/45-not-started campaign. Its correction index may add durable
  cost accounting and deterministic post-runtime attribution, but cannot rewrite `CONTRACT_ERROR`, settle row 3 or
  authorize analysis.
- Raw registered-check controls are replaced by role-prefixed opaque identities. Evaluator-private checker redactions
  are diagnostic; agent-visible event/patch matches alone drive marker-leak verdicts. Control self-collision and actual
  untrusted marker escape use distinct stable codes.
- Persisted rows remain unofficial and analysis-ineligible. Official completion requires exact runtime-issued,
  non-serialized provenance for all 48 rows; historical replay validates bytes without minting that authority.
- Paid campaign identity excludes transient readiness observations and is one-use. A complete plan is validated before
  journal creation; terminal/cost evidence is atomic, started usage precedes qualification, and typed codes—not error
  prose—select confound phase.
- Contract R7, binding R8, materialization R4, execution R5 and preflight/dispatcher R13 are source qualification only.
  They create no candidate, approval, observation, call or spend.

### 2026-08-14 — isolate held-out contracts from historical execution

- The 48-row suite uses dedicated strict models and a metadata-only loader, not `ExperimentSuite` or the live runner.
- Historical completion fixtures remain unofficial. Official held-out analysis may be produced only after 48 exact
  persisted-v2 authenticated and settled rows; any confound seals the matrix inconclusive.
- R7 sealed after CRLF/LF qualification-byte drift. R11 later consumed a fresh approval and also sealed inconclusive;
  neither campaign may retry, resume or transfer authority.
- Materialization R1 owns the sole public pricing GET. Current R4 reuses those exact prices with zero added GET and
  omits runtime secrets, private values/outcomes, final contracts, candidate and spend.

### 2026-08-13 — fast-track attempts, not one-use configurations

- Attempts remain append-only. Local preflight is read-only and bounded to three attempts, while paid campaigns are
  one-use by semantic source/suite/schedule identity even if transient readiness observations differ.
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

D-122 through D-141 and V1-V25 attempt artifacts remain immutable. Their old gates neither prohibit bounded local
no-call preflight nor authorize paid execution. Current status, artifacts and Git/archive retain separate authority.

## Open questions

1. Should later B/D use this design family or a fresh panel?
2. Should exact qualification-leaf symlink provenance be hardened beyond current root containment, hashing and clean
   Git checks before a future candidate?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
