# Post-reproduction repair: restored evidence and single-run preparation

## Problem, decision and scope

The [signature-guided diagnostic](2026-10-28-argument-first-reproduction-results.md)
entered the intended original pylint call and captured F0010, with a normal
package control. It deliberately ended after its first settled probe. Repair
after acquiring that public failure remains unmeasured. The user requested
checkpoint restoration, a short failure-delivery check and experiment preparation.
No new paid execution was authorized or performed in this work.

The question matters because acquisition and repair are different bottlenecks:
repeating acquisition would spend resources without testing the next unresolved
stage. Continue the ordinary repair runner from the public baseline. Do not add
another general runtime gate, force diagnostic_rules, increase resources or inject
a known repair. The normal runner already restores latest tool results and owns
mutation rechecks, public regression feedback, bounded revisions and submission.

The alternative explanation is that failure evidence is lost at the checkpoint
handoff. Offline inspection can distinguish that from actual-model failure to
interpret evidence or produce a correct patch. Delivery now passes; model uptake,
repair and independent acceptance remain live questions. If the model fails,
attribute the stop to observed acquisition/interpretation/mutation/check/budget/
submission/evaluation evidence rather than assuming a larger context is needed.

## Implementation and local result

Commit `5a1f703fae8c161d3263b3f2935dbb855888e20a` adds the opt-in completed-batch
fork and [continuation preparation contract](../../.agent/post-reproduction-repair.md).
The old prepared-input fork remains unchanged. New code includes source seq84
tool_batch_finished, excludes the diagnostic-only review/terminal events, resolves
nested fork artifacts with content/size/type verification, and reconstructs
unchanged source, acquired/refuted original, counters, elapsed time and settled
usage. Original program/case/action/input identities and historical bytes stay fixed.

The ordinary public segment handoff produces the first repair request. The audit
compares the latest action/input identity and complete reproduction result, including
observed JSON, expected/failure comparison, binding and call captures. It accepts
normal public-archive deduplication, and rejects changed observations. Historical
opaque reasoning is not projected. No new original call runs during preparation.

Two independent restores of the actual Astroid checkpoint produce equal first
requests after normalizing only elapsed-time fields, timeout and derived segment
ID. The stage is `needs_mutation`; original acquisition is not reset. Input counting
and dispatch still compare the exact unnormalized actual payload. New funding,
current execution commit and historical/current probe receipts remain separate.

Focused local evidence: 22 restoration/preparation tests PASS in 33.284 seconds;
four existing failure-feedback/public-regression/normal-finish/mock-evaluation
cases PASS in 37.41 seconds. Documentation 5 PASS; Ruff and diff checks PASS.
An intermediate owner run saw implementation-hash drift during concurrent edits;
the stable final owner run passed. Full quick suite and Linux CI were not run;
the changed diagnostic owners and relevant runner feedback paths were selected.
Mock isolated EVALUATOR_PASS is plumbing evidence, not benchmark acceptance.

Reports: `C:/pt/tmp/postrepowners28b.xml`, `C:/pt/tmp/postrepair-core28a.xml`,
`C:/pt/tmp/postrepair-doc28a.xml`. Actual preparation provider calls 0 and new
benchmark target executions 0. Read-only environment preflight is READY; existing
source/dependencies/images were inspected without pulls/builds or credential reads.

## Prospective experiment and Material Passport

Prepared directory: `C:/pt/post-reproduction-repair-plan-v1`.
Manifest, first-request, feedback-audit, preflight, run.ps1, validate.ps1,
README and material-passport are linked by the external append-only preparation
journal. Material is public dev-train task/source and saved model-authored execution
evidence. Codex authored restoration/preparation and scripted checks. Private
evaluator content, hidden tests and reference repairs are excluded from model input.

Source: `C:/pt/argument-first-reproduction-run-v1/B`,
`run_dev_3e21775752a54cae`, cut84 inclusive. Task Astroid-1333,
dev-train current-dev20/13. One proposed run, gpt-5.4-2026-03-05 xhigh,
credential path `C:/Users/geonj/Documents/PatchLoop/.env`.

Proposed NEW invocation cap USD **4.13241570**; NOT APPROVED. Historical settled
USD 0.3675843 is excluded from new charges. This proposal equals the prior
numerical remainder but does not reopen the closed allocation. Remaining limits:
15 responses including correction, 33 tools, 3 edits, general output40K/correction25K,
context60K, solver1727.678 seconds plus evaluation reserve390 (total2117.678).
No counters or active time are reset. The final request uses the normal physical
completion/recovery reservation under these limits.

Run the normal loop through repair, same original replay, required public checks,
bounded revisions, finish and isolated evaluation. Score first edit, failure delivery,
same-call F0010 absence and W0611 processing, normal control, public regression
PASS, cases_verified_delivery/normal finish, isolated acceptance and cost/time
separately. Since diagnostic_rules is null, independently compare candidate captures
against authored booleans after the run. W0611 is an added processing criterion
beyond the issue's explicit error-absence condition.

Count/transport/billing/execution/cleanup uncertainty stops without retry.
The output root `C:/pt/post-reproduction-repair-run-v1` is unused and single-use.
This is checkpoint repair, not a clean-start solve, causal A/B or generalization
claim. Do not repeat merely because budget remains.

Manifest hash: `sha256:179244167169c2a8d1396cfbc5e906d50418bf52c148ed4d6b513a0eda209b2f`.
First request: `sha256:5145942272c86a855d4113c9905671daebc7f78dcf2cff41b91a6563c60cacf1`.
Runtime: `sha256:321e6bc99e4cd3ef014e5d9bc7947c5f3369dedddc39c1be520a21b6142d47b3`.
Diagnostics: `sha256:ae1c255b6ebb6b51d42ec7dab1c79362055f95340f8b421db3fbcd1babc76d2b`.

Prepared and locally validated. Actual-model repair, benchmark public checks,
finish and isolated acceptance remain NOT_RUN for this allocation.
