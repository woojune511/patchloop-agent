# Pre-Work Item 80 topic snapshots

Historical audit only. These pre-successor descriptions grant no execution authority.

## Source: docs/02-architecture.md

# Architecture

Status: current effective overview. Milestone history is archived under `docs/archive/`; Rapid R1-R21 workflow history
is summarized in `docs/archive/rapid-workflow-history-20260830.md`.

## 1. Design principles

- The single coding agent is the product. Evaluation, recovery, memory and experiment machinery support it.
- Workflow transitions are deterministic; model autonomy is bounded to the tools exposed for the current state.
- Public task evidence and private evaluation stay physically and logically separated.
- Run state is append-only, content-addressed and outside the task repository.
- A runtime version is opt-in. A successor never edits or relabels predecessor traces or artifacts.
- External work requires a candidate-bound, one-use authority; offline qualification grants none.

## 2. System flow

```text
audited task package
  -> manifest and runtime admission
  -> isolated agent workspace
  -> INTAKE -> REPRODUCE -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW
  -> submitted diff
  -> separate private evaluator workspace
  -> immutable result, usage and verifier evidence
```

The task package fixes repository/base, public issue, allowed paths and visible checks. The private spec, hidden tests,
reference patch and oracle output enter only the evaluator. Event/checkpoint/evaluator state lives under the external
PatchLoop state root, never inside the task repository.

## 3. Components

| Component | Responsibility |
| --- | --- |
| `patchloop/agent/` | phase state machine, request projection, model dispatch and finalization |
| `patchloop/tools/` | registered read/search/edit/check/diff/finish implementations |
| `patchloop/state/` | events, artifacts, checkpoints, action identity and recovery |
| `patchloop/sandbox/` | local/container process boundary |
| `patchloop/verifier/` | deterministic hidden acceptance, regression, scope and safety grading |
| `patchloop/evals/` | manifests, candidate admission, schedules, metrics and append-only results |
| `patchloop/memory/` | fixed condition bundles and leakage-safe delivery |
| `patchloop/ui/` | read-only public trace viewer |

## 4. Agent runtime

Each model request receives the public task, phase contract, bounded public evidence, durable structured work state,
recent public events and only the permitted tool schemas. It receives neither raw hidden data nor replayed reasoning.
One turn may request one tool action.

The current workflow is:

1. **REPRODUCE/explore:** search/read public allowed paths. Before the first plan, `run_check` is absent in V24-V26.
2. **Plan:** cite current-diff public source spans and record a structured hypothesis, candidate files, intended change,
   expected behavior, preservation obligation and falsification condition.
3. **Implement:** apply one structured edit. A successful mutation records the active plan hash and invalidates stale
   source/check edit authority.
4. **Verify/correct:** run targeted checks before upstream checks. A failed visible check requires bounded fresh
   exploration and a plan revision before the next semantic mutation. Repeated same-signature failures must reject the
   prior hypothesis and select a different causal boundary.
5. **Review:** after all visible checks pass, obtain the full diff. One review correction is allowed only after fresh
   evidence and a revision; all checks and the diff must then be reacquired before submission.

Self-directed exploration keeps a minimum provenance gate without pretending to score understanding. After one current
source read, the model may plan or request another non-duplicate search/read with a bounded investigation intent.
Initial/correction information actions remain capped at 10/3. At the cap, the model may plan or explicitly declare
exploration exhausted; exhaustion creates no patch or submission. The request pins bounded question-target-result
cards, active plan and hypothesis disposition while excluding raw reasoning and duplicate source bodies.

Lean V24 `v26/phase-evidence-v34` projects an exact pre-plan tool surface and bounded investigation context without
rewriting durable V23 state. Lean V25 `v26/phase-evidence-v35` adds only the R20 compatibility seam: initial
`prior_hypothesis_disposition` is `null`-only, revisions retain `retained|refined|rejected`, and the bounded feedback
projector admits `bounded-self-directed-exploration-v1` only for V25. The first invalid plan consumes one durable retry;
a second restores as `WORK_PLAN_ADMISSION_REPEATED` before another dispatch. V22-V24 retain their old fail-closed
policy sets.

