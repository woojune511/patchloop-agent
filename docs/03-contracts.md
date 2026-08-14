# Data and tool contracts

상태: current contract map. Pydantic models, exact JSON artifacts and tests are authoritative. The cumulative
D-001–D-121 prose is preserved at `docs/archive/snapshots/d121/03-contracts.full.md`.

## 1. Cross-cutting rules

- JSON/YAML input uses strict schemas and rejects unknown fields where the owning model is strict.
- IDs derive from canonical content; mutable observations also carry file SHA-256 and byte size.
- UTC timestamps and nondecreasing chronology are required where ordering is material.
- Evidence writers use new-only/append-only attempt records; a new attempt may reuse unchanged source/configuration.
- Public and private task material use separate files and loaders.
- Runtime authority must be explicit; preparation and validation are not execution.

## 2. Task package

Each audited task separates public issue/check inputs from private acceptance, reference patch and audit
evidence. `data/dataset-manifest.yaml` owns dataset role.

Held-out task content may not be used to tune prompt, memory, score policy or selection.

## 3. Experiment inputs

`ExperimentSuite` binds purpose, ordered rows, runtime tuple, budget, pricing, dataset and execution hash.
Current A/C sources are:

- `heldout-ac-preregistration-20260814-v1.yaml`: standalone, execution-closed 48-row task-cluster design;
- `heldout-ac-suite-20260814-v1.yaml` and its plan: strict metadata-only 48-row contracts outside `ExperimentSuite`;
- held-out contract R2, binding R5 and execution/preflight R1/R2 are immutable source predecessors. Materialization R1
  binds 12 evaluator-side packages as opaque templates and prices. Preflight/dispatcher R7 independently binds the
  current secret-free candidate producer, run-manifest-v2/ephemeral marker expansion, exact `$252`/`$275` paid plan,
  append-only journal, one-use rows, persisted-v2 authenticator/replay and complete/inconclusive boundary. R3/R4 are
  preserved zero-authority pre-activation predecessors; R3-R6 created no candidate or runtime;
- `ac-structured-pilot-v11.plan.yaml`: R10-qualified contract-hardened split-budget design used by sealed R8;
- `dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml`: consumed Moto/Babel A/C suite whose four rows all
  resolved, evaluator-v2 receipt-qualified and cost-settled; R7/R9 remains superseded unexecuted;
- R6/R8 and R5/R7: immutable post-evaluator qualification failures; R4/R6-qualification: immutable
  provider-before-dispatch `$0` terminal;
  R3/R5-source-qualification: immutable partial live predecessor.

R1/R2 plans, suites and runtime seals remain immutable predecessors.

An accepted plan/suite grants no provider, evaluator, Docker, runtime-memory or cost authority.

Held-out fixtures never impersonate runtime schemas and emit `official=false`, `analysis_ready=false`. Templates omit
credential-derived markers. Only the R4 dispatcher may unlock analysis, after 48 exact independently authenticated
and settled persisted rows. A fresh no-call candidate and paid approval remain separate gates.

## 4. Run manifest

Every run binds task/source/image, prompt/tool/policy, model/service/transport, memory, limits, fault/schedule
identity and pricing/accounting.

A and C manifests differ only in the memory condition and evidence derived from it. A must bind no index; C
must bind the D-110 index and `fixed-d110-bundle-v1`. The manifest/preflight matcher rejects a legacy
`latest_frozen_index` serialization, suite tamper, wrong profile, source drift or schedule drift. Both
conditions retain the identical runtime tuple and resource ceilings.

Exact R3/R8 runtime and budget tuples are immutable in `docs/09-evidence.md`.

## 5. Event and checkpoint contracts

Events bind run/sequence/time/actor/type/payload/artifacts; checkpoints bind phase, workspace/diff and completed
actions. Usage precedes a malformed terminal. Observations are immutable; corrections explicitly reference them.

## 6. Tool contract

The generic comparison surface is tool schema v2:

| Tool | Boundary |
| --- | --- |
| `search_files` | Literal, bounded search in allowed public files |
| `read_file` | Bounded public-file reads |
| `apply_patch` | Existing tracked text files only; idempotent action identity |
| `run_check` | Task-registered visible checks only |
| `get_diff` | Current allowed diff and provenance |
| `finish_task` | Structured submission after current-diff verification |

No unrestricted shell, arbitrary command, new-file creation, rename or binary patch is exposed to the agent.

## 7. Failure memory

A memory entry binds generalized pattern, applicability, remediation, limits, validation and provenance. Only approved
D-105 `model_facing_text` enters fixed C; run IDs, traces, vectors and reviewer fields do not. D-110 is immutable
storage, not runtime authority; retrieval remains false.

## 8. Fixed-bundle C delivery contract

`fixed-d110-bundle-v1` makes A null/zero and renders C's exact ordered 3,528-byte D-105/D-110 bundle on every request.
Request/CAS/context evidence binds delivery; missing/replaced/tampered inputs or retrieval events fail closed. This is
delivery, not retrieval, and grants no selective authority or provider/evaluator activity during construction.

## 9. Outcome and reporting

Primary task success is:

```python
hidden_pass and regression_pass and scope_pass and safety_pass
```

Evaluator-v1 safety is literal PASS. V2 binds four typed controls, aggregates
`ERROR > FAIL > NOT_RUN > PASS`, and receipt-gates persistence/qualification; raw results remain unofficial.
V5-V25 retain their exact historical observations in `docs/09-evidence.md`.

Fast preflight permits at most three no-call attempts with new attempt IDs; semantic changes require a new version.
Incomplete matrices, including R3, are diagnostic only.

## 10. Cost and completion gates

Cost is reserved before provider dispatch, settled from durable usage in integer nano-USD and reloaded before the
next paid row. Completion requires every exact row once, qualified trace, settlement and evaluator/verdict
consistency; missing, duplicate, retried, replaced or confounded rows are inconclusive. R8's immutable v1/v2 adapter
mismatch is corrected only by its append-only index. Exact historical caps and local durability limits are in
`docs/09-evidence.md`.

## 11. Evidence gates

Preparation, execution receipt, journal and completion remain distinct. No historical identity or approval can be
reused; future execution needs a new qualified suite/source, exact candidate and approval. D-126-D-141 never reopen,
D-142 remains source-qualified/unactivated/deferred, and exact tuples remain in `docs/09-evidence.md`.
