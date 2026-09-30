# Proposed reference-free replay comparison

Status: PLAN_ONLY / NOT_AUTHORIZED / NOT_RUN. This document grants no provider
budget. Historical Darts/MontePy allocations are closed. Do not execute a paid run
until the implementation gates below pass and this exact scope is approved.
Reviewed feature baseline: merged PR #10, `5cc7d9043a40e1a4d1beb4d475dd6e076dade066`.
This is not a dispatch SHA; freeze the final runtime after the arm selector is tested.

## Question and causal boundary

Does reference-free program registration/replay help the agent produce correct
repairs at the same resource limits, beyond existing reference-based cases?

Both arms use the same merged runtime, cases-v1 reference comparison/catalog,
registered checks, probe environment, prompts and solving policies. The sole
intervention is availability of reference-free program registration and its truthful
tool description. A excludes that registration; B exposes the PR #10 capability.
In both arms the agent may write ordinary probes and choose healthy JSON references.

Do NOT substitute `probe-policy none` versus `cases-v1`: that also changes existing
reference comparison and catalog access. This design estimates the incremental
capability conditional on cases-v1, not the benefit of switching the selected
baseline (which remains none). Separate checkout revisions are also not the control:
the journal fix, command diagnostics and all other runtime behavior must be shared.

## Implementation gates before any paid admission

The current CLI has no switch that isolates this intervention. Before execution:

1. Implement a bounded experimental arm selector in the same runtime. In A remove
   the reference-free registration affordance from the schema/description and reject
   it before dispatch; preserve reference-based registration and replay. In B use
   the current interface. Bind each effective contract and arm identity in the
   existing model/tool hashes and exact run envelope; no invisible test monkeypatch.
2. Verify default/none parity, A rejection before dispatch, existing references in
   both arms, B failed-program replay, exact recovery identity, and no new gates,
   probe quotas or automatic executions. Recheck both arms through mock evaluation.
3. Freeze one clean runtime SHA, both tool-contract hashes, task package identities,
   source/dependency descriptors, image digests, row order and output roots. Validate
   unchanged original sources and existing environments without provider calls.
   No Docker startup, image acquisition, dependency replacement or task repair.
4. Verify an invocation-wide admission ledger for all four rows, per-row ceilings,
   zero retries and stop-all behavior. Do not launch four unrelated CLI commands
   without common accounting/stop enforcement. Then obtain separate approval.

These are execution prerequisites, not changes implemented by this planning task.
No copy-paste live command is provided before the selector/ledger gates are met.

## Proposed fixed panel and resources

| Row | Public dev-train task | Version | Arm |
| --- | --- | --- | --- |
| 1 | original-darts-3065 | 1 | A |
| 2 | original-darts-3065 | 1 | B |
| 3 | original-montepy-933 | 2 | B |
| 4 | original-montepy-933 | 2 | A |

Paths: `tasks/dev-train/original-darts-3065/public.yaml` and
`tasks/dev-train/original-montepy-933-v2/public.yaml`.
Darts supplies an exposed public-check-PASS/acceptance-FAIL development case;
MontePy supplies an exposed successful-repair regression case. This is a deliberately
small mechanism/admission pilot, not a representative benchmark or generalization
test. Prior outcomes are selection context, not control-arm results.

Validated package identities at planning time:
- Darts public spec: `sha256:0e1366e9c8cf70b2c0bc3a9ba4eb9380e35eb1ccda2ea25723cfce2318a943aa`;
  package: `sha256:7375e3b698cf9cf5d5558e56c13c36094f577221025aca8b0b86be3046333b17`.
- MontePy public spec: `sha256:82311158f819177093f1f79fada6699253f56b9166cad9bc9c3bf19a662d30ed`;
  package: `sha256:e744e37bbef0a478328d5eb0b2e71bfa693ec17bf44a332cd1d7246f1c637b0b`.

Model: gpt-5.4-2026-03-05, xhigh, desired output 25,000 tokens. Same segmented-v1,
result-or-size-v1, brief-v1, repair-recheck, protected-v1 and per-call-v1 policies;
probes enabled, cases-v1 in both arms. One fresh invocation per row; no continuation.
Each row: USD 3.00 maximum, 1,800 seconds, 40 model calls, 100 tools, four accepted
edits; task mutation limits unchanged. Proposed global maximum: USD 12.00 across
four rows, with no transfer from unused row allocations or replacement rows.
Credential file for a later approval: `C:\Users\geonj\Documents\PatchLoop\.env`;
never read/publish its value in the plan or evidence package.

Existing source/dependency descriptors are candidates for revalidation, not current
readiness evidence or renewed authorization:
- Darts: `C:\pt\preparations\darts-next-repair-20260930-v1\prepared-source.json` and
  `C:\pt\prepared\original-darts-3065-probe-0927-v5\prepared-probe-dependencies.json`.
- MontePy: `C:\pt\preparations\montepy-next-repair-20260930-v1\prepared-source.json` and
  `C:\pt\preparations\montepy-next-probes-20260930-v1\prepared-probe-dependencies.json`.

## Input and stop rules

Give each run only its original public task and permitted repository/tool context.
Do not provide operator-written probes, the Darts correction/matrix, previous patches,
prior trajectories, evaluator details or hints derived from them. Each row starts
fresh; no outputs or notes from one row enter another. Do not add a reminder to use
probes, repair observed non-use with prompting, or change expectations after results.

Count immediately before dispatch and use zero SDK retries. Any count, transport,
billing, cleanup, state-identity or global-accounting uncertainty stops every remaining
row. A row's normal local cap/deadline outcome is retained as that outcome and does
not receive a retry. Missing infrastructure is not an agent error or a replacement
task opportunity. Preserve incomplete rows as NOT_RUN and all original evidence.

## Frozen outcomes and interpretation

For every row report submitted patch identity, registered public checks, isolated
acceptance, safety, actual settled cost, elapsed time and termination reason separately.
Primary task comparison is paired acceptance and public regressions; report per-task
A/B outcomes, not just an aggregate success rate. Also report absolute cost/time and
paired ratios where defined. Cap/unknown outcomes are not dropped from the panel.

After execution, use public action/source evidence to classify B's mechanism use:
was an agent-authored reference-free program saved and replayed unchanged across a
real source edit? Was it a valid test of the public requirement, an invalid setup/API/
expectation, or unresolved? Nonzero exit alone is not a behavioral counterexample;
zero exit alone is not correctness. Coverage/probe counts are descriptive only.

No valid cross-edit use -> NOT_EXERCISED; no follow-up paid rows or new prompt.
Use without paired correctness benefit -> NO_OBSERVED_BENEFIT; no default adoption.
Any lost control success -> REGRESSION, even if total successes tie.
All paired task outcomes tie -> INCONCLUSIVE, even with lower costs.
At least one B-only acceptance PASS, no A-only PASS, and valid mechanism use on the
improved task -> PROMISING_ON_EXPOSED_TASKS only. Report cost/time tradeoffs; this
one-pair-per-task pilot cannot establish a causal quality gain or justify adoption.
Public post-run audits do not overwrite isolated evaluator verdicts.

Every outcome ends this four-row allocation. No default change, additional tasks,
larger sample, automatic retry or general-quality claim follows from this plan.