Lean V26 `v27/phase-evidence-v36` is an opt-in successor. A reasoning-only incomplete generation uses one
dedicated retry that does not consume the shared action/protocol slot; a second incomplete response terminates before
another dispatch. Plan-admission feedback retains full durable evidence but projects only hashes for older rejections
and at most 12,000 bytes for the latest public IDs. `read_file` may bind directly to an exact current-diff search match,
so the returned range must cover that match. Initial/revision plans also record generic lifecycle owners, before/after
states, transitions and falsifiable atomic postconditions. These fields constrain provenance and consistency; the
server does not certify that the model's semantic explanation is true. Existing repeated-failure causal reset and
different-boundary requirements remain unchanged.

## 5. Persistent state and recovery

Events are monotonically sequenced and hash chained. Checkpoints bind phase, workspace/diff identity, completed action
IDs, plan/revision chain, retry slots, exploration counters and artifact hashes. Tool actions bind action ID and input
hash so a restart can reconcile success without replaying an already committed mutation. Persisted request, projection
or chain tamper fails closed. Mock recovery validates enumerated crash points, not arbitrary live billing idempotency.

## 6. Evaluation boundary

The agent sees public task files and registered visible-check output. After a valid submission, the evaluator receives a
separate workspace and private task material. Primary success requires actual hidden acceptance, regression, scope and
safety evidence. Evaluator-v1 still uses literal safety PASS; evaluator-v2 supplies typed controls and receipts, but raw
development results remain `official=false`.

## 7. Memory architecture

Condition A injects no memory. Fixed condition C uses the audited D-110 bundle and order. Model-facing entries contain
general patterns, applicability, remediation, limits, validation and provenance, never answer code, hidden assertions,
reference patches, run identifiers or raw traces. B/D remain deferred and cannot inherit authority from public Rapid
runs.

## 8. Trust and authority boundaries

Runtime capabilities gate trusted orchestration; they are not a hostile-code security boundary. Docker/provider/cost
actions require an exact approved candidate identity. R21 and all earlier approvals are consumed. Candidate-v29 ran
once as a three-row V25 mechanical smoke and cannot retry; its 1/3 evaluator reach failed the 2/3 activation floor.
Work Item 76 adopts the reviewed V26 package for R22, paired with V25 in six interleaved rows. The new registry entry
admits plan-v30 and both exact runtime pairs; the shared append-only settlement driver remains unchanged. R22's approved
entry was subsequently stopped before batch start: row-start image inspections exceed the approved count. No agent
policy changed and no row started. The runner-continuity check stays excluded, not a task successor.
Work Item 78 adds opt-in `batch-pinned-image-admission-v1` for R23. One exact reference/digest is inspected after a
durable attempt marker; an ephemeral capability binds the approved plan and all six manifests. Each row reuses it
through the same live/rehearsal admission gate, with no daemon/version or per-row image lookup. A missing, changed or
foreign-batch receipt fails closed without reinspection; restart cannot deserialize live authority. The digest-pinned
`--pull never` container boundary is unchanged. The V25/V26 reasoning and tool policies are unchanged.
R23 subsequently halted on V26's provider schema rejection. Input-token counting is provider transport before the
ContextBuilt event and generation gate; a rejected count is absent from current usage counters. This gap is not fixed.
No current candidate authorizes Docker, provider, evaluator, visible checks or cost. Authority is in `docs/current-status.md`.

## Source: docs/03-contracts.md

# Contracts

Status: effective machine-visible contracts. Historical version/candidate narratives are in
`docs/archive/rapid-workflow-history-20260830.md` and `docs/09-evidence.md`.

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
row manifests before execution and issues typed one-use row capabilities. Rehearsal follows production order through
the provider-dispatch gate and stops before the call. Any source change supersedes the candidate at zero calls.

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

- `dedicated-generation-incomplete-recovery-v1` allows one retry for a reasoning-only incomplete model response without
  consuming the shared action/protocol recovery slot. A second such response yields
  `MODEL_GENERATION_INCOMPLETE_REPEATED` before a third model dispatch.
- `bounded-plan-admission-feedback-v2` validates the durable V25-compatible source, projects superseded rejections as
  hashes, and exposes only the latest public reason, gate/diff binding, evidence IDs and source-span IDs. The latest
  feedback is capped at 12,000 bytes; durable events and result artifacts are unchanged.
- Tool schema v27 keeps direct `read_file` and adds `search_anchor`. The anchor binds one successful current-run,
  current-diff `search_files` outcome sequence and match index. The server resolves the exact allowed path/range and
  rejects stale, foreign, out-of-range or replay-divergent anchors before read dispatch.
