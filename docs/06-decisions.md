# Effective decisions

Status: current decisions only. Historical decision chronology through R20 is in
`docs/archive/rapid-workflow-history-20260830.md`; older full documents are under `docs/archive/snapshots/d121/`.

## Product and evidence

- Keep one coding agent. Independent reviewer agents, memory variants B/D, arbitrary shell, PR creation and human
  handoff are separate future variables.
- Treat the agent as the product; evaluator, recovery, memory and experiment layers support measurement and safety.
- Separate rapid public development from confirmatory evaluation. Every Rapid output is `official=false`.
- Preserve public/private separation and append-only evidence in code, not only in prompts or prose.
- Do not infer improvement from qualification, mock completion, evaluator-reached subsets or censored cost.

## Workflow and recovery

- Use a deterministic outer state machine with bounded tool choice inside each state.
- Require public current-diff evidence and a structured plan before semantic mutation.
- Permit self-directed extra exploration after the minimum provenance gate; do not make a validator guess whether the
  model truly understands the code.
- After a failed check, require fresh exploration and a revision before semantic correction. If the same public
  signature survives distinct diffs, require rejection of the prior hypothesis and a different causal boundary.
- Roll back the latest successful mutation only at the versioned repeated-failure boundary. Mechanical edit rejection
  does not change the worktree and requires reread, not a new semantic revision.
- Targeted checks precede upstream checks. Review correction requires full revalidation and a fresh diff.
- Share one bounded action/protocol admission slot per gate and persist it across restart. A reasoning-only incomplete
  generation in V26 has a separate one-use slot so it does not consume an action-contract retry.

## Evaluation and authority

- Keep evaluator-v1 safety gap explicit; only deterministic typed evaluator-v2 evidence can support a future official
  result.
- Keep A null and C exactly D-110. The consumed R16 difference `-1/24` supports no memory claim or panel tuning.
- D-142 remains source-qualified only, unactivated and deferred. Harbor remains 0 present/12 missing.
- External execution requires an exact candidate/runtime/config/task/image/schedule/cost hash, two byte-identical no-
  call rehearsals and a separate one-use reserve/cap approval. Source changes supersede the candidate at zero calls.
- A consumed candidate cannot retry, resume or transfer approval.

Completed R20–V26 decision narrative is preserved in `docs/archive/r20-v26-decisions-20260831.md`.
It is historical audit only; effective runtime behavior remains in `docs/03-contracts.md`.

## 2026-08-31 - external-boundary successors

R22 adopted the V25/V26 package but stopped before rows because its path exceeded the one-inspection approval.
R23 added a one-use batch image receipt without changing agent policy, then halted on V26's strict-schema rejection.
Both attempts remain closed; their decisions are archived in `docs/archive/work-item-79-status-runbook-limits-20260831.md`.

Work Item 80 adds V27 only as an offline opt-in: nullable direct/anchor reads, final strict-schema admission and durable
input-count receipts. It changes no task/check, plan/revision, budget or evaluator policy. A pure local gate is not
provider acceptance; keep it before count and create. Work Item 81's review remains frozen. Work Item 82 adopts V25/V27
for six R24 rows, with one common request-authority gate. Rehearsal uses real public task/model inputs and a synthetic
pre-action prefix, stopping before count SDK dispatch. Closed empty-object `required` equivalence is validation-only,
not a V25 wire/policy change. Later dynamic schemas require separate mocks; exact paid approval remains separate.

Work Item 83 consumed that exact approval once. Preserve the 3 settled/3 unstarted schedule and reject retry/resume or
promotion. Treat the three `lifecycle_state_transition_unbound` plan rejections as a machine-contract friction because
the request repeats free-form component identities while server admission enforces a cross-field relation not named in
feedback. Do not weaken fail-closed validation. Work Item 84 therefore added an offline opt-in component registry with
integer transition references and exact public mismatch feedback. It retains the one-use fail-closed recovery boundary
and does not claim semantic correctness from schema admission.

Work Item 85 reviewed that package without calls and recorded `eligible-not-adopted`. The observed contract friction is
addressed structurally, but wrong semantic component choices, the targeted-check failure, provider timeout and live
provider acceptance remain open. Work Item 86 adopts V28 only as a future `official=false` Rapid treatment against
V27; it changes no default runtime and carries every open risk into the later comparison.

## Ordered research path

Work Item 79 consumed R23 once, then closed it after V26's pre-generation strict-schema rejection. Preserve two settled
rows and four unstarted rows, not a failed six-row comparison. Keep predecessor artifacts and behavior immutable;
V27's review transferred no paid authority. R24 then consumed its separate approval and halted after 3 rows. Work Item
86 selects V28 treatment only; Work Item 87 may prepare a fresh candidate/rehearsal but has no execution authority.

When authority and resources exist, the order remains:

1. evaluator correctness v2;
2. consumed A/C evidence audit;
3. Lean Harness offline gates;
4. Rapid Public Development Loop;
5. survivor-only fresh confirmation;
6. B/D on a separately frozen fresh panel.

Later steps cannot borrow authority or evidence from earlier ones. R22 is prestart-stopped; no retry or external
authority remains. R23 and R24 are consumed and halted; their unstarted rows cannot resume.

## Open questions

1. Should the public runner-continuity proposal receive separate base/reference behavior qualification before any task
   successor decision?
2. Should exact qualification-leaf symlink provenance be hardened before a future candidate?
3. When should evaluator-v2 and a fresh qualifying snapshot take priority over further public iteration?

These questions create no Docker/provider call or paid authority. `docs/current-status.md` owns the active
answer and `docs/05-implementation-plan.md` owns the next authorized offline seam.
