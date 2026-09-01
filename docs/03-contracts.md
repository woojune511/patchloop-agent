# Contracts

Status: effective machine-visible contracts. Historical narratives are in `docs/archive/rapid-workflow-history-20260830.md` and `docs/09-evidence.md`.

## 1. Cross-cutting rules

1. Public task input is separated from private evaluator input.
2. Run/event/checkpoint/evaluator state is external to the task repository and append-only.
3. Tool execution is allowlisted by phase, task path and check ID; arbitrary shell is unavailable to the agent.
4. Action IDs plus input hashes make tool recovery idempotent.
5. Success requires real hidden acceptance, regression, scope and safety evidence; missing evidence fails closed.
6. A consumed run is never repaired, retried, relabeled or resumed.
7. Provider/Docker/cost authority binds an exact candidate and is one-use. Offline artifacts grant no authority.

## 2. Task and experiment inputs

`PublicTask` fixes task/version/split, repository/base, issue, allowed/forbidden paths, diff/file limits and ordered
visible checks. `PrivateTask` fixes hidden acceptance, regression, scope/dependency/API/safety controls and reference
provenance. Public hashes may be model-visible; private bodies may not.

Fair A/C comparison fixes model, prompt, tool/runtime, task, commit, image, budget, retry, schedule and evaluator. A is
null memory; C is the exact fixed D-110 bundle. Development task reuse is allowed only with `official=false`; held-out
results are no-tuning. B/D remain deferred.

An external candidate binds runtime build, config, task, image, schedule and cost hashes. Batch admission validates all
row manifests before execution and issues typed one-use row capabilities. R24 rehearsal reaches the initial request's
pre-count gate without transport. Any source change supersedes the candidate at zero calls.

## 3. Run, event and recovery contracts

`RunManifest` binds run/task/base/public/private hashes, runtime/tool/context versions, provider/model, budget, sandbox,
image identities, memory condition, fault policy and creation time. Each event binds run, sequence, type, actor,
timestamp, payload and predecessor hash. Artifacts are content-addressed; checkpoints bind the last durable phase and
the identities needed to reconstruct the next legal request.

Patch/check/submission actions are reconciled from durable success events before dispatch. A matching action ID/input
hash is reused only as the same action; conflicting input fails closed. Recovery restores exploration counts, current
diff, source/evidence eligibility, plan/revision chain and shared retry slots. It does not infer success from an
incomplete side effect.

`BatchExecutionAuthorization` and `RowExecutionAuthorization` are trusted-harness capabilities, not agent tools or a
hostile-code boundary. Admission/infrastructure errors before agent start are typed separately and excluded from agent
failure rates. Terminal-parity driver V2 persists the row decision before advancing the schedule.

## 4. Agent tool and workflow contracts

The request supplies an exact phase surface from registered schemas. One model turn may contain one tool call. Multiple
calls, unavailable tools, invalid check IDs or invalid structured arguments are rejected before dispatch and share one
bounded protocol-recovery slot.

Core tools are `search_files`, `read_file`, `record_work_plan`/`revise_work_plan`, `apply_structured_edit`, `run_check`,
`get_diff`, `finish_task` and `declare_exploration_exhausted`. Search is directional support, not source coverage.
Reads record only model-visible ranges as current-diff source spans; truncated/omitted ranges do not become eligible
evidence. Edits bind exact expected/replacement text, allowed paths, current diff and active plan hash.

Additional pre-plan search/read requires a provenance-bound `investigation_intent`: one blocking public-code question,
current source-span basis, a target role and expected information gain. Duplicate normalized path/range or query/glob in
the same episode is rejected before dispatch. The server validates provenance, scope, format and duplication, not the
truth of the prose.

A plan cites eligible current-diff source spans, candidate files and a structured causal mechanism. It records intended
change, expected behavior, preservation obligation, falsification condition, readiness mode and non-blocking unknowns.
Initial plans require at least one source read and normally two coverage keys; the co-located exception requires one
span to bind ownership, execution and final mutation site. Correction plans also require the current failed-check
evidence plus a fresh post-failure read. Review correction requires full-diff review plus a fresh read.