- `public-lifecycle-state-transition-plan-v1` requires public current-diff span-bound owners, distinct before/after
  states, affected-component transitions, one or more atomic postconditions and a public falsification observation.
  The final mutation span must have a lifecycle owner. The request records `semantic_truth_verified=false`; visible
  checks, not the schema validator, test the plan's semantics.
- Existing plan/revision admission, targeted-before-upstream order, fresh-read correction, correction limits and the
  repeated-public-failure `rejected` plus different-causal-boundary gate are inherited unchanged.

The separate `public-runner-continuity-composite-outcomes` artifact only source-qualifies an unexecuted public check
definition. It creates no task version, observes neither base nor reference behavior and grants no activation.

The V26 activation review binds the exact qualification and runtime-source hashes and accepts all four mechanisms only
as one product-package comparison variable. It forbids single-mechanism attribution and runner-check inclusion, records
`eligible-not-adopted`, creates no candidate and grants no external authority.

R22 separately adopts that frozen package for V25 3-row versus V26 3-row comparison. Only experiment
`rapid-public-dev-anyio-v5-v26-reliability-ab-20260831-r22` admits `v26/v35` and `v27/v36`, with seed `20260831`.
Plan-v30 and all six manifests must pass the registry before row capabilities. Removing the three exact R22
`contracts.py` additions must recover the reviewed source bytes; every other qualified agent source stays identical.
The current complete runtime build is separately hashed. Historical qualification/review files are never rebuilt in
place. AnyIO-v5, model, image, no-memory, per-row budget and evaluator are equal; reserve/cap are `$7.20`/`$7.50`.
The trusted task loader parses sealed schemas and hashes package bytes only for identity; no private/reference content
enters agent context or selection. Candidate/rehearsal creation itself grants no execution authority.

R22 is prestart-stopped: the real row-start path adds two image inspections per row to the wrapper's one, contradicting
approval for one total. The no-call provider-gate rehearsal did not cover this count. No row began; do not reuse that
approval or fabricate an agent terminal. Work Item 78 implements the separately hashed R23 receipt/count successor; it does not reopen R22.

### Batch-scoped image admission V1

R23 admits the same V25/V26 pair under plan-v32/candidate-v32/rehearsal-v29 and requires
`batch-pinned-image-admission-v1`. The approved plan binds one exact image reference/digest, one inspect attempt,
zero daemon-version/per-row inspections, six manifests and unchanged reserve/cap. Legacy capabilities keep their old
path. The public runner selects this by typed capability policy, not an experiment-ID branch.

- The live issuer writes/fsyncs an exclusive attempt event before its sole `image_identity_projection` call.
- RepoDigest membership, not equality with Docker's configuration ID, proves identity; both are retained in the receipt.
- The image capability belongs to the same in-process batch instance and admitted manifests; row capabilities remain
  one-use. Missing/foreign/copied authority, image drift or changed receipt fails before workspace/provider dispatch.
- Interrupted, failed or completed inspection records cannot issue authority after restart or retry. No fallback
  inspection, image pull/build/tag/remove/prune or implicit daemon probe is allowed on this path.
- Rehearsal projects all six row image/provider gates with `image_identity_observed=false`; it cannot become live.
  A separate guarded mock enters real `AgentRunner.start` six times and the shared settlement driver. Synthetic
  terminals exercise orchestration only; no agent, visible-check or evaluator behavior is measured.
- Exact reverse-delta audits recover the frozen R22 runner/contracts bytes; every other reviewed policy file,
  qualification and historical input is byte-identical. The complete successor runtime has its own build hash.

R23 exposed an unresolved provider compatibility gap: V26's strict `read_file` schema has `required=[]` despite its
properties. Input-token counting rejects it before ContextBuilt/generation dispatch; failed counts are not reflected
in usage. The generation capability rehearsal does not validate this provider schema subset. Runtime remains frozen.

## 7. Evaluator, memory and result contracts

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

## 8. Cost, completion and replay

Budget precheck, per-turn output ceiling, total token/call/cost limits and finalization reserve are distinct. Reaching a
turn or total limit is an agent terminal only after the exact request is evaluated against the contract. Settled-row
cost comparisons are interpreted with completion censoring; evaluator-reached subsets never replace the fixed
denominator.

Historical replay verifies stored hashes and deterministic projections; it cannot create live provider/Docker authority
or rehabilitate a consumed row. Fresh-source/Harbor contracts bind metadata, receipts, normalization, membership and
queues. Harbor remains 0/12 local images and pull/build/execution authority is closed.

