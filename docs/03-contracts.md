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
- `heldout-ac-budget-amendment-20260815-v1.yaml`: development-evidence-only equal-A/C override to
  1M input/100k output/1.1M aggregate and `$57.60`/`$60`; it grants no candidate or execution authority;
- held-out contract R8, binding R9, materialization R5, execution R6 and preflight/dispatcher R14 are the current
  zero-authority chain. R5 reuses R4's 12 opaque task bindings without reopening task packages and retains R1 prices
  without another GET. R14 binds atomic cost/replay contracts and the amended paid boundary;
- `ac-structured-pilot-v11.plan.yaml`: R10-qualified contract-hardened split-budget design used by sealed R8;
- `dev-validation-ac-fixed-bundle-readiness-20260814-r8.yaml`: consumed Moto/Babel A/C suite whose four rows all
  resolved, evaluator-v2 receipt-qualified and cost-settled; R7/R9 remains superseded unexecuted;
- R6/R8 and R5/R7: immutable post-evaluator qualification failures; R4/R6-qualification: immutable
  provider-before-dispatch `$0` terminal;
  R3/R5-source-qualification: immutable partial live predecessor.

R1/R2 plans, suites and runtime seals remain immutable predecessors.

An accepted plan/suite grants no provider, evaluator, Docker, runtime-memory or cost authority.

Held-out fixtures never impersonate runtime schemas and emit `official=false`, `analysis_ready=false`. Templates omit
credential-derived markers and serialize role-prefixed opaque registered-check identities, never raw private control
text. Only the trusted runtime adapter may unlock analysis after 48 exact independently authenticated and settled rows;
dumped, reparsed or copied DTOs cannot carry that provenance. A fresh no-call candidate and paid approval remain
separate gates.

## 4. Run manifest

Every run binds task/source/image, prompt/tool/policy, model/service/transport, memory, limits, fault/schedule
identity and pricing/accounting.

A and C manifests differ only in the memory condition and evidence derived from it. A must bind no index; C
must bind the D-110 index and `fixed-d110-bundle-v1`. The manifest/preflight matcher rejects a legacy
`latest_frozen_index` serialization, suite tamper, wrong profile, source drift or schedule drift. Both
conditions retain the identical runtime tuple and resource ceilings.

Exact R3/R8 development and held-out R7/R11 runtime tuples are immutable in `docs/09-evidence.md`.

## 5. Event and checkpoint contracts

Events bind run/sequence/time/actor/type/payload/artifacts; checkpoints bind phase, workspace/diff and completed
actions. Current held-out writes use canonical run-root-contained paths and atomically append terminal plus cost
evidence. Started usage is persisted before qualification, so a later adapter failure cannot erase observed cost.
Credential/context-entry errors seal as typed confounds. Observations are immutable; corrections explicitly reference
them.

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
`ERROR > FAIL > NOT_RUN > PASS`, and receipt-gates persistence/qualification; raw results remain unofficial. Private
checker-output redactions are evaluator diagnostics, while only agent-visible event/patch marker hits are leakage
verdict inputs. Control-contract collision and untrusted marker escape use distinct stable codes.

Fast preflight permits at most three no-call attempts with new attempt IDs; semantic changes require a new version.
Incomplete matrices, including R3, are diagnostic only.

## 10. Cost and completion gates

Cost is reserved before provider dispatch, observed from durable usage in integer nano-USD before qualification, and
reloaded before the next paid row. Reports separate settled, observed-unsettled and total observed-started cost.
Completion requires every exact row once, runtime-authenticated provenance, settlement and evaluator/verdict
consistency; missing, duplicate, retried, replaced or confounded rows are inconclusive. Persisted replay validates
bytes but cannot mint official analysis authority. Exact historical caps and limits are in `docs/09-evidence.md`.

## 11. Evidence gates

Preparation, execution receipt, journal and completion remain distinct. Full path/price/result/qualification/receipt
bytes are replayed, and the semantic paid-campaign identity excludes transient readiness observations so a timestamp
cannot reopen a consumed plan. R11 is immutable inconclusive; current R14 created no candidate or authority. Future
execution needs a clean committed source, fresh no-call candidate and separate exact approval.
