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

The **successor A/C offline qualification** is `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`. V5/V7/V12 are immutable
ERROR terminals. V13 consumed `BLOCKED(docker_not_ready)` before `.env`/SDK. V14 at `e63f418` passed eight Docker
reads and returned one child without a framed envelope, then consumed
`ERROR(child_checker_error/framed_output_invalid)`. Its recorded forbidden counts are 0, but whole-terminal accounting
is incomplete, unknown post-marker activity is true and retry/resume is closed.

Source-only v15 commit/tree `e962291bfea66980a66c7592e87ce5277b43b30a`/
`082840944a46b2fc8d3b9f2df8afcc5d04b759ee` replaces fd 1/2 restoration with a result descriptor duplicated before
the workload. Contract `ncpcontract_ac6959d19db4d7a11ce199a32bde188fbfd515c7bdfcee9241d10ac164800f01` is
qualified at `ac32e78` as `sha256:0cdf9e0bb8ea981e7360bd7acd456c3b8aebfc6cf719aa2527e828ab7dc2f494` after 8/8
offline tests, including an actual Windows subprocess. It made no external observation and has no state, approval,
attempt, terminal, live default observer or execution authority.

## Current roadmap

1. **Evaluator correctness v2.** Typed evidence, fail-closed aggregation and receipt-gated integration are local.
2. **Successor A/C qualification.** New source/runtime/suite identities are local; D-142/R2 remain predecessors.
3. **Offline preflight contracts.** V1-v14 are immutable; v15 is source-qualified only.
4. **Separately approved preflight attempt.** No activation wrapper, state, approval or attempt exists for v15.
5. **Candidate and cost gate.** After READY, bind pricing/reserve/cap/hash/candidate, then obtain paid approval.
6. **Readiness panel.** The four-run A/C readiness runs Moto A/C and Babel C/A once; confounding is inconclusive.
7. **Held-out A/C.** After valid readiness, preregister 12 tasks × A/C × at least two repetitions (48+ rows).
8. **Selective/full comparison.** B/D require frozen leakage/redaction/calibration or a fresh held-out panel.

No official/live evaluator result exists. V7, v12 and v14 are consumed ERROR; v15 is not readiness evidence.

## Consumed boundaries

D-129-D-141 are immutable consumed predecessors. Deferred D-121 candidate
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` was never authorized.

## Closed authority

V5/v7/v12/v13/v14 are consumed. V15 qualification opens no Docker/`.env`/SDK, cost or A/C execution.

## Next gate

No execution gate is open. The next implementation boundary is a new versioned state/activation wrapper around v15;
only its later exact state and approval could open one attempt. Current artifacts grant none. Docker provisioning,
candidate, cost and paid execution remain closed.

D-142 activation is not the next gate. Do not create its receipt, attempt, marker or terminal from this roadmap.
