# Architecture

상태: current effective overview. Historical milestone-specific designs are archived under
`docs/archive/snapshots/d121/02-architecture.full.md`.

## 1. Design principles

- One coding agent, explicit state machine and constrained tools
- Hidden evaluator outside workspace
- Durable run state outside the task repository
- Deterministic model/tool contracts
- Append-only evidence; fail-closed recovery
- Memory as a controlled input, never implicit mutation

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

`DONE` means patch submission; only the evaluator determines success.

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

The state machine requires public intake, evidence-producing reproduce/verify, current-diff checks, a model-visible
final diff and explicit budget/protocol/infrastructure terminals. PLAN is a phase, not a separate agent.

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

Evaluator-v1 safety is unconditional. V2's typed, receipt-gated local path keeps raw results unofficial. V5 is a
consumed checker error, not SDK-readiness evidence. V6 only source-qualifies sanitized diagnostics; parent runtime,
state and approval do not exist, and v1 evidence is unchanged.

Visible checks and agent self-review are feedback; neither can replace hidden evaluation.

## 7. Memory architecture

### Frozen assets

Three generalized entries have approved D-105 text and a D-110 frozen index; retrieval authority remains closed.

### Frozen R2 A/C source

`fixed-d110-bundle-v1` implements a narrow fixed-bundle adapter:

It verifies D-105/D-110 assets, assembles only the three texts in frozen order, renders A as null and C as the exact
3,528-byte bundle, and binds delivery through existing request/context evidence without retrieval events.

It loads no embedding model or scorer. D-122 binds the four-row suite offline, but R2 predates evaluator v2 and no
candidate or live result exists.

### Deferred paths

- B `raw_trace`: portable source selection, redaction and equal-budget truncation are incomplete.
- D `selective_structured`: independent applicability calibration and score policy are incomplete.
- D-121 external-source isolation work belongs to the deferred selective-calibration lane, not the fixed-bundle
  C runtime prerequisite.

## 8. Trust and authority boundaries

- Config, tests and a frozen index authorize neither paid calls nor retrieval/injection.
- A candidate ID does not technically authenticate a user; repository gates are cooperative and append-only.
- No active path may read private/hidden/reference data to construct memory or select a task.
- Failure at a one-use evidence claim remains consumed; it is not silently retried or repaired.

Current authority is summarized only in `docs/current-status.md`.
