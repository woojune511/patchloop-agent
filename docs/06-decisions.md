# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that constrain current work.

## Effective decisions

Current order: evaluator correctness v2 -> successor A/C offline qualification -> supported local preflight ->
execution candidate -> one campaign approval -> four-run A/C readiness -> held-out A/C -> B/D.

### 2026-08-13 — fast-track attempts, not one-use configurations

- Append-only applies to observed attempt records. An attempt is never edited or erased, but unchanged source,
  configuration and campaign definitions remain reusable.
- A new contract version is required only when schema, evaluator semantics, security boundary, treatment or another
  experiment-defining input changes. A transient failure or ordinary rerun gets a new `attempt_id`, not a new V-number.
- Read-only Docker readiness, exact-key-only `.env` loading and fixed-placeholder/no-dispatch SDK diagnostics use one
  supported local preflight with at most three pre-provider attempts. They need no state artifact, exact approval
  paragraph or per-attempt chat gate.
- Provider execution remains separately gated. One campaign approval binds the exact execution hash, evaluator-v2 source,
  four-row schedule, model/runtime tuple, full-schedule reserve and hard cap. It covers the campaign rather than each
  row separately and grants no held-out or B/D authority.
- Campaign rows are single-attempt. Any infrastructure or outcome-bearing row failure ends the panel as inconclusive;
  retry requires a disclosed fresh full panel.
- Historical D/V artifacts and their `retry=false` fields remain exact evidence. This policy supersedes their
  one-use configuration as the active execution design without rewriting them.

### 2026-08-11 — evaluator correctness precedes paid A/C

- Evaluator-v1's literal safety PASS does not satisfy four-verdict success. Historical v1 results remain immutable
  and are not presented as independently safety-verified.
- Evaluator-v2 and the successor A/C source use new source, runtime and suite identities. Their typed safety evidence,
  fail-closed aggregation, receipt, persistence, qualification and completion path are locally verified.
- Raw v2 results remain `official=false`; the receipt-qualified completion adapter is the authority used by A/C.
- D-142 remains source-qualified, unactivated and deferred. It is not relabeled as v2 qualification.
- Historical V1-V25 attempts remain in `docs/09-evidence.md`. V23 ended before evaluator execution with
  `diagnostic_result_invalid`; V24/V25 are correction/wrapper source evidence, not live readiness results.

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

## Superseded sequencing

- A new V-number, state artifact, approval artifact and exact immediate-run paragraph for every local preflight.
- Treating a failed attempt as consumption of otherwise unchanged source/configuration.
- Activating D-142 or continuing D-121 isolation before fixed-bundle A/C readiness.
- Running the full A/B/C/D matrix before the small A/C readiness panel.

## Open questions

1. Before held-out A/C, what exact 12-task × A/C × repetition schedule, analysis and cost cap should be frozen?
2. Should B/D be frozen before A/C unblinding, or use a separate fresh held-out panel afterward?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
