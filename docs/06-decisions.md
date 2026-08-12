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
- Successor source/runtime/suite hashes are distinct at `04ee027`; R2 remains the immutable treatment predecessor.
- V2 is task-bound and keeps direct private IDs out of the manifest. Four typed controls require integrity-checked
  runtime, requested-Docker-policy or artifact evidence; free-form audit prose is not a safety rule.
- V1-v12 are immutable predecessors; consumed attempts cannot retry. Exact activity is indexed in
  `docs/09-evidence.md`. V12 ended `child_output_invalid` after Docker passed.
- V13 consumed `BLOCKED(docker_not_ready)` before `.env`/SDK. V14 bound that terminal and then consumed one separately
  approved attempt. Docker reached READY after eight read-only calls; one child returned without a framed envelope,
  producing `ERROR(child_checker_error/framed_output_invalid)`. Whole-terminal accounting is incomplete, unknown
  activity is true and retry/resume is closed. V16 later consumes the same framed-output class after Docker READY.
  V17 binds that exact terminal and moves the diagnostic to one null-stdio worker behind a stdlib supervisor and
  anonymous result pipe. V18 later passed Docker but consumed a no-envelope supervisor ERROR with incomplete/unknown
  accounting. Its state, approval and attempt cannot be reused. V19 corrects only the outer transport. V20 binds
  that exact qualified source behind separate state/approval/run gates; qualification grants no execution authority.

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

`docs/current-status.md` owns the checkpoint/gate, `reports/` owns artifacts and the archive owns chronology. No
sequencing decision reopens consumed evidence or rewrites D-142.

## Superseded sequencing

- Running the full A/B/C/D matrix immediately is superseded by A/C readiness first.
- Continuing D-121 isolation before any C test is paused; D-121 is not a fixed-bundle prerequisite.
- Activating D-142 as the next step is superseded by the evaluator-v2 successor path.
- Treating the existing R2 source qualification as sufficient for a corrected-evaluator A/C run is superseded;
  the changed evaluator requires successor source and suite qualification.

## Open questions

1. Before held-out A/C, what exact 12-task × A/C × repetition schedule, analysis and cost cap should be frozen?
2. Should B/D be frozen before A/C unblinding, or use a separate fresh held-out panel afterward?

These questions do not authorize work beyond `docs/05-implementation-plan.md`.
