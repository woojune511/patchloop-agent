# Current status — 2026-08-09

## Evidence checkpoint

The latest sealed checkpoint is the D-125 offline A/C runtime-finalization source gate:

- Gate ID: `d125_ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539`
- Semantic body SHA: `sha256:ed9c892a598ce4543591bf3b9135a1cbe3752589fdc447b05867d59e07d45539`
- File SHA: `sha256:9bc5f6e618f31312dc5026a807eabf478e47c05893cca72c71328378b593856e`
- File bytes: `13820`
- Status: `D125_AC_RUNTIME_FINALIZATION_SOURCE_QUALIFIED_EXECUTION_CANDIDATE_BLOCKED`

This gate seals source-path evidence only. No reservation was executed, no result exists, and no one-use
candidate or approved execution hash was created.

## Current priority: four-run A/C readiness

The project now defers the full four-condition campaign and starts with a smaller readiness question:

> Can the exact approved structured bundle be injected through the complete agent workflow without
> leakage or runtime ambiguity, while keeping every non-memory input identical to no-memory?

The design plan is `experiments/ac-structured-pilot-v2.plan.yaml`; the exact suite is
`experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml`:

- Tasks: Moto #7208 and Babel #1042 development-validation fixtures
- Conditions: A `no_memory`, C `structured`
- Repetitions: one
- Rows: four, counterbalanced as Moto A→C and Babel C→A
- C payload: all three approved D-105 model-facing rules in frozen D-110 `group_provenance` order
- C selection: no query embedding, similarity, rerank or threshold
- Runtime tuple: dated gpt-5.4-mini, medium/standard/default, tool v2, phase-evidence-v5,
  3,000,000 total tokens and 3,600 seconds
- Suite ID: `dev-validation-ac-fixed-bundle-readiness-20260808-r2`
- Exact order: Moto A, Moto C, Babel C, Babel A

This is a runtime/readiness panel, not a held-out efficacy experiment. It cannot establish general memory
benefit, statistical significance, negative-transfer rate, individual-rule efficacy or retrieval quality.

## What is implemented and qualified offline

- D-098 seals the baseline; D-105/D-110 seal three leak-scanned rules and their index. D-108 measured a
  702-token full-bundle delta against the 2,000-token allowance.
- `fixed-d110-bundle-v1` renders A null and C the exact 3,528-byte bundle on every request without retrieval,
  embedding, ranking, threshold or a new event type.
- Condition-specific manifests and request/CAS/`ContextBuilt`/consumer provenance are replay-validated against
  the exact suite and runtime contract.
- The R2 source atomically plans an up-front four-row reserve, durable usage-derived settlement, exact event
  keysets/chronology and settlement-unavailable inconclusive sealing.
- The completion source requires a bijective four-row terminal matrix, durable settlement, trace/leak pass,
  official evaluation and resolved/SCRR/four-verdict consistency.
- D-124 is preserved and validated sealed-historical. D-125 adds SQLite-backed repository-local at-most-once
  row consumption before paid execution and fail-closed marker binding.
- D-125 also publishes an fsynced prepared result before `CampaignCompleted` and recovers three mocked process
  fault boundaries idempotently without rerunning rows.
- D-125 gate tests passed 23/23; D-124+D-125 passed 37/37. Row attestation 147 and finalization union 136 are
  overlapping evidence and are never added. These are not live or repository-wide results.

Qualification excludes cross-store/global/cross-clone protection, whole-root rollback, noncooperative path
swap, actual kill and torn-write/power-loss durability. The plan and suite keep all live authority false.

## What is not ready

- Clean committed source sealing and fresh official pricing within 72 hours
- Separately authorized no-call Docker/SDK/credential/endpoint preflight
- Exact runner execution hash and one-use execution-authorization candidate
- Separate approval repeating the exact candidate triple, execution hash and $55 cap
- Any live A/C result

The source contract records $13.6125 per row, $54.45 for the full schedule and a proposed $55.00 hard cap
with $0.55 slack. Those values were not reserved, spent or approved for live use. The existing retrieval path
must not be reused for C: it loads/scores embeddings, uses legacy rendering and remains unauthorized.

## Closed lanes

- Provider/evaluator execution for the A/C panel
- Runtime memory injection
- Selective retrieval and score-policy mutation
- Raw-trace condition
- Held-out/core campaign
- D-121 successor execution
- Agent/provider/evaluator calls associated with the public applicability classifier

Provider calls, evaluator calls, agent runs, Docker calls and retrieval calls made by D-125 are all zero;
added model cost is $0. Runtime memory injection remains unauthorized.

## Historical/deferred D-121 lane

D-121's no-start successor candidate remains deferred:
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`.
Its actual successor was never authorized, and D-119 is not retried, resumed or repaired. D-121 is not a
prerequisite for this fixed-bundle panel.

## Next gate

A separate approval must repeat the exact D-125 gate/body/file tuple and may authorize only clean committed
source sealing, fresh official pricing lookup and a no-call Docker/SDK/credential/endpoint preflight. It must
not create an execution hash or candidate. Those require a later separate gate, followed by exact
candidate-triple/execution-hash/$55-cap approval before any live execution.
