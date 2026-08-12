# Effective decisions and open questions

The full decision ledger through D-121 is archived at
`docs/archive/snapshots/d121/06-decisions.full.md`. This file lists only decisions that currently constrain
work.

## Effective decisions

### 2026-08-11 — evaluator correctness precedes external readiness and A/C

- The critical path is evaluator correctness v2 → successor A/C offline qualification → versioned no-call
  contract → separately approved preflight attempt → refreshed pricing/cost and execution candidate → separate
  paid approval → four-run A/C readiness → preregistered held-out A/C → later B/D comparison.
- The current evaluator's literal safety PASS does not satisfy the documented four-verdict success contract.
  No new paid A/C row may be presented as four-verdict SCRR evidence until deterministic safety checks and
  fail-closed aggregation are versioned, implemented and tested.
- Historical evaluator-v1 results remain immutable and are not regraded. Claims using them must disclose that
  safety was unconditional rather than independently measured.
- D-142 keeps its exact evidence state: source-qualified, unactivated and not consumed. Its planning disposition
  is deferred. This decision does not create a receipt, attempt, marker or terminal and does not invalidate its
  original one-use contract.
- Evaluator-v2 and the A/C successor require new source, runtime and suite identities. D-142 and the R2 suite
  cannot be relabeled as qualification for those changed bytes.
- The successor has distinct source/runtime/suite hashes at commit `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`;
  R2 remains its immutable treatment predecessor and no runtime result exists.
- The initial v2 contract is private and task-bound. The manifest contains task/contract/source hashes, counts and
  opaque projections, not direct private requirement/check IDs. Four controls map to runtime trace,
  requested-Docker-policy trace or artifact scan; integrity is a prerequisite. Free-form `prohibited_behaviors`
  is not promoted to a machine safety rule, and existing task YAML remains unchanged in this slice.
- V1/v2 are immutable; exact-approved v3/v5/v7 attempts are consumed and cannot retry. Their outcomes were
  Docker-not-ready, checker error and diagnostic-runtime import error respectively; exact activity is indexed in
  `docs/09-evidence.md`. V8 maps v7 to omitted `SYSTEMROOT`/Windows 10106 without granting execution.
- V9 applies child-only pass-through and retains Docker gating. V10 exact source
  `3190923f97883e7df4bb53b9b8231c3598239fb1` binds v9 to a fixed post-qualification user statement. Its source
  qualification created no observation. The later exact statement produced one nonreusable self-attested state.
- V11 binds that exact state and v9 runtime/scopes. Source qualification creates no approval/attempt; only its fixed
  post-qualification statement may create one approval pair, which still requires a lifecycle successor.

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

D-122 through D-141 are immutable predecessors indexed in `docs/09-evidence.md` and Git history. Consumed
pricing, Docker and SDK attempts are never retried or repaired. Planning values, observations and source
qualification grant no hash/candidate, cost or A/C authority. D-142 is not consumed, but it is outside the
current critical path and has no activation authority.

### Active docs own current state; archive owns chronology

- Current checkpoint and next gate: `docs/current-status.md`.
- Exact artifacts: `reports/` and the index in `docs/09-evidence.md`.
- Historical narratives: `docs/archive/` and Git history.

No sequencing decision can reopen a consumed receipt, attempt or marker or rewrite the exact D-142 gate.

## Superseded sequencing

- Running the full A/B/C/D matrix immediately is superseded by A/C readiness first.
- Continuing D-121 isolation before any C test is paused; D-121 is not a fixed-bundle prerequisite.
- Activating D-142 as the next step is superseded by the evaluator-v2 successor path.
- Treating the existing R2 source qualification as sufficient for a corrected-evaluator A/C run is superseded;
  the changed evaluator requires successor source and suite qualification.
- No sealed artifact, measured result or authority statement is rewritten by this priority change.

## Open questions

1. Before held-out A/C, what exact 12-task × A/C × repetition schedule, analysis and cost cap should be frozen?
2. Should B/D be frozen before A/C unblinding, or use a separate fresh held-out panel afterward?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
