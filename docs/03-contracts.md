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

Each audited task contains:

- `public.yaml`: repository identity, issue, constraints and registered visible checks;
- `private.yaml`: hidden acceptance and verifier-only configuration;
- `reference.patch`: evaluator/admission evidence only;
- audit evidence binding source, base state, reference and known-bad behavior.

Dataset role is owned by `data/dataset-manifest.yaml`, not inferred from directory names or current results.
Held-out task content may not be used to tune prompt, memory, score policy or selection.

## 3. Experiment inputs

Executable experiment suites use `ExperimentSuite` in `patchloop/evals/runner.py`. A live suite must bind its
purpose, ordered tasks/conditions/repetitions, model tuple, budget, pricing, dataset manifest and execution
hash.

The A/C sources have distinct roles:

- `experiments/ac-structured-pilot-v2.plan.yaml` is the non-executable R2 design record inherited by D-125.
- `experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml` is the exact experiment-v2 source
  for purpose `development-validation-ac-readiness` and binds the R2 cost control.
- Its schedule is Moto A, Moto C, Babel C, Babel A, each once, under `fixed-d110-bundle-v1`.
- It has `approved_execution_hash=null`, `live_cost_approved=false` and no fresh pricing timestamp.

The D-122 R1 plan/suite remain sealed predecessor bytes and are validated only in sealed-historical mode.

The runner accepts only the exact suite purpose/profile and fixed schedule. Neither the plan nor an accepted
suite grants provider, evaluator, Docker, runtime-memory or cost authority.

## 4. Run manifest

Every run binds:

- task, repository commit and evaluator image;
- prompt/tool/context-policy versions;
- model/reasoning/service/transport tuple;
- memory condition and token allowance;
- model/tool/token/wall limits;
- fault policy, schedule row and experiment identity;
- pricing and usage-accounting contract.

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

`fixed-d110-bundle-v1` provides strict `FixedMemoryDeliveryEvidence` and
`FixedMemoryRequestEvidence` contracts:

- A binds no index and renders `selected_memory=null` with zero entries and zero bundle bytes;
- C binds the D-105 gate/render set and D-110 index/marker/gate, then renders the exact ordered 3,528-byte
  bundle on every request;
- the model-request artifact binds the delivery hash, request hash and normalized no-memory request hash;
- replay validation recomputes the actual `selected_memory` byte identity, request normalization and
  `ContextBuilt` binding;
- the existing `ContextBuilt` payload summarizes the same evidence; no new event or `MemoryRetrieved` event is
  emitted;
- missing, linked, replaced or hash-mismatched bound inputs fail closed;
- bundle construction performs no query, embedding, ranking, threshold, retrieval, model, provider or
  evaluator activity.

This is delivery, not retrieval. It does not mutate D-110 or set selective-retrieval authority true.

The A/C qualifier reconstructs delivery from the model-request artifact, CAS bytes, `ContextBuilt` summary
and consumer request-artifact hash. Its A/C checks include `fixed_memory_delivery_integrity`,
`ac_fixed_runtime_contract`, `disabled_call_guard_contract` and `pricing_start_freshness`; the legacy inverse
retains `no_memory_boundary`. A `MemoryRetrieved` event, consumer reuse, mismatched artifact role, provider
state use or byte/hash tamper fails closed.

## 9. Outcome and reporting

Primary task success is:

```python
hidden_pass and regression_pass and scope_pass and safety_pass
```

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

D-126 consumes only clean-source/pricing/no-call scope, binding commit
`68b7c8b0779a33443a4a4e5ae423e3c64e0e1d22`, fresh rates, 12 Docker reads (six daemon/image, zero workload)
and an SDK construction probe with zero network calls.

D-126 has five environment blockers plus a provenance gap: no raw official bytes independently rebind its
recorded digest/size/ETag. It creates no hash/candidate/live authority or cost.

D-127 requires committed receipt/clean identity, the official URL with `trust_env=False`, bounded
replayable pricing, exact-image Docker scope and attempt-first append-only phases. Missing API key or unverified
daemon auto-restart state fails closed. Static stopped on the missing key; only the receipt exists, while
container work, hash/candidate/live authority remain forbidden.
