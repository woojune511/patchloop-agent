# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that currently constrain
work.

## Effective decisions

### 2026-08-08 — start with A/C readiness, not the full four-condition campaign

- First matrix: Moto and Babel development-validation tasks × A/C × one repetition = four rows.
- Purpose: runtime delivery/readiness, not held-out performance.
- Full A/B/C/D 96-run campaign is deferred, not deleted.
- The historical `experiments/core.template.yaml` remains immutable.

Reason: C runtime delivery has never executed. A four-row validation panel can expose delivery, leakage,
qualification and process failures without consuming held-out results or paying for conditions whose inputs
are not ready.

### 2026-08-08 — C is an exact fixed bundle

- C receives all three approved D-105 texts in frozen D-110 `group_provenance` order.
- The exact bundle is delivered on every C model request; A carries the same policy version with null memory.
- No embedding, similarity, rerank or threshold is used.
- This is not selective retrieval and does not change D-110 authority.

Reason: D-112/D-115 showed the current scorer is not ready. Mixing it into C would confound structured-memory
delivery with retrieval quality.

### 2026-08-08 — four rows are diagnostic only

- One repetition provides no variance estimate.
- No statistical, causal, held-out, cross-repository, per-rule or negative-transfer-rate claim is allowed.
- A missing/confounded row makes the entire matrix inconclusive; no row-only replacement.

### 2026-08-08 — D-122 stops before execution authorization

- The exact four-row suite and A/C trace qualifier are sealed as offline source evidence.
- The `$54.45` worst-case reserve and proposed `$55` cap are planning values only.
- A live candidate waits for durable full-schedule reservation, a four-row completion gate, clean committed
  source, fresh pricing and a separately authorized no-call environment preflight.

### 2026-08-09 — D-125 qualifies local finalization source only

- R2 binds an up-front four-row reserve, usage-derived settlement and exact complete-matrix gate.
- D-124 is preserved as the settlement-reconciliation predecessor.
- D-125 qualifies repository-local at-most-once row consumption and mocked fault-boundary finalization
  recovery; it does not claim cross-store/global/cross-clone, actual-kill or power-loss guarantees.
- The next exact-D-125 approval may cover only clean source, fresh pricing and a no-call environment preflight.
  Execution-hash/candidate creation and later $55 live approval remain separate gates.

### 2026-08-08 — active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and `docs/09-evidence.md` index.
- Historical narratives: `docs/archive/`.
- Repeating every milestone in every topic document is discontinued.

## Retained milestone decisions

| Decision | Effective consequence |
| --- | --- |
| D-074 | Generic V2/V5 agent remains the comparison baseline; task-specific V10/V11 changes are not silently promoted. |
| D-096/D-097 | Comparison runtime uses the dated gpt-5.4-mini, tool v2, phase-evidence-v5 and high-headroom 3M/3600 tuple. |
| D-098 | No-memory development baseline is sealed; it is not a held-out memory-effect result. |
| D-103–D-105 | Exactly three reviewed groups and exact model-facing renderings are admitted. |
| D-108 | The full rendered bundle added 702 input tokens in the exact provider count pair. |
| D-110 | The three-entry index is frozen, while retrieval/injection authority remains false. |
| D-112/D-115 | Selective ranking is not ready; threshold/weight-only correction is rejected. |
| D-121 | No-start Docker readiness is sealed; actual successor execution remains separately gated and deferred. |
| D-122 | Exact A/C suite and trace qualification are sealed offline; no execution candidate or live authority exists. |
| D-123 | Historical R2 source seal; post-seal audit found stale runtime settlement reconciliation. |
| D-124 | Historical settlement-reconciliation correction; validate sealed-historical. |
| D-125 | Local/mock runtime-finalization source qualified; candidate and live authority remain blocked. |

## Superseded sequencing

- “Run the full A/B/C/D matrix immediately” is superseded by the A/C readiness-first sequence.
- “Continue D-121 isolation work before any C test” is paused. D-121 remains valid evidence but is not a
  prerequisite for a scorer-free fixed-bundle adapter.
- No sealed artifact, measured result or prior authority statement is rewritten by this priority change.

## Open questions

1. After readiness passes, should the next A/C held-out design use all 12 tasks with repetitions, or a separately
   pre-registered exploratory subset?
2. When, if ever, should B/raw-trace and D/selective return to the critical path?

These questions do not authorize implementation beyond `docs/05-implementation-plan.md`.
