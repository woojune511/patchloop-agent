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

1. **REPRODUCE/explore:** search/read public allowed paths. Before the first plan, `run_check` is absent in V24-V28.
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

Lean V28 `v29/phase-evidence-v38` is a separate opt-in successor to immutable V27. Its plan request defines each
public lifecycle component once with owner span, responsibility and before/after state. Transitions refer to the
component array by integer index instead of repeating free-form identities. Admission validates current public span
provenance, index bounds/uniqueness, distinct states and mutation-owner coverage. On rejection it projects the exact
component count, collision/state indices, transition index violations, unknown spans and mutation-owner mismatch.
This consumes the same single durable plan-recovery slot; a second invalid request terminates before another provider
dispatch. The durable plan record binds the normalized registry and active plan hash. No validator certifies semantic
truth; visible checks and later evaluation retain that role.

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

Runtime capabilities gate trusted orchestration, not hostile code. R21 and all earlier approvals are consumed;
R22 is prestart-stopped and R23 is consumed/halted. The latter's one batch image inspection succeeded, but V26's
strict read schema failed during provider token counting, before the generation gate. No retry or resume is permitted.

Opt-in V27 preserves V26 workflow semantics and adds final-request strict-schema validation before token counting
and generation. A separate adapter leaves the legacy adapter byte-identical. Nullable direct/anchor reads normalize
to one operation while binding the original input for replay. Durable count receipts distinguish completed, failed
and outcome-unknown logical attempts from model generation; uncertain/failed attempts cannot auto-retry.
Work Item 82 adopts V25/V27 for R24 only, with versioned registry admission and the same pre-count request gate on both
arms. Its no-call assembler uses the actual public task/model and a synthetic pre-action prefix, stopping before the
count SDK. Later dynamic requests use separate public smoke mocks, not live AnyIO evidence. A validation-only empty
`required` equivalence preserves V25 no-argument wire bytes; V27's frozen validator and agent semantics stay unchanged.
Marked admission additions recover reviewed source bytes in memory. The one-inspect image contract is unchanged.
Lean V28 is selected only as a future `official=false` treatment; this changes no default runtime and observes no live
provider acceptance or task performance. No current candidate authorizes Docker, provider, evaluator, checks or cost.
Authority is in `docs/current-status.md`.
