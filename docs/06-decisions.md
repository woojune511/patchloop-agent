# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that constrain current work.

## Effective decisions

Completed order: evaluator correctness v2 -> successor A/C offline qualification -> supported local preflight ->
execution candidate -> one campaign approval -> four-run A/C readiness. R3 through R6 were inconclusive. Current order:
R8/R10 offline source qualification -> bounded no-call preflight -> full-panel candidate -> exact `$18` approval ->
fresh four-row readiness execution -> valid complete-matrix gate -> held-out A/C -> B/D.

### 2026-08-14 — preserve R3-R6 and correct runtime evidence before a fresh panel

- R3 is sealed `inconclusive` and never resumed: Moto A passed v2, Moto C hit 3M before submission, and Babel did not
  start. No A/C direction or memory-effect claim follows.
- R4's exact approval was consumed once. It sealed before provider dispatch at `$0` because paid-plan revalidation
  selected the legacy budget; Moto A terminated and the other rows did not start. R4 and its R6 source qualification cannot retry or transfer
  approval.
- R5's exact approval was consumed once. Moto A resolved and passed evaluator v2, but terminal qualification still
  expected the legacy null-call/aggregate-only profile; the other rows did not start and cost settled at `$0.19303425`.
- R6's exact approval was consumed once. Moto A resolved and passed evaluator v2, but runtime evidence recorded the
  legacy call-guard policy; the other rows did not start and cost settled at `$0.169596`.
- R7/R9 and its no-call candidate are superseded unexecuted after API-free contract audits.
- R10 offline-qualifies contract-hardened R8 while R6/R8 and earlier predecessors remain immutable.
- R8 keeps A-null/C-exact-three with equal limits: 3M input, 350k output, 3.35M aggregate, 25k/response, 180 model,
  300 tool and 3,600 seconds; full-price reserve is `$3.825`/row, `$15.30`/panel and `$18` cap.
- Those R3-informed thresholds are not held-out-safe or a completion/benefit claim. R8 has no candidate; next is a
  clean bounded no-call preflight and then a new exact-hash/`$18` approval.

### 2026-08-13 — fast-track attempts, not one-use configurations

- Append-only applies to observed attempt records. An attempt is never edited or erased, but unchanged source,
  configuration and campaign definitions remain reusable.
- Semantic changes require a new version; ordinary reruns get only a new `attempt_id`.
- One supported local preflight performs read-only Docker and no-dispatch SDK checks, at most three attempts, with no
  state artifact or per-attempt approval prose.
- Provider execution needs one campaign approval binding exact hash/source/schedule/runtime/reserve/cap and grants no
  held-out or B/D authority.
- Campaign rows are single-attempt. Any infrastructure or outcome-bearing row failure ends the panel as inconclusive;
  retry requires a disclosed fresh full panel.
- Historical D/V artifacts and their `retry=false` fields remain exact evidence. This policy supersedes their
  one-use configuration as the active execution design without rewriting them.

### 2026-08-11 — evaluator correctness precedes paid A/C

- Evaluator-v1's literal safety PASS does not satisfy four-verdict success. Historical v1 results remain immutable
  and are not presented as independently safety-verified.
- Evaluator-v2 uses new identities; typed evidence, aggregation, receipt and completion are locally verified, while
  raw results remain `official=false`.
- D-142 remains source-qualified, unactivated and deferred. It is not relabeled as v2 qualification.
- `docs/09-evidence.md` owns immutable V1-V25 observations.

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
