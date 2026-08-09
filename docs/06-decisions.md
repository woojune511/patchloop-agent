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

### 2026-08-09 — D-125 source and D-126 no-call preflight remain non-executable

- D-124/D-125 are historical local/mock; D-126 sealed observation only and remained blocked.
- Hash/candidate creation and later `$55` live approval remain separate gates.

### 2026-08-09 — D-127 through D-129 remain terminal history

- D-127/D-128 consumed terminals record six then three read-only Docker failures; later self-attested daemon
  readiness does not reopen them. D-129 records only the sequence incident below. None grants current readiness
  or Desktop/daemon/container/hash/cost/A-C authority.

### 2026-08-08 — active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and `docs/09-evidence.md` index.
- Historical narratives: `docs/archive/`.
- Repeating every milestone in every topic document is discontinued.

Earlier retained decisions remain discoverable in the archived ledger and `docs/09-evidence.md`; they do not
replace the current D-131 offline gate or reopen consumed D-128/D-129 receipts.

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

### 2026-08-09 — D-129 external sequence fails closed

- One approved public-docs open preceded the machine receipt/attempt; transport count is unknown and no
  replayable pricing evidence or retroactive attempt exists. The consumed
  `D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED` receipt/terminal cannot be retried; later paths stayed zero.

### 2026-08-09 — D-130 separates local admission from external activation

- D-130 bound the D-129 chain offline. Its later Stage 1 approval could not be exercised without a committed
  writer, created no receipt/intent and is non-reusable after the D-131 topology change. External activation
  remains a separate tuple-bound authority.

### 2026-08-09 — D-131 qualifies local-admission implementation without admitting it

- D-131 gate `d131_849502e63d33aa3c8ceea8dc03faf0ff86e8ec51db9321fa13544df15a4af057`
  exact-binds the D-130 predecessor/evidence topology and implementation source commit
  `9cd736c0221bba17375c3b7ddce02e5214fc21fe`.
- The source qualifies append-only/new-only receipt and intent writers, exact commit topology, loaded-module
  provenance and challenge rendering. The gate builder invoked none of those future actions.
- Only a fresh exact D-131-qualified approval may create the receipt-only and durable
  `ARMED_WAITING_EXACT_ACTIVATION` intent-only commits and render the challenge. Official-docs/network,
  Docker, SDK and credential observations must remain zero.
- External work still requires a later exact activation quoting the D-131 gate, receipt, intent and both
  commits. D-131 grants no hash/candidate, cost or A/C authority.
