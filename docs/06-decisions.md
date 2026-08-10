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

D-122 through D-140 are immutable predecessors indexed in `docs/09-evidence.md` and Git history. Consumed
pricing, Docker and SDK attempts are never retried or repaired. Planning values, observations and source
qualification grant no hash/candidate, cost or A/C authority.

### Active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and the index in `docs/09-evidence.md`.
- Historical narratives: `docs/archive/` and Git history.

Earlier decisions cannot replace the current D-141 gate or reopen a consumed receipt, attempt or marker.

### 2026-08-09 — D-129 through D-131 preserve the predecessor boundary

D-129 failed closed because a docs open preceded receipt/attempt; transport count is unknown. D-130 separated
local admission from external activation. D-131 materialized receipt-only and armed-intent-only commits with
external actions zero. Those artifacts are immutable predecessors, not reusable activation authority.

### 2026-08-10 — D-132 is sealed; D-136 succeeds; D-137–D-140 are consumed; D-141 qualifies source

- D-132 is sealed without response reconstruction; D-136 preserves one successful official public GET; D-137
  preserves bounded Docker READY plus SDK BLOCKED. All are consumed; exact limits remain in `docs/09-evidence.md`.
- D-138 through D-140 each exercised a fresh contract exactly once. D-140 receipt and attempt preceded
  ACTION_STARTED+BLOCKED commit `4b8eaf4d815f2ad5e2205bace0e8d9a97ad043f2`; the key and routing presence
  bits were false/false/false after three membership checks. Credential/environment value and `.env` reads,
  child launch, SDK import/probe, transport/network and provider/evaluator/agent calls were 0. D-140 is consumed.
- D-141 source `0ffe586760659542d7ecf7c94698a2f1e109e6b0`, tree
  `41d14e4d9778e52834e4e6636f1bcd35ce148876`, is the exact four-add child of D-140 transition commit. Gate
  `d141_51e825a474cc957f6fa20dea9ec5332c9b0defd7569dfe6f063f57f195636aab` qualifies only a future one-use
  SDK successor; preparation created no runtime artifact and performed no membership/value/`.env`/SDK/child/
  network/Docker observation or action. Fully injected/mocked focused tests passed 170/170 separately.
- A later exact D-141 activation must commit receipt and attempt before its fsynced marker. The parent may check only
  approved membership bits; eligible SDK work is confined to the `env={}` zero-ambient-forwarding child with a
  fixed placeholder and zero dispatch. Credential provisioning is separate from and unauthorized by preparation
  and activation; no credential value belongs in approval/chat. The child audit hook begins after CPython/site
  startup, so pre-bootstrap network absence is not claimed. Terminal or marker-only preservation consumes D-141
  and grants no hash/candidate, cost or A/C authority.

## Superseded sequencing

- Running the full A/B/C/D matrix immediately is superseded by A/C readiness first.
- Continuing D-121 isolation before any C test is paused; D-121 is not a fixed-bundle prerequisite.
- No sealed artifact, measured result or authority statement is rewritten by this priority change.

## Open questions

1. After readiness passes, should a held-out A/C design use all 12 tasks with repetitions or a separately
   preregistered exploratory subset?
2. When, if ever, should B/raw-trace and D/selective return to the critical path?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
