# Product and architecture

## Product

PatchLoop is one coding agent that repairs a public software task. It inspects
source, applies a bounded mutation, verifies the current diff with registered
checks, submits it, and receives a public-safe summary from a separate private
evaluator.

The evaluator, state journal, workspace manager, sandbox, and model adapter are
supporting layers. The product is the agent and its ability to reach a durable
submission reliably.

## Development objective

Use short `official=false` loops to improve completion and submission reliability.
Optimize for an answerable next question and a durable terminal. Historical
runtime comparability and claim-producing evaluation are separate concerns.

## Runtime shape

```text
public task ──> dev-head ──> constrained model/tool loop
                    │                   │
                    └──> external JSONL journal
                                        │
                                        v
                               submitted patch artifact
                                        │
                                        v
                            separate private evaluator
                                        │
                                        v
                          PASS/FAIL + public failure class
```

`dev-head` has four states: `WORK -> VERIFY -> REVIEW -> SUBMITTED`. There is no
separate planning phase, runtime-version switch, memory retrieval path, or
candidate/qualification workflow.

## Main components

- `patchloop/dev/runner.py` composes the mutable loop.
- `patchloop/dev/tools.py` provides registered read, search, mutation, check, and
  finish tools.
- `patchloop/dev/state.py` stores append-only, hash-chained run events.
- `patchloop/dev/cost.py` performs provider cost admission immediately before dispatch.
- `patchloop/agent/model.py` owns stateless model requests with zero SDK retries.
- `patchloop/repository.py` creates isolated workspaces and full diffs.
- `patchloop/sandbox/runner.py` runs registered checks locally or in a pinned image.
- `patchloop/verifier/core.py` evaluates the submitted artifact in a separate workspace.

## Scope

Current development includes public source inspection, constrained edits, visible
checks, action recovery, cost enforcement, external run state, and isolated
private evaluation. It excludes memory experiments, held-out tuning, claim runs,
automatic provider retries, Docker startup, image pull/build, and compatibility
with deleted historical runners.
