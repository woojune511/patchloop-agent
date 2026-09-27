# Scope cue delivered at readiness: actions and patch unchanged

2026-09-28, official=false. One sequential development continuation.
See [preparation](2026-09-28-deferred-scope-preparation.md),
[first-turn cue](2026-09-28-verification-scope-results.md), and
[unhinted baseline](2026-09-28-post-edit-budget-results.md).

## Execution and measured result

The user authorized one new $3.00 invocation using the prepared manifest
`sha256:95c1494c00ebb99b0cd2aa0ae5fa5b8557ce4b8579a0acc8b948aa0358755e6f`.
Collector commit: `f26883f`. Same original-toqito-1538 first-post-edit checkpoint,
gpt-5.4-2026-03-05 xhigh, 25,000 desired output tokens, repository `.env`.

| Condition | New calls | New probes / edits | Actions | Benchmark / safety | New cost |
| --- | --- | --- | --- | --- | --- |
| Unhinted | 2 | 0 / 0 | check, finish | FAIL / PASS | $0.2168265 |
| Cue in first input | 2 | 0 / 0 | check, finish | FAIL / PASS | $0.234737 |
| Cue at readiness | 2 | 0 / 0 | check, finish | FAIL / PASS | $0.113142 |

All three checked the same public regression (14 passed, one pre-frozen deselection)
and submitted the identical patch. No new source inspection occurred in these
continuations. New counts in this invocation: two. Billing is known, elapsed group
time 57.87 seconds including preparation/evaluation. Unused $2.886858 is closed;
no retry, resume or further allocation was used. Earlier results remain unchanged.

The first call used 42,013 input tokens including 40,320 cached, plus 830 output;
the second used 36,011 input including 6,528 cached, plus 736 output. Thus lower
cost is not evidence of better verification or repair. Branch cumulative bookkeeping
$1.204441 includes inherited $1.091299; only $0.113142 is new billed usage.

## Delivery verified at the consequential decision

The actual first request equals the previous unhinted first request exactly. After
the required check passed, `diagnostic_scope_cue_prepared` at event 160 bound the
ordinary ready request and selected request hash. The ordinary request differs
from the selected request only by the same frozen `verification_scope_cue` field.
The cue was added before the actual count and dispatch at event 165. The counted
and dispatched requests match exactly, and both new inputs match their saved
canonical public-state projection. Literal cue presence across the two requests
is `[false, true]`; it did not disappear before the finish decision.

Only preparation metadata/context binding changed alongside that added field.
Tools, completion guidance and candidate were preserved. No task-specific hint,
operator witness or private evaluator feedback was supplied to the coding agent.

## Observable decision

The first public plan treated regression as the remaining required action, with
submission expected on PASS unless a concrete unchecked concern remained. At the
ready decision, despite the cue, the model stated that there was no concrete public
uncertainty that would change the edit, classified residual concerns as broader
hidden coverage of the numerical fallback, cleared its open question and finished.
Those hidden-case statements are model speculation, not information from evaluation.
No new evidence for the extension preceded that closure. Read/search/probe/edit
tools remained available; neither the cost nor tool horizon forced submission.

The result rules out **absence of the cue at this particular decision** as its
explanation. It does not isolate whether completion advice, confidence in the
inherited patch, the definition of a concrete uncertainty, or another mechanism
caused closure. One sample per condition is neither a randomized timing experiment
nor evidence of equivalence or general ineffectiveness of scope instructions.

The prior public witness remains applicable by exact patch identity:
`sha256:fdd4fa640b555cc3ef43317ec9b4b3fa2a694902f11d571f43fb48dd2a318745`.
The candidate's 0.5849625 is below a feasible 0.7715533 objective. The saved,
journal-bound public case was reused after byte verification, not rerun. Aggregate
benchmark FAIL is separate; private failing tests and evaluator internals were
not inspected, and their specific failure cause is not inferred from this witness.

## Decision and records

Do not adopt either scope-cue condition as a demonstrated improvement or keep
adding cue variants without a new mechanism. The next evidence question is why
unverified changed behavior is dismissed at completion despite an explicit scope
instruction. Examine the actual public evidence used to close that question and
the existing completion advice before choosing another intervention. No default
change or additional paid run is authorized by this result.

- Live collector: `C:/pt/deferredscopelive0928a/result.json`; group journal
  `runs/run_dev_posteditcontinuation.jsonl`, branch `A1/runs/run_dev_33068b6e257f423a.jsonl`.
- Audit: `C:/pt/analyses/deferred-scope-results-20260928-v1/public-process-audit.json`;
  journal `runs/run_dev_deferredscoperesultaudit.jsonl` binds the report and result.
- Script: `C:/pt/audit_deferred_scope_results_0928.py`.

Provider-free assertions verified original prefix preservation, first-request
equality, exact one-field ready projection, cue-before-count/dispatch ordering,
both delivered projections, cost accounting, unchanged patch and prior witness
receipt. Documentation checks passed. No runtime changes or new full-suite run.
