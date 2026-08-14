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

Status: implemented and exercised for R8. Its exact candidate was used once and is now consumed; R7 remains
superseded unexecuted.

The supported command validates source identities, loads only secret presence, performs bounded Docker/SDK no-call
checks, retries transient pre-provider failures at most three times and emits a candidate only if all gates pass.
Attempt summaries remain immutable; the command makes no provider/evaluator/agent call.

## Work item 4 — one campaign approval

Status: completed for R3 through R8; all five exact approvals are consumed.

R3 bound `$54.45` reserve/`$55` cap. R4 bound `$15.30` reserve/`$18` cap and sealed provider-before-dispatch at
`$0`; R5 and R6 used the same reserve/cap and sealed after one evaluated row failed qualification at `$0.19303425`
and `$0.169596`, respectively. R8 used the same reserve/cap, completed four rows at `$0.3664215` and is consumed.
No approval transfers to another suite or campaign.

## Work item 5 — four-run A/C readiness

Status: complete for the R8 development-readiness matrix after append-only completion-projection correction.

R3 Moto A resolved; Moto C hit 3M before submission and its secondary binding mismatch halted Babel. R4 then failed
capability revalidation before provider dispatch at `$0`. R5 Moto A resolved and passed evaluator v2, but legacy
terminal-qualification assumptions rejected the row and halted the rest. R6 Moto A also resolved, but runtime evidence
serialized the legacy call-guard policy and failed terminal qualification. R8 completed all four exact rows; its raw
result's stale v1 completion envelope misclassified v2 qualifications, and the R3 correction index recomputes the
matrix without rewriting it. Output remains descriptive, not causal or held-out.

## Work item 5a — contract-hardening successor and fresh panel

Status: completed and consumed as R10/R8 plus append-only R8 completion correction.

R8 preserves the runtime-evidence fix and hardens types/evidence bindings while keeping equal A/C limits: 3M input, 350k output, 3.35M aggregate,
25k/response, 180 model, 300 tool and 3,600 seconds; reserve is `$3.825`/row, `$15.30`/panel, `$18` cap. This
R3-informed diagnostic is not held-out-safe or a benefit claim. Both conditions resolved both tasks; observed success
delta is zero, while structured used fewer tokens and list-price cost in both pairs. No rerun is authorized.

## Work item 6 — preregistered held-out A/C

Status: authoritative dispatcher and successor no-call source are offline-qualified; execution remains closed.

The record freezes 12 tasks × A/C × two repetitions = 48 rows, complete-panel analysis and `$252`/`$275` planning cost.
The non-`ExperimentSuite` fixture surfaces remain historical. Materialization R1 stores no private value/outcome and
preserves `$252`/`$275`. Preflight/dispatcher R7 binds the current candidate, manifest, marker expansion, exact
approval plan, append-only journal, persisted-v2 authentication/replay and complete/inconclusive analysis boundary.
R3-R6 are preserved pre-activation predecessors. Next: commit, fresh read-only preflight, then—only for its
exact candidate—a separate 48-row `$252`/`$275` approval. Candidate, approval, runtime call and spend are currently 0.

## Work item 7 — B/D and the full comparison

Status: deferred.

- B/raw-trace needs portable source selection, redaction and equal-budget truncation.
- D/selective needs independent applicability labels and a frozen score/rerank/threshold policy.
- If designed after held-out A/C is unblinded, B/D use a separate fresh held-out panel.

No readiness or held-out A/C result automatically unlocks B, D or a full A/B/C/D campaign.
