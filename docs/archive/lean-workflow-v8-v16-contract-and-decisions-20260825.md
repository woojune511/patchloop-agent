# Lean workflow V8-V16 contract and decision history — 2026-08-25

Status: audit-only extraction from active contract/decision documents. `docs/current-status.md` and current source own
present behavior and authority.

## Contract evolution

The pre-R7 phase-evidence v8-v15 identities and consumed R4-R6 are historical. The
`v10/phase-evidence-v16` descriptor-role successor preserves earlier mechanics; `v11/phase-evidence-v17` adds shared
actionless/incomplete recovery and deterministic completion. R7 and R8 approvals are spent.

V8 `ordered-check-refresh-structured-correction-v1` binds one next check, disables parallel calls, gates upstream on
targeted pass, requires current reads after check/edit failure and uses bounded target ceilings. V9
`v13/phase-evidence-v19` adds bounded investigation, fresh reads, three corrective mutations per check, one review
correction and a shared one-retry model-action contract. V10 `v14/phase-evidence-v20` adds public TaskSpec and durable
`PLAN_RECORDED`; mutation is unavailable before a valid current-run/current-diff public-evidence plan.

V11 `v15/phase-evidence-v21` introduces `eligible-plan-evidence-catalog-v1`. Public successful read/check results may
found a plan, search is support only, and exact replay requires action/input/diff/artifact identity. The second invalid
request at one admission gate yields `WORK_PLAN_ADMISSION_REPEATED` without another provider dispatch. V12
`v16/phase-evidence-v22` adds append-only parent-linked revisions, patch plan hashes and pinned bounded active work
state. Check-failure/review correction requires current evidence; mechanical edit rejection requires reread only.

V13 `v17/phase-evidence-v23` retains the workflow-selected surface and output ceiling through finalization. V14
`v18/phase-evidence-v24` pins one typed durable failed-check descriptor and fails closed if exact reconstruction is
impossible. V15 `v19/phase-evidence-v25` projects a bounded public failure signature; the second consecutive match on
distinct diffs requires search, fresh read and a rejected-hypothesis revision without widening correction limits.

R12 admitted only V8/V15 and is consumed. Lean V16 `v20/phase-evidence-v26` validates every raw candidate/read pair,
groups valid bindings by normalized path, selects the latest canonical read and retains every cited foundation
descriptor. Its durable normalization cannot merge different paths or admit search/support evidence. The shared Rapid
CLI leaves env files untouched in rehearsal and requires the strict single-key loader for execute mode; candidate/hash/
cost admission remains in the production dispatcher.

Input-count v2 mirrors `parallel_tool_calls=False`. Consumed audit reads frozen bytes while live admission requires
current source. Split/finalization/phase limits and `structured-edit-diff-check-replay-v1` remain fixed.

## Effective decisions preserved for audit

### Visible evidence catalog and mutation-epoch planning

- Preserve consumed V8/V10 and R9/R10 bytes; V11/V12 are opt-in.
- Build plan authority only from post-compaction public results visible in the request. Bound each plan gate to one
  recoverable rejection and continue observe-hypothesize-edit after the first mutation.
- Pin structured work state, not raw reasoning. Reacquire source/check authority after mutation.
- The consumed V8/V12 comparison grants no retry or quality authority.

### Reserve finalization, failed-check pin and semantic reset

- R11's reserve-finalization error is infrastructure but the batch still failed promotion. V13 changes only that
  schema path and accepts no legacy alternate.
- R11 row 3 observed the configured initial-plus-three mutation bound; do not increase it. Row 6's 30 reads reflected
  an evicted typed trigger, so V14 pins only that trigger and terminates if reconstruction fails.
- One R11 row repeated one public failure signature across four diffs while refining its hypothesis. V15 requires a
  bounded rejected-hypothesis reset; it does not infer a task solution. The disclosed excluded-fixture glob was not
  used by policy/qualification and blocks uncontaminated-transfer claims.
- V15 activation and R12 candidate/rehearsals were append-only and one-use. R12 reached V15 evaluator 1/3 and success
  0/3, failed promotion and cannot retry.

### Mechanical successor

- Preserve the R12 duplicate-path `plan_schema_invalid` and pre-Docker credential-wrapper stop as historical failures.
- Lean V16 validates first, then normalizes same-path bindings with durable public metadata. Future Rapid rehearsal
  cannot read `.env`; execute requires the safe exact-key loader.
- Qualification is synthetic/public/mock and zero-call. It grants no live candidate, paid authority or quality claim;
  remaining work returns to immutable public terminal diagnosis.
