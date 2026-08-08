# Current status — 2026-08-09

## Evidence checkpoint

The latest sealed checkpoint is D-126 clean-source/pricing/no-call preflight evidence:

- Gate ID `d126_d2ab27d34a7b56e51ba21d1d6274707b13e8345de6feb3bc9719d047ca834c4d`;
  body `sha256:d2ab27d34a7b56e51ba21d1d6274707b13e8345de6feb3bc9719d047ca834c4d`;
  file `sha256:e08e8f7aad8f425c7069290a98ac04a5c471bc8c948e1a08121c962b5ba18696`; 3,078 bytes.
- Bound receipt ID `d126approval_596fd109a08fefbfc7e3075fd89879015ef5c78c5caa72353c45bf3ccbec2ae0`
  and preflight ID `d126preflight_c1412f3daa396daed456b92ffc84360afcd68780fd281fc99efc0d067b6fed04`;
  their exact body/file/byte triples are indexed in `docs/09-evidence.md`.
- Status: `D126_CLEAN_SOURCE_PRICING_NO_CALL_PREFLIGHT_OBSERVED_BLOCKED`.

D-126 seals source commit `68b7c8b0779a33443a4a4e5ae423e3c64e0e1d22` and one unauthenticated
official-doc GET observed within 72 hours. The dated model is `gpt-5.4-mini-2026-03-17`; text-token list
prices are $0.75 input, $0.075 cached input and $4.50 output per 1M tokens. The conservative planning values
remain $13.6125 per row, $54.45 for four rows and a proposed, unapproved $55 cap.

Those facts/math were correct and fresh at capture, but raw official response bytes were not retained, so the
validator cannot independently rebind the recorded body SHA/bytes/ETag. A successor must close this pricing
provenance replayability gap before hash/candidate gating.

The no-call environment observation issued 12 Docker commands across stable before/after snapshots: six
configuration reads, six read-only daemon/image inspections and zero workload or mutating calls. The local
SDK construction probe used OpenAI 2.47.0 matching the lock, the official endpoint and zero network calls.
Execution-hash readiness is false because exactly five blockers remain:

- `docker-cli-observed-identity-awaits-separate-exact-approval`
- `docker-local-daemon-and-exact-images-readiness-failed`
- `openai-api-key-presence-missing`
- `production-openai-client-official-base-url-not-explicit`
- `production-openai-client-trust-env-not-disabled`

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

- D-098 seals the baseline; D-105/D-110 seal three rules/index; D-108 measured a +702-token bundle delta.
- `fixed-d110-bundle-v1` renders A null and C the exact 3,528-byte bundle without retrieval. Exact
  manifest/request/CAS/context/consumer provenance is replay-validated.
- R2 requires an up-front four-row reserve, durable usage settlement and a bijective qualified/evaluated
  four-row completion matrix; missing or unsettled rows are inconclusive.
- D-124/D-125 are sealed-historical settlement/finalization predecessors with local/mock limits.
- D-126 seals the clean tracked source identity, fresh official pricing and bounded no-call environment
  observations. It completed the approved observations but did not establish environment readiness.

Qualification excludes cross-store/global/cross-clone protection, whole-root rollback, noncooperative path
swap, actual kill and torn-write/power-loss durability. The plan and suite keep all live authority false.

## What is not ready

- Resolution of all five D-126 environment blockers and pricing-provenance replayability under separate approval
- A repeated, separately authorized no-call preflight after those corrections
- Exact runner execution hash and one-use execution-authorization candidate under a later approval
- Separate approval repeating the exact candidate triple, execution hash and $55 cap
- Any live A/C result

The planning values were not reserved, spent or approved. The legacy embedding/ranking retrieval path remains
unauthorized for fixed-bundle C.

## Closed lanes

Provider/evaluator execution, runtime injection/retrieval, score-policy mutation, raw trace, held-out/core,
D-121 successor execution and applicability-classifier calls remain closed.

D-126 provider/evaluator calls, agent runs, retrievals, injections and cost are zero. Its only public network
activity was the official pricing GET; its Docker activity was read-only observation with zero workloads.
Runtime memory injection remains unauthorized.

## Historical/deferred D-121 lane

D-121 candidate `d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`
remains deferred; its run was never authorized and is not a fixed-bundle prerequisite.

## Next gate

A separate approval may resolve all five recorded blockers, close pricing-provenance replayability and repeat
the exact no-call preflight only. It must not create an execution hash, candidate or live run. If a successor
preflight is ready, another separate exact-gate approval is required before hash/candidate preparation, followed by exact
candidate-triple/execution-hash/$55-cap approval before any live execution.
