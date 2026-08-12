# Current status — 2026-08-12

## Current checkpoint

D-142 gate `d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914` and source
`1370cf43c08cefb550b158a5d4172a60ac172470` remain D-141's exact four-file sole child; `docs/09-evidence.md` owns
the tuple. Evidence stays **source-qualified only, unactivated** after 170/170 mocked tests, with no runtime artifact
or observation. Its planning disposition is now **deferred**; it is unchanged/unconsumed and cannot qualify v2 A/C.

## Evaluator correctness gap

Success requires hidden acceptance AND regression AND scope AND safety, but evaluator-v1 assigns literal safety
PASS. Historical results remain immutable and are not independently safety-verified. V2's offline successor-only integration path
binds typed event/CAS evidence and uses an authority receipt to gate runner, persistence, qualification and completion; raw
results remain `official=false` and local/mock tests are not official evidence.

The **successor A/C offline qualification** is `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`. V5 consumed
`ERROR(checker_error)`. V7 then consumed one exact-approved attempt: Docker READY after 8 reads, exact key
declared/nonempty, one child launch, then `ERROR(sdk_diagnostic_error)` with child code
`diagnostic_runtime_import_error`. Accounting is complete, unknown activity is false and retry/resume is closed.
V8 localizes the import failure to missing `SYSTEMROOT`/Windows 10106. V9 source-qualifies the corrected parent.
V10 source `3190923f97883e7df4bb53b9b8231c3598239fb1` binds that runtime to contract
`ncpcontract_5365b5b57ad61a691232efb73c930656338e5137ba10fa80d4788c6b2c782539` and qualification
`sha256:e9e8d7425b300ad109ba38ceeda08e8e897cf596c03d381771351792eb761a6e`. Exact user statement binding created
state `ncpstate_cf5f91ae06c6c49dc988ec217a535301b5162208ed227186cb76b15be572abe5` at `5ab4226bfc5017563b673375f9057fde39b1c38c`.
It is self-attested non-proof: Docker/key readiness is unverified and observation/mutation is 0. V11 source
`e1524fbdcffcfc2da04aefdf940cf79d32c71d9d` binds it and exact v9 runtime to contract
`ncpcontract_56b40355ec3805cb987bde6d3f45d7135160336b477186a7e7519bdb55f5285f`, qualification
`sha256:61258adc944956893bde753065e5ec33cd15ee222235b484aba4938e0facadbe`. No approval/attempt exists.

## Current roadmap

1. **Evaluator correctness v2.** Typed evidence, fail-closed aggregation and receipt-gated integration are local.
2. **Successor A/C qualification.** New source/runtime/suite identities are local; D-142/R2 remain predecessors.
3. **Offline preflight contracts.** V1-v10 are predecessors; v11 approval source is qualified, approval absent.
4. **Separately approved preflight attempt.** V3/v5/v7 are consumed and cannot retry.
5. **Candidate and cost gate.** After READY, bind pricing/reserve/cap/hash/candidate, then obtain paid approval.
6. **Readiness panel.** The four-run A/C readiness runs Moto A/C and Babel C/A once; confounding is inconclusive.
7. **Held-out A/C.** After valid readiness, preregister 12 tasks × A/C × at least two repetitions (48+ rows).
8. **Selective/full comparison.** B/D require frozen leakage/redaction/calibration or a fresh held-out panel.

No official/live evaluator result exists. V7 is consumed ERROR, not readiness evidence.

## Consumed boundaries

D-129-D-141 are immutable consumed predecessors. Deferred D-121 candidate
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` was never authorized.

## Closed authority

V5/v7 are consumed. V11 qualification grants no Docker, SDK/`.env`, provider/evaluator/agent, cost or A/C authority.

## Next gate

The next gate is a **fresh exact v11 user approval and binding**, not an attempt. Only the fixed statement from
`--show-approval-template`, citing the exact v11 contract/qualification and v10 state, may create one append-only
`ncpapprovalreceipt_*`/`ncpapproval_*` pair. It starts no attempt; the next source gate is a qualified attempt-lifecycle
successor. Generic continuation and prior approvals are insufficient.

D-142 activation is not the next gate. Do not create its receipt, attempt, marker or terminal from this roadmap.
