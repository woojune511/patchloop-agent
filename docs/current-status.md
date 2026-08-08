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

D-126 binds source `68b7c8b0779a33443a4a4e5ae423e3c64e0e1d22`, dated gpt-5.4-mini prices
($0.75/$0.075/$4.50 per 1M input/cached/output tokens) and unapproved $13.6125 row/$54.45 schedule/$55 cap
math. Raw official bytes were not retained. Its 12 Docker reads included six daemon/image inspections and zero
workloads; the locked-SDK construction probe made zero network calls. Five blockers keep readiness false:

- `docker-cli-observed-identity-awaits-separate-exact-approval`
- `docker-local-daemon-and-exact-images-readiness-failed`
- `openai-api-key-presence-missing`
- `production-openai-client-official-base-url-not-explicit`
- `production-openai-client-trust-env-not-disabled`

## D-127 approval receipt — no downstream evidence

- ID `d127approval_3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21`;
  body `sha256:3a7b8bd3bd95564e4f3cddf10c154850bcc939371d69931eb78c87f0810b0d21`;
  file `sha256:ddea365e3a51c8283bde58bd349222288a45e8ea8bdb3d211ead0bb001df81f4`; 3,914 bytes.
- Status: `D127_D126_SUCCESSOR_BLOCKER_REMEDIATION_NO_CALL_APPROVAL_RECORDED`.

Source now fixes the official OpenAI base URL and `trust_env=False`, and implements bounded replayable pricing,
exact-identity Docker/read-only preflight and attempt-first append-only orchestration. The receipt is append-only,
but static and downstream artifacts are absent, so D-126 remains latest sealed. Static has
not run and `OPENAI_API_KEY` is absent; daemon launch fails closed while container auto-restart is unverified.
D-127 production Docker/network/provider/
evaluator/agent activity, injection/retrieval, cost, run, hash and candidate are zero or absent.
Dedicated D-127 tests pass 55/55; the broader node-disjoint selection passed 231 with 6 skipped (not additive).

## Current priority: four-run A/C readiness

The project now defers the full four-condition campaign and starts with a smaller readiness question:

> Can the exact approved structured bundle be injected through the complete agent workflow without
> leakage or runtime ambiguity, while keeping every non-memory input identical to no-memory?

Plan `experiments/ac-structured-pilot-v2.plan.yaml` and suite
`experiments/dev-validation-ac-fixed-bundle-readiness-20260808-r2.yaml` fix Moto/Babel × A/C once, ordered
Moto A, Moto C, Babel C, Babel A. C is the exact three-rule D-110 bundle without selection; all rows share the
dated model, medium/standard/default, tool v2, phase-evidence-v5 and 3M-token/3,600-second ceiling.

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
- D-127 implements successor source and records approval; no production path ran.

Qualification excludes cross-store/global/cross-clone protection, whole-root rollback, noncooperative path
swap, actual kill and torn-write/power-loss durability. The plan and suite keep all live authority false.

## What is not ready

- Static admission binding the committed D-127 snapshot and receipt
- A passing static prerequisite check; `OPENAI_API_KEY` is currently missing
- Safe Docker daemon/image readiness without any unauthorized incidental container start
- Replayable official pricing evidence and the repeated no-call preflight
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
D-127 production calls and downstream attempt/remediation/pricing/preflight/gate artifacts are zero.
Runtime memory injection remains unauthorized.

## Historical/deferred D-121 lane

D-121 candidate `d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef`
remains deferred; its run was never authorized and is not a fixed-bundle prerequisite.

## Next gate

First commit the D-127 source and recorded approval receipt, then pass the static prerequisites. The approved
external successor may proceed only through Docker remediation, replayable official pricing capture and the
repeated no-call preflight; a down daemon with unverified container auto-restart state remains blocking rather
than being started. Even a ready D-127 gate cannot create an execution hash, candidate or live run. Those need
a later exact-gate approval, followed by exact candidate-triple/execution-hash/$55-cap approval before live
execution.
