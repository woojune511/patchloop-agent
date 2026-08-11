# Current status — 2026-08-12

## Current checkpoint

D-142 remains the exact D-141 SDK-BLOCKED no-call successor gate
`d142_9515aeb4c7289fa26987ec605917c395e54b27d076cd226c266acd2a3cb82914`. Source commit
`1370cf43c08cefb550b158a5d4172a60ac172470` is D-141's exact four-file sole child; `docs/09-evidence.md`
owns the file, tree, parent and evidence-commit tuple.

Its evidence state is unchanged: **source-qualified only, unactivated**. Mocked tests passed 170/170; no receipt,
attempt, ACTION_STARTED or terminal exists, and preparation made no environment/SDK/Docker/external observation.

Its planning disposition is now **deferred**. This does not consume, invalidate, repair or rewrite D-142; it
removes activation from the current critical path. A future decision could still cite the exact tuple for the
original one-use SDK observation, but that observation would not qualify a corrected evaluator or a new A/C
experiment source.

## Evaluator correctness gap

The normative success contract is hidden acceptance AND regression AND scope AND safety. The current
`EvaluationEngine` instead assigns `safety_state = VerdictState.PASS` without running an independent safety
check. Therefore evaluator-v1 results do not establish that safety was measured, and a new paid A/C row must
not be called four-verdict SCRR evidence under that implementation.

Historical artifacts, including D-098, remain immutable evaluator-v1 observations and are not regraded. Claims
using them must state that the safety component was unconditional rather than independently verified.

Evaluator-v2 now has an offline successor-only integration path. With a separately supplied exact authority,
the standard runner derives typed verdicts from the durable accepted-event prefix and CAS, writes an append-only
receipt, and permits completed persistence only when that receipt revalidates. Qualification and A/C completion
consume the same binding while the raw result remains `official=false`. Local mock/requested-policy tests are not
a qualified source, Docker-enforcement result or official run.

The **successor A/C offline qualification** is `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`. Preflight v1/v2 remain
predecessors. Executable v3 `ce0628880107db2319816272cfa49adc7ea99667` confines `.env` bytes to a child, returns
exact-key membership only and uses fixed-placeholder reject-dispatch SDK validation.

## Current roadmap

1. **Evaluator correctness v2.** Contract, typed producer, standard-runner selection, receipt-bound persistence,
   qualification and completion enforcement are implemented and regression-tested locally.
2. **Successor A/C qualification.** New source, runtime and successor-suite identities are materialized and
   locally validated; D-142 and R2 remain immutable predecessors.
3. **Offline preflight contracts.** V1/v2 are preserved; executable v3 source and a fresh self-attested state are
   qualified without reading `.env` or observing credentials.
4. **Separately approved preflight attempt.** A later message must cite the exact v3 contract, source qualification
   and state. Approval authorizes one Docker/isolated-child/SDK no-call attempt; terminal means no retry.
5. **Candidate and cost gate.** After READY, refresh pricing, bind reservation/cap, create the execution hash and
   candidate, then obtain separate exact paid approval. None is implied by preflight.
6. **Readiness panel.** The four-run A/C readiness runs Moto A/C and Babel C/A exactly once after the source is
   qualified. An incomplete or confounded panel is preserved as inconclusive, without row replacement.
7. **Held-out A/C.** If readiness is valid, preregister the frozen 12-task core panel under A/C with at least two
   repetitions (planning target: 48 rows) before unblinding any held-out result.
8. **Selective/full comparison.** Return B/raw-trace and D/selective to the critical path only after their
   leakage, redaction and independent public-development calibration contracts are frozen. If they are designed
   after A/C unblinding, use a separate fresh held-out panel.

No official/live evaluator result, approval, attempt or external observation exists. V2/v3 self-attested states are
unconsumed and are not independent presence evidence.

## Consumed boundaries

D-129 through D-141 remain immutable consumed predecessors; `docs/09-evidence.md` owns their exact tuples and
zero-activity limits. The deferred D-121 candidate
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` was never
authorized and is not a fixed-bundle prerequisite.

## Closed authority

Credential placement is user-reported only. Provider/evaluator/agent calls, memory/retrieval, Docker/SDK/`.env`
observation, execution hash/candidate, cost reservation and A/C execution remain unauthorized and absent.

## Next gate

The next gate is **exact approval**, not observation yet. It must cite contract
`ncpcontract_6e7fa7dac02b594d9f16c84b4d3036632a6f6a2214cd7cf8cbab7b559bd55f9d`, qualification
`sha256:385ac8521f86a4572bb9614af4c5730bb9856e63be3445ddb27521b492bd8079` and state
`ncpstate_105d0becd0a33fe453e6be83044b239263eb855c165da6f275d9e4591e54f317` and reconfirm placement. It permits one
bounded no-call attempt only; no value, network/provider call, candidate or cost authority.

D-142 activation is not the next gate. Do not create its receipt, attempt, marker or terminal from this roadmap.
