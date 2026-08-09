# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that currently constrain
work.

## Effective decisions

### 2026-08-08 — start with A/C readiness, not the full four-condition campaign

- First matrix: Moto and Babel development-validation tasks x A/C x one repetition = four rows.
- Purpose: runtime delivery/readiness, not held-out performance.
- Full A/B/C/D 96-run campaign is deferred, not deleted.
- A missing or confounded row makes the matrix inconclusive; no row-only replacement is allowed.

One repetition provides no variance estimate and supports no statistical, causal, held-out,
cross-repository, per-rule or negative-transfer-rate claim.

### 2026-08-08 — C is an exact fixed bundle

- C receives all three approved D-105 texts in frozen D-110 `group_provenance` order on every model request.
- A carries the same policy version with null memory.
- No embedding, similarity, rerank or threshold is used; this does not grant selective-retrieval authority.

### Historical execution gates remain closed

D-122 through D-134 are immutable predecessors indexed in `docs/09-evidence.md` and Git history. D-127 through
D-129 and the exercised D-132 pricing phase are consumed and never retried or repaired. D-134's preserved gate
is invalid and non-authoritative for terminalization. Planning values, source qualification and self-attested
observations grant no hash/candidate, cost or A/C authority.

### Active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and the index in `docs/09-evidence.md`.
- Historical narratives: `docs/archive/` and Git history.

Earlier decisions cannot replace the current D-135 gate or reopen a consumed receipt, attempt or marker.

### 2026-08-09 — D-129 through D-131 preserve the predecessor boundary

D-129 failed closed because a docs open preceded receipt/attempt; transport count is unknown. D-130 separated
local admission from external activation. D-131 materialized receipt-only and armed-intent-only commits with
external actions zero. Those artifacts are immutable predecessors, not reusable activation authority.

### 2026-08-10 — D-132 pricing is consumed; D-135 is the correction authority

- D-132's exact activation was exercised through the pricing attempt and action-started marker. The
  application-level unauthenticated `client.send` returned one `Response`, but underlying HTTP request
  count/completion and response status, headers, body and redirects are unknown/unretained.
  Completed/replayable canonical pricing evidence count is 0, its artifact is absent, replay bytes are 0,
  and the activation/attempt is consumed with no retry or backfill.
- D-133 preserved the marker. D-134 implemented a procedural-terminal path, but its emitted gate contained an
  ambiguous numeric GET-count claim. That exact gate is preserved append-only and is invalid and
  non-authoritative; its recorded status and next-gate text grant no terminalization authority.
- D-135 source commit `ca50402aa8d3965ea384563262c713c6090d2ecf` removes the ambiguity in a distinct
  gate/future-terminal contract. Gate
  `d135_7e67561d187cfb44440790052a95fc8b95a4006fe886e0f7c3dce9bae437e8c6` requires a fresh exact
  terminalization approval. The D-135 procedural terminal is absent, and current-turn external actions are zero.
- A future terminalization may create only the exact D-135 procedural terminal and its terminal-only commit.
  Pricing repair, fixed-successor qualification, external preflight, hash/candidate, cost and A/C remain
  separately gated.

## Superseded sequencing

- Running the full A/B/C/D matrix immediately is superseded by A/C readiness first.
- Continuing D-121 isolation before any C test is paused; D-121 is not a fixed-bundle prerequisite.
- No sealed artifact, measured result or authority statement is rewritten by this priority change.

## Open questions

1. After readiness passes, should a held-out A/C design use all 12 tasks with repetitions or a separately
   preregistered exploratory subset?
2. When, if ever, should B/raw-trace and D/selective return to the critical path?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
