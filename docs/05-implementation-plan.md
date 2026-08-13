# Implementation plan

Status: active fast-track roadmap. Historical milestone plans remain under `docs/archive/snapshots/d121/`.

## Sequencing rule

Preserve observed attempts, but do not consume unchanged source or configuration. Local no-call readiness may be
retried up to three times for transient pre-provider failures. Provider execution still requires an exact execution
hash, fixed schedule, hard cost cap and one explicit campaign approval.

## Preserved foundation

D-098 is a development baseline; D-110 froze three entries and D-112/D-115 left selective retrieval unready.
`fixed-d110-bundle-v1` keeps A null and C exact-three. D-129-D-141, D-142 and V1-V25 remain historical evidence;
none is relabeled as evaluator-v2 live evidence.

## Work item 1 — evaluator correctness v2

Status: implemented and locally verified.

Task-bound projections, typed safety evidence, fail-closed four-verdict aggregation, authority-gated runner,
receipt, persistence, qualification and completion adapters are tested with v1 byte goldens. R3 Moto A exercised the
live receipt-qualified path; this remains one development row, not a production-security claim.

## Work item 2 — successor A/C qualification

Status: R3-R6 and their R5-R8 qualifications are immutable; R10 offline-qualifies R8 source/tests, tasks/images, v11
plan, four rows and unchanged A-null/C-exact-three treatment. R7/R9 is superseded unexecuted.

## Work item 3 — reusable fast preflight

Status: implemented; the old R7 candidate is superseded. R8 requires a new bounded no-call preflight after a clean
commit and has no candidate yet.

The supported command validates source identities, loads only secret presence, performs bounded Docker/SDK no-call
checks, retries transient pre-provider failures at most three times and emits a candidate only if all gates pass.
Attempt summaries remain immutable; the command makes no provider/evaluator/agent call.

## Work item 4 — one campaign approval

Status: completed for R3 through R6; all four exact approvals are consumed.

R3 bound `$54.45` reserve/`$55` cap. R4 bound `$15.30` reserve/`$18` cap and sealed provider-before-dispatch at
`$0`; R5 and R6 used the same reserve/cap and sealed after one evaluated row failed qualification at `$0.19303425`
and `$0.169596`, respectively. Their approvals cannot transfer. A separate approval must bind a future R8 exact
candidate hash, R10, `$15.30` reserve and `$18` cap.

## Work item 5 — four-run A/C readiness

Status: attempted as sealed R3 through R6; all complete-matrix gates failed and dispositions are `inconclusive`.

R3 Moto A resolved; Moto C hit 3M before submission and its secondary binding mismatch halted Babel. R4 then failed
capability revalidation before provider dispatch at `$0`. R5 Moto A resolved and passed evaluator v2, but legacy
terminal-qualification assumptions rejected the row and halted the rest. R6 Moto A also resolved, but runtime evidence
serialized the legacy call-guard policy and failed terminal qualification. Rows never retry or replace; another attempt
is a disclosed full panel. Output remains descriptive, not causal or held-out.

## Work item 5a — contract-hardening successor and fresh panel

Status: R10/R8 offline implementation and source qualification; no R8 candidate, approval or run.

R8 preserves the runtime-evidence fix and hardens types/evidence bindings while keeping equal A/C limits: 3M input, 350k output, 3.35M aggregate,
25k/response, 180 model, 300 tool and 3,600 seconds; reserve is `$3.825`/row, `$15.30`/panel, `$18` cap. This
R3-informed diagnostic is not held-out-safe or a benefit claim. Next: clean no-call candidate, then fresh exact-hash/`$18` approval.

## Work item 6 — preregistered held-out A/C

Status: planned target only.

After valid readiness, freeze task identities, repetitions, metrics, exclusions, analysis and stop rules before
viewing held-out outcomes. The target is 12 tasks × A/C × at least two repetitions = at least 48 rows. Moto/Babel
results must not tune the fixed bundle or held-out policy.

## Work item 7 — B/D and the full comparison

Status: deferred.

- B/raw-trace needs portable source selection, redaction and equal-budget truncation.
- D/selective needs independent applicability labels and a frozen score/rerank/threshold policy.
- If designed after held-out A/C is unblinded, B/D use a separate fresh held-out panel.

No readiness or held-out A/C result automatically unlocks B, D or a full A/B/C/D campaign.
