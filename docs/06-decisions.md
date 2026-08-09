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

### 2026-08-09 — D-127 remediation is terminal blocked

- Six read-only Docker calls established `preexisting-container-auto-restart-state-unverified`; every mutation
  and later phase stayed zero. The consumed terminal is idempotent and cannot be reopened.

### 2026-08-09 — D-128 external successor is terminal blocked

- D-128's attempt-first phase made three read-only rc-1 calls and recorded
  `already-running-docker-desktop-linux-daemon-unavailable`; all later phases stayed zero and its receipt is consumed.
- Later user verification does not reopen D-128. It remains historical and the agent remains forbidden to
  start Desktop or the daemon.

### 2026-08-09 — D-129 records manual readiness but grants no external authority

- D-129 binds clean source `1fef6716cddca571777c8b7f9f1dc4501f988d1c` and the D-128 chain offline.
- The two manual checks (rc 1, then 29.6.2 linux/amd64/rc 0 with no auto-start) are self-attested. The later
  external approval led only to the sequence incident described below; no readiness claim followed.
- Desktop/daemon start, container execution, other images, hash/candidate, cost and A/C remain unauthorized.

### 2026-08-08 — active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and `docs/09-evidence.md` index.
- Historical narratives: `docs/archive/`.
- Repeating every milestone in every topic document is discontinued.

Earlier retained decisions remain discoverable in the archived ledger and `docs/09-evidence.md`; they do not
replace the current D-129 sequence terminal or reopen consumed D-128/D-129 receipts.

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

- One approved public docs tool open occurred before the machine receipt and durable attempt. It is not
  replayable pricing evidence; underlying HTTP/redirect count is unknown.
- A non-retroactive receipt and `D129_EXTERNAL_NO_CALL_SEQUENCE_OBSERVED_BLOCKED` terminal preserve the event.
  No attempt was backfilled; Docker, canonical pricing, SDK and runtime/cost paths stayed zero.
- The consumed receipt cannot be retried. D-130 must be offline and use receipt+armed-intent admission before a
  later exact external activation.