## Source: docs/04-evaluation-protocol.md

# Evaluation protocol

Status: current effective protocol. Exact historical tuples are in `docs/09-evidence.md`; the Rapid workflow chronology
is in `docs/archive/rapid-workflow-history-20260830.md`.

## 1. Questions and dataset roles

PatchLoop separates three questions:

1. Does the agent complete the workflow and reach evaluation reliably under a fixed resource contract?
2. Conditional on a complete, fair batch, does a workflow or memory treatment improve fixed-denominator success/cost?
3. Does an independently frozen confirmatory panel support a limited external claim?

Smoke fixtures validate contracts. Public development tasks support rapid `official=false` learning and may be reused.
Qualification fixtures validate offline gates without provider/Docker/evaluator/check calls. Held-out tasks are frozen
before execution and cannot be tuned after outcomes are observed. Private specs, hidden tests and reference patches
never enter agent prompts, memory, task selection or public diagnosis.

## 2. Conditions and fair comparison

Condition A is no memory. Condition C is the fixed D-110 structured bundle. B/D remain deferred. A comparison fixes
model, prompt, tool/runtime, task/base, image, total and per-turn budgets, retry, evaluator, pricing and balanced
schedule. Workflow-successor experiments change only the declared versioned package and must state when several policy
changes are bundled, so a product-package result is not misreported as a single-policy causal effect.

Development and confirmatory work use different gates:

- **Rapid public development:** 6-12 rows, public tasks, `official=false`, one experiment plan, one validation command
  and one append-only bundle. Optimize evaluator reach, submission, success at budget, terminal class and cost.
- **Confirmatory:** fresh qualifying panel, preregistration, immutable receipts, independently frozen scoring and no
  tuning. It begins only after a public survivor is selected without consulting held-out outcomes.

## 3. Completion, metrics and interpretation

Every scheduled row has exactly one status: not started, harness/admission failure, infrastructure failure, agent
terminal, evaluator failure or scope-compliant success. Agent-rate denominators exclude only typed pre-agent admission
and infrastructure confounds; token, protocol, exploration and submission terminals remain observed zeros.

Required reporting includes:

- rows scheduled/started/settled and evaluator reach/submission/success at the fixed denominator;
- model/tool calls, input/output/reasoning tokens, total cost and terminal attribution;
- first-mutation search/read/check counts and files;
- edit attempts/acceptance, failed-check correction sequences and check order;
- `get_diff -> finish_task`, stale-evidence violations and infrastructure/confound counts.

Unequal completion censors cost. A lower mean from earlier terminals is not efficiency. Visible-check pass is not hidden
success; evaluator reach normally means submission completed and private evaluation started, not merely that public
checks passed. Selected evaluator-reached subsets cannot replace preregistered fixed denominators.

Public workflow diagnosis reads no model response/reasoning or private/hidden/reference material. It verifies event,
diff, check and result hashes, preserves sequence, and performs zero external/check/state-mutating calls. Observed facts
and hypotheses remain separate.

## 4. Rapid public development loop

Before paid work, the exact runtime/config/task/image/schedule/cost candidate is admitted in production order. Rehearsal
must reach the provider-dispatch boundary and stop without calling it. Two receipts must be byte-identical. Any source
change supersedes the candidate; execution needs a new exact reserve/cap approval. A consumed candidate cannot replay.

R20 compared three V22 rows with three V24 rows on AnyIO-v5 and settled 6/6 for
`$1.62950550`. Both variants reached/submitted/succeeded `0/3/0`; V24 made no mutation. Two V24 rows hit the internal
plan-feedback policy mismatch after invalid initial plans, so its lower cost is early-terminal censoring and agent
quality is inconclusive. R20 fails promotion floors and cannot retry.

Work Item 71 created Lean V25 offline. Production-shaped public mocks cover the two R20 exploration depths, a first
invalid plan followed by one bounded retry and completion, repeated invalid admission stopping before a third dispatch,
restart and request-hash tamper. Qualification and activation review were each built twice byte-identically; their
builders record zero provider, Docker, evaluator, visible-check, network or cost activity, while the real-shaped tests
exercise local mock checks. This permits only a separate candidate-adoption decision; it is not a rehearsal, live
result, quality result or generalization claim.

