# Implementation plan

Status: active fast-track roadmap. Historical milestone plans remain under `docs/archive/snapshots/d121/`.

## Sequencing rule

Preserve observed attempts. Local no-call readiness may be retried up to three times for transient pre-provider
failures, but a paid campaign's semantic source/suite/schedule identity is one-use even when readiness timestamps
change. Provider execution still requires an exact execution hash, fixed schedule, hard cost cap and one explicit
campaign approval.

## Preserved foundation

D-098 is a development baseline; D-110 froze three entries and D-112/D-115 left selective retrieval unready.
`fixed-d110-bundle-v1` keeps A null and C exact-three. D-129-D-141, D-142 and V1-V25 remain historical evidence;
none is relabeled as evaluator-v2 live evidence.

## Work item 1 — evaluator correctness v2

Status: implemented and locally verified.

Task-bound projections, typed safety evidence, fail-closed four-verdict aggregation, authority-gated runner,
receipt, persistence, qualification and completion adapters are tested with v1 byte goldens. Current held-out source
also separates evaluator-private diagnostics from agent-visible leakage, uses opaque control identities and requires
runtime-issued provenance for official completion. This is harness correctness, not a production-security claim.

## Work items 2-5a — development A/C

Status: complete and consumed. R3-R6 are immutable inconclusive, R7/R9 is superseded, and R10-qualified R8 completed
the four Moto/Babel A/C readiness rows for `$0.3664215`. Its append-only correction preserves the raw result while
recomputing the v2 completion projection. This is descriptive development readiness only; exact predecessor limits,
failure classes and hashes remain in `docs/09-evidence.md`. No development candidate or approval may be reused.

## Work item 6 — preregistered held-out A/C

Status: complete and consumed as R16; R7/R11/R14/R15 remain immutable inconclusive predecessors.

The preregistration freezes 12 tasks × A/C × two repetitions = 48 rows. Development-only evidence set equal A/C at
1M/100k/1.1M and `$57.60`/`$60`, excluding held-out outcomes/task content. R7/R11/R14/R15 are immutable inconclusive;
their exact accounting, historical reasons and append-only successor diagnoses remain in `docs/09-evidence.md` and
cannot reauthenticate, relabel, settle or resume them.

The successor added candidate-v3 realized-schedule identity, candidate-bound runtime/cost, current
persisted-v5/row-v2 prior-row revalidation and exact historical replay. R16 candidate `sha256:24044c1e...8813`
consumed a separate approval and completed 48 settled rows at `$27.24465825`: 15 resolved, 14 task failures and
19 typed agent failures. No-memory succeeded 8/24 and structured 7/24, yielding official frozen-panel C-minus-A
`-1/24`; the descriptive stability interval is `[-1/4, 1/6]`. No causal/general memory claim follows.

The candidate, approval and panel are consumed. Preserve the append-only R16 index and do not rerun or tune against
this unblinded panel. Any next experiment begins with a separately preregistered fresh design; current provider
authority is 0.

## Work item 7 — B/D and the full comparison

Status: deferred.

- B/raw-trace needs portable source selection, redaction and equal-budget truncation.
- D/selective needs independent applicability labels and a frozen score/rerank/threshold policy.
- Because held-out A/C is now unblinded, B/D must use a separate fresh held-out panel.

No readiness or held-out A/C result automatically unlocks B, D or a full A/B/C/D campaign.
