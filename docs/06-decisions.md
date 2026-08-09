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

- R2 binds full-schedule reserve/settlement/completion; D-124/D-125 remain historical local/mock predecessors.
- D-126 sealed clean source, official pricing and bounded no-call observation only. Five blockers and missing
  raw pricing bytes keep readiness false.
- D-127 approval is limited to resolving those issues and repeating the no-call preflight. Execution-hash/
  candidate creation and later $55 live approval remain separate gates.

### 2026-08-09 — D-127 remediation is terminal blocked

- Fix official client routing, retain bounded replayable pricing and limit Docker to exact remediation; never
  authorize container create/start/run/exec.
- Static passed through an exact-key ephemeral `.env` loader without exposing the value. Six bounded read-only
  Docker CLI calls then established blocker `preexisting-container-auto-restart-state-unverified`; Desktop
  start, image mutation, container/workload and every later phase remained zero.
- The append-only blocked terminal is idempotent for this receipt. Manual safe Desktop start or expanded
  incidental-start authority does not reopen it; any renewed remediation/pricing/preflight path requires a
  separately approved successor.

### 2026-08-09 — D-128 is offline source, not approval

- D-128 qualifies the D-127-terminal successor contract without loading credentials or making external calls.
- The agent must not start Docker. User manual start plus no-container-auto-start attestation comes first.
- A new receipt/action needs exact approval citing the committed D-128 tuple; generic proceed is insufficient.

### 2026-08-08 — active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and `docs/09-evidence.md` index.
- Historical narratives: `docs/archive/`.
- Repeating every milestone in every topic document is discontinued.

Earlier retained decisions remain discoverable in the archived ledger and `docs/09-evidence.md`; they do not
change D-126 as latest sealed gate or the closed D-128 authority boundary.

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
