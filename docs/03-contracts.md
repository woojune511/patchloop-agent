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

D-126 through D-131 are immutable predecessors; consumed gates never reopen. D-132 committed a pricing attempt
and reached action-started without canonical terminal, consuming its activation and attempt. No retry, resume,
repair or backfill is allowed. The incident records one unauthenticated application-level
`client.send` Response return; HTTP request count/completion are unknown, response fields are unretained,
completed/replayable canonical pricing evidence count is 0, its artifact is absent and replay bytes are 0.

D-133 then committed and preserved the exact marker. D-134's gate is preserved by commit
`9dc450a747537634e89fe2ade824685f8b5a52d6`, but its ambiguous numeric GET counter makes its qualification and
terminalization authority invalid. D-135 corrected that boundary and commit
`98f4560e718145bc7465732c1a3d2f5a4ea8d786` contains only its append-only procedural terminal. That terminal
preserves the incident and no-retry facts; it is not canonical pricing evidence.

D-136 gate `d136_aef9768fcc24b48df09034d14aefcd02b1812531fe77bf56ca1601ac4e5e00fd` exact-binds the
D-135 terminal bytes/commit and predecessor-gate topology. Source
`96916ac481ac8beced2db0be9022607e0705e018` introduces a distinct helper that preserves the exact official
URL, unauthenticated request, maximum three redirects, 128,000 decoded-byte bound and replay validation. It
does not rely on `Response.__enter__`; every returned response is closed in `try/finally` on success, redirect
and error paths.

The future append-only activation contract requires:

- a fresh exact approval quoting the D-136 gate tuple, source commit/tree and gate+active-doc
  evidence-commit tuple;
- one receipt-only commit followed by one attempt-only commit;
- a new-only, fsynced action-started marker immediately before the first helper dispatch;
- on success, marker plus replayable pricing terminal as the exact two-artifact transition commit;
- after any post-marker failure, marker-only preservation as the sole child and no retry;
- a later offline successor before Docker/SDK preflight.

No D-136 receipt, attempt, marker, pricing evidence or terminal exists. Gate construction invoked no future
writer or pricing helper; external, runtime, hash/candidate, cost and A/C authority remain false.
