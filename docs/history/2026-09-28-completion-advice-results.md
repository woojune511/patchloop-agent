# Completion-advice removal: changed process, unresolved correctness

Date: 2026-09-28. `official=false`; one authorized treatment continuation.
Follows [live preparation](2026-09-28-completion-advice-live-preparation.md).

## Execution and accounting

The user authorized the frozen toqito-1538 invocation: gpt-5.4-2026-03-05, xhigh,
repeat 1, new cap $3, existing project credential path. The manifest hash was
`cb3385651c1bfd86a4ae17ced86d69e60a3c68f958222f9f7b7cead9b93bbbdc`.
Preflight passed; 7 new counts and 7 generations cost **$0.9856585**. Billing is
known. The unused $2.0143415 is closed, with no automatic retry/resume. Historical
$1.091299 is separate; the cumulative branch ledger is $2.0769575.

The agent made 9 tool actions: probe, three searches, read, probe, edit, registered
check, finish. There were 2 new probes and 1 additional accepted mutation.
The 14 selected base-regression tests passed, but benchmark acceptance was **FAIL**,
safety **PASS**. This is a continuation, not a fresh solve or an official score.
Private failing tests and evaluator internals were not inspected.

## Delivery audit

The exact source prefix is preserved. All 7 dispatched inputs verify against their
canonical public projection. Each counted/dispatched request matches a recorded
advice-removal projection of its baseline, with the marker preceding input count.
The first treatment input matches the frozen manifest hash. Latest completion
guidance has no recommended action throughout; all other state/tool differences
arise through the ordinary trajectory. System instructions and historical prose
remain, so this is not removal of every completion-related signal.

## Public process

Unlike the prior check/finish-only runs, the agent first identified new behavior
as unverified and tested product, Bell, alpha=1, CQ, error messages and a mixed-state
inequality. The non-orthogonal CQ assertion failed: output 0.5698489418 versus its
self-authored expectation 0.5626401326. Later assertions were after that failure;
printed values alone did not mean all assertions ran.

The agent searched source and read public tests, then explicitly asked whether the
implementation or expectation was wrong. Its second probe rejected an alternative
normalized-block formula on revealing/product cases, but retained the original CQ
formula. A non-orthogonal comparison still failed. Passing those edge cases did not
establish the retained formula on noncommuting inputs.

It changed the implementation to return the purported exact pure/product/CQ values
directly, applying `max(downarrow, optimized)` only to the numerical fallback.
The submitted patch changed from
`fdd4fa640b555cc3ef43317ec9b4b3fa2a694902f11d571f43fb48dd2a318745` to
`878cb57a001bc0aacd1847a0ad55aaf09fe0c5baf56d1e39bf73ea9f35d68250`.

Despite planning a targeted post-repair probe, its next decision narrowed the
question to registered regression. It did not rerun either probe before submitting.
Its finish basis claimed that regression confirmed repaired uparrow branches,
although the selected tests exercise default/downarrow behavior. Thus unsupported
verification closure recurred even without the local action recommendation.

## Independent public post-run checks

An operator-only snapshot was cloned from the pinned source and the exact submitted
patch applied and byte-verified. No observations were sent back to the agent.
Both agent probe programs passed after repair in the existing evaluator image,
with a simple scalar `check_setup` helper. This was a separate operator execution,
not an exact replay of the original constrained probe container.

Nevertheless, the existing full-rank feasible-state witness still contradicts the
patch: candidate 0.5849625007 versus feasible objective 0.7715527056 (epsilon 1e-6).
The witness check's exit 0 means **counterexample confirmed**, not candidate PASS.

A more local operator check applied the agent's own `uparrow >= downarrow` condition
to its non-orthogonal CQ input (weights .35/.65). It failed after repair:
uparrow 0.5626401326 < downarrow 0.5698489418, gap -0.0072088092. The agent had checked
this inequality only on a different mixed non-CQ input. Its repair matched its CQ
expectation by removing a safeguard, while breaking that condition on the changed
case. These public failures are separate from the aggregate benchmark FAIL; no
specific private failure cause is inferred.

## Decision and evidence

This single sequential sample shows a different process, not improved correctness
or an established causal/general effect. Do not adopt advice removal as a proven
improvement. More probes, formula discussion and an extra edit were insufficient.
Next diagnose how the agent chooses and revises expected values: whether it checks
the changed input against independent properties, and whether evidence that rejects
one alternative is incorrectly treated as proof of the remaining formula. Do not
add task-specific formulas, hidden feedback or another generic cue by default.

- Live: `C:/pt/adviceofflive0928a/result.json`; branch A1, run
  `run_dev_33068b6e257f423a`, group journal `run_dev_posteditcontinuation`.
- Delivery/process audit: `C:/pt/analyses/advice-results-20260928-v1/audit.json`;
  hash-chained journal `run_dev_adviceresultaudit` binds report and script.
- Operator results: `C:/pt/analyses/advice-public-checks-20260928-v1/results.json`
  and `same-cq-invariant.json`; journal `run_dev_advicepublicchecks` binds patch,
  executed programs and results. All four operator checks confirmed cleanup.
- Scripts: `C:/pt/audit_advice_results_0928.py`,
  `C:/pt/check_advice_candidate_0928.py`; the additional invariant program is journaled.

Runtime/defaults unchanged. Documentation checks accompany this record; no new
runtime suite or mock repetition is needed for the result-only documentation change.