R21 was a consumed V25-only three-row mechanical smoke, not an A/B estimate. It settled 3/3 for
`$1.42525890`, with no harness/admission failure, initial plan and first mutation in 2/3, reach/submission in 1/3 and
success in 0/3. Two rows crossed R20's plan-feedback blocker, but reach failed the frozen 2/3 floor. V25 is not promoted;
R21 is immutable and cannot retry. Public diagnosis does not reveal row 2's hidden cause.

Work Item 74 selects R21's public mechanical/reliability classes without attributing row 2's hidden failure. Lean V26
is evaluated offline with focused unit, real-shaped mocked runner, restart and V19-V25 regression gates. Its
qualification must be byte-identical across two builds and record zero provider, Docker, evaluator, visible-check,
network and cost activity. The separately source-qualified runner-continuity script combines public skip, xfail,
ordinary-failure and later-pass outcomes under one module-scoped fixture/loop, but is not executed here. Neither
artifact is a candidate, Rapid result or task successor. The separate zero-call review accepts V26 only as one
non-attributable package and leaves it unadopted; candidate design remains a later decision.

Work Item 76 separately adopts R22: V25 control and V26 treatment, three rows each, ordered V25/V26, V26/V25,
V25/V26. The unchanged AnyIO-v5 task/image/model/no-memory/budget/evaluator and `$7.20` reserve/`$7.50` cap are bound
before execution. The runner-continuity check stays excluded. Six manifests and two identical production-order no-call
rehearsals must pass before exact one-use approval is requested. This preparation is not a measured A/B result.

Work Item 77 closed the approved entry before batch start because the full path would perform 13 image inspections
against approval for one. All six rows are not started; this is neither 0/3 agent success in each arm nor a promotion
failure. No public trajectory comparison can be made. The outer inspect count is unobserved, not presumed zero.

V26 promotion floors: zero harness/admission, infrastructure, contract and admission-loop-budget failures; valid initial
plan, first mutation and evaluator reach each at least 2/3; reach, submission and success no lower than same-batch V25;
mean settled-row cost at most 1.25 times V25. Every mutation needs a valid plan; targeted-before-upstream, fresh correction
reads and fresh submission check/diff evidence remain mandatory. Passing only selects a public-development default;
failure preserves its exact candidate without retry and motivates one next public failure class, not a quality/generalization claim.

R23 is the separately adopted Work Item 78 successor for the same V25/V26 six-row package comparison. It changes only
shared batch image admission, identically for both arms: one pinned-reference inspection reused across all rows.
Production-shaped qualification must enter the six actual row-start paths, observe one mocked inspect and zero
per-row inspections, and exercise durable failure/restart rejection. The two no-call rehearsals also enter every row's
shared image/provider gate, but do not assert that a real local image exists. Any interruption consumes the image
attempt marker; no reinspection/retry under that candidate is allowed. R22 stays closed. The floors above, AnyIO-v5,
model, image, no-memory, budgets, evaluator and `$7.20`/`$7.50` remained unchanged before exact approval.

R23 is now the latest consumed live batch: one inspect, two settled rows, four unstarted, `$0.16285425` total.
V25 submitted after all visible passes but failed hidden evaluation. V26's invalid strict read schema caused a provider
400 during pre-generation token counting. Preserve its infrastructure classification and do not count the unstarted
rows as agent failures. This halted, confounded schedule cannot compare or promote V26; no retry/resume is permitted.
Recorded zero generation calls in V26 does not establish zero API transport; the failed count is absent from usage.

## 5. Preregistered held-out A/C

The consumed held-out design froze 12 tasks by A/C by two repetitions, complete-panel SCRR and assumption-limited
stability/sign-flip diagnostics. Eligible evaluator FAIL and typed agent terminals score zero; infrastructure confounds
are inconclusive. R7/R11/R14/R15 remain immutable incomplete predecessors.

R16 settled 48/48 for `$27.24465825`: A 8/24, C 7/24, difference `-1/24`, stability `[-1/4, 1/6]`, sign-flip `p=1`,
same/cross 0/`-1/12`, benefit/negative flips 3/24 and 4/24. This unblinded consumed panel cannot tune caps, tasks,
memory, workflow or thresholds. It establishes neither memory benefit nor harm/generalization.

## 6. Confirmatory successor contract

A future confirmatory successor requires: an independently source-qualified fresh panel; raw-source completeness;
public/private separation; a frozen task/evaluator/runtime/cost schedule; no held-out tuning; deterministic typed
evaluator-v2 evidence; complete execution; append-only artifacts; and prespecified estimands/uncertainty. Selection must
use only public development evidence. No current artifact authorizes that work.
