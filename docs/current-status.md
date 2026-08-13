# Current status — 2026-08-13

## Current checkpoint

V25 is source-qualified/approval-bound/immediate-run-required. Contract
`ncpcontract_c87b73d0a559f1585c4c40a495d1d5718ac89cd72aae935320023b7f4bbbca1f`, qualification
`sha256:d24b7a9849e0c632c05ef09ad9e9f7886bdf121a8b168d55e7040e8c2c732ff8`, self-attested state
`ncpstate_ac6bba89eaa69ecfda433cc0775bff2308e0e95eea1ac3baa2bc47368531dae2` and nonreusable approval
`ncpapproval_eb438ff9b25f404a88e93d3e6462a4d7c70331b94d3c9e617ec802d98f896919` are bound. Qualification observed
nothing external; `attempt_started=false` and authorization/attempt/terminal are absent. `docs/09-evidence.md` owns
exact commits, source/tree and file tuples.

D-142 remains **source-qualified only, unactivated** after 170/170 mocked tests, with no runtime observation. Its
planning disposition is now **deferred**; the unchanged tuple in `docs/09-evidence.md` cannot qualify v2 A/C.

## Evaluator correctness gap

Evaluator-v1 assigns literal safety PASS, so historical results are not independently safety-verified. V2's
offline successor-only integration path receipt-gates typed evidence, persistence and qualification; raw results remain
`official=false` and local/mock tests are not official evidence.

The **successor A/C offline qualification** is `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`; predecessor tuples are in
`docs/09-evidence.md`.

## Current roadmap

1. **Evaluator correctness v2.** Typed evidence, fail-closed aggregation and receipt-gated integration are local.
2. **Successor A/C qualification.** New source/runtime/suite identities are local; D-142/R2 remain predecessors.
3. **Offline preflight contracts.** V1-v24 are immutable; v25 source is qualified and state-bound.
4. **Separately approved preflight attempt.** Approval is bound; require the separate immediate run text.
5. **Candidate and cost gate.** After READY, bind pricing/reserve/cap/hash/candidate, then obtain paid approval.
6. **Readiness panel.** The four-run A/C readiness runs Moto A/C and Babel C/A once; confounding is inconclusive.
7. **Held-out A/C.** After valid readiness, preregister 12 tasks × A/C × at least two repetitions (48+ rows).
8. **Selective/full comparison.** B/D require frozen leakage/redaction/calibration or a fresh held-out panel.

No official/live evaluator result exists. V7/v12/v14/v16/v18/v20/v23 are consumed ERROR and not readiness evidence.

## Consumed boundaries

D-129-D-141 are immutable consumed predecessors. Deferred D-121 candidate
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` was never authorized.

## Closed authority

V5/v7/v12/v13/v14/v16/v18/v20/v23 are consumed and cannot retry. V25 execution, cost and A/C remain closed.

## Next gate

No attempt is open. State/approval grant no observation by themselves. The next action is the exact immediate run
statement; without it no authorization, attempt, execution, candidate or cost authority exists.

D-142 activation is not the next gate. Do not create its receipt, attempt, marker or terminal from this roadmap.
