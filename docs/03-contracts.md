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
- `heldout-ac-suite-20260814-v1.yaml` and its plan: strict metadata-only 48-row contracts that are not
  `ExperimentSuite` and have no live-runner route;
- held-out R2/R5 source gates: R2 validates suite/fixture analysis; R5 replays that closure and binds the 12-task
  metadata plan plus hardened evaluator-v2 materialization and receipt/trace-backed persisted-row authentication
  source. R3/R4 are superseded predecessors; actual bindings stay 0;
- `ac-structured-pilot-v11.plan.yaml`: R10-qualified contract-hardened split-budget design used by sealed R8;
- `dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml`: consumed Moto/Babel A/C suite whose four rows all
  resolved, evaluator-v2 receipt-qualified and cost-settled; R7/R9 remains superseded unexecuted;
- R6/R8 and R5/R7: immutable post-evaluator qualification failures; R4/R6-qualification: immutable
  provider-before-dispatch `$0` terminal;
  R3/R5-source-qualification: immutable partial live predecessor.

R1/R2 plans, suites and runtime seals remain immutable predecessors.

An accepted plan/suite grants no provider, evaluator, Docker, runtime-memory or cost authority.

Held-out fixtures never impersonate runtime schemas and emit `official=false`, `analysis_ready=false`. R5 source can
later validate durable result/qualification/receipt/usage bytes, but authority requires materialized task bindings,
authenticated rows and a fresh candidate.

## 4. Run manifest

Every run binds task/source/image, prompt/tool/policy, model/service/transport, memory, limits, fault/schedule
identity and pricing/accounting.

A and C manifests differ only in the memory condition and evidence derived from it. A must bind no index; C
must bind the D-110 index and `fixed-d110-bundle-v1`. The manifest/preflight matcher rejects a legacy
`latest_frozen_index` serialization, suite tamper, wrong profile, source drift or schedule drift. Both
conditions retain the identical runtime tuple and resource ceilings.

Exact R3/R8 runtime and budget tuples are immutable in `docs/09-evidence.md`.

## 5. Event and checkpoint contracts

Events carry stable run ID, monotonic sequence, timestamp, actor, type, payload and artifact hashes. Durable
model usage is written before a malformed response can terminate the run. Checkpoints bind current phase,
workspace/diff identity and completed action IDs.

Observed events are never edited. Corrections are successor artifacts or events that explicitly reference the
original evidence.

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

A memory entry contains a generalized failure pattern, applicability, remediation, non-applicability,
validation evidence and provenance. Only the approved D-105 `model_facing_text` is eligible for the fixed C
bundle; source run IDs, raw traces, vectors and reviewer-only fields must not enter the model context.

The D-110 frozen index is an immutable storage artifact, not runtime authority. Its current authority says
`retrieval_ready=false` and `retrieval_experiment_authorized=false`.

## 8. Fixed-bundle C delivery contract

`fixed-d110-bundle-v1` provides strict delivery/request evidence:

- A binds no index and renders `selected_memory=null` with zero entries and zero bundle bytes;
- C binds D-105/D-110 inputs and renders the exact ordered 3,528-byte bundle on every request;
- model-request/CAS/`ContextBuilt` evidence binds delivery and normalized A identity; no retrieval event is emitted;
- missing, linked, replaced or hash-mismatched bound inputs fail closed;
- construction performs no retrieval/ranking/model/provider/evaluator activity.

This is delivery, not retrieval. It does not mutate D-110 or set selective-retrieval authority true.

The A/C qualifier reconstructs the same chain and fails closed on retrieval events, consumer reuse, wrong
roles, provider-state use or byte/hash tamper.

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
