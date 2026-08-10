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

D-122 through D-138 are immutable predecessors indexed in `docs/09-evidence.md` and Git history. Consumed
pricing, Docker and SDK attempts are never retried or repaired. Planning values, observations and source
qualification grant no hash/candidate, cost or A/C authority.

### Active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and the index in `docs/09-evidence.md`.
- Historical narratives: `docs/archive/` and Git history.

Earlier decisions cannot replace the current D-139 gate or reopen a consumed receipt, attempt or marker.

### 2026-08-09 — D-129 through D-131 preserve the predecessor boundary

D-129 failed closed because a docs open preceded receipt/attempt; transport count is unknown. D-130 separated
local admission from external activation. D-131 materialized receipt-only and armed-intent-only commits with
external actions zero. Those artifacts are immutable predecessors, not reusable activation authority.

### 2026-08-10 — D-132 is sealed; D-136 succeeds; D-137/D-138 are consumed; D-139 qualifies source

- D-132's exact activation was exercised through the pricing attempt and action-started marker. The
  application-level unauthenticated `client.send` returned one `Response`, but underlying HTTP request
  count/completion and response status, headers, body and redirects are unknown/unretained.
  Completed/replayable canonical pricing evidence count is 0, its artifact is absent, replay bytes are 0,
  and the activation/attempt is consumed with no retry or backfill.
- D-133 preserved the marker. D-134 implemented a procedural-terminal path, but its emitted gate contained an
  ambiguous numeric GET-count claim. That exact gate is preserved append-only and is invalid and
  non-authoritative; its recorded status and next-gate text grant no terminalization authority.
- D-135 source removed the ambiguity, and terminal-only commit
  `98f4560e718145bc7465732c1a3d2f5a4ea8d786` now seals its exact procedural terminal. The terminal is not a
  response reconstruction or canonical pricing evidence and cannot reopen the consumed D-132 action.
- D-136 exercised its exact gate, receipt, pricing attempt and marker+terminal path successfully. The terminal
  retains one official public GET, HTTP 200, no redirects and 3,735 replay bytes. Provider/evaluator/agent calls
  and cost were 0. The activation is consumed and authorizes no successor action.
- D-137 exact activation completed a bounded read-only Docker READY transition and then an SDK BLOCKED transition.
  The blocker was absent `OPENAI_API_KEY` presence; credential/environment values, `.env`, SDK import/probe,
  transport dispatch and network calls remained 0. Both phases are consumed with no retry.
- D-138 exercised that fresh contract exactly once. Receipt and attempt preceded ACTION_STARTED+BLOCKED commit
  `9f31d330190aa83768077b17c3cde47eb86c639d`; `OPENAI_API_KEY` presence was false after three membership
  checks. Credential/environment value and `.env` reads, child launch, SDK import/probe, transport dispatch and
  network calls were 0. D-138 is consumed with no retry.
- D-139 source `f5625be6cf98b5f8824a0d6a5068f1cf03e94d98`, tree
  `073f821ce8f800a9bbd4cf56c228f00804a8c55a`, is the exact four-add child of D-138 transition commit. Gate
  `d139_09f2e9dfe0ee333a2683c058b772b92f025708c4bcc6b7f1eb89c007ed8df7f8` qualifies only a future one-use
  SDK successor; preparation created no runtime artifact and performed no membership/value/SDK/child/network/
  Docker observation or action. Fully injected/mocked focused tests passed 168/168.
- A later exact activation must commit receipt and attempt before its fsynced marker. The parent may check only
  approved membership bits; eligible SDK work is confined to the `env={}` zero-ambient-forwarding child with a
  fixed placeholder and zero dispatch. Terminal or marker-only preservation consumes D-139 and grants no
  hash/candidate, cost or A/C authority.

## Superseded sequencing

- Running the full A/B/C/D matrix immediately is superseded by A/C readiness first.
- Continuing D-121 isolation before any C test is paused; D-121 is not a fixed-bundle prerequisite.
- No sealed artifact, measured result or authority statement is rewritten by this priority change.

## Open questions

1. After readiness passes, should a held-out A/C design use all 12 tasks with repetitions or a separately
   preregistered exploratory subset?
2. When, if ever, should B/raw-trace and D/selective return to the critical path?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
