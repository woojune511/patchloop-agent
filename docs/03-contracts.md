# Data and tool contracts

상태: current contract map. Pydantic models, exact JSON artifacts and tests are authoritative. The cumulative
D-001–D-121 prose is preserved at `docs/archive/snapshots/d121/03-contracts.full.md`.

## 1. Cross-cutting rules

- JSON/YAML input uses strict schemas and rejects unknown fields where the owning model is strict.
- IDs derive from canonical content; mutable observations also carry file SHA-256 and byte size.
- UTC timestamps and nondecreasing chronology are required where ordering is material.
- Evidence writers use new-only/append-only semantics; partial states fail closed.
- Public and private task material use separate files and loaders.
- Runtime authority must be explicit; preparation and validation are not execution.

## 2. Task package

Each audited task separates public issue/check inputs from private acceptance, reference patch and audit
evidence. `data/dataset-manifest.yaml` owns dataset role.

Held-out task content may not be used to tune prompt, memory, score policy or selection.

## 3. Experiment inputs

`ExperimentSuite` binds purpose, ordered rows, runtime tuple, budget, pricing, dataset and execution hash.
Current A/C sources are:

- `ac-structured-pilot-v2.plan.yaml`: non-executable R2 design;
- `dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml`: exact Moto A/C, Babel C/A suite using
  `fixed-d110-bundle-v1`, with null execution hash and live-cost authority false.

The D-122 R1 plan/suite remain sealed predecessor bytes and are validated only in sealed-historical mode.

An accepted plan/suite grants no provider, evaluator, Docker, runtime-memory or cost authority.

## 4. Run manifest

Every run binds task/source/image, prompt/tool/policy, model/service/transport, memory, limits, fault/schedule
identity and pricing/accounting.

A and C manifests differ only in the memory condition and evidence derived from it. A must bind no index; C
must bind the D-110 index and `fixed-d110-bundle-v1`. The manifest/preflight matcher rejects a legacy
`latest_frozen_index` serialization, suite tamper, wrong profile, source drift or schedule drift. Both
conditions retain the identical runtime tuple and resource ceilings.

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
- C binds the D-105 gate/render set and D-110 index/marker/gate, then renders the exact ordered 3,528-byte
  bundle on every request;
- model-request/CAS/`ContextBuilt` evidence binds and replays delivery, request and normalized A identity;
- no new or `MemoryRetrieved` event is emitted;
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

Evaluator-v1 safety is literal PASS. V2 binds four controls to fixed producers and opaque private-ID projections,
aggregates `ERROR > FAIL > NOT_RUN > PASS`, and validates accepted events, CAS and sanitized requested policy.
Its receipt binds authority, event boundaries, patch and inventory; persistence/qualification require it and raw
results remain unofficial.

The A/C successor hashes source, runtime, treatment and schedule. Preflight v1-v4 remain predecessors. V5 bound v4,
approval, read-only Docker and the isolated child, then terminated checker-error after ACTION_STARTED. Its incomplete
accounting is immutable; any future version needs new source/state/approval identities, never a v5 retry.

Experiment reports retain every scheduled row, including agent/infrastructure failures and not-started rows.
Incomplete matrices are diagnostic only. A four-row readiness result cannot be promoted to a core memory
effect claim.

## 10. Cost and completion gates

D-123 binds $13.6125 per row, $54.45 full-schedule reserve and proposed $55 cap. Before any provider call the
journal records campaign/reserve events; each row records start, terminal and settled-or-inconclusive events.
Usage is repriced in integer nano-USD and prior settlements reload before another paid call.

Completion requires each exact row once, qualified trace, durable settlement, official evaluation and
resolved/SCRR/verdict consistency. Missing, duplicate, retried, replaced or confounded rows are inconclusive.

D-124 corrects settlement reconciliation. D-125 adds local SQLite row consumption plus marker and fsynced,
no-replace result publication with mocked idempotent recovery. It does not prove global/cross-clone,
noncooperative-swap, actual-kill or power-loss guarantees. No reservation/result executed.

## 11. Evidence gates

Preparation, execution receipt, journal, completion gate and successor correction are distinct artifacts.
An exact approval applies only to the action named by the approved candidate. Historical exact schemas and
instance bindings remain available in the archived contract ledger and machine artifacts under `reports/`.

D-126 through D-141 are immutable predecessors and consumed attempts never reopen. D-142's exact tuples and
original one-use contract remain canonical in `reports/` and `docs/09-evidence.md`; its evidence state is
source-qualified and unactivated, while its current planning disposition is deferred. Documentation creates no
D-142 receipt, attempt, marker or terminal. A future return to that original observation requires a new exact
decision, and any corrected-evaluator A/C path instead requires new evaluator, source, suite and runtime identities.
