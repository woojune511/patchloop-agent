# Architecture

상태: current effective overview. Historical milestone-specific designs are archived under
`docs/archive/snapshots/d121/02-architecture.full.md`.

## 1. Design principles

- One coding agent, explicit state machine and constrained tools
- Hidden evaluator outside the agent workspace
- Durable run state outside the task repository
- Deterministic contracts around model/tool boundaries
- Append-only evidence and fail-closed recovery
- Memory as one controlled input, never as an implicit agent mutation

## 2. System flow

```text
audited task + immutable repository snapshot
                    |
                    v
        constrained single coding agent
        INTAKE -> REPRODUCE -> PLAN
        -> IMPLEMENT -> VERIFY -> REVIEW -> DONE
                    |
                    v
          submitted patch and run trace
                    |
                    v
     separate hidden evaluator and policy checks
                    |
                    v
       immutable result, usage and evidence
```

`DONE` means the agent submitted a candidate patch. Only the evaluator determines task success.

## 3. Components

| Component | Responsibility |
| --- | --- |
| `patchloop.agent` | Phase policy, context construction, model turns and tool dispatch |
| `patchloop.tools` | Search, read, patch, registered checks, diff and submission |
| `patchloop.state` | Events, checkpoints, CAS and recovery identities |
| `patchloop.sandbox` | Workspace and process/container boundaries |
| `patchloop.verifier` | Hidden/regression/scope checks plus typed v2 evidence, receipt and revalidation |
| `patchloop.failures` | Evidence-backed failure taxonomy |
| `patchloop.memory` | Entry schema, rendering, index and memory-delivery helpers |
| `patchloop.evals` | Suite preflight, immutable schedule, execution and reporting |

## 4. Agent runtime

The generic comparison agent is frozen to SYSTEM_PROMPT_V3, tool schema v2 and phase-evidence-v5.
Each provider turn is rebuilt from durable public state; `previous_response_id` is not used. The tool surface
does not expose arbitrary shell or unrestricted filesystem mutation.

The state machine enforces:

- a public issue intake before implementation;
- evidence-producing reproduction and verification;
- current-diff visible checks before submission;
- a model-visible final diff;
- explicit terminal errors for budget, protocol and infrastructure failures.

PLAN is a phase, not a separately approved planning agent or hidden plan artifact.

## 5. Persistent state and recovery

Events are monotonically sequenced and content-addressed. Checkpoints store phase, workspace identity,
completed actions and relevant artifact hashes. Patch actions have stable identities so a restarted worker can
reconcile the current diff and avoid replaying an already committed mutation.

Historical recovery tests do not imply the current live baseline supports arbitrary hard restart. D-097 live
resume remains disabled and external billing idempotency is not proven.

## 6. Evaluation boundary

The agent can see only public task files and registered check output. The evaluator receives private task
material only after submission and runs in a separate workspace/container. Target primary success is the
conjunction of hidden acceptance, regression, scope and safety.

Evaluator-v1 safety is unconditional. V2 binds typed producers to accepted events/CAS; separate authority and its
append-only receipt gate runner selection, persistence, qualification and completion. Raw results stay unofficial.
Successor source is qualified. Preflight v3 is consumed Docker-blocked; v4 is self-attested. V5 is executable but
source-qualified only: its approval gate precedes intent/ACTION_STARTED and any Docker/SDK observation. None is an
evaluator result and v1 evidence is unchanged.

Visible checks and agent self-review are feedback; neither can replace hidden evaluation.

## 7. Memory architecture

### Frozen assets

Three generalized memory entries have approved D-105 model-facing text and a D-110 frozen index. The index
contains source provenance and embeddings, but runtime retrieval authority remains closed.

### Frozen R2 A/C source

`fixed-d110-bundle-v1` implements a narrow fixed-bundle adapter:

1. It verifies the exact D-105 gate/render files and D-110 index, marker and completion gate.
2. It assembles only the three approved texts in frozen D-110 `group_provenance` order.
3. A renders `selected_memory=null`; C renders the exact 3,528-byte bundle on every model request.
4. The existing model-request artifact and `ContextBuilt` event bind delivery and normalized no-memory request
   hashes without exposing source-run provenance, vectors or raw traces.
5. It emits neither `MemoryRetrieved` nor a new delivery event.

The implementation loads no embedding model and performs no similarity, ranking or threshold. D-122 binds the
four-row suite and trace qualifier offline. This R2 source predates evaluator v2; execution is paused and a new
source/suite/runtime identity is required after evaluator correction. No candidate or live result exists.

### Deferred paths

- B `raw_trace`: portable source selection, redaction and equal-budget truncation are incomplete.
- D `selective_structured`: independent applicability calibration and score policy are incomplete.
- D-121 external-source isolation work belongs to the deferred selective-calibration lane, not the fixed-bundle
  C runtime prerequisite.

## 8. Trust and authority boundaries

- Config files and tests never authorize paid calls.
- A frozen index does not authorize retrieval or injection.
- A candidate ID does not technically authenticate a user; repository gates are cooperative and append-only.
- No active path may read private/hidden/reference data to construct memory or select a task.
- Failure at a one-use evidence claim remains consumed; it is not silently retried or repaired.

Current authority is summarized only in `docs/current-status.md`.
