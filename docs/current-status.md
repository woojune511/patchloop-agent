# Current status — 2026-08-13

## Current checkpoint

The project is switching from one-use preflight ceremony to a reusable fast track. Historical V1-V25 artifacts
remain immutable evidence, but a failed attempt no longer consumes its source or configuration. V25 remains
source-qualified/approval-bound with no attempt; its exact-immediate-run gate is superseded rather than executed.

D-142 remains **source-qualified only, unactivated** after 170/170 mocked tests, with no runtime observation. Its
planning disposition is now **deferred** and it is not the current A/C gate.

## Evaluator correctness gap

Evaluator-v1 assigns literal safety PASS, so historical results are not independently safety-verified. V2's
offline successor-only integration path receipt-gates typed evidence, persistence and qualification; raw results
remain `official=false` and local/mock tests are not official evidence.

The **successor A/C offline qualification** is `04ee027171d9d4891c4f481d2ccfb277e7a4a9e6`. It fixes the Moto/Babel
schedule, evaluator-v2 source/runtime identities and A-null/C-exact-three treatment. No official/live v2 result
exists yet.

## Fast-track roadmap

1. **Evaluator correctness v2.** Typed evidence, fail-closed aggregation and receipt-gated integration are local.
2. **Successor A/C qualification.** New source/runtime/suite identities are local; D-142/R2 remain predecessors.
3. **Reusable no-call preflight.** Run one bounded command, retrying only transient pre-provider failures up to
   three attempts. No state artifact, per-attempt approval prose or new V-number is required.
4. **Candidate and cost gate.** A clean preflight emits the execution hash and current pricing/reserve/cap. One
   explicit campaign approval binds that hash, the four fixed rows and the hard cap.
5. **Readiness panel.** The four-run A/C readiness runs Moto A/C and Babel C/A once. No outcome-bearing row is
   selectively retried; a confounded panel is preserved as inconclusive.
6. **Held-out A/C.** After valid readiness, preregister 12 tasks × A/C × at least two repetitions (48+ rows).
7. **Selective/full comparison.** B/D require frozen leakage/redaction/calibration or a fresh held-out panel.

## Evidence and retry rule

Completed attempt records are append-only. Source, configuration and campaign definitions are reusable until their
semantics change. A new contract version is required only for a schema, evaluator, security boundary or treatment
change—not for another execution of unchanged code or a transient local failure.

Historical V5/V7/V12/V13/V14/V16/V18/V20/V23 attempts remain immutable and are not rewritten. Their old
`retry=false` fields describe those artifacts; they do not prohibit the new fast-track policy.

## Closed authority

No provider call, paid A/C row or cost reservation is authorized by this policy change. Those remain blocked until
the fast preflight produces an exact execution hash and the user approves the single bounded campaign.

## Next gate

Finish local validation of the reusable preflight, then run it without provider/evaluator/agent calls. If it is
READY, generate the exact candidate and request one campaign-level paid approval. D-142 and the V25 one-use
lifecycle are not next gates.
