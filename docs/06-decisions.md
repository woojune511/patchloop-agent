# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that constrain current work.

## Effective decisions

Completed order: evaluator correctness v2 -> successor A/C qualification -> local preflight -> exact campaign approval ->
four-run development A/C readiness. R3 through R6 were inconclusive; R8 completed the matrix. Current
order: preserve/correct R8 evidence -> preregister held-out A/C (complete, execution-closed) -> offline qualification
-> separately authorize execution -> B/D after their own frozen contracts.

### 2026-08-14 — isolate held-out contracts from historical execution

- The 48-row suite uses dedicated strict models and a metadata-only loader, not `ExperimentSuite` or the live runner.
- Completion and analysis code is source-qualified only as an offline-untrusted fixture/preview. It cannot authenticate
  runtime files, claim official analysis or create candidate/approval/spend authority.
- R1 is the pre-seal-race predecessor; R2 binds fixture source. R5 binds the 12-task metadata plan and hardened
  materializer/authenticator while replaying R2. R3/R4 preserve pre-hardening/pre-format source.
- Materialization R1 records 12 opaque evaluator templates and one fresh public pricing GET. It deliberately excludes
  runtime secrets/final contracts, outcomes, candidate and spend; existing R8 authority cannot transfer.
- Execution-contract R1 source-qualifies candidate/manifest/ephemeral marker expansion; preflight R2 source-qualifies
  clean Git, local image, SDK and credential-presence checks. Their source artifacts authorize no observation or run.

### 2026-08-14 — preserve R3-R6 and correct runtime evidence before a fresh panel

- R3-R6 remain sealed, consumed and non-transferable. Their successive token, paid-plan, qualification and runtime
  binding failures and exact costs live in `docs/09-evidence.md`; no A/C or memory-effect claim follows.
- R7/R9 and its no-call candidate are superseded unexecuted after API-free contract audits.
- R10 qualified the exact contract-hardened R8 execution source while R6/R8 and earlier predecessors remain
  immutable.
- R8 keeps A-null/C-exact-three with equal limits: 3M input, 350k output, 3.35M aggregate, 25k/response, 180 model,
  300 tool and 3,600 seconds; full-price reserve is `$3.825`/row, `$15.30`/panel and `$18` cap.
- R8 candidate `sha256:60c67908...cff9e` consumed one exact approval, completed all four qualified rows and settled
  `$0.3664215`. Its immutable raw result used a stale v1 qualification-envelope check; the append-only correction
  records the complete v2 matrix without rewriting runtime evidence.
- Both A and C resolved twice. Lower C token/cost observations are descriptive development results only; no causal,
  held-out, retrieval or general memory-effect claim follows. R8 cannot rerun.

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

1. Should later B/D use this design family or a fresh panel?
2. What separately qualified source and refreshed price should back a future candidate?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
