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

### Historical execution gates remain closed

D-122 through D-131 are immutable predecessors indexed in `docs/09-evidence.md` and Git history. D-127 through
D-129 are consumed/terminal and are never retried or repaired. Planning values, source qualification and
self-attested readiness grant no external, hash/candidate, cost or A/C authority.

### 2026-08-08 — active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and `docs/09-evidence.md` index.
- Historical narratives: `docs/archive/`.
- Repeating every milestone in every topic document is discontinued.

Earlier retained decisions remain discoverable in the archived ledger and `docs/09-evidence.md`; they do not
replace the current D-132 offline gate or reopen consumed D-128/D-129 receipts.

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

### 2026-08-09 — D-129 through D-131 preserve the predecessor boundary

D-129 failed closed because a docs open preceded receipt/attempt; transport count is unknown. D-130 separated
local admission from external activation. D-131 later materialized exact receipt-only and armed-intent-only
commits with external actions zero. Earlier unexercised approval/challenge text cannot cross later topology.

### 2026-08-09 — D-132 qualifies attempt-first external activation source

- Gate `d132_ae224ab320e74bf871b74b0c9df23f88c5de170dfd26e7724aa234f29b2b0ba7` binds source commit
  `ccf898d869342a9d5da42a1fef2c00e593fe91b4` as the sole child of the D-130 armed-intent commit.
- Activation receipt creation must precede external work in a receipt-only commit. Docker, official pricing and
  no-call SDK/credential preflight each require an attempt-only commit, an immediate action-started marker and a
  committed terminal transition before the next phase.
- Started-without-terminal, orphaned attempt and blocked terminal states are consumed and non-retryable.
  A ready final gate still grants no execution-hash/candidate, cost or A/C authority.
- The earlier request/challenge explicitly said it was not activation and is non-reusable after this topology
  change. Only a fresh exact D-132-qualified activation quoting all gate/evidence/receipt/intent commit tuples
  may begin the sequence.
