# Current status — 2026-08-11

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

The **successor A/C offline qualification** is committed at `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`.
Versioned preflight source `4a78745552ef8eab62ddfcdaeb3154de50fe79bf` is its exact four-file sole child;
the append-only qualification records zero external observations and no execution authority.

## Current roadmap

1. **Evaluator correctness v2.** Contract, typed producer, standard-runner selection, receipt-bound persistence,
   qualification and completion enforcement are implemented and regression-tested locally.
2. **Successor A/C qualification.** New source, runtime and successor-suite identities are materialized and
   locally validated; D-142 and R2 remain immutable predecessors.
3. **Offline preflight contract.** Clean-sealed v1 admits only independently trusted value-free credential
   provisioning evidence and binds contract/evidence/approval/ledger identities with one-use terminal behavior.
4. **Separately approved preflight attempt.** Bind `attempt_id` to `contract_version`, a one-use
   `state_change_evidence_id` and exact `approval_id`. Never reuse that evidence, retry/overwrite the attempt or
   infer successor authority from BLOCKED.
5. **Candidate and cost gate.** After READY, refresh pricing, bind reservation/cap, create the execution hash and
   candidate, then obtain separate exact paid approval. None is implied by preflight.
6. **Readiness panel.** The four-run A/C readiness runs Moto A/C and Babel C/A exactly once after the source is
   qualified. An incomplete or confounded panel is preserved as inconclusive, without row replacement.
7. **Held-out A/C.** If readiness is valid, preregister the frozen 12-task core panel under A/C with at least two
   repetitions (planning target: 48 rows) before unblinding any held-out result.
8. **Selective/full comparison.** Return B/raw-trace and D/selective to the critical path only after their
   leakage, redaction and independent public-development calibration contracts are frozen. If they are designed
   after A/C unblinding, use a separate fresh held-out panel.

No official/live v2 result, state-change evidence, approval, attempt or external authority exists.

## Consumed boundaries

D-129 through D-141 remain immutable consumed predecessors; `docs/09-evidence.md` owns their exact tuples and
zero-activity limits. The deferred D-121 candidate
`d121executioncandidate_b37bde7b9f49f92118ca277e521cd409b1e51b6f97c1ad8c2e9ff5090a1c38ef` was never
authorized and is not a fixed-bundle prerequisite.

## Closed authority

Provider/evaluator/agent calls, memory/retrieval execution, Docker or SDK observation, credential provisioning,
execution hash/candidate, cost reservation and A/C execution remain unauthorized and absent. Source qualification,
tests and this roadmap grant none of them.

## Next gate

The next gate is a **separately approved preflight attempt**, but none is presently admissible. It first requires
an independently trusted, one-use credential-provisioning evidence artifact and then an exact approval bound to
that artifact and contract v1. Provisioning itself remains a separate user-controlled authority; no value enters
the repository, approval text or chat. READY/BLOCKED/ERROR is terminal and grants no candidate or paid authority.

D-142 activation is not the next gate. Do not create its receipt, attempt, marker or terminal from this roadmap.