Successful mutation invalidates source/check edit authority, retains the structured hypothesis history and forces the
targeted check sequence again. Mechanical edit rejection changes no worktree state, keeps the plan, invalidates the
read used for editing and requires reread. A semantic correction after a failed check requires a new revision. The same
public failure signature across distinct diffs requires `rejected` disposition and a materially different causal/file
boundary. Check-attempt and review-correction limits remain 3 and 1.

`structured-edit-diff-check-replay-v1` records normalized edit, resulting diff, check identity/output and replay hashes.
Submission requires ordered visible-check evidence for the current diff and a complete current diff review. No stale
check or diff can authorize `finish_task`.

## 5. Lean V25 compatibility contract

Lean V25 binds `lean-harness-v25`, tool schema `v26`, context `phase-evidence-v35`, request evidence
`lean-harness-request-evidence-v25` and `trigger-bound-plan-contract-compatibility-v1`.

- Initial `record_work_plan` exposes `prior_hypothesis_disposition` as exactly `{type:null, enum:[null]}`.
- Check-failure/review `revise_work_plan` exposes exactly `retained|refined|rejected`.
- Server semantic admission remains the inherited causal/self-directed validator.
- Only the V25 feedback projector additionally admits `bounded-self-directed-exploration-v1`; V22-V24 stay unchanged.
- First invalid plan: no tool dispatch, one durable retry consumed, bounded reason/catalog feedback in the next request.
- Second invalid plan for the gate: `WORK_PLAN_ADMISSION_REPEATED` before another model or tool dispatch.
- Restart restores the same gate/slot; persisted request, projection and closure hashes are revalidated.

The offline qualification/review bind both public R20 contract-failure rows but do not replay model responses or raw
reasoning. They create no candidate and authorize no external call.

R21 admitted V25 only for its exact three-row experiment. Candidate-v29's registry admission, two no-call rehearsals
and one fully settled execution are immutable. Its consumed approval cannot retry or transfer; the mechanical smoke
supports no comparative quality/generalization claim. Exact identities remain in `docs/09-evidence.md`.

## 6. Lean V26 reliability contract

Lean V26 binds `lean-harness-v26`, tool schema `v27`, context `phase-evidence-v36` and request evidence
`lean-harness-request-evidence-v26`. It is additive; V25 and consumed R21 identities remain immutable.

- `dedicated-generation-incomplete-recovery-v1` permits one reasoning-only retry outside the shared action slot; a
  second yields `MODEL_GENERATION_INCOMPLETE_REPEATED` before a third dispatch.
- `bounded-plan-admission-feedback-v2` hash-compacts older rejections and caps the latest public IDs at 12,000 bytes
  without changing durable events. Anchored reads bind one current-run/current-diff search match and fail closed on
  stale, foreign, out-of-range or replay-divergent provenance.
- `public-lifecycle-state-transition-plan-v1` binds public owner/state/transition/postcondition spans and records
  `semantic_truth_verified=false`. Existing plan/revision, ordered-check, fresh-read, correction-limit and repeated-
  failure different-boundary gates remain unchanged.

The separate runner-continuity artifact source-qualifies an unexecuted public check only. It creates no task version,
observes no behavior and grants no activation. R22/R23 cannot retry or transfer; no mechanism effect was established.

### Batch-scoped image admission V1

R23's `batch-pinned-image-admission-v1` bound one exact RepoDigest inspection to the same in-process six-manifest batch;
row capabilities stayed one-use and any missing/foreign/drifted/interrupted receipt failed before workspace/provider
dispatch. No fallback inspection, pull/build/tag/remove/prune or daemon probe was allowed. No-call mocks measured no
agent/check/evaluator behavior. R23 later exposed V26's invalid nonempty-read `required=[]` before generation;
consumed V26 is frozen and V27 is opt-in. Full immutable details are in the Work Item 79 archive.

## 7. Lean V27 strict provider admission

Opt-in `lean-harness-v27` / `v28` / `phase-evidence-v37` inherits V26. R24 adds exact V25/V27 live manifest admission;
the frozen Work Item 81 review is not rewritten. Candidate-v33/plan-v33/rehearsal-v30 grant no paid authority.

