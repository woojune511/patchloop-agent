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

D-122 through D-139 are immutable predecessors indexed in `docs/09-evidence.md` and Git history. Consumed
pricing, Docker and SDK attempts are never retried or repaired. Planning values, observations and source
qualification grant no hash/candidate, cost or A/C authority.

### Active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and the index in `docs/09-evidence.md`.
- Historical narratives: `docs/archive/` and Git history.

Earlier decisions cannot replace the current D-140 gate or reopen a consumed receipt, attempt or marker.

### 2026-08-09 — D-129 through D-131 preserve the predecessor boundary

D-129 failed closed because a docs open preceded receipt/attempt; transport count is unknown. D-130 separated
local admission from external activation. D-131 materialized receipt-only and armed-intent-only commits with
external actions zero. Those artifacts are immutable predecessors, not reusable activation authority.

### 2026-08-10 — D-132 is sealed; D-136 succeeds; D-137–D-139 are consumed; D-140 qualifies source

- D-132 is consumed without canonical response evidence; D-133–D-135 preserve and procedurally seal it without
  reconstruction. D-134's ambiguous gate remains invalid and non-authoritative.
- D-136 consumed one successful official public GET with HTTP 200, zero redirects and 3,735 replay bytes;
  provider/evaluator/agent calls and cost were 0.
- D-137 consumed bounded read-only Docker READY and SDK missing-key BLOCKED transitions. Docker mutation and
  credential/value/`.env`/SDK import/probe/dispatch/network counts were 0.
- D-138 and D-139 each exercised a fresh contract exactly once. D-139 receipt and attempt preceded
  ACTION_STARTED+BLOCKED commit `ba3af19a5cada8e49c29f514ad56c299639dc452`; `OPENAI_API_KEY` presence was
  false after three membership checks. Credential/environment value and `.env` reads, child launch, SDK
  import/probe, transport dispatch and network calls were 0. D-139 is consumed with no retry.
- D-140 source `fbb184ea8be0ea90eb044c03dbab538ed0c1f643`, tree
  `45283ebbeb3a7b1b3417ffe1b271020c5f062aba`, is the exact four-add child of D-139 transition commit. Gate
  `d140_7362f061555800354d23ea673ee4d71ea4aab9d26d7572d9359e4d3f6c1cbad1` qualifies only a future one-use
  SDK successor; preparation created no runtime artifact and performed no membership/value/`.env`/SDK/child/
  network/Docker observation or action. Fully injected/mocked focused tests passed 170/170 separately.
- A later exact D-140 activation must commit receipt and attempt before its fsynced marker. The parent may check only
  approved membership bits; eligible SDK work is confined to the `env={}` zero-ambient-forwarding child with a
  fixed placeholder and zero dispatch. Credential provisioning is separate and unauthorized; the child audit
  hook begins after CPython/site startup, so pre-bootstrap network absence is not claimed. Terminal or marker-only
  preservation consumes D-140 and grants no hash/candidate, cost or A/C authority.

## Superseded sequencing

- Running the full A/B/C/D matrix immediately is superseded by A/C readiness first.
- Continuing D-121 isolation before any C test is paused; D-121 is not a fixed-bundle prerequisite.
- No sealed artifact, measured result or authority statement is rewritten by this priority change.

## Open questions

1. After readiness passes, should a held-out A/C design use all 12 tasks with repetitions or a separately
   preregistered exploratory subset?
2. When, if ever, should B/raw-trace and D/selective return to the critical path?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