- `required-nullable-anchored-read-v1` requires all direct/anchor fields with exactly one nullable mode and binds raw
  input, normalization, resolved search provenance, diff, intent and replay. Invalid modes consume the shared slot.
- `responses-strict-tool-admission-v1` validates final dynamic schemas before count/create: nested objects are closed,
  every property is required and unsupported features fail closed. Local success is not provider acceptance.
- Strict count/generation entries use zero SDK retries and the same consumed row capability. Hash-bound count
  start/finish receipts survive without `ModelCalled`; logical failed/unknown attempts are not certified HTTP/billing.
- Failed/interrupted counts stop before generation and cannot auto-retry. Infrastructure classification, the old
  adapter, V26 schemas, plan/check/submission behavior and consumed artifacts remain immutable.
- R24 added the same pre-count request gate to both arms. Empty `required` equivalence applies only to closed empty
  objects and changes no wire bytes. Rehearsal stopped before count and proved no later bytes/count/budget/acceptance.
- R24 exposed free-string lifecycle relations/non-specific `unbound` feedback; its atomic timeout lacked continuation's `RECOVERY_ERROR`. R24 is immutable and cannot retry or resume.

## 8. Lean V28 lifecycle component-binding contract

Opt-in `lean-harness-v28` / `v29` / `phase-evidence-v38` and request evidence v28 inherit V27 without changing it.

- `public-lifecycle-component-binding-plan-v2` defines `components[]` once. Each component binds a current public
  source span, responsibility and distinct before/after states. Each transition uses zero-based
  `affected_component_indices`; atomic postconditions retain public evidence spans and falsification observations.
- Admission rejects duplicate names, unchanged states, duplicate/out-of-range indices, unknown spans and absence of
  the final mutation span from component ownership. It validates structure/provenance only and records
  `semantic_truth_verified=false`; it neither reads nor certifies private/hidden/reference/reasoning material.
- `public-lifecycle-relation-mismatch-v1` returns exact component/index/span mismatch fields and a hash through
  `bounded-plan-admission-feedback-v3`. The first invalid plan consumes the existing durable recovery slot. A second
  yields `WORK_PLAN_ADMISSION_REPEATED` before a third plan/provider dispatch; restart preserves both slot and hash.
- A successful plan records `public-lifecycle-component-binding-v2`, binding run/diff/plan hashes, the normalized
  registry, cited spans and mutation-owner index. Existing targeted-before-upstream, correction, review, submission,
  strict-schema/count and repeated-failure causal-reset contracts remain unchanged.

Work Item 86 selects V28 only as a future `official=false` treatment against V27. The append-only decision changes no
runtime/default, creates no candidate/authority and preserves provider, semantic, timeout and generalization unknowns.

## 9. Evaluator, memory and result contracts

Primary success is `hidden_pass and regression_pass and scope_pass and safety_pass`. Evaluator-v1 still assigns literal
safety PASS and cannot produce official new evidence. Evaluator-v2 uses authenticated typed controls and receipts with
severity `ERROR > FAIL > NOT_RUN > PASS`; raw results remain `official=false` until the full protocol is satisfied.

Memory entries bind generalized pattern, applicability, remediation, limits, validation and provenance. Fixed C exposes
only approved `model_facing_text`; traces, run IDs, retrieval/ranking data, answer code, hidden assertions and reference
patches are excluded.

Result bundles preserve exact schedule order, one start/terminal/settlement per row, usage and cost. Public diagnosis
verifies the append-only content-hash chain and a 1:1 public normalization transcript, then reads only public task,
manifest, tool/check metadata and public artifacts. It excludes response/reasoning text and private/hidden/reference
material.

## 10. Cost, completion and replay

Budget precheck, per-turn output ceiling, total token/call/cost limits and finalization reserve are distinct. Reaching a
turn or total limit is an agent terminal only after the exact request is evaluated against the contract. Settled-row
cost comparisons are interpreted with completion censoring; evaluator-reached subsets never replace the fixed
denominator.

Historical replay verifies stored hashes and deterministic projections; it cannot create live provider/Docker authority
or rehabilitate a consumed row. Fresh-source/Harbor contracts bind metadata, receipts, normalization, membership and
queues. Harbor remains 0/12 local images and pull/build/execution authority is closed.
